---
name: moneyball-proof-and-analysis-toolkit
description: First-principles analysis recipes for building a NEW proof in the Moneyball repo instead of assuming a claim. Load when the task is any of - power studies (is there enough data before an evaluation?), planted-signal batteries as go/no-go gates, split-half reliability (Spearman-Brown), testing whether a correlation beats chance (permutation test), proving a refactor or artifact delta is behavior-neutral (the input-purity byte-match recipe - this skill is its sole owner), determinism / MC-sufficiency (CRN, seed stability), bounding an untested constant (sensitivity sweep), confound controls (gender/party/volume partials), diagnosing a signal-poor vs unlucky stratum, or independently re-deriving a reported number. Does NOT cover the prereg/look lifecycle rules (moneyball-research-methodology), acceptance thresholds and gold-label machinery (moneyball-validation-and-qa), running the SHIPPED diagnostic tools (moneyball-diagnostics-and-tooling), or measurement theory from zero (psychometrics-reference).
---

<!-- PUBLICATION CANDIDATE (local only, not published). Derived from .claude/skills/moneyball-proof-and-analysis-toolkit/SKILL.md at Melange integration 99431fc3c (blob 4eacc0ee). Generic method and engineering content kept; local paths made portable; references to unpublished internal documents marked as such; specific unpublished research outcomes, holds and internal status facts replaced by withheld markers pending the owner's disclosure decision. -->

# Moneyball proof-and-analysis toolkit

This skill is the "prove it, don't just install it" cookbook: ten analysis recipes, each battle-tested in this repo's own history, for turning "I believe X" into "here is the computation that proves X (and here is exactly what it cannot prove)". The repo's core failure modes — silent wrong-numbers, metric artifacts that fake a pass, confounds (gender/party/volume) masquerading as signal, and draws too small to distinguish signal from luck — are all defeated by these recipes, and every one of them has caught a real defect at least once. Each recipe states WHAT IT PROVES and WHAT IT CANNOT PROVE, gives steps and a code sketch, and cites the commit/prereg/report where it was used for real. Use it whenever you are about to claim a number is real, a change is safe, or an evaluation is worth running.

## When NOT to use this skill

- You need the **rules** of the prereg/look/one-look discipline (when a look is allowed, what a lock is, retirement vocabulary) → `moneyball-research-methodology`. This skill gives you the math *inside* those rules.
- You need **engineering QA**: what counts as evidence for shipping code, how to add tests/audit checks, gold-label machinery → `moneyball-validation-and-qa`.
- You want to **run an existing shipped diagnostic** and interpret its output → `moneyball-diagnostics-and-tooling` (owns the tool catalog; this skill owns the underlying recipes so you can build a NEW one).
- You need measurement theory taught from zero (what reliability/validity/halo mean) → `psychometrics-reference`.
- You hit a live failure and need triage → `moneyball-debugging-playbook`.
- You want the history of which investigations already died → `moneyball-failure-archaeology`.

## Quick reference

| # | Recipe | One-line purpose | Worked example (real usage) |
|---|--------|------------------|------------------------------|
| 1 | Power study | Can this N detect the effect at all? Run BEFORE the evaluation | [withheld pending owner disclosure decision: round-4 power-study outcome] |
| 2 | Plant/battery | Synthetic go/no-go gate: machinery must recover planted signal, refuse null+confound | `fec/members/b5_n_matrix.py` `simulate_battery()`; the orthogonalization lesson (internal preregistration addendum, not published) |
| 3 | Split-half + Spearman-Brown | Is a measure stable enough to use? | `fec/members/coop_v2_candidate.py` `sb()`; [withheld pending owner disclosure decision: reliability values of internal measures] |
| 4 | Permutation-significance gate | Does the observed r beat chance at this N? | [withheld pending owner disclosure decision: audio pilot result] |
| 5 | Input-purity byte-match | Prove an artifact delta came from inputs, not code | Gate (d) forensics (internal audit record, not published) |
| 6 | CRN / determinism / MC-sufficiency | Same seed ⇒ same bytes; MC=20 budget is enough | `fec/engine/mc_stability_check.py`; `fec/tests/run_tests.py` sm64 block |
| 7 | Sensitivity bounding | An untested constant cannot have changed decisions | `fec/members/receptivity_sensitivity.py` (.18 scale, 0.60 retiring factor) |
| 8 | Confound attack | Does the signal survive gender/party/volume controls? | [withheld pending owner disclosure decision: emotional-stability confound result] |
| 9 | Stratum signal-poverty diagnostic | Is this subset genuinely signal-poor, or was the draw unlucky? | [withheld pending owner disclosure decision: round-5 stratum diagnostic result] |
| 10 | Adversarial re-derivation | Independently recompute a reported number before trusting it | [withheld pending owner disclosure decision: shrinkage-artifact retraction]; fresh-seed re-derivation clause |

## Safety preamble (read before running anything)

- **Import == execution** for nearly every `fec/*.py`; most write artifacts at import time. `fec/paths.py:7-8` sets ROOT to `MONEYBALL_ROOT` when set, else to the parent of the imported paths.py, so a script run from a git worktree targets that worktree's EMPTY data plane; with `MONEYBALL_ROOT` pointed at LIVE, writes DO land in LIVE. `fec/tests/run_tests.py` resolves its own root from `__file__` (`:8`) and ignores `MONEYBALL_ROOT`, although the kernel it imports reads through `paths.py` (`fec/moneyball_core.py:16`). See `moneyball-change-control` law 7. (Corrected 2026-09-30; verified against `fec/paths.py:7-8`.) Only `fec/tests/run_tests.py` and `fec/audit/audit_full.py` are safe to run casually.
- Build NEW analysis scripts in your scratchpad directory, not in `fec/`. Read live artifacts read-only (`json.load(open(...))`, sqlite `PRAGMA query_only=1`).
- Even "simulate" modes can write: `b5_n_matrix.py --simulate` featurizes, which updates `b5_empath_cache.json` on the live tree (`fec/members/b5_behavioral_instrument.py:52-67`). Warm caches make this a no-op in practice, but do not assume zero-write.
- Check for the owner's live jobs (running python processes, fresh artifact mtimes) before any baseline; run baselines serially (session-ratified, 2026-07).
- All commands below assume the working directory is the repository root (the live tree; repo paths can contain spaces, always quote).

Vocabulary used throughout (full treatment in `psychometrics-reference` and `moneyball-research-methodology`):
- **r** — Pearson correlation, −1..+1; the repo's standard effect measure.
- **z-score** — a value rescaled to (x − mean)/std so different measures are comparable.
- **OOF (out-of-fold)** — predictions for each row made by a model that never trained on that row (5-fold cross-validation); the repo's standard honest prediction vector (`fec/members/b5_behavioral_instrument.py:113-118`).
- **Prereg / look** — a pre-registration is a committed contract fixing method+bars before data is seen; the "look" is the single permitted evaluation against it.
- **Criterion** — the behavioral ground-truth variable a model is validated against (e.g. `reactivity_z`).

---

## Recipe 1 — Power study (before committing to an evaluation)

**Proves:** whether the current sample size can RELIABLY detect a signal of the size you honestly expect — using synthetic data only, so no real result is ever seen.
**Cannot prove:** that the real signal exists, or its size. It only tells you whether looking would be a measurement or a coin flip.

**When:** before locking any evaluation with a magnitude bar (e.g. r ≥ +0.15) on a sample under ~300; whenever a battery run (Recipe 2) fails marginally; before spending a one-look.

**Steps:**
1. Fix the constructor: plant a synthetic criterion with a known true correlation (the honest expected effect size — in this repo r=.40 is the standard "realistic strong signal") into the REAL feature matrix, using the same plant machinery as the battery (Recipe 2).
2. Sweep sample size n (subsample real rows) × true r, with ~5 independent seeds per cell.
3. For each cell, run the FULL evaluation machinery (OOF prediction, all bars) and record the pass rate and the spread of recovered r.
4. Read: the smallest n where the true-r=.40 cell passes ~5/5 is your reliability threshold. Below it, do not look — gate the route on data instead.

**Rule of thumb** (derived empirically in an internal pilot; its preregistration is not published): the noise floor of a correlation at sample size N is r_crit ≈ 1.645/√N (one-sided 95%). At N=40 that is ≈ .26; at N=80 ≈ .18; at N=201 ≈ .117. If your expected effect sits at or below the floor, the design is underpowered no matter what feature engineering you do.

**Code sketch** (standalone, scratchpad):
```python
import numpy as np
# X = real feature matrix (n_total x k), oof = the evaluation's own OOF function
for n in (150, 200, 250, 300, 400):
    passes = []
    for seed in (9001, 9002, 9003, 9004, 9005):
        rng = np.random.default_rng(seed)
        rows = rng.choice(len(X), n, replace=False)
        sig = zz(X[rows] @ rng.standard_normal(X.shape[1]))          # signal that lives in X
        y = 0.4*sig + np.sqrt(1-0.4**2)*rng.standard_normal(n)       # true r = .40 by construction
        pred = oof(X[rows], y)
        passes.append(np.corrcoef(pred, y)[0,1] >= 0.15)             # your locked bar
    print(n, sum(passes), '/5')
```

[withheld pending owner disclosure decision: round-4 power-study outcome and retirement]

---

## Recipe 2 — Plant/battery construction (synthetic go/no-go gate)

**Proves:** that the evaluation MACHINERY works — it recovers a known planted signal, returns nothing on a destroyed pairing, refuses a confound-only signal, and admits a true signal that coexists with confounds. A green battery licenses the real evaluation; a red battery refuses it without consuming anything.
**Cannot prove:** anything about the real data. Battery outcomes ground no claim (the round-4/5 preregs state this explicitly).

**The four pinned parts** (the current standard, `fec/members/b5_n_matrix.py:148-211`, seeds pinned in the internal preregistration, not published):
- **(a) PLANTED** (seed 424242): synthetic criteria with true r≈.4 built FROM the real feature matrix — machinery must recover them (core ≥4/5; the hot-seat leg must clear its bars).
- **(b) NULL** (seed 535353): the REAL criteria permuted before pairing (pairing destroyed) — must yield 0 passes. Calibrates the p-values at the true subset size.
- **(c) CONFOUND-ONLY** (seed 646464): a synthetic criterion driven by gender/party/volume alone — the magnitude bars MAY pass (text encodes demographics) but the gating confound partial (Recipe 8) MUST refuse it.
- **(d) TRUE+CONFOUND** (seed 757575): planted signal PLUS additive confound loadings — the confound partial MUST admit it (proves the gate is not so strict it kills true positives).

**The orthogonalization lesson — orthogonalize plants in signal space.** [withheld pending owner disclosure decision: round-4 battery run-1 failure figures] Fix, scoped to sim(a) only: sequential Gram–Schmidt orthogonalization of the planted signal components (`fec/members/b5_n_matrix.py:128-146` `plant_set()`; internal preregistration addendum, not published). Bars, seeds, and consequences were untouched — amending machinery validation pre-look is legitimate; amending bars is not.

**Battery refusal ≠ MISS.** When the battery fails, the look is REFUSED, not consumed: no RESULT exists, no closure is recorded, the route is "neither validated nor closed" — RETIRED WITHOUT A LOOK, reopening gated on a pinned condition. Calling it "failed" is a mis-claim. [withheld pending owner disclosure decision: retirement status of rounds 4 and 5]

**Code sketch** — the orthogonalized constructor (adapt `plant_set()`; do not reinvent):
```python
S = []
for _ in TRAITS:                                # distinct-by-construction signals
    s = zz(X @ rng.standard_normal(X.shape[1]))
    for s0 in S: s = s - np.corrcoef(s, s0)[0,1]*s0   # Gram-Schmidt vs prior plants
    S.append(zz(s))
y = {t: 0.4*S[i] + np.sqrt(1-0.16)*rng.standard_normal(len(X)) for i,t in enumerate(TRAITS)}
```
(An earlier, simpler design — disjoint 20-category weight blocks, seed 11 — lives in `fec/members/b5_behavioral_instrument.py:158-178` `simulate()`; the orthogonalized `plant_set` is the current standard for anything matrix-shaped.)

**How to read output:** each part prints OK/FAIL and a one-line verdict `SIMULATE BATTERY: ALL GREEN` or `!! FAILURE — look forbidden`. Any FAIL = stop; diagnose whether it is a sim-design artifact (fix the sim, not the bars) or genuine insufficiency (run Recipe 1, then Recipe 9).

**Worked examples:** [withheld pending owner disclosure decision: rounds 4-5 battery outcomes and retirements] Status check that never risks a look: `python "fec\members\b5_n_matrix.py"` with no args prints lock/look/fingerprint state only.

---

## Recipe 3 — Split-half reliability + Spearman-Brown

**Proves:** that a measure is STABLE — two random halves of its own evidence agree with each other. Unreliable measures cap every downstream correlation (see attenuation below), so this is the first number to compute for any new disposition/criterion.
**Cannot prove:** that the measure captures the intended construct (validity), or that it is free of confounds. A perfectly reliable volume counter is still just a volume counter.

**Method:**
1. Split each member's underlying evidence (bills joined, interview turns, partners) into two halves. Half-construction must be STABLE and arbitrary-but-fixed: odd/even rows in a deterministic file order (`fec/members/coop_v2_candidate.py:87-90`), or an md5 hash of the partner name mod 2 (`fec/members/coop_v2_candidate.py:99` — note the in-code warning: Python's builtin `hash()` is salted per process, so NEVER use it for halving; use `hashlib.md5`).
2. Compute the statistic per half, correlate the halves across members: r_half.
3. Spearman-Brown correction (a half is noisier than the whole; SB estimates full-length reliability): **SB = 2·r_half / (1 + r_half)** (`fec/members/coop_v2_candidate.py:125-128`).
4. Enforce minimum evidence per half (the repo uses ≥5 rows or ≥3 partners per half) and report n.

**House calibration** (anchored to repo cases, not an external standard): SB ≥ .80 = solid criterion-grade; ~.40–.60 = real but modest, usable only WITH graded shrinkage toward neutral for thin coverage; ≤ ~.10 = situational noise, reject. [withheld pending owner disclosure decision: the internal measures and reliability values that anchor these bands]

**Attenuation honesty:** a criterion with reliability SB caps observed correlations at ≈ √SB × the other side's ceiling. [withheld pending owner disclosure decision: round-4 pre-look attenuation figures]

**The adversarial-re-derivation standard:** a reliability number is not trusted as reported — a second, independently coded computation must reproduce it (Recipe 10). [withheld pending owner disclosure decision: dependability-audit findings on internal reliability reporting]

---

## Recipe 4 — Permutation-significance gates

**Proves:** that an observed correlation exceeds what THIS machinery on THIS sample size produces by chance — an empirical null distribution, immune to parametric assumptions and to n<<p optimism.
**Cannot prove:** causation, confound-freedom (Recipe 8), or that the effect will replicate on new data.

**The house method** (`fec/members/b5_behavioral_instrument.py:120-129` `exact_perm_p()`): hold the OOF prediction vector FIXED, permute the criterion labels K=5000 times (seed 20260708 — pinned, deliberately never varied across rounds), recompute r each time, and report **p = (#null ≥ observed + 1) / (K + 1)**, one-sided r>0. The +1s make p exact (never zero). The parametric t-test p is printed beside it as a cross-check only. For partial correlations, permute the RESIDUALIZED criterion against the fixed residualized prediction (`fec/members/b5_n_matrix.py:84-90`, seed 20260710).

**Critical design point:** the null must be generated through the SAME pipeline that produced the observed number (same features, same CV, same N). A null computed on a simplified pipeline understates the floor.

[withheld pending owner disclosure decision: audio pilot worked example (noise floor, refuted fix, result)]

**Lesson to reuse:** when a proposed statistical fix sounds plausible (PCA, feature selection, weighting), TEST it on the null harness before adopting it. Plausible fixes can make the floor worse.

---

## Recipe 5 — Input-purity byte-match (gate-d / refactor-neutrality)

**Proves:** (i) that a post-run artifact delta was caused by changed INPUTS, not changed code; or equivalently (ii) that a refactor is behavior-neutral (same inputs ⇒ byte-identical outputs). As a bonus it is a fixed-point check: byte-match against current inputs ⇒ two-run convergence has settled.
**Cannot prove:** that the outputs are CORRECT — only that the code did not change what it computes.

**Precondition:** the engine must be deterministic (Recipe 6) and the pipeline idempotent. [withheld pending owner disclosure decision: internal pipeline idempotency audit record]

**Steps:**
1. Note the drifted production artifact's md5.
2. Re-run the SAME engine against current on-disk inputs, with output redirected to a temp path so production is not clobbered. The engines have env dials for exactly this: `FRONTIER_OUT` (`fec/engine/budget_frontier.py:152-153`; production default `data\money\budget_frontier.json`), `OPT_OUT` (`fec/engine/optimize.py:33`; production default the root `optimize_result.json`); `fec/audit/audit_full.py:173-176,212` uses them the same way (`_audit_tmp_*.json` in `data\system\audit_scratch\`). (Corrected 2026-09-30; verified against those lines.)
3. md5-compare temp vs production. **Byte-match ⇒ a deterministic pure function reproducing the new artifact proves the delta came from inputs, not the engines.** Mismatch ⇒ real regression (or a live job wrote mid-comparison — check mtimes/processes first).

```powershell
cd "<repository root>"
$env:FRONTIER_OUT = "$env:TEMP\bf_purity.json"     # redirect: engine MUTATES live tree without this
python "fec\engine\budget_frontier.py"
Get-FileHash "$env:TEMP\bf_purity.json", ".\data\money\budget_frontier.json" -Algorithm MD5
Remove-Item Env:FRONTIER_OUT
```
(For refactor-neutrality, run the temp-redirected engine once on the OLD code and once on the NEW code against frozen inputs and byte-compare the two temps.)

[withheld pending owner disclosure decision: internal audit-run input-purity worked example]

---

## Recipe 6 — CRN / determinism / MC-sufficiency verification

**Proves:** (i) determinism: same inputs + same seed ⇒ byte-identical output; (ii) MC-sufficiency: the Monte-Carlo budget (MC=20) is not overfitting seed selection to one particular set of random draws.
**Cannot prove:** that the simulated physics is right — only that its randomness is controlled and its budget adequate.

**Background:** CRN (Common Random Numbers) means every "random" draw is a deterministic hash of its key (`moneyball_core.sm64`), so competing candidates in greedy optimization are always compared under IDENTICAL draws. That kills the independently-noisy-estimate failure mode outright (the Almazaydeh CELF++ result the check is motivated by — `fec/engine/mc_stability_check.py:3-10`). The residual risk is subtler: the picked seed SET could be overfit to one seed's particular 20 cascade realizations.

**Three-layer verification, cheapest first:**
1. **Kernel invariants** — `python "fec\tests\run_tests.py"` runs the WHOLE kernel suite; the sm64 invariants (sm64 in [0,1), deterministic, well-spread, key-independent) are its first block (`fec/tests/run_tests.py:24-29`). Not seconds: [withheld pending owner disclosure decision: internal kernel-suite run duration and pass/fail counts]; trust the run's own tail and check for the owner's live jobs first; exit 1 on failure (`run_tests.py:1187`). (corrected 2026-10-15; verified against `fec/tests/run_tests.py:24-29,1187`.)
2. **Double-run byte-match** — run the engine twice with identical env, temp-redirected outputs (Recipe 5 dials); md5s must be identical. Standard audit gate (internal audit record, not published).
3. **MC-budget stability** — the 100%-overlap method, shipped as `fec/engine/mc_stability_check.py`: rebuild a single-topic frontier under (MC=20,SEED=7 production), (MC=100,SEED=7), (MC=20,SEED=1), (MC=20,SEED=13); compare picked-seed-set Jaccard overlap, identical-prefix length, and spread delta. Interpretation printed by the tool itself: "high set-overlap at MC=100 (same seed) and across RNG seeds ⇒ the MC=20+CRN frontier is NOT overfit to its particular draws; low overlap ⇒ raise the frontier MC budget." [withheld pending owner disclosure decision: internal MC-budget validation record]

**Caution:** `mc_stability_check.py` spawns 4 full frontier builds via subprocess (several minutes, live-tree temp files it removes itself). Never run with production-calibration env dials still set in your shell — defaults ARE the ratified state.

---

## Recipe 7 — Sensitivity bounding of untested constants

**Proves:** that a constant's exact value COULD NOT HAVE CHANGED DECISIONS — sweep it across its plausible range and show the decision surface (who gets targeted) is stable. This is the honest next-best thing when no outcome data exists to test a magnitude.
**Cannot prove:** that the constant's value is correct. A decision-robust constant is safely arbitrary; a decision-sensitive one is the one to take to an outcome test FIRST.

**The shipped template** — `fec/members/receptivity_sensitivity.py` (built 2026-07-04 to answer "the .18 scaling and 0.60 retiring factor are literature-shaped design choices no outcome has ever tested"):
1. **Stage 1, replication gate (mandatory — Recipe 10 inline):** recompute the derived quantities from the artifact's own stored components under BASELINE constants; all 533 stored `pressure_mult`/`seed_prob` values must match exactly, else the sweep formulas have drifted from production and every variant is meaningless (`fec/members/receptivity_sensitivity.py:42-52`, hard `sys.exit(1)` on mismatch).
2. Define the DECISION SURFACE — the thing allocations actually key off (per-member flip-model winnability), not the intermediate multiplier.
3. Sweep each constant over a plausible range (the file's variants: susceptibility scale .18 → .09/.27; prospect-theory 1.15/.92 → mild/strong; retiring 0.60 → .45/.80/1.00-off; persona weight .30 → 0/.45).
4. Score each variant by top-20/top-50 target-set overlap and rank correlation vs baseline. Verdict thresholds as shipped: **ROBUST** ≥18/20 overlap, MODERATE ≥15/20, else **SENSITIVE**.
5. Restore baseline state after the sweep (the file swaps the kernel's receptivity cache in memory and restores it — line 107).

**How to read:** "ROBUST = the constant cannot have changed WHO gets targeted (top-20 stable across its plausible range); SENSITIVE = this constant is the one to outcome-test first" (printed by the tool, lines 119-120). The prospective outcome test the file pre-registers in its docstring (seed_prob vs next-quarter cosponsorships; pressure_mult vs stance movement among actually-engaged members) is the eventual real test — `fec/engine/outcome_snapshot.py` exists to freeze predictions for it. Honesty pattern worth copying: where a sweep does NOT rerun the expensive downstream (cascades), the tool says so in its own output ("gate analytics; cascades not rerun"). Operational update (2026-10-02): use `python fec/engine/outcome_snapshot.py --status` for an outcome-blind check. Legacy no-lock freeze/score calls intentionally refuse. A new prospective route requires committed definition/source pins, a predictor freeze committed before its future window, and a baseline receipt committed before the window ends; see `moneyball-diagnostics-and-tooling`. [withheld pending owner disclosure decision: prospective-outcome route hold status]

**Caution:** the script imports `flip_model`, which executes at import (live-tree reads). It writes nothing, but treat it per the safety preamble.

---

## Recipe 8 — Confound attack (robustness look with pre-declared consequences)

**Proves:** whether a validated signal survives removal of NAMED confounds — the repo's recurring killers are **gender** (voice features encode speaker sex), **party**, and **volume** (how much a member talks/cosponsors). A signal that vanishes under the partial was reading the confound.
**Cannot prove:** that no OTHER confound exists; only the ones you conditioned on are excluded.

**The house method — Frisch–Waugh partial** (`fec/members/b5_n_matrix.py:81-90`): residualize BOTH the prediction and the criterion on the confound set Z (least-squares regression with intercept; keep the residuals), then r_partial = corr(residuals) with a permutation p (Recipe 4, seed 20260710) on the residualized criterion. Reported beside it, non-gating: within-group r (e.g. within each sex separately) — the bluntest possible cross-check.

```python
def resid(v, Z):
    Z1 = np.column_stack([np.ones(len(v)), Z])
    b, *_ = np.linalg.lstsq(Z1, v, rcond=None)
    return v - Z1 @ b
rp, ry = resid(pred, Z), resid(y, Z)      # Z: columns e.g. gender, party, log(1+volume)
r_partial = np.corrcoef(rp, ry)[0, 1]     # + permutation p per Recipe 4
```

[withheld pending owner disclosure decision: project rule on settled results and robustness looks]

[withheld pending owner disclosure decision: emotional-stability gender-confound worked example]

**Make the partial GATING in new evaluations,** not post-hoc: wire the confound partial in as a bar, volume-hardened (the conditioning set includes log-volume), with battery parts (c)/(d) proving the gate both refuses confound-only signal and admits true+confound signal (internal preregistrations, not published). [withheld pending owner disclosure decision: cooperation-measure volume finding]

---

## Recipe 9 — Stratum signal-poverty diagnostic

**Proves:** whether a specific member SUBSET (stratum) carries genuinely less recoverable signal than a random subset of the same size — i.e. distinguishes "this stratum is signal-poor" from "we got an unlucky draw." Synthetic-only, so running it never risks a look.
**Cannot prove:** whether the real effect exists in the stratum; it characterizes recoverability, not truth.

**When:** a battery (Recipe 2) fails on a masked/stratified leg even though the power study (Recipe 1) says the raw n should suffice. The discrepancy means the STRATUM, not the n, is the problem — its members may be more homogeneous in feature space than a random draw.

**Steps:**
1. Take the battery's EXACT plant constructor (same target r, same orthogonalization) — do not build a new one.
2. Run it ≥5 times with fresh seeds ON THE ACTUAL STRATUM rows (not random subsamples).
3. Record the recovered own-r distribution and the per-bar pass count; take the MEDIAN.
4. Compare against the power study's random-roster draws at the same n. Median well below the random-draw median at equal n ⇒ the stratum itself is signal-poor; median comparable but variance huge ⇒ draw luck, and more reps or more data are the answer.
5. Pin the same diagnostic (constructor + seeds) as the route's reopening condition, so "safe to check any time" is literally true.

[withheld pending owner disclosure decision: round-5 stratum diagnostic worked example and gate]

---

## Recipe 10 — Adversarial re-derivation

**Proves:** that a reported number is REPRODUCIBLE by an independent computation — different code path, fresh partitions, or shadow recompute — before it is trusted, cited, or allowed to promote anything.
**Cannot prove:** that the number MEANS what its label claims. The deepest catch in this repo's history was a correctly-computed number on the WRONG metric — so re-derive the metric choice, not just the arithmetic.

**Four house patterns, all live in the repo:**

1. **Re-derive the metric itself.** [withheld pending owner disclosure decision: shrinkage-method artifact and claim retraction] Consequence: **every claimed PASS is adversarially re-derived before it is recorded as real.**

2. **Fresh-seed re-derivation of a pass (fold-partition robustness).** Wire it into the consequence clause: on a bars-pass, recompute ALL model prediction vectors with fresh OOF seeds [101,113,127,139,151] (permutation seeds stay pinned) and the re-derivation must re-clear ALL bars; failure = "FRAGILE = MISS for ALL consequences INCLUDING closure" (`fec/members/b5_n_matrix.py:25,323-332`; internal preregistration, not published). A pass that only exists under one fold partition is not a pass.

3. **Shadow recompute of production numbers.** `fec/engine/compute_pillars.py` (no `--write`) recomputes every rank from inputs via an independent Python path and requires exact agreement with the authority artifact — tail `PARITY: CLEAN` (`fec/engine/compute_pillars.py:106-124`; wired into audit_full). Same pattern at analysis scale: `receptivity_sensitivity.py`'s stage-1 replication gate (Recipe 7) refuses to sweep until 533/533 stored values are reproduced exactly.

4. **Remove analyst degrees of freedom that re-derivation cannot check.** [withheld pending owner disclosure decision: acoustic composite sign finding] If a number depends on a hand choice, the re-derivation must vary that choice or eliminate it.

**Worked example of the standard applied to reporting:** [withheld pending owner disclosure decision: dependability-read reporting defects] The generalizable rule: two independent computations must agree before a number enters a document of record; if you cannot independently recompute it, say so instead of citing it. [withheld pending owner disclosure decision: internal verification-agent calibration finding]

---

## Choosing a recipe (decision table)

| You are about to... | Run first |
|---|---|
| Lock an evaluation on n < 300 | 1 (power), then 2 (battery) |
| Trust a correlation someone reports | 10 (re-derive), then 4 (permutation) |
| Ship a new disposition/criterion | 3 (split-half), then 8 (confound partial) |
| Explain why artifact hashes drifted | 6 (double-run), then 5 (input-purity) |
| Refactor an engine | 5 (byte-match old vs new on frozen inputs) |
| Defend/attack a validated result | 8 — but ONLY as a locked look with pre-declared consequences |
| Explain a marginal battery failure | 1 (power at this n), then 9 (stratum diagnostic) |
| Add a new tuned constant | 7 (sensitivity bound), and log it in `moneyball-config-and-flags` |

## Provenance and maintenance (2026-07-09)

Facts here were verified against the repo on 2026-07-09. Volatile facts and one-line re-verification commands (PowerShell, from the repository root; in a worktree, substitute its root):

- [withheld pending owner disclosure decision: re-verification commands for the round-4 and round-5 results]
- Battery parts/seeds 424242/535353/646464/757575 and `plant_set` orthogonalization:
  `Select-String -Path "fec\members\b5_n_matrix.py" -Pattern "424242|535353|646464|757575|Gram-Schmidt"`
- Fresh-seed re-derivation constant RESEEDS [101,113,127,139,151]:
  `Select-String -Path "fec\members\b5_n_matrix.py" -Pattern "RESEEDS"`
- Spearman-Brown helper and md5 half-hash: `Select-String -Path "fec\members\coop_v2_candidate.py" -Pattern "def sb|md5"`
- Reactivity shrinkage dial: `Select-String -Path "fec\members\behavioral_dispositions.py" -Pattern "REACT_TURNS"`
- exact_perm_p (K=5000, seed 20260708) and OOF seeds [7,17,29,43,61]:
  `Select-String -Path "fec\members\b5_behavioral_instrument.py" -Pattern "20260708|SEEDS = "`
- [withheld pending owner disclosure decision: re-verification command for the audio pilot result]
- Input-purity method + gate-d forensics: in the internal audit record (not published), search "input-purity|byte-for-byte".
- Temp-redirect dials: `Select-String -Path "fec\engine\budget_frontier.py","fec\engine\optimize.py" -Pattern "FRONTIER_OUT|OPT_OUT"`
- MC-stability method + interpretation: `Select-String -Path "fec\engine\mc_stability_check.py" -Pattern "MC=100|Jaccard|NOT overfit"`
- Sensitivity harness replication gate + verdict thresholds: `Select-String -Path "fec\members\receptivity_sensitivity.py" -Pattern "REPLICATION GATE|ROBUST"`
- [withheld pending owner disclosure decision: re-verification commands for the confound, shrinkage and sign-choice results]
- Rank shadow-recompute: `Select-String -Path "fec\engine\compute_pillars.py" -Pattern "PARITY: CLEAN"`
- [withheld pending owner disclosure decision: retirement commits and gate states of rounds 4 and 5]
- Session-ratified items above (live-jobs check; the dispositions dependability read) carry no repo citation by nature — the master list with rationale lives in `moneyball-change-control`. [withheld pending owner disclosure decision: project rule on settled results] (Corrected 2026-09-30: "worktree/live-tree non-isolation" is off this list — worktrees DO isolate data, verified against `fec/paths.py:7-8`; change-control law 7.)
