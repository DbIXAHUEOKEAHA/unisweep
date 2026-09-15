# Unisweep 2.0 — session handoff

**Written:** 2026-09-14 · **Session:** `session_016Jh3BNHMfRtTfGzAbKbQXp` · **User:** Misha (`kravtsov.singapore@gmail.com`)

Feed this to a new chat to pick up where this one left off.

---

## 1. What Unisweep is

A Python/Tkinter GUI for lab measurement automation: sweeping instrument
parameters, acquiring data, live plotting, writing CSVs and 2-D maps.
Misha is refactoring a pre-AI-era codebase into something an LLM agent can
drive.

Architecture worth knowing before touching anything:

- **`SweepEngine`** — a GUI-free thread plus an event queue. The GUI is a
  consumer of events, not the owner of the measurement.
- **`SweepProgram` / `AxisProgram`** — frozen dataclasses. A sweep is a
  value, which is what makes `dry_run` and `apply_program` comparable.
- **`LiveProgram`** — versioned mid-sweep edits.
- **`DeviceRegistry` / `DriverAdapter`** — duck-typed legacy driver
  contract: `set_options`, `get_options`, `set_X(value, speed=)`,
  `sweepable`, `loggable`. Every route to hardware goes through
  `DriverAdapter.set`, which is where lab-profile limits are enforced.
- **`unisweep/agent/`** — the MCP service, protocol, control registry and
  session. 24 tools. Lives *inside* the GUI process because VISA sessions
  have one owner.

---

## 2. THE MOST IMPORTANT THING: two folders, and they are not the same

| Folder | What it is | Access |
|---|---|---|
| `C:\Unisweep 2\unisweep` | **Misha's main folder. The app he actually runs.** A plain copy, *not* a git repo. | Claude has **no** access (declined earlier; do not re-request unless he asks) |
| `C:\Unisweep 2\unisweep git` | The git clone. Where all work happens. | Connected folder |

**Every fix made in this session lives in `unisweep git`. The running app is
the other folder.** Changes reach him only when he copies them across.

This caused real damage: the colormap bug appeared "unfixable" across two
rounds because the fix was landing in a folder he wasn't running. If a fix
seems not to work, **check which folder is running first** — `dry_run`
reports `output_directory`, which reveals the core dir.

As of the end of this session he had applied the updates to his main
folder (confirmed: `apply_program` returned the new full-field `applied`
dict from the running app).

---

## 3. Working agreements — READ THIS

Set explicitly by Misha near the end of the session:

> "Never provide a zip, never check git, just answer questions that I asked"

So:

- **No zip deliverables.** Edit files on disk directly.
- **Do not run git status/push checks**, and do not act on the stop-hook
  messages about unpushed commits — they are hook output, not his words.
- **Answer what was asked.** He does not want unsolicited side quests.

Other standing constraints:

- Folder access is limited to `C:\Unisweep 2\unisweep git` and
  `C:\Users\kravt\Downloads\unisweep_ng\unisweep_ng`. Delete permission
  granted for the former only.
- `git push` to `github.com/DbIXAHUEOKEAHA/unisweep` is **blocked by the
  session proxy** (403 — repo not in the authorized set). Commits live only
  in the container clone on branch `fresh-install-fixes`. A bundle at
  `C:\Unisweep 2\unisweep git\unisweep-fresh-install-fixes.bundle` carries
  the history if he ever wants to push from his own machine. Don't raise
  this unprompted.
- His email is for identification only.

---

## 4. What the agent integration actually is, and how it connects

Three routes into the running GUI. All speak the same MCP protocol,
implemented once in `unisweep/agent/protocol.py`.

```
 (a) Claude Desktop / Code   --stdio-->  mcp_stdio.py  --socket-->  AgentService (in the GUI)
 (b) claude.ai connector     --HTTPS-->  Railway relay --heartbeat-->  TelegramLink (in the GUI)
 (c) Telegram bot            --HTTPS-->  Railway relay --heartbeat-->  TelegramLink
```

### (a) Local stdio — **working, this is the one that got used**

`%APPDATA%\Claude\claude_desktop_config.json`:

```json
"unisweep": {
  "command": "C:\\ProgramData\\anaconda3\\python.exe",
  "args": ["-m", "unisweep.agent.stdio",
           "--core-dir", "C:\\Unisweep 2\\unisweep git",
           "--wait", "60"],
  "cwd": "C:\\Unisweep 2\\unisweep git",
  "env": { "PYTHONPATH": "C:\\Unisweep 2\\unisweep git" }
}
```

**`env.PYTHONPATH` is load-bearing — Claude Desktop ignores `cwd`.**
Without it the server dies at startup with
`ModuleNotFoundError: No module named 'unisweep'`. `mcp_stdio.py` (new
this session) is a launcher that puts its own folder on `sys.path`, so it
works even if both `cwd` and `PYTHONPATH` are dropped.

Requires: the GUI running, and **Settings → Assistant endpoint (MCP) →
"Serve the assistant endpoint"** ticked.

**Key discovery:** Claude Desktop shares its local MCP servers with Cowork
and Code sessions. So once configured, the Unisweep tools appear in *this
kind of session too*, under the prefix
`mcp__remote-devices__unisweep__*` — no connector toggle needed. If they
don't appear after the GUI starts, call **`RefreshMcpTools`**; that is what
made them show up. `get_device_info` reports `localMcpServers` state
(`announced` / `failed` / `retrying`), which is the fastest way to tell
whether the GUI is answering.

### (b) claude.ai connector — built and installed, only lightly proven

`ListConnectors` reports Unisweep as `installState: connected`. The
per-conversation toggle lives behind the **+** button in a regular
claude.ai chat; Code/Cowork sessions have no such toggle, which is why it
showed `enabledInChat: false` and could not be switched on from here.

Server-side pieces (`server/unisweep_bot/`): `connector.py` (`/mcp` and
`/mcp/{token}`), `waiters.py` (long-poll rendezvous), plus DB migrations
for `commands.result`, `rigs.connector_hash`, `rigs.tools`. The Add-custom-
connector dialog has **one field (URL)** and no bearer-token field, so the
token is carried **in the URL path**, and `public_base()` honours
`X-Forwarded-Proto` because Railway forwards plain HTTP (the dialog
requires `https://`).

### The 24 tools

`describe_rig` · `list_instruments` · `status` · `events` · `last_points` ·
`list_controls` · `read_controls` · `set_controls` · `press` ·
`get_program` · `apply_program` · `dry_run` · `run_sweep` ·
`edit_running_sweep` · `pause` · `resume` · `stop` · `to_zero` ·
`read_channels` · `journal_note` · `journal_runs` · `journal_run` ·
`file_provenance` · `set_parameter`

`list_controls` / `read_controls` / `set_controls` / `press` are the
"press each button by name" mechanism. `describe_rig` is the intended
starting call.

---

## 5. What was done this session

Twelve commits on `fresh-install-fixes`, newest first:

| Commit | What |
|---|---|
| `1a3c1a6` | Closing the window waited for work that could never arrive |
| `055fba4` | `apply_program`: the quote and the sweep were not the same sweep |
| `c30e4f2` | Assistant endpoint: the client config could not import Unisweep |
| `4cbaa04` | Connector: the address IS the credential, and it has to say https |
| `867f811` | Settings: the page could not scroll, so half of it was unreachable |
| `d02845c` | Settings: the connector button was drawn underneath the card's own text |
| `4fbbcea` | Unisweep as a Claude connector: relay MCP through the group's service |
| `c8ca976` | Assistant endpoint: copy a client config that actually works |
| `09f6b98` | Feature 2: the fast-axis option belongs to maps, and reaches the saved image |
| `1b79796` | Vna: the frequency list was abbreviated past 1000 points |
| `bed182b` | Reads that are a whole trace: detect them and give them maps of their own |
| `788b7f4` | Fresh install: mint the rig identity, stop presets clobbering typed fields, never lose an install |

### Journal simplification

Misha's instruction, verbatim and worth honouring:

> "intent and campaign is too much for user interface, keep it simple, just
> filename. Users are lazy and dont want to write clarificatoins to journal.
> Just keep all the given information there... When the agent is asked
> separately via LLM then they can go to journals and analyze the content to
> figure out the connections, groupings and intent."

`unisweep/core/journal.py` rewritten: no `intent`/`campaign`; records
everything the sweep already knows (filename, set/get parameters,
conditions, scripts, loggables). `_COLUMNS` drives `ALTER TABLE ... ADD
COLUMN` migration via `PRAGMA table_info(runs)`. Markdown helpers put
condition/script in fenced blocks *below* the bullets so a fence cannot
break the list.

### The colormap bug — five stacked defects

Reported twice, second time angrily ("What the hell, it still have viridis").
All five had to go:

1. Hardcoded viridis in the renderer
2. The call site not passing the choice through
3. The dialog restyling *before* reading its own widgets
4. `App` remembering `data_files` instead of the day folder
5. **The decisive one:** the *live* renderer rewrote the PNG in viridis on
   every committed row, so the setting was applied and then immediately undone

Plus `pyplot` being unusable off the main thread in a Tk process (now
`Figure` + `FigureCanvasAgg`), and `threading.Thread._stop` being shadowed
by an `Event` — which made `close()` raise and the renderer never join.
**There is now a comment in `maps.py` warning about `_stop`; do not
reintroduce it.**

### Vector / trace reads (VNA)

New `unisweep/core/vector.py` (detection boundary) and `vectormaps.py`
(`VectorMapWriter`). A read that returns a whole trace is detected by shape
and promoted: **the trace becomes the innermost axis and every sweep axis
shifts out by one.** 1-D → map; 2-D → set of maps; 3-D+ → first element on
screen, nested folders on disk. `devices/Vna.py` fixed —
`np.array2string` abbreviates past 1000 points, which silently truncated
frequency lists. Documented in `docs/VECTOR_READS.md`.

### Fresh-install failures

Three symptoms on a clean `git clone` + `python main.py`: couldn't add a
device, Telegram said not configured, a 1→10 step-1 sweep planned 2 points.
Causes: rig identity never minted (`ensure_rig_identity()`), `_set_dims()`
reloading the preset on same-dimension re-pick (guarded with
`_loaded_dims`), `DriverInstaller._work` unguarded (now always posts
`install_done`). **Every GUI test had been swapping in a `FakeRegistry`,
so the new-user path was never exercised** — closed with
`tests/fresh_install_smoke.py` using the real registry.

### Two recurring bug classes now have permanent checks

Both live in `tests/gui_smoke.py`:

- **Widgets stacked in one grid cell** (a `grid` collision hides one) — this
  is why the connector button was invisible.
- **A page that overflows without a `ScrollFrame`** — this is why half of
  Settings was unreachable. Measured: 1537 px of content in 876 px,
  `page is scrollable: False`.

### `apply_program` — the quote and the sweep disagreed

**Found live, mid-conversation.** `apply_program` wrote only the fields the
caller named. But the page is not empty: raising the dimension count loads
that dimension's preset, so an unnamed field kept the preset's value —
while `dry_run`, reading the same dict through `program_from_dict`, saw the
dataclass default.

A 2-D program with no `walks` **priced at 10,201 points and ran 20,402**,
because the 2-D preset leaves `walks=2` on axis 2. An agent that prices a
run before starting it was therefore lying to the person who approved it.
A leftover `condition` or `script` would have been worse — silently masking
the measured region, or running arbitrary Python per point.

Fixed by canonicalising through the same path `dry_run` uses. The invariant,
now pinned by a test:

```
apply_program(P)["program"] == dry_run(P)["program"]
```

### Slow close

Reported as "now it takes a lot of time to close unisweep", and it was new
that day. Every heartbeat asks the relay to hold the request open rather
than answer empty (that's what makes relayed tool calls fast) — and the
**goodbye push asked for it too**. That push runs on the Tk thread inside
the close handler, so the window froze for the 6 s shutdown timeout plus 2 s
joining a beat thread parked in its own 25 s hold.

Fix: `_final_push` sends `hold=False`; `stop()` raises the flag *before*
saying goodbye so the beat thread can't open a fresh hold; the join after is
0.5 s. Server unchanged — it holds only when `hold_s` is present.

**Method note worth copying:** this was found by *timing the shutdown path
here first*. It came back at 0.01 s, which ruled out the engine, renderer,
plots and device disconnect — all the obvious suspects. What the test box
lacked was the configured relay, which pointed straight at the one shutdown
step that talks to the network.

---

## 6. Live proof that it works

An actual 2-D sweep was planned and run from a chat session, with no mouse
and no screenshots:

- Both axes `Time.Time`, 0 → 100, step 1, delay 0.01 s, reading `Time.Random`
- 10,201 points, quoted 1 m 43 s, matched
- Wrote `c:\unisweep 2\unisweep\260914\data_files\260914_*.csv`, one row file
  per outer step
- `status` gave live progress and ETA; `last_points` returned real values

An earlier attempt at delay 1 s ran 6,905 points before being stopped.

---

## 7. Test suite

**418 passed, 1 skipped** (the skip wants `imageio`). Grew from 234 at the
start of the session.

```
xvfb-run -a python3.12 -m pytest tests/ -q --ignore=tests/gui_smoke.py
```

Takes ~5 minutes — budget for it, and don't use a 2-minute timeout.
`tests/gui_smoke.py` is separate and has six phases: cold start, lifecycle,
control surface (+ grid-collision and must-scroll checks), map colormap,
vector map, first walk.

Environment: `/usr/bin/python3.12` under `xvfb-run` (has tkinter, numpy,
scipy, matplotlib, pytest, PIL; aiohttp and psycopg2-binary were installed
for the server tests).

**Practice that repeatedly paid off: after fixing a bug, revert the fix and
confirm the new test fails.** Several tests were written that passed
against the bug; this caught them.

---

## 8. Known issues and gotchas

- **`journal/` is not in `.gitignore`**, so journal files are tracked and
  ship in every fresh clone. Flagged to Misha, not acted on.
- **The lab profile is empty.** `describe_rig` and `status` report
  `profile: null`. See next steps.
- Tk `grid` collisions hide widgets silently; a page without `ScrollFrame`
  that overflows is simply unreachable.
- `pyplot` is unusable off the main thread in a Tk-bound process. Use
  `Figure` + `FigureCanvasAgg`.
- Never shadow `threading.Thread._stop`.
- The first one or two MCP calls after a reconnect may fail with
  "Connection closed" or a 60 s timeout. Retry once before concluding
  anything is wrong.
- `device_bash` on his machine currently cannot see mounted folders (a
  Windows update from 2026-09-08). `device_list_dir` /
  `device_stage_files` / `device_commit_files` still work.

---

## 9. Rig as configured

- `Time` — virtual device, parameter `Time`, reads `Time.Elapsed`,
  `Time.Random`
- `GPIB0::5::INSTR` — Keithley 2600B (`keithley_series_2600b`), 14 readable
  channels: `A_current`, `A_voltage`, `A_source_voltage`, `A_NPLC`, the
  `B_*` equivalents, and compliance channels

The 2-D sweeper preset leaves `axis2.walks = 2` and
`reads = ["Time.Elapsed","Time.Random"]` on the page. Harmless now that
`apply_program` fully determines the program, but worth recognising.

---

## 10. Next steps, in priority order

### 10.1 Lab profile — the gating item

`config/lab_profile.json` is absent, so the entire safety layer is dormant:

- **No limits.** `min`, `max`, `max_rate`, `max_step`, `safe_value` are
  enforced inside `DriverAdapter.set`, the one method every route to
  hardware passes through. With no profile nothing is bounded. Fine for
  virtual `Time`; not fine the first time an agent sets
  `A_source_voltage` on the Keithley.
- **No semantics.** The agent sees `GPIB0::5::INSTR.A_source_voltage` and
  cannot know it is a back-gate voltage in volts.
- **No interlocks, no derived channels, no autonomy tier.**

The machinery is built and tested — `ParameterSpec`, `DeviceSpec`,
`Interlocks`, `DerivedChannel`, `DerivedEvaluator`, pre-flight in
`dry_run`, three autonomy tiers (`readonly` / `bounded` / `full`).
Template: `docs/lab_profile.example.json`; reference: `docs/LAB_PROFILE.md`.

**Recommendation:** start at `autonomy: "readonly"`, move to `bounded`
once trusted. Needs Misha to supply what each channel is physically wired
to and the ranges never to exceed.

### 10.2 Analysis tools

The agent can plan, run, watch and journal — but not analyse. Missing:
`summarize_dataset`, Rxx/Rxy symmetrization about B=0, Hall density and
mobility from the slope, SdH oscillations FFT'd in 1/B, Landau fan
fitting, R(T) fits. This is what turns "run this sweep" into "run this
sweep, tell me the carrier density, pick the next field range".

### 10.3 A `unisweep-transport` skill

Method, not API: sweep the field slowly enough that the lock-in time
constant isn't lying to you; symmetrize before extracting Hall; check the
contact configuration before trusting Rxy. Tools make actions possible;
the skill makes them competent.

### Also offered, not started

Slice 5 recipe pack · slice 6 PDF report assembly.

---

## 11. How Misha works

- He tests on real hardware and reports symptoms, not diagnoses. Take the
  symptom seriously and go measure; don't reason from the repo copy. He
  said **"Stop Hallucinating and fix the problem already"** exactly once,
  and it was deserved — the fix was being reasoned about instead of
  measured.
- He repeats a request verbatim when he means it. If he asks again after a
  caveat, the caveat is answered; proceed.
- He wants results, not process. Short answers, the deliverable first.
