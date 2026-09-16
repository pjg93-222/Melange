# S2 backfill receipt - lane-08 (+ lane-01 dry run)

Phase 3b, S2. `tools/backfill_contributor_street.py` run against the MIGRATED
scratch copy of lane-08. No live database was opened; the backfill reads
`fec_response_archive` / `api_page_checkpoints` and writes two columns.

## Commands

```
cd C:/Users/pgoff/Mentat/mentat

# (1) dry run
python tools/backfill_contributor_street.py C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-contributor-street-columns-0a1726\acfc8792-f597-44a3-ac0f-f7d883e56447\scratchpad\s2_receipts\lane-08\mentat.db ^
  --receipt C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-contributor-street-columns-0a1726\acfc8792-f597-44a3-ac0f-f7d883e56447\scratchpad\s2_receipts\lane-08\backfill_dry.json

# (2) apply
python tools/backfill_contributor_street.py C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-contributor-street-columns-0a1726\acfc8792-f597-44a3-ac0f-f7d883e56447\scratchpad\s2_receipts\lane-08\mentat.db --apply ^
  --receipt C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-contributor-street-columns-0a1726\acfc8792-f597-44a3-ac0f-f7d883e56447\scratchpad\s2_receipts\lane-08\backfill_apply.json

# (5) idempotence: apply a second time
python tools/backfill_contributor_street.py C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-contributor-street-columns-0a1726\acfc8792-f597-44a3-ac0f-f7d883e56447\scratchpad\s2_receipts\lane-08\mentat.db --apply ^
  --receipt C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-contributor-street-columns-0a1726\acfc8792-f597-44a3-ac0f-f7d883e56447\scratchpad\s2_receipts\lane-08\backfill_apply_2.json

# (6) refusal on an UN-MIGRATED fresh copy of the same snapshot
python tools/backfill_contributor_street.py C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-contributor-street-columns-0a1726\acfc8792-f597-44a3-ac0f-f7d883e56447\scratchpad\s2_receipts\unmigrated\mentat.db ^
  --receipt C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-contributor-street-columns-0a1726\acfc8792-f597-44a3-ac0f-f7d883e56447\scratchpad\s2_receipts\unmigrated\backfill_dry.json

# lane-01: fresh copy, migrate, dry run
"C:/Program Files/R/R-4.6.0/bin/Rscript.exe" C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-contributor-street-columns-0a1726\acfc8792-f597-44a3-ac0f-f7d883e56447\scratchpad\s2_receipts\migrate_copy.R C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-contributor-street-columns-0a1726\acfc8792-f597-44a3-ac0f-f7d883e56447\scratchpad\s2_receipts\lane-01\mentat.db
python tools/backfill_contributor_street.py C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-contributor-street-columns-0a1726\acfc8792-f597-44a3-ac0f-f7d883e56447\scratchpad\s2_receipts\lane-01\mentat.db ^
  --receipt C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-contributor-street-columns-0a1726\acfc8792-f597-44a3-ac0f-f7d883e56447\scratchpad\s2_receipts\lane-01\backfill_dry.json

# (4) spot-check, (3) rates
python C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-contributor-street-columns-0a1726\acfc8792-f597-44a3-ac0f-f7d883e56447\scratchpad\s2_receipts\step4_spotcheck.py
python C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-contributor-street-columns-0a1726\acfc8792-f597-44a3-ac0f-f7d883e56447\scratchpad\s2_receipts\step5_rates.py
```

## Sources

| database | path | bytes | SHA256 |
| --- | --- | --- | --- |
| lane-08 | `C:\Users\pgoff\AppData\Local\Mentat\console\f897a21e05a24d1e9246b0bf972145e0\runs\20260915T152258-18548\industries\credit-unions\fanout\lanes\lane-08\mentat.db` | 44,154,880 | `88024fd3af04903a27a550fff5e15dc824744c97a18ee3fd62a3c909baeb5bb2` |
| lane-01 | `C:\Users\pgoff\AppData\Local\Mentat\console\f897a21e05a24d1e9246b0bf972145e0\runs\20260915T152258-18548\industries\credit-unions\fanout\lanes\lane-01\mentat.db` | 34,689,024 | `dbd0e5b1c1e4d834b166f869023e195ca55481e7ef09280d09409f9cc91c326f` |
| lane-01 copy | `C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-contributor-street-columns-0a1726\acfc8792-f597-44a3-ac0f-f7d883e56447\scratchpad\s2_receipts\lane-01\mentat.db` (fresh copy, SHA256 equal to source before migration) | 34,689,024 | `dbd0e5b1c1e4d834b166f869023e195ca55481e7ef09280d09409f9cc91c326f` |

## (1) DRY RUN - lane-08

```json
{
  "database": "C:\\Users\\pgoff\\AppData\\Local\\Temp\\claude\\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-contributor-street-columns-0a1726\\acfc8792-f597-44a3-ac0f-f7d883e56447\\scratchpad\\s2_receipts\\lane-08\\mentat.db",
  "applied": false,
  "evidence": {
    "archive_records": 4806,
    "checkpoint_records": 0,
    "distinct_sub_ids": 4780,
    "conflicts": 0
  },
  "tables": {
    "corporate_giving": {
      "rows": 3132,
      "candidates": 3132,
      "matched": 3132,
      "updated": 0,
      "unmatched": 0
    },
    "contributions": {
      "rows": 1674,
      "candidates": 1674,
      "matched": 1674,
      "updated": 0,
      "unmatched": 0
    }
  }
}
```

Verification that the dry run wrote nothing:

```
SHA256 lane-08_counts_after.txt                  = 63ca3749ccbf71b056d38e068b07e3858899ec2c01ac40a8d21b3283f5d48179
SHA256 of a fresh count taken after the dry run  = 63ca3749ccbf71b056d38e068b07e3858899ec2c01ac40a8d21b3283f5d48179
MATCH
SELECT count(*) FROM corporate_giving WHERE contributor_street_1 IS NOT NULL -> 0
```

The tool opens the database with `?mode=ro` unless `--apply` is given
(`tools/backfill_contributor_street.py`, `run()`:
`uri = path.resolve().as_uri() + ("?mode=rw" if apply else "?mode=ro")`).

## (2) APPLY - lane-08

```json
{
  "database": "C:\\Users\\pgoff\\AppData\\Local\\Temp\\claude\\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-contributor-street-columns-0a1726\\acfc8792-f597-44a3-ac0f-f7d883e56447\\scratchpad\\s2_receipts\\lane-08\\mentat.db",
  "applied": true,
  "evidence": {
    "archive_records": 4806,
    "checkpoint_records": 0,
    "distinct_sub_ids": 4780,
    "conflicts": 0
  },
  "tables": {
    "corporate_giving": {
      "rows": 3132,
      "candidates": 3132,
      "matched": 3132,
      "updated": 3132,
      "unmatched": 0
    },
    "contributions": {
      "rows": 1674,
      "candidates": 1674,
      "matched": 1674,
      "updated": 1674,
      "unmatched": 0
    }
  }
}
```

Recount of EVERY table after the apply
(`lane-08_counts_after_backfill.txt`):

```
SHA256 lane-08_counts_after.txt          = 63ca3749ccbf71b056d38e068b07e3858899ec2c01ac40a8d21b3283f5d48179
SHA256 lane-08_counts_after_backfill.txt = 63ca3749ccbf71b056d38e068b07e3858899ec2c01ac40a8d21b3283f5d48179
MATCH
PRAGMA integrity_check -> ok
```

The backfill updated 3,132 +
1,674 rows and inserted or deleted
none.

## (3) Post-backfill street rates, per company

| table | industry / company | rows | contributor_street_1 | contributor_street_2 |
| --- | --- | --- | --- | --- |
| corporate_giving | Credit Unions / Mountain America Credit Union | 3,132 | 3132 (100.00%) | 35 (1.12%) |
| contributions | Credit Unions / Mountain America Credit Union | 1,674 | 1674 (100.00%) | 58 (3.46%) |

(fed into `S2_nonnull_rates.md`)

## (4) Spot-check: stored row vs the archived FEC response

Three `corporate_giving` rows, lowest `sub_id` first. House numbers are masked
with `###` in this receipt; the equality columns compare the UNMASKED values.

| sub_id | stored street_1 (masked) | stored street_2 | archive street_1 (masked) | archive street_2 | street_1 equal | street_2 equal |
| --- | --- | --- | --- | --- | --- | --- |
| `1121420220265186565` | `### SLATE STREET` | `<NULL>` | `### SLATE STREET` | `<NULL>` | YES | YES |
| `1121420220265187369` | `### SLATE STREET` | `<NULL>` | `### SLATE STREET` | `<NULL>` | YES | YES |
| `1121420220265192471` | `### SLATE STREET` | `<NULL>` | `### SLATE STREET` | `<NULL>` | YES | YES |

All three rows match the archived response body exactly, including the `NULL`
`contributor_street_2`.

## (5) Idempotence - second `--apply`

```json
{
  "database": "C:\\Users\\pgoff\\AppData\\Local\\Temp\\claude\\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-contributor-street-columns-0a1726\\acfc8792-f597-44a3-ac0f-f7d883e56447\\scratchpad\\s2_receipts\\lane-08\\mentat.db",
  "applied": true,
  "evidence": {
    "archive_records": 4806,
    "checkpoint_records": 0,
    "distinct_sub_ids": 4780,
    "conflicts": 0
  },
  "tables": {
    "corporate_giving": {
      "rows": 3132,
      "candidates": 0,
      "matched": 0,
      "updated": 0,
      "unmatched": 0
    },
    "contributions": {
      "rows": 1674,
      "candidates": 0,
      "matched": 0,
      "updated": 0,
      "unmatched": 0
    }
  }
}
```

`updated` is **0** for both tables, `candidates` is 0 (nothing is left with an
empty `contributor_street_1`), and the recount after the second apply is still
byte-identical to `lane-08_counts_after.txt` (SHA256
`63ca3749ccbf71b056d38e068b07e3858899ec2c01ac40a8d21b3283f5d48179`, **MATCH**).

## (6) Refusal on an UN-MIGRATED copy

Exit code: **1**. stdout: empty. stderr (tail):

```
RuntimeError: backfill_contributor_street refuses to run -- corporate_giving: missing contributor_street_1, contributor_street_2; contributions: missing contributor_street_1, contributor_street_2. Run init_schema() from mentat/R/schema.R against this database first; it adds the street columns without touching the rows.
```

The refusal names `init_schema()` and the exact missing columns, and it fires
before any evidence is read, so a database that cannot hold a street is never
confused with one that has no evidence.

## lane-01 dry run (migrated fresh copy)

`init_schema()` on the fresh lane-01 copy added exactly
`contributor_street_1, contributor_street_2` to `contributions`,
`bulk_candidates` and `corporate_giving`, and the count file was byte-identical
before and after (SHA256
`39dfbe3875d9313ccc4023aadb49c42546b840f818c7071331efeee4ab2f2e0f`, MATCH).

```json
{
  "database": "C:\\Users\\pgoff\\AppData\\Local\\Temp\\claude\\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-contributor-street-columns-0a1726\\acfc8792-f597-44a3-ac0f-f7d883e56447\\scratchpad\\s2_receipts\\lane-01\\mentat.db",
  "applied": false,
  "evidence": {
    "archive_records": 4149,
    "checkpoint_records": 0,
    "distinct_sub_ids": 4139,
    "conflicts": 0
  },
  "tables": {
    "corporate_giving": {
      "rows": 228,
      "candidates": 228,
      "matched": 228,
      "updated": 0,
      "unmatched": 0
    },
    "contributions": {
      "rows": 3911,
      "candidates": 3911,
      "matched": 3911,
      "updated": 0,
      "unmatched": 0
    }
  }
}
```

`corporate_giving` matched **228
of 228** - every row, as expected. `contributions` matched
3,911 of
3,911. Nothing was applied to
lane-01.
