# Hardware Version Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Settings tab that reads the connected device's hardware version and applies V1 by writing `v1` or V2 by clearing the persistent property.

**Architecture:** A focused `SettingsTab` owns the PySide6 controls and asynchronous ADB property processes. `MainWindow` adds the tab, passes it global online/offline state, and requests a refresh when the operator enters the tab. A small pure mapping function makes the V1-versus-V2 default rule explicit and directly testable.

**Tech Stack:** Python 3, PySide6 (`QWidget`, `QRadioButton`, `QProcess`), `unittest`

**Spec:** `docs/superpowers/specs/2026-10-26-hardware-version-settings-design.md`

## Global Constraints

- Only the exact trimmed property value `v1` means V1; every other value means V2.
- V1 runs the remote shell command `setprop persist.usb.hardware.version v1`.
- V2 runs the remote shell command `setprop persist.usb.hardware.version ''` so ADB preserves the empty value; it must never write `v2`.
- The tab must not reboot the device or restart a service.
- Controls are usable only while the shared device status is `Online`.
- Preserve the user's existing uncommitted `info.py` change.

## Review Focus

- Empty, whitespace-only, `v2`, and unexpected property values all select V2; covered by Task 1 mapping tests.
- A failed or unstartable `getprop` does not silently change the selected hardware version, reports failure, and allows retry; covered by Task 1 read-failure tests.
- A failed or unstartable `setprop` reports failure and allows a retry while the device remains online; covered by Task 1 apply-failure tests.
- A device that disconnects while an operation is running stays disabled when that operation finishes; covered by Task 1 disconnect test.
- Entering the tab repeatedly must not create overlapping property reads; covered by Task 1 in-flight-read test.
- Reads and writes must not overlap or overwrite newer UI state; covered by Task 1 serialization tests.

---

### Task 1: Hardware version settings widget

**Files:**
- Create: `settings.py`
- Create: `tests/test_settings_tab.py`

**Interfaces:**
- Consumes: `adb` from `PATH`; global online state passed as a Boolean.
- Produces: `hardware_version_from_property(raw_value: str) -> str` returning `"v1"` or `"v2"`; `SettingsTab.set_device_online(online: bool)`; `SettingsTab.refresh_hardware_version()`; and `SettingsTab.apply_hardware_version()`.
- Exposes for integration/tests: `radio_v1`, `radio_v2`, `btn_apply`, and `status_label` widgets.

- [ ] **Step 1: Write failing property-mapping tests**

Add `HardwareVersionMappingTests` with separate tests asserting that `"v1\n"` maps to `"v1"`, while `""`, whitespace, `"v2"`, `"V1"`, and an unexpected value each map to `"v2"`.

- [ ] **Step 2: Run mapping tests and verify RED**

Run: `QT_QPA_PLATFORM=offscreen python3 -m unittest tests.test_settings_tab.HardwareVersionMappingTests -v`

Expected: import failure because `settings.py` or `hardware_version_from_property` does not exist.

- [ ] **Step 3: Implement the minimal mapping function**

Create `settings.py` with `PROPERTY_NAME = "persist.usb.hardware.version"` and the exact mapping function only.

- [ ] **Step 4: Run mapping tests and verify GREEN**

Run: `QT_QPA_PLATFORM=offscreen python3 -m unittest tests.test_settings_tab.HardwareVersionMappingTests -v`

Expected: all mapping tests pass.

- [ ] **Step 5: Write failing read-process tests**

Using a controllable fake `QProcess`, add tests that assert:

- a new `SettingsTab` contains mutually exclusive V1/V2 choices, an Apply button, and a status label, with both choices and Apply initially disabled.
- `set_device_online(True)` enables both choices and Apply.
- `refresh_hardware_version()` starts `("adb", ["shell", "getprop", PROPERTY_NAME])` only while online.
- successful output `v1` selects `radio_v1`, while successful empty or non-`v1` output selects `radio_v2`.
- nonzero exit reports a read failure without changing the previous selection.
- a second refresh while the first process is running does not start another process.
- controls stay disabled during a read, Apply cannot start concurrently, and `FailedToStart` reports failure and permits retry.

- [ ] **Step 6: Run read-process tests and verify RED**

Run: `QT_QPA_PLATFORM=offscreen python3 -m unittest tests.test_settings_tab.SettingsTabReadTests -v`

Expected: failures because refresh does not yet start or handle `getprop`.

- [ ] **Step 7: Implement asynchronous property reading**

Implement `SettingsTab(QWidget)` with the tested controls and `refresh_hardware_version()` with `QProcess`. Guard against offline and any active read/write, decode output as UTF-8 with ignored errors, update the radio selection only on exit code 0, handle `FailedToStart`, report success/failure in `status_label`, and release the completed process.

- [ ] **Step 8: Run read-process tests and verify GREEN**

Run: `QT_QPA_PLATFORM=offscreen python3 -m unittest tests.test_settings_tab.SettingsTabReadTests -v`

Expected: all read-process tests pass.

- [ ] **Step 9: Write failing apply-process tests**

Add tests that assert:

- selected V1 starts `("adb", ["shell", "setprop persist.usb.hardware.version v1"])`.
- selected V2 starts `("adb", ["shell", "setprop persist.usb.hardware.version ''"])`, which a POSIX shell parses as an empty value, and no invocation contains `"v2"`.
- Apply is ignored while offline, is disabled while `setprop` runs, and reports success on exit code 0.
- nonzero exit reports failure and re-enables Apply when still online.
- going offline before process completion keeps all controls disabled afterward.
- reads and writes are serialized, and `FailedToStart` reports failure and permits retry.

- [ ] **Step 10: Run apply-process tests and verify RED**

Run: `QT_QPA_PLATFORM=offscreen python3 -m unittest tests.test_settings_tab.SettingsTabApplyTests -v`

Expected: failures because Apply does not yet run or handle `setprop`.

- [ ] **Step 11: Implement asynchronous property writing and connection-state handling**

Implement `apply_hardware_version()` and its completion/error handlers with the exact argument lists above. Track online state, serialize reads and writes, keep controls disabled during operations, restore them only if still online, and leave the selected option visible when the device disconnects.

- [ ] **Step 12: Run the widget tests and verify GREEN**

Run: `QT_QPA_PLATFORM=offscreen python3 -m unittest tests.test_settings_tab -v`

Expected: all Settings-tab tests pass with no warnings or errors.

- [ ] **Step 13: Commit the widget**

```bash
git add settings.py tests/test_settings_tab.py
git commit -m "feat: add hardware version settings widget"
```

### Task 2: Main-window integration and operator documentation

**Files:**
- Modify: `main.py`
- Modify: `tests/test_device_status_ui.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: `SettingsTab` and its three public methods from Task 1.
- Produces: `MainWindow.tab_settings`; a fourth `Settings` tab; online-state propagation; and refresh-on-entry behavior.

- [ ] **Step 1: Write failing main-window integration tests**

Extend `DeviceStatusUiTests` with tests asserting that:

- `MainWindow` exposes `tab_settings` and the tab label is `Settings`.
- `update_device_status("Online")` enables Settings controls and `Offline`/`Upgrade` disable them.
- changing from another tab to Settings while Online calls `refresh_hardware_version()` exactly once.
- entering Settings while Offline does not start a refresh.
- a transition to Online while Settings is already selected requests one refresh.

- [ ] **Step 2: Run integration tests and verify RED**

Run: `QT_QPA_PLATFORM=offscreen python3 -m unittest tests.test_device_status_ui -v`

Expected: failures because `MainWindow` has no Settings tab.

- [ ] **Step 3: Integrate Settings into the main window**

Import and construct `SettingsTab`, add it after TEST as the `Settings` tab, propagate status through `set_device_online(status == "Online")`, connect `QTabWidget.currentChanged` to refresh only when Settings is selected and the status is Online, and refresh once if status becomes Online while Settings is selected.

- [ ] **Step 4: Run integration tests and verify GREEN**

Run: `QT_QPA_PLATFORM=offscreen python3 -m unittest tests.test_device_status_ui -v`

Expected: all device-status UI tests pass.

- [ ] **Step 5: Update user-facing documentation**

Update `README.md` from three to four tabs and document that Settings reads the property, maps only `v1` to V1, writes `v1` for V1, clears the property for V2, and requires an Online device.

- [ ] **Step 6: Run the complete test suite and static diff checks**

Run: `QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -v`

Expected: the full suite passes.

Run: `git diff --check`

Expected: no output and exit code 0.

- [ ] **Step 7: Commit the integration**

```bash
git add main.py tests/test_device_status_ui.py README.md
git commit -m "feat: integrate hardware version settings"
```
