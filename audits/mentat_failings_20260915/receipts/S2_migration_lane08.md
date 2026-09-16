# S2 migration receipt - lane-08

Phase 3b, S2 (address fields). `init_schema()` run against a SCRATCH COPY of a
live lane snapshot. The live database was never opened: it was byte-copied
(with its `-wal` / `-shm` siblings) and every read and write below is against
the copy.

## Commands

```
# 1. fresh copy + BEFORE census (Python, PYTHONDONTWRITEBYTECODE=1)
cd C:/Users/pgoff/Mentat/mentat
python C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-contributor-street-columns-0a1726\acfc8792-f597-44a3-ac0f-f7d883e56447\scratchpad\s2_receipts\step1_copy_before.py

# 2. migration (R)
cd C:/Users/pgoff/Mentat/mentat
"C:/Program Files/R/R-4.6.0/bin/Rscript.exe" C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-contributor-street-columns-0a1726\acfc8792-f597-44a3-ac0f-f7d883e56447\scratchpad\s2_receipts\migrate_copy.R C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-contributor-street-columns-0a1726\acfc8792-f597-44a3-ac0f-f7d883e56447\scratchpad\s2_receipts\lane-08\mentat.db

# 3. AFTER census + byte match + schema diff (Python)
cd C:/Users/pgoff/Mentat/mentat
python C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-contributor-street-columns-0a1726\acfc8792-f597-44a3-ac0f-f7d883e56447\scratchpad\s2_receipts\step2_after.py

# 4. independent byte compare
fc /b C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-contributor-street-columns-0a1726\acfc8792-f597-44a3-ac0f-f7d883e56447\scratchpad\s2_receipts\lane-08\lane-08_counts_before.txt ^
      C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-contributor-street-columns-0a1726\acfc8792-f597-44a3-ac0f-f7d883e56447\scratchpad\s2_receipts\lane-08\lane-08_counts_after.txt
```

## Source

| field | value |
| --- | --- |
| source path | `C:\Users\pgoff\AppData\Local\Mentat\console\f897a21e05a24d1e9246b0bf972145e0\runs\20260915T152258-18548\industries\credit-unions\fanout\lanes\lane-08\mentat.db` |
| source bytes | 44,154,880 |
| source SHA256 | `88024fd3af04903a27a550fff5e15dc824744c97a18ee3fd62a3c909baeb5bb2` |
| siblings copied | `mentat.db-wal`, `mentat.db-shm` |
| copy path | `C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-contributor-street-columns-0a1726\acfc8792-f597-44a3-ac0f-f7d883e56447\scratchpad\s2_receipts\lane-08\mentat.db` |
| copy bytes | 44,154,880 |
| copy SHA256 | `88024fd3af04903a27a550fff5e15dc824744c97a18ee3fd62a3c909baeb5bb2` |
| source SHA == copy SHA | **YES** |

## (2) BEFORE

```
PRAGMA integrity_check -> ok
PRAGMA user_version    -> 0
tables in sqlite_master (type='table') -> 28
```

`lane-08_counts_before.txt` (`table\tcount`, ordered by name):

```
api_page_checkpoints	0
api_request_budget	0
api_work_progress	24
attribution_claims	4806
attribution_conflicts	0
bulk_candidates	0
canary_log	201
categories	425
companies	65
company_display_names	13
company_home_states	1
company_match_overrides	78
contributions	1674
corporate_giving	3132
executives	50
fec_response_archive	56
fec_response_observations	136
fixture_crypto	1189
industry_assets	5
leadership	2322
name_diminutives	168
observed_employers	0
review_queue_identity	0
run_log	7
run_metrics	14
scrape_progress	24
source_record_conflicts	0
trade	335
```

Column-name lists for all 28 tables: `lane-08_pragma_before.json`
(SHA256 `03abcca6241a8b328f6148ee6148d932396ff6f05d31e2b18eff8c6947990516`).

## (3) MIGRATE

`migrate_copy.R` sets the working directory to `C:/Users/pgoff/Mentat/mentat`
and reuses the sourcing loop from `mentat/tests/test_raw_contribution_columns.R`
(`for (file in c(...)) source(file.path(project_root, "R", file), local = .GlobalEnv)`),
narrowed to `paths.R` and `schema.R`, then:

```r
connection <- DBI::dbConnect(RSQLite::SQLite(), database_path)
init_schema(connection)
DBI::dbDisconnect(connection)
```

stdout:

```
wd: C:/Users/pgoff/Mentat/mentat
database: C:/Users/pgoff/AppData/Local/Temp/claude/C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-contributor-street-columns-0a1726/acfc8792-f597-44a3-ac0f-f7d883e56447/scratchpad/s2_receipts/lane-08/mentat.db
init_schema: done
```

stderr: (empty)

exit code: **0**

## (4) AFTER

```
PRAGMA integrity_check -> ok
PRAGMA user_version    -> 0
```

`lane-08_counts_after.txt`:

```
api_page_checkpoints	0
api_request_budget	0
api_work_progress	24
attribution_claims	4806
attribution_conflicts	0
bulk_candidates	0
canary_log	201
categories	425
companies	65
company_display_names	13
company_home_states	1
company_match_overrides	78
contributions	1674
corporate_giving	3132
executives	50
fec_response_archive	56
fec_response_observations	136
fixture_crypto	1189
industry_assets	5
leadership	2322
name_diminutives	168
observed_employers	0
review_queue_identity	0
run_log	7
run_metrics	14
scrape_progress	24
source_record_conflicts	0
trade	335
```

## (5) BYTE-MATCH

```
SHA256 lane-08_counts_before.txt = 63ca3749ccbf71b056d38e068b07e3858899ec2c01ac40a8d21b3283f5d48179
SHA256 lane-08_counts_after.txt  = 63ca3749ccbf71b056d38e068b07e3858899ec2c01ac40a8d21b3283f5d48179
MATCH
```

Independent byte compare: `FC: no differences encountered (exit 0)`; Python `bytes` compare of the
two files: **MATCH**
(both files 557 bytes).

**No table gained or lost a single row.**

## (6) SCHEMA DIFF (after minus before, per table, in PRAGMA order)

- `contributions`: `contributor_street_1`, `contributor_street_2`
- `bulk_candidates`: `contributor_street_1`, `contributor_street_2`
- `corporate_giving`: `contributor_street_1`, `contributor_street_2`

Every other table: no columns added, no columns removed
(tables added: none; tables dropped:
none; columns removed:
none).

Columns added anywhere outside the three S2 tables: **NONE**.
Columns added inside the three S2 tables that are not S2's two street columns:
**NONE**.

So `init_schema()` carried **no other lane's pending migration** into this
database: the diff is exactly `contributor_street_1, contributor_street_2` on
`contributions`, `bulk_candidates` and `corporate_giving`.

Street columns are the LAST two in PRAGMA order on all three tables:
contributions=True,
bulk_candidates=True,
corporate_giving=True.

## (7) PRAGMA table_info AFTER

### corporate_giving

| cid | name | type |
| --- | --- | --- |
| 0 | `sub_id` | TEXT |
| 1 | `contributor_id` | TEXT |
| 2 | `contributor_name` | TEXT |
| 3 | `contributor_city` | TEXT |
| 4 | `contributor_state` | TEXT |
| 5 | `contributor_zip` | TEXT |
| 6 | `contributor_employer` | TEXT |
| 7 | `contributor_occupation` | TEXT |
| 8 | `entity_type` | TEXT |
| 9 | `committee_id` | TEXT |
| 10 | `is_entity_contributor` | INTEGER |
| 11 | `committee_name` | TEXT |
| 12 | `recipient_committee_type` | TEXT |
| 13 | `recipient_committee_designation` | TEXT |
| 14 | `contribution_receipt_date` | TEXT |
| 15 | `contribution_receipt_amount` | REAL |
| 16 | `industry` | TEXT |
| 17 | `company` | TEXT |
| 18 | `matched_variant` | TEXT |
| 19 | `cycle` | INTEGER |
| 20 | `scraped_at` | TEXT |
| 21 | `transaction_id` | TEXT |
| 22 | `original_sub_id` | TEXT |
| 23 | `amendment_indicator` | TEXT |
| 24 | `report_year` | INTEGER |
| 25 | `report_type` | TEXT |
| 26 | `file_num` | INTEGER |
| 27 | `pdf_url` | TEXT |
| 28 | `load_date` | TEXT |
| 29 | `filing_form` | TEXT |
| 30 | `receipt_type` | TEXT |
| 31 | `receipt_type_full` | TEXT |
| 32 | `line_number` | TEXT |
| 33 | `line_number_label` | TEXT |
| 34 | `memo_code` | TEXT |
| 35 | `memoed_subtotal` | INTEGER |
| 36 | `memo_text` | TEXT |
| 37 | `back_reference_transaction_id` | TEXT |
| 38 | `back_reference_schedule_name` | TEXT |
| 39 | `is_conduit_leg` | INTEGER |
| 40 | `is_memo_leg` | INTEGER |
| 41 | `is_passthrough_leg` | INTEGER |
| 42 | `superseded_by_amendment` | INTEGER |
| 43 | `duplicate_filing_version` | INTEGER |
| 44 | `duplicate_memo` | INTEGER |
| 45 | `company_match_status` | TEXT |
| 46 | `company_match_reason` | TEXT |
| 47 | `excluded_reason` | TEXT |
| 48 | `contributor_street_1` | TEXT |
| 49 | `contributor_street_2` | TEXT |

### contributions

| cid | name | type |
| --- | --- | --- |
| 0 | `sub_id` | TEXT |
| 1 | `transaction_id` | TEXT |
| 2 | `original_sub_id` | TEXT |
| 3 | `contributor_id` | TEXT |
| 4 | `contributor_name` | TEXT |
| 5 | `contributor_first_name` | TEXT |
| 6 | `contributor_last_name` | TEXT |
| 7 | `contributor_suffix` | TEXT |
| 8 | `contributor_city` | TEXT |
| 9 | `contributor_state` | TEXT |
| 10 | `contributor_zip` | TEXT |
| 11 | `contributor_employer` | TEXT |
| 12 | `contributor_occupation` | TEXT |
| 13 | `contributor_aggregate_ytd` | REAL |
| 14 | `contribution_receipt_amount` | REAL |
| 15 | `contribution_receipt_date` | TEXT |
| 16 | `committee_id` | TEXT |
| 17 | `committee_name` | TEXT |
| 18 | `recipient_committee_type` | TEXT |
| 19 | `recipient_committee_designation` | TEXT |
| 20 | `entity_type` | TEXT |
| 21 | `election_type` | TEXT |
| 22 | `fec_election_type_desc` | TEXT |
| 23 | `receipt_type_full` | TEXT |
| 24 | `memo_code` | TEXT |
| 25 | `memoed_subtotal` | INTEGER |
| 26 | `filing_form` | TEXT |
| 27 | `receipt_type` | TEXT |
| 28 | `line_number_label` | TEXT |
| 29 | `back_reference_transaction_id` | TEXT |
| 30 | `back_reference_schedule_name` | TEXT |
| 31 | `memo_text` | TEXT |
| 32 | `conduit_committee_id` | TEXT |
| 33 | `conduit_committee_name` | TEXT |
| 34 | `amendment_indicator` | TEXT |
| 35 | `report_year` | INTEGER |
| 36 | `report_type` | TEXT |
| 37 | `file_num` | INTEGER |
| 38 | `two_year_transaction_period` | INTEGER |
| 39 | `line_number` | TEXT |
| 40 | `pdf_url` | TEXT |
| 41 | `load_date` | TEXT |
| 42 | `industry` | TEXT |
| 43 | `company` | TEXT |
| 44 | `matched_variant` | TEXT |
| 45 | `phase` | TEXT |
| 46 | `match_confidence` | TEXT |
| 47 | `scraped_at` | TEXT |
| 48 | `is_conduit_leg` | INTEGER |
| 49 | `is_memo_leg` | INTEGER |
| 50 | `is_passthrough_leg` | INTEGER |
| 51 | `memo_review` | INTEGER |
| 52 | `possible_amendment` | INTEGER |
| 53 | `superseded_by_amendment` | INTEGER |
| 54 | `duplicate_filing_version` | INTEGER |
| 55 | `duplicate_memo` | INTEGER |
| 56 | `is_refund` | INTEGER |
| 57 | `is_entity_contributor` | INTEGER |
| 58 | `company_match_status` | TEXT |
| 59 | `company_match_reason` | TEXT |
| 60 | `excluded_reason` | TEXT |
| 61 | `contributor_street_1` | TEXT |
| 62 | `contributor_street_2` | TEXT |

### bulk_candidates

| cid | name | type |
| --- | --- | --- |
| 0 | `cycle` | INTEGER |
| 1 | `company` | TEXT |
| 2 | `sub_id` | TEXT |
| 3 | `contributor_name` | TEXT |
| 4 | `contributor_city` | TEXT |
| 5 | `contributor_state` | TEXT |
| 6 | `contributor_zip` | TEXT |
| 7 | `employer_string` | TEXT |
| 8 | `contributor_occupation` | TEXT |
| 9 | `committee_id` | TEXT |
| 10 | `amount` | REAL |
| 11 | `contributor_street_1` | TEXT |
| 12 | `contributor_street_2` | TEXT |

## (8) Files beside this receipt

- `lane-08_counts_before.txt`
- `lane-08_counts_after.txt`
- `lane-08_pragma_before.json`
- `lane-08_pragma_after.json`

Copy SHA256 after migration: `a1d7eaf2f11950af94c910debd0cb2e93f6fdd967ca465e5fc3931e9f5dbc78d`
(the copy's bytes changed, as an `ALTER TABLE ADD COLUMN` must change them;
the row counts did not).
