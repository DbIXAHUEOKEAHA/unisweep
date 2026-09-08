"""Everything a person can do in the chat.

The Unisweep settings page does exactly one thing: it shows a six-digit
code.  Sending that code here is the entire sign-up — no chat id to look
up, nothing to type on the lab computer — and from that moment this file
is the whole interface.

It is commands and plain sentences, with no inline keyboards anywhere.
Buttons look helpful and are not: they go stale the moment the sweep
moves on, they cannot be typed from a watch or a search bar, and half of
them only existed to make up for a command somebody would otherwise have
had to remember.  There are nine commands, and none of them needs an
argument to do something useful.

The words are the ones a person in a lab would use.  "Line scan", not "a
read parameter against the innermost axis".
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional, Tuple

from telegram import Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from . import config, db, render
from .formatting import (DEFAULT_PREFS, KIND_LABEL, age_seconds, esc,
                         fmt_age, pref_key, prefs_of, rig_line,
                         split_message, state_of, stats_text, status_text,
                         table_text, unpack_snapshot)

logger = logging.getLogger(__name__)

DB_BUSY = ("⚠️ I can't reach the database just now. Nothing is lost — "
           "try again in a minute.")
NOT_LINKED = ("You're not connected to a measurement setup yet.\n\n"
              "On the computer running Unisweep, open <b>Settings → "
              "Telegram notifications</b> and press <b>Generate code</b>. "
              "Send me the six digits and you're in.")

HELP = """<b>What I can do</b>

/status — how the sweep is going
/data — the latest numbers
/line — line scan of one parameter
/map — 2-D map of one parameter
/stats — smallest, largest, average

/setups — your setups, and which one I'm answering about
/alerts — what I message you about
/unlink — stop messages from this setup"""

CONTROL_HELP = """

/pause /resume — pause or carry on
/stop /zero — stop the sweep (asks twice)"""

CONTROL_WORDS = {
    "pause": "pause the sweep",
    "resume": "resume the sweep",
    "stop": "stop the sweep",
    "to_zero": "stop the sweep and ramp everything to zero",
}

#: (chat, command) -> when it was asked for.  Stopping a sweep is not
#: something to do on a mistyped character, so it takes two goes; keeping
#: that in memory is fine, because forgetting it just means asking again.
_PENDING: dict = {}
CONFIRM_WINDOW_S = 60.0


# ------------------------------------------------------------- plumbing --
async def say(update: Update, text: str) -> None:
    message = update.effective_message
    for chunk in split_message(text):
        try:
            if message is not None:
                await message.reply_text(chunk, parse_mode=ParseMode.HTML,
                                         disable_web_page_preview=True)
            elif update.effective_chat is not None:
                await update.effective_chat.send_message(
                    chunk, parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True)
        except BadRequest as exc:
            logger.warning("reply failed: %s", exc)


async def _active_link(chat_id: int) -> Tuple[Optional[dict], Optional[str]]:
    """The setup this chat is currently asking about.

    Returns ``(link, error_text)``.  A database failure produces an error
    string, never "you have no setups" — the two are different facts and
    the person must not be told the wrong one.
    """
    links = await asyncio.to_thread(db.links_for_chat, chat_id)
    if links is None:
        return None, DB_BUSY
    if not links:
        return None, NOT_LINKED
    if len(links) == 1:
        return links[0], None
    chat = await asyncio.to_thread(db.chat_get, chat_id)
    if chat is None:
        return None, DB_BUSY
    active = (chat or {}).get("active_rig")
    for link in links:
        if link["rig_id"] == active:
            return link, None
    return links[0], None


async def _snapshot_for(rig_id: str):
    stored = await asyncio.to_thread(db.snapshot_get, rig_id)
    if stored is None:
        return None, None, DB_BUSY
    if not stored:
        return {}, None, None
    data = unpack_snapshot(stored["payload"]) or {}
    return data, age_seconds(stored["updated_at"]), None


async def _request_fresh(rig_id: str, chat_id: int) -> None:
    """Ask the setup to push now, and give it a moment to answer.

    It polls for commands on its own heartbeat, so this shortens the wait
    rather than guaranteeing anything; whatever arrives (or does not) the
    caller still draws and says how old the data is.
    """
    before = await asyncio.to_thread(db.snapshot_age_marker, rig_id)
    await asyncio.to_thread(db.command_add, rig_id, "snapshot", {}, chat_id)
    waited = 0.0
    while waited < config.SNAPSHOT_WAIT_S:
        await asyncio.sleep(2.0)
        waited += 2.0
        marker = await asyncio.to_thread(db.snapshot_age_marker, rig_id)
        if marker is not None and marker != before:
            return


def _title(link: dict) -> str:
    return esc(link.get("rig_name") or link.get("rig_id"))


# -------------------------------------------------------------- basics ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    await asyncio.to_thread(db.chat_get, chat_id)
    links = await asyncio.to_thread(db.links_for_chat, chat_id)
    if links:
        await status(update, context)
        return
    await say(update,
              "👋 <b>Unisweep</b>\n\n"
              "I watch your measurements and tell you when a sweep ends, "
              "when something goes wrong, and when the measurement computer "
              "goes quiet. You can also ask me for the numbers or a plot at "
              "any time.\n\n"
              "<b>To connect a setup</b>\n"
              "In Unisweep: <b>Settings → Telegram notifications → Generate "
              "code</b>, then send me the six digits.")


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    link, err = await _active_link(update.effective_chat.id)
    text = HELP
    if link and link.get("allow_control"):
        text += CONTROL_HELP
    if err == NOT_LINKED:
        text = NOT_LINKED
    await say(update, text)


async def whoami(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await say(update, f"Your Telegram id is <code>"
                      f"{update.effective_chat.id}</code> — that's the "
                      f"number Unisweep lists you under.")


# -------------------------------------------------------------- pairing --
#: chat_id -> times of wrong codes.  Five guesses per window against
#: 900 000 possibilities is not a searchable space, and keeping the count
#: in memory means a restart can never lock somebody out for good.
_ATTEMPTS: dict = {}


def _too_many_attempts(chat_id: int) -> bool:
    now = time.monotonic()
    tries = [t for t in _ATTEMPTS.get(chat_id, [])
             if now - t < config.PAIR_ATTEMPT_WINDOW_S]
    _ATTEMPTS[chat_id] = tries
    return len(tries) >= config.PAIR_MAX_ATTEMPTS


def _record_attempt(chat_id: int) -> None:
    _ATTEMPTS.setdefault(chat_id, []).append(time.monotonic())


def _display_name(update: Update) -> str:
    user = update.effective_user
    if user is None:
        return ""
    name = " ".join(p for p in (user.first_name, user.last_name) if p)
    if user.username:
        name = f"{name} (@{user.username})".strip()
    return name[:80]


async def _redeem(update: Update, digits: str) -> None:
    """Spend a pairing code.

    There is no ``/link`` command: six digits *are* a code, so typing a
    word in front of them is a rule to remember for no reason.
    """
    chat_id = update.effective_chat.id
    if _too_many_attempts(chat_id):
        await say(update, "That's a few wrong codes now. Give it a few "
                          "minutes, then try a freshly generated one.")
        return
    rig = await asyncio.to_thread(db.pair_code_redeem, digits, chat_id,
                                 _display_name(update))
    if rig is None:
        await say(update, DB_BUSY)
        return
    if not rig:
        _record_attempt(chat_id)
        minutes = int(config.PAIR_CODE_TTL_S // 60)
        await say(update,
                  f"That code didn't work — codes last about {minutes} "
                  f"minutes and can only be used once. Press <b>Generate "
                  f"code</b> again and send me the new one.")
        return
    _ATTEMPTS.pop(chat_id, None)
    await say(update,
              f"✅ You're connected to <b>"
              f"{esc(rig.get('name') or rig['rig_id'])}</b>.\n\n"
              f"I'll message you when a sweep ends and if anything goes "
              f"wrong. Ask me for /status, /data, /line or /map any time — "
              f"/help lists the lot.")


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Plain text: six digits is a code, anything else gets a nudge."""
    message = update.effective_message
    text = (message.text or "").strip() if message else ""
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) == 6 and len(text) <= 12:
        await _redeem(update, digits)
        return
    links = await asyncio.to_thread(db.links_for_chat,
                                    update.effective_chat.id)
    if links is None:
        await say(update, DB_BUSY)
    elif links:
        await say(update, "Not sure what you mean — /help lists what I can "
                          "do.")
    else:
        await say(update, NOT_LINKED)


# ------------------------------------------------------------- questions --
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    link, err = await _active_link(update.effective_chat.id)
    if err:
        await say(update, err)
        return
    snapshot, age, err = await _snapshot_for(link["rig_id"])
    if err:
        await say(update, err)
        return
    await say(update, status_text(link, snapshot, age))


async def data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    link, err = await _active_link(update.effective_chat.id)
    if err:
        await say(update, err)
        return
    snapshot, age, err = await _snapshot_for(link["rig_id"])
    if err:
        await say(update, err)
        return
    if not snapshot:
        await say(update, "Nothing measured on that setup yet.")
        return
    await say(update, f"🧾 <b>{_title(link)}</b> · {esc(fmt_age(age))}\n"
                      + table_text(snapshot))


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    link, err = await _active_link(update.effective_chat.id)
    if err:
        await say(update, err)
        return
    snapshot, age, err = await _snapshot_for(link["rig_id"])
    if err:
        await say(update, err)
        return
    await say(update, f"📐 <b>{_title(link)}</b> · {esc(fmt_age(age))}\n"
                      + stats_text(snapshot))


# ---------------------------------------------------------------- plots --
def _pick_read(reads, asked: str, remembered: str) -> Optional[str]:
    """Which parameter somebody meant.

    Accepts the name, part of it in any case, or its position in the
    list, because nobody wants to type ``LOCKIN.X`` exactly on a phone.
    """
    asked = (asked or "").strip()
    if not asked:
        return remembered if remembered in reads else (reads[0] if reads
                                                       else None)
    if asked.isdigit():
        index = int(asked) - 1
        return reads[index] if 0 <= index < len(reads) else None
    lowered = asked.lower()
    for read in reads:
        if read.lower() == lowered:
            return read
    matches = [r for r in reads if lowered in r.lower()]
    return matches[0] if len(matches) == 1 else None


def _others(reads, chosen: str, command: str) -> str:
    rest = [r for r in reads if r != chosen]
    if not rest:
        return ""
    listed = ", ".join(rest[:6]) + ("…" if len(rest) > 6 else "")
    return f"\nAlso here: {esc(listed)} — try <code>{command} {esc(rest[0])}</code>"


async def _picture(update, context, kind: str) -> None:
    chat_id = update.effective_chat.id
    link, err = await _active_link(chat_id)
    if err:
        await say(update, err)
        return
    rig_id = link["rig_id"]
    snapshot, age, err = await _snapshot_for(rig_id)
    if err:
        await say(update, err)
        return
    reads = render.readable_reads(snapshot)
    if not reads:
        await say(update, "Nothing measured on that setup yet — start a "
                          "sweep, or give it a moment for the first points.")
        return

    prefs = prefs_of(link)
    asked = " ".join(context.args or "") if context.args else ""
    command = "/line" if kind == "line" else "/map"
    read = _pick_read(reads, asked, prefs.get("read") or "")
    if read is None:
        listed = ", ".join(reads[:10]) + ("…" if len(reads) > 10 else "")
        await say(update, f"I don't have <b>{esc(asked)}</b>. This setup "
                          f"measures: {esc(listed)}")
        return

    if age is None or age > config.SNAPSHOT_FRESH_S:
        await say(update, f"⏳ Fetching the latest {esc(read)}…")
        await _request_fresh(rig_id, chat_id)
        snapshot, age, err = await _snapshot_for(rig_id)
        if err:
            await say(update, err)
            return

    prefs["read"] = read
    await asyncio.to_thread(db.link_save_prefs, rig_id, chat_id, prefs)

    subtitle = (snapshot or {}).get("file", "")
    if kind == "map":
        maps = (snapshot or {}).get("maps") or {}
        photo = await asyncio.to_thread(
            render.safe_render, render.render_map, maps.get(read) or {},
            read, f"{link.get('rig_name') or rig_id} — {read}", subtitle,
            prefs.get("cmap", "viridis"))
        missing = ("No map for that one yet — a map needs a 2-D or 3-D "
                   "sweep with at least one finished line.")
    else:
        photo = await asyncio.to_thread(
            render.safe_render, render.render_trace,
            (snapshot or {}).get("trace") or {}, [read],
            f"{link.get('rig_name') or rig_id} — {read}", subtitle)
        missing = "Not enough points on this line yet."

    if not photo:
        await say(update, missing + _others(reads, read, command))
        return

    caption = (f"<b>{_title(link)}</b> · {esc(read)} · "
               f"{esc(fmt_age(age))}" + _others(reads, read, command))
    try:
        await context.bot.send_photo(chat_id=chat_id, photo=photo,
                                     caption=caption,
                                     parse_mode=ParseMode.HTML)
    except Exception as exc:                           # noqa: BLE001
        logger.warning("send_photo failed: %s", exc)
        await say(update, "Couldn't send that picture — try again.")


async def line(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _picture(update, context, "line")


async def map_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _picture(update, context, "map")


# -------------------------------------------------------------- setups ---
async def setups(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    links = await asyncio.to_thread(db.links_for_chat, chat_id)
    if links is None:
        await say(update, DB_BUSY)
        return
    if not links:
        await say(update, NOT_LINKED)
        return

    asked = " ".join(context.args or "").strip() if context.args else ""
    if asked:
        chosen = None
        if asked.isdigit() and 1 <= int(asked) <= len(links):
            chosen = links[int(asked) - 1]
        else:
            named = [l for l in links
                     if asked.lower() in (l.get("rig_name") or "").lower()]
            chosen = named[0] if len(named) == 1 else None
        if chosen is None:
            await say(update, "I don't have that one. Send /setups to see "
                              "the list.")
            return
        await asyncio.to_thread(db.chat_set_active_rig, chat_id,
                                chosen["rig_id"])
        await say(update, f"Now answering about <b>"
                          f"{esc(chosen.get('rig_name') or chosen['rig_id'])}"
                          f"</b>.")
        return

    active, _err = await _active_link(chat_id)
    active_id = active["rig_id"] if active else None
    lines = ["<b>Your setups</b>", ""]
    for i, link in enumerate(links, start=1):
        mark = "  ← answering about this one" \
            if link["rig_id"] == active_id and len(links) > 1 else ""
        lines.append(f"{i} · {esc(rig_line(link))}{mark}")
    if len(links) > 1:
        lines.append("")
        lines.append("Switch with <code>/setups 2</code>")
    await say(update, "\n".join(lines))


async def unlink(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    link, err = await _active_link(chat_id)
    if err:
        await say(update, err)
        return
    name = link.get("rig_name") or link["rig_id"]
    if not _confirmed(chat_id, "unlink"):
        await say(update, f"This stops every message from <b>{esc(name)}</b>. "
                          f"Send /unlink again to confirm.")
        return
    ok = await asyncio.to_thread(db.link_delete, link["rig_id"], chat_id)
    await say(update,
              f"Done — nothing more from {esc(name)}. You can come back any "
              f"time with a new code." if ok else DB_BUSY)


# -------------------------------------------------------------- alerts ---
async def alerts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    link, err = await _active_link(chat_id)
    if err:
        await say(update, err)
        return
    prefs = prefs_of(link)
    args = [a for a in (context.args or []) if a.strip()]

    if args:
        key = pref_key(args[0])
        if not key:
            await say(update, f"I don't know \"{esc(args[0])}\". Send "
                              f"/alerts on its own to see the list.")
            return
        rest = args[1].lower() if len(args) > 1 else ""
        if key == "progress":
            minutes = int(rest) if rest.isdigit() else 0
            prefs["progress"] = minutes > 0
            prefs["progress_min"] = max(0, min(minutes, 720))
        elif rest in ("on", "yes", "1"):
            prefs[key] = True
        elif rest in ("off", "no", "0"):
            prefs[key] = False
        else:
            prefs[key] = not bool(prefs.get(key))
        if not await asyncio.to_thread(db.link_save_prefs, link["rig_id"],
                                       chat_id, prefs):
            await say(update, DB_BUSY)
            return

    lines = [f"🔔 <b>{_title(link)}</b> — what I message you about", ""]
    for key, label in KIND_LABEL.items():
        if key == "progress":
            minutes = int(prefs.get("progress_min") or 0)
            mark = "on " if minutes else "off"
            extra = f" (every {minutes} min)" if minutes else ""
            lines.append(f"<code>{mark}</code>  {esc(label)}{esc(extra)}")
        else:
            mark = "on " if prefs.get(key) else "off"
            lines.append(f"<code>{mark}</code>  {esc(label)}")
    lines.append("")
    lines.append("Change one with <code>/alerts errors off</code>, or "
                 "<code>/alerts progress 30</code> for an update every "
                 "half hour.")
    await say(update, "\n".join(lines))


# ------------------------------------------------------------- control ---
def _confirmed(chat_id: int, kind: str) -> bool:
    """True the second time somebody asks, within a minute of the first."""
    now = time.monotonic()
    key = (chat_id, kind)
    asked = _PENDING.get(key)
    if asked is not None and now - asked < CONFIRM_WINDOW_S:
        _PENDING.pop(key, None)
        return True
    _PENDING[key] = now
    return False


async def _control(update: Update, context: ContextTypes.DEFAULT_TYPE,
                   kind: str) -> None:
    chat_id = update.effective_chat.id
    link, err = await _active_link(chat_id)
    if err:
        await say(update, err)
        return
    name = link.get("rig_name") or link["rig_id"]
    if not link.get("allow_control"):
        await say(update,
                  f"🔒 <b>{esc(name)}</b> doesn't accept commands from here.\n"
                  f"Somebody at the computer can allow it: <b>Settings → "
                  f"Telegram notifications → Allow pause / stop</b>. It's off "
                  f"by default, on purpose — it moves real instruments.")
        return

    sweep = state_of(link).get("state", "idle")
    if sweep not in ("running", "paused"):
        await say(update, f"No sweep running on {esc(name)}.")
        return

    # pausing is reversible; stopping is not, so stopping asks twice
    if kind in ("stop", "to_zero") and not _confirmed(chat_id, kind):
        await say(update, f"This will {esc(CONTROL_WORDS[kind])} on "
                          f"<b>{esc(name)}</b>. Send the same command again "
                          f"to confirm.")
        return

    command_id = await asyncio.to_thread(db.command_add, link["rig_id"], kind,
                                         {}, chat_id)
    if command_id is None:
        await say(update, DB_BUSY)
        return
    await say(update, f"📨 Sent. {esc(name)} picks it up within a few "
                      f"seconds and I'll confirm here.")


async def pause(update, context):
    await _control(update, context, "pause")


async def resume(update, context):
    await _control(update, context, "resume")


async def stop(update, context):
    await _control(update, context, "stop")


async def to_zero(update, context):
    await _control(update, context, "to_zero")


async def on_error(update: object,
                   context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("unhandled error in a handler", exc_info=context.error)
