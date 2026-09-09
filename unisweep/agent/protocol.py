"""MCP over JSON-RPC, dispatching to an :class:`AgentSession`.

Written against the wire protocol directly rather than against an SDK, for
the same reason :mod:`unisweep.core.notify` speaks to Telegram with
``urllib``: this has to run inside whatever Python a lab machine happens to
have, next to pyvisa and a vendor DLL, and "pip install a dependency tree"
is a bad thing to require of an instrument controller.

The transport is newline-delimited JSON-RPC 2.0. :mod:`service` runs this
over a loopback socket inside the GUI process, and :mod:`stdio` is the
pipe that a desktop MCP client launches.

The tool descriptions below are load-bearing. They are the only
instructions the assistant gets about how this rig is driven, so they say
what a tool does *and* what to do when it says no.
"""

from __future__ import annotations

import json
import traceback
from typing import Any, Callable, Optional

__all__ = ["MCPHandler", "TOOLS", "PROTOCOL_VERSION", "SERVER_INFO"]

PROTOCOL_VERSION = "2025-06-18"
SUPPORTED_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")
SERVER_INFO = {"name": "unisweep", "title": "Unisweep",
               "version": "2.0"}

_OBJ = {"type": "object"}
_STR = {"type": "string"}
_NUM = {"type": "number"}
_INT = {"type": "integer"}
_BOOL = {"type": "boolean"}
_STRS = {"type": "array", "items": _STR}


def _tool(name, method, description, properties=None, required=(),
          destructive=False, read_only=False):
    return {
        "name": name,
        "method": method,
        "description": description.strip(),
        "inputSchema": {"type": "object",
                        "properties": dict(properties or {}),
                        "required": list(required)},
        "annotations": {"readOnlyHint": bool(read_only),
                        "destructiveHint": bool(destructive)},
    }


PROGRAM_SCHEMA = {
    "type": "object",
    "description": (
        "A sweep program. axes: 1-3 objects with device (address or a lab "
        "profile alias), parameter, start, stop, rate, delay, count_mode "
        "('ratio' = rate in units/s, 'step' = units per point), and "
        "optionally walks, snake, force_stepwise, back_rate, back_delay. "
        "reads: channels as 'address.option'. condition: region masking / "
        "axis coupling on the SETPOINTS. script: Python run after every "
        "measured point — the place where a measured value decides "
        "something. Also filename."),
    "properties": {
        "axes": {"type": "array", "items": _OBJ},
        "reads": _STRS,
        "condition": _STR,
        "filename": _STR,
        "script": _STR,
    },
}

TOOLS = [
    # ---- knowing where you are ---------------------------------------
    _tool("describe_rig", "describe_rig", read_only=True, description="""
Start here. Returns what this rig is: the lab profile (every instrument,
what each parameter means physically, its units and its safe range),
the sample, named constants, derived channels, the readable channels, and
what the sweep engine is doing now.

If it reports has_profile=false, nothing is described and no limits are
enforced — say so before touching anything, and ask for
config/lab_profile.json to be filled in (docs/LAB_PROFILE.md).
"""),
    _tool("list_instruments", "list_instruments", read_only=True,
          description="""
Every configured address, its driver, whether it is connected, and its
settable/readable parameters with whatever the lab profile says they mean.
Never opens an instrument.
"""),
    _tool("status", "status", read_only=True, properties={
        "points": dict(_INT, description="How many recent points to "
                                         "include (default 3).")},
          description="""
What the sweep engine is doing: state, progress, ETA, the file being
written, recent errors, and the last few measured points.
Fixed size however long the sweep is — poll this, do not read every point.
"""),
    _tool("events", "events", read_only=True, properties={
        "since": dict(_INT, description="Return events numbered above "
                                        "this. Start at 0."),
        "limit": dict(_INT, description="Maximum events (default 200)."),
        "kinds": dict(_STRS, description="Filter by event name, e.g. "
                                         "['SweepError','WalkFinished'].")},
          description="""
The engine's event stream, numbered so you can page forward: pass the
'latest' from the previous call back as 'since'. Use kinds to watch for
something specific rather than reading everything.
"""),
    _tool("last_points", "last_points", read_only=True, properties={
        "count": dict(_INT, description="How many points (default 20).")},
          description="""
The most recent measured rows with their column names. For anything more
than a glance, read the CSV the sweep is writing instead — status reports
its path.
"""),

    # ---- the GUI, as a person uses it ---------------------------------
    _tool("list_controls", "list_controls", read_only=True, properties={
        "page": dict(_STR, description="Restrict to one page: app, sweep, "
                                       "setget, devices, settings."),
        "prefix": dict(_STR, description="Restrict to names starting with "
                                         "this, e.g. 'sweep.axis1'."),
        "values": dict(_BOOL, description="Include current values "
                                          "(default true).")},
          description="""
Every knob in the Unisweep window, by name, with its kind, current value,
allowed options and whether it is greyed out right now. This is the whole
user interface as a list: fields you can type into (number, text), pickers
(choice, multichoice), checkboxes (flag), buttons (action) and values you
can only read (readout).

The set is dynamic: axis cards appear with the dimension count and device
rows appear as addresses are found, so list again after changing either.
"""),
    _tool("read_controls", "read_controls", read_only=True, properties={
        "names": dict(_STRS, description="Specific control names."),
        "page": dict(_STR, description="Or a whole page."),
        "prefix": dict(_STR, description="Or a name prefix.")},
          description="""
Read the current value of specific controls. Cheaper and clearer than
list_controls when you already know the names.
"""),
    _tool("set_controls", "set_controls", properties={
        "values": dict(_OBJ, description="{control name: value}. Numbers "
                                         "for number fields, true/false "
                                         "for flags, one of the options "
                                         "for a choice, a list for a "
                                         "multichoice.")},
          required=["values"], description="""
Type into fields and tick boxes, exactly as a person would. Applied as one
edit: if any name or value is wrong, nothing is applied and the error says
which. Device pickers accept the bare address as well as the displayed
'ADDRESS — Driver' form.

This only fills the form in. Nothing reaches an instrument until you press
something.
"""),
    _tool("press", "press", destructive=True, properties={
        "name": dict(_STR, description="Control name of kind 'action'."),
        "answers": {"type": "array", "description":
                    "Answers to the dialogs this press raises, in order: "
                    "'yes', 'no' or 'cancel'."},
        "files": dict(_STRS, description="Paths for any file dialogs it "
                                         "opens, in order.")},
          required=["name"], description="""
Press a button: runs exactly the command a click runs.

Unisweep asks real questions at real moments. Every dialog the press
raised comes back in 'dialogs' — that is often where the answer is (an
invalid field, a start-position warning naming the instrument). If a
question was asked that you did not answer, nothing happens: ok=false and
'needs_answer' says what was asked; re-issue with answers=[...].

A greyed-out button is refused with the reason (Stop only works while a
sweep runs).
"""),

    # ---- programs -----------------------------------------------------
    _tool("get_program", "get_program", read_only=True, description="""
The sweep the page currently describes. valid=false means fields still
need fixing, and 'complaints' is what the page would have said.
"""),
    _tool("apply_program", "apply_program", properties={
        "program": PROGRAM_SCHEMA}, required=["program"], description="""
Fill the sweep page in from a program, field by field — dimensions first,
then each axis card, then reads, condition, filename and the per-point
script. Nothing is started. Returns the program the page now builds, so you
can check that what you meant is what landed.

To make a measured value decide something — stop when a leakage current
runs away, end a walk where a resistance turns over — put it in `script`.
It runs after every point with `reads` (that row, keyed like the CSV
columns), `values`, `stop()`, `to_zero()` and `live`, e.g.

    if abs(reads["GPIB0::4::INSTR.A_current"]) > 2e-9: stop()

or, to end the current walk instead of the whole sweep,

    live.update_axis(0, stop=values[0])

The lab profile can forbid scripts (interlocks.allow_script); dry_run says
so before you try.

Manual step tables come from a file: press sweep.axisN.load_manual_steps
with files=['/path/to/steps.csv'].
"""),
    _tool("dry_run", "dry_run", read_only=True, properties={
        "program": PROGRAM_SCHEMA}, description="""
Price a sweep without touching an instrument: planned points, estimated
duration, where the files will go, and every problem the lab profile finds
— endpoints outside a safe range, rates above a ceiling, interlocks, a
per-point script the profile does not allow.

With no argument it prices what is on the page. Run this before any long
sweep: it is the difference between finding out now and finding out in
two hours.
"""),
    _tool("run_sweep", "run_sweep", destructive=True, properties={
        "program": PROGRAM_SCHEMA,
        "answers": {"type": "array", "description":
                    "Answers for dialogs Start raises. The common one is "
                    "the start-position warning: 'yes' = ramp to the start "
                    "point first, 'no' = start from where the instruments "
                    "stand, 'cancel' = do not start."},
        "check": dict(_BOOL, description="Pre-flight first (default "
                                         "true). Leave it on.")},
          description="""
Fill the page in (if a program is given) and press Start.

MOVES INSTRUMENTS. Pre-flight runs first and refuses before anything
moves, with the reason. started=false means no sweep began — read
'reason' and the dialogs.
"""),
    _tool("edit_running_sweep", "edit_running_sweep", destructive=True,
          properties={
              "axis": dict(_INT, description="Axis number, 1-based."),
              "start": _NUM, "stop": _NUM, "rate": _NUM, "delay": _NUM,
              "walks": _INT,
              "condition": _STR,
              "script": dict(_STR, description="Replaces the per-point "
                                               "script."),
          }, description="""
Retune a sweep while it runs and press that axis's Apply, so the change
takes effect on the next point. This is how a range is extended or pulled
in without stopping — the adaptive path: watch status, decide, retune.
"""),
    _tool("pause", "pause", destructive=True, description="""
Pause a running sweep. Instruments hold where they are.
"""),
    _tool("resume", "resume", destructive=True, description="""
Resume a paused sweep.
"""),
    _tool("stop", "stop", destructive=True, description="""
Stop a running sweep cleanly. Everything measured so far is kept.
"""),
    _tool("to_zero", "to_zero", destructive=True, properties={
        "confirm": dict(_BOOL, description="Must be true.")},
          description="""
Ramp every sweep axis to zero and end the run. Requires confirm=true.
This is the panic handle — prefer stop unless the instruments need to be
parked.
"""),

    # ---- instruments directly ------------------------------------------
    _tool("read_channels", "read_channels", read_only=True, properties={
        "channels": dict(_STRS, description="'address.option' strings, or "
                                            "lab profile aliases.")},
          required=["channels"], description="""
Read channels once, right now, plus any derived values the profile
defines from them. Use this to check where things stand before planning a
sweep — not as a way to take data, which is what a sweep is for.
"""),
    # ---- the lab journal -----------------------------------------------
    _tool("journal_note", "journal_note", properties={
        "text": dict(_STR, description="The note. Write what you concluded "
                                       "and why, not what you did — the "
                                       "run record already says that."),
        "run_id": dict(_STR, description="Attach it to a run."),
        "author": dict(_STR, description="Defaults to 'assistant'.")},
        required=["text"], description="""
Write a line in the lab journal: append-only Markdown under `journal/`
plus an indexed copy. Use it for what a notebook is for — what you
concluded, what looked wrong, what the next run should do differently.
Runs record themselves; you do not need to log that a sweep happened.
"""),
    _tool("journal_runs", "journal_runs", read_only=True, properties={
        "limit": dict(_INT, description="Most recent first (default 20)."),
        "since": dict(_STR, description="ISO timestamp or date prefix; "
                                        "only runs started at or after it."),
        "full": dict(_BOOL, description="Whole records instead of the "
                                        "digest — verbose.")},
        description="""
What has been measured, newest first: run id, when, what each axis swept
and between which limits, what was read, how many points, whether it was
stopped, and the files it wrote. Nobody labels runs with an intent or a
campaign, so read the grouping out of this: runs on the same channels
close together in time are one investigation. This is also how to find
out what already exists before proposing to measure it again.
"""),
    _tool("journal_run", "journal_run", read_only=True, properties={
        "run_id": _STR}, required=["run_id"], description="""
One run in full — the whole program (axes, reads, condition, per-point
script, output options), the instruments and their logged settings, the
files it wrote, and every note attached to it.
"""),
    _tool("file_provenance", "file_provenance", read_only=True, properties={
        "path": dict(_STR, description="Path to a data file (.csv).")},
        required=["path"], description="""
What produced a data file, from the JSON sidecar written beside it: the
whole sweep program, every instrument's identity and logged settings, a
snapshot of the lab profile, and the software revision. Read this before
drawing conclusions from a file you did not watch being taken.
"""),

    _tool("set_parameter", "set_parameter", destructive=True, properties={
        "address": dict(_STR, description="Address, 'address.parameter', "
                                          "or a lab profile alias."),
        "parameter": dict(_STR, description="Parameter name, when the "
                                            "address does not include it."),
        "value": _NUM,
        "speed": dict(_NUM, description="Ramp rate for instruments that "
                                        "ramp themselves.")},
          required=["address", "value"], description="""
MOVES AN INSTRUMENT. Sets one parameter directly, through the same safety
envelope the sweep engine uses — out-of-range values are refused naming
the limit. For setting up a measurement (bias, temperature setpoint), not
for stepping through values by hand: that is a sweep.
"""),
]

_BY_NAME = {tool["name"]: tool for tool in TOOLS}


def public_tools() -> list:
    """The tool list as the client sees it (no internal 'method' key)."""
    return [{k: v for k, v in tool.items() if k != "method"}
            for tool in TOOLS]


class MCPHandler:
    """One client connection's worth of JSON-RPC state."""

    def __init__(self, session, log: Optional[Callable[[str], None]] = None):
        self.session = session
        self.log = log or (lambda _line: None)
        self.initialized = False
        self.client: dict = {}

    # ---- JSON-RPC ----------------------------------------------------
    def handle_line(self, line: str) -> Optional[str]:
        line = (line or "").strip()
        if not line:
            return None
        try:
            message = json.loads(line)
        except ValueError as exc:
            return json.dumps(_error(None, -32700, f"parse error: {exc}"))
        if isinstance(message, list):              # batch
            out = [r for r in (self._dispatch(m) for m in message) if r]
            return json.dumps(out) if out else None
        response = self._dispatch(message)
        return json.dumps(response) if response is not None else None

    def _dispatch(self, message) -> Optional[dict]:
        if not isinstance(message, dict):
            return _error(None, -32600, "invalid request")
        ident = message.get("id")
        method = message.get("method")
        params = message.get("params") or {}
        if method is None:                         # a response to us
            return None
        try:
            if method == "initialize":
                result = self._initialize(params)
            elif method in ("notifications/initialized", "initialized"):
                self.initialized = True
                return None
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {"tools": public_tools()}
            elif method == "tools/call":
                result = self._call_tool(params)
            elif method.startswith("notifications/"):
                return None
            else:
                return _error(ident, -32601,
                              f"method '{method}' is not supported")
        except Exception as exc:                   # noqa: BLE001
            self.log(f"error in {method}: {traceback.format_exc()}")
            return _error(ident, -32603, f"{type(exc).__name__}: {exc}")
        if ident is None:
            return None
        return {"jsonrpc": "2.0", "id": ident, "result": result}

    def _initialize(self, params: dict) -> dict:
        self.client = params.get("clientInfo") or {}
        wanted = params.get("protocolVersion")
        version = wanted if wanted in SUPPORTED_VERSIONS else PROTOCOL_VERSION
        self.log(f"client {self.client.get('name', '?')} connected "
                 f"(protocol {version})")
        return {"protocolVersion": version,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": SERVER_INFO,
                "instructions": (
                    "Unisweep drives lab instruments. Call describe_rig "
                    "first — it says what this rig is and what its safe "
                    "limits are. Fill the sweep page in and press its "
                    "buttons the way a person would; dry_run before any "
                    "long sweep. Tools marked as moving instruments do "
                    "exactly that.")}

    # ---- tools -------------------------------------------------------
    def _call_tool(self, params: dict) -> dict:
        name = params.get("name")
        arguments = params.get("arguments") or {}
        tool = _BY_NAME.get(name)
        if tool is None:
            return _tool_error(f"there is no tool called '{name}'")
        if not isinstance(arguments, dict):
            return _tool_error("arguments must be an object")
        method = getattr(self.session, tool["method"], None)
        if method is None:                          # pragma: no cover
            return _tool_error(f"'{name}' is not available in this build")
        try:
            result = method(**arguments)
        except TypeError as exc:
            return _tool_error(f"{name}: {exc}")
        except Exception as exc:                    # noqa: BLE001
            self.log(f"tool {name} failed: {traceback.format_exc()}")
            return _tool_error(f"{type(exc).__name__}: {exc}")
        return _tool_result(result)


def _tool_result(result: Any) -> dict:
    if not isinstance(result, dict):
        result = {"result": result}
    text = json.dumps(result, indent=2, default=str)
    return {"content": [{"type": "text", "text": text}],
            "structuredContent": result,
            "isError": False}


def _tool_error(message: str) -> dict:
    return {"content": [{"type": "text", "text": message}],
            "isError": True}


def _error(ident, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": ident,
            "error": {"code": code, "message": message}}
