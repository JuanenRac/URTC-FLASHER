# =============================================================================
# URTC Flasher - tests/test_ota_partial_page.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The real bootloader writes (and acknowledges) a flash page when its 2048-byte buffer is FULL; the last page of an image that is not a whole number of pages is written and
acknowledged only when END_UPDATE (0x7F4) arrives. The flasher used to wait for the acknowledgement of that last page BEFORE sending END_UPDATE, so every image whose size
was not a multiple of 2048 bytes (the official 0.3.3 image is 73476 bytes) waited for a frame the bootloader sends only after one the flasher sends only afterwards, and failed.
The simulated bootloader (MockCAN) used to acknowledge the partial page as soon as its bytes arrived, which hid the bug; it now behaves like the real one, and these tests use
sizes on both sides of a page boundary."""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from flasher_config import CAN_ID_END_UPDATE, CAN_ID_PAGE_ACK, FLASH_PAGE_SIZE
from flasher_protocol import URTCFlasher
from flasher_transports import MockCAN


def _firmware(tmp_path: Path, size: int) -> str:
    path = tmp_path / f"firmware_{size}.bin"
    path.write_bytes(bytes((i % 251) + 1 for i in range(size)))
    return str(path)


class _Recorder(MockCAN):
    """The simulated bootloader, remembering the order of what it was sent and what it answered."""

    def __init__(self):
        super().__init__()
        self.events = []

    def send_frame(self, can_id, data):
        before = len(self._response_queue)
        super().send_frame(can_id, data)
        if can_id == CAN_ID_END_UPDATE:
            self.events.append("end_update_sent")
        for can_id_out, payload in self._response_queue[before:]:
            if can_id_out == CAN_ID_PAGE_ACK:
                self.events.append(("ack", struct.unpack(">I", payload[:4])[0]))


@pytest.mark.parametrize("size", [1, FLASH_PAGE_SIZE - 1, FLASH_PAGE_SIZE, FLASH_PAGE_SIZE + 1, 2 * FLASH_PAGE_SIZE + 7, 73476, 73728])
def test_an_image_of_any_size_is_flashed_against_a_bootloader_that_acknowledges_the_last_partial_page_only_at_the_end(tmp_path, size):
    can = _Recorder()
    flasher = URTCFlasher(can, log=lambda message: None)
    assert flasher.flash(_firmware(tmp_path, size), version=(0, 3)) is True
    pages = (size + FLASH_PAGE_SIZE - 1) // FLASH_PAGE_SIZE
    acks = [event[1] for event in can.events if isinstance(event, tuple)]
    assert acks == list(range(pages)), "every page is acknowledged exactly once, in order"
    partial = size % FLASH_PAGE_SIZE != 0
    if partial:
        # the acknowledgement of the last page came after END_UPDATE, like the real bootloader's
        assert can.events.index(("ack", pages - 1)) > can.events.index("end_update_sent")
    else:
        assert can.events.index(("ack", pages - 1)) < can.events.index("end_update_sent")


def test_the_simulated_bootloader_does_not_acknowledge_a_partial_page_before_the_end():
    can = MockCAN()
    can.send_frame(0x7F1, struct.pack(">II", FLASH_PAGE_SIZE + 10, 0))
    queued_before = len(can._response_queue)
    for _ in range((FLASH_PAGE_SIZE + 10 + 7) // 8):
        can.send_frame(0x7F2, b"\x01" * 8)
    acked = [struct.unpack(">I", payload[:4])[0] for can_id, payload in can._response_queue[queued_before:] if can_id == CAN_ID_PAGE_ACK]
    assert acked == [0], "only the full page 0 is acknowledged while the data arrives"
