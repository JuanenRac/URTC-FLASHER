# =============================================================================
# URTC Flasher - tests/test_python_can_transport.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The optional python-can transport, against a stand-in `can` module (no adapter needed)."""
from __future__ import annotations

import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from flasher_transports import PythonCAN, PythonCANError, is_python_can_port, list_python_can_adapters, python_can_spec


class _Message:
    def __init__(self, arbitration_id=0, data=b"", is_extended_id=False, is_remote_frame=False, is_error_frame=False):
        self.arbitration_id = arbitration_id
        self.data = data
        self.is_extended_id = is_extended_id
        self.is_remote_frame = is_remote_frame
        self.is_error_frame = is_error_frame


class _Bus:
    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.sent = []
        self.incoming = []
        self.closed = False
        _Bus.instances.append(self)

    def send(self, message):
        self.sent.append(message)

    def recv(self, timeout):
        return self.incoming.pop(0) if self.incoming else None

    def shutdown(self):
        self.closed = True


@pytest.fixture
def fake_can(monkeypatch):
    module = types.ModuleType("can")
    module.Bus = _Bus
    module.Message = _Message
    monkeypatch.setitem(sys.modules, "can", module)
    _Bus.instances.clear()
    return module


def test_the_channel_is_opened_at_500k_with_the_named_interface(fake_can):
    transport = PythonCAN("pcan:PCAN_USBBUS1")
    transport.open_channel()
    assert _Bus.instances[0].kwargs == {"interface": "pcan", "channel": "PCAN_USBBUS1", "bitrate": 500_000}


def test_a_numeric_channel_is_passed_as_a_number(fake_can):
    PythonCAN("kvaser:0").open_channel()
    assert _Bus.instances[0].kwargs["channel"] == 0


def test_frames_go_out_as_standard_11_bit_ids_and_come_back_as_tuples(fake_can):
    transport = PythonCAN("gs_usb:0")
    transport.open_channel()
    transport.send_frame(0x7F1, b"\x01\x02")
    sent = _Bus.instances[0].sent[0]
    assert (sent.arbitration_id, sent.data, sent.is_extended_id) == (0x7F1, b"\x01\x02", False)
    _Bus.instances[0].incoming = [_Message(0x7F6, b"\x01\xff")]
    assert transport.read_frame() == (0x7F6, b"\x01\xff")
    assert transport.read_frame() is None


def test_extended_remote_and_error_frames_are_ignored(fake_can):
    transport = PythonCAN("gs_usb:0")
    transport.open_channel()
    _Bus.instances[0].incoming = [_Message(1, b"", is_extended_id=True), _Message(2, b"", is_remote_frame=True), _Message(3, b"", is_error_frame=True)]
    assert [transport.read_frame() for _ in range(3)] == [None, None, None]


def test_an_id_outside_11_bits_is_refused(fake_can):
    transport = PythonCAN("gs_usb:0")
    transport.open_channel()
    with pytest.raises(PythonCANError):
        transport.send_frame(0x800, b"")


def test_close_shuts_the_bus_down(fake_can):
    transport = PythonCAN("gs_usb:0")
    transport.open_channel()
    transport.close()
    assert _Bus.instances[0].closed


def test_a_bad_spec_and_a_missing_package_are_explained(monkeypatch, fake_can):
    with pytest.raises(PythonCANError, match="<interface>:<channel>"):
        PythonCAN("pcan").open_channel()
    monkeypatch.setitem(sys.modules, "can", None)  # import can -> ImportError
    with pytest.raises(PythonCANError, match="python-can is not installed"):
        PythonCAN("pcan:1").open_channel()


class _Detecting:
    def __init__(self, configs=None, error=None):
        self.configs, self.error, self.asked = configs, error, None

    def detect_available_configs(self, interfaces=None):
        self.asked = interfaces
        if self.error:
            raise self.error
        return self.configs


def test_the_window_lists_the_adapters_python_can_finds_and_those_named_in_the_environment():
    module = _Detecting([{"interface": "pcan", "channel": "PCAN_USBBUS1"}, {"interface": "gs_usb", "channel": 0}, {"bad": 1}])
    ports = list_python_can_adapters(module, {"URTC_PYTHON_CAN": "kvaser:0, pcan:PCAN_USBBUS1, nonsense, :x"})
    assert ports == ["python-can:kvaser:0", "python-can:pcan:PCAN_USBBUS1", "python-can:gs_usb:0"]
    assert module.asked == ["pcan", "kvaser", "gs_usb"]  # only the adapters that are asked for, no other driver is loaded
    assert all(is_python_can_port(port) for port in ports) and not is_python_can_port("COM3")
    assert python_can_spec(ports[0]) == "kvaser:0"


def test_nothing_is_offered_and_nothing_fails_without_python_can_or_when_probing_fails():
    assert list_python_can_adapters(None, {}, find_spec=lambda name: None) == []
    assert list_python_can_adapters(None, {"URTC_PYTHON_CAN": "pcan:1"}, find_spec=lambda name: None) == ["python-can:pcan:1"]
    assert list_python_can_adapters(_Detecting(error=OSError("driver missing")), {}) == []
    assert list_python_can_adapters(_Detecting(configs=None), {}) == []
