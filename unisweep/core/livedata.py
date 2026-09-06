"""In-memory store of the running sweep's data for live plotting.

The legacy plots re-read the growing CSV from disk on every animation frame;
here the GUI's event pump feeds measured rows straight into this store and
the plot panel renders from memory. The CSV on disk stays the archival copy.

Robust to live trajectory edits: points are stored as scatter data, so a map
stays correct even if the grid was retuned mid-sweep (rendering interpolates
onto the current point cloud instead of assuming a fixed lattice).
"""

from __future__ import annotations

import threading
from typing import Optional

import numpy as np

__all__ = ["LiveData", "LiveMaps"]


class LiveData:

    def __init__(self):
        self._lock = threading.Lock()
        self.columns: tuple[str, ...] = ()
        self.dimensions = 1
        self.rows: list[tuple] = []
        self.walks: list[int] = []     # innermost walk per row
        self.axis_points: list[tuple] = []     # (v1..vN) per measured row
        self.skipped: list[tuple] = []         # condition-excluded points
        self.current_file = ""
        self._scan_marks: list[int] = [0]      # row index where a file began

    # -----------------------------------------------------------------
    def reset(self, columns: tuple[str, ...], dimensions: int) -> None:
        with self._lock:
            self.columns = tuple(columns)
            self.dimensions = dimensions
            self.rows.clear()
            self.walks.clear()
            self.axis_points.clear()
            self.skipped.clear()
            self._scan_marks = [0]

    def new_file(self, path: str) -> None:
        """A new data file started — that is exactly the legacy boundary of
        one 'scan': files rotate per master point (2-D) / per (master,
        slave) point (3-D), so rows since the last mark form the current
        inner sweep."""
        with self._lock:
            self.current_file = path
            n = len(self.rows)
            if not self._scan_marks or self._scan_marks[-1] != n:
                self._scan_marks.append(n)

    def add_row(self, row: tuple, axis_values: tuple,
                walk: int = 1) -> None:
        with self._lock:
            self.rows.append(row)
            self.walks.append(int(walk))
            self.axis_points.append(axis_values)

    def add_skipped(self, axis_values: tuple) -> None:
        with self._lock:
            self.skipped.append(axis_values)

    # -----------------------------------------------------------------
    def scan_start(self) -> int:
        """Row index where the current data file (= current scan) begins."""
        with self._lock:
            return self._scan_marks[-1] if self._scan_marks else 0

    def column(self, name: str, last: Optional[int] = None,
               start: int = 0) -> np.ndarray:
        """Numeric values of one column (NaN where unparseable)."""
        with self._lock:
            try:
                idx = self.columns.index(name)
            except ValueError:
                return np.array([])
            rows = self.rows[start:]
            rows = rows[-last:] if last else rows
            out = np.empty(len(rows))
            for i, r in enumerate(rows):
                try:
                    out[i] = float(r[idx])
                except (TypeError, ValueError):
                    out[i] = np.nan
            return out

    def xy(self, xcol: str, ycol: str, last: Optional[int] = None,
           scan_only: bool = False, walk: Optional[int] = None):
        """walk=1 keeps only rows of the first innermost walk — the
        'show 1/n of the data along the fast axis' plot option."""
        start = self.scan_start() if scan_only else 0
        x = self.column(xcol, last, start)
        y = self.column(ycol, last, start)
        if walk is not None:
            with self._lock:
                tags = self.walks[start:start + len(x)]
            keep = [i for i, w in enumerate(tags) if w == walk]
            x = [x[i] for i in keep if i < len(x)]
            y = [y[i] for i in keep if i < len(y)]
        return x, y

    def map_arrays(self, xcol: str, ycol: str, zcol: str,
                   plane_axis: Optional[int] = None,
                   plane_value=None):
        """Scatter triplet for map rendering (x, y, z), NaN-filtered.

        For 3-D sweeps pass ``plane_axis`` (0-based axis index, normally the
        master axis 0) and ``plane_value``: a float selects that plane,
        ``"latest"``/None the most recent one — this is what lets the GUI
        flip between the stacked 2-D maps on the go.
        """
        x = self.column(xcol)
        y = self.column(ycol)
        z = self.column(zcol)
        n = min(len(x), len(y), len(z))
        x, y, z = x[:n], y[:n], z[:n]
        with self._lock:
            pts = self.axis_points[:n]
        if plane_axis is not None and pts:
            axis_vals = np.array([p[plane_axis] if plane_axis < len(p)
                                  else np.nan for p in pts])
            if plane_value is None or plane_value == "latest":
                target = axis_vals[~np.isnan(axis_vals)][-1] \
                    if np.isfinite(axis_vals).any() else np.nan
            else:
                target = float(plane_value)
            tol = self._plane_tol(axis_vals)
            sel = np.abs(axis_vals - target) <= tol
            x, y, z = x[sel], y[sel], z[sel]
        ok = ~(np.isnan(x) | np.isnan(y))
        return x[ok], y[ok], z[ok]

    @staticmethod
    def _plane_tol(axis_vals: np.ndarray) -> float:
        uniq = np.unique(axis_vals[np.isfinite(axis_vals)])
        if len(uniq) < 2:
            return 1e-9
        return float(np.min(np.diff(uniq))) / 2.0

    def plane_values(self, plane_axis: int = 0) -> list[float]:
        """Distinct values of an axis in order of first appearance."""
        with self._lock:
            pts = list(self.axis_points)
        seen: list[float] = []
        for p in pts:
            if plane_axis >= len(p):
                continue
            v = round(float(p[plane_axis]), 9)
            if not any(abs(v - s) <= 1e-9 * max(abs(v), 1.0) for s in seen):
                seen.append(v)
        return seen

    def __len__(self) -> int:
        with self._lock:
            return len(self.rows)


class LiveMaps:
    """Map matrices assembled from :class:`events.MapRowCommitted` rows.

    Mirrors the legacy mapper exactly: the columns are the walk-concatenated
    inner grid frozen per iteration, and one row is appended per outer point
    — the plots consume these matrices instead of re-binning raw x/y/z
    points. For 3-D sweeps each master point is a separate iteration
    ("plane"); iteration -1 means the newest one.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self.reads: tuple[str, ...] = ()
        # read -> list of iterations; each iteration:
        #   {"grid": tuple, "rows": [np.array], "labels": [float],
        #    "master": float, "iteration": int}
        self._maps: dict[str, list[dict]] = {}

    def reset(self, reads) -> None:
        with self._lock:
            self.reads = tuple(reads)
            self._maps = {r: [] for r in self.reads}

    def on_row(self, event) -> None:
        with self._lock:
            for read, row in event.read_rows.items():
                iterations = self._maps.setdefault(read, [])
                if not iterations or                         iterations[-1]["iteration"] != event.iteration:
                    iterations.append({"grid": tuple(event.grid),
                                       "rows": [], "labels": [],
                                       "master": event.master_value,
                                       "iteration": event.iteration})
                it = iterations[-1]
                row = np.asarray(row, dtype=float)
                n = len(it["grid"])
                if len(row) < n:
                    row = np.concatenate([row, np.full(n - len(row), np.nan)])
                it["rows"].append(row[:n])
                it["labels"].append(float(event.row_value))

    # -----------------------------------------------------------------
    def iteration_labels(self, read: str) -> list[str]:
        with self._lock:
            its = self._maps.get(read, [])
            return [f"#{it['iteration']}  ax1={it['master']:g}"
                    for it in its]

    def matrix(self, read: str, iteration: int = -1):
        """(grid, row_labels, 2-D array) of one iteration, or None."""
        with self._lock:
            its = self._maps.get(read, [])
            if not its:
                return None
            if iteration == -1 or iteration >= len(its):
                it = its[-1]
            else:
                it = its[iteration]
            if not it["rows"]:
                return None
            return (np.asarray(it["grid"]), list(it["labels"]),
                    np.vstack(it["rows"]))

    def has_data(self, read: str) -> bool:
        with self._lock:
            its = self._maps.get(read, [])
            return bool(its and its[-1]["rows"])
