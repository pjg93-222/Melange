---
name: moneyball-debugging-playbook
description: Symptom-to-fix triage for live Moneyball failures. Load this when something is BROKEN or LOOKS WRONG right now - unexpected rank changes, artifact hash/byte drift, a failing audit_full check, PermissionError writing the workbook, UnicodeEncodeError or garbled text (mojibake), a pipeline step dying with only a terse last line, collector rows missing dates, stale derived artifacts, OneDrive locks, the dashboard JS disagreeing with Python, engines silently going neutral, or a b5_* look script refusing to run. Covers triage and discriminating experiments only. Does NOT cover the history of past investigations (moneyball-failure-archaeology), how to run things day-to-day (moneyball-run-and-operate), what counts as evidence (moneyball-validation-and-qa), adding diagnostics (moneyball-diagnostics-and-tooling), or the change rules themselves (moneyball-change-control).
---

# Moneyball debugging playbook

This is the triage manual for the Moneyball congressional-influence pipeline: a chain of Python scripts under `fec/` that turns congressional data into per-member persuasion rankings, JSON artifacts, an Excel workbook view, and HTML dashboards. Most defects here are "silent wrong-number" failures - the pipeline prints success while producing subtly wrong output - so every section below pairs a symptom with a **discriminating experiment**: a cheap, safe command that separates the likely causes before you touch anything. Each row is backed by a real incident from the dated audit reports at the repo root (`AUDIT_FINDINGS_*.md`), cited so you can read the full story. Run the Step 0 live-jobs check before ANY experiment; several "bugs" in this project's history were another process's writes.

## When NOT to use this skill

- You want the full history of an incident, or to know whether a finding was already refuted/closed: **moneyball-failure-archaeology** (its refuted/do-not-reflag lists are binding).
- You want to run the pipeline, collectors, or dashboards normally: **moneyball-run-and-operate**.
- You are deciding whether a change is allowed, or what "user-gated" means: **moneyball-change-control**.
- You want to add a test or audit check after fixing: **moneyball-validation-and-qa**.
- You want measurement tools (sensitivity sweeps, stability checks): **moneyball-diagnostics-and-tooling**.
- A prereg/look question that is about research process, not a stuck script: **moneyball-research-methodology**.

## Quick reference

**Two facts that shape every experiment here:**

1. **Import == execution.** Nearly every `fec/*.py` runs its whole body at module top level and can write artifacts to its resolved data plane. Only `fec/tests/run_tests.py` and `fec/audit_full.py` are safe to run casually (and even audit_full drops two `_audit_tmp_*.json` files at the resolved root). Never import a fec script "to inspect it". (session-ratified, 2026-07)
2. **Git worktrees isolate DATA - which makes them the WRONG place to run data-dependent work.** `fec/paths.py:7-8` defaults ROOT to the parent of the imported paths.py; a script run from a worktree targets that worktree's EMPTY data plane: reads die on missing inputs and writes land as throwaway worktree artifacts. Run data-dependent work from the live tree, or set `MONEYBALL_ROOT` to it - and then writes DO hit live. Never run `fec/*.py` casually. (Corrected 2026-07-19; the previous version asserted the opposite. Verified against `fec/paths.py:7-8`.)

All commands below assume PowerShell with the repo root as cwd (`cd` there first; quote paths - they contain spaces). "LIVE root" means `C:\Users\pgoff\OneDrive\Desktop\Melange Systems`.

| # | Symptom | First suspect | Section |
|---|---------|---------------|---------|
| 0 | Anything at all | Paul's own live job, not your bug | Step 0 |
| 1 | Ranks moved unexpectedly | Real input change, stale authority, or unmerged branch | 1 |
| 2 | Artifact hashes differ, no input changed | Real regression (post-idempotency) or another process's writes | 2 |
| 3 | audit_full prints FAIL | Read the tail, check the known/accepted list first | 3 |
| 4 | PermissionError saving the workbook | Excel is open | 4 |
| 5 | UnicodeEncodeError / garbled text | cp1252 console, or BOM-CSV read without utf-8-sig | 5 |
| 6 | Chain step dies, one cryptic line | run_pipeline only echoes the last stdout line; rerun standalone | 6 |
| 7 | Collector rows have no dates | Date extraction never covered that leg's URL shape | 7 |
| 8 | A derived artifact disagrees with its inputs | Producer not re-run (mtime ordering) | 8 |
| 9 | Random file locks / truncation / wrong mtimes | OneDrive | 9 |
| 10 | Dashboard shows different numbers than Python | JS mirror drift (tpl has ZERO audit coverage) | 10 |
| 11 | Engine output flattened / everyone looks the same | Missing artifact -> silent neutral fallback | 11 |
| 12 | A `b5_*` script prints "LOOK REFUSED" | That is the gate WORKING - almost never a bug | 12 |

---

## Step 0 - Is it my bug, or a live user job?

Paul runs collectors, pipelines, and batch jobs on this machine at all hours. Before treating any anomaly as a defect, check for his processes and for artifacts still being written. (session-ratified, 2026-07; incidents: run-3's first audit_full "failure" was read contention with Paul's own pipeline finishing at 19:27, `AUDIT_FINDINGS_2026-07-03.md:16-22`; run-4 deferred its run-through until mtimes quiesced, `AUDIT_FINDINGS_2026-07-04.md:11-14`.)

```powershell
# 1. Any python processes alive that you did not start?
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Select-Object ProcessId,CreationDate,CommandLine

# 2. Are live-root artifacts still being written? (fresh mtimes = a job is mid-run)
Get-ChildItem "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\*.json" |
  Sort-Object LastWriteTime -Descending | Select-Object -First 15 Name,LastWriteTime
```

If anything is running or mtimes are minutes-fresh: **wait until they quiesce, then re-check the symptom**. Run your own baselines serially, never concurrently with his work. Only proceed to sections 1-12 once the tree is quiet.

---

## 1. Unexpected rank delta

**Symptom:** `ranks_python.json` (the rank authority - the one file engines read scores from) differs from what you expected, or `compute_pillars.py` (audit mode) exits 1.

**The incident behind it:** three separate audits found ratified fixes stranded on unmerged branches while the scheduled job ran `main` - the ranks were "wrong" because production was running old code (`AUDIT_FINDINGS_2026-07-02_RUN2.md:129`; `AUDIT_FINDINGS_2026-07-04.md`, S2-01/S2-02, lines 367-394). Version control, not math, is the recurring top cause.

**Discriminate, in order:**

```powershell
# (a) Is the authority merely stale vs current inputs? Read-only parity check, exit 1 on drift.
#     Prints one of: "PARITY: CLEAN" / "PARITY: AUTHORITY STALE ... Rerun the pipeline." /
#     "PARITY: DRIFT DETECTED" (workbook formula vs spec math) / "PARITY: AUTHORITY MISSING".
python "fec\compute_pillars.py"

# (b) Is production running the code you think it is?
git status; git log --oneline -5; git branch -a

# (c) Diff two rank files member-by-member (point the second path at your saved baseline copy):
python -c "import json;a=json.load(open(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\ranks_python.json'))['rank'];b=json.load(open(r'<your-baseline>\ranks_python.json'))['rank'];d=[m for m in a if a[m]!=b.get(m)];print(len(d),'moved:',d[:10])"
```

**Interpretation:**
- `AUTHORITY STALE` -> an input (stance matrix, press values, receptivity) changed since the last `compute_pillars --write`. That is an input-driven delta, not a bug - identify WHICH input via section 2's purity method.
- `DRIFT DETECTED` -> a workbook formula no longer matches the spec math. Do not edit the workbook; escalate per moneyball-change-control.
- One extra run's worth of movement after a stance/network change is **two-run convergence** (`bipartisan.json` - the ONLY remaining feedback edge - is written late in the chain and feeds the NEXT run) - expected, settles at a fixed point. Col G is NOT part of this: it has been a pure output since @f17dc2c (`fec/per_category_stance.py:9-13`); do not accept a "col-G convergence" explanation - that superseded excuse is what masked the S2-04 limit cycle. Verified benign in `AUDIT_FINDINGS_2026-07-03.md` (known-benign registry, lines 129-132).
- Real unexplained deltas are severity S1. Stop and report; do not "fix forward".

---

## 2. Artifact hash/byte drift on a no-input-change run

**Symptom:** you re-ran the chain (or one engine) with no input change and an engine artifact's bytes/MD5 changed.

**The incident behind it:** the col-G limit cycle (S2-04) - ~39 stance-tier cells flipped on EVERY consecutive run with zero input change, because col G was both an output and the next run's input; engine hashes alternated A->B->A forever (`AUDIT_FINDINGS_2026-07-02_RUN2.md:77-87`). Fixed at commit `f17dc2c`; the pipeline was then proven idempotent (12/12 byte-identical double-run). **Consequence: post-fix, any no-input hash drift is a REAL regression** (`AUDIT_FINDINGS_2026-07-02_RUN2.md:87`), after you rule out (Step 0) another process's writes.

**Discriminate with the input-purity test** (codified in `AUDIT_FINDINGS_2026-07-03.md:38-44`): re-run the deterministic engine against current on-disk inputs with output redirected to a temp path (`FRONTIER_OUT` for `budget_frontier.py`, `OPT_OUT` for `optimize.py` - never clobber production), then byte-compare MD5s. Byte-match -> the drift was input-driven; find the changed input by mtime (section 8). Mismatch -> a real behavioral change, or nondeterminism (re-run the temp probe twice: differing probes = an unseeded RNG or a set SEED/MC dial). NEVER run probes with calibration env dials set - the defaults ARE the ratified state. **The full recipe (commands, interpretation rules, worked example) is owned by `moneyball-proof-and-analysis-toolkit` Recipe 5 - use that.**

---

## 3. An audit_full check is failing

**How to read it:** `python "fec\audit_full.py"` prints one line per check - `  OK   <name>` or `FAIL  <name> :: <detail>` (detail only on failure) - then a tail: `FULL-BODY AUDIT - N passed, N FAILED`, followed by either `  ALL MODULES CLEAN.` or `  FAILURES: [<names>]`.

**Trap: exit-code behavior differs by script.** `audit_full.py` exits 1 when any check fails and 0 when clean; `audit.py` and `audit_frontier.py` have no `sys.exit` calls and still always exit 0. `run_pipeline.py` therefore registers a failed `audit_full.py` step and aborts. Always gate on the tail text `ALL MODULES CLEAN.` as belt-and-braces because older automation may assume exit 0. (`fec/tests/run_tests.py` also exits 1 on failure.) (Corrected 2026-07-19; verified against `fec/audit_full.py:1198-1202` and zero `sys.exit` hits in both sub-audits.)

**Known/accepted behaviors - NOT findings (as of 2026-07-09):**

| Output | Meaning |
|---|---|
| `A2 allocation: SKIP (view cache stale...)` / `A3 funded: SKIP` | Normal between an openpyxl save and the user's next Excel open. Recorded as passes (`fec/audit.py:18-24`). |
| compute_pillars prints a snapshot-fallback / "view STALE (expected...)" line | Same view-cache contract; normal. |
| Check count higher than a doc says | The suite grows nearly every session (84 kernel / 136 audit as of 2026-07-19; count only grows - trust the run output). Any FAILED is the finding; a higher count is not. |
| `_audit_tmp_optimize.json` / `_audit_tmp_frontier.json` appear at the LIVE root | audit_full's own redirected probe outputs; never cleaned up; harmless. |
| `gate key missing - producer predates 2026-07-07 landing` FAIL | `category_stance.json` was regenerated by pre-say-do-gate code. Re-run the chain from `per_category_stance` with current main. |
| A frontier sub-audit FAIL tied to `electoral_plays.json` | **Stale plays are INVISIBLE to the audit** (see section 8) - audit_full's electoral checks are internal-consistency only (`fec/audit_full.py:39-44`), and the recorded "1 pre-existing electoral_plays fail" predates the 2026-07-10 magical-booth merge (its V-1 freshness check covers vote_category_lean.json, NOT electoral_plays; the post-merge audit passes 71/71). The 2026-07-09 mtime flag itself resolved 2026-07-10: an authorized rebuild was byte-identical — content was already current. So a frontier FAIL here is likely NEW - investigate rather than assume staleness. Either way the rebuild is **user-gated** - report, do not run it. |
| `integrity (22) sub-audit clean` FAIL with passed-count below floor | A check silently vanished from a sub-audit - that count floor (>=22 / >=11 at `fec/audit_full.py:16-18`) exists precisely to catch this (S3-03, commit `c90a530`). Find the removed/skipped check. |

**Discriminate:** re-run the owning sub-audit standalone to isolate (`python "fec\audit.py"` for A/B/C-prefixed workbook checks, `python "fec\audit_frontier.py"` for frontier checks), then open `fec/audit_full.py`, find the `ck('<name>', ...)` line, and read what condition actually failed. One name = one call site. Before declaring a new finding, check the refuted/known-benign lists in **moneyball-failure-archaeology** - re-flagging a closed finding is a protocol violation.

---

## 4. PermissionError writing the workbook

**Symptom:** any openpyxl `wb.save()` raises `PermissionError: [Errno 13]` on `Moneyball Main Version - Blended.xlsx` - typically at chain entry 15 as of 2026-07-19 (`sync_stance_g.py`).

**Cause:** Excel has the file open. Excel must be CLOSED for any workbook write. (session-ratified, 2026-07; documented at `.claude/commands/fable-audit.md` and `fec/run_pipeline.py:9-11` - the retired COM era also produced a lock race and a 2.2 MB truncated save from COM+OneDrive contention.)

**Fix / procedure:**
1. Do NOT kill Excel. Ask Paul to close it (unsaved dial edits are his).
2. Record the error and re-run from the failed step: `python "fec\run_pipeline.py" --from sync_stance_g`.
3. If the workbook must stay open (Paul working), use the ratified dashboard fallback that skips ALL workbook-writing steps: `python "fec\run_pipeline.py" --from per_topic_flip` (this is exactly what `weekly_refresh.py:73-80` does on a locked workbook; user-ratified 2026-07-03). The col-G view stays stale until the next unlocked run - that is the standard self-heal contract, not damage.
4. Related incident: an in-place CSV rewrite once lost 400 paid labels to this same error; `api_prelabel_tweets.py` grew its sidecar + `--merge` design as the fix (`fec/api_prelabel_tweets.py:8-13`). If a script rewrites a file Excel might hold, close Excel first.

The `fec/apply_*` one-shots drive Excel COM and are dangerous manual tools - never run them casually, and never as a "fix" for a lock error. (session-ratified, 2026-07)

---

## 5. UnicodeEncodeError / mojibake

**Symptom A - crash:** `UnicodeEncodeError: 'charmap' codec can't encode character...` when a script prints. The Windows console is cp1252; any member name or smart quote outside cp1252 kills a bare `print`.

**Fix A:** every fec script carries this boilerplate near the top (121 of the fec `*.py` files as of 2026-07-09) - a new script must too:

```python
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
```

If you cannot edit the script, set `$env:PYTHONIOENCODING='utf-8'` for the session instead.

**Symptom B - garbled text (mojibake), e.g. `â€™` or `ï»¿` in output/CSVs:** bytes decoded with the wrong charset. Known cases:
- **CSV starts with `ï»¿` / first column name is corrupted:** the file has a UTF-8 BOM (byte-order mark). Read it with `encoding='utf-8-sig'` (BOM-tolerant), which 33 fec files already use for adjudication queues and Quorum CSVs. Excel writes BOMs; plain `utf-8` reads keep the BOM glued to the first cell.
- **U+FFFD boxes in old Hewitt interview quotes:** known-cosmetic, deliberately NOT fixed (a latin-1 fallback would touch every collector leg) - `AUDIT_FINDINGS_2026-07-06.md:87-89`. Do not re-flag.
- **Workbook `Press Release Articles` sheet mojibake:** that sheet is written by the external Draft-R press pipeline (no fec writer exists - verified by grep). Not fixable from this repo; and press content is Paul's domain anyway.

**Discriminate:** find where the bad bytes ENTERED. Hexdump the first bytes of the suspect file:

```powershell
python -c "print(open(r'<suspect-file>','rb').read(8))"   # b'\xef\xbb\xbf...' = UTF-8 BOM
```

`Ã©`-style double-encoding means a utf-8 file was decoded as cp1252/latin-1 somewhere upstream; fix the READ, never re-encode the data in place.

---

## 6. A pipeline step failed with only a terse last line

**Symptom:** `run_pipeline.py` prints `  <script>  !!  <seconds>  <one line>` and exits.

**What the runner actually shows** (`fec/run_pipeline.py:172-191`): per step it echoes only the LAST stdout line (90 chars); on nonzero return code it prints the last **800 chars of stdout and of stderr**, then returns 1. There is no logging module anywhere in `fec/` - everything is `print`, and scripts follow an implicit "final summary line" contract, which is why the one echoed line is usually meaningful (`wrote N ...`, `PARITY: CLEAN`, a `!!` guard).

**Discriminate:** re-run the failing step standalone to get FULL output:

```powershell
python "fec\<failing_script>.py"    # plus its args as shown in the 36-entry CHAIN list as of 2026-07-19, run_pipeline.py:25-67
```

Caveats:
- Re-running a chain step re-executes its writes against the resolved data tree - acceptable for a step that already ran and failed, but check Step 0 first.
- Stdout **block-buffers when piped**: if you redirect a long-running script's output to a file, prints appear in bursts (collectors carry `flush=True` on progress prints for exactly this reason - 26 sites in `fetch_interviews.py`). An apparently silent process is not necessarily hung; check whether its artifacts/DB rows are still growing before killing it.
- `--from <prefix>` now rejects unknown or ambiguous targets with `parser.error` (exit 2); it no longer fake-completes a typo. Use one exact/case-sensitive script name or a unique prefix, and note that `budget_frontier` is ambiguous because the script appears twice (`fec/run_pipeline.py:145-165`). (Corrected 2026-07-19; verified against the current `start_index()` implementation.)
- A failed `audit_full.py` step returns 1, prints `!!`, and aborts the chain; still gate on the tail text `ALL MODULES CLEAN.` (section 3's exit-code trap).

---

## 7. Collector rows missing dates

**Symptom:** rows in `social_media.db` (`speeches` table) have NULL/empty `date`, or a whole collector leg's rows are dateless.

**The incident behind it (S2-01, 2026-07-06):** two brand-new interview legs stored **100% of their rows dateless** - Hewitt 559/559 (its date map hardcoded sitemaps 1-4) and Fox 488/488 (dates were taken from URL slugs, which mostly carry none). A direct-fetch smoke test masked a second hole: the Hewitt walker enumerated ONLY a historical archive page (all posts 2011-14), so 2026 content was invisible (S2-02). Fixed at commit `962959d` with full sitemap-index enumeration plus a JSON-LD `datePublished` fallback (regex now at `fec/fetch_interviews.py:343,373,507`) and a scoped backfill to 0 dateless rows (`AUDIT_FINDINGS_2026-07-06.md:49-50,134-147`).

**Discriminate - count dateless rows per source (read-only):**

```powershell
python -c "import sqlite3;c=sqlite3.connect(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\social_media.db');[print(r) for r in c.execute(\"SELECT source, SUM(CASE WHEN date IS NULL OR date='' THEN 1 ELSE 0 END) AS dateless, COUNT(*) FROM speeches GROUP BY source\")]"
```

**Interpretation and fix:**
- A cluster of dateless rows from ONE source = that leg's date-extraction path never covered a URL/page shape. Fix the extractor (add a JSON-LD `datePublished` fallback like the existing ones), then backfill scoped to that leg - never blanket-update.
- **Lesson that generalizes:** smoke-test through the SAME code path production uses (enumeration -> fetch -> store), not a direct fetch of a known URL - the direct fetch is what masked S2-02.
- Do not DELETE anything: duplicate/garbage-row removal is user-gated (the D2 ledger). Dates are metadata repair; row deletion is Paul's call. (session-ratified, 2026-07)

---

## 8. Stale derived artifacts (producer not re-run)

**Symptom:** a derived artifact contradicts its inputs - e.g. the dashboard shows a play/label inconsistent with the member's current stance tier.

**The incident behind it:** the Frank Lucas "defend" glitch - 47 members' overall stance tiers moved in the 2026-07-08 refresh, but `build_electoral_plays.py` was never re-run, so `electoral_plays.json` kept plays computed from the OLD tiers (Lucas moved Ally -> Highly-Persuadable, so his 'defend' should be 'none'). audit_full cannot catch this class: its electoral-plays checks compare `play` against the `overall` stored INSIDE THE SAME artifact (`fec/audit_full.py:39-44`), so an internally-consistent-but-stale file passes. **The fix chain (`build_electoral_plays.py` -> `build_dashboard_bundle.py` -> `make_dashboard_html.py`) reclassifies ~47 members and is USER-GATED - never run it unprompted, even though the staleness is real.** (session-ratified, 2026-07; the 2026-07-09 episode resolved 2026-07-10 — Paul authorized the re-run and the rebuild was byte-identical: the reclassification had already landed in an earlier regeneration, leaving an mtime-only flag)

**Discriminate - mtime ordering.** A derived artifact older than any of its inputs is presumptively stale:

```powershell
Get-ChildItem "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\electoral_plays.json",
              "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\category_stance.json",
              "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\ranks_python.json" |
  Select-Object Name,LastWriteTime
```

Then confirm substantively: spot-check that a value stored in the derived artifact matches the current input (e.g. compare a member's `overall` in `electoral_plays.json` against the same member's tier derived from `category_stance.json`).

**General rule:** the canonical chain (`run_pipeline.py`, 36 entries as of 2026-07-19; `CHAIN` at lines 25-67) exists because hand-typed chains kept forgetting passes (the `--electoral` frontier pass was the historically forgotten one). Anything produced OUTSIDE the chain (`big5_traits`, collector-derived layers) can fossilize; `lt_priming.json` was moved INTO the chain in 2026-07-04 for exactly this reason. If you find a stale out-of-chain artifact: report it with the mtime evidence; whether to re-run its producer may be gated (check moneyball-change-control).

---

## 9. OneDrive file locks, sync lag, truncation, mtime weirdness

The live tree sits inside OneDrive, which is actively hostile to this pipeline. Real incidents:
- An Excel-save/OneDrive collision **truncated the master workbook** mid-fix-application; restored from `backups/` (`DEEP_AUDIT_MATH_LOGIC_2026-07-02.md:10`).
- A COM+OneDrive contention produced a **2.2 MB truncated save** (retired the COM recalc path entirely - `fec/run_pipeline.py:9-11`).
- OneDrive **rewrites mtimes** ~11 microseconds apart on old files, destroying real chronology - which breaks any newest-by-mtime file selection (the AUG network xlsx picker is the flagged case; on-branch report, read it with `git show claude/magical-booth-f272da:AUDIT_FINDINGS_2026-07-08_NETWORK_VOTE_CYCLE.md`).

**Defenses already in place - do not re-invent:** all JSON artifact writes go through `MC.dump_atomic` (temp sibling + `os.replace`, atomic on NTFS - `fec/moneyball_core.py:88-101`), so artifacts are either old or new, never truncated. Workbook writers back up first (`backups/` convention). `paths.py`'s docstring notes that escaping OneDrive entirely is a one-variable change (`MONEYBALL_ROOT`) - but relocating the live tree is Paul's decision, not a debugging move.

**Triage:**
- Sporadic `PermissionError` on a file Excel does NOT hold -> OneDrive sync had it; wait and retry once. Repeated -> check the OneDrive tray icon for a sync backlog.
- A truncated/unparseable `.xlsx` -> restore the newest good copy from `backups\` (verify it opens before overwriting anything); never hand-repair.
- mtime-based selection behaving oddly (wrong network file picked up) -> list candidates by mtime AND embedded filename date; trust the filename date.
- New code you write: use `dump_atomic` for JSON, and prefer embedded dates over mtimes for file selection.

---

## 10. Dashboard JS behaves differently from Python

**Symptom:** the network dashboard's in-browser engine (flip totals, cascade sizes, route costs) disagrees with the Python engines' artifacts.

**Why this class exists:** the template `fec/templates/make_dashboard_html_00.tpl` contains a **hand-maintained JS mirror** of the Python engine (`flip_model.py`, `lt_priming.py`, `moneyball_core.build_P`, salience estimation). The template has ZERO audit coverage - all 136 audit checks as of 2026-07-19 can pass while the JS is arithmetically wrong. **The incident:** the JS mirror was fully psych-blind (consumed none of the pressure/edge/delivery receptivity multipliers), drifting up to 2.08% per issue, found by the 07-08 network audit (finding N-1) and fixed at commit `fd963ab` (2026-07-09) - the bundle now ships `engine.pmult/emult/dmult` and the tpl reads them (`make_dashboard_html_00.tpl:326`), with parity re-verified within 0.15% on all 18 issues.

**Discriminate:**
1. **Read the in-page badge.** Bottom-right of the dashboard, element `#engchk`: `updateEngChk()` (tpl:761) recomputes the JS flipModel total per issue and compares to the Python reference value (`engine.refflip`, shipped in the bundle by `build_dashboard_bundle.py`). `engine ✓ flip X = py Y` = parity within max(0.2, 3%); `⚠` = drift. This is the ONLY automated mirror check, and it covers only the flip total - not `prime()`, `spread()`, or the pathfinder.
2. **Check bundle vintage.** The tpl neutral-falls-back to 1.0 when `pmult/emult/dmult` are missing (old bundle + new tpl = silently psych-blind preview that still shows ✓ for psych-neutral members). Confirm the live `dashboard_data.json` contains `"pmult"` before trusting a parity read.
3. **Diff the two implementations by hand.** Python side: the engine constants and mirrors are declared at `fec/build_dashboard_bundle.py` (constants block ~line 238, "KEEP IN SYNC" note at ~line 251) and `fec/lt_priming.py:37,56`. JS side: tpl lines ~324-400 (banner: "faithful port of flip_model + competitive cascade + lt_priming"). Any change to gates/pricing/physics/constants in Python REQUIRES a matching tpl edit - the constants are duplicated literally, not imported.
4. **Preview safely.** Never run the builders just to preview: copy the tpl + `dashboard_data.json` to your scratchpad, substitute `__DATA__` yourself, and serve with `python -m http.server 8802` from the scratchpad. **Port 8801 is Paul's own server - always use 8802.** (session-ratified, 2026-07)

---

## 11. A missing artifact producing silent-neutral engine output

**Symptom:** engine output looks flattened - members who should differ behave identically, receptivity effects vanish, but nothing errored.

**Why:** the kernel's receptivity accessor `rc(member, key, default=1.0)` returns a NEUTRAL multiplier for any missing member, key, or file (`fec/moneyball_core.py:45-51` - a missing `member_receptivity.json` is caught and becomes `{}`). Deleting the receptivity artifact does not crash anything; engines quietly revert to pre-receptivity behavior. The say-do gate likewise **fails OPEN**: missing evidence files mean NO caps, silently un-capping Champions. This is deliberate (neutral fallback beats a crash mid-chain) but it makes absence invisible.

**The incident behind the loud-guard pattern (S2-02, run-1):** the whole `big5_traits.json` went missing and a bare `except FileNotFoundError: T={}` turned every member all-neutral with no signal anything was wrong (`AUDIT_FINDINGS_2026-07-02.md:35-40`). Fix was loud `!!` guards - e.g. `receptivity_layer.py` now prints `!! behavioral_dispositions.json MISSING - falling back to LEXICAL basis` and `!! electoral_plays.json MISSING/EMPTY ...` (`fec/receptivity_layer.py:71-78`).

**Discriminate:**

```powershell
# (a) Do the engine-input artifacts exist and have sane sizes?
Get-ChildItem "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\member_receptivity.json",
              "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\behavioral_dispositions.json",
              "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\say_do_gap.json" |
  Select-Object Name,Length,LastWriteTime

# (b) Scan the last chain run's step output for '!!' guard lines (rerun standalone if needed, section 6).
# (c) Rule out an env killswitch someone left set:
Get-ChildItem Env: | Where-Object Name -in 'RECEPT_LAYER','RECEPT_TRAITS','RECEPT_N','PERSONA_W'
```

`RECEPT_LAYER=0` disables receptivity consumption engine-side entirely (`fec/moneyball_core.py:48`); `RECEPT_TRAITS=lexical` / `RECEPT_N=text` revert bases. Any of these set in a long-lived shell makes engines "mysteriously" flat or different. Also note kernel caches are process-lifetime: a long-lived Python process will not see artifact refreshes until restarted.

---

## 12. A look-gate script refuses to run - this is usually CORRECT

**Symptom:** a `b5_*` validation script prints something like `!! LOOK REFUSED: prereg not LOCKED`, `!! LOOK REFUSED: RESULT-N already recorded (one look only)`, or `!! LOOK REFUSED (not consumed): input fingerprint drift vs pinned lock values` and exits.

**What these are:** the research program's one-look discipline, machine-enforced. A "look" is the single permitted evaluation of real data against pre-registered pass bars; the gate scripts (`fec/b5_n_matrix.py:349-368`, `fec/b5_a_matrix.py:240-242`, `fec/b5_behavioral_instrument.py:183`, `fec/b5_es_robustness.py:103`, `fec/b5_es_votesmart_look.py:89`, `fec/b5_panel_score.py`) refuse when: the prereg file is absent; its literal `STATUS: LOCKED` line is absent; a newline-anchored `## RESULT-*` heading already exists (look consumed); the SHA-256 input fingerprints/roster counts drifted from the pinned lock values; or the in-process simulate battery fails. **Every refusal is the gate protecting a scientific guarantee. Never edit a prereg, delete a RESULT heading, or "fix" fingerprints to make a look run.** See moneyball-research-methodology for the discipline itself.

**Refusal decoder (as of 2026-07-09):**

| Message | Meaning | Action |
|---|---|---|
| `prereg not LOCKED` | Prereg missing its `STATUS: LOCKED` line (e.g. the canceled expert panel - permanently refuses) | Correct behavior. Nothing to run. |
| `RESULT-* already recorded (one look only)` | Look was consumed; the recorded result stands forever | Read the prereg's RESULT section instead. |
| `input fingerprint drift ... (not consumed)` | Data changed since lock; prereg is single-vintage by design. Rounds 4 and 5 are in this state permanently (retired without a look; gated on MEM_N>=250 / a passing 5-seed diagnostic) | Correct behavior. A successor prereg is the only path, and it is gated. |
| `simulate battery failure (not consumed)` | Synthetic pre-checks failed; the look aborts without being spent | Correct behavior - the battery refusing IS the finding. |
| `COLLECTION RECORD addendum absent` (Vote Smart look) | For Vote Smart this is HISTORICAL — collection + the consumed RESULT-VS (TIER 5 UNCORROBORATED) merged to main 2026-07-10. For any FUTURE collection-gated look: absence means collection has not happened on your tree; check `git log --all` before citing status | User-gated. Do nothing; never re-collect. |

**The one genuinely-a-bug case on record:** the gate once false-tripped because prose in the prereg QUOTED the string `## RESULT-A`; fixed by newline-anchoring the heading match (commit `72690c9`, no look consumed - `fec/b5_n_matrix.py:357` carries the lesson as a comment). If a refusal looks wrong, diff the prereg against `git log -p -- <prereg>.md` to see whether the trigger text was legitimately added - do not touch the gate logic without change-control review.

A safe status query never consumes anything: run the script with **no flags** (e.g. `python "fec\b5_n_matrix.py"`) - it prints lock/look/fingerprint state and returns.

---

## Provenance and maintenance

Written 2026-07-09 against the worktree at commit `88a7048` (branch `claude/nifty-cray-f6d053`); all file:line cites and counts verified that day. Re-verification one-liners (run from the repo root; PowerShell unless noted):

- Imported-file-relative root with env override: `git grep -n "MONEYBALL_ROOT" fec/paths.py` (expect `ROOT` to default to the parent of the imported paths.py at lines 7-8).
- run_pipeline tail/800-char contract: `git grep -n "800" fec/run_pipeline.py` (expect lines 189-190) and `git grep -n "splitlines" fec/run_pipeline.py` (line 183).
- audit_full exits 1 on failure and 0 when clean: `git grep -n "sys.exit" fec/audit_full.py` (expect exactly ONE hit, at line ~1201); tail strings: `git grep -n "ALL MODULES CLEAN" fec/audit_full.py`.
- Kernel-test exit code: `git grep -n "sys.exit(1 if F else 0)" fec/tests/run_tests.py` (line 298).
- Current check counts (they grow; update the table): run `python "fec\tests\run_tests.py"` and `python "fec\audit_full.py"` on a quiet tree and read the tails (84 / 136 as of 2026-07-19).
- Parity-mode messages: `git grep -n -E "PARITY:|DRIFT DETECTED" fec/compute_pillars.py` (DRIFT at line 236; STALE/MISSING/CLEAN at lines 244-248).
- A2/A3 view-cache SKIP: `git grep -n "SKIP (view cache stale" fec/audit.py` (lines 24-25).
- Idempotency baseline (section 2's "real regression" rule): `Select-String -Path AUDIT_FINDINGS_2026-07-02_RUN2.md -Pattern "12/12","limit cycle"` and commit `git log --oneline -1 f17dc2c`.
- Input-purity method: `Select-String -Path AUDIT_FINDINGS_2026-07-03.md -Pattern "input-purity"` (lines 38-44); FRONTIER_OUT/OPT_OUT dials: `git grep -n "FRONTIER_OUT" fec/budget_frontier.py` (line 135) and `git grep -n "OPT_OUT" fec/optimize.py` (line 33).
- Electoral-plays checks are internal-consistency only: `git grep -n "overall" fec/audit_full.py` (lines 41-42 compare against the same artifact); the user-gated rebuild status is session-ratified - confirm with Paul before assuming it is still pending.
- Workbook-lock fallback: `git grep -n "per_topic_flip" fec/weekly_refresh.py` (line 80).
- Encoding boilerplate prevalence: `git grep -l "sys.stdout.reconfigure" -- fec/*.py` (121 files as of 2026-07-09); BOM reads: `git grep -l "utf-8-sig" -- fec/*.py` (33 files).
- Dateless-rows fix in place: `git grep -n "datePublished" fec/fetch_interviews.py` (3 sites); incident: `Select-String -Path AUDIT_FINDINGS_2026-07-06.md -Pattern "dateless"`.
- JS-mirror parity plumbing: `git grep -n "pmult" fec/templates/make_dashboard_html_00.tpl fec/build_dashboard_bundle.py`; badge: `git grep -n "updateEngChk" fec/templates/make_dashboard_html_00.tpl` (line 761); parity commit: `git log --oneline -1 fd963ab`.
- Neutral fallbacks and loud guards: `git grep -n "def rc" fec/moneyball_core.py` (line 51); `git grep -n "MISSING" fec/receptivity_layer.py` (lines 72, 78).
- Look-gate refusal sites: `git grep -n "LOOK REFUSED" -- fec/*.py` (b5_n_matrix, b5_a_matrix, b5_behavioral_instrument, b5_es_robustness, b5_es_votesmart_look as of 2026-07-09).
- The 07-08 network/vote/cycle report (OneDrive mtime fact, N-1 story) lives ONLY on a branch: `git show claude/magical-booth-f272da:AUDIT_FINDINGS_2026-07-08_NETWORK_VOTE_CYCLE.md` (read-only git; branch verified present 2026-07-09).
