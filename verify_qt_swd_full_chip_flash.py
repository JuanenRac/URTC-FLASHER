# =============================================================================
# URTC Flasher - real, end-to-end check of the Qt Quick full-chip SWD/JTAG
# programming panel (dry-run only - never touches real hardware)
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Deliberately kept OUTSIDE tests/ - same real reason as the TESTER repo's
own verify_qt_*.py scripts: needs a real Qt event loop for real cross-
thread Signal delivery. Run directly:
    QT_QPA_PLATFORM=offscreen python verify_qt_swd_full_chip_flash.py

Unlike those, this one deliberately uses the REAL PyOCDCLI/CubeProgrammerCLI
classes (both pyocd and STM32CubeProgrammer are actually installed on this
development machine) rather than a fake - dry_run=True short-circuits
flasher_swd_tools.py's own _run() before it ever calls subprocess.Popen
(see full_chip_flash's own real code), so this exercises the REAL command
construction (target names, flash addresses, probe args) with zero risk to
any real board or the local machine.
"""
from __future__ import annotations

import struct
import sys
import time
from pathlib import Path

from PySide6.QtGui import QGuiApplication

from flasher_config import (
    APP_FLASH_ADDR, BOOTLOADER_FLASH_ADDR,
    SLAVE_APP_FLASH_ADDR, SLAVE_BOOTLOADER_FLASH_ADDR,
)
from qt_flasher import FlasherQtBridge

FIXTURE_DIR = Path(__file__).parent / "_swd_fixtures_scratch"


def _make_bin(path: Path, reset_handler_addr: int) -> None:
    """A minimal-but-real Cortex-M vector table: a plausible initial SP
    (inside this chip's real SRAM range) plus a reset handler address
    that lands inside whichever slot the caller is targeting - exactly
    what validate_swd_image_file() (flasher_validation.py) checks for."""
    data = struct.pack("<II", 0x20001000, reset_handler_addr) + b"\x00" * 56
    path.write_bytes(data)


def _pump_until(app: QGuiApplication, condition, timeout_s: float = 5.0) -> None:
    deadline = time.monotonic() + timeout_s
    while not condition() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.02)


def _run() -> None:
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    FIXTURE_DIR.mkdir(exist_ok=True)
    master_boot = FIXTURE_DIR / "master_boot.bin"
    master_app = FIXTURE_DIR / "master_app.bin"
    slave_boot = FIXTURE_DIR / "slave_boot.bin"
    garbage = FIXTURE_DIR / "garbage.bin"
    # Master's own bootloader slot is 32KB, slave's is only 18KB (both
    # share the same 0x08000000 base) - placing this reset handler at
    # +20000 lands inside master's real range but outside slave's,
    # genuinely proving the per-target re-validation below, unlike a
    # low offset which both ranges would happen to accept.
    _make_bin(master_boot, BOOTLOADER_FLASH_ADDR + 20000)
    _make_bin(master_app, APP_FLASH_ADDR + 0x101)
    _make_bin(slave_boot, SLAVE_BOOTLOADER_FLASH_ADDR + 0x101)
    garbage.write_bytes(b"\x00" * 16)  # not a plausible vector table at all

    bridge = FlasherQtBridge()

    # --- real safe defaults, matching flasher_gui.py's own ---
    assert bridge.swdTarget == "master"
    assert bridge.swdDryRun is True
    assert bridge.swdBackup is False
    assert bridge.canFullChipFlash is False, "no files selected yet"

    # --- selecting a valid bootloader/app for the master target ---
    bridge.setSwdBootloaderPath(str(master_boot))
    assert bridge.swdBootloaderValid is True, bridge.swdBootloaderReason
    bridge.setSwdAppPath(str(master_app))
    assert bridge.swdAppValid is True, bridge.swdAppReason
    assert bridge.canFullChipFlash is True

    # --- a garbage file must be rejected, not silently accepted ---
    bridge.setSwdBootloaderPath(str(garbage))
    assert bridge.swdBootloaderValid is False
    assert bridge.canFullChipFlash is True, "an invalid file is a warning, not a hard block - matches flasher_gui.py's own askyesno override"
    bridge.setSwdBootloaderPath(str(master_boot))  # restore for the rest of the run

    # --- switching target re-validates both files against the new real addr/size table ---
    bridge.setSwdTarget("slave")
    assert bridge.swdBootloaderValid is False, "a MASTER bootloader must fail SLAVE's own (smaller) reset-handler-range check"
    bridge.setSwdBootloaderPath(str(slave_boot))
    assert bridge.swdBootloaderValid is True, bridge.swdBootloaderReason
    bridge.setSwdTarget("master")
    # Master's real bootloader slot (32KB) is a strict superset of
    # slave's (18KB, same 0x08000000 base) - a file valid for slave is
    # therefore always valid for master too under this real address
    # layout, so re-validation correctly leaves it green here. The
    # earlier assertion (a MASTER-range-only file failing SLAVE) is the
    # real, asymmetric direction that actually proves per-target
    # re-validation is happening at all.
    assert bridge.swdBootloaderValid is True
    bridge.setSwdBootloaderPath(str(master_boot))
    assert bridge.swdBootloaderValid is True

    # --- multiple probes matching the selected tool force an explicit choice ---
    tool_name = "pyOCD" if bridge.swdTool == "pyocd" else "STM32CubeProgrammer"
    bridge._swd_probes = [
        {"tool": tool_name, "identifier": "AAA", "description": "probe A"},
        {"tool": tool_name, "identifier": "BBB", "description": "probe B"},
        {"tool": "some other tool", "identifier": "CCC", "description": "must not match"},
    ]
    bridge.changed.emit()
    assert len(bridge.swdMatchingProbes) == 2, "the non-matching-tool probe must be filtered out"
    assert bridge.swdNeedsProbeChoice is True
    assert bridge.canFullChipFlash is False, "2 matching probes with none selected must block flashing"
    bridge.setSwdSelectedProbe("AAA")
    assert bridge.swdNeedsProbeChoice is False
    assert bridge.canFullChipFlash is True
    bridge._swd_probes = []
    bridge.setSwdSelectedProbe("")
    bridge.changed.emit()

    # --- confirm body assembly: dry run vs real, real placeholders substituted ---
    assert bridge.swdFlashConfirmTitle == "Dry run"
    dry_body = bridge.buildSwdFlashConfirmBody("")
    assert tool_name in dry_body and "WITHOUT running them" in dry_body

    bridge.setSwdDryRun(False)
    assert bridge.swdFlashConfirmTitle == "Confirm FULL CHIP programming"
    real_body = bridge.buildSwdFlashConfirmBody(r"C:\backup.bin")
    assert str(master_boot) in real_body and str(master_app) in real_body
    assert "Backup to: C:\\backup.bin" in real_body
    bridge.setSwdDryRun(True)  # restore for the real dry-run flash below

    # --- real end-to-end dry-run flash: real PyOCDCLI/CubeProgrammerCLI,
    # real command construction, subprocess never actually spawned ---
    assert bridge.busy is False
    bridge.startFullChipFlash("")
    _pump_until(app, lambda: not bridge.busy)
    assert bridge.swdFlashResult == "SWD_FLASH_DRY_RUN_COMPLETE", bridge.swdFlashResult
    # bridge.logs (the QML-facing Property) only keeps the last 12 lines -
    # a full dry run logs well over a dozen (probe check, erase, 2
    # programming steps, 2 verify steps, reset), so the real erase
    # command is checked against the FULL internal log, not that
    # display-only window.
    assert any("erase" in line.lower() for line in bridge._logs), "the real erase command must have been logged even in dry-run"

    # --- gates hold while busy ---
    bridge._set_state(busy=True)
    assert bridge.canFullChipFlash is False
    before = bridge.swdTarget
    bridge.setSwdTarget("slave")
    assert bridge.swdTarget == before, "target must not change while an operation is in progress"
    bridge._set_state(busy=False)

    # --- QML itself loads with a fresh bridge and shows zero warnings ---
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuickControls2 import QQuickStyle

    QQuickStyle.setStyle("Basic")
    engine = QQmlApplicationEngine()
    qml_bridge = FlasherQtBridge()
    engine.rootContext().setContextProperty("flasherBackend", qml_bridge)
    warnings: list[str] = []
    engine.warnings.connect(lambda ws: warnings.extend(str(w) for w in ws))
    engine.load("assets/qml/FlasherDeck.qml")
    assert engine.rootObjects(), "FlasherDeck.qml must load with the real bridge"
    assert not warnings, f"QML must load with zero warnings, got: {warnings}"

    print("verify_qt_swd_full_chip_flash: all real assertions passed")


if __name__ == "__main__":
    _run()
