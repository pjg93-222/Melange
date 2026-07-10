# AUDIT FINDINGS — 2026-07-10 (extensive audit + true run-through)

Auditor: Fable (session beautiful-hermann continuation). Tree: LIVE checkout, branch main
@aae62c9 ("Merge branch 'claude/beautiful-hermann-20a94c'" + 5a7bd29 N-gate sprint + 5d8db47
weekly-refresh accrual steps). Context this audit must carry: coop_v2 ENGINE PROMOTION shipped
@94f09cf earlier today (RECEPT_COOP=v2 default; receptivity/bundle/dashboards regenerated;
lt_priming/frontier deliberately deferred to "next chain run" = THIS run-through), and another
session backfilled +5,235 interview turns (5a7bd29) — so EXPLAINED engine-artifact deltas are
expected at Phase 2; ranks_python.json must still be ZERO-delta.

## Baselines (Phase 1) — ALL GREEN
- kernel tests: **37 passed, 0 FAILED**
- py_compile sweep: **141 files, 0 FAILED** (fec/*.py, attic skipped)
- audit_full: **69 passed, 0 FAILED — ALL MODULES CLEAN**
- Environment at audit: TWO live collectors running (fetch_interviews pbs 2015-2019, npr
  2019-2023 — the 5a7bd29 sprint continuing); chain is collector-safe by design (run-4 doctrine:
  chain reads no social_media.db). Corpus counts WILL drift during the audit — expected.

## Phase 2 pre-state (md5)
ranks cce0c5a6 | budget_frontier f4249e2e | frontier_electoral b5a00007 | optimize df285886 |
per_topic_alloc 1a3812bf / bridge 9f06802c / coalition 0d030391 | salience 304e121b |
dashboard_data 5d82c71b | member_receptivity 8b82f9f0 (promoted v2) | lt_priming 9321adcb
(pre-promotion — expected to move THIS run per @94f09cf's deferral note).
EXPECTED-DELTA SET for gates c/d: receptivity-downstream engine artifacts (lt_priming, frontier,
optimize, per_topic, dashboard_data) — explained by (i) coop_v2 promotion @94f09cf reaching
lt_priming/frontier for the first time, (ii) +5,235 interview turns / MEM 456->457 (5a7bd29).
ranks_python.json must be ZERO-delta regardless.

## Phase 2 — TRUE RUN-THROUGH: ALL GATES PASS
- (a) every chain step OK, exit 0: **17/17 steps, 7.8 min**
- (b) audit tail: **ALL MODULES CLEAN** (69/69, 214.6s)
- (c) rank delta: **ZERO** — ranks_python.json byte-identical (md5 cce0c5a6 preserved; absent
  from the hash diff entirely)
- (d) artifact hashes: deltas EXACTLY the expected-explained set (frontier ×2, optimize,
  per_topic alloc/coalition, salience, dashboard_data, member_receptivity — receptivity-
  downstream, explained by the @94f09cf promotion reaching the engines + the 5a7bd29
  dispositions rebuild). Consistency proof: the two receptivity-INDEPENDENT artifacts
  (lt_priming, per_topic_alloc_bridge) are byte-identical.
- Determinism: budget_frontier double-run (TOPIC=Interchange, scratchpad outputs) —
  **md5 IDENTICAL** (f60c4a55).

## Phase 3 P5 — UI smoke: PASS
Desk (via preview server :8803): 533 members render, profile opens (Crapo #1 Ally, face-valid
top-10), staff cards + star/notes controls present (18 cards / 13 stars / 15 note fields),
In-contact panel renders, behavioral radar shows the PROMOTED Cooperation axis (v2; Crapo
covered, Reactivity shows the n/a-neutral note convention), N-slot source line present, ES
caveats present (both "gender-confounded" AND "externally uncorroborated" — see S2-01 REVISED),
ZERO console errors. Dashboard: renders, DATA present, full feature set live (Cascade + Who
joins/Max route/Flip route, Receptivity color mode, layer toggles, Path Best/Multi/Budget,
Coalition build), ZERO console errors.

## Findings

[S2-01 — REVISED: transient incident, SELF-HEALED; lesson stands] cu-member-desk.html — the
Vote Smart ES caveat ("externally uncorroborated (PCT-respond null, 2026-07-09, n=517)", a
LOCKED-LOOK pre-declared consequence, tpl:623) was ABSENT from the live desk at audit start. Evidence: grep 'externally
uncorroborated|PCT-respond' over cu-member-desk.html = 0 matches (2026-07-10). Cause: the
coop_v2-promotion regen (@94f09cf session) ran make_member_desk from a worktree branch that
predates the Vote Smart template edit. REVISION on evidence: both session branches are FULLY
MERGED into main (git log main..branch = empty for clever-elbakyan AND beautiful-hermann — the
skills-library memory's "2-branch merge debt" is STALE), and this audit's Phase-2 chain run from
post-merge main REGENERATED the desk with the caveat RESTORED (verified in-browser: "externally
uncorroborated" + "gender-confounded" both present). Net: a same-day drop window of a few hours,
self-healed. Impact: desk overstates ES
credibility (honesty regression on a display caveat mandated by a locked prereg). Remedy: merge
claude/clever-elbakyan-15fa11 into main (also carries methods §22 + votesmart artifact pinning),
regenerate desk artifacts, verify caveat present; then the general lesson — a regen is only safe
from a tree that is a SUPERSET of every merged-and-look-consequence-bearing branch (second
occurrence of this failure mode; first was the 07-09 dashboard-UI drop).

[S2-02] fec/run_pipeline.py:19 — coop_v2_candidate.json became an EVERY-RUN ENGINE INPUT at the
@94f09cf promotion (receptivity_layer step 1 reads it) but has NO chain producer: its values
freeze at the 2026-07-09 cosponsorship snapshot while bipartisan/cosponsor inputs refresh weekly,
and coverage (315/533, the >=10-known-party-cosponsorship floor) can never grow — new/uncovered
members stay neutral forever. Evidence: CHAIN list lines 19-35 contains no coop_v2_candidate.py;
receptivity_layer.py loads B+'\coop_v2_candidate.json'. This is the exact failure class the
chain's own line-25 comment records for lt_priming ("the artifact fossilized"). Impact:
susceptibility/seed_prob/priming/frontier slowly diverge from live cosponsorship reality; the
promotion's coverage-growth story silently never happens. Remedy: insert
('coop_v2_candidate.py',[]) into CHAIN immediately BEFORE receptivity_layer.py — the generator is
deterministic and composition-frozen (@28914b3 doctrine: composition frozen ≠ values frozen), so
this is a values-refresh only. Note: no active look pins the artifact SHA (round-6 is TAKEN and
its gate refuses re-runs), so in-chaining is look-safe.

[S3-03] fec/receptivity_sensitivity.py:38 — the sensitivity harness's seed_prob variants
recompute from d.get('cooperation_z') (v1) while the shipped engine sources the slot from
cooperation_v2 (RECEPT_COOP=v2). The susc side is unaffected (reads susc_trait_z, which already
embeds the promoted slot). Impact: diagnostic-only (not in chain), but its seed_prob robustness
claims are now computed on the retired basis. Remedy: key the read off the artifact's coop_slot
(cooperation_v2_z if v2, else cooperation_z, missing -> 0).

[S3-04] fec/b5_narratives.py:42 — narratives verbalize Cooperation from cooperation_z (v1)
("reaches across the aisle"), so a volume-inflated member (the Emmer class) can carry a brief
asserting cooperativeness his own desk radar (now v2 percentile) contradicts. Display-only;
narratives are frozen and refresh incrementally (NARR_MAX cap) — do NOT mass-regenerate (Fable
cost rule). Remedy: switch the BEH source tuple to the coop-slot logic so future incremental
refreshes verbalize v2; stale texts age out via weekly refresh.

[S3-05] naming collision "round 6": big5_methods.md §23 = the A-route round 6 (locked, look
TAKEN, MISS, 2026-07-10) while commit 5a7bd29's subject calls the N-route successor sprint
"round-6 prereg staged" (files are big5_n2_prereg.md / b5_n2_matrix.py, DRAFT, gate not met).
Two different "round 6"s now exist in the record. Impact: future-session recall risk (the
program's known mis-recall failure mode). Remedy: report-only — big5_n2_prereg.md should
self-describe as the N-route successor (round 4's data-gated heir), not "round 6"; memory files
updated this session to disambiguate.

## Sweep results (Phase 3, clean categories)
- P3 kernel drift: CLEAN — cpf_diffusion/cpf_pressure (two named physics, intentionally
  distinct), PERS, SGATE exist only in fec/moneyball_core.py (attic copies are attic; the
  hard-guarded sync_stance_clean exception did not surface as a bare re-implementation).
- P2 silent-failure surfaces: CLEAN for the chain — `except Exception: pass` population is
  confined to collectors/LLM pilots (soft-fail is the 5d8db47 doctrine); the historical chain
  case (bundle advisory read) already carries its named fix (build_dashboard_bundle.py:273).
- P1 contracts around the promotion: engine consumers of member_receptivity read only the
  unchanged multiplier keys (susc/edge/incent/pt/pressure/seed, LOSSFRAME); the two off-basis
  readers found are S3-03 (sensitivity harness) and S3-04 (narratives); the missing chain
  producer is S2-02.

## Fix lane — branch audit/fixes-2026-07-10 (from main), four commits, verification run pending
- c5fe574 [S2-02] coop_v2_candidate.py in-chained before receptivity_layer (values/coverage
  refresh only, composition frozen @28914b3; inherits col-G-class two-run convergence via the
  previous run's bipartisan.json — documented in the CHAIN comment).
- 37415fb [guard] audit gains the A-slot coop_v2 guard (mirrors the N-slot guard): coop_slot==v2,
  coverage>=250, |z|<=5 — 69 -> 70 checks.
- be5a1cd [S3-03] sensitivity harness seed() is coop_slot-aware (its stage-1 replication gate
  would otherwise FAIL against the promoted artifact — live breakage, not just drift).
- ffd802b [S3-04] narratives Cooperation descriptor overlays cooperation_v2 (omit-if-uncovered,
  never a v1 fallback); future incremental refreshes only, no mass regen (Fable cost rule).
- c80e1d3 [S3-06] coop_v2_candidate stale "consumed by nothing" provenance/print updated
  (string-only, values-inert; next chain run re-hashes the artifact once — benign, documented).

### Fix-lane VERIFICATION RUN — ALL GATES GREEN
- kernel tests (fix branch): **37/37**
- chain: **18/18 steps OK, 7.9 min** — coop_v2_candidate now step 1 (1.5s), receptivity reads
  the fresh artifact, full chain downstream
- ranks_python.json: **md5 IDENTICAL pre/post (cce0c5a6…) — zero-delta**
- audit (fix branch, standalone re-run to pin the count): **70 passed, 0 FAILED**, with the new
  guard explicitly OK ("receptivity A-slot = cooperation_v2 … no silent v1 revert"). Main
  reports 69 until the branch merges.
- ES caveat persistence: "externally uncorroborated" present in the regenerated desk (grep = 1)
- coop_v2_candidate refresh: coverage 315/533 (unchanged — the c2 floor admits new members only
  as the bills archive accrues, which is the point of in-chaining), values re-derived from
  current bipartisan/dispositions under the frozen composition (sha 3110638e…).
- MERGE STATUS: branch audit/fixes-2026-07-10 (5 commits) awaits merge to main.
Additional S2-02 note: coop_v2_candidate.py also reads behavioral_dispositions.json — which is
NOT chain-produced either (weekly_refresh territory); acceptable (same freshness class as its
other inputs), noted for completeness.
