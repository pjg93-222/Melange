# Mentat Tidy Data-Workbook Lane — Delivery Packet

This packet collects the finished deliverables from the Mentat tidy-workbook lane (2026-09-14/15): the proposal and staging contract, the mock tidy workbook produced by Lane A with its evidence and lint/reader-check receipts, and the full Lane B patch set with its receipt and apply order. **Nothing in this lane has been applied to the live Mentat system.** Paul applies the changes by following `patches\APPLY_ORDER.md`; every other file here is supporting evidence (receipts, progress notes, and the scripts that produced the mock workbook and its checks).

Both lanes now have independent verification: `receipts\VERIFY_A.md` (Lane A). Lane B was verified twice: `receipts\VERIFY_B.md` covers the first 12 patches, and `receipts\VERIFY_B2.md` is the independent re-check of the final 15-patch set (adding the P6c, P8, P8b addendum patches).

## File manifest

All sizes in bytes, SHA-256 computed with PowerShell `Get-FileHash`. This file (`README.md`) is not listed — a file cannot record its own hash before it is written.

### Root

| File | Bytes | SHA256 |
|---|---:|---|
| MENTAT_TIDY_WORKBOOK_PROPOSAL_2026-09-14.md | 26885 | 25df11abef7e13f904b1dfbacc8e2f9680b7a67c18994c45d70643bc608b7485 |
| STAGING_CONTRACT.md | 26716 | 1f40e639370cb5c28e233bac6fff526e8450f0d698411ad088f659ea8db399df |
| BRAIN_UPDATES_DRAFT.md | 5395 | 13ed1a9bec9a955fc455e54098bb820ad190b08b39ef297ffaf3bac5e8d4151b |

### mock\

| File | Bytes | SHA256 |
|---|---:|---|
| mock\Credit Union Industry Spending Data (MOCK).xlsx | 33308280 | f7349527e8bc063eea07ca071b39ea861fdf75ae3c17c461c8ce7cdf988ca7f6 |
| mock\Credit Union Industry Spending Data (MOCK).xlsx.receipt.json | 25303 | 81e6f9ffe84010fed01124e281e98da0b4eb18f28886eb2da77e092904098528 |

### patches\

| File | Bytes | SHA256 |
|---|---:|---|
| patches\APPLY_ORDER.md | 8881 | f4c09ea4a49df3b49c48d9e50b6bf7929c594eace26314235bfe77c1c8274dc4 |
| patches\P1-tidy_stage-new.patch | 65871 | 8030f13052af373b25a6ec26836e4b6c4065dd2318068fb525305ec1bb1f78c4 |
| patches\P2-exporter-hook.patch | 8281 | 7a6b3850471f98205cc0be9229056562cf27a5560bdd1375305cf6f132682050 |
| patches\P3-fec_beneficiary-mappings.patch | 2001 | 386650c3a80aac477636168dfa7c10dff9c87fe8c90a6d26e31ac42f950c23be |
| patches\P4-enrich-staging.patch | 10530 | a6ae6095dc5ff41d9aa8c561f0f7bd2fe6a6eca96ed3b827aaae7d6e8951895d |
| patches\P5-build_industry_report.patch | 14511 | a43569e47cb12ef276635fb4774b940d1f2966711d7eccc938bbc4e9dc6a0fc5 |
| patches\P6a-server-catalog.patch | 1789 | 1ee831bb1f6abaad325f4e7a850b2dfc26414bbfce72b0442892e3618376c25d |
| patches\P6b-contribution_data.patch | 2886 | bfc3826050f652bc55bf30ec264516b797e6d17b018864695d3344f58dbd06d3 |
| patches\P6c-report_insights-split.patch | 2147 | 9c8a6e65e83efddf9eb38e51e6eecf05a7739290154ed3ba3b489e7af699e1b4 |
| patches\P7a-test_tidy_stage-new.patch | 30510 | bf424faa602a8dd5ca775f30cd879148b8c266fec55da16e58ad8627cc6a8103 |
| patches\P7b-test_report_insights.patch | 5125 | 52d2203282652f9292d8345d656f2cbcc279f50784afb81520f819c10b1a82bc |
| patches\P7c-test_report_directory_console.patch | 2319 | 37ee6ee2a089792cb40ab441e6a6ec63f44f7ec783ebecc7f9799ea3bc43d493 |
| patches\P7d-test_contribution_data.patch | 3735 | ffc432140501ddb5cebe83aaea9f37e7f29b01f5faa31c1b243847e5d38f5447 |
| patches\P7e-Test-MentatWorkbookBuilderGuards.patch | 3263 | e65f82674377080bc354e842957183a263cfb26389756562d3dfde766339915d |
| patches\P8-build_tidy_workbook-new.patch | 51246 | 80f6bcbc6bd11b5d197a664c363d61191dd2d1f5001415378683ee83e464d76b |
| patches\P8b-test_tidy_workbook-new.patch | 17464 | 0adbf8acfab67c8bba606edce9bbacf94d17a3d85c54422ad4ef1d803da5261f |

### receipts\

| File | Bytes | SHA256 |
|---|---:|---|
| receipts\A_RECEIPT.md | 32503 | fb5dce236911eb092364573a6209360255c5f7bd22538c44874c1d01a0a7858b |
| receipts\B_RECEIPT.md | 39643 | 4961c3b4caee4f90bb2083cb6e1b3424aa158e7aef262a87f8d61d1aaa77bb1c |
| receipts\VERIFY_A.md | 10371 | 1c61140ce07570ac9274c819069e42547e644b4ec292157da22004334ae28f8a |
| receipts\VERIFY_B.md | 12448 | 9c2b9124ff631fbac69522f08cf984cad857fbead9a1132627874e3ac23f09c0 |
| receipts\VERIFY_B2.md | 8174 | 86581191f0c20bff65ad81e9d71c52290c19510e834badb709c9edcf3494ff7a |
| receipts\A_PROGRESS.md | 9340 | b5afa3968fafd3a2b3b35b4ba77ec49fa7d7f6bdb813f2618069cce2314ff12b |
| receipts\B_PROGRESS.md | 11858 | f2c16549465abac2b410a96bd17ed3421df95d45c04c30ef53522f0d54b3e275 |

### scripts\

| File | Bytes | SHA256 |
|---|---:|---|
| scripts\build_tidy_workbook.py | 50681 | 7afee68cc4577e2687165735dd2753971e3e053235358686ee61455a3f8caf75 |
| scripts\test_tidy_workbook.py | 16864 | 6ffb54325dbc2d5e92c46f06e4d812cdb20a38d8f0851bde3a7919c1a135f64f |
| scripts\tidy_lint.py | 12215 | 95af617498f03b04dc46ae8f9aaf44dd5135a4fe56c45618db13f7567a3e883a |
| scripts\payload_to_stage.py | 42248 | 46f73f765dbac0c249d18e7662bb8746b2f4ebb88b06c633cc568d39f4123a1e |
| scripts\reader_check.py | 7572 | 5ab6c55032778e43bdb0ab55e46c05c09d6af2adf496a95e48f7fccdde760129 |
| scripts\negative_control.py | 3479 | 102a3087e2e4c42d5fde77fc7beddff39d674b821de9a37ad2e07d5d1778ffd9 |

### evidence\

| File | Bytes | SHA256 |
|---|---:|---|
| evidence\laneA_overview_lint.txt | 9917 | 1f79443ade200ebc45787832f45eece7bb303a5db486bdb7ab779a4ece7de9a6 |
| evidence\reader_check.txt | 1101 | 548f48b6ffcc2640a13d97837d20c160ba234f5ccda5f72608affdd47b84bd6e |
| evidence\negative_control.txt | 1772 | 082499f434f9d69968898537dd47e9daf6966ae02f0dbe05649e84cd3ccc3bc4 |
| evidence\NEGATIVE CONTROL (should not exist).xlsx.receipt.json | 25449 | f486bb66aea5fac34f0d7c349686059be55ceabbe4226e1387172b63013943e6 |

38 files listed (plus this README).

---

## Addendum 2026-09-15 — the W9 ruling and the first live scratch run

**Paul's ruling: W9 `no_multivalue_cells` is an INCLUDE-LIST of categorical dimension
columns, not "every text column except an exempt list."**

### Why
The first live run of this lane's code — a Credit Union export against
`.cache\receipt-metadata-repair-20260910\credit_union\mentat.db` — refused to publish on
two rows that turned out to be false positives:

| sheet / column | rows | the actual value |
|---|---:|---|
| Contributions / Receipt Type | 6 | `JFC TRANSFER: SAVE AMERICA JOINT FUNDRAISING COMMITTEE; 2021 AGGREGATE` |
| Downstream Activity / Source Committee | 78 | `MADISON PAC; THE` |

Neither is a packed multi-value cell. `MADISON PAC; THE` is one real FEC committee name with
an inverted article. FEC names and filed descriptions legitimately contain `;` and cannot be
enumerated in advance, so an exempt list can never be complete. A packed `a; b` value, by
contrast, can only arise in a column our own derivations write — a small, closed set.
**This also falsifies A_RECEIPT deviation D3's measured claim** that `ownership_status` is the
only `;`-bearing column in the staging store: true of the 2026-09-08 dataset, false on the
first different database.

`build_tidy_workbook.py` now carries `MULTIVALUE_CHECKED_HEADERS` (33 categorical headers);
the old exempt list is retained as `MULTIVALUE_EXEMPT_HEADERS_DOC`, documentation only.
`tidy_lint.py` mirrors the same constant — the two must stay in step.
`Traversal Status` moved from the exempt list into the checked list; it had 0 rows in this run
(`transfer_paths` was empty), so that promotion is not yet verified against real data.

### Run result (scratch copy, nothing published)
Credit Union, on a scratch copy of the 09-10 hydrated database with the 4 gate-refused rows
deleted (see `DRYRUN_RECEIPT.md`; the book is **not** a valid CU artifact and must never be
published). R export exit 0 in 269.5 s with 9/9 EXPORT GUARDS passing, including
`[PASS] tidy_reconciliation ... and hold unique keys` — which is the first time the amended
seven-column `downstream_activity` key (contract amendment D2) has run against a real export.
`enrich_downstream.py --staging` exit 0. Writer **exit 0, 149 s, 17 sheets, 84,588 rows**,
**90/90 checks pass** (1 informational skip: `overview_cycle_totals`, no Overview because
`@oai/artifact-tool` is not installed on this box). Tableau lint `PASS - no findings`. Reader
check with the live app modules: all assertions passed, `_workbook_source` returns the scratch
database sha. Data book sha256
`2e690fb1b65ca09e48ee24f2106a24ae6ab89785ee47a0de1d2ffd183e2ad9fd`, 18,286,810 bytes.

### The mock in `mock\` was produced by the PRE-FIX writer
Its values are unaffected: every `no_multivalue_cells` row in the mock's own receipt passed
under the old exempt-list rule, so the include-list change would not have altered a single
cell of it. The mock is kept as-is.

### Manifest rows superseded by this addendum
The SHA256 table above is from 2026-09-14. These five entries are now stale; the current
values are:

| File | Bytes | SHA256 |
|---|---:|---|
| patches\P8-build_tidy_workbook-new.patch | 54256 | a5c26036c698ae05b5fe822459172757ac5bcd8ba3b2a864ab477848210c4f6e |
| patches\P8b-test_tidy_workbook-new.patch | 20870 | 8907d94f269b95821e292d52da75e3db1c8bee807cd7f38a080dbbe5c9ebb617 |
| scripts\build_tidy_workbook.py | 53627 | e037281051120f4c1b795e56d24f885a5a93d855c417ba8f51e37c65cdf333b1 |
| scripts\test_tidy_workbook.py | 20269 | 90c249b345c357ae5fdf56f99ccb719c3be3ba4161638cae890ae888dabf0934 |
| scripts\tidy_lint.py | 13943 | 1e679d9eca87ebf020897d34ea6be3062572b5683cea4051cd9bb3853d685fb2 |

`scripts\test_tidy_workbook.py` is now the TREE copy (repo import convention) rather than
Lane A's original, and carries the two new W9 cases. `tests\test_tidy_workbook.py` in the tree
runs **13 tests, OK**.
