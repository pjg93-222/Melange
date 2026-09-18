# Mentat cross-verification re-examination: contradictions, not ambiguity (steps 3-6)

Written 2026-09-17 by the fresh-context Fable session that did steps 3 to 6 of the brief in `BRIEF.md`, on the reason-code table and rulings recorded in `STEP2_REPORT.md`. Code lives in `C:\Users\pgoff\Mentat\mentat` on `codex/mentat-crypto`, HEAD `f0ec60b74` (which already carries `c62cc6eb6` and `7d364883e`). Everything below is UNCOMMITTED; the patch is `patches/xref_contradiction_text.patch`, the receipts are under `receipts/`.

## 1. The rule and the rulings

Paul (2026-09-17): "we are focusing on contradictions, not ambiguity" and "its ok if they work at another company if the money is going to something JP Morgan affiliated or if they are an advisor or in an a adjacent position". On the step-2 report: "Your suggestions are correct".

| Ruling | Content | Where it now lives |
|---|---|---|
| D1 | A row whose own non-blank text names another identifiable organisation (not the listed company or any alias) is a CONTRADICTION: excluded under `attribution_contradicted_by_text`, status `excluded_with_evidence`, `counted_cents` 0. Text that names the company or an alias (whole-token match on the company variants plus `inputs/verified_employer_aliases.csv`, short tokens PNC/CITI/BOFA/TRUIST/US BANK included) stays counted and flagged under `company_named_unverified`. Blank / NOT EMPLOYED / NONE / N/A / RETIRED-only / SELF-EMPLOYED-only text stays counted and flagged under `company_attribution_unverified`. Never attribute a row to a different listed company on this test. | `tools/cross_reference_engine.py` unverified block (`analyze`, after the `preexisting_source_exclusion` check) |
| D2 | Short-token matches count, flagged. | same (`company_named_unverified`) |
| D3 | Markers ADVISOR/ADVISER/ADVISORY, CONSULTANT/CONSULTING, CONTRACTOR, TRUSTEE, PARTNER, COUNSEL, BOARD (member / of directors); NOT DIRECTOR; NOT RETIRED. Marker present AND the text names the company or affiliate → `attribution_status` `role_supported`. Status only; dollars are decided by D1. | `ROLE_MARKER` at module level; role branch of the unverified block |
| Recipient route | `recipient_is_dated_company_pac` on an unverified row → `attribution_status` `recipient_supported` (still counted); plus a connected-organisation lookup against `inputs/fec_committee_master/cm22,cm24,cm26/cm.txt` field 14 (`CONNECTED_ORG_NM`) resolving to the company by the same whole-token test → reason `recipient_connected_organization_resolves_to_company`. | unverified block; `run_cross_reference.committee_connected_organizations()` |
| D4 | Register data is Paul's to add; `verified_company_affiliations.json` and the alias CSVs were NOT edited. Gaps are listed in section 6 with counts. | this file |
| D5 | `observed_filing_versions_unresolved` stays counted and flagged; the probable-duplicate figure is reported in section 7. | unchanged |
| D6 | The dead run `20260917T174138-ec8ba8ba4523` is superseded by the re-runs and NOT deleted; `state/cross-reference/latest.json` now points at the new Banking run. | section 5 |

### 1a. How the text test is applied (exact semantics of the patch)

- Population: every row that reaches the unverified block, i.e. `company_match_status` not ACCEPTED/REJECTED/EXCLUDED, or ACCEPTED with a blank company; after the explicit `excluded_reason` check, the non-giving check and the source-conflict branch (the 4 conflicted rows / $375 keep `company_attribution_unverified` unchanged).
- Names of a company: the company label itself, the `companies.variant` rows for the industry in the pinned source DB, the `inputs/verified_employer_aliases.csv` rows for that company, and the register `entity_name`/`aliases` of that company in the supplied affiliations file. Nothing else.
- Whole-token match: the text and each name are reduced to `[A-Z0-9]+` tokens; a name matches when its token sequence appears as whole tokens in the text (`\bCITI\b`, `\bUS BANK\b`, `\bBLOCK INC\b`). A name of eight or more characters also matches with its spaces removed, so `JPMORGAN CHASE` names JP Morgan and `WELLSFARGO` names Wells Fargo; this is the same method the step-2 split used (word + squash for long names), so the counts Paul ruled on are reproduced by the engine.
- Individual rows: the employer decides the contradiction; the company may be named in the employer OR the occupation (so `employer ACME CAPITAL / occupation ADVISOR TO CITI` names Citi and is not contradicted, which is what Paul's second ruling requires). Entity rows (PAC/ORG/COM/CCM/PTY/CAN/blank): the contributor name decides.
- "Names nothing": a text whose tokens are all in `NO_EMPLOYER_TOKENS` = NOT, EMPLOYED, NONE, N, A, NA, UNEMPLOYED, RETIRED, SELF, INFORMATION, REQUESTED, PER, BEST, EFFORTS, UNKNOWN, HOMEMAKER, STUDENT, DISABLED (or blank). Those rows stay `company_attribution_unverified`. `RETIRED FROM IBM` names IBM and is contradicted.
- Order of the routes: recipient route (register PAC by committee id or exact committee name, else committee-master connected organisation) → role route → text verdict. A recipient-supported row counts even when its employer names another organisation (Paul's ruling); it carries `company_named_unverified` or `company_attribution_unverified` according to its text plus the status `recipient_supported`. The recipient route is evaluated for individual rows only (the existing `recipient_is_dated_company_pac` marker's population); a third-party PAC giving to the company's PAC is not the company's giving.
- Excluded rows take the existing bucket `excluded_company_match` (no new bucket, so the digest and data layers are untouched) and status `excluded_with_evidence`; they leave the review queue like every other exclusion.
- Rows with a blank company (accepted-without-company) have no names to test and stay `company_attribution_unverified`.

## 2. Reason-code table (from STEP2_REPORT.md section 1, re-anchored to the patched engine)

Anchors are on the patched `tools/cross_reference_engine.py`. "Class" is the contradiction-vs-ambiguity call; "Effect" is what the patched engine does.

### 2a. Reasons that remove dollars (`exclude()`, status `excluded_with_evidence`)

| Reason | Decided at | Test | Class | Effect |
|---|---|---|---|---|
| `non_giving_receipt_role:other_receipt` / `:asset_liquidation` | non-giving branch via `pac_evidence.receipt_role` | the filing's own line or description says it is not a gift | CONTRADICTION | unchanged |
| `company_attribution_not_accepted` | REJECTED/EXCLUDED branch | the R matcher rejected the match | CONTRADICTION (recorded decision) | unchanged |
| `preexisting_source_exclusion:<policy>` | three sites | explicit workbook exclusion | CONTRADICTION (recorded decision) | unchanged |
| `attribution_contradicted_by_text` (NEW) | unverified block | own text names another organisation and not the company (D1) | CONTRADICTION | new exclusion |
| `superseded_in_observed_filing_family` | amendment families | higher amendment observed | CONTRADICTION | unchanged |
| `absent_from_complete_latest_filing` | complete-manifest pass | manifest lacks the id | CONTRADICTION | unchanged |
| `explicit_same_filing_memo_reference` | memo pass | proven duplicate of a counted parent | CONTRADICTION | unchanged (test 5 pins it) |
| `same_original_gift_at_conduit_and_destination` | earmark pass | reciprocal earmark, one-to-one | CONTRADICTION | unchanged |

### 2b. Reasons that move dollars between ledgers

`separate_observed_pac_activity` (counted → pac_activity) and `explicit_observed_refund` (linked_refund): unchanged.

### 2c. Reasons that flag but keep the money (review queue)

| Reason | Class | Effect |
|---|---|---|
| `company_named_unverified` (NEW) | AMBIGUITY: the text names the company but the matcher left it in review (prefix, short token, trailing tokens) | counted, flagged, queued |
| `company_attribution_unverified` | AMBIGUITY: text names nothing, or the recipient route rescued an other-employer row, or the company is blank, or the row is source-conflicted | counted, flagged, queued (was the whole 36,241 at HEAD) |
| `memo_parent_not_established` / `memo_parent_ambiguous` | AMBIGUITY | unchanged |
| `original_source_of_transfer_unresolved`, `receipt_role_unresolved` | AMBIGUITY | unchanged |
| `treasury_ownership_unresolved`, `company_pac_affiliation_unresolved` | AMBIGUITY (register work) | unchanged |
| `signed_adjustment_not_linked_refund` | AMBIGUITY (negative counted as negative) | unchanged |
| `observed_filing_versions_unresolved` | AMBIGUITY; probable duplicates reported in section 7 | unchanged (D5) |
| earmark reasons, `funding_identity_unresolved`, `source_or_attribution_conflict`, amendment-order reasons, the zero-count reasons | AMBIGUITY | unchanged |

Informational reasons added by this patch (no dollar effect): `recipient_connected_organization_resolves_to_company`, `role_marker_with_company_named`. Attribution statuses added: `recipient_supported`, `role_supported`. Every pre-existing reason code is still emitted.

## 3. What changed (files)

- `tools/cross_reference_engine.py`: module docstring; `NO_EMPLOYER_TOKENS`, `ROLE_MARKER`, `_tokens`, `_names_an_organization`, `_name_patterns`, `_text_names`; `analyze(..., company_names=None, committee_connected_orgs=None)`; `patterns_for` and `recipient_as_contributor` helpers inside `analyze`; the unverified block now runs the recipient route, the role route and the D1 text verdict; the `recipient_is_dated_company_pac` marker reads the committee name from the FEC `committee` object or the DB `committee_name` column (it read the API object only). Review items carry `reported_text`.
- `tools/run_cross_reference.py`: `company_names(database, industry)` (roster variants + alias CSV), `committee_master_paths()`, `committee_connected_organizations()` (cm.txt field 14, latin-1), `excluded_reasons(result)`; the run fingerprints the three committee-master files in `scope.committee_master` (not copied into `rules/`; `inputs/fec_committee_master` is untracked in git, so the sha256 is the record), records `scope.attribution_text_test` counts, checks the master did not change during the run, writes `excluded_reasons` (rows and gross per reason on excluded decisions) into `report.json`, and prints unresolved/excluded reasons and elapsed seconds at the end of `main()`.
- `tests/test_cross_reference_engine.py`: five new tests (section 8) and two re-pinned assertions: the near-name PAC rows `ACME EMPLOYEE PAC SUPPORTERS` and `ACME LEGACY PAC SUPPORTERS` name the company, so under D1 they are queued as `company_named_unverified` instead of `company_attribution_unverified` (their intent, "a near name is not a dated affiliation and stays queued", is unchanged).
- Line endings: all three files are LF in the index and the working tree (`git ls-files --eol` → `i/lf w/lf`); the patch scripts detected and preserved LF. The brief's "most files are CRLF" does not hold for these three.
- Not touched: `app/server.py`, `app/app.js`, `app/index.html`, the collector-slowdown tools files, `verified_company_affiliations.json`, the alias CSVs, `app/cross-reference.js`, `tests/test_studio_wording.cjs` (no "counted at $0" label exists in the live tree; grep over `app/*.js`, `app/*.py`, `tests/*.cjs`, `tests/*.py` finds the old vocabulary only in the engine test that asserts it is gone).

## 4. Fintech: before (run `20260911T010907-d7fdb039c080`, 10 Sep engine) and after (run `20260917T190836-4d409860e341`, patched engine)

Command: `python tools/run_cross_reference.py --database "C:\Users\pgoff\Mentat\mentat\.cache\receipt-metadata-repair-20260910\fintech\mentat.db" --industry Fintech --offline` from `C:\Users\pgoff\Mentat\mentat` (the same database the 10 Sep run pinned; both prior runs made zero FEC requests). Decisive line of `receipts/run_fintech.txt`: `"run_id": "20260917T190836-4d409860e341" ... "elapsed_seconds": 368.94` (the 10 Sep run: 60.81 s; the difference is the attribution recheck that HEAD runs since 13 Sep and a foreign 6.3 GB python process that was competing for the box during the run, not the text test). Baseline: the Fintech accepted-report snapshot, $9,803,891.31 (equals the Fintech workbook).

### 4a. Summary

| Figure | Before | After |
|---|---|---|
| Observed original giving | $9,089,743.52 | $11,050,344.05 |
| Employee giving | $8,506,671.08 | $8,746,811.15 |
| Unverified funding (PAC-named rows with no committee id, ORG rows) | $583,072.44 | $2,303,532.90 |
| Corporate giving / PAC outgoing | $0.00 / $0.00 | $0.00 / $0.00 |
| Baseline (workbook) | $9,803,891.31 | $9,803,891.31 |
| Change against the workbook | -$714,147.79 | +$1,246,452.74 |
| Review-queue rows / gross | 35,106 / $17,899,062.06 (the 10 Sep engine listed the two coverage reasons in this queue) | 3,478 / $4,535,566.55 (coverage is separate) |

### 4b. Per reason, review queue (rows / gross)

| Reason | Before | After |
|---|---|---|
| `company_attribution_unresolved` (zeroed) | 10,302 / $8,558,568.42 | gone |
| `company_named_unverified` (counted) | - | 1,606 / $1,993,000.53 |
| `company_attribution_unverified` (counted) | - | 0 / $0.00 |
| `memo_parent_not_established` | 1,656 / $1,890,257.81 | 1,773 / $2,092,515.92 |
| `receipt_role_unresolved` | 97 / $270,318.61 | 760 / $1,851,948.05 |
| `funding_identity_unresolved` | - | 685 / $1,727,304.00 |
| `original_source_of_transfer_unresolved` | 979 / $1,095,668.07 | 1,045 / $1,183,043.58 |
| `treasury_ownership_unresolved` | 711 / $583,072.44 | 732 / $594,128.90 |
| `signed_adjustment_not_linked_refund` | 56 / $125,375.06 | 61 / $140,125.06 |
| `reciprocal_earmark_not_established` | 6 / $140,000.00 | 6 / $140,000.00 |
| `observed_filing_versions_unresolved` | - | 51 / $2,385.00 |
| `latest_filing_completeness_unproven` / `filing_relationship_evidence_missing` | 20,340 / $6,945,196.45 and 2,808 / $505,039.38 (in the queue) | coverage queue, not in the review queue |

The rows that were held at $0 now sit in `receipt_role_unresolved`, `funding_identity_unresolved`, `memo_parent_not_established` and the two attribution flags; the increases in those reasons are the same rows, counted.

### 4c. Per reason, exclusions (rows / gross removed)

| Reason | Before | After |
|---|---|---|
| `attribution_contradicted_by_text` | - | 8,695 / $6,562,667.89 |
| `company_attribution_not_accepted` | 51,060 / $2,985,544.14 | 51,060 / $2,985,544.14 |
| `non_giving_receipt_role:other_receipt` | 100 / $724,547.79 | 102 / $730,347.79 (HEAD's receipt rules, not this patch) |
| `same_original_gift_at_conduit_and_destination` | 1 / $6,600.00 | 1 / $6,600.00 |
| `explicit_same_filing_memo_reference` | 1 / $2,900.00 | 1 / $2,900.00 |
| `superseded_in_observed_filing_family` | 2 / $1,500.00 | 2 / $1,500.00 |

Text split of the former 10,302, traced row by row from the 10 Sep ledger's `company_attribution_unresolved` ids into the new ledger: contradicted 8,695 / $6,562,667.89 + named 1,606 / $1,993,000.53 + 1 row ($2,900.00, id 4032920241888318943) that HEAD's receipt rules now settle as non-giving = 10,302. The step-2 report's Fintech paragraph quoted four of the first agent's five classes (73 + 8,643 = 8,716 other-organisation rows; 192 + 708 = 900 named); its fifth class, `entity: name resolves to company` 686 rows / $1,729,804.00 (`xref_split2_fintech.txt` line 208: the H&R Block, Robinhood, Stripe and Chime PAC rows), is where the rest of the engine's named bucket sits (192 + 708 + 686 = 1,586 against the engine's 1,606; the remainder is the engine's inclusion of the occupation field and the register names).

### 4d. What the exclusions are (from `receipts/after_fintech_text_census.txt`)

Per company: Cash App 1,264 rows / $6,032,540.47; Dave Inc. 2,560 / $183,526.16; SoFi 2,857 / $176,239.69; Chime 1,287 / $99,228.32; Stripe 723 / $70,878.25; Plaid 4 / $255.00. Top texts: `BLOCKCHAIN COM INC` (ORG, 1 row, $5,000,000.00), `BLOCKCHAIN GAME PARTNERS INC` $598,559.94, `BLOCKCHAIN INNOVATION PROJECT INC` $150,000.00, `BLOCK COMMUNICATIONS INC` 200 rows / $125,303.68, `THE SOFITEL CHICAGO` $66,425.97, `STRIPES` 163 rows / $49,054.80, `DAVE ARBOGAST GROUP INC` $46,000.00, `CHIMEDICAL MANAGEMENT GROUP` $35,200.00, `FRIENDS OF DAVE BRAT INC` $34,500.00, `SOFIA UNIVERSITY` 166 rows / $15,991.72, `DAVE THOMPSON DESIGNS INC` 1,274 rows / $23,425.04. None of these is a Fintech company.

### 4e. Fintech variant note for Paul (data, not changed)

The `companies` table gives Cash App eight variants: `Block Inc`, `Block, Inc.`, `Block/Cash App`, `Cash App`, `Cash App Investing LLC`, `Square Inc`, `Square, Inc.`, `Square/Cash App`. Under the whole-token test `BLOCK INC` is a token subsequence of `H R BLOCK INC PAC`, so every H&R Block Inc PAC row under Cash App names the company: 469 of Cash App's 473 `company_named_unverified` rows / $1,048,754.00 of $1,048,964.00 are `H R BLOCK INC POLITICAL ACTION COMMITTEE BLOCKPAC` (295 / $675,004.00), `H R BLOCK INC PAC BLOCKPAC` (133 / $261,000.00) and their spellings. They count as Cash App unverified funding. `Square Inc` likewise names `FOURSQUARE INC` through the squashed-name rule (`SQUAREINC` in `FOURSQUAREINC`; 0 rows in this run). The single-word variants `Plaid`, `Chime`, `Stripe`, `Dave.com` also name strangers as whole tokens: `PLAID PANTRY` 137 rows / $3,039.89, `PLAID PAISLEY ENTERPRISES` $33,300.00, `ROBINHOOD INTEGRATIVE HEALTH` $7,650.53, `CHIME TV` $17,600.00, `STRIPE WIX` $92,664.71 are counted-flagged. All of this is the lenient direction (counted, flagged, visible in the queue), which is what the ruling asks for when the text is ambiguous; the fix, if Paul wants one, is in the variant list (drop `Block Inc` / `Block, Inc.` as bare variants or qualify them) and is his data call. The step-2 caveat ("the Cash App variant Block matched H&R BLOCK INC PAC rows, $1.05M") is confirmed at $1,048,754.00.

D4 register gaps visible in Fintech (no `verified_company_affiliations.json` record exists for any Fintech company, so every own PAC counts as unverified funding rather than PAC activity): `ROBINHOOD MARKETS INC PAC` 123 rows / $385,250.00 (+ `ROBINHOOD MARKETS PAC` 1 / $5,000.00, COM 2 / $4,500.00), `STRIPE INC POLITICAL ACTION COMMITTEE` 48 / $161,200.00 (+ `STRIPE INC PAC` 16 / $60,700.00, COM 5 / $18,400.00 and 1 / $2,500.00), `CHIME FINANCIAL INC PAC CHIME PAC` 18 / $40,500.00 (+ 2 / $2,000.00, `CHIME PAC` 1 / $1,000.00). Recipient route: 0 rows (no register, and no recipient committee's connected organisation resolves to a Fintech company). Role route: 4 rows / $6,021.07 (`STRIPE INCE` / `CORPORATE ADVISOR` 2 / $5,000.00; `PLAID CONSTRUCTION` / `GENERAL CONTRACTOR` 1 / $1,000.00; `KLARNA FOUNDEVER` / `CONSULTANT` 1 / $21.07).

Observed giving now exceeds the workbook by $1,246,452.74. The reasons responsible, all counted-flagged ambiguity: `company_named_unverified` $1,963,500.53 counted (of which H&R Block $1,048,754.00), `funding_identity_unresolved` $1,709,404.00 counted (entity rows without a committee id, overlapping the named PAC rows), `receipt_role_unresolved` and `memo_parent_not_established` growth. That is Paul's call, not a reason to re-zero.

## 5. Banking: before (run `20260913T074303-bca0ac2b9cd3`, 13 Sep engine) and after (run `20260918T030844-6098810b1ae7`, patched engine)

Command: `python tools/run_cross_reference.py --database "C:\Users\pgoff\Mentat\mentat\.cache\report-repairs\banking-20260910\data\mentat.db" --industry Banking --offline` from `C:\Users\pgoff\Mentat\mentat`. Both runs pin the same source database (`database` line of `receipts/before_banking_reasons.txt` and `receipts/after_banking_reasons.txt` is byte-identical). Decisive lines of `receipts/run_banking.txt`: the final JSON ends `..., "elapsed_seconds": 650.41}` followed by `exit=0`; the 13 Sep run took 558.84 s. `state/cross-reference/latest.json` now reads `"run_id": "20260918T030844-6098810b1ae7"` (D6). The killed run `20260917T191516-1199b40e8c61` has no `report.json`, is not used anywhere in this packet and was not deleted.

Unlike Fintech, Banking's baseline and the published workbook are **different numbers**: the baseline is the accepted-report snapshot, $133,516,227.27, while the published Banking workbook total for the same cycles is $54,762,844.05. Every comparison below is against the workbook figure.

### 5a. Summary

Figures from the `summary` line of `receipts/before_banking_reasons.txt` / `receipts/after_banking_reasons.txt` (the runner's own `report.json` summary), and from the `== status ==` blocks of the same two files.

| Figure | Before | After |
|---|---|---|
| Observed original giving | $72,103,655.70 | $77,054,485.76 |
| Employee giving | $70,446,487.57 | $71,246,149.34 |
| Unverified funding | $1,657,168.13 | $5,808,336.42 |
| PAC activity (`pac_outgoing`) | $22,774,438.00 | $22,774,438.00 |
| Corporate giving | $0.00 | $0.00 |
| Baseline (accepted-report snapshot) | $133,516,227.27 | $133,516,227.27 |
| Published Banking workbook total | $54,762,844.05 | $54,762,844.05 |
| **Observed giving against the workbook** | **+$17,340,811.65** | **+$22,291,641.71** |
| Review queue, rows / gross | 76,197 / $49,929,377.44, of which 36,241 / $37,940,955.71 held at $0 | 46,156 / $16,990,616.89, counted $14,024,190.97 |
| Excluded (`excluded_with_evidence`), rows / gross | 79,947 / $109,735,911.79 | 109,929 / $142,547,260.34 |
| Elapsed | 558.84 s | 650.41 s |

Observed original giving is `employee_giving + unverified_funding` in both runs exactly ($70,446,487.57 + $1,657,168.13 = $72,103,655.70; $71,246,149.34 + $5,808,336.42 = $77,054,485.76), so the whole movement is visible in those two lines.

### 5b. Per reason, review queue (rows / gross)

From the `== review-queue reasons (report.json unresolved_reasons) ==` block of each receipt.

| Reason | Before | After |
|---|---|---|
| `company_attribution_unresolved` (held at $0) | 36,241 / $37,940,955.71 | gone |
| `company_named_unverified` (counted) | - | 6,247 / $5,140,809.45 |
| `company_attribution_unverified` (counted) | - | 17 / $653.82 |
| `memo_parent_not_established` | 19,529 / $8,522,419.98 | 19,648 / $8,799,053.99 |
| `original_source_of_transfer_unresolved` | 18,696 / $5,789,063.20 | 18,814 / $5,937,349.79 |
| `treasury_ownership_unresolved` | 448 / $1,537,481.15 | 1,328 / $4,281,699.33 |
| `receipt_role_unresolved` | 725 / $2,336,852.79 | 1,546 / $3,864,785.48 |
| `funding_identity_unresolved` | 73 / $121,130.46 | 486 / $1,700,421.02 |
| `signed_adjustment_not_linked_refund` | 641 / $1,127,074.41 | 660 / $1,216,462.96 |
| `observed_filing_versions_unresolved` | 1,148 / $526,514.04 | 1,169 / $533,939.04 |
| `earmark_counterpart_not_unique` | 15,915 / $383,125.12 | 16,032 / $384,885.15 |
| `reciprocal_earmark_not_established` | 2,168 / $328,691.08 | 2,188 / $337,295.18 |
| `ambiguous_amendment_order` | 24 / $17,674.00 | 24 / $17,674.00 |
| `source_or_attribution_conflict` | 4 / $375.00 | 13 / $2,211.65 |
| `earmark_destination_ambiguous` | 89 / $737.06 | 89 / $737.06 |

The queue shrinks from $49.9M to $17.0M because the 36,241 held rows leave it: 29,816 of them are excluded and 6,266 are counted and re-flagged. The growth in `treasury_ownership_unresolved`, `receipt_role_unresolved` and `funding_identity_unresolved` is the entity rows arriving from the former hold plus HEAD's own receipt-role movement (see 5f).

### 5c. Per reason, exclusions (rows / gross removed)

From the `== reasons on EXCLUDED decisions (dollars removed) ==` block of each receipt; the after column also appears verbatim as `excluded_reasons` in `receipts/run_banking.txt`.

| Reason | Before | After |
|---|---|---|
| `non_giving_receipt_role:other_receipt` | 45,731 / $100,095,060.72 | 45,895 / $100,365,440.78 |
| `attribution_contradicted_by_text` (NEW) | - | 29,816 / $32,538,668.49 |
| `non_giving_resolved_without_company_attribution` | 40,814 / $23,536,904.99 | 40,973 / $23,795,428.94 |
| `company_attribution_not_accepted` | 33,827 / $7,258,142.81 | 33,827 / $7,258,142.81 |
| `non_giving_receipt_role:asset_liquidation` | 6 / $2,204,936.88 | 6 / $2,204,936.88 |
| `recognized_contribution_receipt` | 383 / $177,771.38 | 385 / $180,071.38 |
| `individual_with_accepted_employer_match` | 381 / $172,771.38 | 381 / $172,771.38 |
| `explicit_same_filing_memo_reference` | 63 / $139,623.55 | 65 / $141,923.55 |
| `superseded_in_observed_filing_family` | 29 / $2,996.00 | 30 / $35,396.00 |
| `same_original_gift_at_conduit_and_destination` | 291 / $35,151.83 | 291 / $35,151.83 |
| `connected_pac_affiliation` | 5 / $14,500.00 | 5 / $14,500.00 |
| `automatic_exact_alias_recheck` | 50 / $8,086.83 | 50 / $8,086.83 |
| `separate_observed_pac_activity` | 2 / $5,000.00 | 2 / $5,000.00 |
| `company_named_unverified` | - | 2 / $2,300.00 |
| `role_marker_with_company_named` | - | 1 / $600.00 |

No new bucket was created, and the arithmetic proves it: the `excluded_company_match` bucket goes from 33,827 rows / $7,258,142.81 to 63,643 rows / $39,796,811.30, and 33,827 + 29,816 = 63,643 with $7,258,142.81 + $32,538,668.49 = $39,796,811.30 exactly. The `attribution_unresolved` bucket and the `held_for_attribution_review` status are gone from the after run's `== bucket ==` and `== status ==` blocks.

### 5d. Where the 36,241 held rows went (`receipts/trace_held_banking.txt`)

`python trace_held.py <13 Sep run> <18 Sep run>`, traced row by row from the before ledger's `company_attribution_unresolved` source ids into the after ledger. `before held rows: 36241` / `after decisions seen for those rows: 36241` - every row is accounted for.

| Verdict | Rows | Gross | Counted |
|---|---|---|---|
| contradicted (`attribution_contradicted_by_text`, excluded) | 29,816 | $32,538,668.49 | $0.00 |
| named (`company_named_unverified`, counted) | 6,249 | $5,143,109.45 | $4,962,032.35 |
| unverified (`company_attribution_unverified`, counted) | 17 | $653.82 | $653.82 |
| settled as non-giving by HEAD's receipt rules | 159 | $258,523.95 | $0.00 |
| **TOTAL** | **36,241** | **$37,940,955.71** | **$4,962,686.17** |

So the ruling releases $4,962,686.17 of the $37,940,955.71 that HEAD was holding at $0, and excludes $32,538,668.49 as contradicted. (The 6,249 named rows in the ledger are 6,247 in the queue because 2 rows / $2,300.00 that carry `company_named_unverified` are excluded by another rule; 6,249 - 2 = 6,247 and $5,143,109.45 - $2,300.00 = $5,140,809.45. Gross is `|amount|` while counted keeps the sign, which is the rest of the gap between the two columns.)

By attribution status, from the same receipt:

| Status x verdict | Rows | Gross | Counted |
|---|---|---|---|
| `unverified` / contradicted | 29,816 | $32,538,668.49 | $0.00 |
| `unverified` / named | 5,587 | $4,929,137.45 | $4,749,860.35 |
| `not_required_for_non_giving` / non-giving | 159 | $258,523.95 | $0.00 |
| `role_supported` / named | 514 | $192,016.13 | $190,216.13 |
| `recipient_supported` / named | 148 | $21,955.87 | $21,955.87 |
| `recipient_supported` / unverified | 17 | $653.82 | $653.82 |

Only the last line is money that the text test alone would have removed and a route saved: 17 Citibank rows whose employer reads `CITICORP NORTH AMERICA INC`, which is not a Citibank variant or alias, so D1 would have called it a contradiction; the recipient route recognised the gift as going to a Citibank-affiliated committee and kept it counted at $653.82. That is Paul's second ruling doing exactly its job. The 514 `role_supported` and 148 `recipient_supported` named rows would have counted anyway under D1; on those rows the status is a label, not a dollar decision.

### 5e. What the exclusions are (`receipts/after_banking_text_census.txt`)

Per company: Citibank 26,024 rows / $29,261,620.88; Bank of America NA 1,519 / $3,032,100.00; US Bank NA 336 / $169,958.52; PNC Bank NA 1,925 / $54,845.09; JP Morgan Chase Bank NA 11 / $20,143.82; Morgan Stanley Bank 1 / $0.18.

$29.3M of the $32.5M is one failure mode: the R matcher had swept **CITIZENS-** organisations into Citibank's review queue on the `CITI` prefix, and the whole-token test correctly refuses to read `CITIZENS` as `CITI`. Top texts, all under Citibank unless marked: `STATE GOVERNMENT CITIZENS CAMPAIGN` 97 rows / $4,202,000.00; `END CITIZENS UNITED` 1,265 / $4,123,980.34; `CITIZENS ALLIANCE POLITICAL ACTION COMMITTEE INC` 23 / $2,310,500.00; `CITIZENS TO ELECT RICK LARSEN` 128 / $1,854,345.00; `INDEPENDENT COMMUNITY BANKERS OF AMERICA POLITICAL ACTION COMMITTEE` (Bank of America NA) 713 / $1,291,500.00 and its `... PAC` spelling 421 / $1,014,500.00; `CITIZENS ALLIANCE OF AMERICA 501C4` 7 / $995,000.00; `CITIZENS UNITED POLITICAL VICTORY FUND` 305 / $833,300.00; `TARGET CORPORATION CITIZENS POLITICAL FORUM` 329 / $763,500.00; `CITIZENS 1ST BANK` 85 / $723,235.00; `CITIZENS BANK` 4,535 IND rows / $382,262.86 and 341 ORG rows / $348,366.50; `CITIZENS BUSINESS BANK` 7,282 / $203,225.05; `CITIZENS FINANCIAL GROUP INC POLITICAL ACTION COMMITTEE CITIZENS PAC` 104 / $243,500.00; `PEPSICO INC CONCERNED CITIZENS FUND` 170 / $380,898.53; `TD BANK US HOLDING COMPANY POLITICAL ACTION COMMITTEE TD BANK PAC` (US Bank NA) 26 / $63,000.00. Citizens Financial Group, Citizens Bank, Citizens Business Bank, End Citizens United, Target, PepsiCo, ICBA and TD Bank are all other organisations. None of the top 60 contradicted texts is one of the ten listed Banking companies.

The counted-and-flagged side, `company_named_unverified` per company: Wells Fargo Bank NA 2,340 rows / $1,575,766.94; PNC Bank NA 534 / $1,217,384.94; JP Morgan Chase Bank NA 462 / $777,876.16; Capital One Bank NA 385 / $379,250.97; Goldman Sachs Bank NA 92 / $302,181.70; Bank of America NA 1,285 / $235,021.13; Citibank 516 / $229,545.56; Truist Bank 262 / $212,497.68; Morgan Stanley Bank 221 / $126,106.75; US Bank NA 152 / $87,477.62. Top texts are the company's own units and PACs: `PNC ADVISORS` 36 / $648,198.75, `WELLS FARGO PAC ACCOUNT` 52 / $621,580.67, `WELLS FARGO BANK` 170 / $478,368.88, `JP MORGAN CHASE` 97 / $310,994.69, `JP MORGAN CHASE NA` 64 / $197,361.95, `GOLDMAN SACHS AND CO` 7 / $107,900.00, `WELLS FARGO BANK RETIRED` 1,105 / $68,710.00, `CITIBANK N A` 26 / $53,998.66, `CITIBANK F S B` 97 / $40,735.90. These are the rows Paul's ruling keeps.

Role route, 514 rows / $192,016.13: the advisor and adjacent-position population, `MORGAN STANLEY PRIVATE WEALTH MANAGEME` / `FINANCIAL ADVISOR` 42 / $56,900.00, `MERRILL LYNCH WEALTH MANAGEMENT` / `FINANCIAL ADVISOR` 20 / $21,851.47, `BANK OF AMERICA MERILL LYNCH` / `SR FINANCIAL CONSULTANT` 12 / $10,200.00, `WELLS FARGO CONTRACTOR` / `BUSINESS EXECUTION ASSOCIATE` 5 / $4,140.24, `PNC MEZZANINE CAPITAL` / `ADVISORY PARTNER` 3 / $3,650.00, `GOLDMAN SACHS ASSET MANAGEMENT L P` / `TRUSTEE` 1 / $1,000.00.

### 5f. The after figure against the $54,762,844.05 workbook total

**Observed original giving is now $77,054,485.76, which sits ABOVE the published Banking workbook total of $54,762,844.05, by $22,291,641.71.** It already sat above it before this change, by $17,340,811.65; the change widened an existing overshoot by $4,950,830.06, it did not create it.

The $4,950,830.06 is fully reconciled: the trace releases $4,962,686.17 of counted dollars from the held rows, of which $4,151,168.29 lands in unverified funding ($1,657,168.13 -> $5,808,336.42) and $811,517.88 in employee giving; $4,151,168.29 + $811,517.88 = $4,962,686.17 exactly. The $11,856.11 by which the release exceeds the observed-giving movement is a 5-row shrink in `individual_with_accepted_employer_match` (725,196 rows / $72,583,589.29 -> 725,191 / $72,571,733.18) on rows that were never in the held population; both runs exclude the identical 381 rows / $172,771.38 under that reason, so it is not an exclusion change and not this patch - it is HEAD's own movement since 13 Sep.

That HEAD movement is real and should not be read as this lane's doing: `recipient_is_dated_company_pac` goes from 150,828 rows / $15,541,025.09 to 174,150 / $17,045,231.49, `provisional_receipt_role:unverified_other_receipt` from 712 / $1,315,806.79 to 1,532 / $3,839,239.48, and a $1,000,000 row leaves `provisional_receipt_role:unverified_receipt_role` (1 row / $1,000,000.00 -> 2 rows / $4,500.00). The two runs are 13 Sep engine versus patched HEAD, so the raw before/after delta mixes both; the clean, patch-attributable measurement is the row-level trace in 5d.

Which reason codes drive the $22,291,641.71 gap. Of the $77,054,485.76 observed, $14,024,190.97 is counted but flagged in the review queue (`== status ==`, `needs_review` counted). The queue reasons carrying the most money, in order: `memo_parent_not_established` $8,799,053.99, `original_source_of_transfer_unresolved` $5,937,349.79, `company_named_unverified` $5,140,809.45, `treasury_ownership_unresolved` $4,281,699.33, `receipt_role_unresolved` $3,864,785.48, `funding_identity_unresolved` $1,700,421.02. Rows carry several queue reasons, so those sum past the $16,990,616.89 queue gross. Only the third of them, $5,140,809.45, is new in this lane; the other five predate it and together account for the bulk of the overshoot that existed before the change.

One inference, flagged as an inference rather than a measurement: the largest single component of the new unverified-funding line is the D4 register gap in section 6 - 1,298 entity rows / $4,324,780.39 whose contributor name **is** the company's own PAC or a company unit. Those rows are counted as original giving only because no register record exists to re-route them. If Paul adds the register data, they should be re-decided as company PAC activity rather than original giving on the next run, which would take most of the $5,808,336.42 unverified-funding line out of observed giving and bring Banking back to roughly its pre-change position against the workbook. That is a prediction about the next run, not a number this run produced.

## 6. D4: the register gaps, with counts (Paul's data to add; nothing here was edited)

`inputs/verified_company_affiliations.json` and the alias CSVs were **not** touched by this lane. Both lists below are read from `receipts/after_banking_text_census.txt`.

### 6a. Recipient committee resolved through the committee master only

One committee in the whole Banking run is recognised as the company's PAC by the FEC committee master (`cm.txt` field 14, `CONNECTED_ORG_NM`) and not by the register:

| Committee id | Committee name | Company | Rows | Gross |
|---|---|---|---|---|
| `C00039305` | `CITIGROUP INC PAC STATE CITI PAC STATE` | Citibank | 2 | $1,000.00 |

Adding `C00039305` to Citibank in `verified_company_affiliations.json` makes that an affiliation the engine can rely on rather than a committee-master inference.

### 6b. The companies' own PACs appearing as DONORS

Entity rows (PAC/ORG/COM/CCM, and one blank) whose contributor name names the listed company, none of which carries an FEC committee id (`no C-id` in every row), so the engine can only count them as unverified funding. **1,298 rows / $4,324,780.39 in total.** The top 40 by dollars:

| Company | Type | Contributor name (tokenised) | Bucket | Rows | Gross |
|---|---|---|---|---|---|
| PNC Bank NA | ORG | PNC ADVISORS | organization_unverified | 36 | $648,198.75 |
| Wells Fargo Bank NA | ORG | WELLS FARGO PAC ACCOUNT | organization_unverified | 52 | $621,580.67 |
| Wells Fargo Bank NA | ORG | WELLS FARGO BANK | organization_unverified | 170 | $478,368.88 |
| JP Morgan Chase Bank NA | ORG | JP MORGAN CHASE | organization_unverified | 97 | $310,994.69 |
| JP Morgan Chase Bank NA | ORG | JP MORGAN CHASE NA | organization_unverified | 64 | $197,361.95 |
| PNC Bank NA | PAC | PNC PAC BIPARTISAN VOLUNTARY PUBLIC AFFAIRS COMMITTEE OF T | funding_unverified | 4 | $110,000.00 |
| Goldman Sachs Bank NA | ORG | GOLDMAN SACHS PHILANTHROPY FUND | organization_unverified | 2 | $100,000.00 |
| Wells Fargo Bank NA | PAC | WELLS FARGO AND CO EMPLOYEE PAC | funding_unverified | 8 | $81,000.00 |
| Wells Fargo Bank NA | ORG | WELLS FARGO FINANCIAL ADVISORS | organization_unverified | 13 | $69,702.45 |
| PNC Bank NA | ORG | PNC BANK | organization_unverified | 52 | $64,130.88 |
| PNC Bank NA | PAC | PNC PAC BIPARTISAN VOLUNTARY PUBLIC AFFAIRS COMMITTEE OF THE PNC FINANCIAL | funding_unverified | 2 | $60,000.00 |
| Citibank | PAC | CITIGROUP INC PAC STATE CITI PAC STATE | funding_unverified | 17 | $58,900.00 |
| PNC Bank NA | PAC | PNC FINANCIAL SERVICES GROUP PAC | funding_unverified | 2 | $55,000.00 |
| Citibank | ORG | CITIBANK N A | organization_unverified | 26 | $53,998.66 |
| Capital One Bank NA | PAC | CAPITAL ONE FINANCIAL CORPORATION | funding_unverified | 15 | $48,500.00 |
| JP Morgan Chase Bank NA | PAC | J P MORGAN CHASE COMPANY PAC | funding_unverified | 3 | $45,000.00 |
| Capital One Bank NA | PAC | CAPITAL ONE ASSOCIATION POLITICAL FUND PAC | funding_unverified | 3 | $45,000.00 |
| Citibank | ORG | CITIBANK F S B | organization_unverified | 97 | $40,735.90 |
| JP Morgan Chase Bank NA | ORG | JP MORGAN CHASE BANK | organization_unverified | 12 | $38,848.03 |
| Truist Bank | COM | TRUIST FINANCIAL CORP FEDERAL STATE LOCAL PAC | funding_unverified | 1 | $31,331.06 |
| JP Morgan Chase Bank NA | PAC | JP MORGAN CHASE FEDERAL PAC | funding_unverified | 3 | $31,000.00 |
| Capital One Bank NA | ORG | CAPITAL ONE BANK | organization_unverified | 124 | $29,602.93 |
| Wells Fargo Bank NA | COM | WELLS FARGO AND COMPANY EMPLOYEES GOOD GOVERNMENT FEDERAL FUND | funding_unverified | 10 | $29,000.00 |
| JP Morgan Chase Bank NA | PAC | J P MORGAN CHASE CO PAC | funding_unverified | 5 | $25,000.00 |
| PNC Bank NA | PAC | BIPARTISAN VOLUNTARY PUBLIC AFFAIRS COMMITTEE OF THE PNC FINANCIAL SERVICES GROUP INC PNC PA | funding_unverified | 5 | $25,000.00 |
| Bank of America NA | PAC | BANK OF AMERICA STATE AND FEDERAL PAC | funding_unverified | 5 | $24,000.00 |
| US Bank NA | PAC | US BANK CORP PAC | funding_unverified | 5 | $20,000.00 |
| Capital One Bank NA | PAC | CAPITAL ONE FINANCIAL CORP ASSOC POLTICAL FUND | funding_unverified | 4 | $20,000.00 |
| Goldman Sachs Bank NA | PAC | GOLDMAN SACHS GROUP INC POLITICAL ACTION COMMITTEE THE | funding_unverified | 8 | $19,500.00 |
| Capital One Bank NA | PAC | CAPITAL ONE FINANCIAL CORP ASSOCIATE PAC | funding_unverified | 5 | $17,500.00 |
| Truist Bank | PAC | TRUIST FINANCIAL CORPORATION FEDERAL STATE LOCAL POLITICAL ACTION COMMITTEE | funding_unverified | 4 | $17,500.00 |
| Capital One Bank NA | PAC | CAPITAL ONE FINANCIAL CORPORATION ASSOC POLITICAL FUND | funding_unverified | 4 | $17,000.00 |
| Truist Bank | ORG | BB T TRUIST | organization_unverified | 14 | $15,724.89 |
| Wells Fargo Bank NA | (blank) | WELLS FARGO CO EMPLOYEE PAC | funding_unverified | 3 | $15,000.00 |
| PNC Bank NA | PAC | PNC PAC FED | funding_unverified | 3 | $15,000.00 |
| PNC Bank NA | PAC | PNC FEDERAL PAC | funding_unverified | 4 | $15,000.00 |
| Bank of America NA | PAC | BANK OF AMERICA CORP PAC | funding_unverified | 4 | $15,000.00 |
| PNC Bank NA | PAC | FED THE PNC FINANCIAL SERVICES GROUP INC PAC PNC PAC FEDERAL | funding_unverified | 4 | $15,000.00 |
| PNC Bank NA | PAC | PNC PAC FEDERAL BIPARTISAN VOLUNTARY PUBLIC AFFAIRS COMMIT | funding_unverified | 3 | $15,000.00 |
| PNC Bank NA | PAC | BIPARTISAN PUBLIC AFFAIRS COMMITTEE OF THE PNC FINANCIAL SERVICES GROUP INC PNC PAC | funding_unverified | 3 | $15,000.00 |

Every one of these is a company PAC, a company unit or a company treasury account giving as a donor. With a register record they become PAC activity; without one they are counted as the company's original giving and flagged, which is the lenient direction the ruling asks for but is not what the workbook counts. This is the single largest lever Paul has over the section 5f gap.

### 6c. Alias gap worth a look

`CITICORP NORTH AMERICA INC` is plainly Citibank but is not a Citibank variant or an entry in `inputs/verified_employer_aliases.csv`. The 17 rows that carry it survived only because the recipient route rescued them (5d); any `CITICORP` row without a company-PAC recipient is excluded as a contradiction under D1. It does not appear in the contradicted top-60 list, which reaches down to $63,000, so any such rows are individually small - but the alias is the correct fix, not the route. Adding `CITICORP` (and `CITICORP NORTH AMERICA`) to the Citibank aliases is Paul's data call.

## 7. D5: probable duplicate filing versions (unchanged by this patch)

`python dup_versions.py <run>` on both runs. `observed_filing_versions_unresolved` groups one review item per (committee, transaction id, company, donor, date); the counted dollars beyond the first row of each group are the probable duplicate.

| | Before | After |
|---|---|---|
| Groups | 389 | 396 |
| Rows | 1,148 | 1,169 |
| Gross | $526,514.04 | $533,939.04 |
| Groups whose rows all carry an identical amount | 389 (all) | 396 (all) |
| Probable duplicate, counted | $344,433.54 | $349,383.54 |

Every group in both runs consists of rows with identical amounts, which is what a duplicate filing version looks like. So roughly $349,383.54 of the counted Banking total is probably the same gift filed twice. Under D5 these stay counted and flagged; this patch changes nothing here, and the small movement between the runs is HEAD's, not this lane's.

## 8. Tests (red before, green after)

All in `tests/test_cross_reference_engine.py`, run from `C:\Users\pgoff\Mentat\mentat`.

| # | Test | Pins |
|---|---|---|
| 1 | `test_text_naming_another_organization_contradicts_the_attribution` | END CITIZENS UNITED (PAC, review) under Citibank → `attribution_contradicted_by_text`, `excluded_with_evidence`, counted 0, pac 0, not queued, `changes` delta -$5,000; the company label alone suffices as a name |
| 2 | `test_text_naming_the_company_stays_counted_while_a_stranger_is_excluded` | CITIBANK N A and CITI TRENDS (short token) → counted, `company_named_unverified`, status `needs_review`; blank and NOT EMPLOYED/RETIRED → counted, `company_attribution_unverified`; CITIZENS BUSINESS BANK → excluded; queue membership per code; totals $400 |
| 3 | `test_recipient_company_pac_supports_an_unverified_attribution` | employer ACME WIDGETS INC: recipient C00008474 (register) → counted, `recipient_supported`, `recipient_is_dated_company_pac`, `employee_to_company_pac`; recipient C00039305 with connected org CITIGROUP INC. → counted, `recipient_supported`, `recipient_connected_organization_resolves_to_company`; recipient C00000001 → excluded |
| 4 | `test_role_marker_with_the_company_named_is_role_supported` | SELF-EMPLOYED / CONSULTANT TO CITIBANK and ACME CAPITAL / ADVISOR TO CITI → counted, `role_supported`; WELLS FARGO BANK RETIRED / RETIRED → counted, `company_named_unverified`, status `unverified`; ACME CAPITAL / MANAGING DIRECTOR → excluded (DIRECTOR is not a marker) |
| 5 | `test_proven_duplicate_memo_leg_stays_excluded_under_the_text_test` | parent CITIBANK (review) counted and named; its explicit same-filing memo leg → `explicit_same_filing_memo_reference`, excluded, one memo link, total $100 |

Re-pinned (two assertions): `test_exact_dated_pac_affiliation_overrides_provisional_corporate_name_review` and `test_affiliation_aliases_are_exact_and_do_not_enable_prefix_matching` now expect the near-name rows (`ACME EMPLOYEE PAC SUPPORTERS`, `ACME LEGACY PAC SUPPORTERS`) in the queue under `company_named_unverified`.

Receipts (decisive lines):

- Before any edit (`receipts/pytest_baseline_before_edit.txt`): `108 passed, 27 subtests passed in 54.05s`.
- Red, tests patched, engine unchanged (`receipts/pytest_red.txt`): `7 failed, 47 deselected in 0.35s` (`TypeError: analyze() got an unexpected keyword argument 'company_names'` on the five new tests; the two re-pinned assertions fail on `company_attribution_unverified`).
- Green, selected (`receipts/pytest_green_selected.txt`): `7 passed, 47 deselected in 0.08s`.
- Green, four-file suite `python -m pytest tests/test_cross_reference_engine.py tests/test_cross_reference_runner.py tests/test_cross_reference_digest.py tests/test_cross_reference_data.py -q` (`receipts/pytest_green_full.txt`): `113 passed, 27 subtests passed in 50.34s`.

`tests/test_studio_wording.cjs` needed no change: no "counted at $0" label exists in the live tree (grep over `app/*.js`, `app/*.py`, `tests/*.cjs`, `tests/*.py`; the old vocabulary survives only in the engine test that asserts it is gone).

## 9. Method notes

- Every number above was read from a run's `report.json`, its `ledger.sqlite` (`receipts/reason_table.py`, `receipts/text_census.py`, `receipts/dup_versions.py`) or a pytest tail; the commands are quoted next to the figures.
- The runs were started detached and read when they exited (one until-loop on the run's exit line each; no poll-supervision). `state/cross-reference/latest.json` moved from the dead run `20260917T174138-ec8ba8ba4523` to `20260917T190836-4d409860e341` when Fintech started and to the Banking run when it started; the dead run's directory is untouched.
- The patch was cut as bytes with `git diff -- <the three files> > patches/xref_contradiction_text.patch` (bash redirect) and proven with `git apply --check` (`receipts/git_apply_check.txt`), per DE-025.
- No Sonnet/Haiku agent was used; no scout claims were relied on.

## 10. D4 closed: the register records added, and what they moved (2026-09-18)

This section is an addition; sections 1-9 are unchanged. It records the register
work section 6 left open, done against the FEC committee master on disk.

### 10a. What was added

Four records, `inputs/verified_company_affiliations.json`, 12 -> 16 records, schema
unchanged (`schema_version` 2, `relationship` `connected_pac`, `valid_from`
`2021-01-01`, LF endings, prettier-style arrays preserved). Every `entity_id` and
`entity_name` is the verbatim `CMTE_ID` / `CMTE_NM` of the master line quoted
beside it; nothing was invented.

| Committee | Company | `CMTE_NM` (field 2, verbatim) | `CONNECTED_ORG_NM` (field 14) | Master lines |
|---|---|---|---|---|
| `C00039305` | Citibank | `CITIGROUP INC. PAC - STATE (CITI PAC-STATE)` | `CITIGROUP INC.` | cm22/cm.txt:268, cm24/cm.txt:260, cm26/cm.txt:254 |
| `C00009639` | Truist Bank | `TRUIST FINANCIAL CORPORATION FEDERAL, STATE & LOCAL POLITICAL ACTION COMMITTEE (FORMERLY SUNTRUST BANKS, INC. MAIN STREET BANKERS PAC)` | `TRUIST FINANCIAL CORPORATION` | cm22/cm.txt:102, cm24/cm.txt:99, cm26/cm.txt:98 |
| `C00043489` | Bank of America NA | `BANK OF AMERICA CORPORATION STATE AND FEDERAL PAC` | `BANK OF AMERICA CORPORATION (blank in cm24)` | cm22/cm.txt:312, cm24/cm.txt:303, cm26/cm.txt:295 |
| `C00018036` | US Bank NA | `U.S. BANCORP POLITICAL PARTICIPATION PROGRAM` | `U.S. BANCORP` | cm22/cm.txt:162, cm24/cm.txt:158, cm26/cm.txt:156 |

Aliases were added only where a reported spelling observed in the Banking run is a
punctuation/abbreviation variant or a literal truncation of that committee's own
master name, and no other committee of that company could be denoted:
`C00009639` took three (the name without its parenthetical, the 100-character
truncation `... (FORMERLY SUNTRUST BA`, and `TRUIST FINANCIAL CORP. FEDERAL STATE
& LOCAL PAC`); `C00043489` took two (`BANK OF AMERICA STATE AND FEDERAL PAC` and
the same name with `PAC` spelled out). `C00039305`'s reported spelling is
byte-identical to its master name, so it needed none. `C00018036` has no observed
spelling that denotes it rather than the already-registered `C00488882`, so its
alias list is empty and it moves nothing - it is added because the master states
its connection unambiguously and it was missing from the register.

### 10b. What was rejected, and why

- **`PNC PAC Michigan`** - no committee of that name exists in `cm22`, `cm24` or
  `cm26` (exact and substring search over `CMTE_NM` both return nothing). It
  cannot be added without inventing an ID.
- **`JP Morgan Chase Co State and Fed PAC`** - likewise absent from the master.
  JP Morgan Chase has exactly two committees in the master, `C00104299` and
  `C00128512`, and both are already registered.
- **`Capital One Association Political Fund PAC`** - absent from the master as a
  committee name. Capital One has exactly one committee, `C00326595`, already
  registered; the reported spellings are variants of it, not a missing committee.
- **`C00150672` `GEORGIA REPUBLICAN PARTY INC.`** - its `CONNECTED_ORG_NM` reads
  `TRUIST BANK`, but the committee is a state party, not the company's PAC.
  Registering it would post a state party's receipts as Truist PAC activity.
- **`C00939330` `ROBB TUCKER FOR CONGRESS`, `C00957126` `ASHLEY WEBB: TAKE NO
  PRISONERS`** - candidate committees that matched only as false positives of the
  `BBT` stem inside `roBBTucker` and `weBBTake`. Both carry `CONNECTED_ORG_NM`
  `NONE`.
- **`C00300178` and `C00429852` (Wells Fargo)** - their `CONNECTED_ORG_NM` fields
  name *each other's committee names* rather than an organisation
  (`C00429852` -> `WELLS FARGO AND COMPANY EMPLOYEE PAC ...`, and the registered
  `C00034595` -> `WELLS FARGO AND COMPANY NORTH CAROLINA EMPLOYEES GOOD GOVERNMENT
  FUND`). The master therefore does not state a connection to Wells Fargo the
  company; establishing it takes a two-step inference through another committee.
  Left out; $36,249.76 of Banking rows turn on this and it is a data call.
- **`C00142596` `BBVA PAC OF THE PNC FINANCIAL SERVICES GROUP, INC.`** (cm22 only)
  - the committee's own name asserts the PNC connection but field 14 is blank, so
  the master does not state it. No Banking row reports this name, so it would move
  nothing. Listed as a candidate, not added.
- **`U.S. BANCORP PIPER JAFFRAY INC. FEDERAL PAC`** (6 rows / $13,750.00) - not a
  committee in any of the three cycle files, so it cannot be corroborated.

### 10c. Measured movement

Command, from `C:\Users\pgoff\Mentat\mentat`:
`python tools/run_cross_reference.py --database "C:\Users\pgoff\Mentat\mentat\.cache\report-repairs\banking-20260910\data\mentat.db" --industry Banking --offline`,
stdout at `receipts/run_banking_after_register.txt`, run `20260918T164949-17cd31b9e70f`,
against run `20260918T030844-6098810b1ae7` (`receipts/run_banking.txt`).

| Figure | Before | After | Delta |
|---|---|---|---|
| Observed original giving | $77,054,485.76 | $76,899,254.70 | -155,231.06 |
| Employee giving | $71,246,149.34 | $71,246,149.34 | 0.00 |
| Unverified funding | $5,808,336.42 | $5,653,105.36 | -155,231.06 |
| PAC activity (`pac_outgoing`) | $22,774,438.00 | $22,929,669.06 | +155,231.06 |
| Corporate giving | $0.00 | $0.00 | 0.00 |
| Review queue, rows | 46,156 | 46,125 | -31 |
| Review queue, gross | $16,990,616.89 | $16,899,116.89 | -91,500.00 |
| Observed giving against the $54,762,844.05 workbook | +$22,291,641.71 | +$22,136,410.65 | -155,231.06 |
| Baseline | $133,516,227.27 | $133,516,227.27 | 0.00 |
| Elapsed | 650.41 s | 1041.23 s | |

Rows that actually changed bucket, from a row-by-row diff of the two runs'
`ledger.sqlite` (`receipts/register_movement_decomposition.txt`):

| Company | Committee | Rows | Gross | Bucket change |
|---|---|---|---|---|
| Citibank | `C00039305` | 17 | $58,900.00 | funding_unverified -> pac_activity |
| Truist Bank | `C00009639` | 7 | $58,831.06 | funding_unverified -> pac_activity |
| Bank of America NA | `C00043489` | 10 | $37,500.00 | funding_unverified -> pac_activity |

Total 34 rows, $155,231.06 now counted as PAC activity rather than the
company's own unverified funding. `C00018036` moved nothing, as expected: it has
no alias, so no row reports a name that resolves to it.

The movement is exactly conservative. Summed over all 849,399 decisions,
`counted_cents` changed by $-155,231.06 and `pac_activity_cents` by
$155,231.06: the same dollars, reclassified, none created or destroyed.
**0 rows were newly excluded** and every one of the fifteen
exclusion reasons is row-for-row and cent-for-cent identical to the before run,
so nothing was lost to make this move.

A further 28,948 rows kept their bucket but newly cite one of the four
evidence IDs. They are not movement: they were already `pac_activity` through
their own committee ID, or - 7,057 of them - are employees giving **to**
the company PAC, whose `funding_direction` is relabelled
`original_donor_to_recipient` -> `employee_to_company_pac` by the recipient route
at `tools/cross_reference_engine.py:467-471`. No dollars move on any of them, which
is why `employee_giving` is unchanged at $71,246,149.34.

The review queue fell by 31 rows
and $91,500.00, not by the full
$155,231.06, because three of the promoted rows stay in the queue on a different
reason: two on `provisional_receipt_role:unverified_other_receipt` ($32,400.00) and
one on `provisional_receipt_role:transfer_receipt` ($31,331.06). $155,231.06 -
$63,731.06 = $91,500.00, which is the measured drop. All 34 promoted rows
dropped `company_named_unverified`, which falls 6,247 -> 6,213 rows
($5,140,809.45 -> $4,985,578.39).

### 10d. The section 6b prediction was wrong, and by how much

HANDOFF step 4 predicted "most of the $5,808,336.42 unverified-funding
line" would move. It did not, and could not. Section 6b's $4,324,780.39 is
dominated by rows the register cannot reach through `connected_pac`:

- **ORG rows** (`PNC ADVISORS`, `WELLS FARGO BANK`, `JP MORGAN CHASE`, `CITIBANK
  N A`, ...) are seeded `organization_unverified` at
  `tools/cross_reference_engine.py:261` and are tested against `treasury_entity`,
  not `connected_pac` (`:302-310`, `:455`). A `connected_pac` record never moves
  them, and a `treasury_entity` record moves them to `corporate_original`, not to
  PAC activity. `treasury_ownership_unresolved` is unmoved at 1,328 rows /
  $4,281,699.33 before and 1,328 / $4,281,699.33 after.
- **PAC-type rows whose reported spelling is not a variant of any master committee
  name** (`PNC PAC FED`, `US BANK CORP PAC`, `J P MORGAN CHASE CO PAC`, ...) can
  only be resolved by asserting which of the company's committees the spelling
  denotes. Where a company has two committees, that is an inference the master does
  not license; where it has one, it is safe but is alias work on an *existing*
  record, not a missing record, and was left for a separate ruling.

So the lever section 6b describes is real but is mostly an **alias** lever on the
twelve existing records plus a `treasury_entity` policy call, not the missing-record
lever this section closes. The measured missing-record effect is $155,231.06.

### 10e. Register defects found while doing this (not fixed)

Four aliases on the pre-existing records are another committee's verbatim master
name: `BANK OF AMERICA CORPORATION STATE AND FEDERAL PAC` on `C00364778` (it is
`C00043489`), the Truist federal/state/local name on `C00386524` (it is
`C00009639`), `U.S. BANCORP POLITICAL PARTICIPATION PROGRAM` on `C00488882` (it is
`C00018036`), and `WELLS FARGO AND COMPANY EMPLOYEES GOOD GOVERNMENT FEDERAL FUND
II` on `C00034595` (it is `C00300178`). Now that three of those committees have
their own records, a row reporting one of those names matches both records, so
`affiliations_for` returns two affiliations and the reason cites two evidence IDs.
No dollars are double counted - `:298`, `:445` and `:459` assign rather than
accumulate - but the citation is wrong on the old record. Removing those four
aliases is a data call and was left alone.

### 10f. Tests

`python -m pytest tests/test_cross_reference_engine.py tests/test_cross_reference_runner.py tests/test_cross_reference_digest.py tests/test_cross_reference_data.py -q`
(`receipts/pytest_after_register.txt`): `113 passed, 27 subtests passed in 10.63s` - the same 113 as section 8.

## 11. The two follow-ups Paul ruled on: alias fix done, treasury records withheld (2026-09-18)

Sections 1-10 are unchanged. Paul's instruction was "fix those" for both 10e (the
misfiled aliases) and the missing `treasury_entity` records. One is done; the other
hit its own tripwire and is reported instead of applied.

### 11a. The misfiled aliases: three removed, one kept

Each of the four aliases in 10e is another committee's verbatim master name. Before
touching the file I looked up every Banking row that reports each spelling
(`receipts/alias_fix_verification.txt`):

| Alias, on record | Really | Rows | Counted + PAC | Cited before | Action |
|---|---|---|---|---|---|
| `BANK OF AMERICA CORPORATION STATE AND FEDERAL PAC` on `C00364778` | `C00043489` | 43 | $158,088.00 | `C00043489` **and** `C00364778` | removed |
| `U.S. BANCORP POLITICAL PARTICIPATION PROGRAM` on `C00488882` | `C00018036` | 136 | $424,000.00 | `C00018036` **and** `C00488882` | removed |
| `TRUIST FINANCIAL CORPORATION FEDERAL, STATE & LOCAL ... (FORMERLY SUNTRUST ...)` on `C00386524` | `C00009639` | 9 | $35,000.00 | `C00009639` **and** `C00386524` | removed |
| `WELLS FARGO AND COMPANY EMPLOYEES GOOD GOVERNMENT FEDERAL FUND II` on `C00034595` | `C00300178` | 242 | $572,500.00 | `C00034595` **only** | **KEPT** |

The first three rows already matched the correct record as well as the wrong one,
because section 10 gave `C00043489`, `C00018036` and `C00009639` their own records.
Dropping the stale alias leaves the correct match standing.

The fourth is the stranding case the instruction asked me to watch for. `C00300178`
is **not** in the register - section 10b withheld it because its master
`CONNECTED_ORG_NM` names another committee rather than Wells Fargo the company - so
those 242 rows match *only* through the alias on `C00034595`. Removing it would
leave all 242 rows, $572,500.00 of observed PAC activity, with no affiliation at
all, falling into `company_pac_affiliation_unresolved`. The spelling is
`WELLS FARGO AND COMPANY EMPLOYEES GOOD GOVERNMENT FEDERAL FUND II`. It was left in
place. Registering `C00300178` properly, or accepting the two-step inference in
10b, is the fix; both are Paul's call.

After the change, measured on run `20260918T173505-84f3f46b7351`
(`receipts/alias_fix_verification.txt`): all three corrected groups cite exactly one
evidence ID - `fec-committee-C00043489`, `fec-committee-C00018036`,
`fec-committee-C00009639` - their bucket is still `pac_activity` and their
counted + PAC cents are identical to before.

### 11b. Measured effect of the alias fix: none, as intended

Run `20260918T173505-84f3f46b7351` (`receipts/run_banking_after_alias_fix.txt`) against
`20260918T164949-17cd31b9e70f`. Every summary figure is **identical**:
observed original giving $76,899,254.70, employee
giving $71,246,149.34, unverified funding
$5,653,105.36, PAC activity
$22,929,669.06, review queue
46,125 rows /
$16,899,116.89. Every review reason and every exclusion
reason is row-for-row and cent-for-cent unchanged. All summary fields equal:
**True**. Elapsed 1041.23 s -> 917.89 s. That is
the right outcome: this was a citation correction, not an accounting change.

### 11c. `treasury_entity`: the tripwire fired, so nothing was added

The register still holds zero `treasury_entity` records and `corporate_original` is
still $0.00. Applying the instructed evidence - the
`companies` table variants for Banking plus `inputs/verified_employer_aliases.csv`,
judged by the whole-token test (`receipts/treasury_entity_candidates.txt`) - selects
**1,328 ORG rows / $4,110,703.75**, which is **3.01x** the workbook's
$1,365,262.42 Corporate tier. That is past the "roughly double" tripwire, so the treasury
half was **not committed** and the alias fix was kept, exactly as instructed.

Two things make me confident the tripwire is right rather than merely cautious.

**The roster test has no discriminating power here.** It matches 1,328 of 1,328
rows; **zero** ORG rows in the bucket fail it. That is tautological: a row is in
`organization_unverified` with this company precisely because its contributor name
already names the company. Using the same test again to decide treasury ownership
adds no evidence.

**The rows are not giving.** Of the 1,328, the FEC's own line label is
`Other Federal Receipts (Dividends, Interest, etc.).` on **873 rows /
$2,629,439.21** and `Total Amount of Other Receipts` on 393 rows / $314,445.18;
only 52 rows / $47,300.88 sit on a contributions line. The engine has already
reached the same conclusion independently: **1,250 of the 1,328 rows carry
`receipt_role = unverified_other_receipt`** ($2,935,434.79) and only 71 rows
($1,153,768.96) are role `contribution`. Across the wider corporate feed the memo
text on such rows reads `INTEREST` (822), `DIVIDEND INCOME` (129), `INTEREST INCOME`
(90), `INTEREST EARNED` (32), `BANK INTEREST` (16). These are banks paying interest
on the committee's own deposit account, reported with the bank as the ORG
contributor - not the bank giving money.

**Federal-candidate check, as asked.** 415 of the matched rows,
$347,611.99, are receipts of federal candidate committees (`committee_type`
H/S/P). Corporate treasury money cannot lawfully go to a federal candidate, so every
one of those rows is evidence of a matching error rather than of treasury giving.
The pattern is unmistakable once listed: `WELLS FARGO BANK` -> `RICK SCOTT FOR
FLORIDA` $1.15; `BANK OF AMERICA` -> `FRIENDS OF CHRIS MURPHY` $46.96, $33.83,
$24.31 in consecutive months; `US BANK` -> `SENSENBRENNER COMMITTEE` $1.55, $1.50,
$1.55; `PNC BANK` -> `VOLUNTEERS FOR SHIMKUS` $49.97; `CAPITAL ONE BANK` ->
`CITIZENS FOR BOYLE` $44.41, $21.54, $26.71. Small, recurring, monthly, from the
bank that holds the account: interest, not contributions.

### 11d. The narrower candidate set Paul may actually want

Restricting to the rows the engine already calls contributions
(`receipt_role == contribution`) gives **71 rows / $1,153,768.96**, which is
**0.85x** the workbook Corporate tier - inside the tripwire. Per company:

| Company | Rows | Gross | To federal candidates |
|---|---|---|---|
| Bank of America NA | 19 | $1,010,980.39 | 0 |
| Goldman Sachs Bank NA | 8 | $109,368.19 | 3 / $6,800.00 |
| Truist Bank | 21 | $17,169.50 | 1 / -$36.00 |
| JP Morgan Chase Bank NA | 2 | $5,800.00 | 2 / $5,800.00 |
| Wells Fargo Bank NA | 7 | $4,910.96 | 4 / $1,552.91 |
| Citibank | 6 | $4,364.44 | 6 / $4,364.44 |
| Morgan Stanley Bank | 2 | $600.00 | 0 |
| PNC Bank NA | 5 | $557.00 | 3 / $2.00 |
| Capital One Bank NA | 1 | $18.48 | 1 / $18.48 |

I did not add these either, for three reasons Paul should weigh:

1. **One row is 87% of it.** A single 2021-01-12 receipt, `BANK OF AMERICA` ->
   `PIC 2021, INC.` for $1,000,000.00, carries the total. Corporate money to a
   presidential inaugural committee is lawful, so this one is plausibly real
   treasury giving - but a "Corporate tier" that is one row is a finding, not a
   tier, and the 0.85x agreement with the workbook may be coincidence.
2. **It still contains non-treasury names.** `GOLDMAN SACHS PHILANTHROPY FUND`
   ($100,000.00) and `MORGAN STANLEY GIFT FUND` ($600.00) are donor-advised funds,
   not company treasuries; `COMPUTERSHARE/KCC - CS WANG V. WELLS FARGO BANK
   SETTLEMENT` ($308.05) is a settlement administrator; `CAPITAL ONE CAFE - UNION
   SQUARE` ($18.48) is a coffee shop; several `BANK OF AMERICA` -> `COMMON POWER`
   rows are memoed `REFUND, NON-CONTRIBUTION ACCOUNT`.
3. **`CITI HEALTH HOME CARE SERVICES` is a false positive of the whole-token test**
   against the roster variant `Citi`. It is not Citibank. Two rows, $0.00, so it
   costs nothing here - but it shows the test will attach unrelated companies to a
   short roster variant, which is exactly the failure mode a treasury register
   would make permanent.

My recommendation, for Paul to accept or reject: do not build the treasury register
from a name test at all. Build it from the receipt evidence - role `contribution`,
a non-candidate recipient, and a named corporate entity - and adjudicate the
surviving handful by hand. On Banking that is a list of well under 71 rows.

### 11e. Tests

`python -m pytest tests/test_cross_reference_engine.py tests/test_cross_reference_runner.py tests/test_cross_reference_digest.py tests/test_cross_reference_data.py -q`
(`receipts/pytest_after_alias_fix.txt`): `113 passed, 27 subtests passed in 8.04s`.
