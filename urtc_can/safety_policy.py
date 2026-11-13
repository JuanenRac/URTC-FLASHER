"""The decisions of the clear-error command and of the communication watchdog, written down apart from the firmware.

Three questions the board answers with a few integers, kept pure so the firmware (``fw_safety_policy.c``) and every tool agree:

* may a latched critical error be lifted now (``clear_error_decision``);
* how long may the host stay silent while a stepper move runs (``stepper_silence_limit_ms`` and ``stepper_must_stop``);
* does the electromagnet let go when the host falls silent (``magnet_must_release``).

The limits come from ``spec/can_protocol.json`` (``CLEAR_ERROR_MAX_TEMP_C``, ``STEPPER_SILENCE_*``, ``MAGNET_SILENCE_MS``). Standard library only.
Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
"""
from __future__ import annotations

from . import protocol

TEMPERATURE_UNKNOWN = 0xFFFF
DEFAULT_SPEED_SPS = 500  # what a move without a speed does: one step every two milliseconds
UINT32_MAX = 0xFFFFFFFF


def clear_error_decision(feature_on: bool, error_latched: bool, reason: int, temperature_c: int, actuators_off: bool) -> int:
    """Outcome code (``CLEAR_ERROR_*``) of a clear-error command with the magic payload.

    The order of the checks is part of the contract: the switch, then whether there is an error, then whether this kind can be lifted at all, then the
    temperature (0xFFFF = unknown, which is refused) and last the actuators.
    """
    if not feature_on:
        return protocol.CLEAR_ERROR_REFUSED_SWITCH_OFF
    if not error_latched:
        return protocol.CLEAR_ERROR_REFUSED_NO_ERROR
    if reason == protocol.ERROR_REASON_TOOL_ID:
        return protocol.CLEAR_ERROR_REFUSED_NOT_CLEARABLE
    if temperature_c == TEMPERATURE_UNKNOWN or temperature_c >= protocol.CLEAR_ERROR_MAX_TEMP_C:
        return protocol.CLEAR_ERROR_REFUSED_HOT
    if not actuators_off:
        return protocol.CLEAR_ERROR_REFUSED_ACTUATOR_ON
    return protocol.CLEAR_ERROR_CLEARED


def stepper_silence_limit_ms(steps: int, speed_sps: int) -> int:
    """How long the host may stay silent while a move of ``steps`` runs at ``speed_sps`` steps/s (0 = the default speed)."""
    speed = speed_sps if speed_sps > 0 else DEFAULT_SPEED_SPS
    expected_ms = (steps * 1000) // speed
    limit = (expected_ms * protocol.STEPPER_SILENCE_PERCENT) // 100
    return min(max(limit, protocol.STEPPER_SILENCE_MIN_MS), UINT32_MAX)


def stepper_must_stop(feature_on: bool, moving: bool, silence_ms: int, limit_ms: int) -> bool:
    """Whether the move is cut: the switch on, a move running and a silence longer than the limit."""
    return bool(feature_on and moving and silence_ms > limit_ms)


def magnet_must_release(watchdog_on: bool, release_on: bool, energised: bool, silence_ms: int) -> bool:
    """Whether the electromagnet lets go: both switches on, the coil energised and a silence longer than ``MAGNET_SILENCE_MS``."""
    return bool(watchdog_on and release_on and energised and silence_ms > protocol.MAGNET_SILENCE_MS)
