"""Device layer.

Design goals:

* **Existing driver files keep working unchanged.** Anything in the
  ``resources`` folder exposing the legacy duck-typed contract
  (``set_options`` / ``get_options`` lists, ``X()`` getters,
  ``set_X(value, speed=...)`` setters, optional ``sweepable`` / ``eps`` /
  ``maxspeed`` lists, optional ``pause()`` / ``clear()``) is wrapped by
  :class:`DriverAdapter` without modification.
* **Lazy connection.** The legacy app opened every VISA resource at import
  time; here nothing is connected until an address is actually used (or the
  user presses *Test* on the Devices page), so startup is instant and one
  dead instrument can't block the app.
* **Background scanning.** VISA / serial discovery runs off the GUI thread.
* pyvisa / pyserial are imported lazily so the core (and the test suite)
  runs on machines without them.
"""

from __future__ import annotations

import glob
import importlib
import importlib.util
import inspect
import json
import os
import sys
import threading
import time
from typing import Callable, Optional

import numpy as np

__all__ = ["VirtualTime", "DriverAdapter", "DeviceRegistry",
           "probe_sweepable", "DRIVER_PACKAGE"]

DRIVER_PACKAGE = "unisweep_drivers"
"""Namespace the driver files in ``resources`` are imported under.

Dotted so a driver called ``time.py`` or ``json.py`` cannot shadow a
stdlib module. The package itself has to exist in ``sys.modules`` — see
:func:`_ensure_driver_package`.
"""


def _ensure_driver_package(resources_dir: str):
    """Register the parent package the driver modules live under.

    Drivers are registered as ``unisweep_drivers.<Name>``, and Python's
    reload machinery resolves the PARENT of a dotted name before doing
    anything else. Without this stub every driver raises

        ImportError: parent 'unisweep_drivers' not in sys.modules

    the moment something tries to reload it. Nothing in Unisweep reloads
    drivers, so this was invisible — until you run ``main.py`` from an
    IPython console with autoreload on, which tries to reload every
    module on every cell and prints a traceback per driver.
    """
    import types
    package = sys.modules.get(DRIVER_PACKAGE)
    if package is None:
        package = types.ModuleType(DRIVER_PACKAGE)
        sys.modules[DRIVER_PACKAGE] = package
    package.__path__ = [resources_dir]      # type: ignore[attr-defined]
    return package


# ---------------------------------------------------------------------------
class VirtualTime:
    """The built-in 'Time' pseudo-device (sweeping it sweeps wall time)."""

    def __init__(self, adress=None):  # legacy spelling kept on purpose
        self.set_options = ["Time"]
        self.get_options = ["Elapsed", "Random"]
        self._t0 = time.perf_counter()

    def set_Time(self, value=None, speed=None):
        return

    def Elapsed(self):
        return time.perf_counter() - self._t0

    def Random(self):
        return float(np.random.random())


# ---------------------------------------------------------------------------
class DriverAdapter:
    """Uniform facade over a legacy driver instance.

    When a :class:`~unisweep.core.limits.LimitPolicy` is attached (the
    registry does that from the lab profile), every ``set`` passes through
    it first. That is deliberately placed here rather than in the engine:
    the Devices page's Test button, a per-point script and an automation
    agent all reach the hardware through this one method, so this is the
    only place a safety envelope cannot be walked around.
    """

    def __init__(self, address: str, instance, policy=None):
        self.address = address
        self.raw = instance
        self.policy = policy
        #: last value successfully commanded per parameter — the reference
        #: point for the profile's max_step ceiling, tracked here so the
        #: check costs no extra instrument I/O in the measurement loop
        self._last_set: dict[str, float] = {}
        self.set_options: list[str] = list(getattr(instance, "set_options", []))
        self.get_options: list[str] = list(getattr(instance, "get_options", []))

    # ---- capabilities ----------------------------------------------------
    def _listed(self, attr: str, parameter: str, default=None):
        values = getattr(self.raw, attr, None)
        if values is None:
            return default
        try:
            v = values[self.set_options.index(parameter)]
            return default if v is None else v
        except (ValueError, IndexError, TypeError):
            return default

    def eps(self, parameter: str, fallback: float) -> float:
        v = self._listed("eps", parameter)
        try:
            return float(v) if v is not None else float(fallback)
        except (TypeError, ValueError):
            return float(fallback)

    def sweepable(self, parameter: str) -> bool:
        return bool(self._listed("sweepable", parameter, False))

    def maxspeed(self, parameter: str) -> Optional[float]:
        v = self._listed("maxspeed", parameter)
        try:
            return float(v) if v is not None else None
        except (TypeError, ValueError):
            return None

    # ---- I/O -------------------------------------------------------------
    def get(self, option: str) -> float:
        return getattr(self.raw, option)()

    def can_read(self, parameter: str) -> bool:
        return parameter in self.get_options

    def _current(self, parameter: str) -> Optional[float]:
        """Where the instrument stands now, for the step ceiling.

        ``_last_set`` only remembers what *we* commanded, so it is empty
        for every parameter until the first set of a session — and a jump
        cannot be measured without a value to measure it from. The first
        command after a restart was therefore unguarded whatever its size:
        on a gate line, the entire range in one go, which is the exact
        move the ceiling exists to stop.

        So ask the instrument the first time, and remember the answer.
        Seeding once rather than reading every time keeps the measurement
        loop free of extra I/O — after the first set the engine is the
        only thing moving the parameter, so our record stays true.
        """
        if parameter not in self._last_set and self.can_read(parameter):
            try:
                self._last_set[parameter] = float(self.get(parameter))
            except Exception:                     # noqa: BLE001
                pass                              # unreadable: as before
        return self._last_set.get(parameter)

    def set(self, parameter: str, value: float,
            speed: Optional[float] = None, safety: bool = False) -> None:
        """Command a parameter, subject to the lab profile's envelope.

        ``safety=True`` marks a protective move (ramp to zero, park at the
        safe value, retreat from a fault): those are clamped into the
        allowed range instead of being refused, because a safety mechanism
        the limits can veto is worse than none.
        """
        policy = getattr(self, "policy", None)
        if policy is not None:
            value, speed = policy.check_set(
                self.address, parameter, value, speed=speed,
                current=self._current(parameter), safety=safety,
                ramps=self.sweepable(parameter))
        setter = getattr(self.raw, f"set_{parameter}")
        if speed is not None:
            try:
                params = inspect.signature(setter).parameters
            except (TypeError, ValueError):
                params = {}
            if "speed" in params:
                setter(value=value, speed=speed)
                self._last_set[parameter] = float(value)
                return
        setter(value=value)
        self._last_set[parameter] = float(value)

    def pause(self) -> None:
        fn = getattr(self.raw, "pause", None)
        if callable(fn):
            fn()

    def close(self) -> None:
        """Release the instrument: call the driver's ``close()`` if the
        library provides one. Idempotent and exception-proof — a dead
        device must never block application shutdown or the closing of
        its siblings."""
        if getattr(self, "_closed", False):
            return
        self._closed = True
        fn = getattr(self.raw, "close", None)
        if callable(fn):
            try:
                fn()
            except Exception as exc:              # noqa: BLE001
                print(f"[unisweep] {self.address}: close() raised "
                      f"{type(exc).__name__}: {exc}")

    def clear(self) -> None:
        fn = getattr(self.raw, "clear", None)
        if callable(fn):
            try:
                fn()
            except Exception:
                pass

    def idn(self) -> str:
        for name in ("IDN", "idn"):
            fn = getattr(self.raw, name, None)
            if callable(fn):
                return str(fn())
        return type(self.raw).__name__


# ---------------------------------------------------------------------------
def _driver_class_of(module, mod_name: str):
    """The driver class inside an imported driver file.

    Legacy drivers do NOT always name the class exactly like the file:
    ``Keithley2400.py`` defines ``keithley2400`` and ``SR830.py`` defines
    ``sr830``. Match case-insensitively first, then fall back to the one
    class the module itself defines that looks like a driver (accepts an
    ``adress`` argument or declares set/get options) — so a perfectly
    good driver is never reported as 'not installed'.
    """
    # classes DEFINED here win over ones merely imported: SR830.py does
    # 'from pymeasure...srs import SR830' and defines its own 'sr830' —
    # the exact-name match must not hand back the vendor base class
    own = [obj for name, obj in vars(module).items()
           if inspect.isclass(obj)
           and getattr(obj, "__module__", "") == module.__name__]
    for obj in own:
        if obj.__name__ == mod_name:
            return obj
    for obj in own:
        if obj.__name__.lower() == mod_name.lower():
            return obj
    def _driverish(obj) -> bool:
        if hasattr(obj, "set_options") or hasattr(obj, "get_options"):
            return True
        try:
            params = inspect.signature(obj.__init__).parameters
        except (TypeError, ValueError):
            return False
        return "adress" in params or "address" in params
    cands = [o for o in own if _driverish(o)]
    if len(cands) == 1:
        return cands[0]
    # several driver-ish classes: prefer the one whose name is closest to
    # the file name (e.g. 'sr830' over a 'my_SR830' helper subclass)
    for obj in cands:
        if mod_name.lower() in obj.__name__.lower():
            return obj
    exact = getattr(module, mod_name, None)      # last resort: re-export
    if inspect.isclass(exact):
        return exact
    return None


def _import_driver_classes(resources_dir: str
                           ) -> tuple[dict[str, type], dict[str, str]]:
    """Import every ``<Name>.py`` in resources.

    Returns ``(classes, errors)``: a broken driver is skipped and its error
    is *captured* (shown on the Devices page with a Fix action) instead of
    disappearing into the console.
    """
    classes: dict[str, type] = {}
    errors: dict[str, str] = {}
    if not os.path.isdir(resources_dir):
        return classes, errors
    # support packages (atto_device, libximc, ...) extracted into resources
    # must be importable by the driver files
    if resources_dir not in sys.path:
        sys.path.insert(0, resources_dir)
    # Some repo drivers import through the repository package name
    # ('from devices.X import ...'). Provide a namespace alias so that
    # resolves against resources/ without the full repo layout.
    package = _ensure_driver_package(resources_dir)
    import types
    dev_mod = sys.modules.get("devices")
    if dev_mod is None or resources_dir not in getattr(dev_mod, "__path__",
                                                       []):
        dev_mod = types.ModuleType("devices")
        dev_mod.__path__ = [resources_dir]           # type: ignore[attr-defined]
        sys.modules["devices"] = dev_mod
    for fname in sorted(os.listdir(resources_dir)):
        if not fname.endswith(".py"):
            continue
        mod_name = fname[:-3]
        path = os.path.join(resources_dir, fname)
        try:
            spec = importlib.util.spec_from_file_location(
                f"{DRIVER_PACKAGE}.{mod_name}", path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            setattr(package, mod_name, module)
            spec.loader.exec_module(module)          # type: ignore[union-attr]
            cls = _driver_class_of(module, mod_name)
            if cls is not None:
                classes[mod_name] = cls
            else:
                errors[mod_name] = (f"file imported but defines no driver "
                                    f"class (expected something like "
                                    f"'{mod_name}')")
        except Exception as exc:                     # noqa: BLE001
            errors[mod_name] = f"{type(exc).__name__}: {exc}"
    return classes, errors


def scan_serial_ports() -> list[str]:
    try:
        import serial  # type: ignore
    except ImportError:
        return []
    if sys.platform.startswith("win"):
        candidates = [f"COM{i + 1}" for i in range(256)]
    elif sys.platform.startswith(("linux", "cygwin")):
        candidates = glob.glob("/dev/tty[A-Za-z]*")
    elif sys.platform.startswith("darwin"):
        candidates = glob.glob("/dev/tty.*")
    else:
        return []
    found = []
    for port in candidates:
        try:
            s = serial.Serial(port)
            s.close()
            found.append(port)
        except Exception:
            pass
    return found


def scan_visa() -> list[str]:
    try:
        import pyvisa  # type: ignore
    except ImportError:
        return []
    try:
        return list(pyvisa.ResourceManager().list_resources())
    except Exception:
        return []


# ---------------------------------------------------------------------------
class DeviceRegistry:
    """Addresses, their assigned driver types, and lazily-connected adapters.

    Persists the address->type mapping to the *same*
    ``config/address_dictionary.txt`` JSON file the legacy app used, so an
    existing installation carries its device setup over untouched.
    """

    def __init__(self, core_dir: str, policy=None):
        self.core_dir = core_dir
        #: shared safety envelope handed to every adapter (see limits.py);
        #: ``None`` means unbounded, which is what a rig without a lab
        #: profile gets — installing this layer changes nothing until the
        #: profile file exists
        self.policy = policy
        self.resources_dir = os.path.join(core_dir, "resources")
        self.config_path = os.path.join(core_dir, "config",
                                        "address_dictionary.txt")
        self.driver_classes, self.import_errors = \
            _import_driver_classes(self.resources_dir)
        self.types: dict[str, str] = {}       # address -> class name
        self.addresses: list[str] = ["Time"]
        self._adapters: dict[str, DriverAdapter] = {}
        self._pending: dict[str, threading.Event] = {}
        self._lock = threading.Lock()
        self._load_types()
        # addresses stored in the mapping (manual IP / cDAQ entries) survive
        for addr in self.types:
            if addr not in self.addresses:
                self.addresses.append(addr)

    # ---- persistence -----------------------------------------------------
    def _load_types(self) -> None:
        try:
            with open(self.config_path, "r", encoding="utf-8") as fh:
                self.types = json.load(fh) or {}
        except (OSError, json.JSONDecodeError):
            self.types = {}
        self.types.setdefault("Time", "Time")

    def save_types(self) -> None:
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as fh:
            json.dump(self.types, fh, indent=2)

    def assign(self, address: str, class_name: str) -> None:
        self.types[address] = class_name
        if address not in self.addresses:
            self.addresses.append(address)
        with self._lock:
            old = self._adapters.pop(address, None)
        if old is not None:
            old.close()          # release the session before the new type
                                 # opens its own — never two at once
        self.save_types()

    def add_address(self, address: str) -> None:
        if address and address not in self.addresses:
            self.addresses.append(address)

    def unassign(self, address: str) -> None:
        if address in self.types and address != "Time":
            del self.types[address]
        with self._lock:
            old = self._adapters.pop(address, None)
        if old is not None:
            old.close()
        self.save_types()

    # ---- driver installation support ------------------------------------
    def resolve_type(self, class_name: str) -> str:
        """Assignments may name a driver in a different case than the
        file on disk (``Keithley2400`` vs ``keithley2400.py``) — resolve
        to the key actually loaded so the row shows green and connects."""
        if not class_name or class_name in self.driver_classes:
            return class_name
        low = class_name.lower()
        for key in self.driver_classes:
            if key.lower() == low:
                return key
        for key in self.import_errors:
            if key.lower() == low:
                return key
        return class_name

    def is_installed(self, class_name: str) -> bool:
        """Is the driver file present and importable?"""
        if class_name == "Time":
            return True
        return self.resolve_type(class_name) in self.driver_classes

    def import_error(self, class_name: str) -> str:
        """The captured import failure of a present-but-broken driver."""
        return self.import_errors.get(self.resolve_type(class_name), "")

    def has_driver_file(self, class_name: str) -> bool:
        """Case-insensitively: Windows copies keep the repository's
        spelling, which may differ from the assignment's."""
        if not class_name:
            return False
        want = f"{class_name}.py".lower()
        try:
            return any(f.lower() == want
                       for f in os.listdir(self.resources_dir))
        except OSError:
            return False

    def reload_drivers(self) -> None:
        """Re-scan resources/ (after the installer added new files).

        ``invalidate_caches`` is required so packages pip-installed a moment
        ago (in this very process) become importable by the driver files.
        """
        importlib.invalidate_caches()
        self.driver_classes, self.import_errors = \
            _import_driver_classes(self.resources_dir)

    # ---- assignment display ---------------------------------------------
    def display_name(self, address: str) -> str:
        """'ADDRESS — DriverName' when assigned, so every device picker in
        the GUI shows which instrument sits on which address."""
        driver = self.types.get(address, "")
        if not driver or address == "Time":
            return address
        return f"{address} — {driver}"

    def display_list(self) -> list[str]:
        return [self.display_name(a) for a in self.addresses]

    @staticmethod
    def address_from_display(display: str) -> str:
        return display.rsplit(" — ", 1)[0] if " — " in display else display

    # ---- scanning --------------------------------------------------------
    def scan_async(self, done: Callable[[list[str]], None]) -> None:
        def work():
            found = scan_visa() + scan_serial_ports()
            for addr in found:
                self.add_address(addr)
            done(found)
        threading.Thread(target=work, daemon=True,
                         name="unisweep-scan").start()

    # ---- connections -----------------------------------------------------
    def connect(self, address: str) -> DriverAdapter:
        """One adapter per address, ever — but the (possibly slow) driver
        __init__ runs OUTSIDE the registry lock, so opening one sluggish
        VISA instrument never blocks Test buttons, sweeps, or the startup
        auto-connect of the others. Concurrent connects to the same
        address wait on a per-address event and share the one instance.
        """
        while True:
            with self._lock:
                adapter = self._adapters.get(address)
                if adapter is not None:
                    return adapter
                ev = self._pending.get(address)
                if ev is None:
                    ev = threading.Event()
                    self._pending[address] = ev
                    break                      # this thread creates it
            ev.wait(timeout=120)               # another thread is creating
        try:
            if address == "Time":
                class_name = "Time"
                adapter = DriverAdapter("Time", VirtualTime())
            else:
                class_name = self.types.get(address)
                if not class_name:
                    raise RuntimeError(
                        f"no driver type assigned to '{address}' "
                        f"(Devices page)")
                cls = self.driver_classes.get(
                    self.resolve_type(class_name))
                if cls is None:
                    raise RuntimeError(
                        f"driver class '{class_name}' not found in "
                        f"resources")
                adapter = DriverAdapter(address, cls(adress=address))
            adapter.policy = getattr(self, "policy", None)
        except BaseException:
            with self._lock:
                self._pending.pop(address, None)
            ev.set()
            raise
        with self._lock:
            if self.types.get(address, "Time" if address == "Time"
                              else None) != class_name:
                stale = adapter               # reassigned mid-connect
            else:
                self._adapters[address] = adapter
                stale = None
            self._pending.pop(address, None)
        ev.set()
        if stale is not None:
            stale.close()
            return self.connect(address)      # build the new type instead
        return adapter

    def set_policy(self, policy) -> None:
        """Install (or replace) the safety envelope, including on the
        instruments already connected — reloading the lab profile must not
        leave a live adapter running under the old limits."""
        self.policy = policy
        with self._lock:
            adapters = list(self._adapters.values())
        for adapter in adapters:
            adapter.policy = policy

    def connected(self, address: str) -> Optional[DriverAdapter]:
        with self._lock:
            return self._adapters.get(address)

    def disconnect_all(self) -> None:
        """Close every connected instrument (drivers with a ``close()``
        get it called) and drop the cache. Safe to call twice."""
        with self._lock:
            adapters = list(self._adapters.values())
            self._adapters.clear()
        for a in adapters:
            a.close()

    # ---- catalogue helpers ----------------------------------------------
    def set_options(self, address: str) -> list[str]:
        """Parameter list without connecting, when the class is known."""
        adapter = self.connected(address)
        if adapter is not None:
            return adapter.set_options
        cls = self.driver_classes.get(
            self.resolve_type(self.types.get(address, "")))
        if address == "Time":
            return ["Time"]
        if cls is None:
            return []
        return self._probe_options(cls, "set_options")

    def get_options(self, address: str) -> list[str]:
        adapter = self.connected(address)
        if adapter is not None:
            return adapter.get_options
        if address == "Time":
            return ["Elapsed", "Random"]
        cls = self.driver_classes.get(
            self.resolve_type(self.types.get(address, "")))
        if cls is None:
            return []
        return self._probe_options(cls, "get_options")

    @staticmethod
    def _probe_options(cls: type, attr: str) -> list[str]:
        """Read option lists from a driver class without opening hardware.

        Legacy drivers assign the lists in ``__init__`` after opening the
        instrument, so we parse the source instead of instantiating.
        """
        try:
            src = inspect.getsource(cls)
        except (OSError, TypeError):
            return []
        import ast as _ast
        try:
            tree = _ast.parse(src)
        except SyntaxError:
            return []
        for node in _ast.walk(tree):
            if isinstance(node, _ast.Assign):
                for tgt in node.targets:
                    if (isinstance(tgt, _ast.Attribute)
                            and tgt.attr == attr
                            and isinstance(node.value, _ast.List)):
                        out = []
                        for elt in node.value.elts:
                            if isinstance(elt, _ast.Constant) \
                                    and isinstance(elt.value, str):
                                out.append(elt.value)
                        return out
        return []

    def read_catalogue(self) -> list[str]:
        """All 'address.option' strings offered as readable parameters."""
        out: list[str] = []
        for addr in self.addresses:
            for opt in self.get_options(addr):
                out.append(f"{addr}.{opt}")
        return out


# ---------------------------------------------------------------------------
def probe_sweepable(adapter: DriverAdapter, parameter: str, target: float,
                    rate: float, timeout: float = 15.0, poll: float = 0.2,
                    log=None) -> dict:
    """Empirically test whether an instrument really ramps to a setpoint.

    Commands ``set(target, speed=rate)`` and watches the readback:

    * ``'ramps'``    — moved gradually and arrived (true sweepable device);
    * ``'jumps'``    — arrived essentially instantly with no intermediate
      readings (behaves like a stepwise source; the driver's 'sweepable'
      flag would make the engine assume a ramp that doesn't exist);
    * ``'stalled'``  — moved, then stopped short of the target;
    * ``'no_motion'``— never moved;
    * ``'unreadable'`` / ``'at_target'`` — the test could not run.

    The result dict carries the verdict, timing, samples, and whether the
    observed behaviour agrees with the driver's ``sweepable`` flag.
    """
    import time as _time
    log = log or (lambda _l: None)
    result = {"outcome": "", "t_reach": None, "samples": [],
              "flag_sweepable": adapter.sweepable(parameter),
              "agrees_with_flag": None, "final": None}
    if parameter not in adapter.get_options:
        result["outcome"] = "unreadable"
        log(f"'{parameter}' is not readable — cannot verify motion")
        return result
    try:
        v0 = float(adapter.get(parameter))
    except Exception as exc:                      # noqa: BLE001
        result["outcome"] = "unreadable"
        log(f"readback failed: {exc}")
        return result
    distance = target - v0
    eps = adapter.eps(parameter, fallback=max(abs(distance) * 0.02, 1e-12))
    eps = max(eps, abs(distance) * 0.02)
    if abs(distance) <= eps:
        result["outcome"] = "at_target"
        log(f"current value {v0:g} already equals the target — pick a "
            f"different target")
        return result
    sign = 1.0 if distance > 0 else -1.0
    expected_t = abs(distance) / rate if rate > 0 else float("inf")
    log(f"start {v0:g} → target {target:g} at rate {rate:g} "
        f"(expected ≈ {expected_t:.2f} s)")
    adapter.set(parameter, float(target), speed=rate)
    t0 = _time.perf_counter()
    intermediate = 0
    last_v = v0
    while True:
        _time.sleep(poll)
        t = _time.perf_counter() - t0
        try:
            v = float(adapter.get(parameter))
        except Exception as exc:                  # noqa: BLE001
            result["outcome"] = "unreadable"
            log(f"readback failed mid-test: {exc}")
            return result
        result["samples"].append((round(t, 3), v))
        log(f"  t={t:5.2f} s   {parameter} = {v:g}")
        if (v - v0) * sign > eps and (target - v) * sign > eps:
            intermediate += 1
        if (target - v) * sign <= eps:            # reached (or passed)
            result["t_reach"] = t
            result["final"] = v
            fast = t <= max(poll * 1.5, expected_t * 0.2)
            result["outcome"] = "jumps" if (fast and intermediate == 0) \
                else "ramps"
            break
        if t >= timeout:
            moved = abs(v - v0)
            result["final"] = v
            result["outcome"] = "no_motion" if moved <= max(eps, 1e-12) \
                else "stalled"
            break
        last_v = v
    result["agrees_with_flag"] = (result["outcome"] == "ramps") == \
        result["flag_sweepable"]
    verdicts = {
        "ramps": "device RAMPS to the setpoint — true sweepable behaviour",
        "jumps": "device sets the value INSTANTLY (no ramp observed)",
        "stalled": f"device STALLED at {result['final']:g} before the target",
        "no_motion": "device did NOT move",
    }
    log(verdicts.get(result["outcome"], result["outcome"]))
    if result["agrees_with_flag"] is False:
        log(f"⚠ driver flag says sweepable={result['flag_sweepable']} but "
            f"the instrument behaved otherwise — the engine would "
            f"{'assume a ramp that does not exist' if result['flag_sweepable'] else 'step a device that could ramp'}; "
            f"consider fixing the driver's 'sweepable' list or using "
            f"'Force stepwise'")
    return result
