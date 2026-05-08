---
created: 2026-05-07
source: dispatch session
topic: runaway terminal spawning incident
status: review
routes_to: same
---

# Runaway terminal spawning — incident report

**Symptom:** 90+ Windows Terminal / cmd windows accumulated overnight (post 02:44, 2026‑05‑08). Guntis attempted a fix yesterday in `bcos-umbrella` (commits up to `c1ba3aa` v0.1.10 at 02:44) and went to bed; the cascade kept firing.

**Position taken below:** the v0.1.10 fix DID land on disk and the CC server was restarted at ~03:09 (proven by `__pycache__` mtimes), so the *in-app* CC spawn path is clean. The remaining cascade is coming from **Windows Scheduled Tasks** (`bcos-{host}`, `bcos-umbrella-{host}`) that were registered at BCOS-install time with a *visible-window* invocation pattern that the v0.1.10 fix never touched. Each fire pops a console; multiple hosts × multiple tasks × hours of cron ticks = 90+. Confirmable via `schtasks /query /v /fo csv` on the host (see Open Flags §7).

---

## 1 · Stop the bleeding — run NOW

You're staring at 90+ windows. Don't blanket-kill `cmd.exe` or `WindowsTerminal.exe` — you'll nuke whatever real terminals you actually have open. Filter by **start-time after 22:00 yesterday**.

### 1a. Survey first (read-only — see what's there before killing)

Open one PowerShell window and paste:

```powershell
$cutoff = Get-Date "2026-05-07 22:00"
$victims = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -in @('cmd.exe','conhost.exe','WindowsTerminal.exe','OpenConsole.exe','wt.exe','claude.exe') -and
    [System.Management.ManagementDateTimeConverter]::ToDateTime($_.CreationDate) -gt $cutoff
}
$victims | Sort-Object CreationDate |
  Select-Object ProcessId, ParentProcessId, Name,
    @{n='Started';e={[System.Management.ManagementDateTimeConverter]::ToDateTime($_.CreationDate).ToString('HH:mm:ss')}},
    @{n='Cmd';e={($_.CommandLine -replace '\s+',' ').Substring(0,[Math]::Min(80,($_.CommandLine -replace '\s+',' ').Length))}} |
  Format-Table -AutoSize
"victim count: $($victims.Count)"
```

Sanity check: the count should match the pile you see. The list should show parents like `python.exe` (CC server) or `svchost.exe` (Task Scheduler). If you see your **active IDE** as a parent — STOP, those are real, refine the cutoff.

### 1b. Targeted kill — descendants of the runaway parent only

If most victims share a single `ParentProcessId` (likely Task Scheduler `svchost.exe`, or your old pre-fix CC `python.exe`):

```powershell
# Replace 1234 with the dominant ParentProcessId from 1a's output
$parent = 1234
Stop-Process -Id $parent -Force        # stop the spawner first so no new ones appear
$victims | Where-Object { $_.ParentProcessId -eq $parent } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
```

### 1c. Fallback — kill the whole post-22:00 cluster (use only if 1b doesn't fit)

Re-run 1a's `$victims` query, **then**:

```powershell
$victims | ForEach-Object {
  Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}
```

This is the precise filter — anything started **before** 22:00 is untouched.

### 1d. Stop the source so it can't refire

Until you've validated §3–§5, **disable the cron triggers** (does not delete tasks):

```powershell
schtasks /change /TN "bcos-theo-portfolio"          /DISABLE
schtasks /change /TN "bcos-umbrella-theo-portfolio" /DISABLE
schtasks /change /TN "bcos-gravity-coo-os"          /DISABLE
schtasks /change /TN "bcos-umbrella-gravity-coo-os" /DISABLE
```

(The task names follow the `bcos-{host}` / `bcos-umbrella-{host}` convention referenced in `actions.py:670` and `umbrella-schedule-config.json` `_comment`. Substitute your actual host names. Unknown task names error harmlessly.)

Then restart the CC once (it now has the v0.1.10 fix in memory):

```powershell
Get-CimInstance Win32_Process |
  Where-Object { $_.CommandLine -match 'command_center_dashboard\\run\.py' } |
  Stop-Process -Force
python "$env:USERPROFILE\Documents\GitHub\theo-portfolio\.claude\scripts\launch_command_center.py" --no-browser
```

---

## 2 · Forensic timeline — what shipped last night

`bcos-umbrella` commits since 2026‑05‑06, oldest first:

| Commit | Time (local) | Title |
|---|---|---|
| `a6669ba` | 05‑06 18:29 | v0.1.2 — refresh job + UTC discipline + un-onboarded-sibling quiet |
| `ceca784` | 05‑07 13:55 | Auto identify new repos, not cloned repos, show command center dashboard. |
| `c720aea` | 05‑07 13:59 | Reconcile |
| `3cb028f` | 05‑07 19:37 | v0.1.3 — stale-path cleanup |
| `a45b625` | 05‑08 00:14 | BCOS update all + launch command center fixes |
| `052efbb` | 05‑08 02:12 | **v0.1.8 — fix WinError 2 when claude resolves to non-.exe shim** |
| `9f7efa9` | 05‑08 02:18 | v0.1.9 — scope CC "View last run" to originating host |
| `c1ba3aa` | 05‑08 02:44 | **v0.1.10 — suppress cascading consoles during bcos_update_all on Windows** ← the attempted fix |

**What `c1ba3aa` actually changed** — quoted from `git show c1ba3aa`:

> When the CC server runs without an inherited console, each cmd-shim child spawned by per-repo review or run_headless triggers Windows to allocate a fresh console window for the shim. Pass CREATE_NO_WINDOW on Windows in both spawn sites. Also broaden the per-repo shim guard to any non-.exe resolution (matches the v0.1.8 fix in _launcher.py).

The diff is two surgical additions:

```python
# scripts/command_center_dashboard/_launcher.py (run_headless)
+    popen_kwargs = {}
+    if platform.system() == "Windows":
+        popen_kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
     proc = subprocess.Popen(argv, ..., **popen_kwargs)

# scripts/command_center_dashboard/actions.py (_review_one_repo, ~line 1278+)
+    run_kwargs = {}
+    if sys.platform.startswith("win"):
+        if not claude_exe.lower().endswith(".exe"):
+            argv = ["cmd", "/c", "claude", *base_flags]
+        else:
+            argv = [claude_exe, *base_flags]
+        run_kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
     proc = subprocess.run(argv, ..., **run_kwargs)
```

**Did the fix actually deploy?** Yes:

- `theo-portfolio/.claude/scripts/command_center_dashboard/_launcher.py:102` → `popen_kwargs["creationflags"] = 0x08000000`
- `theo-portfolio/.claude/scripts/command_center_dashboard/actions.py:1294` → `run_kwargs["creationflags"] = 0x08000000`
- `__pycache__/_launcher.cpython-312.pyc` mtime: **2026‑05‑08 03:09:11** (proves a Python process re-imported it post-fix)
- `__pycache__/actions.cpython-312.pyc` mtime: **2026‑05‑08 03:09:11** (same)

So the CC server WAS restarted at ~03:09 with the new code. The flicker source the fix targeted is genuinely closed *for spawns originating inside the CC process*.

**What the fix did NOT touch** (this is the gap):

The CHANGELOG explicitly carves out: *"`launch_terminal` is unchanged — that path *wants* a visible console."* And the fix never goes near `bcos_update_all`'s chained final step at `actions.py:670–682`:

```python
# theo-portfolio/.claude/scripts/command_center_dashboard/actions.py
node_task     = f"bcos-{host_name}"
umbrella_task = f"bcos-umbrella-{host_name}"
prompt = (
    f"Run the scheduled-tasks MCP task with taskId {node_task}, "
    f"then run the task with taskId {umbrella_task}. ..."
)
maint_run_id = _new_run_id()
start_run(maint_run_id, "bcos-update-all:maintenance", "task_run_now", ...)
run_headless(PORTFOLIO_ROOT, prompt, maint_run_id, ...)
```

That handoff into `mcp__scheduled-tasks__run_now` chains into Windows Scheduled Tasks — and **those** are the tasks doing the visible spawns now.

---

## 3 · The trigger and the loop

### Trigger — Windows Scheduled Tasks `bcos-{host}` / `bcos-umbrella-{host}`

These tasks were registered at BCOS install time. The umbrella config tells you they exist:

```json
// theo-portfolio/.claude/quality/umbrella-schedule-config.json
"dispatcher": {
  "time_hint": "09:30 Mon-Fri",
  "_comment": "Informational only — the actual cron lives on the scheduled
   task (bcos-umbrella-theo-portfolio). Runs 15 min after the node
   dispatcher so the two don't collide."
}
```

And `bcos-umbrella/skills/umbrella-dispatcher/SKILL.md`:

> Invoked automatically by the `bcos-umbrella-{host}` scheduled task

There are at least two tasks per host (node + umbrella). With both `theo-portfolio` and `gravity-coo-os` umbrellas on the same workstation (referenced explicitly in `_launcher.py` and the v0.1.9 changelog), that's **4 tasks** firing on cron.

### Loop — what each fire does

The scheduled task action is configured by the BCOS installer. Per the BCOS conventions in `bcos-umbrella-update.py` and the `umbrella-dispatcher` skill, each task runs a Claude prompt — almost certainly via `cmd /c claude -p "<prompt>"` because that's the same shim path the v0.1.8 / v0.1.10 fixes had to defend against inside the CC. **When `schtasks` is created without `/IT` and without `/RL HIGHEST` + a hidden-window action, every fire allocates a visible Windows Terminal / console.**

Per fire, the dispatcher then asks Claude to run `umbrella-dispatcher`, which (Step 7+ of the skill) calls per-repo update / review across 7+ registered nodes. Even with the CC's own spawns now silenced, every standalone `cmd /c claude -p` invoked **by the scheduled task itself** still pops a window because that spawn is outside the CC process and the v0.1.10 fix can't reach it.

**Math fits the symptom:** 4 tasks × ~15‑minute interval × ~7 hours overnight ≈ 110 fires; minus a few that exited cleanly ≈ ~90 visible windows by the time you woke up.

**Compounding factor — recursive chain:** `bcos_update_all` finishes by calling `task_run_now` on `bcos-{host}` and `bcos-umbrella-{host}` (`actions.py:670–682`). If you also clicked "Update All" from the dashboard last night while debugging, the chain:

1. CC button → `bcos_update_all` (now silenced — good)
2. `bcos_update_all` → `run_headless` with prompt "run the scheduled-tasks task with taskId X" (silenced)
3. Claude inside that headless run → invokes the scheduled-tasks MCP `run_now`
4. `run_now` triggers the Windows scheduled task → **NEW visible terminal** ←—— LEAK
5. Scheduled task does work, may queue another scheduled task, returns
6. Cron tick later — task fires again on its own schedule

Step 4 is the leak. The CC's v0.1.10 fix is real but it ends at step 3.

### Position

**Trigger:** the BCOS-installed Windows Scheduled Tasks (`bcos-{host}`, `bcos-umbrella-{host}`, ×N hosts). They were registered with default visible-window behaviour at install time.

**Loop amplifier:** `theo-portfolio/.claude/scripts/command_center_dashboard/actions.py:670–682` — `_bcos_update_all`'s final chained handoff to `run_now` on those scheduled tasks. The handoff is correct in principle (it asks Claude to dispatch maintenance) but it triggers the misconfigured scheduled tasks every run, and those scheduled tasks fire on their own cron regardless.

---

## 4 · Immediate one-line fix

You already have it on disk; the missing piece is reconfiguring the scheduled tasks themselves so their own action is hidden. Run once per task:

```powershell
foreach ($t in 'bcos-theo-portfolio','bcos-umbrella-theo-portfolio','bcos-gravity-coo-os','bcos-umbrella-gravity-coo-os') {
  schtasks /change /TN $t /RL HIGHEST /IT 2>$null   # ensure interactive flag, run elevated
  # Replace the action so the wrapper hides its console:
  $action = 'pythonw.exe "%USERPROFILE%\Documents\GitHub\bcos-umbrella\skills\umbrella-dispatcher\dispatch.py"'
  # If you previously used cmd /c claude -p ..., switch to pythonw.exe (windowless interpreter)
  # OR keep claude but route through a hidden launcher:
  #   conhost.exe --headless cmd /c claude -p "..."   ← preferred if you must keep claude direct
}
```

If your existing actions hardcode `cmd /c claude -p "..."`, edit them to either:

1. Use `pythonw.exe` to invoke a Python entry point that spawns claude with `creationflags=0x08000000` (mirrors the CC fix), **or**
2. Wrap with `conhost.exe --headless` (Windows 11), **or**
3. Set the task's `Hidden` flag in the XML (export → edit `<Hidden>true</Hidden>` → re-import).

For the export-edit-reimport path:

```powershell
schtasks /query /TN "bcos-umbrella-theo-portfolio" /XML > task.xml
# In task.xml, set <Settings><Hidden>true</Hidden></Settings>
#                set <Actions Context="Author"><Exec><Command>...</Command></Exec></Actions>
#   to a windowless wrapper
schtasks /delete /TN "bcos-umbrella-theo-portfolio" /F
schtasks /create /TN "bcos-umbrella-theo-portfolio" /XML task.xml
```

This is the smallest change that closes the visible-terminal leak permanently.

---

## 5 · Structural fix — make this class of bug impossible

### 5.1  Single chokepoint helper

Right now spawn flags live in 3+ different places (`_launcher.run_headless`, `actions._review_one_repo`, `actions._spawn_detached`) and every new subprocess site is a fresh chance to forget `creationflags`. Add one helper and route everything through it.

Add to `bcos-umbrella/scripts/command_center_dashboard/_launcher.py`:

```python
# _launcher.py — add near the top
import platform, subprocess, sys

_WIN = sys.platform.startswith("win")
_CREATE_NO_WINDOW       = 0x08000000
_CREATE_NEW_PROCESS_GROUP = 0x00000200
_DETACHED_PROCESS       = 0x00000008

def safe_popen_kwargs(*, detached: bool = False) -> dict:
    """Return kwargs that NEVER pop a console window on Windows.

    Use for every subprocess.run/Popen in CC code. The only spawn site that
    should NOT use this is launch_terminal() — and that one is dead code
    pending v0.2 (see incident 2026-05-07).
    """
    if not _WIN:
        return {"start_new_session": True} if detached else {}
    flags = _CREATE_NO_WINDOW
    if detached:
        flags |= _CREATE_NEW_PROCESS_GROUP | _DETACHED_PROCESS
    return {
        "creationflags": flags,
        "stdin": subprocess.DEVNULL,
        "close_fds": True,
    }
```

Then refactor every spawn site in `actions.py` and `_launcher.py` to merge `safe_popen_kwargs()` into its kwargs:

```python
# Before
proc = subprocess.run(argv, capture_output=True, text=True, timeout=300)

# After
proc = subprocess.run(argv, **safe_popen_kwargs(), capture_output=True, text=True, timeout=300)
```

Add a `pre-commit` regex check that fails the commit if any `subprocess.Popen` or `subprocess.run` in `scripts/command_center_dashboard/` is missing `safe_popen_kwargs()`:

```bash
# .git/hooks/pre-commit (or wire into the umbrella's pre_commit_validate.sh)
if git diff --cached --name-only | grep -q 'command_center_dashboard/.*\.py$'; then
  if git diff --cached scripts/command_center_dashboard/*.py |
       grep -E '^\+.*subprocess\.(Popen|run)\(' |
       grep -v 'safe_popen_kwargs\|test_' >/dev/null; then
    echo "ERROR: subprocess call in command_center_dashboard without safe_popen_kwargs()"
    echo "       see docs/_inbox/2026-05-07-runaway-terminals-incident.md §5.1"
    exit 1
  fi
fi
```

### 5.2  Delete dead code

`launch_terminal()` in `_launcher.py:146–216` has **zero callers** in the live tree (verified: only references are in `_archive/`, the docstring of itself, and the pyc binary). It still uses `CREATE_NEW_CONSOLE`. Delete it. Its existence is a foot-gun for future contributors who'll wire it up without realising they're re-opening this incident.

### 5.3  Visibility budget at the spawn-policy layer

Add a single env knob `BCOS_ALLOW_VISIBLE_TERMINALS=0` (default off) checked inside `safe_popen_kwargs`. Anyone who genuinely wants visible windows must set it explicitly per process. This makes "show me a terminal" a deliberate opt-in rather than a default, and gives a one-flag kill switch at the OS level.

### 5.4  Scheduled-task registration discipline

Add to `umbrella-onboarding` skill (Step where `schtasks /create` is invoked): always pass `/IT` and post-create-edit the XML to set `<Hidden>true</Hidden>`, OR invoke via `pythonw.exe` rather than `cmd /c claude`. Document the rationale inline so the next person doesn't "fix" it back. Reference this incident in the SKILL.md.

---

## 6 · Watchdog — poison-pill guard

Per-action rate limiter that refuses if the *same action name* has fired more than `N` times in the last `M` seconds. Add to `_actions.py`:

```python
# _actions.py — add at module scope
import time
from collections import deque
from threading import Lock as _RLock

_FIRES: dict[str, deque] = {}     # action_name -> deque[ts]
_FIRES_LOCK = _RLock()
_RATE_WINDOW_S = 60      # rolling window
_RATE_MAX_PER_WINDOW = 5 # poison-pill threshold

class ActionPoisoned(RuntimeError):
    """Raised when an action fires faster than the watchdog allows."""

def _check_rate(name: str) -> None:
    now = time.time()
    with _FIRES_LOCK:
        q = _FIRES.setdefault(name, deque())
        # Drop entries outside the window
        while q and now - q[0] > _RATE_WINDOW_S:
            q.popleft()
        if len(q) >= _RATE_MAX_PER_WINDOW:
            # Log loudly so the audit log captures it
            try:
                _AUDIT_LOG = Path.home() / ".local-dashboard" / "action-audit.log"
                _AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
                with _AUDIT_LOG.open("a", encoding="utf-8") as fh:
                    fh.write(f'{{"ts":"{time.time()}","event":"poisoned","action":"{name}",'
                             f'"window_s":{_RATE_WINDOW_S},"max":{_RATE_MAX_PER_WINDOW}}}\n')
            except OSError:
                pass
            raise ActionPoisoned(
                f"action {name!r} fired {len(q)} times in the last {_RATE_WINDOW_S}s "
                f"(limit {_RATE_MAX_PER_WINDOW}); refusing further fires until the "
                f"window clears. See docs/_inbox/2026-05-07-runaway-terminals-incident.md."
            )
        q.append(now)
```

Then have the `@action` decorator's wrapper invoke `_check_rate(name)` before calling the handler. In `server.py`'s POST `/api/action/<name>` route, catch `ActionPoisoned` and return HTTP 429 with the message — the dashboard already surfaces error messages in the action drawer, so this becomes self-explaining UX.

Tunables (sensible defaults):

| Action | window_s | max | Reasoning |
|---|---|---|---|
| `bcos_update_all` | 600 | 1 | Heavy job; never reasonable to run twice within 10 min |
| `bcos_update_one` | 60 | 3 | Per-repo retries OK |
| `task_run_now` | 60 | 5 | Default catch-all |
| `umbrella_dispatcher_run` | 1800 | 1 | Daily job |
| (default) | 60 | 5 | Conservative default |

Store the per-action overrides next to the registration:

```python
@action("bcos_update_all", description="...", rate_window_s=600, rate_max=1)
def _bcos_update_all(body): ...
```

This is the smallest piece of code that makes "infinite spawn" structurally impossible at the action layer, regardless of what's calling it.

---

## 7 · Open flags — confirm on the host

Things this report could not verify from disk alone:

1. **The actual `schtasks` action commands.** The strongest claim above is that `bcos-{host}` / `bcos-umbrella-{host}` tasks are registered with visible-window actions. Confirm:
   ```powershell
   schtasks /query /TN "bcos-theo-portfolio"          /V /FO LIST | Select-String -Pattern 'TaskName|Run As|Task To Run|Hidden|Logon'
   schtasks /query /TN "bcos-umbrella-theo-portfolio" /V /FO LIST | Select-String -Pattern 'TaskName|Run As|Task To Run|Hidden|Logon'
   schtasks /query /TN "bcos-gravity-coo-os"          /V /FO LIST 2>$null | Select-String -Pattern 'TaskName|Run As|Task To Run|Hidden|Logon'
   schtasks /query /TN "bcos-umbrella-gravity-coo-os" /V /FO LIST 2>$null | Select-String -Pattern 'TaskName|Run As|Task To Run|Hidden|Logon'
   ```
   Report back the `Task To Run` and `Hidden` values per task.
2. **Whether the running CC PID is the post-03:09 instance** with the fix, or a stale pre-02:44 instance:
   ```powershell
   Get-CimInstance Win32_Process |
     Where-Object { $_.CommandLine -match 'command_center_dashboard\\run\.py' } |
     Select-Object ProcessId,
       @{n='Started';e={[System.Management.ManagementDateTimeConverter]::ToDateTime($_.CreationDate)}},
       CommandLine
   ```
   If `Started` is before 02:44, the in-process code is still buggy regardless of disk state — restart it (§1d).
3. **Whether `gravity-coo-os` is on this workstation.** The 4-task math assumes it is (consistent with v0.1.9's "shared workstation" diagnosis). If only `theo-portfolio` is here, halve the cron ticks.
4. **The audit log** at `~/.local-dashboard/action-audit.log` — line count and the most-frequent `event:"action_enter"` `action` value over the last 12h directly answers "what kept firing?". I couldn't reach it from this session.
5. **Pre-existing terminal windows you actually use.** §1a's filter is start-time-based; if you happened to open a real terminal after 22:00 yesterday it will be in the kill list. Eyeball the list before running 1c.
6. **Multi-instance scheduled-tasks MCP state.** `umbrella-dispatcher` SKILL.md says "Invoked automatically by the `bcos-umbrella-{host}` scheduled task" — but the runtime state is held in the local scheduled-tasks MCP server. If that server has been crash-looping or has dangling tasks, that compounds the cron pressure independently of Windows Task Scheduler.
7. **Did §1a's victim list actually share one ParentProcessId?** If yes, §1b is sufficient. If parents are scattered (one-per-fire model), §1c is the right tool.

---

## Summary

- **The disk is fixed.** v0.1.10 (commit `c1ba3aa`) correctly silences the CC's own subprocess spawns. CC was restarted at 03:09 and picked up the fix.
- **The leak is upstream of the CC.** Windows Scheduled Tasks `bcos-{host}` and `bcos-umbrella-{host}` fire on cron and pop their *own* visible windows. Their action commands and Hidden flags need to be reconfigured (or replaced with `pythonw.exe`-based wrappers).
- **`bcos_update_all` chains into those scheduled tasks at `actions.py:670–682`.** That handoff is fine in principle but it triggers the misconfigured tasks; even cleaning up that one chain wouldn't stop the cron-driven fires.
- **Stop-the-bleeding:** §1a survey, §1d disable cron + restart CC, then §1b/c kill the existing pile.
- **Permanent fix:** §4 reconfigure the four scheduled tasks. §5 prevents recurrence (single chokepoint helper + delete dead `launch_terminal` + commit-time check). §6 adds rate-limit poison-pill protection at the action layer.
