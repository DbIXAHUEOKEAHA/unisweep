"""Small reusable widgets."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from .theme import PALETTE


class Tooltip:
    """Hover tooltip (replacement for the legacy CreateToolTip)."""

    def __init__(self, widget, text: str, delay: int = 500):
        self.widget, self.text, self.delay = widget, text, delay
        self._id = None
        self._tip: Optional[tk.Toplevel] = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _=None):
        self._cancel()
        self._id = self.widget.after(self.delay, self._show)

    def _cancel(self):
        if self._id:
            self.widget.after_cancel(self._id)
            self._id = None

    def _show(self):
        if self._tip or not self.text:
            return
        x = self.widget.winfo_rootx() + 16
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self._tip = tk.Toplevel(self.widget)
        self._tip.wm_overrideredirect(True)
        self._tip.wm_geometry(f"+{x}+{y}")
        tk.Label(self._tip, text=self.text, justify="left",
                 background=PALETTE["card"], foreground=PALETTE["text"],
                 relief="solid", borderwidth=1, padx=8, pady=5,
                 wraplength=340).pack()

    def _hide(self, _=None):
        self._cancel()
        if self._tip:
            self._tip.destroy()
            self._tip = None


class ValidatedEntry(ttk.Entry):
    """Entry validated as float (or with a custom validator).

    Invalid input turns the field red instead of exploding later inside the
    sweep thread (the legacy failure mode). ``value()`` returns None while
    invalid.
    """

    def __init__(self, master, initial="", validator: Callable = float,
                 allow_empty=False, width=9, on_change: Callable = None,
                 **kw):
        self.var = tk.StringVar(value=str(initial))
        super().__init__(master, textvariable=self.var, width=width, **kw)
        self._validator = validator
        self._allow_empty = allow_empty
        self._on_change = on_change
        self.var.trace_add("write", self._revalidate)
        self._revalidate()

    def _revalidate(self, *_):
        ok = self.valid
        self.configure(style="TEntry" if ok else "Invalid.TEntry")
        if self._on_change:
            self._on_change()

    @property
    def valid(self) -> bool:
        text = self.var.get().strip()
        if text == "":
            return self._allow_empty
        try:
            self._validator(text)
            return True
        except (TypeError, ValueError):
            return False

    def value(self):
        text = self.var.get().strip()
        if text == "":
            return None
        try:
            return self._validator(text)
        except (TypeError, ValueError):
            return None

    def set(self, value):
        self.var.set("" if value is None else str(value))


class Card(ttk.Frame):
    """Titled group box on the card colour."""

    def __init__(self, master, title: str = "", **kw):
        super().__init__(master, style="Card.TFrame", padding=12, **kw)
        if title:
            self.title_label = ttk.Label(self, text=title, style="Title.TLabel")
            self.title_label.grid(row=0, column=0, columnspan=8,
                                  sticky="w", pady=(0, 8))


class Collapsible(ttk.Frame):
    """A section that folds away (script editor, back-sweep settings...)."""

    def __init__(self, master, title: str, opened=False):
        super().__init__(master, style="Card.TFrame")
        self._open = tk.BooleanVar(value=opened)
        self._btn = ttk.Checkbutton(
            self, text=title, variable=self._open, style="TCheckbutton",
            command=self._toggle)
        self._btn.grid(row=0, column=0, sticky="w")
        self.body = ttk.Frame(self, style="Card.TFrame", padding=(16, 6, 0, 0))
        self.columnconfigure(0, weight=1)
        self._toggle()

    def _toggle(self):
        if self._open.get():
            self.body.grid(row=1, column=0, sticky="nsew")
        else:
            self.body.grid_forget()

    def open(self):
        self._open.set(True)
        self._toggle()


class Led(tk.Canvas):
    """Instrument-style state LED."""

    def __init__(self, master, diameter=10, **kw):
        super().__init__(master, width=diameter + 2, height=diameter + 2,
                         highlightthickness=0, bg=PALETTE["bg"], **kw)
        self._dot = self.create_oval(1, 1, diameter + 1, diameter + 1,
                                     fill=PALETTE["muted"], outline="")

    def set(self, colour: str):
        self.itemconfigure(self._dot, fill=colour)


class ScrollFrame(ttk.Frame):
    """Vertically scrollable frame (pages can outgrow the window).

    Wheel handling is done by ONE application-wide dispatcher (installed on
    first use) instead of one ``bind_all`` per instance, which fixes several
    real bugs of the naive approach:

    * scrolling inside a Listbox / Text / Treeview no longer also scrolls
      the page underneath it — those widgets scroll themselves natively and
      the dispatcher steps aside;
    * a page whose content fits entirely never reacts to the wheel;
    * handlers no longer accumulate with every new scroll area, and a
      destroyed one (closed wizard, removed plot) can no longer raise from
      a stale binding.
    """

    #: widgets that scroll themselves — the page must not scroll under them
    WHEEL_BLOCKERS = (tk.Listbox, tk.Text, ttk.Treeview, tk.Spinbox)

    def __init__(self, master, canvas_bg: str | None = None, **kw):
        super().__init__(master, **kw)
        canvas = tk.Canvas(self, bg=canvas_bg or PALETTE["surface"],
                           highlightthickness=0)
        vsb = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.inner = ttk.Frame(canvas)
        self.inner.bind("<Configure>", lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")))
        win = canvas.create_window((0, 0), window=self.inner, anchor="nw")
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfigure(win, width=e.width))
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        canvas._unisweep_scrollframe = True       # dispatcher marker
        self._canvas = canvas
        self._install_wheel_dispatcher(canvas)

    # -----------------------------------------------------------------
    @classmethod
    def _install_wheel_dispatcher(cls, widget: tk.Widget) -> None:
        root = widget._root()
        if getattr(root, "_unisweep_wheel_dispatcher", False):
            return
        root._unisweep_wheel_dispatcher = True

        def on_wheel(event):
            w = event.widget
            if not isinstance(w, tk.Misc):        # destroyed widget
                return
            try:
                node = w.winfo_containing(event.x_root, event.y_root)
            except (KeyError, tk.TclError):
                return
            canvas = None
            while node is not None:
                if isinstance(node, cls.WHEEL_BLOCKERS):
                    return                        # widget scrolls itself
                if isinstance(node, tk.Canvas) and                         getattr(node, "_unisweep_scrollframe", False):
                    canvas = node
                    break
                node = node.master
            if canvas is None:
                return
            try:
                lo, hi = canvas.yview()
                if hi - lo >= 1.0:                # everything already fits
                    return
                delta = -1 if getattr(event, "delta", 0) > 0 or                     getattr(event, "num", 0) == 4 else 1
                canvas.yview_scroll(delta, "units")
            except tk.TclError:
                pass

        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            root.bind_all(seq, on_wheel, add="+")
