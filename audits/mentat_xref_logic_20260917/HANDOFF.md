# HANDOFF: xref contradiction-text lane (steps 3-6), 2026-09-17

Everything in this packet is UNCOMMITTED in `C:\Users\pgoff\Mentat\mentat` (branch `codex/mentat-crypto`, HEAD `f0ec60b74` at the time of writing). Nothing was staged, stashed or committed. Paul commits from the patch.

## What changed

Three files, all LF (`git ls-files --eol` shows `i/lf w/lf` for each; the patch scripts preserved that):

1. `tools/cross_reference_engine.py` (+142/-10): rulings D1/D2/D3 and the recipient route. New reason codes `attribution_contradicted_by_text` (exclusion), `company_named_unverified` (counted, flagged), informational `recipient_connected_organization_resolves_to_company` and `role_marker_with_company_named`; new attribution statuses `recipient_supported` and `role_supported`; `analyze()` takes `company_names` and `committee_connected_orgs`. Every existing reason code is still emitted. No new bucket.
2. `tools/run_cross_reference.py` (+60/-8): loads the roster variants + `inputs/verified_employer_aliases.csv` into `company_names`, the FEC committee master field 14 into `committee_connected_orgs`, fingerprints the three `cm.txt` files in `scope.committee_master`, records `scope.attribution_text_test`, writes `excluded_reasons` into `report.json`, prints unresolved/excluded reasons and elapsed seconds at the end of `main()`.
3. `tests/test_cross_reference_engine.py` (+135/-2): five new tests; two near-name PAC assertions re-pinned from `company_attribution_unverified` to `company_named_unverified` (their rows name the company, so D1 puts them in the named flag; the intent "stays queued, not affiliation-supported" is unchanged).

Not touched: `app/server.py`, `app/app.js`, `app/index.html`, `tools/api_company_cycle_fanout.py`, `tools/merge_company_shards.py`, `tools/collect_api_lane.R`, `tools/parallel/*.ps1`, `R/fec_api.R`, `inputs/verified_company_affiliations.json`, the alias CSVs, `app/cross-reference.js`, `tests/test_studio_wording.cjs`. No port was bound. The dead run `state/cross-reference/20260917T174138-ec8ba8ba4523/` was not deleted.

## Receipts

- `receipts/pytest_red.txt`: the seven selected engine tests against the unchanged engine (5 new + 2 re-pinned) fail.
- `receipts/pytest_green_selected.txt`: the same seven pass after the patch.
- `receipts/pytest_green_full.txt`: the four-file suite, `113 passed, 27 subtests passed`.
- `receipts/pytest_baseline_before_edit.txt`: the four-file suite before any edit, `108 passed, 27 subtests passed`.
- `receipts/run_fintech.txt`, `receipts/run_banking.txt`: the runner's stdout (progress lines and the final JSON with summary, unresolved and excluded reasons, elapsed seconds).
- `receipts/before_fintech_reasons.txt`, `receipts/before_banking_reasons.txt`, `receipts/after_fintech_reasons.txt`, `receipts/after_banking_reasons.txt`: per-reason rows and dollars read from each run's ledger (`reason_table.py`).
- `receipts/after_fintech_text_census.txt`, `receipts/after_banking_text_census.txt`: contradicted and named texts per company, route statuses and the D4 register-gap candidates (`text_census.py`).
- `receipts/git_apply_check.txt`: `git apply --check` of the patch against HEAD.
- `receipts/*.py`: the scripts that produced the receipts, copied from the session scratchpad.

## What Paul does next

1. Read `REVIEW.md` sections 4-6 (before/after per reason, the Banking figure against the $54,762,844.05 workbook total, the D4 register gaps, the Fintech variant note).
2. Commit from the patch, explicit paths only (other lanes have uncommitted hunks in shared files; these three files carry only this lane's hunks):
   `git apply --check patches/xref_contradiction_text.patch` then `git apply --index patches/xref_contradiction_text.patch` (or `git add -- mentat/tools/cross_reference_engine.py mentat/tools/run_cross_reference.py mentat/tests/test_cross_reference_engine.py` in the Mentat root) and `git commit` with a message along the lines of "Cross-reference: a row's own text contradicts its attribution; recipient and role routes support it".
3. Add the register data ruled under D4 (`inputs/verified_company_affiliations.json`): C00039305 CITIGROUP INC. PAC - STATE, and the own-PAC-as-donor names listed in REVIEW.md section 6, so those rows move from "unverified funding" to PAC activity on the next run. Consider the alias gaps in section 6 (`CITICORP` and the other contradicted texts that are plainly the company) for `inputs/verified_employer_aliases.csv`.
4. Restart the console (8806) so its cross-reference status line reads the new `latest.json`; the digest is per run and carries no totals (D-040), so nothing else on the tab changes.
5. Optional: re-run Banking after the register data lands; the runner is `python tools/run_cross_reference.py --database <db> --industry Banking --offline` from `C:\Users\pgoff\Mentat\mentat` (the two runs in this packet used `--offline`; both prior runs also made zero FEC requests).

## Known limits

- The recipient route is evaluated for individual rows only (the population of the existing `recipient_is_dated_company_pac` marker); entity rows are decided by their contributor name.
- The whole-token test can be fooled by a variant that is itself a token subsequence of another organisation's name (Fintech `Block Inc` in `H&R BLOCK INC PAC`; `Square Inc` in `FOURSQUARE INC` through the squashed-name rule). Those rows count flagged (the lenient direction); the variant list is Paul's data (REVIEW.md section 6).
- The 4 source-conflicted rows ($375) keep the pre-existing `company_attribution_unverified` handling; the text test does not run on the conflict branch.
- `inputs/fec_committee_master` is untracked in git; the run records the three files' sha256 in `scope.committee_master` instead of copying them into `rules/`.

## The numbers, before and after

Two runs, both `--offline` against the databases their predecessors pinned. Fintech: before `20260911T010907-d7fdb039c080`, after `20260917T190836-4d409860e341` (368.94 s). Banking: before `20260913T074303-bca0ac2b9cd3`, after `20260918T030844-6098810b1ae7` (650.41 s, `exit=0`). `state/cross-reference/latest.json` points at the Banking run.

| Banking | Before | After |
|---|---|---|
| Observed original giving | $72,103,655.70 | $77,054,485.76 |
| Employee giving | $70,446,487.57 | $71,246,149.34 |
| Unverified funding | $1,657,168.13 | $5,808,336.42 |
| PAC activity | $22,774,438.00 | $22,774,438.00 |
| Baseline (accepted-report snapshot) | $133,516,227.27 | $133,516,227.27 |
| Against the published workbook total, $54,762,844.05 | +$17,340,811.65 | +$22,291,641.71 |
| Review queue, rows / gross | 76,197 / $49,929,377.44, of which 36,241 / $37,940,955.71 held at $0 | 46,156 / $16,990,616.89 |
| Excluded, rows / gross | 79,947 / $109,735,911.79 | 109,929 / $142,547,260.34 |

| Fintech | Before | After |
|---|---|---|
| Observed original giving | $9,089,743.52 | $11,050,344.05 |
| Against the workbook / baseline, $9,803,891.31 | -$714,147.79 | +$1,246,452.74 |

The whole Banking movement is the 36,241 rows HEAD was holding at $0 under `company_attribution_unresolved`: 29,816 rows / $32,538,668.49 are now excluded as contradicted, 6,266 rows are counted and re-flagged ($4,962,686.17), and 159 rows / $258,523.95 are settled as non-giving by HEAD's own receipt rules. Observed giving rises $4,950,830.06, which is that release less an $11,856.11 movement outside the held population that belongs to HEAD, not to this patch. Banking's observed giving sits **above** the $54,762,844.05 workbook total, and already did before the change. Tests: `113 passed, 27 subtests passed` on the four-file cross-reference suite against the exact working tree the patch carries.

## Status: UNCOMMITTED

Nothing was committed, staged, stashed or branched. The three changed files are still only in the working tree of `C:\Users\pgoff\Mentat` on `codex/mentat-crypto`:

- `mentat/tools/cross_reference_engine.py`
- `mentat/tools/run_cross_reference.py`
- `mentat/tests/test_cross_reference_engine.py`

`patches/xref_contradiction_text.patch` is 32,211 bytes, LF, ASCII, cut as bytes with a bash redirect from the repo root.

**Two corrections to the sections above, found when the patch was cut:**

1. HEAD is `487589584c33fcc575c52240c9c468ab1f907623`, not `f0ec60b74`. Four commits landed while this lane was running (`494dc133c`, `bd8c65ebb`, `a9ed5c236`, `487589584`). `f0ec60b74` is still an ancestor, and `git diff f0ec60b74..HEAD` over the three files is **empty** - none of the four touched them - so the patch content is unaffected and every figure above still stands. Only the SHA quoted in the write-up was stale.
2. A plain `git apply --check` of the patch **fails**, by construction: the patch was cut from the working tree, so the working tree already contains the change and the check tries to apply it a second time. `receipts/git_apply_check.txt` records all three checks. The two that prove the patch is good both exit 0: `git apply --check --cached` (it applies cleanly to the index, which equals HEAD, so it applies to a clean tree) and `git apply --check --reverse` (it reverses cleanly out of the working tree, so it is an exact and complete description of the change with nothing missing).

## What Paul does next (this list supersedes the earlier "What Paul does next")

The earlier list was written before the patch was cut and tells you to run `git apply --check` and then `git apply --index`. Correction 2 above explains why that fails on the current tree. Use the steps below instead.

1. **Commit by explicit paths.** Do *not* `git apply` the patch on top of the current tree - it will fail as above, because the change is already there. From `C:\Users\pgoff\Mentat`:

   ```
   git add -- mentat/tools/cross_reference_engine.py mentat/tools/run_cross_reference.py mentat/tests/test_cross_reference_engine.py
   git commit
   ```

   Explicit paths matter: other lanes have uncommitted hunks in shared files in this same tree. These three files carry only this lane's hunks. Suggested message: "Cross-reference: a row's own text contradicts its attribution; recipient and role routes support it". The patch is the record of what the three files contain; to replay it on a clean checkout, `git checkout -- <the three paths>` first, then `git apply --index patches/xref_contradiction_text.patch`.

2. **Add the D4 register data** to `inputs/verified_company_affiliations.json` (REVIEW.md section 6, none of it edited by this lane):
   - `C00039305` `CITIGROUP INC PAC - STATE` under Citibank - the one Banking committee the run could only resolve through the FEC committee master, 2 rows / $1,000.00.
   - The companies' own PACs and units appearing as **donors**: 1,298 entity rows / $4,324,780.39, none carrying an FEC committee id, led by `PNC ADVISORS` ($648,198.75), `WELLS FARGO PAC ACCOUNT` ($621,580.67), `WELLS FARGO BANK` ($478,368.88), `JP MORGAN CHASE` ($310,994.69), `JP MORGAN CHASE NA` ($197,361.95), the PNC and Capital One PAC spellings, `CITIBANK N A`, `CITIBANK F S B`, `BANK OF AMERICA STATE AND FEDERAL PAC`, `US BANK CORP PAC`, `TRUIST FINANCIAL CORP FEDERAL STATE LOCAL PAC`. These are the largest lever over the workbook gap: with register records they become PAC activity instead of the company's original giving.
   - Optional alias work in `inputs/verified_employer_aliases.csv`: `CITICORP` / `CITICORP NORTH AMERICA` for Citibank (REVIEW.md 6c), and the Fintech variant note in section 4e (`Block Inc` / `Block, Inc.` as bare Cash App variants match `H&R BLOCK INC PAC`, $1,048,754.00).

3. **Restart the console on 8806** so its cross-reference status line re-reads `state/cross-reference/latest.json`, which now points at `20260918T030844-6098810b1ae7`. The digest is per run and carries no totals (D-040), so nothing else on the tab changes. No port was bound by this lane.

4. **Optional: re-run Banking after the register data lands.** From `C:\Users\pgoff\Mentat\mentat`:

   ```
   python tools/run_cross_reference.py --database "C:\Users\pgoff\Mentat\mentat\.cache\report-repairs\banking-20260910\data\mentat.db" --industry Banking --offline
   ```

   Expect most of the $5,808,336.42 unverified-funding line to move to PAC activity and observed original giving to fall back toward its pre-change position against the workbook. That is a prediction about the next run, not a measured figure - REVIEW.md 5f flags it as such.

The dead run `20260917T174138-ec8ba8ba4523` and the killed Banking run `20260917T191516-1199b40e8c61` (no `report.json`, used nowhere in this packet) were both left in place; nothing under `state/cross-reference` was deleted.

## Register data added, 2026-09-18 (supersedes "What Paul does next" item 2)

Item 2 of the previous list is done, not left as homework. Four records were added
to `inputs/verified_company_affiliations.json` (12 -> 16), each corroborated by a
verbatim FEC committee master line: `C00039305` (Citibank), `C00009639` (Truist
Bank), `C00043489` (Bank of America NA), `C00018036` (US Bank NA). REVIEW.md
section 10 has the master lines, the alias rule, the rejections and the numbers.

Measured, not predicted: Banking re-run `20260918T164949-17cd31b9e70f`
(`receipts/run_banking_after_register.txt`) against `20260918T030844-6098810b1ae7`
moved unverified funding $5,808,336.42 -> $5,653,105.36
(-155,231.06) and PAC activity $22,774,438.00 ->
$22,929,669.06 (+155,231.06); observed original giving
$77,054,485.76 -> $76,899,254.70. Tests
`113 passed, 27 subtests passed in 10.63s` (`receipts/pytest_after_register.txt`).

**Item 4's prediction was wrong.** It expected most of the unverified-funding line
to move; $155,231.06 did. The rest of section 6b is not reachable by adding
missing committees: the ORG rows are `treasury_entity` territory and land in
`corporate_original` rather than PAC activity, and the remaining PAC spellings are
alias work on the twelve existing records. REVIEW.md 10d gives the mechanism with
line references.

Still Paul's calls, all listed with evidence in REVIEW.md 10b and 10e:

1. **`treasury_entity` policy** for the company-unit ORG rows (`PNC ADVISORS`,
   `WELLS FARGO BANK`, `JP MORGAN CHASE`, `CITIBANK N A`, `CITIBANK F S B`,
   `CAPITAL ONE BANK`, ...). These are the bulk of section 6b's
   $4,324,780.39 and they move to `corporate_original`, not PAC activity.
2. **Alias extensions on the existing twelve records** for reported PAC spellings
   the master cannot disambiguate (`PNC PAC FED`, `PNC FEDERAL PAC`, `US BANK CORP
   PAC`, `J P MORGAN CHASE CO PAC`, `BANK OF AMERICA CORP PAC`, ...).
3. **The two Wells Fargo committees** `C00300178` and `C00429852`, whose master
   `CONNECTED_ORG_NM` fields name each other rather than the company.
4. **`C00142596` `BBVA PAC OF THE PNC FINANCIAL SERVICES GROUP, INC.`** - blank
   field 14, no Banking row reports it.
5. **The four misfiled aliases** in 10e.
6. **The 6c alias gap** (`CITICORP`, `CITICORP NORTH AMERICA`) is untouched.

`state/cross-reference/latest.json` now points at `20260918T164949-17cd31b9e70f`, so the console on
8806 shows this run once Paul restarts it. No port was bound and no run was
deleted by this lane.

## Alias fix landed, treasury records withheld, 2026-09-18 (follow-up to the register work above)

**Done.** Three of the four misfiled aliases in REVIEW.md 10e are removed:
`BANK OF AMERICA CORPORATION STATE AND FEDERAL PAC` off `C00364778`,
`U.S. BANCORP POLITICAL PARTICIPATION PROGRAM` off `C00488882`, and the Truist
federal/state/local name off `C00386524`. The 43, 136 and 9 rows that reported those
spellings now cite one correct evidence ID instead of two, with bucket and cents
unchanged (`receipts/alias_fix_verification.txt`). Run `20260918T173505-84f3f46b7351`
reproduces every summary figure of the previous run exactly - all fields equal:
True - which is the intended result for a citation-only change.

**Kept deliberately.** `WELLS FARGO AND COMPANY EMPLOYEES GOOD GOVERNMENT FEDERAL
FUND II` stays on `C00034595`. The committee it really names, `C00300178`, is not in
the register, so 242 rows / $572,500.00 match only through that alias and removing
it would strand all of them. Paul's call: register `C00300178` (its master field 14
names another committee, not Wells Fargo) or leave the alias.

**Withheld: the `treasury_entity` records.** The instructed evidence - Banking
roster variants plus `verified_employer_aliases.csv`, whole-token test - selects
1,328 ORG rows / $4,110,703.75, **3.01x** the workbook's $1,365,262.42 Corporate tier.
Tripwire fired, so nothing was added and `corporate_original` stays
$0.00. The evidence in REVIEW.md 11c is that these
rows are bank interest, not giving: 873 rows / $2,629,439.21 sit on the FEC line
`Other Federal Receipts (Dividends, Interest, etc.).`, 1,250 of 1,328 already carry
`receipt_role = unverified_other_receipt`, and 415 rows / $347,611.99 are
receipts of **federal candidate** committees, which corporate treasury money cannot
lawfully be. The roster test also matched 1,328 of 1,328 rows - no discriminating
power, because naming the company is what put them in the bucket.

Next decisions for Paul, in REVIEW.md 11d:

1. Whether the Corporate tier should be built from receipt evidence (role
   `contribution` + non-candidate recipient + named corporate entity) rather than a
   name test. The role-`contribution` subset is 71 rows / $1,153,768.96 = 0.85x the
   workbook, but $1,000,000.00 of it is a single `BANK OF AMERICA` -> `PIC 2021,
   INC.` row and the rest still holds donor-advised funds, a settlement
   administrator and a coffee shop.
2. `C00300178` (see above).
3. `CITI HEALTH HOME CARE SERVICES` matches the roster variant `Citi` on the
   whole-token test and is not Citibank - worth a roster exclusion before any
   treasury work.

## Treasury register built from receipt evidence, 2026-09-18

Section 11c withheld treasury records because the roster name test selected 3.01x
the workbook. Paul ruled: build it from receipt evidence instead. Done.

**Adjudication** (`receipts/treasury_adjudication.txt`, every row judged
individually): candidate set 51 rows / $1,135,267.13 - role `contribution`,
recipient not a federal candidate committee. **1 accepted, 50 rejected**: 4 rows /
$100,600.00 donor-advised funds, 1 / $308.05 settlement administrator, 15 /
$6,449.60 interest or refunds by their own line label or memo, 30 / $27,909.48
corporate money on a federal contribution line, which is unlawful and therefore a
reporting artefact. A further 20 rows / $18,501.83 never reached adjudication
because their recipient is a federal candidate committee; the Capital One cafe line
and `CITI HEALTH HOME CARE SERVICES` are in that group.

**Accepted:** `BANK OF AMERICA`, Charlotte NC, to `PIC 2021, INC.`, 2021-01-12,
$1,000,000.00, on **FEC Form 13** - the inaugural-committee donation report, which
appears exactly once in the whole Banking corporate feed. Lawful corporate money,
real treasury giving.

**Record added:** one `treasury_entity` for Bank of America NA, `entity_name`
`BANK OF AMERICA`, evidence `fec-receipt-4092420211371961952`. No `entity_id` - a
treasury entity is not a committee. The other nine companies get none.

**Result**, run `20260918T183722-d8f0fb287912`: `corporate_original` $0.00 -> **$1,025,874.75**, unverified
funding down by the same, observed original giving unchanged at
$76,899,254.70. Tests `113 passed, 27 subtests passed in 8.59s`.

**Two things to know before quoting the number.**

1. The corporate line is **71 rows, not one**. `affiliations_for` matches on name
   and never checks `receipt_role`, so the record also pulled in 52 bank-interest
   rows, a transfer and the 17 `BANK OF AMERICA` rows this lane had itself rejected:
   $1,000,000.00 adjudicated plus $25,874.75 (2.5%) carried in on the
   name. A role-aware affiliation test would remove that; it is an engine change,
   not a data one.
2. Against the workbook's $1,365,262.42 Corporate tier this run is **$1,025,874.75, 0.751x**,
   gap $339,387.67. It does **not** land near the workbook. The gap is
   +$101,252.13 for eight companies whose rows this lane rejected as donor-advised
   funds, interest and contribution-line artefacts, +$251,029.90 residual I could not
   reproduce from the database with any of six filters, -$12,894.36 swept
   excess. The residual lives in `R/report.R:2060-2090`, which merges the people and
   corporate feeds and dedups on `sub_id` by `source_priority`; I did not replicate
   that, so I am naming it rather than explaining it away. That is the next
   reconciliation job.

Caveat for the report: the Banking corporate tier is one real row, a single lawful
2021 inaugural donation. It is real money and belongs in the line, but it is not a
distribution and no cross-company comparison should rest on it.
