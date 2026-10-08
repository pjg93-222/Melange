# Opus 5 final adversarial review: network and temporal math

Use Claude Opus 5 at maximum effort. Read-only review; do not edit. You may use
`sha256sum` only to verify the following file pins.

| File | SHA-256 |
|---|---|
| `STAFFER_NETWORK_MATH_ADJUDICATION_20260831.md` | `0d366206ef43fd252d1c893f7b74270e1f8412d2a357518a5fefda7b77108ead` |
| `fec/staffer_network/network_math.py` | `52253220adc2fde4f0a6c8c28dd260892fa43e75d451f588e0fb24d3b8664c83` |
| `fec/staffer_network/graph_build.py` | `bbfe5530832c895151b5d2dcdd31b50fb9e246f1c6cce64ff420c4a7a19ec14f` |
| `fec/staffer_network/employment_history.py` | `1add7ddbaf1be16fcd336af7f4f0e84e11b5f070c8fa7a33428fd48667484447` |
| `fec/staffer_network/publication.py` | `84ab032b0896373887fd42cf1f539b0c19458044aa7d18efd4aeb22691a49b9f` |
| `fec/staffer_network/schemas/temporal_build_receipt.schema.json` | `7e80e2f4e1305ba6f1f369113280c8ddfdf17fb0da67ca5a848de3b029749500` |
| `fec/tests/staffer_network/test_staffer_canonical_graph.py` | `4741a0031c6e6331476ce78cd79c4f4223d1432dcffded5b81420dfa9f4ab927` |
| `fec/tests/staffer_network/test_staffer_employment_history.py` | `cdc4ccf86422ef968edfe2b197d83307f4da23dfab647dfc1e15da270ab49862` |
| `audits/staffer_network/M1_MATH_ADVERSARIAL_AUDIT_20260901.md` | `0d6eb3dd36874946b8e330a9e6dfbbb2ce3b9536e2cc0e7a063bd44749ad5354` |

Adversarially verify:

1. Current structural edge support is unit weight with maximum deduplication
   per unordered endpoint/layer; tested noisy-OR is not wired into production
   and is not an identity probability.
2. Equal-active-layer transition allocation, within-layer proportional
   allocation, PageRank alpha and dangling-mass handling, entity-kind-balanced
   teleport, and isolate treatment are mathematically coherent.
3. Eigenvectors are computed on the symmetrized graph per connected component,
   normalized only within component, and never globally compared.
4. Bridging is a separate normalized Simpson-diversity diagnostic and is not
   mislabeled strength, centrality, access, or causal influence.
5. Co-tenure uses half-open uncertain intervals, union-before-overlap,
   guaranteed/possible lower and upper bounds, and the declared duration
   transform without repeated-observation multiplication.
6. Revolving-door paths require accepted identity/container and guaranteed
   Hill-before-industry ordering; primary edge weight counts unique people;
   gap decay is sensitivity only.
7. Re-test the M1 fix: an accepted pair with an unknown necessary interval
   bound must yield an explicit `INTERVAL_BLOCKED` zero-weight path, null gap
   bounds, conserved receipt count, and no temporal edge—not a crash and not a
   wrong-order inference.
8. Look for double counting, inverted bounds, mass leakage, component-scale
   misuse, zero/NaN divisions, and any prose that overstates descriptive
   connectedness as influence or causation.

Measured local evidence: 203 tests plus 73 subtests passed across the full
staffer suite and A7–A9 integration; M1 focused verification passed 43 tests.

Return exactly:

- `VERDICT: PASS` or `VERDICT: BLOCKED`
- `BLOCKERS:` numbered code/prose discrepancies or `none`
- `NONBLOCKING_FINDINGS:`
- `EQUATION_CHECKS:` concise formula-by-formula disposition
- `EVIDENCE:` exact file/line citations

Correct math does not authorize identity adjudication, canonical promotion,
temporal scoring over review candidates, causal labels, or Meta LOOP closure.
