# DEEP AUDIT II — MATH · LOGIC · SOURCING — 2026-07-02

> **ADDENDUM (same day): ALL FIXES APPLIED AND RATIFIED.** W1 = Topic-Weights tiered spec is live
> (all 19 row-535 weights are literals sourced from your dial sheet; flagships at 0.30). PERS_NONE
> 0.45 · SOCIAL_SHRINK on · RT_W 0.5 · H2/H3/M1/M2/M3/M6/M7 fixed · ψ-caution tag added
> (SAL_PSI_DAMP dial off). GroupKFold verdict: all classifier configs statistically tied (~0.78 CV);
> incumbent SVM retained in production at 83.9%/0.816. New ranks: orphan/snapshots/ranks_AFTER_fixes.json (318 members
> moved ≥5; top 5 = Crapo, Barr, Roger Williams, Hill, Britt; Durbin 531 — his col-G tier is now full
> Opponent, and the audit's deep-but-movable check was repointed to the rung rather than the man).
> One incident during application: an Excel-save/OneDrive collision truncated the workbook; restored
> from backup, and run_pipeline's recalc now zip-validates + retries. **Audit: 48/48 CLEAN.**
> Still open (need your data/queue): flagship legislative sourcing, Truth Social token, Bluesky
> handles; engineering backlog: shared data-loader refactor, same-text-same-split at next refresh.

Second, deeper pass as ordered: every live formula re-derived, every engine's logic traced, every
data source inventoried. One CRITICAL workbook finding (yours to adjudicate), three HIGH code
findings, and a concrete optimization roadmap. Nothing was changed — this report is decision
material.

---

## CRITICAL — W1: the press pillar has ZERO weight on your three flagship categories

**Row 535 of 'Press Release - Normalized' (the SUMPRODUCT weight vector for the entire press/media
pillar) evaluates to 0 for Interchange, Credit Union Tax Status, and Credit Card & Consumer-Fee
Mandates.** The other 16 categories carry a hand-typed flat 0.05.

Why: those three cells don't hold numbers — they hold a stray copy of the LET normalization formula,
which normalizes `Table10[#This Row]` = the raw sheet's row 535 ('Weights' label, all zeros) → 0.
It looks like a fill-down remnant, not a chosen zero.

The workbook can't even agree with itself. Three specs coexist:
| source | Interchange / Tax / CCM | High tier | Medium | Low |
|---|---|---|---|---|
| **LIVE row 535** (what ranks use) | **0** | 0.05 | 0.05 | 0.05 |
| 'Topic Weights' detailed table ("editable dials") | **0.30** (TOP) | 0.15/0.10 | 0.08 | 0.02–0.05 |
| 'Topic Weights' tier summary | **0** | 0.10–0.15 | 0.08 | 0.02–0.05 |

**Consequences right now:** every press release and every social-media post about interchange, the
tax exemption, or credit-card mandates — including the entire media blend we inserted last night —
multiplies by zero in the Blended Model rank. (The data still flows to the python stance matrix,
col G tiers, cascade, and advisory — only the rank's press pillar is blind.) Durbin's rank does not
currently suffer for being the single loudest interchange opponent in the corpus.

**Counterfactuals (computed, not applied; recompute verified 0 mismatches against live first):**
- Flat 0.05 everywhere → 79 members move ≥5 ranks. Durbin 482→529, Grassley 99→185, Fong 439→329.
- Topic-Weights detailed spec (0.30 TOP tier) → **346 members move ≥5 ranks.** Grassley 99→399,
  Fong 439→156, Jayapal 526→388, Durbin 482→531, Warren 146→123, Marshall 531→532.

Weights are your domain. The three options are on the table; whichever you pick, the mechanical fix
is typing numbers into three cells (E535-area: Interchange, CU Tax Status, CCM columns) + recalc +
`run_pipeline.py`. My only engineering recommendation either way: replace the formula remnants with
literals so this class of accident can't recur, and I'll add a row-535-is-numeric audit check.

## HIGH findings

**H1 — Silent members outrank declared Allies in flip targeting, contradicting your own design
note.** `flip_model.py`/`per_topic_flip.py`: the M5 comment documents the decision "0.45 so a silent
member sits at PARITY with a known Ally and never outranks one" — but the shipped default is
`PERS_NONE=0.50` vs Ally 0.40 (a later line re-rationalizes 0.50 as "≈ True Neutral"). Since '—' is
~60% of matrix cells, this constant scales the whole optimizer objective. Decide 0.45 or 0.50; the
losing comment should be deleted.

**H2 — budget_frontier's CFPB candidate ranking ignores CFPB-Reach engagement.** The M3 fix (fold
legislative blocks 99+145 into one CFPB engagement signal) was applied to `flip_model.py` but never
to `budget_frontier.py`, whose `eng()` still reads block 99 only. The frontier's coalition-candidate
ordering for CFPB is built on half the engagement signal. One-line fix (replicate `cat2blocks`).

**H3 — Classifier hyperparameter tuning has CV fold contamination.** With `--augment --tune`,
multi-view copies (title/span views of the same article) are appended to train *before* the 5-fold
CV, so views of one row can sit in both a fold's train and validation sides — the C-parameter sweep
is optimistically biased. Your 83.9%/84.7% headline is unaffected (the held-out test is never
augmented); only model selection is at risk. Fix: `GroupKFold(groups=row_id)`.

## MEDIUM findings

- **M1** `salience_shock.py` prints "held vs a **$100k** competitor shock" but the probe actually
  fires **$250k** (`SAL_PROBE` default 250000). The defections-prevented numbers you read are the
  $250k window mislabeled. Cosmetic fix, but it's in your decision loop.
- **M2** `per_topic_coalition.py` reports projected gain as base + **sum of individual seed
  marginals** — spread is submodular, so the joint gain of the funded set is smaller than that sum.
  The frontier does it right (sequential re-evaluation); the coalition summary is optimistic. Fix:
  evaluate `spread(funded_set)` once for the reported total.
- **M3** Advisory's electoral-vulnerability multiplier reads `dashboard_data.json` = the *previous*
  cycle's bundle (advisory now runs before the bundle in the chain). One-cycle-stale plays; read
  `electoral_plays.json` directly instead.
- **M4** High policy-uncertainty issues (ψ→1, e.g. CU Tax Status ψ=0.98) only raise backfire
  probability mildly (b≈0.15). Noble Prop 5's wait-and-see caution is under-represented — the
  advisory said GO PUBLIC on the single most uncertain issue. Consider a ψ-damped value or a
  ψ-flag in the verdict column. Judgment dial, yours.
- **M5** Cross-module physics inconsistency: the cascade dampens cross-party edges
  (0.4+0.6·√(bpf·bpf)), while the flip model amplifies co-partisan pressure (×1.7) and halves
  out-party (×0.5). Two different partisan-influence models on the same network — defensible
  (diffusion vs. direct pressure) but worth one sensitivity test.
- **M6** Industry-money imputation (H3 fix) exists in flip_model/per_topic_flip but NOT in
  budget_frontier/salience bystander activation — the 18 no-FEC-record members can never be
  industry-activated bystanders in cascades but are imputed in flip. Align via a shared loader.
- **M7** `--intensity auto` matches frame-alignment issues by *first-word substring* ('CU' hits
  multiple keys). Only affects the optional auto mode, but the mapping is fragile.

## SOURCING — inventory and verdicts

**Clean:** congestion.json 533/533 with bioguides, zeros documented and handled (median imputation
verified in code); bipartisan + electoral coverage 533/533; rosters HS117–119 present; social corpus
9,633 posts continuous monthly 2022-05→2026-07 (no gaps; all dates parse); Quorum↔Master reconcile
exact; stance_training splits stable (456/87/21/9).

**Concentration risk on the flagships:** archive_leg covers 11/18 categories, the vote layer 9/18 —
and **all three TOP-tier categories are absent from both**. Interchange/Tax/CCM stance rests almost
entirely on the press+social channel; combine with W1 and the flagship categories are the *least*
instrumented in the whole model while being the highest-stakes. Improvements: extend
`bill_directions.csv` to interchange/CCCA-adjacent bills, add tax-status legislative markers
(resolution cosigners, "Don't Tax My Credit Union" letter signatories) to archive_leg.

**Thin platforms:** Bluesky 74 posts (discovery incomplete pending your handle confirmations);
Truth Social 0 (awaiting TRUTH_TOKEN). X corpus is Quorum-sourced and current to 2026-07-01.

## VERIFIED EXACT (re-derived from scratch)

- Regime probabilities p+q+b≡1 by construction; DTHRESH 11.25 = 18·(1/6)/((1/6)+0.10) exact.
- Press pillar SUMPRODUCT recomputed independently: 0 mismatches. Blended score =
  0.25·Leg% + 0.30·Press% + 0.40·Infl% + 0.05·Demo% (sums to 1.0); RANK direction correct.
  (Note: media/press is 30% of the blend, not 40% — you'd said "40% or whatever it is".)
- Both lazy-greedy (CELF) implementations are *correct*: the stale-marginal tag logic is valid, and
  member marginals are truly independent (pflip of n doesn't depend on cu[m]) so the accumulated
  objective is exact, not drifted. The G-K data-dependent bound derivation holds (concavity +
  per-member headroom capping).
- Edge-keyed splitmix64 CRN verified: draws are activation-order-independent; every member is rolled
  before filtering (marginals isolate true effects, not MC noise).
- Single-issue tier inflation: **checked and absent** — all 22 extreme overall tiers rest on 3+
  categories of signal.
- Legislative block weights uniform 2/7, 1/7, 0.5/7 across all 18 blocks.

## OPTIMIZATION ROADMAP (ranked by impact/effort)

1. **Adjudicate W1** — the single biggest lever in the system (three quantified options above).
2. **PERS_NONE 0.45 vs 0.50** (H1) — one env default + comment cleanup.
3. **Frontier CFPB block merge** (H2) — one line.
4. **GroupKFold in --tune** (H3) + same-text-same-split rule at next label refresh.
5. **Shared data loader module** — congestion/receipts/ind/network loading + symmetrize logic is
   copy-pasted across 6 files; H2 is exactly the drift class this breeds. One `moneyball_data.py`
   kills it.
6. Wire the SOCIAL_SHRINK / RT_W dials (from audit I) once you rule.
7. Coalition submodular-honest totals (M2); probe label (M1); advisory vuln source (M3).
8. Flagship legislative sourcing (bill_directions + tax letters) — turns your highest-stakes
   categories from single-channel to triangulated.
9. ψ-aware advisory damping (M4) — dial, default off.
10. Truth Social token + finish Bluesky discovery (your queue).

Cosmetic sweep for whenever: dead `BETA` constant in two files, dead `ex=[...][:0]` in
money_response, optimizer's hardcoded "all 17 issues" banner.
