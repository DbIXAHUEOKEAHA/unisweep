"""Everything a person can do in the chat.

The Unisweep settings page does exactly one thing: it shows a six-digit
code.  Sending that code here is the entire sign-up — no chat id to look
up, nothing to type on the lab computer — and from that moment this file
is the whole interface: which setup to look at, what to be told about,
and the pictures.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from . import config, db, render
from .formatting import (DEFAULT_PREFS, KIND_LABEL, age_seconds, esc,
                         fmt_age, local, prefs_of, rig_line, split_message,
                         stats_text, status_text, table_text,
                         unpack_snapshot)

logger = logging.getLogger(__name__)

DB_BUSY = ("⚠️ The database is not answering right now. Nothing is lost — "
           "try again in a minute.")
NO_RIGS = ("You are not linked to any measurement setup yet.\n\n"
           "On the computer running Unisweep open <b>Settings → "
           "Notifications</b> and press <b>Generate code</b>. Send me the "
           "six digits it shows and you are linked.")

CONTROL_LABEL = {
    "pause": "⏸ Pause", "resume": "▶️ Resume",
    "stop": "⛔ Stop sweep", "to_zero": "↩️ Stop and ramp to zero",
}


# ------------------------------------------------------------- plumbing --
async def _reply(update: Update, text: str, markup=None) -> None:
    message = update.effective_message
    chunks = split_message(text)
    for i, chunk in enumerate(chunks):
        target = markup if i == len(chunks) - 1 else None
        try:
            if message is not None:
                await message.reply_text(chunk, parse_mode=ParseMode.HTML,
                                         reply_markup=target)
            elif update.effective_chat is not None:
                await update.effective_chat.send_message(
                    chunk, parse_mode=ParseMode.HTML, reply_markup=target)
        except BadRequest as exc:
            logger.warning("reply failed: %s", exc)


async def safe_edit(query, text: str, markup=None) -> None:
    """Editing fails routinely — a double tap produces 'message is not
    modified', and a keyboard older than 48 h can no longer be edited.
    Neither is worth an error to the user."""
    try:
        await query.edit_message_text(text, parse_mode=ParseMode.HTML,
                                      reply_markup=markup)
    except BadRequest as exc:
        if "not modified" not in str(exc).lower():
            logger.warning("edit failed: %s", exc)
    except Exception as exc:                           # noqa: BLE001
        logger.warning("edit failed: %s", exc)


async def _active_link(chat_id: int) -> Tuple[Optional[dict], Optional[str]]:
    """The rig this chat is currently looking at.

    Returns ``(link, error_text)``.  A database failure produces an error
    string, never "you have no rigs" — the two are different facts and the
    user must not be told the wrong one.
    """
    links = await asyncio.to_thread(db.links_for_chat, chat_id)
    if links is None:
        return None, DB_BUSY
    if not links:
        return None, NO_RIGS
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


async def _request_fresh(rig_id: str, chat_id: int,
                         wait_s: float = None) -> None:
    """Ask the rig to push now, and give it a moment to answer.

    The rig polls for commands on its own heartbeat, so this shortens the
    wait rather than guaranteeing anything; whatever arrives (or does not)
    the caller still renders and labels the data's age.
    """
    before = await asyncio.to_thread(db.snapshot_age_marker, rig_id)
    await asyncio.to_thread(db.command_add, rig_id, "snapshot", {}, chat_id)
    deadline = wait_s if wait_s is not None else config.SNAPSHOT_WAIT_S
    waited = 0.0
    while waited < deadline:
        await asyncio.sleep(2.0)
        waited += 2.0
        marker = await asyncio.to_thread(db.snapshot_age_marker, rig_id)
        if marker is not None and marker != before:
            return


# -------------------------------------------------------------- screens --
def main_menu(link: Optional[dict], many: bool) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("📊 Status", callback_data="menu:status"),
         InlineKeyboardButton("🧾 Data table", callback_data="menu:table")],
        [InlineKeyboardButton("📈 Plot vs fast axis",
                              callback_data="menu:plot"),
         InlineKeyboardButton("🗺 Map", callback_data="menu:map")],
        [InlineKeyboardButton("📐 Statistics", callback_data="menu:stats"),
         InlineKeyboardButton("🔔 Notifications",
                              callback_data="menu:notify")],
    ]
    if link and link.get("allow_control"):
        rows.append([InlineKeyboardButton("🎛 Control",
                                          callback_data="menu:control")])
    if many:
        rows.append([InlineKeyboardButton("🔀 Switch rig",
                                          callback_data="menu:rigs")])
    rows.append([InlineKeyboardButton("🔌 Unlink this rig",
                                      callback_data="menu:unlink")])
    return InlineKeyboardMarkup(rows)


def reads_keyboard(reads, prefix: str, back: str = "menu:home"):
    rows, row = [], []
    for i, name in enumerate(reads[:24]):
        row.append(InlineKeyboardButton(name[:24],
                                        callback_data=f"{prefix}:{i}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("↩︎ Menu", callback_data=back)])
    return InlineKeyboardMarkup(rows)


def notify_keyboard(prefs: dict) -> InlineKeyboardMarkup:
    rows = []
    for key in ("finished", "error", "guard", "started", "paused", "file",
                "silent", "photo"):
        mark = "🔔" if prefs.get(key) else "🔕"
        rows.append([InlineKeyboardButton(f"{mark} {KIND_LABEL[key]}",
                                          callback_data=f"pref:{key}")])
    minutes = int(prefs.get("progress_min") or 0)
    label = "off" if not minutes else f"every {minutes} min"
    rows.append([InlineKeyboardButton(f"⏱ progress pings: {label}",
                                      callback_data="pref:progress_min")])
    rows.append([InlineKeyboardButton(f"🎨 colormap: {prefs.get('cmap')}",
                                      callback_data="menu:cmap")])
    rows.append([InlineKeyboardButton("↩︎ Menu", callback_data="menu:home")])
    return InlineKeyboardMarkup(rows)


def control_keyboard(state: str) -> InlineKeyboardMarkup:
    rows = []
    if state == "paused":
        rows.append([InlineKeyboardButton(CONTROL_LABEL["resume"],
                                          callback_data="ctl:resume")])
    else:
        rows.append([InlineKeyboardButton(CONTROL_LABEL["pause"],
                                          callback_data="ctl:pause")])
    rows.append([InlineKeyboardButton(CONTROL_LABEL["stop"],
                                      callback_data="ctl:stop")])
    rows.append([InlineKeyboardButton(CONTROL_LABEL["to_zero"],
                                      callback_data="ctl:to_zero")])
    rows.append([InlineKeyboardButton("↩︎ Menu", callback_data="menu:home")])
    return InlineKeyboardMarkup(rows)


# ------------------------------------------------------------- commands --
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    await asyncio.to_thread(db.chat_get, chat_id)
    links = await asyncio.to_thread(db.links_for_chat, chat_id)
    if links:
        await menu(update, context)
        return
    await _reply(update,
                 "👋 <b>Unisweep measurement bot</b>\n\n"
                 "I watch your sweeps and tell you when they finish, when "
                 "something goes wrong, and when the measurement computer "
                 "stops reporting. I can also show you the data table and "
                 "draw plots on request.\n\n"
                 "<b>To connect a setup</b>\n"
                 "1. On the computer running Unisweep: <b>Settings → "
                 "Notifications → Generate code</b>.\n"
                 "2. Send me the six digits.\n\n"
                 "That is all — everything else is set up here, with /menu.")


async def whoami(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Your numeric id — the one the Settings page lists as linked."""
    await _reply(update, f"Your Telegram id is <code>"
                         f"{update.effective_chat.id}</code>\n"
                         f"That is the number shown in Unisweep's list of "
                         f"linked users.")


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply(update,
                 "<b>Commands</b>\n"
                 "/link 123456 — connect a setup with the code it showed\n"
                 "/menu — everything, with buttons\n"
                 "/status — state, progress, latest readings\n"
                 "/table — the tail of the data table\n"
                 "/plot — a read parameter against the fast axis\n"
                 "/map — a read parameter over the 2-D grid\n"
                 "/stats — min / max / mean per parameter\n"
                 "/rigs — switch between linked rigs\n"
                 "/notify — choose what I tell you about\n"
                 "/control — pause or stop a sweep (if the rig allows it)\n"
                 "/unlink — stop receiving updates from a setup\n"
                 "/id — your Telegram id")


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    links = await asyncio.to_thread(db.links_for_chat, chat_id)
    if links is None:
        await _reply(update, DB_BUSY)
        return
    if not links:
        await _reply(update, NO_RIGS)
        return
    link, err = await _active_link(chat_id)
    if err:
        await _reply(update, err)
        return
    text = f"{rig_line(link)}\n\nWhat would you like?"
    markup = main_menu(link, len(links) > 1)
    if update.callback_query:
        await safe_edit(update.callback_query, text, markup)
    else:
        await _reply(update, text, markup)


async def rigs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    links = await asyncio.to_thread(db.links_for_chat, chat_id)
    if links is None:
        await _reply(update, DB_BUSY)
        return
    if not links:
        await _reply(update, NO_RIGS)
        return
    active = links
    rows = [[InlineKeyboardButton(rig_line(l)[:60],
                                  callback_data=f"rig:{l['rig_id']}")]
            for l in active]
    rows.append([InlineKeyboardButton("↩︎ Menu", callback_data="menu:home")])
    text = "<b>Your setups</b>\n" + "\n".join(
        f"· {esc(l.get('rig_name') or l['rig_id'])} — last seen "
        f"{esc(fmt_age(age_seconds(l.get('last_seen'))))}" for l in active)
    markup = InlineKeyboardMarkup(rows)
    if update.callback_query:
        await safe_edit(update.callback_query, text, markup)
    else:
        await _reply(update, text, markup)


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    link, err = await _active_link(chat_id)
    if err:
        await _reply(update, err)
        return
    snapshot, age, err = await _snapshot_for(link["rig_id"])
    if err:
        await _reply(update, err)
        return
    text = status_text(link, snapshot, age)
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Refresh", callback_data="menu:status"),
         InlineKeyboardButton("📈 Plot", callback_data="menu:plot")],
        [InlineKeyboardButton("↩︎ Menu", callback_data="menu:home")]])
    if update.callback_query:
        await safe_edit(update.callback_query, text, markup)
    else:
        await _reply(update, text, markup)


async def table(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    link, err = await _active_link(chat_id)
    if err:
        await _reply(update, err)
        return
    snapshot, age, err = await _snapshot_for(link["rig_id"])
    if err:
        await _reply(update, err)
        return
    if not snapshot:
        await _reply(update, "That rig has not sent any data yet.")
        return
    text = (f"<b>{esc(link.get('rig_name') or link['rig_id'])}</b> — "
            f"data {esc(fmt_age(age))}\n" + table_text(snapshot))
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Fresh copy", callback_data="fresh:table")],
        [InlineKeyboardButton("↩︎ Menu", callback_data="menu:home")]])
    if update.callback_query:
        await safe_edit(update.callback_query, text, markup)
    else:
        await _reply(update, text, markup)


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    link, err = await _active_link(chat_id)
    if err:
        await _reply(update, err)
        return
    snapshot, age, err = await _snapshot_for(link["rig_id"])
    if err:
        await _reply(update, err)
        return
    text = (f"<b>{esc(link.get('rig_name') or link['rig_id'])}</b> — "
            f"data {esc(fmt_age(age))}\n" + stats_text(snapshot))
    markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton("↩︎ Menu", callback_data="menu:home")]])
    if update.callback_query:
        await safe_edit(update.callback_query, text, markup)
    else:
        await _reply(update, text, markup)


async def _pick_read(update, prefix: str) -> None:
    chat_id = update.effective_chat.id
    link, err = await _active_link(chat_id)
    if err:
        await _reply(update, err)
        return
    snapshot, age, err = await _snapshot_for(link["rig_id"])
    if err:
        await _reply(update, err)
        return
    reads = render.readable_reads(snapshot)
    if not reads:
        msg = ("That rig has not sent any measured data yet — start a sweep, "
               "or wait for the first points.")
        if update.callback_query:
            await safe_edit(update.callback_query, msg, main_menu(link, False))
        else:
            await _reply(update, msg)
        return
    what = "map" if prefix == "map" else "plot against the fast axis"
    text = (f"<b>{esc(link.get('rig_name') or link['rig_id'])}</b>\n"
            f"Which parameter should I {esc(what)}?  "
            f"(data {esc(fmt_age(age))})")
    markup = reads_keyboard(reads, prefix)
    if update.callback_query:
        await safe_edit(update.callback_query, text, markup)
    else:
        await _reply(update, text, markup)


async def plot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _pick_read(update, "plot")


async def map_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _pick_read(update, "map")


async def notify(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    link, err = await _active_link(chat_id)
    if err:
        await _reply(update, err)
        return
    prefs = prefs_of(link)
    text = (f"<b>{esc(link.get('rig_name') or link['rig_id'])}</b>\n"
            f"What should I send you? Tap to toggle.")
    markup = notify_keyboard(prefs)
    if update.callback_query:
        await safe_edit(update.callback_query, text, markup)
    else:
        await _reply(update, text, markup)


async def control(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    link, err = await _active_link(chat_id)
    if err:
        await _reply(update, err)
        return
    if not link.get("allow_control"):
        msg = ("🔒 This rig does not accept remote control.\n\n"
               "Tick <b>Allow pause / stop from Telegram</b> in Unisweep's "
               "Settings page if you want it — it is off by default, "
               "deliberately.")
        if update.callback_query:
            await safe_edit(update.callback_query, msg,
                            main_menu(link, False))
        else:
            await _reply(update, msg)
        return
    state = (link.get("state") or {})
    if isinstance(state, dict):
        sweep = state.get("state", "idle")
    else:
        sweep = "idle"
    text = (f"<b>{esc(link.get('rig_name') or link['rig_id'])}</b> — "
            f"{esc(sweep)}\n\nThe rig picks these up on its next heartbeat, "
            f"so allow a few seconds.")
    markup = control_keyboard(sweep)
    if update.callback_query:
        await safe_edit(update.callback_query, text, markup)
    else:
        await _reply(update, text, markup)


async def unlink(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    link, err = await _active_link(chat_id)
    if err:
        await _reply(update, err)
        return
    name = link.get("rig_name") or link["rig_id"]
    text = (f"Stop receiving anything from <b>{esc(name)}</b>?\n\n"
            f"You can link again any time with a new pairing code.")
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔌 Yes, unlink",
                              callback_data=f"unlinkok:{link['rig_id']}")],
        [InlineKeyboardButton("↩︎ Menu", callback_data="menu:home")]])
    if update.callback_query:
        await safe_edit(update.callback_query, text, markup)
    else:
        await _reply(update, text, markup)


# ------------------------------------------------------------ callbacks --
async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    try:
        await query.answer()
    except Exception:                                  # noqa: BLE001
        pass          # very old callbacks cannot be answered; never fatal
    if update.effective_chat is None:                  # message is gone
        return
    chat_id = update.effective_chat.id
    data = (query.data or "")

    if data == "menu:home":
        await menu(update, context)
        return
    if data == "menu:status":
        await status(update, context)
        return
    if data == "menu:table":
        await table(update, context)
        return
    if data == "menu:stats":
        await stats(update, context)
        return
    if data == "menu:plot":
        await _pick_read(update, "plot")
        return
    if data == "menu:map":
        await _pick_read(update, "map")
        return
    if data == "menu:notify":
        await notify(update, context)
        return
    if data == "menu:control":
        await control(update, context)
        return
    if data == "menu:rigs":
        await rigs(update, context)
        return
    if data == "menu:unlink":
        await unlink(update, context)
        return
    if data == "menu:cmap":
        rows, row = [], []
        for name in render.CMAPS:
            row.append(InlineKeyboardButton(name, callback_data=f"cmap:{name}"))
            if len(row) == 3:
                rows.append(row)
                row = []
        if row:
            rows.append(row)
        rows.append([InlineKeyboardButton("↩︎ Back",
                                          callback_data="menu:notify")])
        await safe_edit(query, "Colormap for maps:",
                        InlineKeyboardMarkup(rows))
        return

    if data.startswith("rig:"):
        rig_id = data.split(":", 1)[1]
        await asyncio.to_thread(db.chat_set_active_rig, chat_id, rig_id)
        await menu(update, context)
        return

    if data.startswith("unlinkok:"):
        rig_id = data.split(":", 1)[1]
        ok = await asyncio.to_thread(db.link_delete, rig_id, chat_id)
        await safe_edit(query,
                        "🔌 Unlinked. You will not hear from that setup "
                        "again unless you send it a new pairing code."
                        if ok else DB_BUSY)
        return

    if data.startswith("pref:"):
        await _toggle_pref(update, data.split(":", 1)[1], chat_id)
        return

    if data.startswith("cmap:"):
        await _set_pref(update, chat_id, {"cmap": data.split(":", 1)[1]})
        await notify(update, context)
        return

    if data.startswith("plot:") or data.startswith("map:"):
        prefix, _, index = data.partition(":")
        await _send_figure(update, context, chat_id, prefix, index)
        return

    if data == "fresh:table":
        link, err = await _active_link(chat_id)
        if err:
            await safe_edit(query, err)
            return
        await safe_edit(query, "⏳ asking the rig for a fresh copy…")
        await _request_fresh(link["rig_id"], chat_id)
        await table(update, context)
        return

    if data.startswith("ctl:"):
        await _confirm_control(update, data.split(":", 1)[1], chat_id)
        return
    if data.startswith("ctlok:"):
        await _do_control(update, data.split(":", 1)[1], chat_id)
        return


# ------------------------------------------------------------- pairing ---
#: chat_id -> [monotonic times of wrong codes].  Five guesses per window
#: against 900 000 possibilities is not a searchable space, and the
#: counter lives in memory on purpose: a restart clearing it costs
#: nothing, and it never becomes a way to lock somebody out for good.
_ATTEMPTS: dict = {}


def _too_many_attempts(chat_id: int) -> bool:
    now = time.monotonic()
    window = config.PAIR_ATTEMPT_WINDOW_S
    tries = [t for t in _ATTEMPTS.get(chat_id, []) if now - t < window]
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


async def link_code(update: Update, context: ContextTypes.DEFAULT_TYPE,
                    code: str = None) -> None:
    """Redeem a six-digit pairing code.

    Reached two ways: ``/link 123456`` and simply sending the digits,
    because that is what people do with a number a screen told them to
    send.
    """
    chat_id = update.effective_chat.id
    if code is None:
        code = " ".join(context.args or "") if context.args else ""
    digits = "".join(ch for ch in str(code) if ch.isdigit())
    if len(digits) != 6:
        await _reply(update,
                     "A pairing code is six digits. Press <b>Generate "
                     "code</b> in Unisweep (Settings → Notifications) and "
                     "send me the number it shows.")
        return
    if _too_many_attempts(chat_id):
        await _reply(update, "Too many wrong codes. Wait a few minutes and "
                             "try again with a freshly generated one.")
        return

    rig = await asyncio.to_thread(db.pair_code_redeem, digits, chat_id,
                                  _display_name(update))
    if rig is None:
        await _reply(update, DB_BUSY)
        return
    if not rig:
        _record_attempt(chat_id)
        await _reply(update,
                     "❌ That code is not valid — it may have expired, been "
                     "used already, or been mistyped.\n\nCodes last about "
                     f"{int(config.PAIR_CODE_TTL_S // 60)} minutes; press "
                     "<b>Generate code</b> again for a fresh one.")
        return

    _ATTEMPTS.pop(chat_id, None)
    link, _err = await _active_link(chat_id)
    await _reply(update,
                 f"✅ Linked to <b>{esc(rig.get('name') or rig['rig_id'])}"
                 f"</b>.\n\nBy default I will tell you when a sweep ends and "
                 f"if something goes wrong. Use the buttons below (or /menu) "
                 f"for the status, the data table and plots.",
                 main_menu(link, False) if link else None)


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Plain text: six digits are a pairing code, anything else gets help."""
    message = update.effective_message
    text = (message.text or "").strip() if message else ""
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) == 6 and len(text) <= 12:
        await link_code(update, context, digits)
        return
    links = await asyncio.to_thread(db.links_for_chat,
                                    update.effective_chat.id)
    if links is None:
        await _reply(update, DB_BUSY)
    elif links:
        await menu(update, context)
    else:
        await _reply(update, NO_RIGS)


async def _set_pref(update: Update, chat_id: int, changes: dict) -> None:
    link, err = await _active_link(chat_id)
    if err:
        await safe_edit(update.callback_query, err)
        return
    prefs = prefs_of(link)
    prefs.update(changes)
    ok = await asyncio.to_thread(db.link_save_prefs, link["rig_id"], chat_id,
                                 prefs)
    if not ok:
        await safe_edit(update.callback_query, DB_BUSY)


async def _toggle_pref(update: Update, key: str, chat_id: int) -> None:
    link, err = await _active_link(chat_id)
    if err:
        await safe_edit(update.callback_query, err)
        return
    prefs = prefs_of(link)
    if key == "progress_min":
        cycle = [0, 15, 30, 60, 120]
        current = int(prefs.get("progress_min") or 0)
        prefs["progress_min"] = cycle[(cycle.index(current) + 1) % len(cycle)] \
            if current in cycle else 0
    elif key in DEFAULT_PREFS:
        prefs[key] = not bool(prefs.get(key))
    else:
        return
    ok = await asyncio.to_thread(db.link_save_prefs, link["rig_id"], chat_id,
                                 prefs)
    if not ok:
        await safe_edit(update.callback_query, DB_BUSY)
        return
    await safe_edit(update.callback_query,
                    f"<b>{esc(link.get('rig_name') or link['rig_id'])}</b>\n"
                    f"What should I send you? Tap to toggle.",
                    notify_keyboard(prefs))


async def _send_figure(update, context, chat_id: int, prefix: str,
                       index: str) -> None:
    query = update.callback_query
    link, err = await _active_link(chat_id)
    if err:
        await safe_edit(query, err)
        return
    rig_id = link["rig_id"]
    snapshot, age, err = await _snapshot_for(rig_id)
    if err:
        await safe_edit(query, err)
        return
    reads = render.readable_reads(snapshot)
    try:
        read = reads[int(index)]
    except (ValueError, IndexError):
        await safe_edit(query, "That parameter is gone — the sweep changed. "
                               "Open the list again.",
                        main_menu(link, False))
        return

    if age is not None and age > config.SNAPSHOT_FRESH_S:
        await safe_edit(query, f"⏳ {esc(read)} — asking the rig for fresh "
                               f"data…")
        await _request_fresh(rig_id, chat_id)
        snapshot, age, err = await _snapshot_for(rig_id)
        if err:
            await safe_edit(query, err)
            return

    prefs = prefs_of(link)
    await _set_pref(update, chat_id, {"read": read})
    name = link.get("rig_name") or rig_id
    subtitle = f"{snapshot.get('file', '')}"
    if prefix == "map":
        maps = (snapshot or {}).get("maps") or {}
        photo = await asyncio.to_thread(
            render.safe_render, render.render_map, maps.get(read) or {}, read,
            f"{name} — {read}", subtitle, prefs.get("cmap", "viridis"))
        missing = ("There is no map for that parameter yet. A map needs a "
                   "2-D or 3-D sweep with at least one finished row.")
    else:
        photo = await asyncio.to_thread(
            render.safe_render, render.render_trace,
            (snapshot or {}).get("trace") or {}, [read],
            f"{name} — {read}", subtitle)
        missing = "There are not enough points on the fast axis yet."

    if not photo:
        await safe_edit(query, missing, reads_keyboard(reads, prefix))
        return

    caption = (f"<b>{esc(name)}</b> · {esc(read)} · data "
               f"{esc(fmt_age(age))}")
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Refresh", callback_data=f"{prefix}:{index}"),
         InlineKeyboardButton("🔀 Other parameter",
                              callback_data=f"menu:{prefix}")],
        [InlineKeyboardButton("↩︎ Menu", callback_data="menu:home")]])
    try:
        await context.bot.send_photo(chat_id=chat_id, photo=photo,
                                     caption=caption,
                                     parse_mode=ParseMode.HTML,
                                     reply_markup=markup)
    except Exception as exc:                           # noqa: BLE001
        logger.warning("send_photo failed: %s", exc)
        await safe_edit(query, "Could not send the picture — try again.")


async def _confirm_control(update: Update, kind: str, chat_id: int) -> None:
    if kind not in CONTROL_LABEL:
        return
    link, err = await _active_link(chat_id)
    if err or not link.get("allow_control"):
        await safe_edit(update.callback_query, err or "🔒 Not allowed.")
        return
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"Confirm: {CONTROL_LABEL[kind]}",
                              callback_data=f"ctlok:{kind}")],
        [InlineKeyboardButton("↩︎ Cancel", callback_data="menu:control")]])
    await safe_edit(update.callback_query,
                    f"This acts on the instruments of "
                    f"<b>{esc(link.get('rig_name') or link['rig_id'])}</b> "
                    f"right now. Confirm?", markup)


async def _do_control(update: Update, kind: str, chat_id: int) -> None:
    if kind not in CONTROL_LABEL:
        return
    link, err = await _active_link(chat_id)
    if err or not link.get("allow_control"):
        await safe_edit(update.callback_query, err or "🔒 Not allowed.")
        return
    cid = await asyncio.to_thread(db.command_add, link["rig_id"], kind, {},
                                  chat_id)
    if cid is None:
        await safe_edit(update.callback_query, DB_BUSY)
        return
    await safe_edit(update.callback_query,
                    f"📨 <b>{esc(CONTROL_LABEL[kind])}</b> sent to "
                    f"{esc(link.get('rig_name') or link['rig_id'])}. "
                    f"I will confirm here once the rig has done it.",
                    InlineKeyboardMarkup(
                        [[InlineKeyboardButton("↩︎ Menu",
                                               callback_data="menu:home")]]))


async def on_error(update: object,
                   context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("unhandled error in a handler", exc_info=context.error)
