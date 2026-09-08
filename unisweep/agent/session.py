"""The agent's view of a running Unisweep.

One object, no transport. :mod:`unisweep.agent.server` maps MCP tools onto
it; a socket server for a future Unisweep daemon would map onto the same
methods without this file changing.

Two rules shape everything here.

**The GUI stays the source of truth.** An assistant does not build a
private copy of the sweep and hand it to the engine — it fills in the same
fields a person fills in and presses the same button, through
:mod:`unisweep.agent.controls`. So whatever it set is visible on screen, a
human can take over mid-thought, and there is no second model of the
experiment that can drift out of step with the first.

**Instrument traffic never runs on the Tk thread.** Reading a lock-in over
GPIB takes tens of milliseconds and opening a dead instrument can take
thirty seconds; doing that inside the UI loop would freeze the window.
Widget work goes through the bridge, instrument work is done on the
calling thread against the registry, which has its own lock.
"""

from __future__ import annotations

import dataclasses
import os
import time
from typing import Any, Iterable, Optional, Sequence

from ..core.config import SweepProgram, program_from_dict, program_to_dict
from ..core.labprofile import DerivedEvaluator, LabProfile
from ..core.limits import LimitPolicy, estimate_program, validate_program
from .bridge import TkBridge
from .controls import ControlError, ControlRegistry, UnknownControl
from .dialogs import intercept
from .tap import plain

__all__ = ["AgentSession", "SessionError"]

_DIM_LABELS = {1: "1D", 2: "2D", 3: "3D"}

#: axis fields that can simply be typed into the card, in the order they
#: must be applied — the device picker repopulates the parameter list, so
#: it has to land before the parameter does
_AXIS_FIELDS = ("device", "parameter", "start", "stop", "mode", "rate",
                "delay", "walks", "snake", "force_stepwise", "back_rate",
                "back_delay")

_MODE_LABELS = {"ratio": "rate, units/s", "step": "step, units/pt"}


class SessionError(RuntimeError):
    """A request that cannot be carried out as asked."""


class AgentSession:
    """Everything an assistant can see or do, on one object."""

    def __init__(self, app, bridge=None):
        self.app = app
        self.bridge = bridge if bridge is not None else TkBridge(app.root)

    # ================================================================
    # the control surface
    # ================================================================
    def registry(self) -> ControlRegistry:
        """Fresh handles for what is currently on screen.

        Rebuilt every call on purpose: axis cards come and go with the
        dimension count and device rows appear as addresses are found, so
        a cached registry would describe a window that no longer exists.
        """
        controls = self.bridge.call(self.app.controls)
        return ControlRegistry(self.bridge, controls)

    def list_controls(self, page: Optional[str] = None,
                      prefix: Optional[str] = None,
                      values: bool = True) -> dict:
        registry = self.registry()
        return {"pages": registry.pages(),
                "controls": registry.describe(page=page, prefix=prefix,
                                              include_values=values)}

    def read_controls(self, names: Optional[Sequence[str]] = None,
                      page: Optional[str] = None,
                      prefix: Optional[str] = None) -> dict:
        return self.registry().read(names=names, page=page, prefix=prefix)

    def set_controls(self, values: dict) -> dict:
        """Type into fields / tick boxes. Applied as one GUI edit."""
        if not values:
            return {}
        return self.registry().set_many(values)

    def press(self, name: str, answers=None, files=None,
              timeout: Optional[float] = None) -> dict:
        """Press a button, answering whatever it asks."""
        return self.registry().press(name, answers=answers, files=files,
                                     timeout=timeout)

    # ================================================================
    # the rig
    # ================================================================
    @property
    def profile(self) -> LabProfile:
        return getattr(self.app, "profile", None) or LabProfile.empty()

    def describe_rig(self) -> dict:
        """What this rig is, in the lab's own language."""
        profile = self.profile
        registry = self.app.registry
        return {
            "lab": profile.lab,
            "sample": dict(profile.sample),
            "profile": profile.describe(),
            "profile_path": profile.path,
            "autonomy": profile.autonomy,
            "has_profile": not profile.is_empty,
            "limits_enforced": bool(getattr(registry, "policy", None)),
            "constants": dict(profile.constants),
            "derived": {name: channel.expression
                        for name, channel in profile.derived.items()},
            "instruments": self.list_instruments()["instruments"],
            "readable_channels": list(registry.read_catalogue()),
            "sweep": self.status(points=0),
        }

    def list_instruments(self) -> dict:
        """Addresses, drivers, parameters and what the profile says they
        mean. Never opens an instrument: option lists come from the cached
        adapter when one exists and from the driver source otherwise."""
        registry = self.app.registry
        profile = self.profile
        out = []
        for address in registry.addresses:
            driver = registry.types.get(address, "")
            adapter = registry.connected(address)
            device = profile.device(address)
            entry: dict = {
                "address": address,
                "driver": driver,
                "installed": registry.is_installed(driver) if driver
                else False,
                "connected": adapter is not None,
            }
            if device is not None:
                entry.update({k: v for k, v in
                              (("alias", device.alias), ("role", device.role),
                               ("notes", device.notes)) if v})
            error = registry.import_error(driver) if driver else ""
            if error:
                entry["import_error"] = error
            params = []
            settable = list(registry.set_options(address))
            readable = list(registry.get_options(address))
            for name in sorted(set(settable) | set(readable)):
                spec = profile.spec(address, name)
                item: dict = {"parameter": name,
                              "settable": name in settable,
                              "readable": name in readable}
                if name in readable:
                    item["channel"] = f"{address}.{name}"
                if spec is not None:
                    if spec.alias:
                        item["alias"] = spec.alias
                    if spec.unit:
                        item["unit"] = spec.unit
                    if spec.quantity:
                        item["quantity"] = spec.quantity
                    if spec.bounded:
                        item["range"] = spec.range_text()
                    if spec.max_rate is not None:
                        item["max_rate"] = spec.max_rate
                    if spec.max_step is not None:
                        item["max_step"] = spec.max_step
                    if not spec.settable:
                        item["settable"] = False
                params.append(item)
            entry["parameters"] = params
            out.append(entry)
        return {"instruments": out}

    # ---- instrument I/O (never on the Tk thread) ---------------------
    def read_channels(self, channels: Iterable[str]) -> dict:
        """Read 'address.option' channels once, plus any derived values."""
        registry = self.app.registry
        profile = self.profile
        wanted = [str(c) for c in (channels or ())]
        values: dict = {}
        errors: dict = {}
        for channel in wanted:
            address, _, option = channel.rpartition(".")
            resolved = profile.resolve(channel)
            if not address and resolved is not None:
                address, option = resolved
                channel = f"{address}.{option}"
            try:
                values[channel] = plain(
                    registry.connect(address).get(option))
            except Exception as exc:               # noqa: BLE001
                errors[channel] = f"{type(exc).__name__}: {exc}"
        out: dict = {"values": values}
        if errors:
            out["errors"] = errors
        derived = DerivedEvaluator(profile, list(values))
        if derived:
            pool = dict(profile.constants)
            pool.update(values)
            out["derived"] = plain(derived.evaluate(pool))
        return out

    def set_parameter(self, address: str, parameter: str = "",
                      value: float = 0.0,
                      speed: Optional[float] = None) -> dict:
        """Set one parameter through the same envelope the engine uses.

        ``address`` may instead be a profile alias ('Vbg') or an
        'address.parameter' string, in which case ``parameter`` is
        implied.
        """
        if not parameter:
            resolved = self.profile.resolve(address)
            if resolved is None and "." in address:
                resolved = tuple(address.rsplit(".", 1))
            if resolved is None:
                raise SessionError(
                    f"'{address}' does not name a settable parameter — "
                    f"pass address and parameter, or an alias from the "
                    f"lab profile")
            address, parameter = resolved
        adapter = self.app.registry.connect(address)
        adapter.set(parameter, float(value), speed=speed)
        read_back = None
        if adapter.can_read(parameter):
            try:
                read_back = plain(adapter.get(parameter))
            except Exception:                      # noqa: BLE001
                read_back = None
        return {"address": address, "parameter": parameter,
                "commanded": float(value), "speed": speed,
                "value": read_back,
                "label": self.profile.label(address, parameter)}

    # ================================================================
    # programs
    # ================================================================
    def get_program(self) -> dict:
        """The sweep the GUI currently describes.

        Runs under dialog interception: the page complains about invalid
        fields with a message box, and that complaint is far more useful
        as data than as a window nobody is looking at.
        """
        page = self.app.pages["Sweep"]
        with intercept() as script:
            program = self.bridge.call(page.build_program)
        out: dict = {"valid": program is not None,
                     "complaints": script.records()}
        if program is not None:
            out["program"] = program_to_dict(program)
        return out

    def apply_program(self, program: dict) -> dict:
        """Fill the sweep page in from a program, field by field.

        This is the ordinary path for running something: the assistant
        types the experiment onto the page, and what it typed is what a
        person sees. Manual step tables are the one thing that cannot be
        typed — they come from a file, so use
        ``sweep.axisN.load_manual_steps`` with ``files=[path]``.
        """
        data = dict(program or {})
        axes = list(data.get("axes") or ())
        if not axes:
            raise SessionError("a program needs at least one axis")
        if len(axes) > 3:
            raise SessionError("Unisweep sweeps at most 3 dimensions")

        # dimensions first: the axis cards below do not exist until it is set
        self.registry().set("sweep.dimensions", _DIM_LABELS[len(axes)])

        edits: dict = {}
        notes: list[str] = []
        for index, axis in enumerate(axes, start=1):
            prefix = f"sweep.axis{index}"
            for field in _AXIS_FIELDS:
                if field == "mode":
                    mode = axis.get("count_mode")
                    if mode:
                        edits[f"{prefix}.mode"] = _MODE_LABELS.get(
                            str(mode), str(mode))
                    continue
                if field in axis:
                    edits[f"{prefix}.{field}"] = axis[field]
            if axis.get("manual_points"):
                notes.append(
                    f"axis {index}: manual step tables are loaded from a "
                    f"file — press {prefix}.load_manual_steps with "
                    f"files=['<path>']")
        for key, control in (("reads", "sweep.reads"),
                             ("condition", "sweep.condition"),
                             ("filename", "sweep.filename"),
                             ("script", "sweep.script")):
            if key in data:
                edits[control] = data[key]
        applied = self.registry().set_many(edits) if edits else {}
        out = self.get_program()
        out["applied"] = applied
        if notes:
            out["notes"] = notes
        return out

    def _program_from(self, program: Optional[dict]):
        """A SweepProgram from a dict, or from what the page shows."""
        if program is not None:
            try:
                return program_from_dict(program), []
            except Exception as exc:               # noqa: BLE001
                raise SessionError(
                    f"that is not a valid sweep program: "
                    f"{type(exc).__name__}: {exc}") from None
        current = self.get_program()
        if not current["valid"]:
            return None, current["complaints"]
        return program_from_dict(current["program"]), current["complaints"]

    def dry_run(self, program: Optional[dict] = None) -> dict:
        """Everything that would happen, without touching an instrument."""
        built, complaints = self._program_from(program)
        out: dict = {"complaints": complaints}
        if built is None:
            out.update({"ok": False,
                        "reason": "the sweep page has fields that need "
                                  "fixing before a program exists"})
            return out
        profile = self.profile
        problems = validate_program(built, profile, self.app.registry)
        points, seconds = estimate_program(built)
        errors = [p for p in problems if p.level == "error"]
        out.update({
            "ok": not errors,
            "program": program_to_dict(built),
            "planned_points": points,
            "estimated_seconds": round(seconds, 1),
            "estimated_duration": _duration(seconds),
            "output_directory": _daily_dir(self.app.core_dir),
            "has_script": bool(built.script.strip()),
            "problems": [{"level": p.level, "where": p.where,
                          "message": p.message} for p in problems],
        })
        if errors:
            out["reason"] = "; ".join(p.message for p in errors)
        return out

    def run_sweep(self, program: Optional[dict] = None,
                  answers=None, check: bool = True) -> dict:
        """Start a sweep by pressing Start, as a person would.

        With ``program`` given the page is filled in first. ``check``
        pre-flights against the lab profile and refuses before anything
        moves; the engine checks again on its own, so turning this off
        loses the explanation, not the protection.
        """
        applied = None
        if program is not None:
            applied = self.apply_program(program)
        if check:
            preview = self.dry_run()
            if not preview.get("ok"):
                return {"started": False, "reason": preview.get(
                    "reason", "pre-flight failed"), "dry_run": preview,
                    "applied": applied}
        # Watch for the engine's own SweepStarted rather than asking
        # whether it is running *now*: a short sweep can be over before
        # this thread looks again, and "already finished" is started.
        mark = self.app.event_tap.sequence
        result = self.press("sweep.start", answers=answers)
        out = {"started": self._saw_start(mark),
               "press": result, "status": self.status(points=0)}
        if applied is not None:
            out["applied"] = applied
        if not out["started"]:
            out["reason"] = ("Start did not begin a sweep — the dialogs "
                             "below say why")
        return out

    def _saw_start(self, since: int, timeout: float = 5.0) -> bool:
        """Did the engine announce a sweep after ``since``?"""
        deadline = time.perf_counter() + timeout
        while True:
            page = self.app.event_tap.since(since, limit=500)
            if any(e["event"] == "SweepStarted" for e in page["events"]):
                return True
            if time.perf_counter() >= deadline:
                return False
            self.bridge.wait(0.02)

    # ---- running-sweep control ---------------------------------------
    def pause(self) -> dict:
        return self.press("sweep.pause")

    def resume(self) -> dict:
        return self.press("sweep.pause")

    def stop(self) -> dict:
        return self.press("sweep.stop")

    def to_zero(self, confirm: bool = False) -> dict:
        if not confirm:
            raise SessionError(
                "to_zero ramps every sweep axis to zero and ends the run — "
                "call it again with confirm=true")
        return self.press("sweep.to_zero", answers=["yes"])

    def edit_running_sweep(self, axis: Optional[int] = None,
                           condition: Optional[str] = None,
                           script: Optional[str] = None,
                           **fields) -> dict:
        """Retune a sweep while it runs — the live-edit path.

        Axis fields are typed into the card and pushed with its Apply
        button, exactly as a person retuning a range mid-run would do, so
        the change takes effect on the next point.
        """
        registry = self.registry()
        if not self.app.event_tap.state == "running":
            raise SessionError("no sweep is running")
        edits: dict = {}
        if axis is not None:
            prefix = f"sweep.axis{int(axis)}"
            for field, value in fields.items():
                if field == "count_mode":
                    edits[f"{prefix}.mode"] = _MODE_LABELS.get(str(value),
                                                               str(value))
                else:
                    edits[f"{prefix}.{field}"] = value
        if condition is not None:
            edits["sweep.condition"] = condition
        if script is not None:
            edits["sweep.script"] = script
        if edits:
            registry.set_many(edits)
        pressed = None
        if axis is not None:
            pressed = self.press(f"sweep.axis{int(axis)}.apply")
        elif edits:
            # the condition and the script travel with any axis's Apply
            pressed = self.press("sweep.axis1.apply")
        return {"edited": list(edits), "press": pressed,
                "status": self.status(points=0)}

    # ================================================================
    # what is happening
    # ================================================================
    def status(self, points: int = 3) -> dict:
        out = self.app.event_tap.snapshot(points=points)
        out["profile"] = self.profile.lab or None
        return out

    def events(self, since: int = 0, limit: int = 200,
               kinds: Optional[Sequence[str]] = None) -> dict:
        return self.app.event_tap.since(
            since, limit=limit, kinds=tuple(kinds) if kinds else None)

    def last_points(self, count: int = 20) -> dict:
        tap = self.app.event_tap
        return {"columns": list(tap.columns),
                "points": tap.last_points(count)}


def _duration(seconds: float) -> str:
    seconds = max(int(seconds), 0)
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours} h {minutes:02d} m"
    if minutes:
        return f"{minutes} m {secs:02d} s"
    return f"{secs} s"


def _daily_dir(core_dir: str) -> str:
    from ..core.writer import daily_data_dir
    try:
        return daily_data_dir(core_dir)
    except Exception:                              # noqa: BLE001
        return os.path.join(core_dir, "<date>", "data_files")
