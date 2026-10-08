# Human Annotation Codebook

## Purpose and boundary

This packet creates an independent human reference for 150 stored
C-SPAN *Washington Journal* interview clips. It tests speaker identity,
turn ownership, audio/visual relations, and directly observable speech
and visual behavior. It does **not** authorize Big Five, personality,
clinical, motive, honesty, intent, or other latent-trait inference.

The 150 cases contain 120 low-risk core cases and 30 deliberately
challenging ownership cases. Automated risk flags are triage signals,
not labels. The available eligible corpus contains 461 House programs
and only 16 Senate programs, so the frozen sample contains 134 House
and all 16 Senate programs. Do not interpret chamber comparisons as
balanced.

## Roles and blinding

1. Coder A completes `Coder A Cases` and `Coder A Events`.
2. Coder B completes `Coder B Cases` and `Coder B Events` independently.
3. Neither coder opens `Identity Key` or `Adjudication` before both
   independent passes are locked.
4. An adjudicator opens the identity key, resolves disagreements, and
   records a rationale. The adjudicator may replay the source URL.

Do not use the target transcript, expected name, source speaker label,
search engines, face recognition, private identity manifest, or outside
biographical knowledge during the independent passes. Code what is
present in the supplied clip.

## Case-level fields

- `media_playable`, `audio_present`, `video_present`: technical
  admission checks. Use `no` if the relevant stream cannot be reviewed.
- `lower_third_text`: transcribe the identifying lower-third text that
  is visibly present; otherwise leave blank.
- `introduced_name`: record a name audibly introduced in the clip;
  otherwise leave blank.
- `primary_visible_person`: brief neutral description, such as
  `remote male guest`, `host at desk`, or `split screen`.
- `primary_audible_speaker`: brief neutral description such as
  `guest`, `host`, `caller`, `multiple`, or `uncertain`.
- `target_turn_owner`: who owns the speech bounded by
  `target_start_sec` and `target_end_sec`:
  `member`, `host`, `caller`, `other`, `mixed`, or `uncertain`.
  `member` means the interview guest/legislator, not that the coder has
  independently identified the person by name.
- `identity_evidence`: `lower_third`, `audible_introduction`,
  `both`, `neither`, or `conflicting`.
- `identity_match`: fill only when an on-clip name is available:
  `yes`, `no`, `uncertain`, or `not_scored`. The adjudicator compares
  the captured name with the sealed expected identity.
- `speaker_count`: number of distinct audible speakers in the target
  interval. Use the best integer estimate.
- `offscreen_speech`: `yes` when the audible speaker is not the person
  visibly speaking for a material portion of the target interval.
- `av_relation`:
  - `synchronized_same_speaker`: visible mouth movement and voice
    belong to the same person.
  - `complementary_offscreen`: a normal production choice such as a
    remote guest heard while the host, graphics, or B-roll are shown.
  - `reaction_shot`: the listener is shown while another person speaks.
  - `mismatched`: evidence suggests the audio is attached to the wrong
    person/program rather than a normal edit.
  - `uncertain`: evidence is insufficient.
- `ownership_confidence`: integer 1–5, where 1 is guesswork and 5 is
  direct, repeated evidence.
- `coder_complete`: set to `yes` only after all required fields and
  event rows have been reviewed.

## Observable event coding

Use `Coder A Events` or `Coder B Events` for time-local behavior. Up to
six events are preallocated per case. Leave unused slots blank.

- `modality`: `audio`, `visual`, or `audiovisual`.
- `event_type` must be directly observable:
  - Audio: `speech_start`, `speech_end`, `pause`, `overlap`,
    `interruption`, `repair_restart`, `filler`, `laughter`,
    `rate_shift`, `volume_shift`, `pitch_shift`.
  - Visual: `gaze_camera`, `gaze_away`, `head_nod`, `head_shake`,
    `hand_gesture`, `facial_change`, `posture_shift`,
    `lower_third_change`, `shot_change`.
  - Audiovisual: `lip_sync_confirmed`, `reaction_while_other_speaks`,
    `offscreen_speech`, `possible_av_mismatch`.
- `start_sec` and `end_sec`: seconds from the beginning of the supplied
  clip, not the source program. Use one decimal place when possible.
- `description`: one short, literal observation. Do not explain intent.
- `target_involved`: `yes` if any part overlaps the target interval.
- `confidence`: integer 1–5.

Do not code broad impressions such as confident, nervous, evasive,
friendly, dominant, deceptive, conscientious, agreeable, or neurotic.

## Adjudication and acceptance

After both coders finish, use the `Adjudication` sheet. Resolve every
row flagged `REVIEW`. A case is admitted only if:

1. audio and video are both playable;
2. the target interval is fully present;
3. final turn ownership is not `uncertain`;
4. identity is supported by on-clip evidence or a documented source
   adjudication;
5. any apparent A/V mismatch has been distinguished from ordinary
   reaction shots, graphics, and offscreen production audio.

If evidence remains insufficient, set `final_disposition` to
`exclude` and explain why. Never repair a label by inference alone.

## Human work to return

Return the completed workbook only. Preserve case IDs and do not rename
worksheets. The machine-side validator will check completeness and
agreement before any Gemini comparison is allowed.
