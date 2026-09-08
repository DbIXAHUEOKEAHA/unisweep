"""Duck-typed stand-ins for the Tk widgets the control layer binds to.

The agent control surface never imports tkinter: every binder in
``unisweep.agent.controls`` needs only ``get`` / ``set`` / ``cget`` /
``invoke``. That is what makes it testable on a machine with no display,
and these are the objects that prove it.
"""


class FakeEntry:
    """Stands in for ValidatedEntry."""

    def __init__(self, initial="", validator=float, allow_empty=False):
        self._text = "" if initial is None else str(initial)
        self._validator = validator
        self._allow_empty = allow_empty
        self.state = "normal"

    def value(self):
        text = self._text.strip()
        if text == "":
            return None
        try:
            return self._validator(text)
        except (TypeError, ValueError):
            return None

    def set(self, value):
        self._text = "" if value is None else str(value)

    def cget(self, key):
        return getattr(self, key, "")


class FakeCombo:
    def __init__(self, values=(), value=None):
        self._values = [str(v) for v in values]
        self._value = str(value) if value is not None else (
            self._values[0] if self._values else "")
        self.state = "readonly"

    def get(self):
        return self._value

    def set(self, value):
        self._value = str(value)

    def configure(self, **kw):
        if "values" in kw:
            self._values = [str(v) for v in kw["values"]]
        for key, value in kw.items():
            if key != "values":
                setattr(self, key, value)

    def cget(self, key):
        return list(self._values) if key == "values" else getattr(self, key, "")

    def current(self, index=None):
        if index is None:
            return (self._values.index(self._value)
                    if self._value in self._values else -1)
        self._value = self._values[int(index)]


class FakeSpin:
    def __init__(self, value=1):
        self._value = str(value)
        self.state = "normal"

    def get(self):
        return self._value

    def set(self, value):
        self._value = str(value)

    def cget(self, key):
        return getattr(self, key, "")


class FakeVar:
    def __init__(self, value=False):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class FakeText:
    def __init__(self, text=""):
        self._text = str(text)
        self.state = "normal"

    def get(self, start="1.0", end="end"):
        return self._text

    def delete(self, start, end=None):
        self._text = ""

    def insert(self, where, text):
        self._text += str(text)

    def cget(self, key):
        return getattr(self, key, "")


class FakeListbox:
    def __init__(self, items=()):
        self._items = [str(i) for i in items]
        self._selected: set = set()
        self.state = "normal"

    def size(self):
        return len(self._items)

    def get(self, index):
        return self._items[int(index)]

    def curselection(self):
        return tuple(sorted(self._selected))

    def selection_clear(self, first, last=None):
        self._selected.clear()

    def selection_set(self, first, last=None):
        index = len(self._items) - 1 if first == "end" else int(first)
        self._selected.add(index)

    def insert(self, where, item):
        self._items.append(str(item))

    def delete(self, first, last=None):
        self._items = []
        self._selected.clear()

    def cget(self, key):
        return getattr(self, key, "")


class FakeButton:
    def __init__(self, command=None, state="normal"):
        self.command = command
        self.state = state
        self.presses = 0

    def invoke(self):
        self.presses += 1
        return self.command() if self.command is not None else None

    def configure(self, **kw):
        for key, value in kw.items():
            setattr(self, key, value)

    def cget(self, key):
        return getattr(self, key, "")


class FakeLabel:
    def __init__(self, text=""):
        self.text = str(text)

    def configure(self, **kw):
        for key, value in kw.items():
            setattr(self, key, value)

    def cget(self, key):
        return getattr(self, key, "")
