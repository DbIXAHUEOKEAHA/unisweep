"""The lab half of the Telegram notifications.

The bot itself does not live here.  It runs unattended on a server (see
``server/`` in this repository), because the thing you most want to be
told about is the measurement computer becoming unreachable — and a
notifier that lives inside Unisweep cannot report that Unisweep has died.

This module is the other end of that arrangement: a single daemon thread
that pushes what the running sweep looks like to the service over HTTPS,
and collects whatever the service wants the rig to do.  Three properties
matter and are what the code is shaped around.

**It cannot disturb a measurement.**  Nothing here runs on the sweep
thread or the Tk thread.  :meth:`TelegramLink.on_event` only appends to a
bounded deque under a lock; every socket, every retry and every JSON
encode happens on the link thread.  An exception inside it is logged and
swallowed — there is no path from a network failure into the engine.

**It cannot lose an event.**  Notifications stay queued until a push
succeeds, and each carries a sequence number.  The service keys its
de-duplication on that number, so a push that timed out *after* the server
committed it is safe to send again: the retry inserts nothing.

**It holds no shared credential.**  The lab machine stores one rig token
that it generated itself, and the database password never leaves the
server.  Talking outward over 443 also means nothing has to be opened on
the lab network for the bot to reach the rig: commands, and the list of
people linked to it, arrive as the reply to the rig's own heartbeat.

Linking a person is a **six-digit code**: the rig asks the service for
one, shows it, and whoever sends those digits to the bot within a few
minutes is subscribed.  Nobody has to find their numeric chat id, and —
unlike a chat id, which is permanent and known to anyone who has ever
messaged you — a code expires and can be spent only once.
"""

from __future__ import annotations

import gzip
import json
import math
import secrets
import threading
import time
import urllib.error
import urllib.request
import uuid
from collections import deque
from typing import Callable, Optional

__all__ = ["TelegramLink", "DEFAULT_SERVICE_URL", "new_rig_identity"]

#: Where the group's bot service lives.  Set once, here, so that every
#: Unisweep installation is configured out of the box and nobody has to
#: type an address into the Settings page.
#:
#: This is deliberately in source: it is a public HTTPS endpoint, not a
#: secret.  Nothing it serves can be reached without a rig token that the
#: lab machine generated for itself, and the two real secrets — the
#: Telegram bot token and the database password — live only in the
#: server's environment variables and never leave it.  Publishing this
#: string is exactly as safe as publishing a website address.
DEFAULT_SERVICE_URL = "https://unisweep-bot.up.railway.app"

#: Overrides for people running their own copy, in this order:
#: ``UNISWEEP_BOT_URL`` in the environment, then ``tg_service_url`` in
#: ``config/settings.json``, then the constant above.
SERVICE_URL_ENV = "UNISWEEP_BOT_URL"


def service_url(configured: str = "") -> str:
    """The address this installation should talk to."""
    import os
    for candidate in (os.getenv(SERVICE_URL_ENV, ""), configured,
                      DEFAULT_SERVICE_URL):
        candidate = (candidate or "").strip().rstrip("/")
        if candidate:
            return candidate
    return ""

_API_HELLO = "/api/v1/hello"
_API_PAIR = "/api/v1/pair"
_API_PUSH = "/api/v1/push"
_API_RESULT = "/api/v1/result"
_API_UNLINK = "/api/v1/links/remove"

#: how much of the fast axis a phone-sized picture can usefully show
MAX_TRACE_POINTS = 800
#: a map bigger than this is decimated; the eye cannot resolve more on a
#: phone and the payload stops being cheap
MAX_MAP_ROWS = 160
MAX_MAP_COLS = 160
MAX_MAP_READS = 6
#: never queue notifications without bound if the service is unreachable
MAX_PENDING_EVENTS = 200
MAX_BACKOFF_S = 300.0
IDLE_PUSH_S = 60.0

#: Events nobody should wait a heartbeat for.  These go out on the next
#: turn of the loop instead of at the next scheduled push — the whole
#: point of the thing is that "your sweep finished" arrives when the
#: sweep finishes, not up to a quarter of a minute later.
URGENT_KINDS = {"finished", "error", "guard"}

#: While something urgent is waiting — or a sweep is running at all — a
#: failed push retries within this long however many failures came
#: before.  The plain exponential back-off climbs to five minutes, which
#: is the right answer for an idle rig and completely the wrong one for a
#: sweep that has just ended: it is what turns "finished" into
#: "finished, eventually".  It also has to stay comfortably under the
#: server's silence grace, or a blip would be read as a crash.
URGENT_BACKOFF_S = 60.0


def new_rig_identity() -> tuple:
    """A fresh ``(rig_id, rig_token)`` for this installation."""
    return uuid.uuid4().hex, secrets.token_urlsafe(32)


# --------------------------------------------------------------- helpers --
def _num(value):
    """JSON-safe number: NaN and infinities become null, not literals that
    only Python's own parser accepts."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(v):
        return None
    return float(f"{v:.6g}")


def _decimate(seq, limit: int):
    """Evenly thin a sequence, always keeping the first and last sample."""
    n = len(seq)
    if n <= limit:
        return list(range(n))
    step = (n - 1) / float(limit - 1)
    idx = sorted({int(round(i * step)) for i in range(limit)})
    if idx and idx[-1] != n - 1:
        idx.append(n - 1)
    return idx


#: What the engine calls a guard action, and what it means to a person.
_GUARD_ACTION = {
    "warn": "carrying on, but watch it",
    "pause": "sweep paused",
    "back_off": "backed off and ended this line",
    "stop": "sweep stopped",
    "to_zero": "sweep stopped, ramping everything to zero",
}


def _basename(path: str) -> str:
    """Windows or POSIX — the data files come from either."""
    return str(path or "").replace("\\", "/").rstrip("/").split("/")[-1]


def _fmt_duration(seconds) -> str:
    try:
        seconds = max(int(float(seconds)), 0)
    except (TypeError, ValueError):
        return "?"
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h} h {m:02d} m"
    if m:
        return f"{m} m {s:02d} s"
    return f"{s} s"


class TelegramLink:
    """Pushes the running sweep to the notification service.

    The GUI owns one of these for the lifetime of the application.  It is
    reconfigured (not recreated) when the Settings page changes, so a
    running sweep never loses its event history to a settings edit.
    """

    def __init__(self, live_data=None, live_maps=None,
                 program_getter: Callable = None,
                 status_cb: Callable = None,
                 command_cb: Callable = None,
                 rig_name: str = ""):
        self._data = live_data
        self._maps = live_maps
        self._program_getter = program_getter or (lambda: None)
        self._status_cb = status_cb or (lambda text, state: None)
        self._command_cb = command_cb or (lambda cid, kind: None)

        self._lock = threading.RLock()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

        self.service_url = ""
        self.rig_id = ""
        self.rig_token = ""
        self.rig_name = rig_name or "Unisweep"
        self.allow_control = False
        self.push_s = 15.0
        self.snapshot_s = 60.0
        self.timeout = 25.0

        self.link_status = "off"        # off | connecting | active | error
        self.last_error = ""
        self.last_push_ok: Optional[float] = None
        #: who the service says is subscribed to this rig — shown on the
        #: Settings page and refreshed on every heartbeat, so removing
        #: somebody in Telegram is visible here too
        self.links: list = []
        self.bot_link = ""
        self.bot_username = ""

        self._events: deque = deque()
        self._seq = 0
        self._dropped = 0
        self._state = "idle"
        self._program: dict = {}
        self._progress: dict = {}
        self._last_row: dict = {}
        self._columns: tuple = ()
        self._dimensions = 1
        self._reads: tuple = ()
        self._file = ""
        self._run_started: Optional[float] = None
        self._snapshot_due = 0.0
        self._force_snapshot = False
        self._urgent = False
        self._results: deque = deque()

    # ------------------------------------------------------------ config --
    @property
    def enabled(self) -> bool:
        return bool(self.service_url and self.rig_id and self.rig_token
                    and self._thread is not None and self._thread.is_alive())

    def configure(self, *, service_url: str, rig_id: str, rig_token: str,
                  rig_name: str, allow_control: bool,
                  push_s: float = 15.0, snapshot_s: float = 60.0) -> None:
        with self._lock:
            self.service_url = (service_url or "").strip().rstrip("/")
            self.rig_id = (rig_id or "").strip()
            self.rig_token = (rig_token or "").strip()
            self.rig_name = (rig_name or "Unisweep").strip()[:64]
            self.allow_control = bool(allow_control)
            self.push_s = max(float(push_s), 5.0)
            self.snapshot_s = max(float(snapshot_s), self.push_s)
        self._wake.set()

    # ----------------------------------------------------------- lifecycle --
    def start(self) -> bool:
        with self._lock:
            if not (self.service_url and self.rig_id and self.rig_token):
                self.link_status = "error"
                self.last_error = "service address or rig identity missing"
                return False
            if self._thread is not None and self._thread.is_alive():
                self._wake.set()
                return True
            self._stop.clear()
            self.link_status = "connecting"
            self._thread = threading.Thread(target=self._run, daemon=True,
                                            name="unisweep-telegram")
            self._thread.start()
        return True

    def stop(self, join: float = 2.0, final_push: bool = True) -> None:
        if final_push:
            self._final_push()
        self._stop.set()
        self._wake.set()
        thread = self._thread
        if thread is not None and join:
            thread.join(join)
        self._thread = None
        with self._lock:
            if self.link_status != "error":
                self.link_status = "off"
        self._status("monitoring stopped")

    def note_shutdown(self) -> None:
        """Unisweep is closing, so the sweep is over.

        Closing the window — on purpose or by accident — ends the
        measurement, so it is reported as an ending rather than left for
        the server's silence watchdog to guess at several minutes later.
        Worded exactly like any other ending: *why* it ended is not what
        somebody reading their phone wants from the first line.  If the
        engine already emitted its own finish, ``_state`` is no longer
        running and this adds nothing.
        """
        with self._lock:
            if self._state not in ("running", "paused"):
                return
            elapsed = (time.time() - self._run_started
                       if self._run_started else
                       (self._progress or {}).get("elapsed_s") or 0)
            points = int((self._progress or {}).get("done") or 0)
            counted = f"{points:,}".replace(",", " ")
            self._queue(
                "finished",
                f"⛔ Sweep ended — {_fmt_duration(elapsed)}, "
                f"{counted} points"
                + (f"\n{_basename(self._file)}" if self._file else ""))
            self._state = "idle"

    def _final_push(self) -> None:
        """One last heartbeat as the application closes.

        Two things depend on it: the sweep-end notification queued a
        moment ago actually leaves, and the rig reports itself idle — so a
        clean quit is not announced as "the rig went silent", which is
        what the watchdog on the server is for.
        """
        self.note_shutdown()
        with self._lock:
            if self.link_status != "active":
                return
            self._state = "idle"
            self._force_snapshot = False
            self._snapshot_due = time.time() + self.snapshot_s
        saved, self.timeout = self.timeout, 6.0
        try:
            self._push()
        except Exception:                              # noqa: BLE001
            pass                      # shutting down; nothing to report to
        finally:
            self.timeout = saved

    def summary(self) -> str:
        with self._lock:
            status, err = self.link_status, self.last_error
            ok = self.last_push_ok
            queued = len(self._events)
            people = len(self.links)
        if status == "off":
            return "not monitoring"
        if status == "error":
            return f"problem: {err}"
        if status == "connecting":
            return "contacting the notification service…"
        age = "never" if ok is None else \
            _fmt_duration(time.time() - ok) + " ago"
        who = ("nobody linked yet — press Generate code" if not people
               else f"{people} Telegram user(s) linked")
        extra = f", {queued} event(s) queued" if queued else ""
        return f"monitoring · {who} · last report {age}{extra}"

    # -------------------------------------------------------- GUI feeding --
    def on_event(self, event) -> None:
        """Called on the Tk thread for every engine event.

        Deliberately trivial: it updates a few fields and appends to a
        deque.  Anything slower would be running inside the GUI's event
        pump, which drains the same queue the measurement writes into.
        """
        try:
            self._absorb(event)
        except Exception:                              # noqa: BLE001
            pass                # a notifier must never break the event pump

    def _absorb(self, event) -> None:
        name = type(event).__name__
        with self._lock:
            if name == "SweepStarted":
                self._columns = tuple(event.columns)
                self._dimensions = int(event.dimensions)
                self._reads = tuple(self._columns[1 + self._dimensions:])
                self._state = "running"
                self._file = ""
                self._progress = {"done": 0, "total": int(
                    getattr(event, "planned_points", 0) or 0)}
                self._last_row = {}
                self._run_started = time.time()
                self._program = self._describe_program()
                planned = f"{self._progress['total']:,}".replace(",", " ")
                self._queue("started",
                            f"▶️ Sweep started — {planned} points"
                            + (f"\n{self._program_line()}"
                               if self._program_line() else ""))
                self._force_snapshot = True
            elif name == "FileOpened":
                self._file = str(getattr(event, "path", ""))
                self._queue("file", f"📄 New data file: "
                                    f"{self._file.split(chr(92))[-1].split('/')[-1]}")
            elif name == "PointMeasured":
                row = tuple(getattr(event, "row", ()) or ())
                self._last_row = {c: _num(v) for c, v in
                                  zip(self._columns, row)}
            elif name == "Progress":
                self._progress = {
                    "done": int(getattr(event, "done", 0) or 0),
                    "total": int(getattr(event, "total", 0) or 0),
                    "eta_s": getattr(event, "eta_seconds", None),
                    "elapsed_s": getattr(event, "elapsed_seconds", None),
                }
            elif name == "SweepPaused":
                self._state = "paused"
                self._queue("paused", "⏸ Sweep paused")
            elif name == "SweepResumed":
                self._state = "running"
                self._queue("resumed", "▶️ Sweep resumed")
            elif name == "SweepError":
                fatal = bool(getattr(event, "fatal", False))
                crucial = bool(getattr(event, "crucial", False))
                if fatal:
                    self._state = "error"
                if fatal or crucial:
                    icon = "🔴" if fatal else "⚠️"
                    self._queue("error",
                                f"{icon} {getattr(event, 'where', 'sweep')} "
                                f"— {getattr(event, 'message', '')}"
                                + ("\nStopping the sweep."
                                   if fatal else ""))
            elif name == "GuardTripped":
                if getattr(event, "applied", False):
                    values = getattr(event, "values", {}) or {}
                    shown = ", ".join(
                        f"{k}={_num(v)}" for k, v in list(values.items())[:6])
                    action = _GUARD_ACTION.get(
                        str(getattr(event, "action", "")),
                        str(getattr(event, "action", "?")))
                    self._queue(
                        "guard",
                        f"🛡 Safety limit reached — {action}"
                        + (f"\n{getattr(event, 'message', '')}"
                           if getattr(event, "message", "") else "")
                        + (f"\n{shown}" if shown else ""))
            elif name == "SweepFinished":
                stopped = bool(getattr(event, "stopped", False))
                self._state = "stopped" if stopped else "finished"
                points = int(getattr(event, "points", 0) or 0)
                elapsed = (time.time() - self._run_started
                           if self._run_started else
                           self._progress.get("elapsed_s") or 0)
                head = "⛔ Sweep stopped" if stopped else "✅ Sweep finished"
                counted = f"{points:,}".replace(",", " ")
                self._queue(
                    "finished",
                    f"{head} — {_fmt_duration(elapsed)}, {counted} points"
                    + (f"\n{_basename(self._file)}" if self._file else ""))
                self._force_snapshot = True
                self._run_started = None
        self._wake.set()

    def _queue(self, kind: str, text: str) -> None:
        self._seq += 1
        self._events.append({"seq": self._seq, "kind": kind,
                             "text": text, "ts": time.time()})
        if kind in URGENT_KINDS:
            self._urgent = True
        while len(self._events) > MAX_PENDING_EVENTS:
            self._events.popleft()
            self._dropped += 1

    def report_result(self, command_id: int, ok: bool, detail: str) -> None:
        """The GUI calls this after running a command from the bot."""
        with self._lock:
            self._results.append({"command_id": int(command_id),
                                  "ok": bool(ok), "detail": str(detail)[:400]})
        self._wake.set()

    # ------------------------------------------------------------- thread --
    def _run(self) -> None:
        failures = 0
        next_push = 0.0
        next_hello = 0.0
        while not self._stop.is_set():
            # Cleared before the work, never after it: an event arriving
            # mid-push then leaves the flag set and the next turn picks it
            # up immediately.  Clearing afterwards swallows that wake-up,
            # and the notification waits for the timeout instead.
            self._wake.clear()
            now = time.time()
            with self._lock:
                urgent = self._urgent
                busy = self._state in ("running", "paused")
            try:
                if self.link_status in ("connecting", "error") \
                        and now >= next_hello:
                    # a rejected name (or any other refusal) must not turn
                    # into a request every couple of seconds
                    next_hello = now + 30.0
                    self._hello()
                if self.link_status == "active" and (urgent
                                                     or now >= next_push):
                    self._push()
                    failures = 0
                    with self._lock:
                        interval = self.push_s if self._state in (
                            "running", "paused") else IDLE_PUSH_S
                    next_push = time.time() + interval
            except Exception as exc:                   # noqa: BLE001
                failures += 1
                delay = min(MAX_BACKOFF_S,
                            self.push_s * (2 ** min(failures, 5)))
                if urgent or busy:
                    delay = min(delay, URGENT_BACKOFF_S)
                next_push = time.time() + delay
                with self._lock:
                    self.last_error = f"{type(exc).__name__}: {exc}"
                    if failures >= 3 and self.link_status == "active":
                        self.link_status = "error"
                self._status(f"cannot reach the notification service "
                             f"({self.last_error}) — retrying in "
                             f"{_fmt_duration(delay)}")
            self._wake.wait(timeout=2.0)

    # ---------------------------------------------------------------- HTTP --
    def _post(self, path: str, payload: dict, headers: dict = None) -> dict:
        body = json.dumps(payload, allow_nan=False).encode("utf-8")
        head = {"Content-Type": "application/json",
                "User-Agent": "Unisweep/2"}
        if len(body) > 4096:
            body = gzip.compress(body, 6)
            head["X-Body-Encoding"] = "gzip"
        head.update(headers or {})
        request = urllib.request.Request(self.service_url + path, data=body,
                                         headers=head, method="POST")
        try:
            with urllib.request.urlopen(request,
                                        timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:300]
            try:
                detail = json.loads(detail).get("error", detail)
            except Exception:                          # noqa: BLE001
                pass
            raise RuntimeError(f"HTTP {exc.code}: {detail}") from None
        try:
            return json.loads(raw)
        except ValueError:
            raise RuntimeError("service returned something that is not JSON")

    def _auth(self) -> dict:
        return {"X-Rig-Id": self.rig_id, "X-Rig-Token": self.rig_token}

    def _hello(self) -> None:
        """Register (or re-authenticate) and read back the roster."""
        with self._lock:
            payload = {"rig_id": self.rig_id, "rig_token": self.rig_token,
                       "name": self.rig_name,
                       "allow_control": self.allow_control, "version": 1}
        try:
            reply = self._post(_API_HELLO, payload)
        except RuntimeError as exc:
            if "name_taken" in str(exc):
                # Not a transient failure: retrying cannot fix it, so say
                # what to do instead of backing off forever.
                with self._lock:
                    self.link_status = "error"
                    self.last_error = (
                        f"another setup is already called "
                        f"'{self.rig_name}' — give this one a different name")
                self._status(self.summary())
                return
            raise
        with self._lock:
            self.last_error = ""
            self.link_status = "active"
            self.bot_username = str(reply.get("bot_username") or "")
            self.bot_link = str(reply.get("bot_link") or "")
            if reply.get("roster_known"):
                self.links = list(reply.get("links") or [])
        self._status(self.summary())

    # --------------------------------------------------------- pairing ----
    def request_code(self) -> dict:
        """Ask the service for a pairing code to show the user.

        Blocking, and called from the GUI thread when the button is
        pressed — the user is standing there waiting for the number, so
        doing it in the background and reporting later would be worse.
        Raises on failure so the page can say what went wrong.
        """
        if not (self.service_url and self.rig_id and self.rig_token):
            raise RuntimeError("the notification service is not configured")
        # a code is useless if the rig is not registered yet
        if self.link_status not in ("active",):
            self._hello()
        reply = self._post(_API_PAIR, {}, self._auth())
        code = str(reply.get("code") or "")
        if len(code) != 6:
            raise RuntimeError("the service did not return a code")
        with self._lock:
            self.bot_username = str(reply.get("bot_username")
                                    or self.bot_username)
            self.bot_link = str(reply.get("bot_link") or self.bot_link)
        return {"code": code,
                "ttl_s": float(reply.get("ttl_s") or 600.0),
                "bot_link": self.bot_link,
                "bot_username": self.bot_username}

    def refresh_links(self) -> list:
        """Re-read the roster now, outside the heartbeat.

        Used while a pairing code is on screen, so the window can say
        "linked" the moment somebody uses it.
        """
        try:
            self._hello()
        except Exception:                              # noqa: BLE001
            pass                      # a failed poll is not worth an error
        with self._lock:
            return list(self.links)

    def remove_link(self, chat_id) -> bool:
        """Unlink one Telegram user from this rig, from the Settings page."""
        reply = self._post(_API_UNLINK, {"chat_id": int(chat_id)},
                           self._auth())
        with self._lock:
            self.links = list(reply.get("links") or [])
        self._status(self.summary())
        return bool(reply.get("ok"))

    def _push(self) -> None:
        with self._lock:
            events = list(self._events)
            results = list(self._results)
            due = (self._force_snapshot
                   or time.time() >= self._snapshot_due
                   or self._state in ("finished", "stopped"))
            state = self._state_payload()
        snapshot = self._build_snapshot() if due else None
        payload = {"state": state, "events": events}
        if snapshot:
            payload["snapshot"] = snapshot

        reply = self._post(_API_PUSH, payload, self._auth())
        sent = {e["seq"] for e in events}
        with self._lock:
            self._events = deque(e for e in self._events
                                 if e["seq"] not in sent)
            self.last_push_ok = time.time()
            self.link_status = "active"
            self.last_error = ""
            if not self._events:
                self._urgent = False
            # the roster travels on every heartbeat, so somebody unlinking
            # in Telegram shows up on the Settings page without asking
            if reply.get("roster_known"):
                self.links = list(reply.get("links") or [])
            if snapshot:
                self._force_snapshot = False
                self._snapshot_due = time.time() + self.snapshot_s
        self._status(self.summary())

        for result in results:
            try:
                self._post(_API_RESULT, result, self._auth())
                with self._lock:
                    if result in self._results:
                        self._results.remove(result)
            except Exception:                          # noqa: BLE001
                break                    # try again on the next heartbeat

        for command in reply.get("commands") or []:
            self._handle_command(command)

    def _handle_command(self, command: dict) -> None:
        kind = str(command.get("kind") or "")
        cid = command.get("id")
        if kind == "snapshot":
            with self._lock:
                self._force_snapshot = True
            self._wake.set()
            if cid is not None:
                self.report_result(cid, True, "snapshot sent")
            return
        if kind in ("pause", "resume", "stop", "to_zero"):
            if not self.allow_control:
                if cid is not None:
                    self.report_result(cid, False,
                                       "remote control is switched off "
                                       "on this rig")
                return
            # runs on the GUI thread — engine control never happens here
            try:
                self._command_cb(cid, kind)
            except Exception as exc:                   # noqa: BLE001
                if cid is not None:
                    self.report_result(cid, False, f"{type(exc).__name__}")

    def _status(self, text: str) -> None:
        try:
            self._status_cb(text, self.link_status)
        except Exception:                              # noqa: BLE001
            pass

    # ------------------------------------------------------------ payloads --
    def _describe_program(self) -> dict:
        program = self._program_getter()
        if program is None:
            return {}
        try:
            axes = []
            for ax in program.axes:
                axes.append({"label": f"{ax.device}.{ax.parameter}",
                             "start": _num(ax.start), "stop": _num(ax.stop),
                             "rate": _num(ax.rate), "delay": _num(ax.delay),
                             "walks": int(ax.effective_walks())})
            return {"axes": axes, "reads": list(program.reads),
                    "dimensions": int(program.dimensions),
                    "file": _basename(self._file)}
        except Exception:                              # noqa: BLE001
            return {}

    def _program_line(self) -> str:
        """The axes, as somebody would read them out: name, from, to."""
        axes = (self._program or {}).get("axes") or []
        if not axes:
            return ""
        width = max(len(str(a.get("label", "?"))) for a in axes)
        return "\n".join(
            f"{str(a.get('label', '?')).ljust(width)}  {a.get('start')} → "
            f"{a.get('stop')}" for a in axes)

    def _state_payload(self) -> dict:
        program = self._describe_program() or self._program
        program = dict(program or {})
        program["file"] = _basename(self._file)
        return {"state": self._state,
                "program": program,
                "progress": {k: (_num(v) if k in ("eta_s", "elapsed_s") else v)
                             for k, v in (self._progress or {}).items()},
                "last_row": self._last_row,
                "dropped_events": self._dropped,
                "at": time.time()}

    def _build_snapshot(self) -> dict:
        """A decimated copy of what the plots are showing.

        Rendering happens on the server, so what travels is numbers, not
        pictures — which is also what lets a chat ask for a *different*
        parameter later without the rig doing anything.
        """
        data, maps = self._data, self._maps
        if data is None:
            return {}
        try:
            with self._lock:
                columns = tuple(self._columns)
                dims = self._dimensions
                reads = tuple(self._reads)
                state = self._state
                file_name = _basename(self._file)
            if not columns:
                columns = tuple(getattr(data, "columns", ()) or ())
                if not columns:
                    return {}
                reads = tuple(columns[1 + dims:])
            out = {"state": state, "columns": list(columns),
                   "dimensions": dims, "reads": list(reads),
                   "file": file_name, "at": time.time(),
                   "trace": self._trace(data, columns, dims, reads),
                   "stats": self._stats(data, reads),
                   "maps": self._map_payload(maps, columns, dims, reads)}
            return out
        except Exception:                              # noqa: BLE001
            return {}

    def _trace(self, data, columns, dims, reads) -> dict:
        """The current walk along the fast (innermost) axis.

        ``scan_start`` is where the current data file began, which is
        exactly one inner sweep — the same slice the live line plot draws
        with 'this scan only'.
        """
        if len(columns) <= dims:
            return {}
        fast = columns[dims]
        try:
            start = data.scan_start()
        except Exception:                              # noqa: BLE001
            start = 0
        x = list(data.column(fast, start=start))
        if len(x) < 2:
            return {}
        keep = _decimate(x, MAX_TRACE_POINTS)
        series = {}
        for read in reads:
            y = list(data.column(read, start=start))
            if len(y) < 2:
                continue
            series[read] = [_num(y[i]) if i < len(y) else None for i in keep]
        if not series:
            return {}
        return {"x_label": fast.replace("_sweep", ""),
                "x": [_num(x[i]) for i in keep],
                "series": series,
                "points": len(x)}

    def _stats(self, data, reads) -> dict:
        out = {}
        for read in reads:
            values = [v for v in data.column(read) if v == v]   # drop NaN
            if not values:
                continue
            out[read] = {"min": _num(min(values)), "max": _num(max(values)),
                         "mean": _num(sum(values) / len(values)),
                         "last": _num(values[-1]), "n": len(values)}
        return out

    def _map_payload(self, maps, columns, dims, reads) -> dict:
        if maps is None or dims < 2 or len(columns) <= dims:
            return {}
        x_label = columns[dims].replace("_sweep", "")
        y_label = columns[dims - 1].replace("_sweep", "")
        out = {}
        for read in list(reads)[:MAX_MAP_READS]:
            try:
                if not maps.has_data(read):
                    continue
                matrix = maps.matrix(read)
            except Exception:                          # noqa: BLE001
                continue
            if not matrix:
                continue
            grid, labels, values = matrix
            grid = list(grid)
            labels = list(labels)
            rows_keep = _decimate(labels, MAX_MAP_ROWS)
            cols_keep = _decimate(grid, MAX_MAP_COLS)
            out[read] = {
                "grid": [_num(grid[j]) for j in cols_keep],
                "rows": [_num(labels[i]) for i in rows_keep],
                "z": [[_num(values[i][j]) for j in cols_keep]
                      for i in rows_keep],
                "x_label": x_label, "y_label": y_label,
            }
        return out
