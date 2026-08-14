"""Set/Get monitor: periodic logging of selected read parameters.

Replaces the legacy ``setget_write`` closure. Writes
``setget_YYMMDD-N.csv`` into the daily data folder (same naming), emits each
row into the event queue for live display, and is pausable / stoppable via
events instead of module globals.
"""

from __future__ import annotations

import csv
import os
import queue
import threading
import time
from datetime import datetime

import numpy as np

from .devices import DeviceRegistry
from .writer import daily_data_dir

__all__ = ["SetGetMonitor"]


class SetGetMonitor(threading.Thread):

    def __init__(self, registry: DeviceRegistry, core_dir: str,
                 reads: list[str], delay: float, out_queue: "queue.Queue"):
        super().__init__(daemon=True, name="unisweep-setget")
        self.registry = registry
        self.reads = list(reads)
        self.delay = max(float(delay), 0.05)
        self.q = out_queue
        self.pause_ev = threading.Event()
        self.stop_ev = threading.Event()

        directory = daily_data_dir(core_dir)
        ymd = datetime.today().strftime("%y%m%d")
        idx = 1
        while os.path.exists(os.path.join(directory,
                                          f"setget_{ymd}-{idx}.csv")):
            idx += 1
        self.path = os.path.join(directory, f"setget_{ymd}-{idx}.csv")

    def run(self) -> None:
        t0 = time.perf_counter()
        adapters = {}
        with open(self.path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["time"] + self.reads)
            while not self.stop_ev.is_set():
                if self.pause_ev.is_set():
                    time.sleep(self.delay)
                    continue
                row = [round(time.perf_counter() - t0, 2)]
                for read in self.reads:
                    addr, _, opt = read.rpartition(".")
                    try:
                        if addr not in adapters:
                            adapters[addr] = self.registry.connect(addr)
                        v = adapters[addr].get(opt)
                        row.append(np.nan if v is None or str(v) == "" else v)
                    except Exception as exc:      # noqa: BLE001
                        row.append(None)
                        try:
                            self.q.put_nowait(("setget_error", read, str(exc)))
                        except queue.Full:
                            pass
                writer.writerow(row)
                fh.flush()
                try:
                    self.q.put_nowait(("setget_row", tuple(row),
                                       tuple(self.reads)))
                except queue.Full:
                    pass
                time.sleep(self.delay)
