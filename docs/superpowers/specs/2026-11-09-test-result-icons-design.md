# Test Result Icons Design

## Intent

Show an immediately visible pass/fail result beside each Test-tab action so factory operators do not need to infer the final outcome from the log.

## Behavior

- Place a dedicated result label to the right of each Test button: Dual Mode Test, SDCard Test, and Reset.
- Empty text means no current result, green `✓` means pass, and red `✗` means fail.
- All labels start empty. Clicking a test clears only that test's previous result before starting it.
- When device status is anything other than `Online`, disable the buttons and clear every result label.
- A callback from an operation started before a disconnect or mode change must not restore a stale result, even if the device later reconnects.

## Final-result rules

- Dual Mode passes only when both the parameter update and the subsequent camera-service restart succeed. Either failure shows `✗`.
- SDCard passes only when mount detection and the read/write/remove test succeed. Either failure shows `✗`.
- Reset passes only when parameter removal, sync, and the subsequent camera-service restart succeed. Any failure shows `✗`.

## Approach

Selected: use separate `QLabel` widgets with Unicode symbols and explicit green/red styling. This keeps button text stable, is deterministic in tests, and avoids platform-dependent system icon artwork. The existing asynchronous workflows remain intact; they gain result ownership and a generation guard so obsolete callbacks cannot repopulate cleared indicators.

Rejected alternatives: appending symbols to button text makes labels shift and mixes action with state; `QStyle` icons vary by platform and are harder to verify consistently.

## Constraints

- Keep the existing log messages and device-status behavior.
- Add no image assets or dependencies.
- Do not cancel or otherwise alter the underlying ADB operations when status changes; only invalidate their result display.
