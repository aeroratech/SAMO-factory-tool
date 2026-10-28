import os
import shlex
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from settings import (
    PROPERTY_NAME,
    SettingsTab,
    hardware_version_from_property,
)


class FakeSignal:
    def __init__(self):
        self.callback = None

    def connect(self, callback):
        self.callback = callback

    def emit(self, *args):
        if self.callback:
            self.callback(*args)


class ControlledProcess:
    FailedToStart = 0
    NotRunning = 0
    Running = 2
    instances = []

    def __init__(self, parent=None):
        self.parent = parent
        self.errorOccurred = FakeSignal()
        self.finished = FakeSignal()
        self.started_with = None
        self.stdout = b""
        self._state = self.NotRunning
        self.deleted = False
        self.instances.append(self)

    def start(self, program, arguments):
        self.started_with = (program, arguments)
        self._state = self.Running

    def state(self):
        return self._state

    def readAllStandardOutput(self):
        return self.stdout

    def deleteLater(self):
        self.deleted = True

    def finish(self, exit_code):
        self._state = self.NotRunning
        self.finished.emit(exit_code, None)

    def fail_to_start(self):
        self._state = self.NotRunning
        self.errorOccurred.emit(self.FailedToStart)


class HardwareVersionMappingTests(unittest.TestCase):
    def test_trimmed_v2_property_maps_to_v2(self):
        self.assertEqual("v2", hardware_version_from_property("v2\n"))

    def test_uppercase_v2_property_maps_to_v2(self):
        self.assertEqual("v2", hardware_version_from_property("V2"))

    def test_empty_property_maps_to_v1(self):
        self.assertEqual("v1", hardware_version_from_property(""))

    def test_whitespace_property_maps_to_v1(self):
        self.assertEqual("v1", hardware_version_from_property("  \n"))

    def test_v1_property_maps_to_v1(self):
        self.assertEqual("v1", hardware_version_from_property("v1"))

    def test_uppercase_v1_property_maps_to_v1(self):
        self.assertEqual("v1", hardware_version_from_property("V1"))

    def test_unexpected_property_maps_to_v1(self):
        self.assertEqual("v1", hardware_version_from_property("prototype"))


class SettingsTabReadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        ControlledProcess.instances.clear()
        self.process_patch = patch("settings.QProcess", ControlledProcess)
        self.process_patch.start()
        self.tab = SettingsTab()

    def tearDown(self):
        self.tab.close()
        self.process_patch.stop()

    def test_new_tab_has_disabled_mutually_exclusive_controls(self):
        self.assertEqual("V1", self.tab.radio_v1.text())
        self.assertEqual("V2", self.tab.radio_v2.text())
        self.assertFalse(self.tab.radio_v1.isEnabled())
        self.assertFalse(self.tab.radio_v2.isEnabled())
        self.assertFalse(self.tab.btn_apply.isEnabled())
        self.assertIsNotNone(self.tab.status_label)
        self.assertTrue(self.tab.radio_v1.isChecked())
        self.assertFalse(self.tab.radio_v2.isChecked())

        self.tab.radio_v2.setChecked(True)
        self.assertFalse(self.tab.radio_v1.isChecked())
        self.assertTrue(self.tab.radio_v2.isChecked())

    def test_online_state_enables_version_controls(self):
        self.tab.set_device_online(True)

        self.assertTrue(self.tab.radio_v1.isEnabled())
        self.assertTrue(self.tab.radio_v2.isEnabled())
        self.assertTrue(self.tab.btn_apply.isEnabled())

    def test_refresh_is_ignored_while_offline(self):
        self.tab.refresh_hardware_version()

        self.assertEqual([], ControlledProcess.instances)

    def test_refresh_starts_getprop_while_online(self):
        process = self.start_refresh()

        self.assertEqual(
            ("adb", ["shell", "getprop", PROPERTY_NAME]),
            process.started_with,
        )

    def test_successful_v1_read_selects_v1(self):
        process = self.start_refresh()
        process.stdout = b"v1\n"

        process.finish(0)

        self.assertTrue(self.tab.radio_v1.isChecked())
        self.assertFalse(self.tab.radio_v2.isChecked())
        self.assertIn("V1", self.tab.status_label.text())

    def test_successful_uppercase_v2_read_selects_v2(self):
        process = self.start_refresh()
        process.stdout = b"V2\n"

        process.finish(0)

        self.assertFalse(self.tab.radio_v1.isChecked())
        self.assertTrue(self.tab.radio_v2.isChecked())
        self.assertIn("V2", self.tab.status_label.text())

    def test_successful_unexpected_read_selects_v1(self):
        process = self.start_refresh()
        process.stdout = b"prototype\n"

        process.finish(0)

        self.assertTrue(self.tab.radio_v1.isChecked())
        self.assertFalse(self.tab.radio_v2.isChecked())
        self.assertIn("V1", self.tab.status_label.text())

    def test_failed_read_preserves_selection_and_reports_failure(self):
        self.tab.radio_v1.setChecked(True)
        process = self.start_refresh()
        process.stdout = b"v2\n"

        process.finish(1)

        self.assertTrue(self.tab.radio_v1.isChecked())
        self.assertIn("failed", self.tab.status_label.text().lower())

    def test_refresh_does_not_overlap_an_active_read(self):
        self.start_refresh()

        self.tab.refresh_hardware_version()

        self.assertEqual(1, len(ControlledProcess.instances))

    def test_read_disables_editing_until_it_finishes(self):
        process = self.start_refresh()

        self.assertFalse(self.tab.radio_v1.isEnabled())
        self.assertFalse(self.tab.radio_v2.isEnabled())
        self.assertFalse(self.tab.btn_apply.isEnabled())

        process.stdout = b"v1\n"
        process.finish(0)

        self.assertTrue(self.tab.radio_v1.isEnabled())
        self.assertTrue(self.tab.radio_v2.isEnabled())
        self.assertTrue(self.tab.btn_apply.isEnabled())

    def test_apply_is_ignored_while_read_is_running(self):
        self.start_refresh()

        self.tab.apply_hardware_version()

        self.assertEqual(1, len(ControlledProcess.instances))

    def test_read_launch_failure_reports_failure_and_allows_retry(self):
        process = self.start_refresh()

        process.fail_to_start()

        self.assertIn("failed", self.tab.status_label.text().lower())
        self.assertTrue(self.tab.btn_apply.isEnabled())

        self.tab.refresh_hardware_version()
        self.assertEqual(2, len(ControlledProcess.instances))

    def start_refresh(self):
        self.tab.set_device_online(True)
        self.tab.refresh_hardware_version()
        return ControlledProcess.instances[-1]


class SettingsTabApplyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        ControlledProcess.instances.clear()
        self.process_patch = patch("settings.QProcess", ControlledProcess)
        self.process_patch.start()
        self.tab = SettingsTab()

    def tearDown(self):
        self.tab.close()
        self.process_patch.stop()

    def test_apply_v1_clears_property(self):
        self.tab.set_device_online(True)
        self.tab.radio_v1.setChecked(True)

        self.tab.btn_apply.click()

        self.assertEqual(1, len(ControlledProcess.instances))
        program, arguments = ControlledProcess.instances[0].started_with
        self.assertEqual("adb", program)
        self.assertEqual(["shell", f"setprop {PROPERTY_NAME} ''"], arguments)
        self.assertEqual(
            ["setprop", PROPERTY_NAME, ""],
            shlex.split(arguments[1]),
        )

    def test_apply_v2_writes_v2_property_value(self):
        self.tab.set_device_online(True)
        self.tab.radio_v2.setChecked(True)

        self.tab.btn_apply.click()

        program, arguments = ControlledProcess.instances[0].started_with
        self.assertEqual("adb", program)
        self.assertEqual(["shell", f"setprop {PROPERTY_NAME} v2"], arguments)
        self.assertEqual(
            ["setprop", PROPERTY_NAME, "v2"],
            shlex.split(arguments[1]),
        )

    def test_apply_is_ignored_while_offline(self):
        self.tab.apply_hardware_version()

        self.assertEqual([], ControlledProcess.instances)

    def test_apply_disables_controls_until_success(self):
        process = self.start_v1_apply()

        self.assertFalse(self.tab.radio_v1.isEnabled())
        self.assertFalse(self.tab.radio_v2.isEnabled())
        self.assertFalse(self.tab.btn_apply.isEnabled())

        process.finish(0)

        self.assertTrue(self.tab.radio_v1.isEnabled())
        self.assertTrue(self.tab.radio_v2.isEnabled())
        self.assertTrue(self.tab.btn_apply.isEnabled())
        self.assertIn("success", self.tab.status_label.text().lower())

    def test_failed_apply_reports_failure_and_allows_retry(self):
        process = self.start_v1_apply()

        process.finish(1)

        self.assertIn("failed", self.tab.status_label.text().lower())
        self.assertTrue(self.tab.btn_apply.isEnabled())

    def test_disconnect_during_apply_keeps_controls_disabled(self):
        process = self.start_v1_apply()
        self.tab.set_device_online(False)

        process.finish(0)

        self.assertFalse(self.tab.radio_v1.isEnabled())
        self.assertFalse(self.tab.radio_v2.isEnabled())
        self.assertFalse(self.tab.btn_apply.isEnabled())

    def test_refresh_is_ignored_while_apply_is_running(self):
        self.start_v1_apply()

        self.tab.refresh_hardware_version()

        self.assertEqual(1, len(ControlledProcess.instances))

    def test_apply_launch_failure_reports_failure_and_allows_retry(self):
        process = self.start_v1_apply()

        process.fail_to_start()

        self.assertIn("failed", self.tab.status_label.text().lower())
        self.assertTrue(self.tab.btn_apply.isEnabled())

        self.tab.apply_hardware_version()
        self.assertEqual(2, len(ControlledProcess.instances))

    def start_v1_apply(self):
        self.tab.set_device_online(True)
        self.tab.radio_v1.setChecked(True)
        self.tab.apply_hardware_version()
        return ControlledProcess.instances[-1]


if __name__ == "__main__":
    unittest.main()
