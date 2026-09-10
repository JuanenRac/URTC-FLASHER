# =============================================================================
# URTC Flasher - tests/test_flasher_protocol_clock.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""FLASH-01 (P1):
flasher_protocol.py's own deadline/duration math used to read time.time()
(the civil/wall clock), which an NTP sync or a manual clock change can move
at any moment with no relation to real elapsed time - shortening a real
flashing timeout (aborting mid-page as "timed out" while the board was
still working) or lengthening one (waiting on a hung board far longer than
intended). Fixed to time.monotonic() throughout.

Patches time.time() to raise if ever called, rather than simulating a
specific clock jump and checking the resulting duration - a direct proof
this code path genuinely never reads the civil clock at all, not just that
one particular jump happened not to matter in this run.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

import flasher_protocol
from flasher_protocol import FlashError, URTCFlasher
from flasher_transports import MockCAN


def _time_time_forbidden(monkeypatch):
    def explode(*args, **kwargs):
        raise AssertionError("flasher_protocol must never call time.time() for a deadline/duration - use time.monotonic()")
    monkeypatch.setattr(flasher_protocol.time, "time", explode)


def test_wait_for_timeout_never_reads_the_civil_clock(monkeypatch):
    _time_time_forbidden(monkeypatch)
    can = MockCAN()  # empty response queue - every read_frame() returns None
    flasher = URTCFlasher(can, log=lambda msg: None)

    with pytest.raises(FlashError, match="Timed out"):
        flasher._wait_for(0x999, timeout=0.15)


def test_wait_for_success_path_never_reads_the_civil_clock(monkeypatch):
    _time_time_forbidden(monkeypatch)
    can = MockCAN()
    can._response_queue.append((0x321, b"\x01\x02"))
    flasher = URTCFlasher(can, log=lambda msg: None)

    data = flasher._wait_for(0x321, timeout=1.0)
    assert data == b"\x01\x02"


def test_query_version_never_reads_the_civil_clock(monkeypatch):
    # MockCAN answers CAN_ID_QUERY_VERSION with a plausible simulated
    # bootloader identification by design (see its own class docstring)
    # - this exercises the real success path, including the post-0x7F9
    # grace-window wait for the bootloader's own separate 0x7FA frame,
    # which has its own time.monotonic() deadline.
    _time_time_forbidden(monkeypatch)
    can = MockCAN()
    flasher = URTCFlasher(can, log=lambda msg: None)

    result = flasher.query_version(timeout=0.5)
    assert result is not None
    assert result["responder"] == "bootloader"


def test_query_slave_version_never_reads_the_civil_clock(monkeypatch):
    _time_time_forbidden(monkeypatch)
    can = MockCAN()  # no slave chip present - must return None, not hang or crash
    flasher = URTCFlasher(can, log=lambda msg: None)

    assert flasher.query_slave_version(timeout=0.15) is None
