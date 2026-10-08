# GovInfo overlay and measurement reconciliation receipt

Status: **PASS**  
Completed: 2026-09-08 21:07 America/New_York  
Branch: `main`  
Staged changes: none

## Overlay and live ledger

All 22 adjudicated candidates are reconciled in the [decision-level receipt](live_receipt/RECEIPT.md). Fourteen false positives and six held measures remain visible but contribute zero. H.R. 10082 is admitted and contributes two live ledger rows: Janelle Bynum receives +3 as sponsor and Young Kim receives +2 as original cosponsor in Charter Modernization. H.R. 10230 is held because its credit-union direction is ambiguous and contributes zero.

The source-to-dashboard receipt passes with the overlay, routing audit, archive, member desk, ranking data, primacy factors, workbook, and both dashboard aliases hash-bound. The measurement audit executed **83,505** checks with zero errors:

| Layer | Checks |
|---|---:|
| Legislative math | 5 |
| Adjudicated routing | 19,525 |
| Headline math | 1,600 |
| Dashboard surfaces | 16,526 |
| Primacy math | 3,199 |
| Label assignments | 19,195 |
| Engine inputs | 20,787 |
| Workbook | 2,668 |

## Primacy, rank, and labels

The industry CU board now uses the same canonical primacy authority as every other CU surface. This reconciled 369 displayed positions. Main headline ranks and canonical primacy positions did not change merely from replacing the divergent industry-only board.

Catherine Cortez Masto remains headline rank **46** and canonical CU primacy rank **18**, Tier 2. Her industry page moves **27 → 18** and its factor moves **0.523485 → 0.550714** because that page now consumes the canonical board. Her stale displayed legislative raw value is corrected **0.937960 → 0.682892**; the live legislative percentile remains **0.733080**.

Existing label wording and thresholds are preserved. Seven assignments were reconciled from adjudicated evidence:

- Brandon Gill, Derek Schmidt, Michael Rulli, Riley Moore, and Tim Moore: Data Privacy & Cyber, Ally → Champion.
- Margaret Hassan: TCPA, Ally → Champion.
- Jack Reed: Payments, Lean Skeptic → True Neutral.

## Self-updating chain and presentation

Congress.gov bill intake, GovInfo/document routing, money, movement/network inputs, category scores, primacy, labels, engines, workbook, dashboard, live alias, and email package are connected through the guarded refresh chain. The source-to-dashboard audit is **PASS**. The current unattended classifier cadence remains weekly.

The ACU typography and purple pattern remain intact. Only the social-network canvas is now a near-black inset; its gold clusters and teal routes retain separate evidence colors. This was verified live with 17,646 records loaded.

## Validation

- Focused supplemental-adjudication suite: **151 passed**, plus **7 subtests passed**, zero failures.
- Legacy workbook integrity: **22 passed**, zero formula errors.
- Full-body integrity audit: **567 passed**, zero failed; manifest agreement **305 checks**, zero failed.
- Dashboard aliases are byte-identical: SHA-256 `20ccdd87161b3eea54cd38c144c448a95c50095cfd44f8e30c1a67fac3baab78`.
- Unrelated worktree changes were preserved. No stash, reset, merge, staging, or commit was performed.

Machine-readable reconciliation: [reconciliation.json](reconciliation.json)  
Full audit result: [rebuild_result.json](rebuild_result.json)  
Source-to-dashboard receipt: [source_to_dashboard_receipt.json](../../data/engine/source_to_dashboard_receipt.json)
