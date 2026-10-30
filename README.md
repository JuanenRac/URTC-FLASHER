<p align="center">
  <img src="/images/URTC_FLASHER_BANNER.svg" alt="URTC Flasher Logo" width="100%">
</p>

# URTC Flasher (Windows / Linux)

<p align="center">
  🇺🇸 <b>English</b> |
  <a href="README_spa.md">🇪🇸 Español</a> |
  <a href="README_fra.md">🇫🇷 Français</a> |
  <a href="README_ita.md">🇮🇹 Italiano</a> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a> |
  <a href="README_por.md">🇵🇹 Português</a>
</p>

### Updates the firmware of a URTC board over CAN (CAN-OTA) and programs the whole chip over SWD/JTAG, on Windows and Linux

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Language-Python-3776AB.svg" alt="Python">
  <img src="https://img.shields.io/badge/UI-Qt%20Quick-38d4e6.svg" alt="Qt Quick">
  <img src="https://img.shields.io/badge/Tests-500-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Protocol-CAN--OTA-orange.svg" alt="CAN-OTA">
</p>

---

**Honesty check - what actually runs today:** `tests/` holds 47 pytest files (500 tests: all pass; 79 of them skip without PySide6) - the CAN-OTA protocol against a real `MockCAN` transport (`flasher_transports.py`) that plays back a full simulated bootloader sequence (start/erase/receive, page data + PAGE_ACK, HMAC chunks, end-update with a real success or a specific `VERIFY_FAIL_REASON`), the signature rules (published signature sent without any key, unsigned image refused, manifest sha256 mismatch refused before any bus traffic), the image integrity checks and the bundled `firmware/` against its manifests. GitHub Actions (`.github/workflows/ci.yml`) runs this suite on every push, and `tools/build_test.py` runs it in `build-test.sh`/`.bat`. It also runs `ruff check` and `python -m mypy` (a type check of the program and of the copies of the shared code). The three `verify_qt_*.py` scripts at the repo root are real end-to-end checks kept outside pytest (they need a real Qt event loop; run them with `QT_QPA_PLATFORM=offscreen python verify_qt_*.py`); `verify_qt_swd_full_chip_flash.py` only builds the `PyOCDCLI`/`CubeProgrammerCLI` commands with `dry_run=True`. None of this has been run against a real board over real hardware in this environment. See `CHANGELOG.md` for exactly what has shipped so far. The simulated bootloader (`MockCAN`) is only a model written from the protocol description: it reproduces the page acknowledgements, the partial last page and the readback frames, but it is not the real bootloader, so a green test run does not replace a trial on a real board (the official 73476-byte image could not be installed, and the last frame of a backup was dropped, while the tests passed, precisely because the simulation was more forgiving than the real bootloader).

---

> **Safety and security status:** this ecosystem is not a certified safety system, and no populated URTC board exists yet. The bootloaders check firmware images with CRC32 and a shared-key HMAC-SHA256, not with an asymmetric signature (planned); the published application images are signed with the public development key (`signing_key_kind: dev`), so anyone can produce an image the bootloader accepts; nothing has been transmitted to a real board. Read the [security baseline](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/SECURITY_BASELINE.md) and the [threat model](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/THREAT_MODEL.md) before relying on any statement here for the safety of a person.

## 📋 At a glance

| | |
|---|---|
| Version | `0.4.2` |
| Maturity | Functional |
| Tests | 500 (`python -m pytest tests -q`) |
| Stack | Python / PySide6 / Qt Quick / CAN-OTA / SWD/JTAG |
| Target | The PC of the person using it |
| On real hardware | Simulated only: tested against emulators, fakes or simulators; no run on real hardware is recorded for this version |

**Jump to:** [Overview](#-overview) · [Architecture](#-architecture) · [Features](#-features) · [Security](#-security--safety) · [Interfaces](#-interfaces) · [Configuration](#-configuration) · [Quick start](#-quick-start) · [Testing](#-testing) · [Structure](#-repository-structure) · [Related](#-related-projects)

<!-- urtc-section:status_flasher -->
## 🚦 Project status

🟢 done and verified · 🟡 works, with known limits · 🟠 half done or not verified · 🔴 not done or not working. Nothing is green if it never ran on real hardware.

| Part | Status | What the repository can show |
| --- | :---: | --- |
| Software | 🟡 | Works on a PC and against the simulator; never run against a real board. |
| Interface | 🟡 | The window runs and is checked against a simulated board; not tried with a real adapter. |
| Tests | 🟢 | The test suite passes in the CI on every push. |
| Real hardware | 🟠 | No run on a real board yet: the bench test is still pending. |
| Security | 🟡 | Releases are signed with Ed25519 and checked before use; the key handling was not reviewed by anyone else. |
| Documentation | 🟡 | README in eight languages and reference documents; the translations were not reviewed by native speakers. |

<!-- /urtc-section:status_flasher -->

## 🎯 Overview

A small cross-platform GUI tool for updating URTC board firmware over CAN
bus. It implements the exact bootloader protocol from `docs/CANBUS.TXT` (in
the sibling [URTC](https://github.com/JuanenRac/URTC) repository this tool
implements against - see "Related Projects" near the end of this document;
every other `docs/*.TXT` reference in this README points there too): the
HardwareID check, shared-key HMAC-SHA256 chunks (not an asymmetric signature), the golden-image backup-slot update
flow, live progress via the bootloader's heartbeat messages, and a
version-query (does this board's application *or* bootloader identify
itself over CAN) so you can see what's currently installed before deciding
what to flash.

**Check for updates.** The button "Check for updates" asks GitHub once for the latest release and, only if it carries a package for this system that is newer than the installed version, offers to download it. The package is accepted only if its SHA-256 and its Ed25519 signature (the key of the releases, pinned in the program) are valid; it is installed only after you confirm it, never while a transfer is running, and the previous version is kept so you can go back (and is restored by itself if the new one does not start). Nothing is ever checked or installed on its own: the check when the program opens is an option, off by default, and the confirmation can only be turned off in the same window after a warning.

Two ways to talk to the board, both speaking the same protocol underneath:

- **Serial / SLCAN** — works on Windows and Linux. Needs a USB-CAN adapter
  running SLCAN firmware, connected as a virtual serial port.
  - With no adapter and no hardware, a virtual board stands in: run `python -m urtc_can.virtual_board`, name its address in the environment variable `URTC_VIRTUAL_PORT` (for example `socket://127.0.0.1:7777`) before starting the program, or give it to `--port` on the command line. It appears in the port list and answers like a board, application and bootloader.
- **SocketCAN** — **Linux only**, and only shown in the tool's UI on
  Linux. Talks directly to a kernel `can0`/`slcan0` network interface. If
  your adapter already runs `gs_usb`/candleLight firmware (most CANable
  boards do out of the box), this path needs **no adapter reflash at
  all** — Linux's own driver handles it natively.

## 🧩 Role in URTC

URTC-FLASHER is the program that puts firmware on a URTC board. It speaks the bootloader protocol of URTC (`docs/CANBUS.TXT` of that repository) over a USB-CAN adapter, as an SLCAN serial port or as SocketCAN on Linux: the HardwareID check, shared-key HMAC-SHA256 chunks, the golden-image backup-slot flow and a version query so that you see what is installed before you decide what to flash. For a board with no working bootloader, or to program the whole chip, it prepares the SWD/JTAG commands for pyOCD or STM32CubeProgrammer. It is the update companion of URTC-TESTER, shares its CAN code with it through URTC-COMMON, and URTC-UPDATER can hand it a firmware image whose release signature was already checked.

## 🏛️ Architecture

<p align="center">
  <img src="images/architecture.svg" alt="URTC-FLASHER architecture: who uses it, what it holds and what it depends on" width="100%">
</p>

How the parts of this repository fit together: who uses it, what it holds and what it depends on. The picture is drawn from `docs/architecture.json` and checked against the code.

<!-- urtc-section:updates -->
### How it updates

This program can look for a newer version of itself: the "Check for updates" button asks GitHub once and offers a signed package only if it is for your system and newer. Nothing is checked or installed on its own unless you turn the check on, and an update needs your confirmation. The package must match its SHA-256 and the signature of the releases key pinned in the program; the previous version is kept, and it is restored by itself if the new one does not start. `urtc-updater --cli package list|check|install|rollback` does the same from the command line for the flasher and the tester, and `install --file` works without a network.
<!-- /urtc-section:updates -->

## 🖼️ Screenshots

<!-- urtc-shots -->
Captured at 1920×1080 on a test bench, with sample data and no real installation behind them.

<table>
<tr>
<td width="50%" valign="top"><img src="images/screenshots/deck.png" alt="The window as it opens: the connection, the firmware inventory, the four checkpoints of a CAN-OTA update and the device configuration." width="100%"><br><sub>The window as it opens: the connection, the firmware inventory, the four checkpoints of a CAN-OTA update and the device configuration.</sub></td>
<td width="50%" valign="top"><img src="images/screenshots/heads.png" alt="Tool heads on the bus: a modelled bus with six heads, one in each state a head can be in (selected, address conflict, fault latched, in its bootloader, lost and ready)." width="100%"><br><sub>Tool heads on the bus: a modelled bus with six heads, one in each state a head can be in (selected, address conflict, fault latched, in its bootloader, lost and ready).</sub></td>
</tr>
<tr>
<td width="50%" valign="top"><img src="images/screenshots/help.png" alt="The Help window: the steps for using the program, written in the language of the window." width="100%"><br><sub>The Help window: the steps for using the program, written in the language of the window.</sub></td>
<td width="50%" valign="top"><img src="images/screenshots/updates.png" alt="The update window: a newer signed package is installed only after you confirm it." width="100%"><br><sub>The update window: a newer signed package is installed only after you confirm it.</sub></td>
</tr>
</table>
<!-- /urtc-shots -->

These pictures are the real window, drawn without a screen as it opens (nothing connected, nothing sent). The guide goes through the deck, the Help window and the update window.

[Guide with pictures](docs/WINDOW_GUIDE.md)

## ✨ Features

### Checking what's currently installed

> In the Qt Quick deck the ports of both transports (serial adapters and, on Linux, SocketCAN interfaces) are in one list, and the queries of this section are made by **READ BOARD STATE**, which asks for the version, the CAN error counters, the expansion board type, the MLX9064x variant and the peripheral info in one go and shows them in the board snapshot. The saves of the device-configuration section write the values.

If you're on Linux and SocketCAN is available, you'll see a **Transport**
choice at the top - pick Serial/SLCAN or SocketCAN before connecting. On
Windows this row doesn't appear at all; Serial/SLCAN is the only option.

Click **Connect**, and the tool automatically asks the board what it's
currently running (CAN ID `0x7F8` → `0x7F9` - see `docs/CANBUS.TXT`). This works
whether the board is running its application normally *or* sitting in the
bootloader, so you don't need to trigger a reset just to find out. Click
**Query** any time afterward to check again (useful right after a flash
completes, to confirm the new version actually took).

**When the bootloader itself answers** (board sitting in the bootloader,
not running its application), it also reports its own version - a
separate thing from the installed application's version, tracked via its
own `BOOTLOADER_VERSION_MAJOR/MINOR/PATCH` in `bootloader_common.h` and sent as
a second frame (`0x7FA`) right alongside `0x7F9`. The running application
never sends this - it has no way to know a currently-flashed bootloader's
version other than asking the bootloader itself, so this only shows up
when the board is actually sitting there (right after `0x7F0`, or on a
fresh boot before it's jumped to the application).

**The patch number.** A board with firmware 0.3.5 or later also sends the
patch number of the installed application (frame `0x7E9`, right after
`0x7F9`), so the window and the log show the full `major.minor.patch` (for
example `v0.3.5`) instead of `major.minor`; the patch of an image is the
third part of the version in its manifest. Before an update the log shows
`installed -> new` in that form, and the patch only takes part in the
"older than installed" warning when both sides carry one. A board that
predates the patch answers without it and is shown exactly as before. When
the bootloader announces (flag in the same frame) that it reads the patch,
the end-of-update frame carries it in the high byte of the minor field; any
other bootloader, and any image without a patch, get the unchanged
two-number frame. The expansion slave's version answer (`0x218`) has the
same optional extension. This follows the protocol description and is
tested against the simulator only; it has not been tried on a real board.

What you'll see:

- **`v0.2 (application, HardwareID 0x0303CC01)`** - normal case, application
  running, everything matches.
- **`Bootloader running, no valid firmware currently installed, bootloader
  v0.1.2`** - the board is stuck in the bootloader with nothing to jump
  to (blank chip, or every check on the main slot failed). This is
  exactly the situation this tool exists to fix - flash it. The
  bootloader version shown here is the bootloader itself, unrelated to
  whatever application version failed its checks.
- **`⚠ HardwareID mismatch!`** shown in red - something answered, but its
  HardwareID doesn't match what this tool expects. Don't flash without
  understanding why first; the bootloader would reject the update anyway,
  but a mismatch here can also mean you're pointed at the wrong board
  entirely.
- **No response** (red) - board unresponsive, wrong bitrate, or not
  actually connected. Check the physical connection and, on the SocketCAN
  path, that the interface is actually up (`ip link show`).

**Expansion board:** a separate dropdown and Query/Save pair, right below
version checking. Reads and sets which of the 7 possible `CONN_EXPANSION`
configurations (none, or one of 6 real variants - see `EXPANSION.TXT`)
is physically installed, over CAN (`0x1A0`/`0x1A1`). There's no
electrical way for the board to sense this itself, so it has to be told -
this lives here (not only in `URTC Tester`) since it's a one-time
hardware-configuration step most naturally done alongside a firmware
update. **Save** asks for confirmation first, since this persists across
power cycles until explicitly changed again.

**MLX9064x sensor variant:** same shape as the expansion board control
right above it - a dropdown and Query/Save pair reading/setting which of
the 3 MLX9064x-family thermal sensors (or none at all) is actually
populated, over CAN (`0x1A6`/`0x1A7` - see `CANBUS.TXT`). Only meaningful
when the expansion board above is set to an Advanced variant or
Basic+MLX9064x; the board's own firmware ignores this setting entirely
on every other expansion board type. "None installed" (the safe default)
deliberately doesn't fall back to assuming MLX90640 - a board with a real
MLX90640 wired to it needs this set explicitly, once, the same way the
expansion board type itself does.

### Flashing

1. **Connect**: pick Serial/SLCAN or SocketCAN (Linux only), then the
   port/interface, then click Connect. For Serial/SLCAN this opens the CAN
   channel at 500 kbit/s (URTC's fixed bus speed); for SocketCAN the
   interface is expected to already be at that bitrate (step 1 above) -
   this tool doesn't set it. Either way, the current version is queried
   automatically - see section 4 above.
2. **Pick a flash target**: "This board (main)" or "Expansion slave" -
   defaults to the main board, the far more common case. The slave option
   only reaches anything on an Advanced expansion board variant
   (TMC2209+STM32F303CBT6 or TMC5160A+STM32F303CBT6) - the update is
   relayed through the main board's own I2C bridge to the slave chip
   (`CANBUS.TXT`'s own `0x210`-`0x219`), not a separate physical
   connection. "Erase F-RAM before flashing" (step 4 below) disables
   itself automatically when Slave is picked - the slave chip has no
   F-RAM of its own to erase.
3. **Select firmware**: pick from the detected list, or Browse - see
   section 3 above for exactly how detection and validation work.
4. **Flash**:
   - Leave "Board is currently running the application" checked if the
     board is powered up and running normally - the tool sends the
     `0x7F0` magic-payload trigger first (or `0x210`, relayed to the
     slave, if Slave is the selected target), which safely shuts down
     every actuator before resetting into the bootloader.
   - Uncheck it if the board is already sitting in the bootloader (right
     after a fresh JTAG flash, or if the version check above showed "no
     valid firmware currently installed").
   - Click **Flash Firmware** and confirm - the confirmation dialog names
     which target you're about to flash, so double-check that matches
     what you actually meant to select. The log shows every protocol
     step; the progress bar tracks page-by-page write progress during
     transfer, then copy progress during the final backup-to-main copy.

If verification fails at any point (CRC32, HMAC, or HardwareID mismatch),
the bootloader's main slot is never touched - the board keeps running
whatever firmware it already had. It's always safe to just try again.

**Back up Firmware (CAN)**: reads the currently-installed firmware back
over the bus, unmodified, and saves it as a `.bin` file - the CAN
equivalent of the SWD section's own "back up entire flash before erasing"
(section 6 below), for the same reason. Worth doing before any update,
especially before a deliberate downgrade (below), since it's the only way
to get today's exact bytes back later if you don't still have the file
that produced them. Main board only, and only while the board is actually
sitting in the bootloader - requires a bootloader that implements
`0x7FE`/`0x7FF` (see `docs/CANBUS.TXT`); an older one just never answers,
surfaced as a clear timeout rather than a silently empty file. In practice this means the backup works on a board that has no valid application or that was left halfway through an update: with a valid application the bootloader jumps to it about 600 ms after reset unless a start-update frame (`0x7F1`) arrives, and this tool has no button that keeps the bootloader waiting (that would need a change in the bootloader). For a board that is running normally, back up the flash over SWD/JTAG (section 6) instead.

**Version and signature hints**: before the transfer the tool asks the board what is installed and logs "installed vX.Y -> new vA.B"; if the new version is older it warns that the bootloader will refuse it unless the downgrade is allowed, and suggests taking a backup first. An image whose manifest says it is signed with the PUBLIC development key (the bundled official images are) shows a red warning under the file name; set `"require_production_signature": true` in `urtc_config.json` to refuse such images altogether. When the board answers from its bootloader with no valid firmware, the newest official main-board image found in `firmware/` is selected for you to check and flash. After every successful update a small report (`logs/urtc_update_report_*.json`: tool version, operator, image name, size and SHA-256, versions before and after) is written; it carries its own SHA-256 so that an edit is noticeable, but it is not a signature.

**Deliberately installing an older version**: the bootloader normally
rejects a validly-signed image if it declares a version older than what's
already installed (verify-failure reason "rollback rejected") - this
stops a version with a since-discovered vulnerability from being
replayed. If you genuinely need to revert to an older, still-trusted
release, check **"Allow downgrade (bypass anti-rollback) for this
update"** (Target: main board only) before flashing - a second
confirmation dialog appears since this is deliberately bypassing a
safety check. This still uploads the complete older image through the
normal transfer, it only lifts the version-ordering check for that one
attempt (`0x7FD` - see `docs/CANBUS.TXT`); the version number reported to
the board comes from the file's own `.manifest.json` when one exists
next to it (see section 3 above), falling back to this tool's own
currently-configured version otherwise, logged clearly either way so
it's never a silent guess.

### Programming the complete chip via SWD/JTAG (advanced)

The **SWD/JTAG Programming** tab's "Program complete chip via SWD/JTAG
(advanced)" panel does a full bring-up flash - mass-erase the entire chip,
then write both the bootloader and application images fresh, at whichever
chip's own real addresses match the **Target chip** selection (see below).
This is a **different kind of operation** from sections 1-5 above:

|  | CAN OTA update (sections 1-5) | Full-chip SWD/JTAG (section 6) |
|---|---|---|
| Self-healing if interrupted | Yes - golden-image backup slot guarantees the running firmware survives | No - won't run anything until reprogrammed |
| Recoverable | Automatically, no action needed | Yes - just reconnect and flash again via SWD; the debug port doesn't depend on flash contents. Only a true permanent lock-out (RDP2 option byte) would prevent this, and nothing in this tool sets option bytes |
| Touches the bootloader | Never | Yes, by design |
| Needs | A USB-CAN adapter | An SWD/JTAG probe (ST-Link or similar) |
| Typical use | Routine firmware updates | First bring-up on a blank chip, or recovering a bricked board |

**Target chip:** "This board (main)" or "Expansion slave" - same 2
options as the CAN-OTA tab's own selector, but a genuinely separate
choice here: SWD/JTAG needs a probe physically wired to whichever chip
this is set to, since there's no bridge (unlike CAN-OTA) that lets one
connection reach both. Switching this changes the flash addresses used
automatically:

| | Main board (STM32F303CC) | Expansion slave (STM32F303CBT6) |
|---|---|---|
| Bootloader address | `0x08000000` (32K region) | `0x08000000` (18K region) |
| Application address | `0x08008000` (112K region) | `0x08005000` (54K region) |
| pyOCD target string | `stm32f303cc` | `stm32f303cb` |

Both target strings above are this project's own best guess at the real
pyOCD target name for each chip, not confirmed against a live pyOCD
install while this was written (STM32 coverage in pyOCD comes largely
through CMSIS-Packs rather than built-in targets) - if flashing fails
with a "target not found"-style error, run `pyocd list --targets --name
stm32f303` yourself and `pyocd pack install <the real name>` pulls the
right CMSIS-Pack.

**Requires one of** (the tool auto-detects which is available and only
enables the ones it finds):
- **pyOCD** - `pip install pyocd`. Free, open-source, no separate install
  beyond the pip package.
- **STM32CubeProgrammer** - ST's official tool, installed separately from
  [st.com](https://www.st.com). If you already have it for other STM32
  work, no extra install needed here.

Both are driven as command-line subprocesses, not imported as Python
libraries - you'll see the exact command logged before it runs.

**File formats:** `.bin` (needs the fixed address this tool already
knows - you don't enter it) or `.hex` (carries its own address, used
as-is). Mixing is fine - bootloader as `.hex` and application as `.bin`,
or vice versa, both work. Both file pickers validate the selected file
(plausible size for the target slot, and - where the format allows
confidently checking it - a plausible initial stack pointer) before
letting you proceed, the same way the CAN path's firmware picker already did.

**Connection is checked before anything destructive runs**, requiring
**positive evidence** of a real probe/target rather than just the
absence of an error - STM32CubeProgrammer's own exit code isn't a
reliable success/failure signal by itself, so a dedicated connection
check (`pyocd list --probes`, or a connect-only `-c port=SWD` for
STM32CubeProgrammer) runs before the mass-erase step ever does. Every
subsequent command's output is also screened for known failure text as a
second layer, in case a tool's exit code alone isn't trustworthy in some
other situation either.

**Dry run is on by default.** The first time, leave it checked and hit
"Flash Complete Chip" - it prints the exact commands to the log without
touching the board. Read through them, confirm the paths and addresses
look right, *then* uncheck dry run and do it for real.

**"Back up entire flash before erasing"** reads the whole 256KB flash
region to a `.bin` file first, via the same tool's own memory-read-to-file
command (`-r` for STM32CubeProgrammer, `commander savemem` for pyOCD) -
real insurance here, since unlike a CAN OTA update (which the golden-image
backup slot already protects), a full-chip erase has no other undo. Off by
default since it adds 10-30s and isn't needed on a blank/new chip; worth
checking before overwriting a board that's already running something.
If the read doesn't actually produce a file, the erase is refused rather
than proceeding without the backup you asked for.

**Testing status:** the connection-check logic above was verified against
real STM32CubeProgrammer output (both a genuine successful-connect log and
a documented "No target connected" failure, both sourced from ST's own
community forum) and against the exact false-success scenario a real user
hit. The full erase/program/verify sequence against a real ST-Link and a
real STM32F303CC has still not been exercised end-to-end - the environment
that wrote this has no USB access. Treat a first full real attempt with
appropriate caution - a spare/test board first if you have one, and keep a
fallback plan (STM32CubeIDE's own flash tool, or `st-flash`) in mind in
case something about your specific pyOCD version or probe doesn't match
what this assumes.

### Diagnostics — bus activity, bitrate, and debug bundles

**Bitrate selector + auto-detect** (Serial/SLCAN only): URTC's bus is fixed
at 500 kbit/s, which stays the default - this is for a misconfigured
adapter or troubleshooting a non-standard board. **Auto-detect** only
*listens*: it opens the adapter in SLCAN listen-only mode (`L`) at each
standard bitrate in turn and stops at the first one where it hears a valid
CAN frame, so it never transmits and cannot disturb a running bus. It
therefore needs other nodes to be sending, and the adapter must support
listen-only mode; on a silent bus (or with an adapter without it) it finds
nothing and you choose the bitrate by hand. Not connected yet when you
click it. SocketCAN's bitrate is set at the OS level (`ip link`), so this
control is disabled for that transport - there's nothing here for it to try.

**Bus activity** ("Check (2s)", next to Query): counts real protocol
frames actually seen over a fixed 2-second window on whichever transport
is connected. This is deliberately **not** the same thing as a true CAN
bus-load percentage - that would need a netlink query (SocketCAN) or
adapter-specific extensions (SLCAN) this tool doesn't have a standard,
dependency-free way to get for the *adapter's own* controller. What it
does give: a genuine, directly-measured "is anything talking on
this bus, and roughly how often" signal, on either transport. For
SocketCAN specifically, it also shows the 2-second delta of Linux's own
interface statistics (`/sys/class/net/<iface>/statistics/`) - basic
rx/tx/error/drop counters every interface exposes, read as plain files,
no extra dependency. Connecting over SocketCAN also reads
`/sys/class/net/<iface>/carrier` - a plain 0/1 file every Linux interface
exposes. When a CAN controller goes bus-off, the kernel driver calls
`netif_carrier_off()`, so "no carrier" here is real evidence of a bus-off
or similarly dead link, logged as a warning with the exact recovery
command (`sudo ip link set <iface> down && sudo ip link set <iface> up
type can bitrate 500000 restart-ms 100`). This tool doesn't run that
command itself - clearing a real bus-off needs the interface taken down
and back up at the kernel level, which needs root and counts as changing
system network configuration, not something to do silently on your behalf.

**Error counters (TEC/REC)** (next to Bus activity): unlike the adapter-
side counters above, this asks the **board itself** for its own CAN
controller's Transmit/Receive Error Counter (`0x7FB`/`0x7FC` - see
`docs/CANBUS.TXT`), answered by whichever of the application or
bootloader is currently running. Green means both counters are at 0
(error-active, healthy); orange means one or both are nonzero but below
128 (still error-active, but something's causing retransmits); red means
128 or above (error-passive or worse) or no response at all (older
firmware/bootloader that doesn't implement `0x7FB` yet, or the board not
connected). A steadily climbing TEC with a flat REC typically points at
this board's own transmissions going unacknowledged - no other node on
the bus, or a wiring/termination/bitrate problem specific to this
board's own connection.

**Export Debug Bundle** (above the log): saves a `.zip` with the current
on-screen log, basic system diagnostics (OS, Python version, which tools
were found, current transport/port/bitrate), and the currently-selected
CAN firmware file - useful for handing a complete picture to whoever wrote
the firmware if something goes wrong in the field, instead of copying log
text by hand.

### SWD/JTAG — file formats, slot verification, and probe selection

**File formats**: the SWD section's bootloader/application pickers accept
`.bin`, `.hex`, and `.elf`/`.axf`. ELF/AXF is parsed with a small amount
of hand-written struct-unpacking (ELF header + program headers only - no
symbols, no section headers), deliberately not using `pyelftools`: this
project stays at zero non-stdlib dependencies, and full ELF parsing is
more than this specific plausibility check needs. Verified against the
actual compiled `BOOTLOADER.elf`/`APP.elf` from this project's own build -
both correctly validate at their real load addresses
(`0x08000000`/`0x08008000`), not just synthetic test files. 32-bit
little-endian ARM only, which is all a Cortex-M target ever is. A `.hex`
file's declared size is the actual occupied byte count, not the address
span from its lowest to highest record - so a sparse file (a small block
of real firmware plus a distant, separate block of option bytes or
calibration data, which some STM32 toolchains bundle into one export)
validates on its real content rather than the gap between them. A raw
firmware image under a non-`.bin` extension (`.img`, `.rom`, or no
extension at all - selectable via the file picker's "All files" option)
gets its base address from which slot you're loading it into, the same
as a `.bin` would.

**Bootloader/application slot verification**: the file pickers verify
each image is meant for the slot it's being put into, not just that it
looks like *some* valid firmware. A bootloader image and an application
image both have an equally plausible stack pointer - same chip, same RAM
- so that check alone can't tell them apart if one ends up in the
other's slot. What can: a linked image's **reset handler** is a real,
absolute address baked in at link time, and it only ever points inside
the region it was actually linked for. Verified against this project's
own real compiled `BOOTLOADER.bin`/`APP.bin`: their reset handlers are
`0x08000785` and `0x0800C0CD` respectively, each correctly inside its
own slot's address range and outside the other's - so putting either one
in the wrong slot is caught and blocked, not silently accepted. Same
logic applies to `.hex`/`.elf`, checked against their own embedded load
address instead.

**Check Option Bytes** (same SWD/JTAG Programming tab, STM32CubeProgrammer
only - pyOCD doesn't expose this the same way via CLI): a read-only `-ob displ` dump, no
erase/write. Flags RDP level with the same care this whole tool takes
around SWD risk:
- **RDP0** - no protection, normal for a dev board.
- **RDP1** - reversible via CubeProgrammer's Read Unprotect, but that
  mass-erases the chip as part of removing it - not something this tool
  does for you automatically.
- **RDP2** - the one genuinely **permanent** lock-out in this whole
  project. Unlike every other risk documented above (all recoverable via
  SWD), RDP2 disables the debug port forever by ST's own design. This
  check exists to catch it before a full-chip operation, not after.

**Probe selection** (same tab): if more than one ST-Link/probe is
connected at once, every command requires picking one explicitly from
the Probe dropdown - there's no "whichever one the OS happens to
enumerate first". With exactly one probe connected, it's auto-selected;
with zero or several, hit Refresh and choose. This applies to the
full-chip flash and the option-bytes check alike, since both are
destructive-adjacent enough that guessing the wrong board is a real risk
on a multi-device bench.

**pyOCD writes are verified with an explicit read-back**, not just
trusted on exit code. pyOCD's own `flash` command skips rewriting pages
that already match (a speed optimization, not a verification report), so
this tool adds a `commander compare` step against both images after
writing - a genuine byte-for-byte check, matching what
STM32CubeProgrammer's `-v` flag already does. Only for `.bin`: `compare`
checks flash content against the file's raw bytes, which wouldn't
correctly match a `.hex`/`.elf` file's own encoding even after a
successful flash, so those two formats skip this specific step and rely
on pyOCD's own internal write-time verification instead.

### Transfer telemetry and verify-failure detail

**Transfer telemetry**: the log shows effective KB/s and elapsed time
per page during a CAN update, plus a summary line at the end (total time,
average KB/s, how many page-ACK retries happened). Purely informational -
doesn't change flashing behavior, just makes it easier to tell "this is
just slow" from "something's actually wrong" at a glance.

**Specific verify-failure reasons**: if verification fails during a CAN
update, `bootloader_protocol.c` sends a reason byte alongside status `0x05`
(verify failed) - incomplete transfer, CRC32 mismatch, HMAC mismatch, or
HardwareID mismatch, rather than every failure looking identical. See
`docs/CANBUS.TXT` for the exact frame format (`0x7F5`, DLC 2 for this specific
status). This tool and the bootloader agree on this frame format, so
flash both together if you're building a custom bootloader with a
different version of the protocol.

**Same detail for the expansion slave**: a failed slave update (Target:
"Expansion slave") queries `0x219` right after `0x215` reports
`STATUS_VERIFY_FAIL`, relaying the slave bootloader's own
`REG_VERIFY_FAIL_REASON` - the same 5 reasons as above, just reached over
the I2C bridge instead of read directly off a CAN frame. Requires a slave
bootloader that implements `0x219` (added alongside this tool's own
support for it); an older slave bootloader simply doesn't answer that
query, and this tool falls back to the generic "verification failed"
message instead.

### Optional F-RAM erase before flashing

Section 3 has a checkbox, **"Also erase the persistence F-RAM before
flashing"** - off by default. If checked, it sends the magic-payload
erase command (`0x192` - see `docs/CANBUS.TXT`) to the board's onboard
FM24CL64B persistence F-RAM before the update sequence starts, wiping
whatever tool-parameter state it had saved.

**Not required for a normal update.** A version mismatch in the saved
record's own layout is already detected and safely ignored on the next
boot (see `src/F303-master/README.md`'s parameter-persistence section) - this
checkbox exists for a genuinely clean slate, not because skipping it
would leave anything broken.

**Only works while the application is running** - the bootloader itself
doesn't handle `0x192` at all, only `firmware_can_global_post.c` does. This checkbox
is silently skipped (with a log line explaining why) if the "board is
currently running the application" checkbox above it is unchecked, since
in that case the board's assumed to already be sitting in the bootloader.

**A missing confirmation doesn't stop the flash.** If the erase command's
own confirmation frame doesn't come back within 2 seconds, this is logged
as a warning and the actual firmware update proceeds anyway - erasing is
a secondary, optional step alongside the real point of this tool, not
something that should abort an otherwise-successful update over its own
confirmation frame going missing. Check the F-RAM state separately
(`URTC Tester`'s own Query State button) if that matters to you.

<!-- urtc-section:heads -->
### Several tool heads on one bus

The firmware can let several tool heads share one CAN bus (the multinode extension). It is **off by default**, and a bus with one head works exactly as before. The **Tool heads** window finds the heads, lists each with its address, tool and serial number, and shows its state: ready, selected, address conflict, fault latched, in its bootloader or lost. You select one, the program asks you to confirm, and only then does it send anything to that head; while several heads are on the bus, a command is refused until one is selected and has confirmed it. If the selected head is lost, every head is put in its safe state (a checkbox of the window switches that off). It has been tried against a model of the bus only, not against boards. See `docs/MULTINODE.md` in URTC-COMMON.
<!-- /urtc-section:heads -->

## 🔒 Security & Safety

| Risk | Defence |
|---|---|
| Flashing an image to the wrong board | The HardwareID check of the bootloader protocol, made before anything is written |
| A corrupted, unsigned or tampered image | The image integrity checks, a manifest whose `sha256` does not match the file is refused before any bus traffic, an unsigned image is refused, and a published signature is sent without any key; a release signature (Ed25519) is checked before an image of a release is used |
| Installing an older image by mistake | The bootloader's anti-rollback check; a deliberate revert needs the downgrade authorization |
| A failed update that leaves the board dead | The golden-image model: the backup slot keeps the previous firmware, a lost confirmation frame is recovered by asking the version again instead of reporting a false failure, and the main slot can be read back first |
| A tampered update of this program | "Check for updates" accepts only a package with a valid SHA-256 and Ed25519 signature (the key of the releases, pinned in the program), installs only after a confirmation and never during a transfer, and keeps the previous version |

The bootloader checks images with CRC32 and a shared-key HMAC-SHA256, not with an asymmetric signature; the published application images are signed with the public development key, so anyone can make an image that the bootloader accepts. Nothing here has been run on a real board.

### Reliability during a CAN update, and session logs

If a page's ACK doesn't arrive within the normal 3s window during a CAN
update, the tool waits again (it does not resend the page's data) up to
twice more with a short backoff before giving up. This only helps an ACK
that is merely late: the bootloader sends each page ACK once and never
repeats it, so an ACK that was really lost cannot be recovered and the
update is aborted with an error (the board is left in its bootloader and
the update can simply be started again). The tool deliberately does not
resend page data on a timeout - if the data had arrived fine, resending
would make the bootloader read those bytes as the start of the *next*
page, desyncing the transfer. While waiting, the bootloader's own
heartbeat (sent roughly once a second) is compared with the progress the
page would imply and the log mentions when they agree; the heartbeat is a
whole percentage, so this is a hint only, not proof that the page arrived,
and it never changes the outcome.

Every session also writes a timestamped log file to `logs/`
(`urtc_flasher_YYYYMMDD_HHMMSS.log`), independent of the on-screen log -
useful for handing a full trace to whoever wrote the firmware if
something goes wrong in the field. This folder is created automatically
and is safe to delete; nothing reads old logs back in. Only the newest 30 session logs are kept; if the folder next to the program cannot be written (a read-only install), a per-user folder is used instead (`%LOCALAPPDATA%\URTC-Flasher\logs` on Windows, `~/.local/state/urtc-flasher/logs` elsewhere).

## 🔌 Interfaces

For CI pipelines, test benches, or production-line scripting where
there's no display:

```
python3 urtc_flasher.py --cli --port /dev/ttyACM0 --file firmware.bin
```

```
usage: urtc_flasher.py --cli [-h] [--transport {serial,socketcan,python-can,mock}] --port PORT
                             --file FILE [--no-trigger] [--force]
```

Exit codes: `0` success, `1` protocol/connection error, `2` bad arguments
or a firmware file that fails validation (pass `--force` to flash it
anyway), `130` cancelled with Ctrl+C. Only covers the CAN OTA update path
(sections 1-3) - the SWD/JTAG full-chip path is deliberately GUI-only for
now, given how much more is at stake if a scripted run gets a wrong
file/target combination wrong with nobody watching.

**`--transport python-can`** uses the optional `python-can` package (`pip install python-can`) for PCAN, Kvaser, gs_usb/candleLight and the other interfaces it supports, so the adapter does not have to be reflashed to SLCAN: `--port` is then `<interface>:<channel>` (for example `pcan:PCAN_USBBUS1`) and the bus is opened at 500 kbit/s. The window offers the same adapters when `python-can` is installed: those it finds for PCAN, Kvaser and gs_usb, and those named in the `URTC_PYTHON_CAN` environment variable (comma separated `<interface>:<channel>`), listed as `python-can:<interface>:<channel>`; the bus speed of that connection is fixed at 500 kbit/s. The window can also be started with `--firmware PATH` to have an image already selected (nothing is written to a board until you connect and confirm the update).

**`--transport mock`** runs the whole update sequence against a
simulated, in-memory bootloader instead of a real board - no adapter, no
port, nothing physical involved:

```
python3 urtc_flasher.py --cli --transport mock --file firmware.bin --no-trigger
```

Useful for testing this tool's own logic (retry behavior, timeout
handling, exit codes) in a CI pipeline or before touching real hardware -
not something that talks to an actual board. `--mock-fail 0x03` (or any
other `VERIFY_FAIL_REASON_*` value from `docs/CANBUS.TXT`) makes the
simulated update fail verification instead of succeeding, for testing
the failure path the same way.

## ⚙️ Configuration

This tool holds **no signing key**. The URTC build signs every application
image and publishes the signature next to it, in `<image>.manifest.json`
(`hmac_sha256`, plus `<image>.sha256`); the flasher sends that published
signature and refuses an image whose sha256 does not match its manifest.
Downloading an image from GitHub also downloads both files, and
`python tools/sync_firmware.py` fills the `firmware/` folder
from the URTC build (`--check` verifies it). By default it takes the set from the assets of the latest URTC release (`--release TAG` picks another one); a local folder, such as a local URTC build, can be given as an argument instead. Only a self-built image with
no manifest, on a bench board, needs a key: set `hmac_key_hex` /
`slave_hmac_key_hex` in `urtc_config.json` below - without one such an image
is refused instead of being signed with a key the bootloader cannot have.
See URTC's `docs/FIRMWARE_SIGNING.TXT`. The published images are signed with the public development key (`signing_key_kind: dev`), so this is a shared-key check: it shows the image was made by someone holding that key, not who they are; asymmetric (Ed25519) signing is planned, not implemented.

**Or override any of this without touching the script:** an optional
`urtc_config.json` next to `firmware/` can set the signing key, the
HardwareID, and the memory-map values - useful for a different board
revision, a rotated key, or (for the memory-map fields) adapting this
tool to a different chip variant or partition scheme, without needing a
new script version per deployment:
```json
{
  "hardware_id": "0x0303CC01",
  "hmac_key_hex": "555254432D4859445241...",
  "app_max_size": 114688,
  "bootloader_max_size": 32768,
  "flash_page_size": 2048,
  "bootloader_flash_addr": "0x08000000",
  "app_flash_addr": "0x08008000"
}
```
Every field is optional - only override what's actually changing. Missing
fields fall back to this tool's own built-in defaults. **The memory-map and HardwareID overrides only apply to the main board's own constants** (the one exception is `slave_hmac_key_hex`, the expansion slave's signing key, which can be set here too) - the
expansion slave chip's own equivalents (`SLAVE_BOOTLOADER_FLASH_ADDR`,
`SLAVE_APP_FLASH_ADDR`, `SLAVE_HARDWARE_ID`, etc.) are fixed in
`flasher_config.py` itself, since that hardware's own real values are
already confirmed against its own linker scripts rather than needing a
deployment-time override the way the main board's own defaults do. A
present-but-broken file logs a warning and also falls back, rather than
crashing the tool over a typo. Whichever source is active gets logged at
startup, so it's always visible which values a given session actually
used. `hardware_id` accepts either a JSON string (`"0x0303CC01"`) or a
plain JSON number (`50580689`) - whichever is more natural for however
the file gets generated. `app_max_size`, `bootloader_max_size`,
`flash_page_size`, `bootloader_flash_addr`, and `app_flash_addr` are
also overridable here, alongside the signing key and HardwareID above -
useful if this tool is ever adapted to a different chip variant or
partition scheme.

## 🚀 Quick start

### Get your adapter talking CAN

Which of these you need depends on your platform and which transport
you'll use:

**Linux, SocketCAN path (recommended if your adapter supports it):**
Nothing to flash on the adapter itself. Bring the interface up once per
boot (or add it to your network config to persist):
```
sudo modprobe can vcan gs_usb   # gs_usb covers most CANable-family boards
sudo ip link set can0 type can bitrate 500000
sudo ip link set can0 up
```
If your adapter enumerates as something other than `can0`, check `ip link
show` (or `dmesg` right after plugging it in) for the actual name. Some
adapters need `slcand` instead of a native driver — if `ip link show`
doesn't show a CAN interface at all after plugging in, this is likely your
case; see your adapter's documentation for the `slcand` invocation, which
creates an `slcan0` interface you then bring up the same way as above.

**Windows, or Linux via the Serial/SLCAN path:**
A CANable Pro v2 ships by default running **candleLight** firmware, which
talks to the host using the `gs_usb` protocol - the same one Linux's
SocketCAN `gs_usb` driver expects natively (see above). That protocol does
**not** present as a serial port, which is what this path needs. To use
Serial/SLCAN instead (required on Windows; optional on Linux):

1. Download SLCAN-compatible firmware for your adapter (search for
   "canable slcan firmware" — there are a few maintained forks; use
   whichever your adapter's own documentation points to).
2. Put the adapter into DFU/bootloader mode (usually a BOOT button held
   during power-up, or a jumper — check your adapter's documentation).
3. Flash the SLCAN firmware using your adapter vendor's flashing tool or
   `dfu-util`.
4. Reconnect — it should now enumerate as a serial port: a COM port on
   Windows, or `/dev/ttyACM0`/`/dev/ttyUSB0`-style on Linux.

If your adapter already runs SLCAN firmware, skip straight to step 2 below.

A received SLCAN line whose actual length doesn't match what its own
declared DLC implies is treated as malformed and skipped, rather than
parsed from its first N hex characters regardless of what follows -
worth knowing if you're debugging against a noisy or non-standard adapter.

### Install and run

**Windows:**
```
python -m pip install -r requirements.txt
python urtc_flasher.py
```
Or build a standalone `.exe` with `build_exe.bat` (see that file).

**Linux:**
```
python3 -m pip install -r requirements.txt
python3 urtc_flasher.py
```
Or build a standalone binary with `./build_exe.sh` (`chmod +x` it first).

Both scripts pass `--noconfirm` to PyInstaller, so rebuilding over an
existing `dist/URTC_Flasher` replaces it directly rather than waiting on
a "replace it?" prompt that's easy to miss in a script's output.

#### Visual command deck

The **Qt Quick** command deck is the only window of the program (tested against the simulator only; image checks use a shared-key HMAC-SHA256). Start it with:
~~~
python urtc_flasher.py
~~~
It has a dark navy/cyan surface with a connection card, readable firmware tables, a dark verification log and a visible progress channel, and it covers the whole workflow: the CAN-OTA update of the main board or of the expansion slave (the target choice; the "board is running the application" option, the F-RAM erase and the downgrade authorisation are for the main board), a backup of the installed firmware over CAN, the bus-speed selector with the listen-only search, the download of a GitHub release, a file picker for any `.bin`, the bus-activity check, the Board Snapshot, the 4 device-configuration writes, read-only SWD/JTAG discovery and full-chip SWD/JTAG programming (erase/write, dry run, back-up-before-erasing, RDP check). Every action that writes to the board asks for confirmation first, the downgrade authorisation asks a second time, and closing the window during a transfer asks once more. None of it has been tried on a real board. `python urtc_flasher.py --cli` is the headless mode (section 7).

#### Header and tools

- **Header** - the connection state, the language selector (the choice is saved and applies on the next start) and the version.
- **Save Logs...** and **Save Debug Bundle** - the on-screen log as plain text, or a fuller zip with system diagnostics and the selected firmware file (see "Diagnostics" below). Every session is also written to `logs/`, and the newest ones are kept.
- **About URTC Flasher** - version and author, with buttons for the **Readme** (in the language of the interface when a translation exists), the **License** and the project's **URTC GitHub** page.

**Language**: English by default.
Chosen with the selector in the header of the window - saves to `urtc_config.json` immediately (same file used for the technical
hardware overrides — the language preference just lives alongside
those), applied on the next launch. Translations live in plain text
files under `language/` (`english.lng`, `spanish.lng`, `italian.lng`,
`french.lng`, `german.lng`, `japanese.lng`, `chinese.lng`, `portuguese.lng`) as simple `KEY=Value` pairs, one per line -
lines starting with `#` and blank lines are ignored, and a literal `\n`
inside a value becomes a real line break (used by the handful of
multi-line dialog messages). Generated from the catalog of URTC-COMMON (a translation is corrected there and the files are written again, never edited by hand), or a starting point for another language (add
`language/<name>.lng`, add `("<name>", "Native Name")` to
`AVAILABLE_LANGUAGES` near the top of `flasher_config.py`, and set
`"language": "<name>"` in `urtc_config.json`). A key missing from a
language file falls back to showing that key's own name rather than
crashing, and a missing or unreadable language file (bad edit, wrong
filename) falls back to English for the whole interface - either way
the tool stays usable while the mismatch gets sorted out.

**Linux serial permissions:** if you're using the Serial/SLCAN path and
connecting fails with "Permission denied", your user needs to be in the
group that owns serial devices (`dialout` on Debian/Ubuntu; varies on
other distros):
```
sudo usermod -a -G dialout $USER
```
Log out and back in (group membership is read at login), then try again.
The tool detects this specific error and shows this same fix in a dialog,
but it's worth knowing ahead of time. SocketCAN doesn't have this
particular gotcha — access to a `can0`-style interface isn't gated by the
`dialout` group — but bringing the interface up in the first place (step 1
above) does need `sudo`, since that's a network-device configuration
change.

Using `python -m pip`/`python3 -m pip` rather than a bare `pip` sidesteps a
common issue on both platforms: `pip`'s own wrapper script isn't always on
PATH even right after a successful install, while `-m pip` finds the
installed module directly.

### Where firmware files go

**The folder starts empty.** The firmware images are not kept in this repository: they are the assets of the releases of [URTC](https://github.com/JuanenRac/URTC). The window downloads them from the release you choose, and `python tools/sync_firmware.py` fills the folder from the newest official release (or `--release TAG`). Every file is checked against the release signature (`.sig`, Ed25519) and its digests before it is used. While no official release exists, GitHub's "latest" answers 404 and `firmware_release.json` names the release used instead (today the bench pre-release); delete the file, or change its tag, when an official one is published.

This tool expects a `firmware/` folder right next to `urtc_flasher.py`,
at this repository's own root:

```
├── assets/
│   └── URTC_LOGO_FLASHER.svg      <- banner source (vector)
├── firmware/
│   ├── URTC_MAIN_FIRMWARE_v<version>.bin  <- put new .bin files here
│   └── URTC_*  <- tools/sync_firmware.py replaces the URTC_* files of this folder with one release; other files stay
├── logs/                          <- created automatically, one file per session
├── urtc_config.json               <- optional, not included by default (see "Changing the HMAC key" below)
├── urtc_flasher.py                <- entry point: CLI arguments and start of the Qt Quick window
├── flasher_config.py              <- config file I/O, language loading, protocol constants
├── flasher_transports.py          <- SLCAN, SocketCAN, MockCAN
├── flasher_swd_tools.py           <- STM32CubeProgrammer / pyOCD wrappers
├── flasher_validation.py          <- firmware file validation (.bin/.hex/.elf)
├── flasher_protocol.py            <- the CAN OTA state machine itself
├── flasher_github.py               <- lists and downloads the assets of a URTC GitHub release
├── flasher_records.py             <- session logs (location, retention) and update reports
├── pytest.ini / ruff.toml          <- pytest and ruff (static checks) settings
├── requirements.txt
├── build_exe.bat                  <- Windows standalone build
├── build_exe.sh                   <- Linux standalone build
└── README.md
```

This tool is organized into the modules above by responsibility, purely
for readability - there's no functional difference between having them
as separate files versus one large one.

This is deliberate: this whole repository is self-contained. If you just
want to flash a board — on a shop floor PC, from a USB stick, wherever —
you can copy this repository on its own, and it still works.

**You can keep more than one `.bin` in there.** Every application-firmware
file gets checked and listed - the tool doesn't just grab whatever it
finds, and bootloader binaries (anything with "BOOTLOADER" in the
filename - `URTC_BOOTLOADER.bin`, `URTC_SLAVE_BOOTLOADER.bin`) are
filtered out of this list entirely, since CAN-OTA only ever flashes
application firmware; a bootloader update needs SWD/JTAG instead (section
6 below). On startup (and whenever you click **Refresh**), each
remaining `.bin` in `firmware/` is checked against the same
plausibility test the bootloader itself applies to a fresh image (its
first 4 bytes have to look like a real initial stack pointer for this
chip's RAM, and its size has to fit the main slot). Every file shows up
in the list with a clear ✓ or ✗ and the reason why:

| File | Size | Status |
|---|---|---|
| URTC_MAIN_FIRMWARE_v<version>.bin | 71.8 KB | ✓ looks valid |
| URTC_SLAVE_FIRMWARE_v<version>.bin | 33.9 KB | ✓ looks valid |
| notes.txt.bin | 0.1 KB | ✗ first word doesn't look like a valid stack pointer |

- **Exactly one file passes the check** → it's selected for you the moment
  the tool starts. An invalid file sitting alone in the folder does *not*
  get auto-selected just because nothing else is competing with it.
- **More than one valid file** → nothing is auto-selected; pick the one you
  want from the list.
- **You select an invalid-looking file anyway** → the tool asks you to
  confirm first. This check exists to catch obvious mistakes (wrong file,
  truncated download, an empty placeholder) - it can't catch everything
  (a corrupted-but-plausible file, or one signed with the wrong key), which
  is what the bootloader's own CRC32/HMAC check during the real transfer
  is for.
- **Nothing found, or you want a file from somewhere else entirely** → use
  the **Browse .bin...** button, which works regardless of where the file
  actually lives (and runs the same validation check either way).
- **Want the latest build without hunting for it yourself** → **Download
  from GitHub...** lists the files attached to the latest GitHub release of
  the URTC repository (`github.com/JuanenRac/URTC/releases` - the firmware
  binaries are published as release assets, they are not kept in git) and
  lets you pick one to download directly into your own local `firmware/`
  folder - it then shows up in the list above like any other file, no
  restart needed. Type a release tag (for example `v0.3.5`) in the box at
  the top of the window and press **Load** to list another release instead
  of the latest. The image's `.sha256` and `.manifest.json` are downloaded
  together with it. Files are only accepted from GitHub's own hosts
  (`github.com` and the asset storage hosts it redirects to), and a file
  whose size differs from what the release announces is discarded. Uses
  GitHub's own public API (unauthenticated, so subject to GitHub's own
  60-requests/hour rate limit if you hit it a lot in a short window; a
  `GITHUB_TOKEN` environment variable raises it) - nothing here needs a
  GitHub account.

Each file of an official release has a release signature (`<file>.sig`, Ed25519): the flasher verifies it when it is there and refuses a wrong one. A set without signatures, such as a bench pre-release, is accepted by `tools/sync_firmware.py` only with `--allow-unsigned`.

**`<filename>.manifest.json` and `<filename>.sha256`, next to each firmware
file** - published by the URTC build for every image (and downloaded
together with it from GitHub). The manifest carries the version, the
`sha256` and, for application images, the `hmac_sha256` value the bootloader expects (a shared-key HMAC-SHA256, not an asymmetric signature; `signing_key_kind: dev` marks the public development key):

```json
{"component": "main_application", "version": "<version>", "sha256": "b48d4cd5...", "hmac_sha256": "b63a701e...", "signing_key_kind": "dev"}
```

Both digests are checked right before flashing and a mismatch **refuses the
flash** before anything is sent on the bus (wrong file, corrupted download
or stale manifest). The published signature is what gets sent to the
bootloader, and the manifest's version is what gets reported to it. A file
without a manifest (your own build) is flashed only if a signing key is set
in `urtc_config.json` - see "Changing the HMAC key" below.

Adding a new build later: just drop it into `firmware/` and click
**Refresh** - no restart needed.

<!-- urtc-section:first_flash -->
### First run without hardware

1. Start the virtual board: `python -m urtc_can.virtual_board`.
2. In another terminal set `URTC_VIRTUAL_PORT=socket://127.0.0.1:7777` and start the flasher: the virtual board is in the list of ports.
3. Select it, press Connect, pick an image from `firmware/` (or Browse) and press Start CAN-OTA.
4. The virtual board takes the whole update, with the same checks of the size, the signature and the version as a real one. It is a model: nothing of this has run on a board.
<!-- /urtc-section:first_flash -->

<!-- urtc-section:compatibility -->
### Requirements & compatibility

Which versions of the URTC programs work together, and which protocol version each one speaks, is listed in the compatibility table that URTC-COMMON generates: [docs/COMPATIBILITY.md](https://github.com/JuanenRac/URTC/blob/main/docs/COMPATIBILITY.md).
<!-- /urtc-section:compatibility -->

## 🧪 Testing

The suite has 500 tests in 47 files (`python -m pytest tests -q`; with Qt on a machine with no screen, `QT_QPA_PLATFORM=offscreen`; the 79 that need PySide6 skip without it): the CAN-OTA protocol against a real `MockCAN` transport that plays back a full simulated bootloader (start, erase, receive, page data and ACK, HMAC chunks, end-update with a real success or a specific `VERIFY_FAIL_REASON`), the signature rules, the image integrity checks, the firmware bundled in `firmware/` against its manifests, the SWD/JTAG commands built with `dry_run`, the language files and the Qt Quick panels. Three scripts at the root (`verify_qt_*.py`) drive the Qt panels end to end. CI also runs `ruff check`, `python -m mypy` and `tools/ci_validate.py`. `MockCAN` is only a model written from the protocol: it is more forgiving than the real bootloader, so a green run does not replace a trial on a real board.

## 🏗️ Build & Release

`build_exe.bat` / `build_exe.sh` build a standalone program with PyInstaller (both pass `--noconfirm`, so rebuilding over an existing `dist/URTC_Flasher` replaces it directly); `build-test.sh` / `build-test.bat` check everything without building anything or changing a version. The version of the program (`FLASHER_VERSION` in `flasher_config.py`, shown in the window banner and the title bar) changes only with the explicit `python bump.py` step; running from source and building never touch it. See `CHANGELOG.md` for the version history.

## 📂 Repository Structure

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of URTC-FLASHER" width="100%">
</p>

<details>
<summary>Text version of the tree</summary>

```text
URTC-FLASHER/
├── urtc_flasher.py                                    entry point
├── qt_flasher.py                                      the Qt Quick deck
├── flasher_*.py                                       protocol, checks, transports, SWD tools, records
├── verify_qt_*.py                                     end-to-end checks of the Qt panels
├── urtc_can/                                          protocol, transports and updates (copy)
├── urtc_ui/                                           interface helpers (copy)
├── firmware/                                          where the images go (starts empty)
├── tests/                                             47 test files, one per area
├── language/                                          the eight .lng language files
├── assets/                                            QML, banner and icon
├── docs/                                              architecture, build and run
├── logs/                                              session logs (kept out of Git)
├── tools/                                             build check, firmware sync, shared tools
├── images/                                            banner and the pictures of this README
├── .github/                                           CI workflow, issue and pull-request templates
├── test.sh test.bat                                   run the tests
├── run.sh run.bat                                     start the program
├── build-test.sh build-test.bat                       build and test scripts that change nothing in the repository
├── urtc.project.json                                  manifest: version, role, maturity and build command
├── CHANGELOG.md                                       what changed in each version
├── SECURITY.md SUPPORT.md LICENSE                     security policy, support and license
├── CONTRIBUTING.md CODE_OF_CONDUCT.md                 how to contribute and the code of conduct
├── .gitattributes .gitignore                          Git settings
├── build_exe.sh build_exe.bat                         standalone program (PyInstaller)
├── bump.py bump_version.py bump_manifest_version.py   scripts that raise the version
├── requirements*.txt requirements*.lock               dependencies, with their locks
├── mypy.ini pytest.ini ruff.toml                      type check, test and lint settings
├── urtc_config.json.example                           example of the hardware overrides and the language
├── urtc_i18n.lock.json                                lock of the generated language files
└── NOTICE LICENSE.md                                  copyright notice and documentation license
```

</details>

The annotated list of every source file, one line each, is in [docs/SOURCE_MAP.md](docs/SOURCE_MAP.md).

## 🗺️ Roadmap & Known limits

**Status:** the CRC32 and HMAC-SHA256 computation in this tool have been
verified byte-for-byte against the bootloader's own C implementation, and
the SocketCAN frame packing was verified against Linux's `struct can_frame`
layout with a round-trip pack/unpack test. What has **not** been tested on
either platform is a real board over real hardware — treat a first
real-world flash attempt with the same caution you'd give any new tool
talking to a bootloader: have JTAG on hand as a fallback. Everything else described here was exercised only against `MockCAN`, a simulated bootloader, never against a real board.

## 🌍 Languages

README and texts exist in English, Spanish, French, Italian, German, Chinese, Japanese and European Portuguese.

## 🔗 Related Projects

URTC is made of independent repositories, each with its own version, tests and README. This is the family, by group:

* **URTC Tool Platform:**
  * [URTC](https://github.com/JuanenRac/URTC) - firmware of the tool-head board (25 tool profiles, CAN bootloader) and the CAN protocol reference.
  * [URTC-COMMON](https://github.com/JuanenRac/URTC-COMMON) - the CAN protocol written once as data (specification, generated tables, conformance vectors) and the code the programs share.
  * **URTC-FLASHER** (this repository) - desktop tool that updates the board firmware over CAN or over SWD/JTAG.
  * [URTC-GATEWAY](https://github.com/JuanenRac/URTC-GATEWAY) - gateway in front of the CAN bus: lets only listed identifiers through, limits their rate and asks for a session key.
  * [URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK) - hardware-independent C logic and command protocol for a tool rack with pre-heating and lifecycle tracking.
  * [URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER) - desktop live CAN-bus tester that shows the controls and telemetry of the tool profile a board reports.
  * [URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL) - sensor-frame protocol in C and a Python thermal/RGB companion for an inspection tool head.
  * [URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO) - browser app that flashes and tests the board over Web Serial and SLCAN, with nothing to install.
* **Ecosystem Operations:**
  * [URTC-DEVTOOLS](https://github.com/JuanenRac/URTC-DEVTOOLS) - the shared repository tools of the family as one versioned set, with a lock file that tells a copy that was edited from one that fell behind.
  * [URTC-DOCS](https://github.com/JuanenRac/URTC-DOCS) - architecture, interfaces, security baseline and generated catalogue of the ecosystem, plus the tools that compare all repositories.
  * [URTC-UPDATER](https://github.com/JuanenRac/URTC-UPDATER) - desktop tool that detects, installs and updates the repositories of the URTC family, one explicit action at a time.

**Sister projects (independent, with the same base and tools):**

* **[HYDRA-UMC-DOCS](https://github.com/JuanenRac/HYDRA-UMC-DOCS)** - sister project: the documentation hub of HYDRA-UMC, an independent ecosystem that shares this one's base and tools
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - sister project: the documentation hub of A.R.M.O.R., the security ecosystem, also independent and on the same base
* **[JuanenRac](https://github.com/JuanenRac/JuanenRac)** - the profile and the status dashboard of all the ecosystems

## 📚 Documentation

- **[CONTRIBUTING.md](CONTRIBUTING.md)** — tech stack and coding guidelines for a pull request.
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — the standards of behavior expected in this community.
- **[SECURITY.md](SECURITY.md)** — how to report a vulnerability, and this project's own real security focus areas.
- **[SUPPORT.md](SUPPORT.md)** — where to ask questions and report bugs.
- **[LICENSE.md](LICENSE.md)** — this project's own license.

## 🤝 Contributing & Community

* Before a pull request run `URTC_CI=1 python tools/ci_validate.py`: it must pass. See [CONTRIBUTING.md](CONTRIBUTING.md) and the [code of conduct](CODE_OF_CONDUCT.md).
* The README exists in eight languages: a change to the text is made in all eight files, and the sections shared with other repositories are written by `tools/readme_sections.py` of URTC-COMMON.
* A change to the CAN protocol starts in URTC-COMMON (`spec/can_protocol.json`) and reaches this repository through the checked copy.
* Do not describe as working on a board what has only been built.
* Report a vulnerability privately: [SECURITY.md](SECURITY.md). Questions, ideas and reports: electrohobby3d@gmail.com ([SUPPORT.md](SUPPORT.md)).

## 👤 AUTHOR

**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 LICENSE

License: **GPL-3.0-or-later** for the source code, **CC BY-SA 4.0** for this
documentation - see `LICENSE` in this repository, or the "License and
Copyright Notices" section at the end of this document.

URTC Flasher is (c) 2026 JuanenRac (Electro Hobby 3D). This notice must
be included in any distributions of this project or derivative works.

This project consists of source code and its own documentation, made
available under different licenses - each suited to what it actually
covers:

1. The source code (`urtc_flasher.py` and every `flasher_*.py` module)
   and any binary built from it via `build_exe.bat`/`build_exe.sh` are
   available under the **GNU General Public License v3.0 or later (GPL-3.0-or-later)**.
   Full text at https://www.gnu.org/licenses/gpl-3.0.html.

2. The documentation (this README and its own translations -
   `README_spa.md`, `README_ita.md`, `README_fra.md`, `README_deu.md`,
   `README_zho.md`, `README_jpn.md`, `README_por.md`)
   is available under **Creative Commons Attribution-ShareAlike 4.0
   International (CC BY-SA 4.0)**. Full text at
   https://creativecommons.org/licenses/by-sa/4.0/.

This tool is the CAN-OTA/SWD-JTAG flashing companion to the
[URTC (Universal Robot Tool Controller)](https://github.com/JuanenRac/URTC)
project - see that project's own repository for the board firmware,
hardware designs, and full protocol documentation this tool implements
against. URTC's own firmware is GPL-3.0-or-later and its hardware designs are
CERN-OHL-S v2; this tool's own license here doesn't extend to that
separate project, and vice versa. A web-based alternative covering
similar ground also exists at
[URTC Web Studio](https://github.com/JuanenRac/URTC-WEB-STUDIO).

If you build on this project, keep the licensing split in mind: code
changes should stay GPL-3.0-or-later, documentation derivatives should stay CC
BY-SA - each with attribution back to this project and its author.
