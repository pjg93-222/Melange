# Cross-reference dwarf lane - RECEIPT

Repo `C:\Users\pgoff\Mentat`, branch `codex/mentat-crypto`.
`git log -1 --format=%H` at session start: **3fdfeae8fed6140f705889fbd3a407645050a047**
`git log -1 --format=%H` at copy-back:      **3fdfeae8fed6140f705889fbd3a407645050a047** (unchanged; nothing committed by any lane during this session)

Scope cut mid-flight by the coordinator: **step 7 (port-8833 live check) and step 8 (README) were dropped**.
`mentat/README.md` was therefore **never written to** - it stays dirty from the other lane only.
`mentat/app/index.html` was never touched.

## Files changed

### Owned by this lane
| File | sha256 before | sha256 after | backup |
|---|---|---|---|
| `C:\Users\pgoff\Mentat\mentat\tools\cross_reference_digest.py` | *(new file)* | `e9158388a737b1cd735cf471b05011000c1d7829ab5208290a66af0b72a617f8` | n/a |
| `C:\Users\pgoff\Mentat\mentat\tools\run_cross_reference.py` | `cb9d0c198147aa15377582c34382a51794cf16cef23d593e5bf4875945d06964` | `2889aa29ce866eac2ac5784072f088e1ae32e47ea16a99696ca733f37a2b7ef4` | `run_cross_reference.py.bak-20260917-xref` |
| `C:\Users\pgoff\Mentat\mentat\app\cross_reference_data.py` | `b747744d211467a95555dce811cb27a249ddeae3de12509dddb9d0209c89f780` | `628bfe6815ec9bb9f37a8e7c6dbe1a19e05ddce9852eafaab072d6cfec196048` | `cross_reference_data.py.bak-20260917-xref` |
| `C:\Users\pgoff\Mentat\mentat\app\cross-reference.js` | `4f4471a0541452c99a601a45147e4bc83cdaec926386c41db38419ec084b6249` | `6fa77ea95f9ce60f233149375104a4cff8c9f6c6f052033a61c255aede0c4c00` | `cross-reference.js.bak-20260917-xref` |
| `C:\Users\pgoff\Mentat\mentat\tests\test_cross_reference_data.py` | `b4f1973a2f52b7e863eba9005ea5c2715f4c05b282074e68e6b7c016f25c1ad2` | `73bf06d00cf01b33f4d4789da3aafa68b18b2abe42f9c1f226de832b64e2901c` | `test_cross_reference_data.py.bak-20260917-xref` |
| `C:\Users\pgoff\Mentat\mentat\tests\test_cross_reference_digest.py` | *(new file)* | `d295a8fc57236050ece2008184de77c1f502913b834da3ded1f9267bac694ebe` | n/a |
| `C:\Users\pgoff\Mentat\mentat\tests\test_cross_reference_view.cjs` | `be674261677cc5101380f09c832a2ef64c22f37f768107d7e848a42907639974` | `b2dbd5b89d22e1fa01573df0c5e2d17d340445238aafcf74253407252b7e25c8` | `test_cross_reference_view.cjs.bak-20260917-xref` |

### Not owned by this lane - one-purpose edits, made because they assert wording the dwarfed tab no longer has
| File | sha256 before | sha256 after | edit |
|---|---|---|---|
| `C:\Users\pgoff\Mentat\mentat\tests\test_navigation_scope_browser.cjs` | `058e39710ae2369ab84271a436756cea16f42b88775e48fba5717ee7ce5fb1c5` | `e34941df688204c6f0d3c2171c4624fafffae9592fbe8c139f846ac49c4c9e5e` | 1 line (`:394` asserted `/Observed original giving/` in the rendered tab -> `/it publishes no totals/`) |
| `C:\Users\pgoff\Mentat\mentat\tests\test_console_browser.cjs` | `c01d8010625bf7d74840c0a8424ff34b28dcee188dc8fa9066218f0aee8d5ea5` | `952d041f33f1f7cb11b895f17bb1e70c59374324d1888b607d78e5a6408bc074` | 3 lines (`:259-261` waited for the removed total, counted 6 `.xref-step` nodes, matched `not yet verified unique dollars`) |
| `C:\Users\pgoff\Mentat\mentat\tests\test_studio_wording.cjs` | `3ff13919089d29f4c750a5b5a3e7270a13f0f40c31a577413cc8985c80031e33` | `adf69e10cc019530cf56c4761062241b2cf6305724cbb4cd20aff79d444ec612` | 1 `test()` block (`:100-124`) - it enumerated the 19-entry `reasons` map and the `$0` caption, both deleted from the view; replaced with a wording contract for what the tab does print |

Each has a `.bak-20260917-xref` backup beside it. `git diff --stat` after copy-back:
```
 mentat/app/cross-reference.js                  | 175 ++++++++++---------------
 mentat/app/cross_reference_data.py             |  96 +++++++++-----
 mentat/tests/test_console_browser.cjs          |   6 +-
 mentat/tests/test_navigation_scope_browser.cjs |   2 +-
 mentat/tests/test_studio_wording.cjs           |  36 ++---
 mentat/tools/run_cross_reference.py            |  30 +++++
 6 files changed, 178 insertions(+), 167 deletions(-)
```
`run_cross_reference.py` is **+30/-0**: nothing in the accounting path was removed or rewritten.

### Line endings
Verified byte-by-byte before and after. Every owned file is **LF** and stayed LF.
`tests/test_console_browser.cjs` is **CRLF (489)**; the first patch attempt aborted on its own
line-ending guard and was redone with CRLF anchors - CRLF count is 489 after, LF-only 0.
`mentat/README.md` (CRLF) was not touched at all.

### Artifacts written outside the repo source
`digest.json` in the two run directories (new files; nothing else in those directories was read for writing):
- `mentat/state/cross-reference/20260913T074303-bca0ac2b9cd3/digest.json` sha256 `95c3d68c2680d6c2e82e8f456bd783d1c61c31723142e750e7f141c6a743c1f3`
- `mentat/state/cross-reference/20260911T010907-d7fdb039c080/digest.json` sha256 `8a4aced9f1c9b36aaf9a6bd5e01b71a671d9c82eed06f668a4ed4b95e1f120ee`

## Baselines taken before any edit
- `python -m unittest discover -s tests -p "test_cross_reference_*.py"` -> `Ran 93 tests ... OK`
- `node --test "app/tests/scope.test.js"` -> `pass 30 / fail 0`
- `node --test "tests/test_cross_reference_view.cjs"` -> **already RED**, one assertion:
  expected `/Rows with an unresolved company attribution are counted at \$0 .../`,
  actual `Unresolved company attributions count as $0 in every total above.` The untracked test
  had drifted from the live view. This lane rewrote the file, so that red is gone.

## Test commands and their exact tails (live tree, `C:\Users\pgoff\Mentat\mentat`)

`python -m unittest discover -s tests -p "test_cross_reference_*.py"`
```
Ran 110 tests in 51.705s

OK
```

`node --test "tests/test_cross_reference_view.cjs" "app/tests/scope.test.js"`
```
Cross-reference view checks passed.
ℹ tests 31
ℹ pass 31
ℹ fail 0
```

`node --test "app/tests/*.test.js"`
```
ℹ tests 163
ℹ pass 163
ℹ fail 0
```

`node --test "tests/test_studio_wording.cjs"`
```
✔ the cross-reference says what it is, in the approved plain words (1.1369ms)
ℹ tests 10
ℹ pass 10
ℹ fail 0
```

`python -m unittest discover -s tests -p "test_industry_routes.py"` (the S4/S5 route contract)
```
Ran 20 tests in 1.608s

OK (skipped=1)
```

`node tests/test_navigation_scope_browser.cjs` (S5 real-client pass, real server + Chromium)
```
PASS step 13 - status "No cross-reference run for Banking · Saved evidence refreshed. This page is read-only."
ALL 13 STEPS PASSED
browser.close() exceeded its 20000ms bound
```
(The `browser.close()` line also appeared on the pre-edit failing run; it is a teardown warning, not a step.)

`node tests/test_console_browser.cjs`
```
Browser checks passed: Graph guided scopes, JFC, levels, direct/downstream separation, exports,
Advanced charts, freshness disclosures, responsive sidebar, skip link, keyboard tabs and local requests only.
```

`MENTAT_CROSS_REFERENCE_BROWSER=1 node tests/test_cross_reference_view.cjs` (opt-in real browser)
```
Cross-reference view checks passed.
Cross-reference browser checks passed.
```

## Step 6 - digests built for the two existing runs

CLI: `python tools/cross_reference_digest.py <run_dir>` (ledger opened `mode=ro`, only `digest.json` written).

Banking `20260913T074303-bca0ac2b9cd3` (3.67 GB ledger):
```
{"run_id": "20260913T074303-bca0ac2b9cd3", "source_records": 849399,
 "linked_refunds": 0, "linked_refund_amount": 0.0,
 "unlinked_adjustments": 641, "unlinked_amount": -1127074.41,
 "non_giving": 4778, "non_giving_amount": 76500263.92,
 "large": 24, "large_amount": 6949500.0, "elapsed_seconds": 31.76}
```
Fintech `20260911T010907-d7fdb039c080`:
```
{"run_id": "20260911T010907-d7fdb039c080", "source_records": 86270,
 "linked_refunds": 0, "linked_refund_amount": 0.0,
 "unlinked_adjustments": 56, "unlinked_amount": -125375.06,
 "non_giving": 100, "non_giving_amount": 724547.79,
 "large": 5, "large_amount": 909800.0, "elapsed_seconds": 2.48}
```
The 5-minute fallback the coordinator authorised was **not needed**: the 849,399-decision scan took 31.76 s,
so `large` is real on both runs, not empty.

Sample Banking rows (real data, from the written file):
- `non_giving[0]`: `Bank of America NA`, cycle 2022, `LOAN`, role `other_receipt`, **$10,000,000 removed**,
  `https://docquery.fec.gov/cgi-bin/fecimg/?202303219579570231`
- `large[0]`: `JP Morgan Chase Bank NA`, cycle 2026, entity `IND`, **$1,058,200** - an individual receipt
  over a million dollars, which is exactly the kind of row this view exists to put in front of someone.
- role census of the 200 listed non-giving rows: `other_receipt` 199, `asset_liquidation` 1
- entity census of the 24 large rows: `IND` 23, `ORG` 1

## What I could not do / deliberately did not do
1. **Step 7 (port 8833 live check) - not run.** Cut by the coordinator. Equivalent evidence exists from two
   real-browser passes against a real `python app/server.py` (`test_navigation_scope_browser.cjs` step 5
   fetched `/api/cross-reference?industry=Banking` and rendered the dwarfed payload; `test_console_browser.cjs`
   asserts `Observed original giving` appears **0** times in the live DOM). Neither used a real
   `state/cross-reference` root, so the two digests built in step 6 have **not** been served over HTTP.
2. **Step 8 (README) - not done.** Cut by the coordinator. `mentat/README.md` still describes the
   Cross-reference tab as the full accounting dashboard. That doc is now wrong and needs the two-sentence
   replacement.
3. **PROGRESS.md** was stopped on instruction after step 0; this receipt carries everything.

## Deviations from the written design (each deliberate, each flagged)
1. **`signed_adjustment_not_linked_refund` is not a decision reason.** The engine files that string in its
   *review queue* and writes `negative_amount_is_not_refund_proof` on the decision row
   (`mentat/tools/cross_reference_engine.py:522-523`). Matching only the design's name would have produced an
   always-empty `refunds.unlinked`. `build_digest` accepts **either** name; a test covers each.
2. **`non_giving` is selected from the decision's own `reasons` list**, not by prefix-matching the change
   row's `reason` string. The runner joins reasons with `'; '` after sorting
   (`run_cross_reference.py:281`), so `automatic_exact_alias_recheck` can sort ahead of
   `non_giving_receipt_role:` and a prefix match would silently drop rows. The change row is still joined for
   its description and URL.
3. **Three extra keyword arguments on `build_digest`:** `run_id`, `generated_at` (the schema requires them and
   they are not derivable from the three inputs), and `descriptions` alongside the design's `entities` and
   `source_urls`. `source_urls`/`descriptions` are needed because a *saved ledger* stores the **engine's**
   change rows, which carry cents and reasons but no prose and no URL - the CLI reads `pdf_url`,
   `receipt_type_full` and `memo_text` from `source_records` instead, matching what `presentation()` shows.
   Without them every CLI-built row would have an empty link.
4. **Memory shape.** The design allowed ~849k retained dicts. `build_digest` instead consumes `links`, then
   `decisions`, then `changes`, retaining only rows it can list, and asks `entities`/`source_urls` for a
   bounded set of ids. The CLI backs those with a lazy `source_records` reader, so the 3.67 GB Banking ledger
   never materialises. This is why the run took 31 s rather than minutes.
5. **`report["status"]` kept.** The design's payload list omits it, but
   `audits/mentat_failings_20260915/contracts/contributions_api.json` example 14 shows `report.status`.
   Keeping it costs nothing and keeps the published contract honest.
6. **`digest_message` added** to the payload to carry the "no digest" sentence the design specified;
   `digest` is `null` when unavailable so the view cannot render empty tables in its place.
7. **The `limitations` panel is no longer rendered** (the payload still carries it, as designed). One of the
   run's own limitation strings is *"Observed original giving is not a certification of complete unique
   dollars"* - rendering it would have put the banned phrase back on the tab.
8. **The whole `reasons` map was deleted** from `cross-reference.js`. The design said to keep the entries
   still used; the new render uses none. Two small maps replaced it: `roles` (2 entries) and `entities`
   (7 entries). `stepHtml` was dropped after grepping - only `app.js` imports this module, and only
   `setActive`.
9. **Thresholds are validated at the top of `run()`**, not at the digest write, so a mistyped
   `MENTAT_XREF_LARGE_RECEIPT_CENTS` fails in the first second rather than after a 40-minute Banking run.

## Risks checked
- **Report keys moved?** No. `run_cross_reference.py` is +30/-0; `report.json`'s dict literal is untouched and
  `test_cross_reference_runner.py` / `test_cross_reference_engine.py` (93 -> now inside the 110) stay green.
- **Digest write failing a long run?** It uses the same `atomic()` helper as every other artifact, which
  already retries `os.replace` 8 times on Windows `PermissionError` (`tools/report_source_guard.py:45-52`) -
  the known `WinError 5` flake. A genuine bug still raises loudly rather than writing a partial file.
- **Read-only guarantee of the CLI.** Opens `ledger.sqlite` with `mode=ro` via `as_uri()`, writes only
  `digest.json`. A test asserts every other file in the run directory is byte-identical afterwards.
- **Path traversal / oversize / duplicate-key / non-finite JSON** for `digest.json`: all four go through the
  same `_load` as `report.json` (4 MB cap) and have tests, including a redirected-resolve test that models a
  reparse point pointing outside the state root.
- **XSS / URL laundering**: every digest row is whitelisted through `_rows`; ids cap at 120 chars,
  descriptions at 300, and all four URL fields go through `_source_url`. The view escapes every value; the
  injection test covers each new table.
- **Donor privacy**: the digest carries no contributor name. A test asserts `PERSON, ONE` never appears in a
  CLI-built digest, and the payload test asserts the report's own totals never appear by key or by value.
- **S5 navigation contract**: `selected_by`, `industry`, the pointer path and the industry path are unchanged
  and proven by `test_industry_routes.py` (20 OK) and the 13-step real-client pass.
