"""What produced this file.

A CSV of numbers is not a measurement. Six months on, the columns say
``GPIB0::1::INSTR.x`` and nothing says what the lock-in time constant was,
which gate range was safe, which driver version spoke to the magnet, or
why anyone ran it. That context exists only while the sweep is running,
and this module writes it down before it is lost.

Every data file gets a JSON sidecar beside it — ``250908-1.csv`` gets
``250908-1.json`` — carrying:

* the complete :class:`~unisweep.core.config.SweepProgram` that produced it;
* the instruments: address, driver, ``IDN`` string, and every parameter the
  driver lists as ``loggable`` (the convention ``sr830.py`` already uses for
  "settings worth writing in the notebook");
* a snapshot of the lab profile — aliases, units, limits, constants — so a
  reader knows what the numbers mean without needing the profile file;
* the environment: git revision, Python, platform, host, and when it ran.

Nothing here is typed by the operator. Everything is read from what the
sweep already is, because a field asking "why are you running this?" gets
left empty. A reader that wants intent — a person or an assistant — infers
it from the programs, the channels and how the runs sit next to each other.

Two decisions worth knowing:

**Instruments are read once per sweep, not once per file.** A 2-D map opens
a file per row; polling every instrument's loggables at each rotation would
add hundreds of round trips to a measurement. The snapshot is taken at the
start and repeated into each sidecar, which is a copy of JSON rather than a
copy of instrument traffic.

**The sidecar is written when the file opens** and updated when it closes.
A sweep that dies overnight still leaves a record of what it was doing;
that is precisely the run whose provenance you want.
"""

from __future__ import annotations

import json
import os
import platform
import socket
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional, Sequence

__all__ = ["SCHEMA_VERSION", "sidecar_path", "read_sidecar", "git_revision",
           "environment", "device_snapshot", "RunProvenance", "new_run_id"]

SCHEMA_VERSION = 1


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def new_run_id() -> str:
    """Sortable and unique enough to name a run in a journal."""
    import secrets
    return (datetime.now().strftime("%y%m%d-%H%M%S") + "-"
            + secrets.token_hex(2))


def sidecar_path(data_path: str) -> str:
    return os.path.splitext(data_path)[0] + ".json"


def read_sidecar(data_path: str) -> Optional[dict]:
    """The record beside a data file, or None. Never raises."""
    try:
        with open(sidecar_path(data_path), "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def git_revision(core_dir: str) -> str:
    """The checkout's commit, with ``+dirty`` when the tree has changes.

    Which version of the software took the data is the first thing anyone
    asks when two runs disagree.
    """
    if not os.path.isdir(os.path.join(core_dir, ".git")):
        return ""
    try:
        rev = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=core_dir,
            capture_output=True, text=True, timeout=5)
        if rev.returncode != 0:
            return ""
        head = rev.stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain"], cwd=core_dir,
            capture_output=True, text=True, timeout=5)
        if dirty.returncode == 0 and dirty.stdout.strip():
            head += "+dirty"
        return head
    except (OSError, subprocess.SubprocessError):
        return ""


def environment(core_dir: str) -> dict:
    out = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "host": "",
        "git": git_revision(core_dir),
        "core_dir": core_dir,
    }
    try:
        out["host"] = socket.gethostname()
    except OSError:                                # noqa: BLE001
        pass
    return out


def device_snapshot(registry, addresses: Sequence[str],
                    profile=None) -> dict:
    """Identity and settings of each instrument, read once.

    ``loggable`` is the existing driver convention (see ``sr830.py``): a
    list of getter names whose values are worth recording — time constant,
    sensitivity, reference frequency. Anything that fails to read is
    recorded as an error against that name rather than dropped, because
    "the instrument would not answer" is itself worth knowing.
    """
    out: dict = {}
    for address in dict.fromkeys(addresses):       # de-duplicated, ordered
        entry: dict = {"address": address}
        try:
            adapter = registry.connect(address)
        except Exception as exc:                   # noqa: BLE001
            entry["error"] = f"{type(exc).__name__}: {exc}"
            out[address] = entry
            continue
        entry["driver"] = type(getattr(adapter, "raw", adapter)).__name__
        try:
            entry["idn"] = str(adapter.idn())
        except Exception as exc:                   # noqa: BLE001
            entry["idn_error"] = f"{type(exc).__name__}: {exc}"
        settings: dict = {}
        for name in list(getattr(adapter.raw, "loggable", []) or []):
            try:
                value = getattr(adapter.raw, str(name))()
            except Exception as exc:               # noqa: BLE001
                settings[str(name)] = {"error":
                                       f"{type(exc).__name__}: {exc}"}
                continue
            settings[str(name)] = _plain(value)
        if settings:
            entry["loggable"] = settings
        if profile is not None:
            device = profile.device(address)
            if device is not None:
                for key in ("alias", "role", "notes"):
                    value = getattr(device, key, "")
                    if value:
                        entry[key] = value
        out[address] = entry
    return out


def _plain(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    item = getattr(value, "item", None)            # numpy scalar
    if callable(item):
        try:
            return _plain(item())
        except Exception:                          # noqa: BLE001
            pass
    return str(value)


def _profile_snapshot(profile) -> dict:
    """Enough of the lab profile that a reader needs nothing else."""
    if profile is None or getattr(profile, "is_empty", True):
        return {}
    out: dict = {
        "lab": profile.lab,
        "path": profile.path,
        "autonomy": profile.autonomy,
        "sample": dict(profile.sample),
        "constants": dict(profile.constants),
        "derived": {name: channel.expression
                    for name, channel in profile.derived.items()},
        "parameters": {},
    }
    for address, device in profile.devices.items():
        for name, spec in device.parameters.items():
            entry = {k: v for k, v in (
                ("alias", spec.alias), ("unit", spec.unit),
                ("quantity", spec.quantity)) if v}
            if spec.bounded:
                entry["range"] = spec.range_text()
            if entry:
                out["parameters"][f"{address}.{name}"] = entry
    return out


# ---------------------------------------------------------------------------
@dataclass
class RunProvenance:
    """The context of one sweep, and the sidecars it writes."""

    core_dir: str
    program: Any = None                 # SweepProgram
    profile: Any = None                 # LabProfile
    registry: Any = None
    run_id: str = field(default_factory=new_run_id)
    started_at: str = ""
    devices: dict = field(default_factory=dict)
    env: dict = field(default_factory=dict)
    files: list = field(default_factory=list)

    # ---- capture ------------------------------------------------------
    def capture(self) -> "RunProvenance":
        """Read the things that are only true at the start. Never raises:
        a sweep must not fail because its paperwork did."""
        self.started_at = _now()
        try:
            self.env = environment(self.core_dir)
        except Exception:                          # noqa: BLE001
            self.env = {}
        addresses: list = []
        try:
            for axis in self.program.axes:
                addresses.append(axis.device)
            for read in self.program.reads:
                addresses.append(str(read).rpartition(".")[0])
        except Exception:                          # noqa: BLE001
            pass
        if self.registry is not None:
            try:
                self.devices = device_snapshot(self.registry, addresses,
                                               self.profile)
            except Exception:                      # noqa: BLE001
                self.devices = {}
        return self

    # ---- the record ---------------------------------------------------
    def record_for(self, data_path: str, outer_values: Sequence[float] = (),
                   columns: Sequence[str] = ()) -> dict:
        from .config import program_to_dict
        try:
            program = program_to_dict(self.program) if self.program else {}
        except Exception:                          # noqa: BLE001
            program = {}
        return {
            "schema": SCHEMA_VERSION,
            "run_id": self.run_id,
            "file": os.path.basename(data_path),
            "columns": list(columns),
            "outer_axis_values": [float(v) for v in outer_values],
            "started_at": self.started_at,
            "file_opened_at": _now(),
            "file_closed_at": "",
            "rows": 0,
            "program": program,
            "instruments": self.devices,
            "lab_profile": _profile_snapshot(self.profile),
            "environment": self.env,
        }

    # ---- writing ------------------------------------------------------
    def write(self, data_path: str, outer_values: Sequence[float] = (),
              columns: Sequence[str] = ()) -> str:
        record = self.record_for(data_path, outer_values, columns)
        path = _dump(sidecar_path(data_path), record)
        if path and data_path not in self.files:
            self.files.append(data_path)
        return path

    @staticmethod
    def close(data_path: str, rows: int) -> None:
        """Stamp the row count and closing time onto an existing sidecar."""
        path = sidecar_path(data_path)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                record = json.load(fh)
        except (OSError, ValueError):
            return
        record["rows"] = int(rows)
        record["file_closed_at"] = _now()
        _dump(path, record)

    @staticmethod
    def discard(data_path: str) -> None:
        """Remove the sidecar of a data file that was deleted empty."""
        try:
            os.remove(sidecar_path(data_path))
        except OSError:
            pass


def _dump(path: str, record: dict) -> str:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(record, fh, indent=2, default=str)
        return path
    except OSError:
        return ""
