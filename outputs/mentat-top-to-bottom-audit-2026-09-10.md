# Mentat collection and accounting audit — September 10, 2026

**The audit found errors in both directions. Several general collection and accounting controls are repaired, and historical metadata is substantially recovered. The results below are an isolated diagnostic, not certified original giving or an OpenSecrets match.**

The approved destination remains original employee and corporate giving counted once, with PAC outgoing spending shown separately. No production workbook was installed and no original source database was changed. Lobbying is excluded.

## What was wrong and what changed

| Failure | General correction |
|---|---|
| Rebuilds could use the wrong historical source. | Pin each accepted database and financial facts; reconcile every ID and signed dollar change. Recovery runs on private copies. |
| Searches changed punctuation, assumed short aliases covered longer aliases, and reused checkpoints after query changes. | Preserve literal terms in API and browser queries; require every roster alias and bind API checkpoints to the complete query/attribution contract. |
| Pagination could look complete despite inexact or moving counts; narrower fallback searches could be mistaken for full coverage. | Require exact stable counts; preserve failed pages; split broad timeouts into exhaustive date windows without changing terms. Unproven narrower subsets remain incomplete. |
| Matching donor/date/amount was used to delete memo records. | Require an explicit FEC transaction reference, one eligible retained parent, matching filing and financial context, and signed amount coverage. Ambiguity stays reviewable. |
| All “other receipts” were treated as non-giving. | Recognize genuine special-account donations on F3X line 17. Other-receipt labels alone do not prove the transaction is interest, a refund or a settlement. |
| An exchange/processor name could be treated as the source of funds. | Use transaction evidence to distinguish asset sales, interest and processing-fee returns from gifts. FEC organization classification is not proof of corporate treasury ownership. |
| Funding views and QA could imply unique money or use different rules. | Share receipt rules, add an explicit accounting-basis sheet, disclose ownership uncertainty and partisan denominators, and gate unresolved receipt evidence. |

## A material correction to the correction

FEC explicitly directs hybrid PAC non-contribution-account donations and national-party special-account contributions to Form 3X line 17. Our blanket exclusion of that line was wrong. See the [FEC hybrid PAC guidance](https://www.fec.gov/updates/fec-statement-on-carey-v-fec/) and [national-party reporting instructions](https://www.fec.gov/help-candidates-and-committees/filing-political-party-reports/additional-national-party-accounts-receipts/).

Concrete records establish why the rule must follow the event, not its label:

- Chime’s $75,000 VoteVets receipt (2024, FEC ID `4082020242014279666`) explicitly says “NON-CONTRIBUTION ACCOUNT.” It is no longer removed by the line-17 rule. This does not independently establish corporate ownership or uniqueness.
- Kalshi employee receipts to NRSC include headquarters/legal-proceedings accounts and JFC attribution memos. They are retained as contribution representations; the JFC stages still require reconciliation.
- Stripe’s $190,000 receipt (2024, `4092020231802645332`) explicitly returns an erroneous debit. Other large Stripe receipts explicitly refund processing fees. These are not new Stripe political gifts.
- SchoolsFirst’s $17,518.21 receipt (2024, `4050820251189302163`) explicitly records interest. Other SchoolsFirst reductions include the same event type.
- Some Gemini receipts explicitly describe assets liquidated through the exchange with the purchaser unknown. Those are sales, not evidence the exchange donated the proceeds.
- Robinhood receipts of $132,900 and $72,800 in 2026 mention impermissible contributions and a later refund. A refund statement alone cannot establish the actual adjustment; these amounts remain provisional pending linked refund evidence.

A generic label such as “other federal receipts (dividends, interest, etc.)” does not classify an individual transaction. Unsupported cases stay in the unresolved ledger. No company-specific exclusion was introduced.

## Evidence recovery and preservation

Across seven industries, accepted records lacking a form or receipt line fell from **1,266,109 to 10**. This is metadata completeness, not uniqueness or complete political-giving coverage.

The recovery reused 13,061 distinct filing headers, of which 13,050 supplied supported form evidence. Exact-record API checks then recovered 1,902 of 1,912 remaining requested records. Cached public filing headers were read with bounded requests; API work used the shared FEC budget. FEC 8.3 headers establish form/committee identity only and are not promoted to amendment-chain evidence.

All seven original database hashes still match their accepted pins. Comparison of IDs, donor, committee, company, industry, dates and amounts found zero missing IDs and zero added or changed financial facts in the recovery copies.

| Industry | Remaining form/line gaps |
|---|---|
| Community Banks | 0 |
| Credit Arms | 0 |
| Credit Union | 0 |
| Crypto | 4 |
| Fintech | 4 |
| Property & Casualty Insurance | 0 |
| Telecom | 2 |

## Test difference — receipt view only

These sums span the observed 2022, 2024 and partial 2026 cycles. They hold historical company, recipient, party and tier assignments fixed to isolate receipt and memo-rule changes. They retain unresolved receipts and restore unsupported historical memo exclusions. They therefore can include repeated representations and are **not publishable headline giving totals**. A rise is not evidence of recovered unique gifts; a fall is not evidence of better accuracy.

| Industry | Accepted baseline | Diagnostic receipt sum | Change | Unresolved receipt representations |
|---|---:|---:|---:|---:|
| Community Banks | $863,505.98 | $805,715.13 | -$57,790.85 | 12; $46,914.46 |
| Credit Arms | $23,932,445.25 | $23,935,021.69 | $2,576.44 | 82; $506,999.71 |
| Credit Union | $1,422,005.65 | $1,152,485.64 | -$269,520.01 | 20; $3,985.88 |
| Crypto | $249,949,483.17 | $302,924,711.97 | $52,975,228.80 | 87; $187,535,762.65 |
| Fintech | $9,803,891.31 | $9,100,743.52 | -$703,147.79 | 97; $270,318.61 |
| Property & Casualty Insurance | $16,687,365.59 | $16,479,398.69 | -$207,966.90 | 161; $27,826.26 |
| Telecom | $37,698,121.09 | $37,509,686.95 | -$188,434.14 | 145; $1,852,363.03 |

The crypto diagnostic is particularly sensitive to previously excluded disclosure memos, including multiple $23 million representations referring to a previously disclosed 2024 asset contribution. Their retention is an unresolved accounting exposure, not a claim that each is a new gift. These dollar exposures are not statistical error bounds and can themselves overlap.

| Fintech comparison, 2024 only | Accepted baseline | Diagnostic receipt sum | Change |
|---|---:|---:|---:|
| Stripe | $1,746,651.77 | $1,517,709.16 | -$228,942.61 |
| Robinhood | $786,456.88 | $786,456.88 | $0.00 |

Every changed receipt and signed dollar change is in [the record ledger](mentat-top-to-bottom-record-diff-2026-09-10.csv). The [unresolved-receipt ledger](mentat-top-to-bottom-unresolved-receipts-2026-09-10.csv) retains the supporting descriptions. Full [company/cycle](mentat-top-to-bottom-company-cycle-diff-2026-09-10.csv) and [industry/cycle](mentat-top-to-bottom-industry-cycle-diff-2026-09-10.csv) comparisons are separate. Each industry and cycle reconciles in integer cents; company and role sums also reconcile.

## Standard for a defensible OpenSecrets comparison

OpenSecrets is a benchmark to explain, not a number to fit. It can be wrong, and a difference can also come from scope, cutoff, aliases, amendments or the money stage being measured. A supported disagreement must identify the FEC receipts and accounting decisions that cause it. More detail or a larger total alone does not make Mentat better.

Direct requests to the supplied Goldman Sachs and JPMorgan OpenSecrets pages returned HTTP 403; browser and web attempts also did not produce verifiable totals. Consequently no current OpenSecrets number or matched comparison is asserted here. The access record is saved at `.tmp/top-to-bottom-audit-20260910/opensecrets-access.json`. The seven-industry diagnostic is not a substitute for the still-uncompleted Goldman Sachs/JPMorgan workbook comparison.

Before certifying original giving or matching an external benchmark, the following evidence must be completed:

1. **Collection:** rerun missing/unproven query scopes under the new contracts. None of the seven legacy sources can yet prove full collection coverage under the new standard. Confirm organizational aliases and historical subsidiary/PAC boundaries.
2. **Amendments:** resolve explicit filing families and transaction replacements, including omitted/deleted transactions. File dates, matching amounts or “amended” flags alone are insufficient.
3. **Routes:** connect donor-to-conduit/JFC-to-recipient records and select one original-giving representation. Reconcile asset gifts with later sale/disclosure entries; do not add the same money at each stage.
4. **Ownership and refunds:** validate employee, corporate treasury and company-PAC attribution. Link actual refunds to gifts and report gross giving, refunds and net giving without treating a promised refund as zero.
5. **Comparison:** obtain verifiable benchmark data with the same cycle, cutoff, company boundary, recipient universe, refund basis and PAC treatment. Explain the residual gap by records, not balancing adjustments.

The previously tested original-giving experiment remains a small, separate evidence trial; it is not silently applied to these broader diagnostic sums. [Earlier trial and diff](mentat-original-giving-test-diff-2026-09-10.md).

## Validation

The final receipt-rule tests cover legitimate line-17 donations, generic-label ambiguity, interest, processing returns, liquidation wording, conflicting evidence and promised refunds. Memo tests cover explicit links, unlinked lookalikes, ineligible/ambiguous parents, signed amounts and incompatible donors/dates/filings. Source-preservation checks and per-cycle cent reconciliation passed.

Python suites passed for PAC evidence (7), source guards (19), coverage (33), metadata hydration (5), filing headers (7), original-giving trials (7), form recovery (1), and shard merging (14). R collection-contract, API, fanout, rules, receipt-role, names and report suites passed during this audit. The report suite verified all 6,035 workbook formulas and cross-sheet references. The workbook-builder JavaScript syntax check passed. These tests verify implemented controls; they do not certify the unresolved historical relationships.

The shared rules and remaining implementation limits are recorded in [METHODOLOGY.md](../mentat/METHODOLOGY.md). Source hashes, rule/code fingerprints and audit totals are in [the evidence summary](mentat-top-to-bottom-audit-evidence-2026-09-10.json).
