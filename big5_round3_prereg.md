# Big-5 Round 3 Pre-Registration — split-sample item surgery + gated shrinkage
**Locked: 2026-07-07, user directive ("keep pushing on the psychology... you will not stop until
they pass... make sure the logic checks out. NO SHORTCUTS"), BEFORE any evaluation runs.**

Targets = the two honest outstanding failures of the shipped pink configuration on the frozen
snapshot (control: SB .748, MTMM .493, discriminant .308, A-ES .653, KG 4/5, C-crit +.156/+.111):
the A-ES halo and the discriminant sitting just over .30. Round-1 taught WHY the naive fixes fail
(P1 reweighting amplifies halo items; P2 global-PC1 removal destroys criterion-valid variance).
Round 3 uses designs that answer those failure modes directly.

## P5 — targeted item exclusion, SPLIT-SAMPLE (the A-ES surgery)
**Design principle:** the A-ES correlation may be driven by specific item PAIRS (e.g., "warm,
considerate" and "calm, even-keeled" both reading pleasant demeanor). Dropping at most one item
from A and at most one from ES is a minimal, interpretable interventionthat — unlike P2 — cannot
destroy variance in the untouched traits.
**Split-sample discipline (the no-peeking mechanism):**
- Members split deterministically: SELECTION half = even md5(member), TEST half = odd.
- On the SELECTION half only, evaluate all 25 candidate configurations (drop none-or-one of the
  4 A items x none-or-one of the 4 ES items; other traits untouched). Choose the configuration
  minimizing A-ES |r| subject to: selection-half split-half SB for A and ES each >= (selection-half
  control - 0.02). Deterministic argmin; ties break toward fewer drops, then item order.
- The chosen configuration is then evaluated ONCE on the TEST half. No iteration, no second look.
**Bars (all on the TEST half, paired against the TEST-half equal-weight control):**
- A-ES |r| <= 0.50
- discriminant mean off-diag |r| <= 0.30
- MTMM mean same-trait cross-genre >= (test-half control - 0.02)
- split-half SB mean >= (test-half control - 0.02)
- known-groups >= 4/5
- C(INTERVIEW) vs votes_cast and vs follow-through each >= (test-half control - 0.03)
**Promotion on PASS:** ship the selected item drops as scoring weights (dropped item weight 0) in
big5_llm aggregation for the FULL roster; artifact regenerates from cache ($0); desk/receptivity
consume unchanged. **On MISS:** all 20 items stand; result documented.

## P6 — coverage-GATED empirical-Bayes shrinkage
**Design principle:** P4 failed because ungated shrinkage moved well-measured extremes (.73 SD).
The bar itself defines well-measured as n>=8, so the redesign makes the protection structural:
shrinkage applies ONLY to members with n_chunks < 8 (score* = z*n/(n+k), method-of-moments k per
trait); members with n >= 8 are untouched BY CONSTRUCTION.
**Bars (frozen snapshot, one look):**
- split-half SB mean >= control + 0.015 (the gated gain is necessarily smaller than P4's +0.038;
  below +0.015 the change is not worth carrying)
- movement of n>=8 members: exactly 0 (asserted, structural)
- MTMM mean >= control - 0.01; discriminant <= control + 0.01
**Promotion on PASS:** shrunken scores become primary for n<8 members (raw retained alongside);
n>=8 unchanged. **On MISS:** raw stands; k ships as info.

## B6 — blue rebuilt on a NEW feature basis (stylometry), staged AFTER P5/P6
Round-1/round-2 established the 31 category-rate features cannot carry genre-stable multi-trait
structure. B6 therefore changes the BASIS, not the fitting: function-word profiles, punctuation
and sentence-length distributions, hedging/certainty markers, and type-token statistics computed
PER GENRE from the raw corpus, standardized WITHIN genre (genre-controlled by construction), then
averaged across genres per member before fitting the v2 behavioral targets (same nested CV).
Blue never touches pink data at any step (standing prohibition).
**Bars (one look):** held-out r A >= +0.14, C >= +0.13, O >= +0.20 (match or beat v2's shipped
values); E >= +0.20 (a real but genre-robust E, vs v2's +0.34 genre-carried); AND family MTMM
mean same-trait cross-genre > mean cross-trait within-genre (the test every lexical family has
failed). **On MISS:** v2 stands; B6 documented; further blue work requires a different modality
(the CT-CM capstone), not another lexical iteration.

## Standing rules
One look per configuration; misses revert; bars never move after data is seen; blue-on-pink
calibration PROHIBITED. Iteration across ROUNDS is legitimate (each failure licenses a new
design with a new prereg); iteration within a look is not.

## P7 addendum — within-chunk ipsatization (locked 2026-07-07 before evaluation, after P5 MISS)
**External benchmark motivating the design:** RKH lifetime means show A-ES r = +.443 (House,
n=916) / +.393 (Senate, n=179): roughly .44 of our .653 is population-real covariance; the ~.21
excess is chunk-tone halo. P5 proved item surgery cannot reach it; P2 proved member-level
component removal destroys valid variance. Ipsatization targets the remaining suspect precisely:
per chunk, subtract the chunk's mean keyed-item score from every item (removing that chunk's
overall tone), then score traits and aggregate as shipped. Chunk-level profile SHAPE survives;
chunk mood does not.
**Bars (frozen snapshot, ONE look, absolute):**
- A-ES |r| <= 0.50   (externally anchored: RKH .443)
- discriminant mean off-diag |r| <= 0.30
- MTMM mean >= 0.450
- split-half SB mean >= 0.72
- known-groups >= 4/5
- C(INT) vs votes >= +0.126 and vs follow-through >= +0.081 (control - 0.03)
**On PASS:** promote ipsatized scoring into big5_llm aggregation (composes with P6 gating).
**On MISS:** the scoring layer is EXHAUSTED (four design families: reweight, component removal,
item surgery, ipsatization). A-ES is then documented as substantive covariance plus judge-level
halo with the RKH benchmark cited, and the remaining lever is itemset v3 (changed item TEXT =
full re-score, a funding decision for the user), not further scoring arithmetic.
