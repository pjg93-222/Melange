# Mentat UI workshop — September 11, 2026

Implemented locally and opened at http://127.0.0.1:8808/#graph. Higgsfield supplied a fresh Graph + PAC evidence design reference; the functional interface remains in the existing Mentat app.

## Result

- Collection separates In progress, History and Archived. Run choices include timestamps. Archive/Restore changes console metadata only; files and checkpoints stay in place. Active runners cannot be archived. Saved drafts show setup controls without an empty monitoring dashboard, and archived drafts require restoration before launch.
- Working folders identify the internal collection workspace and `C:/Users/pgoff/OneDrive/Desktop/Mentat Complete Files` for completed reports.
- PAC evidence defaults to selecting a CSV and PAC, with an optional recorded cycle. The parser retains original fields, malformed/unclassified rows and duplicate filings. Receipts, disbursements and independent spending totals remain separate. These are sums of imported observations, not reconciled totals or donor-attributed spending.
- CSV imports remain in local server memory. Limit: 5 MB / 50,000 rows. The table pages 100 rows at a time; totals and counts cover every selected row. Source details label the SHA-256 as the imported UTF-8 text hash, not necessarily the original file-byte checksum.
- Split view keeps Graph and PAC evidence side by side from 800px; smaller screens stack them. Both selections remain independent and their sources stay visible. The CSV amount column precedes the longer counterparty/activity details.
- Selecting a chart configures compatible fields and preserves a valid selected statistic. Time/ID columns are excluded as automatic monetary measures. Independent funding sources cannot be combined accidentally. Incompatible charts explain the reason.
- Scatter no longer has a 5,000-point rendering cap. Batched SVG paths retain every loaded valid pair. The separate worksheet loader still rejects sources over 50,000 rows explicitly. The dense values table previews 200 points; plotted points and CSV exports remain complete.
- Axes use actual field names and aggregation; grouped names wrap and retain their complete title text. Row-count axes use integer ticks and histogram ranges use readable display labels.

## Time analysis

Over time displays totals (or the selected aggregation) by year or election cycle. Year over year displays percentage change versus the preceding calendar year; missing years and nonpositive prior totals do not produce a percentage. Two-year cycle data uses absolute period change instead.

Forecast uses a same-election-phase historical baseline, following the [seasonal naïve method](https://otexts.com/fpp3/simple-methods.html). It repeats the most recent completed observation from the corresponding phase of the four-year calendar. It does not impose a presidential uplift or extrapolated growth. It requires at least eight consecutive closed years or four consecutive closed two-year cycles, including two observations per phase. Current, explicitly partial and missing-value periods do not train it. Historical calendar closure alone does not establish collection completeness, and no calibrated prediction interval is claimed. Current sources with only three cycles cannot produce this baseline.

## Verification

- 32 Node calculation tests passed, including every chart type, valid selection preservation, independent funding, signed/missing values, phase baselines, partial history and a 125,001-pair scatter calculation.
- 44 Python tests passed: 10 CSV/parser/HTTP, 6 run archive and 28 existing collection console checks. CSV tests include read-only session imports, local authentication, malformed accounting signs, aggregate overflow, paging and source retention.
- Chart browser suite: 2/2 passed. All 15 chart choices, incompatible selections, axis labels, integer count ticks, histogram display ranges, 50,000 rendered scatter points and a complete 50,000-point CSV export verified.
- Full console browser suite passed. Tested CSV file import, PAC/cycle changes, pagination, unsupported values, escaped source text, saved snapshot persistence, first chart load from evidence-led split view, 1440px/820px split and 390px stacked layouts, archive/restore preserving the report, compact ready drafts, and existing Graph, comparison, exports, keyboard and dialog behavior. No unexpected browser errors or external app requests.
- Live app inspected in the in-app browser. Banking and Community Banks remain separate report scopes. The Banking graph still displays the previous pass's selected totals; no live collection or report mutation was performed.
- Live server PID 41080, server.py SHA-256 `83e196946a9575149135638b489e119006abc4130e3004c9501b3d4a1dd74d69`. Health confirms the designated report directory and the current writable app mode.

Screenshots in this folder use fictional fixtures, except the separate live inspection described above. See `split.png`, `split-medium.png`, `split-mobile.png`, `csv-evidence.png`, `ready.png`, `archived.png`, `builder.png` and `dense-scatter.png`.

No real runs were archived automatically; the new controls let the user choose which history to hide. Existing working-tree changes were preserved.

Final time-bucketing regression: Date/Year sources now aggregate 2023 and 2024 into the 2024 election cycle, and 2025 and 2026 into 2026. Explicit Cycle fields require an even end year or a valid consecutive two-year range. Missing/partial annual coverage maps to the containing cycle, and both member years are required when establishing cycle completeness. The final Node calculation count is 36 passing tests (superseding the 32-test checkpoint above).

Final axis verification: scalar axes now use rounded 1/2/5-based intervals. The 50,000-point scatter displays X ticks 0–500 in steps of 100 and Y ticks 0–5,000 in steps of 1,000. Very small nonzero ticks use concise scientific notation; floating-point boundary handling keeps the original minimum and maximum inside the scale. The final focused renderer test passed (exit 0), retaining every point and the exact full CSV export. No further implementation or verification work remained at handoff.
