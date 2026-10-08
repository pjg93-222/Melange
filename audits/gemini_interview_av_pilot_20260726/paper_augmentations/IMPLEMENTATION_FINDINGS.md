# V3 implementation findings

## Outcome

The paper-driven redesign materially improved media integrity and stored-turn
grounding, but it did not pass the preregistered diagnostic gates. The result
is a **no-go for production and no-go for Big Five/behavioral updates**. The
next iteration should repair the remaining timing and mismatch-detection
failures, then repeat the diagnostic before scaling.

## What was implemented

- Preserved all v2 media and results unchanged.
- Inventoried the actual streams of all 30 stored MP4s.
- Recovered the separate C-SPAN audio rendition for seven video-only files and
  muxed new, hash-pinned A/V repair copies.
- Extracted the exact stored target window for ten diagnostic cases.
- Produced ten 16 kHz mono WAVs, ten 16-frame silent storyboards, ten A/V
  clips, and two hidden cross-case A/V composites.
- Ran 30 primary, memory-reset Gemini Flash web evaluations plus two hidden
  mismatch controls.
- Withheld names, source titles, transcripts, party, chamber, and prior model
  output from every prompt.
- Validated exact media hashes, JSON structure, timestamps, modality
  abstention, prohibited inference, transcript grounding, and mismatch labels.

## Measured improvements

### Media integrity

V2 labeled all 30 files as audiovisual, but direct stream inspection found
only 23/30 actually contained audio. Flash had nevertheless returned audio
observables for all 30. V3 identified and repaired all seven missing-audio
cases before analysis, so the selected sample entered Gemini with 10/10
verified A/V sources.

### Target-turn grounding

On the paired ten-case diagnostic sample, the v2 excerpt matched the stored
target turn in 2/10 cases. V3 joint-A/V excerpts matched in 9/10, and
audio-only excerpts matched in 10/10. Seven of the eight deliberately selected
v2 failures were repaired; both aligned sentinels remained aligned.

This is a pipeline-repair result on known failures, not an estimate of
full-corpus accuracy.

### Modality discipline

All 10 audio-only receipts abstained on visual fields, and all 10 visual-only
receipts abstained on audio fields. This is substantially more diagnostic than
v2's single joint answer because unavailable-modality hallucination is now
directly testable.

### Receipt quality

Twenty-eight of 30 primary receipts were schema- and timestamp-clean after the
terminal validator hardening. The F004 A/V receipt placed multiple events at
116.5–125 seconds in an 85.8-second clip. F020 returned objects where the
schema required strings in `displayed_text`. Both failed closed. Zero receipts
contained prohibited trait inference.

## What did not improve enough

### Hidden mismatch detection

Flash detected M001 but missed M002, for 1/2 hidden mismatches:

- M001 was detected largely because visible lower-third text named Adriano
  Espaillat while the audio introduced Buddy Carter. This is an identity/text
  shortcut, not strong evidence of general synchronization skill.
- M002 combined Jamie Raskin video with Mark Pocan audio. Flash called it
  `matched`, claimed zero lag, and reported synchronized lip motion despite
  the deliberately crossed streams. That is a high-confidence false
  audiovisual attribution.

The result reproduces DAVE's warning: models can positively associate streams
without sufficient evidence.

### F018 exposes a source-label defect

The stored `cspan_out/turns.csv` row for F018 turn 37 is resolved to Jamie
Raskin, but the row text is the host introducing a Staten Island caller
followed by the caller's recommendation. V3 audio-only correctly transcribed
that stored row; the A/V pass separately observed Raskin's preceding words and
then the caller over shots of Raskin, classifying the pair as mismatched.

This is not a clean model miss. It reveals that the target-turn attribution is
wrong or overextended. F018 must be relabeled/split before reuse.

### Behavioral scales remain compressed

The ten A/V receipts still rated pace `medium` in 10/10 and prosodic
variability `medium` in 10/10. Disfluency varied slightly more than v2
(`low` 8, `medium` 2), but the coarse ordinal behavior fields remain highly
homogeneous. The papers improved diagnostic perception, not construct
validity for behavioral traits.

## Decision

Hard gates passed:

- 7/8 known semantic failures repaired;
- both sentinels retained;
- 10/10 audio-only and 10/10 visual-only condition discipline;
- at most one false mismatch among the ten nominal source pairs;
- zero prohibited inference.

Hard gates failed:

- primary receipt cleanliness was 28/30, not 30/30;
- hidden mismatch detection was 1/2, not 2/2.

Therefore:

- **No-go** for production Big Five, behavioral criteria, or cross-reference
  updates.
- **No-go** for a blind full-corpus extraction until F004 timing enforcement,
  F018 target attribution, and M002-style mismatch detection are repaired and
  rerun.
- The v3 harness itself is worth keeping: it found silent files,
  misattributed turns, out-of-bounds timing, and false synchronization claims
  that the v2 joint prompt did not expose.
