# Paper-driven audiovisual diagnostic v3

## Scope

This is an isolated, perception-only engineering evaluation. It does not
produce or update Big Five scores, personality labels, mental-state labels,
behavioral criteria, or production cross-references. `production_consumers`
remains zero regardless of outcome.

The paired sample is intentionally diagnostic rather than representative:

- eight v2 semantic-grounding failures: F004, F006, F008, F011, F013, F018,
  F020, and F025;
- two aligned sentinels: F019 and F027.

The known failures test whether stricter target-window extraction and atomic
analysis repair the actual v2 failure mode. The sentinels detect regressions.

## Conditions

Each case is evaluated in a fresh Gemini Flash conversation:

1. `audio_only`: 16 kHz mono PCM audio from the admitted target turn.
2. `visual16_only`: a silent storyboard of exactly 16 equally spaced frames
   from the same target turn, with relative timestamps.
3. `audiovisual`: the admitted target-turn audio and video together.

Two additional hidden controls combine the video from one case with the audio
from another:

- M001: F004 video + F011 audio
- M002: F018 video + F025 audio

The model receives only case IDs. Expected names, source titles, chambers,
parties, target transcripts, and prior outputs are withheld.

## Atomic tasks

- Audio: speech presence, speaker count, active-speech intervals, a short
  verbatim anchor, pace, pausing, disfluency, prosodic variability, and
  timestamped audio events.
- Visual: person/face/upper-body visibility, displayed text, shot changes,
  gesture/head/posture/turn-coordination events, and timestamps.
- Temporal: event order and overlap.
- Composite: matched/mismatched/uncertain, synchronization direction, lag,
  absent modality, and evidence.

Unavailable modalities must be explicitly unobservable. Every timestamp must
be inside the derivative's target-relative duration. Camera edits and framing
are production artifacts, not subject behavior.

## Hard gates

- Source and derivative hashes are pinned.
- Target bounds must be finite, ordered, and within the local source clip.
- A/V derivatives must contain both streams; WAV derivatives contain no video;
  V16 storyboards contain exactly 16 indexed frames.
- JSON schema, enumerations, timestamps, and modality-condition consistency
  must validate.
- Identity or trait inference is a receipt failure.
- No out-of-bounds evidence is tolerated.

Independent human atomic-event coding is still required before claims about
action accuracy, timing precision/recall, or construct validity. In its
absence, the executable comparison is limited to target-text grounding,
schema/timestamp validity, condition discipline, mismatch detection, and
output specificity.

## Predeclared interpretation

A larger perception-only validation is conditionally supported only if:

- all 30 primary receipts are schema- and timestamp-clean;
- at least 7/8 former v2 semantic failures align to the stored target turn,
  and both sentinels remain aligned;
- both hidden A/V mismatches are detected, with at most one false mismatch
  among matched A/V cases;
- no prohibited inference appears;
- audio-only and visual-only conditions abstain on unavailable modalities.

Even a full pass cannot authorize Big Five or durable behavioral updates.
Those require human ground truth, repeated ratings, cross-context reliability,
and criterion/construct validation.
