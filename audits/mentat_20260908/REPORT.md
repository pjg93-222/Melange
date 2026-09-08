# Mentat collection and workbook review — September 8, 2026

**The sampled contribution tables reconcile, but the downstream outputs should not be certified as complete or correctly interpreted.** Three published industry workbooks still contain an older support/opposition treatment and malformed downstream dates. The current source code contains fixes for those two problems, but a source fix is not proof that an exported workbook was rebuilt. Committee-to-committee transfers are outside the inspected downstream collector, and the Super PAC category includes an explicit custom conduit rule.

This was a read-only review of the Crypto, Fintech, and Credit Union published industry workbooks; the staged Crypto workbook; the separate Attributed Industry Spending workbook; the three current industry JSON payloads and their collection databases; and the latest saved resilient Fintech run. It is not a certification of every industry, every filing, or current FEC coverage. No existing workbooks were overwritten and no live collection was launched. Higgsfield supplied a visual design reference for the app; all data findings below come from local source code and workbook evidence.

The reproducible evidence, including full file paths, SHA-256 hashes, row references, and counts, is in [evidence.json](/C:/Users/pgoff/Mentat/audits/mentat_20260908/evidence.json). The read-only diagnostic is [audit_collection_outputs.py](/C:/Users/pgoff/Mentat/mentat/tools/audit_collection_outputs.py).

**1. Published downstream party totals include opposition to that party's candidate.**

In [Crypto Industry Spending Overview.xlsx](</C:/Users/pgoff/Mentat/reports/Crypto Industry Spending Overview.xlsx>), `Beneficiary Summary!E1573:Q1573` identifies Sherrod Brown, 2023–2024, with $66,472,946 Downstream Activity and the same $66,472,946 Democratic Activity. Reconstructing the linked Industry-view committee/candidate rows gives $63,771,343 of opposition, $395,753 of explicit support independent expenditures, and $2,305,850 of contribution/other activity. The non-opposition remainder is $2,701,603. These are associated committees' activity, not $66 million of crypto-company dollars given to Brown.

The same problem is present in the published Fintech and Credit Union books. Fintech `Beneficiary Summary!607:607` assigns $62,383,262 to Republican Activity for Mehmet Oz in 2021–2022, including $60,635,506 opposing him. Credit Union row 991 assigns $47,648,229 to Republican Activity for Oz, including $45,914,973 of opposition.

| Published workbook | Industry-view candidate/cycle rows with opposition | Opposition contained in those rows |
|---|---:|---:|
| Crypto | 144 | $879,434,637 |
| Fintech | 188 | $793,044,082 |
| Credit Union | 180 | $757,296,594 |

These amounts overlap across industry views and must not be added together as unique political spending. The old summaries lack the separate Support Activity and Oppose Activity columns. Current [finalize_crypto_excel.ps1](/C:/Users/pgoff/Mentat/mentat/tools/finalize_crypto_excel.ps1:517) excludes opposition from the party totals. The staged Crypto book has the new columns and the corrected Brown party calculation, but its underlying contribution totals also differ substantially from the published book. Promoting it without reconciling the input versions would change more than the display formula. The builder's descriptive sentence at [crypto_workbook_builder.mjs](/C:/Users/pgoff/Mentat/mentat/tools/crypto_workbook_builder.mjs:2188) still says party totals count only SUPPORT; the current formula also includes contribution/other activity and corrections.

**2. The Super PAC bucket is a reporting convention, not a pure FEC committee-type classification.**

[report.R](/C:/Users/pgoff/Mentat/mentat/R/report.R:2392) explicitly maps ActBlue (`C00401224`) and WinRed (`C00694323`) into Super PAC with category source `user_rule:registered_conduit_super_pac`. This is an existing named user rule, and tests enforce it. The local committee maps identify both as type V, rather than the ordinary O/U Super PAC types. FEC distinguishes independent-expenditure-only committees from hybrid committees with separate accounts. See [FEC PAC classifications](https://www.fec.gov/press/resources-journalists/political-action-committees-pacs/).

In the published Industry-view Recipient Lists, this custom rule accounts for $57,579.54 in Crypto, $444,645.84 in Fintech, and $397,314.62 in Credit Union across the three cycles. These are workbook-version amounts; current JSON payloads sometimes differ. Examples are Crypto Recipient List rows 28 and 90, Fintech rows 7 and 83, and Credit Union rows 6 and 7. The app now discloses the rule. A future category change should preserve both the official FEC type and the custom reporting category so users can choose the intended comparison.

**3. Downstream coverage stops before intercommittee transfer chains.**

The inspected collector reads local `pas2` committee-to-candidate files and requires a candidate identifier. It does not traverse the separate committee-to-committee transfer dataset. FEC describes `pas2` as including contributions and independent expenditures; it should not be described as omitting all independent expenditures. The separate transfer records and the distinction between these files are documented in [FEC bulk data](https://www.fec.gov/data/browse-data/).

For example, the current Crypto payload records $500,000 of 2023–2024 funding to SMP (`C00484642`, official type O), but has no included downstream activity for that committee/cycle. The inspected local `pas224` source also has no rows for that source committee. This is an unresolved destination, not evidence that the committee did no political spending. The audit does not establish where that specific $500,000 ultimately went.

[fec_build_beneficiary_tables](/C:/Users/pgoff/Mentat/mentat/R/fec_beneficiary.R:670) associates a company's funded committees with their full same-cycle candidate activity. It does not scale that activity by the company's contribution. Company views can therefore repeat the same committee activity. They are useful context, but summing them does not produce unique industry-attributed spending.

**4. The separate attributed workbook uses an estimate that cannot be treated as a guaranteed floor.**

[Attributed Industry Spending.xlsx](</C:/Users/pgoff/Mentat/reports/Attributed Industry Spending.xlsx>) contains 13,232 data rows. Its sole sheet's cell A2 describes proportional pass-through allocation and treats spending against same-race rivals as working for the member. It explicitly labels pass-through as an estimate, but also calls both direct and estimated spending floors. Restricting the company universe can undercount a sector; it does not make a proportional recipient allocation a mathematical lower bound. A recipient's estimated share can exceed the amount actually attributable to those companies.

The workbook's cached TOTAL equals DIRECT plus PASSTHROUGH within a cent, rows sort descending within industry/cycle, member/industry/cycle keys are unique, and displayed largest-committee shares lie between 0 and 1. Those are arithmetic checks, not validation of attribution. The generating source and a complete allocation ledger were not located in the inspected repository paths, so rival selection, full denominator construction, and conservation across recipients remain unverified. One negative direct/estimated row exists (6635); negative values alone are not proof of error because corrections and refunds can be legitimate.

**5. There are date, classification, and ranking gaps.**

Published Downstream Activity sheets contain 801 malformed first/last-date cells in Crypto, 1,054 in Fintech, and 1,512 in Credit Union, with years such as `0021` and `0022`. Examples: Crypto N624:O624, Fintech N107:O107, Credit Union N245:O245. Current [fec_beneficiary.R](/C:/Users/pgoff/Mentat/mentat/R/fec_beneficiary.R:351) has a versioned parse fix that preserves leading zeros in the original MMDDYYYY values; the staged Crypto export has no such impossible-year cells. Legitimate prior-cycle dates were not counted as malformed.

Published included contributions still classified Unclassified total $72,688.23 in Crypto, $75,409.23 in Fintech, and $126,998.87 in Credit Union across the three cycles. These dollars are included in the overall totals, but their recipient categories are unresolved. Credit Union's unresolved portion is approximately 12.1% of its $1,050,267.90 included total.

The current [congressional summary filter](/C:/Users/pgoff/Mentat/mentat/R/fec_beneficiary.R:707) ranks all offices before filtering House/Senate and retaining ranks at most 100. Reconstructing the current Crypto payload yields only 98, 90, and 95 congressional candidates for 2022, 2024, and 2026, despite at least 100 being available each cycle. The equivalent Fintech counts are 98/93/98 and Credit Union counts are 98/95/98. If the intended output is the top 100 congressional candidates, the office filter must precede ranking. Also, a rank based on total activity is an activity rank; opposition can raise it, so it is not a rank of financial benefit.

**6. A completed collection certifies planned searches, not all available political money.**

The latest saved resilient Fintech run (`20260723T233744-16884`) has 30 completed company/cycle tasks and seven successful saved coverage checks. The current Fintech database has 174 API work units, all marked fetched and stored complete. This supports completion of the planned search grid at collection time. The current Crypto and Credit Union payload databases use legacy collection history without that same API-progress evidence.

The normal API lane disables the separate phase-2 name expansion at [collect_api_lane.R](/C:/Users/pgoff/Mentat/mentat/tools/collect_api_lane.R:359). It searches the planned employer variants and corporate names; missing employer information and aliases outside the roster can still create omissions. The latest Fintech run also records that its optional bulk employer superset was absent. The legacy G8 completeness guard can warn rather than fail when checkpoints are unavailable. None of these receipts independently establishes comprehensive capture of donor identity, amendments, every alias, or downstream transfers.

The reviewed collections and source snapshots are from July, not September. The local 2025–2026 downstream file was modified July 19 and committee master July 22. File modification dates are not verified data-through dates. The app polls collection progress every three seconds, but that does not itself refresh the underlying FEC bulk files or make reports current to today.

**What passed and what to repair next.** All nine contribution cycle tables in the three published books reconcile Analysis Amount to included raw amounts and Company List totals. No duplicate Source IDs, descending transaction-date sort violations, or standard cached Excel error strings were found in those tables. Excel was not recalculated during this audit. The 13 offline console tests passed, JavaScript syntax passed, the existing beneficiary helper parity test passed (5,000 randomized cases and 15,000 parity rows), and the revised browser UI was checked at desktop and 370-pixel width with no captured browser errors.

Repair order: reconcile and pin source versions before rebuilding the outdated workbooks; validate support/opposition calculations and dates on the rebuilt artifacts; resolve or explicitly retain the conduit reporting rule and unclassified recipients; filter congressional candidates before ranking if top-100 Congress is intended; then add separately auditable transfer edges, freshness receipts, and allocation reconciliation. Keep direct contributions, committee activity, and estimated attribution visibly distinct throughout. Existing reports remain available for comparison, and the app now flags old direction layouts rather than implying that a completed run validates their interpretation.
