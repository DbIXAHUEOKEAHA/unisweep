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
    # There is one bot for the whole group and every installation is
    # configured for it out of the box, so there is nothing to switch on
    # and no address to type.  What is stored here is only who *this*
    # setup is: an identity it generated for itself the first time it
    # reported.  Nothing is delivered to anybody until a person pairs
    # with a code.
    tg_rig_id: str = ""
    tg_rig_token: str = ""
    tg_rig_name: str = ""
    #: normally empty — the address is compiled in; see
    #: ``unisweep.core.telegram_link.service_url``.  Set only when running
    #: against a private copy of the service.
    tg_service_url: str = ""
    #: let the bot pause / stop / ramp-to-zero a running sweep.  Off by
    #: default, because it acts on real instruments.
    tg_allow_control: bool = False
    tg_push_s: float = 15.0
    tg_snapshot_s: float = 60.0

    # -----------------------------------------------------------------
    def ensure_rig_identity(self, core_dir: str,
                            default_name: str = "") -> bool:
        """Give this installation its name-tag if it has none yet.

        The application starts reporting the moment it launches, so the
        identity has to exist before that — not when somebody first
        presses "Generate code". Without this, a fresh install reports
        *problem: service address or rig identity missing* on the
        notifications page forever: a fault message for a setup where
        nothing is wrong, only unpaired.

        A random id and token, no network, nothing delivered to anybody
        until a person pairs with a code. Returns True if it wrote.
        """
        from .telegram_link import new_rig_identity
        changed = False
        if not self.tg_rig_id or not self.tg_rig_token:
            self.tg_rig_id, self.tg_rig_token = new_rig_identity()
            changed = True
        if not self.tg_rig_name and default_name:
            self.tg_rig_name = default_name[:64]
            changed = True
        if changed:
            self.save(core_dir)
        return changed

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
