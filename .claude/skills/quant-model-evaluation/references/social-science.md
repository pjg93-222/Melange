# Social science — quant-model-evaluation reference

> **Load when:** a system claims effects of money, persuasion, lobbying or access; builds measures from text, LLM labels, ratings or roll calls; uses networks, diffusion or influence simulations; or draws inferences about legislators, votes, bills or districts. **Not for:** regression mechanics, multiplicity and bootstrap details (`core-statistics.md`); classifier leakage, calibration and drift (`machine-learning.md`); money-data traps and spend-response curves (`finance.md`); maps, crosswalks and district plans (`geospatial.md`); Monte-Carlo error and sensitivity designs (`engineering-simulation.md`); law and research ethics (`regulatory.md`).
> Facts marked (as of DATE) are time-sensitive; re-verify before relying on them. Snippets need only numpy, pandas, scipy, statsmodels, scikit-learn and networkx unless marked "(needs ...)". A KILLED printed by a script is a candidate until a second independent reader confirms it (SKILL.md hard rule 5).

## 1. Assumption map

| Assumption (class) | Where it usually hides | What breaks if it is false | Tests |
|---|---|---|---|
| Money or lobbying is as good as random given the controls (`CAUSAL`) | response curves, flip models, frontiers that price dollars | "effects" are selection: money follows competitiveness, candidate quality and committee power | 2.1, 2.8, SOC-01, SOC-06, SOC-10 |
| Close-race winners and losers are comparable (`CAUSAL`) | "what seating X changes" estimates | sorting bias; a who-wins effect sold as a dollar effect | 2.2, SOC-02, SOC-03 |
| The instrument, the within-unit change or the border assignment is as good as random (`CAUSAL`) | IV spending models, fixed-effects panels, rematches, media-market borders | inflated, overconfident LATE; quality confounding survives; one border segment drives the result | 2.3, 2.4, SOC-04, SOC-05 |
| Untreated outcomes would have moved like the comparison: parallel trends, or a donor pool that reproduces the treated path (`CAUSAL`) | event studies of committee moves, leadership changes, rule shocks; one-state or one-firm policy effects | TWFE sign reversal; pre-test theatre; poor fit reported as an effect | 2.6, 2.7, SOC-07..09 |
| No control or sample filter is affected by treatment (`CAUSAL`) | covariates dated after the money; winners-only or floor-vote samples | bias of either sign | 2.9, SOC-11 |
| Words follow the design (`PRESENTATION`) | findings text, dashboards, memos | associations published as effects | 2.10, SOC-12 |
| A score measures its construct, not activity volume, and its weights do not decide the order (`MEASUREMENT`) | stance, trait, engagement, "influence" and priority indices | rankings by volume or by contestable weights | 2.11, SOC-13, SOC-14 |
| Sentiment equals stance; text labels are accurate in every subgroup (`MEASUREMENT`) | dictionary or classifier output used as positions | wrong-signed positions; subgroup bias | 2.12, SOC-15 |
| LLM labels are accurate, stable, replayable and non-differential (`MEASUREMENT`, `COMPUTATIONAL`) | annotation pipelines on closed-model APIs | biased regressions; silent drift; no replay | 2.13, 2.14, SOC-17..19 |
| Gold labels are a probability sample with their coders counted, and regressors carry little measurement error (`MEASUREMENT`) | small validation sets; trait scores or ideal points used as covariates | biased validation; attenuation; spurious group interactions | 2.14-2.16, SOC-16, SOC-20 |
| One low dimension, sincere votes, a bridge across Congresses (`MEASUREMENT`) | ideal-point scalings | members misplaced; issue positions read off the wrong axis | 2.17, SOC-21 |
| Aggregate patterns hold for individuals (`MEASUREMENT`) | district-level statements about donors or voters | ecological fallacy | 2.18, SOC-22 |
| Ties transmit influence (`CAUSAL`) | co-sponsorship, co-tenure, staff and donor networks | homophily reported as contagion | 2.19, SOC-23, SOC-24 |
| The network is complete and correctly merged, and centrality parameters do not decide the ranking (`DATA`, `FUNCTIONAL-FORM`) | name-disambiguated staff, lobbyist and donor graphs; Katz-Bonacich, PageRank | central actors are artifacts | 2.20, 2.22, SOC-25, SOC-27 |
| Dyads are independent; the ERGM is well specified (`STATISTICAL`) | dyadic regressions; tie-formation models | SEs far too small; degenerate fits | 2.21, SOC-26 |
| Cascade parameters are known (`CAUSAL`, `COMPUTATIONAL`) | IC/LT influence simulations | scenarios reported as estimates | 2.23, SOC-28 |
| One specification speaks for the evidence, and a visible trend has the right sign (`STATISTICAL`) | headline regressions; per-topic winners; "trend over significance" claims at low power | forking paths; false discoveries; Type S and Type M errors | 2.24, 2.25, SOC-29..31 |
| Rows are independent; pooled strata agree (`STATISTICAL`) | member-vote panels; House and Senate pooled | overconfident SEs; Simpson reversals | 2.26, SOC-32..34 |
| Roll calls and co-sponsorships represent behaviour, and lobbying contacts with members are observed (`DATA`) | position, loyalty and "effectiveness" measures; member-level lobbying links | agenda artifacts; outcome leakage; circular validation | 2.27, 2.28, SOC-35, SOC-36 |
| District identifiers are stable; this data use is permitted (`DATA`, `LEGAL`) | constituency covariates in panels; contributor records, platform text | wrong territory per member; legal exposure | 2.29, SOC-37, SOC-38 |

## 2. Tests

Write the estimand first (population, treatment and comparator, outcome, horizon, summary measure), then name the design that identifies it. If no design identifies a number that prices dollars, label the output "allocation heuristic under an assumed response curve", not an effect estimate.

| Claim in the system | Estimand | Designs that can identify it | Test |
|---|---|---|---|
| "Seating candidate X changes votes, money or seats" | effect of winning (party, seniority and committee access bundled), local to close races | close-election RD | 2.2 |
| "A marginal dollar buys Y votes or Y flip probability" | dose-response of spending | IV; within-unit panels; border and media-market designs | 2.3, 2.4 |
| "Contributions or lobbying buy access or policy" | access or policy effect | field experiments; exogenous shocks to committee power | 2.5 |
| "Event E, adopted at different times, changed Z" | cohort-by-period ATTs | staggered DiD, event study | 2.6 |
| "A policy in one state or firm changed Z" | ATT for one or a few units | synthetic control | 2.7 |
| Any covariate-adjusted observational estimate | ATE under selection on observables | adjustment plus sensitivity and timing audits | 2.8, 2.9 |
| "Who will flip" | a prediction, not an effect | evaluate as prediction (`machine-learning.md`) | — |

### 2.1 Benchmark implied money effects against credible designs
- **Tests:** whether a spending coefficient can be read as an effect and whether its size is plausible. Naive coefficients fail because incumbents spend more when threatened (Jacobson 1978), challenger quality raises both money and votes (Levitt 1994), and business money follows committee power in search of access (Powell & Grimmer 2016).
- **Assumptions of the test itself:** benchmarks transport imperfectly across offices, eras and countries, and experiments estimate contact effects, not dollar effects; a mismatch demands a justification, it does not prove an error.
- **Run it:** convert the implied effect to natural units (pp of vote share per $100k, or per SD of spending) and set it beside the benchmarks: rematch spending effects an order of magnitude below cross-sectional ones (Levitt 1994); incumbent and challenger marginal effects roughly equal once spending is instrumented (Gerber 1998); an average persuasive effect of campaign contact in U.S. general elections of about zero across 49 field experiments (Kalla & Broockman 2018); access to senior officials about three to four times higher when attendees were revealed as donors (Kalla & Broockman 2016); no detectable firm-value gain from corporate-PAC-backed close winners, with effects above 0.3% of firm value rejected (Fowler et al. 2020); in the 2004-12 presidential campaigns, a 1-SD rise in the partisan difference in TV advertising raised the partisan difference in vote share by about 0.5 pp, "taken at face value", with almost no turnout effect (Spenkuch & Toniatti 2018); lobbying that moves the probability of passage only slightly while private returns are large (Kang 2016). Refit with competitiveness, incumbency and quality controls and with unit fixed effects (2.4).
- **Pass criterion (fix before running):** the implied effect lies in the benchmark range, or the system names a design (2.2-2.7) that justifies the departure.
- **Failure signature:** the coefficient flips or collapses under competitiveness and quality controls; the effect sits in races that were already competitive; implied persuasion per dollar is many times the experimental evidence.
- **Source:** Jacobson (1978); Levitt (1994); Powell & Grimmer (2016); Gerber (1998); Kalla & Broockman (2016, 2018); Fowler et al. (2020); Spenkuch & Toniatti (2018); Kang (2016).
### 2.2 Close-election regression discontinuity (RD)
- **Tests:** the effect of barely winning on later outcomes such as votes, PAC flows or committee seats (Lee 2008). The estimand bundles party, seniority and committee access and is local to close races; it never prices a marginal dollar.
- **Assumptions of the test itself:** identification needs continuity of potential outcomes at the threshold, not as-if randomization (de la Cuesta & Imai 2016); density and balance tests have little power when few races are close. On sorting, bare House winners in 1942-2008 held financial and incumbency advantages that grew in the closest races (Caughey & Sekhon 2011), over 40,000 close races elsewhere showed no comparable pattern (Eggers et al. 2015), and the House evidence weakens once multiple testing is handled (de la Cuesta & Imai 2016). Test the population at hand rather than citing a side.
- **Run it:** (needs rdrobust) `rdrobust::rdrobust(y, margin, c = 0)` for robust bias-corrected CIs (Calonico et al. 2014); rerun with each predetermined covariate (lagged vote share, incumbency, pre-election receipts, race rating) as the outcome; halve and double the bandwidth; try placebo cutoffs; density test with `rddensity` (Cattaneo et al. 2020). Never use the archived CRAN `rdd` (as of 2026-09-30). Fallback with conventional CIs only, labelled as such:
```python
import statsmodels.formula.api as smf; from scipy.stats import binomtest
def rd_fit(df, y, x="margin", h=0.05):                  # local linear, triangular kernel, separate slopes each side
    d = df[df[x].abs() <= h].copy(); d["w"] = 1 - d[x].abs() / h; d["win"] = (d[x] >= 0).astype(int)
    return smf.wls(f"{y} ~ win * {x}", data=d, weights=d["w"]).fit(cov_type="HC1")
for h in (0.025, 0.05, 0.10): f = rd_fit(df, "later_yea_rate", h=h); print(h, f.params["win"], f.conf_int().loc["win"].tolist())
near = df[df["margin"].abs() <= 0.01]; print(binomtest(int((near["margin"] >= 0).sum()), len(near)).pvalue)  # crude density check
```
- **Pass criterion (fix before running):** no detectable density jump; each covariate's jump small in its own units with a CI covering zero; the same sign from half to double the bandwidth; the robust CI reported with the number of races inside the bandwidth.
- **Failure signature:** a density or covariate jump; sign changes across bandwidths; conventional CIs only; a global high-order polynomial; a handful of races within a few points; the estimate converted into dollars per vote.
- **Source:** Lee (2008); de la Cuesta & Imai (2016); Caughey & Sekhon (2011); Eggers et al. (2015); Calonico et al. (2014); Cattaneo et al. (2020).
### 2.3 Instrumental variables (IV) for spending
- **Tests:** the marginal effect of money through an instrument that shifts fundraising; in an average Senate race the incumbent's spending advantage was reported to add about 6% to vote share (Gerber 1998). The estimand is the compliers' LATE, not the ATE.
- **Assumptions of the test itself:** relevance, exclusion and monotonicity; no statistic tests exclusion in a just-identified model, so argue it and run placebos. Replications of 67 political-science IV studies found first-stage strength overstated under non-i.i.d. errors, 2SLS uncertainty understated by the usual t-test, and 2SLS/OLS ratios that grow as instruments weaken (Lal et al. 2024). The usual ±1.96 t-test has a true 5% size only when the first-stage F exceeds 104.7 (Lee et al. 2022), so "F > 10" is not a license (Andrews et al. 2019).
- **Run it:** (needs linearmodels) `IV2SLS.from_formula("y ~ 1 + x + [spend ~ z]", df).fit(cov_type="clustered", clusters=df["state"])`, then `.first_stage`; (needs ivDiag; R) `ivDiag()` reports effective F, Anderson-Rubin (AR), tF and bootstrap together. Fallback for one instrument, where the robust first-stage F equals the effective F (Andrews et al. 2019):
```python
import numpy as np, statsmodels.formula.api as smf
cl = dict(cov_type="cluster", cov_kwds={"groups": df["state"]})
F_eff = smf.ols("spend ~ z + x", df).fit(**cl).tvalues["z"] ** 2
def ar_p(b): return smf.ols("yb ~ z + x", df.assign(yb=df["y"] - b * df["spend"])).fit(**cl).pvalues["z"]
ar_set = [b for b in np.linspace(-2, 2, 401) if ar_p(b) > 0.05]   # AR 95% set; unbounded if it reaches the grid edge
```
- **Pass criterion (fix before running):** effective F and the 2SLS/OLS ratio reported; an AR (or tF) set that is bounded and excludes zero before any effect is claimed; the instrument does not predict pre-treatment outcomes.
- **Failure signature:** a weak first stage with conventional CIs; a 2SLS/OLS ratio far above 1 alongside a weak first stage; the instrument predicts lagged outcomes; a reduced form near zero.
- **Source:** Gerber (1998); Lal et al. (2024); Lee et al. (2022); Andrews et al. (2019).
### 2.4 Within-unit and border designs
- **Tests:** spending effects with candidate and district quality differenced out by rematches or unit fixed effects (Levitt 1994), and advertising or spending effects from exposure that changes at media-market or county borders; across 2000-2018 such effects were larger down-ballot than for president and worked mostly through persuasion (Sides et al. 2022).
- **Assumptions of the test itself:** quality is constant across rematches and changes in money are exogenous; a fixed-effects coefficient speaks per within-unit SD, not per pooled SD (Mummolo & Peterson 2018). At borders: no sorting, no spillover, no compound treatment (a state line bundles many policies), and an effect that may vary along the border (Keele & Titiunik 2015).
- **Run it:** fit pooled and within-unit models side by side, `smf.ols("vote ~ spend + C(matchup) + C(year)", df).fit(cov_type="cluster", cov_kwds={"groups": df["matchup"]})`, and compare `df["spend"].sub(df.groupby("matchup")["spend"].transform("mean")).std()` with `df["spend"].std()`; (needs fixest) `feols(vote ~ spend | matchup + year, df, cluster = ~matchup)`. Borders: border-pair fixed effects, covariate balance within pairs, leave-one-segment-out, and placebo borders drawn inside states (distances and joins in `geospatial.md`).
- **Pass criterion (fix before running):** pooled and within-unit estimates share a sign and fall inside the owner's pre-set ratio band; border pairs balanced; the sign survives dropping any segment; placebo borders null.
- **Failure signature:** a pooled coefficient far above the within-unit one; a tiny within-unit SD; national tides correlated with changes in money; one segment or market carries the effect; placebo borders show effects.
- **Source:** Levitt (1994); Mummolo & Peterson (2018); Sides et al. (2022); Keele & Titiunik (2015).
### 2.5 Field experiments: priors, and auditing one
- **Tests:** whether persuasion and access assumptions fit experimental evidence (2.1), and whether an experiment the system relies on was analysed the way it was randomized.
- **Assumptions of the test itself:** randomization happened as documented; units do not interfere unless interference is modelled; randomization inference tests the sharp null of no effect for any unit.
- **Run it:** block fixed effects for blocked designs; cluster-level or randomization inference for cluster assignment (`ri_p` in 2.26); intention-to-treat before per-protocol; attrition compared by arm. Model access (meetings, staff contact) separately from votes (Kalla & Broockman 2016).
- **Pass criterion (fix before running):** implied persuasion within the experimental range (Kalla & Broockman 2018) unless new causal evidence is named; inference matches assignment.
- **Failure signature:** large persuasion per dollar; access and votes merged into one outcome; a cluster-randomized study analysed person by person.
- **Source:** Kalla & Broockman (2016, 2018).
### 2.6 Staggered difference-in-differences (DiD) and event studies
- **Tests:** effects of events that switch on at different times (committee assignments, leadership changes, district bank failures, rule shocks). Two-way fixed effects (TWFE) averages all two-by-two comparisons, including later-treated units compared with already-treated ones, so cohort effects can get negative weights and the sign can reverse (Goodman-Bacon 2021; de Chaisemartin & D'Haultfœuille 2020). Heterogeneity-robust estimators avoid those comparisons (Callaway & Sant'Anna 2021; Sun & Abraham 2021). Reanalysing 49 political-science TWFE studies, robust estimators gave qualitatively similar but highly variable results, parallel trends was often unsupported, and many designs were underpowered (Chiu et al. 2026).
- **Assumptions of the test itself:** parallel trends in untreated outcomes and no anticipation still bind the robust estimators. A non-significant pre-trend test is not evidence of parallel trends: pre-tests have low power, and conditioning on passing them distorts the post-period estimate (Roth 2022). Bound the violation instead (Rambachan & Roth 2023).
- **Run it:** (needs fixest) `feols(y ~ sunab(cohort, period) | unit + period, df)`, with never-treated units given a cohort outside the panel; (needs did, bacondecomp, HonestDiD) `att_gt()` + `aggte()`, `bacon()`, `createSensitivityResults_relativeMagnitudes()`. Plant a pre-trend in a copy and check that the pre-period diagnostic flags it (`scripts/mutation_check.py` automates such mutants). Fallback: cohort-by-period effects against never-treated units (balanced panel, integer periods, no covariates; bootstrap units for intervals):
```python
import pandas as pd
def att_gt(df, y="y", unit="unit", t="period", g="cohort"):          # g: first treated period; NaN = never treated
    w = df.pivot(index=unit, columns=t, values=y); coh = df.groupby(unit)[g].first(); out = []
    for gg in sorted(coh.dropna().astype(int).unique()):
        for tt in w.columns.drop(gg - 1):                             # base = gg - 1; earlier periods are placebos
            d = w[tt] - w[gg - 1]; out.append((gg, tt, d[coh == gg].mean() - d[coh.isna()].mean()))
    return pd.DataFrame(out, columns=["cohort", "period", "att"])
```
- **Pass criterion (fix before running):** two robust estimators agree in sign; TWFE within 50% of them or not reported; the relative-magnitude breakdown value above 1. If that bound cannot be computed, the parallel-trends row is `UNVERIFIED-HERE` and the largest pre-period deviation is printed beside the effect.
- **Failure signature:** TWFE and robust estimates disagree in sign or size; the decomposition is dominated by later-versus-earlier comparisons; pre-period coefficients trend; breakdown at a bound of 1 or less; results hinge on which units count as never treated.
- **Source:** Goodman-Bacon (2021); de Chaisemartin & D'Haultfœuille (2020); Callaway & Sant'Anna (2021); Sun & Abraham (2021); Chiu et al. (2026); Roth (2022); Rambachan & Roth (2023).
### 2.7 Synthetic control (SC)
- **Tests:** effects for one or a few treated aggregates, such as one state's rule change on a sector's giving (Abadie et al. 2010).
- **Assumptions of the test itself:** a long pre-period with good fit; the treated unit inside the donors' convex hull; donors untreated and free of spillover; no large idiosyncratic shocks (Abadie 2021); placebo inference treats units as exchangeable.
- **Run it:** (needs Synth, tidysynth or scpi; R; augsynth and R synthdid are GitHub-only as of 2026-09-30) fallback on pre-period outcomes only (rows = periods, columns = donors). Placebos in space: rerun with each donor as the treated unit and the rest as its pool; the treated unit's rank among the J + 1 ratios gives p = rank / (J + 1). Placebos in time: move T0 earlier. Then drop each positive-weight donor in turn.
```python
import numpy as np; from scipy.optimize import minimize
def sc_w(Y0, y1):                                    # donor weights >= 0 summing to 1
    k = Y0.shape[1]; cons = {"type": "eq", "fun": lambda w: w.sum() - 1}
    return minimize(lambda w: np.sum((y1 - Y0 @ w) ** 2), np.full(k, 1 / k), bounds=[(0, 1)] * k, constraints=cons, method="SLSQP").x
def rmspe_ratio(Y0, y1, T0):                         # post/pre RMSPE; the first T0 rows are pre-treatment
    gap = y1 - Y0 @ sc_w(Y0[:T0], y1[:T0]); return np.sqrt(np.mean(gap[T0:] ** 2) / np.mean(gap[:T0] ** 2))
```
- **Pass criterion (fix before running):** pre-period RMSPE small in the outcome's units (threshold fixed in advance); the treated ratio ranks first or within the pre-set top share; the sign survives leave-one-donor-out; backdated treatment shows no effect.
- **Failure signature:** poor pre-fit; one donor carries most of the weight; the treated ratio is ordinary among placebos; leave-one-out flips the sign; backdating produces effects.
- **Source:** Abadie et al. (2010); Abadie (2021).
### 2.8 Sensitivity to unobserved confounding
- **Tests:** how strong an omitted confounder would have to be to erase or flip an estimate.
- **Assumptions of the test itself:** robustness-value bounds apply to linear regression and assume the unobserved confounder is at most k times as strong as an observed benchmark (Cinelli & Hazlett 2020); E-values work on the risk-ratio scale (VanderWeele & Ding 2017); Oster's δ depends on R²max, and the script's default `--rmax 1.3x` is her suggested min(1.3 × the controlled R², 1) (Oster 2019); Rosenbaum's Γ is for matched designs (Rosenbaum 2002).
- **Run it:** `python scripts/confounding_sensitivity.py --mode sensemakr --estimate 0.042 --se 0.011 --dof 431 --r2dz-bench 0.12 --r2yz-bench 0.30 --kd 1,2,3 --rv-min 0.30` gives the treatment's partial R² with the outcome, RV_q, RV_{q,α} and benchmark-bounded estimates; the same script with `--mode evalue --rr 1.8 --lo 1.2 --hi 2.6` (or `--or X [--rare]`, `--hr X [--rare]`, `--smd D --se SE`) gives E-values of the estimate and of the CI limit nearest the null, and with `--mode oster --beta-short 0.061 --r2-short 0.08 --beta-long 0.042 --r2-long 0.31 --rmax 1.3x` gives δ at β = 0 and β* at δ = 1; `--table rows.csv` runs many rows. Benchmark inputs come from t-statistics, partial R² = t² / (t² + df), using the benchmark's t in the treatment model (`--r2dz-bench`) and in the outcome model (`--r2yz-bench`); political benchmarks are party, an ideology score, seniority and district sector-employment share. (needs sensemakr) `sensemakr(fit, treatment = "spend", benchmark_covariates = "partyR", kd = 1:3)`.
- **Pass criterion (fix before running):** RV_q ≥ `--rv-min` (set it before running to the strongest benchmark's partial R²; default 0.05). The bias-adjusted estimate keeps its sign at every `--kd` multiple, and a flip at kd ≤ `--kd-kill` (default 1) is KILLED. RV_{q,α} is reported, not judged. Oster δ ≥ `--delta-min` (default 1). E-value ≥ `--e-min`. (`--e-min` defaults to 2.0; set it from the strongest measured confounder's risk ratio.)
- **Failure signature:** RV_q below a known confounder's partial R²; a sign flip within the benchmark multiples; δ below 1; an E-value or Γ near 1.
- **Source:** Cinelli & Hazlett (2020); VanderWeele & Ding (2017); Oster (2019); Rosenbaum (2002).
### 2.9 Post-treatment bias and what the regression weights
- **Tests:** whether any control or sample filter is itself affected by treatment (Montgomery et al. 2018), and which units carry the estimate: OLS weights units by the conditional variance of treatment, so the effective sample can differ sharply from the nominal one (Aronow & Samii 2016).
- **Assumptions of the test itself:** each variable's measurement date is known; causal order is argued from the design, not read off the data.
- **Run it:** a timing table with one row per covariate (measured at, treatment date, verdict); watch for committee assignment or co-sponsorship dated after contributions, salience measured after the shock, and samples cut to winners, voters or bills that reached the floor. Weight shares by stratum: `w = smf.ols("spend ~ seniority + C(state)", df).fit().resid ** 2; print((w / w.sum()).groupby(df["party"]).sum())`. Compare classical and robust SEs; a large gap signals misspecification that robust SEs do not fix (King & Roberts 2015). For interactions, check linearity and the moderator's common support (Hainmueller et al. 2019).
- **Pass criterion (fix before running):** no post-treatment control; no outcome-selected sample; weight shares reported by stratum; any large SE gap explained.
- **Failure signature:** the estimate moves sharply when post-treatment controls are dropped; one stratum carries most of the weight unreported; interaction effects exist only outside the moderator's support.
- **Source:** Montgomery et al. (2018); Aronow & Samii (2016); King & Roberts (2015); Hainmueller et al. (2019).
### 2.10 Claim language follows the identification
- **Tests:** whether the verbs in findings match the design.
- **Assumptions of the test itself:** a lexical scan only finds candidates; it misses paraphrased causal claims and flags benign ones, so a person reads every hit.
- **Run it:** tag each finding by claim type (descriptive, associational, predictive, causal); causal ones also name the estimand, the design and the state of the confounding, selection, collider and reverse-causation risks (assessed, unresolved, not applicable). Then scan each line of the findings with `re.compile(r"\b(caus\w*|effect of|leads? to|results? in|drives?|boosts?|buys?|increases?|reduces?)\b", re.I)` and read every hit not tagged causal.
- **Pass criterion (fix before running):** every hit is a tagged causal claim with its estimand and design, or is reworded to "associated with".
- **Failure signature:** "controlled for confounders" offered as proof of exchangeability; causal verbs in associational findings; "confirmed" or "proven" for a single analysis.
- **Source:** claim-typing idea adapted from K-Dense `hypothesis-generation` (§5).
### 2.11 Construct validity: volume proxies and composite weights
- **Tests:** whether a score measures its systematized concept (background concept, systematized concept, indicators, scores) with content, convergent, discriminant and nomological evidence (Adcock & Collier 2001); the first discriminant test is against activity volume. For composite indices ("influence", "priority", "power" scores): whether the order depends on contestable weights.
- **Assumptions of the test itself:** the behavioural criterion (roll calls on the issue, interest-group ratings) is itself valid and not a volume proxy; indicators behave the same across party, chamber, Congress and platform. Stable order under tested weights does not establish validity, and agreement or reliability is not validity.
- **Run it:** bootstrap over units the gap `|spearman(score, criterion)| - |spearman(score, volume)|`, with posts, press releases or speeches as volume, overall and within each party and chamber. Weights: move one weight at a time by ±25%, renormalize, and record Kendall's τ against the declared order and the top-k overlap (`scipy.stats.kendalltau`); for joint perturbation, pass the weights as parameters to `scripts/global_sensitivity.py`.
- **Pass criterion (fix before running):** the gap above zero with its bootstrap interval above zero in every stratum; Kendall's τ and top-k overlap above the owner's pre-set floors for every weight move.
- **Failure signature:** the score tracks volume as closely as behaviour; the relationship flips by party; the top of a ranking changes when one contestable weight moves.
- **Source:** Adcock & Collier (2001); weight-sensitivity idea from K-Dense `scholar-evaluation` (§5).
### 2.12 Text-as-data validation; stance is not sentiment
- **Tests:** whether a text measure is valid for this corpus and task. No text method is best everywhere, so validate each use (Grimmer & Stewart 2013); dictionary sentiment validates poorly against manual, crowd and supervised coding (van Atteveldt et al. 2021); sentiment is not stance toward a target (Bestvater & Monroe 2023); if the estimand is a category proportion, estimate proportions directly instead of counting classified documents (Hopkins & King 2010).
- **Assumptions of the test itself:** the gold set is correct and a probability sample of the corpus (2.14).
- **Run it:** `for g, d in gold.groupby(["chamber", "party"]): print(g, classification_report(d["gold"], d["pred"], zero_division=0))` (`from sklearn.metrics import classification_report`), plus a confusion matrix per subgroup.
- **Pass criterion (fix before running):** macro-F1 and per-class recall above the pre-set floor in every subgroup, and the largest subgroup gap below its pre-set limit.
- **Failure signature:** a convenience validation sample; overall accuracy only, on imbalanced classes; no subgroup breakdown; sentiment used as a position on a bank, a regulator or a bill.
- **Source:** Grimmer & Stewart (2013); van Atteveldt et al. (2021); Bestvater & Monroe (2023); Hopkins & King (2010).
### 2.13 LLM annotation: validity, drift and replay
- **Tests:** whether large-language-model (LLM) labels are valid for the codebook, stable and reproducible. Capability varies by task: LLMs beat crowd workers on several tasks (Gilardi et al. 2023), must be tested against the real codebook in stages (Halterman & Keith 2026), and for stance detection the largest models do best with few examples while fine-tuned small models stay competitive (Chae & Davidson 2026). Replicating 37 annotation tasks with 18 models over 2,361 hypotheses, about 31% of hypotheses reached wrong conclusions with state-of-the-art models and about 50% with small ones; human annotations protect against false positives, and regression-estimator corrections can restore valid inference but trade Type I against Type II errors (Baumann et al. 2025, preprint). LLMs as simulated survey respondents are a different use with separate validity problems (Argyle et al. 2023).
- **Assumptions of the test itself:** the probe panel represents the corpus; prompt paraphrases preserve meaning; naive use requires errors that are non-differential by party, gender and chamber.
- **Run it:** store with every label the model ID and snapshot date, the prompt's SHA-256, temperature and seed; re-annotate a frozen probe panel on a schedule and report the change rate; label under three or more meaning-preserving prompts and report the flip rate `(labels.nunique(axis=1) > 1).mean()`; report the items of the behavioural-science LLM checklist (Feuerriegel et al. 2026). Proprietary models need explicit justification, and open, pinned models are preferred for replay (Palmer et al. 2024).
- **Pass criterion (fix before running):** drift and paraphrase flip rates below pre-set limits; subgroup error gaps within limits; a pinned model version. A closed model with no pinned snapshot leaves replay `UNVERIFIED-HERE`.
- **Failure signature:** accuracy differs by party, gender or chamber; conclusions change under paraphrase; the provider silently updated the model; "validation" is one LLM agreeing with another.
- **Source:** Gilardi et al. (2023); Halterman & Keith (2026); Chae & Davidson (2026); Baumann et al. (2025); Argyle et al. (2023); Feuerriegel et al. (2026); Palmer et al. (2024).
### 2.14 Downstream inference with imperfect labels (DSL, PPI)
- **Tests:** whether regressions and aggregates built on predicted labels have valid estimates and intervals. Plugging surrogate labels in directly gives substantial bias and invalid CIs even at 80-90% accuracy; design-based supervised learning (DSL) corrects this with a doubly robust pseudo-outcome built from a gold subsample drawn with known probabilities (Egami et al. 2023). Related: prediction-powered inference (PPI; Angelopoulos et al. 2023) and ML predictions as covariates (Fong & Tyler 2021). Imperfect human gold distorts validation itself (Song et al. 2020).
- **Assumptions of the test itself:** every gold item's selection probability is known, recorded and positive (stratified sampling is fine; convenience or active-learning picks are not, unless the probabilities were recorded); the number of independent coders and alpha are reported (2.15), and single-coder gold is a stated limitation; the labelling model was not trained on the gold items (otherwise cross-fit).
- **Run it:** (needs ppi-python, or R `dsl` (GitHub-only) or `ipd`) fallbacks, with `f` the model label and the gold items a sample of the same corpus; when the label is a covariate rather than the outcome, use `dsl` or the Fong & Tyler (2021) correction:
```python
import numpy as np, statsmodels.formula.api as smf
def ppi_mean(f_all, f_gold, y_gold, z=1.96):          # label prevalence, rectified by gold residuals
    r = y_gold - f_gold; est = f_all.mean() + r.mean()
    se = np.sqrt(f_all.var(ddof=1) / len(f_all) + r.var(ddof=1) / len(r)); return est, est - z * se, est + z * se
df["y_dsl"] = df["f"] + df["in_gold"] / df["pi"] * (df["y_gold"].fillna(0) - df["f"])   # DSL-style pseudo-outcome
fit = smf.ols("y_dsl ~ spend + party", df).fit(cov_type="HC1")    # the dsl package adds cross-fitting
```
- **Pass criterion (fix before running):** every label feeding a regression, flip model or frontier passes through DSL or PPI, or carries propagated label error; corrected and naive estimates are shown together.
- **Failure signature:** naive regression on LLM labels; convenience gold; single-coder gold presented as validated; CIs that ignore label uncertainty; the same LLM output used both to choose items and to measure them.
- **Source:** Egami et al. (2023); Angelopoulos et al. (2023); Fong & Tyler (2021); Song et al. (2020).
### 2.15 Rater agreement: Krippendorff's alpha
- **Tests:** whether coders agree beyond chance; alpha handles any number of coders, missing data and nominal, ordinal or interval metrics, with a bootstrap CI (Hayes & Krippendorff 2007).
- **Assumptions of the test itself:** coders rate independently; units are a random sample; the metric matches the scale. The usual cutoffs (alpha at least .80, with .667 for tentative conclusions) come from Krippendorff's textbook, which this skill's research did not verify (UNVERIFIED): treat them as conventions. Agreement is necessary for validity, not sufficient. With one coder alpha cannot be computed: record `UNVERIFIED-HERE` and state the limitation.
- **Run it:** (needs `krippendorff` or R `irr`) nominal fallback; bootstrap units for the CI:
```python
import itertools, numpy as np
def k_alpha_nominal(units):                          # units: one list of labels per coded item, missing omitted
    cats = sorted({v for u in units for v in u}); ix = {c: i for i, c in enumerate(cats)}; o = np.zeros((len(cats),) * 2)
    for u in (u for u in units if len(u) > 1):
        for a, b in itertools.permutations(u, 2): o[ix[a], ix[b]] += 1 / (len(u) - 1)
    n_c = o.sum(1); n = n_c.sum(); return 1 - (n - 1) * (o.sum() - np.trace(o)) / (n ** 2 - (n_c ** 2).sum())
```
- **Pass criterion (fix before running):** the bootstrap lower bound meets the owner's pre-set floor on a random subset, overall and per subgroup.
- **Failure signature:** percent agreement only; kappa on highly imbalanced classes (the prevalence paradox); reliability computed on a non-random subset; single-coder gold presented without its limitation.
- **Source:** Hayes & Krippendorff (2007).
### 2.16 Measurement error and attenuation
- **Tests:** how noise biases estimates. Classical error in a regressor attenuates its slope by the reliability ratio λ = var(true) / var(observed); the disattenuated correlation is r_xy / √(r_xx · r_yy) (Spearman 1904); error correlated with the truth or with covariates biases in any direction; error in a control leaves residual confounding. Remedies: regression calibration and SIMEX (Carroll et al. 2006).
- **Assumptions of the test itself:** the reliability estimate is valid for this population, and the error is classical when the simple correction is used.
- **Run it:** `b_obs / lam` and `r_xy / np.sqrt(r_xx * r_yy)` across the reliability's CI; estimate reliability separately in each group before comparing groups.
- **Pass criterion (fix before running):** the conclusion survives correction across the reliability interval; groups are compared only at equal or corrected reliability.
- **Failure signature:** the coefficient grows when a better-measured version is used; unequal reliability manufactures an interaction (score × party).
- **Source:** Spearman (1904); Carroll et al. (2006).
### 2.17 Ideal points and roll-call scaling
- **Tests:** placements of legislators on latent dimensions (Poole & Rosenthal 1985; Clinton et al. 2004).
- **Assumptions of the test itself:** spatial utility; low dimensionality; sincere voting; votes independent given the ideal point; identification by normalization or anchors; comparisons across Congresses only through a bridge; roll calls selected by the agenda (2.27). Polarization can manufacture evidence of one dimension, so check inside each party caucus (Aldrich et al. 2014).
- **Run it:** (needs wnominate, pscl or emIRT; R only) crude dimensionality fallback, overall and within each party, with `V` members × roll calls coded 1/0/NaN: `M = np.nan_to_num(V - np.nanmean(V, axis=0)); s = np.linalg.svd(M, compute_uv=False) ** 2; print(s[:3] / s.sum())`.
- **Pass criterion (fix before running):** sign and scale fixed by named anchors and stable across runs; the second dimension's share reported within each party; issue votes' loadings checked, not assumed onto dimension 1; the bridge stated.
- **Failure signature:** sign or scale flips across runs; finance votes load on dimension 2; lopsided votes dropped by default filters without disclosure; abstentions treated as missing at random.
- **Source:** Poole & Rosenthal (1985); Clinton et al. (2004); Aldrich et al. (2014).
### 2.18 Ecological inference (EI) and MRP
- **Tests:** whether aggregates license individual-level claims; alone they do not (Robinson 1950), and EI adds deterministic bounds plus a no-aggregation-bias assumption (King 1997). Multilevel regression and poststratification (MRP) estimates small-area opinion from national surveys (Lax & Phillips 2009).
- **Assumptions of the test itself:** the bounds use only the accounting identity; MRP needs a correct multilevel model, response ignorable within cells, and a poststratification frame for the district plan in force, whose small-area census counts carry disclosure-avoidance noise (`geospatial.md`).
- **Run it:** bounds for a two-by-two table with group share `X` and overall rate `T` per unit: `lo = np.clip((T - (1 - X)) / X, 0, 1); hi = np.clip(T / X, 0, 1)`; check every EI estimate against them; (needs eiPack, lme4 or brms) for the models. CRAN `eiCompare` and `autoMrP` are archived (as of 2026-09-30).
- **Pass criterion (fix before running):** no individual-level wording from aggregates; estimates inside the bounds; the MRP frame dated to the current plan; intervals shown.
- **Failure signature:** "donors in district X prefer..." from district totals; estimates outside the bounds; MRP estimates collapsed toward the national mean; a frame from the old plan.
- **Source:** Robinson (1950); King (1997); Lax & Phillips (2009).
### 2.19 Homophily versus contagion; what an edge is
- **Tests:** whether behavioural similarity between tied legislators, staffers or donors reflects influence. Homophily, contagion and shared covariates are generically confounded in observational network data (Shalizi & Thomas 2011); in a 27.4M-user network, earlier methods overstated peer influence by 300-700% (Aral et al. 2009); congressional staff exchanges predict similarity in voting and effectiveness, with selection the core threat (Montgomery & Nyhan 2017). Co-sponsorship, co-tenure, co-appearance and shared committees are exposure to a common context, not social ties or influence channels by default; co-sponsorship can measure "connectedness" as a construct (Fowler 2006), which then needs its own validation (2.11).
- **Assumptions of the test itself:** a placebo outcome shares the confounding but cannot travel through the tie; tie dates are recorded.
- **Run it:** date every tie against the behaviour; test placebo outcomes (unrelated issues, pre-period behaviour) and leads (future neighbours' adoption must not predict current adoption); add party × region × committee covariates and watch the influence coefficient; prefer exogenous shocks to ties.
- **Pass criterion (fix before running):** an influence claim only with time ordering, null placebos and leads, and exogenous variation; otherwise the wording is associational.
- **Failure signature:** influence shrinks once covariates enter; contagion appears on placebos or leads; ties formed after the behaviour.
- **Source:** Shalizi & Thomas (2011); Aral et al. (2009); Montgomery & Nyhan (2017); Fowler (2006).
### 2.20 Missing edges, sampling and edge error
- **Tests:** how incomplete or wrong ties distort network statistics: missing data and boundary misspecification (Kossinets 2006); false-positive and false-negative nodes and edges, false merges and false splits (Wang et al. 2012); centrality under imperfect data (Borgatti et al. 2006).
- **Assumptions of the test itself:** random edge deletion mimics the real error process; real errors (disambiguation merges, missing filings) are rarely random, so simulate those too.
- **Run it:** the snippet deletes edges; repeat it with added random edges, merges of similar-name pairs (`nx.contracted_nodes`) and splits:
```python
import networkx as nx, numpy as np
def top_k(H, k): c = nx.pagerank(H); return set(sorted(c, key=c.get, reverse=True)[:k])
def topk_overlap(G, k=10, drop=0.10, reps=200, seed=20260930):      # mean top-k overlap after deleting a share of edges
    rng, E = np.random.default_rng(seed), list(G.edges()); base, m = top_k(G, k), int(len(E) * (1 - drop))
    return np.mean([len(base & top_k(G.edge_subgraph([E[i] for i in rng.choice(len(E), m, replace=False)]), k)) / k for _ in range(reps)])
```
- **Pass criterion (fix before running):** mean top-10 overlap at or above the owner's pre-set floor at 5%, 10% and 20% perturbation.
- **Failure signature:** the top central actors change under small perturbations; clustering or centralization swings.
- **Source:** Kossinets (2006); Wang et al. (2012); Borgatti et al. (2006).
### 2.21 Dyadic dependence: QAP, MRQAP and ERGMs
- **Tests:** dyadic regressions (co-voting on shared staff, state or committee; PAC-member dyads) without assuming independent dyads (Krackhardt 1988), and exponential random graph models (ERGMs) of tie formation with explicit dependence terms, including co-sponsorship networks (Cranmer & Desmarais 2011).
- **Assumptions of the test itself:** QAP needs nodes exchangeable under the null; Freedman-Lane and double semi-partialling (DSP) are the permutation schemes most robust to collinearity and autocorrelation (Dekker et al. 2007). ERGMs need a correctly specified dependence structure, homogeneous parameters, a complete boundary, a converged MCMC-MLE and a model that is not near-degenerate.
- **Run it:** (needs sna; R) `netlm(y, x, nullhyp = "qapspp")` is DSP, and the default `"qap"` currently equals it (per the `sna` documentation, as of 2026-09-30); dyadic cluster-robust SEs are the parametric alternative (Aronow et al. 2015). ERGM (needs ergm; R only, otherwise `UNVERIFIED-HERE`): `fit <- ergm(net ~ edges + nodematch("party") + gwesp(0.5, fixed = TRUE)); mcmc.diagnostics(fit); plot(gof(fit))`; `btergm` for networks over time. Fallback DSP for one focal n × n predictor `X1` with a control `X2`:
```python
import numpy as np, statsmodels.api as sm
def dsp_qap(Y, X1, X2, B=999, seed=20260930):
    n = len(Y); off = ~np.eye(n, dtype=bool); Z = sm.add_constant(X2[off])
    E1 = np.zeros((n, n)); E1[off] = sm.OLS(X1[off], Z).fit().resid           # partial X2 out of X1
    t = lambda E: sm.OLS(Y[off], np.column_stack([Z, E[off]])).fit().tvalues[-1]
    rng = np.random.default_rng(seed); t0 = t(E1); tp = [t(E1[np.ix_(p, p)]) for p in (rng.permutation(n) for _ in range(B))]
    return t0, (1 + np.sum(np.abs(tp) >= abs(t0))) / (B + 1)
```
- **Pass criterion (fix before running):** dyadic inference by DSP or Freedman-Lane permutation, or dyadic-robust SEs; ERGM chains mix, and simulated networks reproduce degree, edgewise-shared-partner and geodesic distributions not used in fitting (Hunter et al. 2008).
- **Failure signature:** plain OLS SEs on dyads; y-permutation QAP with collinear predictors (inflated type I error); ERGM simulations that come out empty or complete; estimates that swing with small specification changes.
- **Source:** Krackhardt (1988); Cranmer & Desmarais (2011); Dekker et al. (2007); Aronow et al. (2015); Hunter et al. (2008).
### 2.22 Centrality: Katz-Bonacich decay and PageRank damping
- **Tests:** whether "who is central" survives the index's free parameter. Power (Katz-type) centrality has an attenuation parameter (Bonacich 1987); the "key player" equals Katz-Bonacich centrality in linear-quadratic network games only when the decay is below 1/λ_max (Ballester et al. 2006).
- **Assumptions of the test itself:** λ_max comes from the same weighted, directed matrix the index uses.
- **Run it:** `lam = max(abs(np.linalg.eigvals(nx.to_numpy_array(G))))`; for a in 0.1, 0.3, 0.5, 0.7 and 0.9 compute `nx.katz_centrality_numpy(G, alpha=a / lam)` and report the minimum `scipy.stats.kendalltau` between the orderings; do the same for PageRank damping from 0.75 to 0.95; report each index's Spearman correlation with degree. (needs netrankr; R) `neighborhood_inclusion()` shows the orderings every index must respect.
- **Pass criterion (fix before running):** decay strictly below 1/λ_max; the minimum Kendall τ across the admissible range above the pre-set floor; the correlation with degree reported.
- **Failure signature:** the ranking changes within the admissible range; decay at or above 1/λ_max; the index is essentially degree (volume); directed and undirected versions disagree.
- **Source:** Bonacich (1987); Ballester et al. (2006); Borgatti et al. (2006).
### 2.23 Cascade models (IC/LT): identifiability and influence simulations
- **Tests:** whether independent-cascade (IC) edge probabilities or linear-threshold (LT) weights and thresholds can be learned from the data at hand (Kempe et al. 2003). They are learnable from time-stamped activation traces on a known graph (Saito et al. 2008; Gomez-Rodriguez et al. 2012), but recovery needs many cascades, and the number needed rises with node degree (Netrapalli & Sanghavi 2012); influence maximization can be unstable under misspecified parameters (He & Kempe 2016); observational cascades still confound influence with homophily (2.19). Static ties (co-sponsorship, co-tenure, committee overlap) do not identify activation probabilities, and LT thresholds are latent draws whose distribution can only be assumed; without timed adoptions (dated co-sponsorships or position statements), the parameters are assumptions and the simulation is scenario analysis.
- **Assumptions of the test itself:** the swept ranges are plausible; Monte-Carlo error is small next to the gaps acted on.
- **Run it:** record each parameter's status (fitted from cascades, literature-shaped, arbitrary) in the model card; `python scripts/global_sensitivity.py --problem ic_params.json --method morris --design-only --N 64`; the owner runs the simulator on `design.csv` (owner-gated); then `python scripts/global_sensitivity.py --problem ic_params.json --method morris --design design.csv --outputs outputs.csv`; replication sufficiency and seed-set stability with `python scripts/mc_error.py --data runs.csv --rep rep --entity node --score spread --topk 10` (one row per replication and node; MC-DEGENERATE flags a metric that never varies across replications, meaning a deterministic model or a seed that never reached it; `engineering-simulation.md`); held-out cascades wherever they exist.
- **Pass criterion (fix before running):** parameters labelled assumed unless learned from timed cascades; seed rankings stable under a ±20% perturbation of p; the Monte-Carlo SE well below the gaps acted on.
- **Failure signature:** edge probabilities set by hand or copied from tie strength; no held-out cascades; seed rankings change under ±20% p; no MCSE, or so few replications (tens) that the MCSE rivals the differences interpreted.
- **Source:** Kempe et al. (2003); Saito et al. (2008); Gomez-Rodriguez et al. (2012); Netrapalli & Sanghavi (2012); He & Kempe (2016).
### 2.24 Forking paths, multiplicity and preregistration
- **Tests:** how much of a result comes from analytic choices (Gelman & Loken 2014; Simonsohn et al. 2020), given that many analysts working on the same data and question disperse widely (Breznau et al. 2022); false-discovery control across families such as per-topic flip models or per-sector regressions (Benjamini & Hochberg 1995); whether choices were fixed before the data were seen, remembering that pre-analysis plans are often imperfectly followed, so deviations must be disclosed (Ofosu & Posner 2023).
- **Assumptions of the test itself:** every specification on the curve is defensible a priori and the set was not tuned after seeing results; the family is counted from the analysis log, not from the report; BH assumes independent or positively dependent tests.
- **Run it:** loop over optional-control subsets × samples (all, House, Senate, each Congress), fitting `smf.ols(...).fit(cov_type="cluster", cov_kwds={"groups": d["member"]})`; collect the coefficient and CI, sort, and report the share with the headline's sign, the median and the 10th-90th percentiles ((needs specr or specification-curve) for plots). Per family: `statsmodels.stats.multitest.multipletests(p, method="fdr_bh")`. Diff the executed analysis against the plan; list each deviation with date, reason and decider.
- **Pass criterion (fix before running):** at least the pre-set share of defensible specifications share the headline sign, with the headline's position on the curve reported; q-values reported per family; every deviation disclosed.
- **Failure signature:** fewer than the pre-set share of defensible specifications share the headline sign; a headline picked from the curve's tail; dozens of topic models with the winners reported unadjusted; exploratory results written up as predictions.
- **Source:** Gelman & Loken (2014); Simonsohn et al. (2020); Breznau et al. (2022); Benjamini & Hochberg (1995); Ofosu & Posner (2023).
### 2.25 Low power, Type S and M errors, and "trend over significance"
- **Tests:** whether a visible trend has the right sign and a plausible size. Across 16,000+ tests in about 2,000 political-science articles, median power was about 10% and about 1 test in 10 had 80% power for consensus effect sizes (Arel-Bundock et al. 2026); a mass reproduction of 110 economics and political-science papers was published in 2026 with a correction notice, so read the corrected text before quoting its figures (Brodeur et al. 2026). At low power, estimates that clear a bar are exaggerated (Type M) and a nontrivial share have the wrong sign (Type S) (Gelman & Carlin 2014). Leading with sign, size and consistency, and judging usefulness by backtest, fits the ASA statement and the case for abandoning bright-line significance (Wasserstein & Lazar 2016; McShane et al. 2019), but only when the sign is shown stable across specifications (2.24) and backtest windows and a Type-S estimate is reported; check a trend "seen" in a chart with a lineup test (`data-visualization.md`).
- **Assumptions of the test itself:** the plausible effect size A comes from prior designs or benchmarks (2.1), never from the estimate being judged.
- **Run it:** (needs retrodesign; R) or the snippet; the chance that one estimate has the wrong sign is `norm.cdf(-A / s)`; for stability over time run `python scripts/backtest_eval.py --data f.csv --actual y --forecast yhat --time cycle --benchmark naive --windows 5`.
```python
import numpy as np; from scipy.stats import norm
def retrodesign(A, s, alpha=0.05, sims=200_000, seed=20260930):   # A > 0: plausible true effect; s: its SE
    z = norm.ppf(1 - alpha / 2); lam = A / s; power = norm.sf(z - lam) + norm.cdf(-z - lam)
    est = A + s * np.random.default_rng(seed).standard_normal(sims); sig = np.abs(est) > z * s
    return power, norm.cdf(-z - lam) / power, np.abs(est[sig]).mean() / A   # power, Type S, exaggeration ratio
```
- **Pass criterion (fix before running):** Type S at most about 10% at the plausible effect; the model wins, and keeps its sign, in at least `--min-window-share` of windows (default 0.75), fixed before running; the sign shared by at least the pre-set share of specifications (2.24); power or MDE stated.
- **Failure signature:** the model wins, and keeps its sign, in fewer than `--min-window-share` of windows (default 0.75); the sign flips across specifications; Type S above about 10%; a significant estimate many times the plausible effect.
- **Source:** Arel-Bundock et al. (2026); Brodeur et al. (2026); Gelman & Carlin (2014); Wasserstein & Lazar (2016); McShane et al. (2019).
### 2.26 Dependence, effective N and strata in legislative data
- **Tests:** whether standard errors and the claimed evidence respect how units were sampled or assigned. Cluster when assignment or sampling is clustered (Abadie et al. 2023); with few clusters use the wild cluster bootstrap (Cameron et al. 2008); cluster two ways for member × roll call (Cameron et al. 2011); practice guide in MacKinnon et al. (2023); dyads in 2.21. A Congress has at most 535 voting members plus delegates, votes nest in members and roll calls, party-line voting shrinks the effective N, and each Congress is one draw of an agenda with shocks common to all members. Never cluster on party (two clusters) or Congress (a handful); enter them as fixed effects or strata.
- **Assumptions of the test itself:** clusters sit at the level of assignment or sampling, and there are enough of them; the design-effect formula assumes similar cluster sizes and exchangeable correlation within member; randomization inference must permute the way treatment was assigned.
- **Run it:** `Rscript scripts/regression_report.R --data votes.csv --formula "yea ~ contrib + seniority + party" --cluster member --cluster2 rollcall --strata chamber` prints the verbatim `summary(lm())`, then a labelled inference block with G, the LM-* diagnostics (LM-UNITS for too few clusters, LM-LEVERAGE for rows fitted exactly) and a one-line trend; with few clusters, `--cluster state --vcov CR2 --boot wild --B 999` (CR2 needs the sandwich package). (needs fixest) `feols(yea ~ contrib | member + rollcall, df, cluster = ~member + rollcall)`. CRAN `fwildclusterboot` and `summclust` are archived (as of 2026-09-30); use the script or Python `wildboottest`. Effective N = rows / (1 + (m̄ − 1) · ICC), with m̄ the mean rows per member and ICC = cov_re / (cov_re + scale) from `smf.mixedlm("yea ~ 1", df, groups=df["member"]).fit()`. Report every pooled estimate by chamber and party (`--strata`) with sign consistency across strata, or label it UNSTRATIFIED. Randomization inference within Congress (`y`, `t`, `block` as numpy arrays):
```python
import numpy as np
def ri_p(y, t, block, B=4999, seed=20260930):        # permute treatment within blocks; two-sided p, difference in means
    rng = np.random.default_rng(seed); idx = np.argsort(block, kind="stable"); stat = lambda tt: y[tt == 1].mean() - y[tt == 0].mean()
    def perm(): tp = np.empty_like(t); tp[idx] = t[np.lexsort((rng.random(len(t)), block))]; return tp
    draws = [stat(perm()) for _ in range(B)]; obs = stat(t); return obs, (1 + np.sum(np.abs(draws) >= abs(obs))) / (B + 1)
```
- **Pass criterion (fix before running):** G and effective N printed beside the row count; CR1 only with roughly 42 or more clusters, otherwise wild bootstrap or CR2, and fewer than 10 clusters labelled descriptive; strata shown or UNSTRATIFIED stated; randomization and sandwich inference agree in conclusion; any large classical-versus-robust gap explained.
- **Failure signature:** clustering on party or Congress; SEs that shrink as more votes by the same members are added; CR1 with few clusters and no small-sample correction; p-values driven by tens of thousands of member-vote rows; one Congress treated as general; a pooled House-and-Senate estimate whose strata disagree in sign (Simpson's paradox).
- **Source:** Abadie et al. (2023); Cameron et al. (2008, 2011); MacKinnon et al. (2023); Arel-Bundock et al. (2026) on power.
### 2.27 Roll calls, co-sponsorship and other cheap signals
- **Tests:** whether position, loyalty or "effectiveness" measures reflect behaviour or the agenda. Recorded votes are the bills the majority chose to schedule, many are procedural or lopsided, and voice votes leave no record; conditioning on "reached the floor" or "voted" is selection on a post-treatment variable (Montgomery et al. 2018). Co-sponsorship, statements and caucus membership are cheap position-taking; co-sponsorship measures "connectedness" only as a validated construct (Fowler 2006).
- **Assumptions of the test itself:** bill-status and vote records are complete for the window; a costly behavioural criterion exists to compare against.
- **Run it:** census the pipeline (introduced, reported, floor, recorded vote) by sponsor party and issue; count votes removed by lopsidedness or procedural filters; tabulate abstention by member and issue; recompute the measure on substantive votes and per Congress. Check cheap signals against votes on the same issue, per party (2.11), and screen for outcome leakage: `python scripts/leakage_audit.py --train tr.csv --test te.csv --group member --time vote_date --available-at feature_date --target voted_yes --features all` (`machine-learning.md`).
- **Pass criterion (fix before running):** the estimand stated as behaviour on the scheduled agenda (or selection modelled); filters disclosed; rankings stable across vote subsets within the pre-set tolerance; no feature taken from the predicted bill or dated after the prediction time.
- **Failure signature:** issue positions inferred from a handful of scheduled votes; rankings that change with the vote subset; co-sponsorship of the predicted bill used as a feature; co-sponsorship edges called influence.
- **Source:** Montgomery et al. (2018); Fowler (2006).
### 2.28 Lobbying disclosures and circular validation
- **Tests:** whether member-level lobbying links are validated independently of how they were built. LD-2 activity reports name the client, the issues and bill numbers, and the chambers and agencies contacted, but no individual member; income and expenses above $5,000 are rounded to the nearest $10,000, with a "less than $5,000" bucket (as of 2026-09-30; law, API terms and filing-error rates in `regulatory.md`; money-data traps in `finance.md`).
- **Assumptions of the test itself:** the construction record of each link (committee jurisdiction, sponsorship, co-sponsorship, text match) is complete.
- **Run it:** for each validation outcome, tabulate whether it was an input to the link; a link built from a member's own bill activity makes "lobbying predicts that member's sponsorship or votes" true by construction. Add a negative control (links assigned from an unrelated committee). Carry dollar amounts as intervals through every total.
- **Pass criterion (fix before running):** validation outcomes disjoint from linking inputs; the negative control null; interval bounds propagated.
- **Failure signature:** validation reuses the linking variables; rounded bands used as exact dollars; documentation that calls member-level lobbying observed.
- **Source:** `regulatory.md` (Lobbying Disclosure Act, status-dated); effect-size benchmarks in 2.1.
### 2.29 Pointers: district plans, research ethics and data-use law
- **District plans:** district codes are not stable identifiers. With mid-decade redraws for 2026 in several states, and primaries and generals that can run on different maps, pin every constituency covariate to the plan in force on each election date (as of 2026-09-30; state status, crosswalks, ZIP-to-district allocation, MAUP and census noise in `geospatial.md`; `python scripts/spatial_audit.py --mode crosswalk --xwalk zip_cd.csv --from zip --to cd --weight res_ratio`).
- **Ethics and data use:** before using contributor records, platform text or staffer data, check `regulatory.md`: the Common Rule (by analogy outside federally supported research), the APSA human-subjects principles (including research's impact on political processes), the AoIR guidelines for internet research, platform terms, and the FEC restriction on the sale or use of contributor information. Statuses are dated there.

## 3. Checklist

- **SOC-01** `CAUSAL` Write the estimand and name the identifying design for every "effect of money, lobbying or access" number. Fail if a response curve, flip model or frontier prices dollars with no named design; relabel it "allocation heuristic under an assumed response curve". (§2 routing table, 2.1)
- **SOC-02** `CAUSAL` Keep who-wins effects apart from dollar effects. Fail if a close-election RD estimate becomes a per-dollar return. (2.2)
- **SOC-03** `CAUSAL` For RD, report robust bias-corrected CIs, a density test, covariate-continuity tests (lagged vote share, incumbency, pre-election receipts) and half-to-double bandwidth sensitivity. Fail on a density or covariate jump, a sign change across bandwidths, or conventional-only CIs. (2.2)
- **SOC-04** `CAUSAL` For IV, report the effective F, AR or tF inference, the 2SLS/OLS ratio and a pre-period placebo. Fail on a weak first stage with conventional CIs or an unexplained ratio far above 1. (2.3)
- **SOC-05** `CAUSAL` Set every cross-sectional money coefficient beside a within-unit estimate, and every border estimate beside leave-one-segment-out and placebo borders. Fail if a pooled coefficient far above the within-unit one is read as causal, or one segment carries a border effect. (2.4)
- **SOC-06** `CAUSAL` Benchmark implied persuasion and access effects against experimental evidence, and check that experiments were analysed as randomized. Fail on large per-dollar persuasion without new causal evidence, or access and votes treated as one outcome. (2.1, 2.5)
- **SOC-07** `CAUSAL` For staggered adoption, run two heterogeneity-robust estimators and a Bacon decomposition beside TWFE. Fail if TWFE and robust estimates differ in sign or by more than 50%. (2.6)
- **SOC-08** `CAUSAL` Replace "pre-trend p > .05 = pass" with relative-magnitude sensitivity bounds. Fail if the result breaks down at a bound of 1 or less; mark `UNVERIFIED-HERE` if the bound cannot be computed. (2.6)
- **SOC-09** `CAUSAL` For synthetic control, report pre-period RMSPE, donor weights, placebos in space and time, and leave-one-donor-out. Fail if the treated RMSPE ratio is ordinary among placebos or leave-one-out flips the sign. (2.7)
- **SOC-10** `CAUSAL` Run `scripts/confounding_sensitivity.py` against benchmarks such as party, ideology and seniority, with `--rv-min` set before running. Fail if RV_q < `--rv-min`, the bias-adjusted estimate flips at kd ≤ `--kd-kill`, or Oster δ < `--delta-min`. (2.8)
- **SOC-11** `CAUSAL` Date every covariate and sample filter against treatment, and report regression weight shares by stratum. Fail on any post-treatment control, an outcome-selected sample, or an unreported stratum carrying most of the weight. (2.9)
- **SOC-12** `PRESENTATION` Tag every finding by claim type and scan for causal verbs. Fail on causal wording without a named estimand and design. (2.10)
- **SOC-13** `MEASUREMENT` Test each latent score's discriminant validity against activity volume, by party and chamber. Fail if the score tracks volume at least as closely as its behavioural criterion. (2.11)
- **SOC-14** `MEASUREMENT` Move each composite weight by ±25% and report rank stability. Fail if Kendall's τ or top-k overlap falls below the pre-set floor. (2.11)
- **SOC-15** `MEASUREMENT` Keep stance separate from sentiment, and report classifier metrics per class and per subgroup. Fail if sentiment is used as a position on a target, or only overall accuracy is shown for imbalanced classes. (2.12)
- **SOC-16** `MEASUREMENT` Report the gold-set design: size, sampling probabilities, the number of independent coders and, with two or more coders, Krippendorff's alpha with a bootstrap CI. Single-coder gold is a stated limitation, not an automatic fail. Fail on convenience sampling or LLM-versus-LLM "validation". (2.14, 2.15)
- **SOC-17** `MEASUREMENT` Report LLM label error by party, gender and chamber. Fail on differential error left uncorrected. (2.13)
- **SOC-18** `MEASUREMENT` Propagate label error into every downstream estimate with DSL or PPI. Fail if regressions, flip models or frontiers use raw predicted labels with naive SEs. (2.14)
- **SOC-19** `COMPUTATIONAL` Log model ID and snapshot, prompt hash, decoding settings and seed for every label; re-annotate a frozen probe panel; test paraphrases. Fail on drift or paraphrase flips above the pre-set rate, or when replay is impossible. (2.13)
- **SOC-20** `MEASUREMENT` Correct or bound attenuation, with reliability estimated per group. Fail if noisy scores are compared across groups of unequal reliability. (2.16)
- **SOC-21** `MEASUREMENT` For ideal points, fix sign and scale by anchors, check dimensionality within each party, and state the bridge across Congresses. Fail if issue positions are read off dimension 1 unchecked. (2.17)
- **SOC-22** `MEASUREMENT` Keep individual-level language out of aggregate data; check EI estimates against the bounds and MRP frames against the current plan. Fail on out-of-bounds estimates or old-plan frames. (2.18)
- **SOC-23** `CAUSAL` Treat similarity between tied actors as confounded; require time ordering, null placebos and leads, or exogenous shocks before any influence claim. Fail on influence claims from static ties. (2.19)
- **SOC-24** `MEASUREMENT` Treat co-sponsorship, co-tenure and co-appearance edges as shared context, not social ties, until validated. Fail if they are called influence channels. (2.19, 2.27)
- **SOC-25** `DATA` Perturb the network (5-20% of edges; simulated merges and splits) and report top-k stability. Fail if the top-10 overlap falls below the pre-set floor. (2.20)
- **SOC-26** `STATISTICAL` Use DSP or Freedman-Lane MRQAP, or dyadic-robust SEs, for dyads; show MCMC diagnostics and simulation goodness of fit for ERGMs. Fail on plain OLS SEs for dyads or degenerate ERGM simulations. (2.21)
- **SOC-27** `FUNCTIONAL-FORM` For Katz-Bonacich, verify decay < 1/λ_max, scan the admissible range and report the correlation with degree. Fail if the ranking hinges on an arbitrary decay or is essentially degree. (2.22)
- **SOC-28** `COMPUTATIONAL` Label IC/LT parameters as assumed unless learned from timed cascades; sweep them with `scripts/global_sensitivity.py`; report MCSE and seed-ranking stability under ±20% p. Fail if simulations are presented as estimates. (2.23)
- **SOC-29** `STATISTICAL` Show a specification curve for each headline regression. Fail if fewer than the pre-set share of defensible specifications share the headline sign. (2.24)
- **SOC-30** `STATISTICAL` Count every test per family from the analysis log, report BH q-values, and disclose deviations from any plan. Fail on unadjusted per-topic winners or undisclosed deviations. (2.24)
- **SOC-31** `STATISTICAL` For every trend claim, show sign stability across windows and specifications and a Type-S estimate at a plausible effect size. Fail if Type S exceeds about 10%, or the model wins, and keeps its sign, in fewer than `--min-window-share` of windows (default 0.75). (2.25)
- **SOC-32** `STATISTICAL` Print `summary(lm())` with a labelled cluster-robust block via `scripts/regression_report.R` (member; member × roll call; wild bootstrap or CR2 for few clusters). Fail on clustering by party or Congress. (2.26)
- **SOC-33** `STATISTICAL` State independent units and effective N beside the row count, with power for plausible effects. Fail if inference leans on member-vote rows. (2.26)
- **SOC-34** `PRESENTATION` Show strata (chamber, party) or label the estimate UNSTRATIFIED. Fail on a pooled estimate with neither. (2.26)
- **SOC-35** `DATA` Census the path from introduction to recorded vote, disclose vote filters, and screen cheap signals for outcome leakage. Fail if a position claim rests on an agenda-selected subset without saying so, or a feature comes from the predicted bill. (2.27)
- **SOC-36** `DATA` Treat member-level lobbying links as inferences, keep validation outcomes disjoint from linking inputs, and carry LD-2 bands as intervals. Fail on circular validation or exact-dollar use of rounded amounts. (2.28)
- **SOC-37** `DATA` Pin district geography to the plan in force on each election date (`geospatial.md`). Fail if district codes serve as stable IDs across plans. (2.29)
- **SOC-38** `LEGAL` Check every person-level source against `regulatory.md` before use. Fail if a use is unchecked. (2.29)

## 4. Pitfalls and anti-patterns

- "Controlled for confounders" read as proof of exchangeability; adjusting for a mediator or collider opens new bias (2.9).
- A pre-trend p > .05 read as parallel trends, or a script printing "SUCCESS" for it (2.6); a close-election RD converted into dollars per vote (2.2).
- A covariate dropped as "not a confounder" because it was not significant; post-hoc power; a continuous score cut into flip / no-flip before analysis; members selected on an extreme change (a giving spike, a vote switch) with the next period's reversion read as an effect (regression to the mean); winners-only samples (survivorship).
- Agreement (human-human, human-LLM, LLM-LLM) treated as validity; LLM "silicon samples" treated as annotations or survey data.
- Feature importance or SHAP values from a flip model read as causal levers (`machine-learning.md`); clustering on party or Congress; chambers pooled without strata; IC probabilities set from tie strength; LD-2 assumed to name members.
- Literature weighted by venue rather than design: credible natural experiments, RD, and IV with strong first stages outrank large cross-sections, and one study, one group or one Congress is weak evidence.
- Archived or wrong packages recommended (as of 2026-09-30): CRAN `rdd`, `fwildclusterboot`, `summclust`, `eiCompare` and `autoMrP` are archived; `dsl`, `augsynth` and R `synthdid` are GitHub-only; PyPI `pysynth` is an unrelated dataset-synthesis package, `synth_runner` is a Stata package, and PyPI `pystata` is a placeholder.

**Public CSS agent skills (read, not installed; as of 2026-09-30).** Borrow structure: route by estimand to specialist checks with a findings catalogue and an output contract (pitcany/statistical-agent-skills), and put a design card and a sign-off gate before analysis (lancegui/causal-powers). scdenney/open-science-skills has the best LLM-annotation content (DSL, learned proxies, Krippendorff's alpha) but asserts no licence, so take ideas only. Avoid prompt hooks that force "mandatory" skill activation, daily version checks that call home, `curl | bash` installers, settings that pre-allow `Bash(*)`, `Edit`, `Write` and `WebFetch` with an empty deny list, scripts that send project material to a second model provider, TWFE event studies labelled Sun-Abraham, and the wrong package names above. This skill ships no hooks and makes no network calls outside `scripts/cite_check.py`.

## 5. References

- Abadie, A. (2021). Using synthetic controls: feasibility, data requirements, and methodological aspects. *Journal of Economic Literature* 59(2), 391-425. https://doi.org/10.1257/jel.20191450
- Abadie, A., Athey, S., Imbens, G. W., & Wooldridge, J. M. (2023). When should you adjust standard errors for clustering? *Quarterly Journal of Economics* 138(1), 1-35. https://doi.org/10.1093/qje/qjac038
- Abadie, A., Diamond, A., & Hainmueller, J. (2010). Synthetic control methods for comparative case studies: estimating the effect of California's tobacco control program. *Journal of the American Statistical Association* 105(490), 493-505. https://doi.org/10.1198/jasa.2009.ap08746
- Adcock, R., & Collier, D. (2001). Measurement validity: a shared standard for qualitative and quantitative research. *American Political Science Review* 95(3), 529-546. https://doi.org/10.1017/s0003055401003100
- Aldrich, J. H., Montgomery, J. M., & Sparks, D. B. (2014). Polarization and ideology: partisan sources of low dimensionality in scaled roll call analyses. *Political Analysis* 22(4), 435-456. https://doi.org/10.1093/pan/mpt048
- Andrews, I., Stock, J. H., & Sun, L. (2019). Weak instruments in instrumental variables regression: theory and practice. *Annual Review of Economics* 11, 727-753. https://doi.org/10.1146/annurev-economics-080218-025643
- Angelopoulos, A. N., Bates, S., Fannjiang, C., Jordan, M. I., & Zrnic, T. (2023). Prediction-powered inference. *Science* 382(6671), 669-674. https://doi.org/10.1126/science.adi6000
- Aral, S., Muchnik, L., & Sundararajan, A. (2009). Distinguishing influence-based contagion from homophily-driven diffusion in dynamic networks. *PNAS* 106(51), 21544-21549. https://doi.org/10.1073/pnas.0908800106
- Arel-Bundock, V., Briggs, R. C., Doucouliagos, H., Mendoza Aviña, M., & Stanley, T. D. (2026). Quantitative political science research is greatly underpowered. *Journal of Politics* 88(1), 36-46. https://doi.org/10.1086/734279
- Argyle, L. P., Busby, E. C., Fulda, N., Gubler, J. R., Rytting, C., & Wingate, D. (2023). Out of one, many: using language models to simulate human samples. *Political Analysis* 31(3), 337-351. https://doi.org/10.1017/pan.2023.2
- Aronow, P. M., & Samii, C. (2016). Does regression produce representative estimates of causal effects? *American Journal of Political Science* 60(1), 250-267. https://doi.org/10.1111/ajps.12185 (correction notice)
- Aronow, P. M., Samii, C., & Assenova, V. A. (2015). Cluster-robust variance estimation for dyadic data. *Political Analysis* 23(4), 564-577. https://doi.org/10.1093/pan/mpv018
- Ballester, C., Calvó-Armengol, A., & Zenou, Y. (2006). Who's who in networks. Wanted: the key player. *Econometrica* 74(5), 1403-1417. https://doi.org/10.1111/j.1468-0262.2006.00709.x
- Baumann, J., Röttger, P., Urman, A., Wendsjö, A., Plaza-del-Arco, F. M., Gruber, J. B., & Hovy, D. (2025). Large language model hacking: quantifying the hidden risks of using LLMs for text annotation. *arXiv preprint*. https://doi.org/10.48550/arXiv.2509.08825
- Benjamini, Y., & Hochberg, Y. (1995). Controlling the false discovery rate: a practical and powerful approach to multiple testing. *Journal of the Royal Statistical Society Series B* 57(1), 289-300. https://doi.org/10.1111/j.2517-6161.1995.tb02031.x
- Bestvater, S. E., & Monroe, B. L. (2023). Sentiment is not stance: target-aware opinion classification for political text analysis. *Political Analysis* 31(2), 235-256. https://doi.org/10.1017/pan.2022.10
- Bonacich, P. (1987). Power and centrality: a family of measures. *American Journal of Sociology* 92(5), 1170-1182. https://doi.org/10.1086/228631
- Borgatti, S. P., Carley, K. M., & Krackhardt, D. (2006). On the robustness of centrality measures under conditions of imperfect data. *Social Networks* 28(2), 124-136. https://doi.org/10.1016/j.socnet.2005.05.001
- Breznau, N., Rinke, E. M., Wuttke, A., et al. (2022). Observing many researchers using the same data and hypothesis reveals a hidden universe of uncertainty. *PNAS* 119(44), e2203150119. https://doi.org/10.1073/pnas.2203150119 (correction notice)
- Brodeur, A., Mikola, D., Cook, N., et al. (2026). Reproducibility and robustness of economics and political science research. *Nature* 652(8108), 151-156. https://doi.org/10.1038/s41586-026-10251-x (correction notice)
- Callaway, B., & Sant'Anna, P. H. C. (2021). Difference-in-differences with multiple time periods. *Journal of Econometrics* 225(2), 200-230. https://doi.org/10.1016/j.jeconom.2020.12.001
- Calonico, S., Cattaneo, M. D., & Titiunik, R. (2014). Robust nonparametric confidence intervals for regression-discontinuity designs. *Econometrica* 82(6), 2295-2326. https://doi.org/10.3982/ecta11757
- Cameron, A. C., Gelbach, J. B., & Miller, D. L. (2008). Bootstrap-based improvements for inference with clustered errors. *Review of Economics and Statistics* 90(3), 414-427. https://doi.org/10.1162/rest.90.3.414
- Cameron, A. C., Gelbach, J. B., & Miller, D. L. (2011). Robust inference with multiway clustering. *Journal of Business & Economic Statistics* 29(2), 238-249. https://doi.org/10.1198/jbes.2010.07136
- Carroll, R. J., Ruppert, D., Stefanski, L. A., & Crainiceanu, C. M. (2006). *Measurement Error in Nonlinear Models* (2nd ed.). Chapman and Hall/CRC. https://doi.org/10.1201/9781420010138
- Cattaneo, M. D., Jansson, M., & Ma, X. (2020). Simple local polynomial density estimators. *Journal of the American Statistical Association* 115(531), 1449-1455. https://doi.org/10.1080/01621459.2019.1635480
- Caughey, D., & Sekhon, J. S. (2011). Elections and the regression discontinuity design: lessons from close U.S. House races, 1942-2008. *Political Analysis* 19(4), 385-408. https://doi.org/10.1093/pan/mpr032
- Chae, Y., & Davidson, T. (2026). Large language models for text classification: from zero-shot learning to instruction-tuning. *Sociological Methods & Research* 55(2), 501-567. https://doi.org/10.1177/00491241251325243
- de Chaisemartin, C., & D'Haultfœuille, X. (2020). Two-way fixed effects estimators with heterogeneous treatment effects. *American Economic Review* 110(9), 2964-2996. https://doi.org/10.1257/aer.20181169
- Chiu, A., Lan, X., Liu, Z., & Xu, Y. (2026). Causal panel analysis under parallel trends: lessons from a large reanalysis study. *American Political Science Review* 120(1), 245-266. https://doi.org/10.1017/s0003055425000243
- Cinelli, C., & Hazlett, C. (2020). Making sense of sensitivity: extending omitted variable bias. *Journal of the Royal Statistical Society Series B* 82(1), 39-67. https://doi.org/10.1111/rssb.12348
- Clinton, J., Jackman, S., & Rivers, D. (2004). The statistical analysis of roll call data. *American Political Science Review* 98(2), 355-370. https://doi.org/10.1017/s0003055404001194
- Cranmer, S. J., & Desmarais, B. A. (2011). Inferential network analysis with exponential random graph models. *Political Analysis* 19(1), 66-86. https://doi.org/10.1093/pan/mpq037
- de la Cuesta, B., & Imai, K. (2016). Misunderstandings about the regression discontinuity design in the study of close elections. *Annual Review of Political Science* 19, 375-396. https://doi.org/10.1146/annurev-polisci-032015-010115
- Dekker, D., Krackhardt, D., & Snijders, T. A. B. (2007). Sensitivity of MRQAP tests to collinearity and autocorrelation conditions. *Psychometrika* 72(4), 563-581. https://doi.org/10.1007/s11336-007-9016-1
- Egami, N., Hinck, M., Stewart, B. M., & Wei, H. (2023). Using imperfect surrogates for downstream inference: design-based supervised learning for social science applications of large language models. *NeurIPS 36*, 68589-68601. https://doi.org/10.52202/075280-3000 (arXiv:2306.04746)
- Eggers, A. C., Fowler, A., Hainmueller, J., Hall, A. B., & Snyder, J. M. (2015). On the validity of the regression discontinuity design for estimating electoral effects: new evidence from over 40,000 close races. *American Journal of Political Science* 59(1), 259-274. https://doi.org/10.1111/ajps.12127
- Feuerriegel, S., Barrie, C., Crockett, M. J., et al. (2026). A reporting checklist for large language models in behavioural science. *Nature Human Behaviour* 10(7), 1182-1186. https://doi.org/10.1038/s41562-026-02492-7
- Fong, C., & Tyler, M. (2021). Machine learning predictions as regression covariates. *Political Analysis* 29(4), 467-484. https://doi.org/10.1017/pan.2020.38
- Fowler, A., Garro, H., & Spenkuch, J. L. (2020). Quid pro quo? Corporate returns to campaign contributions. *Journal of Politics* 82(3), 844-858. https://doi.org/10.1086/707307
- Fowler, J. H. (2006). Connecting the Congress: a study of cosponsorship networks. *Political Analysis* 14(4), 456-487. https://doi.org/10.1093/pan/mpl002
- Gelman, A., & Carlin, J. (2014). Beyond power calculations: assessing Type S (sign) and Type M (magnitude) errors. *Perspectives on Psychological Science* 9(6), 641-651. https://doi.org/10.1177/1745691614551642
- Gelman, A., & Loken, E. (2014). The statistical crisis in science. *American Scientist* 102(6), 460. https://doi.org/10.1511/2014.111.460
- Gerber, A. (1998). Estimating the effect of campaign spending on Senate election outcomes using instrumental variables. *American Political Science Review* 92(2), 401-411. https://doi.org/10.2307/2585672
- Gilardi, F., Alizadeh, M., & Kubli, M. (2023). ChatGPT outperforms crowd workers for text-annotation tasks. *PNAS* 120(30), e2305016120. https://doi.org/10.1073/pnas.2305016120
- Gomez-Rodriguez, M., Leskovec, J., & Krause, A. (2012). Inferring networks of diffusion and influence. *ACM Transactions on Knowledge Discovery from Data* 5(4), 1-37. https://doi.org/10.1145/2086737.2086741
- Goodman-Bacon, A. (2021). Difference-in-differences with variation in treatment timing. *Journal of Econometrics* 225(2), 254-277. https://doi.org/10.1016/j.jeconom.2021.03.014
- Grimmer, J., & Stewart, B. M. (2013). Text as data: the promise and pitfalls of automatic content analysis methods for political texts. *Political Analysis* 21(3), 267-297. https://doi.org/10.1093/pan/mps028
- Hainmueller, J., Mummolo, J., & Xu, Y. (2019). How much should we trust estimates from multiplicative interaction models? Simple tools to improve empirical practice. *Political Analysis* 27(2), 163-192. https://doi.org/10.1017/pan.2018.46
- Halterman, A., & Keith, K. A. (2026). Codebook LLMs: evaluating LLMs as measurement tools for political science concepts. *Political Analysis* 34(2), 188-204. https://doi.org/10.1017/pan.2025.10017
- Hayes, A. F., & Krippendorff, K. (2007). Answering the call for a standard reliability measure for coding data. *Communication Methods and Measures* 1(1), 77-89. https://doi.org/10.1080/19312450709336664
- He, X., & Kempe, D. (2016). Robust influence maximization. *Proceedings of KDD 2016*, 885-894. https://doi.org/10.1145/2939672.2939760
- Hopkins, D. J., & King, G. (2010). A method of automated nonparametric content analysis for social science. *American Journal of Political Science* 54(1), 229-247. https://doi.org/10.1111/j.1540-5907.2009.00428.x
- Hunter, D. R., Goodreau, S. M., & Handcock, M. S. (2008). Goodness of fit of social network models. *Journal of the American Statistical Association* 103(481), 248-258. https://doi.org/10.1198/016214507000000446
- Jacobson, G. C. (1978). The effects of campaign spending in congressional elections. *American Political Science Review* 72(2), 469-491. https://doi.org/10.2307/1954105
- Kalla, J. L., & Broockman, D. E. (2016). Campaign contributions facilitate access to congressional officials: a randomized field experiment. *American Journal of Political Science* 60(3), 545-558. https://doi.org/10.1111/ajps.12180
- Kalla, J. L., & Broockman, D. E. (2018). The minimal persuasive effects of campaign contact in general elections: evidence from 49 field experiments. *American Political Science Review* 112(1), 148-166. https://doi.org/10.1017/s0003055417000363
- Kang, K. (2016). Policy influence and private returns from lobbying in the energy sector. *Review of Economic Studies* 83(1), 269-305. https://doi.org/10.1093/restud/rdv029
- Keele, L. J., & Titiunik, R. (2015). Geographic boundaries as regression discontinuities. *Political Analysis* 23(1), 127-155. https://doi.org/10.1093/pan/mpu014
- Kempe, D., Kleinberg, J., & Tardos, É. (2003). Maximizing the spread of influence through a social network. *Proceedings of KDD 2003*, 137-146. https://doi.org/10.1145/956750.956769
- King, G. (1997). *A Solution to the Ecological Inference Problem: Reconstructing Individual Behavior from Aggregate Data*. Princeton University Press. https://doi.org/10.1515/9781400849208 (De Gruyter digital edition)
- King, G., & Roberts, M. E. (2015). How robust standard errors expose methodological problems they do not fix, and what to do about it. *Political Analysis* 23(2), 159-179. https://doi.org/10.1093/pan/mpu015
- Kossinets, G. (2006). Effects of missing data in social networks. *Social Networks* 28(3), 247-268. https://doi.org/10.1016/j.socnet.2005.07.002
- Krackhardt, D. (1988). Predicting with networks: nonparametric multiple regression analysis of dyadic data. *Social Networks* 10(4), 359-381. https://doi.org/10.1016/0378-8733(88)90004-4
- Lal, A., Lockhart, M., Xu, Y., & Zu, Z. (2024). How much should we trust instrumental variable estimates in political science? Practical advice based on 67 replicated studies. *Political Analysis* 32(4), 521-540. https://doi.org/10.1017/pan.2024.2
- Lax, J. R., & Phillips, J. H. (2009). How should we estimate public opinion in the states? *American Journal of Political Science* 53(1), 107-121. https://doi.org/10.1111/j.1540-5907.2008.00360.x
- Lee, D. S. (2008). Randomized experiments from non-random selection in U.S. House elections. *Journal of Econometrics* 142(2), 675-697. https://doi.org/10.1016/j.jeconom.2007.05.004
- Lee, D. S., McCrary, J., Moreira, M. J., & Porter, J. (2022). Valid t-ratio inference for IV. *American Economic Review* 112(10), 3260-3290. https://doi.org/10.1257/aer.20211063
- Levitt, S. D. (1994). Using repeat challengers to estimate the effect of campaign spending on election outcomes in the U.S. House. *Journal of Political Economy* 102(4), 777-798. https://doi.org/10.1086/261954
- MacKinnon, J. G., Nielsen, M. Ø., & Webb, M. D. (2023). Cluster-robust inference: a guide to empirical practice. *Journal of Econometrics* 232(2), 272-299. https://doi.org/10.1016/j.jeconom.2022.04.001
- McShane, B. B., Gal, D., Gelman, A., Robert, C., & Tackett, J. L. (2019). Abandon statistical significance. *The American Statistician* 73(sup1), 235-245. https://doi.org/10.1080/00031305.2018.1527253
- Montgomery, J. M., & Nyhan, B. (2017). The effects of congressional staff networks in the US House of Representatives. *Journal of Politics* 79(3), 745-761. https://doi.org/10.1086/690301
- Montgomery, J. M., Nyhan, B., & Torres, M. (2018). How conditioning on posttreatment variables can ruin your experiment and what to do about it. *American Journal of Political Science* 62(3), 760-775. https://doi.org/10.1111/ajps.12357
- Mummolo, J., & Peterson, E. (2018). Improving the interpretation of fixed effects regression results. *Political Science Research and Methods* 6(4), 829-835. https://doi.org/10.1017/psrm.2017.44
- Netrapalli, P., & Sanghavi, S. (2012). Learning the graph of epidemic cascades. *Proceedings of SIGMETRICS/PERFORMANCE 2012*, 211-222. https://doi.org/10.1145/2254756.2254783
- Ofosu, G. K., & Posner, D. N. (2023). Pre-analysis plans: an early stocktaking. *Perspectives on Politics* 21(1), 174-190. https://doi.org/10.1017/s1537592721000931
- Oster, E. (2019). Unobservable selection and coefficient stability: theory and evidence. *Journal of Business & Economic Statistics* 37(2), 187-204. https://doi.org/10.1080/07350015.2016.1227711
- Palmer, A., Smith, N. A., & Spirling, A. (2024). Using proprietary language models in academic research requires explicit justification. *Nature Computational Science* 4(1), 2-3. https://doi.org/10.1038/s43588-023-00585-1
- Poole, K. T., & Rosenthal, H. (1985). A spatial model for legislative roll call analysis. *American Journal of Political Science* 29(2), 357-384. https://doi.org/10.2307/2111172
- Powell, E. N., & Grimmer, J. (2016). Money in exile: campaign contributions and committee access. *Journal of Politics* 78(4), 974-988. https://doi.org/10.1086/686615
- Rambachan, A., & Roth, J. (2023). A more credible approach to parallel trends. *Review of Economic Studies* 90(5), 2555-2591. https://doi.org/10.1093/restud/rdad018
- Robinson, W. S. (1950). Ecological correlations and the behavior of individuals. *American Sociological Review* 15(3), 351-357. https://doi.org/10.2307/2087176
- Rosenbaum, P. R. (2002). *Observational Studies* (2nd ed.). Springer. https://doi.org/10.1007/978-1-4757-3692-2
- Roth, J. (2022). Pretest with caution: event-study estimates after testing for parallel trends. *American Economic Review: Insights* 4(3), 305-322. https://doi.org/10.1257/aeri.20210236
- Saito, K., Nakano, R., & Kimura, M. (2008). Prediction of information diffusion probabilities for independent cascade model. *KES 2008, LNCS 5179*, 67-75. https://doi.org/10.1007/978-3-540-85567-5_9
- Shalizi, C. R., & Thomas, A. C. (2011). Homophily and contagion are generically confounded in observational social network studies. *Sociological Methods & Research* 40(2), 211-239. https://doi.org/10.1177/0049124111404820
- Sides, J., Vavreck, L., & Warshaw, C. (2022). The effect of television advertising in United States elections. *American Political Science Review* 116(2), 702-718. https://doi.org/10.1017/s000305542100112x
- Simonsohn, U., Simmons, J. P., & Nelson, L. D. (2020). Specification curve analysis. *Nature Human Behaviour* 4(11), 1208-1214. https://doi.org/10.1038/s41562-020-0912-z (correction notice)
- Song, H., Tolochko, P., Eberl, J.-M., et al. (2020). In validations we trust? The impact of imperfect human annotations as a gold standard on the quality of validation of automated content analysis. *Political Communication* 37(4), 550-572. https://doi.org/10.1080/10584609.2020.1723752
- Spearman, C. (1904). The proof and measurement of association between two things. *American Journal of Psychology* 15(1), 72-101. https://doi.org/10.2307/1412159
- Spenkuch, J. L., & Toniatti, D. (2018). Political advertising and election results. *Quarterly Journal of Economics* 133(4), 1981-2036. https://doi.org/10.1093/qje/qjy010
- Sun, L., & Abraham, S. (2021). Estimating dynamic treatment effects in event studies with heterogeneous treatment effects. *Journal of Econometrics* 225(2), 175-199. https://doi.org/10.1016/j.jeconom.2020.09.006
- van Atteveldt, W., van der Velden, M. A. C. G., & Boukes, M. (2021). The validity of sentiment analysis: comparing manual annotation, crowd-coding, dictionary approaches, and machine learning algorithms. *Communication Methods and Measures* 15(2), 121-140. https://doi.org/10.1080/19312458.2020.1869198
- VanderWeele, T. J., & Ding, P. (2017). Sensitivity analysis in observational research: introducing the E-value. *Annals of Internal Medicine* 167(4), 268-274. https://doi.org/10.7326/m16-2607
- Wang, D. J., Shi, X., McFarland, D. A., & Leskovec, J. (2012). Measurement error in network data: a re-classification. *Social Networks* 34(4), 396-409. https://doi.org/10.1016/j.socnet.2012.01.003
- Wasserstein, R. L., & Lazar, N. A. (2016). The ASA statement on p-values: context, process, and purpose. *The American Statistician* 70(2), 129-133. https://doi.org/10.1080/00031305.2016.1154108

Print years are used; several items appeared online a year earlier. Not cited because unverified: Krippendorff's textbook cutoffs (flagged in 2.15), the discussion-paper version of Brodeur et al. (2026), the Barrie-Palmer-Spirling LLM-replication working paper, and the 2024 Egami et al. LLM-annotation working paper. **Adapted from** (paraphrased; MIT; no K-Dense code copied): K-Dense `hypothesis-generation/references/causal_inference_and_claims.md` and the claim-annotation idea behind `hypothesis-generation/scripts/lint_causal_claims.py` (re-expressed as the one-line scan in 2.10); `scientific-critical-thinking/references/statistical_pitfalls.md`, `scientific-critical-thinking/references/common_biases.md` and `scientific-critical-thinking/references/evidence_hierarchy.md`; `scholar-evaluation/SKILL.md`, `scholar-evaluation/references/evaluation_framework.md` and `scholar-evaluation/references/responsible_assessment.md` (construct first, agreement is not validity, weight sensitivity); `experimental-design/SKILL.md` (the analysis mirrors blocks and clusters).
