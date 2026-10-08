# Mentat visual correction — September 21, 2026

The user rejected the prior implementation because it did not resemble the approved images. That rejection supersedes the previous acceptance claim and `reviewfix2-*` screenshots.

## What changed

The three approved images remain the visual authority, subject to the written 180px sidebar, 28px workspace gutter, readable type, real source data, and accounting distinctions.

| Surface | Corrected composition at 1440px |
|---|---|
| Graph | Six recipient bars, a compact adjacent evidence rail, and company comparison starting at y746. The main frame begins at y302. |
| PAC evidence | Real map with its legend beside it, all five ranked states visible by y959, and selected recipient evidence alongside. Multiple actual filings are grouped under counted disclosures. |
| Insights | Main supported cycle comparison begins at y293 and is 449px tall. Favorites and signed changes begin at y758. |
| Shared shell | Serif wordmark, restrained plum/teal palette, compact scope bands, consistent analysis controls. At 2048px, content starts at x208: sidebar plus the prescribed gutter. |
| Mobile PAC | Committee identity remains visible with collapsed scope controls. Selected place, amount, Clear selection, and View source records appear adjacent to the map. |

Exact Graph amounts remain in the evidence, accessible labels, tables and exports. Aggregate-only records are identified as unavailable rather than invented. Insights uses supported cycle comparisons instead of unsupported monthly lines. The PAC scope retains its actual $2,311 unresolved reconciliation gap and independent accounting meaning.

## Visual review

A fresh independent review of the rejected release returned **rebuild**. A full review of the rebuilt composition returned **fix**, identifying five visual issues and the obsolete acceptance record. After a bounded correction, the same reviewer scored all six fixes **resolved**, with disposition **ship**.

This verdict covers those scored fixes and the supplied states. It does not certify perfect pixel identity or every possible application state. No material regressions from the final batch were visible in the reviewed screenshots.

All 35 final captures were opened and checked: five states at 1440, 1168, 900, 390 and 2048px, plus full-page captures at desktop and mobile widths. The 25 viewport/state measurements reported zero whole-page horizontal overflow, stale-build banners, page errors or console errors. See `release-metrics.json` and the `release-*.png` files.

## Verification

- Graph lazy tables: passed with a 10,012-row fixture; full rows, interactions and exports retained.
- Insights main and control suites: passed, including all eleven analyses, integer-cent charts, scope changes, exports, source paging, retry and stale-response handling.
- Graph, geography, theme and navigation unit checks: 67 passed. Geography checks were rerun after adding national comparison-scale coverage: 17 passed.
- Console template checks: passed; generated HTML is current.
- All seven workspace responsive checks: passed at 1168, 900 and 390px.
- Navigation browser suite: all 13 steps passed; its browser shutdown exceeded the harness's 20-second cleanup bound.
- PAC source/map suite: all 23 steps passed with zero page or console errors.
- Live release checks: served bytes match disk for ten assets; five ranked states fit in the desktop viewport; comparison selection retains the national scale; filing links survive disclosure toggles; mobile source identity, evidence focus handoff, and clear selection work.
- Extended PAC interaction suite: all 22 steps passed, including search, zoom/pan node preservation, national/focused scales, legislative layers, pagination, phone controls and reduced motion; zero page or console errors.

The live application remains at `http://127.0.0.1:8806`. Release identity and served-file SHA-256 values are in `live-build-receipt.json`. Application assets were not changed after the final capture. DESIGN.md, its token sidecar and the surface brief now record the corrected composition and bounded review result.

## Final screenshots

![Graph](C:/Users/pgoff/Mentat/outputs/visual-analysis-correction-20260921/release-graph-selected-1440.png)

![PAC evidence](C:/Users/pgoff/Mentat/outputs/visual-analysis-correction-20260921/release-evidence-selected-1440.png)

![Insights](C:/Users/pgoff/Mentat/outputs/visual-analysis-correction-20260921/release-insights-1440.png)
