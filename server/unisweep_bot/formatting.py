"""Text the user reads.

Every timestamp is rendered in :data:`config.TZ` — the lab's zone — and
never in server-local time: the container runs UTC, so a naive
``datetime.now()`` would put every message eight hours in the past.
"""

from __future__ import annotations

import gzip
import json
import math
from datetime import datetime, timezone
from typing import Any, Optional

from . import config

STATE_ICON = {
    "idle": "⚪",
    "running": "🟢",
    "paused": "🟡",
    "finished": "✅",
    "stopped": "⛔",
    "error": "🔴",
}

KIND_LABEL = {
    "started": "sweep started",
    "finished": "sweep finished / stopped",
    "error": "errors",
    "guard": "guard trips",
    "paused": "pause and resume",
    "file": "each new data file",
    "silent": "rig went silent",
    "progress": "progress pings",
    "photo": "attach a plot when a sweep ends",
}

#: what a freshly linked chat gets.  The noisy kinds are off: a 2-D sweep
#: opens a file per row, and progress pings are for people who ask.
DEFAULT_PREFS = {
    "started": False,
    "finished": True,
    "error": True,
    "guard": True,
    "paused": False,
    "file": False,
    "silent": True,
    "photo": True,
    "progress_min": 0,          # 0 = off, otherwise minutes between pings
    "cmap": "viridis",
    "read": "",                 # last parameter this chat plotted
}


def prefs_of(link: dict) -> dict:
    out = dict(DEFAULT_PREFS)
    stored = (link or {}).get("prefs") or {}
    if isinstance(stored, str):
        try:
            stored = json.loads(stored)
        except ValueError:
            stored = {}
    if isinstance(stored, dict):
        out.update({k: v for k, v in stored.items() if k in DEFAULT_PREFS})
    return out


def now_tz() -> datetime:
    return datetime.now(config.TZ)


def local(dt: Optional[datetime]) -> str:
    if dt is None:
        return "never"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(config.TZ).strftime("%d %b %H:%M:%S")


def age_seconds(dt: Optional[datetime]) -> Optional[float]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - dt).total_seconds()


def fmt_duration(seconds) -> str:
    try:
        seconds = max(int(float(seconds)), 0)
    except (TypeError, ValueError):
        return "—"
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h} h {m:02d} m"
    if m:
        return f"{m} m {s:02d} s"
    return f"{s} s"


def fmt_age(seconds) -> str:
    if seconds is None:
        return "unknown"
    return fmt_duration(seconds) + " ago"


def fmt_value(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (int, float)):
        v = float(value)
        if math.isnan(v):
            return "NaN"
        if math.isinf(v):
            return "inf"
        return f"{v:.6g}"
    return str(value)


def split_message(text: str, limit: int = None) -> list:
    """Break on line boundaries so no chunk exceeds Telegram's cap."""
    limit = limit or config.TELEGRAM_MSG_LIMIT
    if len(text) <= limit:
        return [text]
    chunks, current = [], ""
    for line in text.split("\n"):
        while len(line) > limit:                       # one pathological line
            if current:
                chunks.append(current)
                current = ""
            chunks.append(line[:limit])
            line = line[limit:]
        if current and len(current) + 1 + len(line) > limit:
            chunks.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        chunks.append(current)
    return chunks


# ------------------------------------------------------------- payloads --
def unpack_snapshot(blob: bytes) -> Optional[dict]:
    if not blob:
        return None
    try:
        raw = gzip.decompress(blob) if blob[:2] == b"\x1f\x8b" else blob
        data = json.loads(raw.decode("utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:                                  # noqa: BLE001
        return None


# --------------------------------------------------------------- views ---
def rig_line(link: dict) -> str:
    state = (link.get("state") or {})
    if isinstance(state, str):
        try:
            state = json.loads(state)
        except ValueError:
            state = {}
    sweep = state.get("state", link.get("last_push_state") or "idle")
    icon = STATE_ICON.get(sweep, "⚪")
    seen = age_seconds(link.get("last_seen"))
    stale = "" if (seen is not None and seen < 180) else "  ·  not reporting"
    return f"{icon} {link.get('rig_name') or link.get('rig_id')} — {sweep}{stale}"


def status_text(link: dict, snapshot: Optional[dict],
                snap_age: Optional[float]) -> str:
    """The /status answer: what the rig is doing, and its latest readings."""
    state = link.get("state") or {}
    if isinstance(state, str):
        try:
            state = json.loads(state)
        except ValueError:
            state = {}
    sweep = state.get("state", link.get("last_push_state") or "idle")
    icon = STATE_ICON.get(sweep, "⚪")
    name = link.get("rig_name") or link.get("rig_id")
    lines = [f"{icon} <b>{esc(name)}</b> — {esc(sweep)}"]

    prog = state.get("progress") or {}
    if prog.get("total"):
        done, total = int(prog.get("done", 0)), int(prog["total"])
        pct = 100.0 * done / total if total else 0.0
        bar = _bar(pct)
        lines.append(f"{bar} {pct:.0f}%  ({done}/{total})")
    if prog.get("eta_s") is not None:
        lines.append(f"elapsed {fmt_duration(prog.get('elapsed_s'))} · "
                     f"ETA {fmt_duration(prog.get('eta_s'))}")

    program = state.get("program") or {}
    axes = program.get("axes") or []
    if axes:
        lines.append("")
        for i, ax in enumerate(axes, start=1):
            role = "fast" if i == len(axes) else ("slow" if i == len(axes) - 1
                                                  else f"axis {i}")
            lines.append(
                f"<code>ax{i}</code> {esc(ax.get('label', '?'))}: "
                f"{fmt_value(ax.get('start'))} → {fmt_value(ax.get('stop'))}"
                f"  <i>({role})</i>")
    if program.get("file"):
        lines.append(f"file <code>{esc(program['file'])}</code>")

    last = state.get("last_row") or {}
    if last:
        lines.append("")
        lines.append("<b>Latest readings</b>")
        lines.append("<pre>" + _kv_table(last) + "</pre>")

    lines.append("")
    lines.append(f"rig reported {fmt_age(age_seconds(link.get('last_seen')))}"
                 + (f" · data {fmt_age(snap_age)}"
                    if snap_age is not None else ""))
    return "\n".join(lines)


def table_text(snapshot: dict, rows: int = 12) -> str:
    """The tail of the data table — the 'snapshot of the data table'."""
    table = (snapshot or {}).get("table") or {}
    cols = list(table.get("columns") or [])
    data = list(table.get("rows") or [])[-rows:]
    if not cols or not data:
        return "No rows yet."
    keep = cols[:8]
    idx = [cols.index(c) for c in keep]
    widths = [max(len(c), 10) for c in keep]
    out = ["  ".join(c.rjust(w)[:w] for c, w in zip(keep, widths))]
    for row in data:
        cells = []
        for j, w in zip(idx, widths):
            cells.append(fmt_value(row[j] if j < len(row) else None)
                         .rjust(w)[:w])
        out.append("  ".join(cells))
    text = "\n".join(out)
    more = ("\n\n… showing the last %d of %d rows, %d of %d columns"
            % (len(data), table.get("total", len(data)), len(keep), len(cols)))
    return f"<pre>{esc(text)}</pre>{esc(more)}"


def stats_text(snapshot: dict) -> str:
    stats = (snapshot or {}).get("stats") or {}
    if not stats:
        return "No statistics yet."
    lines = [f"{'parameter':<22}{'min':>13}{'max':>13}{'mean':>13}{'last':>13}"]
    for name, s in list(stats.items())[:20]:
        lines.append(f"{name[:21]:<22}"
                     f"{fmt_value(s.get('min')):>13}"
                     f"{fmt_value(s.get('max')):>13}"
                     f"{fmt_value(s.get('mean')):>13}"
                     f"{fmt_value(s.get('last')):>13}")
    return "<pre>" + esc("\n".join(lines)) + "</pre>"


def _kv_table(mapping: dict, limit: int = 14) -> str:
    items = list(mapping.items())[:limit]
    width = max((len(k) for k, _ in items), default=8)
    return "\n".join(f"{k:<{width}}  {fmt_value(v):>14}" for k, v in items)


def _bar(pct: float, width: int = 14) -> str:
    filled = int(round(max(0.0, min(pct, 100.0)) / 100.0 * width))
    return "▓" * filled + "░" * (width - filled)


def esc(text: Any) -> str:
    """Escape for Telegram's HTML parse mode.

    Everything user- or instrument-supplied goes through here: parameter
    names contain ``<`` and ``&`` often enough that an unescaped message
    would simply fail to send.
    """
    return (str(text).replace("&", "&amp;")
            .replace("<", "&lt;").replace(">", "&gt;"))
