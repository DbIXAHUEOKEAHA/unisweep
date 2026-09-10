"""A read that returns a whole trace, through the whole application.

The rule under test is one sentence: the trace becomes the innermost
axis and every sweep axis shifts out by one. A 1-D sweep of traces is a
map; a 2-D sweep of traces is the set of maps a 3-D sweep of numbers
produces; a 3-D sweep of traces is one level past anything the screen can
draw, so it is written and not shown.
"""

import os
import queue
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest

from unisweep.core import events as ev
from unisweep.core.config import (AxisProgram, CountMode, LiveProgram,
                                  SweepProgram)
from unisweep.core.engine import SweepEngine
from unisweep.core.vector import as_vector
from tests.test_engine import FakeRegistry


N = 5                      # points in a trace: small, so the maps are legible


class VNA:
    """Returns a whole trace per point, the way a network analyser does."""

    def __init__(self, address="VNA", length=N, axis=True, as_text=False):
        self.set_options = ["Power"]
        self.get_options = ["Trace", "Level"]
        self.length = length
        self.as_text = as_text
        self._power = 0.0
        self.calls = 0
        if axis:
            self.Trace_axis = lambda: [1e9 + 1e8 * i
                                       for i in range(self.length)]

    def set_Power(self, value=None, speed=None):
        self._power = float(value)

    def Power(self):
        return self._power

    def Level(self):                       # an ordinary scalar read
        return self._power * 2.0

    def Trace(self):
        self.calls += 1
        trace = [self._power + 0.1 * i for i in range(self.length)]
        return ",".join(f"{v:g}" for v in trace) if self.as_text \
            else np.array(trace)


class Knob:
    def __init__(self, address="K"):
        self.set_options = ["Volt"]
        self.get_options = ["Volt"]
        self._v = 0.0

    def set_Volt(self, value=None, speed=None):
        self._v = float(value)

    def Volt(self):
        return self._v


def axis(device, start, stop, step=1.0):
    return AxisProgram(device=device, parameter="Volt" if device != "VNA"
                       else "Power", start=start, stop=stop, rate=step,
                       delay=0.001, count_mode=CountMode.STEP)


def run(tmp, program, mocks, timeout=120):
    engine = SweepEngine(LiveProgram(program), FakeRegistry(tmp, mocks),
                         tmp, queue.Queue())
    events = []
    engine.q = engine.q          # the queue the engine drains into
    engine.start()
    engine.join(timeout)
    assert not engine.is_alive(), "the engine did not finish"
    while not engine.q.empty():
        events.append(engine.q.get_nowait())
    return engine, events


def tables(tmp):
    out = []
    for root, _dirs, names in os.walk(tmp):
        for name in names:
            if name.endswith(".csv") and "tables" in root:
                out.append(os.path.join(root, name))
    return sorted(out)


def read_table(path):
    lines = [l for l in open(path, encoding="utf-8").read().splitlines()
             if l.strip()]
    header = lines[0].split(",")
    grid = np.array([float(v) for v in header[1:]])
    labels, rows = [], []
    for line in lines[1:]:
        parts = line.split(",")
        labels.append(float(parts[0]))
        rows.append([float(v) if v != "nan" else np.nan
                     for v in parts[1:]])
    return header[0], grid, np.array(labels), np.array(rows)


# ---------------------------------------------------------------------------
# 1-D: a sweep of traces IS a map
# ---------------------------------------------------------------------------
def test_a_1d_sweep_of_traces_is_a_map(tmp_path):
    tmp = str(tmp_path)
    engine, events = run(tmp, SweepProgram(
        axes=(axis("VNA", 0.0, 3.0),), reads=("VNA.Trace",),
        save_maps=True, map_images=False), {"VNA": VNA()})

    found = tables(tmp)
    assert len(found) == 1, found
    head, grid, labels, rows = read_table(found[0])

    assert rows.shape == (4, N), "one row per swept point, one column per bin"
    assert np.allclose(grid, [1e9 + 1e8 * i for i in range(N)]), \
        "the instrument's own x axis, not an index"
    assert np.allclose(labels, [0, 1, 2, 3]), "rows are labelled by the sweep"
    assert np.allclose(rows[2], [2 + 0.1 * i for i in range(N)])
    assert "VNA.Power" in head and "axis" in head


def test_the_row_file_keeps_the_comma_form_it_always_had(tmp_path):
    """One cell per read, still. Every script pointed at these files
    reads them unchanged, and the numbers are recoverable from the cell."""
    import csv
    tmp = str(tmp_path)
    engine, _ = run(tmp, SweepProgram(
        axes=(axis("VNA", 0.0, 1.0),), reads=("VNA.Trace", "VNA.Level"),
        save_maps=False, map_images=False), {"VNA": VNA()})

    path = engine.provenance.files[0]
    with open(path, encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    assert rows[0] == ["time", "VNA.Power_sweep", "VNA.Trace", "VNA.Level"]
    cell = rows[1][2]
    assert "," in cell, "the trace is one cell of comma-separated numbers"
    assert np.allclose(as_vector(cell), [0 + 0.1 * i for i in range(N)])
    assert float(rows[1][3]) == 0.0, "an ordinary read is untouched"


def test_a_driver_can_hand_over_the_numbers_or_the_old_string(tmp_path):
    """The point of the exercise: no parsing needed. Both are understood
    and produce the same map."""
    made = {}
    for as_text in (False, True):
        tmp = str(tmp_path / f"t{int(as_text)}")
        os.makedirs(tmp)
        run(tmp, SweepProgram(axes=(axis("VNA", 0.0, 2.0),),
                              reads=("VNA.Trace",), save_maps=True,
                              map_images=False),
            {"VNA": VNA(as_text=as_text)})
        made[as_text] = read_table(tables(tmp)[0])[3]
    assert np.allclose(made[False], made[True])


def test_without_a_reporting_driver_the_axis_is_the_index(tmp_path):
    tmp = str(tmp_path)
    run(tmp, SweepProgram(axes=(axis("VNA", 0.0, 1.0),),
                          reads=("VNA.Trace",), save_maps=True,
                          map_images=False),
        {"VNA": VNA(axis=False)})
    _head, grid, _labels, _rows = read_table(tables(tmp)[0])
    assert np.allclose(grid, np.arange(N))


# ---------------------------------------------------------------------------
# 2-D: a set of maps, one per master point
# ---------------------------------------------------------------------------
def test_a_2d_sweep_of_traces_is_a_set_of_maps(tmp_path):
    tmp = str(tmp_path)
    engine, events = run(tmp, SweepProgram(
        axes=(axis("K", 0.0, 2.0), axis("VNA", 0.0, 1.0)),
        reads=("VNA.Trace",), save_maps=True, map_images=False),
        {"K": Knob(), "VNA": VNA()})

    found = tables(tmp)
    assert len(found) == 3, f"one map per master point: {found}"
    for i, path in enumerate(found):
        folder = os.path.basename(os.path.dirname(path))
        assert folder.startswith("K.Volt_"), folder
        assert os.path.basename(path).endswith(f"_map_{i}.csv"), path
        _head, grid, labels, rows = read_table(path)
        assert rows.shape == (2, N)
        assert np.allclose(labels, [0, 1]), "rows are the inner sweep"
        assert len(grid) == N

    # …and the GUI is fed the same rows, so the plot window's existing
    # set-of-maps toggle draws it with nothing new added
    committed = [e for e in events if isinstance(e, ev.MapRowCommitted)]
    assert len(committed) == 6
    assert {e.iteration for e in committed} == {0, 1, 2}
    assert all("VNA.Trace" in e.read_rows for e in committed)
    assert len(committed[0].grid) == N


def test_an_ordinary_read_beside_a_trace_is_untouched(tmp_path):
    tmp = str(tmp_path)
    run(tmp, SweepProgram(
        axes=(axis("K", 0.0, 1.0), axis("VNA", 0.0, 1.0)),
        reads=("VNA.Trace", "VNA.Level"), save_maps=True,
        map_images=False), {"K": Knob(), "VNA": VNA()})

    found = tables(tmp)
    level = [p for p in found if "Level" in p]
    trace = [p for p in found if "Trace" in p]
    assert len(level) == 1, "the scalar read keeps its ordinary 2-D map"
    assert len(trace) == 2, "the trace gets one map per master point"
    _h, grid, labels, rows = read_table(level[0])
    assert rows.shape == (2, 2), "sweep axes both, as before"


# ---------------------------------------------------------------------------
# 3-D: past the screen, not past the disk
# ---------------------------------------------------------------------------
def test_a_3d_sweep_of_traces_nests_one_level_deeper(tmp_path):
    tmp = str(tmp_path)
    engine, events = run(tmp, SweepProgram(
        axes=(axis("K", 0.0, 1.0), axis("K2", 0.0, 1.0),
              axis("VNA", 0.0, 1.0)),
        reads=("VNA.Trace",), save_maps=True, map_images=False),
        {"K": Knob(), "K2": Knob(), "VNA": VNA()}, timeout=180)

    found = [p for p in tables(tmp) if "Trace" in p]
    assert len(found) == 4, f"one per (master, slave) pair: {found}"
    assert not any(os.path.basename(p).count("_") == 3 for p in found), \
        "the first-element fallback is a picture, not a second set of files"
    for path in found:
        slave_dir = os.path.dirname(path)
        master_dir = os.path.dirname(slave_dir)
        assert os.path.basename(slave_dir).startswith("K2.Volt_")
        assert os.path.basename(master_dir).startswith("K.Volt_")
        name = os.path.basename(path)
        assert name.count("_map_") == 1
        indices = name.rsplit("_map_", 1)[1][:-4].split("_")
        assert len(indices) == 2, f"an index per level: {name}"
        _h, grid, labels, rows = read_table(path)
        assert rows.shape == (2, N)

    # the screen is not asked to draw a fourth dimension
    committed = [e for e in events if isinstance(e, ev.MapRowCommitted)]
    assert all(len(e.grid) != N or "VNA.Trace" not in e.read_rows
               for e in committed), \
        "a 3-D sweep must not stream promoted maps to the GUI"


def test_in_3d_the_screen_falls_back_to_the_first_element(tmp_path):
    """The ordinary 3-D map for that read still exists — drawn from the
    first point of each trace, which is what was asked for."""
    tmp = str(tmp_path)
    engine, events = run(tmp, SweepProgram(
        axes=(axis("K", 0.0, 1.0), axis("K2", 0.0, 1.0),
              axis("VNA", 0.0, 1.0)),
        reads=("VNA.Trace",), save_maps=True, map_images=False),
        {"K": Knob(), "K2": Knob(), "VNA": VNA()}, timeout=180)

    committed = [e for e in events if isinstance(e, ev.MapRowCommitted)]
    assert committed, "the scalar 3-D map is still built"
    row = committed[0].read_rows["VNA.Trace"]
    assert len(row) == 2, "its columns are the inner SWEEP axis"
    assert np.allclose(row, [0.0, 1.0]), "the first element of each trace"


# ---------------------------------------------------------------------------
# the awkward cases
# ---------------------------------------------------------------------------
def test_a_trace_that_changes_length_is_fitted_and_reported(tmp_path):
    """Someone retunes the span at 3 a.m. The night survives it."""
    tmp = str(tmp_path)

    class Shrinking(VNA):
        def Trace(self):
            self.calls += 1
            n = self.length if self.calls < 3 else self.length - 2
            return np.array([self._power + 0.1 * i for i in range(n)])

    engine, events = run(tmp, SweepProgram(
        axes=(axis("VNA", 0.0, 3.0),), reads=("VNA.Trace",),
        save_maps=True, map_images=False), {"VNA": Shrinking()})

    _h, grid, labels, rows = read_table(tables(tmp)[0])
    assert rows.shape == (4, N), "the run keeps the width it started with"
    assert np.isnan(rows[-1][-1]), "the missing tail is visibly missing"
    assert not np.isnan(rows[0][-1])
    warnings = [e for e in events if isinstance(e, ev.SweepError)
                and "changed length" in e.message]
    assert len(warnings) == 1, "said once, not once per point"


def test_the_profile_can_insist_a_reading_is_not_a_trace(tmp_path):
    from unisweep.core.labprofile import LabProfile
    tmp = str(tmp_path)
    profile = LabProfile.from_dict({
        "devices": {"VNA": {"parameters": {"Trace": {"vector": False}}}}})
    engine = SweepEngine(
        LiveProgram(SweepProgram(axes=(axis("VNA", 0.0, 1.0),),
                                 reads=("VNA.Trace",), save_maps=True,
                                 map_images=False)),
        FakeRegistry(tmp, {"VNA": VNA()}), tmp, queue.Queue(),
        profile=profile)
    engine.start()
    engine.join(60)
    assert not tables(tmp), "no promoted maps for a read declared scalar"


def test_the_xyz_form_carries_the_trace_axis_as_a_coordinate(tmp_path):
    tmp = str(tmp_path)
    run(tmp, SweepProgram(axes=(axis("VNA", 0.0, 1.0),),
                          reads=("VNA.Trace",), save_maps=True,
                          map_style="xyz", map_images=False),
        {"VNA": VNA()})
    xyz = [os.path.join(r, n) for r, _d, ns in os.walk(tmp) for n in ns
           if os.path.basename(r) == "xyz" and n.endswith(".csv")]
    assert len(xyz) == 1, xyz
    lines = [l for l in open(xyz[0], encoding="utf-8").read().splitlines()
             if l.strip()]
    assert lines[0].split(",") == ["VNA.Power", "axis", "VNA.Trace"]
    assert len(lines) - 1 == 2 * N, "a line per point of every trace"
    assert lines[1].split(",")[1] == "1e+09"


def test_maps_turned_off_means_no_promoted_files_either(tmp_path):
    tmp = str(tmp_path)
    engine, _ = run(tmp, SweepProgram(
        axes=(axis("VNA", 0.0, 1.0),), reads=("VNA.Trace",),
        save_maps=False, map_images=False), {"VNA": VNA()})
    assert not tables(tmp)
    assert engine.provenance.files, "the row file is still written"


def test_the_promoted_maps_get_pictures_like_any_other(tmp_path):
    """A map is a map: the same renderer, the same images tree, the same
    folder shape mirrored from tables/ to images/."""
    tmp = str(tmp_path)
    run(tmp, SweepProgram(
        axes=(axis("K", 0.0, 1.0), axis("VNA", 0.0, 1.0)),
        reads=("VNA.Trace",), save_maps=True, map_images=True),
        {"K": Knob(), "VNA": VNA()})

    pngs = sorted(os.path.join(r, n) for r, _d, ns in os.walk(tmp)
                  for n in ns if n.endswith(".png"))
    assert len(pngs) == 2, f"one per master point: {pngs}"
    for png in pngs:
        assert os.path.getsize(png) > 1000, "an empty file is not a picture"
        assert "images" in png and "tables" not in png
        folder = os.path.basename(os.path.dirname(png))
        assert folder.startswith("K.Volt_"), folder


def test_a_trace_read_shares_the_sweeps_one_render_thread(tmp_path):
    """One background renderer per sweep, not one per read: a rig with
    four VNAs must not spawn four threads to draw four maps."""
    tmp = str(tmp_path)
    engine, _ = run(tmp, SweepProgram(
        axes=(axis("K", 0.0, 1.0), axis("VNA", 0.0, 1.0)),
        reads=("VNA.Trace", "VNA.Level"), save_maps=True, map_images=True),
        {"K": Knob(), "VNA": VNA()})
    promoted = engine._vector_maps["VNA.Trace"]
    assert promoted is not None
    assert promoted._renderer is engine._map._renderer
    assert promoted._owns_renderer is False


def test_a_1d_trace_sweep_renders_without_any_scalar_map(tmp_path):
    """There is no MapWriter at all in a 1-D sweep, so the promoted map
    has to bring its own renderer — and close it."""
    tmp = str(tmp_path)
    engine, _ = run(tmp, SweepProgram(
        axes=(axis("VNA", 0.0, 2.0),), reads=("VNA.Trace",),
        save_maps=True, map_images=True), {"VNA": VNA()})
    assert engine._map is None
    promoted = engine._vector_maps["VNA.Trace"]
    assert promoted._owns_renderer is True
    assert not promoted._renderer.is_alive(), "it must be closed at the end"
    pngs = [n for _r, _d, ns in os.walk(tmp) for n in ns
            if n.endswith(".png")]
    assert len(pngs) == 1, pngs
