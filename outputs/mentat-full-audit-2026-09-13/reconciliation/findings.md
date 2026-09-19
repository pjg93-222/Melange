# Reconciliation and publication audit

Audit of current on-disk Mentat code, 2026-09-13. This pass did not edit production source, collections, accepted baselines, or reports. Reproductions create synthetic SQLite databases beneath this audit directory. No FEC request or workbook export was made.

## Confirmed findings

### R1 — P2: Final payload verification omits financial identity fields

Location: `mentat/tools/report_source_guard.py:207-211`, with the incomplete persisted analysis field list at lines 230-235.

The source snapshot records committee ID, contributor name and receipt date, but `check_payload` only compares source ID, amount and cycle. A payload with the same source ID/amount/cycle can point to a different committee, donor and date and still pass both `check_payload` and `accept`. Those three fields also do not enter the before/after analysis ledger, so the changed payload can report **zero changed decisions**.

Verified reproduction: accept a $100 receipt for `PERSON, ONE`, committee `C00000001`, dated `2024-01-01`; prepare a second build against the unchanged source; set payload committee to `C99999999`, contributor to `DIFFERENT, DONOR`, and date to `2024-12-31`. The check and acceptance both return `verified`, `changed_decisions=0`, `delta_cents=0`.

Impact: a payload join/classification regression can misattribute receipts while the final publication safeguard reports no change. This is a demonstrated missing control, not evidence that the current production workbooks contain this exact corruption. Compare all source financial identity fields at the payload boundary, and retain relevant before/after identity in the ledger.

### R2 — P2: Expanding report cycles bypasses accepted-source loss protection

Location: `mentat/tools/report_source_guard.py:105-115`; corresponding runner behavior at `mentat/tools/run_cross_reference.py:38-43`.

When no exact-scope pointer exists, the publication guard only adopts an accepted snapshot whose cycles are a superset of the requested cycles. The cross-reference runner likewise checks only the exact scope and the hard-coded 2022/2024/2026 scope. Neither combines accepted baselines for overlapping narrower scopes. Thus a first all-cycle report ignores a previously accepted single-cycle report.

Verified reproduction: accept a 2024 source containing $100, then replace that source with a 2026-only $25 receipt and prepare 2022/2024/2026. The guard returns `source_verified` with `added=1, missing=0, previous=null`; the runner finds no baseline; final guard acceptance succeeds. The missing accepted $100 never enters the source-change ledger.

Impact: switching from cycle reports to an all-cycle report can silently accept source loss. Current inspected accepted pointers are all full-cycle scopes, so this pass did not establish existing production loss from this path. Resolve applicable baseline protection per overlapping cycle, and track all baseline pointer tokens used.

### R3 — P2: Coalescing same-ID observations erases explicit memo conflicts

Location: `mentat/tools/run_cross_reference.py:140,153-157`; exclusion then occurs at `mentat/tools/cross_reference_engine.py:403-416`.

`present()` treats the explicit empty memo flag as missing. When one stored observation of a FEC ID has `memo_code=''` and another has `memo_code='X'`, the coalescer fills in X and excludes the blank value from conflict detection. This differs from `cross_reference_store.py:285-294`, which deliberately treats explicit blank memo fields as conflicting evidence.

Verified reproduction: a $100 parent and a $100 child with an explicit parent transaction reference; the child has two stored observations differing only by source table and blank versus X memo code. Coalescing records no source conflict; the engine excludes the child's $100 as a memo duplicate with `review_queue=[]` and `status='excluded_with_evidence'`.

Impact: contradictory memo evidence can silently remove dollars in the provisional original-giving view instead of retaining an unresolved decision. Preserve explicit blank memo values during same-ID conflict checks; missing/null metadata can remain separately recoverable.

Live scope check: all 32 same-ID overlap groups in the current Banking ledger were examined; none had the specific blank-versus-X conflict reproduced here.

## Reproduction artifacts

- `reproduce_guards.py` runs all three probes using real production functions with synthetic inputs.
- `reproduction-results.json` contains observed output and the fixture directory.
- Replay with `C:/Users/pgoff/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe` and the script path. Each run uses a new fixture directory.

## Coverage and limits

Reviewed `AGENTS.md`, `METHODOLOGY.md`, relevant README sections; the cross-reference engine, evidence store, runner, source guard, payload projection/chunk reader, workbook builder and publication script; and relevant regression cases. The parent audit owns the complete Python/R/PowerShell/JavaScript regression results.

The documented distinction between included recipient receipts and unique original giving is valid scope, not a defect by itself. Complete filing/route enumeration, independent accuracy measurement, dated treasury/PAC affiliations, legacy signed-percentage edge cases and legacy Stats grouping are explicitly unresolved in `METHODOLOGY.md`. A successful hash, integrity or arithmetic check does not certify those claims.

`inspect_live_ledger.py` separately checked the latest production cross-reference snapshot (`20260913T025223-09b3c7578492`, Banking) in read-only mode. Its durable results are in `live-ledger-check.json`:

- Report SHA-256 matches the current pointer; the full 3,604,254,720-byte ledger SHA-256 matches the report.
- SQLite `quick_check` returned `ok`; the report, ledger and pointer remained unchanged during inspection.
- 849,431 physical source observations, 849,399 distinct source IDs and decisions, 83,780 accounting changes, 333 links, and 11,128 coverage tasks agree with the report.
- All ten independently recomputed count/amount checks passed, including $133,516,227.27 baseline plus -$65,442,042.93 change = $68,074,184.34 provisional original giving.
- The report explicitly identifies 132,890 unresolved source records and $87,793,849.64 of gross unresolved exposure, unproven collection coverage, no accepted baseline for Banking, and zero supported unique dollars. These are limitations/exposures, not measured errors or additional amounts to add to the provisional total.
