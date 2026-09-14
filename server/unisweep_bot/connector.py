"""Unisweep as a Claude connector.

Claude's Settings → Connectors takes remote servers with public URLs
only; a server on the lab PC is a desktop extension and never appears
there. So the MCP endpoint lives here, on the group's service, and every
tool call is relayed to the rig down the channel that already carries
pause and stop from Telegram: queued as a command, collected on the rig's
next heartbeat, answered through ``/api/v1/result``.

Nothing reaches into the lab network, which is what usually kills this
sort of thing on a university subnet.

**The tool list comes from the rig**, not from a copy kept here: a setup
running an older Unisweep advertises exactly what it has, and this
service can never drift out of step with the application it speaks for.

**Permission is decided on the rig.** This module marks a call as
requiring control, but the rig is what refuses it — a server asking
nicely is not authorisation.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Optional

from aiohttp import web

from . import db, waiters

logger = logging.getLogger(__name__)

PROTOCOL_VERSION = "2025-06-18"
SUPPORTED_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")
SERVER_INFO = {"name": "unisweep", "version": "1.0.0"}

#: How long a relayed call may take before the caller is told the rig did
#: not answer. Generous, because the rig may be mid-point on a slow
#: instrument, but finite: an assistant that hangs is worse than one told
#: the setup is not responding.
CALL_TIMEOUT_S = 90.0

#: What the rig will refuse unless its "allow control" switch is on. Kept
#: here only so the refusal can be explained before the round trip; the
#: rig enforces it again regardless.
CONTROL_TOOLS = frozenset({
    "set_parameter", "stop_sweep", "pause_sweep", "resume_sweep",
    "ramp_to_zero", "press_control", "set_controls",
})

routes = web.RouteTableDef()


def _rpc_error(ident, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": ident,
            "error": {"code": code, "message": message}}


def _tool_error(message: str) -> dict:
    return {"content": [{"type": "text", "text": message}], "isError": True}


def _tool_result(result: Any) -> dict:
    if not isinstance(result, dict):
        result = {"result": result}
    return {"content": [{"type": "text",
                         "text": json.dumps(result, indent=2, default=str)}],
            "structuredContent": result,
            "isError": False}


def public_base(request: web.Request) -> str:
    """The address the outside world reaches this service on.

    Railway terminates TLS at its router and forwards plain HTTP, so the
    request this process sees says ``http`` — and a connector URL that
    starts with http is refused. The forwarded headers are what the
    client actually asked for.
    """
    proto = (request.headers.get("X-Forwarded-Proto") or "").split(",")[0]
    host = (request.headers.get("X-Forwarded-Host")
            or request.headers.get("Host") or "").split(",")[0]
    proto = proto.strip() or request.url.scheme
    host = host.strip()
    return f"{proto}://{host}" if host else str(request.url.origin())


def connector_url(request: web.Request, token: str) -> str:
    """Where to point Claude.

    The token is IN the path because the connector dialog has one field —
    a URL — and no way to send a header. That is weaker than a header:
    URLs end up in browser history and proxy logs. It is made bearable by
    being per-rig, replaceable at a button press, and useless for moving
    an instrument unless that setup's control switch is also on.
    """
    return f"{public_base(request)}/mcp/{token}"


async def _authenticate(request: web.Request):
    """The token, from the path or a header, → the rig it speaks for."""
    token = (request.match_info.get("token") or "").strip()
    if not token:
        header = (request.headers.get("Authorization") or "").strip()
        token = header[7:].strip() if header[:7].lower() == "bearer " else ""
    if not token:
        token = (request.headers.get("X-Unisweep-Token") or "").strip()
    if not token:
        return None, web.json_response(
            {"error": "missing bearer token"}, status=401)
    rig = await asyncio.to_thread(db.rig_by_connector, token)
    if rig is None:
        return None, web.json_response(
            {"error": "database unavailable"}, status=503)
    if not rig:
        return None, web.json_response(
            {"error": "unknown or revoked connector token"}, status=401)
    return rig, None


async def _relay(rig: dict, name: str, arguments: dict) -> dict:
    """Queue one tool call and wait for the rig to answer it."""
    rig_id = rig["rig_id"]
    command_id = await asyncio.to_thread(
        db.command_add, rig_id, "mcp",
        {"tool": name, "arguments": arguments})
    if command_id is None:
        return _tool_error("the service could not queue the call — its "
                           "database is unavailable")
    future = waiters.awaiting(command_id)
    waiters.wake_rig(rig_id)                 # end the heartbeat's long poll
    try:
        answer = await asyncio.wait_for(future, timeout=CALL_TIMEOUT_S)
    except asyncio.TimeoutError:
        waiters.forget(command_id)
        return _tool_error(
            f"{rig.get('name') or rig_id} did not answer within "
            f"{int(CALL_TIMEOUT_S)} s — it may be offline, or busy with a "
            f"point that takes longer than that")
    except asyncio.CancelledError:
        waiters.forget(command_id)
        raise
    if not isinstance(answer, dict):
        return _tool_result(answer)
    if answer.get("error"):
        return _tool_error(str(answer["error"]))
    return _tool_result(answer.get("result", answer))


async def _dispatch(rig: dict, message: dict) -> Optional[dict]:
    """One JSON-RPC message. None means it was a notification."""
    ident = message.get("id")
    method = message.get("method") or ""
    params = message.get("params") or {}
    if not isinstance(params, dict):
        params = {}

    if method == "initialize":
        wanted = str(params.get("protocolVersion") or "")
        version = wanted if wanted in SUPPORTED_VERSIONS else PROTOCOL_VERSION
        return {"jsonrpc": "2.0", "id": ident, "result": {
            "protocolVersion": version,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": dict(SERVER_INFO,
                               title=f"Unisweep · {rig.get('name') or ''}"
                               .strip(" ·")),
        }}
    if method in ("notifications/initialized", "initialized"):
        return None
    if method == "ping":
        return {"jsonrpc": "2.0", "id": ident, "result": {}}
    if method == "tools/list":
        tools = rig.get("tools") or []
        if isinstance(tools, str):
            try:
                tools = json.loads(tools)
            except ValueError:
                tools = []
        if not tools:
            # the rig has not said hello since this service learned to ask
            return {"jsonrpc": "2.0", "id": ident, "result": {"tools": []}}
        return {"jsonrpc": "2.0", "id": ident, "result": {"tools": tools}}
    if method == "tools/call":
        name = str(params.get("name") or "")
        arguments = params.get("arguments") or {}
        if not isinstance(arguments, dict):
            return {"jsonrpc": "2.0", "id": ident,
                    "result": _tool_error("arguments must be an object")}
        result = await _relay(rig, name, arguments)
        return {"jsonrpc": "2.0", "id": ident, "result": result}
    return _rpc_error(ident, -32601, f"unknown method '{method}'")


@routes.post("/mcp/{token}")
@routes.post("/mcp")
async def mcp(request: web.Request) -> web.Response:
    rig, err = await _authenticate(request)
    if err is not None:
        return err
    try:
        body = await request.json()
    except Exception:                                  # noqa: BLE001
        return web.json_response(_rpc_error(None, -32700, "invalid JSON"))

    if isinstance(body, list):                         # a batch
        out = []
        for message in body:
            if isinstance(message, dict):
                answer = await _dispatch(rig, message)
                if answer is not None:
                    out.append(answer)
        return web.json_response(out) if out else web.Response(status=202)
    if not isinstance(body, dict):
        return web.json_response(
            _rpc_error(None, -32600, "expected a JSON-RPC object"))
    answer = await _dispatch(rig, body)
    if answer is None:
        return web.Response(status=202)
    return web.json_response(answer)


@routes.get("/mcp/{token}")
@routes.get("/mcp")
async def mcp_stream(request: web.Request) -> web.Response:
    """Streamable HTTP allows a client to open a channel for
    server-initiated messages. This service never sends any, so the
    honest answer is that the method is not allowed — clients treat that
    as "no stream" and carry on with POST."""
    return web.Response(status=405, text="this endpoint answers POST only")
