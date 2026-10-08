# Activation contract v2: purity-anchored delivery mix for the primacy board and Leg%

Date: 2026-09-12. Supersedes `ACTIVATION_CONTRACT_2026-09-12.md` (v1, results-only basis) in full. Status: DRAFT for Codex dispatch after the 2026-09-17 quota reset. Authority: D-028 (board = P × (0.80 + 0.20 × L); Leg% = L) and D-027 (success, amount and substance are within-chamber percentiles). D-026 is superseded.

Nothing in this contract is active today. The lane code sits in the live tree (applied 2026-09-11, kernel 187/4) with every candidate path opt-in; the numbers Paul ruled on come from `evidence/CHAMPION_SHARE_AND_FLOOR_SWEEP.md` (f = 0.80 table) and `evidence/COMPOSITE_BOARDS_118.md`.

## Definitions (binding)

- P: the orientation factor already published as `factor_ranked` in `data/engine/primacy_factors.json`. Unchanged.
- S (success): within-chamber percentile of the signed five-stage results (`results_only_leg_percentile` in the comparison artifact).
- A (amount): within-chamber percentile of `distinct_signed_measures` among members with at least one signed CU measure; members with none get A = 0.
- B (substance): within-chamber percentile of impact-weighted signed advocacy (`impact_advocacy_percentile`); inert while every bill weighs 5, kept in the formula so SS calibration needs no formula change.
- L (delivery) = 0.35 S + 0.35 A + 0.30 B. A member with zero signed CU measures has L = 0 (a real zero). A member whose term results are unavailable (denominators unavailable) has L unavailable, never 0.
- Percentiles use the repo `percentrank` convention (share strictly below over n − 1, truncated to 5 decimals, first-tie value), computed per Congress and per chamber.
- Board score = P × (0.80 + 0.20 × L). Reporting Leg% = L.

## OBJECTIVE

Make the CU primacy board rank on P × (0.80 + 0.20 × L) as a new versioned board mode `purity_delivery_v1`, and make the reporting rank's Leg% equal L, both produced by the chain from frozen local inputs, with the legacy policy kept as explicit revert dials that reproduce today's artifacts byte-identically.

## CONSTRAINTS (numbered; each binding)

1. Claude authors no code; every edit is Codex's, in a throwaway worktree, reviewed before Paul's gate. No git from Claude or agents in the Melange repo; Codex never commits.
2. Legacy stays selectable and byte-identical: `LEG_MODE=legacy` (default until Paul flips it) must make `compute_pillars.py --write` rewrite `ranks_python.json` byte-identical to today (0 of 533 moved); `PRIMACY_BOARD=factor` must leave `data/lobbying/industry_tiers.json` and `data/engine/primacy_factors.json` unchanged. Prove with hashes before and after, in the LIVE tree.
3. The board mode `purity_delivery_v1` is NEW; `factor`, `legxfactor` and `realized_results_v1` keep their current meaning. Its parameters (f = 0.80, weights 0.35/0.35/0.30) live in `pillar_policy.py` with a policy id and are recorded in every receipt and in `scoring_policy()`; they are not read from ad hoc environment variables.
4. Ranking inside the mode: sort by score descending, ties by P descending then name; seats 13/24/48; the evidence floor ("purity ranks, evidence qualifies"), explicit overrides and the conduct ladder are applied exactly as factor mode applies them today, in the same order. The distinct-measure gate of `realized_results_v1` is NOT applied to this mode (amount already carries it).
5. Unavailable is not zero. Where a member's L is unavailable for every scored term, the board uses P alone for that member with a receipted flag, and Leg% falls back to the legacy value with a receipted flag; the count of flagged members is printed and audited. No member is ranked on a fabricated L.
6. The 119th House universe: reserved bill numbers with no action history (the five records that make House denominators unavailable) are excluded by an explicit versioned rule in `build_bill_milestones.py` (`reserved_number_no_history`), reported in `effectiveness_universe_manifest.json` with measure ids, so current-term House denominators become available before activation.
7. Term basis for production: per-term L for the terms the roster served in (118 completed, 119 current as of the run date), combined with the existing decay convention (0.8^(119 − t)) only after term-level normalization, labeled in `pillar_policy.py`; the completed 118th term alone is the acceptance basis for the board listing in criterion 3.
8. Chain placement: a producer step runs the effectiveness build in production mode (as-of = run date, output under `data/engine/legislative_effectiveness/<generation>/`, receipt-gated, atomic generation directory) immediately before `compute_pillars.py --write` and before `primacy_factors.py`; consumers (`tier_util.py`, `industry_tiers.py`, `moneyball_core.primacy_engine_state`, the desk and dashboard builders) read the generation named in the receipt, never a hard-coded path. The chain stays network-free.
9. Crown law interaction: `tier == 1` under the active board mode is the crown; `champions_v2.py` and its two `audit_full.py` checks must keep passing with the new mode active (crown never on a threat board; cross-sector exclusivity).
10. Source contract: re-pin the six literals in `run_legislation_pillars_and_ranks.py` to the current `compute_pillars.py` text; never delete the tripwire.
11. Register the six lane suites plus every new suite in `run_tests.py` `_LANE_MODULES` (bare basenames).
12. `audit_full.py` gains a `[LEGEFF]` block: generation receipt complete, code hashes match the frozen list, active `leg_mode` and `board_mode` and their parameters recorded, denominators available for every scored term, every ranked member's L in [0, 1], flagged-unavailable count reported, and Tier 1 of the active board equal to the recomputed board from the generation.
13. Surfaces: member desk and dashboard show P, S, A, B and L beside the tier with the generation id; rankings-and-data only, no advisory copy; filenames stay Moneyball, visible text Melange.
14. Docs: MATHEMATICAL_SPECIFICATION.md and README describe the mix as a Melange adaptation (purity-anchored delivery), never as the paper's formula; D-026's results-only basis is recorded as rejected on sight.
15. Verification order for a rank-moving change (CONSTRAINTS, tooling): capture the full board and ranks hashes first; run the change in the live tree; enumerate every mover with P, S, A, B, L beside legacy values; revert dials prove byte-identity; `test_primacy_tier` re-pinned only by Paul after he ratifies the new board.

## ACCEPTANCE CRITERIA (observable)

1. `LEG_MODE=legacy` and `PRIMACY_BOARD=factor` in the live tree: `ranks_python.json`, `data/lobbying/industry_tiers.json`, `data/engine/primacy_factors.json` sha256 unchanged from the pre-run capture.
2. `LEG_MODE=delivery_blend_v1`: `ranks_python.json` rewritten; for every ranked member `pcts[m]['leg']` equals the generation's L to 5 decimals (533 of 533 checked by script; unavailable members listed with their legacy fallback and flag).
3. `PRIMACY_BOARD=purity_delivery_v1` on the 118th generation: Tier 1, in order, equals the f = 0.80 table in `evidence/CHAMPION_SHARE_AND_FLOOR_SWEEP.md` before conduct rules (V. Gonzalez, Padilla, Waters, Cramer, Sherman, Fitzpatrick, Fitzgerald, Timmons, T. Scott, Sullivan, Y. Kim, Huizenga, Daines); Tier 2 and Tier 3 equal the same analysis's seats 14 to 85; conduct rules then applied identically to the legacy path and each resulting change receipted.
4. Universe manifest for the 119th lists the reserved-number exclusions and reports `denominators_available: true` for the House.
5. Kernel gate in the live tree: no failure attributable to this change; the six lane suites listed and green; `test_run_legislation_pillars_and_ranks` green against the re-pinned contract.
6. `audit_full.py` `[LEGEFF]` block present and green; crown-law checks green with the new mode active; the existing sections unchanged in count.
7. A full chain run completes end to end with both modes ON; the rank delta report enumerates every mover with P, S, A, B, L and the legacy values side by side; `champions_v2` receipts show the crown following the new Tier 1.
8. Rollback rehearsed: `LEG_MODE=legacy` and `PRIMACY_BOARD=factor`, re-run the producers, pre-run hashes restored exactly.

## IMPACT ENVELOPE

Files Codex may change: `fec/engine/compute_pillars.py`, `fec/engine/live_legislative_pillar.py`, `fec/engine/pillar_policy.py`, `fec/engine/effectiveness_integration.py`, `fec/tier_util.py`, `fec/moneyball_core.py` (primacy_engine_state only), `fec/lobbying/industry_tiers.py`, `fec/engine/primacy_factors.py`, `fec/legislation/build_bill_milestones.py`, `fec/legislation/run_effectiveness_shadow.py`, `fec/run_pipeline.py` (one inserted step), `fec/audit/audit_full.py` (one added block), `fec/tests/run_tests.py` (registration), `fec/legislation/run_legislation_pillars_and_ranks.py` (literal re-pin), the two templates, new tests under `fec/tests/engine/` and `fec/tests/legislation/`, MATHEMATICAL_SPECIFICATION.md, README.md. Processes: unittest runs of the named suites, `run_tests.py`, `audit_full.py`, `compute_pillars.py --write`, `primacy_factors.py`, `industry_tiers.py`, `champions_v2.py`, `run_pipeline.py` in the LIVE tree only on Paul's explicit go, with Excel closed and a rank baseline captured by Claude first.

## CONFIRMATION CONDITIONS

Codex returns: the RECEIPT enumerating every constraint; the diff as before/after text plus `git status --porcelain` of its worktree; hashes for criteria 1 and 8; the 533-row parity output for criterion 2; the board listing for criterion 3; the kernel, audit_full and champions receipts; the eight labeled lists. Claude reviews, a fresh read-only Codex thread hunts defects, Paul gates the apply and the chain run.

## Open items Paul decides at dispatch time

- Whether the 117th term enters the production aggregate (archives exist; not built in the shadow).
- Whether SS stays dormant until a bill-level publication panel is inventoried (substance carries no signal until then).
- Whether the four off-axis acts diluting Cortez Masto's factor are adjudicated (open STATE question since 2026-08-12); that is a factor-side decision, not part of this contract.
