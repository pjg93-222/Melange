# Build lane E-server receipt — saved views, briefing tray, vendor route, pocket publish

Date: 2026-09-14. Repository: `C:\Users\pgoff\Mentat`, branch `codex/mentat-crypto`.
Nothing was committed, staged or stashed. No console process of Paul's was touched.

---

## Files changed — before/after SHA-256, sizes, line-ending class

| File | after sha256 (16) | bytes | class | before sha256 (16) | bytes |
|---|---|---|---|---|---|
| `mentat/app/server.py` | `98168cdb6b645ab7` | 106856 | CRLF | `08374cdc2c35b04f` | 88038 |
| `mentat/app/README.md` | `901eb3c3dac89281` | 38313 | MIXED 397/188 | `2f1c5e6cc10c9535` | 35233 |
| `.gitignore` | `d23073b7822cbbce` | 1595 | MIXED 57/21 | `431c20e8ca3be9ab` | 1478 |
| `mentat/tests/test_contribution_http.py` | `66decc3ecf4a017b` | 22189 | LF | `34fc681bf9a90056` | 20042 |
| `mentat/tools/pocket/extract_pocket_data.py` | `5f034ed326039045` | 16811 | LF | `ef08d6351c8253e6` | 16305 |
| `mentat/tools/pocket/build_page.py` | `dd77514de8490e52` | 1988 | LF | `ebaf866c8f58a783` | 1298 |

New files (no prior version):

| File | sha256 (16) | bytes | class | provenance |
|---|---|---|---|---|
| `mentat/app/vendor/pptxgen.bundle.js` | `4fb9eac5cfefb213` | 460889 | LF | byte-exact copy of the scratchpad vendor bundle; **full sha256 matches the pin** |
| `mentat/app/vendor/LICENSE-pptxgenjs.md` | `4a19dc7413a9520e` | 1161 | LF | byte-exact copy |
| `mentat/tools/pocket/selfcheck.py` | `287af53a3e773213` | 13290 | LF | byte-exact copy of the audit packet |
| `mentat/tools/pocket/negative_control.py` | `2fe6f77c0f03d8ef` | 3871 | LF | byte-exact copy |
| `mentat/tools/pocket/render_harness.js` | `7af0fe37c2c6d161` | 14041 | LF | byte-exact copy |
| `mentat/tools/pocket/mentat-pocket.html` | `d1ac1829b4483439` | 166657 | CRLF | audit copy (`2ae6c772…`, 166579 B) plus 78 bytes of document wrappers |
| `mentat/tests/test_studio_views.py` | `1dd3fd5a2311c2b8` | 10439 | LF | new |
| `mentat/tests/test_studio_briefing.py` | `6c748cbfd7cd2907` | 10648 | LF | new |
| `mentat/tests/test_publish_pocket.py` | `865e1026d581f8b3` | 12232 | LF | new |

Full pinned bundle hash, asserted in the tests and verified against the bytes the console
actually served:
`4fb9eac5cfefb213e2d8743c2b7151025f31bfb3f834c73c12062916daa0f3f8`.

### Backups

`.bak-20260914-E` existed already (from a stalled first attempt) for `server.py`, `README.md`
and `.gitignore`, and each was **verified byte-identical to the live file before the first
edit**, so it is a true pre-edit copy; none was overwritten. `test_contribution_http.py` had no
`.bak-20260914-E`, so one was created before its first edit (`34fc681b…`, confirmed equal).
The new `mentat/tools/pocket` files were not given `.bak` files: their pristine reference is the
audit packet they were copied from, which is unchanged and hash-verified. The patch engine
refuses to run without a pristine reference for every file it edits.

### Line endings — measured, not assumed

The first pass of this lane used a `grep -c $'\r$'` census that reported every file as pure
CRLF. **That census was wrong** for all but `server.py`. The engine asserted the class instead
of trusting it and refused the first LF file, which is how the error surfaced. Re-measured with
Python (byte counts of `\r\n` versus lone `\n`), the truth is:

```
server.py                  1534 CRLF, 0 lone LF     pure CRLF
README.md                   356 CRLF, 188 lone LF   MIXED
.gitignore                   57 CRLF, 17 lone LF    MIXED (tail region LF)
test_contribution_http.py     0 CRLF, 327 lone LF   pure LF
extract_pocket_data.py        0 CRLF, 331 lone LF   pure LF
build_page.py                 0 CRLF, 33 lone LF    pure LF
mentat-pocket.html (audit) 1135 CRLF, 0 lone LF     pure CRLF
```

After the edits: `server.py` 1859 CRLF / 0 lone LF (still pure CRLF); `README.md` 397/188 —
all 544 original lines kept their own ending, the 188 lone-LF lines are untouched, 41 new lines
took CRLF (majority class), and the original file is a byte prefix of the new one; `.gitignore`
57/21 — 4 appended lines took LF, matching its tail region; the LF files stayed pure LF.
`mentat-pocket.html` is CRLF because it is a byte copy of a CRLF source — the "new files LF"
rule was applied to files this lane authored, and byte-identity won for the copy. New authored
files (three test suites) are LF, matching their pure-LF sibling directory.

---

## Edit log (replayable) — `scratchpad\lanes\Eserver\`

| Step | File(s) | What |
|---|---|---|
| `apply-e.js` | — | exact-anchor patch engine; measures the EOL class, asserts it, refuses lone CR, LCS-pairs mixed files against the pristine reference |
| `install.js` | — | whole-file installer for files whose bodies carry backslash escapes a JS patch string would have to double |
| `step1-template.js` | `tools/pocket/mentat-pocket.html` | wraps the audit fragment in `<!doctype>/<html>/<head>/<body>`; asserts that removing the three inserted runs restores the source byte-for-byte |
| `step2-views.js` | `server.py` | `list_views/get_view/save_view/delete_view`, GET+POST routes, read-only 403, 512 KB body ceiling |
| `step3-briefing.js` | `server.py` | `Conflict` exception (→409), tray methods, GET+POST routes, read-only 403 |
| `step4-assets.js` | `server.py` | 3 allow-list entries + 404 for an allow-listed file not on disk |
| `step5-tools.js` | `extract_pocket_data.py` | `--out-dir` (`--datasets` already existed) |
| `manifest-buildpage.js` | `build_page.py` | whole-file install adding `--data` / `--out` |
| `step6-pocket.js` | `server.py` | `Console.port`, `publish_pocket`, `publication`, routes, `main()` port wiring |
| `step7-gitignore.js` | `.gitignore` | two tracking exceptions |
| `step8-pocket-hardening.js` | `server.py` | two races closed (below) |
| `step9-http-tests.js` | `test_contribution_http.py` | vendor-hash test + allow-list test |
| `manifest-tests.js` | 3 new suites | whole-file install, LF |
| `step10-publication-read.js` | `server.py` | publication read retries the swap it races (below) |
| `step11-readme.js` | `README.md` | four documentation paragraphs |

---

## Per-endpoint observed responses

Exercised against **this lane's own consoles**: 8821 writable, 8820 read-only, both on throwaway
data roots under the scratchpad, `MENTAT_REPORT_DIRECTORY` pointing at a scratchpad folder
holding one **copied** workbook (`Crypto Industry Spending Overview.xlsx`). Paul's live report
folder was read once, to make that copy, and never written. Full transcript:
`scratchpad\lanes\Eserver\run\transcript.md`.

### 1. Saved views (8821)

```
GET  /api/studio/views                  200 {"views": []}
POST /api/studio/views                  200 {"id":"3e6d9476f4384bd9bf84982120a339e1","saved_at":1789399132.8144267}
GET  /api/studio/views                  200 {"views":[{id, name:"Ride B", saved_at, sourceKey:"Crypto|2025-2026",
                                              source:{...}, sheet_count:2}]}     (no "sheets" key)
GET  /api/studio/views?id=<32hex>       200 {"view":{id,name,saved_at,sourceKey,source,sheets:[2],active:1}}
GET  /api/studio/views?id=ffff…(32)     404 {"error":"That saved view is not on this console."}
GET  /api/studio/views?id=not-hex       400 {"error":"That is not a saved view identifier."}
POST /api/studio/views  name 81 chars   400 {"error":"Name the view: between 1 and 80 characters."}
POST /api/studio/views  25 sheets       400 {"error":"Save between 1 and 24 sheets in one view."}
POST /api/studio/views  600 077 B body  400 {"error":"That view is too large to save. Remove a sheet and save again."}
POST /api/studio/views/delete           200 {"deleted": true}
POST /api/studio/views/delete (repeat)  200 {"deleted": true}
GET  /api/studio/views                  200 {"views": []}
```

### 2. Briefing tray (8821)

```
GET  /api/studio/briefing               200 {"items": []}
POST /api/studio/briefing/add           200 {"id":"9d3bc1f7aabb4c01a4565ae8dcd8a437","added_at":…}
GET  /api/studio/briefing               200 items carry exactly id,title,scope,note,basis,sheetId,
                                            sheetName,source,provenance,width,height,added_at,origin
GET  /api/studio/briefing/item?id=…     200 text/plain; charset=utf-8  b'<svg width="960" …</svg>'
GET  /api/studio/briefing/item?id=ffff… 404 {"error":"That briefing item is not on this console."}
GET  /api/studio/briefing/item?id=nope  400 {"error":"That is not a briefing item identifier."}
POST /api/studio/briefing/add  <div>    400 {"error":"A briefing item carries the chart it was made from."}
POST /api/studio/briefing/add  >6 MB    400 {"error":"Narrow the view before adding it: this chart is over 6 MB."}
POST /api/studio/briefing/order  perm.  200 {"ok": true}
POST /api/studio/briefing/order  short  400 {"error":"The briefing order must list every item in the tray exactly once."}
POST /api/studio/briefing/add  41st     409 {"error":"The briefing holds 40 items. Remove one before adding another."}
POST /api/studio/briefing/remove        200 {"removed": true}
POST /api/studio/briefing/remove (rpt)  200 {"removed": true}
```

### 3. Vendor route (8821)

```
GET /vendor/pptxgen.bundle.js   200 text/javascript   460 889 bytes served
    sha256 of the served bytes  4fb9eac5cfefb213e2d8743c2b7151025f31bfb3f834c73c12062916daa0f3f8
    pinned value                4fb9eac5cfefb213e2d8743c2b7151025f31bfb3f834c73c12062916daa0f3f8   MATCH
    Content-Security-Policy: default-src 'self'; style-src 'self'; script-src 'self';
                             img-src 'self' blob:; frame-ancestors 'none'
    X-Content-Type-Options: nosniff
GET /chart-briefing.js          200 text/javascript   (the parallel client lane landed it mid-run)
GET /chart-briefing.css         200 text/css          (same)
```

### 4. Phone snapshot publish (8821) — **a real publish, not a stub**

```
GET  /api/contributions/catalog        200  datasets: [{"id":"Crypto","available":true}]
POST /api/publish/pocket  datasets:[]  400  {"error":"Choose at least one dataset to publish."}
POST /api/publish/pocket  ["Telecom"]  400  {"error":"Not in this report: Telecom."}
GET  /api/publish/pocket?id=publish-f…  404 {"error":"That publication is not on this console."}
GET  /api/publish/pocket?id=nope        400 {"error":"That is not a phone snapshot publication."}
POST /api/publish/pocket  ["Crypto"]   200  {"job":{"id":"publish-8ecd205f1580466aa78eafbe6089cf25",
                                             "status":"queued","message":"Preparing the snapshot.",
                                             "datasets":["Crypto"],"output_path":"…\pocket\mentat-pocket.html",
                                             "console_pid":1396,"started_at":…,"finished_at":null}}
POST /api/publish/pocket  (while running) 409 {"error":"A phone snapshot is already being published. …"}
GET  /api/publish/pocket?id=…          200  final: status "done", finished 22.1 s after start,
                                             message "Snapshot published to …\pocket\mentat-pocket.html"
```

Artifacts written to the throwaway report folder's `pocket\`:
`mentat-pocket.html` 57 956 B (full document: `<!doctype html>` … `</html>`),
`pocket-data.json` 10 904 B, `pocket-integrity.json` 3 163 B (25 requests, 11 polls, 21.7 s,
provenance `workbook_sha256 88ea2284…`). The repository template
`mentat/tools/pocket/mentat-pocket.html` is **unchanged** after the publish (`d1ac1829…`).

`build_page.py` idempotence: rebuilt over the same output twice more — byte-identical all three
times (`cdb017ae1159…`), markers intact.

### 5. Read-only console (8820)

```
POST /api/studio/views          403 {"error":"Saved views are read-only in this preview console; save from the original console."}
POST /api/studio/views/delete   403 {"error":"Saved views are read-only in this preview console; save from the original console."}
POST /api/studio/briefing/add   403 {"error":"The briefing is read-only in this preview console."}
POST /api/studio/briefing/remove 403 {"error":"The briefing is read-only in this preview console."}
POST /api/studio/briefing/order 403 {"error":"The briefing is read-only in this preview console."}
POST /api/publish/pocket        403 {"error":"This preview is read-only while the original console manages collection."}
GET  /api/studio/views          200 {"views": []}
GET  /api/studio/briefing       200 {"items": []}
GET  /vendor/pptxgen.bundle.js  200 text/javascript
```

---

## Two defects found and fixed inside this lane

**1. The publish reply shared a live dict with its worker thread.** `publish_pocket` returned the
same `job` dict the worker mutates, and the worker adds a `pid` key the moment the first child
starts. `json.dumps` iterating a dict that gains a key raises `RuntimeError`, so the POST could
fail intermittently *after* the job had already been started — the caller would see an error for
work that was running. Fixed: the reply and every state write serialise a snapshot (`dict(job)`).

**2. Windows refuses both sides of a read/`os.replace` collision, and it is not rare.** The
publish job-state file is rewritten by the worker while a client polls it. Measured on this
machine — one thread replacing a JSON file, one thread reading it, three seconds:

```
reads  22 582   read failures 2 010  (8.9%)  all PermissionError
writes  1 412   write failures 1 789         os.replace refused while the reader held the file
```

`read_json` turns the reader's `PermissionError` into `{}`, and `publication()` was reporting
that as **404 for a job that was running normally**. The full suite reproduced it; the test alone
did not. Fixed on both sides: state writes retry briefly (`record()`), and the reader retries a
state file that will not read — while a publication that never existed still answers on the first
pass, because it has no directory at all.

This measurement also names a **pre-existing exposure outside this lane's file set**:
`atomic_json` has no retry, and `/api/evidence-job` reads `collection.json` while
`collect_evidence`'s thread rewrites it — the same collision, with a lost write meaning a lost
state update. Not touched here: `atomic_json` is shared by upload, evidence, keys and run
manifests, and widening its behaviour is a larger blast radius than this lane should take.
**Flagged for Paul.**

---

## Checks run

| Check | Result |
|---|---|
| `python -m py_compile` on 9 touched `.py` files | OK; `.pyc` deleted (`tools/pocket/__pycache__` removed entirely) |
| `node --check mentat/tools/pocket/render_harness.js` | OK |
| `python -m unittest mentat/tests/test_studio_views.py` | **8 tests, OK** × 3 runs |
| `python -m unittest mentat/tests/test_studio_briefing.py` | **7 tests, OK** × 3 runs |
| `python -m unittest mentat/tests/test_publish_pocket.py` | **9 tests, OK** × 3 runs (plus 3 earlier runs, 6 total) |
| `python -m unittest mentat/tests/test_contribution_http.py` | **22 tests, OK** × 3 runs (was 20; +2 from this lane) |
| `python -m unittest mentat/tests/test_desktop_launcher.py` | **4 tests, OK** × 3 runs (28.7 s / 43.1 s / 36.6 s) |
| Live exercise, every new endpoint, 8820 + 8821 | every response recorded above |
| Real pocket publish, `--datasets Crypto` | reached **done**, 57 956-byte page, 22.1 s |
| `build_page.py` idempotence | byte-identical across 3 builds |
| `git check-ignore -v` before/after | `mentat-pocket.html` was ignored by `.gitignore:20:*.html`, now matched by `!mentat/tools/pocket/*.html`; bundle now matched by `!mentat/app/vendor/*.js` |
| Vendor bundle integrity | copy byte-exact; **served bytes** hash to the pinned value |

**Total: 50 tests per round, 3 rounds, zero failures.**

Running processes checked with `Get-CimInstance` before and after and **left alone**: pid 17756
`staffer_live_server.py --port 8841`, pid 66760 (later 57104) `mentat\app\server.py --port 8806`,
pid 86248 `console_browser_fixture.py` (the parallel client lane's). This lane's own two consoles
(pids 50944 / 1396) were started with `Start-Process` and stopped by those PIDs; both confirmed
gone afterwards.

---

## Skipped, and why

- **`chart-export.js`, `chart-studio.js`, `index.html`, `chart-studio.css`, `graph.js`,
  `charts.js`, `chart-briefing.js/.css`, the `.cjs` browser tests** — the parallel client lane's
  files. Not read for edit, not touched. The `<script>`/`<link>` tags for the three new routes
  are the client lane's to add; only the server allow-list entries are here.
- **`git add` / `commit` / `stash`** — barred by the lane rules. Nothing is staged.
- **`Console.busy()` was deliberately not edited.** A pocket job makes it true through the
  existing `self.jobs` check, because pocket job ids carry a `publish-` prefix and are added to
  that set. Editing `busy()` would have broken
  `test_contribution_http.test_busy_reports_console_owned_work_only`, which calls it unbound
  against a `SimpleNamespace` carrying only `preparing`, `jobs` and `processes`.

---

## Limits and open items for Paul / the orchestrator

1. **The moved `selfcheck.py` cannot run where it now lives.** It resolves every input relative
   to its own folder and needs `pocket-data.json`, `icon-180.png` and `manifest.webmanifest`
   — none of which are in this lane's instructed file set (which named exactly five scripts plus
   the page template). Measured: in `mentat/tools/pocket` it dies with
   `FileNotFoundError: …\pocket\pocket-data.json`; the same file in the audit packet, where its
   inputs live, still prints `ALL CHECKS PASSED`. So the script is intact but unusable in place.
2. **The published page has two broken asset references.** It carries
   `<link rel="apple-touch-icon" href="icon-180.png">` and
   `<link rel="manifest" href="manifest.webmanifest">`, and the publisher writes neither into the
   report `pocket\` folder. The page renders, but "Add to Home Screen" on a phone gets no icon
   and no manifest — which is ride step 31's whole point. Fixing it means either copying
   `icon-180.png` + `manifest.webmanifest` into `mentat/tools/pocket` and having the publisher
   emit them, or giving `selfcheck.py` `--page`/`--data` flags — both outside the contract I was
   given. **Needs a ruling.**
3. **Two response shapes were under-specified and I chose deliberately.** `POST
   /api/publish/pocket` returns `{"job": {...}}` (reading `-> {job}` as a key list, like
   `{deleted:true}`), while `GET /api/publish/pocket?id=` returns the state object itself
   (reading `-> that state` literally). If the client lane expects symmetry, say which.
4. **Delete/remove are idempotent.** The contract fixed the success shape but not the
   unknown-id case. `POST /api/studio/views/delete` and `/briefing/remove` return
   `{"deleted": true}` / `{"removed": true}` for an id that is already gone (the postcondition
   holds, and a double-click in the UI is not an error); a *malformed* id is still 400.
5. **`svg` must start literally with `<svg`** — no leading whitespace tolerated, per the
   contract's wording. A client that emits `\n<svg …` will get a 400.
6. **A 6 MB SVG can hit the generic 7 MB body cap first.** The per-item limit is 6 MiB measured
   on the decoded string; JSON escaping of a quote-heavy SVG can push the request body past
   `7_000_000`, which answers 400 with "Request is empty or too large." rather than the "over
   6 MB" message. Both are 400s; the wording differs.
7. **`!mentat/app/vendor/*.js` is a no-op today.** Measured before the edit: the bundle was
   already `NOT IGNORED` — no pattern hides `.js`. It was added as instructed and is the line
   that keeps the bundle tracked if a `*.js` rule ever lands. The `.html` exception *is*
   load-bearing.
8. **Consoles need a restart.** Three new entries in `STATIC_ASSETS` change `ASSET_TREE_SHA256`,
   and `server.py` changed, so any console still running old code will report itself out of date.
9. **A flake this lane can see but did not cause.** `test_contribution_http`'s health assertion
   `on_disk_assets_sha256_now == assets_sha256` compares a hash taken at import with one taken at
   request time. While a parallel lane is writing `chart-briefing.js`/`.css`, those two can
   differ and the test will fail. It passed 3/3 here; the exposure is real while two lanes edit
   `mentat/app` at once.
10. **Not verified by this lane:** that the briefing drawer, Save/Open view menu entries and the
    PowerPoint export work in a browser — those are the client lane's surfaces. The server side
    is proven by the transcript above; the end-to-end ride steps 27–31 are not.

---

# E-server addendum — coordinator ruling on items 8 and 9

Date: 2026-09-14, after the receipt above. Items 8 (selfcheck unrunnable in its new home) and 9
(published page missing its icon and manifest) are closed inside this lane's file set. Item 7
(`atomic_json` has no retry) stays untouched, as ruled — still flagged for Paul.

## Files changed in the addendum

| File | after sha256 (16) | bytes | class | before sha256 (16) | bytes |
|---|---|---|---|---|---|
| `mentat/app/server.py` | `a3e4b75a2fd8e327` | 108980 | CRLF | `98168cdb6b645ab7` | 106856 |
| `mentat/tools/pocket/selfcheck.py` | `269c5f2ceb416bf7` | 15318 | LF | `287af53a3e773213` | 13290 |
| `mentat/tests/test_publish_pocket.py` | `5955bb1d43b1ad53` | 15681 | LF | `865e1026d581f8b3` | 12232 |

New files, byte-exact copies from the audit packet:

| File | sha256 (16) | bytes | equals audit copy |
|---|---|---|---|
| `mentat/tools/pocket/icon-180.png` | `e1bfad0de8a5f322` | 2030 | yes |
| `mentat/tools/pocket/manifest.webmanifest` | `387be122ea9d2feb` | 276 | yes |

Backups `.bak-20260914-E2` were created for `server.py` and `selfcheck.py` before their first
addendum edit; neither pre-existed, neither `.bak-20260914-E` was touched. Line-ending classes
held: `server.py` 1903 CRLF / 0 lone LF, `selfcheck.py` 302 lone LF / 0 CRLF.

**`.gitignore` was NOT changed — no change was needed.** Measured with `git check-ignore -v`
both before and after the copies: `mentat/tools/pocket/icon-180.png` and
`…/manifest.webmanifest` are `NOT IGNORED`. `*.json` does not match `.webmanifest`, and no
pattern matches `.png`. Both show as `??` in `git status --untracked-files=all`, i.e. trackable.

## Steps (replayable)

| Step | What |
|---|---|
| `step12-selfcheck-dir.js` | `selfcheck.py` gains `--dir` / `--data`; `main()` replaced as a span with the body read from `files/selfcheck-main.py` |
| `step13-publish-assets.js` | publish copies the two assets, records `output_files`, runs the self-check as an advisory post-check |
| `step14-selfcheck-assertions.js` | two inherited assertions corrected (below) |
| `apply-e.js` | extended: per-spec backup `suffix`, span edits (`from`/`to`), and `replaceFile` |

`--dir` defaults to the directory of the `pocket-data.json` being checked, which itself defaults
to the script's own folder, so `python selfcheck.py` with no arguments behaves exactly as it did
in the audit packet — confirmed: run against the audit packet it still prints `ALL CHECKS PASSED`.
The size table splits deliverables (from `--dir`) from `extract_pocket_data.py` (source, from the
script's folder), so it reads correctly in both modes.

## The first re-publish failed its own check — and the checker was wrong, not the page

The first run after wiring the post-check came back `status done, selfcheck fail,
6 CHECK(S) FAILED`. All six were assumptions inherited from the audit packet:

```
FAIL  no <!DOCTYPE> (the publisher wraps the file)
FAIL  no <html> wrapper
FAIL  no <head> wrapper
FAIL  no <body> wrapper
FAIL  8 industries: Crypto          (twice: the inlined copy and pocket-data.json)
```

In the audit packet the page was a *fragment* and an artifact publisher supplied the document
around it, so the checker asserted the wrappers were **absent**. This lane's contract required
the moved template to become a full document, so that assertion is now exactly inverted. And a
`--datasets Crypto` publish has one industry by design, so a hardcoded 8 is wrong for any scoped
publish. `step14` corrects both — wrappers must now be present and complete, and the industry
count becomes a non-empty check that still prints what was published. **Every other assertion is
untouched**, including the reconciliation that recomputes totals from the raw result sets.

### Negative control — the corrected checker still fails when it should

Adding **one cent** to a single company/cycle total in a copy of the published snapshot:

```
before: [0, 79993577, 762]   after: [0, 79993578, 762]

FAIL  Crypto 2021-22: company sum 175627335 cents / 1056 records == industry 175627334 / 1056
FAIL  Crypto / Coinbase / 2021-22: recipient_category sums to 79993577 / 762, cycle total 79993578 / 762
FAIL  Crypto / Coinbase / 2021-22: party sums to 79993577 / 762, cycle total 79993578 / 762
3 CHECK(S) FAILED
```

Three independent reconciliations caught it, so the pass below is a real pass.

## Re-published Crypto snapshot on the throwaway 8821 setup

```
POST /api/publish/pocket ["Crypto"]  -> 200  publish-5ea5df1ff1304e07bbfad32ea9896077
status            : done
selfcheck         : pass
selfcheck_message : ALL CHECKS PASSED
elapsed           : 1.8 s          (21.7 s on the first publish; the contribution query
                                    cache is warm now, the extractor still ran)
output_files      :
  mentat-pocket.html          57,956 bytes
  pocket-data.json            10,904 bytes
  pocket-integrity.json        3,161 bytes
  icon-180.png                 2,030 bytes
  manifest.webmanifest           276 bytes

icon-180.png         byte-identical to mentat/tools/pocket:  True
manifest.webmanifest byte-identical to mentat/tools/pocket:  True
```

Full self-check output over that folder: `ALL CHECKS PASSED`, including
`starts with <!DOCTYPE html>`, all three wrapper checks, `1 industry: Crypto`, and the
three-cycle reconciliation (`company sum 175627334 == industry 175627334`, and the 2023-24 and
2025-26 cycles likewise). Transcript: `scratchpad\lanes\Eserver\run\transcript-addendum.md`.

Note on the count: the ruling said "the four output files"; the publish actually lands **five** —
the page, its data, the integrity block, the icon and the manifest. All five are listed in
`output_files`, and the two assets are verified byte-identical to their sources.

## Advisory, not fatal — as ruled

`done`/`failed` still depend only on whether the children exited cleanly and the page exists.
The self-check verdict is recorded beside them. Covered by two new tests:
`test_a_failed_self_check_is_recorded_without_failing_the_publish` (exit 1 →
`status done, selfcheck fail, selfcheck_message '2 CHECK(S) FAILED'`, page still on disk) and
`test_a_publish_that_never_built_a_page_runs_no_self_check` (`selfcheck` stays `None`, no check
process started, and `output_files` honestly reports the two assets that did land).

## Checks re-run

| Check | Result |
|---|---|
| `python -m py_compile` (server, selfcheck, tests) | OK; `.pyc` deleted |
| `test_studio_views` | **8 tests, OK** × 3 |
| `test_studio_briefing` | **7 tests, OK** × 3 |
| `test_publish_pocket` | **12 tests, OK** × 3 (was 9; +3 this addendum) |
| `test_contribution_http` | **22 tests, OK** × 3 |
| `test_desktop_launcher` | **4 tests, OK** (28.7 s) |
| Real Crypto publish, end to end | `done` + `selfcheck pass`, 5 files |
| Self-check negative control | 3 failures from a one-cent tamper |
| `selfcheck.py` with no arguments, audit packet | `ALL CHECKS PASSED` (backward compatible) |
| `git check-ignore -v` on both new assets | `NOT IGNORED` — no `.gitignore` change made |

**Total: 53 tests per round (was 50), 3 rounds, zero failures.**

Lane consoles for the addendum: pids 67256 (8820) and 73388 (8821), started with
`Start-Process`, stopped by those PIDs, both confirmed gone. Remaining python processes are
pid 17756 (`staffer_live_server`) and pid 57104 (Paul's Mentat console) — untouched.
