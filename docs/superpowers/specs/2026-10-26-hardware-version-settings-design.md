# Hardware Version Settings Design

## Intent

Add a dedicated Settings tab so factory operators can see and change the connected device's hardware version without entering ADB commands manually.

## Goals

- Add a `Settings` tab containing V1 and V2 hardware-version choices and an `Apply` button.
- When the settings page is opened, read `persist.usb.hardware.version` with `adb shell getprop`.
- Interpret the trimmed values `v2` and `V2` as V2; interpret an empty value or any other value as V1.
- Default to V1 before the property has been read.
- Applying V1 clears the property by running `adb shell setprop persist.usb.hardware.version ''`.
- Applying V2 runs `adb shell setprop persist.usb.hardware.version v2`.
- Show whether reading or applying the value succeeded, and disable the controls unless the global device state is `Online`.

## Non-goals and constraints

- Do not reboot the device or restart services after changing the property.
- Do not change the existing Info, Update, or TEST behavior.
- Preserve the existing uncommitted `info.py` button-label change.
- Use the project's existing PySide6 `QProcess` pattern and add no dependency.

## Approaches considered

1. **Selected:** V1/V2 radio buttons plus an explicit `Apply` button, with the current value read when the tab is opened. This shows device state while preventing accidental writes.
2. Apply immediately when a choice changes. This saves one click but makes accidental writes easier.
3. Use a drop-down without reading the device. This is simpler but cannot show the current hardware version.

## Implementation boundary

Create a focused settings widget, register it as a fourth main-window tab, propagate the existing online/offline state to it, and test the value mapping, exact ADB commands, page refresh, and offline control state.
