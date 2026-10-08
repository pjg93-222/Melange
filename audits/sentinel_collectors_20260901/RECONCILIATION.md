# RECONCILIATION — staged candidate feed vs active production feed

Read-only over `MAIN\data\stance\press_refresh_tone.csv`,
`MAIN\data\stance\press_refresh_fulltext.jsonl`, `MAIN\data\press\official_mentions.jsonl`
and the staged candidate under `<STAGING>\data\`.

Per-run rows come from the builder's OWN `build()` function, called once per accepted run via
`_accepted_intake_receipts()` (script: `staging\reconcile.py`), not from a reimplementation.

## Key definitions (quoted from `fec/collect/build_press_engine_feed.py`)

| stream | key | source |
|---|---|---|
| tone | `turn_key(row)` = `(canonical_url(url, keep_fragment=False), bioguide.strip().upper())` | line 165-167 |
| fulltext | `(canonical_url(url, keep_fragment=False), bioguide.strip().upper())` | lines 423-424 |
| mentions | `(canonical_url(article_url, keep_fragment=False), mentioned_bioguide.strip().upper())` | lines 427-428 |

`canonical_url` is `press_stream.canonical_url` (imported at line 25); with
`keep_fragment=False` the member fragment is dropped, so one article page contributes one key
per bioguide.

## Accepted runs, in the builder's own order

Ordered by each run dir's `press_network_retry_receipt.json` `completed_at`
(`ordered.sort(key=lambda item: (item[0], item[1]))`, line 374):

| # | run | completed_at | intake receipt used |
|---|---|---|---|
| 1 | press_refresh_20260828 | 2026-08-28T12:19:00+00:00 | archived `press_refresh_20260828.json` |
| 2 | press_refresh_20260830 | 2026-08-31 05:04:45 UTC | archived `press_refresh_20260830.json` |
| 3 | press_refresh_20260831 | 2026-09-01 02:16:54 UTC | archived `press_refresh_20260831.json` |
| 4 | press_refresh_20260901 | 2026-09-01 09:26:13 UTC | archived `press_refresh_20260901.json` |

All four resolved to the ARCHIVED immutable receipt rather than the rolling `--intake-receipt`,
confirming the `if prior: continue  # prefer the immutable archived path` branch (line 359-360).

## tone — `data/stance/press_refresh_tone.csv`

| quantity | value |
|---|---|
| rows from press_refresh_20260828 | 255 |
| rows from press_refresh_20260830 | 280 |
| rows from press_refresh_20260831 | 281 |
| rows from press_refresh_20260901 | 100 |
| **per-run total (before dedup)** | **916** |
| **deduplicated union across accepted runs** | **294** |
| **candidate rows (staged output)** | **294** |
| **active production rows (MAIN)** | **255** |
| union == candidate | **True** |
| **active − candidate** | **0** |
| **candidate − active** | **39** |
| **exact collisions resolved to the earliest run** | **622** |

Collision attribution (winner ← loser = count):

| winner (kept) | loser (discarded) | count |
|---|---|---|
| press_refresh_20260828 | press_refresh_20260830 | 248 |
| press_refresh_20260828 | press_refresh_20260831 | 248 |
| press_refresh_20260828 | press_refresh_20260901 | 64 |
| press_refresh_20260830 | press_refresh_20260831 | 29 |
| press_refresh_20260830 | press_refresh_20260901 | 29 |
| press_refresh_20260831 | press_refresh_20260901 | 4 |

916 − 622 = 294. ✔

## fulltext — `data/stance/press_refresh_fulltext.jsonl`

Identical to tone at every level, because `build()` emits one fulltext row per scored row that
clears the ≥20-word host-body test (line 257) and no run lost a row to that test.

| quantity | value |
|---|---|
| rows from press_refresh_20260828 | 255 |
| rows from press_refresh_20260830 | 280 |
| rows from press_refresh_20260831 | 281 |
| rows from press_refresh_20260901 | 100 |
| **per-run total (before dedup)** | **916** |
| **deduplicated union across accepted runs** | **294** |
| **candidate rows (staged output)** | **294** |
| **active production rows (MAIN)** | **255** |
| union == candidate | **True** |
| **active − candidate** | **0** |
| **candidate − active** | **39** |
| **exact collisions resolved to the earliest run** | **622** |

Collision attribution: identical to the tone table above (248 / 248 / 64 / 29 / 29 / 4).

## official mentions — `data/press/official_mentions.jsonl`

| quantity | value |
|---|---|
| rows from press_refresh_20260828 | 19561 |
| rows from press_refresh_20260830 | 20858 |
| rows from press_refresh_20260831 | 20851 |
| rows from press_refresh_20260901 | 2317 |
| **per-run total (before dedup)** | **63587** |
| **deduplicated union across accepted runs** | **22243** |
| **candidate rows (staged output)** | **22243** |
| **active production rows (MAIN)** | **19561** |
| union == candidate | **True** |
| **active − candidate** | **0** |
| **candidate − active** | **2682** |
| **exact collisions resolved to the earliest run** | **41344** |

Collision attribution (winner ← loser = count):

| winner (kept) | loser (discarded) | count |
|---|---|---|
| press_refresh_20260828 | press_refresh_20260830 | 18669 |
| press_refresh_20260828 | press_refresh_20260831 | 18745 |
| press_refresh_20260828 | press_refresh_20260901 | 1 |
| press_refresh_20260830 | press_refresh_20260831 | 1958 |
| press_refresh_20260830 | press_refresh_20260901 | 1834 |
| press_refresh_20260831 | press_refresh_20260901 | 137 |

63587 − 41344 = 22243. ✔

## active − candidate

**Empty for all three streams.** No example keys to list. Every previously accepted row survives
the cumulative rebuild.

## Stronger check: content identity, not just key survival

A key can survive a rebuild while its payload changes (a flipped stance, a rescored intensity, a
different host body). `staging\content_identity.py` compares the FULL row payload for every key
present in both feeds:

| stream | shared keys | byte-identical rows | differing rows |
|---|---|---|---|
| tone | 255 | **255** | **0** |
| fulltext | 255 | **255** | **0** |
| mentions | 19561 | **19561** | **0** |

Including `source_run`, which stays `press_refresh_20260828` on all 255/255/19561 preserved rows.
The candidate is a strict row-level superset of the active feed: nothing is rewritten, only added.

## What the 39 / 39 / 2682 additions are

They are the union contributions of runs 20260830, 20260831 and 20260901 that 20260828 did not
already carry:

- tone/fulltext: 280 − 248 = 32 new from 20260830; 281 − 248 − 29 = 4 new from 20260831;
  100 − 64 − 29 − 4 = 3 new from 20260901. 32 + 4 + 3 = **39**. ✔
- mentions: 20858 − 18669 = 2189 new from 20260830; 20851 − 18745 − 1958 = 148 new from 20260831;
  2317 − 1 − 1834 − 137 = 345 new from 20260901. 2189 + 148 + 345 = **2682**. ✔
