# Cosponsorship forecast self-update: apply, flip, and first live run

Date: 2026-09-04. Follows `audits/COSPONSOR_FORECAST_SELF_UPDATE_2026-09-04.md` (design and dry run). Paul's rulings, verbatim: "Build A and B", then "Flip and run / Apply, Keep, Accept", then "FINISH IT UP". Applied: build A (weekly BILLSTATUS bulk refresh) and B (hash-gated forecaster chain step with an audit freshness check). Kept: the audit check fails when the report is absent. Accepted: the bulk refresh publishes its eight archives with sequential atomic replaces after all eight verify.

## 1. What changed in the live tree

Seven files, applied 2026-09-04 20:43Z by the hash-gated apply script, backup manifest at `<scratch>\build_ab\live_backup\20260904T204314Z`. Three new: `fec/legislation/refresh_billstatus_bulk.py`, `fec/lobbying/refresh_cosponsor_forecast.py`, `fec/tests/lobbying/test_cosponsor_forecast_refresh.py` (24 tests). Four insert-only hunks: `fec/run_pipeline.py` (chain entry), `fec/weekly_refresh.py` (weekly step after the Congress.gov repository step, `hard=False`), `fec/audit/audit_full.py` (check `cosponsor_forecast_freshness`), `fec/tests/run_tests.py` (registration). All compile. The same edits sit uncommitted in worktree `employment-tenure-adjudication-e27de8` on branch `claude/bill-lobbying-regression-d38c1e`; nothing was committed (Paul's no-git directive).

One placement correction after apply: the lobby-network page producer (`make_lobby_network_html.py`) reads the forecast files directly and sat two positions before the refresh step, so its forecast grid would have lagged one chain run. The refresh step was moved to sit immediately before it (live chain position 56 of 63; then lobby-network 57, interactions 58, sidecar 59, desk 60, combined 61, email 62, audit 63). Backup of the pre-move file and both trees' hashes are in `<scratch>\build_ab\MOVE_RECORD.md`; the apply script's anchor was updated to match.

Dials, persisted at user scope with `setx` and read by the weekly task (which bakes no environment of its own): `BILLSTATUS_BULK_REFRESH=1`, `COSPONSOR_FORECAST_REFRESH=1`. Rollback is unsetting them; nothing needs deleting. The weekly task `MoneyballWeeklyRefresh` is Enabled (re-enabled today by the sentinel-finish lane), next run Saturday 2026-09-06 06:00.

## 2. Kernel gate in the live tree

`KERNEL TESTS: 175 passed, 2 FAILED`, 31 minutes (it overlapped the first manifest rebuild). Both failures are pre-existing and outside this change, attributed in `<scratch>\KERNEL_FAILURE_ATTRIBUTION.md`:
- `audit_stale_imports`: 10 bare imports, all inside the staffer-network lane's `fec/surfaces/staffer_*` and `install_staffer_live.py` files (modified 17:27 today by that lane). None of the seven files above appears.
- `test_primacy_tier`: the standing frozen-board fixture mismatch from the 633 to 644 act-universe expansion, recorded as Paul's ratified state in the 2026-08-11 memories. It reads `member_desk_bundle.json` and a fixture dated 2026-08-12; neither is touched by this change.
- `test_cosponsor_forecast_refresh` passed.

## 3. Build A first live run

`refresh_billstatus_bulk.py` with the dial on: status RAN, 37.4 s, 8 archives verified and promoted, 8 changed. hr.zip 30.07 MB to 31.01 MB. Receipt: `data/engine/billstatus_bulk_refresh_receipt.json`; sidecar receipt beside the zips. The system manifest was rebuilt afterwards (80 stores, 1722.7 s) because the `[SYS]` gate hashes that source store and the producer is not a chain step; rebuilt again after the chain tail for the same reason (derived store and surfaces changed).

## 4. Chain

The full chain (`run_pipeline.py`, 17:46 local) aborted at step 2, `audit_collection.py`, after 39 minutes with intake status REJECTED: 62 press-delta bodies in `outputs/press_refresh_20260904` lack an exhausted-network-retry receipt. That is the press collector lane's gate doing its job on that lane's afternoon run; it sits before every step of this change and was not touched.

Between my runs, the sentinel-finish lane ran `run_pipeline.py --from sync_sentinel_bill_ledger` from a shell that predates the dial flip. It executed the new step inert and wrote a clean `SKIPPED_DIAL_OFF` receipt at 23:23:52Z: the default-off path is proven in the live chain.

Tail run, `--from refresh_cosponsor_forecast`, 19:33 local, after that lane's chain exited and baselines were re-snapshotted:

| Step | Result |
|---|---|
| refresh_cosponsor_forecast.py | OK 767.9 s, RAN, "8 input hash(es) differ" |
| make_lobby_network_html.py | OK 72.2 s |
| make_lobby_interactions_html.py | OK 47.8 s |
| bill_lobbying_sidecar.py | OK 35.5 s, 2,961 bills |
| make_member_desk.py | OK 295.6 s |
| make_combined.py | OK 17.9 s |
| make_email_package.py | OK 20.0 s |
| audit_full.py | killed at 120.5 s when the session restart took the wrapper shell down; re-run standalone (section 6) |

Ranks and dashboard data are byte-identical before and after (sha256 of `ranks_python.json` and `dashboard_data.json` unchanged). The forecaster is display-only by construction and `compute_pillars` did not run in the tail.

## 5. Proof

Forecast report now carries today's zip hashes (hr `E16CB7D5…`, s `D5A01C64…`), not the 08-01 ones. 119th panel: 815 modeled bills (was 790), 284,583 pairs (was 276,042), 18,817 positives (was 18,048). Headline unchanged in kind: model AP 0.2386 vs best baseline 0.1771, two split wins. Scores file 166.8 MB. Receipt `data/engine/cosponsor_forecast_refresh_receipt.json`: RAN, 767.1 s, return code 0, eight changed inputs, zero unlisted zips.

Verified joins from the Sentinel Bill Ledger (Scoring Eligible, Congress 119):

| | Before (08-01 forecast) | After |
|---|---|---|
| Pairs | 188 | 191 |
| Found in the candidate pool | 178 | 184 |
| `actual = 1` | 166 | 184 |
| `actual = 0` | 12 | 0 |

All twelve post-snapshot joins flipped. The six bills with August joins now match the repository roster exactly (hr 987 at 113, hr 2094 at 151, s 427 at 7, s 978 at 27; s 3623 newly modeled at 5).

Sidecar: bills with a forecast 304 to 306; rows matched 99,225 to 99,760. Surfaces rebuilt: `lobby-forecast.html` (the page that carries the "Chance they sign on" grid; 1,928 bills with fresh rows, top 10 per bill), `lobby-network.html`, `cu-member-desk.html`, `Moneyball.html`, email packages. Glassbox events for both new steps are in the shared stream.

## 6. Standalone audit

`FULL-BODY AUDIT: 573 passed, 6 FAILED` (20:26 to 20:32 local, after the second manifest rebuild). The new check reports `[FCST] cosponsor_forecast_freshness: OK` (353 recorded inputs, all matching disk, no unlisted zips). The six failures:

| Failure | Attribution |
|---|---|
| vote_category_lean.json stale vs bills archive (V-1) | standing, pre-existing |
| culling surface promotion state (legfix5) | standing, Paul-gated |
| press refresh feed hash-bound, sources/intake false | press lane; the same REJECTED `press_refresh_20260904` run that blocks chain step 2 |
| accepted audio manifest partition, hash=False | audio lane; longform collection was running all afternoon |
| A2b glassbox.events sentinels, 2 disagree | live event stream churn between the manifest build and the audit; inherent to auditing a directory other processes write to |
| personal-texture layer propagates exactly to member profiles, 480/480 mismatches | UNDETERMINED (`<scratch>\TEXTURE_FAIL_ATTRIBUTION.md`). My tail rebuilt the desk from the texture artifact the other lane's 18:28 chain had just written (19:20), so no producer was skipped; both producers (`personal_texture_layer.py` 13:19, `make_member_desk.py` 16:08) were last modified today by other lanes before any chain ran; the mismatch is systematic (every member), which points at a layer-to-desk format disagreement in that lane's code rather than at this change. Not proven either way because the pre-tail desk was overwritten. That lane should re-run its own check. |

## 6a. Full chain run, 2026-09-05 (Paul: "Run the full chain now")

`python -u fec/run_pipeline.py`, live tree, 12:11:59 to 12:54:43 local (42.7 min), dial `COSPONSOR_FORECAST_REFRESH=1` set explicitly. Preflight found no live chain, audit, collector, or Excel. Baselines snapshotted at 12:12:03.

Result: 43 steps OK, then step 44 `build_dashboard_bundle.py` failed (`!!`, 11.9 s) and the chain stopped. Steps 45 to 63 did not run, so the forecast refresh step (56), the surfaces, and the in-chain audit were not exercised today; the 2026-09-04 tail run (section 4) remains the evidence for those.

Step 2, the intake gate, passed in 333 s with status ACCEPTED (yesterday it took 2,343 s and rejected on the then-unfinished press retry pass). Step 31 `compute_pillars.py --write` rewrote `ranks_python.json` byte-identical to the 12:12 snapshot: 0 of 533 ranks moved, 0 score values changed, `ab_weights` 45/10/40/5 unchanged (that weight set is the out-of-lane change flagged 09-03 in the sentinel memory; not touched here). `dashboard_data.json` and the lobbying sidecar are byte-identical to their snapshots because their producers were not reached.

Step-44 cause (`<scratch>\CHAIN_FULL_20260905_DIAGNOSIS.md`): the bundle builder's contract check at `fec/surfaces/build_dashboard_bundle.py:81` compares `member_narrative_evidence_v4.json` (`basis_sha256` from 2026-09-04 16:10) against `data/members/profile_basis_v2.json`, which another lane rewrote at 03:05 on 2026-09-05; the hashes disagree and the step refuses. The narrative ledger is produced offline by `build_member_narrative_ledger.py`, which is not a chain step and belongs to the narratives/profile lane. Nothing the bundle builder reads is produced by this lane, and step 44 runs before position 56. An overnight run by someone else wrote `dashboard_data.json` at 03:01 and the sidecar at 03:10 with the old basis, so the desk and dashboard on disk are the 03:xx vintage.

Also observed in the step-31 line, not this lane's: `compute_pillars` prints "ROLE REGISTRY EXPIRES IN 120 DAYS (2027-01-03) - CHAIN WILL FATAL HERE".

Audit tail: not reached; the standalone figure stands at 573 passed / 6 FAILED from 2026-09-04 20:26 (section 6).

To finish a full pass: the narratives lane re-runs `build_member_narrative_ledger.py` against the current basis, then `python fec/run_pipeline.py --from build_dashboard_bundle` completes steps 44 to 63. Until then Sunday's weekly (2026-09-06 06:00) will stop at the same step.

## 7. What happens next without anyone touching it

Saturday 06:00 the weekly task runs: step 3 refreshes the bill repository, the new step re-pulls the eight BILLSTATUS-119 zips (all-or-nothing, last-good kept on any failure, receipt written either way), then `run_pipeline.py` reaches the refresh step, compares input hashes with the report's provenance, and re-runs the 16-minute forecaster only when something moved. Same-input weeks cost about 7 seconds. `audit_full` fails `cosponsor_forecast_freshness` if the report ever falls behind its inputs. The weekly chain still has to clear the press intake gate at step 2, which is the press lane's.

## 8. Open items, none of them this change's

1. Press intake: CLEARED on its own. The 17:46 chain audited `outputs/press_refresh_20260904` while its live-network retry pass was still running; that pass completed at 18:24 local and wrote a valid `press_network_retry_receipt.json` (63 failed bodies, all `body_unavailable_after_network_retry`, 1 recovered, checksums reconcile). A later full intake audit (receipt 21:18 local) shows `press_delta`, `press`, `interviews`, `house` at 0 errors. The gate now rejects on `audio_supply` alone: "title-match-unverified YouTube audio entered the accepted manifest" (`fec/audit_collection.py:880`): 61 YouTube-rooted entries in the accepted clips manifest have no exact-window verification receipt (`data/speech/local_youtube_exact_window_verification*_v1.receipt.json`; manifest last written 2026-08-31, no collector running). The documented clearing path is that lane's verifier, `fec/speech/verify_local_youtube_exact_windows.py --mode write` with a timestamped output receipt (audio signal processing, no network, no LLM); hand-editing either manifest breaks the hash checks. Speech/audio lane's call, not run here. Details: `<scratch>\PRESS_INTAKE_DIAGNOSIS.md`, `<scratch>\AUDIO_SUPPLY_DIAGNOSIS.md`. RESOLVED 22:56 local: a fresh step-2 run with the chain's exact invocation (`python fec/audit_collection.py --output data/engine/collection_intake_receipt.json`, 33 min) returned status ACCEPTED with house, audio_supply, interviews, press, and press_delta all at 0 errors; the audio_supply entry cleared between 21:18 and 22:56 without any action from this lane. The chain is unblocked for Saturday's weekly run.
2. `test_primacy_tier` frozen-board mismatch and the staffer lane's 10 bare imports keep the kernel at 2 FAILED.
3. C-ledger options 1 to 3 and the departed-member policy question from the design record remain Paul's.
4. The new audit check reports FAIL in any data-isolated worktree (report absent), by ruling.
5. The system manifest is git-tracked and was rebuilt twice today; it is now modified on disk and uncommitted, like everything else in the live tree.

## 9. Evidence

Scratch root: `C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-employment-tenure-adjudication-e27de8\27337674-dfbb-4dce-8acd-ad49411e9dfb\scratchpad\`
- `build_ab\BUILD_RECORD.md`, `VERIFY_REPORT.md`, `MOVE_RECORD.md`, `apply_ab.py`, `live_backup\`, `move_backup\`
- `live_kernel_tests.log`, `KERNEL_FAILURE_ATTRIBUTION.md`
- `manifest_rebuild_1.log`, `manifest_rebuild_2.log`
- `live_chain.log` (aborted full run), `CHAIN_STEP2_DIAGNOSIS.md`, `live_chain_tail.log`
- `postrun_proof.py`, `POSTRUN_PROOF.md`, `postrun_proof.json`, `FORECAST_SURFACE_CHECK.md`
- `live_audit_full.log`
- Live receipts: `data/engine/billstatus_bulk_refresh_receipt.json`, `data/engine/cosponsor_forecast_refresh_receipt.json`, `%LOCALAPPDATA%\Melange\lda_rebuild\raw\billstatus119\BILLSTATUS-119.receipt.json`

## 10. Brain update draft (STATE.md, Active workstream)

BILL-LOBBYING REGRESSION LANE (2026-09-04, evening): A (weekly BILLSTATUS-119 bulk refresh) and B (hash-gated `cosponsor_forecast.py` chain step at position 56, before its first consumer, plus `audit_full` check `cosponsor_forecast_freshness`) are APPLIED to the live tree uncommitted, both dials ON at user scope, weekly task Enabled for Saturday 06:00. First live run: A pulled 8/8 changed zips in 37 s; B RAN 768 s; 119th panel 790 to 815 bills; all 12 verified post-snapshot joins now `actual=1`; ranks byte-identical. Kernel 175/2, both failures pre-existing and other-lane. Full chain blocked at step 2 by the press lane's REJECTED intake (62 bodies, `press_refresh_20260904`); tail from the refresh step completed. Records: `audits/COSPONSOR_FORECAST_SELF_UPDATE_2026-09-04.md`, `audits/COSPONSOR_FORECAST_REFRESH_RUN_2026-09-04.md`.
