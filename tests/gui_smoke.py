"""Cold-start GUI smoke test — run under a display (xvfb-run on Linux).

Exercises every user-reachable control on a FRESH app with no sweep and no
monitor running — the state the software is actually in right after
launch — and traps every Tkinter callback exception. The bug class this
exists for: handlers that implicitly assume a sweep has populated columns
(e.g. "New line plot" pressed before any Start crashed with IndexError).

    xvfb-run -a python tests/gui_smoke.py
"""

import os
import sys
import tempfile
import time


def scratch(name: str) -> str:
    """A throwaway core directory.

    Not a hardcoded /tmp: this test is most often run on the Windows
    machine that owns the instruments.
    """
    return os.path.join(tempfile.gettempdir(), name)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter.messagebox

_boxes = []
for _name in ("showinfo", "showwarning", "showerror"):
    setattr(tkinter.messagebox, _name,
            lambda t, m="", *a, _n=_name, **k: _boxes.append((_n, t, m)))
tkinter.messagebox.askyesno = lambda *a, **k: False        # decline dialogs

# ---- Spyder/IPython runfile guard -----------------------------------
# main.py carries one for the same reason: this file is usually run with
# Spyder's runfile, in a kernel that may already hold a half-reloaded
# unisweep tree from an earlier run. A test that imports a stale module
# tests nothing — and reports failures that cannot be reproduced from the
# source on disk. Purge before the first unisweep import.
for _name in [_m for _m in list(sys.modules)
              if _m == "unisweep" or _m.startswith("unisweep.")
              or _m == "tests.mock_driver"]:
    del sys.modules[_name]

from tests.mock_driver import MockDevice                    # noqa: E402
from unisweep.core.devices import DriverAdapter, VirtualTime  # noqa: E402
import unisweep.gui.app as appmod                           # noqa: E402


class FakeRegistry:
    def __init__(self, core_dir=None):
        self.resources_dir = os.path.join(core_dir or "/tmp", "resources")
        self.addresses = ["Time", "SMU", "LOCKIN", "BARE"]
        self.types = {"Time": "Time", "SMU": "Mock", "LOCKIN": "Mock"}
        self.driver_classes = {"Mock": MockDevice}
        self.import_errors = {}
        self._adapters = {}

    def connect(self, a):
        if a not in self._adapters:
            inst = VirtualTime() if a == "Time" else MockDevice(a)
            self._adapters[a] = DriverAdapter(a, inst)
        return self._adapters[a]

    def connected(self, a): return self._adapters.get(a)
    def disconnect_all(self): pass

    def set_options(self, a):
        return ["Time"] if a == "Time" else ["Volt", "Curr"]

    def get_options(self, a):
        return ["Elapsed", "Random"] if a == "Time" else ["Volt", "Curr"]

    def read_catalogue(self):
        return [f"{a}.{o}" for a in self.addresses
                for o in self.get_options(a)]

    def scan_async(self, done): done([])
    def add_address(self, a): pass
    def assign(self, a, t): self.types[a] = t
    def unassign(self, a): self.types.pop(a, None)
    def is_installed(self, n): return True
    def import_error(self, n): return ""
    def has_driver_file(self, n): return True

    def display_name(self, a):
        t = self.types.get(a, "")
        return a if not t or a == "Time" else f"{a} — {t}"

    def display_list(self):
        return [self.display_name(a) for a in self.addresses]

    @staticmethod
    def address_from_display(d):
        return d.rsplit(" — ", 1)[0] if " — " in d else d


def main():
    appmod.DeviceRegistry = FakeRegistry
    app = appmod.App(scratch("uni_coldstart"))
    tk_errors = []
    app.root.report_callback_exception = \
        lambda et, ev_, tb: tk_errors.append((et.__name__, str(ev_)))

    def pump(seconds=0.2):
        t0 = time.time()
        while time.time() - t0 < seconds:
            app.root.update()
            time.sleep(0.01)

    pump(0.4)
    if app._wizard is not None:
        app._wizard._skip()
    pump(0.2)

    # ---- 1. cold plot spawning (the reported crash) -------------------
    line = app.plots.spawn("line")
    mp = app.plots.spawn("map")
    pump(0.5)
    line.redraw_if_dirty()
    mp.redraw_if_dirty()
    assert line.winfo_exists() and mp.winfo_exists()
    line.open_settings()
    pump(0.1)
    [w for w in line.winfo_children()][-1]  # dialog exists
    from unisweep.gui.plot_panel import PlotSettingsDialog
    for dlg in line.winfo_children():
        if isinstance(dlg, PlotSettingsDialog):
            dlg._apply()
            dlg.destroy()
    mp.open_settings()
    pump(0.1)
    for dlg in mp.winfo_children():
        if isinstance(dlg, PlotSettingsDialog):
            dlg._ok()
    pump(0.1)

    # ---- 2. cold monitor plot + idle buttons everywhere ---------------
    app.show_page("Set & Get")
    pump(0.1)
    sg = app.pages["Set & Get"]
    sg_win = app.setget_plots.spawn("line")     # before any monitor
    pump(0.3)
    sg._start()                                  # nothing selected -> box
    sg._stop()                                   # stop while not running
    app.show_page("Sweep")
    page = app.pages["Sweep"]
    page._stop()                                 # stop while idle
    page._to_zero()                              # to-zero while idle
    page._start()                                # start with defaults
    if app.engine is not None and app.engine.is_alive():
        app.engine.stop()
        while app.engine.is_alive():
            pump(0.1)
    pump(0.2)
    app.show_page("Devices")
    pump(0.1)
    rows = app.pages["Devices"].rows
    rows["BARE"]._test()                         # unassigned Test
    rows["BARE"]._sweep_test()                   # unassigned sweep test
    rows["SMU"]._test()                          # background connect
    pump(0.6)
    app.show_page("Settings")
    pump(0.1)
    app.pages["Settings"]._changed()             # save defaults
    app.show_page("Sweep")
    pump(0.1)

    # ---- 2b. live theme toggle with windows open ----------------------
    import unisweep.gui.theme as _th
    from tkinter import ttk as _ttk
    sp2 = app.pages["Settings"]
    sp2.v_theme.set("light")
    sp2._theme_changed()
    pump(0.4)
    assert _ttk.Style(app.root).lookup("TFrame", "background") == \
        _th.LIGHT["surface"]
    sp2.v_theme.set("dark")
    sp2._theme_changed()
    pump(0.4)
    assert _ttk.Style(app.root).lookup("TFrame", "background") == \
        _th.DARK["surface"]

    # ---- 3. the cold windows adopt real columns when a sweep starts ---
    page.dims.current(1)
    page._set_dims()
    cards = page.axis_cards
    for c, dev in ((cards[0], "SMU"), (cards[1], "LOCKIN")):
        c.device.set(app.registry.display_name(dev))
        c._device_changed()
        c.parameter.set("Volt")
        c.start.set(0); c.stop.set(1)
        c.rate.set(0.5); c.delay.set(0.005)
        c.mode.current(1)
    page.refresh_reads()
    for i in range(page.reads_list.size()):
        if page.reads_list.get(i) == "LOCKIN.Curr":
            page.reads_list.selection_set(i)
    prog = page.build_program()
    assert prog is not None, "program should validate"
    app.start_sweep(prog)
    t0 = time.time()
    while app.engine.is_alive() and time.time() - t0 < 40:
        pump(0.05)
    pump(0.5)
    assert line.config.xcol == "SMU.Volt_sweep", line.config.xcol
    assert mp.config.zcol == "LOCKIN.Curr", mp.config.zcol
    x, _ = app.live_data.xy(line.config.xcol, line.config.ycol,
                            scan_only=True)
    assert len(x) > 0, "line window must have data after the sweep"
    assert app.live_maps.has_data("LOCKIN.Curr")

    # ---- 4. monitor after cold window ---------------------------------
    app.show_page("Set & Get")
    for i in range(sg.reads_list.size()):
        if sg.reads_list.get(i) in ("Time.Elapsed", "SMU.Volt"):
            sg.reads_list.selection_set(i)
    sg.delay.set("0.1")
    sg._start()
    pump(0.8)
    sg._stop()
    assert sg_win.config.xcol == "time", sg_win.config.xcol
    mx, _ = app.setget_data.xy("time", sg_win.config.ycol)
    assert len(mx) >= 4

    # ---- 5. close plot windows, spawn again, quit ---------------------
    app.plots.remove(line)
    app.plots.remove(mp)
    again = app.plots.spawn("map")               # template restore path
    pump(0.3)
    again.redraw_if_dirty()
    app.setget_plots.remove(sg_win)
    pump(0.2)

    assert not tk_errors, f"Tk callback exceptions: {tk_errors}"
    print(f"COLD-START SMOKE OK — 0 Tk exceptions, "
          f"{len(_boxes)} dialogs handled")
    app._on_close()                    # exit the way the real app exits


def lifecycle_check():
    """Real DeviceRegistry: a storm of page/dimension switching must
    instantiate each instrument at most once, and closing the app must
    send close() to every instrument that was opened."""
    import json
    import shutil
    import tests.mock_driver as md

    core = scratch("uni_lifecycle")
    shutil.rmtree(core, ignore_errors=True)
    os.makedirs(os.path.join(core, "resources"))
    os.makedirs(os.path.join(core, "config"))
    with open(os.path.join(core, "resources", "LifeDev.py"), "w") as fh:
        repo_root = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))
        fh.write("import sys\n"
                 f"sys.path.insert(0, {repo_root!r})\n"
                 "from tests.mock_driver import MockDevice\n"
                 "class LifeDev(MockDevice):\n"
                 "    def __init__(self, adress=None):\n"
                 "        super().__init__(adress)\n"
                 "        self.set_options = ['Volt', 'Curr']\n"
                 "        self.get_options = ['Volt', 'Curr', 'Noise']\n")
    with open(os.path.join(core, "config", "address_dictionary.txt"),
              "w") as fh:
        json.dump({"Time": "Time", "D1": "LifeDev", "D2": "LifeDev"}, fh)
    with open(os.path.join(core, "config", "setup_complete"), "w") as fh:
        fh.write("done\n")
    with open(os.path.join(core, "config", "repo_index.json"), "w") as fh:
        json.dump({"drivers": {}, "packages": []}, fh)
    # The startup autoconnect deliberately opens every assigned instrument,
    # on a timer ~0.7 s after the window appears — which lands inside the
    # switching storm below and makes "did switching open this?"
    # unanswerable. Switch it off so the first assertion measures what its
    # name says; autoconnect gets its own phase at the end.
    with open(os.path.join(core, "config", "settings.json"), "w") as fh:
        json.dump({"connect_on_start": False}, fh)

    import importlib
    importlib.reload(appmod)                 # restore the real registry
    md.MockDevice.init_log.clear()
    md.MockDevice.close_log.clear()
    app = appmod.App(core)
    tk_errors = []
    app.root.report_callback_exception = \
        lambda et, ev_, tb: tk_errors.append((et.__name__, str(ev_)))

    def pump(seconds=0.15):
        t0 = time.time()
        while time.time() - t0 < seconds:
            app.root.update()
            time.sleep(0.01)

    pump(0.4)
    page = app.pages["Sweep"]
    sg = app.pages["Set & Get"]

    # ---- the switching storm ------------------------------------------
    for _ in range(2):
        for dims in (0, 1, 2, 0):            # 1-D -> 2-D -> 3-D -> 1-D
            page.dims.current(dims)
            page._set_dims()
            for card in page.axis_cards:
                card.device.set(app.registry.display_name("D1"))
                card._device_changed()
            page.refresh_reads()
            pump(0.05)
        for name in ("Set & Get", "Devices", "Settings", "Sweep"):
            app.show_page(name)
            pump(0.05)
    assert md.MockDevice.init_log == [], (
        f"switching alone must not open instruments: "
        f"{md.MockDevice.init_log} (autoconnect is off for this phase, so "
        f"something in page/dimension switching connected them)")

    # ---- monitor + sweep + Test: connect once each, reuse everywhere --
    app.show_page("Set & Get")
    for i in range(sg.reads_list.size()):
        if sg.reads_list.get(i) in ("D1.Volt", "D2.Curr"):
            sg.reads_list.selection_set(i)
    sg.delay.set("0.05")
    sg._start()
    pump(0.4)
    sg._stop()
    app.show_page("Sweep")
    page.dims.current(0)
    page._set_dims()
    card = page.axis_cards[0]
    card.device.set(app.registry.display_name("D1"))
    card._device_changed()
    card.parameter.set("Volt")
    card.start.set(0); card.stop.set(0.3)
    card.rate.set(0.1); card.delay.set(0.005)
    card.mode.current(1)
    page.refresh_reads()
    for i in range(page.reads_list.size()):
        if page.reads_list.get(i) == "D2.Curr":
            page.reads_list.selection_set(i)
    prog = page.build_program()
    assert prog is not None, f"program invalid; dialogs: {_boxes[-2:]}"
    assert app.start_sweep(None) is None       # guarded, no crash
    app.start_sweep(prog)
    t0 = time.time()
    while app.engine.is_alive() and time.time() - t0 < 30:
        pump(0.05)
    app.show_page("Devices")
    app.pages["Devices"].rows["D1"]._test()
    pump(0.6)
    counts = {a: md.MockDevice.init_log.count(a) for a in ("D1", "D2")}
    assert counts == {"D1": 1, "D2": 1}, \
        f"instruments initialised more than once: {md.MockDevice.init_log}"

    # ---- autoconnect must not re-open what is already connected ------
    app.settings.connect_on_start = True
    app._autoconnect_started = False
    app._start_autoconnect()
    pump(0.5)
    assert {a: md.MockDevice.init_log.count(a)
            for a in ("D1", "D2")} == counts, (
        f"autoconnect re-opened already-connected instruments: "
        f"{md.MockDevice.init_log}")

    # ---- close the app: every opened instrument gets close() ---------
    app._on_close()
    assert sorted(md.MockDevice.close_log) == ["D1", "D2"], \
        f"close() not sent to all instruments: {md.MockDevice.close_log}"
    assert not tk_errors, tk_errors
    print(f"LIFECYCLE OK — inits {counts}, "
          f"closed {sorted(md.MockDevice.close_log)}")


def control_surface_check():
    """The agent control surface, against the REAL widgets.

    Everything in tests/test_agent.py runs on duck-typed stand-ins because
    the control layer never imports tkinter. This is the other half: it
    proves that each name in a page's controls() is bound to a widget that
    exists and behaves as the binder assumes — reading every control is
    the part that catches a renamed attribute or a getter that raises.
    """
    appmod.DeviceRegistry = FakeRegistry
    app = appmod.App(scratch("uni_controls"))
    tk_errors = []
    app.root.report_callback_exception = \
        lambda et, ev_, tb: tk_errors.append((et.__name__, str(ev_)))

    def pump(seconds=0.2):
        t0 = time.time()
        while time.time() - t0 < seconds:
            app.root.update()
            time.sleep(0.01)

    pump(0.4)
    if app._wizard is not None:
        app._wizard._skip()
    pump(0.2)

    from unisweep.agent.controls import ControlError
    from unisweep.agent.session import AgentSession
    session = AgentSession(app)          # this thread owns the widgets

    # ---- 1. every page contributes, and every control reads ----------
    app.show_page("Devices")             # device rows are built on show
    pump(0.3)
    app.show_page("Sweep")
    pump(0.2)
    described = session.list_controls()["controls"]
    names = {c["name"] for c in described}
    for required in ("app.page", "app.agent_endpoint", "sweep.start",
                     "sweep.dimensions", "sweep.axis1.start",
                     "sweep.reads", "sweep.script", "sweep.load_script",
                     "sweep.save_script", "sweep.script_file",
                     "setget.row1.set", "setget.delay", "settings.theme",
                     "settings.agent_enabled", "devices.scan"):
        assert required in names, f"missing control: {required}"
    pages = {c["page"] for c in described}
    assert pages >= {"app", "sweep", "setget", "settings", "devices"}, \
        f"a page contributed nothing: {sorted(pages)}"
    broken = [(c["name"], c["error"]) for c in described if "error" in c]
    assert not broken, f"controls whose value could not be read: {broken}"
    assert len(described) > 60, f"only {len(described)} controls found"
    assert any(n.endswith(".type") for n in names), "no device rows"

    # ---- 2. typing into the fields -----------------------------------
    session.set_controls({"sweep.dimensions": "2D"})
    pump(0.2)
    assert "sweep.axis2.start" in session.registry(), \
        "switching to 2D must add the second axis card"
    session.set_controls({
        "sweep.axis1.device": "SMU",      # the bare address, not the label
        "sweep.axis1.start": -1.0, "sweep.axis1.stop": 1.0,
        "sweep.axis1.rate": 0.5, "sweep.axis1.delay": 0.01,
        "sweep.axis1.mode": "step, units/pt", "sweep.axis1.walks": 2,
        "sweep.axis1.snake": True,
        "sweep.script": "pass  # smoke",
        "sweep.filename": "smoke"})
    pump(0.2)
    values = session.read_controls(prefix="sweep.axis1")
    assert values["sweep.axis1.start"] == -1.0
    assert values["sweep.axis1.walks"] == 2
    assert values["sweep.axis1.snake"] is True
    assert values["sweep.axis1.parameter"] in ("Volt", "Curr"), \
        "the parameter list must follow the chosen device"
    try:
        session.set_controls({"sweep.axis1.start": "banana"})
        raise AssertionError("a non-number was accepted")
    except ControlError:
        pass

    # ---- 3. a program round-trips through the page --------------------
    session.set_controls({"sweep.dimensions": "1D",
                          "sweep.reads": ["SMU.Volt"]})
    pump(0.2)
    program = session.get_program()
    assert program["valid"], program["complaints"]
    assert program["program"]["axes"][0]["device"] == "SMU"
    preview = session.dry_run()
    assert preview["ok"], preview
    assert preview["planned_points"] > 1

    # ---- 4. pressing buttons, dialogs answered from a script ----------
    checked = session.press("sweep.check_condition")
    pump(0.2)
    assert checked["ok"], checked
    # the script file buttons go through the GUI's own file dialogs
    script_file = os.path.join(scratch("uni_controls"), "smoke_script.py")
    saved = session.press("sweep.save_script", files=[script_file])
    pump(0.2)
    assert saved["ok"], saved
    assert os.path.exists(script_file), "Save script wrote nothing"
    session.set_controls({"sweep.script": ""})
    loaded = session.press("sweep.load_script", files=[script_file])
    pump(0.2)
    assert loaded["ok"], loaded
    assert "smoke" in session.read_controls(
        ["sweep.script"])["sweep.script"]
    assert session.read_controls(
        ["sweep.script_file"])["sweep.script_file"] == "smoke_script.py"
    unanswered = session.press("sweep.load_script")
    assert unanswered["ok"] is False, "a file dialog must ask, not guess"
    try:
        session.press("sweep.stop")       # greyed out with no sweep
        raise AssertionError("a disabled button was pressed")
    except ControlError as exc:
        assert "greyed out" in str(exc)

    # ---- 5. run one short sweep the way an assistant would -----------
    started = session.run_sweep({
        # walks/snake are set explicitly: phase 2 left them at 2/True on
        # the page, and a program that does not say is a program that
        # inherits whatever the last person did
        "axes": [{"device": "SMU", "parameter": "Volt", "start": 0.0,
                  "stop": 0.4, "rate": 0.1, "delay": 0.01,
                  "count_mode": "step", "walks": 1, "snake": False}],
        "reads": ["SMU.Volt"]})
    assert started["started"], started
    for _ in range(200):
        pump(0.05)
        if app.event_tap.state == "finished":
            break
    assert app.event_tap.state == "finished", session.status()
    assert session.status()["finished"]["points"] == 5

    # ---- 6. the endpoint starts and stops -----------------------------
    assert app.start_agent_endpoint(), app.agent_summary()
    assert app.agent_service.port > 0
    assert "listening" not in app.agent_summary()
    app.stop_agent_endpoint()
    assert app.agent_service is None

    app._on_close()
    assert not tk_errors, tk_errors
    print(f"CONTROL SURFACE OK — {len(described)} controls across "
          f"{len(pages)} pages")


if __name__ == "__main__":
    import shutil
    for _name in ("uni_coldstart", "uni_lifecycle", "uni_controls"):
        shutil.rmtree(scratch(_name), ignore_errors=True)
    main()
    lifecycle_check()
    control_surface_check()
