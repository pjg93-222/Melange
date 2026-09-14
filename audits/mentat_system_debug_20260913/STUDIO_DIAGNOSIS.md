# Mentat Chart Studio — diagnosis of Paul's four symptoms

Read-only lane. Nothing in `C:\Users\pgoff\Mentat` was edited. All proposed fixes are
unified diffs in this directory; each was syntax-checked and dry-run verified with
`git apply --check` against the **current working tree** (all four apply cleanly).

Tree: `C:\Users\pgoff\Mentat` (worktree, branch `codex/mentat-crypto`, dirty).
Tests: `node --test mentat/app/tests/chart-studio-core.test.js` -> **61 pass, 0 fail**.

---

## 0. Which console Paul is actually running (settles a lot)

`Get-CimInstance Win32_Process -Filter "name like 'python%'"` + process creation times
+ a live read-only HTTP probe of every instance:

| Port | PID | Started | serves `/chart-comparison.js` | `frame-ancestors` |
|---|---|---|---|---|
| 8802 | 43404 | 2026-09-12 20:49 | **404** | `'none'` |
| 8803 | 22228 | 2026-09-12 21:15 | **404** | `'none'` |
| 8804 | 67100 | 2026-09-12 22:37 | **404** | `'none'` |
| 8805 | 75920 | 2026-09-13 13:53 | 200 (6125 B) | `'none'` |
| 8808 | 51268 | 2026-09-11 21:57 | **404** | `'none'` |
| 8812 | 77352 | 2026-09-13 14:30 (agent, read-only) | 200 | `'none'` |
| 8813 | 9920 | 2026-09-12 22:32 (agent, read-only) | **404** | `'none'` |

All of them are the **same tree** (`C:\Users\pgoff\Mentat\mentat\app\server.py`,
`--data-root C:\Users\pgoff\AppData\Local\Mentat\console`). None is `--read-only`
except 8813 / 56312 / 8812.

Why the split: static files are re-read per request (`server.py:1273`, cache key
includes mtime), so **every** port serves the current `index.html`, which does
contain `<script src="/chart-comparison.js">` (`index.html:7`). But the **allow-list
is Python code** (`server.py:1239-1268`), frozen at process start:

```python
                      '/chart-studio.js': ('chart-studio.js', 'text/javascript'),
                      '/chart-comparison.js': ('chart-comparison.js', 'text/javascript'),   # server.py:1266
```

`server.py` was last written **2026-09-13 01:31**. Every console started before that
(8802/8803/8804/8808) 404s the script. So on Paul's long-running consoles the
comparison feature is not "gone" — it never loaded.

`git log --all -S "chart-comparison" --oneline` -> empty; `git ls-files
mentat/app/chart-comparison.js` -> empty. The whole split view (file, script tag,
allow-list entry, CSS block) is **uncommitted, never committed**.

---

## S2 — "What happened to the multiple chart split view? … it displayed an error view, saying it refused to connect"

### (a) Root cause — TWO independent causes, both CONFIRMED

**S2-1 (why it is missing): stale server process, not missing code.** Evidence in
section 0: `GET /chart-comparison.js` -> 404 on 8802/8803/8804/8808. The `<script>`
tag is served, the file is not, so the IIFE never runs and no toolbar is built.
CONFIRMED by live HTTP probe of every running instance.

**S2-2 (why it said "refused to connect" when it did load): the server forbids
framing itself.** `mentat/app/server.py:1096-1121`:

```python
    def send(self, value, status=200, content_type="application/json", *, cache_control="no-store", etag=None):
        ...
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' blob:; frame-ancestors 'none'")
```

`frame-ancestors 'none'` blocks framing **even same-origin**. The iframe `src` is
correct and relative — `mentat/app/chart-comparison.js:49-53`:

```js
      if(i<state.count&&!frame){frame=document.createElement('iframe');frame.title='Chart '+id;frame.className='studio-comparison-frame';frame.dataset.pane=id;
        const url=new URL(location.href);url.searchParams.set('studioPane',id);url.hash='chart-studio';frame.src=url.href;
```

No hard-coded host or port; `new URL(location.href)` inherits the current origin.
The path **is** in the allow-list. So a 404 was never the problem — the header was.
Live console (coordinator, port 8812): `GET /?studioPane=B` -> `200 OK` then
`net::ERR_BLOCKED_BY_RESPONSE`, console: `Framing 'http://localhost:8812/' violates
… "frame-ancestors 'none'"`. Chrome paints that as **"localhost refused to
connect."** — exactly Paul's words. CONFIRMED.

`grep -rn "frame-ancestors|X-Frame-Options"` over the repo: the only live site is
`server.py:1119`. There is no middleware, no `X-Frame-Options` header, and neither
`mentat/app/desktop/Launcher.cs` nor `mentat/app/Start-MentatApp.ps1` sets one.
(Other hits are frozen copies under `.tmp/` and `outputs/`, plus the assertion in
`mentat/tests/test_contribution_http.py:74`.)

**S2-3 (secondary, CONFIRMED): a blocked pane throws and aborts the render.**
`chart-comparison.js:55` and `:51`:

```js
      if(frame){frame.hidden=i>=state.count;frame.contentWindow.MentatStudioPane?.options(state.hidden);}
```

`?.` does not help: reading *any* named property of a cross-origin window throws
before the optional-chaining test. Live console shows
`Uncaught SecurityError: Failed to read a named property 'MentatStudioPane' … code 18`
at `chart-comparison.js:27:72`. The throw aborts `render()` before its final
`sync(window)`, and repeats on every subsequent toolbar click.

### (b) Repro
1. Open a console started **after** 2026-09-13 01:31 (8805). Chart Studio tab.
2. The comparison toolbar ("1 chart … 4 charts / Hide all options / Linked filters")
   is above the studio. On 8802/8803/8804/8808 it is absent — that is S2-1.
3. Click **2 charts** -> second pane renders Chrome's "…refused to connect."
   DevTools console shows the CSP `frame-ancestors` violation + the SecurityError.

### (c) Fix
* `S2-csp-server.patch` — adds a `frame_ancestors` keyword to `Handler.send` and
  passes `'self'` **only** for the pane document (`/` with `studioPane=B|C|D`).
  Every other response, including all `/api/*`, keeps `'none'`.
  *This is deliberately scoped so that `mentat/tests/test_contribution_http.py:74`
  (which asserts `'none'` on `/api/contributions/session`) still passes unchanged —
  verified by reading the test, not inferred.*
* `S2-S3-chart-comparison.patch` — routes every pane access through
  `paneOf(frame)`, which try/catches the SecurityError, records the pane in a
  `blocked` set, drops it from `windows()`, and shows an in-app status line
  ("Chart B could not open in this page… restart the console…") instead of
  throwing. So even on an un-restarted server the UI degrades to a sentence.
* Paul must **restart his console processes** after the server patch; a running
  process keeps its old `send()`.

### (d) Blast radius / risk
`send()` is the single response path for the whole console (API + static), so the
signature change touches every response — but the default keeps today's exact header
string, so only the pane document's header changes. Risk of the relaxation:
`frame-ancestors 'self'` lets *this origin* frame that one document. Since the
server binds loopback and `valid_host()` (`server.py:1122`) already rejects any Host
other than `127.0.0.1:<port>` / `localhost:<port>`, no third-party page can be that
ancestor. Clickjacking exposure is unchanged for every other URL. The JS guard is
purely additive.

**Alternative if Paul would rather not relax the header at all:** drop the iframe
architecture and render panes as in-page DOM instances. That is a rewrite of
`chart-comparison.js` (pane isolation currently comes free from the iframe's separate
`window`, `localStorage` suffix and request lifecycle) — I do not recommend it now.

### The ~100 `POST /api/contributions/query` burst
Not caused by the comparison click. Navigating to `http://localhost:8812/` with **no
interaction at all** produced ~160 `POST /api/contributions/query` in one burst
(network log indices 102-263), and the tab's main thread then stopped responding
(`find`, `javascript_tool` both timed out). So this is a **page-load storm**, and it
is a strong candidate for "everything in the studio feels dead".

What I can say with evidence:
* `members()` (`chart-studio.js:523-538`) fires one `/query` per distinct facet key
  and memoises *before* awaiting (`memberCache.set(key,{values:[]})` at `:530`), so a
  single render cannot fan out per field — **but** the `.catch` at `:533` does
  `memberCache.delete(key)`, so every failing facet is re-fired on the next render.
* `contributionReady()` (`chart-studio.js:230-232`) polls at
  `Math.min(4000, retry_after_ms||1000)`; the server's `retry_after_ms` is `1500`
  (`contribution_data.py:601`), so the poller cannot produce 160 requests in seconds.
* `queryCached()` (`chart-studio.js:269-277`) dedupes by exact query JSON with a 30 s
  window, so the storm is **many distinct queries**, not one repeated.
Status: **PLAUSIBLE, not confirmed** — I could not read the request bodies because
the page was wedged. Next step is to capture 10 request payloads and see which
`dimensions` they ask for. I have not patched this; it is a separate lane.

---

## S3 — "There is no way to go back from the hide view to the chart creation"

### (a) Root cause

The control is **"Hide options"** (per pane) / **"Hide all options"** (whole grid),
created in `chart-comparison.js:12` and `:27`:

```js
  const toggle=button('Hide options',()=>setOptions(!hidden));toggle.setAttribute('aria-expanded','true');quick.append(toggle);
  document.getElementById('studio-canvas-wrap').before(quick);
  function setOptions(value){hidden=!!value;studio.classList.toggle('studio-options-hidden',hidden);toggle.textContent=hidden?'Show options':'Hide options';…}
  …
  const allOptions=button('',()=>{state.hidden=!state.hidden;persist();render();});toolbar.append(allOptions);
```

What that one class removes — `mentat/app/chart-studio.css:49` (this entire CSS block
is **uncommitted**; `git show HEAD:mentat/app/chart-studio.css | grep -c
studio-options-hidden` -> 0):

```css
.studio-options-hidden .studio-side,.studio-options-hidden .studio-cards,.studio-options-hidden .studio-showme,.studio-options-hidden .studio-shelf,.studio-options-hidden .studio-toolbar,.studio-options-hidden .studio-quick-tools label {display:none!important}
```

That is the **whole chart-creation UI in one line**: the Data/Analytics side pane,
the Pages/Filters/Marks cards, the Columns/Rows shelves, Show Me, and the toolbar
(Undo/Redo/Swap/Sort/Clear/Duplicate/Download/**Show Me**/Classic builder). What is
left on screen is the canvas plus a small unlabelled bar.

Findings, separated by confidence:

* **CONFIRMED — the state is sticky across reloads.** `state.hidden` is persisted to
  `localStorage['mentat-chart-comparison-v1']` (`chart-comparison.js:21-23`) and
  re-applied at load (`:46`). Once hidden, it stays hidden in every new tab.
* **CONFIRMED — hiding also removes the only restore for a *second* hide.**
  `#studio-showme-close` (`index.html:268`) is a button literally labelled **"Hide"**;
  its only restore is `#studio-showme-toggle` in `.studio-toolbar`
  (`chart-studio.js:1331-1332`), which `studio-options-hidden` deletes. Hide Show Me,
  then hide options, and Show Me is unreachable until options come back.
* **CONFIRMED — a pane opened top-level has no navigation at all.**
  `chart-comparison.js:16-19`:

```js
  if(embedded){
    document.body.classList.add('studio-embedded');
    if(typeof showView==='function')showView('chart-studio');
    return;
  }
```

  with `chart-studio.css:50` `.studio-embedded .app-navigation … {display:none!important}`.
  `embedded` is true for **any** `?studioPane=B|C|D` URL, framed or not. Opening the
  blocked frame in its own tab (the natural reaction to "refused to connect", via
  right-click -> *Open frame in new tab*) gives a page with no tab bar, no heading,
  no route back to any view — you must hand-edit the URL. This is a literal
  "no way to go back".
* **PLAUSIBLE, not confirmed — which of these Paul hit.** I traced `render()` line by
  line: `setOptions(state.hidden)` at `:46` runs *before* the SecurityError at `:55`,
  so the "Show all options" button does still restore on a click. The failure is
  therefore **discoverability plus the top-level-pane trap**, not a dead code path.
  I did not confirm this in a live browser because the page was wedged by the query
  storm; one question to Paul ("was the bar still there, or had the whole tab bar
  gone?") separates the two.

### (b) Repro
1. Console started after 01:31 (8805). Chart Studio -> **Hide all options**. Every
   builder surface disappears; only the canvas and a small bar remain. Reload — it is
   still hidden.
2. Or: click **2 charts**, right-click the "refused to connect" pane -> *Open frame in
   new tab*. The new tab has no navigation whatsoever.

### (c) Fix
* `S2-S3-chart-comparison.patch` also:
  - makes `embedded` require `window.top!==window.self`, so a pane URL opened
    top-level keeps the whole console (closes the confirmed trap);
  - relabels the toggle **"Hide chart options" / "Show chart options"** and gives it
    `id="studio-options-toggle"`, `class="studio-options-restore"`.
* `S3-chart-studio-css.patch` pins `.studio-quick-tools` sticky at the top of the
  view column, force-shows it and the restore button under `.studio-options-hidden`,
  and gives the restore button a visible weight/border. (It was already technically
  visible; this makes it the obvious way back and makes it impossible for a future
  rule to hide it.)

### (d) Blast radius / risk
`.studio-quick-tools` exists only when `chart-comparison.js` runs, so the CSS is
inert everywhere else. `position:sticky` inside `.studio-view` could overlap the
chart title on very short viewports — cosmetic. The `window.top` guard changes
behaviour **only** for a top-level `?studioPane=` URL; inside a real iframe
`window.top!==window.self` is true and nothing changes. Low risk.

---

## S4 — "The Analytics mode does nothing"

### (a) Root cause — CONFIRMED, and it is not the tab

The plumbing is all present: the Analytics tab toggles the pane
(`chart-studio.js:1379-1385`), `renderAnalytics()` is called from `renderAll()`
(`chart-studio.js:1201`), `#studio-analytics-list` exists (`index.html:224`), and
`applyAnalytics()` -> `commit()` -> `renderAll()` (`chart-studio.js:809-816`).
`chart-studio-core.js` genuinely consumes the state (`:215-227` transform,
`:511-521` `referenceValues`, `:534-545` grand total).

The problem is that **the default mode silently drops most of it.** The default data
source is *Verified contributions* (`index.html:189`, first option = `contributions`;
`verified()` = `chart-studio.js:50`), and on that path `renderContributionView()`
takes over (`chart-studio.js:977`). There:

```js
      if(sheet().analytics.totals)notes.push('Selected source total: '+money(result.totals.amount)+'…');
      if(sheet().analytics.average||sheet().analytics.median)notes.push('Reference statistics apply to the displayed marks; source-level averages and medians are available as measures.');
```
(`chart-studio.js:314-315`)

* **Totals**: in verified mode it draws nothing at all — it appends a sentence to the
  note line under the title. No reference line, no annotation. A user who presses it
  and watches the chart sees nothing move. (In worksheet mode it *does* overlay —
  `chart-studio.js:1048-1053`.)
* **Average / Median**: `compile()` forwards them as
  `references:{average,median}` (`chart-studio-contributions.js:110`), and **only
  `contribution-plot.js:96-104` reads that key**:
  ```js
  if(spec.references&&(spec.references.average||spec.references.median)&&spec.type!=='scatter'){
  ```
  `grep -n references contribution-charts.js` -> **no hits**. So for all 13 types in
  `MentatContributionCharts.TYPES` (`contribution-charts.js:6`: heatmap, highlight,
  stacked, dot, series-dot, treemap, bubbles, histogram, box, gantt, bullet,
  combination, dual-line) and for the `pie/doughnut/waterfall/pareto/radar` branch
  and the temporal-transform branch (all three go to `paint.chartSVG`,
  `chart-studio.js:307-312`), the flags are accepted, the button turns on, and
  **nothing is drawn** — while line 315 still tells the reader that reference
  statistics "apply to the displayed marks". They do draw on bar/line/area/circle.
* **The four transforms** (Period totals / YoY / Period change / Same-phase forecast)
  throw unless a time field is on a shelf — `chart-studio-contributions.js:73-81`:
  ```js
    const transform=state.analytics?.transform||'none';
    if(transform!=='none'){
      const time=dimensions.findIndex(d=>['date','year','cycle'].includes(d));
      if(time<0)throw new Error('Period analysis needs Contribution date, Year or Election cycle on a shelf.');
      …
      if(measures.length!==1||measures[0]!=='amount')throw new Error('Period analysis requires one summed Selected amount measure.');
      if(transform!=='annual'&&dimensions.length!==1)throw new Error('Change and forecast analysis need one time dimension; …');
  ```
  For the ordinary "amount by company" bar that the studio opens with, every one of
  the four is an error, not a view.

So: on a default verified bar chart, 5 of the 7 analytics objects are either a
no-op or an error, and the two that work (average/median) are the two least likely
to be tried first. That is "does nothing".

### (b) Repro
Chart Studio (verified contributions, Banking) -> drop `company` on Columns and
`amount` on Rows -> **Analytics** tab -> press **Totals**: button turns on, chart
unchanged. Press **Period totals**: error text, no view. Switch mark type to
Treemap or Histogram, press **Average line**: button on, no line, and the note
claims reference statistics apply.

### (c) Fix
`S1-S4-chart-studio.patch` (the S4 half) makes the studio refuse instead of
pretending, using the idiom Show Me already uses (`requirement`/`reason` tiles,
`chart-studio.js:748-778`):
* new `analyticsRefusal(item)` computes, per item, whether the current mode + mark
  type + shelves can express it;
* `renderAnalytics()` disables the button, replaces the hint with the reason and sets
  a title;
* `renderContributionView()` tracks `drewReferences` and the note now says plainly
  when a reference line was **not** drawn, instead of describing an invisible one.

This is deliberately the *honest-refusal* fix, not the *implement-it* fix. The larger
option, if Paul wants the feature rather than the truth about it: teach
`contribution-charts.js` to read `spec.references` (one shared overlay helper, ~40
lines) and give verified **Totals** a real annotation. That is a behaviour change to
published charts and should be Paul's call, so I did not write it.

### (d) Blast radius / risk
Confined to the Analytics pane rendering and one note string. `analyticsRefusal`
returns `''` (allow) in worksheet mode, so the fully-wired path is untouched. Risk:
if my mark-type list is wrong in either direction a user sees a button disabled that
would have worked (recoverable: change mark type) — it can never *enable* something
that does nothing. `node --check` passes; `node --test tests/chart-studio-core.test.js`
still 61/61 (the patch does not touch core).

---

## S1 — the Graph tab's "Create chart" button

### (a) What the Graph tab holds, and whether it can be handed over — CONFIRMED

Graph scope is exactly `graph.js:20-24`:

```js
  function filters() {
    return new URLSearchParams({id:get('run').value,industry:get('industry').value,company:get('company').value,
      tier:get('tier').value,cycle:get('cycle').value,funding:get('funding').value,mode:get('mode').value,
      direction:get('direction').value,category,recipient});
  }
```

plus module-local drill-down state `category` / `recipient` (`graph.js:9`), fetched
from `/api/graph` and `/api/graph-catalog` (`server.py:1236-1238`).

The studio's verified mode accepts a query of
`{dataset, basis, dimensions, measures, filters:[{field,op,value}], aggregate_filters,
sort, limit, offset}` (`chart-studio-contributions.js:107`). I pulled the real field
list from the live catalog (`GET /api/contributions/catalog` on 8805, dataset
`Banking`): dimensions include `industry, cycle, year, company, date, zip5,
contributor, state, city, employer, occupation, recipient, committee_id,
recipient_category, party, funding_source, decision_status, receipt_role, month,
quarter, weekday, amount_bin`.

So the hand-off is **possible**, field by field:

| Graph control | Contribution field | Verdict |
|---|---|---|
| `industry` | dataset id (`Banking` = an industry) | **already handed over** |
| `company` | `company` dimension | carries as a filter pill |
| `cycle` | `cycle` dimension | carries as a filter pill |
| `category` (recipient type) | `recipient_category` | possible, but the value lives only inside graph.js |
| `recipient` | `recipient` | same |
| `funding` | `funding_source` | possible, value vocabulary not yet checked |
| `tier` (employee level) | — none — | **cannot carry** |
| `mode` / `direction` | — none — | **cannot carry** (graph traversal, not a row attribute) |
| `id` (run folder) | — | studio reads the configured report folder, not a run id |

Note the button is **not** fully redundant today: a partial hand-off already exists at
`chart-studio.js:237`, which is easy to miss —

```js
      const previous=el('dataset').value||new URLSearchParams(location.search).get('industry')||document.getElementById('graph-industry')?.value;
```

the studio already defaults its dataset to the Graph tab's industry. What
`chart-studio.js:1394-1400` does is only a view switch:

```js
  const openBuilder = document.getElementById('graph-open-builder');
  if (openBuilder) {
    openBuilder.textContent = 'Create chart';
    openBuilder.removeAttribute('aria-haspopup');
    openBuilder.onclick = () => { if (typeof showView === 'function') showView('chart-studio'); else location.hash = '#chart-studio'; };
  }
```

**Answer to Paul: import is possible, so the button should be redesigned, not
removed.**

### Design options (Paul's call)

* **A. Remove the button.** Cheapest, loses a real affordance, and leaves the silent
  industry hand-off at `:237` as a hidden behaviour. Not recommended.
* **B. "Open in Chart Studio", scope carried as visible filter pills.** On click,
  read `#graph-industry/#graph-company/#graph-cycle`, switch view, and add the
  matching values as ordinary Filters pills the reader can see and delete. Anything
  the dataset has no field for is named in the error line, never silently dropped.
  Mechanism: an in-page module variable (`pendingScope`) — no `sessionStorage`, no
  URL params, because both tabs are the same document and the same script bundle; a
  `CustomEvent` would buy nothing here and adds a listener to reason about.
  **RECOMMENDED.**
* **C. B, plus carry `category`/`recipient`/`funding`.** Requires graph.js to publish
  its drill-down state (it currently keeps `category`/`recipient` module-private,
  `graph.js:9`) and a check of the `funding_source` value vocabulary against the
  Graph tab's `all/corporate/…` values. Do it as a follow-up once B is accepted.

### (c) Fix
`S1-S4-chart-studio.patch` (the S1 half) implements **B**: `GRAPH_SCOPE`,
`graphScope()`, `applyGraphScope()` (filters become normal pills via `commit()`, so
undo works and the reader can remove them), relabels the button **"Open in Chart
Studio"** with a title naming what travels, and calls the hand-off both on click
(when sources are already loaded) and after `loadContributions()` on first open.

### (d) Blast radius / risk
Touches the Graph tab's button and one point in `loadContributions()`. Risks checked:
*silent-scope-drift* — the pills are visible and undoable, so a user can always see
why a number differs from the Graph tab; *wrong-dataset* — `applyGraphScope()` runs
after the dataset is chosen and matches by field **id**, never by column position;
*field missing* — reported through `failure()`, not swallowed; *worksheet mode* —
`applyGraphScope()` returns early unless `verified()`, so nothing happens there.
`pendingScope` is cleared on use, so a stale scope cannot be reapplied later.

---

## Files in this directory

| File | Target | Lines |
|---|---|---|
| `S2-csp-server.patch` | `mentat/app/server.py` | 38 |
| `S2-S3-chart-comparison.patch` | `mentat/app/chart-comparison.js` | 70 |
| `S3-chart-studio-css.patch` | `mentat/app/chart-studio.css` | 16 |
| `S1-S4-chart-studio.patch` | `mentat/app/chart-studio.js` | 154 |
| `make_patches.py` | regenerates `orig/` + `fixed/` from the live tree | — |

Apply order does not matter (four different files). After applying the server patch
Paul must restart the console; after the JS/CSS patches a hard reload is enough.

---

## Addendum — what the comparison lane itself documented

`mentat/app/CHART_COMPARISON.md` (untracked, written 2026-09-13 01:42) states the
intended contract:

> "**Hide all options** creates a comparison view. **Show options** on a chart reopens
> its editor."
> "Restart Mentat after installing code changes."

Two things follow. (1) The restore path in S3 **is** the author's intent, which
supports treating S3 as a labelling/discoverability defect plus the top-level-pane
trap, rather than a missing code path. (2) The lane knew a restart was required —
Paul's consoles on 8802/8803/8804/8808 predate the `server.py` edit, which is
precisely why they 404 the script. The doc says nothing about
`frame-ancestors`, so the iframe design was evidently never exercised against the
server's own CSP header; that is the one genuine oversight in S2.
