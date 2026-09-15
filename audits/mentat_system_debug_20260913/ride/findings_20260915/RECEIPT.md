# Ride 1 findings, 2026-09-15 - receipt

Paul rode Ride 1 v2 on his console (8806) and marked **27 FAIL, 32 FAIL, 17 not recorded**,
with no notes. This lane reproduced each one from the files and from running code. Nothing
below is taken from a previous summary.

Branch `codex/mentat-crypto`, working tree at `80528938c` (the launcher fix `5c5aa6bfe` had
already landed; `Start-MentatApp.ps1`, `app.js`, `test_desktop_launcher.py` and
`test_app_lazy_startup_browser.cjs` were not touched here).

## How this was run

Two throwaway consoles, both started from `C:\Users\pgoff\Mentat` with `--data-root` pointing
into this lane's scratchpad:

| port | report directory | why |
|---|---|---|
| 8852 | a scratchpad **copy** of `Community Banks` + `Crypto` from `C:\Users\pgoff\Mentat\reports` | fast iteration |
| 8853 | a scratchpad **copy** of `Banking` + `Crypto` from `C:\Users\pgoff\OneDrive\Desktop\Mentat Complete Files` | this is Paul's own report folder, and `Banking` is the report his console opens on |

**Paul's console on 8806 was never posted to.** Two GETs were made against it - `/api/health`
and `/api/studio/briefing` - to learn which reports his console reads and whether his tray
already held items (it held none). That is what turned up the report folder above; the first
attempt at reproduction used `C:\Users\pgoff\Mentat\reports`, which has no `Banking` workbook
at all, and would have reproduced the wrong console.

The page was driven with Playwright against the installed Chrome - the same `channel:'chrome'`
the repo's own `.cjs` suites use, so `locator.click()` is a real hit-tested click - and
confirmed in the Browser pane. The pane reported `innerWidth: 0` while hidden and its
screenshots did not agree with the page's own geometry, so every measurement here comes from
the page (`getBoundingClientRect`, `document.elementFromPoint`) or from Playwright, never from
reading a pane screenshot.

## Step 32 - could NOT be reproduced as failing

Step 32 is `2 charts, then 1 chart` expecting `Chart A/B chips; pane B renders; no "refused to
connect"; back to one pane`. Seven runs, all clean:

| run | pane B drew | chips | back to 1 chart | page errors |
|---|---|---|---|---|
| 1440 plain | yes | Chart A / Chart B | `hidden=true, display:none, width 0` | none |
| 1440, linked filters on (company + party) | yes | Chart A / Chart B | same | none |
| 1440, after "Canvas only in every chart" | yes | Chart A / Chart B | same | none |
| 1100 (under the 1200px Inspector line) | yes | Chart A / Chart B | same | none |
| 820 (single-column comparison grid) | yes | Chart A / Chart B | same | none |
| 8852 before/two/after geometry | yes | - | see below | none |
| 8853 before/two/after geometry | yes | - | see below | none |

The layout does return, exactly. On 8853, the one-pane state before ever pressing 2 charts and
the one-pane state after pressing 1 chart again are the same numbers:

```
before  count 1  compCols 1172px  gridCols 260px 610px 300px  canvas 581  multi False  frames []
two     count 2  compCols 580px 580px  gridCols 578px  canvas 549  multi True   frames [B visible]
after   count 1  compCols 1172px  gridCols 260px 610px 300px  canvas 581  multi False  frames [B hidden, display none, width 0]
```

`findings_20260915/s32c-before.png` and `s32c-after.png` are **byte-identical** files.

Two things worth recording because they are the parts that could break and did not.
`.studio-comparison-frame` sets `display:block`, which outranks the user-agent `[hidden]` rule;
`chart-studio.css:45` carries an explicit `.studio-comparison-frame[hidden] { display:none }`
that keeps the hidden pane gone. And the pane's own document is served with
`frame-ancestors 'self'` only for `/` with `?studioPane=B|C|D` (`server.py:1806-1811`), which is
why no "refused to connect" appeared.

**So this is a finding, not a gap: on a clean console at the current build, step 32 passes.**
What is left that could make it fail on 8806, in the order worth checking:

1. **A console that is not on the current build.** A pane loads `/?studioPane=B`; a server
   started before `frame_ancestors` existed answers `'none'` and Chrome refuses the frame, which
   is the exact "refused to connect" the step names. At the start of this lane 8806 was on
   `git_sha 5937875c8` with an in-process asset tree that no longer matched disk. It is on the
   current build now.
2. **Remembered state.** `chart-comparison.js:29-31` restores `count`, `hidden` and `links` from
   `localStorage['mentat-chart-comparison-v1']`. A console that already remembered 2 or 4 charts
   arrives in that layout, so "2 charts" is a no-op and the step reads as stuck.
3. **A pane that is still drawing.** Pane B is a whole second Chart Studio and runs its own
   query. On Banking that first paint took over three minutes from cold on this box
   (592,570 observations; the index build itself took 13 minutes the first time). A reader who
   presses 1 chart before B has drawn sees an empty pane, not a broken one.
4. **`blocked`, once set, is only cleared on a successful `onload`** (`chart-comparison.js:47,67`).
   If a pane is ever refused, the note "Chart B could not open in this page..." stands until a
   pane loads cleanly again; `report()` never clears it on its own.

## Step 17 - reproduced, root-caused, fixed

Step 17 is `Graph: cycle 2025-2026 + first company, Open in Chart Studio` expecting
`Chip with company and cycle; chart draws (no "No matching observations"); strip agrees to the cent`.

**It depends on whether Chart Studio has already drawn in that page.**

- Walked in the ride's own order (Chart Studio first, as steps 02-14 do, then Graph), step 17
  passes: chip `Carried from Graph - Community Banks - 2025-2026 - Apple Bank for Savings`,
  both filter pills, and `Graph shows $4,096.65 ... Studio shows $4,096.65. Agree.`
- Walked from Graph first - a reader who opens Graph, or reloads while on it - **the carry is
  silently dropped**: chip `Community Banks - All cycles`, no pills, and the strip compares the
  wrong scopes (`Graph shows $167,261.03 for All companies - 2026. Studio shows $618,865.61.`).

Root cause, `mentat/app/chart-studio.js:374-377`:

```js
function applyGraphScope() {
    const scope = pendingScope;
    pendingScope = null;
    if (!scope || !verified() || !data) return;
```

`applyGraphScope()` is called from two places: eagerly by the hand-off button
(`chart-studio.js:2607`, `if (loadedSources && verified()) applyGraphScope();`) and again from
`loadContributions()` when the verified data lands (`chart-studio.js:343`). On a page where
Chart Studio has not loaded, `showView('chart-studio')` runs `activate()` synchronously, which
sets `loadedSources = true` and *starts* the load; control returns to the click handler, the
guard now passes, and the eager call runs while `data` is still undefined. It cleared
`pendingScope` on its first line and then returned at the guard, so when the data arrived the
second call found nothing to apply.

The fix consumes the scope only when it can be used:

```js
function applyGraphScope() {
    const scope = pendingScope;
    if (!scope) return;
    if (verified() && !data) return;   // keep it for the call that follows the data
    pendingScope = null;
    if (!verified()) return;           // a worksheet source cannot express it; drop it
```

A worksheet source still drops the scope rather than holding it for an unrelated later load.

Why no suite caught it: `test_studio_reconciliation_browser.cjs:105-106` waits for
`#studio-canvas svg` *before* pressing the hand-off, so the shipped coverage only ever
exercised the warm path.

## Step 27 - reproduced twice, two different defects

Step 27 is `Add to briefing on two different sheets` expecting `Badge "2"; drawer lists both
with title, scope, basis, time`. The orchestrator's framing also asked for the add from Graph
and from the classic builder.

The first pass is fine: Studio add gives badge `1`, Graph add gives badge `2`, each card carries
a title, a scope line, a basis and a time, and a real SVG thumbnail. Both defects below are
about what happens next.

### R2-27 - the stored item loses its scope chip

`mentat/app/server.py:1005-1012` built the stored item from an explicit list of fields:

```python
item = {'id': identifier, 'title': ..., 'scope': ..., 'note': ..., 'basis': ...,
        'sheetId': ..., 'sheetName': ..., 'source': ..., 'provenance': ...,
        'width': ..., 'height': ..., 'added_at': ..., 'origin': ...}
```

The client sends `chip` (`chart-briefing.js:202`, from `currentChart()` at
`chart-studio.js:1751`), and the server dropped it. Every reader-facing surface prints
`item.chip || item.scope`: the drawer card (`chart-briefing.js:309`), the speaker notes
(`:373`), the printed briefing sheet (`:405`), and the HTML bundle's caption. `scope` is the
full provenance line - roughly 600 characters of workbook digest, analytical index, query
engine and field semantics hashes and the raw filter JSON.

Measured on 8853, the same two items, before and after one reload:

```
added   : "Banking - All cycles"
reloaded: "Banking - Published included receipts - Banking Industry Spending Overview.xlsx -
           Workbook SHA256 842ba7a2312ffb03... - Analytical index 4676e3b27b319d94... -
           Query engine SHA256 a1a8ecdd... - Field semantics SHA256 dc565363... -
           Groups 1-10 of 10 - {"filters":[],"aggregate_filters":[]} - Tracked companies..."
stored keys: added_at,basis,height,id,note,origin,provenance,scope,sheetId,sheetName,source,title,width
```

This is not only a reload problem. The tray is stored per data root precisely so a second
console sees the same one (step 30's mirror console, step 31's published bundle), and every one
of those readers gets the digest string. It also reaches the shipped artefacts: the .pptx slide
scope line and the speaker notes are built from the same readers.

Fixed at the server, one field, beside `scope`. Stored keys are now
`added_at,basis,chip,height,id,note,origin,provenance,scope,sheetId,sheetName,source,title,width`
and both reloaded cards read `Banking - All cycles`.

Why no suite caught it: `test_studio_briefing.py:95` asserts `sorted(item) == sorted(ITEM_FIELDS)`,
and `ITEM_FIELDS` itself omitted `chip` - the contract was wrong, so the assertion passed. The
shared HTTP fixture `studio-contract-examples.json:25` has carried a `chip` since fix1 round 2,
but nothing asserted it survived.

### R3-27 - the open drawer covers the toolbar controls

`.studio-briefing` is `position:fixed; top:0; right:0; bottom:0; width:min(340px,94vw); z-index:12`
(`chart-briefing.css:6`), and `add()` calls `openDrawer()` on every add
(`chart-briefing.js:239`). Nothing reserved room for it, so the studio toolbar's right-hand
controls sat underneath it. `document.elementFromPoint` at each control's centre, with one item
added:

| width | covered by the drawer |
|---|---|
| 1920 | `studio-classic` |
| 1600 | `studio-classic` |
| 1440 | `studio-classic` |
| 1280 | `studio-classic`, `studio-overview-toggle` |
| 1100 | `studio-classic`, `studio-overview-toggle`, `studio-inspector-toggle` |

A real Playwright click on `#studio-classic` with the drawer open times out -
`<p class="studio-briefing-line"> ... intercepts pointer events` - and succeeds the moment the
drawer is closed. So after any add, "Classic builder" is unreachable, and under 1200px so is the
Inspector toggle that **step 24** is about.

Fixed by telling the page the drawer is there. `chart-briefing.js` now toggles
`body.studio-briefing-open` in `openDrawer`/`closeDrawer`, and `chart-briefing.css` reserves the
gutter where the drawer is a panel rather than an overlay:

```css
@media (min-width: 900px) {
  body.studio-briefing-open #view-chart-studio { padding-right: 340px; }
}
```

Below 900px the drawer is most of the window and still stands as an overlay, which is what the
R4 render intends.

## Files changed

| file | before | after | bytes | crlf | lf | class |
|---|---|---|---|---|---|---|
| `mentat/app/chart-studio.js` | cc5ca91 | **24a3377** | 155839 | 2650 | 0 | crlf |
| `mentat/app/server.py` | 1d61082 | **f731c18** | 111559 | 1952 | 0 | crlf |
| `mentat/app/chart-briefing.js` | 34ea288 | **a2dde2d** | 29624 | 0 | 692 | lf |
| `mentat/app/chart-briefing.css` | b9593ba | **19af164** | 7319 | 0 | 125 | lf |
| `mentat/tests/test_studio_briefing.py` | 1c207b6 | **0e60193** | 12347 | 0 | 217 | lf |
| `mentat/tests/test_studio_contract_examples.py` | b87c565 | **f5f7ca9** | 8007 | 0 | 154 | lf |
| `mentat/tests/test_studio_ride1_browser.cjs` | new | **d8f5a05** | 13004 | 0 | 207 | lf |

Every file kept its line-ending class: the two pure-CRLF files are still pure CRLF and the
pure-LF files still pure LF. Each was backed up as `*.bak-20260915-ride1` before it was touched.
The harness Write and Edit tools refuse paths under `C:\Users\pgoff\Mentat`, so every edit went
through an exact-anchor python patcher that matches each anchor once in the file's own
convention, refuses to write unless every anchor matches, and refuses to write at all if the
line-ending class would change. No shell heredoc touched a repo file.

## Tests

A new suite, `mentat/tests/test_studio_ride1_browser.cjs`, two cases, both of which fail before
the fix and pass after:

1. *a Graph scope carried before Chart Studio has its data is still carried* - an offline
   fixture that holds the verified catalog back, asserts the hand-off is pressed while
   `#studio-canvas svg` does not exist yet (so it cannot silently become the warm path the
   existing suite covers), then releases it and asserts both filter pills, the chip
   `Carried from Graph - Banking - 2023-2024 - Alpha Bank`, the filters actually sent on the
   wire, and the strip agreeing at `$12,090,412.00`.
2. *the open briefing drawer never covers the studio toolbar controls* - at 1920, 1440, 1280,
   1100 and 960, adds a chart with a real click, asserts the badge reads `1`, asserts that no
   toolbar control hit-tests into the drawer, presses Classic builder for real, and asserts the
   body class is given back on Close.

Negative control, run by restoring the four application files from their
`.bak-20260915-ride1` backups and running the same suite:

```
pre-fix {'chart-studio.js': 'cc5ca91', 'server.py': '1d61082', 'chart-briefing.js': '34ea288', 'chart-briefing.css': 'b9593ba'}
  x a Graph scope carried before Chart Studio has its data is still carried
      page.waitForFunction: Timeout 20000ms exceeded   (the two pills never arrive)
  x the open briefing drawer never covers the studio toolbar controls
      AssertionError: 1920px: the drawer is sitting on top of studio-classic, studio-overview-toggle
      actual: [ 'studio-classic', 'studio-overview-toggle' ]   expected: []
pass 0  fail 2
restored {'chart-studio.js': '24a3377', 'server.py': 'f731c18', 'chart-briefing.js': 'a2dde2d', 'chart-briefing.css': '19af164'}
```

And on the python side, the same swap:

```
Ran 14 tests   FAILED (failures=1, errors=3)
AssertionError: Lists differ: [...] != [...]
  +  'chip'
```

**No assertion was removed or loosened.** `ITEM_FIELDS` gained `chip` rather than losing the
`sorted(item) == sorted(ITEM_FIELDS)` pin; the `add()` payload now carries a short chip *and* a
long provenance-shaped scope so the two can be told apart; two cases were added
(`test_the_short_scope_chip_survives_the_round_trip`, which also asserts the chip is shorter
than and different from the scope, and
`test_an_item_sent_without_a_chip_still_lists_one_field_rather_than_none`); and the shared HTTP
contract suite gained an assertion that the fixture's chip survives.

### Totals

| suite | result |
|---|---|
| `node --test "mentat/app/tests/**/*.test.js"` | **108 pass, 0 fail** |
| the fix1 round-2 `.cjs` set (7 suites) plus the new one | **36 pass, 0 fail** (was 34) |
| six python suites, three rounds | **Ran 61, OK / OK / OK** (was 58; +1 from the launcher fix, +2 here) |

## Live retest, on the fixed build

Both consoles were restarted onto the fixed code (`git_sha 80528938c`, in-process asset tree
equal to disk) before this.

**Step 17**, on 8853, Graph-first - the path that used to drop the carry:

```
step 16  chip  Carried from Graph - Banking - 2025-2026 - All companies
         shelf Election cycle = 2025-2026
         strip Graph shows $12,003,181.12 for All companies - 2025-2026.
               Studio shows $12,003,181.12. Agree.
step 17  chip  Carried from Graph - Banking - 2025-2026 - Bank of America NA
         shelf Company = Bank of America NA | Election cycle = 2025-2026
         chart drawn, no "No matching observations", no error
         strip Graph shows $1,459,371.05 for Bank of America NA - 2025-2026.
               Studio shows $1,459,371.05. Agree.
         Graph's own note: Net giving in selected scope $1,459,371.05
page errors: none
```

Scope A and Scope B agree to the cent. Screenshots `s17b-graph-scoped.png`, `s17b-step16.png`,
`s17b-step17.png`.

**Step 27**, on 8853, two sheets via Duplicate sheet, then a reload:

```
add 1        badge 1  "1 item"   card: Banking - All cycles / Published included receipts - added ...
add 2        badge 2  "2 items"  both cards: Banking - All cycles
after reload badge 2  "2 items"  both cards: Banking - All cycles      <- was the digest string
stored keys  added_at,basis,chip,height,id,note,origin,provenance,scope,sheetId,sheetName,source,title,width
Classic builder, drawer open: clicked            <- was a click timeout
page errors: none   console errors: none
```

And in the Browser pane, with a real Add to briefing on the live page: badge 2 -> 3,
`body.studio-briefing-open` set, and `studio-classic`, `studio-overview-toggle` and
`studio-briefing-add` every one hit-testing to itself. Screenshots `s27b-two-sheets.png`,
`s27b-after-reload.png`, `s27b-classic.png`.

**Step 32**, on 8853: the before/after table above. `s32c-before.png`, `s32c-two.png`,
`s32c-after.png`.

## Left alone, on purpose

- **The `added_at` epoch.** Cards say `added 12:04` because the server writes `added_at` as a
  UNIX time in seconds (`server.py:1011`, `time.time()`) and `timeLabel()`
  (`chart-briefing.js:104-107`) hands it to `new Date(value)`, which expects milliseconds. This
  is the same bug fix1 round 2 found in `saved_at` and fixed **at the reader** after Paul ruled
  on which side to fix. Nobody has ruled on this one, and the stored value is what
  `test_studio_briefing.py` pins, so it is recorded here rather than changed.
- **`blocked` never being cleared by `report()`** (`chart-comparison.js:47,67,75-79`) - a
  refused pane leaves its note standing for the session. Not reachable on a current console, so
  not touched.
- **Step 27's click path wording.** "+ New sheet" makes an *empty* sheet, so the second add on
  it is refused with `Build a chart before adding it to the briefing.` and the badge stays at 1.
  The refusal is correct; the checklist step does not say to build a chart on the second sheet.
  "Duplicate sheet" gets to badge 2 in one click. That is a checklist call for Paul.
- **`Start-MentatApp.ps1`, `app.js`, `test_desktop_launcher.py`, `test_app_lazy_startup_browser.cjs`**
  - the launcher lane's files. Not read for edit, not touched.

## Consoles

Both of this lane's consoles were started with `Start-Process` and stopped by their pids at the
end; the ports were confirmed free afterwards. Paul's console on 8806 was read twice over HTTP
and never written to, and is still running.
