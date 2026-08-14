"""Devices page.

Redesigned around visible per-address assignment: every address is a row
with a state LED, the assigned instrument in an inline drop-down (catalog
entries that aren't installed yet are marked with ⬇), a status text
(unassigned / not installed / installed / connected + IDN), and Install /
Test actions right on the row. Picking a driver in the drop-down assigns it
immediately — no separate select-then-assign dance.

Assignments are also mirrored everywhere else in the GUI: device pickers on
the Sweep and Set/Get pages show "ADDRESS — Driver".

The Install button drives the on-demand installer (driver file fetched into
resources/ from the local ``driver_bundle`` folder or the configured
``base_url``, missing Python packages pip-installed into this environment),
with the live log in the panel at the bottom. Scanning runs in the
background and never blocks the interface.
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import ttk

from ..core.catalog import DriverCatalog
from ..core.devices import probe_sweepable
from ..core.installer import DriverInstaller
from .theme import PALETTE
from .widgets import Card, Collapsible, Led, ScrollFrame, Tooltip, \
    ValidatedEntry

UNASSIGNED = "— unassigned —"


class DeviceRow:

    def __init__(self, parent, page: "DevicesPage", address: str, row: int):
        self.page = page
        self.address = address
        self.led = Led(parent)
        self.led.grid(row=row, column=0, padx=(2, 6), pady=3)
        self.addr_label = tk.Label(parent, text=address, anchor="w",
                                   bg=PALETTE["card"], fg=PALETTE["text"],
                                   font=("TkFixedFont", 9))
        self.addr_label.grid(row=row, column=1, sticky="w", padx=(0, 8))
        self.combo = ttk.Combobox(parent, width=38, state="readonly")
        self.combo.grid(row=row, column=2, sticky="w", padx=(0, 6), pady=3)
        self.combo.bind("<<ComboboxSelected>>", self._assigned)
        self.install_btn = ttk.Button(parent, text="Install", width=8,
                                      command=self._install)
        self.test_btn = ttk.Button(parent, text="Test", width=6,
                                   command=self._test)
        self.install_btn.grid(row=row, column=3, padx=2)
        self.test_btn.grid(row=row, column=4, padx=2)
        self.sweep_btn = ttk.Button(parent, text="⇄", width=3,
                                    command=self._sweep_test)
        self.sweep_btn.grid(row=row, column=5, padx=2)
        Tooltip(self.sweep_btn,
                "Sweep-capability test: command a setpoint and watch the\n"
                "readback to verify the instrument really ramps there.\n"
                "MOVES THE INSTRUMENT — you choose the target explicitly.")
        # status takes whatever width is left and truncates gracefully
        self.status = ttk.Label(parent, text="", style="Muted.TLabel",
                                anchor="w")
        self.status.grid(row=row, column=6, sticky="ew", padx=(8, 4))
        parent.columnconfigure(6, weight=1)
        Tooltip(self.install_btn,
                "Fetch the driver file and pip-install its Python\n"
                "dependencies into this environment.")
        Tooltip(self.combo, "Which instrument answers on this address.\n"
                            "Entries marked ⬇ will be downloaded on Install.")
        self.refresh()

    # -----------------------------------------------------------------
    def refresh(self):
        page = self.page
        reg = page.registry
        labels = page.driver_labels()
        self.combo.configure(values=[UNASSIGNED] + labels)
        assigned = reg.types.get(self.address, "")
        if self.address == "Time":
            self.combo.set("Time — virtual time device")
            self.combo.configure(state="disabled")
            self.install_btn.grid_remove()
            self.test_btn.grid_remove()
            self.led.set(PALETTE["accent"])
            self.status.configure(text="built-in")
            return
        self.combo.set(page.label_of(assigned) if assigned else UNASSIGNED)
        connected = reg.connected(self.address)
        import_err = reg.import_error(assigned) if assigned else ""
        if not assigned:
            self.led.set(PALETTE["muted"])
            self.status.configure(text="unassigned")
            self.install_btn.grid_remove()
        elif import_err and reg.has_driver_file(assigned):
            # the file is there, but its dependencies are broken — show the
            # actual error instead of a misleading "not installed", and let
            # one click re-resolve the dependencies
            self.led.set(PALETTE["red"])
            self.status.configure(
                text=self._short(f"import failed: {import_err}", 60))
            Tooltip(self.status, f"{assigned}: {import_err}\n\n"
                                 "Press Fix to resolve and install the "
                                 "missing dependencies (the working recipe "
                                 "is recorded in config/dependency_map.json).")
            self.install_btn.configure(text="Fix")
            self.install_btn.grid()
        elif not reg.is_installed(assigned):
            self.led.set(PALETTE["amber"])
            self.status.configure(text="driver not installed")
            self.install_btn.configure(text="Install")
            self.install_btn.grid()
        elif connected is not None:
            self.led.set(PALETTE["green"])
            self.status.configure(text=self._short(f"connected"))
            self.install_btn.grid_remove()
        else:
            self.led.set(PALETTE["accent"])
            self.status.configure(text="driver installed")
            self.install_btn.grid_remove()

    @staticmethod
    def _short(text: str, n: int = 42) -> str:
        return text if len(text) <= n else text[: n - 1] + "…"

    # (Fix and Install share the same path: the installer re-plans from the
    # local driver source, resolves imports, and verifies them afterwards.)

    def _assigned(self, _=None):
        label = self.combo.get()
        if label == UNASSIGNED:
            self.page.registry.unassign(self.address)
        else:
            name = self.page.name_of(label)
            self.page.registry.assign(self.address, name)
            if not self.page.registry.is_installed(name):
                self.page.log(f"{self.address} → {name}: driver not "
                              f"installed yet — press Install on the row")
        self.refresh()
        self.page.app.on_devices_changed()

    def _install(self):
        assigned = self.page.registry.types.get(self.address, "")
        if assigned:
            self.page.install([assigned])

    def _sweep_test(self):
        assigned = self.page.registry.types.get(self.address, "")
        if not assigned or not self.page.registry.is_installed(assigned):
            self.status.configure(text="assign + install the driver first")
            return
        SweepTestDialog(self.page, self.address)

    def _test(self):
        assigned = self.page.registry.types.get(self.address, "")
        if not assigned:
            self.status.configure(text="assign a driver first")
            return
        if not self.page.registry.is_installed(assigned):
            self.status.configure(text="driver not installed")
            return
        self.status.configure(text="connecting…")

        def work():
            try:
                idn = self.page.registry.connect(self.address).idn()
                result = self._short(f"connected: {idn}")
                colour = PALETTE["green"]
            except Exception as exc:              # noqa: BLE001
                result = self._short(f"error: {exc}")
                colour = PALETTE["red"]
            # never touch Tk from a worker thread — route through the
            # page's queue, drained by its poll loop on the Tk thread
            self.page.queue_put(("test_result", self.address, result,
                                 colour))
        threading.Thread(target=work, daemon=True).start()


class DevicesPage(ttk.Frame):

    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.registry = app.registry
        self.catalog: DriverCatalog = app.catalog
        self._q: "queue.Queue" = queue.Queue()
        self.installer = DriverInstaller(self.registry, self.catalog,
                                         self._q)
        self.rows: dict[str, DeviceRow] = {}
        self._label_to_name: dict[str, str] = {}

        bar = ttk.Frame(self, padding=(10, 10, 10, 0))
        bar.pack(fill="x")
        self.scan_btn = ttk.Button(bar, text="Scan VISA + serial",
                                   command=self._scan)
        self.scan_btn.pack(side="left")
        self.update_btn = ttk.Button(
            bar, text="Update catalog",
            command=lambda: (self.update_btn.configure(state="disabled"),
                             self.log("checking GitHub for new drivers…"),
                             self.app.refresh_catalog_async(manual=True)))
        self.update_btn.pack(side="left", padx=(8, 0))
        Tooltip(self.update_btn,
                "Search the GitHub repository for new driver files and\n"
                "append them to the catalog. Works via the GitHub API or,\n"
                "if that is unavailable, by caching the repository archive\n"
                "(which then also serves offline installs). With no\n"
                "connection the local catalog stays in effect.")
        ttk.Label(bar, text="Add address:", style="MutedS.TLabel").pack(
            side="left", padx=(16, 4))
        self.new_addr = ValidatedEntry(bar, "", validator=str,
                                       allow_empty=True, width=18)
        self.new_addr.pack(side="left")
        self.new_addr.bind("<Return>", lambda e: self._add())
        ttk.Button(bar, text="Add", command=self._add).pack(side="left",
                                                            padx=4)
        wiz_btn = ttk.Button(bar, text="Wizard…",
                             command=self.app.open_setup_wizard)
        wiz_btn.pack(side="right")
        Tooltip(wiz_btn, "Re-run the first-start setup wizard:\n"
                         "scan, assign instruments, install drivers.")

        card = Card(self, title="Instruments")
        card.pack(fill="both", expand=True, padx=10, pady=(8, 4))
        card.columnconfigure(0, weight=1)
        card.rowconfigure(2, weight=1)
        head = ttk.Frame(card, style="Card.TFrame")
        head.grid(row=1, column=0, sticky="ew")
        for col, (text, w) in enumerate((("", 3), ("Address", 26),
                                         ("Instrument driver", 40),
                                         ("", 8), ("", 6), ("", 3),
                                         ("Status", 12))):
            ttk.Label(head, text=text, style="Muted.TLabel",
                      width=w).grid(row=0, column=col, sticky="w",
                                    padx=(2 if col == 0 else 0, 6))
        self.scroll = ScrollFrame(card, canvas_bg=PALETTE["card"],
                                  style="Card.TFrame")
        self.scroll.grid(row=2, column=0, sticky="nsew")
        self.scroll.inner.configure(style="Card.TFrame")

        log_box = Collapsible(self, "Installation log", opened=False)
        log_box.pack(fill="x", padx=10, pady=(0, 10))
        self.log_widget = tk.Text(log_box.body, height=8,
                                  bg=PALETTE["field"], fg=PALETTE["text"],
                                  relief="flat", state="disabled",
                                  font=("TkFixedFont", 9))
        self.log_widget.pack(side="left", fill="both", expand=True)
        log_vsb = ttk.Scrollbar(log_box.body, orient="vertical",
                                command=self.log_widget.yview)
        log_vsb.pack(side="right", fill="y")
        self.log_widget.configure(yscrollcommand=log_vsb.set)
        self._log_box = log_box

        self.rebuild_rows()
        self.after(200, self._poll)

    # ---------------- catalog labels ----------------------------------
    def driver_labels(self) -> list[str]:
        self._label_to_name.clear()
        labels = []
        for name in self.catalog.names():
            if name == "Time":
                continue
            label = self.catalog.label(name,
                                       self.registry.is_installed(name))
            self._label_to_name[label] = name
            labels.append(label)
        return labels

    def label_of(self, name: str) -> str:
        return self.catalog.label(name, self.registry.is_installed(name))

    def name_of(self, label: str) -> str:
        return self._label_to_name.get(label, label.split("  ⬇")[0]
                                       .split(" — ")[0])

    # ---------------- rows --------------------------------------------
    def rebuild_rows(self):
        for child in self.scroll.inner.winfo_children():
            child.destroy()
        self.rows.clear()
        for i, addr in enumerate(self.registry.addresses):
            self.rows[addr] = DeviceRow(self.scroll.inner, self, addr, i)

    def refresh_rows(self):
        if set(self.rows) != set(self.registry.addresses):
            self.rebuild_rows()
        else:
            for row in self.rows.values():
                row.refresh()

    # ---------------- actions -----------------------------------------
    def _scan(self):
        self.scan_btn.configure(state="disabled", text="Scanning…")
        self.registry.scan_async(
            lambda found: self._q.put(("scan_done", found)))

    def _add(self):
        addr = (self.new_addr.value() or "").strip()
        if addr:
            self.registry.add_address(addr)
            self.new_addr.set("")
            self.rebuild_rows()
            self.app.on_devices_changed()

    def install(self, driver_names: list[str]):
        if self.installer.busy:
            self.log("an installation is already running")
            return
        self._log_box.open()
        plan = self.installer.plan(driver_names)
        self.log(plan.summary())
        self.installer.install_async(driver_names)

    def log(self, text: str):
        self.log_widget.configure(state="normal")
        self.log_widget.insert("end", text.rstrip() + "\n")
        self.log_widget.see("end")
        self.log_widget.configure(state="disabled")

    def on_catalog_updated(self, added, msg, ok, manual):
        self.update_btn.configure(state="normal")
        if manual or added:
            self.log(msg)
        if added:
            self.refresh_rows()
            for row in self.rows.values():
                row.refresh()

    def queue_put(self, item) -> None:
        try:
            self._q.put_nowait(item)
        except queue.Full:
            pass

    # ---------------- polling -----------------------------------------
    def _poll(self):
        try:
            while True:
                msg = self._q.get_nowait()
                if msg[0] == "scan_done":
                    self.scan_btn.configure(state="normal",
                                            text="Scan VISA + serial")
                    self.refresh_rows()
                    self.app.status(
                        f"Scan finished — {len(msg[1])} address(es) found")
                elif msg[0] == "install_log":
                    self.log(msg[1])
                elif msg[0] == "install_done":
                    self.refresh_rows()
                    self.app.on_devices_changed()
                    self.app.status(msg[2])
                elif msg[0] == "test_result":
                    _tag, addr, text, colour = msg
                    row = self.rows.get(addr)
                    if row is not None:
                        row.status.configure(text=text)
                        row.led.set(colour)
                    self.app.on_devices_changed()
        except queue.Empty:
            pass
        self.after(200, self._poll)


class SweepTestDialog(tk.Toplevel):
    """'Set a point and check it goes there': empirical sweepability test.

    The user picks a settable parameter, an explicit target and a rate; the
    instrument is commanded and the readback is watched. The verdict says
    whether the device truly ramps, jumps instantly, stalls, or never
    moves — and warns when that disagrees with the driver's 'sweepable'
    flag (which is what the engine relies on)."""

    def __init__(self, page: "DevicesPage", address: str):
        super().__init__(page)
        self.page = page
        self.address = address
        self.title(f"Sweep test — {address}")
        self.configure(bg=PALETTE["surface"], padx=14, pady=12)
        self.transient(page.winfo_toplevel())
        self.resizable(False, False)
        self._running = False

        reg = page.registry
        adapter = None
        try:
            adapter = reg.connect(address)
        except Exception as exc:                  # noqa: BLE001
            ttk.Label(self, text=f"cannot connect: {exc}").grid(row=0,
                                                                column=0)
            return
        self.adapter = adapter
        opts = list(adapter.set_options)
        marks = [f"{o}  {'(sweepable)' if adapter.sweepable(o) else ''}"
                 for o in opts]
        self._opt_by_mark = dict(zip(marks, opts))

        ttk.Label(self, text="Parameter", style="MutedS.TLabel").grid(
            row=0, column=0, sticky="w", pady=2)
        self.param = ttk.Combobox(self, values=marks, width=24,
                                  state="readonly")
        default = next((m for m, o in self._opt_by_mark.items()
                        if adapter.sweepable(o)), marks[0] if marks else "")
        self.param.set(default)
        self.param.grid(row=0, column=1, columnspan=2, sticky="w", pady=2)
        self.param.bind("<<ComboboxSelected>>", self._prefill)

        ttk.Label(self, text="Target", style="MutedS.TLabel").grid(
            row=1, column=0, sticky="w", pady=2)
        self.target = ValidatedEntry(self, "", allow_empty=True, width=12)
        self.target.grid(row=1, column=1, sticky="w", pady=2)
        self.current_label = ttk.Label(self, text="", style="MutedS.TLabel")
        self.current_label.grid(row=1, column=2, sticky="w", padx=6)

        ttk.Label(self, text="Rate", style="MutedS.TLabel").grid(
            row=2, column=0, sticky="w", pady=2)
        self.rate = ValidatedEntry(self, 1.0, width=12)
        self.rate.grid(row=2, column=1, sticky="w", pady=2)
        ttk.Label(self, text="Timeout, s", style="MutedS.TLabel").grid(
            row=2, column=2, sticky="e")
        self.timeout = ValidatedEntry(self, 15.0, width=7)
        self.timeout.grid(row=2, column=3, sticky="w", padx=4)

        ttk.Label(self, style="MutedS.TLabel", wraplength=430, justify="left",
                  text="This commands the instrument to the target and "
                       "watches the readback. Choose a safe target.").grid(
            row=3, column=0, columnspan=4, sticky="w", pady=(6, 2))

        log_frame = ttk.Frame(self)
        log_frame.grid(row=4, column=0, columnspan=4, pady=(4, 6),
                       sticky="ew")
        self.log_widget = tk.Text(log_frame, height=10, width=60,
                                  bg=PALETTE["field"], fg=PALETTE["text"],
                                  relief="flat", state="disabled",
                                  font=("TkFixedFont", 9))
        self.log_widget.pack(side="left", fill="both", expand=True)
        dlg_vsb = ttk.Scrollbar(log_frame, orient="vertical",
                                command=self.log_widget.yview)
        dlg_vsb.pack(side="right", fill="y")
        self.log_widget.configure(yscrollcommand=dlg_vsb.set)

        btns = ttk.Frame(self)
        btns.grid(row=5, column=0, columnspan=4, sticky="e")
        self.run_btn = ttk.Button(btns, text="Run test",
                                  style="Accent.TButton", command=self._run)
        self.run_btn.pack(side="right", padx=4)
        ttk.Button(btns, text="Close",
                   command=self.destroy).pack(side="right", padx=4)
        self._q: "queue.Queue" = queue.Queue()
        self._prefill()
        self.after(100, self._poll)

    def _prefill(self, _=None):
        opt = self._opt_by_mark.get(self.param.get(), "")
        try:
            v = float(self.adapter.get(opt))
            self.current_label.configure(text=f"current: {v:g}")
            if self.target.value() is None:
                self.target.set(f"{v:g}")
        except Exception:                          # noqa: BLE001
            self.current_label.configure(text="current: (not readable)")

    def _log(self, line: str):
        # called from the worker thread — queue, never touch Tk directly
        try:
            self._q.put_nowait(("log", line))
        except queue.Full:
            pass

    def _poll(self):
        try:
            while True:
                kind, payload = self._q.get_nowait()
                if kind == "log":
                    self.log_widget.configure(state="normal")
                    self.log_widget.insert("end", payload.rstrip() + "\n")
                    self.log_widget.see("end")
                    self.log_widget.configure(state="disabled")
                elif kind == "done":
                    self.run_btn.configure(state="normal", text="Run test")
                    self._running = False
        except queue.Empty:
            pass
        if self.winfo_exists():
            self.after(100, self._poll)

    def _run(self):
        if self._running:
            return
        opt = self._opt_by_mark.get(self.param.get(), "")
        target = self.target.value()
        rate = self.rate.value()
        timeout = self.timeout.value() or 15.0
        if opt == "" or target is None or rate is None or rate <= 0:
            self._log("enter a parameter, a target and a positive rate")
            return
        self._running = True
        self.run_btn.configure(state="disabled", text="Running…")

        def work():
            try:
                probe_sweepable(self.adapter, opt, float(target),
                                float(rate), timeout=float(timeout),
                                poll=0.2, log=self._log)
            except Exception as exc:               # noqa: BLE001
                self._log(f"test failed: {exc}")
            try:
                self._q.put_nowait(("done", None))
            except queue.Full:
                pass
        threading.Thread(target=work, daemon=True).start()
