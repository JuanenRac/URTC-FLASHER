# =============================================================================
# URTC Flasher - CAN transports: SLCAN (serial), SocketCAN (Linux), python-can
# and MockCAN (in-memory simulator for testing this tool's own logic)
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The transports themselves live in urtc_can/transports.py, a checked copy of the module the URTC tools share
(see urtc_can/urtc_common.lock.json), so a fix made there applies to every tool. This module is the one place
this program imports them from; the only thing it adds is that SocketCAN says its warnings in the language of
the window.

SLCAN FIRMWARE NOTE: a CANable Pro v2 ships by default with "candleLight" firmware, which presents itself over
USB using the gs_usb protocol (what Linux's SocketCAN gs_usb driver expects) - NOT a serial port, and NOT what
SLCAN here speaks. For this tool to see the adapter as a COM port at all, it needs to be running
SLCAN-compatible firmware instead. See this project's README for links to the firmware and the flashing steps:
this is a one-time setup on the adapter itself, separate from flashing the URTC board.
"""
import time  # noqa: F401  (tests slow the transports down or speed them up through this name)

try:
    import serial
except ImportError:
    serial = None  # SLCAN's constructor is what needs it: SocketCAN and MockCAN work without

from flasher_config import _
from urtc_can.transports import (  # noqa: F401
    MESSAGES,
    CanTransport,
    MockCAN,
    PythonCAN,
    PythonCANError,
    SLCANError,
    SocketCANError,
    TransportError,
    as_frames,
    detect_bitrate_listen_only,
    list_socketcan_interfaces,
)
from urtc_can.transports import SLCAN as _SharedSLCAN
from urtc_can.transports import SocketCAN as _SharedSocketCAN


class SLCAN(_SharedSLCAN):
    """The shared SLCAN transport, opening the serial port through this module's ``serial``."""

    def __init__(self, port, baud=115200, log=None, serial_module=None, settle_seconds=0.2):
        super().__init__(port, baud, log, serial_module=serial_module or serial, settle_seconds=settle_seconds)


class SocketCAN(_SharedSocketCAN):
    """The shared SocketCAN transport with its warnings translated into the window's language."""

    def __init__(self, interface, log=None, socket_module=None):
        super().__init__(interface, log=log, socket_module=socket_module, translate=_)
