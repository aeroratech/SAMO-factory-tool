import unittest

from device_monitor import DeviceMonitorThread, probe_device_status


class DeviceStatusProbeTests(unittest.TestCase):
    def test_fastboot_device_has_upgrade_priority(self):
        calls = []

        def run_command(program, arguments):
            calls.append((program, arguments))
            if program == "fastboot":
                return "camera-001\tfastboot\n"
            return "device\n"

        self.assertEqual("Upgrade", probe_device_status(run_command))
        self.assertEqual([("fastboot", ["devices"])], calls)

    def test_adb_device_is_online_when_fastboot_is_empty(self):
        outputs = {"fastboot": "", "adb": "device\n"}

        def run_command(program, arguments):
            return outputs[program]

        self.assertEqual("Online", probe_device_status(run_command))

    def test_missing_fastboot_and_adb_devices_are_offline(self):
        self.assertEqual("Offline", probe_device_status(lambda *_: ""))


class DeviceMonitorThreadTests(unittest.TestCase):
    def test_poll_emits_only_when_status_changes(self):
        outputs = {"fastboot": "", "adb": "device\n"}
        statuses = []
        monitor = DeviceMonitorThread(
            run_command=lambda program, _arguments: outputs[program]
        )
        monitor.status_changed.connect(statuses.append)

        monitor.poll_status()
        monitor.poll_status()
        outputs["fastboot"] = "camera-001\tfastboot\n"
        monitor.poll_status()

        self.assertEqual(["Online", "Upgrade"], statuses)


if __name__ == "__main__":
    unittest.main()
