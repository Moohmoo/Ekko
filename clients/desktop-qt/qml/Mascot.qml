import QtQuick
import QtQuick.Shapes

Item {
    id: mascot
    width: 140
    height: 140

    property string stateMood: "idle" // idle, alert, dizzy

    // Vertical breathing bobbing
    SequentialAnimation on y {
        loops: Animation.Infinite
        running: true
        PropertyAnimation {
            to: 5
            duration: 2000
            easing.type: Easing.InOutQuad
        }
        PropertyAnimation {
            to: 0
            duration: 2000
            easing.type: Easing.InOutQuad
        }
    }

    // Gentle scale breathing
    SequentialAnimation on scale {
        loops: Animation.Infinite
        running: true
        PropertyAnimation {
            to: 1.03
            duration: 2000
            easing.type: Easing.InOutQuad
        }
        PropertyAnimation {
            to: 0.98
            duration: 2000
            easing.type: Easing.InOutQuad
        }
    }

    // Ambient radial glow behind the drop (soft pulsing cyan halo)
    Rectangle {
        id: glow
        anchors.centerIn: parent
        width: 110
        height: 120
        radius: 55
        color: "#00f2fe"
        opacity: 0.15
        z: 0

        SequentialAnimation on scale {
            loops: Animation.Infinite
            running: true
            PropertyAnimation { to: 1.05; duration: 2000; easing.type: Easing.InOutQuad }
            PropertyAnimation { to: 0.95; duration: 2000; easing.type: Easing.InOutQuad }
        }

        SequentialAnimation on opacity {
            loops: Animation.Infinite
            running: true
            PropertyAnimation { to: 0.22; duration: 2000; easing.type: Easing.InOutQuad }
            PropertyAnimation { to: 0.12; duration: 2000; easing.type: Easing.InOutQuad }
        }
    }

    // High-Fidelity Pear Droplet Vector Body using Shape
    Shape {
        id: bodyShape
        anchors.centerIn: parent
        width: 96
        height: 116
        z: 1

        ShapePath {
            strokeColor: "#38bdf8"
            strokeWidth: 1.2
            fillGradient: LinearGradient {
                x1: 48; y1: 0; x2: 48; y2: 116
                GradientStop { position: 0.0; color: "#00f2fe" }
                GradientStop { position: 0.35; color: "#38bdf8" }
                GradientStop { position: 0.75; color: "#0284c7" }
                GradientStop { position: 1.0; color: "#1e3a8a" }
            }

            // Continuous organic pear droplet contour (tapered top, bulbous lower base)
            startX: 48; startY: 8
            // Right shoulder down to bulbous right base
            PathCubic { control1X: 68; control1Y: 30; control2X: 92; control2Y: 62; x: 92; y: 84 }
            // Smooth bottom curve
            PathCubic { control1X: 92; control1Y: 106; control2X: 72; control2Y: 114; x: 48; y: 114 }
            // Bulbous left base
            PathCubic { control1X: 24; control1Y: 114; control2X: 4; control2Y: 106; x: 4; y: 84 }
            // Left shoulder up to tapered top peak
            PathCubic { control1X: 4; control1Y: 62; control2X: 28; control2Y: 30; x: 48; y: 8 }
        }
    }

    // Detached Left Satellite Hand (floating 8px from side)
    Rectangle {
        id: leftHand
        width: 13
        height: 13
        radius: 6.5
        color: "#38bdf8"
        x: 10
        y: 68
        z: 2

        SequentialAnimation on y {
            loops: Animation.Infinite
            running: true
            PropertyAnimation { to: 73; duration: 1500; easing.type: Easing.InOutSine }
            PropertyAnimation { to: 65; duration: 1500; easing.type: Easing.InOutSine }
        }
    }

    // Detached Right Satellite Hand (floating 8px from side)
    Rectangle {
        id: rightHand
        width: 13
        height: 13
        radius: 6.5
        color: "#38bdf8"
        x: 117
        y: 68
        z: 2

        SequentialAnimation on y {
            loops: Animation.Infinite
            running: true
            PropertyAnimation { to: 65; duration: 1500; easing.type: Easing.InOutSine }
            PropertyAnimation { to: 73; duration: 1500; easing.type: Easing.InOutSine }
        }
    }

    // Left Expressive Eye (dark #040814 almond shaped, placed low on face)
    Rectangle {
        id: leftEye
        width: 7
        height: 10
        radius: 3.5
        color: "#040814"
        x: 58
        y: 58
        z: 3

        Rectangle {
            width: 2.2
            height: 2.2
            radius: 1.1
            color: "#ffffff"
            x: 3.2
            y: 1.6
        }
    }

    // Right Expressive Eye (dark #040814 almond shaped, placed low on face)
    Rectangle {
        id: rightEye
        width: 7
        height: 10
        radius: 3.5
        color: "#040814"
        x: 75
        y: 58
        z: 3

        Rectangle {
            width: 2.2
            height: 2.2
            radius: 1.1
            color: "#ffffff"
            x: 3.2
            y: 1.6
        }
    }
}
