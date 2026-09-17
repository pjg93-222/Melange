# S5 DESIGN — Navigation and linking (Area D)

Date: 2026-09-17. Status: **ACCEPTED** by Paul, 2026-09-17, with three rulings:
**A(ii)** show the Graph "Candidate view" select as soon as a report is chosen and make
`mode=activity` linkable, no new tab; **B** leave `mentat/app/graph_data.py` and
`mentat/R/fec_beneficiary.R` untouched (both carry another lane's uncommitted hunks);
**C** keep `history.replaceState`, never `pushState`. Phases 1-3 are built against HEAD
`971d805fc`; HEAD moved to `a565216bf` mid-build (Paul's S3d latency commit, which also
swept in S5's one `server.py` line) and every S5 measurement was taken against those
bytes. See HANDOFF.md's S5 section for what the code contradicted in this document
(§0.5's account of what hides the Candidate view select, and §4's "`server.py`:
untouched"). Designed and reasoned by the session model (Fable) per Paul's 2026-09-16
directive. Line numbers below come from a read-only census of HEAD `971d805fc` on
2026-09-17; re-grep before editing.

## 0. What Area D measured (PACKET.md:982-1096)

1. Six tabs (Loading, Collection, Graph, Chart Studio, Cross-reference, PAC evidence).
   The only navigational state is the tab name in the hash: `history.replaceState(null,
   '', '#' + currentView)` (`app.js:42`), `hashchange -> showView(location.hash.slice(1))`
   (`:53`), init at `:676`. No entity, industry, cycle or filter is ever in the URL;
   `pushState`, `permalink`, `entity_link`: NOT FOUND. "There is no way to link to an
   entity in this console."
2. Click paths from a named entity in Graph: Downstream = one click, nothing lost (same
   view); PAC evidence = one click, industry/entity/cycle/tier/funding/company all lost
   (independent controls); Chart Studio = one click, all Graph selections lost unless the
   "Open in Chart Studio" handler (`chart-studio.js:2628-2638`) set `pendingScope`, and
   returning to Graph loses the scope again; Cross-reference = one click, everything lost
   (separate source, `window.MentatCrossReference?.setActive()` at `app.js:33`).
3. `graph.js:14 clear()` nulls `view` on `loadCatalog()` (`:59`) and `refresh()` (`:74`);
   DOM selections persist, the data object does not.
4. Reload: `sessionStorage` unused; `localStorage` holds only the roster draft, evidence
   preferences and the evidence job id; entity, industry and cycle are lost on reload in
   every tab.
5. Downstream PAC activity is not a tab; it is `<option value="activity">` of the
   `graph-mode` select (`index.html:105`) inside `#graph-candidate-controls`.
   **Corrected during the build:** that container is not "hidden until candidates
   load". `graph.js applyAnalysis()` set `get('candidate-controls').hidden =
   analysis !== 'candidates'`, so the select was reachable only from the Candidates
   analysis tab, at any time, and stripping `hidden` from `index.html` alone would
   have been undone on the next `applyAnalysis()`. Under ruling A(ii) the rule now
   lives in `graph.js` and reads: visible wherever the candidate panel is showing,
   once a report is chosen. `index.html:105` keeps its `hidden` for the moment
   before a report exists. Its data is the "Downstream Activity" worksheet
   (`graph_data.py:83-136 activity_xml_rows`, produced by `fec_beneficiary.R`); the two
   failure texts are `graph_data.py:93` and `:257`. No symbol "PAC analysis" exists.

## 1. Two facts that fix the shape

- Chart Studio ALREADY reads the query string: `new URLSearchParams(location.search)
  .get('industry')` at `chart-studio.js:~337` (dataset preselection) and `studioPane` at
  `:17`. S3's pane model for S6 (HANDOFF:1173-1188) already commits the evidence pane to
  query keys (`?evidence=csv&id=…&committee=…&cycle=…&offset=…`).
- A fragment-only `replaceState('#graph')` resolves against the current URL and KEEPS
  its query string, so the existing tab code preserves whatever scope the query carries.

Therefore: **the hash names the tab; the query string carries the scope.** No second
state store, no new localStorage keys. The URL is the state, so a permalink, a reload
and a tab switch are the same operation.

## 2. Vocabulary (the contract; S6 inherits it)

Query keys, reusing the Graph API's own filter names (`graph.js:20-24 filters()`), so a
URL scope and a `/api/graph` request spell things identically:

| key | value | who writes | who reads |
| --- | --- | --- | --- |
| `industry` | published label (S4; slug accepted by the API, the URL carries the label) | Graph industry select, Chart Studio dataset picker | Graph, Chart Studio, Cross-reference |
| `company` | company name as the Graph select spells it | Graph | Graph, Chart Studio (pill) |
| `cycle` | end year, four digits, as Graph spells it | Graph | Graph, Chart Studio (pill via `core.carriedFilterValue`) |
| `mode` | `direct` \| `activity` \| `estimates` (the `graph-mode` values) | Graph | Graph |
| `direction`, `tier`, `funding`, `category`, `recipient` | Graph filter values, written only when not the default | Graph | Graph |
| `saved` | 32-hex saved-view id | Chart Studio (after save or open) | Chart Studio |
| `studioPane` | existing, unchanged | Chart Studio | Chart Studio |
| `evidence`, `id`, `committee`, `offset`, `limit`, `paneB.*` | RESERVED for S6's pane model; S5 writes none | — | — |

Rules: `showView` keeps writing only the hash; scope keys are written with
`history.replaceState` (never `pushState`: tab switches do not create history entries
today and S5 does not change that; Paul may choose otherwise, question C). A key is
removed from the URL when its control returns to the default/empty. Unknown keys are
preserved untouched (S6's). Values are URL-encoded; labels with `&` survive
(`Property %26 Casualty Insurance`).

## 3. `mentat/app/scope.js` (new, S5-owned)

UMD like `chart-studio-core.js` (browser global `MentatScope`, CommonJS for node tests).
- `read()` -> `{industry, company, cycle, mode, ...}` from `location.search`; validates
  `cycle` (4 digits) and `mode` (enum); invalid values are dropped and reported through
  `read().invalid[]`, never thrown (a bad permalink must still open the tab).
- `write(partial)` -> merges into the current query (empty/undefined removes the key),
  `history.replaceState` with the same hash, then dispatches `mentat:scope` with the new
  scope; no-op when nothing changed.
- `subscribe(fn)` -> `popstate` + `mentat:scope`.
- `href(view, scope)` -> the permalink string for a view and scope, used by the
  "Open in Chart Studio" handler and available to S6 for pane links.
- Pure: no DOM lookups except `location`/`history`; testable in node with a fake
  `location`/`history` pair.

## 4. Wiring, per file

- `index.html` (S5): one `<script src="scope.js">` before `app.js`; `#graph-candidate-controls`
  loses `hidden` so the Candidate view (Downstream) select is visible once a report is
  chosen (question A); the tab strip is unchanged (no new tab: UI simplification law,
  and Paul's wording domain).
- `app.js` (S5): `showView` unchanged; the six tabs stay. **Built without the
  `MentatScope.write({})` call this section proposed**: `write({})` changes nothing,
  and by contract an unchanged URL dispatches nothing, so the call could not make a
  listener re-read. None needs it - each view re-reads on its own entry (`graph.js`
  in `loadCatalog`, `chart-studio.js` in `activate`, `cross-reference.js` in
  `setActive`). `app.js` therefore carries a comment and no behaviour change, which
  keeps a heavily contended file at zero risk.
- `graph.js` (S5): after `loadCatalog()` fills the selects, apply `MentatScope.read()` to
  industry/company/cycle/mode/direction/tier/funding/category/recipient before the first
  `refresh()`; on every control change (the existing `syncControls`/`refresh` path) call
  `MentatScope.write(filtersAsScope())`. `clear()` stays as written: scope now lives in
  the URL, so `loadCatalog()`'s `clear()` no longer loses it. The "Open in Chart Studio"
  handler writes `MentatScope.write({industry, company, cycle})` before `showView`.
- `chart-studio.js` (S5): `loadContributions()` keeps its `?industry=` preselection (now
  through `MentatScope.read()`); after `selectContributionDataset()` it writes `industry`
  back; when the URL carries `company`/`cycle` and no `pendingScope`, it builds
  `pendingScope` from the URL (same shape `graphScope()` produces) so `applyGraphScope()`
  carries them as pills; `saved=<id>` -> after the catalog loads, `openView({id})` through
  the existing `openability()`; saving or opening a view writes `saved`.
- `cross-reference.js` (unowned; S5 claims it in the table): when `MentatScope.read()
  .industry` is set, fetch `/api/cross-reference?industry=<label>` (S4 route), else the
  bare route; render `selected_by` ("newest run for Banking" vs "latest run"); re-fetch
  on `mentat:scope` when `industry` changes.
- `graph_data.py`, `fec_beneficiary.R` (S5 per the table): NOT TOUCHED. Both carry
  another lane's uncommitted hunks (`graph_data.py` +60/-11 `singleflight_cache`;
  `fec_beneficiary.R` +21/-8 PAS2 parser v4), and navigation needs neither. Their
  Downstream failure texts stay; question B.
- `server.py`: **one line**, not untouched. `/?anything` does already serve
  `index.html` (`studioPane` proves it) and the cross-reference route does already
  take `industry`, so no routing changed - but `STATIC_ASSETS` (`server.py:58-91`)
  is an allow-list and `do_GET` answers 404 for any path not in it (`:1963-1982`),
  so a new client script cannot be served without an entry:
  `'/scope.js': ('scope.js', 'text/javascript'),` in `server.py` (grep it; `:71` when
  it landed, `:97` once a later session inserted lazy imports above it). That line
  landed in Paul's `a565216bf` (S3d's latency commit, which swept it in six minutes
  after S5 wrote it), so **the S5 patch carries no `server.py` hunk**.

## 5. Contract and tests (DE-021 method)

- `contracts/url_scope.json` (v1, owner S5): the key table above as data; examples: a
  Graph permalink `/?industry=Banking&company=JPMorgan%20Chase&cycle=2024&mode=activity#graph`,
  a Chart Studio permalink `/?industry=Credit%20Union&company=Navy%20Federal&cycle=2024#chart-studio`,
  a saved-view permalink `/?industry=Banking&saved=<32hex>#chart-studio`, a cross-reference
  permalink `/?industry=Banking#cross-reference`; the `read()` result for each; the
  `write()` merge semantics (remove-on-empty, preserve-unknown); negative controls:
  `mode=pac`, `cycle=24`, `industry=` (blank), `saved=xyz`. Producers listed: scope.js
  write(), graph.js, chart-studio.js. Consumers: scope.js read(), graph.js,
  chart-studio.js, cross-reference.js, S6.
- Node: `app/tests/scope.test.js` imports the contract; round-trips every example through
  `read`/`write`/`href`; negative controls drop the bad key and report it.
- Browser: `tests/test_navigation_scope_browser.cjs` (Playwright, spawn pattern of
  `test_studio_industry_browser.cjs`, two stubbed datasets + a stubbed graph catalog as
  `test_graph_lazy_tables_browser.cjs` does), **13 steps as built**: open the Graph
  permalink and assert the controls (1); switch to Chart Studio and assert dataset +
  pills (2); back to Graph, scope intact (3); reload, intact (4); Cross-reference tab
  issues `/api/cross-reference?industry=…` (5); a Graph control change moves the URL
  (6); "Open in Chart Studio" rewrites the URL (7); the `saved=` permalink opens the
  view on a second page (8); negative control, `mode=pac` opens Graph on `direct` (9);
  ruling A(ii), the Candidate view select is visible (10); a permalink's cycle is not
  overridden by `latest=1` (11); the first edit after an open drops `saved=` and the
  permalink still re-opens the view (12); an industry with no cross-reference run says
  so (13).
- No python route change, so no new python suite; the existing browser tests that touch
  tabs (`test_console_browser.cjs`, `test_app_lazy_startup_browser.cjs`,
  `test_graph_lazy_tables_browser.cjs`) must stay at their baseline.

### Review (Fable, 2026-09-17, on the S5 diff)

Three findings, each fixed only after its new step had been written and RUN against
the pre-fix bytes, so no fix rests on an argument alone. Pre-fix assertions verbatim
in `receipts/S5_phase1-3.txt`.

| # | Finding | Fix | Step |
| --- | --- | --- | --- |
| 1 (HIGH) | `refresh(initial)` sent `&latest=1` unconditionally, and `graph_view()` replaces the requested cycle with `max(years)` when it is present (`graph_data.py:317-318`), so the URL said 2022 while the view showed 2024. S5's own step 1 could not see it: the fixture's newest cycle is the one that permalink asks for. | `graph.js:125` sends it only when `initial && !query.get('cycle')`; the stub now mirrors the server rule so the hole cannot reopen. | **11**, pre-fix `'2024' !== '2022'` |
| 2 (HIGH) | `saved=<id>` outlived the sheets it described: edit the opened view, reload, and `openSavedFromUrl()` re-opened it while `persist()` wrote over every edit since - **a data loss that did not exist before S5 put the id in the URL**. | the first change to the working sheets clears the id, at `commit()` (`:142`) and `step()` (`:154`, undo/redo bypasses `commit`), never at `persist()` (it also runs on load paths and would destroy the permalink before it is read); an open fences its own `commit` (`:2006-2013`). | **12**, pre-fix `saved= leaving the URL after the first edit never happened` |
| 3 (MED) | an industry-scoped ask that found nothing still said "Latest run", naming the one run it was not showing. | `cross-reference.js:150-160` answers "No cross-reference run for <label>"; both branches are pinned (step 5 the found run, step 13 the empty one). | **13**, pre-fix `got "Latest run · Saved evidence refreshed."` |

## 6. Phases (one architect dispatch for 1-3, Fable review, then close-out)

| # | Phase | Exit |
| --- | --- | --- |
| 0 | Paul's go; questions A-C | recorded |
| 1 | Contract + README index row | negative controls non-empty |
| 2 | scope.js + node tests | 100% of contract examples round-trip |
| 3 | Wiring (index.html, app.js, graph.js, chart-studio.js, cross-reference.js) + browser test + real-client pass | browser pass green; baseline browser tests unchanged |
| 4 | Fable review (inline) + fix; sweep in parallel | zero HIGH |
| 5 | Patch cut once after `git log -1`; HANDOFF S5 section with the URL vocabulary for S6; Paul commits; restart; brain + session | done |

Write path for the architect: python scripts run from Bash (Edit/Write refuse Mentat
paths in this session; DE-022). Never Sonnet or Haiku for code.

## 7. Questions for Paul

- **A. Downstream visibility.** Options: (i) leave the select hidden until candidates load
  but make `mode=activity` linkable; (ii) also show the Candidate view select as soon as
  a report is chosen (recommended, no new surface); (iii) a seventh tab "PAC activity"
  (not recommended: UI simplification law, and it duplicates a Graph mode).
- **B. Downstream production gaps.** If any industry's report lacks the worksheet, the
  fix is in `fec_beneficiary.R` (collection side, another lane's uncommitted hunks). S5
  proposes leaving both readers untouched. Confirm, or name the industry that is missing
  it and S5 measures.
- **C. History.** Keep `replaceState` (Back never steps through tabs, as today) or move
  tab switches to `pushState` so Back walks the tabs. Recommended: keep `replaceState`.
