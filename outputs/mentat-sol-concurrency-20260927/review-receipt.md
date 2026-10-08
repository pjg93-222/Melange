# Cycle snapshot and dated FEC coverage review

Reviewed `app/report_identity.py`, `app/contribution_data.py`, `app/snapshot_registry.py`, `app/source_memo.py`, `app/server.py`, `tools/publish_snapshot_lineage.py`, `tools/verify_fec_date_coverage.py`, and `tests/test_cycle_snapshot_lineage.py` in the current workspace. The parent agent handled live UI and live FEC API verification; this Sol review used the code, disposable fixtures, and mocked FEC responses. It did not touch the pilot source DB or make another API request.

Findings and fixes:

* A published lineage manifest could be reused for a different workbook because existing-manifest ownership comparison omitted the workbook path and SHA. `publish_snapshot_lineage.py` now compares both identity fields in preflight and race handling. `contribution_data.py` also verifies workbook identity before admitting a cycle snapshot; an edited workbook is unavailable instead of silently displaying under a stale manifest. A regression mutates the workbook after publication and proves rejection.
* Dated FEC coverage formerly accepted approximate pagination counts, which could certify incomplete rows as complete. `verify_fec_date_coverage.py` now requires `is_count_exact=True`, a nonnegative integer count stable across pages, and a valid cursor. It rejects zero eligible query contracts and sends initial queries in batches no larger than 128. Five mocked tests cover empty contracts, approximate and drifting counts, exact two-page reconciliation with unchanged source hash, and 129-query batching.
* Merge publication and source DB ownership needed child-process fencing after supervisor death. See `README.md` and `verified-merge-owner.log` for the source merge safety change and four direct regressions.

The registry, memo, contribution loader, and cycle snapshot suites passed: 19 + 9 + 27 + 7 tests, respectively. No cross-cycle contamination or memo mismatch was observed under those tests; the selected calendar cycle is checked against manifest, workbook, and dated DB rows. Parent's live UI verification covers actual route rendering separately.

Coverage claim boundary: the Sol helper tests prove exact-count rejection and fixture reconciliation, not independent live FEC completeness. The parent reported two live dated responses with exact counts 95 and 7 matching all 102 pilot records; that live receipt belongs to the parent integration evidence. These verified dates cover configured FEC search contracts and literal aliases, not all national contributions or identity attribution beyond those contracts.
