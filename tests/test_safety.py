"""Lab profile, limit policy, and reacting to a measured value.

The three questions these answer:

* does the profile describe the rig faithfully and round-trip? (labprofile)
* can anything reach an instrument outside its envelope? (limits)
* can a sweep react to what it just *measured*? (the per-point script)

The last one is the interesting one: it is what turns "creep the gate up
until the leakage goes exponential, then stop creeping" from a thing a
person watches into a thing the software does — and it is deliberately
the user's own Python rather than a subsystem, because Unisweep has no
idea which of its float channels is a leakage current.
"""

import math
import os
import queue
import sys
import tempfile
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest

from unisweep.core import events as ev
from unisweep.core.config import (AxisProgram, CountMode, LiveProgram,
                                  SweepProgram)
from unisweep.core.devices import DeviceRegistry, DriverAdapter
from unisweep.core.engine import SweepEngine
from unisweep.core.labprofile import (DerivedEvaluator, DeviceSpec,
                                      LabProfile, ParameterSpec,
                                      channel_ident)
from unisweep.core.limits import (LimitPolicy, LimitViolation,
                                  estimate_program, validate_program)


# ---------------------------------------------------------------------------
# a gate line whose leakage really does run away
# ---------------------------------------------------------------------------
class LeakyGate:
    """Voltage source whose leakage current is exponential in |V|.

    ``Leak`` crosses 2 nA just below 3.9 V, so a script watching for 2 nA
    has a definite, checkable answer.
    """

    def __init__(self, adress="GATE", scale=0.5, floor=1e-12):
        self.adress = adress
        self.set_options = ["Volt"]
        self.get_options = ["Volt", "Leak"]
        self.eps = [1e-9]
        self.sweepable = [False]
        self.maxspeed = [None]
        self._v = 0.0
        self.scale = scale
        self.floor = floor
        self.set_log = []

    def set_Volt(self, value=None, speed=None):
        self._v = float(value)
        self.set_log.append(float(value))

    def Volt(self):
        return self._v

    def Leak(self):
        return self.floor * math.exp(abs(self._v) / self.scale)


class PolicyRegistry(DeviceRegistry):
    """Registry over mock devices that still honours a limit policy."""

    def __init__(self, core_dir, mocks, policy=None):
        self.core_dir = core_dir
        self._mocks = mocks
        self._adapters = {}
        self._lock = threading.Lock()
        self.policy = policy
        self.types = {name: name for name in mocks}

    def connect(self, address):
        with self._lock:
            if address not in self._adapters:
                self._adapters[address] = DriverAdapter(
                    address, self._mocks[address], policy=self.policy)
            return self._adapters[address]


def run(program, mocks, profile=None, policy=None, timeout=30):
    tmp = tempfile.mkdtemp(prefix="unisweep_safety_")
    live = LiveProgram(program)
    q = queue.Queue()
    registry = PolicyRegistry(tmp, mocks, policy)
    engine = SweepEngine(live, registry, tmp, q, profile=profile)
    engine.start()
    engine.join(timeout)
    assert not engine.is_alive(), "engine did not finish"
    out = []
    while not q.empty():
        out.append(q.get_nowait())
    return out, tmp


def gate_axis(**kw):
    base = dict(device="GATE", parameter="Volt", start=0.0, stop=10.0,
                rate=0.5, delay=0.005, count_mode=CountMode.STEP)
    base.update(kw)
    return AxisProgram(**base)


GATE_PROFILE = {
    "lab": "test rig",
    "constants": {"I_ac": 100e-9},
    "devices": {
        "GATE": {
            "alias": "gate",
            "role": "back gate source-measure unit",
            "parameters": {
                "Volt": {"alias": "Vbg", "unit": "V",
                         "quantity": "back gate voltage",
                         "min": -12.0, "max": 12.0, "max_rate": 1.0},
                "Leak": {"alias": "Ileak", "unit": "A",
                         "quantity": "gate leakage", "settable": False},
            },
        },
    },
}


def profile_of(**overrides):
    data = dict(GATE_PROFILE)
    data.update(overrides)
    return LabProfile.from_dict(data)


# ---------------------------------------------------------------------------
# lab profile
# ---------------------------------------------------------------------------
def test_absent_profile_is_permissive_and_changes_nothing():
    tmp = tempfile.mkdtemp()
    profile = LabProfile.load(tmp)
    assert profile.is_empty
    policy = LimitPolicy(profile)
    # anything goes, and no speed is invented
    assert policy.check_set("ANY", "Volt", 1e9) == (1e9, None)
    assert validate_program(SweepProgram(axes=(gate_axis(),)), profile) == []


def test_profile_round_trips_through_json():
    tmp = tempfile.mkdtemp()
    original = profile_of()
    path = original.save(tmp)
    assert os.path.basename(path) == "lab_profile.json"
    again = LabProfile.load(tmp)
    assert again.lab == "test rig"
    assert again.constants["I_ac"] == 100e-9
    spec = again.spec("GATE", "Volt")
    assert spec.alias == "Vbg" and spec.maximum == 12.0
    assert again.spec("GATE", "Leak").settable is False


def test_resolve_accepts_alias_device_alias_and_address():
    profile = profile_of()
    assert profile.resolve("Vbg") == ("GATE", "Volt")
    assert profile.resolve("gate.Volt") == ("GATE", "Volt")
    assert profile.resolve("GATE.Volt") == ("GATE", "Volt")
    assert profile.resolve("nonsense") is None
    assert profile.label("GATE", "Volt") == "Vbg [V]"
    assert profile.label("GATE", "Unknown") == "GATE.Unknown"


def test_validate_reports_contradictions():
    profile = LabProfile.from_dict({"devices": {"A": {"parameters": {
        "p": {"alias": "dup", "min": 5, "max": 1, "safe_value": 99,
              "max_rate": -1}}},
        "B": {"parameters": {"q": {"alias": "dup"}}}}})
    messages = " | ".join(p.message for p in profile.validate()
                          if p.level == "error")
    assert "above max" in messages
    assert "max_rate must be positive" in messages
    assert "outside" in messages
    assert "already used" in messages


def test_channel_ident_is_a_valid_identifier():
    assert channel_ident("GPIB1::8::INSTR.x") == "GPIB1_8_INSTR_x"
    assert channel_ident("2600.A").isidentifier()


# ---------------------------------------------------------------------------
# limit policy
# ---------------------------------------------------------------------------
def test_limits_refuse_out_of_range_and_clamp_the_rate():
    policy = LimitPolicy(profile_of())
    value, speed = policy.check_set("GATE", "Volt", 5.0, speed=99.0)
    assert (value, speed) == (5.0, 1.0)          # clamped to max_rate
    with pytest.raises(LimitViolation) as excinfo:
        policy.check_set("GATE", "Volt", 40.0)
    assert "outside the allowed range" in str(excinfo.value)


def test_a_safety_move_is_clamped_never_refused():
    """A protection mechanism the limits can veto is worse than none."""
    policy = LimitPolicy(profile_of())
    assert policy.check_set("GATE", "Volt", 40.0, safety=True)[0] == 12.0
    assert policy.check_set("GATE", "Leak", 0.0, safety=True)[0] == 0.0


def test_readonly_parameters_and_readonly_tier_are_refused():
    policy = LimitPolicy(profile_of())
    with pytest.raises(LimitViolation):
        policy.check_set("GATE", "Leak", 1.0)
    tier = LimitPolicy(profile_of(autonomy="readonly"))
    with pytest.raises(LimitViolation) as excinfo:
        tier.check_set("GATE", "Volt", 0.5)
    assert "read-only autonomy tier" in str(excinfo.value)


def test_max_step_bounds_jumps_but_not_ramps():
    profile = LabProfile.empty().with_parameter(
        "GATE", ParameterSpec(parameter="Volt", max_step=0.1))
    policy = LimitPolicy(profile)
    policy.check_set("GATE", "Volt", 0.05, current=0.0)          # fine
    with pytest.raises(LimitViolation) as excinfo:
        policy.check_set("GATE", "Volt", 1.0, current=0.0)
    assert "max_step" in str(excinfo.value)
    # the same move on a SELF-RAMPING instrument is a travel instruction
    assert policy.check_set("GATE", "Volt", 1.0, speed=0.2, current=0.0,
                            ramps=True) == (1.0, 0.2)
    # ...but handing a rate to a stepwise source does not make it ramp
    with pytest.raises(LimitViolation):
        policy.check_set("GATE", "Volt", 1.0, speed=0.2, current=0.0)


def gate_like_the_real_one():
    """Both a step ceiling and a rate ceiling — the shape that broke."""
    return LabProfile.empty().with_parameter(
        "GATE", ParameterSpec(parameter="Volt", minimum=-60.0, maximum=60.0,
                              max_step=1.0, max_rate=5.0))


def test_a_max_rate_does_not_disarm_the_step_ceiling():
    """The regression, and it was live on the rig.

    A ``set`` with no speed had one derived from ``max_rate`` before the
    jump check ran, and that check tested ``speed is None`` — so it never
    fired for any parameter carrying a rate. On the simulated rig those
    were exactly the two gate lines and nothing else: the only parameters
    where a single jump destroys the sample were the only ones with no
    step ceiling. An 83 V move was accepted in one command.
    """
    policy = LimitPolicy(gate_like_the_real_one())
    for kwargs in ({}, {"speed": None}, {"speed": 5.0}):
        with pytest.raises(LimitViolation) as excinfo:
            policy.check_set("GATE", "Volt", -40.0, current=43.0, **kwargs)
        assert "83" in str(excinfo.value)
    # a genuinely self-ramping instrument still travels the same distance
    assert policy.check_set("GATE", "Volt", -40.0, current=43.0,
                            ramps=True)[0] == -40.0
    # and a protective move is never refused, ramping or not
    assert policy.check_set("GATE", "Volt", 0.0, current=43.0,
                            safety=True)[0] == 0.0


def test_the_adapter_takes_ramping_from_the_driver_not_the_rate():
    """``ramps`` comes from the driver's own ``sweepable`` flag, which is
    the only thing that knows whether the instrument travels or arrives."""
    stepwise = LeakyGate()
    assert stepwise.sweepable == [False]
    adapter = PolicyRegistry(tempfile.mkdtemp(), {"GATE": stepwise},
                             LimitPolicy(gate_like_the_real_one())
                             ).connect("GATE")
    adapter.set("Volt", 0.5)
    with pytest.raises(LimitViolation):
        adapter.set("Volt", 40.0)
    assert stepwise.set_log == [0.5]              # never reached the device

    ramping = LeakyGate()
    ramping.sweepable = [True]
    twin = PolicyRegistry(tempfile.mkdtemp(), {"GATE": ramping},
                          LimitPolicy(gate_like_the_real_one())
                          ).connect("GATE")
    twin.set("Volt", 0.5)
    twin.set("Volt", 40.0)                        # travels, so allowed
    assert ramping.set_log == [0.5, 40.0]


def test_the_adapter_is_the_choke_point():
    """Every route to the hardware goes through DriverAdapter.set."""
    gate = LeakyGate()
    registry = PolicyRegistry(tempfile.mkdtemp(), {"GATE": gate},
                              LimitPolicy(profile_of()))
    adapter = registry.connect("GATE")
    adapter.set("Volt", 3.0)
    assert gate.set_log == [3.0]
    with pytest.raises(LimitViolation):
        adapter.set("Volt", 30.0)
    assert gate.set_log == [3.0]                 # never reached the device
    adapter.set("Volt", 30.0, safety=True)       # clamped instead
    assert gate.set_log == [3.0, 12.0]


def test_set_policy_reaches_already_connected_instruments():
    gate = LeakyGate()
    registry = PolicyRegistry(tempfile.mkdtemp(), {"GATE": gate})
    adapter = registry.connect("GATE")
    adapter.set("Volt", 30.0)                    # unbounded before
    registry.set_policy(LimitPolicy(profile_of()))
    assert adapter.policy is not None
    with pytest.raises(LimitViolation):
        adapter.set("Volt", 30.0)


# ---------------------------------------------------------------------------
# program pre-flight
# ---------------------------------------------------------------------------
def test_preflight_catches_an_out_of_range_endpoint():
    program = SweepProgram(axes=(gate_axis(stop=40.0),))
    errors = [p for p in validate_program(program, profile_of())
              if p.level == "error"]
    assert len(errors) == 1
    assert "stop 40 V is outside" in errors[0].message


def test_preflight_enforces_interlocks():
    profile = profile_of(interlocks={"max_points": 10,
                                     "max_duration_s": 1.0,
                                     "allow_script": False})
    program = SweepProgram(axes=(gate_axis(rate=0.01, delay=1.0),),
                           script="print(1)")
    messages = " | ".join(p.message for p in validate_program(program, profile)
                          if p.level == "error")
    assert "max_points" in messages
    assert "max_duration_s" in messages
    assert "allow_script=false" in messages


def test_preflight_forbids_sweeping_an_exclusive_pair_together():
    profile = LabProfile.from_dict({
        "devices": {
            "CRYO": {"parameters": {"Field": {"alias": "B"},
                                    "T_sample": {"alias": "T"}}}},
        "interlocks": {"exclusive_ramps": [["B", "T"]]}})
    program = SweepProgram(axes=(
        AxisProgram(device="CRYO", parameter="Field"),
        AxisProgram(device="CRYO", parameter="T_sample")))
    errors = [p for p in validate_program(program, profile)
              if p.level == "error"]
    assert errors and "forbids in one run" in errors[0].message


def test_estimate_counts_walks_and_dimensions():
    program = SweepProgram(axes=(
        gate_axis(start=0.0, stop=1.0, rate=0.5, delay=0.1),
        gate_axis(start=0.0, stop=1.0, rate=0.5, delay=0.1, walks=2)))
    points, seconds = estimate_program(program)
    assert points == 3 * 3 * 2
    assert seconds > 0


# ---------------------------------------------------------------------------
# derived channels — a reading convenience; the sweep never evaluates them
# ---------------------------------------------------------------------------
def test_derived_channels_resolve_through_each_other():
    profile = LabProfile.from_dict({
        "constants": {"I_ac": 100e-9},
        "devices": {"LI": {"parameters": {"x": {"alias": "Vxx"}}}},
        "derived": {"Rxx": {"expression": "Vxx / I_ac"},
                    "Rxx_kohm": {"expression": "Rxx / 1000"}}})
    evaluator = DerivedEvaluator(profile, ["LI.x"])
    values = evaluator.evaluate({"LI.x": 1e-3})
    assert values["Rxx"] == pytest.approx(1e4)
    assert values["Rxx_kohm"] == pytest.approx(10.0)


def test_a_broken_derived_expression_is_named_not_raised():
    profile = LabProfile.from_dict({
        "devices": {"LI": {"parameters": {"x": {"alias": "Vxx"}}}},
        "derived": {"bad": {"expression": "Vxx / nonexistent"},
                    "empty": {"expression": ""}}})
    evaluator = DerivedEvaluator(profile, ["LI.x"])
    assert set(evaluator.errors) == {"bad", "empty"}
    assert evaluator.evaluate({"LI.x": 1.0}) == {}


# ---------------------------------------------------------------------------
# the per-point script: where a measured value decides something
# ---------------------------------------------------------------------------
# Unisweep has no opinion about what a channel *means* — 'GPIB1.x' is a
# float, not a leakage current. Deciding that a number is too big is
# therefore the user's (or their assistant's) judgement, expressed in their
# own Python, rather than a subsystem with its own vocabulary. These pin
# down that the script has everything it needs to make that judgement.
# ---------------------------------------------------------------------------
def test_the_script_sees_the_row_it_just_measured():
    gate = LeakyGate()
    program = SweepProgram(
        axes=(gate_axis(stop=1.0, rate=0.5),), reads=("GATE.Leak",),
        script=("g = devices['GATE'].raw\n"
                "g.seen = dict(reads)\n"
                "g.seen_row = tuple(row)\n"
                "g.seen_columns = tuple(columns)\n"
                "g.seen_walk = walk\n"
                "g.seen_values = list(values)\n"))
    run(program, {"GATE": gate}, profile=profile_of())
    assert set(gate.seen) == {"GATE.Leak"}
    assert gate.seen["GATE.Leak"] > 0
    assert gate.seen_columns == ("time", "GATE.Volt_sweep", "GATE.Leak")
    assert gate.seen_row[-1] == gate.seen["GATE.Leak"]
    assert gate.seen_values == [1.0]              # the last setpoint
    assert gate.seen_walk == 1


def test_a_script_stops_the_sweep_when_a_reading_runs_away():
    """The gate-leakage story, in two lines of the user's own Python."""
    gate = LeakyGate()
    program = SweepProgram(
        axes=(gate_axis(rate=0.5),), reads=("GATE.Leak",),
        script=("if abs(reads['GATE.Leak']) > 2e-9:\n"
                "    stop()\n"))
    events, _ = run(program, {"GATE": gate}, profile=profile_of())
    finished = [e for e in events if isinstance(e, ev.SweepFinished)]
    assert finished and finished[0].stopped
    assert finished[0].points > 0                 # the data so far is kept
    assert 3.5 <= gate.set_log[-1] <= 4.0, gate.set_log[-1]


def test_a_script_can_pull_the_range_in_instead_of_stopping():
    """Retargeting the axis ends the walk and lets the sweep carry on —
    the live-edit machinery doing what a dedicated back-off would."""
    gate = LeakyGate()
    program = SweepProgram(
        axes=(gate_axis(rate=0.5),), reads=("GATE.Leak",),
        script=("if abs(reads['GATE.Leak']) > 2e-9:\n"
                "    live.update_axis(0, stop=values[0])\n"))
    events, _ = run(program, {"GATE": gate}, profile=profile_of())
    finished = [e for e in events if isinstance(e, ev.SweepFinished)]
    assert finished and not finished[0].stopped   # the sweep itself is fine
    assert 3.5 <= max(gate.set_log) <= 4.5, gate.set_log
    assert max(gate.set_log) < 10.0               # never reached the far end


def test_a_script_can_be_swapped_while_the_sweep_runs():
    gate = LeakyGate()
    tmp = tempfile.mkdtemp()
    live = LiveProgram(SweepProgram(
        axes=(gate_axis(rate=0.5, delay=0.05),), reads=("GATE.Leak",)))
    q = queue.Queue()
    registry = PolicyRegistry(tmp, {"GATE": gate})
    engine = SweepEngine(live, registry, tmp, q, profile=profile_of())

    def arm():
        deadline = time.perf_counter() + 30
        while gate.Volt() < 1.0 and time.perf_counter() < deadline:
            time.sleep(0.01)
        live.update(script=("if abs(reads['GATE.Leak']) > 2e-9:\n"
                            "    stop()\n"))

    engine.start()
    threading.Thread(target=arm, daemon=True).start()
    engine.join(60)
    assert not engine.is_alive()
    events = []
    while not q.empty():
        events.append(q.get_nowait())
    finished = [e for e in events if isinstance(e, ev.SweepFinished)]
    assert finished and finished[0].stopped
    assert gate.Volt() < 10.0


def test_a_broken_script_is_reported_once_and_the_sweep_survives():
    gate = LeakyGate()
    program = SweepProgram(
        axes=(gate_axis(stop=2.0, rate=0.5),), reads=("GATE.Leak",),
        script="reads['NOT.A.CHANNEL']\n")
    events, _ = run(program, {"GATE": gate}, profile=profile_of())
    finished = [e for e in events if isinstance(e, ev.SweepFinished)]
    assert finished and not finished[0].stopped
    assert gate.set_log[-1] == pytest.approx(2.0)   # ran to the end
    complaints = [e for e in events if isinstance(e, ev.SweepError)
                  and e.where == "script"]
    assert len(complaints) == 1                     # deduped, not per point


def test_scripts_are_allowed_by_default_so_a_profile_changes_nothing():
    """Installing a lab profile must not silently disable a feature the
    application already had."""
    assert LabProfile.empty().interlocks.allow_script is True
    assert profile_of().interlocks.allow_script is True


def test_a_profile_can_still_forbid_the_script_for_an_unattended_rig():
    gate = LeakyGate()
    profile = profile_of(interlocks={"allow_script": False})
    program = SweepProgram(axes=(gate_axis(stop=1.0),),
                           reads=("GATE.Leak",), script="pass")
    events, _ = run(program, {"GATE": gate}, profile=profile)
    assert gate.set_log == []                      # refused before any move
    fatal = [e for e in events if isinstance(e, ev.SweepError) and e.fatal]
    assert fatal and "allow_script" in fatal[0].message


# ---------------------------------------------------------------------------
# the engine refuses what the profile forbids
# ---------------------------------------------------------------------------
def test_engine_preflight_refuses_and_touches_nothing():
    gate = LeakyGate()
    program = SweepProgram(axes=(gate_axis(stop=40.0),),
                           reads=("GATE.Leak",))
    events, _ = run(program, {"GATE": gate}, profile=profile_of())
    assert gate.set_log == []                    # no instrument was touched
    assert not [e for e in events if isinstance(e, ev.PointMeasured)]
    fatal = [e for e in events if isinstance(e, ev.SweepError) and e.fatal]
    assert fatal and "refuses this sweep" in fatal[0].message


def test_runtime_limit_violation_stops_the_sweep_naming_the_device():
    profile = LabProfile.empty().with_parameter(
        "GATE", ParameterSpec(parameter="Volt", max_step=0.1))
    gate = LeakyGate()
    program = SweepProgram(axes=(gate_axis(stop=5.0, rate=0.5),))
    events, _ = run(program, {"GATE": gate}, profile=profile,
                    policy=LimitPolicy(profile))
    fatal = [e for e in events if isinstance(e, ev.SweepError) and e.fatal]
    assert fatal and "GATE.Volt" in fatal[0].message
    assert len(gate.set_log) == 1                # the first point only


def test_a_sweep_without_a_profile_behaves_exactly_as_before():
    gate = LeakyGate()
    program = SweepProgram(axes=(gate_axis(stop=2.0, rate=0.5),),
                           reads=("GATE.Leak",))
    events, _ = run(program, {"GATE": gate})
    assert gate.set_log == [0.0, 0.5, 1.0, 1.5, 2.0]
    finished = [e for e in events if isinstance(e, ev.SweepFinished)]
    assert finished and not finished[0].stopped
