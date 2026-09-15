# Wording lane - progress (finish pass, 2026-09-15)

Two earlier executors died on rate limits. State below was established from files
only; none of their written summaries was trusted.

## Step 1 - STATE (done)

- HEAD `5937875c8ecd15a73897964f1379ff4e0a9916f1`, branch `codex/mentat-crypto`.
- 11 `*.bak-20260914-wording` backups under `mentat/app`; `before_census.txt` is
  byte-for-byte the backup state, so it is a true pre-patch baseline.
- **All 95 change-table rows verified**: new text present, old text absent.
- Census arithmetic reconciled: 95 changed + 165 stayed + 231 out of scope = 491.
  WORDING_PASS.md's prose says "96 + 164 + 231"; the buckets are really 95/165.
  A typo in the record, not a missing row. Flagged; spec left as Paul approved it.
- Backup-vs-live diff: 86 hunks total, **every one** explained by a spec row or by
  code change 1. No unexplained edit anywhere in the 11 files.
- Line-ending classes identical for all 11 files, `graph.js`'s per-line mix
  (289 CRLF / 22 LF) included. Only delta: `chart-studio.js` 2643 -> 2642 CRLF,
  which is row 142 folding three source lines into two. No BOM added anywhere.
- Test files touched by *this* lane: exactly 3 under `mentat/app/tests`, all dated
  2026-09-14 23:53-23:55 and each with a wording backup byte-identical to HEAD.
  Their edits are pure expectation swaps - nothing needed reverting.
- The other 25 modified files under `mentat/tests` date from 09-09 to 09-13 and
  belong to other lanes. **Left untouched**; reverting them would destroy that work.

## Step 2 - CODE CHANGE 1 (already applied by executor 2; verified here)

Verified mode now folds at 60 like Graph and the classic builder:

- `mentat/app/chart-studio-core.js:191` - `const STUDIO_GROUP_LIMIT = 60;`
  (consumed at `:360`, the real verified-mode default)
- `mentat/app/chart-studio-contributions.js:125` - `Number(state.params?.maxGroups)||60`
- `mentat/app/chart-studio.js:2479`, `:2480` - paging step `||60`
- `mentat/app/index.html:278` - `placeholder="60" title="Groups shown per page"`

No server-side group default exists to change: `contribution_query.py` receives
`limit` from the client and holds no literal 40. The only 40s left in `server.py`
are the SHA-length regex (`:138`) and the briefing-item cap (`:1018`/`:1019`),
which row 462 deliberately keeps. **The 40-filter cap was not touched.**

## Step 3 - TESTS (done)

| suite | result |
|---|---|
| `node --test "mentat/app/tests/**/*.test.js"` | **108 pass, 0 fail** |
| six python unittest suites | **Ran 58, OK** |
| fix1 round-2 `.cjs` set (7 suites) | **34 pass, 0 fail** |
| extra: `test_chart_math.cjs` + `test_studio_click_to_add_browser.cjs` | 21 pass, 0 fail |

Executor 2 had fixed only 3 node expectations before dying. Residual stale pins
were found by running the suites, not by guessing: 2 node, 4 python, 13 `.cjs`.
No assertion was removed or loosened.

A repo-wide literal scan for retired strings was also run. It is useful but not
sufficient: regex-escaped pins such as `\(workbook receipts\)` and short fragment
pins such as `/Preparing cancelled/` defeat literal matching, and three of the
failures above were invisible to it. The suite run is the authority.

## Deviation from the approved spec - needs Paul's ratification

`test_studio_wording.cjs:126` asserts every `RECONCILE_REASONS` value matches
`/^[a-z]/`, so each reads as the tail of "They differ by $X because ...".
The spec's new text for **rows 85 and 86** begins with the proper noun "Graph"
and fails that rule. `lanes/fix1/RECEIPT.md` hit this exact case and recorded the
resolution - "Both assertions are right and neither was loosened" - by rewording
the reason. Same resolution here:

| row | spec text | shipped text |
|---|---|---|
| 85 | `Graph shows one election cycle and this sheet shows all of them` | `the Graph view shows one election cycle and this sheet shows all of them` |
| 86 | `Graph has no total for this scope` | `the Graph view has no total for this scope` |

Meaning and the spec's simplification are preserved; only an article is added.
93 of 95 rows match the spec verbatim; these 2 differ by that article.

## Step 4 - LIVE CHECK (in progress)

Throwaway console only: a scratchpad copy of the Crypto workbook via
`MENTAT_REPORT_DIRECTORY`, a fresh scratchpad `--data-root`, a free port.
Paul's console on 8806 (data-root under LOCALAPPDATA) is never written to.

## Step 5 - RECEIPT + COMMIT (pending)
