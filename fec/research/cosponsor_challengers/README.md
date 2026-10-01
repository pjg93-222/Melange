# Cosponsorship challengers

An isolated research experiment authorized on 2026-09-05. It creates candidate models and evidence; it does not replace production forecasts or write to workbooks, rankings, schedulers, or the production pipeline.

The fixed output directory is `outputs/cosponsor_challengers_20260905`. Read `PROTOCOL.md` for the outcome, population, information boundaries, predeclared comparisons, and limitations. Historical event-time reconstruction is not a claim of actual historical prospective deployment.

## Pipeline

Run from the repository root with Python 3.12 and the installed NumPy, pandas, SciPy, scikit-learn, PyYAML, PyArrow, joblib and threadpoolctl packages:

```powershell
python fec/research/cosponsor_challengers/audit_data.py
python fec/research/cosponsor_challengers/build_panel.py
python fec/research/cosponsor_challengers/extend_public.py prepare
python fec/research/cosponsor_challengers/extend_public.py apply
python fec/research/cosponsor_challengers/test_challengers.py
python fec/research/cosponsor_challengers/validate_panel.py
python fec/research/cosponsor_challengers/run_models.py develop
python fec/research/cosponsor_challengers/simple_benchmarks.py freeze
python fec/research/cosponsor_challengers/run_models.py final
python fec/research/cosponsor_challengers/simple_benchmarks.py evaluate
python fec/research/cosponsor_challengers/component_diagnostics.py
python fec/research/cosponsor_challengers/write_report.py
python fec/research/cosponsor_challengers/verify_artifacts.py
```

Several steps refuse to overwrite completed snapshots or cross an information boundary. The development runner resumes already completed model families. The final runner reuses frozen predictions after an interruption; it does not refit them once the final prediction freeze exists. Start a distinct output directory and protocol for a new experiment. Do not remove freezes to retune against the same final outcomes.

`recover_panel.py` recovered the initial run after a pandas consolidation exceeded available shared-host memory. It rebuilds metadata in the identical deterministic order while retaining the feature matrix bytes. Normal future construction now streams metadata directly, so recovery is not part of the normal pipeline.

## Storage and execution

The full feature matrices contain approximately 11.2 million rows and 63 float32 columns, about 2.8 GB logically. They are memory-mapped for training/prediction and were transparently NTFS-compressed on the user's nearly-full drive. Models and predictions are separate artifacts. Keep several GB of free disk and memory available. ML computations are limited to four threads.

All positive training rows are retained. Binary training samples 10% of negative rows with inverse weight 10; the exposure-expanded survival model samples 2% with inverse weight 50. Development and final scoring include every eligible complete-horizon row, without class balancing. The survival model additionally uses censored training exposure.

## Models

- A new 30-day logistic baseline approximates the existing information family, with dated eligibility and introduced-title topic classification. It is explicitly separate from the real production comparator.
- Enhanced logistic adds previous-Congress member-policy behavior and introduced-title analogues.
- Dynamic logistic and histogram boosted trees add age, dated actions, earlier joins, co-party participation and prior-collaborator participation.
- Weekly time-to-sign fits a piecewise-exponential rate model with a Poisson likelihood and exact exposure weights, then integrates over the same 30-day horizon.
- Public variants add dated topic/bill mentions and conservative first-person or named-actor support/oppose indicators. A coverage/mention-only control separates directional stance from data availability.
- The actual production model is evaluated through its emitted Congress 118 and 119 predictions, using a Congress-118-only mapping from its original endpoint to the 30-day endpoint. Coverage restrictions remain visible.

## Data qualification

The extended public extraction uses raw hearing turns and full social-post text plus official press headlines. It excludes unresolved/wrong-chamber hearing identities, party mismatches, retweets/transcripts, undated sources and third-party press hosts. These rules do not amount to full human validation. Statements, titles and speaker assignments were reconstructed from currently stored sources; historical first-observed versions are not comprehensive.

There are zero usable explicitly bill-linked support/oppose features in the mature training/development risk sets. This experiment can test broad dated topic evidence but cannot establish an endorsement-to-sign relationship. The sparse final-only explicit-support feature is unlearned and cannot establish predictive usefulness.

## Validation

Boundary tests cover date cutoffs, already-signed candidates, source attribution, serving-member eligibility, first-sign outcomes despite withdrawal, bill-level versus amendment-level XML, and weekly event/exposure accounting. `validate_panel.py` checks every matrix for finite values and size, verifies hashes, checks unique risk rows and independently checks 2,500 labels per Congress against frozen source rosters.

`final_results.json` includes full-population and production-common-population metrics, calibration, chamber/party/age summaries, paired legislative-family bootstrap intervals, crossed member/family Brier sensitivity and public-evidence ablations. AP bootstrap intervals use score bins, with the approximation error stated; AP point estimates and shortlist metrics are exact.

Three additional simple historical rules were frozen before final performance was inspected: prior member signing rate, prior sponsor affinity and prior analogue support. Their calibration was fit on Congress 118 only. Results are descriptive benchmarks in `simple_benchmark_results.json`, not additional tuned challengers. A negative calibration slope is disallowed by the monotone mapping; when this happens the calibrated rule becomes the development base-rate forecast.
