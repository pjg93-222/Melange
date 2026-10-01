# Machine learning — quant-model-evaluation reference

> **Load when:** auditing a classifier, regressor, scoring or ranking model; probabilities that feed an allocator, a threshold, an expected count or a dashboard; a train/test or backtest design; model or LLM outputs reused as variables in later analysis; importance or SHAP claims; conformal intervals, double/debiased ML or a Bayesian model. **Not for:** whether the predicted relationship is causal (`social-science.md`); benchmark tests for a single forecast series and backtest-overfitting corrections (`finance.md`, `core-statistics.md`); Monte-Carlo error of simulators (`engineering-simulation.md`); pipeline determinism and provenance (`automation.md`); AI-governance and model-risk rules (`regulatory.md`).
> Facts marked (as of DATE) are time-sensitive; re-verify before relying on them. Every Python snippet below was run on synthetic data with a known answer (scikit-learn 1.9.0, statsmodels 0.14.6, pandas 3.0.3; as of 2026-09-30).
> A KILLED printed by a script is a candidate until a second independent reader confirms it (SKILL.md hard rule 5).

**Prediction is not estimation.** A model can forecast well while its coefficients and importances are unstable or confounded (Mullainathan & Spiess 2017; Grimmer et al. 2021; Hofman et al. 2021). Settle first which claim is under audit: *the model predicts Y out of sample* (this module) or *X changes Y* (`social-science.md`). A model of which legislators will switch and a model of what money causes are different estimands, and a feature that predicts is not a lever. Probabilities that move money make the model tier `T1`.

## 1. Assumption map

| Assumption (class) | Where it usually hides | What breaks if it is false | Tests |
|---|---|---|---|
| Train and test are independent: no duplicate rows, no shared entities, test strictly later (`STATISTICAL`) | Random row splits of panel data; one legislator, donor or district in both folds; oversampling before the split | Skill is optimistic and collapses on new entities or the next period | 2.1, 2.2; ML-03, ML-06, ML-07 |
| Every feature is known at prediction time (`DATA`) | Full-period aggregates; text posted after the vote; co-sponsorship of the bill being predicted; later-amended data vintages | Target leakage: near-perfect backtest, useless in use | 2.1; ML-04, ML-05 |
| Model choice, tuning and thresholds never saw the evaluation data (`STATISTICAL`) | Tuning on the backtest window; best of many models reported; threshold picked on the test set | The headline number is biased upward | 2.2; ML-09 |
| The model beats simple rules (`DECISION`) | Comparison only with other complex models, or with nothing | Complexity with no information gain | 2.3; ML-11, ML-12 |
| Probabilities are calibrated, overall and per subgroup (`MEASUREMENT`) | Class weights, resampling, boosted trees, small data | An allocator overspends on inflated probabilities; expected counts are wrong | 2.4; ML-14 to ML-18 |
| The data-generating process is stable from training to use (`STATISTICAL`) | New Congress, redistricting, rule or disclosure changes, a collector or API change | Silent decay; calibration drifts first | 2.5; ML-19 to ML-21 |
| Predicted labels reused downstream have ignorable error (`MEASUREMENT`) | Regressions or aggregates on classifier or LLM labels (stance, topic, industry codes) | Biased estimates and invalid (under-covering) intervals, even at 80-90% accuracy | 2.6; ML-22 |
| DML nuisance models are adequate and overlap holds (`CAUSAL`) | "ML-adjusted" effect estimates | Bias that depends on the learner; extreme weights | 2.7; ML-23 |
| Intervals cover at their nominal rate (`STATISTICAL`) | Conformal or bootstrap intervals calibrated on exchangeable data, then used over time | Under-coverage in new periods and subgroups | 2.7; ML-24 |
| Importance or SHAP reflects mechanism (`CAUSAL`) | "Drivers" panels, model cards, briefings | Levers that do not move the outcome; credit split arbitrarily among correlated features | 2.8; ML-25 |
| A Bayesian fit converged and reproduces the data (`COMPUTATIONAL`) | Hierarchical models with divergences or unchecked priors | Wrong posteriors presented as uncertainty | 2.9; ML-26 |
| An LLM step is pinned, stable and faithful (`COMPUTATIONAL`, `MEASUREMENT`) | Vendor "latest" aliases, unlogged prompts, unsampled outputs | Labels drift, conclusions flip with prompt wording, facts are confabulated | 2.10; ML-27 to ML-29 |

## 2. Tests

### 2.1 Leakage audit
- **Tests:** whether reported performance uses information the model will not have when it is used. Kapoor & Narayanan (2023) found leakage in 17 fields and 294 papers and sorted it into eight types in three families (paraphrased):
  - *no clean separation*: no held-out set; preprocessing or feature selection fitted on train and test together; duplicate rows across splits;
  - *illegitimate features*: proxies of the outcome (co-sponsoring the bill whose vote is predicted; a status field updated after the event);
  - *test set not drawn from the target distribution*: temporal leakage (training on the future); non-independence (the same member or donor on both sides); sampling bias in the test set.
  In their civil-war re-analysis, complex models lost their edge over logistic regression once leakage was fixed. REFORMS (Kapoor et al. 2024) is a 32-item consensus checklist (study goals, reproducibility, data quality, preprocessing, modelling, leakage, metrics and uncertainty, generalizability); use it as the intake form for any ML-based claim.
- **Assumptions of the test itself:** the entity, time and availability columns are right; hashing finds exact duplicates only (look for near-duplicates, such as re-scored versions of one document, by key); a clean result is not proof of independence.
- **Run it:** `python scripts/leakage_audit.py --train train.csv --test test.csv --id member_id --time vote_date --embargo 90D --target voted_yes --features all --available-at features_known_at`
  - Checks: duplicate rows across splits; entity overlap (`--id`) and coarser group overlap (`--group`); test rows at or before the last training time and inside the embargo; single-feature AUC or R² at or above `--leak-threshold` (default 0.98); rows whose features became known after `--time`; missingness-pattern shift between splits.
  - `--id` is the entity identifier (member, donor, firm), never a row number; `--group` is a coarser unit that must not straddle splits (district, household, firm). Leave row numbers and load stamps out with `--ignore`.
  - `--embargo` is a number and a unit (Y, Q, M for months, W, D, H, min, S: e.g. 20D, 90D, 6M, 1Y), or a plain number when `--time` is numeric. Make it at least as long as the source's reporting lag (money data: `finance.md`).
- **Pass criterion (fix before running):** contamination checks follow the script's share rule: no affected test rows → SURVIVES; affected share ≤ `--kill-share` (default 0.05) → WOUNDED; above → KILLED (a candidate until a second independent reader confirms it). Entity overlap must be 0 when the claim is about new entities. Any feature at the leak threshold is WOUNDED until its availability at prediction time is documented; if no feature can be scored (all missing or constant), the screen is UNVERIFIED-HERE, not a pass.
- **Failure signature:** AUC implausible for the domain; one feature nearly separates the classes; skill collapses under leave-one-period-out; different missingness in train and test (often a new collector version).
- **Source:** Kapoor & Narayanan (2023); Kapoor et al. (2024).

### 2.2 Split design, tuning inside training folds, nested CV
- **Tests:** whether validation mimics use. New entities → split by entity (legislator, donor, district). Future periods → split forward in time (Congress, cycle, quarter). Both → grouped and forward. Every learned step (scaling, imputation, encoding, feature selection, resampling, tuning, threshold) is fitted inside the training fold only; tuning on all rows and then cross-validating the tuned model is biased upward (Varma & Simon 2006).
- **Assumptions of the test itself:** the grouping variable captures the dependence; each Congress is one draw of an agenda, so leave-one-Congress-out has few folds: report every fold, not only the mean.
- **Run it:** nested CV by member; tuning happens only inside the outer training folds:
```python
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV, GroupKFold, cross_validate
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

pipe = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
inner = GridSearchCV(pipe, {"logisticregression__C": [0.01, 0.1, 1, 10]},
                     cv=GroupKFold(n_splits=4), scoring="neg_brier_score")
nested = cross_validate(inner, X, y, groups=member, cv=GroupKFold(n_splits=5),
                        scoring="neg_brier_score", params={"groups": member})
print(-nested["test_score"])   # one Brier score per outer fold: report the spread
```
  Forward-chaining by Congress (tune inside `X[tr]` only):
```python
import numpy as np
from sklearn.metrics import brier_score_loss

for c in np.unique(congress)[2:]:          # train on earlier Congresses only
    tr, te = congress < c, congress == c
    p = pipe.fit(X[tr], y[tr]).predict_proba(X[te])[:, 1]
    print(c, round(brier_score_loss(y[te], p), 4))
```
  - Blocked or grouped CV for temporal, spatial or hierarchical structure: Roberts et al. (2017); time-series CV caveats: Bergmeir & Benítez (2012), Bergmeir et al. (2018), Cerqueira et al. (2020). `TimeSeriesSplit(gap=k)` adds an embargo for evenly spaced series; purged CV for overlapping labels is in `finance.md`. Spatial prediction models need spatially blocked folds (`geospatial.md` §2.2).
- **Pass criterion (fix before running):** the split matches the claim; the headline number comes from an outer loop or an untouched holdout that informed no choice; the optimism gap (`best_score_` of a search run on all rows minus the nested score) and the per-fold spread are reported. WOUNDED if the gap exceeds the between-fold standard deviation.
- **Failure signature:** random `KFold` on panel rows; `best_score_` quoted as performance; a scaler fitted before the split; SMOTE or undersampling before the split; skill that drops sharply under grouped or forward splits.
- **Source:** Varma & Simon (2006); Roberts et al. (2017); Tashman (2000).

### 2.3 Baselines first, improvement with an interval
- **Tests:** whether the model adds information that a simple rule does not already carry. In a mass collaboration, the best predictions of life outcomes were only slightly better than a simple benchmark (Salganik et al. 2020); in conflict forecasting, statistically significant predictors added little out-of-sample accuracy (Ward et al. 2010).
- **Baselines**, strongest applicable first: base rate (a constant prevalence probability) for Brier and log loss; majority class for accuracy; the party-line rule (vote with the party majority); last-period behaviour (as in the previous Congress or cycle); for numeric targets, the training mean, the last value and the seasonal naive (`scripts/backtest_eval.py --benchmark naive|seasonal:K|mean|col:COL`).
- **Assumptions of the test itself:** model and baseline are scored on identical rows; resampling respects the independent unit (members, not member-votes; see `core-statistics.md` on clustering).
- **Run it:** per-row Brier losses for both, then a paired cluster bootstrap over members:
```python
import numpy as np

def paired_cluster_boot(loss_base, loss_model, unit, B=2000, seed=20260930):
    """Mean loss improvement (base minus model) and a 95% interval, resampling whole units."""
    rng = np.random.default_rng(seed)
    d = np.asarray(loss_base, float) - np.asarray(loss_model, float)
    _, inv = np.unique(unit, return_inverse=True)
    sums, counts = np.bincount(inv, weights=d), np.bincount(inv)
    draws = rng.integers(0, sums.size, size=(B, sums.size))
    boot = sums[draws].sum(axis=1) / counts[draws].sum(axis=1)
    return d.mean(), np.percentile(boot, [2.5, 97.5])

gain, ci = paired_cluster_boot((y - p_party) ** 2, (y - p_model) ** 2, member)
```
  - Forecasts scored period by period: `python scripts/backtest_eval.py --data oos.csv --actual y --forecast p_model --time period --benchmark col:p_party_line` (Diebold-Mariano with the Harvey-Leybourne-Newbold correction; Clark-West with `--nested`). For a panel add `--group member_id`: the tests then run on each period's mean loss differential. `--time` must hold numbers or dates (ordered text only with `--allow-text-time`), and non-finite values are refused as usage errors.
  - `scripts/calibration_report.py` also scores Brier, AUC and average precision against the base rate (2.4).
- **Pass criterion (fix before running):** the model beats the strongest simple baseline on a proper score chosen in advance, out of sample, with the improvement's interval above 0 (the bootstrap 95% interval, or the script's one-sided test at `--alpha`); and the model wins, and keeps its sign, in at least `--min-window-share` of windows (default 0.75). The script prints KILLED when skill ≤ 0.
- **Failure signature:** gains only in-sample; the interval includes 0; wins pooled but loses in the newest period; 90% accuracy where the majority rule already scores 90%; the only comparator is another complex model.
- **Source:** Salganik et al. (2020); Ward et al. (2010); Diebold & Mariano (1995); Gneiting & Raftery (2007).

### 2.4 Calibration versus discrimination
- **Tests:** discrimination asks whether cases are ranked correctly (AUC; average precision, whose baseline is the prevalence). Calibration asks whether a predicted 0.3 happens 30% of the time. Anything that multiplies probabilities by dollars, sums them into expected counts or thresholds them needs calibration, and a high AUC does not imply it (Van Calster et al. 2019).
- **Measures:**
  - reliability table: observed rate against mean prediction per bin; ECE = Σ_k (n_k/N)·|ō_k − p̄_k| and MCE = max_k |ō_k − p̄_k| (Naeini et al. 2015; Guo et al. 2017);
  - calibration intercept (calibration-in-the-large: logistic fit of y with logit p as offset; ideal 0) and slope (coefficient on logit p; ideal 1; below 1 means predictions are too extreme, the usual sign of overfitting) (Cox 1958);
  - Brier score = reliability − resolution + uncertainty, where uncertainty ō(1 − ō) is the Brier score of the base rate (Brier 1950; Murphy 1973); Brier skill = 1 − Brier / base-rate Brier;
  - every metric per subgroup (party, chamber, period).
- **Class weights and resampling.** `class_weight="balanced"`, undersampling and oversampling train the model as if the classes were equally common, so its probabilities inflate the rare class. Correct them with the prior-shift rule: multiply the odds by the ratio of target to training priors and renormalize (Saerens et al. 2002).
```python
def prior_shift(p, pi_train, pi_target):
    """Saerens et al. (2002): rescale the odds by the prior ratio, then renormalize."""
    a = p * pi_target / pi_train
    b = (1 - p) * (1 - pi_target) / (1 - pi_train)
    return a / (a + b)
```
  - Use `pi_train=0.5` for balanced binary weights and `pi_target` = the prevalence where the probabilities are used. On synthetic data with 11.4% prevalence, balanced training gave a mean prediction of 0.41; the correction gave 0.116, calibration intercept −0.02, slope 0.985.
  - The correction is a pure shift on the logit scale: it repairs the intercept, never the slope. Re-check on held-out data. For trees and boosting, fit a Platt or isotonic map on a separate calibration split instead (scikit-learn ≥ 1.6: `CalibratedClassifierCV(FrozenEstimator(model), method="sigmoid")` with `from sklearn.frozen import FrozenEstimator`; as of 2026-09-30).
- **Assumptions of the test itself:** ECE depends on the number of bins and the binning rule and is noisy with few events per bin, so report both and treat slope and intercept as the primary tests; subgroups need a minimum size fixed in advance; the recalibration map and its evaluation use different rows.
- **Run it:** `python scripts/calibration_report.py --data preds.csv --y flipped --p p_flip --group party --bins 10 --strategy quantile --prior-train 0.5 --prior-target 0.08` (a non-finite `p` is refused as a usage error).
  Hand check of slope and intercept (`y` is a 0/1 array, `p` the predictions):
```python
import numpy as np
import statsmodels.api as sm

p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6); lp = np.log(p / (1 - p))
binom = sm.families.Binomial()
slope = sm.GLM(y, sm.add_constant(lp), family=binom).fit().params[1]          # ideal 1
citl = sm.GLM(y, np.ones_like(lp), family=binom, offset=lp).fit().params[0]   # ideal 0
```
  R alternatives: `probably::cal_plot_breaks()`, `yardstick::brier_class()`.
- **Pass criterion (fix before running; script defaults shown):** Brier below the base rate with the paired interval excluding 0; |intercept| ≤ 0.2 logit units (`--max-intercept`); slope within [0.8, 1.2] (`--slope-lo`, `--slope-hi`); ECE ≤ 0.05 (`--max-ece`); calibration-in-the-large within tolerance in every group with at least 50 rows and both outcomes (`--min-group-n`). A model no better than the base rate on Brier, or with AUC ≤ 0.5, is KILLED (a candidate until a second independent reader confirms it).
- **Failure signature:** mean prediction far above the observed rate (class weights); slope below 1; high AUC with poor calibration; calibration that differs by party or Congress; error concentrated in the tail where the allocator acts.
- **Source:** Brier (1950); Murphy (1973); Cox (1958); Niculescu-Mizil & Caruana (2005); Guo et al. (2017); Van Calster et al. (2019); Saerens et al. (2002).

### 2.5 Distribution shift across periods, and monitoring
- **Tests:** whether what was learned still holds where the model is used. Kinds of shift (Moreno-Torres et al. 2012): covariate shift (new members, new issue areas, redrawn constituencies); prior shift (base rates move with the agenda or party control); concept shift (realignment: the same features now predict something else). Name the regime changes in the window before testing: a new Congress, redistricting (`geospatial.md` §2.6), rule or disclosure-threshold changes, collector or API changes.
- **Assumptions of the test itself:** each deployment period is large enough for its own metrics; the two-sample classifier uses the model's own features.
- **Run it:** per-period Brier, AUC and calibration intercept from the forward-chaining loop in 2.2, then a two-sample classifier ("can a model tell the periods apart?"):
```python
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import cross_val_score

def shift_auc(X_train, X_deploy, seed=0):
    """Can a classifier tell the periods apart? About 0.5 means similar covariates."""
    Z = np.vstack([X_train, X_deploy])
    s = np.r_[np.zeros(len(X_train)), np.ones(len(X_deploy))]
    clf = HistGradientBoostingClassifier(random_state=seed)
    return cross_val_score(clf, Z, s, cv=5, scoring="roc_auc").mean()
```
  Inspect the features that separate the periods; a feature that encodes the period itself is also a leakage suspect (2.1).
- **Pass criterion (fix before running):** the model wins, and keeps its sign, in at least `--min-window-share` of windows (default 0.75), each period a window; newest-period calibration intercept within ±0.2 logit units, or recalibrated with the correction in 2.4; two-sample AUC below a bound set in advance (for example 0.6) or its separating features explained.
- **Failure signature:** fine pooled, poor in the newest period; mean prediction drifting away from the observed rate (prior shift); two-sample AUC near 1.
- **Monitoring:** write the triggers (new Congress, new maps, rule changes, source changes) and a response ladder (overlay, recalibrate, redevelop) into the model card; `regulatory.md` maps this to model-risk guidance.
- **Source:** Moreno-Torres et al. (2012); Tashman (2000); Gibbs & Candès (2021).

### 2.6 ML predictions used as variables downstream
- **Tests:** whether a regression, aggregate or frontier built on predicted labels (stance, sentiment, topic, industry codes, imputed values) has unbiased estimates and honest intervals. Plugging in surrogate labels biases estimates and invalidates intervals even at 80-90% accuracy (Egami et al. 2023); misclassification bias can take either sign when errors correlate with covariates (Fong & Tyler 2021; TeBlunthuis et al. 2024).
- **Assumptions of the test itself:** a gold subsample exists, drawn with known, recorded probabilities, coded by at least two people with reliability reported; imperfect gold distorts validation (Song et al. 2020).
- **Run it:** first a differential-error check on the gold set (compute `err = y_true - y_pred`; gold items are nested in members): `Rscript scripts/regression_report.R --data gold.csv --formula "err ~ party + chamber" --cluster member_id`. Then re-estimate the downstream quantity with design-based supervised learning or prediction-powered inference (Egami et al. 2023; Angelopoulos et al. 2023). Gold-set design, packages and reliability rules: `social-science.md`.
- **Pass criterion (fix before running):** no material association of the error with the downstream covariates, and the corrected estimate keeps the naive sign → SURVIVES; same sign but the corrected interval includes 0 → WOUNDED; sign flips → KILLED, a candidate until a second independent reader confirms it.
- **Failure signature:** no gold set, or one drawn by convenience or active learning with unrecorded probabilities; naive standard errors; label accuracy that differs by party; one model output used both to select items and to measure them.
- **Source:** Egami et al. (2023); Angelopoulos et al. (2023); Fong & Tyler (2021); Knox et al. (2022); TeBlunthuis et al. (2024); Song et al. (2020).

### 2.7 Double/debiased ML and conformal prediction
**Double/debiased ML (DML).** Flexible learners predict the outcome and the treatment from the controls; the effect comes from the cross-fitted residuals through a Neyman-orthogonal score (Chernozhukov et al. 2018). Causal forests estimate heterogeneous effects (Wager & Athey 2018). DML adjusts flexibly for *observed* confounders; it does not supply identification.
- **Assumptions of the test itself:** unconfoundedness given the controls; overlap (treatment propensities away from 0 and 1); nuisance learners accurate enough; cross-fitting folds that respect groups.
- **Run it:** `DoubleML` and `grf` (R), `DoubleML` and `econml` (Python) (needs these packages). Fallback, partialling-out with cross-fitting (`X` controls, `d` treatment, `member` groups):
```python
import statsmodels.api as sm
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GroupKFold, cross_val_predict

folds = list(GroupKFold(n_splits=5).split(X, y, groups=member))
rf = RandomForestRegressor(n_estimators=300, min_samples_leaf=5, random_state=0)
ry = y - cross_val_predict(rf, X, y, cv=folds)     # cross-fitted outcome residual
rd = d - cross_val_predict(rf, X, d, cv=folds)     # cross-fitted treatment residual
fit = sm.OLS(ry, rd).fit(cov_type="cluster", cov_kwds={"groups": member})
print(fit.params[0], fit.bse[0])                    # partialling-out estimate of theta
```
  On synthetic data with a nonlinear confounder and true θ = 0.5, this returned 0.48 (SE 0.02) while naive OLS returned 0.99.
- **Pass criterion (fix before running):** the same sign, within one standard error, across at least two learner families (forest, lasso, boosting); binary-treatment propensities inside [0.01, 0.99] or trimming reported; heterogeneity claims pass `grf::test_calibration()`; sensitivity to unobserved confounding handled in `social-science.md`.
- **Failure signature:** the estimate depends on the learner; extreme propensities; no cross-fitting; "the ML controls for everything" wording.

**Conformal prediction.** Split-conformal intervals cover at least 1 − α on average when calibration and test points are exchangeable (Lei et al. 2018; Angelopoulos & Bates 2023). Time-ordered political data rarely are: use weighted (Barber et al. 2023) or adaptive (Gibbs & Candès 2021) variants and check coverage by period.
- **Run it:** `MAPIE` or `crepes` (Python), `probably::int_conformal_split()` (R), or by hand:
```python
import numpy as np

r = np.abs(y_cal - model.predict(X_cal)); n = r.size
q = np.quantile(r, min(1.0, np.ceil((n + 1) * 0.9) / n), method="higher")
lo, hi = model.predict(X_test) - q, model.predict(X_test) + q
coverage = np.mean((y_test >= lo) & (y_test <= hi))  # also by period and subgroup
```
  On exchangeable synthetic data coverage was 0.90; after adding a drift to the test outcomes it fell to 0.58. Interval backtests (PICP, width, Kupiec and Christoffersen tests): `python scripts/backtest_eval.py --data oos.csv --actual y --forecast yhat --time period --lower lo --upper hi --level 0.9`.
- **Pass criterion (fix before running):** Kupiec not rejecting at the pre-set `--alpha` (script default 0.10), overall and within each period or major subgroup that has at least `--min-n` points (default 8); the script prints KILLED when the test rejects with coverage below `--level` (intervals too narrow).
- **Failure signature:** coverage fine pooled but low for new members, new issue areas or the newest period; intervals built from training residuals.
- **Source:** Chernozhukov et al. (2018); Wager & Athey (2018); Lei et al. (2018); Angelopoulos & Bates (2023); Barber et al. (2023); Gibbs & Candès (2021).

### 2.8 Attribution claims: SHAP and permutation importance
- **Tests:** whether a "driver", "importance" or "reason" statement is supported. SHAP allocates one model output relative to a background distribution under a chosen masking rule (Lundberg & Lee 2017); it describes the model, not the world.
  - Attribution is not causation: a feature can take credit because it proxies a confounder, and changing it need not change the outcome.
  - With correlated features, credit is split in ways that change with the background, the masker and the fit; permutation importance evaluates the model on feature combinations that never occur (Hooker et al. 2021).
  - Mean |SHAP| is not an effect size, and mean signed attributions cancel across subgroups.
- **Assumptions of the test itself:** the explained model is the evaluated one (same preprocessing, version and output scale: probability, logit or margin); explanations use held-out rows.
- **Run it:** rank stability across grouped folds plus a correlated-pair screen:
```python
import numpy as np
from scipy.stats import kendalltau
from sklearn.base import clone
from sklearn.inspection import permutation_importance
from sklearn.model_selection import GroupKFold

imps = []
for tr, te in GroupKFold(n_splits=5).split(X, y, groups=member):
    m = clone(model).fit(X[tr], y[tr])
    imps.append(permutation_importance(m, X[te], y[te], n_repeats=10, random_state=0,
                                       scoring="neg_brier_score").importances_mean)
taus = [kendalltau(imps[0], v).statistic for v in imps[1:]]  # rank agreement across folds
corr = np.corrcoef(X, rowvar=False)
pairs = np.argwhere(np.triu(np.abs(corr) > 0.8, 1))          # share credit within these
```
  With `shap` installed (needs shap): confirm additivity (`base_values + values.sum(axis=1)` equals the explained output), repeat with a second background sample, and report grouped attributions for correlated clusters.
- **Pass criterion (fix before running):** top-k ranking stable across folds (for example Kendall tau ≥ 0.7); correlated features reported as groups; no causal verbs in any surface text.
- **Failure signature:** "feature X drives flips" on a dashboard; rankings that reorder between folds (on synthetic data with a pair correlated at 0.99, fold-to-fold Kendall tau ranged from 0.33 to 0.67); a leaked feature at the top (back to 2.1); SHAP computed on training rows with a training background.
- **Source:** Lundberg & Lee (2017); Hooker et al. (2021); Mullainathan & Spiess (2017); Hofman et al. (2021).

### 2.9 Bayesian workflow checks
- **Tests:** whether the posterior was computed correctly and the model reproduces the data it claims to describe (Gelman et al. 2020; Gabry et al. 2019). In order:
  - prior predictive simulation: the priors imply plausible data;
  - convergence: rank-normalized R-hat < 1.01 (flag ≥ 1.01), bulk and tail ESS ≥ 400, no post-warmup divergences (Vehtari et al. 2021);
  - posterior predictive checks on the statistic the decision uses, not only the mean;
  - PSIS-LOO with Pareto k; k > 0.7 flags observations where the estimate is unreliable (Vehtari et al. 2017);
  - prior sensitivity for decision-relevant parameters, and parameter recovery on data simulated from known values.
- **Assumptions of the test itself:** diagnostics come from the same run that produced the reported posterior; fitting or refitting the owner's model is owner-gated.
- **Run it:** (needs arviz; not run in this build; ArviZ 1.x API as of 2026-09-30)
```python
import arviz as az
s = az.summary(idata, round_to="none")          # r_hat, ess_bulk, ess_tail per parameter
flagged = s[(s["r_hat"] >= 1.01) | (s["ess_bulk"] < 400) | (s["ess_tail"] < 400)]
n_div = int(idata.sample_stats.diverging.sum().item())
k = az.loo(idata, pointwise=True).pareto_k.values   # k > 0.7: LOO unreliable there
```
  Without arviz, ask the owner for the saved diagnostics and mark the check UNVERIFIED-HERE.
- **Pass criterion (fix before running):** all convergence rules met; the decision statistic inside its 90% posterior predictive interval; no Pareto k above 0.7, or those observations examined.
- **Failure signature:** divergences hidden by raising `target_accept`; a key posterior identical to its prior (not identified by the data); a posterior predictive check that matches the mean but misses the tails that drive decisions.
- **Source:** Gelman et al. (2020); Gabry et al. (2019); Vehtari et al. (2017, 2021).

### 2.10 LLM components
- **Tests:** whether an LLM step (labelling, extraction, summarizing, scoring) is replayable, stable and faithful.
  - Annotation quality varies by task and codebook and must be validated per task (Halterman & Keith 2026).
  - Defensible model and prompt choices can flip conclusions: replicating 37 annotation tasks, about 31% of hypotheses reached wrong conclusions with state-of-the-art models (Baumann et al. 2025).
  - Prompt paraphrases change labels; score prompt stability (Barrie et al. 2024).
  - Proprietary models change silently and need explicit justification (Palmer et al. 2024); report with a checklist (Feuerriegel et al. 2026).
- **Assumptions of the test itself:** the probe panel and the confabulation sample are random draws from production inputs, with the sampling rule recorded.
- **Run it:** log model ID and snapshot date, prompt hash, temperature, seed and input hash for every call; re-run a frozen probe panel on a schedule; run the prompt in several paraphrases and on at least two models; sample outputs and check each claim against the source records:
```python
from itertools import combinations
from sklearn.metrics import cohen_kappa_score
from statsmodels.stats.proportion import proportion_confint

kappa = {(a, b): cohen_kappa_score(labels[a], labels[b])   # labels: {prompt variant: array}
         for a, b in combinations(sorted(labels), 2)}
lo, hi = proportion_confint(n_unsupported, n_sampled, alpha=0.05, method="wilson")
```
- **Pass criterion (fix before running; the owner sets the numbers):** every call replayable from logs; probe-panel and paraphrase agreement at or above the chosen kappa (for example 0.8); upper Wilson bound of the confabulation rate at or below the owner's tolerance; conclusions unchanged across model and prompt variants.
- **Failure signature:** a vendor alias such as "latest"; labels that change after a silent model update; accuracy that differs by party, chamber or gender; validation that is one LLM agreeing with another.
- **Governance:** NIST AI 600-1 (confabulation, value-chain integrity, provenance) is mapped in `regulatory.md`; validity of LLM labels as measures is in `social-science.md`.
- **Source:** Halterman & Keith (2026); Baumann et al. (2025); Barrie et al. (2024); Palmer et al. (2024); Feuerriegel et al. (2026).

## 3. Checklist

- **ML-01** Name the claim: out-of-sample prediction, or an effect. Route effects to `social-science.md`; strip causal wording from predictive models. `CAUSAL` · 2.8
- **ML-02** Fill a REFORMS-style information sheet (data, splits, preprocessing, tuning, metrics, intended use) before testing. `DATA` · 2.1
- **ML-03** Run `scripts/leakage_audit.py` on every train/test pair behind a reported number. `DATA` · 2.1
- **ML-04** Compare every feature's availability time with the prediction time, including text, labels and amended data (`--available-at`). `DATA` · 2.1
- **ML-05** Explain every feature whose single-feature AUC or R² reaches the leak threshold. `DATA` · 2.1
- **ML-06** Split by entity when the claim concerns new entities. `STATISTICAL` · 2.2
- **ML-07** Split forward in time, with an embargo at least as long as the reporting lag, when the claim concerns the future. `STATISTICAL` · 2.2
- **ML-08** Fit every learned transformation (scaling, imputation, encoding, selection, resampling, target encoding) inside the training fold. `DATA` · 2.2
- **ML-09** Tune and set thresholds only inside training folds; report nested or untouched-holdout performance and the optimism gap. `STATISTICAL` · 2.2
- **ML-10** Report per-fold and per-period scores with their spread, and the number of independent units next to the row count. `STATISTICAL` · 2.2
- **ML-11** Score the base-rate, majority, party-line and last-period baselines on the same rows. `DECISION` · 2.3
- **ML-12** Give the improvement as a paired loss difference with a cluster-bootstrap interval, or a Diebold-Mariano or Clark-West test for forecasts scored by period; require that the model wins, and keeps its sign, in at least `--min-window-share` of windows (default 0.75). `STATISTICAL` · 2.3, `scripts/backtest_eval.py`
- **ML-13** Score probabilities with proper rules (Brier, log loss); show accuracy only next to the majority baseline. `MEASUREMENT` · 2.3, 2.4
- **ML-14** Run `scripts/calibration_report.py` before any probability drives money, a threshold or an expected count. `MEASUREMENT` · 2.4
- **ML-15** Report calibration slope and intercept with the reliability table; state bins and strategy for ECE. `MEASUREMENT` · 2.4
- **ML-16** Check calibration and discrimination per party, chamber and period, with a minimum group size fixed in advance. `MEASUREMENT` · 2.4 (`--group`)
- **ML-17** Where class weights or resampling were used, apply the prior-shift correction or recalibrate, then re-check. `MEASUREMENT` · 2.4 (`--prior-train`, `--prior-target`)
- **ML-18** Fit any recalibration map on rows not used to evaluate it. `STATISTICAL` · 2.4
- **ML-19** Report performance per period and list the regime changes in the window (new Congress, redistricting, rule or source changes). `STATISTICAL` · 2.5
- **ML-20** Run a two-sample classifier between training and deployment data; explain the separating features. `DATA` · 2.5
- **ML-21** Record monitoring triggers and the response ladder in the model card. `DECISION` · 2.5, `regulatory.md`
- **ML-22** Treat reused predictions as error-prone measurements: gold subsample with known probabilities, differential-error check, DSL or PPI. `MEASUREMENT` · 2.6
- **ML-23** For DML, confirm cross-fitting, overlap and learner robustness, and state the identifying assumption separately. `CAUSAL` · 2.7
- **ML-24** Check interval coverage by period and subgroup; use weighted or adaptive conformal under drift. `STATISTICAL` · 2.7
- **ML-25** Check attribution rank stability across folds and backgrounds, group correlated features, and remove causal wording. `CAUSAL` · 2.8
- **ML-26** For Bayesian models, require the convergence rules, a posterior predictive check on the decision statistic and a Pareto-k screen. `COMPUTATIONAL` · 2.9
- **ML-27** Pin LLM model snapshot, prompt hash and decoding settings; replay a frozen probe panel on a schedule. `COMPUTATIONAL` · 2.10
- **ML-28** Measure prompt and model sensitivity of every LLM-derived measure. `MEASUREMENT` · 2.10
- **ML-29** Sample LLM outputs for confabulation against source records; report the rate with a Wilson interval. `MEASUREMENT` · 2.10
- **ML-30** Prove the detectors can fail: plant a leak (the target copied into a feature) and a miscalibration (probabilities squared) in copies of the data, confirm the scripts flag both and a clean control passes (`scripts/mutation_check.py` automates mutants). `COMPUTATIONAL`
- **ML-31** Re-run training with the same seed and data and confirm identical outputs; record library versions (`automation.md`). `COMPUTATIONAL`

## 4. Pitfalls and anti-patterns

- Random row-level CV on panel or repeated-measures data; the same entity on both sides of the split.
- Scaling, imputing, selecting features or oversampling before the split.
- Tuning on the backtest window, quoting `best_score_`, or choosing the decision threshold on the test set.
- Feeding balanced-weight or SMOTE probabilities straight into an allocator or an expected-count sum.
- AUC alone for scores that are used as probabilities; accuracy alone on imbalanced classes.
- ECE from ten equal-width bins with a handful of events each, reported as precise; calibrating and checking calibration on the same rows.
- Calling a random split from one period "external validation". External means another period, place or population, with the locked model applied without refitting.
- Median-imputing inputs that are missing not at random, which makes unknown units look typical; report results with and without the imputed rows.
- Picking the best of many models or specifications on one holdout and reporting it without correction (`finance.md` for backtest overfitting; `core-statistics.md` for multiplicity).
- Reading importance or SHAP as levers; explaining a model on its own training rows.
- Regressions on predicted labels with naive standard errors.
- LLM "latest" aliases, unlogged prompts, and validation by agreement between LLMs.
- Time-to-event models (time to retirement, defection or passage): censoring-unaware metrics; Harrell's C under heavy censoring instead of Uno's IPCW C with a horizon chosen in advance (Uno et al. 2011); event-specific risk estimated as 1 − Kaplan-Meier when competing events exist (retirement versus defeat); calibration checked only in aggregate rather than at a fixed horizon.
- Assuming a deeper or boosted model must be better; run 2.3 first.

## 5. References

Verified in the research files (CrossRef or OpenAlex), except items marked [this build], which were checked against CrossRef (CR) or OpenAlex (OA) on 2026-09-30 while writing this module.

- Angelopoulos, A. N., & Bates, S. (2023). Conformal prediction: a gentle introduction. *Foundations and Trends in Machine Learning* 16(4), 494-591. doi:10.1561/2200000101
- Angelopoulos, A. N., Bates, S., Fannjiang, C., Jordan, M. I., & Zrnic, T. (2023). Prediction-powered inference. *Science* 382(6671), 669-674. doi:10.1126/science.adi6000
- Barber, R. F., Candès, E. J., Ramdas, A., & Tibshirani, R. J. (2023). Conformal prediction beyond exchangeability. *Annals of Statistics* 51(2). doi:10.1214/23-aos2276
- Barrie, C., Palaiologou, E., & Törnberg, P. (2024). Prompt stability scoring for text annotation with large language models. arXiv preprint. doi:10.48550/arXiv.2407.02039
- Baumann, J., Röttger, P., Urman, A., Wendsjö, A., Plaza-del-Arco, F. M., Gruber, J. B., & Hovy, D. (2025). Large language model hacking: quantifying the hidden risks of using LLMs for text annotation. arXiv preprint. doi:10.48550/arXiv.2509.08825
- Bergmeir, C., & Benítez, J. M. (2012). On the use of cross-validation for time series predictor evaluation. *Information Sciences* 191, 192-213. doi:10.1016/j.ins.2011.12.028
- Bergmeir, C., Hyndman, R. J., & Koo, B. (2018). A note on the validity of cross-validation for evaluating autoregressive time series prediction. *Computational Statistics & Data Analysis* 120, 70-83. doi:10.1016/j.csda.2017.11.003
- Brier, G. W. (1950). Verification of forecasts expressed in terms of probability. *Monthly Weather Review* 78(1), 1-3. doi:10.1175/1520-0493(1950)078<0001:VOFEIT>2.0.CO;2
- Cerqueira, V., Torgo, L., & Mozetič, I. (2020). Evaluating time series forecasting models: an empirical study on performance estimation methods. *Machine Learning* 109(11), 1997-2028. doi:10.1007/s10994-020-05910-7
- Chernozhukov, V., Chetverikov, D., Demirer, M., Duflo, E., Hansen, C., Newey, W., et al. (2018). Double/debiased machine learning for treatment and structural parameters. *Econometrics Journal* 21(1), C1-C68. doi:10.1111/ectj.12097
- Cox, D. R. (1958). Two further applications of a model for binary regression. *Biometrika* 45(3-4), 562-565. doi:10.1093/biomet/45.3-4.562 [this build, CR]
- Diebold, F. X., & Mariano, R. S. (1995). Comparing predictive accuracy. *Journal of Business & Economic Statistics* 13(3), 253-263. doi:10.1080/07350015.1995.10524599
- Egami, N., Hinck, M., Stewart, B. M., & Wei, H. (2023). Using imperfect surrogates for downstream inference: design-based supervised learning for social science applications of large language models. *NeurIPS 36*, 68589-68601. arXiv:2306.04746
- Feuerriegel, S., Barrie, C., Crockett, M. J., Globig, L. K., McLoughlin, K. L., Mirea, D.-M., et al. (2026). A reporting checklist for large language models in behavioural science. *Nature Human Behaviour* 10(7), 1182-1186. doi:10.1038/s41562-026-02492-7
- Fong, C., & Tyler, M. (2021). Machine learning predictions as regression covariates. *Political Analysis* 29(4), 467-484. doi:10.1017/pan.2020.38
- Gabry, J., Simpson, D., Vehtari, A., Betancourt, M., & Gelman, A. (2019). Visualization in Bayesian workflow. *Journal of the Royal Statistical Society Series A* 182(2), 389-402. doi:10.1111/rssa.12378 [this build, CR]
- Gelman, A., Vehtari, A., Simpson, D., Margossian, C. C., Carpenter, B., Yao, Y., et al. (2020). Bayesian workflow. arXiv preprint. doi:10.48550/arXiv.2011.01808 [this build, OA W4394649545]
- Gibbs, I., & Candès, E. J. (2021). Adaptive conformal inference under distribution shift. *NeurIPS 34*. arXiv:2106.00170
- Gneiting, T., & Raftery, A. E. (2007). Strictly proper scoring rules, prediction, and estimation. *Journal of the American Statistical Association* 102(477), 359-378. doi:10.1198/016214506000001437
- Grimmer, J., Roberts, M. E., & Stewart, B. M. (2021). Machine learning for social science: an agnostic approach. *Annual Review of Political Science* 24, 395-419. doi:10.1146/annurev-polisci-053119-015921
- Guo, C., Pleiss, G., Sun, Y., & Weinberger, K. Q. (2017). On calibration of modern neural networks. *ICML 2017, PMLR* 70, 1321-1330. arXiv:1706.04599
- Halterman, A., & Keith, K. A. (2026). Codebook LLMs: evaluating LLMs as measurement tools for political science concepts. *Political Analysis* 34(2), 188-204. doi:10.1017/pan.2025.10017
- Hofman, J. M., Watts, D. J., Athey, S., Garip, F., Griffiths, T. L., Kleinberg, J., et al. (2021). Integrating explanation and prediction in computational social science. *Nature* 595(7866), 181-188. doi:10.1038/s41586-021-03659-0
- Hooker, G., Mentch, L., & Zhou, S. (2021). Unrestricted permutation forces extrapolation: variable importance requires at least one more model, or there is no free variable importance. *Statistics and Computing* 31(6). doi:10.1007/s11222-021-10057-z [this build, CR]
- Kapoor, S., & Narayanan, A. (2023). Leakage and the reproducibility crisis in machine-learning-based science. *Patterns* 4(9), 100804. doi:10.1016/j.patter.2023.100804
- Kapoor, S., Cantrell, E. M., Peng, K., Pham, T. H., Bail, C. A., Gundersen, O. E., et al. (2024). REFORMS: consensus-based recommendations for machine-learning-based science. *Science Advances* 10(18), eadk3452. doi:10.1126/sciadv.adk3452
- Knox, D., Lucas, C., & Cho, W. K. T. (2022). Testing causal theories with learned proxies. *Annual Review of Political Science* 25, 419-441. doi:10.1146/annurev-polisci-051120-111443
- Lei, J., G'Sell, M., Rinaldo, A., Tibshirani, R. J., & Wasserman, L. (2018). Distribution-free predictive inference for regression. *Journal of the American Statistical Association* 113(523), 1094-1111. doi:10.1080/01621459.2017.1307116
- Lundberg, S. M., & Lee, S.-I. (2017). A unified approach to interpreting model predictions. *NeurIPS 30*. arXiv:1705.07874, doi:10.48550/arXiv.1705.07874 [this build, OA W2618851150]
- Moreno-Torres, J. G., Raeder, T., Alaiz-Rodríguez, R., Chawla, N. V., & Herrera, F. (2012). A unifying view on dataset shift in classification. *Pattern Recognition* 45(1), 521-530. doi:10.1016/j.patcog.2011.06.019
- Mullainathan, S., & Spiess, J. (2017). Machine learning: an applied econometric approach. *Journal of Economic Perspectives* 31(2), 87-106. doi:10.1257/jep.31.2.87
- Murphy, A. H. (1973). A new vector partition of the probability score. *Journal of Applied Meteorology* 12(4), 595-600. doi:10.1175/1520-0450(1973)012<0595:ANVPOT>2.0.CO;2 [this build, CR]
- Naeini, M. P., Cooper, G., & Hauskrecht, M. (2015). Obtaining well calibrated probabilities using Bayesian binning. *Proceedings of the AAAI Conference on Artificial Intelligence* 29(1). doi:10.1609/aaai.v29i1.9602 [this build, CR]
- Niculescu-Mizil, A., & Caruana, R. (2005). Predicting good probabilities with supervised learning. *Proceedings of ICML 2005*, 625-632. doi:10.1145/1102351.1102430
- Palmer, A., Smith, N. A., & Spirling, A. (2024). Using proprietary language models in academic research requires explicit justification. *Nature Computational Science* 4(1), 2-3. doi:10.1038/s43588-023-00585-1
- Roberts, D. R., Bahn, V., Ciuti, S., Boyce, M. S., Elith, J., Guillera-Arroita, G., et al. (2017). Cross-validation strategies for data with temporal, spatial, hierarchical, or phylogenetic structure. *Ecography* 40(8), 913-929. doi:10.1111/ecog.02881
- Saerens, M., Latinne, P., & Decaestecker, C. (2002). Adjusting the outputs of a classifier to new a priori probabilities: a simple procedure. *Neural Computation* 14(1), 21-41. doi:10.1162/089976602753284446 [this build, CR]
- Salganik, M. J., Lundberg, I., Kindel, A. T., Ahearn, C. E., Al-Ghoneim, K., Almaatouq, A., et al. (2020). Measuring the predictability of life outcomes with a scientific mass collaboration. *PNAS* 117(15), 8398-8403. doi:10.1073/pnas.1915006117 (correction notice)
- Song, H., Tolochko, P., Eberl, J.-M., Eisele, O., Greussing, E., Heidenreich, T., et al. (2020). In validations we trust? The impact of imperfect human annotations as a gold standard on the quality of validation of automated content analysis. *Political Communication* 37(4), 550-572. doi:10.1080/10584609.2020.1723752
- Tashman, L. J. (2000). Out-of-sample tests of forecasting accuracy: an analysis and review. *International Journal of Forecasting* 16(4), 437-450. doi:10.1016/S0169-2070(00)00065-0
- TeBlunthuis, N., Hase, V., & Chan, C.-H. (2024). Misclassification in automated content analysis causes bias in regression. Can we fix it? Yes we can! *Communication Methods and Measures* 18(3), 278-299. doi:10.1080/19312458.2023.2293713
- Uno, H., Cai, T., Pencina, M. J., D'Agostino, R. B., & Wei, L. J. (2011). On the C-statistics for evaluating overall adequacy of risk prediction procedures with censored survival data. *Statistics in Medicine* 30(10), 1105-1117. doi:10.1002/sim.4154 [this build, CR]
- Van Calster, B., McLernon, D. J., van Smeden, M., Wynants, L., & Steyerberg, E. W. (2019). Calibration: the Achilles heel of predictive analytics. *BMC Medicine* 17(1), 230. doi:10.1186/s12916-019-1466-7
- Varma, S., & Simon, R. (2006). Bias in error estimation when using cross-validation for model selection. *BMC Bioinformatics* 7, 91. doi:10.1186/1471-2105-7-91 [this build, CR]
- Vehtari, A., Gelman, A., & Gabry, J. (2017). Practical Bayesian model evaluation using leave-one-out cross-validation and WAIC. *Statistics and Computing* 27(5), 1413-1432. doi:10.1007/s11222-016-9696-4 [this build, CR] (correction notice)
- Vehtari, A., Gelman, A., Simpson, D., Carpenter, B., & Bürkner, P.-C. (2021). Rank-normalization, folding, and localization: an improved R-hat for assessing convergence of MCMC. *Bayesian Analysis* 16(2). doi:10.1214/20-BA1221 [this build, CR]
- Wager, S., & Athey, S. (2018). Estimation and inference of heterogeneous treatment effects using random forests. *Journal of the American Statistical Association* 113(523), 1228-1242. doi:10.1080/01621459.2017.1319839
- Ward, M. D., Greenhill, B. D., & Bakke, K. M. (2010). The perils of policy by p-value: predicting civil conflicts. *Journal of Peace Research* 47(4), 363-375. doi:10.1177/0022343309356491

**Adapted from** (ideas paraphrased; no text or code copied): K-Dense-AI scientific-agent-skills (MIT) — `scikit-learn/SKILL.md`, `scikit-learn/references/model_evaluation.md`; `scikit-survival/SKILL.md`, `scikit-survival/references/evaluation-metrics.md`; `shap/SKILL.md`, `shap/references/theory.md`; `pymc/SKILL.md`, `pymc/references/standard_workflow.md`, `pymc/scripts/model_comparison.py` (for the ArviZ 1.x call names); `exploratory-data-analysis/SKILL.md`, `exploratory-data-analysis/scripts/missingness_leakage_audit.py`; `clinical-decision-support/references/model_biomarker_evaluation.md`.
