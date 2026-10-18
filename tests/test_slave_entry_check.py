# =============================================================================
# URTC Flasher - tests/test_slave_entry_check.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""A slave whose application is still running never enters its bootloader (the application only resets and the bootloader jumps straight back), so START_UPDATE is ignored and the
update used to end in a generic timeout. The tool now says so at once."""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from flasher_config import CAN_ID_SLAVE_START_UPDATE, CAN_ID_SLAVE_VERSION_RESP_1, CAN_ID_SLAVE_VERSION_RESP_2, SLAVE_HARDWARE_ID
from flasher_protocol import FlashError, URTCFlasher


class _SlaveRunningItsApplication:
    def __init__(self):
        self.sent = []
        self.queue = []

    def send_frame(self, can_id, data):
        self.sent.append(can_id)
        if can_id == CAN_ID_SLAVE_VERSION_RESP_1:
            self.queue.append((CAN_ID_SLAVE_VERSION_RESP_1, bytes([0x00]) + struct.pack(">IH", SLAVE_HARDWARE_ID, 0) + bytes([3])))
            self.queue.append((CAN_ID_SLAVE_VERSION_RESP_2, bytes([1, 1])))

    def read_frame(self, timeout=0.05):
        return self.queue.pop(0) if self.queue else None


def test_a_slave_that_is_still_running_its_application_is_reported_before_the_update_starts(tmp_path):
    firmware = tmp_path / "slave.bin"
    firmware.write_bytes(bytes(range(1, 200)) * 5)
    bus = _SlaveRunningItsApplication()
    with pytest.raises(FlashError, match="bootloader"):
        URTCFlasher(bus, log=lambda m: None).flash_slave(str(firmware))
    assert CAN_ID_SLAVE_START_UPDATE not in bus.sent, "START_UPDATE was not sent to a slave that is not listening"
