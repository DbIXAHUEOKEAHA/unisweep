"""Smoke test for the Telegram section of the Settings page.

Needs a display, like ``gui_smoke.py``:

    xvfb-run -a python tests/gui_smoke_telegram.py

It builds the real application against the mock registry and then presses
the buttons a user presses — generate a code, look at who is linked, cut
somebody off, switch modes — with a stub standing in for the link so no
packet leaves the machine.  The bug class it exists for: a Settings page
that raises the moment it is opened on a machine that has never been
paired, and a "Remove" button that silently does nothing.
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
        pass


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
        assert app.settings.tg_mode == "service", app.settings.tg_mode
        assert page.tg_service.grid_info(), "service panel is not on screen"

    def help_popup():
        page._tg_help()
        assert _toplevels(app), "the ? button opened nothing"
        for win in _toplevels(app):
            win.destroy()

    def switch_on():
        app.settings.tg_service_url = "https://bot.example"
        page.e_service.set("https://bot.example")
        page.v_tg_service_on.set(True)
        page._tg_service_toggled()
        assert app.settings.tg_enabled, "reporting did not switch on"
        assert app.tg_link.started, "the link was never started"

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

    def modes():
        page.v_tg_mode.set("bot")
        page._tg_mode_changed()
        assert not page.tg_service.grid_info(), "service panel still shown"
        assert page.tg_own.grid_info(), "private-bot panel not shown"
        assert not app.tg_link.started, "reporting kept running in bot mode"
        page.v_tg_mode.set("service")
        page._tg_mode_changed()
        assert page.tg_service.grid_info(), "service panel did not come back"

    def persistence():
        from unisweep.core.settings import AppSettings
        app.settings.save(core)
        again = AppSettings.load(core)
        assert again.tg_mode == "service", again.tg_mode
        assert again.tg_service_url == "https://bot.example"

    def no_address():
        """Switching reporting on without an address must explain itself
        rather than starting a link that can never connect."""
        page.e_service.set("")
        page.v_tg_service_on.set(True)
        page._tg_service_toggled()
        assert not page.v_tg_service_on.get(), "left switched on"
        assert _boxes and "Telegram" in _boxes[-1][1], _boxes[-1:]
        page.e_service.set("https://bot.example")
        page._changed()

    app.tg_link = FakeLink()
    check("service mode is the default and is on screen", default_mode)
    check("the ? button opens the help window", help_popup)
    check("reporting switches on", switch_on)
    check("Generate code shows six digits", code_window)
    check("linked users and the bot link are listed", listing)
    check("Remove cuts the selected user off", removal)
    check("switching modes shows exactly one panel", modes)
    check("settings survive a round trip through disk", persistence)
    check("no service address is explained, not ignored", no_address)

    app.root.update_idletasks()
    print(f"\n{len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
