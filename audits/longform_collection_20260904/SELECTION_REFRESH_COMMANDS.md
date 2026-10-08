# Source-selection refresh after acquisition reconciliation

Do not run selection while an acquisition/transcript writer is active. These are operator commands, not an automatic profile-generation instruction. The selector now fails before writing when cue, transcript, and acquisition identities or hashes disagree, when physical file hashes fail, or when an input changes during verification.

The 2026-09-04 20:30 UTC diagnostic found 30 primary transcript/acquisition mismatches, 37 primary cue/acquisition mismatches, and eight cue/transcript mismatches. The first-retry, second-retry, and leadership streams had zero row-binding mismatches. Those are time-stamped observations during ongoing remediation, not final remaining counts. The old selector could have mixed an old transcript with replacement audio in 36 selected choices. That join is now prohibited.

## 1. Refresh changed primary transcripts

After acquisition reconciliation finishes, use the current primary manifest. Resume detects changes in source ID or WAV hash and processes replacements. This stage provides candidate transcripts, not human review.

At the current September 4 checkpoint, the caption provider returned repeated HTTP 429 rate limits and the caption worker was stopped. Do not keep retrying the blocked route. The finite `fec/speech/continue_member_longform_collection_20260904.ps1 -CpuThreads 4` job is running local original-language ASR, then the six exact-hash quality repairs, then a fresh primary cue screen. It never generates profiles. The standalone commands below document the stages; do not launch another writer while that job is active.

```powershell
python -m fec.speech.transcribe_member_longform_captions `
  --acquisition data\speech\member_longform_acquisition_v1.jsonl `
  --out C:\melange-data\member_longform_transcripts_v1.jsonl `
  --receipt C:\melange-data\member_longform_transcripts_v1.receipt.json `
  --transcript-root C:\melange-data\member_longform_transcripts_v1 `
  --resume --retry-errors --retry-local-asr --workers 1 --request-delay 5

python -m fec.speech.transcribe_member_longform_local_asr `
  --acquisition data\speech\member_longform_acquisition_v1.jsonl `
  --transcripts C:\melange-data\member_longform_transcripts_v1.jsonl `
  --receipt C:\melange-data\member_longform_transcripts_v1.receipt.json `
  --transcript-root C:\melange-data\member_longform_transcripts_v1 `
  --cpu-threads 4 --shortest-first --retry-errors --language auto --no-condition-on-previous-text
```

Review and repair quality-held sources separately, then rerun the quality assessment. Pass its fresh exact-bound hold ledger to selection. A changed transcript hash is not a quality pass. Do not rerun an unchanged retry or leadership transcription merely to refresh a date.

## 2. Rebuild cue screens from current transcripts

These explicit paths avoid the screen's older workspace-relative defaults. Run each stream only after its transcript work has finished and its receipt matches the current acquisition manifest. The screen checks transcript-file hashes but does not verify speaker identity or WAV content; the hardened selector checks the full linkage and file hashes.

```powershell
$CollectionStems = @(
  'member_longform',
  'member_longform_no_cue_retry',
  'member_longform_no_cue_retry2',
  'member_leadership_prerole'
)
foreach ($CollectionStem in $CollectionStems) {
  python -m fec.speech.screen_member_longform_identity_cues `
    --transcripts "C:\melange-data\${CollectionStem}_transcripts_v1.jsonl" `
    --output "C:\melange-data\${CollectionStem}_identity_cues_v1.jsonl" `
    --receipt "C:\melange-data\${CollectionStem}_identity_cues_v1.receipt.json"
  if ($LASTEXITCODE -ne 0) { throw "Cue screen failed: $CollectionStem" }
}

python audits\longform_collection_20260904\audit_selection_lineage.py
```

The diagnostic must show zero mismatched rows for any stream about to be used. Preserve explicit pending or quality-held sources instead of reusing old positive cues. If a fourth-source stream is later acquired, transcribe and screen it by the same process before adding its paths below.

## 3. Select candidate sources with both exclusion ledgers

`superseded_primary_sources.jsonl` contains exactly 50 member-scoped primary substitutions derived from the preserved before-reconciliation acquisition manifest. It is not a declaration that every old recording contains the wrong person; some substitutions concern format or context. Old files remain preserved. A legitimate additional recording remains eligible unless its own source is specifically superseded or quality-held.

The QA-produced `quality_holds.jsonl` must exist and be current before this command. Each hold binds the exact member, source ID, WAV hash, and transcript hash. A matching held source is excluded; another valid source may be selected, otherwise the member receives an explicit quality-review-pending status. Absence from this list grants no human-review authority.

```powershell
python -m fec.speech.select_member_longform_profile_sources `
  --primary-queue data\speech\member_longform_acquisition_queue_v1.jsonl `
  --rejected-sources audits\longform_collection_20260904\superseded_primary_sources.jsonl `
  --quality-holds audits\longform_collection_20260904\quality_holds.jsonl `
  --primary-acquisition data\speech\member_longform_acquisition_v1.jsonl `
  --primary-transcripts C:\melange-data\member_longform_transcripts_v1.jsonl `
  --primary-cues C:\melange-data\member_longform_identity_cues_v1.jsonl `
  --retry-acquisition data\speech\member_longform_no_cue_retry_acquisition_v1.jsonl `
  --retry-transcripts C:\melange-data\member_longform_no_cue_retry_transcripts_v1.jsonl `
  --retry-cues C:\melange-data\member_longform_no_cue_retry_identity_cues_v1.jsonl `
  --retry2-acquisition data\speech\member_longform_no_cue_retry2_acquisition_v1.jsonl `
  --retry2-transcripts C:\melange-data\member_longform_no_cue_retry2_transcripts_v1.jsonl `
  --retry2-cues C:\melange-data\member_longform_no_cue_retry2_identity_cues_v1.jsonl `
  --leader-acquisition data\speech\member_leadership_prerole_acquisition_v1.jsonl `
  --leader-transcripts C:\melange-data\member_leadership_prerole_transcripts_v1.jsonl `
  --leader-cues C:\melange-data\member_leadership_prerole_identity_cues_v1.jsonl `
  --out data\speech\member_longform_profile_source_selection_v1.jsonl `
  --receipt data\speech\member_longform_profile_source_selection_v1.receipt.json
```

The output remains candidate selection only. Preserve the human-only identity, boundary, and semantic review requirement before profile evidence is promoted. No profile generation is included here.
