# S2 - contributor_street backfill DRY RUN on production databases

Tool: `mentat/tools/backfill_contributor_street.py` (committed at `d78cf0b8f`).
Every run below is a DRY RUN. `--apply` was never passed, anywhere.

**No production database file was opened as a database, migrated or written.** Each source file was copied byte-for-byte (with its `-wal` / `-shm` siblings) with `shutil.copyfile`, which only reads; SHA256 of source and copy were compared before any other step, and the source SHA256 was recomputed after every database finished. All work - the refusal check, `init_schema()`, and both dry runs - happened on the copy under the session scratchpad.

Stated precisely, because it is the one place a production path is touched at all: production files were read in exactly two ways, both read-only. (1) `shutil.copyfile`, to make the copy. (2) the sequential raw-byte scan in 1.1, which opens the file as a plain byte stream (`open(path, "rb")`) - no SQLite connection, no lock, no WAL replay, no write. Every `sqlite3.connect()` and every invocation of the backfill tool in this run targeted a scratchpad copy, enforced in code by a guard that raises on any path without `s2_prod_dryrun` in it, and confirmed afterwards against the recorded command lines (0 of 72 referenced a production path).

## 1. Inventory

Search roots (recursive, `*.db` / `*.sqlite` / `*.sqlite3`, skipping `node_modules` and `.git`):

| root | present |
| --- | --- |
| `C:\Users\pgoff\Mentat\.cache` | NO - does not exist |
| `C:\Users\pgoff\Mentat\mentat\.cache` | yes |
| `C:\Users\pgoff\Mentat\mentat\state` | yes |
| `C:\Users\pgoff\Mentat\outputs` | yes |
| `C:\Users\pgoff\Mentat\reports` | yes |
| `C:\Users\pgoff\AppData\Local\Mentat` | yes |

**Correction to the brief.** The brief named `C:\Users\pgoff\Mentat\.cache\...`. That directory does not exist. The cache lives one level deeper, at `C:\Users\pgoff\Mentat\mentat\.cache\`, and that is where both the `receipt-metadata-repair-20260910` and `repair-20260908-databases` sets were found. `C:\Users\pgoff\Mentat\reports` exists but holds no SQLite file.

Enumerated files, by class:

| class | files | bytes | GB |
| --- | ---: | ---: | ---: |
| appdata-other | 1 | 12,288 | 0.00 |
| browser-profile | 7 | 253,952 | 0.00 |
| cache-other | 14 | 1,847,428,096 | 1.72 |
| outputs | 16 | 196,608 | 0.00 |
| repair-20260908 | 8 | 1,726,144,512 | 1.61 |
| report-input-20260910 | 7 | 1,743,925,248 | 1.62 |
| run-lane | 11 | 249,483,264 | 0.23 |
| state | 305 | 33,254,252,544 | 30.97 |
| **TOTAL** | **369** | **38,821,696,512** | **36.16** |

369 files / 36.16 GB exceeds the brief's cap of 25 databases or 40 GB, so the sampling clause applies (see 1.2).

### 1.1 Pruning files that cannot hold `corporate_giving`

Opening 369 databases means copying 36 GB, so the set was first pruned with a **raw-byte scan** that never opens a SQLite connection, takes no lock, replays no WAL and writes nothing. SQLite stores each table's `CREATE TABLE` text verbatim in `sqlite_master`, so a database that really has a `corporate_giving` table is guaranteed to contain those bytes: a file with no hit definitely lacks the table. The scan is an over-approximation (the string can also sit inside a `payload_json` blob), so every hit was confirmed afterwards by opening a copy.

- files scanned: **369** (36.00 GB), read errors: 0
- definitely NO `corporate_giving`: **287** (skipped, per the brief)
- possible `corporate_giving` (byte hit): **82**

### 1.2 What was examined

| class | byte-hits | examined | policy |
| --- | ---: | ---: | --- |
| cache-other | 5 | 5 | ALL |
| outputs | 6 | 6 | ALL |
| repair-20260908 | 8 | 8 | ALL |
| report-input-20260910 | 7 | 7 | ALL - the brief names this set explicitly |
| run-lane | 11 | 11 | ALL |
| state | 45 | 4 | SAMPLED - smallest + largest of each family |
| **TOTAL** | **82** | **41** | |

**Sampling disclosure.** The `state/` byte-hits are 45 files / 25.0 GB in two families (`contribution-analytics`, `cross-reference`). Copying all of them is not proportionate, so the smallest and the largest member of each family was examined (4 files) and the remaining 41 were not. Every non-`state` byte-hit was examined in full (37 files).

### 1.3 Inventory of the examined databases

`corporate_giving`, `contributions`, `fec_response_archive`, `api_page_checkpoints`: table present in the un-migrated copy. `street?`: whether `corporate_giving` already had `contributor_street_1` before migration.

| class | industry / lane | size | mtime (UTC) | corp_giving | contributions | fec_archive | checkpoints | street? |
| --- | --- | ---: | --- | :-: | :-: | :-: | :-: | :-: |
| report-input-20260910 | community_banks | 5,906,432 | 2026-09-11T00:16:55 | yes | yes | no | yes | no |
| report-input-20260910 | credit_arms | 468,652,032 | 2026-09-11T00:16:57 | yes | yes | no | yes | no |
| report-input-20260910 | credit_union | 62,472,192 | 2026-09-11T00:16:58 | yes | yes | no | yes | no |
| report-input-20260910 | crypto | 13,393,920 | 2026-09-11T00:16:58 | yes | yes | no | yes | no |
| report-input-20260910 | fintech | 66,641,920 | 2026-09-11T00:16:58 | yes | yes | no | yes | no |
| report-input-20260910 | property_casualty_insurance | 365,092,864 | 2026-09-11T00:17:02 | yes | yes | no | yes | no |
| report-input-20260910 | telecom | 761,765,888 | 2026-09-11T00:17:03 | yes | yes | no | yes | no |
| repair-20260908 | community_banks | 4,280,320 | 2026-09-08T05:50:12 | yes | yes | no | yes | no |
| repair-20260908 | credit_arms | 347,656,192 | 2026-09-08T05:50:13 | yes | yes | no | yes | no |
| repair-20260908 | credit_union | 382,787,584 | 2026-09-08T05:41:29 | yes | yes | no | yes | no |
| repair-20260908 | crypto | 20,271,104 | 2026-09-08T05:41:27 | yes | yes | no | yes | no |
| repair-20260908 | crypto_recollected | 20,320,256 | 2026-09-08T05:54:40 | yes | yes | no | yes | no |
| repair-20260908 | fintech | 58,269,696 | 2026-09-08T05:41:27 | yes | yes | no | yes | no |
| repair-20260908 | property_casualty_insurance | 286,842,880 | 2026-09-08T05:50:14 | yes | yes | no | yes | no |
| repair-20260908 | telecom | 605,716,480 | 2026-09-08T05:50:48 | yes | yes | no | yes | no |
| run-lane | credit-unions-data | 880,640 | 2026-09-15T19:23:04 | yes | yes | yes | yes | no |
| run-lane | lane-01 | 34,689,024 | 2026-09-15T19:33:33 | yes | yes | yes | yes | no |
| run-lane | lane-02 | 12,431,360 | 2026-09-15T19:39:06 | yes | yes | yes | yes | no |
| run-lane | lane-03 | 29,167,616 | 2026-09-15T19:40:28 | yes | yes | yes | yes | no |
| run-lane | lane-04 | 34,775,040 | 2026-09-15T19:41:19 | yes | yes | yes | yes | no |
| run-lane | lane-05 | 3,719,168 | 2026-09-15T19:33:38 | yes | yes | yes | yes | no |
| run-lane | lane-06 | 15,355,904 | 2026-09-15T19:29:51 | yes | yes | yes | yes | no |
| run-lane | lane-07 | 8,790,016 | 2026-09-15T19:28:08 | yes | yes | yes | yes | no |
| run-lane | lane-08 | 44,154,880 | 2026-09-15T19:39:51 | yes | yes | yes | yes | no |
| run-lane | lane-09 | 56,647,680 | 2026-09-15T19:41:44 | yes | yes | yes | yes | no |
| run-lane | lane-10 | 8,871,936 | 2026-09-15T19:29:18 | yes | yes | yes | yes | no |
| cache-other | fairshake-20260908 | 20,324,352 | 2026-09-08T17:26:18 | yes | yes | no | yes | no |
| cache-other | recollection-lane-1 | 20,475,904 | 2026-09-08T05:52:26 | yes | yes | no | yes | no |
| cache-other | recollection-lane-2 | 20,406,272 | 2026-09-08T05:52:35 | yes | yes | no | yes | no |
| cache-other | recollection-lane-3 | 20,271,104 | 2026-09-08T05:52:08 | yes | yes | no | yes | no |
| cache-other | banking-20260910 | 861,224,960 | 2026-09-10T15:18:47 | yes | yes | no | yes | no |
| outputs | 25bfa50c23dd40b49fc592388cda664f-identity | 12,288 | 2026-09-13T03:33:12 | yes | yes | no | no | no |
| outputs | 25bfa50c23dd40b49fc592388cda664f-scope_expansion | 12,288 | 2026-09-13T03:33:12 | yes | yes | no | no | no |
| outputs | 6816df6e73e044b0b264996aa7648a92-identity | 12,288 | 2026-09-13T03:35:37 | yes | yes | no | no | no |
| outputs | 6816df6e73e044b0b264996aa7648a92-scope_expansion | 12,288 | 2026-09-13T03:35:37 | yes | yes | no | no | no |
| outputs | accc5969fefd43559ff85c14d21ae1fc-identity | 12,288 | 2026-09-13T03:34:53 | yes | yes | no | no | no |
| outputs | accc5969fefd43559ff85c14d21ae1fc-scope_expansion | 12,288 | 2026-09-13T03:34:53 | yes | yes | no | no | no |
| state | contribution-analytics-508c57296863 | 3,047,424 | 2026-09-12T23:32:44 | no | no | no | no | no |
| state | contribution-analytics-d379128c9470 | 717,082,624 | 2026-09-15T17:23:38 | no | no | no | no | no |
| state | cross-reference-ledger | 262,782,976 | 2026-09-11T00:57:50 | no | no | no | no | no |
| state | cross-reference-ledger | 3,673,088,000 | 2026-09-13T07:08:25 | no | no | no | no | no |

**4 of the examined files had no `corporate_giving` TABLE** - the byte hit was a false positive from a payload blob. They were skipped per the brief and never migrated (running `init_schema()` on them would have CREATED the entire Mentat schema inside an unrelated database):

- `C:\Users\pgoff\Mentat\mentat\state\contribution-analytics\508c57296863734c68e66fb0f37c51e9949afe2fd07185d9f87a5059971f04e9.sqlite`
- `C:\Users\pgoff\Mentat\mentat\state\contribution-analytics\d379128c947084d9c1342ffceb00e8386b2cf36fe66da1873d1e277d0d1054a9.sqlite`
- `C:\Users\pgoff\Mentat\mentat\state\cross-reference\20260911T005725-56ca38280348\ledger.sqlite`
- `C:\Users\pgoff\Mentat\mentat\state\cross-reference\20260913T070028-ac0de1a54fdd\ledger.sqlite`

## 2. Results

31 databases completed the full sequence: copy -> refusal on the un-migrated copy -> `init_schema()` -> dry run with `--receipt`.

`would update` = `matched`, per table: the rows the backfill would write if it were run with `--apply`.

| class | industry / lane | corp_giving rows | contributions rows | fec_archive records | checkpoint records | distinct sub_ids | conflicts | CG cand | CG matched | CG unmatched | CN cand | CN matched | CN unmatched | would update |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| report-input-20260910 | community_banks | 368 | 4,293 | 0 | 0 | 0 | 0 | 368 | 0 | 368 | 4,293 | 0 | 4,293 | **0** |
| report-input-20260910 | credit_arms | 10,695 | 424,988 | 0 | 0 | 0 | 0 | 10,695 | 0 | 10,695 | 424,988 | 0 | 424,988 | **0** |
| report-input-20260910 | credit_union | 11,232 | 56,078 | 0 | 0 | 0 | 0 | 11,232 | 0 | 11,232 | 56,078 | 0 | 56,078 | **0** |
| report-input-20260910 | crypto | 1,518 | 13,326 | 0 | 0 | 0 | 0 | 1,518 | 0 | 1,518 | 13,326 | 0 | 13,326 | **0** |
| report-input-20260910 | fintech | 45,754 | 41,082 | 0 | 0 | 0 | 0 | 45,754 | 0 | 45,754 | 41,082 | 0 | 41,082 | **0** |
| report-input-20260910 | property_casualty_insurance | 31,579 | 329,509 | 0 | 0 | 0 | 0 | 31,579 | 0 | 31,579 | 329,509 | 0 | 329,509 | **0** |
| report-input-20260910 | telecom | 63,633 | 746,070 | 0 | 0 | 0 | 0 | 63,633 | 0 | 63,633 | 746,070 | 0 | 746,070 | **0** |
| repair-20260908 | community_banks | 0 | 4,099 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4,099 | 0 | 4,099 | **0** |
| repair-20260908 | credit_arms | 4,535 | 423,654 | 0 | 0 | 0 | 0 | 4,535 | 0 | 4,535 | 423,654 | 0 | 423,654 | **0** |
| repair-20260908 | credit_union | 6,564 | 461,792 | 0 | 0 | 0 | 0 | 6,564 | 0 | 6,564 | 461,792 | 0 | 461,792 | **0** |
| repair-20260908 | crypto | 1,022 | 14,818 | 0 | 0 | 0 | 0 | 1,022 | 0 | 1,022 | 14,818 | 0 | 14,818 | **0** |
| repair-20260908 | crypto_recollected | 1,022 | 14,850 | 0 | 0 | 0 | 0 | 1,022 | 0 | 1,022 | 14,850 | 0 | 14,850 | **0** |
| repair-20260908 | fintech | 45,735 | 41,071 | 0 | 0 | 0 | 0 | 45,735 | 0 | 45,735 | 41,071 | 0 | 41,071 | **0** |
| repair-20260908 | property_casualty_insurance | 20,446 | 345,624 | 0 | 0 | 0 | 0 | 20,446 | 0 | 20,446 | 345,624 | 0 | 345,624 | **0** |
| repair-20260908 | telecom | 63,633 | 746,070 | 0 | 0 | 0 | 0 | 63,633 | 0 | 63,633 | 746,070 | 0 | 746,070 | **0** |
| run-lane | credit-unions-data | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | **0** |
| run-lane | lane-01 | 228 | 3,911 | 4,149 | 0 | 4,139 | 0 | 228 | 228 | 0 | 3,911 | 3,911 | 0 | **4,139** |
| run-lane | lane-02 | 24 | 509 | 1,972 | 200 | 1,969 | 0 | 24 | 24 | 0 | 509 | 509 | 0 | **533** |
| run-lane | lane-03 | 0 | 0 | 5,791 | 600 | 5,691 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | **0** |
| run-lane | lane-04 | 0 | 1,054 | 3,884 | 1,200 | 3,725 | 0 | 0 | 0 | 0 | 1,054 | 1,054 | 0 | **1,054** |
| run-lane | lane-05 | 1 | 302 | 303 | 0 | 303 | 0 | 1 | 1 | 0 | 302 | 302 | 0 | **303** |
| run-lane | lane-06 | 0 | 1,781 | 1,781 | 0 | 1,781 | 0 | 0 | 0 | 0 | 1,781 | 1,781 | 0 | **1,781** |
| run-lane | lane-07 | 15 | 666 | 1,021 | 0 | 681 | 0 | 15 | 15 | 0 | 666 | 666 | 0 | **681** |
| run-lane | lane-08 | 3,132 | 1,674 | 4,806 | 0 | 4,780 | 0 | 3,132 | 3,132 | 0 | 1,674 | 1,674 | 0 | **4,806** |
| run-lane | lane-09 | 0 | 0 | 8,827 | 2,200 | 8,624 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | **0** |
| run-lane | lane-10 | 6 | 962 | 968 | 0 | 968 | 0 | 6 | 6 | 0 | 962 | 962 | 0 | **968** |
| cache-other | fairshake-20260908 | 1,022 | 14,850 | 0 | 0 | 0 | 0 | 1,022 | 0 | 1,022 | 14,850 | 0 | 14,850 | **0** |
| cache-other | recollection-lane-1 | 1,022 | 14,839 | 0 | 0 | 0 | 0 | 1,022 | 0 | 1,022 | 14,839 | 0 | 14,839 | **0** |
| cache-other | recollection-lane-2 | 1,022 | 14,829 | 0 | 0 | 0 | 0 | 1,022 | 0 | 1,022 | 14,829 | 0 | 14,829 | **0** |
| cache-other | recollection-lane-3 | 1,022 | 14,818 | 0 | 0 | 0 | 0 | 1,022 | 0 | 1,022 | 14,818 | 0 | 14,818 | **0** |
| cache-other | banking-20260910 | 67,421 | 783,808 | 0 | 32,582 | 32,581 | 0 | 67,421 | 0 | 67,421 | 783,808 | 32,581 | 751,227 | **32,581** |

### 2.1 Coverage (matched / candidates)

- `report-input-20260910/community_banks`: corporate_giving 0/368 = **0.00%**; contributions 0/4,293 = **0.00%**
- `report-input-20260910/credit_arms`: corporate_giving 0/10,695 = **0.00%**; contributions 0/424,988 = **0.00%**
- `report-input-20260910/credit_union`: corporate_giving 0/11,232 = **0.00%**; contributions 0/56,078 = **0.00%**
- `report-input-20260910/crypto`: corporate_giving 0/1,518 = **0.00%**; contributions 0/13,326 = **0.00%**
- `report-input-20260910/fintech`: corporate_giving 0/45,754 = **0.00%**; contributions 0/41,082 = **0.00%**
- `report-input-20260910/property_casualty_insurance`: corporate_giving 0/31,579 = **0.00%**; contributions 0/329,509 = **0.00%**
- `report-input-20260910/telecom`: corporate_giving 0/63,633 = **0.00%**; contributions 0/746,070 = **0.00%**
- `repair-20260908/community_banks`: corporate_giving 0/0 = **n/a (no candidates)**; contributions 0/4,099 = **0.00%**
- `repair-20260908/credit_arms`: corporate_giving 0/4,535 = **0.00%**; contributions 0/423,654 = **0.00%**
- `repair-20260908/credit_union`: corporate_giving 0/6,564 = **0.00%**; contributions 0/461,792 = **0.00%**
- `repair-20260908/crypto`: corporate_giving 0/1,022 = **0.00%**; contributions 0/14,818 = **0.00%**
- `repair-20260908/crypto_recollected`: corporate_giving 0/1,022 = **0.00%**; contributions 0/14,850 = **0.00%**
- `repair-20260908/fintech`: corporate_giving 0/45,735 = **0.00%**; contributions 0/41,071 = **0.00%**
- `repair-20260908/property_casualty_insurance`: corporate_giving 0/20,446 = **0.00%**; contributions 0/345,624 = **0.00%**
- `repair-20260908/telecom`: corporate_giving 0/63,633 = **0.00%**; contributions 0/746,070 = **0.00%**
- `run-lane/credit-unions-data`: corporate_giving 0/0 = **n/a (no candidates)**; contributions 0/0 = **n/a (no candidates)**
- `run-lane/lane-01`: corporate_giving 228/228 = **100.00%**; contributions 3,911/3,911 = **100.00%**
- `run-lane/lane-02`: corporate_giving 24/24 = **100.00%**; contributions 509/509 = **100.00%**
- `run-lane/lane-03`: corporate_giving 0/0 = **n/a (no candidates)**; contributions 0/0 = **n/a (no candidates)**
- `run-lane/lane-04`: corporate_giving 0/0 = **n/a (no candidates)**; contributions 1,054/1,054 = **100.00%**
- `run-lane/lane-05`: corporate_giving 1/1 = **100.00%**; contributions 302/302 = **100.00%**
- `run-lane/lane-06`: corporate_giving 0/0 = **n/a (no candidates)**; contributions 1,781/1,781 = **100.00%**
- `run-lane/lane-07`: corporate_giving 15/15 = **100.00%**; contributions 666/666 = **100.00%**
- `run-lane/lane-08`: corporate_giving 3,132/3,132 = **100.00%**; contributions 1,674/1,674 = **100.00%**
- `run-lane/lane-09`: corporate_giving 0/0 = **n/a (no candidates)**; contributions 0/0 = **n/a (no candidates)**
- `run-lane/lane-10`: corporate_giving 6/6 = **100.00%**; contributions 962/962 = **100.00%**
- `cache-other/fairshake-20260908`: corporate_giving 0/1,022 = **0.00%**; contributions 0/14,850 = **0.00%**
- `cache-other/recollection-lane-1`: corporate_giving 0/1,022 = **0.00%**; contributions 0/14,839 = **0.00%**
- `cache-other/recollection-lane-2`: corporate_giving 0/1,022 = **0.00%**; contributions 0/14,829 = **0.00%**
- `cache-other/recollection-lane-3`: corporate_giving 0/1,022 = **0.00%**; contributions 0/14,818 = **0.00%**
- `cache-other/banking-20260910`: corporate_giving 0/67,421 = **0.00%**; contributions 32,581/783,808 = **4.16%**

### 2.2 Refusal on the un-migrated copy

Every un-migrated copy was run first, and every one refused. The refusal is a `RuntimeError` that names `init_schema()`, exit code **1**:

- exit codes observed across the 31 databases: 1

```
raise RuntimeError( RuntimeError: backfill_contributor_street refuses to run -- corporate_giving: missing contributor_street_1, contributor_street_2; contributions: missing contributor_street_1, contributor_street_2. Run init_schema() from mentat/R/schema.R against this database first; it adds the street columns without touching the rows.
```

### 2.3 Migration verdict and what `init_schema()` added

Row counts are compared per table, before vs after `init_schema()`, on the copy. A table that did not exist before and was CREATED empty by `init_schema()` is listed as created, not as a row-count change.

| class | industry / lane | row counts | street cols added | other columns added | tables created |
| --- | --- | :-: | --- | --- | --- |
| report-input-20260910 | community_banks | **MATCH** | corporate_giving(2), contributions(2), bulk_candidates(2) | `api_work_progress`: query_contract; `contributions`: contributor_id; `corporate_giving`: contributor_id | `attribution_claims`, `fec_response_archive`, `fec_response_observations`, `source_record_conflicts` |
| report-input-20260910 | credit_arms | **MATCH** | corporate_giving(2), contributions(2), bulk_candidates(2) | `api_work_progress`: query_contract; `contributions`: contributor_id; `corporate_giving`: contributor_id | `attribution_claims`, `fec_response_archive`, `fec_response_observations`, `source_record_conflicts` |
| report-input-20260910 | credit_union | **MATCH** | corporate_giving(2), contributions(2), bulk_candidates(2) | `api_work_progress`: query_contract; `contributions`: contributor_id; `corporate_giving`: contributor_id | `attribution_claims`, `fec_response_archive`, `fec_response_observations`, `source_record_conflicts` |
| report-input-20260910 | crypto | **MATCH** | corporate_giving(2), contributions(2), bulk_candidates(2) | `api_work_progress`: query_contract; `contributions`: contributor_id; `corporate_giving`: contributor_id | `attribution_claims`, `fec_response_archive`, `fec_response_observations`, `source_record_conflicts` |
| report-input-20260910 | fintech | **MATCH** | corporate_giving(2), contributions(2), bulk_candidates(2) | `api_work_progress`: query_contract; `contributions`: contributor_id; `corporate_giving`: contributor_id | `attribution_claims`, `fec_response_archive`, `fec_response_observations`, `source_record_conflicts` |
| report-input-20260910 | property_casualty_insurance | **MATCH** | corporate_giving(2), contributions(2), bulk_candidates(2) | `api_work_progress`: query_contract; `contributions`: contributor_id; `corporate_giving`: contributor_id | `attribution_claims`, `fec_response_archive`, `fec_response_observations`, `source_record_conflicts` |
| report-input-20260910 | telecom | **MATCH** | corporate_giving(2), contributions(2), bulk_candidates(2) | `api_work_progress`: query_contract; `contributions`: contributor_id; `corporate_giving`: contributor_id | `attribution_claims`, `fec_response_archive`, `fec_response_observations`, `source_record_conflicts` |
| repair-20260908 | community_banks | **MATCH** | corporate_giving(2), contributions(2), bulk_candidates(2) | `api_work_progress`: query_contract; `contributions`: contributor_id, filing_form, receipt_type, line_number_label, back_reference_transaction_id, back_reference_schedule_name; `corporate_giving`: contributor_id, filing_form, receipt_type, receipt_type_full, line_number, line_number_label, memo_code, memoed_subtotal, memo_text, back_reference_transaction_id, back_reference_schedule_name | `attribution_claims`, `fec_response_archive`, `fec_response_observations`, `source_record_conflicts` |
| repair-20260908 | credit_arms | **MATCH** | corporate_giving(2), contributions(2), bulk_candidates(2) | `api_work_progress`: query_contract; `contributions`: contributor_id, filing_form, receipt_type, line_number_label, back_reference_transaction_id, back_reference_schedule_name; `corporate_giving`: contributor_id, filing_form, receipt_type, receipt_type_full, line_number, line_number_label, memo_code, memoed_subtotal, memo_text, back_reference_transaction_id, back_reference_schedule_name | `attribution_claims`, `fec_response_archive`, `fec_response_observations`, `source_record_conflicts` |
| repair-20260908 | credit_union | **MATCH** | corporate_giving(2), contributions(2), bulk_candidates(2) | `api_work_progress`: query_contract; `contributions`: contributor_id, filing_form, receipt_type, line_number_label, back_reference_transaction_id, back_reference_schedule_name; `corporate_giving`: contributor_id, filing_form, receipt_type, receipt_type_full, line_number, line_number_label, memo_code, memoed_subtotal, memo_text, back_reference_transaction_id, back_reference_schedule_name | `attribution_claims`, `fec_response_archive`, `fec_response_observations`, `source_record_conflicts` |
| repair-20260908 | crypto | **MATCH** | corporate_giving(2), contributions(2), bulk_candidates(2) | `api_work_progress`: query_contract; `contributions`: contributor_id, filing_form, receipt_type, line_number_label, back_reference_transaction_id, back_reference_schedule_name; `corporate_giving`: contributor_id, filing_form, receipt_type, receipt_type_full, line_number, line_number_label, memo_code, memoed_subtotal, memo_text, back_reference_transaction_id, back_reference_schedule_name | `attribution_claims`, `fec_response_archive`, `fec_response_observations`, `source_record_conflicts` |
| repair-20260908 | crypto_recollected | **MATCH** | corporate_giving(2), contributions(2), bulk_candidates(2) | `api_work_progress`: query_contract; `contributions`: contributor_id, filing_form, receipt_type, line_number_label, back_reference_transaction_id, back_reference_schedule_name; `corporate_giving`: contributor_id, filing_form, receipt_type, receipt_type_full, line_number, line_number_label, memo_code, memoed_subtotal, memo_text, back_reference_transaction_id, back_reference_schedule_name | `attribution_claims`, `fec_response_archive`, `fec_response_observations`, `source_record_conflicts` |
| repair-20260908 | fintech | **MATCH** | corporate_giving(2), contributions(2), bulk_candidates(2) | `api_work_progress`: query_contract; `contributions`: contributor_id, filing_form, receipt_type, line_number_label, back_reference_transaction_id, back_reference_schedule_name; `corporate_giving`: contributor_id, filing_form, receipt_type, receipt_type_full, line_number, line_number_label, memo_code, memoed_subtotal, memo_text, back_reference_transaction_id, back_reference_schedule_name | `attribution_claims`, `fec_response_archive`, `fec_response_observations`, `source_record_conflicts` |
| repair-20260908 | property_casualty_insurance | **MATCH** | corporate_giving(2), contributions(2), bulk_candidates(2) | `api_work_progress`: query_contract; `contributions`: contributor_id, filing_form, receipt_type, line_number_label, back_reference_transaction_id, back_reference_schedule_name; `corporate_giving`: contributor_id, filing_form, receipt_type, receipt_type_full, line_number, line_number_label, memo_code, memoed_subtotal, memo_text, back_reference_transaction_id, back_reference_schedule_name | `attribution_claims`, `fec_response_archive`, `fec_response_observations`, `source_record_conflicts` |
| repair-20260908 | telecom | **MATCH** | corporate_giving(2), contributions(2), bulk_candidates(2) | `api_work_progress`: query_contract; `contributions`: contributor_id, filing_form, receipt_type, line_number_label, back_reference_transaction_id, back_reference_schedule_name; `corporate_giving`: contributor_id, filing_form, receipt_type, receipt_type_full, line_number, line_number_label, memo_code, memoed_subtotal, memo_text, back_reference_transaction_id, back_reference_schedule_name | `attribution_claims`, `fec_response_archive`, `fec_response_observations`, `source_record_conflicts` |
| run-lane | credit-unions-data | **MATCH** | corporate_giving(2), contributions(2), bulk_candidates(2) | none | none |
| run-lane | lane-01 | **MATCH** | corporate_giving(2), contributions(2), bulk_candidates(2) | none | none |
| run-lane | lane-02 | **MATCH** | corporate_giving(2), contributions(2), bulk_candidates(2) | none | none |
| run-lane | lane-03 | **MATCH** | corporate_giving(2), contributions(2), bulk_candidates(2) | none | none |
| run-lane | lane-04 | **MATCH** | corporate_giving(2), contributions(2), bulk_candidates(2) | none | none |
| run-lane | lane-05 | **MATCH** | corporate_giving(2), contributions(2), bulk_candidates(2) | none | none |
| run-lane | lane-06 | **MATCH** | corporate_giving(2), contributions(2), bulk_candidates(2) | none | none |
| run-lane | lane-07 | **MATCH** | corporate_giving(2), contributions(2), bulk_candidates(2) | none | none |
| run-lane | lane-08 | **MATCH** | corporate_giving(2), contributions(2), bulk_candidates(2) | none | none |
| run-lane | lane-09 | **MATCH** | corporate_giving(2), contributions(2), bulk_candidates(2) | none | none |
| run-lane | lane-10 | **MATCH** | corporate_giving(2), contributions(2), bulk_candidates(2) | none | none |
| cache-other | fairshake-20260908 | **MATCH** | corporate_giving(2), contributions(2), bulk_candidates(2) | `api_work_progress`: query_contract; `contributions`: contributor_id; `corporate_giving`: contributor_id | `attribution_claims`, `fec_response_archive`, `fec_response_observations`, `source_record_conflicts` |
| cache-other | recollection-lane-1 | **MATCH** | corporate_giving(2), contributions(2), bulk_candidates(2) | `api_work_progress`: query_contract; `contributions`: contributor_id, filing_form, receipt_type, line_number_label, back_reference_transaction_id, back_reference_schedule_name; `corporate_giving`: contributor_id, filing_form, receipt_type, receipt_type_full, line_number, line_number_label, memo_code, memoed_subtotal, memo_text, back_reference_transaction_id, back_reference_schedule_name | `attribution_claims`, `fec_response_archive`, `fec_response_observations`, `source_record_conflicts` |
| cache-other | recollection-lane-2 | **MATCH** | corporate_giving(2), contributions(2), bulk_candidates(2) | `api_work_progress`: query_contract; `contributions`: contributor_id, filing_form, receipt_type, line_number_label, back_reference_transaction_id, back_reference_schedule_name; `corporate_giving`: contributor_id, filing_form, receipt_type, receipt_type_full, line_number, line_number_label, memo_code, memoed_subtotal, memo_text, back_reference_transaction_id, back_reference_schedule_name | `attribution_claims`, `fec_response_archive`, `fec_response_observations`, `source_record_conflicts` |
| cache-other | recollection-lane-3 | **MATCH** | corporate_giving(2), contributions(2), bulk_candidates(2) | `api_work_progress`: query_contract; `contributions`: contributor_id, filing_form, receipt_type, line_number_label, back_reference_transaction_id, back_reference_schedule_name; `corporate_giving`: contributor_id, filing_form, receipt_type, receipt_type_full, line_number, line_number_label, memo_code, memoed_subtotal, memo_text, back_reference_transaction_id, back_reference_schedule_name | `attribution_claims`, `fec_response_archive`, `fec_response_observations`, `source_record_conflicts` |
| cache-other | banking-20260910 | **MATCH** | corporate_giving(2), contributions(2), bulk_candidates(2) | `api_work_progress`: query_contract; `contributions`: contributor_id; `corporate_giving`: contributor_id | `attribution_claims`, `fec_response_archive`, `fec_response_observations`, `source_record_conflicts` |

### 2.3b `init_schema()` could not migrate 6 audit fixtures

Six 12 KB reconciliation fixtures under `outputs/mentat-full-audit-2026-09-13/reconciliation/fixtures/` hold a `contributions` / `corporate_giving` pair with a hand-built 7-column shape:

```
sub_id, industry, company, committee_id, contributor_name,
contribution_receipt_date, contribution_receipt_amount
```

`init_schema()` fails on all six with:

```
Error: no such column: two_year_transaction_period
```

Mechanism, read off the source: `mentat/R/schema.R:30` declares `two_year_transaction_period` inside the `CREATE TABLE IF NOT EXISTS contributions` statement, so for a table that already exists the narrow fixture shape survives untouched; `mentat/R/schema.R:297` then builds `CREATE INDEX ... ON contributions (company, two_year_transaction_period)`, which has no such column to index. `init_schema()` runs inside `DBI::dbWithTransaction`, so the whole migration rolls back.

Rollback was verified, not assumed: each copy was re-run through the backfill tool afterwards and still refuses, which means the street columns were never added.

| fixture | migration rc | copy still refuses |
| --- | :-: | :-: |
| `25bfa50c23dd40b49fc592388cda664f-identity` | 1 | yes |
| `25bfa50c23dd40b49fc592388cda664f-scope_expansion` | 1 | yes |
| `6816df6e73e044b0b264996aa7648a92-identity` | 1 | yes |
| `6816df6e73e044b0b264996aa7648a92-scope_expansion` | 1 | yes |
| `accc5969fefd43559ff85c14d21ae1fc-identity` | 1 | yes |
| `accc5969fefd43559ff85c14d21ae1fc-scope_expansion` | 1 | yes |

These are audit reconciliation fixtures, not contribution stores, so nothing in the backfill lane depends on them. Recorded because it is a real limit of `init_schema()`: it cannot migrate a database whose `contributions` table is a reduced fixture shape.

### 2.4 SHA256 of each source, start and end

`start` was taken before the copy; `end` was recomputed after that database finished. Equal end-vs-start is the proof the production file was not modified.

| class | industry / lane | SHA256 (source, start) | end == start |
| --- | --- | --- | :-: |
| report-input-20260910 | community_banks | `923ab7866fab51dc4a4771b3b6e8f1fc14b5bb483c9f2eeecfb6795ddfda6ca2` | yes |
| report-input-20260910 | credit_arms | `03324c79c07a0e9247db0edf30285d191c75172798b207f7ab4dd9ce6fa70aa2` | yes |
| report-input-20260910 | credit_union | `43c0c109c057d5cbca55106a5a68a200df871f6bbfc97feef5499bf22e2055d9` | yes |
| report-input-20260910 | crypto | `0c2dc2e228f5343af960a2cb4898f3a47921d7b33080fa60be161b78fc497dcb` | yes |
| report-input-20260910 | fintech | `d55ce04ced908141888e4c271e66c43b4bc7a75dab41246b13ae7b69a265f90a` | yes |
| report-input-20260910 | property_casualty_insurance | `4defdf40e82a872d3e9de5da8aca1f01dbc4bb3699155f1c7e6e10ac3ea3e165` | yes |
| report-input-20260910 | telecom | `44148eb4f504a8fe723dcb41b7a7b79db7a556d70758ced206b056316d1628cb` | yes |
| repair-20260908 | community_banks | `7a972ba5c7cf6d7427ee757bc93c66c93e9c679e426f35e8dda0cda821ec2b59` | yes |
| repair-20260908 | credit_arms | `172b1c168ab5f10cf051d9e255552dfba8308df545188559daa2b89d8362c6ff` | yes |
| repair-20260908 | credit_union | `f9e956354525acb069cae220eb8d1538c479eea1bf23df1b3154adee8f416686` | yes |
| repair-20260908 | crypto | `897892424d976e1a3a848ddfaf9957f4e9d0bca2c996c584be099736cde81b8f` | yes |
| repair-20260908 | crypto_recollected | `7a1436d68168b25931c0533e0b95db35db79c129571734d8fe671725d0b5b08a` | yes |
| repair-20260908 | fintech | `465a00a14d581e7609e2ff65fcd1a7eccf551947b738582a72eb8311a6f92c4a` | yes |
| repair-20260908 | property_casualty_insurance | `e095c6da35081085ac042ec95d9015abce16072496f932deb81427b04bb96ea0` | yes |
| repair-20260908 | telecom | `5bd16e96a9820cf82d6486a673309b77fbb2604cd7891d42539b8d5763cf2fcc` | yes |
| run-lane | credit-unions-data | `18a032dc046c06e5b5dd908d651ef3f4d9252e165d29c286c100d054ea22a0a8` | yes |
| run-lane | lane-01 | `dbd0e5b1c1e4d834b166f869023e195ca55481e7ef09280d09409f9cc91c326f` | yes |
| run-lane | lane-02 | `120fff6e15d6f2f7aab079637685d94c9817f12e06e3f11bbf03f88651c263b9` | yes |
| run-lane | lane-03 | `7483e448b7b62fe9ef4c55394a00c25dcbed84e6fe398d3e14eeee569a871aa8` | yes |
| run-lane | lane-04 | `33eb0d500c489b3786809f0825f7c6dabd455dde9c0bde5eee579140c359248b` | yes |
| run-lane | lane-05 | `22dabc325dfff31da56cabe3c543ead21394debff838f9b9341723e1eb9d144f` | yes |
| run-lane | lane-06 | `bac2deef48f73f393202cd647045a89fa62d2db2741edf954f135c6639e3a6de` | yes |
| run-lane | lane-07 | `ced0076078f188b337cef337f102894a567fcb356b01b175e1412929a28f5fa3` | yes |
| run-lane | lane-08 | `88024fd3af04903a27a550fff5e15dc824744c97a18ee3fd62a3c909baeb5bb2` | yes |
| run-lane | lane-09 | `4d0faa0957d71aed7a0e640fc98b3deea3a7fd5654b932808fb7312ad3a484ae` | yes |
| run-lane | lane-10 | `45682bd41bd9a9dca2c22fbd1974ca405c1a1557fa9926a000da19e033f0a05e` | yes |
| cache-other | fairshake-20260908 | `4e3e0c7d50e8fd260b094b7545dc824962a41ce13d65e00895dbbc7f01ed93a5` | yes |
| cache-other | recollection-lane-1 | `8f58eb57555c05fdbe5d5c932632157d500d51037a2a82bb63af24103f8e42e8` | yes |
| cache-other | recollection-lane-2 | `86880a4b8bde1cfbd517b8b2b56e86b8e0aa4d15f7203e35b19c2f9e902ce104` | yes |
| cache-other | recollection-lane-3 | `13408ef2aa2a819298e657116ff598fe31cc80ab5602d397abde4f61d973c3d1` | yes |
| cache-other | banking-20260910 | `4abdea581b99cec1674252ee098ab6afca57674bd8e90313e9f4156e88b2d991` | yes |
| outputs | 25bfa50c23dd40b49fc592388cda664f-identity | `7311fad4b70723cd2a2ad2cbbcfe2a235971873380c605afb47fa847752eccf1` | yes |
| outputs | 25bfa50c23dd40b49fc592388cda664f-scope_expansion | `b546a72e5e721afec60fe7a1b8c5afe57796f943e42d81e7ac61763fb02ad1fa` | yes |
| outputs | 6816df6e73e044b0b264996aa7648a92-identity | `7311fad4b70723cd2a2ad2cbbcfe2a235971873380c605afb47fa847752eccf1` | yes |
| outputs | 6816df6e73e044b0b264996aa7648a92-scope_expansion | `48649700f4b1cb381c50cea526112b12a41ae5fa2550b52e93beff9301447ce5` | yes |
| outputs | accc5969fefd43559ff85c14d21ae1fc-identity | `7311fad4b70723cd2a2ad2cbbcfe2a235971873380c605afb47fa847752eccf1` | yes |
| outputs | accc5969fefd43559ff85c14d21ae1fc-scope_expansion | `48649700f4b1cb381c50cea526112b12a41ae5fa2550b52e93beff9301447ce5` | yes |
| state | contribution-analytics-508c57296863 | `ee411388e17e1b45f30b6bf277b1dee9280b2dada324f272fa0462d68eb2f711` | yes |
| state | contribution-analytics-d379128c9470 | `4f7250b1a2ff96e95de9d6ce8f38859b2d0c3b3dd3a64ab2e36ee4c35439682d` | yes |
| state | cross-reference-ledger | `4a3a27b0d14f069b1dcb8d9178bc9ea67c8dbdd158b0875b394358705d09513f` | yes |
| state | cross-reference-ledger | `4490854b79a9a65982279e09f783300e40b2e808c4109006b5266f70bb14fdfa` | yes |

Sources whose SHA256 changed during the run: **0**. The end-of-run pass recomputed all 41 of them independently, including each `-wal` / `-shm` sibling.

Copy fidelity: every copy's SHA256 equalled its source's, for the database and for each `-wal` / `-shm` sibling that existed (41/41 databases).

### 2.5 What the backfill would write (house numbers masked)

Up to three examples per database, re-derived from the same evidence the tool reads. Leading house numbers are replaced with `###`, and PO box numbers are masked the same way.

- `cache-other__banking-20260910`
  - contributions: street_1 = `### WALPOLE LN`, street_2 = `<NULL>`
  - contributions: street_1 = `### WALPOLE LN`, street_2 = `<NULL>`
  - contributions: street_1 = `### WALPOLE LN`, street_2 = `<NULL>`
- `run-lane__lane-01`
  - corporate_giving: street_1 = `### S FIGUEROA ST`, street_2 = `STE 1110`
  - corporate_giving: street_1 = `### S FIGUEROA ST, #1110`, street_2 = `<NULL>`
  - corporate_giving: street_1 = `### WILSHIRE BLVD`, street_2 = `STE 1290`
  - contributions: street_1 = `### CORAL GABLES CIR`, street_2 = `<NULL>`
  - contributions: street_1 = `### CORAL GABLES CIR`, street_2 = `<NULL>`
  - contributions: street_1 = `### NEWPORT AVE.`, street_2 = `<NULL>`
- `run-lane__lane-02`
  - corporate_giving: street_1 = `### CLOISTER LAKE LN`, street_2 = `<NULL>`
  - corporate_giving: street_1 = `### W CLEAR CANYON DR`, street_2 = `<NULL>`
  - corporate_giving: street_1 = `### W CLEAR CANYON DR`, street_2 = `<NULL>`
  - contributions: street_1 = `### ROBELINE PROVENCAL RD`, street_2 = `<NULL>`
  - contributions: street_1 = `### NORTHEAST 67TH STREET`, street_2 = `<NULL>`
  - contributions: street_1 = `### CLYDE WAY`, street_2 = `<NULL>`
- `run-lane__lane-04`
  - contributions: street_1 = `### WINDHAM AVENUE`, street_2 = `<NULL>`
  - contributions: street_1 = `### ALLEN STREET`, street_2 = `<NULL>`
  - contributions: street_1 = `### ALLEN STREET`, street_2 = `<NULL>`
- `run-lane__lane-05`
  - corporate_giving: street_1 = `### COLLINS AVE`, street_2 = `<NULL>`
  - contributions: street_1 = `### WESTERN AVE`, street_2 = `<NULL>`
  - contributions: street_1 = `### W GIDDINGS ST 2`, street_2 = `<NULL>`
  - contributions: street_1 = `### W GIDDINGS ST 2`, street_2 = `<NULL>`
- `run-lane__lane-06`
  - contributions: street_1 = `### STERLING DRIVE`, street_2 = `<NULL>`
  - contributions: street_1 = `### STRATTON PL`, street_2 = `<NULL>`
  - contributions: street_1 = `### W 3975 S 15C`, street_2 = `<NULL>`
- `run-lane__lane-07`
  - corporate_giving: street_1 = `### CYPRESS STREET`, street_2 = `<NULL>`
  - corporate_giving: street_1 = `### CYPRESS STREET`, street_2 = `<NULL>`
  - corporate_giving: street_1 = `### CYPRESS STREET`, street_2 = `<NULL>`
  - contributions: street_1 = `### CALHAY WAY`, street_2 = `<NULL>`
  - contributions: street_1 = `### BURHAM CT`, street_2 = `<NULL>`
  - contributions: street_1 = `### TURQUOISE DR`, street_2 = `<NULL>`
- `run-lane__lane-08`
  - corporate_giving: street_1 = `### SLATE STREET`, street_2 = `<NULL>`
  - corporate_giving: street_1 = `### SLATE STREET`, street_2 = `<NULL>`
  - corporate_giving: street_1 = `### SLATE STREET`, street_2 = `<NULL>`
  - contributions: street_1 = `### E LORAN HEIGHTS DRIVE`, street_2 = `<NULL>`
  - contributions: street_1 = `### S 800 E`, street_2 = `<NULL>`
  - contributions: street_1 = `### S 800 E`, street_2 = `<NULL>`
- `run-lane__lane-10`
  - corporate_giving: street_1 = `PO BOX ###`, street_2 = `<NULL>`
  - corporate_giving: street_1 = `PO BOX ###`, street_2 = `<NULL>`
  - corporate_giving: street_1 = `PO BOX ###`, street_2 = `<NULL>`
  - contributions: street_1 = `### HATHAWAY DRIVE`, street_2 = `<NULL>`
  - contributions: street_1 = `### HATHAWAY DRIVE`, street_2 = `<NULL>`
  - contributions: street_1 = `### LANDPORT WAY`, street_2 = `<NULL>`

## 3. Commands

Run from `C:\Users\pgoff\Mentat\mentat`, with `PYTHONDONTWRITEBYTECODE=1`. `<copy>` is always a path under the session scratchpad, never a production path.

```
# a. refusal check, on the UN-migrated copy
python tools/backfill_contributor_street.py <copy>

# b. migrate the COPY (sources R/paths.R + R/schema.R, then
#    init_schema(connection); never `Rscript -e`)
"C:/Program Files/R/R-4.6.0/bin/Rscript.exe" \
    <scratch>/s2_prod_dryrun/scripts/migrate_copy.R \
    C:/Users/pgoff/Mentat/mentat <copy>

# c. dry run on the migrated copy (no --apply, ever)
python tools/backfill_contributor_street.py <copy> --receipt <json>
```

Total wall time for the 41-database sweep: **861.2 s (14 min 21 s), 2026-09-16T20:23:58Z to 2026-09-16T20:38:24Z**.

Per-database JSON receipts: `<scratch>/s2_prod_dryrun/receipts/<label>.json`.

## 4. What this means

The backfill can fill a row only when the stored FEC evidence still holds that row's `sub_id`. On the databases examined, the evidence splits into four cases.

**Complete (8 databases).** Every candidate row is matched, so a `--apply` run would fill the street columns for all of them with no re-collection: `run-lane/lane-01` (4,139 rows); `run-lane/lane-02` (533 rows); `run-lane/lane-04` (1,054 rows); `run-lane/lane-05` (303 rows); `run-lane/lane-06` (1,781 rows); `run-lane/lane-07` (681 rows); `run-lane/lane-08` (4,806 rows); `run-lane/lane-10` (968 rows).

**Partial (1 database).** Some candidates are matched and the rest are not: the evidence present does not carry every `sub_id` these tables hold: `cache-other/banking-20260910` (32,581 matched, 818,648 unmatched).

**Zero evidence (19 databases).** Measured, not inferred: in each of these the `fec_response_archive` table was ABSENT before migration (`init_schema()` created it empty) and `api_page_checkpoints` held zero rows. The backfill therefore has nothing to read and matched nothing. Filling these rows needs S1's re-collect, since the evidence is not on disk: `report-input-20260910/community_banks` (4,661 candidate rows); `report-input-20260910/credit_arms` (435,683 candidate rows); `report-input-20260910/credit_union` (67,310 candidate rows); `report-input-20260910/crypto` (14,844 candidate rows); `report-input-20260910/fintech` (86,836 candidate rows); `report-input-20260910/property_casualty_insurance` (361,088 candidate rows); `report-input-20260910/telecom` (809,703 candidate rows); `repair-20260908/community_banks` (4,099 candidate rows); `repair-20260908/credit_arms` (428,189 candidate rows); `repair-20260908/credit_union` (468,356 candidate rows); `repair-20260908/crypto` (15,840 candidate rows); `repair-20260908/crypto_recollected` (15,872 candidate rows); `repair-20260908/fintech` (86,806 candidate rows); `repair-20260908/property_casualty_insurance` (366,070 candidate rows); `repair-20260908/telecom` (809,703 candidate rows); `cache-other/fairshake-20260908` (15,872 candidate rows); `cache-other/recollection-lane-1` (15,861 candidate rows); `cache-other/recollection-lane-2` (15,851 candidate rows); `cache-other/recollection-lane-3` (15,840 candidate rows).

**Nothing to fill (3 databases).** Both target tables are empty, so there is no candidate row either way (two of them do hold evidence records): `run-lane/credit-unions-data` (0 evidence records); `run-lane/lane-03` (6,391 evidence records); `run-lane/lane-09` (11,027 evidence records).

No claim is made here about WHY any database holds the evidence it holds; the counts above are the whole finding.

