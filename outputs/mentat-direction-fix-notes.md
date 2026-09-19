# Mentat money-direction fixes

The four errors from `mentat-worker-direction-review.md` are corrected in code. Source observations and historical workbooks were preserved.

| Error | Corrected behavior |
|---|---|
| Candidate-committee transfers disappeared without a retained candidate-activity counterpart. | The allocator retains the unmatched share as unresolved. It removes a duplicate only when the retained filing/transaction identity, destination, date, amount and cash type match. Possible overlapping records without that proof withhold allocation at the affected committee. |
| Cash filtering discarded later noncash amendments and revived an older cash record. | OTH index v3 first identifies cash-related transaction keys, then preserves all their observed representations, including noncash and memo changes. Verified report families resolve by amendment number before the cash filter runs. |
| Unverified receipt categories were admitted as other funding, creating a misleading company zero. | Every `unverified_` receipt role withholds the cash estimate. Valid transfer receipts, identified interest and verified special-account contributions still pass their existing checks. The app rejects cached estimates from the old model code. |
| Correcting a transaction date across New Year caused double counting. | Transaction dates no longer define report families. OTH groups require preserved filing-header evidence to resolve competing filings; otherwise they remain unresolved. The PAS2 candidate-spending parser also preserves competing observations and withholds them pending relationship evidence. |

Unresolved source activity propagates into allocation coverage and quality warnings. The separate $90 unmatched transfer / $10 opposition regression now reports $90 unresolved and $10 conditional opposition, conserving the $100 input. Signed corrections and real retained-counterpart matching have regression coverage.

## Verification

- The broader Python run passed 196 tests across worker sharing, collection, merging, cross-reference, evidence, cash modeling, transfers, enrichment and the application server.
- Two additional tests were added afterward: R-to-Python retained-record matching and signed transfer corrections. The final focused run passed 35 tests, including these two, for 198 distinct Python tests passing across the runs.
- `tests/test_transfer_evidence.R` passed its retained-identity, amendment-review, stale-index and coverage-serialization checks, including through the Python integration test.
- `tests/test_fec_beneficiary_helpers.R` passed 5,000 randomized helper cases and parity checks on 15,000 rows and 20,000 benchmark groups.
- The four original offline reproductions were rerun; their updated results are in `mentat-worker-direction-fixed-evidence.json`. The original review evidence remains unchanged.
- `git diff --check` passed.

## Operational limits

No live FEC collection, production source reindex, historical workbook rebuild or running-service restart was performed. New code rejects legacy transfer indexes until they are rebuilt from preserved source files. The existing `tools/fec_transfer_graph.py --directory ... --cycles ...` command rebuilds them offline; its optional `--filing-header-directory` accepts previously preserved header evidence and does not fetch it. PAS2 competing versions currently remain held for review; its parser does not yet consume those OTH header arguments.

These fixes improve conditional estimates and their evidence boundaries. They do not establish the donor's intent, complete political-giving coverage or historical workbook accuracy.
