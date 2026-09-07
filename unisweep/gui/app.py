"""Application window.

One resizable window replaces the legacy stack of fixed 900×600 frames:
sidebar navigation (Sweep / Set & Get / Devices), sweep controls and cards on
the left, live plots on the right, and an instrument-style status strip along
the bottom (state LED, monospace value readouts, progress, ETA, current
file).

All engine communication flows through one event queue drained here on the
Tk main loop (``after``) — no other thread ever touches a widget.
"""

from __future__ import annotations

import os
import queue
import tkinter as tk
from tkinter import messagebox, ttk

from ..core import events as ev
from ..core.config import LiveProgram, SweepProgram
from ..core.catalog import DriverCatalog
from ..core.devices import DeviceRegistry
from ..core.engine import SweepEngine
from ..core.livedata import LiveData, LiveMaps
from ..core.notify import TelegramNotifier, compose_sweep_message
from ..core.settings import AppSettings
from .devices_page import DevicesPage
from .plot_panel import PlotManager
from .setget_page import SetGetPage
from .settings_page import SettingsPage
from .sweep_page import SweepPage
from .theme import PALETTE, apply_theme
from .. import gui as _gui  # noqa: F401
from . import theme as _theme
from .widgets import Led

PUMP_MS = 100


class App:

    def __init__(self, core_dir: str):
        self.core_dir = core_dir
        self.root = tk.Tk()
        self.root.title("Unisweep")
        self.root.minsize(1100, 700)
        self.settings = AppSettings.load(core_dir)
        _theme.init_theme(self.settings.theme)
        apply_theme(self.root)
        self._maximize()

        self.registry = DeviceRegistry(core_dir)
        self.catalog = DriverCatalog(core_dir)
        self.apply_settings()
        self.event_queue: "queue.Queue" = queue.Queue()
        self.live_data = LiveData()
        self.live_maps = LiveMaps()
        self.setget_data = LiveData()
        self.engine: SweepEngine | None = None
        self.live: LiveProgram | None = None
        self._paused = False

        # ---- layout ---------------------------------------------------
        self.root.columnconfigure(1, weight=1, minsize=700)
        self.root.columnconfigure(2, weight=0, minsize=360)
        self.root.rowconfigure(0, weight=1)

        sidebar = ttk.Frame(self.root, style="Bg.TFrame", padding=(0, 8))
        sidebar.grid(row=0, column=0, sticky="nsw")
        ttk.Label(sidebar, text="  UNISWEEP", style="Mono.TLabel").pack(
            anchor="w", pady=(4, 14), padx=6)

        self.container = ttk.Frame(self.root)
        self.container.grid(row=0, column=1, sticky="nsew")
        self.container.rowconfigure(0, weight=1)
        self.container.columnconfigure(0, weight=1)

        import os as _os
        right = ttk.Frame(self.root, padding=(8, 8))
        right.grid(row=0, column=2, sticky="nsew")
        right.rowconfigure(2, weight=1)
        right.columnconfigure(0, weight=1)

        # plots exist only on demand, each in its own small window
        self.plots = PlotManager(self.root, self.live_data, self.live_maps,
                                 _os.path.join(core_dir, "config"))
        self.setget_plots = PlotManager(
            self.root, self.setget_data, LiveMaps(),
            _os.path.join(core_dir, "config"),
            config_name="plots_setget.json", title_prefix="Monitor · ")
        self.plots.apply_topmost(self.settings.plots_on_top)
        self.setget_plots.apply_topmost(self.settings.plots_on_top)
        self.plots.restyle_images = self._restyle_map_images
        bar = ttk.Frame(right)
        bar.grid(row=0, column=0, sticky="ew")
        ttk.Label(bar, text="Plots", style="MutedS.TLabel").pack(side="left")
        ttk.Button(bar, text="New line plot",
                   command=lambda: self._active_plots().spawn(
                       "line")).pack(side="left", padx=(10, 2))
        self._map_btn = ttk.Button(
            bar, text="New map",
            command=lambda: self.plots.spawn("map"))
        self._map_btn.pack(side="left", padx=2)
        self.plots_count = ttk.Label(bar, text="", style="MutedS.TLabel")
        self.plots_count.pack(side="right")
        self.plots.on_count_changed = lambda n: self.plots_count.configure(
            text=f"{n} open" if n else "")

        ttk.Label(right, text="Latest readings",
                  style="MutedS.TLabel").grid(row=1, column=0, sticky="w",
                                              pady=(12, 2))
        self.readings = ttk.Treeview(right, columns=("param", "value"),
                                     show="headings", selectmode="none")
        self.readings.heading("param", text="Parameter")
        self.readings.heading("value", text="Value")
        self.readings.column("param", width=190, anchor="w")
        self.readings.column("value", width=130, anchor="e")
        self.readings.grid(row=2, column=0, sticky="nsew")
        readings_vsb = ttk.Scrollbar(right, orient="vertical",
                                     command=self.readings.yview)
        readings_vsb.grid(row=2, column=1, sticky="ns")
        self.readings.configure(yscrollcommand=readings_vsb.set)

        self.pages: dict[str, ttk.Frame] = {}
        self.pages["Sweep"] = SweepPage(self.container, self)
        self.pages["Set & Get"] = SetGetPage(self.container, self)
        self.pages["Devices"] = DevicesPage(self.container, self)
        self.pages["Settings"] = SettingsPage(self.container, self)
        self._nav_buttons: dict[str, ttk.Button] = {}
        for name in self.pages:
            btn = ttk.Button(sidebar, text=f"  {name}", style="Nav.TButton",
                             width=13,
                             command=lambda n=name: self.show_page(n))
            btn.pack(fill="x")
            self._nav_buttons[name] = btn
        self.show_page("Sweep")

        # ---- status strip --------------------------------------------
        strip = tk.Frame(self.root, bg=PALETTE["bg"])
        strip.grid(row=1, column=0, columnspan=3, sticky="ew")
        self.led = Led(strip)
        self.led.pack(side="left", padx=(10, 6), pady=6)
        self.state_label = ttk.Label(strip, text="idle", style="Mono.TLabel")
        self.state_label.pack(side="left")
        self.values_label = ttk.Label(strip, text="", style="Mono.TLabel")
        self.values_label.pack(side="left", padx=24)
        self.file_label = ttk.Label(strip, text="", style="MonoMuted.TLabel")
        self.file_label.pack(side="right", padx=10)
        self.eta_label = ttk.Label(strip, text="", style="MonoMuted.TLabel")
        self.eta_label.pack(side="right", padx=10)
        self.progress = ttk.Progressbar(strip, length=180, maximum=1.0)
        self.progress.pack(side="right", padx=10)
        self.message_label = ttk.Label(strip, text="",
                                       style="MonoMuted.TLabel")
        self.message_label.pack(side="left", padx=8)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._pump_id = self.root.after(PUMP_MS, self._pump)
        self._wizard = None
        self.root.after(300, self._maybe_run_setup)
        self.root.after(1200, lambda: self.refresh_catalog_async())

    # ---------------- driver catalog auto-update -----------------------
    def refresh_catalog_async(self, manual: bool = False):
        """Discover new drivers on GitHub in the background.

        With a connection, new repository drivers are appended to the
        catalog; without one, the cached/local catalog silently stays in
        effect. The heavyweight zip fallback is only used when there is no
        cached index yet, or when the user asked explicitly.
        """
        import os as _os
        allow_zip = manual or not _os.path.exists(self.catalog.index_path)

        def done(added, msg, ok):
            self.event_queue.put(("catalog_updated", added, msg, ok, manual))
        self.catalog.refresh_remote_async(done, allow_zip=allow_zip)

    # ---------------- first-run setup ----------------------------------
    def _maybe_run_setup(self):
        from .setup_wizard import SetupWizard, setup_done
        assigned = {a: t for a, t in self.registry.types.items()
                    if a != "Time"}
        if setup_done(self.core_dir) or assigned:
            self.root.after(400, self._start_autoconnect)
            return
        self._wizard = SetupWizard(self)

        def _wizard_closed(event):
            if event.widget is self._wizard:
                self.root.after(300, self._start_autoconnect)
        self._wizard.bind("<Destroy>", _wizard_closed)

    def open_setup_wizard(self):
        from .setup_wizard import SetupWizard
        if self._wizard is None or not self._wizard.winfo_exists():
            self._wizard = SetupWizard(self)

    def on_setup_closed(self):
        self._wizard = None
        self.pages["Devices"].refresh_rows()
        self.on_devices_changed()

    @staticmethod
    def _maximize_root(root):
        # baseline: fill the screen even without a window manager…
        root.geometry(f"{root.winfo_screenwidth()}x"
                      f"{root.winfo_screenheight()}+0+0")
        # …then ask the WM for a proper maximize (taskbar-aware)
        try:
            root.state("zoomed")                    # Windows
            return
        except tk.TclError:
            pass
        try:
            root.attributes("-zoomed", True)        # most Linux WMs
        except tk.TclError:
            pass

    def _maximize(self):
        self.root.update_idletasks()
        self._maximize_root(self.root)

    def _reset_readings(self, columns):
        self.readings.delete(*self.readings.get_children())
        for i, name in enumerate(columns):
            self.readings.insert("", "end", iid=f"c{i}",
                                 values=(name, "—"))

    def _update_readings(self, row):
        for i, value in enumerate(row):
            if isinstance(value, float):
                text = f"{value:.6g}"
            else:
                text = "—" if value is None else str(value)
            try:
                self.readings.set(f"c{i}", "value", text)
            except tk.TclError:
                pass

    def set_theme(self, name: str) -> None:
        """Live dark/light switch: restyle every widget in every window,
        re-color the plot figures, persist the choice."""
        if name not in ("dark", "light"):
            return
        if name == self.settings.theme:
            return
        _theme.set_theme(self.root, name)
        self.plots.retheme()
        self.setget_plots.retheme()
        self.pages["Devices"].refresh_rows()   # LED colors re-read PALETTE
        self.settings.theme = name
        self.settings.save(self.core_dir)

    def _notify_sweep_end(self, event) -> None:
        st = self.settings
        if not st.tg_enabled:
            return
        stopped = bool(getattr(event, "stopped", False))
        if stopped and not st.tg_on_error and self._run_fatal:
            return
        text = compose_sweep_message(
            stopped=stopped,
            elapsed_s=getattr(self, "_run_elapsed", 0.0),
            points=getattr(self, "_run_points", 0),
            filename=getattr(self, "_run_file", ""),
            detail=getattr(self, "_run_fatal", ""))
        TelegramNotifier(st.tg_token, st.tg_chat_id).send_async(
            text, done=lambda ok, d: self.event_queue.put(
                ("notify_result", d)))

    def _restyle_map_images(self, config):
        """Feature: settings applied to a map window are applied to the
        saved .png (and .gif) files of that read as well."""
        from ..core.maps import restyle_saved_images
        data_dir = getattr(self, "_last_data_dir", "")
        if not data_dir or not config.zcol:
            self.status("no saved map images for this sweep yet")
            return
        vmin = None if config.auto_z else config.zmin
        vmax = None if config.auto_z else config.zmax
        labels = {"param": config.zcol,
                  "x": config.xlabel or "", "y": config.ylabel or ""}

        def work():
            n = restyle_saved_images(data_dir, config.zcol, vmin, vmax,
                                     labels, title=config.title)
            self.event_queue.put(
                ("notify_result",
                 f"plot settings applied to {n} saved image(s)"
                 if n else "no saved images found for this read"))
        import threading as _th
        _th.Thread(target=work, daemon=True).start()

    def _approach_window_open(self, event):
        """Feature: instruments going to initial positions show live
        progress in a separate window (one row per instrument)."""
        self._approach_close()
        win = tk.Toplevel(self.root)
        win.title("Going to start positions"
                  if event.phase == "approach" else
                  "Returning to initial values")
        win.configure(bg=PALETTE["surface"])
        win.attributes("-topmost", True)
        win.resizable(False, False)
        self._approach_win = win
        self._approach_rows = {}
        for (axis, dev, param, cur, target) in event.targets:
            frame = ttk.Frame(win)
            frame.pack(fill="x", padx=14, pady=6)
            lbl = ttk.Label(frame, width=44, anchor="w",
                            text=f"{dev}.{param}:  {cur:.6g} → "
                                 f"{target:.6g}")
            lbl.pack(side="left")
            bar = ttk.Progressbar(frame, length=180, maximum=1.0)
            bar.pack(side="left", padx=(8, 0))
            span = abs(target - cur) or 1.0
            self._approach_rows[axis] = (lbl, bar, dev, param,
                                         float(target), span)
        win.update_idletasks()

    def _approach_step(self, axis: int, value: float):
        row = getattr(self, "_approach_rows", {}).get(axis)
        if row is None:
            return
        lbl, bar, dev, param, target, span = row
        try:
            lbl.configure(text=f"{dev}.{param}:  {value:.6g} → "
                               f"{target:.6g}")
            bar.configure(value=min(max(
                1.0 - abs(target - value) / span, 0.0), 1.0))
        except tk.TclError:
            pass

    def _approach_close(self):
        win = getattr(self, "_approach_win", None)
        if win is not None:
            try:
                win.destroy()
            except tk.TclError:
                pass
        self._approach_win = None
        self._approach_rows = {}

    def _start_autoconnect(self):
        """Open every assigned, installed instrument in the background —
        the v1 behaviour: everything ready before the first sweep, no
        trip to the Devices page. Slow or dead instruments only delay
        themselves (per-address locking) and report their error on the
        device row instead of blocking startup."""
        if not self.settings.connect_on_start:
            return
        if getattr(self, "_autoconnect_started", False):
            return
        self._autoconnect_started = True
        targets = [a for a in self.registry.addresses
                   if self.registry.connected(a) is None
                   and (a == "Time"
                        or (self.registry.types.get(a)
                            and self.registry.is_installed(
                                self.registry.types[a])
                            and not self.registry.import_error(
                                self.registry.types[a])))]
        if not targets:
            return
        self.status(f"Connecting {len(targets)} instrument(s)…")

        def work():
            ok = fail = 0
            for addr in targets:
                try:
                    self.registry.connect(addr)
                    ok += 1
                    self.event_queue.put(("autoconnect", addr, True, ""))
                except Exception as exc:          # noqa: BLE001
                    fail += 1
                    self.event_queue.put(("autoconnect", addr, False,
                                          f"{type(exc).__name__}: {exc}"))
            self.event_queue.put(("autoconnect_done", ok, fail))
        import threading as _th
        _th.Thread(target=work, daemon=True).start()

    def apply_settings(self):
        """Push app-wide settings where they act immediately."""
        if hasattr(self, "plots"):        # __init__ calls this early
            self.plots.apply_topmost(self.settings.plots_on_top)
            self.setget_plots.apply_topmost(self.settings.plots_on_top)
        from ..core.engine import SweepEngine
        SweepEngine.STALL_WARN_S = float(self.settings.stall_warn_s)
        SweepEngine.STALL_ABORT_S = float(self.settings.stall_abort_s)

    # ---------------- navigation --------------------------------------
    def _active_plots(self):
        """The usual plot buttons act on the page being viewed: on the
        Set & Get page they open MONITOR graphs, elsewhere sweep plots
        (feature: one button, same way as the sweeper menu)."""
        if getattr(self, "_current_page", "") == "Set & Get":
            return self.setget_plots
        return self.plots

    def show_page(self, name: str):
        self._current_page = name
        page = self.pages.get(name)
        if hasattr(page, "on_show"):
            page.on_show()
        if hasattr(self, '_map_btn'):
            self._map_btn.configure(
                state='disabled' if name == 'Set & Get'
                else 'normal')
        for n, btn in self._nav_buttons.items():
            btn.configure(style="NavSel.TButton" if n == name
                          else "Nav.TButton")
        for page in self.pages.values():
            page.grid_forget()
        self.pages[name].grid(row=0, column=0, sticky="nsew")

    def on_devices_changed(self):
        self.pages["Sweep"].refresh_reads()
        self.pages["Set & Get"].refresh_reads()

    def status(self, text: str):
        self.message_label.configure(text=text)

    # ---------------- sweep lifecycle ----------------------------------
    def start_sweep(self, program: SweepProgram) -> LiveProgram | None:
        if program is None:
            return None
        if self.engine is not None and self.engine.is_alive():
            messagebox.showwarning("Sweep", "A sweep is already running.")
            return None
        self.live = LiveProgram(program)
        self.live_data.reset(columns=(), dimensions=program.dimensions)
        self.engine = SweepEngine(self.live, self.registry, self.core_dir,
                                  self.event_queue)
        self._paused = False
        self.engine.start()
        self.led.set(PALETTE["green"])
        self.state_label.configure(text="running")
        self.status("")
        return self.live

    def toggle_pause(self):
        if self.engine is None:
            return
        self._paused = not self._paused
        self.engine.set_paused(self._paused)
        self.pages["Sweep"].pause_btn.configure(
            text="Resume" if self._paused else "Pause")

    def stop_sweep(self):
        if self.engine is not None:
            self.engine.stop()

    def to_zero(self):
        if self.engine is not None:
            self.engine.to_zero()

    # ---------------- event pump ---------------------------------------
    def _pump(self):
        try:
            while True:
                try:
                    event = self.event_queue.get_nowait()
                except queue.Empty:
                    break
                try:
                    self._handle(event)
                except tk.TclError:
                    raise                 # teardown — handled below
                except Exception as exc:  # noqa: BLE001
                    # a single broken handler must NEVER kill the pump:
                    # without this, every later event (rows, finish,
                    # errors, notifications) would be silently lost
                    print(f"[unisweep] event handler failed for "
                          f"{type(event).__name__}: "
                          f"{type(exc).__name__}: {exc}")
            self._pump_id = self.root.after(PUMP_MS, self._pump)
        except tk.TclError:
            pass          # window torn down mid-pump — quiet exit

    def _handle(self, event):
        if isinstance(event, tuple):              # setget monitor traffic
            if event[0] == "autoconnect":
                _tag, addr, ok, msg = event
                page = self.pages.get("Devices")
                row = getattr(page, "rows", {}).get(addr) if page else None
                if row is not None:
                    if ok:
                        row.led.set(PALETTE["green"])
                        row.status.configure(text="connected")
                    else:
                        row.led.set(PALETTE["red"])
                        row.status.configure(text=row._short(f"error: {msg}")
                                             if hasattr(row, "_short")
                                             else f"error: {msg}")
                return
            if event[0] == "autoconnect_done":
                _tag, ok, fail = event
                self.status(f"Instruments connected: {ok}"
                            + (f", failed: {fail} (see Devices)"
                               if fail else ""))
                self.on_devices_changed()
                return
            if event[0] == "notify_result":
                self.status(event[1])
                return
            if event[0] == "setget_row":
                self.pages["Set & Get"].show_row(event[1], event[2])
                self.setget_data.add_row(tuple(event[1]),
                                         (float(event[1][0]),))
                self.setget_plots.mark_dirty()
            elif event[0] == "setget_error":
                self.status(f"monitor {event[1]}: {event[2]}")
            elif event[0] == "catalog_updated":
                _tag, added, msg, ok, manual = event
                self.pages["Devices"].on_catalog_updated(added, msg, ok,
                                                         manual)
                if self._wizard is not None and self._wizard.winfo_exists():
                    self._wizard.on_catalog_updated()
                if added:
                    self.status(f"Driver catalog: +{len(added)} new from "
                                f"GitHub ({', '.join(sorted(added)[:4])}"
                                + ("…" if len(added) > 4 else "") + ")")
                elif manual:
                    self.status(msg)
            return
        if isinstance(event, ev.SweepStarted):
            self._popup_seen = set()
            self._run_points = 0
            self._run_elapsed = 0.0
            self._run_file = ""
            self._run_fatal = ""
            self.live_data.reset(event.columns, event.dimensions)
            self.live_maps.reset(event.columns[1 + event.dimensions:])
            self.plots.set_columns(event.columns, event.dimensions)
            self._reset_readings(event.columns)
            self.progress.configure(value=0)
        elif isinstance(event, ev.FileOpened):
            self._run_file = os.path.basename(event.path)
            self.live_data.new_file(event.path)
            self._last_data_dir = os.path.dirname(event.path)
            self.file_label.configure(text=event.path)
        elif isinstance(event, ev.PointMeasured):
            self.live_data.add_row(event.row, event.axis_values,
                                   walk=event.walk)
            self._update_readings(event.row)
            self.values_label.configure(text="  ".join(
                f"ax{i + 1}={v:.4g}" for i, v in
                enumerate(event.axis_values)))
            self.plots.mark_dirty()
        elif isinstance(event, ev.PointSkipped):
            self.live_data.add_skipped(event.axis_values)
        elif isinstance(event, ev.MapRowCommitted):
            self.live_maps.on_row(event)
            self.plots.mark_dirty()
        elif isinstance(event, ev.Progress):
            self._run_points = event.done
            self._run_elapsed = getattr(event, "elapsed_seconds",
                                        self._run_elapsed) or \
                self._run_elapsed
            frac = event.done / event.total if event.total else 0.0
            self.progress.configure(value=min(frac, 1.0))
            if event.eta_seconds is not None:
                def _hms(t):
                    m, sec = divmod(int(t), 60)
                    h, m = divmod(m, 60)
                    return f"{h:d}:{m:02d}:{sec:02d}"
                elapsed = _hms(event.elapsed_seconds or 0)
                self.eta_label.configure(
                    text=f"{elapsed} elapsed · ETA {_hms(event.eta_seconds)}"
                         f"  ({event.done}/{event.total})")
        elif isinstance(event, ev.SweepPaused):
            self.led.set(PALETTE["amber"])
            self.state_label.configure(text="paused")
        elif isinstance(event, ev.SweepResumed):
            self.led.set(PALETTE["green"])
            self.state_label.configure(text="running")
        elif isinstance(event, ev.SweepError):
            self.status(f"{event.where}: {event.message}")
            if event.fatal:
                self.led.set(PALETTE["red"])
                self._run_fatal = event.message
            if event.fatal or getattr(event, "crucial", False):
                # a device the sweep depends on failed — raise a warning
                # window naming the instrument (once per unique message)
                seen = getattr(self, "_popup_seen", set())
                self._popup_seen = seen
                if event.message not in seen:
                    seen.add(event.message)
                    title = "Sweep stopped" if event.fatal \
                        else "Sweep warning"
                    show = messagebox.showerror if event.fatal \
                        else messagebox.showwarning
                    self.root.after(0, lambda t=title, m=event.message,
                                    fn=show: fn(t, m, parent=self.root))
        elif isinstance(event, ev.ApproachStarted):
            self._approach_window_open(event)
        elif isinstance(event, ev.ApproachFinished):
            self._approach_close()
        elif isinstance(event, ev.AxisStepped):
            self._approach_step(event.axis, event.value)
            self.values_label.configure(text="  ".join(
                f"ax{i + 1}={v:.4g}" for i, v in
                enumerate(self.engine.axis_values))
                if self.engine else "")
        elif isinstance(event, ev.SweepFinished):
            self._approach_close()
            self._notify_sweep_end(event)
            self.led.set(PALETTE["muted"] if not event.stopped
                         else PALETTE["red"])
            self.state_label.configure(
                text="stopped" if event.stopped else "finished")
            self.eta_label.configure(text="")
            self.pages["Sweep"].set_running(False)
            self.status(f"{event.points} points recorded")

    # ---------------- shutdown -----------------------------------------
    def _on_close(self):
        if self.engine is not None and self.engine.is_alive():
            if not messagebox.askyesno(
                    "Quit", "A sweep is running. Stop it and quit?"):
                return
            self.engine.stop()
            self.engine.join(5)
        monitor = self.pages["Set & Get"].monitor
        if monitor is not None:
            monitor.stop_ev.set()
            if hasattr(monitor, "join"):
                monitor.join(2)          # let the last read finish first
        try:
            if self._pump_id is not None:
                self.root.after_cancel(self._pump_id)
        except tk.TclError:
            pass
        self.plots.shutdown()
        self.setget_plots.shutdown()
        # every instrument whose library has close() gets it called
        self.registry.disconnect_all()
        self.root.destroy()

    def run(self):
        self.root.mainloop()
