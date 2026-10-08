# Long-form collection: corrected status and continuation

Checkpoint: September 4, 2026, approximately 16:45 ET. This is a checkpoint, not a claim that evidence review or profile generation is complete.

## What the user requested

Collect podcast/long-form evidence for every member first. Then write exactly three paragraphs, totaling 200–250 words: **personality; speech & landmines; approach**. Do not substitute an archive-coverage summary for that structure. Follow the evidence, retain uncertainty, and distinguish public observations from private-meeting predictions. See [PROFILE_CONTRACT.md](PROFILE_CONTRACT.md).

## Corrected collection finding

Full primary recordings were already present for all 533 members. The earlier statement about only four members concerned the old profile-admitted response excerpts, not downloaded recordings. Confusing those stages materially misrepresented how much had been collected.

This run replaced all 50 superseded primary source selections and preserved the original audio and ledger snapshots. The completed acquisition receipt now verifies:

- 533/533 primary recordings matching the current source queue.
- Zero acquisition errors, unresolved media routes, missing members, source mismatches, or invalid media hashes.
- 285.028 hours in the current primary collection; every primary file is at least ten minutes long.
- These are physically verified recordings and source bindings, not 533 verified member-speaker or behavioral reviews. Three rows retain historical identity-verified status; 530 remain explicitly identity-unverified.

The independent earlier file audit also verified 57 first-additional-source recordings, 32 second-additional-source recordings, and 26 pre-current-role leadership recordings. All 115 have transcript entries. Distinct recording hashes do not establish independent interviews or recurring behavior.

## What is running

The provider caption route returned repeated HTTP 429 rate limits. That worker was stopped; no attempt is being made to evade the limit. Local, original-language transcription is running instead.

- Runner: `fec/speech/continue_member_longform_collection_20260904.ps1 -CpuThreads 4`.
- Active tool session at this checkpoint: `25728`.
- Python PID checked at this checkpoint: `19520`; verify command line before relying on a PID.
- Log: `C:\melange-data\asr_backfill_logs\collection-repair-20260904.log`.
- Primary transcript manifest: `C:\melange-data\member_longform_transcripts_v1.jsonl`.
- Started with 52 pending source-bound transcripts, representing 25.63 hours of recordings. Daniel Webster's first replacement transcript has completed. Subsequent counts change during the run.
- After that backlog, the runner refreshes six specifically quality-held transcripts, preserving previous files, then refreshes primary name-cue candidates.
- The runner does **not** select or promote sources, certify speakers, approve semantic claims, or generate profiles.

Do not launch a second transcript writer. The finite runner holds `C:\melange-data\member-longform-collection-writer.lock` while active. Local ASR uses automatic language detection instead of forced English, and disables previous-text conditioning for this repair run. Language, conditioning, and model-path requests are bound to distinct caches.

## Quality problems being repaired

Exact-hash holds are recorded in `quality_holds.jsonl`:

- Maria Salazar, Pete Stauber, Robert Scott: suspected repeated-text ASR loops.
- Cynthia Lummis: retained captions cover only approximately one quarter of the recording.
- Emanuel Cleaver: transcript timestamps extend beyond the audio.
- Haley Stevens: unusually high text density requires inspection.

These are diagnostic flags, not psychological or behavioral findings. Fresh transcript hashes alone do not prove a repair succeeded. Re-run the transcript quality audit and update the exact-bound holds before source selection.

## New historical lead

A new 21:18 recording featuring Richard Durbin was acquired and hash-verified at `C:\melange-data\discovery_media_20260904\richard-durbin__tobacco-bfx27a00.wav`. Its original catalog date is inconsistent. The potential pre-1992 bound remains provisional, so this discovery has **not** silently cleared the pre-current-role gap. See [durbin_discovery.json](durbin_discovery.json) for the primary archival references and unresolved date evidence.

## Completed safeguards

- Acquisition resume now checks actual media and current source bindings. Failed retries preserve the original audio and prior provenance.
- Queue writes tolerate transient OneDrive file locks.
- A selector bug that could pair old transcripts/cues with replacement audio is fixed. Current cue, transcript, and acquisition identities, paths, and file hashes must agree.
- `superseded_primary_sources.jsonl` records exactly 50 member-scoped primary exclusions. Some were replaced for format/context; the ledger does not call all 50 wrong-person recordings.
- The selector accepts explicit quality holds and can return a pending status or choose a legitimate alternative.
- 109 focused acquisition, queue, ASR, shared-transcription, selector, and continuation tests passed in the final combined test run.

## Next actions after the active run

1. Inspect the runner exit state and fresh transcript receipt; verify current acquisition/transcript source bindings and missing/error counts.
2. Re-run `audit_primary_transcript_quality.py` from this directory and inspect its flags. Reissue quality holds for unresolved or newly detected defects.
3. Refresh all four cue streams as needed, then run the lineage audit.
4. Use the explicit source-selection command in [SELECTION_REFRESH_COMMANDS.md](SELECTION_REFRESH_COMMANDS.md), including both the superseded-source and quality-hold ledgers. The older general continuation wrapper does not yet include those arguments and must not be used unmodified.
5. Review actual speaker identity, full response boundaries, interview context, and semantic observations under the existing evidence-review requirements. Do not turn software or model output into a human attestation.
6. Only then generate the requested three-paragraph profiles. No new profile generation occurred during this collection correction. The preceding descriptive-format rewrite remains the previously published artifact, not the requested final replacement.

Single-source observations are provisional. Recurring patterns require matching observations in two independently produced interviews in different settings. Preserve conflicting evidence, pre-current-role leadership context, and the explicitly secondhand status of Scalise's football example.
