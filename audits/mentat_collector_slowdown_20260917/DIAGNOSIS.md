# Mentat collector: "every lane failing, workers drop to zero" — diagnosis and fix (2026-09-17/18)

Reported symptom, verbatim: *"there has been a massive slow down in data collection since the bug
fixes, and every lane is failing now. I think the workers, when they checkpoint, halt the entire
collection and kill the process. Many times it suddenly drops down to 0 workers."*

This packet lives in the Mentat repo because the lane's worktree
(`.claude/worktrees/mentat-collector-slowdown-dfbf5b`) was removed by the 2026-09-18 disk clearance.
That clearance rehomed all six files here before deleting the worktree, so nothing was lost. An
earlier revision of this paragraph said the copy had been destroyed; that was wrong, and wrong in a
way worth recording — it came from reading a directory listing truncated by a `tail`, which is the
same error of inferring absence from an incomplete view that this packet warns about elsewhere. The
patch files beside this one are that rehomed set; the commits below are the durable record.

## Verdict

**The checkpoints were innocent.** Per-page checkpoints and progress rows are written to each lane's
own `lanes/lane-NN/mentat.db`. The `FEC API pause flush: stored N fetched work unit(s)` line that
looked like a checkpoint halting the run is the `on_abort` handler in `fec_api.R`, which runs *after*
a task has already failed, precisely so fetched-but-unstored work is not lost. Nothing in the fanout
or the orchestrator kills a process; the only hard kill in the system is the console's Stop route,
which runs `taskkill /T /F`, and both 2026-09-17 morning runs ended that way (`control.json` with
`stop: true` at 10:40:16 and 11:30:58 local). The "workers" tile reads the shared request pool's
count of HTTP requests in flight at that instant, so it shows 0 whenever every lane happens to be
parsing or writing rather than waiting on the network. It is a display artifact, not a worker count.

**The real cause was one truncated API key.** Stored key `13ffe51ce05b` in the DPAPI key store
(`%LOCALAPPDATA%\Mentat\credentials\fec-keys.dpapi`) is 39 characters long; every other key is 40.
A one-request probe of all 22 keys returned HTTP 200 for the other 21 and
`{"error":{"code":"API_KEY_INVALID"}}` for that one. Every archived 403 body in every lane database
of the 09-15 and 09-17 runs carries that same code.

**The shared request pool turned one bad key into a total outage.** The pool rotates keys
least-recently-used with no health tracking (it cooled down only on HTTP 429), so roughly one request
in twenty-two drew the bad key in *every* lane: 44 of 899 requests on 09-15, 9 of 296 on 09-17. R
treats 403 as non-retryable, so the first one aborted the whole company-cycle task. Before the pool
existed, each lane held one pinned key and a bad key could only ever kill its own lane, which is why
the 09-10 Banking run scored 30 of 30 and merged.

**Nothing reached the database because merge is all-or-nothing by design.** The fanout merges lane
snapshots into the industry database only when zero tasks failed. On 09-15, 19 of 30 tasks succeeded
and the merge was skipped, leaving the source hash unchanged. No `merge.log` existed in any console
run on disk. So the operator saw both symptoms at once: every lane reporting failures, and no data
arriving no matter how long it ran.

**On throughput.** The pool's HTTP width was taken from a RAM-derived lane cap of 4 to 8 rather than
from the key supply of 22, while ten lanes posted synchronous 22-request batches through it.
Requests per minute measured 22 on 09-10 under the old code, 52 on 09-15 and 24 on 09-17. Per-page
FEC latency on long cursor walks is inherently around 12 seconds. The collapse was in rows *merged*,
which was zero, not in the request rate. Measured per-key limit: about 60 requests per minute
sliding, with no 429 in 70 requests over 52 seconds.

## What was changed, and why

Paul's rulings, verbatim: resume across runs **yes**; *"It should always be complete, no
misrepresentation"*; *"Reconcile the mismatch, API count can change, it should always be verified"*.
All commits are on `codex/mentat-crypto`.

**`494dc133c` — the pool quarantines a bad key instead of poisoning every lane.** A 403 whose body
carries an `API_KEY_*` code retires that key for the run and the same request is re-issued on a
healthy key, so R never sees the 403; if every key is quarantined the run fails loudly with
`API_KEY_POOL_EXHAUSTED`. A key reporting `x-ratelimit-remaining: 0` cools down. The pool's width now
follows the key supply (`--pool-width`, zero meaning every healthy key) and the console's worker dial
moves the R database coordinators only. This commit also lands the whole worker-scaling lane, which
had to travel together: `api_request_pool.py` had never been committed even though a tracked file
imported it, and the committed launchers were already passing `--initial-workers` and
`--merge-batch-limit` that the committed fanout rejected.
Evidence: 9 of 9 pool tests with a mutation check and a quarantine-off negative control; a real-FEC
control firing 66 requests through the 21 good keys plus the truncated one returned 66 × HTTP 200
with exactly one key quarantined and one request re-issued.

**`f0ec60b74` — a moving population is reconciled, not aborted.** FEC's `pagination.count` legitimately
moves mid-crawl as filings and amendments post. A moved count, a shortfall or an overrun now resets
that unit's walk (clearing its checkpoints and progress row) and re-walks until one whole pass
observes a constant count equal to the rows it collected, bounded by `MENTAT_RECONCILE_PASSES`
(default 3), after which the task fails loudly with nothing unverified stored. Date-window units are
verified against a *fresh* parent count fetched after the windows complete, and only the windows whose
own count moved are re-walked. Saved work that no longer matches the current query contract is
discarded per unit and re-collected rather than failing the lane.
The same commit fixes a structural false positive: the determinism spot-check compared a split unit's
first page against a fresh page 1, but a split unit's first page is the synthetic union of all 26
windows, so it could never match. Three of the five task failures in the 12:41 run were this. The
check is now union-aware, and a genuine post-walk change is recorded as an advisory
`determinism: FALSE` with detail in the receipt rather than failing a task, because the walk-time
verification is the guarantee.

**`dba77f87f` — an estimated count is verified, not refused.** openFEC answers a large query with
`is_count_exact: false` and an estimated count, which was a hard task failure. An estimate is not a
verdict on the data, it is a refusal to count. A splittable unit whose count comes back estimated is
now decomposed into its exhaustive date windows; when the parent's own count is estimated too, the
union is verified against the sum of the windows' own exact counts and the reconcile log records
which mode proved it. A window that will not produce an exact count, or a unit that cannot be split
at all, still fails loudly with nothing stored.
For the record: a window-count sum is weaker evidence than an independent parent count, because the
windows are self-reporting. It is the best available when the API refuses to count, and the receipt
says which was used rather than claiming more than was proved. Cost: an estimated count now spends
28 requests instead of one failure, or 54 when the parent never counts exactly.

**`bd8c65ebb` — Resume last run.** `POST /api/resume` relaunches the orchestrator with
`-ResumeRunId` on the most recent run of a stopped or failed roster that has fanout manifests, after
re-staging the runtime (so a code fix since the stopped attempt is the code the resume runs),
clearing every stop flag in the run-level and fanout control files, and dropping the stale stop and
exit fields from `upload.json`. Guards match `/api/start`. Merge semantics are untouched. The
orchestrator gained `Resolve-ManagedLogBase` so a resumed attempt writes its own stage logs beside
the stopped attempt's instead of refusing to start.
Evidence: a real-FEC end-to-end on a scratch console — start, stop after the first task began,
resume — produced `run_resumed` and `industry_resuming` under the same run id, a receipt reading
`succeeded 1/1, merged true`, and 158 contributions in the industry database.

**`2a5f05761` — a run whose process is gone reports stopped.** `finish()` records an exit only for a
process the current console holds a handle for, so a run whose console was killed stayed "starting"
forever. That is a misrepresentation, and because `resume_target()` accepts only a terminal state it
also locked the run out of Resume — the exact run Resume exists for. A run is now reported stopped
when its death is positively established: no live handle here, not being prepared here, and either
its recorded process is gone (verified through the same open-handle identity comparison the stop path
uses, so a recycled pid cannot look alive) or, when no pid was ever written, its status file has been
silent past a 15-minute grace. The state is computed on the read path, never written back.
Evidence: verified against the live console. The stuck 12:41 run went from `starting / resumable
false` to `stopped / resumable true`, while every completed and never-started roster was unchanged
and no `upload.json` was rewritten.

## Decisions taken without a ruling

Four questions were put to Paul and answered by the lane when he said to proceed optimally.

**Estimated counts**: verify by date windows rather than fail, as above, because failing contradicts
"always complete" and accepting contradicts "always verified".
**Auto-resume when Start is pressed**: no. Start is already refused for a roster that is not `ready`,
so a stopped roster offers Resume and only Resume. Continuing stale lane data under a button labelled
Start would be the misrepresentation the ruling forbids.
**Reconciliation pass cap**: keep 3. A 197,000-row unit costs roughly 2,000 requests per pass, about
1.6 minutes of the 21-key pool's capacity. Already tunable by environment variable.
**Post-walk drift**: advisory in the receipt, confirmed as built.

## State of the runs on disk

| Run | Outcome |
|---|---|
| 09-10 Banking | 30 of 30, merged, 907,944 rows. Pre-pool code, one key per lane. |
| 09-15 Credit Unions | 19 of 30, 11 × HTTP 403, merge skipped, nothing written. |
| 09-17 10:28 Credit Unions | 0 of 30 at 12 minutes, stopped from the UI. |
| 09-17 12:41 Credit Unions | 27 of 30, 5 task failures, killed at about 15:56 without a terminal state. |

The 12:41 run is the one to resume. Its five failures were three determinism false positives, one
"a date window was replaced by unproven narrower spellings", and one saved-contract mismatch on a
recovery attempt — all three classes are reconciled rather than fatal under the commits above.

## Known issues found but not fixed

- **Console startup can hang.** `git_sha()` runs `git rev-parse --short HEAD` on the request path.
  This checkout is a linked worktree whose git metadata lives under OneDrive, so the child can wedge;
  the 10-second timeout fires but the child cannot be killed and `communicate()` blocks forever, so
  `/api/session` never answers and the console never finishes booting. Two orphaned `git.exe`
  processes were observed stuck on exactly that command for about an hour while a page's fetch stayed
  pending. `lru_cache` does not serialise callers, so one page load raced two request threads into
  it. A fix needs to bound the subprocess and guard concurrent callers.
- **Single-cycle runs cannot build a workbook.** The runtime stages only the requested cycle's
  committee master, but the generator wants `cm22` regardless.
- **Long runtime paths break imports.** A staged runtime path beyond roughly 275 characters makes
  CPython drop `sys.path[0]`, and the roster validator then cannot import its sibling module.
- **The elapsed clock keeps running on a demoted run**, because `snapshot()` computes elapsed from
  `started_at` whenever `finished_at` is absent, and recording it would require a write from a read
  path.

## Brain drafts for Paul to apply

**STATE.md**: "MENTAT COLLECTOR (2026-09-17/18): every task failure since about 09-09 was HTTP 403
API_KEY_INVALID from one truncated key in the DPAPI store, amplified by the shared request pool's key
rotation and made total by the zero-failure merge gate; checkpoints were never involved. Key
disabled; pool quarantines invalid keys and re-issues; pool width follows the key supply; a moving or
estimated FEC count is reconciled and verified instead of aborting the task; a stopped or failed run
can be resumed and a run whose process is gone now reports stopped. Commits 494dc133c, f0ec60b74,
bd8c65ebb, dba77f87f, 2a5f05761. The 09-17 12:41 Credit Unions run stands at 27 of 30 and is
resumable from the console."

**DEADENDS.md DE-026**: "Reading the collector's failures as a checkpoint fault. Approach: treat the
'FEC API pause flush' line and the worker tile falling to zero as checkpoints halting the run.
Failure mode: the flush is the abort handler running after the failure, checkpoints are per-unit in
each lane's own database, the tile counts in-flight HTTP requests, and the run terminations were
console Stop calls. Root cause: one truncated API key, no key health in the shared pool, and an
all-or-nothing merge. Would reconsider if: 403 rows persist in lane databases after the key is
disabled and the quarantine is in place."

**DECISIONS.md D-040** (built and committed, awaiting ratification): "A pool key that answers with an
API_KEY_* 403 is quarantined for the run and its request re-issued on another key, so R never sees
the 403; pool HTTP width follows the healthy key count, never the RAM lane cap. A moving or estimated
population is reconciled and re-verified rather than aborted, and nothing unverified is ever stored.
Reversal condition: quarantine empties the pool, in which case the run fails loudly with
API_KEY_POOL_EXHAUSTED."

**Correction to standing memory**: `Desktop\API Keys\keys.json` is not Mentat's key store. Mentat
reads the DPAPI store, which held 22 keys, 15 of which are not in that file.
