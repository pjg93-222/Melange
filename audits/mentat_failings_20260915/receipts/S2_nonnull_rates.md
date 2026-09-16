# S2 non-null address-field rates

Phase 3b, S2. Read-only census of the 11 pre-existing copies of the
2026-09-15 credit-unions run, plus the migrated + backfilled lane-08 scratch
copy. "Non-null" below means `col IS NOT NULL AND trim(col) <> ''`.

## Commands

```
cd C:/Users/pgoff/Mentat/mentat
python C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-contributor-street-columns-0a1726\acfc8792-f597-44a3-ac0f-f7d883e56447\scratchpad\s2_receipts\step5_rates.py
```

## Sources

Read-only copies (made earlier in this lane, not re-copied):
`C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-contributor-street-columns-0a1726\acfc8792-f597-44a3-ac0f-f7d883e56447\scratchpad\s2_verify\all\*.db`

| database | bytes | SHA256 |
| --- | --- | --- |
| `industry-data-mentat.db` | 880,640 | `18a032dc046c06e5b5dd908d651ef3f4d9252e165d29c286c100d054ea22a0a8` |
| `lane-01.db` | 34,689,024 | `dbd0e5b1c1e4d834b166f869023e195ca55481e7ef09280d09409f9cc91c326f` |
| `lane-02.db` | 12,431,360 | `120fff6e15d6f2f7aab079637685d94c9817f12e06e3f11bbf03f88651c263b9` |
| `lane-03.db` | 29,167,616 | `7483e448b7b62fe9ef4c55394a00c25dcbed84e6fe398d3e14eeee569a871aa8` |
| `lane-04.db` | 34,775,040 | `33eb0d500c489b3786809f0825f7c6dabd455dde9c0bde5eee579140c359248b` |
| `lane-05.db` | 3,719,168 | `22dabc325dfff31da56cabe3c543ead21394debff838f9b9341723e1eb9d144f` |
| `lane-06.db` | 15,355,904 | `bac2deef48f73f393202cd647045a89fa62d2db2741edf954f135c6639e3a6de` |
| `lane-07.db` | 8,790,016 | `ced0076078f188b337cef337f102894a567fcb356b01b175e1412929a28f5fa3` |
| `lane-08.db` | 44,154,880 | `88024fd3af04903a27a550fff5e15dc824744c97a18ee3fd62a3c909baeb5bb2` |
| `lane-09.db` | 56,647,680 | `4d0faa0957d71aed7a0e640fc98b3deea3a7fd5654b932808fb7312ad3a484ae` |
| `lane-10.db` | 8,871,936 | `45682bd41bd9a9dca2c22fbd1974ca405c1a1557fa9926a000da19e033f0a05e` |
| `lane-08 MIGRATED+BACKFILLED` | 44,154,880 | `dc4ce7cc87ba9f1f389970a985affac13ba091612eb83ee09ba023dc579f60dd` |

Migrated copy: `C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-contributor-street-columns-0a1726\acfc8792-f597-44a3-ac0f-f7d883e56447\scratchpad\s2_receipts\lane-08\mentat.db` (source
`C:\Users\pgoff\AppData\Local\Mentat\console\f897a21e05a24d1e9246b0bf972145e0\runs\20260915T152258-18548\industries\credit-unions\fanout\lanes\lane-08\mentat.db`, SHA256 `88024fd3af04903a27a550fff5e15dc824744c97a18ee3fd62a3c909baeb5bb2`).

## Street columns in the 11 pre-migration copies

**The street columns are ABSENT from every one of the 11 copies** - on both
`corporate_giving` and `contributions`, in all 11 databases. That is a missing
column, not a 0% rate: a query naming `contributor_street_1` against any of
them is a SQL error, so no rate can be quoted for them. (Verified field list
per table: `step5_rates.json`, key `street_columns_present`, `[]` everywhere.)

## corporate_giving

| database | industry / company | rows | city | state | zip | employer | occupation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| industry-data-mentat | ALL / ALL | 0 | n/a | n/a | n/a | n/a | n/a |
| lane-01 | Credit Unions / SchoolsFirst Federal Credit Union | 228 | 228 (100.00%) | 228 (100.00%) | 228 (100.00%) | 0 (0.00%) | 0 (0.00%) |
| lane-01 | ALL / ALL | 228 | 228 (100.00%) | 228 (100.00%) | 228 (100.00%) | 0 (0.00%) | 0 (0.00%) |
| lane-02 | Credit Unions / Boeing Employees Credit Union | 24 | 24 (100.00%) | 24 (100.00%) | 24 (100.00%) | 22 (91.67%) | 22 (91.67%) |
| lane-02 | ALL / ALL | 24 | 24 (100.00%) | 24 (100.00%) | 24 (100.00%) | 22 (91.67%) | 22 (91.67%) |
| lane-03 | ALL / ALL | 0 | n/a | n/a | n/a | n/a | n/a |
| lane-04 | ALL / ALL | 0 | n/a | n/a | n/a | n/a | n/a |
| lane-05 | Credit Unions / Alliant Credit Union | 1 | 1 (100.00%) | 1 (100.00%) | 1 (100.00%) | 1 (100.00%) | 1 (100.00%) |
| lane-05 | ALL / ALL | 1 | 1 (100.00%) | 1 (100.00%) | 1 (100.00%) | 1 (100.00%) | 1 (100.00%) |
| lane-06 | ALL / ALL | 0 | n/a | n/a | n/a | n/a | n/a |
| lane-07 | Credit Unions / Golden 1 Credit Union | 15 | 15 (100.00%) | 15 (100.00%) | 15 (100.00%) | 15 (100.00%) | 15 (100.00%) |
| lane-07 | ALL / ALL | 15 | 15 (100.00%) | 15 (100.00%) | 15 (100.00%) | 15 (100.00%) | 15 (100.00%) |
| lane-08 | Credit Unions / Mountain America Credit Union | 3,132 | 3132 (100.00%) | 3132 (100.00%) | 3131 (99.97%) | 3122 (99.68%) | 3123 (99.71%) |
| lane-08 | ALL / ALL | 3,132 | 3132 (100.00%) | 3132 (100.00%) | 3131 (99.97%) | 3122 (99.68%) | 3123 (99.71%) |
| lane-09 | ALL / ALL | 0 | n/a | n/a | n/a | n/a | n/a |
| lane-10 | Credit Unions / Suncoast Credit Union | 6 | 6 (100.00%) | 6 (100.00%) | 6 (100.00%) | 6 (100.00%) | 6 (100.00%) |
| lane-10 | ALL / ALL | 6 | 6 (100.00%) | 6 (100.00%) | 6 (100.00%) | 6 (100.00%) | 6 (100.00%) |

## contributions

| database | industry / company | rows | city | state | zip | employer | occupation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| industry-data-mentat | ALL / ALL | 0 | n/a | n/a | n/a | n/a | n/a |
| lane-01 | Credit Unions / SchoolsFirst Federal Credit Union | 3,911 | 3911 (100.00%) | 3911 (100.00%) | 3911 (100.00%) | 3911 (100.00%) | 3911 (100.00%) |
| lane-01 | ALL / ALL | 3,911 | 3911 (100.00%) | 3911 (100.00%) | 3911 (100.00%) | 3911 (100.00%) | 3911 (100.00%) |
| lane-02 | Credit Unions / Boeing Employees Credit Union | 509 | 509 (100.00%) | 509 (100.00%) | 509 (100.00%) | 509 (100.00%) | 508 (99.80%) |
| lane-02 | ALL / ALL | 509 | 509 (100.00%) | 509 (100.00%) | 509 (100.00%) | 509 (100.00%) | 508 (99.80%) |
| lane-03 | ALL / ALL | 0 | n/a | n/a | n/a | n/a | n/a |
| lane-04 | Credit Unions / Pentagon Federal Credit Union | 1,054 | 1054 (100.00%) | 1054 (100.00%) | 1054 (100.00%) | 1054 (100.00%) | 1054 (100.00%) |
| lane-04 | ALL / ALL | 1,054 | 1054 (100.00%) | 1054 (100.00%) | 1054 (100.00%) | 1054 (100.00%) | 1054 (100.00%) |
| lane-05 | Credit Unions / Alliant Credit Union | 302 | 302 (100.00%) | 302 (100.00%) | 302 (100.00%) | 302 (100.00%) | 302 (100.00%) |
| lane-05 | ALL / ALL | 302 | 302 (100.00%) | 302 (100.00%) | 302 (100.00%) | 302 (100.00%) | 302 (100.00%) |
| lane-06 | Credit Unions / America First Credit Union | 1,781 | 1781 (100.00%) | 1781 (100.00%) | 1781 (100.00%) | 1781 (100.00%) | 1753 (98.43%) |
| lane-06 | ALL / ALL | 1,781 | 1781 (100.00%) | 1781 (100.00%) | 1781 (100.00%) | 1781 (100.00%) | 1753 (98.43%) |
| lane-07 | Credit Unions / Golden 1 Credit Union | 666 | 666 (100.00%) | 666 (100.00%) | 666 (100.00%) | 666 (100.00%) | 665 (99.85%) |
| lane-07 | ALL / ALL | 666 | 666 (100.00%) | 666 (100.00%) | 666 (100.00%) | 666 (100.00%) | 665 (99.85%) |
| lane-08 | Credit Unions / Mountain America Credit Union | 1,674 | 1674 (100.00%) | 1674 (100.00%) | 1674 (100.00%) | 1674 (100.00%) | 1661 (99.22%) |
| lane-08 | ALL / ALL | 1,674 | 1674 (100.00%) | 1674 (100.00%) | 1674 (100.00%) | 1674 (100.00%) | 1661 (99.22%) |
| lane-09 | ALL / ALL | 0 | n/a | n/a | n/a | n/a | n/a |
| lane-10 | Credit Unions / Suncoast Credit Union | 962 | 962 (100.00%) | 962 (100.00%) | 962 (100.00%) | 962 (100.00%) | 962 (100.00%) |
| lane-10 | ALL / ALL | 962 | 962 (100.00%) | 962 (100.00%) | 962 (100.00%) | 962 (100.00%) | 962 (100.00%) |

## Street columns on the MIGRATED lane-08 copy

Pre-backfill (immediately after `init_schema()`, before
`backfill_contributor_street.py --apply`):

```
SELECT COUNT(*) FROM corporate_giving -> 3132
  contributor_street_1 IS NOT NULL    -> 0   (0.00%)
  contributor_street_2 IS NOT NULL    -> 0   (0.00%)
SELECT COUNT(*) FROM contributions    -> 1674
  contributor_street_1 IS NOT NULL    -> 0   (0.00%)
  contributor_street_2 IS NOT NULL    -> 0   (0.00%)
```

Post-backfill (see `S2_backfill_lane08.md`):

| table | industry / company | rows | contributor_street_1 | contributor_street_2 |
| --- | --- | --- | --- | --- |
| corporate_giving | Credit Unions / Mountain America Credit Union | 3,132 | 3132 (100.00%) | 35 (1.12%) |
| corporate_giving | ALL / ALL | 3,132 | 3132 (100.00%) | 35 (1.12%) |
| contributions | Credit Unions / Mountain America Credit Union | 1,674 | 1674 (100.00%) | 58 (3.46%) |
| contributions | ALL / ALL | 1,674 | 1674 (100.00%) | 58 (3.46%) |

`contributor_street_2` is genuinely sparse in the source filings - the backfill
copies both halves from the SAME archive record, so a filing with no second
address line lands as SQL `NULL`, not as a lost value.
