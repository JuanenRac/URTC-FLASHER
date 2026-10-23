// =============================================================================
// URTC-COMMON - qml/HelpDialog.qml
// Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
// GPL-3.0-or-later - see LICENSE
// =============================================================================
// The quick guide of a program. `model` is a HelpModel (help_qt.py); the colours are properties so each program gives its own.
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

    anchors.centerIn: parent
    modal: true
    width: Math.min(parent ? parent.width - 48 : 640, 640)
    height: Math.min(parent ? parent.height - 48 : 560, 560)
    title: model ? model.title : ""
    standardButtons: Dialog.NoButton
    background: Rectangle { color: dialog.panelColor; radius: 16; border.width: 1; border.color: dialog.borderColor }

    contentItem: ColumnLayout {
        spacing: 10
        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            ColumnLayout {
                width: dialog.width - 64
                spacing: 12
                Repeater {
                    model: dialog.model ? dialog.model.sections : []
                    delegate: ColumnLayout {
                        required property var modelData
                        required property int index
                        Layout.fillWidth: true
                        spacing: 3
                        Text {
                            text: (index + 1) + ". " + modelData.title
                            color: dialog.accentColor
                            font.bold: true
                            font.pixelSize: 13
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                        }
                        Text {
                            text: modelData.text
                            color: dialog.textColor
                            font.pixelSize: 12
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }
        }
        Button { text: model ? model.closeText : ""; Layout.alignment: Qt.AlignRight; onClicked: dialog.close() }
    }
}
