# Opus 5 revolving-door micro-review

- Run: `run-20260831T1850525496629Z-8993807782`
- Stage: `R0b2b-opus5-revolving-microreview`
- Model/effort: Claude Opus 5 / maximum
- Mode: read-only

## Verdict

`VERDICT: PASS`

`BLOCKERS: none`

All nine requested checks passed by static source review. This verdict is
confined to revolving-door temporal mathematics and its validation path; it
does not authorize scoring review-candidate identities, incomplete employment
histories, or causal language.

## Equation checks

1. **Ordering partition: PASS.** `GUARANTEED` means
   `hill.end_latest <= industry.start_earliest`; `POSSIBLE` means
   `hill.end_earliest <= industry.start_latest`
   (`fec/staffer_network/employment_history.py:1617-1618`). Ordered interval
   bounds make guaranteed imply possible, so the ternary at `:1624` is a
   proper three-way partition.
2. **Gap bounds: PASS.** With ordered start and end uncertainty,
   `max(0, start_earliest-end_latest) <=
   max(0, start_latest-end_earliest)`. The runtime inversion guard is at
   `employment_history.py:1621-1622`.
3. **Fixture reproduction: PASS.** The reviewed Hill end of 2024-01-03 and
   industry start bounds 2024-08-01/2024-08-31 yield the tested 211/241-day
   guaranteed gap (`test_staffer_employment_history.py:1004-1008`).
4. **Decay bounds: PASS.** For `h=730.485`,
   `d_lower=2^(-gap_max/h) <= d_upper=2^(-gap_min/h)`
   (`employment_history.py:1649,1860-1861`). Edge sums preserve the ordering
   (`:1916-1917`).
5. **Raw weight: PASS.** A revolving edge's raw weight is the number of unique
   contributing people (`employment_history.py:1893,1911`), independently
   checked against `contributing_person_count`
   (`fec/staffer_network/publication.py:339-340`). Decay remains separate.
6. **Receipt conservation: PASS.** Exactly one status and one path are emitted
   per person/member/organization/role key; status counts sum to candidate keys
   (`employment_history.py:1848,1886,1956`; `publication.py:350-351`).

## Requested checks

| Check | Verdict | Evidence |
|---|---|---|
| ACTIVE episodes with accepted identity/container only | PASS | `employment_history.py:1677-1682,1773-1775` |
| Primary path requires guaranteed Hill-before-industry order | PASS | `:1617,1879,1887` |
| Ordered gap bounds | PASS | `:1619-1622`; `intervals.py:32-35` |
| Possible-only/wrong-order cannot carry primary weight | PASS | `employment_history.py:1879`; `publication.py:301-302` |
| Deterministic, zero-weight `INTERVAL_BLOCKED` path; no edge | PASS | `employment_history.py:1614-1615,1800,1832-1838,1854-1857,1886,1974-1979`; `publication.py:313-317`; tests `:1040-1092` |
| Deterministic selection and no person double count | PASS | `employment_history.py:1670-1672,1778,1810,1817-1845,1893-1895` |
| Unique-person raw weight and ordered decay sensitivity | PASS | `:1649,1860-1861,1911-1917`; `publication.py:339-340` |
| Registrant employment and client activity distinct | PASS | `employment_history.py:71-73,1789-1799`; `publication.py:341-344` |
| Validation rejects invalid endpoints, weights, gaps, loops, and non-conservation | PASS | `publication.py:294-327,339-353`; temporal schemas |

## Nonblocking findings

1. On revolving paths, `possible_weight` stores the upper gap-decay factor,
   not a probability or an upper bound on the unit primary path contribution.
   Cross-predicate consumers must not aggregate this shared field. Temporal
   schemas remain restricted from publication.
2. Publication validation does not independently enforce
   `gap_decay_lower <= gap_decay_upper <= raw_weight`, nor pin a guaranteed
   revolving path's primary weight to exactly one. The producer does satisfy
   these invariants.
3. Missing member or organization IDs reach defensive `continue` statements
   without dedicated receipt counters, although upstream episode validation is
   intended to reject such accepted rows.
4. Non-qualifying reverse-order paths clamp both gap displays to zero; status
   must be read with the gaps. Their weights remain zero.
5. Three zero-valued receipt invariants are literal assertions backed by
   fail-closed producer validation rather than independently measured counts.
6. Direct test coverage is thin for POSSIBLE_ONLY, WRONG_ORDER, precedence
   among blocked/wrong candidates, multi-candidate deterministic selection,
   multiple people per edge, and numeric decay sums.
7. `interval_from_episode` does not itself apply the current/as-of censoring
   helper. Upstream current episodes are expected to be as-of clamped; absent
   bounds fail closed as `INTERVAL_BLOCKED`.
8. A selected path carries support for the chosen episode pair only; discarded
   candidate pairs for the same key are not emitted as provenance.

## Disposition

The revolving-door math and fail-closed publication path are accepted. The
eight findings are retained as implementation hardening/test backlog. They do
not relax the separate data-completeness and adjudication gates.
