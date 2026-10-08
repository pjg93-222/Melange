# Unattended refresh: progress and next steps

Written 2026-09-20 about 00:30 local by Claude Fable 5.1 (session "Normalize mixed line endings in LIVE
tree", worktree `vibrant-sammet-a549a5`). Updated at the end of the session; the status lines below say
what was true at the last update.

## 1. The one-paragraph state

The weekly refresh has not completed since 2026-07-19. Today's work replaced the idea of repairing the
49-step run with a **tick runner**: every fire runs only the steps that are due and not good, each one
isolated and bounded, and publishes only when every evidence source is present, intact and recent.
The runner, the press changes and the lease fix are **built, reviewed and tested on a branch; nothing
from them is on main yet**. An independent break-it pass found real bugs in the runner; the fixes are
being finished now. The scheduled task still launches the old orchestrator, so the 06:00 run on
2026-09-20 behaves as before (collectors run, the press walk exits 3, the run aborts).

## 2. What is already on main (landed earlier on 2026-09-19)

| Commit | What it does |
|---|---|
| `423820d76` | `fec/tools/live_patch.py`: the line-wise, byte-exact cutter for patches against the live tree (92 tests). |
| `99caafa95` | The staffer-network test can no longer hang the kernel (180 s bound). |
| `624e593eb` | `fec/bounded_subprocess.py`; `run_pipeline.py` and `run_tests.py` launch every child bounded. |
| `62aea2f76` | Every weekly-refresh step launches bounded; an unkillable child can no longer pin the writer lease. |
| `61be75ddc` | The weekly refresh no longer dies in 0.2 s on two unrelated `__init__.py` files. |

## 3. What is on the branch `claude/refresh-tick-20260919` (NOT landed)

| Commit | What it does | Status |
|---|---|---|
| `b7fa97dc4` | Press: deferred body URLs are counted per sealed run and stop refusing intake after three consecutive deferrals; zero-row member sites go on a review list; a pruned promoted run is skipped and recorded instead of crashing the fold. | reviewed |
| `a66b39850` | Press baseline fold ON by default. **Rank-affecting** once it first folds (the tone supplement is rebuilt from one run's delta). Its own commit so it can be dropped. | reviewed, **held for your yes** |
| `117788834` | Only sealed runs count; a member that cannot be drained at all is tombstoned as a member and named in the receipt as a standing coverage hole. | reviewed |
| `c1f0b0bb1` | Wording fixes (the "frozen since 06-24" comments were wrong: the baseline was folded once on 09-01). | reviewed |
| `7b3b5270d` | R: maintenance retries run again when every pending row is excused by the tombstone ledger (11,532 revisits were starved; cap 100 per run). Missing ledger = today's behaviour. | reviewed, **held for your yes** |
| `e8bda5d65` | Test: the R gate reads a ledger the Python module really wrote. Depends on `7b3b5270d`. | held with it |
| `1b201d720` | Writer lease records the holder's process creation time, so a recycled pid cannot wedge it and no clock step can make a live holder look stale. | reviewed |
| `326b672ed` | The tick runner: `fec/refresh_table.py`, `fec/refresh_state.py`, `fec/refresh_tick.py`, suite `test_refresh_tick`. | reviewed |
| `6bff03e65` | Wider output watch (data/, outputs/, root data files, the press URL baseline) and seven fixes the builder found itself. | reviewed |
| `406e18e91` | My review fix: a note saved at the project root, an open Excel file or a SQLite sidecar can no longer mark a failing collector "torn". | committed |
| (pending) | Fixes for the sandbox findings in section 5. | **in progress, uncommitted** |

Evidence so far: builder suite 38 tests green; affected existing suites green; kernel from byte-exact
exports is main 220 passed / 29 failed versus branch 222 / 30, with the same 29 failures on both
(an export lacks untracked runtime data), the three new suites passing, and `test_daily_refresh`
proven flaky on main itself (5 of 12 runs fail there; a separate session is now fixing it). The real
kernel gate is a run from the live tree after landing (expected: 249 passed, the 2 known reds).

## 4. Codex

- Cause: OpenAI removed `codex mcp-server` in CLI 0.154.0; the app updated itself on 09-17 16:43, so
  every new session shows `codex (CONNECTION_CLOSED)`. Sign-in is fine.
- Repaired: `~\.codex\bin\codex-mcp.cmd` now falls back to a pinned copy of the last build that serves
  MCP (`~\.codex\bin\mcp-serve-pin\`, hard links, no download; backup `codex-mcp.cmd.bak-20260919`).
  That build refuses `gpt-6-astra`, so the MCP tools only work with `model: gpt-5.6-sol` per call.
- Astra works today through `codex exec` on the app's current build, hardened (read-only, empty
  directory, all tools off). That is how the council critique was obtained.
- `codex` is now on PATH through `%APPDATA%\npm\codex.cmd` (delete that one file to undo).
- **Your step:** install the official plugin in a terminal `claude`:
  `/plugin marketplace add openai/codex-plugin-cc`, `/plugin install codex@openai-codex`, `/codex:setup`.

## 5. Independent sandbox pass (57 scenario roots, 100+ ticks, stub producers, nothing outside the sandbox)

Passed: clean run, retry of filed failures, degraded and refused publication, press exit 3 as PARTIAL,
crash at five internal points plus an external kill (all converge in one tick to byte-identical
output), torn detection, zero floor, lease wait and reclaim (dead pid, recycled pid, old lock format),
second instance, CTRL_BREAK in 0.7 s, unwritable marker, corrupt or future-schema state, budget,
compute gating and audit tolerance, unicode, missing producer, 30,000-file scale (11 s per snapshot).

| Finding | What goes wrong | Fix | Status |
|---|---|---|---|
| HIGH-1 | A collector's file collapsing from 60 rows to 0 is missed when a later step also writes that file, and the tick publishes. | The zero floor now compares against what the step itself last produced, which survives the hand-over. | in progress |
| HIGH-2 | After a backward clock step, a tick that collected new evidence exits 0 "nothing due", permanently. | "New evidence" is decided by each source's generation counter recorded in the publication, not by wall-clock stamps; evidence collected in this tick always counts. | in progress |
| HIGH-3 | A stale lease token in the environment makes the tick poll six hours for a lease nobody holds. | Fatal before step 1, in under a second, with the variable names in the message. | coded |
| MEDIUM-4 | One locked manifest file erases a step's recorded success. | Retry the read; a file that cannot be opened no longer demotes the step; a missing or corrupt one still does, and the step is due at once. | in progress |
| MEDIUM-5 | A hung press walk (36 h table timeout, 18 h tick) eats the whole tick, every tick. | No step may use more than half a tick; a step that timed out is retried only if the remaining budget could survive a second hang. | in progress |
| MEDIUM-6 | The runner imported a producer module to find one path, in every mode. | The path is restated from `paths.DRAFT` and pinned by a test; the runner imports no producer. | coded |
| LOW-7 | The review file grows without bound. | Capped at 2,000 rows; the oldest information-only rows go first. | coded |
| LOW-8 | `*.log` producer outputs are never watched. | Left as is, on purpose: logs are not evidence. | decided |
| mine | A source that has truly gone quiet would block publication until someone edited state by hand. | `--accept-zero NAME`: the owner accepts that step's next zero-floor verdict; recorded in the review file. | in progress |

## 6. Decisions that are yours

1. **Fold default ON** (`a66b39850`): yes or no. Nothing folds until a press run is promoted again, which
   needs two more sealed walks, so there is time. Rank-affecting when it happens.
2. **Gated R retries** (`7b3b5270d` + its test): yes or no. Inert until the ledger has three sealed runs.
3. **Cutover of the scheduled task** to the tick runner. I will not touch a scheduled task without your
   explicit yes. Proposed (untested until you approve):
   ```powershell
   $py  = "C:\Users\pgoff\AppData\Local\Programs\Python\Python312\python.exe"
   $fec = "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\fec"
   $act = New-ScheduledTaskAction -Execute $py -Argument ('"' + "$fec\refresh_tick.py" + '"') -WorkingDirectory $fec
   Set-ScheduledTask -TaskName "MoneyballWeeklyRefresh" -Action $act
   ```
   Roll back by setting the argument back to `weekly_refresh.py`. A daily 06:00 trigger plus an
   at-logon trigger would make ticks converge faster (a tick with nothing due exits in seconds).
   "Run whether logged on or not" needs your Windows password, so that part is yours.
4. **Disk**: C: fell to 9.6 GB free. 93 GB of that is this session's kernel exports
   (`scratchpad\tick_runner\build\`: `base.tar`, `tip.tar`, `export_base`, `export_tip`,
   `kernel_export`). They are reproducible; every result file sits outside those five paths.
   Deleting them is your step. Something else consumed about 15 GB between 22:50 and 23:37 and then
   stopped; I did not find it.
5. Owner-only machine items from the crash forensics: turn off Fast Startup, fix crash dumps
   (pagefile), enable the Task Scheduler operational log, check the NVMe link (59 corrected WHEA errors).

## 7. After cutover, publication still stays blocked, loudly, until

- two more sealed press walks tombstone the nine stuck members (press rows are evidence; "has never
  succeeded" blocks). `--force-due "press delta refresh"` on two days would get there sooner;
- the six un-ratified audit reds are ratified or fixed (a novel audit failure is COMPUTE_FAILED);
- the other lanes' chain blockers clear (interview duplicates at chain step 3; the paid
  `sentinel_admissions` step from 2026-09-21T03:41Z);
- the reference-layer step still calls the AI; the session "Python process independence from AI" owns that.

If `MoneyballCollectorSupervisor` (disabled since 09-01) is ever re-enabled, it must first learn to read
`data/engine/refresh_tick_status.json`; today it relaunches the whole old orchestrator and accepts only
the old status file.

## 8. Known limits of the runner (v1)

`C:\melange-data\*` audio outputs are not watched. About 7 MB of pre-snapshot is written per step
(roughly 350 MB of OneDrive churn for a full 50-step tick); one snapshot plus deltas would cut that.
After a console kill the marker shows the phase it died in with a dead pid; `--status` renders the truth
from the state file. The table is pinned to `weekly_refresh.py` by an AST test while both exist.

## 9. Remaining steps in this session, in order

1. Finish and test the section-5 fixes; commit.
2. Re-run the failing sandbox scenarios against the new tip.
3. Build the landing tip = branch tip plus one revert commit holding items 1 and 2 of section 6.
4. Land with the usual preconditions (on main, fast-forward only, no lock, paths clean), run the kernel
   from the live tree, emit the Glass Box event, record the decision and the dead end in the Project Brain.
5. Report.

## 10. Where things are

- Design contract, the packet sent to Codex and Astra's critique verbatim: this directory.
- Sandbox harness and per-scenario evidence: session scratchpad `tick_runner\sandbox_tick\`.
- Builder evidence (suite, kernel, scan timing): session scratchpad `tick_runner\build\*.txt`.
- Memory: `weekly-refresh-self-sufficiency-audit-2026-09-19.md`, `codex-executor-lane-2026-07-18.md`,
  `lg-gram-npu-crash-2026-08-17.md`.
