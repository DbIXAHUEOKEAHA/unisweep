"""Getting onto the Tk main loop from somewhere else.

Tk is single-threaded: every widget read and every widget write has to
happen on the thread that created the root window. An assistant arrives on
some other thread — an MCP server's request thread, a socket handler — so
each of its calls is scheduled with ``root.after`` and waited on.

The dangerous case is a **modal dialog**. If a button's command opens
``messagebox.askyesno``, the Tk loop stops inside it until a human clicks,
the waiting caller times out, and the window is left stuck behind a dialog
nobody asked for. That is why every agent-initiated press runs under
:mod:`unisweep.agent.dialogs`, which answers dialogs from a script instead
of showing them. The timeout here is the backstop for the case that slips
through, not the primary defence.
"""

from __future__ import annotations

import threading
from typing import Any, Callable, Optional

__all__ = ["BridgeError", "BridgeTimeout", "TkBridge", "DirectBridge"]

DEFAULT_TIMEOUT = 20.0


class BridgeError(RuntimeError):
    """The GUI could not be reached."""


class BridgeTimeout(BridgeError):
    """The Tk loop did not run the call in time — usually a modal dialog."""


class TkBridge:
    """Runs callables on the Tk main loop and returns their result."""

    def __init__(self, root, timeout: float = DEFAULT_TIMEOUT):
        self.root = root
        self.timeout = float(timeout)
        #: the thread that owns the widgets — the one that built the root
        self.owner_thread = threading.get_ident()
        self._closed = False

    def close(self) -> None:
        self._closed = True

    @property
    def on_ui_thread(self) -> bool:
        return threading.get_ident() == self.owner_thread

    def call(self, fn: Callable[..., Any], *args,
             timeout: Optional[float] = None, **kwargs) -> Any:
        """Run ``fn`` on the UI thread; re-raise whatever it raises."""
        if self._closed:
            raise BridgeError("the Unisweep window has closed")
        if self.on_ui_thread:
            return fn(*args, **kwargs)

        box: dict = {}
        done = threading.Event()

        def runner():
            try:
                box["value"] = fn(*args, **kwargs)
            except BaseException as exc:          # noqa: BLE001
                box["error"] = exc
            finally:
                done.set()

        try:
            self.root.after(0, runner)
        except Exception as exc:                  # noqa: BLE001
            self._closed = True
            raise BridgeError(
                f"the Unisweep window is gone ({type(exc).__name__})") from exc
        if not done.wait(self.timeout if timeout is None else timeout):
            raise BridgeTimeout(
                "the Unisweep window did not respond in time — it is most "
                "likely waiting on a dialog box that needs a human")
        if "error" in box:
            raise box["error"]
        return box.get("value")


class DirectBridge:
    """A bridge that just calls things — for tests and headless use."""

    on_ui_thread = True

    def __init__(self, timeout: float = DEFAULT_TIMEOUT):
        self.timeout = float(timeout)

    def close(self) -> None:
        return

    def call(self, fn: Callable[..., Any], *args,
             timeout: Optional[float] = None, **kwargs) -> Any:
        return fn(*args, **kwargs)
