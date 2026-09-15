# Mentat Ride 1 — Checklist (v2)

32 steps across PRE / F1-F6 / E1-E6 / WRAP. Statuses, notes, and screenshots are tracked live in `RIDE_CHECKLIST.html`; this table is the static reference copy.

Verifies commit `f64316daa` (on top of `9b14e1d53` / `215faa9db` / `ed6474351`, branch `codex/mentat-crypto`). Restart the console before step 01 — Restart reads "Already up to date." when you are already on this build.

| ID | Fix | Priority | Click path | Expected result |
| --- | --- | --- | --- | --- |
| 01 | PRE | P1 | Address bar | URL port equals the launcher's port; /api/health server_code_sha256 equals the on-disk server.py hash |
| 02 | PRE | P1 | Ctrl+Shift+R on #chart-studio | Header "Chart Studio", chip "Banking · All cycles", Builder \| Canvas only, Inspector tabs Marks/Analytics/Filters; no console errors |
| 03 | PRE | P1 | DevTools Network, filter query, reload | Single-digit POST /api/contributions/query; status ends "N verified queries this session" |
| 04 | F1 | P1 | Read the status bar | Ends with "build \<sha7\> · port \<port\> · up since HH:MM" matching /api/health |
| 05 | F1 | P2 | Open a second tab to the same port | No stale banner; both tabs show the same stamp |
| 06 | F1 | P1 | Coordinator starts an older server.py copy on 8816; open that tab | Gold banner "This console runs an older build…" with Restart; launcher replaces an idle stale server on the same port |
| 07 | F2 | P1 | Data panel: single-click Company | Company lands on Columns; chart draws; status "Added Company to Columns"; Undo removes it |
| 08 | F2 | P1 | Hover a field pill | Small purple "+" and tooltip "Click to add · drag to place · Enter for actions" |
| 09 | F2 | P1 | Single-click Selected amount | SUM(Selected amount) lands on Rows; title "Published included receipts by Company" |
| 10 | F2 | P1 | Tab to Election cycle, Enter, "Add to Columns" | Same result as the mouse path |
| 11 | F3 | P1 | Look at the left panel on a fresh load | Data source disclosure open; after the first load it collapses to "Data source · Banking · Published included receipts · ready" |
| 12 | F3 | P1 | Open Data source, Report select | Unavailable datasets listed disabled with the server's reason under the select and as the option title |
| 13 | F3 | P1 | Click Refresh verified data | Progress row "Preparing verified data · … · m:ss elapsed" with Cancel; Cancel keeps the previous view |
| 14 | F3 | P2 | Header "Data source" button | Disclosure opens and takes focus, from any state |
| 15 | F4 | P1 | Graph tab: Banking, All companies, All cycles; note "Net giving in selected scope" | Value recorded in the note (Scope A) |
| 16 | F4 | P1 | Graph: Open in Chart Studio | Chip "Carried from Graph · Banking · All cycles"; strip "Graph shows $X for …. Studio shows $X. Agree." to the cent |
| 17 | F4 | P1 | Graph: cycle 2025-2026 + first company, Open in Chart Studio | Chip with company and cycle; chart draws (no "No matching observations"); strip agrees to the cent |
| 18 | F4 | P1 | Strip link "Why Cross-reference differs" | Opens Cross-reference; caption explains the money stage; cycles shown beside every dollar figure |
| 19 | F4 | P2 | Cross-reference review table | Reasons in plain words (no snake_case); "counted at $0" rows marked |
| 20 | F5 | P2 | Read studio notes and errors during the ride | No "contribution explorer"; default empty state names the verified report; refusal reasons in plain words |
| 21 | F5 | P2 | Drop a field on Filters | Pill reads "\<field\>: any value"; chart unchanged |
| 22 | F6 | P1 | Header: Canvas only | Data panel, shelves, toolbar, Inspector gone; header keeps Builder \| Canvas only and Export |
| 23 | F6 | P1 | In Canvas only: Export, Image (PNG) | File downloads with title and scope caption |
| 24 | F6 | P1 | Narrow the window under 1200px; Inspector toggle | Toggle visible with filter-count badge; drawer opens; Builder restores all |
| 25 | E1 | P2 | Export, Copy image | Paste into Word or Teams shows the chart with caption |
| 26 | E2 | P2 | Export, Print chart | Print preview: chart, title, scope, basis, source SHA, one page, no navigation rail |
| 27 | E4 | P1 | Add to briefing on two different sheets | Badge "2"; drawer lists both with title, scope, basis, time |
| 28 | E4 | P2 | Drawer: Remove one, reorder | List updates; order persists after reload |
| 29 | E3 | P1 | Drawer: Export PowerPoint | .pptx opens in PowerPoint; one slide per item; caption and provenance footer |
| 30 | E5 | P2 | Save view "Ride B"; reload; Open view | View restored from the server; visible on the mirror console too |
| 31 | E6 | P2 | Drawer: Share bundle / Publish phone snapshot | Single HTML file written; opens on the phone with the same numbers as step 17 |
| 32 | WRAP | P1 | 2 charts, then 1 chart | Chart A/B chips; pane B renders; no "refused to connect"; back to one pane |

## Acceptance

- All P1 steps pass on Paul's own console.
- Scope A and Scope B totals agree to the cent.
- One briefing with two items exported as .pptx and opened.
- Backstop suites are green.
