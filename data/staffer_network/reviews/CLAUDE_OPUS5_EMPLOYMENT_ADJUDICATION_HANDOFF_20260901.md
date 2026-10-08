# Claude Opus 5 handoff — employment adjudication overlay

Date: 2026-09-01  
Repository: `C:\Users\pgoff\OneDrive\Desktop\Melange Systems`  
Meta LOOP run: `run-20260901T1341531206612Z-06b5ca2f8a`  
Required reviewer: canonical Claude Opus 5/Fable 5 at effort `max`; do not substitute Sonnet.

## Review objective

Perform a read-only adversarial review of the new source-neutral employment-adjudication
overlay. The review must decide whether the implementation is fail-closed and whether any
provisional episode is accidentally able to enter canonical or primary temporal outputs.
Do not edit files. Do not interpret raw acquisition candidates as complete employment
histories. Return `PASS` only if there is no correctness blocker; otherwise return `FAIL`
with exact file/line findings and the smallest non-weakening remediation.

## Primary artifacts

Implementation and verification:

```text
audits/staffer_network/adjudicate_bulk_employment_candidates.py
audits/staffer_network/verify_bulk_employment_adjudication.py
audits/staffer_network/test_adjudicate_bulk_employment_candidates.py
fec/staffer_network/employment_history.py
fec/tests/staffer_network/test_staffer_employment_history.py
```

Generated primary, independent twin, and verifier:

```text
audits/staffer_network/employment_adjudication_generation_20260901_primary
audits/staffer_network/employment_adjudication_generation_20260901_twin
audits/staffer_network/employment_adjudication_generation_20260901_verification
```

Primary receipt SHA-256:

```text
21a58a674585e904cf1e3b3633e95e305b38b25eb560f989bfc74ca01fbf0a49
```

## Measured outcome

The sealed scope is exactly 25,340 LDA source-person IDs. The build conserves 235,454
decision rows and emits 6,289 provisional episodes:

| Lane | Provisional episodes |
|---|---:|
| House payroll corroborated | 3,588 |
| Senate payroll corroborated | 739 |
| LDA covered-position parse | 1,885 |
| Structured public profile | 77 |

Other decision counts:

```text
ACCEPTED_SOURCE_BINDING              10,701
ACCEPTED_SOURCE_NATIVE_ASSOCIATION   25,469
PROVISIONALLY_ACCEPTED                6,289
REJECTED                             22,388
REVIEW_REQUIRED                     170,607
```

The following values must remain exactly zero in this generation:

```text
cross_source_identity_merges
canonical_employment_promotions
complete_lifetime_employment_assertions
primary_temporal_eligible_episodes
```

The primary and twin receipts and all five payloads are byte- and SHA-256-identical. The
independent verifier reports `PASS`, including exact input binding, row conservation,
25,340-person scope, unlabeled gold samples, closed canonical gates, and a token-negative
artifact scan. Fresh local tests report `229 passed, 73 subtests passed`.

## Binding evidence semantics

1. Page-level dates, LDA filing dates, and LegiList `Years Active` never become employment
   dates.
2. A one-token name overlap never accepts identity.
3. An exact LegiList numeric URL ID equal to the LDA source ID plus ordered first/last name
   is only an accepted source-page binding. It is not a cross-source person merge and does
   not prove an employment episode.
4. LDA person-to-registrant activity is a source-native filing association, not continuous
   employment.
5. Payroll matches are provisional until identity calibration and container normalization.
6. Covered-position parses are provisional until the 100-record parser gold sample proves
   precision at or above 0.95.
7. Identity rules remain provisional until the 200-record gold set proves precision at or
   above 0.98 and recall at or above 0.90, with permuted-name false acceptance below 1%.
8. Only an active episode with person identity `ACCEPTED` and container identity
   `ACCEPTED`, valid half-open bounds, and evidence bindings may enter the temporal plane.
9. A complete lifetime history additionally requires a digest-bound, attributed exhaustive
   attestation with zero unresolved employment gaps.

The receipt intentionally leaves these gates open:

```text
COVERED_POSITION_PARSER_PRECISION_GOLD_100_REQUIRED
IDENTITY_PRECISION_RECALL_GOLD_200_REQUIRED
CONTAINER_ADJUDICATION_REQUIRED
FABLE_OPUS_5_ADVERSARIAL_PASS_REQUIRED
```

## Required adversarial checks

1. Inspect representative decisions from every lane, including false-name and generic-role
   risks, multi-clause covered-position strings, current/right-censored intervals, and
   duplicate-name LDA IDs.
2. Try to produce a canonical or primary-temporal episode from any provisional decision.
   Any successful route is a blocking failure.
3. Confirm half-open interval conversion and uncertainty bounds do not overstate tenure.
4. Confirm every decision and episode has a stable unique ID, evidence digest, and no
   page-level date leakage.
5. Confirm accepted source bindings and source-native filing associations cannot be
   confused with accepted employment.
6. Review `audit_history_completeness` specifically. If it can return `COMPLETE` without
   explicit accepted person identity and accepted container identity for every episode,
   treat that as a blocker and specify the exact fail-closed contract.
7. Inspect whether any generated schema ID lacks an enforceable source-neutral JSON Schema;
   report missing registration as a blocker if it could permit semantic drift.
8. Confirm the verifier independently recomputes material invariants instead of merely
   trusting the receipt.

## Required response

Return a complete Markdown review intended for:

```text
data/staffer_network/reviews/OPUS5_EMPLOYMENT_ADJUDICATION_REVIEW_20260901.md
```

Include the exact canonical model name reported by Claude, effort `max`, verdict `PASS` or
`FAIL`, blocking findings with file/line references, non-blocking limitations, and the
specific commands/evidence inspected. Do not return `PASS` while any identified blocker is
open. The coordinator will save the returned text; do not modify the repository.
