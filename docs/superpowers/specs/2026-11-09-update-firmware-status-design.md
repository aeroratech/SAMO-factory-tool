# Update Firmware Status Design

## Goal

Add a persistent firmware-package status area to the Update screen so an operator can see immediately whether all three required firmware files were found in the selected folder.

## User Interface

- Place an `Update Package` group directly below the update-folder selector.
- Show one row for each required file:
  - `abl.elf`
  - `qti-ubuntu-robotics-image-qrb5165-rb5-boot.img`
  - `qti-ubuntu-robotics-image-qrb5165-rb5-sysfs.ext4`
- Before a folder is selected, every row displays `Missing: <filename>` with a red cross.
- After a folder is selected, each row displays `Ready ✓` when the exact path is a regular file, otherwise `Missing: <filename> ✗`.
- All three files are required. Unlike the D64TR reference project, `abl.elf` is not optional and there are no optional-package controls.

## State and Validation

- Keep separate state for firmware-package readiness and Fastboot-device readiness.
- Enable `Update` only when all three files are present and a Fastboot device has been detected.
- Folder selection refreshes all three status rows immediately and logs the selected folder.
- Starting a device-mode check temporarily clears Fastboot readiness but preserves the selected-folder status.
- Revalidate all three paths when `Update` is clicked. If a file was removed or changed after folder selection, refresh the status area, log that required firmware is missing, and do not start flashing.
- On failed or completed flash steps, recompute the Update button from both readiness conditions instead of enabling it unconditionally.

## Structure

- Keep the change in the existing `UpdateTab` rather than restructuring the current update workflow.
- Define the three firmware filenames once as module-level constants and reuse them for status checks and flash paths.
- Add focused Update-tab tests using the repository's `unittest`, offscreen Qt, and mocked process style.

## Compatibility

- Use text symbols (`✓` and `✗`) rendered by Qt, matching the existing Test-screen indicators and remaining portable on Windows.
- Do not add dependencies or change the existing command sequence.
