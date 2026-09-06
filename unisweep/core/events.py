"""Events emitted by the sweep engine.

The engine never touches the GUI (the legacy thread edited Tk widgets
directly, which is what caused the intermittent freezes). Instead it pushes
these events into a ``queue.Queue``; the GUI drains the queue on the Tk main
loop via ``after``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

__all__ = [
    "SweepStarted", "FileOpened", "PointMeasured", "PointSkipped",
    "WalkFinished", "AxisStepped", "SweepPaused", "SweepResumed",
    "SweepError", "SweepFinished", "Progress", "MapRowCommitted",
]


@dataclass(frozen=True)
class SweepStarted:
    columns: tuple
    dimensions: int
    planned_points: int


@dataclass(frozen=True)
class FileOpened:
    path: str
    columns: tuple


@dataclass(frozen=True)
class PointMeasured:
    row: tuple                    # matches columns
    axis_values: tuple            # current setpoints, axis 1..N
    file: str
    walk: int = 1                 # innermost-axis walk number (1-based)


@dataclass(frozen=True)
class PointSkipped:
    axis_values: tuple            # point excluded by the region condition


@dataclass(frozen=True)
class ApproachStarted:
    """Instruments start moving toward initial positions (parallel goto:
    the sweep-start approach or a mid-sweep return). targets: tuples of
    (axis 1-based, device, parameter, current, target)."""
    targets: tuple = ()
    phase: str = "approach"          # 'approach' | 'return'


@dataclass(frozen=True)
class ApproachFinished:
    phase: str = "approach"


@dataclass(frozen=True)
class AxisStepped:
    axis: int                     # 1-based
    value: float


@dataclass(frozen=True)
class MapRowCommitted:
    """A completed map line, built with the legacy walk-aware row logic
    (grid frozen per iteration, rows interpolated onto it, condition holes
    as NaN). GUI maps append these rows — they never re-bin raw points."""
    grid: tuple                   # inner-axis grid (walk-concatenated)
    read_rows: dict               # read name -> tuple of values on the grid
    row_value: float              # outer (row) axis value
    master_value: float           # 3-D master value (0.0 for 2-D)
    iteration: int                # 3-D iteration index (0 for 2-D)


@dataclass(frozen=True)
class WalkFinished:
    axis: int
    walk: int


@dataclass(frozen=True)
class SweepPaused:
    pass


@dataclass(frozen=True)
class SweepResumed:
    pass


@dataclass(frozen=True)
class SweepError:
    where: str
    message: str
    fatal: bool = False
    #: the fault is on a device the sweep depends on (an axis device) —
    #: the GUI raises a warning window naming the instrument
    crucial: bool = False


@dataclass(frozen=True)
class Progress:
    done: int
    total: int                    # re-estimated live (instructions can change)
    eta_seconds: Optional[float] = None
    elapsed_seconds: Optional[float] = None


@dataclass(frozen=True)
class SweepFinished:
    stopped: bool                 # True if user pressed Stop / To-zero
    points: int
