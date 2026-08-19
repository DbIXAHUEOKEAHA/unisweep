"""Telegram notifications for sweep completion (``config/settings.json``).

A measurement that runs overnight should tell you when it's done — or when
it died. This uses Telegram's plain HTTPS Bot API through :mod:`urllib`
(no extra packages): create a bot with @BotFather to get the token, send
it one message, and read your chat id from @userinfobot or the bot's
``getUpdates``. The token is stored locally in ``config/settings.json``.

Sending is fire-and-forget in a daemon thread with a timeout; a network
failure can never raise into the measurement loop — the outcome is
reported back through a callback instead.
"""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request

__all__ = ["TelegramNotifier", "compose_sweep_message"]

_API = "https://api.telegram.org/bot{token}/sendMessage"


def _fmt_duration(seconds: float) -> str:
    seconds = max(int(seconds), 0)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h} h {m:02d} m"
    if m:
        return f"{m} m {s:02d} s"
    return f"{s} s"


def compose_sweep_message(stopped: bool, elapsed_s: float, points: int,
                          filename: str = "", detail: str = "") -> str:
    """The text sent when a sweep ends — same for finish and abort, with
    the reason appended when the engine stopped early."""
    head = "⛔ Unisweep: sweep STOPPED" if stopped \
        else "✅ Unisweep: sweep finished"
    parts = [head, f"duration {_fmt_duration(elapsed_s)}",
             f"{points} points"]
    if filename:
        parts.append(filename)
    text = " — ".join(parts)
    if detail:
        text += f"\n{detail}"
    return text


class TelegramNotifier:
    """Sends messages through the Bot API; safe to call from any thread."""

    def __init__(self, token: str, chat_id: str, timeout: float = 10.0):
        self.token = (token or "").strip()
        self.chat_id = (chat_id or "").strip()
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.token and self.chat_id)

    # -- blocking core (separated so tests can call it directly) --------
    def send(self, text: str) -> tuple[bool, str]:
        if not self.configured:
            return False, "Telegram: token or chat id missing"
        url = _API.format(token=self.token)
        payload = json.dumps({"chat_id": self.chat_id,
                              "text": text}).encode("utf-8")
        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode("utf-8", "replace"))
            if body.get("ok"):
                return True, "Telegram: message sent"
            return False, f"Telegram: API refused — {body}"
        except urllib.error.HTTPError as exc:
            try:
                detail = json.loads(exc.read().decode("utf-8", "replace"))
                detail = detail.get("description", str(exc))
            except Exception:                     # noqa: BLE001
                detail = str(exc)
            return False, f"Telegram: {detail}"
        except Exception as exc:                  # noqa: BLE001
            return False, f"Telegram: {type(exc).__name__}: {exc}"

    # -- what the app uses ----------------------------------------------
    def send_async(self, text: str, done=None) -> None:
        """Send in a daemon thread; ``done(ok, detail)`` may be called
        from that thread — marshal to the GUI through a queue."""
        def work():
            ok, detail = self.send(text)
            if done is not None:
                try:
                    done(ok, detail)
                except Exception:                 # noqa: BLE001
                    pass
        threading.Thread(target=work, daemon=True).start()
