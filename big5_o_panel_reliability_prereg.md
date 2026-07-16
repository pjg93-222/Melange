# O vs the Senate gold — reliability-weighted panel evaluation of the FROZEN composite

STATUS: LOCKED (2026-07-16, committed before any look; adversarially reviewed pre-lock — one
CRITICAL, five MAJOR, four MINOR required changes ALL incorporated (gated --rederive, enforced
count pins + pin-set exactness, battery recalibration, full-RESULT re-derivation, implemented
secondaries, covariate-degeneracy abort, covariate source correction to legislators.csv);
user-authorized: Paul 2026-07-16, "Optimize according to your recommendations, Test-Driven
Design". The lock commit CONTAINS the executable spec: fec/b5_o_weighted_look.py and
fec/b5_gold_criterion_probes.py ride this same commit.)

User authorization: Paul, 2026-07-16 — "Optimize according to your recommendations, Test-Driven
Design", following the presented recommendation "O's reliability-weighted frozen-composite look
first". This is a CRITERION-SIDE round: it changes how the gold panels are AGGREGATED (senator
reliability weights from the appendix's preserved rater counts), never the gold values and never
the O composite. Because it touches what "the criterion says", TWO separate user gates apply and
only the FIRST is granted here: (1) taking this look — granted above; (2) on a PASS, ratifying the
weighted criterion as the gate criterion and any `ACTIVE_EXTERNAL_GOLD_ANCHORED` upgrade — NOT
granted here, presented to Paul afterward. The 2026-07-15 activation rule and every shipped §40
per-panel result remain the results of record; nothing is rewritten.

## Compliance with recorded closures

- No closed route is reopened: this is not a lexical refit (closed), not a new instrument basis
  (round-6 anti-basis-shopping clause not triggered — the O composite is byte-frozen), not an
  expert-panel commissioning (canceled; the gold is the published appendix already in use), and
  not blue-on-pink calibration (prohibited permanently; neither instrument is touched).
- The equal-weight no-gold-fitted E control axis is untouched and remains unfitted.
- NO-STATUS-CHANGE clause: E, A, C, and N statuses cannot move in either direction from anything
  computed in this look. No composite other than O's is paired with any gold column here. The only
  status this look can even PROPOSE to change is O's, and that promotion is separately user-gated.
- NO ENGINE CHANGE flows from this look under any outcome: the O gold-anchored composite is a
  display/profile quantity; receptivity engines do not read it.
- The gold-burn ledger this round joins: this gold has absorbed (i) the fixed control-axis E look
  and (ii) one LOO-OOF v2 fitting round across five traits. This prereg pre-declares itself the
  TERMINAL criterion-weighting look for O under gold vintage `big5_senate_expert_gold.json`
  (pdf pin 43c989262fde0b5b806c316e54147474fb4c0d34d05ba819d49e37921aef731a) — terminal under
  EVERY outcome: PASS, PASS-with-ratification-declined, and MISS alike license no further
  criterion-weighting round for any trait against this gold without a fresh Paul-initiated prereg.
- Battery-refusal disposition (pre-declared): if the in-process battery fails, the round is
  RETIRED WITHOUT A LOOK (nothing consumed). The battery is fully deterministic (fixed seeds), so
  a refusal cannot be re-rolled; the only permitted amendment is round-4 Addendum-1 style —
  machinery validation ONLY, with bars, roster, weighting, seeds, and every consequence clause
  byte-identical to the lock — and the retirement addendum must pin its successor condition
  verbatim.

## Hypothesis and honest prior

HYPOTHESIS: the shipped O composite's insider-panel association miss (r=.1919, n=45, p=.1038 vs
the r>=.20 / p<.10 association gate) is substantially CRITERION unreliability — the insider panel
rates a median of 2 raters per senator (11 of 40 shared-roster senators single-rater) — and a
senator-reliability-weighted evaluation of the SAME frozen composite clears the association gate
on BOTH panels while retaining diagonal dominance.

MOTIVATING CRITERION-SIDE EVIDENCE (all computed pre-lock, criterion-vs-criterion only, no
instrument pairing; reproducible via fec/b5_gold_criterion_probes.py committed with this file):
- Insider-vs-academic cross-panel agreement stratified by insider rater count, 40-member roster
  overlap: O r=-.052 (insider k=1, n=10) vs r=+.485 (insider k>=2, n=29). All-both-panel senators:
  +.189 (k=1, n=34) vs +.354 (k>=2, n=72). Same direction for C/E/A/ES. Single-rater insider rows
  behave as noise; multi-rater rows converge with the independent academic panel.
- Range restriction is negligible (gold-O SD ratio roster/full: insiders 1.021, academics 1.147).
- Null calibration: 4,000 random standard-normal member vectors against the real O gold clear the
  r>=.20 association bar on BOTH panels 1.52% of the time (0.77% with dual diagonal dominance) —
  one weighted look is defensible; iterating is not.

HONEST PRIOR: MODERATE-LOW. Expected weighted insider r ~.21-.25 against a .20 bar — roughly
50-65% power. A MISS is more likely to be a power failure than a refutation, and it still CLOSES
this route (stopping rule below). That trade is accepted and user-authorized.

ADVERSE PRIORS DISCLOSED: (i) the shipped free-grid v2 round already evaluated O unweighted and
recorded the insider fail — this round cannot and does not reinterpret that record; (ii) the
academic pass carries thin discriminance (academic heterotrait C=.452, A=.410 vs own .492), so
bar 4 requires academics to RE-CLEAR dominance under weighting — a weighted evaluation could in
principle break the existing academic pass, and that outcome would be recorded verbatim;
(iii) a session probe on 2026-07-16 computed a look-fragment (a Steiger difference test pairing
shipped FITTED scores with gold on a 38-senator subset) — ruled VOID, cited nowhere in this
prereg, and none of its numbers are load-bearing anywhere in this round.

## Criterion aggregation (the ONLY thing this round changes; pinned)

- Panels and matching: `map_gold(big5_senate_expert_gold.json, congestion.json roster)` imported
  from fec/b5_external_gold_validate.py (name-key matching, ambiguity hard-fail) — identical to
  the shipped validators. Gold O values used as published; N/ES direction irrelevant here.
- PRIMARY weighting (the gate criterion under test): senator weight within each panel
  `w_i = k_i * rho1 / (1 + (k_i - 1) * rho1)` with `k_i` = that senator's `ratings_n` in that
  panel and **rho1 = 0.25 fixed here, pre-look** (single-rater reliability assumption; the
  appendix preserves only panel means + rater counts, so rho1 is not estimable from the artifact.
  0.25 sits mid-grid in the conventional single-observer interjudge-agreement band for Big Five
  observer ratings, roughly .2-.3, and is declared as an assumption, motivated but not fitted —
  the closure clause covers every alternative rho1, so it is not shoppable). The SAME formula
  applies to BOTH panels (symmetry; no panel-specific tuning).
- FIREWALLED SECONDARY weighting (reported, grounds nothing, cannot rescue a miss):
  `w_i = sqrt(k_i)`.
- Weighted statistics (the complete list of NEW weighted statistics; the battery constructors and
  the SB weight formula are specified elsewhere in this document):
  `wmean`, `wcorr` (weighted Pearson: weighted covariance over weighted SDs),
  `weighted_perm_p` (one-sided: composite fixed; the (gold value, weight) rows permuted together
  across the panel's evaluated members; p=(exceed+1)/(K+1)),
  `wresid` (weighted least squares residual), `wpartial` (Frisch-Waugh weighted partial r with the
  same permutation scheme on residuals; the b5_es_robustness partial idiom, weighted).
- SEEDS AND PERMUTATION COUNTS (complete, immovable): weighted_perm_p K=9999, seed
  20260716+panel_index; wpartial K=5000, seed 20260716+100+panel_index; sqrt(k) secondary K=2000,
  seed 20260716+500+panel_index; battery draw seeds 424242+draw / 535353 (one stream) /
  646464+draw / 757575+draw with planted-check perm K=2000 and battery partial K=500. Panels are
  indexed in sorted-name order (academic_experts=0, senate_insiders=1).

## Instrument (byte-frozen; no refit; nothing selected in this round)

- The O composite member scores are read VERBATIM from the shipped
  `big5_gold_anchored.json` -> traits.O.members[*].O (standardized; selected variant
  blue_pink_baseline, weights 0.5 blue_text_o / 0.5 pink_observer_o; coverage 509). No weight,
  channel, roster, or scale decision of any kind is made in this round — the weighting is the only
  degree of freedom and it is fixed above.
- Covariates for bar 5, construction pinned: both from fec/legislators.csv joined via
  congestion.json's bioguide field (the b5_es_robustness / b5_n_matrix gender idiom, re-stated
  locally because importing b5_n_matrix executes the corpus featurizer): female = gender == 'F';
  party_R = party == 'Republican' (congestion.json itself carries NO party field — adversarial-
  review catch; legislators.csv party values are Republican/Democrat/Independent). DEGENERACY
  ABORT: each covariate must show >= 5 ones and >= 5 zeros among each panel's evaluated members,
  else ABORT WITHOUT CONSUMING (a silently broken join would delete bar 5's controls).

## Roster (pinned at lock)

- Insider-evaluated members: the shipped 46 matched (45 with gold O non-null); academic-evaluated:
  52. Exact counts re-verified by the look script against the mapped panels at run time; mismatch
  = ABORT WITHOUT CONSUMING.

## Input pinning (the look ABORTS without consuming on any mismatch)

Pinned 2026-07-16 at a verified-quiescent moment (pipeline lock absent, mtimes stable).
- big5_senate_expert_gold.json  SHA-256 `ff5a948361f478cf7d7da2ce84e333594b242cb65574760dd285a8dbd57afe7a`
- big5_gold_anchored.json       SHA-256 `2b351af4c8fd077cc7fd10b05001a2843f850a3a83f956d5ac75b644a4317c13`
- congestion.json               SHA-256 `ddc9d746600dbdfc60b76c54537662e19c758cbfb9d7a478a71b7bf90cd727a6`
- fec/legislators.csv           SHA-256 `c5a6cbdbaae0bb19faa89852c29922809ececc70b97c149b4709588087e5e391`
- COUNTS insiders/academics/coverage `45`/`52`/`509`
  (insiders = EVALUABLE insider members: gold-O non-null AND in the composite — the shipped 46
  matched minus the O-null row; academics likewise; coverage = O-composite member count. The gate
  parses this line, re-derives all three at run time, verifies n >= 30 per panel, and requires the
  parsed pin-name set to equal exactly the four files above — a malformed pin line refuses.)
- Covariate composition among evaluated members (recorded at lock; enforced by the >=5/>=5 abort):
  insiders female/R = `9/21 of 45`, academics female/R = `16/24 of 52`.

## Bars (ALL must hold; locked here, no post-lock movement)

1. Insiders: weighted r >= +0.20
2. Insiders: weighted one-sided permutation p < .10
3. Insiders: weighted diagonal dominance — weighted own-O r strictly exceeds max |weighted r| of
   the composite against gold C, E, A, ES in the insider panel
4. Academics RE-CLEAR under the same weighting: weighted r >= +0.20 AND p < .10 AND weighted
   diagonal dominance (no trading panels)
5. Gating confound partial: weighted partial r(composite, gold-O | female, party_R) >= +0.10 in
   EACH panel
6. Adversarial re-derivation: the deterministic pipeline is recomputed in a FRESH process
   (--rederive) and every reported statistic must match to 1e-9; any mismatch is a DEFECT HALT —
   nothing is recorded until both computations agree (the Vote Smart deterministic-pipeline
   doctrine).

Power honesty: at n=45, one-sided p<.10 binds near r=.193; the weighted effective n is smaller
than 45, so the p bar binds at a slightly larger r; the r>=.20 bar is expected to be binding.

## Machinery validation (in-process battery; failure REFUSES the look without consuming)

All battery criteria are synthetic or permuted — the real (composite x unpermuted gold) weighted
pairing is computed nowhere in simulate mode. Calibration rationale (adversarial-review change
pre-lock): at n=45/52 a .40 plant against a .30 recovery bar and stochastic confound-refusal
checks would fail CORRECT machinery most of the time (a-priori joint battery pass ~6%) — the
checks below are calibrated so correct machinery passes with high probability while broken
machinery still fails.
(a) PLANTED, seed 424242+draw (5 draws): synthetic gold g = .60-target mixture of the real
    composite plus Gaussian noise over each panel's member set, evaluated with the REAL ratings_n
    weights — weighted machinery must recover: weighted r >= +0.30 and perm p < .05 in BOTH
    panels in >= 4/5 draws (~2-sd margin per panel).
(b) NULL, seed 535353 (200 reps): whole real gold rows permuted within panel (pairing destroyed;
    heterotrait columns travel with the row) — joint r+dominance bars in both panels (p omitted,
    which only makes the null EASIER to pass, so the bound is conservative) may pass in at most
    5/200 reps (measured pre-lock null dual-dominance rate 0.77% implies ~1.5 expected; a <=2
    bound would fail correct machinery ~20% of the time).
(c) CONFOUND REMOVAL, deterministic + gating: for synthetic gold driven by female/party alone
    (seed 646464+draw), the weighted residualization must remove BOTH covariates EXACTLY —
    max |wcorr(residualized gold, covariate, w)| < 1e-9 across panels and draws. The 5-draw
    bar-5 threshold-refusal counts are additionally REPORTED (not gating: at these n a stochastic
    refusal test is a coin flip).
(d) TRUE+CONFOUND, seed 757575+draw (5 draws): planted .60 signal plus additive female/party
    loading — bar 5 must ADMIT (partial >= +0.10) in >= 4/5 draws.
Battery output is recorded verbatim in an addendum whether it passes or fails.

## Pre-declared consequences (fixed wording)

- ON PASS (all six bars): the RESULT records "weighted-criterion association: PASS on both
  panels". Consequences that fire: NOTHING ships. A proposal goes to Paul containing exactly two
  separately gated decisions: (1) ratify reliability-weighted panels (rho1=.25 SB weights) as the
  gate criterion for O in fec/b5_gold_multitrait_validate.py, with every other trait's gates
  recomputed ONLY as a firewalled annotation (no status may move — the no-status-change clause
  outlives this look); (2) upgrade O's label to ACTIVE_EXTERNAL_GOLD_ANCHORED. Declining either
  leaves the shipped state; the RESULT stands as evidence either way.
- ON MISS (any bar): "the criterion-weighting route for O is CLOSED under this gold" — the closure
  covers ANY senator re-weighting scheme over the preserved rater counts (SB weights at any rho1,
  sqrt(k), k-thresholded subsetting, pooled-panel reweighting) and any re-anchoring of the same
  idea. O remains ACTIVE_ONE_PANEL_ASSOCIATION_SUPPORTED with the academic panel. The methods
  ledger records the closure with this prereg's motivating numbers.
- FRAGILE = MISS: bars cleared but the fresh-process re-derivation disagreeing (bar 6) is a defect
  halt; if the recomputation then clears with corrected code, that is still recorded as the one
  look's outcome only if byte-identical statistics are produced by BOTH processes; otherwise MISS
  for all consequences including closure.
- DEMOTION EVENTS: none defined — this look cannot demote anything.

## Secondary reads (reported in the same look; firewalled — they ground NO claim, artifact, or
desk change, and cannot rescue a miss)

- sqrt(k)-weighted r, permutation p (K=2000, seed 20260716+500+panel_index), and weighted
  dominance, per panel.
- k>=2 INSIDER-subset unweighted r and n (insider panel only; the p<.10 threshold there is ~.23 —
  mechanism context only).
- The unweighted r recomputed per panel next to the shipped per-panel r read from
  big5_gold_anchored.json traits.O.validation (drift check only).

## Stopping rule

MISS -> STOP. Do not re-specify past this: no alternative rho1, no alternative weighting family,
no panel subsetting, no "one more variant". The only path that may ever revisit O's insider panel
is a future criterion-side round Paul initiates on NEW gold data (none is expected to exist).

## Look gate (complete refusal conditions, enforced by fec/b5_o_weighted_look.py)

- This file absent, or the locked status marker line absent -> refuse (not consumed).
- Newline-anchored `## RESULT-OW` heading already present -> refuse (consumed; one look only).
- Parsed pin-name set != exactly the four declared files -> refuse (a malformed pin line cannot
  silently drop a file out of verification).
- Any pinned SHA-256 or COUNTS value mismatching the live inputs, or any panel below n=30, or any
  covariate below the >=5/>=5 composition floor -> ABORT (not consumed).
- In-process battery failure -> refuse (not consumed; disposition = RETIRED WITHOUT A LOOK, see
  Compliance).
- `--rederive` is gated IDENTICALLY to the look (refuses unless the gate reads READY; after the
  RESULT heading is recorded it refuses forever) — there is no ungated computing path.
- No-arg invocation prints lock/look/fingerprint status and exits; `--simulate` runs the battery
  only; `--look` runs battery then the one look then the fresh-process bar-6 comparison over the
  ENTIRE flattened RESULT.

## Discipline

One look, consumed forever by the newline-anchored `## RESULT-OW` heading. No LLM calls anywhere
in this round (arithmetic only). No bar, seed, roster, weighting, or wording changes after the
lock commit; permitted addenda are battery records, the RESULT, and dated annotations only. The
look script and this prereg ride the same lock commit. Data inputs are read from the LIVE tree
root via MONEYBALL_ROOT; the script writes NOTHING except stdout (the RESULT block is appended to
this file manually, verbatim, and committed the same session).
