# GovInfo Candidates Review — Reconciliation Receipt

**Date:** 2026-09-06
**Lane:** claude/govinfo-candidates-review-98f805, worktree hungry-edison-77305f
**Status:** ADJUDICATION PROPOSED — NOT APPLIED. Every figure below is read-only measurement.

## 1. Candidate set derivation

The set of 22 is confirmed by two independent derivations that agree exactly (22 added, 0 removed, both routes).

- **Route A:** discovery-row `Canonical Bill ID` set difference between plan `outputs/sentinel_bill_ledger_20260904T174901Z/sentinel_bill_workbook_plan.json` (18,118 discovery rows) and `outputs/sentinel_bill_ledger_20260904T222909Z/sentinel_bill_workbook_plan.json` (18,140 discovery rows).
- **Route B:** `canonical_key` set difference between `data/legislation/congress_advanced_current/congress_advanced_records.ndjson` (18,579 rows, sha256 `7a9bd69dc996c9093a6b9ddb794cba803c3619c98dc25daa4768de943c4880aa`, mtime 2026-09-06T10:06:21Z) and `audits/legfix5/congress_advanced_pages_20260725/congress_advanced_records.ndjson` (18,557 rows, sha256 `debb8a20...`).
- 18,579 − 18,557 = 22. Neither file contains duplicate canonical keys, so line counts equal key counts and the 22 is not a dedup artifact.

**CORRECTION OF RECORD.** `audits/SENTINEL_LANE_COORDINATION_2026-09-04.md:71` and `:80` describe "22 new discovery candidates picked up from data/legislation/congress_advanced_current." That is arithmetically true and mechanistically misleading. `fec/legislation/sync_sentinel_bill_ledger.py:945-947` is a stateless full rebuild whose only exclusion test is membership in `bill_repository_live.json`; there is no incremental-detection predicate and no prior-run state anywhere in the discovery pass. The +22 was caused by the discovery SOURCE switching from the 2026-07-25 audit snapshot (`debb8a20...`) to the newly collected current file (`7a9bd69d...`). Nothing was detected; a different file was read. The doc's "18,806 expected" at `:60` is a human projection, not a computed value.

## 2. Durable sentinel history reconciliation

| Check | Recorded | Measured | Result |
|---|---|---|---|
| history sha256 | `c4107a8cbf743cf7d4de48ff4984db9afaf8a2e7273b64dbf1bbe3ff4a92e6a5` | recomputed identical | MATCH |
| verified_memberships | 199 | 199 rows, 199 distinct membership_key | MATCH |
| verified_interaction_rows | 204 | 204 distinct (membership_key, area) pairs | MATCH |
| rows with empty areas | — | 0 | clean |

- File: `data/members/sentinel_verified_membership_history.ndjson`, 343,877 bytes, mtime 2026-09-04T19:14:34Z (LIVE tree).
- Receipt: `data/engine/sentinel_verified_membership_history_receipt.json`, 6,365 bytes, mtime 2026-09-05T16:26:19Z, status PASS.
- History mtime is OLDER than receipt mtime and the hash matches, so the history was NOT modified after the receipt was written. Today's 06:00 chain did not touch it.
- Intersection of the 22 candidates with the durable history: ZERO, verified two independent ways (stored `repository_key` field, present on 199/199 rows, 34 distinct keys; and re-derivation from `bill` + `congress`, also 34 distinct keys). Both intersections empty.
- History congress histogram: 117 → 5, 118 → 8, 119 → 186. The highest 119th-Congress keys the history carries are `119:hr:8395` and `119:s:3940`, well below the candidates' 9623–10242 / 5042–5358 band.

Writer semantics, for the record: the history file is fully rewritten each run via `write_text_atomic()` (temp file then `os.replace`, atomic on NTFS). It is NOT byte-append. Monotonicity is a RECORD-level property enforced by `merge_verified_history()`, whose contract is that no batch can delete an identity or category. Any claim of "append-only" should be stated at the record level only.

## 3. Workbook receipt

`data/engine/sentinel_bill_workbook_receipt.json`, 2,478 bytes, mtime 2026-09-05T16:27:48Z, status PASS:

- discovery_candidates: 18,579
- discovery_pending_review: 14,031
- discovery_only_ids: 18,140
- repository_bills: 464

Its bound discovery file hash `7a9bd69d...` still matches the live file today, even though a collector rewrote that file at 2026-09-06T10:06:21Z — the 09-06 collection reproduced byte-identical content.

## 4. Vintage split — read before quoting any figure above

Today's chain rewrote `bill_repository_live.json`: mtime 2026-09-06T10:06:41Z, sha256 now `c3af8298e0d14895ba64d59243ea9d453735a96cdfd185ec5ad469e409752dfb`, still 464 bills, correctly hash-bound to `data/engine/congress_bill_refresh_receipt.json` (status PASS, completed_at 2026-09-06T10:06:42Z).

However `sentinel_bill_workbook_receipt.json` still records `repository_sha256: fe0e7fd29b48082b286433f1ad3411278b7a58db635e6284b3701aef89c97506`, and every row of `collector_roster_updates.ndjson` (3 rows) and `collector_roster_pending.ndjson` (20 rows) carries that same `fe0e7fd2...` stamp.

Consequence: the 199/204 history figures and the 18,579/14,031 workbook figures were computed against YESTERDAY's repository. Nothing is corrupt, and the fail-closed binding that actually gates the producer (repository to refresh receipt) is green. But a receipt that quotes 199/204 or 18,579/14,031 alongside the LIVE repository sha `c3af8298...` would be mixing two vintages. This receipt quotes them against `fe0e7fd2...` and says so.

## 5. Member relationships

Resolved from authoritative BILLSTATUS-119 XML (`%LOCALAPPDATA%\Melange\lda_rebuild\raw\billstatus119\`, mtime 2026-09-06T06:06), not from the discovery headline.

- Cosponsor-count cross-check BILLSTATUS vs discovery record: 22 of 22 AGREE, zero disagreements.
- Distinct members touched: 102 (21 distinct sponsors, 86 distinct cosponsors, 5 in both roles). Party split 69 R / 33 D.
- Roster resolution against `member_desk_bundle.json` (533 members, 0 ambiguous bioguides dropped, indexed with the same logic as `verify_collector_roster_updates.py:391-405`): 102 of 102 resolve. Zero unresolved.
- Withdrawn cosponsors: ZERO across all 22, verified by absence of the string `sponsorshipWithdrawnDate` in every file, not merely by parse.
- Four post-introduction cosponsor joins observed: `119:hr:10017` D000634 joined 2026-09-02; `119:hr:10124` C001119 joined 2026-08-31; `119:s:5219` S001150 joined 2026-08-05; `119:s:5335` C001096 joined 2026-08-07.
- Source gaps, genuine and verified by element absence: `119:hr:10242` carries no policyArea and no subjects (introduced 2026-09-03, not yet CRS-coded); `119:sres:817` carries no committees element and is the only one of the 22 with legislative subjects (5).

**STRUCTURAL FINDING.** No member edge from these 22 can be created by the sanctioned path, and the reason is not a queue. `fec/legislation/verify_collector_roster_updates.py:521` iterates only keys already present in `bill_repository_live.json`, so a key absent from the repository is never visited and yields no row of any kind — neither accepted nor queued. The `bill_not_in_ledger_universe` reason at `:529-533` fires for the OPPOSITE condition (present in the repository, no act in the bundle-derived view) and the source marks it unreachable at `:528`. Verified numerically: the bundle's 5,902 member-bill rows yield 644 distinct act keys, of which 464 are parseable repository keys — exactly the 464 in the repository. All 22 candidates are absent from both the repository and the bundle act universe. Searching a pending queue for them will therefore never find them. The governing contract is the CLOSED UNIVERSE clause at `:56-62`, protecting the universe-sync assertion at `fec/engine/primacy_factors.py:466`.

## 6. Dispositions proposed

Staged, NOT applied, at `audits/govinfo_candidates_20260906/proposed_decisions.ndjson` (22 lines, 13,732 bytes, sha256 `87164cca308258065e0736abbdf7688d68921cab4789533b19d1c0466d3a54f5`). Counts: 14 `exclude_candidate_false_positive`, 6 `hold_visible_non_scoring`, 2 `upsert_candidate_memberships`.

All 22 carry `scoring_eligible` false and `ultimate_direction` null, including the two includes: `integrate_greenlit_legislation_culling.py:380-390` derives eligibility from `ultimate_direction`, and direction is a stance ruling reserved to Paul.

Rule applied, fixed in advance of member resolution per D-005:

- **Gate A, negative screen:** zero CU terms in the official GovInfo BILLS/BILLSTATUS XML implies no CU provisions, the one use of term counting DE-001 leaves legal. 14 candidates.
- **Gate B, operative text (L3 rung):** amends the Federal Credit Union Act, concerns NCUA, or carries an explicit CU title. 2 candidates.
- **Gate C, centering test:** CU terms present but centered elsewhere, held for Paul's cell adjudication. 5 candidates.
- **Gate D, non-substantive vehicle:** procedural resolution, scope question reserved to Paul. 1 candidate (`119:sres:817`).

**SUBSTRATE WARNING.** The negative screen was run twice. Over the discovery record's own text (`raw_text`, 144–484 chars) it found CU terms in 2 candidates. Over the official GovInfo XML it found CU terms in 7 — five false negatives (`119:hr:10184`, `119:hr:10242`, `119:s:5335`, `119:s:5358`, `119:sres:817`). The discovery record is a search-result headline, not bill text, and is NOT a valid substrate for this screen. Only the official-XML screen carries the DE-001 negative force.

`119:hr:10017` (anti-CBDC) was deliberately NOT excluded despite zero CU terms: D-002 priced the anti-CBDC pair H.R.1919 / S.1124 as adjudicated tensor cells at relevance 0.15 with zero CU operative content, so the settled class rule places this act at that cell rather than at exclusion.

## 7. What was NOT done, and why

- The roster verifier was NOT rerun. The attempt was blocked by the environment's permission classifier. It remains Paul's step. Note before rerunning: because the repository changed under it today, a rerun is expected to change `collector_roster_updates.ndjson`, which would stale the `current_delta.sha256` binding (`b81f1b7538abf4938a7f648edd5b18a2b82d6e83cc7c9993f7bb40f358718cd8`) recorded in the history receipt. Rebinding requires rerunning `sync_sentinel_bill_ledger.py`, which also rewrites the workbook and the history.
- The adjudication ledger was NOT updated. `legislation_adjudication_ledger.ndjson` is a GENERATED artifact, written by `integrate_greenlit_legislation_culling.py:517-530` and promoted from staging by `promote_greenlit_primacy_integration.py:61-62`. Hand-editing it would violate the standing rule against hand-extending generated JSON. The ledger has not been written since 2026-07-28, which is why all 22 candidates are structurally unadjudicated and why that population will keep growing.
- "Visibly non-scoring" is satisfied in the LEDGER but has NO RENDERER. The 1,184 existing `held_visible_non_scoring` rows are consumed by nothing: repo-wide greps for the ledger filename, `held_visible_non_scoring`, `human_review_hold`, `zero_weight_reason` and `scoring_eligible` find no consumer in `fec/`, `run_pipeline.py`, `make_dashboard_html_00.tpl`, or `make_member_desk_00.tpl`. Discovery candidates are non-scoring by construction (`sync_sentinel_bill_ledger.py:945-965` emits `scoring_eligible` hardcoded False), so the non-scoring half is structurally guaranteed; the "visible" half is a label with no surface behind it. Making these rows genuinely visible is an unbuilt renderer, not part of this adjudication.

## 8. Operational finding outside this lane's scope

The Sunday 2026-09-06 06:00 `MoneyballWeeklyRefresh` did NOT complete. Last Result 1073807364 = 0x40010004 = STATUS_CONTROL_C_EXIT. The last log line is 06:46:53 ("Wikipedia biographies (full roster)" OK) with no further entries. `data/engine/weekly_refresh_status.json` is frozen at `"last_outcome": "RUNNING"`, `"last_start": "2026-09-06 06:00:01"`, with no live process behind it — a stale RUNNING flag that will mislead the next reader. The run died in the collector phase, which sits above the chain, so chain steps 1 and 2 (`verify_collector_roster_updates`, `sync_sentinel_bill_ledger`) almost certainly never executed. Next scheduled run is 2026-09-13 06:00.

## 9. Three stray temp files, not cleaned up (read-only lane)

In `data/legislation/congress_advanced_current/.govinfo_fallback_cache/receipts/`, all mtime 2026-09-04 15:37, from an interrupted atomic write during the 09-04 collection: `.10c4a931….json.8pp5ca4h.tmp` (0 bytes), `.20ec3850….json.s6grpsqo.tmp` (347 bytes), `.bb04e1b5….json.vqt_8n_l.tmp` (343 bytes). Harmless — they are dot-prefixed and not read as receipts — but they inflate a naive receipt count from 9,248 to 9,251.

Separately, `manifest.json` declares `union.records_sha256 = 4392b3c0…`, which matches no hash of the file bytes. This is NOT a defect: `govinfo_discovery_fallback.py:1371` uses `stable_hash(output_records)`, defined at `:115-118` as the sha256 of the compact JSON of the parsed record LIST, not of the file. The value reproduces exactly from the parsed list. Recorded so nobody else investigates it twice.

## Addendum — 2026-09-06 20:32Z: sections 2, 3 and 4 superseded by a peer chain run

Recorded per the frozen-vintage rule. The claims above stand as measured at their time and are deliberately NOT edited; this addendum records their supersession.

At 2026-09-06T20:21:08Z a peer session (worktree graph-consolidation-identity-d8d358) started a full `run_pipeline.py` chain against the LIVE tree. That chain executed step 11 `verify_collector_roster_updates.py` at 20:30:09Z and step 12 `sync_sentinel_bill_ledger.py` at 20:30:12Z, completing PASS at 20:32:04Z. This session ran neither: its manual rerun was halted at pre-flight on the collision and wrote nothing. The negative control holds — `backups\govinfo_candidates_lane_20260906` was never created.

Step 11 result, from the chain's own log: `collector roster verification: 202 accepted, 20 queued, 5015 already present, 910 unresolved`.

| Artifact | Value in sections 2-4 | Post-chain value |
|---|---|---|
| sentinel_verified_membership_history.ndjson sha256 | c4107a8c...4a92e6a5 | 59c3807a2502b90ea472a9d0def3711d059ac6cdef6fa698ef578af9d4ecdde3 |
| verified_memberships | 199 | 205 |
| verified_interaction_rows | 204 | 210 |
| collector_roster_updates.ndjson sha256 | b81f1b75...718cd8 | c1d108ee38683bd1b20a6123caed530d14d4127389bb07f5f44af7599eceb505 |
| collector_roster_updates.ndjson rows | 3 | 202 |
| collector_roster_pending.ndjson sha256 | 49e1e02f...3c5705 | bc0b3cac2d2fa488b13db05b726bd5c90b222f3f01efc56a3f6eb6817e64807c |
| history receipt sha256 | 9120d738...81e2f1 | eb1e1655...e2f3c9 |
| workbook receipt sha256 | 833a7e29...f500d40c | 112fa86a... |
| ledger_rows_excluding_header | 18,828 | 18,834 |

BINDING: HELD, but RE-ESTABLISHED rather than survived. `current_delta.sha256` is now c1d108ee..., matching the new updates file. The b81f1b75... binding quoted in section 7 no longer exists.

VINTAGE SPLIT RESOLVED. Both roster ndjson files now stamp `repository_sha256: c3af8298e0d14895ba64d59243ea9d453735a96cdfd185ec5ad469e409752dfb` (today's repository). The fe0e7fd2... vintage described in section 4 is gone from disk, and the mixed-vintage caveat in that section no longer applies to these files.

SECTIONS 1 AND 6 STAND UNCHANGED. `discovery_candidates` 18,579 and `discovery_pending_review` 14,031 are byte-identical post-run. The 22 candidates remain unadjudicated, and the staged proposal at proposed_decisions.ndjson is unaffected.

SECTION 5'S STRUCTURAL FINDING RE-TESTED AND CONFIRMED. All 22 canonical keys are ABSENT from both collector_roster_updates.ndjson (now 202 rows) and collector_roster_pending.ndjson (20 rows), and the pending reason distribution is unchanged at ledger_row_absent_from_live_roster 13, sponsor_absent_from_ledger 3, role_conflict 2, withdrawn_join_absent_from_ledger 1, withdrawn_on_existing_ledger_row 1. These 22 produce no roster row even when the verifier runs against today's refreshed repository, exactly as verify_collector_roster_updates.py:521 predicts. This is a live confirmation, not an inference from reading.

CORRECTION TO SECTION 7. The collision window is wider than that section states. Live consumers of collector_roster_updates.ndjson are sync_sentinel_bill_ledger.py:411 (which owns the current_delta binding), surfaces/make_member_desk.py:2034 (called at run_pipeline.py:226, far later in the chain), and audit/dashboard_integrity.py. The window in which a manual rewrite silently changes downstream data spans steps 11 to roughly 40, not 11 to 12.

OPEN ITEM FOR PAUL. The step-12 workbook receipt records `status: PASS` alongside `artifact_process_exit: 0xc0000409` (STATUS_STACK_BUFFER_OVERRUN, a fail-fast code). The workbook was installed at 20:32:01Z, so the artifact exists, but a PASS recorded next to a fail-fast exit from the artifact process warrants checking whether that exit code is inspected by the gate at all.
