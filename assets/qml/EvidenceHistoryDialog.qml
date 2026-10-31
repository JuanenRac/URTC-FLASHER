// =============================================================================
// URTC-COMMON - qml/EvidenceHistoryDialog.qml
// Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
// GPL-3.0-or-later - see LICENSE
// =============================================================================
// The history of the evidence the programs wrote. `model` is an EvidenceHistoryModel (evidence_history_qt.py); the colours are properties so each
// program gives its own. Nothing here changes anything: the window only shows.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Dialog {
    id: dialog
    objectName: "evidenceHistoryDialog"
    property var model
    property color panelColor: "#101d30"
    property color borderColor: "#294965"
    property color textColor: "#edf7ff"
    property color mutedColor: "#91a8bd"
    property color accentColor: "#38d4e6"
    property color okColor: "#5fcf8a"
    property color warnColor: "#e0b45a"
    property color badColor: "#ef6f6f"

    function outcomeColor(outcome) {
        return outcome === "pass" ? okColor : (outcome === "skipped" ? mutedColor : (outcome === "" ? mutedColor : badColor))
    }

    anchors.centerIn: parent
    modal: true
    width: Math.min(parent ? parent.width - 48 : 900, 900)
    height: Math.min(parent ? parent.height - 48 : 640, 640)
    title: model ? model.title : ""
    standardButtons: Dialog.NoButton
    onAboutToShow: if (model) model.refresh()
    background: Rectangle { color: dialog.panelColor; radius: 16; border.width: 1; border.color: dialog.borderColor }

    contentItem: ColumnLayout {
        spacing: 8
        Text {
            Layout.fillWidth: true
            text: model ? model.intro : ""
            color: dialog.mutedColor
            wrapMode: Text.WordWrap
            font.pixelSize: 12
        }
        Text {
            Layout.fillWidth: true
            visible: text !== ""
            text: model ? model.folderText : ""
            color: dialog.mutedColor
            elide: Text.ElideMiddle
            font.pixelSize: 11
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            TextField {
                id: searchField
                objectName: "historySearch"
                Layout.fillWidth: true
                placeholderText: model ? model.searchHint : ""
                onTextChanged: if (model && text !== model.query) model.setQuery(text)
            }
            ComboBox {
                id: outcomeBox
                objectName: "historyOutcome"
                Layout.preferredWidth: 150
                model: dialog.model ? dialog.model.outcomeChoices : []
                currentIndex: dialog.model ? dialog.model.outcomeIndex : 0
                onActivated: (index) => { if (dialog.model) dialog.model.setOutcomeIndex(index) }
            }
            CheckBox {
                id: invalidBox
                objectName: "historyOnlyInvalid"
                text: dialog.model ? dialog.model.onlyInvalidText : ""
                checked: dialog.model ? dialog.model.onlyInvalid : false
                onToggled: if (dialog.model) dialog.model.setOnlyInvalid(checked)
                contentItem: Text { text: invalidBox.text; color: dialog.textColor; leftPadding: invalidBox.indicator.width + 6; verticalAlignment: Text.AlignVCenter; font.pixelSize: 12 }
            }
        }
        Text {
            Layout.fillWidth: true
            text: model ? model.summaryText : ""
            color: dialog.accentColor
            font.pixelSize: 12
        }
        Text {
            Layout.fillWidth: true
            visible: text !== ""
            text: model ? model.emptyText : ""
            color: dialog.warnColor
            wrapMode: Text.WordWrap
            font.pixelSize: 12
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            Repeater {
                model: dialog.model ? dialog.model.headers : []
                delegate: Text {
                    required property var modelData
                    required property int index
                    Layout.preferredWidth: [170, 80, 90, 150, 130, 120, 90][index]
                    Layout.fillWidth: index === 4
                    text: modelData
                    color: dialog.accentColor
                    font.bold: true
                    font.pixelSize: 12
                    elide: Text.ElideRight
                }
            }
        }
        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            ColumnLayout {
                width: dialog.width - 64
                spacing: 6
                Repeater {
                    model: dialog.model ? dialog.model.rows : []
                    delegate: ColumnLayout {
                        required property var modelData
                        Layout.fillWidth: true
                        spacing: 2
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            Text { Layout.preferredWidth: 170; text: modelData.time; color: dialog.textColor; font.pixelSize: 12; elide: Text.ElideRight }
                            Text { Layout.preferredWidth: 80; text: modelData.kindText; color: dialog.textColor; font.pixelSize: 12; elide: Text.ElideRight }
                            Text { Layout.preferredWidth: 90; text: modelData.outcomeText; color: dialog.outcomeColor(modelData.outcome); font.pixelSize: 12; elide: Text.ElideRight }
                            Text { Layout.preferredWidth: 150; text: modelData.tool; color: dialog.textColor; font.pixelSize: 12; elide: Text.ElideRight }
                            Text { Layout.preferredWidth: 130; Layout.fillWidth: true; text: modelData.board; color: dialog.textColor; font.pixelSize: 12; elide: Text.ElideRight }
                            Text { Layout.preferredWidth: 120; text: modelData.version; color: dialog.textColor; font.pixelSize: 12; elide: Text.ElideRight }
                            Text { Layout.preferredWidth: 90; text: modelData.checkText; color: modelData.valid ? dialog.okColor : dialog.badColor; font.bold: !modelData.valid; font.pixelSize: 12 }
                        }
                        Text {
                            Layout.fillWidth: true
                            text: modelData.file
                            color: dialog.mutedColor
                            font.pixelSize: 10
                            elide: Text.ElideMiddle
                        }
                        Repeater {
                            model: modelData.problems
                            delegate: Text {
                                required property var modelData
                                Layout.fillWidth: true
                                text: modelData
                                color: dialog.badColor
                                wrapMode: Text.WordWrap
                                font.pixelSize: 11
                            }
                        }
                    }
                }
                Text {
                    objectName: "historyOthers"
                    Layout.fillWidth: true
                    visible: text !== ""
                    text: dialog.model ? dialog.model.othersText : ""
                    color: dialog.mutedColor
                    wrapMode: Text.WrapAnywhere
                    font.pixelSize: 11
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            Button { text: model ? model.refreshText : ""; onClicked: if (model) model.refresh() }
            Button { objectName: "historyReport"; text: model ? model.reportText : ""; onClicked: if (model) model.writeReport() }
            Text {
                Layout.fillWidth: true
                text: model ? model.reportStatus : ""
                color: dialog.mutedColor
                elide: Text.ElideMiddle
                font.pixelSize: 11
            }
            Button { text: model ? model.closeText : ""; onClicked: dialog.close() }
        }
    }
}
