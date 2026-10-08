# Refresh tick completion — 2026-09-20

Completed the handoff's section 9 and fast-forwarded live main from `203a69812893e09c718a5bcafeaab8e9c686fc4d`
to `a7a11b5df1c123568a0672138bb1318d858be9a0`, then landed the final restart-race fix at `1d6b3793a1f496ff07f4b460010c882969dd63eb`.
The local Git mirror matched both landings. The original
Claude worktree was left undisturbed; completion used `codex/finish-refresh-tick-20260920`.

## Changes

- Finished the shared-output zero floor, generation-based publication after clock changes,
  immediate stale-lease rejection, manifest read retry, step budget/retry limits,
  producer-import isolation, review-list cap, and recorded `--accept-zero` support.
- Independent probes found three further unsafe publications: externally damaged input,
  a shared-file zero verdict cleared by a successful no-op, and a zero-row baseline lost
  behind an unreadable manifest. Fixed these and retained known damaged files across
  failures and console interruption. A timestamp-only touch with identical bytes is harmless.
- Closed a final tree-kill race: if a parent files its child's exit failure before dying,
  the next tick retries immediately. A durable flag is cleared atomically at normal tick end;
  normal failed ticks retain their cooldown. The regression failed before and passed after.
- Preserved sealed-run press tombstones, review lists, missing-promoted-run handling, and
  the process-identity writer lease. Integrated current main's daily-refresh clock repair.
- Kept the two opt-ins held with `3a1f2586b`: press baseline folding defaults OFF, and R
  maintenance retry behavior matches prior main. The dependent R gate test was reverted too.

## Verification

- Full private-snapshot refresh suite: **61 passed** in 407.692 seconds.
- Added console-interruption regression on the landing branch: **1 passed**.
- Affected press, process-liveness and daily-refresh suites: **158 passed**.
- Replayed the original sandbox's shared-file collapse and repeated hung-step scenarios.
  A timed-out walk left later press steps able to run; its zero collapse blocked publication.
  `sandbox_batch_g.txt` prints `FAIL` for its old bug predicate ("nothing after it ever runs"):
  that predicate is now false, as required; all four later press steps ran.
- Replayed backward-clock collection across ticks, stale inherited leases, and a real Windows
  exclusive manifest-file lock. New evidence published; the stale lease failed in **0.23 s**;
  the lock preserved durable success and blocked publication until released.
- **LIVE kernel at `a7a11b5df1c123568a0672138bb1318d858be9a0`: 250 passed / 2 failed (the two pre-existing baseline failures)**, 1177.0 seconds.
  The independent pre-landing live kernel completed with 247 passed / 2 failed;
  the same two failures remain after this landing.
  The failures are:
  - FAIL  test_bill_collision_guards suite clean  :: FileNotFoundError: [Errno 2] No such file or directory: 'C:\\Users\\pgoff\\OneDrive\\Desktop\\Melange Systems\\backups\\bill_directions.PRE-LEGFIX3.csv'
  - FAIL  test_make_staffer_network_html suite clean  :: unrecognised verdict
- The final follow-up `1d6b3793a1f496ff07f4b460010c882969dd63eb` changes only the refresh runner and its test suite:
  **64 refresh tests passed** on that branch, followed by **4 focused tests passed in LIVE**
  after landing, covering damaged outputs, console interruption, failure-commit interruption,
  and normal-failure cooldown. The broad kernel result above precedes this two-file follow-up.

No test or audit floor was weakened. The locked-manifest regression was strengthened to
require a non-publication outcome while preserving the existing success record. The full
kernel log and any failure dumps emitted by its runner are retained beside this receipt.

The installed runner's read-only `--dry-run` and `--status` commands also succeeded. Its
new state has 23 of 23 collection steps due and no prior tick publication, as expected
before the first operational run; neither command launched a collector.

## Operational status

`MoneyballWeeklyRefresh` still invokes `fec/weekly_refresh.py`; its schedule and action were
not changed. Switching to `fec/refresh_tick.py` remains the explicit owner decision listed in
the handoff. No real refresh or ranking publication was launched during completion.

The existing press coverage, intake, audit, and reference-layer blockers remain prerequisites
for a successful production publication. This code landing does not claim those separate
data and workflow issues are resolved. Paid AI work, machine settings, and deletion of the
93 GB scratch exports were not part of the handoff's section-9 landing sequence.

The Project Brain update is drafted in `PROJECT_BRAIN_DRAFT_20260920.md` for Paul to apply
under the repository's boot contract. The original dated progress note and critique remain
unchanged. Evidence is in `completion_evidence/`; the landing Glass Box event is
`evt-20260920T0443233133233Z-7dee29fc8a`. A final verification event records the live-kernel result.

Verification event: `evt-20260920T0505461828852Z-2f49e6efa3`.
