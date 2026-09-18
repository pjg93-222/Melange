# Step-2 report of the first xref re-examination agent (Fable, 2026-09-17 ~14:30 ET) plus Paul's rulings

The agent that wrote sections 0 to 5 could not be resumed (its transcript was lost when the parent session re-attached). Its scratch scripts and outputs survive in
`C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-evidence-csv-fetch-streaming-8bedff\ca67743e-065c-4f84-b974-e92f86a7d7ed\scratchpad\` (`xref_split.py`, `xref_split2.py`, `head_engine_probe.py`, `xref_split_out.txt`, `xref_split2_banking.txt`, `xref_split2_fintech.txt`). Reuse them; re-verify any number you quote.

## Paul's rulings on this report (2026-09-17, "Your suggestions are correct")

- **D1:** a row whose own non-blank text names another identifiable organisation (not the listed company or any alias) is a CONTRADICTION: exclude under new reason `attribution_contradicted_by_text`, status `excluded_with_evidence`. Rows whose text names the listed company or an alias (whole-token match on the company variants plus `verified_employer_aliases.csv`, short tokens PNC/CITI/BOFA/TRUIST/US BANK included) stay counted and flagged under `company_named_unverified`. Blank / NOT EMPLOYED / NONE / N/A text stays counted and flagged. Never attribute a row to a different listed company on this test.
- **D3:** adjacent-position markers adopted: ADVISOR / ADVISER / ADVISORY, CONSULTANT / CONSULTING, CONTRACTOR, TRUSTEE, PARTNER, COUNSEL, BOARD (member / of directors). DIRECTOR excluded (bank job rank). RETIRED is not a marker (main session's call; those rows already name the company and count). The role route upgrades verification status only (unverified → role_supported) when a marker is present AND the text names the listed company or its affiliate.
- **D4:** register data is Paul's to add later; do not edit `verified_company_affiliations.json` or alias CSVs; list the gaps in REVIEW.md with counts (C00039305 Citigroup PAC-State; own PACs as donors: Truist Financial Corp Federal State Local PAC, JP Morgan Chase Co State and Fed PAC, PNC PAC Michigan, Capital One Association Political Fund PAC → PAC activity, not unverified funding).
- Main session's calls: short-token matches count flagged; `observed_filing_versions_unresolved` stays counted and flagged with the $344,433.54 probable-duplicate figure reported; the dead run `20260917T174138` is superseded by the re-run (do not delete; note that `latest.json` moves). Recipient route: `recipient_is_dated_company_pac` upgrades status to recipient_supported; add a connected-organisation lookup against `inputs/fec_committee_master/cm{22,24,26}/cm.txt` field 14.

---

# Mentat cross-verification logic: reason-code table, the 36,241-row split, and what to change

## 0. Premise check — the ground moved under the brief

1. **HEAD already applies Paul's first ruling to the one reason that zeroed dollars.** `c62cc6eb6 Cross-reference excludes only on contradiction; ambiguity counts with an unverified flag; outliers are relative` (Paul Goff, 13:46:57 today) and `7d364883e Export gate refuses only self-contradicting receipts…` (13:56:38). The engine diff removes `attribution_review`, `exclude(sid, "company_attribution_unresolved")` and the `held_for_attribution_review` status, and replaces them with `reason(sid, "company_attribution_unverified")` + a review item while `counted_cents` stays at face value. `python -m pytest tests/test_cross_reference_engine.py tests/test_cross_reference_runner.py tests/test_cross_reference_digest.py tests/test_cross_reference_data.py -q` → `108 passed, 27 subtests passed`. No uncommitted diff on any cross-reference file. Brain records this as D-040. (Main session re-verified: HEAD f0ec60b74 > 7d364883e > c62cc6eb6; xref files clean; 108 passed.)
2. **The numbers Paul saw came from the older engine.** Banking run `20260913T074303-bca0ac2b9cd3` carries its own `rules/tools/cross_reference_engine.py` (fingerprint `fc4acd00…`); `diff` against HEAD shows exactly the c62cc6eb6 hunks, so the $37.9M zeroing is the snapshot's `:248-251` / `:264-268`, now HEAD `:262-268` / `:281-296`.
3. **A Banking re-run on the HEAD engine was started today and died.** `state/cross-reference/20260917T174138-ec8ba8ba4523/` (13:41; engine identical to HEAD; progress.json `"detail": "10 companies; 3 cycles"`, identify/connect `"running"`, `updated_at 17:46:12Z`) has no `ledger.sqlite` and no `report.json`; no `run_cross_reference.py` process alive at 14:15. `state/cross-reference/latest.json` points at that dead run.

Smaller premise corrections: the labels at `app/cross-reference.js:33-36` no longer exist — commit `d78265927` dwarfed the tab to clear refunds and obvious outliers and the current file has no reason vocabulary (old labels only in `app/cross-reference.js.bak-20260917-s5:33-34`); `attribution_unresolved` was never a third population, it was the snapshot's **bucket** name for the same 36,241 rows (`totals.by_bucket.attribution_unresolved: records 36241, counted_cents 0`).

## 1. Reason-code table (HEAD engine `tools/cross_reference_engine.py`, Banking run numbers)

Anchors verified against the current file. Council anchors map: register exact-key match `:146` → `:149` (`name_key(candidate) == name_key(reported_name)` inside `affiliations_for`, `:138-157`); transfers `:283-289` → `:307-311`; memo legs `:424-451` → `:441-475`; earmark legs `:456-500` → `:477-524`. "Gross" = positive + |negative|. "Baseline" = what the accepted report (workbook source) counted for the same rows (`decisions.baseline_cents`).

### 1a. Reasons that remove dollars (`exclude()`, status `excluded_with_evidence`)

| Reason code | Decided at | Test the engine applies | Class | Banking rows / gross / baseline removed | Effect |
|---|---|---|---|---|---|
| `non_giving_receipt_role:other_receipt` | `:274-280` via `pac_evidence.receipt_role` (`inputs/fec_receipt_rules.json` + non-giving description patterns) | The filing's own schedule line or description says it is not a gift: F3X line 13 (loans), 15/16 (offsets, refunds of contributions made), line 17 with INTEREST/DIVIDEND | CONTRADICTION | 45,731 / $100,095,060.72 / $74,203,829.46 (ten Bank of America LOAN rows F3X-13 $40.06M; 4,813 INTEREST rows F3X-17 $37.0M; 36,133 CONTRIBUTION REFUND PAC rows F3X-16 $1.29M) | Keep. 7d364883e narrowed the R gate; the Python twin (`pac_evidence.py`) differs from the snapshot by `receipt_line_code` recovery and the `unverified_contradicted_receipt` verdict, so a re-run moves some line-17 rows from excluded to counted-flagged. |
| `non_giving_receipt_role:asset_liquidation` | same, `sale_identity_pattern` + `sale_event_pattern` | Description says stock/asset sold | CONTRADICTION | 6 / $2,204,936.88 / $44,105.77 | Keep |
| `company_attribution_not_accepted` | `:250-255` | Upstream matcher recorded `company_match_status` REJECTED/EXCLUDED | CONTRADICTION by label only: the R matcher's REJECTED is a prefix heuristic (`employer_prefix_not_verified` 29,108 rows; `corporate_query_individual_entity` 4,715): "FIRST CITIZENS BANK"→Citibank rejected (1,951) but "CITIZENS BANK"→Citibank left in REVIEW (4,535); "US ARMY AND US BANK"→US Bank rejected (3,832) | 33,827 / $7,258,142.81 / $0.00 | Keep; D1's text test becomes the real contradiction line |
| `preexisting_source_exclusion:<policy>` | `:240-244`, `:263-265`, `:287-290` | Explicit `excluded_reason` from the source workbook policy | CONTRADICTION (recorded decision) | 0 | Keep |
| `superseded_in_observed_filing_family` | `:382-397` | Same committee, root filing, transaction id, higher amendment observed | CONTRADICTION | 29 / $2,996.00 / $2,496.00 | Keep |
| `absent_from_complete_latest_filing` | `:425-431` | Complete latest-filing manifest lacks this id | CONTRADICTION | 0 | Keep |
| `explicit_same_filing_memo_reference` | `:452-471` | Memo leg with explicit back-reference to a counted parent, same filing/donor/date/sign, parent ≥ memo | CONTRADICTION (proven duplicate) | 63 / $139,623.55 / $127,863.55 | Keep |
| `same_original_gift_at_conduit_and_destination` | `:486-523` | Reciprocal EARMARKED FOR / THROUGH text, same company/donor/date/amount/ZIP, one-to-one | CONTRADICTION (proven duplicate) | 291 / $35,151.83 / $32,370.00 | Keep |
| *(snapshot only)* `company_attribution_unresolved` | snapshot `:248-251`, `:264-268` | status not ACCEPTED/REJECTED/EXCLUDED, or ACCEPTED with blank company | AMBIGUITY as labelled; 89% of dollars name a different organisation | 36,241 / $37,940,955.71 / $0.00 | Count-with-flag at HEAD; split per §2b and D1 |

### 1b. Reasons that move dollars between ledgers (not lost)

| Reason code | Decided at | Test | Effect |
|---|---|---|---|
| `separate_observed_pac_activity` | `:319-327` | Entity PAC/COM/CCM/PTY and `contributor_id` matches `C\d{8}` | `counted_cents`→0, `pac_activity_cents`=amount ("PAC outgoing", $22,774,438.00 Banking). `corporate_giving` source rows carry no `contributor_id` (all 8,814 entity rows in the 36,241), so unverified PAC-named rows land in `funding_unverified`, inside observed original giving. |
| `explicit_observed_refund` | `:548-556` | Explicit `adjustment_type=REFUND` + `refund_of_sub_id` + evidence id, parent counted, dated after | Negative kept in `linked_refund`. 0 in Banking. |

### 1c. Reasons that flag but keep the money (review queue; "unresolved exposure")

All already retained in the snapshot run; ledger confirms counted + pac equals gross for each (e.g. `memo_parent_not_established ids=19529 gross=$8,522,419.98 counted=$7,882,419.98 pac=$640,000.00`).

| Reason code | Decided at | Test | Class | Banking rows / gross | Effect |
|---|---|---|---|---|---|
| `company_attribution_unverified` (HEAD) | `:281-296`; conflicted variant `:262-268` | REVIEW / blank / unrecognised status, or ACCEPTED with no company | AMBIGUITY as labelled | (36,241 / $37.94M on re-run) | Split per D1 |
| `memo_parent_not_established` / `memo_parent_ambiguous` | `:472-475` | Memo leg with no (or >1) qualifying same-filing parent | AMBIGUITY | 19,529 / $8,522,419.98 | Keep counted + flagged |
| `original_source_of_transfer_unresolved` | `:307-311` | Role transfer_receipt (line 12/18) | AMBIGUITY | 18,696 / $5,789,063.20 | Keep |
| `receipt_role_unresolved` | `:307-311` | Role neither contribution nor transfer | AMBIGUITY | 725 / $2,336,852.79 | Keep |
| `treasury_ownership_unresolved` | `:337-346` | ORG contributor with no dated treasury_entity affiliation | AMBIGUITY (register has 0 treasury records) | 448 / $1,537,481.15 | Keep; register work is the fix |
| `company_pac_affiliation_unresolved` | `:337-346` | PAC-bucket donor with no dated connected_pac match | AMBIGUITY | 0 in snapshot | Keep |
| `signed_adjustment_not_linked_refund` | `:528-547` | Negative amount without explicit refund link | AMBIGUITY; negative counted as negative | 641 / $1,127,074.41 | Keep |
| `observed_filing_versions_unresolved` | `:571-584` | Same committee/transaction id/company/donor/date ≥2 times, headers missing | AMBIGUITY; all 389 groups identical amounts: probable duplicate dollars counted $344,433.54 | 1,148 / $526,514.04 | Keep counted; report the figure |
| `earmark_counterpart_not_unique` / `reciprocal_earmark_not_established` / `earmark_destination_ambiguous` / `overlapping_or_cyclic_earmark_links` | `:494`, `:501`, `:512`, `:521` | Earmark language present, route not provable | AMBIGUITY | 15,915 / $383,125.12; 2,168 / $328,691.08; 89 / $737.06; 0 | Keep |
| `funding_identity_unresolved` | `:328-329` | Entity not IND/ORG and no `C\d{8}` id | AMBIGUITY | 73 / $121,130.46 | Keep |
| `source_or_attribution_conflict` | `:259-273`, `:299-306` | Conflicting stored observations or >1 company claim | AMBIGUITY | 4 / $375.00 | Keep |
| `ambiguous_amendment_order` / `amendment_changes_company_identity` | `:386`, `:391` | Tied or company-changing versions, all counted | AMBIGUITY | 24 / $17,674.00 | Keep |
| `receipt_date_missing`, `pac_identity_conflict`, `latest_filing_manifest_not_corroborated`, `latest_filing_transaction_replacement_missing`, `linked_refunds_exceed_original_gift` | `:315`, `:323`, `:423`, `:433`, `:550` | as named | AMBIGUITY | 0 each | Keep |

Coverage-only: `filing_relationship_evidence_missing` `:561` (290,244 rows / $47.98M), `latest_filing_completeness_unproven` `:565` (423,434 / $40.63M). Informational, no dollar effect: `automatic_exact_alias_recheck`, `connected_pac_affiliation`, `treasury_entity_affiliation`, `recognized_contribution_receipt`, `individual_with_accepted_employer_match`, `recipient_is_dated_company_pac` (150,828 rows; the recipient route already exists as a marker at `:347-353` but never upgrades `attribution_status`), `complete_latest_filing_inventory`, `retained_original_earmarked_receipt`, `negative_amount_is_not_refund_proof`, `non_giving_resolved_without_company_attribution`, `excluded_source_metadata_conflict`, `supplied_unique_origin_certificate`.

## 2. What the 36,241 rows actually are

`review_queue` items with that reason → `source_records` in the run ledger (36,241 ids, gross $37,940,955.71). **Baseline (accepted-report) dollars on these rows: $0.00**; the workbook never counted them; the question is whether to add them.

Per company: Citibank 26,716 / $29,750,344.21; Bank of America 2,804 / $3,267,121.13; Wells Fargo 2,340 / $1,575,766.94; PNC 2,459 / $1,272,230.03; JP Morgan 473 / $798,019.98; Capital One 385 / $379,250.97; Goldman 92 / $302,181.70; US Bank 488 / $257,436.14; Truist 262 / $212,497.68; Morgan Stanley 222 / $126,106.93.

| Class | Rows | Gross | What the text says |
|---|---|---|---|
| `corporate_giving` entity rows (PAC 5,828 / ORG 1,552 / COM 869 / CCM 508 / PTY 9 / blank 35) + 13 CAN, all `corporate_name_not_verified` | 8,814 | $33,969,321.45 | FEC keyword hits on contributor name: STATE GOVERNMENT CITIZENS CAMPAIGN $4.31M, END CITIZENS UNITED $4.16M (+ variants), CITIZENS ALLIANCE PAC $2.40M, CITIZENS TO ELECT RICK LARSEN $1.92M, INDEPENDENT COMMUNITY BANKERS OF AMERICA PAC $1.34M + $1.03M + $0.26M, CITIZENS UNITED POLITICAL VICTORY FUND $0.87M, TARGET CITIZENS POLITICAL FORUM $0.79M |
| `contributions` IND rows, `squashed_prefix_unverified_remainder:*` and `prefix_with_unverified_trailing_tokens:*` | 27,427 | $3,971,634.26 | CITIZENS BUSINESS BANK (7,282 rows), CITIZENS BANK (4,535), PNCA (1,387), WELLS FARGO BANK RETIRED (1,105), CITIZENS (679), PNCSD (379) |

### 2a. Route split (recipient A > recipient B > role > neither)

| Route | Rows | Gross |
|---|---|---|
| Recipient A: recipient committee in `verified_company_affiliations.json` for the row's company | 166 | $61,105.75 (PNC 104 / $19,505.88; JPM 38 / $950; Citi 18 / $1,569.06; WF 5 / $7,749.75; Truist 1 / $31,331.06) |
| Recipient B: committee-master `CONNECTED_ORG_NM` resolves to the company, not in the register | 2 | $1,000.00 (both via `C00039305 CITIGROUP INC. PAC - STATE`) |
| Role: advisor/adjacent marker and the text names the listed company (IND only) | 1,926 | $311,080.06 |
| Neither | 34,147 | $37,567,769.90 (PAC $22.50M, ORG $4.71M, IND $3.64M, COM $3.35M, CCM $3.25M, rest $0.14M) |

### 2b. Does the row's own text name the company? (whole-token match on company variants + `verified_employer_aliases.csv`)

| Sub-class | Rows | Gross | Examples |
|---|---|---|---|
| Entity: contributor name is another organisation | 7,682 | $30,656,879.08 | END CITIZENS UNITED, ICBA PAC, CITIZENS FOR WATERS, PEPSICO CONCERNED CITIZENS FUND, CITIZENS BANK (ORG, 341 rows / $348k), CITIZENS FINANCIAL GROUP PAC |
| Entity: name resolves to the listed company | 1,132 | $3,312,442.37 | WELLS FARGO PAC ACCOUNT $621,580.67, WELLS FARGO BANK $480,929.48, JP MORGAN CHASE $310,994.69, JP MORGAN CHASE NA $197,361.95, GOLDMAN SACHS PHILANTHROPY FUND $100,000, CITIGROUP INC PAC STATE $58,900, CITIBANK N A $53,998.66, TRUIST FINANCIAL CORP FEDERAL STATE LOCAL PAC $31,331.06 |
| IND: employer is another organisation | 22,459 | $3,152,651.38 | CITIZENS 1ST BANK $723,235 (85 rows), CITIZENS ADVICE BUREAU $550,000 (2 rows), CITIZENS FIRST BANK $499,129.50, CITIZENS BANK $382,262.86, CITIZENS BUSINESS BANK $203,225.05, PNCA $20,912.08, US BANKRUPTCY COURT $7,057.37 |
| IND: employer names the company (long alias) | 3,962 | $721,636.80 | GOLDMAN SACHS AND CO $107,900, MORGAN STANLEY PRIVATE WEALTH MANAGEME $73,838.44, WELLS FARGO BANK RETIRED $68,710, MERRILL LYNCH WEALTH MANAGEMENT $40,869.23, JP MORGAN ASSET MANAGEMENT $32,743.31, BANK OF AMERICA MERCHANT SERVICES $9,402.34 |
| IND: short-token word match only | 843 | $75,736.39 | PNC CAPITAL FINANCE LLC $10,768.80, PNC ALLIANCE LLC, CITI COMMUNITY CAPITAL, TRUIST INSURANCE HOLDINGS, US BANK CDC; strangers CITI TRENDS $775, CITI HEALTH HOME CARE $1,500, CITI URBAN MANAGEMENT $6,160 |
| IND: recipient is the company's registered PAC | 163 | $21,609.69 | (route A) |

Blank / "not employed" / "retired"-only employers among the unnamed IND rows: 0 rows, $0.00.

### 2c. What HEAD does with these today (`head_engine_probe.py` against live `tools/cross_reference_engine.analyze`)

```
sub_id=1 entity=PAC 'END CITIZENS UNITED'      counted_cents= 500000 bucket=funding_unverified  status=needs_review  reasons=['company_attribution_unverified', 'recognized_contribution_receipt']
sub_id=2 entity=IND 'CITIZENS BUSINESS BANK'   counted_cents=  25000 bucket=employee_original   status=needs_review  reasons=['company_attribution_unverified', ...]
sub_id=3 entity=IND 'WELLS FARGO BANK RETIRED' counted_cents=  10000 bucket=employee_original   status=needs_review  reasons=['company_attribution_unverified', ...]
sub_id=4 entity=IND 'FIRST CITIZENS BANK'      counted_cents=      0 bucket=excluded_company_match status=excluded_with_evidence reasons=['company_attribution_not_accepted']
totals: provisional_original_giving_cents= 535000
```

As committed, a Banking re-run counts End Citizens United as Citibank "unverified funding" and Citizens Business Bank staff as Citibank employees while excluding First Citizens Bank staff; observed original giving would rise from $72.1M toward ≈$110M (workbook $54.76M), ≈$33.8M of it from rows naming a different organisation. D1 fixes this.

## 3. Marker vocabulary (role route), Banking, over the 36,241 rows

| Marker (regex on occupation ∪ employer) | Any row: rows / gross | With company named: rows / gross | Ruling |
|---|---|---|---|
| ADVISOR / ADVISER / ADVISORY | 327 / $172,430.75 | 276 / $166,926.11 | adopted |
| CONSULTANT / CONSULTING | 467 / $752,514.44 | 236 / $20,474.50 | adopted |
| DIRECTOR (any) | 1,394 / $734,481.91 | 68 / $43,053.00 | NOT a marker (bank rank) |
| BOARD (member / of directors) | 122 / $9,887.72 | 0 / $0 | adopted |
| TRUSTEE | 8 / $1,682.00 | 1 / $1,000.00 | adopted |
| COUNSEL | 95 / $6,114.32 | 0 / $0 | adopted |
| CONTRACTOR | 24 / $4,860.24 | 17 / $4,206.24 | adopted |
| PARTNER | 100 / $8,215.83 | 3 / $3,650.00 | adopted |
| RETIRED | 1,590 / $89,809.44 | 1,352 / $81,021.44 | NOT a marker; rows count because they name the company |
| SELF / SELF-EMPLOYED | 154 / $17,257.49 | 119 / $473.49 | not a marker |
| VENDOR / SUPPLIER | 209 / $1,582.12 | 0 | not a marker |

Union of all markers with company named: 1,926 rows / $311,080.06; the role route changes verification status, not whether dollars count.

## 4. Decisions (as ruled; see top of file)

D1 text split (`company_named_unverified` counted-flagged 6,100 rows / $4,131,425.25; `attribution_contradicted_by_text` excluded 30,141 rows / $33,809,530.46); D2 short-token count flagged; D3 markers as adopted; D4 register data note; D5 `observed_filing_versions_unresolved` counted, $344,433.54 reported; D6 dead run superseded.

Fintech, for step 4: `company_attribution_unresolved` 10,302 rows / $8,558,568.42 (run `20260911T010907`, no `affiliations.json`); text split: entity-other-organisation 73 rows / $5,959,699.20 (one $5,000,000 row from BLOCKCHAIN COM INC under Cash App), IND-other 8,643 / $614,425.15, named 192 / $77,813.99, short-token 708 / $176,826.08. Caveat: the Cash App variant "Block" matched H&R BLOCK INC PAC rows ($1.05M) as "resolves to company"; check the Fintech variant list before quoting Fintech numbers as final.

## 5. Steps 3–6

- Code (engine, plus `run_cross_reference.py` summary if needed): the D1 text test and two sub-codes; recipient-route status upgrade at `:347-353` + committee-master connected-org lookup; role-route marker check. No tab change (D-040 dwarfed the tab; no "counted at $0" text exists, so the `test_studio_wording.cjs` relabel is moot).
- Tests: text-contradiction exclusion; company-named row stays counted-flagged; recipient route; role route status (CONSULTANT + company → role_supported; RETIRED → unverified); proven duplicate memo leg still excluded. Four-file pytest suite (108) stays green.
- Re-run Fintech (28–68 s historically) then Banking (558.84 s on 13 Sep); per-reason before/after against the $54.76M workbook; packet under `audits/mentat_xref_logic_20260917/` (holds BRIEF.md).
