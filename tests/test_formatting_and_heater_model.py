# =============================================================================
# URTC-FLASHER - tests/test_formatting_and_heater_model.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The text helpers every program of the family shares, and the simulated soldering iron of the virtual board."""
from __future__ import annotations

import json

import pytest

from urtc_can import heater_sim, protocol
from urtc_ui import formatting as fmt


class TestIdentifiers:
    def test_standard_and_extended_identifiers_have_three_and_eight_digits(self):
        assert fmt.format_can_id(0x1A0) == "0x1A0"
        assert fmt.format_can_id(0x123, extended=True) == "0x00000123"

    @pytest.mark.parametrize("value", [-1, 0x800, 1.5, "1", True])
    def test_a_standard_identifier_outside_the_range_is_refused(self, value):
        with pytest.raises(ValueError):
            fmt.format_can_id(value)

    def test_an_extended_identifier_goes_up_to_29_bits(self):
        assert fmt.format_can_id(0x1FFFFFFF, extended=True) == "0x1FFFFFFF"
        with pytest.raises(ValueError):
            fmt.format_can_id(0x20000000, extended=True)

    @pytest.mark.parametrize("text, number", [("0x1a0", 0x1A0), ("1A0h", 0x1A0), ("416", 416), ("  0X7ff ", 0x7FF)])
    def test_an_identifier_is_read_in_the_three_spellings(self, text, number):
        assert fmt.parse_can_id(text) == number

    @pytest.mark.parametrize("text", ["", "xyz", "0x", "1g0h", "2048", "-1"])
    def test_what_is_not_an_identifier_is_refused(self, text):
        with pytest.raises(ValueError):
            fmt.parse_can_id(text)

    def test_the_extended_range_accepts_what_the_standard_one_refuses(self):
        assert fmt.parse_can_id("0x800", extended=True) == 0x800


class TestFramesAndBitrates:
    def test_bytes_and_frames_are_upper_case_pairs(self):
        assert fmt.format_hex(bytes([1, 0xAB, 255])) == "01 AB FF"
        assert fmt.format_hex([1, 2], separator="") == "0102"
        assert fmt.format_hex(b"") == ""
        assert fmt.format_frame(0x1A0, bytes([1, 2, 3])) == "0x1A0#01 02 03"

    @pytest.mark.parametrize("bps, label", [(500000, "500 kbit/s"), (1000000, "1 Mbit/s"), (800, "800 bit/s"), (125000, "125 kbit/s"), (2500, "2500 bit/s")])
    def test_a_bitrate_is_written_with_the_largest_whole_unit(self, bps, label):
        assert fmt.format_bitrate(bps) == label

    @pytest.mark.parametrize("bps", [0, -5, 1.5, "500", True])
    def test_a_bitrate_that_is_not_positive_is_refused(self, bps):
        with pytest.raises(ValueError):
            fmt.format_bitrate(bps)

    @pytest.mark.parametrize("label, bps", [("500 kbit/s", 500000), ("1 Mbit/s", 1000000), ("250k", 250000), ("1M", 1000000), ("125 kbps", 125000), ("0.5 mbps", 500000), ("9600", 9600), ("800 bit/s", 800)])
    def test_a_bitrate_is_read_in_the_spellings_of_the_family(self, label, bps):
        assert fmt.parse_bitrate(label) == bps

    @pytest.mark.parametrize("label", ["", "fast", "0", "0.0001 k", "1.5", "-3k"])
    def test_what_is_not_a_whole_positive_bitrate_is_refused(self, label):
        with pytest.raises(ValueError):
            fmt.parse_bitrate(label)

    def test_every_label_it_writes_it_reads_back(self):
        for bps in (10_000, 20_000, 50_000, 100_000, 125_000, 250_000, 500_000, 800_000, 1_000_000):
            assert fmt.parse_bitrate(fmt.format_bitrate(bps)) == bps


class TestSizesAndTimes:
    @pytest.mark.parametrize("count, text", [(0, "0 B"), (1023, "1023 B"), (1024, "1.0 KiB"), (1536, "1.5 KiB"), (1024 ** 2, "1.0 MiB"), (5 * 1024 ** 3, "5.0 GiB"), (2048 * 1024 ** 3, "2048.0 GiB")])
    def test_sizes(self, count, text):
        assert fmt.format_bytes(count) == text

    @pytest.mark.parametrize("count", [-1, 1.5, "1", True])
    def test_a_size_that_is_not_a_count_is_refused(self, count):
        with pytest.raises(ValueError):
            fmt.format_bytes(count)

    @pytest.mark.parametrize("ms, text", [(0, "0 ms"), (250, "250 ms"), (1000, "1 s"), (2500, "2.5 s"), (59949, "59.9 s"), (60000, "1 min"), (125000, "2 min 5 s")])
    def test_durations(self, ms, text):
        assert fmt.format_duration_ms(ms) == text

    @pytest.mark.parametrize("ms", [-1, 2.5, "9", True])
    def test_a_duration_that_is_not_a_count_is_refused(self, ms):
        with pytest.raises(ValueError):
            fmt.format_duration_ms(ms)

    @pytest.mark.parametrize("seconds, text", [(0, "0 s"), (59, "59 s"), (60, "1 min"), (3725, "1 h 2 min"), (90000, "1 d 1 h"), (86400 + 61, "1 d 1 min")])
    def test_uptime_shows_two_units_at_most(self, seconds, text):
        assert fmt.format_uptime(seconds) == text

    @pytest.mark.parametrize("seconds", [-1, 1.0, "3", True])
    def test_an_uptime_that_is_not_a_count_is_refused(self, seconds):
        with pytest.raises(ValueError):
            fmt.format_uptime(seconds)


class TestHeaterConfiguration:
    def test_the_file_of_the_package_gives_the_parameters(self):
        config = heater_sim.load_config()
        assert config["heater_power_w"] == 65.0
        assert set(config) == set(heater_sim._DEFAULTS)

    def test_a_missing_or_broken_file_falls_back_to_the_built_in_values(self, tmp_path):
        assert heater_sim.load_config(tmp_path / "none.json") == heater_sim._DEFAULTS
        broken = tmp_path / "broken.json"
        broken.write_text("{not json", encoding="utf-8")
        assert heater_sim.load_config(broken) == heater_sim._DEFAULTS

    def test_the_file_then_the_overrides_win_and_unknown_names_are_ignored(self, tmp_path):
        path = tmp_path / "model.json"
        path.write_text(json.dumps({"kp": 0.5, "unknown": 1, "ambient_c": 20.0}), encoding="utf-8")
        config = heater_sim.load_config(path, ambient_c=30.0, nothing=3)
        assert config["kp"] == 0.5
        assert config["ambient_c"] == 30.0
        assert "unknown" not in config and "nothing" not in config


class TestSolderingIron:
    def test_it_starts_cold_and_stays_cold_without_a_target(self):
        iron = heater_sim.SolderingIronModel()
        frames = iron.advance(1.0)
        assert iron.temperature_c == pytest.approx(25.0)
        assert iron.duty == 0.0
        assert len(frames) == 6  # one telemetry frame every 150 ms
        assert all(frame[0] == protocol.CAN_ID_SOLDER_TELEMETRY for frame in frames)

    def test_it_heats_towards_a_repeated_target_without_overshooting_the_clamp(self):
        iron = heater_sim.SolderingIronModel()
        for _ in range(200):
            iron.set_target(300)
            iron.advance(0.1)
        assert 250 < iron.temperature_c < 345  # 20 s of simulated time
        assert 0.0 <= iron.duty <= 1.0
        assert iron.peak_c >= iron.temperature_c

    def test_the_target_is_held_to_the_ceiling_and_to_zero(self):
        iron = heater_sim.SolderingIronModel()
        iron.set_target(9000)
        assert iron.setpoint_c == 445
        iron.set_target(-20)
        assert iron.setpoint_c == 0

    def test_a_target_that_is_not_repeated_lapses_and_the_iron_cools(self):
        iron = heater_sim.SolderingIronModel()
        for _ in range(30):
            iron.set_target(300)
            iron.advance(0.1)
        hot = iron.temperature_c
        iron.advance(0.5)  # the watchdog (250 ms) gives up the target
        assert iron.setpoint_c == 0 and iron.duty == 0.0
        iron.advance(20.0)
        assert iron.temperature_c < hot

    def test_a_target_below_the_temperature_switches_the_heater_off_through_anti_windup(self):
        iron = heater_sim.SolderingIronModel({"ambient_c": 25.0})
        iron.temperature_c = 400.0
        for _ in range(5):
            iron.set_target(100)
            iron.advance(0.05)
        assert iron.duty == 0.0

    def test_the_derivative_term_acts_when_it_is_configured(self):
        iron = heater_sim.SolderingIronModel({"kd": 0.001})
        iron.set_target(200)
        iron.advance(0.05)
        assert iron.duty > 0.0

    def test_the_telemetry_frame_carries_the_rounded_temperature(self):
        iron = heater_sim.SolderingIronModel()
        iron.temperature_c = 199.6
        frame = iron.telemetry()
        assert frame == protocol.encode("solder_telemetry", temperature_c=200)
        iron.temperature_c = -3.0
        assert iron.telemetry() == protocol.encode("solder_telemetry", temperature_c=0)

    def test_advancing_by_nothing_or_a_negative_time_does_nothing(self):
        iron = heater_sim.SolderingIronModel()
        assert iron.advance(0) == []
        assert iron.advance(-1.0) == []
        assert iron.temperature_c == 25.0
