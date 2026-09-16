# S2 informational - lane-01 corporate_giving employer/occupation

Phase 3b, S2. Read-only, on the migrated scratch copy of lane-01 (the
migration added only the two street columns and changed no row; see
`S2_backfill_lane08.md`). No live database was opened. No fix is proposed
here.

## Commands

```
cd C:/Users/pgoff/Mentat/mentat
python C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-contributor-street-columns-0a1726\acfc8792-f597-44a3-ac0f-f7d883e56447\scratchpad\s2_receipts\step6_employer_zero.py
```

## Source

| field | value |
| --- | --- |
| source path | `C:\Users\pgoff\AppData\Local\Mentat\console\f897a21e05a24d1e9246b0bf972145e0\runs\20260915T152258-18548\industries\credit-unions\fanout\lanes\lane-01\mentat.db` |
| source bytes | 34,689,024 |
| source SHA256 | `dbd0e5b1c1e4d834b166f869023e195ca55481e7ef09280d09409f9cc91c326f` |
| copy | `C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-contributor-street-columns-0a1726\acfc8792-f597-44a3-ac0f-f7d883e56447\scratchpad\s2_receipts\lane-01\mentat.db` (byte-identical to source before migration) |

## Counts

Evidence: `fec_response_archive` rows with
`payload_kind = 'fec_api_response_body'`, read in
`ORDER BY created_at, archive_sha256`, records under `payload_json["results"]`,
first record per `sub_id` wins - the same reader the backfill tool uses.

| measure | count | of 228 |
| --- | --- | --- |
| `corporate_giving` rows | 228 | 100.00% |
| stored `contributor_employer` non-empty | 0 | 0.00% |
| stored `contributor_occupation` non-empty | 0 | 0.00% |
| archive records matched by `sub_id` | 228 | 100.00% |
| archive `contributor_employer` non-empty | 0 | 0.00% |
| archive `contributor_occupation` non-empty | 0 | 0.00% |

Example pairs: **none exist.** The receipt asked for three
(archive employer value vs stored `''`); there are zero archive records with a
non-empty employer to draw them from. The value in every one of the 228
matched archive records is JSON `null` for both fields - not an absent key and
not `''`:

```
distribution of payload_json["results"][*].contributor_employer   -> {None: 228}
distribution of payload_json["results"][*].contributor_occupation -> {None: 228}
```

Two further counts from the same 228 rows and the same 228 archive records,
reported because they bound what the first table can mean:

```
stored entity_type on the 228 corporate_giving rows -> ORG 174, PAC 37, COM 17 (IND 0)
lane-08 corporate_giving, same run, 3,132 rows      -> IND 3,129, ORG 2, PAC 1
lane-08 corporate_giving rows with empty employer   -> 10 (IND 7, ORG 2, PAC 1)
```

## What this shows

The API delivered a non-empty `contributor_employer` for **0 of the 228** rows
and a non-empty `contributor_occupation` for **0 of the 228**: every one of the
228 archived records carries JSON `null` in both fields. The stored `''`
therefore agrees with the archived
response rather than departing from it, so on this snapshot the '' is not
evidence of a value that the API delivered and Mentat then dropped; whatever
DEFECT-EMPLOYER-ZERO describes, the response bodies do not contain the missing
employer strings for these 228 rows. The counts also show that the 228 rows are
entirely non-individual contributors (ORG/PAC/COM), while the lane-08
corporate_giving rows that DO carry employer are almost entirely `IND` and its
3 non-individual rows are likewise empty. These are counts, not a cause: they
establish where the zeros are, not why the API sent null.
