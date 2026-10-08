# Congressional member long-form audio: project context and continuation brief

> Historical snapshot. For the corrected collection counts, active processing job, source replacements, quality holds, and the user's restored three-paragraph format, read [the September 4 collection checkpoint](longform_collection_20260904/COLLECTION_STATUS.md). Do not treat the old profile-admitted count below as downloaded-recording coverage or reuse its earlier meeting implications as validated findings.

Updated: 2026-09-03 19:56 ET

## Purpose

Build a long-form interview evidence layer for every active member of Congress and use it to make each member profile concretely useful before a one-on-one lobbying meeting.

The requested product is not another personality summary. It should tell a lobbyist what they are likely to hear in the room and how to respond: how to open, what to bring, how long to let the member answer, when to interrupt or narrow, what signals are and are not meaningful, and how to close with a specific next step.

The motivating examples were these Apple Podcast episodes:

- [Steve Scalise — “Fly Out Day: Inside the shutdown with Steve Scalise”](https://podcasts.apple.com/us/podcast/fly-out-day-inside-the-shutdown-with-steve-scalise/id1549272440?i=1000732205546)
- [Maxine Waters — “U.S. Rep. Maxine Waters & Dr. Carl L. Hart”](https://podcasts.apple.com/us/podcast/u-s-rep-maxine-waters-dr-carl-l-hart/id1609823559?i=1000783986824)
- [Alex Padilla — “Sen. Alex Padilla Says His Viral Moment ‘Validated’ Democrats’ Warnings”](https://podcasts.apple.com/us/podcast/the-interview-sen-alex-padilla-says-his-viral-moment/id1200361736?i=1000730070252)

The standing mandate is to find comparable podcast or long-form interview audio for all 533 active members, extract complete conversational turns, validate speaker identity, and regenerate profiles as evidence is admitted.

## User decisions that govern the work

1. **Turns may last minutes.** An analysis window is not capped at a few seconds. A semantic turn begins when the member takes the floor and ends when another speaker takes it; one turn can last seconds, minutes, or many minutes.
2. **Profiles must be operational.** Avoid language that merely says a member is warm, cool, exploratory, rigid, visible, or hard to fluster. Translate supported findings into observable meeting behavior and specific preparation or pacing choices.
3. **Leadership changes the audio.** For Mike Johnson, Steve Scalise, and every other current formal leader, the behavioral baseline must come from audio recorded before the member assumed the current leadership role. Later audio can describe current practice but must be marked as role-conditioned.
4. **Scalise requires a precise reading.** The evidence supports a brief person-first opening and suggests that he uses individual conversations and familiarity before consequential decisions. It does not establish that he always requires small talk or a separate conversation before every formal meeting.
5. **Search broadly.** Apple Podcasts supplied the examples, but Google/general-web discovery, YouTube, radio archives, university interviews, conference recordings, and direct podcast feeds are valid source routes when the recording is genuinely long-form and attributable.

## Evidence and promotion contract

An episode title, search result, description, thumbnail, or publication page is a lead—not member-level behavioral evidence. Promotion requires all of the following:

1. A physically acquired WAV and its SHA-256 hash.
2. Timestamped ASR tied to that source and hash.
3. A literal in-band full-name cue localized in the transcript.
4. One or more complete turns bounded at actual speaker handoffs.
5. Acoustic speaker-continuity evidence across the turn.
6. Human review of identity, turn boundaries, and the claimed semantic finding.
7. An explicit source-era classification for current leaders.

Eight-second windows are permitted for identity and acoustic comparison only. They are not conversational turns and must never drive a meeting recommendation by themselves.

This audio layer is descriptive only. It must not alter Big Five scores, rankings, stance, allocation, or persuasion-engine output.

## What is extracted from a long-form recording

For an admitted source, the retained evidence includes:

- member and source identifiers;
- episode title, source URL, recording/publication dates, duration, and leadership-era classification;
- normalized WAV path and SHA-256;
- timestamped transcript path and hash;
- literal identity-cue timestamps;
- full member-turn start/end times, duration, and transcript;
- speaker-continuity windows and comparison result;
- human identity, boundary, and semantic-review decision;
- narrowly worded conversational observations; and
- concrete one-on-one implications, with the evidence limitation preserved.

The intended profile output has four practical fields:

- **Open:** the first sentence and framing order.
- **Bring:** the decision, evidence, implementation detail, and format to have ready.
- **Run the room:** expected answer length, floor-holding, question cadence, and how to narrow without misreading the member.
- **Close:** named owner, deliverable, and date.

## Leadership source-era policy

The strict baseline rule is:

`recorded_at < current_role_assumed_on`

Publication date is a conservative proxy only when the recording date is unavailable. A later archival upload qualifies as pre-role only when an authoritative source documents that the recording itself predates the cutoff.

Audio recorded on or after the cutoff is tagged `CURRENT_ROLE_CONDITIONED`. It remains useful for current-day meeting tactics but cannot, by itself, establish a stable role-independent baseline.

The current cutoff registry covers all 27 formal leaders in `data/members/formal_visibility_roles.json`. Twenty-six have an acquired, hash-bound pre-current-role source. Richard Durbin is the explicit gap: his current whip tenure began in 2005, and the only older interview located is a restricted 6:57 archival recording.

Representative selected sources include Mike Johnson in 2022, Steve Scalise in 2020, Amy Klobuchar in 2016, Bernie Sanders in 2016, Catherine Cortez Masto in 2016, Chuck Schumer in 2007, Elizabeth Warren in 2015, John Thune in 2023, John Barrasso in 2024, Mark Warner in 2014, Pete Aguilar in 2022, Shelley Moore Capito in 2020, Tammy Baldwin in 2016, Tom Cotton in 2017, and Tom Emmer in 2021.

Authoritative cutoff references are anchored to the [House leadership directory](https://www.house.gov/leadership), [Senate leadership directory](https://www.senate.gov/senators/leadership.htm?lv=true), [House Speaker history](https://history.house.gov/People/Office/Speakers-List/), [House Majority Leader history](https://history.house.gov/People/Office/Majority-Leaders/), [Senate floor-leader history](https://www.senate.gov/about/parties-leadership/majority-minority-leaders.htm), and [Senate whip history](https://www.senate.gov/about/parties-leadership/party-whips.htm).

## Verified findings already promoted

### Mike Johnson

- Source: Better for America interview, recorded 2022-03-24, before he became Speaker on 2023-10-25.
- Source ID: `381a280129f9`
- Audio: `C:\melange-data\member_leadership_prerole_audio_v1\mike-johnson__381a280129f9.wav`
- WAV SHA-256: `0fd12c8f57eb0f6cccfd9cea67a6cc877ad5497e236916bdcd23421db1e3bfc3`
- Transcript SHA-256: `deb4805a6a508f67a384a3034ad10a586ab892beaef9c1a27bbbf2a2a2fc0d0b`
- Reviewed turn: 161.71–295.91 seconds; 134.20 seconds; 401 words.
- Identity evidence: four literal name cues and 16 consecutive exact eight-second windows that passed the all-vault zero-false-accept calibration.

Observed implication: a broad compound question produced a multi-minute answer that established principle before stating an operational boundary.

Meeting translation: open with the requested action and deadline, connect it to one governing principle, and state the implementation limit. If time is short, ask one narrow question first. Bring a one-page decision memo, let the answer finish, and if the response stays at principle level, acknowledge the principle once and narrow to a concrete A/B choice.

### Steve Scalise

- Source: *The Takeout*, recorded 2020-02-07, before he became House Majority Leader on 2023-01-03.
- Source ID: `0ec06fa55008`
- Audio: `C:\melange-data\member_leadership_prerole_audio_v1\steve-scalise__0ec06fa55008.wav`
- WAV SHA-256: `a09757c6159b39db92841b517743280547fbaaa0650cfd62bb93673d0b51981e`
- Transcript SHA-256: `ae368d673a039d4ba4ab8bedcab8a0027e5cc3efe26620b970ca37e327aa35ca`
- Reviewed turn: 111.12–182.26 seconds; 71.14 seconds.
- Identity evidence: eight literal name cues and three consecutive exact eight-second windows matched to independent verified Scalise event references ahead of every vaulted competitor. This is supplemental event-reference continuity, not a zero-false-accept claim.

Observed implication: in this pre-role lunch interview, a personal health check-in elicited an appreciative, detailed 71-second answer before policy discussion. Later 2023 material—correctly retained as `CURRENT_ROLE_CONDITIONED`—describes individual conversations, familiarity, and trust around consequential decisions.

Meeting translation: use a brief, bounded personal or shared-context opening, then make an explicit pivot to the decision and deadline. Budget for a real answer; ask one question at a time; do not confuse low interruption or a long response with agreement. Bring a one-page ask and close with an owner, deliverable, and date.

The defensible claim is that person-first rapport is useful with Scalise. The evidence does **not** justify “he always wants to talk first” as a universal rule.

### User-supplied seed set

The Scalise, Maxine Waters, and Alex Padilla episodes were resolved to public audio, transcribed locally, and paired with independently discovered companion sources. Across the six sources, 18 exact identity/acoustic windows are verified. The original seed pipeline retains seven reviewed semantic turns; the two promoted pre-role leadership turns bring the active total to nine turns across four profiles.

## Roster-wide acquisition state

- 533/533 active members have a normalized, physically acquired primary long-form recording.
- The automated discovery ledger contains 1,410 YouTube candidates for 522 members; general-web review supplied the remainder.
- Ten obvious homonym or about-the-member source errors were manually replaced: Christopher Smith, Frederica Wilson, Rick Crawford, Jeff Hurd, Mark Harris, Neal Dunn, Bobby Scott, Tim Kennedy, Laura Friedman, and Brad Schneider.
- Sixty-one initially usable transcripts lacked a literal full-name cue. Four were already covered by reviewed replacements; 57 distinct second recordings were acquired, preserving the originals.
- Primary and second-source acquisition have zero acquisition errors.
- Acquisition does not equal promotion. Most sources still require transcript recovery, identity localization, complete-turn extraction, continuity checks, and human review.

## Active evidence/profile snapshot

The regenerated evidence artifact currently reports:

| Measure | Count |
|---|---:|
| Active members | 533 |
| Profiles with speech gate passing | 533 |
| Profiles with general audio | 501 |
| Profiles with setting audio | 427 |
| Profiles with admitted long-form interview evidence | 4 |
| Admitted long-form turns | 9 |
| Profiles with admitted full turns | 4 |
| Formal leaders covered by source-era policy | 27 |
| Acquired leadership pre-role sources pending promotion | 24 |
| Leadership pre-role sources human-review promoted | 2 |
| Active generated narratives | 533/533 |

All 533 profiles have a deterministic `Open` / `Bring` / `Run the room` / `Close` meeting playbook. Only admitted evidence may individualize those instructions.

## In-progress transcription snapshot

These counts were read at 2026-09-03 19:56 ET and are transient because both local-ASR lanes were still running.

| Ledger | Ready | Still local-ASR-required | Provider/transcript error | Other |
|---|---:|---:|---:|---:|
| 533-member primary | 278 caption-ready + 27 local-ASR-ready | 10 | 215 | 3 reused verified ASR |
| 26 leadership pre-role sources | 12 local-ASR-ready | 9 | 5 | — |
| 57 no-name-cue second sources | 0 | 5 | 52 | — |

The provider errors are explicit failures caused by YouTube caption IP/HTTP 429 blocking. They are not counted as transcripts. The acquired audio remains available for resumable local ASR.

Running processes at the snapshot:

- Primary ASR: Python PID `9916`.
- Leadership ASR: Python PID `50640`.
- Primary continuation wrapper: PowerShell PID `3732`.
- Leadership/secondary continuation wrapper: PowerShell PID `43100`.

The wrappers wait for the current passes, retry retained errors, rerun identity-cue screening, and write logs under `C:\melange-data\asr_backfill_logs`. Process IDs are ephemeral; verify the command lines rather than assuming the PIDs remain valid.

## Artifact map

### Discovery, source review, and acquisition

- `data/speech/member_longform_youtube_discovery_v1.jsonl`
- `data/speech/member_longform_acquisition_queue_v1.jsonl`
- `data/speech/member_longform_acquisition_v1.jsonl`
- `data/speech/member_longform_reviewed_source_overrides_v1.jsonl`
- `data/speech/member_longform_no_cue_retry_discovery_v1.jsonl`
- `data/speech/member_longform_no_cue_retry_queue_v1.jsonl`
- `data/speech/member_longform_no_cue_retry_acquisition_v1.jsonl`

### Leadership era

- `data/speech/member_leadership_role_cutoffs_v1.json`
- `data/speech/member_leadership_prerole_discovery_v1.jsonl`
- `data/speech/member_leadership_prerole_reviewed_sources_v1.jsonl`
- `data/speech/member_leadership_prerole_acquisition_queue_v1.jsonl`
- `data/speech/member_leadership_prerole_acquisition_v1.jsonl`
- `data/speech/member_leadership_prerole_full_turn_candidates_v1.jsonl`
- `data/speech/member_leadership_prerole_speaker_continuity_v1.jsonl`
- `data/speech/member_leadership_prerole_human_reviews_v1.jsonl`
- `data/speech/member_leadership_prerole_long_turns_v1.jsonl`

### Admitted evidence and profiles

- `data/speech/member_interview_long_turns_v1.jsonl`
- `data/members/member_narrative_evidence_v4.json`
- `member_narratives_v2.json`
- `data/members/member_desk_bundle.json`
- `cu-member-desk-profiles.js`
- `cu-member-desk.html`

### Pipeline code

- `fec/speech/transcribe_member_longform_local_asr.py`
- `fec/speech/screen_member_longform_identity_cues.py`
- `fec/speech/verify_member_longform_speaker_continuity.py`
- `fec/speech/materialize_leadership_prerole_reviewed_turns.py`
- `fec/speech/continue_member_longform_asr_backlog.ps1`
- `fec/members/build_member_narrative_ledger.py`
- `fec/members/build_member_meeting_playbooks.py`
- `fec/members/refresh_member_profiles_20260903.py`

Large WAVs and transcript holdings intentionally live outside OneDrive under `C:\melange-data`.

## Verification already completed

- The consolidated long-form discovery, acquisition, caption, local-ASR, cue, turn, speaker-continuity, leadership-era, materialization, and profile-playbook suite last passed: **62 passed, 0 failed**.
- New coverage includes `fec/tests/speech/test_materialize_leadership_prerole_reviewed_turns.py` and `fec/tests/members/test_leadership_audio_source_era.py`, plus enhanced speaker-continuity and narrative-repair tests.
- `data/members/member_narrative_evidence_v4.json` and `member_narratives_v2.json` were regenerated after the Johnson and Scalise promotions.

The rendered desk bundle is intentionally still the last integrity-passing build. A full surface render is blocked by an unrelated ratified pillar-weight mismatch. Do not bypass that policy gate or imply the desk surface contains newer data until the mismatch is resolved and the renderer passes.

## Safe continuation sequence

1. Confirm the two ASR processes and two wrapper processes are still active, or inspect their completion logs.
2. Recount all three transcript ledgers after the wrappers finish; do not reuse the transient table above as final state.
3. Review the regenerated identity-cue ledgers. A name cue creates a candidate, not a promotion.
4. For each candidate, extract the member’s complete floor-taking-to-handoff turns without a duration ceiling.
5. Run speaker continuity over the full turn, then perform human identity, boundary, and semantic review.
6. For leaders, reject or role-condition any source that does not satisfy the strict recording-date cutoff.
7. Materialize only reviewed turns, rebuild the narrative ledger and meeting playbooks, and regenerate profiles.
8. Run the focused test suite and compare artifact counts and hashes.
9. Resolve the independent pillar-weight mismatch before rebuilding the rendered desk surface.

Useful live checks:

```powershell
Get-CimInstance Win32_Process |
  Where-Object {
    $_.CommandLine -like '*transcribe_member_longform_local_asr*' -or
    $_.CommandLine -like '*continue_member_longform_asr_backlog*'
  } |
  Select-Object ProcessId, ParentProcessId, Name, CommandLine

Get-ChildItem -LiteralPath 'C:\melange-data\asr_backfill_logs' -File |
  Sort-Object LastWriteTime |
  Select-Object Name, Length, LastWriteTime
```

## Definition of done

The project is not complete merely because every member has an audio file. It is complete when every member has at least one long-form source that has passed the full evidence contract, every current leader has a valid pre-current-role baseline or an explicit documented gap, complete turns have been human reviewed, concrete meeting implications have been regenerated, all tests pass, and the rendered surface is rebuilt without bypassing policy gates.

The fuller implementation audit is in `audits/MEMBER_LONGFORM_AUDIO_AND_MEETING_PLAYBOOK_REFRESH_20260903.md`.
