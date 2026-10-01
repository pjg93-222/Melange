# Melange-wide evidence audit and continuing-member benchmark

Research code only. This directory does not register a production pipeline step, alter dashboard ranks or issue outreach. The user selected a fixed continuing-member cohort after the audit found current-roster selection in historical media/public coverage.

## Inputs and outputs

The fixed cohort is the 377-member intersection of frozen Congress 117/118 risk panels and the verified September 5, 2026 official roster. Actual dated first cosponsorships are the outcome reference. This is a conditional historical benchmark; current fitted personality/composite scores are not backdated.

Outputs are in `outputs/cosponsor_universe_20260905`. All full-panel metadata and earlier feature arrays remain in `outputs/cosponsor_challengers_20260905` and `outputs/cosponsor_refinement_20260905`. New arrays preserve their exact row ordering; cohort membership masks select original row indices. Earlier experiments and issued prospective forecasts remain immutable.

The whole-system census records 402,142 data artifacts, 323 path families, 578 schemas and 80 declared stores. It inventories operational/media/duplicate material and explicitly lists exclusions and uninspected content. It does not claim every file was substantively analyzed or every measurement was tested.

## Execution order

Run from the repository root using the installed Python environment. Dependencies already used by the project include NumPy, pandas, PyArrow, SciPy, scikit-learn, NetworkX, PyYAML, joblib, matplotlib and threadpoolctl. Several raw inputs live under the user's adjacent Draft Systems directory, `%LOCALAPPDATA%/Melange`, or `C:/melange-data`; source receipts name exact paths and hashes.

The commands below record the experiment's pipeline. Builders intentionally refuse to replace frozen outputs. Re-execution requires a fresh research output location with consistently configured paths and the retained source/panel inputs; do not delete or overwrite the completed audit to rerun it.

```powershell
python fec/research/cosponsor_universe/universe_inventory.py
python fec/research/cosponsor_universe/universe_conduct_features.py
python fec/research/cosponsor_universe/universe_psychology_features.py
python fec/research/cosponsor_universe/universe_election_features.py
python fec/research/cosponsor_universe/universe_relational_features.py
python fec/research/cosponsor_universe/universe_relational_panel.py
python fec/research/cosponsor_universe/universe_amendment_features.py
python fec/research/cosponsor_universe/universe_gold_cohort.py
python fec/research/cosponsor_universe/universe_boundary_checks.py
python fec/research/cosponsor_universe/universe_models.py
python fec/research/cosponsor_universe/universe_statistics.py
python fec/research/cosponsor_universe/universe_verify.py
python fec/research/cosponsor_universe/universe_finalize.py --draft-only
& 'C:/Users/pgoff/AppData/Local/Melange/research_runtime/cosponsor_universe_20260905/Scripts/python.exe' fec/research/cosponsor_universe/write_universe_report.py
# Review the generated report and verification receipt before sealing.
python fec/research/cosponsor_universe/universe_finalize.py
```

Model fitting, statistics and verification used the default project Python 3.12. The report command uses a separate plotting environment because the project environment does not contain Matplotlib. Both runtime paths and package versions are recorded in the final manifest; the report summary records its own rendering environment. `render_requirements.txt` in the output directory pins the isolated renderer's packages. On another machine, create a separate virtual environment and install those requirements for the report command.

The finalizer's `--draft-only` step creates the local Brain update draft before report generation. After report and verification review, running the finalizer without that flag seals the generation.

Model fitting resumes only when the existing plan, code, supporting dependencies, source inputs and completed-model hashes match. All 24 models are refit on the same cohort: 16 challengers and 8 controls. Selection/calibration uses 2023, followed by frozen predictions and 2024 descriptive assessment. No old full-population probability vector is used as a matched-cohort refit. All 23 non-placebo models can win. The protocol and plan give exact features, sampling and configurations.

The weekly hazard model uses the same mature training rows and expands each observed duration into 7/7/7/7/2-day bins. Every positive is retained; negative rows use deterministic 10% sampling and weight 10. The Poisson target is events/exposure and the likelihood weight includes exposure. Thirty-day probabilities integrate the five fitted weekly rates. Prediction always reads original full-panel indices after applying the cohort mask.

Statistics include 79 paired contrasts (78 nontrivial plus the identical-control sanity check), 100,000 legislative-family bootstrap draws, calibration, chamber/party strata, fixed 2023 thresholds and matched recommendation budgets. Intervals are descriptive development evidence because Congress 118 was previously inspected. They do not establish causal lobbying effects or generalization outside the continuing cohort.

## Receipts and revisions

`universe_plan.json` binds the final protocol, all model features/configurations, original panel arrays, cohort, source sidecars and imported model helpers. `universe_selection.json` freezes predictions/models and the 2023 winner before any new 2024 scoring. Independent extraction, cohort, model/statistics and preservation reviews are retained alongside the results.

`pre_coverage_review` preserves the first full-population attempt, stopped after two 2023-only summaries when source-selection bias was discovered. `pre_gold_review` preserves the superseded design that had excluded media before the user's cohort instruction; it was not fitted. `relational_pre_review` and `relational_panel_pre_review` preserve the initial broadcast extraction/panel before exact cross-URL duplicate evidence was removed. Final output receipts distinguish these generations.

No existing September 5 forecast is revised by this experiment. Its recorded outcome window ends October 5; independent scoring is possible no earlier than October 6. This audit does not schedule that future work or claim those outcomes have occurred.
