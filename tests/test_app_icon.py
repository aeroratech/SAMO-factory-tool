import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QWidget

from main import MainWindow


class ApplicationIconTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_main_window_has_an_application_icon_at_desktop_size(self):
        with patch("main.TestTab", QWidget):
            window = MainWindow()
        icon = window.windowIcon()

        self.assertFalse(icon.isNull())
        self.assertFalse(icon.pixmap(256, 256).isNull())
        window.close()


if __name__ == "__main__":
    unittest.main()
