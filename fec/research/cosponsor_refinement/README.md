# Cosponsorship evidence and network refinement

Research outputs: `outputs/cosponsor_refinement_20260905`. This directory extends the frozen first experiment in `fec/research/cosponsor_challengers`; it does not change the production forecaster or pipeline. See the generated `REPORT.md` in the output directory for results, source coverage and uncertainty.

The task is to rank eligible unsigned members for their first cosponsorship in the next 30 days, within finance/agriculture-referred House and Senate bills during their first 175 days. A recommendation is a member–bill–forecast-date opportunity. A high percentage from a short list must always be accompanied by its recommendation, bill and member counts.

## Evaluation boundaries

Congress 119 outcomes were already inspected in the first experiment. This refinement never uses them to tune or confirm new models. Train on Congress 117, select configurations/calibrate on calendar 2023 within Congress 118, and report calendar 2024 as later **development evidence**, not an independent test. Original phase-one configurations had also been selected using 118; the whole refinement therefore remains development-only. All added features are dated, but most historic records were first collected now, so retrospective event-time reconstruction is not historic observation-time replay.

The genuinely prospective September 5 forecast covers September 6–October 5. The five established controls and the separately issued boosted-network challenger share exactly the same frozen candidates. October 6 is the earliest scoring date. Outcomes are pending; no success is inferred from scores. The primary future comparison is boosted network versus boosted public coverage at eight per bill.

## Programs and artifacts

All commands run from the repository root. Completed builders refuse overwrite; archived V1 files remain as provenance for repaired V2 sources. Do not rerun old panel builders in the first experiment, because those can overwrite frozen artifacts.

| Program | Work performed |
|---|---|
| `verify_predecessors.py` | Introduced IH/IS legislative-body text, official source receipts and close-text audit; `--repair-missing` repairs the first batch into V2 |
| `fetch_demographics.py` | Historical 2019/2021/2022 ACS estimates and MOEs, respecting district vintages; `--repair-missing` repairs missing states into V2 |
| `public_review.py` | Dated, source-linked candidate positions; machine candidates are not gold labels |
| `rank_shortlists.py` | Original bounded LambdaMART grid and activity calibration |
| `member_network.py` | Prior-Congress network centrality and strictly earlier coalition exposure, V2 |
| `build_extra_features.py` | Text and historical geographic context |
| `external_context.py` | Bill-level public LDA attention plus separately qualified provisional staff history |
| `fit_extensions.py` | Eleven fixed logistic/tree evidence ablations |
| `rank_network.py` | Fixed public-coverage/network LambdaMART challenger |
| `influence_coverage.py` | Marginal structural coverage beyond the current coalition |
| `network_mechanisms.py` | Four fixed centrality/exposure/coverage diagnostics |
| `paired_extensions.py` | Whole-legislative-family uncertainty on 2024 development shortlists |
| `prospective.py` | Immutable official-source capture, control forecast issue and guarded future scoring |
| `prospective_network.py` | Fixed boosted-network refit on 117/118 and separately frozen future predictions |
| `prospective_shortlists.py` | Confidence cutoffs fixed from historical score quantiles, with disclosed future coverage |
| `test_refinement.py` | Date, actor, district, network, coverage and future-scoring boundary tests |
| `verify_refinement.py` | Matrix/model/source hashes, original experiment preservation, independent live eligibility and re-prediction checks |
| `verify_sources.py` | Retained introduced-text/ACS raw hashes and current status of external LDA/staff source files |
| `write_cosponsor_refinement_report.py` | Report, metrics table, standalone precision/coverage plot and completion manifest |
| `render_plot.py` | Standalone scientific figure, using a separate research-only plotting dependency directory |

LightGBM 4.7.0 is installed only under the output directory's `vendor` path, with `--target --no-deps`; it is not a production dependency. Matplotlib and its plotting dependencies are isolated in `plot_vendor`, used only by `render_plot.py`; neither available Python runtime originally included Matplotlib. Other learners use the existing local NumPy, SciPy, pandas, scikit-learn, joblib and threadpoolctl installation. Network and classification scoring is batched to reduce memory pressure. Raw downloads and matrices are research artifacts, not production deployment inputs. Run `render_plot.py` before `write_cosponsor_refinement_report.py`.

## Later outcome scoring

After October 5, capture a new official snapshot into a new directory:

```powershell
python fec/research/cosponsor_refinement/prospective.py capture --output-dir outputs/cosponsor_refinement_20260905/prospective_outcomes_20261006
```

Prepare a source-backed service review with this schema, using actual official records and dates:

```json
{
  "complete_departure_review": true,
  "reviewed_through": "2026-10-05",
  "sources": ["Official dated membership/change records actually reviewed"],
  "last_serving_dates": {}
}
```

`last_serving_dates` maps the bioguide ID of every departed forecast member to their actual last day serving. An empty object is appropriate only after a complete review establishes no relevant departures. These are instructions for a future factual review, not a claim that such a review has occurred.

```powershell
python fec/research/cosponsor_refinement/prospective.py score --later-snapshot outputs/cosponsor_refinement_20260905/prospective_outcomes_20261006 --service-review path/to/completed_service_review.json
```

The scorer refuses immature outcomes and changed hashes, requires all issued bills to be present, reconciles missing serving members, censors incomplete service windows, excludes backfilled prior signatures, and retains original ranks without replacement picks. It reports paired bill-bootstrap uncertainty and the pre-issued selective policies. No scheduler or future notification has been installed.

## Material data qualifications

- Member-network ties are past cosponsorship relationships. Centrality, exposure and structural reach do not establish causal influence.
- LDA attention uses the later of filing/public posting dates and formally cited bill IDs. It does not identify privately contacted members. Sign-derived member lobbying flags and learned stance labels are excluded.
- Staff V5 has unresolved corpus-level identity and coverage qualifications despite numerical PASS receipts. The exploratory staff fit is excluded from primary selection and prospective scoring. Do not promote it without the governing staff corpus being validated.
- District ACS data are missing before compatible geography is released, including early 118 and redrawn 117 North Carolina districts. Point estimates enter features; retained source MOEs are not propagated through the learner.
- The public-position audit yields no qualifying positive training leads in the defined historic prediction window. Source-context reviews are assistant reviews, not human-adjudicated gold labels. More dated, actor-resolved pre-action evidence is needed.
- The new results describe 30-day cosponsorship, not bill passage, floor voting, long-run support, lobbying effectiveness or guaranteed individual behavior.
