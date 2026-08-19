"""Telegram notifier tests — HTTP layer mocked (wire format asserted
against the documented Bot API sendMessage contract)."""

import io
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unisweep.core.notify import TelegramNotifier, compose_sweep_message


class _Resp(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): return False


def test_compose_messages():
    m = compose_sweep_message(False, 5025, 4512, "260817-2.csv")
    assert m == "✅ Unisweep: sweep finished — duration 1 h 23 m — " \
                "4512 points — 260817-2.csv", m
    m = compose_sweep_message(True, 61, 10, detail="MAGNET.Volt: NaN")
    assert m.startswith("⛔ Unisweep: sweep STOPPED — duration 1 m 01 s "
                        "— 10 points"), m
    assert m.endswith("\nMAGNET.Volt: NaN")
    assert compose_sweep_message(False, 9, 3).endswith("9 s — 3 points")


def test_send_posts_documented_payload(monkey=None):
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["body"] = json.loads(req.data.decode())
        captured["timeout"] = timeout
        return _Resp(json.dumps({"ok": True}).encode())

    orig = urllib.request.urlopen
    urllib.request.urlopen = fake_urlopen
    try:
        ok, detail = TelegramNotifier("123:ABC", "42").send("hello lab")
    finally:
        urllib.request.urlopen = orig
    assert ok and "sent" in detail
    assert captured["url"] == \
        "https://api.telegram.org/bot123:ABC/sendMessage"
    assert captured["body"] == {"chat_id": "42", "text": "hello lab"}
    assert captured["timeout"] == 10.0


def test_send_failures_never_raise():
    def dead(req, timeout=None):
        raise OSError("no route to host")
    orig = urllib.request.urlopen
    urllib.request.urlopen = dead
    try:
        ok, detail = TelegramNotifier("t", "c").send("x")
    finally:
        urllib.request.urlopen = orig
    assert not ok and "OSError" in detail
    ok, detail = TelegramNotifier("", "").send("x")
    assert not ok and "missing" in detail


def test_api_refusal_reported():
    def refused(req, timeout=None):
        return _Resp(json.dumps({"ok": False,
                                 "description": "chat not found"}).encode())
    orig = urllib.request.urlopen
    urllib.request.urlopen = refused
    try:
        ok, detail = TelegramNotifier("t", "c").send("x")
    finally:
        urllib.request.urlopen = orig
    assert not ok and "refused" in detail


if __name__ == "__main__":
    passed = failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
                passed += 1
            except Exception:
                import traceback
                print(f"FAIL {name}")
                traceback.print_exc()
                failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
