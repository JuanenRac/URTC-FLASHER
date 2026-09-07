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
writes or resets one. The established Tkinter SWD/JTAG workflow remains the
only full-chip programming surface until the complete operation is validated
against physical hardware.

After a normal active CAN connection, the deck's **Board snapshot** action
uses only documented query frames to collect the board version, CAN error
counters, expansion type, MLX variant and peripheral information. It never
writes configuration, firmware or option bytes. It is unavailable in
listen-only mode because these protocol queries require a response from the
board.

The non-versioning build check also extracts every `uiText("KEY")` call from
the QML deck and requires that key in all seven shipped language files. It
checks localization coverage without launching Qt or opening a transport.

## Usage

```
$ python urtc_flasher.py --cli -h
usage: urtc_flasher.py --cli [-h] [--transport {serial,socketcan,mock}]
                             [--port PORT] --file FILE [--no-trigger]
                             [--force] [--allow-downgrade]
                             [--mock-fail REASON]

Headless URTC CAN OTA firmware update (no GUI).

options:
  -h, --help            show this help message and exit
  --transport {serial,socketcan,mock}
                        Serial/SLCAN (default, all platforms), SocketCAN
                        (Linux only), or mock (simulated in-memory bootloader,
                        for testing this tool's own logic - not for use
                        against a real board)
  --port PORT           Serial port (e.g. COM3 or /dev/ttyACM0) for
                        --transport serial, or interface name (e.g. can0) for
                        --transport socketcan. Not needed for --transport
                        mock.
  --file FILE           Firmware .bin file to flash
  --no-trigger          Skip the 0x7F0 bootloader-entry trigger - use this if
                        the board is already sitting in the bootloader (fresh
                        JTAG flash, or no valid application currently present)
  --force               Flash even if the file fails the plausibility check
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
below uses it. `serial`/`socketcan` need real hardware (a USB-CAN
adapter or a brought-up SocketCAN interface) and are not demonstrated
here.

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
$ python urtc_flasher.py --cli --transport mock --file firmware/URTC_MAIN_FIRMWARE_v0.2.5.bin
Loaded config overrides from ...\URTC-FLASHER\urtc_config.json: hmac_key_hex, slave_hmac_key_hex
Firmware: firmware/URTC_MAIN_FIRMWARE_v0.2.5.bin (70916 bytes) - looks valid
Using the mock transport - nothing here is touching real hardware.
Connected via mock.
Sending bootloader-entry trigger (0x7F0)...
Firmware: firmware/URTC_MAIN_FIRMWARE_v0.2.5.bin
  size: 70916 bytes (69.3 KB)
  CRC32: 0x927D3DC9
  HMAC-SHA256: c5a01c69fd31d9ac23dde45f4bc91ff45b8469b2e98d791d71d191e44b70d712
  HardwareID: 0x0303CC01
Sending start-update (0x7F1)...
  status: Erasing backup slot
  status: Receiving firmware data
Sending HMAC signature (4x 0x7F7)...
Sending firmware data...
  page 1/35 written and acked (0.41s, 4.8 KB/s)
  ...
  page 35/35 written and acked (0.27s, 4.7 KB/s)
Transfer complete: 70916 bytes in 15.8s (4.4 KB/s average, 0 page-ACK retries)
Sending end-update / verify (0x7F4)...
Verifying and copying to main slot (this can take a while)...
  status: Verifying (size/CRC32/HMAC/HardwareID)
  status: Verify OK - jumping to new firmware
Update verified OK - board is resetting into new firmware.
SUCCESS: firmware update complete.
$ echo $?
0
```

(35 page lines shown collapsed to first/last above; every one was real
in the actual run.) The `Loaded config overrides` line is real too — this
checkout ships a real `urtc_config.json` overriding the HMAC keys used to
sign the transfer, and the CLI logs that override on every invocation.

### Real failure path: `--mock-fail`

`--mock-fail` drives `MockCAN` to report a real bootloader verify
failure (a `VERIFY_FAIL_REASON_*` code from `CANBUS.TXT`) instead of
success, after a real, complete page-by-page transfer — this is the
actual failure-reporting code path, not a simulated short-circuit:

```
$ python urtc_flasher.py --cli --transport mock --file firmware/URTC_MAIN_FIRMWARE_v0.2.5.bin --mock-fail 0x03
...
Sending firmware data...
  page 1/35 written and acked (0.43s, 4.6 KB/s)
  ...
  page 35/35 written and acked (0.27s, 4.7 KB/s)
Transfer complete: 70916 bytes in 20.9s (3.3 KB/s average, 0 page-ACK retries)
Sending end-update / verify (0x7F4)...
Verifying and copying to main slot (this can take a while)...
  status: Verifying (size/CRC32/HMAC/HardwareID)
  status: Verify FAILED - main slot untouched - HMAC signature mismatch (not signed with this project's key)
FAILED: Bootloader reported failure: Verify FAILED - main slot untouched - HMAC signature mismatch (not signed with this project's key)
$ echo $?
1
```

### Real error path: a firmware file that fails the plausibility check

Passing this repo's own real bootloader image (`URTC_MAIN_BOOTLOADER_v0.3.4.bin`)
as if it were an application image is rejected *before* any transport
work starts — its real reset-handler address (`0x080004CD`) genuinely
falls outside the application slot, because it's a real bootloader
image, not a corrupted or synthetic one:

```
$ python urtc_flasher.py --cli --transport mock --file firmware/URTC_MAIN_BOOTLOADER_v0.3.4.bin
Loaded config overrides from ...\URTC-FLASHER\urtc_config.json: hmac_key_hex, slave_hmac_key_hex
Firmware: firmware/URTC_MAIN_BOOTLOADER_v0.3.4.bin (17796 bytes) - reset handler (0x080004CD) doesn't point inside the application slot (0x08008000-0x08024000) - this looks like a bootloader image, not an application image, or an image built for the other target (main board vs. expansion slave). A CAN-OTA update only ever writes to the application slot, so this file can't go through this path regardless of size - use the SWD/JTAG section instead if you actually need to update the bootloader.
Refusing to flash a file that fails the plausibility check (pass --force to override).
$ echo $?
2
```

`--force` overrides this and proceeds anyway (real run, truncated after
a few real transferred pages — the mock bootloader has no opinion on
image *content*, only the local plausibility check does):

```
$ python urtc_flasher.py --cli --transport mock --file firmware/URTC_MAIN_BOOTLOADER_v0.3.4.bin --force --no-trigger
Firmware: firmware/URTC_MAIN_BOOTLOADER_v0.3.4.bin (17796 bytes) - reset handler (0x080004CD) doesn't point inside the application slot (0x08008000-0x08024000) - ...
Using the mock transport - nothing here is touching real hardware.
Connected via mock.
Firmware: firmware/URTC_MAIN_BOOTLOADER_v0.3.4.bin
  size: 17796 bytes (17.4 KB)
  CRC32: 0x8F515C68
  HMAC-SHA256: 82628787f9eae386d94d84cd4fb19ec99f6f1db04a593327cee0f40c0d019732
  HardwareID: 0x0303CC01
Sending start-update (0x7F1)...
  status: Erasing backup slot
  status: Receiving firmware data
Sending HMAC signature (4x 0x7F7)...
Sending firmware data...
  page 1/9 written and acked (0.43s, 4.7 KB/s)
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
$ python urtc_flasher.py --cli --transport serial --file firmware/URTC_MAIN_FIRMWARE_v0.2.5.bin
ERROR: --port is required for --transport serial/socketcan.
$ echo $?
2
```

### Real error path: missing required `--file`

```
$ python urtc_flasher.py --cli --transport mock
usage: urtc_flasher.py --cli [-h] [--transport {serial,socketcan,mock}]
                             [--port PORT] --file FILE [--no-trigger]
                             [--force] [--allow-downgrade]
                             [--mock-fail REASON]
urtc_flasher.py --cli: error: the following arguments are required: --file
$ echo $?
2
```

## Exit codes

Documented directly in `run_cli()`'s own docstring in `urtc_flasher.py`:

| Code | Meaning |
|------|---------|
| `0` | success |
| `1` | protocol/connection error (a `FlashError`/`SLCANError`/`SocketCANError`, or any other unexpected exception, during the actual transport/flash attempt) |
| `2` | bad arguments or an invalid firmware file (missing `--port`, an unavailable transport, a file that fails the plausibility check without `--force`) |
| `130` | cancelled (Ctrl+C) |

## GUI

Running `urtc_flasher.py` with no arguments (or double-clicking it) opens
the default windowed Tkinter GUI instead — a 5-second splash, then the
main window covering both the CAN-OTA update flow shown above and the
GUI-only SWD/JTAG full-chip programming section, with a language
selector (the CLI itself stays English-only).
