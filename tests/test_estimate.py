"""The planned point count and the ETA, against what the engine really does.

Every case here runs the real :class:`SweepEngine` over mock devices and
counts the points it actually measured, then demands that
``estimate_program`` predicted exactly that number. Nothing is asserted
against a formula reimplemented in the test, because a formula copied into
the test is a formula that agrees with itself — which is how the estimate
came to be wrong in three independent ways at once:

* ``walks`` counted on outer axes, though the engine makes exactly one
  measured pass on a non-innermost axis and walks it back as
  repositioning;
* one forward point count reused for a backward walk, whose step size
  differs whenever ``back_rate`` (or ``back_delay`` in rate mode) is set;
* the turning point between consecutive walks counted twice — three
  points there and back is five, not six.

The duration is harder to pin than the count, because the engine also
spends real time talking to instruments and flying axes back to their
start. Those tests therefore assert *relations* the estimate must respect
(a snake row costs less than a row that flies back; a slower return costs
more) rather than a wall-clock number.
"""

import os
import queue
import sys
import tempfile
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("MPLBACKEND", "Agg")

import pytest

from unisweep.core import events as ev
from unisweep.core.config import (AxisProgram, CountMode, LiveProgram,
                                  SweepProgram, plan_axis, plan_program)
from unisweep.core.devices import DeviceRegistry, DriverAdapter
from unisweep.core.engine import SweepEngine
from unisweep.core.limits import estimate_program
from tests.mock_driver import MockDevice


class FakeRegistry(DeviceRegistry):
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


def measured_points(program, devices=1, timeout=120):
    """Run the sweep for real and count the rows it took."""
    tmp = tempfile.mkdtemp(prefix="unisweep_eta_")
    q = queue.Queue()
    mocks = {f"M{i + 1}": MockDevice() for i in range(devices)}
    engine = SweepEngine(LiveProgram(program), FakeRegistry(tmp, mocks),
                         tmp, q)
    engine.start()
    engine.join(timeout)
    assert not engine.is_alive(), "engine did not finish"
    rows = 0
    while not q.empty():
        if isinstance(q.get_nowait(), ev.PointMeasured):
            rows += 1
    return rows


def ax(device="M1", **kw):
    """A 5-point axis by default: 0 -> 1 in steps of 0.25."""
    base = dict(device=device, parameter="Volt", start=0.0, stop=1.0,
                rate=0.25, delay=0.002, count_mode=CountMode.STEP)
    base.update(kw)
    return AxisProgram(**base)


# ---------------------------------------------------------------------------
# the matrix: speeds, steps, walks, snake, on every axis
# ---------------------------------------------------------------------------
CASES = {
    # --- one dimension ---------------------------------------------------
    "1d_single_pass": (SweepProgram(axes=(ax(),)), 1),
    "1d_walks_2": (SweepProgram(axes=(ax(walks=2),)), 1),
    "1d_walks_3": (SweepProgram(axes=(ax(walks=3),)), 1),
    "1d_walks_4": (SweepProgram(axes=(ax(walks=4),)), 1),
    # a coarser return: fewer points on the way back
    "1d_coarse_return": (SweepProgram(axes=(ax(back_rate=0.5),)), 1),
    # a finer return: more points on the way back
    "1d_fine_return": (SweepProgram(axes=(ax(back_rate=0.125),)), 1),
    # a return rate alone implies there-and-back, with walks still at 1
    "1d_return_implies_two_walks": (
        SweepProgram(axes=(ax(back_rate=0.5, walks=1),)), 1),
    "1d_slow_return_same_step": (
        SweepProgram(axes=(ax(back_delay=0.004),)), 1),
    # rate mode: step = rate * delay, so a back_delay changes the step too
    "1d_rate_mode": (SweepProgram(axes=(
        ax(rate=25.0, delay=0.01, count_mode=CountMode.RATE),)), 1),
    "1d_rate_mode_slow_return": (SweepProgram(axes=(
        ax(rate=25.0, delay=0.01, count_mode=CountMode.RATE,
           back_delay=0.02),)), 1),
    "1d_uneven_span": (SweepProgram(axes=(ax(rate=0.3, walks=2),)), 1),

    # --- two dimensions --------------------------------------------------
    "2d_plain": (SweepProgram(axes=(ax("M2", rate=0.5), ax())), 2),
    "2d_inner_walks_2": (
        SweepProgram(axes=(ax("M2", rate=0.5), ax(walks=2))), 2),
    "2d_inner_walks_3": (
        SweepProgram(axes=(ax("M2", rate=0.5), ax(walks=3))), 2),
    "2d_inner_snake": (
        SweepProgram(axes=(ax("M2", rate=0.5), ax(snake=True))), 2),
    "2d_inner_snake_walks_2": (
        SweepProgram(axes=(ax("M2", rate=0.5), ax(walks=2, snake=True))), 2),
    # walks on the master: the engine ignores them, so the count must not move
    "2d_outer_walks_2": (
        SweepProgram(axes=(ax("M2", rate=0.5, walks=2), ax())), 2),
    "2d_outer_walks_3_snake": (
        SweepProgram(axes=(ax("M2", rate=0.5, walks=3, snake=True), ax())), 2),
    "2d_inner_coarse_return": (
        SweepProgram(axes=(ax("M2", rate=0.5), ax(back_rate=0.5))), 2),
    "2d_outer_return_rate": (
        SweepProgram(axes=(ax("M2", rate=0.5, back_rate=1.0), ax())), 2),
    "2d_both_axes_returns": (
        SweepProgram(axes=(ax("M2", rate=0.5, back_rate=1.0),
                           ax(back_rate=0.5))), 2),
    "2d_asymmetric_spans": (
        SweepProgram(axes=(ax("M2", start=-1.0, stop=2.0, rate=0.75),
                           ax(start=0.0, stop=0.6, rate=0.2, walks=2))), 2),

    # --- three dimensions ------------------------------------------------
    "3d_plain": (SweepProgram(axes=(ax("M3", rate=1.0), ax("M2", rate=0.5),
                                    ax())), 3),
    "3d_inner_walks_2": (
        SweepProgram(axes=(ax("M3", rate=1.0), ax("M2", rate=0.5),
                           ax(walks=2))), 3),
    "3d_inner_snake_walks_2": (
        SweepProgram(axes=(ax("M3", rate=1.0), ax("M2", rate=0.5),
                           ax(walks=2, snake=True))), 3),
    "3d_middle_snake": (
        SweepProgram(axes=(ax("M3", rate=1.0),
                           ax("M2", rate=0.5, snake=True), ax())), 3),
    "3d_walks_everywhere": (
        SweepProgram(axes=(ax("M3", rate=1.0, walks=2),
                           ax("M2", rate=0.5, walks=2), ax(walks=2))), 3),
    "3d_inner_coarse_return": (
        SweepProgram(axes=(ax("M3", rate=1.0), ax("M2", rate=0.5),
                           ax(back_rate=0.5))), 3),
}


@pytest.mark.parametrize("name", sorted(CASES))
def test_the_estimate_matches_what_the_engine_measures(name):
    program, devices = CASES[name]
    predicted, _ = estimate_program(program)
    actual = measured_points(program, devices=devices)
    assert predicted == actual, (
        f"{name}: estimate says {predicted} points, the engine took {actual}")


# ---------------------------------------------------------------------------
# the three ways it used to be wrong, pinned individually
# ---------------------------------------------------------------------------
def test_consecutive_walks_share_their_turning_point():
    """0 -> 1 in steps of 0.5 is 3 points; there and back is 5, not 6.
    The engine sets and measures the turn once."""
    assert plan_axis(ax(rate=0.5), walks=1)[0] == 3
    assert plan_axis(ax(rate=0.5), walks=2)[0] == 5
    assert plan_axis(ax(rate=0.5), walks=3)[0] == 7
    assert plan_axis(ax(rate=0.5), walks=4)[0] == 9


def test_a_return_walk_is_counted_at_its_own_step_size():
    """Coarse on the way back: 5 points out, 3 back, turn shared -> 7."""
    assert plan_axis(ax(rate=0.25, back_rate=0.5), walks=2)[0] == 7
    # and finer on the way back: 5 out, 9 back, turn shared -> 13
    assert plan_axis(ax(rate=0.25, back_rate=0.125), walks=2)[0] == 13


def test_walks_on_an_outer_axis_do_not_multiply_the_sweep():
    """The engine makes exactly one measured pass on a non-innermost axis;
    the way back is repositioning. Counting walks there inflated the whole
    nested product."""
    outer = ax("M2", rate=0.5)
    inner = ax()
    plain, _ = plan_program((outer, inner))
    walked, _ = plan_program((AxisProgram(**{**outer.__dict__, "walks": 3}),
                              inner))
    assert plain == walked


def test_the_innermost_axis_is_the_one_whose_walks_count():
    outer = ax("M2", rate=0.5)
    one, _ = plan_program((outer, ax()))
    two, _ = plan_program((outer, ax(walks=2)))
    assert two > one


# ---------------------------------------------------------------------------
# duration: the relations it has to respect
# ---------------------------------------------------------------------------
def test_a_snake_row_costs_less_than_one_that_flies_back():
    """The fly-back between rows was not costed at all, so snake and
    non-snake estimated identically while really differing by hours."""
    outer = ax("M2", rate=0.5)
    _, flying = plan_program((outer, ax(snake=False)))
    _, snaking = plan_program((outer, ax(snake=True)))
    assert flying > snaking


def test_a_slower_return_costs_more_time():
    """back_delay applies to the backward walk only, and used not to be
    read at all — every walk was priced at the forward delay."""
    quick = plan_axis(ax(), walks=2)[1]
    slow = plan_axis(ax(back_delay=0.02), walks=2)[1]
    assert slow > quick
    # and the forward walk is unaffected by it
    assert plan_axis(ax(), walks=1)[1] == plan_axis(
        ax(back_delay=0.02), walks=1)[1]


def test_duration_grows_with_the_nesting():
    inner = ax()
    _, one_d = plan_program((inner,))
    _, two_d = plan_program((ax("M2", rate=0.5), inner))
    _, three_d = plan_program((ax("M3", rate=1.0), ax("M2", rate=0.5), inner))
    assert one_d < two_d < three_d


def test_a_zero_delay_sweep_still_has_points():
    points, seconds = plan_program((ax(delay=0.0),))
    assert points == 5 and seconds == 0.0


# ---------------------------------------------------------------------------
# no second copy of the arithmetic
# ---------------------------------------------------------------------------
def test_every_caller_shares_one_planner():
    """The count had three implementations — the profile pre-flight, the
    engine's progress denominator and the sweep page's estimate — and they
    disagreed. They must now be the same number."""
    program = SweepProgram(axes=(ax("M2", rate=0.5, walks=2),
                                 ax(walks=3, back_rate=0.5)))
    from_limits, _ = estimate_program(program)
    from_planner, _ = plan_program(program.axes)

    tmp = tempfile.mkdtemp(prefix="unisweep_eta_")
    engine = SweepEngine(LiveProgram(program),
                         FakeRegistry(tmp, {"M1": MockDevice(),
                                            "M2": MockDevice()}),
                         tmp, queue.Queue())
    from_engine = engine._planned_total()

    assert from_limits == from_planner == from_engine


def test_the_solved_axis_of_a_coupled_condition_is_not_looped():
    """A curve-following condition computes one axis from another, so it
    has no loop of its own and must not multiply the count."""
    program = SweepProgram(axes=(ax("M2", rate=0.5), ax()),
                           condition="x == 2*y")
    coupled, _ = estimate_program(program)
    single, _ = plan_program((ax(),))
    assert coupled == single
