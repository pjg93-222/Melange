---
version: 1
slug: "visual-analysis"
primary_target: "mentat/app"
related_targets: ["mentat/app/templates/view_graph.html","mentat/app/templates/view_evidence.html","mentat/app/templates/view_insights.html"]
---

# Mentat visual analysis

## Direction contract — industry forecast extension, September 27, 2026

THESIS: Put dated growth and political assumptions beside two comparable forecast horizons, with the model's direction and ordinary p-value visible.

OWN-WORLD: Inherit the existing plum/teal/ivory console, serif headings, sans-serif labels and full-width Insights workspace; no changes to Graph or PAC evidence.

STORY: Choose a supported research industry, enter assumptions for the remaining and next complete cycle, compare projected amounts and shares, then open evidence or export the exact scenario.

FIRST VIEWPORT: A Forecast giving action in the Insights header opens one full-width workspace. Industry, as-of date and political model lead; two horizon columns hold inputs and resulting comparison rows. Long evidence stays in native disclosures.

FORM: Local extension of the existing Operate surface, not a new visual world; no concept seed or image comp required. Results name whole-industry scope, historical baseline and interval meaning.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Graph rollback — current user instruction

On September 21, 2026, the user rejected the redesign again and requested: “just revert Graph back to what it originally was.” Graph uses the saved pre-redesign composition, controls and shared Graph rules. Its summary totals precede the side-by-side recipient-type and candidate charts; the original controls, ten-row previews and multicolor bars are restored. The only subsequent Graph change is the user-requested company sparkline correction: it reads verified quarterly observations in one contribution query, not one Graph request per election-cycle year, and missing quarters remain gaps rather than zeroes. Insights was not reverted. The Graph direction, acceptance and captures below are historical and superseded by this instruction. Current Graph evidence is `outputs/graph-revert-20260921/restored-graph-1440.png` and `verification.json`; those captures predate the quarterly sparkline correction. Do not reapply the rejected Graph redesign.

## PAC rollback — current user instruction

On September 21, 2026, the user said the PAC tab “was better before.” PAC evidence now uses the saved pre-redesign `evidence.js` and `view_evidence.html` from `outputs/visual-analysis-implementation-20260921/pre-edit/`, with the original two-column geography/map-shell rules restored from the saved stylesheet. Shared shell improvements remain, with PAC-specific control typography restored. The later compact toolbar, summary/table subviews, embedded comparison bars, and selected-evidence rail are rejected. The PAC geography composition, measurements, acceptance claims, and captures below are historical and superseded by this instruction. Do not reapply the rejected PAC redesign.

Mode: Operate

Targets: `mentat/app/templates/view_graph.html`, `mentat/app/templates/view_evidence.html`, `mentat/app/templates/view_insights.html`, and their shared shell, styles, and runtime renderers.

The user's selected task is **Compare giving, then trace it to evidence.** The user approved all three visual references together and the written corrections in [the implementation prompt](../../outputs/visual-analysis-direction-20260921/implementation-prompt.md). The prompt's original proposal status predates that approval.

## Direction contract

**THESIS:** Let readable data comparisons lead, with exact evidence adjacent to the real selection. Filters and repeated methodological prose must not displace the principal visualization.

**OWN-WORLD:** Preserve the recognizable plum, teal, ivory, serif headings, sans-serif controls, and seven-workspace shell captured in [DESIGN.md](../../DESIGN.md).

**STORY:** Select a source and period, compare observed giving, select a mark, inspect its exact available evidence, and return without losing compatible scope. Reported PAC activity retains its independent accounting meaning.

**FIRST VIEWPORT:** Graph leads with sorted recipient bars; selected evidence joins the comparison when space allows. PAC geography uses a large real map linked to a ranking and selected-place records. Insights leads with a full-width supported cycle comparison, with generous supporting analyses below. Compact scope and source context precede the graphics.

**FORM:** The three user-approved Graph, PAC evidence, and Insights compositions guide the implementation together. No concept-seed key is asserted: these are the user's supplied and approved direction, with written financial and interaction requirements taking precedence over generated-image errors.

**FINISH:** unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Scope and evidence

Reference images: `outputs/visual-analysis-implementation-20260921/reference-graph.png`, `reference-evidence.png`, and `reference-insights.png`. They guide hierarchy and scale, not financial values, authoritative geography, or unsupported monthly comparisons. The runtime interface uses real HTML and data graphics.

Preserve all existing Graph scopes, multiple PAC panes and comparison, Raised/Spent, cycle/geography/routes/records/filings, all eleven Insights analyses and their controls, source inspection, and CSV/JSON export. Keep receipts, transfers, observed candidate activity, and estimates distinct. Unknown, negative, and observed zero states stay distinguishable. Same-stage and full-observed cycle amounts use actual returned values; waterfall components must reconcile in signed cents.

## Implemented composition

The corrected release restores the three reference compositions through live HTML, SVG, and existing evidence data. At desktop widths the shared workspace begins at the same 208px edge (180px sidebar plus 28px gutter), fills the remaining width, and has no centered maximum-width container. All seven workspaces use that alignment, including ultrawide layouts. Below 1100px the navigation becomes a horizontal row; below 761px the workspace uses 16px side gutters and controls reach at least 44px.

**Graph:** The main sorted recipient comparison shows six leading rows by default, with the existing count controls available. An unselected chart fills the row; a supported selection opens a 2:1 chart/detail composition from 1250px, stacking below that width. The company comparison occupies its own full-width row below. The selected detail shows a compact name, bold receipt amount, exact committee identity, source-record availability, Clear selection, and a full-width plum PAC evidence handoff. The independent accounting distinction remains visible. The downstream chart and route explorer remain in an initially closed native disclosure; the open compact desktop rail scrolls locally at a 680px maximum height, preserving the expanded explorer. The meaningful scope trail follows the scope line without a duplicate single-part industry label.

**PAC geography:** A selected desktop state uses a 330px map with its scale in a 140px side column, an adjacent selected-place evidence rail, and the five-place ranked comparison immediately below the map. The ranking precedes the reconciliation summary so all five marks remain in the first 1440 × 1000 viewport. The unselected desktop map and ranking share the available frame without reserving an empty evidence rail. Below 1250px, a compact selected-place amount, Clear selection, and View source records remain beside the map in document flow; the full record detail follows. The mobile map is 230px high. The collapsed scope summary retains the actual committee ID. Recipient names and amounts share the main line, kind/place appear beneath, and multiple actual filings use a native source-record disclosure. The record list scrolls locally with its existing paging; it retains actual record counts and links.

**Insights:** The full-width, contained cycle comparison leads, with Favorite recipients and What changed in two generous supporting columns below. These columns stack at 1100px and below. Labels and legends stay readable; displayed comparisons remain the supported full-observed and same-election-stage cycle values. Refresh remains beside Export and Sources. Scope, method, coverage, and source records stay available without surrounding each plot with repeated expanded prose.

Measured current release composition at 1440 × 1000, from `outputs/visual-analysis-correction-20260921/release-metrics.json`:

| State | Principal analysis | Supporting comparison / evidence |
| --- | --- | --- |
| Graph, unselected | Begins at y302; 1204px wide × 422px high | Company comparison begins at y740 |
| Graph, selected | Begins at y302; 792px chart + 396px detail | Company comparison begins at y746 |
| PAC geography, selected | Begins at y296; 792px main + 396px evidence | Five-place ranking spans approximately y713–960 |
| Insights | Begins at y293; 1204px wide × 449px high | Two 594px support panels begin at y758 |

These are measurements of the captured source and state, not universal fixed chart heights or financial data promises.

## Review state

**Current acceptance: ship, September 21, 2026.** The final independent verdict scored all six corrections as resolved, with no material regressions from this batch visible in the required viewport and full-page matrix. It applies to the corrected release captures under `outputs/visual-analysis-correction-20260921/release-*`, reviewed against the three approved references and written corrections. Acceptance is limited to the six scored fixes; it does not claim whole-surface perfection. The visual inspection and the automated checks provide separate, bounded evidence.

The user rejected the preceding release: “It is still not looking like the images and looks worse than before.” Consequently, the former **ship** verdict, its 20-check receipt, and the `outputs/visual-analysis-implementation-20260921/reviewfix2-*` captures are superseded and are not current acceptance evidence. A fresh independent reference-fidelity review first returned **rebuild**. A full review of the composition rebuild then returned **fix** and identified six corrections. The final verdict confirmed resolution of the five visual findings: selected PAC map/legend/ranking prominence, immediate mobile selection feedback, visible committee identity in collapsed scope, legible recipient rows with real filing disclosures, and shared left alignment at wide widths. The sixth correction updated the persisted design and surface records to supersede the rejected release's acceptance claims. Compatible scope persistence remains an interaction requirement.

Current release evidence supporting that bounded verdict: `release-metrics.json` captures Graph, selected Graph, PAC geography, selected PAC geography, and Insights at 1440px, 1168px, 900px, 390px, and 2048px, with desktop/mobile full-page companions, totaling 35 screenshots. The 25 viewport/state checks reported zero whole-page horizontal overflow, stale-build banners, or browser errors. No visual application code changed after these release captures. `release-health.json` identifies the server on port 8806 as this checkout (`C:/Users/pgoff/Mentat/mentat`), with matching served and on-disk code hash `41b00450299fa9686f0442ece2015c8a191adc3630457e50f6dc774884ab2a48` and asset hash `a2a2cdef73b53f2e4fd6b88bdb2d4cdc8ad12b5272434462a148fb799f124d2b`. Build identity is evidence for these captures, not a substitute for inspecting them.

These records describe bounded visual and interaction checks of the captured states. They do not establish whole-surface perfection, complete filing coverage, or financial completeness.
