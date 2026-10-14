"""'Interpolate NaN holes in maps': what it fills, and what it must not.

The fill is a convenience for reading a map, so it is held to rules that
keep it from inventing anything a reader would mistake for a measurement:

* interior holes only — a line's ends are never extrapolated;
* forward and backward walks are never blended into each other;
* points a region condition skipped on purpose stay empty;
* the raw data is never touched — only the map worksheet and its image.

The engine tests read a probe that reports ten times the inner position, so
a filled cell has an exact right answer: a hole is not merely gone, it is
filled with the value a measurement there would have given.
"""

import os
import queue
import sys
import tempfile
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("MPLBACKEND", "Agg")

import numpy as np

from unisweep.core import events as ev
from unisweep.core.config import (AxisProgram, CountMode, LiveProgram,
                                  SweepProgram)
from unisweep.core.devices import DeviceRegistry, DriverAdapter
from unisweep.core.engine import SweepEngine
from unisweep.core.maps import fill_row_holes
from tests.mock_driver import MockDevice

NAN = float("nan")


# ---------------------------------------------------------------------------
# the rules, on one row
# ---------------------------------------------------------------------------
def test_an_interior_hole_is_filled_linearly_at_its_grid_position():
    grid = [0.0, 1.0, 2.0, 3.0, 4.0]
    row = [0.0, 10.0, NAN, NAN, 40.0]
    assert np.allclose(fill_row_holes(grid, row), [0, 10, 20, 30, 40])


def test_uneven_grid_spacing_is_respected():
    grid = [0.0, 1.0, 3.0, 4.0]
    row = [0.0, NAN, NAN, 40.0]
    assert np.allclose(fill_row_holes(grid, row), [0, 10, 30, 40])


def test_the_ends_of_a_line_are_never_extrapolated():
    """A walk that stopped early must still look like one."""
    out = fill_row_holes([0.0, 1.0, 2.0, 3.0, 4.0],
                         [NAN, 10.0, NAN, 30.0, NAN])
    assert np.isnan(out[0]) and np.isnan(out[4])
    assert out[2] == 20.0


def test_forward_and_backward_walks_are_not_blended():
    """There and back is [0 1 2 3 | 2 1 0]. A hole at the turn belongs to
    the forward walk, whose last real value is at 2 — so it is the END of
    that segment and stays empty, rather than being borrowed from the
    return pass, which would erase exactly the hysteresis a two-walk map
    exists to show."""
    grid = [0.0, 1.0, 2.0, 3.0, 2.0, 1.0, 0.0]
    row = [0.0, 10.0, 20.0, NAN, 25.0, 15.0, 5.0]
    out = fill_row_holes(grid, row)
    assert np.isnan(out[3])
    # while a hole inside the return pass is filled from that pass alone
    row = [0.0, 10.0, 20.0, 30.0, 25.0, NAN, 5.0]
    assert fill_row_holes(grid, row)[5] == 15.0


def test_protected_cells_stay_empty():
    out = fill_row_holes([0.0, 1.0, 2.0, 3.0, 4.0],
                         [0.0, NAN, NAN, NAN, 40.0],
                         protect=[False, False, True, False, False])
    assert out[1] == 10.0 and out[3] == 30.0
    assert np.isnan(out[2])


def test_a_row_with_nothing_to_anchor_to_is_left_alone():
    assert np.isnan(fill_row_holes([0.0, 1.0, 2.0], [NAN, 5.0, NAN])).sum() == 2
    assert np.isnan(fill_row_holes([0.0, 1.0, 2.0], [NAN, NAN, NAN])).all()


# ---------------------------------------------------------------------------
# through the engine
# ---------------------------------------------------------------------------
class Registry(DeviceRegistry):
    def __init__(self, core, mocks):
        self.core_dir, self._mocks, self._adapters = core, mocks, {}
        self._lock = threading.Lock()

    def connect(self, address):
        with self._lock:
            if address not in self._adapters:
                self._adapters[address] = DriverAdapter(address,
                                                        self._mocks[address])
            return self._adapters[address]


class Probe(MockDevice):
    """Reads ten times the inner axis position, except on chosen calls,
    which return NaN — an instrument dropping a reading."""

    def __init__(self, inner, holes=(), **kw):
        super().__init__(adress="M3", **kw)
        self.inner, self.holes, self.calls = inner, set(holes), 0

    def Curr(self):
        self.calls += 1
        if self.calls in self.holes:
            return NAN
        return 10.0 * self.inner._values["Volt"]


def run(fill, holes=(), condition=""):
    inner = MockDevice(adress="M2")
    probe = Probe(inner, holes)
    prog = SweepProgram(
        axes=(AxisProgram(device="M1", parameter="Volt", start=0.0, stop=1.0,
                          rate=1.0, delay=0.001, count_mode=CountMode.STEP),
              AxisProgram(device="M2", parameter="Volt", start=0.0, stop=1.0,
                          rate=0.1, delay=0.001, count_mode=CountMode.STEP)),
        reads=("M3.Curr",), save_maps=False, condition=condition,
        map_fill_nans=fill)
    core = tempfile.mkdtemp()
    q = queue.Queue()
    engine = SweepEngine(LiveProgram(prog),
                         Registry(core, {"M1": MockDevice(adress="M1"),
                                         "M2": inner, "M3": probe}),
                         core, q)
    engine.start()
    engine.join(60)
    assert not engine.is_alive()
    events = []
    while not q.empty():
        events.append(q.get_nowait())
    rows = [e for e in events if isinstance(e, ev.MapRowCommitted)]
    raw = [e for e in events if isinstance(e, ev.PointMeasured)]
    return rows, raw


def map_line(rows, n=0):
    e = rows[n]
    return np.asarray(e.grid, dtype=float), np.asarray(e.read_rows["M3.Curr"],
                                                       dtype=float)


def test_off_by_default_and_the_hole_shows():
    rows, _ = run(fill=False, holes={4, 5})
    _, line = map_line(rows)
    assert np.isnan(line).sum() == 2


def test_on_the_hole_is_filled_with_what_a_measurement_would_have_read():
    rows, _ = run(fill=True, holes={4, 5})
    grid, line = map_line(rows)
    assert not np.isnan(line).any()
    assert np.allclose(line, 10.0 * grid)


def test_the_raw_data_keeps_its_nan():
    """The fill shapes the map. It never rewrites what was measured."""
    _, raw = run(fill=True, holes={4, 5})

    def as_float(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0
    nans = sum(1 for e in raw for v in e.row if np.isnan(as_float(v)))
    assert nans == 2


def test_the_first_point_of_a_line_is_not_invented():
    rows, _ = run(fill=True, holes={1})
    _, line = map_line(rows)
    assert np.isnan(line[0]) and not np.isnan(line[1:]).any()


def test_points_a_condition_skipped_stay_empty():
    """The middle of the line is excluded on purpose. Filling it would put
    numbers inside a region nobody measured."""
    rows, _ = run(fill=True, condition="y < 0.35 or y > 0.65")
    grid, line = map_line(rows)
    excluded = (grid > 0.35) & (grid < 0.65)
    assert excluded.any()
    assert np.isnan(line[excluded]).all()
    assert np.allclose(line[~excluded], 10.0 * grid[~excluded])


def test_the_journal_says_the_map_was_filled():
    from unisweep.core.journal import Journal
    md = "\n".join(Journal._program_md(
        {"save_maps": True, "map_style": "grid", "map_fill_nans": True,
         "axes": []}, 2))
    assert "NaN holes interpolated" in md
