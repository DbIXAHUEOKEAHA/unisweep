"""Characterisation tests for the new engine.

Each test targets one of the legacy failure modes:
* the endpoint is always set and measured (last-step bug);
* the region condition works on forward AND backward walks (negative-atol bug);
* live edits of the running program take effect (the reason globals existed);
* manual step tables can be hot-swapped mid-sweep;
* coupled equalities follow the curve;
* pause is loop-based (thread survives) and stop is graceful.
"""

import os
import queue
import sys
import tempfile
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from unisweep.core.config import (AxisProgram, CountMode, LiveProgram,
                                  SweepProgram)
from unisweep.core.devices import DeviceRegistry, DriverAdapter
from unisweep.core.engine import SweepEngine
from unisweep.core import events as ev
from tests.mock_driver import MockDevice


class FakeRegistry(DeviceRegistry):
    """Registry that hands out mock devices without touching hardware."""

    def __init__(self, core_dir, mocks):
        self.core_dir = core_dir
        self._mocks = mocks
        self._adapters = {}
        self._lock = threading.Lock()

    def connect(self, address):
        with self._lock:
            if address not in self._adapters:
                self._adapters[address] = DriverAdapter(
                    address, self._mocks[address])
            return self._adapters[address]


def run_engine(program, mocks, live_hook=None, timeout=30):
    """Run a sweep to completion, return (events, live, mocks)."""
    tmp = tempfile.mkdtemp(prefix="unisweep_test_")
    live = LiveProgram(program)
    q = queue.Queue()
    registry = FakeRegistry(tmp, mocks)
    engine = SweepEngine(live, registry, tmp, q)
    if live_hook:
        threading.Thread(target=live_hook, args=(live, engine, q),
                         daemon=True).start()
    engine.start()
    engine.join(timeout)
    assert not engine.is_alive(), "engine did not finish"
    out = []
    while not q.empty():
        out.append(q.get_nowait())
    return out, live, tmp


def sweep_values(dev, param="Volt"):
    return [v for (p, v, *_ ) in dev.set_log if p == param]


def axis(**kw):
    base = dict(device="M1", parameter="Volt", start=0.0, stop=1.0,
                rate=10.0, delay=0.01, count_mode=CountMode.RATE)
    base.update(kw)
    return AxisProgram(**base)


# ---------------------------------------------------------------------------
def test_endpoint_always_measured_even_with_uneven_span():
    """0 -> 1 with step 0.3: legacy stopped at 0.9; endpoint must be 1.0."""
    dev = MockDevice()
    prog = SweepProgram(axes=(axis(rate=0.3, delay=0.01,
                                   count_mode=CountMode.STEP),),
                        reads=("M1.Noise",))
    evs, _, _ = run_engine(prog, {"M1": dev})
    vals = sweep_values(dev)
    assert vals[0] == 0.0
    assert abs(vals[-1] - 1.0) < 1e-12, f"endpoint missing, got {vals[-1]}"
    assert np.allclose(vals, [0.0, 0.3, 0.6, 0.9, 1.0])
    rows = [e for e in evs if isinstance(e, ev.PointMeasured)]
    assert len(rows) == 5
    assert float(rows[-1].row[1]) == 1.0
    fin = [e for e in evs if isinstance(e, ev.SweepFinished)]
    assert fin and not fin[0].stopped


def test_back_and_forth_walks_hit_both_endpoints():
    dev = MockDevice()
    prog = SweepProgram(axes=(axis(rate=0.5, delay=0.01,
                                   count_mode=CountMode.STEP, walks=2),),
                        reads=())
    evs, _, _ = run_engine(prog, {"M1": dev})
    vals = sweep_values(dev)
    assert np.allclose(vals, [0.0, 0.5, 1.0, 1.0, 0.5, 0.0])


def test_live_edit_of_stop_mid_sweep():
    """The whole point of the old globals: retarget the running walk."""
    dev = MockDevice()
    prog = SweepProgram(axes=(axis(rate=0.1, delay=0.05,
                                   count_mode=CountMode.STEP, stop=0.5),),
                        reads=())

    def hook(live, engine, q):
        time.sleep(0.14)                       # a few points in
        live.update_axis(0, stop=0.8)          # extend the sweep

    evs, _, _ = run_engine(prog, {"M1": dev}, live_hook=hook)
    vals = sweep_values(dev)
    assert abs(vals[-1] - 0.8) < 1e-12, f"live retarget failed: {vals[-1]}"
    assert max(vals) <= 0.8 + 1e-12


def test_live_edit_of_step_mid_sweep():
    dev = MockDevice()
    prog = SweepProgram(axes=(axis(rate=0.1, delay=0.05,
                                   count_mode=CountMode.STEP, stop=1.0),),
                        reads=())

    def hook(live, engine, q):
        time.sleep(0.14)
        live.update_axis(0, rate=0.4)          # coarser steps from now on

    evs, _, _ = run_engine(prog, {"M1": dev}, live_hook=hook)
    vals = sweep_values(dev)
    diffs = np.diff(vals)
    assert any(d > 0.35 for d in diffs), "step-size edit not picked up"
    assert abs(vals[-1] - 1.0) < 1e-12


def test_manual_points_hot_swap():
    dev = MockDevice()
    prog = SweepProgram(axes=(axis(delay=0.05,
                                   manual_points=(0.0, 0.1, 0.2, 0.3, 0.4,
                                                  0.5, 0.6, 0.7)),),
                        reads=())

    def hook(live, engine, q):
        time.sleep(0.13)
        live.swap_manual_points(0, (9.0, 9.5, 10.0), name="new_table")

    evs, _, _ = run_engine(prog, {"M1": dev}, live_hook=hook)
    vals = sweep_values(dev)
    assert 10.0 in vals, "hot-swapped manual table not used"
    assert vals[-1] == 10.0


def test_2d_sweep_files_and_region_condition_both_directions():
    """Region mask must hold on forward AND return walks (legacy negative-atol
    bug made every backward point vanish)."""
    d1, d2 = MockDevice("M1"), MockDevice("M2")
    prog = SweepProgram(
        axes=(
            AxisProgram(device="M1", parameter="Volt", start=0, stop=2,
                        rate=1.0, delay=0.0, count_mode=CountMode.STEP),
            AxisProgram(device="M2", parameter="Curr", start=0, stop=2,
                        rate=1.0, delay=0.01, count_mode=CountMode.STEP,
                        walks=2),
        ),
        reads=("M1.Noise",),
        condition="x + y <= 3",
    )
    evs, _, tmp = run_engine(prog, {"M1": d1, "M2": d2})
    measured = [e.axis_values for e in evs if isinstance(e, ev.PointMeasured)]
    skipped = [e.axis_values for e in evs if isinstance(e, ev.PointSkipped)]
    assert all(v1 + v2 <= 3 + 1e-9 for v1, v2 in measured)
    assert skipped, "condition never excluded anything"
    assert all(v1 + v2 > 3 - 1e-9 for v1, v2 in skipped)
    # both directions produced points (walks=2)
    forward = [m for m in measured if m[0] == 0.0]
    assert len(forward) >= 2
    files = {e.path for e in evs if isinstance(e, ev.FileOpened)}
    assert len(files) == 3, f"expected one file per master point, got {files}"
    # rotated names embed the master value
    assert any("_1.0-" in os.path.basename(f) for f in files)


def test_coupled_equality_follows_curve():
    d1, d2 = MockDevice("M1"), MockDevice("M2")
    prog = SweepProgram(
        axes=(
            AxisProgram(device="M1", parameter="Volt", start=0, stop=10,
                        rate=1, delay=0.0, count_mode=CountMode.STEP),
            AxisProgram(device="M2", parameter="Curr", start=0, stop=1,
                        rate=0.25, delay=0.01, count_mode=CountMode.STEP),
        ),
        reads=(),
        condition="x == 2*y + 1",
    )
    evs, _, _ = run_engine(prog, {"M1": d1, "M2": d2})
    pts = [e.axis_values for e in evs if isinstance(e, ev.PointMeasured)]
    assert pts, "no points measured in coupled mode"
    for v1, v2 in pts:
        assert abs(v1 - (2 * v2 + 1)) < 1e-6, f"curve not followed: {v1},{v2}"
    ys = [p[1] for p in pts]
    assert np.allclose(ys, [0, 0.25, 0.5, 0.75, 1.0])


def test_sweepable_device_continuous_mode():
    dev = MockDevice(sweepable_flags=[True, False], ramp_rate=50.0)
    prog = SweepProgram(
        axes=(AxisProgram(device="M1", parameter="Volt", start=0.0, stop=1.0,
                          rate=20.0, delay=0.02),),
        reads=())
    evs, _, _ = run_engine(prog, {"M1": dev})
    # one commanded set toward the target with a speed argument
    cmds = [c for c in dev.set_log if c[2] is not None]
    assert cmds and cmds[0][1] == 1.0
    rows = [e for e in evs if isinstance(e, ev.PointMeasured)]
    assert rows, "continuous mode produced no rows"
    assert abs(float(rows[-1].row[1]) - 1.0) <= 1e-6


def test_pause_longer_than_legacy_recursion_budget_and_stop():
    dev = MockDevice()
    prog = SweepProgram(axes=(axis(rate=0.1, delay=0.02,
                                   count_mode=CountMode.STEP),),
                        reads=())

    def hook(live, engine, q):
        time.sleep(0.06)
        engine.set_paused(True)
        time.sleep(1.5)                 # legacy: ~15 recursion frames/sec
        engine.set_paused(False)
        time.sleep(0.05)
        engine.stop()

    evs, _, _ = run_engine(prog, {"M1": dev}, live_hook=hook)
    kinds = [type(e).__name__ for e in evs]
    assert "SweepPaused" in kinds and "SweepResumed" in kinds
    fin = [e for e in evs if isinstance(e, ev.SweepFinished)]
    assert fin and fin[0].stopped


def test_empty_file_removed_and_rows_match_columns():
    dev = MockDevice()
    prog = SweepProgram(axes=(axis(rate=0.5, delay=0.0,
                                   count_mode=CountMode.STEP),),
                        reads=("M1.Noise", "M1.Curr"))
    evs, _, tmp = run_engine(prog, {"M1": dev})
    started = [e for e in evs if isinstance(e, ev.SweepStarted)][0]
    assert started.columns == ("time", "M1.Volt_sweep",
                               "M1.Noise", "M1.Curr")
    rows = [e.row for e in evs if isinstance(e, ev.PointMeasured)]
    assert all(len(r) == len(started.columns) for r in rows)
    files = [e.path for e in evs if isinstance(e, ev.FileOpened)]
    assert files and os.path.exists(files[0])
    with open(files[0]) as fh:
        lines = fh.read().strip().splitlines()
    assert len(lines) == 1 + len(rows)


def _find_map_tables(tmp):
    out = []
    for root, _d, names in os.walk(tmp):
        for n in names:
            if n.endswith(".csv") and "_map" in n and "tables" in root:
                out.append(os.path.join(root, n))
    return sorted(out)


def test_2d_map_spreadsheets_written():
    """Legacy mapper2D format: header 'axis1 / axis2' + inner grid, one line
    per master point, per read parameter, in 2d_maps/tables/<base>_<idx>."""
    d1, d2 = MockDevice("M1"), MockDevice("M2")
    prog = SweepProgram(
        axes=(
            AxisProgram(device="M1", parameter="Volt", start=0, stop=2,
                        rate=1.0, delay=0.0, count_mode=CountMode.STEP),
            AxisProgram(device="M2", parameter="Curr", start=0, stop=1,
                        rate=0.5, delay=0.0, count_mode=CountMode.STEP),
        ),
        reads=("M1.Noise", "M2.Curr"),
        map_images=False,
    )
    evs, _, tmp = run_engine(prog, {"M1": d1, "M2": d2})
    tables = _find_map_tables(tmp)
    assert len(tables) == 2, f"one map per read expected, got {tables}"
    named = {os.path.basename(t) for t in tables}
    assert any("M1.Noise_map.csv" in n for n in named)
    for t in tables:
        with open(t) as fh:
            lines = [ln.strip() for ln in fh if ln.strip()]
        header = lines[0].split(",")
        assert header[0] == "M1.Volt / M2.Curr"
        grid = [float(v) for v in header[1:]]
        assert grid == [0.0, 0.5, 1.0]
        assert len(lines) == 1 + 3, "one map row per master point"
        masters = [float(ln.split(",")[0]) for ln in lines[1:]]
        assert masters == [0.0, 1.0, 2.0]
        for ln in lines[1:]:
            assert len(ln.split(",")) == 1 + len(grid)
    noise = [t for t in tables if "M1.Noise" in t][0]
    with open(noise) as fh:
        row = fh.read().strip().splitlines()[1].split(",")[1:]
    assert all(abs(float(v) - 0.5) < 1e-9 for v in row)


def test_2d_map_condition_leaves_nan_cells():
    d1, d2 = MockDevice("M1"), MockDevice("M2")
    prog = SweepProgram(
        axes=(
            AxisProgram(device="M1", parameter="Volt", start=0, stop=2,
                        rate=1.0, delay=0.0, count_mode=CountMode.STEP),
            AxisProgram(device="M2", parameter="Curr", start=0, stop=2,
                        rate=1.0, delay=0.0, count_mode=CountMode.STEP),
        ),
        reads=("M1.Noise",),
        condition="x + y <= 2",
        map_images=False,
        map_interpolated=False,          # raw rows: NaN cells stay visible
    )
    evs, _, tmp = run_engine(prog, {"M1": d1, "M2": d2})
    table = _find_map_tables(tmp)[0]
    with open(table) as fh:
        lines = fh.read().strip().splitlines()
    last_row = lines[-1].split(",")      # master = 2: only y=0 measured
    assert float(last_row[0]) == 2.0
    assert last_row[1] != "nan" and "nan" in last_row[2:], \
        f"condition-excluded cells should be NaN: {last_row}"


def test_3d_map_iterations_per_master_point():
    d1, d2, d3 = MockDevice("M1"), MockDevice("M2"), MockDevice("M3")
    prog = SweepProgram(
        axes=(
            AxisProgram(device="M1", parameter="Volt", start=0, stop=1,
                        rate=1.0, delay=0.0, count_mode=CountMode.STEP),
            AxisProgram(device="M2", parameter="Volt", start=0, stop=1,
                        rate=0.5, delay=0.0, count_mode=CountMode.STEP),
            AxisProgram(device="M3", parameter="Curr", start=0, stop=1,
                        rate=0.5, delay=0.0, count_mode=CountMode.STEP),
        ),
        reads=("M3.Noise",),
        map_images=False,
    )
    evs, _, tmp = run_engine(prog, {"M1": d1, "M2": d2, "M3": d3})
    tables = _find_map_tables(tmp)
    # 2 master points -> map_0 and map_1 in per-master subfolders
    assert len(tables) == 2, f"expected one map per master point: {tables}"
    subdirs = {os.path.basename(os.path.dirname(t)) for t in tables}
    assert any(s.startswith("M1.Volt_") for s in subdirs), subdirs
    its = sorted(int(os.path.basename(t).rsplit("_", 1)[-1][:-4])
                 for t in tables)
    assert its == [0, 1]
    with open(tables[0]) as fh:
        lines = fh.read().strip().splitlines()
    assert lines[0].split(",")[0] == "M2.Volt / M3.Curr"
    assert len(lines) == 1 + 3, "one row per slave point"


def test_livedata_plane_filter():
    from unisweep.core.livedata import LiveData
    data = LiveData()
    data.reset(("time", "a1", "a2", "a3", "r"), 3)
    for m in (0.0, 1.0):
        for s in (0.0, 0.5):
            for ss in (0.0, 0.5):
                data.add_row((0.0, m, s, ss, m * 100 + s), (m, s, ss))
    assert data.plane_values(0) == [0.0, 1.0]
    x, y, z = data.map_arrays("a2", "a3", "r", plane_axis=0, plane_value=1.0)
    assert len(x) == 4 and all(abs(v - 100) < 1 for v in z)
    x, y, z = data.map_arrays("a2", "a3", "r", plane_axis=0,
                              plane_value="latest")
    assert len(x) == 4 and all(v >= 100 for v in z)


def test_map_rows_event_carries_legacy_walk_logic():
    """Live maps are built like the spreadsheets: walk-concatenated grid,
    one committed row per outer point, NaN condition holes — even with map
    files disabled."""
    d1, d2 = MockDevice("M1"), MockDevice("M2")
    prog = SweepProgram(
        axes=(AxisProgram(device="M1", parameter="Volt", start=0, stop=2,
                          rate=1.0, delay=0.0, count_mode=CountMode.STEP),
              AxisProgram(device="M2", parameter="Curr", start=0, stop=1,
                          rate=0.5, delay=0.0, count_mode=CountMode.STEP,
                          walks=2)),
        reads=("M2.Curr",), save_maps=False, condition="x + y <= 2.4")
    evs, _, tmp = run_engine(prog, {"M1": d1, "M2": d2})
    rows = [e for e in evs if isinstance(e, ev.MapRowCommitted)]
    assert len(rows) == 3
    assert rows[0].grid == (0.0, 0.5, 1.0, 0.5, 0.0), rows[0].grid
    from unisweep.core.livedata import LiveMaps
    maps = LiveMaps()
    maps.reset(("M2.Curr",))
    for r in rows:
        maps.on_row(r)
    grid, labels, mat = maps.matrix("M2.Curr")
    assert labels == [0.0, 1.0, 2.0]
    assert mat.shape == (3, 5)
    assert np.isnan(mat[2]).any() and not np.isnan(mat[0]).any()
    assert not _find_map_tables(tmp), "save_maps=False must write no files"


def test_map_rows_iterations_for_3d():
    devs = {n: MockDevice(n) for n in ("M1", "M2", "M3")}
    prog = SweepProgram(
        axes=(AxisProgram(device="M1", parameter="Volt", start=0, stop=1,
                          rate=1.0, delay=0.0, count_mode=CountMode.STEP),
              AxisProgram(device="M2", parameter="Volt", start=0, stop=1,
                          rate=0.5, delay=0.0, count_mode=CountMode.STEP),
              AxisProgram(device="M3", parameter="Curr", start=0, stop=1,
                          rate=0.5, delay=0.0, count_mode=CountMode.STEP)),
        reads=("M3.Curr",), save_maps=False)
    evs, _, _ = run_engine(prog, devs)
    rows = [e for e in evs if isinstance(e, ev.MapRowCommitted)]
    assert sorted(set(r.iteration for r in rows)) == [0, 1]
    from unisweep.core.livedata import LiveMaps
    maps = LiveMaps()
    maps.reset(("M3.Curr",))
    for r in rows:
        maps.on_row(r)
    assert len(maps.iteration_labels("M3.Curr")) == 2
    g, labels, mat = maps.matrix("M3.Curr", 0)      # first master plane
    assert mat.shape == (3, 3) and labels == [0.0, 0.5, 1.0]


def test_livedata_scan_boundaries_track_data_files():
    """Line plots default to the current scan: rows since the last file
    rotation — the legacy live-plot behaviour for 2-D/3-D."""
    from unisweep.core.livedata import LiveData
    data = LiveData()
    data.reset(("time", "a1", "a2", "r"), 2)
    data.new_file("f1.csv")
    for i in range(5):
        data.add_row((float(i), 0.0, i * 0.1, i), (0.0, i * 0.1))
    data.new_file("f2.csv")                 # master stepped -> new scan
    for i in range(3):
        data.add_row((float(i), 1.0, i * 0.1, 10 + i), (1.0, i * 0.1))
    x_all, y_all = data.xy("a2", "r")
    x_scan, y_scan = data.xy("a2", "r", scan_only=True)
    assert len(x_all) == 8 and len(x_scan) == 3
    assert list(y_scan) == [10, 11, 12], "scan slice must be the last file"
    # a mid-sweep reset (new sweep) restarts the boundaries
    data.reset(("time", "a1", "r"), 1)
    data.new_file("g1.csv")
    data.add_row((0.0, 0.0, 1.0), (0.0,))
    assert len(data.xy("a1", "r", scan_only=True)[0]) == 1


# ------------------- sweepable (self-ramping) devices ---------------------
def test_sweepable_walk_approaches_start_first():
    """The instrument sits at 0.7; a 0->1 sweep must first ramp to 0 (no
    rows recorded) and only then sweep 0->1 with rows. The legacy-style bug
    was ramping straight to 'stop' from wherever the device was."""
    dev = MockDevice(sweepable_flags=[True, False], ramp_rate=30.0)
    dev._values["Volt"] = 0.7
    prog = SweepProgram(
        axes=(AxisProgram(device="M1", parameter="Volt", start=0.0, stop=1.0,
                          rate=20.0, delay=0.02),),
        reads=())
    evs, _, _ = run_engine(prog, {"M1": dev})
    cmds = [(v, sp) for (p, v, sp, _t) in dev.set_log if p == "Volt"]
    assert cmds[0] == (0.0, 20.0), f"first command must approach start: {cmds}"
    assert cmds[1] == (1.0, 20.0), f"second command must sweep to stop: {cmds}"
    rows = [float(e.row[1]) for e in evs if isinstance(e, ev.PointMeasured)]
    assert rows, "no rows recorded"
    assert min(rows) >= -1e-9 and rows[0] <= 0.35, \
        f"rows must belong to the 0->1 sweep, not the approach: {rows[:4]}"
    assert abs(rows[-1] - 1.0) <= 1e-6
    fin = [e for e in evs if isinstance(e, ev.SweepFinished)][0]
    assert not fin.stopped


def test_sweepable_back_and_forth_hits_both_endpoints():
    dev = MockDevice(sweepable_flags=[True, False], ramp_rate=40.0)
    prog = SweepProgram(
        axes=(AxisProgram(device="M1", parameter="Volt", start=0.0, stop=1.0,
                          rate=25.0, delay=0.02, walks=2),),
        reads=())
    evs, _, _ = run_engine(prog, {"M1": dev})
    targets = [v for (p, v, sp, _t) in dev.set_log if sp is not None]
    assert targets[-2:] == [1.0, 0.0] or targets == [1.0, 0.0], targets
    rows = [float(e.row[1]) for e in evs if isinstance(e, ev.PointMeasured)]
    assert abs(max(rows) - 1.0) <= 1e-6 and abs(min(rows)) <= 1e-6


def test_sweepable_live_retarget_recommands_device():
    dev = MockDevice(sweepable_flags=[True, False], ramp_rate=2.0)
    prog = SweepProgram(
        axes=(AxisProgram(device="M1", parameter="Volt", start=0.0, stop=1.0,
                          rate=2.0, delay=0.05),),
        reads=())

    def hook(live, engine, q):
        time.sleep(0.25)                     # mid-ramp
        live.update_axis(0, stop=0.6)        # retarget shorter

    evs, _, _ = run_engine(prog, {"M1": dev}, live_hook=hook)
    cmds = [v for (p, v, sp, _t) in dev.set_log if sp is not None]
    assert 0.6 in cmds, f"retarget must re-command the instrument: {cmds}"
    rows = [float(e.row[1]) for e in evs if isinstance(e, ev.PointMeasured)]
    assert abs(rows[-1] - 0.6) <= 1e-6
    assert max(rows) <= 0.6 + 0.15           # never went far past new target


def test_sweepable_stall_warns_then_aborts_instead_of_hanging():
    """A dead ramp (readback freezes at 0.5) must produce a warning, then
    abort the walk — the legacy loop would spin forever writing rows."""
    dev = MockDevice(sweepable_flags=[True, False], ramp_rate=5.0,
                     stall_at=0.5)
    prog = SweepProgram(
        axes=(AxisProgram(device="M1", parameter="Volt", start=0.0, stop=1.0,
                          rate=5.0, delay=0.05),),
        reads=())
    import unisweep.core.engine as eng
    old_warn, old_abort = eng.SweepEngine.STALL_WARN_S, \
        eng.SweepEngine.STALL_ABORT_S
    eng.SweepEngine.STALL_WARN_S, eng.SweepEngine.STALL_ABORT_S = 0.4, 1.2
    try:
        evs, _, _ = run_engine(prog, {"M1": dev}, timeout=25)
    finally:
        eng.SweepEngine.STALL_WARN_S = old_warn
        eng.SweepEngine.STALL_ABORT_S = old_abort
    errors = [e for e in evs if isinstance(e, ev.SweepError)]
    assert any("stopped moving" in e.message for e in errors), \
        [e.message for e in errors]
    assert any("aborted" in e.message for e in errors)
    assert any(isinstance(e, ev.SweepFinished) for e in evs), \
        "engine must finish, not hang"


def test_sweepable_overshoot_counts_as_reached():
    """Instrument settles past the target, outside the eps band: the
    direction-aware reach test must still terminate the walk."""
    dev = MockDevice(sweepable_flags=[True, False], ramp_rate=40.0,
                     overshoot=0.05)
    prog = SweepProgram(
        axes=(AxisProgram(device="M1", parameter="Volt", start=0.0, stop=1.0,
                          rate=25.0, delay=0.02),),
        reads=())
    evs, _, _ = run_engine(prog, {"M1": dev}, timeout=20)
    fin = [e for e in evs if isinstance(e, ev.SweepFinished)]
    assert fin and not fin[0].stopped, "overshoot must not hang the walk"


def test_sweepable_zero_rate_falls_back_to_stepwise_with_warning():
    dev = MockDevice(sweepable_flags=[True, False])
    prog = SweepProgram(
        axes=(AxisProgram(device="M1", parameter="Volt", start=0.0, stop=1.0,
                          rate=0.0, delay=0.01, count_mode=CountMode.STEP),),
        reads=())
    evs, _, _ = run_engine(prog, {"M1": dev}, timeout=20)
    errors = [e for e in evs if isinstance(e, ev.SweepError)]
    assert any("not usable for a continuous ramp" in e.message
               for e in errors), [e.message for e in errors]
    fin = [e for e in evs if isinstance(e, ev.SweepFinished)]
    assert fin and not fin[0].stopped            # stepwise fallback ran


def test_sweepable_huge_eps_produces_warning():
    dev = MockDevice(sweepable_flags=[True, False], ramp_rate=40.0)
    dev.eps = [0.8, 1e-9]                        # eps covers most of 0..1
    prog = SweepProgram(
        axes=(AxisProgram(device="M1", parameter="Volt", start=0.0, stop=1.0,
                          rate=25.0, delay=0.02),),
        reads=())
    evs, _, _ = run_engine(prog, {"M1": dev}, timeout=20)
    errors = [e for e in evs if isinstance(e, ev.SweepError)]
    assert any("covers half the sweep span" in e.message for e in errors)


def test_outer_sweepable_master_settles_before_inner_scan():
    """2-D map with a slow self-ramping master: the inner scan must not
    start until the master readback reaches its point."""
    master = MockDevice("M1", sweepable_flags=[True, False], ramp_rate=4.0)
    slave = MockDevice("M2")
    prog = SweepProgram(
        axes=(AxisProgram(device="M1", parameter="Volt", start=0.0, stop=1.0,
                          rate=4.0, delay=0.0, count_mode=CountMode.STEP,
                          rate_unused=None) if False else
              AxisProgram(device="M1", parameter="Volt", start=0.0, stop=1.0,
                          rate=0.5, delay=0.0, count_mode=CountMode.STEP),
              AxisProgram(device="M2", parameter="Curr", start=0.0, stop=0.2,
                          rate=0.1, delay=0.01, count_mode=CountMode.STEP)),
        reads=(), save_maps=False)
    evs, _, _ = run_engine(prog, {"M1": master, "M2": slave}, timeout=30)
    # master commands at 0, 0.5, 1.0 with speed; each followed by slave
    # commands only AFTER the ramp time (distance/rate = 0.5/4 = 0.125 s)
    log = [(p, v, sp, t) for (p, v, sp, t) in
           (master.set_log + slave.set_log)]
    log.sort(key=lambda e: e[3])
    master_cmds = [(v, t) for (p, v, sp, t) in log if p == "Volt"]
    assert [v for v, _ in master_cmds] == [0.0, 0.5, 1.0]
    for (mv, mt) in master_cmds[1:]:
        first_slave_after = min(t for (p, v, sp, t) in log
                                if p == "Curr" and t > mt)
        assert first_slave_after - mt >= 0.5 / 4.0 * 0.8, \
            "inner scan started before the master settled"
    master_speeds = [sp for (p, v, sp, t) in master.set_log if p == "Volt"]
    assert all(sp is not None for sp in master_speeds), \
        "outer sweepable steps must carry a speed"


def test_probe_sweepable_classifies_devices():
    from unisweep.core.devices import DriverAdapter, probe_sweepable
    ramping = DriverAdapter("A", MockDevice(sweepable_flags=[True, False],
                                            ramp_rate=2.0))
    r = probe_sweepable(ramping, "Volt", target=1.0, rate=2.0,
                        timeout=5, poll=0.05)
    assert r["outcome"] == "ramps" and r["agrees_with_flag"] is True, r
    jumping = DriverAdapter("B", MockDevice(sweepable_flags=[False, False]))
    r = probe_sweepable(jumping, "Volt", target=1.0, rate=2.0,
                        timeout=5, poll=0.05)
    assert r["outcome"] == "jumps" and r["agrees_with_flag"] is True, r
    # driver LIES: flag says sweepable but the device jumps — override at
    # the adapter level so the mock itself keeps jumping
    liar = DriverAdapter("C", MockDevice(sweepable_flags=[False, False]))
    liar.sweepable = lambda p: True
    r = probe_sweepable(liar, "Volt", target=1.0, rate=2.0,
                        timeout=5, poll=0.05)
    assert r["outcome"] == "jumps" and r["agrees_with_flag"] is False, r
    stuck = DriverAdapter("D", MockDevice(sweepable_flags=[True, False],
                                          ramp_rate=2.0, stall_at=0.4))
    r = probe_sweepable(stuck, "Volt", target=1.0, rate=2.0,
                        timeout=1.5, poll=0.05)
    assert r["outcome"] == "stalled", r


# ------------- realistic fault conditions during a sweep -------------------
def _fin(evs):
    f = [e for e in evs if isinstance(e, ev.SweepFinished)]
    assert f, "engine must always emit SweepFinished (never hang)"
    return f[0]


def _read_col(evs, idx=-1):
    return [e.row[idx] for e in evs if isinstance(e, ev.PointMeasured)]


def _prog_1d(points=8, delay=0.01, reads=("M2.Curr",)):
    return SweepProgram(
        axes=(AxisProgram(device="M1", parameter="Volt", start=0.0,
                          stop=float(points - 1), rate=1.0, delay=delay,
                          count_mode=CountMode.STEP),),
        reads=reads)


def test_read_device_nan_window_then_recovers():
    """A read instrument spits NaN for a while, then works again: the sweep
    records NaN for those rows, warns once naming the device, and simply
    continues — no hang, no stop."""
    m1 = MockDevice("M1")
    m2 = MockDevice("M2", fault={"param": "Curr", "kind": "nan",
                                 "start": 3, "end": 6})
    evs, _, _ = run_engine(_prog_1d(8), {"M1": m1, "M2": m2}, timeout=30)
    col = [float(v) for v in _read_col(evs)]
    assert len(col) == 8, f"all points must be measured, got {len(col)}"
    assert [bool(np.isnan(v)) for v in col] == \
        [False, False, True, True, True, False, False, False], col
    errors = [e for e in evs if isinstance(e, ev.SweepError)]
    nan_warns = [e for e in errors if "NaN" in e.message]
    assert len(nan_warns) == 1 and "M2.Curr" in nan_warns[0].where
    assert not any(e.fatal for e in errors)
    assert not _fin(evs).stopped


def test_read_device_nan_forever_sweep_still_completes():
    m2 = MockDevice("M2", fault={"param": "Curr", "kind": "nan", "start": 2})
    evs, _, _ = run_engine(_prog_1d(8), {"M1": MockDevice("M1"), "M2": m2},
                           timeout=30)
    col = [float(v) for v in _read_col(evs)]
    assert len(col) == 8 and all(np.isnan(v) for v in col[1:])
    errors = [e for e in evs if isinstance(e, ev.SweepError)]
    assert sum("NaN" in e.message for e in errors) == 1     # warned once
    assert not any(e.fatal for e in errors)
    assert not _fin(evs).stopped


def test_read_device_raises_then_recovers():
    m2 = MockDevice("M2", fault={"param": "Curr", "kind": "raise",
                                 "start": 3, "end": 5})
    evs, _, _ = run_engine(_prog_1d(8), {"M1": MockDevice("M1"), "M2": m2},
                           timeout=30)
    col = _read_col(evs)
    assert len(col) == 8
    nan_rows = [i for i, v in enumerate(col)
                if isinstance(v, float) and np.isnan(v)]
    assert nan_rows == [2, 3], f"failed reads must be NaN rows: {nan_rows}"
    errors = [e for e in evs if isinstance(e, ev.SweepError)]
    assert any("M2.Curr" in e.where and "not responding" in e.message
               for e in errors)
    assert not any(e.fatal for e in errors)
    assert not _fin(evs).stopped


def test_read_device_dies_completely_sweep_continues():
    """Read instrument stops responding for good: every remaining row gets
    NaN, one deduped warning names the device, and the sweep finishes."""
    m2 = MockDevice("M2", fault={"param": "Curr", "kind": "raise",
                                 "start": 2})
    evs, _, _ = run_engine(_prog_1d(10), {"M1": MockDevice("M1"), "M2": m2},
                           timeout=30)
    col = _read_col(evs)
    assert len(col) == 10
    assert all(isinstance(v, float) and np.isnan(v) for v in col[1:])
    errors = [e for e in evs if isinstance(e, ev.SweepError)]
    assert sum("M2.Curr" in e.where for e in errors) == 1
    assert not any(e.fatal for e in errors)
    assert not _fin(evs).stopped


def test_read_device_throttles_then_recovers():
    """One read blocks for 2 s (busy instrument), then answers: no data is
    lost, nothing aborts, and the sweep merely takes longer."""
    m2 = MockDevice("M2", fault={"param": "Curr", "kind": "hang",
                                 "start": 3, "end": 4, "hang_s": 2.0})
    t0 = time.time()
    evs, _, _ = run_engine(_prog_1d(6), {"M1": MockDevice("M1"), "M2": m2},
                           timeout=40)
    wall = time.time() - t0
    col = [float(v) for v in _read_col(evs)]
    assert len(col) == 6 and not any(np.isnan(v) for v in col)
    assert wall >= 2.0, "the block must actually have happened"
    assert not [e for e in evs if isinstance(e, ev.SweepError)]
    assert not _fin(evs).stopped


def _short_budgets():
    import unisweep.core.engine as eng
    return eng.SweepEngine, (eng.SweepEngine.STALL_WARN_S,
                             eng.SweepEngine.STALL_ABORT_S)


def test_axis_nan_readback_stops_sweep_naming_device():
    """NaN on the SWEEP AXIS readback is crucial: warn with the device name
    and a grace period, then stop the whole sweep. (A plain NaN used to
    defeat the stall watchdog — every comparison False — looping forever.)"""
    eng_cls, old = _short_budgets()
    eng_cls.STALL_WARN_S, eng_cls.STALL_ABORT_S = 0.3, 1.0
    try:
        m1 = MockDevice("M1", sweepable_flags=[True, False], ramp_rate=5.0,
                        fault={"param": "Volt", "kind": "nan", "start": 4})
        prog = SweepProgram(
            axes=(AxisProgram(device="M1", parameter="Volt", start=0.0,
                              stop=1.0, rate=5.0, delay=0.05),),
            reads=())
        evs, _, _ = run_engine(prog, {"M1": m1}, timeout=25)
    finally:
        eng_cls.STALL_WARN_S, eng_cls.STALL_ABORT_S = old
    errors = [e for e in evs if isinstance(e, ev.SweepError)]
    warns = [e for e in errors if e.crucial and not e.fatal]
    assert any("M1.Volt" in e.message and "NaN" in e.message
               for e in warns), [e.message for e in errors]
    fatals = [e for e in errors if e.fatal]
    assert fatals and fatals[0].crucial and "M1.Volt" in fatals[0].message
    for e in evs:                                  # no NaN axis rows leaked
        if isinstance(e, ev.PointMeasured):
            assert np.isfinite(float(e.row[1]))
    assert _fin(evs) is not None


def test_axis_nan_short_glitch_recovers_and_completes():
    eng_cls, old = _short_budgets()
    eng_cls.STALL_WARN_S, eng_cls.STALL_ABORT_S = 0.2, 3.0
    try:
        m1 = MockDevice("M1", sweepable_flags=[True, False], ramp_rate=3.0,
                        fault={"param": "Volt", "kind": "nan",
                               "start": 3, "end": 9})
        prog = SweepProgram(
            axes=(AxisProgram(device="M1", parameter="Volt", start=0.0,
                              stop=1.0, rate=3.0, delay=0.05),),
            reads=())
        evs, _, _ = run_engine(prog, {"M1": m1}, timeout=25)
    finally:
        eng_cls.STALL_WARN_S, eng_cls.STALL_ABORT_S = old
    errors = [e for e in evs if isinstance(e, ev.SweepError)]
    assert not any(e.fatal for e in errors), [e.message for e in errors]
    rows = [float(e.row[1]) for e in evs if isinstance(e, ev.PointMeasured)]
    assert rows and abs(rows[-1] - 1.0) <= 1e-6, rows
    assert not _fin(evs).stopped


def test_axis_dead_readback_stops_sweep_naming_device():
    eng_cls, old = _short_budgets()
    eng_cls.STALL_WARN_S, eng_cls.STALL_ABORT_S = 0.3, 1.0
    try:
        m1 = MockDevice("M1", sweepable_flags=[True, False], ramp_rate=5.0,
                        fault={"param": "Volt", "kind": "raise", "start": 4})
        prog = SweepProgram(
            axes=(AxisProgram(device="M1", parameter="Volt", start=0.0,
                              stop=1.0, rate=5.0, delay=0.05),),
            reads=())
        evs, _, _ = run_engine(prog, {"M1": m1}, timeout=25)
    finally:
        eng_cls.STALL_WARN_S, eng_cls.STALL_ABORT_S = old
    errors = [e for e in evs if isinstance(e, ev.SweepError)]
    fatals = [e for e in errors if e.fatal]
    assert fatals and fatals[0].crucial and "M1.Volt" in fatals[0].message \
        and "failing" in " ".join(e.message for e in errors)
    assert _fin(evs) is not None


def test_axis_set_failure_stops_sweep_naming_device():
    m1 = MockDevice("M1", fault={"param": "Volt", "kind": "set_raise",
                                 "start": 3})
    evs, _, _ = run_engine(_prog_1d(6, reads=()), {"M1": m1}, timeout=25)
    errors = [e for e in evs if isinstance(e, ev.SweepError)]
    fatals = [e for e in errors if e.fatal]
    assert fatals and fatals[0].crucial
    assert "M1.Volt" in fatals[0].message and "set" in fatals[0].message
    assert _fin(evs) is not None
    rows = [e for e in evs if isinstance(e, ev.PointMeasured)]
    assert len(rows) == 2, "points before the failure must be preserved"


# ---------------- XYZ output, interpolation, uniform grids -----------------
def _find_xyz(tmp):
    out = []
    for root, _dirs, files in os.walk(tmp):
        if os.path.basename(root) == "xyz":
            out += [os.path.join(root, f) for f in files]
    return sorted(out)


def test_xyz_single_continuous_file_2d():
    """map_style='xyz': one continuous long-format file per read parameter —
    a row per measured point with the axis values as columns, never
    re-gridded; condition-skipped points are absent; NaN reads say 'nan'."""
    d1, d2 = MockDevice("M1"), MockDevice(
        "M2", fault={"param": "Curr", "kind": "nan", "start": 4, "end": 5})
    prog = SweepProgram(
        axes=(AxisProgram(device="M1", parameter="Volt", start=0, stop=2,
                          rate=1.0, delay=0.0, count_mode=CountMode.STEP),
              AxisProgram(device="M2", parameter="Volt", start=0, stop=1,
                          rate=0.5, delay=0.0, count_mode=CountMode.STEP)),
        reads=("M2.Curr",), map_style="xyz", condition="x + y <= 2.6")
    evs, _, tmp = run_engine(prog, {"M1": d1, "M2": d2})
    xyz = _find_xyz(tmp)
    assert len(xyz) == 1, xyz
    lines = open(xyz[0]).read().splitlines()
    header = lines[0].split(",")
    assert header[0].startswith("M1.Volt") and \
        header[1].startswith("M2.Volt") and header[2] == "M2.Curr", header
    rows = [ln.split(",") for ln in lines[1:]]
    measured = [e for e in evs if isinstance(e, ev.PointMeasured)]
    assert len(rows) == len(measured) == 8   # 9 grid pts, 1 skipped
    assert [(float(r[0]), float(r[1])) for r in rows] == \
        [(0.0, 0.0), (0.0, 0.5), (0.0, 1.0),
         (1.0, 0.0), (1.0, 0.5), (1.0, 1.0),
         (2.0, 0.0), (2.0, 0.5)]
    assert rows[3][2] == "nan"                # the injected NaN read
    assert not _find_map_tables(tmp), "style='xyz' must not write worksheets"


def test_xyz_3d_stays_in_one_file_with_master_column():
    devs = {n: MockDevice(n) for n in ("M1", "M2", "M3")}
    prog = SweepProgram(
        axes=(AxisProgram(device="M1", parameter="Volt", start=0, stop=1,
                          rate=1.0, delay=0.0, count_mode=CountMode.STEP),
              AxisProgram(device="M2", parameter="Volt", start=0, stop=1,
                          rate=0.5, delay=0.0, count_mode=CountMode.STEP),
              AxisProgram(device="M3", parameter="Curr", start=0, stop=1,
                          rate=0.5, delay=0.0, count_mode=CountMode.STEP)),
        reads=("M3.Curr",), map_style="both")
    evs, _, tmp = run_engine(prog, devs)
    xyz = _find_xyz(tmp)
    assert len(xyz) == 1, "3-D sweep must stay in ONE continuous xyz file"
    lines = open(xyz[0]).read().splitlines()
    assert len(lines) == 1 + 2 * 3 * 3
    masters = sorted({float(ln.split(",")[0]) for ln in lines[1:]})
    assert masters == [0.0, 1.0], "master column must span both planes"
    assert _find_map_tables(tmp), "style='both' must also write worksheets"


def test_interpolation_preserves_hysteresis_between_walks():
    """Forward and backward walks are matched segment-by-segment: a global
    nearest-by-value lookup would mix the two passes at duplicated grid
    values and destroy hysteresis."""
    import unisweep.core.maps as maps_mod
    from unisweep.core.config import LiveProgram

    prog = SweepProgram(
        axes=(AxisProgram(device="M1", parameter="Volt", start=0, stop=2,
                          rate=1.0, delay=0.0, count_mode=CountMode.STEP),
              AxisProgram(device="M2", parameter="Volt", start=0, stop=1,
                          rate=0.5, delay=0.0, count_mode=CountMode.STEP,
                          walks=2)),
        reads=("M2.Curr",))
    live = LiveProgram(prog)
    tmp = tempfile.mkdtemp()
    w = maps_mod.MapWriter(tmp, live, [0, 1], ["M2.Curr"],
                           os.path.join(tmp, "x.csv"), interpolated=True,
                           images=False, write_files=False)
    # forward pass reads 10,11,12 — backward pass reads 20,21 (hysteresis)
    for x, v in [(0.0, 10), (0.5, 11), (1.0, 12), (0.5, 21), (0.0, 20)]:
        w.add_point(x, [v], axis_values=(0.0, x))
    grid, rows = w.commit_row(row_value=0.0)
    assert tuple(grid) == (0.0, 0.5, 1.0, 0.5, 0.0)
    assert list(rows["M2.Curr"]) == [10, 11, 12, 21, 20], rows
    w.close()


def test_interpolation_maps_offset_readbacks_and_keeps_nan_holes():
    """Sweepable readbacks land between grid points -> nearest per segment;
    a NaN sample stays a NaN cell and is never smeared onto neighbours; an
    aborted walk leaves its remaining cells NaN."""
    import unisweep.core.maps as maps_mod
    from unisweep.core.config import LiveProgram
    prog = SweepProgram(
        axes=(AxisProgram(device="M1", parameter="Volt", start=0, stop=1,
                          rate=1.0, delay=0.0, count_mode=CountMode.STEP),
              AxisProgram(device="M2", parameter="Volt", start=0, stop=1,
                          rate=0.25, delay=0.0, count_mode=CountMode.STEP,
                          walks=2)),
        reads=("r",))
    live = LiveProgram(prog)
    tmp = tempfile.mkdtemp()
    w = maps_mod.MapWriter(tmp, live, [0, 1], ["r"],
                           os.path.join(tmp, "x.csv"), interpolated=True,
                           images=False, write_files=False)
    # forward samples slightly off-grid, one NaN, backward walk ABORTED
    for x, v in [(0.02, 1.0), (0.26, 2.0), (0.49, np.nan),
                 (0.77, 4.0), (0.99, 5.0)]:
        w.add_point(x, [v], axis_values=(0.0, x))
    grid, rows = w.commit_row(row_value=0.0)
    row = list(rows["r"])
    assert tuple(grid) == (0.0, 0.25, 0.5, 0.75, 1.0, 0.75, 0.5, 0.25, 0.0)
    assert row[0] == 1.0 and row[1] == 2.0 and np.isnan(row[2]) \
        and row[3] == 4.0 and row[4] == 5.0, row
    assert all(np.isnan(v) for v in row[5:]), \
        f"aborted backward walk must stay NaN: {row}"
    w.close()


def test_uniform_grid_resamples_manual_points():
    import unisweep.core.maps as maps_mod
    from unisweep.core.config import LiveProgram
    prog = SweepProgram(
        axes=(AxisProgram(device="M1", parameter="Volt", start=0, stop=1,
                          rate=1.0, delay=0.0, count_mode=CountMode.STEP),
              AxisProgram(device="M2", parameter="Volt", start=0, stop=1,
                          rate=0.5, delay=0.0, count_mode=CountMode.STEP,
                          manual_points=(0.0, 0.1, 0.5, 1.0))),
        reads=("r",))
    live = LiveProgram(prog)
    tmp = tempfile.mkdtemp()
    # non-uniform: the grid IS the manual points
    w = maps_mod.MapWriter(tmp, live, [0, 1], ["r"],
                           os.path.join(tmp, "a.csv"), interpolated=False,
                           images=False, write_files=False, uniform=False)
    for x, v in [(0.0, 1), (0.1, 2), (0.5, 3), (1.0, 4)]:
        w.add_point(x, [v], axis_values=(0.0, x))
    grid, rows = w.commit_row(0.0)
    assert tuple(grid) == (0.0, 0.1, 0.5, 1.0)
    assert list(rows["r"]) == [1, 2, 3, 4]
    w.close()
    # uniform: linspace over the same range, samples mapped by value
    w = maps_mod.MapWriter(tmp, live, [0, 1], ["r"],
                           os.path.join(tmp, "b.csv"), interpolated=False,
                           images=False, write_files=False, uniform=True)
    for x, v in [(0.0, 1), (0.1, 2), (0.5, 3), (1.0, 4)]:
        w.add_point(x, [v], axis_values=(0.0, x))
    grid, rows = w.commit_row(0.0)
    assert np.allclose(grid, [0.0, 1 / 3, 2 / 3, 1.0])
    # nearest by value: 0.0->sample 0.0 (1), 1/3->0.5 (3), 2/3->0.5 (3)
    assert list(rows["r"]) == [1, 3, 3, 4], rows
    w.close()


def test_app_settings_roundtrip_and_program_stamp():
    from unisweep.core.settings import AppSettings
    tmp = tempfile.mkdtemp()
    os.makedirs(os.path.join(tmp, "config"))
    st = AppSettings.load(tmp)                      # defaults
    assert st.map_style == "grid" and st.save_maps
    st.map_style = "both"
    st.map_uniform = True
    st.stall_warn_s = 5.0
    st.stall_abort_s = 20.0
    st.save(tmp)
    st2 = AppSettings.load(tmp)
    assert st2.map_style == "both" and st2.map_uniform \
        and st2.stall_abort_s == 20.0
    # invalid values are sanitised on load
    import json
    with open(os.path.join(tmp, "config", "settings.json"), "w") as fh:
        json.dump({"map_style": "bogus", "stall_warn_s": 0,
                   "stall_abort_s": -1}, fh)
    st3 = AppSettings.load(tmp)
    assert st3.map_style == "grid" and st3.stall_abort_s > st3.stall_warn_s


if __name__ == "__main__":
    import traceback
    passed = failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
                passed += 1
            except Exception:
                print(f"FAIL {name}")
                traceback.print_exc()
                failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)


# --------------------------------------------------------------------------
