---
name: moneyball-proof-and-analysis-toolkit
description: First-principles analysis recipes for building a NEW proof in the Moneyball repo instead of assuming a claim. Load when the task is any of - power studies (is there enough data before an evaluation?), planted-signal batteries as go/no-go gates, split-half reliability (Spearman-Brown), testing whether a correlation beats chance (permutation test), proving a refactor or artifact delta is behavior-neutral (the input-purity byte-match recipe - this skill is its sole owner), determinism / MC-sufficiency (CRN, seed stability), bounding an untested constant (sensitivity sweep), confound controls (gender/party/volume partials), diagnosing a signal-poor vs unlucky stratum, or independently re-deriving a reported number. Does NOT cover the prereg/look lifecycle rules (moneyball-research-methodology), acceptance thresholds and gold-label machinery (moneyball-validation-and-qa), running the SHIPPED diagnostic tools (moneyball-diagnostics-and-tooling), or measurement theory from zero (psychometrics-reference).
---

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
| 1 | Power study | Can this N detect the effect at all? Run BEFORE the evaluation | `big5_n_matrix_prereg.md` Addendum 2 (round 4 DATA-GATED at MEM_N≥250) |
| 2 | Plant/battery | Synthetic go/no-go gate: machinery must recover planted signal, refuse null+confound | `fec/b5_n_matrix.py` `simulate_battery()`; Addendum 1 orthogonalization lesson |
| 3 | Split-half + Spearman-Brown | Is a measure stable enough to use? | `fec/coop_v2_candidate.py` `sb()` (SB .873/.821); reactivity SB .43, burst SB .04 |
| 4 | Permutation-significance gate | Does the observed r beat chance at this N? | Audio pilot: +0.228 vs noise floor +0.234 = honest negative (`big5_audio_prereg.md` RESULT) |
| 5 | Input-purity byte-match | Prove an artifact delta came from inputs, not code | Gate (d) forensics, `AUDIT_FINDINGS_2026-07-03.md` |
| 6 | CRN / determinism / MC-sufficiency | Same seed ⇒ same bytes; MC=20 budget is enough | `fec/mc_stability_check.py`; `fec/tests/run_tests.py` sm64 block |
| 7 | Sensitivity bounding | An untested constant cannot have changed decisions | `fec/receptivity_sensitivity.py` (.18 scale, 0.60 retiring factor) |
| 8 | Confound attack | Does the signal survive gender/party/volume controls? | ES robustness look: +0.208 → partial −0.029 = CONFOUNDED (`big5_es_robustness_prereg.md`) |
| 9 | Stratum signal-poverty diagnostic | Is this subset genuinely signal-poor, or was the draw unlucky? | Round-5 5-seed check, median +0.132 < bar (`big5_a_matrix_prereg.md` Addendum 1) |
| 10 | Adversarial re-derivation | Independently recompute a reported number before trusting it | The P6 double-shrink artifact (`big5_methods.md` §9); fresh-seed re-derivation clause |

## Safety preamble (read before running anything)

- **Import == execution** for nearly every `fec/*.py`; most write artifacts at import time, and `fec/paths.py` resolves to the LIVE data tree even from a git worktree (session-ratified, 2026-07; see `moneyball-change-control` for the master rules). Only `fec/tests/run_tests.py` and `fec/audit_full.py` are safe to run casually.
- Build NEW analysis scripts in your scratchpad directory, not in `fec/`. Read live artifacts read-only (`json.load(open(...))`, sqlite `PRAGMA query_only=1`).
- Even "simulate" modes can write: `b5_n_matrix.py --simulate` featurizes, which updates `b5_empath_cache.json` on the live tree (`fec/b5_behavioral_instrument.py:52-67`). Warm caches make this a no-op in practice, but do not assume zero-write.
- Check for Paul's live jobs (running python processes, fresh artifact mtimes) before any baseline; run baselines serially (session-ratified, 2026-07).
- All commands below assume `cd "C:\Users\pgoff\OneDrive\Desktop\Melange Systems"` (the live tree — repo paths contain spaces, always quote).

Vocabulary used throughout (full treatment in `psychometrics-reference` and `moneyball-research-methodology`):
- **r** — Pearson correlation, −1..+1; the repo's standard effect measure.
- **z-score** — a value rescaled to (x − mean)/std so different measures are comparable.
- **OOF (out-of-fold)** — predictions for each row made by a model that never trained on that row (5-fold cross-validation); the repo's standard honest prediction vector (`fec/b5_behavioral_instrument.py:113-118`).
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

**Rule of thumb** (derived empirically in the audio pilot, `big5_audio_prereg.md` Addendum 3): the noise floor of a correlation at sample size N is r_crit ≈ 1.645/√N (one-sided 95%). At N=40 that is ≈ .26; at N=80 ≈ .18; at N=201 ≈ .117. If your expected effect sits at or below the floor, the design is underpowered no matter what feature engineering you do.

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

**Worked example (round 4, 2026-07-09, commit 48fd00d):** the text-N evaluation was fully locked at MEM_N=201 with a +0.15 bar. The power study (seeds 9001–9005, 5 reps/cell, orthogonalized plants — `big5_n_matrix_prereg.md` Addendum 2) found: true r=.40 passes **3/5 at n=201** with recovered r ranging **+0.015…+0.372** (extreme draw variance), but **5/5 at n=250** and 5/5 at 350/400/456; a true r=.50 passes 5/5 even at 201. Consequence: the route was **DATA-GATED at MEM_N ≥ 250** and the prereg RETIRED WITHOUT A LOOK — the look was never spent on a coin flip. Note the honest wrinkle recorded in `big5_a_matrix_prereg.md:50-52`: n=300 showed 4/5 (5-rep noise), so a single-draw battery refusal remains possible even above threshold — 5 reps/cell is a floor, not a luxury.

---

## Recipe 2 — Plant/battery construction (synthetic go/no-go gate)

**Proves:** that the evaluation MACHINERY works — it recovers a known planted signal, returns nothing on a destroyed pairing, refuses a confound-only signal, and admits a true signal that coexists with confounds. A green battery licenses the real evaluation; a red battery refuses it without consuming anything.
**Cannot prove:** anything about the real data. Battery outcomes ground no claim (the round-4/5 preregs state this explicitly).

**The four pinned parts** (the current standard, `fec/b5_n_matrix.py:148-211`, seeds pinned in `big5_n_matrix_prereg.md`):
- **(a) PLANTED** (seed 424242): synthetic criteria with true r≈.4 built FROM the real feature matrix — machinery must recover them (core ≥4/5; the hot-seat leg must clear its bars).
- **(b) NULL** (seed 535353): the REAL criteria permuted before pairing (pairing destroyed) — must yield 0 passes. Calibrates the p-values at the true subset size.
- **(c) CONFOUND-ONLY** (seed 646464): a synthetic criterion driven by gender/party/volume alone — the magnitude bars MAY pass (text encodes demographics) but the gating confound partial (Recipe 8) MUST refuse it.
- **(d) TRUE+CONFOUND** (seed 757575): planted signal PLUS additive confound loadings — the confound partial MUST admit it (proves the gate is not so strict it kills true positives).

**The round-4 lesson — orthogonalize plants in signal space.** Battery run #1 failed with random plant directions: over a low-effective-rank feature matrix (Empath's 194 categories are far from independent), random plants share signal-space variance, and OOF prediction AMPLIFIES the shared span — the N-plant's prediction read the E-plant at −.224 (raw plant overlap only −.146), beating its own weak recovery (+.187). That tested a HARDER, DIFFERENT property than the machinery must prove, because the real criteria are near-orthogonal. Fix, scoped to sim(a) only: sequential Gram–Schmidt orthogonalization of the planted signal components (`fec/b5_n_matrix.py:128-146` `plant_set()`; `big5_n_matrix_prereg.md` Addendum 1). Bars, seeds, and consequences were untouched — amending machinery validation pre-look is legitimate; amending bars is not.

**Battery refusal ≠ MISS.** When the battery fails, the look is REFUSED, not consumed: no RESULT exists, no closure is recorded, the route is "neither validated nor closed" — RETIRED WITHOUT A LOOK, reopening gated on a pinned condition. Calling it "failed" is a mis-claim (`big5_n_matrix_prereg.md:266-267`). Both retirements to date (rounds 4 and 5) were battery refusals with the gate holding: `"LOOK REFUSED (not consumed): simulate battery failure"`.

**Code sketch** — the orthogonalized constructor (adapt `plant_set()`; do not reinvent):
```python
S = []
for _ in TRAITS:                                # distinct-by-construction signals
    s = zz(X @ rng.standard_normal(X.shape[1]))
    for s0 in S: s = s - np.corrcoef(s, s0)[0,1]*s0   # Gram-Schmidt vs prior plants
    S.append(zz(s))
y = {t: 0.4*S[i] + np.sqrt(1-0.16)*rng.standard_normal(len(X)) for i,t in enumerate(TRAITS)}
```
(An earlier, simpler design — disjoint 20-category weight blocks, seed 11 — lives in `fec/b5_behavioral_instrument.py:158-178` `simulate()`; the orthogonalized `plant_set` is the current standard for anything matrix-shaped.)

**How to read output:** each part prints OK/FAIL and a one-line verdict `SIMULATE BATTERY: ALL GREEN` or `!! FAILURE — look forbidden`. Any FAIL = stop; diagnose whether it is a sim-design artifact (Addendum-1 pattern — fix the sim, not the bars) or genuine insufficiency (run Recipe 1, then Recipe 9).

**Worked examples:** round 4 (`big5_n_matrix_prereg.md` Addenda 1–2, retired @48fd00d); round 5 (`big5_a_matrix_prereg.md` Addendum 1, retired @d223188 — battery A-plant recovered only +0.105 at MEM_A=290, and Recipe 9 showed why). Status check that never risks a look: `python "fec\b5_n_matrix.py"` with no args prints lock/look/fingerprint state only.

---

## Recipe 3 — Split-half reliability + Spearman-Brown

**Proves:** that a measure is STABLE — two random halves of its own evidence agree with each other. Unreliable measures cap every downstream correlation (see attenuation below), so this is the first number to compute for any new disposition/criterion.
**Cannot prove:** that the measure captures the intended construct (validity), or that it is free of confounds. A perfectly reliable volume counter is still just a volume counter.

**Method:**
1. Split each member's underlying evidence (bills joined, interview turns, partners) into two halves. Half-construction must be STABLE and arbitrary-but-fixed: odd/even rows in a deterministic file order (`fec/coop_v2_candidate.py:87-90`), or an md5 hash of the partner name mod 2 (`fec/coop_v2_candidate.py:99` — note the in-code warning: Python's builtin `hash()` is salted per process, so NEVER use it for halving; use `hashlib.md5`).
2. Compute the statistic per half, correlate the halves across members: r_half.
3. Spearman-Brown correction (a half is noisier than the whole; SB estimates full-length reliability): **SB = 2·r_half / (1 + r_half)** (`fec/coop_v2_candidate.py:125-128`).
4. Enforce minimum evidence per half (the repo uses ≥5 rows or ≥3 partners per half) and report n.

**House calibration** (anchored to repo cases, not an external standard): SB ≥ .80 = solid criterion-grade (coop_v2 components: c2 .873, c3 .821 — `big5_a_matrix_prereg.md:42-43`); ~.40–.60 = real but modest, usable only WITH graded shrinkage toward neutral for thin coverage (reactivity_z SB=.43 with sh=√(min(1, turns/150)) — `fec/behavioral_dispositions.py:92-109`); ≤ ~.10 = situational noise, reject (burst SB=.04, "do not add it back" — `fec/behavioral_dispositions.py:101-102`).

**Attenuation honesty:** a criterion with reliability SB caps observed correlations at ≈ √SB × the other side's ceiling. Round 4 stated this pre-look: SB≈.43 ⇒ ceiling ≈ .66 × text ceiling, making a +0.15 bar "genuinely demanding" — and kept the bar anyway, with the sentence written down BEFORE the look so it could not become a post-hoc excuse (`big5_n_matrix_prereg.md:121-123`).

**The adversarial-re-derivation standard:** a reliability number is not trusted as reported — a second, independently coded computation must reproduce it (Recipe 10). The dispositions dependability read (2026-07-09) applied exactly this and caught three defects in the battery's own reporting — including a cooperation reliability that had been mislabeled with another statistic's value — with no shipped-code bug (session-ratified, 2026-07; the repo echo is `fec/coop_v2_candidate.py:3-6`, which cites "the dependability audit's 'volume proxy' indictment" as the motivation for coop_v2).

---

## Recipe 4 — Permutation-significance gates

**Proves:** that an observed correlation exceeds what THIS machinery on THIS sample size produces by chance — an empirical null distribution, immune to parametric assumptions and to n<<p optimism.
**Cannot prove:** causation, confound-freedom (Recipe 8), or that the effect will replicate on new data.

**The house method** (`fec/b5_behavioral_instrument.py:120-129` `exact_perm_p()`): hold the OOF prediction vector FIXED, permute the criterion labels K=5000 times (seed 20260708 — pinned, deliberately never varied across rounds), recompute r each time, and report **p = (#null ≥ observed + 1) / (K + 1)**, one-sided r>0. The +1s make p exact (never zero). The parametric t-test p is printed beside it as a cross-check only. For partial correlations, permute the RESIDUALIZED criterion against the fixed residualized prediction (`fec/b5_n_matrix.py:84-90`, seed 20260710).

**Critical design point:** the null must be generated through the SAME pipeline that produced the observed number (same features, same CV, same N). A null computed on a simplified pipeline understates the floor.

**Worked example — the audio pilot (2026-07-08, `big5_audio_prereg.md`), a complete arc:**
1. Addendum 2: a random-audio harness found the fair permutation noise floor at N=40 with 88 features was r **+0.267** — ABOVE the locked +0.15 bar. The pilot as pre-registered could not distinguish signal from chance; random audio had cleared +0.15 on one seed.
2. Addendum 3: the proposed PCA fix was TESTED and **REFUTED empirically** — PCA k=5..15 RAISED the floor to +0.34–0.36 (ridge under-regularized the few components). Diagnosis: +0.267 = 1.645/√40 — an N problem; "feature engineering cannot fix it; only samples can." Ratified pre-look fix: an N-aware significance gate (must clear the bar AND the permutation-null 95th percentile) plus N raised to ≥80.
3. RESULT (N=90): audio-E r = **+0.228** — which WOULD have cleared the naive +0.15 bar — vs noise floor 95% = **+0.234** ⇒ within noise. "An honest NEGATIVE, not a false positive." The gate is why the repo does not carry a fake audio validation today.

**Lesson to reuse:** when a proposed statistical fix sounds plausible (PCA, feature selection, weighting), TEST it on the null harness before adopting it. Plausible fixes can make the floor worse.

---

## Recipe 5 — Input-purity byte-match (gate-d / refactor-neutrality)

**Proves:** (i) that a post-run artifact delta was caused by changed INPUTS, not changed code; or equivalently (ii) that a refactor is behavior-neutral (same inputs ⇒ byte-identical outputs). As a bonus it is a fixed-point check: byte-match against current inputs ⇒ two-run convergence has settled.
**Cannot prove:** that the outputs are CORRECT — only that the code did not change what it computes.

**Precondition:** the engine must be deterministic (Recipe 6) and the pipeline idempotent. Idempotency was established at S2-04 (`AUDIT_FINDINGS_2026-07-02_RUN2.md` — the col-G limit cycle severed @f17dc2c, double-run byte-identical since), so "any future no-input hash drift = real regression."

**Steps:**
1. Note the drifted production artifact's md5.
2. Re-run the SAME engine against current on-disk inputs, with output redirected to a temp path so production is not clobbered. The engines have env dials for exactly this: `FRONTIER_OUT` (`fec/budget_frontier.py:120`), `OPT_OUT` (`fec/optimize.py:22`); `fec/audit_full.py:87-113` uses them the same way (`_audit_tmp_*.json`).
3. md5-compare temp vs production. **Byte-match ⇒ a deterministic pure function reproducing the new artifact proves the delta came from inputs, not the engines.** Mismatch ⇒ real regression (or a live job wrote mid-comparison — check mtimes/processes first).

```powershell
cd "C:\Users\pgoff\OneDrive\Desktop\Melange Systems"
$env:FRONTIER_OUT = "$env:TEMP\bf_purity.json"     # redirect: engine MUTATES live tree without this
python "fec\budget_frontier.py"
Get-FileHash "$env:TEMP\bf_purity.json", ".\budget_frontier.json" -Algorithm MD5
Remove-Item Env:FRONTIER_OUT
```
(For refactor-neutrality, run the temp-redirected engine once on the OLD code and once on the NEW code against frozen inputs and byte-compare the two temps.)

**Worked example (run-3, `AUDIT_FINDINGS_2026-07-03.md:33-44`):** 7 engine artifacts differed after the run-through while the user's own jobs were writing inputs live. A full budget_frontier rerun against current inputs reproduced the chain's artifact **byte-for-byte (md5 6a27a4ed…)** — delta proven input-driven, gate (d) passed, and the byte-match doubled as proof that convergence had settled. The method was first proven on the run-2 A/B artifact orbit (`AUDIT_FINDINGS_2026-07-02_RUN2.md`, "observed orbit" section).

---

## Recipe 6 — CRN / determinism / MC-sufficiency verification

**Proves:** (i) determinism: same inputs + same seed ⇒ byte-identical output; (ii) MC-sufficiency: the Monte-Carlo budget (MC=20) is not overfitting seed selection to one particular set of random draws.
**Cannot prove:** that the simulated physics is right — only that its randomness is controlled and its budget adequate.

**Background:** CRN (Common Random Numbers) means every "random" draw is a deterministic hash of its key (`moneyball_core.sm64`), so competing candidates in greedy optimization are always compared under IDENTICAL draws. That kills the independently-noisy-estimate failure mode outright (the Almazaydeh CELF++ result the check is motivated by — `fec/mc_stability_check.py:3-10`). The residual risk is subtler: the picked seed SET could be overfit to one seed's particular 20 cascade realizations.

**Three-layer verification, cheapest first:**
1. **Kernel invariants** — `python "fec\tests\run_tests.py"`: sm64 in [0,1), deterministic, well-spread, key-independent (`fec/tests/run_tests.py:18-22`). Runs in seconds; exit 1 on failure.
2. **Double-run byte-match** — run the engine twice with identical env, temp-redirected outputs (Recipe 5 dials); md5s must be identical. Standard audit gate (`AUDIT_FINDINGS_2026-07-03.md:31`).
3. **MC-budget stability** — the 100%-overlap method, shipped as `fec/mc_stability_check.py`: rebuild a single-topic frontier under (MC=20,SEED=7 production), (MC=100,SEED=7), (MC=20,SEED=1), (MC=20,SEED=13); compare picked-seed-set Jaccard overlap, identical-prefix length, and spread delta. Interpretation printed by the tool itself: "high set-overlap at MC=100 (same seed) and across RNG seeds ⇒ the MC=20+CRN frontier is NOT overfit to its particular draws; low overlap ⇒ raise the frontier MC budget." The 2026-07-01 validation recorded 100% overlap — MC=20+CRN ratified (memory of record; re-run the tool to re-verify rather than trusting the recollection).

**Caution:** `mc_stability_check.py` spawns 4 full frontier builds via subprocess (several minutes, live-tree temp files it removes itself). Never run with production-calibration env dials still set in your shell — defaults ARE the ratified state.

---

## Recipe 7 — Sensitivity bounding of untested constants

**Proves:** that a constant's exact value COULD NOT HAVE CHANGED DECISIONS — sweep it across its plausible range and show the decision surface (who gets targeted) is stable. This is the honest next-best thing when no outcome data exists to test a magnitude.
**Cannot prove:** that the constant's value is correct. A decision-robust constant is safely arbitrary; a decision-sensitive one is the one to take to an outcome test FIRST.

**The shipped template** — `fec/receptivity_sensitivity.py` (built 2026-07-04 to answer "the .18 scaling and 0.60 retiring factor are literature-shaped design choices no outcome has ever tested"):
1. **Stage 1, replication gate (mandatory — Recipe 10 inline):** recompute the derived quantities from the artifact's own stored components under BASELINE constants; all 533 stored `pressure_mult`/`seed_prob` values must match exactly, else the sweep formulas have drifted from production and every variant is meaningless (`fec/receptivity_sensitivity.py:42-52`, hard `sys.exit(1)` on mismatch).
2. Define the DECISION SURFACE — the thing allocations actually key off (per-member flip-model winnability), not the intermediate multiplier.
3. Sweep each constant over a plausible range (the file's variants: susceptibility scale .18 → .09/.27; prospect-theory 1.15/.92 → mild/strong; retiring 0.60 → .45/.80/1.00-off; persona weight .30 → 0/.45).
4. Score each variant by top-20/top-50 target-set overlap and rank correlation vs baseline. Verdict thresholds as shipped: **ROBUST** ≥18/20 overlap, MODERATE ≥15/20, else **SENSITIVE**.
5. Restore baseline state after the sweep (the file swaps the kernel's receptivity cache in memory and restores it — line 107).

**How to read:** "ROBUST = the constant cannot have changed WHO gets targeted (top-20 stable across its plausible range); SENSITIVE = this constant is the one to outcome-test first" (printed by the tool, lines 119-120). The prospective outcome test the file pre-registers in its docstring (seed_prob vs next-quarter cosponsorships; pressure_mult vs stance movement among actually-engaged members) is the eventual real test — `fec/outcome_snapshot.py` exists to freeze predictions for it. Honesty pattern worth copying: where a sweep does NOT rerun the expensive downstream (cascades), the tool says so in its own output ("gate analytics; cascades not rerun").

**Caution:** the script imports `flip_model`, which executes at import (live-tree reads). It writes nothing, but treat it per the safety preamble.

---

## Recipe 8 — Confound attack (robustness look with pre-declared consequences)

**Proves:** whether a validated signal survives removal of NAMED confounds — the repo's recurring killers are **gender** (voice features encode speaker sex), **party**, and **volume** (how much a member talks/cosponsors). A signal that vanishes under the partial was reading the confound.
**Cannot prove:** that no OTHER confound exists; only the ones you conditioned on are excluded.

**The house method — Frisch–Waugh partial** (`fec/b5_n_matrix.py:81-90`): residualize BOTH the prediction and the criterion on the confound set Z (least-squares regression with intercept; keep the residuals), then r_partial = corr(residuals) with a permutation p (Recipe 4, seed 20260710) on the residualized criterion. Reported beside it, non-gating: within-group r (e.g. within each sex separately) — the bluntest possible cross-check.

```python
def resid(v, Z):
    Z1 = np.column_stack([np.ones(len(v)), Z])
    b, *_ = np.linalg.lstsq(Z1, v, rcond=None)
    return v - Z1 @ b
rp, ry = resid(pred, Z), resid(y, Z)      # Z: columns e.g. gender, party, log(1+volume)
r_partial = np.corrcoef(rp, ry)[0, 1]     # + permutation p per Recipe 4
```

**Non-negotiable discipline (this is Project Law):** never reverse a settled result under conversational pressure — the ONLY legitimate way a settled result gains a caveat is a LOCKED robustness look with pre-declared consequences (session-ratified, 2026-07; enacted verbatim in `big5_es_robustness_prereg.md`). That means: (1) the confound set and method are fixed a-priori; (2) the outcome TIERS and their exact resulting WORDING are written before the look (ROBUST / PARTIAL / CONFOUNDED in that prereg); (3) the original result's text is never modified — a dated addendum annotates it ("history is not rewritten", `big5_es_crossmodal_prereg.md:65-72`); (4) one look, no re-running with different controls after unblinding.

**Worked example — the ES gender confound (2026-07-09, locked @fd963ab, result @34bf7e4):** the voice→text-ES pass (+0.208, held-out, perm p=.0002 — itself a clean look) had never controlled gender, and F0-family acoustic features encode speaker sex almost perfectly. The locked robustness look: partial r(pred, ES | gender, party) = **−0.029, perm-p .7151**; within-sex r = −0.016 (M, n=282) / −0.036 (F, n=113) — essentially zero inside each sex. Pre-declared tier CONFOUNDED applied: the +0.208 pass STANDS as history (its own locked bars were met and are not retro-moved), but every citation must carry the caveat "not demonstrably gender-independent"; "all five traits validated" is superseded. This is the model case of a settled result legitimately gaining a caveat.

**Make the partial GATING in new evaluations,** not post-hoc: rounds 4–5 wired the confound partial in as bar 5, volume-hardened (conditioning set includes log-volume and, in round 4, the shrinkage weight itself), with battery parts (c)/(d) proving the gate both refuses confound-only signal and admits true+confound signal (`big5_n_matrix_prereg.md:111-119`; `big5_a_matrix_prereg.md:105-108`). Precedent for why volume matters: cooperation_z was shown to be 2/3 raw cosponsorship volume (`fec/coop_v2_candidate.py:3-6`).

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

**Worked example — round 5 (2026-07-09, `big5_a_matrix_prereg.md` Addendum 1, retired @d223188):** the battery's A-plant recovered only +0.105 on the MEM_A=290 stratum despite round-4's power study showing random draws at n≈290–300 recover ~.14–.24 (median ≈.195). The 5-seed diagnostic (seeds 424242/515151/616161/717171/818181, the battery's exact constructor, on the actual stratum): own r = **+0.105, +0.119, +0.132, +0.190, +0.251 — median +0.132 < the +0.15 bar; bars 1–4 pass 2/5**. Verdict: NOT single-draw flakiness — the MEM_A stratum (members with ≥10 known-party cosponsorships in the finance-scoped archive) has more homogeneous Empath profiles and genuinely less recoverable text signal at this n; a true r=.40 would MISS ~60% of the time. A multi-rep battery re-spec was considered and REJECTED because it would also have refused (2/5 < any honest threshold) — no battery amendment could license the look. Route **DIAGNOSTIC-GATED**: a successor prereg is allowed only when the SAME pinned diagnostic passes ≥3/5 on bars 1–4 on the then-current stratum.

---

## Recipe 10 — Adversarial re-derivation

**Proves:** that a reported number is REPRODUCIBLE by an independent computation — different code path, fresh partitions, or shadow recompute — before it is trusted, cited, or allowed to promote anything.
**Cannot prove:** that the number MEANS what its label claims. The deepest catch in this repo's history was a correctly-computed number on the WRONG metric — so re-derive the metric choice, not just the arithmetic.

**Four house patterns, all live in the repo:**

1. **Re-derive the metric itself (the P6 lesson — doctrine since 2026-07-07).** P6 empirical-Bayes shrinkage CLEARED its pre-registered split-half bar (SB .748 → .831), but the audit decomposition (`python "fec\big5_improvements_eval.py" --p6diag`) showed shrunk-vs-RAW cross-correlation only .704: shrinking BOTH halves toward 0 mechanically inflates their correlation, so **+0.127 of the apparent gain was a double-shrink ARTIFACT, ~0 real**. The split-half bar was the wrong instrument to judge a shrinkage method — a prereg design error. The claim was RETRACTED; the change was KEPT on independent, shrinkage-neutral external-criterion grounds (`big5_methods.md` §9, lines 192-206; auditor's own-goal ledger H-1 in `AUDIT_FINDINGS_2026-07-07.md`). Consequence: **every claimed PASS is adversarially re-derived before it is recorded as real** — stated in every subsequent prereg (e.g. `big5_audio_prereg.md:4-5`).

2. **Fresh-seed re-derivation of a pass (fold-partition robustness).** Rounds 4–5 wire it into the consequence clause: on a bars-pass, recompute ALL model prediction vectors with fresh OOF seeds [101,113,127,139,151] (permutation seeds stay pinned) and the re-derivation must re-clear ALL bars; failure = "FRAGILE = MISS for ALL consequences INCLUDING closure" (`fec/b5_n_matrix.py:25,323-332`; `big5_n_matrix_prereg.md:174-179`). A pass that only exists under one fold partition is not a pass.

3. **Shadow recompute of production numbers.** `fec/compute_pillars.py` (no `--write`) recomputes every rank from inputs via an independent Python path and requires exact agreement with the authority artifact — tail `PARITY: CLEAN` (`fec/compute_pillars.py:106-124`; wired into audit_full). Same pattern at analysis scale: `receptivity_sensitivity.py`'s stage-1 replication gate (Recipe 7) refuses to sweep until 533/533 stored values are reproduced exactly.

4. **Remove analyst degrees of freedom that re-derivation cannot check.** The acoustic-ES composite was hand-signed on folk intuition ("steady voice = calm") and its −0.165 was real signal read UPSIDE-DOWN; the replacement protocol removed sign choice entirely (held-out CV learns the weights; a spurious in-sample sign flip does not transfer out-of-fold) (`big5_es_crossmodal_prereg.md:3-12,41-45`). If a number depends on a hand choice, the re-derivation must vary that choice or eliminate it.

**Worked example of the standard applied to reporting:** the dispositions dependability read (2026-07-09) independently re-derived every reliability figure the battery had reported and caught three defects in the REPORTING alone — numbers mislabeled or attributed to the wrong statistic — with zero shipped-code bugs (session-ratified, 2026-07; motivating context quoted in `fec/coop_v2_candidate.py:3-6`). The generalizable rule: two independent computations must agree before a number enters a document of record; if you cannot independently recompute it, say so instead of citing it. A related enforcement: verification sub-agents systematically over-claim — all four run-4j literature-audit agents produced at least one false CRITICAL, so every verdict was re-checked against actual code wording before acceptance (`AUDIT_FINDINGS_2026-07-04.md`, agent-calibration ledger).

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

Facts here were verified against the repo on 2026-07-09. Volatile facts and one-line re-verification commands (PowerShell, from the repo root — `cd "C:\Users\pgoff\OneDrive\Desktop\Melange Systems"`; in a worktree, substitute its root):

- Round-4 power study numbers, DATA-GATE at MEM_N≥250, seeds 9001–9005:
  `Select-String -Path "big5_n_matrix_prereg.md" -Pattern "9001|MEM_N >= 250|RETIRED WITHOUT A LOOK"`
- Round-5 5-seed stratum diagnostic (median +0.132, ≥3/5 successor gate):
  `Select-String -Path "big5_a_matrix_prereg.md" -Pattern "median \+0.132|818181|>=3/5|DIAGNOSTIC-GATED"`
- Battery parts/seeds 424242/535353/646464/757575 and `plant_set` orthogonalization:
  `Select-String -Path "fec\b5_n_matrix.py" -Pattern "424242|535353|646464|757575|Gram-Schmidt"`
- Fresh-seed re-derivation constant RESEEDS [101,113,127,139,151]:
  `Select-String -Path "fec\b5_n_matrix.py" -Pattern "RESEEDS"`
- Spearman-Brown helper and md5 half-hash: `Select-String -Path "fec\coop_v2_candidate.py" -Pattern "def sb|md5"`
- Reactivity SB .43 / burst SB .04 / shrinkage: `Select-String -Path "fec\behavioral_dispositions.py" -Pattern "SB=.43|SB=.04|REACT_TURNS"`
- exact_perm_p (K=5000, seed 20260708) and OOF seeds [7,17,29,43,61]:
  `Select-String -Path "fec\b5_behavioral_instrument.py" -Pattern "20260708|SEEDS = "`
- Audio noise-floor arc (1.645/sqrt, PCA REFUTED, +0.228 vs +0.234):
  `Select-String -Path "big5_audio_prereg.md" -Pattern "1.645|REFUTED|\+0.234"`
- Input-purity method + gate-d forensics: `Select-String -Path "AUDIT_FINDINGS_2026-07-03.md" -Pattern "input-purity|byte-for-byte"`
- Temp-redirect dials: `Select-String -Path "fec\budget_frontier.py","fec\optimize.py" -Pattern "FRONTIER_OUT|OPT_OUT"`
- MC-stability method + interpretation: `Select-String -Path "fec\mc_stability_check.py" -Pattern "MC=100|Jaccard|NOT overfit"`
- Sensitivity harness replication gate + verdict thresholds: `Select-String -Path "fec\receptivity_sensitivity.py" -Pattern "REPLICATION GATE|ROBUST"`
- ES robustness result (partial −0.029, CONFOUNDED, tiers): `Select-String -Path "big5_es_robustness_prereg.md" -Pattern "-0.029|CONFOUNDED|ROBUST"`
- P6 double-shrink artifact (+0.127): `Select-String -Path "big5_methods.md" -Pattern "0.127|double-shrink"`
- Mis-signed composite / sign-choice-free CV: `Select-String -Path "big5_es_crossmodal_prereg.md" -Pattern "MIS-SIGNED|sign-hacked"`
- Rank shadow-recompute: `Select-String -Path "fec\compute_pillars.py" -Pattern "PARITY: CLEAN"`
- Retirement commits: `git log --oneline --all -n 20 | Select-String "48fd00d|d223188|28914b3"` (round-4 retired @48fd00d; round-5 locked @28914b3, retired @d223188).
- Gate states (round 4/5 retired-without-a-look) are single-vintage by fingerprint design: the status modes `python "fec\b5_n_matrix.py"` / `python "fec\b5_a_matrix.py"` (no args) print lock/look/fingerprint state — but see the safety preamble before running anything (their featurize path can touch the live Empath cache).
- Session-ratified items above (worktree/live-tree non-isolation; live-jobs check; the dispositions dependability read; the settled-result caveat law) carry no repo citation by nature — the master list with rationale lives in `moneyball-change-control`.
