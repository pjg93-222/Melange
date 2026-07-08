# PRE-REGISTRATION — Incremental validity of the personality N-channel & persona for RECEPTIVITY

**Locked 2026-07-08, BEFORE any real trait×movement association was computed.**
Author: exploration session (branch `claude/compassionate-ellis-d8f98a`). Precedent/harness:
`big5_nomological_prereg.md` + `fec/validate_nomological.py` (the ValiTex label-free method that
legitimized the behavioral basis). This file governs whether the personality signal may be made
**more** load-bearing in the receptivity engine (`fec/receptivity_layer.py` → `susc` →
`susc_mult`/`edge_mult`/`pressure_mult`/`seed_prob` → flip/cascade/optimizer). It does **not**
touch the blended rank (pillars leg/press/inf/demo); psychology is a receptivity signal only.

## Motivation (established before locking — measurement facts, not outcome looks)
- The receptivity engine's susceptibility composite (behavioral basis, production) is
  `susc_trait = .40·coop + .30·N − .20·dil − .10·dom`, where coop/dil/dom are behavioral z-scores
  (`behavioral_dispositions.json`) but **N is the shrunk LEXICAL read** `sh·big5_traits.json[m].N`
  (`sh = min(1, √(tokens/1500))`). N is the one lexical trait never adjudicated: it was neither
  validated nor indicted in `big5_nomological_prereg.md` (no behavioral criterion for it existed).
- A measurement-superior "Pink" LLM read exists (`big5_llm_opus.json`, N = −ES; MTMM-passing,
  split-half N≈.67). **But at the member level lexical-N and Pink-N are nearly orthogonal:
  r = +0.125 (n=509), ρ = +0.131.** Swapping lexical→Pink is therefore NOT a refinement of one
  construct — it substitutes a *different* signal. Offline (faithful to the live engine, max
  |Δsusc|=0.0005): the swap reshuffles susceptibility (Spearman ρ(susc)=0.77), the top-10
  most-pressure-susceptible set overlaps only 50–60%, and 139/533 members change `susc_read`.
  So the swap is decision-relevant and MUST clear a real-criterion gate before shipping.
- Rank impact of any susc change: **0/533** — structurally confirmed (`member_receptivity.json` is
  read by engines + a dashboard color layer only, never the pillar rank). To be re-confirmed at
  ship time via the standard gate (byte-identical ranks).

## Status of this test: EXPLORATORY SCREEN, necessary-but-NOT-sufficient
The only per-member observed-movement criterion available (press-stance dynamics) is **noisy and
confounded** (see Power & Threats). A PASS here therefore **does not authorize an engine change**;
it only promotes a candidate to a future **confirmatory** gate on a *non-text* movement criterion
(roll-call switches / cosponsorship timing — not yet built; avenue 4). A MISS reverts the candidate
(no change; the lexical-N channel stays as-is). One look only; bars below never move after the look.

## Criterion (frozen; reconstructed from `Draft Systems\cu_press_stance_tone.csv`, method = `stance_dynamics.py`)
Per member, per 91-day window, conf-weighted mean of `stance_sign` over **observed** windows only
(no persistence carry). Movement outcomes:
- **PRIMARY Y = `range`** = max−min of observed-window pooled stance, members with **≥3 observed
  windows** (analyzable n = 161 with controls + both N instruments).
- **ROBUSTNESS**: (a) Y=`absmove` (sum of consecutive |Δ|); (b) the ≥2-window set (n = 232);
  (c) reliability-filtered set requiring ≥2 press items in every contributing window.
All predictors and Y standardized within the analyzable roster. This is a PROXY for lobbying
susceptibility (spontaneous/event-driven press-position volatility ≠ movement-when-lobbied) —
a known construct-validity gap, recorded here, not resolved here.

## Predictors & controls
- **Controls (the behavioral basis already in susc):** cooperation_z, diligence_z, dominance_z.
- **Candidate signals tested for INCREMENTAL value over the controls:**
  - H1  lexical-N (current engine channel) — "does N earn its keep at all?"
  - H2  Pink-N (raw_z ES, re-standardized to the lexical-N footprint)
  - H3  Pink-N incremental over {controls **+ lexical-N**} — "does Pink-N add beyond current N?"
  - H4  persona susceptibility `psusc = .60·z(communion) − .40·z(agency)` (already blended at PW=0.30)

## Statistic & test (locked)
Semipartial (part) correlation of each candidate with Y after residualizing the candidate on its
control set. **One-tailed positive** (Byrne: N↑ ⇒ more movable; psusc↑ ⇒ more movable). Significance
by **permutation** (3000 label shuffles, `seed=20260708`), reported as the two-sided |r| 95th/99th
percentile floor. BH-FDR across the H1–H4 family at q=.05.

## Power (computed before the look; no real association used)
Analytic MDE (Fisher-z, one-tailed α=.05, power=.80): n=161 → r=0.195; n=232 → r=0.163.
Permutation noise-floor (95th pct |semipartial r|): 0.155 (n=161) / 0.133 (n=232). **The criterion
is powered only for MODERATE effects** and, because per-window reliability is low (median 1 item/
window), true effects are attenuated — effective MDE is larger than nominal. Small incremental
effects (<~0.13) are indistinguishable from noise here.

## Decision rules (LOCKED — do not move after the look)
For a candidate to **PASS** (→ promote to the confirmatory non-text gate; NOT ship):
1. semipartial r > the permutation 95th-pct floor for its n, **AND**
2. semipartial r ≥ **+0.15** (moderate-effect floor, matched to the power we actually have), **AND**
3. BH-FDR q < .05 within the family, **AND**
4. same-sign on **both** robustness outcomes (`absmove` and the ≥2-window set).

N-swap decision (lexical→Pink) — only meaningful if it also ships later:
- **Swap justified** iff H2 PASSES **and** H3 PASSES **and** Pink-N's simple r(Y) ≥ lexical-N's.
- **Keep lexical-N** iff H1 PASSES and H2/H3 do not.
- **Drop N entirely from susc** (candidate action, user's call) iff neither H1 nor H2 clears rule 1
  (N of either flavor is pure noise on this criterion) — reversion, not addition.
- **Persona**: H4 informs whether PW=0.30 is earning incremental value; PW is user-ratified and is
  NOT changed by this test regardless of outcome (reported for the user only).

## Threats to validity (recorded before the look)
- **Reliability:** median 1 item/(member,window) ⇒ much "movement" is sampling noise (attenuation).
- **Contamination/confound:** Y is classified from CU trade-association press (third-party framing),
  which limits shared-source contamination with member-authored trait text but adds an
  association-*attention* confound. Cannot carry a verdict for text-derived traits alone → the
  necessary-not-sufficient status above.
- **Construct gap:** press volatility ≠ lobbying susceptibility.
- **Class imbalance:** stance_sign is {+1:1068, 0:1126, −1:194}; flips to oppose are rare (≈34
  sign-flippers in the analyzable set).

## Ship gate (applies to ANY engine change arising from this line of work — non-negotiable)
`fec/tests/run_tests.py` (37) green · `fec/audit_full.py` (64) ALL CLEAN · full `run_pipeline.py`
chain · **zero rank delta /533**. Re-standardization, PW, susc weights, and the two cpf physics
are calibrated/user-ratified constants — **no change ships without explicit user ratification.**

---
## OUTCOME — ONE LOOK TAKEN 2026-07-08 (locked; bars above NOT moved). RESULT: MISS (all candidates).
Script: `scratchpad/onelook_incremental.py`. Perm floor (primary, n=161): 95th=0.151, 99th=0.200.

| Hypothesis | PRIMARY (range, n=161) | absmove (n=161) | range ≥2win (n=232) | Verdict |
|---|---|---|---|---|
| H1 lexical-N \| ctrl | −0.020 | −0.014 | −0.028 | **MISS** (wrong sign, ≈0) |
| H2 Pink-N \| ctrl | +0.013 | −0.057 | +0.066 | **MISS** (≪0.151 floor) |
| H3 Pink-N \| ctrl+lexN | +0.016 | −0.056 | +0.068 | **MISS** |
| H4 persona \| ctrl | +0.076 | −0.037 | +0.065 | **MISS** (largest, but <½ floor; sign inconsistent) |

Simple r(Y=range): lexical-N = −0.035, Pink-N = −0.007 (raw, no residualization — the signal is
absent before any modeling, so the null is not a residualization artifact).

**Adversarial validation of the null (not a code bug):** the same pipeline DOES detect effects on
this criterion — `breadth_z` r=+0.217 (clears the floor), `cooperation_z` r=+0.106 — while N and
persona do not. This also exposes a **volume/breadth confound**: members who publish more/broader
show more measured "movement" (partly a sampling artifact of more windows/topics), not position
lability. **Reliability-filtered set (≥2 items in every contributing window, ≥3 windows): n=1** —
essentially no member has a reliably-sampled multi-window press trajectory.

### Consequences under the locked rules
- **N-swap (lexical→Pink): NOT justified.** Requires H2 AND H3 to PASS; both MISS. Keep the
  existing lexical-N channel unchanged. (The measurement-quality argument for Pink remains, but this
  criterion provides no predictive support for the swap.)
- **Making N MORE load-bearing: NOT supported** on this criterion. Neither N flavor shows detectable
  incremental validity for press-stance movement.
- **Do NOT drop N either.** The locked "drop N" trigger (neither H1 nor H2 clears rule 1) is met,
  but it is a candidate action for the USER only, and this criterion is explicitly
  necessary-not-sufficient + noise-attenuated + confounded — it cannot carry a drop verdict against
  a theory-grounded (Byrne) channel. N stays; its engine contribution remains **unverified**, as it
  was before.
- **Persona (PW=0.30): unchanged** (locked regardless of outcome). H4 is the largest signal
  (+0.076 primary) and right-signed in 2/3 sets but sub-threshold; nothing to act on.
- **Binding next step = avenue 4:** the confirmatory gate needs a *non-text, reliably-sampled*
  movement criterion (CU-relevant roll-call switches / cosponsorship timing). This press-movement
  screen is too noisy (n=1 survives reliability filtering) and too confounded (breadth/volume) to
  license any engine change. No engine change ships from this result.

---
## SUCCESSOR-CRITERION DESIGN (2026-07-08, ultracode workflow) — NOT YET LOCKED. Awaits user ratification.
Two independent findings reframe the confirmatory path:
1. **CMC precedent (big5_methods §13) is decisive and was re-reproduced.** Pink × behavioral-
   dispositions (the one clean non-text method) same-trait diagonal mean{A,E,O} = +0.064 (< the
   +0.12 bar), MTMM fails; only A×cooperation ~+0.14 survives — and the susc `.40` slot already
   uses **behavioral** cooperation_z, so text-A there would be a downgrade. ⇒ Making the *text*
   psychology (lexical-N, Pink-N, persona) more load-bearing is **affirmatively unsupported**, not
   merely undemonstrated. Recommendation to the user: extend the §13 ruling to explicitly cover the
   N-swap, edge_mult, and seed_prob routes (forecloses re-exploration).
2. **A materially better MOVEMENT criterion exists in-repo, text-uncontaminated.** `votes/HS117|118|
   119_members.csv` carry per-congress **Nokken-Poole** ideal points. DW-NOMINATE dim1 is frozen
   (common space, |Δ|=0 for all 391 three-window members) but Nokken-Poole dim1/dim2 are
   re-estimated per congress and drift (|Δdim1| median 0.065, p90 0.175; dim2 more). Because drift
   derives from **roll-call votes** and the trait candidates derive from **text**, they are
   generatively independent — the contamination + coverage/volume confound that sank the press
   screen is absent.

### TIER-1 gate (Nokken-Poole ideological-drift) — DESIGN, ready to lock on ratification
- **Criterion Y** = Euclidean per-member drift of Nokken-Poole (dim1,dim2) across 117→119 (or
  adjacent-pair for 2-window members). **Analyzable n = 418** (≥2 windows ∩ dispositions ∩ both N),
  **99% nonzero** (no reliability collapse). MDE r = 0.121 (n=418) / 0.134 (n=345 at ≥3 windows);
  permutation floor 95th ≈ 0.098 — **inside** the Funder-Ozer elite band (|r|~.10–.25), where the
  press screen's 0.155 floor sat at its ceiling. ⇒ 2.6× the press-screen power, clean source.
- **Predictors/controls/statistic/discipline**: identical to the press gate above (candidates
  lexical-N, Pink-N, persona; controls coop/dil/dom; semipartial; one-tailed positive [more
  susceptible ⇒ more drift]; permutation null 3000 shuffles; one look; bars locked pre-look).
- **Join**: use `bioguide_id` (already in the CSVs) → engine panel, lifting the join from 354
  (name+initial) to the full ~418.
- **RATIFICATION REQUIRED before this is locked/run** (user's domain):
  (a) Is **general ideological drift an acceptable proxy** for CU-lobbying susceptibility? Tier-1 is
      honestly CU-*agnostic*. If not, hold for Tier-2.
  (b) Confirm the control set (coop/dil/dom) and whether `nominate_extremity` enters as a covariate
      (note: diligence_z = roll-call participation shares a source with the Nokken outcome — this is
      fine for a *control* absorbing variance; the *candidates* stay text-independent, which is the
      load-bearing property).
  (c) Lock the effect bands (e.g. semipartial ≥ +0.15 PASS / +0.10 directional / |·|<0.10 null).
- **Expectation (honest)**: given the CMC refutation, a MISS is the likely outcome even here; the
  value of running it is a *powered, clean* verdict rather than a noise-limited one.

### TIER-2 gate (CU-specific vote-SWITCH) — the ideal, needs acquisition
Position change (pro→anti / anti→pro) on the **63 CU bills** in `cu_bill_directions.json`, using the
user's pre-set directions. Requires acquiring the member×roll-call matrix + roll-call dates
(Voteview HSall_votes / Congress API) keyed by icpsr/bioguide — **not in-repo**. Likely smaller n
than Tier-1 but each observation is a hard CU-relevant binary; run as a confirmatory refinement, do
not gate the unblock on it.

### AVENUE 3 (persona-approach → conversion multiplier) — DESIGN-ONLY, NO-BUILD
`optimize.py`'s only lever is dollars/member (`cu[m]`, `INC`, `PMAX`) → `pflip(...,pressure_mult)`;
there is **no approach/framing decision variable**, and persona is already inside `pressure_mult`
via susc (PW=0.30) as a *susceptibility* dial. A match→conversion coefficient β cannot be calibrated
(no legislator matched-vs-unmatched outcome exists; the r~.17 evidence is voters/consumers seeing
ads — double transfer risk: population + channel). Minimal viable form if ever pursued:
`conv_mult(m,approach)=1+β·match(m,approach)`, β pre-registered small + transfer-discounted, env
kill-switch default OFF, and a **hard gate: ships only after a legislator-level matched/unmatched
criterion exists and passes a pre-registered validation.** Absent that criterion, design-only.
