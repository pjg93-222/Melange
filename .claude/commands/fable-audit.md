# Moneyball — Extensive Audit + True Run-Through (give this to Fable)

You are auditing a live, calibrated Python→Excel legislative-influence pipeline at
`C:\Users\pgoff\OneDrive\Desktop\Melange Systems` (git repo, branch main). Unlike the read-only
audit variant, this mission INCLUDES a true end-to-end execution of the pipeline with hard gates.
Deliverable = `AUDIT_FINDINGS_<today>.md` at repo root + a clean gate table. Constants and stance
labels are user-ratified — anomalies are reported as questions, never "fixed" by relabeling.

## Ground rules
1. Data artifacts (*.json/csv/xlsx/db) are gitignored → regenerable via the pipeline but NOT via
   git. Never hand-edit one. `Draft Systems` (separate folder) is irreplaceable raw data — out of
   scope entirely, do not even scan it. `backups/` is the recovery layer — read-only.
2. The workbook `Moneyball Main Version - Blended.xlsx` may be OPEN in Excel → any openpyxl save
   will PermissionError. If that happens: record it, skip that step, continue — never kill Excel,
   never use COM (COM was retired in phase 2; there is no recalc step anywhere).
3. Never change calibrated constants (IMP 18-cat, PERS '—'=0.45, SGATE ladder, DTHRESH 11.25,
   LOSSFRAME 1.10, the TWO cpf physics — cpf_diffusion vs cpf_pressure are INTENTIONALLY distinct,
   never unify). Never set the calibration env dials during verification runs (SEED/MC/MAXSHIFT/
   DTHRESH/PERS_NONE/RT_W/SOCIAL_SHRINK/BP_SRC/...) — defaults ARE the ratified state.
4. Press/stance classification is the user's domain (standing rule). Weights are the user's domain.
5. Transform scripts go in the session scratchpad as FILES — bash heredocs are BANNED here (they
   have twice injected control characters/escape damage into this repo).
6. Read files before editing them. Prefer Grep to whole-file reads. One pass per file — write
   conclusions into the findings file immediately.

## Phase 0 — Orientation (minutes)
INDEX.md → README.md → MATHEMATICAL_SPECIFICATION.md (the law-of-the-system table + conventions)
→ `git log --oneline -15` → fec/run_pipeline.py CHAIN (ground-truth execution order)
→ fec/moneyball_core.py (shared kernel). Create the findings file immediately; append as you go.

## Phase 1 — Static baselines (record all three in the report header)
- `python fec/tests/run_tests.py`  → expect **KERNEL TESTS — 84 passed, 0 FAILED** (as of 2026-07-19;
  the count only grows — trust the run output)
- py_compile sweep of fec/*.py (skip attic/; use a scratchpad temp .pyc target, NOT os.devnull —
  invalid on Windows) → expect all clean
- `python fec/audit/audit_full.py` → expect **FULL-BODY AUDIT — 136 passed, 0 FAILED**, then **ALL MODULES CLEAN** (136 checks as of 2026-07-19;
  the count grows as guards are added — any FAILED is the finding, not a count mismatch) (view-stale SKIP notes in
  legacy_workbook_audit.py's A2/A3 are NORMAL when the workbook cache is dead — see Known-benign below)
A failing baseline is finding #1 — diagnose it before anything else.

## Phase 2 — TRUE RUN-THROUGH (the core of this mission)
1. Pre-state capture (to scratchpad): copy `ranks_python.json`; md5 of budget_frontier*.json,
   optimize_result.json, per_topic_*.json, salience_advisory.json, dashboard_data.json.
2. `python fec/run_pipeline.py` (background; 6–19 min depending on view-cache state; the chain ends
   with audit_full).
3. GATES — all must hold:
   a. every chain step prints OK; exit 0
   b. audit tail = ALL MODULES CLEAN
   c. rank delta: new ranks_python.json vs pre-state = **ZERO** for all 533 members. ANY delta must
      be explained by a real input change (new collector data, user dial edit) or the
      `bipartisan.json` two-run convergence (see Known-benign), or it is an S1 finding.
   d. engine artifacts: identical hashes vs pre-state UNLESS (c)'s explanation applies.
4. Determinism spot-check: run fec/engine/budget_frontier.py twice with TOPIC=Interchange and FRONTIER_OUT
   pointed at two scratchpad temp files → hashes must be identical.

## Phase 3 — Deep sweeps (priority order; cut from the bottom if budget tightens)
P1 artifact contracts: README module table → for each producer→artifact→consumer, Grep the
   consumer's key reads vs the producer's dump keys; flag .get(...,default) that silently zeroes a
   member/category; flag any NEW non-atomic write (everything should use MC.dump_atomic).
P2 silent-failure surfaces: bare except; try/except-FileNotFoundError fallbacks that could mask a
   MISSING input file (receptivity's per-member neutral fallback is BY DESIGN; the whole-file-missing
   guards exist — verify they still print).
P3 kernel drift: residual copies of cpf/_sm/PERS/IMP/BLOCKCAT/SGATE outside moneyball_core
   (expect NONE except the hard-guarded sync_stance_clean.py); MC-module vs MC-dial alias confusion
   (cascade engines use MBC for the module because MC is their Monte-Carlo count).
P4 spec-vs-code: MATHEMATICAL_SPECIFICATION tables vs live code, both directions; code presumed
   authoritative; reconcile NEITHER side yourself — report.
P5 UI smoke (preview tools): serve the repo, load cu-member-desk.html → ranked rows render; open
   the #1 member → staff directory cards render (gold/star/notes controls present); switch to the
   In-contact panel; zero console errors. Load Moneyball Dashboard.html → renders, zero console
   errors. Do NOT leave test state in localStorage that alters user data — preview browser only.

## Known-benign registry (do NOT re-flag; context in git log + memory)
- View-stale workbook: after any pipeline run, formula cells (Blended names/O/E/F, R&A col C,
  normalized cells) read None until the user opens Excel (fullCalcOnLoad self-heal). compute_pillars
  falls back to pillar_inputs_snapshot.json — its "(view cache dead -> snapshot)" print is normal.
- Two-run convergence: `bipartisan.json` is the ONLY feedback edge. It is produced late in the chain
  but read by earlier engine steps, so a run after a stance/network change legitimately shifts engine
  outputs once more on the NEXT run. Col-G has been a pure output since @f17dc2c
  (`fec/stance/per_category_stance.py:9-13`); accepting a "col-G convergence" story is exactly the wrong
  excuse that masked the S2-04 limit cycle.
- 4 unmatched staffer offices = AS/GU/VI territorial delegates (not in the 533 roster) — correct.
- Big-Five O-trait party-validation is REVERSED (documented low-validity; engine weight ~0).
- `--recalc` prints a retired-notice — intended.
- per_topic budgets ($2M each) are per-issue diagnostics, NOT additive money.
- write-only diagnostics artifacts list in README §Diagnostics-only.

## Findings format
[S1|S2|S3-nn] file:line — one-line defect. Evidence: quoted line(s). Impact: which artifact/rank
could go wrong. Remedy: minimal suggested diff as text. S1 = corrupts artifacts / crashes chain /
unexplained rank delta. S2 = silent wrong-number risk. S3 = hygiene. No auth/SQL/CORS surface
exists here — don't hunt for one.

## Fix lane (only after the report is complete)
Provably-inert fixes only (unused imports, comment/docstring rot) unless the user is present to
ratify more: branch `audit/fixes-<date>` → fix → rerun kernel tests (84 as of 2026-07-19; count only grows) → one commit
per fix. Output-affecting fixes stay report-only UNLESS you re-run the full pipeline + zero-delta
gate + audit clean afterwards — that is the verification protocol; use it.

## Finish
Final message: gate table (baselines, run-through gates a–d, determinism), counts by severity,
top 5 findings in plain sentences, report path, branch name if the fix lane ran. Update the
moneyball memory files with anything a future session must know. Then stop.
