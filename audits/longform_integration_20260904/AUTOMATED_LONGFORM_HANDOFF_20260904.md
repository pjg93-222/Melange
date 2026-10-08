# Melange: long-form audio integration and profile regeneration

Updated: September 4, 2026, approximately 6:52 p.m. Eastern.

Workspace: `C:/Users/pgoff/OneDrive/Desktop/Melange Systems`

## Bottom line

**Verified long-form integration for all 533 members is not complete. Profiles have not been regenerated or published from the new all-member evidence.**

The primary acquisition receipt reports recordings acquired for all 533 members. Acquisition is not the same as verified member speech, correct turn boundaries, or integrated behavioral findings. Leadership-era requirements leave an additional historical-source gap.

One new automated Scalise response has actually completed boundary reconciliation, speaker verification, exact audio cutting, and the existing six acoustic measurements. The all-roster transcription repairs are in progress. Newly written downstream batch-processing code has not yet been executed or tested end to end.

## User instructions to preserve

- Collect and integrate long-form podcasts/interviews for **every one of the 533 members**, before presenting the regenerated roster as long-form-grounded.
- Use the audio and behavioral findings within Melange. Do not substitute generic biography, impressions, invented meeting habits, or unsupported persuasion claims.
- Preserve the existing methodology; accommodate longer complete responses, including responses lasting many minutes. Computational chunks and identity windows are not behavioral turns.
- For current leaders, use recordings from **before they assumed their current role** for baseline evidence. Keep later recordings separate as current-role context.
- A recurring communication claim needs the same behavior in **two independently produced interviews in different settings**. Two clips or uploads of one interview do not qualify. Single-source observations remain provisional.
- The latest instruction, **“You don't need review, just get it done,” removes human listening/sign-off as a prerequisite.** It does not authorize inventing human attestations, lowering speaker thresholds, or calling failed checks verified.
- Do not ask the user for another sample approval or human-review round.
- The user previously requested a Markdown handoff when usage reaches 1% remaining. No automatic usage-monitoring mechanism has been established in this work.

### Profile format

Exactly **three prose paragraphs**, **280–300 words total**, plain English and natural in tone:

1. **Personality:** describe the existing findings clearly, explaining apparent differences between traits without contradictory shorthand.
2. **Speech & landmines:** describe how the member speaks, responds, and handles exchanges, with practical implications grounded in observed behavior.
3. **Approach:** translate the supported findings into concrete professional meeting preparation and communication. Suggested framing fit must not be presented as demonstrated persuasion or proof of what changes the member's mind.

No citations, source lists, audit language, or technical score dumps inside the profile prose. Retain traceability separately. Do not fill an evidence gap merely to reach the word count.

The user approved an extended Scalise-style sample and asked for additional examples. Earlier Klobuchar and Booker examples were not based on newly qualified long-form findings. Do not repeat that misrepresentation.

### Scalise field report

The user reported that someone told them Scalise asks about incidental subjects, including football, before substantive discussion. This is **secondhand**, with unknown date and frequency. It is not personally observed by the user, independently corroborated, or audio-confirmed. A host asking Scalise about football would not establish that Scalise initiates such conversation in meetings.

### User-supplied podcast leads

- [Steve Scalise — Fly Out Day: Inside the Shutdown](https://podcasts.apple.com/us/podcast/fly-out-day-inside-the-shutdown-with-steve-scalise/id1549272440?i=1000732205546)
- [Maxine Waters — U.S. Rep. Maxine Waters & Dr. Carl L. Hart](https://podcasts.apple.com/us/podcast/u-s-rep-maxine-waters-dr-carl-l-hart/id1609823559?i=1000783986824)
- [Alex Padilla — The Interview](https://podcasts.apple.com/us/podcast/the-interview-sen-alex-padilla-says-his-viral-moment/id1200361736?i=1000730070252)

These links are discovery leads, not verification receipts. Check the actual source and era before admission.

## Actual coverage and artifacts

### Primary acquisition

[Acquisition receipt](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/data/speech/member_longform_acquisition_v1.receipt.json>) reports:

- 533 processed members; zero acquisition errors and zero source mismatches.
- 530 acquisition rows labeled identity-unverified; three labeled identity-verified.
- These acquisition labels do not establish complete-turn verification or two-interview behavioral recurrence.

### Isolated all-member repair batch

Batch directory: `C:/melange-data/longform_candidate_runs/automated-roster-v2-20260904`

[Preparation receipt](C:/melange-data/longform_candidate_runs/automated-roster-v2-20260904/prepare.receipt.json) covers all 533 member queue rows:

| Initial assignment | Members |
| --- | ---: |
| Retranscribe original recording | 425 |
| Reuse existing ASR for subsequent checks | 81 |
| Await existing collection worker | 26 |
| Historical source hold | 1 |

The isolated transcript manifest currently contains 532 source rows: 83 ready-status rows, 422 still requiring ASR, one transcription error, and 26 waiting for the collection worker. These are processing states, **not verified member totals**. The 83 comprise the original 81 reusable rows plus two newly completed transcriptions, Josh Brecheen and Kevin Hern.

John Boozman's attempted repair failed with `mkl_malloc: failed to allocate memory`. The original collection worker also encountered memory errors, including Summer Lee and Mitch McConnell. The workers were stopped and restarted in sequence with a tested lower-memory feature calculation; completed results were retained. No post-restart completion line was visible at the status check above.

An earlier preparation-only directory named `automated-roster-20260904` contains an erroneous all-held result from a subsequently fixed acquisition-validation bug. **Do not use it. No worker ran from that directory.** Use the `automated-roster-v2-20260904` directory.

### Actual verified Scalise result

Directory: `C:/melange-data/longform_candidate_runs/automated-verification-20260904`

- Source: February 2020 Takeout interview, not the user's later shutdown episode.
- 32 agreed complete-response candidates were evaluated; all 153 planned acoustic windows were checked.
- **One complete response passed: 353.59–385.57 seconds, lasting 31.98 seconds.**
- The other 31 candidates were held. A 134.9-second candidate was not shortened to evade failed checks.
- The passing response was cut from the original PCM and measured using the existing six eGeMAPSv02 features.
- Provenance is explicitly **AUTOMATED**, not HUMAN.
- The automated semantic finding is limited to the measured response duration. It does not establish personality, persuasion, or a recurring communication pattern.

[Scalise measurement receipt](C:/melange-data/longform_candidate_runs/automated-verification-20260904/scalise.features.receipt.json)

A staged 533-member narrative evidence ledger successfully incorporates that limited new result alongside existing findings:

[Staged evidence ledger](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/audits/longform_integration_20260904/member_narrative_evidence.automated.json>)

This does **not** mean 533 members have newly qualified long-form evidence. Neither the active evidence ledger nor active profile prose was replaced.

## Current background jobs

Process IDs are a snapshot; verify command lines before acting on them. Never terminate unrelated Python jobs.

| Job | Process | State at last check |
| --- | --- | --- |
| Original collection launcher | PowerShell 26292 | Running |
| Original collection ASR | Python 72788 | Running, three CPU threads, bounded feature memory |
| Isolated 425-source repair launcher | PowerShell 69912 | Waiting for collection launcher 26292 to finish |

Original collection logs:

- `C:/melange-data/asr_backfill_logs/collection-bounded-20260904.stdout.log`
- `C:/melange-data/asr_backfill_logs/collection-bounded-20260904.stderr.log`
- `C:/melange-data/asr_backfill_logs/collection-repair-20260904.log`

Isolated repair logs:

- `C:/melange-data/longform_candidate_runs/automated-roster-v2-20260904/repair-bounded.stdout.log`
- `C:/melange-data/longform_candidate_runs/automated-roster-v2-20260904/repair-bounded.stderr.log`

The original worker owns `C:/melange-data/member_longform_transcripts_v1.jsonl`. The isolated worker owns its separate batch manifest. **Do not start competing writers.**

These launchers run transcription and related collection steps. **There is no running or queued end-to-end all-roster verification/profile-regeneration job.** The downstream controller described below is newly written, not launched.

## Implemented changes and verification

### Executed automated verification path

The following source files are under `C:/Users/pgoff/OneDrive/Desktop/Melange Systems/fec/`:

- `speech/longform_automated_authority.py`: honest automated provenance; exact two-pass boundary proof; no fabricated human review.
- `speech/verify_member_longform_automated.py`: recomputes complete-interior acoustic eligibility and refuses cold-start continuity as positive identity.
- `speech/materialize_member_longform_reviewed_turns.py`: accepts authorized automated verification and cuts exact source audio.
- `speech/build_member_longform_turn_features.py`: admits verified automated turns to the original whole-turn acoustic calculations.
- `speech/verify_member_longform_profile_readiness.py`: accepts automated evidence; now refuses to count a documented historical gap as verified coverage.
- `members/build_member_narrative_ledger.py`: supports automated provenance and explicit staged long-form/turn artifact paths.

Authorization is recorded in [the machine-verification authorization](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/data/speech/member_longform_automated_authorization_v1.json>).

The existing speaker thresholds, complete-interior coverage checks, original recordings, and trait/rank values were not weakened or overwritten. Exact boundary agreement between two annotation passes is not independent-interview corroboration.

### Transcription memory repair

`speech/bounded_whisper_features.py` batches FFT calculations while preserving all recording frames and whole-recording normalization. It does not split ASR requests or behavioral responses. The existing Whisper model, decoder settings, language handling, and speaker checks remain in place. The new runtime is explicitly recorded in ASR cache settings.

Numerical equivalence tests compare against the installed original feature extractor, including quiet/loud regions across batch boundaries. The bounded path is enabled in both restarted launchers. Preserve earlier transcript files and original WAVs.

### Newly written, not yet validated or launched

- `speech/classify_member_longform_two_passes_local.py`: candidate-only full-transcript two-pass Qwen inference with exact opening/closing anchors and explicit context/output limits.
- `speech/prepare_longform_candidate_model.py`: offline conversion of the existing local Qwen model to CTranslate2 int8, with input/output hashes.
- `speech/process_member_longform_automated_batch.py`: freezes completed sources, then invokes candidate reconciliation, speaker checks, automated verification, cutting, and measurements while recording every hold.

**These three new modules have not been tested or run. Do not call them production-ready.** The converted Qwen model does not yet exist. Conversion and candidate inference require additional memory planning. Quantized candidate inference is not bit-identical to the earlier Transformers runtime and must remain explicitly labeled; it does not alter acoustic measurements.

The new controller deliberately does not publish profiles. Aggregating its eventual per-source outputs into a current roster ledger and regenerating the requested prose remain unfinished.

### Tests actually completed

- Earlier relevant integration suite: **144 passed** before the latest memory/readiness/controller changes.
- Bounded-feature and local-ASR tests: **18 passed**.
- Latest readiness and narrative semantic/delivery ledger tests: **54 passed**.

These suites overlap; do not add them into a unique-test total. The three newly written downstream modules are not covered by these results.

## Remaining blockers and unfinished work

1. **Finish and recheck transcription repairs.** Fresh ASR is not automatically accurate or speaker-verified. Re-run physical timing, repetition, source/hash, and transcript quality checks; never repair timestamps by clipping or sorting them.
2. **Validate and run downstream batch processing.** Start with ready ASR sources, exercise the real local inference backend, then speaker verification and measurement. Preserve failed or unavailable cases as explicit gaps. The current automated authority route requires two exactly reconciled candidate passes; ordinary one-pass legacy classifier output is insufficient.
3. **Resolve Richard Durbin's historical source gap.** His registered current Whip tenure starts January 3, 2005. No qualifying accessible pre-2005 long-form recording has been located. A located 2004 Fox interview is only 6:57 and archive-restricted; CNN text transcripts are not verified audio. His later Washington Post recording cannot be relabeled pre-role. Do not count this gap as completed.
4. **Establish recurrence at the claim level.** A program count alone does not show the same behavior in two independently produced interviews in different settings. In particular, the existing `repeated_defensive_reactions` logic uses aggregate interaction measures plus archive program counts; inspect source-level observations before admitting recurrence language. Suggested framing fit is not demonstrated persuasion.
5. **Aggregate actual new outputs into the ledger.** Keep complete-response findings and whole-turn acoustics traceable to source-specific receipts. The existing canonical long-form feature artifact has an older contract and must be rebuilt before it can be used with the updated loader. Do not silently bypass this mismatch.
6. **Regenerate and publish only within verified coverage.** Use the approved three-paragraph, 280–300-word contract. The legacy finalizer still assumes a human-review file and does not implement the newly requested prose workflow; do not run it expecting a completed correct regeneration.

The repository is dirty with unrelated and earlier changes. Preserve them. No destructive reset, cleanup, source deletion, profile overwrite, or external publication has been performed as part of this handoff.

## Completion standard

Completion means evidence is actually processed and integrated for the requested roster, every exception is explicit, and the regenerated profiles use the supported findings in the requested form. Download counts, queued work, candidate labels, passing code tests, or a 533-row ledger do not independently establish that outcome.
