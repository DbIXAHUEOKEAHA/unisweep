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
    # the turning point is set and measured ONCE — the walk-concatenated
    # map grid (0, .5, 1, .5, 0) always counted it once, and the old
    # duplicate row shifted every later cell
    assert np.allclose(vals, [0.0, 0.5, 1.0, 0.5, 0.0])


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


# ---------------- return sweep: full configuration matrix ------------------
def _speeds(dev, param="Volt"):
    return [(v, sp) for (p, v, sp, _t) in dev.set_log if p == param]


def test_return_sweep_implied_for_setpoint_instrument():
    """THE reported bug: back_rate entered, walks left at 1 — the return
    pass silently never ran. Now a return rate implies there-and-back."""
    dev = MockDevice(sweepable_flags=[True, False], ramp_rate=60.0)
    prog = SweepProgram(
        axes=(AxisProgram(device="M1", parameter="Volt", start=0.0, stop=1.0,
                          rate=30.0, delay=0.02, back_rate=10.0),),  # walks=1!
        reads=())
    evs, _, _ = run_engine(prog, {"M1": dev}, timeout=25)
    cmds = _speeds(dev)
    assert (1.0, 30.0) in cmds, f"forward ramp at the forward rate: {cmds}"
    assert (0.0, 10.0) in cmds, f"RETURN ramp at the RETURN rate: {cmds}"
    rows = [float(e.row[1]) for e in evs if isinstance(e, ev.PointMeasured)]
    assert abs(max(rows) - 1.0) <= 1e-6 and abs(rows[-1]) <= 1e-6, \
        f"must go there AND back: {rows[:3]}…{rows[-3:]}"
    fin = [e for e in evs if isinstance(e, ev.SweepFinished)][0]
    assert not fin.stopped


def test_return_sweep_implied_by_back_delay_only():
    dev = MockDevice(sweepable_flags=[True, False], ramp_rate=60.0)
    prog = SweepProgram(
        axes=(AxisProgram(device="M1", parameter="Volt", start=0.0, stop=1.0,
                          rate=25.0, delay=0.02, back_delay=0.06),),
        reads=())
    evs, _, _ = run_engine(prog, {"M1": dev}, timeout=25)
    cmds = _speeds(dev)
    # both passes commanded; return uses the FORWARD rate (no back_rate)
    assert (1.0, 25.0) in cmds and (0.0, 25.0) in cmds, cmds
    rows = [float(e.row[1]) for e in evs if isinstance(e, ev.PointMeasured)]
    assert abs(rows[-1]) <= 1e-6


def test_return_sweep_explicit_walks_2_matches_implied():
    for walks in (1, 2):
        dev = MockDevice(sweepable_flags=[True, False], ramp_rate=60.0)
        prog = SweepProgram(
            axes=(AxisProgram(device="M1", parameter="Volt", start=0.0,
                              stop=1.0, rate=30.0, delay=0.02,
                              back_rate=12.0, walks=walks),),
            reads=())
        evs, _, _ = run_engine(prog, {"M1": dev}, timeout=25)
        assert (0.0, 12.0) in _speeds(dev), f"walks={walks}: {_speeds(dev)}"


def test_return_sweep_step_mode_setpoint_instrument():
    """STEP count mode: the rate fields hold steps; the commanded speeds
    still follow forward/back fields per pass."""
    dev = MockDevice(sweepable_flags=[True, False], ramp_rate=60.0)
    prog = SweepProgram(
        axes=(AxisProgram(device="M1", parameter="Volt", start=0.0, stop=1.0,
                          rate=0.25, delay=0.02, back_rate=0.5,
                          count_mode=CountMode.STEP),),
        reads=())
    evs, _, _ = run_engine(prog, {"M1": dev}, timeout=25)
    cmds = _speeds(dev)
    assert (1.0, 0.25) in cmds and (0.0, 0.5) in cmds, cmds
    rows = [float(e.row[1]) for e in evs if isinstance(e, ev.PointMeasured)]
    assert abs(rows[-1]) <= 1e-6


def test_return_sweep_force_stepwise_uses_back_rate_and_step():
    """Force stepwise on a setpoint instrument: every backward SET must
    carry the RETURN rate as speed and land on the back step grid — the
    old code sent the forward rate on both passes."""
    dev = MockDevice(sweepable_flags=[True, False], ramp_rate=60.0)
    prog = SweepProgram(
        axes=(AxisProgram(device="M1", parameter="Volt", start=0.0, stop=1.0,
                          rate=0.25, delay=0.01, back_rate=0.5,
                          back_delay=0.02, count_mode=CountMode.STEP,
                          force_stepwise=True),),
        reads=())
    evs, _, _ = run_engine(prog, {"M1": dev}, timeout=25)
    cmds = _speeds(dev)
    forward = [c for c in cmds[: 5]]
    backward = [c for c in cmds[5:]]
    assert [v for v, _ in forward] == [0.0, 0.25, 0.5, 0.75, 1.0], forward
    assert all(sp == 0.25 for _, sp in forward), forward
    assert [v for v, _ in backward] == [0.5, 0.0], \
        f"backward must use the BACK step (0.5): {backward}"
    assert all(sp == 0.5 for _, sp in backward), \
        f"backward sets must carry the BACK rate: {backward}"


def test_return_sweep_plain_stepwise_instrument():
    """Non-sweepable device: return pass runs the back step/delay grid."""
    dev = MockDevice()                       # not sweepable
    prog = SweepProgram(
        axes=(AxisProgram(device="M1", parameter="Volt", start=0.0, stop=1.0,
                          rate=0.25, delay=0.01, back_rate=0.5,
                          back_delay=0.02, count_mode=CountMode.STEP),),
        reads=())
    t0 = time.time()
    evs, _, _ = run_engine(prog, {"M1": dev}, timeout=25)
    wall = time.time() - t0
    vals = [v for (p, v, sp, _t) in dev.set_log if p == "Volt"]
    assert vals == [0.0, 0.25, 0.5, 0.75, 1.0, 0.5, 0.0], vals
    assert all(sp is None for (p, v, sp, _t) in dev.set_log), \
        "plain stepwise devices get no speed argument"
    assert wall >= 5 * 0.01 + 2 * 0.02 - 0.005


def test_return_sweep_different_delays_change_row_density():
    """Continuous ramp: a longer back_delay means fewer polls on the
    return pass at the same physical rate."""
    dev = MockDevice(sweepable_flags=[True, False], ramp_rate=2.0)
    prog = SweepProgram(
        axes=(AxisProgram(device="M1", parameter="Volt", start=0.0, stop=1.0,
                          rate=2.0, delay=0.05, back_delay=0.15),),
        reads=())
    evs, _, _ = run_engine(prog, {"M1": dev}, timeout=30)
    rows = [float(e.row[1]) for e in evs if isinstance(e, ev.PointMeasured)]
    peak = rows.index(max(rows))
    n_fwd, n_back = peak + 1, len(rows) - peak - 1
    assert n_fwd >= 2 * n_back, \
        f"3x back_delay must thin the return rows: {n_fwd} vs {n_back}"


def test_return_sweep_map_grid_includes_return_pass():
    """2-D map with an implied return on the inner axis: the frozen grid
    must span BOTH passes and the backward samples must land in it (a
    walk-count mismatch would silently drop the return data as NaN)."""
    d1 = MockDevice("M1")
    d2 = MockDevice("M2", sweepable_flags=[True, False], ramp_rate=60.0)
    prog = SweepProgram(
        axes=(AxisProgram(device="M1", parameter="Volt", start=0.0, stop=1.0,
                          rate=1.0, delay=0.0, count_mode=CountMode.STEP),
              AxisProgram(device="M2", parameter="Volt", start=0.0, stop=1.0,
                          rate=0.5, delay=0.02, back_rate=0.5,
                          count_mode=CountMode.STEP, force_stepwise=True),),
        reads=("M2.Volt",), save_maps=False)
    evs, _, _ = run_engine(prog, {"M1": d1, "M2": d2}, timeout=30)
    rows = [e for e in evs if isinstance(e, ev.MapRowCommitted)]
    assert rows, "map rows must be committed"
    grid = rows[0].grid
    assert grid == (0.0, 0.5, 1.0, 0.5, 0.0), \
        f"grid must concatenate the implied return pass: {grid}"
    for r in rows:
        vals = np.asarray(r.read_rows["M2.Volt"], dtype=float)
        assert not np.isnan(vals).any(), \
            f"return-pass cells must hold data, not NaN: {vals}"


def test_return_sweep_snake_mode_completes_both_directions():
    """Snake + return sweep on the inner axis of a 2-D map: every master
    point still covers both endpoints and the sweep completes."""
    d1 = MockDevice("M1")
    d2 = MockDevice("M2", sweepable_flags=[True, False], ramp_rate=60.0)
    prog = SweepProgram(
        axes=(AxisProgram(device="M1", parameter="Volt", start=0.0, stop=1.0,
                          rate=0.5, delay=0.0, count_mode=CountMode.STEP),
              AxisProgram(device="M2", parameter="Volt", start=0.0, stop=1.0,
                          rate=30.0, delay=0.02, back_rate=15.0,
                          snake=True),),
        reads=(), save_maps=False)
    evs, _, _ = run_engine(prog, {"M1": d1, "M2": d2}, timeout=40)
    fin = [e for e in evs if isinstance(e, ev.SweepFinished)][0]
    assert not fin.stopped
    per_master: dict = {}
    for e in evs:
        if isinstance(e, ev.PointMeasured):
            per_master.setdefault(float(e.axis_values[0]),
                                  []).append(float(e.axis_values[1]))
    assert len(per_master) == 3
    for master, inner in per_master.items():
        assert abs(max(inner) - 1.0) <= 1e-6 and abs(min(inner)) <= 1e-6, \
            f"master {master}: inner axis must span both ends: " \
            f"{min(inner)}..{max(inner)}"


# ---------------- approach-to-start for stepwise axes ----------------------
def test_stepwise_approach_from_parked_position():
    """Device parked at 0.7, stepwise sweep 0->1 in 0.25 steps: the engine
    must WALK it to the start (0.45, 0.2) before the sweep sets 0.0 — not
    jump. Exactly one set lands on the entry point; no rows during it."""
    dev = MockDevice()
    dev._values["Volt"] = 0.7
    prog = SweepProgram(
        axes=(AxisProgram(device="M1", parameter="Volt", start=0.0, stop=1.0,
                          rate=0.25, delay=0.01, count_mode=CountMode.STEP),),
        reads=())
    evs, _, _ = run_engine(prog, {"M1": dev}, timeout=25)
    vals = [round(v, 6) for (p, v, sp, _t) in dev.set_log if p == "Volt"]
    assert vals[:2] == [0.45, 0.2], f"approach steps missing: {vals}"
    assert vals[2:] == [0.0, 0.25, 0.5, 0.75, 1.0], vals
    rows = [float(e.row[1]) for e in evs if isinstance(e, ev.PointMeasured)]
    assert rows[0] == 0.0 and len(rows) == 5, \
        f"no rows during the approach: {rows}"


def test_stepwise_approach_outer_axis_2d():
    """2-D map, OUTER stepwise device parked at 3.0, outer sweep 0..2 step
    1: outer must approach (2.0, 1.0) before its first point, and the inner
    scan must not start until the outer entry point is set."""
    outer = MockDevice("M1")
    outer._values["Volt"] = 3.0
    inner = MockDevice("M2")
    prog = SweepProgram(
        axes=(AxisProgram(device="M1", parameter="Volt", start=0.0, stop=2.0,
                          rate=1.0, delay=0.01, count_mode=CountMode.STEP),
              AxisProgram(device="M2", parameter="Curr", start=0.0, stop=0.2,
                          rate=0.1, delay=0.005, count_mode=CountMode.STEP)),
        reads=(), save_maps=False)
    evs, _, _ = run_engine(prog, {"M1": outer, "M2": inner}, timeout=25)
    log = sorted(outer.set_log + inner.set_log, key=lambda e: e[3])
    outer_vals = [round(v, 6) for (p, v, sp, t) in log if p == "Volt"]
    assert outer_vals == [2.0, 1.0, 0.0, 1.0, 2.0], outer_vals
    t_first_inner = min(t for (p, v, sp, t) in log if p == "Curr")
    t_outer_entry = [t for (p, v, sp, t) in log if p == "Volt"][2]
    assert t_first_inner > t_outer_entry, \
        "inner scan started before the outer axis reached its start"


def test_stepwise_approach_skipped_when_already_at_start():
    dev = MockDevice()                       # parked at 0.0 == start
    prog = SweepProgram(
        axes=(AxisProgram(device="M1", parameter="Volt", start=0.0, stop=0.5,
                          rate=0.25, delay=0.01, count_mode=CountMode.STEP),),
        reads=())
    run_engine(prog, {"M1": dev}, timeout=25)
    vals = [round(v, 6) for (p, v, sp, _t) in dev.set_log if p == "Volt"]
    assert vals == [0.0, 0.25, 0.5], f"no approach sets expected: {vals}"


def test_stepwise_approach_within_one_step_is_direct():
    dev = MockDevice()
    dev._values["Volt"] = 0.2                # one step away from 0.0
    prog = SweepProgram(
        axes=(AxisProgram(device="M1", parameter="Volt", start=0.0, stop=0.5,
                          rate=0.25, delay=0.01, count_mode=CountMode.STEP),),
        reads=())
    run_engine(prog, {"M1": dev}, timeout=25)
    vals = [round(v, 6) for (p, v, sp, _t) in dev.set_log if p == "Volt"]
    assert vals == [0.0, 0.25, 0.5], vals


def test_stepwise_approach_forced_sweepable_carries_speed():
    dev = MockDevice(sweepable_flags=[True, False], ramp_rate=60.0)
    dev._values["Volt"] = 0.9
    prog = SweepProgram(
        axes=(AxisProgram(device="M1", parameter="Volt", start=0.0, stop=0.5,
                          rate=0.25, delay=0.01, count_mode=CountMode.STEP,
                          force_stepwise=True),),
        reads=())
    run_engine(prog, {"M1": dev}, timeout=25)
    cmds = [(round(v, 6), sp) for (p, v, sp, _t) in dev.set_log
            if p == "Volt"]
    assert cmds[:3] == [(0.65, 0.25), (0.4, 0.25), (0.15, 0.25)], \
        f"forced-sweepable approach must step AND carry the rate: {cmds}"


def test_stepwise_approach_unreadable_parameter_sets_directly():
    """A write-only parameter (not in get_options): position unknown ->
    the engine must not crash and must fall back to a direct set."""
    class WriteOnly:
        def __init__(self, adress=None):
            self.adress = adress
            self.set_options = ["Bias"]
            self.get_options = []
            self.log = []
        def set_Bias(self, value=None, speed=None):
            self.log.append(value)
    dev = WriteOnly("W1")
    prog = SweepProgram(
        axes=(AxisProgram(device="W1", parameter="Bias", start=0.0, stop=0.4,
                          rate=0.2, delay=0.005, count_mode=CountMode.STEP),),
        reads=())
    evs, _, _ = run_engine(prog, {"W1": dev}, timeout=25)
    assert dev.log == [0.0, 0.2, 0.4], dev.log
    fin = [e for e in evs if isinstance(e, ev.SweepFinished)][0]
    assert not fin.stopped


def test_stepwise_approach_respects_stop():
    dev = MockDevice()
    dev._values["Volt"] = 5.0                # long approach: 19 steps
    prog = SweepProgram(
        axes=(AxisProgram(device="M1", parameter="Volt", start=0.0, stop=1.0,
                          rate=0.25, delay=0.05, count_mode=CountMode.STEP),),
        reads=())

    def hook(live, engine, q):
        time.sleep(0.2)
        engine.stop()

    evs, _, _ = run_engine(prog, {"M1": dev}, live_hook=hook, timeout=25)
    fin = [e for e in evs if isinstance(e, ev.SweepFinished)][0]
    assert fin.stopped, "stop during the approach must end the sweep"
    assert not [e for e in evs if isinstance(e, ev.PointMeasured)]
    vals = [v for (p, v, sp, _t) in dev.set_log if p == "Volt"]
    assert 0 < len(vals) < 19, f"approach must have been interrupted: {vals}"


# ------------- snake mode: the no-teleport contract, thoroughly -----------
def _per_master(evs):
    """{master_value: [inner readings in order]} preserving event order."""
    out: dict = {}
    order = []
    for e in evs:
        if isinstance(e, ev.PointMeasured):
            m = round(float(e.axis_values[0]), 9)
            if m not in out:
                out[m] = []
                order.append(m)
            out[m].append(round(float(e.axis_values[1]), 9))
    return [(m, out[m]) for m in order]


def _assert_no_teleport(evs, max_jump, label):
    """Snake's physical contract: the inner axis NEVER jumps more than one
    step — not within a row, not across row boundaries. This is the
    invariant that catches any direction-state desync (the overnight bug
    class) regardless of which configuration triggers it."""
    inner = [float(e.axis_values[1]) for e in evs
             if isinstance(e, ev.PointMeasured)]
    for a, b in zip(inner, inner[1:]):
        assert abs(b - a) <= max_jump + 1e-9, \
            f"{label}: inner axis teleported {a} -> {b}"


def _snake_prog(inner_axis, masters=5):
    return SweepProgram(
        axes=(AxisProgram(device="M1", parameter="Volt", start=0.0,
                          stop=float(masters - 1), rate=1.0, delay=0.0,
                          count_mode=CountMode.STEP),
              inner_axis),
        reads=("M2.Volt",), save_maps=False)


def test_snake_stepwise_five_masters_alternate_and_never_jump():
    inner = AxisProgram(device="M2", parameter="Volt", start=0.0, stop=1.0,
                        rate=0.25, delay=0.005, count_mode=CountMode.STEP,
                        snake=True)
    evs, _, _ = run_engine(_snake_prog(inner), {"M1": MockDevice("M1"),
                                                "M2": MockDevice("M2")},
                           timeout=40)
    seq = _per_master(evs)
    assert len(seq) == 5
    for i, (m, vals) in enumerate(seq):
        expect = list(np.linspace(0, 1, 5))
        if i % 2 == 1:
            expect = expect[::-1]
        assert vals == [round(v, 9) for v in expect], \
            f"master {m} (row {i + 1}): {vals}"
    _assert_no_teleport(evs, 0.25, "stepwise snake")


def test_snake_continuous_five_masters_alternate_and_never_jump():
    inner = AxisProgram(device="M2", parameter="Volt", start=0.0, stop=1.0,
                        rate=8.0, delay=0.02, snake=True)
    evs, _, _ = run_engine(
        _snake_prog(inner),
        {"M1": MockDevice("M1"),
         "M2": MockDevice("M2", sweepable_flags=[True, False],
                          ramp_rate=8.0)}, timeout=60)
    seq = _per_master(evs)
    assert len(seq) == 5
    for i, (m, vals) in enumerate(seq):
        assert len(vals) >= 3, f"row {i + 1} nearly empty: {vals}"
        span = max(vals) - min(vals)
        assert span >= 0.9, f"row {i + 1} FROZEN (the reported bug " \
                            f"shape): span {span}, vals {vals[:4]}…"
        going_up = vals[-1] > vals[0]
        assert going_up == (i % 2 == 0), \
            f"row {i + 1} direction wrong: {vals[0]} -> {vals[-1]}"
    _assert_no_teleport(evs, 8.0 * 0.02 * 3, "continuous snake")


def test_snake_with_even_walks_keeps_contract():
    """walks=2 + snake: each master goes there-and-back, so every master
    re-enters FORWARD from the left — still no jumps anywhere. The old
    per-call toggle degenerated exactly here."""
    inner = AxisProgram(device="M2", parameter="Volt", start=0.0, stop=1.0,
                        rate=0.25, delay=0.005, count_mode=CountMode.STEP,
                        snake=True, walks=2)
    evs, _, _ = run_engine(_snake_prog(inner, masters=4),
                           {"M1": MockDevice("M1"), "M2": MockDevice("M2")},
                           timeout=40)
    seq = _per_master(evs)
    assert len(seq) == 4
    up = list(np.linspace(0, 1, 5))
    both = [round(v, 9) for v in up + up[::-1][1:]]
    for i, (m, vals) in enumerate(seq):
        assert vals == both, f"master row {i + 1}: {vals}"
    _assert_no_teleport(evs, 0.25, "snake walks=2")


def test_snake_with_return_sweep_implied_walks():
    """snake + back_rate (implies 2 walks): the overnight configuration
    class. Contract holds; every row covers both endpoints."""
    inner = AxisProgram(device="M2", parameter="Volt", start=0.0, stop=1.0,
                        rate=8.0, delay=0.02, back_rate=8.0, snake=True)
    evs, _, _ = run_engine(
        _snake_prog(inner, masters=4),
        {"M1": MockDevice("M1"),
         "M2": MockDevice("M2", sweepable_flags=[True, False],
                          ramp_rate=8.0)}, timeout=60)
    seq = _per_master(evs)
    assert len(seq) == 4
    for i, (m, vals) in enumerate(seq):
        assert max(vals) >= 0.999 and min(vals) <= 1e-6, \
            f"row {i + 1} missed an endpoint: {min(vals)}..{max(vals)}"
        assert max(vals) - min(vals) >= 0.9, f"row {i + 1} frozen"
    _assert_no_teleport(evs, 8.0 * 0.02 * 3, "snake+return")


def test_snake_with_three_walks_alternates_entry():
    inner = AxisProgram(device="M2", parameter="Volt", start=0.0, stop=1.0,
                        rate=0.5, delay=0.005, count_mode=CountMode.STEP,
                        snake=True, walks=3)
    evs, _, _ = run_engine(_snake_prog(inner, masters=3),
                           {"M1": MockDevice("M1"), "M2": MockDevice("M2")},
                           timeout=40)
    seq = _per_master(evs)
    up = [0.0, 0.5, 1.0]
    m1 = up + [0.5, 0.0] + [0.5, 1.0]          # F,B,F  ends right
    # master 2 enters BACKWARD; its entry point is measured because it is
    # a fresh row (new master coordinate) — only same-row continuation
    # walks skip the turn point
    m2 = [1.0, 0.5, 0.0, 0.5, 1.0, 0.5, 0.0]
    assert seq[0][1] == m1, seq[0]
    assert seq[1][1] == m2, seq[1]
    _assert_no_teleport(evs, 0.5, "snake walks=3")


def test_snake_survives_inner_fault_and_recovers_direction():
    """Field-symptom shape: the inner instrument stalls during master 3's
    walk. The walk aborts with a crucial warning — and the FOLLOWING rows
    must still obey the snake contract from wherever the device stands
    (no teleport, correct continuation), instead of desyncing."""
    eng_cls, old = _short_budgets()
    eng_cls.STALL_WARN_S, eng_cls.STALL_ABORT_S = 0.3, 0.9
    try:
        inner_dev = MockDevice("M2", sweepable_flags=[True, False],
                               ramp_rate=6.0)
        # stall_at only bites walks moving up past 0.4; row 3 enters
        # forward after row 2 ended left -> it freezes at 0.4
        calls = {"n": 0}
        orig_set = inner_dev._set
        def set_hook(p, value, speed):
            if p == "Volt":
                calls["n"] += 1
                inner_dev.stall_at = 0.4 if calls["n"] == 3 else None
            return orig_set(p, value, speed)
        inner_dev._set = set_hook
        inner = AxisProgram(device="M2", parameter="Volt", start=0.0,
                            stop=1.0, rate=6.0, delay=0.03, snake=True)
        evs, _, _ = run_engine(
            _snake_prog(inner, masters=5),
            {"M1": MockDevice("M1"), "M2": inner_dev}, timeout=60)
    finally:
        eng_cls.STALL_WARN_S, eng_cls.STALL_ABORT_S = old
    errors = [e for e in evs if isinstance(e, ev.SweepError)]
    assert any(e.crucial and "M2.Volt" in e.message for e in errors), \
        "the stall must be reported naming the instrument"
    seq = _per_master(evs)
    assert len(seq) == 5, f"all masters must still run: {len(seq)}"
    # the warn-time retry clears the transient stall: every row completes
    for i, (m, vals) in enumerate(seq):
        assert max(vals) - min(vals) >= 0.9, \
            f"row {i + 1} did not recover: {vals[:4]}"
    _assert_no_teleport(evs, 6.0 * 0.03 * 3 + 0.4, "snake with fault")


def test_snake_3d_middle_axis():
    devs = {n: MockDevice(n) for n in ("M1", "M2", "M3")}
    prog = SweepProgram(
        axes=(AxisProgram(device="M1", parameter="Volt", start=0, stop=1,
                          rate=1.0, delay=0.0, count_mode=CountMode.STEP),
              AxisProgram(device="M2", parameter="Volt", start=0, stop=1,
                          rate=0.5, delay=0.0, count_mode=CountMode.STEP,
                          snake=True),
              AxisProgram(device="M3", parameter="Curr", start=0, stop=0.2,
                          rate=0.1, delay=0.002, count_mode=CountMode.STEP)),
        reads=("M3.Curr",), save_maps=False)
    evs, _, _ = run_engine(prog, devs, timeout=60)
    middle = [round(v, 9) for (p, v, sp, t) in devs["M2"].set_log
              if p == "Volt"]
    assert middle == [0.0, 0.5, 1.0, 1.0, 0.5, 0.0], \
        f"middle snake must reverse for the second master plane: {middle}"


def test_snake_map_rows_align_by_value():
    """Committed map rows for alternating snake directions must place the
    values at the right grid cells: reading the inner axis itself, every
    cell must equal its own grid value regardless of direction."""
    d1 = MockDevice("M1")
    d2 = MockDevice("M2")
    inner = AxisProgram(device="M2", parameter="Volt", start=0.0, stop=1.0,
                        rate=0.25, delay=0.002, count_mode=CountMode.STEP,
                        snake=True)
    prog = SweepProgram(
        axes=(AxisProgram(device="M1", parameter="Volt", start=0.0, stop=3.0,
                          rate=1.0, delay=0.0, count_mode=CountMode.STEP),
              inner),
        reads=("M2.Volt",), save_maps=False)
    evs, _, _ = run_engine(prog, {"M1": d1, "M2": d2}, timeout=40)
    rows = [e for e in evs if isinstance(e, ev.MapRowCommitted)]
    assert len(rows) == 4
    for r in rows:
        vals = np.asarray(r.read_rows["M2.Volt"], dtype=float)
        grid = np.asarray(r.grid, dtype=float)
        assert np.allclose(vals, grid, atol=1e-9), \
            f"row {r.row_value}: cells misplaced: grid {grid} vals {vals}"


# ----- the overnight field symptom: flat row, then business as usual ------
def test_field_symptom_deaf_row_recovers_next_row():
    """Reproduces the reported night-scan pattern: the inner instrument
    silently ignores its ramp command for ONE row (row 3). The engine
    records the honest flat readback, warns then aborts that walk naming
    the device, the next row's approach repositions silently, and rows
    after that are normal — a single glitch costs one row, not the night."""
    eng_cls, old = _short_budgets()
    eng_cls.STALL_WARN_S, eng_cls.STALL_ABORT_S = 0.25, 0.7
    try:
        # in a healthy snake chain approaches are in-band no-ops, so set
        # call #3 on Volt is exactly row 3's sweep command — deaf there
        inner_dev = MockDevice("M2", sweepable_flags=[True, False],
                               ramp_rate=6.0,
                               fault={"param": "Volt", "kind": "deaf",
                                      "start": 3, "end": 4})
        inner = AxisProgram(device="M2", parameter="Volt", start=0.0,
                            stop=1.0, rate=6.0, delay=0.04, snake=True)
        evs, _, _ = run_engine(
            _snake_prog(inner, masters=5),
            {"M1": MockDevice("M1"), "M2": inner_dev}, timeout=60)
    finally:
        eng_cls.STALL_WARN_S, eng_cls.STALL_ABORT_S = old
    seq = _per_master(evs)
    assert len(seq) == 5
    spans = [max(v) - min(v) for _m, v in seq]
    # the WARN-TIME RETRY re-sends the lost command: the row that used to
    # stay flat for its whole duration (the overnight field map bug) now
    # COMPLETES — a lost command costs seconds, not the row
    assert all(sp >= 0.9 for sp in spans), \
        f"every row must complete thanks to the retry: spans {spans}"
    errors = [e for e in evs if isinstance(e, ev.SweepError)]
    assert any(e.crucial and "M2.Volt" in e.message
               and "re-sending" in e.message for e in errors), \
        "the retry must be logged naming the instrument"
    fin = [e for e in evs if isinstance(e, ev.SweepFinished)][0]
    assert not fin.stopped


def test_wedged_instrument_escalates_to_clean_stop():
    """Instrument stays deaf: after the SECOND consecutive aborted walk
    the sweep stops fatally naming the device — instead of burning hours
    writing a flat row per master (which is what a whole night of the
    reported symptom would have been)."""
    eng_cls, old = _short_budgets()
    eng_cls.STALL_WARN_S, eng_cls.STALL_ABORT_S = 0.25, 0.7
    try:
        inner_dev = MockDevice("M2", sweepable_flags=[True, False],
                               ramp_rate=6.0,
                               fault={"param": "Volt", "kind": "deaf",
                                      "start": 3})       # deaf forever
        inner = AxisProgram(device="M2", parameter="Volt", start=0.0,
                            stop=1.0, rate=6.0, delay=0.04, snake=True)
        t0 = time.time()
        evs, _, _ = run_engine(
            _snake_prog(inner, masters=30),
            {"M1": MockDevice("M1"), "M2": inner_dev}, timeout=60)
        wall = time.time() - t0
    finally:
        eng_cls.STALL_WARN_S, eng_cls.STALL_ABORT_S = old
    errors = [e for e in evs if isinstance(e, ev.SweepError)]
    fatals = [e for e in errors if e.fatal]
    assert fatals and fatals[0].crucial \
        and "two consecutive walks aborted" in fatals[0].message \
        and "M2.Volt" in fatals[0].message, [e.message for e in errors]
    seq = _per_master(evs)
    assert len(seq) <= 4, f"must stop early, not run 30 masters: {len(seq)}"
    assert wall < 15, f"must stop within ~2 stall budgets, took {wall:.0f} s"


# -------- the overnight field-map incident: full forensic coverage --------
def test_frozen_readback_aborts_and_map_shows_hole_not_smear():
    """The failure mode in the uploaded night file: readback pins at the
    entry endpoint. The retry can't help (command is fine, readback lies),
    the watchdog aborts — and the committed map row must show mostly NaN
    with the few real samples localised, NOT a fabricated full flat line
    (which is exactly what hid the fault in the night data)."""
    eng_cls, old = _short_budgets()
    eng_cls.STALL_WARN_S, eng_cls.STALL_ABORT_S = 0.25, 0.8
    try:
        inner_dev = MockDevice("M2", sweepable_flags=[True, False],
                               ramp_rate=6.0)
        # freeze the readback exactly for row 2 (its sweep command is the
        # 2nd Volt set in a healthy snake chain), unfreeze afterwards
        orig_set = inner_dev._set
        cnt = {"n": 0}
        def hook(pp, value, speed):
            r = orig_set(pp, value, speed)
            if pp == "Volt":
                cnt["n"] += 1
                if cnt["n"] == 2:
                    inner_dev.fault = {"param": "Volt",
                                       "kind": "freeze_read",
                                       "start": inner_dev.read_calls
                                       .get("Volt", 0) + 1}
                elif cnt["n"] == 4:
                    # NOT on 3: the warn-time retry is set #3 and must not
                    # magically unfreeze a lying readback
                    inner_dev.fault = None
                    inner_dev._frozen.clear()
            return r
        inner_dev._set = hook
        # a finer grid (0.12 steps, ~9 cells) so the 1.5-step locality
        # radius is visibly local rather than half the row
        inner = AxisProgram(device="M2", parameter="Volt", start=0.0,
                            stop=1.0, rate=6.0, delay=0.02, snake=True)
        prog = SweepProgram(
            axes=(AxisProgram(device="M1", parameter="Volt", start=0.0,
                              stop=3.0, rate=1.0, delay=0.0,
                              count_mode=CountMode.STEP),
                  inner),
            reads=("M2.Volt",), save_maps=False)
        evs, _, _ = run_engine(prog, {"M1": MockDevice("M1"),
                                      "M2": inner_dev}, timeout=60)
    finally:
        eng_cls.STALL_WARN_S, eng_cls.STALL_ABORT_S = old
    rows = [e for e in evs if isinstance(e, ev.MapRowCommitted)]
    assert len(rows) == 4
    healthy = [r for r in rows
               if np.isfinite(list(r.read_rows.values())[0]).sum()
               > 0.8 * len(r.grid)]
    broken = [r for r in rows if r not in healthy]
    assert broken, "the frozen-readback row must exist"
    for r in broken:
        vals = np.asarray(r.read_rows["M2.Volt"], dtype=float)
        finite = np.isfinite(vals)
        assert finite.sum() <= 0.35 * len(vals), \
            f"aborted row must be MOSTLY NaN (was 100% smeared before): " \
            f"{finite.sum()}/{len(vals)} filled"
        assert finite.any(), "the honestly measured cells must remain"
    errors = [e for e in evs if isinstance(e, ev.SweepError)]
    assert any("aborted" in e.message and "M2.Volt" in e.message
               for e in errors)


def test_watchdog_noise_immune_stuck_readback():
    """Gauss-level jitter on a STUCK field must not keep resetting the
    stall timer (the old progress test compared against eps*0.01 — any
    downward noise fluctuation defeated it and let a stuck row run to
    full length)."""
    eng_cls, old = _short_budgets()
    eng_cls.STALL_WARN_S, eng_cls.STALL_ABORT_S = 0.3, 0.9
    try:
        dev = MockDevice("M1", sweepable_flags=[True, False], ramp_rate=4.0,
                         stall_at=0.5, noise=0.004)
        prog = SweepProgram(
            axes=(AxisProgram(device="M1", parameter="Volt", start=0.0,
                              stop=1.0, rate=4.0, delay=0.03),),
            reads=())
        t0 = time.time()
        evs, _, _ = run_engine(prog, {"M1": dev}, timeout=30)
        wall = time.time() - t0
    finally:
        eng_cls.STALL_WARN_S, eng_cls.STALL_ABORT_S = old
    errors = [e for e in evs if isinstance(e, ev.SweepError)]
    assert any("aborted" in e.message for e in errors), \
        [e.message for e in errors]
    assert wall < 10, f"noisy-stuck must abort within budgets: {wall:.1f} s"


def test_watchdog_no_false_abort_on_noisy_healthy_ramp():
    dev = MockDevice("M1", sweepable_flags=[True, False], ramp_rate=1.5,
                     noise=0.004)
    prog = SweepProgram(
        axes=(AxisProgram(device="M1", parameter="Volt", start=0.0, stop=1.0,
                          rate=1.5, delay=0.04, walks=2),),
        reads=())
    evs, _, _ = run_engine(prog, {"M1": dev}, timeout=30)
    errors = [e for e in evs if isinstance(e, ev.SweepError)]
    assert not any("aborted" in e.message for e in errors), \
        [e.message for e in errors]
    fin = [e for e in evs if isinstance(e, ev.SweepFinished)][0]
    assert not fin.stopped


def test_night_file_scenario_replay():
    """Direct replay of the uploaded map's failure: snake field axis, a
    lost command on some backward rows. With the retry the map comes out
    complete — every committed row tracks the grid."""
    eng_cls, old = _short_budgets()
    eng_cls.STALL_WARN_S, eng_cls.STALL_ABORT_S = 0.25, 0.9
    try:
        field = MockDevice("B", sweepable_flags=[True, False],
                           ramp_rate=8.0, noise=0.002,
                           fault={"param": "Volt", "kind": "deaf",
                                  "start": 2, "end": 3})   # a backward cmd
        inner = AxisProgram(device="B", parameter="Volt", start=-1.0,
                            stop=1.0, rate=8.0, delay=0.03, snake=True)
        prog = SweepProgram(
            axes=(AxisProgram(device="T", parameter="Volt", start=0.0,
                              stop=4.0, rate=1.0, delay=0.0,
                              count_mode=CountMode.STEP),
                  inner),
            reads=("B.Volt",), save_maps=False)
        evs, _, _ = run_engine(prog, {"T": MockDevice("T"), "B": field},
                               timeout=60)
    finally:
        eng_cls.STALL_WARN_S, eng_cls.STALL_ABORT_S = old
    rows = [e for e in evs if isinstance(e, ev.MapRowCommitted)]
    assert len(rows) == 5
    for r in rows:
        vals = np.asarray(r.read_rows["B.Volt"], dtype=float)
        grid = np.asarray(r.grid, dtype=float)
        ok = np.isfinite(vals)
        assert ok.sum() > 0.8 * len(grid), \
            f"row {r.row_value} incomplete: {ok.sum()}/{len(grid)}"
        # nearest-by-value can be off by up to half a grid step (0.12)
        assert np.allclose(vals[ok], grid[ok], atol=0.15), \
            f"row {r.row_value} does not track the grid"
    fin = [e for e in evs if isinstance(e, ev.SweepFinished)][0]
    assert not fin.stopped


# --------- the night replay: full-realism snake soak on OptiCoolMock ------
from tests.mock_driver import OptiCoolMock  # noqa: E402


def _night_prog(masters, span=600.0, step=11.0, delay=0.01):
    """Scaled night program: T_finger outer (stepwise counts, sweepable
    device), Field inner snake; eps/step, latency/warn, noise/eps ratios
    match the real cryostat."""
    return SweepProgram(
        axes=(AxisProgram(device="OC", parameter="T_finger", start=3.0,
                          stop=3.0 + (masters - 1) * 1.0, rate=1.0,
                          delay=0.0, count_mode=CountMode.STEP),
              AxisProgram(device="OC", parameter="Field", start=-span,
                          stop=span, rate=step / delay, delay=delay,
                          snake=True)),
        reads=("OC.Field", "OC.T_finger"), save_maps=False)


def _run_night(masters, seed="OC::1", warn=0.06, abort=0.24, timeout=240):
    eng_cls, old = _short_budgets()
    eng_cls.STALL_WARN_S, eng_cls.STALL_ABORT_S = warn, abort
    try:
        dev = OptiCoolMock(seed)
        dev.maxspeed[0] = 400.0            # scaled fast T so the soak runs
        evs, _, _ = run_engine(_night_prog(masters), {"OC": dev},
                               timeout=timeout)
    finally:
        eng_cls.STALL_WARN_S, eng_cls.STALL_ABORT_S = old
    return evs, dev


def _row_report(evs, span=600.0):
    seq = _per_master(evs)
    flats, bad_dir = [], []
    for i, (m, vals) in enumerate(seq):
        rng = max(vals) - min(vals)
        if rng < 1.9 * span:
            flats.append((i + 1, round(rng, 1), round(vals[0], 1)))
        going_up = vals[-1] > vals[0]
        if going_up != (i % 2 == 0):
            bad_dir.append(i + 1)
    return seq, flats, bad_dir


def test_night_replay_soak_no_flat_rows():
    """THE overnight configuration, three different noise seeds: every
    row must span the full field range, alternate direction, and produce
    zero crucial/stall errors. Any flat row here = the reported bug."""
    for seed in ("OC::A", "OC::B", "OC::C"):
        evs, dev = _run_night(masters=12, seed=seed)
        seq, flats, bad_dir = _row_report(evs)
        errors = [e.message for e in evs if isinstance(e, ev.SweepError)]
        assert len(seq) == 12, f"[{seed}] masters: {len(seq)}"
        assert not flats, f"[{seed}] FLAT ROWS (the night bug!): {flats}"
        assert not bad_dir, f"[{seed}] direction broke at rows {bad_dir}"
        assert not errors, f"[{seed}] unexpected errors: {errors}"
        fin = [e for e in evs if isinstance(e, ev.SweepFinished)][0]
        assert not fin.stopped


def test_night_replay_long_soak_43_masters():
    """The full 43-row night, scaled. Zero tolerance for flat rows."""
    evs, dev = _run_night(masters=43, timeout=400)
    seq, flats, bad_dir = _row_report(evs)
    assert len(seq) == 43, len(seq)
    assert not flats, f"FLAT ROWS: {flats}"
    assert not bad_dir, f"direction: {bad_dir}"
    turn_cmds = [(v, sp) for (p, v, sp, t) in dev.set_log if p == "Field"]
    # 43 sweep commands + 1 initial approach (field starts mid-range)
    assert len(turn_cmds) == 44, \
        f"one command per row plus the first approach: {len(turn_cmds)}"
    assert all(sp == 11.0 / 0.01 for _v, sp in turn_cmds), turn_cmds[:3]


def test_night_replay_latency_beyond_warn_retry_saves_row():
    """Command-to-motion latency LONGER than the stall warn budget: the
    warn fires, the retry re-sends (restarting the mock's latency), and
    the row must still complete without an abort."""
    eng_cls, old = _short_budgets()
    eng_cls.STALL_WARN_S, eng_cls.STALL_ABORT_S = 0.06, 0.5
    try:
        dev = OptiCoolMock("OC::L")
        dev.maxspeed[0] = 400.0
        dev.LATENCY = 0.10                  # > warn budget
        evs, _, _ = run_engine(_night_prog(6), {"OC": dev}, timeout=240)
    finally:
        eng_cls.STALL_WARN_S, eng_cls.STALL_ABORT_S = old
    seq, flats, _ = _row_report(evs)
    assert len(seq) == 6 and not flats, flats
    errors = [e.message for e in evs if isinstance(e, ev.SweepError)]
    assert not any("aborted" in m for m in errors), errors


def test_night_replay_big_overshoot_across_turnarounds():
    """Overshoot comparable to eps at every arrival, settling back during
    the master step: turnarounds must stay clean."""
    dev = OptiCoolMock("OC::O")
    dev.maxspeed[0] = 400.0
    dev.OVERSHOOT = 6.0                     # > eps (5)
    eng_cls, old = _short_budgets()
    eng_cls.STALL_WARN_S, eng_cls.STALL_ABORT_S = 0.06, 0.24
    try:
        evs, _, _ = run_engine(_night_prog(8), {"OC": dev}, timeout=240)
    finally:
        eng_cls.STALL_WARN_S, eng_cls.STALL_ABORT_S = old
    seq, flats, bad_dir = _row_report(evs)
    assert len(seq) == 8 and not flats and not bad_dir, (flats, bad_dir)


# ------- commit-boundary integrity + full-stack (renderer ON) replay ------
def test_map_commit_boundary_never_slides():
    """Every committed row must be built EXCLUSIVELY from its own
    master's samples. The read tags each sample with master*10000+inner,
    so a single stolen or leaked sample across a row boundary changes the
    tag and fails loudly. (The overnight worksheet's flat rows were the
    next scan's first 1-2 samples flushed under the previous boundary —
    a mixed-module state this test would catch in any build.)"""
    class Tagger(MockDevice):
        def __init__(self, adress=None):
            super().__init__(adress, sweepable_flags=[False, False])
        def Curr(self):
            return self._values["Volt"] * 1.0   # inner echo

    outer = MockDevice("M1")
    inner = MockDevice("M2", sweepable_flags=[True, False], ramp_rate=40.0)

    class Tag:
        def __init__(self, adress=None):
            self.adress = adress
            self.set_options = []
            self.get_options = ["tag"]
        def tag(self):
            return outer._values["Volt"] * 10000 + inner._values["Volt"]

    prog = SweepProgram(
        axes=(AxisProgram(device="M1", parameter="Volt", start=0.0, stop=5.0,
                          rate=1.0, delay=0.0, count_mode=CountMode.STEP),
              AxisProgram(device="M2", parameter="Volt", start=0.0, stop=1.0,
                          rate=40.0, delay=0.01, snake=True)),
        reads=("TAG.tag",), save_maps=False)
    evs, _, _ = run_engine(prog, {"M1": outer, "M2": inner,
                                  "TAG": Tag("TAG")}, timeout=60)
    rows = [e for e in evs if isinstance(e, ev.MapRowCommitted)]
    assert len(rows) == 6
    for r in rows:
        vals = np.asarray(r.read_rows["TAG.tag"], dtype=float)
        fin = vals[np.isfinite(vals)]
        masters = np.unique(np.round(fin // 10000))
        assert list(masters) == [round(r.row_value)], \
            f"row {r.row_value}: contains samples from masters " \
            f"{masters} — COMMIT BOUNDARY SLID"


def test_night_replay_full_stack_files_and_renderer():
    """The one combination the soak lacked: write_files=True with the
    background PNG renderer running — the night's real configuration.
    The TABLE FILE on disk is read back and every line must span the
    full field range (a flat line on disk = the reported bug)."""
    eng_cls, old = _short_budgets()
    eng_cls.STALL_WARN_S, eng_cls.STALL_ABORT_S = 0.06, 0.24
    try:
        dev = OptiCoolMock("OC::F")
        dev.maxspeed[0] = 400.0
        prog = SweepProgram(
            axes=(AxisProgram(device="OC", parameter="T_finger", start=3.0,
                              stop=10.0, rate=1.0, delay=0.0,
                              count_mode=CountMode.STEP),
                  AxisProgram(device="OC", parameter="Field", start=-600.0,
                              stop=600.0, rate=1100.0, delay=0.01,
                              snake=True)),
            reads=("OC.Field",), save_maps=True, map_images=True,
            map_style="both")
        evs, _, tmp = run_engine(prog, {"OC": dev}, timeout=300)
    finally:
        eng_cls.STALL_WARN_S, eng_cls.STALL_ABORT_S = old
    tables = _find_map_tables(tmp)
    assert tables, "the worksheet must exist on disk"
    lines = open(tables[0]).read().splitlines()
    grid = np.array([float(x) for x in lines[0].split(",")[1:]])
    assert len(lines) - 1 == 8, f"8 map lines expected: {len(lines) - 1}"
    for li, ln in enumerate(lines[1:], 1):
        vals = np.array([float(x) if x != "nan" else np.nan
                         for x in ln.split(",")[1:]])
        fin = vals[np.isfinite(vals)]
        span = fin.max() - fin.min()
        assert span > 0.9 * (grid.max() - grid.min()), \
            f"DISK line {li} is flat (span {span:.0f}) — the night bug"
        distinct = len(np.unique(np.round(fin, 1)))
        assert distinct > 50, f"line {li}: only {distinct} distinct values"
    fin_ev = [e for e in evs if isinstance(e, ev.SweepFinished)][0]
    assert not fin_ev.stopped
    xyz = _find_xyz(tmp)
    assert xyz, "style='both' must also produce the xyz file"


# --------------- v1 'Start warning': pre-flight + No-branch ---------------
def test_check_start_positions_detects_offsets():
    from unisweep.core.engine import check_start_positions

    class Reg:
        def __init__(self, devs): self.devs = devs
        def connect(self, a): return self.devs[a]
    from unisweep.core.devices import DriverAdapter
    parked = MockDevice("P"); parked._values["Volt"] = 0.7
    parked.eps = [0.05, 1e-6]
    at_start = MockDevice("A")                       # Volt = 0.0
    within = MockDevice("W"); within._values["Volt"] = 0.03
    within.eps = [0.05, 1e-6]
    reg = Reg({d.adress: DriverAdapter(d.adress, d)
               for d in (parked, at_start, within)})
    prog = SweepProgram(
        axes=(AxisProgram(device="P", parameter="Volt", start=0.0, stop=1.0,
                          rate=0.1, delay=0.01, count_mode=CountMode.STEP),
              AxisProgram(device="A", parameter="Volt", start=0.0, stop=1.0,
                          rate=0.1, delay=0.01, count_mode=CountMode.STEP)),
        reads=())
    out = check_start_positions(reg, prog)
    assert len(out) == 1 and out[0]["device"] == "P" \
        and abs(out[0]["current"] - 0.7) < 1e-9 \
        and out[0]["eps"] == 0.05, out
    # within eps -> clean; write-only parameter -> skipped silently
    prog2 = SweepProgram(
        axes=(AxisProgram(device="W", parameter="Volt", start=0.0, stop=1.0,
                          rate=0.1, delay=0.01, count_mode=CountMode.STEP),),
        reads=())
    assert check_start_positions(reg, prog2) == []

    class WriteOnly:
        def __init__(self, adress=None):
            self.adress = adress
            self.set_options = ["Bias"]; self.get_options = []
        def set_Bias(self, value=None, speed=None): pass
    reg2 = Reg({"WO": DriverAdapter("WO", WriteOnly("WO"))})
    prog3 = SweepProgram(
        axes=(AxisProgram(device="WO", parameter="Bias", start=0.0,
                          stop=1.0, rate=0.5, delay=0.01,
                          count_mode=CountMode.STEP),),
        reads=())
    assert check_start_positions(reg2, prog3) == []


def test_approach_start_false_starts_from_current():
    """The dialog's 'No': stepwise device parked at 0.7 gets NO gradual
    approach — the first grid point is set directly (v1's jump); a
    sweepable one ramps straight for the stop from where it stands,
    recording from the current value."""
    dev = MockDevice()
    dev._values["Volt"] = 0.7
    prog = SweepProgram(
        axes=(AxisProgram(device="M1", parameter="Volt", start=0.0, stop=1.0,
                          rate=0.25, delay=0.01, count_mode=CountMode.STEP),),
        reads=(), approach_start=False)
    run_engine(prog, {"M1": dev}, timeout=25)
    vals = [round(v, 6) for (p, v, sp, _t) in dev.set_log if p == "Volt"]
    assert vals == [0.0, 0.25, 0.5, 0.75, 1.0], \
        f"no approach steps expected before the grid: {vals}"

    swp = MockDevice(sweepable_flags=[True, False], ramp_rate=30.0)
    swp._values["Volt"] = 0.7
    prog2 = SweepProgram(
        axes=(AxisProgram(device="M1", parameter="Volt", start=0.0, stop=1.0,
                          rate=20.0, delay=0.02),),
        reads=(), approach_start=False)
    evs, _, _ = run_engine(prog2, {"M1": swp}, timeout=25)
    cmds = [(v, sp) for (p, v, sp, _t) in swp.set_log if p == "Volt"]
    assert cmds[0] == (1.0, 20.0), \
        f"first command must be the sweep target, no approach: {cmds}"
    rows = [float(e.row[1]) for e in evs if isinstance(e, ev.PointMeasured)]
    assert abs(rows[0] - 0.7) < 0.05, \
        f"recording must begin at the current value: {rows[:3]}"


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


# ---------------------------------------------------------------------------
# Nested-loop returns, parallel approach, walk numbering, image restyling and
# filename parsing.
#
# The behaviour these cover already shipped (commits "Multiple bugs fixed —
# core 3D sweep return logic..." and "Graph and maps windows are floating
# atop"); the tests themselves were written alongside it and never committed.
# Recovered so the features have the regression cover they were given.
# ---------------------------------------------------------------------------
def test_return_moves_slave_and_inner_together():
    """The mid-sweep return repositions slave AND the finished inner
    axis simultaneously (inner not snake): interleaved timestamps."""
    devs = {"MA": MockDevice("MA"),
            "SL": MockDevice("SL"),
            "SS": MockDevice("SS")}
    prog = SweepProgram(
        axes=(AxisProgram(device="MA", parameter="Volt", start=0, stop=1,
                          rate=1.0, delay=0.0, count_mode=CountMode.STEP),
              AxisProgram(device="SL", parameter="Volt", start=0, stop=0.3,
                          rate=0.1, delay=0.02, count_mode=CountMode.STEP),
              AxisProgram(device="SS", parameter="Curr", start=0, stop=0.3,
                          rate=0.1, delay=0.02,
                          count_mode=CountMode.STEP)),
        reads=("SS.Curr",), save_maps=False)
    evs, _, _ = run_engine(prog, devs, timeout=90)
    rets = [e for e in evs if isinstance(e, ev.ApproachStarted)
            and e.phase == "return"]
    assert rets, "return phases must be announced"
    assert {t[1] for t in rets[0].targets} == {"SL", "SS"}, \
        f"slave and inner return together: {rets[0].targets}"

def test_return_uses_back_params_and_rate():
    """back_rate/back_delay on the slave = the return's step and speed."""
    devs = {"MA": MockDevice("MA"),
            "SL": MockDevice("SL", sweepable_flags=[True, False],
                             ramp_rate=50.0),
            "SS": MockDevice("SS")}
    prog = SweepProgram(
        axes=(AxisProgram(device="MA", parameter="Volt", start=0, stop=1,
                          rate=1.0, delay=0.0, count_mode=CountMode.STEP),
              AxisProgram(device="SL", parameter="Volt", start=0, stop=0.4,
                          rate=0.2, delay=0.0, count_mode=CountMode.STEP,
                          force_stepwise=True, back_rate=0.4,
                          back_delay=0.001),
              AxisProgram(device="SS", parameter="Curr", start=0, stop=0.1,
                          rate=0.1, delay=0.002, count_mode=CountMode.STEP)),
        reads=("SS.Curr",), save_maps=False)
    run_engine(prog, devs, timeout=60)
    sl = [(round(v, 6), sp) for (p, v, sp, t) in devs["SL"].set_log]
    # forward pass 0, .2, .4 — then the return: with back step 0.4 the
    # whole way back is ONE stroke, commanded at the BACK rate
    assert sl[:4] == [(0.0, None), (0.2, None), (0.4, None), (0.0, 0.4)], \
        f"return must use the BACK step and back rate: {sl}"

def test_snake_slave_does_not_return():
    devs = {n: MockDevice(n) for n in ("MA", "SL", "SS")}
    prog = SweepProgram(
        axes=(AxisProgram(device="MA", parameter="Volt", start=0, stop=1,
                          rate=1.0, delay=0.0, count_mode=CountMode.STEP),
              AxisProgram(device="SL", parameter="Volt", start=0, stop=0.4,
                          rate=0.2, delay=0.0, count_mode=CountMode.STEP,
                          snake=True),
              AxisProgram(device="SS", parameter="Curr", start=0, stop=0.1,
                          rate=0.05, delay=0.002,
                          count_mode=CountMode.STEP)),
        reads=("SS.Curr",), save_maps=False)
    run_engine(prog, devs, timeout=60)
    sl = [round(v, 6) for (p, v, sp, t) in devs["SL"].set_log]
    assert sl == [0.0, 0.2, 0.4, 0.4, 0.2, 0.0], \
        f"snake slave reverses for master 2, no repositioning return: {sl}"

def test_3d_slave_returns_stepwise_before_master_steps():
    """slave-slave walks back&forth per slave point; slave then RETURNS
    to its start (its own steps, nothing swept below) BEFORE master
    steps; master never returns."""
    devs = {n: MockDevice(n) for n in ("MA", "SL", "SS")}
    prog = SweepProgram(
        axes=(AxisProgram(device="MA", parameter="Volt", start=0, stop=1,
                          rate=1.0, delay=0.0, count_mode=CountMode.STEP),
              AxisProgram(device="SL", parameter="Volt", start=0, stop=0.4,
                          rate=0.2, delay=0.0, count_mode=CountMode.STEP),
              AxisProgram(device="SS", parameter="Curr", start=0, stop=0.2,
                          rate=0.1, delay=0.002, count_mode=CountMode.STEP,
                          walks=2)),
        reads=("SS.Curr",), save_maps=False)
    evs, _, _ = run_engine(prog, devs, timeout=60)
    log = sorted([(t, d, v) for d in devs
                  for (p, v, sp, t) in devs[d].set_log], key=lambda e: e[0])
    seq = [(d, round(v, 6)) for (t, d, v) in log]
    # slave return: after the last slave point (0.4), 0.2 then 0.0 appear
    # BEFORE the second master set
    i_master2 = seq.index(("MA", 1.0))
    before = seq[:i_master2]
    tail = [e for e in before if e[0] == "SL"]
    assert tail[-3:] == [("SL", 0.4), ("SL", 0.2), ("SL", 0.0)], \
        f"slave must walk back to start before master steps: {tail}"
    # nothing swept below during the return: between SL 0.2(return) and
    # MA 1.0 there must be no SS sets
    i_ret = len(before) - 1 - before[::-1].index(("SL", 0.2))
    between = [e for e in seq[i_ret:i_master2] if e[0] == "SS"]
    assert between == [], f"slave-slave must NOT sweep during the " \
                          f"return: {between}"
    # master never returns: last MA set is its final point
    ma = [v for (d, v) in seq if d == "MA"]
    assert ma == [0.0, 1.0], f"master steps only forward: {ma}"
    # and after everything, no MA set back to 0
    assert seq[-1][0] != "MA" or seq[-1][1] == 1.0

def test_2d_outer_single_pass_even_with_walks_configured():
    """2D: master makes exactly ONE forward pass — configured walks on a
    non-innermost axis no longer replay the whole nested loop."""
    devs = {"MA": MockDevice("MA"), "IN": MockDevice("IN")}
    prog = SweepProgram(
        axes=(AxisProgram(device="MA", parameter="Volt", start=0, stop=1,
                          rate=0.5, delay=0.0, count_mode=CountMode.STEP,
                          walks=2),
              AxisProgram(device="IN", parameter="Curr", start=0, stop=0.1,
                          rate=0.05, delay=0.002,
                          count_mode=CountMode.STEP)),
        reads=("IN.Curr",), save_maps=False)
    run_engine(prog, devs, timeout=60)
    ma = [round(v, 6) for (p, v, sp, t) in devs["MA"].set_log]
    assert ma == [0.0, 0.5, 1.0], \
        f"one forward pass, no measured backward walk, no return: {ma}"

def test_parallel_approach_moves_instruments_at_once():
    """Two stepwise axes parked away from start: their approach steps
    must INTERLEAVE in time (parallel), not run one axis after the
    other; ApproachStarted/Finished bracket the phase."""
    d1 = MockDevice("A1"); d1._values["Volt"] = 0.5
    d2 = MockDevice("A2"); d2._values["Curr"] = 0.25
    prog = SweepProgram(
        axes=(AxisProgram(device="A1", parameter="Volt", start=0, stop=0.6,
                          rate=0.1, delay=0.03, count_mode=CountMode.STEP),
              AxisProgram(device="A2", parameter="Curr", start=0, stop=0.3,
                          rate=0.05, delay=0.03,
                          count_mode=CountMode.STEP)),
        reads=("A2.Curr",), save_maps=False)
    evs, _, _ = run_engine(prog, {"A1": d1, "A2": d2}, timeout=60)
    starts = [e for e in evs if isinstance(e, ev.ApproachStarted)]
    fins = [e for e in evs if isinstance(e, ev.ApproachFinished)]
    assert starts and fins
    assert {t[1] for t in starts[0].targets} == {"A1", "A2"}
    a1 = [t for (p, v, sp, t) in d1.set_log if v < 0.49]
    a2 = [t for (p, v, sp, t) in d2.set_log if v < 0.24]
    assert a1 and a2
    assert a1[0] < a2[-1] and a2[0] < a1[-1], \
        "approach steps of the two instruments must interleave in time"

def test_point_measured_carries_walk_number():
    dev = MockDevice("M1")
    prog = SweepProgram(
        axes=(AxisProgram(device="M1", parameter="Volt", start=0, stop=0.5,
                          rate=0.25, delay=0.005, count_mode=CountMode.STEP,
                          walks=2),),
        reads=())
    evs, _, _ = run_engine(prog, {"M1": dev}, timeout=25)
    walks = [e.walk for e in evs if isinstance(e, ev.PointMeasured)]
    assert walks == [1, 1, 1, 2, 2], walks

def test_restyle_saved_images_rerenders_png():
    """Applying plot settings to saved files: the PNG is re-rendered
    from its table with the new limits/labels/title."""
    import tempfile
    from unisweep.core.maps import restyle_saved_images
    data_dir = tempfile.mkdtemp()
    tdir = os.path.join(data_dir, "2d_maps", "tables", "run_1")
    os.makedirs(tdir)
    table = os.path.join(tdir, "run_M2.Curr_map_1.csv")
    with open(table, "w") as fh:
        fh.write("T / V,0.0,0.5,1.0\n")
        fh.write("1.0,0.1,0.2,0.3\n")
        fh.write("2.0,0.2,0.4,0.6\n")
    n = restyle_saved_images(data_dir, "M2.Curr", vmin=0.0, vmax=1.0,
                             labels={"x": "V (V)", "y": "T (K)"},
                             title="restyled")
    assert n == 1, n
    png = os.path.join(data_dir, "2d_maps", "images", "run_1",
                       "run_M2.Curr_map_1.png")
    assert os.path.exists(png) and os.path.getsize(png) > 5000
    size1 = os.path.getsize(png)
    n = restyle_saved_images(data_dir, "M2.Curr", vmin=0.0, vmax=0.2,
                             labels={}, title="clipped")
    assert n == 1 and os.path.getsize(png) != size1, \
        "new style must actually change the rendered file"

def test_filename_folder_name_and_extension_logic():
    import datetime
    import tempfile
    from unisweep.core.writer import DataWriter
    ymd = datetime.datetime.today().strftime("%y%m%d")
    core = tempfile.mkdtemp()

    def run(filename):
        w = DataWriter(core, ["a"], filename)
        p = w.open_file()
        w.write((1,))
        w.close()
        return p

    assert run("") == os.path.join(core, ymd, "data_files",
                                   f"{ymd}-1.csv")
    fold = tempfile.mkdtemp()          # folder only -> dated inside it
    assert run(fold) == os.path.join(fold, ymd, "data_files",
                                     f"{ymd}-1.csv")
    par = tempfile.mkdtemp()           # full name -> dated in the parent
    assert run(os.path.join(par, "myscan")) == \
        os.path.join(par, ymd, "data_files", "myscan-1.csv")
    p = run(os.path.join(par, "raw.dat"))     # deliberate extension kept
    assert p.endswith(os.path.join(ymd, "data_files", "raw-1.dat")), p
    assert run("gatecheck") == os.path.join(   # bare name -> core dated
        core, ymd, "data_files", "gatecheck-1.csv")


def test_restyle_applies_the_colormap_and_transform_to_saved_images():
    """'Apply the plot window's settings to the saved files' means ALL of
    them. The colormap and the z-transform are settings, and a saved
    image that ignored them was the bug behind "I applied the settings
    and the colours did not change" — the limits, labels and title were
    re-applied, the colormap was hardcoded to viridis.

    Written against the PIXELS. The test above checks that the byte count
    moves when the LIMITS change, which stayed green for as long as the
    colormap never reached the renderer at all.
    """
    import tempfile
    import matplotlib
    matplotlib.use("Agg", force=False)
    import matplotlib.image as mpimg
    from unisweep.core.maps import restyle_saved_images

    data_dir = tempfile.mkdtemp()
    tdir = os.path.join(data_dir, "2d_maps", "tables", "run_1")
    os.makedirs(tdir)
    with open(os.path.join(tdir, "run_M2.Curr_map_1.csv"), "w") as fh:
        fh.write("T / V,0.0,0.5,1.0\n")
        fh.write("1.0,0.1,0.2,0.3\n")
        fh.write("2.0,0.2,0.4,0.6\n")
    png = os.path.join(data_dir, "2d_maps", "images", "run_1",
                       "run_M2.Curr_map_1.png")

    def render(**style):
        assert restyle_saved_images(data_dir, "M2.Curr", **style) == 1
        return mpimg.imread(png).copy()

    # the same style twice must give the same pixels, or every comparison
    # below would be satisfied by rendering noise alone
    plain = render(cmap="viridis")
    assert np.array_equal(plain, render(cmap="viridis"))

    assert not np.array_equal(plain, render(cmap="magma")), \
        "the colormap must reach the saved PNG"
    assert not np.array_equal(plain, render(cmap="viridis",
                                            ztransform="v ** 2")), \
        "the z-transform must reach the saved PNG"
