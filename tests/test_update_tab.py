import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

import update as update_module
from update import UpdateTab


ABL_IMAGE_NAME = "abl.elf"
BOOT_IMAGE_NAME = "qti-ubuntu-robotics-image-qrb5165-rb5-boot.img"
SYSTEM_IMAGE_NAME = "qti-ubuntu-robotics-image-qrb5165-rb5-sysfs.ext4"
REQUIRED_IMAGES = (ABL_IMAGE_NAME, BOOT_IMAGE_NAME, SYSTEM_IMAGE_NAME)


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


if __name__ == "__main__":
    unittest.main()
