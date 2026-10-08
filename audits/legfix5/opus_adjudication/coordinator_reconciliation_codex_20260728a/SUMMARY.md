# Culling reconciliation — pre-Integration decision gate

**Status: DECISION REQUIRED. No integration, scoring, or rank recomputation was performed.**

## Complete accounting

- Amendments: 3,703 = 60 include + 2,503 false-positive exclude + 1,140 held.
- Short-act collision edges: 454 = 7 include + 417 false-positive exclude + 30 held.
- Bill recall: 465 legacy rows = 442 already covered + 23 adjudicated; the 23 = 6 include + 2 false-positive exclude + 15 held.
- Quorum recall: 44/44 already covered in discovery.

## Reconciled pre-Integration change set

- 2,981 proposal rows: 73 include actions and 2,908 exclusion actions.
- 93 category-membership edges are proposed by the 73 includes.
- Fourteen short-act amendment exclusions were removed as redundant with candidate-level amendment exclusions.
- `118:samdt:1084`: the exact official-purpose exclusion controls.
- `119:samdt:5869`: only its Technology edge is excluded; its separate Examination hold remains.

## Adversarial bill-recall review

- Six full agreements, three BNPL category-only disagreements, and fourteen disposition disagreements.
- Independent official-source review resolved subject matter but not the governing material-credit-union-nexus or all-version closure questions.
- Fail-closed result: preserve the Opus 6/2/15 partition, omit BNPL from Payments, and assign no scoring direction.

## Held for ratification

- 1,184 unresolved decision units across 1,169 unique candidates.
- Held rows remain visible and non-scoring; they are not silently discarded.

## Method

Operative text and official purpose/title/summary control. Floor speech is retained as context, not as a transfer of the parent bill's relevance. Exact press and letter evidence can corroborate direction; missing text or summary is neutral. Bills carry weight 1.0 and amendments 0.5.

## Rank delta

Not computed before Integration. A defensible legislative rank delta requires the greenlit accepted ledger and a clean paired shadow recomputation.
