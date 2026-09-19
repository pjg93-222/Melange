# Mentat frontend audit — 2026-09-13 UTC

Audited the current working tree without editing production source, databases or reports. Read `mentat/AGENTS.md`, the project/app READMEs and the contribution-workspace guide. Tests used synthetic inputs, mocked endpoints or the repository's temporary loopback report fixture. No live console or collector was interrupted. No historical report documents were opened.

## Results

- All 21 shipped JavaScript test files ran: 20 `mentat/tests/test_*.cjs` files plus `mentat/app/tests/chart-studio-core.test.js`.
- 152 reported tests: **151 passed, 1 failed, 0 skipped**. The standalone assertion scripts are counted as one Node test each, as Node reports them.
- Nonbrowser: **139/139 passed** across 10 files.
- Browser: **12/13 passed** across 11 files. The failed file exits early, so its subsequent assertions were not exercised in the shipped run.
- Syntax: **20/20 app JavaScript files passed** `node --check`.
- Two additional synthetic reproductions confirmed product defects; these are not included in shipped-suite counts.

Full per-file exit codes, counts and timings are in `unit-results.json`, `browser-results.json` and `syntax-results.json`; adjacent `.log` files preserve exact output. Browser elapsed times include slow Chrome teardown on this machine. No shipped test timed out or was killed.

## Confirmed product defects

**FE-01 — P2: Contribution time-change and forecast views fail on valid data.** At `mentat/app/chart-studio.js:303`, the synthetic `modelData` omits `row_numbers`; `math.build()` reaches `chart-math.js:36`, which always indexes that array. Year-over-year %, Period change and Same-phase forecast therefore show `Cannot read properties of undefined (reading '0')` and a blank chart for nonempty verified contribution data. An eight-year browser fixture reproduces the forecast failure; direct calls using the adapter's exact data shape reproduce all three failures. Period totals bypasses this path. Evidence: `repro-period-analysis.cjs`, `period-analysis.json`.

**FE-02 — P2: Optional Contribution Studio can mix source versions during inspection.** At `mentat/app/contribution-studio.js:232–234`, `inspect()` checks client revision counters but never compares detail-response provenance with the displayed aggregate. The records endpoint resolves the current source independently. A fixture displays a $100.00 aggregate with $900.00 detail from a different workbook/database/index and no error. This affects the optional `/contribution-studio` prototype. The main Chart Studio has an explicit comparison at `chart-studio.js:338`. Evidence: `repro-stale-inspection.cjs`, `stale-inspection.json`.

Machine-readable findings and recommended fixes are in `findings.json`.

## Test drift and limits

`mentat/tests/test_console_browser.cjs:53–54` expects five navigation tabs; the current interface includes Chart Studio as a sixth tab. This is stale test behavior rather than evidence that the new tab is wrong. The test stops there, before its broad Graph, evidence, cross-reference, navigation and export checks.

An output-only diagnostic copy accepting the sixth tab reached line 172, where the old test expects the legacy chart dialog. Current `chart-studio.js:1391` deliberately sends Create chart to Chart Studio. A second supplementary diagnostic restoring the legacy click handler inside its fixture also timed out at that old dialog expectation. Both are retained as diagnostics, **not current-product validation**, and excluded from the 152-test total. The original failure remains a regression-coverage gap; the independently passing builder and Studio suites cover their narrower fixtures.

Source review focused on chart aggregation and temporal adapters, source identity during query/export/drilldown, ZIP map eligibility and geography separation, Cross-reference amount rendering and FEC links, escaped labels, CSV formula protection, and async view revisions. Existing tests passed for arithmetic, source-query compilation, contribution charts, geography, exports, saved state, layout, keyboard inspection, and lazy Graph tables. This does not certify every UI route or real-data accounting result.

The lazy Graph fixture retained all 10,012 source groups while initially creating zero table rows; its first render took 27 ms and repeated render measurements were about 5 ms on this run. These are synthetic local timings, not production latency estimates.
