# Cross-industry backfire: party-stratified refit

DATE: 2026-08-13. Refit of the 12 models in
audits/CROSS_INDUSTRY_BACKFIRE_ANALYSIS_2026-08-11.md, stratified by party.
Analysis plan pre-declared and hash-fixed BEFORE dispatch; independent
replication on a different solver and join route. Read-only: no producer ran,
no artifact was regenerated.

QUESTION: the 2026-08-11 analysis reported an exposure x alignment interaction
pooled over all 533 members. Does that pooled coefficient describe a quantity
the two parties share, or is it an average over populations that differ?

STATUS: **EXPLORATORY.** No prereg, no bars, no closure — nothing here is a
"successor" in the bridge sense, because the source analysis consumed no look
and closed nothing. Cross-sectional, one exposure epoch, selection unmodeled.
Nothing here is causal and nothing here licenses a screening rule. Promotion
into engine inputs or a published validity claim still requires prereg first
(change-control class 4).

## Why this was run

A prior refit added party as a MAIN EFFECT and reported that the interactions
survived. That test could not answer the question it appeared to answer: a
main-effect dummy shifts the intercept and the align_A slope, but cannot absorb
a product term and cannot reveal that the product term differs by party. The
defect was found by an independent replication round, not by the author.

## Pre-declaration (fixed before any number was seen)

- HEADLINE = S1, the party-stratified subsample estimates. The three-way terms
  are supporting evidence, never the headline.
- Holm within each stratum across that stratum's 12 interactions; Holm across
  the 12 three-way terms as its own family; the two families corrected
  separately, never pooled to 24.
- DECISION RULE: if a pair's three-way term survives Holm, that pair's POOLED
  coefficient is DEPRECATED and only stratified estimates may be quoted.
- Independents (n=3) excluded from stratification, reported not dropped.

## S0 — reproduction gate

All 12 archived models reproduce. Deviation vs backfire_models.json: 0.000e+00
on the transcription route, and 1.5e-13 on an independent SVD/QR route that
never forms X'X. Join 533/533, zero ambiguity, party R 271 / D 259 / I 3.

## S1 — THE HEADLINE

Coefficient on exp_B x align_A, fit separately within each party.
n(D)=259 df=253; n(R)=271 df=265. Holm within stratum, m=12.

```
A->B                    |  DEM b     t      p_holm     |  REP b     t      p_holm
------------------------|---------------------------- |---------------------------
credit_union->bank      |  -0.0998  -3.26   0.00772  * |  -0.0225  -0.93   1.0000
credit_union->crypto    |  +0.2624  +5.46   1.15e-06 * |  -0.0624  -2.49   0.1470
credit_union->fintech   |  +0.0062  +0.25   1.0000     |  +0.0108  +0.46   1.0000
bank->credit_union      |  +0.0315  +1.18   0.7175     |  -0.0362  -1.35   1.0000
bank->crypto            |  +0.2047  +5.78   2.37e-07 * |  -0.0549  -2.57   0.1268
bank->fintech           |  +0.0463  +2.71   0.03567  * |  -0.0078  -0.51   1.0000
crypto->credit_union    |  -0.1848  -5.17   4.32e-06 * |  -0.0601  -1.68   0.6575
crypto->bank            |  -0.1433  -4.70   3.37e-05 * |  -0.0377  -1.37   1.0000
crypto->fintech         |  -0.0985  -4.60   4.75e-05 * |  -0.0663  -2.34   0.1822
fintech->credit_union   |  -0.0637  -1.85   0.2630     |  -0.0200  -0.68   1.0000
fintech->bank           |  -0.0030  -0.11   1.0000     |  +0.0323  +2.03   0.3459
fintech->crypto         |  +0.2538  +6.79   9.33e-10 * |  -0.0562  -2.41   0.1653
```

**Democrats: 8 of 12 survive Holm. Republicans: 0 of 12.**

The association is overwhelmingly located in the Democratic stratum. Stated
against over-reading: five Republican pairs are nominally p_raw < .05 before
correction and all five are killed by Holm at m=12. **"Not significant within
Republicans" is not "zero within Republicans."**

## S2 — three-way terms (supporting evidence only)

S0 plus a Republican dummy and every R x term product; three-way =
R:exp_B:align_A. n=533, df=521. Holm across these 12 as their own family.

**3 of 12 survive: credit_union->crypto (p_holm 1.75e-07), bank->crypto
(4.72e-07), fintech->crypto (7.04e-10)** — exactly the three "crypto as
outcome" pairs. Nearest non-survivor is 0.100.

Internal consistency: the fully-interacted model algebraically reproduces the
stratum-wise fits to 1.2e-13. S1 and S2 are the same fit under two
parameterizations.

## Decision rule, applied without exception

**POOLED COEFFICIENT DEPRECATED (3):** credit_union->crypto (pooled +0.0921),
bank->crypto (+0.0849), fintech->crypto (+0.0615). Only stratified estimates
may be quoted for these.

On all three the strata are opposite-signed with Democratic magnitude 3.7x-4.5x
the Republican:

```
credit_union->crypto  pooled +0.0921 | D +0.2624 | R -0.0624
bank->crypto          pooled +0.0849 | D +0.2047 | R -0.0549
fintech->crypto       pooled +0.0615 | D +0.2538 | R -0.0562
```

**No member of either stratum is described by the pooled number.**

POOLED STANDS (9), stratified reported as context.

ALPHA: the pre-declaration fixed the scheme but not a threshold; alpha=0.05 was
used and the gap is flagged. Not load-bearing — the identical deprecation set
obtains for any alpha in roughly [5e-07, 0.10).

## What the pre-declaration got wrong, recorded

**The expectation was CONFIRMED and was also too conservative.** It predicted
the three crypto fault-line pairs would be Democrat-driven with "two of the
three not significant within Republicans." All THREE are non-significant within
Republicans. Predicted 2 of 3, observed 3 of 3.

**A defect in the pre-declaration itself, found by the replication.** S2 carries
only a Republican dummy, so its reference cell is Democrats UNION Independents
(n=262), not Democrats (n=259); the three-way term tests R vs (D+I), not R vs D.
Immaterial here — refitting on D+R only agrees on all 12 Holm decisions — but
the plan should have fixed the coding.

**A coherence gap in the decision rule, flagged by the analyst and followed
anyway.** For crypto->credit_union, crypto->bank and crypto->fintech the
headline shows Democrat-significant estimates against Republican nulls, yet
their three-way terms miss Holm (0.108, 0.100, 1.000) so the rule leaves their
pooled coefficients standing. A pooled number is retained for pairs whose own
headline evidence says the strata do not share it. The rule was not altered
after the fact; these three pooled coefficients must be quoted with the
stratified split visible alongside.

**A wording overclaim, caught in review.** The reproduction gate was described
as establishing that "downstream is trustworthy." Byte-identical transcription
of the archived ols() proves transcription fidelity, not correctness — a bug in
that function would have been reproduced perfectly and invisibly. Correctness
was established by the replication's independent SVD/QR route, not by the gate.

## Replication

AGREES. Independent numpy-SVD and statsmodels-QR refits, never forming X'X,
with the party join rebuilt from bioguide keys. Worst disagreement anywhere
across S0, S1 and S2: **1.9e-12**. Identical Holm survivor sets, deprecation
set, n, df and ranks.

The replication verified the plan was followed with positive evidence rather
than absence of contradiction: it confirmed numerically that the Holm
monotonicity constraint BINDS in all three families (max |monotone - naive| =
0.087 / 0.356 / 0.236), so an implementation missing the running-max would have
produced visibly different numbers.

Robustness it added: under a single Holm family of m=24 instead of two of 12,
exactly one Democrat survivor flips (bank->fintech); all three deprecated pairs
survive either way by 5-9 orders of magnitude. And coding Kevin Kiley as
Republican rather than Independent shifts no coefficient by more than 0.0002
and leaves Republican Holm survivors at 0.

## Caveats

Cross-sectional; one exposure epoch (2021-2026 pooled); exposure is
bill-mediated; selection unmodeled — industries plausibly lobby hardest where
they are already losing, which produces these signs without any backfire.
Party is a coarse proxy for ideology and no continuous ideology measure was
added. Nothing here speaks to whether exposure precedes alignment. Independents
(Angus King, Bernard Sanders, Kevin Kiley) are excluded from stratification;
three observations cannot support a six-parameter fit.

## Consequence for the source document

CROSS_INDUSTRY_BACKFIRE_ANALYSIS_2026-08-11.md reports pooled interactions.
Three of its twelve pooled coefficients are now deprecated, and its
Democrat/Republican asymmetry is not visible anywhere in it. Amending that
document is a separate decision and has NOT been made here.
