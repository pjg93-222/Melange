# Employment adjudication implementation diagnostic

> **Current governing promotion status:** this document preserves the v3 quarantine
> checkpoint. The later V5 materialization is documented in
> `EMPLOYMENT_PROMOTION_IMPLEMENTATION_DIAGNOSTIC_20260901.md`, but its scoped payload
> `PASS` does not authorize canonical promotion. Complete-history and identity gates
> remain open, so the governing promotion verdict is still `BLOCKED_REVIEW_OPEN`.

Date: 2026-09-01  
Scope: sealed LDA lobbyist cohort (`25,340` source identities)  
Technical verdict: `PASS`  
Promotion verdict: `BLOCKED_REVIEW_OPEN`

## Outcome

The deterministic employment-adjudication quarantine is implemented and ready
for the next adjudication stage. It is not a complete-career corpus and it does
not authorize canonical employment, co-tenure, revolving-door, or influence
weights.

| Measure | Result |
|---|---:|
| Candidate decisions | 235,454 |
| Provisionally accepted supports | 5,667 |
| Unique provisional facts | 4,996 |
| Duplicate supports consolidated | 671 |
| People with at least one provisional fact | 1,186 |
| People without a provisional fact | 24,154 |
| Canonical promotions | 0 |
| Lifetime-complete assertions | 0 |
| Primary temporal-eligible facts | 0 |

Lane facts: House payroll `3,552`; LDA covered positions `1,243`; Senate payroll
`125`; structured public profiles `76`. Temporal semantics: `3,677`
`OBSERVATION_ONLY`, `1,319` `ASSERTED_EPISODE`.

## Verification

- Primary/twin generation receipt SHA-256:
  `02ff23202da31be3ae49db04dc84735316dd4f8c42c632f98380effa11a4a263`
- Independent v4 verification receipt SHA-256:
  `7b6484ea5cdd6ee2558a7b5e9b3e3bf11667e8e40bc311b5daccf152d4f89ef6`
- Generator SHA-256:
  `7cfadd8680408639a0b79889ae5542508436942cd70c8e31f3d9a7c339f04135`
- Verifier SHA-256:
  `066e8d25de9c8f2fa2d6718bcf9d234c8de69c538dc49b4d9a3d2fbfe3b50c73`
- Canonical-completeness implementation SHA-256:
  `10995753369959c264abc3f98a7e500b0501da1561149c7165073f3f69e5ac96`
- Full suite: `250 passed, 73 subtests passed`.
- Independent data-quality lanes: final `PASS`; no known blocking technical
  defect; token scan `0`.

The verification receipt self-binds its schema and executable. The canonical
completeness path independently verifies schema/semantics, immutable checkpoint
receipt and files, decision/observation relationships, source transforms,
supersession chains, exact LDA-person attribution, full episode-set equality,
and full observation support per employment key.

## Residual adjudication work

1. Label and adjudicate the 100-row covered-position parser calibration sample.
2. Label and adjudicate the 200-row identity calibration sample, then evaluate
   precision and recall on a separately frozen holdout.
3. Resolve literal containers for all 4,996 provisional facts.
4. Audit the 125 Senate observations, prioritizing the 39
   `REPORT_PERIOD_ONLY` rows.
5. Resolve the 57 within-year ordering ambiguities across 55 people before
   enabling temporal weights.

The external Opus/Fable review was waived by the user for speed on 2026-09-01.
It is recorded as `WAIVED_NOT_RUN`, never as `PASS`. The four substantive gates
above remain binding.

## Implementation entry points

- Generator: `audits/staffer_network/adjudicate_bulk_employment_candidates.py`
- Independent verifier:
  `audits/staffer_network/verify_bulk_employment_adjudication.py`
- Canonical/temporal guard: `fec/staffer_network/employment_history.py`
- Primary artifacts:
  `audits/staffer_network/employment_adjudication_generation_20260901_v3_primary`
- Twin artifacts:
  `audits/staffer_network/employment_adjudication_generation_20260901_v3_twin`
- Verification:
  `audits/staffer_network/employment_adjudication_generation_20260901_v4_verification`

No provisional episode was promoted.
