# Mentat Crypto Accuracy Report

Reconciliation completed against the ingested Crypto fixture.

## Match stages

- S1 exact: 4
- S2 recipient prefix-25: 1
- S3 name/date/amount: 1
- S4 name/amount within +/-3 days: 1
- Total matched: 7 / 8
- Strict one-to-one match rate: 87.50%
- Present residual rows: 1
- Database coverage: 8 / 8 (100.00%)
- Invalid pipeline key rows excluded from matching: 0

## Unmatched fixture rows

1 fixture rows remain unmatched. See `fixture_unmatched.csv` for nearest-miss diagnostics.

| residual_status | rows |
| --- | --- |
| present_in_database | 1 |

### Named residual rows

| fixture_id | contributor | recipient | receipt_date | amount | status | failed_components |
| --- | --- | --- | --- | --- | --- | --- |
| 195 | NICE, DAVID | COINBASE, INC. INNOVATION PAC (COINBASE INNOVATION PAC) | 2026-03-25 | 250 | present_in_database | amount |

## Pipeline-only rows by probable cause

| probable_cause | rows |
| --- | --- |
| memo_leg | 1 |
| post_fixture_cutoff | 1 |
| unexplained | 2 |

See `pipeline_only.csv` for the row-level detail.

## Duplicate normalized tuples

- Fixture duplicate tuples: 0
- Fixture rows in duplicate tuples: 0
- Pipeline duplicate tuples: 0
- Pipeline rows in duplicate tuples: 0
