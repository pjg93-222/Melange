# Dated cash approximation and dashboard — September 8, 2026

The recommended general approximation is **proportional attribution from the
cash available at each payment**. It answers “what company-funded amount would
this payment represent if the committee mixed available cash proportionally?”
It does not identify donor intent, earmarks, influence, or causal effects.
No empirical accuracy or optimality claim is made for this accounting rule.

## Rule and example

For company c, committee p, and payment time t, maintain a labeled cash balance
for each funding source. A payment receives the fraction belonging to c just
before that payment. An internal PAC transfer moves those same balances into
the receiving committee when its reciprocal receipt arrives. It is not a second
donation. Every other funding source dilutes the company fraction, including
identified funding from outside the selected sector.

Illustration, not a Coinbase result: a PAC with $100 of company funding and
$300 from other sources transfers $200 to a second PAC. The transfer carries
$50 of modeled company funding. If the second PAC then spends $150 supporting
a candidate, $37.50 is modeled company funding and $12.50 remains at that PAC.
If the first PAC spends $100 on operating expenses, $25 is company-funded under
the rule and $25 remains there. Total company funding is conserved:
$37.50 candidate spending + $25 operations + $37.50 retained = $100.

## Implemented controls

- `mentat/tools/pac_cash_model.py` contains the reusable Decimal cash engine
  and the strict Form 3X adapter. The PAC evidence collector invokes it; saved
  snapshots can also be rebuilt offline without making API requests.
- Future receipts never pay for earlier spending. A transfer is unavailable
  at its destination until the matched receipt date. Support and opposition
  remain separate and candidate names/IDs remain as filed.
- Same-day receipts and arriving transfers precede outgoing transfers, refunds,
  and other payments. This is a disclosed assumption because dates do not
  establish within-day ordering. Same-day transfer cycles are refused.
- Operating costs, identified refunds, unspent cash, and outgoing funds beyond
  the selected network remain distinct from candidate spending. Transfer sums
  are not added to terminal spending. No hop-weight or “influence” multiplier
  is applied. The normalized core follows the explicitly supplied dated network.
- Cash conservation is checked with unrounded Decimal balances; every committee
  also needs a closing-cash check within one cent. Output cents are display
  rounding and can have small summation differences across many rows.
- A reusable core can receive donor-labeled opening balances and identified
  refunds. The current automatic snapshot adapter refuses unresolved opening
  ownership and refunds. It does not silently assume that carryover cash is
  unrelated to the company being estimated.
- Noncash gifts and asset sales require donor-lot and offset reconciliation.
  The automatic adapter currently withholds those networks rather than inferring
  ownership from an exchange's name. Negative adjustments, unknown roles, missing
  payment dates, ambiguous transfer pairs, and cash gaps also withhold estimates.
- A withheld estimate has an empty allocation list and specific issue codes,
  never a fabricated zero, a coverage percentage, or a confidence interval.

The FEC describes offsetting receipt/disbursement entries for unliquidated
bitcoin gifts, so their reported value is not available cash. Independent
expenditures may also be disseminated before payment; the cash adapter uses
the payment field rather than silently treating dissemination as cash outflow.
[FEC bitcoin reporting](https://www.fec.gov/help-candidates-and-committees/filing-reports/bitcoin-contributions/),
[FEC independent-expenditure reporting](https://www.fec.gov/help-candidates-and-committees/making-independent-expenditures/reporting-independent-expenditures-form-3x/).

## Current Fairshake result

The unchanged three-PAC snapshot from the preceding audit does **not** pass
the cash-attribution gate. Its sidecar reports 8 outstanding checks for 2024
and 12 for 2026. These are distinct check categories, not counts of erroneous
records, and do not establish that all deficiencies have been enumerated.

For example, Fairshake's 2024 financial summary differs from collected nonmemo
records by $4,796.41 in receipts and $744.99 in disbursements. Its 2026 differences
are $434,442.77 and $14,412,454.28. The latter compares all disbursements, not just
independent expenditures. Other blockers include noncash asset links, a missing
or out-of-period payment date, a negative adjustment, refunds, and unknown
ownership of prior-cycle balances. A small financial difference does not prove
the missing entries have harmless dates or donor identities.

Consequently the UI shows recorded spending alongside **Awaiting reconciliation**
for estimated company funding. Neither the illustrative $2.5 million UI example
nor the example above is presented as a Coinbase result. The prior Crypto and
consolidated workbooks retain their existing audited figures and explicitly
conditional industry allocation. They were not rebuilt as cash-attribution
workbooks during this change.

`cash-estimates.json` is a generated sidecar, bound to the unchanged
`snapshots.json` and `evidence.json` by SHA-256. It records method version,
generation time, and the estimator source-code hash. The server serves the
sidecar only when its evidence hashes match. Earlier source and workbook
evidence is preserved.

## Loading workflow

The regenerated dashboard has Loading, Collection, and PAC evidence tabs.
Loading accepts one sector per manual roster, any number of companies up to
1,000, and up to 100 alternative names per company, subject to the shared
10,000-row roster limit. File uploads retain the
existing multi-sector format. Each alias is a separate line; commas in names
remain literal. Duplicate canonical company entries are rejected and shared
aliases go through the existing readiness checks.

Manual drafts persist in browser local storage without API credentials.
Review saves an isolated roster server-side but performs no FEC queries.
Editing a reviewed draft invalidates readiness in the UI; collection requires
another review. Start collection uses the same runner, encrypted saved keys,
cycle choices and live checkpoints as the existing uploader. A ready saved
roster can be resumed from Collection. Backend readiness remains the authority.

## Validation

- Python suite: 100 tests passed, including 12 new cash-model tests and 3 new
  manual-roster tests. The suite exercises the existing offline runner plan and
  R importer; no live FEC collection is part of those tests.
- Cash tests cover future-donation exclusion, funds in transit, dilution,
  transfer conservation, support/opposition, identified refunds, same-day
  ordering/permutation invariance, duplicate IDs, invalid amounts, closing
  cash failures, unavailable asset/date/gap cases, reciprocal transfer matching,
  and source-hash-bound regeneration. A separate IE summary check prevents an
  offsetting category error from passing the total-cash check.
- JavaScript syntax check passed. Browser verification covered sector/company/
  alias input and a saved two-company, five-search-name roster without starting
  collection. Editing an alias disabled Start and hid the stale review. Reload
  restored the exact sector, companies, and aliases. The PAC evidence tab showed
  its conditional method, 8 unresolved 2024 checks, and 12 unresolved 2026 checks.
  The corrected report links remained accessible in Collection. Browser error logs were
  empty after these checks. The narrow app pane was visually inspected.
