# Backend recovery audit receipt — 2026-09-28

Scope: disposable fixtures and loopback HTTP service only. No production database, active collector, or user server was modified. This is a follow-up to `outputs/mentat-recovery-followup-20260927/sol`.

## Concrete defects reproduced and fixed

1. A Python exception after the shared request pool started released the supervisor lock but left the pool HTTP and control-watcher threads alive in the same process. `test_supervisor_error_cleanup.py` injected a dispatch exception and observed the thread leak before the lifecycle cleanup change. The supervisor now stops and closes both before releasing its lock, and clears active telemetry on an interrupted active invocation.
2. A managed R process could write a succeeded task receipt, fail its final postflight, and exit nonzero. `test_nonzero_lane_exit_cannot_certify_successful_task_receipt` exercised a real child process and saw the false success before the fix. `execute_lane` now fails those tasks when the child exit is nonzero. Resume also refuses to skip tasks from raw R receipts whose `quick_check` failed or from Python-normalized receipts with a recorded nonzero exit. A raw R receipt with `quick_check=ok` remains resumable when the supervisor died before recording the child exit.
3. An early rejected restart (existing manifest without `--resume`) changed a prior successful status and worker telemetry to `interrupted`. `test_rejected_restart_preserves_prior_terminal_telemetry` reproduced this before the fix. Error cleanup now changes telemetry only after this invocation has begun publishing worker state.

## Verification

- Python: `C:\Users\pgoff\AppData\Local\Programs\Python\Python312\python.exe -m pytest -q mentat/tests/test_supervisor_error_cleanup.py mentat/tests/test_worker_sharing.py mentat/tests/test_api_company_cycle_fanout.py mentat/tests/test_merge_crash_recovery.py mentat/tests/test_merge_company_shards.py mentat/tests/test_merge_owner_fence.py mentat/tests/test_api_request_pool.py mentat/tests/test_lane_writer_lock.py mentat/tests/test_resilient_orchestrator.py mentat/tests/test_validate_industry_coverage.py` — **89 passed, 9 subtests passed**. See `python-tests.log`.
- R: `Rscript.exe` separately on `mentat/tests/test_fec_api_fanout.R`, `mentat/tests/test_request_windows.R`, and `mentat/tests/test_sqlite_lane_locking.R` — **all three PASS**. See `r-tests.log`. Startup emitted only Windows locale warnings.
- Scoped `git diff --check` exited 0. File and log SHA-256 values are in `hashes.json`.

The failure injection used a synthetic local child process and loopback request-pool server. This audit does not claim a fresh production FEC run or universal protection against filesystem failure. Earlier commit/rollback and live schema exercises remain documented in the prior follow-up evidence directory.
