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

#: Preference key -> what a person calls it, and the word they type to
#: change it.  Order is the order /alerts prints them in: the ones people
#: actually want first.
KIND_LABEL = {
    "finished": "when a sweep ends",
    "error": "errors",
    "guard": "safety stops",
    "silent": "the computer going quiet",
    "started": "when a sweep starts",
    "paused": "pausing and resuming",
    "file": "every new data file",
    "photo": "a picture with the sweep-ended message",
    "progress": "progress updates",
}

#: What people type for each of them.  Generous on purpose — nobody
#: should have to guess whether it is "error" or "errors".
PREF_WORDS = {
    "finished": ("ends", "end", "finished", "finish", "done"),
    "error": ("errors", "error"),
    "guard": ("safety", "guard", "guards"),
    "silent": ("quiet", "silent", "silence", "offline"),
    "started": ("starts", "start", "started"),
    "paused": ("pause", "paused", "pausing"),
    "file": ("files", "file"),
    "photo": ("picture", "photo", "plot", "image"),
    "progress": ("progress",),
}


def pref_key(word: str) -> str:
    """Turn what somebody typed into a preference key, or ``''``."""
    word = str(word or "").strip().lower()
    for key, words in PREF_WORDS.items():
        if word == key or word in words:
            return key
    return ""

#: What a freshly linked chat gets.  The noisy kinds are off: a 2-D sweep
#: opens a file per row, and progress pings are for people who ask.
#:
#: ``photo`` is off too, and that one is about cost rather than noise: a
#: rendered plot is thousands of times the bytes of the sentence next to
#: it, and the sentence is what you actually read at 3 a.m.  Anyone who
#: wants the picture on every finish can switch it on in /notify, and
#: /plot is always a tap away.
DEFAULT_PREFS = {
    "started": False,
    "finished": True,
    "error": True,
    "guard": True,
    "paused": False,
    "file": False,
    "silent": True,
    "photo": False,
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
    """One setup, one line — for the list and for headers."""
    state = state_of(link)
    sweep = state.get("state", link.get("last_push_state") or "idle")
    icon = STATE_ICON.get(sweep, "⚪")
    seen = age_seconds(link.get("last_seen"))
    quiet = "" if (seen is not None and seen < 180) else "  ·  gone quiet"
    return (f"{icon} {link.get('rig_name') or link.get('rig_id')} "
            f"— {sweep}{quiet}")


def state_of(link: dict) -> dict:
    state = link.get("state") or {}
    if isinstance(state, str):
        try:
            state = json.loads(state)
        except ValueError:
            state = {}
    return state if isinstance(state, dict) else {}


def status_text(link: dict, snapshot: Optional[dict],
                snap_age: Optional[float]) -> str:
    """What the setup is doing, in the order somebody wants to know it."""
    state = state_of(link)
    sweep = state.get("state", link.get("last_push_state") or "idle")
    icon = STATE_ICON.get(sweep, "⚪")
    name = link.get("rig_name") or link.get("rig_id")
    lines = [f"{icon} <b>{esc(name)}</b> — {esc(sweep)}"]

    prog = state.get("progress") or {}
    if prog.get("total"):
        done, total = int(prog.get("done", 0)), int(prog["total"])
        pct = 100.0 * done / total if total else 0.0
        lines.append("")
        lines.append(f"{_bar(pct)} {pct:.0f}%   {done:,} of {total:,} points"
                     .replace(",", " "))
        if prog.get("eta_s") is not None:
            lines.append(f"{fmt_duration(prog.get('elapsed_s'))} in, "
                         f"about {fmt_duration(prog.get('eta_s'))} left")

    program = state.get("program") or {}
    axes = program.get("axes") or []
    if axes:
        lines.append("")
        width = max((len(str(a.get("label", "?"))) for a in axes), default=8)
        for ax in axes:
            lines.append(
                f"<code>{esc(str(ax.get('label', '?')).ljust(width))}  "
                f"{fmt_value(ax.get('start'))} → "
                f"{fmt_value(ax.get('stop'))}</code>")
    if program.get("file"):
        lines.append(f"<code>{esc(program['file'])}</code>")

    last = state.get("last_row") or {}
    if last:
        lines.append("")
        lines.append("<b>Latest</b>")
        lines.append("<pre>" + esc(_kv_table(last)) + "</pre>")

    lines.append("")
    lines.append(f"updated {esc(fmt_age(age_seconds(link.get('last_seen'))))}")
    return "\n".join(lines)


def table_text(snapshot: dict, rows: int = 12) -> str:
    """The most recent measured rows."""
    table = (snapshot or {}).get("table") or {}
    cols = list(table.get("columns") or [])
    data = list(table.get("rows") or [])[-rows:]
    if not cols or not data:
        return "No rows yet."
    keep = cols[:8]
    idx = [cols.index(c) for c in keep]
    # the writer marks swept columns "<device>.<param>_sweep"; that suffix
    # is for the file on disk, not for somebody reading a phone
    shown = [c[:-6] if c.endswith("_sweep") else c for c in keep]
    widths = [max(len(c), 10) for c in shown]
    out = ["  ".join(c.rjust(w)[:w] for c, w in zip(shown, widths))]
    for row in data:
        cells = []
        for j, w in zip(idx, widths):
            cells.append(fmt_value(row[j] if j < len(row) else None)
                         .rjust(w)[:w])
        out.append("  ".join(cells))
    text = "\n".join(out)
    total = int(table.get("total", len(data)))
    more = f"\nlast {len(data)} of {total} rows"
    if len(keep) < len(cols):
        more += f", {len(keep)} of {len(cols)} columns"
    return f"<pre>{esc(text)}</pre>{esc(more)}"


def stats_text(snapshot: dict) -> str:
    stats = (snapshot or {}).get("stats") or {}
    if not stats:
        return "Nothing measured yet."
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
