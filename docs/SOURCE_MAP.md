# Source map

Every file of the repository with a line on what it does: the annotated tree that the README carried before it was reduced to the first level (the first level, in eight languages, is in the section Repository Structure of the README).

```text
├── assets/
│   ├── URTC_APP_ICON.svg          <- shared app/taskbar icon source (vector)
│   ├── URTC_LOGO_FLASHER.svg      <- banner source (vector)
│   ├── qml/
│   │   ├── FlasherDeck.qml        <- Qt Quick UI for the CAN-OTA command deck
│   │   ├── HelpDialog.qml         The quick-guide window (shared)
│   │   ├── NodePickerDialog.qml   The tool heads window (shared)
│   │   ├── UpdateDialog.qml       The Check for updates window (shared)
│   │   └── urtc_common.lock.json  Lock of the files copied from URTC-COMMON
│   ├── urtc_icon.ico              <- Windows taskbar/window icon
│   └── urtc_icon.png              <- Linux taskbar/window icon
├── firmware/
│   ├── URTC_MAIN_FIRMWARE_v<version>.bin     <- current main-board application firmware
│   ├── URTC_MAIN_BOOTLOADER_v<version>.bin   <- main-board bootloader (SWD/JTAG only, filtered out of
│   │                                         the CAN-OTA firmware list - see section 3 above)
│   ├── URTC_SLAVE_FIRMWARE_v<version>.bin    <- expansion slave application (advanced expansion boards only)
│   ├── URTC_SLAVE_BOOTLOADER_v<version>.bin  <- expansion slave bootloader
│   └── *.bin.sha256, *.bin.manifest.json  <- published digest + manifest (version, sha256, signature) of each image
├── images/
│   ├── URTC_FLASHER_BANNER.svg    <- logo banner shown at the top of this README
│   └── URTC_FLASHER_V1_1.png      <- real window screenshot, shown in the Photos section above
├── language/
│   ├── english.lng                <- default language, plain KEY=Value pairs
│   ├── spanish.lng
│   ├── italian.lng
│   ├── french.lng
│   ├── german.lng
│   ├── japanese.lng
│   ├── chinese.lng
│   └── portuguese.lng
├── logs/                           <- created automatically, one file per session
├── urtc_config.json.example        <- template for the optional urtc_config.json override file
│                                       (see "Changing the HMAC key / HardwareID" above) - copy it
│                                       to urtc_config.json and edit, rather than starting from
│                                       scratch
├── urtc_flasher.py                <- entry point: CLI arguments and start of the Qt Quick window
├── qt_flasher.py                  <- Qt Quick front end - real CAN-OTA command deck,
│                                       reuses the same transport/validation/protocol classes below
├── flasher_config.py              <- config file I/O, language loading, protocol constants
├── flasher_transports.py          <- SLCAN, SocketCAN, MockCAN
├── flasher_swd_tools.py           <- STM32CubeProgrammer / pyOCD wrappers
├── flasher_validation.py          <- firmware file validation (.bin/.hex/.elf)
├── flasher_protocol.py            <- the CAN OTA state machine itself
├── flasher_github.py              <- lists and downloads the assets of a URTC GitHub release
├── flasher_records.py             <- session logs (location, retention) and update reports
├── flasher_integrity.py           Checks before a flash is reported as done: SHA-256 and CRC-32 of the image on disk
├── flasher_release_signature.py   Release signatures (Ed25519) of the files this tool downloads or flashes
├── urtc_can/                      Shared code copied from URTC-COMMON: protocol, transports, virtual board, updates, help and the tool heads window
├── urtc_ui/                       Shared interface helpers (copy from URTC-COMMON)
├── verify_qt_device_config.py     <- real, outside-pytest end-to-end check of the Qt Quick config writes (needs a real Qt event loop)
├── verify_qt_swd_full_chip_flash.py <- real, outside-pytest end-to-end check of the Qt Quick full-chip SWD/JTAG panel (dry-run only)
├── verify_qt_can_options.py       <- real, outside-pytest check that the Qt Quick deck loads and that the CAN-OTA options behave (target, downgrade, backup)
├── tests/
│   ├── conftest.py                 <- gives the protocol tests a bench signing key
│   ├── test_firmware_signature.py  <- 7 tests: published signature, unsigned image refused, preflight digests, bundled firmware/
│   ├── test_flash_protocol_dispatch.py <- 8 tests, against a real simulated MockCAN bootloader
│   ├── test_flash_verify_fail_reporting.py <- 8 tests
│   ├── test_flasher_integrity.py   <- 14 tests
│   ├── test_flasher_protocol_clock.py <- 4 tests
│   ├── test_qt_flash_preflight.py  <- 2 tests (skipped without PySide6) - all run by GitHub Actions CI
│   ├── test_bitrate_listen_only.py
│   ├── test_bootloader_entry.py
│   ├── test_can_conformance.py   <- shared CAN vectors (tests/fixtures/can_conformance_vectors.json)
│   ├── test_github_download.py
│   ├── test_pinned_release.py
│   ├── test_language_files.py
│   ├── test_manifest_target.py
│   ├── test_mock_readback.py
│   ├── test_ota_partial_page.py
│   ├── test_patch_number.py
│   ├── test_python_can_transport.py
│   ├── test_qt_bridge_log.py
│   ├── test_qt_connection.py
│   ├── test_qt_firmware_files.py
│   ├── test_qt_flash_options.py
│   ├── test_qt_log_translation.py
│   ├── test_readback_odd_size.py
│   ├── test_records.py
│   ├── test_signing_policy.py
│   ├── test_slave_entry_check.py
│   ├── test_slave_flash.py
│   ├── test_swd_tools.py
│   ├── test_sync_firmware.py
│   ├── test_validation_ccm_stack.py
│   ├── test_validation_formats.py
│   ├── test_version_report.py
│   ├── test_*.py             Plus one file per other area: the Qt window, the language files, the window guide, the virtual board, the release signature and the update dialog
│   └── fixtures/             Vectors shared with the other programs and recorded traces
├── requirements.txt                <- pyserial>=3.5 + PySide6>=6.8,<7
├── requirements-dev.txt / requirements*.lock Dependencies of the tests and of the build, closed with hashes
├── mypy.ini / ruff.toml / pytest.ini Settings of the type check and of the static checks
├── urtc_i18n.lock.json             Lock of the language files generated from the catalog of URTC-COMMON
├── urtc.project.json               Project manifest (version, maturity, evidence)
├── run.bat / run.sh                Start the program
├── build_exe.bat                  <- Windows standalone build
├── build_exe.sh                   <- Linux standalone build
├── build-test.bat                 <- non-versioning build/compile check
├── build-test.sh                  <- same, for Linux
├── bump.py                        <- Explicit version bump command (building never bumps)
├── bump_version.py                <- version bump, called by bump.py
├── bump_manifest_version.py       <- syncs urtc.project.json's version to the native one (--sync)
├── docs/
│   ├── CLI_REFERENCE.md           <- command-line flags reference
│   ├── WINDOW_GUIDE.md            The window step by step, with real pictures in the eight languages
│   └── screenshots/               The pictures of the window guide, in the eight languages
├── tools/
│   ├── build_test.py                     <- non-versioning compile + Qt Quick deck source check
│   ├── ci_validate.py                    <- manifest/CHANGELOG/docs validation used by CI
│   ├── sync_firmware.py                  <- refreshes firmware/ from the assets of a URTC release or a local folder (digests checked; --check verifies)
│   ├── capture_screens.py                Takes the pictures of the window guide without a screen (one language or all)
│   ├── make_update_package.py            Builds and signs the update package of a release
│   └── _doc_policy.py / _readme_parity.py / _tracked_names.py Shared checks used by ci_validate.py
├── README.md                      <- this file
├── README_spa.md / README_ita.md / README_fra.md / README_deu.md / README_zho.md / README_jpn.md / README_por.md  <- translations
├── LICENSE
├── NOTICE                      Copyright notice and the license of the documentation
├── .gitattributes
└── .gitignore
```
