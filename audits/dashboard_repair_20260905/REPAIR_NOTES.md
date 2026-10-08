# Dashboard audit repair — September 5, 2026

Completed 2026-09-05T21:20:05.031430+00:00. **All 13 reported dashboard audit failures are resolved.**
The independent full audit now reports **582 passed, 0 failed**; the original
result was 570 passed, 13 failed. See `full_audit_final.log` and `full_audit_result.json`.

## What changed

| Area | Resolution |
|---|---|
| Personal texture | Preserve all 480 source payloads exactly and validate the added display-deduplication metadata separately. |
| Press intake | Validate all three cumulative accepted runs, their source files and immutable acceptance receipts. Official mentions remain non-scoring. |
| Votes | Replace the stale June export with a hash-bound Voteview snapshot. Rebuild with exact Congress/measure types, existing categories/sign rules, and retained holds/exclusions. |
| Culling status | Verify all 11 installed culling decision/evidence files against the original promotion receipt, and record subsequent rank refreshes separately. The original promotion receipt is unchanged. |
| Dashboard priorities and freshness | Rebuild stance, ranks, primacy, allocation and pages in dependency order. The published scenario priorities now match current engine values. |
| Profile dependencies | Recompute nine existing speech turns, then rebuild the evidence ledger and all 533 descriptive profiles against the current basis before rendering pages. No new audio review or promotion occurred. |
| Inventory drift | Remeasure with the actual manifest producer after publication. Retain the original manifest and a before/after reconciliation; no measured values or source timestamps were manually authored. |
| Glassbox retention | Recognize the installed rolling 5,000-event retention policy. Individual filenames may retire; store presence, size-class and file-count checks remain active. |

The fresh vote snapshot covers House records through September 3 and Senate
records through August 8. It yields 38 accepted final-passage roll calls,
15,046 member-vote rows, 705 historical members and 6,261 category cells.
One CFPB direction is ambiguous across Congresses and remains unscored; all
828 contributions lacking an unambiguous CFPB direction remain unscored.
Source acquisition, hashes and documentation are in `voteview_source`;
see [Voteview vote-code documentation](https://voteview.com/articles/data_help_votes).

## Verification

- Independent full dashboard audit: **582 passed, 0 failed**.
- Repair regression suite: **182 passed** (`targeted_tests_final.log`).
- Expanded inventory suite: **45 passed**, including three new retention controls
  (`manifest_tests_final.log`; 42 overlap with the initial suite).
- Inventory: all **80 declared stores present**, no removed store declarations.
  Existing scan-budget limits, notices and source exceptions remain explicit.
- Browser: current dashboard, member detail shell and combined staffer page load;
  the dashboard reports 533 speech profiles passing, its numerical self-check
  agrees, and browser error logs are empty. This was not a full accordion/visual audit.
- Staffer acceptance passed after the concurrent task's restart on PID
  45620: the same verified v5 graph, 690,500 searchable records,
  original user assertions and tested route behavior are retained.

## Scope and retained evidence

`before` contains the original examined inputs and code. The original staffer
completion receipt and its earlier audit failures remain historical records.
`staffer_release_lineage.json` distinguishes 35 unchanged prior-receipt files,
five changes from this repair and nine changes from the user's concurrent
**Review and complete markdown** routing/UI task. That task owns and verifies its
new standalone implementation; this repair does not claim its source is unchanged.

The nine remeasured audio turns remain candidate-only: zero qualified or
baseline-eligible turns. Existing collection gaps and review-only relationships
were not waived or promoted. A pre-existing descriptive-speech fallback receipt
remains outside this resumed pipeline slice; it retains the last accepted artifact.

An earlier broad primacy test run exposed a live-data/frozen-board-order fixture
mismatch before vote publication. That unrelated frozen fixture was not rewritten
to force a pass. The clean result above is the complete dashboard audit plus the
listed targeted suites, not a claim that every repository test was run or passes.

`WORK_LOG.md` preserves the repair sequence and intermediate failures. The first
inventory attempt rejected an invalid non-secret `presence_only` policy before
writing a manifest; the corrected policy and its loss-detection controls passed.
The pipeline's pre-census audit had eight inventory mismatches; the independent
post-census run above supersedes that result. The `before/fec/run_pipeline.py`
copy was captured after initial vote-step wiring, as recorded in the work log.

`completion_receipt.json` binds the final audit, relevant code, evidence and
published artifacts to their actual SHA-256 hashes. No commit was made.
