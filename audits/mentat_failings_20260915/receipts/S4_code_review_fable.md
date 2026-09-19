# Code Review: S4 cross-industry addressing (commits 8377b5e77, 9262614c2)

**Reviewed**: 2026-09-16, by Fable (the session model, on Paul's instruction "You should review in Fable"), after the three subagent reviews (python, typescript, code-reviewer) had closed their findings.
**Branch**: codex/mentat-crypto, range 21c9cab6d..9262614c2, 36 files
**Decision**: REQUEST CHANGES, then FIXED in `b13d09018` (same session)

## Summary

The registry, scope resolution, route hunks, cross-reference-by-industry and client model are correct against the contracts and carry no injection or path-leak surface. One user-visible regression escaped every prior review and all 118 passing tests: a report-worksheet view could no longer be saved. Fixed with two regression tests; node 121/121, python 24 OK on the studio suites.

## Findings

### CRITICAL
None.

### HIGH
- `mentat/app/chart-studio-core.js:105` (at 9262614c2): `createSheet()` stamped every default sheet source with `industry: ''` and `dataset: ''`; `server.py validate_view_industries()` (:58-63) refuses a sheet source whose `industry` key is present but empty. Every non-contributions (report worksheet) view therefore failed to save. Reproduced in-process against the committed server: `POST /api/studio/views` with a fresh worksheet sheet returned `400 {"error":"Every series source in a saved view needs an industry."}`. Why the tests missed it: the python round-trip fixtures predate the default keys, the browser real-client pass used contributions mode, and the node suite asserted only that `sources: []` exists. Fix (`b13d09018`): the default source carries neither key; contributions mode (`chart-studio.js:355`) and `migrateSheet()` set them when a dataset exists. Regression tests: `app/tests/studio-worksheet-sheet.test.js` (3) and `tests/test_studio_worksheet_view_saves.py` (2, one the negative control that an empty industry is still refused).

### MEDIUM
None.

### LOW
- `mentat/tools/crypto_workbook_builder.mjs:2243`: the Contributor Detail title text still read "state / city / ZIP / employer / occupation" after street joined the grain. Fixed in `b13d09018`.
- `mentat/app/cross_reference_data.py:329`: on the pointer path `industry` is read from `result["report"]["scope"]["industries"]`, so it echoes null whenever `_report()` omits `scope`. The industry path sets it explicitly. Verify `_report()` keeps `scope` before S5 relies on the pointer-path echo.
- `mentat/app/snapshot_registry.py validate_entry` is 55 lines, over the skill's 50-line mark; it is a flat validator with one rule per statement, left as is.

## Sound (checked, no defect)
- No SQL or file path is ever built from the `industry` string: it exact-matches registry labels or a run's `scope.industries`; the cross-reference scan keeps `RUN_ID` gating and `_load()` containment.
- No absolute path enters a registry entry (`_database()` reduces out-of-project paths to a name; `_file()` swallows `OSError` so no `FileNotFoundError` text reaches the 400 body).
- Blank `?industry=` reaches `resolve()` through `keep_blank_values`; unknown labels answer the registry refusal; `industry`/`dataset` disagreement answers its own 400.
- Registry built at most once per request (catalog and graph thread it through); none when no selector is present.
- `migrateSheet()` clones before mutating; `openView()` applies it to every sheet; `chartSourceRecord()`/`viewSourceRecord()` write `industry` only when non-empty.
- No `console.log`, `TODO`, `FIXME` or debugger statements in the added source lines.

## Validation Results

| Check | Result |
| --- | --- |
| Python unittest (9 suites) | Pass, 118 tests, 1 skipped |
| Python studio suites after fix (4 suites) | Pass, 24 tests |
| Node `app/tests/**/*.test.js` | Pass, 118 before fix, 121 after |
| `tests/test_contributor_detail_header.cjs` | Pass, 4 |
| `node --check` / `py_compile` on staged blobs | Pass (at commit time) |
| Lint / type check | Skipped (none configured) |

## Files Reviewed
Modified: mentat/app/server.py, cross_reference_data.py, contribution_data.py, contribution_semantics.py, chart-studio-core.js, chart-studio.js, chart-studio-contributions.js, studio-contract-examples.json, mentat/tools/crypto_workbook_builder.mjs, mentat/R/report.R, mentat/tests/test_spending_detail_frames.R, test_contribution_http.py, mentat/app/tests/studio-contract.test.js, contracts/README.md, contracts/raw_contribution_columns.json, HANDOFF.md.
Added: snapshot_registry.py, industry_scope.py, six S4 test files, three contracts, S4_DESIGN.md, S4 receipts, the S4 patch.
