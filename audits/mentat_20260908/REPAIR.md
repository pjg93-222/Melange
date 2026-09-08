# Mentat repair and validation — September 8, 2026

This repair implements the findings in the historical [review](REPORT.md). It covers Mentat collection, the local upload console, modern industry Excel reports, and the separate attributed-spending workbook. The root Moneyball influence model and historical dated workbook vintages were not rebuilt.

## Corrections

- Support, opposition, and contribution/other activity remain distinct. Party totals exclude opposition, and opposition is never credited to an inferred rival. The congressional top 100 is selected after filtering to House and Senate; activity rankings can still be raised by opposition and are labeled as activity.
- Downstream dates retain the full year. Both first and last dates are validated. Amendment identities include transaction year so repeated identifiers from different years are not collapsed.
- Current same-cycle FEC committee registrations take precedence over stale receipt types. ActBlue and WinRed are classified as hybrid Carey committees. Ordinary registered PACs have a separate Other PAC category. Unresolved classifications retain a review ledger.
- Unservable API queries fail visibly after bounded retries and smaller-page recovery. They cannot manufacture a completed zero. Blank/repeated source IDs, pagination shortfalls, invalid resumed checkpoints, changed source databases, and conflicting shard records fail validation. Corporate filing-version metadata survives merging.
- Verified current API checkpoints supersede overlapping legacy query counts only when matching fetched/stored counts and successful-response stamps establish completion. Older incomplete or unstamped checkpoints remain warnings. No historical checkpoint is retroactively certified merely because a workbook builds.
- Report caches bind input content and output hashes. Code or source changes during export prevent publication. Full CSV audit companions are produced on cache hits too; a manifest binds each CSV, the exact payload, and its workbook. Empty outputs replace stale CSV rows.
- The local console accepts canonical names and aliases from CSV, TSV, or XLSX, previews the roster, and launches the existing collector. It shows checkpoints, sample stored records, retries, source ages, report hashes, and quality warnings. Polling preserves expanded sections. Higgsfield supplied the earlier visual layout reference; data verification uses repository code and source records.

The historical Crypto/Sherrod Brown counterexample now reconciles: 2023–2024 committee activity is $66,472,946, including $63,771,343 opposition and $395,753 explicit support. Democratic activity is the $2,701,603 non-opposition remainder. This is associated committee activity, not traced company funding.

## Keys and collection performed

The user's recorded FEC keys were recovered from local session records and tested with read-only FEC requests. Nineteen distinct keys are retained in user-scoped Windows DPAPI storage at `%LOCALAPPDATA%/Mentat/credentials/fec-keys.dpapi`: 15 validated successfully; four returned HTTP 403 and are disabled. Disabled keys stay encrypted and are excluded from workers. Import is atomic and serialized across processes. Keys are not stored in Git, report receipts, browser responses, or worker command lines. Existing user-authored session history was not rewritten.

Seven targeted company/cycle tasks were recollected: Binance US and Foris Dax Inc for 2022, 2024, and 2026, plus Bitnomial 2022. All seven succeeded with 30 requests and no retries. Crypto's accepted-row count increased from 6,063 to 6,091. Bitnomial 2022 returned a verified zero. The new database is a separate frozen snapshot; original databases remain available.

This was a targeted recollection, not a fresh census of every company, employer spelling, donor, and filing. In particular, older Fintech and some other checkpoints remain unverified. Their completeness and zero-provenance warnings are carried into the workbook and console. A populated cell or successful Excel audit does not establish complete FEC capture.

The remaining collection evidence gaps are specific: Fintech's 174 older API checkpoints lack the new successful-response stamp, and Polymarket 2022 lacks verified-empty evidence. Telecom has 116 of 331 stamped, reconciled API checkpoints; overlapping older counts cannot all be superseded safely. P&C retains Zurich Insurance count discrepancies (2024: 2,325 stored versus 2,434 reported; 2026: 944 versus 984) and an unverified-empty Berkshire Hathaway 2026 cell. These are unresolved historical coverage issues, not silently corrected data. The next collection pass should prioritize these cells before making completeness claims.

## Downstream depth and interpretation

Official committee, candidate, authorized-committee linkage, candidate-activity, and intercommittee transaction snapshots were refreshed for the 2022, 2024, and 2026 cycles. Source receipts retain URLs, SHA-256, ETag, Last-Modified, and retrieval/check times. The curated leadership links retain their previous timestamps and were not independently refreshed. Download dates are not verified filing data-through dates.

The transfer index processed 33,930,408 OTH rows. Outgoing cash-transfer codes 24G and 24K enter the graph; incoming mirrors, memo rows, and independent expenditures are excluded from transfer edges. Latest filing versions and exact source IDs are reconciled. Actual indexed sources had no malformed rows or invalid transfer dates/amounts under these checks. See the [FEC intercommittee file description](https://www.fec.gov/campaign-finance-data/any-transaction-one-committee-another-file-description/) and [transaction codes](https://www.fec.gov/campaign-finance-data/transaction-type-code-descriptions/).

Transfers are followed through at most three edges, stopping at principal/authorized candidate committees. One previously missing path is SMP (`C00484642`) to WINSENATE (`C00865444`): 38 reported 2024 cash-transfer records totaling $312,850,000. This identifies a committee relationship; it does not trace Crypto's $500,000 SMP contribution to a particular candidate.

The existing beneficiary views show funded committees' activity. Separate conditional pro-rata estimates allocate nonnegative root funding across positive observed candidate activity and cash transfers. Every modeled root reconciles estimated activity plus unresolved funding. Cycles, unknown outflows, ambiguous candidate links, depth limits, and the per-root traversal cap stay unresolved. Negative net funding is separately recorded; negative activity does not enter weights. Unobserved operating expenses and retained cash are not modeled. These estimates are neither traced dollars nor guaranteed lower bounds. Company views may share committees and must not be added as unique industry spending.

The new attributed workbook separates observed direct contributions, conditional non-opposition estimates, and conditional opposition. Its combined column is direct plus conditional non-opposition only. It replaces the old rival-credit and “floor” interpretation with an explicit methodology and coverage ledger.

## Efficiency and regression evidence

The same 6,091-row Crypto input built in 125.703 seconds after using the existing batched Excel import path for larger downstream tables, versus 254.848 seconds before. Node construction fell from 138.126 to 18.313 seconds, with a 3 GB heap instead of 8 GB. Both workbooks contained 349,880 formulas and the same included cycle totals: $1,588,786.23, $117,122,787.57, and $90,516,116.41. This is a measured Crypto workload, not a universal speed guarantee.

Large JSON exports now use Python validation and a compact formula-fact projection before Node construction. The complete enriched payload remains unchanged and checksummed; the projection retains the financial and identity inputs required for formulas and all downstream audit arrays. This removes the V8 single-string limit from the verified large builds. Disk-backed, batched SQLite transfer indexing and content-addressed caches avoid retaining the entire OTH corpus in memory or reparsing unchanged sources. API concurrency respects memory, available keys, and a shared primary/recovery limit.

The Python suite passed 73 tests, followed by passing audit-bundle and consolidated-warning regressions (75 total tests exercised; the updated 14-test console suite also passed). R checks passed for API collection, browser pagination, ingest, SQLite lane locking, beneficiary helper parity/ranking/dates, report formulas/vectorization, and export-progress guards. PowerShell workbook guard tests and JavaScript syntax checks passed. Independent workbook audits compare source facts, company totals, bridge activity, directions, party partitions, ranking coverage, date validity, root conservation, and cached Excel errors. The consolidated workbook is independently compared with the bound full CSVs.

## Reproduce and operate

The restarted console lists all ten verified reports, with matching report hashes and separate opposition columns. Its consolidated download matches the independently audited file byte for byte. The desktop and 370-pixel layouts were checked with no horizontal overflow or captured browser errors; expanded quality warnings remained open across polling updates.

Launch the local console with `mentat/app/Start-MentatApp.ps1`; it runs at http://127.0.0.1:8802. See [app instructions](../../mentat/app/README.md). Entering names does not start collection until Start collection is pressed.

The maintained tools are `refresh_fec_sources.py`, `build_industry_report.ps1`, `build_attribution_report.py`, `verify_repaired_reports.py`, and `verify_attribution_report.py` under `mentat/tools`. Run source refreshes into a new snapshot directory, then activate only a complete set. Build from a frozen database; use `-CycleLabel` for individual large cycles. The Python tools use the bundled runtime, and report generation also requires R, Node/artifact-tool, and Excel finalization.

Machine-readable local receipts are retained in `audits/mentat_20260908/`, `mentat/.cache/repair-20260908-databases/`, `mentat/.cache/repair-20260908-recollection/`, and each report's `.audit` directory. The databases, bulk files, generated Excel/CSV artifacts, and credentials are intentionally outside the code commit.


## Published verification receipts

Nine industry workbooks covering seven industries and all 21 industry/cycle combinations passed independent audits, along with the consolidated attributed workbook. Previous modern reports were archived before replacement. The app lists the rebuilt set separately from historical collection runs.

| Workbook | Beneficiary rows | Data-quality warnings | SHA-256 |
|---|---:|---:|---|
| Crypto Industry Spending Overview.xlsx | 2,171 | 1 | `5eb53b826dbc2c83f5d2d2c0799065583c8cbe00466dfafd652c96f0d4620303` |
| Fintech Industry Spending Overview.xlsx | 2,615 | 5 | `58e19076488fd7b51e0a7ef1b2ed9f50e39b96b7ca997c578780654a9b4a21a0` |
| Credit Union Industry Spending Overview.xlsx | 3,100 | 1 | `30bd5d32ed213f6eae1ca548ec80decb13e82381cb9883da1eb72daa9da5bb86` |
| Community Banks Industry Spending Overview.xlsx | 2,688 | 1 | `07f7565f3f811e6b5fda8b99787cb359f634dab77a75e9d8685ce9d0be35a9e3` |
| Telecom Industry Spending Overview 2023-2024.xlsx | 1,100 | 3 | `b2edfce7c915c394e8bed767ab4e5ec3dbc71ae32fcae170bd320b193052b49d` |
| Telecom Industry Spending Overview 2021-2022.xlsx | 1,100 | 3 | `22e88a83dd34697d2c53be3c46e6ff5e18b38a5dc95fdc8307cdb1298cd08fb2` |
| Telecom Industry Spending Overview 2025-2026.xlsx | 1,100 | 2 | `0077253f97ee4b60efdb29e2fd8263799e75762d3ac9bcb4eac540d186a0ce98` |
| Credit Arms Industry Spending Overview.xlsx | 3,184 | 1 | `a81ff911d47aac98396ee13b891f3145b09b7dbc969d781b7c9a4ae5131f7bcc` |
| Property & Casualty Insurance Industry Spending Overview.xlsx | 3,200 | 4 | `593fbbdd947b075e468959e893b765889f1e2716870d316df1714974491658a2` |

The consolidated workbook contains 26,897 unique industry/cycle/candidate summaries. Its hash is `f6adb83507b2c77693099b2ede90b4dce73fe5555b25395ec74d5b2fb8011701`. All 21 industry/cycle combinations are present, with opposition excluded from the combined non-opposition estimate.

Warning counts are not audit failures: empty categories/cells may be legitimate, while unverified checkpoints require recollection before a completeness claim. Full warning details remain in each workbook and the local machine-readable receipts.
