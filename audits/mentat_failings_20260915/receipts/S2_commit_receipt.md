# S2 commit receipt — 2026-09-16

Whole-file commit at Paul's ruling (option 1). Untracked by design; leave it.

## Commits

| | SHA |
| --- | --- |
| OLD_HEAD (session start) | `11654f911184a6ca5d9aa2d079f0c18ade578d09` |
| S2 commit | `d78cf0b8f1a03911ba0791220f396cd838eb6a00` |

Branch `codex/mentat-crypto`. Author/committer `Paul Goff <goff0070@umn.edu>` (config untouched).

Note on the original plan: it assumed HEAD `bd5dc8ea1` and a two-commit split.
`11654f911` had already committed the whole packet directory — the S0 files, the
S2 receipts, both patches, the contract JSON and the post-S2 `HANDOFF.md` /
`contracts/README.md`. The planned "commit 1" was therefore skipped; running it
as written would have staged the pre-S2 `before/` blobs and reverted S2's
HANDOFF section out of history.

## Why whole-file and not hunk-clean

A three-way merge in LF space (`git merge-file -p head.lf before.lf live.lf`)
separated S2's hunks cleanly in 3 of 6 contended files and failed in the other 3:

| File | conflicts | S2 hunks reproduced | other lanes preserved |
| --- | --- | --- | --- |
| `mentat/R/schema.R` | 0 | PASS | PASS |
| `mentat/R/report.R` | 0 | PASS | PASS |
| `mentat/tools/crypto_workbook_builder.mjs` | 0 | PASS | PASS |
| `mentat/R/collect.R` | 2 | FAIL | FAIL |
| `mentat/R/fec_api.R` | 1 | FAIL | FAIL |
| `mentat/tools/export_crypto_spending_data.R` | 1 | FAIL | FAIL |

Cause, verified by occurrence counts rather than inference:

- `contributor_id` — HEAD 0, pre-S2 snapshot 9 (`collect.R`) / 1 (`fec_api.R`).
  Entirely the contributor-id lane's. S2's own column lists carry it, so an
  S2-only blob would reference a column only that lane's hunks produce.
- `fec_assert_receipt_evidence` / `evidence_scope` / `receipt-review` — HEAD 0,
  pre-S2 1/3/1. Entirely the evidence-archive lane's; S2's street-fill guard sits
  immediately against that block.

## Commit contents (`git show --stat`)

```
 audits/mentat_failings_20260915/HANDOFF.md         |  40 +-
 mentat/R/collect.R                                 | 351 +++++++++++++---
 mentat/R/fec_api.R                                 | 274 +++++++++++--
 mentat/R/report.R                                  |  34 +-
 mentat/R/schema.R                                  | 247 ++++++++----
 mentat/R/tidy_stage.R                              |   5 +-
 mentat/tests/test_backfill_contributor_street.py   | 386 ++++++++++++++++++
 .../test_export_raw_contribution_warehouse.py      |  74 +++-
 mentat/tests/test_raw_contribution_columns.R       | 439 +++++++++++++++++++++
 mentat/tests/test_raw_contribution_columns.cjs     | 161 ++++++++
 mentat/tests/test_raw_contribution_columns.py      | 386 ++++++++++++++++++
 mentat/tools/backfill_contributor_street.py        | 340 ++++++++++++++++
 mentat/tools/build_tidy_workbook.py                |   4 +-
 mentat/tools/crypto_workbook_builder.mjs           | 115 ++++--
 mentat/tools/export_crypto_spending_data.R         | 147 ++++++-
 mentat/tools/export_raw_contribution_warehouse.py  | 125 +++++-
 16 files changed, 2884 insertions(+), 244 deletions(-)
```

Staged set was exactly 16 paths (11 `M`, 5 `A`), each added by explicit path.
No `git add -A`, no `git add .`, no stash, checkout, reset, clean or push.

## Working-tree SHA256 (before → after commit)

15 of 16 byte-identical. Only `HANDOFF.md` changed, by the STEP 1 status flips.

| Path | SHA256 |
| --- | --- |
| `mentat/R/schema.R` | `0e91cbf2c3f2034b6dc329b416d1aca1f359743b81c10e6938ddc1e4214e8f7d` |
| `mentat/R/collect.R` | `4af91497af509295c8722f1cb3aa2cea74df1379a80347b8c7d100246cae54a5` |
| `mentat/R/fec_api.R` | `6b94ed072ad8843294d526f653019c730de744a221f61eb16431276d72ff0af7` |
| `mentat/R/report.R` | `661e737a18ce13ac5920524f78a2d182b479dd08e26a3c353dae11f30a74b116` |
| `mentat/R/tidy_stage.R` | `f83a5ad7e169a165ba67ceb0c66341a4ada674fc54af856b802084a77686ce34` |
| `mentat/tools/export_raw_contribution_warehouse.py` | `4ab775e4826e98e4e5d846d7b69ca25117926d0f0da3fa5dde5cc80a9c1d100e` |
| `mentat/tools/export_crypto_spending_data.R` | `0d6dfcca33ced195702ff765d22a8be933db2996eb90602f2a00f66b92fa8b14` |
| `mentat/tools/crypto_workbook_builder.mjs` | `ffafe6cb6846ab310fffffdbbdcc339db77f64837a11b135b9c6dc63c49ac4a6` |
| `mentat/tools/build_tidy_workbook.py` | `9d7059cce3ce69c3a47410cf185f630b67ac263b6eab7e2186303ba8f7d3dfe4` |
| `mentat/tests/test_export_raw_contribution_warehouse.py` | `1627676e9c547c4d6c4406a1a7d08dd1ded63b295ad4e54aae8e28f6ab356de5` |
| `mentat/tools/backfill_contributor_street.py` | `cc0d1d8791db3a6030994c2e0aa67bac0849f5f3621102ec8a74ea0a296b3f66` |
| `mentat/tests/test_raw_contribution_columns.py` | `24f93df7a7a4cae2bb8b50e716af9d205fe0aee6f3ed237cab69047512ae6633` |
| `mentat/tests/test_raw_contribution_columns.R` | `24f13899c2b840c41fab97952bcbbf8c80f3532c0b8a6eef5e8d39fe65189e24` |
| `mentat/tests/test_raw_contribution_columns.cjs` | `f84de1f45546e3d39d97a241409fa65fa52104d5116fca728b9c96388a6109b7` |
| `mentat/tests/test_backfill_contributor_street.py` | `ea6fe55f6275003537d8a10d9b1f6d310f8b938152cadeae12f6341b346fc4e3` |
| `HANDOFF.md` before | `1eca4af48b6b5a754b59cfe432148e05c3b8d4eae50f7445b92016d0f2d2e37c` |
| `HANDOFF.md` after | `61a03b2e0e67bcdf489524ca234a1a321f0ceb8d95519e8bd6ecb2ff39ae03ea` |

`HANDOFF.md` kept its UTF-8 BOM and its mixed endings (8 CRLF unchanged);
+8 LF lines, +542 bytes. All five anchors asserted before substitution;
`receipts ready` occurrences went 15 to 0.

## Status count

Session start 268. Expected after committing 15 tracked-status paths: 253.
Actual: 255. The +2 is a concurrent lane writing to the repo during this session:

- `mentat/tools/pac_evidence.py` — became ` M` at 15:45:25 today
- `mentat/tests/test_pac_evidence_errors.py` — became `??` at 15:44:33 today

Neither is in `d78cf0b8f` (`git show --name-only` has no `pac_evidence` path).
None of the 16 committed paths remains ` M` or `??`.

## Archived-tree self-containment test

`git archive HEAD mentat audits` gave 436 files. Negative control holds: the
untracked `mentat/R/state_destinations.R` and the uncommitted
`mentat/tests/test_pac_evidence_errors.py` are both absent, so the archive is
the committed tree only.

| Suite | Result |
| --- | --- |
| `python -m unittest tests.test_raw_contribution_columns tests.test_backfill_contributor_street tests.test_export_raw_contribution_warehouse` | PASS — 20 tests, OK |
| `node tests/test_raw_contribution_columns.cjs` | PASS — 4/4 |
| `Rscript tests/test_raw_contribution_columns.R` | PASS 8/8 once `inputs/` data present (see below) |
| `Rscript tests/test_fec_api.R` | FAIL on the committed tree (see below) |

### R contract suite — data dependency, not a source gap

First run failed checks (c) and (h) with
`path[1]=".../archive2/mentat/inputs": The system cannot find the file specified`.
`mentat/inputs/` is gitignored (`.gitignore:65`), holds 21 entries in the live
tree and has **0 entries across all git refs** — repo-external data by design,
not something an uncommitted hunk supplies.

- With an empty `inputs/`: check (c) passes; (h) fails on a JSON lexical error.
- Exact file required: `mentat/inputs/fec_receipt_rules.json`, read by
  `fec_receipt_rules()` at `mentat/R/collect.R:33-34` via
  `file.path(mentat_input_dir(), "fec_receipt_rules.json")`.
- With that one file copied in: **8/8 PASS**, exit 0.

S2's own code is therefore self-contained in the commit.

### `tests/test_fec_api.R` — missing uncommitted hunk, named

Fails on the archived tree with:

```
Error: FEC API requires an exact nonnegative pagination.count:
P1_employer:Binance:2024:BINANCE. Response preserved; split or rerun the query.
```

Exact missing item: **`mentat/tests/test_fec_api.R` is modified-uncommitted**
(` M`) in the working tree. Copying only that live file into the archive makes
the suite **PASS, exit 0** — the five modified R sources (`export_guards.R`,
`fec_beneficiary.R`, `fec_page.R`, `fec_transfer_graph.R`, `paths.R`) were not
needed.

Consequence of the whole-file ruling: committing `fec_api.R` whole carried the
contributor-id lane's pagination changes into HEAD, but that lane's matching
update to `tests/test_fec_api.R` is still uncommitted. `tests/test_fec_api.R` is
therefore stale at HEAD and will fail until that lane commits its test hunk.
Not fixed here, per instruction.
