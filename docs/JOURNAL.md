# Provenance and the lab journal

A CSV of numbers is not a measurement. Six months on the columns say
`GPIB0::1::INSTR.x` and nothing says what the lock-in time constant was,
which gate range was safe, or which software revision took the data. That
context exists only while the sweep is running.

Unisweep writes it down, in two places, automatically.

**Nothing is typed by the operator.** There is no "intent" box and no
"campaign" box, because a box asking *why are you running this?* is a box
that gets left empty at 2 a.m., and a journal with half its entries blank
is worse than one with none. The record carries everything the sweep
already knows about itself. Intent and grouping are *read back out* of it
later — by a person, or by an assistant asked in the morning what
happened overnight.

---

## The sidecar, beside every data file

`250908-1.csv` gets `250908-1.json`:

```jsonc
{
  "run_id": "260908-134026-f5d0",
  "file": "250908-1.csv",
  "columns": ["time", "GPIB0::4::INSTR.A_source_voltage_sweep", "…"],
  "outer_axis_values": [1.5],          // which slice of a 2-D/3-D sweep
  "rows": 412,
  "file_opened_at": "…", "file_closed_at": "…",
  "program":     { /* the entire SweepProgram: axes, reads, condition,
                      per-point script, filename, output options */ },
  "instruments": { /* per address: driver, IDN, loggable settings */ },
  "lab_profile": { /* aliases, units, limits, constants, sample */ },
  "environment": { "git": "2c31e24+dirty", "python": "…", "host": "…" }
}
```

**`instruments`** carries each device's `IDN` string and every parameter
its driver lists as `loggable` — the convention `sr830.py` already used
for "settings worth writing in the notebook": time constant, sensitivity,
reference frequency. A getter that will not answer is recorded as an error
against its name rather than dropped, because *the instrument would not
answer* is itself worth knowing.

**`lab_profile`** is a snapshot, not a reference. The sidecar has to stand
on its own years later, when `config/lab_profile.json` has moved on.

Two deliberate choices:

- **Instruments are read once per sweep, not once per file.** A 2-D map
  opens a file per row; polling every loggable at each rotation would add
  hundreds of round trips to the measurement. The snapshot is taken at the
  start and copied into each sidecar — copying JSON, not instrument
  traffic.
- **The sidecar is written when the file opens**, and stamped with the row
  count when it closes. The run whose provenance you most want is the one
  that died overnight, so the record cannot wait for a clean finish.

Nothing here can fail a measurement: every step is wrapped, and a writer
built without provenance behaves exactly as it did before.

## The journal

`journal/YYMMDD.md` — append-only Markdown, one entry per run and per
note, in the order things happened. This is the notebook: nothing ever
rewrites a line.

```markdown
# Lab journal — Wednesday 09 September 2026

## 13:40 · 2-D run `260909-134026-f5d0` started

- file: `landau_fan`
- **master** — `GPIB0::4::INSTR.A_source_voltage` -8 → 8 · 0.5/s, 0.3 s/point
- **slave** — `IP:5000.field` 0 → 1 · step 0.05, 0.1 s/point, 2 walks, snake
- reads: `GPIB0::1::INSTR.x`, `GPIB0::2::INSTR.x`
- output: maps: grid, interpolated, images
- instruments:
  - `GPIB0::1::INSTR` — sr830 (Rxx) — Stanford_Research_Systems,SR830,…
    - time_constant: 300 ms
    - sensitivity: 1 mV
    - frequency: 17.777
- sample: id GR-1
- lab: 2D materials, level 3
- software: 2c31e24

**Per-point script**

```python
if abs(reads["GPIB0::4::INSTR.A_current"]) > 2e-9:
    live.update_axis(0, stop=values[0])
```

### 14:02 · note · assistant · run 260909-134026-f5d0

Leakage crossed 2 nA at +3.9 V; the script pulled the range in there.

## 14:03 · run `260909-134026-f5d0` finished — 78 points, 1 file(s)

- in `C:\Unisweep 2\core\260909`
- `260909-1.csv`
```

Every axis appears with its device, parameter, limits, rate or step,
per-point delay, return rate, walk count and snake flag; manual step
tables are named and counted. Then the channels read, the output options,
each instrument and its logged settings, the sample and the software
revision — and the condition and the per-point script verbatim.

That is deliberately more than a person would write. Writing it costs
nothing because the program already holds it, and it is exactly what makes
the next paragraph possible.

## Working out what it meant

`journal/journal.sqlite` indexes the same records, so *what did I measure
on the 3rd*, *every run that swept the gate* and *which run did this one
come from* are queries rather than a grep.

Nobody labels a run, so grouping is inferred: runs on the same channels,
on the same sample, close together in time are one investigation. An
assistant asked "what did we establish about this sample?" reads the
journal and works that out — which is the kind of judgement it is good at,
and the kind of typing a physicist at 2 a.m. is not.

Runs can also link explicitly through `derived_from` when something knows
the link — an analysis run naming the sweep it came from. That is what
lets a later reader see what has already been established.

A journal that cannot be written is reported, never raised. It is built on
the measurement thread, and a full disk must not cost you a sweep. A
journal written by older code keeps its rows and gains the new columns.

## From an assistant

| tool | what it does |
|---|---|
| `journal_runs` | what has been measured, newest first: what each axis swept, what was read, points, files (`full` for whole records, `since` for a date) |
| `journal_run` | one run in full — program, instruments, files, notes |
| `journal_note` | write a line — what you concluded, not what you did |
| `file_provenance` | read the sidecar beside a data file |

`describe_rig` includes a digest of the five most recent runs, so an
assistant opening a session sees what already exists before proposing to
measure it again.

Runs record themselves. `journal_note` is for the thinking — and it is
optional; nothing in the record depends on anyone writing one.
