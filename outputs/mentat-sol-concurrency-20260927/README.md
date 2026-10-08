# Sol concurrency verification — 2026-09-27

Workspace: `C:\Users\pgoff\Mentat\mentat`, Git HEAD `533b4033e8e28d6f70fe1a4a2b20e14ed7731fb8`. The `pilot-*` logs document an earlier worktree discrepancy only; every `verified-*` log below is from this current workspace and disposable fixtures. No production database, active 2020 Telecom run, or user server was touched. Work remained uncommitted in the existing dirty tree.

Commands from `C:\Users\pgoff\Mentat\mentat` used Python `C:\Users\pgoff\AppData\Local\Programs\Python\Python312\python.exe` and R `C:\Program Files\R\R-4.6.0\bin\Rscript.exe`:

```text
python -m unittest discover -s tests -p test_worker_sharing.py -v
python -m unittest discover -s tests -p test_api_request_pool.py -v
python -m unittest discover -s tests -p test_api_company_cycle_fanout.py -v
python -m unittest discover -s tests -p test_resilient_orchestrator.py -v
python -m unittest discover -s tests -p test_lane_writer_lock.py -v
python -m unittest discover -s tests -p test_merge_company_shards.py -v
python -m unittest discover -s tests -p test_merge_owner_fence.py -v
python -m unittest discover -s tests -p test_verify_fec_date_coverage.py -v
python -m unittest discover -s tests -p test_cycle_snapshot_lineage.py -v
python -m unittest discover -s tests -p test_snapshot_registry.py -v
python -m unittest discover -s tests -p test_source_memo.py -v
python -m unittest discover -s tests -p test_contribution_data.py -v
Rscript tests/test_fec_api_fanout.R
Rscript tests/test_request_windows.R
Rscript tests/test_sqlite_lane_locking.R
git diff --check -- <all modified tracked files in scoped review>
```

All commands exited 0. The Python suites ran **136 tests** across 12 files, including 17 merge tests (2 subtests), 4 merge ownership regressions, 9 worker sharing tests, 10 request pool tests, 1 process-level R lane writer test, 5 dated FEC coverage regressions, and cycle/registry/memo/contribution suites. All three R scripts passed. Logs are `verified-*.log`; changed-file and log SHA-256 hashes are in `sha256.json`. `git diff --check` passed (only line-ending conversion notices).

The adversarial execution uses synthetic keys, disposable SQLite databases, and loopback HTTP. Six pool workers serve one R lane concurrently without key collision or response-order drift. A forced R exit after committing page 0 leaves that checkpoint durable; restart fetches only page 1. A competing live supervisor is rejected before dispatch; its death releases the OS lock, after which a new token can take ownership. A live R writer blocks a replacement and preserves the old receipt; a delayed old-token child is refused even if it starts after the replacement probe. Invocation nonces prevent that child and the replacement from sharing assignment, status, receipt, and log paths. R closes its data and budget connections before releasing its writer lease.

The merge child now owns a cross-process sidecar lock for the entire source-DB merge. Supervisor entry probes this lock before verifying or snapshotting source; a child starting after that probe is fenced by the new supervisor token. The child checks its token before direct-merge commit or staged replacement. A staged merge also rechecks the expected target SHA under a fresh SQLite write lease; a concurrent target edit remains intact and fails the merge. Four direct regressions exercise held merge lock, late old-token child, mid-transaction ownership switch, and source edit during staging.

Limits: local process/SQLite behavior and mocked FEC responses were tested; no live collection or full production run was repeated here. A wholly external source writer that ignores the merge sidecar lock could still write in the narrow interval between the final batched SHA check and Windows `os.replace`. A crash after a successful source merge but before the supervisor writes its final receipt still requires operator review because resume detects the changed source fingerprint. Remote/network filesystem lock behavior was not validated.
