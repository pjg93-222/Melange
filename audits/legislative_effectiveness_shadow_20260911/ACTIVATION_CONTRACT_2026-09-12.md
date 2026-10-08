# Activation contract: results-only legislative basis and chamber-normalized results board

Date: 2026-09-12. Status: DRAFT for Codex dispatch after the 2026-09-17 quota reset. Authority: D-026 (results-only headline basis) and D-027 (chamber-normalized realized-results board), Paul's rulings of 2026-09-12. Frozen vintage once dispatched; corrections go into the dispatch thread, not this file.

Nothing in this contract is active today. The lane code sits in the live tree (applied 2026-09-11, kernel 187/4, see `LEGISLATIVE_EFFECTIVENESS_SHADOW_VALIDATION_2026-09-11.md` and the packet README) with every candidate path opt-in. This contract turns two candidates into production behavior behind versioned policy, with the rollback that D-026/D-027 require.

## OBJECTIVE

Make the reporting rank's Leg% the results-only within-chamber percentile (results_only_v1) and make the CU primacy board rank on the chamber-normalized signed realized results, both produced by the chain from frozen local inputs, with the legacy policy preserved as an explicit revert dial and byte-identical rollback.

## CONSTRAINTS (numbered; each is binding)

1. Claude authors no code; every edit is Codex's, in a throwaway worktree, reviewed before Paul's gate. No git from Claude or agents in the Melange repo; Codex never commits.
2. Legacy stays selectable and byte-identical: with `LEG_MODE=legacy` (default until Paul flips it) `compute_pillars.py --write` must rewrite `ranks_python.json` byte-identical to today (0 of 533 moved), and with `PRIMACY_BOARD=factor` the board is unchanged. Prove both with hashes before and after, in the LIVE tree.
3. Results-only Leg% is the within-chamber percentile of signed results per term, never re-percentiled across the mixed roster (the plan's section 5 rule; `live_legislative_pillar.from_effectiveness` already refuses pooled ranking).
4. Chamber normalization of the board (D-027): rank gate-qualified members on the within-chamber percentile of `realized_results` (repo `percentrank` convention: share strictly below over n-1, truncated to 5 decimals, first-tie value), ties broken by raw `realized_results` descending then name; seats 13/24/48 unchanged; the distinct-measure gate (minimum 1) unchanged; conduct ladder and explicit overrides applied exactly as `realized_results_tiers` applies them today. Register it as a NEW board mode `realized_results_chamber_v1`; do not redefine `realized_results_v1`.
5. Unavailable is not zero. A member whose term results are unavailable (denominators unavailable) gets no results-only Leg% and no board seat; a member with zero realized results gets percentile 0. Never fabricate a result to fill a rank.
6. The 119th House universe: reserved bill numbers with no action history (the five records that make House denominators unavailable) are excluded from the eligible universe by an explicit, versioned rule in `build_bill_milestones.py` (`reserved_number_no_history` exclusion, counted in the universe manifest), so that current-term House denominators become available. The exclusion must be reported in `effectiveness_universe_manifest.json` with the excluded measure ids.
7. Term basis for production: per-term within-chamber percentiles for the terms the roster served in (118 completed, 119 current as of the run date), combined with the existing decay convention (0.8^(119-t)) only after term-level normalization, and labeled in `pillar_policy.py` as the results-only aggregate. A member with no eligible term keeps Leg% unavailable and is reported, not ranked as zero.
8. Chain placement: a new producer step runs `run_effectiveness_shadow.py` in production mode (as-of = run date, output under `data/engine/legislative_effectiveness/<generation>/`, receipt-gated, atomic generation directory) immediately before `compute_pillars.py --write` and before `primacy_factors.py`; the board consumer (`industry_tiers.py`, `tier_util.py`, allocation priority via `moneyball_core.primacy_engine_state`) reads the generation named in the receipt, never a hard-coded path. The chain stays network-free.
9. Source contract: re-pin the six literals in `run_legislation_pillars_and_ranks.py` to the current `compute_pillars.py` text (the Leg% line is now `legp=_leg_percentiles[m]` fed by `legislative_percentiles`), keeping the tripwire's purpose; never delete the check.
10. Register the six lane suites plus any new suite in `run_tests.py` `_LANE_MODULES` (bare basenames; the validated contract at `evidence/contract.json` covers the six).
11. `audit_full.py` gains a `[LEGEFF]` block: generation receipt present and complete, code hashes match the frozen list, reporting mode and board mode recorded in `scoring_policy()`, denominators available for every term the roster is scored on, and the results-only percentile of every ranked member inside [0,1].
12. Surfaces: with the mode active, the member desk and dashboard explanations (`optional_shadow_explanations`) render from the production generation; the copy stays rankings-and-data only, no advisory text; filenames stay Moneyball, visible text Melange.
13. Calibration and docs: `pillar_policy.py` records `leg_mode`, `board_mode`, generation id and code hashes; MATHEMATICAL_SPECIFICATION.md and README describe the results-only pillar and the chamber-normalized board as Melange adaptations of the paper, never as the paper's formula (advocacy composite stays documented as the rejected alternative).
14. Verification order for a rank-moving change (CONSTRAINTS, tooling): capture the full board and ranks hashes first; run the change in the live tree; enumerate every mover; revert-dial proves byte-identity; `test_primacy_tier` re-pinned only by Paul after he ratifies the new board.

## ACCEPTANCE CRITERIA (observable)

1. `LEG_MODE=legacy python fec/engine/compute_pillars.py --write` in the live tree: `ranks_python.json` sha256 unchanged from the pre-run capture.
2. `LEG_MODE=results_only_v1`: `ranks_python.json` rewritten; `scoring_policy()` in the output names the mode and generation; for every ranked member `pcts[m]['leg']` equals the results-only within-chamber percentile in the generation's comparison artifact (533 of 533 checked by a script, with the unavailable count reported).
3. `PRIMACY_BOARD=realized_results_chamber_v1`: the board's Tier 1/2/3 equal the analysis in `evidence/CHAMBER_NORMALIZED_BOARD.md` for the same generation (13/24/48 seats, same names in the same order) before conduct rules; conduct rules then applied identically to the legacy path.
4. `PRIMACY_BOARD=factor`: `data/lobbying/industry_tiers.json` and `data/engine/primacy_factors.json` sha256 unchanged.
5. Universe manifest for the 119th lists the reserved-number exclusions and reports `denominators_available: true` for the House; the manifest's eligible counts drop by exactly the excluded count.
6. Kernel gate in the live tree: no failure attributable to this change; the six lane suites listed and green; `test_run_legislation_pillars_and_ranks` green against the re-pinned contract.
7. `audit_full.py` `[LEGEFF]` block present and green; the existing sections unchanged in count.
8. A full chain run completes end to end with the modes ON, and the rank delta report enumerates every mover with its results-only percentile and legacy percentile side by side.
9. Rollback rehearsed: setting `LEG_MODE=legacy` and `PRIMACY_BOARD=factor` and re-running the two producers restores the pre-run hashes exactly.

## IMPACT ENVELOPE

Files Codex may change: `fec/engine/compute_pillars.py`, `fec/engine/live_legislative_pillar.py`, `fec/engine/pillar_policy.py`, `fec/engine/effectiveness_integration.py`, `fec/tier_util.py`, `fec/moneyball_core.py` (primacy_engine_state only), `fec/lobbying/industry_tiers.py`, `fec/engine/primacy_factors.py`, `fec/legislation/build_bill_milestones.py`, `fec/legislation/run_effectiveness_shadow.py`, `fec/run_pipeline.py` (one inserted step), `fec/audit/audit_full.py` (one added block), `fec/tests/run_tests.py` (registration), `fec/legislation/run_legislation_pillars_and_ranks.py` (literal re-pin), the two templates, new tests under `fec/tests/engine/` and `fec/tests/legislation/`, MATHEMATICAL_SPECIFICATION.md, README.md. Processes: unittest runs of the named suites, `run_tests.py`, `audit_full.py`, `compute_pillars.py --write`, `primacy_factors.py`, `industry_tiers.py`, `run_pipeline.py` in the LIVE tree only on Paul's explicit go, with Excel closed and a rank baseline captured by Claude first.

## CONFIRMATION CONDITIONS

Codex returns: the RECEIPT enumerating every constraint above; the diff as before/after text plus `git status --porcelain` of its worktree; hashes proving acceptance criteria 1, 4 and 9; the 533-row parity script output for criterion 2; the board listing for criterion 3; the kernel and audit_full tails; the eight labeled lists. Claude reviews, a fresh read-only Codex thread hunts defects, and Paul gates the apply and the chain run.

## Open items Paul decides at dispatch time

- Whether the 117th term enters the production aggregate (archives exist; not built in the shadow).
- Whether the distinct-measure gate stays at 1 (one enacted vehicle still vaults a member on 2 to 3 measures under chamber normalization).
- Whether the SS class stays dormant until a publication panel is inventoried (frequency thresholds are uncalibrated; SS never fired in the shadow).
