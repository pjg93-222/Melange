# Sol merge recovery follow-up — 2026-09-27

Workspace: `C:\Users\pgoff\Mentat\mentat`, Git HEAD `533b4033e8e28d6f70fe1a4a2b20e14ed7731fb8`. All tests used disposable SQLite databases and synthetic process/HTTP fixtures. The active collector, production source databases, and user servers were untouched. Changes remain uncommitted in the shared dirty worktree.

The source merge now writes a run-specific commit marker into the **same SQLite target transaction** as merged rows. That marker binds a durable pre-merge intent (source-before SHA, exact shard paths/hashes/companies, manifest run ID, and prepared terminal receipt) to a typed, order-independent logical hash of all material target schema and table rows. The ledger alone is excluded from its own hash. On resume, the supervisor first settles hot rollback journals and checkpoints committed WAL, then holds the source write lease while checking the marker, source content, manifest/shards/tasks, and publishing a recovered success receipt. If the marker is absent, the pre-merge source fingerprint still governs ordinary checkpoint resume. If source contents changed after the merge, recovery refuses.

For more shards than SQLite's attachment limit, the child still prepares consecutive batches in a private staged copy. It now attaches that completed copy and publishes its rows under **one target `BEGIN IMMEDIATE` transaction**. A full logical digest must match the staged result before commit. This removes the prior hash-check-to-`os.replace` gap: an external SQLite writer is serialized by the target write lease and either releases unchanged state for a successful merge or leaves a changed source that the merge rejects. No target DB file replacement occurs.

Test commands from `C:\Users\pgoff\Mentat\mentat` used Python `C:\Users\pgoff\AppData\Local\Programs\Python\Python312\python.exe` and R `C:\Program Files\R\R-4.6.0\bin\Rscript.exe`:

```text
python -m unittest discover -s tests -p test_worker_sharing.py -v
python -m unittest discover -s tests -p test_api_request_pool.py -v
python -m unittest discover -s tests -p test_api_company_cycle_fanout.py -v
python -m unittest discover -s tests -p test_resilient_orchestrator.py -v
python -m unittest discover -s tests -p test_lane_writer_lock.py -v
python -m unittest discover -s tests -p test_merge_company_shards.py -v
python -m unittest discover -s tests -p test_merge_owner_fence.py -v
python -m unittest discover -s tests -p test_merge_crash_recovery.py -v
python -m unittest discover -s tests -p test_validate_industry_coverage.py -v
python -m unittest discover -s tests -p test_collection_coverage.py -v
python -m unittest discover -s tests -p test_query_coverage.py -v
Rscript tests/test_fec_api_fanout.R
Rscript tests/test_request_windows.R
Rscript tests/test_sqlite_lane_locking.R
python -m py_compile tools/api_company_cycle_fanout.py tools/merge_company_shards.py tests/test_merge_crash_recovery.py
git diff --check -- mentat/tools/api_company_cycle_fanout.py mentat/tools/merge_company_shards.py mentat/tests/test_worker_sharing.py
```

All commands exited 0. The final logs record **114 Python tests across 11 suites** (plus four subtests reported by the merge/recovery harnesses) and **three passing R scripts**. `git diff --check` produced only Git line-ending notices. The `*.log` files contain exact stdout/stderr; `sha256.json` hashes scoped source/test files, logs, and this receipt.

The nine new recovery tests include: actual process kill after commit before supervisor receipt; kill while both rows and marker are still uncommitted; unchanged-source rollback and changed-source refusal; WAL-mode recovery; a killed cache-spilled DELETE-journal transaction; uncheckpointed shard WAL refusal; an external writer committing during final staged publication; another writer blocked during recovered receipt publication; and typed duplicate/NULL/schema digest stability. The worker-sharing suite also deletes a completed receipt after a whole-company handoff, resumes, and proves no second dispatch or duplicate ingestion. The recovered receipt passes `validate_fanout_receipt` and terminal status/workers telemetry reports zero active work while preserving historical counters.

Independent root verification used disposable copies of the real pilot schema/data and compared direct, batched, and independently constructed expected databases; every baseline table count was preserved, all three outputs had equal logical digests, and the live source hash stayed unchanged. That evidence is under `outputs/mentat-recovery-followup-20260927/real-schema-verification.json`. Root's independent hot-journal reproduction is under the same directory.

Safety boundary: a later independent source edit causes recovery or subsequent resume to refuse rather than silently certify the old receipt. SQLite transaction/lease behavior was tested on this local Windows filesystem; no universal guarantee for network filesystems or external tools that bypass SQLite is claimed. An orphan process holding a live write lease must finish or be stopped before resume proceeds.
