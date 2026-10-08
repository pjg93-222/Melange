Extensive downstream measurement review — September 20, 2026

Implemented systemic corrections across collection, PAS2/OTH ingestion, network reach, workbook staging/export, and console display. This review extends the first implementation; no production reports were rebuilt, no live FEC collection was performed, and no running console was restarted. Existing unrelated workspace changes were preserved.

The review found and corrected these failure paths:

| Failure | Correction and verification |
| --- | --- |
| Blank candidate identity silently removed observed PAS2 dollars | Default `count_all` retains non-memo observations in an unidentified bucket with an unverified flag. The separate allocation model reserves unidentified activity instead of assigning it to a person. A preserved-baseline fixture changes $0 to $123.45. |
| Identical bulk files in different cycles could share a parsed cache | Cycle IDs now participate in the cache signature; parser version increased to 7. A two-cycle identical-file regression verifies separation. |
| Stale OTH edges could survive a changed raw source | Verify the raw source SHA-256 when available, include raw OTH in build fingerprints and exported source hashes, and disclose stale-index coverage instead of traversing it. Missing raw data does not invalidate otherwise hash-bound saved edges; its absence is explicit. |
| Industry net refunds could hide a positive company’s downstream network | Discover routes from positive company roots and deduplicate their union for the industry view. Preserve signed funding separately. Synthetic industry activity changes $0 to $5,565 while funding remains negative. |
| Full Data workbook inherited the Overview’s top-100 cutoff | Preserve the complete bridge before presentation filtering. The Data workbook now includes a unique Network Candidate Activity table and a separate company-association bridge. Synthetic full detail changes $5,550 to $5,565. |
| Shared company associations could be mistaken for additive spending | Unique network facts count 105 candidate rows totaling $5,565; two company associations legitimately contain 210 rows totaling $11,130. Workbook guidance explains the overlap. Receipt, transfer, activity, and allocation measures remain separate. |
| Exporters dropped uncertainty fields | Carry unverified counts, unresolved counts/dollars, and repeated-itemization counts through R staging, Data Excel, Overview Excel, and deferred Overview sidecars. Verify actual temporary Data workbooks and Overview row/header mapping. |
| Repeated saved source IDs could double count; conflicting units could silently select the first | Deduplicate exact repeats of the same nonblank source ID, reject conflicting observations with the same ID and conflicting committee/cycle units within a snapshot file, exclude explicitly marked notices, and retain equal-dollar observations with distinct IDs. |
| Candidate payments could disappear without a recipient committee ID | Measure Schedule B candidate payments using the known candidate identity. Retain their own contribution/other classification in summaries, graph data, and maps. Candidate payments remain terminal in temporal tracing. |
| A terminal candidate row could swallow a separate PAC transfer to the same recipient | Keep terminal candidate payments and traversable PAC transfers distinct. Also prevent an authorized candidate root from opening OTH traversal. |
| Descendant collection failures could discard successful roots or evade the request budget | Preserve successfully collected roots, count failed attempts against the budget, and disclose failures and the uncollected frontier. Root failures still stop publication. Validate summaries before publishing new snapshots. |
| Missing source comparisons or totals looked like zero | Snapshot-only activity comparisons identify the missing workbook partition; missing financial values remain unavailable. Reject a selected cycle with no saved financial coverage. |
| Unknown directions and candidate gifts could appear as opposition/support | Keep Support, Oppose, Contribution/Other, and Unknown separate. Maps retain candidate gifts in total activity without inventing a Schedule E support classification. Conflicting saved party labels remain visible instead of selecting the last one. |
| Temporal search limits and empty export bodies were misleading | Disclose actual temporal depth-limit frontiers; show collection gaps in the evidence pane. Avoid hydrating empty bridge sidecars or assigning formulas to absent Excel table bodies. |

The unchanged preserved Fairshake snapshot was replayed through both the saved baseline and current console measurement code. Every compared candidate/direction total was unchanged in this second review. Andy Barr (`H0KY06104`) remains:

| Cycle | Before | After | Delta |
| --- | ---: | ---: | ---: |
| 2024 | $106,708.00 | $106,708.00 | $0.00 |
| 2026 | $7,170,138.40 | $7,170,138.40 | $0.00 |

The two equal $3,579,621.20 observations in 2026 have distinct source IDs and remain distinct under `count_all`; the $10,896 observation also remains. There is no extra multiplier from shared transfer routes. These are provisional observed committee expenditures, not proof of unique campaign costs or donor-attributed dollars. The preserved R replay also passes and retains the earlier direct-only versus reachable-network algorithm ledger.

Coverage remains limited. The saved network reaches two 2024 committees without snapshots (`C00476978` and `C00774463`). Its 2026 saved financial windows end July 31, 2026. A read-only scan of current PAS2 bulk files found no non-memo blank-candidate rows for the reached Fairshake committees in either cycle, so that correction produces no measured dollar delta in this particular case. The positive synthetic deltas above are regression evidence, not historical published-report corrections. Published workbook deltas were not measured because the user requested implementation rather than rebuilding reports.

Observed network traversal is cycle-safe and uncapped by transfer depth. Temporal route analysis and the separately labeled allocation model remain bounded to three transfers and disclose unresolved frontiers. Collection defaults to 30 committee/cycle attempts and now exposes both failures and the budget frontier. Same-cycle reach establishes association, not dated donor-to-candidate tracing.

Validation passed: 178 Python tests across 11 suites; five R suites; two JavaScript behavior checks; one Chromium drawer test; preserved-source R replay; Python/JavaScript syntax checks and PowerShell parsing. The Data workbook tests generate and read back temporary XLSX files, including 105-candidate coverage and uncertainty columns. A complete production Overview build and Excel COM finalization were not run. The finalizer null-body change was syntax checked; live Excel execution remains a validation limitation.

Evidence retained in this directory:

- `preserved_evidence_ledger.json`: complete before/after candidate dollar ledger, Barr rows, missing frontier, source coverage, and PAS2 source hashes.
- `barr_measurement_ledger.json`: R algorithm replay with the original source rows and hashes; synthetic $1 funding roots trigger traversal and are not actual donor funding.
- `synthetic_dollar_ledger.json` and `replay_synthetic.R`: reproducible baseline/current synthetic deltas.
- `source_before.json`, `before/`, and `source_hashes.json`: preserved pre-review source files and before/after SHA-256s.
- `review_changes.patch`: this review’s source changes, separated from the already-dirty working tree.
- `test_results.json`, per-suite logs, and `verification.json`: validation receipts. `run_validation.py` and `replay_evidence.py` reproduce the offline checks.

Preserved Fairshake snapshot SHA-256 before and after: `ffee8b261b28fe15cd93f1b5c30b74d493a0b6a955baa22bc0e4a9cfb2af43fa`.
