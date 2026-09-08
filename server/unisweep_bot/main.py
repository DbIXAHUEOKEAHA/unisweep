"""Service entry point.

One process does two things at once and neither may take the other down:

* it polls Telegram for updates (``run_polling`` owns the event loop and,
  crucially, owns *shutdown* as well — the failure mode of hand-rolled
  ``initialize()/start()`` loops is a zombie poller and a 409 Conflict
  from two concurrent ``getUpdates``);
* it serves the rig-facing HTTP API on Railway's ``$PORT``, started inside
  ``post_init`` so it lives on the very same event loop and stops with it.

The outer ``while True`` is the restart loop: a crash logs, waits and
rebuilds the application on a fresh event loop rather than leaving the
container alive but deaf.
"""

from __future__ import annotations

import asyncio
import logging
import sys
import time

from aiohttp import web
from telegram import BotCommand
from telegram.ext import (ApplicationBuilder, CallbackQueryHandler,
                          CommandHandler, MessageHandler, filters)
from telegram.request import HTTPXRequest

from . import config, db, dispatch, handlers, ingest

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    handlers=[logging.StreamHandler(sys.stdout)],
)
# these two are chatty enough to bury everything else at INFO
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("aiohttp.access").setLevel(logging.WARNING)
logger = logging.getLogger("unisweep-bot")

COMMANDS = [
    BotCommand("link", "Connect a setup with its 6-digit code"),
    BotCommand("menu", "Everything, with buttons"),
    BotCommand("status", "State, progress and latest readings"),
    BotCommand("table", "The tail of the data table"),
    BotCommand("plot", "A parameter against the fast axis"),
    BotCommand("map", "A parameter over the 2-D grid"),
    BotCommand("stats", "min / max / mean per parameter"),
    BotCommand("rigs", "Switch between linked rigs"),
    BotCommand("notify", "Choose what I tell you about"),
    BotCommand("control", "Pause or stop a sweep"),
    BotCommand("unlink", "Stop updates from a rig"),
    BotCommand("id", "Your Telegram id"),
    BotCommand("help", "All commands"),
]


async def post_init(app) -> None:
    """Runs once, after the application initialises and before polling.

    Everything that must exist for the service to be useful is set up
    here — schema, HTTP listener, jobs — so a redeploy restores all of it
    without anybody having to send a command.
    """
    await asyncio.to_thread(db.initialize_database)

    username = ""
    try:
        me = await app.bot.get_me()
        username = me.username or ""
        logger.info("connected to Telegram as @%s", username)
    except Exception as exc:                           # noqa: BLE001
        logger.warning("get_me failed (continuing): %s", exc)
    app.bot_data["bot_username"] = username

    try:
        await app.bot.set_my_commands(COMMANDS)
    except Exception as exc:                           # noqa: BLE001
        logger.warning("set_my_commands failed: %s", exc)

    http = ingest.build_app(username)
    runner = web.AppRunner(http)
    await runner.setup()
    site = web.TCPSite(runner, config.HOST, config.PORT)
    await site.start()
    app.bot_data["http_runner"] = runner
    logger.info("ingest API listening on %s:%s%s", config.HOST, config.PORT,
                f"  (public {config.PUBLIC_URL})" if config.PUBLIC_URL else "")

    dispatch.schedule(app)


async def post_shutdown(app) -> None:
    runner = app.bot_data.get("http_runner")
    if runner is not None:
        try:
            await runner.cleanup()
        except Exception:                              # noqa: BLE001
            pass


def build_application():
    request = HTTPXRequest(
        connection_pool_size=20,
        read_timeout=45.0, write_timeout=60.0,
        connect_timeout=45.0, pool_timeout=45.0,
        http_version="1.1",
    )
    app = (
        ApplicationBuilder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .request(request)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )
    app.add_handler(CommandHandler("start", handlers.start))
    app.add_handler(CommandHandler("help", handlers.help_cmd))
    app.add_handler(CommandHandler("id", handlers.whoami))
    app.add_handler(CommandHandler("menu", handlers.menu))
    app.add_handler(CommandHandler("rigs", handlers.rigs))
    app.add_handler(CommandHandler("status", handlers.status))
    app.add_handler(CommandHandler("table", handlers.table))
    app.add_handler(CommandHandler("stats", handlers.stats))
    app.add_handler(CommandHandler("plot", handlers.plot))
    app.add_handler(CommandHandler("map", handlers.map_cmd))
    app.add_handler(CommandHandler("notify", handlers.notify))
    app.add_handler(CommandHandler("control", handlers.control))
    app.add_handler(CommandHandler("unlink", handlers.unlink))
    app.add_handler(CommandHandler("link", handlers.link_code))
    app.add_handler(CallbackQueryHandler(handlers.on_button))
    # last: anything that is not a command. Six digits pair a setup, which
    # is what people actually send after reading a code off the screen.
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,
                                   handlers.on_text))
    app.add_error_handler(handlers.on_error)
    return app


def main() -> None:
    while True:
        try:
            asyncio.set_event_loop(asyncio.new_event_loop())
            application = build_application()
            logger.info("starting…")
            application.run_polling(
                drop_pending_updates=True,
                allowed_updates=["message", "callback_query"],
                bootstrap_retries=-1,
            )
            logger.info("stopped cleanly — exiting")
            break
        except KeyboardInterrupt:
            logger.info("shutdown requested")
            break
        except Exception as exc:                       # noqa: BLE001
            logger.critical("crashed: %s: %s", type(exc).__name__, exc,
                            exc_info=True)
            logger.info("restarting in 15 s…")
            time.sleep(15)


if __name__ == "__main__":
    main()
