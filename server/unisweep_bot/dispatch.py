"""The background jobs.

All three are scheduled **once, at start-up**, from ``post_init`` — never
from a command handler.  That is the difference between monitoring that
survives a redeploy and monitoring that quietly stops the first time the
container restarts, and it is also why no duplicate job can ever stack up:
each one has a name and is registered exactly once.

Each job decides for itself whether there is anything to do.  None of them
has an on/off flag, so there is no state in which the service is running
but not watching.
"""

from __future__ import annotations

import asyncio
import json
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.error import (BadRequest, Forbidden, NetworkError, RetryAfter,
                            TimedOut)

from . import config, db
from .formatting import esc, fmt_age, age_seconds, split_message

logger = logging.getLogger(__name__)

CAPTION_LIMIT = 1000          # Telegram allows 1024; leave room for entities


def _markup(spec):
    if not spec:
        return None
    if isinstance(spec, str):
        try:
            spec = json.loads(spec)
        except ValueError:
            return None
    try:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(b["text"], callback_data=b["data"])
             for b in row] for row in spec])
    except Exception:                                  # noqa: BLE001
        return None


async def _drop_chat(chat_id: int) -> None:
    """A user who blocked the bot stops being work forever."""
    logger.info("chat %s blocked the bot → removing its links", chat_id)
    await asyncio.to_thread(db.links_delete_for_chat, chat_id)
    await asyncio.to_thread(db.outbox_drop_for_chat, chat_id)


async def _send_one(bot, row: dict) -> bool:
    """Deliver one outbox row.  True when it is done with (sent, or the
    chat is gone); False to leave it for the next tick."""
    chat_id = int(row["chat_id"])
    body = row["body"] or ""
    markup = _markup(row.get("markup"))
    chunks = split_message(body)
    try:
        if row.get("photo"):
            caption = chunks[0]
            rest = chunks[1:]
            if len(caption) > CAPTION_LIMIT:
                rest = split_message(caption[CAPTION_LIMIT:]) + rest
                caption = caption[:CAPTION_LIMIT]
            await bot.send_photo(chat_id=chat_id, photo=bytes(row["photo"]),
                                 caption=caption,
                                 parse_mode=ParseMode.HTML,
                                 reply_markup=markup if not rest else None)
            for i, chunk in enumerate(rest):
                await bot.send_message(
                    chat_id=chat_id, text=chunk, parse_mode=ParseMode.HTML,
                    reply_markup=markup if i == len(rest) - 1 else None)
        else:
            for i, chunk in enumerate(chunks):
                await bot.send_message(
                    chat_id=chat_id, text=chunk, parse_mode=ParseMode.HTML,
                    reply_markup=markup if i == len(chunks) - 1 else None)
        return True
    except Forbidden:
        await _drop_chat(chat_id)
        return True
    except RetryAfter as exc:
        await asyncio.sleep(min(float(exc.retry_after) + 1.0, 60.0))
        return False
    except BadRequest as exc:
        # unparsable HTML or a deleted chat: do not retry forever
        logger.warning("outbox %s rejected by Telegram: %s", row["id"], exc)
        return True
    except (NetworkError, TimedOut) as exc:
        logger.warning("network error sending outbox %s: %s", row["id"], exc)
        return False
    except Exception as exc:                           # noqa: BLE001
        logger.error("outbox %s failed: %s: %s", row["id"],
                     type(exc).__name__, exc)
        return False


async def dispatch_outbox(context) -> None:
    """Drain queued notifications.  One place handles rate limits, blocked
    users and message splitting, for every notification in the service."""
    try:
        rows = await asyncio.to_thread(db.outbox_take, 25)
        if rows is None:
            return                                     # database blip: retry
        if not rows:
            return
        done = []
        for row in rows:
            if await _send_one(context.bot, row):
                done.append(row["id"])
        if done:
            await asyncio.to_thread(db.outbox_mark_sent, done)
    except Exception:                                  # noqa: BLE001
        logger.error("dispatch_outbox failed", exc_info=True)


async def watch_rigs(context) -> None:
    """Report rigs that were mid-sweep and stopped reporting.

    An overnight sweep whose computer froze, lost its network or was shut
    down looks exactly like silence — and silence is the one failure the
    rig itself can never tell you about.
    """
    try:
        silent = await asyncio.to_thread(db.rigs_gone_silent,
                                         config.SILENCE_GRACE_S)
        if not silent:
            return
        for rig in silent:
            links = await asyncio.to_thread(db.links_for_rig, rig["rig_id"])
            if not links:
                continue
            age = fmt_age(age_seconds(rig.get("last_seen")))
            body = (f"<b>{esc(rig.get('name') or rig['rig_id'])}</b>\n"
                    f"📡 no contact — the rig was sweeping and last reported "
                    f"{esc(age)}.\nThe measurement computer may have lost "
                    f"its network, gone to sleep, or crashed.")
            for link in links:
                await asyncio.to_thread(
                    db.outbox_add, int(link["chat_id"]), "silent", body,
                    f"{rig['rig_id']}:silent:"
                    f"{rig['last_seen'].isoformat() if rig.get('last_seen') else '0'}"
                    f":{link['chat_id']}", rig["rig_id"])
    except Exception:                                  # noqa: BLE001
        logger.error("watch_rigs failed", exc_info=True)


async def maintenance(context) -> None:
    try:
        stats = await asyncio.to_thread(db.maintenance)
        if stats:
            logger.info("maintenance: %s", stats)
    except Exception:                                  # noqa: BLE001
        logger.error("maintenance failed", exc_info=True)


def schedule(app) -> None:
    """Register the jobs exactly once, by name."""
    if app.job_queue is None:
        raise RuntimeError(
            'JobQueue is unavailable. Install with: '
            'pip install "python-telegram-bot[job-queue]"')
    app.job_queue.run_repeating(dispatch_outbox,
                                interval=config.DISPATCH_INTERVAL_S,
                                first=2, name="dispatch_outbox")
    app.job_queue.run_repeating(watch_rigs,
                                interval=config.WATCHDOG_INTERVAL_S,
                                first=20, name="watch_rigs")
    app.job_queue.run_repeating(maintenance,
                                interval=config.MAINTENANCE_INTERVAL_S,
                                first=120, name="maintenance")
    logger.info("jobs scheduled: outbox every %.0fs, watchdog every %.0fs",
                config.DISPATCH_INTERVAL_S, config.WATCHDOG_INTERVAL_S)
