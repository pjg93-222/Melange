# Core statistics — quant-model-evaluation reference

> **Load when:** a claim rests on a regression, a trend, a hypothesis test, an interval, a simulation summary or a before/after comparison of two pipelines; and whenever you decide how a result is reported (this file owns the presentation contract, §2.14). **Not for:** identification designs and measurement validity (`social-science.md`); backtest protocols and money data (`finance.md`); classifier calibration and leakage (`machine-learning.md`); spatial dependence (`geospatial.md`); simulation engines and V&V (`engineering-simulation.md`); charts and dashboards (`data-visualization.md`).
> Facts marked (as of DATE) are time-sensitive; re-verify before relying on them. `[RUN]` marks behaviour reproduced on synthetic data when this file was written (2026-09-30; Python 3.12.10, statsmodels 0.14.6, NumPy 2.4.6; R 4.6.0).

## 1. Assumption map

| Assumption (class) | Where it usually hides | What breaks if it is false | Tests |
|---|---|---|---|
| The target quantity is defined: quantity, population, unit, window (CAUSAL, MEASUREMENT) | Prose, variable names, a dashboard caption | The analysis answers a different question from the one reported | §2.1 |
| No rival explanation fits the same data (CAUSAL) | Observational "effects", before/after comparisons | A confounded or reverse-caused association is sold as an effect | §2.1, `scripts/confounding_sensitivity.py` |
| The mean function is linear and additive as written (FUNCTIONAL-FORM) | `lm()` formulas, response curves, interaction terms | Biased slopes; marginal effects wrong outside the data's support | §2.2 |
| Error variance is constant (STATISTICAL) | The classical SEs that `summary(lm())` prints | Intervals too narrow or too wide | §2.3 |
| Observations are independent given the model (STATISTICAL) | Panels, repeated units, votes nested in legislators, firms in sectors | SEs shrink as rows are added; false positives | §2.4 |
| Errors are near-normal (STATISTICAL) | Small-sample t and F tests | Small-n p-values and intervals miscalibrated | §2.3 |
| Regressors are not (near-)collinear and the design is not saturated (COMPUTATIONAL) | Dummy sets, derived features, one-hot encodings, cell-mean designs | Aliased terms dropped or split arbitrarily; no residual df | §2.5 |
| No single unit drives the result (DATA) | Large donors, one outlier cycle, one dominant sector | A fragile headline | §2.5 |
| The specification was fixed before results were seen (STATISTICAL) | Stepwise selection, specification searches, window picking | Invalid p-values; exaggerated effects | §2.6, §2.8 |
| Series are stationary or cointegrated, parameters stable (STATISTICAL) | Level regressions of money on time or on other trending money | Spurious significance; a pooled slope that describes no period | §2.7 |
| The design has power for the effect claimed (STATISTICAL) | Short backtests, small panels, subgroup estimates | Exaggerated or wrong-signed trends; nulls misread as absence | §2.9 |
| Uncertainty is carried through to the output (COMPUTATIONAL) | Composite scores, point forecasts, simulation outputs | Overconfident decisions | §2.10 |
| A pipeline change left the answer unchanged (COMPUTATIONAL) | Refactors, migrations, new data vintages | "No significant difference" read as agreement | §2.11 |
| Missingness is ignorable or handled (DATA) | `dropna()`, fill-with-median, zero-filled money | Biased estimates; guesses treated as data | §2.12 |
| MCMC converged and the model reproduces the data (COMPUTATIONAL) | Bayesian fits summarized from one run | Posterior summaries that describe the sampler, not the data | §2.13 |
| The output says what the number is (PRESENTATION) | Headlines, tables, tooltips | Misread units, windows, strength of evidence | §2.14 |

## 2. Tests

### 2.1 Estimand first, then rival explanations and negative controls
- **Tests:** whether the reported number answers a defined question, and whether a non-causal explanation could produce it.
- **Assumptions of the test itself:** the owner can name the decision the number feeds; a negative control shares the main analysis's bias pathways but cannot act through the claimed mechanism.
- **Run it:**
  - Before opening results, write the estimand: quantity (difference, slope, share, rank), population, unit of analysis, window and contrast (Lundberg et al. 2021). Classify the claim as descriptive, associational, predictive or causal; `social-science.md` owns identification.
  - List rivals from different classes (confounding, selection or survivorship, reverse causation, measurement artefact, regression to the mean, chance) and, for each, one observation that would tell it apart.
  - Run at least one negative-control outcome or exposure (Lipsitch et al. 2010), e.g. the spending model "predicting" votes cast before the money arrived.
  - Bound unobserved confounding: `python scripts/confounding_sensitivity.py --mode sensemakr --estimate 0.42 --se 0.11 --dof 480` (your coefficient, its SE and residual df; Cinelli & Hazlett 2020), or `--mode evalue --rr 1.8 --lo 1.2 --hi 2.6`; set `--rv-min` or `--e-min` from the strongest observed confounder before running.
  - Audit covariate timing: a control measured after treatment biases the estimate (Montgomery et al. 2018).
  - Review in this order: target quantity, design and unit, sampling, power, missingness, analysis-design fit, multiplicity, estimates and denominators, causal reach.
- **Pass criterion (fix before running):** a written estimand that matches the reported number; every causal claim has a named design or is worded as association; negative controls null within their intervals.
- **Failure signature:** the headline changes meaning once unit or window is explicit; the negative control is as large as the effect; the effect appears only after adding post-treatment controls; a regression with a dozen controls offered as a design (Achen 2005). OLS with controls weights units by their conditional treatment variance, so the effective sample can differ from the nominal one (Aronow & Samii 2016).
- **Source:** Lundberg, Johnson & Stewart (2021); Lipsitch, Tchetgen Tchetgen & Cohen (2010); Montgomery, Nyhan & Torres (2018); Achen (2005); Aronow & Samii (2016); Cinelli & Hazlett (2020).

### 2.2 Functional form: RESET, partial residuals, interactions
- **Tests:** whether the mean function misses curvature, thresholds or saturation.
- **Assumptions of the test itself:** RESET detects curvature that correlates with fitted values, cannot say which regressor is wrong, and flags trivial curvature at large n, so read it with the plots.
- **Run it:**
  - RESET: Python `from statsmodels.stats.diagnostic import linear_reset; linear_reset(res, power=3, use_f=True).pvalue`; R `lmtest::resettest(fit, power = 2:3)` (needs lmtest; base-R fallback with identical F [RUN]: `f <- fitted(fit); anova(fit, update(fit, . ~ . + I(f^2) + I(f^3)))`). `scripts/regression_report.R` reports it as LM-RESET (SURVIVES at p ≥ `--alpha`, default 0.05).
  - Partial-residual plots per continuous regressor: `sm.graphics.plot_ccpr_grid(res)`; R `termplot(fit, partial.resid = TRUE)`.
  - Interactions: bin the moderator and check that the interaction is linear and that each bin has support (Hainmueller et al. 2019).
  - Money-to-outcome response curves: fit a flexible alternative (splines or bins) and compare predictions over the range where decisions are made.
- **Pass criterion (fix before running):** RESET p above the pre-set level and partial-residual smooths inside the fitted line's band over the decision range, or the flexible fit changes no decision.
- **Failure signature:** residuals curve against a regressor; marginal effects that exist only beyond observed moderator values; a saturation constant the data do not pin down.
- **Source:** Ramsey (1969); Hainmueller, Mummolo & Xu (2019).

### 2.3 Error variance and distribution: Breusch–Pagan, White, HC standard errors, normality
- **Tests:** whether the classical SEs are usable, and whether normality matters at this n.
- **Assumptions of the test itself:** Breusch–Pagan tests variance linear in the regressors; White adds squares and cross-products (weak when k is large); normality tests over-reject at large n and miss problems at small n.
- **Run it:**
  - Python `het_breuschpagan(res.resid, res.model.exog)[1]` and `het_white(res.resid, res.model.exog)[1]`; refit with `cov_type="HC3"` (small n) or `"HC1"`.
  - R `lmtest::bptest(fit)` (needs lmtest) and `sandwich::vcovHC(fit, type = "HC3")` (needs sandwich). Base-R HC3, identical to statsmodels [RUN]: `X <- model.matrix(fit); h <- hatvalues(fit); B <- solve(crossprod(X)); V <- B %*% crossprod(X * resid(fit) / (1 - h)) %*% B`.
  - Put classical and robust SEs side by side. `scripts/regression_report.R` reports LM-BP (a rejection means the classical SEs in the print are unreliable: read the inference block) and LM-HC3 (UNVERIFIED-HERE when a leverage-1 row leaves HC3 undefined; HC1 is shown instead).
- **Pass criterion (fix before running):** robust SEs used when Breusch–Pagan/White reject or the robust/classical SE ratio passes a pre-set bound (e.g. 1.5); normality judged by Q-Q plot, and only when residual df is small (under about 30).
- **Failure signature:** robust and classical SEs differ by a large factor, which signals misspecification that robust SEs do not repair (King & Roberts 2015); fan-shaped residuals; heavy-tailed residuals behind small-n intervals.
- **Source:** Breusch & Pagan (1979); White (1980); Long & Ervin (2000); King & Roberts (2015).

### 2.4 Dependence and clustering
- **Tests:** whether the SEs respect how units were sampled or treatment was assigned.
- **Assumptions of the test itself:** cluster-robust variance (CRVE) is consistent as the number of clusters G grows, not the rows, and needs clusters independent of each other.
- **Run it:**
  - Count independent units first and report N rows beside G clusters (votes nested in members and roll calls; monthly rows nested in firms); DEFF = 1 + (m − 1)·ICC shows how clustering shrinks the effective sample.
  - Cluster where treatment was assigned or units were sampled, not merely where residuals correlate (Abadie et al. 2023); cluster two ways for crossed structures such as member × roll call (Cameron, Gelbach & Miller 2011).
  - Use CR2 with Satterthwaite df at moderate G (Pustejovsky & Tipton 2018), and a wild cluster restricted bootstrap when G is small (Cameron, Gelbach & Miller 2008; MacKinnon, Nielsen & Webb 2023). The skill script does all of this:
  ```
  Rscript scripts/regression_report.R --data panel.csv --formula "y ~ x + z" \
    --cluster member --cluster2 rollcall --vcov CR2 --boot wild --B 999 --out qme_out
  ```
  - The script reports LM-UNITS: G ≥ `--min-clusters` (42) SURVIVES; below it WOUNDED (read the wild-bootstrap p and CI); below `--descriptive-below` (10) the inference is DESCRIPTIVE; with no `--cluster` it is UNVERIFIED-HERE, because one table cannot show that rows are independent. With `--cluster2`, inference uses the smaller G and the wild bootstrap runs one-way on that dimension. `--vcov CR2` needs the sandwich package (without it CR1 is shown and LM-CR2 is UNVERIFIED-HERE); LM-PARITY compares sandwich SEs with the hand-built ones. On a synthetic 30 × 12 panel the command above exited 1, with LM-UNITS WOUNDED at G = 12 [RUN].
  - Python: `smf.ols("y ~ x + z", d).fit(cov_type="cluster", cov_kwds={"groups": d["g"]})` is CR1 with the G/(G−1)·(N−1)/(N−K) factor; a hand-built base-R CR1 matches it [RUN].
- **Pass criterion (fix before running):** clustering level justified by the design; G ≥ 42 for plain CRVE, otherwise wild-bootstrap p-values reported (the script's default switch); G < 10 means the inference is labelled DESCRIPTIVE; never cluster on 2–3 groups such as party or chamber.
- **Failure signature:** SEs shrink as more rows from the same units are added (pseudoreplication; Hurlbert 1984); clustering by party, or by a handful of periods; significance that vanishes under the wild bootstrap; serial correlation within units ignored in difference-in-differences (Bertrand et al. 2004). Unbalanced cluster sizes or few treated clusters make even G ≈ 50 unreliable (MacKinnon et al. 2023).
- **Source:** Abadie et al. (2023); Cameron, Gelbach & Miller (2008, 2011); Pustejovsky & Tipton (2018); MacKinnon, Nielsen & Webb (2023); Esarey & Menger (2019); Bertrand, Duflo & Mullainathan (2004); Hurlbert (1984). The R packages `fwildclusterboot` (archived 2024-05-29) and `summclust` (archived 2025-11-02) are off CRAN (as of 2026-09-30); re-verify before relying on either.

### 2.5 Collinearity, aliasing, saturation and influence
- **Tests:** whether the coefficients are identified, and whether one unit drives them.
- **Assumptions of the test itself:** VIF measures variance inflation, not bias; influence measures delete one row at a time and can miss a cluster of influential rows.
- **Run it:**
  - Regress each regressor on the others: auxiliary R² ≥ 0.9999 (VIF ≥ 10,000) marks it aliased or near-aliased; VIF > 10 marks imprecision worth reporting.
  - R flags exact aliasing with `NA` coefficients and `alias(fit)`. statsmodels does not: it solves by pseudo-inverse and returns arbitrary offsetting coefficients (about −2.2×10⁷ and +1.1×10⁷ for a near-duplicate column, with no error [RUN]).
  - Check residual df: one parameter per cell (a saturated design) leaves nothing for inference.
  - Influence: `infl = res.get_influence(); infl.cooks_distance[0]; infl.dfbetas`; R `cooks.distance(fit)`, `dfbetas(fit)`. Refit without the 1–3 most influential units or clusters and report the change.
  - `scripts/regression_report.R` reports LM-COLLINEAR (aliased terms, or auxiliary R² ≥ `--collinear-r2`, 0.9999), LM-VIF (≤ `--vif-max`, 10), LM-COOK (max Cook's D ≤ `--cook-max`, 1; leverage-1 rows are named and count against it) and LM-LEVERAGE: a row with leverage h = 1, such as a dummy that is 1 on a single row, is fitted exactly, so robust SEs for the coefficient it identifies are unreliable (WOUNDED; reproduced on a synthetic one-row dummy [RUN]).
- **Pass criterion (fix before running):** no auxiliary R² ≥ 0.9999; no `NA` or absurd coefficients; enough residual df for the tests reported (state the floor); the headline sign survives dropping the most influential unit or cluster.
- **Failure signature:** signs flip when a correlated regressor enters; huge offsetting coefficients; `NA` rows in `summary(lm())`; one cycle, sector or donor carries the slope (max Cook's D far above the rest, |DFBETAS| > 2/√n).
- **Source:** Belsley, Kuh & Welsch (1980); Cook (1977).

### 2.6 Post-selection inference
- **Tests:** whether p-values survive the way the model was chosen.
- **Assumptions of the test itself:** classical p-values assume the model was fixed in advance; once the data chose it, the repair must repeat the choosing.
- **Run it:**
  - Ask how the specification was reached: stepwise, dropping weak terms, trying transformations or windows.
  - Planted-null demonstration: regress noise on 50 noise predictors (n = 100), keep terms with p < 0.25, refit. In one run 15 terms were kept, 11 of them "significant" at 0.05, with overall F p < 0.0001 [RUN], as Freedman (1983) showed.
  - Repairs: pre-specify; split the sample (select on one half, estimate on the other); repeat the whole selection inside every bootstrap resample and report the estimate's distribution (zero when not selected) with its selection frequency; or use simultaneous post-selection intervals (Berk et al. 2013).
- **Pass criterion (fix before running):** reported p-values come from a pre-specified model, a held-out half, or selection-repeated resampling.
- **Failure signature:** terms significant only in the final stepwise model; a headline variable selected in under about half of resamples; estimates that shrink toward zero on the held-out half.
- **Source:** Freedman (1983); Leeb & Pötscher (2005); Berk et al. (2013).

### 2.7 Time series: stationarity, spurious regression, HAC, breaks, autocorrelation
- **Tests:** whether a relationship between series over time is real and stable.
- **Assumptions of the test itself:** ADF (unit-root null) and KPSS (stationarity null) both have low power in short series, so they are read together.
- **Run it:**
  - Stationarity: `adfuller(y, autolag="AIC")[1]` and `kpss(y, regression="c", nlags="auto")[1]` (`regression="ct"` for trend-stationarity). ADF rejects and KPSS does not: stationary. ADF does not and KPSS rejects: unit root. Both or neither reject: inconclusive, report both.
  - Spurious regression: difference two trending series or test cointegration (Engle & Granger 1987). Two independent random walks regressed in levels gave t = 21.7 and R² = 0.70; in differences t = 0.7; Newey–West SEs left t = 10.8 [RUN], because HAC repairs SEs, not spuriousness (Granger & Newbold 1974).
  - Autocorrelated residuals in one series: report HAC SEs with the lag, `fit(cov_type="HAC", cov_kwds={"maxlags": L})` or `regression_report.R --vcov NW --nw-lag L --time period` (NW needs one row per period; for a panel, cluster by unit instead). Test with Durbin–Watson and Breusch–Godfrey (`acorr_breusch_godfrey(res, nlags=1)`); with `--time` the script reports LM-SERIAL, where a rejection is WOUNDED under HC1 or HC3 and SURVIVES under NW, CR1 or CR2, which cover it. Under NW, LM-UNITS is UNVERIFIED-HERE (stationarity and weak dependence are assumed, not tested), so the run exits 3 [RUN].
  - Breaks: Chow F at dates named in advance (base R `anova(lm(y ~ t), lm(y ~ t * post))`); unknown dates by sup-F (Andrews 1993) and multiple breaks (Bai & Perron 1998) via `strucchange::sctest(Fstats(y ~ x, from = 0.15))` and `breakpoints()` (needs strucchange; fallback `breaks_cusumolsresid(res.resid)` in statsmodels).
- **Pass criterion (fix before running):** stationarity stated for every series; no levels regression of trending series without a cointegration test; breaks tested at every pre-named date; no pooling across a confirmed break.
- **Failure signature:** high R² and t from trending levels; a residual ACF that decays slowly; a slope that flips across a known regime change.
- **Source:** Dickey & Fuller (1979); Kwiatkowski et al. (1992); Granger & Newbold (1974); Engle & Granger (1987); Newey & West (1987); Breusch (1978); Godfrey (1978); Chow (1960); Andrews (1993); Bai & Perron (1998). Forecast comparison and backtest design: `finance.md`.

### 2.8 Multiplicity and forking paths
- **Tests:** whether a finding is one of many tries.
- **Assumptions of the test itself:** the family can be enumerated: every outcome, subgroup, sector, window, transformation, outlier rule and model tried, reported or not.
- **Run it:**
  - Count the trials first.
  - Within each pre-declared family, control the false-discovery rate with Benjamini–Hochberg for screens (per sector, per topic); control the family-wise error with Holm's step-down or Romano–Wolf (bootstrap, allows dependence) when any single false positive is costly. Python `multipletests(p, method="fdr_bh")` or `"holm"`; R `p.adjust(p, "BH")` or `"holm"`; Romano–Wolf via `arch.bootstrap.StepM` (needs arch).
  - For headline estimates, run every defensible combination of choices and plot the sorted estimates with intervals: a specification curve or multiverse (Simonsohn et al. 2020; Steegen et al. 2016).
  - Check the analysis plan's date against the data pull and log deviations (Ofosu & Posner 2023).
  - Best-of-many forecasting models against a benchmark (reality check, SPA, deflated Sharpe ratio): `finance.md`.
- **Pass criterion (fix before running):** the number of trials is reported with the result; claims rest on adjusted p or q values; the headline sits inside the bulk of its specification curve, and at least a pre-set share of defensible specifications share its sign.
- **Failure signature:** dozens of subgroup regressions with unadjusted winners; a headline at the extreme of its own curve; defensible choices that give opposite signs, as in many-analyst studies (Breznau et al. 2022).
- **Source:** Benjamini & Hochberg (1995); Romano & Wolf (2005); Gelman & Loken (2014); Simonsohn, Simmons & Nelson (2020); Steegen et al. (2016); Breznau et al. (2022); Ofosu & Posner (2023). Holm (1979) is not cited: its record could not be verified here (§5).

### 2.9 Power, minimum detectable effect, Type M and Type S errors
- **Tests:** whether the design could detect the effect the claim is about, and how exaggerated a "significant" estimate is likely to be.
- **Assumptions of the test itself:** the plausible effect comes from outside the data being tested (credible designs, a smallest effect that matters), never from the estimate itself; "observed power" is circular and is not reported.
- **Run it:**
  - MDE ≈ (z₀.₉₇₅ + z₀.₈₀)·SE = 2.80·SE for a two-sided 5% test at 80% power.
  - Type S (wrong sign) and Type M (exaggeration) at plausible effect A with standard error s (Gelman & Carlin 2014):
  ```python
  import numpy as np
  from scipy import stats
  def retrodesign(A, s, alpha=0.05, n_sims=200_000, seed=20260930):
      z = stats.norm.ppf(1 - alpha / 2)
      p_hi, p_lo = 1 - stats.norm.cdf(z - A / s), stats.norm.cdf(-z - A / s)
      est = A + s * np.random.default_rng(seed).standard_normal(n_sims)
      sig = np.abs(est) > s * z
      return p_hi + p_lo, p_lo / (p_hi + p_lo), np.abs(est[sig]).mean() / A  # power, Type S, exaggeration
  ```
  - `retrodesign(2, 8.1)` gives power 0.06, Type S 0.24 and exaggeration 9.5 (9.54 by exact integration) [RUN], in line with the paper's worked example.
  - Base rate: in more than 16,000 political-science tests the median power was about 10% (Arel-Bundock et al. 2026).
  - Backtests: out-of-sample tests have less power than in-sample ones (Inoue & Kilian 2005), and many in-sample predictors fail out of sample (Welch & Goyal 2008). `scripts/backtest_eval.py` reports a backtest's effective n and approximate minimum detectable loss difference.
- **Pass criterion (fix before running):** every null claim carries its MDE in outcome units; every trend claim states power and Type S at a plausible effect; Type S ≤ 10% for claims that drive T1 decisions.
- **Failure signature:** "no effect" from a design whose MDE exceeds any plausible effect; a significant estimate several times larger than credible benchmarks; a trend whose sign flips across windows. A short failed backtest is weak evidence of no effect, and a short passed one is weak evidence of an effect; report both readings with the MDE.
- **Source:** Gelman & Carlin (2014); Arel-Bundock et al. (2026); Inoue & Kilian (2005); Welch & Goyal (2008); Wasserstein & Lazar (2016); McShane et al. (2019).

### 2.10 Uncertainty: bootstrap families, coefficient vs prediction intervals, Monte-Carlo propagation
- **Tests:** whether a reported interval matches the data's dependence and the reader's question.
- **Assumptions of the test itself:** a bootstrap is only as valid as its resampling unit; Monte-Carlo propagation needs honest input distributions, correlations included.
- **Run it:** choose the family by dependence:

  | Data | Bootstrap | Resample |
  |---|---|---|
  | Independent rows, heteroskedastic | Pairs (Efron 1979) or wild (Wu 1986; Mammen 1993) | Rows, or residual signs |
  | Clustered | Cluster pairs, or wild cluster restricted (Cameron et al. 2008) | Whole clusters |
  | Time series | Moving-block (Künsch 1989) or stationary (Politis & Romano 1994) | Blocks of consecutive periods |

  - R `boot::boot()`; `boot::tsboot(x, stat, R = 999, l = L, sim = "geom")` is the stationary bootstrap (for an AR(0.6) series the block SE of the mean was 0.156 against a naive 0.098 [RUN]).
  - Coefficient CI vs prediction interval: `res.get_prediction(new).summary_frame()` returns `mean_ci_*` (where the average lies) and `obs_ci_*` (where a new unit lies); R `predict(fit, new, interval = "confidence")` vs `"prediction"`.
  - Monte-Carlo propagation (the JCGM 101:2008 approach): draw inputs from their distributions, push every draw through the model and summarize, then compare with the linearized interval. For y = x² with x ~ N(1, 0.5²), the linearized 95% interval is [−0.96, 2.96] and the Monte-Carlo shortest 95% interval is [0.00, 3.32] [RUN]; the first is impossible for a square.
  - Report the Monte-Carlo standard error of every simulated number: `python scripts/mc_error.py --data reps.csv --rep rep --target-rel 0.01`, where `--rep` names the replication column so it is not read as a metric (exit 0 on 200 synthetic replications [RUN]). Its precision verdict uses the iid MCSE (sd/√n), switching to the ESS-adjusted MCSE for any column whose replications fail the Ljung-Box independence test; MC-DEGENERATE flags a column that never varies (the model is deterministic, or the randomness never reached it). Rank inputs by their share of output variance with `scripts/global_sensitivity.py`.
- **Pass criterion (fix before running):** resampling unit equals the independent unit; interval type named; prediction intervals for statements about individual outcomes; Monte Carlo whenever the model is nonlinear across ±2 SD of an input, bounded or skewed; MCSE below the smallest decision-relevant gap.
- **Failure signature:** a row bootstrap on clustered or serial data; a coefficient CI presented as the range a unit's outcome will fall in, which leads readers to overrate effects (Hofman et al. 2020); intervals that cross a physical bound; decisions that change across seeds.
- **Source:** Efron (1979); Wu (1986); Mammen (1993); Künsch (1989); Politis & Romano (1994); Cameron, Gelbach & Miller (2008); JCGM 101:2008; Koehler, Brown & Haneuse (2009); Morris, White & Crowther (2019); Hofman, Goldstein & Hullman (2020).

### 2.11 "Did the new pipeline change the answer?" Equivalence and method comparison
- **Tests:** whether two computations (old and new code, vintage, vendor or implementation) agree closely enough for the decision.
- **Assumptions of the test itself:** the margin δ is set from the decision before looking (e.g. ±1 rank, ±0.5 percentage points of probability, ±$1k per unit), and no tighter than the inputs' stored precision allows: jitter rounded inputs within their rounding span first, or the bar may be infeasible from the start; both methods measure the same unit.
- **Run it:**
  - First diff every output row: identical, changed, added, dropped.
  - Then test equivalence with two one-sided tests: agreement is shown only when the (1 − 2α) interval of the paired difference lies inside ±δ (Schuirmann 1987; Lakens 2017): `from statsmodels.stats.weightstats import ttost_paired; p, *_ = ttost_paired(new, old, -delta, delta)`. A non-significant paired t-test is not agreement; it rewards small comparisons.
  - For systematic disagreement, regress new on old allowing error in both: Deming (orthogonal when error variances are equal) or Passing–Bablok (rank-based, tolerant of outliers), and read the intercept (constant bias) and slope (proportional bias). OLS attenuates the slope: with equal errors and a true slope of 1, OLS gave 0.49 and Deming 0.93 [RUN].
  ```python
  import numpy as np
  def deming(x, y, delta=1.0):  # delta = error variance of y / error variance of x
      sxx, syy, sxy = np.var(x, ddof=1), np.var(y, ddof=1), np.cov(x, y, ddof=1)[0, 1]
      b = (syy - delta * sxx + np.sqrt((syy - delta * sxx) ** 2 + 4 * delta * sxy ** 2)) / (2 * sxy)
      return y.mean() - b * x.mean(), b  # intercept, slope
  ```
  - Plot Bland–Altman differences against means with bias and 95% limits of agreement (Bland & Altman 1986). Never use r² as agreement; it rises with the range and ignores bias. Response linearity needs a lack-of-fit F test on replicated levels (`finance.md` §2.5.2).
  - Finally compare decisions: top-K overlap, rank correlation, every changed allocation or label.
- **Pass criterion (fix before running):** TOST p < α at the pre-stated δ; intercept interval contains 0 and slope interval contains 1; no decision changes, or every change is listed with its cause.
- **Failure signature:** "p = 0.4, so the pipelines agree" on a dozen rows; high r² with a slope of 0.8; limits of agreement wider than δ; a trend in the Bland–Altman plot.
- **Source:** Schuirmann (1987); Lakens (2017); Passing & Bablok (1983); Bland & Altman (1986).

### 2.12 Missing data
- **Tests:** whether missingness biases estimates or manufactures precision.
- **Assumptions of the test itself:** MCAR, MAR (missingness depends on observed data only) and MNAR (depends on the unseen value) cannot be told apart from the observed data alone, so MNAR needs a sensitivity analysis (Rubin 1976).
- **Run it:**
  - Census missingness by variable, stratum and period; keep missing, structurally absent, below-reporting-threshold and true zero distinct (unitemized money is not zero).
  - Regress a missingness indicator on observed covariates: dependence rules out MCAR, never MNAR.
  - Compare complete-case, multiple imputation (Python `statsmodels.imputation.mice.MICE`; R `mice`, needs mice) and a delta-shifted MNAR scenario. Report the headline with and without imputed rows, with the count, share and money share imputed.
  - Carry an `_imputed` flag with every imputed cell into every output, chart and export; never use imputed values as validation targets; fit imputers inside training folds only (`scripts/leakage_audit.py` flags missingness-pattern shift between splits; `machine-learning.md`).
- **Pass criterion (fix before running):** mechanism stated per variable; with/without results reported; headline sign and decision survive the plausible MNAR range; imputed flags present end to end.
- **Failure signature:** single median or zero imputation followed by ordinary SEs, which shrinks variance, piles mass at one value, distorts associations and treats guesses as data (Sterne et al. 2009); zero-filled money read as "no money"; a group median that leaks the outcome; imputed values indistinguishable on a dashboard.
- **Source:** Rubin (1976); Sterne et al. (2009); van Buuren & Groothuis-Oudshoorn (2011).

### 2.13 Bayesian workflow essentials
- **Tests:** whether a posterior summary reflects the data and model rather than sampler failure or the prior.
- **Assumptions of the test itself:** diagnostics can reveal failure but never prove convergence; prior influence depends on how much data inform each parameter.
- **Run it** (needs arviz or an R Stan interface; neither was installed on the build machine as of 2026-09-30; without the sampler's draws, mark these checks UNVERIFIED-HERE rather than trusting a printed summary):
  - Prior predictive check: simulate data from the priors; they should cover plausible outcomes without absurd mass.
  - At least 4 chains; rank-normalized R-hat < 1.01 (flag ≥ 1.01) and bulk and tail ESS ≥ 400 (Vehtari et al. 2021); zero divergent transitions, since any divergence can bias the posterior until explained.
  - Posterior predictive checks on decision-relevant features such as the zero share, the maximum and the dispersion by stratum (Gabry et al. 2019).
  - PSIS-LOO for model comparison with every Pareto k < 0.7 (Vehtari et al. 2017); refit under a wider and a narrower prior.
  - ArviZ 1.x `az.summary` defaults to 89% intervals, so pass `ci_prob=0.95` (as of 2026-07, per K-Dense statistical-analysis; re-verify).
- **Pass criterion (fix before running):** all diagnostics pass; posterior predictive p-values for pre-named features within, e.g., 0.05–0.95; the decision is unchanged across priors.
- **Failure signature:** R-hat of 1.01 or more reported as converged; divergences ignored; LOO with many high-k points; a posterior that matches the prior for the decision parameter (the data do not identify it).
- **Source:** Gelman et al. (2020); Gabry et al. (2019); Vehtari, Gelman & Gabry (2017); Vehtari et al. (2021).

### 2.14 Presentation contract (every module reports this way)
- **Tests:** whether a reported result says what the number is, how sure we are, and what the design could detect.
- **Assumptions of the test itself:** the reader acts on the first line; anything below it is read less.
- **Run it:**
  - Write every result in this order: (1) **trend**: sign, size in units, consistency across windows, strata and specifications; (2) **uncertainty** in one line: interval, variance type, G, and p if asked; (3) **power**: MDE or the backtest's power; (4) **scope**: strata or UNSTRATIFIED, associational or causal.
  - Show regressions as the verbatim R `summary(lm())` print, then the labelled robust block. `scripts/regression_report.R` prints, in order: `summary(lm())`; a block headed `=== Inference block: <vcov> (G = <clusters>, <bootstrap desc>) ===` (estimate, SE, t, p, 95% CI per term, plus wild-bootstrap p and CI when used); the diagnostics (N rows vs G units, few-cluster flags, leverage, aliasing, RESET, Breusch–Pagan, VIF, max Cook's D with its row, autocorrelation when `--time` is set); one `Trend:` line. The checks (LM-UNITS, LM-LEVERAGE, LM-COLLINEAR, LM-VIF, LM-RESET, LM-BP, LM-COOK, LM-SERIAL, LM-STRATA, LM-CR2, LM-HC3, LM-PARITY) go to report.md and report.json; a diagnostic that cannot be computed is recorded UNVERIFIED-HERE with its reason.
  ```
  Rscript scripts/regression_report.R --data d.csv --formula "y ~ x + z" --cluster unit \
    --vcov CR2 --boot wild --B 999 --strata party --time period --out qme_out
  ```
  - Defaults: `--vcov` is CR1 with `--cluster`, else HC1; `--boot wild` when a clustered variance has G < `--min-clusters` (42); `--seed 20260930`; `--term` names the focal coefficient (default: the first non-intercept term). LM-STRATA SURVIVES when at least `--min-sign-share` (0.8) of strata share the pooled sign, is WOUNDED from 0.5 and KILLED below it. The R script takes `--no-glassbox` but has no `--quiet`. Without `Rscript` on PATH, set `QME_RSCRIPT` or use `C:\Program Files\R\R-*\bin\Rscript.exe`. On a synthetic 30-unit panel the command above exited 1: LM-UNITS WOUNDED (G = 30 < 42), LM-SERIAL and LM-STRATA SURVIVES [RUN].
  - Script exit codes: 0 every check SURVIVES; 1 any WOUNDED or KILLED; 2 usage or input error; 3 UNVERIFIED-HERE present (a run with no checks also exits 3). A KILLED printed by a script is a candidate until a second independent reader confirms it (SKILL.md hard rule 5).
  - A coefficient plot on the same scale is a companion, never a replacement (`data-visualization.md` §2.3).
  - Headline template: "`<y>` rose with `<x>` in `<k>` of `<K>` windows (`<window>`; data as of `<vintage>`); `<size>` `<units>` per `<unit of x>`; 95% CI `<lo, hi>` (CR2, G = `<g>`, N = `<n>` rows); MDE `<m>`; `<UNSTRATIFIED | strata: …>`; associational; `<N>` specifications tried."
- **Pass criterion (fix before running):** every number names units, window, denominator and data vintage, and the rows and independent units behind it; pooled estimates show strata or carry UNSTRATIFIED; no "confirmed", "proven" or "validated" for a single analysis; causal verbs only with an identified design; "no detectable effect (MDE …)" instead of "no effect"; forecasts compared out of sample against naive and seasonal-naive benchmarks with the backtest's power (`scripts/backtest_eval.py`, `finance.md`).
- **Failure signature:** a p-value or star leads the sentence; classical SEs quoted for clustered data; a number with no window or vintage; a pooled estimate hiding a sign flip between strata.
- **Source:** Wasserstein & Lazar (2016); McShane et al. (2019); King & Roberts (2015).

## 3. Checklist

| ID | Check | Class | Runs with |
|---|---|---|---|
| STA-01 | Write the estimand (quantity, population, unit, window, contrast) before reading results; fail any headline without one. | CAUSAL, MEASUREMENT | §2.1 |
| STA-02 | List rival explanations from distinct classes and run at least one negative control per effect claim. | CAUSAL | §2.1, `scripts/confounding_sensitivity.py` |
| STA-03 | Run RESET and partial-residual plots; fail if curvature changes a decision in the decision range. | FUNCTIONAL-FORM | §2.2, `scripts/regression_report.R` (LM-RESET) |
| STA-04 | For every interaction, check moderator support and the linearity of the interaction. | FUNCTIONAL-FORM | §2.2 |
| STA-05 | Test heteroskedasticity; show HC3 or HC1 SEs beside classical ones and treat a large gap as misspecification. | STATISTICAL | §2.3, `regression_report.R` (LM-BP, LM-HC3) |
| STA-06 | State N rows and G independent units beside every estimate; cluster at the assignment or sampling level. | STATISTICAL | §2.4, `scripts/regression_report.R` (LM-UNITS) |
| STA-07 | With G < 42 report wild cluster bootstrap p-values; with G < 10 label the inference DESCRIPTIVE. | STATISTICAL | §2.4, `regression_report.R --boot wild` (LM-UNITS) |
| STA-08 | Never cluster on 2–3 groups; cluster two ways for crossed structures. | STATISTICAL | §2.4 |
| STA-09 | Judge normality by Q-Q plot and only when residual df is small. | STATISTICAL | §2.3 |
| STA-10 | Flag auxiliary R² ≥ 0.9999, any `NA` or absurd coefficient, leverage-1 rows, and too few residual df for the tests reported. | COMPUTATIONAL | §2.5, `scripts/regression_report.R` (LM-COLLINEAR, LM-VIF, LM-LEVERAGE) |
| STA-11 | Report max Cook's D with its row and refit without the most influential unit or cluster. | DATA | §2.5, `regression_report.R` (LM-COOK) |
| STA-12 | Refuse p-values from stepwise or screened models; use a held-out half or selection-repeated resampling. | STATISTICAL | §2.6 |
| STA-13 | Run ADF and KPSS on every series in a time regression and state the joint reading. | STATISTICAL | §2.7 |
| STA-14 | Refit trending-level regressions in differences, or test cointegration, before reading t or R². | STATISTICAL | §2.7 |
| STA-15 | Use HAC SEs with the lag stated when one series' residuals are autocorrelated (cluster panels instead); test with Durbin–Watson and Breusch–Godfrey. | STATISTICAL | §2.7, `regression_report.R --vcov NW --time` (LM-SERIAL) |
| STA-16 | Test breaks at every pre-named date and by sup-F; never pool across a confirmed break. | STATISTICAL | §2.7 |
| STA-17 | Count every test and specification tried, and report that count with the result. | STATISTICAL | §2.8 |
| STA-18 | Adjust within each declared family: BH for screens, Holm or Romano–Wolf when one false positive is costly. | STATISTICAL | §2.8 |
| STA-19 | Show a specification curve for each headline; fail if fewer than the pre-set share of defensible specifications share the headline sign. | STATISTICAL | §2.8 |
| STA-20 | Attach the MDE, in outcome units, to every null or "no effect" statement. | STATISTICAL | §2.9 |
| STA-21 | Compute Type S and Type M at a plausible external effect for every trend claim. | STATISTICAL | §2.9 |
| STA-22 | Read every backtest verdict against its effective n and minimum detectable loss difference. | STATISTICAL | §2.9, `scripts/backtest_eval.py` |
| STA-23 | Resample the independent unit in every bootstrap and name the bootstrap family. | STATISTICAL | §2.10 |
| STA-24 | Use prediction intervals for statements about individual outcomes; label every interval's type. | PRESENTATION | §2.10 |
| STA-25 | Propagate input uncertainty by Monte Carlo for nonlinear or bounded models; give an MCSE for every simulated number. | COMPUTATIONAL | §2.10, `scripts/mc_error.py` (MC-DEGENERATE, precision), `scripts/global_sensitivity.py` |
| STA-26 | Diff every output row between pipelines, then test equivalence by TOST at a pre-stated margin. | COMPUTATIONAL | §2.11 |
| STA-27 | Compare methods with Deming or Passing–Bablok plus Bland–Altman, never with r². | MEASUREMENT | §2.11 |
| STA-28 | Census missingness by variable, stratum and period, and name the assumed mechanism. | DATA | §2.12 |
| STA-29 | Report headline results with and without imputed rows, with the imputed share. | DATA | §2.12 |
| STA-30 | Carry an imputed flag into every output and fit imputers inside training folds only. | DATA | §2.12, `scripts/leakage_audit.py` |
| STA-31 | For Bayesian fits require R-hat < 1.01 (flag ≥ 1.01), ESS ≥ 400, zero divergences, prior and posterior predictive checks, Pareto k < 0.7. | COMPUTATIONAL | §2.13 |
| STA-32 | Print the verbatim `summary(lm())` followed by the labelled inference block; treat a KILLED printed by a script as a candidate until a second independent reader confirms it. | PRESENTATION | §2.14, `scripts/regression_report.R` (LM-STRATA) |
| STA-33 | Lead with the trend (sign, size, consistency), then one uncertainty line, then power. | PRESENTATION | §2.14 |
| STA-34 | Name units, window, denominator and vintage for every number; label pooled estimates UNSTRATIFIED. | PRESENTATION | §2.14 |
| STA-35 | Strike "confirmed", "proven", "validated" and unearned causal verbs from findings. | PRESENTATION | §2.14 |

## 4. Pitfalls and anti-patterns

- Reading the classical SEs that `summary(lm())` prints as the inference for clustered or serial data. The print is the record; the inference block is the inference.
- Treating rows as evidence: tens of thousands of member-vote rows from a few hundred members and a few dozen roll calls are not independent draws.
- Switching to robust SEs to "fix" a misspecified model (King & Roberts 2015).
- Declaring a difference between strata because one is significant and the other is not; test the interaction (Gelman & Stern 2006).
- Stepwise selection followed by ordinary p-values (§2.6).
- HAC SEs on a levels regression of trending series (§2.7); pooling across a break because the full-sample fit looks better.
- Picking the window or specification after seeing results and reporting it alone.
- Reading p > 0.05 as "no effect"; computing observed power after the fact.
- Claiming equivalence from a non-significant difference test (§2.11).
- Validating a number with the code that produced it; the second path must be independent.
- Single imputation followed by ordinary SEs; imputed values used as validation targets.
- Trusting statsmodels coefficients on an aliased design; it does not stop you (§2.5).
- Bootstrapping rows inside clusters or periods; on serially dependent data the naive SE was about 37% too small [RUN].
- Coefficient intervals shown where readers judge individual outcomes (§2.10).
- Simulation outputs without Monte-Carlo standard errors, or decisions driven by gaps under 2 MCSE (`engineering-simulation.md`).
- Bayesian summaries with R-hat, ESS or divergences left unreported.
- Reporting "p < .05" or stars instead of exact values and intervals.

## 5. References

Verified entries only. Most come from the research bibliographies of 2026-09-29/30 (CrossRef or OpenAlex); entries marked † were verified for this file against CrossRef (2026-09-30; titles matched). "(correction notice)" means CrossRef records a correction or erratum for the work (checked 2026-09-30): read it before quoting details.

- Abadie, A., Athey, S., Imbens, G. W., Wooldridge, J. M. (2023). When should you adjust standard errors for clustering? *QJE* 138(1):1–35. doi:10.1093/qje/qjac038
- Achen, C. H. (2005). Let's put garbage-can regressions and garbage-can probits where they belong. *Conflict Management and Peace Science* 22(4):327–339. doi:10.1080/07388940500339167
- Andrews, D. W. K. (1993). Tests for parameter instability and structural change with unknown change point. *Econometrica* 61(4):821. doi:10.2307/2951764
- Arel-Bundock, V., Briggs, R. C., Doucouliagos, H., Mendoza Aviña, M., Stanley, T. D. (2026). Quantitative political science research is greatly underpowered. *Journal of Politics* 88(1):36–46. doi:10.1086/734279
- Aronow, P. M., Samii, C. (2016). Does regression produce representative estimates of causal effects? *AJPS* 60(1):250–267. doi:10.1111/ajps.12185 (correction notice)
- Bai, J., Perron, P. (1998). Estimating and testing linear models with multiple structural changes. *Econometrica* 66(1):47. doi:10.2307/2998540
- † Belsley, D. A., Kuh, E., Welsch, R. E. (1980). *Regression Diagnostics*. Wiley. doi:10.1002/0471725153
- Benjamini, Y., Hochberg, Y. (1995). Controlling the false discovery rate. *JRSS-B* 57(1):289–300. doi:10.1111/j.2517-6161.1995.tb02031.x
- † Berk, R., Brown, L., Buja, A., Zhang, K., Zhao, L. (2013). Valid post-selection inference. *Annals of Statistics* 41(2). doi:10.1214/12-AOS1077
- Bertrand, M., Duflo, E., Mullainathan, S. (2004). How much should we trust differences-in-differences estimates? *QJE* 119(1):249–275. doi:10.1162/003355304772839588
- † Bland, J. M., Altman, D. G. (1986). Statistical methods for assessing agreement between two methods of clinical measurement. *Lancet* 327(8476):307–310. doi:10.1016/S0140-6736(86)90837-8
- † Breusch, T. S. (1978). Testing for autocorrelation in dynamic linear models. *Australian Economic Papers* 17(31):334–355. doi:10.1111/j.1467-8454.1978.tb00635.x
- † Breusch, T. S., Pagan, A. R. (1979). A simple test for heteroscedasticity and random coefficient variation. *Econometrica* 47(5):1287. doi:10.2307/1911963
- Breznau, N., et al. (2022). Observing many researchers using the same data and hypothesis reveals a hidden universe of uncertainty. *PNAS* 119(44):e2203150119. doi:10.1073/pnas.2203150119 (correction notice)
- Cameron, A. C., Gelbach, J. B., Miller, D. L. (2008). Bootstrap-based improvements for inference with clustered errors. *REStat* 90(3):414–427. doi:10.1162/rest.90.3.414
- Cameron, A. C., Gelbach, J. B., Miller, D. L. (2011). Robust inference with multiway clustering. *JBES* 29(2):238–249. doi:10.1198/jbes.2010.07136
- Chow, G. C. (1960). Tests of equality between sets of coefficients in two linear regressions. *Econometrica* 28(3):591. doi:10.2307/1910133
- Cinelli, C., Hazlett, C. (2020). Making sense of sensitivity: extending omitted variable bias. *JRSS-B* 82(1):39–67. doi:10.1111/rssb.12348
- † Cook, R. D. (1977). Detection of influential observation in linear regression. *Technometrics* 19(1):15–18. doi:10.1080/00401706.1977.10489493
- Dickey, D. A., Fuller, W. A. (1979). Distribution of the estimators for autoregressive time series with a unit root. *JASA* 74(366):427. doi:10.2307/2286348
- † Efron, B. (1979). Bootstrap methods: another look at the jackknife. *Annals of Statistics* 7(1). doi:10.1214/aos/1176344552
- Engle, R. F., Granger, C. W. J. (1987). Co-integration and error correction. *Econometrica* 55(2):251. doi:10.2307/1913236
- Esarey, J., Menger, A. (2019). Practical and effective approaches to dealing with clustered data. *PSRM* 7(3):541–559. doi:10.1017/psrm.2017.42
- † Freedman, D. A. (1983). A note on screening regression equations. *American Statistician* 37(2):152–155. doi:10.1080/00031305.1983.10482729
- † Gabry, J., Simpson, D., Vehtari, A., Betancourt, M., Gelman, A. (2019). Visualization in Bayesian workflow. *JRSS-A* 182(2):389–402. doi:10.1111/rssa.12378
- Gelman, A., Carlin, J. (2014). Beyond power calculations: assessing Type S and Type M errors. *Perspectives on Psychological Science* 9(6):641–651. doi:10.1177/1745691614551642
- Gelman, A., Loken, E. (2014). The statistical crisis in science. *American Scientist* 102(6):460. doi:10.1511/2014.111.460
- † Gelman, A., Stern, H. (2006). The difference between "significant" and "not significant" is not itself statistically significant. *American Statistician* 60(4):328–331. doi:10.1198/000313006X152649
- † Gelman, A., et al. (2020). Bayesian workflow. arXiv preprint. doi:10.48550/arXiv.2011.01808 (OpenAlex record)
- † Godfrey, L. G. (1978). Testing against general autoregressive and moving average error models when the regressors include lagged dependent variables. *Econometrica* 46(6):1293. doi:10.2307/1913829
- Granger, C. W. J., Newbold, P. (1974). Spurious regressions in econometrics. *Journal of Econometrics* 2(2):111–120. doi:10.1016/0304-4076(74)90034-7
- Hainmueller, J., Mummolo, J., Xu, Y. (2019). How much should we trust estimates from multiplicative interaction models? *Political Analysis* 27(2):163–192. doi:10.1017/pan.2018.46
- Hofman, J. M., Goldstein, D. G., Hullman, J. (2020). How visualizing inferential uncertainty can mislead readers about treatment effects in scientific results. *CHI 2020*:1–12. doi:10.1145/3313831.3376454
- † Hurlbert, S. H. (1984). Pseudoreplication and the design of ecological field experiments. *Ecological Monographs* 54(2):187–211. doi:10.2307/1942661
- Inoue, A., Kilian, L. (2005). In-sample or out-of-sample tests of predictability: which one should we use? *Econometric Reviews* 23(4):371–402. doi:10.1081/ETC-200040785
- † JCGM 101:2008. Evaluation of measurement data — Supplement 1 to the GUM — Propagation of distributions using a Monte Carlo method. BIPM. doi:10.59161/JCGM101-2008
- King, G., Roberts, M. E. (2015). How robust standard errors expose methodological problems they do not fix. *Political Analysis* 23(2):159–179. doi:10.1093/pan/mpu015
- Koehler, E., Brown, E., Haneuse, S. J.-P. A. (2009). On the assessment of Monte Carlo error in simulation-based statistical analyses. *American Statistician* 63(2):155–162. doi:10.1198/tast.2009.0030
- † Künsch, H. R. (1989). The jackknife and the bootstrap for general stationary observations. *Annals of Statistics* 17(3). doi:10.1214/aos/1176347265
- Kwiatkowski, D., Phillips, P. C. B., Schmidt, P., Shin, Y. (1992). Testing the null hypothesis of stationarity against the alternative of a unit root. *Journal of Econometrics* 54(1–3):159–178. doi:10.1016/0304-4076(92)90104-Y
- † Lakens, D. (2017). Equivalence tests: a practical primer. *Social Psychological and Personality Science* 8(4):355–362. doi:10.1177/1948550617697177
- † Leeb, H., Pötscher, B. M. (2005). Model selection and inference: facts and fiction. *Econometric Theory* 21(1):21–59. doi:10.1017/S0266466605050036
- † Lipsitch, M., Tchetgen Tchetgen, E., Cohen, T. (2010). Negative controls. *Epidemiology* 21(3):383–388. doi:10.1097/EDE.0b013e3181d61eeb
- † Long, J. S., Ervin, L. H. (2000). Using heteroscedasticity consistent standard errors in the linear regression model. *American Statistician* 54(3):217–224. doi:10.1080/00031305.2000.10474549
- † Lundberg, I., Johnson, R., Stewart, B. M. (2021). What is your estimand? *American Sociological Review* 86(3):532–565. doi:10.1177/00031224211004187
- MacKinnon, J. G., Nielsen, M. Ø., Webb, M. D. (2023). Cluster-robust inference: a guide to empirical practice. *Journal of Econometrics* 232(2):272–299. doi:10.1016/j.jeconom.2022.04.001
- † Mammen, E. (1993). Bootstrap and wild bootstrap for high dimensional linear models. *Annals of Statistics* 21(1). doi:10.1214/aos/1176349025
- McShane, B. B., Gal, D., Gelman, A., Robert, C., Tackett, J. L. (2019). Abandon statistical significance. *American Statistician* 73(sup1):235–245. doi:10.1080/00031305.2018.1527253
- Montgomery, J. M., Nyhan, B., Torres, M. (2018). How conditioning on posttreatment variables can ruin your experiment. *AJPS* 62(3):760–775. doi:10.1111/ajps.12357
- Morris, T. P., White, I. R., Crowther, M. J. (2019). Using simulation studies to evaluate statistical methods. *Statistics in Medicine* 38(11):2074–2102. doi:10.1002/sim.8086
- Newey, W. K., West, K. D. (1987). A simple, positive semi-definite, heteroskedasticity and autocorrelation consistent covariance matrix. *Econometrica* 55(3):703. doi:10.2307/1913610
- Ofosu, G. K., Posner, D. N. (2023). Pre-analysis plans: an early stocktaking. *Perspectives on Politics* 21(1):174–190. doi:10.1017/s1537592721000931
- † Passing, H., Bablok, W. (1983). A new biometrical procedure for testing the equality of measurements from two different analytical methods. *J. Clin. Chem. Clin. Biochem.* 21(11):709–720. doi:10.1515/cclm.1983.21.11.709
- Politis, D. N., Romano, J. P. (1994). The stationary bootstrap. *JASA* 89(428):1303–1313. doi:10.1080/01621459.1994.10476870
- † Pustejovsky, J. E., Tipton, E. (2018; online 2017). Small-sample methods for cluster-robust variance estimation and hypothesis testing in fixed effects models. *JBES* 36(4):672–683. doi:10.1080/07350015.2016.1247004 (correction notice)
- † Ramsey, J. B. (1969). Tests for specification errors in classical linear least-squares regression analysis. *JRSS-B* 31(2):350–371. doi:10.1111/j.2517-6161.1969.tb00796.x
- Romano, J. P., Wolf, M. (2005). Stepwise multiple testing as formalized data snooping. *Econometrica* 73(4):1237–1282. doi:10.1111/j.1468-0262.2005.00615.x
- † Rubin, D. B. (1976). Inference and missing data. *Biometrika* 63(3):581–592. doi:10.1093/biomet/63.3.581
- † Schuirmann, D. J. (1987). A comparison of the two one-sided tests procedure and the power approach for assessing the equivalence of average bioavailability. *J. Pharmacokinet. Biopharm.* 15(6):657–680. doi:10.1007/BF01068419
- Simonsohn, U., Simmons, J. P., Nelson, L. D. (2020). Specification curve analysis. *Nature Human Behaviour* 4(11):1208–1214. doi:10.1038/s41562-020-0912-z (correction notice)
- Steegen, S., Tuerlinckx, F., Gelman, A., Vanpaemel, W. (2016). Increasing transparency through a multiverse analysis. *Perspectives on Psychological Science* 11(5):702–712. doi:10.1177/1745691616658637
- † Sterne, J. A. C., et al. (2009). Multiple imputation for missing data in epidemiological and clinical research: potential and pitfalls. *BMJ* 338:b2393. doi:10.1136/bmj.b2393
- † van Buuren, S., Groothuis-Oudshoorn, K. (2011). mice: multivariate imputation by chained equations in R. *Journal of Statistical Software* 45(3). doi:10.18637/jss.v045.i03
- † Vehtari, A., Gelman, A., Gabry, J. (2017; online 2016). Practical Bayesian model evaluation using leave-one-out cross-validation and WAIC. *Statistics and Computing* 27(5):1413–1432. doi:10.1007/s11222-016-9696-4 (correction notice)
- † Vehtari, A., Gelman, A., Simpson, D., Carpenter, B., Bürkner, P.-C. (2021). Rank-normalization, folding, and localization: an improved R-hat for assessing convergence of MCMC. *Bayesian Analysis* 16(2). doi:10.1214/20-BA1221
- Wasserstein, R. L., Lazar, N. A. (2016). The ASA statement on p-values: context, process, and purpose. *American Statistician* 70(2):129–133. doi:10.1080/00031305.2016.1154108
- Welch, I., Goyal, A. (2008). A comprehensive look at the empirical performance of equity premium prediction. *RFS* 21(4):1455–1508. doi:10.1093/rfs/hhm014
- † White, H. (1980). A heteroskedasticity-consistent covariance matrix estimator and a direct test for heteroskedasticity. *Econometrica* 48(4):817. doi:10.2307/1912934
- † Wu, C. F. J. (1986). Jackknife, bootstrap and other resampling methods in regression analysis. *Annals of Statistics* 14(4). doi:10.1214/aos/1176350142

**UNVERIFIED (named, not cited):** Holm, S. (1979), the sequentially rejective step-down procedure, *Scandinavian Journal of Statistics*: no CrossRef record, and OpenAlex was rate-limited on 2026-09-30. Verify before citing.

**Adapted from** (K-Dense-AI/scientific-agent-skills; the paths are inside that repository, not this skill; ideas paraphrased, no prose or code copied): `statsmodels/references/stats_diagnostics.md` and `statsmodels/references/time_series.md` (BSD-3-Clause); `statistical-analysis/SKILL.md` ("Statistical Integrity") and `statistical-analysis/references/bayesian_statistics.md` (MIT); `statistical-power/SKILL.md` (MDE, design effect, no observed power; MIT); `scientific-critical-thinking/references/statistical_pitfalls.md` (MIT); `hypothesis-generation/SKILL.md` and `hypothesis-generation/references/causal_inference_and_claims.md` (estimands, rivals, negative controls; MIT); `peer-review/SKILL.md` (methods review order; MIT); `experimental-design/SKILL.md` (pseudoreplication; MIT); `exploratory-data-analysis/SKILL.md` (missing vs zero, no automatic imputation; MIT); `uncertainty-and-units/references/gum-methodology.md` (Monte Carlo alongside linearization; MIT); `analytical-method-validation/references/statistics.md` (TOST, Deming, Passing–Bablok, Bland–Altman, r² is not agreement; MIT).
