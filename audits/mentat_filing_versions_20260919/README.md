# Filing versions: what the unresolved-version rule costs, and the index nobody had built

2026-09-19, lane mentat-uncommitted-reconcile (worktree mentat-uncommitted-reconcile-4089f1). Every
measurement read the active FEC source (`mentat/.cache/repair-20260908-inputs`) through hard links and
scratch copies; the real files' sizes and modification times before and after are in
`V3_MEASURE_REPORT.md` section 5.

## 1. What was found

- **No VERSION 3 transfer index had ever been built.** `R/fec_transfer_graph.R` has required index
  VERSION 3 since it was rewritten on 2026-09-10 (committed `a63fabefd`), but the three indexes published
  under the active source were VERSION 2 from 2026-09-08. Every report build therefore took the
  `stale_transfer_index` branch: no transfer edges, every funded committee marked uncertain, and the
  Conditional Non-opposition, Conditional Opposition and Conditional Estimate columns 0.00 in the workbook,
  the console and the tidy store. Direct attribution was unaffected. The quality checks that fail are
  severity `warn` and no export guard covers transfers, so nothing stopped publication. Nothing rebuilds
  a stale index on its own, and `tools/refresh_fec_sources.py` has no production caller.
- **What the rule costs on real data.** OTH: 4.41% / 0.62% / 0.54% of current cash edge dollars are
  blocked (2022 / 2024 / 2026: $108.9M / $33.0M / $10.5M), and 83% / 56% / 70% of that is clean edges of
  a committee blacklisted for a handful of ambiguous rows. PAS2: $7,631,886 across 702 rows left the
  counted committee-to-candidate total, 0.086% of $8.88B.
- **Why.** `committee|report_type|transaction_id` is not an identity. Filers reuse a line label as the
  transaction id (`SE.5` on every Schedule E row of every filing), so different transactions collide and
  are all withheld as "competing versions". 827 of 2022's 1,130 unresolved OTH groups sit inside a single
  filing, where no filing header can ever help, and all fifteen of the largest PAS2 groups span several
  candidate ids. Fetching more headers cannot fix a key collision: settling the "family" would keep one row
  and silently drop the other real transactions.
- **The receipt-evidence gate no longer blocks a report run.** At HEAD it refuses 0 rows for Crypto and 0
  for Credit Union on the hydrated databases; `7d364883e` changed it, and the code before that commit
  refuses 65 and 1 on the same rows. The tidy packet's note that a real orchestrator run is blocked is
  superseded.

## 2. What was done

Built and published the VERSION 3 index for the active source, offline, with the 25 preserved filing
headers (2026-09-19 00:02 to 00:09 local; log in `out/v3_index_build.log`):

    python tools/fec_transfer_graph.py --directory mentat/.cache/repair-20260908-inputs/fec_beneficiary \
      --cycles 2022 2024 2026 --filing-header-directory mentat/state/cross-reference/filing-headers

| cycle | source rows | cash rows | current rows | unresolved groups | unresolved rows | edges | blacklisted committees | seconds |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2022 | 5,364,543 | 1,600,421 | 1,596,263 | 1,130 | 4,158 | 171,780 | 44 | 153.5 |
| 2024 | 18,667,435 | 1,405,634 | 1,404,863 | 366 | 774 | 185,605 | 47 | 175.8 |
| 2026 | 9,898,430 | 261,142 | 260,832 | 155 | 311 | 149,712 | 28 | 53.7 |

The three `itoth.txt` files are byte- and mtime-identical before and after, no `.pending` file remains,
and the full-file counts equal the cash-block counts in `V3_MEASURE_REPORT.md` section 2.4. The replaced
VERSION 2 and 3 info files (counts and source hashes) are kept under `mentat/.cache/transfer-index-backups-20260919/`, and full copies in the session scratchpad; nothing at HEAD can read a
VERSION 2 index, so they are a record, not a rollback. The next report build carries real Conditional
estimates again, except through the committees the committed rule still blacklists. No workbook was
rebuilt and no database was touched: rebuilding is Paul's.

## 3. The rule change

The rule itself is an accounting decision. It was applied as `12a880dc9` on 2026-09-19 with the default the ruling record proposes (count the latest
filed version under an `unverified_version` flag), and the VERSION 4 index was rebuilt and published
(`out/v4_index_build.log`). `RULING_REQUEST.md` is that record: what was wrong, the rule, the measured
effect, the one judgement call (worth about $182,000 across both files) and the one constant that flips it.
`MEASUREMENT.md` carries the numbers and `filing_version_identity.patch` is the change as cut. Taking it
back is one `git revert` and an index rebuild.

## 4. Contents

- `V3_MEASURE_REPORT.md`: census of who builds and reads the index, the kit, the OTH and PAS2
  measurements, the gate check, and the before/after record.
- `kit/`: the scripts that produced it. `measure_transfer_v3.py` refuses an `--itoth` inside the checkout,
  because the indexer writes its cache beside the file it is given.
- `out/`: every result file and log, including the index build log.
