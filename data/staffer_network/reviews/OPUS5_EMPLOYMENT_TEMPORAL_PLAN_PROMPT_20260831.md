# Fable / Opus 5 adversarial plan review: employment-history temporal sidecar

You are Fable, the read-only adversarial reviewer for the active staffer-network Meta LOOP in
`C:\Users\pgoff\OneDrive\Desktop\Melange Systems`. Do not edit files, execute network
collection, or relax a gate. Inspect the referenced implementation and return a concise
Markdown review with `PASS`, `CONDITIONAL PASS`, or `FAIL`, followed by blocking findings,
required changes, and exact adversarial tests.

## Objective

Turn the existing LDA lobbyist corpus into an evidence-bounded employment-history lookup and
temporal-analysis sidecar. The only facts sought from enrichment are employment episodes and
the employer/office for each episode. Search results and LegiStorm URLs are discovery leads;
primary temporal facts require direct source evidence and accepted identity/container
decisions. No paywall bypass or bulk LegiStorm copying is authorized.

## Existing state to inspect

- `fec/staffer_network/intervals.py`
- `fec/staffer_network/network_math.py`
- `fec/staffer_network/graph_build.py`
- `fec/staffer_network/publication.py`
- `fec/staffer_network/schemas/lda_lobbyist_assertion.schema.json`
- `fec/staffer_network/schemas/lda_covered_position_assertion.schema.json`
- `fec/tests/staffer_network/test_staffer_intervals.py`
- `C:\Users\pgoff\Downloads\STAFFER_NETWORK_EXPANSION_DESIGN_20260829.md`
- `C:\Users\pgoff\Downloads\STAFFER_NETWORK_METRICS_20260829.md`
- sealed LDA source-native receipt:
  `C:\Users\pgoff\AppData\Local\Melange\staffer_network\normalized\lda-source-native\generation-20260830T231200Z\lda_source_native_corpus_receipt.json`

The existing canonical v6 and structural graph v6 are PASS and must remain byte-identical
while this sidecar is disabled.

## Measured corpus facts

- 25,340 LDA lobbyist identities.
- 9,484 have non-empty covered-position text.
- 6,527 have an unadjudicated government-term lexical hit.
- 2,166 of the 9,484 covered-position identities contain an unambiguous four-digit year.
- 597 contain a month name.
- LDA covered-position text is prior covered-office narrative, not a complete or uniformly
  dated employment history. Filing `dt_posted` is not an employment start date.

## Proposed artifacts

All artifacts are restricted-machine-local immutable outputs until their gates pass:

1. `employment_lookup_queue.ndjson.gz`: one deterministic row per LDA lobbyist, priority P0
   for covered-position text with government lexical hits, P1 for other non-empty covered
   positions, P2 for no covered position. It carries exact-name Google/LegiStorm discovery
   queries but no asserted match.
2. `employment_observations.ndjson.gz`: source-native employment assertions with raw fields,
   source locators/digests, person name/id, employer/title, date bounds, source date
   semantics, source as-of, and optional member/registrant/client identifiers.
3. `employment_decisions.ndjson.gz`: independent accepted/rejected/ambiguous/review-required/
   superseded person and container decisions.
4. `employment_episodes.ndjson.gz`: derived accepted episodes retaining every supporting
   observation and half-open uncertain interval.
5. `temporal_paths.ndjson.gz` and `temporal_edges.ndjson.gz`, plus a receipt binding every
   input/output by role, bytes, rows, and SHA-256.

## Interval and co-tenure rules

Internal dates are day-granularity half-open intervals. Exact inclusive source ends become
the following day. A month start has bounds on the first and last day of that month; a year
start has January 1 / December 31 bounds. Current episodes are right-censored at
`min(source_as_of, build_as_of)`. Unknown/unbounded episodes are structural-only.

For an episode `e`:

```text
core(e)     = [start_latest(e), end_earliest(e))
envelope(e) = [start_earliest(e), end_latest(e))
```

Union cores and envelopes independently per `(person, normalized_container)` before any
intersection. For people `p,q` and container `c`:

```text
G(p,q,c) = days(union(core(p,c)) intersect union(core(q,c)))
P(p,q,c) = days(union(envelope(p,c)) intersect union(envelope(q,c)))
0 <= G <= P
```

Primary edges require `G > 0`; `G = 0 < P` is possible-only with primary weight zero. Union
overlap calendars across containers before the graph-level duration so simultaneous
multi-office service is not double-counted.

```text
f(d; tau) = 1 - exp(-d/tau)
w_co_lower = f(G, 365.2425)
w_co_upper = f(P, 365.2425)
```

The one-year scale is a declared prior and must be swept at half and double. The current
graph can receive only the conservative lower bound after the sidecar passes.

## Revolving-door rules

Qualified paths require accepted person identity, dated/corroborated Hill employment,
accepted member/container resolution, a later dated industry episode or LDA activity, an
accepted employer-to-registrant crosswalk for employer claims, and guaranteed ordering.

Keep these predicates distinct:

```text
FORMER_STAFFER_EMPLOYED_BY_REGISTRANT
FORMER_STAFFER_NAMED_ON_ACTIVITY_FOR_CLIENT
```

For Hill episode `h` and industry episode/event `z`:

```text
guaranteed order: end_latest(h) <= start_earliest(z)
possible order:   end_earliest(h) <= start_latest(z)
gap_min = max(0, start_earliest(z) - end_latest(h))
gap_max = max(0, start_latest(z) - end_earliest(h))
```

For each `(person, member, organization, organization_role)`, retain only the closest
qualified Hill exit before the earliest supported industry event. Repeated filings add
support, never another person contribution. Primary member-organization weight is the
auditable unique-person count `N`. Gap-decayed sums are sensitivity features only:

```text
q_lower = 2^(-gap_max/H)
q_upper = 2^(-gap_min/H)
R_lower = sum(unique-person q_lower)
R_upper = sum(unique-person q_upper)
```

No output may claim lobbying contact, causation, or influence. A client activity edge is not
client employment. If only a filing post date exists, label the gap as an observation gap.

## Gordon Holzberg golden fixture

LDA person `lda:lobbyist:147664` lists Alma Adams and Emilia Sykes roles. LegiStorm profile
267918 identifies America's Credit Unions from Aug. 2024 and public salary periods expose
Hill service through 2024-01-02. Expected normalized episodes include Sykes
`[2023-01-03, 2024-01-03)` and an industry start with bounds
`[2024-08-01, 2024-08-31]`, giving a 211-241 day start-gap interval. A registrant edge still
requires an accepted organization crosswalk and supporting LDA activity.

## Required receipt conservation

Review whether the following partitions are complete and disjoint and propose corrections:

```text
lookup_cohort = found + not_found + ambiguous + access_blocked
identity_candidates = accepted + rejected + ambiguous + review_required + superseded
employment_rows_observed = emitted + exact_duplicates + invalid_dates + unresolved_person
                           + unresolved_container + excluded_nonemployment
co_tenure_candidate_keys = guaranteed_edges + possible_only + zero_overlap
                           + identity_blocked + interval_blocked
revolving_candidate_keys = emitted_paths + possible_order_only + wrong_order
                           + identity_blocked + org_blocked + missing_corroboration
```

The receipt must also prove no undated temporal weights, no unresolved identities in primary
edges, no self-loops, deterministic output under input permutation, unique support IDs and
digests, and no structural-v6 changes while disabled.

## Review questions

1. Are the schemas sufficient to prevent search snippets, name equality, LDA filing dates,
   and covered-position prose from becoming dated facts?
2. Are interval bounds and gap formulas correct for half-open uncertain intervals?
3. Are co-tenure and revolving-door weights auditable, bounded where appropriate, and free
   of duplicate-row/person inflation?
4. Are the conservation partitions exhaustive and disjoint?
5. What must change before implementation can receive PASS?
