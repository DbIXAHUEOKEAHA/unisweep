"""The pipe an MCP client launches.

    python -m unisweep.agent.stdio

Connects to the endpoint the running Unisweep wrote into
``config/agent_endpoint.json`` and shuttles bytes between it and
stdin/stdout. It speaks no protocol of its own — everything is handled
inside the application, so there is nothing here to fall out of step.

Options (all optional):

  --core-dir PATH   where config/agent_endpoint.json lives; defaults to
                    the Unisweep folder this file was run from, or
                    $UNISWEEP_HOME
  --host / --port / --token   connect explicitly instead of reading the file
  --wait SECONDS    keep retrying while Unisweep starts up (default 0)
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import threading
import time

from .service import HANDSHAKE_KEY, read_endpoint

DEFAULT_CORE = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))


def _fail(message: str, code: int = 2):
    sys.stderr.write(f"unisweep-mcp: {message}\n")
    sys.stderr.flush()
    raise SystemExit(code)


def connect(host: str, port: int, token: str, wait: float = 0.0):
    """Open the socket and complete the handshake.

    Returns ``(socket, reader, writer)``: a socket has ``__slots__``, so
    the file objects cannot ride along on it and have to be handed back.
    """
    deadline = time.time() + max(wait, 0.0)
    while True:
        try:
            client = socket.create_connection((host, port), timeout=10)
            break
        except OSError as exc:
            if time.time() >= deadline:
                _fail(f"cannot reach Unisweep at {host}:{port} ({exc}). Is "
                      f"the application running with its agent endpoint "
                      f"enabled?")
            time.sleep(0.5)
    client.settimeout(None)
    reader = client.makefile("r", encoding="utf-8", newline="\n")
    writer = client.makefile("w", encoding="utf-8", newline="\n")
    writer.write(json.dumps({HANDSHAKE_KEY: token}) + "\n")
    writer.flush()
    reply = reader.readline()
    try:
        ok = json.loads(reply).get("unisweep") == "ok"
    except (ValueError, AttributeError):
        ok = False
    if not ok:
        _fail("Unisweep refused the token — re-read "
              "config/agent_endpoint.json (it changes when the endpoint "
              "restarts)")
    return client, reader, writer


def pump(client: socket.socket, reader, writer) -> int:
    """stdin -> socket and socket -> stdout, until either side closes."""
    done = threading.Event()

    def downstream():
        try:
            for line in reader:
                sys.stdout.write(line)
                sys.stdout.flush()
        except (OSError, ValueError):
            pass
        finally:
            done.set()

    threading.Thread(target=downstream, daemon=True).start()
    try:
        for line in sys.stdin:
            if done.is_set():
                break
            writer.write(line)
            writer.flush()
    except (OSError, ValueError):
        pass
    finally:
        try:
            client.shutdown(socket.SHUT_WR)
        except OSError:
            pass
        done.wait(2.0)
        try:
            client.close()
        except OSError:
            pass
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="unisweep-mcp",
        description="MCP stdio pipe to a running Unisweep.")
    parser.add_argument("--core-dir", default=os.environ.get(
        "UNISWEEP_HOME", DEFAULT_CORE))
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    parser.add_argument("--token")
    parser.add_argument("--wait", type=float, default=0.0,
                        help="seconds to keep retrying the connection")
    args = parser.parse_args(argv)

    host, port, token = args.host, args.port, args.token
    if not (host and port and token):
        endpoint = read_endpoint(args.core_dir)
        if endpoint is None:
            _fail(f"no agent endpoint in {args.core_dir}/config — start "
                  f"Unisweep and enable the agent endpoint on the Settings "
                  f"page (or pass --host/--port/--token)")
        host = host or endpoint.get("host", "127.0.0.1")
        port = port or int(endpoint.get("port", 0))
        token = token or endpoint.get("token", "")
    return pump(*connect(host, int(port), token, wait=args.wait))


if __name__ == "__main__":
    raise SystemExit(main())
