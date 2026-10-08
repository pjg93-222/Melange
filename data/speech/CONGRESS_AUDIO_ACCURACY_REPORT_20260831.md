# Congress Audio Profile Accuracy Report

Generated: 2026-08-31 (America/New_York)  
Scope: the current 537-person congressional audio-profile universe and the artifacts used to admit members to the general, strict-identity, and non-floor descriptive tiers.

## Bottom line

The current coverage count is mechanically reproducible: **500 of 537 members (93.1%) meet the general audio-profile admission rule**. The result is hash-bound, row-complete, and backed by a passing census receipt.

The reportable numerical accuracy figure is **99.9995% calibrated wrong-speaker rejection accuracy (one-sided 95% lower confidence bound)**. The observed result was 100%: zero false accepts in 650,160 wrong-claim sequences. Using the standard zero-failure bound, the upper 95% false-accept rate is approximately `3 / 650,160 = 0.000461%`, giving a lower rejection-accuracy bound of approximately **99.999539%**, rounded to **99.9995%**.

This number is the identity gate's calibrated specificity in its held-out test domain. It is not an estimate of end-to-end label accuracy across all 500 admitted profiles, because the corpus contains multiple evidence paths and has not yet received a blinded human-gold audit. Executive reporting should therefore state both numbers together: **99.9995% calibrated identity-gate specificity; 93.1% member coverage**.

That number must not be described as “99% speaker-identification accuracy.” The repository does not yet contain a blinded human-gold audit large enough to estimate a corpus-wide speaker-label error rate. What can be stated accurately is:

- coverage accounting and current-file integrity are strong and directly testable;
- the positive voice-comparison calibration observed zero false accepts in its held-out test domain, but it is not an end-to-end audit of all 500 profiles;
- the newest 31 exact windows passed their deterministic identity, speech, duration, PCM, and lineage gates, and were rechecked byte-for-byte;
- uncertainty is handled by refusal rather than promotion: 41 of 72 proposed windows in the newest consolidated batch were rejected;
- only **244 of 537 members (45.4%)** currently have the required non-House-floor descriptive profile, so population-level descriptive comparisons must use that smaller, non-random subset or wait for further recovery.

## What “verified” means here

The ledgers intentionally define three different thresholds:

| Tier | Current count | Admission rule | Appropriate use |
|---|---:|---|---|
| General audio profile | **500 / 537** | At least five verified 8-second-equivalent windows from either the anchor ledger or active canonical ledger. The two sources are combined with `max`, not summed. | A member has enough accepted voice material to be represented in the general profile census. |
| Strict identity prerequisite | **416 / 537** | At least three independently verified events and at least 180 unique seconds. | Positive voice-comparison workflows requiring a stronger multi-event identity reference. |
| Non-floor descriptive profile | **244 / 537** | At least five verified non-House-floor exact windows. | Descriptive work where setting diversity matters and House-floor-only material is insufficient. |

The general count is an admission count. Some qualifying anchor or parent recordings are represented as exact 8-second equivalents rather than as separately materialized WAV files for every logical window. Therefore, “500 profiles” does not mean that every contributing logical window exists as its own standalone file.

## Current evidence

### 1. Census and accounting integrity

`congress_audio_profile_census_full_v1.receipt.json` reports `PASS`, 537 rows, 500 verified general profiles, 416 strict-ready profiles, and 244 non-floor profiles. Its census manifest SHA-256 is:

`6fab34a2fcad3941217368880b7c3e80da5cc362c97a1c9c3a7d7a9799b6ccb1`

The profile-basis breakdown is:

| Basis meeting the five-window floor | Members |
|---|---:|
| Both anchor and canonical ledgers | 330 |
| Anchor ledger only | 100 |
| Canonical ledger only | 70 |
| Not yet verified | 37 |

This accounting deliberately excludes superseded canonical rows, refuses raw YouTube title matches as identity evidence, and does not add the anchor and canonical window counts together.

### 2. Latest exact-window recovery batch

The latest verifier evaluated **72 exact 8-second rows** from ten source candidates:

| Outcome | Rows |
|---|---:|
| Accepted exact windows | **31** |
| Refused exact windows | **41** |
| Members completing a general profile | **9** |

The nine recovered members are Christian Menefee, Gabe Evans, Gregory Murphy, James Gallagher, James Justice, Julie Johnson, Laura Friedman, Randy Feenstra, and Timothy Kennedy.

Every accepted row required literal in-band identity evidence, including an approved first-name alias only when the surname was also present. Title, channel, upload date, state, office, and program metadata were not allowed to establish speaker identity. The verifier also enforced an exact 8-second/128,000-frame cut, at least 80% voiced audio, no more than 1.2 seconds of internal silence, question-boundary protection, and acoustic rejection checks.

The 41 refused rows remained refused. Refusal flags include low voiced ratio, target-seed inconsistency, half-window inconsistency, and a question boundary; a row can carry more than one flag.

### 3. Direct physical recheck of the 31 accepted files

A fresh read-only audit on 2026-08-31 re-opened every accepted WAV and compared it with both its verification row and the canonical manifest. Results:

| Check | Result |
|---|---:|
| Accepted WAV exists | **31 / 31** |
| Full-file SHA-256 matches verifier | **31 / 31** |
| Decoded PCM SHA-256 matches verifier | **31 / 31** |
| Mono, 16 kHz, PCM16, exactly 128,000 frames | **31 / 31** |
| Matching canonical path and hash | **31 / 31** |

This validates the newest batch’s file identity and cut geometry. It does not substitute for a human judgment of who is speaking.

### 4. Voice-comparison calibration

The current anchor vault contains **1,512 recordings for 431 speakers and 119.255 hours of audio**. The held-out three-window calibration compared each claim against all vaulted speakers and reports:

| Calibration measure | Result |
|---|---:|
| Held-out events | 1,512 |
| Evaluated held-out events | 1,473 |
| Wrong-claim sequences | **650,160** |
| Observed false accepts | **0** |
| Genuine sequences accepted | **23 / 1,473 (1.56%)** |

The very low genuine acceptance rate shows the intended precision/recall tradeoff: the positive voice gate abstains aggressively. Zero observed errors in these 650,160 structured wrong-claim trials is strong evidence for that comparator under the tested conditions, but it is neither proof of perfect accuracy nor a confidence interval for every legacy, transcript-led, or in-band-name-led profile in the 500-member census.

The newest cold-start recovery lane uses ECAPA only as rejection evidence; positive identity comes from literal in-band naming plus turn-boundary and continuity rules. Therefore the ECAPA calibration cannot be transferred wholesale to those rows.

### 5. Regression coverage

A fresh run of the speech test directory completed **115 tests with 115 passing**. These tests cover profile-gap construction, transcript-start handling, alias rules, candidate classification, exact-window verification, canonical materialization, descriptive contracts, source-media recovery, and voice-first recovery.

This is implementation evidence. It shows that the encoded contracts behave as expected on their test cases; it does not measure real-world speaker-label accuracy.

## The transcript-boundary failure and its correction

The earlier importer treated the acquisition pad as if it were the beginning of the target’s speech. When multiple words or turns occupied that padded region, the row failed as `transcript_start_not_unique` even when the title and the dialogue clearly named the speaker.

The corrected flow separates the two concepts:

1. the padded interval is used only to preserve context and locate the turn;
2. the exact cut is snapped to the actual target-response opening inside that interval;
3. literal in-band name evidence may be recovered deterministically from timestamped ASR before the target span;
4. an approved first-name alias is allowed only with the surname;
5. title/channel metadata remains non-authoritative;
6. if the identity or speech-boundary evidence remains ambiguous, the row is refused.

Tests now exercise the repaired boundary and evidence behavior. This directly addresses the failure that incorrectly discarded clearly introduced speakers.

## Accuracy judgment by claim

| Claim | Assessment | Why |
|---|---|---|
| “There are 500 admitted general profiles.” | **Verified** | Complete 537-row census, deterministic rule, passing receipt, hash-bound inputs. |
| “The newest 31 WAVs are intact exact cuts.” | **Verified** | All files, file hashes, PCM hashes, format geometry, and canonical bindings rechecked. |
| “The strict positive voice comparator is precision-oriented.” | **Strongly supported in-domain** | Zero false accepts in 650,160 held-out wrong-claim sequences; only 1.56% genuine-sequence acceptance. |
| “Every label among all 500 profiles is correct.” | **Not yet empirically measured** | No blinded corpus-wide human-gold sample spanning all evidence paths and sources. |
| “The 500 profiles support representative cross-member descriptive analysis.” | **Not supported** | Only 244 have the non-floor descriptive floor, and recovery is not random. |
| “The remaining 37 are absent because no data exists.” | **False** | Twenty-eight have 413 local transcript packages; seven also have 13 already-downloaded YouTube recordings. The bottleneck is exact identity-bound audio, not raw corpus volume. |

## Recommended accuracy calibration

To turn the current qualitative identity judgment into a defensible numeric error estimate:

1. draw a blinded, stratified random sample of at least **300 accepted exact windows** across source family, setting, admission basis, and recovery vintage;
2. include every nickname/alias case and every row accepted through repaired pre-span name recovery as an additional certainty sample;
3. have two independent reviewers label target identity, overlap, speech purity, and exact boundary, with a third reviewer resolving disagreement;
4. report raw agreement, adjudicated error rate, and a binomial confidence interval by evidence path;
5. if 300 independent audited windows yield zero errors, the rule-of-three gives an approximate 95% upper bound below 1% for the sampled population; any observed errors require source- and rule-specific remediation before extrapolation.

Until that audit exists, the honest description is: **high mechanical integrity, conservative fail-closed acceptance, strong in-domain comparator evidence, and unmeasured corpus-wide speaker-label accuracy**.

## Authoritative current artifacts

- `congress_audio_profile_census_full_v1.jsonl` and receipt: current coverage census.
- `congress_audio_profile_recovery_gap_general_v1.jsonl` and receipt: current 37-member residual.
- `speaker_anchor_vault_all_verified_v3.jsonl` and receipt: accepted anchor inventory.
- `speaker_anchor_calibration_all_verified_v3.json`: current held-out positive-voice calibration.
- `canonical_exact_windows_v1.jsonl`: logical exact-window lineage ledger.
- `local_youtube_holdings_asr_v1.jsonl`: timestamped localization-only ASR.
- `local_youtube_turn_candidates_v1.jsonl`: hard-signal screening ledger.
- `local_youtube_exact_window_verification_v1.jsonl` and receipt: newest exact acceptance/refusal ledger.
