"""On-demand driver installation.

Implements the "engine separated from drivers" flow: when the user assigns
an instrument that isn't present locally, the installer

1. **fetches the driver file** into ``resources/`` — from the local
   ``driver_bundle/`` folder if it's there, otherwise from the entry's URL
   or the catalog ``base_url`` (plain HTTPS to e.g. a raw-GitHub repo);
2. **reads the fetched source** and works out which Python packages it
   needs (AST import scan mapped through :data:`catalog.MODULE_TO_PIP`,
   combined with the catalog's declared requirements);
3. **pip-installs the missing ones into the current environment**
   (``sys.executable -m pip install …``), streaming pip's output live;
4. reloads the driver registry and applies the address→driver assignments.

Everything runs in a daemon thread and reports through a queue with
``("install_log", line)`` / ``("install_done", ok, summary)`` tuples, so the
GUI (setup wizard or Devices page) just tails the log. Failures are per-item
and never leave the registry in a broken state — a driver that couldn't be
fetched is simply reported and skipped.
"""

from __future__ import annotations

import ast
import importlib.util
import os
import queue
import shutil
import subprocess
import sys
import threading
import urllib.request
import zipfile
from dataclasses import dataclass, field

from .catalog import (CORE_MODULES, DriverCatalog, MODULE_TO_PIP, STDLIB_OK,
                      VENDOR_LOCAL)  # noqa: F401 - re-exported for tests
from .depsdb import DependencyDB

__all__ = ["InstallPlan", "DriverInstaller", "imports_of_source",
           "packages_for_modules", "missing_packages"]

# pip distribution -> import name used to test availability
_PIP_TO_IMPORT = {
    "pyvisa": "pyvisa", "pyvisa-py": "pyvisa_py", "pymeasure": "pymeasure",
    "pyserial": "serial", "nidaqmx": "nidaqmx", "msl-equipment": "msl",
    "libximc": "libximc", "MultiPyVu": "MultiPyVu",
    "rohdeschwarz": "rohdeschwarz", "TeledyneLeCroyPy": "TeledyneLeCroyPy",
    "imageio": "imageio",
}


def imports_of_source(source: str) -> set[str]:
    """Top-level module names imported by a driver source."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                out.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module \
                and node.level == 0:
            out.add(node.module.split(".")[0])
    return out


def packages_for_modules(modules: set[str]) -> tuple[list[str], list[str]]:
    """(pip packages, vendor notes) implied by a set of import names."""
    pkgs: list[str] = []
    notes: list[str] = []
    for mod in sorted(modules):
        if mod in STDLIB_OK or mod in CORE_MODULES or mod in sys.builtin_module_names:
            continue
        if mod in MODULE_TO_PIP:
            for pkg in MODULE_TO_PIP[mod]:
                if pkg not in pkgs:
                    pkgs.append(pkg)
        elif mod in VENDOR_LOCAL:
            notes.append(VENDOR_LOCAL[mod])
        elif importlib.util.find_spec(mod) is None:
            notes.append(f"module '{mod}' is not on the known package list "
                         f"and is not importable — install it manually")
    return pkgs, notes


def missing_packages(packages: list[str]) -> list[str]:
    out = []
    for pkg in packages:
        import_name = _PIP_TO_IMPORT.get(pkg, pkg.replace("-", "_"))
        try:
            found = importlib.util.find_spec(import_name) is not None
        except (ModuleNotFoundError, ValueError):
            found = False
        if not found:
            out.append(pkg)
    return out


@dataclass
class InstallPlan:
    drivers: list[str] = field(default_factory=list)      # names requested
    to_fetch: list[str] = field(default_factory=list)     # not in resources
    unavailable: list[str] = field(default_factory=list)  # no source found
    pip_install: list[str] = field(default_factory=list)  # missing packages
    extract_packages: list[str] = field(default_factory=list)  # from repo
    vendor_notes: list[str] = field(default_factory=list)

    def summary(self) -> str:
        parts = []
        if self.to_fetch:
            parts.append(f"{len(self.to_fetch)} driver file(s) to fetch: "
                         + ", ".join(self.to_fetch))
        if self.pip_install:
            parts.append("Python packages to install: "
                         + ", ".join(self.pip_install))
        if self.extract_packages:
            parts.append("support packages from the repository: "
                         + ", ".join(self.extract_packages))
        if self.unavailable:
            parts.append("no source found for: "
                         + ", ".join(self.unavailable))
        if self.vendor_notes:
            parts.append("manual prerequisites: "
                         + "; ".join(sorted(set(self.vendor_notes))))
        return "\n".join(parts) if parts else \
            "Everything needed is already installed."


class DriverInstaller:

    def __init__(self, registry, catalog: DriverCatalog,
                 out_queue: "queue.Queue"):
        self.registry = registry
        self.catalog = catalog
        self.deps = DependencyDB(catalog.core_dir)
        self.q = out_queue
        self.resources = registry.resources_dir
        self._thread: threading.Thread | None = None

    # ---------------- planning ----------------------------------------
    def plan(self, driver_names: list[str]) -> InstallPlan:
        plan = InstallPlan(drivers=list(driver_names))
        packages: list[str] = []
        extract: list[str] = []
        for name in driver_names:
            if not name or name == "Time":
                continue
            entry = self.catalog.get(name)
            local = os.path.join(self.resources, f"{name}.py")
            source_text = None
            if os.path.exists(local):
                source_text = self._read(local)
            else:
                candidates = self.catalog.source_candidates(name)
                if not candidates:
                    plan.unavailable.append(name)
                else:
                    plan.to_fetch.append(name)
                    kind, spec = candidates[0]
                    if kind == "file":                    # bundle file
                        source_text = self._read(spec)
                    elif kind == "zip":
                        source_text = self._read_zip_member(*spec)
            if entry:
                for pkg in entry.requires:
                    if pkg not in packages:
                        packages.append(pkg)
                if entry.vendor_note:
                    plan.vendor_notes.append(entry.vendor_note)
            if source_text:
                mods = imports_of_source(source_text)
                for mod in sorted(mods):
                    if mod in STDLIB_OK or mod in CORE_MODULES                             or mod in sys.builtin_module_names:
                        continue
                    if importlib.util.find_spec(mod) is not None                             and not os.path.isdir(
                                os.path.join(self.resources, mod)):
                        continue
                    if mod == "devices":
                        continue          # repo-layout alias, provided by us
                    if self.catalog.has_repo_package(mod):
                        if mod not in extract and not os.path.isdir(
                                os.path.join(self.resources, mod)):
                            extract.append(mod)
                        continue
                    mapped = self.deps.packages_for(mod)
                    if mapped is not None:
                        for pkg in mapped:
                            if pkg not in packages:
                                packages.append(pkg)
                    elif mod in VENDOR_LOCAL:
                        plan.vendor_notes.append(VENDOR_LOCAL[mod])
                    else:
                        plan.vendor_notes.append(
                            f"module '{mod}': no known pip package — the "
                            f"installer will probe candidates and record "
                            f"what works in config/dependency_map.json")
                # non-import references (DLL folders like ANC350_drivers)
                for pkg_dir in sorted(self.catalog.repo_packages):
                    if pkg_dir in source_text and pkg_dir not in extract                             and not os.path.isdir(
                                os.path.join(self.resources, pkg_dir)):
                        extract.append(pkg_dir)
        # extracted repo packages satisfy their matching pip requirement
        extracted_imports = set(extract)
        packages = [p for p in packages
                    if _PIP_TO_IMPORT.get(p, p.replace("-", "_"))
                    not in extracted_imports]
        plan.extract_packages = extract
        plan.pip_install = missing_packages(packages)
        return plan

    @staticmethod
    def _read_zip_member(zip_path: str, member: str) -> str:
        try:
            with zipfile.ZipFile(zip_path) as z:
                return z.read(member).decode("utf-8", errors="replace")
        except (OSError, KeyError, zipfile.BadZipFile):
            return ""

    @staticmethod
    def _read(path: str) -> str:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                return fh.read()
        except OSError:
            return ""

    # ---------------- installing --------------------------------------
    @property
    def busy(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def install_async(self, driver_names: list[str],
                      assignments: dict[str, str] | None = None) -> None:
        """Fetch drivers + pip-install dependencies in the background.

        ``assignments`` (address -> driver name) are applied after a
        successful install so the Devices page / wizard can hand over the
        whole confirmation in one call.
        """
        if self.busy:
            self._log("an installation is already running")
            return
        self._thread = threading.Thread(
            target=self._work, args=(list(driver_names), assignments or {}),
            daemon=True, name="unisweep-installer")
        self._thread.start()

    # -----------------------------------------------------------------
    def _log(self, line: str) -> None:
        try:
            self.q.put_nowait(("install_log", line))
        except queue.Full:
            pass

    def _work(self, driver_names: list[str],
              assignments: dict[str, str]) -> None:
        ok = True
        failed: list[str] = []
        plan = self.plan(driver_names)
        self._log("Install plan:\n" + plan.summary())
        os.makedirs(self.resources, exist_ok=True)

        for name in plan.to_fetch:
            if not self._fetch_driver(name):
                failed.append(name)
                ok = False
        for name in plan.unavailable:
            self._log(f"✗ {name}: no bundle file and no download URL "
                      f"(set base_url in config/driver_catalog.json or "
                      f"drop the file into driver_bundle/)")
            failed.append(name)
            ok = False

        # dependencies are re-planned from what actually landed on disk
        final_plan = self.plan([n for n in driver_names
                                if n not in failed])
        for package in final_plan.extract_packages:
            if not self.catalog.extract_package(package, self.resources,
                                                log=self._log):
                ok = False
        if final_plan.pip_install:
            if not self._pip_install(final_plan.pip_install):
                ok = False
        for note in sorted(set(final_plan.vendor_notes)):
            self._log(f"note: {note}")

        if not self._verify_and_learn_imports(
                [n for n in driver_names if n not in failed]):
            ok = False

        self.registry.reload_drivers()
        for name in driver_names:
            err = self.registry.import_error(name)
            if err:
                self._log(f"✗ {name} still fails to import: {err}")
                ok = False
        applied = []
        for address, driver in assignments.items():
            if driver in failed:
                continue
            self.registry.assign(address, driver)
            applied.append(f"{address} → {driver}")
        if applied:
            self._log("Assigned: " + ", ".join(applied))
        summary = "Installation finished" if ok else \
            "Installation finished with errors: " + ", ".join(failed)
        self._log(summary)
        try:
            self.q.put_nowait(("install_done", ok, summary))
        except queue.Full:
            pass

    # ---------------- dependency verification -------------------------
    def _driver_imports(self, name: str) -> set[str]:
        src = self._read(os.path.join(self.resources, f"{name}.py"))
        return imports_of_source(src) if src else set()

    def _verify_and_learn_imports(self, driver_names: list[str]) -> bool:
        """After installing, check that every import of every driver
        actually resolves; probe pip candidates for unknown ones and record
        the working recipe permanently (the KDC101/'msl' class of failures
        becomes visible and self-healing instead of silent)."""
        importlib.invalidate_caches()
        ok = True
        for name in driver_names:
            if not name or name == "Time":
                continue
            for mod in sorted(self._driver_imports(name)):
                if mod in STDLIB_OK or mod in CORE_MODULES \
                        or mod in sys.builtin_module_names \
                        or mod == "devices":
                    continue
                if self._find(mod) or os.path.isdir(
                        os.path.join(self.resources, mod)):
                    continue
                if not self._resolve_import(name, mod):
                    ok = False
        return ok

    @staticmethod
    def _find(mod: str) -> bool:
        try:
            return importlib.util.find_spec(mod) is not None
        except (ModuleNotFoundError, ValueError):
            return False

    def _resolve_import(self, driver: str, mod: str) -> bool:
        recorded = self.deps.packages_for(mod)
        tried: list[list[str]] = []
        if recorded:
            tried.append(recorded)
        if self.catalog.has_repo_package(mod):
            if self.catalog.extract_package(mod, self.resources,
                                            log=self._log):
                importlib.invalidate_caches()
                if self._find(mod):
                    return True
        for cand in self.deps.candidates(mod):
            if cand not in tried:
                tried.append(cand)
        for packages in tried:
            self._log(f"{driver}: import '{mod}' unresolved — trying "
                      f"pip package(s) {', '.join(packages)}")
            if not self._pip_install(packages):
                continue
            importlib.invalidate_caches()
            if self._find(mod):
                if self.deps.packages_for(mod) != packages:
                    self.deps.learn(mod, packages)
                    self._log(f"recorded: import '{mod}' ← pip "
                              f"{', '.join(packages)} "
                              f"(config/dependency_map.json)")
                return True
        self._log(f"✗ {driver}: could not resolve import '{mod}' — add the "
                  f"correct pip package to config/dependency_map.json")
        return False

    def _fetch_driver(self, name: str) -> bool:
        target = os.path.join(self.resources, f"{name}.py")
        for kind, spec in self.catalog.source_candidates(name):
            try:
                if kind == "file":
                    shutil.copyfile(spec, target)
                    self._log(f"✓ {name}.py copied from bundle")
                    return True
                if kind == "zip":
                    text = self._read_zip_member(*spec)
                    if not text:
                        continue
                    ast.parse(text)
                    with open(target, "w", encoding="utf-8") as fh:
                        fh.write(text)
                    self._log(f"✓ {name}.py extracted from the cached "
                              f"repository snapshot")
                    return True
                self._log(f"downloading {name}.py from {spec} …")
                req = urllib.request.Request(
                    spec, headers={"User-Agent": "unisweep"})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = resp.read()
                text = data.decode("utf-8", errors="replace")
                ast.parse(text)          # refuse to install non-Python
                with open(target, "w", encoding="utf-8") as fh:
                    fh.write(text)
                self._log(f"✓ {name}.py downloaded")
                return True
            except SyntaxError:
                self._log(f"✗ {name}: fetched file is not valid Python")
            except Exception as exc:                  # noqa: BLE001
                self._log(f"✗ {name}: {exc}")
        return False

    def _pip_install(self, packages: list[str]) -> bool:
        # Plain install first (correct inside venvs / on Windows); if the
        # interpreter is an externally-managed system Python (PEP 668,
        # e.g. Ubuntu 24), retry with --break-system-packages.
        code, output = self._run_pip(["install", *packages])
        if code != 0 and "externally-managed" in output:
            self._log("environment is externally managed (PEP 668) — "
                      "retrying with --break-system-packages")
            code, _ = self._run_pip(["install", "--break-system-packages",
                                     *packages])
        if code != 0:
            self._log(f"✗ pip exited with code {code}")
            return False
        self._log("✓ Python packages installed")
        return True

    def _run_pip(self, args: list[str]) -> tuple[int, str]:
        self._log("pip " + " ".join(args))
        cmd = [sys.executable, "-m", "pip", *args]
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True,
                                    bufsize=1)
        except OSError as exc:
            self._log(f"✗ could not run pip: {exc}")
            return 1, str(exc)
        assert proc.stdout is not None
        collected: list[str] = []
        for line in proc.stdout:
            line = line.rstrip()
            if line:
                collected.append(line)
                self._log(f"  {line}")
        return proc.wait(), "\n".join(collected)
