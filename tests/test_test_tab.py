import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from test import TestTab


class FakeSignal:
    def connect(self, callback):
        self.callback = callback


class RecordingProcess:
    instances = []

    def __init__(self, parent=None):
        self.parent = parent
        self.readyReadStandardOutput = FakeSignal()
        self.readyReadStandardError = FakeSignal()
        self.finished = FakeSignal()
        self.started_with = None
        self.instances.append(self)

    def start(self, program, arguments):
        self.started_with = (program, arguments)


class TestTabCameraServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        RecordingProcess.instances.clear()
        self.tab = TestTab()

    def tearDown(self):
        self.tab.close()

    def assert_camera_service_restart_started(self):
        self.assertEqual(1, len(RecordingProcess.instances))
        self.assertEqual(
            ("adb", ["shell", "systemctl", "restart", "mav_client"]),
            RecordingProcess.instances[0].started_with,
        )

    def test_successful_dual_mode_restarts_only_camera_service(self):
        with patch("test.QProcess", RecordingProcess):
            self.tab.on_dual_finished(0, None)

        self.assert_camera_service_restart_started()

    def test_successful_reset_restarts_only_camera_service(self):
        with patch("test.QProcess", RecordingProcess):
            self.tab.on_reset_sync_finished(0, None)

        self.assert_camera_service_restart_started()

    def test_failed_dual_mode_does_not_restart_camera_service(self):
        with patch("test.QProcess", RecordingProcess):
            self.tab.on_dual_finished(1, None)

        self.assertEqual([], RecordingProcess.instances)


if __name__ == "__main__":
    unittest.main()
