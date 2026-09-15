# The simulated graphene rig

A monolayer-graphene Hall bar on 300 nm SiO2, with a magnet, a back gate, a
cryostat, two lock-ins and a DC source-measure unit. It installs exactly
like real hardware and Unisweep cannot tell the difference.

Two reasons it exists:

1. **A fresh installation has something to measure.** Clone Unisweep, start
   it, and you can take a real 2-D map on your first day with no
   instruments on the bench.
2. **An assistant can be trained and examined without risking a sample.**
   The rig knows the truth about itself — the carrier density, the
   mobility, the Dirac point, whether the gate oxide has been destroyed —
   so a measurement of it can be *scored*, not merely admired.

---

## How Unisweep talks to a device

Worth stating plainly, because the simulated instruments obey exactly the
same contract as the real ones and nothing about them is special-cased.

There is **no base class and no registration call**. A driver is a plain
Python file in `resources/` containing a class, and `DeviceRegistry` finds
it by duck typing (`unisweep/core/devices.py`):

1. **Discovery.** Every `<Name>.py` in `resources/` is imported by path at
   startup. The class is matched to the file name case-insensitively, and
   failing that, by looking for the one class in the file that takes an
   `adress` argument or declares option lists. An import failure is
   captured and shown on the Devices page rather than lost.
2. **Assignment.** `config/address_dictionary.txt` is a JSON map of
   address → driver class name. That is what the Devices page edits.
3. **Connection is lazy.** Nothing is opened until an address is actually
   used, and then exactly once: `cls(adress=address)` — note the legacy
   spelling. One adapter per address for the life of the process.
4. **Everything after that goes through `DriverAdapter`**, which is the
   only thing the engine, the GUI and the agent ever touch:

   | The adapter needs | The driver provides |
   |---|---|
   | what can be set | `self.set_options = ['field', ...]` — a **literal list** in `__init__` |
   | what can be read | `self.get_options = ['x', 'y', ...]` — likewise |
   | a reading | a method named exactly as the option: `x()` returns a number |
   | a setting | `set_<option>(value, speed=None)` |
   | can it ramp? | `self.sweepable = [True, False, ...]`, positional against `set_options` |
   | how fast | `self.maxspeed = [...]`, `self.eps = [...]`, same positions |
   | what to record | `self.loggable = ['IDN', ...]` — called once per sweep into the provenance sidecar |
   | identity | `IDN()` |
   | shutdown | `close()`, optional `pause()`, `clear()` |

   The option lists must be **literal lists assigned in `__init__`**,
   because `DeviceRegistry._probe_options` reads them out of the source
   with `ast` so a device can be listed on the sweep page without being
   connected. A list built any other way makes the device look optionless
   until you connect it. `tests/test_sim.py` pins this.

5. **During a sweep** the engine calls `adapter.set(parameter, value,
   speed=...)` on each axis, waits `delay`, then calls `adapter.get(option)`
   for every entry in the program's `reads`. `speed` is only passed on if
   the setter's signature actually has it. Every route to hardware —
   engine, Set/Get page, agent `set_parameter` — goes through
   `DriverAdapter.set`, which is where the lab-profile limits are enforced.

The swept-axis column arrives in the CSV as a **preformatted string**
(`'0.000e+00'`), while read channels are floats. Worth knowing before you
parse a file.

---

## How the instruments know about each other

The obvious worry: if the magnet, the gate and the lock-ins are separate
driver objects, how does the lock-in know what field it is sitting in?

**They share one rig object.** `unisweep/sim/rig.py` holds a single
module-level `SimRig` — the sample, the field, the gate voltage, the
temperature, the bias — and every `Sim*` driver calls `rig()` in its
`__init__` to get it. The drivers are instrument *faces*; none of them
owns any state. Six driver files, one piece of graphene.

This works inside the running app because `unisweep` is a normal package
import: `main.py` sits in the core directory, so Python puts that
directory on `sys.path` and every driver in `resources/` resolves
`from unisweep.sim.rig import rig` to the same module, hence the same
`SimRig`. A test asserts it (`test_every_instrument_is_looking_at_the_same_piece_of_graphene`):
it drives the gate through `SimGate` and watches `SimLockinXX` respond.

**A per-point script cannot do this job**, which is worth being explicit
about since it is the natural thing to reach for:

* the script runs *after* a point has been measured, so it could not
  influence the reading of the point it belongs to — it would always be
  one point late;
* it would have to be configured correctly on every sweep, and a sweep
  where someone forgot would silently return a lock-in that thinks the
  field is zero;
* the coupling is a property of the apparatus, not of the measurement
  program. Wiring it through the program means the apparatus changes when
  you change what you are measuring.

What a per-point script *is* for here is **reacting** to a measured
value — and the gate leakage is the case worth having. Put this in the
script box (`resources` is not involved; it is saved under
`<core>/<YYMMDD>/scripts` by the Load/Save buttons):

```python
# stop before the oxide does something permanent
if abs(reads["SIM::GATE.current"]) > 2e-9:
    stop()
```

If you want the field, gate and temperature to appear **as columns** in
the CSV, you do not need a script for that either — add them to the
program's reads:

```
SIM::MAGNET.field, SIM::GATE.voltage, SIM::CRYOSTAT.temperature
```

Reading a channel is how a value gets into a row. The script is how a
value changes what happens next.

---

## Setting it up

1. Copy these nine files from `devices/` into `resources/`:

   ```
   SimMagnet.py  SimGate.py  SimTopGate.py  SimCryostat.py
   SimLockinXX.py  SimLockinXY.py  SimSMU.py
   SimTHzSource.py  SimLensStage.py
   ```

2. On the **Devices** page, add these addresses and assign each its driver.
   The addresses are arbitrary strings — nothing is dialled — but the lab
   profile below expects these:

   | Address | Driver |
   |---|---|
   | `SIM::MAGNET` | SimMagnet |
   | `SIM::GATE` | SimGate |
   | `SIM::TOPGATE` | SimTopGate |
   | `SIM::CRYOSTAT` | SimCryostat |
   | `SIM::LOCKIN::XX` | SimLockinXX |
   | `SIM::LOCKIN::XY` | SimLockinXY |
   | `SIM::SMU` | SimSMU |
   | `SIM::THZ` | SimTHzSource |
   | `SIM::LENS` | SimLensStage |

   `config/address_dictionary.txt` already carries these, so they appear
   on the Devices page as soon as the driver files are in `resources/`.

3. `config/lab_profile.json` is already in place, so the safety layer is
   on. (`lab_profile.sim.json` is a copy kept as a backup; the loader only
   reads `lab_profile.json`.)

   **That profile is not about this rig.** Its first and largest section is
   a taxonomy of the *kinds* of instrument this lab uses — lock-ins,
   source-measure units, DC voltage and current sources, voltmeters,
   temperature controllers, magnet supplies, integrated cryostats,
   closed- and open-loop positioners, shutters, waveform generators, DAQs,
   spectrometers, laser sources, scopes, VNAs, spectrum analysers — each
   with what it is for, what it can damage, and how it is used properly. A
   specific address then declares its class and inherits the meaning.

   A driver the profile has never heard of is placed by matching its own
   option names against the class signatures (`LabProfile.classify`). Over
   the 41 drivers in `devices/` that declare literal option lists, the top
   candidate is right 35 times; the rest are either genuinely two classes
   at once (an integrated cryostat really is a temperature controller and
   a magnet supply) or expose too few option names to be placed, and
   returning nothing is the right answer there. Every driver in the lab is
   also bound explicitly by name, and that binding wins.

You do not need all nine. Gate plus one lock-in is enough for a transfer
curve; add the magnet for anything Hall, and the source and stage for
anything optical.

The full measurement pipeline this rig exists to rehearse — the leak hunt,
the coupled bias rule, the fan, the beam-scan calibration, the Te against
absorbed-power series — is in **`docs/TRANSPORT_THZ_PIPELINE.md`**.

---

## What each instrument is

| Instrument | Sets | Reads | Behaves like |
|---|---|---|---|
| **SimMagnet** | `field`, `ramp_rate` | `field`, `target_field`, `state` | AMI-430: commands a ramp and returns; the readback is wherever it has got to |
| **SimGate** | `voltage`, `compliance_current` | `voltage`, `current` | a gate SMU: `current` is the oxide leakage, and it is not decorative |
| **SimCryostat** | `temperature` | `temperature`, `setpoint`, `heater_power` | a VTI: the sample lags the setpoint by ~18 s |
| **SimLockinXX** | `amplitude`, `frequency`, `time_constant`, `sensitivity`, `phase` | `x`, `y`, `r`, `Θ`, `excitation_current` | SR830 on the longitudinal pair. **Its oscillator drives the sample**: I = amplitude / 1 Mohm |
| **SimLockinXY** | as above | as above | SR830 on the Hall pair. A slave — changing *its* amplitude changes nothing |
| **SimSMU** | `source_current`, `source_voltage`, `compliance_voltage`, `NPLC` | `current`, `voltage`, `resistance` | a DC SMU across source-drain. **Two-probe**, so its voltage includes the contacts |
| **SimTopGate** | `voltage`, `compliance_current` | `voltage`, `current`, `displacement_field` | a second gate SMU. Inert unless the sample has a top gate |
| **SimTHzSource** | `power`, `frequency`, `output` | the same + `power_monitor` | a sub-THz multiplier chain with a shutter. The monitor reads what *leaves the source* |
| **SimLensStage** | `x`, `y`, `z` | the same | the XYZ stage carrying the final lens before the cryostat window |

The lock-ins read **volts**, not ohms. Dividing by the excitation current
is the lab profile's job (`Rxx = Vxx / I_ac`), which is what derived
channels are for.

The rig starts **cold, at 4.2 K, with the field at zero and the gate at
zero** — the state a cryostat is in when you sit down at it. Starting at
room temperature would be equally defensible and would put a
two-and-a-half minute cooldown in front of every first measurement, so it
is opt-in (`sample_temperature` in `config/sim_rig.json`).

---

## Your first sweep

Nothing needs configuring. On the 1-D sweeper:

| Field | Value |
|---|---|
| Device / parameter | `SIM::GATE` / `voltage` |
| From / to | −20 → 40 V |
| Step | 2 V (count mode *step*) |
| Delay | 0.15 s |
| Reads | `SIM::LOCKIN::XX.x`, `SIM::LOCKIN::XY.x` |

That gives the transfer curve, about 30 points in 5 seconds, with Vxx
running from roughly 78 µV off to one side up to 375 µV at the peak on
100 nA of excitation — i.e. 780 Ω to 3.8 kΩ, peaking at the Dirac point
near +8.5 V.

**The one setting that will bite you is the time constant against the
delay.** The lock-in defaults to τ = 30 ms at 77.77 Hz, so 0.15 s per
point is five time constants and the reading is settled. Raise τ to
300 ms without raising the delay and the curve comes back lagged and
direction-dependent, with no warning — exactly as it would on the bench.
Rule of thumb: **delay ≥ 5 τ**.

For the Hall measurement, set `SIM::GATE.voltage` to about 33 V first
(that is 25 V past the Dirac point), then sweep `SIM::MAGNET.field` from
−1 to +1 T. The magnet is `sweepable`, so the engine ramps it
continuously and samples on the delay timer rather than stepping — 0.05 s
per point at 0.1 T/s gives a point every 5 mT.

Verified end to end through the real `SweepEngine`: a symmetrised Hall
slope of −345 Ω/T gives n = 1.807e12 cm⁻², against 1.796e12 expected from
the gate — 0.6% out. The even part of Rxy comes to 2.5% of Rxx, which is
the probe misalignment the sample was built with.

---

## The physics, and where it comes from

`unisweep/sim/graphene.py` is pure: given a gate voltage, a field, a
temperature and a bias, it returns what the sample does. Nothing in it
knows about time or instruments.

**Carrier density.** A parallel-plate back gate: 300 nm SiO2 gives
1.15e-4 F/m², i.e. **7.18e10 cm^-2 per volt**. At the Dirac point the
density does not reach zero — disorder breaks the sheet into
electron/hole puddles, and thermal excitation adds carriers of both signs
(8.1e10 cm^-2 at 300 K). Both fold into a residual density `n_0`, and the
two populations follow the mass-action form `n·p = n_0²`, `n − p = n_cv`.

**Scattering.** Graphene's linear dispersion makes the resistivity from
isotropic scatterers *independent of carrier density*, which is why the
phonon terms are added to the resistivity rather than to a mobility:

| Channel | Form | Anchored to |
|---|---|---|
| charged impurities | constant mobility `mu_imp` | the device's own quality |
| acoustic phonons | `0.1 Ω/K × T` | 30 Ω at 300 K (Chen 2008) |
| SiO2 surface polar phonons | `B / (exp(59 meV / kT) − 1)` | RT mobility ceiling 4e4 cm²/Vs |
| short range | a constant | a resistivity floor |

The surface-phonon prefactor has no free parameter: it is fixed by those
two published numbers.

**Magnetotransport.** Two carrier species in a Drude conductivity tensor.
Not a convenience — a single-carrier model gives exactly flat
magnetoresistance and a Hall slope that never turns over, whereas real
graphene near neutrality shows strong positive magnetoresistance and a
non-linear, sign-changing Hall response. Both fall out of the tensor.

**Quantum regime.** Landau quantisation is blended in with a weight
`w = R_T · R_D` from the Lifshitz–Kosevich thermal factor and the Dingle
factor, so the same damping that sets the oscillation amplitude also sets
how well the plateaus form. The cyclotron mass is the Dirac one,
`m_c = ħ√(πn)/v_F`. Oscillations are periodic in 1/B with frequency
`B_F = n h / 4e`, and — the part specific to graphene — the minima sit at
**half-integer** `B_F/B`, giving `ν = ±2, ±6, ±10, …`. That offset is the
Berry phase of π, and it is what a fan diagram or an SdH phase fit is
supposed to recover.

The Dingle temperature is set empirically (8 K by default) to reproduce
the observed onset of oscillations in a device of this mobility, not
derived from a quantum lifetime.

### Sources

* J.-H. Chen, C. Jang, S. Xiao, M. Ishigami, M. S. Fuhrer, *Intrinsic and
  extrinsic performance limits of graphene devices on SiO2*, Nature
  Nanotechnology **3**, 206 (2008); arXiv:0711.3646.
* V. E. Dorgan, M.-H. Bae, E. Pop, *Mobility and saturation velocity in
  graphene on SiO2*, Appl. Phys. Lett. **97**, 082112 (2010).
* Residual density by quantum capacitance, Appl. Phys. Lett. **102**,
  173507 (2013); arXiv:1304.3957.
* A. Konar, T. Fang, D. Jena, surface polar phonon transport in graphene,
  arXiv:1010.4772 (SiO2 mode at 60.0 meV).

---

## The ways it lies

`unisweep/sim/rig.py` is where a measurement stops being the truth. These
are on by default, because they are ordinary instrumentation and a
competent measurement handles them:

| What | Consequence if ignored |
|---|---|
| **Lock-in time constant** | The reading is filtered over the time elapsed since *that channel* was last read. Sweep faster than a few τ per point and the curve lags — direction-dependently, with no warning. Default τ = 30 ms; keep delay ≥ 5 τ. |
| **Johnson + amplifier noise** | Bandwidth is `1/(4τ)`, so a short time constant really does cost signal-to-noise. |
| **1/f drift** | ~1e-4 relative, 30 s correlation. Past about a second of time constant, averaging stops helping. |
| **Magnet ramp rate** | 0.1 T/s maximum. `field()` reports where it is, not where you asked it to go. |
| **Thermal lag** | The sample reaches the setpoint about 18 s after the controller does. |
| **Self-heating** | `ΔT = P × 1e4 K/W`. At 1 mA the electrons are tens of kelvin above the bath and the thermometer does not notice. |
| **Hall probe misalignment** | Rxy carries ~2.5% of Rxx. Even in B, so `[Rxy(+B) − Rxy(−B)]/2` removes it exactly and nothing else does. |
| **Contact resistance** | ~420 Ω per contact. Cancels in a four-probe lock-in measurement, does not cancel in the two-probe SMU one. The difference is how you measure it. |
| **Gate leakage and breakdown** | The SMU reads 1–2 nA of its own offset at zero volts. The device's leak climbs exponentially *out of* that floor, emerging near 55 V on 300 nm SiO2 and near 11 V on 30 nm hBN. **That emergence is what the safe gate limit is.** Past 85 V the oxide is destroyed — permanently, until `reset()`. |
| **Electron heating** | Current and light both land in the same electron bath, through `P/A = Σ(Te³ − T_lattice³)` with Σ ∝ density. 100 nA is under a tenth of a kelvin; 1 µA is several; 10 µA is tens. The thermometer reports none of it. |
| **Beam alignment** | The antenna's lobes are symmetric in position and unequal in strength, so the brightest point of a photoresponse map is 0.45 mm from the device. Take the geometric centre of the lobes. Focus Z first or there are no lobes to find. |

These are **off** by default and switched on per scenario:

| Fault | What it does |
|---|---|
| `gate_hysteresis` | Charge trapping drags the Dirac point toward the gate voltage being held, so it depends on sweep direction and speed |
| `intermittent_contact` | A dry joint that glitches, hitting the Hall channel hardest — a plausible-looking but wrong Hall slope |
| `thermometer_offset_K` | The thermometer reads low by a constant; the sample really is where the model says |

---

## Configuring it

`config/sim_rig.json`, if present, overrides any field of the sample or
the faults:

```json
{
  "sample": {
    "dirac_voltage": -3.0,
    "mobility_impurity_cm2Vs": 40000,
    "puddle_density_cm2": 5e10,
    "dingle_temperature_K": 3.0
  },
  "faults": { "gate_hysteresis": 0.08, "intermittent_contact": 0.002 },
  "sample_temperature": 295.0,
  "seed": 7
}
```

Those particular numbers give a clean device that reaches the ν = 2
plateau within 1% of h/2e² above about 8 T, with ρxx falling from 410 to
31 Ω/□.

From Python — for tests and, later, bench scenarios:

```python
from unisweep.sim import GrapheneSample, SimFaults, configure

configure(sample=GrapheneSample(dirac_voltage=-3.0),
          faults=SimFaults(intermittent_contact=0.01),
          seed=11)
```

---

## Things worth measuring on it

Roughly in order of difficulty. Each has a right answer the rig knows.

1. **Transfer curve.** Sweep the gate at 4 K, read Vxx. Find the Dirac
   point. Compare the width of the peak to the puddle density.
2. **Field sweep and Hall density.** Fix the gate, sweep B from −1 to +1 T,
   read Vxy. Symmetrise, take the slope, get n. Compare it with
   `7.18e10 × (Vg − V_Dirac)`. They agree far from the Dirac point and do
   not agree near it — work out why before believing either.
3. **Mobility.** Combine the Hall density with ρxx. Watch out for the
   aspect ratio: L/W = 3.
4. **Contact resistance.** Two-probe minus four-probe.
5. **R(T).** Sweep temperature at fixed gate. Separate the constant
   impurity term, the linear acoustic term and the activated surface-phonon
   term above 200 K.
6. **Shubnikov–de Haas.** 1.8 K, sweep B to 9 T at fixed density. FFT in
   1/B. The frequency gives n; the phase gives the Berry phase; the
   temperature dependence of the amplitude gives the cyclotron mass.
7. **Landau fan.** A 2-D map of ρxx against B and Vg. The fan lines
   extrapolate to the Dirac point.
8. **Quantum Hall.** Find the plateaus; check they sit at h/νe² with
   ν = 2, 6, 10.
9. **Self-heating.** Sweep the bias current and watch the resistance move
   because the sample, not the bath, is getting warmer.

---

## The answer key

`SimRig.truth()` returns the hidden parameters and what the rig has been
put through — the sample's real density and mobility, the effective Dirac
point, the electron temperature, the maximum gate voltage ever applied,
and whether the oxide is damaged.

**No driver can reach it.** It is not in any `get_options` list and there
is no method on any `Sim*` class that returns it; a test asserts this. It
exists so that a measurement can be scored against the thing being
measured, which is the whole reason to have a simulator rather than a
second real sample.

---

## What is deliberately not modelled

Electron–electron interaction effects, the ν = 0 and ν = ±1
broken-symmetry states at high field, fractional filling, ballistic and
hydrodynamic transport, quantum capacitance corrections to the gate, and
weak localisation (present in the code, off by default — it puts a sharp
even-in-B feature at zero field that complicates a first Hall extraction).

None are needed for the measurements above, and each would add parameters
that the published numbers cannot pin.

---

## Tests

```
python -m pytest tests/test_sim.py -q
```

80 tests, about a quarter of a second, no display and no hardware. They
pin the physics landmarks against the literature and the drivers against
Unisweep's duck-typed driver contract. Several exist because the bug they
describe actually happened:

* `test_the_hall_curve_has_no_cliffs_in_it` — a `floor()` in the plateau
  staircase put a 3.8 kΩ vertical jump in Rxy(B).
* `test_both_channels_advance_when_a_point_reads_both` — found by running
  a real sweep. Every point reads Vxx and then Vxy microseconds apart, and
  while the filter used the time since the rig was last touched by
  *anything*, the second channel saw dt = 0 and came back frozen for the
  whole sweep while the first tracked perfectly. Each channel keeps its
  own last-read clock now.
* `test_the_default_time_constant_settles_within_an_ordinary_point` —
  whoever runs the first sweep will not have touched the lock-in, and a
  default τ comparable to a normal per-point delay makes the simulator
  look broken rather than like a lock-in doing its job.
