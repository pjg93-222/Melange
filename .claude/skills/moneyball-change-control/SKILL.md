---
name: moneyball-change-control
description: The constitution of the Moneyball repo. Load this BEFORE making, approving, or verifying ANY change - code edits, data refreshes, dial/constant changes, experiments, UI/template edits, doc edits, commits, merges, or branch work. Also load when you see gating words you don't know (user-gated, DATA-GATED, DIAGNOSTIC-GATED, LOCKED, look, RETIRED WITHOUT A LOOK, .candidate), when unsure whether something is Paul's decision or yours, when ranks moved and you must decide if that's a bug, or when tempted to revert/relabel/reopen anything. It does NOT teach you how to run the system day-to-day (moneyball-run-and-operate), how to debug failures (moneyball-debugging-playbook), how to design an experiment (moneyball-research-methodology), or the dial values themselves (moneyball-config-and-flags).
---

# Moneyball change control

This skill is the project's constitution: what kinds of changes exist, which gate each one passes through, the one verification protocol every change must survive, the vocabulary of gates, the list of decisions that belong to Paul (the user) alone, and the 18 non-negotiable project laws with the incident behind each. Every other skill in this library defers to this one. The system it governs is a calibrated Python->Excel congressional-influence model whose worst failure mode is "silent wrong number" - the pipeline keeps printing success while producing subtly wrong rankings - so the rules here are mostly about proving a change did exactly what was intended and nothing else. When in doubt, the posture is always: build the mechanism, gate the activation, ask Paul.

## When NOT to use this skill

- Running the chain, collectors, or dashboards day-to-day, ports, what lands where -> **moneyball-run-and-operate**
- A live failure you need to triage right now -> **moneyball-debugging-playbook**
- Designing/locking/executing a pre-registered experiment -> **moneyball-research-methodology**
- The full dial catalog and how to add a dial -> **moneyball-config-and-flags**
- What happened historically (dead ends, reverts, refuted findings in detail) -> **moneyball-failure-archaeology**
- What you may publicly claim about validity, and doc house style -> **moneyball-docs-and-claims**
- How to add tests/audit checks and what counts as evidence -> **moneyball-validation-and-qa**

## Quick reference

Repo root (live tree, where all data lives): `C:\Users\pgoff\OneDrive\Desktop\Melange Systems`. Paths contain spaces - always quote. All commands below are PowerShell-compatible.

**THE verification protocol** (every code change; documented at `README.md:63-64`, `MATHEMATICAL_SPECIFICATION.md:78-79`, `fec/tests/run_tests.py:6`):

```powershell
# 0. Check Paul isn't running jobs (law 5), snapshot ranks
Get-Process python -ErrorAction SilentlyContinue
Copy-Item "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\ranks_python.json" "$env:TEMP\ranks_before.json"

# 1. Kernel tests (84 checks as of 2026-07-19; exit 1 on failure)
python "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\fec\tests\run_tests.py"
#    expect tail:  KERNEL TESTS — 84 passed, 0 FAILED  (as of 2026-07-19; count only grows)

# 2. Full 36-step chain (36 entries as of 2026-07-19; ~6-19 min; MUTATES chain-owned live artifacts + workbook col G)
python "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\fec\run_pipeline.py"
#    expect: every step prints OK, then PIPELINE COMPLETE

# 3. Zero rank delta (unless the change is SUPPOSED to move ranks)
python -c "import json,os;a=json.load(open(os.environ['TEMP']+r'\ranks_before.json'));b=json.load(open(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\ranks_python.json'));d=[m for m in b['rank'] if a['rank'].get(m)!=b['rank'][m]];print(len(d),'members moved');print(d[:10])"
#    expect:  0 members moved

# 4. Full-body audit (136 checks as of 2026-07-19; exits 1 on failure / 0 when clean - still gate on the TEXT)
python "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\fec\audit_full.py"
#    expect tail:  FULL-BODY AUDIT — 136 passed, 0 FAILED   then   ALL MODULES CLEAN.  (as of 2026-07-19; count only grows)
```

**Gating vocabulary in one line each** (formal definitions in section 3): **user-gated** = only Paul may trigger it. **LOCKED** = a prereg's bars are frozen; the one look is armed. **look** = the single permitted evaluation; spent whether PASS or MISS. **RETIRED WITHOUT A LOOK** = experiment withdrawn before evaluation; route neither validated nor closed. **DATA-GATED / DIAGNOSTIC-GATED** = reopening blocked until a data threshold / a pinned synthetic check passes. **`.candidate`** = built but consumed by nothing until Paul promotes it.

**Absolute floor rules** (details in section 5): never run `fec/*.py` casually (import == execution; from a worktree, paths resolve to the worktree's EMPTY data plane unless `MONEYBALL_ROOT` points at live — either way casual runs are how artifacts get clobbered); never hand-edit generated JSON; never relabel stance/press items; never change a user-ratified constant in code; never `git revert`/rebase/squash; Fable model only for the 533 narratives; 8801 is Paul's port, use 8802.

---

## 1. Change classification - what kind of change is this, and what gate does it pass?

Decide the class FIRST. If a change straddles classes, it passes through the gates of every class it touches.

| # | Class | Examples | Gate / who decides | Verification required |
|---|---|---|---|---|
| 1 | **Kernel / engine code** | `fec/moneyball_core.py`, `money_response.py`, `flip_model.py`, cascade engines, `compute_pillars.py`, any script in the 36-step chain (36 entries as of 2026-07-19) | You may implement; Paul ratifies anything that changes outputs or calibrated behavior | Full protocol (above). Zero rank delta for a pure refactor; ANY unexplained delta = stop, it's an S1 finding |
| 2 | **Data refresh** | Collectors, corpus rebuilds, network rebuild, then the chain | Allowed, but check for Paul's live jobs first (law 5); order per `README.md:65-67`: collectors -> `big5_traits` -> `social_interaction_layer` -> `build_multilayer_network` -> `build_media_blend` -> `run_pipeline.py` | Ranks MAY legitimately move (input-driven). Prove it with the input-purity test (section 2.4). Deletions from data (dedup) are user-gated (law 15) |
| 3 | **Dial / constant change** | Env-dial defaults, kernel constant tables (PERS/IMP/SGATE/TORD), workbook dials (pillar weights, row-535 press weights) | **Paul's alone** for anything user-ratified (law 14). Workbook dials are edited by Paul in Excel, never by code. New dials: default must reproduce current behavior (empty env == production) | If a default changes with ratification: full protocol; rank deltas expected and must be reported to Paul |
| 4 | **Prereg'd experiment** | Any statistical validity claim, new instrument/criterion, any "does X predict Y" | A `*_prereg.md` with `STATUS: LOCKED` committed BEFORE data is examined; one look; see **moneyball-research-methodology** | The prereg's own pre-declared consequences. No engine wiring until consequences say so and Paul ratifies engine-touching promotions |
| 5 | **UI / dashboard / desk** | `fec/templates/*.tpl`, `make_dashboard_html.py`, `make_member_desk.py`, `make_combined.py` | You may implement (display-only); anything that reclassifies members (e.g. the electoral_plays chain) is user-gated (law 11) | Full protocol - the HTML builders are chain entries 26, 34, and 35 as of 2026-07-19. Rank delta must be zero (display never feeds engines). **JS-mirror duty**: math duplicated into `make_dashboard_html_00.tpl` (lt_priming `prime()`, cascade kernel) must stay in lockstep with Python - `fec/lt_priming.py:36-37` says so explicitly |
| 6 | **Docs (`*.md`)** | README, spec, methods ledger, audit reports | You may write; claims must follow **moneyball-docs-and-claims** and law 12. Nothing may contradict `MATHEMATICAL_SPECIFICATION.md` ("the code is authoritative", spec:5-6). Audit reports are append-only - never overwrite an old report (the `_RUN2` suffix precedent) | None mechanical; a doc-only commit does not need the chain |
| 7 | **Tests / audit checks** | `fec/tests/run_tests.py`, `fec/audit_full.py` | Adding checks is always welcome. NEVER weaken a floor or count assertion to make your own change pass (incident H-3, `AUDIT_FINDINGS_2026-07-07.md:68-74`) | Run the harness; the check count grows over time - a higher count than documented is normal, any FAILED is the finding (`.claude/commands/fable-audit.md:35-36`) |

**Special hazard class - the `apply_*` family.** Ten one-shot workbook-mutation scripts sit live at `fec/` top level (`apply_alloc_cap.py`, `apply_committee_fix.py`, `apply_committee_reweight.py`, `apply_leg_stance.py`, `apply_press_dedup.py`, `apply_press_overrides.py`, `apply_raw_max_norm.py`, `apply_stance_guard.py`, `apply_two_hop_stance.py`, `apply_weights.py`). They are COM-era manual calibration tools, not pipeline steps. Treat them as loaded guns: never run casually, Excel must be closed, and two of their relatives (`fec/sync_stance_clean.py`, `fec/apply_stance_guard.py`) are hard-guarded with an immediate `sys.exit` because they are superseded AND destructive (`fec/sync_stance_clean.py:4`). See law 17.

## 2. THE verification protocol, in full

The one-line version lives in three docs of record (`README.md:63-64`, `MATHEMATICAL_SPECIFICATION.md:78-79`, `fec/tests/run_tests.py:6`): **kernel tests -> run_pipeline -> zero rank delta vs the last ranks_*.json (unless the change is supposed to move ranks) -> audit clean.** Details, expected outputs, and traps:

### 2.0 Before you start

- **Check for Paul's live jobs** (law 5): `Get-Process python`; also eyeball recent artifact mtimes in the live root (`Get-ChildItem "C:\Users\pgoff\OneDrive\Desktop\Melange Systems" -Filter *.json | Sort-Object LastWriteTime -Descending | Select-Object -First 10 Name,LastWriteTime`). Fresh mtimes you didn't cause = someone else is running. Wait.
- **Ask Paul to close Excel** if the workbook `Moneyball Main Version - Blended.xlsx` is open - chain entry 15 as of 2026-07-19 (`sync_stance_g.py`) saves it via openpyxl and will PermissionError (law 17).
- **Never set calibration env dials during verification** (`SEED`, `MC`, `MAXSHIFT`, `DTHRESH`, `PERS_NONE`, `RT_W`, `SOCIAL_SHRINK`, `BP_SRC`, ...) - defaults ARE the ratified state (`.claude/commands/fable-audit.md:16-19`).
- **Snapshot the pre-state**: at minimum copy `ranks_python.json` to a temp location. For a thorough (audit-grade) run also record md5 hashes of `budget_frontier*.json`, `optimize_result.json`, `per_topic_*.json`, `salience_advisory.json`, `dashboard_data.json` (`.claude/commands/fable-audit.md:41-42`).

### 2.1 Kernel tests

```powershell
python "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\fec\tests\run_tests.py"
```
Expected tail: `KERNEL TESTS — 84 passed, 0 FAILED` (84 checks as of 2026-07-19; the count only grows — trust the run output). This script exits 1 on failure and 0 when clean: `sys.exit(1 if F else 0)` (`fec/tests/run_tests.py:297-298`); `audit_full.py` now does too. It reads live data via the kernel; its core atomic-write checks create and delete OS-temp files (`fec/tests/run_tests.py:31-48`). (Corrected 2026-07-19; verified against `fec/audit_full.py:1198-1202`.)

### 2.2 The chain

```powershell
python "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\fec\run_pipeline.py"
```
36 steps in fixed order as of 2026-07-19 (`fec/run_pipeline.py:25-67`), ending in `audit_full.py`. Each step prints `OK` or `!!` plus its last stdout line; the runner hard-exits 1 on the first failing step. Expected final line: `PIPELINE COMPLETE in N.N min` (~6-19 min depending on the workbook view-cache state). **Trap (softened 2026-07-19)**: an audit step "OK" at chain level now means `audit_full.py` returned 0 and reported no FAILs; it exits 1 when any check fails (`fec/audit_full.py:1198-1202`). Still read the audit tail yourself and require `ALL MODULES CLEAN.` as belt-and-braces for older automation that may assume exit 0.

`--from <prefix>` resumes mid-chain by script-filename prefix. **Guard (corrected 2026-07-19)**: `start_index()` now rejects unknown or ambiguous `--from` prefixes loudly (`ValueError` → `parser.error`, exit 2; `fec/run_pipeline.py:145-154`). `--recalc` is retired and inert.

### 2.3 Zero rank delta - how to actually diff ranks

`ranks_python.json` (the rank authority, written by `compute_pillars.py --write`) is a dict with keys `score` (member -> float), `rank` (member -> int), `press_pillar`, `pcts`, `ab_weights`, `provenance` (`fec/compute_pillars.py:100-102`). Diff the `rank` map against your snapshot:

```powershell
python -c "import json,os;a=json.load(open(os.environ['TEMP']+r'\ranks_before.json'));b=json.load(open(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\ranks_python.json'));d=[(m,a['rank'].get(m),b['rank'][m]) for m in b['rank'] if a['rank'].get(m)!=b['rank'][m]];print(len(d),'of',len(b['rank']),'members moved');[print(x) for x in d[:15]]"
```
Expected for a pure code change: `0 of 533 members moved`.

If members moved, there are exactly three legitimate explanations before it's a bug (known-benign registry, `.claude/commands/fable-audit.md:45-51,72-77`):
1. **Real input change** - new collector data landed, or Paul edited a dial in Excel. Prove it with the input-purity test (2.4).
2. **Two-run convergence** - `bipartisan.json` is the ONLY remaining feedback edge: it is written late in the chain by `build_dashboard_bundle.py` but read by the kernel in earlier steps, so the run AFTER a stance/network change legitimately shifts engine outputs once more. A second chain run must then be a fixed point. (Col G is NOT part of this: it has been a pure output since @f17dc2c - `fec/per_category_stance.py:9-13`; accepting a "col-G convergence" story is exactly the wrong excuse that masked the S2-04 limit cycle.)
3. **Another session wrote mid-run** - check `git worktree list` and live processes.

Anything else = **S1 finding** (unexplained rank delta). Stop, do not commit, diagnose. If your change was SUPPOSED to move ranks: enumerate the movers, confirm every one is explained by the intended mechanism, and put the count + examples in the commit message (precedent: "Judiciary seats added, 494/533 ranks moved intentionally", recorded in `AUDIT_FINDINGS_2026-07-04.md`).

**Cross-check**: `python "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\fec\compute_pillars.py"` (no flag) is a read-mostly parity mode that recomputes everything and prints `PARITY: CLEAN` if the authority matches; it exits 1 on drift/stale/missing (`fec/compute_pillars.py:106-124`).

### 2.4 The input-purity test (proving a hash delta came from inputs, not your code)

For a deterministic engine whose artifact hash changed: re-run it against current on-disk inputs with output redirected to a temp path (the `FRONTIER_OUT`/`OPT_OUT` dials exist precisely so probes never clobber production), then byte-compare MD5s. Byte-match proves the delta was input-driven; mismatch = real behavioral change. **The full recipe (commands, interpretation rules, worked example) is owned by `moneyball-proof-and-analysis-toolkit` Recipe 5** - use that; method codified in `AUDIT_FINDINGS_2026-07-03.md:33-44`.

### 2.5 The audit

```powershell
python "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\fec\audit_full.py"
```
Expected tail (136 checks as of 2026-07-19; the count only grows; report shape at `fec/audit_full.py:1198-1202`):
```
FULL-BODY AUDIT — 136 passed, 0 FAILED
  ALL MODULES CLEAN.
```
On failure it prints `FAILURES: [<names>]` and exits 1; when clean it prints `ALL MODULES CLEAN.` and exits 0 (`fec/audit_full.py:1198-1202`, corrected 2026-07-19). Treat a nonzero return code as a real failure signal, and still gate on the text tail `ALL MODULES CLEAN.` as belt-and-braces because older automation may assume exit 0. Known-normal noise: `audit.py` A2/A3 checks self-SKIP (recorded as passes) when the workbook formula cache is dead between Excel opens, and `compute_pillars` prints "(view cache dead -> snapshot)" - both benign (`.claude/commands/fable-audit.md:72-75`). The audit is not zero-write: it leaves `_audit_tmp_optimize.json` / `_audit_tmp_frontier.json` at the live root by design.

### 2.6 What "verified" means for a commit

A change is committable when: kernel tests 84/84 as of 2026-07-19 (count only grows) -> chain all-OK -> rank delta zero-or-fully-explained -> audit `ALL MODULES CLEAN.` Record the numbers in the commit body (see section 6). Output-affecting fixes discovered during an audit stay report-only UNLESS this full protocol is re-run after them (`.claude/commands/fable-audit.md:90-94`).

## 3. Gating vocabulary - formal definitions

These words are load-bearing in commit messages, preregs, and reports. Use them exactly.

- **user-gated** - the action may only be triggered by Paul's explicit go-ahead, even when the underlying problem is real and the fix is ready. Doing it unprompted is a violation regardless of correctness. Standing user-gated list: section 4.
- **LOCKED** - a pre-registration file (`*_prereg.md` at repo root) contains the literal line `STATUS: LOCKED`, committed BEFORE the evaluation data is examined (strongest form: before the data even exists - `big5_es_votesmart_prereg.md:3`). Bars, method, and consequences are frozen; "bars never move after data is seen." The look-gate scripts machine-enforce this: they refuse to run if the prereg is absent, the `STATUS: LOCKED` line is absent, a newline-anchored `## RESULT-*` heading already exists (look consumed), or input fingerprints drifted (`fec/b5_n_matrix.py:356-367`).
- **look** - the single permitted computation of the real pairing against the locked bars. Consumed whether the outcome is PASS or MISS; recorded verbatim under a `## RESULT` heading in the prereg, same session. Simulate-battery runs and pre-lock probes are NOT looks.
- **MISS / PASS** - the pre-registered bar was not met / met. MISSes are permanent ledger entries (in `big5_methods.md`); they are never reverted, buried, or re-run.
- **RETIRED WITHOUT A LOOK** - the prereg was withdrawn before any evaluation because the simulate battery (a synthetic plant test the analysis machinery must pass first) refused the look. No look consumed, no status changes in either direction, the route is neither validated nor closed. Calling it "failed" is a mis-claim. Each retirement records a re-entry gate:
  - **DATA-GATED** - reopening is blocked until a data condition is met. Example: the round-4 N-route reopens only at MEM_N >= 250 covered members (commit 48fd00d; `big5_n_matrix_prereg.md`).
  - **DIAGNOSTIC-GATED** - reopening is blocked until a pinned synthetic diagnostic passes. Example: the round-5 A-route reopens only when its 5-seed diagnostic passes >= 3/5 on bars 1-4 (commit d223188; `big5_a_matrix_prereg.md`). Safe to re-check the diagnostic any time - it is synthetic-only.
- **`.candidate` / `*_candidate`** - the staged-awaiting-Paul naming convention: an artifact or script that is built, tested, and tracked but consumed by NOTHING until user-ratified promotion. Remaining live example: `fec/liwc/behavior_calibrated.json.candidate`. The convention's showcase, `coop_v2_candidate.*`, GRADUATED 2026-07-10: Paul ratified the engine promotion and it shipped as `RECEPT_COOP=v2` (@94f09cf, merged to main 2026-07-10) - the artifact keeps its `_candidate` name for history, and its docstring/provenance were updated post-promotion (@c80e1d3). Reuse this convention for anything you build that needs Paul's sign-off to go live.
- **CLOSED / CLOSED PERMANENTLY** - a route closed with recorded evidence (a consumed MISS look plus, for PERMANENTLY, a pre-declared "final attempt" clause). Do not reopen; the kill-ledger exists so no future session re-runs them.
- **kill-ledger** - the recorded list of dead probes with cause of death (`big5_methods.md` sections 18-19). Binding on future sessions.
- **Revert switch / env dial** - the repo's rollback mechanism. There are ZERO `git revert` commits in history; shipped changes carry an env-var dial whose non-default value rolls the behavior back (e.g. `BAKKER_XCUE=0`, `RECEPT_TRAITS=lexical`). Rollback = flip the dial, never rewrite history.

## 4. The user-domain boundary - Paul's decisions alone

If a task requires any of these, prepare the mechanism, present the evidence, and STOP. Never execute unprompted, even when you are certain you are right.

| Domain | What specifically | Where it stands as of 2026-07-09 |
|---|---|---|
| **Stance/press labels** | Relabeling ANY press/stance classification | Law 1. Build override mechanisms instead. Velazquez CFPB=Opponent / CCM=True-Neutral ratified correct 2026-07-08 - do not re-flag (session-ratified, 2026-07) |
| **Weights & ratified constants** | Pillar weights (live 30/25/40/5, typed in workbook col-28 rows 2-5), row-535 press tier weights, PERS '-'=0.45, DTHRESH=11.25, BP_SRC=cosponsor, the say-do A/V/J corroboration design, PERSONA_W=0.30 | Law 14, law 9. Paul changes these in Excel or by directive; never silently in code |
| **electoral_plays re-run** | `build_electoral_plays.py -> build_dashboard_bundle.py -> make_dashboard_html.py` | Law 11 - user-gated, standing. The 2026-07-09 staleness flag RESOLVED 2026-07-10: Paul authorized a re-run and the rebuild was byte-identical (the reclassification had already landed; the flag was mtime-only) |
| **Data deletions** | Any DELETE from the D2/legacy duplicate ledgers (CREC/interview dup rows) | Law 15. Ledger stands; no dedup DELETE without Paul |
| **coop_v2 engine promotion** | Wiring `coop_v2_candidate.json` into susceptibility/seed_prob slots | **DECIDED: granted by Paul, SHIPPED and merged to main 2026-07-10** (@94f09cf) - `RECEPT_COOP=v2` default, `v1` = wholesale revert. Reverting to v1 is itself a user decision |
| **Vote Smart collection** | Triggering the collection (originally via an API key -> `fec/votesmart_api_key.txt`, gitignored) | CONCLUDED and merged to main 2026-07-10 (@02a36ac): collection COMPLETED 517/518 via a user-directed browser-session protocol AMENDMENT (@3de2fdc; the key file was never used) and the one look CONSUMED (@e77703c, RESULT-VS TIER 5 UNCORROBORATED — methods §22). **Never re-collect or re-take the look** |
| **Crapo CCM cell** | Filling the blank Credit Card Mandates cell with real anti-CCCA evidence (the only lever back to Champion) | Paul's evidence to supply |
| **Expert panel revival** | Re-opening `big5_expert_panel_prereg.md` | CANCELED; A- is FINAL (law 4). Never re-propose |
| **RL envelope** | Building the reinforcement-learning roadmap from the annotated bibliography | Paul's roadmap - do not build uninvited (law 16) |
| **New-data ratifications** | `fec/retiring_members.txt` population; `BP_SRC=aug` ratification; 'CU Tax Status' DEFENSIVE-set membership; gold-label adjudication queues | All standing user flags in code comments/docs |

## 5. The non-negotiables - master list (all 18, with rationale and incident)

These are project law, user-ratified 2026-07-09. Where the repo documents a rule, the citation is given; otherwise the rule is marked "(session-ratified, 2026-07)". Violating one is never a judgment call.

**1. Stance/press classification is Paul's domain.** Never relabel a press/stance item by model judgment; build override mechanisms instead. *Why*: stance labels encode his domain judgment; a model "correction" silently rewrites his ground truth. *Repo*: `.claude/commands/fable-audit.md:7,20` ("stance labels are user-ratified - anomalies are reported as questions, never 'fixed' by relabeling"). *Incident*: the Velazquez CFPB/CCM cells were flagged as suspicious and ratified CORRECT by Paul 2026-07-08 - the flag was wrong, the labels were right (session-ratified, 2026-07).

**2. LLM cost rule (HARD).** Fable (with Opus fallback) ONLY for the 533 per-member narratives; EVERY other LLM step (verification/classification/extraction) uses Haiku 4.5 (`claude-haiku-4-5-20251001`). *Why*: cost control - the narrative layer is the only place the expensive model's prose quality is the product. *Repo*: `fec/b5_narratives.py:131-135` (fable + opus-fallback pattern), `fec/b5_audio_verify.py:71` (Haiku for verification), model id at `fec/big5_llm.py:38`. *Caution*: several older scripts still carry pre-rule defaults (e.g. `fec/member_reference_layer.py:35` hardcodes `claude-fable-5`) - when invoking any LLM step, apply this rule regardless of the script's default (session-ratified, 2026-07).

**3. Port 8801 is Paul's own server; preview/audit servers use 8802.** *Why*: binding 8801 collides with his live dashboard server. *Repo*: `.claude/launch.json` defines `moneyball-ui-audit` on 8802 serving the live tree; `static` on 8801 is his (session-ratified, 2026-07).

**4. The expert gold panel is CANCELED; grade A- is FINAL; never re-propose human raters.** Panel infrastructure stays dormant - its scorer (`fec/b5_panel_score.py`) refuses the look while the prereg is unlocked. *Why*: Paul canceled it explicitly ("augment what we have instead"); re-proposing overrides a recorded user directive. *Repo*: `big5_expert_panel_prereg.md:3-7` (STATUS line documents the cancellation and the only revival path), `README.md:50`. *Incident*: panel built @34bed72 and canceled the same day @3f91332.

**5. Check for Paul's live jobs before running baselines or the chain; run baselines serially.** *Why*: concurrent runs corrupt each other's reads and produce phantom findings. *Incident*: audit run-3's first `audit_full` "failure" was read contention with Paul's own pipeline run finishing at 19:27 (`AUDIT_FINDINGS_2026-07-03.md:16-22`); run-4 deferred its run-through until artifact mtimes quiesced (session-ratified, 2026-07).

**6. NEVER hand-edit or hand-extend a generated JSON artifact.** *Why*: the producer regenerates the artifact and silently clobbers your edit; worse, the producer and artifact then disagree until the next run. *Incident*: the 18th stance category (CU Tax Status) was hand-added to `category_stance.json` on 2026-07-01 but never to the producer's list - the next regeneration silently dropped the category while IMP weights (3.0!) kept expecting it. The fix and the lesson are memorialized in the producer itself: `fec/per_category_stance.py:21-24`. Also `.claude/commands/fable-audit.md:10-11`.

**7. Git worktrees isolate DATA — which makes them the WRONG place to run data-dependent work.** `fec/paths.py:7-8` resolves ROOT to the parent of the imported paths.py unless `MONEYBALL_ROOT` overrides it, so a script run from a worktree targets the worktree's EMPTY data plane: reads die on missing inputs and writes land as throwaway worktree artifacts, not in live. To operate on real data from a worktree set `MONEYBALL_ROOT` to the live tree — and then writes DO hit live, so the old caution stands in force either way: never run `fec/*.py` casually. (Corrected 2026-07-19; this law previously asserted the opposite, and the wrong version was copied into other skills and commit 10a5f97. Verified against `fec/paths.py:7-8`.)

**8. Only `fec/tests/run_tests.py` and `fec/audit_full.py` are safe to run casually.** Import == execution for nearly every `fec/*.py` - most scripts execute their whole body (including artifact writes) at import time; almost none have `__main__` guards. *Why*: "just importing to inspect" has run entire Monte-Carlo loops and overwritten production artifacts. Even `audit_full.py` is only *safe*, not zero-write (it drops `_audit_tmp_*.json` at the live root). Never `python -c "import some_fec_module"` to check a value - Grep the source instead (session-ratified, 2026-07; the module-top-level pattern is visible across `fec/`, e.g. `fec/per_topic_coalition.py` runs its whole MC loop at import).

**9. PERSONA_W=0.30 is user-ratified KEEP.** Do not propose its removal. It reopens ONLY on a failed 3+ rater panel run to Bono & Loomis standards (trained-multi-coder reliability floor alpha ~ .72). *Why*: two null tests against it were scope-mismatched per the source papers (the construct is PROJECTED persona, which disclaims intrinsic-trait criteria; the gold rater was a single untrained coder below the papers' own floor); construct-appropriate validations passed. *Repo*: `fec/receptivity_layer.py:92` (the dial); full ruling in `AUDIT_FINDINGS_2026-07-04.md` (run-4h/4i persona sections). *Incident*: a removal recommendation was drafted and WITHDRAWN after reading the source papers - the auditor, not the dial, was wrong.

**10. Refuted-findings lists in audit reports are binding.** Do not re-flag what a report marks refuted/closed/known-benign. This includes the Judiciary committee-coverage decision (CLOSED by referral evidence, `AUDIT_FINDINGS_2026-07-04.md` run-4o section) and the known-benign registry in `.claude/commands/fable-audit.md:72-82`. *Why*: re-flagging burns Paul's attention on settled questions and erodes trust in real findings. *Incident*: the run-4j literature audit's four verification sub-agents ALL produced at least one false CRITICAL; the overruled-verdicts ledger exists so they stay overruled (`AUDIT_FINDINGS_2026-07-04.md`, agent-calibration ledger).

**11. The electoral_plays fix chain is user-gated.** `build_electoral_plays.py -> build_dashboard_bundle.py -> make_dashboard_html.py` reclassifies members' electoral plays. Never run unprompted even when staleness looks real (audit_full cannot detect this class - its electoral checks are internal-consistency only). *Why*: play classifications are Paul's client-facing calls (session-ratified, 2026-07). *Record*: the 2026-07-09 flag resolved 2026-07-10 - Paul authorized a re-run and the rebuild was byte-identical (content already current; mtime-only flag).

**12. Claim-discipline receipts.** Verify wording against `big5_methods.md` before embedding any validity claim. Never claim "5/5" for the instrument - the real look was **3/5, O/C/E diagonal-dominant** (`big5_methods.md:389-392`). "A passed via audio" is FALSE - audio-A was null twice; audio's real pass was **E + ES vs Pink** (`big5_audio_faithful_prereg.md:58-64`). ES carries a MANDATORY gender-confounded caveat - never "cross-modally validated" unqualified; the +.208 held-out pass stands as history only (`big5_methods.md:423-424, 430-432`). *Why*: these three mis-claims recurred across sessions; the receipts kill the drift. See **moneyball-docs-and-claims** for the full claims ledger.

**13. Never reverse a settled result under conversational pressure.** The ONLY legitimate way a settled result gains a caveat is a LOCKED robustness look with pre-declared consequences. *Why*: results that flip when someone argues hard are not results. *Precedent*: the ES cross-modal +.208 gained its gender-confound caveat exactly this way - a LOCKED robustness prereg (@fd963ab) whose look (@34bf7e4) applied pre-declared consequences; the original RESULT text was annotated, never rewritten (`big5_methods.md:386-388`) (session-ratified, 2026-07).

**14. User-ratified constants change only by Paul's decision, made in Excel or by directive - never silently in code.** The list: pillar weights 30/25/40/5 (typed workbook cells; live value verified in `ranks_python.json` `ab_weights`); `BP_SRC=cosponsor` (`MATHEMATICAL_SPECIFICATION.md:69`); PERS '-'=0.45 Ally parity (spec:36, `fec/moneyball_core.py:138`); DTHRESH=11.25 (`fec/money_response.py:23`); the say-do gate's 3-path A/V/J corroboration (tested in `fec/tests/run_tests.py:95-107`). *Incident*: the W1 flagship-weights bug (press pillar weight silently 0 via stray formula remnants in row 535) moved 318 members' ranks when Paul's chosen spec was restored - weight cells are that load-bearing (`DEEP_AUDIT_MATH_LOGIC_2026-07-02.md:23-38`).

**15. Data deletions from the D2/legacy duplicate ledgers are user-gated.** No dedup DELETE without Paul. *Why*: deletes are irreversible against gitignored data; the ledger (CREC ~299 + legacy ABC/CNN/interview rows) preserves the decision for him. *Repo*: the audit deliberately tolerates the known surplus rather than deleting (the speech exact-dup check in `fec/audit_full.py` allows the user-gated set) (session-ratified, 2026-07).

**16. The RL envelope in the annotated bibliography is Paul's roadmap - do not build it uninvited.** *Why*: it is his stated future direction; building it preempts his sequencing. *Repo*: ratified in the run-4k commit @201a2b9 ("RL envelope = user's roadmap") (session-ratified, 2026-07).

**17. Excel must be CLOSED for any workbook write; COM is retired from the pipeline; the `apply_*` one-shots are dangerous manual tools.** Any openpyxl save PermissionErrors if the workbook is open. There is NO COM step in the chain - the manual COM-era tools still exist (section 1's hazard list) and require Excel closed. *Why/incident*: COM+OneDrive contention produced a PermissionError lock race and a 2.2MB TRUNCATED workbook save on 2026-07-02 - the incident is memorialized in `fec/run_pipeline.py:9-11` and `MATHEMATICAL_SPECIFICATION.md:54-56`.

**18. Standing user-gated decisions (Paul's alone):** the Crapo CCM-cell evidence; the electoral_plays re-run; dedup deletes. Two former entries are DECIDED and merged to main 2026-07-10 - the Vote Smart collection/look (executed under Paul's direction, TIER 5 UNCORROBORATED @e77703c) and the coop_v2 engine promotion (granted, shipped @94f09cf) - see section 4's rows for the record (session-ratified, 2026-07).

## 6. Branch and commit conventions (as practiced in history)

The repo's history began 2026-07-02 (@62a209e) and its commit messages are the primary lab notebook - many carry the only record of measured numbers and verbatim user directives. Conventions observed and to be continued:

- **Branch naming**: each working session gets a `claude/<codename>` branch in a linked git worktree; audit fix lanes use `audit/fixes-<date>`. Merges to main happen in batches (only 6 merge commits exist in 206 total as of 2026-07-09).
- **Worktree trap**: worktree DIRECTORY names do not match their checked-out BRANCH (`git worktree list` is ground truth; a `+` prefix in `git branch -a` = checked out in another worktree - do not touch it, a live session may be on it).
- **Merge debt is the repo's #1 recurring risk** - three separate audits found ratified fixes stranded on unmerged branches while production ran main (S2-01/S2-02 of run-4, `AUDIT_FINDINGS_2026-07-04.md`). Before trusting "main is fixed", run `git cherry main <branch>` on every open branch; `+` lines are patches main lacks. As of 2026-07-10 (afternoon) the debt is CLEARED - every branch is fully merged into main: magical-booth @2ce51c5 (7 HIGH fixes + the 07-08 audit report, now at repo root), musing-swirles @4f7007d (9 parse fixes), clever-elbakyan @02a36ac (Vote Smart ES RESULT + the MS NOW collector leg), compassionate-ellis @5e63c97 (kill-ledger prereg records), with beautiful-hermann and audit/fixes-2026-07-10 merged earlier the same day. Post-merge verification: kernel 37/37, chain 9.8 min, ranks md5 UNCHANGED, audit 71/71. Re-verify anytime: `git log main..<branch> --oneline` must be empty for every branch. Historical stranded-work table: `moneyball-failure-archaeology` section 4.
- **No `git revert`, ever** (zero exist in history). Rollback = the env-dial revert switch shipped with the change (e.g. `BAKKER_XCUE=0`). Dead code is retired by `git mv` into `fec/attic/` (37 files as of 2026-07-09), never deleted - and check consumers first: `attic/audit.py` had to be restored because `audit_full` shells out to it.
- **Never rebase or squash.** Look-gate scripts literally match newline-anchored `## RESULT` headings in committed prereg text (`fec/b5_n_matrix.py:357`); history rewrites destroy the audit trail and can arm or disarm gates.
- **Commit-message vocabulary** (use these exact terms so future greps work): `... prereg LOCKED (pre-look)` for a lock commit; `LOOK RESULTS: ...` with PASS/MISS counts for the outcome commit (misses are committed permanently, never reverted); `RETIRED WITHOUT A LOOK` + `DATA-GATED`/`DIAGNOSTIC-GATED` for battery-refused retirements; `user-ratified` when Paul approved a value/decision (quote him verbatim where possible); `user-gated` for actions awaiting him; severity tags `S1/S2/S3` in fix-lane commits; audit work units as `Run-<N><letter>:` subjects. Verify any of these with `git log --all --oneline --grep="<term>"`.
- **Commit bodies carry the verification receipts**: kernel-test count, audit count, rank-delta result ("ranks 0/533"), and revert instructions for anything shipped. One fix per commit on fix lanes.
- **Reports are append-only**: a same-day second audit report gets a `_RUN2` suffix rather than clobbering the first.

## 7. When a change is ambiguous - who decides

Walk this ladder; the first YES decides:

1. **Does it change a number, label, or classification Paul ratified** (sections 4-5)? -> Paul decides. Prepare evidence, use a `.candidate` artifact or default-off dial, present, stop.
2. **Is it a statistical claim about validity/measurement?** -> The prereg discipline decides (load **moneyball-research-methodology**). No peeking at the answer while designing the test.
3. **Does it change any engine output** (ranks, allocations, flip probabilities, cascade spreads)? -> The verification protocol decides: run it; a zero delta means class-1 refactor territory (proceed, commit with receipts); a nonzero delta means every mover must be explained by the intended mechanism - and if the mechanism itself embodies a judgment call (weights, thresholds, category membership), escalate to rung 1.
4. **Is it display-only or docs-only?** -> Proceed under classes 5-6, keeping JS mirrors in lockstep and claims within law 12.
5. **Still unsure which class it is?** -> Treat it as the STRICTER class. The default posture, proven repeatedly in this repo's history: build the mechanism fully, gate the activation (candidate suffix / env dial defaulting to current behavior / LOCKED prereg), and hand Paul a one-decision switch. That converts "should I?" into "here it is, armed and off - your call."

If Paul is unavailable and the change cannot wait (e.g. a live corruption): fix the minimum, document it as an incident in a dated report, and leave the judgment-bearing parts gated. A wrong number shipped silently is worse than a delay.

## Provenance and maintenance

Written 2026-07-09 against the live tree at main @88a7048 (authoring worktree `claude/nifty-cray-f6d053`). Volatile facts and how to re-verify each (all read-only; quote the paths):

```powershell
cd "C:\Users\pgoff\OneDrive\Desktop\Melange Systems"   # or any worktree of this repo

# Kernel test count (84 as of 2026-07-19) and its exit-code behavior
Select-String -Path "fec\tests\run_tests.py" -Pattern "KERNEL TESTS|sys.exit"
# Audit check count (136 as of 2026-07-19) + nonzero-on-failure behavior + expected tail text
Select-String -Path "fec\audit_full.py" -Pattern "FULL-BODY AUDIT|ALL MODULES CLEAN"
Select-String -Path ".claude\commands\fable-audit.md" -Pattern "136 checks|ALL MODULES CLEAN"
# 36-step chain order as of 2026-07-19 and --from/--recalc flags
Select-String -Path "fec\run_pipeline.py" -Pattern "CHAIN=|--from|RETIRED"
# The protocol as documented in the docs of record
Select-String -Path "README.md","MATHEMATICAL_SPECIFICATION.md","fec\tests\run_tests.py" -Pattern "zero rank delta"
# paths.py root resolution and env override (law 7)
Select-String -Path "fec\paths.py" -Pattern "MONEYBALL_ROOT"
# ranks_python.json shape + live pillar weights (law 14) - reads the LIVE artifact
Select-String -Path "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\ranks_python.json" -Pattern "ab_weights.{0,60}"
# .candidate convention still live
git ls-files | Select-String "candidate"
# Gating vocabulary still in commit history
git log --all --oneline --grep="RETIRED WITHOUT A LOOK"; git log --all --oneline --grep="LOOK RESULTS"
# Look-gate enforcement (STATUS: LOCKED / RESULT heading / fingerprint refusal)
Select-String -Path "fec\b5_n_matrix.py" -Pattern "STATUS: LOCKED|RESULT-N|REFUSED"
# 18th-category hand-edit incident memorial (law 6)
Select-String -Path "fec\per_category_stance.py" -Pattern "by hand"
# Destructive-script guards + apply_* inventory (law 17)
Select-String -Path "fec\sync_stance_clean.py" -Pattern "sys.exit"; Get-ChildItem "fec\apply_*.py" | Select-Object Name
# COM-truncation incident memorial (law 17)
Select-String -Path "fec\run_pipeline.py" -Pattern "truncated"
# Panel canceled / A- final (law 4)
Get-Content "big5_expert_panel_prereg.md" -TotalCount 8
# Claim receipts (law 12)
Select-String -Path "big5_methods.md" -Pattern "3/5|CLOSED PERMANENTLY|no clean independent validation"
# Unmerged fix branches (merge-debt check - this list should shrink over time)
git branch -a | Select-String "claude/|audit/"; git cherry main claude/magical-booth-f272da
# Ports (law 3)
Get-Content ".claude\launch.json"
# LLM cost rule code anchors (law 2)
Select-String -Path "fec\b5_narratives.py","fec\big5_llm.py" -Pattern "claude-fable-5|claude-haiku-4-5"
```

Counts that WILL drift (re-verify, don't trust this file): kernel tests 84, audit checks 136, and chain steps 36 as of 2026-07-19, plus the attic file count, the unmerged-branch list, and every dated state in sections 4 and 6. The rules themselves (sections 3, 5, 7) change only by Paul's directive.
