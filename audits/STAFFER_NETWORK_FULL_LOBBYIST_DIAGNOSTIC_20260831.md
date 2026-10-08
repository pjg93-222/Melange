# Staffer network — full lobbyist employment-layer diagnostic

Date: 2026-08-31  
Status: **IMPLEMENTED FOUNDATION; EMPLOYMENT ENRICHMENT OPEN**  
Meta LOOP: `run-20260831T0243340126420Z-4fda60e57a`

## Executive ruling

The LDA plane is complete for the sealed local 2021–2026 source window and now has a
conserved, one-row-per-person employment lookup corpus covering all 25,340 LDA lobbyist
IDs. The canonical entity/fact layer and structural graph v6 were already built and passed.
The new code adds a restricted employment episode contract and conservative temporal
co-tenure/revolving-door sidecar without altering structural v6.

What is not complete is the external employment-history enrichment itself. LDA provides
substantial former covered-position prose but not uniformly dated episodes: 9,484 people
have position text, only 2,166 of those contain a four-digit year token, and only 597 contain
a month token. Dates and employers therefore still require direct profile/payroll evidence
and adjudicated identity/container links. Search/LegiStorm discovery is not silently promoted
to a canonical fact.

## Materialized artifacts

### Sealed LDA source-native corpus

```text
C:\Users\pgoff\AppData\Local\Melange\staffer_network\normalized\lda-source-native\generation-20260830T231200Z
```

| Artifact | Count |
|---|---:|
| Lobbyists | 25,340 |
| Lobbyists with covered-position text | 9,484 |
| Covered-position assertions | 748,589 |
| Unique person-position pairs | 21,511 |
| Activities | 1,037,547 |
| Registrants | 7,077 |
| Clients | 46,996 |
| Industry edges | 4,816,559 |

All 383,705 activity IDs referenced by covered-position assertions resolve to an activity;
all have registrant and client IDs. Those organization bindings describe lobbying
activities, not former employers.

### Full employment lookup queue

```text
C:\Users\pgoff\AppData\Local\Melange\staffer_network\employment-lookup\generation-20260831T050000Z
```

Receipt status: `PASS`  
Queue SHA-256: `5e240a91a21e237525547eef84456daee7dd5339723073ced9437a9f5ea5f649`

An independently materialized deterministic twin produced the identical byte hash.

| Priority | People | Scheduling meaning |
|---|---:|---|
| P0 | 6,527 | Government-term lexical hit |
| P1 | 2,957 | Other non-empty covered-position text |
| P2 | 15,856 | No covered-position text in the source window |
| Total | 25,340 | Exact LDA person census |

Every row remains `REVIEW_REQUIRED`; identity matches asserted = 0; canonical merges = 0.
The queue is restricted-machine-local and cannot enter public generation publication.

## Implementation

Primary implementation:

```text
fec/staffer_network/employment_history.py
```

New registered restricted schemas:

```text
employment_lookup_candidate.schema.json
employment_lookup_receipt.schema.json
employment_episode.schema.json
temporal_path.schema.json
temporal_edge.schema.json
temporal_build_receipt.schema.json
```

The builder:

- verifies the sealed zero-merge LDA PASS receipt;
- verifies the lobbyist artifact by exact bytes and SHA-256;
- creates a deterministic source-bound candidate ID per LDA person;
- conserves the full 25,340-person census across P0/P1/P2;
- writes deterministic gzip with `mtime=0`;
- reopens, schema-validates, semantic-validates, and re-conserves persisted rows;
- binds the final queue by rows, bytes, and SHA-256;
- asserts no identity result or merge.

## Temporal math adjudication

All internal intervals are day-granularity half-open `[start,end)`. Source-inclusive end
dates advance one day before storage. Uncertain episodes retain earliest/latest bounds.

For episode `e`:

```text
core(e)     = [start_latest(e), end_earliest(e))
envelope(e) = [start_earliest(e), end_latest(e))
```

### Co-tenure

Union episodes per `(person, container)` before intersection:

```text
G(p,q,c) = days(union(core(p,c)) intersect union(core(q,c)))
P(p,q,c) = days(union(envelope(p,c)) intersect union(envelope(q,c)))
0 <= G <= P
```

Possible-only overlap carries primary weight zero. Union overlap calendars across containers
before graph aggregation to prevent simultaneous multi-office double counting.

```text
f(d;tau) = 1 - exp(-d/tau)
w_lower  = f(G;365.2425)
w_upper  = f(P;365.2425)
```

This is a bounded duration transform, not an influence probability. `tau` is a declared
prior and requires half/double sensitivity.

### Revolving door

The implementation keeps registrant employment and client activity distinct:

```text
FORMER_STAFFER_EMPLOYED_BY_REGISTRANT
FORMER_STAFFER_NAMED_ON_ACTIVITY_FOR_CLIENT
```

For Hill episode `h` and later industry episode/event `z`:

```text
guaranteed order: end_latest(h) <= start_earliest(z)
possible order:   end_earliest(h) <= start_latest(z)
gap_min = max(0, start_earliest(z) - end_latest(h))
gap_max = max(0, start_latest(z) - end_earliest(h))
```

Each person contributes at most once per member/organization/role. Primary
member-organization weight is the unique accepted-person count. Optional gap-decayed bounds
are sensitivity features, never causal/influence claims.

### Structural connectedness and eigenvector ruling

The existing structural graph remains separate:

- source support is combined with bounded noisy-OR after retaining the strongest row per
  source;
- scoring de-duplicates unordered endpoint/layer keys;
- the transition operator divides each node's mass equally across its active layers, then
  proportionally within a layer;
- eigenvector centrality is computed independently inside each connected component on the
  symmetric balanced operator; unconverged component values are null and isolates are zero;
- connectedness influence is PageRank on the layer-balanced transition matrix with
  node-kind-balanced teleportation;
- bridging diversity remains a separate strength-invariant Simpson diversity statistic.

Temporal co-tenure cannot be inferred from LDA filing dates, and temporal weights remain a
sidecar until dated accepted episodes exist.

## Verification

```text
113 passed, 65 subtests passed
```

New tests cover:

- full LDA-person conservation and zero-merge behavior;
- inclusive-end conversion;
- half-open adjacency;
- episode union and duplicate-row noninflation;
- possible-only overlap exclusion;
- Gordon Holzberg's 211–241 day gap fixture;
- distinct registrant-employment/client-activity predicates;
- unique-person revolving contribution;
- schema registry and restricted publication containment.

## Access/source diagnostic

- Politico Pro remains an authorized source in the existing design; this stage did not
  disable it.
- LittleSis is a sealed supplementary source and remains noncanonical until its identity
  decisions pass; it is not frozen by this change.
- LDA is the complete local lobbying spine for the sealed window.
- LegiStorm is useful for person/profile discovery, but its public terms prohibit bulk
  copying without written permission. A production bulk pass requires a license/export/API
  or explicit LegiStorm authorization. Official House/Senate payroll is the scalable source
  for canonical dated employment.

## Remaining implementation work

1. Populate employment observations for all queue rows, scheduled P0 → P1 → P2.
2. Adjudicate person identity and employer/container separately.
3. Normalize dates into the implemented episode schema.
4. Run the temporal sidecar and conservation receipt.
5. Require Opus 5 max adversarial PASS.
6. Only then consider a separately gated temporal promotion; structural v6 stays unchanged
   until that decision.

The self-contained continuation prompt is:

```text
data/staffer_network/reviews/CLAUDE_OPUS5_FULL_LOBBYIST_EMPLOYMENT_HANDOFF_20260831.md
```
