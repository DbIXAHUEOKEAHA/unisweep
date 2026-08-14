"""Catalog + installer tests (offline: bundle and file:// sources only)."""

import os
import queue
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unisweep.core.catalog import DriverCatalog
from unisweep.core.devices import DeviceRegistry
from unisweep.core.installer import (DriverInstaller, imports_of_source,
                                     missing_packages, packages_for_modules)

MOCK_DRIVER = '''
import time
import numpy as np
import definitely_absent_mod_xyz

class BundleDev:
    def __init__(self, adress=None):
        self.set_options = ["Volt"]
        self.get_options = ["Volt"]
    def Volt(self):
        return 0.0
    def set_Volt(self, value=None, speed=None):
        pass
'''


def make_core(tmp):
    os.makedirs(os.path.join(tmp, "resources"), exist_ok=True)
    os.makedirs(os.path.join(tmp, "config"), exist_ok=True)
    os.makedirs(os.path.join(tmp, "driver_bundle"), exist_ok=True)
    return tmp


def test_import_scan_and_package_mapping():
    mods = imports_of_source(
        "import pyvisa\nfrom serial import Serial\nimport os, numpy\n"
        "from atto_device.thing import x\n")
    assert mods == {"pyvisa", "serial", "os", "numpy", "atto_device"}
    pkgs, notes = packages_for_modules(mods)
    assert pkgs == ["pyvisa", "pyvisa-py", "pyserial"]
    assert any("atto_device" in n for n in notes)
    # availability checks must not depend on what this environment has:
    from unisweep.core import installer as inst
    inst._PIP_TO_IMPORT["fake-absent"] = "definitely_not_a_module_xyz"
    inst._PIP_TO_IMPORT["fake-numpy"] = "numpy"
    assert missing_packages(["fake-absent"]) == ["fake-absent"]
    assert missing_packages(["fake-numpy"]) == []


def test_catalog_builtin_and_labels():
    tmp = make_core(tempfile.mkdtemp())
    cat = DriverCatalog(tmp)
    assert "Keithley2400" in cat.names()
    entry = cat.get("Keithley2400")
    assert "2400" in entry.instrument and "pyvisa" in entry.requires
    assert "⬇" in cat.label("Keithley2400", installed=False)
    assert "⬇" not in cat.label("Keithley2400", installed=True)


def test_plan_reports_fetch_and_unavailable():
    from unisweep.core import installer as inst
    from unisweep.core.catalog import MODULE_TO_PIP
    MODULE_TO_PIP["definitely_absent_mod_xyz"] = ("definitely-absent-pkg",)
    inst._PIP_TO_IMPORT["definitely-absent-pkg"] = "definitely_absent_mod_xyz"
    tmp = make_core(tempfile.mkdtemp())
    with open(os.path.join(tmp, "driver_bundle", "BundleDev.py"), "w") as fh:
        fh.write(MOCK_DRIVER)
    registry = DeviceRegistry(tmp)
    cat = DriverCatalog(tmp)
    installer = DriverInstaller(registry, cat, queue.Queue())
    plan = installer.plan(["BundleDev", "Keithley2400"])
    # both fetchable: BundleDev from the bundle, Keithley2400 via the
    # default repository raw URLs
    assert "BundleDev" in plan.to_fetch and "Keithley2400" in plan.to_fetch
    assert plan.unavailable == []
    assert "definitely-absent-pkg" in plan.pip_install  # from the import
    # with the repository disabled, an un-sourced driver is unavailable
    cat.repo = ""
    plan2 = installer.plan(["Keithley2400"])
    assert "Keithley2400" in plan2.unavailable


def test_install_from_bundle_applies_assignment():
    tmp = make_core(tempfile.mkdtemp())
    with open(os.path.join(tmp, "driver_bundle", "BundleDev.py"), "w") as fh:
        fh.write(MOCK_DRIVER.replace(
            "import definitely_absent_mod_xyz", ""))  # offline-safe
    registry = DeviceRegistry(tmp)
    cat = DriverCatalog(tmp)
    q = queue.Queue()
    installer = DriverInstaller(registry, cat, q)
    assert not registry.is_installed("BundleDev")
    installer.install_async(["BundleDev"],
                            assignments={"GPIB0::9::INSTR": "BundleDev"})
    t0 = time.time()
    done = None
    while time.time() - t0 < 30:
        try:
            msg = q.get(timeout=1)
        except queue.Empty:
            continue
        if msg[0] == "install_done":
            done = msg
            break
    assert done is not None and done[1] is True, done
    assert os.path.exists(os.path.join(tmp, "resources", "BundleDev.py"))
    assert registry.is_installed("BundleDev")
    assert registry.types["GPIB0::9::INSTR"] == "BundleDev"
    # the freshly installed driver actually connects
    adapter = registry.connect("GPIB0::9::INSTR")
    assert adapter.set_options == ["Volt"]
    # and the assignment is now visible in display names
    assert registry.display_name("GPIB0::9::INSTR") == \
        "GPIB0::9::INSTR — BundleDev"
    assert DeviceRegistry.address_from_display(
        "GPIB0::9::INSTR — BundleDev") == "GPIB0::9::INSTR"


def test_install_from_url_file_scheme():
    tmp = make_core(tempfile.mkdtemp())
    src = os.path.join(tmp, "remote_repo")
    os.makedirs(src)
    with open(os.path.join(src, "UrlDev.py"), "w") as fh:
        fh.write(MOCK_DRIVER.replace("import definitely_absent_mod_xyz", "")
                 .replace("BundleDev", "UrlDev"))
    registry = DeviceRegistry(tmp)
    cat = DriverCatalog(tmp)
    cat.base_url = "file://" + src.replace(os.sep, "/")
    q = queue.Queue()
    installer = DriverInstaller(registry, cat, q)
    installer.install_async(["UrlDev"])
    t0 = time.time()
    done = None
    while time.time() - t0 < 30:
        try:
            msg = q.get(timeout=1)
        except queue.Empty:
            continue
        if msg[0] == "install_done":
            done = msg
            break
    assert done is not None and done[1] is True, done
    assert registry.is_installed("UrlDev")


def test_bad_download_is_rejected():
    tmp = make_core(tempfile.mkdtemp())
    src = os.path.join(tmp, "remote_repo")
    os.makedirs(src)
    with open(os.path.join(src, "Broken.py"), "w") as fh:
        fh.write("<html>404 not a python file</html>")
    registry = DeviceRegistry(tmp)
    cat = DriverCatalog(tmp)
    cat.base_url = "file://" + src.replace(os.sep, "/")
    q = queue.Queue()
    installer = DriverInstaller(registry, cat, q)
    installer.install_async(["Broken"])
    t0 = time.time()
    done = None
    while time.time() - t0 < 30:
        try:
            msg = q.get(timeout=1)
        except queue.Empty:
            continue
        if msg[0] == "install_done":
            done = msg
            break
    assert done is not None and done[1] is False
    assert not os.path.exists(os.path.join(tmp, "resources", "Broken.py"))


def _fake_repo_zip(tmp, branch="main"):
    """Build a snapshot zip mimicking the NUS_experiment layout."""
    import io, zipfile
    buf = io.BytesIO()
    root = f"NUS_experiment-{branch}"
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(f"{root}/devices/NewScope.py",
                   "import fancy_vendor\nclass NewScope:\n"
                   "    def __init__(self, adress=None):\n"
                   "        self.set_options=['V']; self.get_options=['V']\n"
                   "    def V(self): return fancy_vendor.VALUE\n"
                   "    def set_V(self, value=None, speed=None): pass\n")
        z.writestr(f"{root}/devices/fancy_vendor/__init__.py",
                   "VALUE = 42\n")
        z.writestr(f"{root}/devices/fancy_vendor/sub/util.py", "x = 1\n")
        z.writestr(f"{root}/devices/__init__.py", "")
    path = os.path.join(tmp, "config", "repo_snapshot.zip")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(buf.getvalue())
    return path


def test_repo_discovery_from_snapshot_and_offline_fallback():
    tmp = make_core(tempfile.mkdtemp())
    cat = DriverCatalog(tmp)
    _fake_repo_zip(tmp)
    drivers, packages = cat._parse_snapshot()
    assert "NewScope" in drivers and "__init__" not in drivers
    assert packages == {"fancy_vendor"}
    cat.repo_drivers.update(drivers)
    cat.repo_packages |= packages
    added = cat._merge_repo_drivers()
    assert "NewScope" in added
    assert "repository" in cat.get("NewScope").instrument
    # index cache persists: a fresh catalog knows the driver offline
    cat2 = DriverCatalog(tmp)
    assert cat2.get("NewScope") is not None
    assert cat2.has_repo_package("fancy_vendor")
    # offline refresh (API+zip both unreachable) degrades gracefully
    cat2.repo = "no-such-user/no-such-repo-xyz"
    added, msg, ok = cat2.refresh_remote(timeout=3)
    assert not ok and "offline" in msg
    assert cat2.get("NewScope") is not None       # cache still in effect


def test_install_new_driver_and_support_package_from_snapshot():
    """The 'new device pushed to GitHub' flow, fully offline from the
    cached snapshot: driver appended, fetched, vendored package extracted,
    class importable, device connects."""
    tmp = make_core(tempfile.mkdtemp())
    _fake_repo_zip(tmp)
    cat = DriverCatalog(tmp)
    drivers, packages = cat._parse_snapshot()
    cat.repo_drivers.update(drivers)
    cat.repo_packages |= packages
    cat._merge_repo_drivers()
    registry = DeviceRegistry(tmp)
    q = queue.Queue()
    installer = DriverInstaller(registry, cat, q)
    plan = installer.plan(["NewScope"])
    assert "NewScope" in plan.to_fetch
    assert plan.extract_packages == ["fancy_vendor"]
    assert plan.pip_install == []                 # vendored, not pip
    installer.install_async(["NewScope"], {"COM9": "NewScope"})
    t0 = time.time()
    done = None
    while time.time() - t0 < 30:
        try:
            msg = q.get(timeout=1)
        except queue.Empty:
            continue
        if msg[0] == "install_done":
            done = msg
            break
    assert done and done[1] is True, done
    assert os.path.exists(os.path.join(tmp, "resources", "NewScope.py"))
    assert os.path.exists(os.path.join(tmp, "resources", "fancy_vendor",
                                       "sub", "util.py"))
    assert registry.is_installed("NewScope")
    adapter = registry.connect("COM9")
    assert adapter.get("V") == 42                 # vendored package works


def test_dependency_db_learn_and_precedence():
    from unisweep.core.depsdb import DependencyDB
    tmp = make_core(tempfile.mkdtemp())
    db = DependencyDB(tmp)
    assert db.packages_for("msl") == ["msl-equipment"]     # builtin seed
    assert db.packages_for("no_such_import_abc") is None
    db.learn("no_such_import_abc", ["real-pip-name"])
    assert db.packages_for("no_such_import_abc") == ["real-pip-name"]
    # learned/user record overrides a builtin guess permanently
    db.learn("msl", ["msl-equipment==1.0"])
    db2 = DependencyDB(tmp)                                # reload from disk
    assert db2.packages_for("msl") == ["msl-equipment==1.0"]
    assert db2.packages_for("no_such_import_abc") == ["real-pip-name"]
    cands = db.candidates("My_Module")
    assert ["My_Module"] in cands and ["my-module"] in cands


def test_registry_captures_import_errors_and_fix_path():
    tmp = make_core(tempfile.mkdtemp())
    with open(os.path.join(tmp, "resources", "BrokenDev.py"), "w") as fh:
        fh.write("import definitely_absent_mod_xyz\nclass BrokenDev:\n"
                 "    pass\n")
    registry = DeviceRegistry(tmp)
    assert not registry.is_installed("BrokenDev")
    assert registry.has_driver_file("BrokenDev")
    err = registry.import_error("BrokenDev")
    assert "definitely_absent_mod_xyz" in err, err
    # the installer plan for the broken driver knows what to do with it
    from unisweep.core.catalog import MODULE_TO_PIP
    from unisweep.core import installer as inst
    MODULE_TO_PIP.setdefault("definitely_absent_mod_xyz",
                             ("definitely-absent-pkg",))
    inst._PIP_TO_IMPORT.setdefault("definitely-absent-pkg",
                                   "definitely_absent_mod_xyz")
    installer = DriverInstaller(registry, DriverCatalog(tmp), queue.Queue())
    plan = installer.plan(["BrokenDev"])
    assert "definitely-absent-pkg" in plan.pip_install


def test_devices_alias_package_resolves_repo_style_imports():
    """'from devices.helper import X' must resolve against resources/."""
    tmp = make_core(tempfile.mkdtemp())
    with open(os.path.join(tmp, "resources", "helper.py"), "w") as fh:
        fh.write("MAGIC = 7\n")
    with open(os.path.join(tmp, "resources", "AliasDev.py"), "w") as fh:
        fh.write("from devices.helper import MAGIC\n"
                 "class AliasDev:\n"
                 "    def __init__(self, adress=None):\n"
                 "        self.set_options=['V']; self.get_options=['V']\n"
                 "    def V(self): return MAGIC\n"
                 "    def set_V(self, value=None, speed=None): pass\n")
    registry = DeviceRegistry(tmp)
    assert registry.is_installed("AliasDev"), \
        registry.import_error("AliasDev")
    registry.assign("COMA", "AliasDev")
    assert registry.connect("COMA").get("V") == 7


def test_verify_and_learn_records_working_recipe(monkey_installs=True):
    """Unknown import -> candidate probing -> recipe recorded permanently.
    pip is faked by injecting the module, so the test stays offline."""
    import types
    tmp = make_core(tempfile.mkdtemp())
    with open(os.path.join(tmp, "resources", "LearnDev.py"), "w") as fh:
        fh.write("import strange_module_qqq\nclass LearnDev:\n"
                 "    def __init__(self, adress=None):\n"
                 "        self.set_options=['V']; self.get_options=['V']\n"
                 "    def V(self): return 1\n"
                 "    def set_V(self, value=None, speed=None): pass\n")
    registry = DeviceRegistry(tmp)
    assert "strange_module_qqq" in registry.import_error("LearnDev")
    q = queue.Queue()
    installer = DriverInstaller(registry, DriverCatalog(tmp), q)

    def fake_pip(packages):
        # "installing" the first candidate makes the import resolve
        if packages == ["strange_module_qqq"]:
            import importlib.machinery
            mod = types.ModuleType("strange_module_qqq")
            mod.__spec__ = importlib.machinery.ModuleSpec(
                "strange_module_qqq", None)
            sys.modules["strange_module_qqq"] = mod
            return True
        return False
    installer._pip_install = fake_pip
    installer.install_async(["LearnDev"])
    t0 = time.time()
    done = None
    while time.time() - t0 < 30:
        try:
            msg = q.get(timeout=1)
        except queue.Empty:
            continue
        if msg[0] == "install_done":
            done = msg
            break
    assert done and done[1] is True, done
    assert registry.is_installed("LearnDev")
    assert installer.deps.packages_for("strange_module_qqq") == \
        ["strange_module_qqq"], "recipe must be recorded"
    sys.modules.pop("strange_module_qqq", None)


if __name__ == "__main__":
    import traceback
    passed = failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
                passed += 1
            except Exception:
                print(f"FAIL {name}")
                traceback.print_exc()
                failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)


# --------------------------------------------------------------------------


# --------------------------------------------------------------------------
