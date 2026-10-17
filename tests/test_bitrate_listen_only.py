# =============================================================================
# URTC Flasher - tests/test_bitrate_listen_only.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Bitrate auto-detection must never transmit: the SLCAN channel is opened
with "L" (listen-only) and a bitrate is found only by hearing a frame."""
from __future__ import annotations

import types

import flasher_transports
from flasher_transports import SLCAN, detect_bitrate_listen_only


class FakeSerial:
    def __init__(self, *a, **k):
        self.written = []

    def write(self, data):
        self.written.append(data.decode("ascii"))

    def reset_input_buffer(self):
        pass

    def close(self):
        pass


def _slcan(monkeypatch):
    fake_serial_module = types.SimpleNamespace(Serial=FakeSerial)
    monkeypatch.setattr(flasher_transports, "serial", fake_serial_module, raising=False)
    monkeypatch.setattr(flasher_transports.time, "sleep", lambda s: None)
    return SLCAN("COMX")


def test_listen_only_opens_with_L_and_never_O(monkeypatch):
    can = _slcan(monkeypatch)
    can.open_channel("6", listen_only=True)
    assert "L\r" in can.ser.written
    assert "O\r" not in can.ser.written


def test_normal_open_still_uses_O(monkeypatch):
    can = _slcan(monkeypatch)
    can.open_channel("6")
    assert "O\r" in can.ser.written
    assert "L\r" not in can.ser.written


class ListenTrial:
    def __init__(self, hears, sent):
        self.hears = hears
        self.sent = sent
        self.closed = False

    def read_frame(self, timeout=0.05):
        return (0x7F0, b"\x00") if self.hears else None

    def send_frame(self, can_id, data):
        self.sent.append(can_id)

    def close(self):
        self.closed = True


def test_detection_finds_the_bitrate_with_traffic_and_sends_nothing():
    sent, tried, trials = [], [], []

    def open_trial(code):
        trial = ListenTrial(hears=(code == "5"), sent=sent)
        trials.append(trial)
        return trial

    found = detect_bitrate_listen_only(
        open_trial, [("1 Mbit/s", "8"), ("500 kbit/s", "6"), ("250 kbit/s", "5"), ("125 kbit/s", "4")],
        listen_seconds=0.01, on_try=tried.append,
    )
    assert found == "250 kbit/s"
    assert tried == ["1 Mbit/s", "500 kbit/s", "250 kbit/s"]
    assert sent == []
    assert all(t.closed for t in trials)


def test_silent_bus_gives_no_answer_instead_of_guessing():
    found = detect_bitrate_listen_only(
        lambda code: ListenTrial(False, []), [("500 kbit/s", "6"), ("250 kbit/s", "5")], listen_seconds=0.01,
    )
    assert found is None
