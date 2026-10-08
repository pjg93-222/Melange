# Mentat UI cleanup and regression review — 2026-09-20

The Insights workspace now uses compact controls and three aligned core cards.
The review also found and repaired reproducible data, navigation, export and
evidence-drawer defects. Tests use isolated fixtures; published reports and
Melange source artifacts were not modified.

The console loads the selected industry through verified workbook/database
proofs, retrieves indexed observations, computes exact signed-cent analyses,
and renders charts, tables, record drills and exports under one scope. Optional
panels read saved FEC and Melange evidence. The wider collection/compilation
checks exercise fixture collection, attribution, reconciliation and report
generation into temporary directories; final reports still resolve to the
configured authoritative report directory.

## Interface changes

- Applied the synthetic Higgsfield refinement `7a99a3a2-2751-4214-9094-41ebba2a6408` to the existing Mentat palette and local HTML/SVG interface.
- Aligned filter heights, card headings, spacing and source footers; consolidated repeated CSS overrides.
- Collapsed comparison options and the optional-analysis chooser initially; the three requested core analyses remain enabled.
- Shortened labels and chart captions, moved method notes below charts, and retained expandable exact tables and provenance.
- Added a funding-channel selector to the change chart. Tables and exports still include all returned channels.
- Preserved keyboard focus, visible focus indicators, reduced-motion support and native checkbox fallback in forced-colors mode.

## Reproduced defects and corrections

| Impact | Reproduction | Correction and evidence |
| --- | --- | --- |
| Incomplete evidence behind a displayed total | Analyze blank and literal `Unknown` companies or funding sources, then open their records. | Drill filters now include both source representations; signed sums reconcile in adapter regressions. |
| Wrong integration identities | Provide a record whose event date and election cycle conflict. | It remains in the appropriate non-temporal observed totals but cannot create a dated recipient-cycle integration link. |
| Invalid comparison or malformed request | Select the latest baseline with automatic current, or submit malformed/oversized filter values. | Validate the resolved cycle order and reject invalid values with readable validation errors. An invalid-cycle row no longer exposes an unrestricted drill link. |
| Omitted or misidentified finance summaries | Request a connected company PAC absent from receipt recipients; import a committee endpoint that also contains a candidate ID. | Use the official endpoint's entity kind and exact ID, require the whole period to fit the dated affiliation, and reject inverted coverage dates. |
| Broken filing links | Open a saved FEC image URL with a numeric image selector. | Preserve the official `docquery.fec.gov/cgi-bin/fecimg/?<image-id>` link while continuing to remove credential-bearing queries. |
| Backward inspection timestamps | Inspect a previously seen version using an older clock value. | Keep the later recorded last-inspection timestamp; history remains explicitly distinct from filing/publication dates. |
| Keyboard and recovery traps | Sort a table by keyboard, close its records, or fail page two of evidence. | Preserve sorting focus and scroll position, return focus to the opener, and keep Previous available after failure. |
| Silent filter or scope changes | A selected filter disappears from refreshed options, or the shared industry changes in another workspace. | Preserve unavailable selections visibly, publish/subscribe to shared industry changes, defer hidden queries, and keep independent Insights comparison periods. |
| Ambiguous CSV columns | Export a panel whose row fields duplicate scope fields. | Distinct scope headers prevent duplicate CSV column names; source codes and accounting metadata remain intact. |
| Evidence map stuck on “Reading rows” | Select a district, then choose Back to panes. | Load the selected pane's rows, reject stale replies, show a retry after failure, and clear the hidden focus when removing the district filter. |

The two failing R tests were stale expectations for previously implemented
accounting/column changes. Only those test contracts changed: all prior column
ordering assertions remain, and `count_all`, `count_latest` and `withhold` are
tested explicitly. The initial failure logs are retained beside passing reruns.
An older Studio browser test also expected URL contract v4 after the documented
v5 addition of Graph drawer keys; its version expectation was corrected while
retaining the retired-strip behavior checks.

## Verification

- Full Python discovery: **1,169 tests passed** (`python-full.log`).
- JavaScript unit checks: **370 passed** across the app suite and 11 additional suites.
- Offline R fixture suite: **25 scripts passed**, including passing reruns of the two corrected tests.
- PowerShell runtime/report guards: **6 scripts passed**.
- All **34 `*browser.cjs` harnesses** passed their functional assertions and exited successfully, alongside the additional map-render and Cross-reference checks. See the [integration/browser inventory](integration-browser-qa.md) and the [remaining browser report](browser_remaining_lane/REPORT.md), including original/retry/final process results. Final screenshots are stored in this directory.
- Final targeted reruns passed: **90 analysis tests**, **16 build-stamp tests**, and the **3 HTTP analysis tests** after the last label edit.
- Generated HTML matches its templates.

Three browser processes were interrupted by large host timing gaps and were
rerun in fresh processes; their initial cancelled/timeout logs are retained.
The corrected Studio contract test was also rerun. The final running app's
code and asset hashes match disk (`live-build-final.json`), and its cached
11-panel Banking query completed in **920 ms** (`live-cache-final.json`).

The live Banking analysis scanned **592,570 selected receipts** across all 11
requested panels, with zero newly invented source observations and the same
verified source index. The returned panel states explicitly identify limited
integration coverage and unavailable forecasts. A separate source drill returned
all **494 records** for one recipient/channel and reconciled exactly to
**31,842,374 cents** (`live-reconciliation.json`). No individual source rows were
saved in this audit.

## Limits

This is a broad regression pass, not a proof that every possible interaction is
bug-free. It covers saved-source retrieval and fixture collection/compilation;
it does not rerun live network collectors or replace production reports. Current
saved integration coverage remains partial, and forecasts remain unavailable
without verified complete history. Nonfatal R locale warnings, the Python test
socket ResourceWarning, and any browser cleanup warnings are retained in logs.
