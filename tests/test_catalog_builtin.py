"""The driver list built into the code must match the repository exactly.

``BUILTIN_CATALOG`` ships inside ``catalog.py``. It is the one source of
driver names that a fresh install cannot refresh away — there is no cached
index yet and nothing local — so an entry for a driver that was renamed or
deleted on GitHub is offered for download on every new setup, forever.

That is how a deleted ``SR830`` sat beside the real ``sr830`` in the Devices
drop-down, and ``Keithley2400`` beside ``keithley2400``, and three Standa
stages that no longer exist at all. Nothing compared the list against the
folder it describes. These tests do.
"""

import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pytest

from unisweep.core.catalog import BUILTIN_CATALOG, DriverCatalog

DEVICES = os.path.join(ROOT, "devices")

needs_devices = pytest.mark.skipif(
    not os.path.isdir(DEVICES), reason="no devices/ folder in this checkout")


def repository_drivers() -> set:
    return {f[:-3] for f in os.listdir(DEVICES)
            if f.endswith(".py") and f != "__init__.py"}


def case_twins(names) -> list:
    seen, twins = {}, []
    for name in names:
        key = name.lower()
        if key in seen:
            twins.append((seen[key], name))
        seen[key] = name
    return twins


@needs_devices
def test_every_builtin_driver_exists_in_the_repository():
    """Exact case: Windows would open SR830.py for sr830, but the catalog
    keys are case-sensitive, so the two are offered as separate drivers."""
    present = repository_drivers()
    missing = sorted(n for n in BUILTIN_CATALOG if n not in present)
    assert not missing, (
        f"built into catalog.py but not in devices/: {missing}. Rename the "
        f"entry to the file's exact name, or delete it if the driver is gone "
        f"— a new install will otherwise offer it for download forever.")


def test_no_two_builtin_names_differ_only_by_case():
    assert not case_twins(BUILTIN_CATALOG)


def test_a_new_setup_offers_each_driver_once():
    """The case reported: a fresh install, nothing cached, then the first
    catalog refresh brings in the repository's listing. Each driver must
    appear once — not once from the code and again from GitHub."""
    if os.path.isdir(DEVICES):
        listing = {n: f"https://example.invalid/{n}.py"
                   for n in repository_drivers()}
    else:
        listing = {n: f"https://example.invalid/{n}.py"
                   for n in BUILTIN_CATALOG}
    core = tempfile.mkdtemp()
    os.makedirs(os.path.join(core, "config"), exist_ok=True)
    catalog = DriverCatalog(core)
    catalog._api_listing = lambda timeout: (listing, set())
    catalog.refresh_remote(timeout=0.1, allow_zip=False)

    twins = case_twins(catalog.names())
    assert not twins, f"offered twice under different case: {twins}"
