# =============================================================================
# URTC Flasher - tests/test_flasher_config_file.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The configuration file and the language files: what is read, what is kept when saving and what falls back to the compiled-in values when a field is wrong."""
from __future__ import annotations

import json

import pytest

import flasher_config as config


@pytest.fixture()
def config_file(tmp_path, monkeypatch):
    path = tmp_path / "urtc_config.json"
    monkeypatch.setattr(config, "CONFIG_FILE_PATH", str(path))
    return path


def overrides(config_file, content, log=None):
    config_file.write_text(content if isinstance(content, str) else json.dumps(content), encoding="utf-8")
    return config._load_config_overrides(log)


KEY = "ab" * 32


# ---- load_config / save_config ----------------------------------------------------------------------------------

def test_a_missing_file_reads_as_an_empty_configuration(config_file):
    assert config.load_config() == {}


def test_a_broken_or_non_object_file_reads_as_an_empty_configuration(config_file):
    config_file.write_text("{not json", encoding="utf-8")
    assert config.load_config() == {}
    config_file.write_text("[1, 2]", encoding="utf-8")
    assert config.load_config() == {}
    config_file.write_bytes(b"\xff\xfe\x00bad")
    assert config.load_config() == {}


def test_saving_merges_into_the_keys_a_person_edited_by_hand(config_file):
    config_file.write_text(json.dumps({"hardware_id": "0x01", "language": "es"}), encoding="utf-8")
    assert config.save_config({"language": "de"}) is True
    assert json.loads(config_file.read_text(encoding="utf-8")) == {"hardware_id": "0x01", "language": "de"}
    assert not config_file.with_name("urtc_config.json.tmp").exists()


def test_saving_where_nothing_can_be_written_returns_false(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CONFIG_FILE_PATH", str(tmp_path / "missing_folder" / "urtc_config.json"))
    assert config.save_config({"language": "de"}) is False


# ---- language files ------------------------------------------------------------------------------------------------

def test_a_language_file_skips_comments_and_blank_lines_and_unescapes_newlines(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "LANGUAGE_FOLDER", str(tmp_path))
    (tmp_path / "xx.lng").write_text("﻿# a comment\n\nGREETING=Hello\\nworld\nNO_SEPARATOR\nWITH=EQUALS=inside\r\n", encoding="utf-8")
    assert config.load_language("xx") == {"GREETING": "Hello\nworld", "WITH": "EQUALS=inside"}


def test_a_missing_language_file_reads_as_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "LANGUAGE_FOLDER", str(tmp_path))
    assert config.load_language("zz") == {}


def test_a_text_without_a_translation_is_shown_as_its_key_and_substitutions_survive_a_bad_template(monkeypatch):
    monkeypatch.setattr(config, "_translations", {"HELLO": "Hello {name}", "BAD": "Hello {missing}"})
    assert config._("HELLO", name="Ana") == "Hello Ana"
    assert config._("BAD", name="Ana") == "Hello {missing}"
    assert config._("UNKNOWN_KEY") == "UNKNOWN_KEY"


def test_a_log_line_is_translated_by_its_first_word_and_other_lines_are_left_alone(monkeypatch):
    monkeypatch.setattr(config, "_translations", {"QTLOG_PORT_SCAN": "Scanning ports", "QTLOG_ERROR": "Error"})
    assert config.translate_log_line("PORT_SCAN COM3") == "Scanning ports: COM3"
    assert config.translate_log_line("ERROR something broke") == "Error"
    assert config.translate_log_line("lower case line") == "lower case line"
    assert config.translate_log_line("UNKNOWN_WORD detail") == "UNKNOWN_WORD detail"


def test_a_status_is_translated_by_its_longest_known_run_of_words(monkeypatch):
    monkeypatch.setattr(config, "_translations", {"QTSTATUS_CONNECTED": "Connected", "QTSTATUS_CONNECTED_TO": "Connected to"})
    assert config.translate_status("CONNECTED TO COM3") == "Connected to COM3"
    assert config.translate_status("CONNECTED COM3") == "Connected COM3"
    assert config.translate_status("NOTHING HERE") == "NOTHING HERE"


# ---- the technical overrides ----------------------------------------------------------------------------------------

def test_without_a_file_the_compiled_in_values_are_used_and_the_missing_keys_are_said(config_file):
    messages: list[str] = []
    result = config._load_config_overrides(messages.append)
    assert result == (config.THIS_HARDWARE_ID, config.HMAC_KEY, config.SLAVE_HMAC_KEY, config.APP_MAX_SIZE, config.BOOTLOADER_MAX_SIZE,
                      config.FLASH_PAGE_SIZE, config.BOOTLOADER_FLASH_ADDR, config.APP_FLASH_ADDR, False)
    assert any("hmac_key_hex/slave_hmac_key_hex" in line for line in messages)


def test_a_file_that_is_not_json_falls_back_to_the_defaults_and_says_so(config_file):
    messages: list[str] = []
    result = overrides(config_file, "{broken", messages.append)
    assert result[-1] is False
    assert any(line.startswith("WARNING") for line in messages)


def test_every_valid_override_is_applied(config_file):
    messages: list[str] = []
    result = overrides(config_file, {"hardware_id": "0x0303CC01", "hmac_key_hex": KEY, "slave_hmac_key_hex": KEY, "app_max_size": "0x1000",
                                      "bootloader_max_size": 4096.0, "flash_page_size": config.FLASH_PAGE_SIZE, "bootloader_flash_addr": "0x08000000",
                                      "app_flash_addr": 134250496}, messages.append)
    hw_id, key, slave_key, app_max, bootloader_max, page, bootloader_addr, app_addr, loaded = result
    assert hw_id == 0x0303CC01 and key == bytes.fromhex(KEY) and slave_key == bytes.fromhex(KEY)
    assert app_max == 0x1000 and bootloader_max == 4096 and page == config.FLASH_PAGE_SIZE
    assert bootloader_addr == 0x08000000 and app_addr == 134250496 and loaded is True
    assert any(line.startswith("Loaded config overrides") for line in messages)
    assert not any("No hmac_key_hex" in line for line in messages)


@pytest.mark.parametrize("field", ["app_max_size", "bootloader_max_size", "bootloader_flash_addr", "app_flash_addr"])
@pytest.mark.parametrize("value", [True, 12.5, "not a number", -1, 0x1_0000_0000])
def test_a_wrong_number_reverts_only_that_field(config_file, field, value):
    messages: list[str] = []
    defaults = config._load_config_overrides()
    result = overrides(config_file, {field: value, "hmac_key_hex": KEY}, messages.append)
    names = ["hw", "key", "slave", "app_max_size", "bootloader_max_size", "flash_page_size", "bootloader_flash_addr", "app_flash_addr"]
    assert result[names.index(field)] == defaults[names.index(field)]
    assert result[1] == bytes.fromhex(KEY)   # the field that was right still applied
    assert any(field in line and "fell back" in line for line in messages)


def test_a_wrong_hardware_id_or_key_reverts_to_the_default(config_file):
    messages: list[str] = []
    defaults = config._load_config_overrides()
    result = overrides(config_file, {"hardware_id": True, "hmac_key_hex": "abcd", "slave_hmac_key_hex": "zz"}, messages.append)
    assert result[0] == defaults[0] and result[1] == defaults[1] and result[2] == defaults[2]
    joined = " ".join(messages)
    assert "hardware_id" in joined and "hmac_key_hex" in joined and "slave_hmac_key_hex" in joined


def test_a_hardware_id_out_of_range_is_skipped(config_file):
    defaults = config._load_config_overrides()
    assert overrides(config_file, {"hardware_id": 0x1_0000_0000})[0] == defaults[0]


def test_a_page_size_other_than_the_bootloaders_is_refused(config_file):
    messages: list[str] = []
    result = overrides(config_file, {"flash_page_size": config.FLASH_PAGE_SIZE * 2}, messages.append)
    assert result[5] == config.FLASH_PAGE_SIZE
    assert any("is not the bootloader's" in line for line in messages)
