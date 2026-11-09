import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

import update as update_module
from update import UpdateTab


ABL_IMAGE_NAME = "abl.elf"
BOOT_IMAGE_NAME = "qti-ubuntu-robotics-image-qrb5165-rb5-boot.img"
SYSTEM_IMAGE_NAME = "qti-ubuntu-robotics-image-qrb5165-rb5-sysfs.ext4"
REQUIRED_IMAGES = (ABL_IMAGE_NAME, BOOT_IMAGE_NAME, SYSTEM_IMAGE_NAME)


class FakeSignal:
    def __init__(self):
        self.callback = None

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


class FastbootResult:
    def __init__(self, output=b"SERIAL\tfastboot\n", error=b""):
        self.output = output
        self.error = error

    def readAllStandardOutput(self):
        return self.output

    def readAllStandardError(self):
        return self.error


class UpdateTabFirmwareStatusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.tab = UpdateTab()

    def tearDown(self):
        self.tab.close()
        self.temp_dir.cleanup()

    def assert_status_interface_exists(self):
        for constant_name in (
            "ABL_IMAGE_NAME",
            "BOOT_IMAGE_NAME",
            "SYSTEM_IMAGE_NAME",
        ):
            self.assertTrue(hasattr(update_module, constant_name))
        for attribute_name in (
            "package_status_group",
            "abl_status",
            "boot_status",
            "system_status",
            "firmware_ready",
            "set_update_folder",
        ):
            self.assertTrue(hasattr(self.tab, attribute_name))

    def create_package(self, missing=None):
        for filename in REQUIRED_IMAGES:
            if filename != missing:
                (self.root / filename).touch()

    def test_initial_fixed_status_area_shows_all_images_missing(self):
        self.assert_status_interface_exists()

        self.assertEqual("Update Package", self.tab.package_status_group.title())
        self.assertEqual(
            f"Missing: {ABL_IMAGE_NAME} ✗", self.tab.abl_status.text()
        )
        self.assertEqual(
            f"Missing: {BOOT_IMAGE_NAME} ✗", self.tab.boot_status.text()
        )
        self.assertEqual(
            f"Missing: {SYSTEM_IMAGE_NAME} ✗", self.tab.system_status.text()
        )
        self.assertFalse(self.tab.firmware_ready)

    def test_complete_folder_marks_every_image_ready(self):
        self.assert_status_interface_exists()
        self.create_package()

        self.tab.set_update_folder(str(self.root))

        self.assertEqual("Ready ✓", self.tab.abl_status.text())
        self.assertEqual("Ready ✓", self.tab.boot_status.text())
        self.assertEqual("Ready ✓", self.tab.system_status.text())
        self.assertTrue(self.tab.firmware_ready)
        self.assertFalse(self.tab.btn_update.isEnabled())

    def test_each_image_is_required(self):
        self.assert_status_interface_exists()

        for missing in REQUIRED_IMAGES:
            with self.subTest(missing=missing):
                for child in self.root.iterdir():
                    child.unlink()
                self.create_package(missing=missing)

                self.tab.set_update_folder(str(self.root))

                self.assertFalse(self.tab.firmware_ready)
                status_by_filename = {
                    ABL_IMAGE_NAME: self.tab.abl_status.text(),
                    BOOT_IMAGE_NAME: self.tab.boot_status.text(),
                    SYSTEM_IMAGE_NAME: self.tab.system_status.text(),
                }
                self.assertEqual(
                    f"Missing: {missing} ✗", status_by_filename[missing]
                )

    def test_directory_with_required_filename_is_not_ready(self):
        self.assert_status_interface_exists()
        self.create_package(missing=ABL_IMAGE_NAME)
        (self.root / ABL_IMAGE_NAME).mkdir()

        self.tab.set_update_folder(str(self.root))

        self.assertEqual(
            f"Missing: {ABL_IMAGE_NAME} ✗", self.tab.abl_status.text()
        )
        self.assertFalse(self.tab.firmware_ready)

    def test_selecting_incomplete_folder_clears_previous_readiness(self):
        self.assert_status_interface_exists()
        self.create_package()
        incomplete = self.root / "incomplete"
        incomplete.mkdir()

        self.tab.set_update_folder(str(self.root))
        self.assertTrue(self.tab.firmware_ready)

        self.tab.set_update_folder(str(incomplete))

        self.assertFalse(self.tab.firmware_ready)
        self.assertFalse(self.tab.btn_update.isEnabled())


class UpdateTabReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        RecordingProcess.instances.clear()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.tab = UpdateTab()

    def tearDown(self):
        self.tab.close()
        self.temp_dir.cleanup()

    def assert_readiness_interface_exists(self):
        self.assertTrue(hasattr(self.tab, "fastboot_ready"))
        self.assertTrue(hasattr(self.tab, "_update_controls"))

    def create_package(self):
        for filename in REQUIRED_IMAGES:
            (self.root / filename).touch()

    def detect_fastboot(self):
        self.tab.fastboot_process = FastbootResult()
        self.tab.on_fastboot_check_finished()

    def test_complete_package_without_fastboot_keeps_update_disabled(self):
        self.assert_readiness_interface_exists()
        self.create_package()

        self.tab.set_update_folder(str(self.root))

        self.assertTrue(self.tab.firmware_ready)
        self.assertFalse(self.tab.fastboot_ready)
        self.assertFalse(self.tab.btn_update.isEnabled())

    def test_fastboot_without_complete_package_keeps_update_disabled(self):
        self.assert_readiness_interface_exists()

        self.detect_fastboot()

        self.assertTrue(self.tab.fastboot_ready)
        self.assertFalse(self.tab.firmware_ready)
        self.assertFalse(self.tab.btn_update.isEnabled())

    def test_fastboot_and_complete_package_enable_update(self):
        self.assert_readiness_interface_exists()
        self.create_package()
        self.tab.set_update_folder(str(self.root))

        self.detect_fastboot()

        self.assertTrue(self.tab.fastboot_ready)
        self.assertTrue(self.tab.firmware_ready)
        self.assertTrue(self.tab.btn_update.isEnabled())

    def test_enter_mode_clears_only_fastboot_readiness(self):
        self.assert_readiness_interface_exists()
        self.create_package()
        self.tab.set_update_folder(str(self.root))
        self.detect_fastboot()

        with patch.object(self.tab, "check_fastboot"):
            self.tab.enter_update_mode()

        self.assertTrue(self.tab.firmware_ready)
        self.assertFalse(self.tab.fastboot_ready)
        self.assertFalse(self.tab.btn_update.isEnabled())

    def test_failed_fastboot_check_clears_fastboot_readiness(self):
        self.assert_readiness_interface_exists()
        self.tab.fastboot_ready = True
        self.tab.fastboot_check_after_reboot = True
        self.tab.fastboot_check_attempts = 10
        self.tab.fastboot_process = FastbootResult(output=b"")

        self.tab.on_fastboot_check_finished()

        self.assertFalse(self.tab.fastboot_ready)
        self.assertFalse(self.tab.btn_update.isEnabled())

    def test_full_update_revalidates_removed_image_before_starting_process(self):
        self.assert_readiness_interface_exists()
        self.create_package()
        self.tab.set_update_folder(str(self.root))
        self.detect_fastboot()
        (self.root / SYSTEM_IMAGE_NAME).unlink()

        with patch("update.QProcess", RecordingProcess):
            self.tab.full_update()

        self.assertEqual([], RecordingProcess.instances)
        self.assertEqual(
            f"Missing: {SYSTEM_IMAGE_NAME} ✗", self.tab.system_status.text()
        )
        self.assertFalse(self.tab.firmware_ready)
        self.assertFalse(self.tab.btn_update.isEnabled())
        self.assertIn(
            "ERROR: Missing required firmware files.",
            self.tab.update_text_edit.toPlainText(),
        )

    def test_kernel_failure_respects_combined_readiness(self):
        self.assert_readiness_interface_exists()
        self.tab.firmware_ready = True
        self.tab.fastboot_ready = False
        self.tab.btn_update.setEnabled(False)

        self.tab.on_kernel_finished(1, None)

        self.assertFalse(self.tab.btn_update.isEnabled())

    def test_filesystem_completion_respects_combined_readiness(self):
        self.assert_readiness_interface_exists()
        self.tab.firmware_ready = False
        self.tab.fastboot_ready = True
        self.tab.btn_update.setEnabled(False)

        self.tab.on_filesystem_finished(0, None)

        self.assertFalse(self.tab.btn_update.isEnabled())

    def test_reboot_completion_clears_fastboot_readiness(self):
        self.assert_readiness_interface_exists()
        self.tab.fastboot_ready = True

        self.tab.on_reboot_finished(0, None)

        self.assertFalse(self.tab.fastboot_ready)
        self.assertFalse(self.tab.btn_update.isEnabled())

if __name__ == "__main__":
    unittest.main()
