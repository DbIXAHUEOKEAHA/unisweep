"""A fresh install: git clone, python main.py, nothing else.

Every other GUI test replaces ``DeviceRegistry`` with a fake, because the
real one opens instruments. That is the right trade for testing pages —
and it means the path a NEW USER takes has never been exercised at all:
the real registry, an empty ``resources/``, no ``config/``, no presets,
no settings, no drivers installed, and the first-run wizard in the way.

Three fresh-install failures were reported from that path (no device could
be added, Telegram reported itself unconfigured, a 1→10 sweep planned two
points). This file walks it end to end.

Run it exactly as a user starts the app:

    python tests/fresh_install_smoke.py

It builds a throwaway core directory, copies in only what `git clone`
delivers, and drives the real widgets under whatever display is available.
"""

import os
import shutil
import sys
import tempfile
import time
import traceback

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import tkinter as tk                                    # noqa: E402
import tkinter.messagebox                               # noqa: E402

# dialogs must never block a smoke run: record them and answer the way a
# person would have to, or the window sits behind a modal nobody can see
BOXES: list = []
for _name in ("showinfo", "showwarning", "showerror"):
    setattr(tkinter.messagebox, _name,
            lambda t, m="", *a, _n=_name, **k: BOXES.append((_n, t, m)))
tkinter.messagebox.askyesno = lambda *a, **k: False
tkinter.messagebox.askyesnocancel = lambda *a, **k: False   # "start here"

for _name in [m for m in list(sys.modules)
              if m == "unisweep" or m.startswith("unisweep.")]:
    del sys.modules[_name]

import unisweep.gui.app as appmod                       # noqa: E402
from unisweep.core.migrate import migrate_presets       # noqa: E402


def fresh_core() -> str:
    """A core directory holding only what a clone delivers.

    ``config/`` and ``resources/`` are in .gitignore, so a fresh checkout
    has neither; ``main.py`` creates them empty on the first run. Anything
    that only works because a previous run left a file behind fails here,
    which is the point.
    """
    core = tempfile.mkdtemp(prefix="unisweep_fresh_")
    for name in ("unisweep", "devices", "docs", "server"):
        src = os.path.join(REPO, name)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(core, name),
                            ignore=shutil.ignore_patterns("__pycache__"))
    for name in ("main.py", "requirements.txt", "README.md"):
        src = os.path.join(REPO, name)
        if os.path.exists(src):
            shutil.copy(src, core)
    # exactly what main.py does before building the App
    os.makedirs(os.path.join(core, "resources"), exist_ok=True)
    os.makedirs(os.path.join(core, "config"), exist_ok=True)
    assert not os.listdir(os.path.join(core, "resources"))
    assert not os.listdir(os.path.join(core, "config"))
    return core


class Rig:
    """The app on a fresh core directory, with the REAL registry."""

    def __init__(self):
        self.core = fresh_core()
        migrate_presets(self.core)                  # main.py calls this
        self.errors: list = []
        self.app = appmod.App(self.core)
        self.app.root.report_callback_exception = self._tk_error
        self.pump(0.8)

    def _tk_error(self, kind, exc, tb):
        self.errors.append((kind.__name__, str(exc),
                            "".join(traceback.format_tb(tb))[-500:]))

    def pump(self, seconds=0.3):
        end = time.time() + seconds
        while time.time() < end:
            self.app.root.update()
            time.sleep(0.01)

    def close(self):
        try:
            self.app._on_close()
        except Exception:                           # noqa: BLE001
            pass


def check(name, condition, detail=""):
    print(("PASS " if condition else "FAIL ") + name
          + (f"\n      {detail}" if detail and not condition else ""))
    return bool(condition)


# ---------------------------------------------------------------------------
def wizard_check(rig: Rig) -> bool:
    """The first thing a new user meets."""
    ok = True
    wizard = rig.app._wizard
    ok &= check("the first run opens the setup wizard", wizard is not None)
    if wizard is None:
        return ok
    wizard._show(1)
    rig.pump(0.3)
    ok &= check("the wizard offers drivers to assign",
                len(wizard._driver_labels()) > 10,
                f"{len(wizard._driver_labels())} labels")
    wizard.new_addr.set("GPIB0::4::INSTR")
    wizard._add_address()
    rig.pump(0.3)
    ok &= check("an address added in the wizard gets a row",
                "GPIB0::4::INSTR" in wizard.choices,
                f"rows: {sorted(wizard.choices)}")
    labels = wizard._driver_labels()
    pick = next((l for l in labels if l.startswith("SR830")), labels[0])
    wizard.choices["GPIB0::4::INSTR"].set(pick)
    wizard._update_plan()
    rig.pump(0.2)
    ok &= check("picking a driver builds an install plan",
                wizard._selection().get("GPIB0::4::INSTR") == "SR830",
                str(wizard._selection()))
    wizard._close()
    rig.pump(0.4)
    ok &= check("closing the wizard leaves a usable window",
                rig.app.root.winfo_exists() and rig.app._wizard is None)
    return ok


def devices_page_check(rig: Rig) -> bool:
    """Adding an instrument by hand, with the real registry."""
    ok = True
    rig.app.show_page("Devices")
    rig.pump(0.5)
    page = rig.app.pages["Devices"]
    before = list(rig.app.registry.addresses)

    page.new_addr.set("GPIB0::7::INSTR")
    page._add()
    rig.pump(0.5)
    ok &= check("Add puts the address in the registry",
                "GPIB0::7::INSTR" in rig.app.registry.addresses,
                f"{before} -> {rig.app.registry.addresses}")
    ok &= check("Add builds a row for it",
                "GPIB0::7::INSTR" in page.rows,
                f"rows: {sorted(page.rows)}")
    row = page.rows.get("GPIB0::7::INSTR")
    if row is None:
        return ok
    options = list(row.combo.cget("values"))
    ok &= check("the row offers the driver library",
                len(options) > 10, f"{len(options)} options")
    pick = next((o for o in options if o.startswith("SR830")), "")
    ok &= check("SR830 is among them", bool(pick), str(options[:4]))
    if pick:
        row.combo.set(pick)
        row._assigned()
        rig.pump(0.5)
        ok &= check("picking a type is remembered",
                    rig.app.registry.types.get("GPIB0::7::INSTR") == "SR830",
                    str(rig.app.registry.types))
        ok &= check("the choice survives a restart of the app",
                    "SR830" in open(rig.app.registry.config_path,
                                    encoding="utf-8").read(),
                    rig.app.registry.config_path)
    return ok


def one_d_sweep_check(rig: Rig) -> bool:
    """1 → 10 with a step of 1 is ten points. It planned two."""
    ok = True
    rig.app.show_page("Sweep")
    rig.pump(0.4)
    page = rig.app.pages["Sweep"]
    card = page.axis_cards[0]

    card.device.set("Time")
    card.parameter.set("Time")
    card.start.set(1)
    card.stop.set(10)
    card.mode.set("step, units/pt")
    card.rate.set(1)
    card.delay.set(0.02)
    rig.pump(0.2)
    page.refresh_reads()
    rig.pump(0.2)
    items = page.reads_list.get(0, "end")
    wanted = [i for i, v in enumerate(items) if "Elapsed" in v]
    ok &= check("the built-in Time device offers something to read",
                bool(wanted), str(items))
    if not wanted:
        return ok
    page.reads_list.selection_set(wanted[0])
    rig.pump(0.1)

    program = page.build_program()
    ok &= check("the typed axis becomes a program", program is not None,
                str(BOXES[-1] if BOXES else ""))
    if program is None:
        return ok
    axis = program.axes[0]
    ok &= check("start and stop are what was typed",
                (axis.start, axis.stop) == (1.0, 10.0),
                f"{axis.start} -> {axis.stop}")
    ok &= check("a step of 1 over 1→10 plans ten points",
                axis.planned_count() == 10,
                f"planned {axis.planned_count()}, step "
                f"{axis.step_size()}, mode {axis.count_mode}")
    planned, _duration = page._estimate(program)
    ok &= check("the estimate agrees", planned == 10, f"estimate {planned}")

    page._start()
    rig.pump(0.4)
    for _ in range(600):
        rig.pump(0.05)
        if rig.app.engine is None or not rig.app.engine.is_alive():
            break
    rig.pump(0.5)
    tap = rig.app.event_tap
    done = (tap.summary() or {}).get("points") if hasattr(tap, "summary") \
        else None
    files = sorted(
        os.path.join(r, n)
        for r, _d, ns in os.walk(rig.core) for n in ns
        if n.endswith(".csv") and "data_files" in r)
    ok &= check("the sweep wrote a data file", bool(files), str(files))
    if files:
        rows = [l for l in open(files[-1], encoding="utf-8").read()
                .splitlines() if l.strip()]
        ok &= check("ten measured points reached the file",
                    len(rows) - 1 == 10,
                    f"{len(rows) - 1} rows in {os.path.basename(files[-1])}")
    return ok


def telegram_check(rig: Rig) -> bool:
    """What the notifications page says on a setup nobody has paired.

    The application starts reporting inside ``App.__init__``, before
    anyone presses anything. The identity it reports under used to be
    minted only when someone pressed "Generate code", so a fresh install
    always read *problem: service address or rig identity missing* — a
    fault message for a setup where nothing is wrong, only unpaired.
    """
    ok = True
    settings = rig.app.settings
    ok &= check("a fresh install mints its own rig identity",
                bool(settings.tg_rig_id and settings.tg_rig_token),
                f"id={settings.tg_rig_id!r} token set="
                f"{bool(settings.tg_rig_token)}")
    ok &= check("the identity is written down, not re-minted each launch",
                "tg_rig_id" in open(
                    os.path.join(rig.core, "config", "settings.json"),
                    encoding="utf-8").read())
    summary = rig.app.telegram_summary()
    print(f"      notifications page says: {summary!r}")
    ok &= check("it does not report itself as misconfigured",
                "identity missing" not in summary
                and "service address" not in summary, summary)
    rig.app.show_page("Settings")
    rig.pump(0.5)
    return ok


def preset_clobber_check(rig: Rig) -> bool:
    """Re-picking the dimension must not throw away what was typed.

    A preset REPLACES every field on the page, and the dimension
    combobox loaded one on every selection event — including when the
    dimension picked was the one already showing. Type a sweep, brush the
    combobox, and the fields silently revert to whatever was saved last:
    the sweep then runs the old numbers with nothing on screen to say so.
    """
    ok = True
    rig.app.show_page("Sweep")
    rig.pump(0.3)
    page = rig.app.pages["Sweep"]
    card = page.axis_cards[0]

    card.start.set(0)
    card.stop.set(1)
    card.mode.set("step, units/pt")
    card.rate.set(1)
    rig.pump(0.1)
    page._save_preset()                       # a saved 0 → 1 preset
    rig.pump(0.3)

    card.start.set(1)
    card.stop.set(10)
    rig.pump(0.1)
    page.dims.set("1D")
    page._set_dims()                          # the same dimension again
    rig.pump(0.3)
    ok &= check("re-picking the same dimension keeps what was typed",
                (card.start.value(), card.stop.value()) == (1.0, 10.0),
                f"{card.start.value()} -> {card.stop.value()} "
                f"(the saved preset was 0 -> 1)")

    page.dims.set("2D")
    page._set_dims()
    rig.pump(0.3)
    page.dims.set("1D")
    page._set_dims()
    rig.pump(0.3)
    card = page.axis_cards[0]
    ok &= check("actually changing dimension still loads its preset",
                (card.start.value(), card.stop.value()) == (0.0, 1.0),
                f"{card.start.value()} -> {card.stop.value()}")
    return ok


def main() -> int:
    rig = Rig()
    results = []
    try:
        results.append(("wizard", wizard_check(rig)))
        results.append(("devices page", devices_page_check(rig)))
        results.append(("1-D sweep", one_d_sweep_check(rig)))
        results.append(("telegram", telegram_check(rig)))
        results.append(("preset clobber", preset_clobber_check(rig)))
    finally:
        rig.close()
    if rig.errors:
        print("\nTk callback errors:")
        for kind, msg, tb in rig.errors:
            print(f"  {kind}: {msg}\n{tb}")
    if BOXES:
        print("\nDialogs shown:")
        for box in BOXES:
            print("  ", box)
    bad = [name for name, ok in results if not ok]
    print("\nFRESH INSTALL: "
          + ("OK" if not bad and not rig.errors
             else f"FAILED — {', '.join(bad) or 'Tk errors'}"))
    return 1 if bad or rig.errors else 0


if __name__ == "__main__":
    sys.exit(main())
