import os
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTextEdit,
    QLineEdit,
    QFileDialog,
    QLabel,
    QGroupBox,
    QFormLayout,
)
from PySide6.QtCore import QProcess
from PySide6.QtCore import QTimer
from PySide6.QtGui import QTextCursor


ABL_IMAGE_NAME = "abl.elf"
BOOT_IMAGE_NAME = "qti-ubuntu-robotics-image-qrb5165-rb5-boot.img"
SYSTEM_IMAGE_NAME = "qti-ubuntu-robotics-image-qrb5165-rb5-sysfs.ext4"


class UpdateTab(QWidget):
    def __init__(self):
        super().__init__()

        self.process = None
        self.firmware_ready = False
        self.fastboot_ready = False
        self.update_in_progress = False
        self.entry_step = 0
        self.fastboot_check_attempts = 0
        self.fastboot_check_after_reboot = False
        self.init_ui()

    # ================= UI =================
    def init_ui(self):
        main_layout = QVBoxLayout()

        # ===== Select Folder Area =====
        folder_layout = QHBoxLayout()

        self.update_folder_path_edit = QLineEdit()
        self.update_folder_path_edit.setMinimumHeight(30)
        self.update_folder_path_edit.setReadOnly(True)

        self.btn_select_folder = QPushButton("Select Update Folder")
        self.btn_select_folder.setMinimumHeight(30)
        self.btn_select_folder.clicked.connect(self.select_folder)

        folder_layout.addWidget(self.update_folder_path_edit)
        folder_layout.addWidget(self.btn_select_folder)

        # ===== Firmware Package Status =====
        self.abl_status = QLabel(f"Missing: {ABL_IMAGE_NAME} ✗")
        self.boot_status = QLabel(f"Missing: {BOOT_IMAGE_NAME} ✗")
        self.system_status = QLabel(f"Missing: {SYSTEM_IMAGE_NAME} ✗")
        for status_label in (
            self.abl_status,
            self.boot_status,
            self.system_status,
        ):
            status_label.setStyleSheet("color: red;")

        status_layout = QFormLayout()
        status_layout.addRow("ABL image", self.abl_status)
        status_layout.addRow("Boot image", self.boot_status)
        status_layout.addRow("System image", self.system_status)
        self.package_status_group = QGroupBox("Update Package")
        self.package_status_group.setLayout(status_layout)

        # ===== Update Buttons =====
        button_layout = QVBoxLayout()
        button_layout.setSpacing(20)

        self.btn_entry_update = QPushButton("Entry update mode")
        self.btn_update = QPushButton("Update")
        self.btn_reboot = QPushButton("Reboot")
        self.btn_update.setEnabled(False)
        self.btn_reboot.setEnabled(False)

        buttons = [
            self.btn_entry_update,
            self.btn_update,
            self.btn_reboot,
        ]

        for btn in buttons:
            btn.setMinimumHeight(50)
            btn.setStyleSheet("""
                QPushButton {
                    font-size: 16px;
                    font-weight: bold;
                }
            """)
            button_layout.addWidget(btn)

        # ===== Connect Signals =====
        self.btn_entry_update.clicked.connect(self.enter_update_mode)
        self.btn_update.clicked.connect(self.full_update)
        self.btn_reboot.clicked.connect(self.reboot_device)


        # ===== Output Log =====
        self.update_text_edit = QTextEdit()
        self.update_text_edit.setReadOnly(True)
        self.update_text_edit.setStyleSheet("font-size: 14px;")

        # ===== Layout Combine =====
        main_layout.addLayout(folder_layout)
        main_layout.addSpacing(10)
        main_layout.addWidget(self.package_status_group)
        main_layout.addSpacing(10)
        main_layout.addLayout(button_layout)
        main_layout.addSpacing(10)
        main_layout.addWidget(self.update_text_edit)

        self.setLayout(main_layout)

    def set_update_folder(self, folder):
        self.update_folder_path_edit.setText(folder)
        self._refresh_firmware_status()

    def _refresh_firmware_status(self):
        folder = self.update_folder_path_edit.text().strip()
        status_items = (
            (ABL_IMAGE_NAME, self.abl_status),
            (BOOT_IMAGE_NAME, self.boot_status),
            (SYSTEM_IMAGE_NAME, self.system_status),
        )
        ready = True
        for filename, status_label in status_items:
            file_ready = bool(folder) and os.path.isfile(
                os.path.join(folder, filename)
            )
            if file_ready:
                status_label.setText("Ready ✓")
                status_label.setStyleSheet("color: green;")
            else:
                status_label.setText(f"Missing: {filename} ✗")
                status_label.setStyleSheet("color: red;")
                ready = False

        self.firmware_ready = ready
        self._update_controls()
        return ready

    def _update_controls(self):
        self.btn_update.setEnabled(
            self.firmware_ready
            and self.fastboot_ready
            and not self.update_in_progress
        )

    def _set_update_in_progress(self, active):
        self.update_in_progress = active
        self.btn_select_folder.setEnabled(not active)
        self.btn_entry_update.setEnabled(not active)
        self._update_controls()

    def _finish_update(self):
        self._set_update_in_progress(False)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Update Folder"
        )
        if folder:
            self.set_update_folder(folder)
            self.append_update_log(f"Selected folder: {folder}")
    
    def enter_update_mode(self):
        self.append_update_log("Checking for device in fastboot mode...")
        self.fastboot_ready = False
        self._update_controls()
        self.btn_reboot.setEnabled(False)
        self.entry_step = 0
        self.fastboot_check_attempts = 0
        self.check_fastboot(after_reboot=False)

    def start_adb_entry_flow(self):
        self.append_update_log("Restarting adbd as root before entering bootloader...")
        self.entry_step = 1
        self.start_entry_process(["root"])

    def start_entry_process(self, args):
        self.entry_process = QProcess(self)
        self.entry_process.readyReadStandardOutput.connect(
            self.handle_entry_stdout
        )
        self.entry_process.readyReadStandardError.connect(
            self.handle_entry_stderr
        )
        self.entry_process.finished.connect(
            self.on_enter_update_finished
        )
        self.entry_process.start("adb", args)

    def wait_for_adb_after_root(self):
        self.start_entry_process(["wait-for-device"])

    def start_reboot_to_bootloader(self):
        self.start_entry_process(["reboot", "bootloader"])

    def on_enter_update_finished(self, exitCode=0, exitStatus=None):
        if self.entry_step == 1:
            self.append_update_log("Waiting for device after adb root...")
            self.entry_step = 2
            QTimer.singleShot(1000, self.wait_for_adb_after_root)
            return

        if self.entry_step == 2:
            self.append_update_log("Rebooting device to bootloader...")
            self.entry_step = 3
            self.start_reboot_to_bootloader()
            return

        self.entry_step = 0
        self.append_update_log("Waiting for fastboot device...")

        # wait for device reboot
        self.fastboot_check_attempts = 0
        QTimer.singleShot(3000, lambda: self.check_fastboot(after_reboot=True))

    def update_bootloader(self):
        folder = self.update_folder_path_edit.text()
        if not folder:
            self.append_update_log("Please select update folder first.")
            self._finish_update()
            return
        abl_path = os.path.join(folder, ABL_IMAGE_NAME)
        if not os.path.exists(abl_path):
            self.append_update_log(f"ERROR: File not found -> {abl_path}")
            self._refresh_firmware_status()
            self._finish_update()
            return
        self.append_update_log("Start Bootloader update...")
        self.append_update_log(f"Using file: {abl_path}")
        self.bootloader_step = 0
        self.abl_path = abl_path

        self.bootloader_process = QProcess(self)
        self.bootloader_process.readyReadStandardOutput.connect(
            self.handle_bootloader_stdout
        )
        self.bootloader_process.readyReadStandardError.connect(
            self.handle_bootloader_stderr
        )
        self.bootloader_process.errorOccurred.connect(
            self.on_flash_process_error
        )
        self.bootloader_process.finished.connect(
            self.on_bootloader_step_finished
        )

        # ===== step 1 flash abl_a =====
        self.bootloader_step = 1
        self.bootloader_process.start(
            "fastboot",
            ["flash", "abl_a", self.abl_path]
        )

    def on_bootloader_step_finished(self):
        if not self.update_in_progress:
            return
        if self.bootloader_step == 1:
            self.append_update_log("abl_a flashed. Flashing abl_b...")

            self.bootloader_step = 2
            self.bootloader_process.start(
                "fastboot",
                ["flash", "abl_b", self.abl_path]
            )

        elif self.bootloader_step == 2:
            self.append_update_log("Bootloader update success.\n")
            self.bootloader_step = 0

            # Always continue with kernel update as part of the update flow
            self.update_kernel()

    def update_kernel(self):
        folder = self.update_folder_path_edit.text().strip()

        if not folder:
            self.append_update_log("Please select update folder.", True)
            self._finish_update()
            return

        image_name = BOOT_IMAGE_NAME
        image_path = os.path.join(folder, image_name)

        if not os.path.exists(image_path):
            self.append_update_log(f"Kernel image not found: {image_name}", True)
            self._refresh_firmware_status()
            self._finish_update()
            return

        self.append_update_log("Start upgrading Kernel...", True)
        self.append_update_log(f"Using image: {image_path}", False)

        self.btn_update.setEnabled(False)
        self.btn_reboot.setEnabled(False)

        self.kernel_process = QProcess(self)
        self.kernel_process.readyReadStandardOutput.connect(
            self.handle_kernel_stdout
        )
        self.kernel_process.readyReadStandardError.connect(
            self.handle_kernel_stderr
        )
        self.kernel_process.errorOccurred.connect(
            self.on_flash_process_error
        )
        self.kernel_process.finished.connect(
            self.on_kernel_finished
        )
        # execute command
        self.kernel_process.start(
            "fastboot",
            ["--slot", "all", "flash", "boot", image_path]
        )

    def on_kernel_finished(self, exitCode, exitStatus):
        if exitCode == 0:
            self.append_update_log("Kernel update SUCCESS.", True)
            # Always continue with filesystem update as part of the update flow
            self.update_filesystem()
            return
        else:
            self.append_update_log("Kernel update FAILED.", True)
            # stop update chain on failure

        self._finish_update()
        # Do NOT enable reboot here; only after full update is done

    def update_filesystem(self):
        folder = self.update_folder_path_edit.text().strip()

        if not folder:
            self.append_update_log("Please select update folder.", True)
            self._finish_update()
            return

        image_name = SYSTEM_IMAGE_NAME
        image_path = os.path.join(folder, image_name)

        if not os.path.exists(image_path):
            self.append_update_log(f"File system image not found: {image_name}", True)
            self._refresh_firmware_status()
            self._finish_update()
            return

        self.append_update_log("Start update File System...", True)
        self.btn_update.setEnabled(False)
        self.btn_reboot.setEnabled(False)
        self.filesystem_process = QProcess(self)
        self.filesystem_process.readyReadStandardOutput.connect(
            self.handle_filesystem_stdout
        )
        self.filesystem_process.readyReadStandardError.connect(
            self.handle_filesystem_stderr
        )
        self.filesystem_process.errorOccurred.connect(
            self.on_flash_process_error
        )
        self.filesystem_process.finished.connect(
            self.on_filesystem_finished
        )
        self.filesystem_process.start(
            "fastboot",
            ["--slot", "all", "flash", "system", image_path]
        )

    def on_filesystem_finished(self, exitCode, exitStatus):
        if exitCode == 0:
            self.append_update_log("File system update SUCCESS.", True)
            self.btn_reboot.setEnabled(True)
        else:
            self.append_update_log("File system update FAILED.", True)

        self._finish_update()
        # Reboot is only enabled on success above

    def full_update(self):
        """
        Run bootloader, kernel and filesystem updates in sequence.
        Assumes device is already in fastboot mode and update folder is selected.
        """
        if self.update_in_progress:
            return
        if not self._refresh_firmware_status():
            self.append_update_log(
                "ERROR: Missing required firmware files.", True
            )
            return
        if not self.fastboot_ready:
            self.append_update_log("ERROR: No Fastboot device detected.", True)
            return

        self._set_update_in_progress(True)
        self.append_update_log("Starting FULL UPDATE (Bootloader + Kernel + File System)...", True)
        self.btn_reboot.setEnabled(False)
        self.btn_update.setEnabled(False)
        self.update_bootloader()

    def on_flash_process_error(self, process_error):
        if process_error != QProcess.FailedToStart:
            return
        self.append_update_log("ERROR: Failed to start update process.", True)
        self._finish_update()

    def reboot_device(self):
        self.append_update_log("Rebooting device...", True)
        self.btn_reboot.setEnabled(False)
        self.reboot_process = QProcess(self)
        self.reboot_process.readyReadStandardOutput.connect(
            self.handle_reboot_stdout
        )
        self.reboot_process.readyReadStandardError.connect(
            self.handle_reboot_stderr
        )
        self.reboot_process.finished.connect(
            self.on_reboot_finished
        )
        self.reboot_process.start("fastboot", ["reboot"])

    def on_reboot_finished(self, exitCode, exitStatus):
        if exitCode == 0:
            self.append_update_log("Device reboot SUCCESS.", True)
        else:
            self.append_update_log("Device reboot FAILED.", True)
        self.fastboot_ready = False
        self._update_controls()
        self.btn_reboot.setEnabled(False)

    def check_fastboot(self, after_reboot=False):
        self.fastboot_check_after_reboot = after_reboot
        self.fastboot_check_attempts += 1
        self.fastboot_process = QProcess(self)
        self.fastboot_process.finished.connect(self.on_fastboot_check_finished)
        self.fastboot_process.start("fastboot", ["devices"])

    def on_fastboot_check_finished(self, exitCode=0, exitStatus=None):
        output = bytes(
            self.fastboot_process.readAllStandardOutput()
        ).decode("utf-8", errors="ignore").strip()
        error = bytes(
            self.fastboot_process.readAllStandardError()
        ).decode("utf-8", errors="ignore").strip()

        devices = self.parse_fastboot_devices(output)
        if devices:
            self.append_update_log("Fastboot device detected:")
            self.append_update_log("\n".join(devices), False)
            self.fastboot_ready = True
            self._update_controls()
            self.btn_reboot.setEnabled(True)
            return

        self.fastboot_ready = False
        self._update_controls()
        self.btn_reboot.setEnabled(False)

        if error:
            self.append_update_log("ERROR: " + error)

        if not self.fastboot_check_after_reboot:
            self.append_update_log("No fastboot device found. Trying ADB reboot to bootloader...")
            self.start_adb_entry_flow()
            return

        max_attempts = 10
        if self.fastboot_check_attempts < max_attempts:
            self.append_update_log("No fastboot device found. Waiting...")
            QTimer.singleShot(1000, lambda: self.check_fastboot(after_reboot=True))
            return

        self.append_update_log("No fastboot device found.")

    def parse_fastboot_devices(self, output):
        return [
            line.strip()
            for line in output.splitlines()
            if line.strip()
        ]

    def handle_entry_stdout(self):
        data = self.entry_process.readAllStandardOutput()
        text = bytes(data).decode("utf-8").strip()
        if text:
            self.append_update_log(text)

    def handle_entry_stderr(self):
        data = self.entry_process.readAllStandardError()
        text = bytes(data).decode("utf-8").strip()
        if text:
            self.append_update_log("ERROR: " + text)

    def handle_bootloader_stdout(self):
        data = self.bootloader_process.readAllStandardOutput()
        text = bytes(data).decode("utf-8", errors="ignore")
        self.process_fastboot_output(text)

    def handle_bootloader_stderr(self):
        data = self.bootloader_process.readAllStandardError()
        text = bytes(data).decode("utf-8", errors="ignore")
        self.process_fastboot_output(text)

    def process_fastboot_output(self, text):
        if not hasattr(self, "fastboot_buffer"):
            self.fastboot_buffer = ""
        self.fastboot_buffer += text
        self.fastboot_buffer = self.fastboot_buffer.replace("\r", "")
        lines = self.fastboot_buffer.split("\n")
        self.fastboot_buffer = lines[-1]
        for line in lines[:-1]:
            line = line.strip()
            if not line:
                continue
            self.append_update_log(line, False)

    def handle_kernel_stdout(self):
        data = self.kernel_process.readAllStandardOutput()
        text = bytes(data).decode("utf-8", errors="ignore")
        self.process_kernel_output(text)

    def handle_kernel_stderr(self):
        data = self.kernel_process.readAllStandardError()
        text = bytes(data).decode("utf-8", errors="ignore")
        self.process_kernel_output(text)

    def process_kernel_output(self, text):
        if not hasattr(self, "kernel_buffer"):
            self.kernel_buffer = ""
        self.kernel_buffer += text
        self.kernel_buffer = self.kernel_buffer.replace("\r", "")
        lines = self.kernel_buffer.split("\n")
        self.kernel_buffer = lines[-1]
        for line in lines[:-1]:
            line = line.strip()
            if not line:
                continue
            self.append_update_log(line, False)

    def handle_filesystem_stdout(self):
        data = self.filesystem_process.readAllStandardOutput()
        text = bytes(data).decode("utf-8", errors="ignore")
        self.process_filesystem_output(text)

    def handle_filesystem_stderr(self):
        data = self.filesystem_process.readAllStandardError()
        text = bytes(data).decode("utf-8", errors="ignore")
        self.process_filesystem_output(text)

    def process_filesystem_output(self, text):
        if not hasattr(self, "filesystem_buffer"):
            self.filesystem_buffer = ""
        self.filesystem_buffer += text
        self.filesystem_buffer = self.filesystem_buffer.replace("\r", "")
        lines = self.filesystem_buffer.split("\n")
        self.filesystem_buffer = lines[-1]
        for line in lines[:-1]:
            line = line.strip()
            if not line:
                continue
            self.append_update_log(line, False)

    def handle_reboot_stdout(self):
        data = self.reboot_process.readAllStandardOutput()
        text = bytes(data).decode("utf-8", errors="ignore")
        self.process_reboot_output(text)

    def process_reboot_output(self, text):
        if not hasattr(self, "reboot_buffer"):
            self.reboot_buffer = ""
        self.reboot_buffer += text
        self.reboot_buffer = self.reboot_buffer.replace("\r", "")
        lines = self.reboot_buffer.split("\n")
        self.reboot_buffer = lines[-1]
        for line in lines[:-1]:
            line = line.strip()
            if not line:
                continue
            self.append_update_log(line, False)

    def handle_reboot_stderr(self):
        data = self.reboot_process.readAllStandardError()
        text = bytes(data).decode("utf-8", errors="ignore")
        self.process_reboot_output(text)

    def append_update_log(self, text, show_time=True):
        if show_time:
            timestamp = datetime.now().strftime("%H:%M:%S")
            final_text = f"[{timestamp}] {text}"
        else:
            final_text = text

        self.update_text_edit.append(final_text)

        # auto scroll to the bottom
        cursor = self.update_text_edit.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.update_text_edit.setTextCursor(cursor)
