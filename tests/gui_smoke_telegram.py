"""Smoke test for the Telegram section of the Settings page.

Needs a display, like ``gui_smoke.py``:

    xvfb-run -a python tests/gui_smoke_telegram.py

It builds the real application against the mock registry and then presses
the buttons a user presses — generate a code, look at who is linked, cut
somebody off — with a stub standing in for the link so no packet leaves
the machine.  The bug class it exists for: a Settings page that raises the
moment it is opened on a machine that has never been paired, and a
"Remove" button that silently does nothing.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk                                        # noqa: E402
import tkinter.messagebox as messagebox                     # noqa: E402

import unisweep.gui.app as appmod                           # noqa: E402
from tests.gui_smoke import FakeRegistry                    # noqa: E402

appmod.DeviceRegistry = FakeRegistry

# gui_smoke installs its own dialog stubs at import time, so these have to
# come after it: they must be the ones in force, and here the point is to
# confirm dialogs rather than decline them.
_boxes = []
for _name in ("showinfo", "showwarning", "showerror"):
    setattr(messagebox, _name,
            lambda t, m="", *a, _n=_name, **k: _boxes.append((_n, t, m)))
messagebox.askyesno = lambda *a, **k: True


class FakeLink:
    """Stands in for TelegramLink — no sockets, no threads."""

    def __init__(self):
        self.seen = []
        self.shutdown_noted = False
        self.links = []
        self.bot_link = "https://t.me/unisweep_lab_bot"
        self.bot_username = "unisweep_lab_bot"
        self.removed = []
        self.enabled = True
        self.started = False

    def configure(self, **kw):
        pass

    def start(self):
        self.started = True
        return True

    def stop(self, join=0, final_push=True):
        self.started = False
        if final_push:
            self.shutdown_noted = True

    def summary(self):
        return f"monitoring · {len(self.links)} Telegram user(s) linked"

    def request_code(self):
        return {"code": "418209", "ttl_s": 600, "bot_link": self.bot_link,
                "bot_username": self.bot_username}

    def remove_link(self, chat_id):
        self.removed.append(int(chat_id))
        self.links = [e for e in self.links
                      if int(e["chat_id"]) != int(chat_id)]
        return True

    def refresh_links(self):
        return self.links

    def report_result(self, *a):
        pass

    def on_event(self, event):
        self.seen.append(type(event).__name__)


def _toplevels(app):
    return [w for w in app.root.winfo_children() if isinstance(w, tk.Toplevel)]


def _labels(widget, out=None):
    out = [] if out is None else out
    for child in widget.winfo_children():
        if isinstance(child, tk.Label):
            out.append(str(child.cget("text")))
        _labels(child, out)
    return out


def _rows(page):
    return [tuple(str(v) for v in page.tg_users.item(i)["values"][:2])
            for i in page.tg_users.get_children()]


def main() -> int:
    core = tempfile.mkdtemp()
    os.makedirs(os.path.join(core, "config"), exist_ok=True)
    open(os.path.join(core, "config", "setup_complete"), "w").close()

    app = appmod.App(core)
    page = app.pages["Settings"]
    failed = []

    def check(name, fn):
        try:
            fn()
            print(f"PASS {name}")
        except Exception:
            import traceback
            print(f"FAIL {name}")
            traceback.print_exc()
            failed.append(name)

    def default_mode():
        assert page.tg_service.grid_info(), "the card is not on screen"
        assert page.tg_bot_link.cget("text")   # placeholder until known

    def help_popup():
        page._tg_help()
        assert _toplevels(app), "the ? button opened nothing"
        for win in _toplevels(app):
            win.destroy()

    def address_is_built_in():
        """Nobody should ever have to type the bot's address."""
        from unisweep.core.telegram_link import service_url
        assert service_url("").startswith("https://"), service_url("")
        assert service_url("https://other.example") == "https://other.example"

    def code_window():
        page._tg_generate_code()
        wins = _toplevels(app)
        assert wins, "no code window"
        texts = _labels(wins[-1])
        assert any("418 209" in t for t in texts), texts
        for win in wins:
            win.destroy()

    def listing():
        app.tg_link.links = [{"chat_id": 42, "title": "Misha (@misha)",
                              "since": "2026-09-08T10:00:00+08:00"}]
        page.refresh_telegram_status()
        assert _rows(page) == [("42", "Misha (@misha)")], _rows(page)
        assert "t.me" in page.tg_bot_link.cget("text")

    def removal():
        children = page.tg_users.get_children()
        assert children, "nothing to remove"
        page.tg_users.selection_set(children[0])
        page._tg_remove_user()
        assert app.tg_link.removed == [42], app.tg_link.removed
        assert _rows(page) == [], _rows(page)

    def only_the_necessary_boxes():
        """One bot: no mode radio, no token field, no address field."""
        for gone in ("v_tg_mode", "tg_own", "e_token", "e_service",
                     "v_tg_service_on", "tg_start_btn"):
            assert not hasattr(page, gone), gone
        # and the sweep-behaviour knobs are off this page too
        for gone in ("v_tozero", "v_autoconn", "e_warn", "e_abort"):
            assert not hasattr(page, gone), gone
        # what is left still works
        assert page.tg_code_btn and page.tg_refresh_btn and page.e_rig_name

    def persistence():
        from unisweep.core.settings import AppSettings
        page.e_rig_name.set("ATTODRY-1")
        page._changed()
        again = AppSettings.load(core)
        assert again.tg_rig_name == "ATTODRY-1", again.tg_rig_name
        assert again.tg_rig_id and again.tg_rig_token, "no identity minted"

    def name_clash_is_explained():
        """A name another setup already uses is a fixable mistake, so say
        which name and what to do, not 'HTTP 409'."""
        def boom():
            raise RuntimeError("HTTP 409: name_taken")
        app.tg_link.request_code = boom
        page.e_rig_name.set("ATTODRY-1")
        page._tg_generate_code()
        assert _boxes, "no warning shown"
        assert "already called" in _boxes[-1][2], _boxes[-1]
        assert "ATTODRY-1" in _boxes[-1][2], _boxes[-1]

    def colours_come_from_the_map_window():
        """The bot used to ask which colour scale to draw with. It should
        just use the one on screen, and the last one chosen when there is
        no window open."""
        assert app._map_cmap() in ("viridis", "")     # nothing opened yet
        app.plots._templates["map"] = {"cmap": "plasma"}
        assert app._map_cmap() == "plasma", "the saved choice is ignored"
        win = app.plots.spawn("map")
        try:
            win.config.cmap = "inferno"
            assert app._map_cmap() == "inferno", "the open window is ignored"
        finally:
            app.plots.remove(win)

    def closing_reports_the_sweep():
        """The bug: the engine's SweepFinished lands in the queue, the
        pump is cancelled, and the notification is built and binned."""
        from unisweep.core import events as ev
        app.event_queue.put(ev.SweepFinished(stopped=False, points=99))
        app.event_queue.put(("tg_status", "x", "active"))   # not an event
        app._drain_to_telegram()
        assert app.tg_link.seen == ["SweepFinished"], app.tg_link.seen
        assert app.event_queue.empty()

    app.tg_link = FakeLink()
    check("the notifications card is on screen", default_mode)
    check("the ? button opens the help window", help_popup)
    check("the bot address is built in", address_is_built_in)
    check("Generate code shows six digits", code_window)
    check("linked users and the bot link are listed", listing)
    check("Remove cuts the selected user off", removal)
    check("only the necessary boxes are left", only_the_necessary_boxes)
    check("settings survive a round trip through disk", persistence)
    check("a clashing setup name is explained", name_clash_is_explained)
    check("map colours follow the plot window", colours_come_from_the_map_window)
    check("closing hands the sweep-ended event to the link",
          closing_reports_the_sweep)

    app.root.update_idletasks()
    print(f"\n{len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
