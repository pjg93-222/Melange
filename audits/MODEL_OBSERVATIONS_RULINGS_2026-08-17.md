# RULINGS ON THE FIVE MODEL OBSERVATIONS -- 2026-08-17

Paul's directive: "Rule on the five model observations and fix the susc triple-identity."
Rulings issued under that delegation; observation (a)'s fix executed as the directive's
explicit instruction. Evidence base: audits/FORECAST_COLLINEARITY_2026-08-17.md. Every
ruling below preserves engine BEHAVIOR bit-exactly; anything rank-moving stays gated.

## (a) Susc triple-identity -- FIXED (behavior-neutral refactor, proven)

RULING: the identity (susc_z / susc_mult / edge_mult, measured rho = 1.000) is BY DESIGN --
one susceptibility construct with role-specific gains -- but the code let the two gains be
tuned apart silently. FIX APPLIED in fec/members/receptivity_layer.py: both multipliers now
derive from one SUSC_GAINS table through one _susc_gain helper, with a SINGLE-DIAL comment
naming the collinearity consequence and gating any recalibration.
PROOF: bit-exact equivalence over 212,007 grid points including clip boundaries and
extremes (== and repr equality; proof script committed beside this record). Diff certified:
the only executable-code changes are the two substituted lines plus the helper/table
definitions; float literals and operation order preserved exactly, so regenerated artifacts
are byte-identical by construction.
MERGE-GATE CHECKLIST (live tree, before this branch merges): regenerate
member_receptivity.json and byte-match against pre-merge (input-purity recipe); kernel
suite green; ranks_python.json byte-identical; JS mirror untouched (no constant changed).

## (b) Security double-entry inside pressure_mult -- KEPT AS DESIGNED, documented

RULING: incent_mult (Fouirnaies-Hall electoral incentive) and pt_mult (Linde-Vis prospect
domain) are two theoretically distinct mechanisms that legitimately share the security
input; the resulting security-squared component in pressure_mult (measured rho = -0.671) is
a modeling consequence, not an accident. KEPT; a SHARED-INPUT comment now sits at the
computation site. Any reweighting is a rank-moving recalibration requiring the full
verification protocol.

## (c) bpf + coop_v2 double-count -- RECORDED, no change

RULING: empirically one construct entering tgt x pressure_mult through two doors
(rho = +0.888, party-robust), but both entries are separately ratified machinery (the
(1+0.3*bpf) factor and the round-6 coop_v2 promotion). De-duplication would move ranks and
re-litigate ratified pieces -- NOT done. A DOUBLE-COUNT comment now marks the susc
composition site; the collinearity audit's control (treat {bpf, coop_v2, seed_prob} as one
cluster in any regression) is the operative mitigation.

## (d) pflip pm-cancellation -- SPECIFICATION DOCUMENTED

RULING: the cancellation (pressure_mult multiplies both money terms of the Bradley-Terry
ratio; zero first-order level effect) is correct engine design -- pm reweights channels.
The flip_model docstring now states it explicitly so no future analysis treats pm as an
additive predictor. Code unchanged.

## (e) Docstring-vs-physics divergence -- STALE PROSE CORRECTED, code is authority

RULING: flip_model's pflip deliberately uses party-only cpf_pressure while cascades use
bridge-amplified cpf_diffusion -- that is the load-bearing two-physics design, and the
docstring/comments claiming "bridge-amplified proximity" and "sqrt returns" in pflip were
stale prose describing the wrong physics and a retired functional form. CORRECTED in
fec/engine/flip_model.py (docstring now states the actual saturating form and the physics
split) and fec/engine/per_topic_flip.py (both stale comments). Code untouched -- verified
by diff certification.

## Standing consequence

The five rulings change ZERO behavior. The rank-moving candidates opened by the audit --
gain recalibration (a), reweighting (b), de-duplication (c) -- remain closed until Paul
opens any of them individually with the full 2026-08-12 verification protocol (baseline
hashes, adversarial draft review, revert-dial byte-proof, mover enumeration).
