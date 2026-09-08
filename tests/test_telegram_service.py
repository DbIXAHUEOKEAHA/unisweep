"""Tests for the notification service (``server/unisweep_bot``).

Everything here is the pure half — text, preferences, figures — so the
suite runs without Postgres or a bot token.  The database layer's own
contract (a failure returns ``None``, an empty result returns an empty
container) is exercised by the handlers through fakes.
"""

import gzip
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server"))

# config refuses to import without these; the values are never used
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "0:test")
os.environ.setdefault("DATABASE_URL", "postgresql://test/test")

try:
    from unisweep_bot import formatting as fmt
    from unisweep_bot import render
    HAVE_SERVER = True
except ImportError as exc:                             # pragma: no cover
    print(f"skipping: server dependencies missing ({exc})")
    HAVE_SERVER = False


# ------------------------------------------------------------ formatting --
def test_message_splitting_respects_the_limit():
    text = "\n".join(f"line {i} " + "x" * 60 for i in range(400))
    chunks = fmt.split_message(text, limit=1000)
    assert all(len(c) <= 1000 for c in chunks)
    assert sum(len(c) for c in chunks) >= len(text) - len(chunks)
    # a single pathological line is cut rather than sent over the limit
    chunks = fmt.split_message("y" * 5000, limit=1000)
    assert all(len(c) <= 1000 for c in chunks)
    assert "".join(chunks) == "y" * 5000
    assert fmt.split_message("short") == ["short"]


def test_escaping_survives_parameter_names():
    assert fmt.esc("LOCKIN<X> & Y") == "LOCKIN&lt;X&gt; &amp; Y"


def test_value_formatting_never_prints_nan_as_a_number():
    assert fmt.fmt_value(float("nan")) == "NaN"
    assert fmt.fmt_value(None) == "—"
    assert fmt.fmt_value(0.000123456789) == "0.000123457"
    assert fmt.fmt_value(True) == "yes"


def test_duration_is_readable():
    assert fmt.fmt_duration(5025) == "1 h 23 m"
    assert fmt.fmt_duration(61) == "1 m 01 s"
    assert fmt.fmt_duration(9) == "9 s"
    assert fmt.fmt_duration(None) == "—"


def test_defaults_are_quiet_where_it_matters():
    prefs = fmt.prefs_of({})
    assert prefs["finished"] and prefs["error"] and prefs["silent"]
    # a 2-D sweep opens a file per row: that must not be a message each
    assert not prefs["file"] and not prefs["started"]
    assert prefs["progress_min"] == 0


def test_stored_preferences_win_but_unknown_keys_are_ignored():
    prefs = fmt.prefs_of({"prefs": {"error": False, "nonsense": 1}})
    assert prefs["error"] is False
    assert "nonsense" not in prefs
    # psycopg2 may hand back JSON as text depending on the driver version
    assert fmt.prefs_of({"prefs": '{"error": false}'})["error"] is False
    assert fmt.prefs_of({"prefs": "not json"})["error"] is True


def test_snapshot_unpacking_accepts_gzip_and_plain_and_junk():
    payload = {"reads": ["A"]}
    raw = json.dumps(payload).encode()
    assert fmt.unpack_snapshot(gzip.compress(raw)) == payload
    assert fmt.unpack_snapshot(raw) == payload
    assert fmt.unpack_snapshot(b"\x00\x01broken") is None
    assert fmt.unpack_snapshot(b"") is None


def test_status_text_reports_state_progress_and_readings():
    link = {"rig_name": "ATTODRY", "rig_id": "r1", "last_seen": None,
            "state": {"state": "running",
                      "progress": {"done": 50, "total": 200,
                                   "eta_s": 3600, "elapsed_s": 1200},
                      "program": {"axes": [
                          {"label": "MAG.Field", "start": 0, "stop": 9},
                          {"label": "GATE.Volt", "start": -2, "stop": 2}],
                          "file": "260817-2.csv"},
                      "last_row": {"LOCKIN.X": 1.25e-6}}}
    text = fmt.status_text(link, {}, 12.0)
    assert "ATTODRY" in text and "running" in text
    assert "25%" in text and "(50/200)" in text
    assert "ETA 1 h 00 m" in text
    assert "GATE.Volt" in text and "(fast)" in text
    assert "1.25e-06" in text


def test_table_text_shows_the_tail():
    snapshot = {"table": {"columns": ["time", "A", "B"],
                          "rows": [[i, i * 0.5, None] for i in range(30)],
                          "total": 900}}
    text = fmt.table_text(snapshot, rows=5)
    assert text.count("\n") >= 5
    assert "of 900 rows" in text
    assert fmt.table_text({}, 5) == "No rows yet."


def test_rig_line_marks_a_rig_that_stopped_reporting():
    from datetime import datetime, timedelta, timezone
    fresh = {"rig_name": "A", "state": {"state": "running"},
             "last_seen": datetime.now(timezone.utc)}
    stale = {"rig_name": "B", "state": {"state": "running"},
             "last_seen": datetime.now(timezone.utc) - timedelta(hours=2)}
    assert "not reporting" not in fmt.rig_line(fresh)
    assert "not reporting" in fmt.rig_line(stale)


# ---------------------------------------------------------------- render --
def _trace(n=200):
    import math
    x = [i / n * 4 - 2 for i in range(n)]
    return {"x_label": "GATE.Volt", "x": x,
            "series": {"LOCKIN.X": [math.tanh(v * 3) for v in x],
                       "LOCKIN.Y": [math.exp(-v * v) for v in x]}}


def _map(rows=40, cols=60):
    import math
    grid = [j / cols * 4 - 2 for j in range(cols)]
    labels = [i / rows * 9 for i in range(rows)]
    z = [[math.sin(g * 3) * math.cos(r) for g in grid] for r in labels]
    if rows > 3 and cols > 5:
        z[3][5] = float("nan")                # a condition hole
    return {"grid": grid, "rows": labels, "z": z,
            "x_label": "GATE.Volt", "y_label": "MAG.Field"}


def test_trace_renders_a_png():
    png = render.render_trace(_trace(), ["LOCKIN.X"], "rig — LOCKIN.X")
    assert png and png[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(png) > 5000


def test_trace_renders_several_series():
    png = render.render_trace(_trace(), ["LOCKIN.X", "LOCKIN.Y"], "rig")
    assert png and png[:4] == b"\x89PNG"


def test_trace_declines_when_there_is_nothing_to_draw():
    assert render.render_trace({}, ["A"], "t") is None
    assert render.render_trace(_trace(), ["missing"], "t") is None
    assert render.render_trace({"x": [1], "series": {"A": [1]}},
                               ["A"], "t") is None


def test_map_renders_a_png_with_holes():
    png = render.render_map(_map(), "LOCKIN.X", "rig — LOCKIN.X")
    assert png and png[:4] == b"\x89PNG"


def test_map_survives_a_single_row_and_a_ragged_grid():
    one = _map(rows=1, cols=20)
    assert render.render_map(one, "A", "t")
    ragged = _map(rows=4, cols=10)
    ragged["grid"] = ragged["grid"][:3]        # mismatched on purpose
    assert render.render_map(ragged, "A", "t")


def test_map_declines_on_all_nan():
    dead = _map(rows=3, cols=3)
    dead["z"] = [[float("nan")] * 3 for _ in range(3)]
    assert render.render_map(dead, "A", "t") is None
    assert render.render_map({}, "A", "t") is None


def test_unknown_colormap_falls_back_instead_of_raising():
    assert render.render_map(_map(), "A", "t", cmap="not-a-cmap")


def test_auto_figure_prefers_the_map_when_there_is_one():
    snapshot = {"reads": ["LOCKIN.X"], "trace": _trace(),
                "maps": {"LOCKIN.X": _map()}}
    assert render.auto_figure(snapshot, "LOCKIN.X", "t")
    # with no map (a 1-D sweep, or a map with no committed rows yet) the
    # fast-axis trace is the picture that represents the sweep
    del snapshot["maps"]
    assert render.auto_figure(snapshot, "LOCKIN.X", "t")
    assert render.auto_figure({}, "LOCKIN.X", "t") is None


def test_safe_render_swallows_a_broken_figure():
    def boom(*a, **k):
        raise ValueError("no")
    assert render.safe_render(boom) is None


def test_readable_reads_falls_back_to_the_trace():
    assert render.readable_reads({"reads": ["A", "B"]}) == ["A", "B"]
    assert render.readable_reads({"trace": _trace()}) == ["LOCKIN.X",
                                                          "LOCKIN.Y"]
    assert render.readable_reads({}) == []


def test_series_palette_is_fixed_and_long_enough():
    # colour follows the entity, never its rank: the list is indexed, not
    # cycled through a generator
    assert len(render.SERIES) == 8
    assert render.SERIES[0] == "#2a78d6"
    assert render.DEFAULT_CMAP in render.CMAPS


# --------------------------------------------------------------- routing --
def test_every_rig_event_kind_maps_to_a_preference():
    from unisweep_bot import ingest
    from unisweep_bot.formatting import DEFAULT_PREFS
    for kind, pref in ingest.EVENT_PREF.items():
        assert pref in DEFAULT_PREFS, (kind, pref)
    # the kinds the rig actually emits are all covered
    for kind in ("started", "finished", "error", "guard", "paused",
                 "resumed", "file"):
        assert kind in ingest.EVENT_PREF


def test_inline_markup_is_built_from_the_stored_spec():
    from unisweep_bot import dispatch
    spec = [[{"text": "Menu", "data": "menu:home"},
             {"text": "Plot", "data": "menu:plot"}]]
    markup = dispatch._markup(spec)
    assert markup.inline_keyboard[0][0].callback_data == "menu:home"
    assert dispatch._markup(json.dumps(spec)) is not None
    assert dispatch._markup(None) is None
    assert dispatch._markup("not json") is None
    assert dispatch._markup([[{"oops": 1}]]) is None


def test_callback_data_fits_telegram_limit():
    from unisweep_bot import handlers
    rig_id = "f" * 32                        # a uuid4 hex rig id
    for data in (f"rig:{rig_id}", f"unlinkok:{rig_id}",
                 "pref:progress_min", "cmap:coolwarm", "map:23",
                 "ctlok:to_zero", "fresh:table", "menu:home"):
        assert len(data.encode()) <= 64, data
    assert handlers.CONTROL_LABEL["stop"]


# --------------------------------------------------------------- pairing --
def test_wrong_codes_are_rate_limited_per_chat():
    from unisweep_bot import config, handlers
    handlers._ATTEMPTS.clear()
    chat = 4242
    for _ in range(config.PAIR_MAX_ATTEMPTS):
        assert not handlers._too_many_attempts(chat)
        handlers._record_attempt(chat)
    # 900 000 possibilities against a handful of guesses per window
    assert handlers._too_many_attempts(chat)
    assert not handlers._too_many_attempts(chat + 1)
    handlers._ATTEMPTS.clear()


def test_display_name_survives_a_user_with_no_username():
    from unisweep_bot import handlers

    class _User:
        def __init__(self, first, last=None, username=None):
            self.first_name, self.last_name = first, last
            self.username = username

    class _Update:
        def __init__(self, user):
            self.effective_user = user

    assert handlers._display_name(_Update(_User("Misha", "K", "misha"))) == \
        "Misha K (@misha)"
    assert handlers._display_name(_Update(_User("Ada"))) == "Ada"
    assert handlers._display_name(_Update(None)) == ""


if __name__ == "__main__":
    if not HAVE_SERVER:
        sys.exit(0)
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
