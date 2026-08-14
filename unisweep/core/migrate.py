"""One-time migration of legacy presets.

Reads the old ``config/sweeper{1,2,3}d_preset.csv`` files (written by the
legacy GUI on every start) and turns each into a :class:`SweepProgram` saved
as ``config/preset_{n}d.json``. The device *addresses* referenced by combo
indices in the old presets cannot be recovered reliably (they were positional
indices into a machine-specific device list), so ranges, rates, delays,
back-sweep values, walks, snake flags, condition text and filename are
migrated and the device/parameter fields fall back to 'Time' for the user to
re-pick once. ``address_dictionary.txt`` is reused as-is by the registry —
no migration needed there.
"""

from __future__ import annotations

import os

from .config import (AxisProgram, CountMode, SweepProgram, save_program)

__all__ = ["migrate_presets", "preset_path"]


def preset_path(core_dir: str, dims: int) -> str:
    return os.path.join(core_dir, "config", f"preset_{dims}d.json")


def _f(value, default=None):
    try:
        v = float(value)
        if v != v:                      # NaN
            return default
        return v
    except (TypeError, ValueError):
        return default


def _axis_from_row(row: dict, n: int) -> AxisProgram:
    mode = str(row.get(f"count_option{n}", "ratio")).strip() or "ratio"
    manual = None
    return AxisProgram(
        device="Time", parameter="Time",
        start=_f(row.get(f"from{n}"), 0.0),
        stop=_f(row.get(f"to{n}"), 1.0),
        rate=abs(_f(row.get(f"ratio{n}"), 1.0) or 1.0),
        delay=abs(_f(row.get(f"delay_factor{n}"), 1.0) or 1.0),
        count_mode=CountMode.STEP if mode == "step" else CountMode.RATE,
        back_rate=_f(row.get(f"back_ratio{n}")),
        back_delay=_f(row.get(f"back_delay_factor{n}")),
        walks=1,
        snake=bool(int(_f(row.get(f"status_snakemode{n}"), 0) or 0)),
        manual_points=manual,
    )


def migrate_presets(core_dir: str) -> list[str]:
    """Create JSON presets from legacy CSVs. Returns the files written."""
    try:
        import pandas as pd
    except ImportError:                 # pragma: no cover
        return []
    written = []
    for dims in (1, 2, 3):
        src = os.path.join(core_dir, "config", f"sweeper{dims}d_preset.csv")
        dst = preset_path(core_dir, dims)
        if os.path.exists(dst) or not os.path.exists(src):
            continue
        try:
            row = pd.read_csv(src).iloc[0].to_dict()
        except Exception:               # noqa: BLE001
            continue
        axes = tuple(_axis_from_row(row, n) for n in range(1, dims + 1))
        program = SweepProgram(
            axes=axes,
            condition="" if _is_nan(row.get("condition")) else
            str(row.get("condition", "")),
            filename="" if _is_nan(row.get("filename_sweep")) else
            str(row.get("filename_sweep", "")),
            map_interpolated=bool(int(_f(row.get("interpolated"), 1) or 0)),
        )
        try:
            save_program(program, dst)
            written.append(dst)
        except OSError:
            pass
    return written


def _is_nan(v) -> bool:
    try:
        return v != v
    except Exception:                   # noqa: BLE001
        return False
