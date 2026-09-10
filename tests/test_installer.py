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


# ------------- connection lifecycle: single init + clean close -------------
def _life_core():
    import tests.mock_driver as md
    tmp = make_core(tempfile.mkdtemp())
    with open(os.path.join(tmp, "resources", "LifeDev.py"), "w") as fh:
        fh.write("from tests.mock_driver import MockDevice\n"
                 "class LifeDev(MockDevice):\n    pass\n")
    md.MockDevice.init_log.clear()
    md.MockDevice.close_log.clear()
    registry = DeviceRegistry(tmp)
    registry.assign("GPIB0::5::INSTR", "LifeDev")
    registry.assign("GPIB0::6::INSTR", "LifeDev")
    return registry, md.MockDevice


def test_connect_caches_single_instance_per_address():
    registry, Mock = _life_core()
    a1 = registry.connect("GPIB0::5::INSTR")
    a2 = registry.connect("GPIB0::5::INSTR")
    registry.connect("GPIB0::6::INSTR")
    assert a1 is a2, "same address must reuse the same adapter"
    # option queries and catalogue refreshes never re-instantiate
    registry.set_options("GPIB0::5::INSTR")
    registry.get_options("GPIB0::5::INSTR")
    registry.read_catalogue()
    registry.read_catalogue()
    assert Mock.init_log.count("GPIB0::5::INSTR") == 1, Mock.init_log
    assert Mock.init_log.count("GPIB0::6::INSTR") == 1, Mock.init_log


def test_option_queries_do_not_touch_hardware():
    """Unconnected devices: options come from source parsing, not from an
    instantiation — switching pages/dimensions must not open sessions."""
    registry, Mock = _life_core()
    for _ in range(5):                       # a switching storm
        registry.set_options("GPIB0::5::INSTR")
        registry.get_options("GPIB0::6::INSTR")
        registry.read_catalogue()
    assert Mock.init_log == [], f"hardware touched: {Mock.init_log}"


def test_disconnect_all_closes_every_instrument_once():
    registry, Mock = _life_core()
    registry.connect("GPIB0::5::INSTR")
    registry.connect("GPIB0::6::INSTR")
    registry.disconnect_all()
    assert sorted(Mock.close_log) == ["GPIB0::5::INSTR", "GPIB0::6::INSTR"]
    registry.disconnect_all()                # idempotent
    assert len(Mock.close_log) == 2, "close must be sent exactly once"


def test_reassign_closes_replaced_instrument_before_new_one_opens():
    registry, Mock = _life_core()
    registry.connect("GPIB0::5::INSTR")
    registry.assign("GPIB0::5::INSTR", "LifeDev")   # same type, re-open
    assert Mock.close_log == ["GPIB0::5::INSTR"], \
        "old session must close on reassignment"
    registry.connect("GPIB0::5::INSTR")
    assert Mock.init_log.count("GPIB0::5::INSTR") == 2
    assert len(Mock.close_log) == 1


def test_driver_without_close_shuts_down_quietly():
    tmp = make_core(tempfile.mkdtemp())
    with open(os.path.join(tmp, "resources", "NoClose.py"), "w") as fh:
        fh.write("class NoClose:\n"
                 "    def __init__(self, adress=None):\n"
                 "        self.set_options=['V']; self.get_options=['V']\n"
                 "    def V(self): return 0\n"
                 "    def set_V(self, value=None, speed=None): pass\n")
    registry = DeviceRegistry(tmp)
    registry.assign("COM3", "NoClose")
    registry.connect("COM3")
    registry.disconnect_all()                # no close() -> no error


def test_broken_close_does_not_block_siblings():
    tmp = make_core(tempfile.mkdtemp())
    with open(os.path.join(tmp, "resources", "BadClose.py"), "w") as fh:
        fh.write("class BadClose:\n"
                 "    def __init__(self, adress=None):\n"
                 "        self.adress=adress\n"
                 "        self.set_options=['V']; self.get_options=['V']\n"
                 "    def V(self): return 0\n"
                 "    def set_V(self, value=None, speed=None): pass\n"
                 "    def close(self): raise IOError('bus dead')\n")
    with open(os.path.join(tmp, "resources", "GoodClose.py"), "w") as fh:
        fh.write("from tests.mock_driver import MockDevice\n"
                 "class GoodClose(MockDevice):\n    pass\n")
    import tests.mock_driver as md
    md.MockDevice.close_log.clear()
    registry = DeviceRegistry(tmp)
    registry.assign("A1", "BadClose")
    registry.assign("A2", "GoodClose")
    registry.connect("A1")
    registry.connect("A2")
    registry.disconnect_all()                # A1 raises inside close()
    assert "A2" in md.MockDevice.close_log, \
        "one broken close() must not block the other instruments"


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


# ---------------------------------------------------------------------------
# Driver-name case resolution and one-instance-per-address connection.
# Written alongside the "Lowercase devices libraries" change and never
# committed; recovered here.
# ---------------------------------------------------------------------------
def test_driver_class_name_case_and_imported_base(tmpdir=None):
    """Real-world driver files: 'Keithley2400.py' defines class
    'keithley2400' and 'SR830.py' defines 'sr830' while ALSO importing a
    vendor class literally named SR830. Both must be detected (green
    row), and the module's OWN class must win over the imported one."""
    import json
    import tempfile
    from unisweep.core.devices import DeviceRegistry
    core = tempfile.mkdtemp()
    os.makedirs(os.path.join(core, "resources"))
    os.makedirs(os.path.join(core, "config"))
    res = os.path.join(core, "resources")
    with open(os.path.join(res, "Keithley2400.py"), "w") as fh:
        fh.write("class keithley2400:\n"
                 "    def __init__(self, adress=None):\n"
                 "        self.adress = adress\n"
                 "        self.set_options = ['Volt']\n"
                 "        self.get_options = ['Volt']\n"
                 "    def Volt(self):\n        return 1.0\n")
    with open(os.path.join(res, "SR830.py"), "w") as fh:
        fh.write("class SR830:            # 'imported' vendor base\n"
                 "    pass\n"
                 "SR830.__module__ = 'vendor.pkg'\n"
                 "class my_SR830(SR830):\n    pass\n"
                 "class sr830:\n"
                 "    def __init__(self, adress=None):\n"
                 "        self.adress = adress\n"
                 "        self.set_options = ['amplitude']\n"
                 "        self.get_options = ['x']\n"
                 "    def x(self):\n        return 0.5\n")
    with open(os.path.join(core, "config", "address_dictionary.txt"),
              "w") as fh:
        json.dump({"A1": "Keithley2400", "A2": "SR830"}, fh)
    reg = DeviceRegistry(core)
    assert reg.is_installed("Keithley2400"), reg.import_error("Keithley2400")
    assert reg.is_installed("SR830"), reg.import_error("SR830")
    k = reg.driver_classes[reg.resolve_type("Keithley2400")]
    s = reg.driver_classes[reg.resolve_type("SR830")]
    assert k.__name__ == "keithley2400", k
    assert s.__name__ == "sr830", \
        f"the file's own class must win over the imported base: {s}"
    assert reg.set_options("A1") == ["Volt"]
    assert reg.get_options("A2") == ["x"]
    assert reg.connect("A1").raw.__class__.__name__ == "keithley2400"

def test_assignment_case_resolves_to_the_file_on_disk():
    """An address assigned 'Keithley2400' must go green when the file on
    disk is 'keithley2400.py' (and vice versa) — the mismatch that left
    a correctly installed driver showing as not installed."""
    import json
    import tempfile
    from unisweep.core.devices import DeviceRegistry
    core = tempfile.mkdtemp()
    os.makedirs(os.path.join(core, "resources"))
    os.makedirs(os.path.join(core, "config"))
    with open(os.path.join(core, "resources", "keithley2400.py"),
              "w") as fh:
        fh.write("class keithley2400:\n"
                 "    def __init__(self, adress=None):\n"
                 "        self.set_options = ['Volt']\n"
                 "        self.get_options = ['Volt']\n")
    with open(os.path.join(core, "config", "address_dictionary.txt"),
              "w") as fh:
        json.dump({"A1": "Keithley2400"}, fh)
    reg = DeviceRegistry(core)
    assert reg.is_installed("Keithley2400")
    assert reg.import_error("Keithley2400") == ""
    assert reg.resolve_type("Keithley2400") == "keithley2400"
    assert reg.connect("A1") is not None

def test_every_catalogue_entry_resolves_case_insensitively():
    """Audit: for EVERY catalogue driver, the candidate list must offer
    the exact spelling first and a lower-case fallback, so no entry can
    be defeated by repository casing (only Keithley2400 and SR830 need
    the fallback today, but new entries get the same protection)."""
    import tempfile
    from unisweep.core.catalog import DriverCatalog
    core = tempfile.mkdtemp()
    os.makedirs(os.path.join(core, "config"), exist_ok=True)
    cat = DriverCatalog(core)
    names = cat.names()
    assert len(names) > 20, names
    for n in names:
        urls = [s for k, s in cat.source_candidates(n) if k == "url"]
        assert urls, f"{n}: no download candidates"
        assert urls[0].endswith(f"{n}.py"), \
            f"{n}: exact spelling must be tried first ({urls[0]})"
        assert any(u.endswith(f"{n.lower()}.py") for u in urls), \
            f"{n}: lower-case fallback missing"

def test_all_repo_driver_class_names_are_accepted():
    """The two files whose class name differs from the file name are
    Keithley2400 (class keithley2400) and SR830 (class sr830, plus an
    imported vendor SR830). Both shapes — and the ordinary matching
    ones, including a file with helper classes — must resolve."""
    import tempfile
    from unisweep.core.devices import _driver_class_of
    import types as _t

    def module_from(src: str, name: str):
        mod = _t.ModuleType(f"unisweep_drivers.{name}")
        exec(compile(src, f"{name}.py", "exec"), mod.__dict__)
        for obj in list(mod.__dict__.values()):
            if isinstance(obj, type) and obj.__module__ == "builtins":
                obj.__module__ = mod.__name__
        return mod

    cases = [
        ("Keithley2400", "class keithley2400:\n    set_options=['V']\n",
         "keithley2400"),
        ("sr860", "class my_SR860:\n    pass\n"
                  "class sr860:\n    set_options=['amplitude']\n", "sr860"),
        ("LakeShore336", "class LakeShore336:\n    set_options=['T']\n",
         "LakeShore336"),
        ("keithley_series_2600b",
         "class My_Keithley_2600:\n    pass\n"
         "class keithley_series_2600b:\n    set_options=['V']\n",
         "keithley_series_2600b"),
    ]
    for mod_name, src, expected in cases:
        mod = module_from(src, mod_name)
        cls = _driver_class_of(mod, mod_name)
        assert cls is not None and cls.__name__ == expected, \
            f"{mod_name}: got {cls}"

    # the vendor-import shadow: file defines sr830, imports SR830
    mod = _t.ModuleType("unisweep_drivers.SR830")
    class _Vendor:                      # 'from pymeasure... import SR830'
        pass
    _Vendor.__name__ = "SR830"
    _Vendor.__module__ = "pymeasure.instruments.srs"
    mod.SR830 = _Vendor
    exec(compile("class sr830:\n    set_options=['amplitude']\n",
                 "SR830.py", "exec"), mod.__dict__)
    mod.sr830.__module__ = mod.__name__
    cls = _driver_class_of(mod, "SR830")
    assert cls is mod.sr830, f"own class must win, got {cls}"

def test_source_candidates_try_case_variants():
    """The repository stores 'keithley2400.py' / 'sr830.py' in lower
    case while the catalog lists them capitalised — raw GitHub URLs are
    case-sensitive, so both spellings must be attempted."""
    import tempfile
    from unisweep.core.catalog import DriverCatalog
    core = tempfile.mkdtemp()
    os.makedirs(os.path.join(core, "config"), exist_ok=True)
    cat = DriverCatalog(core)
    for name, wanted in (("Keithley2400", "keithley2400.py"),
                         ("SR830", "sr830.py")):
        urls = [spec for kind, spec in cat.source_candidates(name)
                if kind == "url"]
        assert any(u.endswith(wanted) for u in urls), \
            f"{name}: lower-case URL missing from {urls[:4]}"
        assert any(u.endswith(f"{name}.py") for u in urls), \
            f"{name}: exact-case URL missing"
        assert urls.index(next(u for u in urls
                               if u.endswith(f"{name}.py"))) < \
            urls.index(next(u for u in urls if u.endswith(wanted))), \
            "the exact name must still be tried first"

def test_concurrent_connect_yields_single_instance():
    """Two threads racing connect() on the same address: one driver
    __init__, one shared adapter — and a slow open must not block a
    connect to a DIFFERENT address."""
    import threading as th
    import time as _t
    registry, Mock = _life_core()

    class Slow(Mock):
        def __init__(self, adress=None):
            _t.sleep(0.3)
            super().__init__(adress)
    registry.driver_classes["SlowDev"] = Slow
    registry.assign("SLOW::1", "SlowDev")
    Mock.init_log.clear()

    got = {}
    def grab(tag, addr):
        got[tag] = registry.connect(addr)
    t1 = th.Thread(target=grab, args=("a", "SLOW::1"))
    t2 = th.Thread(target=grab, args=("b", "SLOW::1"))
    t1.start(); t2.start()
    _t.sleep(0.05)
    t0 = _t.perf_counter()
    registry.connect("GPIB0::5::INSTR")     # other address: must not wait
    other_dt = _t.perf_counter() - t0
    t1.join(5); t2.join(5)
    assert got["a"] is got["b"], "racing connects must share the instance"
    assert Mock.init_log.count("SLOW::1") == 1, Mock.init_log
    assert other_dt < 0.2, \
        f"a slow open must not block other addresses: {other_dt:.2f}s"


def test_a_crashing_install_still_says_it_is_over():
    """The installer thread is the only thing that posts
    ``install_done``. The setup wizard enables its Close button on that
    message and holds a modal grab until then, so a thread that dies on
    the way leaves a brand-new installation with a window nobody can use
    and no way to reach the Devices page — which is where an instrument
    would be added. Whatever happens in there, the message goes out.
    """
    import queue as _queue
    from unisweep.core.installer import DriverInstaller

    class Exploding(DriverInstaller):
        def _install(self, driver_names, assignments):
            raise RuntimeError("the network is not there")

    q: "_queue.Queue" = _queue.Queue()
    installer = Exploding.__new__(Exploding)
    installer.q = q
    installer._thread = None
    installer._work(["SR830"], {})

    messages = []
    while not q.empty():
        messages.append(q.get_nowait())
    kinds = [m[0] for m in messages]
    assert "install_done" in kinds, kinds
    done = messages[kinds.index("install_done")]
    assert done[1] is False
    assert "the network is not there" in done[2]
    assert any(m[0] == "install_log" and "network is not there" in m[1]
               for m in messages), "the reason belongs in the log too"


def test_a_normal_install_reports_through_the_same_door():
    """The refactor that made the guard possible must not change what a
    successful run says."""
    import queue as _queue
    from unisweep.core.installer import DriverInstaller

    class Quiet(DriverInstaller):
        def _install(self, driver_names, assignments):
            return True, "Installation finished"

    q: "_queue.Queue" = _queue.Queue()
    installer = Quiet.__new__(Quiet)
    installer.q = q
    installer._thread = None
    installer._work(["SR830"], {})
    assert q.get_nowait() == ("install_done", True, "Installation finished")
