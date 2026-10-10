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

    // Main Rounded Background Card (OLED Coucou Style: radius 28, #0c0c0e)
    Rectangle {
        id: container
        anchors.fill: parent
        radius: 28
        color: "#0c0c0e"
        border.color: "#14ffffff"
        border.width: 1
        clip: true

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            // Minimalist Icon Header (height 40px, padding horizontal 16px, zero text)
            Rectangle {
                Layout.fillWidth: true
                height: 40
                color: "#11141c"
                border.color: "#0affffff"
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 16
                    anchors.rightMargin: 16
                    spacing: 8

                    // Navigation Tabs on Left (💧, 💬, ⚡)
                    Row {
                        spacing: 6

                        // Home Tab (Goutte)
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

                        // Chat Tab (Bulle)
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

                        // Echo Tab (Fiches / Sparkles)
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

                    Item { Layout.fillWidth: true }

                    // Right Side: Discreet Status Dot & Close Button
                    Row {
                        spacing: 12
                        Layout.alignment: Qt.AlignVCenter

                        // Discreet Status Dot
                        Rectangle {
                            width: 7
                            height: 7
                            radius: 3.5
                            anchors.verticalCenter: parent.verticalCenter
                            color: root.daemonConnected ? "#10b981" : "#ef4444"
                        }

                        // Close Button (fine cross 14px)
                        Rectangle {
                            width: 22
                            height: 22
                            radius: 11
                            color: "transparent"
                            anchors.verticalCenter: parent.verticalCenter
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

                        // Drop & Forget Area (Dotted border, Inter font, 11px #94a3b8)
                        Rectangle {
                            id: dropBox
                            Layout.fillWidth: true
                            height: 115
                            radius: 16
                            color: dropTarget.containsDrag ? "#1e293b" : "#08ffffff"

                            // Dotted border via Shape
                            Shape {
                                anchors.fill: parent
                                ShapePath {
                                    strokeColor: dropTarget.containsDrag ? "#38bdf8" : "#26ffffff"
                                    strokeWidth: 1.2
                                    strokeStyle: ShapePath.DashLine
                                    dashPattern: [3, 3]
                                    fillColor: "transparent"

                                    startX: 16; startY: 0
                                    PathLine { x: dropBox.width - 16; y: 0 }
                                    PathArc { x: dropBox.width; y: 16; radiusX: 16; radiusY: 16 }
                                    PathLine { x: dropBox.width; y: dropBox.height - 16 }
                                    PathArc { x: dropBox.width - 16; y: dropBox.height; radiusX: 16; radiusY: 16 }
                                    PathLine { x: 16; y: dropBox.height }
                                    PathArc { x: 0; y: dropBox.height - 16; radiusX: 16; radiusY: 16 }
                                    PathLine { x: 0; y: 16 }
                                    PathArc { x: 16; y: 0; radiusX: 16; radiusY: 16 }
                                }
                            }

                            ColumnLayout {
                                anchors.centerIn: parent
                                spacing: 5

                                Text {
                                    Layout.alignment: Qt.AlignHCenter
                                    text: "Déposer un fichier ou une URL"
                                    font.family: "Inter"
                                    font.pixelSize: 13
                                    font.bold: true
                                    color: "#f8fafc"
                                }

                                Text {
                                    Layout.alignment: Qt.AlignHCenter
                                    text: "Indexation automatique et instantanée"
                                    font.family: "Inter"
                                    font.pixelSize: 11
                                    color: "#94a3b8"
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
                                font.family: "Inter"
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
                                    font.family: "Inter"
                                    font.pixelSize: 12
                                    font.bold: true
                                    color: "#f8fafc"
                                    elide: Text.ElideRight
                                }

                                Text {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    text: model.summary
                                    font.family: "Inter"
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
