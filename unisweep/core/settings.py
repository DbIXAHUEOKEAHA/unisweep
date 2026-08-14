"""Application-wide settings (``config/settings.json``).

These are the knobs that describe *how the software behaves and stores
data*, as opposed to *what a particular sweep does* — so they live on the
Settings page rather than the sweep or set/get pages, persist across
sessions, and are stamped into every :class:`SweepProgram` at start:

* map output: whether to save maps, worksheet grid vs single XYZ long
  file (or both), value-vs-index mapping, uniform grid, PNG mirrors;
* sweep behaviour defaults: ramp everything to zero when a sweep ends;
* engine protection: the stall-watchdog warn/abort budgets for sweepable
  instruments.
"""

from __future__ import annotations

import dataclasses
import json
import os

__all__ = ["AppSettings"]


@dataclasses.dataclass
class AppSettings:
    # ---- map / data output -------------------------------------------
    save_maps: bool = True
    map_style: str = "grid"            # 'grid' | 'xyz' | 'both'
    map_interpolated: bool = True
    map_uniform: bool = False
    map_images: bool = True
    # ---- sweep behaviour ---------------------------------------------
    to_zero_default: bool = False
    # ---- sweepable-device protection ---------------------------------
    stall_warn_s: float = 3.0
    stall_abort_s: float = 12.0

    # -----------------------------------------------------------------
    @classmethod
    def load(cls, core_dir: str) -> "AppSettings":
        path = os.path.join(core_dir, "config", "settings.json")
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError):
            return cls()
        fields = {f.name: f.type for f in dataclasses.fields(cls)}
        kwargs = {k: v for k, v in data.items() if k in fields}
        try:
            out = cls(**kwargs)
        except TypeError:
            return cls()
        if out.map_style not in ("grid", "xyz", "both"):
            out.map_style = "grid"
        out.stall_warn_s = max(float(out.stall_warn_s), 0.5)
        out.stall_abort_s = max(float(out.stall_abort_s),
                                out.stall_warn_s + 0.5)
        return out

    def save(self, core_dir: str) -> None:
        path = os.path.join(core_dir, "config", "settings.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(dataclasses.asdict(self), fh, indent=2)
