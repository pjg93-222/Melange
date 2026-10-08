# Long-form integration — implementation and live run

Checkpoint: September 4, 2026. This is not a claim that the 533-member evidence review is complete.

## Requested contract

Use Melange's collected audio and behavioral findings. Keep the original direct, descriptive profile style: three paragraphs, personality; speech and landmines; approach, 200–250 words, without visible citations or an evidence-audit narrative. Do not regenerate those profiles until the new evidence has actually passed its integration gates. Do not convert descriptive public observations into personalized political-influence advice.

## Implemented this turn

- Complete response WAVs now receive the same six existing eGeMAPSv02 acoustic measurements. There is no turn-duration ceiling. These recording-specific measurements remain separate from eight-second reference percentiles and personality scores.
- Speaker continuity retains the calibrated eight-second windows, but now checks the complete turn interior. An early three-window pass cannot approve a multi-minute response. The two-second boundaries still require actual boundary review. A processing budget produces an explicit incomplete result.
- Supplemental reference clips from the candidate production are excluded, and multiple windows from one production cannot masquerade as independent recordings.
- Review queues retain multiple sources and all qualifying turns, with exact source, transcript, and candidate-boundary hashes. The existing 300-second name-cue linkage restriction remains visible; excluded later turns are not described as missing audio.
- Materialization requires named, timestamped human review bound to the exact audio, transcript and candidate turn. Existing labels without that provenance are not silently upgraded. Descriptive findings no longer require invented meeting advice.
- The narrative evidence builder consumes the new measurements under `speech_profile.longform_measured_delivery`, preserves candidate versus qualified authority, and does not overwrite existing personality estimates or short-window cohorts.
- Local classification now checks exact input/output token budgets. It never silently truncates an oversized transcript or accepts a response exhausted at the output limit.
- Immutable snapshots let completed recordings proceed while the single ASR repair writer handles the remaining backlog.

## Actual measurement result

`data/speech/member_longform_turn_features_v1.json` and its receipt contain an actual OpenSMILE 2.6.0 run over nine previously materialized candidate WAVs, measured end to end: eight sources, four members, 13.438167 minutes. This does not establish that the legacy clip boundaries are complete member responses. All 36 dependencies were physically hash-checked. A ten-minute synthetic response is also covered by the no-duration-cap tests.

| Member | Legacy candidate WAVs | Sources | Measured minutes |
| --- | ---: | ---: | ---: |
| Steve Scalise | 4 | 3 | 5.749833 |
| Alex Padilla | 2 | 2 | 3.083333 |
| Maxine Waters | 2 | 2 | 2.368333 |
| Mike Johnson | 1 | 1 | 2.236667 |

These nine legacy rows lack a named, source-bound whole-turn review record. Their newly measured features therefore remain candidate-only: **zero newly qualified profile turns**. Acquisition, measurement, verified attribution, and profile publication are distinct stages.

The candidate evidence ledger at `audits/longform_integration_20260904/member_narrative_evidence.candidate.json` successfully builds all 533 members. Comparison against the active ledger found zero changes to traits, qualified language reads, behavioral values, or visibility. No active profile prose has been regenerated in this integration turn.

## Active finite jobs

- Collection repair: `fec/speech/continue_member_longform_collection_20260904.ps1`, log `C:/melange-data/asr_backfill_logs/collection-repair-20260904.log`. The old worker had ended without a terminal receipt; it was restarted only after verifying the exclusive lock was free. Latest observed progress at 17:40 ET: nine of the 47 remaining source-bound transcripts completed, in addition to five completed before the restart. Do not launch a second writer.
- Scalise reconciled audio pilot is **finished**: `C:/melange-data/longform_candidate_runs/scalise-reconciled-20260904/`. The immutable source is the February 2020 Takeout interview, before Scalise became Majority Leader, not before all of his leadership service. Actual acoustic results are below. The older Qwen text-classifier pilot was stopped after reconciliation supplied the candidate input; see `SCALISE_LOCAL_PILOT_CANCELLATION.md`. Its token preflight passed, but its inference did not finish and is not reported as an analysis result.

Recheck process command lines and logs before relying on a recorded process ID. Use the workspace acquisition ledger, not the stale duplicate under `C:/melange-data`.

## Remaining work

1. Inspect actual classifier and continuity receipts from the pilot; a launch or token-budget pass is not a completed analysis.
2. For passing turns, create a run-specific review queue. Keep incomplete, rejected, and missing-cue cases explicit.
3. Complete genuine speaker/boundary/content reviews before materialization and profile qualification. Do not generate HUMAN attestations with an AI or treat source titles as voice identity.
4. Process the remaining ready cohort from immutable snapshots; re-run repaired sources only after technical quality checks pass. One recording or multiple copies do not establish a recurring pattern; the user requires two independently produced interviews in different settings.
5. Rebuild measured features and the evidence ledger from qualified turns, preserving leadership source-era boundaries. Only then offer a new profile sample in the requested style.

## Later checkpoints in this turn

- Combined focused suite: **203 tests passed** (24.04 seconds), including complete-turn measurements, both classifier guards, source snapshots, speaker coverage, review queue, materialization, review export, readiness, descriptive drafts, and ledger admission. Do not add overlapping intermediate test counts to this total.
- The complete 533-member immutable readiness snapshot finished and its frozen bindings verified in 99.6 seconds. It is at `C:/melange-data/longform_candidate_runs/roster-ready-20260904/`, with `snapshot.receipt.json` and `source_diagnostics.jsonl`.
- Strict candidate-ready count: **76** (21 pre-current-role leadership sources and 55 primary sources). Exclusions: 395 diagnostic flags, 28 stale transcript/source bindings, 14 pending transcripts, 13 missing in-band name cues, six existing quality holds, and one pending acquisition. These are snapshot counts, not continually updated global totals.
- **390 of those diagnostic exclusions are caption timing backsteps only.** Caption display intervals were linearly interpolated into approximate word times and can overlap. The sampled text remains coherent. These are not 390 unusable recordings. Preserve text order; sorting rows by their estimated timestamps would reorder words. A separate caption-localization route would still need accurate audio alignment and boundary checks before complete-turn measurement admission.
- Five sources have additional repetition flags requiring inspection: David Schweikert, Debbie Wasserman Schultz, Jason Smith, Jay Obernolte, and Ryan Zinke. The ASR cases include 75 consecutive `but` tokens for Wasserman Schultz and a repeated eight-token phrase 51 times for Obernolte. Music/lyrics may explain some caption repetitions; the flags are not a blanket declaration that every recording is defective. No broad rerun or lowered gate was authorized from these diagnostics.
- The original hosted classifier was tried for exactly one Scalise recording after a read-only model-availability check. Inference failed with HTTP 400 because the Anthropic account has insufficient API credit. No retry or bulk paid request was made. Provider token usage and billed USD were unavailable, not asserted to be zero. The failed request and partial receipt are preserved under `C:/melange-data/longform_candidate_runs/scalise-original-route-20260904/`.
- The CPU Qwen pilot is still running at the 17:25 ET checkpoint. Two separate internal automated annotation passes are also reading the entire immutable Scalise transcript as an alternative candidate-extraction route. They are not human listening reviews and do not confer speaker/profile authority. Exact opening/closing-word agreement will be checked before the acoustic stage.
- Collection repair progressed to five of the 47 remaining transcripts at this checkpoint, in addition to the five completed before the restart. New transcripts still require a quality check; a fresh file is not proof of correct recognition.
- A user methodology decision is pending: retain the existing human listening sign-off, or allow explicitly labeled automated review after voice matching and independent boundary checks. **Do not assume approval or write HUMAN attestations.** The current named-human gate remains in effect.

## Full-transcript reconciliation checkpoint

- Separate internal automated passes A and B each read all 10,391 timestamped words of the immutable Scalise Takeout transcript, through 3034.39 seconds. They did not read one another's output, use Qwen output, listen to the audio, or provide human/speaker authority. This is not independent-model corroboration or a second independent interview.
- The source-bound reconciler retained **32 exactly agreed candidate intervals totaling 20.657 minutes**, including an intact **134.9-second** interval at 2650.37–2785.27 seconds. Eighteen unmatched claim records are retained as disagreements, not merged into invented turns. Raw A/B artifacts are in this audit directory; the candidate and receipt are under `C:/melange-data/longform_candidate_runs/scalise-reconciled-20260904/`.
- A real, unlimited whole-interior ECAPA speaker-continuity run completed on those 32 intervals using the existing CPU backend. The launcher requested two threads, but the shared ECAPA backend explicitly sets one; no backend/calibration settings were changed. A successful candidate reconciliation is not a successful acoustic result or profile qualification.
- The combined focused suite passed **218 tests** in 15.98 seconds before the later physical-bounds preflight change. Separate integration tests preserve a 599.8-second turn across 75 interior windows and pass the real reconciler output through mocked embeddings into the real review queue.
- The long-running local Qwen pilot was compute-active, not demonstrably stalled. Its 22,922-token input was expensive on CPU; a bounded microbenchmark did not establish a BF16-specific slowdown. It was stopped at approximately 17:35 ET once the source-bound alternative candidates existed. No dtype fix or arbitrary shorter-turn cutoff was applied. Process checks confirmed only the intended classifier stopped; the acoustic verifier and ASR worker remained active.
- Tokenizer-only preflight of the 76-source strict-ready snapshot found 75 sources fitting their proposed local prompt regions and one oversized source, Sydney Kamlager-Dove. Only 42 sources' regions include every transcript word; 34 are partial. These are candidate-localization regions, not evidence that the full recordings were analyzed. A physical timing issue also surfaced for Margaret Hassan: the last transcript timestamp extends about 1.734 seconds beyond the WAV. The bounded early-validation fix is now implemented under local contract v5. An actual member-scoped rerun returned `FAIL_PREFLIGHT` / `transcript_timestamp_bounds_or_order`, with `model_weights_loaded:false`, `artifacts_written:false`, and `transcript_clipped:false`. The prior 76-source token report remains explicitly historical, before this physical guard.

## Completed acoustic result and handoff

- **153 of 153 planned windows evaluated; one of 32 candidate turns passed complete-interior continuity.** Overall source result: `SPEAKER_CONTINUITY_INCONCLUSIVE`. Two turns were too short to contain even one calibrated interior window; all other planned coverage was evaluated. These are not processing-budget omissions.
- The passing interval is 353.59–385.57 seconds (**31.98 seconds**), source-bound turn `steve-scalise-0ec06fa55008-04`. It is in a run-specific review queue, with padded review audio, a neutral automated draft, and `review.html`. It still requires the existing genuine named listening/boundary/content review before admission. No automated HUMAN record was created.
- The intact 134.9-second candidate was checked in **17 windows**, but it failed the speaker continuity gate. It was not shortened into a more convenient passing excerpt.
- The run used three existing supplemental voice references from separate Face the Nation episodes (2019, 2021, 2026). Scalise is absent from the calibrated speaker-vault cohort. Ninety-three windows failed the required supplemental target-versus-competitor margin; nine failed the target-score floor, and two failed the voiced-ratio floor. These counts can overlap. Failed acoustic checks are not evidence of a personality characteristic and do not by themselves prove the transcript identified the wrong speaker. Thresholds and the speaker vault were not changed to force acceptance.
- The rebuilt audit-only narrative ledger contains all 533 members and the nine measured candidate WAVs. The old semantic pathway is now consistent with the measurement pathway: **five retained legacy semantic findings are explicitly provisional, zero are newly human-qualified**. Exact qualified measurement/review/source/semantic-row bindings are required before findings enter reviewed or baseline arrays. Historical source artifacts are preserved.
- Final focused checks: **226 tests passed** in the main integration suite (19.22 seconds), plus **16 disjoint semantic-authority tests passed** (2.22 seconds): **242 total**. Earlier intermediate counts are not additional tests.
- No active narrative ledger or profile prose was overwritten. The all-member integration and profile regeneration are not complete. Outstanding work includes transcript timing repair/localization coverage, reliable speaker verification, the pending review-authority decision, and two independent interviews in different settings before recurring-pattern claims.
- Final read-only diagnostic found no demonstrated normalization or label-array binding error: all 1,512 vault vectors are finite 192-dimensional float32 and unit-normalized; their member/event/audio-hash bindings match the manifest; the eight Letlow/Fulcher competitor WAV hashes match. The Scalise supplemental route uses fixed 0.55 target-score and 0.03 margin floors, not an established Scalise-specific cross-recording recall calibration. Legacy competitor speaker labels were not independently reverified in this diagnostic. No threshold or vault changes were made, and failed margins are not asserted to prove a different speaker.
- Comparison of the final candidate ledger with the active ledger found zero changes across all 533 members in traits, qualified language reads, behavior, visibility, hearing antagonism, receptivity, and effectiveness. The deliberate change is explicit provisional authority for unqualified long-form claims.
- Usage checkpoint at approximately 17:40 ET: primary weekly window 72% used, **28% remaining**. The user's 1%-remaining markdown threshold was not reached; this markdown preserves the handoff already.

## User reaffirmation and methodology compatibility

After receiving the two context-padded Scalise examples, the user said: "Yeah I trust it, just make sure you are using the same methodology as everything before just adjusted for length". The instruction is to continue with the existing methodology and length adaptation, not to introduce different personality scoring or relax evidence standards. No individual HUMAN listening attestation was manufactured from this general assent.

- All six feature mappings match the original descriptive-speech builder and interview verifier exactly. OpenSMILE remains eGeMAPSv02 Functionals, with the same file extraction and eight-decimal rounding.
- An actual compatibility run processed the same 180.7-second context-padded example through both old and new extractors. **All six numerical results matched exactly**, both using OpenSMILE 2.6.0. The audio SHA256 remained `a8d978feb52b4be7ab3740f2104f5bee8208c8b48a3dbac7e7a1d42c6e064c73`. This tests extraction compatibility; it does not grant speaker or profile authority to the example.
- Added `fec/tests/speech/test_longform_methodology_compatibility.py` to prevent feature/configuration/rounding drift and preserve the no-new-scores, leadership-era, and independent-interview rules. The focused compatibility, whole-turn measurement, continuity and local-classifier suite passed **118 tests**, including three new tests. This overlaps earlier suites and is not an additional 118 distinct tests.
- Speaker processing retains the existing ECAPA backend, 16 kHz mono PCM16, eight-second checks, and applicable rejection/supplemental constants. The length adaptation extends coverage across the complete response interior. Historical short-window code has a global-calibration-v1 default while the existing long-form route uses per-member calibration v3; these are not asserted to be identical threshold lookups, and no calibration lookup was changed by this confirmation.
- Whole-turn functionals remain separate from short-window percentiles; the same extractor does not establish that different-duration distributions share a calibration. Existing personality scores and the requested three-paragraph prose structure remain unchanged.
