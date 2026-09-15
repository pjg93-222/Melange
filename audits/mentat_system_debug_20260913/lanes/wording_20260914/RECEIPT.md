# Wording pass - receipt (finish pass, 2026-09-15)

Paul approved the patch and the commit. Two earlier executors died on rate limits
part-way; this pass established every claim below from the files themselves and
from suites actually run. None of their written summaries was trusted.

Branch `codex/mentat-crypto`, parent `5937875c8ecd15a73897964f1379ff4e0a9916f1`.

## 1. The 95 rows

`WORDING_PASS.md` lists 95 rows in its change table. Every one was checked against
the live file: **new text present, old text absent, 95 of 95**.

The spec's prose line says "Changed rows: 96 ... 96 + 164 + 231 = 491". The real
buckets are **95 changed + 165 stayed + 231 out of scope = 491**, which also sums
to 491 and leaves no row unaccounted for. The prose is off by one in both
directions - a bookkeeping typo in the record, not a missing row. `WORDING_PASS.md`
was left exactly as Paul approved it; this receipt records the correction.

**Negative control on the whole patch.** Each of the 11 `*.bak-20260914-wording`
backups was diffed against its live file: **86 changed hunks in total, and every
single one is explained** by a listed row or by code change 1. No stray edit
exists anywhere in the 11 files. `before_census.txt` was confirmed byte-identical
to the backups, so it is a genuine pre-patch baseline rather than a post-hoc one.

The 165 "rows that stay" are covered by the same control: had any been touched,
it would have surfaced as an unexplained hunk. None did.

## 2. Deviation from the approved text - rows 85 and 86

`mentat/tests/test_studio_wording.cjs:126` asserts that every `RECONCILE_REASONS`
value matches `/^[a-z]/`, so each reads as the tail of
"They differ by $X because ...". The spec's new text for rows 85 and 86 begins
with the proper noun "Graph" and fails that rule.

`lanes/fix1/RECEIPT.md` hit this exact case and recorded how it was settled:
*"Both assertions are right and neither was loosened"* - the reason was reworded.
The same resolution was applied here rather than relaxing a house rule a previous
lane deliberately upheld:

| row | approved text | shipped text |
|---|---|---|
| 85 | `Graph shows one election cycle and this sheet shows all of them` | `the Graph view shows one election cycle and this sheet shows all of them` |
| 86 | `Graph has no total for this scope` | `the Graph view has no total for this scope` |

Only an article is added; the meaning and the spec's simplification are kept, and
"the Graph view" is vocabulary the approved *old* text already used. 93 of 95 rows
match the spec verbatim. **This is the one thing in this lane that needs Paul's
ratification.**

## 3. Code change 1 - the group limit is 60

Already applied by the second executor; verified here rather than assumed:

| file:line | now |
|---|---|
| `mentat/app/chart-studio-core.js:191` | `const STUDIO_GROUP_LIMIT = 60;` (consumed at `:360`) |
| `mentat/app/chart-studio-contributions.js:125` | `Number(state.params?.maxGroups)||60` |
| `mentat/app/chart-studio.js:2479` | `groups-prev` step `||60` |
| `mentat/app/chart-studio.js:2480` | `groups-next` step `||60` |
| `mentat/app/index.html:278` | `placeholder="60" title="Groups shown per page"` |

**No server-side default mirrors the 40.** `contribution_query.py` takes `limit`
from the client and holds no literal 40 at all; `contribution_query_store.py` the
same. The only literal 40s left in `server.py` are the SHA-length regex (`:138`)
and the briefing-item cap (`:1018`/`:1019`), which row 462 deliberately keeps at
40. **The 40-filter cap was not touched.**

## 4. Test files - kept, fixed, reverted

**Reverted: nothing.** The second executor's three edits were inspected before
anything else was done. All three backups (`*.bak-20260914-wording` under
`mentat/app/tests`) are byte-identical to `HEAD`, and every edit in them is a pure
old-string-for-new-string swap matching the spec. Nothing else had been changed,
so there was nothing to revert.

25 other files under `mentat/tests` also differ from HEAD. Their mtimes run from
2026-09-09 to 2026-09-13 and they carry no wording backup: they belong to other
lanes. They were **left untouched and are not in this commit**; reverting them
would have destroyed other lanes' work.

The second executor had fixed 3 node expectations before dying. The rest were
found by running the suites, not by reading its notes:

| where | stale pins fixed |
|---|---|
| `mentat/app/tests` (node) | 2 - scatter grouping, cycle reason tail |
| `mentat/tests/*.py` | 4 - two read-only refusals, the port refusal, the collection refusal |
| `mentat/tests/*.cjs` | 13 - wording suite, lazy-startup stamp, briefing tray, data source, reconciliation, contributions |

**No assertion was removed or loosened.** Three cases deserve naming:

- The build stamp pinned `pid 79412`. Rule 2 removed "pid" from the stamp, so the
  pid can no longer be asserted; the port and build sha, which identify the
  answering console, are still pinned.
- The reconciliation strip pinned the prefix `^Basis: Observed original giving
  (provisional).`. Ruling (a) removed the `Basis:` prefix from the strip, so that
  prefix cannot hold; it was replaced with a pin on the **whole** new sentence
  shape, which asserts strictly more than the old prefix did.
- The two `assertIn` fragment checks now pin the complete new message.

The group-limit test gained two assertions rather than losing any: the markup
`placeholder="60"`, and that `index.html` no longer says "40 per page".

A repo-wide literal scan for retired strings was also run (29,239 files). It is
useful but **not sufficient**, and this receipt will not claim otherwise:
regex-escaped pins such as `\(workbook receipts\)` and short fragment pins such as
`/Preparing cancelled/` defeat literal matching, and three of the failures above
were invisible to it. Running the suites is the authority. Its one live-code hit,
`chart-studio.js:1819`, is a code comment stating a true fact about the data
model, not reader-facing text; it was left alone.

## 5. Test totals

| suite | result |
|---|---|
| `node --test "mentat/app/tests/**/*.test.js"` | **108 pass, 0 fail** |
| six python unittest suites | **Ran 58, OK** |
| the fix1 round-2 `.cjs` set, 7 suites | **34 pass, 0 fail** |
| also run: `test_chart_math.cjs`, `test_studio_click_to_add_browser.cjs` | 21 pass, 0 fail |

The `.cjs` set that gives 34 is lazy-startup (3) + briefing tray (2) + copy/print
(4) + data source (1) + reconciliation (1) + wording (10) + chart studio
contributions (13). That reconstructs fix1's round-2 set exactly.

One python run raised a `WinError 32` while deleting a temp log at teardown - a
spawned console still held the file. It is a Windows cleanup race, not an
assertion, and did not recur on two further runs (58 OK, 58 OK).

## 6. Live check

A throwaway console only: port 8831, pid 43300, `MENTAT_REPORT_DIRECTORY` pointing
at the scratchpad **copy** of `Crypto Industry Spending Overview.xlsx`, and a
brand-new `--data-root`. Paul's console on 8806 was never posted to and is still
running. The console was stopped afterwards; only Paul's 8806 and the unrelated
staffer server on 8841 remain.

| check | live result |
|---|---|
| strip | `Graph shows $102,731,131.38 for All companies · 2026. Studio shows $249,949,483.17. They differ by $147,218,351.79 because the Graph view shows one election cycle and this sheet shows all of them.` |
| groups tooltip | `Groups shown per page. Totals and CSV exports include every group.` |
| groups default | `placeholder="60"` |
| not-carried chips | `Giving type: not carried (not in verified data) · Candidate view: not carried (Graph only)` |
| drawer caption | `Each slide shows its scope, basis and source.` |
| stale banner | `This console runs an older build. Press Restart, or close this tab and open http://127.0.0.1:8831.` |
| `POST /api/restart`, current console | **`Already up to date.`** |
| build stamp | `build 5937875 · port 8831 · up since 03:59 AM` |
| page errors | none |

The strip shows both required shapes: the two totals, then the verdict. The
agreeing form (`Agree.`) was observed in the browser suite; the differing form is
above.

A first restart probe returned 403 `Refresh the app before continuing.` That was
the probe's fault, not the code's: `server.py:1829` requires the `X-Mentat-Token`
header and a raw `fetch` does not send it. Driven the way a reader drives it -
banner up, Restart clicked - the console answered `Already up to date.`

Screenshots in this folder: `W1-reconciliation-strip.png` (the strip),
`W2-briefing-drawer.png` (the drawer caption), `W1b-studio-full.png`,
`W3-not-carried-chips.png` and `W4-not-carried-chips-detail.png`.

## 7. Line-ending census

Every class held. `before` is `before_census.txt`, taken from the pre-patch state.

| file | sha | bytes | crlf | lf | class | before crlf/lf |
|---|---|---|---|---|---|---|
| `mentat/app/app.js` | ee9fc93 | 57365 | 281 | 397 | mixed | 281/397 |
| `mentat/app/chart-briefing.js` | 7ba4c0a | 29199 | 0 | 683 | lf | 0/683 |
| `mentat/app/chart-export.js` | 1b1345c | 6778 | 17 | 79 | mixed | 17/79 |
| `mentat/app/chart-studio-contributions.js` | 502d85f | 19976 | 0 | 177 | lf | 0/177 |
| `mentat/app/chart-studio-core.js` | 8334ed5 | 51546 | 883 | 48 | mixed | 883/48 |
| `mentat/app/chart-studio.js` | 9e2b086 | 155376 | 2642 | 0 | crlf | 2643/0 |
| `mentat/app/charts.js` | efabeb8 | 34828 | 239 | 155 | mixed | 239/155 |
| `mentat/app/cross-reference.js` | c4270d4 | 18408 | 0 | 163 | lf | 0/163 |
| `mentat/app/graph.js` | 1c619d8 | 24949 | 289 | 22 | mixed | 289/22 |
| `mentat/app/index.html` | 6c14d97 | 58009 | 373 | 2 | mixed | 373/2 |
| `mentat/app/server.py` | 49eee44 | 110531 | 1937 | 0 | crlf | 1937/0 |

**How the census relates to what is committed.** This repo has
`core.autocrlf=true` and `HEAD` stores **LF for every one of these files**
(`HEAD:mentat/app/server.py` has 0 CRLF and 1937 LF, and so on down the list).
The CRLF counts in the table are what `autocrlf` writes to disk on checkout, not
what is stored. `git add` therefore strips CR back out, and the staged blobs carry
exactly the line counts `HEAD` carries - 678, 96, 931, 394, 311, 375, 1937, 1133 -
with the single intended exception below. So nothing in this commit changes a line
ending anywhere, in the object store or on disk. Staged and `HEAD` blobs were
compared directly to prove it, rather than inferred from the `add` warnings.

The single count change is `chart-studio.js` 2643 -> 2642 CRLF (and 2643 -> 2642
LF in the blob): row 142 folds three source lines into two. `graph.js` keeps its per-line mix (289 CRLF / 22 LF)
exactly, as do `app.js`, `charts.js`, `chart-export.js`, `chart-studio-core.js`
and `index.html`. No BOM was added to any file.

| test file | sha | bytes | crlf | lf | class |
|---|---|---|---|---|---|
| `mentat/app/tests/chart-briefing.test.js` | 9be9bde | 2826 | 0 | 62 | lf |
| `mentat/app/tests/chart-studio-core.test.js` | c5f500e | 68185 | 1051 | 82 | mixed |
| `mentat/app/tests/reconcile-cycle.test.js` | 896d7b7 | 4046 | 0 | 77 | lf |
| `mentat/tests/test_studio_views.py` | 0e4fff7 | 10409 | 0 | 199 | lf |
| `mentat/tests/test_studio_briefing.py` | 82d0f3c | 10648 | 0 | 191 | lf |
| `mentat/tests/test_publish_pocket.py` | 633c7b1 | 17143 | 0 | 331 | lf |
| `mentat/tests/test_contribution_http.py` | 2f435f1 | 23658 | 0 | 383 | lf |
| `mentat/tests/test_studio_wording.cjs` | 9a18d29 | 8521 | 0 | 130 | lf |
| `mentat/tests/test_app_lazy_startup_browser.cjs` | 4d17dac | 7110 | 0 | 50 | lf |
| `mentat/tests/test_studio_briefing_tray_browser.cjs` | 88f4405 | 10604 | 0 | 173 | lf |
| `mentat/tests/test_studio_data_source_browser.cjs` | 26dad99 | 9065 | 0 | 125 | lf |
| `mentat/tests/test_studio_reconciliation_browser.cjs` | 6205210 | 11042 | 0 | 147 | lf |

## 8. What is in the commit, and what is deliberately not

Committed by explicit path: the 11 app files above, the 12 tracked test files
above, and this lane folder.

Deliberately **not** committed:

- `mentat/app/desktop/Launcher.cs`, `mentat/app/graph.css`, `mentat/app/graph_data.py`,
  `mentat/app/report_insights.py`, `mentat/app/style.css` - modified under
  `mentat/app` by other lanes, nothing to do with wording.
- The 25 other modified files under `mentat/tests` - other lanes, dated 09-09 to 09-13.
- `mentat/tests/test_chart_studio_contributions.cjs` - **this lane edited two lines
  in it** (the verified page size 40 -> 60, and the row 81 basis reason), but the
  file is untracked: it is a live-only file created by an earlier lane and never
  committed. Committing it would land that whole lane's file under this lane's
  message. The two edits stay in the working tree, which matches the file's
  existing uncommitted state. **Flagged for Paul.**
- Every `*.bak-*`, `contribution-studio.*` and `mentat/state` path.
