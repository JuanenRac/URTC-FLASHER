# =============================================================================
# URTC Flasher - tests/test_bootloader_entry.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The bootloader listens for START_UPDATE only for about 600 ms after it starts, and when it starts depends on the installed application. The tool used to sleep 0.8 s and then send
START_UPDATE once; now it waits for the bootloader's own first heartbeat ("listening") and the update starts at once, and only without one does it fall back to the old wait."""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flasher_config import CAN_ID_ENTER_BOOTLOADER, CAN_ID_HEARTBEAT
from flasher_protocol import URTCFlasher


class _Bus:
    def __init__(self, frames_after_trigger):
        self.sent = []
        self.frames = list(frames_after_trigger)
        self.triggered_at = None

    def send_frame(self, can_id, data):
        self.sent.append(can_id)
        if can_id == CAN_ID_ENTER_BOOTLOADER:
            self.triggered_at = time.monotonic()

    def read_frame(self, timeout=0.05):
        if self.frames and time.monotonic() - self.triggered_at >= self.frames[0][0]:
            return self.frames.pop(0)[1]
        time.sleep(min(timeout, 0.005))
        return None


def test_the_update_starts_as_soon_as_the_bootloader_says_it_is_listening():
    bus = _Bus([(0.05, (0x7F6, bytes([0x01, 0xFF])))])
    started = time.monotonic()
    assert URTCFlasher(bus, log=lambda m: None).trigger_bootloader_entry() is True
    assert time.monotonic() - started < 0.6, "it did not wait the fixed 0.8 s"


def test_other_frames_are_not_taken_for_the_listening_heartbeat():
    bus = _Bus([(0.0, (0x123, b"\x01")), (0.01, (CAN_ID_HEARTBEAT, bytes([0x03, 0x10]))), (0.03, (CAN_ID_HEARTBEAT, bytes([0x01, 0xFF])))])
    assert URTCFlasher(bus, log=lambda m: None).trigger_bootloader_entry() is True


def test_without_a_heartbeat_it_waits_at_least_the_old_0_8_seconds_and_says_so():
    bus = _Bus([])
    started = time.monotonic()
    assert URTCFlasher(bus, log=lambda m: None).trigger_bootloader_entry(timeout=0.9) is False
    assert time.monotonic() - started >= 0.8
