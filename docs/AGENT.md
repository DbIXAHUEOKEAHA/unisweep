# Driving Unisweep from an assistant

An assistant works Unisweep the way you do: it reads the fields, types
into them, ticks the boxes and presses the buttons — in *your* window,
while you watch. There is no second copy of the experiment. Whatever it
set is on screen, and you can take the mouse back mid-thought.

This document is the operator's half. `docs/LAB_PROFILE.md` is the safety
half, and you want that one first: without a lab profile, nothing bounds
what an assistant may do to an instrument.

---

## Turning it on

Settings → **Assistant endpoint (MCP)** → tick it. Port 0 lets the OS pick
one. Unisweep writes `config/agent_endpoint.json` with the host, port and
a token, and the *Copy client command* button gives you the line to paste
into your MCP client:

```json
{
  "mcpServers": {
    "unisweep": {
      "command": "C:\\path\\to\\python.exe",
      "args": ["-m", "unisweep.agent.stdio",
               "--core-dir", "C:\\Unisweep 2\\unisweep git"]
    }
  }
}
```

The endpoint listens on loopback only and requires the token. It lives
**inside the running application**, because that process owns the VISA
sessions — a second process would fight it for the instruments. The
`stdio` module your client launches is a dumb pipe: it speaks no protocol
of its own, it just carries bytes to the window.

If Unisweep is not running, the pipe says so and exits rather than
pretending. `--wait 60` makes it keep retrying while the app starts.

---

## What the assistant sees

### The rig

`describe_rig` is the briefing: the lab profile rendered in your own
language, the sample, the constants, the derived channels, every readable
channel, and what the engine is doing right now. With no lab profile it says so — and then no limits are being
enforced, which the assistant is told to raise with you before touching
anything.

### The window

`list_controls` returns every knob in Unisweep as a named handle:

```
app.page                     sweep.dimensions          sweep.axis1.device
sweep.start                  sweep.axis1.start         sweep.axis1.parameter
sweep.stop                   sweep.axis1.stop          sweep.axis1.walks
sweep.to_zero                sweep.axis1.rate          sweep.axis1.snake
sweep.condition              sweep.axis1.delay         sweep.axis1.apply
sweep.script                 sweep.reads               sweep.filename
setget.row1.value            setget.delay              setget.start
settings.map_style           settings.theme            settings.agent_enabled
devices.GPIB0__4__INSTR.type devices.scan              devices.…​.test
```

Each carries its kind — `number`, `text`, `choice`, `multichoice`, `flag`,
`action` (a button), `readout` (display only) — its current value, its
allowed options, and whether it is greyed out at this moment.

The set is **dynamic on purpose**: axis 2 exists only when the sweep is
2-D, and device rows appear as addresses are found. What an assistant can
reach is exactly what you can see, no more and no less.

Names are stable and read like where you would point on screen. A device
picker accepts the bare address (`GPIB0::4::INSTR`) as well as the
displayed `ADDRESS — Driver` form, because the bare address is what
programs and the lab profile use everywhere else.

---

## What it can do

`set_controls` types into fields, as one edit — if any name or value is
wrong, **nothing** is applied and the error says which. That only fills
the form in; nothing reaches an instrument until something is pressed.

`press` runs exactly the command a click runs.

`apply_program` fills the whole sweep page in from a program: dimensions
first, then each axis card, then reads, condition, filename and the
per-point script. It returns the program the page then builds, so the
assistant can check that what it meant is what landed.

`dry_run` prices the sweep without touching an instrument — planned
points, estimated duration, where the files go, and every problem the lab
profile finds. `run_sweep` fills in, pre-flights and presses Start.

To make a **measured** value decide something, the assistant writes a
per-point script, the same box a person uses. Unisweep has no opinion
about what a channel means — `GPIB0::4::INSTR.A_current` is a float, not a
leakage current — so that judgement is Python, not a subsystem:

```python
if abs(reads["GPIB0::4::INSTR.A_current"]) > 2e-9:
    stop()                                # or: live.update_axis(0, stop=values[0])
```

`reads` is the row just measured, keyed like the CSV columns. See
`docs/LAB_PROFILE.md` for the full namespace. The profile can forbid
scripts (`interlocks.allow_script`), and `dry_run` says so before you
try. `sweep.load_script` / `sweep.save_script` take a path in `files=[…]`.

`edit_running_sweep` retunes an axis mid-run and presses its Apply, so the
change takes effect on the next point. That is the adaptive path: watch
`status`, decide, retune — the same live-edit machinery the GUI uses.

`read_channels` and `set_parameter` reach instruments directly, through
the same limit policy the engine uses.

Every run records itself: a JSON sidecar beside each data file and an
entry in the lab journal, carrying the whole program, the instruments and
their logged settings, and the software revision. Nothing is typed by the
operator — there is no intent field and no campaign field — so read the
grouping out of the record instead: `journal_runs` says what each run
swept and read and when, `journal_run` gives one in full, and
`file_provenance` reads the sidecar beside a file. `journal_note` is
where your own conclusions go. See `docs/JOURNAL.md`.

---

## Dialogs are answers, not obstacles

Unisweep asks real questions at real moments: *these axes are not at their
start value — go to start, start from here, or cancel?*; *ramp all sweep
devices to zero and stop?*; *fix the highlighted fields first*.

A person reads them and clicks. An assistant pressing the same button
would hang the whole window inside a modal nobody can see. So during an
agent press the dialog functions are swapped for scripted ones that:

* **record every dialog**, and hand the transcript back with the result.
  This is usually where the real answer is — "Start warning: GPIB4.Volt is
  at 2.5, sweep starts at 0" tells the assistant something it could not
  otherwise know;
* **answer questions from a script** passed with the call;
* **refuse rather than guess.** An unanswered question aborts the press
  with `needs_answer` saying what was asked. Quietly picking a default
  would mean pressing Start and silently cancelling — or worse, silently
  not cancelling.

Purely informational dialogs never need an answer: they are recorded and
dismissed, so a validation complaint arrives as data.

```
press("sweep.start")
  → ok: false, needs_answer: "Start warning … Go to start?"
press("sweep.start", answers=["yes"])
  → ok: true, dialogs: [ … answer: true ]
```

---

## Watching a run without drowning in it

A Landau fan is a hundred thousand rows. An assistant that reads them one
by one has spent its context before it has learned anything.

So the engine's events are tapped into a bounded ring with a rolling
summary. `status` is a fixed size no matter how long the sweep runs:
state, progress, ETA, the file being written, recent errors, and the last
few points. `events` pages through the stream by
sequence number, and admits what it dropped. For real data, the assistant
reads the CSV — `status` reports its path.

---

## The safety model, end to end

Four layers, and an assistant passes through all of them:

1. **The lab profile** bounds every `set`, inside `DriverAdapter.set`.
   Every route to the hardware goes through that one method, so there is
   no path an assistant can take that a person could not, and none that
   skips the check.
2. **Pre-flight** (`dry_run`, and again inside the engine) refuses a
   program whose endpoints, rates or interlocks are out of bounds, with a
   reason instead of a stack trace.
3. **The per-point script** reacts to what was just measured — the
   leakage check that ends a gate ramp at its onset rather than at the
   number someone typed. It is ordinary Python, and the profile can turn
   it off entirely for an unattended rig.
4. **The window.** You are looking at it. Stop always wins, and the
   assistant's Stop is your Stop.

The autonomy tier in the profile is the coarse switch: `readonly` lets an
assistant look, plan and analyse but set nothing at all — a good way to
spend a first session with a new profile.

---

## Design notes

**The GUI is the source of truth.** The session does not build a private
program and hand it to the engine; it fills in the same fields and presses
the same button. So there is no second model of the experiment that can
drift out of step with the first, and a human can take over at any point.

**Widget work is marshalled; instrument work is not.** Tk is
single-threaded, so every control read and write is scheduled onto the
main loop and waited on. Instrument traffic is deliberately *not*: reading
a lock-in takes tens of milliseconds and opening a dead instrument can
take thirty seconds, and doing that inside the UI loop would freeze the
window.

**No dependencies.** The MCP protocol is spoken directly over
newline-delimited JSON-RPC, for the same reason `notify.py` talks to
Telegram with `urllib`: this runs in whatever Python a lab machine has,
next to pyvisa and a vendor DLL.

**Testing, in three layers.** They catch different things, and the middle
one exists because the other two could not.

1. **Logic, no display.** `tests/test_agent.py` and `tests/test_mcp.py`
   cover the control layer, dialogs, the event tap, the session and the
   wire protocol against duck-typed widgets and a real socket. Runs
   anywhere.
2. **Binding, against real Tk.** `tests/test_controls_tk.py` drives each
   binder against an actual `ttk` widget. This layer was added after a
   bug that layer 1 *could not* find: `ttk.Button.invoke()` does not
   propagate an exception raised inside the command — tkinter catches it,
   hands it to the root's `report_callback_exception`, and returns
   normally. Every press therefore reported success, including presses
   that failed and presses that asked a question nobody answered. A fake
   button calls its command directly and raises, so the fakes were all
   green. Skipped automatically without tkinter or a display.
3. **The whole window.** `control_surface_check()` in
   `tests/gui_smoke.py` builds the real application and reads *every*
   control on it, fills the sweep page in, presses buttons through their
   real dialogs, and runs a short sweep end to end.

```
xvfb-run -a python -m pytest tests/ -q        # layers 1 and 2, Linux
xvfb-run -a python tests/gui_smoke.py         # layer 3, Linux
python -m pytest tests\ -q                    # layers 1 and 2, Windows
python tests\gui_smoke.py                     # layer 3, Windows
```

On a headless Linux box, `apt-get install python3-tk xvfb` is all layers
2 and 3 need.
