"""A tap on the engine's event stream.

The GUI drains the engine's queue on the Tk loop and paints it. An
assistant needs the same information, but asynchronously and *without*
being handed every measured point: a Landau fan is a hundred thousand rows,
and a model that reads them one by one has spent its context before it has
learned anything.

So the tap keeps two things:

* a bounded **ring of events**, numbered, so a caller can ask "what has
  happened since 4120?" and page forward;
* a rolling **summary** — state, progress, ETA, current file, the last few
  points and recent errors — which is what a status call
  actually wants and is a fixed, small size no matter how long the sweep
  runs.

Recording happens on the Tk thread inside the pump and must never raise or
block: a tap that can break the event pump would take the GUI down with it.
"""

from __future__ import annotations

import collections
import dataclasses
import threading
import time
from typing import Any, Optional

__all__ = ["EventTap"]


def plain(value: Any) -> Any:
    """JSON-friendly rendering; numpy scalars included."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple, set)):
        return [plain(v) for v in value]
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    item = getattr(value, "item", None)            # numpy scalar
    if callable(item):
        try:
            return plain(item())
        except Exception:                          # noqa: BLE001
            pass
    return str(value)


class EventTap:
    """Bounded history plus a live summary of the current sweep."""

    def __init__(self, capacity: int = 4000, keep_points: int = 200):
        self._lock = threading.Lock()
        self._events: collections.deque = collections.deque(maxlen=capacity)
        self._seq = 0
        self.points: collections.deque = collections.deque(
            maxlen=keep_points)
        self.errors: collections.deque = collections.deque(maxlen=50)
        self.files: list[str] = []
        self.columns: tuple = ()
        self.progress: Optional[dict] = None
        self.state = "idle"          # idle | running | paused | finished
        self.dimensions = 0
        self.planned_points = 0
        self.started_at: Optional[float] = None
        self.finished_at: Optional[float] = None
        self.last_finish: Optional[dict] = None

    # ---- recording ---------------------------------------------------
    def record(self, event: Any) -> None:
        """Called from the GUI event pump. Never raises."""
        try:
            self._record(event)
        except Exception:                          # noqa: BLE001
            pass

    def _record(self, event: Any) -> None:
        name = type(event).__name__
        if isinstance(event, tuple):               # ('setget_row', ...)
            name = str(event[0]) if event else "tuple"
            body = {"data": plain(list(event[1:]))}
        elif dataclasses.is_dataclass(event):
            body = {k: plain(v)
                    for k, v in dataclasses.asdict(event).items()}
        else:
            body = {"repr": str(event)}
        with self._lock:
            self._seq += 1
            entry = {"seq": self._seq, "event": name, "t": time.time()}
            entry.update(body)
            self._events.append(entry)
            self._summarise(name, entry)

    def _summarise(self, name: str, entry: dict) -> None:
        if name == "SweepStarted":
            self.state = "running"
            self.started_at = entry["t"]
            self.finished_at = None
            self.columns = tuple(entry.get("columns") or ())
            self.dimensions = entry.get("dimensions") or 0
            self.planned_points = entry.get("planned_points") or 0
            self.points.clear()
            self.errors.clear()
            self.files = []
            self.progress = None
            self.last_finish = None
        elif name == "FileOpened":
            path = entry.get("path") or ""
            if path and path not in self.files:
                self.files.append(path)
        elif name == "PointMeasured":
            self.points.append({"row": entry.get("row"),
                                "axis_values": entry.get("axis_values"),
                                "walk": entry.get("walk")})
        elif name == "Progress":
            self.progress = {k: entry.get(k) for k in
                             ("done", "total", "eta_seconds",
                              "elapsed_seconds")}
        elif name == "SweepPaused":
            self.state = "paused"
        elif name == "SweepResumed":
            self.state = "running"
        elif name == "SweepError":
            self.errors.append({k: entry.get(k) for k in
                                ("where", "message", "fatal", "crucial")})
        elif name == "SweepFinished":
            self.state = "finished"
            self.finished_at = entry["t"]
            self.last_finish = {"stopped": entry.get("stopped"),
                                "points": entry.get("points")}

    # ---- reading -----------------------------------------------------
    @property
    def sequence(self) -> int:
        with self._lock:
            return self._seq

    def since(self, seq: int = 0, limit: int = 200,
              kinds: Optional[tuple] = None) -> dict:
        """Events numbered above ``seq``, oldest first."""
        with self._lock:
            events = [e for e in self._events if e["seq"] > int(seq or 0)]
            oldest = self._events[0]["seq"] if self._events else 0
            latest = self._seq
        if kinds:
            wanted = {str(k) for k in kinds}
            events = [e for e in events if e["event"] in wanted]
        truncated = len(events) > limit
        out = {"events": events[:limit], "latest": latest}
        if truncated:
            out["next"] = out["events"][-1]["seq"] if out["events"] else seq
            out["more"] = True
        if seq and oldest > int(seq) + 1:
            out["dropped_before"] = oldest
        return out

    def last_points(self, count: int = 5) -> list:
        with self._lock:
            return list(self.points)[-int(max(count, 0)):]

    def snapshot(self, points: int = 3) -> dict:
        """The fixed-size answer to 'what is going on?'."""
        with self._lock:
            out = {
                "state": self.state,
                "dimensions": self.dimensions,
                "planned_points": self.planned_points,
                "columns": list(self.columns),
                "files": list(self.files),
                "current_file": self.files[-1] if self.files else None,
                "progress": dict(self.progress) if self.progress else None,
                "errors": list(self.errors)[-5:],
                "sequence": self._seq,
            }
            if self.started_at:
                end = self.finished_at or time.time()
                out["elapsed_seconds"] = round(end - self.started_at, 1)
            if self.last_finish:
                out["finished"] = dict(self.last_finish)
            out["last_points"] = list(self.points)[-int(max(points, 0)):]
        return out
