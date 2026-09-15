# Wording pass — simple to read, no slop (2026-09-14)

Ruling from Paul: "The UI should be simple to read and have no slop as to confuse the user/reader."

Source: STRING_CENSUS.md in this folder (491 rows, numbered). This file lists every row that changes, with the exact new text, and names every row that stays. Rows are the census numbers.

## Rules applied

1. One sentence says what happened; a second sentence, if any, says what to do. Nothing else.
2. No em dashes, no internal jargon in reader-facing text ("renderer", "viewport", "identifier", "register itself", "pid").
3. Refusals name the fix, not the mechanism.
4. The same situation reads the same everywhere (missing chart, read-only preview, briefing full, no image).
5. Provenance stays where it is a footer (source, basis, SHA-256, date). It leaves captions and tooltips.
6. Group limit: one number everywhere. Verified mode moves from 40 to 60 so Graph, classic and Studio all fold at 60. Ruling (b) resolved by the same rule: one number is simpler than three.

## Out of scope

Rows 156–386 (contribution-studio.html and contribution-studio.js, 231 rows). That page is the unlinked orphan feature; it was committed only because server.py routes it and a fresh checkout 404ed. Nobody reaches it from the console. Left untouched.

## Changes

| Row | file:line | Was | Now |
|---|---|---|---|
| 1 | app.js:562 | `build ${revision.slice(0, 7)} · :${build.port ?? '—'} · started ${buildStartedText(build.started_at)} · pid ${build.pid ?? '—'}` | `build ${revision.slice(0, 7)} · port ${build.port ?? '?'} · up since ${buildStartedText(build.started_at)}` |
| 3 | app.js:605 | `This read-only preview is running an older build. Close this tab and open ${location.origin}.` | `This preview runs an older build. Close this tab and open ${location.origin}.` |
| 4 | app.js:606 | `This console is running an older build. Close this tab and open ${location.origin}, or press Restart.` | `This console runs an older build. Press Restart, or close this tab and open ${location.origin}.` |
| 12 | app.js:644 | `Console already current — nothing to restart.` | `Already up to date.` |
| 13 | app.js:649 | `Restarting this console. The page reloads once the new build answers.` | `Restarting. This page reloads when the new build is ready.` |
| 14 | app.js:654 | `The restart has not answered in two minutes. Close this tab and open ${location.origin}.` | `Restart is taking too long. Close this tab and open ${location.origin}.` |
| 15 | chart-briefing.js:22 | `The briefing holds ${CAP} charts. Remove one before adding another.` | `Briefing is full (${CAP} charts). Remove one first.` |
| 19 | chart-briefing.js:126 | `Not saved in a read-only preview: this briefing is kept in this tab only.` | `Read-only preview. This briefing stays in this tab.` |
| 20 | chart-briefing.js:129 | `Server unavailable: this briefing is kept in this tab only.` | `Server unavailable. This briefing stays in this tab.` |
| 21 | chart-briefing.js:130 | `${text} This briefing is kept in this tab only.` | `${text} This briefing stays in this tab.` |
| 24 | chart-briefing.js:177 | `That chart is no longer stored on this console.` | `Chart no longer on this console.` |
| 25 | chart-briefing.js:184 | `That chart could not be read back.` | `Chart could not be read.` |
| 27 | chart-briefing.js:195 | `The export helper is not loaded on this page.` | `Export is not available. Reload the page.` |
| 29 | chart-briefing.js:221 | `The briefing holds ${CAP} charts. Remove one before adding another.` | `Briefing is full (${CAP} charts). Remove one first.` |
| 39 | chart-briefing.js:399 | `This chart is no longer stored on this console.` | `Chart no longer on this console.` |
| 41 | chart-briefing.js:453 | `This chart is no longer stored on this console.` | `Chart no longer on this console.` |
| 53 | chart-briefing.js:485 | `Every slide carries its scope, basis and source SHA-256.` | `Each slide shows its scope, basis and source.` |
| 54 | chart-briefing.js:505 | `The PowerPoint builder loaded but did not register itself.` | `PowerPoint export failed to load. Reload and try again.` |
| 55 | chart-briefing.js:508 | `This console does not serve the PowerPoint builder yet. Restart it and try again.` | `PowerPoint export needs a console restart.` |
| 56 | chart-briefing.js:522 | `The chart image could not be read back.` | `Chart image could not be read.` |
| 58 | chart-briefing.js:539 | `This chart is no longer stored on this console.` | `Chart no longer on this console.` |
| 60 | chart-briefing.js:570 | `Reading the report catalogue…` | `Loading reports…` |
| 62 | chart-briefing.js:592 | `Choose the reports the phone snapshot should carry.` | `Choose reports for the phone snapshot.` |
| 63 | chart-briefing.js:593 | `This console has no verified reports to publish.` | `No verified reports to publish.` |
| 65 | chart-briefing.js:615 | `The console did not say which job it started.` | `Publish did not start. Try again.` |
| 70 | chart-briefing.js:640 | `The phone snapshot did not finish.` | `Phone snapshot failed.` |
| 76 | chart-export.js:17 | `The chart has no exportable viewport.` | `Nothing to export.` |
| 80 | chart-studio-contributions.js:92 | `This chart type needs individual receipts. Switch Data source to Report worksheet, or select Bar, Line, Circle, Text or Map.` | `Not available for verified data. Use Bar, Line, Circle, Text or Map, or switch to Report worksheet.` |
| 81 | chart-studio-contributions.js:141 | `the basis is not Published included receipts` | `this sheet uses a different basis than Graph` |
| 82 | chart-studio-contributions.js:142 | `a Graph filter (employee level, giving type) has no verified field` | `a Graph filter (employee level or giving type) is not carried` |
| 85 | chart-studio-contributions.js:145 | `the Graph view is pinned to one election cycle and this sheet covers every cycle` | `Graph shows one election cycle and this sheet shows all of them` |
| 86 | chart-studio-contributions.js:146 | `the Graph total for this scope is not available` | `Graph has no total for this scope` |
| 87 | chart-studio-contributions.js:147 | `this is unexplained — report it` | `the cause is unknown; report it` |
| 88 | chart-studio-core.js:213 | `${channel} field encoding is unavailable in the worksheet renderer. Switch Data source to Verified contributions, or remove this field.` | `${channel} is not available for worksheet data. Remove this field or switch to Verified contributions.` |
| 91 | chart-studio-core.js:313 | `This worksheet renderer cannot draw additional measures (${unusedMeasures}). Use a two-measure scatter, separate sheets, or switch Data source to Verified contributions.` | `Worksheet charts show one measure. Not drawn: ${unusedMeasures}. Use separate sheets, a two-measure scatter, or Verified contributions.` |
| 92 | chart-studio-core.js:315 | `Scatter plots individual rows here; dimension and Detail grouping need Data source: Verified contributions.` | `Scatter shows individual rows here. Grouping needs Verified contributions.` |
| 93 | chart-studio-core.js:331 | `Numeric filters apply to source rows before aggregation. Aggregate measure filters are available in Verified contributions.` | `Number filters apply to rows, not totals. Filter totals in Verified contributions.` |
| 99 | chart-studio.js:365 | `40 per page (verified) · fold after 40 (worksheet); Graph and classic fold at 60. Totals and CSV exports include every matching group.` | `Groups shown per page. Totals and CSV exports include every group.` (and the verified default moves 40 → 60; see Code changes) |
| 100 | chart-studio.js:389 | `${field}: not carried (this source has no ${field} field)` | `${field}: not carried (not in this data)` |
| 107 | chart-studio.js:730 | `${field.name} is already on ${zone}. Use Send to … below to move it.` | `${field.name} is already on ${zone}. Use Send to… to move it.` |
| 112 | chart-studio.js:1759 | `This view has no image to copy. Download the data CSV instead.` | `No image to copy. Export the CSV instead.` |
| 113 | chart-studio.js:1763 | `Copied ${size.width}x${size.height} PNG with title and scope caption.` | `Copied image.` |
| 114 | chart-studio.js:1772 | `This view has no image to print. Download the data CSV instead.` | `No image to print. Export the CSV instead.` |
| 118 | chart-studio.js:1802 | `Saved views are read-only in this preview console; save from the original console.` | `Read-only preview. Save views from the main console.` |
| 125 | chart-studio.js:1883 | `${viewMessage(error)} "${name}" is kept in this tab only.` | `${viewMessage(error)} "${name}" stays in this tab.` |
| 126 | chart-studio.js:1894 | `Worksheet views open on the report they were saved from. Choose ${viewSourceText(view) || 'that report'} in the Data panel first.` | `Open ${viewSourceText(view) || 'that report'} in the Data panel first. This view was saved there.` |
| 127 | chart-studio.js:1896 | `Switch the Data panel to verified contribution data to open this view.` | `Switch to Verified contributions to open this view.` |
| 132 | chart-studio.js:1953 | `${viewMessage(error)} Views saved in this browser could not be moved onto this console.` | `${viewMessage(error)} Browser-saved views were not moved to this console.` |
| 141 | chart-studio.js:2256 | `Graph has no saved run selected.` | `Graph has no run selected.` |
| 142 | chart-studio.js:2316 | `Basis: ${basisLabel}. Graph shows ${money(graphCents)} for ${where} (workbook receipts). Studio total ${money(studioCents)}. ` | `Graph shows ${money(graphCents)} for ${where}. Studio shows ${money(studioCents)}. ` |
| 144 | chart-studio.js:2322 | `Differ by ${money(difference)} because ${state.reason}.` | `They differ by ${money(difference)} because ${state.reason}.` |
| 146 | chart-studio.js:2445 | `The briefing tray is not served by this console yet. Restart the console and try again.` | `Briefing needs a console restart.` |
| 147 | chart-studio.js:2519 | `Preparing cancelled. The view above is the last one that loaded.` | `Cancelled. Showing the last loaded view.` |
| 148 | chart-studio.js:2579 | `Employee level: not carried (verified data has no level field)` | `Employee level: not carried (not in verified data)` |
| 149 | chart-studio.js:2580 | `Giving type: not carried (verified data has no employee or corporate funding field)` | `Giving type: not carried (not in verified data)` |
| 150 | chart-studio.js:2581 | `Candidate view: not carried (downstream PAC activity and estimates stay in Graph)` | `Candidate view: not carried (Graph only)` |
| 151 | chart-studio.js:2582 | `Support or opposition: not carried (that distinction exists only in Graph)` | `Support or opposition: not carried (Graph only)` |
| 154 | charts.js:341 | `The briefing tray is not served by this console yet. Restart the console and try again.` | `Briefing needs a console restart.` |
| 387 | cross-reference.js:33 | `Donor not yet matched to a listed company (counted at $0)` | `Donor not matched to a listed company · counted at $0` |
| 388 | cross-reference.js:34 | `Attribution not settled (counted at $0)` | `Attribution unsettled · counted at $0` |
| 407 | cross-reference.js:113 | `Rows with an unresolved company attribution are counted at $0 in every total above; memo, transfer, earmark and role reviews stay inside Observed original giving until resolved.` | `Unresolved company attributions count as $0 in every total above. Memo, transfer, earmark and role reviews stay inside Observed original giving until resolved.` |
| 409 | graph.js:69 | `No finalized report data in this run. Choose another saved run, or check Collection for its status.` | `This run has no finalized report. Choose another run or check Collection.` |
| 410 | graph.js:103 | `Workbook included receipts, net. Same figure as Chart Studio's Published included receipts basis.` | `Net workbook receipts. Same basis as Chart Studio's Published included receipts.` |
| 413 | graph.js:254 | `This chart has no image to copy. Export its CSV instead.` | `No image to copy. Export the CSV instead.` |
| 414 | graph.js:261 | `This chart has no image to add. Export its CSV instead.` | `No image to add. Export the CSV instead.` |
| 415 | graph.js:262 | `The briefing tray is not served by this console yet. Restart the console and try again.` | `Briefing needs a console restart.` |
| 430 | index.html:187 | `Put this chart in the briefing tray` | `Add this chart to the briefing` |
| 434 | index.html:278 | `40 per page (verified) · fold after 40 (worksheet); Graph and classic fold at 60` | `Groups shown per page` |
| 442 | index.html:309 | `Every slide carries its scope, basis and source SHA-256.` | `Each slide shows its scope, basis and source.` |
| 445 | index.html:314 | `Choose the reports the phone snapshot should carry.` | `Choose reports for the phone snapshot.` |
| 449 | index.html:319 | `Uploading to the private phone link is the coordinator's step.` | `The coordinator uploads it to the phone link.` |
| 452 | server.py:928 | `That is not a saved view identifier.` | `Unknown saved view.` |
| 453 | server.py:939 | `Name the view: between 1 and 80 characters.` | `View name must be 1 to 80 characters.` |
| 454 | server.py:942 | `A saved view carries the source it was built from.` | `Saved view is missing its data source.` |
| 455 | server.py:945 | `Save between 1 and 24 sheets in one view.` | `A view holds 1 to 24 sheets.` |
| 457 | server.py:950 | `The active sheet is a sheet number.` | `Active sheet must be a sheet number.` |
| 458 | server.py:964 | `That is not a saved view identifier.` | `Unknown saved view.` |
| 459 | server.py:984 | `That is not a briefing item identifier.` | `Unknown briefing item.` |
| 460 | server.py:995 | `A briefing item carries the chart it was made from.` | `Briefing item is missing its chart.` |
| 461 | server.py:997 | `Narrow the view before adding it: this chart is over 6 MB.` | `Chart is over 6 MB. Narrow the view first.` |
| 462 | server.py:1019 | `The briefing holds 40 items. Remove one before adding another.` | `Briefing is full (40 charts). Remove one first.` |
| 463 | server.py:1031 | `That is not a briefing item identifier.` | `Unknown briefing item.` |
| 464 | server.py:1047 | `Send the briefing order as a list of item identifiers.` | `Briefing order must be a list of item ids.` |
| 465 | server.py:1054 | `The briefing order must list every item in the tray exactly once.` | `Briefing order must list every item once.` |
| 466 | server.py:1067 | `This console does not know its own port. Restart it and publish again.` | `Restart the console, then publish again.` |
| 467 | server.py:1070 | `Choose at least one dataset to publish.` | `Choose at least one report.` |
| 468 | server.py:1073 | `Choose datasets from the report catalog.` | `Choose reports from the catalog.` |
| 470 | server.py:1082 | `A phone snapshot is already being published. Wait for it to finish.` | `A phone snapshot is already publishing. Wait for it to finish.` |
| 483 | server.py:1210 | `The console that was publishing this snapshot is no longer running.` | `The publishing console stopped.` |
| 484 | server.py:1778 | `That publication is not on this console.` | `Publication not on this console.` |
| 485 | server.py:1785 | `That briefing item is not on this console.` | `Briefing item not on this console.` |
| 486 | server.py:1793 | `That saved view is not on this console.` | `Saved view not on this console.` |
| 488 | server.py:1822 | `The briefing is read-only in this preview console.` | `Read-only preview. Briefing changes are not saved.` |
| 489 | server.py:1825 | `Saved views are read-only in this preview console; save from the original console.` | `Read-only preview. Save views from the main console.` |
| 491 | server.py:1855 | `This console is still running collection work. Restart it once that finishes.` | `Collection is running. Restart after it finishes.` |

Changed rows: 96.

## Rows that stay exactly as they are

2, 5, 6, 7, 8, 9, 10, 11, 16, 17, 18, 22, 23, 26, 28, 30, 31, 32, 33, 34, 35, 36, 37, 38, 40, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 57, 59, 61, 64, 66, 67, 68, 69, 71, 72, 73, 74, 75, 77, 78, 79, 83, 84, 89, 90, 94, 95, 96, 97, 98, 101, 102, 103, 104, 105, 106, 108, 109, 110, 111, 115, 116, 117, 119, 120, 121, 122, 123, 124, 128, 129, 130, 131, 133, 134, 135, 136, 137, 138, 139, 140, 143, 145, 152, 153, 155, 389, 390, 391, 392, 393, 394, 395, 396, 397, 398, 399, 400, 401, 402, 403, 404, 405, 406, 408, 411, 412, 416, 417, 418, 419, 420, 421, 422, 423, 424, 425, 426, 427, 428, 429, 431, 432, 433, 435, 436, 437, 438, 439, 440, 441, 443, 444, 446, 447, 448, 450, 451, 456, 469, 471, 472, 473, 474, 475, 476, 477, 478, 479, 480, 481, 482, 487, 490.

Unchanged rows: 164. Out of scope: 231. Total: 96 + 164 + 231 = 491.

## Code changes beyond text

1. Verified-mode group limit default 40 → 60 (chart-studio.js `param-groups` default and any server-side page size for `/api/contributions/query` that mirrors it; keep the 40-filter cap untouched, that is a different limit). The classic builder and Graph already fold at 60.
2. Tests that pin the old strings (`mentat/tests/test_studio_wording.cjs`, `mentat/app/tests/*.test.js`, `mentat/tests/test_studio_*.py`, `test_publish_pocket.py`, `test_contribution_http.py`, browser `.cjs` suites) are updated to the new strings only. No assertion is removed or loosened; the wording suite's rule that a reason reads as the tail of "because …" still holds for rows 81, 82, 85, 86, 87.

## Rulings folded in

- (a) Money labels: the 19 cross-reference labels stand; two are tightened (rows 387, 388) and the caption is split into two sentences (row 407). The strip sentence loses "Basis:" and "(workbook receipts)" (row 142); the basis still appears in the reason when it is the cause (row 81).
- (b) Group limit: 60 everywhere.
- (c) Slide template: text unchanged (title, scope, gold rule, source footer, MENTAT, speaker notes). Only the drawer caption is simplified (rows 53, 442). Read-only refusal simplified (rows 118, 489). Single shared briefing tray stays.
