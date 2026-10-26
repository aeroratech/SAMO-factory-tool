import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QLabel,
)
from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication, QIcon
import os
from info import InfoTab
from update import UpdateTab
from test import TestTab
from settings import SettingsTab
from device_monitor import DeviceMonitorThread


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

        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)

        status_layout = QHBoxLayout()
        status_layout.addStretch()
        status_layout.addWidget(QLabel("Device status:"))
        self.device_status_label = QLabel("Offline")
        self.device_status_label.setStyleSheet("color: red; font-weight: bold;")
        status_layout.addWidget(self.device_status_label)
        main_layout.addLayout(status_layout)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        self.setCentralWidget(central_widget)

        # create three pages
        self.tab_info = InfoTab()
        self.tab_upgrade = UpdateTab()
        self.tab_test = TestTab()
        self.tab_settings = SettingsTab()

        self.tabs.addTab(self.tab_info, "Info")
        self.tabs.addTab(self.tab_upgrade, "Update")
        self.tabs.addTab(self.tab_settings, "Settings")
        self.tabs.addTab(self.tab_test, "test")
        self.tabs.currentChanged.connect(self.on_tab_changed)

        self._device_online = False

        self.device_monitor = DeviceMonitorThread()
        self.device_monitor.status_changed.connect(self.update_device_status)
        self.device_monitor.start()

    def update_device_status(self, status):
        device_online = status == "Online"
        became_online = device_online and not self._device_online
        self._device_online = device_online

        self.device_status_label.setText(status)
        color = {
            "Online": "green",
            "Upgrade": "orange",
            "Offline": "red",
        }.get(status, "red")
        self.device_status_label.setStyleSheet(
            f"color: {color}; font-weight: bold;"
        )
        self.tab_test.set_device_online(device_online)
        self.tab_settings.set_device_online(device_online)
        if became_online and self.tabs.currentWidget() is self.tab_settings:
            self.tab_settings.refresh_hardware_version()

    def on_tab_changed(self, _index):
        if (
            self._device_online
            and self.tabs.currentWidget() is self.tab_settings
        ):
            self.tab_settings.refresh_hardware_version()

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
        if self.device_monitor.isRunning():
            self.device_monitor.stop()

        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
