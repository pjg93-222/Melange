# Audio × Personality — FAITHFUL Marrero-style replication (pre-registration)

**Locked 2026-07-08 BEFORE the look. Reason: the first audio pilot (big5_audio_prereg.md) did NOT
follow the papers — it predicted BEHAVIORAL visibility (not personality) and "fused" the 88 audio
features with a SINGLE text-E scalar (not a linguistic feature block), so it could not test Marrero's
super-additivity and its MISS was a strawman. This design follows Marrero, Gosling, Pennebaker &
Harari (2022, Acta Psychologica): predict PERSONALITY from a VOCAL block + a LINGUISTIC block + their
JOINT model, and report the vocal/linguistic/joint variance decomposition (their 3.13% / 6.24% /
10.67%). New design -> new bars; the iteration-across-designs rule licenses it.**

## Sample & blocks (N=90 = audio ∩ Pink ∩ speech-text; all present, verified)
- CRITERION = **Pink** (big5_llm_opus.json, the A− LLM item-read) per trait — the best legislator
  personality read available (no self-report BFI exists for senators; Marrero's BFI is unobtainable
  here). Pink is IMPERFECT (reliability ~.67), so measurement error ATTENUATES the audio↔personality
  correlation — a PASS is therefore strong; a MISS is ambiguous (could be Pink's noise). Stated up front.
- VOCAL block = eGeMAPS v02 (88 functionals, b5_audio_cache.json). **INDEPENDENT of Pink (different
  modality) -> vocal→Pink is a CLEAN cross-modal convergent test.** This is the primary.
- LINGUISTIC block = Empath categories from each member's speech text (reuse the model's featurizer).
  **SHARES SOURCE with Pink (both from the member's text) -> linguistic→Pink is shared-method inflated.**
  So the super-additivity test is reported WITH that caveat; linguistic-alone is a shared-method
  ceiling, not a clean comparator.
- Method: ridge, repeated 5-seed × 5-fold CV, held-out r per trait; permutation null (K≥100) as the
  N-aware significance floor. Report vocal / linguistic / joint held-out r (and r²) for all 5 traits.

## Bars (ONE look, locked; all 5 traits reported regardless)
- **BAR 1 — PRIMARY (clean cross-modal convergent):** VOCAL-alone predicts **Pink-E** with held-out
  r **≥ +0.15 AND > permutation-null 95th** (significant). E is pre-specified primary (prosody's
  strongest trait: Mairesse/Rubio acoustic-E .47–.54). Marrero vocal-alone ≈ 6.24% var ≈ r .25.
- **BAR 2 — SUPER-ADDITIVITY (Marrero's headline, caveated):** JOINT (vocal+linguistic) held-out r
  for E **> LINGUISTIC-alone by ≥ +0.03** — does vocal ADD beyond language. Reported WITH the
  shared-method caveat (linguistic is inflated vs Pink, so this bar is conservative-against-vocal).
- **BAR 3 — HALO (the real prize):** the vocal→Pink models yield a vocal-A and a vocal-ES read;
  |corr(vocal-A, vocal-ES)| **< 0.45** (vs Pink's own A–ES entanglement ~.65) AND vocal-A is itself
  valid (vocal-A held-out r > its perm-null). A low A-ES is meaningless if vocal-A is noise (the gate).

## Outcomes
- **PASS Bar 1:** audio MEASURES personality cross-modally (Marrero replicated) — a real positive, and
  audio becomes the INDEPENDENT third indicator the CT-CM halo model lacked (earlier CT-CM failed only
  because lexical Blue was collinear). That is the concrete route to cracking the A–ES halo → the
  straight-A / load-bearing question. Adversarial P6 re-derivation before it is recorded.
- **PASS Bar 3:** direct evidence the acoustic modality separates A from ES — wire audio as the CT-CM
  identifying indicator (separate ratified step).
- **MISS:** documented as a FAITHFUL (not strawman) negative; audio genuinely does not carry the signal
  at N=90 against the Pink criterion (with the attenuation caveat). Text terminus stands.

## Discipline
Locked + committed BEFORE the look. One look; misses revert; bars never move after data is seen.
Vocal block never sees Pink at fit time except as the ridge target (that IS the convergent test).
Any PASS is adversarially re-derived (independent recomputation) before it is recorded (the P6 lesson).
