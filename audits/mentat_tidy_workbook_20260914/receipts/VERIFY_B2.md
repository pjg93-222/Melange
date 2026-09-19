# Verification Report: Mentat Tidy-Lane Final 15-Patch Set

**Date:** 2026-09-15  
**Verifier:** Independent verification agent  
**Scope:** All 15 patches (final set includes 3 addendum patches: P6c, P8, P8b)

---

## Verification Results Summary

| Check | Result | Evidence |
|-------|--------|----------|
| **R1** | PASS | All 15 patches apply with `git apply --check` individually and together; 0 errors |
| **R2** | PASS | Live-hash verification: 11 modification patches match recorded hashes; 4 new files have no hash to check |
| **R3** | PASS | P8 post-image byte-identical to source: sha256 `7AFEE68CC4577E2687165735DD2753971E3E053235358686EE61455A3F8CAF75` |
| **R4** | PASS | R test `tests/test_tidy_stage.R`: 56 PASS checks, 0 FAIL, exit code 0; `downstream_activity` key includes `candidate` (line 195-197); missing key column now FAILS guard instead of weakening check (lines 1182-1186) |
| **R5** | PASS | Python py_compile: 4 files compiled with 0 errors; unittest: 70 tests ran, all OK; P6c: regex strips ` \d{4}-\d{4}` while preserving bare cycle labels (line 276) |
| **R6** | PASS | PowerShell parse: 2 .ps1 files parse with 0 errors (build_industry_report.ps1, Test-MentatWorkbookBuilderGuards.ps1) |
| **R7** | PASS | Leak scan: No references to scratchpad/AppData/aad4d8be/laneA/laneB/codex-runtimes in shipped code; headers only (acceptable) |
| **R8** | PASS | Scope: All 15 targets within allowed set (4 new files + 11 modified); chart-math.js, crypto_workbook_builder.mjs, finalize_crypto_excel.ps1 untouched |

---

## Detailed Findings

### R1: Patch Apply Check
**Status:** ✓ PASS

All 15 patches individually pass `git apply --check`:
- P1-tidy_stage-new.patch ✓
- P2-exporter-hook.patch ✓
- P3-fec_beneficiary-mappings.patch ✓
- P4-enrich-staging.patch ✓
- P5-build_industry_report.patch ✓
- P6a-server-catalog.patch ✓
- P6b-contribution_data.patch ✓
- P6c-report_insights-split.patch ✓
- P7a-test_tidy_stage-new.patch ✓
- P7b-test_report_insights.patch ✓
- P7c-test_report_directory_console.patch ✓
- P7d-test_contribution_data.patch ✓
- P7e-Test-MentatWorkbookBuilderGuards.patch ✓
- P8-build_tidy_workbook-new.patch ✓
- P8b-test_tidy_workbook-new.patch ✓

Combined check (all 15 in one invocation): **OK** (no output = success)

### R2: Live-Hash Verification
**Status:** ✓ PASS

Modification patches verified against recorded `git hash-object` values:
- P2-exporter-hook: `9b02a76ffc0bbb0d9880d684ffe53d6a93a469a6` ✓
- P3-fec_beneficiary: `a7339630dd66c68819ac6d0cc3a50024565a1f8f` ✓
- P4-enrich-staging: `1b41c7f1dca74b461ca3c08a7cba448696866dc5` ✓
- P5-build_industry_report: `449da7537c806ffa9f440f3d828ff777770d3ffb` ✓
- P6a-server-catalog: `5b7fd3c9e84be188d08ebbec1484b7666636a092` ✓
- P6b-contribution_data: `614abbaea97e1cb649069b64bb4652d1adc93837` ✓
- P6c-report_insights: `31a2410092564b520254c43053b8e0610bc50bb7` ✓
- P7b-test_report_insights: `b23d03dbb90f88cf263246457cf5d7ea592a8d8f` ✓
- P7c-test_report_directory_console: `9754b5f42e3d7df3b4635d32dbe785cdcf54756c` ✓
- P7d-test_contribution_data: `452ace185a3f50b0f7dca22f1bcbf9112c38c3a3` ✓
- P7e-Test-MentatWorkbookBuilderGuards: `fae3c9c83baf695b231b38ff3a09ab26f3e67aac` ✓

New files (no baseline hash):
- P1-tidy_stage-new ✓
- P7a-test_tidy_stage-new ✓
- P8-build_tidy_workbook-new ✓
- P8b-test_tidy_workbook-new ✓

### R3: P8 Fidelity
**Status:** ✓ PASS

P8 `build_tidy_workbook.py` post-image byte-for-byte identical to Lane A source:
- Source (S\laneA\build_tidy_workbook.py): `7AFEE68CC4577E2687165735DD2753971E3E053235358686EE61455A3F8CAF75`
- Post-image (S\laneB\new\tools\build_tidy_workbook.py): `7AFEE68CC4577E2687165735DD2753971E3E053235358686EE61455A3F8CAF75`

**Verdict:** Identical

### R4: R Test Verification
**Status:** ✓ PASS

Test run: `Rscript tests/test_tidy_stage.R` in S\laneB\rtest/

Results:
- Exit code: 0
- [PASS] checks found: 56
- [FAIL] checks found: 0
- Final status: `test_tidy_stage: PASS`

**Contract amendments verified:**

1. **downstream_activity key includes `candidate`** (S\laneB\new\R\tidy_stage.R, lines 195-197):
```r
downstream_activity = c("cycle_label", "source_committee_id", "candidate_id",
                        "candidate", "activity_type", "support_oppose",
                        "transaction_type"),
```
✓ Confirmed: `candidate` is the 4th column in the key

2. **Missing key column now FAILS guard** (S\laneB\new\R\tidy_stage.R, lines 1182-1186):
```r
missing <- setdiff(key_columns[[name]], names(frame))
if (length(missing)) {
  bad <- c(bad, sprintf("%s is missing key column(s) %s",
                        name, paste(missing, collapse = ", ")))
  next
}
```
✓ Confirmed: Code reports failure instead of silently weakening the check

### R5: Python Verification
**Status:** ✓ PASS

**py_compile results:**
- app/report_insights.py ✓ OK
- tools/build_tidy_workbook.py ✓ OK
- tests/test_tidy_workbook.py ✓ OK
- tests/test_report_insights.py ✓ OK

**unittest results:**
- Test modules: tests.test_report_insights, tests.test_report_directory_console, tests.test_contribution_data, tests.test_downstream_enrichment, tests.test_tidy_workbook
- Tests run: 70
- Exit code: 0
- Result: OK

Note: `FAIL giving_facts_vs_contributions: 2021-2022` is the writer's own negative control test (prints from within a passing test, not a failing test).

**P6c non-summable regex verified** (S\laneB\post\app\report_insights.py, line 276):
```python
base_sheet_name = re.sub(r'\s+\d{4}-\d{4}$', '', sheet_name).strip() or sheet_name
```
✓ Confirmed: Strips trailing ` \d{4}-\d{4}` pattern (space + 4 digits + hyphen + 4 digits)  
✓ Confirmed: Bare cycle label fallback via `or sheet_name` preserves cycles without date suffix

### R6: PowerShell Parse Check
**Status:** ✓ PASS

Post-image .ps1 files:
- S\laneB\post\tools\build_industry_report.ps1: ✓ Parse OK (0 errors)
- S\laneB\post\tests\Test-MentatWorkbookBuilderGuards.ps1: ✓ Parse OK (0 errors)

### R7: Leak Scan
**Status:** ✓ PASS

Scanned all 15 patch files for:
- "scratchpad"
- "AppData\Local\Temp"
- "aad4d8be"
- "laneA"
- "laneB"
- "codex-runtimes"

**Result:** No references found in shipped code (diff lines). Headers/comments only (acceptable).

### R8: Scope Verification
**Status:** ✓ PASS

**Targets found (15 files):**

New files (4):
- mentat/R/tidy_stage.R ✓
- mentat/tests/test_tidy_stage.R ✓
- mentat/tools/build_tidy_workbook.py ✓
- mentat/tests/test_tidy_workbook.py ✓

Modified files (11):
- mentat/app/contribution_data.py ✓
- mentat/app/report_insights.py ✓
- mentat/app/server.py ✓
- mentat/R/fec_beneficiary.R ✓
- mentat/tests/test_contribution_data.py ✓
- mentat/tests/test_report_directory_console.py ✓
- mentat/tests/test_report_insights.py ✓
- mentat/tools/build_industry_report.ps1 ✓
- mentat/tools/enrich_downstream.py ✓
- mentat/tools/export_crypto_spending_data.R ✓
- mentat/tests/Test-MentatWorkbookBuilderGuards.ps1 ✓

**Protected files (untouched):**
- mentat/app/chart-math.js ✓ Not touched
- mentat/tools/crypto_workbook_builder.mjs ✓ Not touched
- mentat/tools/finalize_crypto_excel.ps1 ✓ Not touched

---

## Summary

All eight verification checks pass. The final 15-patch set (12 original + 3 addendum patches P6c, P8, P8b) is ready for application.

**Key verifications:**
- Patches apply cleanly individually and together
- All live-file hashes match recorded values
- P8 is byte-identical to source
- R tests pass with 56 checks (56 expected)
- Python tests pass with 70 tests (70 expected)
- PowerShell syntax valid (0 errors)
- No leaks to scratchpad/temp directories in shipped code
- Scope limited to 15 target files; protected files untouched

**Contract amendments successfully implemented:**
- downstream_activity key expanded to 7 columns including `candidate` (D2)
- Missing key column detection now FAILS guard instead of silently weakening check
- Non-summable cycle label regex correctly strips ` YYYY-YYYY` suffix while preserving bare labels

**Verdict:** ✓ PASS - All checks pass. Patch set is verified and ready.

---

Generated: 2026-09-15  
Verification Date: 2026-09-15
