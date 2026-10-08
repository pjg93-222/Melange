# Legislation downstream recomputation contract

No newly collected legislation may be synced to the production archive,
workbook, network, roll-call aggregate, rank authority, dashboard, member
desk, or mainframe until this contract passes.

## Canonical scoring identity

The sole scoring input is the accepted relationship ledger keyed by:

`(Congress, measure type, measure number, category, member Bioguide ID)`

Every discovered candidate and every excluded, unresolved, withdrawn, neutral,
or unmatched membership remains in an audit ledger. Only a ratified included
membership with a current official relationship and explicit direction may
score.

Relationship handling:

- `Sponsor + current` → Sponsor.
- `Cosponsor + current + original_cosponsor=true` → Original Cosponsor.
- `Cosponsor + current + original_cosponsor=false` → later Cosponsor.
- `Cosponsor + withdrawn` → visible audit record, zero score, zero network.

One member/measure/category contributes only its strongest active role.
Original cosponsorship must never also score as ordinary cosponsorship.

## Coverage gate

- Congress.gov Advanced Search is primary; Quorum is disregarded.
- All 62 registry searches must complete and page-reconcile exactly.
- Congresses 116–119 and all ten selected measure types must be present.
- Every named bill, identifier probe, historical recall, and trusted-article
  citation must be recovered or appear in an explicit gap ledger.
- Official title, summary, text, and provisions must resolve each proposed
  category membership.
- False-positive exclusions require affirmative evidence. Press-article
  absence is never evidence.
- Sponsor, Original Cosponsor, later Cosponsor, and withdrawn counts must
  reconcile to Congress.gov.

## Computation gate

- Decay is exactly 119=1.00, 118=.66, 117=.33, 116=.16.
- Measure identity is type-aware everywhere.
- Direction is explicit and provenance-bearing per measure/category.
- Existing consumer-specific role methods are preserved only through an
  explicit approved profile; no global role weight may be silently imposed.
- Legislative efficiency needs one approved success definition and an
  explicit mapping of 18 categories to the legacy 17-slot AG:AW surface.
- CU/CW letter units are recomputed from the hash-bound manual ledger under
  active decay; CV/CX are explicit zero; AV/DX are rebuilt from accepted bills
  under the approved success definition and declared precision.
- Workbook raw, normalized, sublayer, primary-layer, and blended values must
  rederive from the accepted generation with zero unexplained cells.
- Rank inputs must be generation-bound. A stale workbook cache or
  `pillar_inputs_snapshot.json` is prohibited.

## Preserved graph and rank method

Base edges:

- later cosponsor: `0.5 × decay / sqrt(current cosponsor count)`;
- original cosponsor: `1.0 × decay / sqrt(current cosponsor count)`.

Centrality:

```text
W = WeightedOutDegree / max(WeightedOutDegree)
B = Betweenness / max(Betweenness)
E = Eigenvector / max(Eigenvector)
raw = 0.60W + 0.25B + 0.15E
InfluenceScore = round(100 × raw / max(raw), 1)
```

The current rank method uses committee score E as the influence pillar; base
and augmented Centrality carry zero effective rank weight. That method remains
unchanged unless separately approved.

## Mandatory shadow order

1. Verify the immutable production baseline.
2. Build the accepted relationship generation.
3. Build direction, official roll-call, base-network, and policy artifacts.
4. Materialize archive/workbook inputs.
5. Aggregate official roll calls.
6. Build base network, Centrality, and pre-behavior bipartisanship.
7. Recompute behavior, dispositions, cooperation, and receptivity.
8. Recompute augmented network, stance, and say/do first pass.
9. Recompute all legislative workbook layers with `@oai/artifact-tool`.
10. Recompute pillars and ranks from the new evaluated workbook.
11. Recompute coalitions, flips, budgets, optimizer, allocation, dashboard,
    and member desk.
12. Run say/do second pass and all second-pass dependents.
13. Attribute every delta and repeat the identical run.

All 16 consumer stages must execute only inside the sealed shadow run and own
exact, non-overlapping output paths.

## Promotion gate

Promotion remains prohibited unless:

- coverage, review, relationships, and reconciliation pass;
- every excluded, unresolved, withdrawn, and neutral record contributes zero;
- every archive, workbook, roll-call, network, behavior, stance, pillar, and
  rank value reproduces from manifested inputs;
- both workbook runs use the approved spreadsheet engine and pass required
  sheet, formula-error, numeric-cell, and generation-hash checks;
- every delta is attributable to accepted evidence or an explicitly approved
  computation repair;
- the second run is semantically and byte-idempotent for deterministic
  artifacts; and
- the user explicitly approves the final pre-sync report.

Current machine-readable readiness:
`audits/legfix5/downstream_readiness/downstream_readiness.json`.
