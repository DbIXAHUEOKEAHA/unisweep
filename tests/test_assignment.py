"""The assignment object: what a session is for, and who decides it is done.

The question these answer is narrow and load-bearing: can an assistant's
report talk its way past an acceptance criterion? It must not. Coverage
is read out of the journal — the runs actually executed — and a reported
value may only supply what the journal cannot know.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from unisweep.agent.assignment import (Criterion, facts_from_programs,
                                       facts_from_runs, list_assignments,
                                       load_assignment, merge_facts,
                                       parse_assignment)
from unisweep.agent.session import AgentSession, SessionError
from unisweep.core.config import AxisProgram, CountMode, SweepProgram
from unisweep.core.journal import Journal
from unisweep.core.labprofile import LabProfile

TEXT = """# Hall density at base temperature

## Question
What is the carrier density at Vbg = -40 V, and how sure are you?

## Sample
Monolayer graphene on 300 nm SiO2, back gate only. Cold.

## Constraints
- Do not exceed the gate limit you measure.
- Finish inside two hours.

## Acceptance
- field_span >= 1.8 — the Hall slope needs at least +-0.9 T
- points >= 150
- density_uncertainty <= 0.05 — 5% or better
- 2 +  — deliberately broken

## Deliverables
- The density, with an uncertainty.

## Wiring
Contacts 3 and 7 are the Hall pair.
"""


def written(text=TEXT, name="hall"):
    core = tempfile.mkdtemp()
    folder = os.path.join(core, "assignments")
    os.makedirs(folder)
    with open(os.path.join(folder, f"{name}.md"), "w", encoding="utf-8") as fh:
        fh.write(text)
    return core


# ---------------------------------------------------------------------------
# the file
# ---------------------------------------------------------------------------
def test_an_assignment_parses_into_its_parts():
    task = parse_assignment(TEXT, name="hall")
    assert task.title == "Hall density at base temperature"
    assert "carrier density" in task.question
    assert task.sample.startswith("Monolayer graphene")
    assert len(task.constraints) == 2
    assert task.deliverables == ("The density, with an uncertainty.",)
    assert [c.test for c in task.criteria][:3] == [
        "field_span >= 1.8", "points >= 150", "density_uncertainty <= 0.05"]
    assert task.criteria[0].why.startswith("the Hall slope")
    assert task.criteria[0].wants == ("field_span",)


def test_an_unknown_section_is_kept_rather_than_dropped():
    """A supervisor writing something the parser has no field for must not
    lose it: the assistant is shown every section either way."""
    task = parse_assignment(TEXT, name="hall")
    assert dict(task.extra)["Wiring"] == "Contacts 3 and 7 are the Hall pair."


def test_a_broken_criterion_is_reported_not_silently_dropped():
    """Dropping it would quietly delete a requirement."""
    task = parse_assignment(TEXT, name="hall")
    broken = task.criteria[3]
    assert broken.expr is None and broken.error
    verdict = broken.check({"anything": 1.0})
    assert verdict["met"] is False
    assert "does not compile" in verdict["reason"]


def test_load_and_list(tmp_path=None):
    core = written()
    assert [a["name"] for a in list_assignments(core)] == ["hall"]
    assert load_assignment(core, "hall").title.startswith("Hall density")
    assert load_assignment(core, "hall.md").name == "hall"
    with pytest.raises(Exception) as excinfo:
        load_assignment(core, "nope")
    assert "Available: hall" in str(excinfo.value)


# ---------------------------------------------------------------------------
# facts
# ---------------------------------------------------------------------------
def run_record(**kw):
    base = {
        "run_id": "r1", "points": 100, "stopped": False,
        "started_at": "2026-09-22T10:00:00", "finished_at": "2026-09-22T10:02:00",
        "program": {"axes": [{"device": "MAG", "parameter": "field",
                              "start": -1.0, "stop": 1.0}],
                    "reads": ["LOCK.x"]},
    }
    base.update(kw)
    return base


def test_facts_come_from_what_the_runs_actually_did():
    facts = facts_from_runs([run_record(), run_record(
        run_id="r2", points=73, stopped=True,
        program={"axes": [{"device": "MAG", "parameter": "field",
                           "start": 0.0, "stop": 2.5}],
                 "reads": ["LOCK.y"]})])
    assert facts["runs"] == 2
    assert facts["points"] == 173
    assert facts["stopped"] == 1.0            # any stopped run taints the set
    assert facts["field_min"] == -1.0 and facts["field_max"] == 2.5
    assert facts["field_span"] == 3.5         # union across the cited runs
    assert facts["read_LOCK_x"] == 1.0 and facts["read_LOCK_y"] == 1.0
    assert facts["duration_s"] == 240.0        # summed over the cited runs


def test_a_plan_predicts_the_same_facts_before_it_runs():
    predicted = facts_from_programs([
        {"planned_points": 200, "estimated_seconds": 60,
         "program": {"axes": [{"parameter": "field", "start": -1.0,
                               "stop": 1.0}], "reads": ["LOCK.x"]}}])
    assert predicted["points"] == 200
    assert predicted["field_span"] == 2.0
    assert predicted["read_LOCK_x"] == 1.0


# ---------------------------------------------------------------------------
# the asymmetry that makes acceptance mean anything
# ---------------------------------------------------------------------------
def test_a_reported_fact_cannot_overwrite_a_measured_one():
    """Otherwise a criterion about how far the field was swept would be
    checked against the claim instead of against the sweep."""
    measured = facts_from_runs([run_record()])          # field_span == 2.0
    facts, refused = merge_facts(measured, {"field_span": 99.0,
                                            "density_uncertainty": 0.03})
    assert facts["field_span"] == 2.0                   # the sweep, not the claim
    assert facts["density_uncertainty"] == 0.03         # only it can know this
    assert refused[0]["name"] == "field_span"
    assert refused[0]["measured"] == 2.0
    assert refused[0]["reported"] == 99.0


def test_evidence_that_is_not_a_number_is_refused():
    facts, refused = merge_facts({}, {"snr": "excellent"})
    assert "snr" not in facts
    assert refused[0]["reason"] == "not a number"


def test_a_criterion_with_no_fact_behind_it_is_not_met():
    """Silence must not read as success."""
    verdict = Criterion.parse("density_uncertainty <= 0.05").check(
        {"points": 500.0})
    assert verdict["met"] is False
    assert "density_uncertainty" in verdict["reason"]
    assert verdict["missing"] == ["density_uncertainty"]


# ---------------------------------------------------------------------------
# through the session
# ---------------------------------------------------------------------------
class StubApp:
    def __init__(self, core_dir):
        self.core_dir = core_dir
        self.registry = None
        self.profile = LabProfile.empty()


def session_on(core):
    return AgentSession(StubApp(core), bridge=object())


def journal_a_run(core, run_id, start, stop, points):
    program = SweepProgram(
        axes=(AxisProgram(device="MAG", parameter="field", start=start,
                          stop=stop, rate=0.05, delay=0.01,
                          count_mode=CountMode.STEP),),
        reads=("LOCK.x",))

    class Provenance:
        pass

    prov = Provenance()
    prov.run_id = run_id
    prov.program = program
    prov.started_at = "2026-09-22T10:00:00"
    prov.env = {}
    prov.devices = {}
    prov.profile = None
    journal = Journal(core)
    journal.start_run(prov, dimensions=1)
    journal.finish_run(run_id, stopped=False, points=points)
    return run_id


def test_get_assignment_lists_then_serves():
    core = written()
    session = session_on(core)
    listing = session.get_assignment()
    assert [a["name"] for a in listing["assignments"]] == ["hall"]
    served = session.get_assignment("hall")
    assert served["question"].startswith("What is the carrier density")
    assert served["acceptance"][0]["needs"] == ["field_span"]


def test_report_finding_is_judged_by_the_runs_not_by_the_claim():
    core = written()
    session = session_on(core)
    journal_a_run(core, "r-short", -0.5, 0.5, 400)      # field_span 1.0

    out = session.report_finding(
        claim="n = 3.5e12 cm^-2", assignment="hall", value=3.5e12,
        uncertainty=0.02, runs=["r-short"],
        evidence={"density_uncertainty": 0.02, "field_span": 5.0})

    assert out["accepted"] is False
    coverage = [c for c in out["criteria"] if c["test"].startswith("field_span")]
    assert coverage[0]["met"] is False           # 1.0 T swept, 1.8 required
    assert coverage[0]["using"]["field_span"] == 1.0
    assert out["refused_evidence"][0]["name"] == "field_span"
    assert out["journalled"] is True             # recorded even when refused


def test_a_finding_is_accepted_when_the_runs_actually_cover_it():
    core = written()
    session = session_on(core)
    journal_a_run(core, "r-wide", -1.0, 1.0, 200)       # field_span 2.0

    out = session.report_finding(
        claim="n = 3.5e12 cm^-2", assignment="hall", value=3.5e12,
        runs=["r-wide"], evidence={"density_uncertainty": 0.02})
    unmet = [c for c in out["criteria"] if not c["met"]]
    # only the deliberately broken criterion in the fixture remains
    assert [c["test"] for c in unmet] == ["2 +"]


def test_an_unknown_run_id_is_refused_rather_than_ignored():
    core = written()
    session = session_on(core)
    with pytest.raises(SessionError) as excinfo:
        session.report_finding(claim="something", runs=["not-a-run"])
    assert "not-a-run" in str(excinfo.value)


def test_a_finding_with_no_assignment_is_recorded_but_not_judged():
    core = written()
    session = session_on(core)
    out = session.report_finding(claim="the helium was low")
    assert out["accepted"] is False
    assert "nothing to accept against" in out["accepted_why"]
    assert out["journalled"] is True


def test_propose_plan_prices_steps_and_checks_coverage_before_running():
    core = written()
    session = session_on(core)
    plan = session.propose_plan(assignment="hall", steps=[
        {"purpose": "Hall slope",
         "program": {"axes": [{"device": "MAG", "parameter": "field",
                               "start": -0.5, "stop": 0.5, "rate": 0.01,
                               "delay": 0.01, "count_mode": "step"}],
                     "reads": ["LOCK.x"]}}])
    assert plan["total_points"] > 0
    coverage = [c for c in plan["would_satisfy"]
                if c["test"].startswith("field_span")]
    assert coverage[0]["met"] is False           # +-0.5 T cannot ever satisfy it
    assert plan["predicted_facts"]["field_span"] == 1.0


def test_a_plan_needs_a_step():
    session = session_on(written())
    with pytest.raises(SessionError):
        session.propose_plan(steps=[])
