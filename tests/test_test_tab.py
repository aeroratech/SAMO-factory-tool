import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from test import TestTab


class FakeSignal:
    def __init__(self):
        self.callback = None

    def connect(self, callback):
        self.callback = callback

    def emit(self, *args):
        if self.callback:
            self.callback(*args)


class RecordingProcess:
    instances = []

    def __init__(self, parent=None):
        self.parent = parent
        self.readyReadStandardOutput = FakeSignal()
        self.readyReadStandardError = FakeSignal()
        self.finished = FakeSignal()
        self.started_with = None
        self.stdout = b""
        self.instances.append(self)

    def start(self, program, arguments):
        self.started_with = (program, arguments)

    def readAllStandardOutput(self):
        return self.stdout


class TestTabResultIndicatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tab = TestTab()

    def tearDown(self):
        self.tab.close()

    def test_result_labels_start_empty_beside_their_buttons(self):
        result_pairs = [
            (self.tab.btn_dual_mode, self.tab.dual_result_label),
            (self.tab.btn_sdcard, self.tab.sdcard_result_label),
            (self.tab.btn_reset, self.tab.reset_result_label),
        ]
        button_layout = self.tab.layout().itemAt(0).layout()

        for index, (button, label) in enumerate(result_pairs):
            row_layout = button_layout.itemAt(index).layout()
            self.assertIs(button, row_layout.itemAt(0).widget())
            self.assertIs(label, row_layout.itemAt(1).widget())
            self.assertEqual("", label.text())
            self.assertNotIn("green", label.styleSheet())
            self.assertNotIn("red", label.styleSheet())

    def test_current_success_renders_green_check(self):
        self.tab.set_device_online(True)
        token = self.tab._begin_test("dual")

        self.tab._complete_test("dual", True, token)

        self.assertEqual("✓", self.tab.dual_result_label.text())
        self.assertIn("green", self.tab.dual_result_label.styleSheet())

    def test_current_failure_renders_red_cross(self):
        self.tab.set_device_online(True)
        token = self.tab._begin_test("sdcard")

        self.tab._complete_test("sdcard", False, token)

        self.assertEqual("✗", self.tab.sdcard_result_label.text())
        self.assertIn("red", self.tab.sdcard_result_label.styleSheet())


class TestTabResultLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        RecordingProcess.instances.clear()
        self.tab = TestTab()
        self.tab.set_device_online(True)

    def tearDown(self):
        self.tab.close()

    def set_all_results_to_pass(self):
        for test_name in ("dual", "sdcard", "reset"):
            token = self.tab._begin_test(test_name)
            self.tab._complete_test(test_name, True, token)

    def test_starting_dual_clears_only_dual_result(self):
        self.set_all_results_to_pass()

        with patch("test.QProcess", RecordingProcess):
            self.tab.run_dual_mode()

        self.assertEqual("", self.tab.dual_result_label.text())
        self.assertEqual("✓", self.tab.sdcard_result_label.text())
        self.assertEqual("✓", self.tab.reset_result_label.text())

    def test_starting_sdcard_clears_only_sdcard_result(self):
        self.set_all_results_to_pass()

        with patch("test.QProcess", RecordingProcess):
            self.tab.run_sdcard_test()

        self.assertEqual("✓", self.tab.dual_result_label.text())
        self.assertEqual("", self.tab.sdcard_result_label.text())
        self.assertEqual("✓", self.tab.reset_result_label.text())

    def test_starting_reset_clears_only_reset_result(self):
        self.set_all_results_to_pass()

        with patch("test.QProcess", RecordingProcess):
            self.tab.run_reset()

        self.assertEqual("✓", self.tab.dual_result_label.text())
        self.assertEqual("✓", self.tab.sdcard_result_label.text())
        self.assertEqual("", self.tab.reset_result_label.text())

    def test_non_online_state_clears_all_results(self):
        self.set_all_results_to_pass()

        self.tab.set_device_online(False)

        self.assertEqual("", self.tab.dual_result_label.text())
        self.assertEqual("", self.tab.sdcard_result_label.text())
        self.assertEqual("", self.tab.reset_result_label.text())

    def test_result_from_before_disconnect_stays_invalid_after_reconnect(self):
        token = self.tab._begin_test("dual")
        self.tab.set_device_online(False)
        self.tab.set_device_online(True)

        self.tab._complete_test("dual", True, token)

        self.assertEqual("", self.tab.dual_result_label.text())

    def test_new_run_invalidates_previous_run_for_same_test(self):
        old_token = self.tab._begin_test("sdcard")
        current_token = self.tab._begin_test("sdcard")

        self.tab._complete_test("sdcard", False, old_token)
        self.assertEqual("", self.tab.sdcard_result_label.text())

        self.tab._complete_test("sdcard", True, current_token)
        self.assertEqual("✓", self.tab.sdcard_result_label.text())


class TestTabDualResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        RecordingProcess.instances.clear()
        self.tab = TestTab()
        self.tab.set_device_online(True)

    def tearDown(self):
        self.tab.close()

    def test_dual_parameter_failure_shows_failure(self):
        token = self.tab._begin_test("dual")

        with patch("test.QProcess", RecordingProcess):
            self.tab.on_dual_finished(1, None, token)

        self.assertEqual("✗", self.tab.dual_result_label.text())
        self.assertEqual([], RecordingProcess.instances)

    def test_dual_parameter_success_stays_blank_while_service_restarts(self):
        token = self.tab._begin_test("dual")

        with patch("test.QProcess", RecordingProcess):
            self.tab.on_dual_finished(0, None, token)

        self.assertEqual("", self.tab.dual_result_label.text())
        self.assertEqual(1, len(RecordingProcess.instances))

    def test_dual_service_success_shows_pass_without_changing_other_results(self):
        sdcard_token = self.tab._begin_test("sdcard")
        self.tab._complete_test("sdcard", False, sdcard_token)
        reset_token = self.tab._begin_test("reset")
        self.tab._complete_test("reset", False, reset_token)
        self.start_dual_service_restart()

        self.tab.service_process.finished.emit(0, None)

        self.assertEqual("✓", self.tab.dual_result_label.text())
        self.assertEqual("✗", self.tab.sdcard_result_label.text())
        self.assertEqual("✗", self.tab.reset_result_label.text())

    def test_dual_service_failure_shows_failure(self):
        self.start_dual_service_restart()

        self.tab.service_process.finished.emit(1, None)

        self.assertEqual("✗", self.tab.dual_result_label.text())

    def start_dual_service_restart(self):
        token = self.tab._begin_test("dual")
        with patch("test.QProcess", RecordingProcess):
            self.tab.on_dual_finished(0, None, token)
        return token


class TestTabSdcardResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        RecordingProcess.instances.clear()
        self.tab = TestTab()
        self.tab.set_device_online(True)

    def tearDown(self):
        self.tab.close()

    def test_mount_failure_shows_failure(self):
        token = self.tab._begin_test("sdcard")
        self.tab.sdcard_process = RecordingProcess(self.tab)

        self.tab.on_sdcard_check_finished(1, None, token)

        self.assertEqual("✗", self.tab.sdcard_result_label.text())

    def test_mount_success_stays_blank_until_function_test_passes(self):
        token = self.start_sdcard_function_test()

        self.assertEqual("", self.tab.sdcard_result_label.text())

        self.tab.on_sdcard_func_finished(0, None, token)
        self.assertEqual("✓", self.tab.sdcard_result_label.text())

    def test_function_test_failure_shows_failure(self):
        token = self.start_sdcard_function_test()

        self.tab.on_sdcard_func_finished(1, None, token)

        self.assertEqual("✗", self.tab.sdcard_result_label.text())

    def start_sdcard_function_test(self):
        token = self.tab._begin_test("sdcard")
        self.tab.sdcard_process = RecordingProcess(self.tab)
        self.tab.sdcard_process.stdout = b"/dev/mmcblk0 on /mnt/sdcard\n"
        with patch("test.QProcess", RecordingProcess):
            self.tab.on_sdcard_check_finished(0, None, token)
        return token


class TestTabResetResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        RecordingProcess.instances.clear()
        self.tab = TestTab()
        self.tab.set_device_online(True)

    def tearDown(self):
        self.tab.close()

    def test_delete_failure_shows_failure(self):
        token = self.tab._begin_test("reset")

        with patch("test.QProcess", RecordingProcess):
            self.tab.on_reset_delete_finished(1, None, token)

        self.assertEqual("✗", self.tab.reset_result_label.text())

    def test_delete_success_stays_blank_while_sync_is_pending(self):
        token = self.tab._begin_test("reset")

        with patch("test.QProcess", RecordingProcess):
            self.tab.on_reset_delete_finished(0, None, token)

        self.assertEqual("", self.tab.reset_result_label.text())
        self.assertEqual(1, len(RecordingProcess.instances))

    def test_sync_failure_shows_failure(self):
        token = self.tab._begin_test("reset")

        with patch("test.QProcess", RecordingProcess):
            self.tab.on_reset_sync_finished(1, None, token)

        self.assertEqual("✗", self.tab.reset_result_label.text())

    def test_sync_success_stays_blank_until_service_passes(self):
        self.start_reset_service_restart()

        self.assertEqual("", self.tab.reset_result_label.text())

        self.tab.service_process.finished.emit(0, None)
        self.assertEqual("✓", self.tab.reset_result_label.text())

    def test_service_failure_shows_reset_failure(self):
        self.start_reset_service_restart()

        self.tab.service_process.finished.emit(1, None)

        self.assertEqual("✗", self.tab.reset_result_label.text())

    def test_reset_service_result_does_not_change_dual_result(self):
        dual_token = self.tab._begin_test("dual")
        self.tab._complete_test("dual", False, dual_token)
        self.start_reset_service_restart()

        self.tab.service_process.finished.emit(0, None)

        self.assertEqual("✗", self.tab.dual_result_label.text())
        self.assertEqual("✓", self.tab.reset_result_label.text())

    def start_reset_service_restart(self):
        token = self.tab._begin_test("reset")
        with patch("test.QProcess", RecordingProcess):
            self.tab.on_reset_sync_finished(0, None, token)
        return token


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
