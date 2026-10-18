# =============================================================================
# URTC Flasher - tests/test_validation_formats.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Image plausibility checks done before anything is flashed: the raw .bin
path of the CAN update, and the .hex / .elf / .bin paths of the SWD section.
Each rejection reason is exercised with a small synthetic file."""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from flasher_config import APP_FLASH_ADDR, APP_MAX_SIZE
from flasher_validation import validate_firmware_file, validate_swd_image_file

GOOD_SP = 0x20009000
GOOD_RESET = APP_FLASH_ADDR + 0x101


def _write(tmp_path, name, payload):
    path = tmp_path / name
    path.write_bytes(payload)
    return str(path)


# ---- raw .bin of the CAN update --------------------------------------------------
def test_a_missing_file_is_reported_not_raised(tmp_path):
    ok, reason, size = validate_firmware_file(str(tmp_path / "nothing.bin"))
    assert (ok, size) == (False, 0)
    assert "can't read" in reason


def test_an_empty_file_is_rejected(tmp_path):
    assert validate_firmware_file(_write(tmp_path, "a.bin", b""))[:2] == (False, "empty file")


def test_a_file_that_cannot_hold_a_vector_table_is_rejected(tmp_path):
    ok, reason, size = validate_firmware_file(_write(tmp_path, "a.bin", b"\x00" * 7))
    assert not ok and "too small" in reason and size == 7


def test_a_file_larger_than_the_slot_is_rejected_by_size_first(tmp_path):
    path = _write(tmp_path, "a.bin", struct.pack("<II", GOOD_SP, GOOD_RESET) + bytes(APP_MAX_SIZE))
    ok, reason, _ = validate_firmware_file(path)
    assert not ok and "too large" in reason


def test_exactly_the_slot_size_is_accepted(tmp_path):
    path = _write(tmp_path, "a.bin", struct.pack("<II", GOOD_SP, GOOD_RESET) + bytes(APP_MAX_SIZE - 8))
    assert validate_firmware_file(path)[0] is True


def test_a_reset_handler_outside_the_slot_means_the_wrong_image(tmp_path):
    for handler in (0x08000101, APP_FLASH_ADDR - 1, APP_FLASH_ADDR + APP_MAX_SIZE):
        path = _write(tmp_path, "a.bin", struct.pack("<II", GOOD_SP, handler) + bytes(100))
        ok, reason, _ = validate_firmware_file(path)
        assert not ok and "reset handler" in reason, hex(handler)


def test_the_slave_slot_has_its_own_base_address(tmp_path):
    path = _write(tmp_path, "slave.bin", struct.pack("<II", GOOD_SP, 0x08005101) + bytes(100))
    assert validate_firmware_file(path)[0] is False
    assert validate_firmware_file(path, expected_base_addr=0x08005000, max_size=54 * 1024)[0] is True


# ---- Intel HEX ------------------------------------------------------------------------
def _hex_record(address, record_type, data=b""):
    body = bytes([len(data), address >> 8, address & 0xFF, record_type]) + data
    checksum = (-sum(body)) & 0xFF
    return ":" + (body + bytes([checksum])).hex().upper()


def _hex_file(tmp_path, records, name="image.hex"):
    path = tmp_path / name
    path.write_text("\n".join(records) + "\n", encoding="ascii")
    return str(path)


def _hex_image(base, sp=GOOD_SP, reset=GOOD_RESET, extra=()):
    records = [_hex_record(0, 0x04, struct.pack(">H", base >> 16)),
               _hex_record(base & 0xFFFF, 0x00, struct.pack("<II", sp, reset))]
    records.extend(extra)
    records.append(_hex_record(0, 0x01))
    return records


def test_a_valid_hex_is_accepted_and_reports_its_load_address(tmp_path):
    ok, reason, _ = validate_swd_image_file(_hex_file(tmp_path, _hex_image(APP_FLASH_ADDR)), APP_MAX_SIZE, "application", APP_FLASH_ADDR)
    assert ok and "0x08008000" in reason


def test_hex_without_the_colon_is_rejected(tmp_path):
    ok, reason, _ = validate_swd_image_file(_hex_file(tmp_path, ["hello"]), APP_MAX_SIZE, "application")
    assert not ok and "not a valid Intel HEX" in reason


def test_hex_with_a_bad_checksum_is_rejected(tmp_path):
    records = _hex_image(APP_FLASH_ADDR)
    records[1] = records[1][:-2] + ("00" if not records[1].endswith("00") else "01")
    ok, reason, _ = validate_swd_image_file(_hex_file(tmp_path, records), APP_MAX_SIZE, "application", APP_FLASH_ADDR)
    assert not ok and "checksum" in reason


def test_hex_with_bad_digits_is_rejected(tmp_path):
    ok, reason, _ = validate_swd_image_file(_hex_file(tmp_path, [":10ZZ0000AABBCCDD"] + _hex_image(APP_FLASH_ADDR)), APP_MAX_SIZE, "application")
    assert not ok and "bad hex digits" in reason


def test_hex_without_an_eof_record_is_rejected(tmp_path):
    ok, reason, _ = validate_swd_image_file(_hex_file(tmp_path, _hex_image(APP_FLASH_ADDR)[:-1]), APP_MAX_SIZE, "application", APP_FLASH_ADDR)
    assert not ok and "EOF" in reason


def test_hex_with_only_an_eof_has_no_data(tmp_path):
    ok, reason, _ = validate_swd_image_file(_hex_file(tmp_path, [_hex_record(0, 0x01)]), APP_MAX_SIZE, "application")
    assert not ok and "no data" in reason


def test_hex_with_a_truncated_line_is_rejected(tmp_path):
    ok, reason, _ = validate_swd_image_file(_hex_file(tmp_path, [":0400"]), APP_MAX_SIZE, "application")
    assert not ok and "malformed" in reason


def test_hex_missing_its_checksum_digits_is_rejected(tmp_path):
    ok, reason, _ = validate_swd_image_file(_hex_file(tmp_path, [":0000000100"[:-2] + "0"]), APP_MAX_SIZE, "application")
    assert not ok


def test_hex_that_does_not_decode_as_text_is_rejected(tmp_path):
    path = _write(tmp_path, "image.hex", b":\x81\x8d\x8f\x90\x9d\x81\x8d\x8f\n")
    ok, reason, _ = validate_swd_image_file(path, APP_MAX_SIZE, "application")
    assert not ok and "decode" in reason


def test_hex_with_an_implausible_stack_pointer_is_rejected(tmp_path):
    ok, reason, _ = validate_swd_image_file(_hex_file(tmp_path, _hex_image(APP_FLASH_ADDR, sp=0x12345678)), APP_MAX_SIZE, "application", APP_FLASH_ADDR)
    assert not ok and "stack pointer" in reason


def test_hex_for_the_wrong_slot_is_rejected(tmp_path):
    ok, reason, _ = validate_swd_image_file(_hex_file(tmp_path, _hex_image(0x08000000, reset=0x08000101)), APP_MAX_SIZE, "application", APP_FLASH_ADDR)
    assert not ok and "wrong image" in reason


def test_hex_whose_reset_handler_leaves_the_slot_is_rejected(tmp_path):
    ok, reason, _ = validate_swd_image_file(_hex_file(tmp_path, _hex_image(APP_FLASH_ADDR, reset=0x08000101)), APP_MAX_SIZE, "application", APP_FLASH_ADDR)
    assert not ok and "reset handler" in reason


def test_hex_with_more_data_than_the_slot_is_rejected(tmp_path):
    records = [_hex_record(0, 0x04, struct.pack(">H", APP_FLASH_ADDR >> 16))]
    for offset in range(0, 64, 32):
        records.append(_hex_record((APP_FLASH_ADDR & 0xFFFF) + offset, 0x00, bytes(32)))
    records.append(_hex_record(0, 0x01))
    ok, reason, _ = validate_swd_image_file(_hex_file(tmp_path, records), 40, "bootloader")
    assert not ok and "larger than" in reason


def test_a_metadata_block_below_the_image_does_not_hide_the_vector_table(tmp_path):
    extra = [_hex_record(0x0100, 0x00, b"\x01\x02\x03\x04")]  # lower address than the application
    records = _hex_image(APP_FLASH_ADDR, extra=extra)
    ok, _, _ = validate_swd_image_file(_hex_file(tmp_path, records), APP_MAX_SIZE, "application", APP_FLASH_ADDR)
    assert ok


def test_hex_without_a_vector_table_is_accepted_with_a_warning(tmp_path):
    records = [_hex_record(0, 0x04, struct.pack(">H", 0x0800)), _hex_record(0x1000, 0x00, b"\xAA\xBB"), _hex_record(0, 0x01)]
    ok, reason, _ = validate_swd_image_file(_hex_file(tmp_path, records), APP_MAX_SIZE, "application")
    assert ok and "couldn't confidently" in reason


def test_hex_extended_segment_address_records_are_understood(tmp_path):
    records = [_hex_record(0, 0x02, struct.pack(">H", 0x0800 << 0)), _hex_record(0, 0x00, struct.pack("<II", GOOD_SP, 0x00008101)), _hex_record(0, 0x01)]
    ok, reason, _ = validate_swd_image_file(_hex_file(tmp_path, records), APP_MAX_SIZE, "application")
    assert ok and "0x00008000" in reason


# ---- ELF ---------------------------------------------------------------------------------
def _elf(segments, machine=0x28, ei_class=1, ei_data=1, phnum=None, magic=b"\x7fELF"):
    """segments: list of (paddr, payload). One PT_LOAD program header per segment."""
    header_size, ph_size = 52, 32
    count = len(segments) if phnum is None else phnum
    data_offset = header_size + ph_size * len(segments)
    header = bytearray(header_size)
    header[0:4] = magic
    header[4], header[5], header[6] = ei_class, ei_data, 1
    struct.pack_into("<H", header, 18, machine)
    struct.pack_into("<I", header, 28, header_size)
    struct.pack_into("<H", header, 42, ph_size)
    struct.pack_into("<H", header, 44, count)
    program_headers, blobs, offset = b"", b"", data_offset
    for paddr, payload in segments:
        program_headers += struct.pack("<IIIIIIII", 1, offset, paddr, paddr, len(payload), len(payload), 5, 4)
        blobs += payload
        offset += len(payload)
    return bytes(header) + program_headers + blobs


def _elf_file(tmp_path, content, name="image.elf"):
    return _write(tmp_path, name, content)


def test_a_valid_elf_is_accepted(tmp_path):
    image = struct.pack("<II", GOOD_SP, GOOD_RESET) + bytes(64)
    ok, reason, _ = validate_swd_image_file(_elf_file(tmp_path, _elf([(APP_FLASH_ADDR, image)])), APP_MAX_SIZE, "application", APP_FLASH_ADDR)
    assert ok and "0x08008000" in reason


@pytest.mark.parametrize("kwargs, fragment", [
    ({"magic": b"NOPE"}, "ELF magic"),
    ({"ei_class": 2}, "32-bit"),
    ({"ei_data": 2}, "little-endian"),
    ({"machine": 0x03}, "not ARM"),
    ({"phnum": 0}, "no program headers"),
])
def test_elf_header_problems_are_reported(tmp_path, kwargs, fragment):
    image = struct.pack("<II", GOOD_SP, GOOD_RESET) + bytes(64)
    ok, reason, _ = validate_swd_image_file(_elf_file(tmp_path, _elf([(APP_FLASH_ADDR, image)], **kwargs)), APP_MAX_SIZE, "application", APP_FLASH_ADDR)
    assert not ok and fragment in reason


def test_a_too_short_elf_is_rejected(tmp_path):
    ok, reason, _ = validate_swd_image_file(_elf_file(tmp_path, b"\x7fELF\x01\x01"), APP_MAX_SIZE, "application")
    assert not ok and "ELF magic" in reason


def test_a_truncated_elf_segment_is_reported_as_an_interrupted_download(tmp_path):
    image = struct.pack("<II", GOOD_SP, GOOD_RESET) + bytes(200)
    content = _elf([(APP_FLASH_ADDR, image)])
    ok, reason, _ = validate_swd_image_file(_elf_file(tmp_path, content[:-100]), APP_MAX_SIZE, "application", APP_FLASH_ADDR)
    assert not ok and "truncated ELF" in reason


def test_an_elf_with_no_loadable_segment_is_rejected(tmp_path):
    content = bytearray(_elf([(APP_FLASH_ADDR, b"\x00" * 16)]))
    struct.pack_into("<I", content, 52, 4)  # p_type = PT_NOTE
    ok, reason, _ = validate_swd_image_file(_elf_file(tmp_path, bytes(content)), APP_MAX_SIZE, "application", APP_FLASH_ADDR)
    assert not ok and "no loadable" in reason


def test_an_elf_with_more_data_than_the_slot_is_rejected(tmp_path):
    ok, reason, _ = validate_swd_image_file(_elf_file(tmp_path, _elf([(APP_FLASH_ADDR, struct.pack("<II", GOOD_SP, GOOD_RESET) + bytes(300))])), 100, "bootloader", APP_FLASH_ADDR)
    assert not ok and "larger than" in reason


def test_an_elf_with_a_bad_stack_pointer_is_rejected(tmp_path):
    image = struct.pack("<II", 0x12345678, GOOD_RESET) + bytes(16)
    ok, reason, _ = validate_swd_image_file(_elf_file(tmp_path, _elf([(APP_FLASH_ADDR, image)])), APP_MAX_SIZE, "application", APP_FLASH_ADDR)
    assert not ok and "stack pointer" in reason


def test_an_elf_for_another_slot_is_rejected(tmp_path):
    image = struct.pack("<II", GOOD_SP, 0x08000101) + bytes(16)
    ok, reason, _ = validate_swd_image_file(_elf_file(tmp_path, _elf([(0x08000000, image)])), APP_MAX_SIZE, "application", APP_FLASH_ADDR)
    assert not ok and "wrong image" in reason


def test_an_elf_whose_reset_handler_leaves_the_slot_is_rejected(tmp_path):
    image = struct.pack("<II", GOOD_SP, 0x08000101) + bytes(16)
    ok, reason, _ = validate_swd_image_file(_elf_file(tmp_path, _elf([(APP_FLASH_ADDR, image)])), APP_MAX_SIZE, "application", APP_FLASH_ADDR)
    assert not ok and "reset handler" in reason


def test_an_axf_extension_is_handled_as_elf(tmp_path):
    image = struct.pack("<II", GOOD_SP, GOOD_RESET) + bytes(16)
    ok, _, _ = validate_swd_image_file(_elf_file(tmp_path, _elf([(APP_FLASH_ADDR, image)]), "image.AXF"), APP_MAX_SIZE, "application", APP_FLASH_ADDR)
    assert ok


# ---- bin through the SWD picker -----------------------------------------------------------
def test_swd_picker_rejects_missing_and_empty_files(tmp_path):
    assert validate_swd_image_file(str(tmp_path / "none.bin"), 100, "application")[0] is False
    assert validate_swd_image_file(_write(tmp_path, "empty.bin", b""), 100, "application")[:2] == (False, "empty file")


def test_swd_picker_applies_the_slot_size_to_a_bin(tmp_path):
    path = _write(tmp_path, "a.bin", struct.pack("<II", GOOD_SP, GOOD_RESET) + bytes(500))
    ok, reason, _ = validate_swd_image_file(path, 100, "bootloader", APP_FLASH_ADDR)
    assert not ok and "100" in reason
    assert validate_swd_image_file(path, APP_MAX_SIZE, "application", APP_FLASH_ADDR)[0] is True
