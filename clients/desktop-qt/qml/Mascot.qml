import QtQuick
import QtQuick.Shapes

Item {
    id: mascot
    width: 140
    height: 140

    property string stateMood: "idle" // idle, pulse, dizzy

    // Vertical breathing bobbing
    SequentialAnimation on y {
        loops: Animation.Infinite
        running: true
        PropertyAnimation {
            to: 6
            duration: 1800
            easing.type: Easing.InOutSine
        }
        PropertyAnimation {
            to: 0
            duration: 1800
            easing.type: Easing.InOutSine
        }
    }

    // Gentle scale breathing
    SequentialAnimation on scale {
        loops: Animation.Infinite
        running: true
        PropertyAnimation {
            to: 1.04
            duration: 1800
            easing.type: Easing.InOutSine
        }
        PropertyAnimation {
            to: 0.98
            duration: 1800
            easing.type: Easing.InOutSine
        }
    }

    // Ambient radial glow behind the drop
    Rectangle {
        id: glow
        anchors.centerIn: parent
        width: 110
        height: 120
        radius: 60
        color: "#00f2fe"
        opacity: 0.22
        z: 0

        SequentialAnimation on opacity {
            loops: Animation.Infinite
            running: true
            PropertyAnimation { to: 0.35; duration: 1800; easing.type: Easing.InOutSine }
            PropertyAnimation { to: 0.15; duration: 1800; easing.type: Easing.InOutSine }
        }
    }

    // Vector Droplet Body using Shape
    Shape {
        id: bodyShape
        anchors.centerIn: parent
        width: 100
        height: 120
        z: 1

        ShapePath {
            strokeColor: "#38bdf8"
            strokeWidth: 1.5
            fillGradient: LinearGradient {
                x1: 0; y1: 0; x2: 100; y2: 120
                GradientStop { position: 0.0; color: "#00f2fe" }
                GradientStop { position: 1.0; color: "#4facfe" }
            }

            // Pear / droplet curve
            startX: 50; startY: 10
            PathCubic { control1X: 70; control1Y: 35; control2X: 95; control2Y: 65; x: 95; y: 85 }
            PathCubic { control1X: 95; control1Y: 108; control2X: 75; control2Y: 118; x: 50; y: 118 }
            PathCubic { control1X: 25; control1Y: 118; control2X: 5; control2Y: 108; x: 5; y: 85 }
            PathCubic { control1X: 5; control1Y: 65; control2X: 30; control2Y: 35; x: 50; y: 10 }
        }
    }

    // Left satellite hand
    Rectangle {
        id: leftHand
        width: 14
        height: 14
        radius: 7
        color: "#38bdf8"
        x: 14
        y: 65
        z: 2

        SequentialAnimation on y {
            loops: Animation.Infinite
            running: true
            PropertyAnimation { to: 69; duration: 1400; easing.type: Easing.InOutQuad }
            PropertyAnimation { to: 62; duration: 1400; easing.type: Easing.InOutQuad }
        }
    }

    // Right satellite hand
    Rectangle {
        id: rightHand
        width: 14
        height: 14
        radius: 7
        color: "#38bdf8"
        x: 112
        y: 65
        z: 2

        SequentialAnimation on y {
            loops: Animation.Infinite
            running: true
            PropertyAnimation { to: 62; duration: 1400; easing.type: Easing.InOutQuad }
            PropertyAnimation { to: 69; duration: 1400; easing.type: Easing.InOutQuad }
        }
    }

    // Left Eye
    Rectangle {
        id: leftEye
        width: 7
        height: 10
        radius: 3.5
        color: "#050811"
        x: 58
        y: 56
        z: 3

        Rectangle {
            width: 2.5
            height: 2.5
            radius: 1.25
            color: "#ffffff"
            x: 3.5
            y: 1.5
        }
    }

    // Right Eye
    Rectangle {
        id: rightEye
        width: 7
        height: 10
        radius: 3.5
        color: "#050811"
        x: 75
        y: 56
        z: 3

        Rectangle {
            width: 2.5
            height: 2.5
            radius: 1.25
            color: "#ffffff"
            x: 3.5
            y: 1.5
        }
    }
}
