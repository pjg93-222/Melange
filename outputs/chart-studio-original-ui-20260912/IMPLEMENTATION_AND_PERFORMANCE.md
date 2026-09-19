# Original Chart Studio restored: accounting, geography and latency

The original Chart Studio is again the main interface at `/#chart-studio`. Its plum, ivory and gold styling, Data/Analytics pane, toolbar, shelves, Marks, Show Me and sheet tabs are preserved. Verified contribution analysis is integrated into these controls; Report worksheet remains a source choice. This supersedes the earlier separate-interface routing, while retaining the accounting and geography repairs documented in the earlier implementation report.

Open [the local original Chart Studio](http://127.0.0.1:8813/#chart-studio). This running preview is read-only for collection management and supports analysis, local saved sheets and exports. The normal desktop launcher loads the changed application on its next launch.

## Data and money

The chart reader uses physical source observations from verified report sources. It no longer adds alternative industry, company and recipient summaries together or copies an employee's full subtotal to every ZIP in an aggregated ZIP list. Integer-cent measures, record identity, source fingerprints and distinct-donor counts are retained through filtering, grouping, paging, charts and exports.

The confirmed Banking chart-layer inflation was twofold when industry and company summaries were combined ($109,525,688.10 instead of $54,762,844.05), and threefold for alternative 2023–2024 breakdowns ($78,321,612.48 instead of $26,107,204.16). Those views now query the same contribution facts at an explicit grouping level. [Original reproductions and Tableau/FEC/Census/HUD research](../chart-studio-review-20260912/MENTAT_CHART_STUDIO_REVIEW.md).

The default is **published included receipts**. Provisional original giving, the supported positive gross subset, raw observations and recipient-reported PAC activity remain distinct. Included receipts are not a certification of unique economic gifts: intermediary stages and unresolved filing evidence can still overlap. Ambiguous evidence is retained and explained. Source amounts and authoritative workbooks were not rewritten to force smaller totals.

Every current industry passed both a cycle query and the original interface's default company chart through the guarded live HTTP API. Repeated requests returned identical results. All three published cycles reconcile to the cent, with these all-cycle included-receipt totals:

| Industry | Included receipts |
|---|---:|
| Banking | $54,762,844.05 |
| Community Banks | $863,505.98 |
| Credit Arms | $23,932,445.25 |
| Credit Union | $1,422,005.65 |
| Crypto | $249,949,483.17 |
| Fintech | $9,803,891.31 |
| Property & Casualty Insurance | $16,687,365.59 |
| Telecom | $37,698,121.09 |

These are separate industry scopes, not a combined unique-giving total. [Final live API receipts](live-api-validation.json), [workbook reconciliation](../chart-studio-implementation-20260912/published-workbook-reconciliation.json), [source and accounting implementation](../chart-studio-implementation-20260912/IMPLEMENTATION_AND_VALIDATION.md).

## Charts and geography in the existing interface

Dimensions on Colour, Detail, Label and Tooltip define each mark's grouping. Source filters precede aggregation; grouped filters follow it. Statistical measures retain their source-level meaning instead of being aggregated a second time. Paging does not change population totals. Circle/scatter requires two measures; distribution charts explain their need for individual worksheet values. Time axes preserve missing periods. Projections and reference lines are separate from the contribution totals.

ZIP/state maps include every selected geographic group. State, congressional and ZIP-area overlays are independent of amounts. Congress 119 and 120 are explicit options. Eligible ZIP groups use Census ZCTA representative points, and foreign or unknown state codes remain unmapped. ZIP intersections do not manufacture district totals.

The final live original UI showed Banking's 8,547 ZIP/state groups as 8,175 located marks: $54,762,844.05 selected, $53,940,783.88 located and $822,060.17 unmapped. Switching from Congress 119 to 120 left these amounts unchanged. ZIP and state marks drill into the exact contributing source selection. CSV retrieves all groups and carries source/query fingerprints; a source change during inspection or export is rejected.

## Measured performance

| Measurement | Before | After | Interpretation |
|---|---:|---:|---|
| Banking cycle request, guarded HTTP | 13.713 s | 0.639 s; 0.105 s repeat | Same data selection; source/cache preparation already complete |
| Banking ZIP/state, new configuration | 1.830 s previous SQL plan | 0.496 s public Python call; 0.054 s repeat | All returned rows, totals and donor counts match; this new request was absent from response cache |
| Original default company chart, eight industries | — | 0.091–0.352 s; 0.092–0.121 s repeat | Live HTTP after preparing the exact default request for each source |
| Guided Graph, initial render and layout | 458.4 ms | 30.7 ms | Same offline 10,012-row browser fixture; 42 visible marks in both |
| Hidden table rows created on initial Graph render | 10,012 | 0 | All rows remain available on first expansion; subsequent expansion reuses them |
| Cold desktop launch | 4.413 s | 2.103 s | Median of three isolated synthetic-server launches |
| Managed process completion handoff | 2.007 s | 1.060 s | Median of three synthetic processes; exit now wakes the status wait |
| Shared-pool lane 32 ordinal delay | 7.750 s per invocation | 0 s | Direct mode's existing stagger and all request budgets retained |
| 25 original-page assets, transfer size | 437,416 bytes | 154,348 bytes gzip; 0 body bytes on 304 | Identical decoded files; assets still revalidate when changed |
| State/district geometry plus ZIP 02134, transfer size | 1,675,424 bytes | 570,558 bytes gzip | Identical decoded geometry; smaller transfer is not a universal timing guarantee |

The HTTP comparison uses the earlier [live API receipt](../chart-studio-implementation-20260912/live-api-validation.json) and this phase's [final receipt](live-api-validation.json). SQL and public Python measurements have different boundaries and are labelled accordingly. OS caches were not forcibly cleared. Render and launcher figures are fixture measurements, not promises of total application latency.

The compact Banking query fact table is 63.6 MB; its original 537.5 MB analytical index remains byte-identical. Every projected field is verified against its observation identity, and long detail fields are read only as needed. Population summaries and full responses have separate bounded caches. Index, query-code and projection-code fingerprints, WAL/journal checks, atomic writes and process locks prevent stale or competing results. All eight derived views and default chart requests were prepared before delivery.

The original UI reuses the current query for visual changes, caches alternate selections briefly, and caches geometry separately. Explicit source refresh invalidates browser results and member lists. Chart Studio starts with a light local handshake; collection polling and saved-evidence scans run when their views require them. A credential-status failure no longer prevents report analysis; actual collection authentication is unchanged.

The guided Graph delays full table construction until a disclosure opens, reducing its initial DOM from 40,432 to 349 descendants in the fixture. Exact values, full-table actions, row callbacks and complete exports remain available. The launcher checks a free port before attempting HTTP, avoids importing openpyxl twice, and preserves server/project/data-root/report-directory identity checks. Managed workers wake immediately on process exit and avoid redundant shared-pool staggering.

First use of a new or changed source still performs necessary validation. Banking's one-time compact projection took 17.3 seconds; the first authoritative index build can take substantially longer. A fresh server's first catalog verification measured 5.76 seconds, versus 0.14–0.16 seconds warm. Warm desktop reuse remained about 1.3–1.4 seconds; no improvement is claimed there. Remote FEC time, source copying and genuine R startup remain outside these measured savings.

Detailed receipts: [query performance](../chart-studio-implementation-20260912/QUERY_PERFORMANCE.md), [all-eight preparation](../chart-studio-implementation-20260912/query-prewarm-validation.json), [guided Graph rendering](../worker-startup-performance-20260912/GRAPH_RENDERING_PERFORMANCE.md), [desktop and worker startup](../worker-startup-performance-20260912/STARTUP_PERFORMANCE.md), [asset delivery](delivery-after.json), [server entry points](server-after.json).

## Validation

Focused validation passed for the financial source/workbook guards and original accounting fixes, 21 query acceleration tests (including more than 100 reference-equivalence comparisons), the 13 contribution HTTP contracts, 28 collection-console checks and five delivery/session tests. The query tests cover signed money, exact distinct identities, detail dimensions, filters, paging, source and derivative mutation, malformed caches, and concurrent threads/processes.

Original UI core/adapter and plot tests passed. Browser checks cover the restored shell, ZIP/state drill-through, both congressional choices, source refresh and drift rejection, leading-zero ZIP export, source-mode switching, label/fit query reuse, readability and lazy startup. The guided Graph browser fixture verifies every value in all five breakdown tables, negative values, row callbacks, table reuse, CSV/SVG exports and Show all rows. Seventeen focused startup/worker Python checks and the R fanout/transport fixtures passed. Test suites overlap and are not added into one total.

The final live browser verified the original Chart Studio, Banking totals and full ZIP coverage with no displayed error. Scoped diff whitespace checks passed. Existing unrelated working-tree changes were preserved. This work remains local and uncommitted; no active production collection was restarted.

[Usage and accounting guide](../../mentat/app/CONTRIBUTION_STUDIO.md)
