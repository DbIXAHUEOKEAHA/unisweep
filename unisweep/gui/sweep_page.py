"""The sweep page — one page for 1-D / 2-D / 3-D.

Replaces the three ~1500-line Sweeper frames. Each axis is a card; the same
card works as master, slave or slave-slave. While a sweep runs the cards stay
editable and **Apply** pushes the changes into the running engine through the
shared :class:`LiveProgram` — the supported, race-free version of what the
legacy globals allowed. Manual step files can be loaded (and hot-swapped
mid-sweep) per axis.
"""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import numpy as np

from ..core.condition import ConditionError, ConditionSet
from ..core.config import (AxisProgram, CountMode, SweepProgram,
                           load_program, save_program)
from ..core.expr import ExprError
from ..core.migrate import preset_path
from .theme import PALETTE
from .widgets import Card, Collapsible, ScrollFrame, Tooltip, ValidatedEntry

AXIS_TITLES = ["Axis 1 · Master", "Axis 2 · Slave", "Axis 3 · Slave-slave"]


def _read_manual_file(path: str) -> tuple[float, ...]:
    """First numeric column of a txt/csv manual-steps file."""
    try:
        arr = np.loadtxt(path, delimiter=",", ndmin=2)
    except ValueError:
        arr = np.loadtxt(path, ndmin=2)
    return tuple(float(v) for v in np.atleast_2d(arr)[:, 0])


class AxisCard(Card):

    def __init__(self, master, page: "SweepPage", index: int):
        super().__init__(master, title=AXIS_TITLES[index])
        self.page = page
        self.index = index
        self.manual_points: tuple[float, ...] | None = None
        self.manual_name = ""
        reg = page.registry

        r = 1
        ttk.Label(self, text="Device", style="Muted.TLabel").grid(
            row=r, column=0, sticky="w")
        self.device = ttk.Combobox(self, values=reg.display_list(),
                                   width=26, state="readonly")
        self.device.set("Time")
        self.device.grid(row=r, column=1, sticky="w", padx=4)
        self.device.bind("<<ComboboxSelected>>", self._device_changed)
        ttk.Label(self, text="Parameter", style="Muted.TLabel").grid(
            row=r, column=2, sticky="e", padx=(10, 0))
        self.parameter = ttk.Combobox(self, values=["Time"], width=12,
                                      state="readonly")
        self.parameter.set("Time")
        self.parameter.grid(row=r, column=3, sticky="w", padx=4)

        r += 1
        ttk.Label(self, text="From", style="Muted.TLabel").grid(
            row=r, column=0, sticky="w", pady=(8, 0))
        self.start = ValidatedEntry(self, 0.0)
        self.start.grid(row=r, column=1, sticky="w", padx=4, pady=(8, 0))
        ttk.Label(self, text="To", style="Muted.TLabel").grid(
            row=r, column=2, sticky="e", pady=(8, 0))
        self.stop = ValidatedEntry(self, 1.0)
        self.stop.grid(row=r, column=3, sticky="w", padx=4, pady=(8, 0))

        r += 1
        self.mode = ttk.Combobox(self, values=["rate, units/s",
                                               "step, units/pt"],
                                 width=12, state="readonly")
        self.mode.current(0)
        self.mode.grid(row=r, column=0, sticky="w", pady=(8, 0))
        self.rate = ValidatedEntry(self, 1.0)
        self.rate.grid(row=r, column=1, sticky="w", padx=4, pady=(8, 0))
        Tooltip(self.mode, "How the sweep speed is entered:\n"
                           "rate — units per second (step = rate × delay)\n"
                           "step — units per point")
        ttk.Label(self, text="Delay, s", style="Muted.TLabel").grid(
            row=r, column=2, sticky="e", pady=(8, 0))
        self.delay = ValidatedEntry(self, 1.0)
        self.delay.grid(row=r, column=3, sticky="w", padx=4, pady=(8, 0))

        r += 1
        ttk.Label(self, text="Walks", style="Muted.TLabel").grid(
            row=r, column=0, sticky="w", pady=(8, 0))
        self.walks = ttk.Spinbox(self, from_=1, to=999, width=5)
        self.walks.set(1)
        self.walks.grid(row=r, column=1, sticky="w", padx=4, pady=(8, 0))
        Tooltip(self.walks, "Back-and-forth passes: 2 = there and back")
        flags = ttk.Frame(self, style="Card.TFrame")
        flags.grid(row=r, column=2, columnspan=2, sticky="w", pady=(8, 0))
        self.snake = tk.BooleanVar(value=False)
        ttk.Checkbutton(flags, text="Snake",
                        variable=self.snake).pack(side="left", padx=(10, 8))
        self.stepwise = tk.BooleanVar(value=False)
        ttk.Checkbutton(flags, text="Force stepwise",
                        variable=self.stepwise).pack(side="left")

        r += 1
        back = Collapsible(self, "Return sweep (different rate / delay)")
        back.grid(row=r, column=0, columnspan=4, sticky="ew", pady=(8, 0))
        ttk.Label(back.body, text="Back rate", style="Muted.TLabel").grid(
            row=0, column=0, sticky="w")
        self.back_rate = ValidatedEntry(back.body, "", allow_empty=True)
        self.back_rate.grid(row=0, column=1, padx=4)
        ttk.Label(back.body, text="Back delay, s",
                  style="Muted.TLabel").grid(row=0, column=2, sticky="w",
                                             padx=(10, 0))
        self.back_delay = ValidatedEntry(back.body, "", allow_empty=True)
        self.back_delay.grid(row=0, column=3, padx=4)
        ttk.Label(back.body, style="MutedS.TLabel",
                  text="Entering a value here adds the return pass "
                       "automatically (Walks 1 → 2).").grid(
            row=1, column=0, columnspan=4, sticky="w", pady=(2, 0))
        ttk.Label(back.body, text="empty = same as forward",
                  style="Muted.TLabel").grid(row=0, column=4, padx=(10, 0))

        r += 1
        row = ttk.Frame(self, style="Card.TFrame")
        row.grid(row=r, column=0, columnspan=4, sticky="ew", pady=(8, 0))
        ttk.Button(row, text="Load manual steps…",
                   command=self._load_manual).pack(side="left")
        ttk.Button(row, text="Clear",
                   command=self._clear_manual).pack(side="left", padx=4)
        self.manual_label = ttk.Label(row, text="auto grid",
                                      style="Muted.TLabel")
        self.manual_label.pack(side="left", padx=8)
        self.apply_btn = ttk.Button(row, text="Apply", state="disabled",
                                    command=self._apply_live)
        self.apply_btn.pack(side="right")
        Tooltip(self.apply_btn, "Push these values into the running sweep.\n"
                                "They take effect on the next point.")

    # -----------------------------------------------------------------
    def device_address(self) -> str:
        return self.page.registry.address_from_display(self.device.get())

    def _device_changed(self, _=None):
        opts = self.page.registry.set_options(self.device_address())
        self.parameter.configure(values=opts or [""])
        self.parameter.set(opts[0] if opts else "")

    def _load_manual(self):
        path = filedialog.askopenfilename(
            title="Manual steps file",
            filetypes=[("Step tables", "*.txt *.csv *.dat"), ("All", "*.*")])
        if not path:
            return
        try:
            pts = _read_manual_file(path)
        except Exception as exc:                  # noqa: BLE001
            messagebox.showerror("Manual steps", f"Could not read file:\n{exc}")
            return
        self.manual_points = pts
        self.manual_name = os.path.basename(path)
        self.manual_label.configure(
            text=f"{self.manual_name} · {len(pts)} pts")
        if self.page.running:                     # hot swap mid-sweep
            self.page.live.swap_manual_points(self.index, pts,
                                              self.manual_name)

    def _clear_manual(self):
        self.manual_points = None
        self.manual_name = ""
        self.manual_label.configure(text="auto grid")
        if self.page.running:
            self.page.live.swap_manual_points(self.index, None)

    # -----------------------------------------------------------------
    def to_axis(self) -> AxisProgram | None:
        vals = dict(start=self.start.value(), stop=self.stop.value(),
                    rate=self.rate.value(), delay=self.delay.value())
        if any(v is None for v in vals.values()):
            return None
        mode = CountMode.STEP if self.mode.current() == 1 else CountMode.RATE
        try:
            walks = max(int(self.walks.get()), 1)
        except (TypeError, ValueError):
            walks = 1
        return AxisProgram(
            device=self.device_address(), parameter=self.parameter.get(),
            start=vals["start"], stop=vals["stop"],
            rate=abs(vals["rate"]), delay=abs(vals["delay"]),
            count_mode=mode,
            back_rate=self.back_rate.value(), back_delay=self.back_delay.value(),
            walks=walks, snake=self.snake.get(),
            manual_points=self.manual_points, manual_name=self.manual_name,
            force_stepwise=self.stepwise.get())

    def from_axis(self, ax: AxisProgram):
        if ax.device in self.page.registry.addresses:
            self.device.set(self.page.registry.display_name(ax.device))
            self._device_changed()
        if ax.parameter in self.parameter.cget("values"):
            self.parameter.set(ax.parameter)
        self.start.set(ax.start)
        self.stop.set(ax.stop)
        self.rate.set(ax.rate)
        self.delay.set(ax.delay)
        self.mode.current(1 if ax.count_mode == CountMode.STEP else 0)
        self.back_rate.set(ax.back_rate)
        self.back_delay.set(ax.back_delay)
        self.walks.set(ax.walks)
        self.snake.set(ax.snake)
        self.stepwise.set(ax.force_stepwise)

    def _apply_live(self):
        ax = self.to_axis()
        if ax is None:
            messagebox.showwarning("Apply", "Fix the highlighted fields first.")
            return
        self.page.apply_axis_live(self.index, ax)


class SweepPage(ttk.Frame):

    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.registry = app.registry
        self.live = None
        self.running = False

        scroll = ScrollFrame(self)
        scroll.pack(fill="both", expand=True)
        body = scroll.inner
        body.columnconfigure(0, weight=1)

        top = ttk.Frame(body, padding=(10, 10, 10, 0))
        top.grid(row=0, column=0, sticky="ew")
        row1 = ttk.Frame(top)
        row1.pack(fill="x")
        ttk.Label(row1, text="Dimensions").pack(side="left")
        self.dims = ttk.Combobox(row1, values=["1D", "2D", "3D"], width=4,
                                 state="readonly")
        self.dims.current(0)
        self.dims.pack(side="left", padx=6)
        self.dims.bind("<<ComboboxSelected>>", lambda e: self._set_dims())
        self.start_btn = ttk.Button(row1, text="Start",
                                    style="Accent.TButton",
                                    command=self._start)
        self.start_btn.pack(side="left", padx=(14, 4))
        self.pause_btn = ttk.Button(row1, text="Pause", state="disabled",
                                    command=self._pause)
        self.pause_btn.pack(side="left", padx=4)
        self.stop_btn = ttk.Button(row1, text="Stop", state="disabled",
                                   command=self._stop)
        self.stop_btn.pack(side="left", padx=4)
        self.zero_btn = ttk.Button(row1, text="To zero",
                                   style="Danger.TButton",
                                   state="disabled", command=self._to_zero)
        self.zero_btn.pack(side="left", padx=4)
        row2 = ttk.Frame(top)
        row2.pack(fill="x", pady=(6, 0))
        ttk.Button(row2, text="Load preset",
                   command=self._load_preset).pack(side="left", padx=(0, 4))
        ttk.Button(row2, text="Save preset",
                   command=self._save_preset).pack(side="left")

        self.axis_cards: list[AxisCard] = []
        self.axes_holder = ttk.Frame(body, padding=(10, 6))
        self.axes_holder.grid(row=1, column=0, sticky="ew")
        self.axes_holder.columnconfigure(0, weight=1)
        for i in range(3):
            card = AxisCard(self.axes_holder, self, i)
            self.axis_cards.append(card)

        cond = Card(body, title="Condition")
        cond.grid(row=2, column=0, sticky="ew", padx=10, pady=6)
        cond.columnconfigure(0, weight=1)
        self.condition = tk.Text(cond, height=3, bg=PALETTE["field"],
                                 fg=PALETTE["text"],
                                 insertbackground=PALETTE["text"],
                                 relief="flat", padx=6, pady=4)
        self.condition.grid(row=1, column=0, sticky="ew")
        side = ttk.Frame(cond, style="Card.TFrame")
        side.grid(row=1, column=1, sticky="n", padx=(8, 0))
        ttk.Button(side, text="Check / preview",
                   command=self._preview_condition).pack()
        ttk.Label(cond, style="Muted.TLabel", justify="left", wraplength=520,
                  text=(
            "Inequalities restrict the measured region, e.g. x**2 + y**2 <= 25. "
            "One equality couples two axes (curve following), e.g. x == 2*y + 1. "
            "Aliases: x/Master · y/Slave · z/SlaveSlave; one condition per line."
        )).grid(row=2, column=0, columnspan=2, sticky="w", pady=(6, 0))

        reads = Card(body, title="Read parameters")
        reads.grid(row=3, column=0, sticky="ew", padx=10, pady=6)
        reads.columnconfigure(1, weight=1)
        self.reads_list = tk.Listbox(reads, selectmode="multiple", height=7,
                                     bg=PALETTE["field"], fg=PALETTE["text"],
                                     selectbackground=PALETTE["select"],
                                     relief="flat", exportselection=False)
        self.reads_list.grid(row=1, column=0, columnspan=2, sticky="ew")
        reads_vsb = ttk.Scrollbar(reads, orient="vertical",
                                  command=self.reads_list.yview)
        reads_vsb.grid(row=1, column=2, sticky="ns")
        self.reads_list.configure(yscrollcommand=reads_vsb.set)
        ttk.Button(reads, text="Refresh list",
                   command=self.refresh_reads).grid(row=2, column=0,
                                                    sticky="w", pady=(6, 0))
        self.reads_hint = ttk.Label(reads, text="", style="Muted.TLabel")
        self.reads_hint.grid(row=2, column=1, sticky="e", pady=(6, 0))

        out = Card(body, title="Output")
        out.grid(row=4, column=0, sticky="ew", padx=10, pady=6)
        ttk.Label(out, text="Filename", style="Muted.TLabel").grid(
            row=1, column=0, sticky="w")
        self.filename = ValidatedEntry(out, "", validator=str,
                                       allow_empty=True, width=48)
        self.filename.grid(row=1, column=1, sticky="w", padx=6)
        ttk.Label(out, text="empty = auto (YYMMDD-N, outer values embedded)",
                  style="Muted.TLabel").grid(row=1, column=2, sticky="w")
        ttk.Label(out, text="Map/data output options moved to the "
                            "Settings page.",
                  style="Muted.TLabel").grid(row=2, column=0, columnspan=3,
                                             sticky="w", pady=(6, 0))

        script = Collapsible(body, "Per-point script (advanced)")
        script.grid(row=5, column=0, sticky="ew", padx=10, pady=(0, 12))
        self.script = tk.Text(script.body, height=6, bg=PALETTE["field"],
                              fg=PALETTE["text"],
                              insertbackground=PALETTE["text"],
                              relief="flat", padx=6, pady=4)
        self.script.pack(side="left", fill="both", expand=True)
        script_vsb = ttk.Scrollbar(script.body, orient="vertical",
                                   command=self.script.yview)
        script_vsb.pack(side="right", fill="y")
        self.script.configure(yscrollcommand=script_vsb.set)
        ttk.Label(script.body, style="Muted.TLabel", justify="left", text=(
            "Runs after every measured point. Namespace: point (dict), "
            "values (list), devices (dict), engine, np, time."
        )).pack(anchor="w", pady=(4, 0))

        self._set_dims()
        self.refresh_reads()
        self._autoload_preset()

    # ---------------- helpers -----------------------------------------
    @property
    def n_dims(self) -> int:
        return self.dims.current() + 1

    def _set_dims(self):
        for i, card in enumerate(self.axis_cards):
            card.grid_forget()
            if i < self.n_dims:
                card.grid(row=i, column=0, sticky="ew", pady=4)
        self._autoload_preset()

    def refresh_reads(self):
        selected = {self.reads_list.get(i)
                    for i in self.reads_list.curselection()}
        self.reads_list.delete(0, "end")
        for name in self.registry.read_catalogue():
            self.reads_list.insert("end", name)
            if name in selected:
                self.reads_list.selection_set("end")
        for card in self.axis_cards:
            current = card.device_address()
            card.device.configure(values=self.registry.display_list())
            if current in self.registry.addresses:
                card.device.set(self.registry.display_name(current))

    def selected_reads(self) -> tuple[str, ...]:
        return tuple(self.reads_list.get(i)
                     for i in self.reads_list.curselection())

    def build_program(self) -> SweepProgram | None:
        axes = []
        for card in self.axis_cards[: self.n_dims]:
            ax = card.to_axis()
            if ax is None:
                messagebox.showwarning(
                    "Sweep", "Fix the highlighted axis fields first.")
                return None
            axes.append(ax)
        reads = self.selected_reads()
        if not reads:
            messagebox.showwarning("Sweep",
                                   "Select at least one read parameter.")
            return None
        cond_text = self.condition.get("1.0", "end").strip()
        if cond_text:
            try:
                ConditionSet(cond_text, len(axes))
            except (ExprError, ConditionError, ValueError) as exc:
                messagebox.showerror("Condition", str(exc))
                return None
        return SweepProgram(
            axes=tuple(axes), reads=reads, condition=cond_text,
            script=self.script.get("1.0", "end").rstrip(),
            filename=(self.filename.value() or ""),
            to_zero_on_finish=self.app.settings.to_zero_default,
            save_maps=self.app.settings.save_maps,
            map_style=self.app.settings.map_style,
            map_uniform=self.app.settings.map_uniform,
            map_images=self.app.settings.map_images,
            map_interpolated=self.app.settings.map_interpolated)

    # ---------------- run control --------------------------------------
    @staticmethod
    def _estimate(program) -> tuple[int, float]:
        """(planned points, rough duration in s) from the current program."""
        points = 1
        duration = 0.0
        outer_product = 1
        for ax in program.axes:
            count = max(ax.planned_count(), 1) * ax.effective_walks()
            points *= count
            outer_product *= count
            duration += outer_product * ax.point_delay()
        return points, duration

    def _start(self):
        program = self.build_program()
        if program is None:
            return
        # ---- v1 'Start warning': axes standing away from their start ----
        try:
            from ..core.engine import check_start_positions
            offenders = check_start_positions(self.app.registry, program)
        except Exception:                          # noqa: BLE001
            offenders = []
        if offenders:
            lines = [f"{o['device']}.{o['parameter']} is at "
                     f"{o['current']:.6g} — sweep starts at "
                     f"{o['start']:.6g} (eps {o['eps']:g})"
                     for o in offenders]
            answer = messagebox.askyesnocancel(
                "Start warning",
                "\n".join(lines) + "\n\nGo to start?\n\n"
                "Yes — walk/ramp to the start point first (position shown "
                "in the status bar)\nNo — start measuring from the current "
                "value\nCancel — do not start",
                parent=self.app.root)
            if answer is None:
                self.app.status("Sweep cancelled — instruments not at "
                                "their start values")
                return
            if answer is False:
                import dataclasses
                program = dataclasses.replace(program,
                                              approach_start=False)
        self._save_preset(silent=True)
        self.live = self.app.start_sweep(program)
        if self.live is not None:
            self.set_running(True)
            points, seconds = self._estimate(program)
            m, sec = divmod(int(seconds), 60)
            h, m = divmod(m, 60)
            self.app.status(f"Sweep started — {points} planned points, "
                            f"≈ {h:d}:{m:02d}:{sec:02d} at current delays")

    def _pause(self):
        self.app.toggle_pause()

    def _stop(self):
        self.app.stop_sweep()

    def _to_zero(self):
        if messagebox.askyesno("To zero",
                               "Ramp all sweep devices to zero and stop?"):
            self.app.to_zero()

    def set_running(self, running: bool):
        self.running = running
        state = "disabled" if running else "normal"
        run_state = "normal" if running else "disabled"
        self.start_btn.configure(state=state)
        self.dims.configure(state="disabled" if running else "readonly")
        for btn in (self.pause_btn, self.stop_btn, self.zero_btn):
            btn.configure(state=run_state)
        for card in self.axis_cards:
            card.apply_btn.configure(state=run_state)
        if not running:
            self.pause_btn.configure(text="Pause")

    def apply_axis_live(self, index: int, ax: AxisProgram):
        if self.live is None:
            return
        self.live.update_axis(
            index, start=ax.start, stop=ax.stop, rate=ax.rate,
            delay=ax.delay, count_mode=ax.count_mode, back_rate=ax.back_rate,
            back_delay=ax.back_delay, walks=ax.walks, snake=ax.snake,
            force_stepwise=ax.force_stepwise)
        cond_text = self.condition.get("1.0", "end").strip()
        self.live.update(condition=cond_text,
                         script=self.script.get("1.0", "end").rstrip())
        self.app.status(f"Axis {index + 1} updated — applies on next point")

    # ---------------- condition preview --------------------------------
    def _preview_condition(self):
        text = self.condition.get("1.0", "end").strip()
        if not text:
            self.app.status("Condition is empty — every point is measured")
            return
        n = self.n_dims
        try:
            cs = ConditionSet(text, n)
        except (ExprError, ConditionError, ValueError) as exc:
            messagebox.showerror("Condition", str(exc))
            return
        if cs.coupled is not None:
            messagebox.showinfo(
                "Condition",
                f"Coupled equality detected:\n  {cs.coupled.expr.source}\n\n"
                f"Axis {cs.coupled.solved} will be solved from axis "
                f"{cs.coupled.driven[0]} at every step (curve following).")
            if not cs.region:
                return
        if n < 2:
            messagebox.showinfo("Condition",
                                "Region preview needs a 2-D/3-D sweep.")
            return
        ax1 = self.axis_cards[0].to_axis()
        ax2 = self.axis_cards[1].to_axis()
        if ax1 is None or ax2 is None:
            return
        g1 = np.linspace(ax1.start, ax1.stop, max(ax1.planned_count(), 2))
        g2 = np.linspace(ax2.start, ax2.stop, max(ax2.planned_count(), 2))
        mask = cs.preview_mask(g1, g2, ax1.step_size(), ax2.step_size())

        win = tk.Toplevel(self)
        win.title("Condition preview")
        win.configure(bg=PALETTE["surface"])
        import matplotlib
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib.figure import Figure
        fig = Figure(figsize=(4.6, 3.8), dpi=100,
                     facecolor=PALETTE["surface"])
        ax = fig.add_subplot(111)
        ax.pcolormesh(g1, g2, mask.astype(float), shading="auto",
                      cmap="Blues", vmin=0, vmax=1.4)
        ax.set_xlabel("axis 1 (x / Master)")
        ax.set_ylabel("axis 2 (y / Slave)")
        ax.set_title(f"{int(mask.sum())} of {mask.size} points measured",
                     fontsize=9)
        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas.get_tk_widget().pack(fill="both", expand=True)
        canvas.draw()

    # ---------------- presets ------------------------------------------
    def _preset_file(self) -> str:
        return preset_path(self.app.core_dir, self.n_dims)

    def _save_preset(self, silent=False):
        program = self.build_program() if not silent else None
        if program is None:
            axes = [c.to_axis() or AxisProgram()
                    for c in self.axis_cards[: self.n_dims]]
            program = SweepProgram(
                axes=tuple(axes), reads=self.selected_reads(),
                condition=self.condition.get("1.0", "end").strip(),
                script=self.script.get("1.0", "end").rstrip(),
                filename=self.filename.value() or "",
                to_zero_on_finish=self.app.settings.to_zero_default,
                save_maps=self.app.settings.save_maps,
                map_style=self.app.settings.map_style,
                map_uniform=self.app.settings.map_uniform,
                map_images=self.app.settings.map_images,
                map_interpolated=self.app.settings.map_interpolated)
        os.makedirs(os.path.dirname(self._preset_file()), exist_ok=True)
        try:
            save_program(program, self._preset_file())
            if not silent:
                self.app.status(f"Preset saved: {self._preset_file()}")
        except OSError as exc:
            if not silent:
                messagebox.showerror("Preset", str(exc))

    def _load_preset(self):
        self._autoload_preset(announce=True)

    def _autoload_preset(self, announce=False):
        path = self._preset_file()
        if not os.path.exists(path):
            if announce:
                self.app.status("No preset saved for this dimension yet")
            return
        try:
            program = load_program(path)
        except Exception as exc:                  # noqa: BLE001
            if announce:
                messagebox.showerror("Preset", f"Could not load preset:\n{exc}")
            return
        for card, ax in zip(self.axis_cards, program.axes):
            card.from_axis(ax)
        self.condition.delete("1.0", "end")
        self.condition.insert("1.0", program.condition)
        self.script.delete("1.0", "end")
        self.script.insert("1.0", program.script)
        self.filename.set(program.filename)


        self.refresh_reads()
        wanted = set(program.reads)
        for i in range(self.reads_list.size()):
            if self.reads_list.get(i) in wanted:
                self.reads_list.selection_set(i)
        if announce:
            self.app.status(f"Preset loaded: {path}")
