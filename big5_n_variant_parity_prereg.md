# N vs the Senate gold — variant-parity round (constrained-floor composites, measure-side)

STATUS: LOCKED (2026-07-16, committed before any look; adversarially reviewed pre-lock — one
CRITICAL, two HIGH, three MEDIUM, two LOW required changes ALL incorporated (gated --rederive,
computed baseline drift-check secondary, enforced count pins + pin-set exactness, covariate
source correction to legislators.csv + degeneracy abort, full-RESULT re-derivation, battery
disposition + per-outcome terminality + n>=30 conjunct + power line, plant recalibrated to .60
for parity with the O review); user-authorized: Paul 2026-07-16, "Optimize according to your
recommendations, Test-Driven Design". The lock commit CONTAINS the executable spec:
fec/b5_n_variant_look.py and fec/b5_gold_criterion_probes.py ride this same commit.)

User authorization: Paul, 2026-07-16 — "Optimize according to your recommendations, Test-Driven
Design", following the presented recommendation of an "N variant-parity round" (giving N the same
constrained-variant treatment E already received). This is a MEASURE-SIDE round inside the
existing, shipped LOO-OOF machinery: the criterion (both gold panels, unweighted) is untouched;
the candidate channels are unchanged and already validated project quantities; the ONLY new degree
of freedom is two pre-declared weight-floor variants. No new instrument basis exists, so the
round-6 anti-basis-shopping clause is not triggered.

## Compliance with recorded closures

- The promoted narrow affective-content N slot (round-7, 2026-07-11) is NOT in play: the engine
  N-slot, `affective_n.json`, and RECEPT_N are untouched under every outcome. This round concerns
  only the broad display/profile gold-anchored composite.
- Round-4 (text-N vs reactivity criterion) stays as recorded: RETIRED WITHOUT A LOOK, DATA-GATED
  at MEM_N >= 250. This round neither takes nor licenses that look (different question, different
  criterion). Its data gate now reads ~270 eligible by the cutoff/turns>=30 construction — noted
  for Paul, not acted on here.
- Voice-ES (closed permanently), audio-E (miss), dialogic-assent A, NPAT-current-roster, st_mean
  round 6: none reopened.
- Blue-on-pink calibration: not touched (weights over independently standardized channels via the
  shipped OOF machinery is gold-fitting through the ONLY permitted gate).
- The equal-weight no-gold-fitted E control axis: untouched.
- NO-STATUS-CHANGE clause: O, C, E, A statuses cannot move in either direction from this look.
- NO ENGINE CHANGE flows from this look under any outcome.
- Gold-burn ledger: this gold has absorbed the control-axis look and the v2 fitting round. This
  prereg pre-declares itself the TERMINAL N-composite round against gold vintage
  `big5_senate_expert_gold.json` (pdf pin 43c98926...) — terminal under EVERY outcome: on a MISS
  the N-composite variant space freezes permanently under this gold; on a PASS (ratified or
  declined by Paul) no further N-composite variant round may be run against this gold either —
  the RESULT is the final N-composite evidence under this vintage.
- Battery-refusal disposition (pre-declared): battery failure = RETIRED WITHOUT A LOOK (nothing
  consumed). The battery is deterministic (fixed seeds), so a refusal cannot be re-rolled; the
  only permitted amendment is round-4 Addendum-1 style — machinery validation ONLY, with bars,
  variants, roster, seeds, and every consequence clause byte-identical to the lock — and the
  retirement addendum must pin its successor condition verbatim.

## Hypothesis and honest prior

HYPOTHESIS: the shipped N selection (blue_pink_baseline, 10% affective_content_n / 90%
pink_observer_n; insiders r=.3743 strict PASS, academics r=.1234 FAIL) over-weights the Pink
observer channel's insider-proximal variance. Pre-declared constrained variants that FORCE the
affective and behavioral channels in — exactly the constrained treatment E's selected variant
received — yield an OOF composite loading more on the shared ES factor and clearing the
association gate on BOTH panels with diagonal dominance.

MOTIVATING CRITERION-SIDE EVIDENCE (pre-lock, criterion-vs-criterion only; reproducible via
fec/b5_gold_criterion_probes.py): cross-panel ES agreement r=.412 on the 40-member roster overlap
(.437 all both-panel senators) — essentially E's .426, and E's composite clears both panels at
.493/.505. The academic miss margin is .077 (~0.55 SE at n=52). Insider single-rater rows are
noise-like across traits (see the O prereg's stratified table); the panels are not measuring
incompatible constructs.

HONEST PRIOR: MODERATE-LOW (~35-50%). The free 0.10-grid search over the SAME three channels
already preferred 10/90 by worst-panel OOF r — a constrained variant can only win the bars through
better OOF generalization (the regularization path E's constrained variant took), not through a
better training fit.

ADVERSE PRIORS DISCLOSED (each verbatim-relevant):
- reactivity_z is EXTRAVERSION-contaminated on record (round-7 re-anchor, 2026-07-11: +.185 with
  E, -.14 with N). Forcing it in can buy insider r with E variance and BREAK diagonal dominance —
  which is exactly why dominance in BOTH panels is a locked bar, not a hope.
- The shipped all_channels variant (free weights over these same three channels) already exists in
  big5_gold_anchored.json and did not beat 10/90 on worst-panel OOF r.
- A 2026-07-16 session probe computed a VOID look-fragment (Steiger on fitted scores); none of its
  numbers appear in, or motivated, any bar here.

## Instrument & protocol (imported, zero re-implementation)

- Machinery imported VERBATIM from fec/b5_gold_multitrait_validate.py: `raw_channels`,
  `oof_variant`, `map_gold` (via its own import), `gold_value`, permutation seeds
  (20260715 + panel_index + 17 * trait_index) — leave-one-member-out out-of-fold weight selection
  on the non-negative 0.10 simplex grid, held-out senator labels never entering their own score,
  panels evaluated independently. No constant, seed, or fold rule is redefined.
- THE TWO PRE-DECLARED VARIANTS (the complete new-decision list — nothing else is new):
  (V1) `all_channels_reactivity_min_10pct`: channels {affective_content_n, pink_observer_n,
       behavioral_reactivity}, minima {affective_content_n: .10, pink_observer_n: .10,
       behavioral_reactivity: .10}.
  (V2) `blue_pink_affective_min_30pct`: channels {affective_content_n, pink_observer_n}, minima
       {affective_content_n: .30, pink_observer_n: .10}.
- SELECTION RULE (pre-declared, mirrors the shipped non-E rule): the variant with the greater
  (worst_panel_r, mean_panel_r) tuple is THE candidate; the other is reported as a firewalled
  secondary. Bars are evaluated on the selected variant ONLY. There is no third variant and no
  post-look selection change.
- REPORTED-ONLY DRIFT CHECK (computed in the same look, firewalled, never enters selection or
  bars): the shipped `blue_pink_baseline` construction (both primary channels, minima .10/.10) is
  re-run through the same imported machinery and reported next to the shipped numbers.
- New code, complete list (nothing else): the bar evaluation over the returned panel results, the
  gender/party confound partial on the OOF predictions (unweighted Frisch-Waugh partial + exact
  one-sided permutation p, K=5000, seed 20260716; the b5_es_robustness idiom restated locally
  because importing b5_n_matrix executes the corpus featurizer), and the battery constructors
  below. Battery seeds: 424242+draw / 535353 (one stream) / 646464+draw / 757575+draw.
- Covariates, construction pinned: both from fec/legislators.csv joined via congestion.json's
  bioguide field: female = gender == 'F'; party_R = party == 'Republican' (congestion.json
  carries NO party field — adversarial-review catch). DEGENERACY ABORT: each covariate must show
  >= 5 ones and >= 5 zeros among the OOF-eligible members, else ABORT WITHOUT CONSUMING.

## Roster (pinned at lock)

Panels from `map_gold` over the current congestion roster (insiders 46 matched / 45 with ES
non-null; academics 52). The OOF eligible set = senators with averaged gold (union roster, ~58).
Exact counts re-verified at run time; mismatch = ABORT WITHOUT CONSUMING.

## Input pinning (the look ABORTS without consuming on any mismatch)

Pinned 2026-07-16 at a verified-quiescent moment (pipeline lock absent, mtimes stable).
- big5_senate_expert_gold.json      SHA-256 `ff5a948361f478cf7d7da2ce84e333594b242cb65574760dd285a8dbd57afe7a`
- big5_blue_validated.json          SHA-256 `ebaae2fa5524a3ea7dd712f6ae55cb248657ca03c57bc3d00162824ea7bad4e1`  (affective_content_n source channel)
- big5_llm_opus.json                SHA-256 `4b462228f5445dec43d66fc04e801cbd1974d31d569908938150604c8ec19632`  (pink_observer_n source channel)
- behavioral_dispositions.json      SHA-256 `56dbd11bf7bd98a7cafdd4e53b6120b9ff9b4a02ccee2a28050233c8e3404cc8`  (behavioral_reactivity channel)
- congestion.json                   SHA-256 `ddc9d746600dbdfc60b76c54537662e19c758cbfb9d7a478a71b7bf90cd727a6`
- fec/legislators.csv               SHA-256 `c5a6cbdbaae0bb19faa89852c29922809ececc70b97c149b4709588087e5e391`
- COUNTS insiders/academics/eligible `46`/`52`/`58`
  (matched panel sizes and the OOF-eligible n = senators with averaged gold. The gate parses this
  line, re-derives all three at run time, verifies n >= 30 per panel, and requires the parsed
  pin-name set to equal exactly the six files above — a malformed pin line refuses.)
- Covariate composition among OOF-eligible members (recorded at lock; enforced by the >=5/>=5
  abort): female/R = `16/27 of 58`.

## Bars (ALL must hold on the SELECTED variant; locked here)

1. Academics: n >= 30 AND OOF r >= +0.20 AND one-sided permutation p < .10 AND diagonal dominance
   (the shipped gate including its n element, now required on the panel N currently fails)
2. Insiders: n >= 30 AND OOF r >= +0.30 AND p < .10 AND diagonal dominance (stricter than the .20
   gate so a pass cannot be bought by trading the currently-passing panel down)

Power honesty: one-sided p < .10 binds near r=.18 at n=52 and r=.19 at n=45, so the r bars are
the binding constraints on both panels; the ~.41 cross-panel ES agreement puts the shared-factor
ceiling near .5 per panel — bar 2's .30 sits inside it, bar 1's .20 well inside it.
3. Gating confound partial: partial r(OOF predictions, gold-N | female, party_R) >= +0.10 in EACH
   panel (exact perm p reported; the partial magnitude is the gate)
4. Adversarial re-derivation: the full deterministic pipeline recomputed in a FRESH process
   (--rederive) matches every reported statistic to 1e-9; mismatch = DEFECT HALT.

## Machinery validation (in-process battery; failure REFUSES the look without consuming)

Real channels x REAL UNPERMUTED gold is computed nowhere in simulate mode. Plant targets follow
the O round's adversarial-review recalibration (a .40 plant against a .30 recovery bar at n~45-58
would fail correct machinery too often; .60 gives ~2-sd margin).
(a) PLANTED, seed 424242+draw (5 draws): synthetic gold built as a .60-target mixture of a random
    non-negative simplex mix of the three real channels plus Gaussian noise, written into
    synthetic panel rows as ES = -(signal) (other trait columns = independent noise for the
    dominance rows); the full two-variant + selection machinery must recover it: selected-variant
    OOF r >= +0.30 with p < .05 in both synthetic panels in >= 4/5 draws. Single plant per draw
    (the round-4 orthogonalization lesson does not arise; recorded so nobody adds a second plant
    casually).
(b) NULL, seed 535353 (50 reps): whole real gold rows permuted within each panel (heterotrait
    columns travel with the row) — the full machinery (both variants, selection, bars 1-2 sans p;
    omitting p only makes the null EASIER to pass, so the bound is conservative) may pass in at
    most 1/50 reps (estimated true per-rep null joint rate 0.2-0.5%).
(c) CONFOUND REMOVAL, deterministic + gating: for synthetic gold driven by female/party alone
    (seed 646464+draw), residualizing the confound-only criterion must remove BOTH covariates
    EXACTLY — max |r(residualized gold, covariate)| < 1e-9 across panels and draws. The 5-draw
    bar-3 threshold-refusal counts are additionally REPORTED (not gating).
(d) TRUE+CONFOUND, seed 757575+draw (5 draws): planted .60 signal plus additive female/party
    loading — bar 3 must ADMIT (>= +0.10) in >= 4/5 draws.
Battery output recorded verbatim in an addendum, pass or fail.

## Pre-declared consequences (fixed wording)

- ON PASS (all four bars): NOTHING ships. A proposal goes to Paul: adopt the passing constrained
  variant into fec/b5_gold_multitrait_validate.py `variants_for('N')` (mirroring E's constrained-
  variant rule) and regenerate big5_gold_anchored.json — a separate, user-gated promotion; N's
  label upgrade to ACTIVE_EXTERNAL_GOLD_ANCHORED rides that same user decision. Declining leaves
  the shipped state; the RESULT stands.
- ON MISS (any bar): "the N-composite variant space is FROZEN under this gold" — the closure
  covers ANY composite over {affective_content_n, pink_observer_n, behavioral_reactivity}: any
  subset, any weights, any minima, any re-anchoring. N remains
  ACTIVE_ONE_PANEL_ASSOCIATION_SUPPORTED with the insider panel. The ceiling arithmetic and this
  prereg's motivating numbers land in the methods ledger as the closure rationale.
- FRAGILE = MISS: bar-4 re-derivation mismatch is a defect halt; persistent disagreement = MISS
  for ALL consequences including closure.
- DEMOTION EVENTS: none defined; this look cannot demote anything.

## Secondary reads (same look; firewalled — ground NOTHING, rescue nothing)

- The non-selected variant's full results (panels, weights).
- The shipped blue_pink_baseline construction re-run through the same machinery (drift check
  only; reported next to the shipped .3743/.1234).
- Fold-weight mode of the selected variant (interpretability context).

## Stopping rule

MISS -> STOP. Do not re-specify past this: no third variant, no other floors, no other channel
subsets, no re-run at a later corpus vintage against THIS gold. The only future N-composite
evidence path is new gold data (none expected) or the separate round-4 successor (its own gate,
its own prereg, its own criterion).

## Look gate (complete refusal conditions, enforced by fec/b5_n_variant_look.py)

- This file absent, or the locked status marker line absent -> refuse (not consumed).
- Newline-anchored `## RESULT-NV` heading already present -> refuse (consumed; one look only).
- Parsed pin-name set != exactly the six declared files -> refuse (a malformed pin line cannot
  silently drop a file out of verification).
- Any pinned SHA-256 or COUNTS value mismatching the live inputs, or any panel below n=30, or any
  covariate below the >=5/>=5 composition floor -> ABORT (not consumed).
- In-process battery failure -> refuse (not consumed; disposition = RETIRED WITHOUT A LOOK, see
  Compliance).
- `--rederive` is gated IDENTICALLY to the look (refuses unless the gate reads READY; after the
  RESULT heading is recorded it refuses forever) — there is no ungated computing path.
- No-arg = status print; `--simulate` battery only; `--look` battery then the one look then the
  fresh-process bar-4 comparison over the ENTIRE flattened RESULT.

## Discipline

One look, consumed forever by the newline-anchored `## RESULT-NV` heading. No LLM calls
(arithmetic only). No bar, seed, variant, roster, or wording changes after the lock commit;
permitted addenda: battery records, the RESULT, dated annotations. The look script and this
prereg ride the same lock commit. Data reads via MONEYBALL_ROOT from the live tree; the script
writes NOTHING except stdout; the RESULT block is appended manually, verbatim, committed the same
session.
