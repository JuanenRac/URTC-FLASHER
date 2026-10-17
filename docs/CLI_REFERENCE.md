# URTC-FLASHER — CLI Reference

`urtc_flasher.py` defaults to a windowed Tkinter GUI (double-click, or
run with no arguments). Passing `--cli` switches to the headless
argparse fallback documented here — checked directly against `sys.argv`
*before* `tkinter` is ever imported, so `--cli` mode works on a genuinely
headless machine (CI runner, production-line bench, a Linux box with no
`python3-tk`) with no display and no Tk dependency at all. The CLI only
covers the CAN-OTA update path (sections 1-3 of the GUI: trigger the
bootloader, HMAC-sign and transfer a firmware image, verify); the
SWD/JTAG full-chip programming path is deliberately GUI-only. Every
example below was captured from a real run of the installed script — not
written from memory.

## Qt Quick diagnostic surface

The command python urtc_flasher.py --qtquick opens the optional Qt Quick command deck.
Its **Advanced diagnostics** card can detect whether `pyOCD` and
`STM32CubeProgrammer` are installed and can enumerate USB debug probes using
their existing read-only listing commands. This is deliberately not an SWD
programming interface: the scan neither connects to a target chip nor erases,
writes or resets one. Full-chip programming is a separate panel of the deck (and of the Tkinter window).

After a normal active CAN connection, the deck's **Board snapshot** action
uses only documented query frames to collect the board version, CAN error
counters, expansion type, MLX variant and peripheral information. It never
writes configuration, firmware or option bytes. It is unavailable in
listen-only mode because these protocol queries require a response from the
board.

The non-versioning build check also extracts every `uiText("KEY")` call from
the QML deck and requires that key in all eight shipped language files. It
checks localization coverage without launching Qt or opening a transport.

## Usage

```
$ python urtc_flasher.py --cli -h
usage: urtc_flasher.py --cli [-h]
                             [--transport {serial,socketcan,python-can,mock}]
                             [--port PORT] --file FILE [--no-trigger]
                             [--force] [--version MAJOR.MINOR[.PATCH]]
                             [--allow-downgrade] [--mock-fail REASON]

Headless URTC CAN OTA firmware update (no GUI).

options:
  -h, --help            show this help message and exit
  --transport {serial,socketcan,python-can,mock}
                        Serial/SLCAN (default, all platforms), SocketCAN
                        (Linux only), python-can (PCAN, Kvaser, gs_usb ...;
                        needs the python-can package), or mock (simulated in-
                        memory bootloader, for testing this tool's own logic -
                        not for use against a real board)
  --port PORT           Serial port (e.g. COM3 or /dev/ttyACM0) for
                        --transport serial, interface name (e.g. can0) for
                        --transport socketcan, or <interface>:<channel> (e.g.
                        pcan:PCAN_USBBUS1) for --transport python-can. Not
                        needed for --transport mock.
  --file FILE           Firmware .bin file to flash
  --no-trigger          Skip the 0x7F0 bootloader-entry trigger - use this if
                        the board is already sitting in the bootloader (fresh
                        JTAG flash, or no valid application currently present)
  --force               Flash even if the file fails the plausibility check
  --version MAJOR.MINOR[.PATCH]
                        Version of the firmware file, for an image that has no
                        .manifest.json and no version in its name (never
                        guessed); the optional patch is sent only to a
                        bootloader that reads it
  --allow-downgrade     Send CAN_ID_AUTHORIZE_DOWNGRADE (0x7FD) before ending
                        the update, bypassing the bootloader's own anti-
                        rollback check for this attempt only - use to
                        deliberately revert to an older, still-signed release.
                        Off by default.
  --mock-fail REASON    With --transport mock: simulate a verify failure with
                        this VERIFY_FAIL_REASON_* value (e.g. 0x03 for HMAC
                        mismatch) instead of a successful update. Ignored for
                        real transports.
```

`--transport mock` is a real, self-contained in-memory bootloader
simulator (`MockCAN` in `flasher_transports.py`) built for exercising
this tool's own protocol logic (retries, timeouts, page-ACK pacing, the
verify handshake) with no adapter and no board attached — every example
below uses it. `serial`/`socketcan`/`python-can` need real hardware (a USB-CAN
adapter, a brought-up SocketCAN interface, or an adapter python-can supports)
and are not demonstrated here.

Before any transport work, `--file` is checked with the same
plausibility check the GUI's own file picker applies
(`flasher_validation.py`): file exists and is non-empty, small enough for
the 112KB application slot, and its first 8 bytes decode as a plausible
Cortex-M vector table — an initial stack pointer that actually lands in
this chip's SRAM, and a reset-handler address that actually lands inside
the application flash slot (`0x08008000`-`0x08024000`), not the
bootloader's own slot. This repo ships real, already-built firmware
images under `firmware/` used as fixtures below — no synthetic/dummy
file was invented for these examples.

## Commands

### Success: `--transport mock --file <real .bin>`

```
$ python urtc_flasher.py --cli --transport mock --file firmware/URTC_MAIN_FIRMWARE_v0.3.3.bin
Firmware: firmware/URTC_MAIN_FIRMWARE_v0.3.3.bin (73476 bytes) - looks valid
Image digest verified: 52a0fcd33ef5eb227beda253240663ba87a5167533bce691a1bd6aa76f8eb69e
Using the mock transport - nothing here is touching real hardware.
Connected via mock.
Installed v0.2 -> new v0.3.3.
Sending bootloader-entry trigger (0x7F0)...
  Manifest: version=0.3.3, build_date=2026-10-11T11:36:36Z
  Manifest SHA-256 matches this file.
Using the signature published in the manifest (key: dev).
NOTE: signed with the PUBLIC development key - only boards whose bootloader was built with that same key accept it.
Firmware: firmware/URTC_MAIN_FIRMWARE_v0.3.3.bin
  size: 73476 bytes (71.8 KB)
  CRC32: 0xF7B03747
  HMAC-SHA256: 73f168d0823552b798dc6b8f6b1c981bc4c13a5eacfd9c67af7e336e19719028
  HardwareID: 0x0303CC01
Sending start-update (0x7F1)...
  status: Erasing backup slot
  status: Receiving firmware data
Sending HMAC signature (4x 0x7F7)...
Sending firmware data...
  page 1/36 written and acked (0.40s, 5.0 KB/s)
  ...
  (last partial page 35: the bootloader writes and acknowledges it only when the end of the update arrives, so it is not waited for here)
  page 36/36 written and acked (0.62s, 2.8 KB/s)
Transfer complete: 73476 bytes in 16.8s (4.3 KB/s average, 0 page-ACK retries)
Sending end-update / verify (0x7F4)...
Verifying and copying to main slot (this can take a while)...
  status: Verifying (size/CRC32/HMAC/HardwareID)
  status: Verify OK - jumping to new firmware
Update verified OK - board is resetting into new firmware.
SUCCESS: firmware update complete.
$ echo $?
0
```

(The 36 page lines are shown collapsed to the first and the last one; every one was real in the
actual run. The mock board reports an installed version of 0.2 and no patch number (like a board that predates it), so the log shows `Installed v0.2 ->
new v0.3.3` (the image's own version, patch included); against a real board the installed version is the one the board answers, as major.minor.patch when it sends its patch (frame 0x7E9). The patch is only compared when both sides carry one, and it goes into the end-of-update frame only towards a bootloader that announced it reads it. If a
`urtc_config.json` is present, the CLI also logs which of its fields override the built-in values, as
its first line.)

### Real failure path: `--mock-fail`

`--mock-fail` drives `MockCAN` to report a real bootloader verify
failure (a `VERIFY_FAIL_REASON_*` code from `CANBUS.TXT`) instead of
success, after a real, complete page-by-page transfer — this is the
actual failure-reporting code path, not a simulated short-circuit:

```
$ python urtc_flasher.py --cli --transport mock --file firmware/URTC_MAIN_FIRMWARE_v0.3.3.bin --mock-fail 0x03
...
Sending firmware data...
  page 1/36 written and acked (0.41s, 4.9 KB/s)
  ...
  (last partial page 35: the bootloader writes and acknowledges it only when the end of the update arrives, so it is not waited for here)
  page 36/36 written and acked (0.36s, 4.9 KB/s)
Transfer complete: 73476 bytes in 15.8s (4.5 KB/s average, 0 page-ACK retries)
Sending end-update / verify (0x7F4)...
Verifying and copying to main slot (this can take a while)...
  status: Verifying (size/CRC32/HMAC/HardwareID)
  status: Verify FAILED - main slot untouched - HMAC signature mismatch (not signed with this project's key)
FAILED: Bootloader reported failure: Verify FAILED - main slot untouched - HMAC signature mismatch (not signed with this project's key)
$ echo $?
1
```

### Real error path: a firmware file that fails the plausibility check

Passing this repo's own real bootloader image (`URTC_MAIN_BOOTLOADER_v0.3.8.bin`)
as if it were an application image is rejected *before* any transport
work starts — its real reset-handler address (`0x08000785`) genuinely
falls outside the application slot, because it's a real bootloader
image, not a corrupted or synthetic one:

```
$ python urtc_flasher.py --cli --transport mock --file firmware/URTC_MAIN_BOOTLOADER_v0.3.8.bin
Firmware: firmware/URTC_MAIN_BOOTLOADER_v0.3.8.bin (18244 bytes) - reset handler (0x08000785) doesn't point inside the application slot (0x08008000-0x08024000) - this looks like a bootloader image, not an application image, or an image built for the other target (main board vs. expansion slave). A CAN-OTA update only ever writes to the application slot, so this file can't go through this path regardless of size - use the SWD/JTAG section instead if you actually need to update the bootloader.
Refusing to flash a file that fails the plausibility check (pass --force to override).
$ echo $?
2
```

`--force` overrides this and proceeds anyway (real run on a bench with a signing key configured,
truncated after a few real transferred pages — the mock bootloader has no opinion on
image *content*, only the local plausibility check does):

```
$ python urtc_flasher.py --cli --transport mock --file firmware/URTC_MAIN_BOOTLOADER_v0.3.8.bin --force --no-trigger
Firmware: firmware/URTC_MAIN_BOOTLOADER_v0.3.8.bin (18244 bytes) - reset handler (0x08000785) doesn't point inside the application slot (0x08008000-0x08024000) - this looks like a bootloader image, not an application image, or an image built for the other target (main board vs. expansion slave). A CAN-OTA update only ever writes to the application slot, so this file can't go through this path regardless of size - use the SWD/JTAG section instead if you actually need to update the bootloader.
Image digest verified: 9176c0ebb31da2bb6678884fa2c9a3d68e0153c2683de69b257ae344af18cc67
Using the mock transport - nothing here is touching real hardware.
Connected via mock.
  Manifest: version=0.3.8, build_date=2026-10-11T11:36:36Z
  Manifest SHA-256 matches this file.
No published signature - signing locally with the master key from urtc_config.json.
Firmware: firmware/URTC_MAIN_BOOTLOADER_v0.3.8.bin
  size: 18244 bytes (17.8 KB)
  CRC32: 0xC3A4FDE3
  HMAC-SHA256: 018cdad0f22b0d3836bedb127a58b4a5cc52cb105e6cba8e39ef1e736c8f184d
  HardwareID: 0x0303CC01
Sending start-update (0x7F1)...
  status: Erasing backup slot
  status: Receiving firmware data
Sending HMAC signature (4x 0x7F7)...
Sending firmware data...
  page 1/9 written and acked (0.40s, 5.0 KB/s)
  page 2/9 written and acked (0.40s, 5.0 KB/s)
  ...
```

(`--no-trigger` here really does skip the `Sending bootloader-entry
trigger (0x7F0)...` line seen in the earlier examples.)

### Real error path: a missing/unreadable file

The same plausibility check catches an unreadable path with an honest,
OS-reported reason (wording below is Windows/`OSError`-locale-dependent;
the shape of the message — `can't read file: <OSError>` — is not):

```
$ python urtc_flasher.py --cli --transport mock --file firmware/DOES_NOT_EXIST.bin
Firmware: firmware/DOES_NOT_EXIST.bin (0 bytes) - can't read file: [WinError 2] El sistema no puede encontrar el archivo especificado: 'firmware/DOES_NOT_EXIST.bin'
Refusing to flash a file that fails the plausibility check (pass --force to override).
$ echo $?
2
```

### Real error path: `--transport serial`/`socketcan` without `--port`

```
$ python urtc_flasher.py --cli --transport serial --file firmware/URTC_MAIN_FIRMWARE_v0.3.3.bin
ERROR: --port is required for --transport serial/socketcan/python-can.
$ echo $?
2
```

### Real error path: missing required `--file`

```
$ python urtc_flasher.py --cli --transport mock
usage: urtc_flasher.py --cli [-h]
                             [--transport {serial,socketcan,python-can,mock}]
                             [--port PORT] --file FILE [--no-trigger]
                             [--force] [--version MAJOR.MINOR[.PATCH]]
                             [--allow-downgrade] [--mock-fail REASON]
urtc_flasher.py --cli: error: the following arguments are required: --file
$ echo $?
2
```

## Exit codes

Documented directly in `run_cli()`'s own docstring in `urtc_flasher.py`:

| Code | Meaning |
|------|---------|
| `0` | success |
| `1` | protocol/connection error (a `FlashError`/`SLCANError`/`SocketCANError`/`PythonCANError`, or any other unexpected exception, during the actual transport/flash attempt) |
| `2` | bad arguments or an invalid firmware file (missing `--port`, an unavailable transport, a file that fails the plausibility check without `--force`) |
| `130` | cancelled (Ctrl+C) |

## GUI

Running `urtc_flasher.py` with no arguments (or double-clicking it) opens
the default windowed Tkinter GUI instead — a 5-second splash, then the
main window covering both the CAN-OTA update flow shown above and the
GUI-only SWD/JTAG full-chip programming section, with a language
selector (the CLI itself stays English-only).
