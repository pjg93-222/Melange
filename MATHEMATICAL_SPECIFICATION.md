# MATHEMATICAL SPECIFICATION — Moneyball / Melange Systems
*Rewritten 2026-07-02 (architecture review). The previous long-form spec drifted behind the code
repeatedly and was retired (recoverable via git history: commit 62a209e). This version states the
LAW OF THE SYSTEM: where each piece of math lives, what its invariants are, and the conventions that
span modules. **The code is authoritative; this document tells you where to look and what must
always hold.***

## Authoritative sources by subsystem

| Subsystem | Authoritative code | Verified by |
|---|---|---|
| Rank (Blended Model) | `fec/engine/compute_pillars.py --write` → `ranks_python.json`; the workbook is a view. Score = 0.25·Leg% + 0.30·Press% + 0.40·Infl% + 0.05·Demo% | audit_full authority/parity guards |
| Media blend (press+social) | `fec/stance/build_media_blend.py` — raw cell = (1−0.5f)·press/p80 + 0.5f·social/p80; f = min(1, nz/15) (SHRINK); RT intensity ×0.5; decay 0.5^(age/HL), HL press 2.0y / social 0.5y; press ALWAYS from press_raw_original.json cache | deep_audit_A exact recompute |
| Per-category stance tiers | `fec/stance/per_category_stance.py` — self-calibrating median+k·IQR cuts, rate-clamped; DEFENSIVE={Interchange, Credit Card Mandates, CU Tax Status}; 18 categories | audit_full stance sanity + ≥18 guard |
| Overall tier (col G) | `fec/moneyball_core.py` + `fec/stance/sync_stance_g.py` — IMP-weighted mean of TORD tier scores → strict fixed ladder; Tier 1 overlays Champion | kernel tests; audit_full |
| Money response | `fec/engine/money_response.py` — Δlean = MAXSHIFT·(r/(r+HALF))·pressure_mult (·LOSSFRAME if threat); defection ≥ DTHRESH walks ONE rung; Champion/Opponent immune | kernel tests; audit_full [2] |
| Flip/winnability | `fec/engine/flip_model.py` — pflip = a/(a+b); Michaelis-Menten money terms ×pressure_mult + peer proximity ×cpf_pressure; tgt = engagement·PERS·(1+0.3·bpf) | kernel tests; audit_full [8] G-K bound |
| Cascades (frontier/coalition/salience) | kernel p = w·cpf_diffusion·edge_mult(receiver)/(…+6); CRN splitmix64 keyed (iteration, edge); contingent seeds gate = seed_prob·SGATE(stance), floor 0.15 | audit_full determinism; frontier sub-audit (12) |
| Salience shock (Noble-Turner) | `fec/engine/salience_shock.py` — p=(1−b)(1−zn), q=(1−b)zn, b=min(0.35, 0.05+0.10ψ) (p+q+b≡1); regime-signed party-asymmetric ladder steps ×VULN×susc_mult; defensive-appeal threshold ×(1+DELTA/2) at $250k probe | audit_full [10] |
| Receptivity layer | `fec/members/receptivity_layer.py` — susc = .40A+.30N−.20C−.10E (Byrne); pressure_mult = clip(susc·incent·pt, 0.50, 1.60) (F&H incentive · Linde-Vis PT domain); seed_prob = clip(.60+.10A+.06O+.04E, .30, .90) | audit_full caps; kernel tests |
| Big Five traits | `fec/members/big5_traits.py` — Ramey-synth closed-vocab on tweets+floor+hearings; z relative to THIS corpus; shrinkage √(tokens/1500); O flagged low-validity | party-validation printout every build |
| Network layers | `fec/network/build_multilayer_network.py` — cosponsor verbatim (mean-symmetrized) + press engagement w=6p/(1−p) + HCoI isolated-incident + social new-edge/reinforcement (+30% cap) | structural audit; provenance sheet |
| Pillar shadow-compute | `fec/engine/compute_pillars.py` — Python reproduction of the ENTIRE raw→normalized→pillar→score→rank chain; Excel PERCENTRANK = truncate to 5 DECIMAL digits (empirically pinned) | audit_full parity check (533/533 exact) |
| Shared kernel | `fec/moneyball_core.py` — rosters, network loader (every member has an entry), TWO named cpf physics, sm64, PERS/IMP/BLOCKCAT/SGATE | `fec/tests/run_tests.py` (30 checks) |

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

**Workbook contract (PHASE 2, 2026-07-02 — system of record INVERTED):** Python owns ALL derived
math; **ranks_python.json is the rank authority** (`compute_pillars --write`, engines read it via
`moneyball_core.scores()/ranks()`). The workbook is a self-refreshing **VIEW**: every Python writer
sets `fullCalcOnLoad`, so Excel recalculates the formulas whenever the user opens it. There is NO
COM anywhere IN THE PIPELINE (the manual `apply_*` / `write_im_sheet` / `sync_stance_clean` tools
still drive Excel COM — run those with the workbook closed). Physics of the file: **openpyxl saves strip cached formula values** — after a
sync/blend save, `data_only` reads of FORMULA cells return None until the next user Excel open;
TYPED cells always survive (R&A names + col G, AB2:AB5 dials, Press Raw, row-535 weights). Pillar
inputs O/E/F are formula-backed → `pillar_inputs_snapshot.json` (auto-refreshed while the view
cache is alive, auto-bootstrapped from the newest cache-alive backup; correct because O/E/F change
only through user Excel edits, which revive the cache). Python still writes VALUES only,
backup-first into `backups/`. Chain order: authority is computed BEFORE the cache-killing sync.
User dial edits (Topic Weights, Category Stance, AB weights) happen in Excel as always — an Excel
save restores every cache. Full-pipeline runtime on a cache-dead workbook is ~19 min (slower
openpyxl parses; optimization candidate: cache the frozen Legislative-Normalized sheet).

## Standing dials (env; defaults = the ratified state)
`PRIMACY_METHOD=diagnostic_v1` (user-ratified 2026-09-20: the
`CLASS_DOCK_PRESS_GRADE_ALL` diagnostic, retaining within-chamber seating.
Removes the extra uncertainty dock, applies beneficiary magnitudes to legislative
grade contributions, and uses the adopted classified media intensity share in
the existing 20% press lane. Ordinary shrinkage, votes, tensor, floors and conduct
remain. `legacy` plus full regeneration restores the previous factor and grade
byte-for-byte on the same inputs. `PRIMACY_UNCERT_K` remains an explicit override;
its default is 0 under the diagnostic and .25 under legacy. Corpus provenance,
limitations and verification: [adoption record](fec/docs/primacy_diagnostic_20260920.md).)

`PERS_NONE=0.45 · OVERALL_OPPONENT_CUTOFF=-1.50 (user-ratified 2026-07-18; fixed bands: 3.0/2.0/1.0/0.4/0.0/-0.3/-0.75/-1.5) ·
SOCIAL_SHRINK=1 · RT_W=0.5 · LOSSFRAME=1.10 · SOC_REINF=0.3 · SOC_CAP=2.0 ·
SOC_VOLFLOOR=25 · SOC_MEN_W=0.4 · BP_SRC=cosponsor (user-ratified 2026-07-03: bipartisanship stays a COSPONSORSHIP concept; aug = available but unratified) ·
RECEPT_LAYER=1 · IMPUTE_IND0=1 · SAL_PSI_DAMP=0 (off) · DTHRESH=11.25 · MAXSHIFT=18 ·
HALF=0.10 (money_response receipts-fraction) · HALFF=0.10 (flip-family capacity — DISTINCT dial, same default) ·
MC=20 · SEED=7 · LEGSTANCE_ORIGCO=1 (2026-07-17: Original-Co-Sponsor counts included in the leg agenda; 0 reverts to sponsor+plain-cosponsor) ·
IV_TURN_TAGS=2 (2026-09-19, packet audits/laundry_list_closeout_20260918 R1 d / N12: the interview collector's turn-boundary grammar. The legacy ALL-CAPS label classes (`fetch_interviews.py` LABEL, INLINE_LABEL, MIXED_LABEL) could not see a backtick (`O`DONNELL:`), a lower-case parenthetical (`WALLACE (voice-over):`), a bracketed timestamp, or PBS's `", U.S. <Title>:"` tail, so those speakers' words stayed inside the PREVIOUS member's row — 5,835 of 153,576 stored INTERVIEW rows measured, MS NOW 8.7% / CNN 4.5% / PBS-NPR-C-SPAN 0%. The rules now live in the pure `fec/members/turn_tags.py`, which the collector and the one-off history repair (`fec/members/migrate_interview_turn_bleed.py`) share. `2` = repaired, and applies to NEW rows only; `1` restores all three legacy patterns byte for byte. The stored corpus is a SEPARATE, owner-gated migration, not a dial) ·
LEG_SPONSOR_FROM_COLUMN=1 (2026-09-19: the bill archive's bill-level `Sponsor` column mints the missing sponsor-role rows, which then pass every unchanged gate; 0 reverts to ignoring the column) ·
PRESS_URL_CANON=2 (2026-09-19, packet audits/laundry_list_closeout_20260918 A5: one press release ingested under two aliased URL forms counts ONCE — 11 pairs, all path aliases, merged only when the date and title agree too (a 12th candidate, Vargas 2022-09-30 vs 2023-01-30, reuses one headline for a different release and is KEPT, counted in release_key_conflict_kept); the extra rules sit in `release_url_key`, reached only by `tone_turn_key`, never by `canonical_url`, whose every other join is unchanged. Merged rows stay named in `press_component_meta.json.tone_ingest_dedup`. `1` restores the legacy key byte for byte) ·
CROSSPOST_KEY_CHARS=0 (2026-09-19, packet audits/laundry_list_closeout_20260918 A3: the cross-post duplicate key is the WHOLE normalised statement, not its first 120 characters — 445 of 1,434 groups were false prefix collisions. `normalized_text` keeps the 120-char truncation because it is the tweet_stance_final JOIN key. `120` restores the legacy duplicate key byte for byte; it changes no score at CROSSPOST_DEDUP=0) ·
DESK_PRESS_SOURCE=engine (2026-09-19, packet audits/laundry_list_closeout_20260918 A1: the member desk reads the same press stream as the ranking engine — the union of workbook sheet `Press Release Articles` and `fec/press_stream.py`'s two tone files. No chain script writes that sheet (external R pipeline), so the desk showed a frozen corpus: 291 engine rows had no sheet row, 221 of them scoring. Measured effect: 288 rows added across 146 members, 0 removed, 0 existing rows changed. The SHEET wins the overlap because on the 2,376 shared keys the CSV disagrees on date (2,138), score_graded (1,207), stance_src (493) and the displayed stance label (57) — press classification is the owner's domain. DISPLAY ONLY: no engine input, rank input or stance label moves. `sheet` restores the workbook-only path byte for byte) ·
REF_PRESS_OWN_DOMAIN=1 · REF_ROSTER_FILTER=1 · REF_IDENTICAL_ONCE=1 (2026-09-19 member-reference admission filters, packet audits/laundry_list_closeout_20260918 B6/B4/B5: a PRESS headline counts only off the speaker's own .house.gov/.senate.gov domain; roll-call rosters and signature blocks are not references; identical windows on one edge count once in n_scored/pos/neg/neu while n_raw keeps every mention. Each 0 restores the prior behaviour exactly; census in the artifact's `admission_filters` block) ·
MONEYBALL_ROOT / MONEYBALL_DRAFT (paths.py)`

## Regeneration & verification protocol
Data refresh: collectors (`fetch_congressional_record`, `tweet_collector`, Quorum) →
`big5_traits` → `social_interaction_layer` → `build_multilayer_network` → `build_media_blend` →
**`run_pipeline.py --recalc`** (chain incl. receptivity, stance, advisory, exports, audit).
Any code change: `fec/tests/run_tests.py` (30) → `run_pipeline.py` → **zero rank delta** vs the
last ranks_*.json baseline → `audit_full.py` all-clean.
