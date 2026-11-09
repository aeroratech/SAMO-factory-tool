from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLabel,

)
from PySide6.QtCore import QProcess, Qt


class TestTab(QWidget):
    def __init__(self):
        super().__init__()

        self.test_buffer = ""
        self._device_online = False
        self._next_result_token = 0
        self._active_result_tokens = {
            "dual": None,
            "sdcard": None,
            "reset": None,
        }
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

        self.dual_result_label = self._create_result_label()
        self.sdcard_result_label = self._create_result_label()
        self.reset_result_label = self._create_result_label()

        self._result_labels = {
            "dual": self.dual_result_label,
            "sdcard": self.sdcard_result_label,
            "reset": self.reset_result_label,
        }

        button_result_pairs = [
            (self.btn_dual_mode, self.dual_result_label),
            (self.btn_sdcard, self.sdcard_result_label),
            (self.btn_reset, self.reset_result_label),
        ]

        for btn, result_label in button_result_pairs:
            btn.setMinimumHeight(45)
            btn.setStyleSheet("""
                QPushButton {
                    font-size: 15px;
                    font-weight: bold;
                }
            """)
            btn.setEnabled(False)

            result_layout = QHBoxLayout(btn)
            result_layout.setContentsMargins(12, 0, 12, 0)
            result_layout.addStretch()
            result_layout.addWidget(result_label)
            result_label.setAttribute(Qt.WA_TransparentForMouseEvents)
            button_layout.addWidget(btn)

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

    @staticmethod
    def _create_result_label():
        label = QLabel("")
        label.setFixedWidth(32)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 24px; font-weight: bold;")
        return label

    def set_device_online(self, online):
        self._device_online = online
        for btn in [self.btn_dual_mode, self.btn_sdcard, self.btn_reset]:
            btn.setEnabled(online)
        if not online:
            self._clear_all_test_results()

    def _begin_test(self, test_name):
        self._next_result_token += 1
        token = self._next_result_token
        self._active_result_tokens[test_name] = token
        self._clear_test_result(test_name)
        return token

    def _complete_test(self, test_name, passed, token):
        if not self._device_online:
            return
        if self._active_result_tokens.get(test_name) != token:
            return

        label = self._result_labels[test_name]
        label.setText("✓" if passed else "✗")
        color = "green" if passed else "red"
        label.setStyleSheet(
            f"font-size: 24px; font-weight: bold; color: {color};"
        )
        self._active_result_tokens[test_name] = None

    def _clear_test_result(self, test_name):
        label = self._result_labels[test_name]
        label.setText("")
        label.setStyleSheet("font-size: 24px; font-weight: bold;")

    def _clear_all_test_results(self):
        for test_name in self._result_labels:
            self._active_result_tokens[test_name] = None
            self._clear_test_result(test_name)

    def _connect_process_failure(self, process, test_name, token):
        process.errorOccurred.connect(
            lambda error, result_name=test_name, run_token=token:
            self._on_process_error(error, result_name, run_token)
        )

    def _on_process_error(self, error, test_name, token):
        if error == QProcess.FailedToStart:
            self._complete_test(test_name, False, token)

    def run_dual_mode(self):
        token = self._begin_test("dual")
        self.append_log("Setting Dual Mode ...", True)
        self.dual_process = QProcess(self)
        self._connect_process_failure(self.dual_process, "dual", token)
        self.dual_process.readyReadStandardOutput.connect(
            self.handle_dual_stdout
        )
        self.dual_process.readyReadStandardError.connect(
            self.handle_dual_stderr
        )
        self.dual_process.finished.connect(
            lambda exit_code, exit_status, run_token=token:
            self.on_dual_finished(exit_code, exit_status, run_token)
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
    
    def on_dual_finished(self, exitCode, exitStatus, token=None):
        if exitCode == 0:
            self.append_log("Dual Mode set SUCCESS.", True)
            self.restart_camera_service("dual", token)
        else:
            self.append_log("Dual Mode set FAILED.", True)
            self._complete_test("dual", False, token)
        self.append_log("Please using uvc player for preview", True)

    def run_sdcard_test(self):
        token = self._begin_test("sdcard")
        self.append_log("Checking SDCard mount status...", True)

        self.sdcard_process = QProcess(self)
        process = self.sdcard_process
        self._connect_process_failure(process, "sdcard", token)
        self.sdcard_process.finished.connect(
            lambda exit_code, exit_status, run_token=token,
            source_process=process:
            self.on_sdcard_check_finished(
                exit_code, exit_status, run_token, source_process
            )
        )

        self.sdcard_process.start(
            "adb",
            ["shell", "mount | grep /mnt/sdcard"]
        )

    def on_sdcard_check_finished(
        self, exitCode, exitStatus, token=None, process=None
    ):
        source_process = process or self.sdcard_process
        output = bytes(
            source_process.readAllStandardOutput()
        ).decode("utf-8", errors="ignore").strip()

        if exitCode == 0 and output:
            self.append_log("SDCard INSERTED ✓", True)

            # continue do read/write test
            self.run_sdcard_function_test(token)
        else:
            self.append_log("SDCard NOT detected ✗", True)
            self._complete_test("sdcard", False, token)

    def run_sdcard_function_test(self, token=None):
        self.append_log("Running SDCard write/read test...", True)

        self.sdcard_func_process = QProcess(self)
        self._connect_process_failure(
            self.sdcard_func_process, "sdcard", token
        )
        self.sdcard_func_process.finished.connect(
            lambda exit_code, exit_status, run_token=token:
            self.on_sdcard_func_finished(
                exit_code, exit_status, run_token
            )
        )

        test_cmd = (
            'echo TEST_OK > /mnt/sdcard/test.tmp && '
            'grep TEST_OK /mnt/sdcard/test.tmp && '
            'rm /mnt/sdcard/test.tmp'
        )
        self.sdcard_func_process.start("adb", ["shell", test_cmd])

    def on_sdcard_func_finished(self, exitCode, exitStatus, token=None):
        if exitCode == 0:
            self.append_log("SDCard FUNCTION TEST PASS ✓", True)
        else:
            self.append_log("SDCard FUNCTION TEST FAIL ✗", True)
        self._complete_test("sdcard", exitCode == 0, token)

    def run_reset(self):
        token = self._begin_test("reset")
        self.append_log("Resetting camera parameters...", True)

        # Step 1: delete param file
        self.reset_process = QProcess(self)
        self._connect_process_failure(self.reset_process, "reset", token)
        self.reset_process.finished.connect(
            lambda exit_code, exit_status, run_token=token:
            self.on_reset_delete_finished(
                exit_code, exit_status, run_token
            )
        )
        self.reset_process.start(
            "adb",
            ["shell", "rm -f /data/camera/cam_param.bin"]
        )

    def on_reset_delete_finished(self, exitCode, exitStatus, token=None):
        if exitCode == 0:
            self.append_log("Parameter file removed.", False)

            # Step 2: sync
            self.sync_process = QProcess(self)
            self._connect_process_failure(
                self.sync_process, "reset", token
            )
            self.sync_process.finished.connect(
                lambda sync_exit_code, sync_exit_status, run_token=token:
                self.on_reset_sync_finished(
                    sync_exit_code, sync_exit_status, run_token
                )
            )
            self.sync_process.start(
                "adb",
                ["shell", "sync"]
            )
        else:
            self.append_log("Reset FAILED (ADB error during delete).", True)
            self._complete_test("reset", False, token)

    def on_reset_sync_finished(self, exitCode, exitStatus, token=None):
        if exitCode == 0:
            self.append_log("File system synced.", False)

            # Step 3: restart the camera service
            self.restart_camera_service("reset", token)
        else:
            self.append_log("Reset FAILED (ADB error during sync).", True)
            self._complete_test("reset", False, token)

    def restart_camera_service(self, test_name, token):
        self.service_process = QProcess(self)
        self._connect_process_failure(
            self.service_process, test_name, token
        )

        self.service_process.readyReadStandardOutput.connect(
            self.handle_service_stdout
        )
        self.service_process.readyReadStandardError.connect(
            self.handle_service_stderr
        )
        self.service_process.finished.connect(
            lambda exit_code, exit_status, result_name=test_name,
            run_token=token: self.on_service_finished(
                exit_code, exit_status, result_name, run_token
            )
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

    def on_service_finished(self, exitCode, exitStatus, test_name, token):
        if exitCode == 0:
            self.append_log("Camera service restarted.", True)
        else:
            self.append_log("Camera service restart FAILED.", True)
        self._complete_test(test_name, exitCode == 0, token)

    # ===============================
    # log
    # ===============================
    def append_log(self, text, new_line):
        if new_line:
            self.test_text_edit.append(text)
        else:
            self.test_text_edit.append(text)
