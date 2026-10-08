# Congress Speech and Audio Data Guide

Generated: 2026-08-31 (America/New_York)
Scope: what the corpus measures, how speech-habit fields should be interpreted, which evidence authorizes a speaker label, where the data lives, and the failure modes that must remain fail-closed.

## Read this first

There are three different products in this corpus. They answer different questions and must not be conflated:

1. **Coverage census:** does a named member have enough verified audio material to count as a general, strict-identity, or non-floor profile?
2. **Identity and provenance layer:** why is a particular interval attributed to that member, and is its PCM/hash/lineage intact?
3. **Descriptive measurement layer:** what acoustic delivery measurements were observed in accepted clips, by setting, source, and sometimes subject?

The current headline is **500 of 537 members (93.1%) with a verified general audio profile**. That does **not** mean there are current interview-based speech-habit estimates for all 500. The current descriptive snapshot contains 8,708 prepared clips for 427 members; 274 members have a non-null interview headline, and 231 have at least three headline clips and therefore receive headline percentiles. The separately defined current non-floor census threshold is met by 244 members.

The corpus is intentionally conservative. A title, thumbnail, channel, upload date, transcript package, or large quantity of text can route work, but cannot by itself establish who is speaking in an audio interval.

## Current state

| Claim | Current value | Authority |
|---|---:|---|
| Official named-member universe | **537** | `congress_audio_profile_census_full_v1.receipt.json` |
| General verified audio profiles | **500 (93.1%)** | Census and PASS receipt |
| Strict identity-prerequisite profiles | **416 (77.5%)** | Census; at least 3 events and 180 unique seconds |
| Verified non-floor descriptive profiles | **244 (45.4%)** | Census; at least 5 verified non-House-floor exact windows |
| General-profile residual | **37** | General recovery-gap ledger |
| Speech database | **269,585 rows / 57,765,095 words** | `social_media.db` inventory |
| Source-media inventory | **52,311 packages / 153,063 turns** | Cumulative current source snapshot |
| Accepted anchor vault | **1,512 recordings / 431 labels / 119.255 hours** | Anchor manifest and receipt |
| Physical canonical manifest | **6,911 rows / 425 labels / 95.558 hours** | `C:\melange-data\member_clips\clips_manifest.jsonl` |
| Logical non-floor exact windows | **24,524 / 267 labels / 54.498 hours** | Exact-window lineage ledger |
| Descriptive snapshot | **8,708 clips / 427 members / 99.267 hours** | Descriptive artifact and PASS receipt |
| Latest consolidated exact recovery | **31 accepted / 41 refused / 9 completed profiles** | Exact verification ledger and receipt |

Counts from these rows are not additive. Anchors, canonical clips, exact logical windows, and descriptive records can represent overlapping physical speech.

### Current freshness warning

`speech_descriptive_v1.json` was generated at `2026-08-31T05:28:59Z` from 6,880 canonical rows. The physical canonical manifest now has 6,911 rows after the later 31-window recovery. Its PASS receipt proves that the descriptive snapshot was internally valid when built; it does not make that snapshot current after an upstream append.

Likewise, `local_youtube_exact_window_verification_current_v1.*` is an older 30-window receipt from `05:17Z`; the newer consolidated result is `local_youtube_exact_window_verification_v1.*` from `16:08Z`. A filename containing `current` is not proof of recency. Use receipt timestamps, input hashes, output hashes, and dependency bindings.

## What is measured

### 1. Coverage and provenance measurements

The census measures availability and readiness, not speaking style:

- verified anchor events and seconds;
- canonical parent clips and seconds;
- 8-second-equivalent window counts;
- non-floor exact-window counts;
- whether the general five-window floor is met;
- whether the strict three-event/180-second prerequisite is met;
- whether the five-window non-floor floor is met;
- unverified YouTube title-match holdings, kept visibly separate.

For the general profile, eligible anchor and canonical window counts are combined using `max`, not addition. This prevents overlapping representations from manufacturing coverage.

### 2. Acoustic speech-habit measurements

Accepted audio is measured with openSMILE 2.6.0 using eGeMAPSv02 functionals. The six public channels are aliases for the following feature columns:

| Public field | eGeMAPSv02 source field | Unit / scale | Careful interpretation |
|---|---|---|---|
| `pause` | `MeanUnvoicedSegmentLength` | Seconds | Mean length of unvoiced segments. Higher values indicate longer unvoiced intervals in that clip. This includes acoustic silence and is not a semantic measure of hesitation. |
| `pace` | `VoicedSegmentsPerSec` | Voiced segments per second | Rate of detected voiced segments. Higher values mean more voiced segments per second. It is **not** words per minute or syllables per second. |
| `volume_dyn` | `loudness_sma3_stddevNorm` | Normalized dispersion | Relative variability of smoothed loudness. Higher values mean more loudness variation. It is not absolute loudness and is not in dB. |
| `pitch_var` | `F0semitoneFrom27.5Hz_sma3nz_stddevNorm` | Normalized dispersion | Relative variability of voiced fundamental frequency on the semitone scale. It is not raw pitch range. |
| `strain` | `jitterLocal_sma3nz_amean` | Local jitter ratio | Mean local cycle-to-cycle F0-period variation. The field name is a convenience label; it is **not** a clinical diagnosis or a direct measure of psychological strain. |
| `f0_mean` | `F0semitoneFrom27.5Hz_sma3nz_amean` | Semitones above 27.5 Hz | Mean voiced fundamental frequency. For intuition, `Hz = 27.5 * 2^(semitones/12)`. Do not treat it as gender, emotion, or personality. |

For every member block:

- `clips` is the number of accepted measurement rows;
- `minutes` is the sum of their durations;
- `episodes` is the number of distinct `(outlet, sid)` pairs;
- `<channel>_mean` is the arithmetic mean of the clip-level functional;
- `<channel>_sd` is the sample standard deviation across those clip-level values, or null when only one value exists.

Only `pause`, `pace`, `volume_dyn`, and `pitch_var` receive interview-headline percentiles. A member needs at least three `headline_interviews_only` clips. Percentiles are relative to other eligible members in that artifact snapshot; they are not population norms and are not comparable across independently rebuilt snapshots without checking the reference population.

### 3. Aggregation views

Each member in `speech_descriptive_v1.json` can contain:

| Field | Meaning |
|---|---|
| `coverage` | Clips, minutes, settings, source families, subjects, identity tiers, URLs, and cut status |
| `headline_interviews_only` | Pooled accepted interview settings; House-floor audio is excluded |
| `by_setting` | Separate descriptive blocks for each venue/setting |
| `by_source` | Separate descriptive blocks by source family |
| `by_subject` | Separate blocks for the limited set of verified-final clips with subject labels |
| `setting_contrasts` | Within-member first-minus-second setting differences, only when each side has at least two clips |
| `subject_tonality_contrasts` | Within-member first-minus-second subject differences, only when each side has at least two clips |
| `subject_effects` | Reaction/topic side analysis; descriptive only |
| `caveats` | Member-specific warnings, including House-floor exclusion from the headline |

### 4. Settings

The implemented interview-headline settings are:

- `washington_journal`;
- `npr`;
- `sunday_show`;
- `longform_podcast`;
- `broadcast_news_interview`.

`house_floor` is retained for display and setting contrasts but never enters `headline_interviews_only`.

The current artifact also contains **90 `podcast_interview` clips across 13 members**. That setting is not currently listed in `INTERVIEW_SETTINGS` or `SETTING_LABELS`, so it is not pooled into the interview headline by the present builder. Do not silently assume that its name makes it headline-eligible; resolve the contract explicitly before changing this behavior.

Global setting effects use matched-member setting means. Each member contributes one difference, each setting needs at least two clips for that member, and a comparison needs at least five matched members. The normal-approximation interval is descriptive, not causal.

### 5. Subject and topic measurements

There are two distinct subject layers:

1. `by_subject` and `subject_tonality_contrasts` describe verified-final audio clips with labels such as education, healthcare, and public safety. The current snapshot has 90 labeled clips and 8,618 unlabeled clips.
2. `subject_effects.topics` is a Washington Journal reaction-window join containing 343 labeled rows across a separate topic taxonomy.

The topic taxonomy is not adjudicated, and the artifact records earlier reaction cross-family reliability of only `r = 0.20`. These results must not be described as personality effects, emotional reactions, causal effects, or stable member dispositions.

### 6. Text and content holdings

`social_media.db` stores attributed transcript/speech text from interviews, the Congressional Record, and hearings. It supports discovery, localization, word counts, and content work. Transcript text is **not** acoustic tonality evidence. A transcript-only row never becomes an audio measurement merely because the member label is known.

The current acoustic layer does not directly measure filler-word frequency, vocabulary, syntax, rhetorical frames, sentiment, truthfulness, deception, competence, health, or diagnosis. Those require separate, explicitly validated instruments.

## What “verified” means

### Member readiness tiers

| Tier | Rule | Appropriate claim |
|---|---|---|
| General audio profile | At least five verified 8-second-equivalent windows from anchors or active canonical audio, using the larger eligible source per member | Enough accepted voice material to count in the general coverage census |
| Strict identity prerequisite | At least three independently verified events and 180 unique seconds | Enough multi-event reference material for stricter positive voice-comparison work |
| Non-floor descriptive profile | At least five verified non-House-floor exact windows | Minimum non-floor material for descriptive recovery accounting |

These are readiness rules, not estimates of behavioral reliability.

### Identity tiers inside the descriptive snapshot

| Identity tier | Current clips | Meaning |
|---|---:|---|
| `turn_bound` | 2,630 | Exact attributed transcript turn with immutable turn/text/source bindings |
| `turn_bound_receipt_verified` | 30 | Literal in-band named exact turn with a verification receipt |
| `package_aligned` | 2,642 | NPR package/member binding plus monotonic transcript alignment |
| `episode_aligned` | 1,559 | Sunday-program episode/date/member or transcript-feature alignment |
| `exhaustive_voice_verified` | 1,847 | Verified-final source-media chain with exhaustive multi-anchor structural consensus; no probability claim |

Identity confidence is path-specific. A calibration result for one voice-comparison path cannot be transferred wholesale to package alignment, transcript attribution, or the cold-start YouTube lane.

### Latest local YouTube exact-window gate

For the newest cold-start recovery lane, positive identity comes from literal in-band naming tied to the first continuous target response. An approved first-name alias may be used only with the surname. Timestamped ASR can recover or localize the cue, including deterministic tolerance for transcription errors, but title/channel metadata remains non-authoritative.

Each accepted window in this lane requires:

- exactly 8.0 seconds, 128,000 frames, mono, 16 kHz, PCM16;
- a two-second inset from the candidate target span;
- at least eight overlapping ASR words;
- no question mark inside the window;
- at least 80% voiced frames;
- no internal silence longer than 1.2 seconds;
- first-half/second-half voice consistency of at least 0.35;
- no match to an already vaulted other speaker at or above `0.595722615`;
- consistency with the cold seed at or above `0.595722615` after the first accepted window;
- full source, transcript, PCM, WAV, and receipt hashes.

ECAPA is rejection-only in this cold-start lane. It can veto a candidate; it cannot establish the identity of an otherwise unnamed speaker.

## Accuracy: the number and its boundary

The reportable numerical result is **99.9995% calibrated wrong-speaker rejection accuracy, expressed as a one-sided 95% lower confidence bound**. The held-out comparison observed zero false accepts in 650,160 wrong-claim sequences. This is specificity for the calibrated comparator in its tested domain.

It is not corpus-wide speaker-label accuracy for all 500 profiles. There is not yet a blinded human-gold audit spanning every source and evidence path. The same calibration accepted only 23 of 1,473 genuine sequences (1.56%), showing the deliberate high-specificity, low-recall tradeoff.

The newest 31 accepted exact WAVs were separately re-opened and passed file SHA-256, decoded PCM SHA-256, format, frame-count, and canonical-binding checks 31/31. That proves file and lineage integrity, not human-perceived speaker identity.

The honest executive statement is:

> **99.9995% calibrated identity-gate specificity; 93.1% member coverage; corpus-wide speaker-label accuracy not yet measured by blinded human audit.**

## Landmines and required handling

| Landmine | Why it fails | Required handling |
|---|---|---|
| Acquisition pad treated as speech start | The pad can contain host words or multiple turns, causing `transcript_start_not_unique` even when the real member turn is clear | Treat the pad as context only; infer and persist the actual member turn start, preferably by the uniquely labeled turn whose next transcript boundary matches the saved end |
| Title, channel, office, date, or thumbnail used as identity | Metadata says what a package is about, not who occupies a particular interval | Use metadata only for routing; require an accepted in-band, transcript-turn, package/episode, or verified voice evidence path |
| ASR treated as ground truth | Names can be misspelled and turn boundaries drift | Bind to the timestamped source and retain the literal evidence; use only the approved deterministic name/alias tolerance and refuse ambiguity |
| First name or surname alone promoted casually | Common names and formal recognitions are ambiguous | Follow the lane contract. The newest exact lane requires surname plus an approved first name/alias; any different formal-recognition rule needs its own reviewed evidence contract |
| Interviewer question or speaker change inside a cut | The clip may measure the interviewer or mixed voices | Use turn inset, question-boundary protection, VAD, half-window consistency, and refusal ledgers; do not trim a refused row until it happens to pass without preserving the new lineage |
| ECAPA used to create a cold identity | A nearest voice can still be the wrong person | In the cold-start lane, ECAPA is rejection-only; literal in-band identity is mandatory |
| General, strict, and non-floor counts treated as one threshold | They answer different readiness questions | Always name the tier and its rule with the count |
| Anchor and canonical windows added together | The representations can overlap | General coverage uses `max(anchor, canonical)`, not sum; unique duration requires source-frame deduplication |
| Logical exact windows assumed to be separate WAVs | `canonical_exact_windows_v1.jsonl` intentionally has `output_wav: null` for most rows | Resolve the parent WAV plus source frame interval and verify lineage hashes |
| Descriptive PASS receipt mistaken for current freshness | A receipt can remain valid while an upstream manifest later grows | Compare generated time and input SHA-256 to current upstream receipts before publishing counts |
| `current` in a filename trusted blindly | Some later consolidated artifacts have older-looking names | Determine authority from receipt status, generated time, input/output hashes, and dependency chain |
| Candidate-stage features consumed | Candidates may be mislabeled, stale, or measured before final cuts | Candidate features are forbidden from verified measurements; recompute every verified-final WAV |
| `b5_cache_present` or persisted `target_eligible` treated as verification | The census records 28 persisted eligibility contradictions and legacy caches have different contracts | Recompute strict readiness from physical verified events/seconds; persisted flags are not dispositive |
| House-floor delivery pooled into interview habits | Floor procedure, microphones, and speaking format materially alter delivery | Keep floor data in `by_setting`; never include it in the headline |
| `podcast_interview` assumed headline-eligible | The current builder does not include it in the headline setting set | Treat it as excluded until the contract and tests explicitly add it |
| Setting or subject differences treated causally | Selection, microphone, format, topic, and audience are uncontrolled | Report as descriptive matched-member contrasts only |
| `strain` read clinically | The field is local jitter, not a diagnosis | Call it jitter or an acoustic roughness proxy and retain the non-clinical warning |
| `pace` called words per minute | It is voiced segments per second | Use the exact field definition; derive WPM separately from aligned text if needed |
| Absolute loudness compared across sources | Broadcast processing, gain, compression, and microphones differ | Prefer within-source/within-member contrasts and normalized dynamics; never call `volume_dyn` absolute vocal loudness |
| Missing values converted to neutral values | Missing headline data is informative and recovery is non-random | Preserve nulls and coverage fields; do not impute a 50th percentile |
| Superseded source intervals counted twice | Canonical and recovered clips can cover the same physical source frames | Apply canonical source-lineage supersession; do not physically delete evidence |
| Historical or legacy corpora silently merged | `audio_pilot` and title-only YouTube holdings lack the uniform accepted contract | Keep them as discovery/source supply until they pass the current identity, PCM, and receipt chain |
| Temporary cache consumed | `speech_descriptive_clip_cache.jsonl.43560.tmp` is an interrupted working file | Ignore `.tmp` files; only use the receipt-bound cache/artifact pair |
| 536 forced from a 537-person universe | The current reconciliation contains 537 named people | A 536-person request requires one explicit named exclusion; never silently drop a member |
| Off-repo media assumed protected by Git | Bulk WAVs, models, and vectors live under `C:\melange-data` | Back up the external store and keep every repo manifest/receipt hash-bound to it |
| Cleanup performed to remove duplicates | Duplicate physical evidence can be needed for audit and recovery | No source-audio physical cleanup is authorized; supersede logically and preserve lineage |

## Where everything is located

### Repository: authoritative reports and ledgers

All paths below are relative to the repository root unless shown as absolute.

| Path | Role | Consumption status |
|---|---|---|
| `data/speech/CONGRESS_AUDIO_ACCURACY_REPORT_20260831.md` | Accuracy claims, limitations, and audit recommendation | Current human-readable authority |
| `data/speech/CONGRESS_AUDIO_CORPUS_INVENTORY_20260831.md` | Full storage, source, transcript, and coverage inventory | Current human-readable authority |
| `data/speech/congress_audio_profile_census_full_v1.jsonl` + receipt | One row per named member; current tier coverage | **Primary coverage authority** |
| `data/speech/congress_audio_profile_recovery_gap_general_v1.jsonl` + receipt | Current 37-member residual and local package routing | Routing only; not identity evidence |
| `data/speech/congress_audio_profile_recovery_gap_strict_v1.jsonl` + receipt | Strict identity-prerequisite gap | Routing only |
| `data/speech/congress_audio_profile_recovery_gap_nonfloor_v1.jsonl` + receipt | Non-floor descriptive gap | Routing only |
| `data/speech/congress_audio_roster_reconciliation_2026-08-31.json` | 537-person universe, additions, and removal | Universe authority for this snapshot |
| `data/speech/speech_descriptive_v1.json` + receipt | Member acoustic aggregates, settings, sources, subjects, and contracts | Valid snapshot; currently 31 canonical rows behind |
| `data/speech/speech_descriptive_clip_cache.jsonl` | Receipt-bound clip-level descriptive measurement cache | Internal build input/output; do not substitute for the aggregate contract |
| `data/speech/canonical_exact_windows_v1.jsonl` + receipt | Logical 8-second non-floor source-frame windows | Authoritative lineage ledger; usually no separate output WAV |
| `data/speech/speaker_anchor_vault_all_verified_v3.jsonl` + receipt | Accepted identity anchor inventory | Current anchor authority |
| `data/speech/speaker_anchor_calibration_all_verified_v3.json` | Held-out voice-comparison calibration | Accuracy authority for that comparator only |
| `data/speech/source_media_inventory_cumulative_current_snapshot.jsonl` + receipt/summary | Package discovery and acquisition state | Current routing inventory; packages are not accepted clips |
| `data/speech/source_media_verified_cumulative_exact_windows_v6.jsonl` + receipt | Current verified-final exact source-media set used by the descriptive snapshot | Accepted only through its full candidate/identity/calibration/final chain |
| `data/speech/canonical_source_lineage_v1.jsonl` + receipt | Canonical-to-full-source lineage and overlap protection | Required where source overlap exists |
| `data/speech/local_youtube_holdings_asr_v1.jsonl` + receipt | Timestamped ASR holdings | Localization only |
| `data/speech/local_youtube_turn_candidates_v1.jsonl` + receipt | Literal-name and target-span screening | Candidate routing only |
| `data/speech/local_youtube_exact_window_verification_v1.jsonl` + receipt | Latest 72-row consolidated exact accept/refuse ledger | Latest exact recovery authority |
| `data/speech/local_youtube_exact_window_verification_current_v1.jsonl` + receipt | Older 49-row/30-pass consolidation | Historical input to the descriptive snapshot; do not mistake for latest |
| `social_media.db` | Interview, Congressional Record, and hearing text | Text/discovery authority; not acoustic identity evidence |

Receipts are part of the artifact. Never copy or consume a JSON/JSONL payload without its matching PASS receipt when the contract provides one.

### Repository: implementation and tests

| Path | Responsibility |
|---|---|
| `fec/speech/build_descriptive_speech.py` | Feature mapping, clip validation, aggregation, settings, subject contrasts, artifact and receipt build |
| `fec/speech/descriptive_contract.py` | Fail-closed reader used by downstream surfaces |
| `fec/speech/build_full_audio_profile_census.py` | Roster-complete coverage census and tier calculations |
| `fec/speech/build_audio_profile_recovery_gap.py` | General/strict/non-floor routing gaps |
| `fec/speech/import_wj_clips.py` | C-SPAN/Washington Journal exact transcript binding and padded-start recovery |
| `fec/speech/classify_local_youtube_turns.py` | Literal in-band name and target-span screening |
| `fec/speech/verify_local_youtube_exact_windows.py` | Exact cold-start YouTube cut, refusal, and canonical append logic |
| `fec/speech/source_media_recovery.py` | Candidate, identity, calibration, and verified-final recovery contracts |
| `fec/speech/voice_first_recovery.py` | Voice-first recovery support |
| `fec/surfaces/build_dashboard_bundle.py` | Surface consumer; exposes clip/minute/setting coverage plus pitch/volume-dynamic percentiles |
| `fec/surfaces/make_member_desk.py` | Member-desk consumer through the fail-closed descriptive loader |
| `fec/tests/speech/` | Speech contract and regression tests; latest run was 115/115 passing |

Upstream feature and reaction shards are under `outputs/npr_pilot_20260824`, `outputs/sunday_pilot_20260825`, `outputs/wj_features_20260825`, `outputs/axe_pilot_20260827`, `outputs/speech_reaction_profiles_20260825`, and `outputs/speech_triggers_20260826`. They are build inputs, not safer substitutes for the receipt-bound final artifact.

### External bulk store: `C:\melange-data`

| Location | Contents |
|---|---|
| `C:\melange-data\member_clips\clips_manifest.jsonl` | Physical canonical clip manifest |
| `C:\melange-data\member_clips\` | Canonical WAVs and verified exact-cut subdirectories |
| `C:\melange-data\member_clips\cspan_youtube_verified_v1\` | Materialized latest local YouTube exact WAVs |
| `C:\melange-data\speaker_anchor_vault_all_verified_v3\` | Current accepted anchor audio store |
| `C:\melange-data\speaker_anchor_vault_expanded_v2\ecapa_anchor_vectors_v2.npz` | Anchor vectors used by the current calibration/recovery chain |
| `C:\melange-data\youtube_audio\` | Downloaded raw YouTube recovery WAVs and manifest |
| `C:\melange-data\youtube_audio_asr_v1\<video_id>\transcript.words.jsonl` | Timestamped ASR word ledgers |
| `C:\melange-data\source_audio\` and versioned source-audio folders | Candidate/full-source recovery media and manifests |
| `C:\melange-data\npr_audio\` | NPR source audio and fetch bindings |
| `C:\melange-data\sunday_audio\` | Sunday-program source audio and targets |
| `C:\melange-data\wj_audio\` | Washington Journal/C-SPAN source turns and transcripts |
| `C:\melange-data\axe_audio\` | CNN Axe Files source audio |
| `C:\melange-data\houselive\` | House-floor source media |
| `C:\melange-data\models\` | Local ASR and speaker-embedding models |

The bulk store currently contains 17,282 audio/video files totaling 58.852 GiB. That is storage volume, not unique accepted speech.

## Safe consumption recipes

### “How many members have audio?”

Read `congress_audio_profile_census_full_v1.receipt.json`, require `status: PASS`, then read the census rows. State the tier explicitly. For the general count, use `verified_audio_profile`; for strict identity use `strict_identity_prerequisite_ready`; for non-floor use `verified_nonfloor_descriptive_profile`.

### “What are this member's observed speech habits?”

Load `speech_descriptive_v1.json` through `fec.speech.descriptive_contract.load_optional`, which validates the receipt and contract. Read `members[member].headline_interviews_only` for the headline and use `by_setting` for context. Preserve nulls. State the number of clips, minutes, settings, and the snapshot date. Until the descriptive rebuild incorporates the newest 31 canonical rows, disclose that freshness boundary.

### “Give me the exact audio behind this claim”

Resolve the accepted manifest row and its receipt chain. Check the file SHA-256 and WAV geometry. For a logical exact-window row with `output_wav: null`, read the parent path and frame offsets from `lineage`; do not search for a nonexistent child WAV.

### “Find more members”

Start with `congress_audio_profile_recovery_gap_general_v1.jsonl`, then use the current source-media inventory and local YouTube holdings for routing. A package, transcript, ASR row, or title match is a lead. Promotion still requires the applicable identity, exact-cut, speech-purity, hash, and receipt contract.

### “Compare members”

Use the same artifact snapshot and the same setting policy. Report coverage with every comparison. Do not compare floor-only measurements to interview headlines, and do not describe the 244-member non-floor subset as representative of all 537 members; recovery is non-random.

## Rebuild and validation order

From the repository root, the principal deterministic rebuilds are:

```powershell
python -m fec.speech.build_descriptive_speech
python -m fec.speech.build_full_audio_profile_census
python -m fec.speech.build_audio_profile_recovery_gap --target general --output data/speech/congress_audio_profile_recovery_gap_general_v1.jsonl
python -m fec.speech.build_audio_profile_recovery_gap --target strict --output data/speech/congress_audio_profile_recovery_gap_strict_v1.jsonl
python -m fec.speech.build_audio_profile_recovery_gap --target nonfloor --output data/speech/congress_audio_profile_recovery_gap_nonfloor_v1.jsonl
python -m unittest discover -s fec/tests/speech -p "test_*.py"
```

After any accepted upstream append:

1. verify the new exact/final receipt and canonical append;
2. rebuild the descriptive artifact if the new audio belongs in measurement;
3. rebuild the full census because it binds the descriptive and canonical input hashes;
4. rebuild all affected recovery-gap ledgers;
5. rerun the speech tests;
6. refresh human-readable accuracy/inventory numbers;
7. inspect `git diff --check` and commit only the intended repo artifacts.

Do not use `--no-verify-audio-hashes` for a production artifact. Do not use `--no-measure-missing` unless every accepted clip already has a receipt-compatible cached measurement.

## Before publishing a member profile

- Confirm the member is in the reconciled 537-person universe.
- Name the coverage tier being claimed.
- Require the relevant PASS receipt and matching SHA-256 bindings.
- Confirm that identity evidence is authoritative for the interval, not merely for the package.
- Confirm WAV/PCM geometry and exact source lineage.
- Exclude interviewer speech, questions, crosstalk, and uncertain boundaries.
- Show clip, minute, episode, setting, and source coverage.
- Use interview-only headline values; display floor values separately.
- Preserve nulls and state the reference population for percentiles.
- Describe setting and subject differences as descriptive, not causal.
- Never route audio into Big Five, rank, allocation, or persuasion values.
- Never claim corpus-wide speaker-label accuracy until a blinded stratified human audit measures it.

## Non-negotiable contract

The descriptive artifact is `DISPLAY_ONLY_NO_ENGINE_WIRING`. Audio may not modify Big Five, rank, allocation, stance, persuasion, or any other Moneyball engine value. Candidate-stage features may not enter verified measurements. Program metadata may not identify a speaker. Floor audio may not enter the headline. Source audio may not be physically cleaned up. Every exception requires a new explicit contract, tests, audit evidence, and receipt—not an informal interpretation of an existing field.
