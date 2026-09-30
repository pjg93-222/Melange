# Giving Forecast refit pipeline (Phase 1 parity, Phase 2 bundle v2, Phase 5 refit agent)

R pipeline that rebuilds every number of `mentat/app/data/giving-models-v1.json` from **raw inputs** and proves it reproduces the
frozen v1 bundle and every Codex design file to the spec's tolerances. Phase 1 makes **no methodology change**: the v1 variable
selections are frozen, there is no DL blend in the bundle output, no anchor change, no seats removal and no v2 schema. The DL
blend, backtests, prediction intervals and the rule auto-pick exist as tested library code and are not used by the v1 projection.

Design spec: `SPEC.md` of the Phase 1 architect (scratchpad `phase1_spec`). Rulings applied: clubSandwich from a pipeline-owned
library outside git with a hash manifest, every input pinned (including `interpretable_effects.csv` and `analyze.py`, which the
v1 builder read but did not list), lobbying sample = all complete years from 2008, ordinary p primary, Paul's 2026-09-30 slope-rule
auto-pick.

## Run

```
Rscript run_refit.R --mode parity [--run-id <id>] [--no-tests]      # rebuild + compare + run folder; never publishes
Rscript tests/testthat.R                                            # the parity suite (RF_TEST_FILTER=<regex> for a subset)
Rscript tools/parity_report.R                                       # measured max deviation of every parity target -> parity_deviations.csv
Rscript tools/make_inputs_manifest.R                                # regenerate registry/inputs.json (only for a new input vintage)
Rscript tools/record_rlib_manifest.R                                # record the vendored package hashes of this platform
```

Windows: `& "C:\Program Files\R\R-4.6.0\bin\Rscript.exe" ...` (R 4.6.0 or later).

### Environment variables

| Variable | Meaning |
|---|---|
| `RF_RUNTIME` | runtime folder: raw vault, runs (default `%LOCALAPPDATA%\Mentat\forecast\refit`, `<MENTAT_DATA_ROOT>\forecast\refit`, or `~/.local/share/Mentat/forecast/refit` off Windows) |
| `RF_RLIB` | vendored package library (default `<RUNTIME>\Rlib`): clubSandwich 0.7.0, sandwich 3.1-3 |
| `RF_INPUT_ROOT` | one folder mirroring the input roots: `LOO`, `CHE`, `SGSD`, `SGSA`, `RLIBX`, `House_Senate_Control_Forecasts_CSV.zip` |
| `RF_ROOT_<ALIAS>` | override one alias (`LOO CHE SGSD SGSA ZIPC RLIBX BUNDLE_V1`); wins over `RF_INPUT_ROOT` |
| `RF_GLASSBOX_DIR` | Glass Box event folder (default `C:\Users\pgoff\.claude\glassbox\events`) |
| `REFIT_OUT` | where run folders go (default `<RUNTIME>`) |
| `REFIT_CORES` | workers of the parallel batteries; `1` = serial (default: serial on Windows, detectCores()-2 elsewhere) |
| `RF_TEST_RUNTIME` | tests only: keep the raw vault between test runs |

Parallel runs are **bit-identical** to serial runs: no unit of work uses R's global RNG. Every stream comes from explicit entropy
through `R/rf_rng.R` (numpy SeedSequence of `c(seed, crc32(model), crc32(term), crc32(cluster))`, or the stepwise case counter),
results are combined in input order, bootstrap blocks return integer hit counts. `tests/testthat/test-13-parallel.R` proves it
(`REFIT_CORES=1` vs 2 on a bootstrap enumeration, the backtest folds and the stepwise grid). Set `OPENBLAS_NUM_THREADS=1` on a
machine with a threaded BLAS so a matrix product cannot differ in its last bits between runs.

## Inputs

`registry/inputs.json` pins 98 files by sha256 (OpenSecrets captures, FEC candidate masters, IBISWorld / CPI / control / LobbyView
workbooks, the IEM zip, the four 2026 daily market files, and the Codex design files as **parity references only**). Aliases
resolve through `R/rf_config.R`. On first sight each file is copied into `<RUNTIME>/raw/<sha256>/<name>` and read from there, so
a Downloads / Temp clean-up cannot break a refit. A pinned file whose hash changes fails gate G1 until the manifest is regenerated.
`registry/industries.json` lists the six fitted industries and four declined ones (with reasons); property and casualty is a pilot
entry whose OpenSecrets F3400 capture is withheld with the reason "OpenSecrets F3400 capture not supplied".
`registry/models.json` holds the frozen specifications and the package version pins.

## What a parity run does

1. G0 environment (R >= 4.6.0, package pins from the vendored library, `rf_rng.R` hash).
2. G1 inputs (every pinned hash, vault copy byte-equal).
3. Panels from raw inputs: PAC growth panel (21 rows), congressional money panel (42 rows; 16,916 recipients, 64 presidential
   overlaps, 22 FEC identities), IEM Jan-Jun control score, seat calls, 48 stepwise cases, lobbying levels (77) and differences (71). G3 panel checks.
4. The frozen lm() fits, PAC forward-AIC selection-repeated p (22 of 216), lobbying wild p (1,432 of 46,656).
5. The 48-case stepwise grid: masks, CR2, selection-repeated bootstrap on the reproduced numpy stream, Holm, nested validation.
6. The v1 bundle projection, compared leaf by leaf with `giving-models-v1.json`.
7. Review files: `regressions.txt` (real `summary(lm())` plus the labelled robustness block of every model), backtests, the rule-selection table.
8. G2 parity: the parity test files run inside the run.

Run folder `<runs>/<run_id>/`: `panels/*.csv`, `bundle/giving-models-v1.projection.json` (never published), `review/{regressions.txt,
backtests.csv, rule_selection.csv, selected_models.csv, nested_validation_metrics.csv, inputs.csv, gates.json}`, `receipt.json`
(every input hash, every code file hash, packages, gates, parity counts, bundle hash, decision), `log.txt`. Decision: `PARITY_GREEN` or `FAIL`.
Every stage and gate emits a Glass Box event (`kind` run.start / stage.start / stage.finish / gate.result / run.finish, lane `claude`,
source `giving-forecast-refit`).

## Library code for later phases (tested, not wired into the v1 output)

* `rf_partial_pool`, `rf_dl`: DerSimonian-Laird partial pooling toward the pooled slope (spec 3.8).
* `rf_backtest`, `rf_backtest_metrics`: leave-one-election-out, chronological and rolling-origin backtests with R0 / R1 / R2 rules, fold-restandardized growth, anchored-step prediction intervals.
* `rf_select_rule`, `rf_select_rules`, `rf_choose_rule`: Paul's auto-pick: lowest MAE in both designs, blend when they disagree, pooled reported when the blend resolves to it. `RF$RULE_MIN_GAIN` (default 0 = literal rule) sets an optional clear-winner margin.
* `rf_step_sigma2`, `rf_interval`: prediction intervals beside the coefficient interval.

## Tests

`tests/testthat/test-01 ... test-13`: registry, pinned inputs and vault, panels vs Codex design files, coefficients vs the v1 bundle,
bootstrap / selection-repeated p-values, nested validation, partial pooling, backtests vs `SP/tailoring/summary.csv` and the SPEC section 8 table,
rule auto-pick, the whole v1 projection, the run (read-only, events, receipt, failure path), no-network scan, parallel == serial.
Fixtures in `tests/testthat/fixtures/` are copies of the earlier audit lanes' outputs (`robustness_pvalues.csv`, `fold_coefficients.csv`,
`full_sample_slopes.csv`, `summary.csv`, `pac_prevchg_reconcile.csv`), used as numerical references.

## Phase 2: bundle v2 (asserted against the shared contract)

`rf_v2_context()` computes everything a refit needs; `rf_bundle_v2()` writes `giving-models-v2.json` exactly as `mentat/forecast/contracts/giving-models-v2.schema.json`
demands (objects are closed; the schema, the example and the 16 shared negative controls are the contract and are read-only here). `R/rf_schema.R` validates with a hand-written
validator of the contract's keyword subset (no JSON Schema package is installed); `tools/check_bundle_contract.py` runs the contract's own Python validator on a bundle as a second
opinion, and `test-15-bundle-v2.R` asserts: the example validates, every shared control is rejected on the example AND on the writer's output, the writer's output validates in R and
in Python, plus the numbers of ADDENDUM section F.

* PAC: the auto-pick (`rf_select_rule`, a non-pooled rule must beat the pooled slope by 5% in every design) chose own slopes (R1). `pac_model.slopes[id].applied` is the slope the
  calculator uses; `prediction.industries[id]` holds each industry's anchored-step residual (pairs (t-2, t)); `evidence` (open object) records the rule-selection table and the
  calculator-path leave-one-election-out MAE per industry, which a later refit's G6 compares against.
* Shares: pooled slope (R0) and the previous-cycle anchor; Polymarket-to-Polymarket control inputs (`political_inputs` 2024, `saved_outlook` 2026, Kalshi and the equal weight kept as sensitivities).
* Lobbying: `lobby_model.log_refit` (`dly ~ dg + factor(year)`, -0.811% per point, p 0.029), the dollar model kept as evidence.
* Seats are evidence only (`evidence_models`, `calculator: false`). `pac_complete` and the lobbying differenced-controls regressions stay in `regressions.txt`: the contract's evidence model requires a chamber.

## Phase 5: the refit agent

```
Rscript run_refit.R --mode detect                                  # read-only scan of Mentat's report directory; queue industries the registry does not know
Rscript run_refit.R --mode refit [--industry <id>] [--publish auto|never]
Rscript run_refit.R --rollback <model_version>
```
* **Watcher** (`rf_agent_detect`): lists `* Industry Spending Overview.xlsx` in the report directory (mentat/config/report-directory.json, or `RF_REPORT_DIR`), reads each workbook's
  export receipt (`<name>.audit/audit-manifest.json`) read-only, compares with the registry and with what it saw last (`<runtime>/agent/seen.json`). A workbook the registry does not know is queued
  once (`<runtime>/agent/queue/<slug>.json`) with a `DATA_REQUEST.md` and a registry stub; declined industries are not re-flagged.
* **Waiting for data**: an industry whose inputs are missing (property and casualty: OpenSecrets F3400 captures, and IBISWorld revenue that ends before the 2024 cycle) ends as
  `WAITING_FOR_DATA` (exit 0, success event, `DATA_REQUEST.md`), never as a failure; the packet lists the gaps.
* **Gates** (`R/rf_gates.R`): G0 environment, G1 inputs, G2 parity (the parity suite, in the same run), G3 panels, G4 sample adequacy (WARN, capability withheld with a stated reason),
  G5 stability (HOLD), **G6 hard backtest gate: no existing industry's calculator-path leave-one-election-out MAE may exceed the published calculator's (new <= published + 1e-9)** (HOLD),
  G7 bundle schema and completeness (FAIL), G8 consumer smoke (HOLD until `MENTAT_G8_CMD` names a v2-capable calculator command), G9 beats last-period naive (WARN only).
  Decision: any FAIL, else any HOLD, else PUBLISH.
* **Publish** (`R/rf_publish.R`): only on PUBLISH. Under the lock (`<runtime>/refit.lock`, stale after 6 h with a dead owner): stage, re-validate and hash-check the bundle, rename it into place as
  `giving-models-v2.json` with its receipt, archive the pair under `<runtime>/published/<model_version>/`, then switch the pointer `giving-models-current.json` atomically. v1 stays where it is;
  nothing is committed. `RF_PUBLISH_DIR` (default `mentat/app/data`) names the target. `--rollback <model_version>` restores an archived publish or the kept v1.
* **Review packet** (`<run>/review/`): `REVIEW.md` (decision, gate table, rule-selection table, slopes, G6 table, log refit, data gaps, 2026 inputs, platform), `regressions.txt` (real
  `summary(lm())` blocks plus the robustness block of every model, including the lobbying log refit), backtests, rule selection, robustness p-values, G4/G5/G6 tables, bundle diff, inputs.
* **Glass Box**: run.start, stage.start/finish per stage, gate.result per gate, publish.start/done/hold, run.finish or a failure event.
* **Platform**: every receipt carries `platform` (R version, BLAS, LAPACK, worker count). Results on another platform agree to ~1e-13 (a pod's ATLAS BLAS against a laptop's reference
  BLAS); bundles are compared with `rf_bundle_diff()` (tolerances, run-identity fields ignored), never byte equality. Parallel == serial bit-for-bit holds within one platform.

## Not built

The IEM `max_contract_trade_age_days` column (no bundle number depends on it); the `lobby_differenced_controls` evidence regression; an R port of the LobbyView raw builder; the Python
consumer and the anchor snapshot builder (other lanes). Gate G8 stays HOLD until the v2 calculator exists.
