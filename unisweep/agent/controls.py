"""Every knob in Unisweep, as a named handle.

The goal is that an assistant can do what a person at the keyboard does:
read every field, type into every box, tick every checkbox and press every
button — and that the application cannot tell the difference afterwards.

The way *not* to do that is to synthesise mouse and key events at the
widgets. Instead every control is bound to the same widget API the
callbacks already use, so a change lands in the same place a human's
change lands: the entry's variable, the combobox's selection, the button's
command. The GUI stays the single source of truth; nothing is mirrored,
so nothing can drift.

Control names are stable dotted paths that read like where you would point
on screen::

    sweep.axis1.start          sweep.axis1.device        sweep.start
    sweep.reads                setget.row1.value         settings.map_style
    devices.GPIB0__4__INSTR.type

A control declares its ``kind``, which tells a caller what a value may be:

``number``       a float (``None`` when the box is legitimately empty)
``text``         free text
``choice``       one of ``options``
``multichoice``  any subset of ``options``
``flag``         a checkbox
``action``       a button: no value, only :meth:`ControlRegistry.press`
``readout``      a value the GUI displays but nobody can type into

Widget access is duck-typed on purpose: the binders below need only
``get``/``set``/``cget``/``invoke``, so the whole layer is testable without
a display.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Optional, Sequence

__all__ = ["Control", "ControlRegistry", "ControlError", "UnknownControl",
           "KINDS", "choice", "number", "spin", "flag", "text_field",
           "entry_text", "option_var", "selection", "multichoice", "action",
           "readout"]

KINDS = ("number", "text", "choice", "multichoice", "flag", "action",
         "readout")

_TRUE = {"1", "true", "yes", "on", "y"}
_FALSE = {"0", "false", "no", "off", "n", ""}


class ControlError(RuntimeError):
    """A control exists but the requested operation is not possible."""


class UnknownControl(KeyError):
    """No control by that name."""

    def __init__(self, name: str, suggestions: Sequence[str] = ()):
        hint = ""
        if suggestions:
            hint = " — did you mean " + ", ".join(list(suggestions)[:5]) + "?"
        super().__init__(f"no control named '{name}'{hint}")
        self.name = name
        self.suggestions = list(suggestions)

    def __str__(self) -> str:                     # KeyError quotes its arg
        return self.args[0]


# ---------------------------------------------------------------------------
@dataclass
class Control:
    """One user-facing knob, bound to the widget that owns it."""

    name: str
    kind: str
    label: str
    page: str
    getter: Optional[Callable[[], Any]] = None
    setter: Optional[Callable[[Any], None]] = None
    presser: Optional[Callable[[], Any]] = None
    options_fn: Optional[Callable[[], list]] = None
    enabled_fn: Optional[Callable[[], bool]] = None
    help: str = ""
    unit: str = ""

    @property
    def writable(self) -> bool:
        return self.setter is not None

    def options(self) -> Optional[list]:
        if self.options_fn is None:
            return None
        try:
            return list(self.options_fn())
        except Exception:                          # noqa: BLE001
            return None

    def enabled(self) -> bool:
        if self.enabled_fn is None:
            return True
        try:
            return bool(self.enabled_fn())
        except Exception:                          # noqa: BLE001
            return True

    def value(self) -> Any:
        if self.getter is None:
            return None
        return self.getter()

    def describe(self, include_value: bool = True) -> dict:
        out: dict = {"name": self.name, "kind": self.kind,
                     "label": self.label, "page": self.page}
        if self.unit:
            out["unit"] = self.unit
        if self.help:
            out["help"] = self.help
        options = self.options()
        if options is not None:
            out["options"] = options
        if self.kind != "action":
            out["writable"] = self.writable
        if include_value and self.kind != "action":
            try:
                out["value"] = _plain(self.value())
            except Exception as exc:               # noqa: BLE001
                out["value"] = None
                out["error"] = f"{type(exc).__name__}: {exc}"
        if not self.enabled():
            out["enabled"] = False
        return out


def _plain(value):
    """JSON-friendly rendering of a widget value."""
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return str(value)


# ---------------------------------------------------------------------------
# widget binders — duck-typed, so none of this needs a display to test
# ---------------------------------------------------------------------------
def _enabled_of(widget) -> Callable[[], bool]:
    def enabled() -> bool:
        try:
            return str(widget.cget("state")) != "disabled"
        except Exception:                          # noqa: BLE001
            return True
    return enabled


def _match_option(value, options: Sequence[str], name: str) -> str:
    """Accept what a person would type, not only the exact display string.

    Device pickers show ``'GPIB0::4::INSTR — keithley2400'``; naming the
    bare address has to work, because that is what programs and profiles
    use everywhere else.
    """
    text = "" if value is None else str(value)
    options = [str(o) for o in options]
    if not options:
        return text
    if text in options:
        return text
    lowered = text.strip().lower()
    for option in options:                         # case-insensitive
        if option.strip().lower() == lowered:
            return option
    for option in options:                         # 'ADDR — Driver' -> ADDR
        if option.split(" — ")[0].strip().lower() == lowered:
            return option
    raise ControlError(
        f"'{text}' is not one of the options for '{name}': "
        + ", ".join(options[:20]) + (" …" if len(options) > 20 else ""))


def _to_bool(value, name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in _TRUE:
        return True
    if text in _FALSE:
        return False
    raise ControlError(f"'{value}' is not a true/false value for '{name}'")


def _to_number(value, name: str, allow_empty: bool):
    if value is None or (isinstance(value, str) and not value.strip()):
        if allow_empty:
            return None
        raise ControlError(f"'{name}' needs a number")
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ControlError(f"'{value}' is not a number for '{name}'") from None


def choice(name, widget, *, label, page, help="", after_set=None,
           options_fn=None):
    """A readonly combobox."""
    def get():
        return widget.get()

    def options():
        if options_fn is not None:
            return [str(o) for o in options_fn()]
        return [str(o) for o in (widget.cget("values") or ())]

    def setv(value):
        widget.set(_match_option(value, options(), name))
        if after_set is not None:
            after_set()

    return Control(name=name, kind="choice", label=label, page=page,
                   getter=get, setter=setv, options_fn=options,
                   enabled_fn=_enabled_of(widget), help=help)


def number(name, widget, *, label, page, help="", unit="",
           allow_empty=False, after_set=None):
    """A :class:`~unisweep.gui.widgets.ValidatedEntry` holding a number."""
    def get():
        return widget.value()

    def setv(value):
        widget.set(_to_number(value, name, allow_empty))
        if after_set is not None:
            after_set()

    return Control(name=name, kind="number", label=label, page=page,
                   getter=get, setter=setv, enabled_fn=_enabled_of(widget),
                   help=help, unit=unit)


def spin(name, widget, *, label, page, help="", minimum=None, maximum=None):
    """A ttk.Spinbox holding an integer."""
    def get():
        try:
            return int(float(widget.get()))
        except (TypeError, ValueError):
            return None

    def setv(value):
        try:
            number_ = int(float(value))
        except (TypeError, ValueError):
            raise ControlError(
                f"'{value}' is not a whole number for '{name}'") from None
        if minimum is not None and number_ < minimum:
            raise ControlError(f"'{name}' cannot be below {minimum}")
        if maximum is not None and number_ > maximum:
            raise ControlError(f"'{name}' cannot be above {maximum}")
        widget.set(number_)

    return Control(name=name, kind="number", label=label, page=page,
                   getter=get, setter=setv, enabled_fn=_enabled_of(widget),
                   help=help)


def flag(name, var, *, label, page, help="", after_set=None):
    """A checkbox, bound through its BooleanVar."""
    def setv(value):
        var.set(_to_bool(value, name))
        if after_set is not None:
            after_set()

    return Control(name=name, kind="flag", label=label, page=page,
                   getter=var.get, setter=setv, help=help)


def text_field(name, widget, *, label, page, help="", strip=True):
    """A multi-line tk.Text box."""
    def get():
        text = widget.get("1.0", "end")
        return text.strip() if strip else text

    def setv(value):
        widget.delete("1.0", "end")
        if value:
            widget.insert("1.0", str(value))

    return Control(name=name, kind="text", label=label, page=page,
                   getter=get, setter=setv, enabled_fn=_enabled_of(widget),
                   help=help)


def entry_text(name, widget, *, label, page, help=""):
    """A single-line entry holding free text."""
    def setv(value):
        widget.set("" if value is None else str(value))

    return Control(name=name, kind="text", label=label, page=page,
                   getter=widget.value, setter=setv,
                   enabled_fn=_enabled_of(widget), help=help)


def selection(name, getter, setter, options_fn, *, label, page, help=""):
    """A choice backed by a pair of functions rather than a widget."""
    def setv(value):
        setter(_match_option(value, [str(o) for o in options_fn()], name))

    return Control(name=name, kind="choice", label=label, page=page,
                   getter=getter, setter=setv,
                   options_fn=lambda: [str(o) for o in options_fn()],
                   help=help)


def option_var(name, var, options, *, label, page, help="", after_set=None):
    """A radio-button group, bound through its StringVar."""
    values = [str(o) for o in options]

    def setv(value):
        var.set(_match_option(value, values, name))
        if after_set is not None:
            after_set()

    return Control(name=name, kind="choice", label=label, page=page,
                   getter=var.get, setter=setv, options_fn=lambda: list(values),
                   help=help)


def multichoice(name, listbox, *, label, page, help=""):
    """A multi-select listbox (the read-parameter pickers)."""
    def options():
        return [listbox.get(i) for i in range(listbox.size())]

    def get():
        return [listbox.get(i) for i in listbox.curselection()]

    def setv(values):
        if values is None:
            values = []
        if isinstance(values, str):
            values = [values]
        available = options()
        wanted = []
        for value in values:
            wanted.append(_match_option(value, available, name))
        listbox.selection_clear(0, "end")
        for index, option in enumerate(available):
            if option in wanted:
                listbox.selection_set(index)

    return Control(name=name, kind="multichoice", label=label, page=page,
                   getter=get, setter=setv, options_fn=options,
                   enabled_fn=_enabled_of(listbox), help=help)


def action(name, button, *, label, page, help="", disabled_hint=""):
    """A button. Pressing runs exactly the command the click would run."""
    enabled = _enabled_of(button)

    def press():
        if not enabled():
            raise ControlError(
                f"'{name}' is greyed out right now"
                + (f" — {disabled_hint}" if disabled_hint else ""))
        return button.invoke()

    return Control(name=name, kind="action", label=label, page=page,
                   presser=press, enabled_fn=enabled, help=help)


def readout(name, getter, *, label, page, help="", unit=""):
    """Something the GUI shows but nobody can type into."""
    return Control(name=name, kind="readout", label=label, page=page,
                   getter=getter, help=help, unit=unit)


# ---------------------------------------------------------------------------
class ControlRegistry:
    """All controls, indexed by name, reached over a UI-thread bridge.

    Every method here is one bridge round trip, including the bulk ones —
    reading the whole GUI is a single hop onto the Tk loop rather than one
    per field, and a batched write lands as one coherent edit.
    """

    def __init__(self, bridge, controls: Iterable[Control] = ()):
        self.bridge = bridge
        self._controls: dict[str, Control] = {}
        for control in controls:
            self.add(control)

    # ---- building ----------------------------------------------------
    def add(self, control: Control) -> Control:
        if control.kind not in KINDS:
            raise ValueError(f"{control.name}: unknown kind "
                             f"'{control.kind}'")
        self._controls[control.name] = control
        return control

    def extend(self, controls: Iterable[Control]) -> None:
        for control in controls:
            self.add(control)

    def clear(self) -> None:
        self._controls.clear()

    def __contains__(self, name: object) -> bool:
        return name in self._controls

    def __len__(self) -> int:
        return len(self._controls)

    def names(self) -> list[str]:
        return sorted(self._controls)

    def pages(self) -> list[str]:
        return sorted({c.page for c in self._controls.values()})

    # ---- lookup ------------------------------------------------------
    def control(self, name: str) -> Control:
        try:
            return self._controls[name]
        except KeyError:
            raise UnknownControl(name, self._similar(name)) from None

    def _similar(self, name: str) -> list[str]:
        text = str(name).lower()
        tail = text.rsplit(".", 1)[-1]
        scored = [n for n in self._controls
                  if tail and tail in n.lower()] or \
                 [n for n in self._controls if text[:4] and
                  n.lower().startswith(text[:4])]
        return sorted(scored)

    # ---- reading -----------------------------------------------------
    def describe(self, page: Optional[str] = None,
                 prefix: Optional[str] = None,
                 include_values: bool = True) -> list[dict]:
        """Every control, with its current value — one trip to the GUI."""
        selected = self._select(page, prefix)

        def work():
            return [c.describe(include_values) for c in selected]

        return self.bridge.call(work)

    def read(self, names: Optional[Sequence[str]] = None,
             page: Optional[str] = None,
             prefix: Optional[str] = None) -> dict:
        """``{name: value}`` for the named controls (or a whole page)."""
        if names is None:
            selected = [c for c in self._select(page, prefix)
                        if c.kind != "action"]
        else:
            selected = [self.control(n) for n in names]

        def work():
            out = {}
            for control in selected:
                if control.kind == "action":
                    continue
                try:
                    out[control.name] = _plain(control.value())
                except Exception as exc:           # noqa: BLE001
                    out[control.name] = f"<error: {exc}>"
            return out

        return self.bridge.call(work)

    def _select(self, page: Optional[str],
                prefix: Optional[str]) -> list[Control]:
        controls = [self._controls[n] for n in self.names()]
        if page:
            controls = [c for c in controls if c.page == page]
        if prefix:
            controls = [c for c in controls if c.name.startswith(prefix)]
        return controls

    # ---- writing -----------------------------------------------------
    def set(self, name: str, value: Any) -> dict:
        return self.set_many({name: value})

    def set_many(self, values: dict) -> dict:
        """Apply several edits as one GUI update.

        Controls are resolved (and rejected) before anything is written, so
        a typo in the fifth field does not leave the first four applied.
        """
        planned = [(self.control(name), value)
                   for name, value in values.items()]
        for control, _ in planned:
            if not control.writable:
                raise ControlError(
                    f"'{control.name}' is a {control.kind}, not something "
                    f"that can be typed into")

        def work():
            applied = {}
            for control, value in planned:
                control.setter(value)
                applied[control.name] = _plain(control.value())
            return applied

        return self.bridge.call(work)

    # ---- pressing ----------------------------------------------------
    def press(self, name: str, answers=None, files=None,
              timeout: Optional[float] = None) -> dict:
        """Press a button exactly as a click would, answering its dialogs.

        Returns ``{'pressed', 'dialogs', 'result'}``; ``dialogs`` is every
        message the GUI raised, which is usually where the real answer is.
        """
        from .dialogs import UnansweredDialog, intercept

        control = self.control(name)
        if control.presser is None:
            raise ControlError(f"'{name}' is a {control.kind}, not a button")
        with intercept(answers=answers, files=files) as script:
            try:
                result = self.bridge.call(control.presser, timeout=timeout)
            except UnansweredDialog as exc:
                return {"pressed": name, "ok": False,
                        "dialogs": [r.to_dict() for r in exc.transcript],
                        "needs_answer": exc.record.to_dict(),
                        "error": str(exc)}
            return {"pressed": name, "ok": True,
                    "dialogs": script.records(),
                    "result": _plain(result)}
