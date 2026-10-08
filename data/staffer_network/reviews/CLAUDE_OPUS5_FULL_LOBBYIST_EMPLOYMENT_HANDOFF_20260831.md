# Claude Opus 5 handoff — full LDA lobbyist employment-history enrichment

Date: 2026-08-31  
Repository: `C:\Users\pgoff\OneDrive\Desktop\Melange Systems`  
Meta LOOP run: `run-20260831T0243340126420Z-4fda60e57a`  
Required review model: `claude-opus-5`, effort `max`; do not substitute Sonnet.

## Outcome already achieved

The complete local LDA lobbyist universe is materialized as a deterministic, restricted
employment-history lookup queue:

```text
C:\Users\pgoff\AppData\Local\Melange\staffer_network\employment-lookup\generation-20260831T050000Z
  employment_lookup_queue.ndjson.gz
  employment_lookup_receipt.json
```

The receipt is `PASS` and records:

| Cohort | People | Meaning |
|---|---:|---|
| Full LDA person universe | 25,340 | One unique queue row per `lda_source_person_id` |
| P0 | 6,527 | Covered-position text with an unadjudicated government-term lexical hit |
| P1 | 2,957 | Other non-empty covered-position text |
| P2 | 15,856 | No covered-position text in the sealed 2021–2026 source window |
| Any covered-position text | 9,484 | P0 + P1 |
| Four-digit year token in position text | 2,166 | Text feature only, not an accepted date |
| Month token in position text | 597 | Text feature only, not an accepted date |

Queue SHA-256:

```text
5e240a91a21e237525547eef84456daee7dd5339723073ced9437a9f5ea5f649
```

The queue asserts zero identity matches and zero canonical merges. Every record has
`identity_status=REVIEW_REQUIRED` and carries three discovery queries. The full test result
before Opus review was `113 passed, 65 subtests passed`.

## Source of truth already on disk

Do not re-download LDA. Use this sealed source-native generation:

```text
C:\Users\pgoff\AppData\Local\Melange\staffer_network\normalized\lda-source-native\generation-20260830T231200Z
```

It contains:

| Artifact | Rows |
|---|---:|
| Lobbyist assertions | 25,340 |
| Covered-position assertions | 748,589 |
| Activities | 1,037,547 |
| Organizations | 54,073 = 7,077 registrants + 46,996 clients |
| Industry edges | 4,816,559 |

There are 21,511 unique `(source_person_id, covered_position)` pairs and 19,149 unique
position strings. All 383,705 covered-position activity IDs resolve to activity assertions;
none lacks a registrant or client ID. Those joins describe a lobbying activity, not the
lobbyist's former employer.

Use these source-native joins:

```text
covered_position.source_activity_id
  -> activity.source_activity_id
  -> activity.registrant_source_org_id / client_source_org_id
  -> organization.source_org_id

lobbyist --NAMED_ON_ACTIVITY--> activity
activity --FILED_BY--> registrant
activity --FOR_CLIENT--> client
```

Never infer that a registrant/client named on an activity was the lobbyist's former Hill
employer.

## Immediate objective

For every queue person, obtain the complete facts needed by the temporal layer:

1. every identifiable employment episode, with employer/office, title, and
   evidence-bounded start and end dates; and
2. every identifiable education episode, with institution, degree/field when
   stated, and attendance start/end dates or class year.

The LDA `covered_position` field is a lookup seed and former-covered-office corroboration.
Under current LDA guidance it is not a complete career history, does not list the lobbyist's
current private-sector role, and does not require episode start/end dates. Filing
`dt_posted` is never an employment date.

## Binding complete-history gate

Profile discovery, a current-employer heading, a list of former positions without
dates, or one education institution without attendance dates is **not** a completed
record. These are useful partial observations only.

A person may be labeled `COMPLETE` only when all of the following hold:

1. every emitted employment episode has a non-empty employer, title, start bound,
   end bound (or an explicitly current interval), and episode-level source URL;
2. every emitted education episode has an institution, attendance interval or
   class year, and episode-level source URL;
3. the search record explicitly attests that employment and education coverage are
   exhaustive for the available evidence universe;
4. `unresolved_gaps` is an empty list; and
5. an adjudicator records `adjudication_status=PASS`.

Missing degree/field values must remain null rather than inferred, but the missing
field must be notated. Any unresolved chronology, inaccessible history section,
unknown employer/title/date, or education date gap forces `PARTIAL`/`INCOMPLETE`.

The executable gate is:

```text
python -m fec.staffer_network.employment_history audit-completeness \
  --records <one-or-more-enrichment.ndjson> \
  --output-root <empty-audit-directory>
```

## Collection order

1. Process all 25,340 people; use P0, then P1, then P2 only as scheduling priority.
2. Preserve `lda_source_person_id` as the task authority. Same-name LDA IDs remain separate.
3. Search exact name variants to discover a LegiStorm profile/person ID:

   ```text
   site:legistorm.com/person/bio/ "{FULL NAME}"
   site:legistorm.com/person/ "{FULL NAME}" "Congressional Staffer"
   "{FULL NAME}" "Employment History" Congress
   ```

4. Search snippets are URL leads only. Open the direct result before recording evidence.
5. Prefer the original House/Senate payroll or other official employment record for
   canonical dates. A direct LegiStorm profile, salary, member, or office page is strong
   secondary evidence and an identity lead.
   Apply an asymmetric corroboration gate: a direct LegiStorm page may support a
   `HIGH_REVIEW_CANDIDATE` when the person identifier and career clues agree with the LDA
   record. A non-LegiStorm result needs either (a) two independent corroborating sources,
   or (b) one authoritative primary employment/payroll record plus matching LDA evidence.
   A single non-LegiStorm biography, employer page, news item, or search snippet remains
   `REVIEW_REQUIRED` and cannot supply a primary temporal episode by itself.
6. Record `FOUND`, `NOT_FOUND`, `AMBIGUOUS`, or `ACCESS_BLOCKED`; never drop a queue row.
7. Checkpoint by `candidate_id`; output must be restartable and idempotent.

LegiStorm's published terms prohibit automated collection, and even a manual process used
to copy the site at scale, without prior written permission. Do not treat permission for
Politico Pro as permission for LegiStorm. Use LegiStorm in bulk only with a license/export/
API or written authorization. Otherwise use it for bounded discovery/review and obtain
canonical dates from official House/Senate payroll sources. Do not bypass subscriber-only
tables or challenges.

References:

- LDA guidance: <https://lobbyingdisclosure.house.gov/ldaguidance.pdf>
- LegiStorm terms: <https://www.legistorm.com/index/legal.html>
- LDA API terms: <https://lda.gov/api/tos/>

## Evidence model

Keep source observations separate from adjudication and derived episodes. An employment
observation should carry:

```text
observation_id
source_system_id
source_person_id
source_locator
source_record_digest
retrieved_at
source_as_of
raw_person_name
raw_employer
raw_title
raw_start
raw_end
source_end_semantics       # inclusive | exclusive | unknown
start_earliest
start_latest
end_earliest
end_latest                 # normalized half-open day boundaries
start_precision            # day | month | year | unknown
end_precision
asserted_current
member_bioguide_id?
member_office_term_id?
lda_registrant_id?
lda_client_id?
external_org_id?
```

Person identity and employer/container resolution are independent decisions:

```text
REVIEW_REQUIRED | ACCEPTED | REJECTED | AMBIGUOUS | SUPERSEDED
```

Each decision needs `decision_id`, reviewer kind/ID, decision time, rationale code(s),
evidence IDs, and optional supersession. Only active `ACCEPTED` person and container
decisions can enter primary temporal outputs. A LegiStorm page found by exact name is not an
automatic match. An employer name is not an LDA registrant crosswalk until separately
accepted. Registrant and client roles stay distinct even when IDs refer to related entities.

The implemented episode schema is:

```text
fec/staffer_network/schemas/employment_episode.schema.json
```

The implemented lookup and temporal code is:

```text
fec/staffer_network/employment_history.py
```

## Interval normalization

All internal intervals are `[start, end)` at day granularity.

| Source value | Normalized bounds |
|---|---|
| Exact start `D` | `start_earliest = start_latest = D` |
| Worked through inclusive day `D` | `end_earliest = end_latest = D + 1 day` |
| Month start `YYYY-MM` | first through last day of that month |
| Year start `YYYY` | January 1 through December 31 |
| Current/open | right-censor at the source/build as-of boundary; never extrapolate past source as-of |
| Unknown/unbounded | retain as structural-only; exclude from temporal weight |

For episode `e`:

```text
guaranteed_core(e)   = [start_latest(e), end_earliest(e))
possible_envelope(e) = [start_earliest(e), end_latest(e))
```

Union cores and envelopes independently by `(person, normalized_container)` before
intersection. Convert inclusive salary end dates before union. Join touching intervals;
never bridge a positive evidence gap merely because a quarterly record is missing.

## Co-tenure math

```text
U-(p,c) = union of guaranteed cores for person p in container c
U+(p,c) = union of possible envelopes for person p in container c

G(p,q,c) = days(U-(p,c) intersect U-(q,c))
P(p,q,c) = days(U+(p,c) intersect U+(q,c))
0 <= G <= P
```

Primary co-tenure requires `G > 0`. `G = 0 < P` is `POSSIBLE_ONLY` with primary weight
zero. Union shared calendars across containers before the graph-level duration to avoid
double-counting simultaneous assignments.

```text
f(d; tau) = 1 - exp(-d/tau)
w_co_lower = f(G, 365.2425)
w_co_upper = f(P, 365.2425)
```

Keep raw `G`, `P`, and per-container paths. The one-year `tau` is a declared prior; report
sensitivity at half and double. Only `w_co_lower` may later enter the primary graph.

## Revolving-door math

Keep separate predicates:

```text
FORMER_STAFFER_EMPLOYED_BY_REGISTRANT
FORMER_STAFFER_NAMED_ON_ACTIVITY_FOR_CLIENT
```

The client predicate means only that the accepted person was named on a dated activity for
the client. It does not assert client employment, member contact, causation, or influence.

For Hill episode `h` and later industry episode/event `z`:

```text
guaranteed order: end_latest(h) <= start_earliest(z)
possible order:   end_earliest(h) <= start_latest(z)

gap_min = max(0, start_earliest(z) - end_latest(h))
gap_max = max(0, start_latest(z)   - end_earliest(h))
```

For each `(person, member, organization, organization_role)`, retain only the closest
qualified Hill exit before the earliest supported industry event. Repeated filings add
support, never another person contribution.

Primary member-organization weight is the auditable unique-person count:

```text
N(m,o,r) = number of unique accepted people with a qualified path
```

Gap-decayed values are sensitivity features, not influence scores:

```text
q_lower(p; H) = 2^(-gap_max/H)
q_upper(p; H) = 2^(-gap_min/H)
R_lower = sum over unique p of q_lower
R_upper = sum over unique p of q_upper
```

Use `N` as primary `raw_weight`. Report one-, two-, and five-year half-life sensitivities.
If only LDA `dt_posted` exists, call the result an `observation_gap`, never a transition gap.

## Gordon Holzberg golden fixture

```text
LDA person: lda:lobbyist:147664
LegiStorm profile: 267918
Hill covered positions: Alma Adams, then Emilia Sykes
Industry biography: America's Credit Unions, Aug. 2024-
```

Expected normalized Sykes episode:

```text
[2023-01-03, 2024-01-03)
```

Expected month-precision industry start bounds:

```text
2024-08-01 through 2024-08-31
```

Expected start-gap bounds:

```text
211-241 days
```

A registrant-employment edge still requires an accepted America's Credit Unions → LDA
registrant crosswalk and supporting evidence. Client paths require the actual dated LDA
activity. Direct profile: <https://www.legistorm.com/person/bio/267918/Gordon_E_Holzberg.html>

## Required conservation and gates

```text
lookup_cohort = found + not_found + ambiguous + access_blocked

identity_candidates = accepted + rejected + ambiguous + review_required + superseded

employment_rows_observed = emitted + exact_duplicates + invalid_dates
                         + unresolved_person + unresolved_container
                         + excluded_nonemployment

co_tenure_candidate_keys = guaranteed_edges + possible_only + zero_overlap
                         + identity_blocked + interval_blocked

revolving_candidate_keys = emitted_paths + possible_order_only + wrong_order
                         + identity_blocked + organization_blocked
                         + missing_corroboration
```

Every receipt must bind every input/output by role, path, bytes, row count, and SHA-256 and
record formula versions, source windows, build `as_of`, parameter values, support-reference
counts, duplicate collapses, and unique-person contributions. `PASS` additionally requires:

- zero unresolved identities or containers in primary edges;
- zero undated episodes in temporal weights;
- zero self-loops;
- no client/employer predicate swaps;
- deterministic output under input permutation;
- exact support digests over sorted unique evidence IDs;
- the structural canonical/graph v6 artifacts remain byte-identical while the temporal
  sidecar is disabled;
- no automated LegiStorm collection without the required authorization;
- no influence, access, contact, or causal language.

## Commands

Rebuild the full lookup queue into a new empty immutable generation:

```powershell
python -m fec.staffer_network.employment_history build-lookup `
  --lda-corpus-root 'C:\Users\pgoff\AppData\Local\Melange\staffer_network\normalized\lda-source-native\generation-20260830T231200Z' `
  --output-root '<NEW_EMPTY_LOCAL_GENERATION>' `
  --generated-at '<PINNED_UTC_TIMESTAMP>'
```

Run the staffer suite:

```powershell
python -m pytest -q fec/tests/staffer_network
```

Do not promote temporal outputs to canonical/graph v6 until the evidence corpus is
populated, the receipt passes, Opus 5 max returns final adversarial `PASS`, and the Meta LOOP
terminal receipt is verified.
