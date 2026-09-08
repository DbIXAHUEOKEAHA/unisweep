"""Application-wide settings (``config/settings.json``).

These are the knobs that describe *how the software behaves and stores
data*, as opposed to *what a particular sweep does* — so they live on the
Settings page rather than the sweep or set/get pages, persist across
sessions, and are stamped into every :class:`SweepProgram` at start:

* map output: whether to save maps, worksheet grid vs single XYZ long
  file (or both), value-vs-index mapping, uniform grid, PNG mirrors;
* sweep behaviour defaults: ramp everything to zero when a sweep ends;
* engine protection: the stall-watchdog warn/abort budgets for sweepable
  instruments.
"""

from __future__ import annotations

import dataclasses
import json
import os

__all__ = ["AppSettings"]


@dataclasses.dataclass
class AppSettings:
    # ---- appearance ---------------------------------------------------
    theme: str = "dark"                # 'dark' | 'light'
    plots_on_top: bool = True          # graph/map windows above all apps
    # ---- map / data output -------------------------------------------
    save_maps: bool = True
    map_style: str = "grid"            # 'grid' | 'xyz' | 'both'
    map_interpolated: bool = True
    map_uniform: bool = False
    map_images: bool = True
    # ---- sweep behaviour ---------------------------------------------
    to_zero_default: bool = False
    connect_on_start: bool = True      # open all assigned instruments
                                       # in the background at launch
    # ---- sweepable-device protection ---------------------------------
    stall_warn_s: float = 3.0
    stall_abort_s: float = 12.0
    # ---- assistant endpoint -------------------------------------------
    #: serve the MCP agent endpoint from inside the running application
    agent_enabled: bool = False
    agent_port: int = 0                # 0 = let the OS pick a free port
    agent_token: str = ""              # generated on first enable
    # ---- notifications ------------------------------------------------
    #: 'service' — the shared Unisweep bot the group runs on its own
    #: server: the user supplies only a chat id and arranges everything
    #: else from Telegram.  'bot' — the original private-token mode, one
    #: message when a sweep ends and nothing more.
    tg_mode: str = "service"
    tg_enabled: bool = False
    tg_chat_id: str = ""
    tg_on_error: bool = True
    #: 'bot' mode only — a token from @BotFather, stored locally
    tg_token: str = ""
    #: 'service' mode: where the bot lives, and who this rig is.  The rig
    #: identity is generated on first use and is this installation's only
    #: credential; the database password never comes near this machine.
    tg_service_url: str = ""
    tg_rig_id: str = ""
    tg_rig_token: str = ""
    tg_rig_name: str = ""
    #: let the bot pause / stop / ramp-to-zero a running sweep.  Off by
    #: default, because it acts on real instruments.
    tg_allow_control: bool = False
    tg_push_s: float = 15.0
    tg_snapshot_s: float = 60.0

    # -----------------------------------------------------------------
    @classmethod
    def load(cls, core_dir: str) -> "AppSettings":
        path = os.path.join(core_dir, "config", "settings.json")
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError):
            return cls()
        fields = {f.name: f.type for f in dataclasses.fields(cls)}
        kwargs = {k: v for k, v in data.items() if k in fields}
        try:
            out = cls(**kwargs)
        except TypeError:
            return cls()
        if out.map_style not in ("grid", "xyz", "both"):
            out.map_style = "grid"
        if out.theme not in ("dark", "light"):
            out.theme = "dark"
        try:
            out.agent_port = int(out.agent_port)
        except (TypeError, ValueError):
            out.agent_port = 0
        if not 0 <= out.agent_port <= 65535:
            out.agent_port = 0
        out.stall_warn_s = max(float(out.stall_warn_s), 0.5)
        out.stall_abort_s = max(float(out.stall_abort_s),
                                out.stall_warn_s + 0.5)
        if out.tg_mode not in ("service", "bot"):
            out.tg_mode = "service"
        out.tg_chat_id = str(out.tg_chat_id or "").strip()
        out.tg_service_url = str(out.tg_service_url or "").strip().rstrip("/")
        try:
            out.tg_push_s = max(float(out.tg_push_s), 5.0)
        except (TypeError, ValueError):
            out.tg_push_s = 15.0
        try:
            out.tg_snapshot_s = max(float(out.tg_snapshot_s), out.tg_push_s)
        except (TypeError, ValueError):
            out.tg_snapshot_s = max(60.0, out.tg_push_s)
        return out

    def save(self, core_dir: str) -> None:
        path = os.path.join(core_dir, "config", "settings.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(dataclasses.asdict(self), fh, indent=2)
