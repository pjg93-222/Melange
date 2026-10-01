# Audio round 2 — nail down C (valid criterion) + CT-CM halo attack (pre-registration)

**Locked 2026-07-08 BEFORE the look. Two motivations, both from the articles the user gave:**
1. **C error:** the faithful pilot tested audio→**Pink-C**, but text-C is invalid (5-method null), so a
   null there is uninformative — I was predicting a broken target. Marrero(2022) & Rubio(2024) both got
   C from voice against **valid** criteria (self-report NEO-FFI / expert / close-other). Our valid C
   criterion is **behavioral diligence** (diligence_z: roll-call + LEP follow-through + CHRG). Voice and
   behavior share NO method → the cleanest possible test.
2. **Halo:** audio-ES is a validated INDEPENDENT indicator (faithful result perm-p=.017) — the thing
   CT-CM lacked. Anchor the latent ES factor with it.

## TEST A — nail down C against the VALID criterion (Marrero/Rubio-faithful)
Blocks: VOCAL (eGeMAPS-88) + LINGUISTIC (Empath) → **diligence_z** (behavioral C). Also report the
other traits vs their behavioral analogs (cooperation=A, visibility=E, breadth=O) for context. Ridge,
repeated 5×5 CV, held-out r, exact permutation p (K≥300). **Both blocks are clean here** (neither shares
method with the behavioral criterion — unlike the Pink-based test).
- **BAR A1 (does voice measure C):** vocal→diligence held-out r **≥ +0.15 AND exact perm-p < .05.**
- **BAR A2 (super-additivity, CLEAN):** joint (vocal+linguistic) → diligence **> linguistic-alone by
  ≥ +0.03** — the clean Marrero interaction test (no shared-method confound here).
- Report vocal / linguistic / joint decomposition for diligence. If vocal clears A1, that is the first
  valid-criterion C signal from any modality (text-C failed against votes; voice may succeed).
- **MFCC fallback (pre-declared):** if eGeMAPS-88 vocal→diligence is null, it is NOT yet a C verdict —
  Rubio used MFCC/spectral (voice-quality) features, which eGeMAPS functionals summarize away; a
  documented follow-up (not this look) would test an MFCC block before C-from-voice is closed.

## TEST B — CT-CM halo attack with the validated audio indicator
CT-CM latent (semopy) with **audio-E and audio-ES as the independent (non-text) indicators** alongside
Pink(raw_z) + behavioral; orthogonal Pink METHOD factor. Audio is the identification CT-CM lacked
(big5_ctcm2 failed only because lexical Blue was collinear). Instruments' own scores UNTOUCHED.
- **BAR B1:** latent **A-ES |r| ≤ 0.50** (vs Pink's .65) — the halo separated by the independent anchor.
- **BAR B2:** latent **C vs votes_cast Spearman ≥ +0.15** (keep the earned criterion).
- **BAR B3:** no Heywood, on-trait loadings positive incl. the audio indicators, converges.
- PASS all → ship big5_latent.json (desk overlay) + audit guard (separate ratified step). MISS → documented.

## Discipline
Locked + committed BEFORE the look. One look per test; misses revert; bars never move after data seen.
Any PASS adversarially re-derived (independent recomputation) before it is recorded (P6). Instrument
independence intact (audio never fit to Pink except as the convergent target; behavioral never fit to text).

## RESULT — THE ONE LOOK (2026-07-08, N=90/89)
**TEST A (nail down C):**
- BAR A1 (VOICE measures C): **MISS.** vocal->diligence held-out r=-0.081, exact perm-p=0.73. Voice does
  NOT measure C (Rubio MFCC fallback remains the only untried voice-C route; not pursued this look).
- BAR A2 (super-additivity): MISS (vocal adds -0.046 to linguistic for C).
- **EXPLORATORY FINDING (not the pre-registered bar, which was voice — flagged as exploratory):** the
  LINGUISTIC block (Empath) -> behavioral diligence = **+0.348, perm-p=.003 (K=300)**, CROSS-method
  (text vs voting/follow-through, no shared source). Party-controlled: **partial r=+0.355, p=.0004**,
  party-alone->diligence only -0.115, holds WITHIN-D (+0.378) and WITHIN-R (+0.324) -> NOT party-proxy.
  **-> TEXT DOES measure C against the valid behavioral criterion.** Overturns the campaign's "text
  can't measure C" (which tested the wrong thing: a pre-built lexical-C CONSTRUCT vs votes, reversed).
  Marrero/Rubio-faithful (predict against a valid criterion). CONFIRMATORY step to lock it: full roster
  (500+, not just these 90), held-out split, seniority + party controls, pre-registered.
- Context: vocal ADDS to text for E against behavioral visibility (+0.119) — a clean super-additivity
  win for E (unlike vs Pink where it was redundant).

**TEST B (CT-CM halo attack): MISS.** latent A-ES |r| = **0.946** (WORSE than Pink's .65); audio-ES
loaded negatively and is too weak (r=-.25) to anchor the ES factor; Heywood clean, converged, but B3
fails on the negative audio_ES loading. latent C vs votes +0.301 (B2 clear, criterion preserved).
**Third CT-CM failure (lexical Blue, embedding Blue, now audio-ES) -> the A-ES halo is irreducible at
the latent level with available indicators. Closed.** No overlay shipped; instruments untouched.
