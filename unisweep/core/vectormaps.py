"""Traces on disk: one read that returns a whole line per point.

The rule is one sentence: **the trace becomes the innermost axis, and
every sweep axis shifts out by one.** Everything else follows from it.

* A **1-D** sweep of traces *is* a map — x is the trace's own axis, y is
  the swept parameter — and it is written in the same worksheet layout a
  2-D sweep of numbers produces, so every script already pointed at those
  files reads it unchanged.
* A **2-D** sweep of traces is a *set* of maps, one per master point:
  exactly the layout a 3-D sweep of numbers produces, folder per master
  and an iteration index in the name.
* A **3-D** sweep of traces needs one more level than the application has
  any way to display. The files get it anyway — folder per master, folder
  per slave, an index per level — because the data is real even when the
  picture is not; the screen falls back to the first element of each
  trace.

Rows are written in measurement order rather than interpolated onto a
grid the way :class:`~unisweep.core.maps.MapWriter` does. There is
nothing to interpolate: the instrument returns the whole line at once, on
its own axis, already aligned. What varies between rows is only which
point of the sweep produced them, and that is the row label.
"""

from __future__ import annotations

import os
import numpy as np
from typing import Optional, Sequence

from .filenames import fix_unicode, unify_filename
from .maps import _Renderer, _axis_name, _safe, day_dir_for
from .vector import VectorSpec, fit_to_length

__all__ = ["VectorMapWriter"]


def _tag(value: float) -> str:
    return f"{float(value):g}"


class VectorMapWriter:
    """Every trace of one read, laid out as maps."""

    def __init__(self, core_dir: str, live, loop_axes: Sequence[int],
                 read: str, spec: VectorSpec, data_path: str,
                 images: bool = True, write_files: bool = True,
                 style: str = "grid", renderer=None, style_source=None):
        self.core_dir = core_dir
        self.live = live
        self.loop_axes = list(loop_axes)
        self.inner = self.loop_axes[-1]
        self.outer = self.loop_axes[:-1]      # master … slave, outermost first
        self.read = read
        self.spec = spec
        self.style = style if style in ("grid", "xyz", "both") else "grid"
        self.write_files = write_files
        self.grid_files = write_files and self.style in ("grid", "both")
        self.xyz_files = write_files and self.style in ("xyz", "both")
        self.images = images and self.grid_files
        self.style_source = style_source

        base = os.path.basename(data_path)
        stem = os.path.splitext(base)[0]
        self.index = 0
        if "-" in stem and stem[stem.rfind("-") + 1:].isdigit():
            self.index = int(stem[stem.rfind("-") + 1:])
            stem = stem[: stem.rfind("-")]
        self.base = unify_filename(stem)
        day = day_dir_for(data_path)
        self.root = os.path.join(day, "2d_maps", "tables",
                                 f"{self.base}_{self.index}")
        self.image_root = os.path.join(day, "2d_maps", "images",
                                       f"{self.base}_{self.index}")
        # the renderer is shared with the scalar maps when there is one:
        # one background thread per sweep, not one per read
        self._renderer = renderer if renderer is not None else (
            _Renderer() if self.images else None)
        self._owns_renderer = renderer is None and self._renderer is not None

        self._counters = [0] * len(self.outer)   # step ordinal per level
        self._outer_now: Optional[tuple] = None
        self._path = ""
        self._rows = 0
        self._xyz = None
        self.iterations = 0
        self.rows_written = 0
        self.last_error = ""

    # ---------------- naming ------------------------------------------
    def _folders(self, outer_values: Sequence[float]) -> str:
        prog = self.live.get()
        path = self.root
        for level, axis_index in enumerate(self.outer):
            name = _safe(_axis_name(prog.axes[axis_index]))
            path = os.path.join(path, f"{name}_{_tag(outer_values[level])}")
        return path

    def _table_name(self) -> str:
        suffix = "".join(f"_{n}" for n in self._counters)
        return f"{self.index}_{_safe(self.read)}_map{suffix}.csv"

    def table_path(self) -> str:
        return self._path

    # ---------------- the map file ------------------------------------
    def _open(self, outer_values: Sequence[float]) -> None:
        directory = fix_unicode(self._folders(outer_values))
        self._path = fix_unicode(os.path.join(directory, self._table_name()))
        self._rows = 0
        if not self.grid_files:
            return
        prog = self.live.get()
        head = (f"{_axis_name(prog.axes[self.inner])} / "
                f"{self.spec.axis_label}")
        header = ",".join([head] + [f"{v:g}" for v in self.spec.axis])
        try:
            os.makedirs(directory, exist_ok=True)
            with open(self._path, "w", encoding="utf-8") as fh:
                fh.write(header)
        except OSError as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"

    def _rotate_if_needed(self, axis_values: Sequence[float]) -> bool:
        """A new file whenever an axis outside the innermost has moved."""
        now = tuple(float(axis_values[i]) for i in self.outer)
        if self._outer_now is not None and now == self._outer_now:
            return False
        if self._outer_now is not None:
            self._close_current()
            for level in range(len(self.outer) - 1, -1, -1):
                if now[level] != self._outer_now[level]:
                    self._counters[level] += 1
                    # an outer step restarts every level under it
                    for deeper in range(level + 1, len(self.outer)):
                        self._counters[deeper] = 0
                    break
        self._outer_now = now
        self.iterations += 1
        self._open(now)
        return True

    def _close_current(self) -> None:
        """Render what is on disk before the next file starts."""
        if self._renderer is not None and self._rows and self._path:
            self._submit_png()

    def _submit_png(self) -> None:
        style = {}
        if self.style_source is not None:
            try:
                style = dict(self.style_source(self.read) or {})
            except Exception:                      # noqa: BLE001
                style = {}
        prog = self.live.get()
        labels = {"param": self.read,
                  "x": self.spec.axis_label,
                  "y": _axis_name(prog.axes[self.inner])}
        self._renderer.submit_png(
            self._path, None, None, labels,
            cmap=style.get("cmap") or "viridis",
            ztransform=style.get("ztransform") or "")

    # ---------------- collecting --------------------------------------
    def add_row(self, inner_value: float, values,
                axis_values: Sequence[float]) -> Optional[dict]:
        """One measured point: a whole row of the map.

        Returns what the GUI needs to draw it — grid, row, row label,
        which map of the set — or None when nothing was written.
        """
        trace = fit_to_length(values, self.spec.length)
        rotated = self._rotate_if_needed(axis_values)
        if self.grid_files and self._path:
            line = ",".join(
                [f"{float(inner_value):g}"]
                + [f"{v:g}" if np.isfinite(v) else "nan" for v in trace])
            try:
                with open(self._path, "a", encoding="utf-8") as fh:
                    fh.write("\n" + line)
                self._rows += 1
                self.rows_written += 1
            except OSError as exc:
                self.last_error = f"{type(exc).__name__}: {exc}"
        if self.xyz_files:
            self._write_xyz(axis_values, trace)
        if self._renderer is not None and self._rows:
            self._submit_png()
        return {"grid": tuple(float(v) for v in self.spec.axis),
                "row": tuple(float(v) for v in trace),
                "row_value": float(inner_value),
                "master_value": float(self._outer_now[0])
                if self._outer_now else 0.0,
                "iteration": max(self.iterations - 1, 0),
                "rotated": rotated}

    def add_skipped(self, inner_value: float,
                    axis_values: Sequence[float]) -> Optional[dict]:
        """A point the condition cut out still holds its place in the map."""
        return self.add_row(inner_value,
                            np.full(self.spec.length, np.nan), axis_values)

    # ---------------- XYZ ---------------------------------------------
    def _xyz_path(self) -> str:
        return os.path.join(fix_unicode(self.root), "xyz",
                            f"{self.base}_xyz_{_safe(self.read)}.csv")

    def _write_xyz(self, axis_values: Sequence[float],
                   trace: np.ndarray) -> None:
        """Long format, with the trace's axis as one more coordinate.

        One line per point of every trace: that is what the format means,
        and it is why it is not the default for a read that returns a
        thousand numbers at a time.
        """
        prog = self.live.get()
        try:
            if self._xyz is None:
                os.makedirs(os.path.dirname(self._xyz_path()), exist_ok=True)
                self._xyz = open(self._xyz_path(), "a", encoding="utf-8")
                if self._xyz.tell() == 0:
                    header = ",".join(
                        [_axis_name(prog.axes[i]) for i in self.loop_axes]
                        + [self.spec.axis_label, self.read])
                    self._xyz.write(header)
            coords = ",".join(f"{float(axis_values[i]):g}"
                              for i in self.loop_axes)
            for x, v in zip(self.spec.axis, trace):
                self._xyz.write(f"\n{coords},{float(x):g},"
                                + (f"{v:g}" if np.isfinite(v) else "nan"))
            self._xyz.flush()
        except OSError as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"

    # ---------------- end ---------------------------------------------
    def finish(self) -> None:
        self._close_current()
        if self._xyz is not None:
            try:
                self._xyz.close()
            except OSError:
                pass
            self._xyz = None
        if self._owns_renderer and self._renderer is not None:
            try:
                self._renderer.close()
            except Exception:                      # noqa: BLE001
                pass

    @property
    def last_render_error(self) -> str:
        return getattr(self._renderer, "last_error", "") \
            if self._renderer is not None else ""
