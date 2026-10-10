import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Shapes

ApplicationWindow {
    id: root
    width: 420
    height: 540
    visible: true
    color: "transparent"

    // Top-level window flags: frameless, stay on top, popup tool
    flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool

    // Current navigation tab: "home", "chat", "echo"
    property string activeTab: "home"
    property bool daemonConnected: false

    // Close on Escape key
    Shortcut {
        sequence: "Escape"
        onActivated: root.hide()
    }

    // Main Rounded Background Card (OLED Coucou Style)
    Rectangle {
        id: container
        anchors.fill: parent
        radius: 24
        color: "#0c0c0e"
        border.color: "#14ffffff"
        border.width: 1
        clip: true

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            // Top Header (42px)
            Rectangle {
                Layout.fillWidth: true
                height: 42
                color: "#12141a"
                border.color: "#0affffff"
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 16
                    anchors.rightMargin: 12
                    spacing: 12

                    // Status Indicator Dot
                    Rectangle {
                        width: 8
                        height: 8
                        radius: 4
                        color: root.daemonConnected ? "#10b981" : "#ef4444"
                    }

                    Text {
                        text: "Ekko"
                        font.pixelSize: 13
                        font.bold: true
                        color: "#f8fafc"
                    }

                    Item { Layout.fillWidth: true }

                    // Navigation Tabs Pill
                    Row {
                        spacing: 6

                        // Home Tab
                        Rectangle {
                            width: 28
                            height: 28
                            radius: 14
                            color: root.activeTab === "home" ? "#1effffff" : "transparent"
                            Text {
                                anchors.centerIn: parent
                                text: "💧"
                                font.pixelSize: 13
                            }
                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.activeTab = "home"
                            }
                        }

                        // Chat Tab
                        Rectangle {
                            width: 28
                            height: 28
                            radius: 14
                            color: root.activeTab === "chat" ? "#1effffff" : "transparent"
                            Text {
                                anchors.centerIn: parent
                                text: "💬"
                                font.pixelSize: 12
                            }
                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.activeTab = "chat"
                            }
                        }

                        // Echo Tab
                        Rectangle {
                            width: 28
                            height: 28
                            radius: 14
                            color: root.activeTab === "echo" ? "#1effffff" : "transparent"
                            Text {
                                anchors.centerIn: parent
                                text: "⚡"
                                font.pixelSize: 12
                            }
                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    root.activeTab = "echo"
                                    bridge.getNotes()
                                }
                            }
                        }
                    }

                    // Close Button
                    Rectangle {
                        width: 24
                        height: 24
                        radius: 12
                        color: "transparent"
                        Text {
                            anchors.centerIn: parent
                            text: "✕"
                            font.pixelSize: 12
                            color: "#94a3b8"
                        }
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.hide()
                        }
                    }
                }
            }

            // Body Stack
            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                // VIEW 1: HOME
                Item {
                    id: homeView
                    anchors.fill: parent
                    visible: root.activeTab === "home"

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 20
                        spacing: 16

                        Item { Layout.fillHeight: true }

                        // Center Mascot
                        Mascot {
                            Layout.alignment: Qt.AlignHCenter
                        }

                        // Drop Area Card
                        Rectangle {
                            id: dropBox
                            Layout.fillWidth: true
                            height: 120
                            radius: 16
                            color: dropTarget.containsDrag ? "#1e293b" : "#131722"
                            border.color: dropTarget.containsDrag ? "#38bdf8" : "#14ffffff"
                            border.width: dropTarget.containsDrag ? 2 : 1

                            ColumnLayout {
                                anchors.centerIn: parent
                                spacing: 6

                                Text {
                                    Layout.alignment: Qt.AlignHCenter
                                    text: "Déposer un fichier ou une URL"
                                    font.pixelSize: 13
                                    font.bold: true
                                    color: "#f8fafc"
                                }

                                Text {
                                    Layout.alignment: Qt.AlignHCenter
                                    text: "Indexation automatique et instantanée"
                                    font.pixelSize: 11
                                    color: "#64748b"
                                }
                            }

                            DropArea {
                                id: dropTarget
                                anchors.fill: parent
                                onDropped: (drop) => {
                                    if (drop.hasUrls) {
                                        for (var i = 0; i < drop.urls.length; i++) {
                                            bridge.ingestFilePath(drop.urls[i])
                                        }
                                        root.activeTab = "chat"
                                    } else if (drop.hasText) {
                                        bridge.submitPrompt(drop.text)
                                        root.activeTab = "chat"
                                    }
                                }
                            }
                        }

                        // Telemetry Badge
                        Rectangle {
                            Layout.alignment: Qt.AlignHCenter
                            width: 170
                            height: 24
                            radius: 12
                            color: "#141824"
                            border.color: "#0fffffff"
                            border.width: 1

                            Text {
                                anchors.centerIn: parent
                                text: "nice +10 • VRAM 0M • socket OK"
                                font.pixelSize: 10
                                color: "#64748b"
                            }
                        }

                        Item { Layout.fillHeight: true }
                    }
                }

                // VIEW 2: CHAT
                ChatView {
                    id: chatTab
                    visible: root.activeTab === "chat"
                }

                // VIEW 3: ECHO (NOTES)
                Item {
                    id: echoView
                    anchors.fill: parent
                    visible: root.activeTab === "echo"

                    ListView {
                        id: notesList
                        anchors.fill: parent
                        anchors.margins: 14
                        clip: true
                        spacing: 8
                        model: ListModel { id: notesModel }

                        delegate: Rectangle {
                            width: notesList.width
                            height: 80
                            radius: 12
                            color: "#161b26"
                            border.color: "#0fffffff"
                            border.width: 1

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 4

                                Text {
                                    Layout.fillWidth: true
                                    text: model.title
                                    font.pixelSize: 12
                                    font.bold: true
                                    color: "#f8fafc"
                                    elide: Text.ElideRight
                                }

                                Text {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    text: model.summary
                                    font.pixelSize: 11
                                    color: "#94a3b8"
                                    elide: Text.ElideRight
                                    wrapMode: Text.WordWrap
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // Connect Bridge Signals
    Connections {
        target: bridge

        function onDaemonStatusChanged(isOnline) {
            root.daemonConnected = isOnline
        }

        function onNotesLoaded(notes) {
            notesModel.clear()
            for (var i = 0; i < notes.length; i++) {
                notesModel.append(notes[i])
            }
        }

        function onResponseChunkReceived(chunk) {
            // If current last message is not from assistant, create one
            var count = chatTab.listModel.count
            if (count > 0 && chatTab.listModel.get(count - 1).isUser) {
                chatTab.listModel.append({
                    isUser: false,
                    content: chunk
                })
            } else if (count > 0) {
                var prev = chatTab.listModel.get(count - 1).content
                chatTab.listModel.setProperty(count - 1, "content", prev + chunk)
            }
        }

        function onPromptCompleted(fullResponse) {
            chatTab.isStreaming = false
            var count = chatTab.listModel.count
            if (count > 0 && !chatTab.listModel.get(count - 1).isUser) {
                chatTab.listModel.setProperty(count - 1, "content", fullResponse)
            } else {
                chatTab.listModel.append({
                    isUser: false,
                    content: fullResponse
                })
            }
        }

        function onErrorOccurred(errMsg) {
            chatTab.isStreaming = false
            chatTab.errorMessage = errMsg
        }
    }

    Component.onCompleted: {
        bridge.checkDaemonStatus()
    }
}
