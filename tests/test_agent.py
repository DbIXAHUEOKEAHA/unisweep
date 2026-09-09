"""The agent control surface: handles, dialogs, the event tap, the session.

What these pin down:

* every knob is reachable by name, reads back what it was set to, and
  refuses values it cannot hold;
* pressing a button runs exactly the command a click runs, and whatever
  the GUI would have said in a dialog comes back as data instead of
  stopping the world;
* the session can fill the sweep page in from a program, pre-flight it,
  press Start and then say what is happening — all without a display.

Widgets here are duck-typed stand-ins (``tests.fake_widgets``). The
control layer never imports tkinter, which is what makes that possible;
the live wiring of the real pages is exercised by ``tests/gui_smoke.py``
under a display, and by ``test_real_pages_only_bind_widgets_that_exist``
below, which reads the actual GUI source.
"""

import ast
import os
import queue
import sys
import tempfile
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from unisweep.agent import controls as ctl
from unisweep.agent import dialogs as dlg
from unisweep.agent.bridge import BridgeTimeout, DirectBridge, TkBridge
from unisweep.agent.controls import (ControlError, ControlRegistry,
                                     UnknownControl)
from unisweep.agent.session import AgentSession, SessionError
from unisweep.agent.tap import EventTap
from unisweep.core import events as ev
from unisweep.core.config import CountMode, SweepProgram
from unisweep.core.devices import DeviceRegistry, DriverAdapter
from unisweep.core.engine import SweepEngine
from unisweep.core.labprofile import LabProfile
from unisweep.core.limits import LimitPolicy
from tests.fake_widgets import (FakeButton, FakeCombo, FakeEntry, FakeLabel,
                                FakeListbox, FakeSpin, FakeText, FakeVar)
from tests.test_safety import LeakyGate, GATE_PROFILE

# the fake page below lives in this module, so the dialog interceptor has
# to know about it the same way it knows about the real pages
dlg.EXTRA_MODULES.add(__name__)

try:                                    # a machine with a display toolkit
    from tkinter import filedialog, messagebox   # noqa: E402
except ImportError:                     # ...and one without
    class _NoDialogs:
        """Same surface as the tkinter dialog modules, but unusable.

        The interceptor swaps this out for the whole of an agent action,
        so the fake page below never calls through it — and if it ever
        did, saying so loudly beats silently opening nothing."""

        def __getattr__(self, name):
            def unavailable(*args, **kwargs):
                raise RuntimeError(
                    f"{name} was called outside dialog interception")
            return unavailable

    messagebox = _NoDialogs()
    filedialog = _NoDialogs()


# ---------------------------------------------------------------------------
# a registry over mock instruments that still honours the limit policy
# ---------------------------------------------------------------------------
class MockRegistry(DeviceRegistry):

    def __init__(self, core_dir, mocks, policy=None):
        self.core_dir = core_dir
        self._mocks = dict(mocks)
        self._adapters = {}
        self._lock = threading.Lock()
        self.policy = policy
        self.addresses = list(mocks)
        self.types = {a: type(m).__name__ for a, m in mocks.items()}
        self.driver_classes = {}
        self.import_errors = {}

    def connect(self, address):
        with self._lock:
            if address not in self._adapters:
                self._adapters[address] = DriverAdapter(
                    address, self._mocks[address], policy=self.policy)
            return self._adapters[address]

    def set_options(self, address):
        return list(getattr(self._mocks[address], "set_options", []))

    def get_options(self, address):
        return list(getattr(self._mocks[address], "get_options", []))

    def is_installed(self, name):
        return True

    def import_error(self, name):
        return ""


# ---------------------------------------------------------------------------
# a stand-in sweep page with the same control names as the real one
# ---------------------------------------------------------------------------
class FakeAxisCard:

    def __init__(self, page, index):
        self.page = page
        self.index = index
        reg = page.app.registry
        self.device = FakeCombo(reg.display_list(), reg.display_list()[0])
        self.parameter = FakeCombo(reg.set_options(self.device_address()))
        self.start = FakeEntry(0.0)
        self.stop = FakeEntry(1.0)
        self.mode = FakeCombo(["rate, units/s", "step, units/pt"])
        self.rate = FakeEntry(1.0)
        self.delay = FakeEntry(0.01)
        self.walks = FakeSpin(1)
        self.snake = FakeVar(False)
        self.stepwise = FakeVar(False)
        self.back_rate = FakeEntry("", allow_empty=True)
        self.back_delay = FakeEntry("", allow_empty=True)
        self.manual_label = FakeLabel("auto grid")
        self.manual_btn = FakeButton(self._load_manual)
        self.clear_manual_btn = FakeButton(lambda: None)
        self.apply_btn = FakeButton(self._apply_live, state="disabled")
        self.manual_points = None

    def device_address(self):
        return self.page.app.registry.address_from_display(self.device.get())

    def _device_changed(self):
        options = self.page.app.registry.set_options(self.device_address())
        self.parameter.configure(values=options or [""])
        self.parameter.set(options[0] if options else "")

    def _load_manual(self):
        path = filedialog.askopenfilename(title="Manual steps file")
        if not path:
            return
        self.manual_label.configure(text=os.path.basename(path))

    def _apply_live(self):
        self.page.applied.append(self.index)

    def to_axis(self):
        from unisweep.core.config import AxisProgram
        values = {"start": self.start.value(), "stop": self.stop.value(),
                  "rate": self.rate.value(), "delay": self.delay.value()}
        if any(v is None for v in values.values()):
            return None
        return AxisProgram(
            device=self.device_address(), parameter=self.parameter.get(),
            count_mode=(CountMode.STEP if self.mode.current() == 1
                        else CountMode.RATE),
            back_rate=self.back_rate.value(),
            back_delay=self.back_delay.value(),
            walks=int(float(self.walks.get())), snake=self.snake.get(),
            force_stepwise=self.stepwise.get(), **values)

    def controls(self, page="sweep"):
        p = f"sweep.axis{self.index + 1}"
        return [
            ctl.choice(f"{p}.device", self.device, page=page,
                       label="Device", after_set=self._device_changed),
            ctl.choice(f"{p}.parameter", self.parameter, page=page,
                       label="Parameter"),
            ctl.number(f"{p}.start", self.start, page=page, label="From"),
            ctl.number(f"{p}.stop", self.stop, page=page, label="To"),
            ctl.choice(f"{p}.mode", self.mode, page=page, label="Mode"),
            ctl.number(f"{p}.rate", self.rate, page=page, label="Rate"),
            ctl.number(f"{p}.delay", self.delay, page=page, label="Delay"),
            ctl.spin(f"{p}.walks", self.walks, page=page, label="Walks",
                     minimum=1, maximum=999),
            ctl.flag(f"{p}.snake", self.snake, page=page, label="Snake"),
            ctl.flag(f"{p}.force_stepwise", self.stepwise, page=page,
                     label="Force stepwise"),
            ctl.number(f"{p}.back_rate", self.back_rate, page=page,
                       label="Return rate", allow_empty=True),
            ctl.number(f"{p}.back_delay", self.back_delay, page=page,
                       label="Return delay", allow_empty=True),
            ctl.readout(f"{p}.manual_steps",
                        lambda: self.manual_label.cget("text"), page=page,
                        label="Manual steps"),
            ctl.action(f"{p}.load_manual_steps", self.manual_btn, page=page,
                       label="Load manual steps"),
            ctl.action(f"{p}.apply", self.apply_btn, page=page,
                       label="Apply", disabled_hint="only while running"),
        ]


class FakeSweepPage:

    def __init__(self, app):
        self.app = app
        self.running = False
        self.applied = []
        self.dims = FakeCombo(["1D", "2D", "3D"], "1D")
        self.start_btn = FakeButton(self._start)
        self.pause_btn = FakeButton(self._pause, state="disabled")
        self.stop_btn = FakeButton(self._stop, state="disabled")
        self.zero_btn = FakeButton(self._to_zero, state="disabled")
        self.condition = FakeText()
        self.reads_list = FakeListbox(app.registry.read_catalogue())
        self.filename = FakeEntry("", validator=str, allow_empty=True)
        self.script = FakeText()
        self.script_name = ""
        self.script_label = FakeLabel("no file")
        self.load_script_btn = FakeButton(self._load_script)
        self.save_script_btn = FakeButton(self._save_script)
        self.axis_cards = [FakeAxisCard(self, i) for i in range(3)]

    @property
    def n_dims(self):
        return self.dims.current() + 1

    def _set_dims(self):
        return

    def selected_reads(self):
        return tuple(self.reads_list.get(i)
                     for i in self.reads_list.curselection())

    def _load_script(self):
        path = filedialog.askopenfilename(title="Load a per-point script")
        if not path:
            return
        with open(path, "r", encoding="utf-8") as fh:
            self.script.delete("1.0", "end")
            self.script.insert("1.0", fh.read())
        self.script_label.configure(text=os.path.basename(path))

    def _save_script(self):
        path = filedialog.asksaveasfilename(title="Save the script")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.script.get("1.0", "end").rstrip() + "\n")
        self.script_label.configure(text=os.path.basename(path))

    def build_program(self):
        axes = []
        for card in self.axis_cards[: self.n_dims]:
            axis = card.to_axis()
            if axis is None:
                messagebox.showwarning(
                    "Sweep", "Fix the highlighted axis fields first.")
                return None
            axes.append(axis)
        reads = self.selected_reads()
        if not reads:
            messagebox.showwarning("Sweep",
                                   "Select at least one read parameter.")
            return None
        return SweepProgram(
            axes=tuple(axes), reads=reads,
            condition=self.condition.get("1.0", "end").strip(),
            script=self.script.get("1.0", "end").strip(),
            filename=(self.filename.value() or ""))

    def set_running(self, running):
        self.running = running
        self.start_btn.state = "disabled" if running else "normal"
        for button in (self.pause_btn, self.stop_btn, self.zero_btn):
            button.state = "normal" if running else "disabled"
        for card in self.axis_cards:
            card.apply_btn.state = "normal" if running else "disabled"

    # ---- the buttons -------------------------------------------------
    def _start(self):
        program = self.build_program()
        if program is None:
            return
        if self.app.start_warning:
            answer = messagebox.askyesnocancel(
                "Start warning",
                "GATE.Volt is at 2.5 — sweep starts at 0. Go to start?")
            if answer is None:
                self.app.status("Sweep cancelled")
                return
            if answer is False:
                import dataclasses
                program = dataclasses.replace(program, approach_start=False)
        if self.app.start_sweep(program) is not None:
            self.set_running(True)

    def _pause(self):
        self.app.toggle_pause()

    def _stop(self):
        self.app.stop_sweep()

    def _to_zero(self):
        if messagebox.askyesno("To zero",
                               "Ramp all sweep devices to zero and stop?"):
            self.app.to_zero()

    def controls(self):
        page = "sweep"
        out = [
            ctl.choice("sweep.dimensions", self.dims, page=page,
                       label="Dimensions", after_set=self._set_dims),
            ctl.action("sweep.start", self.start_btn, page=page,
                       label="Start sweep"),
            ctl.action("sweep.pause", self.pause_btn, page=page,
                       label="Pause", disabled_hint="only while running"),
            ctl.action("sweep.stop", self.stop_btn, page=page,
                       label="Stop", disabled_hint="only while running"),
            ctl.action("sweep.to_zero", self.zero_btn, page=page,
                       label="To zero", disabled_hint="only while running"),
            ctl.text_field("sweep.condition", self.condition, page=page,
                           label="Condition"),
            ctl.multichoice("sweep.reads", self.reads_list, page=page,
                            label="Read parameters"),
            ctl.entry_text("sweep.filename", self.filename, page=page,
                           label="Filename"),
            ctl.text_field("sweep.script", self.script, page=page,
                           label="Script"),
            ctl.action("sweep.load_script", self.load_script_btn, page=page,
                       label="Load a per-point script"),
            ctl.action("sweep.save_script", self.save_script_btn, page=page,
                       label="Save the per-point script"),
            ctl.readout("sweep.script_file",
                        lambda: self.script_label.cget("text"), page=page,
                        label="Script file"),
            ctl.readout("sweep.running", lambda: bool(self.running),
                        page=page, label="Running"),
        ]
        for card in self.axis_cards[: self.n_dims]:
            out.extend(card.controls(page))
        return out


class FakeApp:
    """Enough of ``unisweep.gui.app.App`` for the agent surface."""

    def __init__(self, core_dir, mocks, profile=None):
        self.core_dir = core_dir
        self.root = None
        self.profile = profile or LabProfile.empty()
        self.registry = MockRegistry(core_dir, mocks,
                                     LimitPolicy(self.profile))
        self.event_tap = EventTap()
        self.event_queue = queue.Queue()
        self.engine = None
        self.live = None
        self.start_warning = False
        self.messages = []
        self._current_page = "Sweep"
        self.pages = {"Sweep": FakeSweepPage(self)}
        self._pump = threading.Thread(target=self._drain, daemon=True)
        self._stop_pump = threading.Event()
        self._pump.start()

    # ---- app plumbing ------------------------------------------------
    def status(self, text):
        self.messages.append(text)

    def show_page(self, name):
        self._current_page = name

    def profile_summary(self):
        return ("no lab profile" if self.profile.is_empty
                else f"lab profile '{self.profile.lab}'")

    def controls(self):
        out = [
            ctl.selection("app.page", lambda: self._current_page,
                          self.show_page, lambda: list(self.pages),
                          page="app", label="Visible page"),
            ctl.readout("app.status",
                        lambda: self.messages[-1] if self.messages else "",
                        page="app", label="Status line"),
            ctl.readout("app.lab_profile", self.profile_summary, page="app",
                        label="Lab profile"),
        ]
        for page in self.pages.values():
            out.extend(page.controls())
        return out

    # ---- sweep lifecycle ---------------------------------------------
    def start_sweep(self, program):
        from unisweep.core.config import LiveProgram
        if self.engine is not None and self.engine.is_alive():
            return None
        self.live = LiveProgram(program)
        self.engine = SweepEngine(self.live, self.registry, self.core_dir,
                                  self.event_queue, profile=self.profile)
        self.engine.start()
        return self.live

    def toggle_pause(self):
        if self.engine is not None:
            self.engine.set_paused(not self.engine.pause_ev.is_set())

    def stop_sweep(self):
        if self.engine is not None:
            self.engine.stop()

    def to_zero(self):
        if self.engine is not None:
            self.engine.to_zero()

    def _drain(self):
        while not self._stop_pump.is_set():
            try:
                event = self.event_queue.get(timeout=0.05)
            except queue.Empty:
                continue
            self.event_tap.record(event)
            if isinstance(event, ev.SweepFinished):
                self.pages["Sweep"].set_running(False)

    def close(self):
        self._stop_pump.set()

    def wait_idle(self, timeout=30):
        engine = self.engine
        if engine is not None:
            engine.join(timeout)
        deadline = time.perf_counter() + 5
        while (self.event_tap.state == "running"
               and time.perf_counter() < deadline):
            time.sleep(0.02)


# ---------------------------------------------------------------------------
@pytest.fixture
def session():
    tmp = tempfile.mkdtemp(prefix="unisweep_agent_")
    profile = LabProfile.from_dict(GATE_PROFILE)
    app = FakeApp(tmp, {"GATE": LeakyGate()}, profile)
    yield AgentSession(app, bridge=DirectBridge())
    app.close()


# ===========================================================================
# controls
# ===========================================================================
def test_every_knob_is_listed_with_its_value_and_options(session):
    listing = session.list_controls()
    names = {c["name"] for c in listing["controls"]}
    assert {"sweep.start", "sweep.dimensions", "sweep.axis1.start",
            "sweep.reads", "app.page"} <= names
    by_name = {c["name"]: c for c in listing["controls"]}
    assert by_name["sweep.dimensions"]["options"] == ["1D", "2D", "3D"]
    assert by_name["sweep.axis1.start"]["value"] == 0.0
    assert by_name["sweep.start"]["kind"] == "action"
    assert "value" not in by_name["sweep.start"]
    assert by_name["sweep.stop"]["enabled"] is False   # no sweep running
    assert "sweep" in listing["pages"] and "app" in listing["pages"]


def test_typing_into_fields_reads_back(session):
    applied = session.set_controls({
        "sweep.axis1.start": -1.5,
        "sweep.axis1.stop": "2.5",
        "sweep.axis1.walks": 3,
        "sweep.axis1.snake": "yes",
        "sweep.condition": "x > 0",
        "sweep.filename": "run_a",
    })
    assert applied["sweep.axis1.start"] == -1.5
    assert applied["sweep.axis1.stop"] == 2.5
    assert applied["sweep.axis1.walks"] == 3
    assert applied["sweep.axis1.snake"] is True
    values = session.read_controls(["sweep.condition", "sweep.filename"])
    assert values == {"sweep.condition": "x > 0",
                      "sweep.filename": "run_a"}


def test_a_bad_value_is_refused_by_name(session):
    with pytest.raises(ControlError) as excinfo:
        session.set_controls({"sweep.axis1.start": "banana"})
    assert "not a number" in str(excinfo.value)
    with pytest.raises(ControlError) as excinfo:
        session.set_controls({"sweep.dimensions": "7D"})
    assert "not one of the options" in str(excinfo.value)


def test_a_rejected_batch_leaves_nothing_applied(session):
    before = session.read_controls(["sweep.axis1.start"])
    with pytest.raises(UnknownControl):
        session.set_controls({"sweep.axis1.start": 9.0,
                              "sweep.axis1.nonsense": 1})
    assert session.read_controls(["sweep.axis1.start"]) == before


def test_unknown_control_suggests_the_real_names(session):
    with pytest.raises(UnknownControl) as excinfo:
        session.read_controls(["sweep.axis1.from"])
    assert "no control named" in str(excinfo.value)
    with pytest.raises(UnknownControl) as excinfo:
        session.read_controls(["sweep.axis1.walk"])
    assert "walks" in str(excinfo.value)


@pytest.mark.parametrize("separator", [" \u2014 ", " - ", " \u2013 ",
                                       " | ", "  "])
def test_a_bare_address_matches_whatever_separates_the_label(separator):
    """The separator in 'ADDRESS — Driver' is a display detail, and the
    option strings come back out of Tk — so the rule must never name it.
    Splitting on a literal ' \u2014 ' looked equivalent and was not."""
    options = ["Time", f"SMU{separator}Mock", f"LOCKIN{separator}Mock",
               "BARE"]
    assert ctl._match_option("SMU", options, "x") == options[1]
    assert ctl._match_option("smu", options, "x") == options[1]
    assert ctl._match_option("BARE", options, "x") == "BARE"
    assert ctl._match_option(options[1], options, "x") == options[1]


def test_a_prefix_that_is_not_a_boundary_is_not_a_match():
    with pytest.raises(ControlError):
        ctl._match_option("SMU", ["SMU2 - a", "NOPE"], "x")


def test_an_unmatched_option_reports_the_raw_strings():
    """A look-alike character is invisible in a console; repr is not."""
    with pytest.raises(ControlError) as excinfo:
        ctl._match_option("SMU", ["SMUX - a", "SMUY - b"], "x")
    message = str(excinfo.value)
    assert "closest" in message
    assert repr("SMUX - a") in message


def test_device_choice_accepts_the_bare_address_and_repopulates(session):
    session.set_controls({"sweep.axis1.device": "GATE"})
    values = session.read_controls(["sweep.axis1.device",
                                    "sweep.axis1.parameter"])
    assert values["sweep.axis1.device"].startswith("GATE")
    assert values["sweep.axis1.parameter"] == "Volt"


def test_multi_select_lists_take_a_subset(session):
    session.set_controls({"sweep.reads": ["GATE.Leak"]})
    assert session.read_controls(["sweep.reads"])["sweep.reads"] == \
        ["GATE.Leak"]
    with pytest.raises(ControlError):
        session.set_controls({"sweep.reads": ["GATE.NotAThing"]})


def test_writing_to_a_button_is_refused(session):
    with pytest.raises(ControlError) as excinfo:
        session.set_controls({"sweep.start": True})
    assert "not something that can be typed into" in str(excinfo.value)


def test_pressing_a_greyed_out_button_says_so(session):
    with pytest.raises(ControlError) as excinfo:
        session.press("sweep.stop")
    assert "greyed out" in str(excinfo.value)
    assert "only while running" in str(excinfo.value)


# ===========================================================================
# dialogs
# ===========================================================================
def test_an_informational_dialog_comes_back_as_data(session):
    """No reads selected: the page complains, and the complaint is the
    answer rather than a window nobody can see."""
    result = session.press("sweep.start")
    assert result["ok"] is True
    assert result["dialogs"]
    assert "read parameter" in result["dialogs"][0]["message"]
    assert session.status()["state"] == "idle"


def test_a_question_without_an_answer_aborts_and_says_what_was_asked(session):
    session.app.start_warning = True
    _arm(session)
    result = session.press("sweep.start")
    assert result["ok"] is False
    assert result["needs_answer"]["function"] == "askyesnocancel"
    assert "Go to start?" in result["needs_answer"]["message"]
    assert "answers=" in result["error"]
    assert session.status()["state"] == "idle"      # nothing was started


def test_a_scripted_answer_gets_through(session):
    session.app.start_warning = True
    _arm(session)
    result = session.press("sweep.start", answers=["yes"])
    assert result["ok"] is True
    answered = [d for d in result["dialogs"]
                if d["function"] == "askyesnocancel"]
    assert answered and answered[0]["answer"] is True
    session.app.wait_idle()


def test_a_file_dialog_takes_a_path(session):
    result = session.press("sweep.axis1.load_manual_steps",
                           files=["/tmp/steps.csv"])
    assert result["ok"] is True
    assert session.read_controls(
        ["sweep.axis1.manual_steps"])["sweep.axis1.manual_steps"] == \
        "steps.csv"
    refused = session.press("sweep.axis1.load_manual_steps")
    assert refused["ok"] is False
    assert refused["needs_answer"]["function"] == "askopenfilename"


def test_dialog_proxies_are_removed_afterwards():
    module = sys.modules[__name__]
    original = module.messagebox
    with dlg.intercept(answers=["yes"], modules=[__name__]):
        assert module.messagebox is not original
        assert module.messagebox.askyesno("t", "m") is True
    assert module.messagebox is original


# ===========================================================================
# the bridge
# ===========================================================================
class _FakeRoot:
    """A root whose ``after`` runs the callback on a worker thread."""

    def __init__(self, run=True):
        self.run = run

    def after(self, _ms, fn):
        if self.run:
            threading.Thread(target=fn, daemon=True).start()


def test_the_bridge_runs_work_on_the_owning_thread_and_returns_it():
    bridge = TkBridge(_FakeRoot())
    box = {}

    def worker():
        box["value"] = bridge.call(lambda a, b: a * b, 6, 7)

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join(5)
    assert box["value"] == 42


def test_the_bridge_re_raises_what_the_ui_raised():
    bridge = TkBridge(_FakeRoot())
    box = {}

    def worker():
        try:
            bridge.call(lambda: (_ for _ in ()).throw(ValueError("boom")))
        except ValueError as exc:
            box["error"] = str(exc)

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join(5)
    assert box["error"] == "boom"


def test_a_wedged_ui_times_out_instead_of_hanging_for_ever():
    bridge = TkBridge(_FakeRoot(run=False), timeout=0.2)
    box = {}

    def worker():
        try:
            bridge.call(lambda: None)
        except BridgeTimeout as exc:
            box["error"] = str(exc)

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join(5)
    assert "dialog" in box["error"]


# ===========================================================================
# the event tap
# ===========================================================================
def test_the_tap_summarises_instead_of_hoarding():
    tap = EventTap(capacity=10, keep_points=3)
    tap.record(ev.SweepStarted(columns=("time", "v"), dimensions=1,
                               planned_points=100))
    for i in range(20):
        tap.record(ev.PointMeasured(row=(i, float(i)), axis_values=(i,),
                                    file="f.csv", walk=1))
    snapshot = tap.snapshot(points=3)
    assert snapshot["state"] == "running"
    assert snapshot["planned_points"] == 100
    assert len(snapshot["last_points"]) == 3       # not 20
    assert snapshot["last_points"][-1]["axis_values"] == [19]


def test_the_tap_pages_forward_and_admits_what_it_dropped():
    tap = EventTap(capacity=5)
    for i in range(12):
        tap.record(ev.AxisStepped(axis=1, value=float(i)))
    page = tap.since(0, limit=3)
    assert len(page["events"]) == 3 and page["more"] is True
    assert tap.since(page["next"], limit=99)["events"][0]["seq"] > \
        page["next"]
    assert tap.since(1)["dropped_before"] > 1


def test_the_tap_never_raises_on_junk():
    tap = EventTap()
    tap.record(object())
    tap.record(None)
    assert tap.sequence == 2


# ===========================================================================
# the session: filling in the page and running it
# ===========================================================================
def _arm(session, **overrides):
    """Put a runnable 1-D gate sweep on the page."""
    program = {
        "axes": [{"device": "GATE", "parameter": "Volt", "start": 0.0,
                  "stop": 1.0, "rate": 0.5, "delay": 0.005,
                  "count_mode": "step"}],
        "reads": ["GATE.Leak"],
    }
    program.update(overrides)
    return session.apply_program(program)


def test_a_program_is_typed_onto_the_page_field_by_field(session):
    script = "if abs(reads['GATE.Leak']) > 2e-9:\n    stop()"
    result = _arm(session, filename="run_a", script=script)
    assert result["valid"] is True
    values = session.read_controls([
        "sweep.axis1.device", "sweep.axis1.stop", "sweep.axis1.mode",
        "sweep.reads", "sweep.filename", "sweep.script"])
    assert values["sweep.axis1.stop"] == 1.0
    assert values["sweep.axis1.mode"] == "step, units/pt"
    assert values["sweep.reads"] == ["GATE.Leak"]
    assert values["sweep.filename"] == "run_a"
    assert values["sweep.script"] == script
    # ...and the page now builds exactly that program
    assert result["program"]["axes"][0]["parameter"] == "Volt"
    assert result["program"]["script"] == script


def test_dimensions_are_set_before_the_axis_cards_they_create(session):
    session.apply_program({
        "axes": [{"device": "GATE", "parameter": "Volt", "stop": 1.0},
                 {"device": "GATE", "parameter": "Volt", "stop": 2.0}],
        "reads": ["GATE.Leak"]})
    assert session.read_controls(
        ["sweep.dimensions"])["sweep.dimensions"] == "2D"
    assert "sweep.axis2.stop" in session.registry()


def test_a_manual_step_table_is_reported_as_needing_a_file(session):
    result = session.apply_program({
        "axes": [{"device": "GATE", "parameter": "Volt",
                  "manual_points": [0.0, 0.5, 1.0]}],
        "reads": ["GATE.Leak"]})
    assert any("load_manual_steps" in note for note in result["notes"])


def test_an_incomplete_page_reports_the_complaint_not_a_program(session):
    # a human clearing a required field, which the control layer itself
    # refuses to do (see test_a_bad_value_is_refused_by_name)
    session.app.pages["Sweep"].axis_cards[0].start.set("")
    current = session.get_program()
    assert current["valid"] is False
    assert current["complaints"]
    assert "highlighted" in current["complaints"][0]["message"]


def test_dry_run_prices_the_sweep_without_touching_anything(session):
    _arm(session, axes=[{"device": "GATE", "parameter": "Volt",
                         "start": 0.0, "stop": 1.0, "rate": 0.1,
                         "delay": 0.5, "count_mode": "step"}])
    preview = session.dry_run()
    assert preview["ok"] is True
    assert preview["planned_points"] == 11
    assert preview["estimated_seconds"] == pytest.approx(5.5, abs=0.1)
    assert preview["estimated_duration"] == "5 s"
    assert session.app.registry._mocks["GATE"].set_log == []


def test_dry_run_refuses_what_the_profile_forbids(session):
    _arm(session, axes=[{"device": "GATE", "parameter": "Volt",
                         "start": 0.0, "stop": 40.0, "rate": 1.0,
                         "delay": 0.01, "count_mode": "step"}])
    preview = session.dry_run()
    assert preview["ok"] is False
    assert "outside the allowed range" in preview["reason"]
    assert any(p["level"] == "error" for p in preview["problems"])


def test_dry_run_reports_whether_a_script_is_attached(session):
    _arm(session)
    assert session.dry_run()["has_script"] is False
    _arm(session, script="pass")
    preview = session.dry_run()
    assert preview["has_script"] is True
    assert preview["ok"] is True


def test_dry_run_refuses_a_script_the_profile_forbids(session):
    session.app.profile = LabProfile.from_dict(
        dict(GATE_PROFILE, interlocks={"allow_script": False}))
    _arm(session, script="pass")
    preview = session.dry_run()
    assert preview["ok"] is False
    assert "allow_script" in preview["reason"]


def test_run_sweep_fills_in_presses_start_and_reports_what_happened(session):
    result = session.run_sweep({
        "axes": [{"device": "GATE", "parameter": "Volt", "start": 0.0,
                  "stop": 1.0, "rate": 0.25, "delay": 0.005,
                  "count_mode": "step"}],
        "reads": ["GATE.Leak"]})
    assert result["started"] is True
    session.app.wait_idle()
    status = session.status()
    assert status["state"] == "finished"
    assert status["finished"]["stopped"] is False
    assert status["progress"]["done"] == 5
    assert session.app.registry._mocks["GATE"].set_log[-1] == 1.0


def test_run_sweep_refuses_before_anything_moves(session):
    result = session.run_sweep({
        "axes": [{"device": "GATE", "parameter": "Volt", "start": 0.0,
                  "stop": 40.0, "rate": 1.0, "delay": 0.01,
                  "count_mode": "step"}],
        "reads": ["GATE.Leak"]})
    assert result["started"] is False
    assert "outside the allowed range" in result["reason"]
    assert session.app.registry._mocks["GATE"].set_log == []


def test_a_script_that_stops_the_sweep_shows_up_in_the_status(session):
    """The whole point of the script route: a measured value ends the run,
    and the assistant can see that it did."""
    result = session.run_sweep({
        "axes": [{"device": "GATE", "parameter": "Volt", "start": 0.0,
                  "stop": 10.0, "rate": 0.5, "delay": 0.005,
                  "count_mode": "step"}],
        "reads": ["GATE.Leak"],
        "script": "if abs(reads['GATE.Leak']) > 2e-9:\n    stop()"})
    assert result["started"] is True
    session.app.wait_idle()
    status = session.status()
    assert status["finished"]["stopped"] is True
    assert session.app.registry._mocks["GATE"].set_log[-1] < 5.0


def test_a_script_can_be_loaded_and_saved_through_the_buttons(session,
                                                              tmp_path):
    path = str(tmp_path / "abort.py")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("if abs(reads['GATE.Leak']) > 2e-9:\n    stop()\n")
    loaded = session.press("sweep.load_script", files=[path])
    assert loaded["ok"] is True
    values = session.read_controls(["sweep.script", "sweep.script_file"])
    assert "stop()" in values["sweep.script"]
    assert values["sweep.script_file"] == "abort.py"

    out = str(tmp_path / "copy.py")
    saved = session.press("sweep.save_script", files=[out])
    assert saved["ok"] is True
    assert "stop()" in open(out, encoding="utf-8").read()
    # ...and with no path the GUI's file dialog asks, rather than guessing
    refused = session.press("sweep.save_script")
    assert refused["ok"] is False
    assert refused["needs_answer"]["function"] == "asksaveasfilename"


def test_stopping_uses_the_stop_button(session):
    session.run_sweep({
        "axes": [{"device": "GATE", "parameter": "Volt", "start": 0.0,
                  "stop": 5.0, "rate": 0.05, "delay": 0.05,
                  "count_mode": "step"}],
        "reads": ["GATE.Leak"]})
    time.sleep(0.15)
    assert session.stop()["ok"] is True
    session.app.wait_idle()
    assert session.status()["finished"]["stopped"] is True


def test_to_zero_needs_saying_so_twice(session):
    session.run_sweep({
        "axes": [{"device": "GATE", "parameter": "Volt", "start": 0.0,
                  "stop": 5.0, "rate": 0.05, "delay": 0.05,
                  "count_mode": "step"}],
        "reads": ["GATE.Leak"]})
    with pytest.raises(SessionError) as excinfo:
        session.to_zero()
    assert "confirm=true" in str(excinfo.value)
    assert session.to_zero(confirm=True)["ok"] is True
    session.app.wait_idle()
    assert session.app.registry._mocks["GATE"].set_log[-1] == 0.0


def test_a_running_sweep_can_be_retuned_through_its_apply_button(session):
    session.run_sweep({
        "axes": [{"device": "GATE", "parameter": "Volt", "start": 0.0,
                  "stop": 5.0, "rate": 0.05, "delay": 0.05,
                  "count_mode": "step"}],
        "reads": ["GATE.Leak"]})
    time.sleep(0.1)
    result = session.edit_running_sweep(axis=1, stop=0.2)
    assert "sweep.axis1.stop" in result["edited"]
    assert result["press"]["ok"] is True
    assert 0 in session.app.pages["Sweep"].applied
    session.stop()
    session.app.wait_idle()


def test_editing_with_no_sweep_running_says_so(session):
    with pytest.raises(SessionError) as excinfo:
        session.edit_running_sweep(axis=1, stop=1.0)
    assert "no sweep is running" in str(excinfo.value)


# ===========================================================================
# the rig
# ===========================================================================
def test_describe_rig_speaks_the_lab_s_language(session):
    described = session.describe_rig()
    assert described["has_profile"] is True
    assert described["limits_enforced"] is True
    assert "Vbg" in described["profile"]
    assert "GATE.Leak" in described["readable_channels"]
    gate = described["instruments"][0]
    assert gate["address"] == "GATE" and gate["alias"] == "gate"
    by_name = {p["parameter"]: p for p in gate["parameters"]}
    assert by_name["Volt"]["alias"] == "Vbg"
    assert by_name["Volt"]["range"] == "[-12, 12] V"
    assert by_name["Leak"]["settable"] is False
    assert by_name["Leak"]["channel"] == "GATE.Leak"


def test_reading_channels_adds_the_derived_ones(session):
    session.app.profile = LabProfile.from_dict(
        dict(GATE_PROFILE, derived={"Ileak_pA": {"expression":
                                                 "Ileak * 1e12"}}))
    session.set_parameter("GATE", "Volt", 1.0)
    result = session.read_channels(["GATE.Leak"])
    assert result["values"]["GATE.Leak"] > 0
    assert result["derived"]["Ileak_pA"] == pytest.approx(
        result["values"]["GATE.Leak"] * 1e12)


def test_setting_a_parameter_by_alias_goes_through_the_limits(session):
    from unisweep.core.limits import LimitViolation
    result = session.set_parameter("Vbg", value=2.0)
    assert result["address"] == "GATE" and result["parameter"] == "Volt"
    assert result["value"] == 2.0
    assert result["label"] == "Vbg [V]"
    with pytest.raises(LimitViolation):
        session.set_parameter("Vbg", value=40.0)


def test_an_unknown_parameter_name_is_explained(session):
    with pytest.raises(SessionError) as excinfo:
        session.set_parameter("Vsomething", value=1.0)
    assert "does not name a settable parameter" in str(excinfo.value)


# ===========================================================================
# the real GUI pages (source-level: no display needed)
# ===========================================================================
GUI_FILES = ["app.py", "sweep_page.py", "setget_page.py", "devices_page.py",
             "settings_page.py"]


def _classes_with_controls(path):
    tree = ast.parse(open(path, encoding="utf-8").read())
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for item in node.body:
            if isinstance(item, ast.FunctionDef) and item.name == "controls":
                yield node, item


def test_real_pages_only_bind_widgets_that_exist():
    """Every ``self.x`` a real controls() reaches for must be assigned.

    A typo here would only show up when someone opened that page with an
    assistant attached; this catches it from the source, on a machine with
    no display.
    """
    gui = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "unisweep", "gui")
    checked = 0
    for filename in GUI_FILES:
        path = os.path.join(gui, filename)
        for klass, method in _classes_with_controls(path):
            defined = {m.name for m in klass.body
                       if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))}
            for node in ast.walk(klass):
                if isinstance(node, ast.Attribute) and \
                        isinstance(node.value, ast.Name) and \
                        node.value.id == "self" and \
                        isinstance(node.ctx, ast.Store):
                    defined.add(node.attr)
            used = {n.attr for n in ast.walk(method)
                    if isinstance(n, ast.Attribute)
                    and isinstance(n.value, ast.Name)
                    and n.value.id == "self"}
            missing = sorted(used - defined)
            assert not missing, (f"{filename}:{klass.name}.controls() uses "
                                 f"undefined attributes: {missing}")
            checked += 1
    assert checked >= 5, "expected a controls() on every page"


def test_real_pages_declare_unique_control_names():
    """Two controls with one name would silently shadow each other."""
    gui = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "unisweep", "gui")
    seen = {}
    for filename in GUI_FILES:
        path = os.path.join(gui, filename)
        for klass, method in _classes_with_controls(path):
            for node in ast.walk(method):
                if not (isinstance(node, ast.Call) and node.args):
                    continue
                first = node.args[0]
                if isinstance(first, ast.Constant) and \
                        isinstance(first.value, str) and "." in first.value:
                    where = f"{filename}:{klass.name}"
                    assert first.value not in seen or seen[first.value] == \
                        where, (f"control '{first.value}' is declared in "
                                f"both {seen.get(first.value)} and {where}")
                    seen[first.value] = where
    assert len(seen) > 40, f"only {len(seen)} named controls found"


# ===========================================================================
# the lab journal and provenance
# ===========================================================================
def test_the_page_asks_for_nothing_but_the_filename(session):
    """The output card is one field. Anything that would have to be typed
    to explain a run — an intent, a campaign — is gone on purpose: the
    record is read off the sweep instead."""
    result = _arm(session, filename="gate_sweep")
    assert session.read_controls(["sweep.filename"])["sweep.filename"] == \
        "gate_sweep"
    assert result["program"]["filename"] == "gate_sweep"
    for gone in ("sweep.intent", "sweep.campaign"):
        with pytest.raises(UnknownControl):
            session.read_controls([gone])


def test_a_run_started_by_the_assistant_files_what_it_did(session):
    from unisweep.core.provenance import read_sidecar
    started = session.run_sweep({
        "axes": [{"device": "GATE", "parameter": "Volt", "start": 0.0,
                  "stop": 1.0, "rate": 0.25, "delay": 0.005,
                  "count_mode": "step", "walks": 1}],
        "reads": ["GATE.Leak"]})
    assert started["started"] is True
    session.app.wait_idle()

    runs = session.journal_runs()["runs"]
    assert runs and runs[0]["points"] == 5
    assert runs[0]["swept"] == ["GATE.Volt 0.0 to 1.0"]
    assert runs[0]["reads"] == ["GATE.Leak"]
    assert runs[0]["stopped"] is False

    record = session.journal_run(runs[0]["run_id"])
    assert record["files"], "the run must record the files it wrote"
    assert record["program"]["axes"][0]["parameter"] == "Volt"
    assert record["instruments"]["GATE"]["driver"] == "LeakyGate"
    sidecar = read_sidecar(record["files"][0])
    assert sidecar["run_id"] == runs[0]["run_id"]


def test_the_assistant_can_write_in_the_notebook(session):
    written = session.journal_note("leakage runs away above +4 V")
    assert written["written"] is True
    text = open(written["file"], encoding="utf-8").read()
    assert "leakage runs away above +4 V" in text
    assert "assistant" in text
    assert session.journal.notes()[0]["author"] == "assistant"


def test_file_provenance_reads_the_sidecar_back(session):
    session.run_sweep({
        "axes": [{"device": "GATE", "parameter": "Volt", "start": 0.0,
                  "stop": 0.5, "rate": 0.25, "delay": 0.005,
                  "count_mode": "step", "walks": 1}],
        "reads": ["GATE.Leak"]})
    session.app.wait_idle()
    path = session.journal_runs()["runs"][0]["files"][0]
    record = session.file_provenance(path)
    assert record["columns"] == ["time", "GATE.Volt_sweep", "GATE.Leak"]
    assert record["instruments"]["GATE"]["driver"] == "LeakyGate"
    assert record["lab_profile"]["parameters"]["GATE.Volt"]["alias"] == "Vbg"


def test_asking_for_provenance_that_is_not_there_explains_itself(session):
    with pytest.raises(SessionError) as excinfo:
        session.file_provenance("/nowhere/at/all.csv")
    assert "no provenance sidecar" in str(excinfo.value)
    with pytest.raises(SessionError):
        session.journal_run("not-a-run")


def test_describe_rig_shows_what_has_been_measured_lately(session):
    session.run_sweep({
        "axes": [{"device": "GATE", "parameter": "Volt", "start": 0.0,
                  "stop": 0.5, "rate": 0.25, "delay": 0.005,
                  "count_mode": "step", "walks": 1}],
        "reads": ["GATE.Leak"]})
    session.app.wait_idle()
    described = session.describe_rig()
    recent = described["recent_runs"][0]
    assert recent["swept"] == ["GATE.Volt 0.0 to 0.5"]
    assert recent["reads"] == ["GATE.Leak"]
    assert recent["points"] == 3 and recent["files"]

