# Backend accounting review closeout — 2026-09-12

This is internal engineering evidence for the chart-creation review. It is not a replacement for a published industry report. Source databases, payloads and historical ledgers were read-only throughout this lane.

## Findings fixed by the backend lane

- Source observations are globally coalesced before company partitioning. The previous first-company/first-source approach asserted accepted claims for rejected observations and could charge the wrong company or count an entirely rejected gift.
- Stored attribution claims, legacy attribution conflicts and source-record conflicts now enter the engine.
- Canonical rejected/excluded records stay at zero even when copies disagree about ZIP or other metadata. Independent reproduction `rejected-conflict-probe.py` changed from `counted_cents=10000` to `0`, preserving the metadata-conflict reason.
- Ledger reuse now requires matching rule fingerprints, database, industry, complete election-cycle scope, company roster and distinct source-ID count. The cache records its source/evidence/ledger epoch and refuses to label old loaded code as new code.
- Canonical ledger rows preserve accepted-query priority and enrichment instead of selecting an arbitrary minimum row ID. Financial identity is checked before verified remote metadata enriches geography.
- Payload receipts use a bounded disk-backed projection, reject conflicting representations of one physical source ID, and reconcile included cents to the pinned payload. Dates use calendar validation.

## Banking evidence and limits

The pinned Banking payload `industry_data-4abdea581b99cec1.json` has included receipt totals of $16,652,458.77 (2021–2022), $26,107,204.16 (2023–2024), and $12,003,181.12 (2025–2026): **$54,762,844.05 / 5,476,284,405 cents**. An earlier `$54,762,843.98` message from this reviewer was a transcription error, not an observed source discrepancy.

The historical immutable ledger `20260912T204736-ed3b2a351279` reports **$78,233,832.96 provisional observed original giving** and **$0 supported original subset**. Its own baseline is **$133,516,227.27**, because its published-receipt baseline was unpinned. The ledger delta therefore cannot explain the difference from the published $54.76m view. These historical amounts must not be relabeled as final results from the revised index.

That ledger contains 332 supported local duplicate-representation links:

| Link | Count | Signed amount excluded |
| --- | ---: | ---: |
| Reciprocal earmark | 246 | $32,370.00 |
| Explicit observed amendment | 28 | $2,496.00 |
| Same-filing memo reference | 58 | $130,818.55 |
| Total | 332 | $165,684.55 |

These links support particular relationship deductions. They do not certify that all remaining gifts are unique or that collection is complete. The old ledger also has 32 repeated physical source observations coalesced to one decision per source ID; those are query copies, not 32 proven duplicate gifts. Unknown roles, unverified ownership, transfers and missing complete filing inventories remain material limitations of the provisional basis.

The receipt basis is the appropriate reconciled default. It reproduces the published included-receipt view; reconciliation alone does not establish unique original gifts. Retain the provisional/support-subset labels and drill-through evidence for other bases.

## Verification

- Five current JS suites: **112 passed, 0 failed**. These cover compound grouping, prohibited money splitting, distinct coverage tokens, non-null field counts, source-grain guards, additive Other, forecast/percentage totals, chronology/gaps, multiple-measure panels, signed bars, cents formatting, scatter complete pairs, selection identity and legends.
- Existing chart-builder browser suite: **2 passed, 0 failed**.
- Independent backend focused suite: **15 passed**, before the final scope/rejected-conflict additions. Backend owner subsequently reported **80 tests passed** across backend/legacy/engine/runner suites.
- Final independent read of changed backend found no remaining critical issue; corrected rejected-conflict reproduction passed. All-industry live reconciliation remains owned by the backend lane and must supply the final production-data totals.

Useful internal probes: `backend-accounting-probes.py` (historical first-seen bug model), `banking-ledger-audit.py`, `inspect-contribution-index.py`, `rejected-conflict-probe.py`. The original JavaScript reproduction asserts pre-fix behavior and is an audit receipt, not a post-fix regression suite.

## Recovered-source lineage follow-up

The hydration output hash is stale or absent for several recovered databases after metadata repairs. A stronger, independent check compares each current database's complete financial identity universe against the accepted snapshot pinned to the original report database. Snapshots include excluded/source-only observations, not just published included receipts.

All seven recovered sources passed: **1,776,120 distinct physical source IDs**, with **zero added, changed, missing, or financially conflicting identities**. The 1,144 repeated query observations agree financially with their physical source IDs. Identity here is source ID, committee, contributor name, exact date, integer cents and election cycle; this does not certify donor linkage or unique gifts.

| Recovered source | Distinct source IDs |
| --- | ---: |
| Community Banks | 4,649 |
| Credit Arms | 434,958 |
| Credit Union | 67,169 |
| Crypto | 14,801 |
| Fintech | 86,270 |
| Property & Casualty Insurance | 360,207 |
| Telecom | 808,066 |

`recovered-source-lineage.jsonl` records every original/current/snapshot fingerprint and comparison result. In particular, Fintech's current `d55ce04c…` database matches all 86,270 identities from snapshot `74658d00…`, pinned to original report database `2a9bc019…`; it is not accepted merely because it occupies the hydration output path.

The new `mentat/app/contribution_source_guard.py` enforces this comparison at runtime and retains content-bound disk proofs. Source, accepted pointer, snapshot or algorithm changes invalidate a proof. The module refuses to claim a newer algorithm fingerprint from old loaded code, checks uncheckpointed writes even after cache hits, and verifies the exact original database fingerprint for non-recovered sources such as Banking. **14 focused source-guard tests passed**. Root owns workbook-guard/server wiring and final live HTTP validation. No contribution-index monetary code or token was changed by this follow-up.
