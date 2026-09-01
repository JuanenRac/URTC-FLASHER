// =============================================================================
// URTC Flasher - Qt Quick CAN-OTA command deck
// Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
// GPL-3.0 - see LICENSE
// =============================================================================
import QtQuick
import QtQuick.Controls
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
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
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
                Text { text: flasherBackend.uiText("QT_ACTIVITY_LOG"); color: cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 13 }
                ListView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    model: flasherBackend.logs
                    clip: true
                    delegate: Text { required property string modelData; text: modelData; color: muted; font.family: "Cascadia Mono"; font.pixelSize: 10; width: parent.width; wrapMode: Text.WrapAnywhere }
                    }
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
            }
        }
}
