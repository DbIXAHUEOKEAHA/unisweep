"""Taking things off the rig: an address, and a driver the repo has dropped.

Both are about *removal*, which the code only ever did by addition before:

* ``DeviceRegistry`` could unassign an address (clear which driver answers
  on it) but not remove it, so a retired instrument left a permanent row;
* ``DriverCatalog.refresh_remote`` merged the GitHub listing with
  ``dict.update`` and ``set |=``, which can only grow. A driver deleted
  upstream therefore stayed in ``config/repo_index.json`` for good and went
  on being offered on the Devices page long after it had ceased to exist.
"""

import io
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from unisweep.core.catalog import BUILTIN_CATALOG, DriverCatalog
from unisweep.core.devices import DeviceRegistry


# ---------------------------------------------------------------------------
# removing an address
# ---------------------------------------------------------------------------
def registry_with(addresses):
    core = tempfile.mkdtemp()
    os.makedirs(os.path.join(core, "config"), exist_ok=True)
    reg = DeviceRegistry(core)
    for address, driver in addresses.items():
        reg.assign(address, driver)
    return core, reg


def test_an_address_can_be_taken_off_the_rig():
    core, reg = registry_with({"GPIB0::5::INSTR": "keithley_series_2600b"})
    assert "GPIB0::5::INSTR" in reg.addresses

    assert reg.remove_address("GPIB0::5::INSTR") is True
    assert "GPIB0::5::INSTR" not in reg.addresses
    assert "GPIB0::5::INSTR" not in reg.types

    # and it stays gone: the saved dictionary no longer names it
    saved = json.load(io.open(os.path.join(core, "config",
                                           "address_dictionary.txt"),
                              encoding="utf-8"))
    assert "GPIB0::5::INSTR" not in saved


def test_removing_differs_from_unassigning():
    """Unassign keeps the row so another driver can be picked for it.
    Remove is for an instrument that is gone."""
    _, reg = registry_with({"COM3": "asc500"})
    reg.unassign("COM3")
    assert "COM3" in reg.addresses and "COM3" not in reg.types
    reg.remove_address("COM3")
    assert "COM3" not in reg.addresses


def test_the_virtual_clock_cannot_be_removed():
    """Time is the axis every sweep can use when nothing else is ready."""
    _, reg = registry_with({})
    assert "Time" in reg.addresses
    assert reg.remove_address("Time") is False
    assert "Time" in reg.addresses


def test_removing_something_absent_says_so():
    _, reg = registry_with({})
    assert reg.remove_address("GPIB0::9::INSTR") is False
    assert reg.remove_address("") is False


# ---------------------------------------------------------------------------
# the catalog forgetting what the repository dropped
# ---------------------------------------------------------------------------
def catalog_with_repo(drivers, packages=(), user_drivers=(), local=()):
    core = tempfile.mkdtemp()
    os.makedirs(os.path.join(core, "config"), exist_ok=True)
    with io.open(os.path.join(core, "config", "repo_index.json"), "w",
                 encoding="utf-8") as fh:
        json.dump({"drivers": drivers, "packages": list(packages)}, fh)
    if user_drivers:
        with io.open(os.path.join(core, "config", "driver_catalog.json"), "w",
                     encoding="utf-8") as fh:
            json.dump({"drivers": [{"name": n, "instrument": "mine"}
                                   for n in user_drivers]}, fh)
    if local:
        os.makedirs(os.path.join(core, "resources"), exist_ok=True)
        for name in local:
            io.open(os.path.join(core, "resources", f"{name}.py"),
                    "w", encoding="utf-8").write("# local\n")
    return core, DriverCatalog(core)


def refresh_returning(catalog, drivers, packages=()):
    """Drive refresh_remote with a stubbed listing, no network."""
    catalog._api_listing = lambda timeout: (drivers, set(packages))
    return catalog.refresh_remote(timeout=0.1, allow_zip=False)


def test_a_driver_dropped_upstream_leaves_the_catalog():
    _, cat = catalog_with_repo({"oldscope": "u1", "newscope": "u2"})
    assert "oldscope" in cat.names()

    added, msg, ok = refresh_returning(cat, {"newscope": "u2"})
    assert ok
    assert "oldscope" not in cat.names(), "a retired driver is still offered"
    assert "newscope" in cat.names()
    assert "no longer in the repository" in msg and "oldscope" in msg


def test_the_index_on_disk_forgets_it_too():
    """Otherwise it comes back on the next start."""
    core, cat = catalog_with_repo({"oldscope": "u1", "newscope": "u2"})
    refresh_returning(cat, {"newscope": "u2"})
    index = json.load(io.open(os.path.join(core, "config",
                                           "repo_index.json"),
                              encoding="utf-8"))
    assert "oldscope" not in index["drivers"]
    assert "oldscope" not in DriverCatalog(core).names()


def test_a_builtin_driver_survives_a_repo_refresh():
    name = sorted(BUILTIN_CATALOG)[0]
    _, cat = catalog_with_repo({name: "u1", "oldscope": "u2"})
    refresh_returning(cat, {})   # nothing in the repo at all...
    # ...but an empty listing is refused outright, so nothing was pruned
    assert name in cat.names() and "oldscope" in cat.names()

    refresh_returning(cat, {"something_else": "u3"})
    assert name in cat.names(), "a built-in entry must not be prunable"


def test_a_locally_installed_driver_survives():
    """A file the user keeps in resources/ is theirs, whatever upstream did."""
    _, cat = catalog_with_repo({"mine": "u1"}, local=("mine",))
    refresh_returning(cat, {"other": "u2"})
    assert "mine" in cat.names()


def test_a_user_catalog_entry_survives():
    _, cat = catalog_with_repo({"listed": "u1"}, user_drivers=("listed",))
    refresh_returning(cat, {"other": "u2"})
    assert "listed" in cat.names()


def test_an_empty_listing_is_refused_rather_than_obeyed():
    """A broken response is far likelier than a repository with no drivers,
    and obeying it would delete the whole catalog."""
    _, cat = catalog_with_repo({"a": "u1", "b": "u2"})
    added, msg, ok = refresh_returning(cat, {})
    assert ok is False
    assert "keeping the cached catalog" in msg
    assert "a" in cat.names() and "b" in cat.names()


def test_packages_are_replaced_not_accumulated():
    _, cat = catalog_with_repo({"a": "u1"}, packages=("oldpkg",))
    assert cat.has_repo_package("oldpkg")
    refresh_returning(cat, {"a": "u1"}, packages=("newpkg",))
    assert cat.has_repo_package("newpkg")
    assert not cat.has_repo_package("oldpkg")


def test_a_new_driver_is_still_reported_as_added():
    _, cat = catalog_with_repo({"a": "u1"})
    added, msg, ok = refresh_returning(cat, {"a": "u1", "b": "u2"})
    assert added == ["b"] and ok
    assert "1 new: b" in msg
