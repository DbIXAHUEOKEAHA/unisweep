"""The lab journal: what was run, when, and with what settings.

Two representations of the same thing, because they serve different
readers:

* ``journal/YYMMDD.md`` — append-only Markdown, one entry per run and per
  note, in the order things happened. This is the notebook: a person opens
  it and reads the day. Nothing ever rewrites a line, so it can be trusted
  the way a paper notebook is trusted.
* ``journal/journal.sqlite`` — the same records indexed, so "what did I
  measure on the 3rd", "every run that swept the gate" and "which run did
  this one come from" are queries rather than a grep.

**Nothing here is typed by the operator.** There is no intent field and no
campaign field, because a box asking "why are you running this?" is a box
that gets left empty, and a journal with half its entries blank is worse
than one with none. Instead the entry carries everything the sweep already
knows about itself — filename, every axis and its limits, the channels
read, the condition, the per-point script, each instrument's identity and
its ``loggable`` settings, the output options, the software revision.

Grouping and intent are then *read out* of that, not written into it. Runs
that swept the same channel on the same sample within the hour belong
together whether or not anyone said so; an assistant asked later opens the
journal and works out the connections from the record, which is exactly
the kind of judgement it is good at and the kind of typing a physicist at
2 a.m. is not.

Runs still link explicitly through ``derived_from`` when something knows
the link — an analysis run naming the sweep it came from.

Every method here swallows its exceptions. A journal that cannot be
written is a problem to report, never a reason to lose a measurement that
is already running.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime
from typing import Any, Optional, Sequence

__all__ = ["Journal", "journal_dir"]

_COLUMNS = {
    "run_id": "TEXT PRIMARY KEY",
    "started_at": "TEXT",
    "finished_at": "TEXT",
    "stopped": "INTEGER",
    "points": "INTEGER",
    "dimensions": "INTEGER",
    "lab": "TEXT",
    "sample": "TEXT",
    "git": "TEXT",
    "directory": "TEXT",
    "files": "TEXT",
    "program": "TEXT",
    "instruments": "TEXT",
    "derived_from": "TEXT",
}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id       TEXT PRIMARY KEY,
    started_at   TEXT,
    finished_at  TEXT,
    stopped      INTEGER,
    points       INTEGER,
    dimensions   INTEGER,
    lab          TEXT,
    sample       TEXT,
    git          TEXT,
    directory    TEXT,
    files        TEXT,
    program      TEXT,
    instruments  TEXT,
    derived_from TEXT
);
CREATE INDEX IF NOT EXISTS runs_started ON runs (started_at);
CREATE TABLE IF NOT EXISTS notes (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    at        TEXT,
    run_id    TEXT,
    author    TEXT,
    text      TEXT
);
CREATE INDEX IF NOT EXISTS notes_run ON notes (run_id);
"""


def journal_dir(core_dir: str) -> str:
    path = os.path.join(core_dir, "journal")
    os.makedirs(path, exist_ok=True)
    return path


def _now() -> datetime:
    return datetime.now()


def _loads(raw: Any) -> Any:
    if isinstance(raw, str) and raw:
        try:
            return json.loads(raw)
        except ValueError:
            return {}
    return raw


def _num(value: Any) -> str:
    """A number the way a person would write it in a notebook."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return str(value)
    if f == int(f) and abs(f) < 1e15:
        return str(int(f))
    return f"{f:g}"


class Journal:
    """Append-only record of runs and notes, with a queryable index."""

    def __init__(self, core_dir: str):
        self.core_dir = core_dir
        self._lock = threading.Lock()
        self.last_error = ""
        # even constructing must not raise: this object is built on the
        # measurement thread, and an unwritable disk is a thing to report
        # rather than a reason to lose a sweep
        try:
            self.dir = journal_dir(core_dir)
        except OSError as exc:
            self.dir = core_dir
            self.last_error = f"{type(exc).__name__}: {exc}"
        self.db_path = os.path.join(self.dir, "journal.sqlite")
        self._ensure()

    # ---- plumbing ------------------------------------------------------
    def _connect(self):
        # a fresh connection per operation: the engine thread, the GUI and
        # an agent's request thread all write here, and a sqlite3
        # connection belongs to the thread that made it
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure(self) -> None:
        try:
            with self._connect() as conn:
                conn.executescript(_SCHEMA)
                # a journal older than the code keeps its rows and gains
                # the new columns; losing the day's record to a schema
                # change would defeat the point of an append-only log
                have = {r["name"] for r in
                        conn.execute("PRAGMA table_info(runs)")}
                for name, decl in _COLUMNS.items():
                    if name not in have:
                        kind = decl.split()[0]
                        conn.execute(
                            f"ALTER TABLE runs ADD COLUMN {name} {kind}")
        except Exception as exc:                   # noqa: BLE001
            self.last_error = f"{type(exc).__name__}: {exc}"

    def markdown_path(self, when: Optional[datetime] = None) -> str:
        return os.path.join(self.dir,
                            (when or _now()).strftime("%y%m%d") + ".md")

    def _append(self, text: str, when: Optional[datetime] = None) -> None:
        path = self.markdown_path(when)
        try:
            new = not os.path.exists(path)
            with open(path, "a", encoding="utf-8") as fh:
                if new:
                    day = (when or _now()).strftime("%A %d %B %Y")
                    fh.write(f"# Lab journal — {day}\n")
                fh.write("\n" + text.rstrip() + "\n")
        except OSError as exc:
            self.last_error = str(exc)

    # ---- runs ----------------------------------------------------------
    def start_run(self, provenance, dimensions: int = 0,
                  derived_from: Sequence[str] = ()) -> str:
        """Record that a sweep has begun. Returns its run id."""
        run_id = getattr(provenance, "run_id", "") or ""
        try:
            program = getattr(provenance, "program", None)
            profile = getattr(provenance, "profile", None)
            sample = ""
            if profile is not None and getattr(profile, "sample", None):
                sample = json.dumps(dict(profile.sample), default=str)
            from .config import program_to_dict
            row = {
                "run_id": run_id,
                "started_at": getattr(provenance, "started_at", "")
                or _now().isoformat(timespec="seconds"),
                "finished_at": "", "stopped": 0, "points": 0,
                "dimensions": int(dimensions),
                "lab": getattr(profile, "lab", "") or "",
                "sample": sample,
                "git": (getattr(provenance, "env", {}) or {}).get("git", ""),
                "directory": "", "files": "[]",
                "program": json.dumps(program_to_dict(program), default=str)
                if program is not None else "{}",
                "instruments": json.dumps(
                    getattr(provenance, "devices", {}) or {}, default=str),
                "derived_from": json.dumps(list(derived_from)),
            }
            with self._lock, self._connect() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO runs ("
                    "run_id, started_at, finished_at, stopped, points,"
                    "dimensions, lab, sample, git, directory, files,"
                    "program, instruments, derived_from) VALUES ("
                    ":run_id,:started_at,:finished_at,:stopped,:points,"
                    ":dimensions,:lab,:sample,:git,:directory,:files,"
                    ":program,:instruments,:derived_from)", row)
            self._append(self._run_started_md(row))
        except Exception as exc:                   # noqa: BLE001
            self.last_error = f"{type(exc).__name__}: {exc}"
        return run_id

    def finish_run(self, run_id: str, stopped: bool = False,
                   points: int = 0, files: Sequence[str] = (),
                   directory: str = "") -> None:
        files = [str(f) for f in files]
        try:
            with self._lock, self._connect() as conn:
                conn.execute(
                    "UPDATE runs SET finished_at=?, stopped=?, points=?,"
                    " files=?, directory=? WHERE run_id=?",
                    (_now().isoformat(timespec="seconds"), int(bool(stopped)),
                     int(points), json.dumps(files), directory, run_id))
            self._append(self._run_finished_md(run_id, stopped, points,
                                               files, directory))
        except Exception as exc:                   # noqa: BLE001
            self.last_error = f"{type(exc).__name__}: {exc}"

    # ---- notes ---------------------------------------------------------
    def note(self, text: str, run_id: str = "", author: str = "") -> bool:
        """Write a line in the notebook.

        Not part of the measurement path and never required of the
        operator: this is where an assistant records what it concluded, or
        a person records that the helium was low.
        """
        text = str(text or "").strip()
        if not text:
            return False
        when = _now()
        try:
            with self._lock, self._connect() as conn:
                conn.execute(
                    "INSERT INTO notes (at, run_id, author, text)"
                    " VALUES (?,?,?,?)",
                    (when.isoformat(timespec="seconds"), run_id, author,
                     text))
            head = f"### {when.strftime('%H:%M')} · note"
            if author:
                head += f" · {author}"
            if run_id:
                head += f" · run {run_id}"
            self._append(f"{head}\n\n{text}", when)
            return True
        except Exception as exc:                   # noqa: BLE001
            self.last_error = f"{type(exc).__name__}: {exc}"
            return False

    # ---- reading -------------------------------------------------------
    def runs(self, limit: int = 20, since: str = "") -> list:
        sql = "SELECT * FROM runs"
        args: list = []
        if since:
            sql += " WHERE started_at >= ?"
            args.append(str(since))
        sql += " ORDER BY started_at DESC LIMIT ?"
        args.append(int(limit))
        return [self._row(r) for r in self._query(sql, args)]

    def run(self, run_id: str) -> Optional[dict]:
        rows = self._query("SELECT * FROM runs WHERE run_id = ?", [run_id])
        return self._row(rows[0]) if rows else None

    def notes(self, limit: int = 20, run_id: str = "") -> list:
        sql = "SELECT * FROM notes"
        args: list = []
        if run_id:
            sql += " WHERE run_id = ?"
            args.append(run_id)
        sql += " ORDER BY id DESC LIMIT ?"
        args.append(int(limit))
        return [dict(r) for r in self._query(sql, args)]

    def _query(self, sql: str, args: Sequence[Any]) -> list:
        try:
            with self._connect() as conn:
                return list(conn.execute(sql, list(args)).fetchall())
        except Exception as exc:                   # noqa: BLE001
            self.last_error = f"{type(exc).__name__}: {exc}"
            return []

    @staticmethod
    def _row(row) -> dict:
        out = dict(row)
        for key in ("files", "program", "instruments", "derived_from",
                    "sample"):
            if isinstance(out.get(key), str) and out[key]:
                out[key] = _loads(out[key])
        out["stopped"] = bool(out.get("stopped"))
        return out

    # ---- Markdown rendering --------------------------------------------
    @staticmethod
    def _axis_md(index: int, axis: dict, dimensions: int) -> str:
        role = {1: "master", 2: "slave", 3: "slave-slave"}.get(
            index, f"axis {index}") if dimensions > 1 else "axis"
        head = (f"- **{role}** — `{axis.get('device', '?')}."
                f"{axis.get('parameter', '?')}` "
                f"{_num(axis.get('start'))} → {_num(axis.get('stop'))}")
        bits = []
        if axis.get("count_mode") == "step":
            bits.append(f"step {_num(axis.get('rate'))}")
        else:
            bits.append(f"{_num(axis.get('rate'))}/s")
        bits.append(f"{_num(axis.get('delay'))} s/point")
        if axis.get("back_rate") is not None:
            bits.append(f"back {_num(axis.get('back_rate'))}/s")
        if axis.get("back_delay") is not None:
            bits.append(f"back {_num(axis.get('back_delay'))} s/point")
        walks = int(axis.get("walks") or 1)
        if walks != 1:
            bits.append(f"{walks} walks")
        if axis.get("snake"):
            bits.append("snake")
        if axis.get("force_stepwise"):
            bits.append("stepwise")
        points = axis.get("manual_points")
        if points:
            name = axis.get("manual_name") or "manual"
            bits.append(f"{len(points)} manual points ({name})")
        return head + " · " + ", ".join(bits)

    @classmethod
    def _program_md(cls, program: dict, dimensions: int) -> list:
        lines: list = []
        name = program.get("filename") or ""
        lines.append(f"- file: `{name}`" if name
                     else "- file: auto-named (YYMMDD-N)")
        for i, axis in enumerate(program.get("axes") or (), start=1):
            lines.append(cls._axis_md(i, axis, dimensions))
        reads = program.get("reads") or ()
        if reads:
            lines.append("- reads: "
                         + ", ".join(f"`{r}`" for r in reads))
        out = []
        if not program.get("approach_start", True):
            out.append("started from where the instruments stood")
        if program.get("to_zero_on_finish"):
            out.append("to zero on finish")
        if dimensions > 1 and program.get("save_maps", True):
            style = program.get("map_style", "grid")
            out.append(f"maps: {style}"
                       + (", interpolated"
                          if program.get("map_interpolated") else "")
                       + (", uniform grid"
                          if program.get("map_uniform") else "")
                       + (", images" if program.get("map_images") else ""))
        elif dimensions > 1:
            out.append("no maps")
        if out:
            lines.append("- output: " + "; ".join(out))
        return lines

    @staticmethod
    def _blocks_md(program: dict) -> list:
        """Condition and script go below the bullets, verbatim. A fence
        inside a list item breaks the list, and these are the two things a
        reader most wants to see exactly as they were run."""
        lines: list = []
        condition = (program.get("condition") or "").strip()
        if condition:
            lines += ["", "**Condition**", "", "```", condition, "```"]
        script = (program.get("script") or "").strip()
        if script:
            lines += ["", "**Per-point script**", "", "```python", script,
                      "```"]
        return lines

    @staticmethod
    def _instruments_md(instruments: dict) -> list:
        if not instruments:
            return []
        lines = ["- instruments:"]
        for address, entry in instruments.items():
            entry = entry or {}
            head = f"  - `{address}`"
            driver = entry.get("driver")
            if driver:
                head += f" — {driver}"
            alias = entry.get("alias") or entry.get("role")
            if alias:
                head += f" ({alias})"
            idn = entry.get("idn")
            if idn:
                head += f" — {str(idn).strip()}"
            if entry.get("error"):
                head += f" — unreachable: {entry['error']}"
            lines.append(head)
            settings = entry.get("loggable") or {}
            for key, value in settings.items():
                if isinstance(value, dict) and "error" in value:
                    lines.append(f"    - {key}: (error) {value['error']}")
                else:
                    lines.append(f"    - {key}: {value}")
        return lines

    @classmethod
    def _run_started_md(cls, row: dict) -> str:
        when = str(row.get("started_at", ""))[11:16] or "--:--"
        dims = int(row.get("dimensions") or 0)
        shape = f"{dims}-D " if dims else ""
        lines = [f"## {when} · {shape}run `{row['run_id']}` started", ""]
        program = _loads(row.get("program")) or {}
        if not dims:
            dims = len(program.get("axes") or ())
        lines += cls._program_md(program, dims)
        lines += cls._instruments_md(_loads(row.get("instruments")) or {})
        sample = _loads(row.get("sample")) or {}
        if sample:
            lines.append("- sample: " + ", ".join(
                f"{k} {v}" for k, v in sample.items()))
        if row.get("lab"):
            lines.append(f"- lab: {row['lab']}")
        if row.get("git"):
            lines.append(f"- software: {row['git']}")
        lines += cls._blocks_md(program)
        return "\n".join(lines)

    @staticmethod
    def _run_finished_md(run_id: str, stopped: bool, points: int,
                         files: Sequence[str], directory: str = "") -> str:
        when = _now().strftime("%H:%M")
        verb = "stopped" if stopped else "finished"
        lines = [f"## {when} · run `{run_id}` {verb} — {points} points, "
                 f"{len(files)} file(s)", ""]
        if directory:
            lines.append(f"- in `{directory}`")
        for path in list(files)[:12]:
            lines.append(f"- `{os.path.basename(path)}`")
        if len(files) > 12:
            lines.append(f"- … and {len(files) - 12} more")
        return "\n".join(lines)
