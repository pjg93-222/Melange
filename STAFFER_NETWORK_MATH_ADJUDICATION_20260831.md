# Staffer Network Mathematical Adjudication — 2026-08-31

## 0. 2026-09-01 verification addendum

M1 returned **PASS after one fail-closed temporal fix**. An accepted Hill/
industry episode pair with a missing ordering boundary previously reached an
empty `min()` candidate set. The temporal sidecar now retains one explicit
`INTERVAL_BLOCKED` review path with null gap bounds, `primary_weight=0`,
`possible_weight=0`, and no temporal edge. When no guaranteed or possible pair
exists, `INTERVAL_BLOCKED` takes precedence over `WRONG_ORDER`, because unknown
chronology cannot be dismissed as wrong order.

The on-disk Opus 5 structural-math micro-review is `PASS`. The separate on-disk
Opus 5 interval/co-tenure micro-review is also `PASS`, confined to half-open
normalization, union/intersection, co-tenure bounds, and the duration transform.
The revolving-door micro-review is now also `PASS`, confined to revolving-door
temporal mathematics and its fail-closed validation path. Its review file is
`data/staffer_network/reviews/OPUS5_REVOLVING_DOOR_MICROREVIEW_20260901.md`
(4,978 bytes; SHA-256
`58db6b2e3ca1b4d7cc03131407d358521655ba5538c6d3e236e5a4425625c01f`).
None of these verdicts authorizes identity, employment, temporal-production,
or causal claims. The separate final consolidation-receipt review is `PASS`
only for receipt semantic safety. Its file is
`data/staffer_network/reviews/OPUS5_CONSOLIDATION_RECEIPT_FINAL_REVIEW_20260901.md`
(SHA-256
`eb9f118cb4f5e9ff3db65fbce753b85e58fb9415f1b874857d75d8429b7559ba`).
It does not establish employment-corpus completeness, identity resolution, or
temporal-production readiness; its seven nonblocking hardening findings remain
open.

The broad local staffer-network regression command
`python -m pytest -q fec/tests/staffer_network audits/staffer_network` passed
222 tests plus 73 subtests with zero failures or errors. The receipt-safety
focused suite passed 48 tests. The
current `fec/staffer_network/network_math.py` is 13,668 bytes with SHA-256
`011ae4dcb7e4611f5215fa0ac1a9fb24950a24984f65844ae3419f316a3daf5c`.

This is implementation verification, not employment-corpus completion. A9
conserves all 25,340 sealed IDs, but only 13,697 have any employment candidate;
11,643 have none, 16,486 lack a dated former-position candidate, 18,227 lack a
bounded employment-interval candidate, and 7,113 remain in P3 identity and
chronology adjudication. All 25,340 lack complete-lifetime employment
attestation, and canonical employment promotions are zero. A7, A8, and A9
remain noncanonical review/scheduling sidecars. A5c remains
`BLOCKED_PARTIAL_RECOVERY`: one report part does not establish the 52-quarter
House backfile. Data and production remain closed, and the Meta LOOP
disposition remains `BLOCKED`.

## Verdict

The structural graph mathematics is implemented and internally consistent for
descriptive connectedness. The temporal co-tenure and revolving-door
mathematics is also implemented, but it must remain closed over the current
review-candidate identity plane until identity, employer/container, and dated
episode evidence is adjudicated. No value below is evidence of causal
influence, access, friendship, or ideology.

Employment chronology is the binding enrichment dimension. Education remains
an optional affiliation layer and does not block employment-history
completeness.

## 1. Structural edge support

Canonical v6 assigns each direct canonical fact structural weight `1.0`.
Before scoring, repeated evidence rows for the same unordered endpoint/layer
key are collapsed by `max`, so duplicate rows cannot create extra graph mass.
Evidence rows remain conserved in the fact plane.

The library also implements a bounded independent-source support combiner:

```text
s_e = 1 - product_q (1 - max_r s[q,r])
```

where `q` is a source system and `r` is a row from that source. This keeps only
the strongest row within a source and applies noisy-OR across source systems.
It is evidence strength, not an identity probability. This combiner is tested
but is not wired into the current canonical v6 graph builder; therefore it
must not be described as a live production weight.

## 2. Layer-balanced traversal

For node `i`, neighbor `j`, active layer `l`, layer edge weight `w[i,j,l]`,
and active-layer set `L_i`, the implemented transition is:

```text
P[i,j] += (1 / |L_i|) * w[i,j,l] / sum_k w[i,k,l]
```

Non-isolate rows sum to one. Traversal is made bidirectional for descriptive
connectedness, while direction remains on the canonical fact. Equal mass per
active layer is an explicit modeling prior, not a claim that the layers have
equal causal importance.

## 3. Connectedness

Primary connectedness is PageRank on the layer-balanced operator:

```text
r = alpha * P.T * r + alpha * dangling(r) * v + (1 - alpha) * v
```

The production point estimate uses `alpha = 0.85`; `0.70` and `0.95` are
required sensitivity runs. Teleport mass `v` is equal across represented
entity kinds and uniform within each kind. Primary scores exclude all identity
review candidates. An explicitly exploratory score may add only strict
one-to-one review candidates.

This quantity should be labeled `connectedness_pagerank`, not causal
influence. Isolates retain teleport-only mass and must be excluded from ranked
reads using the emitted isolate flag. Cross-kind comparisons are shaped by the
kind-balanced teleport prior.

## 4. Eigenvector centrality

The diagnostic operator is:

```text
A = (P + P.T) / 2
```

The Perron vector is solved independently inside each connected component and
L1-normalized within that component. Isolates receive zero. A component that
does not meet the fixed tolerance is emitted as null rather than approximate.
The values are not comparable across components and must never be globally
ranked. This is a component-local degree-normalized diagnostic, not standard
global Bonacich eigenvector centrality.

## 5. Bridging

Bridging is normalized Simpson diversity of a node's row-normalized walk mass
across neighbor entity kinds:

```text
B_i = (1 - sum_g p[i,g]^2) / (1 - 1/G)
```

It is invariant to a scalar increase in total tie strength and is reported
separately from strength and PageRank. Feasible neighbor kinds differ by entity
kind, so bridging values are not directly comparable across kinds.

## 6. Temporal co-tenure

All normalized episodes use uncertain half-open intervals. Overlapping and
adjacent episode ranges are unioned before intersection, preventing duplicate
payroll rows, quarterly observations, or simultaneous multi-office records
from double-counting time.

For two people, `G` is guaranteed overlap in days between their interval
cores, and `P` is possible overlap in days between their interval envelopes:

```text
w_co_lower = 1 - exp(-G / tau)
w_co_upper = 1 - exp(-P / tau)
tau = 365.2425 days
```

Possible-only overlap has primary weight zero. A graph-level person pair again
unions overlap calendars across containers before converting days to weight.

## 7. Revolving-door paths

A Hill-to-industry path qualifies only when the Hill episode is guaranteed to
end no later than the industry episode begins under their uncertainty bounds.
The member-to-organization primary weight is the number of unique adjudicated
people with a guaranteed ordered path. Optional gap decay is reported only as
a sensitivity interval:

```text
d_lower = 2^(-gap_max / h)
d_upper = 2^(-gap_min / h)
h = 730.485 days
```

Registrant employment and being named on a client activity remain distinct
predicates. LDA filing participation, covered-position text, or a client name
alone never asserts employment.

An episode pair without all four ordering bounds is retained as
`INTERVAL_BLOCKED`, with null gap bounds and zero primary/possible weight. It
cannot contribute to a revolving edge. This fail-closed disposition is a
review record, not evidence that the transition occurred or that its order is
wrong.

### 7.1 Revolving-door hardening backlog

The Opus 5 revolving-door verdict is `PASS` with eight nonblocking findings:

1. Revolving-path `possible_weight` stores the upper gap-decay factor, not a
   probability or an upper bound on the unit primary contribution. Consumers
   must not aggregate it across predicates; temporal schemas remain restricted.
2. Publication validation does not independently enforce
   `gap_decay_lower <= gap_decay_upper <= raw_weight` or pin each guaranteed
   path's primary weight to one. The producer satisfies these invariants, but
   edge decay ordering is not yet independently validated.
3. Defensive skips for missing member or organization IDs lack dedicated
   receipt counters; accepted upstream episodes are expected to reject them.
4. Reverse-order paths display clamped zero gaps. Their `WRONG_ORDER` status,
   not the displayed gaps, carries the disposition; both weights remain zero.
5. Three zero-valued receipt invariants are literal fail-closed assertions, not
   independently measured counters.
6. Direct tests remain thin for `POSSIBLE_ONLY`, `WRONG_ORDER`, blocked/wrong
   precedence, multi-candidate selection, multiple people per edge, and numeric
   decay sums.
7. `interval_from_episode` does not itself apply current/as-of censoring.
   Upstream current episodes must be clamped; absent bounds remain
   `INTERVAL_BLOCKED` with zero weight and no edge.
8. A selected path retains support only for its chosen episode pair; discarded
   candidates for the same key are not emitted as provenance.

These items harden validation, observability, tests, and field semantics. They
do not relax identity, employment-completeness, or canonical-promotion gates.

## 8. Composite score ruling

No composite influence score is emitted. Adding raw strength, PageRank,
component-local eigenvector values, and bridging would double-count
connectivity while mixing incompatible scales. Each statistic remains a
separately named diagnostic.

## 9. Verification and remaining gate

- Focused post-integration run: 43 passed — 7 canonical-graph tests, 33
  employment-history tests, and 3 interval tests.
- Consolidation receipt-safety focused suite: 48 tests passed.
- Broad staffer-network regression: 222 tests and 73 subtests passed with zero
  failures or errors.
- Opus 5 structural-math micro-review: `PASS`.
- Opus 5 interval/co-tenure micro-review: `PASS`, confined to its named scope.
- Opus 5 revolving-door micro-review: `PASS`, confined to revolving-door math
  and its fail-closed validation path; the eight nonblocking findings above
  remain hardening work.
- Opus 5 consolidation-receipt final review: `PASS`, confined to receipt
  semantic safety; its seven nonblocking findings remain hardening work.
- No end-to-end employment-completeness or production `PASS` is inferred from
  the scoped consolidation-receipt verdict.
- The employment-completeness audit now fails closed on employment episode
  content, dates, sources, exhaustive attestation, unresolved employment gaps,
  and adjudication status. Education defects are separately reported and
  nonblocking.
- Temporal scores remain blocked for review-candidate identities. They may be
  built into a new immutable canonical generation only after identity and
  episode adjudication, an independent-source verification pass, deterministic
  reproduction, and adversarial review.
