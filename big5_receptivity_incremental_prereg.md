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
