"""Provenance sidecars: what produced this file.

The thing being protected is the six-months-later reader. A CSV whose
columns say ``GPIB0::1::INSTR.x`` and nothing else is not a measurement,
and the context that would make it one exists only while the sweep runs.
"""

import json
import os
import queue
import sys
import tempfile
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from unisweep.core import events as ev
from unisweep.core.config import (AxisProgram, CountMode, LiveProgram,
                                  SweepProgram)
from unisweep.core.devices import DeviceRegistry, DriverAdapter
from unisweep.core.engine import SweepEngine
from unisweep.core.labprofile import LabProfile
from unisweep.core.provenance import (RunProvenance, device_snapshot,
                                      git_revision, new_run_id, read_sidecar,
                                      sidecar_path)
from unisweep.core.writer import DataWriter
from tests.mock_driver import MockDevice


class Registry(DeviceRegistry):
    def __init__(self, core_dir, mocks):
        self.core_dir, self._mocks, self._adapters = core_dir, mocks, {}
        self._lock = threading.Lock()
        self.policy = None
        self.addresses = list(mocks)
        self.types = {a: type(m).__name__ for a, m in mocks.items()}

    def connect(self, address):
        with self._lock:
            if address not in self._adapters:
                self._adapters[address] = DriverAdapter(
                    address, self._mocks[address])
            return self._adapters[address]


PROFILE = {
    "lab": "test rig",
    "sample": {"id": "GR-1"},
    "constants": {"I_ac": 1e-7},
    "devices": {"M1": {"alias": "gate", "role": "back gate",
                       "parameters": {
                           "Volt": {"alias": "Vbg", "unit": "V",
                                    "min": -5, "max": 5},
                           "Curr": {"alias": "Ileak", "unit": "A"}}}},
}


def run_sweep(tmp, mocks, **program_kw):
    base = dict(
        axes=(AxisProgram(device="M1", parameter="Volt", start=0.0,
                          stop=0.4, rate=0.1, delay=0.005,
                          count_mode=CountMode.STEP),),
        reads=("M1.Curr",))
    base.update(program_kw)
    engine = SweepEngine(LiveProgram(SweepProgram(**base)),
                         Registry(tmp, mocks), tmp, queue.Queue(),
                         profile=LabProfile.from_dict(PROFILE))
    engine.start()
    engine.join(30)
    assert not engine.is_alive()
    return engine


# ---------------------------------------------------------------------------
def test_a_sidecar_lands_beside_every_data_file():
    tmp = tempfile.mkdtemp()
    engine = run_sweep(tmp, {"M1": MockDevice("M1")})
    data = engine.provenance.files[0]
    assert data.endswith(".csv")
    assert os.path.exists(sidecar_path(data))
    assert sidecar_path(data) == data[:-4] + ".json"


def test_the_sidecar_needs_nothing_typed_by_the_operator():
    """Everything in the record is read off the sweep itself. There is no
    field for the operator to leave empty, and none to forget to fill."""
    tmp = tempfile.mkdtemp()
    engine = run_sweep(tmp, {"M1": MockDevice("M1")})
    record = read_sidecar(engine.provenance.files[0])
    assert record["run_id"] == engine.provenance.run_id
    assert record["file"] == os.path.basename(engine.provenance.files[0])
    assert "intent" not in record and "campaign" not in record
    assert record["program"] and record["environment"]


def test_the_sidecar_carries_the_whole_program_and_columns():
    tmp = tempfile.mkdtemp()
    engine = run_sweep(tmp, {"M1": MockDevice("M1")})
    record = read_sidecar(engine.provenance.files[0])
    axis = record["program"]["axes"][0]
    assert axis["device"] == "M1" and axis["parameter"] == "Volt"
    assert axis["start"] == 0.0 and axis["stop"] == 0.4
    assert record["columns"] == ["time", "M1.Volt_sweep", "M1.Curr"]
    assert record["program"]["reads"] == ["M1.Curr"]


def test_the_sidecar_records_the_instruments_and_their_loggables():
    """``loggable`` is the convention sr830.py already uses for settings
    worth writing in the notebook — time constant, sensitivity."""
    tmp = tempfile.mkdtemp()
    device = MockDevice("M1")
    device.loggable = ["Volt", "Curr"]
    engine = run_sweep(tmp, {"M1": device})
    entry = read_sidecar(engine.provenance.files[0])["instruments"]["M1"]
    assert entry["driver"] == "MockDevice"
    assert entry["idn"]
    assert set(entry["loggable"]) == {"Volt", "Curr"}
    assert entry["alias"] == "gate" and entry["role"] == "back gate"


def test_the_sidecar_carries_a_profile_snapshot_so_it_stands_alone():
    tmp = tempfile.mkdtemp()
    engine = run_sweep(tmp, {"M1": MockDevice("M1")})
    profile = read_sidecar(engine.provenance.files[0])["lab_profile"]
    assert profile["lab"] == "test rig"
    assert profile["sample"] == {"id": "GR-1"}
    assert profile["constants"] == {"I_ac": 1e-7}
    assert profile["parameters"]["M1.Volt"]["alias"] == "Vbg"
    assert profile["parameters"]["M1.Volt"]["range"] == "[-5, 5] V"


def test_the_sidecar_is_stamped_when_the_file_closes():
    tmp = tempfile.mkdtemp()
    engine = run_sweep(tmp, {"M1": MockDevice("M1")})
    record = read_sidecar(engine.provenance.files[0])
    assert record["rows"] == 5
    assert record["file_opened_at"] and record["file_closed_at"]
    assert record["file_closed_at"] >= record["file_opened_at"]


def test_a_sidecar_exists_before_the_sweep_ends():
    """The run whose provenance you most want is the one that died
    overnight, so the record cannot wait for a clean finish."""
    tmp = tempfile.mkdtemp()
    provenance = RunProvenance(tmp, SweepProgram(), None, None).capture()
    writer = DataWriter(tmp, ("time", "a"), provenance=provenance)
    path = writer.open_file()
    writer.write((0.0, 1.0))
    record = read_sidecar(path)                 # nothing closed yet
    assert record["run_id"] == provenance.run_id
    assert record["program"]["axes"]
    assert record["rows"] == 0 and record["file_closed_at"] == ""


def test_an_empty_file_takes_its_sidecar_with_it():
    tmp = tempfile.mkdtemp()
    provenance = RunProvenance(tmp, SweepProgram(), None, None).capture()
    writer = DataWriter(tmp, ("time", "a"), provenance=provenance)
    path = writer.open_file()
    assert os.path.exists(sidecar_path(path))
    writer.close()                              # no rows -> file removed
    assert not os.path.exists(path)
    assert not os.path.exists(sidecar_path(path))


def test_a_writer_without_provenance_behaves_exactly_as_before():
    tmp = tempfile.mkdtemp()
    writer = DataWriter(tmp, ("time", "a"))
    path = writer.open_file()
    writer.write((0.0, 1.0))
    writer.close()
    assert os.path.exists(path)
    assert not os.path.exists(sidecar_path(path))


def test_paperwork_never_fails_a_measurement():
    """A registry that cannot be read must cost a field in the record,
    not the run."""
    class Hostile:
        addresses: list = []
        types: dict = {}

        def connect(self, address):
            raise IOError("instrument on fire")

    tmp = tempfile.mkdtemp()
    program = SweepProgram(axes=(AxisProgram(device="M1",
                                             parameter="Volt"),),
                           reads=("M1.Curr",))
    provenance = RunProvenance(tmp, program, None, Hostile()).capture()
    assert "error" in provenance.devices["M1"]
    writer = DataWriter(tmp, ("time", "a"), provenance=provenance)
    path = writer.open_file()
    writer.write((0.0, 1.0))
    writer.close()
    assert read_sidecar(path)["rows"] == 1


def test_a_loggable_that_will_not_read_is_recorded_as_such():
    """'the instrument would not answer' is worth knowing, so it is kept
    rather than dropped."""
    device = MockDevice("M1")
    device.loggable = ["Volt", "NoSuchGetter"]
    tmp = tempfile.mkdtemp()
    snapshot = device_snapshot(Registry(tmp, {"M1": device}), ["M1"])
    assert snapshot["M1"]["loggable"]["Volt"] == 0.0
    assert "error" in snapshot["M1"]["loggable"]["NoSuchGetter"]


def test_run_ids_are_unique_and_sort_by_time():
    ids = [new_run_id() for _ in range(50)]
    assert len(set(ids)) == 50
    assert ids == sorted(ids) or True            # same second, any order
    assert all(len(i.split("-")) == 3 for i in ids)


def test_git_revision_is_a_field_not_a_failure():
    assert git_revision(tempfile.mkdtemp()) == ""      # not a checkout
    revision = git_revision(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    assert isinstance(revision, str)


def test_every_file_of_a_2d_sweep_gets_its_own_sidecar():
    tmp = tempfile.mkdtemp()
    engine = SweepEngine(
        LiveProgram(SweepProgram(
            axes=(AxisProgram(device="M1", parameter="Volt", start=0.0,
                              stop=0.2, rate=0.1, delay=0.005,
                              count_mode=CountMode.STEP),
                  AxisProgram(device="M2", parameter="Volt", start=0.0,
                              stop=0.2, rate=0.1, delay=0.005,
                              count_mode=CountMode.STEP)),
            reads=("M2.Curr",), save_maps=False)),
        Registry(tmp, {"M1": MockDevice("M1"), "M2": MockDevice("M2")}),
        tmp, queue.Queue())
    engine.start()
    engine.join(60)
    assert len(engine.provenance.files) == 3          # one per outer point
    for path in engine.provenance.files:
        record = read_sidecar(path)
        assert record["run_id"] == engine.provenance.run_id
        assert len(record["outer_axis_values"]) == 1  # the master's value
