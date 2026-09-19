# Mentat cross-reference review — September 12, 2026

The review was too restrictive in identifiable, repeatable ways. On a rerun of all 849,399 Banking records, the receipt-review queue fell from **811,704 to 132,890**: 678,814 fewer records (83.6%). There are now **716,509 automatic decisions**. This is a workflow measure, not an accuracy percentage.

Scope: the latest Banking cross-reference, ten named major banks, election cycles 2022, 2024 and 2026. Its company scope matches the Banking workbook in the designated Mentat Complete Files folder. Community Banks and the other industry workbooks are separate scopes. The shared corrections apply across industries.

## What was unnecessarily strict

1. **Whole-filing completeness was being demanded for ordinary receipt decisions.** The old queue contained 561,167 records whose only questions concerned filing coverage. Clear contribution classification does not require manually reviewing every transaction in a missing filing census. Coverage now has its own grouped follow-up queue; observed conflicting versions and unresolved links remain receipt questions.
2. **Prefix checks could block stronger exact employer matches.** The scalar and batch matchers now check full approved aliases first and normalize equivalent bank legal suffixes, spacing and punctuation. The saved-data recheck accepted 79,312 historical individual-employer holds. BANK OF AMERICA, N.A.; CITI BANK; CITIBANK N.A.; JP MORGAN CHASE; and WELLS FARGO BANK pass. CITIZENS BANK is still not accepted as Citibank. An accepted employer match can still leave a separate memo or transaction question.
3. **Irrelevant attribution questions preceded obvious receipt meaning.** The old queue held 40,332 already classifiable non-giving observations. Two Truist broker-sale descriptions alone accounted for $2,040,066 of review exposure. Such observations now resolve as non-giving without pretending their corporate identity is verified.
4. **Explicit interest wording was missed.** NON-CONTRIBUTION: INTEREST, HEADQUARTERS INTEREST INCOME, RECOUNT INTEREST INCOME and exact INVESTMENT INCOME now have shared recognition rules. An account designation no longer overrides an explicit interest event. Generic form captions, contradictory gift descriptions and missing roles remain unresolved.

## Measured result

| Measure | Previous cross-reference | Revised cross-reference |
|---|---:|---:|
| Records examined | 849,399 | 849,399 |
| Automatic decisions | 37,695 | 716,509 |
| Records requiring receipt review | 811,704 | 132,890 |
| Provisional original giving | $78,233,832.96 | $68,074,184.34 |
| Employee-attributed receipts | $57,534,888.87 | $64,240,332.09 |
| Unverified funding in provisional giving | $20,698,944.09 | $3,833,852.25 |

Of the automatic decisions, 13,683 were checked against preserved exact FEC responses and 702,826 were classified from stored evidence. Filing coverage still affects 658,709 records, grouped into 11,128 tasks. Of those records, 637,902 have no outstanding receipt question. Coverage figures overlap the receipt populations and must not be added to them.

### Accounting changes from the previous cross-reference

| Mechanism | Changed records | Signed net change |
|---|---:|---:|
| Explicit interest and investment income | 456 | −$16,864,494.25 |
| Exact employer alias rechecks | 79,310 | +$6,705,443.22 |
| Existing rejected-company exclusions | 51 | −$597.59 |
| **Total** | **79,817** | **−$10,159,648.62** |

Positive changes total +$6,917,485.40; negative changes total −$17,077,134.02. They reconcile exactly in cents. These changes compare two cross-reference computations. The page also shows its separate original receipt baseline of $133,516,227.27; that is a different comparison.

### How old review items were resolved

This partition is disjoint. Employer corrections that still have another receipt question are not counted as fully resolved here.

| Resolution | Records now automatic |
|---|---:|
| Explicit non-giving receipt resolved | 40,860 |
| Exact employer alias rechecks | 77,733 |
| Existing rejected-company exclusions | 51 |
| Filing coverage separated from receipt review | 560,170 |

### Examples of changed giving decisions

| Company / cycle | Evidence | Change |
|---|---|---:|
| JP Morgan Chase Bank NA / 2026 | NON-CONTRIBUTION: INTEREST · [FEC 4090820261595886408](https://docquery.fec.gov/cgi-bin/fecimg/?202608209903328715) | −$608,896.04 |
| JP Morgan Chase Bank NA / 2026 | NON-CONTRIBUTION: INTEREST · [FEC 4071420261533989526](https://docquery.fec.gov/cgi-bin/fecimg/?202606209870958106) | −$606,046.83 |
| JP Morgan Chase Bank NA / 2026 | NON-CONTRIBUTION: INTEREST · [FEC 4060220261512109024](https://docquery.fec.gov/cgi-bin/fecimg/?202604209866614096) | −$603,210.96 |
| JP Morgan Chase Bank NA / 2026 | NON-CONTRIBUTION: INTEREST · [FEC 4081220261580775417](https://docquery.fec.gov/cgi-bin/fecimg/?202607209894265391) | −$587,896.54 |
| JP Morgan Chase Bank NA / 2024 | JP MORGAN CHASE · [FEC 4110520241050881745](https://docquery.fec.gov/cgi-bin/fecimg/?202410159698191643) | +$175,000.00 |
| JP Morgan Chase Bank NA / 2024 | JP MORGAN CHASE · [FEC 4010620251126152367](https://docquery.fec.gov/cgi-bin/fecimg/?202412059739446891) | +$123,900.00 |
| JP Morgan Chase Bank NA / 2022 | JP MORGAN CHASE & COMPANY · [FEC 4092120221576375905](https://docquery.fec.gov/cgi-bin/fecimg/?202209209528867892) | +$100,000.00 |
| PNC Bank NA / 2026 | PNC BANK · [FEC 4072920261539307443](https://docquery.fec.gov/cgi-bin/fecimg/?202607159890612554) | +$50,000.00 |

## Lessons implemented systemically

- **Shared rules:** `mentat/inputs/fec_receipt_rules.json`, the Python receipt classifier, and the R receipt classifier now agree on explicit income treatment.
- **One employer matcher:** collection, retagging and historical cross-reference rechecks use the same R matching code. The bridge opens the source database read-only. Historical rechecks release only exact approved matches, retain rejections/exclusions, and defer conflicting FEC employer inputs.
- **Separate verification dimensions:** the engine and ledger distinguish automatic receipt decisions, exact-source verification, actual receipt ambiguity and collection coverage. Complete unique-dollar evidence remains a separate claim.
- **Durable evidence:** each run saves source observations, old and new attribution reasons, matching inputs/results with SHA-256 fingerprints, rule snapshots, grouped coverage tasks and every signed accounting change.
- **Product and operating guidance:** the cross-reference page exposes the new distinctions. The methodology, README and repository agent instructions require these practices on future work.
- **Regression coverage:** positive examples and plausible counterexamples cover exact aliases, unrelated banks, persistent exclusions, conflicting employer evidence, generic versus explicit income, genuine special-account gifts, ambiguous memos, observed amendments and incomplete filings.

## Verification and remaining work

All 22 comparison checks passed, including unchanged source IDs, receipt amounts and baselines, identical preserved raw observations, and exact reconciliation of all signed changes. The source database fingerprint is unchanged. The published Banking workbook has the same SHA-256 before and after this review; the revised figures are in the cross-reference view.
Validation passed: 118 Python tests, five R suites (including report generation and 6,035 workbook formula checks), JavaScript view checks, and desktop/mobile browser checks. The complete 849,399-record offline rerun finished successfully.

The remaining queue is visible by reason below. Coverage follow-up is separate; resolving a receipt does not assert a complete filing census, ownership history or money route.

| Remaining receipt question | Records | Associated gross amount |
|---|---:|---:|
| company attribution unresolved | 93,732 | $71,115,245.50 |
| receipt role unresolved | 1,645 | $8,265,945.87 |
| treasury ownership unresolved | 1,081 | $7,810,995.09 |
| memo parent not established | 18,347 | $7,637,811.58 |
| original source of transfer unresolved | 17,461 | $5,106,997.74 |
| signed adjustment not linked refund | 703 | $2,991,347.96 |
| earmark counterpart not unique | 15,677 | $377,343.74 |
| reciprocal earmark not established | 2,122 | $300,211.08 |

Reason groups may overlap. Associated amounts are review exposure, not estimated errors or unique giving.

## Evidence and references

- [FEC receipt data reference](https://www.fec.gov/campaign-finance-data/about-campaign-finance-data/about-receipts-data/) and [investment income reporting guidance](https://www.fec.gov/help-candidates-and-committees/filing-reports/investment-income-and-loss/) support the receipt-role distinctions.
- [JPMorgan Chase official terms](https://www.jpmorganchase.com/legal/terms-and-conditions) establish the JPMorgan Chase brand relationship used for the employer alias; this is not treasury or subsidiary-ownership proof.
- [FEC conduit reporting guidance](https://www.fec.gov/help-candidates-and-committees/filing-reports/contributions-received-through-conduits/) supports keeping original gifts and memo/intermediary representations distinct.
- Revised immutable run: `20260913T025223-09b3c7578492`. Previous run: `20260912T204736-ed3b2a351279`.
- [Full machine-readable comparison](comparison.json), [initial review evidence](before-analysis.json), and [verification record](verification.json).
- [Refreshed read-only cross-reference](http://127.0.0.1:56312/#cross-reference).
