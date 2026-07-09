# Psych-audit round 4 — the fifth trait re-anchored as NEUROTICISM (text → behavioral reactivity)

STATUS: LOCKED (2026-07-09, committed before any look; adversarially panel-reviewed pre-lock, 4 lenses, all
required changes incorporated). User directive (Paul, 2026-07-09): "switch over to Neuroticism … fix
everything else." Goal: the FIRST per-trait criterion-validity test of a text fifth-trait read against a
genuinely behavioral criterion — `reactivity_z` (live-interview cutoff proneness, round-3's shipped engine
N-slot). Method locked to prevent overfitting under pressure. ONE look. (Titled "psych-audit round 4" to
avoid collision with big5_round4_prereg.md, the 2026-07-07 embedding round — different program.)

## Compliance with recorded closures (why this look is legitimate)

- **Not a CT-CM/halo re-spec** (big5_halo_neuroticism_prereg.md stopping rule respected): this is per-trait
  EXTERNAL CRITERION validity — §15's field-correct bar ("PER-TRAIT EXTERNAL CRITERION VALIDITY, not A-ES
  discriminant correlation").
- **Genuinely new external criterion, with the adverse prior disclosed**: `reactivity_z` did not exist when
  §17 took its look or §18 closed the ES routes; round-3 shipped it afterward and explicitly reserved this
  test (session memory psych-audit-2026-07-09.md: "Did NOT compute text-N × cutoff — that's a look; prereg
  if ever wanted"; NOT in methods §19 — the reservation lives in the memory record). **Adverse prior on
  record**: the halo look (big5_halo_neuroticism_prereg.md RESULT, 2026-07-08, N=265) recorded
  corr(interaction-N composite, pink_ES) = **+0.013 NULL**, and that composite CONTAINED z(cutoff). This
  design differs in every load-bearing way — that was an UNSUPERVISED raw composite (diluted by burst,
  later shown SB .04 situational noise, and by dominance-flavored defense/discmark), unshrunken,
  correlated against the Pink LLM ES read (itself 0/5 diagonal-dominant); this is a SUPERVISED Empath
  ridge trained directly on the cutoff-only SB .43 survivor, and Pink-0/5 → supervised-3/5 (§17) is the
  recorded precedent that supervision finds what raw scores lack. Still: **Honest prior: LOW.** A MISS is
  the expected outcome and will be recorded as final.
- **Voice-ES closure (PERMANENT) untouched**: zero audio anywhere in this round.
- **NPAT / Vote Smart untouched**: the ES-construct external-survey path stays user-gated, unclaimed here.
- **Framing**: the fifth trait is analyzed on the N pole (`+reactivity_z` = N+), per the round-3 reframe.
  No ES-framed record (§16/§17/§18) is amended by this look; those results stand as written.
- **A is OUT OF SCOPE BY CONSTRUCTION**: A's §17 dominance failure is against the C (+.210) and O (+.197)
  columns, which this round does not alter. Whatever this look returns, A's state remains "criterion-valid
  (+.183, perm-p .0004), not discriminant" — no A claim may be derived from this round.
- **Core-matrix NO-STATUS-CHANGE clause**: the look reproduces the full §17 6-model matrix on refreshed
  inputs; the reproduced core×core cells **cannot change any core trait's status in EITHER direction** —
  no promotion of A or ES from drift, no demotion except the reactivity-column demotion event defined
  below. Any core-core flip observed is recorded as input-drift ONLY; re-adjudicating any §17 verdict
  requires its own future prereg. Specifically: an apparent A dominance in the reproduction is drift, not
  evidence, and grounds no claim.

## Instrument (locked = the §17 machinery, IMPORTED from fec/b5_behavioral_instrument.py)

- Features: `featurize()` verbatim — Empath 194 categories over full member text (all speeches +
  non-repost tweets, 600k-char cap), z-scored within the full MEM roster, cache `b5_empath_cache.json`
  (verified warm: 456/456, 0 cold). Featurization never sees criteria.
- Model: `oof()` verbatim — per-trait Ridge, outer 5-fold × seeds [7,17,29,43,61] averaged OOF, inner
  GridSearchCV alphas [1,3,10,30,100,300,1000] cv=3 neg-MSE.
- Permutation test: `exact_perm_p()` verbatim — exact, K=5000, one-sided r>0, seed **20260708** (the
  function default, unchanged from §17 — deliberately NOT varied).
- **New code, complete list** (nothing else): criterion assembly for N; subset masking + the masked
  matrix; the Frisch–Waugh gating partial (mirroring fec/b5_es_robustness.py; its permutation seed
  **20260710**, the partial_test default); the noiv corpus builder; the masked simulate battery
  (a)–(d) below; Williams' t for the demotion guard; gate/fingerprint plumbing. Script:
  `fec/b5_n_matrix.py`, PREREG constant = THIS file (big5_n_matrix_prereg.md at repo root).

## Roster and criteria (exact, verified pre-lock, read-only)

- Core roster MEM = `load_corpus()` verbatim (§17 eligibility). **MEM = 456 (exact).**
- Core criteria unchanged: A=cooperation_z, C=diligence_z, E=visibility_z, O=breadth_z; the §17 ES row
  (residual-GMP) is also reproduced — as bar-4 competitor and no-status-change reference, NOT as a verdict
  candidate.
- **Fifth = N: `+reactivity_z` exactly as shipped** in behavioral_dispositions.json (shrinkage included —
  the engine input IS the construct under test). **MEM_N = MEM ∩ reactivity_z non-null = 201 (exact).**
  Gender coverage verified pre-lock: 0 of MEM_N (and 0 of MEM) lack legislators.csv gender — **all bars
  1–5 share the single roster MEM_N = 201.** No fallback ladder (a direct behavioral criterion needs none).
- **Input pinning** (recorded at lock; the look ABORTS without consuming if any mismatch):
  behavioral_dispositions.json SHA-256 `6b9bb9d2a15ce9be1ddd0a8ec63c51fef1449e68f37ffda08b3c70e6564397d7`
  (2026-07-09 17:04 vintage); interaction_features.json SHA-256
  `55d908d7ed1a7b1d0b7cb889f01484f6d454a9bed57847cf39ebfdcf68f26553`; social_media.db speeches rows
  **234,827**, non-null posts rows **29,098**; MEM must equal 456 and MEM_N must equal 201 at look time.
  The RESULT reports these fingerprints verbatim.
- Input-freshness note: core-row numbers may drift slightly from §17's recorded values (inputs refreshed
  at the round-3 ship). Drift >0.02 on any §17 diagonal is reported in the RESULT as input-drift. Such
  drift does NOT re-open §17 (see no-status-change clause).

## Evaluation protocol (masked matrix, pre-declared)

- pred_O/C/E/A/ES: `oof(X, crit)` on the full MEM roster (deterministic §17 reproduction, six-model set).
- pred_N: `oof(X_sub, react_sub)` trained/evaluated within MEM_N only (X rows taken from the
  roster-z-scored matrix; no re-z-scoring on the subset).
- Matrix cells: core row × core col on MEM (N=456); **any cell involving N (N row × all cols; all rows ×
  N col) on MEM_N (N=201)** (pairwise complete — all N-involved comparisons share one roster). The RESULT
  prints each cell annotated with its N.
- **Non-finite rule**: any correlation (matrix cell, bar statistic, or permutation replicate) that
  evaluates non-finite is recorded as 0 for all bar and dominance purposes (i.e., counts toward MISS),
  noted in the RESULT; no re-run.
- **Demotion event** (the only §17-touching outcome, pinned): for a §17-passing trait t, computed WHOLLY
  on MEM_N with this run's pred_t (full-MEM OOF restricted to MEM_N rows): a demotion event is declared
  iff |r(pred_t, reactivity_z)|_MEM_N > |r(pred_t, crit_t)|_MEM_N **AND** Williams' t for dependent
  overlapping correlations (Steiger 1980; shared variable pred_t, computed on sign-aligned correlations
  so the compared pair is positive; two-sided) gives p < .05. An inversion failing the significance guard
  is recorded as "stratum inversion, n.s." — reported verbatim, no demotion, honest count unchanged. A
  declared demotion is recorded as "not row-dominant on the interview stratum (MEM_N)": §17's full-roster
  verdict is ANNOTATED, not reversed; every forward-going dominance claim for that trait carries the
  mandatory caveat, and the headline count is restated as x/5-with-caveat.

## Bars for N (ALL five must hold; no relaxation, no re-scoping after this commit)

1. Own held-out r(pred_N, +reactivity_z) ≥ **+0.15** on MEM_N.
2. Exact permutation p < **.05** (K=5000, seed 20260708). (At N=201 this binds at r≈.117 one-sided —
   bar 1 remains the binding magnitude bar; stated for power honesty.)
3. **Row-dominant**: |own r| ≥ |r(pred_N, crit_c)| for all four core criteria (all on MEM_N), own r > 0.
   (§17's `>=` semantics kept verbatim for machinery identity.)
4. **Column-specific, strict**: |r(pred_N, react)| must STRICTLY exceed |r(pred_c, react)| for every
   other model c ∈ {O, C, E, A, ES(residual-GMP)}, all on MEM_N; an exact tie = FAIL. (The §17
   `es_criterion_valid` role; pred_ES included deliberately — it is the most plausible rival reader of an
   N-flavored criterion, and excluding it would be a hidden leniency. The bar-3 `≥` vs bar-4 strict
   asymmetry is deliberate: own-row generosity at exact ties matches §17 machinery; column-specificity is
   held strict. Power note for the RESULT: the five competitors train on ~456 rows vs pred_N's 201 — a
   pass is not rigged in N's favor, and a miss is partly power-limited.)
5. **GATING confound partial, volume-hardened**: Frisch–Waugh partial r(pred_N, reactivity_z |
   gender, party, log(1+turns), sh) ≥ **+0.10 AND its exact perm-p < .05** (K=5000, seed 20260710 —
   the b5_es_robustness.py partial_test default, mirrored verbatim; permute the residualized criterion
   against the fixed residualized prediction), on MEM_N, where sh = √(min(1, turns/150)) — the shrinkage
   weight itself. Conditioning on volume is deliberate: the criterion is already recorded gender +.02 /
   party −.09 clean, so a gender/party-only partial would be near-vacuous; volume is this repo's
   documented proxy failure mode. Verified pre-lock (criterion side): r(react, log turns) = −.066,
   r(react, sh) = −.090, r(react, visibility_z) = +.036 — this gate costs a true positive nothing.
   Effective magnitude bar = max(+0.10, r_crit ≈ .117 via the p-clause).

Attenuation honesty, stated pre-look: the criterion's program-split-half reliability is SB≈.43, so the
attenuation ceiling on observed r is ≈ √.43 ≈ .66 × the text-side ceiling — the +0.15 bar is genuinely
demanding against this criterion. It is retained anyway. A MISS under attenuation is a MISS.

## Secondary reads (REPORTED in the same look; see firewall below)

- r(pred_N, unshrunken cutoff) on MEM_N (unshrunken = interaction_features.json per-member `cutoff`,
  turns≥30, no shrinkage factor) — is the shrinkage policy driving the result?
- Gender/party-only Frisch–Waugh partial and plain log-turns partial (demoted from gating by panel —
  superseded by bar 5's combined conditioning set; reported for continuity with the round-2 record).
- Raw corr(pred_N, gender) and corr(pred_N, party) on MEM_N — fairness record.
- Own r restricted to MEM_N members with n_programs ≥ 2 — program-cluster fragility probe.
- Per-member interview share of the capped corpus (median / p75 across MEM_N) — context for noiv.

## The noiv probe — SHIP-GATE (not verdict gate), fully pinned

- Corpus: speeches WHERE source != 'INTERVIEW' (i.e., CREC + CHRG — CHRG retained deliberately:
  non-interview spoken text) plus non-repost posts; same concat order and 600k cap as `load_corpus()`.
- Featurization: same `featurize()` with the module CACHEF attribute swapped to
  **b5_empath_cache_noiv.json** for the call and restored after — `b5_empath_cache.json` is NEVER
  touched by the noiv pass (verified hazard: the cache is keyed member→{hash,vector}; reuse with
  different text would clobber the warm §17 entries). Run order: primary featurization first, then noiv.
- Roster: features z-scored within full MEM (mirroring the primary); train/eval on MEM_N ∩ {noiv text
  > 2000 chars}; dropped count reported.
- **Ship-gate rule**: consequences (a)–(c) below additionally require r(pred_N_noiv, reactivity_z) > 0
  with exact perm-p < .05 (K=5000, seed 20260708) on the noiv-eligible subset. If bars 1–5 pass but the
  ship-gate fails, the outcome is recorded as **"PASS — interview-stratum text only
  (shared-source-dependent)"**: NO b5_n_text.json, NO desk reframe; methods §20 + memory record only;
  the route is CLOSED either way. Rationale, stated now so this cannot be read as post-hoc bar-shopping:
  a noiv miss cannot distinguish leakage from "interviews are the only unstaffable spontaneous text
  carrying N" (§19's own observation), so it must not overturn the verdict; but extrapolating beyond the
  interview stratum (the 533-member artifact, the desk axis) is only licensed if signal exists outside
  interview text — which only noiv tests.
- Additional mandatory caveat: if the ship-gate passes but r(pred_N_noiv, react) < half the primary own
  r, every shipped claim carries the fixed caveat "interview-leaning text signal" (wording fixed here).

## Machinery validation BEFORE the look (in-process, no look consumed)

`--look` RUNS THE FULL SIMULATE BATTERY FIRST, in-process, and aborts before any real pairing if any
check fails (no sentinel files — the gate is the battery itself). `--simulate` runs the same battery
standalone. Real trait × criterion pairings are never computed in simulate. Pinned battery:
- (a) PLANTED (rng seed 424242): synthetic criteria with real ~r .4 signal from X — core plants must
  recover ≥4/5; the masked-N plant must clear bars 1–4 (bar 5 reported; near-vacuous on unconfounded
  synthetic signal by construction).
- (b) NULL (rng seed 535353): real criteria permuted before any pairing (pairing destroyed) — core 0/5
  AND the N leg must MISS the full 5-bar stack at the true subset size n=201 (perm-p calibration checked
  at 201, not 456).
- (c) CONFOUND-ONLY (rng seed 646464): synthetic N criterion driven by gender/party/volume alone — bars
  1–2 may pass (text encodes demographics); **bar 5 must FAIL** (partial < +0.10).
- (d) TRUE+CONFOUND (rng seed 757575): planted signal plus additive gender/party loading on both sides —
  **bar 5 must PASS** (≥ +0.10).

## Pre-declared consequences

- **N PASS (bars 1–5)**: before any promotion the pass is **adversarially re-derived** (fold-partition
  robustness): all six model prediction vectors recomputed with fresh OOF seeds [101,113,127,139,151]
  (the module SEEDS constant swapped and restored; permutation seeds stay pinned as locked), and the
  re-derivation must again clear **ALL FIVE bars**. Failure = recorded **FRAGILE = MISS for ALL
  consequences INCLUDING closure** (the route closes; both runs reported verbatim). On a re-derived PASS
  + noiv ship-gate: (a) artifact `b5_n_text.json` — OOF preds for MEM_N + final-refit reads (single
  Ridge on all MEM_N rows, alpha by GridSearchCV cv=5 over the locked grid, applied to primary-corpus
  Empath features for every member with >2000 chars text; others null; `validated` flag = MEM_N
  membership); (b) desk fifth Big-5 axis reframes ES→N ('EmoSt'→'Neurot'), Blue trace sourced from
  b5_n_text — **the desk change replaces only WHICH score the fifth-axis Blue trace displays; NO
  recorded caveat is deleted anywhere: §16's gender-confound annotation, the voice-ES desk line and its
  caveat, and every ES-framed record stand verbatim as history** (Pink overlay + its §15 halo caveat
  unchanged); (c) audit_full schema guard with the recorded r pinned (the b5_es_voice guard idiom);
  (d) methods §20; (e) memory update. Every claim carries the stratum caveat (validated on MEM_N=201,
  the interview-covered stratum).
- **N MISS on any bar**: the Empath-text→reactivity route is **CLOSED** — one look, no re-spec, no bar
  shopping, no seed shopping. The closure COVERS the secondary variants (pred_N_noiv IS
  Empath-text→reactivity; the unshrunken-criterion variant IS the same route) — none may be resurrected
  as a re-spec. The fifth text axis stays ES-framed with existing caveats. Round-3's reactivity_z engine
  slot is UNAFFECTED either way — it is a measured behavior, valid by construction for its engine ROLE
  (§19); this look tests the TEXT read of N, not the disposition. **The MISS is recorded in methods §20
  and the memory index the same session** (the §18 precedent: closures are recorded so no future session
  re-runs them).
- **Demotion event on any core trait**: recorded in RESULT + methods §20 per the pinned rule above.
- **Secondaries firewall**: no claim, promotion, artifact, desk change, or methods claim may be derived
  from any secondary regardless of outcome (the noiv SHIP-GATE above is the sole pre-declared exception,
  and it can only restrict, never expand, what ships).
- Either way: the outcome appends verbatim under a `RESULT-N` H2 heading (gate = newline-anchored
  heading match, per the @72690c9 lesson), MISSes included, committed same session.

## Look gate (complete refusal conditions)

`fec/b5_n_matrix.py --look` REFUSES if: (a) big5_n_matrix_prereg.md is absent; (b) the literal line
`STATUS: LOCKED` is absent (prereg unlocked — the b5_panel_score.py idiom); (c) the file already
contains a newline-anchored `RESULT-N` H2 heading (look consumed); (d) any input fingerprint or roster
count mismatches the pinned values (input drift — aborts WITHOUT consuming; fix inputs or re-lock);
(e) any simulate-battery check fails in-process. Default no-arg mode = status (lock state, gate state,
fingerprint check, no look).

## Discipline

Locked + committed before the look. Machinery imported from the §17 look (no re-implementation drift);
all new numerics enumerated above, none discretionary. ONE look. No LLM calls (Empath + sklearn
arithmetic only). No audio. No bar/seed/roster/wording changes after this commit. The pressure to "make
N pass" makes these guards MORE binding, not less. Honest prior: LOW — and a MISS closes the route
permanently, recorded with the same care as a pass.
