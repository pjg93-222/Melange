# Staffer Social Network — Completed Ranking Design and Implementation

**Date:** 2026-09-08
**Implementation:** `staffer-social-network-v5-duration-attributed` / `staffer-ranking-duration-v1`
**Controlled comparison:** `staffer_social_network_20260908_v7_math_primary` on the unchanged v7 spine
**Released graph:** `staffer_social_network_20260908_v8_math_primary` on `hill_personnel_spine_20260908_v8_primary`
**Status:** implemented, independently verified and live. Both graph generations passed primary/twin verification with zero failures. Ten math source/test files plus coordinated consumer selectors were updated. All live cutover checks pass. The separate full-dashboard audit records 554 passes and 15 classified delivery/manifest failures.

The earlier session completed an audit and recorded the owner's decisions, but its attempt to save the Markdown stopped before creating the file. This document recovers that historical draft below and records the implementation completed in this worktree. The recovered text is historical evidence, not a new instruction or a current status report.

## Current mathematical contract

Let `i,j` be exact spine person IDs, `c` a normalized payroll workplace, `G_ijc` the unioned guaranteed overlap calendar within that workplace, and `d_ijc = |G_ijc|` its days. Admin containers and intern-compensation headers supply no scored co-tenure support. People and their source records remain available.

```
D_ij = |union_c G_ijc|                     # each calendar day counted once
lambda = 0.05                             # exploratory shared-role damping
q_ijc = lambda if either endpoint has an exact shared-role title in c, else 1
A_ij = sum_c(d_ijc * q_ijc) / sum_c(d_ijc)
w_ij = kappa_max * min(S_i,S_j) * (1 - exp(-D_ij / 365.2425)) * A_ij
f_ijc = d_ijc * q_ijc / sum_h(d_ijh * q_ijh)
s_i = sum_j w_ij
T_ic = sum_j(w_ij * f_ijc)                 # attributed office connection strength
m_ic = T_ic / s_i                          # zero for isolates
B_i = (1 - sum_c m_ic^2) / (1 - 1/K)       # K = all distinct containers in generation
```

`D` is a cross-container union. The denominator of `f` is an attribution total; it never replaces `D` in the edge's duration transform. Concurrent support from two offices therefore divides one edge's mass and cannot duplicate days. `sum_c f_ijc = 1` and `sum_c T_ic = s_i`.

Shared-role classification is exact after whitespace/case normalization: `SHARED EMPLOYEE` and `SHARED EMPLOYEE (OTHER COMPENSATION)`. The available span's `title_last` is the evidence used; this does not establish that the title held on every historical day. Damping is confined to that person/container cell, and valid support from other workplaces remains. Financial, IT and part-time titles are not silently added to this class.

The owner's "soft cap" is implemented as retained positive contribution, using the prior audit's damping interpretation. This is **not a finite cap on a person's total strength**: more legitimate supported ties can still increase it. It is also not a contact probability. A distinct aggregate-strength cap would be a different model.

The persons-only PageRank operator, uniform restart, damping sensitivity at 0.70/0.85/0.95, and component-local eigenvector calculation remain as specified in the recovered audit. All diagnostics are recomputed from the revised weights. No time-since-service decay, container-size normalization, or new identity merge has been introduced.

One statement in the recovered audit needed correction: an isolate's final PageRank is **not** the uniform restart value `1/N`. With `z` isolates and damping `alpha`, its stationary score is `(1-alpha)/(N-alpha*z)` because dangling mass is redistributed. In the controlled v7 comparison, `N=144,690`, `z=23,697`, and `alpha=0.85` give `1.204359298918365e-6`; every emitted isolate agrees within `2.12e-22`. The restart value is `6.911327666044648e-6`. Isolates are excluded from ranked connectedness lists.

## Ranking and tie decisions

- **Member list:** descending published PageRank, then descending `member_connection_strength` (sum of `T_ic` over eligible non-shared workplaces belonging to that member). `rank_tie_size` records equal numeric keys. IDs are only a deterministic display key; a cutoff through a tie remains explicitly a tie.
- **Bridge list:** require positive supported connections to at least two eligible member workplaces. Rank by the connection strength beyond the strongest member office: `sum_b T_ib - max_b T_ib`, then PageRank. This replaces the count-first order. Shared-role cells, intern pools and admin pools do not qualify for this list.
- **Outreach-specific comparison:** `staffer_outreach_ranking.py` accepts exact origin, target and candidate IDs, verifies the generation, and reads the complete operator. It breaks equal published PageRank by `distance(origin,candidate) + distance(candidate,target)`, then the larger leg, using positive edge cost `1/w`. These are independently shortest legs and can retrace nodes; the result is a comparative distance, not a claim of a simple introduction route. Unreachable legs remain unknown/infinite internally and are exposed as null with ties preserved. A sampled display graph is never used.

The outreach command is a complete callable consumer and is tested. The existing 8841 interface has its own feature-weighted route objective; it has not been silently replaced by this co-tenure comparator. A dashboard can call this consumer when it has a specific origin and target.

## Parameter selection and full-population result

The damping-only sweep reproduces the existing 4,660,388-edge v6 graph's PageRank to a maximum absolute difference of `2.85e-19`. The rows below measure shared-role people among the first 100 ranked people. This is a concentration diagnostic, not ground-truth validation of relationships.

| Retained shared-role contribution | Shared-role people / top 100 | Newly isolated people |
|---:|---:|---:|
| 100% | 99 / 100 | 0 |
| 50% | 77 / 100 | 0 |
| 25% | 50 / 100 | 0 |
| 15% | 29 / 100 | 0 |
| 10% | 22 / 100 | 0 |
| 5% | 18 / 100 | 0 |
| 2% | 14 / 100 | 0 |
| 1% | 14 / 100 | 0 |
| Deletion control | 14 / 100 | 182 |

Five percent is the largest tested positive factor below the audit's provisional 20-of-100 concentration criterion. That criterion is an implementation selection rule, not an owner-specified accuracy target. The value remains an exploratory default. The independently rebuilt v8 graph also has 18 shared-role people in its top 100; this verifies implementation consistency, not relationship accuracy.

The controlled v7-spine comparison includes duration attribution, damping and pool exclusion. Its unchanged IDs isolate the mathematical change:

| Measure | Result |
|---|---:|
| Conserved person IDs | 144,690 / 144,690 |
| Excluded intern compensation headers | 244 |
| Excluded administrative pools | 54 |
| Positive co-tenure edges | 4,546,099 |
| Possible-only, zero-weight rows | 766,885 |
| Candidates rejected for zero overlap | 10,103,526 |
| Damped edges | 257,427 |
| People with positive co-tenure | 120,993 |
| New isolates from pool exclusion | 9,280 |
| Shared-role people in new top 100 | 18 / 100 |
| Original top 100 retained | 13 / 100 |
| Spearman rank correlation, all 130,273 previously scored people | 0.866294 |
| Maximum office-strength conservation error | 1.17e-12 |
| Null eigenvector values | 0 |

All 2,471 edges supported by an intern pool **and another eligible workplace** retain their other workplace support; removing every edge that mentions a pool would incorrectly delete these. The 114,289 pool-only positive edges are removed. The larger whole-population change mainly reflects the explicit intern-pool decision.

## Verification and released consumers

The coordinated v8 spine passed all 50 independent assertions with seven byte-identical primary/twin artifacts. This task separately checked its release bindings. The direct native v6-to-v8 map gives all 7,712 referenced Politico IDs exactly one target. The two v7 split reversals are never resolved by arbitrarily selecting a child, and scores are recomputed rather than copied through an ID map.

The v8 graph's primary and independent twin are complete; full verification is **PASS with zero failures**. The graph has 144,692 people, 120,993 with positive co-tenure, 23,699 isolates and 4,546,099 positive edges. There are 18 shared-role people in its top 100. Maximum office-strength conservation error is `1.17e-12`, isolate PageRank error is `2.12e-22`, and no eigenvector values are null. The verifier independently recomputed every emitted weight and office-strength total, reconstructed source calendars for a deterministic 2,000-edge sample, enumerated the complete candidate population and checked primary/twin identity and source hashes.

Passing implementation checks: 17 math/interval tests, 140 graph fixture checks, 213 surface contract checks, 219 HTML-renderer checks, four rendered tie cases, 11 inventory/routing selector tests and 120 live-cutover integration tests. These include 3-day versus 3,000-day attribution, source-ID remapping, conservation, malformed/nonfinite weight rejection and revised rankings. These are named checks, not a claim that the entire repository suite passes.

The published section contains 533 members, 7,675 ranked rows and 25 bridges. Lists retain up to 15 people; 888 rows carry explicit tie metadata. Group-schema and office-name resolution defects are fixed. The final v8 section is 5,393,487 bytes, within the 6 MB limit. Five office names remain explicitly unresolved. The complete-graph outreach consumer passed with a disconnected candidate correctly returning null distance. The legacy member template now renders shared ranks and tie/cutoff explanations. The current Groups template intentionally uses its narrower provenance scope.

The old payroll bundle required source-row migration. The verified replacement conserves 425,825 episodes, 135,039 employment people, 231 pairs and 1,351,415 admitted source rows. The live API returns all four split targets separately with v8 provenance. Every one of the 144,692 payroll IDs appears in the complete live inventory as a profile or accepted alias, with zero invalid v8 IDs. Live groups, all four static data files and both rebuilt pages pass the same ID-membership checks. Historical source identifiers remain in provenance; unchanged IDs remain valid members of v8.

The guarded switch completed on port 8841, PID 31944, with `ready=true`, no errors and the verified graph receipt. The member desk, staffer page, combined redesign and email redesign pages were rebuilt. HTTP content matches the selected redesign artifact after its documented local navigation/profile-script transformation, and the external profile script matches its local hash. The launcher preserves the selected dashboard on restart and defaults explicitly to the authorized redesign target.

The broad `audit_full.py` result remains **554 passed, 15 failed**, classified in `audit_failure_classification.json`. Two email-input hash mismatches demonstrably predate the cutover; the historical manifest already disagreed with the prior staffer section. Other failures concern stale manifest sentinels and absent rescue/git-pack paths outside this task. No pre-cutover snapshots are claimed for files that were not backed up.

Carbonite locks `Moneyball.html`. The dashboard task explicitly designated the rebuilt `Moneyball_Redesign.html` as the live publication target and directed preservation of its deployment artifacts/global manifests. The served response, committed restart selector and complete v8 data islands prove that target is current. The global audit's canonical-filename freshness check is recorded as a superseded target check, not falsely marked passing. No in-scope live publication target remains stale.

The scoped source commit preserves unrelated workspace edits. The dashboard task's existing uncommitted pipeline Groups block remains intact; `live_rollout.patch` records its two v8 guards and the complete exact selector delta. This task does not adjudicate new identities or turn exploratory employment into canonical fact.

Durable records in main, relative to the repository:

- `audits/staffer_ranking_math_20260908/completion_receipt.json`: final source/artifact hashes and outcomes.
- `audits/staffer_ranking_math_20260908/live_cutover_validation.json`: complete live and published-consumer checks.
- `audits/staffer_ranking_math_20260908/audit_failure_classification.json`: the 15 wider audit failures and evidence.
- `audits/staffer_network/staffer_social_network_20260908_v8_math_verification/staffer_social_network_verification_receipt.json`: full graph PASS, SHA256 `66574aa1e3e520b367c40ef81b82dfbe32d5675c9a001c9e6617e1730fe43034`.
- `audits/staffer_network/staffer_social_network_20260908_v8_math_primary/staffer_social_network_receipt.json`: graph receipt SHA256 `9c5384786f9b260edeca643297ab575c59324969077627ca6680788499d54723`.
- `audits/staffer_live_runtime/repin_20260908T060735Z.json`: successful guarded switch.

---

# Recovered historical audit (prior session, before implementation)

# Staffer Social Network — Mathematical Specification and Audit

**Date:** 2026-09-08
**Generation audited:** `staffer_social_network_20260907_v6_primary`
**Status:** specification verified; two defects confirmed by measurement; owner rulings recorded in §6; implementation not yet applied.

---

## 1. Scope and provenance

### 1.1 Authoritative files

All of the following live in the **live tree** (`C:\Users\pgoff\OneDrive\Desktop\Melange Systems`) and are **untracked by git**.

| Role | Path |
|---|---|
| Graph builder — all node, edge and score math | `audits\staffer_network\build_staffer_social_network.py` (3,506 lines) |
| Shared linear algebra | `fec\staffer_network\network_math.py` (352 lines) |
| Interval primitives | `fec\staffer_network\intervals.py` |
| Identity spine (node minting) | `audits\staffer_network\build_hill_personnel_spine.py` |
| Independent verifier | `audits\staffer_network\verify_staffer_social_network.py` |
| Dashboard section producer | `fec\surfaces\build_staffer_network_section.py` (1,915 lines) |
| Groups section producer | `fec\surfaces\build_staffer_groups_section.py` |
| Page renderer | `fec\surfaces\make_staffer_network_html.py` |
| 8841 sidecar loader | `fec\surfaces\staffer_graph_snapshot.py` |

### 1.2 Dead and legacy code

`fec\staffer_network\graph_build.py` is the old heterogeneous builder. It emits `network_edges.ndjson.gz` and `network_scores.ndjson.gz`, and it still calls `group_balanced_teleport` at line 255. Nothing in the current staffer social chain imports it.

`network_math.bridging_diversity` and `network_math.group_balanced_teleport` remain live code with no callers in this lane. Their non-import is deliberate and commented at `build_staffer_social_network.py:97-100`.

`audits\dashboard_repair_20260905\before\fec\run_pipeline.py:213` is an archived pre-D-022 snapshot with no groups step. It is not a second live pipeline.

### 1.3 Invocation

The producers are invoked from exactly one live place: `fec\run_pipeline.py:219` and `:226`. No PowerShell script invokes either.

---

## 2. The mathematics

### 2.1 Nodes

A node is a **person**, and only a person. Offices, organisations and policy areas were moved to the Groups layer under D-022 and carry `operator_included: False`.

```python
# build_staffer_social_network.py:182
NODE_KINDS = ("person",)
```

Node count: **144,690**.

Identity is minted by the spine (`build_hill_personnel_spine.py:316-321`):

```
spine_person_id = "hill:person:" + sha256(compact({
    "chamber":          <anchor node chamber>,
    "first_office_key": <anchor node office key>,
    "first_period":     <anchor node first period>,
    "name_key":         "<last>|<first_class>|<middle initial>",
})).hexdigest()
```

The anchor node is the minimum over the person's office nodes of (period start ordinal, chamber, office key).

Each person carries an identity tier, which feeds directly into edge weight:

| Tier | Definition | Strength `S` | Count |
|---|---|---|---|
| S1 | One office | 0.75 | 116,559 |
| S2 | Multiple offices in one chamber, linked only across non-overlapping periods, or a shared-employee row | 0.50 | 25,901 |
| S3 | Cross-chamber, name-only | 0.25 | 2,230 |

### 2.2 Edges — existence

There is exactly one operator layer, `co_tenure`. Membership, revolving-door and policy-area layers exist but carry `operator_weight 0.0` and contribute no operator edges.

Edges are produced by a sweep line over concurrent occupancy inside a single payroll container. This is **not** a clique over the container: a pair is emitted only where two people's calendars actually intersect.

```python
# build_staffer_social_network.py:1455-1480
def sweep(people, which):
    """Enumerate only pairs whose calendars actually intersect."""
    ...
    for s, e, p in segs:
        if active:
            active = [a for a in active if a[1] > s]
        for (as_, ae, ap) in active:
            if ap == p:
                continue
            lo = s if s > as_ else as_
            hi = e if e < ae else ae
            if hi <= lo:
                continue
            a, b = (p, ap) if p < ap else (ap, p)
            out_pair.append(a * NP + b)
```

The overlap test is `hi > lo` on half-open ordinal-day intervals. The minimum overlap is therefore **one day**; no `min_overlap_days` dial exists anywhere in the builder.

Core and envelope semantics are defined at `:274-285` and implemented in `intervals.py:79-86`:

```
core(e)     = [start_latest,   end_earliest)
envelope(e) = [start_earliest, end_latest)

guaranteed_overlap_days(a, b) = max(0, min(a.end_earliest,   b.end_earliest)
                                     - max(a.start_latest, b.start_latest))
```

Three outcomes:

| Status | Meaning | Treatment | v6 count |
|---|---|---|---|
| GUARANTEED | Core calendars intersect | Positive weight, enters the operator | 4,660,388 |
| POSSIBLE_ONLY | Envelopes intersect, cores do not | Emitted at weight 0.0, excluded from the operator (`:2831-2838`) | 915,176 |
| ZERO_OVERLAP | Neither intersects | Never emitted | 10,471,278 |

65.25% of co-container candidates are rejected for zero overlap. This is the D-019 overlap rule firing, and the build reports the count so that a silent failure of the test would be visible.

Senate REPORT_PERIOD stints are handled as the union of observed periods, one interval per contiguous run (`span_core_runs`, `:430-471`), with every run clamped into `[core_s, core_e)` at `:465-466`. That clamp can only narrow an interval, never widen it.

### 2.3 Edges — admin exclusion

```python
# build_staffer_social_network.py:181
CO_TENURE_EXCLUDED_CONTAINER_KINDS = frozenset({"admin"})

# build_staffer_social_network.py:1331-1334
co_tenure_containers = {
    cid for cid in by_container
    if c_kind[cid] not in CO_TENURE_EXCLUDED_CONTAINER_KINDS
}
```

54 of 1,833 containers are excluded. 14,328 people hold only excluded containers and become co-tenure isolates. Excluded containers keep their membership layer and their node scores; they simply enumerate no pairs.

The exclusion is applied to the candidate census as well as to the sweep (`:1325-1330`), so the D-019 rejection count is not inflated by pairs that were never eligible. **Measured: zero guaranteed edges touch an admin container. The exclusion is airtight.**

### 2.4 Edges — weight

For an unordered pair (i, j):

```
w(i,j) = kappa_max × min(S_i, S_j) × (1 − exp(−guaranteed_days / 365.2425))
```

```python
# build_staffer_social_network.py:2146-2155
hi_tbl, lo_tbl = mask_table(KAPPA)
g_kappa_max = hi_tbl[g_bucketmask]
g_kappa_min = lo_tbl[g_bucketmask]

ga = (g_key // NP).astype(np.int64)
gb = (g_key % NP).astype(np.int64)
w_lower = 1.0 - np.exp(-g_days.astype(np.float64) / TAU_DAYS)
tier_pair = np.minimum(p_str[ga], p_str[gb])
w_kappa = g_kappa_max * w_lower
w_tiered = g_kappa_max * tier_pair * w_lower
```

Container-kind coefficients (`:140-149`):

| Container kind | kappa |
|---|---|
| member_office | 1.00 |
| committee_same_side | 0.75 |
| leadership | 0.75 |
| committee_side_unknown | 0.60 |
| committee_bipartisan | 0.60 |
| admin | 0.50 |
| unresolved | 0.50 |
| committee_opposite_side | 0.40 |

`kappa_max` is the maximum over the containers that actually supplied guaranteed days. `kappa_min` is emitted alongside on every edge (`:2803`), so the min-kappa alternative is recomputable without a rebuild.

`guaranteed_days` is the **union** across containers, not the sum (`:1532-1550`). 98,539 pairs share two or more containers; the union rule removed 501,966 days that a naive sum would have double-counted.

Maximum possible single-edge weight is 1.00 × 0.75 × 1 → **0.750000**, which is attained. 136,109 edges (2.92%) sit within 5% of the ceiling. Median edge weight is 0.219, mean 0.257.

### 2.5 Normalization and decay

There is **no** container-size normalization, **no** tenure-length normalization and **no** degree normalization applied to the weight. The only normalization is the row-stochastic walk:

```
P[i,j] = w_ij / Σ_j w_ij
```

`layer_balanced_transition` divides by `active_layers[i]`, but with a single operator layer that divisor is always 1 for every non-isolated node (`network_math.py:149-159`; the builder notes this at `:193-194`).

There is **no time decay**. The builder states this outright:

```python
# build_staffer_social_network.py:210-213
"current_behaviour": (
    "no decay of any kind; w_lower depends only on guaranteed overlap DAYS, "
    "never on how long ago those days were"
),
```

`1 − exp(−days/τ)` is a saturating function of tie **duration**, not a decay in elapsed time. A 1998 tie and a 2024 tie of equal length score identically. τ = 365.2425 days is the duration scale, not a half-life.

### 2.6 Node scores

**PageRank** — `connectedness_pagerank_exploratory` (`:2221-2231`):

```
teleport v = 1/N uniform = 6.9113276660446475e-06
r ← (1−α)·v + α·Pᵀ·r + α·(Σ_{dangling} r)·v
α ∈ {0.70, 0.85, 0.95};  tolerance 1e-11 (L1);  max 750 iterations
```

The teleport is uniform over persons. It is **not** kind-balanced — the 09-05 inflation channel is gone structurally, because the node universe is now single-kind. Convergence: 55, 116 and 339 iterations respectively. The 14,417 isolates each hold exactly the teleport prior. The dashboard reads α = 0.85.

**Eigenvector** — `eigenvector_component_local_exploratory` (`:2233-2264`):

```
A = (P + Pᵀ) / 2
y = A·x + x                    # the +I term kills bipartite 2-cycles
normalize L1 WITHIN each component
tolerance 1e-12, max 750 iterations
non-converged components repaired by eigsh(k=1, which="LA")
```

14,502 components, all converged in 202 iterations, zero repairs, residual 9.44e-13. **Values are not comparable across components**, and the emitted note says so.

**Office diversity** — `office_diversity_exploratory` (`:576-577`, `:649-657`):

```
office_diversity(i) = clip(1 − Σ_c m_ic², 0, 1) / (1 − 1/K),   K = 1,833
```

The mass `m_ic` is currently allocated by splitting each edge's `w_e / strength(i)` share **equally** across the containers that supplied guaranteed days. See §4.1 — this is the subject of a ruling.

**Degree and strength** (`:2275-2277`):

```
raw_strength(i)     = Σ_j w_ij
co_tenure_degree(i) = |{ j : w_ij > 0 }|
```

### 2.7 The ranking

There is no composite score. No z-scoring, no percentile transform, no weighted blend. The published ranking is a single lexicographic sort:

```python
# build_staffer_network_section.py:1224-1225
ranked = sorted(eligible, key=lambda index: (-people[index][3],   # pagerank @ 0.85
                                             -people[index][2],   # co_tenure_degree
                                              people[index][0]))  # node_id
```

Values are rounded to six significant digits at ingest rather than at emission (`:805-807`), so the published order is reproducible from the published fields.

Pre-ranking exclusion, per the 2026-09-07 ruling:

```python
# build_staffer_network_section.py:292-295
TOP_STAFF_EXCLUDED_TITLES = frozenset({
    'SHARED EMPLOYEE',
    'SHARED EMPLOYEE (OTHER COMPENSATION)',
})
```

Matching is exact on the normalized string, never a substring, and is scoped per member.

Other ranked lists:

- `top_bridge_people` (25 rows) — sorted by `(−member_count, −office_diversity, node_id)`.
- `shared_with` (12 per member) — sorted by `(−count, bioguide)`. This is a count of people attached to both offices and is explicitly **not** an edge.

`top_shared_pairs`, built in the 2026-09-05 variant-A work, is not present in any current producer.

### 2.8 Inputs

| Variable | Source | Units | Enters at |
|---|---|---|---|
| `spine_person_id` | `hill_person_spine.ndjson.gz` (144,690 rows) | id | node identity `:2138` |
| core / envelope spans | `hill_person_office_spans.ndjson.gz` (204,697 rows) | ordinal days | sweep `:1455` |
| `contiguous_runs` | spine | period tokens | `span_core_runs :452` |
| House printed service dates | `house_personnel_ledger` (1,083,476 observations) | days | day-precision enrichment `:868` |
| `identity_tier` | spine | — | `tier_pair :2153` |
| `container_kind` | container metadata (1,833 rows) | categorical | `kappa_for :912` |
| committee side MAJ/MIN | payroll sub-unit regex `:931` | categorical | kappa bucket `:1284` |
| `guaranteed_days` | derived, cross-container union | days | `w_lower :2152` |
| roster (533 members) | `data\engine\congestion.json` | — | attachment |
| LDA / revolving | exploratory temporal tier | — | grouping layer only, 0 operator edges |
| Politico policy | `staffer_social_policy_layer.ndjson.gz` (11,525 rows) | — | grouping layer only, 0 operator edges |

Payroll co-tenure is the sole operator input. The receipt confirms `revolving_in_operator: 0` and `policy_edges_in_operator: 0`, consistent with the 2026-09-01 adjudication that keeps LDA out of the weights.

### 2.9 Dials

Every dial is stamped `DIAL_STATUS = "UNTESTED_DEFAULTS_PENDING_FREEZE"` (`:117`).

| Dial | Value |
|---|---|
| `TAU_DAYS` | 365.2425 |
| `ALPHAS` | 0.70 / 0.85 / 0.95 |
| `KAPPA` | 8 values, 0.40–1.00 |
| `S_STRENGTH` | 0.75 / 0.50 / 0.25 |
| `CO_TENURE_EXCLUDED_CONTAINER_KINDS` | `{admin}` |
| minimum overlap | 1 day, implicit in `hi > lo` |
| minimum shared count | none |
| PageRank tolerance / iterations | 1e-11 / 750 |
| Eigenvector tolerance / iterations | 1e-12 / 750 |
| `TOP_STAFF` / `TOP_BRIDGE_PEOPLE` | 15 / 25 |
| `--max-bytes` | 5,000,000 |

---

## 3. Correctness audit

Ten independent checks were run against the shipped generation. **No arithmetic bug was found.** Three controls passed exactly, which establishes that the specification above is what the code actually computes rather than what it claims to compute.

| Control | Result |
|---|---|
| Weight formula recomputed in CPython vs emitted `w_tiered_lower` | max abs diff **0.000e+00**, max ULP diff **0**, over all 4,660,388 edges |
| PageRank at α = 0.85 recomputed vs published scores | max abs diff **0.000e+00**, 116 iterations, residual 9.98e-12 |
| `guaranteed_days` reconstructed from trajectory stints vs emitted | **4,660,388 / 4,660,388 (100.000%)** |

| # | Check | Verdict |
|---|---|---|
| 1 | Vectorized vs scalar weight path | CORRECT |
| 2 | Multi-segment union loop | CORRECT |
| 3 | kappa bitmask assignment | CORRECT |
| 4 | `tier_pair` index alignment | CORRECT |
| 5 | Undirected deduplication | CORRECT, and a measured no-op |
| 6 | Row normalization with isolates | CORRECT |
| 7 | PageRank dangling mass | CORRECT |
| 8 | Eigenvector `(A+I)` iteration | CORRECT |
| 9 | `office_diversity` mass allocation | DESIGN CHOICE — ruled on, see §6 |
| 10 | Rounding and tie-break | DESIGN CHOICE — ruled on, see §6 |

Selected detail:

**Integer packing.** `g_key = a·NP + b` with NP = 144,690 gives a maximum key of 20,935,051,409 against an int64 maximum of 9.22e18 — a headroom factor of 4.4e8. Round-trip inversion is exact over 1,000,577 boundary and random pairs. Zero self-loops in the emitted file.

**Union loop.** Verified against a set-of-integers ground truth on disjoint, touching, nested, identical, single-segment and last-is-longest cases, plus 200,000 randomized sorted inputs with zero mismatches. The trailing `tot += cur_hi - cur_lo` at `:1548` is the only line that closes the final run; the single-segment and last-is-longest cases are the negative controls that would fail without it. Sortedness at the call site is guaranteed by `np.lexsort` at `:1508`. Were the input ever unsorted the error would **deflate, never inflate** — measured over 200,000 permutations: 0 inflated, 162,119 deflated, 9,008 equal.

**kappa bitmask.** Seven buckets, 128 masks. Sixteen distinct real mask values were decoded from the emitted edges and checked against the published container kinds: **zero mismatches over all 4,660,388 edges**, including 9,468 multi-bucket edges, so the test discriminates. The docstring at `:1305` says "6 buckets -> 64 masks" and is stale; the array is sized from `len(BUCKETS)` so no code depends on the wrong number.

**PageRank mass conservation.** Measured pre-normalization sum drift of 4.4e-16 per iteration on synthetic graphs. Negative control with the dangling term deleted drifts to 0.405 after 30 iterations, so the check is not vacuous.

**Eigenvector.** All entries of `(P + Pᵀ)/2` are non-negative (minimum 0.00086832, zero negative entries, symmetry residual 0.000e+00). The `+I` shift moves every eigenvalue by exactly 1 (measured to 1.33e-15) and leaves the dominant eigenvector unchanged. Power iteration matches a dense `eigh` solve on the largest component to 1.99e-12 with identical rank order.

### 3.1 Latent fragilities

None of these affects a shipped number today. All four are worth recording.

1. `duration_weight` at `:560` is dead code. Its only callers are an older builder and a unit test, so the tested weight function is not the one that produces the weights. The vectorized line that does produce them has no unit test asserting it equals the scalar rule. They agree to 0 ULP today.
2. `mask_table`'s docstring at `:1305` is stale. `g_bucketmask` is `uint8`, so a ninth bucket would raise `OverflowError` — loud, not silent.
3. `office_diversity_simpson` is called at `:2272-2274` with the pre-`keep`, pre-dedup edge arrays while the operator uses the post-dedup arrays at `:2215-2216`. Both premises were verified as identical today (`keep` is all-True; dedup removes nothing), but the coupling is unasserted.
4. The union loop's correctness rests entirely on the `np.lexsort` at `:1508`. `cross_check_intervals()` at `:722-748` reconciles the pairwise intersection only and does not cover the multi-segment union.

---

## 4. Confirmed defects

### 4.1 `office_diversity` ignores time

Each edge's mass is split **equally** across the containers that supplied guaranteed days, with no regard for how many days each container actually supplied.

```python
# build_staffer_social_network.py:634-642
share = np.repeat(w[lo:hi] / counts[lo:hi], repeat)
...
    np.divide(share, strength[ea], out=np.zeros_like(share), where=strength[ea] > 0),
```

`counts` is the *number* of containers on the edge, not the days each contributed.

The mass distribution is otherwise sound: `Σ_c m_ic = 1` holds for all 130,273 scored persons to a maximum deviation of 9.99e-15.

Exposure is concentrated. 4,561,849 edges (97.8856%) touch a single container, where the rule is a no-op. 98,539 edges (2.1144%) touch more, up to a maximum of 61.

Where it bites, it bites hard. A person with 3,000 days in one office and a 3-day committee detail:

| Rule | m_office | m_committee | office_diversity |
|---|---|---|---|
| Equal split (shipped) | 0.750000 | 0.250000 | 0.375205 |
| Days-proportional | 0.999500 | 0.000500 | 0.000999 |

A **375× inflation** for a container that supplied 0.0999% of the days. A staffer with one three-day detail scores as a near-perfect bridge.

Two smaller notes on the same function. `K` is set to 1,833, the number of containers in the generation, but only 1,753 containers can ever carry co-tenure mass; the normalizer differs by 2.4e-5 relative, which is immaterial but not what the docstring implies. And the population mean of 0.0725 cannot move much given the 2.1% exposure — the defect moves individuals, not the aggregate.

### 4.2 The degree tie-break is inert

`co_tenure_degree` broke **0 of 612** PageRank ties. Not once. Anyone equal on PageRank is structurally equal on degree, because identical calendars in one office produce identical degree and identical rank. The effective second key is therefore `node_id`, which is a sha256 digest — the order inside every tie group is pseudo-random hash order.

Measured across the 515 members with a published list, 7,205 adjacent pairs:

| Measure | Value |
|---|---|
| Members with at least one adjacent PageRank tie in the top 15 | 226 of 515 (43.9%) |
| Adjacent pairs tied on published PageRank | 612 of 7,205 (8.5%) |
| ... tied only because of six-digit rounding | 96 (15.7%) |
| ... genuinely equal at full float precision | 516 (84.3%) |
| Ties resolved by `co_tenure_degree` | **0** |
| Ties resolved by `node_id` | **612** |

It decides list membership, not just order. For the 85 members whose lists reproduce exactly from the raw node scores, **19 of 85 (22.4%)** have a rank-15/16 cut falling inside a tie group; mean tie-group size at the cut is 8.8, maximum 26. Member `B001319` has a 10-person tie group spanning ranks 11–20, all at `co_tenure_degree = 59` and one identical full-precision PageRank; five are published and five are dropped purely on sha256 order.

Raising `SIGNIFICANT_DIGITS` would fix 5 of the 19 boundary cases and 96 of 612 ordering cases, and would break the "reproducible from the emitted fields" property that the rounding exists to protect. Rounding is not the real issue.

---

## 5. Concentration census

The owner's stated concern was that certain people hold outsized weight for trivial reasons. The concern is **real**. The mechanism is not the one the open rulings address.

### 5.1 Container size is not the driver

| Measure | Top 100 | All scored |
|---|---|---|
| Median size of primary container | 167 | 154 |
| Share of strength from containers over 200 people | **15.01%** | **56.64%** |
| Median distinct containers | **18** | **1** |

Spearman correlation between PageRank and primary container size is **0.126**. The top 100 draw *less* of their strength from large containers than the population does — the inverse of the size hypothesis. The driver is **breadth**: many containers, not big ones.

Container size distribution over the 1,779 eligible containers: minimum 1, p25 34, median 66, mean 94.0, p90 192, p99 459, maximum 1,038. Cumulatively, the largest 1% of containers (18 of them) supply 21.65% of pairs; the largest 10% supply 57.05%.

### 5.2 The driver is SHARED EMPLOYEE

Top 100 by PageRank at α = 0.85, cross-tabbed by the title on the stint in their largest-strength container:

| Title | Count |
|---|---|
| SHARED EMPLOYEE | 64 |
| SHARED EMPLOYEE (OTHER COMPENSATION) | 5 |
| Financial administrator / finance assistant | 6 |
| System administrator / IT director | 5 |
| PART-TIME EMPLOYEE | 2 |
| Genuine senior staff (Chief of Staff, Legislative Director, Counsel, Staff Director) | ~14 |

**99 of the top 100 have held a SHARED EMPLOYEE title, against 1.06% of the 130,273 scored population — a 94× enrichment.**

Ranks 1 through 4 are Thomas E. Anfinson (degree 4,321 across 78 containers), Susan Anfinson (3,777 across 76), Michelle M. Donches (2,053 across 28) and T E. Anfinson (2,103 across 53). Imran Awan and Abid A. Awan hold ranks 36 and 53.

Maximum degree is 4,321, but that person's largest container holds only 208 people — the degree is accumulated across 78 containers. That is the breadth signature, not a large-pool signature. 74 people exceed degree 1,000; 14 exceed 2,000.

Enrichment decays sharply with depth, so the pathology is confined to roughly the top 1,000 to 2,500:

| Top N | Ever SHARED EMPLOYEE | Enrichment | Median containers |
|---|---|---|---|
| 50 | 100% | 94.3× | 20 |
| 100 | 99% | 93.4× | 18 |
| 250 | 65% | 61.1× | 8 |
| 1,000 | 29% | 27.0× | 2 |
| 10,000 | 8% | 7.2× | 1 |
| 130,273 | 1% | 1.0× | 1 |

**This reaches the shipped page.** The 2026-09-07 SHARED EMPLOYEE exclusion is scoped to the per-member `top_staff` list only. `global.top_bridge_people` sorts purely on distinct member-office count (`build_staffer_network_section.py:1434-1437`) with no title exclusion, and it is the only per-person ranked list that survives render. Kathryn J. Doherty (130 offices), Nina E. Doorley (121), Anthony G. Flynn (119) and both Anfinsons appear on it.

### 5.3 Intern pools

**244 containers named `INTERN COMPENSATION - <SENATOR>`**, all typed `member_office`, all carrying **kappa = 1.00** — the same coefficient as a real member office. They hold 11,545 people and supply 116,760 pairs (2.505% of edges, 2.555% of weight). 114,289 of those pairs have an intern pool as their only source. **9,685 people draw their largest strength from an intern pool.** The largest are Schumer 328, Feinstein 284, Warner 276, Blumenthal 276, Gillibrand 244.

Structurally these are payroll headers wearing a `member_office` label. The `{admin}` exclusion caught the genuine paymasters — Office of Congressional Accessibility Services (3,372), Chief Administrative Officer of the House (2,551), Sergeant at Arms and Doorkeeper (2,059), Resolution and Reorganization Reserve (1,555), Clerk of the House (1,118) — but not these.

Negative control: removing every intern-pool edge scrambles the middle of the distribution (Spearman 0.873) while leaving **all 100** of the current top 100 in place. Intern pools are a separate defect from the shared-employee one, and they move the middle rather than the top.

`unresolved` containers are a non-issue: 34 containers, 494 people, and only 360 people (0.28% of scored) have one as their largest strength source.

### 5.4 Counterfactuals

Each variant recomputes PageRank from the emitted edge file with modified weights.

| Variant | Spearman | Top 100 kept | Top 1000 kept | Median move | New top 100 still shared |
|---|---|---|---|---|---|
| D1a size norm `w/(n−1)` | 0.93854 | 92/100 | 629/1000 | 5,530 | **100%** |
| D1b size norm `w/√(n−1)` | 0.98385 | 95/100 | 806/1000 | 2,836 | **99%** |
| D2a decay H = 5y | 0.89911 | 87/100 | 745/1000 | 9,967 | 95% |
| D2b decay H = 10y | 0.96740 | 95/100 | 841/1000 | 5,481 | 97% |
| D3 kappa_min | 0.99998 | 99/100 | 992/1000 | 10 | 98% |
| D4 sqrt + 10y | 0.95509 | 95/100 | 762/1000 | 5,896 | 99% |
| **F drop shared-employee edges** | **0.99086** | **9/100** | 781/1000 | **620** | **14%** |
| X1 drop intern-pool edges | 0.87273 | 100/100 | 989/1000 | 7,220 | 100% |

**D1 is wrong-signed and should be rejected on its own evidence.** Its largest fallers are real senior committee staff — Staff Director (Foreign Affairs), Chief Counsel and Senior Counsel (Energy and Commerce), Minority Professional Staff (Appropriations), Cloakroom Floor Director (Speaker's office). Its largest risers sit in 2-, 3-, 10- and 16-person containers, including `INTERN COMPENSATION - OSSOFF` (2 people) and `INTERN COMPENSATION - HYDE-SMITH` (3 people), whose stint titles read "INTERN FROM JUL. 5 TO JUL. 28". Size normalization does not demote pool-sitters; it promotes them.

**D3 is a near no-op by construction, not by choice.** Only 9,380 edges (0.201%, 0.235% of weight) have `kappa_min ≠ kappa_max`, because committee side is UNKNOWN almost everywhere.

**D2 is a defensible recency question but not this fix.** Median age of a last co-tenure day is 5.99 years (p90 14.1, maximum 17.9), so H = 5y is aggressive and H = 10y mild. It demotes shared employees and real staff alike.

**F is the only variant that removes the pathology, and it is also the cheapest in collateral.** Only 182 people become isolates, all of them people whose every payroll cell is a shared cell. 1,199 of the 1,381 shared employees remain in the graph with their non-shared work intact (mean degree 315 → 118). Non-shared persons barely move (mean degree 68.9 → 67.1). The resulting top 20 reads: Oversight Director and Communications Director (Homeland Security), Republican Staff Director and Democratic Director of Legislation (Oversight), Chief Investigative Counsel (Energy and Commerce), subcommittee directors and counsel, and four Chiefs of Staff.

---

## 6. Owner rulings, 2026-09-08

The following were ruled by Paul on 2026-09-08 and are binding on this lane.

### R-1 — `office_diversity` becomes days-proportional

> "The time matters more than the breadth, remember we are thinking about connections."

The equal split at `:634-642` is replaced by a days-proportional split. A container's share of an edge's mass becomes the share of guaranteed days it actually supplied, not `1/counts`. The rationale is that the field exists to describe connection strength, and a three-day detail is not a connection comparable to a three-thousand-day tenure.

Affects 98,539 edges (2.1144%); the remaining 97.9% are unchanged by construction.

### R-2 — the tie-break becomes relative to the outreach

> "For tie breakers we should consider the person who is going to be reaching out and their connectivity relative to the target and other things as a tie-breaker."

The inert `co_tenure_degree` key is replaced. The tie-break is no longer a global property of the tied person; it is a property of the tied person *relative to the outreach being contemplated* — the connectivity between the person reaching out, the candidate, and the target.

This has two contexts with different available information, and the design must cover both:

- **Static per-member surfaces** (`top_staff`), where no origin exists at build time. The natural relative anchor is the member whose page it is. Consistent with R-1, the key should be time-weighted connection to that member's office rather than a count.
- **Interactive surfaces** (the 8841 sidecar), where origin and target are both supplied as query parameters and a routing engine already exists. Here a genuinely query-relative key is available.

`node_id` is retained as the final deterministic key only, never as a load-bearing one.

Detailed design pending; see §7.

### R-3 — intern pools are excluded

> "Fuck the interns, get irrelevant."

The 244 `INTERN COMPENSATION - <SENATOR>` containers are excluded from the co-tenure operator. They are payroll headers, not workplaces, and their `member_office` typing at kappa 1.00 is a misclassification.

Expected effect from the X1 control: Spearman 0.873 against the current ranking, all of the current top 100 retained, 989 of the top 1000 retained. This moves the middle of the distribution, which is the intended correction.

### R-4 — the exclusions apply to `top_bridge_people`

The shared-employee and intern-pool exclusions are extended to `global.top_bridge_people`, which currently applies no title exclusion and is the only per-person ranked list that survives render.

### R-5 — F is applied as a soft cap, not a deletion

Shared-employee edges are damped rather than dropped. The damping parameter is not yet chosen; it will be selected on measured evidence against the F deletion result as the reference point (14% shared share in the top 100, Spearman 0.99086, median move 620).

---

## 7. Open items

1. **Soft-cap parameter for R-5.** A sweep over damping factors is required, targeting the F deletion outcome without its collateral. Not yet run.
2. **Tie-break design for R-2.** The static and interactive cases need concrete key definitions and a check that the static key is not itself inert. `raw_strength` restricted to the member's own container is the leading candidate for the static case.
3. **Recompute scope.** All counterfactuals to date recompute PageRank only. Eigenvector centrality, `office_diversity` and the section surfaces have not been recomputed under any variant.
4. **The ranking does not currently reach the page.** `run_pipeline.py:235` renders with `--sdata provenance`, and `make_staffer_network_html.py:161-169` empties `members`. The 4.99 MB `staffer_network_section.json` — 515 members by up to 15 ranked staff — is built every chain run and discarded at render. Whether that is intended or a regression is undecided.
5. **Staleness guard mismatch.** `make_combined.py:170-172` guards `staffer_network_section.json` and the `_00` template, while the shipped panel is built from `_01` plus the three groups artifacts. The guard can pass green over a stale panel.
6. **Renderer default.** `make_staffer_network_html.py:77` defaults to the `_00` template, so any bare run silently reverts the shipped page.
7. **Stale score notes.** `build_staffer_network_section.py:1764` and `:1767` ship v5-era descriptions that are false for v6 — they describe a heterogeneous graph and equal restart mass per node kind, neither of which is true now.
8. **Possible identity duplication at the top.** `Thomas E. Anfinson` exists as three separate spine persons, and `T E. Anfinson` (payee_raw `ANFINSON, T E.`) is plausibly the same human as the 78-office record. Those two hold ranks 1 and 4. This is an identity question, not a ranking-math one, and has not been adjudicated.
9. **Stale generation names in handoff docs.** `STAFFER_SOCIAL_NETWORK_USAGE_HANDOFF_20260904.md` and `NEXT_STEPS_20260905.md` quote v5 generation names against the live v6, which is a copy-paste hazard if their commands are run verbatim.

---

## 8. Standing exposure

The entire staffer network — `fec\staffer_network\`, `audits\staffer_network\` and every producer — is untracked in git, on a single disk, in a tree that OneDrive stopped syncing around 2026-08-11. The 582 MB edge file and the 61 MB identity SQLite database are not recoverable from any mirror. Nothing in this document changes that, but it is the standing exposure behind every number in it.
