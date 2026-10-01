# Staffer Network Expansion Design — Employment Promotion Addendum

**Version:** 3.2 employment-promotion corrective addendum  
**Date:** 2026-09-01  
**Extends:** sealed `STAFFER_NETWORK_EXPANSION_DESIGN_20260829.md`  
**Status:** V5 is a verified provisional materialization; canonical employment promotion and temporal production remain blocked

## Corrective ruling

V5's internal `quarantine_enabled=false` flag does **not** disable the governing
employment quarantine. V5 verified deterministic behavior for a narrow six-lane input,
but it omitted material local evidence and did not establish complete employment
chronologies for the sealed 25,340-person scope. Its episodes, memberships, and temporal
edges therefore remain provisional implementation outputs and may not be represented as
canonical employment or used by production consumers.

Source-native LDA person IDs may retain their own source-native evidence without
cross-source identity calibration. That narrow evidence-retention rule does not authorize
an employment episode, a cross-source person binding, a co-tenure edge, a revolving-door
edge, or a complete-history assertion. Those outputs remain subject to accepted identity
adjudication, source/container resolution, chronology completeness, and the publication
gates in the governing corpus specification and diagnostic.

The gates that V5 recorded as removed—identity gold calibration, the Senate temporal-
observation audit, and external review—are historical properties of that prototype, not
governing waivers. The current canonical boundary remains fail closed. Covered-position
parser calibration and container normalization also remain required record-level gates.

Official Senate report intervals are split into bounded observations. Ambiguous undated
LDA covered-position literals may corroborate independently dated roles but cannot date a
role themselves.

## Provisional V5 hierarchy

```text
person
  ├─ employment episode ──> normalized member office / office / organization
  └─ LDA filing-year affiliation ──> registrant

normalized container + overlapping time
  └─ shared-affiliation path ──> weighted person-person edge input
```

Employment and LDA registrant-filing affiliation remain different relationship types.
Registrant membership is segmented by each observed filing year; the implementation does
not fill gaps between a person's first and last filing year.

## Provisional co-service edge construction

For each person and normalized container:

1. union all supported half-open intervals;
2. intersect the two people's unioned ranges;
3. sum guaranteed overlap days `d`;
4. emit an edge only when `d > 0`;
5. retain every supporting observation ID and a deterministic digest.

The bounded duration weight is:

\[
w_{ij,c}=1-\exp(-d/365.2425).
\]

Union-before-intersection prevents duplicate payroll reports and corroborating profile
episodes from multiplying the weight. Possible-only overlap remains separate from
guaranteed overlap in the canonical temporal sidecar.

## Narrow V5 verification

- 2,672 people with provisional V5 employment;
- 18,815 provisional V5 employment episodes;
- 102,162 typed employment/filing-year memberships;
- 8,169 normalized office or organization groups;
- 189,098 shared-affiliation edge inputs;
- 27,088 primary canonical co-tenure edges;
- 12 primary revolving-door edges;
- zero self-loops or undated temporal weights.

These counts prove internal integrity and deterministic reproduction only. They do not
supersede the governing corpus result of zero canonical employment promotions and zero
complete-lifetime attestations across the 25,340-person scope.

The selected generations are bound by
`data/staffer_network/employment_promotion_current.json` and
`data/staffer_network/employment_temporal_current.json`.

Those pointers select the current V5 **prototype** generations for verification; they are
not publication or consumer-arm pointers.

## Binding employment-completion contract

Employment chronology is the binding objective for every one of the 25,340 sealed LDA
identities. `COMPLETE` requires a nonempty accepted person ID; employer or office and title
for every episode; source-supported start and end bounds or explicit currentness; an
exhaustive-history attestation bound to the exact merged episode digest; no unresolved
typed or legacy employment gaps; and adjudication `PASS`. Missing, ambiguous, stale, or
unresolved evidence fails closed as `PARTIAL` or `REVIEW_REQUIRED`.

Education is optional enrichment. It has a separate evidence and diagnostic surface, but
missing education never blocks the employment verdict and education cannot certify an
employment history as complete.

## Database-overview revision

V5 is a verified materialization of six input lanes, not a conserved build of the local
staffer-network corpus. It must not be described as the completed employment or industry
layer. A corrected implementation adds a source-neutral affiliation fact model:

```text
person
  ├─ accepted dated employment ──> normalized container ──> temporal scoring eligible
  ├─ accepted undated employment ──> normalized container ──> structural only
  ├─ review candidate role/employer ──> candidate container ──> no canonical edge
  ├─ LDA filing association ──> registrant ──> affiliation only
  └─ FEC employer observation ──> organization ──> point observation only
```

The fact schema must carry relation semantics, raw and normalized container fields, raw
role title, temporal precision including `UNDATED` and `POINT`, nullable dates,
identity-binding class, container and fact status, independent structural/temporal
eligibility, exact support IDs and digest, and source-receipt hashes. Silence creates an
inventory state of `NONE`, never a negative employment fact.

Undated records may contribute to organization grouping only after accepted identity and
container decisions. They have `temporal_eligible=false`, zero temporal weight, and may
not enter co-tenure, revolving-door, eigenvector, or connectedness calculations as if a
duration were observed. Candidate-only Politico, LittleSis, payroll, profile, and
cross-source rows stay in a separate candidate schema until their bindings pass.

The source-native LDA client/industry layer must be loaded alongside registrants: 4,816,559
held edges comprise 2,741,465 `NAMED_ON_ACTIVITY`, 1,037,547 `FILED_BY`, and 1,037,547
`FOR_CLIENT`. This is the missing third layer beneath staffers and former staffers.

The fresh evidence inventory is bound by
`data/staffer_network/profile_evidence_inventory_current.json`. Its PASS means deterministic
scope and support reconciliation only; lifetime-history completeness remains unattested.

Profile completeness is now intentionally multi-axis. `SOURCE_PROFILE_ROLE_EMPLOYER_COMPLETE`
means a structured profile has at least one job and every captured job has employer plus
role/title; it ignores education and temporal coverage. `FIELD_COMPLETE_ON_COLLECTED_ASSERTIONS`
applies the same field rule across all evidence lanes. `LIFETIME_HISTORY_NOT_ATTESTED` remains
a provenance warning and must never overwrite either usable-content state. Known profile
captures that disappear between acquisition and structured ledgers must enter a repair queue,
not be silently reclassified as people with no employment evidence.
