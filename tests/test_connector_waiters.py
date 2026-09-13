"""The rendezvous between a tool call and the rig that answers it."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server"))
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "0:test")
os.environ.setdefault("DATABASE_URL", "postgresql://test/test")

import pytest

from unisweep_bot import waiters


def run(coro):
    return asyncio.run(coro)


def test_a_call_waits_until_the_rig_answers():
    async def scenario():
        future = waiters.awaiting(7)
        asyncio.get_running_loop().call_later(
            0.05, lambda: waiters.resolve(7, {"ok": True, "detail": "done"}))
        return await asyncio.wait_for(future, timeout=2)
    assert run(scenario())["detail"] == "done"
    assert waiters.pending_count() == 0, "the future is not left behind"


def test_an_answer_nobody_waited_for_is_not_an_error():
    """Every Telegram button press takes this path."""
    async def scenario():
        return waiters.resolve(999, {"ok": True})
    assert run(scenario()) is False


def test_a_caller_that_gives_up_leaves_nothing_behind():
    async def scenario():
        waiters.awaiting(11)
        waiters.forget(11)
        return waiters.pending_count()
    assert run(scenario()) == 0


def test_a_heartbeat_sleeps_until_there_is_work():
    async def scenario():
        loop = asyncio.get_running_loop()
        loop.call_later(0.05, waiters.wake_rig, "rig-a")
        started = loop.time()
        woken = await waiters.wait_for_work("rig-a", 5.0)
        return woken, loop.time() - started
    woken, elapsed = run(scenario())
    assert woken is True
    assert elapsed < 1.0, "it waited for the timeout instead of the wake"


def test_a_quiet_heartbeat_returns_on_its_own():
    async def scenario():
        return await waiters.wait_for_work("rig-quiet", 0.05)
    assert run(scenario()) is False


def test_work_queued_while_the_rig_was_away_is_not_lost():
    """The wake happens between two polls: the next one must return at
    once rather than sleeping through work that is already waiting."""
    async def scenario():
        waiters.wake_rig("rig-b")
        return await waiters.wait_for_work("rig-b", 5.0)
    assert run(scenario()) is True


def test_rigs_do_not_wake_each_other():
    async def scenario():
        waiters.wake_rig("rig-one")
        return await waiters.wait_for_work("rig-two", 0.05)
    assert run(scenario()) is False
