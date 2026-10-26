from PySide6.QtCore import QProcess
from PySide6.QtWidgets import (
    QButtonGroup,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)


PROPERTY_NAME = "persist.usb.hardware.version"


def hardware_version_from_property(raw_value: str) -> str:
    return "v1" if raw_value.strip() == "v1" else "v2"


class SettingsTab(QWidget):
    def __init__(self):
        super().__init__()

        self._device_online = False
        self._read_in_progress = False
        self._apply_in_progress = False
        self.read_process = None
        self.write_process = None

        self.radio_v1 = QRadioButton("V1")
        self.radio_v2 = QRadioButton("V2")
        self.radio_v2.setChecked(True)

        self.version_group = QButtonGroup(self)
        self.version_group.addButton(self.radio_v1)
        self.version_group.addButton(self.radio_v2)

        version_layout = QHBoxLayout()
        version_layout.addWidget(self.radio_v1)
        version_layout.addWidget(self.radio_v2)
        version_layout.addStretch()

        version_box = QGroupBox("Hardware Version")
        version_box.setLayout(version_layout)

        self.btn_apply = QPushButton("Apply")
        self.btn_apply.clicked.connect(self.apply_hardware_version)
        self.status_label = QLabel("Device offline.")

        layout = QVBoxLayout(self)
        layout.addWidget(version_box)
        layout.addWidget(self.btn_apply)
        layout.addWidget(self.status_label)
        layout.addStretch()

        self._update_controls()

    def set_device_online(self, online: bool):
        self._device_online = online
        self._update_controls()
        if not online:
            self.status_label.setText("Device offline.")

    def _update_controls(self):
        enabled = (
            self._device_online
            and not self._read_in_progress
            and not self._apply_in_progress
        )
        self.radio_v1.setEnabled(enabled)
        self.radio_v2.setEnabled(enabled)
        self.btn_apply.setEnabled(enabled)

    def refresh_hardware_version(self):
        if (
            not self._device_online
            or self._read_in_progress
            or self._apply_in_progress
        ):
            return

        process = QProcess(self)
        self.read_process = process
        self._read_in_progress = True
        self._update_controls()
        process.finished.connect(
            lambda exit_code, _exit_status, active_process=process:
            self._on_read_finished(active_process, exit_code)
        )
        process.errorOccurred.connect(
            lambda error, active_process=process:
            self._on_read_error(active_process, error)
        )
        self.status_label.setText("Reading hardware version...")
        process.start("adb", ["shell", "getprop", PROPERTY_NAME])

    def _on_read_finished(self, process, exit_code):
        if process is not self.read_process:
            return

        if exit_code == 0:
            raw_value = bytes(process.readAllStandardOutput()).decode(
                "utf-8", errors="ignore"
            )
            version = hardware_version_from_property(raw_value)
            self.radio_v1.setChecked(version == "v1")
            self.radio_v2.setChecked(version == "v2")
            self.status_label.setText(
                f"Current hardware version: {version.upper()}"
            )
        else:
            self.status_label.setText("Failed to read hardware version.")

        self._complete_read(process)

    def _on_read_error(self, process, error):
        if error != QProcess.FailedToStart or process is not self.read_process:
            return

        if self._device_online:
            self.status_label.setText("Failed to read hardware version.")
        else:
            self.status_label.setText("Device offline.")
        self._complete_read(process)

    def _complete_read(self, process):
        self.read_process = None
        self._read_in_progress = False
        self._update_controls()
        process.deleteLater()

    def apply_hardware_version(self):
        if (
            not self._device_online
            or self._read_in_progress
            or self._apply_in_progress
        ):
            return

        shell_value = "v1" if self.radio_v1.isChecked() else "''"
        version = "V1" if shell_value == "v1" else "V2"

        process = QProcess(self)
        self.write_process = process
        self._apply_in_progress = True
        self._update_controls()
        self.status_label.setText(f"Applying hardware version {version}...")
        process.finished.connect(
            lambda exit_code, _exit_status, active_process=process,
            pending_version=version: self._on_write_finished(
                active_process, exit_code, pending_version
            )
        )
        process.errorOccurred.connect(
            lambda error, active_process=process,
            pending_version=version: self._on_write_error(
                active_process, error, pending_version
            )
        )
        process.start(
            "adb",
            ["shell", f"setprop {PROPERTY_NAME} {shell_value}"],
        )

    def _on_write_finished(self, process, exit_code, version):
        if process is not self.write_process:
            return

        if self._device_online:
            if exit_code == 0:
                self.status_label.setText(
                    f"Hardware version {version} applied successfully."
                )
            else:
                self.status_label.setText(
                    f"Failed to apply hardware version {version}."
                )
        else:
            self.status_label.setText("Device offline.")

        self._complete_write(process)

    def _on_write_error(self, process, error, version):
        if error != QProcess.FailedToStart or process is not self.write_process:
            return

        if self._device_online:
            self.status_label.setText(
                f"Failed to apply hardware version {version}."
            )
        else:
            self.status_label.setText("Device offline.")
        self._complete_write(process)

    def _complete_write(self, process):
        self.write_process = None
        self._apply_in_progress = False
        self._update_controls()
        process.deleteLater()
