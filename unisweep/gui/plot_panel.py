"""On-demand plot windows.

No plots are shown when a sweep starts. **New line plot** / **New map**
spawn small independent windows — as many as needed, simultaneously. Each
window has its own settings dialog (gear button or right-click) and closes
with its window.

Line windows plot any two columns of the measured rows, as before.

**Map windows follow the legacy mapper logic exactly**: they render the
matrices assembled by the engine's row builder — the columns are the
walk-concatenated inner grid frozen per iteration, one row is appended per
outer point (interpolated onto the grid, condition holes as NaN), and the
axes are drawn in index space with value-labelled ticks, exactly like the
old ``add_ticks`` figures. Raw x/y/z points are never re-binned. For 3-D
sweeps the plane selector flips between the per-master iterations, or
follows the newest one.

The last-used settings of each kind are remembered (``config/plots.json``)
and pre-fill the next spawned window.
"""

from __future__ import annotations

import dataclasses
import json
import os
import tkinter as tk
from tkinter import colorchooser, ttk
from typing import Optional

import numpy as np
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,
                                               NavigationToolbar2Tk)
from matplotlib.figure import Figure

from ..core.expr import ExprError, SafeExpr, apply_transform
from ..core.livedata import LiveData, LiveMaps
from ..core.maps import index_ticks
from .theme import PALETTE
from .widgets import Tooltip, ValidatedEntry

def _mpl_style() -> dict:
    """Matplotlib rc matching the CURRENT palette (theme can switch)."""
    return {
        "figure.facecolor": PALETTE["surface"],
        "axes.facecolor": PALETTE["bg"],
        "axes.edgecolor": PALETTE["card_edge"],
        "axes.labelcolor": PALETTE["text"],
        "xtick.color": PALETTE["muted"],
        "ytick.color": PALETTE["muted"],
        "text.color": PALETTE["text"],
        "grid.color": PALETTE["card_edge"],
        "axes.grid": True,
        "grid.alpha": 0.4,
        "font.size": 9,
    }

REDRAW_MS = 300
CMAPS = ["viridis", "plasma", "inferno", "magma", "cividis", "jet",
         "seismic", "RdBu_r", "coolwarm", "gray"]


@dataclasses.dataclass
class PlotConfig:
    kind: str = "line"                 # 'line' | 'map'
    title: str = ""
    xcol: str = ""
    ycol: str = ""
    zcol: str = ""                     # map read parameter
    xlabel: str = ""
    ylabel: str = ""
    logx: bool = False
    logy: bool = False
    auto_x: bool = True
    xmin: Optional[float] = None
    xmax: Optional[float] = None
    auto_y: bool = True
    ymin: Optional[float] = None
    ymax: Optional[float] = None
    auto_z: bool = True
    zmin: Optional[float] = None
    zmax: Optional[float] = None
    color: str = PALETTE["accent"]
    marker_size: float = 2.5
    first_walk_only: bool = False      # show 1/n of the fast-axis data
    on_top: bool = True                # this window above all apps
    cmap: str = "viridis"
    xtransform: str = ""
    ytransform: str = ""
    ztransform: str = ""
    plane: str = "latest"              # 3-D: iteration index or 'latest'
    scope: str = "scan"                # line: 'scan' (current file) | 'all'

    def label(self) -> str:
        if self.title:
            return self.title
        if self.kind == "map":
            return f"Map · {self.zcol.split('.')[-1] or '?'}"
        return f"Line · {self.ycol.split('.')[-1] or '?'}"


def _apply_transform(expr_text: str, values: np.ndarray) -> np.ndarray:
    # One implementation, shared with the saved-image renderer: a
    # restyled PNG has to show the same numbers this window does.
    return apply_transform(expr_text, values)


class PlotSettingsDialog(tk.Toplevel):

    def __init__(self, window: "PlotWindow"):
        super().__init__(window)
        self.view = window
        self.cfg = window.config
        self.title("Plot settings")
        self.configure(bg=PALETTE["surface"], padx=14, pady=12)
        self.transient(window)
        self.resizable(False, False)
        c = self.cfg
        r = 0

        def lab(text, row, col=0):
            ttk.Label(self, text=text, style="MutedS.TLabel").grid(
                row=row, column=col, sticky="w", pady=2, padx=(0, 6))

        lab("Title", r)
        self.e_title = ValidatedEntry(self, c.title, validator=str,
                                      allow_empty=True, width=30)
        self.e_title.grid(row=r, column=1, columnspan=3, sticky="w"); r += 1

        if c.kind == "line":
            cols = list(window.manager.columns)
            lab("X column", r)
            self.b_x = ttk.Combobox(self, values=cols, width=26)
            self.b_x.set(c.xcol)
            self.b_x.grid(row=r, column=1, columnspan=3, sticky="w"); r += 1
            lab("Y column", r)
            self.b_y = ttk.Combobox(self, values=cols, width=26)
            self.b_y.set(c.ycol)
            self.b_y.grid(row=r, column=1, columnspan=3, sticky="w"); r += 1
            lab("X label", r)
            self.e_xlabel = ValidatedEntry(self, c.xlabel, validator=str,
                                           allow_empty=True, width=18)
            self.e_xlabel.grid(row=r, column=1, sticky="w")
            lab("Y label", r, 2)
            self.e_ylabel = ValidatedEntry(self, c.ylabel, validator=str,
                                           allow_empty=True, width=18)
            self.e_ylabel.grid(row=r, column=3, sticky="w"); r += 1
            self.v_scope = tk.BooleanVar(value=(c.scope == "scan"))
            self.v_walk1 = tk.BooleanVar(value=c.first_walk_only)
            ttk.Checkbutton(self, text="show only the first walk "
                                       "(1/n of the fast-axis data)",
                            variable=self.v_walk1,
                            style="S.TCheckbutton").grid(
                row=r, column=0, columnspan=4, sticky="w"); r += 1
            ttk.Checkbutton(self, text="show only the current scan "
                                       "(latest inner sweep)",
                            variable=self.v_scope,
                            style="S.TCheckbutton").grid(
                row=r, column=1, columnspan=3, sticky="w"); r += 1
            self.v_logx = tk.BooleanVar(value=c.logx)
            self.v_logy = tk.BooleanVar(value=c.logy)
            ttk.Checkbutton(self, text="log x", variable=self.v_logx,
                            style="S.TCheckbutton").grid(row=r, column=1,
                                                         sticky="w")
            ttk.Checkbutton(self, text="log y", variable=self.v_logy,
                            style="S.TCheckbutton").grid(row=r, column=3,
                                                         sticky="w"); r += 1
            r = self._limits_row("X limits", r, "x", c.auto_x, c.xmin, c.xmax)
            r = self._limits_row("Y limits", r, "y", c.auto_y, c.ymin, c.ymax)
            lab("Line colour", r)
            self.color = c.color
            self.swatch = tk.Label(self, text="   ", bg=self.color,
                                   relief="solid", borderwidth=1)
            self.swatch.grid(row=r, column=1, sticky="w")
            ttk.Button(self, text="Pick…",
                       command=self._pick_color).grid(row=r, column=2,
                                                      sticky="w")
            lab("Marker size", r, 3)
            self.e_marker = ValidatedEntry(self, c.marker_size, width=6)
            self.e_marker.grid(row=r, column=3, sticky="e"); r += 1
            lab("X transform", r)
            self.e_xt = ValidatedEntry(self, c.xtransform, validator=str,
                                       allow_empty=True, width=18)
            self.e_xt.grid(row=r, column=1, sticky="w")
            lab("Y transform", r, 2)
            self.e_yt = ValidatedEntry(self, c.ytransform, validator=str,
                                       allow_empty=True, width=18)
            self.e_yt.grid(row=r, column=3, sticky="w"); r += 1
        else:
            reads = list(window.manager.reads) or \
                list(window.manager.columns)
            lab("Read parameter (z)", r)
            self.b_z = ttk.Combobox(self, values=reads, width=26)
            self.b_z.set(c.zcol)
            self.b_z.grid(row=r, column=1, columnspan=3, sticky="w"); r += 1
            lab("Colormap", r)
            self.b_cmap = ttk.Combobox(self, values=CMAPS, width=12,
                                       state="readonly")
            self.b_cmap.set(c.cmap)
            self.b_cmap.grid(row=r, column=1, sticky="w"); r += 1
            r = self._limits_row("Colour limits", r, "z",
                                 c.auto_z, c.zmin, c.zmax)
            lab("Z transform", r)
            self.e_zt = ValidatedEntry(self, c.ztransform, validator=str,
                                       allow_empty=True, width=18)
            self.e_zt.grid(row=r, column=1, sticky="w"); r += 1

        ttk.Label(self, style="MutedS.TLabel",
                  text="Transforms are expressions in v, e.g. v*1e3, "
                       "log10(abs(v))").grid(
            row=r, column=0, columnspan=4, sticky="w", pady=(2, 6)); r += 1
        self.v_ontop = tk.BooleanVar(value=c.on_top)
        ttk.Checkbutton(self, text="keep this window on top of other "
                                   "applications",
                        variable=self.v_ontop,
                        style="S.TCheckbutton").grid(
            row=r, column=0, columnspan=4, sticky="w", pady=(4, 0)); r += 1
        btns = ttk.Frame(self)
        btns.grid(row=r, column=0, columnspan=4, sticky="e", pady=(6, 0))
        ttk.Button(btns, text="Cancel",
                   command=self.destroy).pack(side="right", padx=4)
        ttk.Button(btns, text="Apply",
                   command=self._apply).pack(side="right", padx=4)
        ttk.Button(btns, text="OK", style="Accent.TButton",
                   command=self._ok).pack(side="right", padx=4)
        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())

    def _limits_row(self, label, r, tag, auto, lo, hi):
        ttk.Label(self, text=label, style="MutedS.TLabel").grid(
            row=r, column=0, sticky="w", pady=2)
        var = tk.BooleanVar(value=auto)
        setattr(self, f"v_auto_{tag}", var)
        ttk.Checkbutton(self, text="auto", variable=var,
                        style="S.TCheckbutton").grid(row=r, column=1,
                                                     sticky="w")
        e_lo = ValidatedEntry(self, "" if lo is None else lo,
                              allow_empty=True, width=9)
        e_hi = ValidatedEntry(self, "" if hi is None else hi,
                              allow_empty=True, width=9)
        e_lo.grid(row=r, column=2, sticky="w")
        e_hi.grid(row=r, column=3, sticky="w")
        setattr(self, f"e_{tag}min", e_lo)
        setattr(self, f"e_{tag}max", e_hi)
        return r + 1

    def _pick_color(self):
        rgb = colorchooser.askcolor(color=self.color, parent=self)
        if rgb and rgb[1]:
            self.color = rgb[1]
            self.swatch.configure(bg=self.color)

    def _apply(self):
        if not self.view.winfo_exists():
            self.destroy()
            return
        c = self.cfg
        c.title = self.e_title.value() or ""
        c.on_top = self.v_ontop.get()
        self.view.set_topmost(c.on_top)
        if c.kind == "line":
            c.xcol, c.ycol = self.b_x.get(), self.b_y.get()
            c.xlabel = self.e_xlabel.value() or ""
            c.ylabel = self.e_ylabel.value() or ""
            c.logx, c.logy = self.v_logx.get(), self.v_logy.get()
            c.first_walk_only = self.v_walk1.get()
            c.auto_x = self.v_auto_x.get()
            c.xmin, c.xmax = self.e_xmin.value(), self.e_xmax.value()
            c.auto_y = self.v_auto_y.get()
            c.ymin, c.ymax = self.e_ymin.value(), self.e_ymax.value()
            c.color = self.color
            c.marker_size = self.e_marker.value() or 2.5
            c.xtransform = self.e_xt.value() or ""
            c.ytransform = self.e_yt.value() or ""
            c.scope = "scan" if self.v_scope.get() else "all"
        else:
            c.zcol = self.b_z.get()
            c.cmap = self.b_cmap.get()
            c.auto_z = self.v_auto_z.get()
            c.zmin, c.zmax = self.e_zmin.value(), self.e_zmax.value()
            c.ztransform = self.e_zt.value() or ""
        # Only now does the config hold what the widgets say. Restyling
        # the saved images any earlier hands the renderer the PREVIOUS
        # colormap, limits and transform — one Apply behind, which from
        # the outside looks exactly like "the settings did nothing".
        if c.kind == "map" and self.view.manager.restyle_images:
            try:
                self.view.manager.restyle_images(c)
            except Exception:                     # noqa: BLE001
                pass
        self.view.refresh_header()
        self.view.mark_dirty()
        self.view.manager.save_templates()

    def _ok(self):
        self._apply()
        self.destroy()


class PlotWindow(tk.Toplevel):
    """One independent plot in its own small window."""

    def __init__(self, manager: "PlotManager", config: PlotConfig):
        super().__init__(manager.master)
        self.manager = manager
        self.config = config
        self._dirty = True
        self.configure(bg=PALETTE["surface"])
        n = len(manager.windows)
        self.geometry(f"620x470+{140 + 40 * (n % 8)}+{110 + 40 * (n % 8)}")
        self.minsize(420, 340)
        self.protocol("WM_DELETE_WINDOW", self._close)
        self._topmost = False
        self.bind("<Map>", self._reassert_topmost)
        if config.on_top:
            self.set_topmost(True)

        head = ttk.Frame(self)
        head.pack(fill="x", padx=8, pady=(8, 0))
        self.title_label = ttk.Label(head, text=config.label())
        self.title_label.pack(side="left")
        b_gear = ttk.Button(head, text="⚙", width=3, command=self.open_settings)
        b_gear.pack(side="right", padx=2)
        Tooltip(b_gear, "Plot settings (right-click on the plot works too)")
        head2 = ttk.Frame(self)
        head2.pack(fill="x", padx=8, pady=(2, 0))
        self.quick_label = ttk.Label(head2, text="z:", style="MutedS.TLabel")
        self.quick_label.pack(side="left")
        self.quick_box = ttk.Combobox(head2, width=22, state="readonly")
        self.quick_box.bind("<<ComboboxSelected>>", self._quick_changed)
        self.quick_box.pack(side="left", padx=(2, 10))
        self.plane_label = ttk.Label(head2, text="plane:",
                                     style="MutedS.TLabel")
        self.plane_box = ttk.Combobox(head2, width=14, state="readonly")
        self.plane_box.bind("<<ComboboxSelected>>", self._plane_changed)
        self._scope_var = tk.BooleanVar(value=(config.scope == "scan"))
        self.scope_check = ttk.Checkbutton(
            head2, text="current scan only", variable=self._scope_var,
            style="S.TCheckbutton", command=self._scope_changed)
        Tooltip(self.scope_check,
                "On: plot only the ongoing inner sweep — the rows of the\n"
                "current data file, which rotates at every master (2D) /\n"
                "slave (3D) step, exactly like the legacy live plot.\n"
                "Off: plot the whole sweep history.")

        with matplotlib.rc_context(_mpl_style()):
            self.figure = Figure(figsize=(4.4, 3.4), dpi=100,
                                 facecolor=PALETTE["surface"])
            self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        widget = self.canvas.get_tk_widget()
        widget.pack(fill="both", expand=True, padx=8, pady=4)
        for seq in ("<Button-3>", "<Control-Button-1>"):
            widget.bind(seq, lambda e: self.open_settings())
        toolbar = NavigationToolbar2Tk(self.canvas, self, pack_toolbar=False)
        toolbar.config(background=PALETTE["surface"])
        for child in toolbar.winfo_children():
            try:
                child.config(background=PALETTE["surface"])
            except tk.TclError:
                pass
        toolbar.update()
        toolbar.pack(fill="x", padx=8, pady=(0, 6))
        self.refresh_header()

    # -----------------------------------------------------------------
    def open_settings(self):
        PlotSettingsDialog(self)

    def set_topmost(self, flag: bool) -> None:
        self._topmost = bool(flag)
        try:
            self.attributes("-topmost", self._topmost)
        except tk.TclError:
            pass

    def _reassert_topmost(self, _event=None):
        """Minimizing hides the window (naturally not on top); on
        restore, some window managers forget -topmost — re-apply it."""
        if self._topmost:
            try:
                self.attributes("-topmost", True)
            except tk.TclError:
                pass

    def _close(self):
        self.manager.remove(self)

    def mark_dirty(self):
        self._dirty = True

    def refresh_header(self):
        c = self.config
        self.title(f"Unisweep — {self.manager.title_prefix}{c.label()}")
        self.title_label.configure(text=c.label())
        if c.kind == "map":
            options = list(self.manager.reads) or list(self.manager.columns)
            self.quick_label.configure(text="z:")
        else:
            options = list(self.manager.columns)
            self.quick_label.configure(text="y:")
        if tuple(options) != tuple(self.quick_box.cget("values") or ()):
            self.quick_box.configure(values=options)
        self.quick_box.set(c.zcol if c.kind == "map" else c.ycol)
        if c.kind == "map" and self._is_a_set(c.zcol):
            self.plane_label.pack(side="left", padx=(0, 2))
            self.plane_box.pack(side="left")
            self._refresh_planes()
        else:
            self.plane_label.pack_forget()
            self.plane_box.pack_forget()
        if c.kind == "line" and self.manager.dimensions >= 2:
            self._scope_var.set(c.scope == "scan")
            self.scope_check.pack(side="left", padx=(6, 0))
        else:
            self.scope_check.pack_forget()

    def _refresh_planes(self):
        labels = self.manager.maps.iteration_labels(self.config.zcol)
        options = ["latest"] + labels
        if tuple(options) != tuple(self.plane_box.cget("values") or ()):
            self.plane_box.configure(values=options)
        cur = str(self.config.plane)
        if cur != "latest":
            try:
                cur = options[1 + int(cur)] if 1 + int(cur) < len(options) \
                    else "latest"
            except ValueError:
                cur = "latest"
        if self.plane_box.get() != cur:
            self.plane_box.set(cur)

    def _plane_changed(self, _=None):
        sel = self.plane_box.get()
        if sel == "latest":
            self.config.plane = "latest"
        else:
            try:
                self.config.plane = str(
                    list(self.plane_box.cget("values")).index(sel) - 1)
            except ValueError:
                self.config.plane = "latest"
        self.mark_dirty()
        self.manager.save_templates()

    def _scope_changed(self):
        self.config.scope = "scan" if self._scope_var.get() else "all"
        self.mark_dirty()
        self.manager.save_templates()

    def _quick_changed(self, _=None):
        if self.config.kind == "map":
            self.config.zcol = self.quick_box.get()
        else:
            self.config.ycol = self.quick_box.get()
        self.refresh_header()
        self.mark_dirty()
        self.manager.save_templates()

    # -----------------------------------------------------------------
    def redraw_if_dirty(self):
        if not self._dirty:
            return
        self._dirty = False
        try:
            with matplotlib.rc_context(_mpl_style()):
                self.figure.clf()
                self.ax = self.figure.add_subplot(111)
                if self.config.kind == "map":
                    self._draw_map()
                else:
                    self._draw_line()
                self.figure.tight_layout()
            self.canvas.draw_idle()
        except Exception:                        # noqa: BLE001
            pass

    def _draw_line(self):
        c = self.config
        if not self.manager.columns:
            self.ax.text(0.5, 0.5, "waiting for data —\n"
                                   "start a sweep or monitor",
                         transform=self.ax.transAxes, ha="center",
                         color=PALETTE["muted"])
            self.ax.grid(False)
            return
        scan_only = c.scope == "scan" and self.manager.dimensions >= 2
        x, y = self.manager.data.xy(
            c.xcol, c.ycol, scan_only=scan_only,
            walk=1 if c.first_walk_only else None)
        n = min(len(x), len(y))
        x = _apply_transform(c.xtransform, x[:n])
        y = _apply_transform(c.ytransform, y[:n])
        if n:
            self.ax.plot(x, y, "-", color=c.color, lw=1.2, marker="o",
                         ms=c.marker_size, mfc=c.color, mec="none")
        self.ax.set_xlabel(c.xlabel or c.xcol)
        self.ax.set_ylabel(c.ylabel or c.ycol)
        if c.title:
            self.ax.set_title(c.title, fontsize=10)
        if c.logx:
            self.ax.set_xscale("log")
        if c.logy:
            self.ax.set_yscale("log")
        if not c.auto_x and (c.xmin is not None or c.xmax is not None):
            self.ax.set_xlim(left=c.xmin, right=c.xmax)
        if not c.auto_y and (c.ymin is not None or c.ymax is not None):
            self.ax.set_ylim(bottom=c.ymin, top=c.ymax)

    def _is_a_set(self, read: str) -> bool:
        """Whether this read has more than one map to step through.

        A 3-D sweep always has. So does a 2-D sweep of a read that
        returns a whole trace: the trace is its own inner axis, so each
        master point is a map of its own — the same set, arrived at from
        one dimension lower.
        """
        if self.manager.dimensions >= 3:
            return True
        try:
            return len(self.manager.maps.iteration_labels(read)) > 1
        except Exception:                          # noqa: BLE001
            return False

    def _draw_map(self):
        """Legacy-mapper rendering: committed rows on the frozen walk grid,
        index-space axes with value-labelled ticks (add_ticks style)."""
        c = self.config
        if self._is_a_set(c.zcol):
            self._refresh_planes()
        plane = -1 if c.plane == "latest" else int(c.plane)
        result = self.manager.maps.matrix(c.zcol, plane)
        # a trace-valued read is drawn against the trace's own axis, and
        # says so; everything else keeps the sweep's labels
        own_x, own_y = self.manager.maps.axis_labels(c.zcol)
        self.ax.set_xlabel(own_x or self.manager.inner_label)
        self.ax.set_ylabel(own_y or self.manager.row_label)
        if c.title:
            self.ax.set_title(c.title, fontsize=10)
        if result is None:
            self.ax.text(0.5, 0.5, "waiting for the first map row…",
                         transform=self.ax.transAxes, ha="center",
                         color=PALETTE["muted"])
            self.ax.grid(False)
            return
        grid, row_labels, mat = result
        z = _apply_transform(c.ztransform, mat.copy())
        vmin = None if c.auto_z else c.zmin
        vmax = None if c.auto_z else c.zmax
        m = self.ax.pcolormesh(np.ma.masked_invalid(z), cmap=c.cmap,
                               vmin=vmin, vmax=vmax, shading="flat")
        cb = self.figure.colorbar(m, ax=self.ax)
        cb.set_label(c.zcol)
        index_ticks(self.ax, grid, row_labels)
        self.ax.grid(False)


class PlotManager:
    """Spawns, ticks, and remembers the independent plot windows."""

    def __init__(self, master: tk.Widget, data: LiveData, maps: LiveMaps,
                 config_dir: str, config_name: str = "plots.json",
                 title_prefix: str = ""):
        self.master = master
        self.data = data
        self.maps = maps
        self.title_prefix = title_prefix
        self.config_path = os.path.join(config_dir, config_name)
        self.columns: tuple[str, ...] = ()
        self.reads: tuple[str, ...] = ()
        self.dimensions = 1
        self.inner_label = ""
        self.row_label = ""
        self.topmost = False
        self.restyle_images = None    # app hook: apply a window's
                                      # style to saved png/gif files
        self.windows: list[PlotWindow] = []
        self._templates: dict[str, dict] = self._load_templates()
        self.on_count_changed = lambda n: None
        self._stopped = False
        self._after_id = master.after(REDRAW_MS, self._tick)

    # ---------------- spawning ----------------------------------------
    def spawn(self, kind: str) -> PlotWindow:
        cfg = self._config_for(kind)
        win = PlotWindow(self, cfg)
        self.windows.append(win)
        self.on_count_changed(len(self.windows))
        win.mark_dirty()
        return win

    def map_style_for(self, read: str = "") -> dict:
        """How a saved map image of ``read`` should be drawn.

        A map window showing this read is the truth; any map window is the
        next best answer; failing that, the template the last one left
        behind, which is what the next window would use. Called from the
        render thread, so it reads plain attributes and touches no Tk
        widget.
        """
        chosen = None
        for win in self.windows:
            cfg = getattr(win, "config", None)
            if cfg is None or cfg.kind != "map":
                continue
            if read and cfg.zcol == read:
                chosen = cfg
                break
            if chosen is None:
                chosen = cfg
        if chosen is not None:
            return {"cmap": chosen.cmap, "ztransform": chosen.ztransform}
        saved = self._templates.get("map") or {}
        default = PlotConfig(kind="map")
        return {"cmap": saved.get("cmap") or default.cmap,
                "ztransform": saved.get("ztransform")
                or default.ztransform}

    def map_cmap(self) -> str:
        """The colour scale maps are being drawn with right now.

        An open map window is the truth.  With none open, the template the
        last one left behind is what the next window would use, so it is
        the honest answer to "what colours does this setup use" — and only
        a machine that has never opened a map falls back to the default.

        Safe to call from another thread: it reads plain attributes and
        touches no Tk widget.
        """
        return self.map_style_for()["cmap"]

    def _config_for(self, kind: str) -> PlotConfig:
        fields = {f.name for f in dataclasses.fields(PlotConfig)}
        saved = self._templates.get(kind)
        cfg = PlotConfig(kind=kind)
        if saved:
            for k, v in saved.items():
                if k in fields and k != "kind":
                    setattr(cfg, k, v)
        cols = list(self.columns)
        reads = list(self.reads)
        if kind == "map":
            if cfg.zcol not in reads:
                cfg.zcol = reads[0] if reads else (cols[-1] if cols else "")
            cfg.plane = "latest"
        else:
            if cfg.xcol not in cols:
                if not cols:
                    # cold start: no sweep/monitor yet — the window opens
                    # empty and adopts columns when data starts flowing
                    cfg.xcol = ""
                elif self.dimensions <= 0 or len(cols) < 2:
                    # monitors plot against time by default
                    cfg.xcol = cols[0]
                else:
                    cfg.xcol = cols[1]
            if cfg.ycol not in cols:
                cfg.ycol = reads[0] if reads else (cols[-1] if cols else "")
        return cfg

    def remove(self, win: PlotWindow):
        if win in self.windows:
            self.windows.remove(win)
        try:
            win.destroy()
        except tk.TclError:
            pass
        self.on_count_changed(len(self.windows))
        self.save_templates()

    def close_all(self):
        for win in list(self.windows):
            self.remove(win)

    # ---------------- data plumbing -----------------------------------
    def set_columns(self, columns: tuple[str, ...], dimensions: int):
        self.columns = tuple(columns)
        self.dimensions = dimensions
        self.reads = tuple(columns[1 + dimensions:])
        self.inner_label = columns[dimensions] if len(columns) > dimensions \
            else ""
        self.row_label = columns[dimensions - 1] if dimensions >= 2 else ""
        for win in self.windows:
            cfg = win.config
            if cfg.kind == "map" and cfg.zcol not in self.reads:
                cfg.zcol = self.reads[0] if self.reads else cfg.zcol
            if cfg.kind == "line":
                if cfg.xcol not in self.columns and self.columns:
                    if self.dimensions <= 0 or len(self.columns) < 2:
                        cfg.xcol = self.columns[0]
                    else:
                        cfg.xcol = self.columns[1]
                if cfg.ycol not in self.columns and self.reads:
                    cfg.ycol = self.reads[0]
            win.refresh_header()
            win.mark_dirty()

    def mark_dirty(self):
        for win in self.windows:
            win.mark_dirty()

    def _tick(self):
        if self._stopped:
            return
        for win in list(self.windows):
            try:
                win.redraw_if_dirty()
            except tk.TclError:
                self.windows.remove(win)
        try:
            self._after_id = self.master.after(REDRAW_MS, self._tick)
        except tk.TclError:
            pass

    def apply_topmost(self, flag: bool) -> None:
        """Live toggle for every open window; also the default for new
        ones (self.topmost)."""
        self.topmost = bool(flag)
        for win in self.windows:
            try:
                win.set_topmost(self.topmost)
            except tk.TclError:
                pass

    def retheme(self):
        """Follow a live theme switch: figures and toolbars re-colored,
        every window redrawn under the new rc."""
        for win in self.windows:
            try:
                win.figure.set_facecolor(PALETTE["surface"])
                win.canvas.get_tk_widget().configure(bg=PALETTE["surface"])
                win.mark_dirty()
            except tk.TclError:
                pass

    def shutdown(self):
        """Stop the redraw timer and close all windows — called on app
        exit so no pending timer fires into a destroyed interpreter."""
        self._stopped = True
        try:
            if self._after_id is not None:
                self.master.after_cancel(self._after_id)
        except tk.TclError:
            pass
        self.close_all()

    # ---------------- persistence -------------------------------------
    def save_templates(self):
        for win in self.windows:          # newest window of each kind wins
            self._templates[win.config.kind] = \
                dataclasses.asdict(win.config)
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as fh:
                json.dump(self._templates, fh, indent=2)
        except OSError:
            pass

    def _load_templates(self) -> dict:
        try:
            with open(self.config_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError):
            return {}
        if isinstance(data, dict) and "plots" in data:   # old format
            return {}
        return data if isinstance(data, dict) else {}
