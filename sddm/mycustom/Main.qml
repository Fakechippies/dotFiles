import QtQuick 2.15
import SddmComponents 2.0

Rectangle {
    id: root
    width: Screen.width
    height: Screen.height
    color: "#000000"

    property int sessionIndex: session.index

    // === BACKGROUND GIF ===
    AnimatedImage {
        id: backgroundImage
        anchors.fill: parent
        source: Qt.resolvedUrl("assets/background.gif")
        fillMode: Image.PreserveAspectCrop
        playing: true
        cache: false
    }

    // Darkening overlay
    Rectangle {
        anchors.fill: parent
        color: "#00000060"
    }

    // === LOGIN BOX ===
    Rectangle {
        id: loginBox
        width: parent.width * 0.28
        height: parent.height * 0.40
        anchors.centerIn: parent
        radius: 20
        color: "#1a1a1a95"
        border.color: "#ffffff15"
        border.width: 1

        Column {
            anchors.centerIn: parent
            spacing: 25

            Text {
                text: "Welcome Back"
                color: "#ffffff"
                font.pixelSize: 36
                font.bold: true
                horizontalAlignment: Text.AlignHCenter
                anchors.horizontalCenter: parent.horizontalCenter
            }

            // Username field
            Rectangle {
                id: usernameBox
                width: loginBox.width * 0.75
                height: 50
                color: "#00000050"
                radius: 10
                border.color: usernameInput.activeFocus ? "#3b82f6" : "#ffffff15"
                border.width: 2

                Row {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 10

                    Text {
                        text: "👤"
                        color: "#ffffff80"
                        font.pixelSize: 18
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    TextInput {
                        id: usernameInput
                        width: parent.width - 30
                        height: parent.height
                        color: "#ffffff"
                        font.pixelSize: 15
                        verticalAlignment: TextInput.AlignVCenter
                        selectByMouse: true
                        selectionColor: "#3b82f6"
                        text: userModel.lastUser

                        Text {
                            text: "Username"
                            color: "#ffffff60"
                            font.pixelSize: 15
                            anchors.verticalCenter: parent.verticalCenter
                            visible: usernameInput.text.length === 0
                        }

                        Keys.onTabPressed: passwordInput.forceActiveFocus()
                        Keys.onReturnPressed: passwordInput.forceActiveFocus()
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: usernameInput.forceActiveFocus()
                    cursorShape: Qt.IBeamCursor
                }
            }

            // Password field
            Rectangle {
                id: passwordBox
                width: loginBox.width * 0.75
                height: 50
                color: "#00000050"
                radius: 10
                border.color: passwordInput.activeFocus ? "#3b82f6" : "#ffffff15"
                border.width: 2

                Row {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 10

                    Text {
                        text: "🔒"
                        color: "#ffffff80"
                        font.pixelSize: 18
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    TextInput {
                        id: passwordInput
                        width: parent.width - 30
                        height: parent.height
                        color: "#ffffff"
                        font.pixelSize: 15
                        verticalAlignment: TextInput.AlignVCenter
                        echoMode: TextInput.Password
                        selectByMouse: true
                        selectionColor: "#3b82f6"

                        Text {
                            text: "Password"
                            color: "#ffffff60"
                            font.pixelSize: 15
                            anchors.verticalCenter: parent.verticalCenter
                            visible: passwordInput.text.length === 0
                        }

                        Keys.onReturnPressed: loginButton.clicked()
                        Keys.onTabPressed: loginButton.forceActiveFocus()
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: passwordInput.forceActiveFocus()
                    cursorShape: Qt.IBeamCursor
                }
            }

            // Login button
            Item {
                width: loginBox.width * 0.5
                height: 45
                anchors.horizontalCenter: parent.horizontalCenter

                Rectangle {
                    id: loginButton
                    anchors.fill: parent
                    color: loginButtonArea.pressed ? "#2563eb" : (parent.activeFocus ? "#2563eb" : "#3b82f6")
                    radius: 10

                    Text {
                        text: "Login"
                        color: "white"
                        font.pixelSize: 16
                        font.bold: true
                        anchors.centerIn: parent
                    }

                    MouseArea {
                        id: loginButtonArea
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            sddm.login(usernameInput.text, passwordInput.text, sessionIndex)
                        }
                    }
                }

                focus: true
                Keys.onReturnPressed: sddm.login(usernameInput.text, passwordInput.text, sessionIndex)
                Keys.onEnterPressed: sddm.login(usernameInput.text, passwordInput.text, sessionIndex)
                Keys.onTabPressed: usernameInput.forceActiveFocus()
            }

            // Session indicator
            Text {
                text: session.current
                color: "#ffffff60"
                font.pixelSize: 12
                anchors.horizontalCenter: parent.horizontalCenter
            }
        }
    }

    // Session selector (hidden)
    ComboBox {
        id: session
        visible: false
        width: 0
        height: 0
        model: sessionModel
        index: sessionModel.lastIndex
    }

    // Connect to SDDM components
    Connections {
        target: sddm
        function onLoginFailed() {
            passwordInput.text = ""
            passwordInput.forceActiveFocus()
        }
    }

    Component.onCompleted: {
        if (usernameInput.text === "") {
            usernameInput.forceActiveFocus()
        } else {
            passwordInput.forceActiveFocus()
        }
    }
}
