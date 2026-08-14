"""First-run setup wizard.

The core ships without instrument drivers. On the first start (or from the
Devices page at any time) this wizard walks through the separation:

1. **Scan** — VISA and serial addresses are discovered in the background
   (addresses can also be typed in manually);
2. **Assign** — for every address, pick which instrument answers on it from
   the driver catalog; entries not present locally are marked ⬇ and the
   footer keeps a live install plan (which driver files will be fetched,
   which Python packages will be pip-installed, which vendor prerequisites
   need manual steps);
3. **Confirm & install** — driver files are fetched into ``resources/``
   (from the local ``driver_bundle`` folder or the configured ``base_url``)
   and missing packages are installed into the current environment, with
   the live pip log shown. Assignments are applied at the end.

Nothing here blocks the Tk main loop; the installer runs in its own thread
and the wizard just tails its queue.
"""

from __future__ import annotations

import os
import queue
import tkinter as tk
from tkinter import ttk

from ..core.installer import DriverInstaller
from .devices_page import UNASSIGNED
from .theme import PALETTE
from .widgets import ScrollFrame, ValidatedEntry

SETUP_FLAG = "setup_complete"


def setup_done(core_dir: str) -> bool:
    return os.path.exists(os.path.join(core_dir, "config", SETUP_FLAG))


def mark_setup_done(core_dir: str) -> None:
    os.makedirs(os.path.join(core_dir, "config"), exist_ok=True)
    with open(os.path.join(core_dir, "config", SETUP_FLAG), "w") as fh:
        fh.write("done\n")


class SetupWizard(tk.Toplevel):

    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.registry = app.registry
        self.catalog = app.catalog
        self._q: "queue.Queue" = queue.Queue()
        self.installer = DriverInstaller(self.registry, self.catalog,
                                         self._q)
        self.choices: dict[str, ttk.Combobox] = {}
        self._label_to_name: dict[str, str] = {}
        self._finished = False

        self.title("Unisweep setup")
        self.configure(bg=PALETTE["surface"], padx=18, pady=16)
        self.geometry("+180+120")
        self.minsize(760, 520)
        self.transient(app.root)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._close)

        self.steps = [ttk.Frame(self) for _ in range(3)]
        self._build_welcome(self.steps[0])
        self._build_assign(self.steps[1])
        self._build_install(self.steps[2])
        self._show(0)
        self.after(200, self._poll)

    # ---------------- step frames -------------------------------------
    def _show(self, index: int):
        for frame in self.steps:
            frame.pack_forget()
        self.steps[index].pack(fill="both", expand=True)

    def _build_welcome(self, f: ttk.Frame):
        ttk.Label(f, text="Welcome to Unisweep",
                  font=("TkDefaultFont", 14, "bold")).pack(anchor="w")
        ttk.Label(f, style="MutedS.TLabel", justify="left", wraplength=680,
                  text=(
            "\nThe Unisweep core is installed separately from the "
            "instrument drivers. This wizard scans for connected "
            "instruments, lets you choose which instrument answers on each "
            "address, and then fetches the required driver files and "
            "installs their Python dependencies into this environment.\n\n"
            "Driver files come from the local 'driver_bundle' folder next "
            "to the application, or from the repository URL configured in "
            "config/driver_catalog.json.\n"
        )).pack(anchor="w")
        bar = ttk.Frame(f)
        bar.pack(side="bottom", fill="x", pady=(14, 0))
        ttk.Button(bar, text="Skip — configure later",
                   command=self._skip).pack(side="left")
        self.scan_button = ttk.Button(bar, text="Scan for instruments",
                                      style="Accent.TButton",
                                      command=self._scan)
        self.scan_button.pack(side="right")

    def _build_assign(self, f: ttk.Frame):
        ttk.Label(f, text="Assign instruments",
                  font=("TkDefaultFont", 13, "bold")).pack(anchor="w")
        ttk.Label(f, style="MutedS.TLabel",
                  text="Pick the instrument on each address. Entries "
                       "marked ⬇ will be downloaded.").pack(anchor="w",
                                                            pady=(2, 8))
        self.rows_scroll = ScrollFrame(f)
        self.rows_scroll.pack(fill="both", expand=True)
        addbar = ttk.Frame(f)
        addbar.pack(fill="x", pady=(8, 0))
        ttk.Label(addbar, text="Add address manually:",
                  style="MutedS.TLabel").pack(side="left")
        self.new_addr = ValidatedEntry(addbar, "", validator=str,
                                       allow_empty=True, width=26)
        self.new_addr.pack(side="left", padx=6)
        ttk.Button(addbar, text="Add",
                   command=self._add_address).pack(side="left")
        ttk.Label(f, text="Install plan", style="MutedS.TLabel").pack(
            anchor="w", pady=(10, 2))
        self.plan_text = tk.Text(f, height=5, bg=PALETTE["field"],
                                 fg=PALETTE["muted"], relief="flat",
                                 state="disabled", font=("TkFixedFont", 9))
        self.plan_text.pack(fill="x")
        bar = ttk.Frame(f)
        bar.pack(side="bottom", fill="x", pady=(12, 0))
        ttk.Button(bar, text="Back",
                   command=lambda: self._show(0)).pack(side="left")
        self.confirm_btn = ttk.Button(bar, text="Confirm and install",
                                      style="Accent.TButton",
                                      command=self._confirm)
        self.confirm_btn.pack(side="right")

    def _build_install(self, f: ttk.Frame):
        ttk.Label(f, text="Installing",
                  font=("TkDefaultFont", 13, "bold")).pack(anchor="w")
        log_frame = ttk.Frame(f)
        log_frame.pack(fill="both", expand=True, pady=(8, 0))
        self.log_widget = tk.Text(log_frame, bg=PALETTE["field"],
                                  fg=PALETTE["text"], relief="flat",
                                  state="disabled",
                                  font=("TkFixedFont", 9))
        self.log_widget.pack(side="left", fill="both", expand=True)
        wiz_vsb = ttk.Scrollbar(log_frame, orient="vertical",
                                command=self.log_widget.yview)
        wiz_vsb.pack(side="right", fill="y")
        self.log_widget.configure(yscrollcommand=wiz_vsb.set)
        bar = ttk.Frame(f)
        bar.pack(side="bottom", fill="x", pady=(12, 0))
        self.close_btn = ttk.Button(bar, text="Close", state="disabled",
                                    style="Accent.TButton",
                                    command=self._finish)
        self.close_btn.pack(side="right")

    # ---------------- actions -----------------------------------------
    def _scan(self):
        self.scan_button.configure(state="disabled", text="Scanning…")
        self.registry.scan_async(
            lambda found: self._q.put(("scan_done", found)))

    def on_catalog_updated(self):
        """New drivers appeared on GitHub while the wizard is open —
        refresh the drop-downs, preserving current selections."""
        if self.choices:
            current = {addr: c.get() for addr, c in self.choices.items()}
            self._populate_rows()
            for addr, value in current.items():
                if addr in self.choices and value:
                    self.choices[addr].set(value)
            self._update_plan()

    def _populate_rows(self):
        for child in self.rows_scroll.inner.winfo_children():
            child.destroy()
        self.choices.clear()
        labels = self._driver_labels()
        addresses = [a for a in self.registry.addresses if a != "Time"]
        if not addresses:
            ttk.Label(self.rows_scroll.inner, style="MutedS.TLabel",
                      text="No addresses found — add one manually below, "
                           "or Skip and scan later from the Devices page."
                      ).grid(row=0, column=0, sticky="w", pady=6)
        for i, addr in enumerate(addresses):
            tk.Label(self.rows_scroll.inner, text=addr, anchor="w",
                     bg=PALETTE["surface"], fg=PALETTE["text"],
                     font=("TkFixedFont", 9), width=30).grid(
                row=i, column=0, sticky="w", pady=3)
            combo = ttk.Combobox(self.rows_scroll.inner, width=52,
                                 state="readonly",
                                 values=[UNASSIGNED] + labels)
            assigned = self.registry.types.get(addr, "")
            combo.set(self.catalog.label(
                assigned, self.registry.is_installed(assigned))
                if assigned else UNASSIGNED)
            combo.grid(row=i, column=1, sticky="w", padx=8, pady=3)
            combo.bind("<<ComboboxSelected>>",
                       lambda e: self._update_plan())
            self.choices[addr] = combo
        self._update_plan()

    def _driver_labels(self) -> list[str]:
        self._label_to_name.clear()
        out = []
        for name in self.catalog.names():
            if name == "Time":
                continue
            label = self.catalog.label(name,
                                       self.registry.is_installed(name))
            self._label_to_name[label] = name
            out.append(label)
        return out

    def _add_address(self):
        addr = (self.new_addr.value() or "").strip()
        if addr:
            self.registry.add_address(addr)
            self.new_addr.set("")
            self._populate_rows()

    def _selection(self) -> dict[str, str]:
        out = {}
        for addr, combo in self.choices.items():
            label = combo.get()
            if label and label != UNASSIGNED:
                out[addr] = self._label_to_name.get(label, label)
        return out

    def _update_plan(self):
        drivers = sorted(set(self._selection().values()))
        plan = self.installer.plan(drivers)
        self.plan_text.configure(state="normal")
        self.plan_text.delete("1.0", "end")
        self.plan_text.insert("1.0", plan.summary() if drivers else
                              "Nothing selected yet.")
        self.plan_text.configure(state="disabled")

    def _confirm(self):
        assignments = self._selection()
        drivers = sorted(set(assignments.values()))
        self._show(2)
        if not drivers:
            self._log("Nothing selected — no drivers to install.")
            self.close_btn.configure(state="normal")
            return
        self.installer.install_async(drivers, assignments)

    # ---------------- plumbing ----------------------------------------
    def _log(self, text: str):
        self.log_widget.configure(state="normal")
        self.log_widget.insert("end", text.rstrip() + "\n")
        self.log_widget.see("end")
        self.log_widget.configure(state="disabled")

    def _poll(self):
        try:
            while True:
                msg = self._q.get_nowait()
                if msg[0] == "scan_done":
                    self.scan_button.configure(state="normal",
                                               text="Scan for instruments")
                    self._populate_rows()
                    self._show(1)
                elif msg[0] == "install_log":
                    self._log(msg[1])
                elif msg[0] == "install_done":
                    self.close_btn.configure(state="normal")
        except queue.Empty:
            pass
        if not self._finished:
            self.after(150, self._poll)

    def _skip(self):
        mark_setup_done(self.app.core_dir)
        self._close()

    def _finish(self):
        mark_setup_done(self.app.core_dir)
        self._close()

    def _close(self):
        self._finished = True
        self.grab_release()
        self.destroy()
        self.app.on_setup_closed()
