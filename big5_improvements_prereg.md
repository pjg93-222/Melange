# Big-5 Instrument Improvements — Pre-Registration
**Locked: 2026-07-06, BEFORE the post-collector full re-score exists.**
User-ratified ("Yes, do it"). Same discipline as `big5_nomological_prereg.md` and the interview-C
retest: bars are set here, once, before the data they will be judged on is generated. Each
improvement gets ONE look against its bars on the frozen post-Monday-gate corpus snapshot.
Misses revert; no post-hoc bar adjustment; partial passes promote only the passing component.

**Baselines the bars reference (full-roster artifact @2adda6b, 469 members):**
- MTMM mean same-trait cross-genre: **+0.410** (halo floor 0.280)
- Discriminant mean off-diagonal |r|: **0.28**; worst pair A–ES **+0.68**
- Known-groups party signs: **4/5**
- Split-half (even/odd chunks, SB): **O .73, C .62, E .67, A .68, ES .67** (mean .674)
- Criterion: LLM-C vs votes_cast **+0.146** (interview-genre, n=180), vs follow-through **+0.132**
- Blue v2 held-out criterion r: **A +.14, C +.13, E +.34, O +.20**
- Blue's lexical family MTMM: FAILED (cross-genre .21–.28 < halo .27–.32)

Test order (declared): P1 → P2 → P4 → B5. Each evaluated against the ORIGINAL baselines above
(not against each other); the final shipped configuration composes only the individually-passing
changes, then the composed configuration must itself re-clear bars P-ALL before promotion.

---

## P1 — Pink: item reweighting (equal weights → discrimination weights)
**Method:** per trait, weights = item-total correlations computed on the full post-gate chunk
cache (each item scored −1/0/+1; item-total r vs the trait's own remaining items, corrected for
overlap). Weights clipped to [0.10, 0.60] of total and renormalized; signs fixed by the itemset
keying (never flipped by data).
**Bars (all must hold):**
- Split-half SB improves on ≥3 of 5 traits AND mean SB ≥ **+0.03** over .674
- MTMM mean same-trait cross-genre ≥ **0.390** (baseline −0.02)
- Discriminant mean off-diag |r| ≤ **0.30**
**On miss:** equal weights stand.

## P2 — Pink: bifactor halo removal (targets A–ES .68)
**Method:** chunk-level 20-item matrix → extract first principal component (the general
evaluative/halo factor) → score each trait from item residuals after removing that component
(loadings estimated once on the full cache; the same projection applied to every chunk).
**Bars (all must hold):**
- A–ES |r| ≤ **0.50**
- MTMM mean same-trait cross-genre ≥ **0.390**
- Known-groups signs ≥ **4/5**
- LLM-C vs votes_cast and vs follow-through each ≥ (baseline − **0.02**)
**On miss:** halo stays in (interpreted as partly real trait covariance); the A–ES caveat
remains documented on the desk instead.

## P4 — Pink: empirical-Bayes shrinkage by chunk coverage
**Method:** member score* = [n/(n+k)]·z where n = member chunk count and k is estimated
method-of-moments from the within-member between-chunk variance (one k per trait). Raw
unshrunk scores retained in the artifact alongside.
**Bars (all must hold):**
- Mean split-half SB ≥ **+0.02** over the configuration under test
- No member with n_chunks ≥ 8 moves more than **0.5 SD** (shrinkage must act on thin coverage,
  not reshuffle well-measured members)
**On miss:** raw scores stand; k and the reliability column still ship (as information only).

## B5 — Blue: genre-residualized features, refit
**Method:** regress every lexical feature on genre indicators + log(text volume); replace
features with residuals; re-run the v2 behavior-calibrated fitting (same targets, same nested
5-fold, same clipping) on the residualized features.
**Bars (both must hold):**
- Held-out criterion r: A ≥ **+0.12**, C ≥ **+0.11**, O ≥ **+0.18** (baseline −0.02); E ≥
  **+0.29** (baseline −0.05 — E is allowed a larger give-back because part of current E is
  genre variance that residualization is SUPPOSED to remove)
- MTMM on the refit family: mean same-trait cross-genre **exceeds** mean cross-trait
  within-genre (the pass its parent family failed)
**On miss:** current v2 stands; the failure is itself informative (lexical signal may be
inseparable from genre) and gets documented in big5_methods.md.

## P-ALL — composition gate
The composed final configuration (whichever of P1/P2/P4 passed, applied together) must
re-clear: MTMM ≥ 0.390, discriminant ≤ 0.30, known-groups ≥ 4/5, mean SB ≥ .674 + (sum of
individually-earned SB gains − 0.02 tolerance). If composition interacts destructively,
drop changes in reverse order of individual gain until it clears.

## Explicitly out of scope for this round
- Genre-validity weighting for C: governed by the ALREADY-locked interview-C retest bars
  (ρ ≥ +0.15 votes_cast AND ≥ +0.10 follow-through at the Monday gate).
- Interaction-features → blue E (round 2; needs its own bars).
- CT-CM latent trait model (capstone; separate pre-registration).
- Any change to item TEXT or the −1/0/+1 scale (new itemset = full re-score; not funded).
- **PROHIBITED permanently: calibrating blue against pink (or vice versa).** Instrument
  independence is what gives the desk's agreement zones evidentiary meaning.
