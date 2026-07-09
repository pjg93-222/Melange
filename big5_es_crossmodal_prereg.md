# ES cross-modal validity — the held-out re-test (pre-registration)

**Locked 2026-07-09 BEFORE the look. Motivated by the es-voice-recheck workflow (32 agents, 21/24
findings survived adversarial verification), which established two things: (1) our COMMITTED acoustic-ES
composite in b5_audio_ctcm.py / b5_audio_eval.py was MIS-SIGNED (folk "steady/clean voice = calm"; the
features actually track ES the other way in clean data), so the earlier -0.165 was real signal read
upside-down; (2) the literature on voice->neuroticism DIRECTION is genuinely contradictory (arousal-state
strand: high F0 = anxiety = low ES; trait strand incl. Mairesse 2007: high N = LOW F0; Stern et al. 2021
n=2217 = NULL), and N is the hardest Big-Five trait to read from voice (~15% variance ceiling, depression-
confounded). Because the direction is contested, ANY hand-signed composite is a p-hacking hazard — the
workflow's own +0.195 recommendation was computed on the same rows it proposed to test. So this test
REMOVES sign-choice from the analyst entirely.**

## Data
- N = 395 identity-verified clean voiceprints (b5_audio_cache.json, eGeMAPS v02, 88 functionals,
  z-within-source). Text criterion from big5_v2.json (the behavior-calibrated instrument; ES == -N exactly).

## Method (fixed a-priori — the committed CV protocol, NO analyst sign choice)
- Features: **all 88 eGeMAPS functionals** (no feature selection, no manual composite, no manual signs —
  the whole point is that the model learns the weights/directions, not me).
- Model: **Ridge**, nested CV — inner GridSearchCV over ALPHAS=[1,3,10,30,100,300,1000] (3-fold),
  outer 5-fold, out-of-fold predictions averaged over SEEDS=[7,17,29,43,61]. (Identical protocol to
  b5_behavioral_instrument.py — a-priori, already in the repo.)
- Target (PRIMARY): **big5_v2 ES** trait z. Target (SECONDARY, reported not gating): Pink LLM ES
  (to compare against the contaminated held-out +0.298).
- Metric: **held-out (out-of-fold) Pearson r** between the ridge prediction and the target.
- Null: **5000 label permutations** of the target -> one-sided permutation p on the held-out r.
- Discriminant (halo guard): the SAME voice->ES model's held-out predictions must correlate with
  big5_v2-ES MORE than with big5_v2-A (r_ES > r_A), so a pass is ES-specific, not a generic
  evaluative/agreeableness halo (that halo is what sank the CT-CM latent model).

## Pass rule (ONE look, locked)
ES cross-modal validity PASSES iff ALL:
1. held-out r(pred, big5_v2-ES) **>= +0.15** and right-signed (+);
2. permutation p **< 0.01**;
3. discriminant: r(pred, big5_v2-ES) **>** r(pred, big5_v2-A).
Point estimate is expected MODEST (literature true ceiling ~0.15-0.30 for N from voice; this is voice-vs-
text-model convergence, not voice-vs-ground-truth). MISS on any = ES stays measured-but-unvalidated,
documented honestly. NO re-running with a different target/feature set after unblinding.

## Why this is honest where the workflow's composite was not
Held-out CV cannot be sign-hacked: the model fits weights on training folds and is scored on data it
never saw, so a spurious in-sample sign flip does NOT transfer. If voice genuinely carries ES-specific
signal, it survives out-of-fold + permutation; if the -0.165->+0.195 swing was feature/sign fishing, it
collapses out-of-fold. The analyst chooses NO signs. One look; misses revert; bars fixed before data.

## Discipline
Locked + committed BEFORE the look. Method = the repo's existing CV protocol (no new degrees of freedom).
Any PASS adversarially re-derived. The pressure (user believes ES was validated) makes these guards MORE
binding, not less. big5_v2 targets are never fit to audio (they ARE the independent criteria).

## RESULT — THE ONE LOOK (2026-07-09, N=395)
**PASS on all three bars.**
- BAR 1: held-out r(ridge_pred, big5_v2-ES) = **+0.208**, right-signed. CLEAR (>= +0.15).
- BAR 2: permutation p (5000 label perms, one-sided) = **0.0002**; parametric p = 0.0000. CLEAR (< 0.01).
- BAR 3: discriminant r(pred, ES)=+0.208 **>** r(pred, A)=-0.030. CLEAR — ES-specific, not an A-halo.
- Secondary: the big5_v2-ES model's held-out preds vs Pink-ES = +0.170 (same sign as the contaminated
  ridge->Pink-ES +0.298, weaker & clean).
**VERDICT: ES is cross-modally VALIDATED** — clean-audio voice predicts the text-ES read out-of-fold,
ES-specifically. Effect is modest (~4% variance) = the literature's true N-from-voice ceiling, not
inflated. This SUPERSEDES the mis-signed acoustic-ES composite in b5_audio_ctcm.py / b5_audio_eval.py
(whose -0.165 was real signal read upside-down). All five traits now validated: A/C/E/O behaviorally +
ES cross-modally. Caveats: voice<->text-MODEL convergence (not ground truth); minor C-overlap.
