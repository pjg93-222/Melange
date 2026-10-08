# Audiovisual interview-analysis paper synthesis

## Executive finding

The three papers support a diagnostic redesign, not a more elaborate
personality prompt. Reliable audiovisual analysis requires atomic
single-modality tests, explicit temporal and cross-modal consistency tests,
negative controls, evidence attribution, calibrated abstention, and
task-specific metrics. A fluent joint A/V answer is not evidence that a model
used both streams.

This directly changes the congressional-interview pilot: the v2 receipts are
useful feasibility artifacts, but they cannot validate speaker behavior or
Big Five updates. V3 therefore isolates perception and keeps every production
consumer disconnected.

## DAVE: Diagnostic Benchmark for Audio Visual Evaluation

Source: *NeurIPS 2025 DAVE: Diagnostic Benchmark for Audio Visual Evaluation*.

- Existing audiovisual benchmarks are often visually answerable, so aggregate
  accuracy can conceal failure to integrate sound and vision. DAVE constructs
  questions for which neither modality alone is sufficient and decomposes the
  task into constituent capabilities (pp. 2, 5).
- Its composite tests cover multimodal synchronization, sound absence, and
  sound discrimination. Atomic tests cover action recognition, temporal
  ordering, and audio discrimination (pp. 5–6).
- Human accuracy was `84.74 ± 2.26%`; Gemini 2.5 Flash reached
  `58.73 ± 1.04%` overall, with `59.15%` synchronization, `70.69%` sound
  absence, and `44.21%` sound discrimination (p. 7).
- Some models strongly associated audio and visual events even when the
  queried sound was absent. The paper argues for explicit mismatch/absence
  mechanisms rather than assuming correspondence (pp. 7–8).
- Visual action recognition was substantially stronger than joint
  synchronization, locating the bottleneck in temporal cross-modal
  integration rather than basic visual recognition (p. 8).
- Modality ablations confirmed that full A/V performs better than video-only
  or audio-only. Conditional analysis showed that correct visual recognition
  and temporal ordering contributed more to joint success than correct audio
  classification alone (p. 9).

Implementation consequence: score audio, visual, temporal, and composite
tasks independently; include audio-absence and hidden mismatch controls; fail
the composite when required atomic evidence is missing.

## Gemini: A Family of Highly Capable Multimodal Models

Source: *Gemini: A Family of Highly Capable Multimodal Models*,
arXiv:2312.11805v5.

- Gemini is trained natively across text, images, audio, and video. Video is
  represented as a sequence of frames, while audio is represented separately
  from 16 kHz signals (pp. 14–16).
- The report's video benchmark protocol sampled 16 equally spaced frames per
  clip and used task-specific captioning or question-answering metrics rather
  than a single prose-quality score (p. 16).
- Audio capabilities were evaluated separately with ASR word/character error
  rates and translation BLEU, including qualitative error analysis for proper
  nouns and rare words (p. 18).
- Factuality was decomposed into correctness, attribution to supplied context,
  and hedging when an answer was not supported. Human evaluation and explicit
  adaptation improved all three dimensions (pp. 11–12).

Implementation consequence: use a deterministic 16-frame visual condition,
keep audio as a separate 16 kHz derivative, measure transcript grounding and
source attribution directly, and require `not_observable` rather than forcing
answers.

## Early Exploration into AI-Assisted Visual Analytics for Dynamic Videos

Source: *Early Exploration into AI-Assisted Visual Analytics for Dynamic
Videos* (IEEE VIS×GenAI 2025 workshop).

- The exploratory study used five videos and three versions of each:
  original A/V, audio-only, and silent video, producing 15 stimuli. It used a
  strict memory reset between conditions (p. 3).
- General-purpose models could separate modalities but could not reliably
  segment by time, so the authors manually selected high-information scenes
  (p. 3).
- Audio prompts targeted spoken information; silent-video prompts targeted
  visible cues; joint prompts explicitly requested synthesis and
  inconsistency detection. Prompts were iterated to recover omissions
  (pp. 3–4).
- Gemini 2.5 Pro was comparatively consistent across audio and visual
  conditions, while the models still showed audio extraction failures,
  incomplete visual interpretation, numeric/OCR errors, and trouble tracking
  dynamic trajectories (pp. 3–4).
- The paper organizes video difficulty by data type, data dynamics,
  visualization presence, and A/V alignment, and calls for task taxonomies,
  temporal synchronization, visualization-aware prompting, and explicit
  treatment of complementary, redundant, irrelevant, or misaligned channels
  (pp. 1–4).

Implementation consequence: use fresh conversations for each condition,
separate observation from integration, label the relationship between
channels, and allow one omission-recovery pass only after validating the first
receipt.

## Adopted augmentations

1. Ten-case paired repair sample: all eight known v2 semantic failures plus
   two aligned sentinels.
2. Thirty primary Flash calls: audio-only, 16-frame visual-only, and A/V for
   every case in a fresh session.
3. Two hidden mismatched A/V composites.
4. Blind case IDs: no expected name, source title, transcript, party, chamber,
   or prior output in prompts.
5. Strict JSON with atomic audio/visual/temporal outputs, joint consistency,
   condition-specific abstention, and timestamped evidence.
6. Hash-pinned source and derivative media; fail-closed stream inventory.
7. Paired comparison to v2 for target-text grounding, timestamp validity,
   modality evidence, mismatch detection, and output specificity.
8. No production or Big Five path. Human event coding remains mandatory
   before claiming behavior-measure accuracy or construct validity.

## Immediate implementation discovery

The new stream gate found that 7/30 v2 MP4s had video but no audio:
F004, F006, F011, F013, F020, F021, and F025. Nevertheless, v2 reported
audio observables for all 30 cases. C-SPAN's master playlists expose audio as a
separate rendition; the earlier downloader had selected the 360p video
playlist without muxing that audio.

V3 preserves the original v2 files, downloads only the corresponding C-SPAN
audio segments, muxes repaired copies, verifies both streams, and pins new
hashes before any Gemini call. This is already a material improvement:
unsupported audio analysis is now structurally impossible to admit.
