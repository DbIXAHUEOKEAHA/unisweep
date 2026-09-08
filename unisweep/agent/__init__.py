"""The agent-facing surface of Unisweep.

Everything an automation assistant can see or do goes through this package.
It is deliberately transport-agnostic: :mod:`session` is a plain Python
facade, and :mod:`server` is a thin MCP adapter over it, so the same
surface can later be served over a socket by a Unisweep daemon without the
facade changing.
"""

from .bridge import BridgeError, BridgeTimeout, TkBridge
from .controls import Control, ControlRegistry, UnknownControl

__all__ = ["BridgeError", "BridgeTimeout", "TkBridge",
           "Control", "ControlRegistry", "UnknownControl"]
