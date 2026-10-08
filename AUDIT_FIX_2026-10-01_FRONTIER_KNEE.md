# Frontier cutoff repair — 2026-10-01

Paul authorized this repair with “Fix” after the independent council review identified the stored-path cutoff error. Starting state: live `main`, commit `8cd949ab0bf17c518169bade15a6eafb3359b965`. The original council report is retained unchanged. The repair, full regeneration and independent publication checks are complete; the kernel qualification below remains.

## Repair and contract

The declared rule chooses the last recorded budget whose marginal spread gain is at least one quarter of the largest marginal gain. Binary subtraction could reject equality on the published one-decimal path, for example a stored 0.3 gain at a stored 1.2 peak. The producer now reconstructs integer tenths before subtracting and compares `4 * gain >= peak`. This retains the inclusive quarter rule, raw/clamped choice and rounded path contract. It uses each point’s recorded dollar budget instead of deriving dollars from the position. Empty and single-point paths retain no-knee status.

The frontier audit independently parses stored values with `Decimal`, computes its own threshold and scans backward. It does not call the producer helper. Its old-artifact clamped fallback remains. Audit count floors and policy constants are unchanged.

The bundle carries `knee_found` to the dashboard. The actual refresh caption prints the numeric best-value location only for a true flag. False or missing status prints “best-value point not identified within this range.” This corrects the endpoint claim for Member Business Lending and the already-flagged Technology & Emerging Issues endpoint. Paths and sliders are unchanged.

## Confirmed output changes

The expected deltas were recorded before regeneration. Both post-run readers confirmed exactly these four amounts and one flag, with every other frontier field unchanged:

| Mode | Topic | Old cutoff | Corrected cutoff | Status |
|---|---|---:|---:|---|
| Coalition | CDFI Fund | $1,900,000 | $2,100,000 | Interior stays true |
| Coalition | Credit Card & Consumer-Fee Mandates | $1,300,000 | $1,450,000 | Interior stays true |
| Coalition | Member Business Lending | $2,100,000 | $2,200,000 | Interior becomes false; terminal point |
| Electoral | Telephone Consumer Protection Act Issues | $900,000 | $1,300,000 | Interior stays true |

## Verification

Both focused suites passed: **36 tests**, no skips. They test fixed equality and below-cutoff answers, endpoint flags, empty/single/zero-gain paths, actual budgets, raw/clamped selection, legacy fallback, bundle preservation and execution of the actual JavaScript refresh caption. Both suites are registered in the full kernel.

The independent reviewer compared both helpers against a Fraction oracle on all 36 frozen paths and 2,921 synthetic paths: **11,684 synthetic comparisons, zero mismatches**. Planted strict-cutoff and endpoint mutants were rejected. Source scope and exact patch replay were verified separately.

The full kernel completed **263 passed, 3 failed** (exit 1). Both new suites passed. All three failure lines match the preceding kernel run: missing `backups/bill_directions.PRE-LEGFIX3.csv` in `test_bill_collision_guards`, unrecognised verdict in `test_make_staffer_network_html`, and the existing `audit_stale_imports` failure. This is an unchanged baseline failure set, not a clean kernel pass.

The full default chain completed with exit 0 in **56.8 minutes**, at 2026-10-02 03:35:36 UTC. Its 79 recorded steps comprise 78 completed, one explicit absent-LODES-input skip and zero tolerated failures. The normal default excludes responsiveness. Forecast reuse verified 353 unchanged inputs. Its final audit returned **ALL MODULES CLEAN**.

The separately captured final audit completed at 2026-10-02 03:40:51 UTC, exit 0, with the actual retained tail:

```text
FULL-BODY AUDIT — 571 passed, 0 FAILED
  ALL MODULES CLEAN.
```

Its manifest section retains nine explicit observation skips and six notices; this is not universal filesystem coverage. No manifest regeneration or weakening of checks was required.

The controller’s 12 post-verification checks and the independent publication reader both passed. All **36 live topic/mode records** match exact Fraction arithmetic; paths, seeds and spreads are unchanged. **0 of 533 ranks moved**, with rank and score maps and the entire rank artifact byte-identical. The optimizer remains byte-identical: **$2,500,000 across 380 allocations**. All 18 coalition projections and the actual wired captions in `Moneyball Dashboard.html` and `Moneyball.html` match current source. Coalition flags comprise 16 interior and two no-interior cases.

A supplemental seven-check reader passed for `Moneyball_Email.html` and both rebuilt delivery ZIPs. The extracted monolith `Moneyball.html` matches the email HTML byte-for-byte, and the family ZIP’s dashboard entry matches the current standalone dashboard. Inputs stayed stable throughout the readers.

All **19 invariant protected files** retain their pre-run raw hashes, including Paul’s QME skill edits, `audit_full.py` and `pillar_freshness.py`. The deliberately regenerated email ZIP is the sole protected-file exception; its pre-run copy is retained. It is not part of this source commit.

## Evidence and limits

Evidence is retained under `C:/melange-data/qme-knee-fix-20261002`: `before.json` and its backups, `uncommitted-before.patch`, focused/kernel/pipeline/audit logs and exit receipts, `kernel-baseline-comparison.json`, `post-verification.json`, `email-publication-verification.json`, `ui/REPORT.md` and `verifier/verification.md`. The independent final receipt is `verifier/post-publication-independent-20261002T034122Z.json` (SHA-256 `4eec67c41a6a2210f02eeb3d348e84d9211c0ad8ef86cb6f7125dbc4240bcd32`); `verifier/final-summary-v2.json` records the compact verdict, actual counts and separately scoped email checks. Earlier receipts remain intact.

Only the seven repair source/test files and this record are committed. No weights, dials, labels or outcome-look policy changed. This repair establishes compliance with the rounded-path rule and its display status; it does not establish unrounded optima or empirical spending effects.
