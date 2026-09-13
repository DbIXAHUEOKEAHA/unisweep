"""Settings page.

What belongs here is what a person changes rarely and deliberately:
appearance, where map data goes, who gets told about a sweep, the
assistant endpoint, the lab profile and the driver repository. Changes
save immediately and apply to the next sweep.

Engine tuning that has a sane default and a real cost to getting wrong —
the to-zero default, the auto-connect flag, the stall-watchdog budgets —
is deliberately *not* on this page. It still exists in
``config/settings.json`` and still applies; it is simply not something to
scroll past on the way to something else.
"""

from __future__ import annotations

import time
import tkinter as tk
from tkinter import messagebox, ttk

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
        self.v_ontop = tk.BooleanVar(value=st.plots_on_top)
        cb_top = ttk.Checkbutton(lbody, text="Keep graph and map windows "
                                             "on top of other applications",
                                 variable=self.v_ontop,
                                 command=self._changed)
        cb_top.grid(row=2, column=0, columnspan=3, sticky="w", pady=(6, 2))
        Tooltip(cb_top, "Plot windows stay visible above any program\n"
                        "(unless minimized). Applies to open windows\n"
                        "immediately and to new ones by default.")

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

        # ---------------- notifications ---------------------------------
        # One bot serves the whole group and every installation is built
        # knowing where it is, so there is no address to type and nothing
        # to switch on.  What is left is the two things a person actually
        # does: hand out a code, and see (or revoke) who holds one.
        noti = Card(self, title="Telegram notifications")
        noti.pack(fill="x", padx=10, pady=4)
        nbody = ttk.Frame(noti, style="Card.TFrame")
        nbody.grid(row=1, column=0, sticky="ew", pady=(4, 2))

        # ---- the default: a link, a code, and a list of people ---------
        self.tg_service = ttk.Frame(nbody, style="Card.TFrame")
        self.tg_service.grid(row=1, column=0, columnspan=4, sticky="ew")
        srv = self.tg_service
        bar = ttk.Frame(srv, style="Card.TFrame")
        bar.grid(row=1, column=0, columnspan=4, sticky="w")
        ttk.Label(bar, text="Bot", style="MutedS.TLabel").grid(
            row=0, column=0, sticky="w", padx=(0, 8))
        self.tg_bot_link = ttk.Label(bar, text="—", style="MonoMuted.TLabel")
        self.tg_bot_link.grid(row=0, column=1, sticky="w")
        self.tg_open_btn = ttk.Button(bar, text="Open", width=7,
                                      command=self._tg_open_bot)
        self.tg_open_btn.grid(row=0, column=2, sticky="w", padx=(10, 2))
        self.tg_copy_btn = ttk.Button(bar, text="Copy link", width=10,
                                      command=self._tg_copy_link)
        self.tg_copy_btn.grid(row=0, column=3, sticky="w", padx=2)
        self.tg_help_btn = ttk.Button(bar, text="?", width=3,
                                      command=self._tg_help)
        self.tg_help_btn.grid(row=0, column=4, sticky="w", padx=(8, 0))
        Tooltip(self.tg_help_btn, "How does this work?")

        self.tg_code_btn = ttk.Button(srv, text="Generate code",
                                      command=self._tg_generate_code)
        self.tg_code_btn.grid(row=2, column=0, sticky="w", pady=(8, 2))
        ttk.Label(srv, style="MutedS.TLabel",
                  text="— send the six digits to the bot to link your "
                       "Telegram account to this setup").grid(
            row=2, column=1, columnspan=3, sticky="w", padx=(8, 0))

        ttk.Label(srv, text="This setup is called",
                  style="MutedS.TLabel").grid(row=3, column=0, sticky="w",
                                              pady=2)
        self.e_rig_name = ValidatedEntry(srv, st.tg_rig_name, validator=str,
                                         allow_empty=True, width=24)
        self.e_rig_name.grid(row=3, column=1, sticky="w", padx=4)
        ttk.Label(srv, text="— the name shown in Telegram",
                  style="MutedS.TLabel").grid(row=3, column=2, columnspan=2,
                                              sticky="w", padx=(8, 0))

        # ---- who is linked, and how to remove them ---------------------
        ttk.Label(srv, text="Linked Telegram users",
                  style="MutedS.TLabel").grid(row=4, column=0, columnspan=4,
                                              sticky="w", pady=(8, 2))
        self.tg_users = ttk.Treeview(srv, columns=("id", "who", "since"),
                                     show="headings", height=4,
                                     selectmode="browse")
        self.tg_users.heading("id", text="User ID")
        self.tg_users.heading("who", text="Telegram name")
        self.tg_users.heading("since", text="Linked")
        self.tg_users.column("id", width=120, anchor="w")
        self.tg_users.column("who", width=260, anchor="w")
        self.tg_users.column("since", width=130, anchor="w")
        self.tg_users.grid(row=5, column=0, columnspan=4, sticky="ew")
        ubar = ttk.Frame(srv, style="Card.TFrame")
        ubar.grid(row=6, column=0, columnspan=4, sticky="w", pady=(4, 2))
        self.tg_remove_btn = ttk.Button(ubar, text="Remove selected",
                                        command=self._tg_remove_user)
        self.tg_remove_btn.pack(side="left")
        Tooltip(self.tg_remove_btn,
                "The bot stops sending that person anything about this\n"
                "setup immediately, and tells them it happened. They can\n"
                "link again with a new code.")
        self.tg_refresh_btn = ttk.Button(ubar, text="Update info",
                                         command=self._tg_refresh_users)
        Tooltip(self.tg_refresh_btn,
                "Ask the service who is linked right now. The list also\n"
                "refreshes on its own with every heartbeat, so this is\n"
                "for when you have just added or removed somebody.")
        self.tg_refresh_btn.pack(side="left", padx=8)

        self.v_tg_control = tk.BooleanVar(value=st.tg_allow_control)
        cb_ctl = ttk.Checkbutton(
            srv, text="Allow pause / stop / ramp-to-zero from Telegram",
            variable=self.v_tg_control, command=self._changed)
        cb_ctl.grid(row=7, column=0, columnspan=4, sticky="w", pady=(6, 2))
        Tooltip(cb_ctl, "Off by default. With it on, anyone linked to this\n"
                        "setup can stop a running sweep from their phone,\n"
                        "after a confirmation tap. The bot never sets a\n"
                        "value: it can only pause, stop, or stop and ramp\n"
                        "to zero — exactly the buttons on the Sweep page.")

        self.tg_link_status = ttk.Label(srv, text="", style="MutedS.TLabel",
                                        justify="left", wraplength=660)
        self.tg_link_status.grid(row=8, column=0, columnspan=4, sticky="w",
                                 pady=(4, 0))

        # ---------------- assistant endpoint ----------------------------
        agent = Card(self, title="Assistant endpoint (MCP)")
        agent.pack(fill="x", padx=10, pady=4)
        abody = ttk.Frame(agent, style="Card.TFrame")
        abody.grid(row=1, column=0, sticky="ew", pady=(4, 2))
        self.v_agent = tk.BooleanVar(value=st.agent_enabled)
        ttk.Checkbutton(
            abody, text="Serve the assistant endpoint while Unisweep runs",
            variable=self.v_agent, command=self._agent_changed).grid(
            row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(abody, text="Port", style="MutedS.TLabel").grid(
            row=1, column=0, sticky="w", pady=2)
        self.e_agent_port = ValidatedEntry(abody, st.agent_port,
                                           validator=int, width=8)
        self.e_agent_port.grid(row=1, column=1, sticky="w", padx=4)
        ttk.Label(abody, text="0 = pick a free port",
                  style="MutedS.TLabel").grid(row=1, column=2, sticky="w")
        self.agent_status = ttk.Label(abody, text="", style="MutedS.TLabel",
                                      justify="left", wraplength=680)
        self.agent_status.grid(row=2, column=0, columnspan=3, sticky="w",
                               pady=(4, 0))
        self.agent_copy_btn = ttk.Button(abody,
                                         text="Copy client config",
                                         command=self._agent_copy)
        self.agent_copy_btn.grid(row=3, column=0, sticky="w", pady=(6, 2))
        self.agent_cmd = ttk.Label(abody, text="", style="MutedS.TLabel",
                                   justify="left", wraplength=560)
        self.agent_cmd.grid(row=3, column=1, columnspan=2, sticky="w",
                            padx=4)
        self.connector_btn = ttk.Button(
            abody, text="Copy connector link (claude.ai)",
            command=self._connector_copy)
        self.connector_btn.grid(row=4, column=0, sticky="w", pady=(2, 2))
        ttk.Label(abody, text="for Settings → Connectors, on the web and "
                              "your phone", style="MutedS.TLabel").grid(
            row=4, column=1, columnspan=2, sticky="w", padx=4)
        ttk.Label(abody, style="MutedS.TLabel", justify="left",
                  wraplength=680, text=(
            "An assistant drives this same window: it fills in the fields "
            "and presses the buttons, and every change is visible here — "
            "you can take over at any moment. What it may do to an "
            "instrument is bounded by the lab profile below.\n"
            "Two ways in. The client config runs a pipe on this computer: "
            "Claude Desktop and Claude Code only, nothing leaves the "
            "machine. The connector link goes through the group's "
            "notification service, so it works in claude.ai on any device "
            "— issuing a new one revokes the old.")).grid(
            row=5, column=0, columnspan=3, sticky="w", pady=(6, 0))
        self._refresh_agent_status()

        # ---------------- lab profile -----------------------------------
        prof = Card(self, title="Lab profile (safety envelope)")
        prof.pack(fill="x", padx=10, pady=4)
        pbody = ttk.Frame(prof, style="Card.TFrame")
        pbody.grid(row=1, column=0, sticky="ew", pady=(4, 2))
        self.profile_status = ttk.Label(pbody, text="", style="MutedS.TLabel",
                                        justify="left", wraplength=680)
        self.profile_status.grid(row=0, column=0, columnspan=2, sticky="w")
        self.profile_reload_btn = ttk.Button(
            pbody, text="Reload lab profile", command=self._reload_profile)
        self.profile_reload_btn.grid(row=1, column=0, sticky="w",
                                     pady=(6, 2))
        ttk.Label(pbody, style="MutedS.TLabel", justify="left",
                  wraplength=680, text=(
            "config/lab_profile.json gives every parameter a name, a unit "
            "and a safe range, and its limits are enforced on every set — "
            "by the sweep engine, by this page and by anything driving "
            "Unisweep. With no file, nothing is enforced. "
            "See docs/LAB_PROFILE.md.")).grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(2, 0))
        self._refresh_profile_status()

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
        self.save_repo_btn = ttk.Button(bar, text="Save repository settings",
                                        command=self._save_repo)
        self.save_repo_btn.pack(side="left")
        self.update_catalog_btn = ttk.Button(
            bar, text="Update catalog now",
            command=lambda: self.app.refresh_catalog_async(manual=True))
        self.update_catalog_btn.pack(side="left", padx=8)
        self.repo_status = ttk.Label(body, text="", style="MutedS.TLabel")
        self.repo_status.grid(row=4, column=0, columnspan=4, sticky="w")

    # -----------------------------------------------------------------
    def _refresh_agent_status(self):
        try:
            self.agent_status.configure(text=self.app.agent_summary())
            self.agent_cmd.configure(
                text=self.app.agent_command()
                if self.v_agent.get() else "")
        except Exception:                          # noqa: BLE001
            self.agent_status.configure(text="agent endpoint unavailable")

    def _agent_changed(self):
        st = self.app.settings
        st.agent_enabled = self.v_agent.get()
        port = self.e_agent_port.value()
        st.agent_port = int(port) if port is not None else 0
        st.save(self.app.core_dir)
        if st.agent_enabled:
            if not self.app.start_agent_endpoint():
                self.v_agent.set(False)
                st.agent_enabled = False
                st.save(self.app.core_dir)
        else:
            self.app.stop_agent_endpoint()
        self._refresh_agent_status()

    def _connector_copy(self):
        """The URL and token for Settings → Connectors in claude.ai.

        A different thing from the client config above: that one runs a
        pipe on this computer and works in Claude Desktop only; this one
        goes through the group's service and works everywhere, phone
        included. Pressing it again issues a new token, which is how an
        assistant is cut off.
        """
        try:
            issued = self.app.tg_link.connector_token()
        except Exception as exc:                       # noqa: BLE001
            messagebox.showwarning(
                "Connector",
                f"Could not get a connector token:\n\n{exc}")
            return
        text = (f"URL:   {issued['url']}\n"
                f"Token: {issued['token']}")
        self._copy(text)
        messagebox.showinfo(
            "Connector",
            "Copied. In claude.ai open Settings → Connectors → Add custom "
            "connector, paste the URL, and put the token in as a bearer "
            "header.\n\nIssuing this replaces any earlier token, so an "
            "assistant configured with the old one stops working.\n\n"
            + text)

    def _agent_copy(self):
        # the whole server entry, not the bare command: a client launches
        # the pipe from its own directory, where 'unisweep' is not
        # importable, and the cwd in here is what makes it work
        command = self.app.agent_client_config()
        try:
            self.app.root.clipboard_clear()
            self.app.root.clipboard_append(command)
            self.app.status("Client command copied to the clipboard")
        except Exception:                          # noqa: BLE001
            self.app.status(command)

    # -----------------------------------------------------------------
    def _refresh_profile_status(self):
        try:
            self.profile_status.configure(text=self.app.profile_summary())
        except Exception:                          # noqa: BLE001
            self.profile_status.configure(text="lab profile unavailable")

    def _reload_profile(self):
        self.app.reload_profile()
        self._refresh_profile_status()
        problems = getattr(self.app, "profile_problems", [])
        if problems:
            listing = "\n".join(f"  {p}" for p in problems[:20])
            messagebox.showwarning("Lab profile",
                                   f"Loaded with findings:\n{listing}")
        self.app.status(self.app.profile_summary())

    # -----------------------------------------------------------------
    def controls(self) -> list:
        """Named handles for the Settings page."""
        from ..agent import controls as ctl
        page = "settings"
        changed = self._changed
        return [
            ctl.option_var("settings.theme", self.v_theme, ("dark", "light"),
                           page=page, label="Theme",
                           after_set=self._theme_changed),
            ctl.flag("settings.plots_on_top", self.v_ontop, page=page,
                     label="Keep plot windows on top", after_set=changed),
            ctl.flag("settings.save_maps", self.v_save, page=page,
                     label="Write 2-D/3-D map files", after_set=changed),
            ctl.option_var("settings.map_style", self.v_style,
                           ("grid", "xyz", "both"), page=page,
                           label="Map file format", after_set=changed,
                           help="grid = legacy worksheet, xyz = one long "
                                "file per read parameter, both = each."),
            ctl.flag("settings.map_interpolated", self.v_interp, page=page,
                     label="Map samples onto the grid by value",
                     after_set=changed),
            ctl.flag("settings.map_uniform", self.v_uniform, page=page,
                     label="Force a uniformly spaced map grid",
                     after_set=changed),
            ctl.flag("settings.map_images", self.v_images, page=page,
                     label="Keep PNG (and 3-D GIF) map mirrors",
                     after_set=changed),
            ctl.entry_text("settings.telegram_rig_name", self.e_rig_name,
                           page=page,
                           label="Name this setup shows in Telegram",
                           help="Must be unique across the lab — it is how "
                                "people tell setups apart in the chat."),
            ctl.flag("settings.telegram_allow_control", self.v_tg_control,
                     page=page, after_set=changed,
                     label="Allow pause/stop from Telegram"),
            ctl.action("settings.telegram_generate_code", self.tg_code_btn,
                       page=page,
                       label="Generate a Telegram pairing code",
                       help="Shows six digits; whoever sends them to the "
                            "bot is linked to this setup."),
            ctl.action("settings.telegram_update", self.tg_refresh_btn,
                       page=page, label="Update the linked-user list"),
            ctl.readout("settings.telegram_link",
                        self.app.telegram_summary, page=page,
                        label="Telegram link status"),
            ctl.readout("settings.telegram_users",
                        self.app.telegram_users_summary, page=page,
                        label="Linked Telegram users"),
            ctl.flag("settings.agent_enabled", self.v_agent, page=page,
                     label="Serve the assistant endpoint",
                     after_set=self._agent_changed),
            ctl.number("settings.agent_port", self.e_agent_port, page=page,
                       label="Assistant endpoint port",
                       help="0 lets the OS pick a free port."),
            ctl.readout("settings.agent_status", self.app.agent_summary,
                        page=page, label="Assistant endpoint status"),
            ctl.readout("settings.agent_command", self.app.agent_command,
                        page=page, label="MCP client command"),
            ctl.readout("settings.lab_profile", self.app.profile_summary,
                        page=page, label="Lab profile"),
            ctl.action("settings.reload_lab_profile",
                       self.profile_reload_btn, page=page,
                       label="Reload the lab profile"),
            ctl.entry_text("settings.driver_repo", self.e_repo, page=page,
                           label="Driver repository"),
            ctl.entry_text("settings.driver_branch", self.e_branch,
                           page=page, label="Driver repository branch"),
            ctl.entry_text("settings.driver_folder", self.e_folder,
                           page=page, label="Driver repository folder"),
            ctl.entry_text("settings.driver_base_url", self.e_base,
                           page=page, label="Driver base_url override"),
            ctl.action("settings.save_repo", self.save_repo_btn, page=page,
                       label="Save repository settings"),
            ctl.action("settings.update_catalog", self.update_catalog_btn,
                       page=page, label="Update the driver catalog now"),
            ctl.readout("settings.catalog_status",
                        lambda: self.repo_status.cget("text"), page=page,
                        label="Driver catalog status"),
        ]

    # ---------------- telegram ----------------------------------------
    def _tg_help(self):
        """The pop-up behind the '?' — how the whole thing works."""
        win = tk.Toplevel(self.app.root)
        win.title("Telegram notifications")
        win.configure(bg=PALETTE["surface"])
        win.transient(self.app.root)
        win.resizable(False, False)
        frame = ttk.Frame(win, padding=16)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Linking a Telegram account to this setup",
                  style="Title.TLabel").pack(anchor="w")
        steps = (
            "1.  Open the bot in Telegram.\n"
            "        Press  Open  above, or  Copy link  and paste it into\n"
            "        Telegram. It is the same bot for the whole group, and\n"
            "        it runs on the group's server — not on this computer.\n"
            "\n"
            "2.  Press  Generate code  here.\n"
            "        You get six digits, valid for a few minutes.\n"
            "\n"
            "3.  Send those six digits to the bot.\n"
            "        That is the whole sign-up: no chat id to look up and\n"
            "        nothing else to type here. Your Telegram account then\n"
            "        appears in the list of linked users below.\n"
            "\n"
            "4.  Everything else happens in the chat.\n"
            "        /menu chooses what you are told about, /status shows\n"
            "        progress and the latest readings, /table the data,\n"
            "        /plot a parameter against the fast axis, /map a 2-D\n"
            "        map of one.\n"
            "\n"
            "By default the bot writes when a sweep ends, when an error or\n"
            "a guard stops it, and when this computer stops reporting at\n"
            "all — the one failure a notifier running here could never\n"
            "tell you about. Each person can change that for themselves.\n"
            "\n"
            "To cut somebody off, select them below and press Remove: the\n"
            "bot stops sending them anything about this setup at once, and\n"
            "tells them so. Give out a new code to let them back in.\n"
            "\n"
            "A code is deliberately short-lived and single-use, so one left\n"
            "on the screen is not a standing invitation."
        )
        text = tk.Text(frame, width=66, height=27, wrap="word", relief="flat",
                       bg=PALETTE["card"], fg=PALETTE["text"],
                       padx=10, pady=8, borderwidth=0,
                       highlightthickness=0)
        text.insert("1.0", steps)
        text.configure(state="disabled")   # readable and copyable, not edited
        text.pack(fill="both", expand=True, pady=(10, 8))
        ttk.Button(frame, text="Close", command=win.destroy).pack(anchor="e")
        win.bind("<Escape>", lambda _e: win.destroy())
        try:
            win.grab_set()
        except tk.TclError:
            pass

    # -----------------------------------------------------------------
    def _bot_url(self) -> str:
        """The bot's Telegram address, as the service reported it.

        Never hard-coded here: the service knows its own @name (it asks
        Telegram at start-up) and hands it back on every heartbeat, so
        renaming the bot cannot leave stale links in the software.
        """
        return getattr(self.app.tg_link, "bot_link", "") or ""

    def _tg_open_bot(self):
        url = self._bot_url()
        if not url:
            messagebox.showinfo(
                "Telegram",
                "The bot's address is not known yet — this setup has not "
                "reached the service. Press 'Update info'; if it stays "
                "unknown, the notification service is down or this "
                "computer has no route to it.")
            return
        import webbrowser
        webbrowser.open(url)

    def _tg_copy_link(self):
        url = self._bot_url()
        if not url:
            self.app.status("the bot address is not known yet")
            return
        try:
            self.app.root.clipboard_clear()
            self.app.root.clipboard_append(url)
            self.app.status(f"Bot link copied: {url}")
        except tk.TclError:
            self.app.status(url)

    def _tg_generate_code(self):
        """Ask the service for a pairing code and put it on screen."""
        self._changed()
        try:
            issued = self.app.telegram_pairing_code()
        except Exception as exc:                       # noqa: BLE001
            detail = str(exc)
            if "name_taken" in detail:
                detail = (f"another setup in the lab is already called "
                          f"'{self.e_rig_name.value() or ''}'. Give this one "
                          f"a different name and try again.")
            messagebox.showwarning(
                "Telegram", f"Could not get a pairing code:\n\n{detail}")
            self.refresh_telegram_status()
            return
        self._show_code_window(issued)

    def _show_code_window(self, issued: dict):
        win = tk.Toplevel(self.app.root)
        win.title("Pairing code")
        win.configure(bg=PALETTE["surface"])
        win.transient(self.app.root)
        win.resizable(False, False)
        frame = ttk.Frame(win, padding=18)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Send this code to the bot",
                  style="Title.TLabel").pack(anchor="w")
        code = issued.get("code", "")
        spaced = f"{code[:3]} {code[3:]}" if len(code) == 6 else code
        big = tk.Label(frame, text=spaced, font=("Consolas", 40, "bold"),
                       bg=PALETTE["card"], fg=PALETTE["text"],
                       padx=24, pady=10)
        big.pack(fill="x", pady=(12, 8))
        link = issued.get("bot_link") or self._bot_url()
        ttk.Label(frame, style="MutedS.TLabel", justify="left",
                  wraplength=420,
                  text=(f"Open {link or 'the bot'} in Telegram and send it "
                        f"these six digits. Anyone who does is linked to "
                        f"this setup.")).pack(anchor="w")
        countdown = ttk.Label(frame, text="", style="MutedS.TLabel")
        countdown.pack(anchor="w", pady=(8, 0))
        row = ttk.Frame(frame)
        row.pack(fill="x", pady=(12, 0))
        ttk.Button(row, text="Copy code",
                   command=lambda: self._copy(code)).pack(side="left")
        if link:
            ttk.Button(row, text="Open bot",
                       command=self._tg_open_bot).pack(side="left", padx=8)
        ttk.Button(row, text="Close", command=win.destroy).pack(side="right")
        win.bind("<Escape>", lambda _e: win.destroy())

        # While the code is on screen, keep asking the service who is
        # linked: the moment somebody uses it, this window says so instead
        # of leaving the user wondering whether it worked.
        deadline = time.time() + float(issued.get("ttl_s") or 600.0)
        before = len(getattr(self.app.tg_link, "links", []))

        def tick():
            if not win.winfo_exists():
                return
            left = int(deadline - time.time())
            if left <= 0:
                countdown.configure(text="This code has expired — generate "
                                         "a new one.")
                big.configure(fg=PALETTE["muted"])
                return
            countdown.configure(text=f"valid for {left // 60}:"
                                     f"{left % 60:02d} more")
            now = len(getattr(self.app.tg_link, "links", []))
            if now > before:
                self.refresh_telegram_status()
                countdown.configure(text="✅ Linked — you can close this.")
                big.configure(fg=PALETTE["green"])
                return
            self.app.telegram_refresh_links()
            win.after(3000, tick)

        win.after(500, tick)
        try:
            win.grab_set()
        except tk.TclError:
            pass

    def _copy(self, text: str):
        try:
            self.app.root.clipboard_clear()
            self.app.root.clipboard_append(text)
            self.app.status("copied to the clipboard")
        except tk.TclError:
            pass

    def _tg_remove_user(self):
        selected = self.tg_users.selection()
        if not selected:
            self.app.status("select a linked user first")
            return
        item = self.tg_users.item(selected[0])
        chat_id = item["values"][0] if item.get("values") else None
        who = item["values"][1] if item.get("values") else ""
        if chat_id is None:
            return
        if not messagebox.askyesno(
                "Remove user",
                f"Stop sending anything about this setup to "
                f"{who or chat_id}?\n\nThe bot tells them it happened. They "
                f"can link again with a new code."):
            return
        try:
            self.app.telegram_remove_user(chat_id)
        except Exception as exc:                       # noqa: BLE001
            messagebox.showwarning("Telegram",
                                   f"Could not remove that user:\n\n{exc}")
        self.refresh_telegram_status()

    def _tg_refresh_users(self):
        self.app.telegram_refresh_links()
        self.refresh_telegram_status()

    def refresh_telegram_status(self):
        """Called from the event pump whenever the link reports in."""
        try:
            self.tg_link_status.configure(text=self.app.telegram_summary())
            url = self._bot_url()
            self.tg_bot_link.configure(text=url or "—")
            links = list(getattr(self.app.tg_link, "links", []))
            self.tg_users.delete(*self.tg_users.get_children())
            for entry in links:
                since = str(entry.get("since") or "")[:16].replace("T", " ")
                self.tg_users.insert(
                    "", "end", values=(entry.get("chat_id", ""),
                                       entry.get("title") or "—", since))
        except tk.TclError:
            pass
        except Exception:                              # noqa: BLE001
            pass

    def _theme_changed(self):
        self.app.set_theme(self.v_theme.get())

    def _changed(self):
        st = self.app.settings
        st.save_maps = self.v_save.get()
        st.map_style = self.v_style.get()
        st.map_interpolated = self.v_interp.get()
        st.map_uniform = self.v_uniform.get()
        st.map_images = self.v_images.get()
        st.plots_on_top = self.v_ontop.get()
        st.tg_rig_name = (self.e_rig_name.value() or "").strip()
        st.tg_allow_control = self.v_tg_control.get()
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
