# Mentat visual analysis implementation

Implemented the three approved compositions in the existing Graph, PAC evidence, and Insights workspaces. The reference images governed hierarchy, palette, comparison size, and evidence placement; actual local records govern every displayed amount.

## Delivered behavior

- Shared plum/teal/ivory presentation, seven workspace tabs, underline analysis navigation, Chart/Table/Export controls, and compact scope controls.
- Graph leads with recipient comparisons and a full-width company analysis. Selection preserves the comparison query; a compact evidence rail shows the selected amount and its accounting scope. Downstream PAC charts and the existing route explorer remain available in a disclosure. Exact committee/cycle handoffs, full tables, exports, and company sparklines remain available.
- PAC evidence keeps imports, saved snapshots, multiple panes, geography layers, source rows, filings, search, zoom, and comparisons. Map and ranked selection agree. Loaded thumbnails use a shared positive color range, with reversals and missing geography distinguished. Coverage and reconciliation gaps remain explicit; long snapshot inventories are disclosed.
- Insights preserves all eleven analyses and their scope controls. Cycle comparisons show full observed and same-stage observations separately. Waterfalls require exact signed-cent reconciliation. Source records, CSV/JSON exports, and retry behavior remain available.
- Mobile names wrap at the actual plotting width. Supporting Insights charts stack, evidence rails move below comparisons, and narrow controls retain usable sizes.

## Live build identity

Verified the user’s port **8806** instance, not the separate preview server.

| Field | Verified value |
|---|---|
| URL | `http://127.0.0.1:8806` |
| Server | `C:\Users\pgoff\Mentat\mentat\app\server.py` |
| Data root | `C:\Users\pgoff\AppData\Local\Mentat\console` |
| Report directory | `C:\Users\pgoff\OneDrive\Desktop\Mentat Complete Files` |
| Git base | `862a6c46a` with existing working-tree edits preserved |
| Final PID | `65936` |
| Final asset SHA-256 | `c3ce4f2aa94900a5403c4223109bbfd64df8b9b82e88481290841588532b02c9` |
| Code aggregate | `41b00450299fa9686f0442ece2015c8a191adc3630457e50f6dc774884ab2a48` |

The loaded and on-disk aggregate hashes match. Nine directly fetched JS/CSS assets match their local bytes. The supported restart endpoint was used to load the final build. See [live build receipt](C:/Users/pgoff/Mentat/outputs/visual-analysis-implementation-20260921/live-build-receipt.json).

## Verification

| Check | Result |
|---|---|
| Graph layout/navigation, map geometry and text-fit unit tests | 67 passed |
| Console template tests | 10 passed, plus 2 subtests |
| Navigation and shared scope browser suite | 13 steps passed |
| Graph lazy tables and exports | Passed with 10,012 fixture rows; source rows retained, deferred tables, exact CSV, selection scope and preview counts verified |
| Existing Graph explorer browser suite | Passed |
| Insights browser suite | Passed all eleven toggles, cents, scope invalidation, source pagination, exports, recovery and narrow layout |
| Insights control audit | Passed keyboard sorting, evidence focus return, retained filters, channel selectors and export headers |
| PAC map/source browser suite | 23 steps passed |
| Extended PAC map interaction suite | 22 steps passed; map enlarges 420→720→420px while preserving zoom |
| PAC pane browser suite | 33 steps passed, including import parsing, multiple cycles, source caching, pagination and exact Graph handoff |
| Seven-workspace responsive suite | Passed at 1168, 900 and 390px |
| Final live capture run | 20 viewport/state captures; no whole-page overflow, stale-build banner or page errors |

The final capture also exercised keyboard recipient selection, unchanged Graph scope, opening the downstream explorer, and clearing selection. Screenshots use live local Credit Union records and the saved CULAC 2024 spending snapshot; fixture suites run on isolated temporary servers.

## Visual review

An independent review inspected the three references and desktop/mobile/intermediate captures. Its five initial material findings were resolved. The final verdict was **ship**, specifically scoring the remaining compact Graph rail, Refresh placement, and Graph selection-header fixes as resolved. This is a scoped finish verdict, not a claim of pixel-perfect equivalence or a new financial-data audit.

The final capture set is `reviewfix2-*`. Earlier `before-*`, `inspect-*`, `final-*`, and `reviewfix1-*` files are retained as intermediate evidence and are not the delivery images. Canonical review copies are also under `.impeccable/review/`.

## Screenshots

| Workspace | Desktop | Full page | Mobile full page |
|---|---|---|---|
| Graph, selected recipient | [1440px](C:/Users/pgoff/Mentat/outputs/visual-analysis-implementation-20260921/reviewfix2-graph-selected-1440.png) | [Full page](C:/Users/pgoff/Mentat/outputs/visual-analysis-implementation-20260921/reviewfix2-graph-selected-1440-full.png) | [390px](C:/Users/pgoff/Mentat/outputs/visual-analysis-implementation-20260921/reviewfix2-graph-selected-390-full.png) |
| PAC evidence | [1440px](C:/Users/pgoff/Mentat/outputs/visual-analysis-implementation-20260921/reviewfix2-evidence-1440.png) | [Full page](C:/Users/pgoff/Mentat/outputs/visual-analysis-implementation-20260921/reviewfix2-evidence-1440-full.png) | [390px](C:/Users/pgoff/Mentat/outputs/visual-analysis-implementation-20260921/reviewfix2-evidence-390-full.png) |
| Insights | [1440px](C:/Users/pgoff/Mentat/outputs/visual-analysis-implementation-20260921/reviewfix2-insights-1440.png) | [Full page](C:/Users/pgoff/Mentat/outputs/visual-analysis-implementation-20260921/reviewfix2-insights-1440-full.png) | [390px](C:/Users/pgoff/Mentat/outputs/visual-analysis-implementation-20260921/reviewfix2-insights-390-full.png) |

All three also have 1168px and 900px captures. Graph and PAC have selected-state captures at all four widths.

## Deliberate differences and limits

- The mockups’ fictional values and monthly trajectories were not substituted for source data. Insights uses the actual cycle-level response, with separate observed and matching-stage values.
- The CULAC spending snapshot has a real **$2,311 unresolved reconciliation gap**. The UI shows it and does not print a verified equality or attribute downstream network spending to a donor.
- Controls and required scope qualifications make some compositions taller than the mockups. Long labels wrap on phones; dense source tables retain local scrolling.
- These are fresh headless Chrome renders of the real running server at the specified viewport sizes. The native Edge application’s exact current window geometry was unavailable; it was not claimed as separately captured.
- Figma connectivity was verified. No Figma file was supplied or modified. The implementation keeps UI text and plots as editable HTML/SVG; no raster mockup text, logo regeneration, or AI-generated financial values were introduced.
- No backend accounting computation or report pipeline was changed. Existing unrelated working-tree edits were preserved; no commit was created.

Design guidance is recorded in [DESIGN.md](C:/Users/pgoff/Mentat/DESIGN.md), its [structured sidecar](C:/Users/pgoff/Mentat/.impeccable/design.json), and the [surface brief](C:/Users/pgoff/Mentat/.impeccable/surfaces/visual-analysis.md).
