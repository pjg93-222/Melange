---
name: moneyball-diagnostics-and-tooling
description: Loads when a model needs to run and interpret the Moneyball system's SHIPPED harnesses and helper scripts — fec/tests/run_tests.py (kernel tests), fec/audit/audit_full.py (full-body audit), reading "N passed, M FAILED" tails, deciding whether an audit FAIL / SKIP / stale artifact is real, the zero-rank-delta gate, MC=20 sufficiency, bounding untested constants, stance-vs-gold scoring, the Katz-Bonacich benchmark, antagonist-coalition detection, the prospective-outcome harness, mtime freshness checks, and three shipped read-only helpers (rank_delta.py, artifact_freshness.py, env_dials.py). Does NOT cover building a NEW proof from first principles — power studies, plant batteries, the input-purity byte-match recipe (moneyball-proof-and-analysis-toolkit) — nor day-to-day chain operation (moneyball-run-and-operate), evidence standards or adding checks (moneyball-validation-and-qa), prereg/look discipline (moneyball-research-methodology), or live-failure triage (moneyball-debugging-playbook).
---

# Moneyball diagnostics and tooling

This skill is the measurement manual for the Moneyball system — a calibrated Python pipeline that ranks 533 members of Congress and simulates influence campaigns, with Excel as a display view. The project's core discipline is "never eyeball what you can measure": every claim of "nothing changed", "this constant is safe", or "the model is well-calibrated" has a specific tool that produces a number. This file documents the two pass/fail harnesses, the standing diagnostic fleet with interpretation guides, the byte-match method for proving a change is behavior-neutral, mtime-based freshness checking, and three helper scripts shipped in this skill's `scripts/` directory. Every command below was verified against the repo on 2026-07-09.

## When NOT to use this skill

- **Running the pipeline/collectors/dashboards, ports, what lands where** → `moneyball-run-and-operate`
- **What counts as evidence, acceptance thresholds, adding a test or audit check** → `moneyball-validation-and-qa`
- **First-principles analysis recipes (power study, split-half reliability, permutation gate, CRN proof)** → `moneyball-proof-and-analysis-toolkit`
- **Prereg/look/battery discipline for research ideas** → `moneyball-research-methodology`
- **A live failure you need to triage right now** → `moneyball-debugging-playbook`
- **The full env-dial catalog with meanings** → `moneyball-config-and-flags` (this skill ships only the live-scan drift detector)

## Quick reference

Run data-dependent tools from the live tree, or invoke the absolute live-tree script paths shown below — `fec/paths.py:7-8` defaults ROOT to the parent of the imported paths.py, so a script run from a git worktree targets that worktree's EMPTY data plane unless `MONEYBALL_ROOT` redirects it. Reads there die on missing inputs and writes land as throwaway worktree artifacts; if `MONEYBALL_ROOT` points at live, writes DO hit live. Quote every path (they contain spaces). (Corrected 2026-07-19; the previous version asserted the opposite. Verified against `fec/paths.py:7-8`.)

| Tool | Command | Proves / measures | Safe to run? |
|---|---|---|---|
| Kernel tests | `python "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\fec\tests\run_tests.py"` | math-kernel invariants (count grows — trust the run's own tail) | YES (reads live data; atomic-write checks use and clean OS-temp files) |
| Full-body audit | `python "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\fec\audit\audit_full.py"` | whole-system checks (count grows — trust the run's own tail) | YES-ish (~2.5 min; leaves 2 `_audit_tmp_*.json` in `data\system\audit_scratch\`; audit mode does not advance `pillar_inputs_snapshot.json`, `compute_pillars.py:64-69`) |
| Integrity sub-audit | `python "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\fec\audit\legacy_workbook_audit.py"` | 22 workbook+artifact checks | YES (read-only) |
| Frontier sub-audit | `python "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\fec\audit\audit_frontier.py"` | 11–12 frontier-artifact checks | YES (read-only) |
| Rank parity | `python "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\fec\engine\compute_pillars.py"` | `ranks_python.json` matches a fresh recompute (`PARITY: CLEAN`) | YES (audit mode; may refresh snapshot; exit 1 on drift) |
| Stance accuracy | `python "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\fec\stance\stance_eval.py" [pred_column]` | macro-F1 of any prediction column vs adjudicated gold | YES (read-only) |
| MC sufficiency | `python "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\fec\engine\mc_stability_check.py"` | MC=20+CRN frontier not overfit to draws | YES (creates+deletes `_mcstab_*.json` at live root; ~4 frontier subprocesses) |
| Constant bounds | `python "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\fec\members\receptivity_sensitivity.py"` | which untested constants could change decisions | YES (read-only; restores kernel cache) |
| KB benchmark | `python "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\fec\engine\kb_benchmark.py"` | allocation vs network-centrality equilibrium | writes `kb_benchmark.json` (diagnostic; chain does not consume) |
| Coalition detect | `python "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\fec\network\signed_coalitions.py"` | antagonist splinter on signed mention graph | writes `signed_coalitions.json` (diagnostic; chain does not consume) |
| Outcome harness | `python "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\fec\engine\outcome_snapshot.py" --freeze` / `--score <snap>` | out-of-sample validation of receptivity magnitudes | `--freeze` writes one dated snapshot; `--score` read-only |
| Method diagnostics | `cd "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\fec"; python engine/method_audit.py` | M1–M4 calibration prose (no pass/fail) | YES but **cwd must be the live fec/** (opens `itpas2.txt` relative) |
| Rank diff | `python "$SKILL\scripts\rank_delta.py" "<before>" "<after>"` | zero-rank-delta gate | YES (stdlib, read-only) |
| Freshness | `python "$SKILL\scripts\artifact_freshness.py" "C:\Users\pgoff\OneDrive\Desktop\Melange Systems"` | derived artifacts vs input mtimes | YES (stdlib, read-only) |
| Dial scan | `python "$SKILL\scripts\env_dials.py" "<root-containing-fec>"` | every env dial + whether set now | YES (stdlib, regex-only, read-only) |

(`$SKILL` = this skill's own directory, `...\.claude\skills\moneyball-diagnostics-and-tooling`, wherever the repo checkout lives.)

**Before running anything that spawns engine subprocesses** (audit_full, mc_stability_check): check for Paul's live jobs first — `Get-Process python -ErrorAction SilentlyContinue` and look for fresh artifact mtimes in the live root. Never run baselines concurrently with his work (session-ratified, 2026-07). And never run with calibration env dials set (SEED/MC/MAXSHIFT/DTHRESH/PERS_NONE/...) — defaults ARE the ratified state (`.claude/commands/fable-audit.md:16-19`); verify a clean shell with `scripts/env_dials.py` (recursive over `fec/` since 2026-09-30, so it now sees these dials; see section 5).

---

## 1. The two harnesses

### 1a. Kernel tests — `fec/tests/run_tests.py`

**What it protects.** The shared math layer every engine imports: `fec/moneyball_core.py` (the "kernel"), `fec/engine/money_response.py`, `fec/engine/flip_model.py`. These hold the calibrated constants and physics that, if silently changed, would move all 533 ranks with no error message. Zero test framework — plain `ok(name, cond, detail)` calls that tally pass/fail (`run_tests.py:11-14`).

Long-standing core check groups (newer routing, identity, attribution, and registered module suites follow in `fec/tests/run_tests.py`):

| Group | Checks | What breaks if it fails |
|---|---|---|
| CRN kernel (19-22) | 4 | `sm64` — the deterministic hash that replaces random draws ("Common Random Numbers"; same key → same number forever). Failure = Monte Carlo results stop being reproducible. |
| Atomic write (27-32) | 2 | `dump_atomic` must never leave a corrupt/partial JSON, even on serialization failure. |
| Calibrated constants (35-38) | 4 | 18-category importance table, `PERS['—']=0.45` (user-ratified "silence = Ally parity"; N6 flag added 2026-09-30: the code has Ally = 0.40 (`fec/moneyball_core.py:430-431`), so parity does not currently hold — open ruling N6, Paul's; do not change either value in code. The check, `fec/tests/run_tests.py:54`, asserts only `PERS['—']==0.45` and `<= PERS['Highly Persuadable']`, so it stays green), CFPB block fold, stance-gate ladder monotone. These are user-ratified; a failure means someone edited a constant — that is the finding, do NOT "fix" the test. |
| Roster + network (41-47) | 5 | 533 members, symmetric co-sponsor network, no self-loops, sane weights. |
| Physics (54-57) | 3 | The TWO intentionally distinct cross-party dampening functions (`cpf_diffusion` vs `cpf_pressure` — never unify them) + cascade kernel probabilities in (0,1). |
| Receptivity gate (60-61) | 2 | Gate bounded [0.15, 0.90]; Opponent gated below Highly Persuadable. |
| money_response (69-74) | 6 | Concave (diminishing-returns) money curve, loss-frame asymmetry, defection ladder rungs valid, committed rungs immune. |
| flip_model (81-84) | 4 | Flip probability in (0,1), CU money raises it, industry money lowers it, receptivity scales it. |
| Say-do gate (95-107) | 7 | The "cap law": an uncorroborated Champion/Defender stance displays as Ally unless corroborated by Authorship (A), a recorded Vote (V), or committee Jurisdiction (J); missing evidence source fails OPEN (no caps); `delivery_mult` bounded [0.70, 1.00]. |

**How to read output.** Per-check `  OK   name` / `FAIL  name  :: detail` lines (detail prints only on failure), tail line `KERNEL TESTS — N passed, 0 FAILED` (count grows — trust the run's own tail). Exit code 1 on any failure (`run_tests.py:960-961`); `audit_full.py` also exits 1 on failure, and so does the `legacy_workbook_audit.py` sub-audit run as a script (`main()` returns `1 if F else 0` at `fec/audit/legacy_workbook_audit.py:167`; `sys.exit(main())` at `:171`), while `audit_frontier.py` has no `sys.exit` call, so a failed check there still exits 0. (Sub-audit exit codes corrected 2026-09-30; verified against those lines.)

**Expected count: none pinned — the count grows, so trust the run's own tail** (last measured value: Provenance and maintenance). The convention (`.claude/commands/fable-audit.md:35-36`): a HIGHER count than documented is fine (guards get added); any FAILED is the finding.

**Trap for test authors.** The say-do block monkey-patches kernel caches (`MC._CORR/_VOTECORR/_JURISCORR/_DELIV`) and must restore each to `None` (the lazy-loader sentinel) afterward — copy the pattern at `run_tests.py:90-108` or every later check runs against synthetic data.

### 1b. Full-body audit — `fec/audit/audit_full.py`

The last entry of the production chain (`CHAIN` in `fec/run_pipeline.py:45-292`: 80 entries; a default run executes 79 because `DESK_RESPONSIVENESS=0` drops `responsiveness_layers.py` at `:300-302`; as of 2026-09-30), so every pipeline run self-audits. Also runnable standalone.

**Module structure** (section headers printed at runtime, line refs in `fec/audit/audit_full.py`):

| Section | Lines | Checks | Type |
|---|---|---|---|
| `[1] Existing audits` | 15-18 | 2 | **Aggregation floors**: runs `legacy_workbook_audit.py` and `audit_frontier.py` as subprocesses, regex-parses their tails, requires 0 FAILED **and** passed-count ≥22 / ≥11. The count floor exists so a silently-skipped check FAILS here instead of vanishing (S3-03, commit c90a530). |
| `[2] Money-response` | 19-37 | 6 | Module correctness (concavity, capacity, loss-frame, defection ladder). Tests the RUNG, not a named member (members legitimately move tiers). |
| `[3] Electoral plays` | 38-44 | 3 | **Internal-consistency ONLY** — compares `play` against the `overall` stored inside the same artifact. A stale `electoral_plays.json` vs the live stance matrix passes silently (the failure class behind the 2026-07-09 Frank Lucas flag — resolved 2026-07-10 as mtime-only; see §4). |
| `[4] Stance matrix` | 45-50 | 3 | Gold anchors incl. hardcoded "Durbin is Interchange Opponent" + champion-rate discipline. Stance labels are Paul's domain — a failure here is a question for him, never a relabel. |
| `[5] Co-sponsor route` | 51-64 | 3 | Incl. **determinism gate** (line 64): same seed → byte-identical output. |
| `[6] LT-priming` | 65-69 | 3 | Recipe validity (sorted, gap-closing, no committed tiers). |
| `[7] Scenario` | 70-84 | 5 | End-to-end + **determinism gate** (76) + sign-sanity regressions. |
| `[8] Optimizer` | 85-115 | 7 | Runs `optimize.py`/`budget_frontier.py` with `OPT_OUT`/`FRONTIER_OUT` pointed at `data\system\audit_scratch\_audit_tmp_*.json` (an UNMEASURED directory — see DE-011) so test runs never clobber production artifacts; **determinism gates** at 94 and 115; monotone-path and imputation regressions. |
| `[NEW] Salience/press-SNA` | 117-149 | 8 | **Schema guards** (probabilities valid, communities disjoint, provenance columns present). Each skips-if-absent. |
| `[GOLD]` | 152-182 | 6 | Gold-label vocabulary, the user's 456/87/goldeval train/test firewall, no dup URLs, conflicts flagged not silently resolved, classifier smoke-predict, sqlite `integrity_check`. |
| Receptivity + workbook | 186-263 | ~10 | Coverage/caps; press weight-row W1 guard; press-component freshness + non-degeneracy (see §4); **look-consequence locks** (236-248): `basis='behavioral'`, N-slot=reactivity, reactivity_z sanity — these prevent silent reversion of decisions that pre-registered "looks" ratified (a "look" = a one-shot statistical test on held-out data whose consequences were declared in advance); roster-drift; **rank-parity gate** (261-263, requires `PARITY: CLEAN` from a `compute_pillars.py` sub-run). |
| Psych/media schema | 265-347 | ~12 | Split-leak bound (≤4 known collisions); big5/reference/co-appearance/narrative/audio schema guards; desk-display reconstruction (displayed pillars × weights must rebuild the displayed score); **look-consequence lock** at 345-347: `b5_es_voice.json` must carry the recorded look `r=+0.208` exactly (that number is the recorded history of the ES cross-modal look — when writing about ES elsewhere, it carries a mandatory gender-confounded caveat; see `moneyball-docs-and-claims`). |
| Say-do gate | 348-370 | 2 | Cap/proven/corroboration-path coherence (A/V/J; J only on gatekeep categories). |

**What ALL CLEAN looks like** (`audit_full.py:2795-2799` on main; cite corrected 2026-09-30):

```
FULL-BODY AUDIT — N passed, 0 FAILED
  ALL MODULES CLEAN.
```

On failure the tail shows a nonzero FAILED count plus `  FAILURES: [<names>]`, and the per-check line carries the detail.

**Critical trap: exit-code behavior differs by script.** `audit_full.py` exits 1 when any check fails and 0 when clean; `legacy_workbook_audit.py`, run as a script, does the same (`main()` returns `1 if F else 0` at `fec/audit/legacy_workbook_audit.py:167`; `sys.exit(main())` at `:171`); `audit_frontier.py` has no `sys.exit` call, so it exits 0 even when a check fails. The chain runner therefore registers a failed `audit_full.py` step and aborts. **Gate on the tail text `ALL MODULES CLEAN.` as belt-and-braces because older automation may assume exit 0.** (Corrected 2026-07-19; sub-audit exit codes and cites corrected 2026-09-30, verified against `fec/audit/audit_full.py:2795-2799` on main, `fec/audit/legacy_workbook_audit.py:167,171` and zero `sys.exit` hits in `fec/audit/audit_frontier.py`.)

**Not strictly read-only.** It leaves `_audit_tmp_optimize.json` and `_audit_tmp_frontier.json` in `data\system\audit_scratch\` (never cleaned up — no `os.remove` in the file; the directory is created with `os.makedirs(exist_ok=True)` at `audit_full.py:167`, and it is deliberately outside every store the system manifest measures — landing them in `data\lobbying`/`data\money` is what made those stores' A2b sentinels always-red, DE-011), and its `compute_pillars.py` sub-run refreshes `pillar_inputs_snapshot.json` when the workbook view cache is alive. "Read-only-safe" (project law) means *safe to run autonomously*, not zero-write.

**Normal noise, do not flag:**
- `legacy_workbook_audit.py` A2/A3 print `SKIP (view cache stale; self-heals on Excel open)` and count as passes — Excel formula caches die after any openpyxl save and revive when Paul opens the workbook (`legacy_workbook_audit.py:19-25`).
- `compute_pillars` printing `view STALE ... verifying the AUTHORITY instead` (`compute_pillars.py:115`) is normal between Excel opens.
- Deliberately tolerant thresholds in `audit_frontier.py`, each with an inline history comment: defend-skew ≤0.92 (relaxed 0.80→0.85→0.90→0.92 because pro-CU defendable allies genuinely skew Republican — a data fact, verified repeatedly, lines 67-78), electoral-base tolerance 1.5 for Monte-Carlo noise (41-45), contest entry-mix enforced only at n≥12 (52-66). Do not "tighten" these; the comments are the refuted-finding ledger.

**Known accepted failures: none on this tree as of 2026-07-09** — a healthy run is `N passed, 0 FAILED` (count grows — trust the run's own tail). One caution: a 2026-07-08 audit on a different branch (`claude/magical-booth-f272da`, report `AUDIT_FINDINGS_2026-07-08_NETWORK_VOTE_CYCLE.md`, not on main) recorded "64/65 with 1 pre-existing electoral_plays fail"; that report is not in this tree, so if you ever see an electoral-plays check fail, read that branch's report before treating it as new.

**legacy_workbook_audit.py argument-order trap.** `legacy_workbook_audit.py` uses `ok(cond, msg)`; `run_tests.py`/`audit_full.py`/`audit_frontier.py` use `(name, cond, detail)`. Copy-pasting a check between files silently inverts it.

---

## 2. The standing diagnostic fleet — with interpretation

These are measurement instruments, not gates: most print numbers for a human/model to interpret. None of them is consumed by the production chain.

### `fec/stance/stance_eval.py` — stance-classifier accuracy vs gold

**What it measures.** Scores ANY prediction column in `gold_label_queue.csv` (live root) against the user-adjudicated `gold_cu_alignment` column. Labels are 4-class: support / oppose / neutral / unrelated. Usage: `python ...\fec\stance\stance_eval.py [pred_column]`, default column `model_stance` (`stance_eval.py:12`).

**How to read it.** The headline is **macro-F1**, not accuracy. F1 = harmonic mean of precision (of the items I predicted class X, how many were truly X) and recall (of the truly-X items, how many I found). *Macro*-F1 averages F1 over the classes that appear — so a classifier can't look good by only nailing the majority class. It prints the same breakdown per source channel (`own-domain`, `acu`, `third-party`) and per slice tag (`cfpb`, `interchange`, ...) so you can pick per-slice champions, plus a gold→pred confusion matrix. If no rows are adjudicated yet it says so and exits 0.

**Interpretation rules.** Accuracy >> macro-F1 means the model is coasting on an easy majority class. A slice that lags the ALL row tells you where the next labeling/model effort goes. **Never** "fix" a disagreement by relabeling gold — gold labels are Paul's domain; the mechanism for disputes is the conflict column, which the audit checks is flagged-not-silently-resolved (`audit_full.py:163-167`).

### `fec/engine/mc_stability_check.py` — is MC=20 enough?

**The question.** The budget-frontier engine estimates influence cascades by Monte Carlo (MC) — running the random spread process 20 times and averaging. Published work (Almazaydeh et al., cited in the docstring) shows noisy MC estimates can corrupt greedy seed selection. Moneyball is protected by CRN (all candidates compared under identical draws), but a residual risk remains: the picked seed set could be overfit to one seed's particular 20 realizations.

**What it does** (`mc_stability_check.py:15-27`): rebuilds a single-topic frontier 4 ways — production (MC=20, SEED=7), 5× budget (MC=100, SEED=7), and two different RNG seeds — via `budget_frontier.py` subprocesses with `FRONTIER_OUT` pointed at `_mcstab_*.json` temp files (created then deleted at live root). Compares the picked seed sequences: Jaccard set-overlap, longest identical prefix, spread delta.

**How to read it** (printed by the script itself): high set-overlap at MC=100 and across seeds ⇒ MC=20+CRN is NOT draw-overfit; low overlap ⇒ raise the frontier MC budget. The recorded validation result is 100% seed overlap (comment at `salience_shock.py:44`). Env: `TOPIC=<name>` (default Interchange). Re-run after any change to cascade physics or seed scoring.

### `fec/members/receptivity_sensitivity.py` — bounding untested constants

**The honesty problem it solves.** Constants like the `.18` susceptibility scaling and the `0.60` retiring factor are literature-shaped design choices no outcome data has ever tested. This harness does the next-best thing: it **bounds** them — sweep each constant across a plausible range and recompute the decision surface (per-member flip-model winnability, the thing allocations key off).

**Built-in safety**: a Stage-1 replication gate recomputes `pressure_mult`/`seed_prob` from the artifact's own stored components under baseline constants and requires an exact 533/533 match before any sweep is trusted (`receptivity_sensitivity.py:43-52`) — if formulas drifted, it aborts with `REPLICATION GATE FAILED`. It also aborts if the artifact basis isn't `behavioral`.

**How to read it.** Per variant it prints top-20 overlap, top-50 overlap, rank correlation (Spearman rho — correlation of rank orderings, 1.0 = identical order), and a verdict: **ROBUST** (top-20 overlap ≥18/20: the constant's exact value cannot have changed WHO gets targeted), MODERATE (≥15), **SENSITIVE** (the constant to take to an outcome test first). The 9 swept variants include halving/1.5×ing the susceptibility scale, prospect-theory weights, retiring factor 0.45/0.80/1.00, and persona weight 0/.45 (`receptivity_sensitivity.py:84-94`). The seed_prob sweep is gate-level analytics only — cascades are not rerun, and the script says so honestly. Note: PERSONA_W=0.30 itself is user-ratified KEEP — sensitivity output about it informs, it does not reopen the decision (session-ratified, 2026-07).

### `fec/engine/kb_benchmark.py` — external theory benchmark (Battaglini-Patacchini)

**What it measures.** B-P's NBER model predicts interest groups allocate money in proportion to **Katz-Bonacich (KB) centrality** — a network score counting all weighted downstream walks (who you can move, directly and through intermediaries). This script computes KB on the live diffusion kernel `build_P` and prints Spearman correlations against: the optimizer's suggested allocation, observed CU money, observed industry money, and the legislative score. Writes `kb_benchmark.json`; the chain does NOT consume it (`kb_benchmark.py:6-18,102`). Env: `KB_DELTA=0.85` (decay as a fraction of spectral radius). Requires `optimize_result.json` to exist.

**Why allocator ≈ −0.21 is BY DESIGN, not a bug.** Recorded results (in-repo: `AUDIT_FINDINGS_2026-07-04.md:682-690`): KB↔legislative score +0.62 (the network pillar already prices centrality); industry money tracks KB (+0.24) more than CU money (+0.14) — the opposition plays closer to the B-P equilibrium; and the optimizer **anti-correlates** (−0.21). The top-decile-KB-but-$0 list is committed allies (Barr, Hill, Emmer...) priced out by ally-parity and stance gates: the model knowingly buys *marginal persuasion*, not *access to centrality*. If you rerun this and see a negative allocator rho, that is the documented design choice being measured — do not "fix" the optimizer toward KB.

### `fec/network/signed_coalitions.py` — antagonist splinter detection

**What it measures.** Runs the Aref-Neal generalized-balance partition on the signed member-mention graph (`member_references.json`: cross-media mentions with a net valence per pair). It finds the k=1..3 partitions minimizing **frustration** — the weight of negative edges inside clusters plus positive edges across clusters (a perfectly "balanced" signed network has zero). Deterministic multi-restart local search; env `SC_MINW` (edge weight floor, default 0) and `SC_RESTARTS` (default 60). Writes `signed_coalitions.json`; chain does not consume.

**How to read it.** Our substrate is the *mention* layer, ~87% positive weight, so — unlike Aref-Neal's vote-signed House graph — expect a near-single-bloc partition, and the script says so at k=2 (`signed_coalitions.py:92-93`). **The splinter IS the finding**: the small cluster is the antagonist set whose signed ties frustrate the main bloc (recorded 2026-07-04 result: a 16-member partisan-combat splinter, `AUDIT_FINDINGS_2026-07-04.md:673-681`; the k=3 third cluster came back empty — an honest null). Use it to sanity-check that members the influence engines treat as bridge-builders are not actually in the antagonist set.

### `fec/engine/outcome_snapshot.py` — the prospective-outcome harness (armed once, 2026-07-04)

**Why it exists.** `receptivity_sensitivity.py` can only prove constants are decision-robust; only **out-of-sample outcomes** can validate their magnitudes (the "A-grade path" — the docstring's phrase, `outcome_snapshot.py:3-6`). This harness freezes today's predictions so a future comparison is untouchable by hindsight.

**Pre-registered hypotheses, locked in the file** (`outcome_snapshot.py:8-17`): H1 — frozen `seed_prob` correlates positively with NEW co-sponsorships adopted after the freeze; H2 — frozen `pressure_mult` correlates positively with |stance-tier movement|. Bars, locked: rho ≥ +.20 PASS · +.10–.20 DIRECTIONAL · below +.10 the magnitudes stay design choices · ≤ −.10 INDICTED. Minimum data: ≥60 days elapsed AND ≥150 members with a co-sponsorship delta, else the scorer prints UNDERPOWERED and refuses.

**How to arm and score it:**

```powershell
# ARM (freeze). PROPOSE TO PAUL FIRST, then run — arming a pre-registered harness is a
# research action with look-discipline consequences (see moneyball-research-frontier Problem 2).
# Writes data\engine\outcome_snapshot_<date>.json (fec/engine/outcome_snapshot.py:64). Reads
# member_receptivity.json + behavior_panel.json + category_stance.json.
python "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\fec\engine\outcome_snapshot.py" --freeze

# SCORE (read-only), any time >= 60 days later:
python "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\fec\engine\outcome_snapshot.py" --score "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\data\engine\outcome_snapshot_2026-07-04.json"
```

**Current state (2026-07-09): already armed once.** The frozen 2026-07-04 snapshot (taken the day the behavioral basis shipped) is `data\engine\outcome_snapshot_2026-07-04.json` — pass that path to `--score`; `--freeze` writes `data\engine\outcome_snapshot_<date>.json` (`fec/engine/outcome_snapshot.py:64`). (Location corrected 2026-09-30; verified against that line and the LIVE `data\engine\` listing.) It is scoreable from ~2026-09-02 if the movers floor is met. Practice: freeze a NEW snapshot after any change to the receptivity formulas (the old snapshot still scores the old formula — that is the point), propose each freeze to Paul before running it, and never edit a frozen snapshot. Do not "re-look" or reinterpret the bars after seeing data — the consequences are pre-declared, which is what makes a pass mean something (see `moneyball-research-methodology`).

### `fec/engine/method_audit.py` — calibration diagnostics (prose, not a gate)

Prints four diagnostics: M1 flip-probability calibration by stance tier (expect monotone decreasing from Champion to Opponent + a negative Spearman vs the stance ordinal), M2 cascade coefficient-of-variation over 15 runs (stable if CV < 0.03), M3 PAC-money cross-check against pasted OpenSecrets totals, M4 rank calibration. It predates parts of the current taxonomy and uses its own `random.seed(3)` — treat output as diagnostic prose, never as pass/fail. **cwd matters**: it opens `itpas2.txt` relative, and that file lives only on the live tree (data files are gitignored, so a worktree has no copy):

```powershell
cd "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\fec"; python engine/method_audit.py
```

### `fec/audit/audit_frontier.py` — standalone frontier sub-audit

Usually consumed via audit_full section [1], but useful alone after frontier work: monotone spread paths, submodularity (marginals broadly non-increasing, MC-noise tolerant), play gating (contest=Opponents, defend=allies), party-blindness of gates, knee-in-range, nested paths. 12 checks when `member_receptivity.json` is present; 11 with a visible `SKIP` line when absent (the missing check then drops the count below audit_full's ≥11 floor — deliberate). Always exits 0; read the tail (`FRONTIER AUDIT — N passed, 0 FAILED` + `ALL CHECKS PASSED.`).

---

## 3. Input-purity byte-match (gate-d): proving a change is behavior-neutral

**The problem.** After you touch code (or after any run), engine artifacts' hashes differ from your pre-state. Was that your change (bad — unexplained behavioral delta, an S1 finding) or did the inputs move underneath you (Paul's collectors and jobs write to the live tree continuously)?

**The method, in brief.** The engines are deterministic pure functions of their on-disk inputs (CRN, fixed seeds), so: rerun the engine against current inputs with output redirected to a temp path (`FRONTIER_OUT` at `budget_frontier.py:153`, production default `data\money\budget_frontier.json` at `:152` / `OPT_OUT` at `optimize.py:33`; pins corrected 2026-09-30) and MD5-compare against the live artifact — a byte-match proves the delta was input-driven; a mismatch is a real behavioral change. The byte-match doubles as a fixed-point check that two-run convergence has settled (`bipartisan.json` is the ONLY remaining feedback edge — col G has been a pure output since @f17dc2c, `fec/stance/per_category_stance.py:9-13`). For engines without a redirect dial, use the determinism double-run (two temp outputs, byte-compare — what audit_full's determinism gates at lines 64/76/94/115 automate).

**The full recipe — commands, interpretation rules, and the worked example — is owned by `moneyball-proof-and-analysis-toolkit` Recipe 5; use that, don't re-derive it here.** Method codified in `AUDIT_FINDINGS_2026-07-03.md:33-44`; idempotency baseline (12/12 byte-identical double-run) established at S2-04. Check for live user jobs and a clean shell (`scripts/env_dials.py`) before running.

**The full gate-d protocol** for a code change (from `.claude/commands/fable-audit.md:40-53` and `README.md:63`): kernel tests → run pipeline → **zero rank delta** (use `scripts/rank_delta.py` on the pre-state copy of `ranks_python.json` vs the new one) → audit tail ALL MODULES CLEAN → any artifact-hash delta explained via input-purity. Whether you are *allowed* to run the pipeline for this is governed by `moneyball-change-control`.

---

## 4. Mtime-ordering freshness checks

Derived artifacts do not know when their inputs changed — nothing re-runs producers automatically outside the chain (`CHAIN` in `fec/run_pipeline.py:45-292`: 80 entries; a default run executes 79 because `DESK_RESPONSIVENESS=0` drops `responsiveness_layers.py` at `:300-302`; as of 2026-09-30), and several diagnostic/collector producers are NOT in the chain at all (`kb_benchmark.py`, `signed_coalitions.py`, the collectors). The cheap detector is mtime ordering: **an input file newer than its derived artifact means the producer has not seen that input.**

- The audit itself uses this method once: the press-component meta must be fresh vs the tone CSV within one weekly cycle (`audit_full.py:206-210`).
- The audit CANNOT see the most famous staleness: `electoral_plays.json` internal-consistency checks pass even when the stance matrix has moved (audit_full §[3]). The 2026-07-09 flag resolved 2026-07-10: an authorized rebuild was **byte-identical** (content already current; the flag was mtime-ordering only). The fix chain (`build_electoral_plays.py → build_dashboard_bundle.py → make_dashboard_html.py`) remains **user-gated: never run it unprompted** (session-ratified, 2026-07).
- `scripts/artifact_freshness.py` (below) automates the sweep with a verified dependency table. A STALE flag is a *lead, not a verdict*: chain ordering makes some "input newer than consumer" situations legitimate (the workbook is written after `ranks_python.json`; `bipartisan.json` is two-run-convergent), which is why those pairs are deliberately absent from the table.

---

## 5. Shipped helper scripts

Location: `.claude/skills/moneyball-diagnostics-and-tooling/scripts/` (this skill's directory — `$SKILL` below means wherever this SKILL.md lives, main repo or worktree; the scripts behave identically from either because they take the target root as an argument). All three are stdlib-only, never import fec modules (import == execution over there), and only print. All three were run against the live tree on 2026-07-09.

### `scripts/rank_delta.py` — the zero-rank-delta gate, mechanized

```powershell
# BEFORE a run: copy the authority aside
Copy-Item "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\ranks_python.json" "$env:TEMP\ranks_before.json"
# ... run whatever you are verifying ...
python "$SKILL\scripts\rank_delta.py" "$env:TEMP\ranks_before.json" "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\ranks_python.json" --top 15
```

Prints member add/drop, rank-delta count, score-delta count (>1e-12), and top movers. Exit 0 only on ZERO DELTA (so it can gate a script); exit 1 on any delta; exit 2 on usage error. Schema it reads (`score`/`rank` maps) verified against the producer `compute_pillars.py:100-102`.

### `scripts/artifact_freshness.py` — staleness sweep

```powershell
python "$SKILL\scripts\artifact_freshness.py" "C:\Users\pgoff\OneDrive\Desktop\Melange Systems" --tol 2
```

Checks 11 derived artifacts against their producer's verified file reads (table embedded in the script with producer names; e.g. `budget_frontier.json` depends on `member_receptivity.json` via the kernel's lazy receptivity load). Prints `fresh` / `STALE (+minutes, which input)` / `MISSING` per artifact and a summary. Always exits 0 — staleness can be legitimate; the output tells you which producer to *consider*, and marks the user-gated ones. On 2026-07-09 it flagged `electoral_plays.json` STALE by mtime (resolved 2026-07-10: the authorized rebuild was byte-identical — a standing reminder that an mtime flag is a lead, not proof of content drift) plus the non-chain diagnostics (`kb_benchmark.json`, `signed_coalitions.json`) as post-dating their inputs — expected, since nothing re-runs them automatically.

### `scripts/env_dials.py` — dial drift detector + clean-shell proof

```powershell
# point it at whichever source tree you are working on (live repo root or a worktree root):
python "$SKILL\scripts\env_dials.py" "C:\Users\pgoff\OneDrive\Desktop\Melange Systems"
```

Regex-scans every `.py` under `<root>/fec/`, recursively (skipping `__pycache__`, hidden directories and `fec/attic/`), for `os.environ.get / os.environ[...] / os.getenv` and prints every dial with its in-code default, reading files, and a loud `<== SET NOW` flag plus summary WARNING if any dial is set in the current shell. Found 88 distinct dials across 138 files on 2026-07-09; on 2026-09-30 the recursive scan of a worktree found 296 across 1243 files, where the old top-level-only scan (`fec/*.py` + `fec/tests/*.py`) saw 21 across 26 and missed `FRONTIER_OUT`, `OPT_OUT`, `SEED`, `MC` and `TOPIC` (corrected 2026-09-30; verified by running the script before and after the change). Two uses: (1) prove your shell is clean before a baseline — the WARNING tail names every dial set in this shell; OS variables the code also reads (`APPDATA`, `LOCALAPPDATA`, `TEMP`, `TMP`, `USERPROFILE` and the rest of the script's `PLATFORM` set) are labelled `platform variable` and never count, so a clean shell ends `shell clean: no dial set` (corrected 2026-09-30), (2) diff against the curated catalog in `moneyball-config-and-flags` to find dials added since it was written. Defaults are shown as written at the call site — a dial appearing with multiple defaults (e.g. `TOPIC`, `MC`) means different scripts choose different defaults, which is real and worth knowing.

---

## Provenance and maintenance (2026-07-09)

Facts here decay. Re-verify before trusting a number; run data-dependent commands from the live repo root (`cd "C:\Users\pgoff\OneDrive\Desktop\Melange Systems"`), or set `MONEYBALL_ROOT` to it — quote the path.

Last measured (dated — counts drift, so trust each run's own tail): `fec/tests/run_tests.py` 247 passed / 2 FAILED in LIVE on 2026-09-20 (standing reds `test_bill_collision_guards`, `test_make_staffer_network_html`); `fec/audit/audit_full.py` 559 passed / 9 FAILED in LIVE on 2026-09-19 (after that day's membership refresh) (both recorded in the Project Brain STATE); the chain has 80 `CHAIN` entries, 79 run by default (`fec/run_pipeline.py:45-302`), counted 2026-09-30 at main 25eefa3fc.

| Volatile fact | Re-verify with |
|---|---|
| Kernel test count (grows — trust the run's own tail) | `python "fec\tests\run_tests.py"` → tail `KERNEL TESTS — N passed`; or count: `grep -c "^ok(" fec/tests/run_tests.py` is unreliable (indented calls and registered module suites) — run it. |
| audit_full check count (grows — trust the run's own tail), ALL MODULES CLEAN | `python "fec\audit\audit_full.py"` → tail (check live jobs first); count grows as guards are added — any FAILED is the finding, not a count mismatch (`.claude/commands/fable-audit.md:35`). |
| Harness exit codes differ | `Select-String -Path fec\audit\audit_full.py -Pattern "sys.exit"` → expect exactly one hit, line 2798 on main; `Select-String -Path fec\audit\legacy_workbook_audit.py,fec\audit\audit_frontier.py -Pattern "sys.exit"` → expect one hit, `legacy_workbook_audit.py:171` `sys.exit(main())` (it returns `1 if F else 0` at `:167`), and none in `audit_frontier.py` (corrected 2026-09-30). |
| Sub-audit floors ≥22 / ≥11 | `Select-String -Path fec\audit\audit_full.py -Pattern "legacy_workbook_audit.py','integrity"` (line 34). |
| Temp files left in the audit scratch dir | `Select-String -Path fec\audit\audit_full.py -Pattern "_audit_tmp"` (lines 159, 169, 176, 205); `Get-ChildItem "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\data\system\audit_scratch\_audit_tmp_*.json"`. |
| Redirect dials FRONTIER_OUT / OPT_OUT | `Select-String -Path fec\engine\budget_frontier.py,fec\engine\optimize.py -Pattern "FRONTIER_OUT|OPT_OUT"` (budget_frontier.py:153, optimize.py:33; pins corrected 2026-09-30). |
| README's stated kernel/audit counts | `Select-String -Path README.md -Pattern "kernel invariants|full-audit checks"` — stated counts drift; trust the run's own tail. |
| stance_eval default column + gold file | `Select-String -Path fec\stance\stance_eval.py -Pattern "model_stance|gold_label_queue"` (lines 12-13). |
| mc_stability RUNS matrix + 100%-overlap record | `Select-String -Path fec\engine\mc_stability_check.py -Pattern "RUNS ="` (line 15); `Select-String -Path fec\engine\salience_shock.py -Pattern "mc_stability"` (line 44). |
| receptivity_sensitivity replication gate + variants | `Select-String -Path fec\members\receptivity_sensitivity.py -Pattern "REPLICATION GATE|VARIANTS"` (lines 43-52, 84). |
| kb_benchmark −0.21-by-design record | `Select-String -Path AUDIT_FINDINGS_2026-07-04.md -Pattern "anti-correlates"` (line 686). |
| signed_coalitions 16-member splinter record | `Select-String -Path AUDIT_FINDINGS_2026-07-04.md -Pattern "antagonist splinter"` (line 677). |
| outcome_snapshot armed state + bars | `Get-ChildItem "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\data\engine\outcome_snapshot_*.json"` (2026-07-04 freeze exists there; `--freeze` writes there, `outcome_snapshot.py:64`; corrected 2026-09-30); bars in `fec\engine\outcome_snapshot.py:14-17`. |
| electoral_plays staleness + user gate | freshness script output; the fix chain remains user-gated until Paul directs it (session-ratified, 2026-07) — check `git log --oneline -5 -- fec/engine/build_electoral_plays.py` for a re-run having landed. |
| method_audit cwd dependency | `Select-String -Path fec\engine\method_audit.py -Pattern "itpas2"` (line 67); file exists only at the LIVE `fec\itpas2.txt`. |
| Dial inventory | `python "...\scripts\env_dials.py" "<root>"` — the number moves; the tool is the source. |
| Input-purity method codification | `Select-String -Path AUDIT_FINDINGS_2026-07-03.md -Pattern "input-purity"` (lines 33-44). |
| Imported-file-relative ROOT / worktree isolation | `Select-String -Path fec\paths.py -Pattern "MONEYBALL_ROOT"` (lines 7-8). |
