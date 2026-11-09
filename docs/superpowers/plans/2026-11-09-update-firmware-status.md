# Update Firmware Status Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a fixed Update Package status area and prevent flashing unless all three required firmware files and a Fastboot device are available.

**Architecture:** `UpdateTab` owns three module-level firmware-name constants, three status labels, and two readiness flags. A single package-status refresh validates exact regular files, while a single control-state method combines package readiness with Fastboot readiness; `full_update()` revalidates before launching the existing flash chain.

**Tech Stack:** Python 3, PySide6, `unittest`, `unittest.mock`

**Spec:** `docs/superpowers/specs/2026-11-09-update-firmware-status-design.md`

## Global Constraints

- All three exact firmware names are required: `abl.elf`, `qti-ubuntu-robotics-image-qrb5165-rb5-boot.img`, and `qti-ubuntu-robotics-image-qrb5165-rb5-sysfs.ext4`.
- `abl.elf` is not optional and the UI has no optional-package controls.
- `Update` is enabled only when the package is complete and Fastboot is ready.
- Revalidate immediately before flashing.
- Do not change the existing flash command sequence or add dependencies.

## Review Focus

- A directory with a required filename must remain Missing because only regular files count; test this in Task 1.
- Selecting a second incomplete folder after a complete folder must clear readiness and disable Update; test this in Task 1.
- Detecting Fastboot before selecting a valid folder must not enable Update; test this in Task 2.
- Removing firmware after selection must prevent the flash process from starting; test this in Task 2.
- Flash completion or failure must not re-enable Update if package or Fastboot readiness is false; test this in Task 2.

---

### Task 1: Firmware package status area

**Files:**
- Modify: `update.py`
- Create: `tests/test_update_tab.py`

**Interfaces:**
- Consumes: Existing `UpdateTab` folder selector and update button.
- Produces: module constants `ABL_IMAGE_NAME`, `BOOT_IMAGE_NAME`, `SYSTEM_IMAGE_NAME`; labels `abl_status`, `boot_status`, `system_status`; state `firmware_ready: bool`; methods `set_update_folder(folder: str) -> None` and `_refresh_firmware_status() -> bool`.

- [ ] **Step 1: Write failing status-area tests**

Add `UpdateTabFirmwareStatusTests` asserting initial Missing status for all three rows, `Ready ✓` only for exact regular files, all three files are required, a same-named directory is Missing, and selecting a second incomplete folder clears `firmware_ready` and disables Update.

- [ ] **Step 2: Run the focused tests and verify failure**

Run: `QT_QPA_PLATFORM=offscreen python3 -m unittest tests.test_update_tab.UpdateTabFirmwareStatusTests -v`

Expected: FAIL because the constants, status labels, and refresh methods do not exist.

- [ ] **Step 3: Implement the status area and package validation**

In `update.py`, add the three constants; add a `QGroupBox`/`QFormLayout` below the folder selector; implement `set_update_folder(folder: str) -> None` and `_refresh_firmware_status() -> bool`; make `select_folder()` call `set_update_folder()` and keep its existing log message. Use `os.path.isfile` and set each row to `Ready ✓` or `Missing: <filename> ✗`.

- [ ] **Step 4: Run the focused tests and verify success**

Run: `QT_QPA_PLATFORM=offscreen python3 -m unittest tests.test_update_tab.UpdateTabFirmwareStatusTests -v`

Expected: PASS.

- [ ] **Step 5: Commit Task 1**

```bash
git add update.py tests/test_update_tab.py
git commit -m "feat: show required firmware package status"
```

### Task 2: Gate and revalidate the update workflow

**Files:**
- Modify: `update.py`
- Modify: `tests/test_update_tab.py`

**Interfaces:**
- Consumes: Task 1 constants, `firmware_ready`, and `_refresh_firmware_status() -> bool`.
- Produces: state `fastboot_ready: bool` and method `_update_controls() -> None`; `full_update()` starts flashing only after successful package revalidation.

- [ ] **Step 1: Write failing workflow tests**

Add `UpdateTabReadinessTests` asserting: a complete package alone does not enable Update; Fastboot alone does not enable it; both together do; a missing file after selection blocks `update_bootloader()` and refreshes its row; entering update mode clears only Fastboot readiness; and completion/failure handlers call combined control-state logic rather than unconditionally enabling Update.

- [ ] **Step 2: Run the focused tests and verify failure**

Run: `QT_QPA_PLATFORM=offscreen python3 -m unittest tests.test_update_tab.UpdateTabReadinessTests -v`

Expected: FAIL because Fastboot readiness and combined control-state logic do not exist.

- [ ] **Step 3: Implement combined readiness and preflight validation**

In `update.py`, add `fastboot_ready`; implement `_update_controls() -> None` as `btn_update.setEnabled(firmware_ready and fastboot_ready)`; update folder selection, Fastboot detection/failure, entry/reboot transitions, and flash completion handlers to update state then call it. Make `full_update()` call `_refresh_firmware_status()` and log `ERROR: Missing required firmware files.` without starting the bootloader process when validation fails. Reuse the filename constants in all three flash stages.

- [ ] **Step 4: Run Update-tab tests and verify success**

Run: `QT_QPA_PLATFORM=offscreen python3 -m unittest tests.test_update_tab -v`

Expected: PASS.

- [ ] **Step 5: Run the full regression suite**

Run: `QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -v`

Expected: all tests PASS.

- [ ] **Step 6: Commit Task 2**

```bash
git add update.py tests/test_update_tab.py
git commit -m "feat: require complete firmware before update"
```
