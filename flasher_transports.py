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
    is_serial_url,
    list_socketcan_interfaces,
)
from urtc_can.transports import SLCAN as _SharedSLCAN
from urtc_can.transports import SocketCAN as _SharedSocketCAN


VIRTUAL_PORT_ENV = "URTC_VIRTUAL_PORT"
PYTHON_CAN_PREFIX = "python-can:"
PYTHON_CAN_ENV = "URTC_PYTHON_CAN"
# Adapters python-can is asked about on its own (the others it knows would load drivers the person never asked for); SocketCAN has its own entry.
PYTHON_CAN_DETECT = ("pcan", "kvaser", "gs_usb")


def is_python_can_port(port):
    """True for an entry of the port list that stands for a python-can adapter (``python-can:<interface>:<channel>``)."""
    return str(port or "").startswith(PYTHON_CAN_PREFIX)


def python_can_spec(port):
    """The ``<interface>:<channel>`` part of such an entry."""
    return str(port)[len(PYTHON_CAN_PREFIX):]


def list_python_can_adapters(can_module=None, environ=None, find_spec=None):
    """The python-can adapters to offer in the window, as ``python-can:<interface>:<channel>`` entries.

    Those named in URTC_PYTHON_CAN (comma separated ``<interface>:<channel>``) come first, then those python-can finds
    for ``PYTHON_CAN_DETECT``. Nothing is offered, and nothing is imported, when python-can is not installed; an adapter that
    cannot be probed is left out and never raises.
    """
    import os

    entries = []
    for item in (os.environ if environ is None else environ).get(PYTHON_CAN_ENV, "").split(","):
        item = item.strip()
        interface, separator, channel = item.partition(":")
        if interface and separator and channel and PYTHON_CAN_PREFIX + item not in entries:
            entries.append(PYTHON_CAN_PREFIX + item)
    module = can_module
    if module is None:
        import importlib.util

        if (find_spec or importlib.util.find_spec)("can") is None:
            return entries
        try:
            import can as module
        except Exception:
            return entries
    try:
        configs = module.detect_available_configs(interfaces=list(PYTHON_CAN_DETECT))
    except Exception:
        return entries
    for config in configs or []:
        try:
            entry = f"{PYTHON_CAN_PREFIX}{config['interface']}:{config['channel']}"
        except (KeyError, TypeError):
            continue
        if entry not in entries:
            entries.append(entry)
    return entries


def virtual_ports(environ=None):
    """The serial URLs named in URTC_VIRTUAL_PORT (comma separated), for example socket://127.0.0.1:7777: a virtual board
    (python -m urtc_can.virtual_board) to try the program with no adapter and no hardware. Anything that is not a URL is ignored."""
    import os

    text = (os.environ if environ is None else environ).get(VIRTUAL_PORT_ENV, "")
    return [item.strip() for item in text.split(",") if is_serial_url(item.strip())]


class SLCAN(_SharedSLCAN):
    """The shared SLCAN transport, opening the serial port through this module's ``serial``."""

    def __init__(self, port, baud=115200, log=None, serial_module=None, settle_seconds=0.2):
        super().__init__(port, baud, log, serial_module=serial_module or serial, settle_seconds=settle_seconds)


class SocketCAN(_SharedSocketCAN):
    """The shared SocketCAN transport with its warnings translated into the window's language."""

    def __init__(self, interface, log=None, socket_module=None):
        super().__init__(interface, log=log, socket_module=socket_module, translate=_)
