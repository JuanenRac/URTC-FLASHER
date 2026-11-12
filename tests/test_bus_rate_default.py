# =============================================================================
# URTC Flasher - tests/test_bus_rate_default.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The bus of the tool heads runs at 1 Mbit/s: the flasher opens it at that speed and keeps 500 kbit/s (the speed of the early boards) in the table of the adapter."""
from __future__ import annotations

import flasher_config as config
from urtc_can import protocol


def test_the_default_speed_is_one_megabit_from_the_specification():
    assert protocol.BITRATE == 1_000_000 and protocol.BITRATE_LEGACY == 500_000
    assert config.BITRATE_DEFAULT_SLCAN_CODE == protocol.SLCAN_BITRATE_DEFAULT_CODE == "8"
    assert config.DEFAULT_BITRATE_LABEL == "1 Mbit/s"


def test_both_speeds_of_the_family_are_in_the_table_of_the_adapter():
    labels = dict(config.SLCAN_BITRATES)
    assert labels[config.DEFAULT_BITRATE_LABEL] == config.BITRATE_DEFAULT_SLCAN_CODE
    assert labels["500 kbit/s"] == "6"
    assert len(set(labels.values())) == len(labels)         # no code is listed twice


def test_the_default_code_is_the_one_the_transport_opens_the_channel_with():
    import inspect

    from urtc_can import transports
    default = inspect.signature(transports.SLCAN.open_channel).parameters["bitrate_code"].default
    assert default == config.BITRATE_DEFAULT_SLCAN_CODE
