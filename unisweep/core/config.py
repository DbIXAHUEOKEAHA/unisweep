"""Sweep configuration.

The legacy engine kept every knob in module globals precisely so the GUI (or a
freshly uploaded manual-steps file) could change a running sweep. That
capability is preserved here, but made safe:

* :class:`AxisProgram` / :class:`SweepProgram` are *immutable snapshots* of the
  instructions;
* :class:`LiveProgram` is the single shared, lock-protected holder. The GUI
  replaces fields through it at any time; the engine re-reads it **at every
  step boundary**, so edits take effect on the very next point — exactly the
  behaviour the globals used to provide, minus the race conditions.

A monotonically increasing ``version`` lets long-running pieces (the
continuous-ramp loop for "sweepable" devices, the compiled condition, manual
step tables) notice a change and re-arm themselves.
"""

from __future__ import annotations

import json
import math
import threading
from dataclasses import dataclass, field, replace, asdict
from typing import Optional, Tuple

__all__ = ["CountMode", "AxisProgram", "SweepProgram", "LiveProgram"]


class CountMode:
    RATE = "ratio"   # user enters units / second (legacy 'ratio')
    STEP = "step"    # user enters units / step  (legacy 'step')


@dataclass(frozen=True)
class AxisProgram:
    """Instructions for one sweep axis (axis 1 = master/outermost)."""

    device: str = "Time"          # device address key in the registry
    parameter: str = "Time"       # entry of the device's set_options
    start: float = 0.0
    stop: float = 1.0
    rate: float = 1.0             # units per second, forward direction
    delay: float = 1.0            # seconds spent on each point, forward
    count_mode: str = CountMode.RATE
    back_rate: Optional[float] = None    # None -> same as forward
    back_delay: Optional[float] = None   # None -> same as forward
    walks: int = 1                # back-and-forth passes (legacy meaning)
    snake: bool = False           # boustrophedon: don't fly back between rows
    manual_points: Optional[Tuple[float, ...]] = None
    manual_name: str = ""         # display-only origin of manual points
    force_stepwise: bool = False  # legacy 'stepper_flag' per axis

    # ---- derived helpers -------------------------------------------------
    def step_size(self, backward: bool = False) -> float:
        """Unsigned units-per-step for the requested direction."""
        rate = self.rate if not backward or self.back_rate is None \
            else self.back_rate
        delay = self.delay if not backward or self.back_delay is None \
            else self.back_delay
        if self.count_mode == CountMode.STEP:
            return abs(rate)          # 'rate' field then *is* the step
        return abs(rate * delay)

    def point_delay(self, backward: bool = False) -> float:
        d = self.delay if not backward or self.back_delay is None \
            else self.back_delay
        return max(float(d), 0.0)

    def effective_walks(self) -> int:
        """Walk count the sweep actually runs.

        A return rate/delay only exists on a backward pass, so entering
        one **implies** there-and-back: with the walk counter still at 1
        the legacy 'return sweep' silently never happened. Everything —
        engine loop, map grid, ETA — takes the count from here so the
        implication stays consistent.
        """
        w = max(int(self.walks), 1)
        if w < 2 and (self.back_rate is not None
                      or self.back_delay is not None):
            return 2
        return w

    def planned_count(self, backward: bool = False) -> int:
        """Number of points in one walk in the given direction.

        The direction matters: ``back_rate`` — or ``back_delay`` in rate
        mode — changes the step size, so a return walk can have a different
        number of points from the forward one. Reusing the forward count
        for every walk is one of the three things that made the ETA wrong.

        The walk takes ``floor(span/step)`` whole steps plus the start, and
        one more only when a partial step is left over — the runner clamps
        that onto the endpoint. The float remainder has to be judged
        against *both* ends: ``1 % 0.1`` is 0.0999…, which looks like a
        whole leftover step and used to add a phantom point to every span
        that happened to divide evenly in decimal.
        """
        if self.manual_points is not None:
            return max(len(self.manual_points), 1)
        step = self.step_size(backward)
        if step <= 0 or not math.isfinite(step):
            return 1
        span = abs(self.stop - self.start)
        steps = span / step
        whole = math.floor(steps + 1e-9)
        leftover = steps - whole
        return int(whole) + 1 + (1 if leftover > 1e-9 else 0)


def plan_axis(axis: "AxisProgram", walks: int = 1):
    """``(points, measured seconds, cost of flying it back)`` for one axis.

    ``walks`` is 1 for every axis but the innermost looping one: the engine
    makes exactly one measured pass on an outer axis and walks it back as
    repositioning, never as measurement.
    """
    points, seconds = 0, 0.0
    for w in range(max(int(walks), 1)):
        backward = bool(w % 2)
        n = max(axis.planned_count(backward), 1)
        if w:
            # the turning point was set and measured by the previous walk
            # and is not taken again — 3 points there and back is 5, not 6
            n -= 1
        n = max(n, 0)
        points += n
        seconds += n * axis.point_delay(backward)
    back_steps = max(max(axis.planned_count(True), 1) - 1, 0)
    flyback = 0.0 if axis.snake else back_steps * axis.point_delay(True)
    return points, seconds, flyback


def plan_program(axes, solved: Optional[int] = None):
    """``(points, seconds)`` the engine is expected to take.

    The single home for this arithmetic. The engine's progress total, the
    lab profile's ``max_duration_s`` pre-flight and the sweep page's
    estimate all call it, because three separate copies had drifted apart
    and all three were wrong in the same three ways:

    * ``walks`` counted on outer axes, which the engine ignores by design;
    * one forward point count reused for a backward walk that has its own
      step size;
    * the turning point between consecutive walks counted twice.

    What it models: per-direction step sizes and delays, the shared
    turning point, walks on the innermost axis only, and the fly-back
    between rows that a ``snake`` axis does not pay.

    What it cannot: whether an instrument ramps itself, so the fly-back is
    priced as a stepwise walk and a self-ramping axis returns sooner than
    this says. Instrument settling and communication time are invisible
    here too, so treat the result as a floor.
    """
    loop = [i for i in range(len(axes)) if i != solved]
    if not loop:
        return 1, 0.0
    inner = loop[-1]
    plans = {i: plan_axis(axes[i],
                          axes[i].effective_walks() if i == inner else 1)
             for i in loop}

    total = 1
    for i in loop:
        total *= max(plans[i][0], 1)

    seconds = 0.0
    entries = 1                       # how often this level is entered
    for pos, i in enumerate(loop):
        points, measured, _ = plans[i]
        seconds += entries * measured
        steps = entries * max(points, 1)
        below = [plans[j][2] for j in loop[pos + 1:]]
        if below:
            # the levels below are walked back together, so one return
            # costs the slowest of them rather than their sum
            seconds += steps * max(below)
        entries = steps
    return total, seconds


@dataclass(frozen=True)
class SweepProgram:
    axes: Tuple[AxisProgram, ...] = (AxisProgram(),)
    reads: Tuple[str, ...] = ()          # "address.option" strings
    condition: str = ""                  # multi-line user condition text
    script: str = ""                     # per-point user script
    filename: str = ""                   # '' -> auto naming
    to_zero_on_finish: bool = False
    approach_start: bool = True          # walk axes to their start point
                                         # (False = start from wherever
                                         # the instrument stands — the
                                         # v1 'Start warning' No-branch)
    save_maps: bool = True               # write 2d_maps output (2D/3D)
    map_style: str = "grid"              # 'grid' worksheet | 'xyz' | 'both'
    map_interpolated: bool = True        # map samples onto the grid by value
    map_uniform: bool = False            # force a uniformly spaced grid
    map_images: bool = True              # keep PNG (and 3D GIF) mirrors

    @property
    def dimensions(self) -> int:
        return len(self.axes)


class LiveProgram:
    """Thread-safe, versioned holder of the current :class:`SweepProgram`.

    This object *is* the replacement for the old globals: the GUI writes
    through it while the engine runs, and the engine reads it every step.
    """

    def __init__(self, program: SweepProgram):
        self._lock = threading.Lock()
        self._program = program
        self._version = 0
        self._axis_versions = [0] * len(program.axes)

    # ---- reading ---------------------------------------------------------
    def get(self) -> SweepProgram:
        with self._lock:
            return self._program

    def axis(self, index: int) -> AxisProgram:
        with self._lock:
            return self._program.axes[index]

    @property
    def version(self) -> int:
        with self._lock:
            return self._version

    def axis_version(self, index: int) -> int:
        with self._lock:
            return self._axis_versions[index]

    # ---- writing (GUI thread) -------------------------------------------
    def replace(self, program: SweepProgram) -> None:
        with self._lock:
            self._program = program
            self._version += 1
            self._axis_versions = [v + 1 for v in self._axis_versions]

    def update(self, **changes) -> None:
        with self._lock:
            self._program = replace(self._program, **changes)
            self._version += 1

    def update_axis(self, index: int, **changes) -> None:
        """Push a live edit of one axis (from/to/rate/delay/manual...)."""
        with self._lock:
            axes = list(self._program.axes)
            axes[index] = replace(axes[index], **changes)
            self._program = replace(self._program, axes=tuple(axes))
            self._version += 1
            self._axis_versions[index] += 1

    def swap_manual_points(self, index: int, points, name: str = "") -> None:
        """Hot-swap the manual step table of an axis mid-sweep."""
        pts = tuple(float(p) for p in points) if points is not None else None
        self.update_axis(index, manual_points=pts, manual_name=name)


# ---- (de)serialisation ---------------------------------------------------

def program_to_dict(program: SweepProgram) -> dict:
    d = asdict(program)
    return d


def program_from_dict(d: dict) -> SweepProgram:
    axes = tuple(
        AxisProgram(**{k: (tuple(v) if k == "manual_points" and v is not None
                           else v) for k, v in ax.items()})
        for ax in d.get("axes", [{}])
    )
    keys = {f.name for f in SweepProgram.__dataclass_fields__.values()}  # type: ignore[attr-defined]
    rest = {k: v for k, v in d.items() if k in keys and k != "axes"}
    if "reads" in rest:
        rest["reads"] = tuple(rest["reads"])
    return SweepProgram(axes=axes, **rest)


def save_program(program: SweepProgram, path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(program_to_dict(program), fh, indent=2)


def load_program(path: str) -> SweepProgram:
    with open(path, "r", encoding="utf-8") as fh:
        return program_from_dict(json.load(fh))
