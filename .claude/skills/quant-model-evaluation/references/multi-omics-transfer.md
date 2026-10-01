# Multi-omics methods transferred — quant-model-evaluation reference

> **Load when:** a model or report runs many simultaneous tests (per member, topic, sector or district); ranks many noisy units; claims a category is over-represented among flagged units; pools data across cycles, collector versions or sources; analyzes budget or spending shares; correlates two relationship matrices; reports one optimal allocation; joins entities across sources; or fits a complex model on few labels. **Not for:** multiplicity basics and power (`core-statistics.md`); network inference and QAP in depth (`social-science.md`); classifier evaluation (`machine-learning.md`); pipeline fallbacks and freshness (`automation.md`); profile-likelihood mechanics (`engineering-simulation.md` §2.8).
> Facts marked (as of DATE) are time-sensitive; re-verify before relying on them.

**Why this module exists.** Multi-omics (genomics, transcriptomics, microbiome and metabolic data) has no direct finance or computational-social-science application, and nothing here is a biological claim. The field did build unusually careful tools for problems that political-finance and CSS models share: thousands of simultaneous tests, many small noisy units, batch artifacts from changing instruments, data that sum to a fixed total, silent identifier mismatches, and complex models fitted on few labels. This module carries those statistical tools across and states the translation for each.

## 1. Assumption map

| Assumption (class) | Where it usually hides | What breaks if it is false | Tests |
|---|---|---|---|
| Reported hits survived multiplicity (STATISTICAL) | loops over topics, members, sectors or districts that report raw p-values | false discoveries presented as findings | 2.1 |
| A ranking of many units is not ranked noise (STATISTICAL) | leaderboards of rates, ROI or deviations per member or district | the extremes are the smallest samples | 2.2 |
| Enrichment uses the right universe (STATISTICAL) | "category X is over-represented among flagged units", tested against all units | inflated significance | 2.3 |
| Batch boundaries do not coincide with labels (DATA) | cycle, collector version, vendor, annotator or model version, vintage | batch artifacts read as effects | 2.4 |
| Shares are analyzed as compositions (FUNCTIONAL-FORM) | budget shares, spending mix, portfolio weights, multi-party vote shares | spurious negative correlations; misread "increases" | 2.5 |
| Matrix-level tests respect dyadic dependence (STATISTICAL) | ordinary p-values on the n(n−1)/2 cells of two relationship matrices | overstated significance | 2.6 |
| Fitted constants are identified (STATISTICAL) | curve parameters fitted on few outcomes | arbitrary optimizer choices reported as estimates | 2.7 |
| The optimum is unique, or decisions survive near-optimal alternatives (DECISION) | one allocation reported as "the" answer | false precision about which target gets what | 2.8 |
| Joins and identifier mappings do not drop units silently (DATA) | name or ID mismatches; vocabulary drift across versions | missing data read as true zeros | 2.9 |
| A complex model beats simple baselines at this label count (STATISTICAL) | embeddings or large models fitted on hundreds of labels | complexity without gain | 2.10 |
| Multi-view integration is validated (MEASUREMENT) | text, vote, money and network views concatenated ad hoc | structure driven by one view's scale | 2.11 |

## 2. Tests

### 2.1 False discovery rate, controlled per family
- **Tests:** whether reported hits survive the number of tests actually run.
- **Assumptions of the test itself:** families are defined by question before any result is seen. Benjamini-Hochberg (BH) needs independence or positive dependence among tests; Benjamini-Yekutieli (BY) holds under any dependence, at a cost in power.
- **Translation:** genomics tests every gene; a legislative model tests every topic, member or sector. A family is one question (for example, "which of 12 topics shows a spending effect"). Running several families multiplies the tests even though each family is corrected on its own.
- **Run it:**
  ```python
  import pandas as pd
  from statsmodels.stats.multitest import multipletests
  df = pd.read_csv("tests.csv")                     # one row per test: family, unit, p
  df["q"] = df.groupby("family")["p"].transform(lambda p: multipletests(p, method="fdr_bh")[1])
  print(df.groupby("family").agg(tests=("p", "size"), hits=("q", lambda q: int((q < 0.05).sum()))))
  ```
  Use `method="fdr_by"` when tests are strongly and arbitrarily dependent. In R: `p.adjust(p, "BH")`. Storey's q-values gain power when many nulls are false (they estimate the share of true nulls).
- **Pass criterion (fix before running):** families, alpha and the correction written down before looking; every report states the number of tests per family.
- **Failure signature:** "12 significant sectors" out of 200 unadjusted tests; families drawn after the results; the correction applied only to the reported subset; one family chosen from several.
- **Source:** Benjamini & Hochberg (1995); Benjamini & Yekutieli (2001); Storey (2002); Storey & Tibshirani (2003); adapted from K-Dense `pathway-enrichment` (FDR is per library).

### 2.2 Empirical-Bayes shrinkage for ranking many units
- **Tests:** whether a ranking of many units reflects signal or sample size.
- **Assumptions of the test itself:** units are exchangeable a priori within the pooling group; standard errors are roughly right; the pooling group does not contain the effect of interest (never shrink treated units toward untreated ones).
- **Translation:** DESeq2 shrinks the noisy fold changes of low-count genes before ranking them. A per-member ROI, flip rate or deviation built from a few votes or a few dollars needs the same treatment, because raw extremes come from the smallest samples.
- **Run it:** rank on shrunk estimates; test on unshrunk estimates with FDR (2.1); report both rankings, their overlap, and each unit's sample size.
  ```python
  import numpy as np
  def eb_shrink(est, se):
      """Normal-normal empirical Bayes (moment estimate): pull each unit toward the pooled mean
      in proportion to its noise. Returns shrunk estimates and factors b (1 = fully pooled)."""
      est, se = np.asarray(est, float), np.asarray(se, float)
      tau2 = max(0.0, np.var(est, ddof=1) - np.mean(se**2))      # between-unit variance
      w = 1 / (se**2 + tau2)
      mu = np.sum(w * est) / np.sum(w)
      b = se**2 / (se**2 + tau2)
      return mu + (1 - b) * (est - mu), b
  ```
  For rates from counts (flips out of votes, wins out of races) report numbers from a beta-binomial or multilevel model (statsmodels `MixedLM`; R `lme4`, needs lme4); the moment version above is a quick audit.
- **Pass criterion (fix before running):** the shrunk top-K is shown beside the raw top-K with sample sizes; every "best" or "worst" claim rests on shrunk estimates.
- **Failure signature:** a leaderboard led by the units with the fewest observations; shrunk estimates then tested as if they were data; maps or tables of raw rates for small areas.
- **Source:** Efron & Morris (1975); Gelman & Price (1999); Love, Huber & Anders (2014); Zhu, Ibrahim & Love (2019); adapted from K-Dense `pydeseq2` (shrink to rank, test unshrunk).

### 2.3 The right background universe for enrichment
- **Tests:** whether a category is over-represented among flagged units relative to the units that could have been flagged.
- **Assumptions of the test itself:** flagged units and category members are subsets of the universe, in one identifier namespace; the threshold that defines "flagged" was fixed before testing.
- **Translation:** "banking-committee members are over-represented among legislators who flipped" needs, as its universe, the members who could have flipped (served the whole window, held a prior position, faced the vote), not every member of the chamber.
- **Run it:**
  ```python
  from scipy.stats import hypergeom
  universe, category, flagged = range(400), range(60), [*range(30), *range(200, 230)]   # synthetic ids
  U = set(universe); C, F = set(category) & U, set(flagged) & U
  N, K, n, k = len(U), len(C), len(F), len(F & C)
  p = hypergeom.sf(k - 1, N, K, n)                  # P(overlap >= k): over-representation
  ratio = (k / n) / (K / N)                         # report with k/n and K/N, never alone
  print(k, n, K, N, p, ratio)
  ```
  With a full ranked list instead of a flagged set, a rank-based test (GSEA-style) avoids an arbitrary threshold. Correct across categories (2.1) and test up and down directions separately.
- **Pass criterion (fix before running):** universe defined and justified before testing; zero flagged units outside the universe; overlap counts reported with every p-value and ratio.
- **Failure signature:** the universe is "everyone"; flagged units missing from the universe because of an ID mismatch; a "significant" category resting on two units.
- **Source:** Subramanian et al. (2005); adapted from K-Dense `pathway-enrichment` (background universe, significance versus relevance, ID mismatch).

### 2.4 Batch effects and cross-cycle harmonization
- **Tests:** whether data-collection batches can masquerade as effects.
- **Assumptions of the test itself:** every batch variable is recorded per row: cycle, collector or pipeline version, vendor, source, annotator or model version, data vintage.
- **Translation:** a sequencing run or a laboratory is a batch; so is an election cycle, a collector rewrite, an LLM-labeler version or a data vendor. The fatal case is a batch boundary that coincides with the label boundary, such as a new collector going live in the same cycle as the policy change under study.
- **Run it:** cross-tabulate batch by label (`pd.crosstab(df.batch, df.label)`); a batch level holding a single label makes that contrast unidentifiable from the data. Prefer modeling batch as a covariate, adjustment terms first (`y ~ batch + label`; `Rscript scripts/regression_report.R --data d.csv --formula "y ~ factor(batch) + label"`), over pre-correcting and then comparing groups. Location-scale correction (ComBat-style) works best in balanced designs; in unbalanced ones, removing batch while protecting group differences exaggerates confidence in later group comparisons. Bridge versions directly: run the new collector on an old cycle and measure the shift on the overlap. Negative control: permute labels within batch; the effect must vanish.
- **Pass criterion (fix before running):** no batch level contains a single label, or the confound is declared and that contrast dropped; the bridged shift is below a stated tolerance; results hold with batch terms included.
- **Failure signature:** a trend that starts exactly at a collector or vendor change; every "treated" unit drawn from one source; batch-corrected data analyzed with the degrees of freedom of uncorrected data.
- **Source:** Leek et al. (2010); Johnson, Li & Rabinovic (2007); Nygaard, Rødland & Hovig (2016); adapted from K-Dense `waypoint-bio` (never let a run boundary coincide with the label boundary), `pydeseq2` (adjustment variables first) and `scanpy` (batch-correction options).

### 2.5 Compositional data: budget and spending shares
- **Tests:** whether shares are analyzed in a geometry that respects their fixed sum.
- **Assumptions of the test itself:** parts are positive or zeros are handled explicitly; the question concerns relative amounts (analyze totals separately when scale matters).
- **Translation:** relative abundances sum to one, and so do a committee's spending mix across party committees, a firm's lobbying mix across issues, and a budget split across channels. When one share rises others must fall, so correlations between raw shares are biased negative and a share can "rise" only because another fell.
- **Run it:** close the composition, replace zeros (disclose the rule) and take log-ratios: centered log-ratios (CLR) for description and distances, isometric log-ratios (ILR) for regression, because CLR coordinates sum to zero and have a singular covariance. The Aitchison distance between two compositions is the Euclidean distance between their CLR vectors.
  ```python
  import numpy as np
  def clr(X, zero=0.5):
      """Centred log-ratio of compositions in rows. Zeros get multiplicative replacement with
      delta = zero * smallest positive share in the data (disclose delta; it moves results)."""
      X = np.asarray(X, float); X = X / X.sum(axis=1, keepdims=True)      # closure
      delta = zero * X[X > 0].min()
      nz = (X == 0).sum(axis=1, keepdims=True)
      Z = np.where(X > 0, X * (1 - nz * delta), delta)                     # rows still sum to 1
      L = np.log(Z)
      return L - L.mean(axis=1, keepdims=True)
  C = clr([[0.5, 0.3, 0.2, 0.0], [0.25, 0.25, 0.25, 0.25]])
  print(np.linalg.norm(C[0] - C[1]))                                       # Aitchison distance
  ```
  scikit-bio's `skbio.stats.composition` adds ILR and compositional differential-abundance tests (needs scikit-bio; not installed on the build machine as of 2026-09-30).
- **Pass criterion (fix before running):** shares analyzed on log-ratios, or every share-based claim carries the closure caveat; the zero rule reported, and conclusions unchanged when delta is halved and doubled; totals analyzed separately where scale matters.
- **Failure signature:** "a larger lobbying share means a smaller PAC share" read as a trade-off; t-tests or correlations on raw shares; results that flip with the zero-replacement constant.
- **Source:** Aitchison (1982); Egozcue et al. (2003); Gloor et al. (2017); adapted from K-Dense `waypoint-bio` and `13c-metabolic-flux` (closure: drop one part and keep the reduced covariance).

### 2.6 Distance-matrix permutation tests: PERMANOVA, Mantel and QAP
- **Tests:** whether two relationship matrices are associated, or groups differ in multivariate distance, without treating dyads as independent.
- **Assumptions of the test itself:** nodes are exchangeable under the null; permutations move whole rows and columns (nodes), never single cells (dyads).
- **Translation:** ecologists correlate genetic distance with geographic distance; a CSS audit asks whether a co-sponsorship network tracks a donor-overlap matrix, or whether committees differ in voting distance. The network form of the Mantel test is QAP; regression on several matrices is MRQAP.
- **Run it:**
  ```python
  import numpy as np
  def mantel(A, B, perms=999, seed=20260930):
      """Correlation of two symmetric matrices (upper triangles), two-sided permutation p-value
      from joint row-and-column permutations of A (nodes, not dyads)."""
      rng = np.random.default_rng(seed)
      iu = np.triu_indices_from(A, k=1)
      r0 = np.corrcoef(A[iu], B[iu])[0, 1]
      hits = sum(abs(np.corrcoef(A[np.ix_(p, p)][iu], B[iu])[0, 1]) >= abs(r0)
                 for p in (rng.permutation(A.shape[0]) for _ in range(perms)))
      return r0, (hits + 1) / (perms + 1)
  ```
  With several predictor matrices use MRQAP with semi-partialling (R `sna::netlm`, needs sna). Read PERMANOVA (R `vegan::adonis2`, needs vegan; or scikit-bio) beside PERMDISP: a PERMANOVA "difference" can be a difference in spread rather than location. Keep the Mantel test for hypotheses stated in terms of distances; for relationships between the underlying variables, or spatial structure, it has low power and other methods fit better.
- **Pass criterion (fix before running):** node-level permutations with at least 999 draws; PERMDISP reported with every PERMANOVA; MRQAP instead of a plain Mantel test when predictor matrices are collinear.
- **Failure signature:** an ordinary p-value computed on n(n−1)/2 dyads; a PERMANOVA effect driven purely by dispersion.
- **Source:** Anderson (2001); Anderson (2006); Legendre, Fortin & Borcard (2015); Krackhardt (1988); Dekker, Krackhardt & Snijders (2007); adapted from K-Dense `scikit-bio`.

### 2.7 Identifiability of fitted constants
- **Tests:** whether a fitted constant is determined by the data or by an arbitrary optimizer choice.
- **Assumptions of the test itself:** as in `engineering-simulation.md` §2.8.
- **Translation:** isotope-tracing flux studies profile each flux and report unresolved directions instead of an arbitrary optimum. A spend-response saturation constant, or a flip-model weight fitted on a few dozen outcomes, needs the same profile before it is called "fitted".
- **Run it:** profile likelihood (`engineering-simulation.md` §2.8), with the planted control: remove the measurement that should pin the parameter and confirm the profile goes flat. Keep data-supported estimates apart from the optimizer's arbitrary point along a flat direction, and label intervals that end on an imposed bound as constraint-limited.
- **Pass criterion (fix before running):** a bracketed profile for every constant that drives a decision.
- **Failure signature:** "a small residual" offered as identification; an interval edge sitting on an imposed bound.
- **Source:** Raue et al. (2009); adapted from K-Dense `13c-metabolic-flux` (references/inference.md).

### 2.8 Near-optimal solution sets (the flux-variability idea)
- **Tests:** whether the allocation an optimizer reports is determined by its objective, or is one of many allocations that score almost the same.
- **Assumptions of the test itself:** objective and constraints are those the allocator uses; the tolerance is fixed before running and is at least the objective's uncertainty, for example tol = max(1% of the optimum, 2 MCSE), as in `finance.md` §2.6.1.
- **Translation:** flux variability analysis reports, for each reaction, the range of flux compatible with near-optimal growth. For an allocator it gives the range of dollars each target could receive while the plan stays within tol of the best achievable outcome.
- **Run it:** for a linear allocator, two LPs per variable (below); for a separable allocator solved greedily or by simulation, `allocation_check(gains, alloc, budget, tol)` returns the same ranges from one gains table (`engineering-simulation.md` §2.10).
  ```python
  import numpy as np
  from scipy.optimize import linprog
  def near_optimal_ranges(c, A_ub, b_ub, bounds, tol):
      """Min and max of each variable over allocations scoring at least the optimum minus tol
      (maximize c @ x; tol in objective units)."""
      c = np.asarray(c, float)
      best = -linprog(-c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method="highs").fun
      A2, b2 = np.vstack([A_ub, -c]), np.append(b_ub, tol - best)          # c @ x >= best - tol
      ranges = []
      for j in range(c.size):
          e = np.eye(c.size)[j]
          lo = linprog(e, A_ub=A2, b_ub=b2, bounds=bounds, method="highs").fun
          hi = -linprog(-e, A_ub=A2, b_ub=b2, bounds=bounds, method="highs").fun
          ranges.append((lo, hi))
      return best, ranges
  print(near_optimal_ranges([1.0, 1.0, 0.5], [[1, 1, 1]], [10], [(0, 10)] * 3, tol=0.2))   # tied: 0..10 each
  ```
- **Pass criterion (fix before running):** a range reported for every target; targets whose range runs from zero to the cap labeled "not determined by the objective".
- **Failure signature:** one point allocation presented as uniquely optimal while ties or noise make many allocations equivalent; per-target dollar figures quoted to the dollar from such a plan.
- **Source:** Mahadevan & Schilling (2003); the idea only (K-Dense `cobrapy` is GPL-2.0; none of its text was used).

### 2.9 Silent drops and coverage
- **Tests:** whether joins, lookups and vocabularies lose units without saying so.
- **Assumptions of the test itself:** both sides of each join are available; a true zero and "not found" can be told apart.
- **Translation:** unmapped gene identifiers fall out of enrichment, and out-of-vocabulary taxa vanish from embeddings. Unmatched donor, committee or registrant identifiers turn into zero dollars. A zero produced by a failed match is missing data, not an observation.
- **Run it:** measure coverage by count and by magnitude, and list what did not match:
  ```python
  import pandas as pd
  left = pd.read_csv("receipts.csv"); right = pd.read_csv("entities.csv")   # entity_id, amount | entity_id, sector
  m = left.merge(right, on="entity_id", how="outer", indicator=True, validate="many_to_one")
  print(m["_merge"].value_counts())                                        # both / left_only / right_only
  dollars = m.loc[m["_merge"] == "both", "amount"].sum() / m.loc[m["_merge"] != "right_only", "amount"].sum()
  ```
  Plant known entities (a negative control for the matcher) and confirm they are found; re-check coverage after every source or vocabulary version change. Spatial joins and crosswalks: `scripts/spatial_audit.py --mode join` (`geospatial.md`).
- **Pass criterion (fix before running):** coverage by count and by dollars above thresholds set in advance (for example 98% of dollars); every zero classified as observed or unmatched.
- **Failure signature:** "nothing significant" traced later to an identifier mismatch; unmatched rows filled with 0; three-quarters of rows matched but under a fifth of the dollars.
- **Source:** adapted from K-Dense `pathway-enrichment` (ID mismatch silently drops matches) and `waypoint-bio` (report vocabulary coverage); fallbacks in `automation.md` §2.9.

### 2.10 Baselines first when labels are few
- **Tests:** whether a complex or pretrained model beats simple baselines at the label count available.
- **Assumptions of the test itself:** every model uses the same held-out split and the same tuning effort.
- **Translation:** in their source benchmark, pretrained microbiome transformers began to beat classical baselines reliably only above roughly ten thousand training examples (Treloar, Ur-Rehman & Yang 2026, a preprint; stated in its abstract). K-Dense's summary adds that they lose to a random forest below about a thousand (UNVERIFIED: not in the abstract, the only part read here). Measure the crossover rather than assume it: stance, flip or salience models trained on a few hundred labelled members face the same arithmetic.
- **Run it:** on one split, fit the base rate, a regularized logistic regression and a random forest on raw features, then the complex model; compare Brier score, calibration and AUC or average precision with intervals (`scripts/calibration_report.py`; `machine-learning.md`).
- **Pass criterion (fix before running):** the complex model beats the best baseline by a margin stated in advance and outside fold-to-fold noise.
- **Failure signature:** no baseline reported; baselines tuned less than the headline model; a gain smaller than the spread across folds.
- **Source:** Treloar, Ur-Rehman & Yang (2026); adapted from K-Dense `waypoint-bio` (scientific caveats: fit the baseline first).

### 2.11 Multi-view integration (named external methods only)
- **Tests:** whether a combined view of several data types (text, votes, money, networks) finds structure that survives checks.
- **Assumptions of the test itself:** each view is scaled and quality-checked on its own before integration.
- **Translation:** MOFA (unsupervised factor analysis across views), DIABLO (supervised multi-block discriminant analysis) and similarity network fusion (SNF) combine omics layers. They are not in the K-Dense library (repository-wide search, tree 65d6e786, as of 2026-09-29) and are not installed here: treat them as external methods to evaluate, not tools this skill runs.
- **Run it:** require stability of factors or clusters across subsamples and seeds, a leave-one-view-out analysis (does one view drive everything?), a label-permutation test for supervised variants, and a comparison with single-view baselines (2.10).
- **Pass criterion (fix before running):** integrated structure reproducible across subsamples and seeds, not driven by one view, and better than single-view baselines out of sample.
- **Failure signature:** clusters that track one view's scale; supervised integration scored in-sample; factors that change with the seed.
- **Source:** Argelaguet et al. (2018); Singh et al. (2019); Wang et al. (2014).

## 3. Checklist

- **OMX-01** Define test families and the correction before looking; report the number of tests per family. `STATISTICAL` · 2.1
- **OMX-02** Use BY (or a permutation-based FDR) when tests are strongly and arbitrarily dependent. `STATISTICAL` · 2.1
- **OMX-03** Rank many units on shrunk estimates, test on unshrunk ones, and show both rankings with sample sizes. `STATISTICAL` · 2.2
- **OMX-04** Never shrink across a boundary that carries the effect of interest. `STATISTICAL` · 2.2
- **OMX-05** Define the enrichment universe as the units that could have been flagged; assert flagged units lie inside it. `STATISTICAL` · 2.3
- **OMX-06** Report overlap counts (k of n against K of N) with every enrichment p-value; correct across categories. `PRESENTATION` · 2.3
- **OMX-07** Record batch variables (cycle, collector version, vendor, annotator or model version, vintage) on every row. `DATA` · 2.4
- **OMX-08** Cross-tabulate batch by label; drop or declare any contrast whose batch and label boundaries coincide. `DATA` · 2.4
- **OMX-09** Model batch as a covariate instead of pre-correcting and then comparing groups; bridge versions on overlapping data. `DATA` · 2.4
- **OMX-10** Analyze shares on log-ratios (CLR, ILR), or attach the closure caveat to every share claim. `FUNCTIONAL-FORM` · 2.5
- **OMX-11** Disclose the zero-replacement rule and show conclusions survive halving and doubling it. `FUNCTIONAL-FORM` · 2.5
- **OMX-12** Test matrix associations with node-level permutations (Mantel, QAP, MRQAP), never dyad-level p-values. `STATISTICAL` · 2.6
- **OMX-13** Report PERMDISP beside every PERMANOVA. `STATISTICAL` · 2.6
- **OMX-14** Profile every fitted constant that drives a decision; report flat profiles as priors. `STATISTICAL` · 2.7
- **OMX-15** Report near-optimal ranges for every allocated target and label the undetermined ones. `DECISION` · 2.8
- **OMX-16** Measure join coverage by count and by magnitude, list unmatched units, and split zeros into observed and unmatched. `DATA` · 2.9
- **OMX-17** Plant known entities to test every matcher; re-check coverage after each source or vocabulary change. `DATA` · 2.9
- **OMX-18** Fit base-rate, linear and tree baselines on the same split before any complex model. `STATISTICAL` · 2.10
- **OMX-19** Require stability, leave-one-view-out and permutation checks for any multi-view integration. `MEASUREMENT` · 2.11
- **OMX-20** State the translation from the biological method to the finance or CSS use in every report that borrows one. `PRESENTATION` · 2.1-2.11

## 4. Pitfalls and anti-patterns

- Treating a method as validated for political or financial data because it is standard in genomics. Each transfer needs its own checks.
- FDR applied separately to many families, then the most striking family reported.
- Leaderboards of raw per-unit rates whose top and bottom are simply the smallest units.
- Enrichment tested against "all units" when only some could have been flagged.
- A collector, vendor or labeler change timed with the change under study.
- Batch-corrected data compared across groups as if no correction had happened.
- Correlations between raw shares read as trade-offs.
- One optimal allocation quoted to the dollar when many allocations are equivalent within noise.
- Unmatched identifiers turned into zeros.
- A foundation model or embedding reported without the simple baseline it had to beat.

## 5. References

- Aitchison, J. (1982). The Statistical Analysis of Compositional Data. *Journal of the Royal Statistical Society Series B: Statistical Methodology* 44(2), 139-160. DOI: 10.1111/j.2517-6161.1982.tb01195.x
- Anderson, M. J. (2001). A new method for non-parametric multivariate analysis of variance. *Austral Ecology* 26(1), 32-46. DOI: 10.1111/j.1442-9993.2001.01070.pp.x
- Anderson, M. J. (2006). Distance-Based Tests for Homogeneity of Multivariate Dispersions. *Biometrics* 62(1), 245-253. DOI: 10.1111/j.1541-0420.2005.00440.x
- Argelaguet, R., Velten, B., Arnol, D., et al. (2018). Multi-Omics Factor Analysis—a framework for unsupervised integration of multi-omics data sets. *Molecular Systems Biology* 14(6). DOI: 10.15252/msb.20178124
- Benjamini, Y., & Hochberg, Y. (1995). Controlling the False Discovery Rate: A Practical and Powerful Approach to Multiple Testing. *Journal of the Royal Statistical Society Series B: Statistical Methodology* 57(1), 289-300. DOI: 10.1111/j.2517-6161.1995.tb02031.x
- Benjamini, Y., & Yekutieli, D. (2001). The control of the false discovery rate in multiple testing under dependency. *The Annals of Statistics* 29(4). DOI: 10.1214/aos/1013699998
- Dekker, D., Krackhardt, D., & Snijders, T. A. B. (2007). Sensitivity of MRQAP Tests to Collinearity and Autocorrelation Conditions. *Psychometrika* 72(4), 563-581. DOI: 10.1007/s11336-007-9016-1
- Efron, B., & Morris, C. (1975). Data Analysis Using Stein's Estimator and its Generalizations. *Journal of the American Statistical Association* 70(350), 311-319. DOI: 10.1080/01621459.1975.10479864
- Egozcue, J. J., Pawlowsky-Glahn, V., Mateu-Figueras, G., & Barceló-Vidal, C. (2003). Isometric Logratio Transformations for Compositional Data Analysis. *Mathematical Geology* 35(3), 279-300. DOI: 10.1023/a:1023818214614
- Gelman, A., & Price, P. N. (1999). All maps of parameter estimates are misleading. *Statistics in Medicine* 18(23), 3221-3234. DOI: 10.1002/(sici)1097-0258(19991215)18:23<3221::aid-sim312>3.0.co;2-m
- Gloor, G. B., Macklaim, J. M., Pawlowsky-Glahn, V., & Egozcue, J. J. (2017). Microbiome Datasets Are Compositional: And This Is Not Optional. *Frontiers in Microbiology* 8. DOI: 10.3389/fmicb.2017.02224
- Johnson, W. E., Li, C., & Rabinovic, A. (2007). Adjusting batch effects in microarray expression data using empirical Bayes methods. *Biostatistics* 8(1), 118-127. DOI: 10.1093/biostatistics/kxj037
- Krackhardt, D. (1988). Predicting with networks: Nonparametric multiple regression analysis of dyadic data. *Social Networks* 10(4), 359-381. DOI: 10.1016/0378-8733(88)90004-4
- Leek, J. T., Scharpf, R. B., Bravo, H. C., et al. (2010). Tackling the widespread and critical impact of batch effects in high-throughput data. *Nature Reviews Genetics* 11(10), 733-739. DOI: 10.1038/nrg2825
- Legendre, P., Fortin, M.-J., & Borcard, D. (2015). Should the Mantel test be used in spatial analysis? *Methods in Ecology and Evolution* 6(11), 1239-1247. DOI: 10.1111/2041-210x.12425
- Love, M. I., Huber, W., & Anders, S. (2014). Moderated estimation of fold change and dispersion for RNA-seq data with DESeq2. *Genome Biology* 15(12). DOI: 10.1186/s13059-014-0550-8
- Mahadevan, R., & Schilling, C. H. (2003). The effects of alternate optimal solutions in constraint-based genome-scale metabolic models. *Metabolic Engineering* 5(4), 264-276. DOI: 10.1016/j.ymben.2003.09.002
- Nygaard, V., Rødland, E. A., & Hovig, E. (2016). Methods that remove batch effects while retaining group differences may lead to exaggerated confidence in downstream analyses. *Biostatistics* 17(1), 29-39. DOI: 10.1093/biostatistics/kxv027
- Raue, A., Kreutz, C., Maiwald, T., et al. (2009). Structural and practical identifiability analysis of partially observed dynamical models by exploiting the profile likelihood. *Bioinformatics* 25(15), 1923-1929. DOI: 10.1093/bioinformatics/btp358
- Singh, A., Shannon, C. P., Gautier, B., et al. (2019). DIABLO: an integrative approach for identifying key molecular drivers from multi-omics assays. *Bioinformatics* 35(17), 3055-3062. DOI: 10.1093/bioinformatics/bty1054
- Storey, J. D. (2002). A Direct Approach to False Discovery Rates. *Journal of the Royal Statistical Society Series B: Statistical Methodology* 64(3), 479-498. DOI: 10.1111/1467-9868.00346
- Storey, J. D., & Tibshirani, R. (2003). Statistical significance for genomewide studies. *Proceedings of the National Academy of Sciences* 100(16), 9440-9445. DOI: 10.1073/pnas.1530509100
- Subramanian, A., Tamayo, P., Mootha, V. K., et al. (2005). Gene set enrichment analysis: A knowledge-based approach for interpreting genome-wide expression profiles. *Proceedings of the National Academy of Sciences* 102(43), 15545-15550. DOI: 10.1073/pnas.0506580102
- Treloar, N. J., Ur-Rehman, S., & Yang, J. (2026). Learning the Language of the Microbiome with Transformers. *bioRxiv* (preprint, posted 2026-05-06; not peer reviewed). DOI: 10.64898/2026.05.02.722381
- Wang, B., Mezlini, A. M., Demir, F., et al. (2014). Similarity network fusion for aggregating data types on a genomic scale. *Nature Methods* 11(3), 333-337. DOI: 10.1038/nmeth.2810
- Zhu, A., Ibrahim, J. G., & Love, M. I. (2019). Heavy-tailed prior distributions for sequence count data: removing the noise and preserving large differences. *Bioinformatics* 35(12), 2084-2092. DOI: 10.1093/bioinformatics/bty895

All DOIs were resolved against CrossRef on 2026-09-30 (titles, authors and venues match; no retraction or correction notices); Benjamini & Hochberg, Gelman & Price, Krackhardt and Dekker et al. were also verified in the social-science research file. For Treloar et al. only the abstract (via OpenAlex) was read, not the full preprint.

**Adapted from** (ideas paraphrased; no text or code copied): K-Dense `pydeseq2` (SKILL.md key reminders: adjustment variables first, BH, shrink only to rank; MIT), `pathway-enrichment` (SKILL.md workflow and pitfalls; references/interpretation.md; MIT), `scikit-bio` (SKILL.md: PERMANOVA with PERMDISP, Mantel; BSD-3-Clause), `waypoint-bio` (SKILL.md scientific caveats; MIT), `scanpy` (SKILL.md batch-correction options; BSD-3-Clause), `13c-metabolic-flux` (SKILL.md; references/inference.md; MIT). From `cobrapy` (GPL-2.0) only the flux-variability idea is used, cited to its primary source; no cobrapy text appears here.
