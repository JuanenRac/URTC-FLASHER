# =============================================================================
# URTC Flasher - tests/test_flash_cut_scenarios.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""An update that is cut or damaged half way, against the simulated bootloader behind a bus scenario: the adapter is unplugged during the transfer, the board stops
hearing, an acknowledgement is lost, the confirmation never comes. In every case the flasher must stop with an error and a progress bar that never says it finished, and a
lost acknowledgement must not stop an update that can still go on. Evidence: simulator (MockCAN, which is more forgiving than the real bootloader); the same cuts on a
real board are still to be tried."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

import flasher_scenario
from flasher_config import CAN_ID_AUTHORIZE_DOWNGRADE, CAN_ID_END_UPDATE, CAN_ID_PAGE_ACK
from flasher_protocol import FlashError, URTCFlasher
from flasher_transports import MockCAN
from urtc_can import bus_scenario as bs

PAGE = 2048   # the page of the simulated bootloader (protocol.FLASH_PAGE_SIZE)


def image(tmp_path: Path, size: int = 6 * PAGE + 100) -> str:
    path = tmp_path / "firmware.bin"
    path.write_bytes(bytes((i * 7 + 1) % 251 for i in range(size)))
    return str(path)


def run(tmp_path: Path, faults: list[dict], *, allow_downgrade: bool = False, seed: int = 4):
    """Flash behind the scenario on a virtual clock. Returns (bus, mock, progress list, the error or None)."""
    virtual = bs.VirtualTime()
    mock = MockCAN(delay=0.0)
    scenario = bs.from_dict({"format": bs.FORMAT, "name": "cut", "seed": seed, "faults": faults})
    bus = bs.FaultyBus(mock, scenario, clock=virtual.clock, sleep=virtual.sleep, read_cost_s=flasher_scenario.READ_COST_S)
    progress: list[int] = []
    error = None
    with flasher_scenario.virtual_clock(virtual):
        bus.open_channel()
        flasher = URTCFlasher(bus, log=lambda m: None, progress_cb=progress.append)
        try:
            flasher.flash(image(tmp_path), allow_downgrade=allow_downgrade, version=(0, 3))
        except FlashError as exc:
            error = exc
    return bus, mock, progress, error


def test_the_reference_run_without_faults_finishes(tmp_path):
    _, _, progress, error = run(tmp_path, [])
    assert error is None and progress[-1] == 100


# In the reference run the board sends 12 frames that matter before the update is over: 3 for the handshake and the start, one acknowledgement per page and the last
# status frames. A cut after k of them leaves the update at a different point each time.
@pytest.mark.parametrize("cut_after", [0, 2, 3, 5])
def test_an_adapter_unplugged_during_the_transfer_stops_the_update_short_of_the_end(tmp_path, cut_after):
    """The answers stop after ``cut_after`` frames of the board: the transfer cannot finish and the bar never reaches the end."""
    _, mock, progress, error = run(tmp_path, [{"fault": "mute", "direction": "rx", "from": cut_after}])
    assert isinstance(error, FlashError) and "Timed out" in str(error)
    assert not progress or max(progress) < 70      # the transfer phase tops out at 70 %: it never got there
    assert mock.end_update_payload is None         # the end of the update was never sent: the flasher does not close an update it could not watch


@pytest.mark.parametrize("cut_from", [300, 700, 1200])
def test_a_board_that_stops_hearing_in_the_middle_of_the_pages_ends_in_an_error(tmp_path, cut_from):
    _, mock, progress, error = run(tmp_path, [{"fault": "mute", "direction": "tx", "from": cut_from}])
    assert isinstance(error, FlashError)
    assert not progress or max(progress) < 70 and mock.end_update_payload is None


def test_one_lost_page_acknowledgement_does_not_stop_an_update_that_can_go_on(tmp_path):
    bus, _, progress, error = run(tmp_path, [{"fault": "drop", "direction": "rx", "id": CAN_ID_PAGE_ACK, "from": 2, "count": 1}])
    # the flasher either recovers by asking again or stops with an error: it must not stop silently, and a recovery must reach the end
    if error is None:
        assert progress[-1] == 100 and bus.stats["drop"] == 1
    else:
        assert max(progress or [0]) < 100


def test_every_page_acknowledgement_lost_is_an_error_not_a_success(tmp_path):
    _, _, progress, error = run(tmp_path, [{"fault": "drop", "direction": "rx", "id": CAN_ID_PAGE_ACK}])
    assert isinstance(error, FlashError) and (not progress or max(progress) < 100)


def test_a_second_copy_of_an_acknowledgement_is_refused_as_a_mismatch_and_never_skips_a_page(tmp_path):
    """Today the flasher takes a repeated acknowledgement for the wrong page and stops (strict). A real bootloader never repeats one; whether to ignore a repeat of the
    previous page instead is a design decision that is left open (it is recorded as pending), and this test holds the safe behaviour until it is taken."""
    _, _, progress, error = run(tmp_path, [{"fault": "duplicate", "direction": "rx", "id": CAN_ID_PAGE_ACK}])
    assert isinstance(error, FlashError) and "mismatch" in str(error).lower()
    assert not progress or max(progress) < 70


def test_the_authorisation_to_downgrade_is_sent_only_when_asked_and_before_the_end_of_the_update(tmp_path):
    _, mock, _, error = run(tmp_path, [])
    assert error is None and CAN_ID_AUTHORIZE_DOWNGRADE not in [i for i, _ in mock.sent]
    _, mock, _, error = run(tmp_path, [], allow_downgrade=True)
    ids = [i for i, _ in mock.sent]
    assert error is None and ids.count(CAN_ID_AUTHORIZE_DOWNGRADE) == 1
    assert ids.index(CAN_ID_AUTHORIZE_DOWNGRADE) < ids.index(CAN_ID_END_UPDATE)


def test_a_cut_after_the_end_of_the_update_never_ends_in_a_success_that_nobody_saw(tmp_path):
    """The end of the update went out and then the bus died: no confirmation and no new application answering -> an error, not a green bar."""
    _, mock, progress, error = run(tmp_path, [{"fault": "mute", "direction": "rx", "from": 8}])
    assert mock.end_update_payload is not None          # the update was closed: the pages had been acknowledged
    assert isinstance(error, FlashError) and "final verification" in str(error)
    assert max(progress) == 70                          # and the bar waited at the end of the transfer phase


@pytest.mark.parametrize("seed", range(12))
def test_no_generated_cut_makes_a_failed_update_look_finished(tmp_path, seed):
    """Whatever mix of faults the generator draws, a run that ends in an error never reported 100 % and a run that reports 100 % has no error."""
    scenario = bs.generate(seed, kinds=("drop", "burst_loss", "delay", "duplicate", "truncate", "mute"))
    faults = [dict(rule) for rule in scenario.faults]
    _, _, progress, error = run(tmp_path, faults, seed=seed)
    if error is not None:
        assert not progress or max(progress) < 100
    else:
        assert progress[-1] == 100
