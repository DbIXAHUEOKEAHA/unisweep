"""The MCP endpoint, over a real socket.

These talk to the service the way a desktop client does: handshake, then
newline-delimited JSON-RPC. Nothing is stubbed below the session — the
sweeps here really run, on mock instruments, through the same engine.
"""

import json
import os
import socket
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from unisweep.agent.protocol import PROTOCOL_VERSION, TOOLS
from unisweep.agent.bridge import DirectBridge
from unisweep.agent.service import AgentService, new_token, read_endpoint
from unisweep.agent.session import AgentSession
from unisweep.core.labprofile import LabProfile
from tests.test_agent import FakeApp
from tests.test_safety import GATE_PROFILE, LeakyGate


class MCPClient:
    """A minimal MCP client: exactly what the wire needs, nothing more."""

    def __init__(self, host, port, token):
        self.sock = socket.create_connection((host, port), timeout=10)
        self.reader = self.sock.makefile("r", encoding="utf-8", newline="\n")
        self.writer = self.sock.makefile("w", encoding="utf-8", newline="\n")
        self._send({"unisweep_token": token})
        self.handshake = json.loads(self.reader.readline())
        self._id = 0

    def _send(self, payload):
        self.writer.write(json.dumps(payload) + "\n")
        self.writer.flush()

    def request(self, method, params=None):
        self._id += 1
        self._send({"jsonrpc": "2.0", "id": self._id, "method": method,
                    "params": params or {}})
        return json.loads(self.reader.readline())

    def notify(self, method, params=None):
        self._send({"jsonrpc": "2.0", "method": method,
                    "params": params or {}})

    def raw(self, text):
        self.writer.write(text + "\n")
        self.writer.flush()
        return json.loads(self.reader.readline())

    def initialize(self, version=PROTOCOL_VERSION):
        response = self.request("initialize", {
            "protocolVersion": version, "capabilities": {},
            "clientInfo": {"name": "pytest", "version": "1"}})
        self.notify("notifications/initialized")
        return response

    def call(self, tool, **arguments):
        response = self.request("tools/call",
                                {"name": tool, "arguments": arguments})
        assert "result" in response, response
        return response["result"]

    def data(self, tool, **arguments):
        result = self.call(tool, **arguments)
        assert not result.get("isError"), result["content"][0]["text"]
        return result["structuredContent"]

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


@pytest.fixture
def endpoint():
    tmp = tempfile.mkdtemp(prefix="unisweep_mcp_")
    app = FakeApp(tmp, {"GATE": LeakyGate()},
                  LabProfile.from_dict(GATE_PROFILE))
    # the fake app has no Tk loop to marshal onto, so calls run on the
    # service's own client thread; TkBridge marshalling is covered in
    # tests/test_agent.py
    service = AgentService(AgentSession(app, bridge=DirectBridge()), tmp,
                           token=new_token())
    service.start_listening()
    yield service, app, tmp
    service.stop()
    app.close()


def connect(service):
    return MCPClient("127.0.0.1", service.port, service.token)


# ---------------------------------------------------------------------------
# the endpoint itself
# ---------------------------------------------------------------------------
def test_the_endpoint_file_carries_the_port_and_token(endpoint):
    service, _, core_dir = endpoint
    written = read_endpoint(core_dir)
    assert written["port"] == service.port
    assert written["token"] == service.token
    assert written["host"] == "127.0.0.1"
    assert written["pid"] == os.getpid()
    service.stop()
    assert read_endpoint(core_dir) is None      # cleaned up on stop


def test_a_wrong_token_is_refused(endpoint):
    service, _, _ = endpoint
    client = MCPClient("127.0.0.1", service.port, "not-the-token")
    assert client.handshake == {"unisweep": "unauthorised"}
    client.close()


def test_initialize_negotiates_and_introduces_itself(endpoint):
    service, _, _ = endpoint
    client = connect(endpoint[0])
    assert client.handshake == {"unisweep": "ok"}
    result = client.initialize()["result"]
    assert result["serverInfo"]["name"] == "unisweep"
    assert result["protocolVersion"] == PROTOCOL_VERSION
    assert "tools" in result["capabilities"]
    assert "describe_rig" in result["instructions"]
    # an older client keeps its own version
    other = connect(service)
    assert other.initialize("2024-11-05")["result"]["protocolVersion"] == \
        "2024-11-05"
    client.close()
    other.close()


def test_every_tool_is_advertised_with_a_usable_schema(endpoint):
    client = connect(endpoint[0])
    client.initialize()
    tools = client.request("tools/list")["result"]["tools"]
    assert len(tools) == len(TOOLS)
    names = {t["name"] for t in tools}
    assert {"describe_rig", "dry_run", "run_sweep", "press",
            "set_controls", "status"} <= names
    for tool in tools:
        assert "method" not in tool          # internal, never on the wire
        assert tool["description"].strip()
        assert tool["inputSchema"]["type"] == "object"
    by_name = {t["name"]: t for t in tools}
    assert by_name["run_sweep"]["annotations"]["destructiveHint"] is True
    assert by_name["status"]["annotations"]["readOnlyHint"] is True
    client.close()


def test_protocol_errors_are_reported_as_json_rpc(endpoint):
    client = connect(endpoint[0])
    client.initialize()
    assert client.raw("{not json")["error"]["code"] == -32700
    assert client.request("no/such/method")["error"]["code"] == -32601
    client.close()


def test_notifications_get_no_reply(endpoint):
    """A reply to a notification would desynchronise the stream."""
    client = connect(endpoint[0])
    client.initialize()
    client.notify("notifications/cancelled", {"requestId": 1})
    assert client.request("ping")["result"] == {}
    client.close()


# ---------------------------------------------------------------------------
# the tools
# ---------------------------------------------------------------------------
def test_describe_rig_arrives_as_text_and_structure(endpoint):
    client = connect(endpoint[0])
    client.initialize()
    result = client.call("describe_rig")
    assert result["isError"] is False
    assert "Vbg" in result["content"][0]["text"]
    described = result["structuredContent"]
    assert described["has_profile"] is True
    assert described["instruments"][0]["address"] == "GATE"
    client.close()


def test_a_bad_tool_name_or_argument_comes_back_as_a_tool_error(endpoint):
    client = connect(endpoint[0])
    client.initialize()
    missing = client.call("no_such_tool")
    assert missing["isError"] is True
    assert "no tool called" in missing["content"][0]["text"]
    wrong = client.call("read_channels", nonsense=1)
    assert wrong["isError"] is True
    client.close()


def test_filling_in_a_field_over_mcp_shows_up_in_the_gui(endpoint):
    service, app, _ = endpoint
    client = connect(service)
    client.initialize()
    client.data("set_controls", values={"sweep.axis1.stop": 3.5,
                                        "sweep.filename": "mcp_run"})
    assert app.pages["Sweep"].axis_cards[0].stop.value() == 3.5
    assert app.pages["Sweep"].filename.value() == "mcp_run"
    read = client.data("read_controls", names=["sweep.axis1.stop"])
    assert read["sweep.axis1.stop"] == 3.5
    client.close()


def test_a_refused_limit_reaches_the_client_with_its_reason(endpoint):
    client = connect(endpoint[0])
    client.initialize()
    result = client.call("set_parameter", address="Vbg", value=40.0)
    assert result["isError"] is True
    assert "outside the allowed range" in result["content"][0]["text"]
    assert endpoint[1].registry._mocks["GATE"].set_log == []
    client.close()


def test_dry_run_then_run_sweep_over_the_wire(endpoint):
    service, app, _ = endpoint
    client = connect(service)
    client.initialize()
    program = {"axes": [{"device": "GATE", "parameter": "Volt",
                         "start": 0.0, "stop": 1.0, "rate": 0.25,
                         "delay": 0.005, "count_mode": "step"}],
               "reads": ["GATE.Leak"]}
    preview = client.data("dry_run", program=program)
    assert preview["ok"] is True
    assert preview["planned_points"] == 5
    assert app.registry._mocks["GATE"].set_log == []      # nothing moved

    started = client.data("run_sweep", program=program)
    assert started["started"] is True
    app.wait_idle()
    status = client.data("status")
    assert status["state"] == "finished"
    assert status["finished"]["points"] == 5
    events = client.data("events", since=0, kinds=["SweepStarted",
                                                   "SweepFinished"])
    assert [e["event"] for e in events["events"]] == ["SweepStarted",
                                                      "SweepFinished"]
    client.close()


def test_a_forbidden_sweep_is_refused_before_anything_moves(endpoint):
    service, app, _ = endpoint
    client = connect(service)
    client.initialize()
    result = client.data("run_sweep", program={
        "axes": [{"device": "GATE", "parameter": "Volt", "start": 0.0,
                  "stop": 40.0, "rate": 1.0, "delay": 0.01,
                  "count_mode": "step"}],
        "reads": ["GATE.Leak"]})
    assert result["started"] is False
    assert "outside the allowed range" in result["reason"]
    assert app.registry._mocks["GATE"].set_log == []
    client.close()


def test_a_dialog_the_gui_raises_comes_back_through_mcp(endpoint):
    service, app, _ = endpoint
    app.start_warning = True
    client = connect(service)
    client.initialize()
    client.data("apply_program", program={
        "axes": [{"device": "GATE", "parameter": "Volt", "start": 0.0,
                  "stop": 1.0, "rate": 0.5, "delay": 0.005,
                  "count_mode": "step"}],
        "reads": ["GATE.Leak"]})
    unanswered = client.data("press", name="sweep.start")
    assert unanswered["ok"] is False
    assert "Go to start?" in unanswered["needs_answer"]["message"]
    answered = client.data("press", name="sweep.start", answers=["yes"])
    assert answered["ok"] is True
    app.wait_idle()
    client.close()


def test_two_clients_can_be_connected_at_once(endpoint):
    service, _, _ = endpoint
    first, second = connect(service), connect(service)
    first.initialize()
    second.initialize()
    first.data("set_controls", values={"sweep.filename": "from_first"})
    assert second.data("read_controls",
                       names=["sweep.filename"])["sweep.filename"] == \
        "from_first"
    assert service.clients == 2
    first.close()
    second.close()


# ---------------------------------------------------------------------------
# the stdio pipe a desktop client actually launches
# ---------------------------------------------------------------------------
def test_the_stdio_pipe_carries_a_real_session(endpoint):
    service, _, core_dir = endpoint
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    process = subprocess.Popen(
        [sys.executable, "-m", "unisweep.agent.stdio",
         "--core-dir", core_dir],
        cwd=repo, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, bufsize=1)
    try:
        process.stdin.write(json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": PROTOCOL_VERSION,
                       "capabilities": {},
                       "clientInfo": {"name": "pipe", "version": "1"}}
        }) + "\n")
        process.stdin.flush()
        response = json.loads(process.stdout.readline())
        assert response["result"]["serverInfo"]["name"] == "unisweep"

        process.stdin.write(json.dumps({
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": "describe_rig", "arguments": {}}}) + "\n")
        process.stdin.flush()
        described = json.loads(process.stdout.readline())
        assert described["result"]["structuredContent"]["has_profile"] is True
    finally:
        process.stdin.close()
        process.wait(timeout=10)


def test_the_pipe_explains_itself_when_unisweep_is_not_running():
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    empty = tempfile.mkdtemp(prefix="unisweep_noendpoint_")
    process = subprocess.run(
        [sys.executable, "-m", "unisweep.agent.stdio", "--core-dir", empty],
        cwd=repo, capture_output=True, text=True, timeout=30)
    assert process.returncode != 0
    assert "no agent endpoint" in process.stderr
    assert "Settings page" in process.stderr


def test_the_client_config_is_pasteable_as_it_stands():
    """The bare command is not enough to hand someone.

    ``python -m unisweep.agent.stdio`` needs the application's folder on
    sys.path, and an MCP client launches the pipe from its OWN working
    directory — so pasting just the command gets "No module named
    'unisweep'" and an hour of confusion. The config carries the cwd that
    makes it work, and a --wait so the client may start first.
    """
    import json
    import sys as _sys
    import types

    from unisweep.gui.app import App

    core = "/some/where/unisweep"
    stub = types.SimpleNamespace(core_dir=core)
    text = App.agent_client_config(stub)
    entry = json.loads(text)["mcpServers"]["unisweep"]

    assert entry["command"] == _sys.executable
    assert core in entry["args"], "the endpoint file is found by core dir"
    assert "--wait" in entry["args"], \
        "a client that starts before Unisweep must retry, not fail"
    assert App.agent_command(stub).startswith('"')

    # three independent ways to find the package, because clients differ
    # in which they honour -- Claude Desktop drops cwd, and with only cwd
    # the server dies at startup with ModuleNotFoundError
    import os as _os
    assert entry["args"][0] == _os.path.join(core, "mcp_stdio.py"), \
        "a script finds its own folder; -m has to be told where to look"
    assert entry["cwd"] == core
    assert entry["env"]["PYTHONPATH"] == core, \
        "the fallback for a client that also drops the script's folder"


def test_launcher_script_imports_without_cwd_or_pythonpath(tmp_path):
    """The launcher must work from a directory that knows nothing.

    This is the failure Claude Desktop produced: it launches the server
    from its own working directory and ignores the entry's ``cwd``, so
    ``python -m unisweep.agent.stdio`` cannot see the package and the
    server exits before the handshake. Run the real launcher in a clean
    process, from an unrelated cwd, with PYTHONPATH scrubbed -- if the
    path bootstrap is missing this fails with ModuleNotFoundError.
    """
    import os
    import subprocess
    import sys

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    launcher = os.path.join(root, "mcp_stdio.py")
    assert os.path.exists(launcher), "the config points clients at this file"

    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    # no endpoint file in an empty core dir: reaching that complaint means
    # the import worked, which is the whole point of the test
    proc = subprocess.run(
        [sys.executable, launcher, "--core-dir", str(tmp_path)],
        cwd=str(tmp_path), env=env, capture_output=True, text=True,
        timeout=60)

    assert "No module named" not in proc.stderr, proc.stderr
    assert "no agent endpoint" in proc.stderr, \
        f"expected the endpoint complaint, got: {proc.stderr!r}"
