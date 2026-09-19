# Original guided Graph rendering — September 12, 2026

The guided Graph now creates a full values table when its disclosure is first opened. Reopening uses the existing table. The visible SVG preview, chart controls, full-table buttons, formatting, row actions and export sources remain unchanged.

The same offline browser fixture supplied 10,012 rows across categories, organizations, candidates, companies and employee levels. Each run used the original page structure and styles. No report scans or external requests were involved.

| Initial Graph work | Before | After |
|---|---:|---:|
| Hidden table body rows constructed | 10,012 | 0 |
| Descendant DOM elements in Graph panels | 40,432 | 349 |
| Visible preview marks | 42 | 42 |
| Initial render plus layout measurement | 458.4 ms | 30.7 ms |
| Two repeat renders | 306.6 / 352.7 ms | 5.0 / 4.9 ms |

These timings describe the local synthetic rendering fixture, not report loading or total application startup. The DOM counts demonstrate the avoided work independently of timing variability. Opening a full table still performs the work needed to display all requested rows.

The browser regression verifies that all five breakdowns materialize every exact formatted value after expansion, including negative amounts; a reopened table retains its DOM identity; full-table controls still select the correct analysis; recipient and candidate row callbacks retain their behavior; CSV includes all 5,000 organization values and source fingerprints; SVG export retains its ten-row preview and full-count caption; and Show all rows still renders the complete SVG. The deferred tables reset with each new selection as before.

Evidence: [graph-before.json](graph-before.json), [graph-after.json](graph-after.json), and the preserved [previous graph.js](graph-before.js). Reproduce with `mentat/tests/test_graph_lazy_tables_browser.cjs`; `MENTAT_GRAPH_SCRIPT` selects the previous file, `MENTAT_GRAPH_BENCH_ONLY=1` runs only the timing probe, and `MENTAT_GRAPH_BENCHMARK_OUTPUT` saves its JSON receipt.
