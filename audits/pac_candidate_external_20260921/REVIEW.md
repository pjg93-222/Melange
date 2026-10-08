# External PAC candidate-spending audit — September 21, 2026

Completed: 2026-09-21T04:31:44.268512+00:00

## Result

CULAC / America's Credit Unions PAC (C00007880): all nine independent-spending candidate/cycle entries already present in the Credit Union report are supported by current FEC regular-report records. These are expenses supporting candidates, not money received by the candidate campaigns. Bacon's 2022 $450,000 and Lawler's 2024 $400,000 are genuine.

The broader saved data is **not entirely current or correct**. The review identifies:

- Whole-dollar precision loss in the PAS2 source, demonstrated against exact Schedule E values. It does not explain away the large CULAC expenditures.
- A missing 2026 CULAC expenditure: Ben McAdams, $299,999.87. The saved Credit Union report contains Young Kim's $500,000 but no McAdams entry.
- **21 understated Congressional Leadership Fund (C00504530) candidate/direction totals for 2022**, totaling $7,300,261.00 below the already-preserved local whole-dollar source rows. This is a data-processing issue, not new 2026 spending. The old maximum-filing-per-transaction-label rule reproduces all 21 saved totals exactly while dropping distinct candidate expenses under recycled transaction labels.
- Current 2026 FEC records differ from numerous saved report totals. These are reported as refresh/reconciliation differences; the comparison does not presume every difference is an application defect.
- The saved PAC API snapshots agree exactly on all 122 candidate/direction groups they contain; current records add 12 groups in 2026.

No production workbook, source database, imported file, or application code was edited. New downloaded evidence and analysis are isolated in this audit directory. Existing September 20 review notes record related version-policy corrections in code but explicitly say published reports were not rebuilt. This review verifies the remaining saved-report differences; it does not claim deployment or rebuilding has occurred.

## Scope and method

Read all eight designated `*Industry Spending Overview.xlsx` reports from `C:/Users/pgoff/OneDrive/Desktop/Mentat Complete Files`; Excel lock files were excluded. Read the Downstream Activity sheet and preserve each report's cycle and accounting basis. The scope here is independent-spending Support/Oppose entries analogous to Bacon and Lawler, not every direct contribution, employee receipt, or legal contribution-limit question.

The workbooks contain 22,650 independent-spending report entries representing 8,818 distinct committee/cycle/candidate/direction groups. Overlapping reports were compared separately, never added. They contain 8,934 distinct amount claims because some workbooks contain different vintages of the same group.

Fresh official FEC PAS2 files for 2022, 2024 and 2026 were downloaded, hashed and retained. For the saved included-spending basis, non-memo rows were grouped by exact committee, cycle, candidate ID and support/oppose code; exact repeated source IDs were counted once. 8,689 distinct amount claims match that current whole-dollar bulk comparison exactly. All exceptions were queried against current regular-report Schedule E data, with pagination exhausted and 24/48-hour notices excluded.

For duplicated API records, a comparison counted the same filing number + transaction ID + candidate + direction + amount + expense/dissemination dates + payee + purpose only once. This resolves eight additional distinct amount claims (six from 2022 and two from 2024). Records merely sharing an amount were never merged. A malformed or changed image-number field did not create a second transaction.

The remaining unique amount-claim categories are recorded in `external_exceptions.json`. This is a reconciliation of the existing non-memo included basis, not certification that excluding every memo item captures every unpaid independent-expenditure obligation. The FEC cautions that memo items can disclose unpaid activity. A matching amount does not independently validate every name, underlying ad, campaign coordination, or donor-to-candidate attribution. Missing source groups were not treated as proven zero spending.

## CULAC: all candidate spending in current regular reports

| Cycle | Candidate | Saved Credit Union report | Exact FEC amount | Result |
|---|---|---:|---:|---|
| 2022 | [BACON, DONALD REP.](https://docquery.fec.gov/cgi-bin/fecimg/?202210189537551894) | $449,999.00 | $450,000.00 | Supported; whole-dollar source loses cents |
| 2022 | [KUSTER, ANN MCLANE REP.](https://docquery.fec.gov/cgi-bin/fecimg/?202301259574960322) | $256,323.00 | $256,323.00 | Supported; exact match |
| 2022 | [VALADAO, DAVID REP.](https://docquery.fec.gov/cgi-bin/fecimg/?202301259574960321) | $249,999.00 | $250,000.00 | Supported; whole-dollar source loses cents |
| 2022 | [LURIA, ELAINE G. REP.](https://docquery.fec.gov/cgi-bin/fecimg/?202210189537551895) | $243,084.00 | $243,084.00 | Supported; exact match |
| 2022 | [PAPPAS, CHRIS REP.](https://docquery.fec.gov/cgi-bin/fecimg/?202301259574960323) | $200,730.00 | $200,730.00 | Supported; exact match |
| 2024 | [TESTER, JON SEN.](https://docquery.fec.gov/cgi-bin/fecimg/?202501309748316996) | $999,915.00 | $999,915.50 | Supported; whole-dollar source loses cents |
| 2024 | [LAWLER, MICHAEL REP.](https://docquery.fec.gov/cgi-bin/fecimg/?202501309748316999) | $399,999.00 | $400,000.00 | Supported; whole-dollar source loses cents |
| 2024 | [FITZPATRICK, BRIAN REP.](https://docquery.fec.gov/cgi-bin/fecimg/?202501309748316998) | $400,000.00 | $400,000.00 | Supported; exact match |
| 2026 | [KIM, YOUNG REP.](https://docquery.fec.gov/cgi-bin/fecimg/?202605209870051835) | $500,000.00 | $500,000.00 | Supported; exact match |
| 2026 | [MCADAMS, BEN](https://docquery.fec.gov/cgi-bin/fecimg/?202607209890921089) | Absent | $299,999.87 | Missing from saved report |

All ten current candidate groups are Support. Totals reconcile exactly to the FEC committee financial summary: 2022: $1,400,137.00, 2024: $1,799,915.50, 2026: $799,999.87.

Independent corroboration:

- [Nebraska Credit Union League, October 14, 2022](https://www.ncultheaffiliate.com/?p=4330) describes the CULAC independent-expenditure campaign supporting Don Bacon, including advertising featuring a retired Cobalt Credit Union executive.
- [America's Credit Unions, October 16, 2024](https://www.americascreditunions.org/news-media/news/credit-unions-support-rep-fitzpatrick-direct-mail-digital-advertising) confirms the Fitzpatrick campaign. Exact dollars are verified from FEC records, not inferred from this announcement.
- [America's Credit Unions, June 1, 2026](https://www.americascreditunions.org/news-media/press-release/press-release-americas-credit-unions-pac-announces-new-expenditure-utah) confirms the McAdams and Young Kim independent-expenditure campaigns. Its separate Sherman discussion is not attributed to C00007880 without matching FEC evidence.

## Confirmed historical understatement: Congressional Leadership Fund, 2022

All amounts below are committee spending supporting/opposing the named candidate. They are not direct contributions.

| Candidate | Direction | Saved report amount | Preserved local PAS2 total | Current exact FEC total |
|---|---|---:|---:|---:|
| PORTER, KATHERINE | Oppose | $6,251,897.00 | $6,785,465.00 | $6,785,471.24 |
| GRAY, ADAM C. | Oppose | $5,944,666.00 | $6,613,182.00 | $6,613,191.59 |
| LEVIN, MIKE | Oppose | $5,569,733.00 | $5,944,329.00 | $5,944,338.55 |
| SALAS, RUDY | Oppose | $4,897,128.00 | $5,926,586.00 | $5,926,597.73 |
| CARAVEO, YADIRA | Oppose | $4,677,372.00 | $5,520,521.00 | $5,520,529.74 |
| HAYES, JAHANA | Oppose | $2,393,712.00 | $2,775,415.00 | $2,775,433.46 |
| CHEN, JAY | Oppose | $2,304,312.00 | $2,988,871.00 | $2,988,875.78 |
| ENGEL, KIRSTEN | Oppose | $2,202,252.00 | $2,499,171.00 | $2,499,173.46 |
| SMITH, CHRISTY | Oppose | $1,982,548.00 | $2,450,522.00 | $2,450,531.83 |
| LOGAN, GEORGE S | Support | $1,452,796.00 | $1,634,986.00 | $1,634,998.20 |
| CISCOMANI, JUAN | Support | $1,050,190.00 | $1,176,686.00 | $1,176,691.39 |
| GREEN, JENNIFER-RUTH | Support | $947,695.00 | $1,047,695.00 | $1,047,695.42 |
| VALADAO, DAVID | Support | $642,743.00 | $752,197.00 | $752,203.27 |
| GARCIA, CASSANDRA | Support | $438,191.00 | $488,191.00 | $488,191.38 |
| DUARTE, JOHN | Support | $390,499.00 | $443,021.00 | $443,025.02 |
| BARRETT, THOMAS MORE | Support | $354,500.00 | $619,500.00 | $619,500.00 |
| ADKINS, AMANDA | Support | $275,000.00 | $425,000.00 | $425,000.00 |
| STEEL, MICHELLE | Support | $200,000.00 | $300,000.00 | $300,000.00 |
| WHEELESS, TANYA CONTRERAS | Support | $75,000.00 | $175,000.00 | $175,000.00 |
| FITZPATRICK, BRIAN | Support | $0.00 | $194,523.00 | $194,527.15 |
| SMITH, SANDY | Oppose | $0.00 | $589,634.00 | $589,634.00 |

Discriminating example: Brian Fitzpatrick shows $0 from CLF in the saved 2022 report, while the FEC reports $194,527.15 across eight regular-report Schedule E items. Original electronic filings [1592379](https://docquery.fec.gov/dcdev/posted/1592379.fec) and [1598276](https://docquery.fec.gov/dcdev/posted/1598276.fec), downloaded in full, contain these eight distinct items and sum to exactly $194,527.15. This is separate from CULAC's 2024 Fitzpatrick spending.

`clf_legacy_check.json` records the independent reproduction of all 21 lower saved totals. Related source-policy fixes were already described in `audits/mentat_contradictions_only_20260920.md`; saved report regeneration was expressly not performed in that earlier work.

## 2026 identity and freshness differences

- C00821439 / Julia Letlow: the saved report associates $116,119 with her House ID H2LA05126. Current regular filings associate the four expenses, $116,120.25 exactly, with her Senate ID S6LA00664. This is a historical-ID difference plus lost cents; it is not evidence of zero expenditure.
- C00687848 / Joe Kerr: current filings use H6CA40317, while a saved small-dollar group uses H4CA40098. Another saved group labels a purported candidate with the paying organization's name. These source-identity differences need source-aware refresh/reconciliation; no silent reassignment was made.
- C00687848 / Robert Garcia: current retrieved rows exist but are memo-coded; a non-memo comparison therefore has no included API amount. It would be wrong to describe this as no spending or automatically replace it with zero.
- Other current-cycle changes are retained at candidate/direction level in `external_exceptions.json`, with original filing links, saved amounts, current exact values, and whole-dollar comparison values. Differences include new reports and corrections; this audit does not indiscriminately relabel them as bugs.

## Saved API snapshots

Six distinct committee/cycle units were selected from the two saved snapshot directories using the app's current selection rule. Current FEC regular-report records match 71 existing 2024 groups and 51 existing 2026 groups, to the cent. Twelve additional 2026 groups appear in current FEC data. These are new to the saved snapshot, not necessarily newly incurred expenses. Details: `snapshot_comparison.json`.

## Evidence and reproducibility

- `report_inventory.json`: report names, SHA-256 hashes, row counts, and source notes.
- `report_activity.json` and `bulk_comparison.json`: complete scoped report inventory and current official bulk comparison.
- `culac_external.json`: all CULAC transactions, exact amounts, payees, dates, and original filing URLs; raw API response receipts accompany it.
- `external_exceptions.json`: every initial bulk exception checked against current regular-report Schedule E; `external_failures.json` is empty.
- `snapshot_comparison.json`: independent-spending comparisons for saved API snapshot units.
- `official-pas2*-receipt.json`: fresh FEC download URLs, modification times, lengths and hashes. Archive files are retained unchanged.
- `clf_legacy_check.json` and original electronic filing files: concrete reproduction and primary evidence for the historical understatement.

Reference definitions: [FEC independent expenditures](https://www.fec.gov/help-candidates-and-committees/making-independent-expenditures/), [FEC PAS2 file description](https://www.fec.gov/campaign-finance-data/contributions-committees-candidates-file-description/).
