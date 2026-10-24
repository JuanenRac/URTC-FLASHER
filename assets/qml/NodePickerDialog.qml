// =============================================================================
// URTC-COMMON - qml/NodePickerDialog.qml
// Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
// GPL-3.0-or-later - see LICENSE
// =============================================================================
// The window that finds the tool heads of a bus and selects one. `model` is a NodePickerModel (node_picker_qt.py); the colours are
// properties so each program gives its own. Nothing is selected without the confirmation, and every state a head can be in is
// written out (ready, selected, address conflict, fault, bootloader, lost), never only coloured.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Dialog {
    id: dialog
    property var model
    property color panelColor: "#101d30"
    property color borderColor: "#294965"
    property color textColor: "#edf7ff"
    property color mutedColor: "#91a8bd"
    property color accentColor: "#38d4e6"
    property color warnColor: "#e0b45a"
    property color errorColor: "#e07a7a"
    property color okColor: "#4fcf93"

    function levelColor(level) { return level === "error" ? errorColor : (level === "warning" ? warnColor : mutedColor) }
    function stateColor(status) {
        if (status === "selected") return okColor
        if (status === "ready") return accentColor
        return status === "lost" ? mutedColor : errorColor
    }

    function syncConfirm() {
        if (!model) return
        if (model.confirmText.length > 0 && !confirmBox.opened) confirmBox.open()
        else if (model.confirmText.length === 0 && confirmBox.opened) confirmBox.close()
    }
    onOpened: syncConfirm()

    anchors.centerIn: parent
    modal: true
    width: Math.min(parent ? parent.width - 48 : 680, 680)
    title: model ? model.title : ""
    standardButtons: Dialog.NoButton
    closePolicy: model && model.busy ? Dialog.NoAutoClose : Dialog.CloseOnEscape
    background: Rectangle { color: dialog.panelColor; radius: 16; border.width: 1; border.color: dialog.borderColor }

    contentItem: ColumnLayout {
        spacing: 10

        Text {
            Layout.fillWidth: true
            text: model ? model.summary : ""
            color: dialog.accentColor
            font.bold: true
            font.pixelSize: 14
            wrapMode: Text.WordWrap
        }
        Text {
            Layout.fillWidth: true
            visible: text.length > 0
            text: model ? model.switchText : ""
            color: model ? dialog.levelColor(model.switchLevel) : dialog.mutedColor
            font.pixelSize: 11
            wrapMode: Text.WordWrap
        }

        Rectangle {
            Layout.fillWidth: true
            visible: model && model.lapseText.length > 0
            color: Qt.darker(dialog.warnColor, 3.2)
            border.color: dialog.warnColor
            border.width: 1
            radius: 8
            implicitHeight: lapseLabel.implicitHeight + 16
            Text {
                id: lapseLabel
                anchors.fill: parent
                anchors.margins: 8
                text: model ? model.lapseText : ""
                color: dialog.textColor
                font.pixelSize: 12
                wrapMode: Text.WordWrap
            }
        }

        // the header of the table
        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 9
            visible: model && model.mayShowRows
            spacing: 6
            Text { Layout.preferredWidth: 80; text: model ? model.t("NP_COL_ADDRESS") : ""; color: dialog.mutedColor; font.pixelSize: 11; font.bold: true }
            Text { Layout.fillWidth: true; Layout.preferredWidth: 110; text: model ? model.t("NP_COL_TOOL") : ""; color: dialog.mutedColor; font.pixelSize: 11; font.bold: true }
            Text { Layout.preferredWidth: 90; text: model ? model.t("NP_COL_SERIAL") : ""; color: dialog.mutedColor; font.pixelSize: 11; font.bold: true }
            Text { Layout.preferredWidth: 150; text: model ? model.t("NP_COL_STATE") : ""; color: dialog.mutedColor; font.pixelSize: 11; font.bold: true }
            Item { Layout.preferredWidth: 96 }
        }
        Repeater {
            model: dialog.model && dialog.model.mayShowRows ? dialog.model.rows : []
            delegate: Rectangle {
                required property var modelData
                Layout.fillWidth: true
                implicitHeight: 38
                radius: 8
                color: modelData.mine ? Qt.darker(dialog.okColor, 3.4) : Qt.darker(dialog.panelColor, 1.15)
                border.width: 1
                border.color: modelData.mine ? dialog.okColor : dialog.borderColor
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 12
                    spacing: 6
                    Text { Layout.preferredWidth: 80; text: modelData.address; color: dialog.textColor; font.pixelSize: 13; font.bold: true }
                    Text { Layout.fillWidth: true; Layout.preferredWidth: 110; text: modelData.tool; color: dialog.textColor; font.pixelSize: 12; elide: Text.ElideRight }
                    Text { Layout.preferredWidth: 90; text: modelData.serial; color: dialog.mutedColor; font.pixelSize: 11; font.family: "Consolas" }
                    Text { Layout.preferredWidth: 150; text: modelData.status_text; color: dialog.stateColor(modelData.status); font.pixelSize: 12; font.bold: true; elide: Text.ElideRight }
                    Button {
                        Layout.preferredWidth: 96
                        implicitWidth: 96
                        text: model.t("NP_BTN_SELECT")
                        enabled: modelData.selectable && !model.busy
                        onClicked: model.ask(modelData.address)
                    }
                }
            }
        }

        Text {
            Layout.fillWidth: true
            text: model ? model.message : ""
            color: model ? dialog.levelColor(model.messageLevel) : dialog.mutedColor
            font.pixelSize: 12
            wrapMode: Text.WordWrap
        }

        CheckBox {
            id: releaseBox
            text: model ? model.t("NP_OPT_RELEASE") : ""
            checked: model ? model.releaseOnLapse : true
            enabled: model && !model.busy
            palette.windowText: dialog.textColor
            onToggled: {
                if (model.needsWarningForRelease(checked)) warn.open()
                else model.setReleaseOnLapse(checked)
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            Button { text: model ? model.t("NP_BTN_FIND") : ""; enabled: model && !model.busy; onClicked: model.find() }
            Button { text: model ? model.t("NP_BTN_RELEASE") : ""; visible: model && model.hasSelection; enabled: model && !model.busy; onClicked: model.release() }
            BusyIndicator { visible: model && model.busy; running: visible; implicitWidth: 24; implicitHeight: 24 }
            Item { Layout.fillWidth: true }
            Button { text: model ? model.t("NP_BTN_CLOSE") : ""; enabled: model && !model.busy; onClicked: dialog.close() }
        }
    }

    Dialog {
        id: confirmBox
        objectName: "confirmBox"
        anchors.centerIn: parent
        modal: true
        width: 420
        title: dialog.model ? dialog.model.title : ""
        closePolicy: Dialog.NoAutoClose
        background: Rectangle { color: dialog.panelColor; radius: 12; border.width: 1; border.color: dialog.borderColor }
        contentItem: Text { text: dialog.model ? dialog.model.confirmText : ""; color: dialog.textColor; wrapMode: Text.WordWrap; font.pixelSize: 13 }
        footer: DialogButtonBox {
            Button { text: dialog.model ? dialog.model.t("NP_BTN_CANCEL") : ""; DialogButtonBox.buttonRole: DialogButtonBox.RejectRole }
            Button { text: dialog.model ? dialog.model.t("NP_BTN_CONFIRM") : ""; DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole }
        }
        onAccepted: dialog.model.confirm()
        onRejected: dialog.model.cancel()
    }

    Connections {
        target: dialog.model
        function onChanged() { if (dialog.opened) dialog.syncConfirm() }
    }

    Dialog {
        id: warn
        anchors.centerIn: parent
        modal: true
        width: 420
        title: model ? model.title : ""
        background: Rectangle { color: dialog.panelColor; radius: 12; border.width: 1; border.color: dialog.borderColor }
        contentItem: Text { text: model ? model.t("NP_OPT_RELEASE_LOWER") : ""; color: dialog.textColor; wrapMode: Text.WordWrap }
        footer: DialogButtonBox {
            Button { text: model ? model.t("NP_BTN_CANCEL") : ""; DialogButtonBox.buttonRole: DialogButtonBox.RejectRole }
            Button { text: model ? model.t("NP_BTN_CONFIRM") : ""; DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole }
        }
        onAccepted: model.setReleaseOnLapse(false)
        onRejected: releaseBox.checked = model.releaseOnLapse
    }
}
