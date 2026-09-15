"""The simulated rig: instruments, time, noise and faults.

:mod:`unisweep.sim.graphene` says what the sample does. This module says
what you *measure*, which is not the same thing, and the difference is the
point of the whole exercise.

A measurement here is wrong in the ways real measurements are wrong:

* a lock-in reports a filtered value, so sweeping faster than a few time
  constants per point returns a lagged, direction-dependent curve and
  never says so;
* a magnet ramps at a finite rate and the readback is wherever it has got
  to, not the setpoint;
* the sample temperature lags the setpoint;
* Johnson noise, amplifier noise and 1/f drift sit on every reading, with
  the bandwidth set by the time constant the operator chose;
* bias current heats the sample, so an I-V taken too hard measures a
  hotter device than the thermometer reports;
* the Hall probes are not perfectly opposite, so Rxy carries a slice of
  Rxx — removable by symmetrising in field, and not otherwise;
* the gate oxide leaks, and past its breakdown voltage it is destroyed
  and stays destroyed.

All of these are on by default because they are ordinary instrumentation,
and a competent measurement handles them. The nastier faults — gate
hysteresis, an intermittent contact — are off by default and switched on
per scenario, so that the baseline rig is honest and reproducible.

One rig per process, shared by every simulated driver: the magnet, the
gate and the lock-ins are all looking at the same piece of graphene, and
nothing works if they each have their own.

Configuration
-------------
``config/sim_rig.json`` next to the other Unisweep config, if present,
overrides any of the sample or fault fields::

    {"sample": {"dirac_voltage": -3.0, "dielectric": "hBN",
                "oxide_thickness_nm": 30, "oxide_epsilon": 3.4,
                "top_gate_thickness_nm": 25},
     "faults": {"gate_hysteresis": 0.08, "intermittent_contact": 0.002},
     "beam": {"axis_x_mm": -0.4, "focus_z_mm": 2.2},
     "sample_temperature": 295.0,
     "seed": 7}
"""

from __future__ import annotations

import json
import math
import os
import random
import threading
import time
from dataclasses import dataclass, asdict, fields

from .graphene import GrapheneSample, E_CHARGE, K_B
from .optics import BeamPath

__all__ = ["SimRig", "SimFaults", "BeamPath", "rig", "configure",
           "reset"]


@dataclass
class SimFaults:
    """Imperfections that can be switched on per scenario."""

    gate_hysteresis: float = 0.0
    """How strongly the charge-neutrality point is dragged toward the
    gate voltage being held (0 = none, 0.05-0.15 is realistic on SiO2).
    Produces a Dirac point that depends on sweep direction and speed."""
    trap_time_constant_s: float = 240.0

    intermittent_contact: float = 0.0
    """Probability per reading that a voltage contact glitches. The Hall
    channel is affected more than the longitudinal one, which is what
    makes a bad contact look like a plausible-but-wrong Hall slope."""

    lockin_lag: bool = True
    """Honour the time constant. Turning this off makes the lock-in
    instantaneous, which no lock-in is."""

    self_heating: bool = True
    noise: bool = True

    thermometer_offset_K: float = 0.0
    """A thermometer that reads low by a constant. The sample really is
    at the temperature the model uses; the instrument just lies."""


@dataclass
class _Lockin:
    """State of one lock-in channel."""

    amplitude: float = 0.1
    frequency: float = 77.77
    """Off the mains and its low harmonics, and high enough that a 30 ms
    time constant still averages a couple of hundred cycles."""
    time_constant: float = 0.03
    """Chosen so that an ordinary first sweep — 0.1 to 0.2 s per point —
    is already three to six time constants and therefore settled. Raise it
    for a quieter reading and the lag comes back; that trade is the point
    of having a time constant at all."""
    sensitivity: float = 1e-3
    phase: float = 0.0
    filtered: float = 0.0
    filtered_q: float = 0.0
    primed: bool = False
    last_read: float = 0.0
    """When this channel was last read. Each channel keeps its own clock:
    a point that reads Vxx and then Vxy asks the rig for two readings
    microseconds apart, and if the filter used the time since the rig was
    last touched by *anything* the second channel would see dt = 0 and
    never move. Every sweep reads more than one channel, so this is not an
    edge case — it is the normal path."""


class SimRig:
    """Everything the simulated instruments share."""

    BIAS_RESISTOR = 1.0e6
    """The lock-in oscillator drives the sample through this, so the AC
    excitation current is amplitude / BIAS_RESISTOR. 0.1 V gives 100 nA."""

    MAX_FIELD_T = 9.0
    MAX_RAMP_T_PER_S = 0.1
    MIN_TEMPERATURE_K = 1.6
    MAX_TEMPERATURE_K = 320.0
    MAX_TEMP_RATE_K_PER_S = 2.0
    THERMAL_TIME_CONSTANT_S = 18.0

    GATE_OFFSET_CURRENT_A = 1.5e-9
    """A source-measure unit does not read zero current at zero volts. A
    nanoamp-scale offset, drifting slowly, is ordinary — and it sets the
    floor the leak hunt works against: the safe gate limit is where the
    leakage climbs *out of this*, not where it first becomes non-zero.
    Without it the exponential onset would be visible at picoamps and the
    procedure would be trivial."""
    GATE_OFFSET_NOISE_A = 8.0e-11

    INITIAL_TEMPERATURE_K = 4.2
    """The rig starts cold, because that is the state a cryostat is in when
    you sit down at it. Starting at 300 K would be equally defensible and
    would put a two-and-a-half minute cooldown in front of every first
    measurement — the ramp is capped at 2 K/s and the sample lags it — for
    no teaching value. Set `sample_temperature` in config/sim_rig.json to
    start warm and watch it cool."""

    def __init__(self, sample: GrapheneSample | None = None,
                 faults: SimFaults | None = None, seed: int = 20260914,
                 clock=None, initial_temperature: float | None = None,
                 beam: BeamPath | None = None):
        self.sample = sample or GrapheneSample()
        self.faults = faults or SimFaults()
        self.beam = beam or BeamPath()
        self.initial_temperature = (self.INITIAL_TEMPERATURE_K
                                    if initial_temperature is None
                                    else float(initial_temperature))
        self._rng = random.Random(seed)
        self._seed = seed
        self._clock = clock or time.perf_counter
        self._lock = threading.RLock()
        self.reset()

    # ==================================================================
    # lifecycle
    # ==================================================================
    def reset(self) -> None:
        """Back to a cold, undamaged, zero-field rig."""
        with self._lock:
            now = self._clock()
            self._t = now
            self._t_started = now

            # magnet
            self._field = 0.0
            self._field_from = 0.0
            self._field_target = 0.0
            self._field_rate = self.MAX_RAMP_T_PER_S
            self._field_t0 = now

            # cryostat
            start_t = float(getattr(self, "initial_temperature",
                                    self.INITIAL_TEMPERATURE_K))
            self._temp_setpoint = start_t
            self._temp_sample = start_t
            self._temp_target = start_t
            self._temp_rate = self.MAX_TEMP_RATE_K_PER_S

            # gates
            self._gate_v = 0.0
            self._top_gate_v = 0.0
            self._gate_compliance = 1.0e-7
            self._top_gate_compliance = 1.0e-7
            self._dirac_eff = self.sample.dirac_voltage
            self._oxide_damaged = False

            # light path: source dark, lens parked at the origin. The stage
            # starts nowhere near the optical axis on purpose — finding it
            # is the first thing an optical session has to do.
            self._thz_power = 0.0
            self._thz_frequency = 0.3e12
            self._thz_output = False
            self._lens_x = 0.0
            self._lens_y = 0.0
            self._lens_z = 0.0

            # dc bias source
            self._bias_current = 0.0
            self._bias_voltage_source = 0.0
            self._bias_mode = "current"
            self._bias_compliance_v = 10.0
            self._nplc = 1.0

            # lock-ins
            self._lockins = {"xx": _Lockin(), "xy": _Lockin()}

            # slow 1/f drift, as a bounded random walk on resistance
            self._drift = 0.0

            # bookkeeping the bench can score against
            self._max_gate_seen = 0.0
            self._max_top_gate_seen = 0.0
            self._max_field_seen = 0.0
            self._max_bias_seen = 0.0
            self._reads = 0

    # ==================================================================
    # time evolution
    # ==================================================================
    def _advance(self) -> float:
        """Bring the rig up to now. Returns the elapsed time."""
        now = self._clock()
        dt = max(now - self._t, 0.0)
        self._t = now
        if dt <= 0.0:
            return 0.0

        # --- magnet ramp --------------------------------------------------
        if self._field != self._field_target:
            span = self._field_target - self._field
            step = self._field_rate * dt
            if abs(span) <= step:
                self._field = self._field_target
            else:
                self._field += math.copysign(step, span)
        self._max_field_seen = max(self._max_field_seen, abs(self._field))

        # --- cryostat: setpoint walks, sample lags behind it ---------------
        if self._temp_setpoint != self._temp_target:
            span = self._temp_target - self._temp_setpoint
            step = self._temp_rate * dt
            if abs(span) <= step:
                self._temp_setpoint = self._temp_target
            else:
                self._temp_setpoint += math.copysign(step, span)
        alpha = 1.0 - math.exp(-dt / self.THERMAL_TIME_CONSTANT_S)
        self._temp_sample += alpha * (self._temp_setpoint - self._temp_sample)

        # --- gate charge trapping -----------------------------------------
        if self.faults.gate_hysteresis > 0.0:
            beta = 1.0 - math.exp(-dt / self.faults.trap_time_constant_s)
            pull = self.faults.gate_hysteresis * beta
            self._dirac_eff += pull * (self._gate_v - self._dirac_eff)

        # --- 1/f drift: Ornstein-Uhlenbeck, ~1e-4 relative -----------------
        if self.faults.noise:
            tau_d = 30.0
            decay = math.exp(-dt / tau_d)
            self._drift = (self._drift * decay
                           + math.sqrt(1.0 - decay * decay)
                           * self._rng.gauss(0.0, 1.2e-4))
        return dt

    # ==================================================================
    # the sample, as it currently stands
    # ==================================================================
    def _absorbed_thz_power(self) -> float:
        """Power the sheet actually absorbs from the beam, W.

        Deliberately private and absent from every driver: absorbed optical
        power is not a measurable quantity. Inferring it — by matching the
        photoresistance against the resistance drop under a known DC power —
        is the exercise, so handing it over through an instrument would
        delete the exercise.
        """
        if not self._thz_output or self._thz_power <= 0.0:
            return 0.0
        coupling = self.beam.coupling(self._lens_x, self._lens_y,
                                      self._lens_z)
        n, p = self.sample.carrier_densities(
            self._gate_v, self._temp_sample, self._dirac_eff,
            self._top_gate_v)
        return (self._thz_power * coupling
                * self.sample.absorptance(self._thz_frequency, n + p))

    def _electron_temperature(self) -> float:
        """Where the electrons sit, given everything heating them.

        Joule heating from the AC excitation and the DC bias, and absorbed
        light, all land in the same electron bath. That is not a modelling
        shortcut — it is the assumption the whole DC-power calibration
        rests on, and if the two channels did not share a bath the
        comparison would be measuring nothing.

        Two stages in series: the lattice rises above the bath through the
        substrate thermal resistance, and the electrons rise above the
        lattice through the cooling law. At the powers a THz measurement
        uses, the second term is the whole story.
        """
        t_bath = self._temp_sample
        if not self.faults.self_heating:
            return t_bath
        i_ac = self.ac_current()
        i_dc = self._bias_current
        i_rms_sq = i_dc * i_dc + 0.5 * i_ac * i_ac
        p_light = self._absorbed_thz_power()
        if i_rms_sq <= 0.0 and p_light <= 0.0:
            return t_bath
        t = t_bath
        for _ in range(4):    # R, n and Te all depend on one another
            r = self.sample.two_probe_resistance(
                self._gate_v, self._field, t, self._dirac_eff,
                self._top_gate_v)
            if not math.isfinite(r):
                break
            power = i_rms_sq * r + p_light
            t_lattice = (t_bath
                         + power * self.sample.thermal_resistance_K_per_W)
            n, p = self.sample.carrier_densities(
                self._gate_v, t, self._dirac_eff, self._top_gate_v)
            t = self.sample.electron_temperature(power, t_lattice, n + p)
        return t

    def ac_current(self) -> float:
        """Excitation current set by the lock-in oscillator, A."""
        return self._lockins["xx"].amplitude / self.BIAS_RESISTOR

    def _true_resistances(self) -> tuple[float, float]:
        t_e = self._electron_temperature()
        r_xx, r_xy = self.sample.resistances(
            self._gate_v, self._field, t_e, self._dirac_eff,
            self._top_gate_v)
        if self._oxide_damaged:
            # a punched-through oxide shunts the channel to the gate
            r_xx *= 0.3
            r_xy *= 0.3
        drift = 1.0 + self._drift
        return r_xx * drift, r_xy * drift

    # ==================================================================
    # noise
    # ==================================================================
    def _voltage_noise(self, resistance: float, time_constant: float
                       ) -> float:
        """One sample of voltage noise, V.

        Bandwidth follows the time constant the operator chose: a
        single-pole filter has an equivalent noise bandwidth of 1/(4 tau),
        so asking for a short time constant really does cost you noise.
        """
        if not self.faults.noise:
            return 0.0
        enbw = 1.0 / (4.0 * max(time_constant, 1e-4))
        t_e = max(self._electron_temperature(), 0.05)
        r = max(min(abs(resistance), 1e7), 1.0)
        johnson = math.sqrt(4.0 * K_B * t_e * r * enbw)
        amplifier = 5.0e-9 * math.sqrt(enbw)        # 5 nV/rtHz input noise
        return self._rng.gauss(0.0, math.hypot(johnson, amplifier))

    # ==================================================================
    # magnet
    # ==================================================================
    def set_field(self, value: float, rate: float | None = None) -> None:
        with self._lock:
            self._advance()
            target = max(-self.MAX_FIELD_T, min(self.MAX_FIELD_T,
                                                float(value)))
            if rate is not None:
                self._field_rate = min(abs(float(rate)),
                                       self.MAX_RAMP_T_PER_S)
            self._field_from = self._field
            self._field_target = target
            self._field_t0 = self._t

    def field(self) -> float:
        with self._lock:
            self._advance()
            return self._field

    def field_target(self) -> float:
        return self._field_target

    def field_rate(self) -> float:
        return self._field_rate

    def set_field_rate(self, value: float) -> None:
        with self._lock:
            self._field_rate = min(abs(float(value)), self.MAX_RAMP_T_PER_S)

    def magnet_state(self) -> float:
        """2 = holding, 1 = ramping, matching the AMI-430 convention."""
        with self._lock:
            self._advance()
            return 2.0 if self._field == self._field_target else 1.0

    # ==================================================================
    # cryostat
    # ==================================================================
    def set_temperature(self, value: float, rate: float | None = None
                        ) -> None:
        with self._lock:
            self._advance()
            self._temp_target = max(self.MIN_TEMPERATURE_K,
                                    min(self.MAX_TEMPERATURE_K,
                                        float(value)))
            if rate is not None:
                self._temp_rate = min(abs(float(rate)),
                                      self.MAX_TEMP_RATE_K_PER_S)

    def temperature(self) -> float:
        """What the thermometer reports — which may not be the truth."""
        with self._lock:
            self._advance()
            return max(0.0, self._temp_sample
                       - self.faults.thermometer_offset_K)

    def temperature_setpoint(self) -> float:
        return self._temp_target

    def heater_power(self) -> float:
        with self._lock:
            self._advance()
            err = self._temp_setpoint - self._temp_sample
            return max(0.0, min(100.0, 12.0 + 4.0 * err))

    # ==================================================================
    # gate
    # ==================================================================
    def set_gate_voltage(self, value: float) -> None:
        with self._lock:
            self._advance()
            v = float(value)
            self._gate_v = v
            self._max_gate_seen = max(self._max_gate_seen, abs(v))
            if abs(v) >= self.sample.breakdown_voltage_V:
                self._oxide_damaged = True

    def gate_voltage(self) -> float:
        with self._lock:
            self._advance()
            return self._gate_v

    def gate_current(self) -> float:
        """Leakage through the oxide, A — clamped at the compliance."""
        with self._lock:
            self._advance()
            leak = self.sample.gate_leakage(self._gate_v,
                                            self._oxide_damaged)
            leak += self.GATE_OFFSET_CURRENT_A
            if self.faults.noise:
                leak += self._rng.gauss(0.0, self.GATE_OFFSET_NOISE_A)
            limit = abs(self._gate_compliance)
            return max(-limit, min(limit, leak))

    def set_gate_compliance(self, value: float) -> None:
        self._gate_compliance = abs(float(value))

    def gate_compliance(self) -> float:
        return self._gate_compliance

    def oxide_damaged(self) -> bool:
        return self._oxide_damaged

    # ==================================================================
    # lock-ins
    # ==================================================================
    def _channel(self, which: str) -> _Lockin:
        return self._lockins[which]

    def set_lockin(self, which: str, field_name: str, value: float) -> None:
        with self._lock:
            self._advance()
            setattr(self._channel(which), field_name, float(value))

    def get_lockin(self, which: str, field_name: str) -> float:
        return float(getattr(self._channel(which), field_name))

    def lockin_xy_pair(self, which: str) -> tuple[float, float]:
        """In-phase and quadrature readings of one channel, V.

        The in-phase value is the sample voltage put through the time
        constant. The quadrature value is small and mostly noise, as it
        should be for a resistive sample — a reader who finds a large Y is
        being told the phase is wrong or the sample is reactive.
        """
        with self._lock:
            self._advance()
            self._reads += 1
            chan = self._channel(which)
            dt = max(self._t - chan.last_read, 0.0)
            chan.last_read = self._t
            i_ac = self.ac_current()
            r_xx, r_xy = self._true_resistances()
            resistance = r_xx if which == "xx" else r_xy

            if (self.faults.intermittent_contact > 0.0
                    and self._rng.random() < self.faults.intermittent_contact):
                # a dry joint: the Hall pair suffers most
                kick = 1.0 + self._rng.uniform(0.4, 2.5)
                resistance *= kick if which == "xy" else \
                    1.0 + 0.25 * (kick - 1.0)

            target = i_ac * resistance
            phase = math.radians(chan.phase)
            target_x = target * math.cos(phase)
            target_y = target * math.sin(phase)

            if self.faults.lockin_lag and chan.time_constant > 0.0:
                if not chan.primed:
                    chan.filtered = target_x
                    chan.filtered_q = target_y
                    chan.primed = True
                else:
                    # settling of a single-pole filter over the time that
                    # has actually elapsed since this channel was last read
                    a = 1.0 - math.exp(-dt / chan.time_constant)
                    chan.filtered += a * (target_x - chan.filtered)
                    chan.filtered_q += a * (target_y - chan.filtered_q)
                x, y = chan.filtered, chan.filtered_q
            else:
                x, y = target_x, target_y

            noise_x = self._voltage_noise(resistance, chan.time_constant)
            noise_y = self._voltage_noise(resistance, chan.time_constant)
            return x + noise_x, y + noise_y

    # ==================================================================
    # top gate (inert unless the sample has one)
    # ==================================================================
    def set_top_gate_voltage(self, value: float) -> None:
        with self._lock:
            self._advance()
            v = float(value)
            self._top_gate_v = v
            self._max_top_gate_seen = max(self._max_top_gate_seen, abs(v))

    def top_gate_voltage(self) -> float:
        with self._lock:
            self._advance()
            return self._top_gate_v

    def top_gate_current(self) -> float:
        """Leakage through the top dielectric, A."""
        with self._lock:
            self._advance()
            if not self.sample.has_top_gate:
                leak = 0.0
            else:
                leak = self.sample.gate_leakage(self._top_gate_v,
                                                self._oxide_damaged)
            leak += self.GATE_OFFSET_CURRENT_A
            if self.faults.noise:
                leak += self._rng.gauss(0.0, self.GATE_OFFSET_NOISE_A)
            limit = abs(self._top_gate_compliance)
            return max(-limit, min(limit, leak))

    def set_top_gate_compliance(self, value: float) -> None:
        self._top_gate_compliance = abs(float(value))

    def top_gate_compliance(self) -> float:
        return self._top_gate_compliance

    def displacement_field(self) -> float:
        """D/eps0 in V/nm. Zero on a single-gated device."""
        with self._lock:
            self._advance()
            return self.sample.displacement_field(
                self._gate_v, self._top_gate_v, self._dirac_eff)

    # ==================================================================
    # the light path
    # ==================================================================
    def set_thz_power(self, value: float) -> None:
        with self._lock:
            self._advance()
            self._thz_power = max(0.0, min(float(value),
                                           self.beam.max_source_power_W))

    def thz_power(self) -> float:
        return self._thz_power

    def set_thz_frequency(self, value: float) -> None:
        with self._lock:
            self._advance()
            self._thz_frequency = max(0.0, float(value))

    def thz_frequency(self) -> float:
        return self._thz_frequency

    def set_thz_output(self, value: float) -> None:
        """Shutter. Anything non-zero opens it."""
        with self._lock:
            self._advance()
            self._thz_output = bool(round(float(value)))

    def thz_output(self) -> float:
        return 1.0 if self._thz_output else 0.0

    def thz_power_monitor(self) -> float:
        """What the source's own power meter reads, W.

        This is the power leaving the source, not the power reaching the
        sample — there is no instrument anywhere on this rig that reports
        the latter.
        """
        with self._lock:
            self._advance()
            if not self._thz_output:
                base = 0.0
            else:
                base = self._thz_power
            if self.faults.noise and base > 0.0:
                base *= 1.0 + self._rng.gauss(0.0, 0.01)
            return max(0.0, base)

    def set_lens(self, axis: str, value: float) -> None:
        with self._lock:
            self._advance()
            setattr(self, f"_lens_{axis}", float(value))

    def lens(self, axis: str) -> float:
        with self._lock:
            self._advance()
            return float(getattr(self, f"_lens_{axis}"))

    # ==================================================================
    # dc source-measure unit (2-probe I-V, self-heating)
    # ==================================================================
    def set_bias_current(self, value: float) -> None:
        with self._lock:
            self._advance()
            self._bias_mode = "current"
            self._bias_current = float(value)
            self._max_bias_seen = max(self._max_bias_seen,
                                      abs(float(value)))

    def set_bias_voltage(self, value: float) -> None:
        with self._lock:
            self._advance()
            self._bias_mode = "voltage"
            self._bias_voltage_source = float(value)
            r = self.sample.two_probe_resistance(
                self._gate_v, self._field, self._electron_temperature(),
                self._dirac_eff, self._top_gate_v)
            self._bias_current = float(value) / max(r, 1.0)

    def set_bias_compliance_voltage(self, value: float) -> None:
        self._bias_compliance_v = abs(float(value))

    def bias_compliance_voltage(self) -> float:
        return self._bias_compliance_v

    def set_nplc(self, value: float) -> None:
        self._nplc = max(0.01, min(25.0, float(value)))

    def nplc(self) -> float:
        return self._nplc

    def bias_current(self) -> float:
        with self._lock:
            self._advance()
            i = self._bias_current
            if self.faults.noise:
                i += self._rng.gauss(0.0, 1e-12 / math.sqrt(self._nplc))
            return i

    def bias_voltage(self) -> float:
        """Two-probe voltage across the device, V — contacts included."""
        with self._lock:
            self._advance()
            r = self.sample.two_probe_resistance(
                self._gate_v, self._field, self._electron_temperature(),
                self._dirac_eff, self._top_gate_v)
            v = self._bias_current * r
            v = max(-self._bias_compliance_v,
                    min(self._bias_compliance_v, v))
            if self.faults.noise:
                enbw = 1.0 / (2.0 * self._nplc / 50.0)
                v += self._rng.gauss(
                    0.0, math.sqrt(4.0 * K_B * max(
                        self._electron_temperature(), 0.05)
                        * max(abs(r), 1.0) * enbw) + 2e-7)
            return v

    MIN_MEANINGFUL_BIAS_A = 1.0e-10
    """Below this the measured current is mostly the SMU's own noise, and
    V/I is a ratio of two noise values."""

    def bias_resistance(self) -> float:
        """Two-probe resistance, or NaN when no real current is flowing.

        The threshold is not cosmetic. The lab's bias safety rule converts
        through this number — the ceiling is 500 uA times R_2pt — so a
        plausible-looking value read at zero bias would hand back a
        permission that is off by orders of magnitude. Better NaN, which
        is obviously unusable, than a number that is quietly wrong.
        """
        i = self.bias_current()
        if abs(i) < self.MIN_MEANINGFUL_BIAS_A:
            return float("nan")
        return self.bias_voltage() / i

    # ==================================================================
    # for the bench, never for a driver
    # ==================================================================
    def truth(self) -> dict:
        """The answer key: hidden sample parameters and what the rig has
        been put through. Deliberately unreachable from any get_option."""
        with self._lock:
            self._advance()
            t_e = self._electron_temperature()
            n, p = self.sample.carrier_densities(
                self._gate_v, t_e, self._dirac_eff)
            r_xx, r_xy = self.sample.resistances(
                self._gate_v, self._field, t_e, self._dirac_eff)
            return {
                "sample": self.sample.truth(),
                "faults": asdict(self.faults),
                "seed": self._seed,
                "beam": self.beam.truth(),
                "state": {
                    "field_T": self._field,
                    "gate_V": self._gate_v,
                    "top_gate_V": self._top_gate_v,
                    "displacement_field_V_per_nm":
                        self.sample.displacement_field(
                            self._gate_v, self._top_gate_v,
                            self._dirac_eff),
                    "lens_mm": (self._lens_x, self._lens_y, self._lens_z),
                    "thz_output": self._thz_output,
                    "thz_source_power_W": self._thz_power,
                    "thz_frequency_Hz": self._thz_frequency,
                    "beam_coupling": self.beam.coupling(
                        self._lens_x, self._lens_y, self._lens_z),
                    "absorbed_thz_power_W": self._absorbed_thz_power(),
                    "dirac_voltage_effective": self._dirac_eff,
                    "bath_temperature_K": self._temp_sample,
                    "electron_temperature_K": t_e,
                    "ac_current_A": self.ac_current(),
                    "bias_current_A": self._bias_current,
                },
                "sample_now": {
                    "electron_density_cm2": n / 1e4,
                    "hole_density_cm2": p / 1e4,
                    "net_density_cm2": (n - p) / 1e4,
                    "R_xx_ohm": r_xx,
                    "R_xy_ohm": r_xy,
                    "mobility_cm2Vs": self.sample.mobility(
                        max(n, p), t_e) * 1e4,
                },
                "history": {
                    "max_abs_gate_V": self._max_gate_seen,
                    "max_abs_top_gate_V": self._max_top_gate_seen,
                    "max_abs_bias_A": self._max_bias_seen,
                    "max_abs_field_T": self._max_field_seen,
                    "oxide_damaged": self._oxide_damaged,
                    "readings": self._reads,
                    "uptime_s": self._t - self._t_started,
                },
            }


# ---------------------------------------------------------------------------
# the one rig every simulated driver talks to
# ---------------------------------------------------------------------------
_RIG: SimRig | None = None
_RIG_LOCK = threading.Lock()


def _config_path() -> str:
    """``config/sim_rig.json`` beside the running installation."""
    package = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    core = os.path.dirname(package)       # .../<core>/unisweep/sim -> <core>
    return os.path.join(core, "config", "sim_rig.json")


def _from_config() -> SimRig:
    sample = GrapheneSample()
    faults = SimFaults()
    beam = BeamPath()
    seed = 20260914
    path = _config_path()
    try:
        with open(path, "r", encoding="utf-8") as fh:
            cfg = json.load(fh) or {}
    except (OSError, ValueError):
        cfg = {}
    known_sample = {f.name for f in fields(GrapheneSample)}
    for key, value in (cfg.get("sample") or {}).items():
        if key in known_sample:
            setattr(sample, key, value)
    known_faults = {f.name for f in fields(SimFaults)}
    for key, value in (cfg.get("faults") or {}).items():
        if key in known_faults:
            setattr(faults, key, value)
    known_beam = {f.name for f in fields(BeamPath)}
    for key, value in (cfg.get("beam") or {}).items():
        if key in known_beam:
            setattr(beam, key, value)
    if isinstance(cfg.get("seed"), int):
        seed = cfg["seed"]
    start_t = cfg.get("sample_temperature")
    return SimRig(sample=sample, faults=faults, seed=seed,
                  initial_temperature=start_t, beam=beam)


def rig() -> SimRig:
    """The shared rig, built on first use."""
    global _RIG
    with _RIG_LOCK:
        if _RIG is None:
            _RIG = _from_config()
        return _RIG


def configure(sample: GrapheneSample | None = None,
              faults: SimFaults | None = None,
              seed: int | None = None, clock=None,
              initial_temperature: float | None = None,
              beam: BeamPath | None = None) -> SimRig:
    """Replace the shared rig — for tests and bench scenarios."""
    global _RIG
    with _RIG_LOCK:
        _RIG = SimRig(sample=sample, faults=faults,
                      seed=20260914 if seed is None else seed, clock=clock,
                      initial_temperature=initial_temperature, beam=beam)
        return _RIG


def reset() -> SimRig:
    """Put the existing rig back to its starting state."""
    r = rig()
    r.reset()
    return r
