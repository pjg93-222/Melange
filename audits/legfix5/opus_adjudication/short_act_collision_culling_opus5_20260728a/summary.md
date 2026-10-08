# Opus 5 short-act-collision culling proposal — 454 exact membership edges

Run id: `short_act_collision_culling_opus5_20260728a`
Adjudicator: Opus 5 (`claude-opus-5`), max effort, local evidence only.
Status: **culling proposal. Nothing integrated, promoted, scored, or ranked.**
Every row requires human ratification.

## What this lane adjudicated

454 `(canonical_key, query_id)` membership edges whose original short-act /
title-alias provenance was stripped by a legacy rollup. All 454 are class-b
orphans: the edge exists in the ledger, but the only thing that ever supplied it
was a **stemmed** short-act probe. Stemming is what did the damage — `AFFORD
Act` matched *afford·ability*, `SUPPLY Act` matched *water supply*, `SMART Act`
matched fifteen unrelated acts sharing the acronym.

## Coverage — proven, not asserted

| quantity | value |
|---|---|
| source of truth | `audits/legfix5/orphan_edge_classification_2026-07-27.ndjson` |
| source edge rows / unique | 454 / 454 |
| proposal rows / unique | 454 / 454 |
| duplicates | 0 |
| exact set equality with source | true |
| bill edges (weight 1.0) | 423 |
| amendment edges (weight 0.5) | 31 |

**The sidecar holds 345 rows, not 454.** Its own `summary.json` decomposes the
population: `orphans_examined: 454` = `guard_already_fired: 109` +
`guard_silent_flagged_here: 345`. The sidecar restores provenance only for the
345 the ledger's short-act guard never fired on. The binding scope — "prove
exactly 454 … 423 bill edges and 31 amendment edges" — is satisfiable only from
the classification file, whose SHA-256 matches the sidecar's declared
`source_sha256`. All 454 canonical keys were located in the 18,557-line packet
file with zero missing and zero duplicates.

## Dispositions

| disposition | edges |
|---|---|
| `exclude_false_positive` | 417 |
| `flagged` | 30 |
| `include` | 7 |

By category:

| category | exclude | flagged | include |
|---|---|---|---|
| cdfi_fund | 170 | 5 | 0 |
| mortgage_lending_housing | 117 | 21 | 0 |
| examination_supervision | 64 | 3 | 0 |
| technology_emerging_issues | 54 | 1 | 7 |
| fraud_prevention | 12 | 0 | 0 |

## The 7 includes — all Technology & Emerging Issues

Affirmative nexus found in the measure's own operative text:

- `117:hr:3962`, `118:hr:1059` — **SECURE Notarization Act** (2022, 2023). This
  is the category's own named bill in earlier Congresses. Operative text
  authorises electronic and remote notarization and compels Federal/State
  recognition; *remote online notarization* is an enumerated boundary term. High
  confidence. Here the "collision" was not a collision — the probe found the real
  thing.
- `116:hr:8378`, `117:hr:4451`, `118:hr:3572`, `119:hr:2365` — **Securities
  Clarity Act**. Operative text carves investment contract assets out of the
  security definition, addressed on its face to digital assets raised through
  blockchain-based protocols. Medium confidence: core digital-asset market
  structure, but not a named bill and no credit-union-specific provision.
- `117:hr:5082` — **Cryptocurrency Tax Clarity Act**. Amends IRC §6045 to define
  digital assets and treat them as specified securities for broker reporting.
  The regulated instrument is the digital asset itself. Medium confidence.

## The 30 flagged — three distinct blockers

**16 — `no_own_operative_amendment_text`.** Amendment edges with no operative
amendment text and no floor remarks on the original-method surface
(`house_sponsor_block_not_found`, `senate_body_unbounded_*`). Rule 7 bars using
the parent bill, so neither include nor exclude is available. Absence is neutral.

**7 — `operative_text_review_incomplete`.** Bills that cannot certify a complete
all-version operative-text review: `119:hr:7147` (evidence text exceeded the
packet ceiling), `118:hr:7324`, `119:hr:5185`, `117:hr:5695`, `118:hr:3496`,
`119:hr:4584` (no declared official text version), `119:hr:998` (7 declared
versions, not all reviewed). Exclusion is withheld rather than asserted.

**7 — `category_boundary_unresolved`.** A genuine boundary question reserved to
the human ratifier, not an evidence gap:

- `117:hr:9522`, `118:hr:6948`, `119:hr:5077` — Strengthening Housing Supply Act
  (2022/2024/2025). Single operative section making affordable housing
  construction an eligible CDBG activity.
- `119:hr:4659`, `119:s:2416` — Identifying Regulatory Barriers to Housing Supply
  Act. CDBG grantee land-use plans, expressly covering accessory dwelling units.
- `119:hr:8185` — HELP Act of 2026. Eviction database, eviction-prevention
  grants, housing-court records in consumer reports.
- `118:hr:6307` — CLARITY Act of 2023. Bans Federal acquisition of foreign
  adversary distributed-ledger/blockchain equipment.

The first six turn on one unresolved question: the category is labelled
**Mortgage Lending & Housing**, but every one of its boundary terms and all three
named bills are mortgage-*credit*. Housing production, land use, and eviction sit
inside the label and outside the terms. `118:hr:6307`'s primary subject genuinely
is an enumerated emerging technology, but the policy domain is national-security
procurement. In all seven, neither the include test nor the exclude test is
affirmatively met, so the edge stays flagged.

## Method actually applied

1. The decision unit was the exact `(canonical_key, query_id)` edge. Several
   candidates are plainly relevant to *some* ACU category while being false
   positives for *this* one — the FHA Loan Affordability Act is a real mortgage
   bill and still a CDFI-Fund false positive; the NFIP Reauthorization and Reform
   Act is squarely a mortgage/flood measure and still an Examination &
   Supervision false positive. No other edge for any candidate was touched.
2. The stemmed alias was recorded as provenance and never used as evidence.
3. Disposition came from official title, official summary where published, and
   operative text, read against the category's own boundary as drawn in
   `category_method_registry.json`.
4. Include required affirmative nexus; exclude required affirmative evidence of
   an out-of-category operative effect. Term *absence* was never treated as
   negative evidence.
5. Parent and neighbouring memberships transferred nothing.
6. The 31 amendment edges were adjudicated on the amendment's own operative
   effect only. The 15 with text proved to insert Montana/North Dakota rural
   water supply, Bureau of Reclamation infrastructure, Colorado River
   appropriations, the INTERPOL-abuse TRAP Act, pharmaceutical supply-chain
   mapping (MAPS Act), DHS WMD/health-security offices, and beneficial-ownership
   access — none within their claimed category.

## Cross-run identity for the 31 amendment edges

All 31 matched `amendment_content_v2.ndjson` (3,703 records, SHA-256 bound in the
receipt). Each amendment row carries `amendment_partition_identity` with the
partition name, source, record count, and dedupe key. **Reconcile on
`(canonical_key, query_id)`** so an edge appearing in both this population and
the 3,703-amendment partition is counted once. Weight stays fixed at 0.5.

## Confidence

| disposition | high | medium | no claim |
|---|---|---|---|
| `exclude_false_positive` | 381 | 36 | — |
| `include` | 2 | 5 | — |
| `flagged` | — | 7 (boundary) | 23 |

The 36 medium excludes are the edges whose CRS summary is unsettled
(`available_pending_congress_gov_fetch`); operative-text review was still
complete for each, so the exclusion rests on affirmative text evidence and
summary absence stays neutral. The 23 no-claim flags are the evidence-absent and
review-incomplete blockers, which carry no confidence claim by construction.

## What was not done

`integration_performed: false` · `production_write_performed: false` ·
`scoring_performed: false` · `rank_recompute_performed: false`

No junk ledger, no `manual_bill_evidence.csv`, no workbook, no discovery corpus,
no packet, no sidecar, no membership review ledger. Every binding input is
re-hashed in `receipt.json` and unmodified. No network access; no semantic
decision delegated.
