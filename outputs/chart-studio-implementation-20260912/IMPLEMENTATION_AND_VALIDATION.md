# Contribution Studio — implementation and validation

Mentat now has a local contribution-analysis workspace with a verified source reader, explicit accounting bases, field-driven queries, native charts, and ZIP maps. All eight industry datasets pass the guarded live API checks against the authoritative published cycle totals. Generated 2026-09-12T20:47:32-04:00.

Open [Contribution Studio](http://127.0.0.1:8813/contribution-studio?industry=Banking). The current local preview supports analytical queries, saved browser views and exports in read-only mode. Relaunching the normal Mentat desktop app loads the updated server and opens Contribution Studio through its console tab. [Usage and accounting guide](C:/Users/pgoff/Mentat/mentat/app/CONTRIBUTION_STUDIO.md).

## Verified included receipts

These are the published **included-receipt** amounts across the three available election cycles. They are not a certification that every receipt is a separate economic gift. Industry scopes remain separate; no cross-industry unique-giving total is asserted.

| Industry | 2021–2022 | 2023–2024 | 2025–2026 | All three cycles |
|---|---:|---:|---:|---:|
| Banking | $16,652,458.77 | $26,107,204.16 | $12,003,181.12 | $54,762,844.05 |
| Community Banks | $228,755.22 | $379,455.03 | $255,295.73 | $863,505.98 |
| Credit Arms | $8,778,979.26 | $9,677,525.39 | $5,475,940.60 | $23,932,445.25 |
| Credit Union | $369,423.16 | $779,088.35 | $273,494.14 | $1,422,005.65 |
| Crypto | $1,756,273.34 | $145,462,078.45 | $102,731,131.38 | $249,949,483.17 |
| Fintech | $1,891,559.66 | $3,859,524.56 | $4,052,807.09 | $9,803,891.31 |
| Property & Casualty Insurance | $5,240,339.66 | $7,857,445.42 | $3,589,580.51 | $16,687,365.59 |
| Telecom | $12,463,873.75 | $17,978,153.89 | $7,256,093.45 | $37,698,121.09 |

Every cycle agrees to the cent with both its pinned source payload and the current workbook's actual cached Total Giving rows. Company-by-cycle dollars also reconcile, using the existing display-name register for four Crypto aliases. The raw alias differences remain in the evidence. See [full data validation](C:/Users/pgoff/Mentat/outputs/chart-studio-implementation-20260912/data-validation.json), [guarded live API results](C:/Users/pgoff/Mentat/outputs/chart-studio-implementation-20260912/live-api-validation.json), [actual workbook reconciliation](C:/Users/pgoff/Mentat/outputs/chart-studio-implementation-20260912/published-workbook-reconciliation.json) and [company/cycle and source-only checks](C:/Users/pgoff/Mentat/outputs/chart-studio-implementation-20260912/source-only-observations.json).

## What changed

The reader builds facts from physical source identities and the pinned payload, rather than aggregating overlapping worksheet summaries. It coalesces repeated copies of the same source ID, preserves attribution conflicts and evidence, and stores monetary values in integer cents. Source IDs are not treated as unique economic gifts. Raw observations, included receipts, provisional original giving, the supported gross subset, and recipient-reported PAC activity remain separate bases.

This removes the confirmed chart-layer inflation: Banking's industry and company recipient summaries previously added to $109,525,688.10 even though each represented the same $54,762,844.05. Its 2023–2024 overview could sum three alternative breakdowns to $78,321,612.48 instead of $26,107,204.16. Multi-ZIP employee summaries could also copy the full amount into every ZIP. The new ZIP view uses the ZIP on each contribution observation. Raw Crypto observations can no longer silently replace the included basis and restore $92 million excluded from the five-row Coinbase/Fairshake example. The original reproduced cases remain in [the pre-fix research report](C:/Users/pgoff/Mentat/outputs/chart-studio-review-20260912/MENTAT_CHART_STUDIO_REVIEW.md).

The existing evidence engine also now keeps rejected company attribution excluded when metadata conflicts are present. Ambiguous filing versions are retained with their reasons; they are not arbitrarily deleted to force a smaller total. A zero supported gross subset does not establish zero giving. Unresolved exposure is absolute raw exposure, overlaps other views, and must not be added to the selected amount.

## Source integrity and the compact Telecom format

Workbooks are discovered only in the configured authoritative report folder. Workbook, payload and database fingerprints are checked. Recovered databases must match the complete accepted original financial universe, including records excluded from the payload. The seven recovered sources preserve 1,776,120 financial identities with no added, missing, changed or conflicting identities; Banking uses its exact original database fingerprint. Active uncheckpointed database writes and changed loaded code block queries. Each live response is bound to the workbook and database versions that passed these checks.

Telecom deliberately omits dates from its declared compact payload. An independent audit matched all 506,017 payload records to the preserved source in amount, donor, committee and election cycle. The adapter permits an absent date only for that explicit compact schema, after complete source verification, and requires the verified source date to fall in the payload's exact cycle. Present dates retain the strict comparison. No source amounts or published workbooks were rewritten. The seven already-verified caches were copied through an audited migration with unchanged complete fact-content hashes and original-cache provenance; only Telecom required a new build. See [the compact-format audit](C:/Users/pgoff/Mentat/outputs/chart-studio-review-20260912/chart-audit/TELECOM_COMPACT_PAYLOAD_REVIEW.md) and [cache migration receipts](C:/Users/pgoff/Mentat/outputs/chart-studio-implementation-20260912/cache-migration/receipt.json).

## Charts and maps

The Higgsfield-generated design reference guided the warm-white, charcoal and green workbench, implemented locally in HTML/CSS/JavaScript. The image-generation prompt contained a generic political-contribution interface brief; no private contribution records were supplied to Higgsfield. Its completed design job was `6ad8b067-7842-494d-be18-73435857a1ea`.

Dimensions, measures and colour define the query grain. Source filters precede grouping; grouped measure filters follow it. Bars, timelines, areas, scatter plots and tables use the returned aggregates, with separate axes for different measures. Missing periods remain gaps. Ongoing calendar cycles/years are labelled without claiming collection through today. Mark selection opens the matching source records, amounts, decisions and filing links. Undo and named views are local to the browser. Chart labels remain readable in narrow layouts, with scrolling contained inside the chart.

ZIP maps include all selected ZIP/state groups, with no top-N cutoff. Recorded state controls U.S. postal eligibility; foreign, missing and unrecognized states remain unmapped even if a postal code resembles a U.S. ZIP. Eligible state groups combine into ZIP marks, and drill-through retains the exact eligible-state selection. Grouped filters operate before that combination. State outlines and the 119th or 120th Congress boundaries are independent overlays. ZIP areas use Census ZCTAs, which approximate postal geography; they do not identify a donor's address or allocate money across overlapping districts. Missing geography retains its dollars, and deferred polygons are disclosed.

The final live Banking map showed $54,762,844.05 selected, $53,940,783.88 located, and $822,060.17 unmapped across 8,175 located marks. Changing between the tested congressional boundary editions preserved those amounts. The 119th-Congress view rendered 56 state/territory and 444 district/undefined-area paths. Geography requests contain public ZIP identifiers and layer choices, not contribution amounts. See [final browser validation](C:/Users/pgoff/Mentat/outputs/chart-studio-implementation-20260912/final-ui-validation.json).

CSV exports include all matching groups, signed dollars, filters, workbook/index/query fingerprints, and protections against formula injection or a source version changing mid-export. ZIP text retains leading zeros in the file; import ZIP columns as text in spreadsheet software. SVG/PNG exports retain legends, the displayed map viewport, accounting context, coverage and source notes. Large PNG exports stay within browser canvas limits.

## Validation and practical limits

Targeted accounting, source-integrity, HTTP, query-equivalence, chart, map and export tests pass. The final accounting/legacy engine suite passed 86 tests; source and workbook guards passed 18; HTTP contracts passed 13; the optimized query layer passed 10 tests spanning more than 100 reference-equivalent request combinations. Browser checks cover saved views, pagination, signed CSV values, source drift, foreign ZIP collisions, exact drill-through, viewport exports, mobile containment and desktop scrolling. These suites overlap in scope and are not combined into a misleading single count.

The optimized query layer reuses grouped results and reduces six fact scans to two. A measured Banking ZIP/state request returned 8,547 groups with the full amount preserved in 16.56 seconds during concurrent validation. This is a measured request, not a general latency guarantee. The largest first build plus reference checks took about 22 minutes; completed sources reuse prepared caches. See [query performance evidence](C:/Users/pgoff/Mentat/outputs/chart-studio-review-20260912/chart-audit/QUERY_PERFORMANCE_CLOSEOUT.md) and [live ZIP/state request](C:/Users/pgoff/Mentat/outputs/chart-studio-implementation-20260912/banking-zip-state-query.json).

Collection completeness, donor identity and economic uniqueness remain explicit limits. The application exposes supported evidence and unresolved decisions instead of treating missing evidence as zero or labelling provisional dollars as verified unique giving. The authoritative workbooks and raw source databases remain preserved. Existing unrelated working-tree changes were retained; this work was not committed or deployed publicly.

[Thorough Tableau/FEC/Census/HUD research](C:/Users/pgoff/Mentat/outputs/chart-studio-review-20260912/MENTAT_CHART_STUDIO_REVIEW.md) · [Backend accounting receipt](C:/Users/pgoff/Mentat/outputs/chart-studio-implementation-20260912/BACKEND_ACCOUNTING.md) · [Implementation guide](C:/Users/pgoff/Mentat/mentat/app/CONTRIBUTION_STUDIO.md)
