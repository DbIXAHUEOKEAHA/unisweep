"""Instrument-panel theme for ttk.

A dark, low-glare palette suited to a cryostat lab, applied through plain
``ttk.Style`` on the 'clam' base — no third-party theme packages required.
Numeric readouts use a monospace face, interactive elements a single blue
accent, and run-state is shown with instrument-style LED colours.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont

DARK = {
    "bg":        "#12161b",   # window
    "surface":   "#191f26",   # page background
    "card":      "#20272f",   # grouped controls
    "card_edge": "#2c353f",
    "field":     "#161b21",   # entry interiors
    "text":      "#e8ebef",
    "muted":     "#8d97a5",
    "accent":    "#4f9cf9",   # interactive blue
    "accent_hi": "#71b1ff",
    "green":     "#3fb27f",   # LED: running / ok
    "amber":     "#d9a03f",   # LED: paused / warning
    "red":       "#e5534b",   # LED: error / stop
    "select":    "#294564",
}

LIGHT = {
    "bg":        "#e8eaee",
    "surface":   "#f4f5f7",
    "card":      "#ffffff",
    "card_edge": "#d3d8de",
    "field":     "#fcfdfe",
    "text":      "#1b2027",
    "muted":     "#5d6773",
    "accent":    "#1d6fd6",
    "accent_hi": "#3f8ae6",
    "green":     "#1d8a5f",
    "amber":     "#b07514",
    "red":       "#c2382f",
    "select":    "#c7ddf5",
}

# The LIVE palette. Mutated in place on a theme switch so every module
# holding a reference to it (and every widget created afterwards) follows.
PALETTE = dict(DARK)


def init_theme(name: str) -> None:
    """Select the palette BEFORE any widget exists (app start-up)."""
    PALETTE.clear()
    PALETTE.update(LIGHT if name == "light" else DARK)


#: color-bearing widget options a live re-theme rewrites
_COLOR_OPTS = ("background", "foreground", "insertbackground",
               "selectbackground", "selectforeground",
               "highlightbackground", "highlightcolor",
               "activebackground", "activeforeground",
               "readonlybackground", "disabledforeground", "troughcolor")


def _remap_colors(widget: tk.Misc, reverse: dict) -> None:
    """Walk the whole widget tree (Toplevels included) and translate every
    color that belonged to the OLD palette into the same key of the new
    one — plain-tk widgets capture colors at creation, so a live switch
    must rewrite them; anything user-custom (plot line colors) is left
    untouched because it is not in the map."""
    for opt in _COLOR_OPTS:
        try:
            cur = str(widget.cget(opt)).lower()
        except tk.TclError:
            continue
        key = reverse.get(cur)
        if key is not None:
            try:
                widget.configure({opt: PALETTE[key]})
            except tk.TclError:
                pass
    for child in widget.winfo_children():
        _remap_colors(child, reverse)


def set_theme(root: tk.Tk, name: str) -> None:
    """Switch dark/light LIVE: ttk styles are reconfigured (all ttk
    widgets follow instantly) and plain-tk widgets are color-remapped."""
    old = dict(PALETTE)
    init_theme(name)
    apply_theme(root)
    reverse = {v.lower(): k for k, v in old.items()}
    _remap_colors(root, reverse)

FONT_UI = None       # filled by apply_theme
FONT_MONO = None
FONT_TITLE = None


def apply_theme(root: tk.Tk) -> dict:
    """Configure ttk styles; returns the palette for ad-hoc widgets."""
    global FONT_UI, FONT_MONO, FONT_TITLE
    p = PALETTE

    families = set(tkfont.families(root))
    ui_face = next((f for f in ("Segoe UI", "SF Pro Text", "Ubuntu",
                                "DejaVu Sans") if f in families), "TkDefaultFont")
    mono_face = next((f for f in ("Consolas", "SF Mono", "Menlo",
                                  "DejaVu Sans Mono") if f in families),
                     "TkFixedFont")
    FONT_UI = (ui_face, 10)
    FONT_MONO = (mono_face, 10)
    FONT_TITLE = (ui_face, 11, "bold")

    root.configure(bg=p["bg"])
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(".", background=p["surface"], foreground=p["text"],
                    fieldbackground=p["field"], bordercolor=p["card_edge"],
                    lightcolor=p["surface"], darkcolor=p["surface"],
                    troughcolor=p["card"], font=FONT_UI, relief="flat")

    style.configure("TFrame", background=p["surface"])
    style.configure("Bg.TFrame", background=p["bg"])
    style.configure("Card.TFrame", background=p["card"])
    style.configure("TLabel", background=p["surface"], foreground=p["text"])
    style.configure("Card.TLabel", background=p["card"])
    style.configure("Muted.TLabel", background=p["card"],
                    foreground=p["muted"])
    style.configure("MutedS.TLabel", background=p["surface"],
                    foreground=p["muted"])
    style.configure("Title.TLabel", background=p["card"],
                    foreground=p["text"], font=FONT_TITLE)
    style.configure("Mono.TLabel", background=p["bg"], foreground=p["text"],
                    font=FONT_MONO)
    style.configure("MonoMuted.TLabel", background=p["bg"],
                    foreground=p["muted"], font=FONT_MONO)

    style.configure("TButton", background=p["card"], foreground=p["text"],
                    padding=(10, 5), borderwidth=1, focusthickness=1)
    style.map("TButton",
              background=[("active", p["card_edge"]),
                          ("disabled", p["surface"])],
              foreground=[("disabled", p["muted"])])
    style.configure("Accent.TButton", background=p["accent"],
                    foreground="#0d1117", padding=(12, 5))
    style.map("Accent.TButton",
              background=[("active", p["accent_hi"]),
                          ("disabled", p["card"])],
              foreground=[("disabled", p["muted"])])
    style.configure("Danger.TButton", background=p["card"],
                    foreground=p["red"])
    style.map("Danger.TButton", background=[("active", "#3a2a29")])
    style.configure("Nav.TButton", background=p["bg"], foreground=p["muted"],
                    padding=(14, 9), anchor="w", borderwidth=0)
    style.map("Nav.TButton", background=[("active", p["surface"])])
    style.configure("NavSel.TButton", background=p["surface"],
                    foreground=p["text"], padding=(14, 9), anchor="w",
                    borderwidth=0)

    style.configure("TEntry", insertcolor=p["text"], padding=4)
    style.map("TEntry", bordercolor=[("focus", p["accent"])],
              lightcolor=[("focus", p["accent"])])
    style.configure("Invalid.TEntry", fieldbackground="#2a1c1c")
    style.map("Invalid.TEntry", bordercolor=[("!disabled", p["red"])],
              lightcolor=[("!disabled", p["red"])])

    style.configure("TCombobox", padding=3, arrowcolor=p["muted"])
    style.map("TCombobox",
              fieldbackground=[("readonly", p["field"])],
              foreground=[("readonly", p["text"])],
              bordercolor=[("focus", p["accent"])])
    root.option_add("*TCombobox*Listbox.background", p["card"])
    root.option_add("*TCombobox*Listbox.foreground", p["text"])
    root.option_add("*TCombobox*Listbox.selectBackground", p["select"])
    root.option_add("*TCombobox*Listbox.selectForeground", p["text"])

    style.configure("TCheckbutton", background=p["card"],
                    foreground=p["text"])
    style.map("TCheckbutton", background=[("active", p["card"])],
              indicatorcolor=[("selected", p["accent"]),
                              ("!selected", p["field"])])
    style.configure("S.TCheckbutton", background=p["surface"],
                    foreground=p["text"])
    style.map("S.TCheckbutton", background=[("active", p["surface"])])

    style.configure("TSpinbox", padding=3, arrowcolor=p["muted"],
                    insertcolor=p["text"])
    style.configure("Horizontal.TProgressbar", background=p["accent"],
                    troughcolor=p["card"], bordercolor=p["card"],
                    lightcolor=p["accent"], darkcolor=p["accent"])
    style.configure("TSeparator", background=p["card_edge"])
    style.configure("Vertical.TScrollbar", troughcolor=p["surface"],
                    background=p["card_edge"], bordercolor=p["surface"],
                    arrowcolor=p["muted"], relief="flat")
    style.map("Vertical.TScrollbar",
              background=[("active", p["muted"])])

    # The default ttk class bindings make the mouse wheel CHANGE the value
    # of comboboxes and spinboxes under the pointer — in a lab GUI that can
    # silently switch the sweep device or walk count while scrolling the
    # page. Remove them; the wheel then scrolls the page as expected.
    for cls_name in ("TCombobox", "TSpinbox", "Spinbox"):
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>",
                    "<Shift-MouseWheel>", "<Shift-Button-4>",
                    "<Shift-Button-5>"):
            try:
                root.unbind_class(cls_name, seq)
            except tk.TclError:
                pass
    style.configure("TNotebook", background=p["surface"], borderwidth=0)
    style.configure("TNotebook.Tab", background=p["card"],
                    foreground=p["muted"], padding=(12, 5))
    style.map("TNotebook.Tab",
              background=[("selected", p["surface"])],
              foreground=[("selected", p["text"])])

    style.configure("Treeview", background=p["card"],
                    fieldbackground=p["card"], foreground=p["text"],
                    rowheight=26, borderwidth=0)
    style.configure("Treeview.Heading", background=p["surface"],
                    foreground=p["muted"], relief="flat", padding=4)
    style.map("Treeview", background=[("selected", p["select"])])
    return p
