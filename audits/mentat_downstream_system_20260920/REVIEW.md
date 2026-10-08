# Systemic downstream measurement correction

Implemented on September 20, 2026. No report rebuild, source refresh, published workbook replacement, or accepted-baseline change was performed.

## Confirmed defects and changes

- The exporter loaded descendant PAC activity but joined the beneficiary bridge only to directly funded committees. The bridge now joins the cycle-safe reachable network once per cycle/view/company/spending committee. Multiple funded roots, diamonds, cycles and direct-plus-indirect relationships cannot multiply candidate activity. Actual spending committee IDs remain the formula keys. Associated receipts stay at their actual recipient; an indirect spender can correctly have zero associated receipts.
- R report discovery stopped after three transfers. Observed activity discovery and its Transfer Paths evidence now follow the complete saved positive-transfer graph, stopping at authorized candidate committees. The separately labeled conditional allocation model retains its explicit three-transfer bound.
- The console could read descendant activity from a workbook but discard it when there was no saved API snapshot establishing the route. It now reads complete workbook Transfer Paths, collapses repeated representations of the same edge, rejects conflicting edge values and truncated route tables, and uses a saved snapshot's entire route partition when one is selected. The workbook hash already carried by the API binds workbook evidence; snapshot hashes remain separately displayed.
- PAC evidence collection previously required every committee to be manually named. It now follows recipient PACs automatically, once per committee/cycle, while treating candidate-linked gifts as terminal. A default budget of 30 committee/cycle units bounds collection; an uncollected frontier is recorded by committee and cycle as `collection_limit`. No live collection was run for this change.
- Overview and Data workbook producers now include Downstream Reach, Downstream Measurement and Downstream Sources. The audit CSV manifest includes these same ledgers. Measurement compares the old direct-only association and the new reachable association on identical current source rows, before top-100 display filtering. It is not a comparison against an earlier published workbook. PAS2 and transfer source fingerprints and active policies accompany it. The existing builder fingerprints the changed producers, so cached pre-fix payloads are invalidated.

## Andy Barr preserved-source replay

The replay selects candidate ID `H0KY06104` exactly from the saved Fairshake snapshot; it does not substring-match names such as Barry Moore. A synthetic $1 root-funding trigger exercises route discovery only. All candidate-spending dollars and transfer observations are copied from the preserved source.

| Cycle | Regular-report source rows | Direct-only association | Reachable observed activity | Algorithm delta |
|---|---:|---:|---:|---:|
| 2024 | 2 | $0.00 | $106,708.00 | +$106,708.00 |
| 2026 | 3 | $0.00 | $7,170,138.40 | +$7,170,138.40 |

Each amount appears once in the Industry view and once in its separate Company view; these views must not be added. The spender is Defend American Jobs (`C00836221`), reached from Fairshake (`C00835959`). The upstream transfer is not added to candidate activity. The two $3,579,621.20 observations in 2026 have distinct source IDs and transaction IDs; equal amounts do not establish a duplicate. Their preservation follows the current contradictions-only/count-all policy.

The snapshot reports House/KY-06 for the 2024 rows and Senate/KY for the 2026 rows while retaining the House-style candidate ID. The replay preserves those filed office facts. PAS2-only builds lack those filed office fields and depend on candidate-master metadata; this change does not independently resolve that coverage limitation.

Source SHA-256, verified unchanged before/after: `ffee8b261b28fe15cd93f1b5c30b74d493a0b6a955baa22bc0e4a9cfb2af43fa`.

Evidence: [source rows and replay input](barr_source_replay.json), [before/after ledger](barr_measurement_ledger.json), [hashes and coverage windows](verification.json). No claim is made that these replay deltas equal the deltas of a future complete PAS2 report build.

## Verification

106 targeted Python tests passed across capture, downstream network, enrichment, transfer versions, PAC evidence, graph API, Data-workbook output, payload projection and audit manifests. Three R suites passed: transfer evidence/version policy; downstream system tests and preserved-source replay; beneficiary helper parity (5,000 randomized cases and exact existing financial-column parity on 15,000 input rows). One Playwright downstream display test passed. Python compilation, JavaScript builder syntax, exporter R parsing and targeted whitespace checks passed.

Regression cases include multiple roots, direct and indirect reach of the same spender, diamonds, cycles, a fourth transfer, cycle isolation, signed edges, authorized-candidate stops, a zero-funded committee reached from another root, missing snapshots, snapshot/report route precedence, conflicting route values, capped displays, collection limits, and ledger/hash persistence through a temporary Data workbook, and cycle-specific ledger filtering.

The first legacy parity check found changed ordering of tied bridge rows. The producer now preserves the original ordering when no routes are supplied; the original financial columns and summary match exactly. The helper test also bounds data.table threads to avoid excessive parallel overhead. Existing expected-failure publication controls still reject corrupted financial facts.

## Limits

These are observed committee activities, not traced donor allocations or certified unique economic dollars. Existing attribution, memo and transfer-version rules remain in force, including provisional retention of distinct observations whose filing relationship is unknown. Existing snapshots and reports retain their collection dates and scope; API pagination completeness does not prove that every filing or route exists in those sources. Missing source files and collection-budget frontiers are coverage gaps, not measured zeroes. No live API collection, full production report build, Excel finalization, or deployed-server restart was performed. The Overview producer was checked structurally and for syntax; the Data-workbook writer was exercised with an isolated fixture.
