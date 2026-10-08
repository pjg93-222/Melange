# All-member long-form verification recheck

September 4, 2026, approximately 18:25 Eastern. **Regeneration is held. Verified long-form coverage for all 533 members has not been delivered.**

The Klobuchar and Booker conversation samples used existing public-personality, language, behavioral, and accepted short-clip findings. Neither member has newly qualified long-form evidence or whole-turn measurements in the candidate ledger. The samples must not be described as completed long-form integrations or as proof of what changes either member's mind.

## Fresh roster check

The immutable run at `C:/melange-data/longform_candidate_runs/regeneration-preflight-20260904T1812/` inspected all 533 roster entries. Source files that reached physical validation were hash-checked and their transcripts frozen. This is a candidate-selection diagnostic, not complete audio listening, speaker certification, or semantic review.

The original frozen snapshot reported 88 candidate-ready sources and 445 exclusions:

- 395 transcript diagnostic holds, predominantly estimated caption timing overlaps;
- 21 stale transcript/source bindings;
- 14 missing in-band name cues;
- eight pending transcripts;
- six existing recording-quality holds;
- one pending selected acquisition in the leadership/pre-current-role route.

The primary acquisition receipt still covers 533 recordings. A selected leadership source can remain pending despite the existence of a different primary recording. A source gap does not count as a verified member.

## Physical-timing defect fixed

The early quality diagnostic allowed end timestamps to exceed audio duration by the larger of two seconds or 0.5% of runtime. That was weaker than the complete-turn classifier's existing 0.1-second tolerance. It hid the known 1.734-second overrun in Margaret Hassan's transcript and made the early candidate-ready count too permissive.

The diagnostic now uses the same 0.1-second tolerance as the classifier. Three regression cases cover permitted rounding, a small invalid overrun, and the 1.734-second case. No transcript was clipped, reordered, or repaired by changing its timestamps; no audio was recut to force a pass.

A read-only comparison of the frozen diagnostic end times to WAV durations found 236 overruns greater than 0.1 seconds, mostly among already excluded caption sources. Hassan was the only additional previously ready source affected. Thus **87 of the original snapshot's sources remain technical candidates after this correction**, not verified members. The original snapshot and its historical code hash are preserved; its receipt was not rewritten. These are a frozen-cohort calculation, not a replacement live receipt.

Klobuchar's selected pre-role source has overlapping estimated caption times and ends approximately 1.955 seconds beyond its WAV. Booker's selected pre-role recording passes this preliminary transcript diagnostic but still lacks qualified complete-response evidence.

## Actual qualification status and sample-claim risks

- The current measured long-form artifact still contains nine legacy candidate WAVs, eight sources, four members, and **zero newly qualified turns**.
- The designated named-human review file and the fully reviewed whole-turn output file are absent. No attestation or completed member was fabricated.
- The completed Scalise pilot evaluated all 153 planned speaker windows. Only one of 32 candidate responses passed whole-interior continuity; it still awaits the existing listening/boundary/content review. A failed check is not proof of another speaker, and thresholds were not relaxed.
- The ledger's repeated-floor-defense node uses total archive program count and an aggregate score. It does not itself demonstrate that the same behavior occurred in two independently produced interviews in different settings. Recurring claims need observation-level corroboration.
- The motivating-appeals node is derived from agency/communion framing scores. It does not provide an observed argument-response sequence demonstrating persuasion. Treat proposed approaches as hypotheses, not verified persuasion outcomes.

## Checks and ongoing work

- Main selected verification/measurement/ledger suite: **206 tests passed** in 16.49 seconds.
- Snapshot and classifier suite after the timing fix: **64 tests passed** in 4.71 seconds, including the three new timing cases. These suites overlap and must not be summed.
- The existing exclusive transcription-repair worker remains running. The latest observed progress is 19 of 47 source-bound transcripts after its restart, plus five completed earlier. This is transcription progress, not verified-member progress. No second live-manifest writer was launched.
- No profile prose, active narrative ledger, personality scores, speaker thresholds, or source-selection manifest was changed by this recheck.

The user requires verified long-form evidence across **all 533 members**, complete responses of unrestricted length, pre-current-role leadership sources, and two independent interviews in different settings for recurring claims. Requested profiles remain exactly three paragraphs—personality; speech and landmines; approach—at 280–300 words. Drafting cannot substitute for the missing verification.

The existing publication code requires named human listening review. The user has been asked whether to retain that requirement or authorize explicitly labeled automated verification for clear passes while retaining listening review for ambiguous cases. Neither option waives audio alignment, speaker verification, full-response boundaries, source independence, or faithful interpretation. No new authority has been assumed.
