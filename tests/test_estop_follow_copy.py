# =============================================================================
# URTC Flasher - tests/test_estop_follow_copy.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The emergency stop following of a tool head, as the flasher sees it.

The flasher switches the optional functions only from its optional panel (hidden unless the config file turns it on, check box off, a button that writes): it
otherwise carries the copy of URTC-COMMON that its virtual board needs. These tests keep that copy complete and keep a flash from writing the switch. Nothing here has
run against a real board.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from urtc_can import protocol  # noqa: E402
from urtc_can.virtual_board import VirtualBoard  # noqa: E402

ESTOP_BIT = 0x80


def test_the_copy_has_the_feature_and_the_two_reasons():
    assert protocol.FEATURE_ESTOP_FOLLOW == ESTOP_BIT
    assert protocol.ERROR_REASON_ESTOP == 9
    assert protocol.ERROR_REASON_ESTOP_SILENCE == 10
    # the silence of the master is configurable inside hard limits, and a head nobody configured keeps 100 ms
    from urtc_can import estop_follow
    assert protocol.ESTOP_ALIVE_TIMEOUT_MS == 100 and (protocol.ESTOP_ALIVE_TIMEOUT_MIN_MS, protocol.ESTOP_ALIVE_TIMEOUT_MAX_MS) == (20, 500)
    assert estop_follow.Node().alive_timeout_ms == 100 and estop_follow.Node(250).alive_timeout_ms == 250
    assert estop_follow.resolve_timeout(19) == (100, estop_follow.TIMEOUT_REJECTED) and estop_follow.resolve_timeout(501) == (100, estop_follow.TIMEOUT_REJECTED)
    assert estop_follow.effective_timeout(100, 300) == (100, estop_follow.TIMEOUT_MASTER_DIFFERS)
    assert protocol.ESTOP_CAN_ID == 1


def test_the_virtual_head_ignores_the_stop_frame_until_the_switch_is_on():
    off = VirtualBoard()
    assert off.estop is None and not off.system_error
    on = VirtualBoard(features=ESTOP_BIT)
    assert on.estop is not None and on.system_error
    assert on.error_reason == protocol.ERROR_REASON_ESTOP


def test_the_flasher_never_writes_the_optional_functions_on_its_own():
    """Only flasher_functions.py, behind the optional panel, may name the switch; a flash and every other module never write it."""
    for path in ROOT.glob("*.py"):
        found = re.search(r"SET_FEATURES|CAN_ID_SET_FEATURES|0x1AE", path.read_text(encoding="utf-8"))
        if path.name == "flasher_functions.py":
            assert found, "the panel module is where the switch is written"
        else:
            assert not found, path.name


def test_the_flash_paths_never_call_the_panel_module():
    flash = (ROOT / "flasher_protocol.py").read_text(encoding="utf-8")
    assert "flasher_functions" not in flash
    qt = (ROOT / "qt_flasher.py").read_text(encoding="utf-8")
    worker = qt[qt.index("def _flash_worker"):qt.index("def _write_update_report")]
    assert "write_optional_functions" not in worker and "flasher_functions" not in worker
