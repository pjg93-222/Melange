# Mentat UI correction verification — 2026-09-21

## Delivered

- PAC map heat domains follow the painted geography and do not collapse to a single selected state. Existing PAC pane layout retained.
- Chart variants preserve selected shelves, filters, and aggregation. Explicit primary-measure aggregation control added. Worksheet accounting no longer silently discards alternative scopes; overlapping sums require explicit grouping/filtering.
- Independent comparison of two to four report worksheets, with per-source grouping, measure, aggregation, worksheet row range, and filters. Missing groups remain missing, not zero. Source changes invalidate old charts/exports.
- Downstream candidate data uses the verified complete saved transfer payload when the workbook contains only a shortened preview. Native and fallback paths agree. Saved coverage is not claimed as complete FEC coverage.
- Insights uses Rust-backed workbook scans, a narrow immutable SQLite analysis projection, selected-panel execution, and persistent result caching. Statistical computation is not a complete Rust rewrite.
- Graph panels share chart baselines and reserve separate rows for coverage notes, footers, and detail tables. Quarterly sparklines retained.

## Verification

- Python: analysis adapter 21, report insights 18, graph data 20, native scanner 9, console templates 10, analysis history 4, downstream network 11 tests passed.
- JavaScript: chart core/map/comparison 121, chart math 20, contribution compiler 14 tests passed.
- Rust scanner unit test passed; release build completed.
- Browser: worksheet comparison passed independent mean/sum, missing versus zero, row ranges, stale export invalidation, bars/table, desktop/mobile.
- Browser: PAC map 23/23 steps; map interaction 22/22 steps including heat-index layout, layer changes, state filtering, zoom, and reduced motion. The interaction harness reported a browser-close timeout after all assertions passed.
- Browser: Graph alignment passed shared baselines and non-overlapping note/footer assertions at 1280, 900, and 620 pixels.
- Browser: Insights controls and contribution chart-family regressions passed earlier in this pass.
- Live console: Banking Graph and Studio scope total agreed at $12,003,181.12; downstream view displayed 295 candidates. Insights Overview, Choose analyses, and Source records rendered. Comparison source columns inspected visually; document width did not overflow.
- Scoped diff whitespace check passed.

## Measured performance and limits

Same Banking/default-three-panel request: initial uncached run 189.122 seconds; revised uncached result 79.601 seconds; cached repeat 0.190 seconds. These are local observations, not a controlled benchmark. The first result is materially faster but still not instant; cold source-index/projection creation adds work. Reports and source evidence were not rewritten.

Comparison intentionally rejects unsafe overlapping sums and truncated worksheet results rather than presenting an inaccurate total. Derived source statistics remain marked as such rather than being silently re-aggregated.
