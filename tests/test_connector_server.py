"""The connector endpoint, with a rig on the other end of the relay.

Claude posts a tool call to a public URL; the rig is behind a lab
firewall and only ever talks outbound. What is under test is that those
two meet: the call is queued, the heartbeat collects it, the answer comes
back on the same HTTPS request the assistant is still holding.

No Postgres: the database layer's contract is small and faked here, which
is how the rest of the service's tests work too.
"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server"))
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "0:test")
os.environ.setdefault("DATABASE_URL", "postgresql://test/test")

import pytest

aiohttp = pytest.importorskip("aiohttp")
from aiohttp.test_utils import TestClient, TestServer          # noqa: E402
from aiohttp import web                                        # noqa: E402

from unisweep_bot import connector, db, waiters                # noqa: E402


TOOLS = [{"name": "describe_rig", "description": "the rig",
          "inputSchema": {"type": "object", "properties": {}}},
         {"name": "set_parameter", "description": "move something",
          "inputSchema": {"type": "object", "properties": {}}}]


class FakeDB:
    """Only what the connector touches."""

    def __init__(self):
        self.rigs = {"rig-1": {"rig_id": "rig-1", "name": "bench 3",
                               "connector_hash": db.token_hash("s3cret"),
                               "tools": TOOLS}}
        self.queue = []
        self.finished = {}
        self.next_id = 100
        self.down = False

    def rig_by_connector(self, token):
        if self.down:
            return None
        rig_id, _, secret = (token or "").partition(".")
        rig = self.rigs.get(rig_id)
        if not rig or not db.token_matches(
                secret, rig.get("connector_hash") or ""):
            return {}
        return rig

    def command_add(self, rig_id, kind, args=None, chat_id=None):
        if self.down:
            return None
        self.next_id += 1
        self.queue.append({"id": self.next_id, "rig_id": rig_id,
                           "kind": kind, "args": args or {}})
        return self.next_id

    def commands_take(self, rig_id, limit=10):
        taken, self.queue = self.queue, []
        return taken

    def command_finish(self, command_id, payload):
        self.finished[int(command_id)] = payload
        return True


@pytest.fixture
def fake_db(monkeypatch):
    fake = FakeDB()
    for name in ("rig_by_connector", "command_add", "commands_take",
                 "command_finish"):
        monkeypatch.setattr(connector.db, name, getattr(fake, name))
    return fake


def serve(fake):
    app = web.Application()
    app.add_routes(connector.routes)
    return app


async def client_for(app):
    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()
    return client


def call(client, payload, token="rig-1.s3cret"):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return client.post("/mcp", json=payload, headers=headers)


def run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
def test_a_token_is_required_and_a_wrong_one_is_refused(fake_db):
    async def scenario():
        client = await client_for(serve(fake_db))
        try:
            no_token = await client.post("/mcp", json={"jsonrpc": "2.0",
                                                       "id": 1,
                                                       "method": "ping"})
            bad = await call(client, {"jsonrpc": "2.0", "id": 1,
                                      "method": "ping"}, token="rig-1.nope")
            unknown = await call(client, {"jsonrpc": "2.0", "id": 1,
                                          "method": "ping"},
                                 token="rig-9.s3cret")
            return no_token.status, bad.status, unknown.status
        finally:
            await client.close()
    assert run(scenario()) == (401, 401, 401)


def test_a_database_outage_is_not_reported_as_a_bad_credential(fake_db):
    """Sending somebody hunting for a token that is perfectly good is a
    cruel way to spend an afternoon."""
    fake_db.down = True

    async def scenario():
        client = await client_for(serve(fake_db))
        try:
            reply = await call(client, {"jsonrpc": "2.0", "id": 1,
                                        "method": "ping"})
            return reply.status
        finally:
            await client.close()
    assert run(scenario()) == 503


def test_the_handshake_names_the_rig(fake_db):
    async def scenario():
        client = await client_for(serve(fake_db))
        try:
            reply = await call(client, {
                "jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {"protocolVersion": "2025-06-18"}})
            return await reply.json()
        finally:
            await client.close()
    result = run(scenario())["result"]
    assert result["protocolVersion"] == "2025-06-18"
    assert result["capabilities"]["tools"] is not None
    assert "bench 3" in result["serverInfo"]["title"]


def test_the_tool_list_is_the_rigs_own(fake_db):
    """Not a copy kept on the server: a setup running an older Unisweep
    advertises exactly what it has, and this service cannot drift."""
    async def scenario():
        client = await client_for(serve(fake_db))
        try:
            reply = await call(client, {"jsonrpc": "2.0", "id": 2,
                                        "method": "tools/list"})
            return await reply.json()
        finally:
            await client.close()
    tools = run(scenario())["result"]["tools"]
    assert [t["name"] for t in tools] == ["describe_rig", "set_parameter"]


def test_a_call_is_relayed_to_the_rig_and_answered(fake_db):
    """The whole point: Claude holds one HTTPS request while the rig,
    which nothing can reach into, collects the call on its heartbeat and
    posts the answer back."""
    async def scenario():
        client = await client_for(serve(fake_db))
        try:
            async def be_the_rig():
                for _ in range(200):               # the heartbeat loop
                    taken = fake_db.commands_take("rig-1")
                    if taken:
                        command = taken[0]
                        assert command["kind"] == "mcp"
                        assert command["args"]["tool"] == "describe_rig"
                        waiters.resolve(command["id"], {
                            "ok": True,
                            "result": {"lab": "2D materials",
                                       "sample": {"id": "GR-1"}}})
                        return
                    await asyncio.sleep(0.01)

            rig = asyncio.ensure_future(be_the_rig())
            reply = await call(client, {
                "jsonrpc": "2.0", "id": 3, "method": "tools/call",
                "params": {"name": "describe_rig", "arguments": {}}})
            body = await reply.json()
            await rig
            return body
        finally:
            await client.close()

    result = run(scenario())["result"]
    assert result["isError"] is False
    assert result["structuredContent"]["lab"] == "2D materials"
    assert "2D materials" in result["content"][0]["text"]


def test_a_rig_that_refuses_says_why(fake_db):
    async def scenario():
        client = await client_for(serve(fake_db))
        try:
            async def be_the_rig():
                for _ in range(200):
                    taken = fake_db.commands_take("rig-1")
                    if taken:
                        waiters.resolve(taken[0]["id"], {
                            "ok": False,
                            "error": "moving instruments from the bot is "
                                     "switched off for this setup"})
                        return
                    await asyncio.sleep(0.01)

            rig = asyncio.ensure_future(be_the_rig())
            reply = await call(client, {
                "jsonrpc": "2.0", "id": 4, "method": "tools/call",
                "params": {"name": "set_parameter",
                           "arguments": {"address": "GATE", "value": 1.0}}})
            body = await reply.json()
            await rig
            return body
        finally:
            await client.close()

    result = run(scenario())["result"]
    assert result["isError"] is True
    assert "switched off" in result["content"][0]["text"]


def test_a_silent_rig_times_out_with_an_explanation(fake_db, monkeypatch):
    """An assistant told the setup is not answering can do something
    about it; one that hangs cannot."""
    monkeypatch.setattr(connector, "CALL_TIMEOUT_S", 0.2)

    async def scenario():
        client = await client_for(serve(fake_db))
        try:
            reply = await call(client, {
                "jsonrpc": "2.0", "id": 5, "method": "tools/call",
                "params": {"name": "describe_rig", "arguments": {}}})
            return await reply.json()
        finally:
            await client.close()

    result = run(scenario())["result"]
    assert result["isError"] is True
    assert "did not answer" in result["content"][0]["text"]
    assert "bench 3" in result["content"][0]["text"]
    assert waiters.pending_count() == 0, "a timed-out call is cleaned up"


def test_a_notification_gets_no_answer(fake_db):
    async def scenario():
        client = await client_for(serve(fake_db))
        try:
            reply = await call(client, {"jsonrpc": "2.0",
                                        "method": "notifications/initialized"})
            return reply.status
        finally:
            await client.close()
    assert run(scenario()) == 202


def test_an_unknown_method_is_a_protocol_error_not_a_crash(fake_db):
    async def scenario():
        client = await client_for(serve(fake_db))
        try:
            reply = await call(client, {"jsonrpc": "2.0", "id": 6,
                                        "method": "resources/list"})
            return await reply.json()
        finally:
            await client.close()
    assert run(scenario())["error"]["code"] == -32601
