"""Per-axis point generation.

This module is the direct replacement for the old ``value += step`` /
``while condition(axis)`` machinery, and it is designed around the same
requirement that motivated the globals: **the trajectory may be edited while
the sweep runs**.

How live editing works
----------------------
:meth:`AxisRunner.walk` is a generator. On *every* iteration it re-reads the
axis instructions from the shared :class:`~unisweep.core.config.LiveProgram`.
Consequences:

* changing ``stop`` mid-walk retargets the walk — the runner heads toward the
  new endpoint from wherever it currently is (even if that means reversing);
* changing ``rate`` / ``delay`` changes the step size and dwell time from the
  next point on;
* hot-swapping ``manual_points`` (uploading a new manual-steps file) is picked
  up immediately: the runner re-anchors to the nearest position in the new
  table and continues.

Endpoint guarantee (the "last step" fix)
----------------------------------------
The legacy loop stopped when ``value + step`` exceeded ``to + eps``, so the
final point was frequently *never set or measured*, and ``final_step`` only
patched it under fragile conditions. Here the overshoot check clamps the last
point exactly onto ``stop`` and marks it ``is_final`` — the endpoint is always
produced, once, regardless of whether the span divides evenly by the step and
regardless of device epsilons.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .config import LiveProgram

__all__ = ["StepPoint", "AxisRunner"]


@dataclass(frozen=True)
class StepPoint:
    value: float          # setpoint to apply
    delay: float          # dwell time after applying it
    is_final: bool        # True exactly once, on the walk's last point
    index: int            # 0-based point index within this walk


def _close(a: float, b: float) -> bool:
    scale = max(abs(a), abs(b), 1e-30)
    return abs(a - b) <= 1e-9 * scale


class AxisRunner:
    """Generates the points of one axis walk, honouring live edits."""

    def __init__(self, live: LiveProgram, axis_index: int):
        self.live = live
        self.index = axis_index
        self.last_value: float | None = None   # where the axis currently sits

    # -----------------------------------------------------------------
    def walk(self, backward: bool = False, start_at: float | None = None):
        """Yield :class:`StepPoint` s from start to stop (inclusive).

        ``backward=True`` swaps the roles of start/stop and uses the
        back-sweep rate/delay (legacy back_ratio / back_delay_factor).
        ``start_at`` lets snake mode continue from the current position
        instead of flying back.
        """
        ax0 = self.live.axis(self.index)
        if ax0.manual_points is not None:
            yield from self._walk_manual(backward)
            return

        value: float | None = None
        i = 0
        while True:
            ax = self.live.axis(self.index)          # live re-read
            if ax.manual_points is not None:         # switched to manual mid-walk
                yield from self._walk_manual(backward, anchor=True)
                return
            a = ax.stop if backward else ax.start
            b = ax.start if backward else ax.stop
            if value is None:
                value = float(start_at) if start_at is not None else float(a)
                self.last_value = value
                final = _close(value, b)
                yield StepPoint(value, ax.point_delay(backward), final, i)
                if final:
                    return
                i += 1
                continue

            step_mag = ax.step_size(backward)
            if step_mag <= 0 or not math.isfinite(step_mag):
                # degenerate instructions: finish the walk on the endpoint
                value = float(b)
                self.last_value = value
                yield StepPoint(value, ax.point_delay(backward), True, i)
                return

            sign = 1.0 if (b - value) >= 0 else -1.0   # toward the *current* b
            nxt = value + sign * step_mag
            # tolerance absorbs float-accumulation dust: without it a span
            # like 0->1 in 0.1 steps produced BOTH 0.9999999999999999 and
            # 1.0 as separate points
            final = sign * (b - nxt) <= step_mag * 1e-9
            value = float(b) if final else nxt         # clamp onto the endpoint
            self.last_value = value
            yield StepPoint(value, ax.point_delay(backward), final, i)
            if final:
                return
            i += 1

    # -----------------------------------------------------------------
    def _walk_manual(self, backward: bool, anchor: bool = False):
        """Walk a manual step table; tolerant to mid-walk hot swaps.

        When the table is replaced while walking (or when an auto walk is
        switched to manual), the runner *re-anchors*: it finds the entry of
        the new table nearest to the current position and continues from
        there, so a freshly uploaded file is always walked to its end.
        """
        last_seq: tuple | None = None
        i = 0
        while True:
            ax = self.live.axis(self.index)          # live re-read
            pts = ax.manual_points
            if pts is None:                          # switched back to auto
                yield from self.walk(backward, start_at=self.last_value)
                return
            seq = tuple(pts[::-1]) if backward else tuple(pts)
            if last_seq is None:
                if anchor and self.last_value is not None:
                    i = self._nearest(seq, self.last_value, skip_equal=True)
                last_seq = seq
            elif seq != last_seq:                    # hot swap mid-walk
                base = self.last_value if self.last_value is not None \
                    else seq[0]
                i = self._nearest(seq, base, skip_equal=True)
                last_seq = seq
            if i >= len(seq):
                return
            value = float(seq[i])
            self.last_value = value
            yield StepPoint(value, ax.point_delay(backward),
                            i == len(seq) - 1, i)
            i += 1

    @staticmethod
    def _nearest(seq: tuple, value: float, skip_equal: bool = False) -> int:
        i = min(range(len(seq)), key=lambda k: abs(seq[k] - value))
        if skip_equal and _close(seq[i], value):
            i += 1                                   # already sitting there
        return i

    # -----------------------------------------------------------------
    def local_step(self, backward: bool = False) -> float:
        """Current unsigned step size — used for condition tolerances."""
        ax = self.live.axis(self.index)
        if ax.manual_points is not None and len(ax.manual_points) > 1:
            diffs = [abs(b - a) for a, b in
                     zip(ax.manual_points, ax.manual_points[1:])]
            return max(sum(diffs) / len(diffs), 1e-30)
        return max(ax.step_size(backward), 1e-30)
