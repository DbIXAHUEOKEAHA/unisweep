"""Persistent record of how each Python dependency is actually installed.

The import name of a module frequently does **not** match the pip
distribution that provides it (``import msl`` → ``pip install
msl-equipment``, ``import serial`` → ``pyserial``). This database keeps that
mapping as an explicit, per-instrument-verified record:

* seeded from the built-in table (:data:`catalog.MODULE_TO_PIP`), which was
  derived by scanning the imports of every driver in the repository;
* user-correctable and extensible through ``config/dependency_map.json``;
* **self-learning**: when the installer meets an unknown import, it tries a
  short chain of candidate pip names (the import name itself, dash/underscore
  variants, lowercase) and, whichever one makes the import resolve, records
  it permanently — so the correct installation recipe only has to be
  discovered once per lab.

Entries are pip requirement lists per import name, e.g.::

    { "msl":  ["msl-equipment"],
      "cv2":  ["opencv-python"],
      "yaml": ["PyYAML"] }
"""

from __future__ import annotations

import json
import os
import threading
from typing import Iterable, Optional

from .catalog import MODULE_TO_PIP

__all__ = ["DependencyDB"]


class DependencyDB:

    def __init__(self, core_dir: str):
        self.path = os.path.join(core_dir, "config", "dependency_map.json")
        self._lock = threading.Lock()
        self._learned: dict[str, list[str]] = {}
        self._load()

    # -----------------------------------------------------------------
    def _load(self) -> None:
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError):
            return
        if isinstance(data, dict):
            self._learned = {str(k): [str(p) for p in v]
                            for k, v in data.items()
                            if isinstance(v, (list, tuple))}

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(self._learned, fh, indent=2, sort_keys=True)

    # -----------------------------------------------------------------
    def packages_for(self, import_name: str) -> Optional[list[str]]:
        """pip requirement list for an import name, or None if unknown.

        The user's / learned record takes precedence over the built-in
        table, so a wrong builtin guess can be corrected permanently in
        ``config/dependency_map.json``.
        """
        with self._lock:
            if import_name in self._learned:
                return list(self._learned[import_name])
        if import_name in MODULE_TO_PIP:
            return list(MODULE_TO_PIP[import_name])
        return None

    def learn(self, import_name: str, packages: Iterable[str]) -> None:
        """Record a verified installation recipe permanently."""
        with self._lock:
            self._learned[import_name] = list(packages)
            try:
                self._save()
            except OSError:
                pass

    def candidates(self, import_name: str) -> list[list[str]]:
        """Ordered guesses for an unknown import, tried until one makes the
        import resolve. Kept short and predictable."""
        seen: list[list[str]] = []
        for cand in (import_name,
                     import_name.replace("_", "-"),
                     import_name.lower(),
                     import_name.lower().replace("_", "-")):
            if [cand] not in seen:
                seen.append([cand])
        return seen
