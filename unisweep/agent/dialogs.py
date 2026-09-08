"""Answering the GUI's dialog boxes from a script.

Unisweep asks real questions at real moments: "these axes are not at their
start value — go to start, start from here, or cancel?"; "ramp all sweep
devices to zero and stop?"; "fix the highlighted fields first". A human
reads them and clicks. An assistant pressing the same button would hang
the Tk loop forever inside a modal nobody can see.

So an agent-initiated press runs with the dialog functions swapped for
proxies that:

* **record every dialog** the GUI would have shown, and hand the
  transcript back with the result — the assistant sees exactly what the
  user would have seen, which is often the most informative part of the
  answer ("Start warning: GPIB4.Volt is at 2.5, sweep starts at 0");
* **answer questions from a script** supplied with the call;
* **refuse rather than guess.** An unanswered question aborts the action
  with :class:`UnansweredDialog`, naming what was asked. Silently picking
  a default would mean pressing Start and quietly cancelling — or worse,
  quietly not cancelling.

Purely informational dialogs (``showinfo`` / ``showwarning`` /
``showerror``) never need an answer: they are recorded and dismissed, so a
validation complaint surfaces as data instead of stopping the world.
"""

from __future__ import annotations

import contextlib
import threading
from dataclasses import dataclass, field
from typing import Any, Optional

__all__ = ["DialogRecord", "DialogScript", "UnansweredDialog", "intercept",
           "discover_modules", "GUI_PACKAGE", "EXTRA_MODULES"]

#: every loaded module under this package did ``from tkinter import
#: messagebox`` at import time, so the proxies are installed by scanning
#: rather than by a hand-kept list — a page added later is covered without
#: anyone remembering to add it here
GUI_PACKAGE = "unisweep.gui."

#: extra module names to intercept (test doubles, third-party pages)
EXTRA_MODULES: set = set()


def discover_modules() -> list:
    """Loaded modules that hold a reference to a tkinter dialog module."""
    import sys as _sys
    names = [n for n in list(_sys.modules)
             if n.startswith(GUI_PACKAGE)] + sorted(EXTRA_MODULES)
    out = []
    for name in names:
        module = _sys.modules.get(name)
        if module is None:
            continue
        if hasattr(module, "messagebox") or hasattr(module, "filedialog"):
            out.append(name)
    return out

_LOCK = threading.RLock()

_YES = {"yes", "y", "true", "ok", "1"}
_NO = {"no", "n", "false", "0"}
_CANCEL = {"cancel", "none", ""}


@dataclass(frozen=True)
class DialogRecord:
    """One dialog the GUI raised while an agent action was running."""

    kind: str            # info | warning | error | question | file | directory
    function: str        # the tkinter call, e.g. 'askyesnocancel'
    title: str
    message: str
    answer: Any = None

    def to_dict(self) -> dict:
        return {"kind": self.kind, "function": self.function,
                "title": self.title, "message": self.message,
                "answer": self.answer}

    def __str__(self) -> str:                     # pragma: no cover
        return f"[{self.kind}] {self.title}: {self.message}"


class UnansweredDialog(RuntimeError):
    """The GUI asked something the caller did not provide an answer for."""

    def __init__(self, record: DialogRecord, transcript: list):
        options = _options_for(record.function)
        super().__init__(
            f"Unisweep asked: \"{record.title}: {record.message}\" — "
            f"re-issue the call with answers={options!r} (one entry per "
            f"question, in order)")
        self.record = record
        self.transcript = list(transcript)


def _options_for(function: str) -> list:
    if function == "askyesnocancel":
        return ["yes | no | cancel"]
    if function in ("askopenfilename", "asksaveasfilename", "askdirectory"):
        return ["<a path>"]
    return ["yes | no"]


def _as_bool(value: Any, function: str) -> Any:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in _YES:
        return True
    if text in _NO:
        return False
    if text in _CANCEL:
        return None
    raise ValueError(
        f"'{value}' is not a valid answer to {function} "
        f"({' / '.join(_options_for(function))})")


@dataclass
class DialogScript:
    """Answers to hand the GUI, plus the transcript of what it asked."""

    answers: list = field(default_factory=list)
    files: list = field(default_factory=list)
    transcript: list = field(default_factory=list)
    _answer_i: int = 0
    _file_i: int = 0

    def next_answer(self, record: DialogRecord):
        if self._answer_i >= len(self.answers):
            self.transcript.append(record)
            raise UnansweredDialog(record, self.transcript)
        value = self.answers[self._answer_i]
        self._answer_i += 1
        return value

    def next_file(self, record: DialogRecord):
        if self._file_i >= len(self.files):
            self.transcript.append(record)
            raise UnansweredDialog(record, self.transcript)
        value = self.files[self._file_i]
        self._file_i += 1
        return value

    def records(self) -> list:
        return [r.to_dict() for r in self.transcript]

    @property
    def unused_answers(self) -> int:
        return max(len(self.answers) - self._answer_i, 0)


def _text(kwargs, args, index, key, default=""):
    if key in kwargs:
        return str(kwargs[key] or "")
    if len(args) > index:
        return str(args[index] or "")
    return default


class _MessageBoxProxy:
    """Stand-in for ``tkinter.messagebox`` during an agent action."""

    def __init__(self, script: DialogScript):
        self._script = script

    # -- informational: recorded, never blocking ------------------------
    def _show(self, kind, function, args, kwargs, result):
        record = DialogRecord(
            kind=kind, function=function,
            title=_text(kwargs, args, 0, "title"),
            message=_text(kwargs, args, 1, "message"),
            answer=result)
        self._script.transcript.append(record)
        return result

    def showinfo(self, *a, **kw):
        return self._show("info", "showinfo", a, kw, "ok")

    def showwarning(self, *a, **kw):
        return self._show("warning", "showwarning", a, kw, "ok")

    def showerror(self, *a, **kw):
        return self._show("error", "showerror", a, kw, "ok")

    # -- questions: answered from the script ----------------------------
    def _ask(self, function, args, kwargs, coerce):
        record = DialogRecord(
            kind="question", function=function,
            title=_text(kwargs, args, 0, "title"),
            message=_text(kwargs, args, 1, "message"))
        raw = self._script.next_answer(record)
        answer = coerce(_as_bool(raw, function))
        self._script.transcript.append(
            DialogRecord(record.kind, record.function, record.title,
                         record.message, answer))
        return answer

    def askyesno(self, *a, **kw):
        return self._ask("askyesno", a, kw, lambda v: bool(v))

    def askokcancel(self, *a, **kw):
        return self._ask("askokcancel", a, kw, lambda v: bool(v))

    def askretrycancel(self, *a, **kw):
        return self._ask("askretrycancel", a, kw, lambda v: bool(v))

    def askyesnocancel(self, *a, **kw):
        return self._ask("askyesnocancel", a, kw, lambda v: v)

    def askquestion(self, *a, **kw):
        return self._ask("askquestion", a, kw,
                         lambda v: "yes" if v else "no")


class _FileDialogProxy:
    """Stand-in for ``tkinter.filedialog`` during an agent action."""

    def __init__(self, script: DialogScript):
        self._script = script

    def _ask(self, function, kind, kwargs):
        record = DialogRecord(kind=kind, function=function,
                              title=str(kwargs.get("title", "") or ""),
                              message="")
        path = str(self._script.next_file(record) or "")
        self._script.transcript.append(
            DialogRecord(kind, function, record.title, path, path))
        return path

    def askopenfilename(self, **kw):
        return self._ask("askopenfilename", "file", kw)

    def asksaveasfilename(self, **kw):
        return self._ask("asksaveasfilename", "file", kw)

    def askdirectory(self, **kw):
        return self._ask("askdirectory", "directory", kw)


@contextlib.contextmanager
def intercept(answers=None, files=None, modules=None):
    """Swap the GUI's dialog modules for scripted proxies.

    Yields the :class:`DialogScript`, whose ``transcript`` lists every
    dialog raised inside the block. Held under a lock, so two agent
    actions can never intercept at once; a dialog a *human* triggers
    during the block would also be intercepted, which is why the block
    should wrap one action, not a whole session.
    """
    import sys

    script = DialogScript(answers=list(answers or ()),
                          files=list(files or ()))
    saved: list[tuple] = []
    with _LOCK:
        for name in (discover_modules() if modules is None else modules):
            module = sys.modules.get(name)
            if module is None:
                continue
            for attr, proxy in (("messagebox", _MessageBoxProxy(script)),
                                ("filedialog", _FileDialogProxy(script))):
                if hasattr(module, attr):
                    saved.append((module, attr, getattr(module, attr)))
                    setattr(module, attr, proxy)
        try:
            yield script
        finally:
            for module, attr, original in saved:
                setattr(module, attr, original)
