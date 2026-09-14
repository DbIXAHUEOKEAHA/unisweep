# Unisweep update — copy into your main folder

Unzip `unisweep-update.zip` over `C:\Unisweep 2\unisweep`, keeping folder
structure. 34 files: 11 new, 23 replaced. Nothing is deleted, and none of
your own data is touched — `config/`, `resources/`, `journal/` and the
dated data folders are not in the archive.

**Close Unisweep first.** Python holds `.pyc` files open, and replacing a
module under a running process gives you a half-updated app.

After unzipping, from that folder:

    python -m pytest tests -q

Expect `416 passed, 1 skipped` (the skip wants `imageio`). If instead you
get import errors, something didn't land — check the file list below.

## What changes for you

- The colormap you pick reaches the saved `.png`. This is the one that
  looked unfixable: the live renderer rewrote every image in viridis as
  rows committed, so the setting was applied and then immediately undone.
- The "first walk only" checkbox works, on line plots and on maps, and
  survives into the saved image.
- A read that returns a whole trace (VNA) is detected and given a map of
  its own, one dimension out from the sweep. See `docs/VECTOR_READS.md`.
- Fresh-install fixes: devices can be added, Telegram identity is minted
  on first run, and a 1→10 step-1 sweep plans 10 points, not 2.
- Settings scrolls, so the lower half of the page is reachable at all.
- `mcp_stdio.py` — the launcher Claude Desktop needs. It finds its own
  folder, so it works whatever directory a client starts it from.
- `apply_program` now fully determines the sweep page, so what `dry_run`
  prices is what runs.

## Files

- replaced devices/Vna.py
- NEW      docs/VECTOR_READS.md
- NEW      mcp_stdio.py
- replaced server/unisweep_bot/config.py
- NEW      server/unisweep_bot/connector.py
- replaced server/unisweep_bot/db.py
- replaced server/unisweep_bot/ingest.py
- NEW      server/unisweep_bot/waiters.py
- NEW      tests/fresh_install_smoke.py
- replaced tests/gui_smoke.py
- replaced tests/test_agent.py
- NEW      tests/test_connector_server.py
- NEW      tests/test_connector_waiters.py
- replaced tests/test_engine.py
- replaced tests/test_installer.py
- replaced tests/test_mcp.py
- replaced tests/test_telegram_link.py
- NEW      tests/test_vector.py
- NEW      tests/test_vector_sweeps.py
- replaced unisweep/agent/session.py
- replaced unisweep/core/engine.py
- replaced unisweep/core/events.py
- replaced unisweep/core/installer.py
- replaced unisweep/core/labprofile.py
- replaced unisweep/core/livedata.py
- replaced unisweep/core/maps.py
- replaced unisweep/core/settings.py
- replaced unisweep/core/telegram_link.py
- NEW      unisweep/core/vector.py
- NEW      unisweep/core/vectormaps.py
- replaced unisweep/gui/app.py
- replaced unisweep/gui/plot_panel.py
- replaced unisweep/gui/settings_page.py
- replaced unisweep/gui/sweep_page.py
