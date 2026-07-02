# MATHEMATICAL SPECIFICATION — Moneyball / Melange Systems
*Rewritten 2026-07-02 (architecture review). The previous long-form spec drifted behind the code
repeatedly and was retired (recoverable via git history: commit 62a209e). This version states the
LAW OF THE SYSTEM: where each piece of math lives, what its invariants are, and the conventions that
span modules. **The code is authoritative; this document tells you where to look and what must
always hold.***

## Authoritative sources by subsystem

| Subsystem | Authoritative code | Verified by |
|---|---|---|
| Rank (Blended Model) | Workbook: Score = 0.25·Leg% + 0.30·Press% + 0.40·Infl% + 0.05·Demo%; Press% = pillar/max; pillar = SUMPRODUCT(normalized press × row-535 tiered weights per 'Topic Weights' sheet) | audit_full W1 guard; audit-II exact recompute |
| Media blend (press+social) | `fec/build_media_blend.py` — raw cell = (1−0.5f)·press/p80 + 0.5f·social/p80; f = min(1, nz/15) (SHRINK); RT intensity ×0.5; decay 0.5^(age/HL), HL press 2.0y / social 0.5y; press ALWAYS from press_raw_original.json cache | deep_audit_A exact recompute |
| Per-category stance tiers | `fec/per_category_stance.py` — self-calibrating median+k·IQR cuts, rate-clamped; DEFENSIVE={Interchange, Credit Card Mandates} weights (0.55,0.70,0.20) vs offensive (0.55,0.35,0.10)/Σ; 18 categories incl. CU Tax Status | audit_full stance sanity + ≥18 guard |
| Overall tier (col G) | `fec/sync_stance_g.py` — IMP-weighted mean of TORD tier scores → 10-rung ladder | audit_full |
| Money response | `fec/money_response.py` — Δlean = MAXSHIFT·(r/(r+HALF))·pressure_mult (·LOSSFRAME if threat); defection ≥ DTHRESH walks ONE rung; Champion/Opponent immune | kernel tests; audit_full [2] |
| Flip/winnability | `fec/flip_model.py` — pflip = a/(a+b); Michaelis-Menten money terms ×pressure_mult + peer proximity ×cpf_pressure; tgt = engagement·PERS·(1+0.3·bpf) | kernel tests; audit_full [8] G-K bound |
| Cascades (frontier/coalition/salience) | kernel p = w·cpf_diffusion·edge_mult(receiver)/(…+6); CRN splitmix64 keyed (iteration, edge); contingent seeds gate = seed_prob·SGATE(stance), floor 0.15 | audit_full determinism; frontier sub-audit (12) |
| Salience shock (Noble-Turner) | `fec/salience_shock.py` — p=(1−b)(1−zn), q=(1−b)zn, b=0.05+0.10ψ (p+q+b≡1); regime-signed party-asymmetric ladder steps ×VULN×susc_mult; defensive-appeal threshold ×(1+DELTA/2) at $250k probe | audit_full [10] |
| Receptivity layer | `fec/receptivity_layer.py` — susc = .40A+.30N−.20C−.10E (Byrne); pressure_mult = clip(susc·incent·pt, 0.50, 1.60) (F&H incentive · Linde-Vis PT domain); seed_prob = clip(.60+.10A+.06O+.04E, .30, .90) | audit_full caps; kernel tests |
| Big Five traits | `fec/big5_traits.py` — Ramey-synth closed-vocab on tweets+floor+hearings; z relative to THIS corpus; shrinkage √(tokens/1500); O flagged low-validity | party-validation printout every build |
| Network layers | `fec/build_multilayer_network.py` — cosponsor verbatim (mean-symmetrized) + press engagement w=6p/(1−p) + HCoI isolated-incident + social new-edge/reinforcement (+30% cap) | structural audit; provenance sheet |
| Pillar shadow-compute | `fec/compute_pillars.py` — Python reproduction of the ENTIRE raw→normalized→pillar→score→rank chain; Excel PERCENTRANK = truncate to 5 DECIMAL digits (empirically pinned) | audit_full parity check (533/533 exact) |
| Shared kernel | `fec/moneyball_core.py` — rosters, network loader (every member has an entry), TWO named cpf physics, sm64, PERS/IMP/BLOCKCAT/SGATE | `fec/tests/run_tests.py` (28 checks) |

## Cross-module conventions (the parts that used to drift)

**The two partisan physics (deliberate, distinct — never merge):**
- `cpf_diffusion` (cascades): cross-party ×(0.4+0.6√(bpf_a·bpf_b)) — contagion crosses the aisle
  through bridge-builders; same-party 1.0.
- `cpf_pressure` (flip model): co-partisan ×1.7, out-partisan ×0.5 — Furnas/Bakker source-alignment
  for direct persuasion.

**The '—' (no recorded position) ontology** — a blank means *unknown*; each module maps unknown to
its own neutral point, never to zero and never to enthusiasm:
- Persuadability PERS['—'] = **0.45** (Ally parity; silence never outranks a declared Ally — user-ratified).
- Contingency gate SGATE['—'] = **0.85** (an unknown is slightly harder to activate than a known Neutral).
- Overall-tier aggregation: '—' **excluded** (silence doesn't dilute earned tiers).
- Salience ψ: the '—' share **raises** issue uncertainty (Noble Prop 5 caution).

**One post's journey (the composed social formula):** a post enters the media pillar as
`sign·clip(margin,.25,1.5)·(0.5 if RT)·0.5^(age/0.5y)/n_categories`, p80-scaled, thin-category-shrunk
(nz/15), ×0.30 pillar weight × its category's tiered weight (0.30 flagships … 0.02 CDFI). The same
post's text feeds the Big Five → pressure_mult/seed_prob. A member-to-member repost additionally
becomes (or +30%-reinforces) a network edge (Fink author-volume-normalized, kernel-inverse mapped).

**Determinism contract:** every stochastic engine runs seed 7 / MC 20 with splitmix64 keyed on
(iteration, edge-or-member) — draws are evaluation-order-independent so marginals isolate true
effects. Any NEW random draw must claim a dedicated key range (seed gating uses offset 2^62).

**Workbook contract:** Python writes VALUES only (never formulas), backup-first into `backups/`,
Excel-COM recalc (zip-validated, retried once) before any data_only read. The workbook is the rank's
system of record; everything else is Python.

## Standing dials (env; defaults = the ratified state)
`PERS_NONE=0.45 · SOCIAL_SHRINK=1 · RT_W=0.5 · LOSSFRAME=1.10 · SOC_REINF=0.3 · SOC_CAP=2.0 ·
SOC_VOLFLOOR=25 · SOC_MEN_W=0.4 · BP_SRC=cosponsor (aug = unratified augmented definition) ·
RECEPT_LAYER=1 · IMPUTE_IND0=1 · SAL_PSI_DAMP=0 (off) · DTHRESH=11.25 · MAXSHIFT=18 · HALFF=0.10 ·
MC=20 · SEED=7 · MONEYBALL_ROOT / MONEYBALL_DRAFT (paths.py)`

## Regeneration & verification protocol
Data refresh: collectors (`fetch_congressional_record`, `tweet_collector`, Quorum) →
`big5_traits` → `social_interaction_layer` → `build_multilayer_network` → `build_media_blend` →
**`run_pipeline.py --recalc`** (chain incl. receptivity, stance, advisory, exports, audit).
Any code change: `fec/tests/run_tests.py` (28) → `run_pipeline.py` → **zero rank delta** vs the
last ranks_*.json baseline → `audit_full.py` all-clean.
