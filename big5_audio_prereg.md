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

## Addendum 1 (2026-07-08, external confirmation — NO bar changed, no outcome seen)
User-provided references CONFIRM the design: Rubio et al. 2024 Sensors (voice->Big5 r.3-.5;
Extraversion the most voice-externalized trait self-report .47/expert .48 — validates the E-primary
endpoint; openSMILE; observer-criterion; O weakest); Marrero et al. 2022 Acta Psych (vocal 6.24% var
> text-LIWC 3.13%, joint 10.67% SUPER-ADDITIVE — audio complements text; A carried MORE by voice than
text = halo-relevant; E/C/N best, O worst); Simchon et al. 2024 PNAS Nexus (personality-MATCHED
persuasion works r~.17 — the case for making psychology load-bearing IF the pilot proves fruitful).
Citations only; every bar stands.

## Addendum 2 (2026-07-08, code audit + integration smoke — NO bar changed)
Self-audit (7 fixes: dead code, scale-unfair fused ridge -> z the text col, 0-imputed missing text ->
restrict to text-having members, z-score NaN <2 members, non-PCM wav duration, dead imports) + a full
`run()` integration smoke on the 40 real members with RANDOM audio. **Pre-look robustness fixes to how
the LOCKED quantity is measured (not the bar): (1) repeated 5-seed CV** (a single split at n~40 is
high-variance — random cleared +0.15 on one seed; repeated CV -> ~0); **(2) a permutation noise-floor
diagnostic** printed beside the primary bar.
**POWER FINDING (material): at N=40 with 88 eGeMAPS features the fair permutation noise floor (95th
pct, repeated-CV) = r +0.267 — ABOVE the locked audio-alone bar (+0.15), and the expected real effect
(Marrero/Rubio r~.25-.33) sits AT that floor.** The pilot as pre-registered is UNDERPOWERED: a genuine
signal could not be separated from chance, and noise can clear +0.15. **RECOMMENDED pre-look amendment
(pending user ratification; acquisition has NOT run): (A) PCA-reduce eGeMAPS 88 -> ~10-15 components
before ridge (standard for n<<p; sharply lowers the floor so +0.15 is meaningful at N=40), and/or
(B) raise N to ~90+.** The three BARS are unchanged; only the design's dimensionality/N is under review.
Until ratified, the perm-null diagnostic + the P6 re-derivation guard against a within-noise false pass.

## Addendum 3 (2026-07-08, user "pursue the most optimal adjustment" — PCA REFUTED; N + significance fix)
Addendum 2's recommended PCA fix was TESTED on the random-audio harness and **REFUTED**: at N=40 the
permutation noise floor is +0.267 with no PCA but +0.34-0.36 with PCA k=5/8/10/15 (PCA let ridge
under-regularize the few noise components). **Diagnosis: the +0.267 floor = 1.645/sqrt(40) = the
sampling limit of a correlation at n=40 — an N problem, not a dimensionality problem. Feature
engineering cannot fix it; only samples can.** RATIFIED adjustment (stricter than the original, both
pre-look): **(1) the audio-E pass now REQUIRES clearing +0.15 AND exceeding the permutation-null 95th
pct (one-sided p<.05) — an N-aware significance gate wired into `pass` (b1a), not just the fixed bar;
(2) target N raised to >=80** (r_crit ~= 1.645/sqrt(80) ~= .18, so the expected .25-.33 effect from
Marrero/Rubio becomes detectable above the floor; fetch --eligible now defaults to 80). The three
numeric bars (+0.15, +0.03, <=0.45) are UNCHANGED; the significance gate + N are added rigor. The
incremental-delta and A-ES tests remain higher-variance and are best read at the larger N. Net: the
pilot is now honestly powered; a within-noise result cannot register as PASS.

## Addendum 4 (2026-07-08, acquisition UNBLOCKED + Bar-2 gate + test run — NO bar changed)
**In-sandbox acquisition is no longer a handoff:** the YouTube CDN 403 is bypassed with the
ios/web_safari/android player-client fallback (format 18 -> extract wav). b5_audio_fetch gained an
autonomous `--search` mode (ytsearch floor-speech clips per member, solo-biased/C-SPAN-dominant,
resumable via yt-dlp download-archive, rate-limited). **SOLO caveat (honest):** search-fetched floor
clips are single-speaker by the nature of floor speech but are NOT own-channel-verified — a pilot
limitation vs the own-channel guarantee (news/panel clips would contaminate the acoustic sample);
documented, not hidden. **Bar-2 rigor gate (stricter, pre-look):** halo-separation now REQUIRES audio-A
to be a VALID measure (audio-A held-out r > its permutation null) before a low A-ES counts — else the
separation is vacuous (random audio 'separates' trivially). **TEST RUN (--search 3) PASSED the
machinery check:** real C-SPAN floor audio (Pelosi 2319s / M.Johnson 920s / AOC 2026s) -> b5_audio_build
produced real eGeMAPS (88 feat, all non-zero). Fetch+build now proven on REAL audio; eval machinery was
already validated. **FULL RUN in progress: --search 90 (buffer over N>=80) -> build -> the ONE look.**
No bar changed; a PASS still gets adversarial P6 re-derivation before it is recorded.

## RESULT — THE ONE LOOK (2026-07-08, N=90, MISS; pilot CLOSED)
Full run: --search 90 -> 90 members cleared the 180s floor -> parallel eGeMAPS build (NaN-clip drop +
z winsorized to +/-5) -> b5_audio_eval, one look. **MISS on both bars:**
- BAR 1: audio-alone E held-out r = **+0.228** (real-ish, in the Marrero/Rubio band) BUT permutation
  noise floor 95% = **+0.234** -> WITHIN NOISE (not significant at N=90/88-feat). And text-alone E .258
  vs fused .254 -> **delta -0.004**: audio adds NOTHING incremental over text. Audio-E is REDUNDANT
  with the text instrument, not complementary (Marrero super-additivity was self-report; did not
  transfer to our behavioral criterion / legislators). Secondary audio-alone: A +0.129, C -0.081, O -0.059.
- BAR 2: within-audio A-ES |r| = 0.100 (low) BUT audio-A NOT valid (+0.129 < its null +0.165) ->
  separation VACUOUS (no A signal to entangle). The Bar-2 validity gate correctly caught this.
**Discipline note:** audio-E +0.228 WOULD have cleared the original naive +0.15 bar; the significance
gate (Addendum 3) flagged it within-noise, the incremental bar showed no lift over text, and the NaN/
winsorization fixes kept it real -> an honest NEGATIVE, not a false positive. **Text terminus stands;
psychology unchanged; DISPLAY-ONLY; no number moves.** Pilot CLOSED. Audio is NOT the lever to a
straight-A or to load-bearing. Scale-up (interview audio + diarization) NOT pursued — the pilot's own
E signal is redundant with text, so more audio of the same kind won't add. Real load-bearing avenues
live elsewhere (N-channel upgrade to Pink; incremental-validity gate vs observed movement).
