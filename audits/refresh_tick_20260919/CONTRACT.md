# refresh_tick - due-work runner for the Moneyball refresh (design contract, 2026-09-19)

Owner ruling: Paul, 2026-09-19, after the four-voice council plus the Codex Astra critique: "Yeah go forward"
(tick runner recommended over repairing the 49-step resume run). Earlier rulings that bind this design, verbatim:
"make sure that the checkpoint/fail-save for one worker doesn't apply to every single one and stop the whole
process"; "make the weekly poll that continuously updates"; "The lock collision needs verification logic and
retry"; "if a fail is detected it is filed and then returned too once collection for that session is complete";
"We will let it run, making sure it is independent of AI".

## 0. Shape, scope, non-goals

The old orchestrator is ONE run of 49 steps that either finishes or is lost (worst path 76.4 h; not completed
since 2026-07-19; the laptop dies about every two days). The tick runner has NO run that spans days. Every
fire (weekly task, boot, logon, supervisor) is a short TICK: run whatever is due and not good, each step
isolated and bounded, under one hard total budget; then compute and publish only if the publication contract
passes. State lives per STEP, not per run, so a crash costs one step and the next tick continues.

STRANGLER RULE: new files only, plus the two shared-module changes in section 7. `fec/weekly_refresh.py`,
`fec/run_pipeline.py` and every producer stay byte-identical. The scheduled task keeps launching the old
orchestrator until Paul flips it. Nothing in this build may run, import or edit a producer, a collector,
`weekly_refresh.py` or `run_pipeline.py` (import == execution in this repo; tests use stub producers in temp roots).

Not in v1 (say so in the module docstring): no backup/restore of last-good outputs (a torn source waits for its
next success); no per-source coverage thresholds beyond the zero floor (ratios are recorded so thresholds can be
set from data later); the daily congress pipeline stays a separate orchestrator; press-walk internals, the AI
degrade and the Excel dependency are separate changes; no scheduled-task changes.

## 1. Files

- `fec/refresh_table.py` - the step table, PURE DATA (no imports beyond stdlib typing/dataclasses, no I/O).
- `fec/refresh_tick.py` - the runner. Real `main(argv) -> int`; nothing happens at import.
- `fec/refresh_state.py` - state store, manifests, snapshots, atomic writes (may absorb what is reusable from
  the WIP `refresh_orchestrator.py` at commit 352a5e495: `replace_atomic`, ledger ideas, filed-failure retry).
- `fec/tests/infra/test_refresh_tick.py` - the suite in section 8; register it in `fec/tests/run_tests.py`.
- Reuse as is: `fec/bounded_subprocess.py` (`run_bounded`, `kill_tree`), `fec/surfaces/glassbox_emit.py`,
  `fec/audit_failure_gate.py`, `fec/paths.py` roots (verify it is import-safe before importing; if not, resolve
  ROOT the way `weekly_refresh.py` does).

## 2. The table

One row per step, same 49 steps, same order, same names, same argv, same timeouts and same hard/soft as
`fec/weekly_refresh.py` on main (61be75ddc). Fields: `name, argv, timeout_s, kind, hard, evidence, cadence_h,
requires, gate, skip_if`. `argv[0]` stays the string main uses; the runner resolves it the way main does
(basename index over `fec/`, only table producers, a duplicated real producer is fatal before step 1).
Date arguments are tokens, resolved at launch in LOCAL date like main: `('days_ago', 14)`, `('yesterday',)`.

kinds and their semantics:
- `source` (steps 1-18: CREC ... Wikipedia): evidence=True, soft, isolated, filed on failure, retried.
- `press` (19-22: press delta refresh, press intake audit, press engine feed, fold promoted press runs):
  evidence=True; internal order by `requires`; `press intake audit` runs whenever `press delta refresh` was
  attempted this tick (it audits what is on disk).
- `gate` (23-25: collection intake audit, accepted audio intake, collector roster verification): hard; first
  steps of the COMPUTE PHASE.
- `derive` (26-39, 41): soft, short; compute phase.
- `compute` (40 reference layer, 42 FULL PIPELINE + dashboards): hard; 42 keeps main's audit gate semantics
  exactly (tolerate exit 1 only when every failing audit is in `audit_failure_gate.KNOWN_GATED_FAILURES` and the
  tail is the audit_full tail; anything novel is a hard failure). Lift that logic by reading main; do not import main.
- `publish` (43 prepare dashboard deployment): hard; `skip_if` deployment not configured
  (`DASHBOARD_PASSWORD_FILE` unset) = SKIPPED_NOT_CONFIGURED, which is NOT a failure (Paul: "Don't need to do that").
- `diag` (44-49): soft; run only after step 42 succeeded in the same tick.

`cadence_h` = 168 for sources and press. A pin test (T12) extracts main's `step()` calls by AST and asserts the
table's (name, argv-with-tokens-rendered, timeout, hard) sequence equals main's, so the two cannot drift while
both exist.

## 3. State

`data/engine/refresh_state.json` (atomic replace; schema 1):
per step `{state: NEVER|RUNNING|OK|FAILED|SKIPPED, last_ok_utc, last_attempt_utc, attempts_since_ok,
failure:{kind: exit|timeout|killed|interrupted|torn|coverage, exit, detail}, duration_s, generation, manifest_sha,
torn: bool, coverage: OK|SUSPECT}` plus `publication:{last_publish_utc, degraded, inputs:{source: {last_ok_utc,
manifest_sha, age_h}}, stale_sources:[...]}` plus `updated_utc`.

- The state file is the ONLY truth. `data/engine/refresh_tick_status.json` (human/supervisor marker) is RENDERED
  from state by one function; nothing else writes it; its write uses at most 4 attempts and never delays a step
  (N3). It carries `phase, current_step, waited_seconds, last_tick{outcome, ended_utc}, last_publication{...}` as
  SEPARATE blocks, so a BLOCKED or failed tick never erases what the last good tick did (N5). No terminal outcome
  is written while a tick is still running (N4).
- A step found RUNNING at tick start = the previous tick died inside it: mark FAILED kind=interrupted, torn per
  section 4, due now.
- Unreadable state file: rotate to `refresh_state.corrupt-<utc>.json`, log, start fresh (everything due).
- One line per tick appended to `data/engine/refresh_ticks.jsonl`: start, end, budget, steps run, outcome.
  Metrics come from here: days since last clean PUBLISHED, days since last publication of any kind, filed count.
- Log: `data/engine/refresh_tick.log`, UTF-8, append. The legacy `weekly_refresh.log` and
  `weekly_refresh_status.json` are NOT written in v1.

## 4. Step commit protocol and torn detection (answers the Codex critique)

Scan roots = the data roots from `fec/paths.py` (default `data/`), excluding the runner's own files
(state, status, ticks, log, manifests, `*.lock`, temp). Measured on LIVE: 29,631 files, 3.2 GB, stat-walk 11 s.

For every launched step:
1. `pre = snapshot(roots)` -> {relpath: (size, mtime_ns)}; persist `pre` (compact JSON) to
   `data/engine/refresh_manifests/_pre.<step-slug>.json`; write state RUNNING. (The post-snapshot of one step may
   serve as the pre-snapshot of the next.)
2. Launch with `run_bounded` (timeout = min(step timeout, remaining budget), `CREATE_NEW_PROCESS_GROUP`, adopt the
   child for the exit guard, children get `PYTHONUTF8=1`).
3. Success (exit 0, or a tolerated gate result): `post = snapshot`; changed = new or different files; manifest =
   {step, generation+1, finished_utc, files:{rel:{size, sha256, rows}}} where files = this step's previously owned
   files that still exist and were not taken over, plus `changed`; `rows` = line count for .csv/.jsonl/.ndjson and
   top-level length for .json under 50 MB. Files in `changed` leave every other step's manifest (last writer owns).
   Write manifest files first (content-addressed name `<step-slug>.<sha12>.json`), then ONE atomic state write that
   sets OK + manifest_sha + clears torn. The state write is the commit point; a manifest the state does not
   reference is garbage. Old manifests are collected at tick end.
4. Failure, timeout or kill: `post = snapshot`; if `diff(pre, post)` is non-empty the step wrote before dying:
   `torn=True`. If it changed nothing, `torn=False` and its last-good outputs stand.
5. Interrupted (RUNNING at next tick start): diff the persisted `pre` against now; non-empty -> torn=True. Other
   writers may cause a false torn; that only delays a degraded publication and heals on the step's next success.
6. Zero floor (the "plausible zeros" failure): a file that had >= 50 rows in the previous manifest and now has 0
   rows, is empty, or vanished -> the step ends FAILED kind=coverage, coverage=SUSPECT, entry appended to
   `data/engine/refresh_review.json` for Paul. Every other shrink ratio is RECORDED in the manifest and the review
   file as information only and never blocks (we have no per-source data to set thresholds yet).
7. Crash points for the tests: `_crashpoint(name)` calls `os._exit(137)` only when env
   `REFRESH_TICK_CRASH_AT == name`. Points: mid-step is external; `after_step_exit`, `after_manifest_write`,
   `after_state_commit`, `before_compute`, `after_compute_before_publication_record`.

## 5. A tick

1. Open log, status and Glass Box FIRST (before any lock) so a blocked or failed fire is never blind.
2. Single-instance guard (msvcrt lock file `data/engine/.refresh_tick.lock`): a second instance logs, emits one
   event, leaves the first instance's status untouched and exits 75.
3. Writer lease `.pipeline_run.lock` via `fec/pipeline_lock.py`, owner_kind `refresh_tick`. If held by a LIVE
   holder: poll every 60 s up to `--lease-wait-hours` (default 6), status phase WAITING_FOR_LEASE with
   `waited_seconds` updating each poll, one Glass Box event per 15 min. Exhausted -> outcome BLOCKED, exit 75.
   Holder liveness = section 7.
4. Reconcile state (RUNNING -> interrupted; torn checks).
5. COLLECT PHASE: for each source/press row in table order that is DUE (`state != OK` or `now - last_ok_utc >=
   cadence_h`, and `now - last_attempt_utc >= 1 h` unless `--force-due`), and whose `requires` are OK this tick
   or fresh: run it. A failure is FILED and the loop continues. When the pass is complete, RETRY PASS: every
   filed step again in order, up to 2 retries each, then dependents of a step that recovered. Nothing in this
   phase can stop another step.
6. COMPUTE PHASE runs iff ELIGIBLE and (any evidence step got a new OK since `last_publish_utc`, or the last
   compute failed, or `--force-compute`). ELIGIBLE = every evidence row has `last_ok_utc`, `torn == False`,
   `coverage == OK` and `age <= WINDOW_DAYS` (constant 14, the project's own existing vintage number). Inside the
   phase the hard rows keep main's meaning: a hard failure stops the phase (not the tick); it is retried next tick.
7. Publication record: after step 42 OK (43 OK or SKIPPED_NOT_CONFIGURED): write `publication` into state with the
   exact inputs (each evidence source's last_ok_utc, manifest_sha, age) and `degraded = any evidence source not
   refreshed OK in this cadence window`.
8. Budget: `--budget-hours` (default 18). No step is launched after the budget is spent; a running step's timeout
   is capped to what remains (never below 60 s).
9. Outcomes and exit codes: PUBLISHED 0; PUBLISHED_DEGRADED 0 (stale sources listed); NOTHING_DUE 0;
   COLLECTED_NOT_PUBLISHED 1 (blockers listed: which source, why: never OK, torn, SUSPECT, older than window,
   budget); COMPUTE_FAILED 1 (the failing hard step named; N1 and N2: an unpublished tick never exits 0 and a
   failure after the chain is never reported as success); BLOCKED 75; FATAL_PRESTEP 1.
10. Exit guard: atexit + native console control handler kill the live child TREE before either lock is released;
    CTRL_BREAK ends the tick inside 2 s with the step recorded FAILED kind=killed.
11. Glass Box: tick start/end, step start/end/failure, lease waiting, blocked, review-list additions. Source name
    `moneyball-refresh-tick`.

CLI: `--budget-hours`, `--lease-wait-hours`, `--only NAME` (repeatable), `--skip-compute`, `--force-due NAME|all`,
`--force-compute`, `--dry-run` (no locks, no writes, no launches: prints what is due and why, and the eligibility
verdict with blockers), `--status` (render state; no locks, no writes).

## 6. Things the builder must REPORT, not decide

- What `fec/collect/collector_supervisor.py` does around its outcome check (about :477) when the weekly's
  outcome is not COMPLETE / COMPLETE_WITH_KNOWN_GATED_FAILURES: exactly what it relaunches, how often, and which
  status file and fields it reads. Cutover needs this; v1 does not write the legacy status.
- What `fec/audit_collection.py --scope all` actually refuses (its gate logic), in ten lines.
- Whether `fec/paths.py` is import-safe and which roots hold collector outputs (is everything under `data/`?).

## 7. Shared-module changes (keep them minimal and backward compatible)

`fec/pipeline_lock.py`: the lock body gains `proc_start` = the holder's OS process creation time taken from
`process_liveness.process_start_time(os.getpid())` at acquisition. A holder is LIVE iff its pid is alive AND
(`proc_start` absent -> today's rule on main, unchanged) or (live process creation time equals the recorded
`proc_start` within 2 s). Both values come from the same kernel record, so no wall-clock step can make a live
holder look stale (Critic F4: the WIP compared process start against wall-clock `started_utc` with a 5 s skew).
Every existing reader must keep working with the extra key: check each reader of the lock body and say so.
`fec/process_liveness.py`: add `process_start_time(pid)` (from the WIP). Nothing else in shared modules.

## 8. Tests = sign-off evidence (stub producers, temp roots, never LIVE)

T1 all OK -> PUBLISHED, exit 0, manifests exist and verify, publication record lists every evidence source.
T2 a source fails once, recovers in the retry pass. T3 a source always fails: last_ok 8 d ago and intact ->
PUBLISHED_DEGRADED naming it; last_ok 15 d ago -> COLLECTED_NOT_PUBLISHED, exit 1, previous artifact bytes
untouched. T4 torn: a source modifies an output then dies -> not eligible; next tick it succeeds -> publishes.
T5 crash at every crashpoint plus an external kill mid-step: the following tick converges to PUBLISHED, no step
is OK without a verifying manifest, and the final output bytes equal an uninterrupted control run. T6 exit codes
N1/N2. T7 unwritable status marker: whole-tick overhead under 2 s and the outcome is still in state. T8 no
terminal outcome visible mid-tick. T9 BLOCKED leaves last_publication and last good tick intact. T10 lock
identity: recycled pid detected; a backward clock step of 1 h cannot reclaim a live holder (negative control: the
WIP rule DOES reclaim it in the same scenario); second acquirer refused while the first lives. T11 budget.
T12 table pin against main by AST. T13 corrupt state rotated. T14 `--dry-run` and `--status` take no lock and
change no byte (tree hash before == after). T15 zero floor -> SUSPECT blocks + review entry; a 40 % shrink is
recorded and does not block. T16 hard gate failure stops the compute phase only; diagnostics do not run.
T17 one failing source never prevents any other source from running (assert every other source launched).
T18 lease wait: status `waited_seconds` increases while waiting; acquires when the holder exits (scaled timings
via constructor arguments, not by editing constants).
Then the kernel: `python fec/tests/run_tests.py` from a byte-exact export of the branch (a worktree run gives 35
false failures; baseline on main is 246 passed / 2 failed: test_bill_collision_guards,
test_make_staffer_network_html).

## 8a. AMENDMENT 1 (2026-09-19 20:20, after the press investigation; facts verified by the coordinator)

Measured: the press walk's exit 3 means "ran to the end, some URLs deferred" (09-13: 3 h 13 m, status PARTIAL,
2,200 deferred URLs in 9 members, never attempted because the 600 s per-member budget ran out). Retrying it
inside the same tick would burn three 3-hour walks for nothing, and the daily lane already treats rc 3 as PARTIAL
(`fec/collect/daily_media_refresh.py:410-417`). So:

- Table rows gain `partial_codes: tuple = ()`. `press delta refresh` gets `(3,)`.
- A step that exits with a partial code ends in state `PARTIAL`: it is committed exactly like OK (manifest,
  `last_ok_utc`, generation), satisfies `requires`, counts as fresh for cadence and eligibility, and is NOT
  retried in the retry pass. It is listed under `partial_steps` in the tick line, the status marker and the Glass
  Box event (status `partial`). Whether the deferred work is acceptable is decided by the downstream press gates
  (intake audit and feed validation), not by the runner.
- Table rows gain `tick_only: bool = False` for steps that exist only in the tick runner. The T12 pin compares
  the rows with `tick_only == False` against main. One tick-only row is coming from the press build:
  `'press zero-row review'`, argv `['collect/press_zero_row_review.py']`, timeout 600, kind `press`,
  evidence=False, soft, requires `('fold promoted press runs',)` attempted-or-OK, placed right after the fold.
  Add the row now; the producer file is being written by the press build in the same worktree. The runner's
  producer index must treat a table producer that does not exist on disk as a FILED failure of that one step,
  never a fatal pre-step error (test it).
- Add T19: a step exiting with its partial code is committed, satisfies `requires`, is not retried, and shows
  up as partial everywhere; the same exit code on a row WITHOUT that partial code is a plain failure.

## 8b. AMENDMENT 2 (2026-09-20, after the coordinator's inline review and the independent sandbox pass)

Decisions taken after the build, each answering a measured finding. They supersede the text above
where they differ.

- SCAN ROOTS (supersedes section 4's "data roots ... default `data/`"): `data/` and `outputs/`
  recursively; the project ROOT's own files, data-shaped ones only (`.db .sqlite .jsonl .ndjson .json
  .csv .parquet .xlsx .xlsm .html`); one named external file, the press URL baseline
  (`paths.DRAFT/all_press_release_index.csv`, keyed `ext:<abspath>`), restated in the runner and
  pinned against `press_baseline_fold.DEFAULT_BASELINE` by a test because the runner imports no
  producer. Ignored everywhere: `~$` Office lock files and SQLite `-wal`/`-shm`/`-journal` siblings.
  Reason: a human saving a note, or Excel or SQLite touching a sidecar, while a collector happens to
  be failing must never mark that collector TORN (a torn evidence step blocks all publication).
- ZERO FLOOR (supersedes section 4 item 6's "previous manifest"): the baseline is what the step
  ITSELF last produced. Each manifest carries `produced` {file: rows} for the tables (>= 50 rows) the
  step wrote, carried forward across runs and across a later step taking the file over; it is
  consulted only for files the current run rewrote. A `.csv` with at most one line (the header) is a
  collapse, not one row. Reason: "last writer owns" removed a shared file from the earlier step's
  manifest, so a 60 -> 0 collapse on a file two steps write was invisible and was published.
- `--accept-zero NAME`: the owner accepts that step's next zero-floor verdict; the step runs now, the
  collapse is recorded as a non-blocking review row, and the baseline resets. Without it a source
  that has truly gone quiet would block publication until someone edited state by hand.
- NEW EVIDENCE IS CLOCK-FREE (supersedes section 5 item 6's "new OK since `last_publish_utc`"):
  evidence that succeeded in this tick always counts; across ticks each source's `generation` is
  compared with the generation the publication record stored for it. Reason: after a backward
  clock step, fresh evidence carried an older stamp than the last publication and every later tick
  exited 0 NOTHING_DUE over data nobody had computed.
- LEASE: an inherited lease claim in the environment that does not validate is FATAL_PRESTEP at
  once; it is never polled. Reason: it can never become valid, and polling it held the
  single-instance lock for the whole six-hour wait on a lease nobody held.
- MANIFEST READS: a manifest that cannot be OPENED is retried and, if still locked, does not demote
  the step (its baseline is unknown for that tick); a missing or unparseable manifest demotes the
  step and makes it due at once, bypassing the one-hour attempt gap.
- ONE STEP'S SHARE: no step's timeout may exceed half the tick budget, whatever the table says (the
  press walk's table timeout is 36 h against an 18 h tick); a filed step whose failure was a TIMEOUT
  is retried in the same tick only when the remaining budget is at least twice what it just burned.
- The review file is capped at 2,000 rows; the oldest information-only rows go first.
- Left as built, on purpose: `*.log` files are never watched (logs are not evidence); a console kill
  leaves the marker showing the phase it died in with a dead pid (`--status` renders the truth).

## 9. House rules for the code

Match the surrounding code's idiom and comment density. Never `subprocess.run(capture_output=True, timeout=)` or
`communicate(timeout=)`: `run_bounded` only. Split text on `b'\n'` only, never `str.splitlines`. UTC timestamps
via `datetime.now(timezone.utc)` (N6). Every file write atomic (temp in the same directory, then `os.replace`).
No new dependencies. Commit on the branch only; never touch LIVE; never amend; commit message via `-F` file with
the trailer `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
