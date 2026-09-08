"""The agent endpoint, living inside the running Unisweep.

Hardware has one owner. The GUI holds the VISA sessions, so the agent
endpoint lives in that same process rather than in a second one that would
fight it for the instruments — this is the "MCP server inside the app"
topology, and it is why an assistant and a person can drive the same sweep
and see each other's changes.

A desktop MCP client, though, launches a *subprocess* and talks to it over
stdin/stdout. So the split is:

    MCP client ──stdio──▶ unisweep.agent.stdio ──socket──▶ this service
                          (a dumb pipe)              (inside the GUI)

The protocol is spoken here, not in the pipe, so there is one
implementation and the pipe cannot get out of step with it.

The listener binds to loopback only and requires a token, which is written
to ``config/agent_endpoint.json`` alongside the port. That file is how the
pipe finds the service, and its permissions are the security boundary:
anything that can read it could already read the data files.
"""

from __future__ import annotations

import json
import os
import secrets
import socket
import threading
from typing import Callable, Optional

from .protocol import MCPHandler

__all__ = ["AgentService", "endpoint_path", "read_endpoint", "new_token"]

ENDPOINT_FILE = "agent_endpoint.json"
HANDSHAKE_KEY = "unisweep_token"


def endpoint_path(core_dir: str) -> str:
    return os.path.join(core_dir, "config", ENDPOINT_FILE)


def read_endpoint(core_dir: str) -> Optional[dict]:
    try:
        with open(endpoint_path(core_dir), "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def new_token() -> str:
    return secrets.token_urlsafe(24)


class AgentService(threading.Thread):
    """Loopback JSON-RPC listener handing each client an MCP handler."""

    def __init__(self, session, core_dir: str, host: str = "127.0.0.1",
                 port: int = 0, token: str = "",
                 log: Optional[Callable[[str], None]] = None):
        super().__init__(daemon=True, name="unisweep-agent-service")
        self.session = session
        self.core_dir = core_dir
        self.host = host
        self.requested_port = int(port or 0)
        self.token = token or new_token()
        self.log = log or (lambda _line: None)
        self.port = 0
        self._server: Optional[socket.socket] = None
        self._stop = threading.Event()
        self._clients = 0
        self._lock = threading.Lock()
        self.error = ""

    # ---- lifecycle ---------------------------------------------------
    def start_listening(self) -> int:
        """Bind before the thread starts, so the caller learns the port
        (and any bind failure) synchronously."""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.host, self.requested_port))
        server.listen(8)
        server.settimeout(0.5)
        self._server = server
        self.port = server.getsockname()[1]
        self._write_endpoint()
        self.start()
        self.log(f"agent endpoint listening on {self.host}:{self.port}")
        return self.port

    def stop(self) -> None:
        self._stop.set()
        server, self._server = self._server, None
        if server is not None:
            try:
                server.close()
            except OSError:
                pass
        self._remove_endpoint()

    @property
    def running(self) -> bool:
        return self._server is not None and not self._stop.is_set()

    @property
    def clients(self) -> int:
        with self._lock:
            return self._clients

    # ---- endpoint file -----------------------------------------------
    def _write_endpoint(self) -> None:
        path = endpoint_path(self.core_dir)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = {"host": self.host, "port": self.port, "token": self.token,
                "pid": os.getpid()}
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        try:                                       # POSIX: owner-only
            os.chmod(path, 0o600)
        except OSError:
            pass

    def _remove_endpoint(self) -> None:
        try:
            os.remove(endpoint_path(self.core_dir))
        except OSError:
            pass

    # ---- serving -----------------------------------------------------
    def run(self) -> None:
        while not self._stop.is_set():
            server = self._server
            if server is None:
                break
            try:
                client, address = server.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            threading.Thread(target=self._serve, args=(client, address),
                             daemon=True,
                             name="unisweep-agent-client").start()

    def _serve(self, client: socket.socket, address) -> None:
        with self._lock:
            self._clients += 1
        handler = MCPHandler(self.session, log=self.log)
        try:
            reader = client.makefile("r", encoding="utf-8", newline="\n")
            writer = client.makefile("w", encoding="utf-8", newline="\n")
            if not self._handshake(reader, writer):
                self.log(f"agent client {address} rejected: bad token")
                return
            for line in reader:
                if self._stop.is_set():
                    break
                response = handler.handle_line(line)
                if response is None:
                    continue
                writer.write(response + "\n")
                writer.flush()
        except (OSError, ValueError) as exc:
            self.log(f"agent client {address} dropped: {exc}")
        finally:
            with self._lock:
                self._clients -= 1
            try:
                client.close()
            except OSError:
                pass

    def _handshake(self, reader, writer) -> bool:
        line = reader.readline()
        if not line:
            return False
        try:
            offered = json.loads(line).get(HANDSHAKE_KEY, "")
        except ValueError:
            return False
        import hmac
        ok = hmac.compare_digest(str(offered), self.token)
        writer.write(json.dumps(
            {"unisweep": "ok" if ok else "unauthorised"}) + "\n")
        writer.flush()
        return ok
