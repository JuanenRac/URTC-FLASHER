// =============================================================================
// URTC Flasher - Qt Quick CAN-OTA command deck
// Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
// GPL-3.0-or-later - see LICENSE
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
    property bool closeApproved: false
    onClosing: function(close) {
        // A transfer in progress is never abandoned by accident.
        if (flasherBackend.busy && !closeApproved) {
            close.accepted = false
            closeConfirm.open()
        }
    }

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
    // earlier Tk window's own messagebox.askyesno.
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
        // Explicit, not left implicit - a real on-screen check showed this
        // ToolBar's own Basic-style implicit sizing collapsing to 0 height
        // for this window (branding/status text all overlapping at the
        // top-left corner instead of laid out in a row), the same real bug
        // HYDRA-UMC-SUITE's own Qt Quick shell already found and fixed the
        // same way - never propagated back to this sibling app until now.
        // Sized to comfortably fit the 50px icon box plus this Card's own
        // 7px and this RowLayout's own 10px margins top and bottom
        // (50 + 2*7 + 2*10).
        height: 84
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
                Text { text: flasherBackend.status; color: flasherBackend.statusColor; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 11 }
                ComboBox {
                    id: languageBox
                    model: flasherBackend.languageNames
                    currentIndex: flasherBackend.languageIndex
                    Layout.preferredWidth: 130
                    font.pixelSize: 11
                    onActivated: function(index) { languageNotice.text = flasherBackend.selectLanguage(index) }
                }
                Text { id: languageNotice; visible: text !== ""; color: "#e0b04a"; font.pixelSize: 10; Layout.maximumWidth: 220; wrapMode: Text.WordWrap }
                Text { text: "v" + flasherBackend.version; color: muted; font.family: "Bahnschrift"; font.pixelSize: 10 }
            }
        }
    }

    Dialog {
        id: confirm
        anchors.centerIn: parent
        modal: true
        width: 440
        title: flasherBackend.flashConfirmTitle
        standardButtons: Dialog.Cancel
        background: Rectangle { color: window.panel; radius: 16; border.width: 1; border.color: window.panelBorder }
        contentItem: ColumnLayout {
            spacing: 14
            Text { text: flasherBackend.flashConfirmBody; color: window.textPrimary; wrapMode: Text.WordWrap; Layout.preferredWidth: 380 }
            GameButton {
                text: flasherBackend.uiText("QT_CONFIRM_FLASH")
                Layout.fillWidth: true
                onClicked: {
                    confirm.close()
                    // The anti-rollback bypass always gets its own, second prompt.
                    if (flasherBackend.allowDowngrade)
                        downgradeConfirm.open()
                    else
                        flasherBackend.confirmCanOtaFlash()
                }
            }
        }
    }

    Dialog {
        id: downgradeConfirm
        anchors.centerIn: parent
        modal: true
        width: 440
        title: flasherBackend.downgradeConfirmTitle
        standardButtons: Dialog.Cancel
        background: Rectangle { color: window.panel; radius: 16; border.width: 1; border.color: "#b86a35" }
        contentItem: ColumnLayout {
            spacing: 14
            Text { text: flasherBackend.downgradeConfirmBody; color: window.textPrimary; wrapMode: Text.WordWrap; Layout.preferredWidth: 380 }
            GameButton {
                text: flasherBackend.uiText("QT_CONFIRM_FLASH")
                accent: "#b86a35"
                Layout.fillWidth: true
                onClicked: { downgradeConfirm.close(); flasherBackend.confirmDowngrade(); flasherBackend.confirmCanOtaFlash() }
            }
        }
    }

    HelpDialog {
        id: helpDialog
        objectName: "helpDialog"
        model: flasherBackend.help
        panelColor: window.panel
        borderColor: window.panelBorder
        textColor: window.textPrimary
        mutedColor: window.muted
        accentColor: window.cyan
    }

    UpdateDialog {
        id: updateDialog
        objectName: "updateDialog"
        model: flasherBackend.updates
        panelColor: window.panel
        borderColor: window.panelBorder
        textColor: window.textPrimary
        mutedColor: window.muted
        accentColor: window.cyan
    }

    Dialog {
        id: aboutDialog
        anchors.centerIn: parent
        modal: true
        width: Math.min(parent.width - 48, 640)
        height: Math.min(parent.height - 48, 560)
        title: flasherBackend.uiText("TITLE_ABOUT")
        standardButtons: Dialog.Close
        property string shownText: ""
        onOpened: shownText = ""
        background: Rectangle { color: window.panel; radius: 16; border.width: 1; border.color: window.panelBorder }
        contentItem: ColumnLayout {
            spacing: 10
            Text { text: flasherBackend.aboutText; color: window.textPrimary; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            RowLayout {
                Layout.fillWidth: true
                GameButton { text: flasherBackend.uiText("MENU_README"); accent: "#24465e"; Layout.fillWidth: true; onClicked: aboutDialog.shownText = flasherBackend.readmeText() }
                GameButton { text: flasherBackend.uiText("MENU_LICENSE"); accent: "#24465e"; Layout.fillWidth: true; onClicked: aboutDialog.shownText = flasherBackend.licenseText() }
                GameButton { text: flasherBackend.uiText("MENU_GITHUB"); accent: "#24465e"; Layout.fillWidth: true; onClicked: Qt.openUrlExternally(flasherBackend.githubUrl) }
            }
            ScrollView {
                visible: aboutDialog.shownText.length > 0
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                TextArea {
                    text: aboutDialog.shownText
                    readOnly: true
                    wrapMode: Text.WordWrap
                    color: window.textPrimary
                    font.family: "Cascadia Mono"
                    font.pixelSize: 10
                    background: Rectangle { color: window.panelAlt; radius: 8 }
                }
            }
        }
    }

    FileDialog {
        id: readbackDialog
        title: flasherBackend.uiText("TITLE_SAVE_READBACK")
        fileMode: FileDialog.SaveFile
        nameFilters: ["Binary files (*.bin)"]
        onAccepted: flasherBackend.startReadback(selectedFile.toString())
    }
    FileDialog {
        id: saveLogDialog
        title: flasherBackend.uiText("MENU_SAVE_LOGS")
        fileMode: FileDialog.SaveFile
        nameFilters: ["Text (*.txt)"]
        onAccepted: flasherBackend.saveLogText(selectedFile.toString())
    }
    FileDialog {
        id: debugBundleDialog
        title: flasherBackend.uiText("TITLE_SAVE_DEBUG_BUNDLE")
        fileMode: FileDialog.SaveFile
        nameFilters: ["ZIP (*.zip)"]
        onAccepted: flasherBackend.exportDebugBundle(selectedFile.toString())
    }

    Dialog {
        id: githubDialog
        anchors.centerIn: parent
        modal: true
        width: Math.min(parent.width - 48, 620)
        height: Math.min(parent.height - 48, 480)
        title: flasherBackend.uiText("TITLE_DOWNLOAD_FROM_GITHUB")
        standardButtons: Dialog.Close
        background: Rectangle { color: window.panel; radius: 16; border.width: 1; border.color: window.panelBorder }
        onOpened: flasherBackend.loadRelease("")
        contentItem: ColumnLayout {
            spacing: 8
            RowLayout {
                Layout.fillWidth: true
                Text { text: flasherBackend.uiText("LBL_GITHUB_RELEASE_TAG"); color: muted; font.pixelSize: 11 }
                TextField { id: releaseTag; color: textPrimary; Layout.preferredWidth: 120; font.pixelSize: 11; onAccepted: flasherBackend.loadRelease(text); background: Rectangle { radius: 8; color: panelAlt; border.width: 1; border.color: panelBorder } }
                GameButton { text: flasherBackend.uiText("BTN_GITHUB_LOAD"); accent: "#24465e"; enabled: !flasherBackend.releaseBusy; onClicked: flasherBackend.loadRelease(releaseTag.text) }
            }
            Text { text: flasherBackend.releaseStatus; color: muted; font.pixelSize: 10; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            ListView {
                id: releaseList
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: 4
                model: flasherBackend.releaseImages
                currentIndex: -1
                delegate: Rectangle {
                    required property int index
                    required property var modelData
                    width: releaseList.width
                    height: 34
                    radius: 8
                    color: releaseList.currentIndex === index ? "#1a4967" : panelAlt
                    border.width: 1
                    border.color: panelBorder
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 8
                        Text { text: modelData.name; color: textPrimary; elide: Text.ElideRight; Layout.fillWidth: true; font.pixelSize: 11 }
                        Text { text: modelData.size; color: muted; font.pixelSize: 10 }
                    }
                    MouseArea { anchors.fill: parent; onClicked: releaseList.currentIndex = index }
                }
            }
            ProgressBar {
                Layout.fillWidth: true
                value: flasherBackend.releaseProgress / 100
                background: Rectangle { radius: 5; color: "#07111e"; border.width: 1; border.color: panelBorder }
                contentItem: Item { implicitHeight: 8; Rectangle { width: parent.width * flasherBackend.releaseProgress / 100; height: parent.height; radius: 5; color: cyan } }
            }
            GameButton {
                text: flasherBackend.uiText("BTN_DOWNLOAD_SELECTED")
                Layout.fillWidth: true
                enabled: releaseList.currentIndex >= 0 && !flasherBackend.releaseBusy
                onClicked: flasherBackend.downloadReleaseFile(releaseList.model[releaseList.currentIndex].name)
            }
        }
    }

    Dialog {
        id: releaseOverwriteConfirm
        anchors.centerIn: parent
        modal: true
        width: 440
        visible: flasherBackend.releaseOverwriteName.length > 0
        title: flasherBackend.uiText("TITLE_FILE_EXISTS")
        standardButtons: Dialog.NoButton
        closePolicy: Popup.NoAutoClose
        background: Rectangle { color: window.panel; radius: 16; border.width: 1; border.color: "#b86a35" }
        contentItem: ColumnLayout {
            spacing: 14
            Text { text: flasherBackend.releaseOverwriteQuestion; color: window.textPrimary; wrapMode: Text.WordWrap; Layout.preferredWidth: 380 }
            RowLayout {
                Layout.fillWidth: true
                GameButton { text: flasherBackend.uiText("BTN_CANCEL"); accent: "#24465e"; Layout.fillWidth: true; onClicked: flasherBackend.cancelReleaseOverwrite() }
                GameButton { text: flasherBackend.uiText("BTN_ACCEPT"); accent: "#b86a35"; Layout.fillWidth: true; onClicked: flasherBackend.confirmReleaseOverwrite() }
            }
        }
    }

    Dialog {
        id: closeConfirm
        anchors.centerIn: parent
        modal: true
        width: 440
        title: flasherBackend.closeWhileBusyTitle
        standardButtons: Dialog.Cancel
        background: Rectangle { color: window.panel; radius: 16; border.width: 1; border.color: "#b86a35" }
        contentItem: ColumnLayout {
            spacing: 14
            Text { text: flasherBackend.closeWhileBusyBody; color: window.textPrimary; wrapMode: Text.WordWrap; Layout.preferredWidth: 380 }
            GameButton {
                text: flasherBackend.uiText("BTN_CLOSE")
                accent: "#b86a35"
                Layout.fillWidth: true
                onClicked: { closeConfirm.close(); window.closeApproved = true; flasherBackend.prepareToQuit(); window.close() }
            }
        }
    }

    Dialog {
        id: invalidFirmwareConfirm
        anchors.centerIn: parent
        modal: true
        width: 440
        visible: flasherBackend.invalidFirmwareReason.length > 0
        title: flasherBackend.uiText("TITLE_FILE_LOOKS_INVALID")
        standardButtons: Dialog.NoButton
        closePolicy: Popup.NoAutoClose
        background: Rectangle { color: window.panel; radius: 16; border.width: 1; border.color: "#b86a35" }
        contentItem: ColumnLayout {
            spacing: 14
            Text { text: flasherBackend.invalidFirmwareReason; color: window.textPrimary; wrapMode: Text.WordWrap; Layout.preferredWidth: 380 }
            RowLayout {
                Layout.fillWidth: true
                GameButton { text: flasherBackend.uiText("BTN_CANCEL"); accent: "#24465e"; Layout.fillWidth: true; onClicked: flasherBackend.rejectInvalidFirmware() }
                GameButton { text: flasherBackend.uiText("BTN_ACCEPT"); accent: "#b86a35"; Layout.fillWidth: true; onClicked: flasherBackend.acceptInvalidFirmware() }
            }
        }
    }

    FileDialog {
        id: firmwareBrowseDialog
        title: flasherBackend.uiText("TITLE_SELECT_URTC_FIRMWARE")
        fileMode: FileDialog.OpenFile
        nameFilters: ["Firmware (*.bin)", "All files (*)"]
        onAccepted: flasherBackend.addFirmwareFile(selectedFile.toString())
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
        title: flasherBackend.uiText("QT_SWD_BACKUP_DIALOG_TITLE")
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
                    Text { text: flasherBackend.uiText("LBL_BITRATE"); color: "#9fb4c4"; font.pixelSize: 12 }
                    ComboBox { id: bitrateBox; Layout.fillWidth: true; model: flasherBackend.bitrateLabels; currentIndex: Math.max(0, flasherBackend.bitrateLabels.indexOf(flasherBackend.selectedBitrate)); enabled: !flasherBackend.connected && !flasherBackend.busy; onActivated: flasherBackend.selectBitrate(currentText) }
                    GameButton { text: flasherBackend.uiText("BTN_AUTO_DETECT"); accent: "#24465e"; enabled: !flasherBackend.connected && !flasherBackend.busy; onClicked: flasherBackend.autoDetectBitrate() }
                }
                RowLayout {
                    Layout.fillWidth: true
                    GameButton { text: flasherBackend.uiText("BTN_REFRESH"); accent: "#24465e"; Layout.fillWidth: true; onClicked: flasherBackend.scanPorts() }
                    GameButton { text: flasherBackend.connected ? flasherBackend.uiText("BTN_DISCONNECT") : flasherBackend.uiText("BTN_CONNECT"); Layout.fillWidth: true; enabled: !flasherBackend.busy; onClicked: flasherBackend.toggleConnection() }
                }
                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: panelBorder }
                Text { text: flasherBackend.uiText("QT_FIRMWARE_INVENTORY"); color: cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 13 }
                RowLayout {
                    Layout.fillWidth: true
                    GameButton { text: flasherBackend.uiText("QT_SCAN_FIRMWARE"); accent: "#24465e"; Layout.fillWidth: true; enabled: !flasherBackend.busy; onClicked: flasherBackend.scanFirmware() }
                    GameButton { text: flasherBackend.uiText("BTN_BROWSE_BIN"); accent: "#24465e"; Layout.fillWidth: true; enabled: !flasherBackend.busy; onClicked: firmwareBrowseDialog.open() }
                }
                GameButton { text: flasherBackend.uiText("BTN_DOWNLOAD_FROM_GITHUB"); accent: "#24465e"; Layout.fillWidth: true; enabled: !flasherBackend.busy; onClicked: githubDialog.open() }
                Text { visible: flasherBackend.signingWarning.length > 0; text: flasherBackend.signingWarning; color: "#ee6b80"; font.pixelSize: 10; wrapMode: Text.WordWrap; Layout.fillWidth: true }
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
                Text {
                    visible: flasherBackend.transferSpeedText.length > 0
                    text: flasherBackend.transferSpeedText
                    color: muted
                    font.family: "Cascadia Mono"
                    font.pixelSize: 11
                }
                Text {
                    visible: flasherBackend.transferStalledText.length > 0
                    text: flasherBackend.transferStalledText
                    color: "#e0a030"
                    font.family: "Cascadia Mono"
                    font.pixelSize: 11
                }
                // Which chip is flashed, and the options that only exist for the main board.
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    Text { text: flasherBackend.uiText("LBL_FLASH_TARGET"); color: muted; font.pixelSize: 12 }
                    RadioButton { text: flasherBackend.uiText("OPT_TARGET_MASTER"); checked: flasherBackend.flashTarget === "master"; enabled: !flasherBackend.busy; onClicked: flasherBackend.setFlashTarget("master"); palette.windowText: textPrimary }
                    RadioButton { text: flasherBackend.uiText("OPT_TARGET_SLAVE"); checked: flasherBackend.flashTarget === "slave"; enabled: !flasherBackend.busy; onClicked: flasherBackend.setFlashTarget("slave"); palette.windowText: textPrimary }
                }
                Text { text: flasherBackend.uiText("HELP_FLASH_TARGET_SLAVE"); color: muted; font.pixelSize: 9; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                RowLayout {
                    Layout.fillWidth: true
                    CheckBox { text: flasherBackend.uiText("CHK_BOARD_RUNNING_APP"); checked: flasherBackend.triggerBootloader; enabled: !flasherBackend.busy; onToggled: flasherBackend.setTriggerBootloader(checked); palette.windowText: textPrimary }
                    CheckBox { text: flasherBackend.uiText("CHK_ERASE_FRAM_BEFORE_FLASHING"); checked: flasherBackend.eraseFram; enabled: !flasherBackend.busy && flasherBackend.downgradeOptionsAvailable; onToggled: flasherBackend.setEraseFram(checked); palette.windowText: textPrimary }
                }
                Text { text: flasherBackend.uiText("HELP_UNCHECK_IF_IN_BOOTLOADER"); color: muted; font.pixelSize: 9; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                RowLayout {
                    Layout.fillWidth: true
                    CheckBox { text: flasherBackend.uiText("CHK_ALLOW_DOWNGRADE"); checked: flasherBackend.allowDowngrade; enabled: !flasherBackend.busy && flasherBackend.downgradeOptionsAvailable; onToggled: flasherBackend.setAllowDowngrade(checked); palette.windowText: textPrimary }
                    GameButton { text: flasherBackend.uiText("BTN_BACKUP_FIRMWARE_CAN"); accent: "#24465e"; Layout.fillWidth: true; enabled: flasherBackend.canReadback; onClicked: readbackDialog.open() }
                }
                Text { text: flasherBackend.uiText("HELP_ALLOW_DOWNGRADE"); color: "#e0a030"; font.pixelSize: 9; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                Text { text: flasherBackend.uiText("HELP_BACKUP_FIRMWARE_CAN"); color: muted; font.pixelSize: 9; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                Text { visible: flasherBackend.readbackResult.length > 0; text: flasherBackend.readbackResult; color: "#43db9b"; font.pixelSize: 10; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                RowLayout {
                    Layout.fillWidth: true
                    GameButton { text: flasherBackend.uiText("QT_START_CAN_OTA"); Layout.fillWidth: true; enabled: flasherBackend.canFlash; onClicked: confirm.open() }
                    GameButton { text: flasherBackend.uiText("BTN_CANCEL"); accent: "#7c3543"; enabled: flasherBackend.busy; onClicked: flasherBackend.cancelFlash() }
                }
                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: panelBorder }
                Text { text: flasherBackend.uiText("QT_BOARD_SNAPSHOT"); color: cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 13 }
                Text { text: flasherBackend.uiText("QT_BOARD_SNAPSHOT_HELP"); color: muted; font.pixelSize: 9; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                GameButton { text: flasherBackend.uiText("QT_READ_BOARD_STATE"); accent: "#24465e"; Layout.fillWidth: true; enabled: flasherBackend.canReadBoardSnapshot; onClicked: flasherBackend.readBoardSnapshot() }
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: flasherBackend.uiText("LBL_BUS_ACTIVITY"); color: muted; font.pixelSize: 11 }
                    GameButton { text: flasherBackend.uiText("BTN_CHECK_2S"); accent: "#24465e"; enabled: flasherBackend.connected && !flasherBackend.busy; onClicked: flasherBackend.checkBusActivity() }
                    Text { text: flasherBackend.busActivityText; color: "#43db9b"; font.family: "Cascadia Mono"; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight }
                }
                RowLayout {
                    Layout.fillWidth: true
                    GameButton { text: flasherBackend.uiText("TITLE_SAVE_DEBUG_BUNDLE"); accent: "#24465e"; Layout.fillWidth: true; onClicked: debugBundleDialog.open() }
                    GameButton { text: flasherBackend.uiText("MENU_SAVE_LOGS"); accent: "#24465e"; Layout.fillWidth: true; onClicked: saveLogDialog.open() }
                    GameButton { text: flasherBackend.updates.t("UPD_BTN_CHECK"); accent: "#24465e"; Layout.fillWidth: true; onClicked: updateDialog.open() }
                    GameButton { text: flasherBackend.help.title; accent: "#24465e"; Layout.fillWidth: true; onClicked: helpDialog.open() }
                    GameButton { text: flasherBackend.uiText("TITLE_ABOUT"); accent: "#24465e"; Layout.fillWidth: true; onClicked: aboutDialog.open() }
                }
                Text { visible: flasherBackend.exportResult.length > 0; text: flasherBackend.exportResult; color: muted; font.pixelSize: 9; wrapMode: Text.WordWrap; Layout.fillWidth: true }
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
                // confirmation the earlier Tk window already
                // does (see the earlier Tk window's own save_expansion_board_
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
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: flasherBackend.uiText("QT_ACTIVITY_LOG"); color: cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 13; Layout.fillWidth: true }
                    Rectangle {
                        id: copyIconButton
                        property bool copied: false
                        Layout.preferredWidth: 36
                        Layout.preferredHeight: 30
                        radius: 8
                        color: copyIconMouse.containsMouse ? "#1b3c52" : "#102a3b"
                        border.width: 1
                        border.color: copyIconButton.copied ? "#5df0c4" : "#264966"
                        Item {
                            anchors.centerIn: parent
                            width: 18; height: 18
                            Rectangle { x: 6; y: 0; width: 11; height: 12; radius: 2; color: "transparent"; border.width: 1.6; border.color: copyIconButton.copied ? "#5df0c4" : "#9fd8e3" }
                            Rectangle { x: 1; y: 5; width: 11; height: 12; radius: 2; color: copyIconMouse.containsMouse ? "#1b3c52" : "#102a3b"; border.width: 1.6; border.color: copyIconButton.copied ? "#5df0c4" : "#9fd8e3" }
                        }
                        TextEdit { id: copyHelper; visible: false }
                        Timer { id: copiedTimer; interval: 1400; onTriggered: copyIconButton.copied = false }
                        MouseArea {
                            id: copyIconMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                copyHelper.text = flasherBackend.logs.join("\n"); copyHelper.selectAll(); copyHelper.copy(); copyHelper.deselect()
                                copyIconButton.copied = true; copiedTimer.restart()
                            }
                        }
                    }
                }
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
                // the earlier Tk window's own start_swd_flash()/_swd_flash_worker.
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
                        // Same real condition as the earlier Tk window's own
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
