# Melange dashboard next steps

## Immediate review queue

- Review the 22 new GovInfo candidates discovered on 2026-09-04. Keep every row `pending_human_review` until its bill identity, relevance category, member relationship, and source evidence are accepted.
- After review, rerun the roster verifier. Accepted member-bill relationships must append to `data/members/sentinel_verified_membership_history.ndjson`; rejected or unresolved candidates remain visible but non-scoring.
- Confirm the cumulative Excel ledger and its receipt reconcile exactly to the durable history before publishing any dashboard build.

## Recurring collection

- Run the strict Fox, MS NOW, and Washington Journal source audits on schedule. Treat archive terminal dates as source properties, not collector failures.
- Retry press-body network failures through the bounded recovery lane. Keep exhausted failures in the accounting receipt rather than dropping them from source coverage totals.
- Preserve all interview and press records in the data bundle. The 50-item value is UI pagination only and must never be reapplied as a producer cap.
- Refresh Wikipedia summaries for the full authoritative roster and fail publication if coverage, revision provenance, or cross-section deduplication regresses.

## Ranking and display safeguards

- Keep press sentiment active at its reduced weight and allow it to affect labels; legislative action remains the dominant rank input.
- Monitor realized pillar contribution, rank deltas, and tier movement after every rebuild. Investigate fixed-position rules, clamps, or missing-data fallbacks before accepting unexplained immobility.
- Keep personal-experience deduplication display-only. Raw evidence and provenance remain untouched, and contradictory or differently named family details must not collapse together.

## Release gate

1. Collection intake receipt passes with source-level counts and explicit failures.
2. Sentinel history, workbook sheets, and downstream legislative interactions reconcile by canonical bill ID, Bioguide ID, and role.
3. Focused regression tests and the full audit pass.
4. Workbook formula scan and rendered-sheet inspection pass.
5. Dashboard is regenerated, published, and compared with the saved pre-change rank and tier baseline.
