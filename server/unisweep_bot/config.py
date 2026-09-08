"""Service configuration — environment only, never source.

Every secret arrives through the environment (Railway variables). Nothing
here has a credential default: a missing token or database URL is a fatal
start-up error, not a silent fall-back onto a hard-coded value.
"""

from __future__ import annotations

import logging
import os
import sys
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        logger.critical("%s environment variable is missing!", name)
        sys.exit(1)
    return value


def _num(name: str, default, cast=float):
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return cast(raw)
    except (TypeError, ValueError):
        logger.warning("%s=%r is not a number — using %r", name, raw, default)
        return default


# ---- required ----------------------------------------------------------
TELEGRAM_BOT_TOKEN = _require("TELEGRAM_BOT_TOKEN")
DATABASE_URL = _require("DATABASE_URL")

# ---- where the HTTP ingest listens -------------------------------------
#: Railway injects PORT. Binding 0.0.0.0 is required for its router.
PORT = int(_num("PORT", 8080, int))
HOST = os.getenv("HOST", "0.0.0.0").strip() or "0.0.0.0"

#: shown to users so they can paste it into Unisweep's Settings page
PUBLIC_URL = os.getenv("PUBLIC_URL", "").strip().rstrip("/")

# ---- timing ------------------------------------------------------------
#: the lab is in Singapore; Railway containers run UTC. Every timestamp a
#: human reads is rendered in this zone — never in server-local time.
TZ = ZoneInfo(os.getenv("TZ_NAME", "Asia/Singapore"))

#: how often the single outbox job drains pending notifications
DISPATCH_INTERVAL_S = _num("DISPATCH_INTERVAL_S", 3.0)
#: how often rigs are checked for having gone silent
WATCHDOG_INTERVAL_S = _num("WATCHDOG_INTERVAL_S", 60.0)
#: a *running* rig that has not pushed for this long is reported as silent
SILENCE_GRACE_S = _num("SILENCE_GRACE_S", 240.0)
#: housekeeping (old outbox rows, stale commands)
MAINTENANCE_INTERVAL_S = _num("MAINTENANCE_INTERVAL_S", 3600.0)
#: delivered notifications are kept this long for debugging, then deleted
OUTBOX_RETENTION_H = _num("OUTBOX_RETENTION_H", 72.0)
#: a command nobody collected is dropped after this long
COMMAND_TTL_S = _num("COMMAND_TTL_S", 600.0)

# ---- limits ------------------------------------------------------------
TELEGRAM_MSG_LIMIT = 3800          # safely under Telegram's 4096 cap
MAX_SEND_ATTEMPTS = 5              # per outbox row, then it is abandoned
MAX_EVENTS_PER_PUSH = 50           # a rig cannot flood the outbox
MAX_BODY_BYTES = int(_num("MAX_BODY_BYTES", 8 * 1024 * 1024, int))
SNAPSHOT_FRESH_S = _num("SNAPSHOT_FRESH_S", 30.0)
SNAPSHOT_WAIT_S = _num("SNAPSHOT_WAIT_S", 22.0)

# ---- pairing -----------------------------------------------------------
#: how long a pairing code stays valid.  Short enough that a code left on
#: a lab screen is not a standing invitation; long enough to walk back to
#: your desk and type it.
PAIR_CODE_TTL_S = _num("PAIR_CODE_TTL_S", 600.0)
#: wrong codes one chat may try before it is ignored for a while.  900 000
#: possibilities and five guesses per window is not a searchable space.
PAIR_MAX_ATTEMPTS = int(_num("PAIR_MAX_ATTEMPTS", 5, int))
PAIR_ATTEMPT_WINDOW_S = _num("PAIR_ATTEMPT_WINDOW_S", 600.0)

DB_CONNECT_TIMEOUT_S = int(_num("DB_CONNECT_TIMEOUT_S", 10, int))
DB_POOL_MAX = int(_num("DB_POOL_MAX", 8, int))

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
