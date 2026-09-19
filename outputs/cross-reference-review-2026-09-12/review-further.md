# Mentat Banking cross-reference — further review

Date: September 13, 2026  
Final immutable run: `20260913T070028-ac0de1a54fdd`  
Original strict run: `20260912T204736-ed3b2a351279`

The original cross-reference was substantially too strict. The deeper replay confirms that **735,471 of the original 811,704 review records can be decided automatically** from evidence already present or from exact, cited identity registers. That is a 90.61% reduction in the original review queue. The final run has **773,166 automatic decisions and 76,233 records with at least one real review question** across all 849,399 source records.

This is a workflow result, not an accuracy percentage. The remaining records are still provisional where the evidence is incomplete, and complete unique-dollar coverage is not established.

## Final measured result

Scope: Banking; ten named major banks; cycles 2022, 2024 and 2026. Community Banks is a different workbook and scope. The accounting basis is original giving counted once, with recipient-reported PAC activity shown separately.

| Measure | Original strict run | Final run | Change |
|---|---:|---:|---:|
| Source records | 849,399 | 849,399 | 0 |
| Automatic decisions | 37,695 | 773,166 | +735,471 |
| Records with receipt review | 811,704 | 76,233 | −735,471 |
| Automatic classification share | 4.44% | 91.03% | +86.59 points |
| Provisional original giving | $78,233,832.96 | $72,104,550.08 | −$6,129,282.88 |
| Employee-attributed receipts | $57,534,888.87 | $70,446,737.57 | +$12,911,848.70 |
| Unverified funding in provisional giving | $20,698,944.09 | $1,657,812.51 | −$19,041,131.58 |
| Recipient-reported PAC activity | $0.00 | $22,774,438.00 | +$22,774,438.00 |

The PAC amount is a separate activity view. It is not added to original giving. Supported unique original giving remains $0 because the run does not claim complete filing and route coverage.

The final run classified 13,853 records automatically using exact preserved FEC responses and 759,313 from stored evidence. Filing coverage follow-up affects 713,707 records and $88,610,341.92; 693,255 of those records have no receipt question. Coverage is tracked separately because a missing global filing inventory does not make the meaning of a clear observed receipt ambiguous.

## How the original review queue resolved

This partition is disjoint and adds exactly to 735,471. An exact employer correction that leaves a separate memo, transfer or filing-version question is not counted as a fully resolved row here.

| Resolution mechanism | Original review records now automatic |
|---|---:|
| Explicit non-giving receipt resolved | 42,114 |
| Exact employer alias recheck | 125,490 |
| Other automatic resolution, chiefly exact dated PAC identity and preserved exclusions | 7,701 |
| Filing coverage separated from receipt review | 560,166 |
| **Total** | **735,471** |

Of the original 213,447 company-attribution holds, 173,951 are now automatic (81.50%) and 39,496 still have a review question. No previously automatic row became a review row.

## Accounting effect

The final $6,129,282.88 reduction in provisional original giving reconciles exactly in cents:

| Mechanism | Changed counted records | Signed change |
|---|---:|---:|
| Exact employer aliases | 128,466 | +$12,916,268.70 |
| Explicit interest and investment income | 1,128 | −$18,602,141.04 |
| Other explicit non-giving receipts | 175 | −$442,812.95 |
| Preserved accounting exclusions | 51 | −$597.59 |
| **Net** | **129,820** | **−$6,129,282.88** |

Positive changes total +$15,219,104.43 and negative changes total −$21,348,387.31. Both sides and the net reconcile independently. These are changes between two experimental cross-reference decisions; the accepted workbook was not edited.

The final incremental check also found 481 obvious holds missed by the preceding replay: 449 exact Wells Fargo affiliate-employer aliases and 32 explicit non-giving events. That layer changed provisional giving by +$12,847.02. One exact Truist PAC row described as `STOP PAY` removed $5,000 from the PAC activity view, demonstrating that exact organization identity does not override an explicit non-giving receipt role.

## What remains in review

The remaining reasons overlap, so these counts must not be added. Their associated amounts are review exposure, not estimated error or unique giving.

| Remaining question | Records | Associated gross amount |
|---|---:|---:|
| Company attribution unresolved | 36,248 | $37,947,436.09 |
| Memo parent not established | 19,529 | $8,522,419.98 |
| Original source of transfer unresolved | 18,696 | $5,789,063.20 |
| Receipt role unresolved | 754 | $2,337,747.17 |
| Treasury ownership unresolved | 476 | $1,538,125.53 |
| Signed adjustment not linked to refund | 641 | $1,127,074.41 |
| Observed filing versions unresolved | 1,148 | $526,514.04 |
| Earmark counterpart not unique | 15,915 | $383,125.12 |
| Reciprocal earmark not established | 2,168 | $328,691.08 |

The largest residual employer patterns show why further fuzzy automation would be unsafe:

- Citibank prefix holds include `CITIZENS BUSINESS BANK` (7,282 records), `CITIZENS BANK` (4,530), `CITIZENS` (679), and many other unrelated Citizens organizations.
- PNC holds include typo-only strings such as `PNCA` (1,387) and `PNCSD` (379).
- Wells Fargo includes `WELLS FARGO BANK (RETIRED)` (1,097), where the qualifier changes the employment assertion.
- Bank of America includes `BANK OF AMERICA MERCHANT SERVICES` (253) and the typo `BANK OF AMERICAL` (224), which need dated identity or employment evidence rather than prefix inference.
- US Bank includes the unrelated `US BANKRUPTCY COURT` (215).
- PAC, organization and committee rows with blank employer fields require entity or relationship evidence; an employer alias cannot answer them.

Those examples are counterexamples in the regression suite. Broad prefix, edit-distance or substring expansion would convert obvious false positives along with true aliases.

## Systemic implementation

- `mentat/inputs/verified_employer_aliases.csv` is the evidence-backed exact employer register. Each row records the company, exact alias, source URL and evidence note.
- `mentat/inputs/verified_company_affiliations.json` is the dated exact PAC register. It records FEC committee IDs, canonical names, observed exact aliases, relationship dates and source URLs.
- `mentat/R/collect.R` evaluates the exact alias register before prefix heuristics and returns the supporting evidence. Collection and historical rechecks use the same matcher.
- `mentat/inputs/fec_receipt_rules.json` now contains shared exact descriptions and anchored field-level non-giving and transfer patterns. `mentat/R/collect.R` and `mentat/tools/pac_evidence.py` consume the same rules.
- `mentat/tools/cross_reference_engine.py` accepts PAC affiliation only by exact committee ID, exact normalized canonical name or listed exact alias within its evidence dates. It keeps PAC activity out of original giving.
- `mentat/tools/run_cross_reference.py` loads the verified PAC register by default and fingerprints and snapshots the employer alias register on every run.
- `mentat/tools/recheck_attribution.R` and `.py` preserve prior decisions and attach alias evidence to every accepted historical recheck.
- `mentat/README.md`, `mentat/METHODOLOGY.md` and `mentat/AGENTS.md` now make these rules part of the project contract, including the requirement that near names, typos and prefixes remain review.

The tests include true exact aliases, Citizens-vs-Citi, US Bankruptcy Court-vs-US Bank, contribution-plus-refund conflicts, explicit financial income, fee reversals, fraud recovery, bank errors, exact PAC aliases, near PAC names and PAC non-giving events.

## Verification

- The end-to-end comparison passed all **22 of 22** invariants: identical source-ID coverage, one decision per source ID, unchanged source amounts, unchanged baselines, unchanged company/cycle scope, preserved raw observations, preserved financial identities, identical source database hash, and exact positive, negative and net reconciliation.
- Source database SHA-256 before and after: `4abdea581b99cec1674252ee098ab6afca57674bd8e90313e9f4156e88b2d991`.
- Published Banking workbook SHA-256 remains `842ba7a2312ffb03d969e8452c970b32f227fd09befcbf80f935a63c94e97bd3`.
- The final ledger SHA-256 is `4490854b79a9a65982279e09f783300e40b2e808c4109006b5266f70bb14fdfa`.
- The final regression pass completed 123 Python tests, three shared R rule suites, the JavaScript cross-reference view check, Python compilation, JSON validation and diff whitespace checks.
- `mentat/state/cross-reference/latest.json` points to the completed final run.

One successful intermediate run was compressed after its archive entries and hash were verified to manage local storage. Its archive remains at `mentat/state/cross-reference/20260913T054905-dc11ad68c0c8.tar.gz` with SHA-256 `1679c4f1eb0e636c33f579027de326c5f167b809de0585da4e5999b8aaf6c2ec`.

## Evidence and machine-readable artifacts

- [FEC receipts data reference](https://www.fec.gov/campaign-finance-data/about-campaign-finance-data/about-receipts-data/)
- [FEC investment income and loss guidance](https://www.fec.gov/help-candidates-and-committees/filing-reports/investment-income-and-loss/)
- [FEC Bank of America PAC record](https://www.fec.gov/data/committee/C00364778/), [FEC Citigroup PAC record](https://www.fec.gov/data/committee/C00008474/), [FEC JPMorgan Chase PAC record](https://www.fec.gov/data/committee/C00128512/), [FEC Truist PAC record](https://www.fec.gov/data/committee/C00386524/), and [FEC Wells Fargo PAC record](https://www.fec.gov/data/committee/C00034595/)
- [Bank of America affiliate disclosure](https://www.bankofamerica.com/security-center/affiliate-companies/), [Capital One legal disclosures](https://www.capitalone.com/digital/disclosures/), [Morgan Stanley subsidiary list](https://www.morganstanley.com/about-us-ir/subsidiaries), [PNC company information](https://investor.pnc.com/company-information), and [Wells Fargo Advisors disclosure](https://www.wellsfargo.com/help/investing/brokerage-client-service-center/)
- Machine comparison: `outputs/cross-reference-review-2026-09-12/final-comparison.json`
- Final residual profile: `outputs/cross-reference-review-2026-09-12/remaining-profile-final.json`
- Final run report: `mentat/state/cross-reference/20260913T070028-ac0de1a54fdd/report.json`

## Limits

The run still reports `verified_unique: false`. Legacy query evidence does not establish a complete filing inventory; observed amendment families and route links do not prove that every later filing or representation was collected. Recipient-reported PAC activity is not a complete Schedule B spending census. Automatically classified records establish reproducible decisions from the available evidence, not complete or error-free real-world coverage.
