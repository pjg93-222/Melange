# Build prompt 04 · Insights (I1)

**Builder:** one Opus architect or Codex agent, alone in the tree, after 01-03. **Read first:** `prompts\00_README.md`.

## Visual spec (binding)

- `boards\I1_insights.webp`: final.
- Context only: `boards\src_M10_insights_change_report.webp` (the base) and `boards\src_B15_insights_then_now.webp` (the running-total chart).

**Don't copy:** the sidebar footer "build 2b1a62d · port 8800" (carried from M10); the rail label "Favorites" (use "Top recipients"); every amount.

## What exists today (verified 2026-09-22)

Template `mentat/app/templates/view_insights.html` (37 lines; new and untracked, like `insights.js` and `insights.css`); data from `mentat/app/analysis_data.py` and `analysis_*.py` through `/api/insights/catalog`, `/api/insights/query` and `/api/insights/records` (`server.py` 2425 and 2701).

- Header: `#insights-export-csv`, `#insights-export-json`, `#insights-page-sources`, and a Refresh button.
- Filters: `#insights-dataset` (Industry), `#insights-company`, `#insights-basis`, `#insights-funding-source`, `#insights-compare-open` (Compare).
- Sub-tabs: `#insights-analysis-overview`, `#insights-analysis-choose`, `#insights-analysis-sources`.
- `insights.js` lines 7-19 `PANELS`: favorites "Industry favorites", trends "Comparable-cycle trends", changes "Explain the change", concentration, relationships, overlap, timing, profiles, spending, legislation, forecast; line 20 `CORE = ['favorites','trends','changes']`; line 26 `FUNDING_LABELS` (includes `conflicting_source_evidence`); `renderPanel()` 261; `makeChart()` 352; the per-card channel select is filled at line 407 from the cards' funding sources, which is why a card can open on "Conflicting source evidence".
- Request fields: `dataset, basis, panels, company, funding_source, as_of, baseline_cycle, current_cycle, comparison_dataset, retry`. Response: `token, status, message, panels, scope, options, provenance, history, source_history, notices`; panels carry `rows`, `columns`, `cards`, `series`, `quarterly_series` and more.
- Tests: `test_insights_browser.cjs` (103 id references), `test_insights_controls_browser.cjs` (31).

## Build this

1. **Header:** title "Insights", subtitle "Compare periods and explain observed changes."; at the right: secondary "Sources" (`#insights-page-sources`), secondary "Export ▾" (one menu: CSV = `#insights-export-csv`, JSON = `#insights-export-json`), plum "Refresh".
2. **Filter card:** labelled selects Industry, Company, Basis and Funding (label above the select, as on I1), then the period pair: two select chips "2023-2024" -> "2025-2026" with an arrow between them, and a swap button (⇄, accessible name "Swap periods") that exchanges them. They drive `baseline_cycle` and `current_cycle`, and replace `#insights-compare-open` (re-home its test assertions).
3. **Summary strip card**, four cells divided by thin rules: "Net giving 2023-2024" and its value; "Net giving 2025-2026" and its value; "Change", value and percentage (teal when up, `--chart-negative` when down); "Recipients" as "214 continuing · 61 new · 38 no longer observed". Every number comes from the query response; if a count is not in it, show the cell without that count and report the missing field.
4. **Analyses rail** (left card, about 350px): serif title "Analyses"; one toggle row per analysis with short labels (Top recipients, Trends, Changes, Concentration, Relationships, Company overlap, Timing, Recipient profiles, Outgoing spending, Legislative context, Forecasts) and teal switches; footer links "Core three | All". It replaces the "Choose analyses" sub-tab; source records open from the header's "Sources". Keep sub-tab ids only if tests need them (hidden) and re-home the rest.
5. **Cards (right, grid)** with one shared chrome: serif title, an (i) that opens method and sources, and a Chart | Table `.segmented`. No per-card Export or "View source records" links (the header has both).
   - "Giving through the same point in each cycle" (wide, top): a running-total line chart. X axis: days before the general election (Nov 5, 2024 for 2023-2024; Nov 3, 2026 for 2025-2026), from 600 on the left to 0 on the right, titled "Days before the election". Y axis: cumulative net giving. The earlier period is a dashed `--acu-taupe` line; the later is a solid `--acu-teal` line ending at a dot labelled "Today $12.0M"; a thin vertical rule marks "Today"; the legend sits at the top right. Data: the trends panel's dated `series` or `quarterly_series`. If only quarterly points exist, join them with straight segments and add "quarterly points" to the legend. If no dated series exists, stop and report; never draw a curve from undated totals.
   - "What changed": a waterfall Baseline <earlier> -> Continuing (+) -> Newly observed (+) -> No longer observed (−, `--chart-negative`) -> Current <later>, with values labelled.
   - "Top recipients" (was "Favorite recipients"): a ranked table # | Recipient | Amount | Change (teal up, red down); Chart view draws bars.
6. **Default measure:** every card opens on the same basis as the summary strip's Net giving. A diagnostic channel such as "Conflicting source evidence" is never the default; if a card offers channels, its select sits inside the card and defaults to the aggregate.
7. **Truncation:** remove the yellow banner. In Table view, a muted line "Showing 25 of 2,385 rows" under the table.
8. **Empty and error states:** a card with no rows reads "No receipts in this period for this scope." in `--muted`; a failed query shows its message and a "Try again" link inside that card only.

## Acceptance
States at 1440x900 and 1920x1080 beside I1: Banking, 2023-2024 -> 2025-2026, core three on; after swapping the periods; with Concentration switched on (a fourth card appears); Table view on each card; an empty scope. Checks: no card opens on a diagnostic channel; Export appears once; the running-total chart's x axis ends at 0 on election day. Suites: `test_insights_browser.cjs`, `test_insights_controls_browser.cjs`, `render_console.py --check`.
