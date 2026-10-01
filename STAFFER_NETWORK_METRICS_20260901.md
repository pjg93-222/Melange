# Staffer Network Metrics — Employment Promotion Addendum

**Version:** 3.3 employment-promotion corrective record  
**Date:** 2026-09-01  
**Extends:** sealed `STAFFER_NETWORK_METRICS_20260829.md`  
**Status:** BLOCKED — V5 payloads verify for narrow inputs, but full evidence conservation, identity adjudication, and complete-history gates fail

## Gate metrics

| Metric | Result |
|---|---:|
| V5 internal quarantine flag | false — implementation defect; not a governing waiver |
| Governing canonical employment quarantine | true |
| Gates V5 recorded as removed | identity gold; Senate observation audit; external review — prototype history only |
| Retained gates | covered-position parser; container normalization |
| Decisions reporting container gate PASS | 18,965 |
| Decisions using unadjudicated `NORMALIZED_LITERAL` container slugs | 7,965 |
| Non-unique source-name bindings blocked | 2,642 |
| Invalid intervals blocked | 70 |

Source-native LDA IDs do not require cross-source entity-resolution calibration merely to
retain their own evidence. Employment episodes, cross-source bindings, temporal edges,
complete-history assertions, publication, and consumer use remain quarantined. The 2,712
V5 blocked records are Senate-stage outcomes only, not a global exclusion ledger. The
retained container gate is not yet substantive for the 7,965 automatic literal slugs.

## Coverage metrics

| Metric | Result |
|---|---:|
| Provisional V5 employment people | 2,672 |
| Provisional V5 employment episodes | 18,815 |
| Provisional V5 education records | 17 |
| Typed affiliation memberships | 102,162 |
| Normalized containers/groups | 8,169 |
| Shared-affiliation edge inputs | 189,098 |
| Primary canonical co-tenure edges | 27,088 |
| Primary canonical revolving-door edges | 12 |

## Numerical and integrity metrics

| Metric | Target | Result |
|---|---:|---:|
| Provisional V5 episode schema/semantics failures | 0 | 0 |
| Dangling promotion decisions | 0 | 0 |
| Duplicate episode/decision/edge IDs | 0 | 0 |
| Self-loops | 0 | 0 |
| Undated nonzero temporal weights | 0 | 0 |
| Primary/twin payload mismatches | 0 | 0 |
| Edge-weight recomputation tolerance | `<=1e-15` | PASS |
| Support-digest mismatches | 0 | 0 |

For `d` guaranteed overlap days after unioning intervals per person/container:

\[
w=1-\exp(-d/365.2425).
\]

LDA filing affiliation is segmented into observed filing years before overlap is
calculated. No first-to-last-year continuity is imputed.

## Stephanie Belk control case

All assertions passed:

- five authenticated profile jobs present;
- one education record present;
- the LDA Staff Assistant/Scheduler literal retained as corroboration;
- seven Senate payroll intervals retained;
- current role normalized to `lda:registrant:11322`;
- filing memberships limited to observed years 2024, 2025, and 2026.

Independent verifier receipt:
`audits/staffer_network/employment_promotion_generation_20260901_v5_verification/employment_promotion_verification_receipt.json`.

## Fresh database-overview correction

The 2026-09-01 source-neutral inventory changes the interpretation of the coverage
metrics without changing the V5 payload counts.

| Metric | Result |
|---|---:|
| Sealed people | 25,340 |
| People with structured source-profile employment | 912 |
| Source profiles role/employer complete, ignoring education and time | 890 |
| Source profiles role/employer incomplete | 22 |
| People with substantive collected employment assertions | 9,847 |
| Field-complete on collected assertions, ignoring education and time | 4,802 |
| Lifetime histories attested exhaustive | 0 |
| V5 field-complete people on represented inputs | 2,672 |
| Complete-lifetime employment histories | 0 |
| People still failing the complete-lifetime gate | 25,340 |
| People with every substantive LDA claim ID in same-person canonical support | 460 |
| Substantive LDA claims | 41,262 |
| Same-person canonical-supported LDA claims | 2,812 |
| Unrepresented substantive LDA claims | 38,450 |
| Unrepresented claims already containing both role and employer/office | 21,650 |

`SOURCE_PROFILE_ROLE_EMPLOYER_COMPLETE` is the practical source-profile state: at least
one structured profile job and employer plus role/title on every captured profile job.
Stephanie Belk passes this state with five profile jobs. Gordon Holzberg does not yet pass
because the earlier profile capture was not conserved into a current structured ledger;
his exact LDA identity, LegiStorm crosswalk, and five-role covered-position claim remain.

`FIELD_COMPLETE_ON_COLLECTED_ASSERTIONS` is the broader field-coverage state, not a
canonical promotion or lifetime-history assertion. Explicit-no-position responses remain
separate. The zero lifetime-attestation count must not be presented as zero usable
profiles, but it does mean that canonical employment promotion and temporal production
remain blocked. Education is nonbinding enrichment: missing education neither fails nor
passes the employment-completeness gate.

V5 omits already-local House 2016–2026, House 1997Q1, A7 FEC point observations, A7
LD-203 candidate IDs, Politico, LittleSis, public LinkedIn, most rapid structured facts,
working-history source facts, and the source-native client/industry edge layer. The union
of omitted candidate families contains 11,337 people without V5 provisional employment.

Current inventory receipt:
`audits/staffer_network/profile_evidence_inventory_20260901_v4_primary/profile_evidence_inventory_receipt.json`.

## Final adjudication

V5 passes deterministic payload and numerical-integrity checks for its represented input
lanes. It fails the governing corpus gate because the build is not source-conserving, all
25,340 complete-lifetime attestations are absent, cross-source identity adjudication is
unfinished, and material employment families remain omitted. The governing counts are
therefore zero canonical employment promotions and zero production temporal edges.
