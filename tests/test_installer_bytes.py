"""A downloaded driver must land exactly as it is in the repository.

The installer used to decode the download to text and write that text in
text mode. On Windows, text mode turns every ``\\n`` into ``\\r\\n`` — so a
file already stored with CRLF, which most of the repository is, was written
as ``\\r\\r\\n`` and showed a blank line under every line.

Linux never saw it: there text mode translates nothing, which is why the
whole test suite stayed green while the installed file was wrong on the only
platform the GUI runs on. ``test_text_mode_is_what_doubled_the_newlines``
reproduces the mechanism on any platform so the reason cannot be forgotten;
the rest assert the contract — same bytes in, same bytes out.
"""

import ast
import io
import os
import queue
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from unisweep.core.catalog import DriverCatalog
from unisweep.core.devices import DeviceRegistry
from unisweep.core.installer import DriverInstaller

CRLF_DRIVER = (b"import pyvisa as visa\r\n"
               b"\r\n"
               b"class Thing:\r\n"
               b"    def __init__(self, adress='GPIB0::1::INSTR'):\r\n"
               b"        self.adress = adress\r\n")

LF_DRIVER = CRLF_DRIVER.replace(b"\r\n", b"\n")


def installer_for(core=None):
    core = core or tempfile.mkdtemp()
    os.makedirs(os.path.join(core, "config"), exist_ok=True)
    os.makedirs(os.path.join(core, "resources"), exist_ok=True)
    registry = DeviceRegistry(core)
    return DriverInstaller(registry, DriverCatalog(core), queue.Queue())


def zip_with(payload: bytes, member="unisweep-main/devices/thing.py"):
    path = os.path.join(tempfile.mkdtemp(), "snapshot.zip")
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(member, payload)
    return path, member


def fetch_from_zip(inst, payload, name="thing"):
    zip_path, member = zip_with(payload)
    inst.catalog.source_candidates = lambda n: [("zip", (zip_path, member))]
    ok = inst._fetch_driver(name)
    target = os.path.join(inst.resources, f"{name}.py")
    written = io.open(target, "rb").read() if os.path.exists(target) else None
    return ok, written


# ---------------------------------------------------------------------------
# the mechanism, reproduced anywhere
# ---------------------------------------------------------------------------
def test_text_mode_is_what_doubled_the_newlines():
    """What open(path, 'w') does on Windows to content that already has
    CRLF. Nothing in the installer may write a driver this way."""
    path = os.path.join(tempfile.mkdtemp(), "t.py")
    with io.open(path, "w", encoding="utf-8", newline="\r\n") as fh:
        fh.write(CRLF_DRIVER.decode())
    mangled = io.open(path, "rb").read()
    assert b"\r\r\n" in mangled
    assert mangled.count(b"\r\r\n") == CRLF_DRIVER.count(b"\r\n")


# ---------------------------------------------------------------------------
# the contract
# ---------------------------------------------------------------------------
def test_a_crlf_driver_is_installed_byte_for_byte():
    ok, written = fetch_from_zip(installer_for(), CRLF_DRIVER)
    assert ok
    assert written == CRLF_DRIVER
    assert b"\r\r" not in written


def test_an_lf_driver_is_installed_byte_for_byte():
    """Neither direction is normalised: as it is, means as it is."""
    ok, written = fetch_from_zip(installer_for(), LF_DRIVER)
    assert ok
    assert written == LF_DRIVER
    assert b"\r" not in written


def test_a_byte_order_mark_survives():
    payload = b"\xef\xbb\xbf" + LF_DRIVER
    ok, written = fetch_from_zip(installer_for(), payload)
    assert ok and written == payload


def test_unicode_in_a_docstring_survives():
    payload = '"""Ω per square, ±1 µV."""\nx = 1\n'.encode("utf-8")
    ok, written = fetch_from_zip(installer_for(), payload)
    assert ok and written == payload


# ---------------------------------------------------------------------------
# what must still be refused
# ---------------------------------------------------------------------------
def test_something_that_is_not_python_is_refused():
    ok, written = fetch_from_zip(installer_for(), b"<html>nope</html>\n")
    assert ok is False
    assert written is None, "a non-Python file must not be installed"


def test_undecodable_bytes_are_refused_not_silently_replaced():
    """errors='replace' used to turn these into U+FFFD and install a
    corrupted driver that happens to parse."""
    payload = b"x = 1  # caf\xe9 in latin-1\n"
    ok, written = fetch_from_zip(installer_for(), payload)
    assert ok is False
    assert written is None
    assert b"\xef\xbf\xbd" not in (written or b"")


def test_an_empty_member_is_skipped():
    inst = installer_for()
    ok, written = fetch_from_zip(inst, b"")
    assert ok is False


# ---------------------------------------------------------------------------
# and it is still Python when it arrives
# ---------------------------------------------------------------------------
def test_the_installed_file_imports_as_written():
    inst = installer_for()
    ok, written = fetch_from_zip(inst, CRLF_DRIVER)
    assert ok
    ast.parse(io.open(os.path.join(inst.resources, "thing.py"),
                      "rb").read().decode("utf-8"))
