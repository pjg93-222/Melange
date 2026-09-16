# S3 proposed patches — evidence-csv on-disk store (2026-09-16)

Three PROPOSED patches. Nothing here has been applied to any file in the
working tree; each patch was produced by copying the target file into this
session's scratchpad, editing the copy, and diffing original vs. copy with
`git diff --no-index` (headers rewritten to `a/<repo-relative>` /
`b/<repo-relative>` so `git apply --check` accepts them from the repo root).
Paul applies these with `git apply <patch>` (or by hand) after review; S3 did
not touch the target files in place, per the file-ownership rule for files S3
does not own.

Context for all three: S3 replaced the in-memory, per-process CSV import
(`Console.csv_imports`) with an on-disk store under
`<console.root>/evidence-csv/<id>/`, so an import now survives a console
restart and is shared across every console on the same data root. The size
limit moved from a 5 MB literal duplicated in client and server to a single
server constant `evidence_csv.MAX_BYTES = 50_000_000`, published to the client
as `GET /api/evidence-csv` → `limits.max_bytes` / `limits.max_bytes_message`
(`'Choose a CSV no larger than 50 MB.'`). The client pre-flights against that
published limit and shows `'<name> (<MB, 1 decimal> MB): <max_bytes_message>'`.

## 1. `S3_proposed_test_evidence_csv_pin.patch` — `mentat/tests/test_evidence_csv.py`

**Why:** `test_csv_http_is_authenticated_memory_only_and_available_in_read_only_mode`
pinned the exact defect S3 removed. It asserted `list(root.rglob('*')) ==
[console.root]` ("no files are ever written for an import") and
`restarted.evidence_csv_view()['sources'] == []` ("a restart forgets every
import"). Both are now false by design: imports are written to disk precisely
so they survive a restart. Left as-is, this test would fail against the new,
intended behavior and give Paul a false "S3 broke something" signal.

**What:**
- Renamed the test to `test_csv_http_is_authenticated_and_available_in_read_only_mode`
  (dropped `memory_only`, which no longer describes the behavior).
- Replaced the "no files written" assertion with a check that the on-disk
  record exists: `(console.root / 'evidence-csv' / source['id'] /
  'import.json').is_file()`. `source['id']` is the id the same test already
  captured from the POST response a few lines above; the path matches
  `Store.record_path` in `mentat/app/evidence_csv.py` exactly
  (`STORE_DIRECTORY = 'evidence-csv'`, `directory(id)/'import.json'`).
- Replaced the "a restart forgets" assertion with "a restart remembers":
  `restarted.evidence_csv_view()['sources'][0]['id'] == source['id']`.
- Every other assertion in the test (403 without a token, GET listing after
  POST, paginated GET view, row/total values) is untouched.

**Proof (test tallies):**
- Baseline, unpatched, `cd C:\Users\pgoff\Mentat\mentat && python -m unittest
  tests.test_evidence_csv -v`: **9 passed, 1 failed** — the one failure is
  exactly `test_csv_http_is_authenticated_memory_only_and_available_in_read_only_mode`,
  failing at the `list(root.rglob('*')) == [console.root]` line (the store
  directory now exists on disk, so the list has 6 extra entries). This is the
  expected, single, targeted failure.
- Patched, via a temporary untracked copy `mentat/tests/_s3_proposed_test_evidence_csv.py`
  (the scratchpad-edited file copied in, run, then deleted — never added or
  committed): `python -m unittest tests._s3_proposed_test_evidence_csv -v`:
  **10 passed, 0 failed**.
- `git -C C:\Users\pgoff\Mentat apply --check
  audits\mentat_failings_20260915\patches\S3_proposed_test_evidence_csv_pin.patch`:
  exit code **0**.

**Paul applies this** (it is not applied): `git apply
audits/mentat_failings_20260915/patches/S3_proposed_test_evidence_csv_pin.patch`
from the repo root, then re-run the suite to confirm 10/10.

## 2. `S3_proposed_test_console_browser_limit.patch` — `mentat/tests/test_console_browser.cjs`

**Why:** Lines 86-87 feed a 5,000,001-byte file and assert the status text
matches `/no larger than 5 MB/` — the old client-side literal. Before touching
it, the fixture had to be checked: does the browser test's `page.route` mock
intercept `GET /api/evidence-csv` (in which case the new client's `limits`
object would never arrive from a mock and the pre-flight would be skipped,
silently uploading the oversize buffer to the mock and making the assertion's
premise wrong), or does it hit a real server (in which case the new 50 MB
limit is genuinely enforced end-to-end and only the numbers need updating)?

Read the whole test file and `mentat/tests/console_browser_fixture.py`: the
fixture (`console_browser_fixture.py:84-88`) starts a **real**
`app.ThreadingHTTPServer` with `app.Handler` in front of a `FixtureConsole`
that subclasses `app.Console` and does not override `evidence_store` /
`evidence_csv_view` / `import_evidence_csv`. The test file only mocks three
routes with `page.route`: `**/api/evidence?*`, `**/api/evidence`, and
`**/api/cross-reference` (lines ~41-43). `/api/evidence-csv` is never among
them, so the client's `GET /api/evidence-csv` reaches the real fixture server,
which answers with the real `evidence_csv.limits()` (`max_bytes: 50_000_000`,
`max_bytes_message: 'Choose a CSV no larger than 50 MB.'`). The client's
pre-flight in `evidence-csv.js:135-138` therefore genuinely runs against the
real 50 MB ceiling in this test.

**Choice made:** because the fixture proxies to a real server (second option
in the brief), the minimal change is exactly that: bump the oversize buffer
from 5,000,001 to 50,000,001 bytes and update the expected message to the new
one, keeping the test's original intent (client refuses an oversize file
before uploading it) intact. No route mocking needed or added.

**What:**
```
- await page.locator('#evidence-csv-file').setInputFiles({name:'too-large.csv',mimeType:'text/csv',buffer:Buffer.alloc(5000001,65)});
- assert.match(await page.locator('#evidence-csv-status').innerText(),/no larger than 5 MB/);
+ await page.locator('#evidence-csv-file').setInputFiles({name:'too-large.csv',mimeType:'text/csv',buffer:Buffer.alloc(50000001,65)});
+ assert.match(await page.locator('#evidence-csv-status').innerText(),/too-large\.csv \(50\.0 MB\): Choose a CSV no larger than 50 MB\./);
```
50,000,001 / 1e6 = 50.000001 → the client's `megabytes()` helper (`.toFixed(1)`)
renders `50.0`, so the expected string is `too-large.csv (50.0 MB): Choose a
CSV no larger than 50 MB.`, matching `evidence-csv.js:135-136`'s
`` `${file.name} (${megabytes(file.size)} MB): ${limits.max_bytes_message}` ``
and `evidence_csv.py`'s `bytes_message()`.

**Proof:** `git -C C:\Users\pgoff\Mentat apply --check
audits\mentat_failings_20260915\patches\S3_proposed_test_console_browser_limit.patch`:
exit code **0**. Note this file is tracked and already modified by another,
unrelated lane in the working tree (`git status` shows it `M`); the patch was
diffed against that live working-tree content, not HEAD, which is why the
apply-check above (against the same working tree) is the correct proof.
Running the Playwright browser test itself was not required and was not run.

**Paul applies this** after resolving with whatever else that other lane is
doing to this file (both patches, if independent hunks, may need a manual
merge — check before applying).

## 3. `S3_proposed_index_html_limit_text.patch` — `mentat/app/index.html`

**Why:** Line 343 (task brief said "~342"; the enclosing `<div>` is 342, the
text itself is on 343 — re-grepped, not assumed) holds a static placeholder
inside `#evidence-csv-status`: `"FEC or Mentat CSV with a committee ID column
· up to 5 MB."` That number is stale twice over: it predates S3 (the limit was
already moving) and, more basically, hard-coding it here means any future
change to `evidence_csv.MAX_BYTES` requires remembering to also edit this HTML
string — exactly the duplication S3's server-published `limits` was meant to
end. The real, current limit is stated dynamically by
`evidence-csv.js:135-136` the moment a file is chosen, using the server's
`limits.max_bytes_message`, so the static line doesn't need to (and shouldn't)
carry its own number.

(The unrelated `up to 5 MB` at line 39, for the roster-file `<input id="file">`
upload, is a different feature governed by a different limit, not by
`evidence_csv`, and was left untouched — it is out of S3's scope.)

**What:**
```
- <p id="evidence-csv-status" role="status">FEC or Mentat CSV with a committee ID column · up to 5 MB.</p>
+ <p id="evidence-csv-status" role="status">FEC or Mentat CSV with a committee ID column · the console states the size limit when you choose a file.</p>
```
Kept the existing `·`-separated clause style used throughout this line and the
surrounding panel copy; no number appears, so the sentence never goes stale
again.

**Proof:** `git -C C:\Users\pgoff\Mentat apply --check
audits\mentat_failings_20260915\patches\S3_proposed_index_html_limit_text.patch`:
exit code **0**. `index.html` was clean (unmodified) in the working tree before
and remains so — the patch only exists on disk under `patches/`.

**Paul applies this** with a plain `git apply
audits/mentat_failings_20260915/patches/S3_proposed_index_html_limit_text.patch`
from the repo root; no test depends on this exact wording (the browser test
matches `#evidence-csv-status` only after a file is chosen, never the resting
placeholder text).
