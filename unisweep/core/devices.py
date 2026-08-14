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
           "probe_sweepable"]


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
    """Uniform facade over a legacy driver instance."""

    def __init__(self, address: str, instance):
        self.address = address
        self.raw = instance
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

    def set(self, parameter: str, value: float,
            speed: Optional[float] = None) -> None:
        setter = getattr(self.raw, f"set_{parameter}")
        if speed is not None:
            try:
                params = inspect.signature(setter).parameters
            except (TypeError, ValueError):
                params = {}
            if "speed" in params:
                setter(value=value, speed=speed)
                return
        setter(value=value)

    def pause(self) -> None:
        fn = getattr(self.raw, "pause", None)
        if callable(fn):
            fn()

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
                f"unisweep_drivers.{mod_name}", path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)          # type: ignore[union-attr]
            cls = getattr(module, mod_name, None)
            if inspect.isclass(cls):
                classes[mod_name] = cls
            else:
                errors[mod_name] = (f"file imported but defines no class "
                                    f"'{mod_name}'")
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

    def __init__(self, core_dir: str):
        self.core_dir = core_dir
        self.resources_dir = os.path.join(core_dir, "resources")
        self.config_path = os.path.join(core_dir, "config",
                                        "address_dictionary.txt")
        self.driver_classes, self.import_errors = \
            _import_driver_classes(self.resources_dir)
        self.types: dict[str, str] = {}       # address -> class name
        self.addresses: list[str] = ["Time"]
        self._adapters: dict[str, DriverAdapter] = {}
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
            self._adapters.pop(address, None)   # force reconnect with new type
        self.save_types()

    def add_address(self, address: str) -> None:
        if address and address not in self.addresses:
            self.addresses.append(address)

    def unassign(self, address: str) -> None:
        if address in self.types and address != "Time":
            del self.types[address]
        with self._lock:
            self._adapters.pop(address, None)
        self.save_types()

    # ---- driver installation support ------------------------------------
    def is_installed(self, class_name: str) -> bool:
        """Is the driver file present and importable?"""
        if class_name == "Time":
            return True
        return class_name in self.driver_classes

    def import_error(self, class_name: str) -> str:
        """The captured import failure of a present-but-broken driver."""
        return self.import_errors.get(class_name, "")

    def has_driver_file(self, class_name: str) -> bool:
        return os.path.exists(os.path.join(self.resources_dir,
                                           f"{class_name}.py"))

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
        with self._lock:
            adapter = self._adapters.get(address)
            if adapter is not None:
                return adapter
            if address == "Time":
                adapter = DriverAdapter("Time", VirtualTime())
            else:
                class_name = self.types.get(address)
                if not class_name:
                    raise RuntimeError(
                        f"no driver type assigned to '{address}' "
                        f"(Devices page)")
                cls = self.driver_classes.get(class_name)
                if cls is None:
                    raise RuntimeError(
                        f"driver class '{class_name}' not found in resources")
                adapter = DriverAdapter(address, cls(adress=address))
            self._adapters[address] = adapter
            return adapter

    def connected(self, address: str) -> Optional[DriverAdapter]:
        with self._lock:
            return self._adapters.get(address)

    def disconnect_all(self) -> None:
        with self._lock:
            for a in self._adapters.values():
                a.clear()
            self._adapters.clear()

    # ---- catalogue helpers ----------------------------------------------
    def set_options(self, address: str) -> list[str]:
        """Parameter list without connecting, when the class is known."""
        adapter = self.connected(address)
        if adapter is not None:
            return adapter.set_options
        cls = self.driver_classes.get(self.types.get(address, ""))
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
        cls = self.driver_classes.get(self.types.get(address, ""))
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
