# =============================================================================
# URTC Flasher - tests/test_estop_follow_copy.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The emergency stop following of a tool head, as the flasher sees it.

The flasher does not switch the optional functions (that is the tester and the web studio, where the check box starts off): it only carries the copy of
URTC-COMMON that its virtual board needs. These tests keep that copy complete and keep the flasher from writing the switch on its own. Nothing here has
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
    assert protocol.ESTOP_CAN_ID == 1


def test_the_virtual_head_ignores_the_stop_frame_until_the_switch_is_on():
    off = VirtualBoard()
    assert off.estop is None and not off.system_error
    on = VirtualBoard(features=ESTOP_BIT)
    assert on.estop is not None and on.system_error
    assert on.error_reason == protocol.ERROR_REASON_ESTOP


def test_the_flasher_never_writes_the_optional_functions_on_its_own():
    for path in ROOT.glob("*.py"):
        assert not re.search(r"SET_FEATURES|CAN_ID_SET_FEATURES|0x1AE\b", path.read_text(encoding="utf-8")), path.name
