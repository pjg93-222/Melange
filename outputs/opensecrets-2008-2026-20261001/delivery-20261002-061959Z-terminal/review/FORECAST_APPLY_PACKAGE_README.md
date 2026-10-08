# Forecast completion package

The scratch implementation and handoff audit are complete. This 33-file package integrates those fixes into the existing code layout. It does not publish the candidate or change the active model pointer. The candidate remains **HOLD**. The final disposable-copy proof passed all 19 checks. The package remains unapplied.

The current record is [REVIEW_AND_COMPLETION_2026-10-01.txt](../../REVIEW_AND_COMPLETION_2026-10-01.txt). See [the manifest](apply_forecast_completion_manifest.json) for the exact targets and hashes, and `diffs/` for changes to existing files. Original phase copies remain in `../base/`; current-live preimages are separately pinned in `../package_baseline/`. The integration dependency review is `../APPLY_PACKAGE_INTEGRATION_REVIEW.txt`. The package integrates source capability and test fixtures; reproducing the frozen-input national refit remains the scratch workflow under `../input/national` and `../impl/refit/work/cx`. Production input registry pins are not repointed to scratch paths.

Changes include the executable phase/drift/inflation/conditioning chain, genuine national variants, strict complete-grid selection, explicit BLEND dependence qualifications, signed-net-giving/refund wording, response-derived dollar-basis notes, contract guards and the corresponding checks. Seven national variants and all owner acceptance thresholds remain frozen.

The candidate is `../out/candidate/giving-models-v2.candidate.json`, version `refit-20261002-377f7324-e99d3756300f`, SHA256 `41b190f8c3ec1ed018eff8108dee1205251978daae131c78a15526a50cf6aa7c`. Its actual build timestamp is `2026-10-02T00:15:34Z`; `built_on` is October 1 in New York, consistent with the consumer's date-only cutoff. It is included as a test fixture, not installed as the active model.

G2 passes executed R/Python parity and G8 passes 297 arithmetic comparisons against frozen anchors. All four Senate non-degradation cells still fail G6. The copula dependence validation also remains HOLD. Arithmetic, contract validity and package integration do not establish statistical readiness or current-workbook freshness. The broader historical R test run remains recorded as failed; successful targeted checks do not relabel it.

## Review without writing

From `C:/melange-data/forecast-redesign-20261001-review/forecast-completion`:

```powershell
python package/apply_forecast_completion.py --dry-run
```

The current-live dry run has passed and changes no target, backup or receipt. Any changed/missing preimage or conflicting new file makes the real apply refuse before target writes. The real apply requires the owner's explicit instruction under the handoff's apply rule. This package has not been applied to production.

## Apply and rollback mechanics

After owner authorization, running the same command without `--dry-run` applies exactly the manifest targets. Verified backups and a durable `recovery.json` journal precede target writes; per-file replacement is atomic, and each result is checked by hash. A repeated apply is a no-op. Applying while another process edits these targets is unsupported; the checks are not an operating-system atomic compare-and-swap.

Defaults are the Mentat checkout, `apply_forecast_completion_backup/` and `apply_forecast_completion_receipts/` beside this script. Successful apply prints the exact apply receipt path. Preserve the script, verified backups and receipts together.

```powershell
python package/apply_forecast_completion.py --rollback --receipt '<exact apply receipt path>'
```

Rollback verifies backup hashes, restores existing preimages and removes files created by that apply. A file edited after apply is left untouched and reported. An interrupted apply can be rolled back using its printed backup `recovery.json` path as `--receipt`, even if the ordinary apply receipt was never written. Exit 0 means success/no-op; 2 means a refusal or reported rollback conflict; 3 means a write/recovery-record error requiring inspection of the retained journal.

## Verification evidence

The [final proof receipt](proof_receipt.json) passes 19/19 checks and binds script SHA256 `f8ddaa39cafdeafcb319a17d77d78188cd40f0bf2b2c396aa30998b609e5e679`. Receipt SHA256: `f7ace1824e5024a0f600d11f877639df48b609b7cbb44cfa998848d465c8494c`. Applied-copy Python: 40 tests passed. JavaScript: 51 passed. R: 88 blocks / 958 expectations, 956 passes, zero failures/errors, one intentional malformed-input warning and one unchanged external full-fold reproduction skip. Logs are in `../package_test/`; prior unsuccessful verifier runs remain preserved in this package folder. The verifier uses only a disposable tree under `../package_test/`; the live checkout is read as a seed. It checks exact listed writes, idempotence, applied-copy Python/R/JavaScript behavior, rollback, changed/missing/new-file conflicts, interrupted writes, receipt-write failure and journal-based recovery. The proof receipt binds its result to the actual script hash. Failed earlier verifier logs are preserved separately.

OpenSecrets collection continues independently in the standardized collector. Complete requested source coverage and redesigned UI publication are not certified by this package.