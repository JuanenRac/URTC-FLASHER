# =============================================================================
# URTC Flasher - tests/test_frame_gap_virtual_flash.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The pause between the data frames of a transfer, measured in a whole update against the simulated bootloader on a virtual clock.

The settings test (test_frame_gap.py) checks the limits of ``frame_gap_ms`` and replays the pacing statement; here the real ``flash()`` runs with 0, 1, 5 and 50 ms
(the ends and the middle of the accepted range) and the time at which each data frame is handed to the bus is recorded. The gap between two data frames of the same
page must be the configured one, the longer the gap the longer the update by exactly one gap per data frame, and the frames themselves must not change. Evidence:
simulator; the real spacing on the wire (what the adapter adds) and the time of a real update are still to be measured with an analyser on a board."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

import flasher_config as config
import flasher_protocol as protocol
import flasher_scenario
from flasher_protocol import URTCFlasher
from flasher_transports import MockCAN
from urtc_can import bus_scenario as bs

PAGES = 3
FRAMES_PER_PAGE = protocol.FLASH_PAGE_SIZE // 8


class Recording(MockCAN):
    """The simulated bootloader that notes when (on the virtual clock) each frame was handed to it."""

    def __init__(self, virtual):
        super().__init__(delay=0.0)
        self._virtual = virtual
        self.data_times: list[float] = []
        self.data_frames: list[bytes] = []

    def send_frame(self, can_id: int, data: bytes = b"") -> None:
        if can_id == config.CAN_ID_DATA:
            self.data_times.append(self._virtual.clock())
            self.data_frames.append(bytes(data))
        super().send_frame(can_id, data)


def flash_with_gap(tmp_path: Path, monkeypatch, gap_ms: float):
    """One whole update with the pause between data frames set to ``gap_ms``; returns (data frame times, data frames, total virtual seconds)."""
    monkeypatch.setattr(protocol, "FRAME_GAP_S", gap_ms / 1000.0)
    virtual = bs.VirtualTime()
    mock = Recording(virtual)
    bus = bs.FaultyBus(mock, bs.from_dict({"format": bs.FORMAT, "name": "gap", "seed": 3, "faults": []}), clock=virtual.clock, sleep=virtual.sleep,
                       read_cost_s=flasher_scenario.READ_COST_S)
    firmware = tmp_path / f"firmware_{gap_ms}.bin"
    firmware.write_bytes(bytes((i * 7 + 1) % 251 for i in range(PAGES * protocol.FLASH_PAGE_SIZE)))
    started = virtual.clock()
    with flasher_scenario.virtual_clock(virtual):
        bus.open_channel()
        URTCFlasher(bus, log=lambda m: None, progress_cb=lambda p: None).flash(str(firmware), allow_downgrade=False, version=(0, 3))
    return mock.data_times, mock.data_frames, virtual.clock() - started


@pytest.mark.parametrize("gap_ms", [0, 1, 5, 50])
def test_the_data_frames_of_a_page_are_spaced_by_the_configured_gap(tmp_path, monkeypatch, gap_ms):
    times, frames, _total = flash_with_gap(tmp_path, monkeypatch, gap_ms)
    assert len(frames) == PAGES * FRAMES_PER_PAGE
    gap = gap_ms / 1000.0
    for page in range(PAGES):
        page_times = times[page * FRAMES_PER_PAGE:(page + 1) * FRAMES_PER_PAGE]
        spacings = [b - a for a, b in zip(page_times, page_times[1:], strict=False)]
        assert min(spacings) >= gap - 1e-9, "two data frames closer than the configured gap"
        assert max(spacings) <= gap + 1e-9, "the pacing added more than the configured gap inside a page"


def test_a_longer_gap_makes_the_update_longer_by_one_gap_per_data_frame(tmp_path, monkeypatch):
    _t0, frames0, total0 = flash_with_gap(tmp_path, monkeypatch, 0)
    _t1, frames1, total1 = flash_with_gap(tmp_path, monkeypatch, 1)
    _t5, frames5, total5 = flash_with_gap(tmp_path, monkeypatch, 5)
    _t50, frames50, total50 = flash_with_gap(tmp_path, monkeypatch, 50)
    count = PAGES * FRAMES_PER_PAGE
    assert total0 < total1 < total5 < total50
    assert total1 - total0 == pytest.approx(count * 0.001, abs=1e-6)
    assert total5 - total0 == pytest.approx(count * 0.005, abs=1e-6)
    assert total50 - total0 == pytest.approx(count * 0.050, abs=1e-6)
    # the pacing changes only the time, never what is sent
    assert frames0 == frames1 == frames5 == frames50


def test_the_default_of_the_configuration_is_one_millisecond_and_reaches_the_flash(tmp_path, monkeypatch):
    assert config.FRAME_GAP_S == pytest.approx(0.001)
    times, _frames, _total = flash_with_gap(tmp_path, monkeypatch, config.FRAME_GAP_S * 1000.0)
    assert times[1] - times[0] == pytest.approx(0.001, abs=1e-9)
