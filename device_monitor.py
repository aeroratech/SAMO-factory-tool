from PySide6.QtCore import QProcess, QThread, Signal


def probe_device_status(run_command):
    """Return the current device mode, preferring Fastboot over ADB."""
    fastboot_output = run_command("fastboot", ["devices"])
    if fastboot_output.strip():
        return "Upgrade"

    adb_output = run_command("adb", ["get-state"])
    if adb_output.strip() == "device":
        return "Online"

    return "Offline"


class DeviceMonitorThread(QThread):
    status_changed = Signal(str)

    def __init__(self, interval=2, run_command=None):
        super().__init__()
        self.interval = interval
        self._run_command = run_command or self._execute_command
        self._running = True
        self._last_status = None

    @staticmethod
    def _execute_command(program, arguments):
        process = QProcess()
        process.start(program, arguments)
        if not process.waitForStarted(1000):
            return ""
        if not process.waitForFinished(3000):
            process.kill()
            process.waitForFinished(1000)
            return ""
        if process.exitCode() != 0:
            return ""
        return bytes(process.readAllStandardOutput()).decode(
            "utf-8", errors="ignore"
        )

    def poll_status(self):
        status = probe_device_status(self._run_command)
        if status != self._last_status:
            self.status_changed.emit(status)
            self._last_status = status
        return status

    def run(self):
        while self._running:
            self.poll_status()
            for _ in range(max(1, self.interval * 10)):
                if not self._running:
                    return
                self.msleep(100)

    def stop(self):
        self._running = False
        self.wait()
