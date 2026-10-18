# =============================================================================
# URTC Flasher - tests/test_readback_odd_size.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The bootloader sends the last data frame of a readback with fewer than 8 bytes when the installed size is not a multiple of 8 (the official 0.3.3 image, 73476 bytes, leaves 4).
The flasher only accepted frames of exactly 8 bytes, so that last frame was dropped, the page never completed and the backup failed after the page timeout."""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from flasher_config import CAN_ID_READBACK, CAN_ID_READBACK_PAGE_ACK, FLASH_PAGE_SIZE
from flasher_protocol import URTCFlasher


class _Bootloader:
    """A simulated bootloader that answers the readback exactly as bootloader_protocol.c does: the size (DLC 4), then a page of frames of 8 bytes (the last one as short as it must be), and the next page after each acknowledgement."""

    def __init__(self, image):
        self.image = image
        self.queue = []
        self.sent = 0

    def _page(self):
        page = self.image[self.sent:self.sent + FLASH_PAGE_SIZE]
        for i in range(0, len(page), 8):
            self.queue.append((CAN_ID_READBACK, page[i:i + 8]))
        self.sent += len(page)

    def send_frame(self, can_id, data):
        if can_id == CAN_ID_READBACK:
            self.queue.append((CAN_ID_READBACK, struct.pack(">I", len(self.image))))
            self._page()
        elif can_id == CAN_ID_READBACK_PAGE_ACK and self.sent < len(self.image):
            self._page()

    def read_frame(self, timeout=0.05):
        return self.queue.pop(0) if self.queue else None


@pytest.mark.parametrize("size", [8, 9, 12, 2047, 2048, 2049, 4100, 73476])
def test_the_backup_is_complete_whatever_the_size_of_the_installed_image(tmp_path, size):
    image = bytes((i * 7 + 3) % 256 for i in range(size))
    flasher = URTCFlasher(_Bootloader(image), log=lambda message: None)
    output = tmp_path / "backup.bin"
    assert flasher.read_back_flash(str(output)) == size
    assert output.read_bytes() == image
