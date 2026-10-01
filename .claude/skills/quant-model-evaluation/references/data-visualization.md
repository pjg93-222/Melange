# Data visualization — quant-model-evaluation reference

> **Load when:** auditing a chart, dashboard, report table or exported figure that presents a model's numbers; checking labels, units, rounding, ranks, tiers, totals, or clamped and smoothed curves; checking that a front end reproduces the model; deciding whether a surface describes or advises. **Not for:** the statistics behind the intervals (`core-statistics.md`); map geometry, MAUP and spatial dependence (`geospatial.md`); parity harnesses, determinism and freshness (`automation.md`); reliability diagrams for classifiers (`machine-learning.md`); the model-risk status of advisory tools (`regulatory.md`).
> Facts marked (as of DATE) are time-sensitive; re-verify before relying on them. `[RUN]` marks behaviour reproduced when this file was written (2026-09-30; Python 3.12.10, NumPy 2.4.6, pandas 3.0.3, SciPy 1.18.0, matplotlib; R 4.6.0; Node 24.18.0). Rounding, ranking and quantile defaults are library behaviour: re-run the checks on the versions in use. A KILLED printed by a script is a candidate until a second independent reader confirms it (SKILL.md hard rule 5).

## 1. Assumption map

| Assumption (class) | Where it usually hides | What breaks if it is false | Tests |
|---|---|---|---|
| Length, area and slope encode magnitude honestly (PRESENTATION) | Bar charts with auto-scaled axes, dual axes, log axes, bubbles | Effects look larger or smaller than they are | §2.1 |
| Colour matches the data type and survives colour-vision deficiency (PRESENTATION) | Heatmaps, choropleths, category palettes, traffic lights | False boundaries; order misread; information lost for some readers | §2.2 |
| Every estimate shows its uncertainty, of the right kind (PRESENTATION, STATISTICAL) | KPI tiles, rankings, forecast lines | Overconfidence; parameter intervals read as outcome ranges | §2.3 |
| The drawn curve is the model's output (PRESENTATION, COMPUTATIONAL) | Response curves, frontiers, "monotone" series, capped tails | Model defects hidden; checks that read the display cannot fail | §2.4 |
| Display rounding keeps the information a decision needs (PRESENTATION, COMPUTATIONAL) | Number formatters, $k and $M suffixes, exports | Small values shown as 0; totals that do not add; two surfaces disagree | §2.5 |
| Ranks are deterministic under ties and larger than their noise (STATISTICAL, PRESENTATION) | Leaderboards, percentile ranks, top-10 lists | Ranks change when rows are re-sorted; noise ranked as signal | §2.6 |
| The label's unit, denominator, price basis and window match the computation (MEASUREMENT, PRESENTATION) | Tooltips, column headers, KPI captions | Wrong scale; per-capita vs total; nominal vs real; circular metrics | §2.7 |
| Displayed aggregates are additive and tier labels mean what readers think (PRESENTATION) | Totals rows, rollups, quartile badges | Summed medians or rates; relative tiers read as absolute levels | §2.8 |
| The front end computes what the model computes (COMPUTATIONAL) | JavaScript ports of scoring, ranking, rounding | Two answers to one question | §2.9 |
| The surface's role, describe or advise, is declared and matches its wording (DECISION, PRESENTATION) | "Recommended", "best", "priority", colour-coded advice | An unvalidated model acting as advice | §2.10 |
| Numbers agree across text, tables, charts and source (PRESENTATION) | Executive summaries, captions, exports | Internal contradictions; stale numbers | §2.11 |
| Map colour shows the estimate, not the size of the unit (STATISTICAL, PRESENTATION) | Rate choropleths | Small-population units look extreme | §2.12 |

## 2. Tests

### 2.1 Honest encoding: baselines, aspect, dual axes, log scales, area
- **Tests:** whether the chart's geometry preserves the magnitudes it encodes.
- **Assumptions of the test itself:** readers judge position on a common scale most accurately, then length, then angle and area, then colour (Cleveland & McGill 1984; replicated by Heer & Bostock 2010); the auditor has the data behind the chart.
- **Run it:**
  - Bars and filled areas encode length from a baseline and must start at zero; truncated axes inflate perceived differences even when the truncation is flagged (Correll et al. 2020; Pandey et al. 2015).
  - Lines and points may use a non-zero range, but for standardized effects keep at least 1 SD of range, about 1.5 SD preferred (Witt 2019), and put panels meant for comparison on one scale.
  - Aspect ratio changes perceived slope: bank the lines to about 45° or show two aspects before judging a trend (Cleveland, McGill & McGill 1988).
  - Replace dual y-axes with aligned panels or indexed series: readers misjudge dual-scale charts, and either axis can be rescaled to fake a correlation (Isenberg et al. 2011).
  - Label log axes with the base and state how zeros are handled; many readers misread log scales (Menge et al. 2018). Scale bubbles by area, never radius; drop 3D.
  - Audit an existing matplotlib figure [RUN]:
  ```python
  for ax in fig.axes:
      bars = any(type(p).__name__ == "Rectangle" for p in ax.patches)
      if bars and ax.get_ylim()[0] != 0: print("bar axis not at 0:", ax.get_title(), ax.get_ylim())
      if ax.get_yscale() != "linear": print("non-linear axis:", ax.get_title(), ax.get_yscale(), repr(ax.get_ylabel()))
      if len(ax.get_shared_x_axes().get_siblings(ax)) > 1: print("dual-axis candidate:", ax.get_title())
  ```
- **Pass criterion (fix before running):** zero baseline for every length or area encoding; no dual y-axis without an aligned-panel alternative; log axes labelled with base; compared panels share limits.
- **Failure signature:** a 3% gap drawn as a threefold bar; two series that move together only because one axis was rescaled; an auto-fitted axis that makes a flat series look volatile.
- **Source:** Cleveland & McGill (1984); Heer & Bostock (2010); Correll, Bertini & Franconeri (2020); Pandey et al. (2015); Witt (2019); Cleveland, McGill & McGill (1988); Isenberg et al. (2011); Menge et al. (2018).

### 2.2 Colour: palette type, perceptual order, colour-vision safety, missing values
- **Tests:** whether colour encodes the right kind of data without inventing structure or hiding it from some readers.
- **Assumptions of the test itself:** ordered data need a palette whose lightness changes monotonically; a sizeable minority of readers have a colour-vision deficiency, so hue alone cannot carry meaning.
- **Run it:**
  - Match palette to data: sequential for ordered magnitudes; diverging only around a meaningful centre (zero change, a target), with the centre stated; qualitative for categories, at most about 7–8, with direct labels or markers as a second cue.
  - Rainbow and jet maps create boundaries that are not in the data and hide order (Borland & Taylor 2007; Crameri et al. 2020). Prefer perceptually uniform maps such as viridis or the deficiency-optimized cividis (Nuñez et al. 2018), ColorBrewer schemes at their stated class counts (Harrower & Brewer 2003), and the Okabe–Ito set for categories (Wong 2011).
  - Give missing values their own labelled neutral colour, never the low end of the scale.
  - Lightness check (relative luminance of linearized sRGB) [RUN: viridis, cividis and Blues pass; jet and rainbow fail]:
  ```python
  import numpy as np, matplotlib.pyplot as plt
  def lightness_monotone(name, n=256):
      rgb = plt.get_cmap(name)(np.linspace(0, 1, n))[:, :3]
      lin = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
      d = np.diff(lin @ np.array([0.2126, 0.7152, 0.0722]))
      return bool(np.all(d >= -1e-9) or np.all(d <= 1e-9))
  ```
  - For web delivery, WCAG 2.2 asks for 3:1 contrast for graphical objects needed to understand the content and for colour never to be the only cue (as of 2026-07-23 per K-Dense scientific-visualization; re-verify).
- **Pass criterion (fix before running):** palette type matches the data; monotone lightness for ordered data; a non-colour cue for every category; missing values distinct and labelled.
- **Failure signature:** bands in a rainbow heatmap that are not in the data; red versus green as the only distinction; missing data drawn as the minimum; a diverging map centred on an arbitrary value.
- **Source:** Borland & Taylor (2007); Crameri, Shephard & Heron (2020); Nuñez, Anderton & Renslow (2018); Harrower & Brewer (2003); Wong (2011).

### 2.3 Uncertainty: intervals always, the right interval, and tests readers can run by eye
- **Tests:** whether every displayed estimate carries its uncertainty, whether the interval answers the reader's question, and whether a "visible" trend is really there.
- **Assumptions of the test itself:** readers misread error bars (Belia et al. 2005; Cumming & Finch 2005); overlapping 95% CIs do not imply a non-significant difference (Schenker & Gentleman 2001); bars with error bars bias reading (Correll & Gleicher 2014).
- **Run it:**
  - Name every interval (SD, SE, 95% CI, prediction interval, credible interval) with its n and unit of replication in the caption.
  - Pair every printed regression with a coefficient plot on one scale that uses the robust intervals from the inference block (Kastellec & Leoni 2007; Gelman, Pasarica & Dodhia 2002; `core-statistics.md` §2.14, `scripts/regression_report.R`).
  - Where readers judge outcomes for a unit, show prediction intervals: coefficient intervals lead readers to overrate effects (Hofman et al. 2020).
  - For orderings and trends, hypothetical outcome plots (animated draws) beat error bars (Hullman et al. 2015; Kale et al. 2019); quantile dotplots improve decisions (Kay et al. 2016; Fernandes et al. 2018).
  - Fan charts: nested central intervals that widen with horizon. Check that each band's realized coverage matches its label: `python scripts/backtest_eval.py --data f.csv --actual y --forecast yhat --time t --lower lo --upper hi --level 0.9` (PICP, Kupiec, Christoffersen). `--time` must hold numbers or dates (text needs `--allow-text-time`; infinite values are refused as input errors). BT-COVER SURVIVES when Kupiec p ≥ `--alpha` (0.10); a rejection with coverage below the level is KILLED (bands too narrow) and above it WOUNDED (too wide); BT-INDEP checks that misses do not cluster. On a synthetic 60-period file the command exited 1, with BT-COVER SURVIVES at PICP 0.90 [RUN].
  - Before claiming a trend is visible, run a lineup: hide the real panel among 19 panels with y permuted (`pos = rng.integers(20); panels = [y if i == pos else rng.permutation(y) for i in range(20)]`); if a viewer who has not seen the data picks it, p ≈ 1/20 (Buja et al. 2009; Wickham et al. 2010).
- **Pass criterion (fix before running):** no point-only display of an estimate; interval type and n in every caption; prediction intervals for outcome judgments; fan coverage within its backtest tolerance; a passed lineup for every "visible trend" claim.
- **Failure signature:** KPI tiles with bare numbers; "the CIs overlap, so there is no difference"; SE bars chosen because they look tight; a band labelled 90% that covers 60% out of sample.
- **Source:** Kastellec & Leoni (2007); Gelman, Pasarica & Dodhia (2002); Hofman, Goldstein & Hullman (2020); Hullman, Resnick & Adar (2015); Kale et al. (2019); Kay et al. (2016); Fernandes et al. (2018); Belia et al. (2005); Cumming & Finch (2005); Schenker & Gentleman (2001); Correll & Gleicher (2014); Buja et al. (2009); Wickham et al. (2010); Padilla, Kay & Hullman (2021).

### 2.4 Display transforms that hide model behaviour
- **Tests:** whether the plotted series is the model's output or a transformed version: clamped or capped, running maximum ("monotonized"), smoothed, winsorized, or interpolated across gaps.
- **Assumptions of the test itself:** the auditor can obtain raw model output on the same grid as the display.
- **Run it:**
  - Compare raw output with the displayed series point by point. A running maximum hides every dip in a curve that ought to be monotone, and any check run on the displayed series (for instance "the response curve never decreases") can no longer fail. Point the check at raw output and prove it can fail with `scripts/mutation_check.py` (§2.9).
  - Winsorizing hides the tail that often drives totals; smoothing and interpolation imply values between observations.
  - Show raw and transformed together (raw as points, the transform as a labelled line) and state the share of points the transform changed. On a seven-point curve with one dip, the running maximum altered 2 of 7 points [RUN].
  ```python
  import numpy as np
  raw, shown = np.asarray(model_output), np.asarray(display_series)             # same x-grid
  monotonized = np.allclose(shown, np.maximum.accumulate(raw)) and not np.all(np.diff(raw) >= 0)
  changed = int((~np.isclose(shown, raw)).sum())                                 # points altered by the transform
  at_cap = float(np.mean(np.isclose(shown, shown.max())))                        # share sitting on a cap
  ```
- **Pass criterion (fix before running):** every transform disclosed on the chart; raw shown beside transformed; every validation check reads raw output; share of altered points reported.
- **Failure signature:** flat plateaus where the model declines; "monotone by construction"; a winsorized tail that drops the units that dominate a sum; lines drawn across missing periods.
- **Source:** Weissgerber et al. (2015); Rougier, Droettboom & Bourne (2014).

### 2.5 Rounding and quantization
- **Tests:** whether display rounding changes what a reader concludes, and whether two implementations show the same digits for the same value.
- **Assumptions of the test itself:** rounding behaviour depends on language, library and version (as of 2026-09-30); re-run the half-way cases on the stack in use.
- **Run it:**
  - Know the rules [RUN]. Python `round`, NumPy and pandas round half to even: `round(2.5) == 2`, `round(500, -3) == 0`, and `round(1500, -3) == round(2500, -3) == 2000`; binary storage makes `round(2.675, 2) == 2.67`. R `round(2.5)` is also 2, and `round(0.15, 1)` is 0.1. JavaScript `Math.round(2.5)` is 3 and `Math.round(-2.5)` is −2; `(1.005).toFixed(2)` is "1.00" while `Intl.NumberFormat` shows "1.01". A Python backend and a JavaScript front end can therefore disagree on the same number; binary floating point (IEEE 2019) underlies the edge cases.
  - Small values vanish: showing dollars in $k turns everything under $500 into 0; in a seven-value test, 4 nonzero amounts displayed as "0" [RUN].
  - Totals stop adding: three shares of 1/3 display as 33.3% and sum to 99.9%; five amounts of $400 display as $0k each while their total displays as $2k [RUN]. State "may not sum due to rounding", or use one rule (e.g. largest remainder) everywhere; never compute a total from rounded parts.
  - Quantization: tiers, stars and bins discard order; count the units within a small ε of each tier boundary, because they change tier on noise.
  ```python
  shown = (vals / 1000).round(0)                         # the display rule under audit ($ -> $k)
  vanished = int(((vals != 0) & (shown == 0)).sum())     # nonzero values displayed as 0
  gap = shown.sum() - round(vals.sum() / 1000)           # sum of shown parts vs the shown total
  ```
- **Pass criterion (fix before running):** no nonzero decision-relevant value displays as 0 (show "<0.5k" instead); displayed totals reconcile to source within a stated tolerance; one documented rounding rule across backend, front end and exports; boundary-proximity counts reported for tiers.
- **Failure signature:** "$0" next to a nonzero contribution; a KPI total that differs from its table's column sum; one entity with two values on two surfaces.
- **Source:** IEEE (2019); rounding only at the point of reporting follows K-Dense uncertainty-and-units (reporting rules).

### 2.6 Ranks, ties and rank uncertainty
- **Tests:** whether a rank or percentile rank is deterministic under ties, and whether rank differences exceed rank noise.
- **Assumptions of the test itself:** ranks inherit the noise of the scores they order, and small score gaps become whole rank steps.
- **Run it:**
  - Name the tie rule. For the values [10, 20, 20, 20, 30], the three tied values get percentile rank 0.6 (midrank), 0.4 (min), 0.8 (max), or 0.4/0.6/0.8 by row order under `method="first"` or any rank taken from a sort index; SciPy `percentileofscore(a, 20, kind=...)` returns 20, 50, 60 or 80 for `strict`, `mean`, `rank` and `weak` [RUN].
  - Use midranks (R `rank()` default; pandas `rank(method="average")`) and prove determinism: shuffle the rows, re-rank, compare.
  - Quantify rank uncertainty: bootstrap the units behind each score and re-rank (Hall & Miller 2009); show rank intervals or P(A outranks B); for rates, prefer funnel plots to league tables (Spiegelhalter 2005); check top-K stability with `python scripts/mc_error.py --data reps.csv --rep rep --entity entity --score score --topk 10`. `--rep` is required for top-K input (without it the script exits 2 [RUN]); P(same set) ≥ `--min-stability` (0.9) SURVIVES, and below `--kill-below` (0.5) it is KILLED, because the seed rather than the model then decides the set.
  ```python
  import numpy as np, pandas as pd
  groups = {k: g.to_numpy() for k, g in units.groupby("entity")["value"]}    # unit-level rows
  names, rng = sorted(groups), np.random.default_rng(20260930)
  boot = np.array([pd.Series({k: rng.choice(v, v.size).mean() for k, v in groups.items()})[names]
                   .rank(ascending=False, method="average").to_numpy() for _ in range(999)])
  lo, hi = np.percentile(boot, [2.5, 97.5], axis=0)                          # 95% rank interval per entity
  ```
  With 8 entities, 12 observations each and true means 0.1 SD apart, 7 of 8 rank intervals spanned five or more places, and the truly higher of two neighbours ranked above the other in only 47% of resamples [RUN].
- **Pass criterion (fix before running):** tie rule named and deterministic (identical output after a row shuffle); rank intervals or pairwise probabilities wherever ranks are displayed; no "A beats B" claim when P(A outranks B) is near 0.5.
- **Failure signature:** ranks that change when the input file is re-sorted; a percentile rank with no stated rule; rank 3 vs rank 7 treated as meaningful when both intervals span most of the table.
- **Source:** Goldstein & Spiegelhalter (1996); Marshall et al. (1998); Hall & Miller (2009); Spiegelhalter (2005).

### 2.7 Metric-definition audit: label vs computation
- **Tests:** whether each displayed metric's label (name, unit, scale, denominator, window, price basis) matches what the code computes.
- **Assumptions of the test itself:** the auditor can read the code that produces the number (file:line) and recompute it from raw data by a second path.
- **Run it:**
  - Build one row per displayed metric:

  | Label as shown | Unit implied | Formula (file:line) | Unit computed | Numerator / denominator | Window | Nominal or real | Vintage |
  |---|---|---|---|---|---|---|---|

  - Recompute three to five values from raw data by an independent path.
  - Check scale words ("per $1k" vs per dollar); per-capita vs totals (maps and rankings of totals mostly track population, while per-capita rates of small units are noisy; Gelman & Price 1999); nominal vs real (name the deflator, base year and index vintage, and never mix bases in one total or growth rate); stock vs flow; gross vs net; calendar year vs election cycle.
  - Flag circular metrics: an ROI or cost-per-outcome score computed from outcomes that the optimizer itself predicts measures the model's internal consistency, not results, and cannot evaluate that optimizer.
- **Pass criterion (fix before running):** a complete row for every displayed metric; second-path recomputation agrees within display rounding; no circular metric presented as evidence of performance.
- **Failure signature:** "cost per vote" computed per thousand votes; ten-year "growth" in nominal dollars; a map of totals that is really a population map; an efficiency score validated against its own predictions.
- **Source:** Gelman & Price (1999); measurement-contract items adapted from K-Dense market-research-reports.

### 2.8 Aggregation and forced-quantile labels
- **Tests:** whether the totals and averages shown are valid for the quantity, and whether tier labels imply levels they do not have.
- **Assumptions of the test itself:** the auditor knows each column's quantity type: count, amount, rate, share, median, rank, probability, index.
- **Run it:**
  - Sum only additive quantities (counts, amounts, expected counts). Pool rates from numerators and denominators: the mean of 1/10 and 90/100 is 50%, the pooled rate 82.7% [RUN]. Never sum medians, percentiles, ranks or maxima: for a = (1, 2, 100) and b = (100, 4, 5), median(a) + median(b) = 7 but median(a + b) = 101 [RUN]. A sum of probabilities is an expected count, not a probability.
  - Tiers: quartiles put a quarter of units in each tier by construction, so "top quartile" says nothing about the absolute level; show the cut points in units.
  - Binning on ranks splits ties: `pd.qcut(x.rank(method="first"), 4)` put identical zeros into three different quartiles, and `pd.qcut(x, 4)` on data that are 60% zeros raises an error unless `duplicates="drop"`, which silently returns 2 bins instead of 4 [RUN].
  - Quantile definitions differ: the 0.25 quantile of 1..10 is 3.25 (R type 7, the NumPy and pandas default), 2.75 (R type 6, NumPy `method="weibull"`) or 3.0 (R type 1, `method="inverted_cdf"`) [RUN; Hyndman & Fan 1996], so two implementations can draw different tier boundaries.
  ```python
  edges = np.unique(np.quantile(x, [0, .25, .5, .75, 1]))      # tie-safe: equal values share a tier
  tiers = pd.cut(x, bins=edges, include_lowest=True)           # report len(edges) - 1 tiers and the edges
  ```
- **Pass criterion (fix before running):** only additive quantities summed; rates pooled from numerator and denominator; tier cut points shown in units; ties never split across tiers; fewer tiers than labels disclosed; one named quantile definition across implementations.
- **Failure signature:** a "Total" row of medians or percentages; an average of percentages presented as the overall rate; identical units in different tiers; "top quartile" read as "high".
- **Source:** Hyndman & Fan (1996).

### 2.9 Parity between front-end code and the model it mirrors
- **Tests:** whether display code (JavaScript dashboard, spreadsheet, report generator) reproduces the model's numbers digit for digit.
- **Assumptions of the test itself:** the model's outputs on a fixed fixture are the reference, and the fixture exercises the display edge cases.
- **Run it:** the general parity recipe (inventory every copy, trace each constant to one definition, a shared fixture grid, coverage before accuracy) lives in `automation.md` §2.7. This section adds what is specific to display code.
  - Freeze a golden fixture with ties, zeros, missing values, negatives, very large values, half-way rounding cases and values on tier boundaries; export the model's displayed values for it; run the front-end code on it headlessly (e.g. in Node) and diff every field.
  - Check the display divergences: rounding rule (§2.5), tie rule and quantile type (§2.6, §2.8), sort stability, null vs NaN vs 0, date parsing and time zones, stale copies of constants.
  - Fix the tolerance before comparing, but only after propagating the fixture's stored precision (jitter rounded inputs within their rounding span): a bar tighter than the exported digits allow can never be met.
  - Prove the check can fail: `python scripts/mutation_check.py --input golden.json --auto --cmd node parity_check.js '{input}'`. Declare mutants that the check cannot catch by design with `--expect-survive`, and justify each. On a synthetic $k display fixture, 9 of 10 mutants were killed; the survivor swapped two inputs that both display as $0k (exit 1, WOUNDED). With `--expect-survive swap_adjacent:/values` the run exited 0, listing that mutant as EXPECTED-SURVIVOR [RUN]. The script executes the command given, so point it only at approved checks.
- **Pass criterion (fix before running):** every golden row present and within the pre-set tolerance; every unexpected mutant killed and every expected survivor justified in the report; the parity test re-run whenever either implementation changes.
- **Failure signature:** a hard-coded constant the model has since changed; a front end that treats null as 0; ranks that differ only for tied entities; a tolerance no fixture could meet.
- **Source:** canonical recipe in `automation.md` §2.7; this skill's protocol (`SKILL.md`: model card "implementations"; hard rule 6 on controls).

### 2.10 Descriptive vs advisory surfaces
- **Tests:** whether a surface recommends action (ranks for action, names a "best" or "priority" target, suggests amounts, colours cells as act/avoid) while it is documented or validated only as description.
- **Assumptions of the test itself:** wording, ordering and colour carry advice even without the word "recommend".
- **Run it:**
  - Search the surface's templates and strings for advisory language, then classify each surface as descriptive or advisory:
  ```python
  import re, pathlib
  pat = re.compile(r"\b(recommend\w*|best|should|prioriti\w*|target\w*|opportunit\w*|undervalued|next action)\b", re.I)
  for p in pathlib.Path("ui").rglob("*"):
      if p.is_file() and p.suffix in {".html", ".js", ".ts", ".jsx", ".tsx", ".json", ".md"}:
          for i, line in enumerate(p.read_text(errors="ignore").splitlines(), 1):
              if pat.search(line): print(f"{p}:{i}: {line.strip()[:100]}")
  ```
  - An advisory surface is a decision model: it needs the full protocol (objective and units, validation against outcomes, uncertainty, owner sign-off), and model-risk guidance may treat it as a model (`regulatory.md`).
  - A descriptive surface uses neutral wording ("highest reported receipts", not "best target") and no colour semantics that imply action.
- **Pass criterion (fix before running):** every advisory surface is registered as a model with a validation record; descriptive surfaces carry no advisory wording, ordering or colour that implies action.
- **Failure signature:** a leaderboard titled "top targets" built from an unvalidated score; green and red "act/avoid" colouring on descriptive data.
- **Source:** this skill's presentation contract (`SKILL.md`; `core-statistics.md` §2.14); model-risk status in `regulatory.md`.

### 2.11 Numeric consistency of reports and dashboards
- **Tests:** whether every number agrees with its source and with every other place it appears.
- **Assumptions of the test itself:** each number can be extracted with its label and mapped to a source row.
- **Run it:**
  - Extract every number with its label from text, tables, captions and tiles.
  - Keep a registry keyed by concept and analysis set, holding value, unit, denominator, n, window, vintage and source. The same concept must carry the same value, unit, n and denominator everywhere; every percentage must equal numerator/denominator within display rounding; no numerator may exceed its denominator.
  - Recompute reported statistics: p from t and df (a reported t = 2.10 with df = 40 implies p = 0.042, not 0.03), as statcheck does at scale (Nuijten et al. 2016); GRIM for means of integer data (a mean of 3.48 from 19 integer responses is impossible, 3.47 is possible; Brown & Heathers 2017) [RUN]; totals against the sum of parts; a symmetric 95% interval against estimate ± 1.96·SE.
  - Check that vintages and as-of dates agree across sections.
  ```python
  import math
  from scipy import stats
  p_from_t = lambda t, df: 2 * stats.t.sf(abs(t), df)
  def grim_ok(mean, n, decimals=2):  # can n integers average to this reported mean?
      return any(round(s / n, decimals) == round(mean, decimals) for s in (math.floor(mean * n), math.ceil(mean * n)))
  ```
- **Pass criterion (fix before running):** zero unresolved inconsistencies; every number traces to a source row and a run's provenance line.
- **Failure signature:** an executive summary quoting an older run; a percentage computed on a different denominator than its table; a p-value that its own t and df cannot produce.
- **Source:** Nuijten et al. (2016); Brown & Heathers (2017); the cross-section registry idea adapted from K-Dense scientific-writing.

### 2.12 Maps
- **Tests:** whether a choropleth shows the estimate or the size of the unit.
- **Assumptions of the test itself:** the denominator (population, voters, accounts) is known for every unit.
- **Run it:** raw-rate maps make small-population units the extremes (Gelman & Price 1999). Map shrunken estimates, or encode uncertainty with value-suppressing palettes (Correll, Moritz & Heer 2018); choose class breaks deliberately and report them (Brewer & Pickle 2002); use equal-area tiles or hexes when each unit is one legislator or district. Joins, crosswalks, MAUP and spatial dependence: `geospatial.md` and `scripts/spatial_audit.py`.
- **Pass criterion (fix before running):** no colour extreme or ranking driven by small denominators; class breaks stated.
- **Failure signature:** the darkest units are the least populated; large rural districts dominate a per-member map.
- **Source:** Gelman & Price (1999); Brewer & Pickle (2002); Correll, Moritz & Heer (2018).

## 3. Checklist

| ID | Check | Class | Runs with |
|---|---|---|---|
| VIZ-01 | Start every bar and area encoding at zero; report any non-zero baseline. | PRESENTATION | §2.1 |
| VIZ-02 | Replace dual y-axes with aligned panels or indexed series. | PRESENTATION | §2.1 |
| VIZ-03 | Label log axes with base and zero handling; keep compared panels on common limits. | PRESENTATION | §2.1 |
| VIZ-04 | Check aspect ratio and axis range (at least 1 SD for standardized effects) before judging a slope. | PRESENTATION | §2.1 |
| VIZ-05 | Match palette type to data; reject rainbow and jet for ordered values; give missing values their own labelled colour. | PRESENTATION | §2.2 |
| VIZ-06 | Pair every colour distinction with a second cue (marker, label, pattern). | PRESENTATION | §2.2 |
| VIZ-07 | Show an interval with every displayed estimate, named with n and unit of replication. | PRESENTATION | §2.3 |
| VIZ-08 | Use prediction intervals where readers judge outcomes; never use CI overlap as a test. | STATISTICAL | §2.3 |
| VIZ-09 | Pair each printed regression with a coefficient plot that uses the robust intervals. | PRESENTATION | §2.3, `scripts/regression_report.R` |
| VIZ-10 | Check forecast-band coverage out of sample. | STATISTICAL | §2.3, `scripts/backtest_eval.py` |
| VIZ-11 | Run a lineup before claiming a trend is visible. | STATISTICAL | §2.3 |
| VIZ-12 | Compare every plotted curve with raw model output; flag running maxima, caps, smoothing, winsorizing. | COMPUTATIONAL | §2.4 |
| VIZ-13 | Point validation checks at raw output and prove they can fail. | COMPUTATIONAL | §2.4, `scripts/mutation_check.py` |
| VIZ-14 | Count nonzero values that display as zero at the display precision. | PRESENTATION | §2.5 |
| VIZ-15 | Reconcile displayed totals to source; never total rounded parts. | PRESENTATION | §2.5 |
| VIZ-16 | Use one documented rounding rule across backend, front end and exports; test half-way cases. | COMPUTATIONAL | §2.5, §2.9 |
| VIZ-17 | Report how many units sit within ε of each tier boundary. | PRESENTATION | §2.5 |
| VIZ-18 | Name the tie rule for every rank and percentile rank; prove ranks unchanged after a row shuffle. | COMPUTATIONAL | §2.6 |
| VIZ-19 | Show rank intervals or pairwise probabilities wherever ranks are displayed. | STATISTICAL | §2.6, `scripts/mc_error.py` |
| VIZ-20 | Build a label-vs-computation row for every displayed metric and recompute by a second path. | MEASUREMENT | §2.7 |
| VIZ-21 | State per-capita vs total, nominal vs real (deflator, base year) and stock vs flow for every money metric. | MEASUREMENT | §2.7 |
| VIZ-22 | Flag any performance metric computed from the model's own predictions. | DECISION | §2.7 |
| VIZ-23 | Sum only additive quantities; pool rates from numerators and denominators. | PRESENTATION | §2.8 |
| VIZ-24 | Show tier cut points in units; never split ties across tiers; disclose collapsed tiers. | PRESENTATION | §2.8 |
| VIZ-25 | Use one named quantile definition across implementations. | COMPUTATIONAL | §2.8 |
| VIZ-26 | Diff the front end against the model on a golden fixture with edge cases; justify every expected mutant survivor. | COMPUTATIONAL | §2.9, `automation.md` §2.7, `scripts/mutation_check.py` |
| VIZ-27 | Classify every surface as descriptive or advisory; strip advisory wording from descriptive ones. | DECISION | §2.10 |
| VIZ-28 | Register every advisory surface as a model with a validation record. | DECISION | §2.10, `regulatory.md` |
| VIZ-29 | Keep one registry of reported numbers; reconcile values, units, n and denominators across sections. | PRESENTATION | §2.11 |
| VIZ-30 | Recompute p from t and df, and run GRIM on reported means of integer data. | PRESENTATION | §2.11 |
| VIZ-31 | Map shrunken or uncertainty-coded estimates, not raw small-area rates. | STATISTICAL | §2.12, `geospatial.md` |

## 4. Pitfalls and anti-patterns

- A clean-looking dashboard whose checks read the display layer: every monotonicity or range check on clamped data passes by construction.
- Bars that do not start at zero; axes auto-fitted so every wiggle looks large; dual axes.
- Rainbow colour maps for ordered data; missing values coloured as the minimum.
- Point estimates without intervals; SE bars chosen because they look tight; CI overlap treated as a test.
- Coefficient intervals shown where readers need the range of outcomes.
- Mixed rounding rules across Python, R, JavaScript and spreadsheets; formatting numbers before summing them.
- Percentile ranks taken from a sort index; ties broken by row order.
- League tables of noisy rates; "rank 1" treated as a finding.
- Labels that say one unit while the code computes another; nominal money presented as growth; totals mapped as if they were rates.
- "Total" rows of medians, rates, percentiles or ranks; averages of percentages.
- Quartile badges read as absolute levels; identical units in different tiers.
- A front-end port that copied constants once and was never re-synced.
- Advisory verbs, orderings or colours on a descriptive surface.
- Narrative numbers typed by hand into a report and never re-checked against the run.
- Leaving uncertainty out because it makes the figure look busy (Hullman 2020).
- Interactive hover as the only way to read values; provide a static table too.

## 5. References

Verified entries only. Most come from the research bibliography of 2026-09-29/30 (css.md, CrossRef or OpenAlex); entries marked † were verified for this file against CrossRef (2026-09-30; titles and authors matched). "(correction notice)" means CrossRef records a correction or erratum for the work (checked 2026-09-30): read it before quoting details.

- Belia, S., Fidler, F., Williams, J., Cumming, G. (2005). Researchers misunderstand confidence intervals and standard error bars. *Psychological Methods* 10(4):389–396. doi:10.1037/1082-989x.10.4.389
- † Borland, D., Taylor, R. M., II (2007). Rainbow color map (still) considered harmful. *IEEE Computer Graphics and Applications* 27(2):14–17. doi:10.1109/MCG.2007.323435
- Brewer, C. A., Pickle, L. (2002). Evaluation of methods for classifying epidemiological data on choropleth maps in series. *Annals of the Association of American Geographers* 92(4):662–681. doi:10.1111/1467-8306.00310
- † Brown, N. J. L., Heathers, J. A. J. (2017; online 2016). The GRIM test. *Social Psychological and Personality Science* 8(4):363–369. doi:10.1177/1948550616673876
- Buja, A., Cook, D., Hofmann, H., et al. (2009). Statistical inference for exploratory data analysis and model diagnostics. *Phil. Trans. R. Soc. A* 367(1906):4361–4383. doi:10.1098/rsta.2009.0120
- Cleveland, W. S., McGill, R. (1984). Graphical perception: theory, experimentation, and application to the development of graphical methods. *JASA* 79(387):531–554. doi:10.1080/01621459.1984.10478080
- † Cleveland, W. S., McGill, M. E., McGill, R. (1988). The shape parameter of a two-variable graph. *JASA* 83(402):289–300. doi:10.1080/01621459.1988.10478598
- Correll, M., Bertini, E., Franconeri, S. (2020). Truncating the y-axis: threat or menace? *CHI 2020*:1–12. doi:10.1145/3313831.3376222
- Correll, M., Gleicher, M. (2014). Error bars considered harmful: exploring alternate encodings for mean and error. *IEEE TVCG* 20(12):2142–2151. doi:10.1109/tvcg.2014.2346298
- Correll, M., Moritz, D., Heer, J. (2018). Value-suppressing uncertainty palettes. *CHI 2018*:1–11. doi:10.1145/3173574.3174216
- † Crameri, F., Shephard, G. E., Heron, P. J. (2020). The misuse of colour in science communication. *Nature Communications* 11:5444. doi:10.1038/s41467-020-19160-7
- Cumming, G., Finch, S. (2005). Inference by eye: confidence intervals and how to read pictures of data. *American Psychologist* 60(2):170–180. doi:10.1037/0003-066x.60.2.170
- Fernandes, M., Walls, L., Munson, S., Hullman, J., Kay, M. (2018). Uncertainty displays using quantile dotplots or CDFs improve transit decision-making. *CHI 2018*:1–12. doi:10.1145/3173574.3173718
- Gelman, A., Pasarica, C., Dodhia, R. (2002). Let's practice what we preach: turning tables into graphs. *American Statistician* 56(2):121–130. doi:10.1198/000313002317572790
- Gelman, A., Price, P. N. (1999). All maps of parameter estimates are misleading. *Statistics in Medicine* 18(23):3221–3234. doi:10.1002/(sici)1097-0258(19991215)18:23<3221::aid-sim312>3.0.co;2-m
- † Goldstein, H., Spiegelhalter, D. J. (1996). League tables and their limitations: statistical issues in comparisons of institutional performance. *JRSS-A* 159(3):385. doi:10.2307/2983325
- † Hall, P., Miller, H. (2009). Using the bootstrap to quantify the authority of an empirical ranking. *Annals of Statistics* 37(6B). doi:10.1214/09-AOS699
- † Harrower, M., Brewer, C. A. (2003). ColorBrewer.org: an online tool for selecting colour schemes for maps. *Cartographic Journal* 40(1):27–37. doi:10.1179/000870403235002042
- Heer, J., Bostock, M. (2010). Crowdsourcing graphical perception: using Mechanical Turk to assess visualization design. *CHI 2010*:203–212. doi:10.1145/1753326.1753357
- Hofman, J. M., Goldstein, D. G., Hullman, J. (2020). How visualizing inferential uncertainty can mislead readers about treatment effects in scientific results. *CHI 2020*:1–12. doi:10.1145/3313831.3376454
- Hullman, J. (2020). Why authors don't visualize uncertainty. *IEEE TVCG* 26(1):130–139. doi:10.1109/tvcg.2019.2934287
- Hullman, J., Resnick, P., Adar, E. (2015). Hypothetical outcome plots outperform error bars and violin plots for inferences about reliability of variable ordering. *PLOS ONE* 10(11):e0142444. doi:10.1371/journal.pone.0142444
- † Hyndman, R. J., Fan, Y. (1996). Sample quantiles in statistical packages. *American Statistician* 50(4):361–365. doi:10.1080/00031305.1996.10473566
- † IEEE (2019). IEEE Standard for Floating-Point Arithmetic (IEEE Std 754-2019). doi:10.1109/IEEESTD.2019.8766229
- † Isenberg, P., Bezerianos, A., Dragicevic, P., Fekete, J.-D. (2011). A study on dual-scale data charts. *IEEE TVCG* 17(12):2469–2478. doi:10.1109/TVCG.2011.160
- Kale, A., Nguyen, F., Kay, M., Hullman, J. (2019). Hypothetical outcome plots help untrained observers judge trends in ambiguous data. *IEEE TVCG* 25(1):892–902. doi:10.1109/tvcg.2018.2864909
- Kastellec, J. P., Leoni, E. L. (2007). Using graphs instead of tables in political science. *Perspectives on Politics* 5(4). doi:10.1017/s1537592707072209
- Kay, M., Kola, T., Hullman, J. R., Munson, S. A. (2016). When (ish) is my bus? User-centered visualizations of uncertainty in everyday, mobile predictive systems. *CHI 2016*:5092–5103. doi:10.1145/2858036.2858558
- † Marshall, E. C., Sanderson, C., Spiegelhalter, D. J., McKee, M. (1998). Reliability of league tables of in vitro fertilisation clinics: retrospective analysis of live birth rates. *BMJ* 316(7146):1701–1705. doi:10.1136/bmj.316.7146.1701
- † Menge, D. N. L., et al. (2018). Logarithmic scales in ecological data presentation may cause misinterpretation. *Nature Ecology & Evolution* 2(9):1393–1402. doi:10.1038/s41559-018-0610-7
- † Nuijten, M. B., Hartgerink, C. H. J., van Assen, M. A. L. M., Epskamp, S., Wicherts, J. M. (2016; online 2015). The prevalence of statistical reporting errors in psychology (1985–2013). *Behavior Research Methods* 48(4):1205–1226. doi:10.3758/s13428-015-0664-2
- † Nuñez, J. R., Anderton, C. R., Renslow, R. S. (2018). Optimizing colormaps with consideration for color vision deficiency to enable accurate interpretation of scientific data. *PLOS ONE* 13(7):e0199239. doi:10.1371/journal.pone.0199239
- Padilla, L., Kay, M., Hullman, J. (2021). Uncertainty visualization. *Wiley StatsRef: Statistics Reference Online*:1–18. doi:10.1002/9781118445112.stat08296
- Pandey, A. V., Rall, K., Satterthwaite, M. L., Nov, O., Bertini, E. (2015). How deceptive are deceptive visualizations? An empirical analysis of common distortion techniques. *CHI 2015*:1469–1478. doi:10.1145/2702123.2702608
- † Rougier, N. P., Droettboom, M., Bourne, P. E. (2014). Ten simple rules for better figures. *PLOS Computational Biology* 10(9):e1003833. doi:10.1371/journal.pcbi.1003833
- Schenker, N., Gentleman, J. F. (2001). On judging the significance of differences by examining the overlap between confidence intervals. *American Statistician* 55(3):182–186. doi:10.1198/000313001317097960
- † Spiegelhalter, D. J. (2005; online 2004). Funnel plots for comparing institutional performance. *Statistics in Medicine* 24(8):1185–1202. doi:10.1002/sim.1970
- † Weissgerber, T. L., Milic, N. M., Winham, S. J., Garovic, V. D. (2015). Beyond bar and line graphs: time for a new data presentation paradigm. *PLOS Biology* 13(4):e1002128. doi:10.1371/journal.pbio.1002128
- Wickham, H., Cook, D., Hofmann, H., Buja, A. (2010). Graphical inference for infovis. *IEEE TVCG* 16(6):973–979. doi:10.1109/tvcg.2010.161
- Witt, J. K. (2019). Graph construction: an empirical investigation on setting the range of the y-axis. *Meta-Psychology* 3. doi:10.15626/mp.2018.895
- † Wong, B. (2011). Points of view: color blindness. *Nature Methods* 8(6):441. doi:10.1038/nmeth.1618 (correction notice)

**UNVERIFIED (not cited):** Britton, Fisher & Whitley (1998) on the Bank of England fan chart has no CrossRef record, and OpenAlex was rate-limited on 2026-09-30. The WCAG 2.2 thresholds in §2.2 come from K-Dense scientific-visualization (checked there 2026-07-23) and were not re-verified here.

**Adapted from** (K-Dense-AI/scientific-agent-skills; the paths are inside that repository, not this skill; ideas paraphrased, no prose or code copied): `scientific-visualization/SKILL.md`, `scientific-visualization/references/publication_guidelines.md` and `scientific-visualization/references/color_palettes.md` (MIT); `uncertainty-and-units/references/reporting-rules.md` (SD vs SE vs CI in figures, round only at reporting; MIT); `market-research-reports/references/data_analysis_patterns.md` (measurement contract, nominal vs real, double counting; MIT); `scientific-writing/scripts/check_consistency.py` (cross-section consistency registry, as an idea only; MIT); `peer-review/SKILL.md` (figures and tables checked for denominators, units, axes; MIT); `exploratory-data-analysis/SKILL.md` (missing, zero and excluded kept distinct; MIT).
