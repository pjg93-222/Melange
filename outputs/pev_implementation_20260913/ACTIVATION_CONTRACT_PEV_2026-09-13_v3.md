# PEV implementation and activation contract, version 3

Date: 2026-09-13. Current instruction: “Then adjust and make as optimal as possible,” following the review of Primacy → Efficiency → Volume. This specification replaces the proposed 80/20 delivery blend for this candidate. It preserves the historical record and makes no claim of empirically optimal calibration.

The implementation is an isolated, executable scoring package. It creates a candidate board and its supporting evidence; it does not silently change the production board, official reporting weights, or member labels.

## Decision rule

Use the current full-precision, evidence-adjusted `factor_ranked` as P. Preserve the source board's rankable membership and established constraints. Sort the analytical candidate by:

1. P descending.
2. At identical P, an observed E precedes unavailable E; then E descending.
3. At identical observed E, beneficial V descending.
4. Bioguide identity ascending for a stable final tie.

E is the within-chamber percentile of the reliability-adjusted observed conversion rate. The source percentile convention is share strictly below divided by n−1, truncated to five decimals; one observed peer receives zero. Peers are all available historical roster records in that chamber, not just today's displayed members. Unavailable records are excluded from percentile denominators and their coverage is shown.

When E is unavailable, V cannot rescue it or imply a known rate. Two equally primacy-ranked unavailable records use identity for their final tie. A higher P with unavailable E still outranks a lower P with known E: missingness does not replace the primary objective. No fabricated maximum or zero E is introduced.

Exact P ordering means E/V affect only P ties. This is intentional. Meaningful primacy bands would be a different policy and must not be chosen by inspecting which named members they seat.

## Efficiency definition

Policy ID: `primacy_efficiency_volume_v1`.

- Observation horizon: **180 days after the first verified join**, inclusive of the endpoint. This is an explicit candidate setting, not a consequence of the old cosponsor half-life or a fitted optimum.
- One opportunity: one distinct member–measure with consistent accepted positive `tensor_cu`, a law-capable eligible measure, verified chronology, and sufficient dated service.
- One success: any observed legislative milestone above the highest milestone attained strictly before joining, reached during the observation window while the member holds an active role and is in service.
- Advancement stages: AIC, ABC, PASS, LAW. BILL establishes the attempt; introduction alone is not conversion. Stage-specific rates remain visible diagnostics rather than a second hidden weighted score.
- Full window: the entire horizon must fit before Congress ends, within continuous dated service, and through the requested as-of date. The bill snapshot must cover the horizon. Early successes and unresolved attempts face the identical maturity test.
- Withdrawals remain in the denominator. Success while withdrawn is not credited. Rejoining neither resets the clock nor creates another attempt. Same-day join qualifies; same-day withdrawal does not.
- Unknown, inconsistent, or missing alignment, chronology, or mature milestone coverage is not failure. Any such accepted scope makes the member's ranking E unavailable while retaining observed counts for inspection. Immature windows are separately excluded and counted.
- Raw rate: successful unique opportunities / fully observed unique opportunities. Zero opportunities means unavailable.
- Evidence adjustment: the Wilson lower endpoint with fixed `z=1.96`, then within-chamber percentile. Counts are unweighted distinct opportunities; fractional role credits are not passed off as independent binomial trials. Sponsor, original-cosponsor and later-cosponsor diagnostics are retained.

The Wilson formula is a conventional proportion method, documented by [NIST](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm). Its use here is a descriptive reliability policy. Legislative measures are dependent and the accepted alignment selection is retrospective; this implementation does not claim a validated 95% prediction interval, causal effect, or future success probability.

This measures conversion to further progress, not economic value or lobbying return per dollar. Enactment and other stage outcomes remain inspectable. A different definition of outcome value requires a separately versioned policy.

## Useful volume and substance

V counts distinct verified positive-CU law-capable member–measure engagements. Repeated stages, categories, episodes and signal rows do not increase V. Neutral and harmful accepted scopes have separate counters; missing evidence is explicit. Non-law measures and undocumented letters remain excluded from law opportunities and separately counted.

No new publication attention bonus enters P/E/V. Existing provisional impact classifications are not recalibrated. The revised collector contract specifies how complete exposure, article versions, source families, and as-of evidence must be produced before any future substance policy can use them.

## Existing constraints and board identity

Use copied source helpers to apply the current policy in the same order: candidate order → explicit placements → CU-primary evidence floor → conduct ladder → 13/24/48 seats. The 0.75 CU-primary role-credit floor is distinct from P and from the formerly reported .556 observed minimum. Preserve the established explicit-placement exemptions.

The replay must first reproduce every displayed baseline member's tier and rank against the copied CU industry board. Preserve the baseline's usable reporting-Leg membership rule; do not substitute the old 352-person effectiveness cohort. Identity matches use Bioguide, with names checked for display consistency.

Audit final constraints after reseating. A helper returning successfully is insufficient evidence that its output satisfies the evidence floor and conduct ceilings. A failure leaves candidate tiers/ranks non-authoritative and appears in the receipt.

Congress 118 is the default completed-term comparison. Congress 119 is a separate diagnostic when requested. There is no unannounced cross-term pool. P and constraints are the frozen current baseline applied to historical conversion, not reconstructed historical P. The official blended reporting rank and its other pillars retain their existing meaning.

## Reproduction and output boundary

`src/pev.py` is pure, standard-library code. `src/replay_pev.py` reads the frozen canonical files and an explicit source root, snapshots policy/helpers, and writes only to a dedicated output directory. It refuses output paths that could overwrite source, frozen evidence, or code.

The generation contains the 533-member comparison when the source roster contains 533 members, a member–measure opportunity ledger, a searchable HTML review, a Markdown report, and a receipt with source and code hashes. Building and failed states cannot masquerade as a completed generation. Source changes during a run invalidate it.

Canonical consumed evidence includes bill milestones, member roles, accepted signals, dated population, and identity comparison. No network, publication sweep, source relabeling, workbook write, or allocation re-run is part of replay.

## Acceptance and production activation

The candidate must pass behavioral tests for priority order, missingness, chamber normalization, duplicate immunity, chronology, withdrawal, service gaps, observation maturity, input-order determinism, and invalid-schema rejection. Repeated replay from identical inputs must give the same scoring artifacts.

Before any production consumer changes, all of the following are required:

- Baseline tier/rank reproduction and final evidence/conduct checks pass on the full roster.
- The candidate's schema, policy ID, hashes, coverage and complete generation receipt are validated by consumers; missing generation inputs stop the update rather than invoke a preferential fallback.
- All movers are enumerated, with P, conversion numerator/denominator, reliability score, chamber percentile, V, coverage and constraint effects.
- Production wiring uses this tuple order directly. A scalar Leg% substitute, renormalization across missing axes, or 80/20 fallback is not equivalent.
- Kernel, full-chain, crown/exclusivity, source-contract, and audit checks run against the actual changed production integration. Reverting the selected policy must restore the frozen baseline artifacts byte-for-byte.

The standalone test/replay receipts establish the behavior of this implementation. They do not certify an unbuilt production integration or satisfy the full-chain gate by implication.
