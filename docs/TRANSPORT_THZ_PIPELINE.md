# Electronic transport under THz excitation — the lab's pipeline

What this lab does: conventional electron transport, characterised against
magnetic field, **compared with the same device under light**. The light is
THz or sub-THz, and it either heats the electron bath non-resonantly
(Drude absorption) or drives the system commensurately where there are
flat bands. The power of the method is the comparison, so the dark
measurement is not a warm-up — it is half the experiment, and it has to be
good enough to be the reference.

This document is *method*, not API. The lab profile
(`config/lab_profile.json`) says what the knobs are and where the fences
are; this says what to do with them and in what order. Read both.

---

## The standing rules

**Check the simple slice before committing to the long map.** Take it,
look at it, and let it set the limits, the resolution and the time
constant for the map. A map started from assumptions is a map you will
throw away.

**Resolution: about 100 points per axis is usually enough.** Vary it with
the size of the features you are trying to resolve and with how much time
there is. Finer where the physics is; coarser where it is not.

**Time constant against dwell: at least 5 τ per point.** Less and the
curve lags, direction-dependently, and nothing warns you. Noise falls as
`sqrt(1/4τ)` until 1/f drift takes over near a second, past which a longer
time constant buys nothing.

**Frequency: push it up until the lock-in's Y reaches about 10% of X, then
stop.** Higher frequency means less 1/f noise and faster settling; past
the point where the quadrature becomes noticeable, the sample or the
wiring is reactive and X is no longer just a resistance.

**The thermometer measures the bath, not the electrons.** Once current
flows or the beam is on, the electron temperature is somewhere else. How
far is a property of the device, not a constant: the heating goes as
`I^2 R`, and the cooling coupling scales with carrier density, so the same
current lifts a resistive, lightly doped device far more than a degenerate
one. Order of magnitude on an ordinary device at 4 K, tenths of a kelvin
at a microamp and several to tens of kelvin at ten microamps — but do not
carry those as numbers. Measure the onset on the device in front of you:
sweep the bias, watch Rxx against a low-current baseline, and find where
it leaves it. A bias sweep is a temperature sweep whether or not that was
the intention.

---

## 0. Sample in, cold, contacts checked

Sample into the holder, pins assigned on the breakout box, into the
cryostat, down to base. Then **check every contact pair resistance** — it
is the cheapest way to find a dead contact, and every number you take
afterwards depends on it.

On the simulated rig the breakout box cannot be switched, so treat this
step as already done.

---

## 1. Gate safety — the leak hunt

**Nothing else starts until this is finished.**

1. Sample cold, gate at 0 V. Start measuring Rxx.
2. Read the gate current. **It will not be zero.** A nanoamp or two at
   zero volts is the source-measure unit's own offset, not the device.
   Write that floor down; it is what everything after is judged against.
3. Sweep the gate outward, left to right, in **slowly increasing ranges**,
   watching the leakage the whole way.
4. Past some voltage the leakage climbs **exponentially out of the offset
   floor**. **The onset of that climb is the safe gate limit** for the
   rest of the cooldown.

Priors, not permissions — the measured onset always wins:

| Dielectric | Expect the onset around | Never go past unless there is a real reason |
|---|---|---|
| hBN | ~10 V | 10 V |
| SiO2 (300 nm) | ~55–60 V | 60 V |

A per-point script is the right guard while hunting, because it acts
before the next point:

```python
if abs(reads["SIM::GATE.current"]) > 4e-9:   # scale to YOUR measured floor
    stop()
```

On a dual-gated device run the hunt on **both** gates. The top dielectric
is usually thinner hBN, so it is the more fragile one and its limit
binds.

---

## 2. Bias safety — and it is coupled to the gate

Two cases, and they are not the same.

**Bias the SAME SIGN as the gate.** The out-of-plane field is compensated
from both sides, so the dielectric is not at risk. What limits you instead
is current through the sheet:

> **Never more than 500 µA through a 2D device.**

Take the characteristic two-point resistance and convert:
`|V_bias| ≤ 500 µA × R_2pt`. Measure `R_2pt` with current actually
flowing — at zero bias it is the ratio of two noise values and means
nothing.

**Bias the OPPOSITE SIGN to the gate.** Now the two fields add and the
dielectric *is* at risk. **Halve both limits**: half the safe gate voltage
and half the bias ceiling, so the combined out-of-plane field stays inside
the envelope the leak hunt established.

This rule is **coupled** — the allowed gate depends on the bias sign, the
allowed bias depends on a measured resistance — and a static min/max
cannot express it. It is deliberately left as procedure. Check it before
every bias change; nothing will check it for you.

---

## 3. Zero field, base temperature

The first real measurement. On a graphene device:

**Rxx, Rxy and R2pt against gate voltage, at base temperature.**

This is the slice that tells you whether anything else is worth doing.
From it: where the Dirac point actually is, how sharp it is, what the
mobility looks like, whether the contacts behave. `R2pt − R4pt` is the
contact resistance.

If it looks right, go on. If it does not, find out why before spending
hours on a map.

---

## 4. Temperature

**A 2-D map of the same three quantities against gate voltage and
temperature.** Base to 300 K if there is time.

If there is not, **upload custom steps**: uneven, spread out at the high
end. The interesting structure is at the cold end and the high end only
needs to be covered, not resolved. A manual step table costs nothing and
saves hours against a uniform grid.

---

## 5. Magnetic field

In this order, each step setting up the next:

1. **Rxx, Rxy against B**, at a few gate voltages in the doped regime.
   Symmetrise: `Rxy_true(B) = [Rxy(+B) − Rxy(−B)]/2`. The Hall probes are
   never exactly opposite, so the raw Rxy carries a slice of Rxx, even in
   B while the Hall signal is odd. Nothing but symmetrising removes it,
   and an unsymmetrised Hall density is wrong by that fraction times the
   aspect ratio.

2. **A slice at fixed quantizing B against Vg**, to extract the slope of
   Rxy — and from it the gate capacitance, which **confirms the hBN
   thickness**. A discrepancy here means the geometry you think you have
   is not the geometry you have.

3. Now you know the size of the quantization features, so you can **pick a
   resolution**. Then the **Landau fan**: Rxx and Rxy against Vg and B.

4. If the device is expected to be a half metal, a quarter metal, a
   compensated semimetal, or to have any other unusual quantum structure,
   **magnetic field is the strongest tool you have.** Raise the resolution
   of the fan at *non-quantizing* fields to record Shubnikov–de Haas
   oscillations, and do the fermiology: the oscillation frequency in 1/B
   gives the size of each Fermi surface, and the number of frequencies
   gives how many there are.

5. **Repeat at different displacement fields** if the device has a top
   gate. Density follows the weighted sum of the two gates, D follows
   their weighted difference — so a D-dependence study sweeps along lines
   of constant density, which is a condition on the sweep page, not a
   property of either gate.

6. **Effective mass.** At the gate voltages that turned out interesting,
   run SdH scans at a series of temperatures, extract the damping of the
   oscillation amplitude, and fit it with Lifshitz–Kosevich.

That is the basic characterisation. **If something interesting turns up
along the way, roam.** Take more data around that region of the parameter
space. The pipeline is a floor, not a ceiling.

---

## 6. Optics — calibrating the lens

The beam is guided by lenses and mirrors to the cryostat. The **final lens
sits on an XYZ stage**, so it can deflect the beam across the sample. That
is what makes a beam scan possible, and the scan is how the lens gets
positioned.

**Focus Z first.** Defocused, the coupling structure blurs into a single
blob and there is nothing left to centre on.

**Then scan X and Y and record the resistance with the source on.**

> **The correct lens position is the point of highest symmetry of the
> photoresponse map — not the point of highest signal.**

Why they differ: at sub-THz the coupling structure is an antenna, and an
antenna is wavelength-scale, so the beam *can* resolve it. Its lobes sit
symmetrically about the device, because that is lithography. Their
strengths are not equal, because that is fabrication. So the maximum lands
on the stronger lobe. The intensity centroid is pulled the same way but
far less, being weighted by the whole pattern rather than by its brightest
point — on the simulated rig roughly 0.08 mm against the maximum's 0.45 —
and only the **geometric centre of the lobe positions** is the device.

Find the features, take their geometric centre, and keep their brightness
out of the arithmetic. On the simulated rig taking the maximum instead
puts the lens 0.45 mm out, and every optical measurement afterwards
inherits that error.

---

## 7. Under light

With the lens calibrated:

1. **Repeat the Rxx, R2pt against Vg and T map**, now with the beam on.
   The comparison against the dark map is the measurement.

2. **In the dark, measure Rxx and R2pt against bias current** — or against
   bias voltage while recording the source-drain current, though bias
   voltage is limited by roughly the bandwidth of the sample. This gives
   the resistance as a function of known DC Joule power, and therefore
   **as a function of electron temperature**.

   That curve is the calibration. Read the photoresistance against it and
   you have **the absorbed THz power**, and the temperature it corresponds
   to. This works because Joule heating and absorbed light land in the
   same electron bath; if they did not, the comparison would be measuring
   nothing.

   There is no instrument anywhere that reports absorbed power. This is
   how you get it.

3. **Repeat at different light powers**, and at different carrier
   densities, to extract **Te against P_abs**.

   That relation is the point of the whole exercise. The electrons cool
   through `P/A = Σ(Te^δ − T_lattice^δ)`, and the exponent names the
   channel: δ = 3 is disorder-assisted supercollision cooling, δ = 4 is
   clean acoustic-phonon cooling. Σ scales linearly with carrier density,
   which is why the density dependence is worth the extra runs. Between
   them, δ and Σ(n) tell you how this device gets rid of heat.

---

## What the operator has to supply

None of this can be derived from the instruments, and the assignment has
to state it:

- the dielectric and its thickness, and whether there is a top gate;
- the expected Dirac point, if there is one;
- what the device is supposed to be, and what would be interesting;
- and, once it has been measured, **the safe gate limit from this
  cooldown's leak hunt**.

Everything else the rig can find out for itself.
