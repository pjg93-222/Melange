# M1 adversarial math audit — 2026-09-01

## Verdict

**PASS after one fail-closed temporal fix.** Structural graph math matches the 2026-08-31 adjudication. Temporal overlap, duration, ordered-transition, unique-person, and decay math also match after correcting one valid-schema `INTERVAL_BLOCKED` revolving-path crash. No identity merge, canonical promotion, composite influence score, or temporal edge was introduced by this audit.

Focused post-integration command:

```text
python -m pytest -q \
  fec/tests/staffer_network/test_staffer_canonical_graph.py \
  fec/tests/staffer_network/test_staffer_employment_history.py \
  fec/tests/staffer_network/test_staffer_intervals.py
```

Result: **43 passed** in 1.07 seconds: 7 graph, 33 employment-history, and 3 interval tests. Python compilation of all four reviewed modules also passed.

## Structural graph findings

1. **Support dedup is live and non-additive.** The scoring key is unordered endpoints plus layer,
   `k = ({min(i,j), max(i,j)}, l)`, and the retained weight is
   `w_k = max_e w_e`. Probe inputs `(0,1,.4,l2)`, `(1,0,.8,l2)`, `(0,1,.6,l2)`, `(0,1,1,l3)` produced only `(0,1,.8,l2)` and `(0,1,1,l3)`. `graph_build.py` calls this before both primary and exploratory transitions and reports the excluded count.
2. **Noisy-OR is not live.** `network_math.py` implements
   `s = 1 - product_q(1 - max_r s[q,r])`; the probe `a:.4,a:.7,b:.5` gives `.85`. `graph_build.py` neither imports nor calls the combiner. Current canonical facts carry direct structural weight `1.0`, followed by max dedup.
3. **Equal-active-layer transitions are exact.** For each node,
   `P[i,j] += |L_i|^-1 * w[i,j,l] / sum_k w[i,k,l]`.
   A two-layer probe produced row 0 `[0,.25,.25,.5,0]`; every non-isolate row summed to 1 and the isolate row to 0.
4. **PageRank, dangling mass, teleport, and isolates are coherent.** The implemented equation is
   `r = alpha P.T r + alpha sum_d r_d v + (1-alpha)v`.
   With groups `[0,0,1,1,2]`, teleport was `[1/6,1/6,1/6,1/6,1/3]`. At `alpha=.85`, the independent fixed-point residual was `5.403e-13`; the isolate retained prior-shaped mass `0.06976744186` and is explicitly flagged for exclusion from ranked reads. Production runs `.70`, `.85`, and `.95`; `.85` is primary.
5. **Eigenvectors are component-local.** The operator is `A=(P+P.T)/2`; each non-isolate connected component is independently L1-normalized, isolates are zero, and nonconverged components become null. A two-edge-component plus isolate probe returned `[.5,.5]`, `[.5,.5]`, and `0`, with component sums `1,1,0`.
6. **Bridging matches normalized Simpson diversity:**
   `B_i = (1-sum_g p[i,g]^2)/(1-1/G)` on row-normalized transition mass. The transition probe returned node-0 `0.5625`; scalar tie-strength growth leaves its composition unchanged. The existing warning that feasible neighbor kinds differ by entity kind is necessary.

## Temporal findings

Uncertain episodes use half-open bounds. For episode `x`, the guaranteed core is `[start_latest, end_earliest)` and the possible envelope is `[start_earliest, end_latest)`. Ranges are unioned before intersection, so duplicates and adjacency do not double count. The probe union of duplicate `[2024-01-01,2024-01-10)` plus adjacent `[2024-01-10,2024-01-20)` was one 19-day range; two episodes meeting at the exclusive boundary had zero overlap.

Co-tenure uses
`w_lower = 1-exp(-G/tau)` and `w_upper = 1-exp(-P/tau)`, `tau=365.2425`. The one-tau probe was `0.6321205588285577`. Possible-only overlap has primary weight zero, and pair-level calendars are unioned across containers before conversion.

Hill-to-industry ordering is:

```text
GUARANTEED    iff hill.end_latest   <= industry.start_earliest
POSSIBLE      iff hill.end_earliest <= industry.start_latest
gap_min = max(0, industry.start_earliest - hill.end_latest)
gap_max = max(0, industry.start_latest   - hill.end_earliest)
```

The Gordon fixture remains `GUARANTEED` with `[211,241]` days. Each person contributes at most once to a member/organization/predicate edge. Primary weight is the unique adjudicated-person count. Gap sensitivity remains
`d_lower=2^(-gap_max/730.485)` and `d_upper=2^(-gap_min/730.485)`, only for guaranteed paths. Registrant employment and client-activity participation remain separate predicates.

## Resolved blocker and counterexample

Before the fix, the temporal sidecar admitted `ACTIVE` episodes with accepted person and container decisions even when one ordering boundary was null. `transition_gap_bounds` correctly returned `("INTERVAL_BLOCKED", None, None)`, but candidate selection partitioned only `GUARANTEED`, `POSSIBLE_ONLY`, and `WRONG_ORDER`, then evaluated `min([])`. A valid-schema pair consisting of an accepted Hill episode with an unknown end and an accepted dated registrant episode reproduced:

```text
ValueError: min() iterable argument is empty
```

The minimal correction:

- retains one deterministic `INTERVAL_BLOCKED` review path;
- gives blocked candidates precedence over `WRONG_ORDER` when no guaranteed or possible pair exists, because an unknown pair cannot be dismissed as wrong-order;
- emits null `gap_min_days`/`gap_max_days`, `primary_weight=0`, and `possible_weight=0`;
- excludes the path from revolving-edge aggregation;
- adds an explicit conserved `INTERVAL_BLOCKED` receipt count;
- validates that blocked paths cannot carry gap bounds or temporal weight.

The independent post-fix reproduction returned:

```json
{"paths":[["INTERVAL_BLOCKED",null,null,0.0,0.0]],"revolving_edges":0,"status_counts":{"GUARANTEED":0,"INTERVAL_BLOCKED":1,"POSSIBLE_ONLY":0,"WRONG_ORDER":0}}
```

## Final reviewed hashes

| File | Bytes | SHA-256 |
|---|---:|---|
| `STAFFER_NETWORK_MATH_ADJUDICATION_20260831.md` | 5,934 | `0d366206ef43fd252d1c893f7b74270e1f8412d2a357518a5fefda7b77108ead` |
| `fec/staffer_network/network_math.py` | 13,666 | `52253220adc2fde4f0a6c8c28dd260892fa43e75d451f588e0fb24d3b8664c83` |
| `fec/staffer_network/graph_build.py` | 21,450 | `bbfe5530832c895151b5d2dcdd31b50fb9e246f1c6cce64ff420c4a7a19ec14f` |
| `fec/staffer_network/employment_history.py` | 87,709 | `1add7ddbaf1be16fcd336af7f4f0e84e11b5f070c8fa7a33428fd48667484447` |
| `fec/staffer_network/publication.py` | 74,370 | `84ab032b0896373887fd42cf1f539b0c19458044aa7d18efd4aeb22691a49b9f` |
| `fec/staffer_network/schemas/temporal_path.schema.json` | 2,461 | `8b62f48ab5cf3977980b7a322cb51c5ba74c4d5d31cb31723142636079c9b885` |
| `fec/staffer_network/schemas/temporal_build_receipt.schema.json` | 2,947 | `7e80e2f4e1305ba6f1f369113280c8ddfdf17fb0da67ca5a848de3b029749500` |
| `fec/tests/staffer_network/test_staffer_canonical_graph.py` | 15,287 | `4741a0031c6e6331476ce78cd79c4f4223d1432dcffded5b81420dfa9f4ab927` |
| `fec/tests/staffer_network/test_staffer_employment_history.py` | 47,856 | `cdc4ccf86422ef968edfe2b197d83307f4da23dfab647dfc1e15da270ab49862` |
| `fec/tests/staffer_network/test_staffer_intervals.py` | 1,519 | `ec7da50e74e3639070ee67ae4b5d9fddfc2682c96a095079c4a8ff8f86109dd1` |

The pre-fix pinned `employment_history.py` hash was `7f0c20b3564a6faa42bf7539299170015ae1964880b0a4f2a3406d59a8e6c1e7`. The final shared-file hash also includes the separately coordinated top-of-file date-order audit changes; the M1 temporal change is confined to lower revolving selection/weight/receipt logic.
