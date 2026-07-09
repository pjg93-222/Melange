# Behavior-anchored per-trait text instrument — the optimal build (pre-registration)

**Locked 2026-07-08 BEFORE the look. Goal: diagonal-dominant per-trait validity (each trait's text
read predicts its OWN behavioral criterion best). The 0/5 was on Pink's raw LLM trait SCORES; this
REBUILDS each trait the way the C win worked: text features supervised DIRECTLY to the behavioral
criterion, held-out. Method locked to prevent overfitting under pressure.**

## Instrument (fixed a-priori — NO feature/model search)
- Features: **Empath (194 categories)** from each member's full text (speeches+interviews+tweets),
  z-within-roster. (Empath is the fixed set that won C; no LSA/stylometric search to avoid p-hacking.)
- Model: **Ridge**, nested 5x5 CV (alpha grid fixed), HELD-OUT out-of-fold prediction per trait.
- One supervised model PER TRAIT, each fit to that trait's behavioral criterion.

## Criteria (independent of text)
A=cooperation_z ; C=diligence_z ; E=visibility_z ; O=breadth_z (behavioral dispositions).
ES = the hard one; PRE-DECLARED attempts, in order (first that is a VALID criterion is used):
  (1) **residual-GMP** = Voteview GMP residualized on cooperation_z + extremity + party (isolates
      voting-consistency NOT explained by agreeableness -> the ES-specific part);
  (2) **affect lability** = std of per-tweet sentiment (Empath positive-negative) over time (emotional
      volatility = low ES), sign flipped.
An ES criterion is VALID only if it is not just a proxy for another trait's criterion (checked:
its strongest text-model predictor must be the ES model, not A/C/E/O).

## Pass rule per trait (ONE look, locked)
A trait PASSES iff BOTH:
- (1) held-out r(pred_t, own criterion) **>= +0.15 AND exact perm-p < .05** (real, not chance);
- (2) **DIAGONAL-DOMINANT:** corr(pred_t, own criterion) is the MAX over all 5 criteria (the model
  predicts its OWN behavior more than any other trait's behavior).
Count = traits passing. **5/5 requires a VALID ES criterion; if both ES attempts are null/invalid,
ES CANNOT pass and the honest count is 4/5 — NO fabrication, NO relaxing the bars, NO cherry-picking.**

## Discipline
Locked + committed BEFORE the look. Features/model fixed a-priori. One look. Held-out CV + permutation
guard every diagonal. Criteria never fit to text (they ARE the independent targets). Any PASS
adversarially re-derived. The pressure to hit 5/5 makes these guards MORE binding, not less.
