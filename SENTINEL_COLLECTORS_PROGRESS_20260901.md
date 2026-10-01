# Sentinel Collectors Repair — Progress and Next Steps

Date: 2026-09-01 (updated 2026-09-02 by the branch lane)
Status: **Repair tracked on a branch and regression-validated; production recovery rehearsed in staging and reconciled; hearing feed producer built with a provenance chain; production flow remains held. Promotion, fold, pipeline, dashboard publication, and scheduler re-enable are Paul's gate.**

Branch: `claude/sentinel-collectors-progress-f7de7d` (worktree `.claude/worktrees/sentinel-collectors-progress-f7de7d`, based on `ade12ee22`).

Commits on the branch:

| Commit | Content |
|---|---|
| `7e1cb0e66` | The 2026-09-01 repair (8 modified + 8 newly tracked modules), byte-identical to the live tree's copies except that the desk and bundle builders carry only the hearing-contract hunks. |
| `dbdac0ca1` | `audit_collection.py`: a partial press run directory yields a REJECTED receipt with named reasons (exit 2) instead of an uncaught `FileNotFoundError` (exit 1). |
| `8d21605bc` | Hearing display feed producer plus corpus provenance chain (section D). |
| this commit | This document and the staging evidence under `audits/sentinel_collectors_20260901/`. |

## Safety hold

- `MoneyballCollectorSupervisor`: **Disabled** (last run 2026-09-01 13:56, result 267014).
- `MoneyballWeeklyRefresh`: **Disabled** (last run 2026-08-30 09:39, result 75).
- User-level `PRESS_BASELINE_FOLD`: **0**.
- `DASHBOARD_PASSWORD_FILE`: **not set** in any scope.
- No collector, refresh, fold, feed build, or publication process was running at any check during this pass.
- Nothing under the live tree's `outputs/`, `data/stance`, `data/press`, `data/engine` changed during this pass (8,109-entry before/after snapshot, 0 added / 0 removed / 0 changed). `Draft Systems/all_press_release_index.csv` untouched (257,224 lines, mtime 2026-09-01 06:57 UTC).

The hold stays in place until the gates in the "Remaining work" section pass in the live tree.

## Important facts learned this pass

1. **The repair lived only as uncommitted edits in the live tree.** The live tree is also being edited concurrently by at least one other lane (member narratives v2, speech profile, staffer network, bill withdrawals). Their hunks sit in the same working copies of `make_member_desk.py` and `build_dashboard_bundle.py`. The branch commit carries only the hearing-contract hunks of those two files; the other lanes' edits stay in the live tree and are not this lane's to commit.
2. **The live press feed receipt is rejected by the repaired consumer.** `fec/press_stream.py` now requires `promotion_mode == CUMULATIVE_ACCEPTED_RUN_LEDGER` and a non-empty `accepted_runs`. The active receipt (`data/stance/press_refresh_feed_receipt.json`, single run `press_refresh_20260828`) has neither. Once the repair is merged, no engine consumer can read the press feed until the cumulative candidate is promoted (step 2 below).
3. **`press_refresh_20260829` is a partial run** (discovery files only, no retry receipt, no scored/host/mention CSVs). It is not a valid run and must never be promoted or folded. It exposed the crash fixed in `dbdac0ca1`.
4. **The hearing corpus was never rebuilt after the chamber-scope fix.** `fec/collect/fetch_hearings_seq.py` resolves surnames within the package's chamber since 2026-08-18, but `hearings_seq.db` (7,174 packages, dates to 2026-09-30) was built 2026-07-11 with the senate-first guess (9.7% cross-chamber misattribution measured). The collector is incremental and skips packages already in `seq_log`, so an ordinary run does not correct anything. Nothing recorded which resolver built the corpus. The branch adds that provenance (section D).
5. **`fec/paths.py` differs between the live tree and the branch** (the live tree has an uncommitted STAFFER_NETWORK block from another lane). Inert for every press module; noted so the merge is not a surprise.

## Progress this pass

### A. Neutral regression validation — complete

Measured in the worktree (worktree figures are not live-tree gate figures; kernel and `audit_full` still need their live-tree measurement after merge).

| Gate | Result |
|---|---|
| `fec/tests/infra/test_collection_stream_wiring.py` | 73 passed, 1 skipped (skip = `collector_targets.json` absent in the checkout) |
| `fec/tests/collect/test_press_baseline_fold.py` | 21 passed |
| `fec/tests/members/test_hearing_display_feed.py` (new) | 18 passed; 91 passed / 1 skipped together with the wiring file |
| `python -m py_compile` on every touched `.py` | pass |
| `git diff --check` | clean |
| `refresh_press_delta.R` parse | not verifiable here (no `Rscript` on PATH); the file is byte-identical to the live tree's copy |

Negative controls, each asserted as a positive rejection (named reason, raise, or `None`), not merely "no exception":

| Control | Test |
|---|---|
| malformed timestamp rejected with a named reason | `test_shared_receipt_timestamp_contract_accepts_iso_and_legacy_r_shape` (`TIMESTAMP_UNPARSABLE`) |
| changed source hash rejected | `test_accepted_receipt_archive_is_immutable_and_binding_checked` (`binding changed`) |
| unaccepted dated run cannot enter the feed | `test_publishers_reject_negative_collection_receipts` |
| unpromoted run cannot fold | `test_fold_consumes_only_hash_bound_promoted_runs` |
| stale or changed hearing artifact omitted | `test_hearing_display_requires_current_hash_bound_corrected_attribution` (changed bytes) and the new `test_hearing_display_omits_expired_or_incomplete_coverage_artifact` (expired, partial coverage, v1 contract) |
| deployment receipt contains no password material | `test_dashboard_publication_is_password_safe_and_lineage_bound` |
| partial run directory rejected, nothing archived | new `test_press_only_audit_rejects_partial_run_dir_with_named_reason` |

Wiring collection needed `data/engine/congestion.json`, which is gitignored; it was copied into the worktree as read-only input and is not committed.

### B. Repair files tracked — complete on the branch

The four live-but-untracked modules (`fec/audit_collection.py`, `fec/press_stream.py`, `fec/pipeline_lock.py`, `fec/members/b5_audio_manifest_adapter.py`) and the four new repair modules are tracked in `7e1cb0e66`. No unrelated lane work, generated output, collector checkpoint, or `.json` was staged (verified by an independent pass: 16 paths exactly, 12 of them byte-identical to the live copies at commit time, desk/bundle diffs contain only hearing hunks).

### C. Controlled production recovery — rehearsed in staging, not applied

Staging root: a scratch tree with junctions onto the live run directories (read-through), `MONEYBALL_ROOT` and `MONEYBALL_DRAFT` pointed at the scratch tree so every default path resolved into staging.

Press-only audit per run:

| Run | Result | receipts / articles / mentions / failed bodies |
|---|---|---|
| `press_refresh_20260828` | ACCEPTED | 27,434 / 27,234 / 19,561 / 200 |
| `press_refresh_20260829` | REJECTED after `dbdac0ca1` (before: uncaught crash) | partial directory |
| `press_refresh_20260830` | ACCEPTED | 32,434 / 29,208 / 20,858 / 3,226 |
| `press_refresh_20260831` | ACCEPTED | 29,338 / 29,134 / 20,851 / 204 |
| `press_refresh_20260901` | ACCEPTED | 3,658 / 3,456 / 2,317 / 202 |

The 20260828 receipt's source and retry hashes equal those in the live feed receipt, so the staged binding is the one that produced production.

Cumulative candidate feed (built from the staged accepted-run ledger, order 0828 → 0830 → 0831 → 0901, earliest accepted run wins exact collisions):

| Stream | per run (0828 / 0830 / 0831 / 0901) | dedup union | candidate | active | active − candidate | candidate − active |
|---|---|---|---|---|---|---|
| tone | 255 / 280 / 281 / 100 | 294 | 294 | 255 | 0 | 39 |
| fulltext | 255 / 280 / 281 / 100 | 294 | 294 | 255 | 0 | 39 |
| official mentions | 19,561 / 20,858 / 20,851 / 2,317 | 22,243 | 22,243 | 19,561 | 0 | 2,682 |

Every previously accepted row is preserved byte-for-byte (255 / 255 / 19,561 shared-key payloads identical). The candidate has no duplicate keys. An independent recount from the builder's key definitions confirmed all of the above. Staged output hashes: tone `cd8e935d…`, fulltext `4d13b1a2…`, mentions `ca7a203e…`; the receipt's `outputs_sha256` matches the files, and `promotion_mode` is `CUMULATIVE_ACCEPTED_RUN_LEDGER`. The staged receipt passes `press_stream.validate_refresh_receipt`; the live receipt fails it.

The production sequence (one rolling intake receipt, archive growing 1 → 4) was rehearsed separately and produced byte-identical outputs, so the build is deterministic given the same four accepted runs.

Rehearsal details and the recount are in `audits/sentinel_collectors_20260901/`.

Not done on purpose: no accepted receipt was archived into the live tree, no candidate was promoted, nothing folded, nothing published.

### D. Hearing correction — producer and provenance chain built; production feed not built

On the branch (`8d21605bc`):

- `fec/collect/fetch_hearings_seq.py` gains `--db <path>` and `--rebuild` (refuses an existing path; never drops or truncates a database) and writes `<db>.receipt.json` (`hearings-seq-receipt-v1`: window, package counts listed/ok/nopage/failed, max date, database sha256, rebuild flag, previous receipt hash). It declares `chamber-scoped-speaker-attribution-v2` only for a fresh rebuild or a run chained to a v2 receipt bound to the pre-run database hash; otherwise `unknown-pre-fix-corpus`. Fetch, parse, and resolve behavior is unchanged (7 deleted lines, all mechanical: an optional DB-path argument and the argv block replaced by `main()` with the same defaults).
- `fec/members/emit_antagonism.py` binds `hearing_antagonism.json` to the corpus by database and receipt sha256 (13 added lines, nothing changed). `hearing_antagonism_build.py` exposes the corpus path as the module constant `SEQDB`, the same `<ROOT>\hearings_seq.db` as before, still opened with `PRAGMA query_only=1`.
- `fec/members/build_hearing_display_feed.py` writes `data/stance/hearing_display_feed.json` and `hearing_display_receipt.json` under the contract the desk and dashboard require, and refuses with named reasons (`SEQ_RECEIPT_MISSING`, `ATTRIBUTION_CONTRACT_NOT_V2`, `SEQ_DB_HASH_MISMATCH`, `COVERAGE_INCOMPLETE`, `ANTAGONISM_UNBOUND`, `ANTAGONISM_MISSING`) any corpus that is pre-fix, hash-mismatched, incomplete, or unbound.
- The fixture in `fec/tests/members/test_hearing_display_feed.py` runs the real resolver against the real roster: `MORAN` resolves to Nathaniel Moran in a House package and Jerry Moran in a Senate package, and the resulting feed passes `hearing_display_contract.load_optional`. Every named reason has a negative test; the receipt chain (rebuild → v2, chained → v2, unbound → pre-fix) is tested.

Until the corpus is rebuilt and the antagonism facet re-validated (step D.3 below), the hearing surface stays omitted. That is the intended fail-closed state.

## Remaining work, in order (Paul's gate at each step)

### 1. Merge the branch into the live tree

The live tree holds uncommitted copies of the same files. Before merging:

1. Commit or set aside the other lanes' in-progress edits in the live tree (their call; `make_member_desk.py`, `build_dashboard_bundle.py`, `fec/paths.py`, `fec/audit/audit_full.py`, the desk template, the narratives and staffer-network files).
2. Remove the eight untracked repair modules from the live working tree (`fec/audit_collection.py`, `fec/press_stream.py`, `fec/pipeline_lock.py`, `fec/members/b5_audio_manifest_adapter.py`, `fec/collect/press_receipt.py`, `fec/collect/fold_promoted_press_runs.py`, `fec/members/hearing_display_contract.py`, `fec/surfaces/publish_dashboard.py`) and restore the tracked repair files to HEAD (`git checkout -- <file>`); the branch carries identical or newer content for every one of them. Move aside the live tree's untracked copy of this document.
3. `git merge claude/sentinel-collectors-progress-f7de7d`. Hearing hunks in the desk and bundle builders are identical on both sides and merge clean.
4. Re-measure the gates in the live tree: `python fec/tests/run_tests.py` and `python fec/audit/audit_full.py`. Expect the two standing pre-existing failures; a `[SYS]` A2b red on a newest-file sentinel under `repo.fec_code` is the DE-011 residual, not a defect of this lane.

### 2. Promote the cumulative press candidate

Both schedulers stay disabled. Run from the live tree root with `PRESS_BASELINE_FOLD` unset or 0. The press intake audit's `--press-delta-root` defaults to the single newest `outputs\press_refresh_*` run (`discover_run()` returns the last valid candidate, `fec/collect/build_press_engine_feed.py:146-162`; `fec/audit_collection.py:41-46`), and `weekly_refresh.py:331` never overrides it, so for the recovery it must be run once per accepted run root, in date order, with an explicit override:

```powershell
python fec\audit_collection.py --scope press --output data\engine\press_collection_intake_receipt.json --press-delta-root outputs\press_refresh_20260828  # fec/weekly_refresh.py:331 (+override)
python fec\audit_collection.py --scope press --output data\engine\press_collection_intake_receipt.json --press-delta-root outputs\press_refresh_20260830  # fec/weekly_refresh.py:331 (+override)
python fec\audit_collection.py --scope press --output data\engine\press_collection_intake_receipt.json --press-delta-root outputs\press_refresh_20260831  # fec/weekly_refresh.py:331 (+override)
python fec\audit_collection.py --scope press --output data\engine\press_collection_intake_receipt.json --press-delta-root outputs\press_refresh_20260901  # fec/weekly_refresh.py:331 (+override)

# press engine feed, once. Without --source-root, main() takes the build_cumulative() branch
# (fec/collect/build_press_engine_feed.py:507-511), which unions the current --intake-receipt with every
# archived data\engine\press_collection_receipts\press_refresh_*.json (_accepted_intake_receipts(), :328-375).
python fec\collect\build_press_engine_feed.py --intake-receipt data\engine\press_collection_intake_receipt.json  # fec/weekly_refresh.py:332
```

Gate: the four archived receipts appear under `data/engine/press_collection_receipts/`; the feed receipt reports `promotion_mode CUMULATIVE_ACCEPTED_RUN_LEDGER` with `accepted_runs` 0828, 0830, 0831, 0901; tone 294 / fulltext 294 / mentions 22,243; output sha256 equal to the staged values above (the build is deterministic for the same accepted runs). Any difference means a run changed on disk and must be explained before continuing.

### 3. Fold

`fold_promoted_press_runs.py` skips a root already folded: `fold_promoted()` loads the `history` of `data/engine/press_baseline_fold_receipt.json` (`press_baseline_fold.py:292-299`, receipt path at `:62`) into `already`, then `if root.name in already: continue` (`fold_promoted_press_runs.py:75-76`) before `fold_run()` is ever called. The live receipt's history already holds `press_refresh_20260828` (`FOLDED`, 2026-09-01T06:57:39 UTC, 7,454 rows added), so once the cumulative candidate is promoted the unmodified script folds only 0830, 0831, and 0901. There is no root-limiting flag (arguments: `--feed-receipt`, `--baseline`, `--fold-receipt`, `--keep-backups`, `--enable`) and none is needed.

Fold only with the gate set for the one process (`$env:PRESS_BASELINE_FOLD='1'` in that shell, not user-level):

```powershell
python fec\collect\fold_promoted_press_runs.py  # fec/weekly_refresh.py:333; under PRESS_BASELINE_FOLD=0 it prints "press baseline fold held" and exits 0
```

Then confirm the fold receipt history lists exactly the accepted roots named in the active ledger and nothing else.

### 4. Full audit and pipeline

`python fec/audit_collection.py --scope all --output data/engine/collection_intake_receipt.json`, then the accepted-audio adaptation and the remaining chain only if every deferred collector and the full audit pass. The chain is an APPLY-class run in the live tree.

### 5. Dashboard

1. Create the password file outside the repository and set `DASHBOARD_PASSWORD_FILE` (user scope) to its path. Nothing in this lane reads or records the password; the receipt carries `password_material_recorded: false`.
2. `python fec/surfaces/publish_dashboard.py` produces `deploy/index.html` and `data/engine/dashboard_deployment_receipt.json` (status `LOCAL_DEPLOY_ARTIFACT_READY_NOT_REMOTE`). Verify the receipt binds the source dashboard, the locked output, and the cumulative press feed lineage.
3. Final integrity review. Remote deployment is a separate action and is not claimed.

### D.3. Rebuild the hearing corpus and produce the feed

1. `python fec\collect\fetch_hearings_seq.py --rebuild --db hearings_seq_v2.db --since 2019-01-01 --until 2026-12-31` (network, multi-hour). The `--until` default is still 2024-12-31 and must be overridden, since the current corpus holds packages dated to 2026-09-30. Writes `hearings_seq_v2.db` and `hearings_seq_v2.db.receipt.json`, declaring v2 because it is a fresh rebuild.
2. Re-run the antagonism validation gate on the rebuilt corpus (the 2026-07-11 5/5 gate was measured on pre-fix attributions; a display-facet re-validation is Paul's psychometric call).
3. The antagonism producer reads the corpus at the conventional path only (`hearing_antagonism_build.py:24`, `SEQDB = B + r'\hearings_seq.db'`; no flag, no environment variable). Archive the old `hearings_seq.db` (and its receipt if any), rename `hearings_seq_v2.db` and `hearings_seq_v2.db.receipt.json` to `hearings_seq.db` and `hearings_seq.db.receipt.json` at the repo root, then `python fec\members\emit_antagonism.py` (no arguments; it binds the output to the new corpus by sha).
4. `python fec/members/build_hearing_display_feed.py --seq-db hearings_seq.db --meta-db social_media.db` writes the feed and receipt; the desk and bundle builders then show the hearing section. If the producer refuses, the surface stays omitted; read the named reason.

### 6. Release decision

Re-enable scheduling only when all of the following hold: live-tree kernel and `audit_full` measured; four immutable accepted receipts archived; active feed receipt and output hashes validated and equal to the staged values; only promoted runs folded; deferred collectors and the full audit pass; corrected hearing data accepted or the surface intentionally omitted; deployment receipt password-safe and lineage-complete; final integrity gate passed. Then re-enable one scheduler at a time, observe one bounded run, verify its receipts, restore cadence.

## Current disposition

The four failure paths named in the original diagnosis (stranded valid runs, newest-only publication discarding accepted rows, unrelated failures blocking press acceptance, folding before durable promotion) are closed in code, tracked on a branch, and proven against the real dated runs in staging without touching production. Two further defects surfaced and were fixed on the branch (partial-run crash; missing hearing-corpus provenance). The remaining steps all mutate production or resume production flow and stay behind Paul's gate.
