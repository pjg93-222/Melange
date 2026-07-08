# Big-5 Audio-Prosody Pilot — Pre-Registration

**Locked: 2026-07-08, BEFORE any audio is downloaded, any acoustic feature is computed, or any
outcome is seen. Committed to lock the bars (the P6 lesson: a pass judged on the wrong metric is a
false pass; every claimed pass is adversarially re-derived before promotion).**

## Motivation
The independent literature review (2026-07-08, big5_methods S12) graded the text psychology **A-/
high-A** within the elite-speech class, with two documented soft spots: Extraversion is volume-bound
(v2-E is talkativeness) and the **A-ES tone-halo (.65 vs a population .44)** is a TEXT artifact,
proven inseparable at the text level twice (P2 member-level, P7 chunk-level: removing it crushes the
C criterion too). Every prior round stayed inside the TEXT modality (lexical rates, genre-residualized,
stylometric, embeddings, LLM item-read) — all hit the text ceiling and could not break the halo.
**Acoustic prosody is the one untried modality, and it is literature-matched to exactly these two
weak spots:** Mairesse et al. (2007), the seminal speech-personality pipeline this niche descends
from, got its best results from prosody on **Extraversion (r .54) and Emotional Stability (r .47)**.
Because acoustic features are an INDEPENDENT source from text, they are the independent third indicator
the CT-CM halo model never had (collinear text-Blue is why CTCM/CTCM2 were under-identified).

## Design principle (de-risking)
**SOLO audio only — no diarization in the pilot.** The corpus is text/captions, not audio; the codebase
already establishes (attic/fetch_youtube_interviews.py) that per-speaker attribution on multi-speaker
media is the blocker, deferred to "a future Whisper+diarization pass." The pilot sidesteps that entirely
by using single-speaker audio, where the whole clip's prosody is unambiguously the member's:
C-SPAN floor-speech audio (single-speaker, presiding-officer-attributed, available for any floor-active
member) as PRIMARY; members' own-channel video (member_youtube.json) as supplement. The build spike
confirms which source yields the minimum audio per member; **this prereg locks the FEATURE SET, the
TEST, and the BARS — not the download mechanics.** Multi-speaker interview audio + Whisper diarization
is explicitly OUT of scope here (it is the scale-up if the pilot clears).

## Instrument
- **Features: eGeMAPS v02** (Geneva Minimalistic Acoustic Parameter Set, 88 functionals; openSMILE /
  opensmile-python) — the field-standard acoustic personality/affect feature set. Per solo clip ->
  88-dim functionals; per member = mean-pool across that member's clips; z-within-source.
- **Fit (independence intact):** ridge to the BEHAVIORAL dispositions only (A<-cooperation_z,
  C<-diligence_z, E<-visibility_z, O<-breadth_z), nested 5-fold, same protocol as b5_round4_eval.
  NEVER fit to pink/text (audio-on-text calibration is PROHIBITED, as blue-on-pink is).
- **Slice:** target **N=40** members with (a) >= **3 minutes** of clean solo audio, (b) existing text
  Pink + Blue scores, (c) behavioral dispositions. Deterministic selection: most solo-audio-minutes
  among the eligible. Report actual N and per-member minutes.

## Bars (ONE look on the pilot slice, both must hold to declare a win)
1. **INCREMENTAL VALIDITY (primary endpoint, criterion-anchored) — Extraversion.** E is pre-specified
   as the single primary trait (prosody's strongest per Mairesse; ours is volume-bound so audio has
   the most room). Both must hold:
   - audio-alone held-out r for E (vs visibility_z) **>= +0.15**, AND
   - text+audio fused held-out r for E exceeds text-alone by **>= +0.03** (a real increment, not
     redundant with text volume).
   A/C/O reported as secondary (no bar) to characterize breadth.
2. **HALO SEPARATION (the scientific payoff).** Build an a-priori theory-driven acoustic
   emotional-stability index from eGeMAPS (pre-specified, UNSUPERVISED, fitted to nothing):
   `ES_acoustic = -z(F0semitoneStddev) - z(jitterLocal) - z(shimmerLocal) - z(loudnessStddev)`,
   equal-weighted (low vocal variability/perturbation = vocally steady = ES+; standard affective-
   computing arousal/instability markers). With the criterion-fit audio-A, the **within-audio
   A-ES |r| <= 0.45** — materially below the text halo of .65 and approaching the RKH population truth
   .44. (Honest limitation, stated up front: audio-A is criterion-fit while audio-ES is theory-driven
   because no behavioral ES criterion exists — the same ES-anchor gap that constrained CTCM2; this is
   a directional halo test, not a full latent MTMM.)

## Outcomes
- **PASS (both bars):** acoustic prosody is a validated INDEPENDENT indicator that adds over text and
  is less halo-entangled. Documented; audio-A/E become the independent indicators for a cross-modal
  CT-CM (the concrete A- -> straight-A path). Any pass is **adversarially re-derived** (independent
  recomputation on a resampled/held-out split) before it is recorded as real — the P6 doctrine.
  Scale-up (interview audio + Whisper diarization) becomes a separately-prereg'd program, not built
  uninvited.
- **MISS (either bar):** audio prosody does not clear the pilot; text terminus stands; the modality is
  documented as tried-and-closed at pilot scale so no future session re-runs it. No number moves.

## Standing rules
One look on the pilot slice. Bars never move after any acoustic feature is seen. A miss reverts.
Audio is fit to behavioral targets only — audio-on-text/pink calibration is PROHIBITED (independence
is what gives a cross-modal agreement its meaning). Psychology remains DISPLAY-ONLY: even a pass feeds
no rank or engine; the payoff is measurement quality for the desk and the straight-A validation.

## Executability note (honest, 2026-07-08)
The pilot's only heavy external dependency is AUDIO ACQUISITION (network + yt-dlp/ffmpeg or a C-SPAN
fetch + storage); eGeMAPS extraction (openSMILE) and the ridge/MTMM math are light and local. If audio
download is unavailable in-session, the pipeline + this prereg are handed off to run as a background/
overnight job (the established collector pattern), with the ONE look taken only after the full slice's
features exist. The build spike (one member, end-to-end) gates the full run.
