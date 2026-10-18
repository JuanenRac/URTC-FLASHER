# =============================================================================
# URTC Flasher - tests/test_slave_flash.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The expansion-slave update (0x210-0x219 relayed by the main board), against
a scripted stand-in for the slave bootloader: the frames the flasher sends,
what it does with each way the slave can answer, and the guards in front."""
from __future__ import annotations

import hashlib
import hmac
import json
import struct
import sys
import time
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

import flasher_config as cfg
from flasher_protocol import FlashError, URTCFlasher
from conftest import BENCH_SLAVE_KEY


class SlavePeer:
    """Answers the relayed slave queries; records every frame the flasher sends."""

    def __init__(self, responder=0x01, outcome="ok", reason=0x03, answer_progress=True, patch_extension=False, status_polls_before_done=1):
        self.sent = []
        self.queue = []
        self.responder = responder
        self.outcome = outcome
        self.reason = reason
        self.answer_progress = answer_progress
        self.patch_extension = patch_extension
        self.status_polls_before_done = status_polls_before_done
        self._ended = False
        self._polls = 0

    def send_frame(self, can_id, data):
        data = bytes(data)
        self.sent.append((can_id, data))
        if can_id == cfg.CAN_ID_SLAVE_VERSION_RESP_1:
            self.queue.append((cfg.CAN_ID_SLAVE_VERSION_RESP_1, bytes([self.responder]) + struct.pack(">I", cfg.SLAVE_HARDWARE_ID) + struct.pack(">H", 0) + b"\x00"))
            tail = bytes([2, 1])
            if self.patch_extension:
                tail += bytes([7, 3, 5])
            self.queue.append((cfg.CAN_ID_SLAVE_VERSION_RESP_2, tail))
        elif can_id == cfg.CAN_ID_SLAVE_END_UPDATE:
            self._ended = True
        elif can_id == cfg.CAN_ID_SLAVE_STATUS:
            if not self._ended:
                self.queue.append((cfg.CAN_ID_SLAVE_STATUS, b"\x03"))
            else:
                self._polls += 1
                if self.outcome == "fail":
                    status = 0x05
                elif self.outcome == "error":
                    status = 0xFF
                elif self._polls > self.status_polls_before_done:
                    status = 0x04
                else:
                    status = 0x07
                self.queue.append((cfg.CAN_ID_SLAVE_STATUS, bytes([status])))
        elif can_id == cfg.CAN_ID_SLAVE_PROGRESS and self.answer_progress:
            self.queue.append((cfg.CAN_ID_SLAVE_PROGRESS, b"\x32"))
        elif can_id == cfg.CAN_ID_SLAVE_VERIFY_FAIL_REASON:
            self.queue.append((cfg.CAN_ID_SLAVE_VERIFY_FAIL_REASON, bytes([self.reason])))

    def read_frame(self, timeout=0.05):
        if self.queue:
            return self.queue.pop(0)
        time.sleep(min(timeout, 0.002))
        return None

    def frames(self, can_id):
        return [data for frame_id, data in self.sent if frame_id == can_id]


def _image(tmp_path, size=100, name="slave.bin"):
    path = tmp_path / name
    path.write_bytes(bytes((i * 7 + 1) & 0xFF for i in range(size)))
    return str(path), path.read_bytes()


def _flasher(peer, **kwargs):
    logs = []
    return URTCFlasher(peer, logs.append, **kwargs), logs


def test_a_successful_slave_update_sends_the_documented_sequence(tmp_path):
    path, image = _image(tmp_path, 100)
    peer = SlavePeer()
    percentages = []
    flasher, _logs = _flasher(peer, progress_cb=percentages.append)
    assert flasher.flash_slave(path) is True

    ids = [frame_id for frame_id, _ in peer.sent]
    assert ids[0] == cfg.CAN_ID_SLAVE_VERSION_RESP_1
    assert ids.index(cfg.CAN_ID_SLAVE_START_UPDATE) < ids.index(cfg.CAN_ID_SLAVE_HMAC_CHUNK) < ids.index(cfg.CAN_ID_SLAVE_DATA) < ids.index(cfg.CAN_ID_SLAVE_END_UPDATE)

    assert peer.frames(cfg.CAN_ID_SLAVE_START_UPDATE) == [struct.pack(">II", 100, cfg.SLAVE_HARDWARE_ID)]
    chunks = peer.frames(cfg.CAN_ID_SLAVE_HMAC_CHUNK)
    assert len(chunks) == 4 and all(len(chunk) == 8 for chunk in chunks)
    assert b"".join(chunks) == hmac.new(BENCH_SLAVE_KEY, image, hashlib.sha256).digest()
    assert b"".join(peer.frames(cfg.CAN_ID_SLAVE_DATA)) == image
    assert [len(chunk) for chunk in peer.frames(cfg.CAN_ID_SLAVE_DATA)][-1] == 100 % 8
    assert peer.frames(cfg.CAN_ID_SLAVE_END_UPDATE) == [struct.pack(">IHH", zlib.crc32(image) & 0xFFFFFFFF, 0, 0)]
    assert percentages[-1] == 100


def test_the_version_of_the_manifest_goes_into_the_end_frame(tmp_path):
    path, image = _image(tmp_path, 64)
    manifest = {"version": "0.4.0", "component": "slave_application", "hardware_id": cfg.SLAVE_HARDWARE_ID, "sha256": hashlib.sha256(image).hexdigest(),
                "hmac_sha256": hmac.new(BENCH_SLAVE_KEY, image, hashlib.sha256).hexdigest()}
    Path(path + ".manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    peer = SlavePeer()
    flasher, _logs = _flasher(peer)
    flasher.flash_slave(path)
    assert peer.frames(cfg.CAN_ID_SLAVE_END_UPDATE) == [struct.pack(">IHH", zlib.crc32(image) & 0xFFFFFFFF, 0, 4)]


def test_the_patch_goes_into_the_minor_field_only_when_the_slave_bootloader_reads_it(tmp_path):
    path, image = _image(tmp_path, 64)
    manifest = {"version": "0.4.6", "component": "slave_application", "hardware_id": cfg.SLAVE_HARDWARE_ID, "sha256": hashlib.sha256(image).hexdigest(),
                "hmac_sha256": hmac.new(BENCH_SLAVE_KEY, image, hashlib.sha256).hexdigest()}
    Path(path + ".manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    legacy = SlavePeer(patch_extension=False)
    _flasher(legacy)[0].flash_slave(path)
    assert legacy.frames(cfg.CAN_ID_SLAVE_END_UPDATE)[0][6:8] == struct.pack(">H", 4)

    modern = SlavePeer(patch_extension=True)
    _flasher(modern)[0].flash_slave(path)
    assert modern.frames(cfg.CAN_ID_SLAVE_END_UPDATE)[0][6:8] == struct.pack(">H", (0x80 | 6) << 8 | 4)


def test_an_empty_image_is_refused_before_any_frame(tmp_path):
    path, _ = _image(tmp_path, 0)
    peer = SlavePeer()
    with pytest.raises(FlashError):
        _flasher(peer)[0].flash_slave(path)
    assert peer.sent == []


def test_an_image_larger_than_the_slave_slot_is_refused_before_any_frame(tmp_path):
    path, _ = _image(tmp_path, cfg.SLAVE_APP_MAX_SIZE + 1)
    peer = SlavePeer()
    with pytest.raises(FlashError):
        _flasher(peer)[0].flash_slave(path)
    assert peer.sent == []


def test_a_slave_still_running_its_application_is_not_flashed(tmp_path):
    path, _ = _image(tmp_path, 64)
    peer = SlavePeer(responder=0x00)
    with pytest.raises(FlashError):
        _flasher(peer)[0].flash_slave(path)
    assert not peer.frames(cfg.CAN_ID_SLAVE_START_UPDATE)


def test_a_verification_failure_reports_the_reason(tmp_path):
    path, _ = _image(tmp_path, 64)
    peer = SlavePeer(outcome="fail", reason=0x03)
    with pytest.raises(FlashError) as error:
        _flasher(peer)[0].flash_slave(path)
    assert cfg.VERIFY_FAIL_REASONS[0x03] in str(error.value)


def test_an_unknown_failure_reason_is_still_reported(tmp_path):
    path, _ = _image(tmp_path, 64)
    peer = SlavePeer(outcome="fail", reason=0x77)
    with pytest.raises(FlashError) as error:
        _flasher(peer)[0].flash_slave(path)
    assert "0x77" in str(error.value)


def test_a_generic_slave_error_stops_the_update(tmp_path):
    path, _ = _image(tmp_path, 64)
    with pytest.raises(FlashError):
        _flasher(SlavePeer(outcome="error"))[0].flash_slave(path)


def test_cancelling_stops_before_any_data_is_sent(tmp_path):
    path, _ = _image(tmp_path, 64)
    peer = SlavePeer()
    flasher, _logs = _flasher(peer, stop_flag=lambda: True)
    with pytest.raises(FlashError):
        flasher.flash_slave(path)
    assert not peer.frames(cfg.CAN_ID_SLAVE_DATA)


def test_a_bridge_that_stops_answering_is_detected_after_three_missed_progress_checks(tmp_path):
    path, _ = _image(tmp_path, 6300)
    peer = SlavePeer(answer_progress=False)
    with pytest.raises(FlashError):
        _flasher(peer)[0].flash_slave(path)
    sent = sum(len(chunk) for chunk in peer.frames(cfg.CAN_ID_SLAVE_DATA))
    assert 6144 <= sent < 6300


def test_the_slave_version_answer_is_assembled_from_two_frames():
    peer = SlavePeer(responder=0x01, patch_extension=True)
    info = _flasher(peer)[0].query_slave_version(timeout=0.5)
    assert info["responder"] == "bootloader"
    assert info["hardware_id"] == cfg.SLAVE_HARDWARE_ID
    assert (info["app_version_major"], info["app_version_minor"]) == (0, 2)
    assert info["bootloader_version"] == 1
    assert info["app_version_patch"] == 7 and info["bootloader_minor"] == 3 and info["bootloader_patch"] == 5
    assert info["accepts_patch_in_end_update"] is True


def test_a_legacy_slave_answer_has_no_patch():
    info = _flasher(SlavePeer(patch_extension=False))[0].query_slave_version(timeout=0.5)
    assert info["app_version_patch"] is None and info["accepts_patch_in_end_update"] is False


def test_a_silent_slave_gives_no_version():
    class Silent(SlavePeer):
        def send_frame(self, can_id, data):
            self.sent.append((can_id, bytes(data)))
    assert _flasher(Silent())[0].query_slave_version(timeout=0.2) is None
