# Optimizer evaluation: TEST PLAN (phase 4), locked before any test is run
System: fec/engine/optimize.py (T1). Repo commit under review: bfec947 (code-only snapshot of LIVE main 5e92f304c).
Status: PLAN ONLY. Nothing has been run. No data plane in the cloud session; RUNS-SYSTEM steps are owner-gated and run on Paul's PC.
Tabled: original open question 3 (Paul does not recall it). Re-open if it resurfaces.

Common: read-only; scripts write only to a fresh --out folder; project binding melange.md rules apply; frozen money/receipt code untouched.
Provenance line required on every result: commit, SEED/MC (7/20), script seed, inputs sha256[:12], N units, UTC date.

## O-1 PAC own-gift headroom (DECISION/LEGAL) -- cost: READ-ONLY (data plane, PC)
Test: census funded members whose planned alloc + this PAC's own prior-cycle gifts exceeds $10,000 (per-candidate per-cycle limit as modeled).
Criterion (fixed now): PASS if 0 members exceed; WOUNDED if 1-19 (<5% of funded) exceed; KILLED-candidate if >=20 or total excess >= $50,000.
Control: plant a synthetic member with own-gift 9,500 + alloc 2,000; the census must flag it.
Needs: the PAC's own disbursement record (not tracked by the optimizer -- first confirm a source exists; if none, verdict UNVERIFIED-HERE).
Second path: recompute from raw receipts/disbursements without optimize.py output.
Owner question if it fails: add own-gift tracking, or keep the $10k cap as a model convention? Not a legal determination.

## O-2 Constant sensitivity (FUNCTIONAL-FORM) -- cost: RUNS-SYSTEM (owner-gated); design step is READ-ONLY
Test: scripts/global_sensitivity.py --design-only over WM(+WP=1-WM), HALFF, MAXSHIFT, HALF, BASE with literature-status tokens; owner then runs optimize.py per design row with OPT_OUT set.
Criterion (fixed now): over a +/-25% box, PASS if median Jaccard of funded sets vs the baseline >= 0.80 and base-objective gain stays within 10% of baseline; WOUNDED if 0.60-0.80; KILLED-candidate below 0.60.
Control: a planted dummy parameter that does not enter the model must show ~0 sensitivity index.
Precision floor: first measure Jaccard between two baseline runs (determinism; expected 1.0). If <1.0 the bar is invalid.
Second path: re-run 10 design rows through a pure-python reimplementation from flip_model formulas.

## O-3 Certificate re-derivation (COMPUTATIONAL) -- cost: RUNS-SYSTEM
Test: small instance (<=12 members, BUDGET 20,000, INC 500, PMAX 2,000), brute-force/DP exact optimum of the same objective vs lazy greedy.
Criterion (fixed now): PASS if greedy objective equals exact optimum within 1e-9 when certificate_valid is True; any gap > 1e-9 with certificate_valid True = KILLED-candidate. When certificate_valid is False, report gap only (no pass/fail).
Also check: conversion_reachable computed over fundable members only (optimize.py:49-50) -- confirm gated members' conversions cannot change fundable members' marginals (cross-member pressure). PASS if marginals identical with gated members' stances toggled on a fixture.
Control: a fixture with a known non-concave chunk sequence must make certificate_valid False.

## O-4 Outcome validation (DATA) -- cost: owner-gated, prereg
Not run ad hoc. Hand to moneyball-research-methodology: prereg, power study first (need >=150 positive deltas; 19 on 2026-07-04 snapshot), one look. No contaminated or altered-hypothesis look.

Deviations from this plan are listed in the report, never folded in silently.
