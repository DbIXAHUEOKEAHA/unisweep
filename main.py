"""Unisweep entry point.

Run with:  python main.py

Expects (and creates if missing) next to this file:
  resources/   — instrument driver files (the legacy ones, unchanged)
  config/      — address_dictionary.txt, presets
Daily data goes to <core>/<YYMMDD>/data_files as before.
"""

import os
import sys

CORE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, CORE_DIR)

# ---- Spyder/IPython runfile guard -----------------------------------
# Spyder's module reloader re-executes edited unisweep modules while live
# objects keep references to the OLD ones. A sweep run in that mixed
# state can misbehave in ways a clean import never would (the overnight
# map's slid commit boundary was exactly this). Purge any previously
# loaded unisweep modules so every runfile starts from a coherent tree.
for _name in [m for m in list(sys.modules)
              if m == "unisweep" or m.startswith("unisweep.")]:
    del sys.modules[_name]

os.makedirs(os.path.join(CORE_DIR, "resources"), exist_ok=True)
os.makedirs(os.path.join(CORE_DIR, "config"), exist_ok=True)

from unisweep.core.migrate import migrate_presets      # noqa: E402
from unisweep.gui.app import App                       # noqa: E402


def main():
    migrated = migrate_presets(CORE_DIR)
    app = App(CORE_DIR)
    if migrated:
        app.status(f"Migrated {len(migrated)} legacy preset(s) — "
                   f"re-pick devices once and save")
    app.run()


if __name__ == "__main__":
    main()
