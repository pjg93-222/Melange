# ES cross-modal robustness — gender/party partial (pre-registration)

**Locked 2026-07-09 BEFORE the look (psych-audit session, user-approved augment). The ES cross-modal
PASS (held-out r=+0.208, big5_es_crossmodal_prereg.md RESULT) was sign-choice-free and adversarially
derived, but never controlled for GENDER: the F0-family eGeMAPS functionals encode speaker sex almost
perfectly, and text-ES plausibly differs by gender (self-report N shows d~0.4 sex differences in
general populations), so a voice->text-ES correlation could partly ride that confound. Party is
included for the same reason (voice register and text style both differ by party demographics). This
test ANNOTATES the recorded pass; it does not re-litigate that test's own locked bars.**

## Data & method (fixed a-priori — no analyst degrees of freedom)
- The SAME out-of-fold prediction vector as the recorded pass: b5_es_crossmodal.py's protocol re-run
  verbatim (all 88 clean eGeMAPS z-features -> ridge nested CV, ALPHAS=[1,3,10,30,100,300,1000],
  outer 5-fold x SEEDS=[7,17,29,43,61], out-of-fold predictions averaged) — deterministic, so it
  reproduces the recorded +0.208 exactly (reproduction is printed as a sanity line).
- Gender: fec/legislators.csv (unitedstates export), bioguide_id -> gender (M/F), joined via the
  kernel bioguide map. Party: kernel party(). Members with no gender mapping are DROPPED (count
  reported; expected ~0 of the 395).
- PARTIAL (Frisch-Waugh): residualize BOTH pred and big5_v2-ES on [1, gender, party];
  r_partial = corr(resid_pred, resid_y).
- Null: 5000 permutations of resid_y against fixed resid_pred (seed 20260710), one-sided (r>0).
- Reported, NON-gating: within-gender r (M and F separately, with n), gender balance of the 395,
  raw-r reproduction check.

## Pre-declared outcomes (ONE look, wording fixed now)
- **ROBUST**: r_partial >= +0.10 AND perm-p < .05 -> big5_methods §16 gains "gender/party-robust";
  desk voice-ES line unchanged.
- **PARTIAL**: 0 < r_partial < +0.10 AND perm-p < .05 -> §16 and the desk voice-ES line gain a
  "partly gender/party-mediated" caveat; the validation stands WITH the caveat.
- **CONFOUNDED**: perm-p >= .05 OR r_partial <= 0 -> §16 and the desk line gain an explicit "not
  demonstrably gender-independent" caveat; the recorded +0.208 pass STANDS as history (its own locked
  bars were met and are not retro-moved), but the VALIDATION CLAIM must carry the confound caveat
  wherever cited (incl. the "all five traits validated" summary line).

## Discipline
Locked + committed BEFORE the look. One look; no re-runs with different controls after unblinding.
`--simulate` validates the machinery on planted confound-only and true-signal synthetic cases without
touching the real pairing. Any outcome is recorded verbatim under RESULT below.

## RESULT — THE ONE LOOK (2026-07-09, N=395, dropped 0 without gender; F=113 M=282)
**CONFOUNDED** (pre-declared outcome 3). Machinery pre-validated via --simulate (planted confound
correctly detected, planted true signal correctly survives).
- Raw r reproduction: **+0.208** (exact match to the recorded pass — deterministic protocol confirmed).
- **Partial r(pred, big5_v2-ES | gender, party) = -0.029, perm-p = 0.7151** (5000 perms, seed 20260710).
- Within-gender (reported, non-gating): **M (n=282) r = -0.016; F (n=113) r = -0.036** — the
  voice->text-ES convergence is essentially ZERO within each sex.
**Interpretation (per the pre-declared consequence):** the recorded +0.208 pass STANDS as history —
its own locked bars were met and are not retro-moved — but the VALIDATION CLAIM carries the explicit
caveat: the cross-modal ES effect is **not demonstrably gender-independent**; controlling gender and
party removes it entirely, and it is null within both sexes. The voice model was predominantly
reading speaker sex (F0-family features), and text-ES differs by sex in this roster. "All five
traits validated" must therefore be cited as: A/C/E/O behaviorally validated (O/C/E now
diagonal-dominant per big5_behavioral_instrument_prereg RESULT); **ES measured but without a clean
independent validation** (text: +.149 near-miss, not dominant; voice: gender-confounded).
Consequences applied: big5_methods §16 annotation + §17 record; desk voice-ES line caveated;
big5_es_crossmodal_prereg.md carries a dated addendum pointing here. The original result text is
left unmodified (history is not rewritten).
