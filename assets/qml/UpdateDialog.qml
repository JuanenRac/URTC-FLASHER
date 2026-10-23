// =============================================================================
// URTC-COMMON - qml/UpdateDialog.qml
// Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
// GPL-3.0-or-later - see LICENSE
// =============================================================================
// The "Check for updates" window of the programs. `model` is an UpdateModel (update_qt.py); the colours are
// properties so each program gives its own. Nothing here installs by itself: the install button asks first.
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
    property color errorColor: "#e07a7a"

    anchors.centerIn: parent
    modal: true
    width: Math.min(parent ? parent.width - 48 : 560, 560)
    title: model ? model.t("UPD_TITLE") : ""
    closePolicy: model && model.busy ? Dialog.NoAutoClose : Dialog.CloseOnEscape
    background: Rectangle { color: dialog.panelColor; radius: 16; border.width: 1; border.color: dialog.borderColor }
    onOpened: if (model && !model.busy) model.dismiss()

    contentItem: ColumnLayout {
        spacing: 10
        Text {
            Layout.fillWidth: true
            text: model ? model.statusText : ""
            color: model && model.isError ? dialog.errorColor : dialog.textColor
            wrapMode: Text.WordWrap
            font.pixelSize: 13
            visible: text.length > 0
        }
        ProgressBar {
            Layout.fillWidth: true
            from: 0
            to: 100
            value: model ? model.progress : 0
            visible: model && model.state === "downloading"
        }
        Text {
            visible: model && model.notes.length > 0 && (model.state === "available" || model.state === "ready")
            text: model ? model.t("UPD_NOTES") : ""
            color: dialog.accentColor
            font.bold: true
            font.pixelSize: 11
        }
        ScrollView {
            visible: model && model.notes.length > 0 && (model.state === "available" || model.state === "ready")
            Layout.fillWidth: true
            Layout.preferredHeight: 120
            clip: true
            TextArea {
                readOnly: true
                text: model ? model.notes : ""
                wrapMode: Text.WordWrap
                color: dialog.textColor
                font.pixelSize: 11
                background: Rectangle { color: Qt.darker(dialog.panelColor, 1.2); radius: 8 }
            }
        }
        Text {
            Layout.fillWidth: true
            text: model ? model.t("UPD_NEVER_AUTO") : ""
            color: dialog.mutedColor
            wrapMode: Text.WordWrap
            font.pixelSize: 10
        }
        CheckBox {
            id: autoBox
            text: model ? model.t("UPD_OPT_AUTO") : ""
            checked: model ? model.autoCheck : false
            enabled: model && !model.busy
            palette.windowText: dialog.textColor
            onToggled: {
                if (model.needsWarningForAuto(checked)) { pendingOption = "auto"; pendingValue = checked; warn.open() }
                else model.setAutoCheck(checked)
            }
        }
        CheckBox {
            id: confirmBox
            text: model ? model.t("UPD_OPT_CONFIRM") : ""
            checked: model ? model.requireConfirmation : true
            enabled: model && !model.busy
            palette.windowText: dialog.textColor
            onToggled: {
                if (model.needsWarningForConfirmation(checked)) { pendingOption = "confirm"; pendingValue = checked; warn.open() }
                else model.setRequireConfirmation(checked)
            }
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            Button { text: model ? model.t("UPD_BTN_CHECK") : ""; enabled: model && model.canCheck; onClicked: model.check() }
            Button { text: model ? model.t("UPD_BTN_DOWNLOAD") : ""; visible: model && model.canDownload; onClicked: model.download() }
            Button {
                text: model ? model.t("UPD_BTN_INSTALL").replace("{version}", model.version) : ""
                visible: model && model.canInstall
                onClicked: installConfirm.open()
            }
            Button { text: model ? model.t("UPD_BTN_ROLLBACK") : ""; visible: model && model.canRollBack; onClicked: model.rollBack() }
            Item { Layout.fillWidth: true }
            Button { text: model ? model.t("UPD_BTN_CLOSE") : ""; enabled: model && !model.busy; onClicked: dialog.close() }
        }
    }

    property string pendingOption: ""
    property bool pendingValue: false

    Dialog {
        id: warn
        anchors.centerIn: parent
        modal: true
        width: 400
        title: model ? model.t("UPD_TITLE") : ""
        background: Rectangle { color: dialog.panelColor; radius: 12; border.width: 1; border.color: dialog.borderColor }
        contentItem: Text { text: model ? model.t("UPD_OPT_LOWER") : ""; color: dialog.textColor; wrapMode: Text.WordWrap }
        footer: DialogButtonBox {
            Button { text: model ? model.t("UPD_BTN_CANCEL") : ""; DialogButtonBox.buttonRole: DialogButtonBox.RejectRole }
            Button { text: model ? model.t("UPD_BTN_YES") : ""; DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole }
        }
        onAccepted: {
            if (dialog.pendingOption === "auto") model.setAutoCheck(dialog.pendingValue)
            else model.setRequireConfirmation(dialog.pendingValue)
        }
        onRejected: { autoBox.checked = model.autoCheck; confirmBox.checked = model.requireConfirmation }
    }

    Dialog {
        id: installConfirm
        anchors.centerIn: parent
        modal: true
        width: 400
        title: model ? model.t("UPD_TITLE") : ""
        background: Rectangle { color: dialog.panelColor; radius: 12; border.width: 1; border.color: dialog.borderColor }
        contentItem: Text { text: model ? model.t("UPD_CONFIRM").replace("{version}", model.version) : ""; color: dialog.textColor; wrapMode: Text.WordWrap }
        footer: DialogButtonBox {
            Button { text: model ? model.t("UPD_BTN_CANCEL") : ""; DialogButtonBox.buttonRole: DialogButtonBox.RejectRole }
            Button { text: model ? model.t("UPD_BTN_YES") : ""; DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole }
        }
        onAccepted: model.install()
    }
}
