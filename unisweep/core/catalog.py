"""Driver catalog.

The engine ships **separated from the instrument drivers**: the core runs
with only the virtual ``Time`` device, and every real driver is an entry in
this catalog that can be installed on demand — its ``.py`` file fetched into
``resources/`` and its Python dependencies pip-installed into the current
environment (see :mod:`installer`).

Catalog entries come from three layers, merged in this order:

1. the **built-in catalog** below — every driver of the legacy Unisweep
   distribution with its instrument name and pip requirements (derived from
   the actual imports of the driver sources);
2. ``config/driver_catalog.json`` — user-editable additions/overrides,
   including ``base_url`` for a remote driver repository;
3. whatever ``.py`` files already sit in ``resources/`` or in a local
   ``driver_bundle/`` folder (a plain folder of driver files works as an
   offline repository).

The pip mapping is import-name → package-name, so the installer can both
*check* availability (``importlib.util.find_spec``) and *install* the right
distribution.
"""

from __future__ import annotations

import io
import json
import os
import threading
import time
import urllib.request
import zipfile
from dataclasses import dataclass, field, asdict
from typing import Callable, Optional

__all__ = ["DriverEntry", "DriverCatalog", "MODULE_TO_PIP", "STDLIB_OK",
           "CORE_MODULES", "VENDOR_LOCAL", "DEFAULT_REPO", "DEFAULT_BRANCH",
           "DEFAULT_REPO_FOLDER"]

# The reference driver repository. New driver files pushed to it are
# discovered automatically (GitHub API first, repository zipball as an
# API-free fallback) and appended to the catalog; with no connection the
# catalog silently keeps whatever is installed / cached locally.
DEFAULT_REPO = "DbIXAHUEOKEAHA/unisweep"
DEFAULT_BRANCH = "main"
DEFAULT_REPO_FOLDER = "devices"

# import name -> pip distribution(s)
MODULE_TO_PIP: dict[str, tuple[str, ...]] = {
    "pyvisa": ("pyvisa", "pyvisa-py"),      # pyvisa-py = pure-python backend
    "pymeasure": ("pymeasure",),
    "serial": ("pyserial",),
    "nidaqmx": ("nidaqmx",),
    "msl": ("msl-equipment",),
    "libximc": ("libximc",),
    "MultiPyVu": ("MultiPyVu",),
    "rohdeschwarz": ("rohdeschwarz",),
    "TeledyneLeCroyPy": ("TeledyneLeCroyPy",),
    "imageio": ("imageio",),
    "lakeshore": ("lakeshore",),        # Lake Shore M81 and friends
}

# import names satisfied by the core install (never re-installed per driver)
CORE_MODULES = {"numpy", "scipy", "pandas", "matplotlib"}

# stdlib names commonly seen in the driver sources
STDLIB_OK = {
    "os", "sys", "time", "re", "glob", "ctypes", "enum", "copy", "typing",
    "pathlib", "platform", "warnings", "threading", "struct", "socket",
    "math", "json", "csv", "datetime", "functools", "itertools",
}

# import names that are vendor-local Python packages (not on PyPI)
VENDOR_LOCAL = {
    "ASC500_Python_Control": "attocube ASC500 Python package (from the "
                             "vendor SDK; place it next to resources/)",
    "atto_device": "attocube 'atto_device' Python package (from the vendor "
                   "software; place it next to resources/)",
}


@dataclass
class DriverEntry:
    name: str                              # class/file name (Name.py)
    instrument: str = ""                   # human-readable instrument
    requires: tuple[str, ...] = ()         # pip distributions
    vendor_note: str = ""                  # non-pip prerequisites (DLL/SDK)
    url: Optional[str] = None              # explicit download URL
    files: tuple[str, ...] = ()            # extra files besides <name>.py

    @property
    def filename(self) -> str:
        return f"{self.name}.py"


def _e(name, instrument, requires=(), vendor_note=""):
    return DriverEntry(name=name, instrument=instrument,
                       requires=tuple(requires), vendor_note=vendor_note)


_VISA = ("pyvisa", "pyvisa-py")

BUILTIN_CATALOG: dict[str, DriverEntry] = {e.name: e for e in [
    _e("Time", "Virtual time device (built into the core)"),
    # --- source-measure / meters ---------------------------------------
    _e("Keithley2400", "Keithley 2400 SourceMeter (SMU)", _VISA),
    _e("keithley_series_2600b", "Keithley 2600B-series SourceMeter",
       _VISA + ("pymeasure",)),
    _e("keithley2182", "Keithley 2182/2182A nanovoltmeter", _VISA),
    _e("keithley2000", "Keithley 2000 multimeter", ("pymeasure",) + _VISA),
    _e("sim900", "SRS SIM900 mainframe", _VISA),
    _e("sim928", "SRS SIM928 isolated voltage source", _VISA),
    _e("sr580", "SRS current preamplifier", _VISA),
    _e("SR830", "SRS SR830 lock-in amplifier", ("pymeasure",) + _VISA),
    _e("sr860", "SRS SR860 lock-in amplifier", ("pymeasure",) + _VISA),
    _e("AFG1000", "Tektronix AFG1000 function generator", _VISA),
    _e("QDAQ2", "QDAQ data acquisition unit", _VISA),
    _e("NI_DAQ", "National Instruments DAQ (nidaqmx)", ("nidaqmx",),
       "NI-DAQmx runtime must be installed from National Instruments"),
    _e("Waverunner9000", "Teledyne LeCroy WaveRunner 9000 oscilloscope",
       ("TeledyneLeCroyPy",)),
    _e("Vna", "Rohde & Schwarz vector network analyzer", ("rohdeschwarz",)),
    # --- temperature / cryogenics --------------------------------------
    _e("LakeShore336", "Lake Shore 336 temperature controller", _VISA),
    _e("mercuryITC", "Oxford Instruments MercuryiTC temperature controller",
       _VISA),
    _e("heliox_mercuryITC", "Oxford MercuryiTC (Heliox insert)", _VISA),
    _e("mercuryIPS", "Oxford Instruments MercuryiPS magnet supply", _VISA),
    _e("ami430", "AMI Model 430 magnet power supply programmer", _VISA),
    _e("opticool", "Quantum Design OptiCool", ("MultiPyVu",)),
    _e("TC300", "Thorlabs TC300 temperature controller", _VISA),
    _e("AttoDry800", "attocube attoDRY800 cryostat", (),
       "attocube attoDRY DLL from the vendor software"),
    _e("AttoDry2100", "attocube attoDRY2100 cryostat", (),
       "attocube attoDRY DLL from the vendor software"),
    _e("AttoDry2100_vector", "attocube attoDRY2100 (vector magnet)", (),
       VENDOR_LOCAL["atto_device"]),
    _e("ADry2100", "attocube attoDRY2100 (atto_device interface)", (),
       VENDOR_LOCAL["atto_device"]),
    # --- positioners / stages ------------------------------------------
    _e("ANC300", "attocube ANC300 positioner controller",
       ("pymeasure",) + _VISA),
    _e("ANC350", "attocube ANC350 positioner controller", (),
       "attocube ANC350 DLL from the vendor software"),
    _e("amc", "attocube AMC motion controller", (),
       VENDOR_LOCAL["atto_device"]),
    _e("asc500", "attocube ASC500 SPM controller", (),
       VENDOR_LOCAL["ASC500_Python_Control"]),
    _e("KDC101", "Thorlabs KDC101 DC servo motor controller",
       ("msl-equipment",),
       "Thorlabs Kinesis software (DLLs) from Thorlabs"),
    _e("KSC101", "Thorlabs KSC101 solenoid controller", ("pyserial",)),
    _e("RotStage", "Standa rotation stage (libximc)", ("libximc",)),
    _e("XStage", "Standa X stage (libximc)", ("libximc", "pyserial")),
    _e("YStage", "Standa Y stage (libximc)", ("libximc",)),
    _e("ZStage", "Standa Z stage (libximc)", ("libximc",)),
    _e("_8MTF_75LS05", "Standa 8MTF-75LS05 motorized stage",
       ("libximc", "pyserial")),
    _e("_8MVT100_25_1", "Standa 8MVT100-25-1 vertical stage",
       ("libximc", "pyserial")),
    _e("slider", "Positioner slider", _VISA),
    _e("Avaspec", "Avantes AvaSpec spectrometer", ("msl-equipment",),
       "AvaSpec DLL (AS5216/avaspecx64) from Avantes"),
]}


class DriverCatalog:
    """Merged view: built-in + config/driver_catalog.json + local files."""

    def __init__(self, core_dir: str):
        self.core_dir = core_dir
        self.config_path = os.path.join(core_dir, "config",
                                        "driver_catalog.json")
        self.index_path = os.path.join(core_dir, "config", "repo_index.json")
        self.snapshot_file = os.path.join(core_dir, "config",
                                          "repo_snapshot.zip")
        self.base_url: Optional[str] = None
        self.bundle_dir = os.path.join(core_dir, "driver_bundle")
        self.repo: str = DEFAULT_REPO
        self.branch: str = DEFAULT_BRANCH
        self.repo_folder: str = DEFAULT_REPO_FOLDER
        self.repo_drivers: dict[str, Optional[str]] = {}   # name -> url
        self.repo_packages: set[str] = set()
        self._lock = threading.Lock()
        self.entries: dict[str, DriverEntry] = {
            k: DriverEntry(**asdict(v)) for k, v in BUILTIN_CATALOG.items()}
        self._load_user_catalog()
        self._load_repo_index()
        self._absorb_local_files()

    # -----------------------------------------------------------------
    def _load_user_catalog(self) -> None:
        try:
            with open(self.config_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError):
            return
        self.base_url = data.get("base_url") or None
        self.repo = data.get("repo") or self.repo
        self.branch = data.get("branch") or self.branch
        self.repo_folder = data.get("repo_folder") or self.repo_folder
        bundle = data.get("bundle_dir")
        if bundle:
            self.bundle_dir = bundle if os.path.isabs(bundle) \
                else os.path.join(self.core_dir, bundle)
        for item in data.get("drivers", []):
            try:
                name = item["name"]
            except (TypeError, KeyError):
                continue
            base = self.entries.get(name)
            merged = asdict(base) if base else {"name": name}
            merged.update({k: v for k, v in item.items()
                           if k in DriverEntry.__dataclass_fields__})
            merged["requires"] = tuple(merged.get("requires", ()))
            merged["files"] = tuple(merged.get("files", ()))
            self.entries[name] = DriverEntry(**merged)

    def save_user_config(self) -> None:
        data = {"repo": self.repo, "branch": self.branch,
                "repo_folder": self.repo_folder,
                "base_url": self.base_url,
                "bundle_dir": os.path.relpath(self.bundle_dir, self.core_dir)
                if self.bundle_dir.startswith(self.core_dir)
                else self.bundle_dir,
                "drivers": []}
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)

    def _absorb_local_files(self) -> None:
        """Any .py in resources/ or the bundle becomes a catalog entry."""
        for directory in (os.path.join(self.core_dir, "resources"),
                          self.bundle_dir):
            if not os.path.isdir(directory):
                continue
            for fname in os.listdir(directory):
                if fname.endswith(".py"):
                    name = fname[:-3]
                    if name not in self.entries:
                        self.entries[name] = DriverEntry(
                            name=name, instrument=f"{name} (local driver)")

    # -----------------------------------------------------------------
    def names(self) -> list[str]:
        return sorted(self.entries, key=str.lower)

    def get(self, name: str) -> Optional[DriverEntry]:
        return self.entries.get(name)

    def label(self, name: str, installed: bool) -> str:
        entry = self.entries.get(name)
        instrument = entry.instrument if entry else ""
        mark = "" if installed else "  ⬇"
        return f"{name}{mark}" + (f" — {instrument}" if instrument else "")

    # -----------------------------------------------------------------
    def source_candidates(self, name: str) -> list[tuple[str, object]]:
        """Where the driver file may be fetched from, in priority order.

        Typed candidates: ``("file", path)`` — copy a local file;
        ``("zip", (snapshot_path, member))`` — extract from the cached
        repository snapshot (works fully offline);
        ``("url", url)`` — plain HTTPS download.
        """
        entry = self.entries.get(name)
        out: list[tuple[str, object]] = []
        bundle = os.path.join(self.bundle_dir, f"{name}.py")
        if os.path.exists(bundle):
            out.append(("file", bundle))
        member = self.zip_member_for(name)
        if member:
            out.append(("zip", (self.snapshot_file, member)))
        if entry and entry.url:
            out.append(("url", entry.url))
        if name in self.repo_drivers and self.repo_drivers[name]:
            out.append(("url", self.repo_drivers[name]))
        if self.base_url:
            out.append(("url", self.base_url.rstrip("/") + f"/{name}.py"))
        if self.repo:
            raw = (f"https://raw.githubusercontent.com/{self.repo}/{{br}}/"
                   f"{self.repo_folder}/{name}.py")
            for br in dict.fromkeys([self.branch, "main", "master"]):
                url = raw.format(br=br)
                if ("url", url) not in out:
                    out.append(("url", url))
        return out

    # ---------------- remote repository ------------------------------
    def _load_repo_index(self) -> None:
        try:
            with open(self.index_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError):
            return
        self.repo_drivers = dict(data.get("drivers", {}))
        self.repo_packages = set(data.get("packages", []))
        self._merge_repo_drivers(save=False)

    def _save_repo_index(self) -> None:
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        with open(self.index_path, "w", encoding="utf-8") as fh:
            json.dump({"repo": self.repo, "branch": self.branch,
                       "fetched": time.time(),
                       "drivers": self.repo_drivers,
                       "packages": sorted(self.repo_packages)}, fh, indent=2)

    def _merge_repo_drivers(self, save: bool = True) -> list[str]:
        added = []
        for name, url in self.repo_drivers.items():
            if name in ("__init__",):
                continue
            entry = self.entries.get(name)
            if entry is None:
                self.entries[name] = DriverEntry(
                    name=name,
                    instrument=f"from {self.repo.split('/')[-1]} repository",
                    url=url)
                added.append(name)
            elif url and not entry.url:
                entry.url = url
        if save:
            self._save_repo_index()
        return added

    def has_repo_package(self, name: str) -> bool:
        return name in self.repo_packages

    def refresh_remote(self, timeout: float = 15.0,
                       allow_zip: bool = True,
                       log: Optional[Callable[[str], None]] = None
                       ) -> tuple[list[str], str, bool]:
        """Discover drivers on GitHub. Returns (new names, message, ok).

        Strategy: the tiny GitHub contents API first; if it fails (rate
        limit / offline) fall back to the repository zipball via codeload —
        which is also cached as ``config/repo_snapshot.zip`` and doubles as
        an offline driver repository. Never raises: with no connection the
        cached/local catalog stays in effect.
        """
        log = log or (lambda _line: None)
        with self._lock:
            try:
                drivers, packages = self._api_listing(timeout)
                source = "GitHub API"
            except Exception as api_exc:          # noqa: BLE001
                log(f"GitHub API unavailable ({api_exc}); "
                    + ("trying repository archive…" if allow_zip
                       else "using cached catalog"))
                if not allow_zip:
                    return [], f"offline — using local catalog ({api_exc})",                         False
                try:
                    drivers, packages = self._zip_refresh(timeout, log)
                    source = "repository archive"
                except Exception as zip_exc:      # noqa: BLE001
                    return [], ("offline — using local catalog "
                                f"({zip_exc})"), False
            self.repo_drivers.update(drivers)
            self.repo_packages |= packages
            added = self._merge_repo_drivers()
            msg = (f"catalog updated from {source}: "
                   f"{len(drivers)} drivers in repo"
                   + (f", {len(added)} new: " + ", ".join(sorted(added))
                      if added else ", no new ones"))
            log(msg)
            return added, msg, True

    def refresh_remote_async(self, done: Callable, **kw) -> None:
        def work():
            done(*self.refresh_remote(**kw))
        threading.Thread(target=work, daemon=True,
                         name="unisweep-catalog").start()

    # ---- strategy 1: contents API ------------------------------------
    def _api_listing(self, timeout: float):
        url = (f"https://api.github.com/repos/{self.repo}/contents/"
               f"{self.repo_folder}?ref={self.branch}")
        req = urllib.request.Request(url, headers={
            "User-Agent": "unisweep",
            "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            items = json.load(resp)
        if not isinstance(items, list):
            raise RuntimeError(items.get("message", "unexpected response")
                               if isinstance(items, dict) else "bad response")
        drivers: dict[str, Optional[str]] = {}
        packages: set[str] = set()
        for item in items:
            name = item.get("name", "")
            if item.get("type") == "file" and name.endswith(".py")                     and name != "__init__.py":
                drivers[name[:-3]] = item.get("download_url")
            elif item.get("type") == "dir":
                packages.add(name)
        return drivers, packages

    # ---- strategy 2: repository zipball ------------------------------
    def _zip_refresh(self, timeout: float, log) -> tuple[dict, set]:
        url = (f"https://codeload.github.com/{self.repo}/zip/refs/heads/"
               f"{self.branch}")
        log(f"downloading repository archive {url} …")
        req = urllib.request.Request(url, headers={"User-Agent": "unisweep"})
        with urllib.request.urlopen(req, timeout=max(timeout, 60)) as resp:
            data = resp.read()
        zipfile.ZipFile(io.BytesIO(data)).testzip()
        os.makedirs(os.path.dirname(self.snapshot_file), exist_ok=True)
        tmp = self.snapshot_file + ".tmp"
        with open(tmp, "wb") as fh:
            fh.write(data)
        os.replace(tmp, self.snapshot_file)
        log(f"repository snapshot cached "
            f"({len(data) // 1024 // 1024} MB) — installs now work offline")
        return self._parse_snapshot()

    def _parse_snapshot(self) -> tuple[dict, set]:
        drivers: dict[str, Optional[str]] = {}
        packages: set[str] = set()
        raw = (f"https://raw.githubusercontent.com/{self.repo}/"
               f"{self.branch}/{self.repo_folder}/")
        with zipfile.ZipFile(self.snapshot_file) as z:
            for member in z.namelist():
                parts = member.split("/")
                if len(parts) < 3 or parts[1] != self.repo_folder:
                    continue
                if len(parts) == 3 and parts[2].endswith(".py")                         and parts[2] != "__init__.py":
                    drivers[parts[2][:-3]] = raw + parts[2]
                elif len(parts) > 3 and parts[2]                         and parts[2] != "__pycache__":
                    packages.add(parts[2])
        return drivers, packages

    # ---- snapshot helpers --------------------------------------------
    def snapshot(self) -> Optional[str]:
        return self.snapshot_file if os.path.exists(self.snapshot_file)             else None

    def ensure_snapshot(self, timeout: float = 60.0,
                        log: Optional[Callable[[str], None]] = None
                        ) -> Optional[str]:
        if self.snapshot():
            return self.snapshot_file
        try:
            self._zip_refresh(timeout, log or (lambda _l: None))
            return self.snapshot_file
        except Exception:                          # noqa: BLE001
            return None

    def zip_member_for(self, name: str) -> Optional[str]:
        snap = self.snapshot()
        if not snap:
            return None
        try:
            with zipfile.ZipFile(snap) as z:
                for member in z.namelist():
                    parts = member.split("/")
                    if len(parts) == 3 and parts[1] == self.repo_folder                             and parts[2] == f"{name}.py":
                        return member
        except (OSError, zipfile.BadZipFile):
            return None
        return None

    def extract_package(self, package: str, dest_dir: str,
                        log: Optional[Callable[[str], None]] = None) -> bool:
        """Extract a vendored support package (atto_device, libximc, DLL
        folders, …) from the repository snapshot into resources/."""
        log = log or (lambda _l: None)
        snap = self.ensure_snapshot(log=log)
        if not snap:
            log(f"✗ {package}: no repository snapshot and no connection")
            return False
        prefix = None
        try:
            with zipfile.ZipFile(snap) as z:
                for member in z.namelist():
                    parts = member.split("/")
                    if len(parts) > 3 and parts[1] == self.repo_folder                             and parts[2] == package:
                        prefix = "/".join(parts[:3]) + "/"
                        break
                if prefix is None:
                    log(f"✗ {package}: not found in the repository")
                    return False
                count = 0
                for member in z.namelist():
                    if not member.startswith(prefix)                             or member.endswith("/")                             or "__pycache__" in member:
                        continue
                    rel = member[len(prefix) - len(package) - 1:]
                    target = os.path.join(dest_dir, *rel.split("/"))
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    with z.open(member) as src, open(target, "wb") as out:
                        out.write(src.read())
                    count += 1
        except (OSError, zipfile.BadZipFile) as exc:
            log(f"✗ {package}: {exc}")
            return False
        log(f"✓ support package '{package}' extracted ({count} files)")
        return True
