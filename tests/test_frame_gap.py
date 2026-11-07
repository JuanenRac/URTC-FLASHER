# =============================================================================
# URTC Flasher - tests/test_frame_gap.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The pause between the data frames of a transfer: the limits of "frame_gap_ms", what falls back to the default and that the transfer really uses the value."""
from __future__ import annotations

import math

import pytest

import flasher_config as config
import flasher_protocol as protocol


@pytest.mark.parametrize("value, expected", [(None, 1.0), (1, 1.0), (0, 0.0), (0.0, 0.0), (2.5, 2.5), (50, 50.0), (50.0, 50.0), (0.25, 0.25)])
def test_a_value_inside_the_limits_is_used_as_it_is(value, expected):
    assert config.parse_frame_gap_ms(value) == (expected, None)


@pytest.mark.parametrize("value", [-0.001, -1, 50.001, 51, 1e9, math.inf, -math.inf, math.nan, "2", "", [1], {"a": 1}, True, False])
def test_a_value_outside_the_limits_or_not_a_number_falls_back_to_the_default_with_a_reason(value):
    gap, problem = config.parse_frame_gap_ms(value)
    assert gap == config.FRAME_GAP_MS_DEFAULT == 1.0
    assert "frame_gap_ms" in problem


def test_the_default_is_one_millisecond_and_the_limits_are_ordered():
    assert config.FRAME_GAP_MS == 1.0 and config.FRAME_GAP_S == 0.001 and config.FRAME_GAP_PROBLEM is None
    assert config.FRAME_GAP_MS_MIN == 0.0 < config.FRAME_GAP_MS_DEFAULT < config.FRAME_GAP_MS_MAX == 50.0


def test_the_example_configuration_does_not_set_the_gap_so_the_default_applies():
    import json
    import os
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(here, "urtc_config.json.example"), encoding="utf-8") as handle:
        assert "frame_gap_ms" not in json.load(handle)


class _Recorder:
    def __init__(self):
        self.sleeps = []

    def sleep(self, seconds):
        self.sleeps.append(seconds)


def _count_data_frame_pauses(monkeypatch, gap_s):
    """Run the pacing statement the way flash() does for one 2048-byte page and return the pauses taken."""
    recorder = _Recorder()
    monkeypatch.setattr(protocol.time, "sleep", recorder.sleep)
    monkeypatch.setattr(protocol, "FRAME_GAP_S", gap_s)
    for _frame in range(0, protocol.FLASH_PAGE_SIZE, 8):
        if protocol.FRAME_GAP_S > 0:
            protocol.time.sleep(protocol.FRAME_GAP_S)
    return recorder.sleeps


def test_the_protocol_module_reads_the_configured_gap_from_the_config_module():
    assert protocol.FRAME_GAP_S == config.FRAME_GAP_S


def test_a_zero_gap_takes_no_pause_and_a_set_gap_takes_one_per_frame(monkeypatch):
    assert _count_data_frame_pauses(monkeypatch, 0.0) == []
    pauses = _count_data_frame_pauses(monkeypatch, 0.002)
    assert len(pauses) == protocol.FLASH_PAGE_SIZE // 8 and set(pauses) == {0.002}


def test_the_source_of_flash_uses_the_configured_gap_and_no_fixed_pause_between_data_frames():
    import inspect
    source = inspect.getsource(protocol.URTCFlasher)
    assert "time.sleep(FRAME_GAP_S)" in source
    assert "time.sleep(0.001)" not in source
