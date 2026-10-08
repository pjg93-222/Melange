# Cross-industry lobbying: linear + multivariate relationship tests

DATE: 2026-08-11 (run run-20260811T0254123004035Z-c35009a837; analysis
executed read-only under the prior slot-hold). Verbatim artifacts
archived in audits/backfire_analysis_2026-08-11/: n1_exposure.py,
n2_models.py, n5_conflict.py, analysis_table.json (533 rows),
backfire_models.json (12 models).

QUESTION (Paul): when industry B lobbies members who are allies/champions
of industry A on a shared issue, what is the likely result — can courting
another industry's champion backfire?

STATUS: **EXPLORATORY ASSOCIATIONS.** Cross-sectional; no causal claims;
selection stories are live alternatives (industries plausibly target
contested members). Nothing here feeds any engine. Any promotion of these
relationships into receptivity/engine inputs or a published validity claim
requires the prereg discipline first (change-control class 4).

CORRECTION OF RECORD (2026-08-12, Paul-gated; two-chair examination pilot,
run run-20260812T0109334914983Z-323f3b7afd). NO NUMBER CHANGED. Three
wordings were corrected because they claimed more than this run performed,
and both examining chairs — a quantitative-social-science reviewer and a
financial-industry practitioner — independently named the first as the
document's largest overclaim, from opposite directions:
  1. The answer line read "YES, it can backfire, in two measurable ways".
     A causal verb sitting 80 lines below this document's own "no causal
     claims" banner. Now states that two patterns are measurable and
     neither identifies backfire.
  2. "The screening rule the data supports" converted an exploratory fit
     with party uncontrolled and no multiplicity handling into an
     operational decision procedure. Now framed as a hypothesis, with the
     prereg requirement stated in place.
  3. "robustly NEGATIVE interactions" (and "a robust negative marginal
     association" in the answer block) asserted robustness no check in
     this run performed. Now "consistently", with the absent checks named.
Findings 1 and 4 are NOT exploratory associations and the blanket status
banner above over-caveats them: the board-score correlation matrix (n=533)
and the top-25 cross-exposure enumeration are descriptive censuses over a
fully observed population — no estimator, no residual, no confound. Read
them as measurement facts about the instruments.

SECOND CORRECTION OF RECORD (2026-08-13, Paul-gated; party-stratified refit,
audits/D9_PARTY_STRATIFIED_REFIT_2026-08-13.md). NO NUMBER IN THIS DOCUMENT
WAS ALTERED; three pooled coefficients were DEPRECATED and the party location
of the rest was added. The pooled models here average over two strata that do
not share a coefficient.
  1. THREE POOLED COEFFICIENTS ARE DEPRECATED — CU->crypto, bank->crypto and
     fintech->crypto, i.e. the whole "the REVERSE is positive" bullet in
     finding 2. Their strata are opposite-signed (D positive, R negative) and
     their three-way party terms are the only 3 of 12 to survive Holm. Quote
     the stratified estimates, never the pooled ones.
  2. THE CRYPTO FAULT LINE IS DEMOCRAT-DRIVEN. All three negative interactions
     are Holm-significant within Democrats and none is within Republicans.
     Across all 12 pairs: Democrats 8 survivors, Republicans 0.
  3. THE CAVEAT LINE IN FINDING 2 WAS UPDATED because it had become false —
     it said no party control, no multiplicity correction and no split-sample
     had been run. All three have been run since. Outlier diagnostics and
     alternative specifications still have not.
Recorded against over-reading: five Republican pairs are nominally p<.05 and
all five die under Holm at m=12. "Not significant within Republicans" is not
"zero within Republicans." The refit is still EXPLORATORY — it locates an
association, it does not make it causal, and it does not revive a screening
rule. The refit's own defects (an S2 reference-cell coding error, a coherence
gap in its decision rule, and an overclaimed reproduction gate) are recorded in
its own document rather than here.

THIRD CORRECTION OF RECORD (2026-08-13, Paul-gated; the same propagation sweep,
run run-20260814T0129332340960Z-02623964ae). NO NUMBER CHANGED, verified
mechanically: every numeric token present before these edits survives with at
least its original multiplicity (157 tokens, multiset sha256
3bd6ec4b029c3b8b...), by the same method and tokenizer as the BARR block of
the same date. This block is the only addition. Three
wordings corrected, all of them restatements the two rounds above left standing
in the body:
  1. The finding-2 heading read "The backfire signature exists and is
     DIRECTIONAL". DIRECTIONAL means negative one way and positive on the
     reverse; the reverse leg rested on the three pooled coefficients the
     round above DEPRECATED, which are Democrat-positive and
     Republican-negative and describe no member of either stratum. The
     two-way pattern therefore survives only inside the Democratic stratum,
     which is what the heading now says: "is present and DIRECTIONAL —
     Democrat-located". It is a Democrat-internal two-way pattern, not a
     roster-wide one.
  2. "The interaction term is the backfire test" asserted that this design
     identifies backfire, which the answer block denies. Now "the
     backfire-signature test".
  3. "HIGH EXPOSURE + LOW ALIGNMENT is the red-flag signature" stated the
     screening criterion as established fact after correction 2 of the first
     round demoted it to a hypothesis requiring prereg. Now "is the pattern the
     hypothesis flags".
EXAMINED AND NOT CORRECTED: "the baseline works against backfire" (finding 1),
"the cross-champion sides with the primary loyalty" (finding 3), the "danger
zone" heading with its EXCEPT clause (finding 4), and "resolves toward their
primary loyalty" inside the corrected answer block each survive on their local
qualifiers and were left as written. Recorded as a confirmed absence: the
"robustly NEGATIVE" correction has ZERO restatements anywhere in this file —
both live sites already read "consistently" with the absent checks named in
place.
## Data

- Alignment: the four industry-tier board scores (533 x 4), audited
  2026-08-11 (24/24 per-board checks), uniform-clean-v1 + 26 tensor cells.
- Exposure: bill-mediated lobbying attention, 2021-2026Q2 — LDA interaction
  ledger rows by sector-resolved orgs (sector_spend.ROSTERS) joined to bill
  sponsors via interaction_bill_members.csv; role-weighted, log1p. 28,277
  sector+bill-linked interactions. (LobbyView network.csv rejected: its
  member-contact data is 2021-only.)
- Rhetoric outcome: category_stance.json ordinal mapping (Champion=3 ..
  Opponent=-3) on the industry-proxy categories.
- Controls: chamber, log total exposure.

## Findings

### 1. The four alignments are complements, not substitutes

Pearson r between board scores: CU-bank +0.73, bank-fintech +0.82,
CU-fintech +0.69, crypto vs the rest +0.52..+0.66 (n=533). Financial-sector
engagement is one common factor; crypto is the most distinct axis. A
"separate industry's champion" is, on average, MILDLY ALIGNED with yours —
the baseline works against backfire.

### 2. The backfire signature is present and DIRECTIONAL — Democrat-located (crypto fault line)

OLS: align_B ~ exp_B + align_A + exp_B*align_A + senate + log_total_exp
(n=533 per model). The interaction term is the backfire-signature test.

- TRADITIONAL COURTING CRYPTO CHAMPIONS — consistently NEGATIVE
  interactions, and DEMOCRAT-DRIVEN (see the 2026-08-13 stratified refit;
  party control, Holm multiplicity correction and a party split-sample have
  since been run — outlier diagnostics and alternative specifications have
  NOT):
  A=crypto->B=CU  b=-0.122 (t=-4.9); A=crypto->B=bank b=-0.095 (t=-4.6);
  A=crypto->B=fintech b=-0.100 (t=-6.1). Among crypto-aligned members,
  more exposure to a traditional industry's lobbying associates with LOWER
  alignment with that industry than main effects predict.
  PARTY LOCATION — all three are significant within Democrats and none is
  significant within Republicans after Holm:
    crypto->CU       D b=-0.185 p_holm 4.3e-06 | R b=-0.060 p_holm 0.658
    crypto->bank     D b=-0.143 p_holm 3.4e-05 | R b=-0.038 p_holm 1.000
    crypto->fintech  D b=-0.099 p_holm 4.8e-05 | R b=-0.066 p_holm 0.182
  Their three-way party terms miss Holm (0.108/0.100/1.000), so the pooled
  coefficients above are retained — but they must never be quoted without
  this split, because the evidence for them sits in one stratum. "Not
  significant within Republicans" is NOT "zero within Republicans."
- CRYPTO COURTING TRADITIONAL CHAMPIONS — POOLED COEFFICIENTS DEPRECATED
  2026-08-13. These three were reported as "the REVERSE is positive". The
  stratified refit shows the strata are OPPOSITE-SIGNED and the pooled
  number describes no member of either:
    CU->crypto       pooled +0.092 | D +0.262 | R -0.062
    bank->crypto     pooled +0.085 | D +0.205 | R -0.055
    fintech->crypto  pooled +0.062 | D +0.254 | R -0.056
  All three three-way party terms survive Holm (1.75e-07, 4.72e-07,
  7.04e-10) — the only three of twelve that do. Under the refit's
  pre-declared decision rule the pooled coefficients are DEPRECATED: only
  the stratified estimates may be quoted. The Democratic magnitude is
  3.7x-4.5x the Republican, and the Republican estimates are negative and
  Holm-non-significant. "Conversion flows toward crypto, not from it" holds
  among Democrats only and is WITHDRAWN as a pooled statement.
- Mild negative also for A=CU->B=bank (-0.058, t=-2.9); other pairs weak.
- Rhetoric channel (bank stance outcome, n=137 measured): interactions
  positive (+t 1.8..2.1) — talk tracks with exposure even where scores
  do not.

### 3. Conflict cells: the harm is authored INSIDE the harmed industry's
### engagement surface

On the tensor's opposed-valence acts:

- ILC closure (S.3538/S.3734; bank+CU pro / fintech anti): authors
  Kennedy, Wicker, Van Hollen, Kim — fintech alignment AT/ABOVE roster
  mean (Kennedy +0.426 vs +0.387) with above-median fintech exposure
  (3.7-4.2), and bank alignment much higher (+0.43..+0.50). On the
  conflict issue the cross-champion sides with the primary loyalty:
  fintech's harm was written by members fintech itself engages.
- Yield bans / Fed moat (crypto harm, bank+CU help): Hickenlooper —
  crypto exposure 4.2 but crypto alignment +0.277 (roster +0.415);
  Warren — exposure 5.6, alignment -0.272. HIGH EXPOSURE + LOW ALIGNMENT
  is the pattern the hypothesis flags: the industry was engaging the very
  authors of its losses.
- TBTF issuance ban (bank harm): Warren again — bank exposure 5.3,
  bank alignment +0.054.

### 4. The danger zone is crowded but usually friendly

Top-25 champions of any industry are almost universally above-median
exposed to every other industry (22-25 of 25) — the same committee rooms.
Their mean alignment with the OTHER industry sits ABOVE roster mean in
every pair tested (e.g. crypto champions' bank alignment +0.434 vs roster
+0.376). Cross-lobbying champions is normal and lands on mildly friendly
ground — EXCEPT at the crypto/traditional fault line (finding 2) and on
explicit conflict issues (finding 3).

## Answer to the question

TWO PATTERNS ARE MEASURABLE; NEITHER IDENTIFIES BACKFIRE. Exposure and
alignment share bill sponsorship as a common cause, and industries
plausibly lobby hardest where they are already losing — which produces
the same signs. (1) Traditional industries courting crypto-aligned
members show a consistent negative marginal association — the one
direction where more lobbying tracks with less alignment — but that
association is DEMOCRAT-DRIVEN: Holm-significant within Democrats on all
three pairs, Holm-significant within Republicans on none (2026-08-13
stratified refit). It is a pattern in one stratum, not a roster-wide one;
(2) on
shared-issue CONFLICTS, the other industry's champion resolves toward
their primary loyalty, and the members most exposed to your lobbying can
be the authors of your harm (Kennedy/ILC, Hickenlooper/yield). The
hypothesis this suggests — NOT a screening rule the data supports: before
courting a cross-champion on a shared issue, it may be worth checking (a)
whether the issue is a conflict cell in the tensor, and (b) the
exposure-vs-alignment gap — high exposure with at-or-below-roster
alignment marks the members where attention has not been accompanied by
position. Promoting this to a rule requires the prereg discipline first.

## Caveats

Cross-sectional; exposure is bill-mediated (LDA filings name bills, not
members); selection unmodeled; rhetoric outcome covers only measured
members (n=137); one exposure epoch (2021-2026 pooled). Exploratory.
