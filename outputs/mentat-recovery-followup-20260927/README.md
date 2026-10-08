# Recovery follow-up — 2026-09-27

This follow-up closes the recovery gaps identified in the earlier pilot verification. GPT-6 Sol implemented and exercised the backend recovery changes; the primary agent reviewed the transaction boundaries and independently checked production-schema preservation, hot-journal recovery, and the live chart layout.

## Changes

- A durable merge intent names the run, source fingerprint, exact shard ownership and hashes, and the prepared receipt. The merge writes its completion marker in the same SQLite transaction as the data. If the process dies after commit, `--resume` validates that evidence and reconstructs the terminal receipt without collecting or merging the completed work again.
- Source validation and terminal receipt publication hold the source database write lease. Recovery clears stale running, queued, and writer indicators while retaining historical request counts.
- Large merges still prepare batches privately, but publish through one transaction in the actual target database. They no longer replace the target file. A writer that changes the target during preparation is detected, and its committed data is preserved.
- Resume lets SQLite recover an interrupted rollback journal and checkpoint committed WAL before comparing source fingerprints. This covers large transactions that spilled modified pages before a crash.
- Chart Studio titles, scope text, totals, and footers keep their natural text height when the map needs more space. The chart canvas handles scrolling.

## Independent verification

Sol's final affected regression run passed **114 Python tests in 11 suites**, including **9 recovery tests**, plus 4 parameterized subcases and **all 3 R test scripts**. The process tests cover termination before and after commit, rollback and WAL journals, competing writers at final publication, source-write locking during receipt publication, stale worker state, and repeat resume without duplicate rows. The R scripts cover lane locking, fanout, date-window union, missing/overlapping windows, checkpoint resume, and retained counts. Detailed logs are in `sol/`.

`real-schema-verification.json` and `verify_real_schema.py` compare direct and batched merges using disposable copies of the actual pilot database. Both outputs exactly match an independently constructed expected database containing the original rows plus three synthetic employee and three synthetic corporate records. All production schema tables and baseline data are preserved; SQLite quick checks pass. The live pilot database hash is unchanged.

`hot-journal-before-fix.json` records the reproduced bug: killing a transaction after dirty-page spill left the raw file fingerprint different until a SQLite read recovered the journal. `hot-journal-verification.json` records the passing fix, which restores the exact baseline bytes before fingerprinting. `verify_hot_journal.py` reproduces the process interruption on a disposable database.

`ui-verification.json` records live browser measurements at 1707×932, 1440×900, 1280×720, and 390×844. Titles, subtitles, and verified totals use their natural line height or wrap normally. No page-wide horizontal overflow was observed. The pilot remained $51,152,975.30 across 102 observations and 28 reported identities. `ui-detector.json` contains no layout findings.

The dedicated read-only preview was restarted after backend edits and checked again in the browser. Its title, scope, and totals measured 34, 20, and 16 pixels high, respectively, matching their line heights. The stale-code notice was absent. Preview: http://127.0.0.1:8816/?industry=Rust%20FEC%20Verified%202023-2024#chart-studio

`final-verification.json` records the current code hashes, test totals, and unchanged pilot files. `sha256.json` fingerprints this follow-up evidence. `git diff --check` passed; Git reported only existing LF/CRLF conversion notices. R emitted Windows locale startup warnings, and all three scripts completed with PASS.

## Scope

These changes are in the current workspace and apply to runs using this code. The active legacy collectors and other user servers were left running. Automatic postcommit recovery requires the durable intent and marker created by the new implementation; it does not fabricate missing evidence for older interrupted runs. If the source, shards, or intent have actually changed, recovery refuses to certify the old result.

The checks cover local Windows processes and SQLite storage. They do not certify network-filesystem locking. The earlier evidence folders remain historical records; this report supersedes their listed postcommit-recovery and batched-replacement limitations.
