"""CSV writing with the legacy naming scheme.

Output stays byte-compatible with the old app so every downstream tool
(mapper scripts, data2map, notebooks) keeps working:

* daily folder ``<core>/<YYMMDD>/data_files``;
* base name defaults to ``YYMMDD``; an auto-incremented ``-N`` suffix is
  scanned from existing files; outer-axis values are embedded as
  ``_<cut(value)>`` for 2-D / 3-D sweeps (same ``cut`` rounding);
* columns: ``time``, one ``<device>.<param>_sweep`` column per axis, then the
  selected read parameters;
* a file that ends up with no data rows is deleted on close (legacy
  behaviour).

The writer runs entirely inside the engine thread — one owner, no shared
file handles.
"""

from __future__ import annotations

import csv
import os
from datetime import datetime
from typing import Optional, Sequence

from .filenames import cut, fix_unicode, unify_filename

__all__ = ["DataWriter", "daily_data_dir"]

DELIMITER = ","


def daily_data_dir(core_dir: str) -> str:
    ymd = datetime.today().strftime("%y%m%d")
    path = os.path.join(core_dir, ymd, "data_files")
    os.makedirs(path, exist_ok=True)
    return path


def _next_index(directory: str, basic_name: str) -> int:
    best = 0
    try:
        names = os.listdir(directory)
    except OSError:
        return 1
    for f in names:
        if basic_name not in f or "manual" in f or "setget" in f:
            continue
        stem = f[: f.rfind(".")] if "." in f else f
        if "-" not in stem:
            continue
        tail = stem[stem.rfind("-") + 1:]
        if tail.isdigit():
            best = max(best, int(tail))
    return best + 1


class DataWriter:
    """Owns the current data file; rotates per outer-axes point."""

    def __init__(self, core_dir: str, columns: Sequence[str],
                 filename: str = ""):
        self.core_dir = core_dir
        self.columns = tuple(columns)
        self.directory = daily_data_dir(core_dir)
        self.ymd = datetime.today().strftime("%y%m%d")
        self.ext = ".csv"
        if filename:
            filename = fix_unicode(filename.strip())
            if filename.endswith(("/", "\\")) or os.path.isdir(filename):
                # a FOLDER: the usual dated structure goes inside it
                root = filename.rstrip("/\\") or self.directory
                self.directory = os.path.join(root, self.ymd,
                                              "data_files")
                self.base = self.ymd
            else:
                # a NAME (with or without folder/extension): the dated
                # structure goes into the name's parent folder; the
                # extension is kept when deliberately given, else .csv
                parent = os.path.dirname(filename)
                base = os.path.basename(filename)
                stem, ext = os.path.splitext(base)
                if ext:
                    self.ext = ext
                if "-" in stem and stem[stem.rfind("-") + 1:].isdigit():
                    stem = stem[: stem.rfind("-")]
                self.base = unify_filename(stem) or self.ymd
                if parent:
                    self.directory = os.path.join(parent, self.ymd,
                                                  "data_files")
        else:
            self.base = self.ymd
        os.makedirs(self.directory, exist_ok=True)
        self.path: Optional[str] = None
        self._fh = None
        self._writer = None
        self._rows_in_file = 0

    # -----------------------------------------------------------------
    def open_file(self, outer_values: Sequence[float] = ()) -> str:
        """Start a new data file for the given outer-axis values."""
        self.close()
        name = self.base
        for v in outer_values:
            name += f"_{cut(float(v))}"
        index = _next_index(self.directory, self.base)
        self.path = os.path.join(self.directory,
                                 f"{name}-{index}{self.ext}")
        self._fh = open(self.path, "w", newline="", encoding="utf-8")
        self._writer = csv.writer(self._fh, delimiter=DELIMITER)
        self._writer.writerow(self.columns)
        self._fh.flush()
        self._rows_in_file = 0
        return self.path

    def write(self, row: Sequence) -> None:
        if self._writer is None:
            self.open_file()
        self._writer.writerow(row)
        self._fh.flush()
        self._rows_in_file += 1

    def close(self) -> None:
        if self._fh is not None:
            path, empty = self.path, self._rows_in_file == 0
            self._fh.close()
            self._fh = self._writer = None
            if empty and path:
                try:
                    os.remove(path)
                except OSError:
                    pass
        self.path = None if self._fh is None else self.path
