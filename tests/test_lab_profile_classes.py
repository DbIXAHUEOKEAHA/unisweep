"""Instrument classes in the lab profile.

The profile used to describe only the boxes currently plugged in. That is
the wrong shape for a file an assistant reasons through: it has to be
rewritten whenever anything is swapped, and nothing it says transfers to
the next instrument. So the profile now carries a taxonomy of instrument
*kinds* — what a lock-in is for, what a source-measure unit can destroy,
why an open-loop positioner is not a closed-loop one — and a specific
address inherits the meaning of its class.

The part that has to keep working is placing hardware the file has never
heard of, by matching a driver's own option names against the class
signatures. Two of the tests below exist because the matcher got that
wrong in ways that were only visible when it was run over all 41 real
drivers in ``devices/``:

* ``test_short_option_names_do_not_match_by_substring`` — a cryostat that
  exposes its PID terms as ``P``, ``I``, ``D`` matched every signature
  containing the letter p, and was classified as a positioner.
* ``test_an_option_may_decorate_a_token_but_not_be_a_fragment_of_one`` —
  matching was bidirectional, so an option literally named ``Field``
  scored against a magnet supply's ``field_rate`` token and out-ranked
  the device's own class.
"""

from __future__ import annotations

import os

import pytest

from unisweep.core.labprofile import InstrumentClass, LabProfile

CORE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Option lists copied verbatim from the drivers in devices/, so these are
# real instruments and not invented ones.
REAL_DRIVERS = {
    "sr830": (["amplitude", "frequency", "phase", "sensitivity",
               "time_constant"],
              ["x", "y", "r", "Θ", "sensitivity", "time_constant"]),
    "M81_lockin": (["LI_current_amplitude", "LI_frequency",
                    "LI_time_constant"],
                   ["LI_x", "LI_y", "LI_r", "LI_theta"]),
    "keithley_series_2600b": (["A_source_current", "A_compl_current",
                               "A_source_voltage", "A_NPLC"],
                              ["A_current", "A_voltage", "A_NPLC"]),
    "keithley2000": ([], ["Volt_DC", "Volt_AC", "Curr_DC", "Res_2W",
                          "Res_4W"]),
    "ami430": (["field", "current", "ramp_field_speed"],
               ["field", "coil_const", "supply_current", "state"]),
    "ANC350": (["gnd_x", "step_up_x", "step_down_x", "volt_x", "freq_x"],
               ["pos_x", "cap_x"]),
    "XStage": (["position", "shift"], ["position", "I_pwr", "T_proc"]),
    "NI_DAQ": (["rate", "n_sample"],
               ["ch0_mean", "ch1_array", "n_statistics"]),
    "Avaspec": (["integration_time", "n_average"],
                ["wavelength", "data", "dark_data", "num_pixels"]),
    "slider": (["close", "open"], ["state"]),
    "RigolDG800": (["freq1", "ampl1", "offset1", "phas1", "outp1"], []),
    "sr580": (["DC_cur", "compl_volt", "gain", "speed"],
              ["DC_cur", "compl_volt", "gain", "speed"]),
    "Time": (["Time"], ["Elapsed", "Random"]),
}

EXPECTED_CLASS = {
    "sr830": "lock_in",
    "M81_lockin": "lock_in",
    "keithley_series_2600b": "source_measure_unit",
    "keithley2000": "voltmeter",
    "ami430": "magnet_supply",
    "ANC350": "positioner_open_loop",
    "XStage": "positioner_closed_loop",
    "NI_DAQ": "daq",
    "Avaspec": "spectrometer",
    "slider": "shutter",
    "RigolDG800": "waveform_generator",
    "sr580": "dc_current_source",
    "Time": "virtual",
}


@pytest.fixture(scope="module")
def profile() -> LabProfile:
    prof = LabProfile.load(CORE_DIR)
    if not prof.instrument_classes:
        pytest.skip("config/lab_profile.json carries no instrument classes")
    return prof


# ==========================================================================
# the matcher
# ==========================================================================
def test_an_exact_option_name_matches():
    klass = InstrumentClass("k", signature=("x", "y"))
    assert klass.match_score(["x", "y", "r"]) == 1.0


def test_an_option_may_decorate_a_token():
    # every driver author spells the same concept differently
    klass = InstrumentClass("k", signature=("time_constant",
                                            "source_voltage", "volt"))
    assert klass.match_score(["LI_time_constant", "A_source_voltage",
                              "volt1"]) == 1.0


def test_an_option_may_decorate_a_token_but_not_be_a_fragment_of_one():
    # Matching used to run both ways, so an option called 'Field' scored
    # against a magnet supply's 'field_rate' and beat the cryostat class
    # the device actually belonged to.
    klass = InstrumentClass("k", signature=("field_rate",))
    assert klass.match_score(["Field"]) == 0.0
    assert klass.match_score(["Field_rate"]) == 1.0


def test_short_option_names_do_not_match_by_substring():
    # A cryostat exposing PID terms as P, I, D matched every signature
    # containing the letter p and came back classified as a positioner.
    positioner = InstrumentClass("p", signature=("position", "shift"))
    assert positioner.match_score(["Temp", "Field", "P", "I", "D"]) == 0.0
    assert positioner.match_score(["position", "shift"]) == 1.0


def test_matching_ignores_case():
    klass = InstrumentClass("k", signature=("volt",))
    assert klass.match_score(["Volt1"]) == 1.0


def test_a_class_with_no_signature_never_matches():
    assert InstrumentClass("k").match_score(["anything"]) == 0.0


# ==========================================================================
# the taxonomy in the shipped profile
# ==========================================================================
def test_the_profile_describes_kinds_of_instrument_not_only_this_rig(
        profile):
    assert len(profile.instrument_classes) >= 12
    for essential in ("lock_in", "source_measure_unit",
                      "temperature_controller", "magnet_supply",
                      "positioner_closed_loop", "daq"):
        assert essential in profile.instrument_classes


def test_every_class_says_what_it_is_and_what_it_can_hurt(profile):
    for name, klass in profile.instrument_classes.items():
        assert klass.what, f"{name} has no description"
        assert klass.safety, f"{name} says nothing about what can go wrong"
        assert klass.method, f"{name} says nothing about how to use one"


def test_every_named_driver_resolves_to_its_own_class(profile):
    bound = 0
    for name, klass in profile.instrument_classes.items():
        for driver in klass.drivers:
            found = profile.class_of(driver)
            assert found is not None, f"{driver} resolves to nothing"
            assert found.name == name, \
                f"{driver} is listed under {name} but resolves to {found.name}"
            bound += 1
    assert bound >= 30, "the taxonomy should cover most of devices/"


def test_a_configured_device_inherits_its_class(profile):
    for address, device in profile.devices.items():
        assert device.instrument_class, \
            f"{address} is not bound to an instrument class"
        assert device.instrument_class in profile.instrument_classes
        assert profile.class_of(address).name == device.instrument_class
        if device.alias:
            assert profile.class_of(device.alias).name == \
                device.instrument_class


@pytest.mark.parametrize("driver", sorted(EXPECTED_CLASS))
def test_a_real_driver_is_placed_by_its_own_option_names(profile, driver):
    set_options, get_options = REAL_DRIVERS[driver]
    guesses = profile.classify(set_options, get_options)
    assert guesses, f"{driver} was not classified at all"
    assert guesses[0][0] == EXPECTED_CLASS[driver], \
        f"{driver} -> {guesses[:3]}, expected {EXPECTED_CLASS[driver]}"


def test_an_instrument_with_nothing_distinctive_is_not_guessed_at(profile):
    # A driver exposing a single option called 'V' cannot be placed, and
    # saying so is the right answer. Reporting a confident wrong class
    # would be worse than reporting none.
    assert profile.classify(["V"], ["V"]) == []


def test_classification_scores_come_back_ranked(profile):
    guesses = profile.classify(*REAL_DRIVERS["sr830"])
    scores = [score for _, score in guesses]
    assert scores == sorted(scores, reverse=True)
    assert all(0.0 < s <= 1.0 for s in scores)


# ==========================================================================
# serialisation and rendering
# ==========================================================================
def test_classes_survive_a_round_trip(profile):
    again = LabProfile.from_dict(profile.to_dict())
    assert set(again.instrument_classes) == set(profile.instrument_classes)
    first = next(iter(profile.instrument_classes))
    assert again.instrument_classes[first].safety == \
        profile.instrument_classes[first].safety
    assert again.instrument_classes[first].signature == \
        profile.instrument_classes[first].signature
    for address, device in profile.devices.items():
        assert again.devices[address].instrument_class == \
            device.instrument_class


def test_describe_hands_the_taxonomy_to_the_assistant(profile):
    text = profile.describe()
    assert "INSTRUMENT CLASSES" in text
    assert "CONFIGURED INSTRUMENTS" in text
    # the general knowledge comes before the particular rig
    assert text.index("INSTRUMENT CLASSES") < text.index(
        "CONFIGURED INSTRUMENTS")
    for name, klass in profile.instrument_classes.items():
        assert f"[{name}]" in text
        if klass.safety:
            assert klass.safety[:40] in text


def test_a_profile_with_only_classes_is_not_empty():
    prof = LabProfile.from_dict(
        {"instrument_classes": {"lock_in": {"what": "phase sensitive"}}})
    assert not prof.is_empty
    assert LabProfile.from_dict({}).is_empty


def test_a_device_alias_beats_a_class_of_the_same_name(profile):
    # 'cryostat' is both a class of instrument and the alias of a
    # particular box on this rig. Asking about the box has to return the
    # box's class, not the category it shares a name with — the lookup
    # used to check class names first and answered 'cryostat' for a
    # controller that has no magnet at all.
    aliased = {dev.alias: dev for dev in profile.devices.values()
               if dev.alias}
    collisions = set(aliased) & set(profile.instrument_classes)
    for alias in collisions:
        assert profile.class_of(alias).name == \
            aliased[alias].instrument_class
    # and a class name that is not also an alias still resolves normally
    for name in profile.instrument_classes:
        if name not in aliased:
            assert profile.class_of(name).name == name
