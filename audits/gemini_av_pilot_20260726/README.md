# Gemini congressional-recording audio capability pilot

Status: `RESEARCH_CANDIDATE_NOT_CONSUMED`

This directory contains a frozen, research-only pilot for 30 congressional
recordings. It must not update Big Five traits, behavioral criteria, member
cross-references, narratives, or production dashboards.

## Scope correction recorded after the run

The frozen benchmark is the project's legacy, floor-speech-biased audio pilot,
with some hearing or mixed-speaker material. It is not a human-validated set of
30 interviews. The MP4 files supplied to Gemini contain the original audio with
a neutral blank visual track, so this run tests auditory media processing—not
facial, gesture, gaze, or other visual analysis. These limits were discovered
during reconciliation and are carried into the final interpretation.

The initial 30-item execution also exposed the entire audit directory to the
model process, including the private manifest, and its timestamp gate accepted
items with a mixture of valid and impossible timestamps. Those results are
retained only as invalidated diagnostics. The corrected run confines the model
to neutral media, records MP4 hashes, and fails closed on timestamps; it
completed 9/30 before the shared Google quota was exhausted.

## Purpose

Test whether Google Gemini can:

1. directly process the recorded audio/video;
2. distinguish a dominant speaker from panels or mixed-speaker recordings;
3. match the dominant speaker to a blinded five-person candidate set, with an
   explicit abstain option; and
4. return timestamped, observable delivery features without converting those
   observations into personality, emotion, clinical, demographic, or protected
   attribute claims.

## Frozen cohort

The cohort is the existing 30-row
`audio_wav2vec_30member_scores.csv` benchmark. Reusing it enables a direct
comparison with the local Wav2Vec weak-label pilot and avoids choosing cases
after seeing Gemini output.

Each recording is exposed to Gemini under a neutral ID (`P001` through `P030`).
The member folder, YouTube ID, source URL, prior prediction, and expected label
are withheld from Gemini. The private `manifest.json` keeps the mapping for
scoring after all responses are recorded.

The expected member names are existing machine-caption/folder labels, not
human-ratified identity gold. Identity results are therefore reported as
agreement with the recorded label, never as definitive biometric
identification. A Gemini disagreement cannot relabel a recording; it can only
flag it for human review.

## Required response

One JSON object per pilot item:

```json
{
  "pilot_id": "P001",
  "media_processed": true,
  "modality": "audio",
  "estimated_speaker_count": 1,
  "dominant_speaker_fraction": 0.92,
  "candidate_choice": "Candidate Name",
  "identity_confidence": 0.74,
  "abstained": false,
  "observable_delivery": {
    "pace": "medium",
    "pause_frequency": "low",
    "disfluency_frequency": "low",
    "prosodic_variability": "medium",
    "turn_competition": "not_observable",
    "response_directness": "not_observable"
  },
  "evidence": [
    {
      "timestamp_sec": 18.2,
      "observation": "brief pause followed by faster delivery"
    }
  ],
  "transcript_excerpt": "maximum twenty words",
  "quality_flags": [],
  "error": null
}
```

Allowed categorical values are `low`, `medium`, `high`, or `not_observable`.
The model must abstain when the media or identity evidence is insufficient.

## Predeclared pilot gates

- Media processing: at least 27 of 30 items must be directly processed.
- Schema completion: at least 27 of 30 responses must pass local validation.
- Evidence grounding: at least 24 of 30 processed items must include at least
  one plausible timestamped observation.
- Recorded-label agreement: reported with Wilson 95% interval; a provisional
  scale-up requires at least 24 of 30 matches. This is not a production identity
  gate because the labels are not human gold.
- Abstention is scored separately and is preferable to an unsupported match.
- Cross-run reliability: six frozen items are re-rated with
  `gemini-3.1-pro-high`; categorical agreement and identity-choice agreement
  must be reported.
- Visual analysis is a separate gate. Audio-only success does not establish
  audiovisual success.

## Promotion rule

No output in this directory is consumable by the production pipeline. A later
full-corpus study requires:

- human-ratified identity labels;
- a locked retention policy for uploaded media;
- a defined visual corpus or source-video acquisition step;
- cross-source/program normalization;
- validation of any mapping from observable delivery features to behavioral or
  Big Five criteria; and
- explicit user ratification.
