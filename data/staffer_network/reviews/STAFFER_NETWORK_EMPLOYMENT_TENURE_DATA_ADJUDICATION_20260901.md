# Staffer Network Employment-Tenure Data Adjudication — 2026-09-01

Adjudicator: Fable (Claude Fable 5.1), read-only session, glassbox run
`run-20260901T1952278368647Z-0a9157cd`.
Companion to `STAFFER_NETWORK_MATH_ADJUDICATION_20260831.md` (which adjudicated the
mathematics) and to the v3 design/metrics revisions dated 2026-08-31. This document
adjudicates the DATA on the one dimension those documents name as binding: employment
chronology, meaning dated, bounded, precision-tagged employment intervals bound to an
accepted person and an accepted container.

Scope of the session: every figure below was re-measured from the on-disk artifacts by
streaming the receipts and ledgers; nothing was run, promoted, demoted, edited, or deleted
in the live tree. The live tree was quiescent during measurement (no Python process, no
lane file modified in the preceding four hours; the four `codex.exe` processes present are
MCP server hosts, not lane execution).

## 0. Verdict

Employment tenure is adjudicated as **NOT ESTABLISHED for any of the 25,340 sealed LDA
identities under the lane's own governing contract**, and the current review-candidate
identity plane cannot carry a canonical tenure interval until the identity, container,
parser, and Senate-temporal gates are satisfied rather than removed. Concretely:

- Zero canonical employment episodes exist in a generation that satisfies the governing
  contract. The v3 overlay (the state of record) holds 4,996 bounded provisional
  episodes for 1,186 of 25,340 people, every one carrying at least one promotion blocker.
- The v5 promotion prototype's 18,815 "canonical" episodes for 2,672 people are ruled
  **NOT CANONICAL** (section 6). Fable's adversarial verdict on that payload is
  **BLOCKED for canonical promotion; PASS for determinism and conservation only**.
- Complete-lifetime employment attestations: 0 of 25,340, and structurally unreachable
  for any non-LegiStorm episode as the code stands (section 7).
- The pre-2009 House backfile stays `BLOCKED_PARTIAL_RECOVERY`, 1 of 52 quarters
  (section 3.12), closed to CAPTCHA retries and open only to a newly admissible source.
- The Meta LOOP disposition `BLOCKED` (event `evt-20260901T0141474876529Z-24f3966659`,
  stage A4) **stands**. Its exit conditions are enumerated in section 10; four of the
  seven are Paul's rulings, not engineering work.
- One material accounting finding: a House payroll match lane covering 2016Q1–2026Q1
  (11,788 candidate rows, 3,355 people) exists on disk and was not conserved by the v3
  adjudication overlay, which conserved only the 32,103 rows of the 2009Q3–2015Q4 lane
  (section 3.4). All 3,355 of those people sit in P3, so the priority partition is not
  overstated by the omission; the adjudication overlay and the v5 prototype are simply
  blind to 11,788 rows of bounded House tenure candidates (section 4).

Nothing in this document is evidence of influence, access, friendship, or ideology
(design §6.8 language law; DE-006).

## 1. The contract this document adjudicates against

- An employment episode is `(person, container_kind, container_key, title, t0, t1,
  t_precision ∈ {day, month, year, none})`; undated episodes are kept, flagged, and
  excluded from every duration-weighted computation (design §5 lines 292–303).
- Tenure enters mathematics only through half-open uncertain intervals: `core(e) =
  [start_latest, end_earliest)`, `envelope(e) = [start_earliest, end_latest)`; possible-only
  overlap has primary weight zero (design §0A lines 33–46; math doc §6).
- A dated former-position candidate needs at least one of `raw_start_date`,
  `raw_end_date`, `raw_dates`, or a recognised `date_granularity`; a bounded candidate
  needs both a start and an end, or a payment-period granularity
  (`build_public_employment_acquisition_queue.py:67–88`).
- Identity: exact normalised-name equality is blocking evidence for review, never proof
  (`lda_identity_candidates.py:2–5`; candidate schema pins `confidence` to `null`).
  Cross-source acceptance requires the I-4 gold set: precision ≥ 0.98 and recall ≥ 0.90 on
  ≥ 200 hand-adjudicated pairs (metrics I-4).
- Canonical promotion requires a reviewer-attributed decision record whose identity and
  container decisions are live and hash-bound
  (`employment_history.py:1146–1155, 1317–1498`); the completeness audit fails closed
  unless every episode is dated, sourced, provenance-bound, and an attributed attestation
  declares the history exhaustive with an empty unresolved-gap list
  (`employment_history.py:350–605`).
- Language law: no influence or predictor phrasing on revolving-door or LDA-derived edges
  (metrics I-15; DE-006).

## 2. Identity plane — verdict: SOURCE-NATIVE ONLY

| Fact | Value | Receipt |
|---|---:|---|
| Sealed LDA source-native lobbyists, filing window 2021–2026 | 25,340 | `AppData\Local\Melange\staffer_network\normalized\lda-source-native\generation-20260830T231200Z` |
| Canonical identity merges / cross-source identity assertions | 0 / 0 | same receipt |
| LDA identity candidates method | `NORMALIZED_NAME_EQUALITY_REVIEW_CANDIDATES_ONLY`; `downstream_identity_gate: CLOSED` | `lda-identity-candidates\generation-20260830T231700Z` |
| Politico↔Quorum pilot: directory persons / legacy rows / candidates / strict candidates | 18,618 / 5,773 / 4,836 / 2,643 | `data\staffer_network\receipts\politico_resolution_pilot_20260829.json` |
| Politico pilot reviewed by two model reviewers / human gold labels / canonical merges | 200 (100 calibration at 100% agreement; 100 holdout `QUARANTINED`, `evaluation_count: 0`) / 0 / 0 | `politico_adjudication_results_20260830.json` |
| Politico→LDA employment candidates: rows / LDA people / Politico persons | 560 / 412 / 363, all `DIRECTORY_OBSERVATION_TIME_ONLY`, identity `REVIEW_REQUIRED` | `politico_lda_employment_candidates_20260831` receipt |
| v3 `source_native_identity_status` | `ACCEPTED` for 25,340 of 25,340 (the LDA ID is accepted as itself; no cross-source identity is accepted) | v3 person summary |
| v3 gate `IDENTITY_PRECISION_RECALL_GOLD_200_REQUIRED` | `OPEN` on all 25,340 rows; a 200-row sample file exists (`identity_rule_gold_sample_200.ndjson.gz`), no receipt records it as adjudicated | v3 receipt |

Ruling. Every cross-source link on disk is a review candidate. The two-model 100/100
agreement on the Politico pilot is uncalibrated against any ground truth (schema pins
`estimated_human_gold_precision` to `null`), and 2,443 of 2,643 strict candidates were
never reviewed at all. The I-4 gold set has no owner because D-Q5 is unanswered. No
tenure interval can be attached to a cross-source person until this gate is satisfied.

## 3. Source-by-source tenure capacity

Each source is ruled on what it can establish about tenure (dates, bounds, precision),
and on what the v3 overlay actually did with it. "Window" and denominator are stated with
every figure.

| # | Source | Window on disk | Rows / people | Tenure semantics | v3 disposition | Verdict |
|---|---|---|---:|---|---|---|
| 3.1 | LDA `covered_position` free text (A5a) | filings 2021–2026 | 41,680 claim rows over 25,340 people; 9,484 with a response, 9,152 substantive, 15,856 without (A5a materialization receipt); 2,166 with a four-digit year token and 597 with a month token (`employment_lookup_receipt.json`, generation-20260831T050000Z, fields `covered_position_people_with_year_token` / `_month_token`) | asserted role text; year-precision at best; a filing's `dt_posted` is never an employment date | parse lane: 1,878 `PROVISIONALLY_ACCEPTED`, 418 `REJECTED`, 39,384 `REVIEW_REQUIRED` (`COVERED_POSITION_PARSE_AMBIGUOUS_UNBOUNDED_OR_OUTSIDE_CUTOFF`); 1,243 provisional `ASSERTED_EPISODE`s, all blocked on `COVERED_POSITION_PARSER_GOLD_REQUIRED` | Discovery seed, not tenure. The parser gold-100 gate is `OPEN`. |
| 3.2 | LDA registrant association | filings 2021–2026 | 25,469 rows over 25,340 people | registrant-employment predicate observed per filing year (`FILING_ACTIVITY_OBSERVATION_NOT_EMPLOYMENT_CONTINUITY`) | 25,469 `ACCEPTED_SOURCE_NATIVE_ASSOCIATION` | Annual membership observation, not a bounded interval. Never client employment. |
| 3.3 | House SOD payroll, A1 lane | 2009Q3–2015Q4 | 293,881 payroll rows → 32,103 candidate rows, 29,647 matched payroll rows, 2,135 LDA people | quarter-period `OBSERVATION_ONLY`; name match to LDA | 3,588 `PROVISIONALLY_ACCEPTED`, 28,515 `REVIEW_REQUIRED` (`HOUSE_PAYROLL_NAME_MATCH_NOT_STRICTLY_CORROBORATED_OR_CLEAN`); 3,552 provisional episodes, identity `PROVISIONALLY_ACCEPTED_CORROBORATED`, blocked on identity-gold + container + external review | Bounded quarter observations exist; identity is name-matched. Tenure = union of payroll quarters, not an asserted start/end. |
| 3.4 | House SOD payroll, 2016–2026 lane | 2016Q1–2026Q1 | 681,177 payroll rows → 11,788 candidate rows, 52,499 name-matched payroll rows, 3,355 LDA people; promotions 0 | same as 3.3 | **Not conserved by v3** (`house_payroll_rows_conserved: 32103` = the A1 lane only) | Coverage exists but is outside the A4 integration, the v3 overlay, and v5: v3's `inputs.house_payroll` sha256 `1083fdeb…` is the A1 file, this lane's candidates file is `9d6634ec…`, and the A4 receipt names only `house_sod_2009q3_2015q4` and `senate_2011_2026`. Every row is `canonical_identity_decision: NOT_ADJUDICATED`, `canonical_employment_fact: false`, `name_match_method: EXACT_FIRST_LAST_MIDDLE_COMPATIBLE`. Section 4 gives the partition join. |
| 3.5 | Senate Secretary payroll (A2) | 2011-04-01–2026-03-31, 30 semiannual periods | 305,261 archive candidates (233,009 accepted / 72,252 rejected at parse) → 6,953 match rows, 2,798 LDA people; **all 6,953 rows carry `promotion_gate: BLOCKED_PENDING_IDENTITY_AND_EMPLOYMENT_REVIEW`** | semiannual-period `OBSERVATION_ONLY` | 125 `PROVISIONALLY_ACCEPTED`, 6,828 `REVIEW_REQUIRED` (`MULTIPLE_OR_REVIEW_MARKED_OBSERVATION_INTERVALS_REQUIRE_SPLIT`); 125 provisional episodes | Bounded half-year observations exist; the lane's own rows say review is pending. Splitting an observation into episodes is not an audit of it. |
| 3.6 | Public web profile lines (bulk acquisition cycle `profile-acquisition-20260901T092410Z`) | crawl to 2026-09-01 | 12,672 people bundled; 97,358 employment-line and 18,837 education-line candidates; 72 people with structured profile evidence | unstructured page lines | employment lines: 20,330 `REJECTED`, 77,028 `REVIEW_REQUIRED` (52,760 `UNSTRUCTURED_PAGE_LINE_REQUIRES_RELATION_PARSING`); education lines: 1,640 / 17,197; structured episodes: 76 `PROVISIONALLY_ACCEPTED`, 255 `REVIEW_REQUIRED` | Leads. 76 asserted episodes at multi-source provisional identity; the rest need relation parsing before any date is a date. |
| 3.7 | LegiList page binding | as crawled | 12,723 rows; 10,701 `ACCEPTED_SOURCE_BINDING` for 10,691 people, 2,022 `REVIEW_REQUIRED` | page-to-ID binding (`URL_NUMERIC_ID_EQUALS_LDA_SOURCE_PERSON_ID`); `PAGE_YEARS_MUST_NOT_BE_USED_AS_EMPLOYMENT_DATES` | as stated | Identity-binding evidence for 10,691 people. Zero tenure. |
| 3.8 | Authenticated / structured profiles | as captured | 912 people with structured source-profile employment, 890 role/employer-complete; 74 `authenticated_profile` episodes in v5 | asserted episodes with source dates | not a v3 evidence lane except via 3.6 | Depth exists for under 4% of the census (912 of 25,340). |
| 3.9 | LittleSis Position records | 2026-08-29 dump | 368,995 records; 9.6% dual-dated, 61.4% undated (design §2.5, §9.12) | mostly undated | not a v3 provisional evidence lane | Undated co-affiliation at best; weight 0 in every duration computation by contract. |
| 3.10 | LD-203 affiliations and FEC employer observations (A7) | machine-local only | 143,513 LD-203 rows for 22,754 people; 979 FEC rows for 37 people | undated affiliation / point-in-time employer | A9 consumed FEC (zero bucket moves) and deliberately not LD-203 | Neither is a tenure interval. |
| 3.11 | House SOD 1997Q1 Part 2 (A8) | one quarter | 4,939 personnel observations → 453 candidate rows, 388 people | bounded quarter; name match unadjudicated | routed 209 people into P3 | A dated, bounded former-House candidate for 388 people, identity unadjudicated. |
| 3.12 | Pre-2009 House backfile (A5c) | target 1996Q1–2008Q4, 52 quarters | 12 report candidates discovered, 40 undiscovered; 23 Google Books candidates tested, 1 valid PDF, 22 HTTP-200 CAPTCHA pages; 1 of 52 quarters recovered (3.11) | — | `BLOCKED_PARTIAL_RECOVERY` (prose-only status; no script emits or tests it) | **CLOSED as blocked.** Reopens only on a newly admissible source (official archive or a licensed provider under D-Q2). Never on CAPTCHA retries. |
| 3.13 | Prose episode extraction (A6) | — | 0 safely linked; 3,090 near-candidates blocked | — | fail-closed | Stands. Zero output is preferable to unsafe output. |
| 3.14 | LegiStorm | — | Common-Crawl index: 0 unique profiles (`ConnectTimeout: 1`, `NO_CAPTURES: 4`); fan-out queue 41 rows (32 `REVIEW_ONLY`, 8 `PARTIAL`); crosswalk 10 records (7 resolved, 3 unresolved); one saved profile (`gordon_holzberg_legistorm_profile.json`) | full dated histories where licensed | policy `DISCOVERY_QUEUE_ONLY_NO_AUTOMATED_LEGISTORM_COLLECTION` | The only source whose episodes the completeness audit can bind (section 7) has effectively no data on disk. D-Q2 is the gate. |

Aggregate ruling on tenure capacity. The only bounded tenure evidence on disk is
payroll-period observation (House quarters, Senate half-years) for name-matched people,
plus 1,319 asserted episodes from parsed prose and structured profiles. Payroll
observation gives a union of pay periods, which is a lower bound on presence and an upper
bound on absence, not an asserted start and end; the math doc's core/envelope algebra is
the correct carrier for it, and it must stay on the review-candidate side of the identity
gate until I-4 is met.

## 4. The partitions — two "P" vocabularies that must never be conflated

| Scheme | Definition | P0 | P1 | P2 | P3 | Receipt |
|---|---|---:|---:|---:|---:|---|
| Employment-lookup queue (2026-08-31) | LDA text only: P0 = government-term lexical hit in `covered_position`; P1 = other non-empty text; P2 = no text (`employment_history.py:847–851`) | 6,527 | 2,957 | 15,856 | — | `employment-lookup\generation-20260831T050000Z`, sha256 `5e240a91…`, twin byte-identical |
| Acquisition priority queue, A5b baseline | cross-source evidence completeness: P0 = no employment candidate; P1 = no dated former-position candidate; P2 = no bounded interval candidate; P3 = residue ready for identity and chronology adjudication (`build_employment_adjudication_priority_queue.py:123–152`) | 11,720 | 4,932 | 1,784 | 6,904 | `employment_adjudication_priority_queue_20260901_a` receipt |
| A9 sidecar after A7/A8 | same rule after A8 moved 209 people to P3 | 11,643 | 4,843 | 1,741 | 7,113 | `a9_a7_a8_priority_sidecar_20260901_primary` receipt, primary/twin sha256 `f7e3350f…` |

The math doc's addendum figures reconcile exactly to A9 bucket sums: 16,486 "lack a dated
former-position candidate" = P0 + P1; 18,227 "lack a bounded employment-interval
candidate" = P0 + P1 + P2; 13,697 "have any employment candidate" = 25,340 − P0. The
earlier coverage-ledger gap counts 16,652 and 18,436 are the same sums on the A5b
baseline. All four buckets are mutually exclusive and conserve 25,340 in both receipts.

P3 is a fall-through residue, not a hardness class: a person is in P3 if and only if they
have at least one employment candidate, a dated former-position candidate, and a bounded
interval candidate. The 7,113 are the people for whom only adjudication remains.

v3 adjudication state crossed with the A9 bucket (both files hold exactly the same
25,340 IDs):

| v3 `adjudication_state` | P0 | P1 | P2 | P3 | Total |
|---|---:|---:|---:|---:|---:|
| `PROVISIONAL_EPISODES_PENDING_REVIEW` | 0 | 4 | 363 | 819 | 1,186 |
| `CANDIDATES_REVIEW_REQUIRED` | 11,643 | 4,839 | 1,378 | 6,294 | 24,154 |

Partition finding (section 3.4). The 2016Q1–2026Q1 House payroll lane's 3,355 matched
people were not an input to the A4 integration or the v3 overlay; both name only the
2009Q3–2015Q4 lane. Joined to the A9 sidecar on `lda_source_person_id`, all 3,355 sit in
P3 (P0 = 0, P1 = 0, P2 = 0, none missing); the control join of the A1 lane's 2,135 people
gives the same pattern, and every one of the 11,643 P0 people carries
`employment_provider_count = 0` in the A5b baseline. The partition is therefore not
overstated by the omission. The omission is an adjudication-overlay gap: 11,788 bounded
House tenure candidates for 3,355 P3 people were never adjudicated and are absent from v5.
Whether the A5b coverage merge consumed this lane directly, or these people qualify for P3
through other lanes, was not determined in this session.

## 5. The v3 quarantine overlay — verdict: STATE OF RECORD, HONEST, NOT A COMPLETENESS MEASURE

| Fact | Value |
|---|---:|
| Receipt status / method | `GENERATION_VALID_REVIEW_OPEN` / `bulk-employment-adjudication-overlay-v3` |
| Candidate decisions | 235,454 over 25,340 people: `REVIEW_REQUIRED` 171,229 (12,270 people), `ACCEPTED_SOURCE_NATIVE_ASSOCIATION` 25,469, `REJECTED` 22,388 (12,949 people), `ACCEPTED_SOURCE_BINDING` 10,701, `PROVISIONALLY_ACCEPTED` 5,667 (1,186 people) |
| Provisional episodes | 4,996 for 1,186 people; all bounded on `valid_start_*`/`valid_end_*`; `OBSERVATION_ONLY` 3,677, `ASSERTED_EPISODE` 1,319; start precision day 3,696 / year 1,264 / month 36; span 1978-01-01 to 2026-09-02 |
| Promotion blockers on episodes | `CONTAINER_NORMALIZATION_REQUIRED` 4,996; `FABLE_OPUS_REVIEW_REQUIRED` 4,996; `IDENTITY_GOLD_CALIBRATION_REQUIRED` 3,753; `COVERED_POSITION_PARSER_GOLD_REQUIRED` 1,243 |
| Gates | all five `OPEN` on all 25,340 rows: parser gold-100, identity gold-200, container adjudication, Senate temporal observation audit, Fable/Opus adversarial pass |
| Promotions / attestations / merges / temporal-eligible episodes | 0 / 0 / 0 / 0 (schema constants) |
| Determinism | twin receipt sha256 `02ff23202da31be3ae49db04dc84735316dd4f8c42c632f98380effa11a4a263` identical to primary; all five payload hashes match; independent verifier `PASS`, 73 assertions true, 0 failures |
| Reviewer | `reviewer_kind` is the schema constant `RULE`; a human decision cannot be represented on this record type |

Ruling. v3 is the lawful state of record for employment-tenure candidates. Its zeros are
construction invariants, exactly as `EMPLOYMENT_PROMOTION_GATE_AUDIT_20260901.md` says:
the overlay cannot measure how many histories are complete, only that none has been
promoted. The external review it names was recorded `WAIVED_NOT_RUN` on 2026-09-01; that
record is preserved unchanged. Section 6 supplies the review, over the later payload.

## 6. The v5 promotion prototype — verdict: NOT CANONICAL

Facts, all re-measured:

| Fact | Value |
|---|---:|
| Receipt | `employment_promotion_generation_20260901_v5_primary`, status `PASS`, sha256 `644d9ded24aef5a4563c3eaa00910c84f9db85a4b31d162fefc244bfeaa665cc`; `quarantine_enabled: false`; `canonical_identity_policy: LDA_SOURCE_NATIVE_ID_ACCEPTED` |
| Gates removed / retained | removed `IDENTITY_PRECISION_RECALL_GOLD_200_REQUIRED`, `SENATE_TEMPORAL_OBSERVATION_AUDIT_REQUIRED`, `FABLE_OPUS_5_ADVERSARIAL_PASS_REQUIRED`; retained parser gold-100 and container adjudication |
| Episodes / people | 18,815 / 2,672; all `identity_status`, `container_status` = `ACCEPTED` (hard-coded literals, `employment_promotion.py:272–279`), all `episode_status` = `ACTIVE`; all bounded; precision day×day 17,462, year×year 1,244, other 109 |
| Source lanes | `senate_payroll_split` 13,840 (73.6% of 18,815); `v3_provisional:house_payroll_corroborated` 3,552; `v3_provisional:lda_covered_position_parse` 1,218; `v3_provisional:structured_public_profile_episode` 76; `authenticated_profile` 74; `v3_provisional:senate_payroll_corroborated` 55 |
| Containers | `member_office` 10,869; `other_org` 7,922; `registrant` 24 |
| Decisions | 18,965 rows, all `promotion_status: PROMOTED`, `identity_gate: REMOVED_SOURCE_NATIVE_ID_ACCEPTED`, `external_review_gate: REMOVED`; **not unique on `episode_id`**: 18,815 distinct episodes, 147 of them with 2–3 decision rows, 126 of those groups disagreeing on `source_lane`. The lane counts above are one row per episode and carry a ±147 uncertainty on the v3-provisional lanes accordingly; all 147 duplicated episodes belong to the 1,186 people who also had v3 provisional episodes. |
| Blocked | 2,712: `SOURCE_NATIVE_ID_NOT_UNIQUE` 2,642, `INVALID_INTERVAL` 70 |
| Promoted people × A9 bucket | P3 2,301; P2 363; P1 8 |
| Promoted people × v3 state | 1,186 had provisional episodes; **1,486 were `CANDIDATES_REVIEW_REQUIRED` with zero provisional episodes** |
| Governing prose | `EMPLOYMENT_PROMOTION_IMPLEMENTATION_DIAGNOSTIC_20260901.md:4–6`: "SCOPED PASS / GOVERNING GATE BLOCKED"; "V5 internal quarantine flag: OFF — prototype defect, not a governing waiver"; "Governing canonical employment quarantine: ON"; lines 121–125: the pointers "are verification selectors, not publication or consumer-arm pointers" |

Defects, each verified by measurement or by reading the enforcing code:

1. **Dangling decision references.** The 2,672 distinct `identity_decision_id` values
   (`employment:identity-decision:…`) and 1,371 `container_decision_id` values
   (`employment:container-decision:…`) on the episodes match 0 of the 18,965 decision
   IDs in the decisions file, all of which are `promotion:decision:…`. Every v5 episode
   therefore fails `_verified_canonical_episode_bindings` at
   `employment_history.py:1449` ("canonical episode identity decision is dangling").
2. **Unbound inputs.** The receipt has no `inputs` block, no input path, no input hash,
   and no receipt schema exists for it. The generation is not reproducible from its own
   receipt (metrics I-11).
3. **Schema laundering.** 4,901 episodes are copies of v3 provisional rows whose schema
   pins `canonical_eligible: false`, `episode_status: PROVISIONAL`, `container_status:
   LITERAL_REVIEW_REQUIRED`, and `promotion_blockers` with at least one entry. The target
   `employment_episode` schema has none of those fields, so the copy silently drops every
   quarantine invariant. No gate was passed; the fields that record the gate were removed
   by the schema change.
4. **Senate observations promoted against their own lane.** All 6,953 Senate match rows
   carry `promotion_gate: BLOCKED_PENDING_IDENTITY_AND_EMPLOYMENT_REVIEW`; v3 held 6,828 of
   them at `REVIEW_REQUIRED` and accepted 125 provisionally. v5 emitted 13,840 Senate
   episodes by splitting observation periods after removing the Senate temporal audit gate.
   Of the 1,486 promoted people with no v3 provisional episode (confirmed by two
   independent methods: person-summary state, and the set difference of the two episode
   files), 1,478 enter v5 only through `senate_payroll_split` (11,477 episodes) and 8 only
   through `authenticated_profile` (62 episodes); none mixes lanes. 1,480 of the 1,486
   appear in the Senate match-candidate file.
5. **Identity gate removed, not met.** 2,301 of the 2,672 promoted people sit in P3, whose
   defining next action is "adjudicate identity with independent anchors". Accepting the
   LDA source ID as the resolved person does not resolve the payroll-name-to-LDA-person
   link that every one of these episodes depends on.
6. **No consumer, and publication bars the schema.** Only the producer and its verifier
   reference the output; `publication.py:33–47` lists
   `staffer-network-employment-episode-v1` among `RESTRICTED_SCHEMA_IDS`.
7. **Conflicting decisions per episode.** 147 episodes carry two or three promotion
   decisions, and in 126 of those groups the rows disagree on `source_lane`. The v5
   verifier asserts `decision_ids_unique` and `decisions_reference_canonical_episode`,
   both true, and therefore never checks episode-level uniqueness; a fact with two
   provenance labels has no single provenance.

Ruling. v5 is a deterministic prototype and must be retained immutably as such, never
deleted, never armed, never cited as canonical. The word `PROMOTED` in its decision file
is a field value, not a governing status. Fable's adversarial verdict, supplied here in
place of the gate that v5 removed: **BLOCKED for canonical promotion**. The verifier's
`PASS` is correct for what it checks (byte twins, hash binding, edge-weight arithmetic,
one traced person) and is not a promotion verdict.

## 7. Completeness and attestation — verdict: 0 OF 25,340, STRUCTURALLY UNREACHABLE TODAY

- No `history_completeness_attestation` object exists in any generation. Every
  employment-completeness verdict on disk is therefore `INCOMPLETE` with
  `EXHAUSTIVENESS_ATTESTATION_MISSING`, or a hard-coded `NOT_ATTESTED` where the audit is
  the content inventory (`audit_profile_content_completeness.py:359, 463`).
- The only constructor of a canonical provenance registry reads a LegiStorm checkpoint
  receipt (`employment_history.py:1334–1336`); no other constructor exists in `fec\` or
  `audits\`. Omitting the registry fails every episode with
  `_CANONICAL_PROVENANCE_UNVERIFIED`. LegiStorm holds effectively no data (section 3.14).
- Consequence: no v3, v5, payroll, or profile episode can reach `COMPLETE` as the code
  stands, independent of whether the substantive gates are met. This is a design gap to
  be closed deliberately, not an audit to be relaxed.

## 8. Temporal sidecar over the v5 payload — verdict: EXPLORATORY AT MOST

`employment_temporal_sidecar_20260901_v4_primary` (twin byte-identical; selected by
`employment_temporal_current.json`, manifest sha256 `0c3a13b8…`): 18,815 episode rows;
co-tenure `GUARANTEED` 27,728 / `POSSIBLE_ONLY` 264 / `ZERO_OVERLAP` 31,606 over 59,598
candidate keys; 27,088 primary co-tenure edges; revolving `GUARANTEED` 12 /
`INTERVAL_BLOCKED` 0 / `POSSIBLE_ONLY` 0 / `WRONG_ORDER` 0; 12 primary revolving edges.

Ruling. The mathematics is the reviewed mathematics (math doc §§6–7, both Opus 5
micro-reviews `PASS`), and the sidecar honours its invariants. But its inputs are v5
episodes whose identities are accepted by gate removal (section 6), so under the math
doc's own rule that primary scores exclude identity review candidates, none of these
edges is a primary weight. They are exploratory diagnostics over a prototype and must be
labelled as such wherever they appear. The receipt binds only its outputs, not its inputs.

## 9. The review chain — what is and is not a verdict

- Three Opus 5 terminal reviews on run `run-20260831T1850525496629Z-8993807782` timed
  out (900 s, 600 s, 600 s) with no output. They are non-verdicts and remain so.
- The split constituent routes resolved: date/identity `BLOCKED` then post-fix `PASS`;
  completeness/attestation `BLOCKED` then resolved with the date/identity fix;
  consolidation attestation `PASS`; identity/accounting `PASS`; receipt/determinism
  `BLOCKED`, `BLOCKED`, then `PASS`. These are code-path and receipt-safety verdicts.
- Structural math, interval/co-tenure, revolving-door, and consolidation-receipt
  micro-reviews: `PASS`, each confined to its named scope (math doc §0, §9).
- Fable adversarial review of the v5 promotion payload: **BLOCKED** (section 6). This is
  the first merits verdict on the data side of the employment dimension.
- Test counts quoted by the lane (222 tests plus 73 subtests; 48 focused) were not
  re-run in this session and are cited as the lane's receipt, not this document's.

## 10. Meta LOOP disposition — `BLOCKED` stands; exit conditions

The blocking event reads: "Identity and episode adjudication blocked by incomplete
evidence. All 25,340 histories lack complete-lifetime attestation; identity/employer/
container/chronology gaps remain, 16,486 lack dated former-position candidates, 18,227
lack bounded intervals, and promotions remain zero." Every clause is confirmed above.

The disposition lifts only when all of the following hold. Owners are stated honestly.

| # | Exit condition | Owner | Status |
|---|---|---|---|
| E1 | I-4 identity gold set: ≥ 200 hand-adjudicated cross-source pairs, precision ≥ 0.98, recall ≥ 0.90, with CIs; a `HUMAN` reviewer decision record | Paul (D-Q5 owner ruling; labels are his domain or a delegate he names) | not started; sample drawn |
| E2 | Container adjudication for every promoted episode's employer/office | rule build plus human residue; owner unnamed | gate `OPEN` |
| E3 | `covered_position` parser precision ≥ 0.95 on the 100-string sample (I-8) | adjudicated sample; owner unnamed | gate `OPEN`; sample drawn |
| E4 | Senate temporal observation audit: I-7-class cross-source agreement for period-split episodes | engineering, then review | gate removed in v5, never met |
| E5 | An attestation producer with a named reviewer, and a provenance-registry constructor that accepts non-LegiStorm canonical generations, or a LegiStorm corpus | engineering; D-Q2 for the corpus | absent |
| E6 | Fold the 2016Q1–2026Q1 House lane into a new immutable v4-class adjudication overlay (its people are already in P3; the overlay, not the partition, is blind to them) | engineering, reversible, no promotion | not done |
| E7 | An adversarial merits review of any promotion generation before its pointer is treated as anything but a verification selector | Fable (this document covers v5) | done for v5: BLOCKED |

E1, E2 (residue), E3, and E5 (corpus route) are rulings or labels, not code. The lane
cannot finish the P3 adjudication by itself; it can only make the queue smaller and more
honest.

## 11. Decision menu for Paul

Nothing below proceeds without a ruling. Recommendations are marked.

| # | Decision | Recommendation |
|---|---|---|
| T-1 | v5 disposition: keep as immutable prototype under its current prose status; or repoint `employment_promotion_current.json` to nothing / to v3; never delete | Keep, immutable, labelled prototype; leave the pointer as a verification selector and add the word "prototype" to the pointer's `status_meaning` in the next generation, not by editing this one |
| T-2 | D-Q5 owner for the I-4 gold set (E1) and the P3 identity queue | Paul labels or names a delegate; Haiku 4.5 may pre-sort candidates, never label gold (law 2, law 1 spirit) |
| T-3 | D-Q2 LegiStorm licence | The only route to pre-2009 House tenure, Senate ease, and a completeness-bindable corpus; decide before any further backfile effort |
| T-4 | D-Q1 Politico attended crawl continuation | The depth channel; 912 structured profiles today against 18,618 listed |
| T-5 | Authorise E6 (fold House 2016–2026 into a new immutable adjudication overlay) | Yes; deterministic, twin-verified, zero promotion, reversible by pointer |
| T-6 | Authorise a Fable-owned sponsor of E5 (attestation producer plus registry constructor), gated to `HUMAN` reviewer kind | Yes, as a `.candidate`-class build consumed by nothing until ruled |
| T-7 | Whether the math doc's 09-01 addendum is amended to cite this document and to correct "canonical employment promotions are zero" to "zero under the governing contract; a non-canonical v5 prototype exists" | Amend in the living doc; the frozen record stays as written |

## 12. What this session did and did not do

Did: booted the project brain; located the lane (untracked in the live tree, absent from
every branch); re-measured every count above by streaming the receipts and ledgers;
verified the primary/twin hashes the lane cites; emitted glassbox events for every
fan-out; wrote this document.

Did not: run any producer, verifier, test, or acquisition script; modify, promote,
demote, repoint, or delete any artifact; edit any existing review or diagnostic (frozen
vintage law); label any identity pair or episode; commit anything. The lane remains
entirely untracked in git, which is a single-disk exposure the mirror does not cover.

## 13. Receipts

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `fec\staffer_network\network_math.py` | 13,668 | `011ae4dcb7e4611f5215fa0ac1a9fb24950a24984f65844ae3419f316a3daf5c` |
| `data\staffer_network\reviews\OPUS5_REVOLVING_DOOR_MICROREVIEW_20260901.md` | 4,978 | `58db6b2e3ca1b4d7cc03131407d358521655ba5538c6d3e236e5a4425625c01f` |
| `data\staffer_network\reviews\OPUS5_CONSOLIDATION_RECEIPT_FINAL_REVIEW_20260901.md` | 4,216 | `eb9f118cb4f5e9ff3db65fbce753b85e58fb9415f1b874857d75d8429b7559ba` |
| `employment-lookup\generation-20260831T050000Z\employment_lookup_queue.ndjson.gz` | 2,625,687 | `5e240a91a21e237525547eef84456daee7dd5339723073ced9437a9f5ea5f649` |
| v3 `employment_adjudication_receipt.json` (primary = twin) | — | `02ff23202da31be3ae49db04dc84735316dd4f8c42c632f98380effa11a4a263` |
| v3 `candidate_adjudication_decisions.ndjson.gz` | 41,762,272 | `157451540b421a06ac5340b58b68311f82a99d7be05de0c2c64f1badd79fade2` |
| v3 `provisional_employment_episodes.ndjson.gz` | 1,502,300 | `b192a41f753685d93285e69c6d29843c14333a5ea1838601117bf48542b8e2d5` |
| v3 `employment_adjudication_person_summary_25340.ndjson.gz` | 1,810,637 | `d575da8257bfb0adc78cdf8dc74843bac80af6959358713bf0716bf0fad157ef` |
| v5 `employment_promotion_receipt.json` (primary = twin) | — | `644d9ded24aef5a4563c3eaa00910c84f9db85a4b31d162fefc244bfeaa665cc` |
| v5 `canonical_employment_episodes.ndjson.gz` | 4,924,839 | `cc8177994617af646745a68f62e7b9f4ec9d2a6e589a30a2cbdbd74f42699e41` |
| v5 `employment_promotion_decisions.ndjson.gz` | 1,653,232 | `0b862bb7a4b1cc52ed8d1a768e4b4dfefee32f5ec33ee5a1c0688adea20157d3` |
| A9 sidecar ledger (primary = twin) | — | `f7e3350f122b5d5c5347baabf4ec1e268c00e300df282ae61db78ab0b8a68423` |
| A5b priority queue `employment_acquisition_adjudication_priority_queue_25340.ndjson.gz` | 2,530,929 | `59b24e1bc6c7af1b68b99203d831c43e2df97fac04d676161e45a9042b4e8ea2` |
| A5c recovered artifact, 1997Q1 Part 2 PDF | 39,235,422 | `21bb07508249c8ec28dd731a64bdc343cdc6347c3355b0523fc6e011104215d4` |
| Temporal v4 manifest (from pointer) | — | `0c3a13b8d664a504df97263eed6cab7e6b5974c3633119dbb52465de5d3266ce` |
| Meta LOOP blocking event | — | `C:\Users\pgoff\.claude\glassbox\events\evt-20260901T0141474876529Z-24f3966659.json` |

Measurement scripts and machine-readable tallies for every figure are in the session
scratchpad (`census_v3_v5.json`, `source_coverage.json`, `house_2016_join.json`).
