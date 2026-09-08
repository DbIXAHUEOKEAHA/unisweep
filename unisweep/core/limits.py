"""Safety envelope: nothing reaches an instrument outside its profile.

Two lines of defence, both fed from the same
:class:`~unisweep.core.labprofile.LabProfile`:

1. :class:`LimitPolicy` — a runtime gate installed on the
   :class:`~unisweep.core.devices.DeviceRegistry`. Every
   ``DriverAdapter.set`` consults it, so *any* caller (the sweep engine, the
   Devices page's Test button, a per-point script, an automation agent)
   is bounded by the same numbers. There is no path to the hardware that
   skips it.
2. :func:`validate_program` — a pre-flight over a whole
   :class:`~unisweep.core.config.SweepProgram`. Catching an out-of-range
   endpoint before the sweep starts is far better than faulting on it two
   hours in, and it gives an assistant a *reason* it can act on ("Vbg stop
   of 12 V exceeds the +8 V limit") instead of a stack trace.

Design notes
------------
* **Absent profile means no limits.** An empty profile permits everything,
  so installing this layer cannot change the behaviour of an existing rig
  until its owner writes the file.
* **A safety move is never blocked.** Ramping to zero, parking at
  ``safe_value`` and retreating from a fault pass ``safety=True``,
  which *clamps* into the allowed range instead of raising — a protection
  mechanism that can itself be refused by the limits would be worse than
  no protection at all.
* **``max_step`` applies to jumps, not to ramps.** The engine hands a
  self-ramping instrument one ``set`` with a ``speed`` and lets it travel;
  that is not a jump. A ``set`` with no speed *is*, and on a gate line that
  is the dangerous one — so the step ceiling is enforced exactly there.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .labprofile import LabProfile, ParameterSpec, Problem

__all__ = ["LimitViolation", "LimitPolicy", "validate_program",
           "estimate_program"]


class LimitViolation(RuntimeError):
    """A set was refused by the lab profile's safety envelope."""

    def __init__(self, address: str, parameter: str, message: str):
        super().__init__(f"{address}.{parameter}: {message}")
        self.address = address
        self.parameter = parameter
        self.reason = message


class LimitPolicy:
    """Runtime gate over ``DriverAdapter.set``.

    Held by the registry and shared by every adapter it hands out, so a
    profile reload updates the whole application at once.
    """

    def __init__(self, profile: Optional[LabProfile] = None,
                 enabled: bool = True):
        self.profile = profile or LabProfile.empty()
        self.enabled = bool(enabled)

    # ---- introspection -----------------------------------------------
    @property
    def readonly(self) -> bool:
        return self.enabled and self.profile.autonomy == "readonly"

    def spec(self, address: str, parameter: str) -> Optional[ParameterSpec]:
        return self.profile.spec(address, parameter)

    def bounds(self, address: str,
               parameter: str) -> tuple[Optional[float], Optional[float]]:
        spec = self.spec(address, parameter)
        return (None, None) if spec is None else (spec.minimum, spec.maximum)

    def safe_value(self, address: str, parameter: str) -> float:
        """Where 'park this safely' puts the parameter (0 by default)."""
        spec = self.spec(address, parameter)
        if spec is None:
            return 0.0
        if spec.safe_value is not None:
            return float(spec.safe_value)
        return spec.clamp(0.0)

    # ---- the gate ----------------------------------------------------
    def check_set(self, address: str, parameter: str, value: float,
                  speed: Optional[float] = None,
                  current: Optional[float] = None,
                  safety: bool = False) -> tuple[float, Optional[float]]:
        """Validate one set. Returns the ``(value, speed)`` to actually use.

        Raises :class:`LimitViolation` for a refused move. With
        ``safety=True`` nothing is ever refused: the value is clamped into
        the allowed range and the rate ceiling still applies.
        """
        value = float(value)
        if not self.enabled:
            return value, speed
        spec = self.spec(address, parameter)
        if self.readonly and not safety:
            raise LimitViolation(
                address, parameter,
                "the lab profile is in read-only autonomy tier — no "
                "parameter may be set")
        if spec is None:
            return value, speed
        if not spec.settable and not safety:
            raise LimitViolation(
                address, parameter,
                f"marked read-only in the lab profile"
                + (f" ({spec.notes})" if spec.notes else ""))
        if not spec.contains(value):
            if not safety:
                raise LimitViolation(
                    address, parameter,
                    f"{value:g}{(' ' + spec.unit) if spec.unit else ''} is "
                    f"outside the allowed range {spec.range_text()}")
            value = spec.clamp(value)
        if spec.max_rate is not None and speed is not None:
            try:
                speed = min(abs(float(speed)), float(spec.max_rate))
            except (TypeError, ValueError):
                speed = float(spec.max_rate)
        elif spec.max_rate is not None and speed is None:
            # a ramping instrument commanded without a rate still gets the
            # ceiling, so 'no speed given' can't mean 'slew at maximum'
            speed = float(spec.max_rate)
        if (spec.max_step is not None and current is not None
                and speed is None and not safety):
            try:
                jump = abs(value - float(current))
            except (TypeError, ValueError):
                jump = 0.0
            if jump > spec.max_step:
                raise LimitViolation(
                    address, parameter,
                    f"a single step of {jump:g} exceeds the max_step of "
                    f"{spec.max_step:g} (from {float(current):g} to "
                    f"{value:g}) — use a finer step or raise max_step")
        return value, speed

    # ---- convenience --------------------------------------------------
    def describe(self) -> str:
        if not self.enabled:
            return "limit enforcement OFF"
        if self.profile.is_empty:
            return "no lab profile — every parameter unbounded"
        return self.profile.describe()


# ---------------------------------------------------------------------------
def estimate_program(program) -> tuple[int, float]:
    """(points, seconds) a program is expected to take.

    Same accounting the engine's ETA uses: the product of the per-axis
    planned counts and walk counts, with the coupled-equality axis (if the
    condition defines one) removed because it is solved rather than looped.
    """
    solved = None
    try:
        from .condition import ConditionSet
        cond = ConditionSet(program.condition, program.dimensions)
        if cond.coupled is not None:
            solved = cond.coupled.solved - 1
    except Exception:                              # noqa: BLE001
        solved = None
    total = 1
    seconds = 0.0
    counts: list[int] = []
    for i, axis in enumerate(program.axes):
        if i == solved:
            counts.append(1)
            continue
        n = max(axis.planned_count(), 1) * axis.effective_walks()
        counts.append(n)
        total *= n
    # dwell is dominated by the innermost axis; outer axes add their own
    for i, axis in enumerate(program.axes):
        outer = 1
        for j in range(i):
            outer *= counts[j]
        seconds += outer * counts[i] * axis.point_delay(False)
    return total, seconds


def validate_program(program, profile: Optional[LabProfile] = None,
                     registry=None,
                     policy: Optional[LimitPolicy] = None) -> list[Problem]:
    """Pre-flight a whole sweep against the lab profile.

    Returns findings; the caller decides what to do with them. Anything at
    level ``'error'`` describes a sweep that would be refused (or would
    damage something) and should block the start.
    """
    profile = profile or (policy.profile if policy else None) \
        or LabProfile.empty()
    problems: list[Problem] = []

    if profile.autonomy == "readonly":
        problems.append(Problem(
            "error", "autonomy",
            "the lab profile is in read-only tier — sweeps are not "
            "permitted until it is raised to 'bounded' or 'full'"))

    # ---- per-axis envelope -------------------------------------------
    swept: list[tuple[str, str, str]] = []     # (address, parameter, label)
    for i, axis in enumerate(program.axes):
        where = f"axis {i + 1}"
        label = profile.label(axis.device, axis.parameter)
        swept.append((axis.device, axis.parameter, label))
        spec = profile.spec(axis.device, axis.parameter)
        if registry is not None:
            try:
                options = list(registry.set_options(axis.device))
            except Exception:                      # noqa: BLE001
                options = []
            if options and axis.parameter not in options:
                problems.append(Problem(
                    "error", where,
                    f"'{axis.parameter}' is not settable on "
                    f"{axis.device}"))
        if spec is None:
            continue
        if not spec.settable:
            problems.append(Problem(
                "error", where,
                f"{label} is marked read-only in the lab profile"))
        for name, value in (("start", axis.start), ("stop", axis.stop)):
            if not spec.contains(float(value)):
                problems.append(Problem(
                    "error", where,
                    f"{label} {name} {float(value):g}"
                    f"{(' ' + spec.unit) if spec.unit else ''} is outside "
                    f"the allowed range {spec.range_text()}"))
        if axis.manual_points:
            bad = [p for p in axis.manual_points if not spec.contains(p)]
            if bad:
                problems.append(Problem(
                    "error", where,
                    f"{label}: {len(bad)} manual step(s) outside "
                    f"{spec.range_text()} (first {bad[0]:g})"))
        if spec.max_rate is not None and abs(axis.rate) > spec.max_rate:
            problems.append(Problem(
                "warning", where,
                f"{label} rate {abs(axis.rate):g} exceeds the profile's "
                f"max_rate {spec.max_rate:g} — it will be clamped"))
        if spec.max_step is not None:
            step = axis.step_size(False)
            if step > spec.max_step:
                problems.append(Problem(
                    "warning", where,
                    f"{label} step {step:g} exceeds max_step "
                    f"{spec.max_step:g} — allowed only if the instrument "
                    f"ramps to each point"))

    # ---- read channels ------------------------------------------------
    if registry is not None:
        for read in program.reads:
            addr, _, option = str(read).rpartition(".")
            try:
                options = list(registry.get_options(addr))
            except Exception:                      # noqa: BLE001
                options = []
            if options and option not in options:
                problems.append(Problem(
                    "warning", "reads",
                    f"'{read}' is not in {addr}'s get_options"))

    # ---- interlocks ---------------------------------------------------
    inter = profile.interlocks
    points, seconds = estimate_program(program)
    if inter.max_points is not None and points > inter.max_points:
        problems.append(Problem(
            "error", "interlocks",
            f"the program plans {points} points, above the profile's "
            f"max_points of {inter.max_points}"))
    if inter.max_duration_s is not None and seconds > inter.max_duration_s:
        problems.append(Problem(
            "error", "interlocks",
            f"estimated duration {seconds / 3600:.1f} h exceeds the "
            f"profile's max_duration_s of "
            f"{inter.max_duration_s / 3600:.1f} h"))
    for group in inter.exclusive_ramps:
        resolved = set()
        for ref in group:
            hit = profile.resolve(ref)
            if hit is not None:
                resolved.add(hit)
        clash = [lbl for addr, param, lbl in swept if (addr, param) in resolved]
        if len(clash) > 1:
            problems.append(Problem(
                "error", "interlocks",
                "this program sweeps " + " and ".join(sorted(set(clash)))
                + ", which the profile forbids in one run"))
    if program.script.strip() and not inter.allow_script:
        problems.append(Problem(
            "error", "script",
            "the per-point script runs arbitrary Python; the lab profile "
            "has allow_script=false"))
    if inter.require_preflight and not program.approach_start:
        problems.append(Problem(
            "warning", "preflight",
            "approach_start is off, so instruments start from wherever "
            "they stand; the profile asks for a preflight approach"))
    return problems
