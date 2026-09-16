# S2 export header receipt - lane-08 warehouse

Phase 3b, S2. `tools/export_raw_contribution_warehouse.py` run against the
MIGRATED scratch copy of lane-08, then against a fresh UN-MIGRATED copy of the
same snapshot. No live database was opened.

## Commands

```
cd C:/Users/pgoff/Mentat/mentat

# migrated copy (init_schema() already applied - see S2_migration_lane08.md)
python tools/export_raw_contribution_warehouse.py ^
  C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-contributor-street-columns-0a1726\acfc8792-f597-44a3-ac0f-f7d883e56447\scratchpad\s2_receipts\lane-08\mentat.db "Credit Unions" "2021-2022,2023-2024,2025-2026" ^
  --output-root C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-contributor-street-columns-0a1726\acfc8792-f597-44a3-ac0f-f7d883e56447\scratchpad\s2_receipts\lane-08\warehouse ^
  --receipt C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-contributor-street-columns-0a1726\acfc8792-f597-44a3-ac0f-f7d883e56447\scratchpad\s2_receipts\lane-08\warehouse_receipt.json

# fresh UN-MIGRATED copy of the same source snapshot
python tools/export_raw_contribution_warehouse.py ^
  C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-contributor-street-columns-0a1726\acfc8792-f597-44a3-ac0f-f7d883e56447\scratchpad\s2_receipts\unmigrated\mentat.db "Credit Unions" "2021-2022,2023-2024,2025-2026" ^
  --output-root C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-contributor-street-columns-0a1726\acfc8792-f597-44a3-ac0f-f7d883e56447\scratchpad\s2_receipts\unmigrated\warehouse ^
  --receipt C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-contributor-street-columns-0a1726\acfc8792-f597-44a3-ac0f-f7d883e56447\scratchpad\s2_receipts\unmigrated\warehouse_receipt.json

# header comparison against the contract
python C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-contributor-street-columns-0a1726\acfc8792-f597-44a3-ac0f-f7d883e56447\scratchpad\s2_receipts\step3_export_check.py
```

## Source

| field | value |
| --- | --- |
| source path | `C:\Users\pgoff\AppData\Local\Mentat\console\f897a21e05a24d1e9246b0bf972145e0\runs\20260915T152258-18548\industries\credit-unions\fanout\lanes\lane-08\mentat.db` |
| source bytes | 44,154,880 |
| source SHA256 | `88024fd3af04903a27a550fff5e15dc824744c97a18ee3fd62a3c909baeb5bb2` |
| migrated copy | `C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-contributor-street-columns-0a1726\acfc8792-f597-44a3-ac0f-f7d883e56447\scratchpad\s2_receipts\lane-08\mentat.db` |
| un-migrated copy | `C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-contributor-street-columns-0a1726\acfc8792-f597-44a3-ac0f-f7d883e56447\scratchpad\s2_receipts\unmigrated\mentat.db` (SHA256 `88024fd3af04903a27a550fff5e15dc824744c97a18ee3fd62a3c909baeb5bb2`, byte-identical to source) |
| contract | `C:\Users\pgoff\Mentat\audits\mentat_failings_20260915\contracts\raw_contribution_columns.json` |

## Argument format (read from the live tool)

`parse_cycles()` is at `tools/export_raw_contribution_warehouse.py:134-146`
(the brief cited `:96-102`; the live file has moved - the concurrent S2 code
edits shifted it). It splits on `,` or `|`, and accepts only the labels in
`CYCLE_MAP`: `2021-2022`/`2022`, `2023-2024`/`2024`, `2025-2026`/`2026`.
`expected_companies()` is at `:310-334` (brief cited `:266-290`): it reads
`SELECT DISTINCT company FROM companies WHERE industry=?`, and raises if the
roster table is absent or the industry has no roster.

Cycles present in the copy:

```
SELECT DISTINCT cycle FROM corporate_giving                  -> 2022, 2024, 2026
SELECT DISTINCT two_year_transaction_period FROM contributions -> 2022, 2024, 2026
```

so the run used `"2021-2022,2023-2024,2025-2026"`.
`companies` roster for `Credit Unions` holds 10 companies; the lane's own rows
are all `Mountain America Credit Union` (corporate_giving 3,132 /
contributions 1,674). The exporter did **not** refuse: it wrote empty
partitions for the other nine companies. No fix of any kind was needed, on the
copy or anywhere else.

## Exporter result

| run | exit code | receipt `status` | partitions | rows |
| --- | --- | --- | --- | --- |
| migrated | 0 | `succeeded` | 30 | {"contributions": 1674, "corporate_giving": 3132} |
| un-migrated | 0 | `succeeded` | 30 | {"contributions": 1674, "corporate_giving": 3132} |

## MIGRATED copy - partition checked

`C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-contributor-street-columns-0a1726\acfc8792-f597-44a3-ac0f-f7d883e56447\scratchpad\s2_receipts\lane-08\warehouse\Credit Unions\2021-2022\Mountain America Credit Union\fd3e1fed8d103586338d\manifest.json`
(row counts {"contributions": 579, "corporate_giving": 825})

### corporate_giving.csv.gz vs `surfaces.raw_warehouse_corporate_giving.header`

```
CSV header (50 columns):
["sub_id", "contributor_id", "contributor_name", "contributor_employer", "contributor_occupation", "contributor_street_1", "contributor_street_2", "contributor_city", "contributor_state", "contributor_zip", "entity_type", "committee_id", "is_entity_contributor", "committee_name", "recipient_committee_type", "recipient_committee_designation", "contribution_receipt_date", "contribution_receipt_amount", "industry", "company", "matched_variant", "cycle", "scraped_at", "transaction_id", "original_sub_id", "amendment_indicator", "report_year", "report_type", "file_num", "pdf_url", "load_date", "filing_form", "receipt_type", "receipt_type_full", "line_number", "line_number_label", "memo_code", "memoed_subtotal", "memo_text", "back_reference_transaction_id", "back_reference_schedule_name", "is_conduit_leg", "is_memo_leg", "is_passthrough_leg", "superseded_by_amendment", "duplicate_filing_version", "duplicate_memo", "company_match_status", "company_match_reason", "excluded_reason"]

contract header used (50 columns):
["sub_id", "contributor_id", "contributor_name", "contributor_employer", "contributor_occupation", "contributor_street_1", "contributor_street_2", "contributor_city", "contributor_state", "contributor_zip", "entity_type", "committee_id", "is_entity_contributor", "committee_name", "recipient_committee_type", "recipient_committee_designation", "contribution_receipt_date", "contribution_receipt_amount", "industry", "company", "matched_variant", "cycle", "scraped_at", "transaction_id", "original_sub_id", "amendment_indicator", "report_year", "report_type", "file_num", "pdf_url", "load_date", "filing_form", "receipt_type", "receipt_type_full", "line_number", "line_number_label", "memo_code", "memoed_subtotal", "memo_text", "back_reference_transaction_id", "back_reference_schedule_name", "is_conduit_leg", "is_memo_leg", "is_passthrough_leg", "superseded_by_amendment", "duplicate_filing_version", "duplicate_memo", "company_match_status", "company_match_reason", "excluded_reason"]

comparison: EQUAL
manifest columns == csv header: True
manifest missing_contract_columns: []
```

### contributions.csv.gz vs `surfaces.raw_warehouse_contributions.header`

```
CSV header (63 columns):
["sub_id", "transaction_id", "original_sub_id", "contributor_id", "contributor_name", "contributor_first_name", "contributor_last_name", "contributor_suffix", "contributor_employer", "contributor_occupation", "contributor_street_1", "contributor_street_2", "contributor_city", "contributor_state", "contributor_zip", "contributor_aggregate_ytd", "contribution_receipt_amount", "contribution_receipt_date", "committee_id", "committee_name", "recipient_committee_type", "recipient_committee_designation", "entity_type", "election_type", "fec_election_type_desc", "receipt_type_full", "memo_code", "memoed_subtotal", "filing_form", "receipt_type", "line_number_label", "back_reference_transaction_id", "back_reference_schedule_name", "memo_text", "conduit_committee_id", "conduit_committee_name", "amendment_indicator", "report_year", "report_type", "file_num", "two_year_transaction_period", "line_number", "pdf_url", "load_date", "industry", "company", "matched_variant", "phase", "match_confidence", "scraped_at", "is_conduit_leg", "is_memo_leg", "is_passthrough_leg", "memo_review", "possible_amendment", "superseded_by_amendment", "duplicate_filing_version", "duplicate_memo", "is_refund", "is_entity_contributor", "company_match_status", "company_match_reason", "excluded_reason"]

contract header used (63 columns):
["sub_id", "transaction_id", "original_sub_id", "contributor_id", "contributor_name", "contributor_first_name", "contributor_last_name", "contributor_suffix", "contributor_employer", "contributor_occupation", "contributor_street_1", "contributor_street_2", "contributor_city", "contributor_state", "contributor_zip", "contributor_aggregate_ytd", "contribution_receipt_amount", "contribution_receipt_date", "committee_id", "committee_name", "recipient_committee_type", "recipient_committee_designation", "entity_type", "election_type", "fec_election_type_desc", "receipt_type_full", "memo_code", "memoed_subtotal", "filing_form", "receipt_type", "line_number_label", "back_reference_transaction_id", "back_reference_schedule_name", "memo_text", "conduit_committee_id", "conduit_committee_name", "amendment_indicator", "report_year", "report_type", "file_num", "two_year_transaction_period", "line_number", "pdf_url", "load_date", "industry", "company", "matched_variant", "phase", "match_confidence", "scraped_at", "is_conduit_leg", "is_memo_leg", "is_passthrough_leg", "memo_review", "possible_amendment", "superseded_by_amendment", "duplicate_filing_version", "duplicate_memo", "is_refund", "is_entity_contributor", "company_match_status", "company_match_reason", "excluded_reason"]

comparison: EQUAL
manifest columns == csv header: True
manifest missing_contract_columns: []
```

## UN-MIGRATED copy - same partition, no `init_schema()`

`C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-contributor-street-columns-0a1726\acfc8792-f597-44a3-ac0f-f7d883e56447\scratchpad\s2_receipts\unmigrated\warehouse\Credit Unions\2021-2022\Mountain America Credit Union\db0d1278fdd765499dde\manifest.json`
(row counts {"contributions": 579, "corporate_giving": 825})

The un-migrated database has no street columns
(`corporate_giving` 48 columns, `contributions` 61, `bulk_candidates` 11), so
the expected header here is the contract header MINUS the two street names.

### corporate_giving.csv.gz

```
CSV header (48 columns):
["sub_id", "contributor_id", "contributor_name", "contributor_employer", "contributor_occupation", "contributor_city", "contributor_state", "contributor_zip", "entity_type", "committee_id", "is_entity_contributor", "committee_name", "recipient_committee_type", "recipient_committee_designation", "contribution_receipt_date", "contribution_receipt_amount", "industry", "company", "matched_variant", "cycle", "scraped_at", "transaction_id", "original_sub_id", "amendment_indicator", "report_year", "report_type", "file_num", "pdf_url", "load_date", "filing_form", "receipt_type", "receipt_type_full", "line_number", "line_number_label", "memo_code", "memoed_subtotal", "memo_text", "back_reference_transaction_id", "back_reference_schedule_name", "is_conduit_leg", "is_memo_leg", "is_passthrough_leg", "superseded_by_amendment", "duplicate_filing_version", "duplicate_memo", "company_match_status", "company_match_reason", "excluded_reason"]

contract header used (48 columns):
["sub_id", "contributor_id", "contributor_name", "contributor_employer", "contributor_occupation", "contributor_city", "contributor_state", "contributor_zip", "entity_type", "committee_id", "is_entity_contributor", "committee_name", "recipient_committee_type", "recipient_committee_designation", "contribution_receipt_date", "contribution_receipt_amount", "industry", "company", "matched_variant", "cycle", "scraped_at", "transaction_id", "original_sub_id", "amendment_indicator", "report_year", "report_type", "file_num", "pdf_url", "load_date", "filing_form", "receipt_type", "receipt_type_full", "line_number", "line_number_label", "memo_code", "memoed_subtotal", "memo_text", "back_reference_transaction_id", "back_reference_schedule_name", "is_conduit_leg", "is_memo_leg", "is_passthrough_leg", "superseded_by_amendment", "duplicate_filing_version", "duplicate_memo", "company_match_status", "company_match_reason", "excluded_reason"]

comparison: EQUAL
manifest columns == csv header: True
manifest missing_contract_columns: ['contributor_street_1', 'contributor_street_2']
```

### contributions.csv.gz

```
CSV header (61 columns):
["sub_id", "transaction_id", "original_sub_id", "contributor_id", "contributor_name", "contributor_first_name", "contributor_last_name", "contributor_suffix", "contributor_employer", "contributor_occupation", "contributor_city", "contributor_state", "contributor_zip", "contributor_aggregate_ytd", "contribution_receipt_amount", "contribution_receipt_date", "committee_id", "committee_name", "recipient_committee_type", "recipient_committee_designation", "entity_type", "election_type", "fec_election_type_desc", "receipt_type_full", "memo_code", "memoed_subtotal", "filing_form", "receipt_type", "line_number_label", "back_reference_transaction_id", "back_reference_schedule_name", "memo_text", "conduit_committee_id", "conduit_committee_name", "amendment_indicator", "report_year", "report_type", "file_num", "two_year_transaction_period", "line_number", "pdf_url", "load_date", "industry", "company", "matched_variant", "phase", "match_confidence", "scraped_at", "is_conduit_leg", "is_memo_leg", "is_passthrough_leg", "memo_review", "possible_amendment", "superseded_by_amendment", "duplicate_filing_version", "duplicate_memo", "is_refund", "is_entity_contributor", "company_match_status", "company_match_reason", "excluded_reason"]

contract header used (61 columns):
["sub_id", "transaction_id", "original_sub_id", "contributor_id", "contributor_name", "contributor_first_name", "contributor_last_name", "contributor_suffix", "contributor_employer", "contributor_occupation", "contributor_city", "contributor_state", "contributor_zip", "contributor_aggregate_ytd", "contribution_receipt_amount", "contribution_receipt_date", "committee_id", "committee_name", "recipient_committee_type", "recipient_committee_designation", "entity_type", "election_type", "fec_election_type_desc", "receipt_type_full", "memo_code", "memoed_subtotal", "filing_form", "receipt_type", "line_number_label", "back_reference_transaction_id", "back_reference_schedule_name", "memo_text", "conduit_committee_id", "conduit_committee_name", "amendment_indicator", "report_year", "report_type", "file_num", "two_year_transaction_period", "line_number", "pdf_url", "load_date", "industry", "company", "matched_variant", "phase", "match_confidence", "scraped_at", "is_conduit_leg", "is_memo_leg", "is_passthrough_leg", "memo_review", "possible_amendment", "superseded_by_amendment", "duplicate_filing_version", "duplicate_memo", "is_refund", "is_entity_contributor", "company_match_status", "company_match_reason", "excluded_reason"]

comparison: EQUAL
manifest columns == csv header: True
manifest missing_contract_columns: ['contributor_street_1', 'contributor_street_2']
```

## Finding

On the migrated copy both CSV headers are **EQUAL** to the contract headers and
both manifests report `missing_contract_columns: []`. On the un-migrated copy
both headers are **EQUAL** to the contract header minus the street pair, and
both manifests report
`missing_contract_columns: ["contributor_street_1", "contributor_street_2"]` -
the exporter names the gap instead of silently emitting a short header.
