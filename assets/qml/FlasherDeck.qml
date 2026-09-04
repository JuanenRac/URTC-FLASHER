// =============================================================================
// URTC Flasher - Qt Quick CAN-OTA command deck
// Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
// GPL-3.0 - see LICENSE
// =============================================================================
import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import QtQuick.VectorImage

ApplicationWindow {
    id: window
    width: 1440
    height: 900
    minimumWidth: 1080
    minimumHeight: 680
    visible: true
    title: "URTC Flasher"
    color: "#07111e"

    property color panel: "#101d30"
    property color panelAlt: "#14253b"
    property color panelBorder: "#294965"
    property color textPrimary: "#edf7ff"
    property color muted: "#91a8bd"
    property color cyan: "#38d4e6"
    property var pendingConfigAction: null
    property string pendingConfigTitle: ""
    property string pendingConfigBody: ""

    // Real, generic confirmation for the 4 device-configuration writes
    // (separate from the CAN-OTA `confirm` dialog below, which stays
    // dedicated to that one real flow) - each real write persists a
    // real EEPROM field, so every one of them asks first, same as the
    // established Tkinter panel's own messagebox.askyesno.
    function requestConfigWrite(title, body, action) {
        if (!flasherBackend.canWriteDeviceConfig)
            return
        pendingConfigTitle = title
        pendingConfigBody = body
        pendingConfigAction = action
        configConfirm.open()
    }

    // Full-chip SWD/JTAG flash reuses this SAME confirm dialog (title/
    // body assembled backend-side by buildSwdFlashConfirmBody - see its
    // own docstring for why) rather than a second dialog component -
    // one real destructive-action confirm shell for the whole app.
    // Backup, when requested and not a dry run, needs its own save-file
    // path BEFORE the confirm body can even be built (the real message
    // includes a backup_line naming that path), so that FileDialog is
    // opened first when needed; requestFullChipFlash(backupPath) is the
    // shared continuation both branches funnel into.
    function requestFullChipFlash(backupPath) {
        if (!flasherBackend.canFullChipFlash)
            return
        pendingConfigTitle = flasherBackend.swdFlashConfirmTitle
        pendingConfigBody = flasherBackend.buildSwdFlashConfirmBody(backupPath)
        pendingConfigAction = function() { flasherBackend.startFullChipFlash(backupPath) }
        configConfirm.open()
    }

    component Card: Rectangle {
        color: window.panel
        radius: 16
        border.width: 1
        border.color: window.panelBorder
    }

    component GameButton: Button {
        id: control
        property color accent: window.cyan
        implicitHeight: 42
        hoverEnabled: true
        font.family: "Bahnschrift"
        font.bold: true
        contentItem: Text {
            text: control.text
            color: control.enabled ? "#f5fbff" : "#6d8294"
            font: control.font
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            radius: 10
            color: !control.enabled ? "#122031" : (control.down ? Qt.darker(control.accent, 1.35) : (control.hovered ? Qt.lighter(control.accent, 1.13) : control.accent))
            border.width: 1
            border.color: control.enabled ? Qt.lighter(control.accent, 1.12) : "#25384b"
            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                height: 1
                color: "#9eeeff"
                opacity: control.enabled ? 0.6 : 0.15
            }
        }
    }

    header: ToolBar {
        background: Rectangle { color: "#07111e" }
        Card {
            anchors.fill: parent
            anchors.margins: 7
            RowLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 10
                Rectangle {
                    Layout.preferredWidth: 50
                    Layout.preferredHeight: 50
                    radius: 12
                    color: "#0e3045"
                    border.width: 1
                    border.color: "#2d7695"
                    VectorImage { anchors.fill: parent; anchors.margins: 7; source: flasherBackend.iconSource }
                }
                ColumnLayout {
                    Layout.preferredWidth: 250
                    spacing: 0
                    Text { text: "URTC"; color: cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 10 }
                    Text { text: "FLASHER"; color: textPrimary; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 19 }
                    Text { text: "CAN-OTA • REAL FIRMWARE CONTROL"; color: muted; font.family: "Bahnschrift"; font.pixelSize: 8 }
                }
                Item { Layout.fillWidth: true }
                Text { text: flasherBackend.status; color: flasherBackend.connected ? "#43db9b" : muted; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 11 }
                Text { text: "v" + flasherBackend.version; color: muted; font.family: "Bahnschrift"; font.pixelSize: 10 }
            }
        }
    }

    Dialog {
        id: confirm
        anchors.centerIn: parent
        modal: true
        width: 440
        title: flasherBackend.uiText("QT_CONFIRM_CAN_OTA")
        standardButtons: Dialog.Cancel
        background: Rectangle { color: window.panel; radius: 16; border.width: 1; border.color: window.panelBorder }
        contentItem: ColumnLayout {
            spacing: 14
            Text { text: flasherBackend.uiText("QT_CONFIRM_CAN_OTA_BODY"); color: window.textPrimary; wrapMode: Text.WordWrap; Layout.preferredWidth: 380 }
            GameButton { text: flasherBackend.uiText("QT_CONFIRM_FLASH"); Layout.fillWidth: true; onClicked: { confirm.close(); flasherBackend.confirmCanOtaFlash() } }
        }
    }

    Dialog {
        id: configConfirm
        anchors.centerIn: parent
        modal: true
        width: 440
        title: window.pendingConfigTitle
        standardButtons: Dialog.Cancel
        background: Rectangle { color: window.panel; radius: 16; border.width: 1; border.color: window.panelBorder }
        contentItem: ColumnLayout {
            spacing: 14
            Text { text: window.pendingConfigBody; color: window.textPrimary; wrapMode: Text.WordWrap; Layout.preferredWidth: 380 }
            GameButton {
                text: flasherBackend.uiText("BTN_SAVE")
                accent: "#b86a35"
                Layout.fillWidth: true
                onClicked: { configConfirm.close(); if (window.pendingConfigAction) window.pendingConfigAction() }
            }
        }
    }

    FileDialog {
        id: swdBootloaderDialog
        title: flasherBackend.uiText("LBL_BOOTLOADER_FILE")
        fileMode: FileDialog.OpenFile
        nameFilters: ["Bootloader image (*.bin *.hex *.elf *.axf)", "All files (*)"]
        onAccepted: flasherBackend.setSwdBootloaderPath(selectedFile.toString())
    }
    FileDialog {
        id: swdAppDialog
        title: flasherBackend.uiText("LBL_APPLICATION_FILE")
        fileMode: FileDialog.OpenFile
        nameFilters: ["Application image (*.bin *.hex *.elf *.axf)", "All files (*)"]
        onAccepted: flasherBackend.setSwdAppPath(selectedFile.toString())
    }
    FileDialog {
        id: swdBackupDialog
        title: "Save flash backup as..."
        fileMode: FileDialog.SaveFile
        nameFilters: ["Binary files (*.bin)"]
        onAccepted: window.requestFullChipFlash(selectedFile.toString().replace("file:///", ""))
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 14
        Card {
            Layout.preferredWidth: 400
            Layout.fillHeight: true
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 10
                Text { text: flasherBackend.uiText("QT_CONNECTION"); color: cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 13 }
                ComboBox { id: ports; Layout.fillWidth: true; model: flasherBackend.ports; enabled: !flasherBackend.connected && !flasherBackend.busy; onActivated: flasherBackend.selectPort(currentText) }
                RowLayout {
                    Layout.fillWidth: true
                    GameButton { text: flasherBackend.uiText("BTN_REFRESH"); accent: "#24465e"; Layout.fillWidth: true; onClicked: flasherBackend.scanPorts() }
                    GameButton { text: flasherBackend.connected ? flasherBackend.uiText("BTN_DISCONNECT") : flasherBackend.uiText("BTN_CONNECT"); Layout.fillWidth: true; enabled: !flasherBackend.busy; onClicked: flasherBackend.toggleConnection() }
                }
                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: panelBorder }
                Text { text: flasherBackend.uiText("QT_FIRMWARE_INVENTORY"); color: cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 13 }
                    GameButton { text: flasherBackend.uiText("QT_SCAN_FIRMWARE"); accent: "#24465e"; Layout.fillWidth: true; enabled: !flasherBackend.busy; onClicked: flasherBackend.scanFirmware() }
                ListView {
                    id: files
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    model: flasherBackend.firmware
                    spacing: 5
                    delegate: Rectangle {
                        width: files.width
                        height: 58
                        radius: 10
                        color: modelData.path === flasherBackend.selectedFirmware ? "#1a4967" : panelAlt
                        border.width: 1
                        border.color: modelData.valid ? panelBorder : "#9a4555"
                        Column {
                            anchors.fill: parent
                            anchors.margins: 9
                            Text { text: modelData.name; color: textPrimary; font.bold: true; elide: Text.ElideRight; width: parent.width }
                            Text { text: (modelData.valid ? flasherBackend.uiText("QT_VALID") + " • " : flasherBackend.uiText("QT_INVALID") + " • ") + modelData.reason; color: modelData.valid ? "#43db9b" : "#ee6b80"; font.pixelSize: 10; width: parent.width; elide: Text.ElideRight }
                        }
                        MouseArea { anchors.fill: parent; enabled: modelData.valid && !flasherBackend.busy; onClicked: flasherBackend.selectFirmware(modelData.path) }
                    }
                }
            }
        }
        Card {
            Layout.fillWidth: true
            Layout.fillHeight: true
            // Real scroll wrapper - added alongside the new device-
            // configuration sections below (see their own header
            // comment), since this card's real content no longer
            // reliably fits the window's own default height.
            ScrollView {
                anchors.fill: parent
                anchors.margins: 16
                clip: true
                contentWidth: availableWidth
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
            ColumnLayout {
                width: parent.width
                spacing: 12
                Text { text: flasherBackend.uiText("QT_UPDATE_CHECKPOINTS"); color: cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 14 }
                Text { text: flasherBackend.uiText("QT_CHECKPOINTS"); color: muted; font.family: "Bahnschrift"; font.pixelSize: 12; lineHeight: 1.55 }
                ProgressBar {
                    Layout.fillWidth: true
                    value: flasherBackend.progress / 100
                    background: Rectangle { radius: 5; color: "#07111e"; border.width: 1; border.color: panelBorder }
                    contentItem: Item { implicitHeight: 12; Rectangle { width: parent.width * flasherBackend.progress / 100; height: parent.height; radius: 5; color: cyan } }
                }
                Text { text: flasherBackend.progress + "%"; color: cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 20 }
                RowLayout {
                    Layout.fillWidth: true
                    GameButton { text: flasherBackend.uiText("QT_START_CAN_OTA"); Layout.fillWidth: true; enabled: flasherBackend.canFlash; onClicked: confirm.open() }
                    GameButton { text: flasherBackend.uiText("BTN_CANCEL"); accent: "#7c3543"; enabled: flasherBackend.busy; onClicked: flasherBackend.cancelFlash() }
                }
                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: panelBorder }
                Text { text: flasherBackend.uiText("QT_BOARD_SNAPSHOT"); color: cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 13 }
                Text { text: flasherBackend.uiText("QT_BOARD_SNAPSHOT_HELP"); color: muted; font.pixelSize: 9; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                GameButton { text: flasherBackend.uiText("QT_READ_BOARD_STATE"); accent: "#24465e"; Layout.fillWidth: true; enabled: flasherBackend.canReadBoardSnapshot; onClicked: flasherBackend.readBoardSnapshot() }
                Text { visible: flasherBackend.boardSnapshot.length === 0; text: flasherBackend.uiText("QT_NO_BOARD_SNAPSHOT"); color: muted; font.pixelSize: 9 }
                ListView {
                    Layout.fillWidth: true
                    Layout.preferredHeight: Math.min(contentHeight, 105)
                    visible: flasherBackend.boardSnapshot.length > 0
                    model: flasherBackend.boardSnapshot
                    clip: true
                    spacing: 2
                    delegate: Text {
                        required property var modelData
                        text: modelData.label + ": " + modelData.value
                        color: modelData.ok ? "#43db9b" : "#f7b955"
                        font.family: "Cascadia Mono"
                        font.pixelSize: 9
                        width: parent.width
                        elide: Text.ElideRight
                    }
                }
                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: panelBorder }

                // -- Device configuration writes - real, persistent
                // EEPROM fields only this tool ever writes (every other
                // real app, including URTC-TESTER's own Qt Quick deck,
                // only reads them). Each Save asks for the same real
                // confirmation the established Tkinter panel already
                // does (see flasher_gui.py's own save_expansion_board_
                // type/save_mlx_sensor_variant/program_free_tool_config/
                // program_device_serial) via the one shared configConfirm
                // dialog below.
                Text { text: flasherBackend.uiText("QT_DEVICE_CONFIG"); color: cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 13 }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 6
                    ComboBox { id: expansionTypeCombo; model: flasherBackend.expansionBoardTypeOptions; Layout.fillWidth: true }
                    GameButton {
                        text: flasherBackend.uiText("BTN_SAVE")
                        accent: "#b86a35"
                        Layout.preferredWidth: 100
                        enabled: flasherBackend.canWriteDeviceConfig
                        onClicked: window.requestConfigWrite(
                            flasherBackend.uiText("TITLE_CONFIRM_EXPANSION_BOARD_TYPE"),
                            flasherBackend.uiText("MSG_CONFIRM_EXPANSION_BOARD_TYPE").replace("{type}", expansionTypeCombo.currentText),
                            function() { flasherBackend.saveExpansionBoardType(expansionTypeCombo.currentIndex) })
                    }
                }
                Text { text: flasherBackend.expansionBoardTypeResult; visible: flasherBackend.expansionBoardTypeResult !== ""; color: muted; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 9 }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 6
                    ComboBox { id: mlxVariantCombo; model: flasherBackend.mlxSensorVariantOptions; Layout.fillWidth: true }
                    GameButton {
                        text: flasherBackend.uiText("BTN_SAVE")
                        accent: "#b86a35"
                        Layout.preferredWidth: 100
                        enabled: flasherBackend.canWriteDeviceConfig
                        onClicked: window.requestConfigWrite(
                            flasherBackend.uiText("TITLE_CONFIRM_MLX_VARIANT"),
                            flasherBackend.uiText("MSG_CONFIRM_MLX_VARIANT").replace("{type}", mlxVariantCombo.currentText),
                            function() { flasherBackend.saveMlxSensorVariant(mlxVariantCombo.currentIndex) })
                    }
                }
                Text { text: flasherBackend.mlxSensorVariantResult; visible: flasherBackend.mlxSensorVariantResult !== ""; color: muted; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 9 }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 6
                    ComboBox { id: freeToolCombo; model: flasherBackend.freeToolOptions; Layout.fillWidth: true }
                    GameButton {
                        text: flasherBackend.uiText("BTN_SAVE")
                        accent: "#b86a35"
                        Layout.preferredWidth: 100
                        enabled: flasherBackend.canWriteDeviceConfig
                        onClicked: window.requestConfigWrite(
                            flasherBackend.uiText("TITLE_CONFIRM_FREE_TOOL_CONFIG"),
                            flasherBackend.uiText("MSG_CONFIRM_FREE_TOOL_CONFIG").replace("{tool}", freeToolCombo.currentText),
                            function() { flasherBackend.saveFreeToolConfig(freeToolCombo.currentIndex) })
                    }
                }
                Text { text: flasherBackend.freeToolConfigResult; visible: flasherBackend.freeToolConfigResult !== ""; color: muted; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 9 }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 6
                    TextField { id: deviceSerialField; text: "0"; inputMethodHints: Qt.ImhDigitsOnly; color: textPrimary; placeholderText: "0-255"; Layout.fillWidth: true; background: Rectangle { radius: 8; color: panelAlt; border.width: 1; border.color: panelBorder } }
                    GameButton {
                        text: flasherBackend.uiText("BTN_SAVE")
                        accent: "#b86a35"
                        Layout.preferredWidth: 100
                        enabled: flasherBackend.canWriteDeviceConfig
                        onClicked: window.requestConfigWrite(
                            flasherBackend.uiText("TITLE_CONFIRM_DEVICE_SERIAL"),
                            flasherBackend.uiText("MSG_CONFIRM_DEVICE_SERIAL").replace("{serial}", deviceSerialField.text),
                            function() { flasherBackend.saveDeviceSerial(parseInt(deviceSerialField.text, 10) || 0) })
                    }
                }
                Text { text: flasherBackend.deviceSerialResult; visible: flasherBackend.deviceSerialResult !== ""; color: muted; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 9 }

                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: panelBorder }
                Text { text: flasherBackend.uiText("QT_ACTIVITY_LOG"); color: cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 13 }
                ListView {
                    Layout.fillWidth: true
                    // Was Layout.fillHeight: true - meaningless now that
                    // this whole ColumnLayout lives inside a ScrollView
                    // (see this Card's own comment above) rather than a
                    // fixed-height parent; a real, generous fixed
                    // viewport instead.
                    Layout.preferredHeight: 200
                    model: flasherBackend.logs
                    clip: true
                    delegate: Text { required property string modelData; text: modelData; color: muted; font.family: "Cascadia Mono"; font.pixelSize: 10; width: parent.width; wrapMode: Text.WrapAnywhere }
                }
                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: panelBorder }
                Text { text: flasherBackend.uiText("QT_ADVANCED_DIAGNOSTICS"); color: cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 13 }
                Text { text: flasherBackend.uiText("QT_SWD_JTAG_READONLY"); color: muted; font.family: "Bahnschrift"; font.pixelSize: 10 }
                Repeater {
                    model: flasherBackend.swdTools
                    delegate: Text {
                        required property var modelData
                        text: modelData.name + ": " + (modelData.available ? modelData.path : flasherBackend.uiText("QT_NOT_INSTALLED"))
                        color: modelData.available ? "#43db9b" : "#ee6b80"
                        font.family: "Cascadia Mono"
                        font.pixelSize: 9
                        width: parent.width
                        elide: Text.ElideMiddle
                    }
                }
                GameButton {
                    text: flasherBackend.swdScanning ? "..." : flasherBackend.uiText("QT_SCAN_PROBES")
                    accent: "#24465e"
                    Layout.fillWidth: true
                    enabled: !flasherBackend.busy && !flasherBackend.swdScanning
                    onClicked: flasherBackend.scanSwdProbes()
                }
                ListView {
                    Layout.fillWidth: true
                    Layout.preferredHeight: Math.min(contentHeight, 78)
                    visible: flasherBackend.swdProbes.length > 0
                    model: flasherBackend.swdProbes
                    clip: true
                    delegate: Text {
                        required property var modelData
                        text: modelData.tool + " • " + modelData.identifier + " — " + modelData.description
                        color: "#43db9b"
                        font.family: "Cascadia Mono"
                        font.pixelSize: 9
                        width: parent.width
                        elide: Text.ElideMiddle
                    }
                }
                Text {
                    visible: !flasherBackend.swdScanning && flasherBackend.swdProbes.length === 0
                    text: flasherBackend.uiText("QT_NO_PROBES")
                    color: muted
                    font.pixelSize: 9
                }
                Text {
                    text: flasherBackend.uiText("QT_SWD_SAFETY_NOTE")
                    color: muted
                    font.pixelSize: 8
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: panelBorder }
                // -- Full-chip SWD/JTAG programming - the one real
                // destructive action this deck migrates from
                // flasher_gui.py's own start_swd_flash()/_swd_flash_worker.
                // flasher_swd_tools.py's PyOCDCLI/CubeProgrammerCLI are
                // reused completely unchanged; only the UI is new. See
                // startFullChipFlash's own docstring in qt_flasher.py.
                Text { text: flasherBackend.uiText("QT_SWD_FULL_CHIP_SECTION"); color: cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 13 }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    Text { text: flasherBackend.uiText("LBL_SWD_TARGET"); color: muted; font.pixelSize: 9 }
                    RadioButton {
                        id: swdTargetMaster
                        text: flasherBackend.uiText("OPT_TARGET_MASTER")
                        checked: flasherBackend.swdTarget === "master"
                        enabled: !flasherBackend.busy
                        contentItem: Text { text: swdTargetMaster.text; color: muted; leftPadding: swdTargetMaster.indicator.width + 4; verticalAlignment: Text.AlignVCenter; font.pixelSize: 9 }
                        onToggled: if (checked) flasherBackend.setSwdTarget("master")
                    }
                    RadioButton {
                        id: swdTargetSlave
                        text: flasherBackend.uiText("OPT_TARGET_SLAVE")
                        checked: flasherBackend.swdTarget === "slave"
                        enabled: !flasherBackend.busy
                        contentItem: Text { text: swdTargetSlave.text; color: muted; leftPadding: swdTargetSlave.indicator.width + 4; verticalAlignment: Text.AlignVCenter; font.pixelSize: 9 }
                        onToggled: if (checked) flasherBackend.setSwdTarget("slave")
                    }
                }
                Text { text: flasherBackend.uiText("HELP_SWD_TARGET_SLAVE"); color: muted; font.pixelSize: 8; wrapMode: Text.WordWrap; Layout.fillWidth: true }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    RadioButton {
                        id: swdToolPyocd
                        text: flasherBackend.uiText("RADIO_PYOCD_BUILTIN")
                        checked: flasherBackend.swdTool === "pyocd"
                        enabled: !flasherBackend.busy
                        contentItem: Text { text: swdToolPyocd.text; color: muted; leftPadding: swdToolPyocd.indicator.width + 4; verticalAlignment: Text.AlignVCenter; font.pixelSize: 9 }
                        onToggled: if (checked) flasherBackend.setSwdTool("pyocd")
                    }
                    RadioButton {
                        id: swdToolCube
                        text: flasherBackend.uiText("RADIO_STM32CUBEPROGRAMMER")
                        checked: flasherBackend.swdTool === "cube"
                        enabled: !flasherBackend.busy
                        contentItem: Text { text: swdToolCube.text; color: muted; leftPadding: swdToolCube.indicator.width + 4; verticalAlignment: Text.AlignVCenter; font.pixelSize: 9 }
                        onToggled: if (checked) flasherBackend.setSwdTool("cube")
                    }
                }

                // Only the probes that answer to the currently selected
                // tool (see swdMatchingProbes' own docstring) - clicking
                // one selects it for the actual flash below.
                Text { text: flasherBackend.uiText("LBL_PROBE"); color: muted; font.pixelSize: 9; visible: flasherBackend.swdMatchingProbes.length > 0 }
                ListView {
                    Layout.fillWidth: true
                    Layout.preferredHeight: Math.min(contentHeight, 84)
                    visible: flasherBackend.swdMatchingProbes.length > 0
                    model: flasherBackend.swdMatchingProbes
                    clip: true
                    spacing: 3
                    delegate: Rectangle {
                        required property var modelData
                        width: ListView.view.width
                        height: 24
                        radius: 6
                        color: flasherBackend.swdSelectedProbe === modelData.identifier ? "#1a4967" : "transparent"
                        border.width: 1
                        border.color: flasherBackend.swdSelectedProbe === modelData.identifier ? "#43db9b" : panelBorder
                        Text {
                            anchors.fill: parent
                            anchors.margins: 4
                            text: modelData.identifier + " - " + modelData.description
                            color: muted
                            font.family: "Cascadia Mono"
                            font.pixelSize: 9
                            elide: Text.ElideMiddle
                            verticalAlignment: Text.AlignVCenter
                        }
                        MouseArea { anchors.fill: parent; enabled: !flasherBackend.busy; onClicked: flasherBackend.setSwdSelectedProbe(modelData.identifier) }
                    }
                }
                Text {
                    visible: flasherBackend.swdNeedsProbeChoice
                    text: flasherBackend.uiText("MSG_MULTIPLE_PROBES_PICK_ONE_FULLCHIP")
                    color: "#f7b955"
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 6
                    Text { text: flasherBackend.uiText("LBL_BOOTLOADER_FILE"); color: muted; font.pixelSize: 9; Layout.preferredWidth: 120; wrapMode: Text.WordWrap }
                    TextField {
                        id: swdBootloaderField
                        text: flasherBackend.swdBootloaderPath
                        color: textPrimary
                        Layout.fillWidth: true
                        background: Rectangle { radius: 8; color: panelAlt; border.width: 1; border.color: panelBorder }
                        onEditingFinished: flasherBackend.setSwdBootloaderPath(text)
                    }
                    GameButton { text: flasherBackend.uiText("BTN_BROWSE"); accent: "#24465e"; Layout.preferredWidth: 90; enabled: !flasherBackend.busy; onClicked: swdBootloaderDialog.open() }
                }
                Text {
                    visible: swdBootloaderField.text !== "" && !flasherBackend.swdBootloaderValid
                    text: flasherBackend.uiText("TITLE_BOOTLOADER_FILE_LOOKS_INVALID") + ": " + flasherBackend.swdBootloaderReason
                    color: "#f7b955"
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 6
                    Text { text: flasherBackend.uiText("LBL_APPLICATION_FILE"); color: muted; font.pixelSize: 9; Layout.preferredWidth: 120; wrapMode: Text.WordWrap }
                    TextField {
                        id: swdAppField
                        text: flasherBackend.swdAppPath
                        color: textPrimary
                        Layout.fillWidth: true
                        background: Rectangle { radius: 8; color: panelAlt; border.width: 1; border.color: panelBorder }
                        onEditingFinished: flasherBackend.setSwdAppPath(text)
                    }
                    GameButton { text: flasherBackend.uiText("BTN_BROWSE"); accent: "#24465e"; Layout.preferredWidth: 90; enabled: !flasherBackend.busy; onClicked: swdAppDialog.open() }
                }
                Text {
                    visible: swdAppField.text !== "" && !flasherBackend.swdAppValid
                    text: flasherBackend.uiText("TITLE_APPLICATION_FILE_LOOKS_INVALID") + ": " + flasherBackend.swdAppReason
                    color: "#f7b955"
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                CheckBox {
                    id: swdDryRunCheck
                    text: flasherBackend.uiText("CHK_DRY_RUN")
                    checked: flasherBackend.swdDryRun
                    enabled: !flasherBackend.busy
                    contentItem: Text { text: swdDryRunCheck.text; color: muted; leftPadding: swdDryRunCheck.indicator.width + 4; verticalAlignment: Text.AlignVCenter; wrapMode: Text.WordWrap; width: swdDryRunCheck.width - swdDryRunCheck.indicator.width - 4; font.pixelSize: 9 }
                    onToggled: { flasherBackend.setSwdDryRun(checked); checked = flasherBackend.swdDryRun }
                }
                CheckBox {
                    id: swdBackupCheck
                    text: flasherBackend.uiText("CHK_BACKUP_BEFORE_ERASING")
                    checked: flasherBackend.swdBackup
                    enabled: !flasherBackend.busy
                    contentItem: Text { text: swdBackupCheck.text; color: muted; leftPadding: swdBackupCheck.indicator.width + 4; verticalAlignment: Text.AlignVCenter; wrapMode: Text.WordWrap; width: swdBackupCheck.width - swdBackupCheck.indicator.width - 4; font.pixelSize: 9 }
                    onToggled: { flasherBackend.setSwdBackup(checked); checked = flasherBackend.swdBackup }
                }

                GameButton {
                    text: flasherBackend.uiText("BTN_CHECK_OPTION_BYTES")
                    accent: "#24465e"
                    Layout.fillWidth: true
                    enabled: flasherBackend.canCheckSwdOptionBytes
                    onClicked: flasherBackend.checkSwdOptionBytes()
                }
                Text {
                    visible: flasherBackend.swdOptionByteText !== ""
                    text: flasherBackend.swdOptionByteText
                    color: muted
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                    font.pixelSize: 9
                }
                Text {
                    text: flasherBackend.uiText("HELP_RDP_CHECK_READONLY")
                    color: muted
                    font.pixelSize: 8
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                GameButton {
                    id: fullChipFlashButton
                    text: flasherBackend.uiText("BTN_FLASH_COMPLETE_CHIP")
                    accent: "#b86a35"
                    Layout.fillWidth: true
                    enabled: flasherBackend.canFullChipFlash
                    onClicked: {
                        // Same real condition as flasher_gui.py's own
                        // start_swd_flash(): a backup is only ever taken
                        // for a real (non-dry-run) flash - matches
                        // startFullChipFlash's own dry_run short-circuit.
                        if (swdBackupCheck.checked && !swdDryRunCheck.checked) {
                            swdBackupDialog.open()
                        } else {
                            window.requestFullChipFlash("")
                        }
                    }
                }
                Text {
                    visible: flasherBackend.swdFlashResult !== ""
                    text: flasherBackend.swdFlashResult
                    color: flasherBackend.swdFlashResult.indexOf("FAILED") >= 0 || flasherBackend.swdFlashResult.indexOf("UNEXPECTED") >= 0 ? "#ee6b80" : "#43db9b"
                    font.family: "Cascadia Mono"
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                    font.pixelSize: 9
                }
                Text {
                    text: flasherBackend.uiText("HELP_ERASES_WHOLE_CHIP")
                    color: "#f7b955"
                    font.pixelSize: 8
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }
            }
            }
        }
    }
}
