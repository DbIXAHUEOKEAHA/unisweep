"""Lab profile — what the instruments *mean*, and what they may not do.

The registry knows that ``GPIB0::4::INSTR.A_source_voltage`` is a settable
float. It does not know that this is the back-gate voltage of a graphene
Hall bar, that it is measured in volts, that going past ±8 V punches the
oxide, or that the number actually wanted is ``Rxx = Vxx / 100 nA``. That
knowledge lives in one file per rig::

    config/lab_profile.json        (or .yaml / .yml when PyYAML is present)

Why a file and not a conversation
---------------------------------
An automation agent driving Unisweep must be told the wiring exactly once,
not at the start of every session — and the wiring has to be the *same*
object the safety layer enforces (:mod:`unisweep.core.limits`), otherwise
the description and the protection drift apart. So one profile carries
three things:

* **semantics** — alias, unit, physical quantity and free-text role, so a
  reader (human or machine) can say "sweep Vbg from -5 V to 5 V" instead of
  "set A_source_voltage on GPIB0::4::INSTR";
* **limits** — per parameter minimum / maximum / max rate / max single step
  plus a safe parking value, enforced on every ``set`` that goes through a
  :class:`~unisweep.core.devices.DriverAdapter`;
* **derived channels** — expressions over measured channels and named
  constants (``Rxx = Vxx / I_ac``), so the interesting quantity is defined
  once, in the lab's own language.

Everything is optional. With no profile file the loader returns an empty,
fully permissive profile and Unisweep behaves exactly as it did before.

Naming
------
Any parameter can be referred to in three ways, and :meth:`LabProfile.resolve`
accepts all of them:

* its **alias** — ``Vbg`` (only when the profile gives one);
* ``<device alias>.<parameter>`` — ``gate.A_source_voltage``;
* ``<address>.<parameter>`` — ``GPIB0::4::INSTR.A_source_voltage``, the
  spelling the engine and the CSV columns already use.

Derived-channel expressions additionally accept a *sanitised* spelling of
the full channel name (``GPIB0_4_INSTR_A_current``) so they can be written
even for channels the profile has not aliased.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field, replace
from typing import Any, Iterable, Mapping, Optional

__all__ = ["ParameterSpec", "DeviceSpec", "DerivedChannel", "Interlocks",
           "LabProfile", "Problem", "DerivedEvaluator", "channel_ident",
           "PROFILE_FILENAMES"]

PROFILE_FILENAMES = ("lab_profile.json", "lab_profile.yaml",
                     "lab_profile.yml")

#: autonomy tiers, least to most permissive
AUTONOMY_TIERS = ("readonly", "bounded", "full")

_IDENT_BAD = re.compile(r"[^0-9A-Za-z_]+")


def channel_ident(name: str) -> str:
    """A Python-identifier spelling of ``'GPIB1::8::INSTR.x'``.

    Derived-channel expressions are compiled with
    :class:`~unisweep.core.expr.SafeExpr`, which only accepts identifiers.
    Channel names contain dots and colons, so every channel also gets this
    mechanical alias — available even when the profile names nothing.
    """
    out = _IDENT_BAD.sub("_", str(name)).strip("_")
    if not out:
        return "ch"
    return out if not out[0].isdigit() else f"ch_{out}"


def _f(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if out == out else None          # drop NaN


class DerivedEvaluator:
    """Computes a profile's derived channels for a row of measurements.

    Purely a reading convenience: derived values are never written to the
    data files and the sweep engine never evaluates them, so nothing about
    a measurement depends on this. It exists so that a reader asking for
    "Rxx" gets ohms instead of lock-in volts.

    Order-independent — derived channels may reference each other, and a
    cycle simply leaves the unresolvable names out rather than looping.
    """

    def __init__(self, profile, channels):
        from .expr import ExprError, SafeExpr
        self._ExprError = ExprError
        self.names: list[str] = []
        self._exprs: dict = {}
        self.errors: dict[str, str] = {}
        self.constants = dict(getattr(profile, "constants", {}) or {})
        variables = dict(profile.channel_variables(channels))
        variables.update({name: name for name in self.constants})
        variables.update({name: name for name in
                          getattr(profile, "derived", {}) or {}})
        for name, channel in (getattr(profile, "derived", {}) or {}).items():
            source = getattr(channel, "expression", "")
            if not str(source).strip():
                self.errors[name] = "empty expression"
                continue
            try:
                self._exprs[name] = SafeExpr(str(source), variables)
                self.names.append(name)
            except ExprError as exc:
                self.errors[name] = str(exc)

    def __bool__(self) -> bool:
        return bool(self._exprs)

    def evaluate(self, values: Mapping[str, Any]) -> dict:
        out: dict = {}
        if not self._exprs:
            return out
        pool = dict(self.constants)
        pool.update(values)
        pending = dict(self._exprs)
        while pending:
            progressed = False
            for name in list(pending):
                expr = pending[name]
                if any(dep not in pool for dep in expr.canonical_used):
                    continue
                del pending[name]
                progressed = True
                try:
                    out[name] = float(expr(dict(pool), tol=0.0))
                except (self._ExprError, TypeError, ValueError):
                    continue
                pool[name] = out[name]
            if not progressed:
                break
        return out


@dataclass(frozen=True)
class Problem:
    """One validation finding. ``level`` is 'error' or 'warning'."""
    level: str
    where: str
    message: str

    @property
    def fatal(self) -> bool:
        return self.level == "error"

    def __str__(self) -> str:                    # pragma: no cover - display
        return f"[{self.level}] {self.where}: {self.message}"


def _vector_mode(value: Any) -> str:
    """``true``/``false`` are the natural things to write in JSON, and
    "auto" is what the absence of the key means."""
    if isinstance(value, bool):
        return "always" if value else "never"
    text = str(value or "auto").strip().lower()
    return text if text in ("auto", "always", "never") else "auto"


@dataclass(frozen=True)
class ParameterSpec:
    """Meaning and safe envelope of one driver parameter."""

    parameter: str                    # the driver's own set/get option name
    alias: str = ""                   # short physical name ('Vbg', 'Rxx')
    unit: str = ""
    quantity: str = ""                # human description of the quantity
    minimum: Optional[float] = None   # hard lower bound for any set
    maximum: Optional[float] = None   # hard upper bound for any set
    max_rate: Optional[float] = None  # units/second ceiling for ramps
    max_step: Optional[float] = None  # biggest single jump allowed
    safe_value: Optional[float] = None   # where 'park safely' puts it
    settable: bool = True
    readable: bool = True
    notes: str = ""
    #: whether a reading of this parameter is a whole trace. "auto"
    #: decides by the shape of the value, which is right almost always;
    #: "always"/"never" settle a device that is ambiguous about it.
    vector: str = "auto"
    #: the trace's own x axis: a list of values, or the name of the
    #: driver getter that reports them. Absent, the driver's
    #: ``<option>_axis`` is tried and then the plain index.
    vector_axis: Any = None
    axis_name: str = ""               # 'frequency', 'delay'
    axis_unit: str = ""               # 'Hz', 's'

    # ---- helpers -----------------------------------------------------
    @property
    def bounded(self) -> bool:
        return self.minimum is not None or self.maximum is not None

    def contains(self, value: float) -> bool:
        if self.minimum is not None and value < self.minimum:
            return False
        if self.maximum is not None and value > self.maximum:
            return False
        return True

    def clamp(self, value: float) -> float:
        if self.minimum is not None:
            value = max(value, self.minimum)
        if self.maximum is not None:
            value = min(value, self.maximum)
        return float(value)

    def range_text(self) -> str:
        if not self.bounded:
            return "unbounded"
        lo = "-inf" if self.minimum is None else f"{self.minimum:g}"
        hi = "+inf" if self.maximum is None else f"{self.maximum:g}"
        return f"[{lo}, {hi}]{(' ' + self.unit) if self.unit else ''}"

    def to_dict(self) -> dict:
        out: dict[str, Any] = {}
        for key, value in (("alias", self.alias), ("unit", self.unit),
                           ("quantity", self.quantity),
                           ("notes", self.notes)):
            if value:
                out[key] = value
        for key, value in (("min", self.minimum), ("max", self.maximum),
                           ("max_rate", self.max_rate),
                           ("max_step", self.max_step),
                           ("safe_value", self.safe_value)):
            if value is not None:
                out[key] = value
        if not self.settable:
            out["settable"] = False
        if not self.readable:
            out["readable"] = False
        return out

    @classmethod
    def from_dict(cls, parameter: str, data: Any) -> "ParameterSpec":
        if not isinstance(data, Mapping):
            # a bare string is read as the description, so the shortest
            # useful profile is {"A_current": "gate leakage"}
            return cls(parameter=parameter, quantity=str(data or ""))
        return cls(
            parameter=parameter,
            alias=str(data.get("alias", "") or ""),
            unit=str(data.get("unit", "") or ""),
            quantity=str(data.get("quantity", data.get("description", ""))
                         or ""),
            minimum=_f(data.get("min", data.get("minimum"))),
            maximum=_f(data.get("max", data.get("maximum"))),
            max_rate=_f(data.get("max_rate")),
            max_step=_f(data.get("max_step")),
            safe_value=_f(data.get("safe_value")),
            settable=bool(data.get("settable", True)),
            readable=bool(data.get("readable", True)),
            notes=str(data.get("notes", "") or ""),
            vector=_vector_mode(data.get("vector", "auto")),
            vector_axis=data.get("vector_axis",
                                 data.get("axis", None)),
            axis_name=str(data.get("axis_name", "") or ""),
            axis_unit=str(data.get("axis_unit", "") or ""),
        )


@dataclass(frozen=True)
class InstrumentClass:
    """A *kind* of instrument, not a particular one.

    A lab profile that only described the boxes currently plugged in would
    have to be rewritten every time something was swapped, and an
    assistant reading it would learn nothing transferable. The classes
    below are the general knowledge: what a lock-in is for, what a
    source-measure unit can hurt, why an open-loop positioner is not a
    closed-loop one. A specific address then says which class it belongs
    to, and inherits the meaning.

    ``signature`` is the part that makes this work for instruments the
    profile has never heard of: it lists option names that identify the
    kind. :meth:`LabProfile.classify` matches an unknown driver's own
    option lists against every class's signature, so a box bought
    tomorrow is still placed.
    """

    name: str
    what: str = ""          # what this kind of instrument is, in one line
    sets: str = ""          # what you command on one
    reads: str = ""         # what it gives back
    signature: tuple[str, ...] = ()   # option names that identify the kind
    drivers: tuple[str, ...] = ()     # driver classes of this kind here
    safety: str = ""        # what it can damage, and how
    method: str = ""        # how to use one properly
    notes: str = ""

    def to_dict(self) -> dict:
        out: dict[str, Any] = {}
        for key, value in (("what", self.what), ("sets", self.sets),
                           ("reads", self.reads), ("safety", self.safety),
                           ("method", self.method), ("notes", self.notes)):
            if value:
                out[key] = value
        if self.signature:
            out["signature"] = list(self.signature)
        if self.drivers:
            out["drivers"] = list(self.drivers)
        return out

    @classmethod
    def from_dict(cls, name: str, data: Any) -> "InstrumentClass":
        data = data if isinstance(data, Mapping) else {}
        def _tuple(key):
            raw = data.get(key) or ()
            if isinstance(raw, str):
                raw = [raw]
            return tuple(str(v) for v in raw)
        return cls(
            name=name,
            what=str(data.get("what", "") or ""),
            sets=str(data.get("sets", "") or ""),
            reads=str(data.get("reads", "") or ""),
            signature=_tuple("signature"),
            drivers=_tuple("drivers"),
            safety=str(data.get("safety", "") or ""),
            method=str(data.get("method", "") or ""),
            notes=str(data.get("notes", "") or ""),
        )

    def match_score(self, options: Iterable[str]) -> float:
        """How much of this class's signature the given options cover.

        A signature token counts when an option name is exactly it, or
        when a long enough token appears inside an option name — driver
        authors write ``LI_time_constant``, ``A_source_voltage`` and
        ``volt1`` for concepts named ``time_constant``, ``source_voltage``
        and ``volt``. Keep signatures short: the score is a fraction of
        the tokens listed, so an exhaustive signature scores low on a
        driver that legitimately exposes only part of it.
        """
        if not self.signature:
            return 0.0
        names = [str(o).lower() for o in options]
        hits = 0
        for want in self.signature:
            w = want.lower()
            for n in names:
                if w == n:
                    hits += 1
                    break
                # Substring matching only for tokens long enough to mean
                # something. Without this a driver that exposes PID terms
                # as 'P', 'I', 'D' matches every signature containing the
                # letter p — which classified a cryostat as a positioner.
                # One-directional on purpose: an option name may DECORATE
                # a signature token ('LI_time_constant' carries
                # 'time_constant', 'volt1' carries 'volt'), but an option
                # that is merely a fragment of a token must not count — a
                # cryostat exposing 'Field' was scoring against a magnet
                # supply's 'field_rate' and out-ranking its own class.
                if len(w) >= 4 and w in n:
                    hits += 1
                    break
        return hits / len(self.signature)


@dataclass(frozen=True)
class DeviceSpec:
    """One instrument as the lab thinks of it."""

    address: str
    alias: str = ""                   # 'gate', 'lockin_xx', 'cryostat'
    instrument_class: str = ""        # key into LabProfile.instrument_classes
    role: str = ""                    # free text: what it does here
    driver: str = ""                  # expected driver class (informational)
    notes: str = ""                   # wiring: which contacts, what gain
    parameters: Mapping[str, ParameterSpec] = field(default_factory=dict)

    def spec(self, parameter: str) -> Optional[ParameterSpec]:
        return self.parameters.get(parameter)

    def to_dict(self) -> dict:
        out: dict[str, Any] = {}
        for key, value in (("alias", self.alias),
                           ("class", self.instrument_class),
                           ("role", self.role),
                           ("driver", self.driver), ("notes", self.notes)):
            if value:
                out[key] = value
        params = {name: spec.to_dict()
                  for name, spec in self.parameters.items()}
        if params:
            out["parameters"] = params
        return out

    @classmethod
    def from_dict(cls, address: str, data: Any) -> "DeviceSpec":
        data = data if isinstance(data, Mapping) else {}
        raw = data.get("parameters", {})
        params = {name: ParameterSpec.from_dict(name, spec)
                  for name, spec in (raw.items()
                                     if isinstance(raw, Mapping) else ())}
        return cls(
            address=address,
            alias=str(data.get("alias", "") or ""),
            instrument_class=str(data.get("class",
                                          data.get("instrument_class", ""))
                                 or ""),
            role=str(data.get("role", "") or ""),
            driver=str(data.get("driver", "") or ""),
            notes=str(data.get("notes", "") or ""),
            parameters=params,
        )


@dataclass(frozen=True)
class DerivedChannel:
    """A quantity computed from measured channels and constants."""

    name: str
    expression: str
    unit: str = ""
    quantity: str = ""

    def to_dict(self) -> dict:
        out: dict[str, Any] = {"expression": self.expression}
        if self.unit:
            out["unit"] = self.unit
        if self.quantity:
            out["quantity"] = self.quantity
        return out

    @classmethod
    def from_dict(cls, name: str, data: Any) -> "DerivedChannel":
        if not isinstance(data, Mapping):
            return cls(name=name, expression=str(data or ""))
        return cls(name=name,
                   expression=str(data.get("expression",
                                           data.get("expr", "")) or ""),
                   unit=str(data.get("unit", "") or ""),
                   quantity=str(data.get("quantity",
                                         data.get("description", "")) or ""))


@dataclass(frozen=True)
class Interlocks:
    """Whole-run ceilings, checked before a sweep is allowed to start."""

    max_points: Optional[int] = None
    max_duration_s: Optional[float] = None
    #: groups of parameter references that must not be swept in one program
    #: (e.g. never ramp field and temperature at the same time)
    exclusive_ramps: tuple[tuple[str, ...], ...] = ()
    require_preflight: bool = True    # axes must be near their start value
    #: the per-point script in a SweepProgram. On by default, because it is
    #: how a measured value decides anything — installing a profile must
    #: not silently disable a feature the application already had. Set it
    #: false to lock a rig down for unattended operation.
    allow_script: bool = True

    def to_dict(self) -> dict:
        out: dict[str, Any] = {}
        if self.max_points is not None:
            out["max_points"] = self.max_points
        if self.max_duration_s is not None:
            out["max_duration_s"] = self.max_duration_s
        if self.exclusive_ramps:
            out["exclusive_ramps"] = [list(g) for g in self.exclusive_ramps]
        out["require_preflight"] = self.require_preflight
        out["allow_script"] = self.allow_script
        return out

    @classmethod
    def from_dict(cls, data: Any) -> "Interlocks":
        data = data if isinstance(data, Mapping) else {}
        groups = []
        for group in data.get("exclusive_ramps", ()) or ():
            if isinstance(group, str):
                group = [group]
            names = tuple(str(g) for g in group if str(g).strip())
            if len(names) > 1:
                groups.append(names)
        points = data.get("max_points")
        return cls(
            max_points=int(points) if points not in (None, "") else None,
            max_duration_s=_f(data.get("max_duration_s")),
            exclusive_ramps=tuple(groups),
            require_preflight=bool(data.get("require_preflight", True)),
            allow_script=bool(data.get("allow_script", True)),
        )


@dataclass(frozen=True)
class LabProfile:
    """The whole rig description. Immutable; edit by :meth:`replace_device`."""

    version: int = 1
    lab: str = ""
    sample: Mapping[str, Any] = field(default_factory=dict)
    constants: Mapping[str, float] = field(default_factory=dict)
    instrument_classes: Mapping[str, InstrumentClass] = \
        field(default_factory=dict)
    devices: Mapping[str, DeviceSpec] = field(default_factory=dict)
    derived: Mapping[str, DerivedChannel] = field(default_factory=dict)
    interlocks: Interlocks = field(default_factory=Interlocks)
    autonomy: str = "bounded"
    notes: str = ""
    path: str = ""                     # where it was loaded from ('' = none)

    # ---- construction ------------------------------------------------
    @classmethod
    def empty(cls) -> "LabProfile":
        """A profile that describes nothing and forbids nothing."""
        return cls()

    @property
    def is_empty(self) -> bool:
        return (not self.devices and not self.derived and not self.constants
                and not self.instrument_classes)

    # ---- persistence -------------------------------------------------
    @staticmethod
    def locate(core_dir: str) -> Optional[str]:
        for name in PROFILE_FILENAMES:
            path = os.path.join(core_dir, "config", name)
            if os.path.exists(path):
                return path
        return None

    @classmethod
    def load(cls, core_dir: str) -> "LabProfile":
        """Load ``config/lab_profile.*``; an absent or broken file yields
        the empty (permissive) profile rather than an exception — a rig
        must never fail to start because of its description file."""
        path = cls.locate(core_dir)
        if path is None:
            return cls.empty()
        try:
            return cls.load_file(path)
        except Exception:                          # noqa: BLE001
            return replace(cls.empty(), path=path)

    @classmethod
    def load_file(cls, path: str) -> "LabProfile":
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
        if path.lower().endswith((".yaml", ".yml")):
            try:
                import yaml                        # type: ignore
            except ImportError as exc:             # pragma: no cover
                raise RuntimeError(
                    "lab_profile.yaml needs PyYAML installed; rename the "
                    "file to lab_profile.json to use the stdlib reader"
                ) from exc
            data = yaml.safe_load(text) or {}
        else:
            data = json.loads(text or "{}")
        return replace(cls.from_dict(data), path=path)

    def save(self, core_dir: str, filename: str = "lab_profile.json") -> str:
        path = os.path.join(core_dir, "config", filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2)
        return path

    # ---- (de)serialisation -------------------------------------------
    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "lab": self.lab,
            "notes": self.notes,
            "autonomy": self.autonomy,
            "sample": dict(self.sample),
            "constants": dict(self.constants),
            "instrument_classes": {name: klass.to_dict()
                                   for name, klass
                                   in self.instrument_classes.items()},
            "devices": {addr: dev.to_dict()
                        for addr, dev in self.devices.items()},
            "derived": {name: ch.to_dict()
                        for name, ch in self.derived.items()},
            "interlocks": self.interlocks.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Any) -> "LabProfile":
        data = data if isinstance(data, Mapping) else {}
        raw_devices = data.get("devices", {})
        devices = {str(addr): DeviceSpec.from_dict(str(addr), spec)
                   for addr, spec in (raw_devices.items()
                                      if isinstance(raw_devices, Mapping)
                                      else ())}
        raw_classes = data.get("instrument_classes", {})
        classes = {str(name): InstrumentClass.from_dict(str(name), spec)
                   for name, spec in (raw_classes.items()
                                      if isinstance(raw_classes, Mapping)
                                      else ())}
        raw_derived = data.get("derived", {})
        derived = {str(name): DerivedChannel.from_dict(str(name), spec)
                   for name, spec in (raw_derived.items()
                                      if isinstance(raw_derived, Mapping)
                                      else ())}
        constants = {}
        raw_constants = data.get("constants", {})
        if isinstance(raw_constants, Mapping):
            for name, value in raw_constants.items():
                number = _f(value)
                if number is not None:
                    constants[str(name)] = number
        autonomy = str(data.get("autonomy", "bounded") or "bounded").lower()
        if autonomy not in AUTONOMY_TIERS:
            autonomy = "bounded"
        return cls(
            version=int(data.get("version", 1) or 1),
            lab=str(data.get("lab", "") or ""),
            sample=dict(data.get("sample", {}) or {}),
            constants=constants,
            instrument_classes=classes,
            devices=devices,
            derived=derived,
            interlocks=Interlocks.from_dict(data.get("interlocks")),
            autonomy=autonomy,
            notes=str(data.get("notes", "") or ""),
        )

    # ---- lookup ------------------------------------------------------
    def device(self, address: str) -> Optional[DeviceSpec]:
        return self.devices.get(address)

    def spec(self, address: str, parameter: str) -> Optional[ParameterSpec]:
        dev = self.devices.get(address)
        return dev.spec(parameter) if dev is not None else None

    def address_of(self, device_alias: str) -> Optional[str]:
        for addr, dev in self.devices.items():
            if dev.alias and dev.alias == device_alias:
                return addr
        return None

    def resolve(self, name: str) -> Optional[tuple[str, str]]:
        """``'Vbg'`` / ``'gate.A_source_voltage'`` / ``'ADDR.param'`` ->
        ``(address, parameter)``. ``None`` when nothing matches."""
        name = (name or "").strip()
        if not name:
            return None
        for addr, dev in self.devices.items():          # bare alias
            for param, spec in dev.parameters.items():
                if spec.alias and spec.alias == name:
                    return addr, param
        if "." in name:
            head, _, param = name.rpartition(".")
            if head in self.devices:
                return head, param
            addr = self.address_of(head)
            if addr is not None:
                return addr, param
        return None

    def alias_of(self, address: str, parameter: str) -> str:
        spec = self.spec(address, parameter)
        return spec.alias if spec is not None and spec.alias else ""

    def label(self, address: str, parameter: str) -> str:
        """The friendliest unambiguous name for a channel."""
        spec = self.spec(address, parameter)
        if spec is not None and spec.alias:
            unit = f" [{spec.unit}]" if spec.unit else ""
            return f"{spec.alias}{unit}"
        return f"{address}.{parameter}"

    # ---- expression variables ----------------------------------------
    def channel_variables(self, channels: Iterable[str]) -> dict[str, str]:
        """alias -> canonical channel name, for derived values.

        ``channels`` are ``'address.option'`` strings (the engine's own
        read names, which are also the CSV column headers). Every channel
        is reachable by its canonical name, by its sanitised identifier,
        and — when the profile names one — by its alias.
        """
        out: dict[str, str] = {}
        for channel in channels:
            addr, _, param = str(channel).rpartition(".")
            out[str(channel)] = str(channel)
            out[channel_ident(channel)] = str(channel)
            alias = self.alias_of(addr, param)
            if alias:
                out[alias] = str(channel)
        return out

    def constant_variables(self) -> dict[str, str]:
        return {name: name for name in self.constants}

    def derived_variables(self) -> dict[str, str]:
        return {name: name for name in self.derived}

    # ---- description for humans and agents ---------------------------
    def class_of(self, what: str) -> Optional[InstrumentClass]:
        """The instrument class of a driver name, an address or an alias.

        Falls back to the class named on the device entry, then to the
        driver lists of every class.
        """
        if not what:
            return None
        key = str(what)
        # A concrete instrument beats a category with the same name: a
        # device aliased 'cryostat' is a particular box, and asking about
        # it should not return the whole class of cryostats. Addresses and
        # aliases are therefore resolved before class names.
        device = self.devices.get(key)
        if device is None:
            for dev in self.devices.values():
                if dev.alias == key:
                    device = dev
                    break
        if device is not None:
            if device.instrument_class in self.instrument_classes:
                return self.instrument_classes[device.instrument_class]
            key = device.driver or key
        else:
            klass = self.instrument_classes.get(key)
            if klass is not None:
                return klass
            for dev in self.devices.values():
                if dev.driver == key and \
                        dev.instrument_class in self.instrument_classes:
                    return self.instrument_classes[dev.instrument_class]
        low = key.lower()
        for klass in self.instrument_classes.values():
            if any(d.lower() == low for d in klass.drivers):
                return klass
        return None

    def classify(self, set_options: Iterable[str] = (),
                 get_options: Iterable[str] = (),
                 threshold: float = 0.30
                 ) -> list[tuple[str, float]]:
        """Guess the class of an instrument from its own option lists.

        This is what makes the profile useful for hardware it has never
        heard of: a new box is placed by what its driver *offers*, not by
        what it is called. Returns ``(class name, score)`` best first;
        empty when nothing matches well enough, which is itself an answer
        worth reporting rather than guessing past.
        """
        options = list(set_options) + list(get_options)
        if not options:
            return []
        scored = [(name, klass.match_score(options))
                  for name, klass in self.instrument_classes.items()]
        scored = [(n, round(sc, 3)) for n, sc in scored if sc >= threshold]
        scored.sort(key=lambda t: (-t[1], t[0]))
        return scored

    def describe(self) -> str:
        """A compact plain-text rendering — this is what an assistant is
        handed instead of the raw driver option lists."""
        lines: list[str] = []
        if self.lab:
            lines.append(f"Lab: {self.lab}")
        if self.sample:
            bits = ", ".join(f"{k}={v}" for k, v in self.sample.items())
            lines.append(f"Sample: {bits}")
        if self.constants:
            bits = ", ".join(f"{k}={v:g}" for k, v in self.constants.items())
            lines.append(f"Constants: {bits}")
        if self.instrument_classes:
            lines.append("")
            lines.append("INSTRUMENT CLASSES — the kinds of hardware this "
                         "lab uses. A specific box inherits the meaning of "
                         "its class; an unlisted box is placed by matching "
                         "its option names against these signatures.")
            for name, klass in self.instrument_classes.items():
                lines.append(f"  [{name}] {klass.what}")
                if klass.sets:
                    lines.append(f"      sets:   {klass.sets}")
                if klass.reads:
                    lines.append(f"      reads:  {klass.reads}")
                if klass.safety:
                    lines.append(f"      SAFETY: {klass.safety}")
                if klass.method:
                    lines.append(f"      method: {klass.method}")
                if klass.notes:
                    lines.append(f"      note:   {klass.notes}")
                if klass.drivers:
                    lines.append("      drivers here: "
                                 + ", ".join(klass.drivers))
                if klass.signature:
                    lines.append("      identified by: "
                                 + ", ".join(klass.signature))
            lines.append("")
        if self.devices:
            lines.append("CONFIGURED INSTRUMENTS — what is on this rig now.")
        for addr, dev in self.devices.items():
            head = addr
            if dev.alias:
                head = f"{dev.alias} ({addr})"
            if dev.instrument_class:
                head += f"  [{dev.instrument_class}]"
            if dev.role:
                head += f" — {dev.role}"
            lines.append(head)
            if dev.notes:
                lines.append(f"    note: {dev.notes}")
            for param, spec in dev.parameters.items():
                tag = spec.alias or param
                bits = [f"    {tag} = {addr}.{param}"]
                if spec.quantity:
                    bits.append(spec.quantity)
                if spec.bounded:
                    bits.append(f"limit {spec.range_text()}")
                if spec.max_rate is not None:
                    unit = f"{spec.unit}/s" if spec.unit else "units/s"
                    bits.append(f"max rate {spec.max_rate:g} {unit}")
                if not spec.settable:
                    bits.append("read-only")
                lines.append("  ".join(bits))
        if self.derived:
            lines.append("Derived channels")
            for name, ch in self.derived.items():
                unit = f" [{ch.unit}]" if ch.unit else ""
                bits = [f"    {name}{unit} = {ch.expression}"]
                if ch.quantity:
                    bits.append(ch.quantity)
                lines.append("  ".join(bits))
        inter = []
        if self.interlocks.max_points is not None:
            inter.append(f"max {self.interlocks.max_points} points")
        if self.interlocks.max_duration_s is not None:
            inter.append(f"max {self.interlocks.max_duration_s:g} s")
        for group in self.interlocks.exclusive_ramps:
            inter.append("never sweep together: " + " + ".join(group))
        if not self.interlocks.allow_script:
            inter.append("per-point script forbidden")
        if inter:
            lines.append("Interlocks: " + "; ".join(inter))
        lines.append(f"Autonomy tier: {self.autonomy}")
        return "\n".join(lines) if lines else "(no lab profile configured)"

    # ---- validation --------------------------------------------------
    def validate(self, registry=None) -> list[Problem]:
        """Structural checks, plus cross-checks against a live registry.

        Never raises: the result is a list the Devices page (or an agent)
        can render. Passing ``registry`` additionally verifies that every
        described address is assigned and every named parameter exists in
        the driver's option lists.
        """
        problems: list[Problem] = []
        if self.autonomy not in AUTONOMY_TIERS:
            problems.append(Problem("error", "autonomy",
                                    f"unknown tier '{self.autonomy}'"))
        seen_alias: dict[str, str] = {}
        for addr, dev in self.devices.items():
            where = dev.alias or addr
            if dev.alias and dev.alias in seen_alias:
                problems.append(Problem(
                    "error", where,
                    f"device alias '{dev.alias}' is already used by "
                    f"{seen_alias[dev.alias]}"))
            elif dev.alias:
                seen_alias[dev.alias] = addr
            set_options = get_options = None
            if registry is not None:
                try:
                    set_options = list(registry.set_options(addr))
                    get_options = list(registry.get_options(addr))
                except Exception:                  # noqa: BLE001
                    set_options = get_options = None
                if not registry.types.get(addr) and addr != "Time":
                    problems.append(Problem(
                        "warning", where,
                        "no driver type assigned to this address on the "
                        "Devices page"))
            for param, spec in dev.parameters.items():
                tag = f"{where}.{param}"
                if spec.alias:
                    if spec.alias in seen_alias:
                        problems.append(Problem(
                            "error", tag,
                            f"alias '{spec.alias}' is already used by "
                            f"{seen_alias[spec.alias]}"))
                    else:
                        seen_alias[spec.alias] = tag
                if (spec.minimum is not None and spec.maximum is not None
                        and spec.minimum > spec.maximum):
                    problems.append(Problem(
                        "error", tag,
                        f"min {spec.minimum:g} is above max "
                        f"{spec.maximum:g}"))
                if spec.max_rate is not None and spec.max_rate <= 0:
                    problems.append(Problem(
                        "error", tag, "max_rate must be positive"))
                if spec.max_step is not None and spec.max_step <= 0:
                    problems.append(Problem(
                        "error", tag, "max_step must be positive"))
                if (spec.safe_value is not None
                        and not spec.contains(spec.safe_value)):
                    problems.append(Problem(
                        "error", tag,
                        f"safe_value {spec.safe_value:g} lies outside "
                        f"{spec.range_text()}"))
                if set_options is not None and spec.settable \
                        and param not in set_options \
                        and param not in (get_options or ()):
                    problems.append(Problem(
                        "warning", tag,
                        f"'{param}' is not in the driver's set_options or "
                        f"get_options"))
        for name, ch in self.derived.items():
            if not ch.expression.strip():
                problems.append(Problem("error", f"derived.{name}",
                                        "empty expression"))
            if name in seen_alias:
                problems.append(Problem(
                    "error", f"derived.{name}",
                    f"name collides with {seen_alias[name]}"))
        for name in self.constants:
            if name in seen_alias:
                problems.append(Problem(
                    "error", f"constants.{name}",
                    f"name collides with {seen_alias[name]}"))
        for group in self.interlocks.exclusive_ramps:
            for ref in group:
                if self.resolve(ref) is None:
                    problems.append(Problem(
                        "warning", "interlocks",
                        f"exclusive_ramps names '{ref}', which does not "
                        f"resolve to a parameter"))
        return problems

    # ---- small editing helpers (the GUI / an agent build profiles) ---
    def replace_device(self, spec: DeviceSpec) -> "LabProfile":
        devices = dict(self.devices)
        devices[spec.address] = spec
        return replace(self, devices=devices)

    def with_parameter(self, address: str,
                       spec: ParameterSpec) -> "LabProfile":
        dev = self.devices.get(address) or DeviceSpec(address=address)
        params = dict(dev.parameters)
        params[spec.parameter] = spec
        return self.replace_device(replace(dev, parameters=params))
