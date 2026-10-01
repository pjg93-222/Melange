# Staffer Network Expansion Design

**Version:** 6.2 structural implementation plus verified employment-adjudication overlay  
**Date:** 2026-08-30  
**Latest adjudication:** 2026-09-01 UTC  
**Status:** Canonical structural plane and deterministic employment-adjudication quarantine are implemented; provisional employment facts remain noncanonical and non-temporal; promotion awaits human gold, container, and Senate-observation gates  
**Supersedes:** `STAFFER_NETWORK_EXPANSION_DESIGN_20260829.md` v3.0

## 0A.0 Implemented adjudication boundary (2026-09-01)

The implementation now has an immutable decision plane, normalized provisional
episode plane, exact person summaries, content-bound calibration samples,
deterministic twin generation, and a self-bound independent verification
receipt. Decision, episode, evidence, schema, generator, verifier, source-file,
and sealed-queue relationships are independently replayed. Exact duplicate
facts consolidate support rather than multiplying graph weight.

Canonical completeness is separately fail-closed. A purported canonical episode
must pass schema and semantic validation and resolve byte-for-byte through a
hash-bound canonical checkpoint. The verifier enforces exact LDA-person binding,
the complete episode set for that person, all observations for every employment
key, latest-observation consistency, active identity/container decisions,
supersession integrity, source transforms, and receipt summaries. Provisional
rows cannot enter canonical facts, lifetime-complete histories, or primary
temporal weights.

The current overlay contains 4,996 provisional facts for 1,186 of 25,340 people.
All 4,996 remain container-review required; 57 retain within-year ordering
ambiguity, and 39 Senate observations use the weaker report-period-only basis.
The external Opus review was waived by the user to expedite closure and is not
represented as passed. Implementation may proceed on the review queues, but
canonical promotion remains prohibited until the four substantive gates pass.

## 0A. Employment and temporal adjudication addendum (2026-09-01 UTC)

This addendum is the current authority for employment acquisition, review-
candidate coverage, temporal-code readiness, and phase state. The dated
sections below remain the provenance record for the 2026-08-30/31 structural
build. Where their pre-build statements say that payroll, graph, or the loader
is unbuilt or disabled, this addendum supersedes those statements without
rewriting their historical evidence.

### 0A.1 Current boundary and measured coverage

The sealed employment scope is exactly **25,340 LDA source identities**. The
immutable A9 sidecar, which adds verified A8 review evidence without rewriting
the A4/A5b baselines, reports:

| Measure | People |
|---|---:|
| any employment candidate | 13,697 |
| no employment candidate | 11,643 |
| dated former-position candidate missing | 16,486 |
| bounded employment-interval candidate missing | 18,227 |

The mutually exclusive scheduling partition is:

| Bucket | People | Meaning |
|---|---:|---|
| `P0_NO_EMPLOYMENT_CANDIDATE` | 11,643 | acquire a defensible employment candidate |
| `P1_DATED_FORMER_POSITION_MISSING` | 4,843 | obtain a source-supported former-position date |
| `P2_BOUNDED_INTERVAL_MISSING` | 1,741 | obtain defensible interval bounds |
| `P3_IDENTITY_AND_CHRONOLOGY_ADJUDICATION` | 7,113 | adjudicate identity, container, dates, and chronology gaps |

These are candidate and scheduling counts, not accepted identities, canonical
employment facts, or complete careers. All **25,340** people still lack a
complete-lifetime employment attestation. Canonical employment promotions are
exactly **zero**.

### 0A.2 A7–A9 and House backfile disposition

- **A7 machine-local inventory:** independent `PASS`. Official Senate LD-203
  holdings emit **143,513** dated registrant-affiliation candidates for
  **22,754** people; these are professional affiliations, not employment-tenure
  assertions. A conservative three-anchor FEC rule emits **979** dated self-
  reported employer point observations for **37** people. FEC point evidence is
  contextual and causes no priority-bucket move. Neither A7 lane promotes a
  fact.
- **A8 recovered House evidence:** independent `PASS` for a review-only match
  ledger of **453** candidate rows covering **388** LDA people from recovered
  1997Q1 Part 2 observations. Exact-name compatibility is discovery evidence,
  not identity proof.
- **A9 immutable scheduling sidecar:** independent `PASS` over the exact
  25,340-person scope. A8 moves **209** people to P3—77 from P0, 89 from P1,
  and 43 from P2; 179 A8 people were already P3. A7 LD-203 is prohibited as an
  employment input and A7 FEC points move no bucket. A4 and A5b remain
  immutable.
- **A5c House pre-web acquisition:** remains
  `BLOCKED_PARTIAL_RECOVERY`. Exactly one report part, 1997Q1 Part 2, was
  recovered from the 52-quarter 1996Q1–2008Q4 target. The other 51 quarters are
  not claimed covered.

Receipt pins are A7 verifier
`7c8402784db9861c928bd4045ac7792022d96a92d18bf7e9d91bf38d3590d969`,
A8 verifier
`e05c9e31b32229b116ec91c043950ec84321ff5e3d88a9cc77cdb6038bd5e87d`,
and A9 verifier
`0b1dca553a254c686bee197d172e0d35ce1a86eb27a3ddf2c2bf7c4960423429`.

### 0A.3 Temporal math and external review

M1 is **`PASS` after one fail-closed temporal fix**. A valid-schema pair with
an unknown necessary ordering bound previously reached an empty `min()` in the
revolving selector. The repaired path is explicitly `INTERVAL_BLOCKED`, retains
null gap bounds and zero primary/possible weights, emits no revolving edge, and
is conserved in the temporal receipt. M1 introduced no identity merge,
canonical promotion, temporal edge, or composite influence score.

Claude Opus 5 returned:

- **structural math: `PASS`**, confined to the implemented structural graph;
- **interval/co-tenure math: `PASS`**, confined to normalization, union,
  intersection, guaranteed/possible bounds, and the duration transform;
- **revolving-door math: `PASS`**, confined to ordered Hill-to-industry
  transition math and its fail-closed validation path.
- **consolidation receipt semantics: `PASS`**, confined to the final receipt
  validator's conservation identities and reviewed forgery paths.

The revolving review is
`data/staffer_network/reviews/OPUS5_REVOLVING_DOOR_MICROREVIEW_20260901.md`
(SHA-256
`58db6b2e3ca1b4d7cc03131407d358521655ba5538c6d3e236e5a4425625c01f`).
Its eight nonblocking validation, observability, test, provenance, and field-
semantics findings remain the compact hardening backlog in
`STAFFER_NETWORK_MATH_ADJUDICATION_20260831.md` §7.1; in particular,
`possible_weight` is an upper gap-decay factor, and publication validation does
not yet independently enforce ordered edge-decay bounds.

The final receipt review is
`data/staffer_network/reviews/OPUS5_CONSOLIDATION_RECEIPT_FINAL_REVIEW_20260901.md`
(SHA-256
`eb9f118cb4f5e9ff3db65fbce753b85e58fb9415f1b874857d75d8429b7559ba`).
It is a scoped receipt-safety `PASS`, not an end-to-end employment-gate or
corpus-completeness attestation. Its seven nonblocking hardening findings do
not authorize canonical promotion or temporal publication.

The interval, revolving, and receipt reviews expressly do not open review-
candidate identities or incomplete histories for temporal scoring. The
measured local evidence is **48 focused tests and 222 staffer-network tests plus
73 subtests**, all passing. Those are code regression results, not proof that
the actual 25,340-person corpus contains complete-lifetime histories. The data
and production gates remain closed, and the Meta LOOP disposition is
`BLOCKED`.

### 0A.4 Implementation and phase state

The framework and code path are implemented for evidence observations,
candidate scheduling, employment-episode validation, completeness auditing,
consolidation, uncertain half-open intervals, co-tenure, revolving paths,
receipt validation, and guarded publication. The final receipt-semantic review
passes within its declared scope. Production data readiness remains blocked by
unadjudicated identities/containers, incomplete chronologies, the partial House
backfile, and the absence of complete-lifetime attestations; Meta LOOP closure
is therefore `BLOCKED`.

Current phase rulings:

| Phase | 2026-09-01 ruling |
|---|---|
| 2 public payroll/employment acquisition | partial: House 2009Q3–2015Q4 and Senate 2011–2026 candidate lanes pass; A5c pre-web breadth is `BLOCKED_PARTIAL_RECOVERY` |
| 4 identity/episode resolution | review queues implemented; no canonical employment promotion; all 25,340 histories incomplete |
| 5 graph | structural graph `PASS`; M1, interval/co-tenure, revolving-door, and consolidation-receipt reviews `PASS` within their scopes; canonical temporal production remains blocked by incomplete/unadjudicated data |
| 6 analysis loader | `PASS` for explicit immutable structural generation loading; default remains `off` |
| 7 consumers/publication | closed pending claim-specific and source-governance approval |

The existing five-source v6 canonical generation and structural graph remain
the only internally enabled canonical/analysis plane. A7, A8, A9, employment
candidate ledgers, completeness audits, and any future temporal sidecar are
noncanonical until a new immutable generation passes every identity, evidence,
receipt, and terminal-review gate.

## 0. Implementation closure revision (2026-08-31 UTC)

This section is the current implementation authority. Sections 1 onward retain
the pre-build design and evidence history; where they describe canonical facts,
analysis, LittleSis, or Politico as disabled, this section supersedes them.

The implemented hierarchy is a typed multiplex rather than a single untyped
social graph:

```text
legislator -> supported staff/office tie -> staffer or former staffer
staffer/former staffer --review-candidate identity bridge--> LDA lobbyist
LDA lobbyist -> filing activity -> registrant and client organization
```

The canonical generation contains 1,585,038 singleton entities and 6,050,221
support-backed facts. Each source entity receives one deterministic canonical
identifier. Cross-source memberships and entity merges are exactly zero. The
6,978 exact-name identity rows remain reversible links; 2,519 meet strict
one-to-one multiplicity conditions but are still not canonical identity facts.

The corrected generation excludes and receipts 44 source self-loops (43
LittleSis `POSITION_AT`, one `LOBBIED_FOR`). The source assertions remain in the
source-native plane; invalid self-loops never enter canonical facts or graph
traversal.

Canonical v6 also minimizes contact text: 549 public legislator-term contact
occurrences are removed in each of the entity and term-fact planes, five Senate
LDA entity contact values are removed, and 68 blank covered-position literals
are excluded and counted separately. Contact-only fact exclusions are zero.

### 0.1 Edge and connectedness mathematics

Direct canonical support has structural weight `1`. Repeated rows are not
allowed to manufacture extra weight. For node `i`, active layer `l`, and
neighbor `j`, traversal is

```text
P[i,j,l] = (1 / |L_i|) * w[i,j,l] / sum_k w[i,k,l]
P[i,j]   = sum_l P[i,j,l]
```

where `L_i` is the set of layers active at `i`. This makes each active layer
receive equal transition mass before within-layer proportional allocation. It
does not assert that employment, education, lobbying, and filing participation
have comparable causal effect. Traversal is bidirectional for connectedness;
the source fact retains its directedness and no causal reversal is inferred.

Primary connectedness is PageRank

```text
r = alpha * P.T * r + alpha * dangling(r) * v + (1 - alpha) * v
```

with teleport vector `v` allocating equal mass to each represented entity kind
and then uniformly within kind. The primary value uses `alpha=0.85`; sensitivity
runs at `0.70` and `0.95` must converge. Primary scores exclude every identity
candidate. A separately named exploratory score adds only the 2,519 strict
one-to-one review candidates. Equal mass per active layer is a modeling prior:
a node with one employment layer and one education layer sends half its walk
mass through each. Likewise, entity-kind-balanced teleport shapes cross-kind
scores. An isolate receives positive teleport-only PageRank, so every score row
now carries `primary_isolate` and `exploratory_isolate`; isolate rows must be
excluded from any connectedness ranking.

Eigenvector centrality is diagnostic only. It is computed independently per
connected component on `(P + P.T)/2`, L1-normalized within that component.
Isolates are zero. Components that do not meet the fixed convergence tolerance
are null rather than approximate; four components covering 585 nodes are null
in this build. L1 normalization makes values incomparable across components, so
global ranking is prohibited; this is a degree-normalized component diagnostic,
not standard Bonacich eigenvector centrality. A chronological transition DAG
must not use eigenvector centrality because its eigenvalues are zero.

Bridging is the normalized Simpson diversity of row-normalized tie mass across
neighbor entity kinds:

```text
B_i = (1 - sum_g p[i,g]^2) / (1 - 1/G)
```

It is computed on layer-balanced walk mass and reported separately from total
strength. Feasible neighbor kinds differ by entity kind, so bridging values are
not directly comparable across kinds. No composite influence score is emitted
because summing strength, eigenvector centrality, PageRank, and bridging would
double-count connectivity and mix incompatible scales.

### 0.2 Source activation and consumption

LittleSis `frozen` now means byte-pinned input vintage, not disabled compute.
LittleSis, Senate LDA, Politico Pro, the contact-free legacy seed, and the
legislator reference are all `ENABLED_INTERNAL_ANALYSIS` in the canonical
receipt. Politico is enabled by the v3 manifest and contributes normalized
people, roles, issues, and supported member-role links. This activation does
not turn contact data into an analytical field, make an identity candidate a
merge, or claim permission to redistribute raw source rows publicly.

`STAFF_NET=analysis` is implemented. The loader requires an explicit immutable
generation root, a PASS receipt, exact artifact roles, byte counts, and SHA-256
matches. Default `STAFF_NET=off` still performs no filesystem read.

### 0.3 Adjudication of the attached proposed temporal math

Section 6 of the attached 2026-08-29 design is evidence for a future temporal
co-tenure model, not the formula used by the structural graph above.

| Proposed formula | Ruling | Required repair before implementation |
|---|---|---|
| `O_min` interval overlap | Keep concept | Define half-open date bounds, day-count/year conversion, leap-year behavior, open/right-censored episodes, and `O_mid`; union overlapping episodes per person/container before pairwise overlap; report that conservative overlap also measures date coverage when undatedness is high |
| `w_work` | Revise | Summing every episode pair double-counts split or overlapping episodes; operate on unioned intervals and deduplicated source support; use a bounded or concave duration transform so long tenure cannot dominate the layer |
| container `kappa` table | Pilot only | Values are unvalidated construct choices; preserve raw sublayers and run parameter/rank sensitivity rather than treating ±50% as validation |
| `w_x` member coupling | Reject/remove | It imports the legislator network into the staff graph and is circular for studies relating staff and member-network structure; global-max normalization adds outlier/corpus dependence |
| `w_edu` | Revise/pilot | Deduplicate repeated school episodes; define campus/entity resolution; keep education as a separate non-contact layer; prevent multiplicative tier terms from being interpreted causally |
| `w_sup` | Default off | Use `max(0, min(rank_i-rank_j,2)/2)` mathematically, but title rank does not prove direct supervision; if enabled, preserve it as a separate directed layer because undirected traversal destroys the hierarchy |
| `W_staff` overlay | Revise | Define sequential versus concurrent service, interval union, committee mediation, and historic-member denominators explicitly; require an office-size/tenure-preserving null model before interpretation |
| `W_rev(m,f)` | Block as written | The right side must restrict each person to firm `f`; require measured identity precision, Hill exit before lobbying start, transition-gap bounds, and an actual registrant/employer fact rather than covered-position text alone |
| `0.60/0.15/0.25` composite | Reject | Global-max-scaled arbitrary coefficients mix units, drift with corpus growth, and double-count connectivity; raw sublayers plus the layer-balanced operator replace it |

The current corpus still cannot safely run duration math: every LittleSis
temporal weight is zero, Politico is a snapshot rather than an employment
history, and the LDA identity bridges are review candidates. Canonical v6
corrects all 11,758 undated Politico member-role links from temporal weight 1 to
0, and the builder now aborts if any `undated-only` fact has a nonzero temporal
weight. The receipt's zero is the result of this fail-closed rule, not an
independently estimated readiness statistic. Temporal weights may be added only
after source-specific dated episode evidence and interval tests pass. This
closes the data-invariant defect without pretending the missing temporal
evidence exists. Filing dates on LDA participation facts are not dated
employment episodes and cannot support co-tenure or revolving-door timing.

> **2026-09-01 adjudication:** the temporal implementation now passes M1 after
> the fail-closed `INTERVAL_BLOCKED` repair, and the interval/co-tenure math has
> an independent Opus `PASS`. Revolving-door math and its fail-closed validation
> path also have an independent Opus `PASS`, subject to the eight nonblocking
> hardening findings in the math adjudication. This is code readiness only.
> Review-candidate employment data remains barred from canonical temporal
> production. The consolidation-receipt review also passes within receipt-
> semantic scope; it does not alter the closed data/production gate or the
> `BLOCKED` Meta LOOP disposition.

## 1. Decision summary

Paul's hierarchy is retained as the user-facing model, with one structural
revision: legislators are represented by effective-dated terms and offices,
not as parents that own staffer identity.

```text
legislator person + term
          |
          v
member office / committee container
          ^
          |
source-supported employment assertion
          |
staff/current/former/lobbyist person role
          |
          v
organization / registrant / client / school / LDA activity
          |
          v
industry and policy-domain assertions
```

This preserves the intended three analytical levels:

1. legislators and their effective-dated institutional containers;
2. staffers/former staffers and their supported relationships to offices and
   one another;
3. industry actors and filed/source-supported relationships to those persons.

The durable implementation is an evidence graph first and a social graph only
after identity, temporal, and claim gates pass.

## 2. Current implementation boundary

The 2026-08-30 P2 local generation contains:

- 443,140 source-native LittleSis entities;
- 424,323 source-native LittleSis Position, Education, and true Lobbying
  assertions;
- 1,456,165 accepted LittleSis relationships explicitly dispositioned outside
  the P2 category scope;
- 5,773 contact-free restricted legacy staff records covering 533 offices.

All 873,236 P2 records passed complete schema and semantic validation. A
separate passed LDA generation contains 6,682,108 independently validated rows:
25,340 lobbyists, 54,073 registrant/client organizations, 1,037,547 activities,
4,816,559 filing-participation edges, and 748,589 covered-position assertions,
derived from 541,659 reconciled filings through cutoff-exclusive 2026-08-30.
The two conservation totals are not added together as one generation.

There are zero cross-source identity assertions and canonical merges. A separate
6,978-row exact-name candidate artifact is restricted, review-required, and
confidence-null. Politico, payroll, and the normalized historic member spine
remain separate gated planes and are not silently joined.

This boundary is intentional. It makes the corpus useful for candidate
generation, parser work, mapping design, and resolution evaluation without
prematurely asserting who is the same person or who influenced whom.

> **2026-09-01 employment-plane update:** A7 inventories 143,513 LD-203
> affiliation candidates for 22,754 people and 979 FEC employer-point
> observations for 37 people; A8 contributes 453 House review matches covering
> 388 people; and A9 moves 209 people into P3. Across the fixed 25,340-person
> scope, 13,697 have at least one candidate and 11,643 have none, but all
> 25,340 still lack complete-lifetime employment attestation and canonical
> employment promotions remain zero. These review and scheduling artifacts do
> not alter the canonical v6 generation.

## 3. Non-claims and invariants

The initial system never infers:

- direct personal contact from co-employment, common education, LittleSis, or
  an LDA filing;
- supervision from title rank or reporting proximity;
- continuous employment from payroll payments;
- departure dates from LDA covered-position text;
- current employment from an old `is_current` source field;
- influence, access, friendship, or ideology from structural proximity;
- historical committee membership from a current-membership snapshot;
- canonical identity from an exact-name match.

Required invariants:

1. Raw bytes, source-native assertions, resolution decisions, canonical facts,
   and graph edges remain separate planes.
2. Every accepted record is emitted or explicitly dispositioned.
3. Person identity is source-namespaced until a reversible resolution decision.
4. Current staffer, former staffer, lobbyist, and legislator are temporal roles
   of a person; they are not mutually exclusive permanent node classes.
5. Registrants and clients retain distinct namespaces.
6. Raw/coarse dates stay literal. Precision may degrade, never sharpen.
7. Undated-only evidence receives temporal weight zero.
8. PII and restricted text stay outside repository artifacts.
9. No source, analysis loader, or consumer arms from corpus existence alone.
10. Existing legislator network/workbook/config families remain unchanged.

## 4. Entity and container model

| Kind | Stable identifier policy | Notes |
|---|---|---|
| `person` | opaque canonical ID after resolution | Roles are effective-dated facts |
| `source_person` | `(source_system_id, source_entity_id)` | Never globally meaningful |
| `legislator_term` | Bioguide + chamber/congress/service bounds | Anchors office validity |
| `member_office` | member/term-aware container | Distinct from the legislator person |
| `committee` / `subcommittee` | chamber + committee code + effective dates | Party side/role nullable |
| `organization` | source-native then canonical xref | No registrant/client conflation |
| `lda_activity` | filing/version + activity ID | Connects lobbyist, registrant, client, issues |
| `institution` / `program` | source-native then UNITID/CIP when supported | Education is affiliation/affinity |

Observed predicates include source employment, position, education, lobbying,
payroll observation, LDA lobbyist/activity/registrant/client links, and source
identifier assertions. Derived predicates such as co-tenure, sequential office
service, staff-to-lobbying transitions, and member overlays are built only from
admissible canonical facts with explicit support.

## 5. Data planes

```text
immutable source bytes
        |
        v
source manifests + raw record locators
        |
        v
source-native entities and assertions
        |
        +--> reject/disposition ledger
        |
        v
candidate generation + append-only adjudication
        |
        v
canonical entities/facts with fact support
        |
        v
typed graph layers + claim-specific evaluation
```

### 5.1 Raw/provenance plane

Each snapshot records authority scope, terms/license vintage, redistribution
class, query/inventory, collected/source times, parser/collector versions,
file bytes/hashes, counts, reject reasons, freshness, and a manifest hash.

### 5.2 Source-native plane

Identifiers remain namespaced. LittleSis source entities use
`littlesis:entity:<id>` and relationships use
`littlesis:relationship:<id>`. The restricted legacy record file remains
byte-identical to its P1 seed and carries `source_system_id` per record.

### 5.3 Resolution plane

Candidate generation does not mutate canonical identity. Decisions are
append-only and retain reviewer, method/version, evidence references, outcome,
confidence only when calibrated, valid/system time, and supersession/reversal.

### 5.4 Canonical fact plane

Facts are support-backed and bitemporal. Conflicting source assertions coexist;
consolidation is a versioned derivation, not destructive truth replacement.

### 5.5 Graph plane

Every layer is typed and independently reproducible. No default composite ships.
Raw layer weights remain available; any future scaling uses a frozen reference
vintage and claim-specific sensitivity packet, not per-build global maxima.

## 6. Implemented source-native corpus

### 6.1 LittleSis

The locally frozen pair is observationally paired, not publisher-declared as one
release vintage:

- entities gzip: 76,691,985 bytes, SHA-256 `5cc0039a…cd29d3c`;
- relationships gzip: 110,381,587 bytes, `c11d7058…38d489`;
- 443,140 valid unique entities;
- 1,880,491 observed relationships;
- 1,880,488 accepted, three dangling rejects, zero invalid/duplicates.

The corrected category vocabulary is binding: category 5 is Donation
(1,267,716), not Lobbying; category 7 is Lobbying (10,655). P2 emits Position,
Education, and Lobbying only. All other accepted categories are explicitly
`OUT_OF_SCOPE_CATEGORY`.

Every assertion retains source relationship and endpoint IDs, literal dates,
conservative precision, descriptions after contact-value minimization, raw
currentness as a source field, source locator, and category-specific attributes.
It carries temporal weight zero.

### 6.2 Restricted legacy seed

The corpus copies the sealed 5,773-record/533-office contact-free seed by exact
hash. It does not re-open raw workbooks, resolve people to Politico/LittleSis,
or claim canonical/current employment. Its interim authority is provisional
pending Paul's ratification; refusal is handled by append-only withdrawal.

### 6.3 Separate gated planes

> **2026-09-01 supersession note:** the bullets below record the 2026-08-30
> pre-build state. Politico is now one of the five enabled v6 structural
> sources; verified House 2009Q3–2015Q4 and Senate 2011–2026 candidate lanes
> now exist. A5c pre-web House breadth remains `BLOCKED_PARTIAL_RECOVERY`, with
> only 1997Q1 Part 2 recovered, and A8 is a 453-row/388-person review ledger.
> None of these employment lanes has produced a canonical employment
> promotion, and full career breadth remains incomplete.

- Politico: 18,618 normalized profiles and model-assisted source-pair review
  exist locally, but human-gold precision is null and the source is disabled.
- LDA: C-5 and restricted source-native conservation pass. Composite receipt
  SHA-256 `0f985e79…c0b250` binds 541,659 unique filings, 12 twin windows, zero
  shortfall/cross-year duplicate UUIDs, registered 120 RPM/page-size-25/eight-
  in-flight conduct, one hash-bound DNS resume, and unchanged legacy seal
  `d7304591…94961e`. Source-native receipt SHA-256 `5dfd3bbb…9dce8c` binds five
  deterministic restricted files and 6,682,108 independently validated rows.
- Historic member references: broad Voteview spine and commit-pinned exact-term
  references exist, but the normalized effective-dated plane is incomplete.
- House/Senate payroll: collectors, inventories, parsers, and gold sets are not
  built.

## 7. Identity and adjudication contract

Candidate stages may use normalized names, aliases, role/title evidence,
container/time compatibility, and hard-negative rules. They must report strata
and abstain rather than force a link.

The existing Politico↔legacy pilot has two model reviewers and an all-MATCH
100-row calibration stratum. This demonstrates consistency only. It cannot
freeze Q-1/I-4 because human gold is zero, precision is null, negative/ambiguous
examples are absent, and recall has no exhaustively labeled universe. Holdout
labels are single-use and outcomes remain sealed until the calibration rule is
frozen.

The implemented LDA exact-name candidate corpus is also evidence, not identity
truth. Receipt SHA-256 `b8be6326…e1f4a` binds 6,978 rows: 6,313 LittleSis, 446
Politico, and 219 legacy candidates. The rows cover 4,741 unique LDA lobbyists,
5,526 unique targets, and 3,910 normalized keys; 4,459 rows carry a within-source
name collision and 3,345 carry cross-source multiplicity. The method is
`NORMALIZED_NAME_EQUALITY_REVIEW_CANDIDATES_ONLY`, version
`lda-identity-normalized-name-candidates-v2`, using
`politico-normalize-name-v1`. Raw paired name evidence and receipt hashes are
retained. All rows require review, confidence is null, and canonical merges are
zero. The 1,953 rows with a government-term hit record lexical covered-position
evidence only; they do not verify government employment.

Required human evaluation before canonical joins:

- calibration and untouched holdout separation;
- hard-name, collision, title-conflict, office-missing, and negative strata;
- pair/cluster precision and recall with confidence intervals;
- reviewer agreement and conflict adjudication;
- leakage audit and one-shot holdout evaluation;
- explicit false-merge rollback/rebuild procedure.

## 8. Temporal and graph rules

Dates are uncertain half-open intervals with raw values preserved. A source
value such as `2007-00-00` has year precision; `2008-00-10` retains the literal
but cannot support day precision because the month is unknown. Open/current
bounds clip only to an explicit analysis `as_of`, never collection time by
accident.

Initial graph outputs, once their upstream gates pass, are separate:

- `person_edges`: co-tenure, sequential service, supported affiliations;
- `member_overlay`: shared personnel by concurrent/sequential interval union;
- `industry_edges`: person/activity, activity/registrant, activity/client, and
  corroborated Hill-to-industry transitions;
- `education_affinity`: non-social affiliation/affinity layer.

Title seniority may be a contextual feature. It is never labeled supervision.
Existing legislator adjacency cannot create a staffer edge.

The passed LDA `industry_edges` file contains filing-participation edges only.
It does not contain a corroborated Hill-to-industry transition, personal
contact, influence, or an employment fact. Those derivations remain unbuilt and
require identity, covered-position, temporal, and claim gates.

> **2026-09-01 implementation note:** the typed structural graph and its
> guarded score plane have been built and independently reviewed. Temporal
> interval/co-tenure and revolving computations exist as fail-closed code
> paths, but candidate-derived temporal sidecars remain noncanonical. No
> temporal employment or revolving edge is enabled in production.

## 9. Storage and publication

Restricted roots are under configured `%LOCALAPPDATA%\Melange\staffer_network`,
outside OneDrive. The corpus builder refuses targets outside the configured
corpus root and rejects known synced roots by default. Repository files contain
schemas, code, tests, aggregate receipts, and review/diagnostic documents only.

The 2026-08-30 accepted P2 generation contains:

```text
littlesis_entities.ndjson.gz
littlesis_relationship_assertions.ndjson.gz
quorum_legacy_source_native_seed.ndjson
source_native_corpus_receipt.json
```

Repository receipts bind source inputs, record files, exact counts, corrected
category vocabulary, same-machine twin determinism, and full 873,236-row
validation. CC BY-SA publication review remains deferred; the local corpus is
not a public artifact.

The separate restricted LDA generation contains:

| File | Records | Bytes | SHA-256 |
|---|---:|---:|---|
| `lda_lobbyist_assertions.ndjson.gz` | 25,340 | 1,928,569 | `80ac82346c435bb8f1231d9f3425d759ca9a8ae063db879ec104244f9fcd282e` |
| `lda_organization_assertions.ndjson.gz` | 54,073 | 2,503,228 | `0d35902244f02688d9ac961379efee0f96e3cfab1184409a4c93bb0584a1aed2` |
| `lda_activity_assertions.ndjson.gz` | 1,037,547 | 110,195,153 | `2ff6864f8a06e822277083230ab6a59abcc979ca12681e58490c89cb8a85b485` |
| `lda_industry_edges.ndjson.gz` | 4,816,559 | 430,061,239 | `363027b2c3fff40331b304c9dd9b1d7bd81691bc9f9915aaf1b8f4acd0a869b7` |
| `lda_covered_position_assertions.ndjson.gz` | 748,589 | 58,789,826 | `81841c810269bf967cb3edc10664dbbad5aa17261089eaa67e4f288c2fcda625` |

The restricted candidate file has 6,978 rows, 653,038 bytes, and SHA-256
`e2007da31695931954d309d8c25f577fa9a072ae8fc1b88728c4d0d92d2ae41f`.
Both LDA source-native and candidate schemas are refused by public-generation
load/publish paths. Names and record bodies remain machine-local.

## 10. Code and contract map

Implemented:

```text
fec/staffer_network/
  schema.sql
  source_manifest.py
  legacy_seed.py
  littlesis_contract.py
  source_native_corpus.py
  lda_contract.py
  run_lda_generation.py
  lda_composite_repair.py
  lda_source_native_corpus.py
  lda_identity_candidates.py
  politico_normalize.py
  politico_adjudication.py
  politico_adjudication_run.py
  publication.py
  schema_validation.py
  intervals.py
  phase0_gates.py
  employment_history.py
  graph_build.py
  network_math.py
  schemas/*.json

fec/network/staffer_network_loader.py
fec/tests/staffer_network/test_*.py
data/staffer_network/{policy,receipts,reference,reviews}/
```

Next implementation components:

```text
fec/staffer_network/
  adjudicate_lda_identity_candidates.py
  parse_lda_covered_positions.py
  ingest_historic_members.py
  ingest_house_sod.py / ingest_senate_reports.py
  build_source_ledger.py
  resolution_candidates.py
  adjudication_import.py
  consolidate_facts.py
  build_edges.py
  build_member_overlay.py
  refresh.py

fec/collect/
  collect_house_sod.py
  collect_senate_disbursements.py

fec/audit/audit_staffer_network.py
```

## 11. Enablement contract

```text
STAFF_NET=off       # default; no analysis artifact open
STAFF_NET=analysis  # explicit read-only structural overlay; Phase 6 PASS
```

The analysis loader admits only an immutable, receipt-validated structural
generation. A7–A9, employment ledgers, completeness audits, and temporal
sidecars are not canonical loader inputs.

There is no global `engine` value. Every engine consumer requires a separate
flag, schema handshake, frozen-input comparison, stability/impact assessment,
claim scope, rollback, reviewer, and accepted receipt.

## 12. Phase exits and exact next backlog

> **2026-09-01 phase adjudication:** the table immediately below is the frozen
> 2026-08-30 backlog snapshot. Section 0A.4 is current: Phase 2 is partial,
> Phase 5 has a structural `PASS` while canonical temporal production remains
> blocked, and Phase 6 has passed for the explicit immutable structural loader.

| Phase | Status | Exit remaining |
|---|---|---|
| 0 contracts/privacy/isolation | Passed | Preserve off behavior and receipts |
| 1 source-native seed/references/LDA/LittleSis | Partially passed | LittleSis/legacy and LDA restricted source-native substages pass; historic normalization, canonical identity, legacy ratification, and ShareAlike publication gates remain |
| 2 public payroll breadth | Not built | House/Senate inventories, collectors, parsers, gold, conservation |
| 3 restricted profiles | Corpus exists, source disabled | Human validity and redistribution-safe output contract |
| 4 resolution | Model-only report | Human calibration/holdout, negative strata, I-4/Q-1 freeze |
| 5 graph | Not built | Canonical facts, numerical/temporal invariants, ablations/nulls |
| 6 analysis loader | Closed | Selected-generation handshake and isolation packet |
| 7 consumers | Closed | One accepted packet per consumer |

Implementation order:

1. Human-review the restricted LDA identity candidates and evaluate
   covered-position semantics; do not promote lexical matches or participation
   edges into identity, employment, or transitions.
2. Normalize the pinned historic member/term spine without back-projecting
   current committee membership.
3. Build a source-native ledger loader for the validated local corpus; maintain
   zero cross-source identity assertions.
4. Obtain/rule on legacy A-0 ratification and LittleSis publication obligations.
5. Construct human adjudication calibration/holdout strata; evaluate once.
6. Inventory and collect House/Senate public payroll sources with lossless
   parsers and annotated gold.
7. Build canonical facts only from source planes whose authority, conservation,
   quality, temporal, and privacy gates pass.
8. Emit separate graph layers, evaluate robustness, then consider analysis-only
   loading. Consumer work comes last and remains independent.

## 13. Acceptance statement

The design and metric contracts are ready for implementation. The 873,236-row
P2 generation is complete for its declared LittleSis/legacy scope, and the
separate 6,682,108-row LDA source-native generation is complete through its
cutoff. The 6,978 candidate rows are a restricted review queue. These artifacts
do not establish person identity, employment episodes, Hill-to-industry
transitions, or analytical claims. Canonical identity, graph, analysis,
publication, consumers, and `STAFF_NET` remain metric-gated and off.

**2026-09-01 acceptance addendum.** The canonical fact plane, typed structural
graph, and explicit analysis loader are implemented for the five-source v6
generation. M1 passes after the `INTERVAL_BLOCKED` fix, structural Opus review
passes, interval/co-tenure Opus review passes, revolving-door Opus review passes
within its math/validation scope, and the consolidation-receipt review passes
within receipt-semantic scope. The measured regression evidence is 48 focused
tests and 222 staffer-network tests plus 73 subtests, all passing. Employment
completion is false: all 25,340 scoped people
still lack complete-lifetime attestation, canonical employment promotions are
zero, A5c remains `BLOCKED_PARTIAL_RECOVERY`, and temporal employment/
publication stays closed pending admissible adjudicated data. The overall Meta
LOOP disposition remains `BLOCKED`.
