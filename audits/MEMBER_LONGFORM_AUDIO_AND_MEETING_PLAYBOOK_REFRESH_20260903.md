# Member long-form audio and meeting-playbook refresh

Date: 2026-09-03

## Outcome

- All 533 active members now have a physically acquired, normalized, SHA-256-bound primary long-form recording. Three are already fully identity-verified; the other 530 remain explicitly identity-unverified until promotion gates pass.
- The search ledger contains 1,410 YouTube candidates for 522 members. General-web review supplied the remaining primary sources, and ten obvious homonym/about-the-member errors were replaced with manually reviewed sources before reacquisition.
- Sixty-one usable first transcripts lacked a literal in-band full-name cue. Four were already covered by a reviewed primary replacement, and 57 different second recordings were acquired without discarding the first source.
- The three user-supplied interviews were resolved to public audio, transcribed locally, speaker-checked, and paired with independent companion sources. Six sources and 18 exact identity/acoustic windows are fully verified.
- Seven complete reviewed semantic turns are retained from those sources. A turn begins when the member takes the floor and ends at the next speaker handoff; it has no duration ceiling and may last seconds, minutes, or many minutes.
- Every active profile has an operational one-on-one meeting playbook: `Open`, `Bring`, `Run the room`, and `Close`.
- Current formal leaders now have a separate pre-current-role source ledger. Twenty-six of 27 have an acquired pre-role recording, totaling 17.4 hours; all are at least 20 minutes. Dick Durbin is an explicit historical gap because his current whip tenure began in 2005 and the only older interview located is a restricted 6:57 archival item.
- Mike Johnson and Steve Scalise are the first pre-current-role sources promoted through the complete evidence chain. The other 24 acquired leadership sources remain pending transcription and review, not silently treated as profile evidence.

## Leadership source-era rule

For a current formal leader, audio recorded before the member assumed the current leadership office supplies the behavioral baseline. Audio recorded later is retained as `CURRENT_ROLE_CONDITIONED`: it may describe useful present-day behavior but cannot alone establish a stable, role-independent style.

This distinction is now enforced in the source ledger, narrative evidence builder, writer prompt, reviewer prompt, and meeting-playbook derivation. A later archival upload may qualify only when an authoritative source documents that the recording itself occurred before the cutoff.

Examples:

- Mike Johnson: a 32-minute Better for America interview recorded March 24, 2022, nineteen months before he was elected Speaker.
- Steve Scalise: a 50-minute *The Takeout* interview recorded February 7, 2020, before he became Majority Leader.
- John Thune: a 26-minute 2023 Agri-Pulse interview before he became Majority Leader.
- John Barrasso: a 23-minute December 2024 WSJ interview before he became Majority Whip.

The existing reviewed Scalise turns are from 2023 and 2025, after he became Majority Leader, and remain labeled role-conditioned. His 2020 *Takeout* interview has now passed ASR, eight literal name cues, full-turn boundary review, three consecutive speaker-continuity windows against independent verified event references and every vaulted competitor, and human review. In the admitted 71-second answer, a personal health check-in elicits a substantive reply before policy. Combined with the later accounts of individual conversations, familiarity, and trust, this supports a brief person-first opening. It does not prove that he always requires small talk or a conversation before every meeting.

Mike Johnson's 2022 pre-Speakership interview has also been promoted. Four literal name cues and 16 consecutive all-vault zero-false-accept speaker matches bind a reviewed 134.2-second answer. A broad two-part question produces a multi-minute, principle-first response before he states the operational boundary. His playbook now tells the lobbyist to open with the decision, deadline, governing principle, and limit, and to ask one narrow question first when time is constrained.

## Verified seed sources

| Member | User-supplied episode / public audio | Independently discovered companion |
|---|---|---|
| Steve Scalise | Punchbowl News, “Fly Out Day: Inside the shutdown with Steve Scalise” | POLITICO Playbook Deep Dive, “Steve Scalise reveals what’s really happened since McCarthy’s fall” |
| Maxine Waters | Tavis Smiley, “U.S. Rep. Maxine Waters & Dr. Carl L. Hart” | Our Body Politic, “Congresswoman Maxine Waters on How the Democratic Party Moves Forward” |
| Alex Padilla | The New York Times, “Sen. Alex Padilla Says His Viral Moment ‘Validated’ Democrats’ Warnings” | Making Los Angeles, “Alex Padilla: From Pacoima to Power” |

Public source URLs and the original Apple episode URLs are bound into `data/speech/member_interview_descriptive_v1.json`.

## Promotion contract

An episode title, search result, or directory record is only a lead. Profile promotion requires:

1. a physical audio holding and SHA-256 hash;
2. timestamped ASR with a transcript-localized, literal in-band naming cue;
3. complete member turns from floor-taking through speaker handoff;
4. accepted speaker-continuity evidence across the turn;
5. human identity, boundary, and semantic review; and
6. the descriptive-only contract.

Eight-second excerpts are identity/acoustic probes, not conversational turns. Search metadata never proves identity. The added audio cannot change Big Five values, member ranks, stance, allocation, or persuasion-engine output.

## Roster-wide acquisition and transcription state

Primary acquisition:

- 533/533 recordings acquired;
- 530 identity-unverified and three already identity-verified;
- zero acquisition errors or provider-resolution gaps.

Second-source retry:

- 57/57 different recordings acquired for the no-name-cue retry set;
- zero acquisition errors;
- first recordings preserved.

The second-source caption pass is also materialized: five direct/non-captioned
sources are explicitly queued for local ASR and 52 YouTube sources retain a
visible provider-error status after the same IP/HTTP 429 caption block. No
failed caption lookup is counted as a transcript.

At the start of local-ASR recovery, the 533-source transcript ledger contained 283 caption-ready transcripts, three reused verified transcripts, 31 sources needing local ASR, and 216 YouTube caption errors caused by provider IP/HTTP 429 blocking. Local ASR is resumable and writes each completed transcript atomically. The remaining provider-error audio is approximately 129.7 hours; it is retained for a later provider retry or staged local transcription, not silently treated as usable text.

The hard literal-name screen over the initially usable transcripts found 587 cue instances across 225 members. Those are candidates for turn localization, not identity promotions.

Two resumable four-thread local-ASR lanes are active. After the current 23-source primary repair pass, a hidden continuation runner will process the 216 retained provider-error recordings and rerun the primary identity-cue screen. After the current leadership pass, the second lane will rerun the leadership cue screen, transcribe all 57 second-source recordings locally, and screen those transcripts. Logs are written under `C:\melange-data\asr_backfill_logs`.

## Leadership pre-role acquisition state

- 27 current formal leaders in the cutoff registry;
- 26 manually reviewed pre-current-role sources acquired and hash-bound;
- six YouTube and 20 direct podcast/radio sources;
- 17.4 measured audio hours;
- shortest source 20.1 minutes, longest 66.0 minutes;
- zero acquisition errors;
- one explicit historical long-form gap: Richard Durbin.

The initial caption pass placed all 26 into transcription recovery: the six YouTube sources encountered the same caption-provider block and the 20 direct sources required local ASR. At that stage none had identity authority or profile effect.

The first three leadership sources are locally transcribed and each contains literal in-band name cues. Mike Johnson and Steve Scalise are human-review promoted; Charles Schumer remains a transcript/cue candidate only. Local ASR is continuing over the remaining leadership queue, including the six caption-provider errors.

## Practical one-on-one translation

Each active member carries a deterministic meeting playbook derived only from admitted evidence:

- `open`: the literal first sentence and framing order;
- `bring`: a one-page decision, deadline, affected people, and implementation path;
- `run_the_room`: observable turn length, floor-holding, rapid-exchange, and repeated-defense cues translated into pacing choices; and
- `close`: a named office owner, next deliverable, and date, with pressure language scaled to the measured evidence.

For Scalise, the current playbook now says explicitly that the brief personal/shared-context opening is observed in current-role interviews and remains a current-practice finding until the pre-role source confirms the baseline.

## Main artifacts

- `data/speech/member_longform_youtube_discovery_v1.jsonl`
- `data/speech/member_longform_acquisition_queue_v1.jsonl`
- `data/speech/member_longform_acquisition_v1.jsonl`
- `data/speech/member_longform_reviewed_source_overrides_v1.jsonl`
- `data/speech/member_longform_no_cue_retry_discovery_v1.jsonl`
- `data/speech/member_longform_no_cue_retry_queue_v1.jsonl`
- `data/speech/member_longform_no_cue_retry_acquisition_v1.jsonl`
- `data/speech/member_leadership_role_cutoffs_v1.json`
- `data/speech/member_leadership_prerole_discovery_v1.jsonl`
- `data/speech/member_leadership_prerole_reviewed_sources_v1.jsonl`
- `data/speech/member_leadership_prerole_acquisition_queue_v1.jsonl`
- `data/speech/member_leadership_prerole_acquisition_v1.jsonl`
- `data/speech/member_leadership_prerole_full_turn_candidates_v1.jsonl`
- `data/speech/member_leadership_prerole_speaker_continuity_v1.jsonl`
- `data/speech/member_leadership_prerole_human_reviews_v1.jsonl`
- `data/speech/member_leadership_prerole_long_turns_v1.jsonl`
- `data/speech/member_interview_long_turns_v1.jsonl`
- `data/members/member_narrative_evidence_v4.json`
- `member_narratives_v2.json`

Large WAV and transcript holdings remain outside the OneDrive repository under `C:\melange-data`.

## Verification

- Leadership selection tests enforce exact roster coverage, strict pre-role dates, explicit gaps, and long-form duration when known.
- Source-era tests enforce the strict cutoff and require role-conditioned relationship evidence to be labeled in the playbook.
- Acquisition, caption, local-ASR, identity-cue, full-turn, and speaker-continuity stages have dedicated unit tests.
- The active 533-member narrative evidence and meeting-playbook artifacts were regenerated after source-era separation.
- `python -m pytest` over the long-form discovery, acquisition, caption, local-ASR, identity-cue, turn-classification, speaker-continuity, leadership-era, promotion-materialization, and profile-playbook suites passes all 62 tests.

The active source profile artifact is regenerated. The already-rendered desk files remain the last integrity-passing surface build because the full desk renderer is currently blocked by an unrelated ratified pillar-weight mismatch; this work does not bypass or silently rewrite that policy gate.

Final ASR counts are appended after the in-progress local transcription passes finish.
