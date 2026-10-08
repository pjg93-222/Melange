# Employment promotion gate audit

Date: 2026-09-01  
Scope: sealed LDA lobbyist cohort and Stephanie Belk trace  
Verdict: **the reported zero is a construction invariant, not an empirical count of complete histories**

## Correction

The statement "fully verified complete employment histories: 0" overstates what the
adjudication output proves. The v3 overlay was deliberately implemented as a quarantine:
it hard-codes every decision and provisional episode as noncanonical, assigns zero final
episodes to every person, and writes zero promotions and zero lifetime assertions to the
receipt. Its verifier then requires those zero/false values. Therefore the output cannot
measure how many histories in the underlying evidence are complete.

The defensible result is:

- canonical histories promoted by this run: **0 by construction**;
- people with at least one provisional episode: **1,186**;
- number of substantively complete histories present in all acquired evidence: **not yet
  measured by this run**.

## Global gates in the v3 receipt

All five were marked `OPEN` for every one of the 25,340 LDA source identities:

1. `COVERED_POSITION_PARSER_PRECISION_GOLD_100_REQUIRED`
2. `IDENTITY_PRECISION_RECALL_GOLD_200_REQUIRED`
3. `CONTAINER_ADJUDICATION_REQUIRED`
4. `SENATE_TEMPORAL_OBSERVATION_AUDIT_REQUIRED`
5. `FABLE_OPUS_5_ADVERSARIAL_PASS_REQUIRED`

The first four are substantive or calibration gates. The fifth remained open even though
the external review was recorded as waived for speed; it consequently functioned as a
blanket promotion blocker rather than a person-level evidence test.

## Construction gates that force zero

The generator:

- sets `canonical_eligible=false`, `canonical_employment_promoted=false`, and
  `complete_lifetime_employment_asserted=false` in every decision;
- sets the same fields to false in every provisional episode and also forces
  `temporal_weight_eligible=false`;
- sets every person summary to `final_episode_count=0`,
  `canonical_employment_promoted_count=0`, and
  `complete_lifetime_employment_asserted=false`;
- writes receipt totals of zero for canonical promotions, lifetime assertions, and
  primary temporal-eligible episodes.

The independent verifier treats any true canonical value as a failure. This correctly
verifies a quarantine artifact, but it cannot adjudicate completeness.

## Corpus-level disposition

The run produced 235,454 decisions:

| Lane | Provisional/accepted | Review required | Rejected |
|---|---:|---:|---:|
| LDA covered-position parser | 1,878 | 39,384 | 418 |
| House payroll | 3,588 | 28,515 | 0 |
| Senate payroll | 125 | 6,828 | 0 |
| Structured public profiles | 76 | 255 | 0 |
| Bulk employment lines | 0 | 77,028 | 20,330 |

Those counts show that most acquired employment evidence was retained as review material,
not promoted. Exact fact consolidation reduced 5,667 supporting acceptances to 4,996
provisional episodes.

## Stephanie Belk (`lda:lobbyist:147663`)

Stephanie's data was not deleted from the workspace. It was split across evidence lanes,
and the richest lane was omitted from the v3 adjudicator input manifest.

### Evidence still present

1. **Authenticated LinkedIn profile** — five dated employment facts and one education
   fact:
   - America's Credit Unions — Legislative Advocacy Director — Aug 2024–present
   - Scalise Leadership Fund — Political Operations Director — Jul 2018–Nov 2023
   - Scalise Leadership Fund — Political Operations Coordinator — Aug 2015–Jul 2018
   - United States Senate — Scheduler — Jan 2013–Aug 2015
   - United States Senate — Staff Assistant — Jan–Dec 2012
   - University of Richmond, BS, Business Administration/Marketing/Leadership Studies;
     attendance dates absent

2. **LDA covered-position literal** —
   `Staff Assistant for Senator David Vitter Scheduler for Senator David Vitter`.
   The parser found two high-confidence titles and two high-confidence office mentions,
   but no embedded dates. It left the structured title/employer null and marked the claim
   review-required instead of splitting it into two episodes.

3. **Official Senate payroll** — one bounded Staff Assistant observation was provisionally
   accepted (2012-04-02 through 2012-09-30 in the source interval; represented internally
   with a half-open 2012-10-01 end). Six later Scheduler report intervals spanning
   2012-10-01 through 2015-08-12 were sent to review because the adjudicator refused to
   merge or split a multi-interval observation set.

4. **LDA registrant association** — 22 filings associate her with Credit Union National
   Association/America's Credit Unions in filing years 2024–2026. The run accepted the
   source-native association but, correctly in isolation, did not treat filing activity as
   proof of continuous employment. Her authenticated current-employer evidence supplies
   the missing independent employment assertion.

### Actual integration defect

`linkedin_authenticated_evidence.ndjson` contains ten authenticated profiles, 74
employment facts, and 17 education facts. It was **not listed among the v3 adjudicator's
inputs**. The structured-profile input used by v3 was a different file and contains no
Stephanie Belk row. Consequently, all five of her dated profile jobs and her education
record were invisible to the run that generated the zero-promotion summary.

### Stephanie's v3 result

- four decision rows;
- one provisional episode (Staff Assistant observation only);
- one LDA covered-position claim left review-required;
- one six-interval Scheduler payroll record left review-required;
- one registrant association accepted but not materialized as employment;
- all five authenticated profile jobs omitted from adjudication;
- zero final episodes because the generator forces zero for every person.

## Gates that should remain versus gates that need repair

Keep fail-closed checks for exact identity, source binding, date ordering, employer/container
resolution, and distinguishing payroll observation from continuous employment.

Repair the following:

1. ingest the authenticated profile ledger as a first-class adjudication input;
2. replace blanket global blockers with episode/person-level gate results;
3. split multi-role LDA literals and disjoint payroll observation sets instead of rejecting
   the whole record;
4. allow independent evidence lanes to corroborate one another (for Stephanie: profile +
   LDA role literal + Senate payroll + LDA registrant filings);
5. stop requiring the quarantine verifier's universal false/zero invariant in the
   promotion-stage verifier;
6. compute completeness only after reconciling all retained evidence, then record explicit
   known gaps separately from unknown/missing coverage;
7. report `not adjudicated` rather than `0 complete` until the promotion-stage computation
   has actually run.

No source artifacts were modified during this audit.
