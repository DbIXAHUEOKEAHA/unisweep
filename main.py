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
