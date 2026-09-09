"""The lab journal: runs record themselves; nobody is asked to type.

Two properties are worth pinning. The journal must be trustworthy later —
append-only, and never able to take a measurement down with it — and it
must carry everything the sweep already knew, because that record is all a
reader (a person, or an assistant asked in the morning) has to work out
what was going on and which runs belong together.
"""

import json
import os
import queue
import sqlite3
import sys
import tempfile
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from unisweep.core.config import (AxisProgram, CountMode, LiveProgram,
                                  SweepProgram)
from unisweep.core.engine import SweepEngine
from unisweep.core.journal import Journal
from unisweep.core.labprofile import LabProfile
from unisweep.core.provenance import RunProvenance
from tests.mock_driver import MockDevice
from tests.test_provenance import PROFILE, Registry


@pytest.fixture
def journal():
    return Journal(tempfile.mkdtemp())


def a_run(tmp, registry=None, **program_kw):
    base = dict(
        axes=(AxisProgram(device="M1", parameter="Volt", start=0.0,
                          stop=1.0, rate=0.5, delay=0.01),),
        reads=("M1.Curr",))
    base.update(program_kw)
    return RunProvenance(tmp, SweepProgram(**base),
                         LabProfile.from_dict(PROFILE), registry).capture()


# ---------------------------------------------------------------------------
def test_a_run_is_recorded_from_start_to_finish(journal):
    provenance = a_run(journal.core_dir)
    run_id = journal.start_run(provenance, dimensions=1)
    assert run_id == provenance.run_id

    live = journal.run(run_id)
    assert live["finished_at"] == "" and live["points"] == 0
    assert live["program"]["axes"][0]["device"] == "M1"

    journal.finish_run(run_id, stopped=False, points=42,
                       files=["/data/260908-1.csv"], directory="/data")
    done = journal.run(run_id)
    assert done["finished_at"] and done["points"] == 42
    assert done["stopped"] is False
    assert done["files"] == ["/data/260908-1.csv"]
    assert done["directory"] == "/data"


def test_the_entry_carries_everything_the_sweep_knew(journal):
    """No intent, no campaign — but the filename, the limits of every
    axis, the channels read, the condition, the per-point script and each
    instrument's logged settings, so intent can be *read out* of it."""
    device = MockDevice("M1")
    device.loggable = ["Volt", "Curr"]
    registry = Registry(journal.core_dir, {"M1": device})
    provenance = a_run(
        journal.core_dir, registry,
        filename="dirac_map",
        condition="x**2 + y**2 <= 25",
        script="if abs(reads['M1.Curr']) > 2e-9:\n    stop()")
    journal.start_run(provenance, dimensions=1)
    text = open(journal.markdown_path(), encoding="utf-8").read()

    assert "dirac_map" in text
    assert "- **axis** — `M1.Volt` 0 → 1" in text
    assert "0.5/s" in text and "0.01 s/point" in text
    assert "`M1.Curr`" in text
    assert "x**2 + y**2 <= 25" in text
    assert "```python" in text and "stop()" in text
    assert "MockDevice" in text and "(gate)" in text
    assert "- Volt: 0.0" in text                  # a logged setting
    assert "sample: id GR-1" in text

    record = journal.run(provenance.run_id)
    assert record["program"]["filename"] == "dirac_map"
    assert record["program"]["condition"] == "x**2 + y**2 <= 25"
    assert "stop()" in record["program"]["script"]
    assert record["instruments"]["M1"]["loggable"]["Curr"] == 0.0
    assert record["lab"] == "test rig"
    assert record["sample"] == {"id": "GR-1"}


def test_an_axis_that_is_not_a_plain_ramp_still_reads_back(journal):
    provenance = a_run(journal.core_dir, axes=(
        AxisProgram(device="M1", parameter="Volt", start=-2.0, stop=2.0,
                    rate=0.05, delay=0.2, count_mode=CountMode.STEP,
                    back_rate=0.1, walks=4, snake=True),))
    journal.start_run(provenance, dimensions=1)
    text = open(journal.markdown_path(), encoding="utf-8").read()
    assert "-2 → 2" in text
    assert "step 0.05" in text
    assert "back 0.1/s" in text
    assert "4 walks" in text and "snake" in text


def test_the_markdown_is_append_only(journal):
    provenance = a_run(journal.core_dir)
    journal.start_run(provenance, dimensions=1)
    after_start = open(journal.markdown_path(), encoding="utf-8").read()
    journal.note("the cryostat was still settling")
    journal.finish_run(provenance.run_id, points=7, files=["a.csv"])
    text = open(journal.markdown_path(), encoding="utf-8").read()

    assert text.startswith("# Lab journal — ")
    assert text.startswith(after_start), "earlier entries must never move"
    assert "the cryostat was still settling" in text
    assert "7 points, 1 file(s)" in text


def test_a_stopped_run_says_so(journal):
    provenance = a_run(journal.core_dir)
    journal.start_run(provenance)
    journal.finish_run(provenance.run_id, stopped=True, points=3)
    assert journal.run(provenance.run_id)["stopped"] is True
    assert "stopped" in open(journal.markdown_path(), encoding="utf-8").read()


def test_notes_attach_to_a_run(journal):
    """Notes are optional and nothing depends on them: they are where an
    assistant writes a conclusion, not where a run gets its meaning."""
    provenance = a_run(journal.core_dir)
    journal.start_run(provenance)
    assert journal.note("leakage onset near +4 V",
                        run_id=provenance.run_id) is True
    journal.note("sample intact after thermal cycling", author="misha")
    assert journal.note("   ") is False              # nothing to record

    on_run = journal.notes(run_id=provenance.run_id)
    assert len(on_run) == 1 and "+4 V" in on_run[0]["text"]
    assert len(journal.notes()) == 2
    assert journal.notes()[0]["author"] == "misha"   # newest first


def test_runs_are_listed_newest_first_and_can_start_from_a_date(journal):
    ids = []
    for day in ("2026-01-01T09:00:00", "2026-01-02T09:00:00",
                "2026-01-03T09:00:00"):
        provenance = a_run(journal.core_dir)
        provenance.started_at = day       # three runs, three days
        journal.start_run(provenance)
        journal.finish_run(provenance.run_id, points=1)
        ids.append(provenance.run_id)

    assert [r["run_id"] for r in journal.runs()] == list(reversed(ids))
    assert len(journal.runs(limit=1)) == 1
    assert len(journal.runs(since="2026-01-02")) == 2
    assert journal.runs(since="2999-01-01") == []


def test_a_run_can_say_which_runs_it_came_from(journal):
    """The DAG: the Landau fan records that it used the safe gate range
    established earlier."""
    first = a_run(journal.core_dir)
    journal.start_run(first)
    journal.finish_run(first.run_id, points=20)

    second = a_run(journal.core_dir)
    journal.start_run(second, derived_from=[first.run_id])
    assert journal.run(second.run_id)["derived_from"] == [first.run_id]


def test_an_unwritable_journal_reports_rather_than_raises():
    """It is built on the measurement thread. A bad disk is a message."""
    blocked = os.path.join(tempfile.mkdtemp(), "a_file")
    open(blocked, "w").close()                   # a file where a dir goes
    journal = Journal(blocked)
    assert journal.last_error
    assert journal.note("this cannot be written") is False
    assert journal.runs() == []
    provenance = a_run(tempfile.mkdtemp())
    journal.start_run(provenance)                # must not raise
    journal.finish_run(provenance.run_id, points=1)


def test_a_journal_written_by_older_code_keeps_its_rows(journal):
    """An append-only log must survive the code growing a column."""
    path = journal.db_path
    os.remove(path)
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE runs (run_id TEXT PRIMARY KEY,"
                     " started_at TEXT, intent TEXT)")
        conn.execute("INSERT INTO runs VALUES ('old-1','2026-01-01','why')")

    reopened = Journal(journal.core_dir)
    assert not reopened.last_error
    provenance = a_run(reopened.core_dir)
    reopened.start_run(provenance, dimensions=1)
    assert {r["run_id"] for r in reopened.runs()} == {"old-1",
                                                     provenance.run_id}
    assert reopened.run(provenance.run_id)["instruments"] == {}


def test_two_threads_writing_at_once_do_not_collide(journal):
    """The engine thread finishes a run while an assistant writes a note."""
    errors = []

    def writer(n):
        try:
            for i in range(20):
                journal.note(f"thread {n} note {i}")
        except Exception as exc:                 # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=writer, args=(n,)) for n in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(30)
    assert not errors
    assert len(journal.notes(limit=200)) == 80


def test_asking_for_a_run_that_is_not_there(journal):
    assert journal.run("nope") is None


# ---------------------------------------------------------------------------
# the engine files its own runs
# ---------------------------------------------------------------------------
def test_a_sweep_records_itself_in_the_journal():
    tmp = tempfile.mkdtemp()
    device = MockDevice("M1")
    device.loggable = ["Volt"]
    engine = SweepEngine(
        LiveProgram(SweepProgram(
            axes=(AxisProgram(device="M1", parameter="Volt", start=0.0,
                              stop=0.4, rate=0.1, delay=0.005,
                              count_mode=CountMode.STEP),),
            reads=("M1.Curr",))),
        Registry(tmp, {"M1": device}), tmp, queue.Queue(),
        profile=LabProfile.from_dict(PROFILE))
    engine.start()
    engine.join(30)

    record = Journal(tmp).run(engine.provenance.run_id)
    assert record is not None
    assert record["points"] == 5
    assert record["stopped"] is False
    assert record["dimensions"] == 1
    assert len(record["files"]) == 1
    assert record["files"][0].endswith(".csv")
    assert record["lab"] == "test rig"
    assert record["program"]["reads"] == ["M1.Curr"]
    assert "Volt" in record["instruments"]["M1"]["loggable"]
    text = open(Journal(tmp).markdown_path(), encoding="utf-8").read()
    assert "`M1.Volt` 0 → 0.4" in text and "5 points" in text
