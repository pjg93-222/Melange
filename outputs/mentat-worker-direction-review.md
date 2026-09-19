# Mentat worker and money-direction review

Read-only review of the current working tree, with isolated synthetic reproductions. Production code, collection databases and published workbooks were not changed. The repository already contained substantial uncommitted work before this review.

**Result: four reproducible accounting/estimation errors, plus the previously identified scheduling requirement gap.** The examples establish executable failure cases. They do not establish the number of affected historical records or the dollar impact on existing workbooks.

## Findings

### 1. [P1] Preserve unmatched candidate transfers in allocation coverage

Code: [fec_transfer_graph.py:131](C:/Users/pgoff/Mentat/mentat/tools/fec_transfer_graph.py:131); caller: [enrich_downstream.py:49](C:/Users/pgoff/Mentat/mentat/tools/enrich_downstream.py:49).

`allocate()` drops every outgoing edge whose destination is an authorized candidate committee in `stop_nodes`. This is meant to avoid counting a transfer again when its candidate activity appears in another source, but it never establishes that the counterpart activity is present. Missing or differently scoped candidate activity therefore removes a known outflow from the allocation denominator.

Reproduction: $100 of root funding; an observed $90 transfer to an authorized candidate committee; separate $10 opposition activity against another candidate; no activity counterpart for the $90 transfer. The allocator assigns the entire $100 to the opposition activity and reports $0 unresolved. The same fixture passed through the report enrichment function produces `estimated_opposition=100`, with every listed quality check passing.

The accounting model may be conditional, but omitting a supplied observed outflow and redistributing its share to a different activity is a substantive allocation error. Preserve the candidate route or its unresolved share. Remove a representation only when a compatible retained counterpart has been established. Process steps affected: Connect, Count, Verify/report.

### 2. [P1] Resolve filing versions before filtering for cash transfers

Code: [fec_transfer_graph.py:73](C:/Users/pgoff/Mentat/mentat/tools/fec_transfer_graph.py:73).

The transfer index filters to cash codes `24G` and `24K` before it considers filing versions. If a later amendment corrects an old cash entry to an in-kind transaction or another role outside those codes, the corrected row is discarded before it can supersede the old cash entry.

Reproduction: an original $100 `24K` row and a later amended `24Z` row with the same committee, report type, date and transaction ID. The index keeps a $100 cash edge from the superseded row and reports no superseded row. The FEC distinguishes `24K` contributions to nonaffiliated committees from `24Z` in-kind contributions to registered filers in its [transaction-code reference](https://www.fec.gov/campaign-finance-data/transaction-type-code-descriptions/).

Retain relevant version candidates before classifying the final observed representation. Establish the filing family from evidence; unresolved relationships must remain visible. Process steps affected: Identify, Connect, Count.

### 3. [P1] Withhold cash attribution when the receipt role remains unresolved

Code: [pac_cash_model.py:206](C:/Users/pgoff/Mentat/mentat/tools/pac_cash_model.py:206); presentation: [app.js:334](C:/Users/pgoff/Mentat/mentat/app/app.js:334).

The cash adapter guards the exact role `unverified_receipt_role` but allows other unresolved roles such as `unverified_other_receipt`. These rows enter the cash ledger as Other/unresolved funding, even when they match the selected company. The adapter can return `status=estimated` with no issues. The interface then defaults the missing company allocation to zero and announces that the cash ledger reconciled.

Reproduction: the existing balanced snapshot fixture, with its $100 company receipt changed to Form 3X line 17 and the generic description `OTHER FEDERAL RECEIPTS`. The shared classifier returns `unverified_other_receipt`. The adapter still returns `estimated`, reports no issues, assigns the $50 expenditure entirely to Other/unresolved funding, and the current UI calculation displays $0 for the company's share.

Balancing cash does not resolve whether this company-associated receipt was a gift or another economic event. Preserve the unknown and withhold the company attribution until the role is resolved. Review every unresolved-role variant rather than one string. Process steps affected: Identify, Count, Verify/report.

### 4. [P2] Do not use the transaction-date year as filing-family identity

Code: [fec_transfer_graph.py:83](C:/Users/pgoff/Mentat/mentat/tools/fec_transfer_graph.py:83).

The transfer version key is committee + report type + transaction-date year + transaction ID. Correcting a transaction date across New Year changes the key, so the old and amended representations both survive.

Reproduction: one $100 transfer originally dated December 31, 2023, then amended to January 1, 2024, with the same committee, report type and transaction ID. Both dates are in election cycle 2024. The index emits a $200 edge with two retained rows and no superseded row.

The FEC defines a transaction ID in the context of a committee's specific report and its amendments; transaction-date year is not filing-family evidence. See the [OTH file definition](https://www.fec.gov/campaign-finance-data/any-transaction-one-committee-another-file-description/). Use verified report-family identity, preserving ambiguity where the bulk fields do not establish it. Merely removing the year from this key would risk merging legitimate transactions from distinct reports. Process steps affected: Connect, Count.

## Worker scheduling

The requested sequence is: complete assigned collection, verify it, verify the furthest-along active shard, then assist that shard's remaining collection. The current scheduler shares requests and unstarted company work, but has no checkpoint-scoped verification work queue or priority for the most advanced shard. The completion branch calls `submit_company()` and then handles retry work ([api_company_cycle_fanout.py:1446](C:/Users/pgoff/Mentat/mentat/tools/api_company_cycle_fanout.py:1446)). This is the already discussed missing requirement, not a newly discovered implementation of that sequence.

Existing worker tests cover exclusive database/key leases, persisted company handoffs, crash recovery, resumes, shared request capacity and merging. No additional worker corruption failure was reproduced in this review. Passing these tests does not supply the missing verification scheduling.

## Validation and reproduction

- 153 existing tests passed across worker sharing, fanout, request pooling, query/industry coverage, merging, cross-reference engine/runner/store, source guards, PAC evidence, PAC cash estimates and downstream enrichment.
- Five existing transfer-graph tests also passed: **158 existing tests passed in total**.
- Four additional isolated cases reproduced the findings above. The allocation case was checked through both the allocator and report enrichment, and the unresolved cash case was traced to the UI's zero fallback.
- No FEC collection requests were issued. Public FEC documentation was consulted to verify transaction-code and identifier meanings. No production code or data was changed.

[Reproduction script](C:/Users/pgoff/Mentat/outputs/mentat-worker-direction-repro.py) and [saved results with source-file hashes](C:/Users/pgoff/Mentat/outputs/mentat-worker-direction-evidence.json).

Run the script with the bundled Python runtime. It uses existing synthetic fixtures and disposable temporary directories; its default behavior prints results. An optional output-file argument saves the JSON result. Fixes should add regression coverage for these examples and their counterexamples, then quantify affected source records before rebuilding user reports.
