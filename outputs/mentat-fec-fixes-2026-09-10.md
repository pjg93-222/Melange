# Mentat FEC accounting fixes — September 10, 2026

The collection/reporting rules have been corrected and regression-tested. Historical FEC records and existing production workbooks are preserved. Revised production totals have not been published: legacy sources still need receipt-evidence recovery before those totals can be certified.

## What changed

| Defect | Corrected behavior |
|---|---|
| An older database could replace a completed source while passing hash checks. | Report builds require an explicit source and compare its FEC IDs and financial facts with the accepted baseline. Missing or altered facts block publication. Cycle-specific builds inherit the full-report baseline. |
| Missing metadata could become either counted money or an exclusion depending on a company-name keyword. | Names no longer decide receipt roles. Form/line evidence determines contributions, transfers and other receipts. Unresolved records remain available and generate a review file before publication stops. |
| “Previously disclosed” text could remove money without its original counted record. | The wording alone cannot exclude a contribution. Memo exclusions identify a retained counterpart and the evidence rule. Structured FEC references take precedence over text; filing context, donor, date, cash direction and amount coverage are checked. |
| QA used a different eligibility calculation. | Receipt eligibility and QA countability share the same predicate, including refreshed memo decisions and non-contribution exclusions. |
| Corporate, personal and PAC funding could be confused with the recipient's type. | Funding Cohorts carry source-of-money and direction fields. Company PAC column labels explicitly say receipts; outgoing PAC spending remains a separate stage. Existing employee tiers and partisan denominators are retained. |
| Changed totals lacked a consistent record-level explanation. | Every changed inclusion/classification decision carries before/after values, source evidence and its dollar effect. Source and dollar ledgers are linked from a report companion. Raw company-match exclusions remain auditable even when omitted from Excel. |

Original/amended rows retain the established treatment. Conduit and intermediary involvement alone does not cause an exclusion. Lobbying is outside this work.

Historical comparison baselines are now pinned for Fintech, Credit Union, Community Banks, Credit Arms, Property & Casualty Insurance, Telecom and Crypto, using the sources behind their completed reports. These baselines preserve old decisions for comparison; they do not certify those decisions as correct.

## Real-data checks

The new guard rejected the actual September 8 Fintech and Credit Union repair databases when compared with their completed-report sources:

| Industry | Previously counted receipts missing from the repair source | Dollars on those missing receipts |
|---|---:|---:|
| Fintech | 13 | $508,545.00 |
| Credit Union | 458 | $415,768.18 |

These are **missing-receipt amounts**, before any offsetting newly added receipts. The Credit Union replacement added 405,070 raw source IDs while dropping 5,189 others; a net record-count check would have missed the loss of counted money.

Exact FEC API recovery also validated two Stripe records in a private database copy:

| FEC source ID | Amount | Recovered evidence | Classification |
|---|---:|---|---|
| 4092020231802645332 | $190,000 | F3X, line 17; memo identifies return of an erroneous Stripe debit | Other receipt; excluded from contribution totals |
| 4060320251204404546 | $50,000 | F4, line 14A | Convention contribution; retained |

The [FEC's form-specific receipt documentation](https://www.fec.gov/campaign-finance-data/about-campaign-finance-data/about-receipts-data/) explains the line distinctions. The corresponding filed pages are the [Stripe debit return](https://docquery.fec.gov/pdf/500/202309209597131500/202309209597131500_000049.pdf) and [convention receipt](https://docquery.fec.gov/pdf/435/202506039761730435/202506039761730435_000141.pdf). The API metadata, recovery scope and original-source hash are recorded in the local verification receipt.

## Validation

- 24 Python regression tests passed: source loss, amount changes, omitted evidence, unexplained reductions, cycle-scope bypass, historical baseline formats, concurrent baseline changes, active WAL writes, hydration identity conflicts, source immutability, PAC/treasury cohort separation and workbook payload preservation.
- R receipt-role and accounting-rule tests passed, including cross-filing references, structured links, uncounted parents, opposite signs and amounts exceeding the parent.
- The full R report test passed, including 6,035 Stats formulas, cached totals, source counts, amendments, signed redesignations and Excel layout checks.
- PowerShell workbook-builder guards, PAC-label/formula compatibility, JavaScript syntax and whitespace checks passed. The Excel finalizer maps the displayed “Company PAC receipts” label back to the canonical source category and uses the renamed columns for partisan formulas and integrity checks.
- A read-only export of the real 2024 Fintech recovery copy stopped before installing a payload and wrote a review queue for 12,721 otherwise-countable receipts with unresolved evidence.
- The full report test exposed a writexl 2.x inline/shared-string compatibility change. The writer now explicitly preserves the inline-string format required by the existing header restoration code.

## Remaining data limitation

Cache-first recovery found no usable saved API metadata in the original Fintech/Credit Union sources. After the two targeted Stripe recoveries, 24,950 accepted Fintech source IDs and 27,595 accepted Credit Union source IDs still lack a filing form or receipt line in the recovery copies. These are metadata gaps across the stored data, not a dollar-loss estimate and not proof that each receipt is questionable. They must not be silently excluded.

`tools/hydrate_receipt_metadata.py` performs resumable recovery into a private copy, validates financial identity before updates, and records each changed metadata value. Its `complete` status applies to the requested company/cycle/source-ID scope only. The original databases and financial amounts remain intact.

Operational instructions are in [the Mentat README](C:/Users/pgoff/Mentat/mentat/README.md). Accepted comparison state is in `mentat/state/accepted-report-sources/`; back it up with the databases. The comparison baseline records historical facts and decisions, not an endorsement of every old classification.

Local evidence:

- [Fintech source-loss receipt](C:/Users/pgoff/Mentat/mentat/.cache/accepted-report-sources/runs/regression-proof-fintech-20260910.json)
- [Credit Union source-loss receipt](C:/Users/pgoff/Mentat/mentat/.cache/accepted-report-sources/runs/regression-proof-credit_union-20260910.json)
- [Stripe API recovery verification](C:/Users/pgoff/Mentat/mentat/.cache/receipt-metadata-repair-20260910/fintech/stripe-verification.json)
- [Fintech full recovery status](C:/Users/pgoff/Mentat/mentat/.cache/receipt-metadata-repair-20260910/fintech/mentat.db.hydration.json)
- [Credit Union full recovery status](C:/Users/pgoff/Mentat/mentat/.cache/receipt-metadata-repair-20260910/credit_union/mentat.db.hydration.json)
