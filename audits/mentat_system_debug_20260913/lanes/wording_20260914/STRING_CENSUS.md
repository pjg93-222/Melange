# Chart Studio usability lane — user-facing string census

Scope: `git diff e666f95e5..9b14e1d -- mentat/app/*.js mentat/app/*.html mentat/app/*.css mentat/app/server.py`, commits ed64743, 215faa9, 9b14e1d, 5937875 (Chart Studio usability lane). ADDED or CHANGED lines only. `file:line` is the line number in the file **as of 9b14e1d** (the diff's right-hand/new side). Read-only census — no rewrites proposed.

**Methodology notes (read before using this table):**
- A line that the diff shows as `-`/`+` but whose visible string text is byte-identical to the old line (e.g. a trailing function argument was added, or an unrelated statement was inserted above/below) is **not** listed — the wording itself was not introduced or changed. Where a whole line's wording changed, or a brand-new line/string was added, it is listed.
- CSS files (`chart-briefing.css`, `chart-studio.css`, `contribution-studio.css`, `workspace.css`) are excluded from the table per the task's "skip CSS" instruction, even though one rule in each of `chart-studio.css` (`content:'+'`) and `contribution-studio.css` (`content:'Drop a field here'`) renders visible text via a CSS pseudo-element. Flagged here for transparency, not counted below.
- `contribution-studio.html`, `contribution-studio.js`, and `chart-briefing.js` are wholly new files in this diff range, so every visible string in them is "introduced" — all are included.
- Template placeholders are kept verbatim as `${…}` (JS) form. Unicode escapes actually rendered to the reader (`·` = `·`, `—` = `—`, `›` = `›`) are shown as the rendered character, since that is what a reader sees on screen.
- Word counts are approximate (whitespace-split), counting a `${…}` placeholder as one word.
- "Reason labels" and "reconciliation strip" rows (explicitly requested) are marked in the control/context column.

---

## mentat/app/app.js

| # | file:line | where it appears (control/context) | exact current text | words |
|---|---|---|---|---|
| 1 | app.js:562 | build stamp text in nav bar | `build ${revision.slice(0, 7)} · :${build.port ?? '—'} · started ${buildStartedText(build.started_at)} · pid ${build.pid ?? '—'}` | 14 |
| 2 | app.js:581 | stale-build banner Restart button (initial) | `Restart` | 1 |
| 3 | app.js:605 | stale-build banner message, read-only preview | `This read-only preview is running an older build. Close this tab and open ${location.origin}.` | 14 |
| 4 | app.js:606 | stale-build banner message, normal console | `This console is running an older build. Close this tab and open ${location.origin}, or press Restart.` | 16 |
| 5 | app.js:607 | stale-build banner Restart button (code-changed branch) | `Restart` | 1 |
| 6 | app.js:610 | stale-build banner message, assets changed | `Interface files changed.` | 3 |
| 7 | app.js:611 | stale-build banner button, assets changed | `Reload` | 1 |
| 8 | app.js:620 | Restart button while restarting | `Restarting…` | 1 |
| 9 | app.js:624 | restart failure, button reset | `Restart` | 1 |
| 10 | app.js:625 | restart failure banner message | `${error.message} Close this tab and open ${location.origin} instead.` | 8 |
| 11 | app.js:638 | "already current" banner, button reset | `Restart` | 1 |
| 12 | app.js:644 | "already current" banner message | `Console already current — nothing to restart.` | 7 |
| 13 | app.js:649 | restart-in-progress banner message | `Restarting this console. The page reloads once the new build answers.` | 11 |
| 14 | app.js:654 | restart-timeout banner message | `The restart has not answered in two minutes. Close this tab and open ${location.origin}.` | 14 |

**app.js: 14 rows**

---

## mentat/app/chart-briefing.js (new file)

| # | file:line | where it appears (control/context) | exact current text | words |
|---|---|---|---|---|
| 15 | chart-briefing.js:22 | model.add() over-cap error | `The briefing holds ${CAP} charts. Remove one before adding another.` | 10 |
| 16 | chart-briefing.js:74 | sourceNote sentence template (model) | `Source: ${sourceText(item) || 'workbook'} · SHA-256 ${provenanceSha(item).slice(0, 12) || 'unstated'} · basis ${item.basis || 'unstated'} · exported ${exportedOn} from Mentat Chart Studio` | 16 |
| 17 | chart-briefing.js:116 | briefing problem(), read-only preview | `This preview console is read-only.` | 5 |
| 18 | chart-briefing.js:119 | briefing problem(), generic failure | `Server unavailable.` | 2 |
| 19 | chart-briefing.js:126 | briefing refusal(), read-only preview | `Not saved in a read-only preview: this briefing is kept in this tab only.` | 14 |
| 20 | chart-briefing.js:129 | briefing refusal(), server unavailable | `Server unavailable: this briefing is kept in this tab only.` | 10 |
| 21 | chart-briefing.js:130 | briefing refusal(), other error suffix | `${text} This briefing is kept in this tab only.` | 9 |
| 22 | chart-briefing.js:136 | getJSON() fetch failure | `Server unavailable (${response.status}).` | 4 |
| 23 | chart-briefing.js:140 | post() when api() missing | `Server unavailable.` | 2 |
| 24 | chart-briefing.js:177 | svgFor() fetch failure | `That chart is no longer stored on this console.` | 9 |
| 25 | chart-briefing.js:184 | nodeFor() parse failure | `That chart could not be read back.` | 7 |
| 26 | chart-briefing.js:194 | describe(), no chart to add | `Build a chart before adding it to the briefing.` | 9 |
| 27 | chart-briefing.js:195 | describe(), MentatExport missing | `The export helper is not loaded on this page.` | 9 |
| 28 | chart-briefing.js:198 | describe(), oversized SVG | `Narrow the view before adding it` | 6 |
| 29 | chart-briefing.js:221 | add(), over-cap notice (drawer) | `The briefing holds ${CAP} charts. Remove one before adding another.` | 10 |
| 30 | chart-briefing.js:291 | thumbnail paint failure | `No image` | 2 |
| 31 | chart-briefing.js:306 | card title fallback | `Chart` | 1 |
| 32 | chart-briefing.js:318 | card action button | `Move up` | 2 |
| 33 | chart-briefing.js:319 | card action button | `Move down` | 2 |
| 34 | chart-briefing.js:320 | card action button | `Remove` | 1 |
| 35 | chart-briefing.js:337 | drawer item-count chip | `${count} item${count === 1 ? '' : 's'}` | 2 |
| 36 | chart-briefing.js:346 | drawer empty state | `Nothing in the briefing yet. Use "Add to briefing" on a chart.` | 12 |
| 37 | chart-briefing.js:363 | guard() failure prefix | `${label}: ${error.message || 'that did not finish.'}` | 4 |
| 38 | chart-briefing.js:377 | speakerNotes template, console line | `Console ${consoleUrl()}` | 2 |
| 39 | chart-briefing.js:399 | Print briefing, missing chart | `This chart is no longer stored on this console.` | 9 |
| 40 | chart-briefing.js:412 | Print briefing, sheet mark | `MENTAT` | 1 |
| 41 | chart-briefing.js:453 | HTML bundle, missing chart markup | `This chart is no longer stored on this console.` | 9 |
| 42 | chart-briefing.js:462 | HTML bundle, section mark | `MENTAT` | 1 |
| 43 | chart-briefing.js:475 | HTML bundle `<title>` | `Mentat briefing · ${dateLabel()}` | 3 |
| 44 | chart-briefing.js:477 | HTML bundle `<h1>` | `Briefing` | 1 |
| 45 | chart-briefing.js:478 | HTML bundle lead paragraph | `${items.length} chart${items.length === 1 ? '' : 's'} · exported ${dateLabel()} from Mentat Chart Studio · ${consoleUrl()}` | 9 |
| 46 | chart-briefing.js:482 | HTML bundle `<h2>` | `Provenance` | 1 |
| 47 | chart-briefing.js:483 | HTML bundle provenance table header | `#` | 1 |
| 48 | chart-briefing.js:483 | HTML bundle provenance table header | `Chart` | 1 |
| 49 | chart-briefing.js:483 | HTML bundle provenance table header | `Scope` | 1 |
| 50 | chart-briefing.js:483 | HTML bundle provenance table header | `Basis` | 1 |
| 51 | chart-briefing.js:484 | HTML bundle provenance table header | `Workbook` | 1 |
| 52 | chart-briefing.js:484 | HTML bundle provenance table header | `Workbook SHA-256` | 2 |
| 53 | chart-briefing.js:485 | HTML bundle lead caption | `Every slide carries its scope, basis and source SHA-256.` | 9 |
| 54 | chart-briefing.js:505 | PowerPoint loader, script loaded but no global | `The PowerPoint builder loaded but did not register itself.` | 9 |
| 55 | chart-briefing.js:508 | PowerPoint loader, script failed | `This console does not serve the PowerPoint builder yet. Restart it and try again.` | 14 |
| 56 | chart-briefing.js:522 | pngFor(), FileReader failure | `The chart image could not be read back.` | 8 |
| 57 | chart-briefing.js:532 | slide.addText title fallback | `Chart` | 1 |
| 58 | chart-briefing.js:539 | slide.addText, missing chart image | `This chart is no longer stored on this console.` | 9 |
| 59 | chart-briefing.js:548 | slide.addText, corner mark | `MENTAT` | 1 |
| 60 | chart-briefing.js:570 | share dialog, opening progress | `Reading the report catalogue…` | 4 |
| 61 | chart-briefing.js:587 | share dialog, dataset unavailable suffix | `— ${dataset.message || 'unavailable'}` | 2 |
| 62 | chart-briefing.js:592 | share dialog, datasets loaded | `Choose the reports the phone snapshot should carry.` | 8 |
| 63 | chart-briefing.js:593 | share dialog, no datasets | `This console has no verified reports to publish.` | 8 |
| 64 | chart-briefing.js:607 | share dialog, none checked | `Choose at least one report first.` | 6 |
| 65 | chart-briefing.js:615 | publishPocket(), no job id returned | `The console did not say which job it started.` | 9 |
| 66 | chart-briefing.js:616 | publishPocket(), started | `Building the phone snapshot…` | 4 |
| 67 | chart-briefing.js:632 | pollPocket(), succeeded fallback | `Phone snapshot built.` | 3 |
| 68 | chart-briefing.js:634 | pollPocket(), output path known | `Written to ${body.output_path}` | 3 |
| 69 | chart-briefing.js:635 | pollPocket(), output path unknown | `Written on the console.` | 4 |
| 70 | chart-briefing.js:640 | pollPocket(), failed fallback | `The phone snapshot did not finish.` | 6 |
| 71 | chart-briefing.js:644 | pollPocket(), in-progress with elapsed | `${body.message || 'Building the phone snapshot…'} · ${elapsed}s elapsed` | 5 |
| 72 | chart-briefing.js:646 | pollPocket(), 15-minute stall | `Still building after 15 minutes. Check the console window.` | 9 |
| 73 | chart-briefing.js:665 | guard() label for PPTX export | `Export PowerPoint` | 2 |
| 74 | chart-briefing.js:666 | guard() label for print | `Print briefing` | 2 |
| 75 | chart-briefing.js:667 | guard() label for HTML bundle | `HTML bundle` | 2 |

**chart-briefing.js: 61 rows**

---

## mentat/app/chart-export.js

| # | file:line | where it appears (control/context) | exact current text | words |
|---|---|---|---|---|
| 76 | chart-export.js:17 | compose(), invalid viewBox | `The chart has no exportable viewport.` | 6 |
| 77 | chart-export.js:83 | copy(), insecure/unsupported context | `Copy needs Chrome or Edge at localhost. Download the PNG instead.` | 11 |
| 78 | chart-export.js:90 | copy(), clipboard permission denied | `Click the chart, then copy again, or download the PNG.` | 10 |

**chart-export.js: 3 rows**

---

## mentat/app/chart-studio-contributions.js

| # | file:line | where it appears (control/context) | exact current text | words |
|---|---|---|---|---|
| 79 | chart-studio-contributions.js:83 | compile(), no measure placed | `Add a dollar or count measure to Rows or Columns.` | 10 |
| 80 | chart-studio-contributions.js:92 | compile(), unsupported mark type | `This chart type needs individual receipts. Switch Data source to Report worksheet, or select Bar, Line, Circle, Text or Map.` | 20 |
| 81 | chart-studio-contributions.js:141 | RECONCILE_REASONS.basis | `the basis is not Published included receipts` | 7 |
| 82 | chart-studio-contributions.js:142 | RECONCILE_REASONS.graph_filter | `a Graph filter (employee level, giving type) has no verified field` | 11 |
| 83 | chart-studio-contributions.js:143 | RECONCILE_REASONS.workbook | `the workbook version differs` | 4 |
| 84 | chart-studio-contributions.js:144 | RECONCILE_REASONS.aggregate | `grouped filters apply after aggregation` | 5 |
| 85 | chart-studio-contributions.js:145 | RECONCILE_REASONS.cycle | `the Graph view is pinned to one election cycle and this sheet covers every cycle` | 16 |
| 86 | chart-studio-contributions.js:146 | RECONCILE_REASONS.unavailable | `the Graph total for this scope is not available` | 10 |
| 87 | chart-studio-contributions.js:147 | RECONCILE_REASONS.unexplained | `this is unexplained — report it` | 6 |

**chart-studio-contributions.js: 9 rows**

---

## mentat/app/chart-studio-core.js

| # | file:line | where it appears (control/context) | exact current text | words |
|---|---|---|---|---|
| 88 | chart-studio-core.js:213 | worksheet compile(), unsupported channel encoding | `${channel} field encoding is unavailable in the worksheet renderer. Switch Data source to Verified contributions, or remove this field.` | 19 |
| 89 | chart-studio-core.js:232 | worksheet compile(), no grouping/measure (orientation=none) | `Add a grouping (company, recipient, cycle) and a dollar measure.` | 11 |
| 90 | chart-studio-core.js:262 | worksheet compile(), no grouping/measure (bar path) | `Add a grouping (company, recipient, cycle) and a dollar measure.` | 11 |
| 91 | chart-studio-core.js:313 | worksheet compile(), extra unused measures | `This worksheet renderer cannot draw additional measures (${unusedMeasures}). Use a two-measure scatter, separate sheets, or switch Data source to Verified contributions.` | 22 |
| 92 | chart-studio-core.js:315 | worksheet compile(), scatter with grouping | `Scatter plots individual rows here; dimension and Detail grouping need Data source: Verified contributions.` | 14 |
| 93 | chart-studio-core.js:331 | worksheet compile(), numeric filter note | `Numeric filters apply to source rows before aggregation. Aggregate measure filters are available in Verified contributions.` | 15 |

**chart-studio-core.js: 6 rows**

---

## mentat/app/chart-studio.js

| # | file:line | where it appears (control/context) | exact current text | words |
|---|---|---|---|---|
| 94 | chart-studio.js:24 | CLICK_HINT constant, field pill tooltip/aria fragment | `Click to add · drag to place · Enter for actions` | 9 |
| 95 | chart-studio.js:164 | renderSourceSummary(), folded-panel summary seed | `Data source` | 2 |
| 96 | chart-studio.js:172 | renderSourceSummary(), ready state word | `ready` | 1 |
| 97 | chart-studio.js:219 | tickProgress(), elapsed-time suffix | `${mm}:${ss} elapsed` | 2 |
| 98 | chart-studio.js:326 | contributionReady(), showProgress message | `Preparing verified data · ${waiting}` | 4 |
| 99 | chart-studio.js:365 | Group-limit field tooltip (verified/contributions pane) | `40 per page (verified) · fold after 40 (worksheet); Graph and classic fold at 60. Totals and CSV exports include every matching group.` | 21 |
| 100 | chart-studio.js:389 | applyGraphScope(), field not carried note | `${field}: not carried (this source has no ${field} field)` | 9 |
| 101 | chart-studio.js:412 | renderContributionView(), no dataset chosen | `Choose a verified report in the Data panel to begin.` | 9 |
| 102 | chart-studio.js:427 | renderContributionView(), group-count line | `${first}–${last} of ${group_count} groups · totals cover all ${group_count}` | 8 |
| 103 | chart-studio.js:520 | field pill aria-label, unplaced field | `${label}, field. Click to add · drag to place · Enter for actions.` | 10 |
| 104 | chart-studio.js:717 | quickAdd(), field already placed | `${field.name} is already on ${zone}.` | 6 |
| 105 | chart-studio.js:720 | quickAdd(), field placed via click | `Added ${field.name} to ${zone}.` | 5 |
| 106 | chart-studio.js:730 | field context menu, disabled entry label | `Add to a shelf` | 4 |
| 107 | chart-studio.js:730 | field context menu, disabled entry reason | `${field.name} is already on ${zone}. Use Send to … below to move it.` | 12 |
| 108 | chart-studio.js:732 | field context menu, quick-add entry | `Add to ${zone}` | 3 |
| 109 | chart-studio.js:1471 | renderView(), no worksheet data | `Choose a report worksheet in the Data panel to begin.` | 9 |
| 110 | chart-studio.js:1711 | CSV export, new "Note" row | `Note` | 1 |
| 111 | chart-studio.js:1729 | currentChart(), basis label for worksheet mode | `Worksheet values` | 2 |
| 112 | chart-studio.js:1759 | copyImage(), nothing to copy | `This view has no image to copy. Download the data CSV instead.` | 11 |
| 113 | chart-studio.js:1763 | copyImage(), success status | `Copied ${size.width}x${size.height} PNG with title and scope caption.` | 8 |
| 114 | chart-studio.js:1772 | printChart(), nothing to print | `This view has no image to print. Download the data CSV instead.` | 11 |
| 115 | chart-studio.js:1777 | printChart(), print footer source line | `Source ${chart.sourceLabel}` | 2 |
| 116 | chart-studio.js:1778 | printChart(), print footer workbook hash | `Workbook SHA-256 ${chart.sha}` | 3 |
| 117 | chart-studio.js:1779 | printChart(), print footer date | `Printed ${date}` | 2 |
| 118 | chart-studio.js:1802 | viewMessage(), read-only preview | `Saved views are read-only in this preview console; save from the original console.` | 13 |
| 119 | chart-studio.js:1804 | viewMessage(), generic failure | `Server unavailable.` | 2 |
| 120 | chart-studio.js:1811 | getJSON(), fetch failure | `Server unavailable (${response.status}).` | 3 |
| 121 | chart-studio.js:1836 | storeKeyLabel(), fallback label | `worksheet` | 1 |
| 122 | chart-studio.js:1842 | viewLabel(), memory-only badge | `this tab only` | 3 |
| 123 | chart-studio.js:1853 | saveView(), rename-input aria-label | `View name` | 2 |
| 124 | chart-studio.js:1877 | saveViewNamed(), success status | `Saved view "${name}" · ${record.sheets.length} sheet${… === 1 ? '' : 's'}.` | 6 |
| 125 | chart-studio.js:1883 | saveViewNamed(), server refused, kept locally | `${viewMessage(error)} "${name}" is kept in this tab only.` | 8 |
| 126 | chart-studio.js:1894 | openability(), wrong source (worksheet view) | `Worksheet views open on the report they were saved from. Choose ${viewSourceText(view) || 'that report'} in the Data panel first.` | 16 |
| 127 | chart-studio.js:1896 | openability(), not in verified mode | `Switch the Data panel to verified contribution data to open this view.` | 12 |
| 128 | chart-studio.js:1898 | openability(), unknown report | `This console has no report called ${parts[1]}.` | 7 |
| 129 | chart-studio.js:1899 | openability(), report unavailable fallback | `That report is unavailable on this console.` | 7 |
| 130 | chart-studio.js:1911 | openView(), empty view | `That saved view has no sheets in it.` | 8 |
| 131 | chart-studio.js:1923 | openView(), success status | `Opened view "${full.name}".` | 3 |
| 132 | chart-studio.js:1953 | migrateStoredViews(), server refused | `${viewMessage(error)} Views saved in this browser could not be moved onto this console.` | 12 |
| 133 | chart-studio.js:1973 | openViews() menu, group label | `This source` | 2 |
| 134 | chart-studio.js:1975 | openViews() menu, no views for source | `No saved views for this source yet` | 7 |
| 135 | chart-studio.js:1976 | openViews() menu, disabled-item reason | `Save one with Export › Save view.` | 6 |
| 136 | chart-studio.js:1977 | openViews() menu, group label | `Other sources` | 2 |
| 137 | chart-studio.js:1985 | openViews() menu, no other-source views | `None` | 1 |
| 138 | chart-studio.js:1985 | openViews() menu, disabled-item reason | `Views saved on other reports appear here.` | 7 |
| 139 | chart-studio.js:2185 | Inspector toggle aria-label, filters active | `Inspector · ${rows.length} active filter${rows.length === 1 ? '' : 's'}` | 4 |
| 140 | chart-studio.js:2186 | Inspector toggle aria-label, no filters | `Inspector` | 1 |
| 141 | chart-studio.js:2256 | graphTotals(), no Graph run | `Graph has no saved run selected.` | 6 |
| 142 | chart-studio.js:2316 | reconciliation strip, lead sentence | `Basis: ${basisLabel}. Graph shows ${money(graphCents)} for ${where} (workbook receipts). Studio total ${money(studioCents)}. ` | 13 |
| 143 | chart-studio.js:2321 | reconciliation strip, verdict (agree) | `Agree.` | 1 |
| 144 | chart-studio.js:2322 | reconciliation strip, verdict (differ) | `Differ by ${money(difference)} because ${state.reason}.` | 5 |
| 145 | chart-studio.js:2326 | reconciliation strip, link to Cross-reference | `Why Cross-reference differs` | 3 |
| 146 | chart-studio.js:2445 | Add-to-briefing click handler, tray not served | `The briefing tray is not served by this console yet. Restart the console and try again.` | 16 |
| 147 | chart-studio.js:2519 | progress-cancel click handler, status | `Preparing cancelled. The view above is the last one that loaded.` | 11 |
| 148 | chart-studio.js:2579 | GRAPH_NOT_CARRIED, tier — composed scope-note sentence | `Employee level: not carried (verified data has no level field)` | 9 |
| 149 | chart-studio.js:2580 | GRAPH_NOT_CARRIED, funding — composed scope-note sentence | `Giving type: not carried (verified data has no employee or corporate funding field)` | 12 |
| 150 | chart-studio.js:2581 | GRAPH_NOT_CARRIED, mode — composed scope-note sentence | `Candidate view: not carried (downstream PAC activity and estimates stay in Graph)` | 11 |
| 151 | chart-studio.js:2582 | GRAPH_NOT_CARRIED, direction — composed scope-note sentence | `Support or opposition: not carried (that distinction exists only in Graph)` | 10 |

**chart-studio.js: 58 rows**

---

## mentat/app/charts.js

| # | file:line | where it appears (control/context) | exact current text | words |
|---|---|---|---|---|
| 152 | charts.js:29 | measureLabel(), count aggregation with a real column | `Count of ${columnLabel(config.y, source)}` | 3 |
| 153 | charts.js:31 | measureLabel(), split result suffix | `${measured} · coverage` | 3 |
| 154 | charts.js:341 | Add-to-briefing click handler, tray not served | `The briefing tray is not served by this console yet. Restart the console and try again.` | 16 |
| 155 | charts.js:345 | Add-to-briefing, basis metadata | `Worksheet values` | 2 |

**charts.js: 4 rows**

---

## mentat/app/contribution-studio.html (new file)

| # | file:line | where it appears (control/context) | exact current text | words |
|---|---|---|---|---|
| 156 | contribution-studio.html:3 | `<title>` | `Contribution Studio · MENTAT` | 4 |
| 157 | contribution-studio.html:8 | skip link | `Skip to analysis` | 3 |
| 158 | contribution-studio.html:9 | header wordmark link | `MENTAT` | 1 |
| 159 | contribution-studio.html:9 | header product label | `Contribution Studio` | 2 |
| 160 | contribution-studio.html:9 | nav aria-label | `Mentat workspaces` | 2 |
| 161 | contribution-studio.html:9 | nav link | `Collection` | 1 |
| 162 | contribution-studio.html:9 | nav link | `Cross-reference` | 1 |
| 163 | contribution-studio.html:9 | nav link | `Worksheet explorer` | 2 |
| 164 | contribution-studio.html:9 | header badge | `Local workspace` | 2 |
| 165 | contribution-studio.html:11 | aside aria-label | `Data and fields` | 3 |
| 166 | contribution-studio.html:12 | Data pane heading | `Data` | 1 |
| 167 | contribution-studio.html:12 | refresh button title | `Refresh available sources` | 3 |
| 168 | contribution-studio.html:12 | refresh button aria-label | `Refresh sources` | 2 |
| 169 | contribution-studio.html:12 | refresh button glyph | `↻` | 1 |
| 170 | contribution-studio.html:13 | source select label | `Industry / source` | 3 |
| 171 | contribution-studio.html:13 | source select loading option | `Loading sources…` | 2 |
| 172 | contribution-studio.html:14 | basis select label | `Accounting basis` | 2 |
| 173 | contribution-studio.html:15 | cycle select label | `Election cycle` | 2 |
| 174 | contribution-studio.html:15 | cycle select default option | `All available cycles` | 3 |
| 175 | contribution-studio.html:16 | company select label | `Company` | 1 |
| 176 | contribution-studio.html:16 | company select default option | `All tracked companies` | 3 |
| 177 | contribution-studio.html:17 | Fields heading | `Fields` | 1 |
| 178 | contribution-studio.html:17 | Fields hint | `Drag or select +` | 4 |
| 179 | contribution-studio.html:18 | field search sr-only label | `Search fields` | 2 |
| 180 | contribution-studio.html:18 | field search placeholder | `Find a field…` | 3 |
| 181 | contribution-studio.html:20 | source details summary | `Source & accounting` | 3 |
| 182 | contribution-studio.html:22 | analysis section aria-label | `Contribution analysis` | 2 |
| 183 | contribution-studio.html:23 | eyebrow text | `EXPLORE THE MONEY` | 3 |
| 184 | contribution-studio.html:23 | view title default | `Giving by company` | 3 |
| 185 | contribution-studio.html:23 | Undo button title | `Undo the last view change` | 5 |
| 186 | contribution-studio.html:23 | view action button | `Undo` | 1 |
| 187 | contribution-studio.html:23 | view action button | `Reset view` | 2 |
| 188 | contribution-studio.html:23 | view action button | `Export CSV` | 2 |
| 189 | contribution-studio.html:23 | view action button | `SVG` | 1 |
| 190 | contribution-studio.html:23 | view action button | `PNG` | 1 |
| 191 | contribution-studio.html:24 | shelf label | `Dimensions` | 1 |
| 192 | contribution-studio.html:24 | shelf aria-label | `Dimensions shelf` | 2 |
| 193 | contribution-studio.html:24 | shelf label | `Measures` | 1 |
| 194 | contribution-studio.html:24 | shelf aria-label | `Measures shelf` | 2 |
| 195 | contribution-studio.html:25 | filter bar caption | `Filters` | 1 |
| 196 | contribution-studio.html:25 | add-filter button | `+ Add filter` | 3 |
| 197 | contribution-studio.html:26 | filter editor label | `Field` | 1 |
| 198 | contribution-studio.html:26 | filter op option | `Equals` | 1 |
| 199 | contribution-studio.html:26 | filter op option | `Contains` | 1 |
| 200 | contribution-studio.html:26 | filter op option | `At least` | 2 |
| 201 | contribution-studio.html:26 | filter op option | `At most` | 2 |
| 202 | contribution-studio.html:26 | filter editor label | `Match` | 1 |
| 203 | contribution-studio.html:26 | filter editor label | `Value` | 1 |
| 204 | contribution-studio.html:26 | filter editor label | `Apply to` | 2 |
| 205 | contribution-studio.html:26 | filter stage option | `Source records` | 2 |
| 206 | contribution-studio.html:26 | filter stage option | `Grouped measure` | 2 |
| 207 | contribution-studio.html:26 | filter editor submit button | `Apply` | 1 |
| 208 | contribution-studio.html:26 | filter editor cancel button | `Cancel` | 1 |
| 209 | contribution-studio.html:27 | chart type group aria-label | `Chart type` | 2 |
| 210 | contribution-studio.html:27 | chart type button | `Bars` | 1 |
| 211 | contribution-studio.html:27 | chart type button | `Line` | 1 |
| 212 | contribution-studio.html:27 | chart type button | `Area` | 1 |
| 213 | contribution-studio.html:27 | chart type button | `Scatter` | 1 |
| 214 | contribution-studio.html:27 | chart type button | `Map` | 1 |
| 215 | contribution-studio.html:27 | chart type button | `Table` | 1 |
| 216 | contribution-studio.html:28 | status line, initial | `Connecting to saved contribution sources…` | 5 |
| 217 | contribution-studio.html:29 | visualization aria-label | `Contribution visualization` | 2 |
| 218 | contribution-studio.html:30 | pager button | `Previous` | 1 |
| 219 | contribution-studio.html:30 | pager button | `Next` | 1 |
| 220 | contribution-studio.html:31 | inspection heading | `Underlying records` | 2 |
| 221 | contribution-studio.html:31 | inspection close aria-label | `Close underlying records` | 3 |
| 222 | contribution-studio.html:31 | inspection close glyph | `×` | 1 |
| 223 | contribution-studio.html:31 | inspection pager button | `Next records` | 2 |
| 224 | contribution-studio.html:32 | view name sr-only label | `View name` | 2 |
| 225 | contribution-studio.html:32 | view name default value | `Giving by company` | 3 |
| 226 | contribution-studio.html:32 | save view button | `Save view` | 2 |
| 227 | contribution-studio.html:32 | saved views sr-only label | `Saved views` | 2 |
| 228 | contribution-studio.html:32 | saved view default option | `Open a saved view…` | 4 |
| 229 | contribution-studio.html:34 | settings aside aria-label | `View settings` | 2 |
| 230 | contribution-studio.html:34 | settings heading | `View settings` | 2 |
| 231 | contribution-studio.html:35 | colour select label | `Colour by` | 2 |
| 232 | contribution-studio.html:35 | colour default option | `Single colour` | 2 |
| 233 | contribution-studio.html:36 | sort select label | `Order` | 1 |
| 234 | contribution-studio.html:36 | sort option | `Largest measure first` | 3 |
| 235 | contribution-studio.html:36 | sort option | `Smallest measure first` | 3 |
| 236 | contribution-studio.html:36 | sort option | `Dimension order` | 2 |
| 237 | contribution-studio.html:37 | limit select label | `Groups per page` | 3 |
| 238 | contribution-studio.html:37 | limit option | `25` | 1 |
| 239 | contribution-studio.html:37 | limit option | `50` | 1 |
| 240 | contribution-studio.html:37 | limit option | `100` | 1 |
| 241 | contribution-studio.html:37 | limit option | `500` | 1 |
| 242 | contribution-studio.html:38 | labels checkbox | `Show values` | 2 |
| 243 | contribution-studio.html:39 | map settings heading | `Map layers` | 2 |
| 244 | contribution-studio.html:39 | layer checkbox | `State outlines` | 2 |
| 245 | contribution-studio.html:39 | layer checkbox | `Congressional districts` | 2 |
| 246 | contribution-studio.html:39 | layer checkbox | `ZIP areas` | 2 |
| 247 | contribution-studio.html:39 | congress select label | `Congressional boundaries` | 2 |
| 248 | contribution-studio.html:39 | congress option | `119th Congress` | 2 |
| 249 | contribution-studio.html:39 | congress option | `120th Congress` | 2 |
| 250 | contribution-studio.html:39 | map settings caption | `ZIP areas use Census ZCTAs. Boundaries add context; they do not allocate dollars.` | 12 |
| 251 | contribution-studio.html:40 | receipt heading | `Accounting receipt` | 2 |
| 252 | contribution-studio.html:40 | receipt-basis default | `Awaiting source` | 2 |
| 253 | contribution-studio.html:40 | inspect-all button | `Inspect selected records` | 3 |
| 254 | contribution-studio.html:40 | reconciliation summary | `Reconciliation & coverage` | 3 |
| 255 | contribution-studio.html:41 | guide heading | `A question to start with` | 5 |
| 256 | contribution-studio.html:41 | preset button | `Which companies gave?` | 3 |
| 257 | contribution-studio.html:41 | preset button | `Who received it?` | 3 |
| 258 | contribution-studio.html:41 | preset button | `How did giving change?` | 4 |
| 259 | contribution-studio.html:41 | preset button | `Where did giving originate?` | 4 |
| 260 | contribution-studio.html:43 | footer | `MENTAT · Evidence behind every view` | 6 |

**contribution-studio.html: 105 rows**

---

## mentat/app/contribution-studio.js (new file)

| # | file:line | where it appears (control/context) | exact current text | words |
|---|---|---|---|---|
| 261 | contribution-studio.js:7 | basisLabel(), original_supported fallback | `Supported original giving (gross subset)` | 5 |
| 262 | contribution-studio.js:8 | basisFields(), field relabel for original_supported | `Supported gross amount` | 3 |
| 263 | contribution-studio.js:24 | filterValue(), non-numeric measure value | `Enter a number without a currency symbol or commas.` | 9 |
| 264 | contribution-studio.js:26 | filterValue(), fractional cents on a dollar field | `Use an amount with at most two decimal places.` | 9 |
| 265 | contribution-studio.js:26 | filterValue(), non-integer count field | `Use a whole count.` | 4 |
| 266 | contribution-studio.js:27 | filterValue(), rounding-precision guard | `Use an amount with at most two decimal places.` | 9 |
| 267 | contribution-studio.js:52 | calendarNotice(), ongoing cycle note | `${cycleEnd - 1}–${cycleEnd} is an ongoing calendar cycle` | 6 |
| 268 | contribution-studio.js:53 | calendarNotice(), ongoing year note | `${year} is an ongoing calendar year` | 6 |
| 269 | contribution-studio.js:54 | calendarNotice(), coverage caveat suffix | `. Collection coverage is not established.` | 5 |
| 270 | contribution-studio.js:71 | failure(), status line | `View unavailable. Adjust the selection or retry.` | 7 |
| 271 | contribution-studio.js:74 | request(), API error fallback | `Contribution service unavailable.` | 3 |
| 272 | contribution-studio.js:80 | ready(), verification failed | `The source index could not be verified.` | 7 |
| 273 | contribution-studio.js:82 | ready(), preparing progress fallback | `Verifying source records and building the contribution index…` | 8 |
| 274 | contribution-studio.js:90 | basis-help description, original_observed | `Evidence-aware original giving. Ambiguous observations remain provisional; review the supported subset and unresolved exposure.` | 14 |
| 275 | contribution-studio.js:90 | basis-help description, original_supported | `Supported original giving is a gross subset of positive amounts supported by the current evidence rules. Refunds are excluded. This is not the complete amount given.` | 27 |
| 276 | contribution-studio.js:90 | basis-help description, receipt | `Matches the workbook's included receipts. Receipts may repeat economic gifts or include intermediary stages.` | 14 |
| 277 | contribution-studio.js:90 | basis-help description, raw | `Every retained source observation, including excluded and repeated representations. This is not a giving total.` | 15 |
| 278 | contribution-studio.js:90 | basis-help description, pac_activity | `Recipient-reported PAC activity, separate from original giving. Coverage is not a complete Schedule B ledger.` | 15 |
| 279 | contribution-studio.js:106 | shelf pill remove button aria-label | `Remove ${fieldName(id)}` | 2 |
| 280 | contribution-studio.js:111 | grain-label, map view | `One mark per ZIP, combining selected ZIP/state groups. Recorded state determines map eligibility.` | 12 |
| 281 | contribution-studio.js:111 | grain-label, with dimensions | `One mark per ${dims}` | 4 |
| 282 | contribution-studio.js:111 | grain-label, no dimensions | `One mark for all selected records` | 6 |
| 283 | contribution-studio.js:112 | view-title subject, original_observed | `Observed giving` | 2 |
| 284 | contribution-studio.js:112 | view-title subject, original_supported | `Supported original giving (gross subset)` | 5 |
| 285 | contribution-studio.js:112 | view-title subject, receipt | `Included receipts` | 2 |
| 286 | contribution-studio.js:112 | view-title subject, raw | `Raw observations` | 2 |
| 287 | contribution-studio.js:112 | view-title subject, pac_activity | `PAC receipts` | 2 |
| 288 | contribution-studio.js:112 | view-title subject fallback | `Contributions` | 1 |
| 289 | contribution-studio.js:113 | view-title suffix, map | ` by Contributor ZIP` | 3 |
| 290 | contribution-studio.js:113 | view-title suffix, dimensioned | ` by ${dims}` | 2 |
| 291 | contribution-studio.js:113 | view-title suffix, ungrouped | ` in this selection` | 3 |
| 292 | contribution-studio.js:119 | Fields panel section heading | `Dimensions` | 1 |
| 293 | contribution-studio.js:119 | Fields panel section heading | `Measures` | 1 |
| 294 | contribution-studio.js:122 | field row glyph, ZIP field | `◎` | 1 |
| 295 | contribution-studio.js:122 | field row glyph, other dimension | `Abc` | 1 |
| 296 | contribution-studio.js:122 | field row glyph, measure | `#` | 1 |
| 297 | contribution-studio.js:123 | field row add-button aria-label | `Add ${f.label} to ${role}s` | 4 |
| 298 | contribution-studio.js:133 | filter chip, aggregate-stage prefix | `Grouped ` | 1 |
| 299 | contribution-studio.js:134 | filter chip remove aria-label | `Remove filter ${fieldName(f.field)}` | 3 |
| 300 | contribution-studio.js:138 | source-info row label | `Workbook` | 1 |
| 301 | contribution-studio.js:138 | source-info row label | `Cycle basis` | 2 |
| 302 | contribution-studio.js:138 | source-info row label | `Coverage` | 1 |
| 303 | contribution-studio.js:138 | source-info row label | `Workbook SHA-256` | 2 |
| 304 | contribution-studio.js:138 | source-info row label | `Analytical source SHA-256` | 3 |
| 305 | contribution-studio.js:138 | source-info row label | `Original report source SHA-256` | 4 |
| 306 | contribution-studio.js:141 | footer source stamp suffix | ` · SHA ${sha12}` | 3 |
| 307 | contribution-studio.js:145 | receipt line item, gross basis | `Selected gross amount` | 3 |
| 308 | contribution-studio.js:145 | receipt line item, net basis | `Selected net amount` | 3 |
| 309 | contribution-studio.js:145 | receipt line item | `Included observations` | 2 |
| 310 | contribution-studio.js:145 | receipt line item | `Reported donor identities` | 3 |
| 311 | contribution-studio.js:146 | receipt line item (comparison) | `Supported gross subset` | 3 |
| 312 | contribution-studio.js:146 | receipt line item (comparison) | `Unresolved exposure¹` | 2 |
| 313 | contribution-studio.js:147 | receipt line item (grouped filters) | `After grouped filters` | 3 |
| 314 | contribution-studio.js:149 | receipt-scope caption suffix | `. Totals cover matching source records before grouped filters. ¹ Absolute raw exposure flagged unresolved; it overlaps the selected amount and must not be added to it.` | 27 |
| 315 | contribution-studio.js:152 | reconciliation line, match true | `Included receipt amounts reconcile exactly to the pinned workbook.` | 10 |
| 316 | contribution-studio.js:152 | reconciliation line, match false | `Receipt reconciliation failed. This source needs review.` | 7 |
| 317 | contribution-studio.js:152 | reconciliation line, match unavailable | `Receipt reconciliation is unavailable.` | 4 |
| 318 | contribution-studio.js:152 | reconciliation line, conserved | `Grouping preserves the selected amount to the cent.` | 9 |
| 319 | contribution-studio.js:152 | reconciliation line, grouped-filter subset | `Grouped filters select a subset after aggregation.` | 7 |
| 320 | contribution-studio.js:158 | empty-view heading | `Preparing your view` | 3 |
| 321 | contribution-studio.js:158 | empty-view caption | `Checking the source and accounting basis…` | 6 |
| 322 | contribution-studio.js:159 | receipt-basis placeholder before first result | `Awaiting verified result` | 3 |
| 323 | contribution-studio.js:163 | status line, run() start | `Reading verified contribution records…` | 4 |
| 324 | contribution-studio.js:165 | run(), source unavailable fallback | `Select an available source.` | 4 |
| 325 | contribution-studio.js:167 | run(), no measures | `Add at least one measure to create a view.` | 9 |
| 326 | contribution-studio.js:168 | run(), invalid ZIP-map shelf state | `The ZIP map uses Contributor ZIP, recorded state and the selected amount. Select the map preset to restore those fields.` | 20 |
| 327 | contribution-studio.js:182 | loadFacets(), quick-filter load failure | `Chart ready. Quick filters could not load; use Add filter.` | 10 |
| 328 | contribution-studio.js:189 | render(), result-count with groups | `${first}–${last} of ${group_count} groups · select a mark for records` | 9 |
| 329 | contribution-studio.js:189 | render(), result-count empty | `No included observations in this selection.` | 6 |
| 330 | contribution-studio.js:195 | render(), status suffix | `Totals include groups on every page.` | 6 |
| 331 | contribution-studio.js:195 | render(), status suffix | `All matching groups shown.` | 4 |
| 332 | contribution-studio.js:195 | render(), status suffix | ` Grouped filters apply after aggregation.` | 5 |
| 333 | contribution-studio.js:195 | render(), status suffix | ` Economic uniqueness is unresolved.` | 4 |
| 334 | contribution-studio.js:201 | renderMap(), loading status | `Loading Census geography for the selected ZIPs…` | 7 |
| 335 | contribution-studio.js:205 | renderMap(), too many groups for the map | `The map query has more groups than its supported page. Narrow the filters to keep every ZIP in view.` | 19 |
| 336 | contribution-studio.js:211 | map render valueLabel, gross basis | `Selected gross amount` | 3 |
| 337 | contribution-studio.js:211 | map render valueLabel, net basis | `Selected net amount` | 3 |
| 338 | contribution-studio.js:217 | map-coverage line | `${points} located ZIPs · ${unmatched} ZIPs without a location. ` | 8 |
| 339 | contribution-studio.js:218 | result-count, map view | `${group_count} selected ZIP/state groups; ${marks} located ZIP marks. All amounts retained, including unmapped amounts.` | 13 |
| 340 | contribution-studio.js:219 | status, map view suffix | ` · ${congress}th Congress boundaries · money is unchanged by overlays.` | 9 |
| 341 | contribution-studio.js:219 | status, map view grouped-filter suffix | ` Grouped filters select ZIP/state groups before eligible groups combine into ZIP marks.` | 13 |
| 342 | contribution-studio.js:226 | inspect(), record-table loading | `Loading source records…` | 3 |
| 343 | contribution-studio.js:228 | inspect(), missing dimension value | `Missing` | 1 |
| 344 | contribution-studio.js:228 | inspect(), title fallback | `All selected source records` | 4 |
| 345 | contribution-studio.js:229 | inspection-scope suffix | ` · Selected mark` | 3 |
| 346 | contribution-studio.js:229 | inspection-scope suffix | ` · Before grouped filters` | 4 |
| 347 | contribution-studio.js:229 | inspection-scope suffix | ` · Amounts use the same accounting basis as the chart.` | 10 |
| 348 | contribution-studio.js:234 | inspect(), source changed mid-inspection | `Source changed before record inspection. Refresh the chart before inspecting its records.` | 12 |
| 349 | contribution-studio.js:235 | record table column header | `Date` | 1 |
| 350 | contribution-studio.js:235 | record table column header | `Contributor` | 1 |
| 351 | contribution-studio.js:235 | record table column header | `Company` | 1 |
| 352 | contribution-studio.js:235 | record table column header | `Recipient` | 1 |
| 353 | contribution-studio.js:235 | record table column header | `Selected amount` | 2 |
| 354 | contribution-studio.js:235 | record table column header | `Raw observation` | 2 |
| 355 | contribution-studio.js:235 | record table column header | `ZIP` | 1 |
| 356 | contribution-studio.js:235 | record table column header | `State` | 1 |
| 357 | contribution-studio.js:235 | record table column header | `Accounting status` | 2 |
| 358 | contribution-studio.js:235 | record table column header | `Receipt role` | 2 |
| 359 | contribution-studio.js:235 | record table column header | `Reasons` | 1 |
| 360 | contribution-studio.js:235 | record table column header | `Source ID` | 2 |
| 361 | contribution-studio.js:235 | record table column header | `FEC evidence` | 2 |
| 362 | contribution-studio.js:237 | record table, FEC filing link text | `Open filing` | 2 |
| 363 | contribution-studio.js:237 | record table, non-FEC / bad URL cell | `Unavailable` | 1 |
| 364 | contribution-studio.js:238 | record-count line | `${a}–${b} of ${total} included observations` | 6 |
| 365 | contribution-studio.js:245 | restoreView(), source unavailable | `The saved view's source is unavailable.` | 6 |
| 366 | contribution-studio.js:246 | restoreView(), field missing | `A saved field is no longer available. Create a new view.` | 10 |
| 367 | contribution-studio.js:247 | restoreView(), basis unavailable | `The saved accounting basis is unavailable.` | 6 |
| 368 | contribution-studio.js:250 | filter-value placeholder, aggregate stage | `Amount in USD, or a count` | 6 |
| 369 | contribution-studio.js:250 | filter-value placeholder, row stage | `Exact value or text` | 4 |
| 370 | contribution-studio.js:258 | start(), no dataset available | `No verified contribution sources are available in the configured report folder.` | 12 |
| 371 | contribution-studio.js:278 | filter submit, measure + contains | `Choose Equals, At least or At most for a measure.` | 9 |
| 372 | contribution-studio.js:280 | save-view, blank name | `Name the view before saving.` | 5 |
| 373 | contribution-studio.js:280 | save-view, success status | `Saved on this device.` | 4 |
| 374 | contribution-studio.js:281 | saved-view select, source changed since save | `Source changed since this view was saved; using its current verified version.` | 12 |
| 375 | contribution-studio.js:281 | saved-view select, restored | `Saved view restored.` | 3 |
| 376 | contribution-studio.js:283 | export-csv, preparing status | `Preparing all matching groups for CSV…` | 6 |
| 377 | contribution-studio.js:285 | export-csv, source changed mid-export | `Source changed during export. Refresh the view first.` | 8 |
| 378 | contribution-studio.js:285 | export-csv, empty page mid-export | `Export stopped because the next page was empty.` | 8 |
| 379 | contribution-studio.js:286 | export-csv, success status | `Exported ${rows.length} groups with accounting basis, source fingerprint and filters.` | 10 |
| 380 | contribution-studio.js:291 | SVG/PNG export caption, Census geography line | `Census geography; Congress ${view.congress}; ${view.layers}; overlays do not allocate money.` | 10 |
| 381 | contribution-studio.js:292 | SVG/PNG export caption, colour key | `Negative amounts use orange; other amounts use teal.` | 8 |
| 382 | contribution-studio.js:293 | SVG/PNG export caption, mapped/unmapped totals | `Mapped ${mapped}; unmapped ${unmapped}` | 4 |
| 383 | contribution-studio.js:294 | SVG/PNG export caption, ZIP-mark note | `ZIP marks combine eligible selected ZIP/state groups; grouped filters apply before that combination.` | 13 |
| 384 | contribution-studio.js:296 | SVG/PNG export caption prefix | `Source ` | 1 |
| 385 | contribution-studio.js:296 | SVG/PNG export caption prefix | `Analytical index ` | 2 |
| 386 | contribution-studio.js:296 | SVG/PNG export caption prefix | `Query engine SHA256 ` | 3 |

**contribution-studio.js: 126 rows**

---

## mentat/app/cross-reference.js

| # | file:line | where it appears (control/context) | exact current text | words |
|---|---|---|---|---|
| 387 | cross-reference.js:33 | reasons map — company_attribution_unresolved | `Donor not yet matched to a listed company (counted at $0)` | 11 |
| 388 | cross-reference.js:34 | reasons map — attribution_unresolved | `Attribution not settled (counted at $0)` | 6 |
| 389 | cross-reference.js:35 | reasons map — company_attribution_not_accepted | `Company match not accepted` | 4 |
| 390 | cross-reference.js:36 | reasons map — memo_parent_not_established | `Memo entry without a proven parent receipt` | 7 |
| 391 | cross-reference.js:37 | reasons map — original_source_of_transfer_unresolved (reworded) | `Transfer whose original donor is unresolved` | 6 |
| 392 | cross-reference.js:38 | reasons map — earmark_counterpart_not_unique | `Earmark with more than one possible counterpart` | 7 |
| 393 | cross-reference.js:39 | reasons map — earmark_destination_ambiguous | `Earmark destination ambiguous` | 3 |
| 394 | cross-reference.js:40 | reasons map — overlapping_or_cyclic_earmark_links | `Earmark links overlap or loop` | 5 |
| 395 | cross-reference.js:41 | reasons map — observed_filing_versions_unresolved | `Amended filings not reconciled` | 4 |
| 396 | cross-reference.js:42 | reasons map — latest_filing_transaction_replacement_missing | `Latest filing lacks the replacing transaction` | 6 |
| 397 | cross-reference.js:43 | reasons map — latest_filing_manifest_not_corroborated | `Latest filing not corroborated by its manifest` | 7 |
| 398 | cross-reference.js:44 | reasons map — linked_refunds_exceed_original_gift | `Refunds exceed the original gift` | 5 |
| 399 | cross-reference.js:45 | reasons map — receipt_date_missing | `Receipt date missing` | 3 |
| 400 | cross-reference.js:46 | reasons map — excluded_source_metadata_conflict | `Source metadata conflict` | 3 |
| 401 | cross-reference.js:47 | reasons map — superseded_in_observed_filing_family | `Superseded by a later filing` | 5 |
| 402 | cross-reference.js:48 | reasons map — same_original_gift_at_conduit_and_destination | `Same gift seen at conduit and destination` | 7 |
| 403 | cross-reference.js:49 | reasons map — explicit_same_filing_memo_reference | `Memo references its own filing` | 5 |
| 404 | cross-reference.js:50 | reasons map — explicit_observed_refund | `Observed refund` | 2 |
| 405 | cross-reference.js:51 | reasons map — linked_refund | `Linked refund adjustment` | 3 |
| 406 | cross-reference.js:77 | metric(), per-cycle badge on a money tile | `Cycles ${escape(scopeCycles)}` | 2 |
| 407 | cross-reference.js:113 | money-grid, new $0-attribution caption | `Rows with an unresolved company attribution are counted at $0 in every total above; memo, transfer, earmark and role reviews stay inside Observed original giving until resolved.` | 27 |

**cross-reference.js: 21 rows**

---

## mentat/app/graph.js

| # | file:line | where it appears (control/context) | exact current text | words |
|---|---|---|---|---|
| 408 | graph.js:54 | run select, option label (now includes state) | `${r.name} · ${r.state}` | 3 |
| 409 | graph.js:69 | loadCatalog(), no finalized report data | `No finalized report data in this run. Choose another saved run, or check Collection for its status.` | 17 |
| 410 | graph.js:103 | basis-note under Net giving total | `Workbook included receipts, net. Same figure as Chart Studio's Published included receipts basis.` | 13 |
| 411 | graph.js:167 | row-count input, invalid value | `Enter a positive whole number.` | 5 |
| 412 | graph.js:168 | "all rows" button, status | `Showing every matching row.` | 4 |
| 413 | graph.js:254 | copy-image click handler, nothing to copy | `This chart has no image to copy. Export its CSV instead.` | 10 |
| 414 | graph.js:261 | briefing click handler, nothing to add | `This chart has no image to add. Export its CSV instead.` | 10 |
| 415 | graph.js:262 | briefing click handler, tray not served | `The briefing tray is not served by this console yet. Restart the console and try again.` | 16 |
| 416 | graph.js:266 | briefing capture, basis metadata | `Graph totals` | 2 |

**graph.js: 9 rows**

---

## mentat/app/index.html

| # | file:line | where it appears (control/context) | exact current text | words |
|---|---|---|---|---|
| 417 | index.html:112 | Graph export tools, new button | `Copy image` | 2 |
| 418 | index.html:112 | Graph export tools, new button | `Add to briefing` | 3 |
| 419 | index.html:160 | Classic chart export tools, new button | `Copy image` | 2 |
| 420 | index.html:160 | Classic chart export tools, new button | `Add to briefing` | 3 |
| 421 | index.html:168 | Studio header, scope-change button (was "Change scope") | `Data source` | 2 |
| 422 | index.html:168 | Studio header, scope-change button title | `Open the Data source panel and choose a report` | 8 |
| 423 | index.html:187 | Studio toolbar, download-menu summary (was "Download") | `Export` | 1 |
| 424 | index.html:187 | Studio toolbar, download menu item | `Copy image` | 2 |
| 425 | index.html:187 | Studio toolbar, download menu item | `Print chart` | 2 |
| 426 | index.html:187 | Studio toolbar, download menu item | `Add to briefing` | 3 |
| 427 | index.html:187 | Studio toolbar, download menu item | `Save view` | 2 |
| 428 | index.html:187 | Studio toolbar, download menu item | `Open view` | 2 |
| 429 | index.html:187 | Studio toolbar, new standalone button | `Add to briefing` | 3 |
| 430 | index.html:187 | Studio toolbar, standalone button title | `Put this chart in the briefing tray` | 7 |
| 431 | index.html:215 | Data-pane progress row, cancel button | `Cancel` | 1 |
| 432 | index.html:238 | Studio canvas note (was "Choose a report worksheet in the Data pane to begin.") | `Choose a verified report in the Data panel to begin.` | 9 |
| 433 | index.html:239 | Studio print-only footer mark | `MENTAT` | 1 |
| 434 | index.html:278 | Group-limit field title (static HTML control) | `40 per page (verified) · fold after 40 (worksheet); Graph and classic fold at 60` | 13 |
| 435 | index.html:301 | Briefing drawer aria-label | `Briefing` | 1 |
| 436 | index.html:302 | Briefing drawer heading | `Briefing` | 1 |
| 437 | index.html:302 | Briefing drawer close button | `Close` | 1 |
| 438 | index.html:306 | Briefing drawer primary button | `Export PowerPoint` | 2 |
| 439 | index.html:307 | Briefing drawer action button | `Print briefing` | 2 |
| 440 | index.html:307 | Briefing drawer action button | `Share bundle` | 2 |
| 441 | index.html:308 | Briefing drawer button | `Save view` | 2 |
| 442 | index.html:309 | Briefing drawer footer caption | `Every slide carries its scope, basis and source SHA-256.` | 9 |
| 443 | index.html:313 | Share-bundle dialog heading | `Share bundle` | 2 |
| 444 | index.html:313 | Share-bundle dialog close button | `Close` | 1 |
| 445 | index.html:314 | Share-bundle dialog caption | `Choose the reports the phone snapshot should carry.` | 8 |
| 446 | index.html:315 | Share-bundle datasets group aria-label | `Reports` | 1 |
| 447 | index.html:316 | Share-bundle dialog primary button | `Publish phone snapshot` | 3 |
| 448 | index.html:316 | Share-bundle dialog button | `Download HTML bundle` | 3 |
| 449 | index.html:319 | Share-bundle dialog footnote | `Uploading to the private phone link is the coordinator's step.` | 10 |

**index.html: 33 rows**

---

## mentat/app/server.py

| # | file:line | where it appears (control/context) | exact current text | words |
|---|---|---|---|---|
| 450 | server.py:538 | Console.restart(), launcher script missing | `The launcher script is unavailable. Close this window and open MENTAT again.` | 12 |
| 451 | server.py:556 | Console.restart(), Popen failed | `The launcher could not be started. Close this window and open MENTAT again.` | 12 |
| 452 | server.py:928 | Console.get_view(), malformed id | `That is not a saved view identifier.` | 7 |
| 453 | server.py:939 | Console.save_view(), name length | `Name the view: between 1 and 80 characters.` | 8 |
| 454 | server.py:942 | Console.save_view(), missing source | `A saved view carries the source it was built from.` | 10 |
| 455 | server.py:945 | Console.save_view(), sheet count | `Save between 1 and 24 sheets in one view.` | 9 |
| 456 | server.py:947 | Console.save_view(), unnamed sheet | `Every sheet in a saved view needs a name.` | 8 |
| 457 | server.py:950 | Console.save_view(), bad active index | `The active sheet is a sheet number.` | 7 |
| 458 | server.py:964 | Console.delete_view(), malformed id | `That is not a saved view identifier.` | 7 |
| 459 | server.py:984 | Console.briefing_item(), malformed id | `That is not a briefing item identifier.` | 7 |
| 460 | server.py:995 | Console.add_to_briefing(), not an SVG | `A briefing item carries the chart it was made from.` | 10 |
| 461 | server.py:997 | Console.add_to_briefing(), oversized SVG | `Narrow the view before adding it: this chart is over 6 MB.` | 12 |
| 462 | server.py:1019 | Console.add_to_briefing(), tray full | `The briefing holds 40 items. Remove one before adding another.` | 11 |
| 463 | server.py:1031 | Console.remove_from_briefing(), malformed id | `That is not a briefing item identifier.` | 7 |
| 464 | server.py:1047 | Console.order_briefing(), bad payload shape | `Send the briefing order as a list of item identifiers.` | 10 |
| 465 | server.py:1054 | Console.order_briefing(), not a full permutation | `The briefing order must list every item in the tray exactly once.` | 12 |
| 466 | server.py:1067 | Console.publish_pocket(), console has no port | `This console does not know its own port. Restart it and publish again.` | 12 |
| 467 | server.py:1070 | Console.publish_pocket(), no datasets chosen | `Choose at least one dataset to publish.` | 7 |
| 468 | server.py:1073 | Console.publish_pocket(), malformed dataset id | `Choose datasets from the report catalog.` | 6 |
| 469 | server.py:1078 | Console.publish_pocket(), unknown dataset(s) | `Not in this report: ${unknown_list}.` | 5 |
| 470 | server.py:1082 | Console.publish_pocket(), publish already running | `A phone snapshot is already being published. Wait for it to finish.` | 12 |
| 471 | server.py:1090 | publish job, initial message | `Preparing the snapshot.` | 3 |
| 472 | server.py:1128 | run_selfcheck(), subprocess failed to run | `The published page could not be checked: ${error}` | 7 |
| 473 | server.py:1133 | run_selfcheck(), no PASS/FAIL summary line found | `The self-check produced no summary. See ${log_path}` | 8 |
| 474 | server.py:1144 | publish job, extracting-data stage message | `Reading the published report through this console.` | 8 |
| 475 | server.py:1149 | publish job, extractor step failed | `The snapshot reader did not finish. See ${log_path}` | 9 |
| 476 | server.py:1151 | publish job, build-page stage message | `Building the page.` | 3 |
| 477 | server.py:1155 | publish job, build_page step failed | `The page could not be built from the snapshot. See ${log_path}` | 11 |
| 478 | server.py:1157 | publish job, selfcheck stage message | `Checking the published page.` | 4 |
| 479 | server.py:1161 | publish(), OSError starting the pipeline | `The publisher could not be started: ${error}` | 6 |
| 480 | server.py:1167 | publish(), output file never written | `The page was not written. See ${log_path}` | 8 |
| 481 | server.py:1169 | publish job, success message | `Snapshot published to ${job['output_path']}` | 4 |
| 482 | server.py:1191 | Console.publication(), malformed job id | `That is not a phone snapshot publication.` | 7 |
| 483 | server.py:1210 | Console.publication(), owning console gone | `The console that was publishing this snapshot is no longer running.` | 11 |
| 484 | server.py:1778 | GET /api/publish/pocket, job not found | `That publication is not on this console.` | 7 |
| 485 | server.py:1785 | GET /api/studio/briefing/item, not found | `That briefing item is not on this console.` | 7 |
| 486 | server.py:1793 | GET /api/studio/views?id=, not found | `That saved view is not on this console.` | 7 |
| 487 | server.py:1800 | GET static asset, file missing on disk | `Not found.` | 2 |
| 488 | server.py:1822 | POST /api/studio/briefing/*, read-only preview refusal | `The briefing is read-only in this preview console.` | 8 |
| 489 | server.py:1825 | POST /api/studio/views, read-only preview refusal | `Saved views are read-only in this preview console; save from the original console.` | 13 |
| 490 | server.py:1843 | POST /api/studio/views, oversized payload | `That view is too large to save. Remove a sheet and save again.` | 12 |
| 491 | server.py:1855 | POST /api/restart, console busy | `This console is still running collection work. Restart it once that finishes.` | 12 |

**server.py: 42 rows**

---

## Excluded from the table (CSS files, per "skip CSS")

| file:line | note |
|---|---|
| chart-studio.css:88 | `content: '+';` — a CSS-drawn `+` glyph on an expand affordance (visible to the reader, excluded per instruction to skip CSS) |
| contribution-studio.css:8 | `content:'Drop a field here';` — CSS-drawn placeholder text inside an empty dropzone (visible to the reader, excluded per instruction to skip CSS) |
| chart-briefing.css, workspace.css | no `content:` text values; nothing excluded beyond the general CSS skip |

---

## Counts

| File | Rows |
|---|---|
| app.js | 14 |
| chart-briefing.css | 0 (excluded — CSS) |
| chart-briefing.js | 61 |
| chart-export.js | 3 |
| chart-studio-contributions.js | 9 |
| chart-studio-core.js | 6 |
| chart-studio.css | 0 (excluded — CSS) |
| chart-studio.js | 58 |
| charts.js | 4 |
| contribution-studio.css | 0 (excluded — CSS) |
| contribution-studio.html | 105 |
| contribution-studio.js | 126 |
| cross-reference.js | 21 |
| graph.js | 9 |
| index.html | 33 |
| server.py | 42 |
| workspace.css | 0 (excluded — CSS) |
| **Total** | **491** |
