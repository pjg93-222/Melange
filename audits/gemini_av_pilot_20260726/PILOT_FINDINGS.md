# Gemini 30-recording pilot findings

Date: 2026-07-26  
Status: `RESEARCH_CANDIDATE_NOT_CONSUMED`

## Decision

**NO-GO for scale-up, identity claims, or updating Big Five scores, behavioral
criteria, cross-references, narratives, or any other production output.**

Gemini demonstrated direct access to audio in a corrected nine-item isolated
diagnostic. The nominal 30-item run is not valid blinded identity evidence
because the CLI could access the private manifest. The corrected rerun was
stopped by Google's individual quota after 9/30 items; the service reports a
reset in about five days. This run did not validate visual analysis, open-set
voice identification, interview-specific behavioral analysis, or personality
inference.

## What ran

- Frozen cohort: the existing 30-row Wav2Vec benchmark.
- Media: 150.44 minutes of original WAV audio, losslessly preserved in neutral
  MP4 containers with blank visual frames.
- Model: Google Gemini 3.1 Pro High through the authenticated Antigravity CLI,
  high reasoning effort, one fresh conversation per item.
- Initial run flaw: the CLI received the whole audit directory, including the
  private manifest mapping neutral IDs to members. Prompt-based instructions
  did not enforce blinding.
- Corrected isolation: the rerun confined each model process to the neutral
  media directory and recorded the exact MP4 SHA-256. Nine items completed
  before the shared Gemini quota was exhausted.
- Candidate design: every item still supplied a shuffled, closed set of five
  names containing the recorded label, with an abstain option.

## Results and their valid interpretation

| Measure | Initial 30-item run | Corrected isolated rerun |
|---|---:|---:|
| Completed items | 30/30 | 9/30 |
| Verifiable media SHA-256 receipts | 0/30 | 9/9 |
| Valid fail-closed timestamps | 25/30 | 9/9 |
| Raw recorded-label matches | 27/30 | 8/9 |
| Matches after fail-closed validation | 22/30 | 8/9 |
| Abstentions | 3/30 | 1/9 |
| Blinding enforceable | No | Yes |
| Valid identity-accuracy estimate | No | No |

The initial 27/30 recorded-label result is retained as a diagnostic observation
only. It cannot be called accuracy: the manifest was exposed, expected labels
are weak, the answer was always present in a five-name set, and recordings
often say a member's name, state, district, committee role, or legislation.
The isolated 8/9 result still tests content-assisted closed-set matching, not
voice biometrics, and the sample is too small and selection-limited.

The Wav2Vec result of 11/30 used a different 30-member acoustic trial contract,
so a direct performance comparison is invalid.

## Independent grounding and repeat checks

- All nine corrected-isolation excerpts matched the project's existing caption
  cache under the post-primary exploratory overlap rule. Together with
  non-null media hashes, this supports access to those nine audio tracks. It
  does not validate identity.
- Five initial-run items and one repeat item contained at least one timestamp
  beyond the recording duration. The original scorer incorrectly accepted an
  item when any timestamp was valid. The scorer now fails an item when any
  timestamp is out of range.
- Repeat identity decisions agreed on 6/6 items, including the repeated
  abstention.
- Observable-delivery categories agreed on 32/36 fields (88.9%).
- Estimated speaker count matched exactly on 5/6 repeats and was within one on
  all six.
- Mean absolute identity-confidence change was 0.0133.

The repeat subset belongs to the manifest-exposed run, and the caption-overlap
rule was formalized after the primary run. Neither is confirmatory evidence.

## Behavioral-output warning

The delivery ratings were strongly compressed:

- pace: 27 medium, 3 low;
- pause frequency: 24 medium, 3 low, 3 high;
- disfluency frequency: 26 low, 4 medium;
- prosodic variability: 29 medium, 1 high;
- turn competition: 29 low, 1 medium; and
- response directness: 17 high, 1 medium, 12 not observable.

This limited spread is unsuitable for updating member-level behavioral or Big
Five measures. The model also estimated more than one speaker in 17/30 files,
whereas the legacy review marked all 30 as solo-target matches. That
disagreement requires diarization and human boundary review before behavioral
features can be assigned to any member.

## Scope limits discovered during reconciliation

1. The frozen corpus comes from the legacy floor-speech-biased audio pilot,
   with some hearing or mixed-speaker material. It is not a validated
   30-interview corpus.
2. The MP4 visual track was intentionally blank. No claim about faces, gesture,
   gaze, posture, visual turn-taking, or full audiovisual analysis was tested.
3. Candidate identities were supplied. Open-set speaker identification was not
   tested.
4. Expected identities are machine-caption/folder expectations, not
   independently human-ratified labels.
5. `P004` is a concrete label-quality warning: the expected member is Nicole
   Malliotakis, while the excerpt refers to a "daughter of New Mexico."
6. Observable speech delivery is not a Big Five measurement. Any mapping needs
   a separate, preregistered validation study with context and venue controls.
7. A provider retention/deletion record was not available for this run.

## Gate disposition

The original four technical gates are invalidated by the blinding and timestamp
defects. The corrected diagnostic completed only 9/30 because of quota. The
correct next step is limited to the human-gold audiovisual preparation
described in `SCALE_UP_PREPARATION.md`; no full-corpus model run should start.
