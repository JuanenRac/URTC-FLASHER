#!/usr/bin/env python3
"""
URTC Flasher - cross-platform firmware update tool for the URTC board
Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>

Licensed under the GNU General Public License v3.0 or later (GPL-3.0-or-later), matching the
URTC firmware itself. See LICENSE in the repository root.

Flashes a compiled URTC application .bin file to a board over CAN bus.
Implements the exact CAN bootloader protocol documented in CANBUS.TXT:
HardwareID check, HMAC-SHA256 signing, the golden-image backup-slot update
flow, and live progress via the bootloader's heartbeat messages.

Two transports are supported, both talking the same protocol:

  1. Serial / SLCAN - works on Windows, Linux, and macOS. Needs a USB-CAN
     adapter running SLCAN firmware (e.g. a CANable Pro v2 flashed with a
     "candleLight"->slcan alternative firmware, or any other adapter
     presenting an SLCAN-compatible virtual COM port / /dev/tty* device).

  2. SocketCAN - Linux only, not shown on other platforms. Talks directly
     to a kernel can0/slcan0 network interface via a raw AF_CAN socket -
     no serial layer, no firmware reflash needed on adapters that already
     support Linux's native gs_usb driver (most CANable-family boards ship
     this way by default). The interface itself must already be brought up
     at 500 kbit/s at the OS level first - see the README's Linux section.

See this file's own "SLCAN FIRMWARE NOTE" and "SOCKETCAN NOTE" comments
(in flasher_transports.py) and the README's tool section, for setup
details on each path.

This is the entry point only - CLI argument handling and the start of the
Qt Quick deck. Everything else lives in its own module:
flasher_config.py (config/language/constants), flasher_transports.py
(SLCAN/SocketCAN/MockCAN), flasher_swd_tools.py (CubeProgrammer/pyOCD),
flasher_validation.py (firmware file validation), flasher_protocol.py
(the CAN OTA state machine), and qt_flasher.py with assets/qml/FlasherDeck.qml
(the window).
"""

import sys
import argparse

try:
    import serial
    import serial.tools.list_ports  # noqa: F401 - checks that the port listing is available too
    HAVE_SERIAL = True
except ImportError:
    HAVE_SERIAL = False

# SocketCAN (socket.AF_CAN) is only ever present in Python's stdlib on
# Linux - it doesn't exist as an attribute on Windows/macOS builds, so this
# check alone is enough to gate the whole feature without an explicit
# sys.platform test too. No extra pip package needed for the raw-socket
# approach used here - just the standard library.
import socket
HAVE_SOCKETCAN = hasattr(socket, "AF_CAN")

if not HAVE_SERIAL and not HAVE_SOCKETCAN:
    print("This tool needs pyserial for serial/SLCAN support. Install it with:")
    print("    pip install pyserial")
    print("(SocketCAN support, Linux only, would still work without pyserial,")
    print(" but no transport at all is available on this system as-is.)")
    # Raising rather than sys.exit(1) here - the latter would kill the
    # entire Python process on import, even for a programmatic importer
    # (e.g. a test script doing `import urtc_flasher` to inspect
    # constants) that has no way to catch and handle a SystemExit at
    # import time the way it could catch this.
    raise RuntimeError("No CAN transport available: neither pyserial nor SocketCAN is present")
elif not HAVE_SERIAL:
    print("NOTE: pyserial isn't installed, so Serial/SLCAN mode is unavailable.")
    print("SocketCAN mode will still work. To also enable Serial/SLCAN:")
    print("    pip install pyserial")

from flasher_integrity import preflight_image
from flasher_config import _CONFIG_LOADED, _load_config_overrides
from flasher_transports import SLCAN, SLCANError, SocketCAN, SocketCANError, PythonCAN, PythonCANError, MockCAN
from flasher_protocol import URTCFlasher, FlashError
from flasher_validation import validate_firmware_file

def _cli_log(msg):
    print(msg, flush=True)


def run_cli(argv):
    """Headless CAN OTA update, no GUI involved - for CI pipelines,
    test benches, or production-line scripting where there's no display.
    Only covers the CAN update path (section 1-3 of the GUI); the SWD/JTAG
    full-chip path is deliberately GUI-only for now, given how much more
    is at stake if a scripted run gets a wrong file/target combination
    wrong with nobody watching.

    Exit codes: 0 success, 1 protocol/connection error, 2 bad arguments
    or invalid firmware file, 130 cancelled (Ctrl+C).
    """
    parser = argparse.ArgumentParser(
        prog="urtc_flasher.py --cli",
        description="Headless URTC CAN OTA firmware update (no GUI).",
    )
    parser.add_argument("--transport", choices=["serial", "socketcan", "python-can", "mock"], default="serial",
                         help="Serial/SLCAN (default, all platforms), SocketCAN (Linux only), "
                              "python-can (PCAN, Kvaser, gs_usb ...; needs the python-can package), "
                              "or mock (simulated in-memory bootloader, for testing this tool's "
                              "own logic - not for use against a real board)")
    parser.add_argument("--port",
                         help="Serial port (e.g. COM3 or /dev/ttyACM0) for --transport serial, "
                              "interface name (e.g. can0) for --transport socketcan, "
                              "or <interface>:<channel> (e.g. pcan:PCAN_USBBUS1) for --transport python-can. "
                              "Not needed for --transport mock.")
    parser.add_argument("--file", required=True, help="Firmware .bin file to flash")
    parser.add_argument("--no-trigger", action="store_true",
                         help="Skip the 0x7F0 bootloader-entry trigger - use this if the board "
                              "is already sitting in the bootloader (fresh JTAG flash, or no "
                              "valid application currently present)")
    parser.add_argument("--force", action="store_true",
                         help="Flash even if the file fails the plausibility check")
    parser.add_argument("--version", default=None, metavar="MAJOR.MINOR[.PATCH]",
                        help="Version of the firmware file, for an image that has no .manifest.json and no version in its name (never guessed); the optional patch is sent only to a bootloader that reads it")
    parser.add_argument("--allow-downgrade", action="store_true",
                         help="Send CAN_ID_AUTHORIZE_DOWNGRADE (0x7FD) before ending the update, "
                              "bypassing the bootloader's own anti-rollback check for this attempt "
                              "only - use to deliberately revert to an older, still-signed release. "
                              "Off by default.")
    parser.add_argument("--mock-fail", type=lambda s: int(s, 0), default=None, metavar="REASON",
                         help="With --transport mock: simulate a verify failure with this "
                              "VERIFY_FAIL_REASON_* value (e.g. 0x03 for HMAC mismatch) instead "
                              "of a successful update. Ignored for real transports.")
    args = parser.parse_args(argv)

    if args.transport != "mock" and not args.port:
        _cli_log("ERROR: --port is required for --transport serial/socketcan/python-can.")
        return 2

    if _CONFIG_LOADED:
        _load_config_overrides(_cli_log)  # re-run just to emit its own log line - values don't change

    if args.transport == "socketcan" and not HAVE_SOCKETCAN:
        _cli_log("ERROR: --transport socketcan requires Linux with socket.AF_CAN support.")
        return 2
    if args.transport == "serial" and not HAVE_SERIAL:
        _cli_log("ERROR: --transport serial requires pyserial (pip install pyserial).")
        return 2

    is_valid, reason, size = validate_firmware_file(args.file)
    _cli_log(f"Firmware: {args.file} ({size} bytes) - {reason}")
    if not is_valid and not args.force:
        _cli_log("Refusing to flash a file that fails the plausibility check "
                  "(pass --force to override).")
        return 2

    # a digest published next to the image (<image>.sha256, or in its manifest) must match it, as in the two windows
    check = preflight_image(args.file)
    if check.blocked:
        _cli_log("ERROR: the image was refused: " + "; ".join(check.reasons))
        return 2
    _cli_log(("Image digest verified: " if check.verified else "Image digest (no published digest to compare): ") + check.sha256)
    _cli_log({"signed": "Release signature verified.", "unsigned": "No release signature (image of a bench pre-release)."}.get(check.release_signature, ""))

    transport = None
    try:
        if args.transport == "serial":
            transport = SLCAN(args.port, log=_cli_log)
        elif args.transport == "socketcan":
            transport = SocketCAN(args.port, log=_cli_log)
        elif args.transport == "python-can":
            transport = PythonCAN(args.port, log=_cli_log)
        else:
            transport = MockCAN(simulate_failure=args.mock_fail, log=_cli_log)
            _cli_log("Using the mock transport - nothing here is touching real hardware.")
        transport.open_channel()
        _cli_log(f"Connected via {args.transport}" + (f" on {args.port}." if args.port else "."))

        flasher = URTCFlasher(transport, log=_cli_log, progress_cb=lambda pct: None)
        if not args.no_trigger:
            flasher.report_version_change(args.file, "master", args.version)
            flasher.trigger_bootloader_entry()
        flasher.flash(args.file, allow_downgrade=args.allow_downgrade, version=args.version)
        _cli_log("SUCCESS: firmware update complete.")
        return 0
    except KeyboardInterrupt:
        _cli_log("Cancelled.")
        return 130
    except (FlashError, SLCANError, SocketCANError, PythonCANError) as e:
        _cli_log(f"FAILED: {e}")
        return 1
    except Exception as e:
        _cli_log(f"UNEXPECTED ERROR: {e}")
        return 1
    finally:
        if transport is not None:
            try:
                transport.close()
            except Exception:
                pass



def run_history(argv):
    """``urtc_flasher.py --history FOLDER [--json]``: the evidence records (urtc-evidence/1) of a folder, newest first, each one checked.
    Opens no bus. Exit codes: 0 every record is valid, 1 one of them fails its check (edited after it was written, not JSON ...), 2 the folder does not exist."""
    from urtc_can import evidence_history

    parser = argparse.ArgumentParser(prog="urtc_flasher.py --history", description="List the evidence records of a folder, checking each one.")
    parser.add_argument("folder", help="the folder with the evidence files (the reports of the updates are written next to the report)")
    parser.add_argument("--json", action="store_true", help="print the list with its summary as one JSON document")
    args = parser.parse_args(argv)
    try:
        entries = evidence_history.select(evidence_history.load_folder(args.folder))
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(evidence_history.to_json(entries).rstrip("\n") if args.json else evidence_history.to_text(entries))
    return 1 if any(not entry.valid for entry in entries) else 0


def main():
    if "--history" in sys.argv:
        return run_history([a for a in sys.argv[1:] if a != "--history"])
    if "--cli" in sys.argv and "--qtquick" in sys.argv:
        print("ERROR: --cli and --qtquick are mutually exclusive modes.", file=sys.stderr)
        return 2
    if "--cli" in sys.argv:
        argv = [a for a in sys.argv[1:] if a != "--cli"]
        return run_cli(argv)
    # The Qt Quick deck is the only window; --qtquick is still accepted so older shortcuts keep working.
    try:
        from qt_flasher import run_qtquick
    except ImportError as exc:
        print(
            "ERROR: the window needs PySide6 (Qt Quick). "
            "Install this repository's requirements.txt first, or use --cli for the headless update. "
            f"Details: {exc}",
            file=sys.stderr,
        )
        return 2
    return run_qtquick()


if __name__ == "__main__":
    raise SystemExit(main())
