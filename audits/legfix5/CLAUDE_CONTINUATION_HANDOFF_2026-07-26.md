# Claude continuation handoff: six-year legislation acceptance

Generated: 2026-07-26 America/Chicago / 2026-07-27 UTC

## Mission and non-negotiable policy

Continue the six-year legislation coverage, evidence enrichment, reversible membership-level culling, and staged integration work without depending on an active Codex task.

- Congress.gov Advanced Search is the primary discovery instrument.
- Quorum is only a 44-row recall floor and must never replace Congress.gov discovery.
- Preserve every candidate, query/category membership, exclusion, failure, and restoration provenance. Never silently delete or overwrite evidence.
- Review official title, official summary or explicit summary absence, every available official text version, identifier excerpts, stage/actions, sponsor, original cosponsors, and cosponsors before exclusion.
- Missing or incomplete evidence is always `flagged`, never `junk`.
- Decisions are membership-level `(canonical_key, query_id/category)`. A whole candidate may be globally junk only when every membership is explicitly excluded and no keep, flagged, legacy, or restored edge exists.
- Do not score, sync, promote, publish, or write to the main corpus/mainframe until coverage reconciliation, evidence completeness, culling/reversibility, role attribution, recomputation, regression-currentness, and hash binding all pass.

## Verified checkpoint

### Discovery

- Registry queries: **62/62 complete**.
- Congress.gov result pages: **304**.
- Unique candidates: **18,557**.
- Query/category memberships: **64,004**.
- Reconciliation: exact at the latest verified receipt.
- Quorum primary usage: **none**.

Primary discovery run:

`audits/legfix5/congress_advanced_pages_20260725`

### Existing Congress full-text lane

- The former R/HTTR lane is stopped; do not trust or reuse an old PID.
- Accepted gzip archives physically rehashed: **2,886/2,886 valid**.
- Invalid accepted receipts: **0**.
- Unaccounted dispatches: **0**.
- Malformed batch receipts: **0**.
- Unresolved candidates: **6**.
- Latest status: `PASS_RECEIPT_LEVEL_WITH_UNRESOLVED_FAILURES`.
- The six unresolved attempts were genuine Cloudflare failures (429, then 403 after a headed refresh). Do not repeat that burst blindly.

Run directory:

`audits/legfix5/congress_advanced_pages_20260725/text_relevance_httr_full_stage_20260726`

Catchnet:

`fec/audit_congress_full_text_failure_catchnet.py`

### GovInfo official XML lane

This is the tested fast path for official text versions and does not use a browser, cookies, Cloudflare clearance, Playwright, or retry waits.

- BillStatus source records: **14,854**.
- Planned official GovInfo text-version URLs: **18,440**.
- Explicit no-text-URL keys: **10**, preserved in each run receipt.
- Stable plan SHA-256: `b4f85fcc986e5a4bfd6136ae5ce0c96f1fecda231efa0029a77a3c0f7cefb11b`.
- Final canary: `canary-32-20260727-v3`.
- Canary result: **32/32 accepted, 0 failures, 16 workers, one attempt per URL, 0 retry waits**.
- Collector syntax and focused tests: **13/13 pass** after the canary fixes.
- Full 18,440-version run has **not** been started.

Collector:

`fec/collect_govinfo_bill_xml_versions.py`

Test:

`fec/tests/test_collect_govinfo_bill_xml_versions.py`

Canary receipt:

`audits/legfix5/govinfo_bill_xml_versions/runs/canary-32-20260727-v3/completed.json`

The two earlier canaries are immutable failure evidence and must remain:

- `canary-32-20260727-v1`: 1 accepted / 31 quarantined.
- `canary-32-20260727-v2`: 28 accepted / 4 quarantined.

The v3 correction narrowly accepts exact official Congress DTD variants for bills, resolutions, and amendment documents, plus exact 116th-119th worded Congress identities. It still rejects near-match DTDs, entities, HTML/challenge bodies, malformed XML, wrong measures, wrong Congresses, and wrong originating-bill references.

### Frozen pre-work production/ranking baseline

An immutable baseline exists at:

`audits/legfix5/production_baseline/baseline_manifest.json`

- Frozen at: `2026-07-26T01:13:27.652513+00:00`.
- Manifest SHA-256: `2c3ff4103c2a6e6a35030ae590fc8edd417241ac3b059a1eb4a04e8c97542e10`.
- Files: **33**.
- Physical copy rehash: **33/33 match**, 0 missing or corrupt.

The older downstream report says `DRIFT/ABSENT` because live source files changed after freezing; that does not mean the frozen copies were lost. Treat live-source drift as an integration blocker and the frozen 33-file copy set as intact comparison evidence.

### Data-loss conclusion

No data loss or corruption was found in the preserved discovery corpus, the 2,886 accepted R archives, the three GovInfo canary runs, or the 33-file frozen baseline. Failed/quarantined attempts remain preserved. No main-corpus or ranking promotion occurred.

## What was reverted before this handoff

Only the final, untested partial edit that attempted to add live GovInfo event/progress instrumentation and validator-failure body binding was reverted. The tested v3 validator correction and its tests were retained. After the revert, collector syntax passed and all 13 collector tests passed again.

No collector, acceptance service, or paid model process was active at handoff time. The old Glassbox R matrix may still be open as a read-only viewer; it is not evidence that a collector is running.

## Standalone components already added

### Acceptance service

Files:

- `fec/run_legislation_acceptance_service.py`
- `fec/start_legislation_acceptance_service.ps1`
- `fec/tests/test_run_legislation_acceptance_service.py`

Verified focused tests: **6/6 pass**. It has a single-writer lock, stale-owner diagnosis, hash-bound stage receipts, resumability, no retry sleeps, and explicit plan/canary/full guards. Current terminal boundary is only `EVIDENCE_READY_CULLING_PREPARATION`; it does not yet run culling, Claude review, final integration, or promotion.

### Claude ambiguity-review lane

Files:

- `fec/run_legislation_claude_ambiguity_review.py`
- `fec/tests/test_run_legislation_claude_ambiguity_review.py`

Capabilities:

- Standalone from Codex.
- Anthropic API or `claude` CLI transport.
- Flagged/ambiguous memberships only.
- Strict evidence-bound prompt and JSON schema.
- Missing evidence never calls Claude and stays flagged.
- Unsafe junk proposals are downgraded to flagged.
- Immutable prompts, dispatches, call-start markers, responses, and terminal receipts.
- Crash-safe paid-call handling and a hard aggregate cost cap.
- Six-worker default.
- No corpus/ranking/junk-ledger/production writes.

Focused direct smoke checks reported **12/12 pass**. The local machine has no `pytest`, so the pytest file was not executed by pytest. A two-line dynamic-import registration fix was applied after those smoke checks; rerun syntax/direct tests before paid use.

Provider availability at handoff:

- `ANTHROPIC_API_KEY`: **not present** in the environment.
- `claude` CLI: **not installed/on PATH**.
- Claude Desktop is open, but it is not a standalone CLI/API transport for this runner.

Therefore, do not claim automatic Claude continuation until one provider transport is configured. Never print or persist the API key. Use a small explicit dollar cap and send only the deterministic flagged queue.

### Reversible deterministic culling engine — do not run yet

Files:

- `fec/run_reversible_legislation_culling.py`
- `fec/tests/test_run_reversible_legislation_culling.py`

Reported smoke state: **9/11 pass**. It must be patched and retested before any real run:

1. Enforce exact equality between evidence `membership_query_ids` and the discovered membership universe; mismatch must flag every affected row as `membership_universe_mismatch`.
2. Fix immutable generation rerun behavior so an identical rerun reuses/verifies the existing manifest rather than colliding because of transient `appended_count` invocation metadata.
3. The local environment lacks pytest; use a dependency-free test harness or install pytest intentionally.
4. A tamper test should accept the actual fail-closed reasons `content hash drift`, `noncanonical CRLF`, or `schema or canonical JSON drift`.

Do not run this engine on the real corpus until all focused tests pass.

### Staged integration gate

Files:

- `fec/build_legislation_staged_integration_gate.py`
- `fec/tests/test_build_legislation_staged_integration_gate.py`

Reported validation: **7/7 focused tests** plus **6/6 existing culling-contract compatibility tests**. It rehashes six required gates and outputs only a plan/receipt under `audits/`. Even a complete pass yields `READY_FOR_EXPLICIT_INTEGRATION_REVIEW`; promotion remains prohibited.

## Required continuation order

1. Reinspect git/workspace state, process chain, newest receipts, and Glassbox viewers. Do not inherit PIDs.
2. Re-run the GovInfo collector syntax and 13 focused tests.
3. Preserve the v3 canary receipt and start a new immutable full run ID only after confirming no other collector is active.
4. Add or attach a standalone progress/event watcher so the user sees overhead progress plus live commands, inputs, outputs, accepted records, and quarantines. Do not expose secrets.
5. Complete the full GovInfo run and reconcile every dispatch to exactly one accepted or quarantined terminal receipt. Do not retry in-process; any retry is a new explicit immutable run.
6. Reconcile the 14,854 BillStatus records and 10 missing-URL exceptions against all 18,557 discovery candidates. Any candidate without complete official evidence remains flagged.
7. Fix and fully test the reversible deterministic culling engine. Run deterministic culling first over all 64,004 memberships.
8. Create the user-visible flagged review workbook/CSV and append-only junk/restoration ledgers. Nothing is deleted.
9. Configure Claude transport only after verifying credentials privately. Send only unresolved flagged memberships, with a hard dollar cap and immutable call receipts.
10. Run the staged integration gate, isolated recomputation, rank-drift comparison against the 33-file baseline, and current full regression.
11. Stop before any score/sync/promotion/mainframe write unless every strengthened gate is current, hash-bound, and passing and the user explicitly authorizes integration.

## Safe commands

From `C:\Users\pgoff\OneDrive\Desktop\Melange Systems`:

```powershell
& 'C:\Users\pgoff\AppData\Local\Programs\Python\Python312\python.exe' -m py_compile fec\collect_govinfo_bill_xml_versions.py
& 'C:\Users\pgoff\AppData\Local\Programs\Python\Python312\python.exe' fec\tests\test_collect_govinfo_bill_xml_versions.py
```

Before a full run, verify exact processes:

```powershell
Get-CimInstance Win32_Process |
  Where-Object { $_.CommandLine -match 'collect_govinfo_bill_xml_versions|run_legislation_acceptance_service|harvest_congress_text_httr' } |
  Select-Object ProcessId,ParentProcessId,CreationDate,Name,CommandLine
```

Full GovInfo command template; replace the run ID with a new unique immutable value and attach progress observation first:

```powershell
& 'C:\Users\pgoff\AppData\Local\Programs\Python\Python312\python.exe' `
  fec\collect_govinfo_bill_xml_versions.py `
  --input audits\legfix5\billstatus_bulk_enrichment\fetch_runs\c7ca822fd5951478a33a814d228b71ffdf69745e6d823001fefaba620282c435\parsed\sha256 `
  --out audits\legfix5\govinfo_bill_xml_versions `
  --run-id full-18440-UNIQUE `
  --full --workers 16 --timeout-seconds 45
```

The collector has exactly one request attempt per selected URL and zero retry waits. Do not reuse an existing run ID.

Inspect standalone CLI contracts before use:

```powershell
& 'C:\Users\pgoff\AppData\Local\Programs\Python\Python312\python.exe' fec\run_legislation_acceptance_service.py --help
& 'C:\Users\pgoff\AppData\Local\Programs\Python\Python312\python.exe' fec\run_legislation_claude_ambiguity_review.py --help
& 'C:\Users\pgoff\AppData\Local\Programs\Python\Python312\python.exe' fec\build_legislation_staged_integration_gate.py --help
```

## User-supplied floors and references

- Efficient reference scraper: `C:\Users\pgoff\OneDrive\Desktop\Draft Systems\congress_member_scraper.R`
- Quorum recall floor: `C:\Users\pgoff\Downloads\search-results-generated-by-quorum (55).xlsx`
- Initial prior handoff: `audits/legfix4/PROJECT_STATE_AND_HANDOFF_2026-07-25.md`

Treat the Quorum workbook as a bare minimum recall check only. Congress.gov Advanced Search remains the discovery authority.
