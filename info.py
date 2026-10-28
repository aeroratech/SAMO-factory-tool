from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTextEdit,
    QLabel
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtCore import QProcess
from datetime import datetime


class InfoTab(QWidget):
    def __init__(self):
        super().__init__()

        self.process = None
        self.command_queue = []
        self.current_index = 0

        self.init_ui()

    # ================= UI =================
    def init_ui(self):
        main_layout = QVBoxLayout()

        # ===== Top layout (title + buttons) =====
        top_layout = QHBoxLayout()

        title_label = QLabel("")
        title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        title_label.setStyleSheet("font-size:18px; font-weight:bold;")

        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.btn_version = QPushButton("Info")
        self.btn_clear = QPushButton("Clear")

        self.btn_version.clicked.connect(self.show_version)
        self.btn_clear.clicked.connect(self.clear_info_log)

        button_layout.addWidget(self.btn_version)
        button_layout.addWidget(self.btn_clear)

        top_layout.addWidget(title_label)
        top_layout.addStretch()
        top_layout.addLayout(button_layout)

        # ===== Text Output =====
        self.info_text_edit = QTextEdit()
        self.info_text_edit.setStyleSheet("""
            QTextEdit {
                font-size: 14px;
                font-family: Consolas;
            }
        """)
        self.info_text_edit.setReadOnly(True)

        main_layout.addLayout(top_layout)
        main_layout.addWidget(self.info_text_edit)

        self.setLayout(main_layout)

     # =========================
    # function
    # =========================
    def append_info_text(self, text, show_time=True):
        if show_time:
            timestamp = datetime.now().strftime("%H:%M:%S")
            final_text = f"[{timestamp}] {text}"
        else:
            final_text = text

        self.info_text_edit.append(final_text)

        # auto scroll to the bottom
        cursor = self.info_text_edit.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.info_text_edit.setTextCursor(cursor)

    def clear_info_log(self):
        """clear the text edit"""
        self.info_text_edit.clear()

    def show_version(self):
        self.commands = [
            {
                "title": "Camera Version:",
                "cmd": ["adb", "shell", "cat", "/etc/aerora-version"]
            },
            {
                "title": "Gimbal Version:",
                "cmd": ["adb", "shell", "cat", "/etc/gimbal-version"]
            }
        ]

        self.current_index = 0

        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.run_next_command)
        self.run_next_command()

    def run_next_command(self):
        if self.current_index < len(self.commands):
            item = self.commands[self.current_index]
            self.current_index += 1

            self.append_info_text(item["title"], show_time=True)
            # execute the command
            cmd = item["cmd"]
            self.process.start(cmd[0], cmd[1:])
        else:
            self.append_info_text("Done.")

    def handle_stdout(self):
        data = self.process.readAllStandardOutput()
        text = bytes(data).decode("utf-8").strip()
        if text:
            self.append_info_text(text, show_time=False)
            self.append_info_text("--------------------------------", show_time=False)

    def handle_stderr(self):
        data = self.process.readAllStandardError()
        text = bytes(data).decode("utf-8").strip()
        if text:
            self.append_info_text(f"ERROR: {text}")
