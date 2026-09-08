"""The control binders against REAL Tk widgets.

``tests/test_agent.py`` proves the *logic* of the control layer against
duck-typed stand-ins, which is what lets it run anywhere. This module
proves the *binding*: that a real ttk widget behaves the way the binder
assumes it does.

That gap was not academic. ``ttk.Button.invoke()`` does not propagate an
exception raised inside the command — tkinter catches it, hands it to the
root's ``report_callback_exception`` and returns normally — so every
press reported success, including presses that failed and presses that
asked a question nobody answered. A fake button calls its command
directly and raises, so no amount of testing against fakes could ever
have found it.

Skipped automatically without tkinter or a display; under Linux run it as

    xvfb-run -a python -m pytest tests/test_controls_tk.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

tk = pytest.importorskip("tkinter")
from tkinter import ttk                                       # noqa: E402

from unisweep.agent import controls as ctl                    # noqa: E402
from unisweep.agent import dialogs as dlg                     # noqa: E402
from unisweep.agent.bridge import DirectBridge                # noqa: E402
from unisweep.agent.controls import ControlError, ControlRegistry  # noqa: E402
from unisweep.gui.theme import apply_theme, init_theme        # noqa: E402
from unisweep.gui.widgets import ValidatedEntry               # noqa: E402

dlg.EXTRA_MODULES.add(__name__)
from tkinter import filedialog, messagebox                    # noqa: E402


@pytest.fixture(scope="module")
def root():
    try:
        window = tk.Tk()
    except tk.TclError as exc:                    # pragma: no cover
        pytest.skip(f"no usable display: {exc}")
    window.withdraw()
    init_theme("dark")
    apply_theme(window)
    yield window
    try:
        window.destroy()
    except tk.TclError:                           # pragma: no cover
        pass


def one(control):
    return ControlRegistry(DirectBridge(), [control])


# ---------------------------------------------------------------------------
# the bug this module exists for
# ---------------------------------------------------------------------------
def test_a_real_button_reports_what_its_command_raised(root):
    """Tk swallows callback exceptions; press() must not read that as
    success — an assistant told 'ok' for a press that failed is worse
    than one told nothing."""
    def boom():
        raise RuntimeError("the GUI refused")

    button = ttk.Button(root, command=boom)
    result = one(ctl.action("x.go", button, label="Go", page="p")).press("x.go")
    assert result["ok"] is False
    assert "the GUI refused" in result["error"]


def test_a_real_button_leaves_the_root_error_hook_as_it_found_it(root):
    """The redirect lasts exactly one press."""
    marker = object()
    root.report_callback_exception = marker
    button = ttk.Button(root, command=lambda: None)
    one(ctl.action("x.go", button, label="Go", page="p")).press("x.go")
    assert root.report_callback_exception is marker
    del root.report_callback_exception
    assert "report_callback_exception" not in vars(root)
    one(ctl.action("x.go", button, label="Go", page="p")).press("x.go")
    assert "report_callback_exception" not in vars(root)   # not left behind


def test_a_real_file_dialog_is_refused_without_a_path(root):
    """The press must ask, not guess — and the command must not run on."""
    picked = []

    def load():
        picked.append(filedialog.askopenfilename(title="pick a script"))

    button = ttk.Button(root, command=load)
    registry = one(ctl.action("x.load", button, label="Load", page="p"))
    refused = registry.press("x.load")
    assert refused["ok"] is False
    assert refused["needs_answer"]["function"] == "askopenfilename"
    assert picked == []                        # never reached the command
    accepted = registry.press("x.load", files=["/tmp/thing.py"])
    assert accepted["ok"] is True
    assert picked == ["/tmp/thing.py"]


def test_a_real_message_box_is_recorded_and_the_press_succeeds(root):
    button = ttk.Button(
        root, command=lambda: messagebox.showwarning("Sweep", "fix the fields"))
    result = one(ctl.action("x.go", button, label="Go", page="p")).press("x.go")
    assert result["ok"] is True
    assert result["dialogs"][0]["message"] == "fix the fields"


def test_a_command_that_returns_nothing_reports_none_not_the_string(root):
    button = ttk.Button(root, command=lambda: None)
    result = one(ctl.action("x.go", button, label="Go", page="p")).press("x.go")
    assert result["result"] is None            # not the Tcl string 'None'


def test_a_real_disabled_button_is_refused(root):
    button = ttk.Button(root, command=lambda: None, state="disabled")
    registry = one(ctl.action("x.go", button, label="Go", page="p",
                              disabled_hint="only while a sweep runs"))
    with pytest.raises(ControlError) as excinfo:
        registry.press("x.go")
    assert "greyed out" in str(excinfo.value)
    assert "only while a sweep runs" in str(excinfo.value)


# ---------------------------------------------------------------------------
# every other binder, against the real widget
# ---------------------------------------------------------------------------
def test_a_real_combobox_accepts_the_bare_address(root):
    """The exact shape that failed on a live rig: the device picker shows
    'ADDRESS — Driver' and the address alone has to resolve."""
    widget = ttk.Combobox(root, state="readonly",
                          values=["Time", "SMU — Mock", "LOCKIN — Mock",
                                  "BARE"])
    widget.set("Time")
    control = ctl.choice("x.dev", widget, label="Device", page="p")
    assert control.options() == ["Time", "SMU — Mock", "LOCKIN — Mock",
                                 "BARE"]
    control.setter("SMU")
    assert control.value() == "SMU — Mock"
    control.setter("BARE")
    assert control.value() == "BARE"
    with pytest.raises(ControlError):
        control.setter("nonexistent")


def test_a_real_combobox_reports_its_values_as_a_sequence(root):
    """cget('values') has historically come back as a Tcl list string; if
    it did, every option would be a single character."""
    widget = ttk.Combobox(root, values=["one", "two three"])
    options = ctl.choice("x.c", widget, label="c", page="p").options()
    assert options == ["one", "two three"]


def test_a_real_validated_entry_round_trips(root):
    widget = ValidatedEntry(root, 1.5)
    control = ctl.number("x.n", widget, label="n", page="p")
    assert control.value() == 1.5
    control.setter("-2.25")
    assert control.value() == -2.25
    with pytest.raises(ControlError):
        control.setter("banana")
    optional = ctl.number("x.o", ValidatedEntry(root, "", allow_empty=True),
                          label="o", page="p", allow_empty=True)
    optional.setter(None)
    assert optional.value() is None


def test_a_real_spinbox_and_checkbox_round_trip(root):
    spin = ttk.Spinbox(root, from_=1, to=999)
    spin.set(1)
    control = ctl.spin("x.s", spin, label="s", page="p", minimum=1,
                       maximum=999)
    control.setter(4)
    assert control.value() == 4
    with pytest.raises(ControlError):
        control.setter(0)

    var = tk.BooleanVar(value=False)
    flag = ctl.flag("x.f", var, label="f", page="p")
    flag.setter("yes")
    assert flag.value() is True and var.get() is True


def test_a_real_text_box_and_listbox_round_trip(root):
    text = tk.Text(root, height=3)
    control = ctl.text_field("x.t", text, label="t", page="p")
    control.setter("if abs(reads['A.B']) > 1e-9:\n    stop()")
    assert control.value().endswith("stop()")
    control.setter("")
    assert control.value() == ""

    listbox = tk.Listbox(root, selectmode="multiple", exportselection=False)
    for item in ("A.x", "A.y", "B.x"):
        listbox.insert("end", item)
    picker = ctl.multichoice("x.m", listbox, label="m", page="p")
    assert picker.options() == ["A.x", "A.y", "B.x"]
    picker.setter(["A.y", "B.x"])
    assert picker.value() == ["A.y", "B.x"]
    picker.setter([])
    assert picker.value() == []


def test_describe_reads_every_real_widget_without_raising(root):
    """The whole point of list_controls: one hop, nothing throws."""
    combo = ttk.Combobox(root, values=["a", "b"])
    combo.set("a")
    controls = [
        ctl.choice("x.c", combo, label="c", page="p"),
        ctl.number("x.n", ValidatedEntry(root, 2.0), label="n", page="p"),
        ctl.flag("x.f", tk.BooleanVar(value=True), label="f", page="p"),
        ctl.text_field("x.t", tk.Text(root, height=2), label="t", page="p"),
        ctl.action("x.a", ttk.Button(root, command=lambda: None),
                   label="a", page="p"),
        ctl.readout("x.r", lambda: "shown", label="r", page="p"),
    ]
    described = ControlRegistry(DirectBridge(), controls).describe()
    assert [d["name"] for d in described] == ["x.a", "x.c", "x.f", "x.n",
                                              "x.r", "x.t"]
    assert not any("error" in d for d in described)
    by_name = {d["name"]: d for d in described}
    assert by_name["x.c"]["value"] == "a"
    assert by_name["x.n"]["value"] == 2.0
    assert by_name["x.f"]["value"] is True
    assert "value" not in by_name["x.a"]           # a button has none
