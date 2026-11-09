# Test Result Icons Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add clear pass/fail indicators beside all Test-tab buttons and keep their state correct across retries and device-mode changes.

**Architecture:** `TestTab` will own three adjacent `QLabel` indicators plus a small token-based result-state API. Each asynchronous workflow carries its test name and run token through to the terminal callback, so intermediate success cannot show a pass and callbacks invalidated by a new run or device-mode change cannot restore stale results.

**Tech Stack:** Python 3, PySide6 (`QLabel`, layouts, `QProcess`), `unittest`

**Spec:** `docs/superpowers/specs/2026-11-09-test-result-icons-design.md`

## Global Constraints

- Empty text means no current result, green `✓` means pass, and red `✗` means fail.
- Clicking a test clears only that test's prior result before its ADB workflow starts.
- Any status other than `Online` disables actions, clears all results, and invalidates in-flight result callbacks.
- Keep existing log messages and ADB command sequences.
- Add no assets or dependencies and do not cancel ADB operations on status changes.

## Review Focus

- A callback from before an Offline/Upgrade transition must remain invalid after a later reconnect; covered by Task 1 stale-token test.
- Starting the same test twice must prevent the first run from overwriting the second run's state; covered by Task 1 repeated-run test.
- Dual Mode and Reset must remain blank after their first command succeeds and show pass only after service restart succeeds; covered by Task 2 intermediate-success tests.
- Mount/delete/sync failures must immediately show failure without a later stage changing it; covered by Task 2 early-failure tests.
- The shared service-restart path must update only the originating Dual Mode or Reset indicator; covered by Task 2 result-ownership tests.

---

### Task 1: Result indicator UI and lifecycle state

**Files:**
- Modify: `test.py`
- Modify: `tests/test_test_tab.py`

**Interfaces:**
- Consumes: `TestTab.set_device_online(online: bool)` from the main-window integration.
- Produces: `dual_result_label`, `sdcard_result_label`, and `reset_result_label`; `_begin_test(test_name: str) -> int`; `_complete_test(test_name: str, passed: bool, token: int)`; `_clear_all_test_results()`.
- Test names are the literals `"dual"`, `"sdcard"`, and `"reset"`.

- [ ] **Step 1: Write failing indicator initialization and rendering tests**

Add `TestTabResultIndicatorTests` asserting that all three labels exist beside their corresponding buttons, start with empty text and no success/failure color, and that `_complete_test()` renders green `✓` for pass and red `✗` for failure when the token is current and the device is Online.

- [ ] **Step 2: Run indicator tests and verify RED**

Run: `QT_QPA_PLATFORM=offscreen python3 -m unittest tests.test_test_tab.TestTabResultIndicatorTests -v`

Expected: failures because the labels and result-state methods do not exist.

- [ ] **Step 3: Implement indicator rows and token-based result rendering**

In `test.py`, import `QLabel`, `QHBoxLayout`, and `Qt`; replace the direct button-only additions with one horizontal row per button and result label. Give labels a fixed display width, centered bold text, and implement the Task 1 interfaces with monotonically increasing run tokens and per-test active-token tracking.

- [ ] **Step 4: Run indicator tests and verify GREEN**

Run: `QT_QPA_PLATFORM=offscreen python3 -m unittest tests.test_test_tab.TestTabResultIndicatorTests -v`

Expected: all indicator rendering tests pass.

- [ ] **Step 5: Write failing clearing and invalidation tests**

Add tests asserting that each `run_*` method clears only its own prior indicator before starting, `set_device_online(False)` clears all three indicators, an old token cannot render after Offline then Online, and a second `_begin_test()` for the same test invalidates the first token.

- [ ] **Step 6: Run lifecycle tests and verify RED**

Run: `QT_QPA_PLATFORM=offscreen python3 -m unittest tests.test_test_tab.TestTabResultLifecycleTests -v`

Expected: failures because click clearing and status invalidation are not wired.

- [ ] **Step 7: Wire test starts and device status to result lifecycle**

Have `run_dual_mode()`, `run_sdcard_test()`, and `run_reset()` call `_begin_test()` before creating a process and capture the returned token in their signal callbacks. Update `set_device_online()` to track online state and call `_clear_all_test_results()` whenever `online` is false.

- [ ] **Step 8: Run all Task 1 tests and verify GREEN**

Run: `QT_QPA_PLATFORM=offscreen python3 -m unittest tests.test_test_tab.TestTabResultIndicatorTests tests.test_test_tab.TestTabResultLifecycleTests -v`

Expected: all Task 1 tests pass.

- [ ] **Step 9: Commit Task 1**

```bash
git add test.py tests/test_test_tab.py
git commit -m "feat: add factory test result indicators"
```

### Task 2: Terminal workflow result integration

**Files:**
- Modify: `test.py`
- Modify: `tests/test_test_tab.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: Task 1's test names, run tokens, and `_complete_test()` method.
- Produces: terminal result reporting for Dual Mode, SDCard, and Reset, including origin-aware `restart_camera_service(test_name: str, token: int)`.

- [ ] **Step 1: Write failing Dual Mode terminal-result tests**

Add tests asserting that a failed parameter update shows Dual `✗`; a successful update leaves the indicator blank while service restart is pending; and service exit 0/1 shows Dual `✓`/`✗` respectively without changing the other indicators.

- [ ] **Step 2: Run Dual Mode tests and verify RED**

Run: `QT_QPA_PLATFORM=offscreen python3 -m unittest tests.test_test_tab.TestTabDualResultTests -v`

Expected: failures because Dual Mode does not report terminal indicator state.

- [ ] **Step 3: Carry Dual Mode ownership through service restart**

Change the Dual finished callback to receive its captured token, report immediate failure on a nonzero exit, and otherwise call `restart_camera_service("dual", token)`. Capture both values in the service finished callback and complete the originating result only when service restart finishes.

- [ ] **Step 4: Run Dual Mode tests and verify GREEN**

Run: `QT_QPA_PLATFORM=offscreen python3 -m unittest tests.test_test_tab.TestTabDualResultTests -v`

Expected: all Dual result tests pass.

- [ ] **Step 5: Write failing SDCard and Reset terminal-result tests**

Add tests asserting that mount failure and read/write failure show SDCard `✗`, full SDCard success shows `✓`, reset delete/sync failure shows Reset `✗`, and Reset stays blank until its service restart reports `✓`/`✗`. Include a test proving a Reset service result does not modify Dual Mode.

- [ ] **Step 6: Run SDCard and Reset tests and verify RED**

Run: `QT_QPA_PLATFORM=offscreen python3 -m unittest tests.test_test_tab.TestTabSdcardResultTests tests.test_test_tab.TestTabResetResultTests -v`

Expected: failures because these workflows do not report owned terminal indicator state.

- [ ] **Step 7: Carry tokens through SDCard and Reset workflow stages**

Capture the SDCard token in mount and function-test callbacks and complete on mount failure or function-test exit. Capture the Reset token through delete and sync callbacks; complete on either failure or pass `("reset", token)` to the shared service-restart path after sync succeeds.

- [ ] **Step 8: Update operator documentation**

In `README.md`, document the empty/green-check/red-cross states, per-click clearing, terminal success rules, and clearing on non-Online status.

- [ ] **Step 9: Run the full suite and diff checks**

Run: `QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -v`

Expected: the full suite passes.

Run: `git diff --check`

Expected: no output and exit code 0.

- [ ] **Step 10: Commit Task 2**

```bash
git add test.py tests/test_test_tab.py README.md
git commit -m "feat: report factory test outcomes"
```
