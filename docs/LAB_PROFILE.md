# The lab profile: what the instruments mean, and what they may not do

Unisweep's registry knows that `GPIB0::4::INSTR.A_source_voltage` is a
settable float. It does not know that this is the back gate of a graphene
Hall bar, that it is measured in volts, or that past ±8 V the oxide punches
through.

That knowledge goes in one file per rig:

```
config/lab_profile.json          (or lab_profile.yaml, if PyYAML is installed)
```

`docs/lab_profile.example.json` is a filled-in template for a transport
setup — copy it to `config/`, replace the addresses, and **check every
limit against your own device.** A wrong limit is worse than no limit,
because it buys confidence you have not earned.

Everything below is optional. With no profile file, Unisweep behaves
exactly as it did before: no limits, no pre-flight.

---

## What one file gives you

**Semantics.** Every parameter can carry an `alias`, a `unit` and a
`quantity`. Once `A_source_voltage` is `Vbg [V] back gate voltage`, error
messages, the Set & Get page and anything driving Unisweep can name the
thing you actually care about.

**Limits.** `min`, `max`, `max_rate`, `max_step` and `safe_value` are
enforced inside `DriverAdapter.set`. Every route to the hardware goes
through that one method: the sweep engine, the Devices page's *Test*
button, a per-point script, an automation agent. There is no path that
skips the check.

**Interlocks.** Whole-run ceilings checked before a sweep may start.

**Derived channels.** `Rxx = Vxx / I_ac`, written once. These are purely a
*reading* convenience — they are never written to the data files and the
sweep engine never evaluates them, so nothing about a measurement depends
on them. They exist so that asking for "Rxx" gives ohms rather than
lock-in volts.

---

## Anatomy

```jsonc
{
  "lab": "electronic transport",
  "autonomy": "bounded",              // readonly | bounded | full
  "sample":    { "id": "GR-2026-09-A", "material": "..." },
  "constants": { "I_ac": 1e-7 },

  "devices": {
    "GPIB0::4::INSTR": {
      "alias":  "gate",
      "driver": "keithley_series_2600b",
      "role":   "back-gate source-measure unit, channel A",
      "notes":  "channel A drives the graphite back gate",
      "parameters": {
        "A_source_voltage": {
          "alias": "Vbg", "unit": "V", "quantity": "back gate voltage",
          "min": -8.0, "max": 8.0,
          "max_rate": 0.5,            // units/second ceiling for ramps
          "max_step": 0.1,            // biggest single JUMP allowed
          "safe_value": 0.0           // where "park safely" puts it
        },
        "A_current": { "alias": "Ileak", "unit": "A", "settable": false }
      }
    }
  },

  "derived": {
    "Rxx": { "expression": "Vxx / I_ac", "unit": "ohm" }
  },

  "interlocks": {
    "max_points": 500000,
    "max_duration_s": 172800,
    "exclusive_ramps": [["B", "T"]],  // never sweep these together
    "require_preflight": true,
    "allow_script": true              // the per-point script; see below
  }
}
```

Any parameter can be named three ways, and all three resolve:
its alias (`Vbg`), `<device alias>.<parameter>` (`gate.A_source_voltage`),
or `<address>.<parameter>` — the spelling the engine and the CSV headers
already use.

### `max_rate` versus `max_step`

They protect different things and are enforced differently.

* `max_rate` clamps the *speed* handed to a self-ramping instrument. It
  also applies when no speed was given, so "no rate specified" can never
  mean "slew at the instrument's maximum".
* `max_step` bounds a single **jump** — a `set` with no ramp behind it.
  It does not apply to a ramp, because handing a magnet one setpoint and
  a rate is a travel instruction, not a jump. On a gate line the jump is
  the dangerous one, so that is exactly where the ceiling sits.

### Safety moves are clamped, never refused

Ramping to zero and parking at `safe_value` pass `safety=True`, which
clamps into the allowed range instead of raising. A protection mechanism
that the limits themselves can veto would be worse than no protection.

---

## Reacting to a measured value

The `condition` field masks which points get *taken*, from the axis
setpoints alone. To react to something that was just **measured** — stop
when a gate leakage runs away, pull a range in where a resistance turns
over — use the **per-point script** on the sweep page.

Unisweep has no opinion about what a channel means: `GPIB0::4::INSTR.A_current`
is a float, not a leakage current. Deciding that a number is too big is a
physics judgement, so it lives in your Python rather than in a subsystem
with a vocabulary of its own.

The script runs after every measured point, inside the sweep thread, with:

| name | what it is |
|---|---|
| `reads` | the row just measured, keyed exactly like the CSV columns |
| `row`, `columns` | that row as written, and its header |
| `point`, `values` | the axis setpoints (`{'ax1': …}` and a list) |
| `walk` | the innermost walk number, 1-based |
| `devices` | the axis adapters, by address |
| `engine`, `live` | the running engine and its live program |
| `stop()`, `pause()`, `to_zero()` | end, hold, or park and end |
| `np`, `time` | numpy and the stdlib module |

Stop the run when the leakage passes 2 nA:

```python
if abs(reads["GPIB0::4::INSTR.A_current"]) > 2e-9:
    stop()
```

Or end just this walk and let the sweep carry on — the "creep up until it
misbehaves, then stop creeping" move, useful in a 2-D map where each row
should find its own boundary:

```python
if abs(reads["GPIB0::4::INSTR.A_current"]) > 2e-9:
    live.update_axis(0, stop=values[0])      # retarget axis 1 to here
```

The tripping point stays in the data, because the row is written before
the script runs — on a gate ramp that boundary is usually the result you
were after.

**Load script…** and **Save script…** sit under the editor; scripts live in
`<core>/<YYMMDD>/scripts`. Loading does *not* push into a running sweep —
press an axis card's **Apply** for that, the same as for any other live
edit.

`allow_script` defaults to **true**, because installing a profile must not
silently disable something the application already did. Set it false to
lock a rig down for unattended operation; a program carrying a script is
then refused at pre-flight, and a live Apply will not push one either.

---

## Pre-flight

Before any instrument is touched, `validate_program` checks the whole
`SweepProgram` against the profile: endpoints and manual step tables
inside their ranges, rates below their ceilings, read channels that exist,
the interlock ceilings, and `allow_script`.

Anything at level `error` refuses the sweep with a message naming the
reason — "Vbg stop of 40 V is outside the allowed range [-8, 8] V" —
rather than faulting two hours in. Warnings are reported and the sweep
proceeds.

---

## Autonomy tiers

`autonomy` is a coarse switch over the whole rig:

* **`readonly`** — no parameter may be set at all. Reading, monitoring and
  analysis still work. Useful while a new profile is being trusted.
* **`bounded`** — the default. Everything inside the declared envelope is
  permitted.
* **`full`** — limits still apply where declared, but the tier stops
  standing in the way of anything else.

---

## Reloading

Settings → **Lab profile** → *Reload lab profile*, or
`App.reload_profile()`, re-reads the file and pushes the new policy onto
the registry, which forwards it to the instruments **already connected** —
a reload must never leave a live adapter running under the previous
limits.

`LabProfile.validate(registry)` cross-checks against the live registry:
unassigned addresses, parameter names absent from a driver's option lists,
duplicate aliases, contradictory bounds.

`LabProfile.describe()` renders the whole thing as compact plain text —
the file's contents in the lab's own language, and the same object the
safety layer enforces, so the description and the protection cannot drift
apart.
