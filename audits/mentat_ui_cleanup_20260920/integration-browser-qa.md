# Integration and browser regression QA — 2026-09-20

Final result: all 17 browser suites passed. The original evidence-map suite exposed a production regression; its original district assertion was preserved, the production code was fixed, and the expanded 23-step suite passed. The integration adapter's 24 Python tests also passed. No production data, FEC evidence, workbooks, or Melange database contents were changed by this lane.

Logs and tested-file SHA256 values are in `browser_integrations_lane/`. `test_evidence_map_browser.cjs.log` and `test_evidence_map_browser.before-fix.log` preserve the initial failure. `test_evidence_map_browser.after-fix.log` is the final passing run.

## Confirmed defects fixed

- Returning from a selected map district opened the pane's source drawer without loading its rows. The independent in-map source request did not populate that drawer, so it stayed on “Reading rows…” and the original CA-12 assertion timed out. Returning now loads the pane's selected source rows. A load failure has an explicit retry control. Request tickets and captured source, committee, cycle, and page reject replies from stale or removed panes.
- Clearing the visible district removed the district label but left the underlying geographic focus active. Clear now removes both, and the regression verifies that all three fixture rows return.
- Company-connected PAC financial summaries could be omitted unless the PAC was also a selected receipt recipient. Saved committee summaries now qualify independently through the approved dated affiliation, only when the entire financial coverage period fits that affiliation. Inverted periods are rejected.
- A saved committee financial record's optional candidate ID could misclassify the record. Financial record type now follows its verified saved endpoint, with matching entity IDs required.
- Saved FEC image links used an official `docquery.fec.gov` URL whose numeric image selector was discarded. The adapter now preserves only the bare numeric selector for the exact official image endpoint; credential and unrelated queries remain excluded.

The map regression simulates a source-row failure before fetch, verifies the displayed failure and retry, preserves the original CA-12 selection check, verifies one filtered row, clears the district, and verifies all three rows. The final run reports zero page errors and zero console errors.

## Final browser inventory

Each command ran from `mentat/` as `node tests/<suite>`. Test fixtures and isolated local servers were used.

| Suite | Result | Main coverage |
| --- | --- | --- |
| test_console_browser.cjs | PASS | Guided graph scopes, JFC, direct/downstream separation, export, chart controls, freshness, keyboard and responsive navigation |
| test_chart_builder_browser.cjs | PASS (2 tests) | Chart/comparison state, missing values, stale requests, chart labels, dense scatter and complete export |
| test_graph_explorer_browser.cjs | PASS | 10,000 relationships, search, pagination, inspection, complete export |
| test_graph_lazy_tables_browser.cjs | PASS | Deferred tables without lost rows, callbacks, or exports; 10,012-row fixture |
| test_navigation_scope_browser.cjs | PASS (13 steps) | Scope carried between app views, refresh, readonly cross-reference |
| test_downstream_measurement_browser.cjs | PASS | Observed activity, signed amounts, source differences, coverage |
| test_contribution_charts_browser.cjs | PASS | Chart families, typed values, source groups, keyboard inspection |
| test_contribution_export_browser.cjs | PASS | SVG/PNG map export, viewport clipping, legends |
| test_evidence_map_browser.cjs | PASS after fix (23 steps) | Exact map totals, selected district, pane loading/retry, clearing, permalink, cycles, private geocoding payload, zero browser errors |
| test_evidence_map_interaction_browser.cjs | PASS (17 steps) | 3,200 ZIP map fixture, interactions, responsive rendering, zero browser errors |
| test_contribution_plot_readability_browser.cjs | PASS | Bounded readable chart text and narrow-screen internal scrolling |
| test_contribution_studio_state_browser.cjs | PASS (2 tests) | Saved scope, exact filters, complete source-checked CSV, long filter values on narrow screens |
| test_contribution_studio_map_browser.cjs | PASS | Geography-only requests, viewport, stale response rejection |
| test_studio_reconciliation_browser.cjs | PASS | Graph-to-Studio reconciliation to the cent and explicit mismatch reasons |
| test_studio_temporal_regression_browser.cjs | PASS | Year-over-year, change, and forecast rendering |
| test_studio_inspection_regression_browser.cjs | PASS | Matching source accepted, stale inspection rejected |
| test_cross_reference_scope_browser.cjs | PASS | Scope replacement, late responses, empty state, failure, retry, tab reactivation |

The navigation suite exited 0 with all assertions passing; browser shutdown exceeded its bounded 20-second cleanup window and printed a nonfatal warning. This is preserved in its log and was not a product assertion failure.

## Targeted checks and freeze

- `python -m unittest discover -s mentat/tests -p test_analysis_integrations.py`: 24 tests, PASS (0.644 seconds in final logged run).
- `node --check mentat/app/evidence.js`: PASS.
- Final production map edit: `mentat/app/evidence.js`, filesystem modification time `2026-09-20T18:01:39.3918993-04:00` / `2026-09-20T22:01:39.3918993Z`.
- Final map browser-test edit: `mentat/tests/test_evidence_map_browser.cjs`, `2026-09-20T18:02:38.1218017-04:00`.
- This lane is frozen after the passing map rerun. Root owns the final full-app checks and live-source reconciliation; those results are recorded separately in this audit directory.
