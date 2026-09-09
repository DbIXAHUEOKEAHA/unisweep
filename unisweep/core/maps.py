"""Map spreadsheets for 2-D / 3-D sweeps (legacy ``mapper2D`` / ``mapper3D``).

Alongside the row-wise data CSVs, every read parameter also gets a *matrix*
spreadsheet in the legacy location and layout, so all downstream tooling
keeps working:

2-D sweep::

    <core>/<YYMMDD>/2d_maps/tables/<base>_<idx>/<idx>_<param>_map.csv

    "<axis1 name> / <axis2 name>", <inner grid values...>
    <master value>, <param interpolated onto the grid...>
    <master value>, ...

3-D sweep — one 2-D map per master point ("iteration")::

    .../2d_maps/tables/<base>_<idx>/<axis1 name>_<master value>/
        <idx>_<param>_map_<iteration>.csv

    with the header "<axis2 name> / <axis3 name>" and one line per slave
    point. A PNG of every table is kept up to date in the mirrored
    ``2d_maps/images`` tree, and for 3-D sweeps a GIF over the iterations is
    written to ``images/<base>_<idx>/gifs`` (as ``data2gif`` did; z colour
    limits are held fixed across iterations like ``stack_iteration``).

Differences from legacy, on purpose:

* rows are interpolated onto a grid *frozen when the file is created*, so a
  live-edited trajectory can't silently shift the columns mid-file (a fresh
  grid is taken for each 3-D iteration);
* ':' is stripped from directory names too, not only file names, so VISA
  addresses can't produce invalid Windows paths;
* PNG/GIF rendering runs in one background worker with coalescing (only the
  newest state of each file is rendered), so a fast sweep is never stalled
  by 300-dpi rendering.

Everything here is driven by the engine thread; the worker only renders.
"""

from __future__ import annotations

import os
import queue
import threading
from typing import Optional, Sequence

import numpy as np

from .config import LiveProgram
from .filenames import fix_unicode, unify_filename

__all__ = ["MapWriter", "index_ticks"]


def day_dir_for(data_path: str) -> str:
    """The ``<YYMMDD>`` folder a data file belongs to.

    Data files live in ``<YYMMDD>/data_files``; the map tables and images
    live in ``<YYMMDD>/2d_maps``, a *sibling* of it. Anything that wants
    to find one from the other has to step up two levels, and getting
    that wrong is silent — the walk simply finds nothing. So there is one
    implementation, and both the map writer and the GUI call it.
    """
    return os.path.dirname(os.path.dirname(data_path))


def _safe(name: str) -> str:
    return name.replace(":", "").replace("/", "-").replace("\\", "-")


def _axis_name(ax) -> str:
    return f"{ax.device}.{ax.parameter}"


def _forward_points(ax) -> np.ndarray:
    """The planned forward walk of an axis (same clamping as the runner)."""
    if ax.manual_points is not None:
        return np.asarray(ax.manual_points, dtype=float)
    step = ax.step_size(False)
    if step <= 0 or not np.isfinite(step):
        return np.array([ax.start, ax.stop], dtype=float)
    sign = 1.0 if ax.stop >= ax.start else -1.0
    out = [float(ax.start)]
    v = float(ax.start)
    while sign * (ax.stop - (v + sign * step)) > step * 1e-9:
        v += sign * step
        out.append(v)
    if np.isclose(out[-1], ax.stop, rtol=1e-9, atol=1e-12):
        out[-1] = float(ax.stop)       # snap the dust onto the endpoint
    else:
        out.append(float(ax.stop))
    return np.array(out, dtype=float)


def _monotonic_segments(arr: np.ndarray,
                        turn_eps: float = 0.0) -> list[slice]:
    """Slices of maximal monotonic runs (direction changes = walk turns).

    ``turn_eps`` adds hysteresis: a reversal only counts once the values
    have retreated more than ``turn_eps`` from the running extremum.
    Measured readbacks carry noise — without this, gauss-level jitter on a
    flat stretch fragments the row into micro-segments and the segment
    pairing then discards the real data (the overnight field-map failure).
    A real snake turn spans the whole axis; noise never exceeds one grid
    step, so ``turn_eps`` = one grid step separates them cleanly. With
    ``turn_eps=0`` the behaviour is the exact strict split (used for the
    planned grid itself, which is noise-free).
    """
    n = len(arr)
    if n <= 1:
        return [slice(0, n)]
    out = []
    start = 0
    direction = 0
    ext = float(arr[0])
    ext_i = 0
    for i in range(1, n):
        v = float(arr[i])
        if direction == 0:
            if abs(v - ext) > turn_eps or (turn_eps == 0.0 and v != ext):
                direction = 1 if v > ext else -1
                ext, ext_i = v, i
            continue
        if (v - ext) * direction >= 0:
            ext, ext_i = v, i                 # still advancing
        elif (ext - v) * direction > turn_eps:
            out.append(slice(start, ext_i + 1))
            start = ext_i + 1
            direction = -direction
            ext, ext_i = v, i
    out.append(slice(start, n))
    return out


def _walk_grid(ax, uniform: bool = False) -> np.ndarray:
    """Forward grid concatenated over walks, alternating direction and
    dropping the duplicated turning point — exactly the legacy uniform grid
    (``grid[::±1][walk % 2:]``)."""
    base = _forward_points(ax)
    if uniform and len(base) > 1:
        base = np.linspace(float(base[0]), float(base[-1]), len(base))
    parts = []
    for walk in range(ax.effective_walks()):
        g = base if walk % 2 == 0 else base[::-1]
        if walk % 2 == 1:
            g = g[1:]
        parts.append(g)
    return np.concatenate(parts) if parts else base


class _Renderer(threading.Thread):
    """Background PNG/GIF renderer with per-file coalescing."""

    def __init__(self):
        super().__init__(daemon=True, name="unisweep-maps")
        self._q: "queue.Queue" = queue.Queue()
        self._pending: dict[str, tuple] = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self.start()

    def submit_png(self, table_path: str, vmin, vmax, labels) -> None:
        with self._lock:
            self._pending[table_path] = (vmin, vmax, labels)
        self._q.put(("png", table_path))

    def submit_gif(self, image_dir: str, param: str) -> None:
        self._q.put(("gif", (image_dir, param)))

    def close(self, timeout: float = 15.0) -> None:
        self._q.put(("stop", None))
        self.join(timeout)

    # -----------------------------------------------------------------
    def run(self) -> None:
        while True:
            kind, payload = self._q.get()
            if kind == "stop":
                return
            try:
                if kind == "png":
                    with self._lock:
                        job = self._pending.pop(payload, None)
                    if job is not None:
                        self._render_png(payload, *job)
                elif kind == "gif":
                    self._render_gif(*payload)
            except Exception:                     # noqa: BLE001 - best effort
                pass

    @staticmethod
    def _image_path(table_path: str) -> str:
        parts = list(os.path.normpath(table_path).split(os.path.sep))
        parts[parts.index("tables")] = "images"
        parts[-1] = os.path.splitext(parts[-1])[0] + ".png"
        return os.path.sep.join(parts)

    def _render_png(self, table_path, vmin, vmax, labels) -> None:
        render_table_png(table_path, vmin, vmax, labels)

    def _render_gif(self, image_dir: str, param: str) -> None:
        try:
            import imageio.v2 as imageio
        except ImportError:
            return
        files = []
        for root, _dirs, names in os.walk(image_dir):
            if "gifs" in root:
                continue
            for n in names:
                if n.endswith(".png") and f"_{_safe(param)}_map_" in n:
                    try:
                        it = int(n.rsplit("_", 1)[-1][:-4])
                    except ValueError:
                        continue
                    files.append((it, os.path.join(root, n)))
        if len(files) < 2:
            return
        files.sort()
        gif_dir = os.path.join(image_dir, "gifs")
        os.makedirs(gif_dir, exist_ok=True)
        out = os.path.join(gif_dir, f"{_safe(param)}_map.gif")
        frames = [imageio.imread(p) for _, p in files]
        imageio.mimsave(out, frames, duration=0.5)


def render_table_png(table_path, vmin, vmax, labels,
                     title: str = "", cmap: str = "viridis",
                     ztransform: str = "") -> Optional[str]:
    """Render (or RE-render) the PNG for one saved map table — the same
    output the sweep produces, so applying a plot window's settings to
    the saved images is a matter of calling this again with new style.

    ``cmap`` and ``ztransform`` mirror what the plot window draws with. A
    saved image that ignored them was the bug behind "I applied the
    settings and the colours did not change": the limits, labels and
    title were re-applied, the colormap was hardcoded.
    """
    from .expr import apply_transform
    import matplotlib
    matplotlib.use("Agg", force=False)
    import matplotlib.pyplot as plt

    rows, header, grid = _read_table(table_path)
    if rows is None or not len(rows):
        return None
    y = rows[:, 0]
    # transform first: auto limits have to be taken from the values that
    # are actually drawn, not from the raw table
    z = apply_transform(ztransform, rows[:, 1:])
    image_path = _Renderer._image_path(table_path)
    os.makedirs(os.path.dirname(image_path), exist_ok=True)
    fig, ax = plt.subplots(figsize=(6, 4.5))
    if vmin is None or vmax is None:
        vmin = np.nanmin(z) if np.isfinite(z).any() else 0
        vmax = np.nanmax(z) if np.isfinite(z).any() else 1
    m = ax.pcolormesh(np.ma.masked_invalid(z), cmap=cmap or "viridis",
                      vmin=vmin, vmax=vmax, shading="flat")
    cb = fig.colorbar(m, ax=ax)
    cb.set_label(labels.get("param", ""))
    ax.set_title(title or f"Map {labels.get('param', '')}", fontsize=10)
    ax.set_xlabel(labels.get("x", ""))
    ax.set_ylabel(labels.get("y", ""))
    index_ticks(ax, grid, y)
    try:
        fig.savefig(image_path, dpi=300, bbox_inches="tight")
    finally:
        plt.close(fig)
    return image_path


def restyle_saved_images(data_dir: str, param: str, vmin=None, vmax=None,
                         labels: Optional[dict] = None,
                         title: str = "", cmap: str = "viridis",
                         ztransform: str = "") -> int:
    """Apply a plot window's settings to every SAVED image of ``param``
    under ``data_dir`` (tables re-rendered to PNG; iteration GIFs
    rebuilt when present). Returns how many PNGs were re-rendered."""
    labels = dict(labels or {})
    labels.setdefault("param", param)
    tag = f"_{_safe(param)}_map"
    tables_root = os.path.join(data_dir, "2d_maps", "tables")
    n = 0
    gif_dirs = set()
    for root, _dirs, names in os.walk(tables_root):
        for name in names:
            if tag in name and name.endswith(".csv"):
                out = render_table_png(os.path.join(root, name),
                                       vmin, vmax, labels, title=title,
                                       cmap=cmap, ztransform=ztransform)
                if out:
                    n += 1
                    gif_dirs.add(os.path.dirname(os.path.dirname(out)))
    r = _Renderer.__new__(_Renderer)      # gif logic without a thread
    for d in gif_dirs:
        try:
            r._render_gif(d, param)
        except Exception:                 # noqa: BLE001
            pass
    return n

def _read_table(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            lines = [ln.strip() for ln in fh if ln.strip()]
    except OSError:
        return None, None, None
    if not lines:
        return None, None, None
    header = lines[0].split(",")
    grid = np.array([float(v) for v in header[1:]]) if len(header) > 1 \
        else np.array([])
    rows = []
    for ln in lines[1:]:
        try:
            rows.append([float(v) if v not in ("", "nan") else np.nan
                         for v in ln.split(",")])
        except ValueError:
            continue
    width = len(grid) + 1
    rows = [r + [np.nan] * (width - len(r)) if len(r) < width else r[:width]
            for r in rows]
    return (np.array(rows, dtype=float) if rows else np.empty((0, width)),
            header, grid)


def index_ticks(ax, xvals, yvals, max_ticks: int = 6) -> None:
    """Value-labelled ticks on an index-space pcolormesh (add_ticks)."""
    for vals, setter, lbl_setter, rot in (
            (np.asarray(xvals), ax.set_xticks, ax.set_xticklabels, 30),
            (np.asarray(yvals), ax.set_yticks, ax.set_yticklabels, 0)):
        n = len(vals)
        if n == 0:
            continue
        stride = max(n // max_ticks, 1)
        ticks = np.arange(n)[::stride] + 0.5
        labels = [f"{v:.3g}" for v in vals[::stride]]
        setter(ticks)
        lbl_setter(labels, rotation=rot, fontsize=7)


class MapWriter:
    """Collects measured points and writes the legacy map spreadsheets.

    Driven by the engine:

    * :meth:`add_point` / :meth:`add_skipped` per innermost point;
    * :meth:`commit_row` when the innermost walks of one outer point finish;
    * :meth:`new_iteration` when the 3-D master steps;
    * :meth:`finish` at sweep end.
    """

    def __init__(self, core_dir: str, live: LiveProgram,
                 loop_axes: Sequence[int], reads: Sequence[str],
                 data_path: str, interpolated: bool = True,
                 images: bool = True, write_files: bool = True,
                 style: str = "grid", uniform: bool = False):
        self.core_dir = core_dir
        self.live = live
        self.loop_axes = list(loop_axes)
        self.inner = self.loop_axes[-1]
        self.row_axis = self.loop_axes[-2]
        self.master_axis = self.loop_axes[-3] if len(self.loop_axes) >= 3 \
            else None
        self.reads = list(reads)
        self.interpolated = interpolated
        self.uniform = uniform
        self.style = style if style in ("grid", "xyz", "both") else "grid"
        self.write_files = write_files
        self.grid_files = write_files and self.style in ("grid", "both")
        self.xyz_files = write_files and self.style in ("xyz", "both")
        self._xyz_handles: dict[str, object] = {}
        self.images = images and self.grid_files

        base = os.path.basename(data_path)
        stem = os.path.splitext(base)[0]
        self.index = 0
        if "-" in stem and stem[stem.rfind("-") + 1:].isdigit():
            self.index = int(stem[stem.rfind("-") + 1:])
            stem = stem[: stem.rfind("-")]
        self.base = unify_filename(stem)
        day_dir = day_dir_for(data_path)
        self.root = os.path.join(day_dir, "2d_maps", "tables",
                                 f"{self.base}_{self.index}")
        self.image_root = os.path.join(day_dir, "2d_maps", "images",
                                       f"{self.base}_{self.index}")
        self.iteration = 0
        self._grid: Optional[np.ndarray] = None
        self._files_created = False
        self._inner_vals: list[float] = []
        self._read_vals: dict[str, list[float]] = {r: [] for r in self.reads}
        self._zmin: dict[str, float] = {}
        self._zmax: dict[str, float] = {}
        self._renderer = _Renderer() if images else None

    # ---------------- naming -----------------------------------------
    def _dir(self) -> str:
        prog = self.live.get()
        if self.master_axis is None:
            return self.root
        name = _safe(_axis_name(prog.axes[self.master_axis]))
        return os.path.join(self.root,
                            f"{name}_{self._master_value:g}")

    def _table(self, read: str) -> str:
        suffix = f"_map_{self.iteration}" if self.master_axis is not None \
            else "_map"
        return fix_unicode(os.path.join(
            self._dir(), f"{self.index}_{_safe(read)}{suffix}.csv"))

    def _labels(self, read: str) -> dict:
        prog = self.live.get()
        return {"param": read,
                "x": _axis_name(prog.axes[self.inner]),
                "y": _axis_name(prog.axes[self.row_axis])}

    # ---------------- collection --------------------------------------
    def add_point(self, inner_value: float, read_values: Sequence,
                  axis_values: Optional[Sequence] = None) -> None:
        self._inner_vals.append(float(inner_value))
        vals = []
        for read, value in zip(self.reads, read_values):
            try:
                v = float(value)
            except (TypeError, ValueError):
                v = np.nan
            self._read_vals[read].append(v)
            vals.append(v)
        if self.xyz_files and axis_values is not None:
            self._write_xyz(axis_values, vals)

    # ---------------- XYZ long-format files ----------------------------
    def _xyz_path(self, read: str) -> str:
        directory = os.path.join(fix_unicode(self._xyz_dir()), "xyz")
        return os.path.join(directory,
                            f"{self.base}_xyz_{_safe(read)}.csv")

    def _xyz_dir(self) -> str:
        """The map day-directory WITHOUT the per-master suffix: the xyz
        file is one continuous file for the whole sweep, so it must not
        rotate with the 3-D master the way the worksheet tables do."""
        return self.root

    def _write_xyz(self, axis_values: Sequence,
                   read_values: list) -> None:
        """One continuous file per read parameter: a row per measured point
        with the loop-axis values as X(,Y),Z-like columns — never
        re-gridded, raw coordinates as measured (readback for sweepable
        axes). 3-D sweeps stay in ONE file with the master as the first
        column."""
        prog = self.live.get()
        if not self._xyz_handles:
            os.makedirs(os.path.join(fix_unicode(self._xyz_dir()), "xyz"),
                        exist_ok=True)
            header = ",".join([_axis_name(prog.axes[i])
                               for i in self.loop_axes])
            for read in self.reads:
                fh = open(self._xyz_path(read), "a", encoding="utf-8")
                if fh.tell() == 0:
                    fh.write(header + f",{read}")
                self._xyz_handles[read] = fh
        coords = ",".join(f"{float(axis_values[i]):g}"
                          for i in self.loop_axes)
        for read, v in zip(self.reads, read_values):
            fh = self._xyz_handles[read]
            fh.write(f"\n{coords},"
                     + (f"{v:g}" if np.isfinite(v) else "nan"))
            fh.flush()

    def add_skipped(self, inner_value: float) -> None:
        self._inner_vals.append(float(inner_value))
        for read in self.reads:
            self._read_vals[read].append(np.nan)

    # ---------------- committing --------------------------------------
    def _ensure_files(self) -> None:
        if self._files_created:
            return
        prog = self.live.get()
        self._grid = _walk_grid(prog.axes[self.inner], uniform=self.uniform)
        if not self.grid_files:
            self._files_created = True
            return
        directory = fix_unicode(self._dir())
        os.makedirs(directory, exist_ok=True)
        if self.master_axis is None:
            head = (f"{_axis_name(prog.axes[self.row_axis])} / "
                    f"{_axis_name(prog.axes[self.inner])}")
        else:
            head = (f"{_axis_name(prog.axes[self.row_axis])} / "
                    f"{_axis_name(prog.axes[self.inner])}")
        header = ",".join([head] + [f"{v:g}" for v in self._grid])
        for read in self.reads:
            with open(self._table(read), "w", encoding="utf-8") as fh:
                fh.write(header)
        self._files_created = True

    def _row_onto_grid(self, values: list[float]) -> np.ndarray:
        """Map the collected samples of one row onto the frozen grid.

        * **index mode** (``interpolated=False`` and non-uniform grid):
          sample k lands in grid cell k — exact for stepwise sweeps.
        * **value mode**: nearest-by-value *per walk segment*. The
          walk-concatenated grid is non-monotonic (0→1→0), so forward and
          backward passes are matched segment-by-segment — a global
          nearest lookup would conflate the two directions and destroy
          hysteresis. NaN samples (condition holes, NaN reads) stay NaN in
          their own cells and are never smeared onto neighbours; a walk
          that aborted early leaves its remaining cells NaN.
        """
        n = len(self._grid)
        x = np.asarray(self._inner_vals, dtype=float)
        y = np.asarray(values, dtype=float)
        by_value = self.interpolated or self.uniform
        if not by_value or len(x) < 2:
            out = np.full(n, np.nan)
            out[: min(len(y), n)] = y[:n]
            return out
        out = np.full(n, np.nan)
        garr = np.asarray(self._grid, dtype=float)
        gd = np.abs(np.diff(garr))
        step_all = float(np.median(gd[gd > 0])) if (gd > 0).any() else 0.0
        grid_segments = _monotonic_segments(garr)
        sample_segments = _monotonic_segments(x, turn_eps=step_all)
        for g_sl, s_sl in zip(grid_segments, sample_segments):
            xs, ys = x[s_sl], y[s_sl]
            keep = np.isfinite(xs)
            xs, ys = xs[keep], ys[keep]
            if len(xs) == 0:
                continue
            g = np.asarray(self._grid[g_sl], dtype=float)
            if len(xs) == 1:
                xs_s = xs
                idx = np.zeros(len(g), dtype=int)
            else:
                order = np.argsort(xs)
                xs_s, ys_s = xs[order], ys[order]
                pos = np.searchsorted(xs_s, g).clip(1, len(xs_s) - 1)
                left, right = xs_s[pos - 1], xs_s[pos]
                idx = np.where(np.abs(g - left) <= np.abs(right - g),
                               pos - 1, pos)
                ys = ys_s
            vals = ys[idx].astype(float)
            # VALUE LOCALITY: a cell farther from every sample than ~1.5
            # grid steps was never measured — it stays NaN. Without this,
            # a walk that stalled after a handful of samples had its few
            # flat values smeared across the WHOLE row, fabricating a
            # complete-looking (and wrong) map line and hiding the fault.
            if len(g) > 1:
                step_g = np.median(np.abs(np.diff(g)))
                radius = max(step_g * 1.5, 1e-30)
                vals[np.abs(g - xs_s[idx]) > radius] = np.nan
            out[g_sl] = vals
        return out

    def commit_row(self, row_value: float, master_value: float = 0.0):
        """One map line per read parameter (inner walks finished).

        Returns ``(grid, {read: row values})`` so the engine can hand the
        freshly built row to the live plots — the GUI maps are assembled by
        exactly the same walk-aware row logic as the spreadsheets, never by
        re-binning scattered x/y/z points.
        """
        if not self._inner_vals:
            return None
        self._master_value = master_value
        self._ensure_files()
        rows_out: dict[str, tuple] = {}
        for read in self.reads:
            row = self._row_onto_grid(self._read_vals[read])
            rows_out[read] = tuple(float(v) for v in row)
            if np.isfinite(row).any():
                lo = float(np.nanmin(row))
                hi = float(np.nanmax(row))
                self._zmin[read] = min(self._zmin.get(read, lo), lo)
                self._zmax[read] = max(self._zmax.get(read, hi), hi)
            if not self.grid_files:
                continue
            line = ",".join([f"{row_value:g}"] +
                            [f"{v:g}" if np.isfinite(v) else "nan"
                             for v in row])
            path = self._table(read)
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(f"\n{line}")
            if self._renderer is not None:
                vmin = self._zmin.get(read) if self.master_axis is not None \
                    else None
                vmax = self._zmax.get(read) if self.master_axis is not None \
                    else None
                self._renderer.submit_png(path, vmin, vmax,
                                          self._labels(read))
        self._inner_vals.clear()
        for read in self.reads:
            self._read_vals[read].clear()
        return (tuple(float(v) for v in self._grid), rows_out)

    def new_iteration(self) -> None:
        """3-D: the master stepped — start a fresh map file set."""
        if self.master_axis is None:
            return
        if self._renderer is not None and self.grid_files \
                and self._files_created:
            for read in self.reads:
                self._renderer.submit_gif(self.image_root, read)
        self.iteration += 1
        self._files_created = False
        self._grid = None

    # `close` is the friendlier name; `finish` kept for the engine
    def finish(self) -> None:
        for fh in self._xyz_handles.values():
            try:
                fh.close()
            except OSError:
                pass
        self._xyz_handles.clear()
        if self._renderer is not None:
            if self.master_axis is not None and self._files_created:
                for read in self.reads:
                    self._renderer.submit_gif(self.image_root, read)
            self._renderer.close()

    close = finish
