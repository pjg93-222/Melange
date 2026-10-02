# Files excluded from git

This file lists what was deliberately left out when the live Mentat tree (`C:\Users\pgoff\Mentat\mentat`) was migrated into this repository on 2026-10-02. Everything listed here stays local in `C:\Users\pgoff\Mentat`. GitHub rejects any file over 100 MB, and this migration used a stricter 50 MB per-file cutoff. The cache directories and state ledgers are either regenerable by re-running the pipeline or are local-only working state, so they are not needed to rebuild the code in this repository.

Files were excluded with robocopy `/MAX:52428800` (50 MiB), so anything larger than 50 MiB was not copied. Hashes were not computed for the large files.

## A. Files larger than 50 MB (excluding .cache contents)

There are 68 such files, totalling 29,946.8 MB. Paths are relative to `mentat\`.

| Relative path | Size (MB) | LastWriteTime |
|---|---:|---|
| `state\cross-reference\20260913T074303-bca0ac2b9cd3\ledger.sqlite` | 3,502.9 | 2026-09-13 03:51 |
| `state\cross-reference\20260918T183722-d8f0fb287912\ledger.sqlite` | 3,502.0 | 2026-09-18 14:55 |
| `state\cross-reference\20260918T030844-6098810b1ae7\ledger.sqlite` | 3,501.3 | 2026-09-17 23:19 |
| `state\contribution-analytics\37ad98cef0954462457843331422d9521d0440e85d705016ece83ba078c69784.sqlite` | 688.6 | 2026-09-19 13:25 |
| `state\contribution-analytics\719285b6881b7aa460672d2516767e6e7552340eb02fb16bc8115f7957e73743.sqlite` | 675.1 | 2026-09-27 21:08 |
| `state\contribution-analytics\acd68859aec91909ab027b93d234ef85a511b64e87840e81294d6cc58d0cff6a.sqlite` | 675.1 | 2026-09-27 03:53 |
| `state\contribution-analytics\e0aea06d98bb8297e770db5c66f1b0b37450aef0796976eaf956035669f1178c.sqlite` | 675.1 | 2026-09-26 03:12 |
| `state\contribution-analytics\ab5d961b6d9cead4af4c83c9413205ecbd535831888ba94316a65e95bc68c7f5.sqlite` | 675.1 | 2026-09-26 01:46 |
| `state\contribution-analytics\ecebcf95f0386a230f33e9e627a02f199110c241955abb612d77d2f339b9e9f9.sqlite` | 675.1 | 2026-09-20 23:10 |
| `state\contribution-analytics\bb2b2452b4fc14c827c6632ae8b1ecc47444ce835d6e44d6a7d885997424b7d0.sqlite` | 675.1 | 2026-09-21 14:47 |
| `state\contribution-analytics\ade44c087e9db61b373686c378905a9ee48f1a24c7d8f03bafb0012a0d668fdd.sqlite` | 675.1 | 2026-09-20 13:42 |
| `state\contribution-analytics\3434390f30f992f391aade133ed603d816d883fb4f09ff36dc7fbc3f063f857b.sqlite` | 674.7 | 2026-09-16 22:19 |
| `state\contribution-analytics\6f7acaee8a6e8c5ac34e5d572094a078c85c68c46b1f990c022f3021d2dbc08c.sqlite` | 645.3 | 2026-09-22 11:50 |
| `state\contribution-analytics\17606d9d03538a5d2f67657d90880e8e75327e838a971eb9cb19ebb631c063b7.sqlite` | 641.4 | 2026-09-13 22:01 |
| `state\accepted-report-sources\telecom\2022-2024-2026\efa98bdff76241e689f360d32ecf7bdc.db` | 591.8 | 2026-09-10 16:14 |
| `state\cross-reference\evidence.sqlite` | 515.3 | 2026-09-27 00:27 |
| `state\contribution-query-cache\views\7e969cf496b5e2024dd936c165895ff58ca349924b764213f029f64dc279ef81.sqlite` | 430.4 | 2026-09-30 18:56 |
| `state\accepted-report-sources\telecom\2022-2024-2026\778185604b1e45be8bb7c6b76611e59d.db` | 421.1 | 2026-09-10 16:09 |
| `state\accepted-report-sources\telecom\2022-2024-2026\efa98bdff76241e689f360d32ecf7bdc.dollar-changes.jsonl` | 391.2 | 2026-09-10 16:14 |
| `state\contribution-analytics\ba38420fc8c51460f192df48c78542fe66fd650e7dc8eeb8910a1aa5a2c41234.sqlite` | 382.7 | 2026-09-22 18:47 |
| `state\contribution-analytics\276f2473dae60171e7c541f1d28f8304cdec8fb3957528214c2d5c31f4335cf5.sqlite` | 382.7 | 2026-09-28 10:05 |
| `state\contribution-analytics\9c515889ad4b97841be7042b9b7676f9da2dce7b13254174ed0ab41f81f1a06f.sqlite` | 380.9 | 2026-09-13 21:46 |
| `state\cross-reference\20260917T190836-4d409860e341\ledger.sqlite` | 322.1 | 2026-09-17 15:14 |
| `state\contribution-query-cache\records\02d0e9a571a1895228a709d090d95447ab827bffdaf4f9eb3d276f119ec23c4a.sqlite` | 318.7 | 2026-09-25 02:34 |
| `state\cross-reference\20260921T052649-b0d18e0fef61\ledger.sqlite` | 307.9 | 2026-09-21 01:29 |
| `state\cross-reference\20260921T055153-885792788fa7\ledger.sqlite` | 307.9 | 2026-09-21 01:54 |
| `state\cross-reference\20260921T054358-37fc6057a617\ledger.sqlite` | 307.9 | 2026-09-21 01:46 |
| `state\cross-reference\20260911T010412-03169a41d58f\ledger.sqlite` | 306.7 | 2026-09-10 21:05 |
| `state\cross-reference\20260911T010614-28bf69639f78\ledger.sqlite` | 306.7 | 2026-09-10 21:07 |
| `state\cross-reference\20260911T010907-d7fdb039c080\ledger.sqlite` | 306.7 | 2026-09-10 21:10 |
| `state\contribution-analytics\b9dabba3d54e6550f75fb0a8e4e5e8774ea6d7745d98e20585c5f498569ada34.sqlite` | 288.4 | 2026-09-22 18:54 |
| `state\contribution-analytics\5cd59a37059a7b097d9c707ea762e9ced6322b58417a8aef659a48d46f42b667.sqlite` | 288.4 | 2026-09-28 10:18 |
| `state\contribution-analytics\ad52afbe7d60daa39d338c55dbda83529efdc20a585e8793bb52772d768cebdb.sqlite` | 287.0 | 2026-09-13 21:50 |
| `state\accepted-report-sources\telecom\2022-2024-2026\778185604b1e45be8bb7c6b76611e59d.dollar-changes.jsonl` | 269.1 | 2026-09-10 16:09 |
| `state\contribution-query-cache\views\3704306eaa7f1782476bf59b15052dcf958b3e1fcb3643cede52a71a03822163.sqlite` | 252.3 | 2026-09-29 23:09 |
| `state\insights-history\2702e84965c37716996dccafb1f0b7c786349302fe0c6edc86c9b0e93388dc35.sqlite` | 251.3 | 2026-10-01 10:29 |
| `state\cross-reference\20260911T005725-56ca38280348\ledger.sqlite` | 250.6 | 2026-09-10 20:57 |
| `state\accepted-report-sources\credit_arms\2022-2024-2026\6b1d060685a64581be01862bef0fb005.db` | 249.9 | 2026-09-10 16:04 |
| `state\accepted-report-sources\property_casualty_insurance\2022-2024-2026\6319a49a75ee4adaafc1dae1a6fd01ba.db` | 200.2 | 2026-09-10 16:06 |
| `state\contribution-query-cache\insights-views\8d613970cb5a1210440414c96b158c01afcbc915e58e477a7061fadf2070a431.sqlite` | 200.2 | 2026-09-30 18:51 |
| `state\accepted-report-sources\banking\2022-2024-2026\1ee5154933cd4b21828f4b9d37d16ef9.source-changes.jsonl` | 198.0 | 2026-09-12 17:23 |
| `state\accepted-report-sources\telecom\2022-2024-2026\efa98bdff76241e689f360d32ecf7bdc.source-changes.jsonl` | 188.5 | 2026-09-10 16:12 |
| `state\accepted-report-sources\telecom\2022-2024-2026\778185604b1e45be8bb7c6b76611e59d.source-changes.jsonl` | 188.5 | 2026-09-10 16:07 |
| `state\contribution-query-cache\views\b2db434fcdadfddf9240041cf636bdcffab8f0dae1b01d2f934a1e7d522b12d5.sqlite` | 188.0 | 2026-09-29 23:09 |
| `state\accepted-report-sources\banking\2022-2024-2026\1ee5154933cd4b21828f4b9d37d16ef9.db` | 184.7 | 2026-09-12 17:23 |
| `state\cross-reference\20260913T062936-059b0fec447f.tar.gz` | 182.2 | 2026-09-13 03:42 |
| `state\cross-reference\20260913T061220-3355f05ade29.tar.gz` | 182.2 | 2026-09-13 03:24 |
| `state\insights-history\7fe3b28fb3e47e13c2c84c7f70eb9e0c2a3cf77f9eccffc5b72b45ddac0be5c8.sqlite` | 182.0 | 2026-09-25 00:48 |
| `state\cross-reference\20260913T054905-dc11ad68c0c8.tar.gz` | 181.8 | 2026-09-13 03:00 |
| `state\cross-reference\20260912T204736-ed3b2a351279\review.csv` | 179.8 | 2026-09-12 17:06 |
| `state\accepted-report-sources\credit_arms\2022-2024-2026\6b1d060685a64581be01862bef0fb005.dollar-changes.jsonl` | 169.1 | 2026-09-10 16:04 |
| `state\insights-history\d3e9c93f2ffba81070c77739f47cba573f6919f3b211e7fb2f7e787df6121759.sqlite` | 149.6 | 2026-10-01 09:57 |
| `state\accepted-report-sources\property_casualty_insurance\2022-2024-2026\6319a49a75ee4adaafc1dae1a6fd01ba.dollar-changes.jsonl` | 128.5 | 2026-09-10 16:06 |
| `state\contribution-query-cache\insights-views\88599dd9fddcf6a003a6be3c1976b2a416b19c96a0da95529b1ea5b0b49e17e8.sqlite` | 127.3 | 2026-09-30 18:57 |
| `inputs\fec_beneficiary\pas222\itpas2.txt` | 124.8 | 2026-07-19 17:23 |
| `inputs\fec_beneficiary\pas224\itpas2.txt` | 117.0 | 2026-03-08 22:46 |
| `state\accepted-report-sources\credit_arms\2022-2024-2026\6b1d060685a64581be01862bef0fb005.source-changes.jsonl` | 101.8 | 2026-09-10 16:03 |
| `state\insights-history\5b4b21ebdc3fa0eb323a1c950d3c5ef509ee26cf2c55e35cd9eca0e607cb8aa5.sqlite` | 100.2 | 2026-10-01 09:57 |
| `state\contribution-query-cache\insights-views\d8f838de5d21154bd29ad25becc1527036d2465cae2e34529f1fc6e81ed5225e.sqlite` | 86.9 | 2026-09-30 19:02 |
| `state\accepted-report-sources\property_casualty_insurance\2022-2024-2026\6319a49a75ee4adaafc1dae1a6fd01ba.source-changes.jsonl` | 83.9 | 2026-09-10 16:05 |
| `state\cross-reference\20260927T042628-10f5615df7a8\ledger.sqlite` | 78.9 | 2026-09-27 00:27 |
| `state\cross-reference\20260927T013921-ff432e440975\ledger.sqlite` | 76.9 | 2026-09-26 21:40 |
| `state\contribution-analytics\2f9fa3df526b0f27a753943ed615240adf931be93f3223838752b517824ceb65.sqlite` | 65.1 | 2026-09-22 18:48 |
| `state\contribution-analytics\ca279177f678ae3c9ffbb2c7f37a296fa38770658f633893c5891f342610680b.sqlite` | 64.4 | 2026-09-13 21:47 |
| `state\contribution-analytics\88e3f70252e75c3ebcbefab2096f39687b0f4874420f97f9b63f83e1e4d85bae.sqlite` | 54.3 | 2026-09-21 10:39 |
| `state\contribution-analytics\2573fdc05d25f8a91c3875dd47d3a2d8201f5a8cdbf3497b87b30ddf45d0f3d7.sqlite` | 54.2 | 2026-09-28 09:49 |
| `state\contribution-analytics\639738a4f13af62232b285a6d327d38dd32fe1253a1b20e4e7f9c4f6ae6f9490.sqlite` | 54.2 | 2026-09-27 13:36 |
| `state\contribution-analytics\ce0ffeca180a3ec7c347a1e7a3ab311388e3474b6ddf7aa848f45cae9f8d83df.sqlite` | 54.0 | 2026-09-16 22:21 |

## B. Excluded directories

| Directory | File count | Total size (MB) |
|---|---:|---:|
| `.cache` | 23,972 | 50,231.3 |
| `.Rproj.user` | 25 | 0.1 |
| `.pytest_cache` | 5 | 0.0 |
| `test-results` | 1 | 0.0 |

Also skipped by name wherever they occur: `__pycache__`, `node_modules`, `.git` directories, and files matching `*.pyc` or `.Rhistory`.
