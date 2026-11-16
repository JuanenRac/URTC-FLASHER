# =============================================================================
# URTC Flasher - tests/test_final_version_check.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""When the confirmation frame of an update is lost, an application that answers afterwards proves the update only if it is the version that was sent. Evidence: simulator."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

import flasher_scenario
from flasher_protocol import FlashError, URTCFlasher
from flasher_transports import MockCAN
from urtc_can import bus_scenario as bs

PAGE = 2048


def _run(tmp_path, answer):
    """Flash (0, 3) behind a bus whose answers stop after the end of the update; ``answer`` is what an application then says about its version."""
    virtual = bs.VirtualTime()
    mock = MockCAN(delay=0.0)
    scenario = bs.from_dict({"format": bs.FORMAT, "name": "cut", "seed": 4, "faults": [{"fault": "mute", "direction": "rx", "from": 8}]})
    bus = bs.FaultyBus(mock, scenario, clock=virtual.clock, sleep=virtual.sleep, read_cost_s=flasher_scenario.READ_COST_S)
    progress: list[int] = []
    path = tmp_path / "firmware.bin"
    path.write_bytes(bytes((i * 7 + 1) % 251 for i in range(6 * PAGE + 100)))
    error = None
    with flasher_scenario.virtual_clock(virtual):
        bus.open_channel()
        flasher = URTCFlasher(bus, log=lambda m: None, progress_cb=progress.append)
        real_query = flasher.query_version

        def query(*args, **kwargs):
            if mock.end_update_payload is None:
                return real_query(*args, **kwargs)
            return {"responder": "application", "version_major": answer[0], "version_minor": answer[1], "version_patch": None}

        flasher.query_version = query
        try:
            flasher.flash(str(path), version=(0, 3))
        except FlashError as exc:
            error = exc
    return progress, error


def test_an_application_with_the_version_that_was_sent_proves_the_update(tmp_path):
    progress, error = _run(tmp_path, (0, 3))
    assert error is None and progress[-1] == 100


@pytest.mark.parametrize("answer", [(0, 2), (1, 3), (0, 4)])
def test_another_application_answering_is_not_a_success(tmp_path, answer):
    progress, error = _run(tmp_path, answer)
    assert isinstance(error, FlashError) and "final verification" in str(error)
    assert not progress or max(progress) < 100
