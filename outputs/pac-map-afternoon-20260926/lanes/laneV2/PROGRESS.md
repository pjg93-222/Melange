# Lane V2 PROGRESS: verify and package the 09-26 afternoon change set (lane-v2-20260926)

Status: DONE, 2026-09-26. Repo C:\Users\pgoff\Mentat, branch codex/mentat-crypto, HEAD fadd2c751 (the morning's
Z6, route A; the mirror is at the same sha). No git write in the live repo: every git call there was read-only
and `status`/`diff` ran with `--no-optional-locks` (the live index file's mtime is still 16:53:55 UTC, Paul's
apply). No test ran in the live tree. Nothing was deleted (one scratch file of this lane, pm\rules_C7.json,
was created and removed within the same minute). Port 8806 untouched; no server restarted. The only write in
C:\Users\pgoff\Mentat is the kit folder outputs\pac-map-afternoon-20260926 (untracked, outside mentat/).
Work folder: laneV2\pm\ (laneV2\ also holds the early-morning lane V2's files, left as they were).

## 1. Inventory

- `git status --porcelain=v1 -uall` (live): 73 tracked ` M` (72 under mentat/ plus
  audits/mentat_failings_20260915/contracts/flow.json) and 2 new files under mentat/
  (tests/test_hawaii_inset_clip.py, tests/test_studio_busy_mark_browser.cjs); nothing untracked under the
  contracts. The other 1,099 untracked paths are outside mentat/ (other owners), as in the morning.
- Receipts: 125 live writes over 87 files (J2 19, J3 14, S2 7, L2 42, L3 33; L2/L3 scratch rows and the J2/J3
  mirror receipts are not live writes and were left out).
- All 87: the latest recorded sha256 equals the file on disk; every file's writes chain (each sha_before =
  the previous sha_after): 0 breaks.
- Every first pre-image is a known state: 50 = the bytes the morning kit tested (its commit_set.json), 8 = the
  HEAD blob, 10 = the HEAD blob in CRLF form, 5 = the HEAD blob with mixed line endings (checked on the first
  writer's byte-exact backup), 2 new files, 12 = the inputs the morning supplied (laneZ export_B). No
  unrecorded writer touched these files before the lanes.
- Claimed by a receipt but not in status: 12 files, the gitignored geo v2 detail tier that L2 (AK x7) and L3
  (HI x5) rebuilt (`mentat/app/geo/.gitignore:12 v2/albers/detail/`). Not committed. The committed
  v2/index.json lists their new sha256, so the export was supplied their live bytes (below).
- Changed but claimed by no receipt: NONE. Nothing had to be left out for that reason.
- Assignment: C7 19, C8 7, C9 49 = 75 paths, each in exactly one commit. Only METHODOLOGY.md has writers from
  two commits' lanes (L2 line 3 at 17:16 UTC, then J2 and J3); it goes to C7 whole, as the brief says.
Evidence: pm\inventory.py, pm\inventory.json.

## 2. The three commits (throwaway clone laneV2\pm\clone)

Clone: `git clone --no-local --depth 1 --branch codex/mentat-crypto -c core.autocrlf=false
file:///C:/Users/pgoff/Mentat` at fadd2c751 (tree 89977f4e = Z6); origin removed; hooks -> an empty folder;
user Paul Goff <goff0070@umn.edu> (the live repo's configured identity, which made Z1-Z6). For each commit:
the live bytes of its files copied in after a drift check (live sha256 = the receipts' latest, before and
after the copy), staged with `git -c core.autocrlf=true add -f` (Paul's default add; the morning plan's 6.1),
the staged list checked to be exactly the commit's list, committed with laneV2\messages\Ck.txt. After the C7/C8
own-export runs passed, the three commits were re-made with the final messages (their closing lines name those
runs and credit J3's replay for C7's figures) by `git commit-tree` on the SAME trees (pm\rebuild_messages.py;
the first versions 07554a9e / 4116ac74 / 5158bb88 and messages_v1\ are kept).

| # | tested commit (clone, final messages) | tree | files | diff | blobs vs working tree |
|---|---|---|---|---|---|
| C7 Count money unless it is proven counted twice | 2599c2aabd4674a5f0e6d9897ccc50a9c9e84321 | eed2d401519229f38654a6d0a45c68a18422d86a | 19 | +908 / -94 | 12 identical, 7 CRLF-only |
| C8 Name split workbook sheets by election year | 4a33efce196cb6d26b722d45985d017346d250bc | d073a56f6194a0e9c040235013e34c626a3bc6ed | 7 | +317 / -20 | 1 identical, 6 CRLF-only |
| C9 Fix the Alaska and Hawaii map insets, the busy canvas and test temp folders | f20e502e211738072171509896c7925301f76c40 | aeab81ad2a3abddb5355d31b8f43faf07e1fad16 | 49 (2 new) | +1,457 / -358 | 32 identical, 17 CRLF-only |

- C7: audits/mentat_failings_20260915/contracts/flow.json; mentat/METHODOLOGY.md (with L2's line 3);
  R/collect.R, R/report.R, R/schema.R; app/flow_data.py; inputs/fec_receipt_rules.json;
  tests/fixtures/memo_redisclosure_cases.json; tests/test_cross_reference_engine.py, test_export_memo_reason.R,
  test_flow_route.py, test_memo_redisclosure.R, test_memo_redisclosure.py, test_pac_evidence.py,
  test_receipt_roles.R, test_rules.R; tools/cross_reference_engine.py, tools/export_crypto_spending_data.R,
  tools/pac_evidence.py.
- C8: app/chart-studio-core.js, app/report_insights.py, app/tests/chart-studio-core.test.js,
  tests/test_report_insights.py, tests/test_tidy_workbook.py, tests/test_worksheet_not_traced.py,
  tools/build_tidy_workbook.py.
- C9: README.md; app/chart-studio.js, app/map-layers.js, app/tests/map-layers.test.js; 27 geo files
  (geo/cd116, cd118, cd119, zcta_points; sld/index, sld/upper and lower AK and HI; v2/index; v2/albers hex25,
  hex50, hex/AK/hex10, hex/HI/hex10; national cd116, cd118, cd119, county, state, AK place/sldl/sldu/tract/zcta,
  HI sldl/sldu/tract); tools/build_district_geo.py, build_geo_layers.py, build_state_legislative_geo.py,
  build_zip_centroids.py; tests/test_district_geo.py, test_geo_v2_alignment.py, test_state_legislative_geo.py,
  test_zip_centroids.py, NEW test_hawaii_inset_clip.py; browser suites test_evidence_map, test_evidence_map_interaction,
  test_studio_board, test_studio_industry, test_studio_strip_removed, test_ui_cleanup (L2/L3),
  test_evidence_panes, test_navigation_scope (J3), NEW test_studio_busy_mark.
- Checks: the series diff (fadd2c751..C9) equals the live `git diff` numstat for all 73 tracked files, plus the
  two new files; the clone's `git status` (autocrlf=true) is empty after C9. inputs/fec_receipt_rules.json
  changes only in C7, and its C7 blob is byte-identical to J3's final (ad8b954f); `git log --all -S'"version": 7'`
  on the live repo finds no commit, so "v7" names one file in history.
- Messages: laneV2\messages\C7.txt, C8.txt, C9.txt (LF, ASCII, subject + prose, each ending with the
  Co-Authored-By line). C7 quotes Paul's 09-26 rule, keeps H1/H2/H3 = No, records F13 back to "dated on or
  before" and bare NON-CONTRIBUTION counted and flagged, and says METHODOLOGY carries L2's header line. C8
  cites S1 = Yes. Each lists its re-pins for Paul to ratify.
Evidence: pm\build_commits.py, pm\commits.json, pm\paths_C7/C8/C9.nul.

## 3. Verification on a clean export

Export (lane Z's method, D-048 / DE-031): `git -c core.autocrlf=false -c core.eol=lf archive <C9> mentat
audits/mentat_failings_20260915/contracts` to a tar, extracted to laneV2\pm\export_C9, every file's blob id
compared with `git ls-tree -r` both ways: 1,123 files (Z6's 1,121 + the 2 new), 0 missing, 0 extra, 0 blob
mismatches; the 75 files vs live: 45 identical, 30 CRLF-only, 0 different (pm\export_C9_verify.json).
Inputs supplied by name as lane T did (pm\supply_inputs.py): 2,032 files unchanged since lane Z hard-linked from
laneZ\export_B after a re-hash (2.07 GB); the 12 AK/HI detail-tier files L2/L3 rebuilt COPIED from live (the
committed v2/index.json lists their new sha256); 0 refused.
Runner: lane T's run_matrix.py (RAM gate changed to this lane's rule: >= 2.5 GB, 30 s sleeps, <= 20 min), one
suite per process, venv Python, PYTHONDONTWRITEBYTECODE=1, groups one at a time, free RAM checked before each
(4.2, 5.2, 5.6, 6.6 GB). During the Python group other sessions' processes (the sector-growth Rscript at ~10 GB,
the 8841 staffer server at ~7 GB) pushed available RAM to 0.7 GB for about a minute; the runner's gate held
test_geo_v2_assign for 30 s (and, later, one browser suite for 30 s). No suite was skipped for memory.
The browser suites ran 3-6x slower than lane T's (about 60-120 s each instead of 3-20 s): other sessions'
Chrome and node processes were running on the same machine. No suite timed out; two printed their own
teardown notice "browser.close() exceeded its 10000/20000 ms bound" AFTER "ALL 23/17 STEPS PASSED"
(test_evidence_map_interaction, test_navigation_scope), as lane J3 saw under load.

| Suite | Z6 baseline (lane T) | C9 export (lane V2) | Difference, explained |
|---|---|---|---|
| Python modules (venv) | 128/130 (1,759 tests, 15 skipped, 1 failure) | 129/131 (1,787 tests, 15 skipped, 1 failure) | +1 module test_hawaii_inset_clip (L3, 5 tests, passes). +28 tests: test_flow_route +7 (J2), test_pac_evidence +4 (J2, J3), test_memo_redisclosure +1 (J3), test_cross_reference_engine +1 (J2), test_tidy_workbook +5, test_report_insights +2, test_worksheet_not_traced +1 (S2), test_district_geo +1, test_geo_v2_alignment +1 (L2), test_hawaii_inset_clip +5 (L3). No status changed. |
| node --test app/tests | 619/619 | 622/622 | +3: chart-studio-core (S2), map-layers FRAME / Alaska (L2), map-layers Hawaii clip (L3) |
| cjs | 14/14 | 14/14 | none |
| R testthat scripts | 32/32 | 32/32 | none (the J2/J3 R tests are in existing scripts) |
| PowerShell | 6/6 | 6/6 | none |
| render --check | pass | pass | none |
| browser (all suites, one at a time) | 50/50 | **51/51** | +1 new suite test_studio_busy_mark (L2, 4/4 steps). Every baseline suite ran and passed; test_graph_racf skipped its single test in both runs (it needs a console on 8827). No new %TEMP% mentat-* folder was left by any suite. |

The two Python reds are the baseline's two, unchanged in kind:
- test_state_legislative_geo, 1 of 25: `AssertionError: 218860 != 218861 : sld/upper/AK.json` (baseline
  `149571 != 149572`). The Alaska rebuild moved the pinned number, not the cause: sld/index.json records the
  CRLF-checkout size of EVERY one of its 102 files (each is one JSON line ending CRLF in a checkout), and an
  eol=lf export writes each 1 byte shorter. Measured on both exports: claim - export size = 1 byte x 102 files,
  Z6 and C9 alike. upper/AK is simply the first file the test checks. Green on a CRLF checkout (L2/L3 ran it
  live: 25 OK). Proposed fix (Paul's call, not done): have the builder record the LF (blob) size and the test
  compare `len(bytes.replace(b"\r\n", b"\n"))`, or mark mentat/app/geo/**/*.json `-text` so checkouts keep the
  blob bytes; either re-pins 102 sizes.
- test_split_telecom_workbook: "NO TESTS RAN" (a pytest-style module; the venv has no pytest), as in the
  baseline.

C7 and C8 on their own (beyond the brief; their trees are new combinations): exported the same way
(C7 1,121 files, C8 1,121; 0 missing / extra / mismatched; the later commits' files at fadd2c751's blobs),
inputs supplied from lane Z's copies only (the bytes fadd2c751's v2/index.json lists), then:
- C7 export: node 619/619 (C7 changes no node test); R 8/8 (test_memo_redisclosure, test_receipt_roles, test_rules,
  test_export_memo_reason, test_report, test_tidy_stage, test_raw_contribution_columns, test_reconcile); Python 21/21
  modules, 316 tests, 0 failures, 0 errors, 0 skipped (J2/J3's py-core, py-flow, py-downstream sets and extra sweep;
  test_flow_route 38 tests including IndustryRefunds on the Banking payload).
- C8 export: node 620/620 (+1, S2's chart-studio-core test); Python 8/8 modules, 116 tests, 0 failures
  (test_tidy_workbook, test_report_insights, test_worksheet_not_traced, test_raw_contribution_columns,
  test_transfer_paths_contract, test_report_receipts_streamed, test_graph_not_traced, test_graph_data).
Evidence: pm\runs\C7_only, pm\runs\C8_only, pm\groupIntermediates.out.

Independent check of C9's claim "every feature outside Alaska and Hawaii is unchanged" (fadd2c751 vs C9,
pm\geo_claim_check*.py): cd116/118/119 484 records each, v2 national cd116/118/119 434 each, county 3,190,
state 50, v2/index 808 entries outside AK/HI: 0 changed; zcta_points: the 245 changed points are all ZIP
995xx-999xx (Alaska); hex25: 1,411 changed all AK + 6 removed HI; hex50: 425 AK + 1 HI changed, 6 HI removed.

## 4. The kit: C:\Users\pgoff\Mentat\outputs\pac-map-afternoon-20260926\

- cPlan.bundle (714,478 bytes; refs/heads/cPlan = the tested C9 f20e502e; requires fadd2c751), apply_plan.ps1,
  commit_set.json (base, tested commits and trees, and all 75 files with sha256, commit, blob, mode, kind),
  plan_trees.txt, paths_C7/C8/C9.nul, messages\C7..C9.txt, README.md (check, apply, confirm, undo, what to
  rule on), lanes\ (RECEIPT.json + PROGRESS.md of J2, J3, S2, L2, L3 and V2), MANIFEST.sha256.
- apply_plan.ps1: check mode by default, every git call `--no-optional-locks` (branch, HEAD = fadd2c751, no
  index.lock, nothing staged, bundle verifies, the 75 files' sha256 unchanged, every planned file shows in
  status, nothing else under mentat/ or the contracts (NOTE line if there is), messages exist). `-Execute`:
  fetch the bundle, check the fetched tip and each tree against commit_set.json, `git commit-tree` x3 with
  messages\Ck.txt (configured user), final tree check, `update-ref refs/heads/codex/mentat-crypto <new>
  fadd2c751`, `read-tree`, `update-index -q --refresh`, and a status check. No hook runs; no working-tree file
  is written; the mirror push is by hand (the README says so).
- Undo (README): `git -C C:\Users\pgoff\Mentat reset --mixed fadd2c751e1936c8924cab8c060d28f54837909b`.
- Check mode against the LIVE repo, final kit: every line OK, "Checks passed", rc 0 (pm\real_check_final.out;
  it also passed three times on the first kit, pm\real_check.out holding the first); the live index file's
  mtime unchanged by any of them.
- -Execute rehearsed on simC with the final kit: a fresh depth-1 clone checked out under the system
  autocrlf=true with the 75 live files copied in (status identical to live: 73 ` M`, 2 `??`): check rc 0,
  execute rc 0, three commits on fadd2c751 whose trees are the tested trees, messages equal to
  messages\Ck.txt, author and committer Paul Goff, `git status` EMPTY, no planned file rewritten on disk
  (pm\sim_rehearsal_simC.json/.out). The first kit passed the same on simB (and simA, whose record's
  before-status counts read 72 on both sides because that helper stripped the first porcelain line's leading
  space; fixed).

## 5. Read-only measurement

Method. Databases found as the console finds them (app/contribution_data.py `_sources`, which reads what
tools/build_industry_report.ps1 stamps and caches): report directory from config/report-directory.json ->
"<Industry> Industry Spending Overview.xlsx" -> its "Source DB SHA-256" -> .cache/industry-report/<slug>/
manifest + payload (database_sha256 must match) -> the payload's database_path, or, where that file is gone,
.cache/receipt-metadata-repair-20260910/<slug>/mentat.db.hydration.json (source_sha256 must match) -> its
output (pm\resolve_dbs.py, pm\dbs.json). Every -wal is 0 bytes and the databases are unchanged since 09-10,
so each was opened `mode=ro&immutable=1` with `PRAGMA query_only=ON` (no lock, no -wal/-shm access; the
db/-wal/-shm sizes and mtimes were compared before and after: 0 changed). Both receipt tables
(contributions, corporate_giving) are read; a SUB_ID in both counts once. Captions are matched the way
R/collect.R `fec_receipt_role()` matches them (upper case, every run of non-alphanumerics -> one space,
trimmed) on the receipt description (receipt_type_full); the rule also fires on memo_text, so memo-only
matches are counted separately. Positive control: the same matcher finds the bare label J3 changed,
"NON-CONTRIBUTION", in Crypto: 5 rows, $35,045,000 (Foris DAX x4 + the Petkovich row) (pm\measure_controls.py).
Identity (pm\db_identity.py): Banking's file hashes to the workbook's pinned Source DB SHA-256 (4abdea58...).
The seven hydrated files do NOT hash to their hydration manifests' output_sha256: each database file was
written at 20:16-20:17 on 09-10, after its manifest (17:15-20:06). The console never checks that field (it
hashes the file itself, contribution_data.py:247), so these are the files it reads; whether their logical
content changed after hydration was not examined (a pointer, outside this brief).

### Databases (resolved as the console resolves them)

| Industry | Database (under mentat\) | Route | contributions / corporate_giving rows |
|---|---|---|---|
| Banking | .cache\report-repairs\banking-20260910\data\mentat.db | payload database_path | 783,808 / 67,421 |
| Community Banks | .cache\receipt-metadata-repair-20260910\community_banks\mentat.db | hydration output | 4,293 / 368 |
| Credit Arms | .cache\receipt-metadata-repair-20260910\credit_arms\mentat.db | hydration output | 424,988 / 10,695 |
| Credit Union | .cache\receipt-metadata-repair-20260910\credit_union\mentat.db | hydration output | 56,078 / 11,232 |
| Crypto | .cache\receipt-metadata-repair-20260910\crypto\mentat.db | hydration output | 13,326 / 1,518 |
| Fintech | .cache\receipt-metadata-repair-20260910\fintech\mentat.db | hydration output | 41,082 / 45,754 |
| Property & Casualty Insurance | .cache\receipt-metadata-repair-20260910\property_casualty_insurance\mentat.db | hydration output | 329,509 / 31,579 |
| Telecom | .cache\receipt-metadata-repair-20260910\telecom\mentat.db | hydration output | 746,070 / 63,633 |

### "NON-CONTRIBUTION AMOUNT" (unique SUB_IDs across both tables)

| Industry | As receipt description: rows | dollars | In memo text only: rows | dollars |
|---|---|---|---|---|
| Banking | 0 | $0.00 | 241 | $4,420.00 |
| Community Banks | 0 | $0.00 | 0 | $0.00 |
| Credit Arms | 0 | $0.00 | 0 | $0.00 |
| Credit Union | 0 | $0.00 | 0 | $0.00 |
| Crypto | 0 | $0.00 | 0 | $0.00 |
| Fintech | 0 | $0.00 | 0 | $0.00 |
| Property & Casualty Insurance | 0 | $0.00 | 0 | $0.00 |
| Telecom | 0 | $0.00 | 0 | $0.00 |

#### Banking: 241 rows, $4,420.00 (memo text; receipt description blank)

- FEC transaction types: 10 (Contribution to a Super PAC, hybrid PAC or non-federal account from an individual, partnership or LLC): 241 rows, $4,420.00
- Form / line: F3X line 17: 241 rows, $4,420.00
- Recipient committees: C00580068 PROGRESSIVE TURNOUT PROJECT: 241 rows, $4,420.00
- Spellings as filed: 'NON-CONTRIBUTION AMOUNT' x241
- Receipt description beside it: '' x241
- Memo codes: '' x241
- Companies (match status): Wells Fargo Bank NA: 241 rows, $4,420.00 (accepted 241)

Three samples (the three largest amounts):

| SUB_ID | Contributor | Amount | Date | Committee | Form / line | Type | Memo code | Memo text |
|---|---|---|---|---|---|---|---|---|
| 4010520231665591797 | TIANO, ALICE | $100.00 | 2022-11-13 | C00580068 PROGRESSIVE TURNOUT PROJECT | F3X 17 | 10 | (blank) | NON-CONTRIBUTION AMOUNT |
| 4010520231665591943 | TIANO, ALICE | $50.00 | 2022-11-27 | C00580068 PROGRESSIVE TURNOUT PROJECT | F3X 17 | 10 | (blank) | NON-CONTRIBUTION AMOUNT |
| 4010520231665591903 | TIANO, ALICE | $50.00 | 2022-11-23 | C00580068 PROGRESSIVE TURNOUT PROJECT | F3X 17 | 10 | (blank) | NON-CONTRIBUTION AMOUNT |

How the committed R rules classify them (role_check.R on the C9 export; counterfactual in memory only):

```
COMMITTED RULES (C9): 
            role countable  rows dollars
          <char>    <lgcl> <int>   <num>
1: other_receipt     FALSE   241    4420
  flagged receipt_role_unverified: 0 
COUNTERFACTUAL (caption removed from non_giving_exact_pattern, in memory only): 
                       role countable  rows dollars
                     <char>    <lgcl> <int>   <num>
1: unverified_other_receipt      TRUE   241    4420
  flagged receipt_role_unverified: 241
```

### The other exact descriptions (non_giving_exact_descriptions), per database

Rows = receipt description matches; memo-only = the description is in memo_text only; F3X line 17 = the rows (of either kind) where collect.R lets the caption decide the role. Descriptions not listed matched no row.

| Industry | Description | Rows | Dollars | Memo-only rows (dollars) | Of all: F3X line 17 rows (dollars) |
|---|---|---|---|---|---|
| Banking | ADJUSTMENT FOR PAST MUTUAL FUND INVESTMENT ACTIVITY | 1 | $166,421.58 | 0 | 0 |
| Banking | REIMBURSEMENT INTEREST | 2 | $50,872.66 | 0 | 2 ($50,872.66) |
| Banking | INVESTMENT INC/LOSS | 1 | $-37,440.30 | 0 | 0 |
| Banking | INVESTMENT INCOME LOSS | 1 | $-33,754.17 | 0 | 1 ($-33,754.17) |
| Banking | NONCONTRIBUTIONS ACCOUNT - INTEREST | 1 | $27,621.43 | 0 | 1 ($27,621.43) |
| Banking | INCREASE IN MARKET VALUE | 1 | $25,113.58 | 0 | 0 |
| Banking | NET INVESTMENT EARNINGS/LOSS | 1 | $-20,843.46 | 0 | 0 |
| Banking | OCTOBER INTEREST | 1 | $15,076.53 | 4 ($1,936.14) | 5 ($17,012.67) |
| Banking | INTEREST, DIVIDENDS, CAPITAL GAIN (LOSS) | 3 | $9,296.67 | 0 | 3 ($9,296.67) |
| Banking | INTREREST | 2 | $9,252.16 | 0 | 1 ($9,130.35) |
| Banking | REFUND | 15 | $6,224.76 | 8 ($2,765.79) | 1 ($216.27) |
| Banking | STOP PAY | 1 | $5,000.00 | 0 | 0 |
| Banking | INVESTMENT EARNINGS, NET OF FEES | 1 | $3,801.94 | 0 | 1 ($3,801.94) |
| Banking | INTEREST AND GAINS NET OF INVESTMENT FEES | 1 | $3,591.24 | 0 | 1 ($3,591.24) |
| Banking | MUTUAL FUND ACTIVITY FOR PERIOD 4-1-26 THROUGH 6-30-26 | 1 | $1,997.75 | 0 | 0 |
| Banking | INTEREST EARNED ON CDS | 1 | $1,861.15 | 0 | 1 ($1,861.15) |
| Banking | INTEREST/DIVIDENDS INCOME PLUS UNREALIZED LOSS ON INVESTMENTS | 11 | $-1,696.44 | 0 | 11 ($-1,696.44) |
| Banking | INVESTMENT INCOME NET OF MGMT FEES | 2 | $1,422.50 | 0 | 2 ($1,422.50) |
| Banking | JANUARY INTEREST | 1 | $1,361.20 | 4 ($1,990.26) | 5 ($3,351.46) |
| Banking | INTEREST FEBRUARY | 1 | $1,262.91 | 0 | 1 ($1,262.91) |
| Banking | PAST INTEREST EARNED NOT PREVIOUSLY REPORTED | 1 | $1,018.34 | 0 | 0 |
| Banking | INTEREST ON INVESTMENT ACCT | 3 | $783.84 | 0 | 3 ($783.84) |
| Banking | INTEREST & LATE FEES | 1 | $266.33 | 0 | 1 ($266.33) |
| Banking | DUPLICATE BANK FEE CREDIT | 1 | $266.29 | 0 | 1 ($266.29) |
| Banking | NTEREST INCOME | 1 | $239.59 | 0 | 0 |
| Banking | SERVICE FEE | 4 | $200.00 | 0 | 4 ($200.00) |
| Banking | ANNUAL SERVICE CHARGE | 1 | $175.00 | 0 | 1 ($175.00) |
| Banking | BANK CHARGE | 1 | $175.00 | 0 | 1 ($175.00) |
| Banking | INTEREST ON BANK ACCT | 2 | $2.29 | 0 | 2 ($2.29) |
| Banking | MONEY MARKET MATURITY PLUS INTEREST | 0 | $0.00 | 1 ($30,795.33) | 1 ($30,795.33) |
| Banking | REBATE | 0 | $0.00 | 1 ($1,000.00) | 0 |
| Banking | BANKING BONUS | 0 | $0.00 | 1 ($1,000.00) | 1 ($1,000.00) |
| Banking | PROMOTION FOR ACCOUNT OPENING | 0 | $0.00 | 1 ($1,000.00) | 1 ($1,000.00) |
| Banking | ONE TIME ADJUSTMENT | 0 | $0.00 | 1 ($-5,698.59) | 0 |
| Banking | REDUCTION OF REALIZED LOSS | 0 | $0.00 | 1 ($2,427.14) | 0 |
| Banking | OFFSETTING BALANCE ADJUSTMENT | 0 | $0.00 | 1 ($855.09) | 1 ($855.09) |
| Banking | SALE OF INVESTMENT | 0 | $0.00 | 1 ($-78,429.50) | 0 |
| Banking | UNREALIZEZD INVESTMENT LOSSES | 0 | $0.00 | 1 ($-187.20) | 0 |
| Banking | UNREALIZEZD INVESTMENT GAINS | 0 | $0.00 | 1 ($1,495.17) | 0 |
| Banking | BANK ERROR | 0 | $0.00 | 1 ($250.00) | 0 |
| Property & Casualty Insurance | REFUND | 30 | $9,720.32 | 9 ($11,050.84) | 2 ($1,607.00) |
| Property & Casualty Insurance | REBATE | 1 | $162.68 | 0 | 0 |
| Telecom | REFUND | 68 | $4,660.77 | 39 ($7,659.83) | 1 ($352.01) |

Per database, all 40 descriptions together:

| Industry | Rows | Dollars | Memo-only rows | Memo-only dollars | F3X line 17 rows | F3X line 17 dollars |
|---|---|---|---|---|---|---|
| Banking | 64 | $239,570.37 | 27 | $-38,800.37 | 53 | $129,509.81 |
| Community Banks | 0 | $0.00 | 0 | $0.00 | 0 | $0.00 |
| Credit Arms | 0 | $0.00 | 0 | $0.00 | 0 | $0.00 |
| Credit Union | 0 | $0.00 | 0 | $0.00 | 0 | $0.00 |
| Crypto | 0 | $0.00 | 0 | $0.00 | 0 | $0.00 |
| Fintech | 0 | $0.00 | 0 | $0.00 | 0 | $0.00 |
| Property & Casualty Insurance | 31 | $9,883.00 | 9 | $11,050.84 | 2 | $1,607.00 |
| Telecom | 68 | $4,660.77 | 39 | $7,659.83 | 1 | $352.01 |

Descriptions with no row in any database: 0

## Risks checked

- Wrong or partial bytes in a commit: every file's live sha256 = the receipts' latest at copy time (before and
  after), staged list = assigned list, series diff = live diff, export blob check 1,123/1,123 both ways, change
  set vs live 45 identical + 30 CRLF-only + 0 different. Not exposed.
- A commit holding a file state that never existed: each file's committed bytes are its final live state; the
  75 paths split into three disjoint sets (METHODOLOGY.md, the only two-commit-lane file, rides whole in C7).
  The trees of C7 and C8 are new combinations (J2/J3 wrote while S2/L2 edits were already on disk), so they
  were exported and tested on their own too (section 3). 
- "v7" naming two contents: rules file only in C7, byte-equal to J3's final; no v7 anywhere in history.
- Line endings: blobs LF, as Paul's default add makes them; apply rehearsed; status empty afterwards.
- Hooks / mirror: plumbing route runs no hook; README tells Paul to push the mirror by hand.
- Drift between test and apply: check mode refuses on any changed planned file, extra NOTE for unplanned ones.
- Test hermeticity: suites ran only in exports under laneV2\pm; inputs hard-linked from lane Z's copies (each
  re-hashed first), the 12 live-changed detail files copied (not linked). Close-out re-hash of every file
  supplied to the C9, C7 and C8 exports (pm\post_checks.py): 0 changed by any suite. %TEMP% mentat-* folders: 58
  before the browser group, 58 after the browser and C7/C8 runs, 0 new.
- Live tree: no git write, no test run there, measurement reads immutable (0 files changed).

## Open for the lead / Paul

1. Apply: Paul runs the kit's check, then `-Execute`, then pushes the mirror by hand (README). Nothing is
   committed yet.
2. Paul's ruling (measured, nothing changed): "NON-CONTRIBUTION AMOUNT" is on no receipt description in the
   eight databases, but it is the memo text of 241 Banking rows ($4,420.00): every one FEC type 10 (the FEC's
   code for a contribution to a Super PAC, hybrid PAC or non-federal account from an individual), Form 3X line
   17, to C00580068 Progressive Turnout Project, attributed to Wells Fargo Bank NA (accepted,
   verified_roster_alias); all 241 are one individual, TIANO, ALICE, $2-$100 each, 2022-08-03 to
   2022-11-28, with a blank receipt description and no memo code. With the
   committed rules they are other_receipt and excluded; with that caption taken out of
   non_giving_exact_pattern (in memory only) they would be unverified_other_receipt, counted and flagged,
   the treatment J3 gave bare NON-CONTRIBUTION.
3. The 40 non_giving_exact_descriptions: Banking 64 rows ($239,570.37) as the receipt description plus 27 as
   memo text only; of all those, 53 rows ($129,509.81) are on Form 3X line 17, where the caption decides the
   role. P&C 31 + 9 memo-only (2 on line 17, $1,607.00), Telecom 68 + 39 (1 on line 17, $352.01); Community
   Banks, Credit Arms, Credit Union, Crypto and Fintech none. REFUND is the widest (113 + 56 memo-only rows).
   Nothing changed; listed for Paul's review of the list itself.
4. Re-pins to ratify: listed in each commit message and in the kit README.
5. Open decisions carried forward: the Hawaii clip extent (L3); METHODOLOGY Version 6 (L2 kept 5).
6. The pre-existing export-only red (sld sizes, 102 files) has a proposed fix above; not done.
7. Rebuilds and restarts stay Paul's: the Crypto workbook (J3's figures), the Data workbooks' split-sheet names
   (S2) on their next build, and any running console (restart to load the new code).

## Evidence index (laneV2\pm\)

inventory.py/.json; build_commits.py, commits.json (commits_v1.json = first messages), paths_C7/C8/C9.nul,
rebuild_messages.py, messages_v1\; export_and_verify.py, export_C9/C7/C8_verify.json, supply_inputs.py,
export_*_supplied.json; run_matrix.py, runs\C9, runs\C9_browser, runs\C7_only, runs\C8_only (results.json +
one log per suite), groupA/R/Py/Browser/Intermediates.out, compare_runs.py/.json, chain_intermediates.ps1/.log;
geo_claim_check*.py/.json/.out; make_kit.py, kit_src\, finalize_kit.ps1/.out, real_check.out,
real_check_final.out, sim_rehearse.py, sim_rehearsal_simA/B/C.json/.out; resolve_dbs.py, dbs.json,
db_identity.py/.json, measure.py/.json/.md, measure_controls.py/.json, nca_rows_csv.py, nca_banking.csv,
role_check.R/.out; post_checks.py/.json; write_receipt.py. Glass Box run lane-v2-20260926.

## Brain drafts (for Paul to apply)

- STATE: 09-26 afternoon change set packaged by lane V2: kit C:\Users\pgoff\Mentat\outputs\pac-map-afternoon-20260926
  (C7 money rules J2+J3 with L2's METHODOLOGY header, C8 split-sheet names S2, C9 AK/HI insets + busy canvas +
  test temp folders L2+L3+J3's two cleanups); tested on a clean export; check mode passes on the live repo;
  NOT applied.
- DEADENDS / correction of the morning plan's wording: test_state_legislative_geo's size check fails on any
  eol=lf export because sld/index.json records the CRLF-checkout size of all 102 SLD files, not only
  sld/upper/AK.json (AK is the first file the test reaches). Would reconsider: if the index records blob sizes.
- DECISIONS pending (Paul): whether "NON-CONTRIBUTION AMOUNT" stays an exact non-giving caption (241 Banking
  rows, $4,420.00, FEC type 10, line 17).
