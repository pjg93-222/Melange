# Melange bill-sentinel integration handoff

Generated when Codex usage reached 99% used / 1% remaining on 2026-09-03.

## Outcome

The bill sentinel now has a durable Excel ledger and a same-cycle dashboard path:

1. The weekly refresh runs the official Congress.gov Advanced Search discovery collector.
2. Every discovered measure retains its canonical bill ID in `Sentinel Bill Ledger.xlsx`.
3. Unreviewed discoveries are visible as pending and cannot enter scoring.
4. Verified member/bill relationships are written to the Excel ledger and its role-specific interaction tabs.
5. `build_archive_legislative.py` reads scoring-eligible rows from the Excel ledger before stance labels are regenerated.
6. The member desk still consumes the verified collector sidecar for primacy, with the Excel ledger and receipt added to the dashboard integrity fingerprint.
7. Dashboards were regenerated after the integration.

The formula-heavy `Moneyball Main Version - Blended.xlsx` is deliberately not used as the persistence target. An attempted artifact-tool export recalculated unrelated legacy formulas to errors; it was rolled back from the automatic backup before publication. The dedicated ledger workbook isolates bill collection from that legacy formula risk.

## Current ledger

- 18,557 unique Congress.gov discovery candidates tracked.
- 18,118 candidate IDs are outside the existing 464-bill live repository.
- 14,009 candidates remain pending review and are not scoring eligible.
- 464 official GovInfo/Congress.gov repository bills tracked with canonical IDs.
- 196 verified member joins, expanded to 201 category-specific interaction rows.
- 20 collector exceptions retained as pending review.
- 18,803 total data rows in the Excel ledger.
- Role tabs contain 31 original-cosponsor rows and 170 later-cosponsor rows.

The current discovery inventory comes from the latest completed local Advanced Search checkpoint (`audits/legfix5/congress_advanced_pages_20260725`). The new weekly step will create and resume `data/legislation/congress_advanced_current`; its first fresh network run has not yet been completed in this session.

## Downstream state

- `archive_leg.json` loaded all 201 scoring-eligible Excel rows.
- `category_stance.json`, `member_desk_bundle.json`, `cu-member-desk.html`, `Moneyball Dashboard.html`, and `Moneyball.html` were regenerated.
- Dashboard integrity report: PASS.
- Rank delta: 0 members; score map exactly matches the pre-change authority.
- Primacy factor delta: 0 members, because these 196 joins were already present in the verified sidecar consumed by the prior primacy build.
- Primacy tiers: T1 13, T2 24, T3 48, untiered 448.

## Verification

- 92 focused legislation/dashboard tests passed.
- Python and Node syntax checks passed.
- Excel workbook has exactly three generated sheets and 18,804 rows including the ledger header.
- Artifact-tool formula-error scan found zero errors in all generated bill ranges.
- All three generated sheets were rendered and visually inspected.
- Dashboard integrity and exact rank/score parity assertions passed.
- The full-body audit reported 545 passes and 30 failures. Most are pre-existing freshness/system-manifest drift. One relevant outstanding item is that the legacy main workbook's stance display column is not synchronized to the newly regenerated shared crown-law labels; the shipped HTML/dashboard labels are current.

## Code diff

- Added `fec/legislation/refresh_legislation_discovery.py`.
- Added `fec/legislation/sync_sentinel_bill_ledger.py`.
- Added `fec/sync_sentinel_bill_ledger_artifact.cjs`.
- Added `fec/tests/legislation/test_sentinel_bill_workbook_sync.py`.
- Updated `fec/weekly_refresh.py` to run open-universe discovery before bill refresh.
- Updated `fec/run_pipeline.py` to verify, persist to Excel, then build legislative downstream artifacts in the same cycle.
- Updated `fec/legislation/build_archive_legislative.py` to consume only Excel rows marked `Scoring Eligible`.
- Updated `fec/audit/dashboard_integrity.py` to hash the collector rows, pending queue, Excel ledger, and receipt.
- Updated `fec/moneyball_core.py` to safely read standards-valid sparse Excel rows.

## Remaining work

1. Complete the first fresh `refresh_legislation_discovery.py` network run and review its delta against the July checkpoint.
2. Adjudicate new pending candidate IDs; do not auto-score broad-search matches.
3. Run the governed legislative numeric-workbook recomputation when newly verified measures should change the legislative rank pillar. Current rank delta is intentionally zero.
4. Reconcile the legacy workbook stance display column with `category_stance.json` without reintroducing formula-cache corruption.
5. Resolve or explicitly ratify the 30 full-body audit failures, especially stale press receipts, email package hashes, vote-lean freshness, production culling state, and the system manifest.

## Key artifacts

- `Sentinel Bill Ledger.xlsx`
- `data/engine/sentinel_bill_workbook_receipt.json`
- `outputs/sentinel_bill_ledger_20260904T011145Z/Sentinel Bill Ledger.xlsx`
- `Moneyball Dashboard.html`
- `cu-member-desk.html`
- `Moneyball.html`
