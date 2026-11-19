# =============================================================================
# URTC Flasher - flasher_functions.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The optional panel of firmware functions: the switch of the emergency stop following, written only on request.

A flash never touches the optional functions of a board. This panel exists only when ``optional_functions_panel`` is exactly ``true`` in
``urtc_config.json`` (it is off by default) and writes only when the person presses its button. The head is asked for its stored mask first and
only the bit of the emergency stop following is changed, so every other function keeps the value it had; a head that does not answer is left as
it is. The switch stored in the board acts after the next power-up. This is not a certified safety function and never replaces a hardware
emergency stop. This is the only module of the flasher that writes the identifier 0x1AE.
"""
from __future__ import annotations

from typing import Any

from urtc_can import protocol

FEATURES_MAGIC = b"FEAT"
ESTOP_FOLLOW_BIT = protocol.FEATURE_ESTOP_FOLLOW


def panel_enabled(config: dict[str, Any] | None) -> bool:
    """True only when the config file says exactly ``true``: anything else (missing, ``"true"``, 1) keeps the panel hidden."""
    return isinstance(config, dict) and config.get("optional_functions_panel") is True


def features_frame(mask: int) -> tuple[int, bytes]:
    """The identifier and the five data bytes of a write of the mask (``FEAT`` and the mask)."""
    if not 0 <= mask <= 0xFF:
        raise ValueError("the mask is one byte")
    return protocol.CAN_ID_SET_FEATURES, FEATURES_MAGIC + bytes([mask])


def decode_features(data: bytes) -> dict[str, int] | None:
    """The answer of the head: the stored mask, the mask in force and the mask it supports (None for any other length)."""
    if len(data) != 3:
        return None
    return {"stored": data[0], "running": data[1], "supported": data[2]}


def merged_mask(stored: int, estop_follow: bool) -> int:
    """The stored mask with only the bit of the emergency stop following set or cleared."""
    return (stored | ESTOP_FOLLOW_BIT) if estop_follow else (stored & ~ESTOP_FOLLOW_BIT & 0xFF)


def write_optional_functions(flasher: Any, estop_follow: bool, translate: Any) -> dict[str, int] | None:
    """Query the head, then write the merged mask; return the answer of the write, or None when the head did not answer (nothing is written then).

    ``flasher`` is a URTCFlasher (its ``can``, ``log`` and ``_wait_for``); ``translate`` is the text lookup of the flasher."""
    flasher.can.send_frame(protocol.CAN_ID_FEATURES_RESP, b"")
    try:
        before = decode_features(flasher._wait_for(protocol.CAN_ID_FEATURES_RESP, timeout=2.0))
    except Exception:
        before = None
    if before is None:
        flasher.log(translate("LOG_OPT_FUNCTIONS_NO_ANSWER"))
        return None
    mask = merged_mask(before["stored"], estop_follow) & before["supported"] if before["supported"] else merged_mask(before["stored"], estop_follow)
    can_id, data = features_frame(mask)
    flasher.can.send_frame(can_id, data)
    try:
        after = decode_features(flasher._wait_for(protocol.CAN_ID_FEATURES_RESP, timeout=2.0))
    except Exception:
        after = None
    if after is None:
        flasher.log(translate("LOG_OPT_FUNCTIONS_NO_ANSWER"))
        return None
    flasher.log(translate("LOG_OPT_FUNCTIONS_WRITTEN", mask=f"0x{mask:02X}", stored=f"0x{after['stored']:02X}", running=f"0x{after['running']:02X}",
                          supported=f"0x{after['supported']:02X}"))
    return after
