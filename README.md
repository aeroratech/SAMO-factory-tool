# Factory Test Tool

Desktop GUI tool (PySide6) for SAMO (`qrb5165-rb5`) factory operations over `adb` and `fastboot`.

## Overview

The app has 4 tabs:

- `Info`: Read camera/gimbal version files from target device.
- `Update`: Flash bootloader, kernel, and filesystem images.
- `Settings`: Read and set the connected device's hardware version.
- `test`: Run factory checks (dual mode, SD card test, reset).

## Requirements

- Python `3.7+`
- `adb` in `PATH`
- `fastboot` in `PATH`
- GUI-capable host (Linux/Windows/macOS)

Python dependencies:

```bash
pip install -r requirements.txt
```

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Sanity check tools:

```bash
adb version
fastboot --version
```

## Update Package Layout

When selecting an update folder in the `Update` tab, it must include:

- `abl.elf`
- `qti-ubuntu-robotics-image-qrb5165-rb5-boot.img`
- `qti-ubuntu-robotics-image-qrb5165-rb5-sysfs.ext4`

## Tab Behavior

A global device status is shown above all four tabs:

- `Upgrade`: `fastboot devices` returns a device.
- `Online`: no Fastboot device is present and `adb get-state` returns `device`.
- `Offline`: neither Fastboot nor ADB reports a device.

### Info Tab

- `Version` runs:
  - `adb shell cat /etc/aerora-version`
  - `adb shell cat /etc/gimbal-version`
- `Clear` clears the log.

### Update Tab

1. Click `Select Update Folder`.
2. Click `Entry update mode` (runs `adb root`, waits for the device, then `adb reboot bootloader`).
3. Tool waits and checks `fastboot devices`.
4. Click `Update` to run full chain:
   - `fastboot flash abl_a abl.elf`
   - `fastboot flash abl_b abl.elf`
   - `fastboot --slot all flash boot ...boot.img`
   - `fastboot --slot all flash system ...sysfs.ext4`
5. Click `Reboot` (runs `fastboot reboot`) after successful flash.

Notes:

- `Update` is disabled until a fastboot device is detected.
- `Reboot` is enabled after full update success (and can also be enabled after fastboot detection).

### test Tab

- Factory test actions are enabled only while the global status is `Online`.
- `Dual Mode Test` updates `CAM_DIS_MODE` to `"3"` in `/data/camera/cam_param.bin`, then restarts the `mav_client` camera service.
- `SDCard Test` checks mount state (`/mnt/sdcard`) and runs write/read/remove test.
- `Reset` removes `/data/camera/cam_param.bin`, syncs, then restarts the `mav_client` camera service.

### Settings Tab

- Settings controls are enabled only while the global status is `Online`.
- Opening the tab reads `persist.usb.hardware.version` with `adb shell getprop`.
- Only the exact value `v1` is shown as V1; an empty or any other value is shown as V2.
- Applying V1 writes `v1` to the property.
- Applying V2 clears the property instead of writing `v2`.

## Build Executable

```bash
pyinstaller \
  --onefile \
  --windowed \
  --icon assets/app-icon.ico \
  --add-data "assets/app-icon.png:assets" \
  main.py
```

Output is generated under `dist/`.

On Windows PowerShell, use `;` instead of `:` in the `--add-data`
value: `"assets/app-icon.png;assets"`.

## Project Files

- `main.py`: Main window and tab container.
- `device_monitor.py`: Shared ADB/Fastboot device status monitor.
- `assets/app-icon.png`: Runtime window/taskbar icon.
- `assets/app-icon.ico`: Multi-size Windows executable icon.
- `info.py`: Device version read UI/logic.
- `update.py`: Full update workflow and fastboot logging.
- `test.py`: Factory test actions and ADB online monitor thread.
- `settings.py`: Hardware-version property UI and ADB read/write logic.

## Troubleshooting

- Device not visible in app:
  - Run `adb devices` and accept device authorization prompt.
  - Confirm USB cable/port and power.
- `Update` button stays disabled:
  - Confirm device is in bootloader mode and visible in `fastboot devices`.
- Flash failures:
  - Verify exact filenames in selected update folder.
  - Re-enter bootloader and retry.
- Linux USB permission issues:
  - Configure proper udev rules for your device vendor and reload udev.

## License

Internal factory use only.
