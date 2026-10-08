# Prepared next-stage intensive analysis

Status: prepared only; not started  
Promotion state: `BLOCKED_PENDING_HUMAN_GOLD_AND_REAL_VIDEO`

## Objective

Validate whether Gemini can consistently extract speaker-attributed,
observable auditory and visual behavior from actual congressional interviews,
then determine whether any features add reliable evidence to the project's
behavioral criteria. Big Five updates remain downstream of independent
construct validation and explicit approval.

## Phase 1 — build human gold

1. Freeze 30–100 actual interview recordings across programs, dates, venues,
   demographics, and speaking conditions.
2. Have two independent reviewers mark target identity, target speaking
   intervals, interviewer intervals, overlap, cuts, and unusable regions.
3. Resolve disagreements through adjudication and record reviewer agreement.
4. Keep train/development/test sources disjoint by interview program and source
   channel.

## Phase 2 — acquire true audiovisual media

1. Preserve original source video where authorized; record source URL, capture
   time, duration, checksum, rights/retention status, and transformation log.
2. Create aligned audio-only and full-audiovisual versions of every test item.
3. Strip filenames and sidecar metadata that expose identity while retaining
   on-screen information in the audiovisual arm as a separately scored cue.
4. Define upload retention and deletion policy before sending the corpus to an
   external model.

## Phase 3 — preregister the comparison

Run the same frozen items in four conditions:

| Arm | Media | Identity candidates |
|---|---|---|
| A | audio only | closed set |
| B | full video plus audio | closed set |
| C | audio only | open set plus abstain |
| D | full video plus audio | open set plus abstain |

Predeclare identity accuracy, abstention, diarization error, target-attribution
error, timestamp tolerance, category reliability, calibration, and
audio-versus-video lift. Include shuffled candidate order, unknown-speaker
controls, and deliberately hard impostors.

## Phase 4 — extract only observable measures

Allowed candidate measures include:

- speaking rate and within-turn changes;
- pause, restart, filler, and repair frequencies;
- pitch and intensity variation with recording-quality controls;
- turn length, interruption/overlap, latency, and response completion;
- visible gaze direction, gesture rate, posture shifts, and visual
  turn-taking—only when the target interval is human-confirmed; and
- timestamped examples with uncertainty and quality flags.

Do not ask the model for personality, mental state, honesty, ideology,
protected attributes, diagnoses, or demographic inference.

## Phase 5 — normalize and validate

1. Normalize within venue, program, interviewer, recording chain, topic,
   speaking role, and date before comparing members.
2. Require repeated recordings per member and report within-member stability.
3. Compare model features with independent human annotations and deterministic
   acoustic measurements.
4. Use held-out sources for every confirmatory result.
5. Reject features with weak reliability, severe range compression, source
   leakage, poor calibration, or inconsistent target attribution.

## Phase 6 — controlled project integration

Only after the earlier phases pass:

1. write versioned candidate feature tables, never silent profile mutations;
2. define and validate any behavioral-criterion cross-reference;
3. test incremental value beyond existing text and structured evidence;
4. document uncertainty, provenance, exclusions, and venue sensitivity; and
5. require explicit approval before any Big Five or production consumer reads
   the artifacts.

## Immediate inputs still required

- an inventory or path for the actual recorded-interview media;
- permission/retention rules for sending real video to Gemini;
- two human reviewers or an existing adjudicated identity/boundary gold set;
  and
- the exact behavioral criteria and cross-reference fields proposed for later
  validation.

