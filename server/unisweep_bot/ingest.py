"""The rig-facing HTTP API.

Why HTTP and not a direct database connection from the lab computer:

* the measurement PC sits behind whatever the institute's firewall allows,
  and outbound 443 is the one thing that always works;
* the database password then never leaves this service — a lab machine
  holds one rig token, revocable on its own, instead of full credentials
  to everybody's data.  (Credentials on client machines are exactly the
  mistake this whole design is a reaction to.)

Endpoints, all idempotent:

``POST /api/v1/hello``         register or re-authenticate a rig
``POST /api/v1/pair``          mint a 6-digit pairing code to show the user
``POST /api/v1/push``          heartbeat + events + (optionally) a snapshot
``POST /api/v1/links/remove``  drop one linked chat
``POST /api/v1/result``        the outcome of a command the rig collected

The reply to ``push`` carries the rig's pending commands and its current
list of linked chats, so control and the roster both flow back over the
rig's own outbound connection — nothing has to listen on the lab network.
"""

from __future__ import annotations

import asyncio
import gzip
import json
import logging
import time
from typing import Any

from aiohttp import web

from . import config, db, waiters, render
from .formatting import (DEFAULT_PREFS, esc, fmt_duration, prefs_of,
                         unpack_snapshot)

logger = logging.getLogger(__name__)

routes = web.RouteTableDef()

#: notification kinds a rig may emit, mapped to the preference that gates
#: them.  An unknown kind is dropped rather than delivered — a future rig
#: version cannot spam an older service.
EVENT_PREF = {
    "started": "started",
    "finished": "finished",
    "error": "error",
    "guard": "guard",
    "paused": "paused",
    "resumed": "paused",
    "file": "file",
}

_LAST_CALL: dict = {}          # (rig_id, endpoint) -> monotonic seconds


def _throttle(rig_id: str, endpoint: str, seconds: float) -> bool:
    key = (rig_id, endpoint)
    now = time.monotonic()
    if now - _LAST_CALL.get(key, 0.0) < seconds:
        return True
    _LAST_CALL[key] = now
    return False


async def _body(request: web.Request) -> Any:
    raw = await request.content.read(config.MAX_BODY_BYTES + 1)
    if len(raw) > config.MAX_BODY_BYTES:
        raise web.HTTPRequestEntityTooLarge(
            max_size=config.MAX_BODY_BYTES, actual_size=len(raw))
    if request.headers.get("X-Body-Encoding", "").lower() == "gzip" or \
            raw[:2] == b"\x1f\x8b":
        try:
            raw = await asyncio.to_thread(gzip.decompress, raw)
        except Exception:                              # noqa: BLE001
            raise web.HTTPBadRequest(reason="bad gzip body")
    try:
        data = json.loads(raw.decode("utf-8"))
    except Exception:                                  # noqa: BLE001
        raise web.HTTPBadRequest(reason="body is not JSON")
    if not isinstance(data, dict):
        raise web.HTTPBadRequest(reason="body must be a JSON object")
    return data


def _fail(status: int, reason: str) -> web.Response:
    return web.json_response({"ok": False, "error": reason}, status=status)


async def _authenticate(request: web.Request):
    rig_id = (request.headers.get("X-Rig-Id") or "").strip()
    token = (request.headers.get("X-Rig-Token") or "").strip()
    if not rig_id or not token:
        return None, _fail(401, "missing rig credentials")
    rig = await asyncio.to_thread(db.rig_get, rig_id)
    if rig is None:
        # the database is down — tell the rig to retry.  Never "unknown
        # rig", which would make it register itself all over again.
        return None, _fail(503, "database unavailable")
    if not rig:
        return None, _fail(404, "unknown rig — call /hello first")
    if not db.token_matches(token, rig.get("token_hash", "")):
        return None, _fail(401, "bad rig token")
    return rig, None


def _bot_link(request: web.Request) -> str:
    username = request.app.get("bot_username") or ""
    return f"https://t.me/{username}" if username else ""


async def _roster(rig_id: str):
    """The linked chats, as the Settings page shows them."""
    links = await asyncio.to_thread(db.links_for_rig, rig_id)
    if links is None:
        return None
    return [{"chat_id": int(link["chat_id"]),
             "title": link.get("title") or "",
             "since": link["created_at"].isoformat()
             if link.get("created_at") else None}
            for link in links]


# ------------------------------------------------------------- endpoints --
@routes.get("/")
@routes.get("/healthz")
async def healthz(request: web.Request) -> web.Response:
    return web.json_response({"ok": True, "service": "unisweep-telegram",
                              "bot": request.app.get("bot_username", "")})


@routes.post("/api/v1/hello")
async def hello(request: web.Request) -> web.Response:
    """Register a rig (trust on first use) and read back its roster."""
    data = await _body(request)
    rig_id = str(data.get("rig_id") or "").strip()
    token = str(data.get("rig_token") or "").strip()
    name = str(data.get("name") or "").strip()[:64]
    allow_control = bool(data.get("allow_control"))
    if not rig_id or not token or len(token) < 20:
        return _fail(400, "rig_id and a rig_token of >= 20 chars are required")
    if _throttle(rig_id, "hello", 2.0):
        return _fail(429, "slow down")

    rig = await asyncio.to_thread(db.rig_get, rig_id)
    if rig is None:
        return _fail(503, "database unavailable")

    # Setup names are how people tell setups apart in the chat, so they
    # have to be unique across the service — otherwise every message and
    # every /rigs entry is ambiguous.
    if name:
        owner = await asyncio.to_thread(db.rig_name_owner, name)
        if owner is None:
            return _fail(503, "database unavailable")
        if owner and owner != rig_id:
            return _fail(409, "name_taken")

    if not rig:
        created = await asyncio.to_thread(db.rig_create, rig_id, name, token,
                                          allow_control)
        if created is None:
            return _fail(503, "database unavailable")
        if created.get("error") == "name_taken":
            return _fail(409, "name_taken")
        rig = await asyncio.to_thread(db.rig_get, rig_id)
        if not rig:
            return _fail(503, "registration did not stick")
        logger.info("registered setup %s (%s)", rig_id, name)
    elif not db.token_matches(token, rig.get("token_hash", "")):
        return _fail(401, "this rig id is taken by another token")
    else:
        status = await asyncio.to_thread(db.rig_update_meta, rig_id,
                                         name or rig.get("name", ""),
                                         allow_control)
        if status is None:
            return _fail(503, "database unavailable")
        if status == "name_taken":
            return _fail(409, "name_taken")

    roster = await _roster(rig_id)
    return web.json_response({
        "ok": True,
        "rig_id": rig_id,
        "bot_username": request.app.get("bot_username", ""),
        "bot_link": _bot_link(request),
        "links": roster if roster is not None else [],
        "roster_known": roster is not None,
    })


@routes.post("/api/v1/pair")
async def pair(request: web.Request) -> web.Response:
    """Mint a pairing code for the rig to show.

    Whoever sends this code to the bot within the window is linked.  That
    is the whole authentication: it replaces asking people to find and
    type their numeric chat id, and — unlike a chat id, which is public
    and permanent — a code is short-lived and single-use, so it cannot be
    used to sign somebody else up.
    """
    rig, err = await _authenticate(request)
    if err is not None:
        return err
    if _throttle(rig["rig_id"], "pair", 3.0):
        return _fail(429, "slow down")
    issued = await asyncio.to_thread(db.pair_code_new, rig["rig_id"],
                                     config.PAIR_CODE_TTL_S)
    if issued is None:
        return _fail(503, "database unavailable")
    if not issued:
        return _fail(503, "could not allocate a code — try again")
    return web.json_response({
        "ok": True,
        "code": issued["code"],
        "expires_at": issued["expires_at"].isoformat(),
        "ttl_s": float(config.PAIR_CODE_TTL_S),
        "bot_username": request.app.get("bot_username", ""),
        "bot_link": _bot_link(request),
    })


@routes.post("/api/v1/links/remove")
async def links_remove(request: web.Request) -> web.Response:
    """Unlink one chat from the rig, from the rig's own settings page."""
    rig, err = await _authenticate(request)
    if err is not None:
        return err
    data = await _body(request)
    try:
        chat_id = int(data.get("chat_id"))
    except (TypeError, ValueError):
        return _fail(400, "chat_id is required")
    ok = await asyncio.to_thread(db.link_delete, rig["rig_id"], chat_id)
    if not ok:
        return _fail(503, "database unavailable")
    # telling them is the honest thing, and it stops the silent-failure
    # question "why did the bot stop messaging me?"
    await asyncio.to_thread(
        db.outbox_add, chat_id, "unlinked",
        f"🔌 <b>{esc(rig.get('name') or rig['rig_id'])}</b> removed this chat "
        f"from its notifications.\n\nAsk for a new pairing code on that "
        f"computer if this was not intended.",
        f"unlink:{rig['rig_id']}:{chat_id}:{int(time.time())}",
        rig["rig_id"])
    roster = await _roster(rig["rig_id"])
    return web.json_response({"ok": True,
                              "links": roster if roster is not None else []})


@routes.post("/api/v1/push")
async def push(request: web.Request) -> web.Response:
    """Heartbeat, events and (optionally) a fresh data snapshot."""
    rig, err = await _authenticate(request)
    if err is not None:
        return err
    rig_id = rig["rig_id"]
    data = await _body(request)

    state = data.get("state") or {}
    if not isinstance(state, dict):
        state = {}
    sweep_state = str(state.get("state") or "idle")[:24]

    snapshot = data.get("snapshot")
    snap_saved = False
    if isinstance(snapshot, dict) and snapshot:
        blob = await asyncio.to_thread(
            lambda: gzip.compress(json.dumps(snapshot).encode("utf-8"), 6))
        snap_saved = await asyncio.to_thread(db.snapshot_put, rig_id, blob)

    if not await asyncio.to_thread(db.rig_seen, rig_id, state, sweep_state):
        return _fail(503, "database unavailable")

    tools = data.get("tools")
    if isinstance(tools, list) and tools:
        # the rig is the source of truth for what it can do, so a setup on
        # an older Unisweep advertises exactly what it has
        await asyncio.to_thread(db.rig_tools_set, rig_id, tools[:200])

    links = await asyncio.to_thread(db.links_for_rig, rig_id)
    roster_known = links is not None
    if links is None:
        # Deliberately not an error for the rig: its data is stored and the
        # notifications will be built on a later push.  A database blip
        # must never make a rig believe it has been unlinked.
        links = []

    events = data.get("events") or []
    if isinstance(events, list) and links:
        await _fanout(rig, links, events[:config.MAX_EVENTS_PER_PUSH],
                      snapshot)
    if links:
        await _progress_pings(rig, links, state)

    commands = await asyncio.to_thread(db.commands_take, rig_id)
    if commands is None:
        commands = []
    if not commands:
        # Hold the beat open rather than sending an empty answer: a relayed
        # tool call would otherwise wait for the next one, and an assistant
        # that pauses fifteen seconds per question is an assistant nobody
        # uses. The rig asks for this by sending hold_s; a rig that does
        # not simply gets the old behaviour.
        try:
            hold = float(data.get("hold_s") or 0.0)
        except (TypeError, ValueError):
            hold = 0.0
        if hold > 0:
            if await waiters.wait_for_work(rig_id,
                                           min(hold, config.MAX_HOLD_S)):
                commands = await asyncio.to_thread(db.commands_take, rig_id)
                if commands is None:
                    commands = []

    marker = await asyncio.to_thread(db.snapshot_age_marker, rig_id)
    return web.json_response({
        "ok": True,
        "stored_snapshot": snap_saved,
        "snapshot_at": marker.isoformat() if marker else None,
        "commands": [{"id": c["id"], "kind": c["kind"],
                      "args": c["args"] or {}, "chat_id": c["chat_id"]}
                     for c in commands],
        "links": [{"chat_id": int(link["chat_id"]),
                   "title": link.get("title") or "",
                   "since": link["created_at"].isoformat()
                   if link.get("created_at") else None}
                  for link in links],
        "roster_known": roster_known,
    })


async def _fanout(rig: dict, links: list, events: list,
                  snapshot: Any) -> None:
    """Turn rig events into per-chat outbox rows.

    The rig numbers its events, and the de-duplication key is
    ``rig:seq:chat`` — so a push retried after a timeout produces the same
    keys and inserts nothing the second time.
    """
    rig_id = rig["rig_id"]
    name = rig.get("name") or rig_id
    photo_cache: dict = {}

    for raw in events:
        if not isinstance(raw, dict):
            continue
        kind = str(raw.get("kind") or "")
        pref_key = EVENT_PREF.get(kind)
        if pref_key is None:
            continue
        seq = raw.get("seq")
        text = str(raw.get("text") or "").strip()
        if not text:
            continue
        body = f"<b>{esc(name)}</b>\n{esc(text)}"

        for link in links:
            prefs = prefs_of(link)
            if not prefs.get(pref_key, DEFAULT_PREFS.get(pref_key, False)):
                continue
            chat_id = int(link["chat_id"])
            photo = None
            if kind == "finished" and prefs.get("photo"):
                photo = await _finish_photo(rig_id, name, snapshot,
                                            prefs.get("read") or "",
                                            photo_cache)
            key = (f"{rig_id}:{seq}:{chat_id}" if seq is not None
                   else f"{rig_id}:{kind}:{hash(text) & 0xffffffff}:{chat_id}")
            await asyncio.to_thread(db.outbox_add, chat_id, kind, body, key,
                                    rig_id, photo, None)


async def _finish_photo(rig_id: str, name: str, snapshot: Any, read: str,
                        cache: dict):
    """One render per parameter, however many chats want that parameter."""
    if not isinstance(snapshot, dict) or not snapshot:
        stored = await asyncio.to_thread(db.snapshot_get, rig_id)
        snapshot = unpack_snapshot((stored or {}).get("payload")) or {}
    reads = render.readable_reads(snapshot)
    if not reads:
        return None
    if read not in reads:
        read = reads[0]
    if read in cache:
        return cache[read]
    photo = await asyncio.to_thread(
        render.safe_render, render.auto_figure, snapshot, read,
        f"{name} — {read}", snapshot.get("file", ""),
        snapshot.get("cmap", ""))
    cache[read] = photo
    return photo


async def _progress_pings(rig: dict, links: list, state: dict) -> None:
    """Optional "still going" messages, per chat, on that chat's cadence."""
    prog = state.get("progress") or {}
    if str(state.get("state")) != "running" or not prog.get("total"):
        return
    from .formatting import age_seconds
    rig_id = rig["rig_id"]
    name = rig.get("name") or rig_id
    done, total = int(prog.get("done", 0)), int(prog.get("total") or 0)
    pct = 100.0 * done / total if total else 0.0
    for link in links:
        minutes = prefs_of(link).get("progress_min") or 0
        if not minutes:
            continue
        age = age_seconds(link.get("last_progress_at"))
        if age is not None and age < minutes * 60:
            continue
        chat_id = int(link["chat_id"])
        body = (f"<b>{esc(name)}</b>\n⏱ {pct:.0f}% ({done}/{total})"
                + (f" · ETA {fmt_duration(prog.get('eta_s'))}"
                   if prog.get("eta_s") is not None else ""))
        bucket = int(time.time() // max(minutes * 60, 60))
        await asyncio.to_thread(db.outbox_add, chat_id, "progress", body,
                                f"{rig_id}:prog:{bucket}:{chat_id}", rig_id)
        await asyncio.to_thread(db.link_touch_progress, rig_id, chat_id)


@routes.post("/api/v1/connector")
async def connector_token(request: web.Request) -> web.Response:
    """Mint this rig's connector token, for pasting into Claude.

    Rig-authenticated, so the credential is only ever handed to the
    computer that owns the instruments. Issuing replaces any earlier one:
    that is the revoke, and it is why this is separate from rig_token —
    cutting off an assistant must not make the rig pair again.
    """
    rig, err = await _authenticate(request)
    if err is not None:
        return err
    token = await asyncio.to_thread(db.connector_issue, rig["rig_id"])
    if token is None:
        return _fail(503, "database unavailable")
    if not token:
        return _fail(404, "unknown rig")
    base = str(request.url.origin())
    return web.json_response({"ok": True, "token": token,
                              "url": f"{base}/mcp"})


@routes.post("/api/v1/result")
async def result(request: web.Request) -> web.Response:
    """What happened when the rig ran a command the bot sent it."""
    rig, err = await _authenticate(request)
    if err is not None:
        return err
    data = await _body(request)
    try:
        command_id = int(data.get("command_id"))
    except (TypeError, ValueError):
        return _fail(400, "command_id is required")
    command = await asyncio.to_thread(db.command_get, command_id)
    if command is None:
        return _fail(503, "database unavailable")
    if not command or command.get("rig_id") != rig["rig_id"]:
        return _fail(404, "no such command for this rig")
    payload = {"ok": bool(data.get("ok")),
               "result": data.get("result"),
               "error": data.get("error") or "",
               "detail": str(data.get("detail") or "")[:400]}
    await asyncio.to_thread(db.command_finish, command_id, payload)
    # a relayed tool call is somebody waiting on an open HTTPS request;
    # a Telegram button press is nobody, and that is not an error
    waiters.resolve(command_id, payload)

    chat_id = command.get("chat_id")
    if chat_id:
        ok = bool(data.get("ok"))
        detail = str(data.get("detail") or "")[:400]
        icon = "✅" if ok else "⚠️"
        body = (f"<b>{esc(rig.get('name') or rig['rig_id'])}</b>\n"
                f"{icon} {esc(command['kind'])}"
                + (f" — {esc(detail)}" if detail else ""))
        await asyncio.to_thread(db.outbox_add, int(chat_id), "result", body,
                                f"result:{command_id}", rig["rig_id"])
    return web.json_response({"ok": True})


def build_app(bot_username: str = "") -> web.Application:
    app = web.Application(client_max_size=config.MAX_BODY_BYTES + 1024)
    app["bot_username"] = bot_username
    app.add_routes(routes)
    from . import connector
    app.add_routes(connector.routes)
    return app
