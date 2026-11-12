# Changelog

All notable changes to this project are documented here.

## [Unreleased]

- **The package tool signs the package the Windows build makes:** `tools/make_update_package.py sign PACKAGE` (the copy of URTC-COMMON's tool, refreshed) signs the very bytes of the `.zip` that the manual Windows build in Actions packs without a key, after checking that the `app_info.json` inside agrees with the name of the file, and writes `PACKAGE.sha256` and `PACKAGE.sig` next to it; it then runs the same check the program runs. The package is never rewritten, so the attestation of the build still describes the bytes that are signed. A test checks that the companions are byte for byte the ones a signed build writes.

- **The flasher reads the header inside the image before it sends a frame:** an image built with the header slot sealed states its hardware, version, length and CRC-32 inside the file; the flasher refuses an image for another board (main or expansion slave), a version that differs from the file name, a length or CRC-32 that does not match, a header nobody sealed, and a stamped `.urimg` file, and logs the identity it read. Nothing is sent when it refuses.

- **`image_header_policy` in `urtc_config.json` is the compatibility switch for an image without the header:** `warn` (the default) flashes it and says its identity could not be checked, `accept` flashes it silently, `require` refuses it; any other value means `require`. A header that is there is always checked.

- **The messages of the header check are in the eight languages** (the shared catalog of URTC-COMMON).

- **The German README addresses the reader formally in the contributing list:** the three lines that still used the informal form now use the same formal form as the rest of the text and as the other repositories.

- **The simulated readback tests no longer depend on the speed of the computer:** the simulated board answers at once in the readback tests, so the whole file runs in about one second instead of ten and cannot time out on a busy machine.

## [0.5.5] - The Spanish texts say "grabar" and "velocidad de bus": the calques "flashear", "flasheo" and "bitrate" are replaced in the window, the guide, the Spanish README and the shared sections, with the gender of the sentence... (and 7 more changes)

- **The Spanish texts say "grabar" and "velocidad de bus":** the calques "flashear", "flasheo" and "bitrate" are replaced in the window, the guide, the Spanish README and the shared sections, with the gender of the sentence corrected, so the README names what the window shows.

- **The manifest says which version of the shared contracts it needs:** `min_common` in `urtc.project.json` is the oldest version of URTC-COMMON among the copies this repository carries, the value the updater compares with what is installed (a warning only). `tools/min_common.py` of URTC-COMMON checks it and a new copy brings it up to date.

- **The note on the Qt Quick deck no longer swallows the next paragraph in the Spanish, German, French and Italian READMEs:** a blank line was missing after the quoted note, so the paragraph about the transport choice was drawn inside the quotation.

- **The README quotes the buttons as the application shows them:** `Flash Complete Chip`, `Auto-detect`, `Browse .bin...`, `Check Option Bytes`, `Target chip:`, `Connect` and `Refresh` are written in each language as the language file of the application has them (Portuguese and the four languages that still had the English name of the chip button).

- **The copy of the CAN identifiers and vectors is refreshed:** the shared tables now list `0x1BC` (ask for the crash record) and `0x1BD` (the six frames of the record), the identifiers a firmware built with the crash capture answers; this program neither sends nor reads them.

- **The README states how many tests need PySide6, as measured:** the 830 tests all pass with PySide6 (820 passed and 10 skipped for other reasons) and 719 pass without it, so 101 of them need PySide6 (the earlier figure of 73 was not what the runs show).

- **The pause between the data frames of a transfer is a setting:** `frame_gap_ms` in `urtc_config.json` (a number of milliseconds, default 1.0, from 0 to 50; 0 sends the frames back to back). A value that is not a number or lies outside the limits falls back to the default and the log says why. The measured speed of every page and of the whole transfer is already in the log, so a value can be tried and compared. New tests cover the limits, the fall-back, the example file and that the transfer uses the value.
- **The copies of the shared repository are refreshed:** the generated protocol module, the user-interface helpers, the vectors, the tools and the signature file name table (`.imgsig`) are at the current version of URTC-COMMON again.

## [0.5.4] - Tests of an update that is cut or damaged half way: the adapter unplugged during the transfer, a board that stops hearing, a lost or repeated page acknowledgement and a bus that dies after the end of the update are played... (and 4 more changes)

- **Tests of an update that is cut or damaged half way:** the adapter unplugged during the transfer, a board that stops hearing, a lost or repeated page acknowledgement and a bus that dies after the end of the update are played against the simulated bootloader behind a bus scenario; none of them can end in a finished progress bar. The copy of the shared transports now ignores a start frame cut short, as the bootloader does.

- **Both signing keys are shown while a rotation is in progress:** before an update the flasher asks the bootloader which keys it trusts (`0x7EA` operation `05`), writes both fingerprints and the minutes left of the window in the log, accepts an image signed with either of them and warns when it uses the previous one; a revoked current key is said too. Anything ambiguous (several different answers, a count that does not match) is treated as no data. Tried against the virtual bootloader; texts in the eight languages.

- **The copy of the CAN protocol (generated module and conformance vectors) is refreshed:** it now includes the key rotation status frames (operation `05` of `0x7EA` and its seven-byte answer on `0x7EB`). Nothing in this program sends or needs them yet.

- **The repository check compares the manifest with what can be computed:** `tools/ci_validate.py` now also runs the shared `tools/sync_manifests.py` offline, which compares the shipped version, the newest released heading of this changelog, the presence of tests and the claimed level of evidence with the manifest. It is part of the shared set of tools, so the copy is pinned by the lock.
- **The window compares the firmware folder with the newest official release:** the dialog that lists the files of a release has a button that says, image by image, whether `firmware/` holds the images of the newest official release (up to date, older, newer or missing), in the language of the window. It asks GitHub once, only when pressed, keeps the answer for an hour and downloads nothing.

## [0.5.3] - The firmware in the firmware/ folder can be compared with the newest official release: python tools/syncfirmware.py --newer (with --language for the text in one of the eight languages and --refresh to ask again) says, image by... (and 2 more changes)

- **The firmware in the `firmware/` folder can be compared with the newest official release:** `python tools/sync_firmware.py --newer` (with `--language` for the text in one of the eight languages and `--refresh` to ask again) says, image by image, whether it is up to date, older, newer (a test build) or missing. It makes one request to GitHub, keeps the answer for an hour so the anonymous limit is not spent, does not repeat a failed request within a minute, downloads nothing and exits with 1 when an image is older or missing. The check is the shared `firmware_check` of URTC-COMMON (copied with its texts), and `tests/test_firmware_newer.py` holds it.
- **The release list reads the official release and nothing else:** the window and `tools/sync_firmware.py` take GitHub's "latest" release of URTC (an official one exists now); the fallback to a release named in a `firmware_release.json` file, its reader, its test and its log line (in the eight languages) are gone. A release is chosen by its tag in the window or with `--release`.
- **The key check before the transfer uses the key named by the signature record:** the first eight bytes of the `.imgsig` next to the image are the fingerprint of the key that signed it, so they are compared with the fingerprint the bootloader publishes and win over the key an older manifest declares; an image with a record and no key in its manifest is now compared too. A file that is not a record still stops the transfer with its own message. Host tests cover a match, a mismatch, the record over the manifest and a malformed record.

## [0.5.2] - An official release synchronizes without hmacsha256: tools/syncfirmware.py accepts an application image whose .imgsig record is there (152 hexadecimal digits on one line) with a manifest that has no hmacsha256, because the... (and 1 more changes)

- **An official release synchronizes without `hmac_sha256`:** `tools/sync_firmware.py` accepts an application image whose `.imgsig` record is there (152 hexadecimal digits on one line) with a manifest that has no `hmac_sha256`, because the images of the current generation of bootloaders are signed with the Ed25519 record and carry no HMAC. The HMAC is still required of a set of the earlier generation that has no record; an image of an official release (`signing_key_kind` `release`) without its record is refused whatever the manifest says, and so is a record that is not 152 hexadecimal digits. The sync downloads the `.imgsig` of each application image and its release signature, refuses a wrong signature, and keeps both in `firmware/` next to the image. Tests for a set with the record and without the HMAC (accepted), without either (refused), an official image without its record (refused), corrupt records (refused) and the signatures of the records.
- **The text helpers and the simulated soldering iron are tested:** 87 new tests cover the identifier, frame, bitrate, size, duration and uptime text (every spelling it reads, every value it refuses) and the iron of the virtual board (parameter file and fall-backs, heating curve, ceiling of the target, watchdog, anti-windup, telemetry frame); the coverage floor of the CI follows the measurement (about 68 %), from 61 % to 67 %.

## [0.5.1] - The full build check compiles only on CI or when allowed: tools/buildtest.py prints BUILDTEST=SKIPPED (exit status 2) for the stacks that compile unless it runs on a CI runner or ALLOWLOCALBUILD=1 says so; the light check is... (and 7 more changes)

- **The full build check compiles only on CI or when allowed:** `tools/build_test.py` prints `BUILD_TEST=SKIPPED` (exit status 2) for the stacks that compile unless it runs on a CI runner or `ALLOW_LOCAL_BUILD=1` says so; the light check is not locked.

- **The virtual board refuses to compile on a plain PC:** the copy of the shared virtual board carries the lock on local builds (a CI runner, or `ALLOW_LOCAL_BUILD=1`, may build); the test of the bootloader twin is skipped with that reason elsewhere.

- **A workshop tool makes the signed command that programs the serial number of a bootloader:** `tools/serial_command.py` takes the unique ID of the head, the serial it answers with now, the new serial and a counter, signs them with the seed in a key file that the person names (it never looks for a key by itself) and prints the twelve SLCAN lines of `0x7EE` and the answer to expect on `0x7EF`; without `--yes` it only describes what it would make. The copy of the shared code gains the reference of the command (`bl_serial.py`, with the Ed25519 it needs); the tests sign with ephemeral keys. Nothing is sent from here.
- **The build check of the repository is one text for the whole family, with a light mode that CI runs:** `tools/build_test.py` is the same file in every repository of the family (taken from the shared set); what used to differ between its seven variants is data in an optional `tools/build_test.json`. `python tools/build_test.py --check` looks at the manifest, the stack and the files the full check needs and compiles the Python sources, builds and runs nothing, and the baseline step of the workflow now runs it.
- **The test against the real bootloader runs with a signature record:** `tests/test_bootloader_twin.py` flashes the patterned image of the case that the firmware repository signed with the public development seed (the bench table of the twin trusts that key), with its `<image>.imgsig` next to it, and checks that a record with one bit changed is refused. It was skipped while the flasher sent no record; it runs where the firmware repository and a host compiler are present, as before.
- **The README files describe what the bootloaders check now:** the main-board bootloader verifies an Ed25519 record against a table of public keys and holds no secret, the expansion-slave bootloader checks a plain SHA-256 and installs only an image that the main board confirms; the HMAC of the manifest is described as what bootloaders of the earlier generation check. Eight languages.
- **The signature record travels with the image, for the main board and for the expansion slave:** the flasher reads `<image>.imgsig` (the 76-byte Ed25519 record as 152 hexadecimal digits; also `<name>.imgsig` beside `<name>.bin`) and sends it in 11 frames, `0x7EC` to the main-board bootloader and `0x21A` to the expansion slave (through the main board, which verifies it and confirms the image). The `0x212` frames to the slave now carry the plain SHA-256 of the image, because the slave bootloader holds no key and no HMAC routine any more; an image without a record is refused for the slave before any frame is sent, and a file that is not a record (wrong length, not hexadecimal) is an error and never ignored. For the main board the HMAC chunks are only sent when a published or configured HMAC exists (bootloaders of the earlier generation); a record is enough for the current one. The option `slave_hmac_key_hex` of `urtc_config.json` is read and no longer used. Five messages in the eight languages. The copy of URTC-COMMON is refreshed (the two new identifiers and the registers of the slave rollback counter).
- **The test count in the "At a glance" table of the README is the real one:** the number was counted by collecting the tests of the suite and written into the eight READMEs.

## [0.5.0] - The check of the signing key reads the fingerprint from 0x7ED and a missing fingerprint is never reported as a difference, the README shows screenshots of the windows and the texts of the serial number are in eight languages

- **The screenshots of the README are listed in `docs/screenshots.json`:** each picture has a short name and a caption in the eight languages, the README section is written from that file, and `tools/capture_screenshots.py` takes the pictures again without opening a window on the desktop.
- **The signing key is checked before the transfer:** a bootloader that publishes the fingerprint of the signing key it accepts (its identifier travels on `0x7ED`, see below) is compared with the `signing_key_id` of the image manifest, and a mismatch is logged before a single data frame goes out. `key_id_precheck` in `urtc_config.json` is `warn` by default, `refuse` stops the update and `off` skips the check; a bootloader or a manifest without the fingerprint is never a mismatch. Tried against a simulated bootloader only; no bootloader publishes the fingerprint yet.
- **The key check reads the fingerprint where a bootloader can send it:** the check that compares the signing key a bootloader accepts with the key of the image read a `0x7FA` frame of eleven bytes, which cannot exist on a classic CAN frame (eight data bytes at most), so it never worked. It now reads the eight bytes of `0x7ED`, sent right after the answer to the version query, in either order; `0x7FA` is read only at its three bytes.
- **A bootloader without the fingerprint gives no data:** an older bootloader, one without a key, an application, a frame of the wrong length or several heads with different keys give "unknown" (the log says once that the key is not compared), never a difference and never an error; `key_id_precheck` keeps `off`, `warn` (the default) and `refuse`.
- **Copies of the shared specification refreshed:** the identifiers `0x7EA` to `0x7ED` and the conformance vectors, and the new log line in the eight languages.

## [0.4.9] - The flasher is tested against the real bootloader built for the host and the virtual board can be the receive path of the firmware itself

- **The flasher is tested against the real bootloader:** the copy of the virtual board from URTC-COMMON takes `--firmware-bootloader` (with `--firmware-repo`), which starts the bootloader of the master compiled for the host, and two new tests flash a signed image through it (the manifest names the board, the hash and the signature) and check that a signature with one bit changed is refused. They need the URTC repository next to this one (or `URTC_FIRMWARE_REPO`) and a host C compiler, WSL on Windows; the CI of this repository clones it.

- **The virtual board can be the firmware's own receive path:** the copy of the virtual board from URTC-COMMON 0.1.6 takes `--firmware-repo DIR` (`python -m urtc_can.virtual_board --firmware-repo ../URTC`, with a checkout of the URTC repository and a host C compiler, or WSL on Windows), builds the firmware's `tests/virtual_board.c` and bridges the SLCAN port to it; the port URL it prints goes in `URTC_VIRTUAL_PORT` or `--port` as before.

## [0.4.8] - The shared evidence code accepts the outcome unknown and a plan of the update can be run without a bus

- **The shared evidence code accepts the outcome `unknown`:** a record whose result could not be decided (written by the tester when a check has no evidence either way) is read and listed as valid, and the history and the report say it in the eight languages (Portuguese of Portugal).
- **A plan of the update without a bus:** `--cli --check-only --file IMAGE` (with `--json` for a document) checks an image and prints the steps of the update without opening a bus, asking for a port or sending a frame: the plausibility of the file, the published digest, the release signature, the version, the size, the SHA-256, the CRC32 and the steps of the protocol in order. Exit 0 when the flasher would go on with the image and 2 when it would refuse it; the update itself is unchanged. `docs/CLI_REFERENCE.md` says what it does not do.

## [0.4.7] - The History window is in the pictures of the README in the eight languages

- **The History window is in the pictures of the README:** the Screenshots section also shows the window of the history of operations (every record checked on its own, with the Signature column that says whether it is signed, by which of your keys, or not valid), in the eight languages of the README. The picture is taken over sample records, on a bench, with no real installation behind.

## [0.4.6] - The flasher signs its evidence records like the tester, with a switch in the window, a Signature column in the history, the store of trusted keys and a screenshot of the history

- **The flasher signs its evidence records like the tester does:** with `"sign_evidence": true` in the config file (off by default; the key in `record_key_file`, else the default of the family, never printed) the evidence record of an update, and of a run against a simulated bus, carries an Ed25519 signature; if signing fails no evidence file is written and the log says why. `sign_update_reports` is a different switch and stays as it was.
- **The deck has the switch to sign the evidence:** a check box, "Sign the evidence records of this flasher with my Ed25519 key", turns the `sign_evidence` setting on and off (off by default; it is saved in the config file), in the eight languages (Portuguese of Portugal); if the setting cannot be saved the log says so and the box does not claim to be on.
- **A trust store of public keys:** `"trusted_keys": {"alias": "<public key>"}` in the config file makes `--history` and the History window say "Signed by <alias>" or "Valid signature, unknown key"; `--public-key HEX` wins over the store. The History window has a Signature column. The shared copy and its lock files are synchronized.
- **Pictures of the History window:** `tools/capture_screens.py` now also takes the History window (over four sample records and one trusted key, so the Signature column shows each state) in the eight languages, `docs/WINDOW_GUIDE.md` shows it, and the other pictures were taken again. The window's columns were narrowed so the Signature column is not cut off.
- **The PDF report prints more Chinese and Japanese names:** the shared font data now holds both levels of GB 2312 and of JIS X 0208 (6763 hanzi and 6355 kanji) besides the text of the catalogs; Traditional Chinese forms and rare kanji still print as the visible square with the note that counts them. A PDF with Chinese or Japanese text grows from about 0.6-0.74 MB to about 1.2-1.3 MB (a report without such text embeds no font) and the module of the font data from 1.97 MB to 3.71 MB; the shared copy and its lock file are synchronized.

## [0.4.5] - The shared evidence modules accept the optional Ed25519 signature of an evidence record

- **The shared evidence modules accept the optional Ed25519 signature of an evidence record:** a signed record keeps its digest and is no longer refused for the extra field; the history lists the state of each signature (matches, does not match, not signed) and the HTML and PDF report show it in the eight languages (Portuguese of Portugal). The flasher already signs its update report; its copy of the evidence modules now lists and checks the signature of an evidence record in the history and the report. The copies and their lock files are synchronized with the shared repository, and the font data of the PDF report was regenerated.

## [0.4.4] - The reply of the tool rack has a fixed CAN identifier, the PDF of the evidence report prints Chinese and Japanese, the history no longer lists other files as not valid and an update can run against a faulty simulated bus

- **The reply of the tool rack has a fixed CAN identifier, `0x261`:** the shared protocol copy has the rack frames (the pre-heat order `0x260` and the reply `0x261`), and the bus scenario `reject` no longer needs `reply_id` (it sends the reply on `0x261`; another identifier can still be named). The conformance fixtures cover both frames.
- **The PDF of the evidence report prints Chinese and Japanese:** the file embeds a subset of Noto Sans CJK (SIL Open Font License 1.1, see `NOTICE`) as a Type0 / CIDFontType2 font, so the text can be selected and searched; Western reports still use Courier. A character the subset lacks is printed as a hollow square and the report says how many were replaced (no more silent `?`). Copies of the shared report module and its font data are synchronized.
- **The history of the flasher no longer lists the files that are not evidence as NOT VALID:** The update report (`urtc_update_report_<time>.json`) shares the folder with its evidence record (`urtc_evidence_<time>.json`) and was counted as a record that fails its check. The shared history recognizes them by their shape (never by the file name), counts them apart as "other records" and lists them by name and type in the text, in the JSON (`others`), in the History window (a counter and a list) and in the report, in the eight languages; the exit status of the history is 0 when there is only valid evidence and other records, and JSON of any other shape stays NOT VALID. The copies of the shared code were synchronized (`history_qt`, `history_qml` and `report`, with their locks).
- **Run an update against a faulty simulated bus:** `--cli --transport mock --scenario FILE` (with `--seed N` and `--evidence-dir DIR`) puts the bus scenario of `urtc_can/bus_scenario.py` between the program and the in-memory bootloader, on a virtual clock (the timeouts of the protocol count virtual seconds, so a lost frame costs no real waiting). Whether the update succeeds or fails, the run writes the update report and a `urtc-evidence/1` record that says the bus was a simulation, with the scenario, its seed and what it did; the report is not signed. It is off unless given and is refused with a real adapter; a scenario that is not valid runs nothing. The quick guide says so in the eight languages.


## [0.4.3] - A History window with the operations of the flasher, the evidence of the updates listed from the command line, an out-of-range HardwareID no longer kept and the lights of Project status following the evidence

- **The Help window has a History step and the README describes the History window:** the quick guide (eight languages) says what the History button shows, the Interfaces section of the README in the eight languages describes the window and its command line form, and `docs/WINDOW_GUIDE.md` has a History section.
- **An out-of-range HardwareID in the configuration file is no longer kept:** a `hardware_id` above 32 bits was reported as skipped but still replaced the built-in value; now it is checked first and the default stays.
- **A History window with the operations of the flasher:** a new button next to Help opens the history of operations, the same window as in the tester and the updater (shared from URTC-COMMON, in the eight languages): it lists the records the flasher wrote in its logs folder, newest first, with the kind, result, tool, board and versions, and marks as not valid a record that was edited after it was written or a file that is not a record. It can be filtered by result and text, reads only, and changes nothing on disk. The tool that prints the notes of a release (`tools/changelog_section.py`, with `--compat` it adds the compatibility table of `docs/COMPATIBILITY.md`) travels with the program.
- **The lights of Project status follow the evidence of the manifest:** the manifest says how far the repository has been shown to work (`evidence`: `host-test`, `simulator`, `bench` or `field`) and the validator fails when a light is above what that evidence and the maturity allow (`tools/status_lights.py`), so a green that never ran on real hardware cannot come back.
- **The evidence of the updates can be listed from the command line:** `urtc_flasher.py --history FOLDER [--json]` reads the evidence records (`urtc-evidence/1`) of a folder, checks each one and lists them newest first with a summary; a record edited after it was written is listed as not valid and the exit status is 1. It opens no bus. The shared code is the history of the common evidence.

## [0.4.2] - The evidence of every flashing in the common format and the universal README

- **Every update also leaves an evidence record:** next to the update report the flasher writes `urtc_evidence_<time>.json` in the common `urtc-evidence/1` shape (tool, time, board, versions before and after, the image with its SHA-256, outcome and a digest of the record), the same shape the tester and the updater can write. The report is unchanged, and a record that cannot be made never fails an update.
- **Related Projects lists the URTC family:** the section names the repositories of URTC by group, each with one short line about what it is for, and, in one short line each, the sister projects (independent ecosystems of the same author that share the base and the tools), in the eight languages. It no longer says that URTC is part of another ecosystem.
- **The README follows the universal layout in the eight languages:** the numbered sections are now the fixed ones, with the step-by-step manual (adapter, install, firmware files, installed version, flashing, SWD/JTAG, command line, diagnostics, F-RAM erase, key and HardwareID) kept in Quick start, Features, Interfaces and Configuration; the Architecture and the Repository Structure are drawn from `docs/architecture.json` and `docs/structure.json`, and the annotated tree of the files is `docs/SOURCE_MAP.md`. The number of tests is current (500). The notice of the licenses now lists the eight README files and the guides of the documentation license.
- **The layout of the README is checked in the CI:** the validator runs `tools/universal_readme_check.py` and lists, as a warning, what differs from the universal layout of the README.
- **Project status is the second section of the README,** right after At a glance, in the eight languages.
- **The full CI runs every night:** a scheduled workflow runs the complete baseline again on the default branch and opens (or updates) one issue when it fails, so a change in a runner image, a toolchain or a pinned dependency is found the next day instead of with the next unrelated change. The workflow also starts when the firmware repository announces a new release of its images.
- **The copy of the shared update code is current:** downloads now follow a redirect only to another allowed https host, and the bytes really written while extracting a package count towards the size limit.

## [0.4.1] - The whole version of the slave application and the status line of the window in the language of the program

### Firmware and protocol

- **The whole version of the slave application:** "Read board status" now shows `v0.2.4` where it showed `v0.?.4`: the master sends the low byte of the minor number in a third byte of the `0x222` companion frame and the shared code joins it with the high byte of the `0x221` answer. A slave or a master from before that byte still shows the minor as `?`.
- **The version of the slave application in the board state:** when the board has an expansion board, **Read board state** also reads the version register of the slave application through the master (`0x221`, and the patch in its `0x222` companion): it shows as `v0.?.5` (the minor number is not in the answer, so it shows as `?`) and without a patch for a slave application from before the field. Texts in the eight languages.
- **A virtual board stands in for the hardware:** the program uses `urtc_can/virtual_board.py` from URTC-COMMON (a SLCAN server over TCP with a model of the board, application and bootloader), opens `socket://host:port` serial URLs, and the window lists the URLs named in `URTC_VIRTUAL_PORT` next to the real ports; a test flashes an image end to end through it. 6 new tests.

### Programs and windows

- **The status line of the window in the language of the program:** the statuses the window sets (`READY`, `CONNECTED COM3`, `CAN-OTA IN PROGRESS` ...) have texts in the eight languages in the catalog (`QTSTATUS_*`), shown by `translate_status`; what follows the words (the port, the bit rate) is kept, and a test checks that every literal status the window sets has a text in every language.
- **A window for several tool heads on one bus:** the new **Tool heads** button opens the window of `urtc_can/node_picker*.py` (copied from URTC-COMMON): **Find heads** lists every head with its address, tool and serial number and a state written in words (ready, selected, address conflict, fault latched, in its bootloader, lost), **Select** asks for a confirmation and sends nothing to the head until it has confirmed, and the connection is wrapped so that, while several heads are on the bus, a command is refused until one is selected and confirmed. The multinode extension of the firmware is off by default: with it off, or with one head, nothing is found and everything is sent as before; the window says whether the head reports the extension as on, off or saved for the next power-up. If the selected head is lost the window shows why and, by default, every head is put in its safe state (a checkbox, saved in the configuration, switches that off after asking). The window keeps off the bus while a transfer runs. Texts in the eight languages, a sixth step in the Help guide, a README section, a fourth picture of the window guide in each language, and tests with the offscreen Qt window against a modelled bus. Tried against that model only, not against boards.
- **The old animated HYDRA-UMC mark is gone from the assets:** `assets/HYDRA_UMC_ICON.svg` is no longer kept; the window and the executable use the URTC icon and banner.
- **The pictures of the window guide in the eight languages:** `tools/capture_screens.py --all-languages` takes the three pictures of the flasher (the window, the Help window and the update window) in every language of the program, `--language NAME` one of them; the guide shows them in a table and `tests/test_window_guide.py` checks the 24 files (PNG, size of the window) and their links. The pictures use the texts of the program, not texts of the guide.
- **A guide of the window with real pictures:** `docs/WINDOW_GUIDE.md` goes through the deck, the Help window and the update window with three pictures of the real Qt Quick window, drawn without a screen (`tools/capture_screens.py`, `QT_QPA_PLATFORM=offscreen`, `grabWindow`) in `docs/screenshots/`; the eight READMEs show the first one and point to the guide, and a test checks the files and the links. Nothing was connected or sent when they were taken.
- **A Help window with a quick guide:** a button next to "Check for updates" opens five short steps for the flasher in the eight languages (shared with the other program from URTC-COMMON: `urtc_can/help_text.py`, `help_qt.py` and `assets/qml/HelpDialog.qml`), in the language of the window. It promises nothing the program does not do, and says that none of it has run on a board.
- **Texts the other programs also say follow the shared glossary of URTC-COMMON:** the Spanish "Browse" button now says `Examinar...` like the web studio. The glossary names each shared phrase once in the eight languages and the nightly comparison checks the programs against it.
- **Check for updates:** a button of the window opens the update dialog of URTC-COMMON (`urtc_can/update_*.py`, `assets/qml/UpdateDialog.qml`, texts in the eight languages). It asks GitHub once for the latest release and offers a package only if it is for this system and strictly newer; the download must match its SHA-256 and the Ed25519 signature of the key of the releases pinned in the program, is installed only after the person confirms, never while a transfer or a flash runs, keeps the previous release and goes back to it by itself if the new one does not start. The check when the program opens (`update_auto_check`) and the confirmation (`update_require_confirmation`) are options saved in `urtc_config.json`; the defaults are no automatic check and always ask, and the window warns before lowering either.

### Tests, builds and checks

- The project tree of the README lists the shared code, the lock of the language files, the checks and the window guide, the test counts and the description of the checks (the type check included) are current, and the Portuguese tree is in Portuguese; the At a glance table shows the current test count.
- **A type check on every push, and the development lock written for the Python the CI runs:** `mypy.ini` and a step of the CI (`python -m mypy`) check the program and the copies of the shared code (the window code in `qt_flasher.py` included; the Qt objects shared from URTC-COMMON are checked there); `requirements-dev.lock` is written with hashes for Python 3.12 and includes mypy.
- **The language files are generated** from the catalog of texts of URTC-COMMON (`tools/i18n_generate.py sync`), with a lock (`urtc_i18n.lock.json`) and a test of this program (`tests/test_i18n_generated.py`) that fails when a generated file is edited by hand; a text the glossary names is a reference to it. Nothing a person sees changes: a stray sentence that no key owned was left out of the eight files and the section comments are kept.
- **The dependencies are closed with hashes:** `requirements.lock` (the libraries the program runs with), `requirements-build.lock` (the packager of the executable, from the new `requirements-build.txt`) and `requirements-dev.lock` (what the tests and the checks run with) pin every package, PySide6 held at 6.11.2 (the version the tests run with), with the hashes of every file (`pip-compile --generate-hashes`); `build_exe.bat` and `build_exe.sh` install with `--require-hashes` from the first two, so two builds of the same tag use the same libraries, and the CI installs the third. They install on Windows with Python 3.14 and on Linux with Python 3.12 (checked with a dry run); regenerate them on purpose when a dependency is raised. The ranges of `requirements.txt` stay for running from the sources. The executable itself was not rebuilt.
- **The update package of a release is built and signed from this repository:** `tools/make_update_package.py` (a copy of URTC-COMMON's) packs the folder the executable build leaves in `dist/` as `urtc-flasher-<version>-<platform>.zip` (`.tar.gz` outside Windows) with the same bytes every time, adds `app_info.json` (name, version, platform, entry) and writes `.sha256` and `.sig`, the Ed25519 signature of the key of the releases over `urtc-pkg/1|app|version|platform|sha256|size`; it refuses to sign with a key other than the one the program trusts and `verify` checks a package with no private key. Run it as `python tools/make_update_package.py build --app urtc-flasher --version X.Y.Z --platform windows-x64 --source dist/<folder> --entry URTC-Flasher.exe --out out/` and attach the three files to the release.
- The CI holds the tests to a coverage floor of 61 percent (measured 69; `pytest-cov` is in `requirements-dev.txt`).

### Documentation

- **The README files carry sections written once in URTC-COMMON:** "How it updates", "First flash without hardware" (the virtual board, step by step) and "Compatibility", in the eight languages, between marker comments before the license heading (`tools/readme_sections.py` of URTC-COMMON writes and checks them; the rest of each README is hand-written as before).

## [0.4.0] - Official images listed for a bare board and a development requirements file

- **A board with no firmware and no image on disk gets the list of official images:** when the board answers from its boot-loader with no valid application and `firmware/` holds no image for it, the images of the newest release on GitHub are listed in the download section (nothing is downloaded or chosen by itself), with the log line in the eight languages. When an image is already there it is still chosen as before.

- **The tests and the checks have a requirements file:** `requirements-dev.txt` lists pytest and ruff, and the CI installs from it.

## [0.3.9] - Shared protocol copies follow the optional functions

- The copies of the shared protocol follow URTC-COMMON (the new identifiers of the optional functions).
- The README lists URTC-GATEWAY, the new gateway in front of the CAN bus, among the related projects.

## [0.3.8] - Firmware from the signed release, shared CAN transports and the safe-side settings

- `tools/ci_validate.py` fails when a versioned file has the name of a Windows path (a colon, the character a file system uses to store one, or a first folder named like a drive or a user profile): a path handed to WSL without translation once put build output inside a repository. The same check (`tools/_tracked_names.py`) is in every URTC repository.
- **The firmware images are no longer kept in git.** The `firmware/` folder starts empty (only a `.gitkeep` is tracked) and is filled from the assets of the URTC releases: the window downloads them, and `python tools/sync_firmware.py` takes them from the newest official release, checking every file against the release signature (Ed25519) and its digests. The CI downloads them the same way before the tests.
- **`firmware_release.json` names the release to use while the project has no official release**: GitHub's "latest" ignores pre-releases and answers 404, so the window and the sync tool then take the release named there (today the bench pre-release) and say so in the log; a tag that was asked for is never replaced, and any other failure is shown as it is. Delete the file, or change its tag, when an official release exists.
- The `build-test` scripts use the interpreter named by `URTC_PYTHON` (which URTC-UPDATER sets to its own) and, without it, the first `python3` or `py -3` found, so a build check runs with a Python whose packages are known.
- The dashboard notice is sent only after the CI of the push finished green (`workflow_run`).
- The banner follows the animated style of the ecosystem banners, with the name, the kind and the technologies of the project.
- **The CAN transports (SLCAN, SocketCAN, python-can, the simulated board and the bitrate listen-only detection) now come from the shared module** copied into `urtc_can/` (with the framing, SLCAN codec, versioning, quick-state and conformance helpers), so a fix made once in URTC-COMMON applies here too. `flasher_transports.py` keeps its name and only adds what is specific to this program: SocketCAN warnings said in the language of the window and the serial port taken from this module's `serial`. The shared SLCAN keeps writes from two threads apart, clears stale input when the channel opens and turns a failed serial write into a typed error; a channel opened listen-only refuses to transmit.
- The eight copies of shared modules that sat unused at the top of the repository (they could not be imported there) are gone; the one lock file for the shared modules is `urtc_can/urtc_common.lock.json`, and the test that checks the copies are not behind URTC-COMMON now covers every file in it.
- The tests that built an SLCAN object by hand or read the simulated board's internals now go through the public classes (`serial_module` for a fake port, the board's own `sent` list).
- The test count in the README matches the test suite.
## [0.3.7] - Follow URTC-COMMON 0.0.5 and keep only the language entries the Qt window uses

- The copies of the CAN protocol module and of the conformance vectors follow URTC-COMMON 0.0.5, so the tool carries the multinode extension of the protocol that the firmware already speaks.
- The language files no longer carry the entries that only the retired window used (160 per language); the entries the code builds from a prefix are kept.
- The manifest declares how far the project has been shown to work (`evidence`: simulator) and `tools/ci_validate.py` checks the value.
- The manifest notes are shorter.
- Build version synchronized with `urtc.project.json` and the repository-native version source.

## [0.3.6] - Follow URTC-COMMON 0.0.5 and the 0.3.8 firmware

- The 0.3.8 firmware images (with the multinode switch, off by default) are bundled, and the shared protocol and widget copies follow URTC-COMMON 0.0.5.

## [0.3.5] - The Qt Quick deck is the only window, with everything the Tkinter window had

- The Qt Quick deck can flash the expansion slave: a target choice (main board or slave), with the images checked against the slot of the chosen target. The "board is running the application" option (bootloader entry), the F-RAM erase and the downgrade authorisation are for the main board and are switched off for the slave.
- The downgrade authorisation asks for its own second confirmation after the routine one, and that confirmation is used up by one flash; the backend refuses the flash without it.
- New backup of the installed firmware over CAN (main board only) to a file chosen in a save dialog, with progress and cancel.
- A firmware file can be picked from anywhere; a file that does not look like an image for the chosen slot waits for an explicit yes. A red warning shows when the selected image is signed with the public development key.
- The GitHub download is a dialog again: a release tag box with Load, the images of the release with their size, download of the selected one together with its digest and manifest, and a question before an existing file is replaced (the earlier one-button download replaced files without asking).
- New bus-activity check (frames seen in two seconds and, on SocketCAN, the counter deltas), Save Logs, Save Debug Bundle and an About dialog with the Readme, the License and the GitHub page. Every session is also written to `logs/`, a report is written after each successful update, and the newest official image is offered when the board sits in its bootloader with no application.
- Closing the window during a transfer asks first, and the adapter is released when the program exits.
- The Tkinter window is retired: `urtc_flasher.py` starts the Qt Quick deck (`--cli` stays for headless updates, `--qtquick` is still accepted). `flasher_gui.py`, `flasher_uithread.py`, the animated-mark widgets, their frames and the startup banner are removed, and the build scripts, the documentation and the language files follow.
- The language list and selector, the colour of the connection state and the size formatting come from the `urtc_ui` copy of URTC-COMMON; the protocol copies follow URTC-COMMON 0.0.4, and the test that compares them with the shared repository passes with it next to this one.
- Fix: three log labels (bit-rate search failed, GitHub failure, GitHub download blocked) were stored as one dictionary of all eight languages and showed that text; each language file now holds its own text.
- New tests for the target choice, the downgrade confirmation, the backup, the files picked by hand, the release dialog, the session log and closing, plus an offscreen check that loads the deck with the options.

## [0.3.4] - The Qt Quick deck gains a bus-speed selector and a release download

- The Qt Quick deck has a bus-speed (bitrate) selector for serial CAN adapters, from 10 kbit/s to 1 Mbit/s, locked while connected; it was fixed at 500 kbit/s.
- The Qt Quick deck can download the images of the newest GitHub release together with their digest and manifest files, then rescans the firmware folder; a file name that would leave the firmware folder is never written.
- The Qt Quick deck can search for the bus speed by listening only: each candidate speed is only listened to, nothing is transmitted, and a silent bus leaves the chosen speed untouched.
- Tests for both: every listed speed maps to its adapter code, an unknown speed is ignored, the speed cannot change while connected, and the release download covers images, digest files, unsafe names and a failed lookup.

## [0.3.3] - An explicit bump command: building never changes the version

- Building no longer changes the version: build_exe.bat and build_exe.sh only read it, and raising it is the explicit `python bump.py` step.
- Every licence statement and source header says GPL-3.0-or-later.

## [0.3.2] - Release signatures, shared protocol constants and a language selector

- Release signatures: every file of an official release has an Ed25519 signature (<file>.sig) by the key of the releases. The flasher carries the public key and checks <image>.sig before a flash (a wrong signature blocks the update, a missing one is reported as the image of a bench pre-release), and tools/sync_firmware.py checks every file it downloads, refusing a wrong signature and requiring --allow-unsigned for a set that has none.
- The CAN identifiers, the hardware ids, the flash page size and the erase-memory magic bytes are now aliases of the generated protocol module (urtc_can/protocol.py, a copy of URTC-COMMON kept honest by a lock file); a new test fails when the copy is edited by hand or falls behind, and the shared conformance vectors are refreshed.
- The header of the Qt Quick window has a language selector (the eight languages); the choice is saved and applies on the next start. The new log lines are translated in the eight languages.
- The README examples no longer name a fixed bundled firmware version.
- The build and run scripts read URTC_CI as their non-interactive switch.
- The file tree of the README (all eight languages) shows what tools/sync_firmware.py really does with firmware/: it replaces the URTC_* files of the folder with the set of one release and leaves other files alone; it no longer says that older versions are kept next to the new one.
- The README of every language lists URTC-UPDATER among the related projects.
- CONTRIBUTING.md says what this tool verifies (a PAGE_ACK for every page and the verification status of the bootloader) and that the read-back of the copy is done by the bootloader, not by this tool.
- .gitattributes keeps the firmware images (.bin, .elf) binary.
- The CI workflow no longer carries steps for stacks this repository does not have.
- LICENSE holds the full text of the GNU General Public License v3.0; the copyright notice and the license of the documentation moved to a new NOTICE file. The license is GPL-3.0-or-later everywhere: LICENSE.md, source headers, script banners, About texts and READMEs (eight languages).
- A test compares hydra_umc_animation.py and hydra_umc_deck_widgets.py with the copies in the other desktop tool (by syntax tree, so comments and layout do not count) and fails when one of them changes alone; it skips when the other repository is not next to this one.
- The number of tests and test files in the README (eight languages) and in the At a glance table is the current one, and the Japanese and Chinese texts no longer quote an older count.

## [0.3.1] - Claims aligned with what has been tested

- Maturity is functional: nothing here has been verified on real hardware yet.
- The README (all eight languages) no longer presents the signed flashing path as authenticated: the check is a shared-key HMAC-SHA256, the published images are signed with the public development key, and asymmetric signatures are planned.
- The README states that every flashing path was exercised only against the MockCAN simulator, never against a real board.

## [0.3.0] - Serial reader drops extended frames and line noise

- **The serial (SLCAN) reader no longer turns an extended 29-bit frame into a standard one.** A `T` line from another device on the bus, or noise that looks like one, used to be delivered with its raw 29-bit value as the identifier, so a frame with id 0x00000111 was indistinguishable from the real 0x111 answer. Such lines are now discarded, as the SocketCAN and python-can transports already did.
- **Identifiers and data digits must be real hexadecimal.** A signed, `0x`-prefixed or underscore-separated field in a received line used to be accepted by the number parser and delivered as a frame; the line is now ignored.
- **More of the tool is covered by tests.** The CAN protocol is checked against vectors shared with the other URTC tools (identifiers, magic payloads, serial framing, version answers with the patch frame, the end-of-update minor field), and the image checks (bin, Intel HEX, ELF), the SWD wrappers and the expansion-slave update now have their own tests.

## [0.2.9] - Firmware from release assets, and the firmware patch number

- **Download from GitHub reads the assets of a release.** The URTC firmware binaries are no longer kept in git: they are attached to each GitHub release. The download window now lists the images and their sha256 and manifest files from the latest release through the Releases API, has a box to type a release tag and load another release, and shows the tag it loaded. Files are only accepted from github.com release assets and the asset storage hosts it redirects to (objects.githubusercontent.com and release-assets.githubusercontent.com); the host is checked before the request and again on the address the answer came from, the size is compared with what the release announces, and an optional GITHUB_TOKEN raises the API rate limit.
- **tools/sync_firmware.py takes the firmware set from a release.** With no argument it downloads the assets of the latest URTC release into a temporary folder (--release TAG for another one), runs the same digest and signature checks as before and only then replaces the bundled firmware/ folder; a local folder, such as a local URTC build, can still be given as an argument. The bundled firmware/ folder works as it did.
- **The firmware patch number over CAN.** The new frame 0x7E9 (installed application patch plus a flag that says the bootloader reads the patch) is collected next to the version answer, the slave version answer 0x218 is read in its extended 5-byte form, and the window, the log and the installed -> new line show major.minor.patch when the side has a patch. The patch only takes part in the older-than-installed warning when both sides carry one. The end-of-update frame carries the image patch in the high byte of the minor field only towards a bootloader that announced it reads it; every other board, and every image without a patch, gets the unchanged payload, so boards that predate the extension work as before. The command-line --version option accepts an optional patch (MAJOR.MINOR.PATCH).
- **MockCAN speaks the new frames.** The simulated board can send 0x7E9 (with or without the bootloader flag) and answer the slave version query in the legacy and in the extended form, and it keeps the end-of-update payloads it received; by default it still behaves like a board that predates the patch. Not verified on a real board: the new frames follow the protocol description and are tested against the simulator only.

## [0.2.8] - Thread-safe window, fully translated messages, and updates that say what they replace

- **Worker threads never touch Tkinter.** Results, log lines and dialogs are posted to a queue that the main thread drains from a timer, and every option a worker needs (target, trigger, F-RAM erase, downgrade, bitrate, SWD tool, probe) is read on the main thread and handed over. Closing the window while a worker is still logging no longer raises or hangs; late messages are dropped.
- **Messages are translated.** The 21 error messages of the update protocol, the connection and status texts, the file-dialog titles and types, the version line and the Qt Quick log lines (shown in the chosen language, and limited to the newest 500) come from the language files in all 8 languages (97 new texts). The manifest is read as UTF-8.
- **Before an update the tool says what it replaces:** it asks the board what is installed and logs installed vX.Y -> new vA.B, warns when the new version is older (the bootloader refuses that unless the downgrade is allowed) and suggests a backup first. The Tk window, the Qt Quick deck and the command line all do it.
- **Signing hints:** an image signed with the public development key shows a red warning under the file name, and with require_production_signature set to true in urtc_config.json such images are refused before any frame is sent.
- **A board in its bootloader with no firmware** gets the newest official main-board image of firmware/ preselected, to check and flash.
- **Update reports:** after every successful update logs/urtc_update_report_*.json records tool version, operator, image name, size, SHA-256 and signing kind, and the versions before and after, with its own digest so an edit is noticeable.
- **Session logs:** only the newest 30 are kept, and a per-user folder is used when the folder next to the program cannot be written.
- **Optional python-can transport** for the command line (--transport python-can, --port interface:channel) for PCAN, Kvaser, gs_usb and the other interfaces python-can supports.
- **The simulated bootloader answers a readback** (pages of 8-byte frames, a shorter last frame) and reports a configurable installed version, so the backup and version paths are tested against it.
- **Documentation made accurate:** the README and the project notes list exactly what the Qt Quick deck does and does not do compared with the Tkinter window; the language list (8 files), the override paragraph (the slave signing key can be overridden), the reset-handler addresses of the shipped images, the 0x210-0x219 range, the limits of the CAN backup and of the simulation are corrected, and the command-line reference was regenerated from real runs of the shipped 0.3.3 and 0.3.8 images.
- **Code hygiene and CI:** unused imports removed, exceptions chained, ruff runs in CI, the Qt tests and the two Qt end-to-end checks run offscreen in CI, the tests also run on Windows, and pytest.ini limits collection to tests/.
- Tests: 171 (before 104).

## [0.2.7] - Bitrate auto-detect no longer transmits, downloads are verified, and the build scripts are consistent

- **Bitrate auto-detect only listens.** It opens the SLCAN adapter in listen-only mode (`L`) at each standard bitrate and stops at the first one where it hears a valid frame, so it can no longer cause bit and form errors on a running bus; on a silent bus it reports that nothing was heard and the bitrate is chosen by hand. The interface texts and the README say so in all 8 languages.
- **The README no longer promises that a lost page acknowledgement is recovered.** The bootloader sends each page ACK once, so the retry only helps an ACK that is merely late; the section and the log message now say that an ACK that never arrives aborts the update, and that the heartbeat is a hint, not proof.
- **GitHub downloads are verified:** the number of bytes written must match the announced Content-Length and the size in the listing, only `.bin` images and their `.sha256`/`.manifest.json` files are listed, downloads are accepted only from the GitHub file host (also after a redirect), a failure to create the firmware folder is reported instead of raised, a 403 is called a rate limit only when GitHub says so, and an optional `GITHUB_TOKEN` environment variable raises the API limit.
- **Build scripts:** `build_exe.sh` checks that `python3` exists, its steps are numbered in the order they run, and the stale PyInstaller spec (which both scripts ignored) was removed; `build_exe.bat` has the same numbering fix.

## [0.2.6] - The update of any image size works, a backup of any size is complete, and the version is never invented

- **Portuguese (Portugal) is a language of the interface** (`language/portuguese.lng`, in the language menu), and the Readme menu opens `README_por.md`; the README exists in Portuguese too.
- **An update of an image whose size is not a whole number of 2048-byte pages now completes.** The bootloader writes and acknowledges a page when its buffer is full, and the last, partial page only when the end of the update (0x7F4) arrives; the flasher waited for that last acknowledgement before sending the end, so the official image of 73476 bytes could never be installed over CAN. The simulated bootloader now behaves like the real one, and the tests use sizes on both sides of a page.
- **The CAN backup of the installed firmware is complete whatever its size:** the last data frame of a readback has fewer than 8 bytes when the size is not a multiple of 8, and it used to be dropped (the backup then failed after the page timeout).
- **The version written into the board is never invented.** It is the manifest's, the one given with the new `--version MAJOR.MINOR`, or the one in the file name (`..._v0.3.3.bin`); without any of them nothing is sent and the tool says so. The made-up 1.0 made every later official image look older to the anti-rollback check and be rejected.
- **The update starts as soon as the bootloader says it is listening** (its first heartbeat) instead of after a fixed 0.8 s, which could miss the 600 ms window it listens in; without a heartbeat the old wait is kept.
- **An image for the other board is refused before a single frame is sent:** the manifest's `component` and `hardware_id` are compared with the target (the slave's image sent to the main board was transferred in full and refused only at the end, blaming the key).
- **A slave whose application is still running is reported at once** instead of ending in a generic timeout.
- **No answer is not "none installed":** when the board does not answer the question about the expansion board or the MLX sensor, the combo keeps its value, so a later Save cannot write a made-up 0 over the real configuration.
- A stack pointer in the CCM RAM is accepted by the plausibility check, as the bootloader accepts it; the bootloader limit is 30 KB (its metadata page starts at 0x7800); a page size other than the bootloader's 2048 in `urtc_config.json` is ignored; the example configuration only asks for the language; the command line checks the published digests of the image like the windows do; the programmers' output is read as UTF-8 without console windows; `run.sh` finds `python3`.
- The build test no longer fails on a machine without pytest (it installs it, or says the tests were skipped).
- Texts: four new messages in the seven languages. Tests: 79 (before 41).

## [0.2.5] - Copy-log icon button

- **Copy-log button:** the activity log has a small copy icon (two sheets) that puts the whole log on the clipboard and flashes green when done.

## [0.2.4] - Bundled firmware 0.3.3, READMEs updated in all languages

- `firmware/` re-synced with URTC's current build (main 0.3.3 / boot 0.3.8,
  slave 0.1.9 / boot 0.2.2) via `tools/sync_firmware.py`.
- READMEs (en, es, de, fr, it, ja, zh): the manifest section describes the
  published `.sha256`/`.manifest.json` (a mismatch refuses the flash), the
  signing-key section says the tool carries no key, the "Honesty check" and
  the repository tree list the real test suite (43 tests, run by GitHub
  Actions) and `tools/sync_firmware.py`, and example file names match the
  current firmware.

## [0.2.3] - No signing key, published signatures, firmware/ in sync with URTC

- **No default signing key any more.** The placeholder `HMAC_KEY`/`SLAVE_HMAC_KEY`
  are gone (`None`). `flash()`/`flash_slave()` send the signature the URTC build
  publishes in `<image>.manifest.json` (`hmac_sha256`); a self-built image with
  no manifest is only signed with a key from `urtc_config.json`, and refused
  before any bus traffic otherwise. See URTC `docs/FIRMWARE_SIGNING.TXT`.
- **A manifest sha256 mismatch now refuses the flash** (it was a warning).
  `preflight_image()` also checks the manifest's sha256 when there is no
  `<image>.sha256`, and blocks when the two published digests disagree.
- **GitHub download brings the sidecars**: picking an image also downloads its
  `.sha256` and `.manifest.json`, and the sidecars are no longer listed as
  images of their own.
- **`firmware/` = URTC's build** (main 0.3.2 / boot 0.3.7, slave 0.1.8 /
  boot 0.2.1, each with its sidecars). `tools/sync_firmware.py` copies them
  from URTC after checking every digest; `--check` verifies the folder, and a
  test runs it.
- **Tests**: `tests/test_firmware_signature.py` (published signature sent
  without any key, unsigned image refused, bench-key signing, malformed
  signature, preflight digests, bundled firmware); `tests/conftest.py` gives
  the protocol tests a bench key. CI now runs the pytest suite.

## [0.2.2] - The Qt Quick flash checks the image too

- The Qt Quick CAN-OTA flash (`--qtquick`) now runs the same image check as the Tk window: a digest published next to the image (`image.bin.sha256`) must match it or the flash is refused before any frame is sent, and an image with no published digest has its SHA-256 logged so it can be recorded. Two tests cover the refusal and the recording.

## [0.2.1] - Image digest before flashing

- Before a flash the image's SHA-256 is computed and logged. If a digest is published next to it (image.bin.sha256, bare or sha256sum layout) it must match, otherwise the flash is refused; an image without a published digest is still flashed, with its digest recorded.

## [0.2.0] - Image and target integrity checks

- `flasher_integrity.py`: `verify_image()` compares a firmware file's SHA-256 (required) and
  optional CRC-32 with the expected values and names both when they differ; `verify_target()`
  confirms the board that answered is the board that was meant to be flashed;
  `may_report_success()` is true only when both passed. A missing expectation is never a pass.
  Nine new tests. Not yet wired into the flashing screens.

## [0.1.9] - The real pytest suite now runs as part of build-test, not just manually

- `tools/build_test.py` compiled every `.py` file but never actually ran
  `tests/` (3 real files, 20 tests, including a full simulated CAN
  bootloader via `MockCAN`) - a real regression in `flasher_protocol.py`
  or `flasher_validation.py` could pass `build-test.sh`/`build-test.bat`
  cleanly. Now runs `pytest tests/` (with `PYTHONPATH` pointed at the
  repo root, where these modules live) right after the compile check,
  same pattern already used elsewhere in this ecosystem. GitHub Actions
  CI itself still doesn't run it (that workflow is the shared
  ecosystem-wide baseline, with no generic Python-pytest step) -
  documented honestly in the README rather than silently claimed as
  covered.
- README (all 7 languages) "Honesty check" section and file-tree comment
  corrected: it described 2 test files / 12 tests, actually 3 files / 20
  tests today - stale since `test_flash_protocol_dispatch.py` was added.

## [0.1.8] - Live transfer speed and a reactive stall indicator during CAN-OTA

- **Live transfer speed (kB/s)** during a CAN-OTA update/readback, in both
  the established Tkinter panel and the Qt Quick deck. `flasher_protocol.py`
  already computed per-page and overall kB/s for its own log lines; a new,
  independent `speed_cb` callback on `URTCFlasher` now carries that same
  figure out to the UI at the same cadence the existing `progress_cb`
  already fires at (kept as a separate callback, not a second argument on
  `progress_cb`, so every existing single-argument `progress_cb` caller
  keeps working unchanged). Both flashing UIs show it next to the
  percentage while a transfer is running.
- **Reactive stall indicator**, driven independently of the flash worker
  thread (a Tkinter `after` poll / a Qt `QTimer`, not the callbacks
  themselves) so a genuinely stalled transfer - where neither `progress_cb`
  nor the new `speed_cb` fires at all - is visibly different from one still
  making progress, instead of the UI just freezing on its last known
  percentage with no cue that it's now stale. New
  `LBL_TRANSFER_SPEED`/`LBL_TRANSFER_STALLED` keys across all 7 languages.

## [0.1.7] - Full-chip SWD/JTAG programming in the Qt Quick deck, real About window

- **Full-chip SWD/JTAG programming** is now available in the Qt Quick
  deck, completing its migration - the one real gap left after CAN-OTA,
  read-only SWD/JTAG discovery, Board Snapshot and device-configuration
  writes. Reuses `flasher_swd_tools.py`'s `PyOCDCLI`/`CubeProgrammerCLI`
  completely unchanged (only the UI is new): target chip (this board /
  expansion slave), tool (pyOCD / STM32CubeProgrammer), a probe picker
  scoped to whichever tool is selected (a pyOCD uid and a
  STM32CubeProgrammer serial are never interchangeable), bootloader/
  application file pickers (editable path field + native file dialog,
  both re-validated against the real per-target flash address/size
  table on every selection AND on every target switch), dry run
  (default on) and back-up-before-erasing toggles, a real read-only RDP
  (readout protection) option-byte check, and the full-chip flash
  itself behind the same shared confirm dialog every other real
  persistent write in this deck already uses - its title/body are
  assembled from the real selected tool/target/files, matching the
  established Tkinter panel's own confirmation message. An invalid
  file shows an inline warning rather than hard-blocking the button,
  same real "proceed anyway" latitude the Tkinter panel gives (the
  destructive action still requires a second, explicit confirmation
  either way). Zero new i18n keys beyond one new section header
  (`QT_SWD_FULL_CHIP_SECTION`, added across all 7 languages) - every
  other label, help text and confirmation message reuses the legacy
  panel's own already-translated keys verbatim.
- **Real About window**, matching HYDRA-UMC-STUDIO's own `About.tsx` and
  the ecosystem's PySide6 tools: the Tkinter About window now shows a
  tagline, a one-paragraph description, and a real Version/Author/Email/
  License info block, not just a banner and one line of text. New
  `TITLE_ABOUT`/`ABOUT_TAGLINE`/`ABOUT_DESCRIPTION`/`ABOUT_VERSION`/
  `ABOUT_AUTHOR`/`ABOUT_EMAIL`/`ABOUT_LICENSE` keys across all 7
  languages, replacing the old `LBL_ABOUT_AUTHOR` - full key parity
  verified across every language file.

- The Qt Quick deck's own header `ToolBar` relied on the Basic style's
  implicit sizing, which collapsed to 0 height for this specific window -
  the branding/status text all overlapped at the top-left corner instead
  of laying out in a real row. The same real bug HYDRA-UMC-SUITE's own
  Qt Quick shell already found and fixed (an explicit `height: 84`,
  sized to fit the header's own 50px icon plus its Card/RowLayout
  margins) - never propagated back to this sibling app until now.
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

- SLCAN reception now rejects impossible CAN 2.0 DLC values (`9`-`F`) before
  they can be exposed to the flashing protocol. Valid standard and extended
  frames remain parsed exactly as before.

- `flash()`'s own verify-failure reporting is now exercised end-to-end for
  real, not just reachable by hand via `--mock-fail`: a simulated
  bootloader (`MockCAN(simulate_failure=...)`) accepts every real page of
  a real firmware file, then fails final verification - `flash()` raises
  `FlashError` with the real, human-readable `VERIFY_FAIL_REASONS` text
  (never a generic "failed"), and `progress_cb` reaches its real 70% page-
  transfer ceiling but never 100% on that path (100% would read as
  "verified", which never happened). Parametrized across all 5 real
  documented failure reasons, plus one unrecognized reason byte (a
  possible future firmware revision) still reported honestly rather than
  swallowed, plus a positive control confirming a genuine success does
  reach 100%. Doesn't bump `FLASHER_VERSION` on its own, same convention
  as this file's own note above.

## [0.1.6] - Real automated test coverage for flash()/flash_slave() dispatch

- `tests/test_flash_protocol_dispatch.py` (new): `flash()`/`flash_slave()`'s
  own size guards (empty/oversized firmware, both rejected before any CAN
  frame is sent) are now exercised directly, alongside `query_version()`
  against the real `MockCAN` simulated peer and the manifest sha256
  cross-check's real "warn, never abort" behavior. Previously only the
  verify-fail reporting path and the monotonic-clock usage had automated
  coverage - the size guards and manifest check had none.

## [0.1.5] - The SWD backup save-file dialog title was hardcoded English, never routed through the language files

- The full-chip SWD/JTAG flow's "Save flash backup as..." `FileDialog`
  title was a plain literal QML string, never calling
  `flasherBackend.uiText()` - every non-English language always showed
  English text there. New `QT_SWD_BACKUP_DIALOG_TITLE` key added to all
  7 `language/*.lng` files, wired into `assets/qml/FlasherDeck.qml`.
- `python tools/build_test.py`'s own real QML-key extraction now reports
  `QML_I18N=PASS keys=57 languages=7` (up from 56), proving the new key
  is required and present in every language.

## [0.1.4] - Every timeout uses the monotonic clock, not the civil one

Found on code review:
`flasher_protocol.py`'s every deadline/duration computation (`query_version`,
`_wait_for`, the page-transfer/readback loops, `query_slave_version`, the
slave status/progress queries - 33 call sites total) used `time.time()`, the
civil/wall clock. An NTP sync or a manual clock change mid-wait had nothing
to do with real elapsed time but could still shorten a real flashing timeout
(aborting mid-page as "timed out" while the board was still working fine) or
lengthen one (waiting on a genuinely hung/unresponsive board far longer than
intended). Switched to `time.monotonic()` throughout - nothing in this file
ever used one of these values as a real calendar timestamp, only for "how
long has this taken" and "when should this deadline expire", so there was no
wall-clock use to preserve.

4 new tests (`tests/test_flasher_protocol_clock.py`, this repo's first
pytest suite for `flasher_protocol.py`) patch `time.time()` to raise if ever
called - a direct proof the deadline/duration code path genuinely never
reads the civil clock at all - covering both the timeout and success paths
of `_wait_for`, `query_version` (including its post-response grace-window
wait), and `query_slave_version`, each against the real `MockCAN` simulated
transport.

Also carries a `README.md` (all 7 languages) version-badge correction
(0.1.0 -> 0.1.3, matching the real current version) that had been sitting
uncommitted from earlier work, unrelated to this fix, bundled here rather
than left stranded.

Verified with `python tools/build_test.py` (this repo's own real CI check -
PASS) and `python -m pytest tests/` (4/4 PASS).

## [0.1.3]

- **The Qt Quick deck now has real device-configuration writes**:
  expansion board type, MLX9064x sensor variant, free tool selection,
  and device serial number - the real last gap between it and the
  established Tkinter panel (whose own docstring already said "Tkinter
  remains the default until the SWD/JTAG and configuration pages reach
  parity"; Board Snapshot already covered every one of these fields
  read-only, so the write side was the one real thing missing). Each
  Save asks for the same real confirmation the Tkinter panel's own
  `save_expansion_board_type`/`save_mlx_sensor_variant`/
  `program_free_tool_config`/`program_device_serial` already require -
  every one of these persists a real EEPROM field on the board.
- New `_run_config_write()` - one real generic write-then-confirm
  worker all 4 writes share (send the real SET frame, wait up to 1.5s
  for the board's own real confirmation, compare against what was
  actually sent) - not 4 near-duplicate workers. Reuses the exact same
  real, already-translated per-field result wording the Tkinter panel
  already has (`LOG_EXPANSION_TYPE_SAVED_CONFIRMED`/`_MISMATCH`/
  `_NO_CONFIRMATION` and the equivalent 3 sets for the other fields) -
  no new duplicate translations invented for the same real event.
- The right-hand card **now scrolls** - real content no longer reliably
  fit the window once these 4 new sections landed; the Activity Log's
  own real height, previously `Layout.fillHeight: true` against a
  fixed-height parent, is now a real fixed 200px viewport instead.
- New `verify_qt_device_config.py` (repo root - needs a real PySide6
  event loop): a fake transport answers each real SET frame from a
  separate thread - real confirmed writes, a real out-of-range value
  rejected before ever reaching the transport, a real MISMATCH
  correctly reported as one (not read as success), a genuine timeout
  producing real "no confirmation" text, `busy` correctly blocking a
  second write from starting concurrently, and a final real QML load
  with zero warnings.
- **Full-chip SWD/JTAG programming remains deliberately in the
  established Tkinter workflow** - unchanged in this pass. The Qt Quick
  deck's own real SWD/JTAG discovery (tool capability detection + probe
  enumeration) was already real and read-only; porting the actual
  destructive programming flow is explicitly gated on real hardware
  validation, per this file's own existing `QT_SWD_SAFETY_NOTE`.

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

- Ecosystem-wide build-versioning policy: `FLASHER_VERSION` normalized from
  the old two-part `"0.1"` to the three-part `"0.1.0"`, and `bump_version.py`
  added to auto-increment it on every real build. Wired into both `build_exe.bat` and `build_exe.sh` as a new step
  right before compiling.
- This CHANGELOG.md.

## Earlier history

### [0.1]

Visual/text version bump (banner SVGs, splash text) from v0.0 to v0.1,
plus a full pass fixing every leftover "v0.0"/"0.0" reference across the
project (build banners, README screenshots and examples, `/images/` gallery
duplicates) that earlier passes had missed - including some caught only
after the user reported still seeing "v0.0" post-migration.

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

- **Critical**: SWD backup-before-flash used the `-r32` STM32CubeProgrammer
  flag, which (confirmed against official ST documentation) only ever
  dumps to screen and never accepts an output file - full-chip SWD backups
  were silently failing every time, and the tool correctly refused to
  proceed with erasing without a successful backup, so full-chip flashing
  could never complete at all. Fixed to the correct `-r` flag.
- **Critical**: `-c` probe-selection parameters were passed to
  `subprocess` as separate arguments instead of one combined string,
  breaking selection of a specific probe by serial number.
  10 further real bugs fixed in the same review pass: byte-at-a-time SLCAN
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

- Split the single 3603-line `urtc_flasher.py` into 7 focused modules plus
  a thin entry point, purely for readability.

### Earlier history (pre-1.1, no formal version tags)

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
