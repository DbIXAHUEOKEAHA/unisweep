"""Postgres access layer.

Two conventions run through this whole module and the code above it:

1. **A database error is not an empty result.**  Every reader returns
   ``None`` when the query *failed* and an empty container when the query
   *succeeded and found nothing*.  Conflating the two is what lets a
   thirty-second database blip look like "nobody is subscribed" and
   silently switch monitoring off forever.
2. **One row per write.**  Nothing ever re-writes a whole table from an
   in-memory copy, so two chats (or a chat and a rig) editing different
   rows can never lose each other's update.

Every function here is blocking and is called from the event loop through
``asyncio.to_thread``.  Connections come from a small pool that heals
itself: a connection that raises is closed rather than returned, and an
``OperationalError`` (the shape a restarted database takes) throws the
whole pool away so the next call rebuilds it.
"""

from __future__ import annotations

import contextlib
import hashlib
import hmac
import json
import logging
import secrets
import threading
import time
from typing import Any, Optional

import psycopg2
import psycopg2.extras
import psycopg2.pool

from . import config

logger = logging.getLogger(__name__)

_pool: Optional[psycopg2.pool.ThreadedConnectionPool] = None
_pool_lock = threading.Lock()


# ---------------------------------------------------------------- pool ---
def _get_pool():
    global _pool
    with _pool_lock:
        if _pool is None:
            _pool = psycopg2.pool.ThreadedConnectionPool(
                1, config.DB_POOL_MAX, config.DATABASE_URL,
                connect_timeout=config.DB_CONNECT_TIMEOUT_S,
                # a dead TCP path is noticed in about a minute instead of
                # hanging a worker thread until the kernel gives up
                keepalives=1, keepalives_idle=30, keepalives_interval=10,
                keepalives_count=3,
            )
        return _pool


def _drop_pool() -> None:
    """Throw the pool away — every pooled connection is suspect."""
    global _pool
    with _pool_lock:
        pool, _pool = _pool, None
    if pool is not None:
        with contextlib.suppress(Exception):
            pool.closeall()


@contextlib.contextmanager
def _conn():
    pool = _get_pool()
    conn = pool.getconn()
    broken = False
    try:
        yield conn
    except Exception:
        broken = True
        raise
    finally:
        try:
            pool.putconn(conn, close=broken)
        except Exception:                              # noqa: BLE001
            pass


@contextlib.contextmanager
def _cursor(commit: bool = False):
    try:
        with _conn() as conn:
            try:
                with conn.cursor(
                        cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    yield cur
                if commit:
                    conn.commit()
                else:
                    conn.rollback()
            except Exception:
                with contextlib.suppress(Exception):
                    conn.rollback()
                raise
    except psycopg2.OperationalError:
        _drop_pool()
        raise


SCHEMA = """
CREATE TABLE IF NOT EXISTS rigs (
    rig_id          TEXT PRIMARY KEY,
    name            TEXT        NOT NULL DEFAULT '',
    token_hash      TEXT        NOT NULL,
    allow_control   BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen       TIMESTAMPTZ,
    last_push_state TEXT        NOT NULL DEFAULT 'idle',
    silent_since    TIMESTAMPTZ,
    state           JSONB       NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS links (
    rig_id      TEXT   NOT NULL REFERENCES rigs(rig_id) ON DELETE CASCADE,
    chat_id     BIGINT NOT NULL,
    title       TEXT   NOT NULL DEFAULT '',
    prefs       JSONB  NOT NULL DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_progress_at TIMESTAMPTZ,
    PRIMARY KEY (rig_id, chat_id)
);
CREATE INDEX IF NOT EXISTS links_chat_idx ON links(chat_id);

-- Pairing codes.  The rig shows one; whoever sends it to the bot inside
-- the window is linked.  Possession of the code is the entire proof,
-- which is why it is short-lived, single-use, and replaced rather than
-- added to.
CREATE TABLE IF NOT EXISTS pair_codes (
    code       TEXT PRIMARY KEY,
    rig_id     TEXT        NOT NULL REFERENCES rigs(rig_id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    used_at    TIMESTAMPTZ,
    used_by    BIGINT
);
CREATE INDEX IF NOT EXISTS pair_codes_rig_idx ON pair_codes(rig_id);

CREATE TABLE IF NOT EXISTS snapshots (
    rig_id     TEXT PRIMARY KEY REFERENCES rigs(rig_id) ON DELETE CASCADE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    payload    BYTEA       NOT NULL
);

CREATE TABLE IF NOT EXISTS outbox (
    id         BIGSERIAL PRIMARY KEY,
    rig_id     TEXT,
    chat_id    BIGINT      NOT NULL,
    kind       TEXT        NOT NULL,
    body       TEXT        NOT NULL,
    photo      BYTEA,
    markup     JSONB,
    dedup_key  TEXT        NOT NULL,
    attempts   INTEGER     NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    sent_at    TIMESTAMPTZ
);
CREATE UNIQUE INDEX IF NOT EXISTS outbox_dedup_idx ON outbox(dedup_key);
CREATE INDEX IF NOT EXISTS outbox_pending_idx
    ON outbox(id) WHERE sent_at IS NULL;

CREATE TABLE IF NOT EXISTS commands (
    id         BIGSERIAL PRIMARY KEY,
    rig_id     TEXT        NOT NULL REFERENCES rigs(rig_id) ON DELETE CASCADE,
    kind       TEXT        NOT NULL,
    args       JSONB       NOT NULL DEFAULT '{}'::jsonb,
    chat_id    BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    taken_at   TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS commands_pending_idx
    ON commands(rig_id, id) WHERE taken_at IS NULL;

CREATE TABLE IF NOT EXISTS chats (
    chat_id    BIGINT PRIMARY KEY,
    active_rig TEXT,
    prefs      JSONB       NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def initialize_database() -> bool:
    """Create the schema, retrying while the database wakes up.

    A failure here is logged and tolerated: every operation reconnects on
    its own, so the service must not refuse to start merely because the
    database was slow to come up alongside it.
    """
    for attempt in range(6):
        try:
            with _cursor(commit=True) as cur:
                cur.execute(SCHEMA)
            logger.info("database schema ready")
            return True
        except Exception as exc:                       # noqa: BLE001
            logger.warning("DB init attempt %d failed: %s", attempt + 1, exc)
            time.sleep(min(5 * (attempt + 1), 20))
    logger.error("database initialization failed — the service keeps running "
                 "and retries on every use")
    return False


# ------------------------------------------------------------- helpers ---
def token_hash(token: str) -> str:
    return hashlib.sha256((token or "").encode("utf-8")).hexdigest()


def token_matches(token: str, stored_hash: str) -> bool:
    return hmac.compare_digest(token_hash(token), stored_hash or "")


# ---------------------------------------------------------------- rigs ---
def rig_get(rig_id: str) -> Optional[dict]:
    """Row as a dict, ``{}`` when there is no such rig, ``None`` on error."""
    try:
        with _cursor() as cur:
            cur.execute("SELECT * FROM rigs WHERE rig_id = %s", (rig_id,))
            row = cur.fetchone()
        return dict(row) if row else {}
    except Exception as exc:                           # noqa: BLE001
        logger.error("rig_get(%s) failed: %s", rig_id, exc)
        return None


def rig_create(rig_id: str, name: str, token: str,
               allow_control: bool) -> Optional[dict]:
    """Trust-on-first-use registration; returns the row or None on error."""
    try:
        with _cursor(commit=True) as cur:
            cur.execute(
                """
                INSERT INTO rigs (rig_id, name, token_hash, allow_control)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (rig_id) DO NOTHING
                RETURNING *
                """,
                (rig_id, name or rig_id[:8], token_hash(token),
                 bool(allow_control)),
            )
            row = cur.fetchone()
        return dict(row) if row else {}
    except Exception as exc:                           # noqa: BLE001
        logger.error("rig_create(%s) failed: %s", rig_id, exc)
        return None


def rig_update_meta(rig_id: str, name: str, allow_control: bool) -> bool:
    try:
        with _cursor(commit=True) as cur:
            cur.execute(
                "UPDATE rigs SET name = %s, allow_control = %s "
                "WHERE rig_id = %s",
                (name, bool(allow_control), rig_id))
        return True
    except Exception as exc:                           # noqa: BLE001
        logger.error("rig_update_meta(%s) failed: %s", rig_id, exc)
        return False


def rig_seen(rig_id: str, state: dict, sweep_state: str) -> bool:
    """One upsert per push: last_seen, the small state blob, silence reset."""
    try:
        with _cursor(commit=True) as cur:
            cur.execute(
                """
                UPDATE rigs
                   SET last_seen = now(),
                       state = %s,
                       last_push_state = %s,
                       silent_since = NULL
                 WHERE rig_id = %s
                """,
                (json.dumps(state, default=str), sweep_state, rig_id))
        return True
    except Exception as exc:                           # noqa: BLE001
        logger.error("rig_seen(%s) failed: %s", rig_id, exc)
        return False


def rigs_gone_silent(grace_s: float) -> Optional[list]:
    """Rigs that were mid-sweep and have stopped reporting.

    ``silent_since`` is stamped by this same statement, so each silence is
    announced exactly once however often the watchdog runs.
    """
    try:
        with _cursor(commit=True) as cur:
            cur.execute(
                """
                UPDATE rigs
                   SET silent_since = now()
                 WHERE silent_since IS NULL
                   AND last_seen IS NOT NULL
                   AND last_push_state IN ('running', 'paused')
                   AND last_seen < now() - (%s * INTERVAL '1 second')
                RETURNING rig_id, name, last_seen, state
                """,
                (float(grace_s),))
            return [dict(r) for r in cur.fetchall()]
    except Exception as exc:                           # noqa: BLE001
        logger.error("rigs_gone_silent failed: %s", exc)
        return None


# -------------------------------------------------------- pairing codes ---
def pair_code_new(rig_id: str, ttl_s: float) -> Optional[dict]:
    """Mint a fresh code for a rig, replacing any it has not spent.

    One live code per rig: a pile of old codes lying around is a pile of
    ways in, and the rig can always show a new one.
    """
    try:
        with _cursor(commit=True) as cur:
            cur.execute("DELETE FROM pair_codes "
                        "WHERE rig_id = %s AND used_at IS NULL", (rig_id,))
            for _ in range(12):
                code = f"{secrets.randbelow(900000) + 100000:06d}"
                cur.execute(
                    """
                    INSERT INTO pair_codes (code, rig_id, expires_at)
                    VALUES (%s, %s, now() + (%s * INTERVAL '1 second'))
                    ON CONFLICT (code) DO NOTHING
                    RETURNING code, expires_at
                    """,
                    (code, rig_id, float(ttl_s)))
                row = cur.fetchone()
                if row:
                    return {"code": row["code"],
                            "expires_at": row["expires_at"]}
            return {}                    # every draw collided: ask again
    except Exception as exc:                           # noqa: BLE001
        logger.error("pair_code_new(%s) failed: %s", rig_id, exc)
        return None


def pair_code_redeem(code: str, chat_id: int, title: str) -> Optional[dict]:
    """Spend a code and link the chat.

    The claim is one statement with ``used_at IS NULL`` in its WHERE
    clause, so two people racing on the same code cannot both win, and a
    code cannot be replayed.

    Returns the rig row on success, ``{}`` if the code is unknown, expired
    or already spent, and ``None`` on a database error — those are three
    different things and the bot says three different things.
    """
    try:
        with _cursor(commit=True) as cur:
            cur.execute(
                """
                UPDATE pair_codes
                   SET used_at = now(), used_by = %s
                 WHERE code = %s AND used_at IS NULL AND expires_at > now()
                RETURNING rig_id
                """,
                (int(chat_id), str(code)))
            row = cur.fetchone()
            if not row:
                return {}
            rig_id = row["rig_id"]
            cur.execute(
                """
                INSERT INTO links (rig_id, chat_id, title)
                VALUES (%s, %s, %s)
                ON CONFLICT (rig_id, chat_id) DO UPDATE SET title = %s
                """,
                (rig_id, int(chat_id), title, title))
            cur.execute(
                "INSERT INTO chats (chat_id, active_rig) VALUES (%s, %s) "
                "ON CONFLICT (chat_id) DO UPDATE SET active_rig = "
                "EXCLUDED.active_rig", (int(chat_id), rig_id))
            cur.execute("SELECT * FROM rigs WHERE rig_id = %s", (rig_id,))
            rig = cur.fetchone()
        return dict(rig) if rig else {}
    except Exception as exc:                           # noqa: BLE001
        logger.error("pair_code_redeem failed: %s", exc)
        return None


# --------------------------------------------------------------- links ---
def link_get(rig_id: str, chat_id: int) -> Optional[dict]:
    try:
        with _cursor() as cur:
            cur.execute(
                "SELECT l.*, r.name AS rig_name, r.allow_control, "
                "       r.last_seen, r.last_push_state, r.state "
                "  FROM links l JOIN rigs r USING (rig_id) "
                " WHERE l.rig_id = %s AND l.chat_id = %s",
                (rig_id, int(chat_id)))
            row = cur.fetchone()
        return dict(row) if row else {}
    except Exception as exc:                           # noqa: BLE001
        logger.error("link_get failed: %s", exc)
        return None


def links_for_chat(chat_id: int) -> Optional[list]:
    """Every rig this chat may see.  ``[]`` means none; ``None`` means the
    database is unreachable and the caller must say so rather than telling
    the user they have no rigs."""
    try:
        with _cursor() as cur:
            cur.execute(
                "SELECT l.*, r.name AS rig_name, r.allow_control, "
                "       r.last_seen, r.last_push_state, r.state "
                "  FROM links l JOIN rigs r USING (rig_id) "
                " WHERE l.chat_id = %s ORDER BY r.name, l.rig_id",
                (int(chat_id),))
            return [dict(r) for r in cur.fetchall()]
    except Exception as exc:                           # noqa: BLE001
        logger.error("links_for_chat(%s) failed: %s", chat_id, exc)
        return None


def links_for_rig(rig_id: str) -> Optional[list]:
    try:
        with _cursor() as cur:
            cur.execute(
                "SELECT * FROM links WHERE rig_id = %s ORDER BY created_at",
                (rig_id,))
            return [dict(r) for r in cur.fetchall()]
    except Exception as exc:                           # noqa: BLE001
        logger.error("links_for_rig(%s) failed: %s", rig_id, exc)
        return None


def link_save_prefs(rig_id: str, chat_id: int, prefs: dict) -> bool:
    """Upsert ONE link's preferences — never a whole-table rewrite."""
    try:
        with _cursor(commit=True) as cur:
            cur.execute(
                "UPDATE links SET prefs = %s "
                "WHERE rig_id = %s AND chat_id = %s",
                (json.dumps(prefs), rig_id, int(chat_id)))
        return True
    except Exception as exc:                           # noqa: BLE001
        logger.error("link_save_prefs failed: %s", exc)
        return False


def link_delete(rig_id: str, chat_id: int) -> bool:
    """Actually DELETE.  A row merely flagged inactive comes back to life
    on the next restart; this is the fix for that class of bug."""
    try:
        with _cursor(commit=True) as cur:
            cur.execute(
                "DELETE FROM links WHERE rig_id = %s AND chat_id = %s",
                (rig_id, int(chat_id)))
        return True
    except Exception as exc:                           # noqa: BLE001
        logger.error("link_delete failed: %s", exc)
        return False


def links_delete_for_chat(chat_id: int) -> bool:
    try:
        with _cursor(commit=True) as cur:
            cur.execute("DELETE FROM links WHERE chat_id = %s",
                        (int(chat_id),))
            cur.execute("DELETE FROM chats WHERE chat_id = %s",
                        (int(chat_id),))
        return True
    except Exception as exc:                           # noqa: BLE001
        logger.error("links_delete_for_chat failed: %s", exc)
        return False


def link_touch_progress(rig_id: str, chat_id: int) -> bool:
    try:
        with _cursor(commit=True) as cur:
            cur.execute(
                "UPDATE links SET last_progress_at = now() "
                "WHERE rig_id = %s AND chat_id = %s", (rig_id, int(chat_id)))
        return True
    except Exception:                                  # noqa: BLE001
        return False


# --------------------------------------------------------------- chats ---
def chat_get(chat_id: int) -> Optional[dict]:
    try:
        with _cursor(commit=True) as cur:
            cur.execute(
                "INSERT INTO chats (chat_id) VALUES (%s) "
                "ON CONFLICT (chat_id) DO NOTHING", (int(chat_id),))
            cur.execute("SELECT * FROM chats WHERE chat_id = %s",
                        (int(chat_id),))
            row = cur.fetchone()
        return dict(row) if row else {}
    except Exception as exc:                           # noqa: BLE001
        logger.error("chat_get(%s) failed: %s", chat_id, exc)
        return None


def chat_set_active_rig(chat_id: int, rig_id: str) -> bool:
    try:
        with _cursor(commit=True) as cur:
            cur.execute(
                "INSERT INTO chats (chat_id, active_rig) VALUES (%s, %s) "
                "ON CONFLICT (chat_id) DO UPDATE SET active_rig = "
                "EXCLUDED.active_rig", (int(chat_id), rig_id))
        return True
    except Exception as exc:                           # noqa: BLE001
        logger.error("chat_set_active_rig failed: %s", exc)
        return False


# ----------------------------------------------------------- snapshots ---
def snapshot_put(rig_id: str, payload: bytes) -> bool:
    try:
        with _cursor(commit=True) as cur:
            cur.execute(
                """
                INSERT INTO snapshots (rig_id, payload, updated_at)
                VALUES (%s, %s, now())
                ON CONFLICT (rig_id) DO UPDATE
                    SET payload = EXCLUDED.payload, updated_at = now()
                """,
                (rig_id, psycopg2.Binary(payload)))
        return True
    except Exception as exc:                           # noqa: BLE001
        logger.error("snapshot_put(%s) failed: %s", rig_id, exc)
        return False


def snapshot_get(rig_id: str) -> Optional[dict]:
    """``{"payload": bytes, "updated_at": dt}``, ``{}`` if the rig has never
    sent one, ``None`` on a database error."""
    try:
        with _cursor() as cur:
            cur.execute(
                "SELECT payload, updated_at FROM snapshots WHERE rig_id = %s",
                (rig_id,))
            row = cur.fetchone()
        if not row:
            return {}
        return {"payload": bytes(row["payload"]),
                "updated_at": row["updated_at"]}
    except Exception as exc:                           # noqa: BLE001
        logger.error("snapshot_get(%s) failed: %s", rig_id, exc)
        return None


def snapshot_age_marker(rig_id: str):
    try:
        with _cursor() as cur:
            cur.execute("SELECT updated_at FROM snapshots WHERE rig_id = %s",
                        (rig_id,))
            row = cur.fetchone()
        return row["updated_at"] if row else None
    except Exception:                                  # noqa: BLE001
        return None


# -------------------------------------------------------------- outbox ---
def outbox_add(chat_id: int, kind: str, body: str, dedup_key: str,
               rig_id: str = None, photo: bytes = None,
               markup: Any = None) -> bool:
    """Queue one notification.

    ``dedup_key`` is what makes the rig's own retries harmless: the rig
    numbers its events, so an event re-sent after a network timeout
    collides with the row already queued and is dropped.
    """
    try:
        with _cursor(commit=True) as cur:
            cur.execute(
                """
                INSERT INTO outbox (rig_id, chat_id, kind, body, photo,
                                    markup, dedup_key)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (dedup_key) DO NOTHING
                """,
                (rig_id, int(chat_id), kind, body,
                 psycopg2.Binary(photo) if photo else None,
                 json.dumps(markup) if markup is not None else None,
                 dedup_key))
        return True
    except Exception as exc:                           # noqa: BLE001
        logger.error("outbox_add failed: %s", exc)
        return False


def outbox_take(limit: int = 25) -> Optional[list]:
    try:
        with _cursor(commit=True) as cur:
            cur.execute(
                """
                SELECT id, rig_id, chat_id, kind, body, photo, markup,
                       attempts
                  FROM outbox
                 WHERE sent_at IS NULL
                   AND attempts < %s
                 ORDER BY id
                 LIMIT %s
                 FOR UPDATE SKIP LOCKED
                """,
                (config.MAX_SEND_ATTEMPTS, int(limit)))
            rows = [dict(r) for r in cur.fetchall()]
            if rows:
                cur.execute(
                    "UPDATE outbox SET attempts = attempts + 1 "
                    "WHERE id = ANY(%s)", ([r["id"] for r in rows],))
        for r in rows:
            if r["photo"] is not None:
                r["photo"] = bytes(r["photo"])
        return rows
    except Exception as exc:                           # noqa: BLE001
        logger.error("outbox_take failed: %s", exc)
        return None


def outbox_mark_sent(ids: list) -> bool:
    if not ids:
        return True
    try:
        with _cursor(commit=True) as cur:
            cur.execute("UPDATE outbox SET sent_at = now() WHERE id = ANY(%s)",
                        (list(ids),))
        return True
    except Exception as exc:                           # noqa: BLE001
        logger.error("outbox_mark_sent failed: %s", exc)
        return False


def outbox_drop_for_chat(chat_id: int) -> bool:
    """A chat that blocked the bot must stop generating work forever."""
    try:
        with _cursor(commit=True) as cur:
            cur.execute("DELETE FROM outbox WHERE chat_id = %s AND "
                        "sent_at IS NULL", (int(chat_id),))
        return True
    except Exception:                                  # noqa: BLE001
        return False


# ------------------------------------------------------------ commands ---
def command_add(rig_id: str, kind: str, args: dict = None,
                chat_id: int = None) -> Optional[int]:
    try:
        with _cursor(commit=True) as cur:
            cur.execute(
                "INSERT INTO commands (rig_id, kind, args, chat_id) "
                "VALUES (%s, %s, %s, %s) RETURNING id",
                (rig_id, kind, json.dumps(args or {}),
                 int(chat_id) if chat_id else None))
            return int(cur.fetchone()["id"])
    except Exception as exc:                           # noqa: BLE001
        logger.error("command_add failed: %s", exc)
        return None


def commands_take(rig_id: str, limit: int = 10) -> Optional[list]:
    """Hand the rig its pending commands and mark them collected in the
    same statement, so a retried push can never run a command twice."""
    try:
        with _cursor(commit=True) as cur:
            cur.execute(
                """
                UPDATE commands SET taken_at = now()
                 WHERE id IN (SELECT id FROM commands
                               WHERE rig_id = %s AND taken_at IS NULL
                               ORDER BY id LIMIT %s
                               FOR UPDATE SKIP LOCKED)
                RETURNING id, kind, args, chat_id
                """,
                (rig_id, int(limit)))
            return [dict(r) for r in cur.fetchall()]
    except Exception as exc:                           # noqa: BLE001
        logger.error("commands_take(%s) failed: %s", rig_id, exc)
        return None


def command_get(command_id: int) -> Optional[dict]:
    try:
        with _cursor() as cur:
            cur.execute("SELECT * FROM commands WHERE id = %s",
                        (int(command_id),))
            row = cur.fetchone()
        return dict(row) if row else {}
    except Exception:                                  # noqa: BLE001
        return None


# --------------------------------------------------------- maintenance ---
def maintenance() -> Optional[dict]:
    try:
        with _cursor(commit=True) as cur:
            cur.execute(
                "DELETE FROM outbox WHERE sent_at IS NOT NULL "
                "AND sent_at < now() - (%s * INTERVAL '1 hour')",
                (float(config.OUTBOX_RETENTION_H),))
            sent = cur.rowcount
            cur.execute(
                "DELETE FROM outbox WHERE sent_at IS NULL AND attempts >= %s "
                "AND created_at < now() - INTERVAL '1 day'",
                (config.MAX_SEND_ATTEMPTS,))
            dead = cur.rowcount
            cur.execute(
                "DELETE FROM commands WHERE taken_at IS NULL "
                "AND created_at < now() - (%s * INTERVAL '1 second')",
                (float(config.COMMAND_TTL_S),))
            stale = cur.rowcount
            cur.execute(
                "DELETE FROM commands WHERE taken_at IS NOT NULL "
                "AND taken_at < now() - INTERVAL '1 day'")
            cur.execute("DELETE FROM pair_codes WHERE "
                        "expires_at < now() - INTERVAL '1 day'")
            codes = cur.rowcount
        return {"sent_pruned": sent, "dead_pruned": dead,
                "commands_pruned": stale, "codes_pruned": codes}
    except Exception as exc:                           # noqa: BLE001
        logger.error("maintenance failed: %s", exc)
        return None
