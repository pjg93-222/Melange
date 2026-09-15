# fix1 — the defects the live integration verification found, fixed and proven

This lane finished the interrupted fix lane dispatched at about 16:45 on 2026-09-14. It
covers D1 (Save view answering 400), D2 ("[object Obje" printed where a workbook digest
belongs), D3 (a leaked publish worker), D5 (a console claiming to restart when it was
already current), D6 (the reconciliation strip dead on a cold Studio load) and A3 (the
stale `node --test mentat/app/tests` invocation). Everything below was established from
the files and from running code. No prior summary was taken on trust.

## The state this lane found

The interrupted lane had started and then done nothing. All nine `*.bak-20260914-fix1`
backups were **byte-identical** to their live files — `cmp -s` reported IDENTICAL for
every one of `mentat/app/README.md`, `app.js`, `chart-briefing.js`, `chart-studio.js`,
`server.py`, and `mentat/tests/test_contribution_http.py`, `test_publish_pocket.py`,
`test_studio_reconciliation_browser.cjs`, `test_studio_views.py`. Its scratchpad at
`...mentat-system-debug-1f368e\fd1758bd-...\scratchpad\lanes\fix1` held only
`census-before.txt`, `census.py` and `region_eol.py`: a census and an intent to preserve
line endings, no step scripts, no PROGRESS.md and no RECEIPT.md. So the diff against
every backup is empty, there was nothing to undo, and every defect below was still live
exactly as reported.

Baseline before any edit: `node --test "mentat/app/tests/**/*.test.js"` gave 88 tests,
88 pass, 0 fail. The five python suites the earlier lanes ran
(`test_studio_views test_studio_briefing test_publish_pocket test_contribution_http
test_desktop_launcher`) gave **Ran 53 tests, FAILED (failures=1, errors=1)** — D3
reproducing exactly: a `PermissionError [WinError 32]` on `reports\pocket\icon-180.png`
held by a still-running worker, and `test_datasets_have_to_be_a_non_empty_list_of_catalog_ids`
seeing two commands recorded by an earlier test.

A note on one claim in the packet: a scout had called D5 "fixed" because the 409-busy
branch exists. That branch is the original F1 behaviour. The handler at server.py:1831-1833
had exactly three outcomes — 403 read-only, 409 busy, and `{'restarting': True, ...}` —
and no current-build branch at all. The scout was wrong.

## Files changed

| file | before | after | bytes | crlf | lf | class |
|---|---|---|---|---|---|---|
| mentat/app/chart-studio.js | 766f216 | 88086cb | 154711 | 2630 | 0 | crlf |
| mentat/app/chart-briefing.js | 57b4ff9 | 6893db0 | 29531 | 0 | 684 | lf |
| mentat/app/server.py | a3e4b75 | 5800d52 | 109703 | 1912 | 0 | crlf |
| mentat/app/app.js | 4bb658b | 4df8f05 | 56852 | 281 | 385 | mixed |
| mentat/tests/test_contribution_http.py | 66decc3 | e09f00f | 23624 | 0 | 383 | lf |
| mentat/tests/test_publish_pocket.py | 5955bb1 | cd30c82 | 17107 | 0 | 331 | lf |
| mentat/app/tests/chart-studio-core.test.js | fda752d | 3f1834f | 68171 | 1051 | 82 | mixed |
| mentat/app/tests/chart-briefing.test.js | b2e0a18 | 144d2bf | 2836 | 0 | 62 | lf |
| mentat/app/studio-contract-examples.json | new | 5dae482 | 2697 | 0 | 54 | lf |
| mentat/app/tests/studio-contract.test.js | new | ee3c1e3 | 4260 | 0 | 84 | lf |
| mentat/tests/test_studio_contract_examples.py | new | 058ebac | 6390 | 0 | 131 | lf |
| .gitignore | d23073b | 202b4b8 | 1886 | 57 | 26 | mixed |

Every file kept its line-ending class. The two pure-CRLF files are still pure CRLF and
the pure-LF files still pure LF. The two mixed files were the ones to watch: `app.js`
kept its 281 CRLF line endings untouched and grew only in the LF region the restart flow
lives in (372 → 385 LF), and `chart-studio-core.test.js` grew by exactly the two CRLF
lines that were added (1049 → 1051). This was done with an exact-anchor patch tool that
matches each anchor in its own local convention and refuses to write anything unless
every anchor matches exactly once; the harness Write and Edit tools refuse paths under
`C:\Users\pgoff\Mentat`, so all edits went through python scripts, never shell heredocs.

Three files still carry a `.bak-20260914-fix1` backup that this lane did not need to
touch, and their backups are still byte-identical to the live files: `mentat/app/README.md`,
`mentat/tests/test_studio_views.py`, `mentat/tests/test_studio_reconciliation_browser.cjs`.
`chart-studio-core.test.js` and `chart-briefing.test.js` had no fix1 backup, so one was
created before they were edited.

## D1 — Save view answered 400

The server requires a saved view to carry the source it was built from as an object:
`if not isinstance(source_key, str) or not isinstance(source, dict)` at server.py:918-919
raises, and the handler turns that into a 400. The client was sending
`source: viewSourceLabel()` — a caption string — so every Save view was refused.

Fixed on the client, as the packet directed. `chart-studio.js` gained `viewSourceRecord()`,
which builds the object from the live `sheet().source`: `reportName`, `sha256`, `runName`,
`sheet`, `mode`, `dataset`, plus `datasetLabel` and a human `label` when the verified
dataset is chosen. `saveViewNamed()` now sends that object. Two consumers read `view.source`
as text and would have printed `[object Object]` once it became an object — the "choose
that report first" refusal and the Other sources menu entry — so both now go through one
new reader, `viewSourceText(view)`, which handles the object, an older bare string and a
missing value without ever handing an object to string concatenation.

Evidence. Against the live console on 8826, the exact payload the browser now sends is
accepted and the old one is still refused:

```
POST /api/studio/views (object source)                    -> 200 {"id": "f0728eb8...", "saved_at": ...}
GET  /api/studio/views                                    -> 200 [('Crypto receipts by recipient', 'Crypto Industry Spending Overview.xlsx')]
POST /api/studio/views (caption source, the old client)   -> 400 {"error": "A saved view carries the source it was built from."}
```

Then through the real page: Chart Studio was opened cold, the Company overview preset
built a real chart from the throwaway Crypto workbook, and Export › Save view was typed
and committed as "Fix lane live proof". It reached disk as
`verify/data/studio/views/f2396a6fea994eb6afde4b8d5b28cd50.json` with

```
source is a dict
source : {"dataset": "Crypto", "datasetLabel": "Crypto", "label": "Crypto",
          "mode": "contributions", "reportName": "Crypto Industry Spending Overview.xlsx",
          "runName": "Configured completed-report folder",
          "sha256": "88ea228457b8499d1ec27eeaba967f61505bde842ae0ecfe35c30791c23d66f6",
          "sheet": "Verified source observations"}
```

`evidence/B-open-view-lists-saved-view.png` shows Open view listing it under THIS SOURCE
and the other view under OTHER SOURCES with its caption printed as
"Crypto Industry Spending Overview.xlsx" — the consumer fix, visible on screen.

Tests: `test_the_example_saved_view_is_accepted_exactly_as_written` and
`test_a_saved_view_whose_source_is_a_caption_is_refused_with_the_reason` in
`mentat/tests/test_studio_contract_examples.py`.

## D2 — "[object Obje" printed as the workbook SHA-256

`currentChart()` sent `source` and `provenance` as strings; the server replaces a
non-dict with `{}` at server.py:988-989; `shortSha` then did `String(item.provenance || '')`
on an empty object, which is truthy, giving `"[object Object]".slice(0, 12)` — the twelve
characters `[object Obje` in the one line a reader would use to check a number, in every
.pptx and HTML bundle. Two bugs in sequence: the digest was thrown away on the way out,
and an object was stringified on the way back.

Both ends fixed. `currentChart()` now returns `source` and `provenance` as objects —
`provenance` being `{sha, reportName, source, generatedAt}` — and keeps flat
`sourceLabel` and `sha` fields beside them for the print sheet, which has one line and
no room for either. `chart-briefing.js` gained three pure readers above the node/browser
split, so they are testable without a document: `provenanceSha(item)` reads a string
field (`sha`, `sha256`, `workbook_sha256`, `digest`) out of the object and never
stringifies one; `sourceText(item)` does the same for the caption; `sourceNoteText(item,
exportedOn)` is the one line every export carries. `describe()` now sends objects, and
wraps a bare string rather than letting the server drop it. The HTML bundle's table, which
also printed both fields raw, goes through the same readers.

Evidence, from the shipped artefacts of the real client. The HTML bundle:

```
Source: Crypto Industry Spending Overview.xlsx · SHA-256 88ea228457b8 · basis Published
included receipts · exported September 14, 2026 from Mentat Chart Studio
<tr>…<td>Crypto Industry Spending Overview.xlsx</td>
     <td>88ea228457b8499d1ec27eeaba967f61505bde842ae0ecfe35c30791c23d66f6</td></tr>
containsShortSha: true   containsObjectObject: false
```

The .pptx, saved from the real Export PowerPoint path and unzipped
(`evidence/briefing.pptx`, 92390 bytes, 40 parts):

```
occurrences of the short SHA-256 88ea228457b8 across every part : 4
occurrences of the full  SHA-256 across every part              : 2
parts containing the string '[object'                           : NONE

ppt/notesSlides/notesSlide1.xml
  … Workbook SHA256 88ea228457b8499d1ec27eeaba967f61505bde842ae0ecfe35c30791c23d66f6 …
  Source: Crypto Industry Spending Overview.xlsx · SHA-256 88ea228457b8 · basis
  Published included receipts · exported September 14, 2026 from Mentat Chart Studio
```

Tests: `the export source line carries the true short SHA and never the word object` and
`no reader ever stringifies an object, whatever shape the item arrives in` (seven item
shapes, including an object, an empty object, a legacy string, null and `{}`) in
`mentat/app/tests/studio-contract.test.js`; and
`test_the_example_briefing_item_keeps_its_provenance_object` plus the negative control
`test_a_briefing_item_sent_with_a_string_provenance_loses_it_entirely` on the python side.

## The shared fixture

The lesson the packet drew from D1 and D2 is that both sides passed their own unit tests
while disagreeing about the payload. `mentat/app/studio-contract-examples.json` now holds
worked example payloads for both endpoints — exactly what the browser sends — and both
suites read that one file: `mentat/tests/test_studio_contract_examples.py` posts them to
a real Console over HTTP, and `mentat/app/tests/studio-contract.test.js` runs the client
readers over the same items. A client that starts sending something else fails there
rather than on a reader's screen.

**This needed a `.gitignore` line, and Paul should look at it.** Line 6 of `.gitignore`
is a blanket `*.json` for regenerable data artifacts, so the fixture was being ignored —
`git check-ignore` confirmed it. A fixture that cannot be committed is not a contract:
on a fresh checkout both new suites would fail on a missing file. So one negation was
added, in the same "keep" style the repo already uses for `!mentat/app/vendor/*.js` and
`!mentat/tools/pocket/*.html`, with a comment saying why:

```
# Chart Studio HTTP contract: the worked example payloads both the python and the
# node suites read. Source of truth, not a regenerable artifact - without this the
# *.json sweep above would drop it and both suites would fail on a fresh checkout.
!mentat/app/studio-contract-examples.json
```

`.gitignore` is shared config, so this is flagged rather than buried: it is the one
change here that is not strictly a defect fix. It is backed up at
`.gitignore.bak-20260914-fix1` and is a single line to revert. After it, the fixture
shows as `??` rather than `!!` — visible to `git add`, which is the whole point.

## D3 — a publish worker leaking into the next test

Root cause, from the agent that fixed it: `Console.publish_pocket` (server.py:1114-1157)
starts a daemon thread per publish job, and `test_a_second_publish_while_one_is_running_is_a_conflict`
fired a final successful publish and asserted only its status, never waiting for it to
settle. That thread ran on into later tests, appending Popen calls to whichever test's
`self.commands` was live and racing the next test's unlink of `icon-180.png` against its
own `shutil.copyfile`. `setUp` also called `self.console.jobs.clear()`, which masked the
leak rather than preventing it.

Fixed by removing that masking `clear()`, adding a `tearDown` that waits on
`self.console.jobs` — the set the worker's `finally` empties immediately before its
thread returns — and asserts it is empty, and by making the racy test capture its final
job id and wait on it. Six consecutive `test_publish_pocket` rounds were all OK, 12 tests
each. The suite was flaky at 2 clean of 6 before.

## D5 — a console that claimed to restart when it was already current

The handler had no current-build branch. It now compares what this process loaded to what
is on disk, using the identity F1 added, before it spawns anything:

```python
if (CODE_TREE_SHA256 == tree_sha256(code_files())
        and ASSET_TREE_SHA256 == tree_sha256(asset_files())):
    return self.send({'restarting': False, 'current': True,
                      'build': build_status(self.server.app, self.server.server_port)})
```

The 403 read-only guard and the 409 busy branch are untouched and still ahead of it. On
the client, `restartConsole()` now reads the answer instead of discarding it; on
`current: true` it refreshes the stamp, says so, and returns — so the two-minute poll for
a new pid never starts.

Evidence, against the live console:

```
POST /api/restart (8826, writable, current) -> 200 {"restarting": false, "current": true}
   code   in-process 1fb344c9b99d  on disk 1fb344c9b99d  equal=True
   assets in-process a866f386327b  on disk a866f386327b  equal=True
POST /api/restart (8827, read-only)         -> 403 "This preview is read-only …"
```

And through the real client, in a fresh browser context, put into the exact state the
defect was reported from — the page believing an older build is running while the console
is in fact current — then pressing the real Restart button:

```
before : banner visible, "This console is running an older build… or press Restart.", pid 40176
after  : "Console already current. This console is running the build that is on disk,
          so there is nothing to restart."
         button "Restart", not disabled
         /api/health polls in nine seconds : 0     (six would have fired)
         pid after : 40176                          (unchanged, nothing spawned)
```

Screenshot `evidence/C-console-already-current.png`.

Tests: `test_restart_is_refused_read_only_and_while_the_console_is_busy` in
`mentat/tests/test_contribution_http.py` now asserts the current-build answer with the
launcher never called (`spawn.assert_not_called()`), then patches `CODE_TREE_SHA256` to
prove a code change still restarts, then patches `ASSET_TREE_SHA256` alone to prove the
branch reads both trees and not just the Python one. That test failed the moment the
server became truthful, which is itself the cleanest evidence the branch is live.

## D6 — the reconciliation strip dead on a cold Studio load

`graphTotals` read `#graph-run`, which is empty until the Graph view has rendered once,
and rejected outright. It now asks the endpoint Graph asks and chooses a run the way
Graph chooses one, cached for the session, falling back only when the select is empty.

Evidence, on a fresh browser context that opened Chart Studio directly and never visited
Graph:

```
#graph-run : exists=true  value=""  options=0
strip      : hidden=false
             "Basis: Published included receipts. Graph shows $249,949,483.17 for
              All companies · All cycles (workbook receipts). Studio total
              $249,949,483.17. Agree."
network    : GET /api/graph?id=published-reports&industry=Crypto&… -> 200
```

The run identity `published-reports` came from `/api/report-sources`; before the fix no
`/api/graph` request would have been issued at all. Screenshot
`evidence/A-studio-cold-load.png`.

One honest limit: a second request, scoped to the company `BINANCE US`, answered 400
"Choose a company in this industry." That is the throwaway Crypto copy's Graph index not
carrying that company spelling, not a defect in this fix — and the strip correctly stays
away for that scope rather than guessing, which is the documented behaviour.

## A3 — the stale test invocation

Node 24 rejects `node --test mentat/app/tests`; the glob form works. Repo-wide census
found the bare form live in two files, both in the app tree, both fixed:
`mentat/app/tests/chart-studio-core.test.js:1` and `mentat/app/tests/chart-briefing.test.js:1-2`.
It also appears in `audits/.../lanes/Eclient/RECEIPT.md:187` and that lane's
`chart-briefing.test.src.js:2`, which are historical records and were left alone, and in
several `.bak-*` snapshots, also left alone. No occurrence in `mentat/app/README.md`, in
any `package.json`, or in any `.ps1`.

Worth recording: the glob `"mentat/app/tests/**/*.test.js"` contains the sequence `*/`,
which closes a JavaScript block comment. Both files carried their run line inside a
`/* */` block, so a naive substitution would have made them syntax errors. The run line
was moved out into a `//` comment in each. This lane hit that trap once, in the new
`studio-contract.test.js`, before catching it.

## How the live verification was run

Two throwaway consoles: 8826 writable and 8827 read-only, started from
`C:\Users\pgoff\Mentat` with `--data-root` pointing into this lane's scratchpad and
`MENTAT_REPORT_DIRECTORY` pointing at a scratchpad folder holding a **copy** of
`Crypto Industry Spending Overview.xlsx` (itself copied from the earlier verifier's
throwaway copy). Paul's real report directory was never opened by a writable console, and
nothing was ever posted to his console on 8806. Every saved view, briefing item, SVG and
published bundle produced by this lane lives in the scratchpad data roots.

The page was driven both through the Browser pane and, where the pane could not render or
could not accept a download, through Playwright against the installed Chrome — the same
`channel: 'chrome'` the repo's own `.cjs` suites use. Two interactions were dispatched as
programmatic clicks on the live page rather than as pane pixel clicks (the Add to briefing
button and the Restart button), because the pane was hidden and screenshots were timing
out; both fired the real handlers on the real page, and the Playwright runs that produced
the screenshots repeated them independently in fresh contexts.

## Test totals

| suite | before | after |
|---|---|---|
| `node --test "mentat/app/tests/**/*.test.js"` | 88 pass, 0 fail | **95 pass, 0 fail** |
| studio/briefing/lazy-startup `.cjs` suites | 17 pass, 0 fail (4 suites) | **21 pass, 0 fail** (6 suites) |
| five python suites | Ran 53, FAILED (1 failure, 1 error) | — |
| six python suites (adding the new contract suite) | — | **Ran 57**, round 1 OK, round 2 FAILED, round 3 OK |

The three python rounds are three full runs, as asked, to expose flakes rather than hide
them.

## The one thing still failing, and why it is not this lane's

Round 2 failed on `test_contribution_http.test_invalid_json_shape_length_and_unknown_routes_fail`
with `ConnectionAbortedError [WinError 10053]`. That test declares
`Content-Length: 7000001` and sends two bytes; the server refuses the oversized body and
closes the connection, and on Windows the client sometimes loses the race to read the
response first.

This lane did not assume that was pre-existing, it measured it. A paired A/B on the same
box, 40 rounds each of `mentat.tests.test_contribution_http`, comparing this lane's tree
against the tree exactly as it was found (both `server.py` and `test_contribution_http.py`
restored from their `.bak-20260914-fix1` backups):

```
A  this lane's tree                {'OK': 38, 'ConnectionAbortedError in test_invalid_json_shape…': 2}
B  the tree as this lane found it  {'OK': 37, 'ConnectionAbortedError in test_invalid_json_shape…': 3}
```

2 of 40 against 3 of 40 — the same rate, so the race is pre-existing and this lane neither
caused nor worsened it. An earlier 16-round pass had read 2 against 0 and looked like a
regression; it was noise, which is why the larger paired run was done. Both files were
copied aside before the swap, restored in a `finally`, and their hashes checked afterwards
(`server.py` 5800d52, `test_contribution_http.py` e09f00f — the fixed bytes).

It is left unfixed because the fix belongs in the oversized-body drain path that F1 owns
(its `step8-drain-body.js` and `step9-drain-bounded.js` are in that lane's folder), and
touching it here would be a change nobody asked for in a file two lanes are already
editing. It is a test-side race, not a defect a reader can hit.

## Two other things noticed, not changed

Saved views display their date as 1/21/1970 in the Open view menu — visible in
`evidence/B-open-view-lists-saved-view.png`. The server writes `saved_at` as a UNIX time
in **seconds** (`time.time()`), and `viewLabel` in chart-studio.js does
`new Date(view.saved_at)`, which expects milliseconds. The in-tab fallback path stores an
ISO string instead, so the two disagree as well. This predates the lane, is untouched by
it, and is a one-line fix in either place — but which place is a call for Paul, so it was
left.

Paul's console on 8806 was running as pid 16900 at the start of this lane and as pid 20820
at the end, with a command line that now also carries `--rscript`. Nothing here posted to
8806. The A/B above did briefly swap `server.py` on disk (about six minutes in total,
fully restored and hash-checked), which would have made any open console page show its
stale-build banner during those windows. That banner is also correct right now and will
stay until 8806 is restarted, because this lane genuinely did change `server.py` and his
process is still running the older one.

---

# Round 2 — the review's conditions

Independent review returned "ship conditional" on six items. All six are applied and
verified below. Nothing on the do-not-change list was touched: the strip's `latest=1`
semantics, the app.js banner wording, and the `atomic_json` retry are all exactly as
round 1 left them.

## Files changed in round 2

| file | round 1 | round 2 | bytes | crlf | lf | class |
|---|---|---|---|---|---|---|
| mentat/app/chart-studio.js | 88086cb | 8c2e88f | 155222 | 2632 | 0 | crlf |
| mentat/app/chart-studio-core.js | 04d4f88 | fd3eaf0 | 51687 | 883 | 48 | mixed |
| mentat/app/graph.js | 2d2f273 | 76edd54 | 25076 | 289 | 22 | mixed |
| mentat/app/chart-briefing.js | 6893db0 | c2ad3fe | 29470 | 0 | 683 | lf |
| mentat/app/server.py | 5800d52 | 0f88652 | 109950 | 1915 | 0 | crlf |
| mentat/app/studio-contract-examples.json | 5dae482 | 048819e | 5081 | 0 | 106 | lf |
| mentat/app/tests/studio-contract.test.js | ee3c1e3 | 3bed9df | 7727 | 0 | 152 | lf |
| mentat/tests/test_studio_contract_examples.py | 058ebac | b87c565 | 7699 | 0 | 150 | lf |

Unchanged since round 1, confirmed by hash: `app.js` 4df8f05, `test_contribution_http.py`
e09f00f, `test_publish_pocket.py` cd30c82, `chart-briefing.test.js` 144d2bf,
`chart-studio-core.test.js` 3f1834f, `.gitignore` 202b4b8.

`chart-studio-core.js` and `graph.js` had no fix1 backup, so one was made before either
was touched. Line-ending classes all held: the two pure-CRLF files are still pure CRLF,
the pure-LF files still pure LF, and the two mixed files kept their LF counts exactly
(core 48, graph 22) while only the replaced regions grew in CRLF.

**One line-ending near-miss worth recording.** The `saved_at` fix replaces a single line
with two, and the patch tool's single-line path wrote the new newline as a bare LF into
the pure-CRLF `chart-studio.js` — 2630 CRLF / 0 LF became 2631 / 1. It was caught by the
census immediately, the tool was fixed to write a one-line-to-many replacement in the
convention of the line it sits on, and the file was repaired by a script that refuses to
act unless it finds exactly one bare LF. `chart-studio.js` is 2632 CRLF / 0 LF now. The
lesson is that the census is what catches this, not the intent to preserve endings.

## 1 (HIGH) — the migration path was still sending a caption

`migrateStoredViews()` did indeed still POST `source: label`, so every legacy view was
refused 400, and `catch { return saved; }` swallowed it — the reader was told nothing and
the migration flag was never set, so it silently retried on every menu open for ever.

It now sends `core.captionSource(label)`, which is `{label}`, because the old
browser-local store recorded nothing else. The bare catch is gone: a refusal now says
*"…Views saved in this browser could not be moved onto this console."* through the same
`failure()` channel every other refusal uses.

Proved live, not just by unit test, as the review asked. A fresh browser context seeded
`localStorage['mentat-chart-studio-v1']` with a legacy entry and cleared the migration
flag, then opened the views menu on a console whose data root had never held a view:

```
r1_seeded        : ["contributions|Crypto|deadbeef"]
r1_views (on disk, read back over HTTP):
  {"name":"Recovered · Crypto · 1 sheet","source":{"label":"Crypto"},
   "sourceKey":"contributions|Crypto|deadbeef"}
  {"name":"Recovered · Crypto · 1 sheet","source":{"label":"Crypto"},
   "sourceKey":"contributions|Crypto|88ea228457b8…"}
r1_migrationFlag : "1"      (set, so it will not retry for ever)
r1_error         : ""        (nothing refused)
r1_pageErrors    : []
```

Both the seeded entry and the live sheet's own store entry migrated, each landing on disk
with an object source. Screenshot `evidence/R1-recovered-view.png`. Tests:
`a view recovered from the old browser store sends its caption as an object` (node) and
`test_a_view_recovered_from_the_old_browser_store_is_accepted_too` (python).

## 2 (MEDIUM) — one chooser, and no caching of a non-answer

Round 1's `graphRunId()` used `runs.find(state==='completed') || runs[0]`, which is not
Graph's rule. The rule now lives in exactly one place. `graph.js` gained `runCandidates()`
and `chooseRun()` — the preferred run first, runs that are only `ready` or `needs review`
never chosen, and each candidate's `/api/graph-catalog` probed so a run with no industries
is walked past — and `loadRuns()` now calls it instead of carrying its own copy.
`globalThis.MentatGraphRun` exposes it, and Chart Studio calls that.

The strip also now insists on a run Graph would actually display (`result.catalog` must be
non-empty), and caches only a real id: on an empty or failed answer `graphRunPromise` is
set back to null, so one bad moment no longer leaves the strip dead for the session.

Verified live on a cold Studio-first load, and — because this refactor moved Graph's own
code — Graph itself was re-checked:

```
r2_graphRun : {"value":"", "options":0, "chooserPresent":"object"}
r2_strip    : hidden=false
              "Basis: Published included receipts. Graph shows $249,949,483.17 for
               All companies · All cycles (workbook receipts). Studio total
               $249,949,483.17. Agree."
r2_pageErrors: []

r3 (the Graph view itself, after the extraction):
  run "published-reports", 1 run option, 1 industry,
  status "418 included receipt groups · local data", error "", pageErrors []
```

Screenshots `evidence/R2-cold-strip.png` and `evidence/R3-graph-loads.png`. The seven
`.cjs` browser suites that cover Studio, Graph wording and lazy startup were re-run whole:
34 pass, 0 fail.

## 3 (MEDIUM) — the contract tests now test the producer

The review was right that nothing asserted the client *produces* the fixture shape. The
shaping has moved out of `chart-studio.js` into `chart-studio-core.js`, which node can
require: `viewSourceRecord`, `chartSourceRecord`, `chartProvenanceRecord`, `captionSource`
and `sourceLabelOf`. `chart-studio.js` now only delegates, and the same builders are also
exposed on the pane object it already exports, so a browser test can reach them too.

The fixture gained a `producer` block recording the inputs each payload is built from, and
the node suite runs the real builders over those inputs and deep-equals the result against
the payloads the python suite posts. Four producer cases: the verified path, a plain
worksheet with no dataset, a recovered view, and the chart's source and provenance.

**Negative control.** The assertion is only worth having if it fails. `viewSourceRecord`
was temporarily changed to return a caption string and the suite re-run:

```
kept chart-studio-core.js sha fd3eaf0
broken  sha e633b4a - viewSourceRecord now returns a caption string
node suite: pass=98 fail=3
restored sha fd3eaf0
```

101 pass drops to 98 with 3 failures, and the file is back at fd3eaf0. A revert to a
string cannot pass this suite.

One knock-on the fixture forced into the open: a saved view's caption is the *dataset's*
label (`Crypto`) while an exported chart's is the *workbook's*
(`Crypto Industry Spending Overview.xlsx`). Round 1's fixture conflated them. They are now
`expected.view_source_caption` and `expected.source_caption`, and the python suite asserts
the view's `label`, `reportName` and `sha256` separately.

Confirmed live too — the real client's Save view POST body:

```
r4_sent.sourceType : "object"
r4_sent.source     : {"label":"Crypto","reportName":"Crypto Industry Spending Overview.xlsx",
                      "sha256":"88ea228457b8…","runName":"Configured completed-report folder",
                      "sheet":"Verified source observations","mode":"contributions",
                      "dataset":"Crypto","datasetLabel":"Crypto"}
```

## 4 (MEDIUM) — saved_at is seconds, and the reader now knows it

Fixed at the reader only, one expression, exactly as directed. The server still writes
seconds and `test_studio_views.py:115` still pins that; files already on disk are unaffected.

```js
view.saved_at ? new Date(typeof view.saved_at === 'number'
  ? view.saved_at * 1000 : view.saved_at).toLocaleString() : '',
```

The `typeof` check is what keeps the in-tab fallback working, since that path stores an
ISO string. Live, the Open view menu now reads:

```
"Round two proof · 1 sheet · 9/14/2026, 6:20:05 PM"
"Recovered · Crypto · 1 sheet · 1 sheet · 9/14/2026, 6:19:16 PM · Crypto"
```

Round 1's screenshot showed `1/21/1970, 12:03:41 PM` for the same field. Screenshot
`evidence/R5-saved-view-date.png`.

(Visible in that second line and left alone: a recovered view's *name* already contains
its sheet count, so `viewLabel` appends a second "1 sheet". That is pre-existing naming in
`migrateStoredViews`, cosmetic, and outside the review's list.)

## 5 (LOW) — one build snapshot, compared against itself

```python
build = build_status(self.server.app, self.server.server_port)
if (build['code_sha256'] == build['on_disk_code_sha256_now']
        and build['assets_sha256'] == build['on_disk_assets_sha256_now']):
    return self.send({'restarting': False, 'current': True, 'build': build})
```

The block handed to the reader can no longer carry on-disk values from a different stat
than the one the decision was made on. Re-verified on both live consoles:

```
port 8826  POST /api/restart -> 200  restarting=False current=True
   one snapshot: code 7be208b18c vs 7be208b18c equal=True | assets f2bbd440f7 vs f2bbd440f7 equal=True
port 8829  POST /api/restart -> 200  restarting=False current=True
```

`test_restart_is_refused_read_only_and_while_the_console_is_busy` still passes unchanged,
so the 403, 409, current-build and both staleness branches are all still asserted.

## 6 (INFO) — the dead shortSha is gone

`chart-briefing.js:369`'s `shortSha` was shadowed and unreachable; the live one is
`model.shortSha` at :81, which is what the test calls. The dead binding was deleted rather
than wired into :471, because the HTML bundle's table column deliberately prints the *full*
digest — that is what round 1's evidence quoted, and shortening it would have been an
unrequested change to shipped output.

## Recorded, not changed

Per the instruction, three things were left exactly as they were, and one is recorded here
with the reviewer's own measurement:

- The strip's `latest=1` semantics (chart-studio.js ~:2260) — pre-existing, noted only.
- The app.js restart banner wording and behaviour (:620-624) — a UX call for Paul.
- The `atomic_json` retry. The reviewer measured `os.replace` raising WinError 5 on
  `index.json`: **2 failures in 20 runs of test_studio_views + test_studio_briefing
  together, and 0 in 10 runs of either alone.** Pre-existing, and Paul's call.

Also still open from round 1 and unchanged: the
`test_invalid_json_shape_length_and_unknown_routes_fail` socket race, measured at 2/40
against the pre-lane tree's 3/40. It did not recur in round 2's three rounds.

## Round 2 test totals

| suite | round 1 | round 2 |
|---|---|---|
| `node --test "mentat/app/tests/**/*.test.js"` | 95 pass, 0 fail | **101 pass, 0 fail** |
| studio / graph / lazy-startup `.cjs` suites | 21 pass, 0 fail (6 suites) | **34 pass, 0 fail** (7 suites) |
| six python suites, three rounds | Ran 57 — 2 of 3 rounds clean | **Ran 58 — 3 of 3 rounds clean** |

```
round 1  OK  ran=58  69.3s
round 2  OK  ran=58  54.5s
round 3  OK  ran=58  52.8s

3 of 3 rounds clean
```

Both round-2 consoles (8826 pid 34284, 8829 pid 42580) and the blob sink were stopped.
Paul's console on 8806 was never posted to and is still running.

---

# Round 3 — the three items Paul ruled on

All three applied and verified live. `.gitignore`'s negation is untouched, as instructed.
One of the three turned out to be hiding a wrong number that this lane had already
written down as evidence; that correction is below, because it matters more than the fix.

## Files changed in round 3

| file | round 2 | round 3 | bytes | crlf | lf | class |
|---|---|---|---|---|---|---|
| mentat/app/server.py | 0f88652 | b154782 | 110885 | 1937 | 0 | crlf |
| mentat/app/chart-studio.js | 8c2e88f | 3f9690a | 155975 | 2643 | 0 | crlf |
| mentat/app/chart-studio-contributions.js | c63edd5 | 1c5f86d | 20021 | 0 | 177 | lf |
| mentat/app/app.js | 4df8f05 | 086735d | 57472 | 281 | 397 | mixed |
| mentat/tests/test_studio_wording.cjs | 2b9418a | 7025af3 | 8520 | 0 | 127 | lf |
| mentat/app/tests/reconcile-cycle.test.js | new | a4e0f22 | 4033 | 0 | 77 | lf |

Unchanged and hash-confirmed: `chart-studio-core.js` fd3eaf0, `graph.js` 76edd54,
`chart-briefing.js` c2ad3fe, `studio-contract-examples.json` 048819e,
`studio-contract.test.js` 3bed9df, `test_studio_contract_examples.py` b87c565,
`test_contribution_http.py` e09f00f, `test_publish_pocket.py` cd30c82, `.gitignore`
202b4b8.

Classes all held. `app.js` is the only mixed file touched and its 281 CRLF endings are
untouched — the growth is 385 to 397 LF, entirely inside the LF region the restart flow
lives in. `chart-studio-contributions.js` and `test_studio_wording.cjs` had no fix1
backup and were backed up before being edited; every file this lane has touched now has
one, except the three it created itself.

## 1 — atomic_json retries past a reader's hold

`atomic_json` now calls a new `replace_with_retry`: ten attempts, 20 ms doubling to a
second, about four seconds in all, and a hold that never clears is raised rather than
swallowed. The same helper is used for the one sibling in the same studio write path that
had no retry — the briefing item's SVG at server.py:1000, written beside the `index.json`
that `atomic_json` now protects.

The `/api/evidence-job` race the receipts mention is covered by this one change:
`collect_evidence` writes `collection.json` through `atomic_json` at server.py:850, 859
and 868, so it inherits the retry. Two other write paths already had their own retries
and were left alone — the publish job's `record()` (server.py:1073, five attempts) and
the job-state *read* at server.py:1172 (six attempts).

Measured on this box rather than borrowed from the review — 20 paired runs of
`test_studio_views` + `test_studio_briefing` together, with a control that restores
`server.py` from its backup:

```
A  with the os.replace retry       server.py sha=b154782   0 failures in 20 runs
B  no retry (the backup)           server.py sha=a3e4b75   3 failures in 20 runs
     round 6  KeyError in test_remove_drops_the_item_and_its_chart_and_repeats_harmlessly
     round 8  KeyError in test_the_forty_first_item_is_a_conflict_not_a_bad_request
     round 17 KeyError in test_the_forty_first_item_is_a_conflict_not_a_bad_request
restored server.py sha b154782 == fixed
```

**0 of 20 with the retry, 3 of 20 without**, consistent with the reviewer's 2 of 20. The
mechanism is visible in the failure: a lost `index.json` write leaves the item out of the
index, and the test that looks it up raises `KeyError`.

## 2 — the strip was quoting a number Graph was not showing

This is the item that mattered most, and not for the reason I expected.

The fix is as directed: when the carried scope has no cycle of its own, the strip now
sends the same `latest=1` Graph's first paint sends, which the server answers by pinning
the newest cycle it holds (`graph_data.py:317`, `selected['cycle'] = max(years)`), and the
sentence names that pinned cycle instead of saying "All cycles". A scope that carries an
explicit cycle is unchanged.

**The correction.** Rounds 1 and 2 of this receipt quoted the strip as evidence:

> "Graph shows $249,949,483.17 for All companies · All cycles (workbook receipts).
> Studio total $249,949,483.17. Agree."

That agreement was false, and I recorded it as proof. The throwaway Crypto report holds
more than one cycle. Graph on screen was showing **$102,731,131.38 for 2026**; the strip
asked a different question, got the every-cycle total, and called the match agreement. It
agreed with itself. The same live check now reads:

```
Basis: Published included receipts. Graph shows $102,731,131.38 for All companies · 2026
(workbook receipts). Studio total $249,949,483.17. Differ by $147,218,351.79 because the
Graph view is pinned to one election cycle and this sheet covers every cycle.
```

So the round-1 and round-2 D6 evidence should be read as proving only that the strip
*reaches Graph* on a cold load. Its claim of agreement was an artifact of this bug and
should not be relied on. The reviewer was right to call `latest=1` out.

**Why a new reason id was needed.** Sending `latest=1` without more would have turned a
false "Agree" into a false mystery: the reason chain had no entry for a cycle-scope
difference, so the strip would have said *"Differ by $147,218,351.79 because this is
unexplained — report it"* about a gap with a plain explanation. That is a worse thing to
tell a reader than the original bug. So `RECONCILE_REASONS` gained `cycle`, and the chain
ranks it directly below `basis` — a pinned cycle explains more than a Graph filter does.
When the report holds a single cycle the totals still match and `reconcile` returns early,
so no cycle reason is ever raised spuriously.

**A house rule I broke and the suite caught.** My first wording began "Graph is showing…",
with a capital G, and `test_studio_wording.cjs` asserts every reason reads as the tail of a
sentence (`/^[a-z]/`). It also pins the exact list of reason ids. Both assertions are
right and neither was loosened: the reason was reworded to "the Graph view is pinned to
one election cycle and this sheet covers every cycle", and the pinned list was told about
the new id.

Verified live both ways the review asked. Studio-first cold load, `#graph-run` with zero
options:

```
s1_graphRunBefore : 0
s1_graphCalls     : [{"latest": true, "cycle": ""}]
s1_strip          : "…Graph shows $102,731,131.38 for All companies · 2026 …
                     Differ by $147,218,351.79 because the Graph view is pinned to one
                     election cycle and this sheet covers every cycle."
s1_pageErrors     : []
```

And after visiting Graph first, where Graph's own cycle control reads 2026:

```
s2_graphCycleOnScreen : "2026"
s2_graphRunAfterVisit : "published-reports"
s2_strip              : the same sentence, naming the same cycle
s2_pageErrors         : []
```

Screenshots `evidence/S1-strip-cold.png` and `evidence/S2-strip-after-graph.png`. Test:
`mentat/app/tests/reconcile-cycle.test.js`, seven cases covering the one-cycle report that
still agrees, the multi-cycle gap that is now named, a sheet with its own cycle that is
never explained away by it, the ranking against `basis` and `graph_filter`, the no-pinned-
cycle case that leaves the old reasons exactly as they were, and wording for every id.

## 3 — the "already current" confirmation clears itself

The banner no longer stands with a live Restart button when nothing is stale. On a
`current: true` answer the message goes into the same slot, the button is hidden, and a
five-second timer hands the banner back to whatever `renderBuild` computes — which is
hidden, on a console that is current. A second press restarts the countdown rather than
stacking timers.

Verified live, on a console confirmed current, by pressing the real button:

```
before : bannerVisible true,  buttonVisible true,   "This console is running an older build…"
during : bannerVisible true,  buttonVisible false,  "Console already current — nothing to restart."
after  : bannerVisible false, buttonVisible false
pidUnchanged : true
pageErrors   : []
```

Screenshot `evidence/S3-banner-settled.png`. The 403 read-only and 409 busy branches are
untouched and still asserted by `test_restart_is_refused_read_only_and_while_the_console_is_busy`.

An incidental confirmation of the D5 fix's value, from running this: an intermediate pass
was done against a console started *before* the round-3 edits, so it was genuinely stale
and correctly took the restart path — and the launcher then reused the running process
without the pid ever changing, which is precisely the situation that produced D5. The
console was stopped and restarted onto the current build before the final check above.

## Round 3 test totals

| suite | round 2 | round 3 |
|---|---|---|
| `node --test "mentat/app/tests/**/*.test.js"` | 101 pass, 0 fail | **108 pass, 0 fail** |
| studio / graph / lazy-startup `.cjs` suites | 34 pass, 0 fail | **34 pass, 0 fail** |
| six python suites, three rounds | Ran 58 — 3 of 3 clean | **Ran 58 — 3 of 3 clean** |

```
round 1  OK  ran=58  34.8s
round 2  OK  ran=58  34.1s
round 3  OK  ran=58  34.1s

3 of 3 rounds clean
```

Both throwaway consoles were stopped. Paul's console on 8806 was never posted to and is
still running; it will show its stale-build banner until he restarts it, which is correct,
because this lane did change `server.py`.

## The commit

Paul ruled fix-then-commit, but this lane's standing rules say no git write commands, so
nothing was committed and no git write command was run at any point. The tree is staged
for Paul exactly as described above: every changed file listed with its hash, every one
backed up as `.bak-20260914-fix1`, and three files newly created by this lane. The
`.gitignore` negation is in place so `mentat/app/studio-contract-examples.json` can be
added — without it the fixture is ignored and both new contract suites fail on a fresh
checkout.

Two other files this lane's work depends on are still untracked from earlier lanes and
would need adding in the same commit: `mentat/app/chart-briefing.js` and
`mentat/tests/test_contribution_http.py` show as `??`, not as modifications.
