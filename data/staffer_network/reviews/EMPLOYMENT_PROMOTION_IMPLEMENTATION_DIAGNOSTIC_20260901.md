# Employment promotion and shared-affiliation implementation diagnostic

Date: 2026-09-01  
Status: **SCOPED PASS / GOVERNING GATE BLOCKED**  
V5 internal quarantine flag: **OFF — prototype defect, not a governing waiver**  
Governing canonical employment quarantine: **ON**

This diagnostic records deterministic and numerical verification of the V5 prototype.
It does not override the governing corpus specification or the complete-history contract:
all 25,340 people lack complete-lifetime attestations, cross-source identity adjudication
is unfinished, material local evidence is omitted, and canonical employment promotions
remain zero.

## Gate disposition

Recorded as removed inside V5; retained as prototype history rather than governing
waivers:

- `IDENTITY_PRECISION_RECALL_GOLD_200_REQUIRED`
- `SENATE_TEMPORAL_OBSERVATION_AUDIT_REQUIRED`
- `FABLE_OPUS_5_ADVERSARIAL_PASS_REQUIRED`

Retained:

- `COVERED_POSITION_PARSER_PRECISION_GOLD_100_REQUIRED`
- `CONTAINER_ADJUDICATION_REQUIRED`

The retained parser gate prevents an ambiguous, undated multi-role LDA literal from
becoming a standalone dated episode. Such literals may still corroborate roles that are
dated by independent payroll or profile evidence. Container normalization is performed
before provisional V5 materialization. Source-native LDA person IDs may retain their own
evidence without identity calibration, but that rule does not authorize cross-source
binding, canonical employment, temporal production, or a complete-history assertion.

## Materialized corpus

| Measure | Count |
|---|---:|
| Provisional V5 people with employment | 2,672 |
| Provisional V5 employment episodes | 18,815 |
| Promotion decisions | 18,965 |
| Provisional V5 education records | 17 |
| Service/filing affiliation memberships | 102,162 |
| Normalized office/organization groups | 8,169 |
| Shared-affiliation weighted edges | 189,098 |
| Records still blocked | 2,712 |

The blocked set contains 2,642 non-unique LDA-name bindings and 70 invalid or unusable
intervals. These are V5 record-level failures, not a complete global exclusion ledger.

## Grouping and edge weights

Employment episodes and LDA registrant-filing associations are grouped by normalized
office or organization. Employment remains typed separately from
`LDA_REGISTRANT_FILINGS`; filing co-occurrence is not relabeled as employment.
Registrant membership is segmented by each observed filing year rather than filling the
first-to-last-year envelope.

For each person and container, half-open service intervals are unioned before pairwise
intersection. This prevents duplicate sources or adjacent payroll reports from inflating
duration. If two people have `d` guaranteed overlap days in the same container, the
bounded edge input is:

\[
w_{ij,c}=1-\exp(-d/365.2425).
\]

Weights are finite, nonnegative, below one for finite duration, and are emitted only for
positive overlap. The source support set and digest are retained on every edge.

The provisional V5 temporal builder independently produced:

- 59,598 co-tenure candidate keys;
- 27,728 guaranteed-overlap candidates;
- 264 possible-only candidates;
- 31,606 zero-overlap candidates;
- 27,088 primary co-tenure edges;
- 12 primary revolving-door edges;
- zero self-loops, unresolved identities, or undated temporal weights.

## Stephanie Belk

`lda:lobbyist:147663` now has:

- all five authenticated profile employment episodes;
- one education record;
- the two-role LDA literal retained as corroboration;
- all seven Senate payroll intervals split and retained;
- the current America's Credit Unions role normalized to
  `lda:registrant:11322`;
- 15 total affiliation memberships (12 employment evidence episodes plus three observed
  LDA registrant-filing years);
- 41 shared-affiliation edges in the broader employment-plus-filing grouping layer.

The multiple payroll observations and the five profile jobs are not five-plus-seven
distinct jobs: payroll observations remain bounded supports for the two Senate roles.
Union-before-intersection prevents those observations from multiplying edge weight.

## Verification

- Independent promotion verifier: `PASS`
- Primary/twin payloads: byte-identical for all six promoted artifacts
- Provisional V5 episode schemas and semantics: `PASS`
- Promotion decision IDs: unique; all references resolve
- Episode IDs: unique
- Edge IDs: unique
- Edge formula recomputation: exact within `1e-15`
- Edge support digests: exact
- Self-loops: zero
- Full staffer-network suite: `172 passed, 73 subtests passed`

Primary promotion receipt SHA-256:
`644d9ded24aef5a4563c3eaa00910c84f9db85a4b31d162fefc244bfeaa665cc`

Provisional V5 employment payload SHA-256:
`cc8177994617af646745a68f62e7b9f4ec9d2a6e589a30a2cbdbd74f42699e41`

Temporal edge payload SHA-256:
`be5b82f7c355e10742f7ec9f1688bdc609f5c19afacf36f925e4bf6ca5cce9d1`

The selected-generation pointers are `data/staffer_network/employment_promotion_current.json`
and `data/staffer_network/employment_temporal_current.json`; they bind the verified v5
promotion receipt and the byte-identical v4 temporal receipt over the unchanged V5
episode payload, respectively. They are verification selectors, not publication or
consumer-arm pointers.

## Implementation entry points

- `fec/staffer_network/employment_promotion.py`
- `audits/staffer_network/verify_employment_promotion.py`
- `fec/staffer_network/employment_history.py` (`build-temporal`)
- primary generation:
`audits/staffer_network/employment_promotion_generation_20260901_v5_primary`
- twin generation:
`audits/staffer_network/employment_promotion_generation_20260901_v5_twin`
- independent verification:
`audits/staffer_network/employment_promotion_generation_20260901_v5_verification`
- temporal primary:
  `audits/staffer_network/employment_temporal_sidecar_20260901_v4_primary`
- temporal twin:
  `audits/staffer_network/employment_temporal_sidecar_20260901_v4_twin`
