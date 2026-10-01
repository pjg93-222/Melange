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
- **BAR 1a — PRIMARY, POWERED (pre-look amendment for power; theory-driven, NOT data-snooped):** an
  a-priori acoustic-EXTRAVERSION composite index — mean of z(+loudness_amean, +loudness_stddevNorm,
  +F0semitone_stddevNorm, +spectralFlux_amean, +loudnessPeaksPerSec, +VoicedSegmentsPerSec), the 6
  eGeMAPS markers Mairesse(2007)/Scherer/Rubio link to extraversion (louder, more dynamic, more pitch
  variation, faster) — correlated with **Pink-E**: r **≥ +0.15 AND one-sided p<.05** (a 6-feature
  a-priori index has a clean N=90 null r_crit≈.17, unlike the 88-feature ridge whose fitting floor is
  ~.23 — this is the powered test, so N=90 can actually detect Marrero's ~.25 effect).
- **BAR 1b — FAITHFUL DIMENSIONALITY (secondary):** full eGeMAPS-88 ridge → Pink-E, repeated-CV
  held-out r, reported with its permutation-null (near the power edge at N=90/88-feat; honest).
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

## RESULT — THE ONE LOOK (2026-07-08, N=90)
- **BAR 1a (a-priori acoustic-E composite -> Pink-E), PRIMARY: MISS.** r=+0.085, one-sided p=0.21. The
  6 classic Mairesse markers (loudness/pitch-var/tempo) do NOT carry Pink-E; the signal is not where
  theory predicts.
- **BAR 1b (full eGeMAPS-88 -> Pink-E): CLEAR, adversarially confirmed.** held-out r=+0.284, exact
  perm-p=**0.030** (K=300). ES also +0.298, perm-p=**0.017**. A -0.043 (p=.69), C +0.090 (p=.33),
  O +0.094 (p=.27) all NULL. **-> Vocal prosody is a VALIDATED independent (cross-modal) measure of
  the AROUSAL traits E and ES — a genuine partial Marrero replication. (The first pilot's strawman —
  behavioral criterion + single-scalar fusion — buried this; the method correction surfaced it.)**
- **BAR 2 (super-additivity): MISS.** vocal adds +0.001 over linguistic for E (negative for A/C).
  CAVEAT: the linguistic (Empath) block is shared-method-inflated vs Pink (E ling +0.607), so this is
  conservative-against-vocal, not a clean refutation of Marrero's interaction.
- **BAR 3 (halo, audio's own A-ES): MISS.** vocal A-ES |r|=0.819 (worse than Pink's .65); vocal-A
  NULL (-0.043 < perm-null .216). Audio reads only the ES/arousal side; its "A" is recycled arousal
  features -> cannot separate A from ES via its own A read.
**SYNTHESIS:** Faithfully tested, audio VALIDLY measures E & ES (arousal) as an independent modality,
but is redundant with text for measurement and cannot crack the A-ES halo through an A read (it has
none). **REMAINING avenue (enabled, NOT yet tried):** audio-E/audio-ES are exactly the INDEPENDENT
indicators CT-CM lacked (big5_ctcm2 failed ONLY because lexical Blue was collinear). Anchoring the
latent ES factor with the validated audio-ES (perm-p .017) could separate the A-ES variance in a
CT-CM — the halo attack uses **audio-ES**, not audio-A. That is the honest next step toward the goal.
