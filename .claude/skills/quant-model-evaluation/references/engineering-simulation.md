# Engineering and simulation — quant-model-evaluation reference

> **Load when:** auditing a simulation or Monte-Carlo engine (network cascades, agent-based or discrete-event models, scenario engines), a sensitivity analysis, a fitted curve whose constants may not be identified, an optimizer or budget allocator, a closed-form derivation, or any check that might be unable to fail. **Not for:** regression and inference diagnostics (`core-statistics.md`); legal caps, spend-response curves and the money semantics of allocators (`finance.md`); learning cascade parameters from data, homophily versus contagion (`social-science.md`); pipelines, run-to-run determinism and parity between implementations (`automation.md`); near-optimal allocation sets and batch artifacts (`multi-omics-transfer.md`); the legal or supervisory status of any standard (`regulatory.md`).
> Facts marked (as of DATE) are time-sensitive; re-verify before relying on them.

**Vocabulary** (ASME VVUQ 1 usage). *Code verification*: the code solves its stated equations or rules correctly, shown on cases with known answers. *Solution verification*: the numerical error of a particular run (Monte-Carlo noise, step size, tolerance, iteration cap) is estimated and small enough. *Validation*: outputs agree with real outcomes, to a stated accuracy, over the intended domain of use. *UQ*: the spread of outputs caused by uncertain inputs, parameters and model form. *MCSE*: Monte-Carlo standard error, the spread of a simulated estimate across reruns with fresh random numbers. *CRN*: common random numbers, the same draws reused across scenarios so their difference is less noisy. Verification says nothing about validation, and a reproducible run is not a valid model. A KILLED printed by a script is a candidate until a second independent reader confirms it (SKILL.md hard rule 5).

## 1. Assumption map

| Assumption (class) | Where it usually hides | What breaks if it is false | Tests |
|---|---|---|---|
| The code implements the documented model (COMPUTATIONAL) | engine kernels; hand-written ports; handling of probabilities 0 and 1, empty sets, ties | every downstream number | 2.2; SIM-04..06 |
| Model form is adequate for the intended use (FUNCTIONAL-FORM) | cascade or threshold rules, saturation curves, update order | decisions rest on an unvalidated mechanism | 2.3; SIM-07, SIM-08 |
| A scenario contrast is an effect in the world (CAUSAL) | reports that turn "the simulation moves X" into "doing A causes X" | overclaiming | 2.3; `social-science.md` |
| Monte-Carlo error is small next to the gaps that drive decisions (COMPUTATIONAL) | a replication constant chosen for speed; a sufficiency check run once | rankings, knees and allocations are noise | 2.4, 2.6; `scripts/mc_error.py` |
| Replications are independent and streams separate (STATISTICAL) | one global seed, shared generators, draws taken inside branches | MCSE understated; CRN silently broken | 2.5 |
| Warm-up and run length are adequate (STATISTICAL) | steady-state numbers from short or single runs | biased estimates, false precision | 2.5 |
| Uncalibrated constants do not drive the decision (FUNCTIONAL-FORM) | hand-set dials, literature-shaped constants, thresholds | the decision is an artifact of an arbitrary number | 2.7; `scripts/global_sensitivity.py` |
| Fitted parameters are identified by the data (STATISTICAL) | saturation constants, edge probabilities, weights fitted on few outcomes | a prior presented as an estimate | 2.8 |
| The optimizer returns the optimum of the stated problem (DECISION) | greedy or lazy-greedy loops, heuristics, early stopping, coarse increments | allocations off the optimum; guarantees claimed out of scope | 2.9, 2.10 |
| Objective, constraints and units are coherent (DECISION) | sums of non-additive terms, caps, gates, increments | the optimizer answers a different question | 2.10; `finance.md` |
| Displayed curves are the computed curves (PRESENTATION) | running-max clamps, smoothing, rounding; knee rules run on display data | bugs hidden; checks vacuous | 2.11 |
| Numerical gates hold (COMPUTATIONAL) | solver status ignored; conservation never checked | silent non-convergence | 2.12 |
| Closed forms are right (FUNCTIONAL-FORM) | derivative or inverse formulas typed into code | wrong marginals, wrong allocation | 2.13 |
| Checks can fail (COMPUTATIONAL) | audits that read post-processed outputs; wide tolerances | false assurance | 2.14; `scripts/mutation_check.py` |
| Validation evidence is current (COMPUTATIONAL) | one-off sufficiency or validation runs; model changed since | stale assurance | 2.4; SIM-12; `automation.md` |

## 2. Tests

### 2.1 Keep verification, validation and UQ apart, and record credibility
- **Tests:** whether each engine has separate evidence for code verification, solution verification, validation and UQ, and whether the rigor matches the decision it feeds.
- **Assumptions of the test itself:** the intended use and the decision are written down; without them no accuracy requirement exists.
- **Run it:** one row per engine: intended use; criticality (T1-T3); acceptance criteria; assumptions and limits; permissible uses; data pedigree; domain of verification; domain of validation; UQ method; sensitivity coverage; run warnings. Set rigor by model risk, the output's influence on the decision times the consequence of a wrong decision (V&V 40 logic). Rate NASA-STD-7009B's capability factors (data pedigree, verification, validation, development review, development management) and results factors (use against permissible use, input pedigree, uncertainty characterization, results robustness, technical review, process management). The standard sets no required levels; it requires that levels be assessed and reported, and that decision-makers be warned when acceptance criteria are unmet, limits are breached or runs raised warnings. Keep Monte-Carlo, parameter, structural, validation-discrepancy and scenario uncertainty apart: a replication interval covers only the first. Carry the ratings into the SKILL.md credibility table.
- **Pass criterion (fix before running):** every T1 engine has distinct evidence for each V&V activity, a stated domain of validation, and a current use inside that domain.
- **Failure signature:** "all tests pass" offered as validation; "validated" claimed from reproducibility; use outside the calibrated domain (a new legislative session, a new budget scale) with no warning attached.
- **Source:** ASME VVUQ standards page; NASA-STD-7009B; Oberkampf & Roy (2010); Roy & Oberkampf (2011). Status (as of 2026-09-29, re-verify before relying): V&V 10-2019 reaffirmed 2025, V&V 20-2009 reaffirmed 2021, V&V 40-2018 reaffirmation unverified, VVUQ 1-2022 current, NASA-STD-7009B approved 2024-03-05; status and applicability live in `regulatory.md`.

### 2.2 Code verification with known answers
- **Tests:** whether the engine reproduces answers computed another way.
- **Assumptions of the test itself:** the reference answer comes from hand calculation, enumeration or a second implementation, never from the code under audit.
- **Run it:** degenerate and extreme-condition cases for a cascade engine: edge probability 0 gives spread equal to the seed set; probability 1 gives the reachable set (breadth-first search); an empty graph; one seed on a path or star. Metamorphic relations: relabeling nodes or shuffling input rows leaves the output distribution unchanged; monitoring on or off gives identical results. Conservation: dollars in = allocated + unallocated; probabilities sum to 1. On small graphs the exact expected spread comes from enumerating live-edge graphs (Kempe et al. 2003). Running the engine is owner-gated (`RUNS-SYSTEM`).
  ```python
  import itertools, math
  def exact_ic_spread(edges, p, seeds, n):
      """Exact expected Independent-Cascade spread by enumerating live-edge graphs (<= ~16 edges)."""
      total = 0.0
      for live in itertools.product((0, 1), repeat=len(edges)):
          w = math.prod(pi if b else 1 - pi for pi, b in zip(p, live))
          adj = {u: [] for u in range(n)}
          for (u, v), b in zip(edges, live):
              if b: adj[u].append(v)
          seen, stack = set(seeds), list(seeds)
          while stack:
              for v in adj[stack.pop()]:
                  if v not in seen: seen.add(v); stack.append(v)
          total += w * len(seen)
      return total
  print(exact_ic_spread([(0, 1), (1, 2), (2, 3)], [0.5] * 3, [0], 4))   # 1.875 = 1 + .5 + .25 + .125
  ```
- **Pass criterion (fix before running):** degenerate cases exact; each analytic case within 3 MCSE of the engine's mean; metamorphic relations hold.
- **Failure signature:** bias beyond 3 MCSE; probability 1 not reaching the reachable set; output changes with row order; a conservation residual nobody can explain.
- **Source:** Sargent (2013); Roache (2002) for the manufactured-solution pattern; Chen et al. (2019) for metamorphic relations; Kempe, Kleinberg & Tardos (2003).

### 2.3 Validation against observed outcomes
- **Tests:** whether outputs agree with reality well enough for the intended use (Sargent's operational validity), on top of data validity and conceptual-model validity.
- **Assumptions of the test itself:** holdout outcomes set no parameter; the comparison metric matches the decision (ranks for ranking decisions, calibration for probabilities).
- **Run it:** in order of strength: predictive validation on outcomes that arrived after the model was frozen; historical comparison on a holdout period; model-to-model comparison with an accepted or simpler model; face validity from experts (weakest, never alone). Check internal validity too: outputs that swing widely across replications mean the model's own noise may swamp the signal (quantify in 2.4). Compare error E = S − D (simulated minus observed) with validation uncertainty u_val = sqrt(u_num² + u_input² + u_D²) (V&V 20 logic): within about 2·u_val the data cannot separate model error from uncertainty; beyond it, the model-form error is roughly E ± 2·u_val. Probability outputs: `scripts/calibration_report.py`; forecasts: `scripts/backtest_eval.py`. For an old versus a new engine, or two implementations, test equivalence at a pre-stated margin (two one-sided tests), never "no significant difference".
- **Pass criterion (fix before running):** accuracy requirement stated in the decision's units before the comparison; holdout untouched by calibration.
- **Failure signature:** face validity only; validation on the calibration period; a prospective outcome test armed and never scored; "the simulation shows A causes B" (a scenario contrast is conditional on the encoded assumptions; causal wording needs a design, see `social-science.md`).
- **Source:** Sargent (2013); Sargent & Balci (2017); ASME V&V 20 via the VVUQ page; Oberkampf & Roy (2010).

### 2.4 Monte-Carlo standard error, convergence and runs needed
- **Tests:** whether the replication count gives the precision the decision needs.
- **Assumptions of the test itself:** replications are independent (2.5). For one long autocorrelated run use batch means or an autocorrelation-adjusted effective sample size (ESS), not s/√R.
- **Run it:** `python scripts/mc_error.py --data reps.csv --rep rep --target-rel 0.01` (wide: one row per replication, one column per metric; name the replication-id column with `--rep`, or it is analyzed as a metric), or long format: `python scripts/mc_error.py --data reps_long.csv --rep rep --metric metric --value value --target-se 0.05 --batch 20`. It reports MCSE three ways (iid, batch means, ESS-adjusted); the precision verdict uses the iid MCSE, switching to the ESS-adjusted one for any column whose replications fail the Ljung-Box test (`--lb-lags`, default automatic). It also gives the replications needed for the target and a running-mean table, and marks replications WOUNDED when they are autocorrelated or drift between the first 10% and the last 50% (the drift check is UNVERIFIED-HERE below `--drift-min-reps`, default 20). Fewer than 10 replications (`--min-reps`) is UNVERIFIED-HERE. A column identical in every replication (range within `--degenerate-rtol`, default 1e-12) is MC-DEGENERATE, WOUNDED: the model is deterministic or the seed never reached it, and that column's precision check is UNVERIFIED-HERE. The former `--min-ess-ratio` flag was removed. By hand: MCSE = s/√R; for a proportion sqrt(p(1 − p)/R); runs needed R* = (s / target_se)²; with autocorrelation MCSE = s/√ESS, where ESS = R/(1 + 2Σρ_k) with the sum truncated by Geyer's initial-sequence rule (Geyer 1992).
- **Pass criterion (fix before running):** MCSE at or below a target derived from the decision, for example a quarter of the smallest gap that would change it; running mean flat over the last half of replications.
- **Failure signature:** a replication count chosen for speed (tens of runs) whose MCSE is comparable to the differences interpreted; no MCSE reported; a sufficiency check run once and never repeated after the model changed.
- **Source:** Morris, White & Crowther (2019); Koehler, Brown & Haneuse (2009); Schmeiser (1982); Law & Kelton (1984); Geyer (1992).

### 2.5 Seeds, streams, replications and common random numbers
- **Tests:** whether replications are independent and reproducible, and whether compared scenarios are correctly paired.
- **Assumptions of the test itself:** the generator and version are recorded; streams are separated by construction (spawned or jumped). Distinct hash-derived seeds give reproducibility, not proven independence.
- **Run it:** give each replication a child seed and each stochastic source its own stream within it; store the seed manifest. For CRN, make each draw depend only on (replication, source, item): draw one uniform per candidate edge or unit and decide by comparison (u < p), so changing p or the seed set moves no other draw. Draw for every candidate first and filter afterwards; drawing only for filtered items shifts the stream. Analyze paired differences.
  ```python
  import numpy as np
  p_a = np.array([0.30, 0.30, 0.50]); p_b = p_a + 0.03       # two scenarios over three edges
  root = np.random.SeedSequence(20260930)                     # record in the seed manifest
  diffs = []
  for child in root.spawn(1000):                              # one child seed per replication
      edge_ss, _other_ss = child.spawn(2)                     # one stream per stochastic source
      u = np.random.default_rng(edge_ss).random(p_a.size)     # one uniform per edge, every edge
      diffs.append(int((u < p_b).sum()) - int((u < p_a).sum()))   # same u in both: CRN
  print(np.mean(diffs), np.std(diffs, ddof=1) / np.sqrt(len(diffs)))   # swap in your engine's output
  ```
  A terminating model (to election day, to cycle end) needs identical initial conditions across replications. A steady-state estimate needs a declared warm-up deletion, run length well beyond the warm-up, and independent replications; never build a confidence interval from observations inside one run.
- **Pass criterion (fix before running):** Var(A − B) under CRN well below Var(A) + Var(B) (report the ratio); seed manifest present; per-replication results stored.
- **Failure signature:** one global seed shared with unrelated code; CRN claimed but paired correlation near zero; draws taken inside conditionals; an interval computed from one run's entities.
- **Source:** L'Ecuyer (2015); Glasserman & Yao (1992); Law & Kelton (1984); Hoad, Robinson & Davies (2010).

### 2.6 Decision gaps against Monte-Carlo noise; rank and seed stability
- **Tests:** whether the decision (the chosen plan, the top-K list, the knee of a frontier) survives fresh random numbers.
- **Assumptions of the test itself:** replications are exchangeable; the decision is recomputed identically on each resample.
- **Run it:** paired plans: `python scripts/mc_error.py --data reps.csv --rep rep --compare planA,planB` (is the gap larger than z·MCSE of the paired difference, with CRN-aware covariance?). Rankings: `python scripts/mc_error.py --data reps_long.csv --rep rep --entity target --score spread --topk 10 --min-stability 0.9` (probability the top-K set is unchanged across bootstrap resamples of replications, the Kendall tau distribution, and the paired gap between the K-th and (K+1)-th entity; below `--kill-below`, default 0.5, it prints KILLED because the seed, not the model, sets the list, a candidate until a second independent reader confirms it; add `--smaller-better` when lower scores win). Seeds: rerun under three or more master seeds (owner-gated) and compare the decision, not only the mean. Fix the smallest decision-relevant gap δ first (the indifference zone), then choose replications so that 2·MCSE of the difference is below δ.
- **Pass criterion (fix before running):** gap above 2 MCSE of the difference and top-K stability of at least 0.9 (the script defaults; state yours in advance).
- **Failure signature:** the knee or argmax moves across seeds; top-list seed overlap reported without MCSE (overlap can be complete while the knee moves); frontier points closer together than their noise.
- **Source:** Kim & Nelson (2001); Hall & Miller (2009); Morris, White & Crowther (2019).

### 2.7 Sensitivity ladder: one-at-a-time, Morris, Sobol, by parameter status
- **Tests:** which uncertain inputs drive the output and the decision, and whether those inputs were ever calibrated.
- **Assumptions of the test itself:** each parameter's range or distribution is defensible and written before the run; the analyzed output is the decision (rank overlap, dollars to a target, knee location), not only a score.
- **Run it:** classify each parameter as **ratified** by the owner, **literature-shaped** (borrowed, not fitted), **fitted**, or **arbitrary**. One-at-a-time tornado sweeps are a first screen only: they miss interactions and cover a vanishing share of the space as dimension grows (Saltelli et al. 2019). Morris elementary effects (mu*, sigma) screen k parameters in r(k + 1) runs; Sobol first-order S1 and total ST quantify importance and interaction in N(k + 2) runs (Saltelli et al. 2010 design; Jansen estimator for ST). The script never runs your model: design, then the owner runs the model, then analysis.
  ```
  python scripts/global_sensitivity.py --problem problem.json --method morris --design-only --N 50
  # owner runs the model once per design.csv row; outputs.csv keeps the run_id column (or the row order)
  python scripts/global_sensitivity.py --problem problem.json --method morris --design design.csv --outputs outputs.csv --output-col topk_overlap
  python scripts/global_sensitivity.py --problem problem.json --method sobol --design-only --N 1024
  ```
  `problem.json` is `{"names": [...], "bounds": [[lo, hi], ...], "status": [...]}` with optional `dists` and `nominal`; status values are `ratified`, `literature`, `fitted`, `arbitrary`. With SALib installed, its analyzers and the script's numpy estimators run as two paths that must agree within `--path-tol` (GSA-PATH, default 1e-6); without it numpy runs alone; the report says which. Design mode adds GSA-DESIGN: the design is regenerated from the same `--seed` and must be byte-identical. Analysis adds GSA-R (Morris: at least `--min-trajectories`, default 10), GSA-PREC (Sobol: ST half-widths within `--max-conf`) and GSA-CONSIST (S1 ≤ ST, and the sum of S1 at most `--max-sum-s1`, default 1.1). An influential parameter with no status comes back UNVERIFIED-HERE. Keep dependent parameters (weights that must sum to one) inside the model and sample only the free ones; unknown problem keys are listed as ignored.
- **Pass criterion (fix before running):** no arbitrary or literature-shaped parameter has importance above 0.1 on a decision output (ST for Sobol, share of mu* for Morris, swing share for one-at-a-time; the script's `--st-threshold` default, applied to the statuses in `--uncalibrated-status`, default `arbitrary,literature`); bootstrap intervals exclude zero for every index you call important.
- **Failure signature:** only ±10% sweeps around one point; S1 summing far below 1 with interactions never examined; a "calibrated" constant with no calibration artifact among the top drivers.
- **Source:** Morris (1991); Campolongo, Cariboni & Saltelli (2007); Sobol′ (2001); Saltelli (2002); Saltelli et al. (2010); Jansen (1999); Saltelli et al. (2019); Herman & Usher (2017).

### 2.8 Identifiability by profile likelihood
- **Tests:** whether the data pin down a fitted parameter, or the optimizer returned an arbitrary point on a flat ridge.
- **Assumptions of the test itself:** the likelihood or loss is the one used in fitting; the grid spans the plausible range; the chi-square cut-off is asymptotic.
- **Run it:** fix the parameter at each grid value, refit the others, accept values with 2·(NLL_profile − NLL_min) ≤ 3.84 (95%, 1 df). Planted negative control: refit without the observations that should identify it; the profile must go flat.
  ```python
  import numpy as np
  from scipy.optimize import minimize
  def profile(nll, theta_hat, j, grid):
      """Profile a negative log-likelihood over parameter j, refitting the others at each value."""
      theta_hat = np.asarray(theta_hat, float)
      free = [k for k in range(theta_hat.size) if k != j]
      rows = []
      for g in grid:
          def f(z):
              t = theta_hat.copy(); t[free] = z; t[j] = g
              return nll(t)
          r = minimize(f, theta_hat[free], method="Nelder-Mead")
          rows.append((g, r.fun, r.success))      # a failed refit is unknown, not excluded
      return rows
  ```
- **Pass criterion (fix before running):** the accepted region is bracketed inside the bounds on both sides; if any profile point beats the original fit, refit before reporting.
- **Failure signature:** a flat profile (the constant is a prior; show decisions across its range); an interval edge on an imposed bound (constraint-limited, not data-determined); "the residual is small" offered as identification.
- **Source:** Raue et al. (2009); adapted from K-Dense `13c-metabolic-flux`.

### 2.9 Which optimality guarantee applies
- **Tests:** whether the guarantee claimed for an optimizer holds for this objective and constraint.
- **Assumptions of the test itself:** the objective's structure (separable, concave, submodular) is read from the code, not the documentation.
- **Run it:** match the case.

  | Objective and constraint | What greedy delivers |
  |---|---|
  | Separable, concave in each target (non-increasing marginal returns), one budget, integer increments | exactly optimal (Fox 1966) |
  | Monotone submodular set function, choose k items | at least (1 − 1/e) ≈ 63% of the optimum's value above the empty set (Nemhauser et al. 1978); expected spread under IC, and under LT with random thresholds, qualifies (Kempe et al. 2003) |
  | Same, objective estimated by Monte Carlo | (1 − 1/e − ε), with ε shrinking as replications grow (Kempe et al. 2003) |
  | Submodular with item costs (knapsack budget) | benefit-per-cost greedy alone has no constant guarantee; the better of it and unit-cost greedy reaches ½(1 − 1/e) (Leskovec et al. 2007) |
  | Deterministic thresholds, S-curves, competitive or conversion dynamics | no general guarantee (unless a result for that specific model applies, e.g. follower IC against fixed opponent seeds; cite it only after verification); greedy is a heuristic, check it with 2.10 |

  Lazy (CELF-style) evaluation equals plain greedy only when marginals truly shrink; with noisy estimates it can bury an item whose earlier estimate came out low by chance, so evaluate with CRN. For monotone submodular f, report the data-dependent bound OPT ≤ f(S) + (sum of the k largest marginal gains over S) (Leskovec et al. 2007).
- **Pass criterion (fix before running):** the printed guarantee matches a row whose conditions were checked in code (for example, concavity of every per-target curve over its whole range).
- **Failure signature:** "(1 − 1/e)-optimal" printed for a threshold or competitive model; a certificate printed while a modeled conversion is reachable; robustness to misspecified parameters never examined (He & Kempe 2018).
- **Source:** Fox (1966); Nemhauser, Wolsey & Fisher (1978); Kempe, Kleinberg & Tardos (2003); Leskovec et al. (2007); He & Kempe (2018).

### 2.10 Canonical recipe `allocation_check`: swap gap, exact optimum, near-optimal ranges
- **Tests:** whether the reported allocation is optimal for the allocator's own separable objective, how far short it falls, and which targets' amounts the objective actually determines. This is the recipe's one home; `finance.md` §2.6.1 and `multi-omics-transfer.md` §2.8 point here.
- **Assumptions of the test itself:** the objective is a sum of per-target values; `gains` reproduces what the allocator maximizes (same gates, imputations, caps; k counts its increments) and is tabulated once, with CRN when the model is stochastic. Non-separable objectives (cascades) need enumeration of small instances instead.
- **Run it:** three answers from one table. The swap gap is the discrete KKT check: at an optimum of a separable concave objective no one-increment transfer between targets helps (continuous analogue: equal marginal return per dollar across interior targets, higher at a cap, lower when unfunded; Boyd & Vandenberghe 2004). The exact curve is the dynamic-programming optimum at every budget, for comparison with the plan and with any published frontier. With `tol`, each target gets its near-optimal range (the flux-variability idea, `multi-omics-transfer.md` §2.8); take tol = max(1% of the optimum, 2 MCSE), as in `finance.md` §2.6.1.
  ```python
  import math
  import numpy as np
  def allocation_check(gains, alloc, budget, tol=None):
      """gains[i][k]: the model's value for target i holding k increments (k = 0..cap_i), tabulated
      once. alloc[i]: increments the allocator gave i. budget: increments available. Any separable
      objective; tol (objective units) adds near-optimal ranges."""
      g = [np.asarray(t, float) for t in gains]
      def exact(tables):                  # best[b]: exact max of sum_i t_i[k_i] with sum_i k_i <= b
          best = np.zeros(budget + 1)
          for t in tables:
              new = np.full(budget + 1, -np.inf)
              for k in range(min(len(t) - 1, budget) + 1):
                  new[k:] = np.maximum(new[k:], best[: budget + 1 - k] + t[k])
              best = new
          return best
      up = [t[a + 1] - t[a] if a + 1 < len(t) else -np.inf for t, a in zip(g, alloc)]
      down = [t[a] - t[a - 1] if a > 0 else np.inf for t, a in zip(g, alloc)]
      curve = exact(g)
      out = {"swap_gap": max(up) - min(down),                                  # <= 0: no single move helps
             "shortfall": curve[budget] - sum(t[a] for t, a in zip(g, alloc)),  # > 0: a better plan exists
             "exact_curve": curve}                                             # exact V(b), b = 0..budget
      if tol is not None:                 # per target: increments that keep the plan within tol
          out["ranges"] = []
          for i, t in enumerate(g):
              rest = exact(g[:i] + g[i + 1:])
              ok = [k for k in range(min(len(t) - 1, budget) + 1) if rest[budget - k] + t[k] >= curve[budget] - tol]
              out["ranges"].append((min(ok), max(ok)))                         # the set may have gaps
      return out
  # planted failure: small concave gains vs a target that pays only after five increments (a threshold)
  gains = [[0.3 * (1 - math.exp(-k)) for k in range(11)], [1.0 if k >= 5 else 0.0 for k in range(11)]]
  r = allocation_check(gains, alloc=[5, 0], budget=5)                          # [5, 0] is greedy's plan
  print(round(r["swap_gap"], 4), round(r["shortfall"], 3))                    # -0.0022 0.702
  ```
  The planted case is worth running once: greedy's plan scores 0.30 against an exact 1.00, yet the swap gap reports no helpful move. The swap test cannot see threshold jumps; the exact curve, or a guarantee from 2.9, covers them. For a deterministic allocator no MCSE applies: tabulate gains from a replica or the model's exported arrays, and derive tolerances from the exported precision first (jitter the rounded inputs within their rounding; a bar tighter than that spread cannot be met).
- **Pass criterion (fix before running):** swap gap ≤ 0 within tolerance (1e-9 relative when deterministic, 2 MCSE of the gain difference when simulated); shortfall within the stated guarantee (zero for separable concave); no published frontier point below the exact curve beyond tolerance; every target reported as essential has a range that excludes zero.
- **Failure signature:** a positive swap gap (money should move); a shortfall on a small instance; a frontier below the exact curve; `gains` built without a gate or cap the allocator applies; an "essential" target whose range runs from zero to its cap.
- **Source:** Fox (1966); Boyd & Vandenberghe (2004); what each dollar legally is: `finance.md`.

### 2.11 Frontiers, knees and clamped displays
- **Tests:** whether a budget frontier V(B) is computed rather than cosmetically repaired, and whether its knee belongs to the model rather than to noise.
- **Assumptions of the test itself:** raw, pre-display values are readable; each frontier point carries an MCSE.
- **Run it:** the best achievable value cannot fall as budget rises when money may stay unspent, so a raw dip is Monte-Carlo noise or a bug. Check `np.all(np.diff(raw) >= -2 * mcse[1:])` on the raw path and `np.max(np.abs(display - raw))` against the display. A running max (`np.maximum.accumulate`) or smoothing must be disclosed, and no check or knee rule may read the displayed series. Re-derive the knee under several seeds and plausible constants (2.6, 2.7). Multi-objective optimizers (needs pymoo or similar): fix seeds, keep the convergence history, filter to zero constraint violation, normalize objectives before choosing a point, and compare with a known front on a benchmark or an exact small instance.
- **Pass criterion (fix before running):** raw path monotone within 2 MCSE; display equal to raw or its transformation disclosed; knee stable across seeds within the budget step.
- **Failure signature:** a monotonicity audit reading the clamped path (it cannot fail, 2.14); a knee that moves between seeds by more than one budget step; a Pareto "front" from one unseeded run.
- **Source:** Blank & Deb (2020); adapted from K-Dense `pymoo`; display honesty: `data-visualization.md`.

### 2.12 Numerical acceptance gate
- **Tests:** whether a run is numerically trustworthy before anyone interprets it.
- **Assumptions of the test itself:** the numerical controls (replications, step, tolerance, iteration cap, grid) can change without changing the model.
- **Run it:** refine each control on its own (double replications, halve the tolerance or step) and require the reported observable to move less than its tolerance. Check and record conservation and budget residuals (money, probability mass, counts). Read solver status and convergence flags (`res.success`, `res.status`, warnings) instead of trusting the absence of an exception. Record every run warning; NASA-STD-7009B requires that decision-makers hear about them. Floating-point totals depend on summation order: reconcile with `math.fsum` (Goldberg 1991).
- **Pass criterion (fix before running):** refinement changes and residuals below stated tolerances; zero unexamined solver warnings.
- **Failure signature:** "converged" asserted from parameter values or a smooth plot; optimizer warnings suppressed; the third significant figure moving when replications double.
- **Source:** adapted from K-Dense `fluidsim` (scientific acceptance gate); Oberkampf & Roy (2010); Goldberg (1991).

### 2.13 Symbolic verification of closed forms
- **Tests:** whether a derivative, inverse or limit typed into the code matches the documented curve.
- **Assumptions of the test itself:** the documented curve is the intended one; a simplification to zero is proof, while a nonzero residue may only mean the simplifier gave up (then check numerically).
- **Run it:** (needs sympy; fallback below uses numpy)
  ```python
  import numpy as np, sympy as sp
  x, h = sp.symbols("x h", positive=True)
  curve = x / (x + h)                          # documented response curve
  claimed = h / (x + h)**2                     # marginal return as coded
  assert sp.simplify(sp.diff(curve, x) - claimed) == 0        # solve and verify: difference is 0
  xs = np.linspace(1e3, 1e6, 200); hv = 5e4; e = 1e-4 * xs    # fallback: central differences
  num = ((xs + e) / (xs + e + hv) - (xs - e) / (xs - e + hv)) / (2 * e)
  assert np.allclose(num, hv / (xs + hv)**2, rtol=1e-6)
  ```
  Also check limits (x → 0, x → ∞) and the signs of the first and second derivatives against the claimed shape.
- **Pass criterion (fix before running):** the difference simplifies to zero, or numeric agreement within 1e-6 relative over the operating range.
- **Failure signature:** a marginal formula off by a factor or a sign; a "concave" curve whose second derivative changes sign inside the operating range.
- **Source:** Meurer et al. (2017); adapted from K-Dense `sympy` (solve and verify).

### 2.14 Vacuous checks: prove a check can fail
- **Tests:** whether an audit check detects the fault it is named for.
- **Assumptions of the test itself:** each mutant violates the property the check claims to test; an equivalent mutant (property intact) is not a blind spot.
- **Run it:** feed the check planted faults and count kills. `scripts/mutation_check.py` gives the command a copy, always named `input.csv` or `input.json` inside its run folder: first a byte-for-byte copy, then an identity re-serialization (both must pass, or nothing can be concluded), then each mutant. Automatic CSV mutations, per numeric column: shuffle, sort, flip the sign, set to the median, 10% NaN; plus dropping and duplicating 10% of rows and swapping adjacent columns (labelled `a<->b`). JSON numeric arrays: reverse, swap two adjacent values (a monotone series becomes non-monotone), scale by 10, zero out, delete the key. A mutant whose parsed values equal the control's is EQUIVALENT and not counted. Name mutants the check cannot catch by design in `--expect-survive NAME[,NAME]` (an op, an op:target such as `swap:b<->gap`, or a mutant id): if they pass they are EXPECTED-SURVIVOR and excluded from the verdict. A run past `--timeout` has its whole process tree killed and is listed, not counted.
  ```
  python scripts/mutation_check.py --input frontier.json --auto --expect-survive scale,zero --cmd python check_frontier.py '{input}'
  python scripts/mutation_check.py --input gap.csv --auto --expect-survive "drop_rows,dup_rows,swap:b<->gap" --cmd python check_rowwise.py '{input}'
  python scripts/mutation_check.py --input reps.csv --mutations spec.json --pass-codes 0 --timeout 120 --cmd python check_reps.py '{input}'
  ```
  Quote `'{input}'` (PowerShell reads bare braces as a script block) and any name holding `<->`. In the second line, a row-wise identity check of gap = a − b cannot see whole rows dropped or duplicated, and swapping b with gap keeps the identity true.
  **Warning:** the script executes the command you give it, once per mutant plus two controls, with your rights. Never aim it at code whose import executes it, or at the pipeline itself: copy the check's predicate into a scratch script that reads `{input}` and imports nothing from the audited repository. A check that reads fixed paths and ignores `{input}` survives every mutant, which yields a false "vacuous" verdict. A `.bat`, `.cmd` or `.ps1` program, or the cmd, powershell or pwsh shells, is refused unless `--allow-shell-script`.
- **Pass criterion (fix before running):** the unmodified copy and the identity control pass; every counted mutant that breaks the named property is killed; each survivor is either declared in `--expect-survive` with the reason recorded or listed as a blind spot. Read kills per property-breaking mutant: a crash on a deleted key is a kill that says nothing about the property.
- **Failure signature:** zero counted kills, printed as KILLED ("vacuous check"), a candidate until a second independent reader confirms it; a monotonicity check surviving the reversed and swapped-neighbor mutants because it reads a running-max display, its only "kill" a crash on the deleted key; a check that exits 0 when its input is missing.
- **Source:** DeMillo, Lipton & Sayward (1978); Jia & Harman (2011); Barr et al. (2015).

### 2.15 Documentation a second team can rebuild from: ODD, TRACE, STRESS
- **Tests:** whether the simulation is described well enough to re-implement and to judge.
- **Assumptions of the test itself:** re-implementation from the description alone is the standard; code comments are not a description.
- **Run it:** ODD (2020 update): purpose and patterns; entities, state variables and scales; process overview and scheduling; design concepts, including stochasticity and observation; initialization; input data; submodels. TRACE: problem formulation, model description, data evaluation, conceptual model evaluation, implementation verification, model output verification, model analysis, model output corroboration. STRESS: reporting checklists for discrete-event (STRESS-DES), agent-based (STRESS-ABS) and system-dynamics (STRESS-SD) studies, covering objectives, logic, data, experimentation, implementation and code access. Give the ODD to someone who has not seen the code and ask for the update order, the random draws and the stopping rule.
- **Pass criterion (fix before running):** every ODD element present; scheduling (synchronous or asynchronous updates, tie-breaking) stated; a TRACE file with implementation verification and corroboration against independent data.
- **Failure signature:** parameters documented only in code; update order unstated (it changes cascade outcomes); stochastic elements undocumented.
- **Source:** Grimm et al. (2006, 2010, 2014, 2020); Schmolke et al. (2010); Ayllón et al. (2021); Monks et al. (2019).

## 3. Checklist

- **SIM-01** Write each engine's intended use, tier and acceptance criteria before testing it. `DECISION` · 2.1
- **SIM-02** Keep code-verification, solution-verification and validation evidence in separate records. `COMPUTATIONAL` · 2.1
- **SIM-03** Set rigor by influence times consequence; rate the NASA-STD-7009B capability and results factors. `DECISION` · 2.1
- **SIM-04** Run degenerate and extreme cases: probability 0 and 1, empty and one-node graphs, zero budget, budget above every cap. `COMPUTATIONAL` · 2.2
- **SIM-05** Compare the engine with exact answers on small instances; require agreement within 3 MCSE. `COMPUTATIONAL` · 2.2
- **SIM-06** Test metamorphic relations: relabeling, row order and monitoring must not change results. `COMPUTATIONAL` · 2.2
- **SIM-07** Validate on outcomes the model never saw, in the decision's units, against a requirement stated first. `FUNCTIONAL-FORM` · 2.3
- **SIM-08** Report comparison error against validation uncertainty, not a bare correlation. `FUNCTIONAL-FORM` · 2.3
- **SIM-09** Word scenario contrasts as conditional on the model's assumptions; send causal claims to `social-science.md`. `CAUSAL` · 2.3
- **SIM-10** Report MCSE for every simulated number that is shown or ranked. `COMPUTATIONAL` · 2.4, `scripts/mc_error.py`
- **SIM-11** Derive the replication count from a precision target tied to the smallest decision-relevant gap. `COMPUTATIONAL` · 2.4
- **SIM-12** Re-run Monte-Carlo sufficiency and validation after any change to mechanics, inputs or constants; date the last run. `COMPUTATIONAL` · 2.4
- **SIM-13** Use independent replications with spawned per-source streams and a stored seed manifest. `STATISTICAL` · 2.5
- **SIM-14** Align draws by (replication, source, item) when comparing scenarios; report the CRN variance ratio. `STATISTICAL` · 2.5
- **SIM-15** Declare terminating or steady-state design, warm-up and run length; never build an interval from one run. `STATISTICAL` · 2.5
- **SIM-16** Test every decision (top-K, argmax, knee) across bootstrap resamples and at least three master seeds. `DECISION` · 2.6
- **SIM-17** Require each decision gap to exceed 2 MCSE of the paired difference. `DECISION` · 2.6, `scripts/mc_error.py --compare`
- **SIM-18** Classify every constant as ratified, literature-shaped, fitted or arbitrary in the model card. `FUNCTIONAL-FORM` · 2.7
- **SIM-19** Screen with Morris and quantify with Sobol on decision outputs; flag uncalibrated parameters whose importance (ST or mu* share) exceeds 0.1. `FUNCTIONAL-FORM` · 2.7, `scripts/global_sensitivity.py`
- **SIM-20** Profile every fitted constant that drives a decision; report flat or bound-limited profiles as priors. `STATISTICAL` · 2.8
- **SIM-21** Name the optimality guarantee and verify its conditions (concavity, submodularity, constraint type) in code. `DECISION` · 2.9
- **SIM-22** Run `allocation_check` at the reported allocation, built with the allocator's own gates, caps and increments; report swap gap and shortfall. `DECISION` · 2.10
- **SIM-23** Compare every published frontier point with the exact curve; enumerate small instances when the objective is not separable. `DECISION` · 2.10
- **SIM-24** Plant a threshold response and confirm the verification catches the greedy failure. `DECISION` · 2.10
- **SIM-25** Read raw, pre-display values for every frontier or curve; disclose clamps and smoothing. `PRESENTATION` · 2.11
- **SIM-26** Refine replications, tolerance and step one at a time; check conservation residuals and solver status. `COMPUTATIONAL` · 2.12
- **SIM-27** Verify coded derivatives, inverses and limits symbolically or by finite differences. `FUNCTIONAL-FORM` · 2.13
- **SIM-28** Prove each audit check can fail using planted faults, declaring by-design survivors with `--expect-survive`, on scratch copies of owner-approved checks only. `COMPUTATIONAL` · 2.14, `scripts/mutation_check.py`
- **SIM-29** Document each engine in ODD with a TRACE file; test re-implementation from the ODD alone. `COMPUTATIONAL` · 2.15
- **SIM-30** Attach a warning to any output used outside its validated domain or produced with run warnings. `PRESENTATION` · 2.1, 2.12

## 4. Pitfalls and anti-patterns

- A passing test suite offered as validation. Tests show the code does what it says; only outcome comparisons show the model is right.
- A replication count set once for speed and inherited by every later version of the model.
- Top-list seed overlap reported as "stable" with no MCSE; the list can match while the knee moves.
- CRN announced but broken: draws taken only for filtered items or inside branches, so streams drift apart.
- One-at-a-time ±10% sweeps presented as a sensitivity analysis.
- Hand-chosen constants later called "fitted" or "from the literature". A paper cited for a mechanism never validates a local number.
- (1 − 1/e) claimed for greedy on a threshold, S-curve or competitive model.
- Allocations computed against separate per-topic budgets summed as if they were one plan against one budget.
- Monotonicity or concavity checks that read a clamped display, which makes them vacuous by construction.
- Knee rules run on display data, or on curves whose points sit within noise of each other.
- Tripwire thresholds relaxed step by step after each failure until the check passes (see `automation.md`).
- Scenario contrasts reported with causal verbs.
- Numerical warnings suppressed to keep logs clean.

## 5. References

- ASME. Verification, Validation and Uncertainty Quantification standards (V&V 10, V&V 20, V&V 40, VVUQ 1). https://www.asme.org/codes-standards/publications-information/verification-validation-uncertainty (status as of 2026-09-29; see `regulatory.md`).
- Ayllón, D., Railsback, S. F., Gallagher, C., et al. (2021). Keeping modelling notebooks with TRACE: Good for you and good for environmental research and management support. *Environmental Modelling & Software* 136, 104932. DOI: 10.1016/j.envsoft.2020.104932
- Barr, E. T., Harman, M., McMinn, P., et al. (2015). The Oracle Problem in Software Testing: A Survey. *IEEE Transactions on Software Engineering* 41(5), 507-525. DOI: 10.1109/tse.2014.2372785
- Blank, J., & Deb, K. (2020). Pymoo: Multi-Objective Optimization in Python. *IEEE Access* 8, 89497-89509. DOI: 10.1109/access.2020.2990567
- Boyd, S., & Vandenberghe, L. (2004). *Convex Optimization*. Cambridge University Press. DOI: 10.1017/cbo9780511804441
- Campolongo, F., Cariboni, J., & Saltelli, A. (2007). An effective screening design for sensitivity analysis of large models. *Environmental Modelling & Software* 22(10), 1509-1518. DOI: 10.1016/j.envsoft.2006.10.004
- Chen, T. Y., Kuo, F.-C., Liu, H., et al. (2019). Metamorphic Testing: A Review of Challenges and Opportunities. *ACM Computing Surveys* 51(1), 1-27. DOI: 10.1145/3143561
- DeMillo, R. A., Lipton, R. J., & Sayward, F. G. (1978). Hints on Test Data Selection: Help for the Practicing Programmer. *Computer* 11(4), 34-41. DOI: 10.1109/c-m.1978.218136
- Fox, B. (1966). Discrete Optimization Via Marginal Analysis. *Management Science* 13(3), 210-216. DOI: 10.1287/mnsc.13.3.210
- Geyer, C. J. (1992). Practical Markov Chain Monte Carlo. *Statistical Science* 7(4). DOI: 10.1214/ss/1177011137
- Glasserman, P., & Yao, D. D. (1992). Some Guidelines and Guarantees for Common Random Numbers. *Management Science* 38(6), 884-908. DOI: 10.1287/mnsc.38.6.884
- Goldberg, D. (1991). What every computer scientist should know about floating-point arithmetic. *ACM Computing Surveys* 23(1), 5-48. DOI: 10.1145/103162.103163
- Grimm, V., Berger, U., Bastiansen, F., et al. (2006). A standard protocol for describing individual-based and agent-based models. *Ecological Modelling* 198(1-2), 115-126. DOI: 10.1016/j.ecolmodel.2006.04.023
- Grimm, V., Berger, U., DeAngelis, D. L., et al. (2010). The ODD protocol: A review and first update. *Ecological Modelling* 221(23), 2760-2768. DOI: 10.1016/j.ecolmodel.2010.08.019
- Grimm, V., Augusiak, J., Focks, A., et al. (2014). Towards better modelling and decision support: Documenting model development, testing, and analysis using TRACE. *Ecological Modelling* 280, 129-139. DOI: 10.1016/j.ecolmodel.2014.01.018
- Grimm, V., Railsback, S. F., Vincenot, C. E., et al. (2020). The ODD Protocol for Describing Agent-Based and Other Simulation Models: A Second Update to Improve Clarity, Replication, and Structural Realism. *Journal of Artificial Societies and Social Simulation* 23(2). DOI: 10.18564/jasss.4259
- Hall, P., & Miller, H. (2009). Using the bootstrap to quantify the authority of an empirical ranking. *The Annals of Statistics* 37(6B). DOI: 10.1214/09-aos699
- He, X., & Kempe, D. (2018). Stability and Robustness in Influence Maximization. *ACM Transactions on Knowledge Discovery from Data* 12(6), 1-34. DOI: 10.1145/3233227
- Herman, J., & Usher, W. (2017). SALib: An open-source Python library for Sensitivity Analysis. *The Journal of Open Source Software* 2(9), 97. DOI: 10.21105/joss.00097
- Hoad, K., Robinson, S., & Davies, R. (2010). Automated selection of the number of replications for a discrete-event simulation. *Journal of the Operational Research Society* 61(11), 1632-1644. DOI: 10.1057/jors.2009.121
- Jansen, M. J. W. (1999). Analysis of variance designs for model output. *Computer Physics Communications* 117(1-2), 35-43. DOI: 10.1016/s0010-4655(98)00154-4
- Jia, Y., & Harman, M. (2011). An Analysis and Survey of the Development of Mutation Testing. *IEEE Transactions on Software Engineering* 37(5), 649-678. DOI: 10.1109/tse.2010.62
- Kempe, D., Kleinberg, J., & Tardos, É. (2003). Maximizing the spread of influence through a social network. *Proceedings of the 9th ACM SIGKDD International Conference on Knowledge Discovery and Data Mining*, 137-146. DOI: 10.1145/956750.956769
- Kim, S.-H., & Nelson, B. L. (2001). A fully sequential procedure for indifference-zone selection in simulation. *ACM Transactions on Modeling and Computer Simulation* 11(3), 251-273. DOI: 10.1145/502109.502111
- Koehler, E., Brown, E., & Haneuse, S. J.-P. A. (2009). On the Assessment of Monte Carlo Error in Simulation-Based Statistical Analyses. *The American Statistician* 63(2), 155-162. DOI: 10.1198/tast.2009.0030
- L'Ecuyer, P. (2015). Random number generation with multiple streams for sequential and parallel computing. *2015 Winter Simulation Conference (WSC)*, 31-44. DOI: 10.1109/wsc.2015.7408151
- Law, A. M., & Kelton, W. D. (1984). Confidence Intervals for Steady-State Simulations: I. A Survey of Fixed Sample Size Procedures. *Operations Research* 32(6), 1221-1239. DOI: 10.1287/opre.32.6.1221
- Leskovec, J., Krause, A., Guestrin, C., et al. (2007). Cost-effective outbreak detection in networks. *Proceedings of the 13th ACM SIGKDD International Conference on Knowledge Discovery and Data Mining*, 420-429. DOI: 10.1145/1281192.1281239
- Meurer, A., Smith, C. P., Paprocki, M., et al. (2017). SymPy: symbolic computing in Python. *PeerJ Computer Science* 3, e103. DOI: 10.7717/peerj-cs.103
- Monks, T., Currie, C. S. M., Onggo, B. S., et al. (2019). Strengthening the reporting of empirical simulation studies: Introducing the STRESS guidelines. *Journal of Simulation* 13(1), 55-67. DOI: 10.1080/17477778.2018.1442155
- Morris, M. D. (1991). Factorial Sampling Plans for Preliminary Computational Experiments. *Technometrics* 33(2), 161-174. DOI: 10.1080/00401706.1991.10484804
- Morris, T. P., White, I. R., & Crowther, M. J. (2019). Using simulation studies to evaluate statistical methods. *Statistics in Medicine* 38(11), 2074-2102. DOI: 10.1002/sim.8086
- NASA (2024). NASA-STD-7009B, Standard for Models and Simulations (approved 2024-03-05). https://standards.nasa.gov/sites/default/files/standards/NASA/B/1/NASA-STD-7009B-Final-3-5-2024.pdf (status as of 2026-09-29; see `regulatory.md`).
- Nemhauser, G. L., Wolsey, L. A., & Fisher, M. L. (1978). An analysis of approximations for maximizing submodular set functions—I. *Mathematical Programming* 14(1), 265-294. DOI: 10.1007/bf01588971
- Oberkampf, W. L., & Roy, C. J. (2010). *Verification and Validation in Scientific Computing*. Cambridge University Press. DOI: 10.1017/cbo9780511760396
- Raue, A., Kreutz, C., Maiwald, T., et al. (2009). Structural and practical identifiability analysis of partially observed dynamical models by exploiting the profile likelihood. *Bioinformatics* 25(15), 1923-1929. DOI: 10.1093/bioinformatics/btp358
- Roache, P. J. (2002). Code Verification by the Method of Manufactured Solutions. *Journal of Fluids Engineering* 124(1), 4-10. DOI: 10.1115/1.1436090
- Roy, C. J., & Oberkampf, W. L. (2011). A comprehensive framework for verification, validation, and uncertainty quantification in scientific computing. *Computer Methods in Applied Mechanics and Engineering* 200(25-28), 2131-2144. DOI: 10.1016/j.cma.2011.03.016
- Saltelli, A. (2002). Making best use of model evaluations to compute sensitivity indices. *Computer Physics Communications* 145(2), 280-297. DOI: 10.1016/s0010-4655(02)00280-1
- Saltelli, A., Annoni, P., Azzini, I., et al. (2010). Variance based sensitivity analysis of model output. Design and estimator for the total sensitivity index. *Computer Physics Communications* 181(2), 259-270. DOI: 10.1016/j.cpc.2009.09.018
- Saltelli, A., Aleksankina, K., Becker, W., et al. (2019). Why so many published sensitivity analyses are false: A systematic review of sensitivity analysis practices. *Environmental Modelling & Software* 114, 29-39. DOI: 10.1016/j.envsoft.2019.01.012
- Sargent, R. G. (2013). Verification and validation of simulation models. *Journal of Simulation* 7(1), 12-24. DOI: 10.1057/jos.2012.20
- Sargent, R. G., & Balci, O. (2017). History of verification and validation of simulation models. *2017 Winter Simulation Conference (WSC)*, 292-307. DOI: 10.1109/wsc.2017.8247794
- Schmeiser, B. (1982). Batch Size Effects in the Analysis of Simulation Output. *Operations Research* 30(3), 556-568. DOI: 10.1287/opre.30.3.556
- Schmolke, A., Thorbek, P., DeAngelis, D. L., & Grimm, V. (2010). Ecological models supporting environmental decision making: a strategy for the future. *Trends in Ecology & Evolution* 25(8), 479-486. DOI: 10.1016/j.tree.2010.05.001
- Sobol′, I. M. (2001). Global sensitivity indices for nonlinear mathematical models and their Monte Carlo estimates. *Mathematics and Computers in Simulation* 55(1-3), 271-280. DOI: 10.1016/s0378-4754(00)00270-6

All DOIs were resolved against CrossRef on 2026-09-30 (titles, authors and venues match; no retraction or correction notices); the ODD, TRACE and Sargent entries were also verified in the regulatory research file.

**Adapted from** (ideas paraphrased; no text or code copied): K-Dense `simpy` (references/simulation-methodology.md; MIT), `fluidsim` (SKILL.md, scientific acceptance gate; MIT), `sympy` (SKILL.md, pattern 1: solve and verify; upstream SymPy license), `pymoo` (SKILL.md and references/constraints_mcdm.md; Apache-2.0), `analytical-method-validation` (SKILL.md and references/statistics.md: criteria fixed before data, equivalence testing; MIT), `13c-metabolic-flux` (SKILL.md and references/inference.md: profile statuses, the remove-the-informative-measurement control; MIT).
