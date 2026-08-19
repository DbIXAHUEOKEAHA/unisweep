"""Settings page.

Everything that is not the definition of a particular sweep or set/get
action lives here: data-output choices (map worksheets vs the single XYZ
long file, interpolation, uniform grid, PNG mirrors), sweep-behaviour
defaults (to-zero on finish), the sweepable stall-watchdog budgets, and the
driver-repository configuration. Changes save immediately and apply to the
next sweep.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .theme import PALETTE
from .widgets import Card, Tooltip, ValidatedEntry


class SettingsPage(ttk.Frame):

    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        st = app.settings

        # ---------------- appearance ------------------------------------
        look = Card(self, title="Appearance")
        look.pack(fill="x", padx=10, pady=(10, 4))
        lbody = ttk.Frame(look, style="Card.TFrame")
        lbody.grid(row=1, column=0, sticky="ew", pady=(4, 2))
        ttk.Label(lbody, text="Theme", style="MutedS.TLabel").grid(
            row=0, column=0, sticky="w", padx=(0, 8))
        self.v_theme = tk.StringVar(value=st.theme)
        for col, (value, text) in enumerate((("dark", "Dark"),
                                             ("light", "Light"))):
            ttk.Radiobutton(lbody, text=text, value=value,
                            variable=self.v_theme,
                            command=self._theme_changed).grid(
                row=0, column=1 + col, sticky="w", padx=(0, 14))
        ttk.Label(lbody, style="MutedS.TLabel",
                  text="Applies immediately to every window, including "
                       "open plots.").grid(row=1, column=0, columnspan=3,
                                           sticky="w", pady=(2, 0))

        # ---------------- map / data output ----------------------------
        maps = Card(self, title="Map data output (2-D / 3-D sweeps)")
        maps.pack(fill="x", padx=10, pady=(10, 4))
        body = ttk.Frame(maps, style="Card.TFrame")
        body.grid(row=1, column=0, sticky="ew", pady=(4, 2))

        self.v_save = tk.BooleanVar(value=st.save_maps)
        cb = ttk.Checkbutton(body, text="Save map data files",
                             variable=self.v_save, command=self._changed)
        cb.grid(row=0, column=0, sticky="w", pady=2, columnspan=3)
        Tooltip(cb, "Live map plots work regardless — this controls files "
                    "on disk.")

        ttk.Label(body, text="Format", style="MutedS.TLabel").grid(
            row=1, column=0, sticky="w", padx=(16, 8))
        self.v_style = tk.StringVar(value=st.map_style)
        for col, (value, text, tip) in enumerate((
                ("grid", "Grid worksheet",
                 "Legacy spreadsheet: header = the inner walk grid, one\n"
                 "line appended per outer point (2d_maps/tables)."),
                ("xyz", "Single XYZ file",
                 "One continuous file per read parameter: a row per\n"
                 "measured point with the axis values as X(,Y),Z columns —\n"
                 "raw coordinates, never re-gridded (2d_maps/.../xyz).\n"
                 "A 3-D sweep stays in ONE file, master value first."),
                ("both", "Both", "Write the worksheet and the XYZ file."))):
            rb = ttk.Radiobutton(body, text=text, value=value,
                                 variable=self.v_style,
                                 command=self._changed)
            rb.grid(row=1, column=1 + col, sticky="w", padx=(0, 12))
            Tooltip(rb, tip)

        self.v_interp = tk.BooleanVar(value=st.map_interpolated)
        cb = ttk.Checkbutton(body, text="Map samples onto the grid by value "
                                        "(per walk segment)",
                             variable=self.v_interp, command=self._changed)
        cb.grid(row=2, column=0, sticky="w", pady=2, columnspan=3,
                padx=(16, 0))
        Tooltip(cb, "On: each worksheet cell takes the nearest sample of the\n"
                    "matching walk segment — right for sweepable devices\n"
                    "whose readback lands between grid points. Forward and\n"
                    "backward walks are matched separately (hysteresis is\n"
                    "preserved) and NaN holes are never smeared.\n"
                    "Off: sample k lands in cell k (exact for stepwise).")
        self.v_uniform = tk.BooleanVar(value=st.map_uniform)
        cb = ttk.Checkbutton(body, text="Force a uniformly spaced grid",
                             variable=self.v_uniform, command=self._changed)
        cb.grid(row=3, column=0, sticky="w", pady=2, columnspan=3,
                padx=(16, 0))
        Tooltip(cb, "Replace the planned grid (e.g. a non-uniform manual\n"
                    "step file) by a uniform linspace over the same range —\n"
                    "samples are mapped onto it by value.")
        self.v_images = tk.BooleanVar(value=st.map_images)
        cb = ttk.Checkbutton(body, text="Render PNG mirrors (and 3-D GIF "
                                        "stacks)",
                             variable=self.v_images, command=self._changed)
        cb.grid(row=4, column=0, sticky="w", pady=2, columnspan=3,
                padx=(16, 0))

        # ---------------- sweep behaviour ------------------------------
        beh = Card(self, title="Sweep behaviour")
        beh.pack(fill="x", padx=10, pady=4)
        body = ttk.Frame(beh, style="Card.TFrame")
        body.grid(row=1, column=0, sticky="ew", pady=(4, 2))
        self.v_tozero = tk.BooleanVar(value=st.to_zero_default)
        ttk.Checkbutton(body, text="Ramp all axes to zero when a sweep "
                                   "finishes",
                        variable=self.v_tozero,
                        command=self._changed).grid(row=0, column=0,
                                                    sticky="w", pady=2)

        ttk.Label(body, text="Sweepable stall watchdog:  warn after",
                  style="MutedS.TLabel").grid(row=1, column=0, sticky="w",
                                              pady=2)
        self.e_warn = ValidatedEntry(body, st.stall_warn_s, width=6)
        self.e_warn.grid(row=1, column=1, sticky="w", padx=4)
        ttk.Label(body, text="s, abort after",
                  style="MutedS.TLabel").grid(row=1, column=2, sticky="w")
        self.e_abort = ValidatedEntry(body, st.stall_abort_s, width=6)
        self.e_abort.grid(row=1, column=3, sticky="w", padx=4)
        ttk.Label(body, text="s of no readback progress",
                  style="MutedS.TLabel").grid(row=1, column=4, sticky="w")
        for e in (self.e_warn, self.e_abort):
            e.bind("<FocusOut>", lambda _e: self._changed())
            e.bind("<Return>", lambda _e: self._changed())

        # ---------------- notifications ---------------------------------
        noti = Card(self, title="Notifications (Telegram)")
        noti.pack(fill="x", padx=10, pady=4)
        nbody = ttk.Frame(noti, style="Card.TFrame")
        nbody.grid(row=1, column=0, sticky="ew", pady=(4, 2))
        self.v_tg = tk.BooleanVar(value=st.tg_enabled)
        cb = ttk.Checkbutton(nbody, text="Send a Telegram message when a "
                                         "sweep ends",
                             variable=self.v_tg, command=self._changed)
        cb.grid(row=0, column=0, columnspan=4, sticky="w", pady=2)
        Tooltip(cb, "Create a bot with @BotFather to get the token; get\n"
                    "your chat id from @userinfobot (send it any message).\n"
                    "The token is stored locally in config/settings.json.")
        ttk.Label(nbody, text="Bot token", style="MutedS.TLabel").grid(
            row=1, column=0, sticky="w", pady=2)
        self.e_token = ValidatedEntry(nbody, st.tg_token, validator=str,
                                      allow_empty=True, width=46)
        self.e_token.grid(row=1, column=1, columnspan=3, sticky="w", padx=4)
        ttk.Label(nbody, text="Chat id", style="MutedS.TLabel").grid(
            row=2, column=0, sticky="w", pady=2)
        self.e_chat = ValidatedEntry(nbody, st.tg_chat_id, validator=str,
                                     allow_empty=True, width=18)
        self.e_chat.grid(row=2, column=1, sticky="w", padx=4)
        self.v_tg_err = tk.BooleanVar(value=st.tg_on_error)
        ttk.Checkbutton(nbody, text="also when a sweep stops on an error",
                        variable=self.v_tg_err,
                        command=self._changed).grid(row=2, column=2,
                                                    columnspan=2,
                                                    sticky="w", padx=(14, 0))
        ttk.Button(nbody, text="Send test message",
                   command=self._tg_test).grid(row=3, column=1, sticky="w",
                                               padx=4, pady=(6, 2))
        self.tg_status = ttk.Label(nbody, text="", style="MutedS.TLabel")
        self.tg_status.grid(row=3, column=2, columnspan=2, sticky="w",
                            padx=8)
        for e in (self.e_token, self.e_chat):
            e.bind("<FocusOut>", lambda _e: self._changed())
            e.bind("<Return>", lambda _e: self._changed())

        # ---------------- driver repository ----------------------------
        repo = Card(self, title="Driver repository (GitHub auto-discovery)")
        repo.pack(fill="x", padx=10, pady=4)
        body = ttk.Frame(repo, style="Card.TFrame")
        body.grid(row=1, column=0, sticky="ew", pady=(4, 2))
        cat = app.catalog
        ttk.Label(body, text="Repository", style="MutedS.TLabel").grid(
            row=0, column=0, sticky="w", pady=2)
        self.e_repo = ValidatedEntry(body, cat.repo, validator=str,
                                     allow_empty=True, width=34)
        self.e_repo.grid(row=0, column=1, sticky="w", padx=4)
        ttk.Label(body, text="Branch", style="MutedS.TLabel").grid(
            row=0, column=2, sticky="e")
        self.e_branch = ValidatedEntry(body, cat.branch, validator=str,
                                       allow_empty=True, width=10)
        self.e_branch.grid(row=0, column=3, sticky="w", padx=4)
        ttk.Label(body, text="Folder", style="MutedS.TLabel").grid(
            row=1, column=0, sticky="w", pady=2)
        self.e_folder = ValidatedEntry(body, cat.repo_folder, validator=str,
                                       allow_empty=True, width=16)
        self.e_folder.grid(row=1, column=1, sticky="w", padx=4)
        ttk.Label(body, text="base_url override",
                  style="MutedS.TLabel").grid(row=2, column=0, sticky="w",
                                              pady=2)
        self.e_base = ValidatedEntry(body, cat.base_url or "", validator=str,
                                     allow_empty=True, width=48)
        self.e_base.grid(row=2, column=1, columnspan=3, sticky="w", padx=4)
        bar = ttk.Frame(body, style="Card.TFrame")
        bar.grid(row=3, column=0, columnspan=4, sticky="w", pady=(6, 2))
        ttk.Button(bar, text="Save repository settings",
                   command=self._save_repo).pack(side="left")
        ttk.Button(bar, text="Update catalog now",
                   command=lambda: self.app.refresh_catalog_async(
                       manual=True)).pack(side="left", padx=8)
        self.repo_status = ttk.Label(body, text="", style="MutedS.TLabel")
        self.repo_status.grid(row=4, column=0, columnspan=4, sticky="w")

    # -----------------------------------------------------------------
    def _tg_test(self):
        from ..core.notify import TelegramNotifier
        self._changed()
        st = self.app.settings
        notifier = TelegramNotifier(st.tg_token, st.tg_chat_id)
        if not notifier.configured:
            self.tg_status.configure(text="enter a token and a chat id "
                                          "first")
            return
        self.tg_status.configure(text="sending…")
        notifier.send_async(
            "Unisweep: test message — notifications are working.",
            done=lambda ok, d: self.app.event_queue.put(
                ("notify_result", d)))

    def _theme_changed(self):
        self.app.set_theme(self.v_theme.get())

    def _changed(self):
        st = self.app.settings
        st.save_maps = self.v_save.get()
        st.map_style = self.v_style.get()
        st.map_interpolated = self.v_interp.get()
        st.map_uniform = self.v_uniform.get()
        st.map_images = self.v_images.get()
        st.to_zero_default = self.v_tozero.get()
        st.tg_enabled = self.v_tg.get()
        st.tg_on_error = self.v_tg_err.get()
        st.tg_token = (self.e_token.value() or "").strip()
        st.tg_chat_id = (self.e_chat.value() or "").strip()
        warn = self.e_warn.value()
        abort = self.e_abort.value()
        if warn is not None and warn > 0:
            st.stall_warn_s = float(warn)
        if abort is not None and abort > st.stall_warn_s:
            st.stall_abort_s = float(abort)
        st.save(self.app.core_dir)
        self.app.apply_settings()

    def _save_repo(self):
        cat = self.app.catalog
        cat.repo = (self.e_repo.value() or "").strip()
        cat.branch = (self.e_branch.value() or "main").strip() or "main"
        cat.repo_folder = (self.e_folder.value() or "devices").strip() \
            or "devices"
        cat.base_url = (self.e_base.value() or "").strip() or None
        try:
            cat.save_user_config()
            self.repo_status.configure(
                text="saved to config/driver_catalog.json")
        except OSError as exc:
            self.repo_status.configure(text=f"could not save: {exc}")
