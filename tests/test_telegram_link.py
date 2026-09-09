"""Tests for the lab half of the Telegram notifications.

The properties worth protecting are the ones that only show up at 3 a.m.:
a notification is never lost when the network drops, a retry after a
timeout cannot produce a duplicate message, the payload is valid JSON
(no bare ``NaN``), and nothing in here can raise into the GUI's event
pump.
"""

import io
import json
import gzip
import math
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unisweep.core import events as ev                          # noqa: E402
from unisweep.core.livedata import LiveData, LiveMaps           # noqa: E402
from unisweep.core.telegram_link import (                       # noqa: E402
    DEFAULT_SERVICE_URL, TelegramLink, _basename, _decimate, _num,
    new_rig_identity, service_url)


class _Resp(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): return False


class _Server:
    """Records what the link posted and replies like the real service."""

    def __init__(self, reply=None, fail=False):
        self.calls = []
        self.reply = reply or {"ok": True}
        self.fail = fail

    def __call__(self, request, timeout=None):
        body = request.data
        if request.headers.get("X-body-encoding") == "gzip" or \
                body[:2] == b"\x1f\x8b":
            body = gzip.decompress(body)
        self.calls.append({
            "url": request.full_url,
            "headers": {k.lower(): v for k, v in request.headers.items()},
            "body": json.loads(body.decode("utf-8")),
            "timeout": timeout,
        })
        if self.fail:
            raise OSError("no route to host")
        reply = self.reply(self.calls[-1]) if callable(self.reply) \
            else self.reply
        return _Resp(json.dumps(reply).encode())


def _patched(server, fn):
    original = urllib.request.urlopen
    urllib.request.urlopen = server
    try:
        return fn()
    finally:
        urllib.request.urlopen = original


def _link(allow_control=False, **kw):
    link = TelegramLink(**kw)
    link.configure(service_url="https://bot.example/", rig_id="RIG",
                   rig_token="t" * 32, rig_name="ATTODRY",
                   allow_control=allow_control)
    return link


# ------------------------------------------------------------- helpers ---
def test_num_is_json_safe():
    assert _num(float("nan")) is None
    assert _num(float("inf")) is None
    assert _num("abc") is None
    assert _num(None) is None
    assert _num(1 / 3) == 0.333333
    assert _num(2) == 2.0
    # what matters: json.dumps with allow_nan=False must never fail
    json.dumps([_num(v) for v in (float("nan"), 1e-30, 2)], allow_nan=False)


def test_decimate_keeps_the_ends():
    assert _decimate(list(range(5)), 10) == [0, 1, 2, 3, 4]
    idx = _decimate(list(range(1000)), 50)
    assert idx[0] == 0 and idx[-1] == 999
    assert len(idx) <= 51
    assert idx == sorted(set(idx))


def test_basename_handles_both_separators():
    assert _basename(r"C:\data\260817-2.csv") == "260817-2.csv"
    assert _basename("/home/lab/260817-2.csv") == "260817-2.csv"
    assert _basename("") == ""


def test_the_service_address_is_compiled_in():
    """Every installation must reach the group's bot with no setting up.

    The address is public — it is a website, and nothing behind it opens
    without a rig token — so keeping it in source is what makes "already
    configured" possible.
    """
    assert DEFAULT_SERVICE_URL.startswith("https://"), DEFAULT_SERVICE_URL
    assert service_url("") == DEFAULT_SERVICE_URL
    assert service_url("https://mine.example/") == "https://mine.example"
    import os
    os.environ["UNISWEEP_BOT_URL"] = "https://env.example"
    try:
        # the environment wins, so a developer can point one machine at a
        # private copy without editing anything
        assert service_url("https://mine.example") == "https://env.example"
    finally:
        del os.environ["UNISWEEP_BOT_URL"]


def test_a_taken_setup_name_is_reported_not_retried():
    link = _link()
    server = _Server(fail=False)

    def refuse(request, timeout=None):
        server(request, timeout)
        raise urllib.error.HTTPError(
            request.full_url, 409, "Conflict", {},
            io.BytesIO(json.dumps({"error": "name_taken"}).encode()))

    _patched(refuse, link._hello)          # must not raise into the loop
    assert link.link_status == "error"
    assert "different name" in link.last_error
    assert "ATTODRY" in link.last_error


def test_rig_identity_is_unique_and_long():
    a_id, a_token = new_rig_identity()
    b_id, b_token = new_rig_identity()
    assert a_id != b_id and a_token != b_token
    assert len(a_token) >= 20            # the service rejects shorter ones


# -------------------------------------------------------------- events ---
def test_events_are_composed_and_kept_until_delivered():
    link = _link()
    link.on_event(ev.SweepStarted(columns=("time", "SMU.Volt_sweep",
                                           "LOCKIN.X"),
                                  dimensions=1, planned_points=101))
    link.on_event(ev.SweepError(where="LOCKIN", message="timeout",
                                fatal=False, crucial=False))
    link.on_event(ev.SweepError(where="MAGNET", message="quench",
                                fatal=True))
    link.on_event(ev.SweepFinished(stopped=True, points=57))
    kinds = [e["kind"] for e in link._events]
    # a non-fatal, non-crucial error is a status-bar matter, not a push
    assert kinds == ["started", "error", "finished"], kinds
    # sequence numbers count *queued* events, so they stay dense and
    # the service's de-duplication key never has holes to reason about
    assert [e["seq"] for e in link._events] == [1, 2, 3]
    assert "quench" in link._events[1]["text"]
    assert "57 points" in link._events[2]["text"]


def test_a_finished_sweep_does_not_wait_for_the_next_heartbeat():
    """The bug this exists for: the loop only pushed at `next_push`, so a
    sweep that ended one second after a heartbeat sat there for the rest
    of the interval — and for up to five minutes if the network had been
    flaky, because the back-off deadline applied too."""
    link = _link()
    link.on_event(ev.PointMeasured(row=(1.0,), axis_values=(1.0,), file="f"))
    assert not link._urgent                # ordinary traffic can wait
    link.on_event(ev.SweepFinished(stopped=False, points=10))
    assert link._urgent                    # this cannot
    # every other kind the link treats as urgent must do the same. The
    # guards subsystem that once supplied a third kind is gone (its job
    # belongs to the per-point script), so these are the two that remain.
    for urgent in (ev.SweepError(where="x", message="y", fatal=True),
                   ev.SweepFinished(stopped=True, points=3)):
        link._urgent = False
        link.on_event(urgent)
        assert link._urgent, urgent


def test_the_urgent_flag_clears_only_once_everything_is_delivered():
    link = _link()
    link.on_event(ev.SweepFinished(stopped=False, points=3))
    _patched(_Server({"ok": True}), link._push)
    assert not link._events and not link._urgent


def test_closing_unisweep_reports_the_sweep_as_over():
    """Shutting the window ends the measurement, so it is announced as an
    ending rather than left for the server to guess at from silence."""
    link = _link()
    link.on_event(ev.SweepStarted(columns=("time", "A_sweep", "R"),
                                  dimensions=1, planned_points=100))
    link.on_event(ev.Progress(done=42, total=100))
    link._events.clear()
    link.note_shutdown()
    assert [e["kind"] for e in link._events] == ["finished"]
    text = link._events[0]["text"]
    # it reads like any other ending — how it ended is not the headline
    assert "Sweep ended" in text and "42 points" in text
    assert "closed" not in text and "Unisweep" not in text
    assert link._state == "idle"
    # and it is not said twice if the engine already finished properly
    link._events.clear()
    link.note_shutdown()
    assert not link._events


def test_a_normal_finish_is_not_relabelled_as_a_close():
    link = _link()
    link.on_event(ev.SweepStarted(columns=("time", "A_sweep", "R"),
                                  dimensions=1, planned_points=100))
    link.on_event(ev.SweepFinished(stopped=False, points=100))
    link.note_shutdown()
    kinds = [e["kind"] for e in link._events]
    assert kinds == ["started", "finished"], kinds
    assert "Sweep finished" in link._events[-1]["text"]


def test_event_queue_is_bounded():
    link = _link()
    for i in range(400):
        link.on_event(ev.SweepPaused())
        link.on_event(ev.SweepResumed())
    assert len(link._events) <= 200
    assert link._dropped > 0


def test_on_event_never_raises():
    link = _link()
    for junk in (None, object(), "nonsense", 42):
        link.on_event(junk)             # must not raise into the event pump


# ---------------------------------------------------------------- push ---
def test_push_posts_events_and_clears_them_on_success():
    link = _link()
    link.on_event(ev.SweepStarted(columns=("time", "A_sweep", "R"),
                                  dimensions=1, planned_points=10))
    server = _Server({"ok": True, "commands": []})
    _patched(server, link._push)

    call = server.calls[-1]
    assert call["url"] == "https://bot.example/api/v1/push"
    assert call["headers"]["x-rig-id"] == "RIG"
    assert call["headers"]["x-rig-token"] == "t" * 32
    assert [e["kind"] for e in call["body"]["events"]] == ["started"]
    assert call["body"]["state"]["state"] == "running"
    assert not link._events               # delivered, so no longer queued


def test_failed_push_keeps_events_with_the_same_sequence_numbers():
    """A push that fails must not drop the notification, and a push that
    timed out after the server stored it must not produce a second
    message — which is what stable sequence numbers give the service."""
    link = _link()
    link.on_event(ev.SweepFinished(stopped=False, points=3))
    seqs = [e["seq"] for e in link._events]

    try:
        _patched(_Server(fail=True), link._push)
    except OSError:
        pass
    assert [e["seq"] for e in link._events] == seqs

    server = _Server({"ok": True})
    _patched(server, link._push)
    assert [e["seq"] for e in server.calls[-1]["body"]["events"]] == seqs
    assert not link._events


def test_large_payloads_are_gzipped_and_still_valid_json():
    link, data, maps = _sweep_2d(rows=40, points=400)
    server = _Server({"ok": True})
    _patched(server, link._push)
    call = server.calls[-1]
    assert "snapshot" in call["body"]
    assert call["headers"].get("x-body-encoding") == "gzip"


def test_hello_learns_the_bot_link_and_the_roster():
    link = _link()
    server = _Server({"ok": True, "bot_username": "unisweep_lab_bot",
                      "bot_link": "https://t.me/unisweep_lab_bot",
                      "roster_known": True,
                      "links": [{"chat_id": 42, "title": "Misha",
                                 "since": "2026-09-08T10:00:00+08:00"}]})
    _patched(server, link._hello)
    assert link.link_status == "active"
    assert link.bot_link == "https://t.me/unisweep_lab_bot"
    assert [e["chat_id"] for e in link.links] == [42]
    assert "1 Telegram user(s) linked" in link.summary()
    # the rig never sends a chat id — nobody has to look one up
    assert "chat_id" not in server.calls[-1]["body"]


def test_a_database_blip_does_not_empty_the_roster():
    """'roster_known: false' means the service could not read the list.

    Blanking the Settings page then would tell the user they have nobody
    linked, which is a different — and wrong — statement."""
    link = _link()
    _patched(_Server({"ok": True, "roster_known": True,
                      "links": [{"chat_id": 42, "title": "Misha"}]}),
             link._hello)
    _patched(_Server({"ok": True, "roster_known": False, "links": []}),
             link._hello)
    assert [e["chat_id"] for e in link.links] == [42]


def test_pairing_code_is_requested_and_returned():
    link = _link()
    link.link_status = "active"
    server = _Server({"ok": True, "code": "418209", "ttl_s": 600,
                      "bot_link": "https://t.me/unisweep_lab_bot",
                      "bot_username": "unisweep_lab_bot"})
    issued = _patched(server, link.request_code)
    assert server.calls[-1]["url"] == "https://bot.example/api/v1/pair"
    assert server.calls[-1]["headers"]["x-rig-token"] == "t" * 32
    assert issued["code"] == "418209"
    assert issued["bot_link"].endswith("unisweep_lab_bot")


def test_a_malformed_code_is_an_error_not_a_silent_pass():
    link = _link()
    link.link_status = "active"
    for bad in ({"ok": True}, {"ok": True, "code": "12"},
                {"ok": True, "code": "1234567"}):
        try:
            _patched(_Server(bad), link.request_code)
        except RuntimeError:
            continue
        raise AssertionError(f"accepted {bad}")


def test_removing_a_user_posts_and_updates_the_roster():
    link = _link()
    link.links = [{"chat_id": 42, "title": "Misha"},
                  {"chat_id": 43, "title": "Ada"}]
    server = _Server({"ok": True,
                      "links": [{"chat_id": 43, "title": "Ada"}]})
    assert _patched(server, lambda: link.remove_link(42)) is True
    call = server.calls[-1]
    assert call["url"] == "https://bot.example/api/v1/links/remove"
    assert call["body"] == {"chat_id": 42}
    assert [e["chat_id"] for e in link.links] == [43]


def test_control_is_refused_when_the_rig_has_not_allowed_it():
    seen = []
    link = _link(allow_control=False,
                 command_cb=lambda cid, kind: seen.append((cid, kind)))
    link._handle_command({"id": 7, "kind": "stop"})
    assert not seen                       # never reaches the GUI
    assert link._results[-1] == {"command_id": 7, "ok": False,
                                 "detail": "remote control is switched off "
                                           "on this rig"}


def test_control_is_handed_to_the_gui_thread_when_allowed():
    seen = []
    link = TelegramLink(command_cb=lambda cid, kind: seen.append((cid, kind)))
    link.configure(service_url="https://bot.example", rig_id="RIG",
                   rig_token="t" * 32, rig_name="R", allow_control=True)
    link._handle_command({"id": 9, "kind": "to_zero"})
    assert seen == [(9, "to_zero")]
    # the link itself never touches the engine: no result until the GUI says
    assert not link._results


def test_snapshot_command_only_schedules_a_push():
    link = _link()
    link._handle_command({"id": 3, "kind": "snapshot"})
    assert link._force_snapshot is True
    assert link._results[-1]["ok"] is True


# ------------------------------------------------------------ snapshot ---
def _sweep_2d(rows=6, points=25, cmap_getter=None):
    """A 2-D sweep whose live stores hold plausible data."""
    columns = ("time", "MAG.Field_sweep", "GATE.Volt_sweep",
               "LOCKIN.X", "LOCKIN.Y")
    data, maps = LiveData(), LiveMaps()
    data.reset(columns, 2)
    maps.reset(("LOCKIN.X", "LOCKIN.Y"))
    link = TelegramLink(live_data=data, live_maps=maps,
                        program_getter=lambda: None,
                        cmap_getter=cmap_getter)
    link.configure(service_url="https://bot.example", rig_id="RIG",
                   rig_token="t" * 32, rig_name="R", allow_control=False)
    link.on_event(ev.SweepStarted(columns=columns, dimensions=2,
                                  planned_points=rows * points))
    grid = tuple(j / points for j in range(points))
    for i in range(rows):
        link.on_event(ev.FileOpened(path=rf"C:\data\row{i}.csv",
                                    columns=columns))
        data.new_file(rf"C:\data\row{i}.csv")
        for j, g in enumerate(grid):
            row = (i * points + j, float(i), g,
                   math.sin(g * 6.0) + i, math.cos(g * 6.0))
            data.add_row(row, (float(i), g), walk=1)
            link.on_event(ev.PointMeasured(row=row, axis_values=(float(i), g),
                                           file=f"row{i}.csv", walk=1))
        maps.on_row(ev.MapRowCommitted(
            grid=grid,
            read_rows={"LOCKIN.X": tuple(math.sin(g * 6.0) + i for g in grid),
                       "LOCKIN.Y": tuple(math.cos(g * 6.0) for g in grid)},
            row_value=float(i), master_value=0.0, iteration=0))
    return link, data, maps


def test_snapshot_carries_trace_stats_and_maps():
    link, _data, _maps = _sweep_2d(rows=5, points=30)
    snap = link._build_snapshot()

    assert snap["dimensions"] == 2
    assert snap["reads"] == ["LOCKIN.X", "LOCKIN.Y"]
    assert snap["file"] == "row4.csv"

    trace = snap["trace"]
    # the fast axis is the innermost one, and only the current file's rows
    assert trace["x_label"] == "GATE.Volt"
    assert trace["points"] == 30
    assert len(trace["x"]) == 30
    assert set(trace["series"]) == {"LOCKIN.X", "LOCKIN.Y"}
    assert len(trace["series"]["LOCKIN.X"]) == 30

    # the latest numbers ride on the heartbeat's last row, so the snapshot
    # carries no copy of the table — nothing on the server reads one
    assert "table" not in snap

    stats = snap["stats"]["LOCKIN.X"]
    assert stats["n"] == 150
    assert stats["min"] <= stats["mean"] <= stats["max"]

    grid_map = snap["maps"]["LOCKIN.X"]
    assert len(grid_map["rows"]) == 5
    assert len(grid_map["grid"]) == 30
    assert len(grid_map["z"]) == 5 and len(grid_map["z"][0]) == 30
    assert grid_map["x_label"] == "GATE.Volt"
    assert grid_map["y_label"] == "MAG.Field"

    # and the whole thing must survive strict JSON
    json.dumps(snap, allow_nan=False)


def test_the_snapshot_carries_the_screens_own_colour_scale():
    """A map in the chat should look like the map on the screen, so the
    scale is reported rather than chosen again in Telegram — and a plot
    window that has gone away mid-read costs a default, not a snapshot."""
    link, _d, _m = _sweep_2d(rows=2, points=5, cmap_getter=lambda: "plasma")
    assert link._build_snapshot()["cmap"] == "plasma"

    def boom():
        raise RuntimeError("the window closed")
    link, _d, _m = _sweep_2d(rows=2, points=5, cmap_getter=boom)
    snap = link._build_snapshot()
    assert snap["cmap"] == "" and snap["maps"], snap.get("cmap")

    # a machine that has never opened a map says nothing and the server
    # picks; a name long enough to be nonsense is trimmed, not trusted
    link, _d, _m = _sweep_2d(rows=2, points=5)
    assert link._build_snapshot()["cmap"] == ""
    link, _d, _m = _sweep_2d(rows=2, points=5, cmap_getter=lambda: "x" * 200)
    assert len(link._build_snapshot()["cmap"]) == 32


def test_snapshot_is_decimated_and_stays_small():
    link, _data, _maps = _sweep_2d(rows=200, points=1200)
    snap = link._build_snapshot()
    assert len(snap["trace"]["x"]) <= 801
    assert snap["trace"]["points"] == 1200
    m = snap["maps"]["LOCKIN.X"]
    assert len(m["rows"]) <= 161 and len(m["grid"]) <= 161
    assert len(m["z"]) == len(m["rows"])
    assert all(len(line) == len(m["grid"]) for line in m["z"])
    encoded = gzip.compress(json.dumps(snap, allow_nan=False).encode())
    assert len(encoded) < 1_500_000, len(encoded)


def test_snapshot_is_empty_before_a_sweep_and_never_raises():
    link = TelegramLink(live_data=LiveData(), live_maps=LiveMaps())
    assert link._build_snapshot() == {}
    assert TelegramLink()._build_snapshot() == {}


def test_1d_sweep_has_a_trace_but_no_map():
    columns = ("time", "GATE.Volt_sweep", "SMU.Curr")
    data = LiveData()
    data.reset(columns, 1)
    link = TelegramLink(live_data=data, live_maps=LiveMaps())
    link.on_event(ev.SweepStarted(columns=columns, dimensions=1,
                                  planned_points=50))
    for j in range(50):
        data.add_row((j, j * 0.1, j * 1e-9), (j * 0.1,))
    snap = link._build_snapshot()
    assert snap["trace"]["x_label"] == "GATE.Volt"
    assert snap["maps"] == {}


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
