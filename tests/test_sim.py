"""The simulated graphene rig.

Two things are being pinned here. The first is that the physics still says
what the published numbers say — if someone retunes a coefficient, the
landmark tests fail and name which one. The second is that the drivers
still satisfy Unisweep's duck-typed driver contract, because a driver that
quietly stops matching it fails at the point where a sweep is running.

Several tests exist because the bug they describe actually happened:
``test_the_hall_curve_has_no_cliffs_in_it`` is here because a floor() in
the plateau staircase put a 3.8 kohm vertical jump in R_xy(B), and
``test_every_driver_declares_its_options_as_a_literal_list`` is here
because DeviceRegistry reads those lists out of the source with ast, so a
list built any other way makes the device look optionless until it is
connected.
"""

from __future__ import annotations

import ast
import importlib.util
import inspect
import math
import os
import sys

import pytest

from unisweep.sim import (BeamPath, GrapheneSample, SimFaults,
                          configure, rig)
from unisweep.sim.graphene import E_CHARGE, H_PLANCK, R_K

CM2 = 1e4
DEVICES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "devices")
DRIVERS = ["SimMagnet", "SimGate", "SimTopGate", "SimCryostat",
           "SimLockinXX", "SimLockinXY", "SimSMU", "SimTHzSource",
           "SimLensStage"]


class FakeClock:
    """Time we control, so no test depends on how fast the box is."""

    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def tick(self, dt):
        self.t += float(dt)


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def sim(clock):
    return configure(clock=clock, seed=4242)


@pytest.fixture
def sample():
    return GrapheneSample()


def load_driver(name):
    """Import a driver file the way DeviceRegistry does."""
    path = os.path.join(DEVICES_DIR, f"{name}.py")
    spec = importlib.util.spec_from_file_location(f"sim_drivers.{name}", path)
    module = importlib.util.module_from_spec(spec)
    # registering before exec is what DeviceRegistry does, and it is also
    # what lets inspect.getsource find the file again later
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return getattr(module, name)


# ==========================================================================
# the sample: landmarks from the literature
# ==========================================================================
def test_the_back_gate_adds_the_carriers_a_300nm_oxide_should(sample):
    # 300 nm SiO2: C_ox = 1.15e-4 F/m2, i.e. 7.2e10 cm^-2 per volt
    assert sample.oxide_capacitance == pytest.approx(1.151e-4, rel=0.01)
    assert sample.density_per_volt_cm2 == pytest.approx(7.18e10, rel=0.01)


def test_acoustic_phonons_cost_thirty_ohms_at_room_temperature(sample):
    # Chen et al., Nature Nanotech 3, 206 (2008): the intrinsic limit
    assert sample.rho_acoustic_per_K * 300.0 == pytest.approx(30.0, rel=0.05)


def test_the_substrate_caps_room_temperature_mobility_near_forty_thousand(
        sample):
    # the same paper: SiO2 surface phonons limit RT mobility to ~4e4 cm2/Vs
    n = 1e12 * CM2
    mu = 1.0 / (n * E_CHARGE * sample.phonon_resistivity(300.0)) * CM2
    assert mu == pytest.approx(4.0e4, rel=0.05)


def test_phonon_scattering_is_negligible_below_a_hundred_kelvin(sample):
    assert sample.phonon_resistivity(100.0) < 15.0
    assert sample.phonon_resistivity(10.0) < 2.0


def test_phonon_resistivity_does_not_depend_on_carrier_density(sample):
    # the headline result of the linear dispersion, and the reason the
    # phonon terms are added to rho and not to a mobility
    rho = sample.phonon_resistivity(300.0)
    assert rho == sample.phonon_resistivity(300.0)
    low = sample.mobility(1e15, 300.0)
    high = sample.mobility(1e17, 300.0)
    assert low > high          # same rho, so mobility falls with density


def test_thermal_carriers_matter_at_room_temperature(sample):
    assert sample.thermal_density(300.0) / CM2 == pytest.approx(8.1e10,
                                                                rel=0.05)
    assert sample.thermal_density(4.0) / CM2 < 1e9


def test_electrons_and_holes_are_equal_at_the_dirac_point(sample):
    n, p = sample.carrier_densities(sample.dirac_voltage, 4.0)
    assert n == pytest.approx(p, rel=1e-9)
    assert n / CM2 == pytest.approx(sample.puddle_density_cm2, rel=0.05)


def test_the_two_carrier_densities_obey_the_mass_action_law(sample):
    n, p = sample.carrier_densities(sample.dirac_voltage + 7.0, 4.0)
    n_0 = sample.residual_density(4.0)
    assert n - p == pytest.approx(
        sample.gate_density(sample.dirac_voltage + 7.0), rel=1e-9)
    assert n * p == pytest.approx(n_0 ** 2, rel=1e-6)


def test_the_resistance_peaks_at_the_dirac_point(sample):
    peak, _ = sample.resistances(sample.dirac_voltage, 0.0, 4.0)
    for dv in (-40.0, -15.0, 15.0, 40.0):
        away, _ = sample.resistances(sample.dirac_voltage + dv, 0.0, 4.0)
        assert away < peak
    far, _ = sample.resistances(sample.dirac_voltage + 40.0, 0.0, 4.0)
    assert 3.0 < peak / far < 20.0


def test_far_from_the_dirac_point_the_hall_slope_gives_the_gate_density(
        sample):
    vg = sample.dirac_voltage + 40.0
    b = 0.4
    _, rho_xy = sample.resistivities(vg, b, 4.0)
    n_hall = -b / (E_CHARGE * rho_xy)
    assert n_hall == pytest.approx(sample.gate_density(vg), rel=0.03)


def test_near_the_dirac_point_the_hall_slope_overestimates_the_density(
        sample):
    # not a defect: with both carriers present the Hall coefficient is
    # (p mu_p^2 - n mu_n^2)/(e (p mu_p + n mu_n)^2), which is not 1/(ne).
    # A reader who extracts a density at low gate and does not say so is
    # making a real mistake, and the rig has to be able to catch them.
    vg = sample.dirac_voltage + 5.0
    b = 0.4
    _, rho_xy = sample.resistivities(vg, b, 4.0)
    n_hall = -b / (E_CHARGE * rho_xy)
    assert n_hall > sample.gate_density(vg) * 1.2


def test_the_hall_sign_flips_through_the_dirac_point(sample):
    _, electrons = sample.resistivities(sample.dirac_voltage + 20.0, 1.0, 4.0)
    _, holes = sample.resistivities(sample.dirac_voltage - 20.0, 1.0, 4.0)
    assert electrons < 0.0 < holes


def test_a_single_carrier_has_no_magnetoresistance(sample):
    vg = sample.dirac_voltage + 50.0        # deep in the electron branch
    zero, _ = sample.resistivities(vg, 0.0, 4.0), None
    r0, _ = sample.resistivities(vg, 0.0, 4.0)
    r9, _ = sample.resistivities(vg, 2.0, 4.0)
    assert r9 == pytest.approx(r0, rel=0.10)


def test_two_carriers_at_the_dirac_point_do_have_magnetoresistance(sample):
    r0, _ = sample.resistivities(sample.dirac_voltage, 0.0, 4.0)
    r3, _ = sample.resistivities(sample.dirac_voltage, 3.0, 4.0)
    assert r3 > 5.0 * r0


# ==========================================================================
# the quantum regime
# ==========================================================================
def test_a_clean_sample_reaches_the_nu_equals_two_plateau():
    clean = GrapheneSample(dingle_temperature_K=3.0,
                           puddle_density_cm2=5e10,
                           mobility_impurity_cm2Vs=40000.0)
    vg = clean.dirac_voltage + 6.0
    n = clean.gate_density(vg)
    b = n * H_PLANCK / (2.0 * E_CHARGE)          # exactly nu = 2
    rho_xx, rho_xy = clean.resistivities(vg, b, 1.8)
    assert abs(rho_xy) == pytest.approx(R_K / 2.0, rel=0.02)
    rho_low, _ = clean.resistivities(vg, b * 0.55, 1.8)
    assert rho_xx < 0.25 * rho_low               # rho_xx collapses on it


def test_the_hall_plateau_is_flatter_than_the_classical_line():
    clean = GrapheneSample(dingle_temperature_K=3.0,
                           puddle_density_cm2=5e10,
                           mobility_impurity_cm2Vs=40000.0)
    b = 8.5
    values = []
    for nu in (1.9, 2.0, 2.1):
        n = nu * E_CHARGE * b / H_PLANCK
        vg = clean.dirac_voltage + n / (clean.oxide_capacitance / E_CHARGE)
        values.append(abs(clean.resistivities(vg, b, 1.8)[1]))
    spread = (max(values) - min(values)) / values[1]
    classical = 1 / 1.9 - 1 / 2.1                # ~10% over the same range
    assert spread < 0.5 * classical


def test_the_hall_curve_has_no_cliffs_in_it(sample):
    # a floor() in the plateau staircase used to put a 3.8 kohm vertical
    # jump here, which is both unphysical and fatal to any derivative
    vg = sample.dirac_voltage + 6.0
    b = 0.2
    previous = sample.resistivities(vg, b, 1.8)[1]
    worst = 0.0
    while b < 9.0:
        b += 0.002
        current = sample.resistivities(vg, b, 1.8)[1]
        worst = max(worst, abs(current - previous))
        previous = current
    assert worst < 20.0, f"R_xy jumps by {worst:.0f} ohm in 2 mT"


def test_shubnikov_de_haas_minima_sit_at_half_integer_filling(sample):
    # Minima at half-integer B_F/B is the Berry phase of pi, and is what
    # separates graphene from a conventional 2DEG. Getting this backwards
    # would still look like an oscillation.
    vg = sample.dirac_voltage + 15.0
    n = abs(sample.gate_density(vg))
    b_f = n * H_PLANCK / (4.0 * E_CHARGE)
    at = {ratio: sample.resistivities(vg, b_f / ratio, 1.8)[0]
          for ratio in (1.5, 2.0, 2.5, 3.0, 3.5)}
    assert at[1.5] < at[2.0]
    assert at[2.5] < at[2.0]
    assert at[2.5] < at[3.0]
    assert at[3.5] < at[3.0]


def test_oscillations_die_when_the_sample_is_warm(sample):
    vg = sample.dirac_voltage + 15.0
    n = abs(sample.gate_density(vg))
    b_f = n * H_PLANCK / (4.0 * E_CHARGE)
    cold_min = sample.resistivities(vg, b_f / 2.5, 1.8)[0]
    cold_max = sample.resistivities(vg, b_f / 3.0, 1.8)[0]
    warm_min = sample.resistivities(vg, b_f / 2.5, 80.0)[0]
    warm_max = sample.resistivities(vg, b_f / 3.0, 80.0)[0]
    assert (cold_max - cold_min) / cold_max > 0.15
    assert abs(warm_max - warm_min) / warm_max < 0.05


def test_quantisation_can_be_switched_off_entirely(sample):
    flat = GrapheneSample(quantum_enabled=False)
    vg = flat.dirac_voltage + 15.0
    n = abs(flat.gate_density(vg))
    b_f = n * H_PLANCK / (4.0 * E_CHARGE)
    a = flat.resistivities(vg, b_f / 2.5, 1.8)[0]
    b = flat.resistivities(vg, b_f / 3.0, 1.8)[0]
    assert a == pytest.approx(b, rel=0.02)


# ==========================================================================
# wiring: the mistakes the rig is meant to be able to catch
# ==========================================================================
def test_symmetrising_in_field_removes_the_probe_misalignment(sample):
    vg = sample.dirac_voltage + 12.0
    b = 0.5
    _, plus = sample.resistances(vg, +b, 4.0)
    _, minus = sample.resistances(vg, -b, 4.0)
    _, truth = sample.resistivities(vg, b, 4.0)
    assert 0.5 * (plus - minus) == pytest.approx(truth, rel=1e-9)


def test_an_unsymmetrised_hall_reading_is_wrong_by_a_visible_amount(sample):
    vg = sample.dirac_voltage + 12.0
    _, raw = sample.resistances(vg, 0.5, 4.0)
    _, truth = sample.resistivities(vg, 0.5, 4.0)
    assert abs(raw - truth) / abs(truth) > 0.05


def test_the_leak_hunt_works_the_way_the_lab_does_it(sim, clock):
    """The safe gate limit is found, not declared.

    At zero volts the SMU already reads a nanoamp or two of its own
    offset. The device's own leakage starts far below that and climbs
    exponentially; the voltage where it emerges from the offset floor is
    the limit for the rest of the cooldown. If the floor were picoamps the
    onset would be visible immediately and the procedure would be empty.
    """
    sim.set_gate_compliance(1e-6)
    sim.set_gate_voltage(0.0)
    clock.tick(1.0)
    floor = abs(sim.gate_current())
    assert 5e-10 < floor < 5e-9, "the offset floor should be nanoamps"

    sim.set_gate_voltage(30.0)
    clock.tick(1.0)
    assert abs(sim.gate_current()) == pytest.approx(floor, rel=0.2), \
        "at 30 V the device is still quiet under the offset"

    sim.set_gate_voltage(70.0)
    clock.tick(1.0)
    assert abs(sim.gate_current()) > 3.0 * floor, \
        "by 70 V the leak has to be unmistakable"

    # and the onset is somewhere in between, findable by walking outward
    onset = None
    for volts in range(0, 81, 5):
        sim.set_gate_voltage(float(volts))
        clock.tick(1.0)
        if abs(sim.gate_current()) > 2.0 * floor:
            onset = volts
            break
    assert onset is not None and 40 < onset < 75, \
        f"leak onset at {onset} V is not where a 300 nm oxide should be"


def test_an_hbn_device_leaks_ten_times_sooner(clock):
    # the prior the lab works to: hBN, never past 10 V unless pushed
    hbn = GrapheneSample(dielectric="hBN", oxide_thickness_nm=30.0,
                         oxide_epsilon=3.4, leakage_voltage_V=1.5,
                         breakdown_voltage_V=22.0, dirac_voltage=0.6)
    sim = configure(sample=hbn, clock=clock, seed=3)
    sim.set_gate_compliance(1e-6)
    sim.set_gate_voltage(0.0)
    clock.tick(1.0)
    floor = abs(sim.gate_current())
    onset = None
    for tenths in range(0, 200, 5):
        sim.set_gate_voltage(tenths / 10.0)
        clock.tick(1.0)
        if abs(sim.gate_current()) > 2.0 * floor:
            onset = tenths / 10.0
            break
    assert onset is not None and 8.0 < onset < 15.0, \
        f"hBN leak onset at {onset} V"
    # and it carries ten times the capacitance of 300 nm oxide
    assert hbn.density_per_volt_cm2 > 5.0 * GrapheneSample(
        ).density_per_volt_cm2


def test_breakdown_is_permanent_until_the_rig_is_reset(sim, clock):
    sim.set_gate_compliance(1e-6)
    sim.set_gate_voltage(60.0)
    clock.tick(1.0)
    assert not sim.oxide_damaged()
    sim.set_gate_voltage(90.0)
    clock.tick(1.0)
    assert sim.oxide_damaged()
    sim.set_gate_voltage(5.0)
    clock.tick(1.0)
    assert sim.oxide_damaged()
    assert abs(sim.gate_current()) >= sim.gate_compliance() * 0.999
    sim.reset()
    assert not sim.oxide_damaged()


# ==========================================================================
# the instruments
# ==========================================================================
def test_the_magnet_takes_time_to_get_there(sim, clock):
    sim.set_field(1.0, rate=0.1)
    clock.tick(2.0)
    assert sim.field() == pytest.approx(0.2, abs=1e-9)
    assert sim.magnet_state() == 1.0
    clock.tick(30.0)
    assert sim.field() == pytest.approx(1.0, abs=1e-9)
    assert sim.magnet_state() == 2.0


def test_the_magnet_clamps_at_its_own_limit(sim, clock):
    sim.set_field(100.0)
    clock.tick(1e5)
    assert sim.field() == pytest.approx(sim.MAX_FIELD_T)


def test_the_sample_lags_the_temperature_setpoint(clock):
    sim = configure(clock=clock, seed=7, initial_temperature=300.0)
    sim.set_temperature(4.0, rate=2.0)
    clock.tick(10.0)
    assert sim.temperature() > 100.0
    clock.tick(2000.0)
    assert sim.temperature() == pytest.approx(4.0, abs=0.5)


def test_the_rig_starts_cold_so_a_first_sweep_does_not_wait(sim):
    # a cryostat you sit down at is already cold; starting at 300 K would
    # put a two-and-a-half minute cooldown in front of every experiment
    assert sim.temperature() == pytest.approx(4.2, abs=0.01)


def test_a_scenario_can_ask_for_a_warm_start(clock):
    sim = configure(clock=clock, seed=7, initial_temperature=290.0)
    assert sim.temperature() == pytest.approx(290.0, abs=0.01)


def test_the_lockin_lags_when_it_is_read_too_soon(sim, clock):
    sim.set_gate_voltage(sim.sample.dirac_voltage + 30.0)
    sim.set_lockin("xx", "time_constant", 0.3)
    clock.tick(5.0)
    sim.lockin_xy_pair("xx")
    for _ in range(60):
        clock.tick(1.0)
        settled = sim.lockin_xy_pair("xx")[0]

    sim.set_gate_voltage(sim.sample.dirac_voltage + 8.0)
    clock.tick(0.03)                      # a fast sweep's dwell time
    hasty = sim.lockin_xy_pair("xx")[0]
    clock.tick(10.0)
    patient = sim.lockin_xy_pair("xx")[0]

    moved = abs(hasty - settled) / abs(patient - settled)
    assert moved < 0.25, f"the filter moved {moved:.0%} in 0.1 tau"


def test_both_channels_advance_when_a_point_reads_both(sim, clock):
    # Found by running a real sweep: every point reads Vxx and then Vxy
    # microseconds apart. When the filter used the time since the rig was
    # last touched by anything, the second channel saw dt = 0 and never
    # moved — Vxy came back frozen for the whole sweep while Vxx tracked
    # perfectly. Each channel has to keep its own last-read clock.
    sim.set_gate_voltage(sim.sample.dirac_voltage + 30.0)
    for _ in range(40):                    # settle both channels
        clock.tick(1.0)
        sim.lockin_xy_pair("xx")
        sim.lockin_xy_pair("xy")
    before_xx = sim.lockin_xy_pair("xx")[0]
    before_xy = sim.lockin_xy_pair("xy")[0]

    sim.set_gate_voltage(sim.sample.dirac_voltage)
    moved_xx = moved_xy = 0.0
    for _ in range(12):                    # a sweep's worth of points
        clock.tick(0.5)
        xx = sim.lockin_xy_pair("xx")[0]   # read in the same order a
        xy = sim.lockin_xy_pair("xy")[0]   # program's `reads` list gives
        moved_xx = abs(xx - before_xx)
        moved_xy = abs(xy - before_xy)
    assert moved_xx > 0.2 * abs(before_xx)
    assert moved_xy > 0.2 * abs(before_xy), \
        "the second channel read in each point never moved"


def test_turning_the_lag_off_makes_the_lockin_instantaneous(clock):
    sim = configure(faults=SimFaults(lockin_lag=False, noise=False),
                    clock=clock, seed=1)
    sim.set_gate_voltage(sim.sample.dirac_voltage + 30.0)
    sim.set_lockin("xx", "time_constant", 3.0)
    clock.tick(1.0)
    first = sim.lockin_xy_pair("xx")[0]
    sim.set_gate_voltage(sim.sample.dirac_voltage + 8.0)
    clock.tick(0.001)
    assert sim.lockin_xy_pair("xx")[0] != pytest.approx(first, rel=0.01)


def test_the_default_time_constant_settles_within_an_ordinary_point(sim,
                                                                    clock):
    # Whoever runs the first sweep will not have touched the lock-in. If
    # the default tau is comparable to a normal per-point delay, that
    # sweep comes back lagged and looks like a broken simulator rather
    # than like a lock-in doing its job.
    assert sim.get_lockin("xx", "time_constant") <= 0.04
    sim.set_gate_voltage(sim.sample.dirac_voltage + 30.0)
    for _ in range(40):
        clock.tick(0.2)
        settled = sim.lockin_xy_pair("xx")[0]
    sim.set_gate_voltage(sim.sample.dirac_voltage + 5.0)
    clock.tick(0.15)                       # one ordinary point
    after_one_point = sim.lockin_xy_pair("xx")[0]
    clock.tick(20.0)
    final = sim.lockin_xy_pair("xx")[0]
    progress = abs(after_one_point - settled) / abs(final - settled)
    assert progress > 0.95, f"only {progress:.0%} settled after one point"


def test_white_noise_follows_the_bandwidth_the_operator_chose(sim, clock):
    sim.faults.lockin_lag = False
    sim.set_gate_voltage(sim.sample.dirac_voltage + 30.0)

    def sigma(tau, n=500):
        sim.set_lockin("xx", "time_constant", tau)
        values = []
        for _ in range(n):
            clock.tick(0.5)
            sim._drift = 0.0              # white noise alone
            values.append(sim.lockin_xy_pair("xx")[0])
        mean = sum(values) / len(values)
        return math.sqrt(sum((v - mean) ** 2 for v in values) / len(values))

    # ENBW = 1/(4 tau), so a hundredfold longer tau is ten times quieter
    ratio = sigma(0.003) / sigma(0.3)
    assert 6.0 < ratio < 15.0, f"noise ratio {ratio:.1f}, expected ~10"


def test_slow_drift_stops_a_long_time_constant_from_helping(sim, clock):
    sim.faults.lockin_lag = False
    sim.set_gate_voltage(sim.sample.dirac_voltage + 30.0)
    sim.set_lockin("xx", "time_constant", 0.3)

    def sigma(drift):
        values = []
        for _ in range(500):
            clock.tick(0.5)
            if not drift:
                sim._drift = 0.0
            values.append(sim.lockin_xy_pair("xx")[0])
        mean = sum(values) / len(values)
        return math.sqrt(sum((v - mean) ** 2 for v in values) / len(values))

    assert sigma(True) > 1.5 * sigma(False)


def test_noise_can_be_switched_off_for_a_deterministic_run(clock):
    sim = configure(faults=SimFaults(noise=False, lockin_lag=False),
                    clock=clock, seed=9)
    sim.set_gate_voltage(sim.sample.dirac_voltage + 20.0)
    clock.tick(1.0)
    first = sim.lockin_xy_pair("xx")[0]
    clock.tick(1.0)
    assert sim.lockin_xy_pair("xx")[0] == pytest.approx(first, rel=1e-12)


def test_bias_current_heats_the_sample_without_telling_the_thermometer(
        sim, clock):
    sim.set_temperature(4.0)
    clock.tick(3000.0)
    sim.set_bias_current(0.0)
    clock.tick(1.0)
    cold = sim.truth()["state"]["electron_temperature_K"]
    sim.set_bias_current(1e-3)
    clock.tick(1.0)
    hot = sim.truth()["state"]["electron_temperature_K"]
    assert cold < 5.0
    assert hot > 20.0
    assert sim.temperature() == pytest.approx(4.0, abs=0.2)


def test_a_hundred_nanoamps_barely_heats_anything(sim, clock):
    # Not exactly nothing: the cooling law says the electrons always sit
    # a little above the lattice. At 100 nA it is a hundredth of a kelvin,
    # which is the point — the excitation you measure with is negligible
    # and the bias you sweep with is not.
    sim.set_temperature(4.0)
    clock.tick(3000.0)
    sim.set_bias_current(1e-7)
    clock.tick(1.0)
    assert sim.truth()["state"]["electron_temperature_K"] - 4.0 < 0.2
    sim.set_bias_current(1e-6)
    clock.tick(1.0)
    warm = sim.truth()["state"]["electron_temperature_K"]
    assert warm > 5.0, "a microamp should already be visible at base"
    sim.set_bias_current(1e-5)
    clock.tick(1.0)
    assert sim.truth()["state"]["electron_temperature_K"] > 20.0


def test_the_two_probe_reading_carries_the_contacts(sim, clock):
    sim.set_temperature(4.0)
    clock.tick(3000.0)
    sim.set_gate_voltage(sim.sample.dirac_voltage + 30.0)
    sim.set_bias_current(1e-6)
    clock.tick(5.0)
    two_probe = sim.bias_voltage() / sim.bias_current()
    sheet = sim.sample.resistivities(sim.gate_voltage(), 0.0, 4.0)[0]
    four_probe = sheet * sim.sample.aspect_ratio
    assert two_probe > four_probe + sim.sample.contact_resistance_ohm


def test_two_probe_resistance_is_nan_when_no_current_flows(sim, clock):
    # The bias safety rule converts through R_2pt: the ceiling is 500 uA
    # times this number. Read at zero bias it would otherwise be the ratio
    # of two noise values — a plausible-looking number, wrong by orders of
    # magnitude, handed over as a permission.
    sim.set_bias_current(0.0)
    clock.tick(1.0)
    assert math.isnan(sim.bias_resistance())
    sim.set_bias_current(5e-6)
    clock.tick(1.0)
    r = sim.bias_resistance()
    assert math.isfinite(r) and 500.0 < r < 1e5


def test_the_excitation_current_comes_from_the_xx_oscillator(sim, clock):
    sim.set_lockin("xx", "amplitude", 0.2)
    assert sim.ac_current() == pytest.approx(0.2 / sim.BIAS_RESISTOR)
    sim.set_lockin("xy", "amplitude", 1.5)
    assert sim.ac_current() == pytest.approx(0.2 / sim.BIAS_RESISTOR)


# ==========================================================================
# faults
# ==========================================================================
def test_the_nasty_faults_are_off_by_default():
    f = SimFaults()
    assert f.gate_hysteresis == 0.0
    assert f.intermittent_contact == 0.0
    assert f.thermometer_offset_K == 0.0
    # while ordinary instrumentation is on
    assert f.noise and f.lockin_lag and f.self_heating


def test_gate_hysteresis_drags_the_dirac_point(clock):
    sim = configure(faults=SimFaults(gate_hysteresis=0.12), clock=clock,
                    seed=5)
    before = sim.truth()["state"]["dirac_voltage_effective"]
    for v in range(0, 61, 5):
        sim.set_gate_voltage(float(v))
        clock.tick(60.0)
    after = sim.truth()["state"]["dirac_voltage_effective"]
    assert after - before > 1.0


def test_an_intermittent_contact_hits_the_hall_channel_hardest(clock):
    sim = configure(faults=SimFaults(intermittent_contact=1.0, noise=False,
                                     lockin_lag=False), clock=clock, seed=2)
    sim.set_gate_voltage(sim.sample.dirac_voltage + 20.0)
    clock.tick(1.0)
    clean = configure(faults=SimFaults(noise=False, lockin_lag=False),
                      clock=clock, seed=2)
    clean.set_gate_voltage(clean.sample.dirac_voltage + 20.0)
    clock.tick(1.0)
    bad_xy = abs(sim.lockin_xy_pair("xy")[0])
    good_xy = abs(clean.lockin_xy_pair("xy")[0])
    assert bad_xy > 1.3 * good_xy


def test_the_answer_key_is_not_reachable_through_any_instrument():
    # truth() is how the bench scores a measurement; if a driver could
    # read it, every scenario would be open-book
    for name in DRIVERS:
        cls = load_driver(name)
        instance = cls(adress=f"SIM::{name}")
        assert "truth" not in instance.get_options
        assert not hasattr(instance, "truth")


# ==========================================================================
# the driver contract
# ==========================================================================
@pytest.mark.parametrize("name", DRIVERS)
def test_every_get_option_has_a_getter_that_returns_a_number(name, sim):
    cls = load_driver(name)
    instance = cls(adress=f"SIM::{name}")
    for option in instance.get_options:
        getter = getattr(instance, option, None)
        assert callable(getter), f"{name} has no getter '{option}'"
        float(getter())


@pytest.mark.parametrize("name", DRIVERS)
def test_every_set_option_has_a_setter(name, sim):
    cls = load_driver(name)
    instance = cls(adress=f"SIM::{name}")
    for option in instance.set_options:
        assert callable(getattr(instance, f"set_{option}", None)), \
            f"{name} has no setter 'set_{option}'"


@pytest.mark.parametrize("name", DRIVERS)
def test_every_capability_list_lines_up_with_set_options(name):
    cls = load_driver(name)
    instance = cls(adress=f"SIM::{name}")
    expected = len(instance.set_options)
    for attr in ("sweepable", "maxspeed", "eps"):
        if hasattr(instance, attr):
            assert len(getattr(instance, attr)) == expected, \
                f"{name}.{attr} does not match set_options"


@pytest.mark.parametrize("name", DRIVERS)
def test_every_loggable_is_callable_and_does_not_raise(name, sim):
    cls = load_driver(name)
    instance = cls(adress=f"SIM::{name}")
    for entry in getattr(instance, "loggable", []):
        attribute = getattr(instance, entry, None)
        assert callable(attribute), f"{name}.{entry} is not callable"
        attribute()


@pytest.mark.parametrize("name", DRIVERS)
def test_every_driver_declares_its_options_as_a_literal_list(name):
    # DeviceRegistry._probe_options reads these off the source with ast so
    # that a device can be listed without being connected. A list built
    # any other way makes the device look optionless on the sweep page.
    cls = load_driver(name)
    found = set()
    for node in ast.walk(ast.parse(inspect.getsource(cls))):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (isinstance(target, ast.Attribute)
                        and target.attr in ("set_options", "get_options")
                        and isinstance(node.value, ast.List)):
                    found.add(target.attr)
    assert found == {"set_options", "get_options"}


@pytest.mark.parametrize("name,parameter", [("SimMagnet", "field"),
                                            ("SimCryostat", "temperature")])
def test_a_ramping_setter_accepts_the_speed_the_engine_passes(name,
                                                              parameter):
    cls = load_driver(name)
    instance = cls(adress="SIM::X")
    setter = getattr(instance, f"set_{parameter}")
    assert "speed" in inspect.signature(setter).parameters


def test_every_instrument_is_looking_at_the_same_piece_of_graphene(sim,
                                                                   clock):
    # the whole rig falls apart if the drivers each build their own
    gate = load_driver("SimGate")(adress="SIM::GATE")
    lockin = load_driver("SimLockinXX")(adress="SIM::LOCKIN::XX")
    magnet = load_driver("SimMagnet")(adress="SIM::MAGNET")

    gate.set_voltage(gate.rig.sample.dirac_voltage)
    clock.tick(1.0)
    at_dirac = abs(lockin.x())
    gate.set_voltage(gate.rig.sample.dirac_voltage + 40.0)
    clock.tick(50.0)
    away = abs(lockin.x())
    assert at_dirac > 2.0 * away, "the lock-in cannot see the gate"

    magnet.set_field(3.0)
    clock.tick(200.0)
    assert magnet.field() == pytest.approx(3.0, abs=1e-6)
    assert sim.field() == pytest.approx(3.0, abs=1e-6)


def test_the_drivers_survive_being_closed_twice(sim):
    for name in DRIVERS:
        instance = load_driver(name)(adress="SIM::X")
        instance.close()
        instance.close()


# ==========================================================================
# configuration
# ==========================================================================
def test_a_scenario_can_replace_the_sample(clock):
    special = GrapheneSample(dirac_voltage=-12.0,
                             mobility_impurity_cm2Vs=30000.0)
    sim = configure(sample=special, clock=clock, seed=11)
    assert sim.sample.dirac_voltage == -12.0
    assert sim.truth()["sample"]["mobility_impurity_cm2Vs"] == 30000.0


def test_the_answer_key_reports_what_the_rig_has_been_put_through(sim,
                                                                  clock):
    sim.set_gate_voltage(45.0)
    sim.set_field(2.0)
    clock.tick(100.0)
    history = sim.truth()["history"]
    assert history["max_abs_gate_V"] == pytest.approx(45.0)
    assert history["max_abs_field_T"] == pytest.approx(2.0, abs=1e-6)
    assert history["oxide_damaged"] is False


def test_the_shared_rig_is_the_same_object_every_time():
    assert rig() is rig()


# ==========================================================================
# the light path
# ==========================================================================
def test_the_lens_starts_nowhere_near_the_optical_axis(sim):
    # if the stage started aligned there would be no beam scan to do
    assert abs(sim.lens("x") - sim.beam.axis_x_mm) > 0.5
    assert abs(sim.lens("z") - sim.beam.focus_z_mm) > 0.5


def test_the_three_ways_of_reading_a_beam_map_give_three_answers():
    # The reason the lab's rule is 'highest symmetry, not highest signal'.
    # The antenna's lobes are placed symmetrically and driven unequally,
    # so brightness-based estimators are pulled toward the stronger arm
    # and a geometric one is not.
    beam = BeamPath()
    assert beam.lobes_resolved(), "one blob has no geometry to centre on"
    by_max = beam.argmax_offset(span_mm=1.4, points=201)
    by_centroid = beam.centroid_offset(span_mm=1.4, points=201)
    by_geometry = beam.lobe_midpoint_offset()

    assert by_max > 0.3, f"argmax only {by_max:.3f} mm out — no trap"
    assert by_centroid < by_max / 3.0     # better, and still wrong
    assert by_centroid > 0.03
    assert by_geometry == pytest.approx(0.0, abs=1e-9)


def test_equal_lobes_would_put_the_maximum_on_the_axis():
    # proves the offset comes from the amplitude imbalance and nothing
    # else — with matched arms every estimator agrees
    fair = BeamPath(lobes=((-0.45, 0.0, 1.0), (0.45, 0.0, 1.0)))
    assert fair.centroid_offset(span_mm=1.4, points=201) == \
        pytest.approx(0.0, abs=1e-6)
    for d in (0.2, 0.45, 0.7):
        left = fair.coupling(fair.axis_x_mm - d, fair.axis_y_mm,
                             fair.focus_z_mm)
        right = fair.coupling(fair.axis_x_mm + d, fair.axis_y_mm,
                              fair.focus_z_mm)
        assert left == pytest.approx(right, rel=1e-9)


def test_defocus_merges_the_lobes_and_costs_coupling():
    beam = BeamPath()
    focused = max(v for _, _, v in beam._sample_map(1.4, 141))
    blurred = max(v for _, _, v in
                  beam._sample_map(1.4, 141,
                                   beam.focus_z_mm + beam.rayleigh_mm))
    assert blurred < 0.75 * focused
    assert beam.spot_size(beam.focus_z_mm + beam.rayleigh_mm) > \
        1.3 * beam.waist_mm
    # far enough out and there is no structure left to centre on
    assert not beam.lobes_resolved(beam.focus_z_mm + 3.0 * beam.rayleigh_mm)


def test_a_closed_shutter_means_no_photoresponse(sim, clock):
    sim.set_gate_voltage(sim.sample.dirac_voltage + 25.0)
    sim.set_lens("x", sim.beam.axis_x_mm)
    sim.set_lens("y", sim.beam.axis_y_mm)
    sim.set_lens("z", sim.beam.focus_z_mm)
    sim.set_thz_power(sim.beam.max_source_power_W)
    sim.set_thz_output(0)
    clock.tick(1.0)
    dark = sim.truth()["state"]["electron_temperature_K"]
    sim.set_thz_output(1)
    clock.tick(1.0)
    light = sim.truth()["state"]["electron_temperature_K"]
    assert light > dark + 1.0
    assert sim.thz_power_monitor() > 0.0
    sim.set_thz_output(0)
    clock.tick(1.0)
    assert sim.thz_power_monitor() == 0.0


def test_light_raises_the_resistance_of_a_doped_sample(sim, clock):
    # heating a doped sheet adds phonon scattering, so Rxx goes up. That
    # is the photoresistance the whole optical pipeline measures.
    sim.set_gate_voltage(sim.sample.dirac_voltage + 25.0)
    sim.set_lens("x", sim.beam.axis_x_mm)
    sim.set_lens("y", sim.beam.axis_y_mm)
    sim.set_lens("z", sim.beam.focus_z_mm)
    clock.tick(1.0)
    dark = sim.truth()["sample_now"]["R_xx_ohm"]
    sim.set_thz_power(sim.beam.max_source_power_W)
    sim.set_thz_output(1)
    clock.tick(1.0)
    lit = sim.truth()["sample_now"]["R_xx_ohm"]
    te = sim.truth()["state"]["electron_temperature_K"]

    # The response is modest and that is the physics, not a weak model:
    # below about 50 K the only thing moving with temperature is the
    # acoustic-phonon term, 0.1 ohm/square/K. So a bolometric
    # photoresponse at base temperature is a measurement of that slope,
    # and it is a fraction of a percent per ten kelvin.
    assert lit > dark * 1.003
    expected = (sim.sample.rho_acoustic_per_K * (te - 4.2)
                * sim.sample.aspect_ratio)
    assert (lit - dark) == pytest.approx(expected, rel=0.35)


def test_absorbed_power_is_not_readable_from_any_instrument(sim):
    for name in DRIVERS:
        instance = load_driver(name)(adress=f"SIM::{name}")
        for option in instance.get_options:
            assert "absorb" not in option.lower(), \
                f"{name}.{option} hands over the answer"
    # it lives in the answer key, where the bench can score against it
    assert "absorbed_thz_power_W" in sim.truth()["state"]


def test_the_cooling_law_can_be_recovered_from_a_power_series(sim, clock):
    # This is the measurement: park the lens, step the source power, read
    # the electron temperature, and fit Te^delta against absorbed power.
    # The exponent that comes back has to be the one the sample was built
    # with, or the exercise is unscoreable.
    sim.set_gate_voltage(sim.sample.dirac_voltage + 25.0)
    sim.set_lens("x", sim.beam.axis_x_mm)
    sim.set_lens("y", sim.beam.axis_y_mm)
    sim.set_lens("z", sim.beam.focus_z_mm)
    sim.set_thz_output(1)
    powers, temps = [], []
    for fraction in (0.15, 0.3, 0.45, 0.6, 0.8, 1.0):
        sim.set_thz_power(fraction * sim.beam.max_source_power_W)
        clock.tick(1.0)
        state = sim.truth()["state"]
        powers.append(state["absorbed_thz_power_W"])
        temps.append(state["electron_temperature_K"])

    delta = sim.sample.cooling_exponent
    bath = temps[0] ** delta - powers[0] * 0.0      # placeholder, see below
    # Te^delta should be linear in absorbed power, through T_bath^delta
    xs, ys = powers, [t ** delta for t in temps]
    n = len(xs)
    mean_x, mean_y = sum(xs) / n, sum(ys) / n
    slope = (sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
             / sum((x - mean_x) ** 2 for x in xs))
    intercept = mean_y - slope * mean_x
    # residuals must be tiny if the exponent is right
    worst = max(abs(y - (slope * x + intercept)) / max(y, 1.0)
                for x, y in zip(xs, ys))
    assert worst < 0.02, f"Te^{delta} is not linear in P ({worst:.3f})"
    assert intercept > 0
    # and a wrong exponent must NOT fit, or the test proves nothing
    ys_wrong = [t ** (delta + 2.0) for t in temps]
    mean_yw = sum(ys_wrong) / n
    slope_w = (sum((x - mean_x) * (y - mean_yw)
                   for x, y in zip(xs, ys_wrong))
               / sum((x - mean_x) ** 2 for x in xs))
    inter_w = mean_yw - slope_w * mean_x
    worst_w = max(abs(y - (slope_w * x + inter_w)) / max(y, 1.0)
                  for x, y in zip(xs, ys_wrong))
    assert worst_w > 3.0 * worst


def test_dc_power_and_absorbed_light_heat_the_same_electron_bath(sim,
                                                                 clock):
    # The premise of calibrating absorbed optical power against DC power.
    # If the two channels did not share a bath the comparison would be
    # measuring nothing, so it is worth pinning.
    sim.set_gate_voltage(sim.sample.dirac_voltage + 25.0)
    sim.set_lens("x", sim.beam.axis_x_mm)
    sim.set_lens("y", sim.beam.axis_y_mm)
    sim.set_lens("z", sim.beam.focus_z_mm)
    sim.set_thz_power(sim.beam.max_source_power_W)
    sim.set_thz_output(1)
    clock.tick(1.0)
    lit = sim.truth()["state"]
    p_light = lit["absorbed_thz_power_W"]
    te_light = lit["electron_temperature_K"]

    # now the same power, in the dark, as DC Joule heating
    sim.set_thz_output(0)
    clock.tick(1.0)
    r2 = sim.sample.two_probe_resistance(
        sim.gate_voltage(), 0.0, te_light, sim.sample.dirac_voltage)
    sim.set_bias_current((p_light / r2) ** 0.5)
    clock.tick(1.0)
    te_dc = sim.truth()["state"]["electron_temperature_K"]
    assert te_dc == pytest.approx(te_light, rel=0.06)


def test_a_single_gated_device_has_no_displacement_field(sim, clock):
    assert not sim.sample.has_top_gate
    sim.set_top_gate_voltage(5.0)
    clock.tick(1.0)
    assert sim.displacement_field() == 0.0
    before = sim.truth()["sample_now"]["net_density_cm2"]
    sim.set_top_gate_voltage(-5.0)
    clock.tick(1.0)
    assert sim.truth()["sample_now"]["net_density_cm2"] == \
        pytest.approx(before, rel=1e-9)


def test_a_dual_gated_device_separates_density_from_field(clock):
    dual = GrapheneSample(dielectric="hBN", oxide_thickness_nm=30.0,
                          oxide_epsilon=3.4, top_gate_thickness_nm=25.0,
                          top_gate_epsilon=3.4, dirac_voltage=0.0)
    sim = configure(sample=dual, clock=clock, seed=13)
    assert dual.has_top_gate

    ratio = dual.oxide_capacitance / dual.top_gate_capacitance

    # Along the constant-DENSITY line the two gates cancel in the sum and
    # add in the difference: n stays put while D sweeps. This is the line
    # the 'repeat at different D' step walks along.
    n_held = dual.gate_density(2.0, None, -2.0 * ratio)
    assert n_held == pytest.approx(0.0, abs=1e13)
    d_pos = dual.displacement_field(2.0, -2.0 * ratio)
    d_neg = dual.displacement_field(-2.0, 2.0 * ratio)
    assert abs(d_pos) > 0.01
    assert d_pos == pytest.approx(-d_neg, rel=1e-9)

    # And along the constant-FIELD line they cancel in the difference:
    # D stays at zero while the density sweeps.
    assert dual.displacement_field(2.0, 2.0 * ratio) == \
        pytest.approx(0.0, abs=1e-12)
    assert abs(dual.gate_density(2.0, None, 2.0 * ratio)) > 1e15

    # and the rig reports the same field the sample computes
    sim.set_gate_voltage(2.0)
    sim.set_top_gate_voltage(-2.0 * ratio)
    clock.tick(1.0)
    assert sim.displacement_field() == pytest.approx(d_pos, rel=1e-6)


# ==========================================================================
# loading drivers the way the running application does
# ==========================================================================
def test_driver_modules_can_be_reloaded():
    """Found by running main.py from an IPython console.

    Drivers are registered in sys.modules under 'unisweep_drivers.<Name>',
    and Python resolves the PARENT of a dotted name before doing anything
    else with it. The parent package was never created, so every reload
    raised "parent 'unisweep_drivers' not in sys.modules". Nothing in
    Unisweep reloads a driver, so it stayed invisible — until autoreload,
    which tries on every cell and printed a traceback per driver.
    """
    import importlib
    from unisweep.core.devices import DeviceRegistry, DRIVER_PACKAGE

    core = os.path.dirname(DEVICES_DIR)
    registry = DeviceRegistry(core)
    if not registry.driver_classes:
        pytest.skip("no drivers installed in resources/")
    assert DRIVER_PACKAGE in sys.modules, \
        "the driver parent package was never registered"

    failures = []
    for name in list(registry.driver_classes):
        module = sys.modules.get(f"{DRIVER_PACKAGE}.{name}")
        assert module is not None, f"{name} is not in sys.modules"
        try:
            importlib.reload(module)
        except Exception as exc:               # noqa: BLE001
            failures.append(f"{name}: {type(exc).__name__}: {exc}")
    assert not failures, "; ".join(failures)


def test_the_registry_still_works_after_a_driver_is_reloaded(sim, clock):
    import importlib
    from unisweep.core.devices import DeviceRegistry, DRIVER_PACKAGE

    core = os.path.dirname(DEVICES_DIR)
    registry = DeviceRegistry(core)
    if "SimGate" not in registry.driver_classes:
        pytest.skip("SimGate is not installed in resources/")
    importlib.reload(sys.modules[f"{DRIVER_PACKAGE}.SimGate"])
    adapter = registry.connect("SIM::GATE")
    adapter.set("voltage", 12.0)
    assert adapter.get("voltage") == pytest.approx(12.0, abs=1e-6)
