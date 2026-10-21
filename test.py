from PySide6.QtWidgets import (
    QWidget, QVBoxLayout,
    QPushButton, QTextEdit,

)
from PySide6.QtCore import QProcess


class TestTab(QWidget):
    def __init__(self):
        super().__init__()

        self.test_buffer = ""
        self.init_ui()

    # ===============================
    # UI
    # ===============================
    def init_ui(self):
        main_layout = QVBoxLayout()

        # ===== buttons layout =====
        button_layout = QVBoxLayout()
        button_layout.setSpacing(15)

        self.btn_dual_mode = QPushButton("Dual Mode Test")
        self.btn_sdcard = QPushButton("SDCard Test")
        self.btn_reset = QPushButton("Reset")

        buttons = [
            self.btn_dual_mode,
            self.btn_sdcard,
            self.btn_reset
        ]

        for btn in buttons:
            btn.setMinimumHeight(45)
            btn.setStyleSheet("""
                QPushButton {
                    font-size: 15px;
                    font-weight: bold;
                }
            """)
            button_layout.addWidget(btn)
            btn.setEnabled(False)

        self.test_text_edit = QTextEdit()
        self.test_text_edit.setReadOnly(True)
        self.test_text_edit.setStyleSheet("""
            QTextEdit {
                font-size: 14px;
                font-family: Consolas;
            }
        """)

        # ===== layout =====
        main_layout.addLayout(button_layout)
        main_layout.addSpacing(10)
        main_layout.addWidget(self.test_text_edit)
        self.setLayout(main_layout)

        self.btn_dual_mode.clicked.connect(self.run_dual_mode)
        self.btn_sdcard.clicked.connect(self.run_sdcard_test)
        self.btn_reset.clicked.connect(self.run_reset)

    def set_device_online(self, online):
        for btn in [self.btn_dual_mode, self.btn_sdcard, self.btn_reset]:
            btn.setEnabled(online)

    def run_dual_mode(self):
        self.append_log("Setting Dual Mode ...", True)
        self.dual_process = QProcess(self)
        self.dual_process.readyReadStandardOutput.connect(
            self.handle_dual_stdout
        )
        self.dual_process.readyReadStandardError.connect(
            self.handle_dual_stderr
        )
        self.dual_process.finished.connect(
            self.on_dual_finished
        )

        sed_command = (
            'sed -i \'s/"CAM_DIS_MODE"[[:space:]]*:[[:space:]]*"[0-9]*"/'
            '"CAM_DIS_MODE" : "3"/\' '
            '/data/camera/cam_param.bin'
        )

        self.dual_process.start(
            "adb",
            ["shell", sed_command]
        )

    def handle_dual_stdout(self):
        data = self.dual_process.readAllStandardOutput()
        text = bytes(data).decode("utf-8", errors="ignore")
        if text.strip():
            self.append_log(text.strip(), False)

    def handle_dual_stderr(self):
        data = self.dual_process.readAllStandardError()
        text = bytes(data).decode("utf-8", errors="ignore")
        if text.strip():
            self.append_log(text.strip(), False)
    
    def on_dual_finished(self, exitCode, exitStatus):
        if exitCode == 0:
            self.append_log("Dual Mode set SUCCESS.", True)
            self.restart_camera_service()
        else:
            self.append_log("Dual Mode set FAILED.", True)
        self.append_log("Please using uvc player for preview", True)

    def run_sdcard_test(self):
        self.append_log("Checking SDCard mount status...", True)

        self.sdcard_process = QProcess(self)
        self.sdcard_process.finished.connect(self.on_sdcard_check_finished)

        self.sdcard_process.start(
            "adb",
            ["shell", "mount | grep /mnt/sdcard"]
        )

    def on_sdcard_check_finished(self, exitCode, exitStatus):
        output = bytes(
            self.sdcard_process.readAllStandardOutput()
        ).decode("utf-8", errors="ignore").strip()

        if exitCode == 0 and output:
            self.append_log("SDCard INSERTED ✓", True)

            # continue do read/write test
            self.run_sdcard_function_test()
        else:
            self.append_log("SDCard NOT detected ✗", True)

    def run_sdcard_function_test(self):
        self.append_log("Running SDCard write/read test...", True)

        self.sdcard_func_process = QProcess(self)
        self.sdcard_func_process.finished.connect(
            self.on_sdcard_func_finished
        )

        test_cmd = (
            'echo TEST_OK > /mnt/sdcard/test.tmp && '
            'grep TEST_OK /mnt/sdcard/test.tmp && '
            'rm /mnt/sdcard/test.tmp'
        )
        self.sdcard_func_process.start("adb", ["shell", test_cmd])

    def on_sdcard_func_finished(self, exitCode, exitStatus):
        if exitCode == 0:
            self.append_log("SDCard FUNCTION TEST PASS ✓", True)
        else:
            self.append_log("SDCard FUNCTION TEST FAIL ✗", True)

    def run_reset(self):
        self.append_log("Resetting camera parameters...", True)

        # Step 1: delete param file
        self.reset_process = QProcess(self)
        self.reset_process.finished.connect(self.on_reset_delete_finished)
        self.reset_process.start(
            "adb",
            ["shell", "rm -f /data/camera/cam_param.bin"]
        )

    def on_reset_delete_finished(self, exitCode, exitStatus):
        if exitCode == 0:
            self.append_log("Parameter file removed.", False)

            # Step 2: sync
            self.sync_process = QProcess(self)
            self.sync_process.finished.connect(self.on_reset_sync_finished)
            self.sync_process.start(
                "adb",
                ["shell", "sync"]
            )
        else:
            self.append_log("Reset FAILED (ADB error during delete).", True)

    def on_reset_sync_finished(self, exitCode, exitStatus):
        if exitCode == 0:
            self.append_log("File system synced.", False)

            # Step 3: restart the camera service
            self.restart_camera_service()
        else:
            self.append_log("Reset FAILED (ADB error during sync).", True)

    def restart_camera_service(self):
        self.service_process = QProcess(self)

        self.service_process.readyReadStandardOutput.connect(
            self.handle_service_stdout
        )
        self.service_process.readyReadStandardError.connect(
            self.handle_service_stderr
        )
        self.service_process.finished.connect(
            self.on_service_finished
        )
        self.service_process.start(
            "adb",
            ["shell", "systemctl", "restart", "mav_client"],
        )

    def handle_service_stdout(self):
        data = self.service_process.readAllStandardOutput()
        text = bytes(data).decode("utf-8", errors="ignore")
        self.process_service_output(text)

    def handle_service_stderr(self):
        data = self.service_process.readAllStandardError()
        text = bytes(data).decode("utf-8", errors="ignore")
        self.process_service_output(text)

    def process_service_output(self, text):
        if not hasattr(self, "service_buffer"):
            self.service_buffer = ""
        self.service_buffer += text
        self.service_buffer = self.service_buffer.replace("\r", "")

        lines = self.service_buffer.split("\n")
        self.service_buffer = lines[-1]

        for line in lines[:-1]:
            line = line.strip()
            if line:
                self.append_log(line, False)

    def on_service_finished(self, exitCode, exitStatus):
        if exitCode == 0:
            self.append_log("Camera service restarted.", True)
        else:
            self.append_log("Camera service restart FAILED.", True)

    # ===============================
    # log
    # ===============================
    def append_log(self, text, new_line):
        if new_line:
            self.test_text_edit.append(text)
        else:
            self.test_text_edit.append(text)
