# =============================================================================
# URTC-COMMON - src/urtc_common/quick_state.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The answer to the active-tool query (0x111), with the legacy lengths of older firmware."""
from __future__ import annotations

from . import protocol

THERMAL_FAULT_NAMES = {entry: name for entry, name in protocol.ENUM_NAMES["thermal_fault"].items() if entry}


def decode(data: bytes) -> dict | None:
    """Fields of a 0x111 payload; None below four bytes. Bytes 4 and 5 are None when the firmware does not send them (not zero)."""
    fields = protocol.decode_active_tool_resp(data)
    if fields is None:
        return None
    thermal = fields["thermal_fault"]
    reset = fields["reset_cause"]
    return {
        "tool_id": fields["tool_id"],
        "system_error": bool(fields["system_error"]),
        "can_error": bool(fields["can_error"]),
        "booting": bool(fields["booting"]),
        "thermal_fault": thermal,
        "thermal_fault_name": (THERMAL_FAULT_NAMES.get(thermal, f"CODE_{thermal}") if thermal else None),
        "reset_cause": reset,
        "reset_causes": [name for bit, name in protocol.ENUM_NAMES["reset_cause"].items() if reset is not None and reset & bit],
        "watchdog_reset": bool(reset is not None and reset & protocol.RESET_CAUSE_IWDG),
    }
