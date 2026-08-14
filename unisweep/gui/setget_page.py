"""Set / Get page.

Immediate parameter sets (with optional speed) and a periodic monitor that
logs selected reads to ``setget_YYMMDD-N.csv`` — the legacy SetGet frame,
minus the shared-global machinery. Sets run in a worker thread so a slow
instrument can't freeze the interface.
"""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from ..core.setget import SetGetMonitor
from .theme import PALETTE
from .widgets import Card, Tooltip, ValidatedEntry

N_SET_ROWS = 4


class SetRow:

    def __init__(self, parent, page, row):
        self.page = page
        reg = page.registry
        self.device = ttk.Combobox(parent, values=reg.display_list(),
                                   width=30, state="readonly")
        self.device.grid(row=row, column=0, padx=2, pady=3, sticky="w")
        self.device.bind("<<ComboboxSelected>>", self._device_changed)
        self.parameter = ttk.Combobox(parent, values=[""], width=14,
                                      state="readonly")
        self.parameter.grid(row=row, column=1, padx=2, sticky="w")
        self.value = ValidatedEntry(parent, "", allow_empty=True)
        self.value.grid(row=row, column=2, padx=2, sticky="w")
        self.speed = ValidatedEntry(parent, "", allow_empty=True, width=7)
        self.speed.grid(row=row, column=3, padx=2, sticky="w")
        self.btn = ttk.Button(parent, text="Set", command=self._set)
        self.btn.grid(row=row, column=4, padx=4)
        self.result = ttk.Label(parent, text="", style="Muted.TLabel")
        self.result.grid(row=row, column=5, padx=4, sticky="w")

    def address(self) -> str:
        return self.page.registry.address_from_display(self.device.get())

    def _device_changed(self, _=None):
        opts = self.page.registry.set_options(self.address())
        self.parameter.configure(values=opts or [""])
        self.parameter.set(opts[0] if opts else "")

    def _set(self):
        addr, param = self.address(), self.parameter.get()
        value = self.value.value()
        if not addr or not param or value is None:
            self.result.configure(text="fill device / parameter / value")
            return
        speed = self.speed.value()
        self.btn.configure(state="disabled")
        self.result.configure(text="setting…")

        def work():
            try:
                self.page.registry.connect(addr).set(param, value, speed)
                msg = f"set to {value:g}"
            except Exception as exc:              # noqa: BLE001
                msg = f"error: {exc}"
            self.page.after(0, lambda: (
                self.result.configure(text=msg),
                self.btn.configure(state="normal")))
        threading.Thread(target=work, daemon=True).start()


class SetGetPage(ttk.Frame):

    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.registry = app.registry
        self.monitor: SetGetMonitor | None = None

        set_card = Card(self, title="Set")
        set_card.pack(fill="x", padx=10, pady=(10, 6))
        hdr = ("Device", "Parameter", "Value", "Speed", "", "")
        for c, text in enumerate(hdr):
            ttk.Label(set_card, text=text, style="Muted.TLabel").grid(
                row=1, column=c, sticky="w", padx=2)
        self.rows = [SetRow(set_card, self, r + 2) for r in range(N_SET_ROWS)]

        get_card = Card(self, title="Monitor (Get)")
        get_card.pack(fill="both", expand=True, padx=10, pady=6)
        get_card.columnconfigure(0, weight=1)
        get_card.rowconfigure(1, weight=1)
        self.reads_list = tk.Listbox(get_card, selectmode="multiple",
                                     height=7, bg=PALETTE["field"],
                                     fg=PALETTE["text"],
                                     selectbackground=PALETTE["select"],
                                     relief="flat", exportselection=False)
        self.reads_list.grid(row=1, column=0, columnspan=5, sticky="nsew")
        vsb = ttk.Scrollbar(get_card, orient="vertical",
                            command=self.reads_list.yview)
        vsb.grid(row=1, column=5, sticky="ns")
        self.reads_list.configure(yscrollcommand=vsb.set)
        bar = ttk.Frame(get_card, style="Card.TFrame")
        bar.grid(row=2, column=0, columnspan=5, sticky="ew", pady=(8, 0))
        ttk.Button(bar, text="Refresh list",
                   command=self.refresh_reads).pack(side="left")
        ttk.Label(bar, text="Delay, s:", style="Muted.TLabel").pack(
            side="left", padx=(14, 4))
        self.delay = ValidatedEntry(bar, 1.0, width=6)
        self.delay.pack(side="left")
        self.start_btn = ttk.Button(bar, text="Start monitor",
                                    style="Accent.TButton",
                                    command=self._start)
        self.start_btn.pack(side="left", padx=(14, 4))
        self.stop_btn = ttk.Button(bar, text="Stop", state="disabled",
                                   command=self._stop)
        self.stop_btn.pack(side="left")
        plot_btn = ttk.Button(bar, text="New plot",
                              command=lambda:
                              self.app.setget_plots.spawn("line"))
        plot_btn.pack(side="left", padx=(14, 0))
        Tooltip(plot_btn, "Open a live graph window of the monitored\n"
                          "values (against time by default). Spawn as\n"
                          "many as needed, before or during a monitor.")
        self.live_label = ttk.Label(get_card, text="", style="Muted.TLabel",
                                    justify="left")
        self.live_label.grid(row=3, column=0, columnspan=5, sticky="w",
                             pady=(8, 0))
        self.refresh_reads()

    # -----------------------------------------------------------------
    def refresh_reads(self):
        self.reads_list.delete(0, "end")
        for name in self.registry.read_catalogue():
            self.reads_list.insert("end", name)
        for row in self.rows:
            row.device.configure(values=self.registry.display_list())

    def _start(self):
        reads = [self.reads_list.get(i)
                 for i in self.reads_list.curselection()]
        if not reads:
            messagebox.showwarning("Monitor", "Select parameters to read.")
            return
        delay = self.delay.value() or 1.0
        columns = ("time",) + tuple(reads)
        self.app.setget_data.reset(columns, 1)
        self.app.setget_plots.set_columns(columns, 0)
        self.monitor = SetGetMonitor(self.registry, self.app.core_dir,
                                     reads, delay, self.app.event_queue)
        self.monitor.start()
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.app.status(f"Monitor logging to {self.monitor.path}")

    def _stop(self):
        if self.monitor:
            self.monitor.stop_ev.set()
            self.monitor = None
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")

    def show_row(self, row: tuple, reads: tuple):
        text = "   ".join(f"{r.split('.')[-1]} = {v}"
                          for r, v in zip(reads, row[1:]))
        self.live_label.configure(text=f"t = {row[0]} s   {text}")
