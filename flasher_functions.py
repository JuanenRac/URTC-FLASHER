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

from urtc_can import estop_follow, protocol

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


# ---- the silence of the master of the emergency stop (ESTOP_FOLLOW) -------------------------------------------------------------------------------
# Written only with the eight-byte form of 0x1AE and only when the person ticks the confirmation of this write; read with the queries 3 and 4 of 0x1AF.
# The mask the head stores, the second byte of it included, is carried over from the head's own answer, so nothing else changes. A flash never gets here.
TIMEOUT_MIN_MS = estop_follow.TIMEOUT_MIN_MS
TIMEOUT_MAX_MS = estop_follow.TIMEOUT_MAX_MS


def timeout_valid(timeout_ms: Any) -> bool:
    """True for 0 (the default) and for a whole number of milliseconds inside the limits; text, a float or a bool is not guessed at."""
    return isinstance(timeout_ms, int) and not isinstance(timeout_ms, bool) and estop_follow.write_timeout_valid(timeout_ms)


def _ask(flasher: Any, query: int) -> dict[str, int] | None:
    """Ask 0x1AF with the byte ``query`` (3: the silence in force, 4: the silence stored) and decode the eight-byte answer; None when there is none."""
    can_id, data = protocol.encode_features_resp_request_estop_timeout_stored() if query == 4 else protocol.encode_features_resp_request_estop_timeout()
    flasher.can.send_frame(can_id, data)
    try:
        return estop_follow.decode_timeout_answer(flasher._wait_for(protocol.CAN_ID_FEATURES_RESP, timeout=2.0))
    except Exception:
        return None


def read_estop_timeout(flasher: Any, translate: Any) -> dict[str, int] | None:
    """The silence in force and the silence stored in the head, logged; None (nothing changed, it only reads) when the head does not answer in the new form."""
    stored = _ask(flasher, 4)
    running = _ask(flasher, 3) if stored is not None else None
    if stored is None or running is None:
        flasher.log(translate("LOG_OPT_TIMEOUT_UNSUPPORTED"))
        return None
    flasher.log(translate("LOG_OPT_TIMEOUT_READ", running=running["timeout_ms"], stored=stored["timeout_ms"]))
    return {"running": running["timeout_ms"], "stored": stored["timeout_ms"]}


def write_estop_timeout(flasher: Any, estop_follow_on: bool, timeout_ms: int, confirmed: bool, translate: Any) -> dict[str, int] | None:
    """Write the switch of the emergency stop following together with the silence of the master; return the answer of the head, or None when nothing was written.

    Nothing is written without ``confirmed``, with a value outside 0 and the limits, or when the head does not answer the query of its stored state (an older
    firmware has no eight-byte form: the five-byte write of ``write_optional_functions`` is the one to use then)."""
    if not confirmed:
        flasher.log(translate("LOG_OPT_TIMEOUT_NOT_CONFIRMED"))
        return None
    if not timeout_valid(timeout_ms):
        flasher.log(translate("LOG_OPT_TIMEOUT_INVALID", min=TIMEOUT_MIN_MS, max=TIMEOUT_MAX_MS))
        return None
    before = _ask(flasher, 4)
    if before is None:
        flasher.log(translate("LOG_OPT_TIMEOUT_UNSUPPORTED"))
        return None
    mask = merged_mask(before["stored"], estop_follow_on) & before["supported"] if before["supported"] else merged_mask(before["stored"], estop_follow_on)
    can_id, data = protocol.encode_set_features_request_estop_timeout(mask, before["stored_ext"], timeout_ms)
    flasher.can.send_frame(can_id, data)
    try:
        after = estop_follow.decode_timeout_answer(flasher._wait_for(protocol.CAN_ID_FEATURES_RESP, timeout=2.0))
    except Exception:
        after = None
    if after is None:
        flasher.log(translate("LOG_OPT_FUNCTIONS_NO_ANSWER"))
        return None
    flasher.log(translate("LOG_OPT_FUNCTIONS_WRITTEN", mask=f"0x{mask:02X}", stored=f"0x{after['stored']:02X}", running=f"0x{after['running']:02X}",
                          supported=f"0x{after['supported']:02X}"))
    if after["timeout_ms"] != timeout_ms:
        flasher.log(translate("LOG_OPT_TIMEOUT_MISMATCH", stored=after["timeout_ms"]))
    return after
