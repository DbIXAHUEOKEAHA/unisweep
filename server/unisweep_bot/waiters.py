"""Waiting for a rig to answer.

A tool call arrives over HTTPS and has to be answered on the same
request, but the rig is behind a lab firewall and only ever talks
outbound. So the call is queued as a command, the request waits here, and
the rig's ``/api/v1/result`` post resolves it.

Two things live in this module, and both are deliberately in-process:

* :func:`awaiting` — one future per queued command;
* :func:`rig_gate` — one event per rig, so a heartbeat with nothing to do
  can sleep until there is something rather than returning empty and
  making the next call wait for the next beat.

In-process means **one service instance**. That is true on Railway today
and it is the first thing to revisit if the service is ever scaled out;
the fix is a LISTEN/NOTIFY on the same Postgres, not a rewrite, because
the queue itself is already in the database.
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional

__all__ = ["awaiting", "resolve", "forget", "rig_gate", "wake_rig",
           "wait_for_work", "pending_count"]

_results: dict = {}
_gates: dict = {}


def awaiting(command_id: int) -> "asyncio.Future":
    """A future for this command's result, created on first ask."""
    loop = asyncio.get_running_loop()
    future = _results.get(int(command_id))
    if future is None or future.done():
        future = loop.create_future()
        _results[int(command_id)] = future
    return future


def resolve(command_id: int, payload: Any) -> bool:
    """The rig answered. Returns False when nobody was waiting — which is
    the ordinary case for a Telegram button press."""
    future = _results.pop(int(command_id), None)
    if future is None or future.done():
        return False
    future.set_result(payload)
    return True


def forget(command_id: int) -> None:
    """Give up on a command — a timeout, or a caller that went away."""
    future = _results.pop(int(command_id), None)
    if future is not None and not future.done():
        future.cancel()


def pending_count() -> int:
    return len(_results)


def rig_gate(rig_id: str) -> asyncio.Event:
    gate = _gates.get(rig_id)
    if gate is None:
        gate = _gates[rig_id] = asyncio.Event()
    return gate


def wake_rig(rig_id: str) -> None:
    """Something is queued for this rig: end its long poll now."""
    rig_gate(rig_id).set()


async def wait_for_work(rig_id: str, seconds: float) -> bool:
    """Hold a heartbeat open until there is something to send.

    Returns True if woken by work, False on timeout. The gate is cleared
    before waiting, so a wake that arrives while the rig was away is not
    lost — it simply returns at once on the next poll.
    """
    gate = rig_gate(rig_id)
    if gate.is_set():
        gate.clear()
        return True
    try:
        await asyncio.wait_for(gate.wait(), timeout=max(float(seconds), 0.0))
    except asyncio.TimeoutError:
        return False
    gate.clear()
    return True
