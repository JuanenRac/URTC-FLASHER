# =============================================================================
# URTC Flasher - tests/test_virtual_board.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The flasher against the virtual board of the shared package, reached through its own SLCAN transport over TCP.

No adapter and no board are involved: the transport opens a ``socket://`` URL, the server behind it plays an SLCAN
adapter, and behind that a simulated board answers like the application and the bootloader. The real
``URTCFlasher`` runs unchanged: it queries the version, makes the application enter the bootloader, sends the whole
image and waits for the verification.
"""
from __future__ import annotations

import socket
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from flasher_protocol import FlashError, URTCFlasher
from flasher_transports import SLCAN
from urtc_can.virtual_board import BOOTLOADER, VirtualBoard, VirtualBoardServer


class SocketSerial:
    """Just enough of pyserial's socket:// handler for the transport: a socket with a short read timeout."""

    def __init__(self, url, baudrate=115200, timeout=None):
        host, _, port = url[len("socket://"):].partition(":")
        self.sock = socket.create_connection((host, int(port)), timeout=2)
        self.sock.settimeout(timeout)
        self.timeout = timeout

    @property
    def in_waiting(self):
        return 0

    def read(self, size=1):
        try:
            return self.sock.recv(size)
        except (socket.timeout, TimeoutError):
            return b""

    def write(self, data):
        self.sock.sendall(data)
        return len(data)

    def reset_input_buffer(self):
        self.sock.settimeout(0)
        try:
            while self.sock.recv(4096):
                pass
        except OSError:
            pass
        self.sock.settimeout(self.timeout)

    def close(self):
        self.sock.close()


SERIAL_MODULE = types.SimpleNamespace(SerialException=OSError, serial_for_url=SocketSerial)


def _firmware(tmp_path: Path, size: int = 600) -> str:
    path = tmp_path / "firmware.bin"
    path.write_bytes(bytes((i % 251) + 1 for i in range(size)))
    return str(path)


def _connect(server, serial_module=SERIAL_MODULE):
    transport = SLCAN(server.url, serial_module=serial_module, settle_seconds=0)
    transport.open_channel()
    return transport


def test_the_flasher_reads_the_version_of_the_application_over_tcp():
    with VirtualBoardServer(VirtualBoard(version=(0, 4), patch=2)) as server:
        transport = _connect(server)
        try:
            answer = URTCFlasher(transport, log=lambda message: None).query_version()
        finally:
            transport.close()
    assert answer["responder"] == "application"
    assert (answer["version_major"], answer["version_minor"], answer["version_patch"]) == (0, 4, 2)


def test_the_flasher_makes_the_application_enter_the_bootloader_and_flashes_the_image(tmp_path):
    board = VirtualBoard(version=(0, 2))
    progress: list[int] = []
    with VirtualBoardServer(board) as server:
        transport = _connect(server)
        try:
            flasher = URTCFlasher(transport, log=lambda message: None, progress_cb=progress.append)
            assert flasher.trigger_bootloader_entry() is True
            assert board.mode == BOOTLOADER
            assert flasher.flash(_firmware(tmp_path), version=(0, 3)) is True
        finally:
            transport.close()
    assert 100 in progress


def test_a_board_that_fails_its_verification_is_reported_honestly(tmp_path):
    board = VirtualBoard(version=(0, 2), bootloader=True, simulate_failure=0x03)
    with VirtualBoardServer(board) as server:
        transport = _connect(server)
        try:
            with pytest.raises(FlashError):
                URTCFlasher(transport, log=lambda message: None).flash(_firmware(tmp_path), version=(0, 3))
        finally:
            transport.close()


def test_the_real_pyserial_url_handler_reaches_the_board(tmp_path):
    serial = pytest.importorskip("serial")
    with VirtualBoardServer(VirtualBoard(version=(0, 6))) as server:
        transport = _connect(server, serial)
        try:
            answer = URTCFlasher(transport, log=lambda message: None).query_version()
        finally:
            transport.close()
    assert (answer["version_major"], answer["version_minor"]) == (0, 6)


def test_virtual_ports_are_read_from_the_environment_and_only_urls_count():
    from flasher_transports import virtual_ports

    assert virtual_ports({}) == []
    assert virtual_ports({"URTC_VIRTUAL_PORT": "socket://127.0.0.1:7777, COM3 ,rfc2217://host:2217,"}) == ["socket://127.0.0.1:7777", "rfc2217://host:2217"]


def test_the_deck_lists_the_virtual_board_among_the_ports(monkeypatch):
    qt_flasher = pytest.importorskip("qt_flasher")
    monkeypatch.setenv("URTC_VIRTUAL_PORT", "socket://127.0.0.1:7777")
    bridge = qt_flasher.FlasherQtBridge()
    bridge._log = lambda message: None
    bridge.scanPorts()
    assert "socket://127.0.0.1:7777" in bridge.ports
    bridge.selectPort("socket://127.0.0.1:7777")
    assert bridge.selectedPort == "socket://127.0.0.1:7777"
