import os
import time
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel
from device_monitor import DeviceMonitorThread
from main import MainWindow


class DeviceStatusUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def create_window_without_monitor(self):
        with patch("main.DeviceMonitorThread.start"):
            return MainWindow()

    def test_device_status_is_outside_the_tab_pages(self):
        window = self.create_window_without_monitor()

        status_titles = [
            label
            for label in window.findChildren(QLabel)
            if label.text().strip() == "Device status:"
        ]

        self.assertEqual(1, len(status_titles))
        self.assertFalse(window.tabs.isAncestorOf(status_titles[0]))
        window.close()

    def test_online_status_enables_factory_test_actions(self):
        window = self.create_window_without_monitor()
        update_status = getattr(window, "update_device_status", None)

        self.assertIsNotNone(update_status)
        update_status("Online")
        self.assertEqual("Online", window.device_status_label.text())
        self.assertIn("green", window.device_status_label.styleSheet())
        self.assertTrue(window.tab_test.btn_dual_mode.isEnabled())
        self.assertTrue(window.tab_test.btn_sdcard.isEnabled())
        self.assertTrue(window.tab_test.btn_reset.isEnabled())
        window.close()

    def test_online_status_does_not_add_a_test_log_entry(self):
        window = self.create_window_without_monitor()

        window.update_device_status("Online")

        self.assertEqual("", window.tab_test.test_text_edit.toPlainText())
        window.close()

    def test_upgrade_status_disables_factory_test_actions(self):
        window = self.create_window_without_monitor()

        window.update_device_status("Upgrade")

        self.assertEqual("Upgrade", window.device_status_label.text())
        self.assertIn("orange", window.device_status_label.styleSheet())
        self.assertFalse(window.tab_test.btn_dual_mode.isEnabled())
        self.assertFalse(window.tab_test.btn_sdcard.isEnabled())
        self.assertFalse(window.tab_test.btn_reset.isEnabled())
        window.close()

    def test_offline_status_disables_factory_test_actions(self):
        window = self.create_window_without_monitor()
        window.update_device_status("Online")

        window.update_device_status("Offline")

        self.assertEqual("Offline", window.device_status_label.text())
        self.assertIn("red", window.device_status_label.styleSheet())
        self.assertFalse(window.tab_test.btn_dual_mode.isEnabled())
        self.assertFalse(window.tab_test.btn_sdcard.isEnabled())
        self.assertFalse(window.tab_test.btn_reset.isEnabled())
        window.close()

    def test_main_window_has_settings_tab(self):
        window = self.create_window_without_monitor()

        settings_index = window.tabs.indexOf(window.tab_settings)

        self.assertGreaterEqual(settings_index, 0)
        self.assertEqual("Settings", window.tabs.tabText(settings_index))
        window.close()

    def test_device_status_controls_settings_actions(self):
        window = self.create_window_without_monitor()

        window.update_device_status("Online")
        self.assertTrue(window.tab_settings.radio_v1.isEnabled())
        self.assertTrue(window.tab_settings.radio_v2.isEnabled())
        self.assertTrue(window.tab_settings.btn_apply.isEnabled())

        for status in ("Offline", "Upgrade"):
            window.update_device_status(status)
            self.assertFalse(window.tab_settings.radio_v1.isEnabled())
            self.assertFalse(window.tab_settings.radio_v2.isEnabled())
            self.assertFalse(window.tab_settings.btn_apply.isEnabled())
        window.close()

    def test_entering_settings_online_refreshes_hardware_version_once(self):
        window = self.create_window_without_monitor()
        window.update_device_status("Online")

        with patch.object(
            window.tab_settings, "refresh_hardware_version"
        ) as refresh:
            window.tabs.setCurrentWidget(window.tab_settings)

        refresh.assert_called_once_with()
        window.close()

    def test_entering_settings_offline_does_not_refresh(self):
        window = self.create_window_without_monitor()

        with patch.object(
            window.tab_settings, "refresh_hardware_version"
        ) as refresh:
            window.tabs.setCurrentWidget(window.tab_settings)

        refresh.assert_not_called()
        window.close()

    def test_becoming_online_while_settings_selected_refreshes_once(self):
        window = self.create_window_without_monitor()
        window.tabs.setCurrentWidget(window.tab_settings)

        with patch.object(
            window.tab_settings, "refresh_hardware_version"
        ) as refresh:
            window.update_device_status("Online")

        refresh.assert_called_once_with()
        window.close()

    def test_main_window_monitors_status_and_stops_monitor_on_close(self):
        monitor = DeviceMonitorThread(
            interval=1,
            run_command=lambda program, _arguments: (
                "device\n" if program == "adb" else ""
            ),
        )
        try:
            with patch("main.DeviceMonitorThread", return_value=monitor, create=True):
                window = MainWindow()
                deadline = time.monotonic() + 1
                while (
                    window.device_status_label.text() != "Online"
                    and time.monotonic() < deadline
                ):
                    QApplication.processEvents()
                    time.sleep(0.01)

                self.assertEqual("Online", window.device_status_label.text())
                self.assertTrue(monitor.isRunning())
                window.close()
                self.assertFalse(monitor.isRunning())
        finally:
            monitor.stop()


if __name__ == "__main__":
    unittest.main()
