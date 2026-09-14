"""Launcher for the MCP stdio pipe, safe to start from anywhere.

    python "<unisweep folder>/mcp_stdio.py"

``python -m unisweep.agent.stdio`` only resolves when the application
folder is on ``sys.path``, which in practice means trusting the client to
honour the ``cwd`` of its server entry. Claude Desktop does not, and the
result is a server that dies at startup with

    ModuleNotFoundError: No module named 'unisweep'

A script knows where it lives, so this one puts its own folder on the
path before importing anything and works whatever directory the client
launches it from, with or without ``cwd`` and ``PYTHONPATH``.
"""

from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from unisweep.agent.stdio import main  # noqa: E402  (needs the path first)

if __name__ == "__main__":
    raise SystemExit(main())
