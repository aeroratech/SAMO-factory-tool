import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QTabWidget,
    QLabel,
)
from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication, QIcon
import os
from info import InfoTab
from update import UpdateTab
from test import TestTab


def resource_path(relative_path):
    """Return an asset path that works both from source and PyInstaller."""
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base_path / relative_path

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("SAMO Factory Tool")
        self.setWindowIcon(QIcon(str(resource_path("assets/app-icon.png"))))
        self.resize(600, 600)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # create three pages
        self.tab_info = InfoTab()
        self.tab_upgrade = UpdateTab()
        self.tab_test = TestTab()

        self.tabs.addTab(self.tab_info, "Info")
        self.tabs.addTab(self.tab_upgrade, "Update")
        self.tabs.addTab(self.tab_test, "TEST")

    def center_window(self):
        """Center the main window on the primary screen."""
        screen = QGuiApplication.primaryScreen()
        if not screen:
            return

        # Use frame geometry so borders/titlebar are accounted for
        qr = self.frameGeometry()
        cp = screen.availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def showEvent(self, event):
        """Ensure the window is centered after it is shown."""
        super().showEvent(event)
        # Defer centering until after the window is fully shown/layouted
        QTimer.singleShot(0, self.center_window)

    def closeEvent(self, event):
        # Stop any threads in child tabs
        if hasattr(self.tab_test, "adb_thread") and self.tab_test.adb_thread.isRunning():
            self.tab_test.adb_thread.stop()
            self.tab_test.adb_thread.wait()

        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
