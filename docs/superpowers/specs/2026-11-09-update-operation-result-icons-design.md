# Update Operation Result Icons Design

## Intent

Show direct success or failure feedback beside each Update-screen action so operators do not have to interpret the console log.

## Selected Approach

Use the same fixed-width green `✓` / red `✗` labels as the Test screen, with one label beside each top-level button:

- `Entry update mode`
- `Update`
- `Reboot`

The alternative considered was clearing only the clicked button's result exactly like the Test screen. The selected workflow-aware approach also clears downstream results so a previous update session cannot look current.

## Layout and Result Lifecycle

- Each button and its result label share one horizontal row.
- Labels start blank; running an operation leaves its label blank until the operation reaches a terminal result.
- Clicking `Entry update mode` clears Entry, Update, and Reboot results.
- Clicking `Update` clears Update and Reboot results.
- Clicking `Reboot` clears only Reboot.
- Selecting another firmware folder clears Update and Reboot because their old results refer to a different package.
- Use operation tokens, as on the Test screen, so callbacks from an older run cannot overwrite a newer result.

## Success and Failure Rules

- Entry succeeds only after a Fastboot device is detected. It fails when an ADB entry command fails, a required process cannot start, or Fastboot polling is exhausted.
- Update succeeds only after Bootloader A/B, Kernel, and File System flashing all finish successfully. Missing files, non-zero process exits, or process launch failures show failure and stop the chain.
- Reboot succeeds only when `fastboot reboot` exits with code `0`; non-zero exit or launch failure shows failure.
- The console log remains available for details; result icons summarize the final outcome.

## Scope

- Modify `UpdateTab` and its focused tests only.
- Reuse Qt text symbols and styling already used by `TestTab`; add no image assets or dependencies.
- Do not change firmware filenames or the successful flash command sequence.
