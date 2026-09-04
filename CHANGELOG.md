# Changelog

All notable changes to URTC Flasher are summarized here. This file tracks
**this tool's own version** (`FLASHER_VERSION` in `flasher_config.py`, shown
in the window title bar and the Help > About dialog) - it is tracked
separately from the URTC board firmware version this tool writes to a
connected board.

This is a condensed summary of real development history; the full
day-by-day internal record (audits, bugs found and fixed, verification
methodology) lives in the project owner's private internal log and is not
published here.

## Versioning scheme

Starting with this entry, `FLASHER_VERSION` follows an ecosystem-wide
`MAJOR.MINOR.PATCH` scheme (three parts, always). `PATCH` increments by 1
automatically on every real packaged build (`build_exe.bat` on Windows,
`build_exe.sh` on Linux) via `bump_version.py`, which both scripts now run
right before invoking PyInstaller. The increment is an odometer-style
base-10 carry: if `PATCH` would go past 9 it resets to 0 and `MINOR`
increments instead (e.g. `0.1.9` -> `0.2.0`), and the same carry applies
from `MINOR` into `MAJOR`. Running the tool from source (not through a
build script) never changes the version - only a real build does.

## [Unreleased]

### Added
- **Real About window**, matching HYDRA-UMC-STUDIO's own `About.tsx` and
  the ecosystem's PySide6 tools: the Tkinter About window now shows a
  tagline, a one-paragraph description, and a real Version/Author/Email/
  License info block, not just a banner and one line of text. New
  `TITLE_ABOUT`/`ABOUT_TAGLINE`/`ABOUT_DESCRIPTION`/`ABOUT_VERSION`/
  `ABOUT_AUTHOR`/`ABOUT_EMAIL`/`ABOUT_LICENSE` keys across all 7
  languages, replacing the old `LBL_ABOUT_AUTHOR` - full key parity
  verified across every language file.

### Fixed
- `qt_flasher.py`'s SWD probe scan shadowed the module-level `serial`
  import with a loop variable of the same name (`for serial in
  CubeProgrammerCLI(...).list_probes()`) - harmless in that one function
  today, but a real footgun for whoever edits it next expecting `serial`
  to still mean the pyserial module. Renamed to `probe_serial`.
- `flasher_gui.py`'s manual serial connect crashed with `NameError:
  BITRATE_500K_SLCAN_CODE` whenever the saved bitrate label didn't match a
  known entry (a blank or corrupted config value) - the constant was used
  as a fallback but never imported from `flasher_config`.
- The GitHub firmware-browser dialog's error handlers (`_load_list` and
  `_do_download`) crashed with `NameError` reporting a download/list
  failure: each `except ... as e:` scheduled a `lambda` referencing `e` via
  `root.after()`, but Python deletes the exception variable the moment the
  `except` block exits, before the deferred lambda ever runs. Fixed by
  capturing the message into a plain string first, the same pattern
  already used correctly elsewhere in this file (see the `_connect_worker`
  comment).

### Added
- The Qt Quick deck now includes a **Board snapshot** action after an active
  CAN connection. It performs only the existing documented version, counter
  and peripheral read queries and renders their responses in the deck; it
  cannot alter firmware, persistent board configuration or option bytes.
- The Qt Quick deck now exposes an **Advanced diagnostics** card for
  non-destructive SWD/JTAG readiness: it reports the actual local pyOCD and
  STM32CubeProgrammer executables and can enumerate USB debug probes through
  their existing listing commands. It intentionally does not connect to,
  erase, write or reset a target; full-chip SWD/JTAG programming remains in
  the established Tkinter workflow pending physical validation.
- The Qt Quick CAN-OTA flow snapshots the selected firmware before its worker
  starts and locks firmware/transport selection while an operation is active.
  A running update therefore cannot silently switch to another file from the
  visible inventory.
- The Qt Quick transport selector now recognises the actual discovered
  SocketCAN interface set instead of guessing from names such as `can0`.
  This also handles valid interfaces such as `vcan0`. Combining `--cli`
  and `--qtquick` is rejected explicitly because they are separate modes.
- Qt Quick worker logs are now marshalled back to the GUI thread before the
  QML log model is updated. This removes a possible cross-thread UI race
  during connection and CAN-OTA progress. Selecting `--qtquick` without
  PySide6 now reports the missing dependency clearly instead of exposing an
  import traceback.
- An explicit Qt Quick CAN-OTA command deck is now available with
  python urtc_flasher.py --qtquick. It is a real front end over the
  established SLCAN/SocketCAN transports, firmware validation and signed
  URTCFlasher protocol: port discovery, connection, firmware selection,
  cancellation, progress and outcome logs are not simulated. The established
  Tkinter UI remains the default until its advanced SWD/JTAG and
  board-configuration workflows have equivalent Qt Quick pages.
- PyInstaller build scripts now collect the Qt Quick/QML runtime and the
  staged command-deck entry point. This prevents a packaged executable from
  silently omitting the renderer selected by --qtquick.
- A full dark navy/cyan command-deck presentation now wraps the established
  flashing UI: product/status header, real 16px rounded canvas cards on the
  connection, CAN-OTA, SWD/JTAG and log surfaces, 10px curved primary actions,
  plus coherent tab surfaces,
  high-contrast controls, readable firmware table and a dark monospace
  verification log. It is visual-only; CAN-OTA/SWD command and safety flows
  are unchanged.
- The fixed connection panel now displays the official animated HYDRA-UMC
  mark. Tkinter plays twelve bundled PNG frames rendered from
  `assets/HYDRA_UMC_ICON.svg`, so the source run and PyInstaller executable
  show the same visual identity without adding a heavyweight GUI dependency.
  The URTC-specific native window/taskbar icon remains static and unchanged.
- `tools/render_hydra_umc_icon_frames.py` regenerates those frames with
  PySide6 when the source SVG changes; PySide6 is a development-only renderer,
  not an application runtime requirement.
- Chinese and Japanese added to the Language menu: new `language/chinese.lng`
  (简体中文) and `language/japanese.lng` (日本語), full translation of all 331
  keys, matching the coverage of the existing english/spanish/italian/
  french/german files. Added to `flasher_config.py`'s own `AVAILABLE_LANGUAGES`
  list, which the Language menu builds from dynamically - no other UI code
  needed changing. Verified two ways: a real `load_language()` call for both
  new files confirmed all 331 keys present with zero gaps or extras against
  `english.lng`, and a real Tkinter `FlasherGUI` instantiation confirmed
  both new entries render correctly in the actual Language menu alongside
  the other 5. New `README_zho.md` / `README_jpn.md` documentation
  translations, plus the 5 existing README files' language selectors
  updated to link them. Doesn't bump `FLASHER_VERSION` on its own - this
  project's own versioning convention only advances it on a real
  `build_exe.bat`/`build_exe.sh` packaged build.

### Fixed
- SLCAN reception now rejects impossible CAN 2.0 DLC values (`9`-`F`) before
  they can be exposed to the flashing protocol. Valid standard and extended
  frames remain parsed exactly as before.

## [0.1.2]

- **Converted every remaining `ttk.Button` in `flasher_gui.py` to the
  app's own `RoundedDeckButton`** (20 call sites) - the real, larger
  follow-up v0.1.1's own changelog entry named. One real special case:
  the GitHub firmware-browser dialog's own `download_btn` started with
  no `command` at all (wired later via `.config(command=...)` once a
  real selection exists) - `RoundedDeckButton` requires a `command` at
  construction, so this one call passes `command=None` explicitly;
  verified directly that a `None`-command button stays inert while
  disabled and a later `.config(command=...)` correctly takes over.

## [0.1.1]

- **Same real fix as URTC-TESTER's own v0.1.2** (real user feedback,
  button shapes and header not fully matching HYDRA-UMC-UPDATER's
  visual language despite `RoundedDeckCard`/`RoundedDeckButton`
  already existing for exactly that purpose). Refresh, Auto-Detect,
  Export Debug Bundle, and the License/About dialogs' own Accept/Close
  converted from plain `ttk.Button` to the app's own `RoundedDeckButton`.
  The animated HYDRA-UMC mark moved from inside the Connect card into
  the header row itself, directly left of the "URTC Flasher" wordmark.
  Many more `ttk.Button` calls remain across the flashing/SWD panels -
  not converted in this pass, a real, larger follow-up.

## [0.1.0]

### Added
- Ecosystem-wide build-versioning policy: `FLASHER_VERSION` normalized from
  the old two-part `"0.1"` to the three-part `"0.1.0"`, and `bump_version.py`
  added to auto-increment it on every real build (see "Versioning scheme"
  above). Wired into both `build_exe.bat` and `build_exe.sh` as a new step
  right before compiling.
- This CHANGELOG.md.

## [0.1]

Visual/text version bump (banner SVGs, splash text) from v0.0 to v0.1,
plus a full pass fixing every leftover "v0.0"/"0.0" reference across the
project (build banners, README screenshots and examples, `/images/` gallery
duplicates) that earlier passes had missed - including some caught only
after the user reported still seeing "v0.0" post-migration.

### Added
- Full README documentation for the Flasher, in all 5 supported languages
  (English, Spanish, Italian, French, German).
- 2-column redesign of the CAN-OTA tab (firmware/flashing on the left,
  free-tool configuration + peripheral info on the right), measured
  before/after under Xvfb across all 5 languages.
- Firmware download directly from GitHub (`flasher_github.py`), with a
  progress dialog and atomic temp-file-then-rename downloads.
- CAN-OTA flashing of the expansion slave board over its I2C bridge
  (0x210-0x218), including the "This board (main) / Expansion slave"
  target selector.
- SWD/JTAG full-chip flashing of the expansion slave chip, with its own
  (genuinely different) flash memory map verified against the real linker
  scripts rather than assumed to mirror the main board.
- MLX9064x sensor variant selection/query (0x1A6/0x1A7) and Free Tool
  Configuration / Peripheral Type & Serial Number sections in the CAN-OTA
  tab.
- 5-language selector (English/Spanish/Italian/French/German) replacing
  the original binary English/Spanish checkbox; full internationalization
  of the whole GUI (217 translation keys x 5 languages).
- Tabbed 2-tab UI (CAN-OTA / SWD-JTAG) replacing the original 2-column
  layout, to stop the window growing past a 1080p screen.
- Full Help menu (Readme / GitHub / License / About), replacing scattered
  entries, with per-language README selection.

### Fixed
- **Critical**: SWD backup-before-flash used the `-r32` STM32CubeProgrammer
  flag, which (confirmed against official ST documentation) only ever
  dumps to screen and never accepts an output file - full-chip SWD backups
  were silently failing every time, and the tool correctly refused to
  proceed with erasing without a successful backup, so full-chip flashing
  could never complete at all. Fixed to the correct `-r` flag.
- **Critical**: `-c` probe-selection parameters were passed to
  `subprocess` as separate arguments instead of one combined string,
  breaking selection of a specific probe by serial number.
  10 further real bugs fixed in the same audit pass: byte-at-a-time SLCAN
  reads, a BELL character corrupting valid CAN frames, an uncaught
  `struct.error` in the SocketCAN path, a socket descriptor leak on a
  failed `bind()`, unquoted pyOCD paths breaking on spaces, blind
  `probe_uid` verification, false positives in Option Bytes parsing, an
  ignored Intel HEX record type with no checksum verification, a timeout
  loop that could block, and a Windows probe search limited to `HKLM`
  only (now also checks `HKCU`).
- `flasher_github.py` missing from both build scripts' `--hidden-import`
  list - would have failed with `ModuleNotFoundError` at runtime in a
  compiled `.exe`/binary despite working fine from source; verified with a
  real PyInstaller build, not just a code read.
- `TOOL_NAMES` in `flasher_config.py` had its own stale copy of the tool
  list (12 entries) that never picked up the Tester's later expansion to
  25 - user-reported in real use, fixed by syncing the list.
- Post-write SWD verification (`commander -c compare`) for the expansion
  slave was comparing against the *main board's* flash addresses instead
  of the slave's own, which would have reported a false mismatch even
  after a successful slave flash.
- Several smaller real bugs: undefined `CAN_ID_SET_EXPANSION_TYPE`/
  `CAN_ID_EXPANSION_TYPE_RESP` imports, a stale hardware ID lingering in
  the expansion-board type list, an outdated `> 4` range check that
  rejected the 2 newest expansion board types, an uncaught `AttributeError`
  on a malformed `manifest.json`.

### Changed
- Split the single 3603-line `urtc_flasher.py` into 7 focused modules plus
  a thin entry point, purely for readability.

## Earlier history (pre-1.1, no formal version tags)

- Standalone-binary packaging via PyInstaller (`build_exe.bat`/`build_exe.sh`)
  for Windows and Linux.
- CAN OTA flashing of the main board over SLCAN/SocketCAN, with page-ACK
  progress tracking, HMAC-signed updates, and anti-rollback / HardwareID
  checks.
- SWD/JTAG full-chip flashing of the main board via pyOCD or
  STM32CubeProgrammer, with an optional full-flash backup before erasing.
- Manifest-based (`manifest.json`) pre-flash sha256/version/build-date
  verification.
- Background-threaded connection handling so opening a port never blocks
  the GUI.
- A mock/simulated CAN transport (`--transport mock`) for CI and
  reproducible testing without real hardware.
- Physical bus diagnostics heuristics (e.g. flagging missing 120-ohm
  termination as a likely cause of framing errors).
