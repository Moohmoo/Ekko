"""Native PySide6/QML Desktop Pod application entry point for Ekko."""

from pathlib import Path
import sys

# Ensure current script directory is in sys.path when invoked from project root
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PySide6.QtCore import QEvent, QObject, Qt, QUrl
from PySide6.QtGui import QGuiApplication, QScreen
from PySide6.QtQml import QQmlApplicationEngine

from bridge import EkkoBridge


class WindowFocusFilter(QObject):
    """Event filter that hides the root window when user clicks outside or window deactivates."""

    def __init__(self, window: QObject) -> None:
        super().__init__(window)
        self._window = window

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.WindowDeactivate:
            # Hide popover when clicking outside
            if hasattr(self._window, "hide"):
                self._window.hide()
        return super().eventFilter(watched, event)


def main() -> None:
    """Run native PySide6/QML application."""
    app = QGuiApplication(sys.argv)
    app.setApplicationName("Ekko Desktop Pod")
    app.setOrganizationName("Ekko")

    engine = QQmlApplicationEngine()

    # Instantiate Bridge and expose as context property
    bridge = EkkoBridge()
    engine.rootContext().setContextProperty("bridge", bridge)

    qml_file = Path(__file__).parent / "qml" / "App.qml"
    engine.load(QUrl.fromLocalFile(str(qml_file)))

    if not engine.rootObjects():
        sys.exit(-1)

    window = engine.rootObjects()[0]

    # Position in top-right corner with 20px margin
    screen = QGuiApplication.primaryScreen()
    if screen:
        geo = screen.availableGeometry()
        x = geo.x() + geo.width() - 420 - 20
        y = geo.y() + 40
        window.setProperty("x", x)
        window.setProperty("y", y)

    # Attach focus filter for auto-hide on click outside
    focus_filter = WindowFocusFilter(window)
    window.installEventFilter(focus_filter)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
