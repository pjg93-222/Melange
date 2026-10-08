# Audio and public behavior: methodology review and consultation

Date: 2026-09-04. Scope: descriptive analysis of recorded public communication and the validity of the resulting claims.

## Decision reached with the user

A recurring communication pattern requires the same observable behavior in at least two independently produced interviews in different settings. A single interview is provisional. Two recordings are a minimum evidence rule chosen for this project, not a scientifically validated sample size or proof of a stable trait.

Multiple clips, answers, uploads, syndications, or platform URLs from one production count as one interview. Independence and setting must be reviewed explicitly. Different channel names alone do not prove independence. Missing context means the claim remains provisional. Contradictory observations remain visible and prevent an unqualified recurring-pattern label.

Define settings by the interaction design (for example, an informal biographical interview versus a moderated public policy interview), not merely by platform or show name. Keep interviewer familiarity, live/edited format, audience, and question style as separate context fields. The setting vocabulary should be agreed during the pilot so changing labels cannot manufacture apparent replication.

The user described a report that Steve Scalise asks about incidental subjects, such as football, before substantive discussion. The user clarified this was reported to them. Frequency, date, original observer, and source-era details remain unknown. The report is preserved in `data/speech/member_behavior_field_reports_v1.jsonl`; it contributes zero verified interviews.

## What the current system actually establishes

The active narrative artifact contains 533 profiles. Its evidence ledger marks nine complete turns across four members as admitted long-form evidence, totaling approximately 13.44 minutes. These are stored admission statuses, not a new independent listening review or confirmation that every historical review has the provenance required by the newer workflow. The other 529 members do not yet have admitted complete long-form turns in this ledger.

All 533 meeting cards are populated, but 531 openings derive from generic or percentile rules. Four cards expose long-form examples. A populated card and a general speech `PASS` therefore cannot mean that a recurring interview behavior has been established.

Earlier acquisition coverage of 533 audio slots is also distinct from valid source coverage: reviewed source replacements still require acquisition reconciliation and downstream processing. At this review's process check, no transcription or classifier worker was running; the last primary transcript receipt remained partial. Do not describe the old CPU job as still progressing without a new process check.

## Findings requiring correction

| Current mechanism | What it supports | Required correction |
|---|---|---|
| Caption duration divided evenly among words | Approximate locations for searching/listening | Mark timing as estimated. Verify the waveform and align both ends before measuring pauses, response latency, or exact boundaries. |
| Up to 18 consecutive eight-second identity windows per member; any three can pass | Evidence about sampled speaker intervals | Report identity-anchor coverage separately from whole-response continuity. Inspect the beginning, middle, end, and suspected changes; listen to the full response. |
| One review turn chosen nearest the introduction | One opening exchange | Sample throughout each interview and across question types. Retain short complete answers as well as long ones. |
| Gini of one member's answer word counts | Inequality in answer lengths | Call it answer-length inequality. It is not share of the floor, dominance, or control over the conversation. |
| Runs of short member turns, with host speech omitted | A transcript sequence proxy | Do not call this rapid contested exchange or interruption. Rebuild these measures from timed speech for every participant. |
| Agency/communion vocabulary mapped to framing fit | Language the member used | Do not infer what arguments persuade the member from their own vocabulary. |
| Model multiplier described as pressure returns | A model's stipulated output | Do not present it as an observed causal response to pressure. |
| Trait impressions stated as facts about character | Observer/model impressions under the instrument used | Keep instrument, construct, uncertainty, and behavioral observations separate. |
| Pre-current-role source called a baseline | Behavior in an earlier role and context | Preserve role and date for each recording. Earlier audio does not isolate an unchanging personality. |

Code evidence: `fec/speech/transcribe_member_longform_captions.py` (`json3_words`, `transcript_api_words`); `fec/speech/verify_member_longform_speaker_continuity.py` (`MAX_WINDOWS_PER_MEMBER`, candidate-window loop and consecutive-run acceptance); `fec/speech/build_member_longform_review_queue.py` (cue-gap ranking); `fec/members/interaction_features.py` (member-only ingestion, `gini`, short-turn runs); `fec/members/build_member_narrative_ledger.py` (interaction labels, motivating appeals, pressure-note conversion); `fec/members/build_member_meeting_playbooks.py` (opening, room pacing, and close rules).

The older `fec/members/behavioral_dispositions.py` explicitly records a split-half reliability of .04 and rejection for the burst proxy. Current narrative uses of that proxy need reconciliation with that result.

The portrait prompt also conflicts with the guarded writing instructions: `fec/members/member_narratives_v2_portrait_prompt.md` suppresses uncertainty and missingness, asks for character claims, and converts public wording into claims about what kind of argument works. A future canonical descriptive prompt should allow a plain “not established” and keep estimates attributed to their instrument. This review has not silently replaced the existing writer or regenerated production profiles.

## Revised unit of analysis

Maintain two linked units:

1. **Speaker interval:** uninterrupted speech by one identified person, used for acoustic measurements. Exclude other voices and label overlap or uncertain attribution.
2. **Response episode:** the full eliciting question, the member's response, brief listener acknowledgments, and the next substantive handoff/follow-up. Preserve the member's full response even when it lasts many minutes. A computational chunk ending is not a behavioral boundary.

An “uh-huh” may let the member continue; it need not end the response or indicate agreement. Record the local function rather than classifying from a keyword alone. This distinction follows the conversation-analysis treatment of continuers in [Schegloff (1982)](https://www.conversationanalysis.org/wp-content/uploads/2019/06/06_Schegloff_Discourse_as_Interactional_Achievement_-_uhhuh.pdf).

Do not solve the previous short-window problem by selecting only long answers. A one-word complete answer is part of the communication distribution. If it cannot pass a long acoustic-anchor test, obtain identity evidence elsewhere in the recording and separately review attribution to that short interval.

## What to code

For each episode, retain production identity, producer/interviewer, recording and publication dates, setting, role at recording, original language, editing limitations, and actual member participation duration. Episode runtime includes ads and hosts and is not member speaking time.

For each response episode, retain the full prompt; initiation actor; prompt type (single, multipart, biographical, factual, challenge); member response; next substantive follow-up; verified timestamps; and any editorial cuts, overlap, interruptions, or uncertainty. Question design is part of the explanation for a response, as illustrated by [Clayman and Heritage (2002)](https://clayman.scholar.ss.ucla.edu/wp-content/uploads/sites/15/2019/07/Clayman-and-Heritage-2002-Questioning-Presidents.pdf).

Start with a small observable codebook:

- Member initiates a social question versus responds to a host's personal question.
- Requests clarification before answering.
- Gives the requested factual answer, qualifies it, or explicitly declines it.
- Introduces an example before or after a general statement.
- States a principle before or after an implementation detail.
- Responds to a substantive follow-up with clarification, repetition, correction, or a new point.
- Continues after a backchannel; interrupts; is interrupted; yields the floor. Code these separately.

Keyword matches propose passages for inspection. Words such as “first,” “but,” and “example” do not by themselves establish a principle-first structure, defensiveness, or a conversational preference.

Report response-length distributions within comparable settings and prompt types: count, median, spread, and upper tail, with distinct episode counts. A maximum illustrates an observed possibility and must not be described as a typical answer. Estimate uncertainty at the episode level; many answers from the same recording are clustered observations.

## Acoustic and transcript quality

Preserve original-language text. The current English-only caption selection and forced-English local ASR need a language-aware route before non-English recordings are interpreted. Code-switching should remain explicit; translated text cannot provide original speech-rate or word-choice measurements.

Audio-derived ASR and alignment should validate passages used for semantic interpretation and both response boundaries. Alignment locates proposed words; it does not establish correct transcription or speaker identity. [Bain et al. (2023), WhisperX](https://www.isca-archive.org/interspeech_2023/bain23_interspeech.html), treats transcription and timing as distinct technical problems.

Keep clipping, noise, music, compression, channel, and microphone changes in the measurement record. Absolute recorded loudness is not an interpersonal trait. Within-recording comparisons still need production-context checks. Microphone response and placement can materially affect voice measurements: [Svec, Sramkova and Granqvist (2009)](https://www.isca-archive.org/maveba_2009/svec09_maveba.html).

## Claim and evidence records

A descriptive claim must specify the behavior, initiating actor, elicitation, setting, eligible opportunities, supporting and contradicting observations, reviewed recording identities, and unresolved limitations. It may be:

- **No reviewed observation:** no admissible observation supports assessment.
- **Provisional:** an observation exists, but recurrence or context requirements are unmet.
- **Recurring in the reviewed public interviews:** the ratified cross-recording/context rule is met for the same behavior.
- **Mixed or context dependent:** reviewed opportunities show relevant disagreement or contradictory behavior.

These labels concern the reviewed public-interview sample. They do not establish private preferences or a causal effect on political decisions. Repeated observations matter because substantial within-person variability can coexist with stable averages; see [Fleeson (2001)](https://pubmed.ncbi.nlm.nih.gov/11414368/). This paper does not establish a two-interview sufficiency threshold for legislators.

Field reports remain separately attributed. A secondhand report can suggest what to look for, but cannot count as a reviewed recording or be upgraded into a human listening attestation.

## Scalise: the precise distinction

The existing 2020 Takeout entry describes the host asking a personal question and Scalise responding for about 71 seconds. That supports **host-elicited personal response** in that recorded context.

The user's secondhand example describes **member-initiated social questioning** before substantive discussion. It concerns a different initiating actor and a different behavior. Neither observation corroborates the other for the two-interview rule, and neither establishes that football is a preferred topic or that social talk changes an outcome.

Suggested evidence wording:

> A secondhand meeting report describes Scalise initiating conversation about football before the substantive discussion. Its frequency and date are unknown. Separately, a recorded interview contains an extended response to a host's personal question. The recorded example does not establish who typically initiates social conversation in meetings.

This wording preserves the useful lead while making the unanswered question concrete.

## Validation pilot proposed for consultation

Use 12 members with two contrasting independent interviews each, including short and long responses, different interviewer styles, leaders before and after their current role, and at least one non-English source. This is a workflow pilot, not a powered validation of personality or private-meeting prediction.

Two reviewers independently code the pilot before seeing the existing portrait or each other's labels. Review source identity, response boundaries, and semantic codes separately. Report per-code agreement, uncertainty, adjudicated disagreements, and examples of failure. Consensus after discussion is not an independent reliability estimate. [Hayes and Krippendorff (2007)](https://www.asc.upenn.edu/sites/default/files/2021-03/Answering%20the%20Call%20for%20a%20Standard%20Reliability%20Measure%20for%20Coding%20Data.pdf) supports using an appropriate agreement measure on representative independent coding.

Search deliberately for counterexamples to each proposed pattern. A missing social opening in an edited podcast is not a negative observation when the opening was never observable. Record “not assessable” separately from “absent despite opportunity.”

Before scale-up, repair review exports so the human's acceptance is bound to the exact audio, transcript, queue item, and corrected boundaries they reviewed. Supplemental identity references must be deduplicated by recording and exclude the candidate recording. Recalibrate the actual long-form acceptance rule on held-out recordings before using a zero-observed-false-accept label.

## Implemented during this review

- Local classifier reuse now checks source and transcript hashes, cue evidence, and effective classifier settings. Replaced sources cannot inherit a previous successful classification merely because the member name is unchanged.
- New caption word records and ledger rows explicitly label interpolated timing as estimated and unaligned. This adds honest provenance; it does not retroactively align existing transcripts or fix downstream timing consumers.
- The Scalise report is stored with explicit secondhand provenance and zero interview authority.
- A separate consultation helper implements the two-interview descriptive evidence rule. It is not connected to profile publication and does not manufacture missing human-review provenance.

Helper: `fec/speech/assess_member_behavior_evidence.py`. Its input consists of explicitly coded observations, the target behavior/initiator/elicitation, and current source-audio/transcript hashes. It returns a deterministic assessment with supporting, contrary, duplicate, and excluded records. Human-review and independence metadata must be supplied from actual review; historical admission labels do not fill those fields automatically.

Validation completed: 50 focused tests passed across the descriptive evidence assessor, caption timing provenance, and local-classifier reuse. Tests include secondhand reports, duplicate recordings, missing context, stale review hashes, elicitation mismatch, contrary observations with incomplete context, and deterministic ordering. Passing software tests does not validate the behavioral codebook; the independent reviewer pilot remains outstanding.

Remaining: integrate the approved evidence standard into the production source/response selection and display; repair the methodological defects above; conduct the reviewer pilot; reacquire corrected sources; then regenerate descriptive observations with their actual evidence status. The existing 533 profiles have not been revalidated by these changes.
