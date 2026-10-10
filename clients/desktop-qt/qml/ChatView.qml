import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: chatView
    anchors.fill: parent

    property alias listModel: messageModel
    property bool isStreaming: false
    property string errorMessage: ""

    ListModel {
        id: messageModel
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 10

        // Error banner if any
        Rectangle {
            Layout.fillWidth: true
            height: 32
            radius: 8
            color: "#3f1418"
            border.color: "#ef4444"
            border.width: 1
            visible: chatView.errorMessage.length > 0

            Text {
                anchors.centerIn: parent
                text: chatView.errorMessage
                color: "#fca5a5"
                font.pixelSize: 11
                elide: Text.ElideRight
            }
        }

        // Message List
        ListView {
            id: chatList
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: messageModel
            spacing: 10
            boundsBehavior: Flickable.StopAtBounds

            onCountChanged: {
                Qt.callLater(() => chatList.positionViewAtEnd())
            }

            delegate: Column {
                width: chatList.width
                spacing: 4

                Row {
                    width: parent.width
                    layoutDirection: model.isUser ? Qt.RightToLeft : Qt.LeftToRight

                    Rectangle {
                        width: Math.min(textItem.implicitWidth + 24, chatList.width * 0.82)
                        height: textItem.implicitHeight + 18
                        radius: 14
                        color: model.isUser ? "#0284c7" : "#181d29"
                        border.color: model.isUser ? "#38bdf8" : "#14ffffff"
                        border.width: 1

                        TextEdit {
                            id: textItem
                            anchors.fill: parent
                            anchors.margins: 10
                            text: model.content
                            color: "#f8fafc"
                            font.pixelSize: 12
                            wrapMode: TextEdit.Wrap
                            readOnly: true
                            selectByMouse: true
                        }
                    }
                }
            }
        }

        // Input Bar
        Rectangle {
            Layout.fillWidth: true
            height: 44
            radius: 22
            color: "#161b26"
            border.color: "#1effffff"
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 14
                anchors.rightMargin: 6
                spacing: 8

                TextInput {
                    id: promptInput
                    Layout.fillWidth: true
                    color: "#f8fafc"
                    font.pixelSize: 13
                    clip: true
                    selectByMouse: true

                    Text {
                        anchors.fill: parent
                        text: "Demander à Ekko..."
                        color: "#64748b"
                        font.pixelSize: 13
                        visible: !promptInput.text && !promptInput.activeFocus
                    }

                    onAccepted: sendButton.clicked()
                }

                // Send Button
                Rectangle {
                    id: sendButton
                    width: 32
                    height: 32
                    radius: 16
                    color: promptInput.text.trim().length > 0 && !chatView.isStreaming ? "#38bdf8" : "#2d3748"

                    signal clicked()

                    Text {
                        anchors.centerIn: parent
                        text: "↑"
                        font.pixelSize: 16
                        font.bold: true
                        color: promptInput.text.trim().length > 0 && !chatView.isStreaming ? "#050811" : "#64748b"
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: sendButton.clicked()
                    }

                    onClicked: {
                        var text = promptInput.text.trim()
                        if (text.length > 0 && !chatView.isStreaming) {
                            messageModel.append({
                                isUser: true,
                                content: text
                            })
                            promptInput.text = ""
                            chatView.isStreaming = true
                            chatView.errorMessage = ""
                            bridge.submitPrompt(text)
                        }
                    }
                }
            }
        }
    }
}
