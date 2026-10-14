"""What produced this file.

A CSV of numbers is not a measurement. Six months on, the columns say
``GPIB0::1::INSTR.x`` and nothing says what the lock-in time constant was,
which gate range was safe, which driver version spoke to the magnet, or
why anyone ran it. That context exists only while the sweep is running,
and this module writes it down before it is lost.

Every sweep gets ONE record beside its data — ``<run id>.run.json`` in the
data folder — carrying:

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

Three decisions worth knowing:

**One record per sweep, not one per file.** A 2-D or 3-D map opens a new
data file for every line, and this used to write a full sidecar beside each
of them — program, every instrument, the whole lab profile, twice per line.
A 31 x 81 map meant five thousand writes of the same few tens of kilobytes.
Now the record is written when the sweep starts, rewritten only if the
program is edited while it runs, and completed once at the end with the
list of files it produced.

**A data file still resolves to a full record.** :func:`read_sidecar` takes
any data file and returns the same shape it always did, by finding the run
record that owns it. A file's row count is read from the file itself until
the run is finished, so even a sweep that died overnight answers correctly —
that is precisely the run whose provenance you want, and its record was
written before the first point. Per-file sidecars from older runs are still
read as they are.

**An edit mid-run is recorded, not lost.** Changing a limit or a speed while
a sweep runs updates the record's program and appends what changed, when,
to its ``edits`` list, so the record describes the sweep that actually ran
rather than the one that was started.
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
           "run_record_path", "describe_changes",
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


RUN_SUFFIX = ".run.json"


def run_record_path(directory: str, run_id: str) -> str:
    return os.path.join(directory, f"{run_id}{RUN_SUFFIX}")


def _load(path: str) -> Optional[dict]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _file_index(name: str) -> Optional[int]:
    stem = os.path.splitext(name)[0]
    tail = stem.rpartition("-")[2]
    return int(tail) if tail.isdigit() else None


def _find_run(data_path: str) -> Optional[dict]:
    """The run record that owns a data file.

    A finished run lists its files by name. An unfinished one — a sweep that
    is still going, or one that died — does not yet, but every file it opens
    takes the next index after its ``first_index`` under its ``base`` name,
    so the run with the highest first_index not above the file's own index
    is the one that wrote it.
    """
    directory = os.path.dirname(os.path.abspath(data_path))
    name = os.path.basename(data_path)
    try:
        candidates = [f for f in os.listdir(directory) if f.endswith(RUN_SUFFIX)]
    except OSError:
        return None
    runs = [r for r in (_load(os.path.join(directory, f)) for f in candidates)
            if isinstance(r, dict)]
    for run in runs:
        if any(e.get("file") == name for e in run.get("files") or ()):
            return run
    index = _file_index(name)
    if index is None:
        return None
    best = None
    for run in runs:
        base = str(run.get("base") or "")
        first = run.get("first_index")
        if not base or not name.startswith(base) or not isinstance(first, int):
            continue
        if first <= index and (best is None or first > best["first_index"]):
            best = run
    return best


def _csv_header(data_path: str) -> list:
    try:
        with open(data_path, "r", encoding="utf-8", newline="") as fh:
            first = fh.readline().rstrip("\r\n")
    except OSError:
        return []
    return first.split(",") if first else []


def _csv_rows(data_path: str) -> int:
    try:
        with open(data_path, "r", encoding="utf-8", newline="") as fh:
            return max(sum(1 for _ in fh) - 1, 0)
    except OSError:
        return 0


def _file_view(run: dict, data_path: str) -> dict:
    """One file's record, in the shape a per-file sidecar always had."""
    name = os.path.basename(data_path)
    entry = next((e for e in run.get("files") or () if e.get("file") == name),
                 None)
    view = {k: v for k, v in run.items() if k != "files"}
    view["file"] = name
    if entry is not None:
        view["columns"] = list(entry.get("columns") or ())
        view["outer_axis_values"] = list(entry.get("outer_axis_values") or ())
        view["file_opened_at"] = entry.get("opened_at", "")
        view["file_closed_at"] = entry.get("closed_at", "")
        view["rows"] = int(entry.get("rows", 0))
    else:
        # the run has not finished yet: the file itself is the evidence
        view["columns"] = _csv_header(data_path)
        view["outer_axis_values"] = []
        view["file_opened_at"] = ""
        view["file_closed_at"] = ""
        view["rows"] = _csv_rows(data_path)
    return view


def read_sidecar(data_path: str) -> Optional[dict]:
    """The record of what produced a data file, or None. Never raises.

    A per-file sidecar from an older run is returned as it is. Otherwise
    the run record that owns the file is found and presented in the same
    per-file shape, so nothing that reads provenance has to know the
    difference.
    """
    try:
        legacy = _load(sidecar_path(data_path))
        if legacy is not None:
            return legacy
        run = _find_run(data_path)
        return _file_view(run, data_path) if run is not None else None
    except Exception:                              # noqa: BLE001
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
    files: list = field(default_factory=list)     # data paths, in order
    # where the run's files go, and the index its first one takes — what
    # lets a file of an unfinished run find this record
    directory: str = ""
    base: str = ""
    first_index: int = 0
    edits: list = field(default_factory=list)
    finished_at: str = ""
    stopped: bool = False
    points: int = 0
    writes: int = 0                               # how often the record hit disk
    _entries: dict = field(default_factory=dict)  # path -> that file's facts
    _seen_version: Any = None
    _baseline: Any = None

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
    def _program_dict(self, program=None) -> dict:
        from .config import program_to_dict
        try:
            source = self.program if program is None else program
            return program_to_dict(source) if source is not None else {}
        except Exception:                          # noqa: BLE001
            return {}

    def record(self) -> dict:
        """The whole run, as it is written to disk."""
        return {
            "schema": SCHEMA_VERSION,
            "run_id": self.run_id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "stopped": self.stopped,
            "points": self.points,
            "directory": self.directory,
            "base": self.base,
            "first_index": self.first_index,
            "program": self._program_dict(),
            "edits": list(self.edits),
            "instruments": self.devices,
            "lab_profile": _profile_snapshot(self.profile),
            "environment": self.env,
            "files": [self._entries[p] for p in self.files
                      if p in self._entries],
        }

    def record_for(self, data_path: str, outer_values: Sequence[float] = (),
                   columns: Sequence[str] = ()) -> dict:
        """One file's record in the per-file shape, from what is in memory."""
        entry = self._entries.get(data_path) or {
            "file": os.path.basename(data_path),
            "columns": list(columns),
            "outer_axis_values": [float(v) for v in outer_values],
            "opened_at": _now(), "closed_at": "", "rows": 0}
        view = {k: v for k, v in self.record().items() if k != "files"}
        view.update({"file": entry["file"], "columns": entry["columns"],
                     "outer_axis_values": entry["outer_axis_values"],
                     "file_opened_at": entry["opened_at"],
                     "file_closed_at": entry["closed_at"],
                     "rows": entry["rows"]})
        return view

    def _save(self) -> str:
        if not self.directory:
            return ""
        path = _dump(run_record_path(self.directory, self.run_id),
                     self.record())
        if path:
            self.writes += 1
        return path

    # ---- the run's life -------------------------------------------------
    def begin(self, directory: str, base: str, first_index: int) -> str:
        """Write the record once, before the first point.

        Everything heavy — the program, every instrument, the lab profile,
        the environment — goes to disk here and is not written again unless
        the program changes. A sweep that dies overnight leaves this behind.
        """
        self.directory, self.base = directory, base
        self.first_index = int(first_index)
        self._baseline = self._program_dict()
        return self._save()

    def write(self, data_path: str, outer_values: Sequence[float] = (),
              columns: Sequence[str] = ()) -> str:
        """A data file has opened. Remembered, NOT written: the run record
        is completed once at the end, rather than rewritten for every line
        of a map."""
        self._entries[data_path] = {
            "file": os.path.basename(data_path),
            "columns": list(columns),
            "outer_axis_values": [float(v) for v in outer_values],
            "opened_at": _now(), "closed_at": "", "rows": 0}
        if data_path not in self.files:
            self.files.append(data_path)
        return run_record_path(self.directory, self.run_id) \
            if self.directory else ""

    def close(self, data_path: str, rows: int) -> None:
        entry = self._entries.get(data_path)
        if entry is not None:
            entry["rows"] = int(rows)
            entry["closed_at"] = _now()

    def discard(self, data_path: str) -> None:
        """A data file was deleted empty: it never existed as far as the
        record is concerned."""
        self._entries.pop(data_path, None)
        if data_path in self.files:
            self.files.remove(data_path)

    def track(self, live) -> list:
        """Record an edit made while the sweep runs.

        Cheap when nothing changed — one integer comparison per call, so it
        can sit in the measurement loop. When the live program has moved on,
        the differences from the last recorded program are appended to
        ``edits`` and the record is rewritten, so it describes the sweep
        that actually ran. Returns the changes, for the journal.
        """
        try:
            version = live.version
        except Exception:                          # noqa: BLE001
            return []
        if version == self._seen_version:
            return []
        self._seen_version = version
        current = self._program_dict(live.get())
        if self._baseline is None:
            self._baseline = current
            return []
        changes = _program_changes(self._baseline, current)
        if not changes:
            return []
        stamp = _now()
        for change in changes:
            change["at"] = stamp
        self.edits.extend(changes)
        self.program = live.get()
        self._baseline = current
        self._save()
        return changes

    def finish(self, stopped: bool = False, points: int = 0) -> str:
        """Complete the record once, with the files the run produced."""
        self.finished_at = _now()
        self.stopped = bool(stopped)
        self.points = int(points)
        return self._save()


def _program_changes(before: dict, after: dict) -> list:
    """What differs between two program dicts, field by field and per axis."""
    out: list = []
    axes_a = list(before.get("axes") or ())
    axes_b = list(after.get("axes") or ())
    for i in range(max(len(axes_a), len(axes_b))):
        a = axes_a[i] if i < len(axes_a) else {}
        b = axes_b[i] if i < len(axes_b) else {}
        for key in sorted(set(a) | set(b)):
            if a.get(key) != b.get(key):
                out.append({"axis": i + 1, "field": key,
                            "from": a.get(key), "to": b.get(key)})
    for key in sorted((set(before) | set(after)) - {"axes"}):
        if before.get(key) != after.get(key):
            out.append({"axis": None, "field": key,
                        "from": before.get(key), "to": after.get(key)})
    return out


def describe_changes(changes: list) -> str:
    """One line for the journal: 'axis 3 stop 35 -> 30; axis 3 rate 3 -> 2'."""
    parts = []
    for c in changes:
        where = f"axis {c['axis']} " if c.get("axis") else ""
        parts.append(f"{where}{c['field']} {c['from']} \u2192 {c['to']}")
    return "; ".join(parts)


def _dump(path: str, record: dict) -> str:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(record, fh, indent=2, default=str)
        return path
    except OSError:
        return ""
