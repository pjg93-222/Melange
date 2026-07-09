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

## RESULT — THE ONE LOOK (2026-07-09, N=456; machinery pre-validated via --simulate: planted 5/5, null 0/5)
**VERDICT: 3/5 traits pass** (bars exactly as locked: held-out r >= +0.15 AND exact perm-p < .05 AND
diagonal-dominant; no bar moved, no cherry-picking). Pre-look hardening, bars untouched: exact
permutation p restored per this prereg (the committed script had substituted a parametric p), a
__main__ one-look gate added (the file formerly ran the look at import), Empath features cached.

Discriminant matrix, corr(held-out pred_row, criterion_col), ES criterion = residual-GMP:

| model\crit | O | C | E | A | ES |
|---|---|---|---|---|---|
| pred_O  | **+.198** | +.137 | +.028 | +.187 | +.079 |
| pred_C  | +.117 | **+.277** | -.146 | +.149 | +.126 |
| pred_E  | +.023 | -.096 | **+.552** | -.035 | -.148 |
| pred_A  | +.197 | +.210 | -.083 | **+.183** | +.066 |
| pred_ES | +.092 | +.155 | -.303 | +.072 | **+.149** |

- **O PASS** (+.198, perm-p .0002, dominant). **C PASS** (+.277, perm-p .0002, dominant) — the C
  recipe is now CONFIRMED full-roster with held-out CV + exact permutation; this retires the
  "Empath->diligence never full-roster confirmed" caveat and SUBSUMES the big5_textC_prereg
  confirmatory (same question, stricter test). **E PASS** (+.552, perm-p .0002, dominant) — with a
  genre-composition caveat: the criterion (broadcast engagement) and the corpus (which includes
  interview transcripts) share the interview modality, so part of the size is corpus composition,
  not disposition.
- **A MISS on dominance only**: own +.183 (perm-p .0004 — real signal) but pred_A reads C's
  criterion (+.210) and O's (+.197) slightly higher; cooperation/diligence/breadth intercorrelate
  behaviorally. The A text read is criterion-valid but not A-specific at this bar.
- **ES MISS**: own +.149 (0.001 under the +.15 bar, perm-p .0008) AND dominance fails (pred_ES
  anti-reads E's criterion at -.303 — media-visible members read as less stable in text). Criterion
  ladder honored: residual-GMP was VALID (ES model its strongest predictor, .149 vs E's .148); the
  affect-lability fallback was computed and is INVALID as a criterion (no model predicts it; ES
  model r = -.046) -> residual-GMP stands as the attempt of record; honest count unchanged.
- Against Pink's 0/5 (big5_pertrait_validity_prereg.md): supervising text features per-trait
  recovers REAL diagonal structure for O/C/E where the LLM trait scores had none. The defensible
  per-trait text claim is now: **O, C, E distinct and criterion-valid; A criterion-valid but not
  discriminant; ES neither (in text)** — ES's status rests on the cross-modal record, which as of
  2026-07-09 carries the gender-confound caveat (big5_es_robustness_prereg.md RESULT).
