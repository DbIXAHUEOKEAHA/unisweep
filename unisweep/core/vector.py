"""Reads that are a whole trace, not one number.

A VNA hands back a sweep of its own at every point: 201, 1601, 20 001
numbers where the rest of Unisweep expects a float. The way round it so
far has been to join them into a comma-separated string, put that in one
CSV cell, and unpick it afterwards. That works, and it throws away the
one thing the instrument was sure about — the shape of the data.

This module is the boundary where a reading is recognised for what it is.
Everything downstream then knows: the engine, the map writers, the plot
windows.

**Detection is by shape, not by configuration.** A driver that already
returns a list or a numpy array is understood with no profile, no flag
and no code change; a driver that returns the legacy comma-joined string
is understood too, because that is what most of them do today. The lab
profile can force the question either way when a reading is ambiguous —
a device that returns "1,2" only sometimes, say — but nothing has to be
declared for the common case.

**The trace has an axis of its own** (frequency, delay, wavelength), and
where it comes from is a precedence, not a rule:

1. the lab profile, when it states one;
2. the driver, through a companion getter — ``Trace`` is paired with
   ``Trace_axis`` — read once per run, not once per point;
3. failing both, the index 0…N-1, which is honest about knowing nothing.

**A trace that changes length mid-sweep** is fitted to the length the run
started with — padded with NaN or truncated — and the caller is told once.
Someone retuning the span at 3 a.m. must not cost the night's data, and a
NaN in the file is visible in a way a silently reshaped grid is not.
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from typing import Any, Optional, Sequence

__all__ = ["as_vector", "vector_text", "fit_to_length", "resolve_axis",
           "VectorSpec", "MAX_LENGTH", "axis_getter_name"]

#: A trace longer than this is almost certainly a mistake — a whole
#: waveform memory read back by accident. It is truncated rather than
#: allowed to size an array that eats the machine.
MAX_LENGTH = 1_000_000

_SEPARATORS = (",", ";", "\t")


def _from_text(text: str) -> Optional[np.ndarray]:
    """A trace as most drivers write one today, or None.

    Deliberately strict: every token has to be a number and there have to
    be at least two of them. A reading that happens to be the string
    "open" or "1 error" is a scalar-ish reading with a problem, not a
    trace, and guessing otherwise would quietly reshape someone's data.
    """
    text = text.strip().strip("()[]{}").strip()
    if not text:
        return None
    parts: list = []
    for separator in _SEPARATORS:
        if separator in text:
            parts = text.split(separator)
            break
    else:
        parts = text.split()
    if len(parts) < 2:
        return None
    out = np.empty(len(parts), dtype=float)
    for i, token in enumerate(parts):
        token = token.strip()
        if not token:
            return None
        try:
            out[i] = float(token)
        except ValueError:
            return None
    return out


def as_vector(value: Any, force: str = "auto") -> Optional[np.ndarray]:
    """The reading as a 1-D float array, or None if it is one number.

    ``force`` is the lab profile's say: ``"always"`` insists a reading is
    a trace (a length-1 array stays a trace, so the files keep their
    shape), ``"never"`` insists it is not, ``"auto"`` looks at the value.
    """
    if force == "never":
        return None
    if value is None:
        return None
    if isinstance(value, (bool, int, float, np.number)):
        # forced: one number is a one-point trace, so a run whose
        # instrument occasionally returns a single point keeps the shape
        # of its files instead of changing kind halfway through
        return (np.array([float(value)], dtype=float)
                if force == "always" else None)
    if isinstance(value, (bytes, bytearray)):
        try:
            value = value.decode("ascii", "ignore")
        except Exception:                          # noqa: BLE001
            return None
    if isinstance(value, str):
        found = _from_text(value)
        if found is None and force == "always":
            try:
                return np.array([float(value)], dtype=float)
            except ValueError:
                return None
        return found if found is None else _capped(found)
    try:
        array = np.asarray(value, dtype=float)
    except (TypeError, ValueError):
        return None
    if array.ndim == 0:
        return np.array([float(array)]) if force == "always" else None
    array = array.ravel()
    if array.size < 2 and force != "always":
        # a driver handing back [x] is reporting one number in a box
        return None
    return _capped(array)


def _capped(array: np.ndarray) -> np.ndarray:
    return array[:MAX_LENGTH] if array.size > MAX_LENGTH else array


def vector_text(values: Sequence[float]) -> str:
    """The trace as it goes into the per-point CSV: one cell, commas.

    Unchanged from what the drivers produce today on purpose — the row
    file stays readable by every script already pointed at it, and the
    full-precision copy lives in the map tables beside it.
    """
    return ",".join("nan" if not np.isfinite(v) else f"{v:.10g}"
                    for v in np.asarray(values, dtype=float).ravel())


def fit_to_length(values: Sequence[float], length: int) -> np.ndarray:
    """Force a trace onto the length the run started with."""
    array = np.asarray(values, dtype=float).ravel()
    if array.size == length:
        return array
    if array.size > length:
        return array[:length]
    return np.concatenate([array, np.full(length - array.size, np.nan)])


def axis_getter_name(option: str) -> str:
    """``Trace`` → ``Trace_axis``: the companion getter convention."""
    return f"{option}_axis"


@dataclass(frozen=True)
class VectorSpec:
    """What a trace-valued read looks like, fixed for the whole run."""

    read: str
    length: int
    axis: np.ndarray = field(default_factory=lambda: np.empty(0))
    axis_name: str = "index"
    axis_unit: str = ""
    source: str = "index"             # profile | driver | index

    @property
    def axis_label(self) -> str:
        return (f"{self.axis_name} ({self.axis_unit})" if self.axis_unit
                else self.axis_name)

    def describe(self) -> str:
        return (f"{self.read}: {self.length} points, x = {self.axis_label} "
                f"from the {self.source}")


def _axis_from_profile(spec) -> Optional[np.ndarray]:
    declared = getattr(spec, "vector_axis", None)
    if declared is None or isinstance(declared, str):
        return None
    try:
        axis = np.asarray(declared, dtype=float).ravel()
    except (TypeError, ValueError):
        return None
    return axis if axis.size else None


def _axis_from_driver(adapter, option: str, spec) -> Optional[np.ndarray]:
    """Ask the instrument for its own x axis, once.

    The getter is named by the profile when it says so, and by the
    ``<option>_axis`` convention otherwise — the same shape of agreement
    as ``loggable``: a driver opts in by having the attribute, and every
    driver that does not is simply indexed.
    """
    if adapter is None:
        return None
    declared = getattr(spec, "vector_axis", None)
    names = []
    if isinstance(declared, str) and declared and declared != "index":
        names.append(declared)
    names.append(axis_getter_name(option))
    raw = getattr(adapter, "raw", adapter)
    for name in names:
        getter = getattr(raw, name, None)
        if not callable(getter):
            continue
        try:
            axis = as_vector(getter(), force="always")
        except Exception:                          # noqa: BLE001
            continue                               # an axis is a bonus
        if axis is not None and axis.size:
            return axis
    return None


def resolve_axis(read: str, length: int, adapter=None,
                 spec=None) -> VectorSpec:
    """Settle the trace's x axis once, at the start of a run."""
    axis, source = None, "index"
    from_profile = _axis_from_profile(spec)
    if from_profile is not None:
        axis, source = from_profile, "profile"
    if axis is None:
        from_driver = _axis_from_driver(adapter, read.rpartition(".")[2],
                                        spec)
        if from_driver is not None:
            axis, source = from_driver, "driver"
    if axis is None:
        axis, source = np.arange(length, dtype=float), "index"
    elif axis.size != length:
        # the instrument's own axis has to match its own trace; when it
        # does not, the trace is the thing that was measured
        axis = fit_to_length(axis, length)
    name = ""
    unit = ""
    if spec is not None:
        name = str(getattr(spec, "axis_name", "") or "")
        unit = str(getattr(spec, "axis_unit", "") or "")
    if not name:
        name = {"profile": "axis", "driver": "axis",
                "index": "index"}[source]
    return VectorSpec(read=read, length=int(length), axis=axis,
                      axis_name=name, axis_unit=unit, source=source)
