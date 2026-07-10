---
name: moneyball-run-and-operate
description: Day-to-day operations runbook for the Moneyball system. Load this when the task is to RUN something - regenerate artifacts, run the pipeline chain (run_pipeline.py), refresh data (collectors, big5_traits, network, media blend), rebuild or preview a dashboard, write to the Excel workbook, lock/deploy the combined HTML, or figure out which script writes which artifact. Also load when symptoms include "which order do I run these in", "PermissionError saving the workbook", "the chain printed PIPELINE COMPLETE but did nothing", "can collectors run during the chain", "openpyxl reads None", or "what port do I preview on". Does NOT cover what changes are allowed or how to verify them (moneyball-change-control), diagnosing a failing run (moneyball-debugging-playbook), env-dial meanings (moneyball-config-and-flags), recreating the environment (moneyball-build-and-env), or measurement/diagnostic tooling (moneyball-diagnostics-and-tooling).
---

# Moneyball: run and operate

This skill is the operations manual for the Moneyball congressional-influence model: how to run the canonical pipeline chain, refresh the underlying data in the right order, operate the collectors, write safely to the Excel workbook, and build/preview/deploy the dashboards. The system is a set of Python scripts under `fec/` that read and write a LIVE data tree at `C:\Users\pgoff\OneDrive\Desktop\Melange Systems` (JSON artifacts, a SQLite database, an Excel workbook, and generated HTML). Almost every script executes its whole body at import time and writes to that live tree even when run from a git worktree, so "just running it to see what happens" is never safe. Everything below was verified against the repo on 2026-07-09.

## When NOT to use this skill

- Deciding whether a change/run is ALLOWED, what is user-gated, and the verification protocol → **moneyball-change-control**.
- A run failed and you need to triage the symptom → **moneyball-debugging-playbook**.
- What an env var (dial) means or its default → **moneyball-config-and-flags**.
- Setting up Python, packages, encodings, or new-code conventions → **moneyball-build-and-env**.
- Adding tests/audit checks or judging evidence quality → **moneyball-validation-and-qa**.
- History of why something is the way it is → **moneyball-failure-archaeology** / **moneyball-architecture-contract**.

## Quick reference

```powershell
# ALWAYS operate from the LIVE tree root (paths are resolved there regardless of cwd anyway):
cd "C:\Users\pgoff\OneDrive\Desktop\Melange Systems"

# BEFORE any run: check for Paul's live jobs (see section 7)
Get-Process python* -ErrorAction SilentlyContinue | Format-Table Id,StartTime,CPU

# The canonical chain (17 steps + audit; ~6-8 min warm, up to ~19 min if the workbook view cache is dead)
python "fec\run_pipeline.py"
python "fec\run_pipeline.py" --from optimize     # resume mid-chain (prefix match on script filename)

# Read-only-safe to run casually (session-ratified allowlist, 2026-07):
python "fec\tests\run_tests.py"    # kernel unit tests (37 as of 2026-07-09; README's "30" is stale)
python "fec\audit_full.py"         # full-body audit (~69 checks reported as of 2026-07-09; count grows)

# Safe dashboard preview (8801 is Paul's server - NEVER use it; 8802 is yours):
python -m http.server 8802 --bind 127.0.0.1 --directory "C:\Users\pgoff\OneDrive\Desktop\Melange Systems"
```

Hard rules embedded in this skill (master list with rationale lives in **moneyball-change-control**):

| Rule | Source |
|---|---|
| Worktrees do NOT isolate data: `fec/paths.py:7` hardcodes the live tree as ROOT | `fec/paths.py` (verified) |
| Import == execution for nearly every `fec/*.py`; never import to inspect | session-ratified, 2026-07 |
| Only `fec/tests/run_tests.py` and `fec/audit_full.py` are read-only-safe to run casually | session-ratified, 2026-07 |
| Check for Paul's live jobs before any run; run baselines serially | session-ratified, 2026-07 |
| Port 8801 is Paul's own server; previews use 8802 | session-ratified, 2026-07; `.claude/launch.json` |
| Excel must be CLOSED for any workbook write (PermissionError otherwise) | `.claude/commands/fable-audit.md:13-15` |
| Never hand-edit/extend generated JSON (producer clobbers it) | incident recorded at `fec/per_category_stance.py:21-24` |
| The electoral_plays rebuild chain is USER-GATED - refuse politely | session-ratified, 2026-07 |
| Never run the `fec/apply_*` COM one-shots casually (section 4 DANGER table) | session-ratified, 2026-07 |

---

## 1. The canonical chain: `python fec/run_pipeline.py`

"The chain" is the single sequenced runner that regenerates every derived artifact in dependency order. It exists because hand-typed script sequences kept forgetting passes (`fec/run_pipeline.py:4,27`). Each step runs as a subprocess; the runner prints the step name, OK/!!, elapsed seconds, and the step's LAST stdout line; the first nonzero exit code aborts with 800-char stdout/stderr tails (`run_pipeline.py:41-50`).

The 17 steps in order (CHAIN list at `fec/run_pipeline.py:19-35`), with the artifact each writes:

| # | Step | Writes |
|---|---|---|
| 1 | `receptivity_layer.py` | `member_receptivity.json` (per-member psychology multipliers) |
| 2 | `per_category_stance.py` | `category_stance.json` (533 members x 18 issue stances, incl. say-do gate block) |
| 3 | `compute_pillars.py --write` | `ranks_python.json` = THE rank authority; also refreshes `pillar_inputs_snapshot.json` |
| 4 | `sync_stance_g.py` | Workbook `Rank & Allocation` col G ONLY (openpyxl values write; kills the view cache) |
| 5 | `per_topic_flip.py` | `per_topic_alloc.json` |
| 6 | `per_topic_coalition.py` | `per_topic_coalition.json` |
| 7 | `lt_priming.py` | `lt_priming.json` (in-chain since 2026-07-04 - it once fossilized) |
| 8 | `budget_frontier.py` | `budget_frontier.json` |
| 9 | `budget_frontier.py --electoral` | `budget_frontier_electoral.json` ("the pass that got forgotten once") |
| 10 | `optimize.py` | `optimize_result.json` |
| 11 | `build_im_allocation.py` | `im_allocation.json` |
| 12 | `salience_shock.py --advise` | `salience_advisory.json` (must be fresh BEFORE the bundle) |
| 13 | `build_dashboard_bundle.py` | `dashboard_data.json` AND `bipartisan.json` |
| 14 | `make_dashboard_html.py` | `Moneyball Dashboard.html` |
| 15 | `make_member_desk.py` | `member_desk_bundle.json` + `cu-member-desk.html` |
| 16 | `make_combined.py` | `Moneyball.html` (dashboard + desk in one file) |
| 17 | `audit_full.py` | nothing - prints the pass/fail ledger, ends `FULL-BODY AUDIT — N passed, N FAILED` |

**Flags** (`run_pipeline.py:36-44`):

- `--from <prefix>` - skip steps until one whose FILENAME starts with the prefix, then run to the end. `--from budget_frontier` runs BOTH frontier passes; `--from b` also starts at budget_frontier (first prefix match). **Trap:** a typo'd prefix matches nothing, every step is skipped, and the runner still prints `PIPELINE COMPLETE` with no error. If your run finished in under a second, that is what happened.
- `--recalc` - accepted but RETIRED. It prints a note and continues. Since "Phase 2" (2026-07-02) Python owns all derived math; there is no Excel recalculation step anywhere (`run_pipeline.py:6-11,38`). Older docs (the README data-refresh line) still say `run_pipeline --recalc`; just run plain `run_pipeline.py`.

**Ordering is load-bearing - never hand-order the steps:**
- `compute_pillars` (step 3) runs BEFORE `sync_stance_g` (step 4) because it reads workbook formula cells "while the view cache is alive"; sync's openpyxl save destroys those cached values (`run_pipeline.py:21-22`).
- `salience_shock --advise` (step 12) must precede the bundle (step 13) so the dashboard exports a fresh advisory (`run_pipeline.py:30`).
- `bipartisan.json` is written at step 13 but read by the kernel in steps 5-12, so earlier steps consume the PREVIOUS run's copy. Consequence: after a stance/network change, engine outputs legitimately shift once more on the NEXT run ("two-run convergence" - not a determinism bug). `bipartisan.json` is the ONLY remaining feedback edge - col G has been a pure output since @f17dc2c (`fec/per_category_stance.py:9-13`); note `.claude/commands/fable-audit.md:76-77` still also names the col-G sync here, which is stale (doc-rot).

**Runtime expectations** (as of 2026-07-09): ~6-8 min warm (7.4 min on 2026-07-04, 5.9 min on 2026-07-06 per the in-repo AUDIT_FINDINGS reports); up to ~19 min when the workbook view cache is dead (`MATHEMATICAL_SPECIFICATION.md:64`; `.claude/commands/fable-audit.md:43` says "6-19 min").

**Determinism:** SEED=7, MC=20 defaults with edge-keyed common random numbers (a splitmix64 hash keyed by iteration+edge, so the same seed gives the same draw regardless of evaluation order). Same-seed reruns with unchanged inputs produce byte-identical artifacts - any no-input hash drift is a real regression. Non-default `SEED`/`MC` change some output FILENAMES (`per_topic_coalition_seed%d_mc%d.json`, `per_topic_coalition.py:74`), so downstream consumers of the unsuffixed name silently won't see your run. CRN machinery details → **moneyball-proof-and-analysis-toolkit**.

**The audit at the end:** step 17 is `audit_full.py` - the full-body audit (~69 checks reported at runtime as of 2026-07-09; the count grows as guards are added, so a FAILED check is the finding, not a count mismatch). Expect the tail `ALL MODULES CLEAN`. It shells out to `audit.py` (workbook integrity) and `audit_frontier.py`, and re-runs engines under `FRONTIER_OUT`/`OPT_OUT` temp redirects so production artifacts are never clobbered. "View-stale SKIP" notes from audit.py checks A2/A3 are NORMAL when the workbook cache is dead.

**Verification protocol after any code change** (owned by moneyball-change-control; stated here because you will be asked): kernel tests → pipeline → ZERO rank delta vs the previous `ranks_python.json` (unless the change is supposed to move ranks) → audit clean (`README.md:63-64`).

---

## 2. The data refresh order (and why it matters)

The chain (section 1) only RECOMPUTES from existing inputs. Refreshing the inputs themselves has its own order (`README.md:65-67`):

```
collectors  →  big5_traits  →  social_interaction_layer  →  build_multilayer_network  →  build_media_blend  →  run_pipeline
```

Why the order matters - each stage writes the next stage's input:

| Stage | Reads | Writes | Feeds |
|---|---|---|---|
| Collectors (section 3) | web sources | `social_media.db` (speeches/posts), Quorum exports | everything below |
| `big5_traits.py` | `social_media.db` | `big5_traits.json` (text personality z-scores) | disposition/receptivity layer |
| `social_interaction_layer.py` | `social_media.db` | `social_interactions.json` | the multilayer network |
| `build_multilayer_network.py` | cosponsor xlsx + `social_interactions.json` | `congress_cosponsor_network_AUG<date>.xlsx` | ALL network loaders (they glob `congress_cosponsor_network_*.xlsx` newest-by-mtime, so the AUG file goes live pipeline-wide with zero loader changes; revert = delete the AUG file) |
| `build_media_blend.py` | press cache + social corpus | workbook `Press Release - Raw` values (+ `press_component_meta.json`); timestamped workbook backup FIRST | the press pillar `compute_pillars` reads |
| `run_pipeline.py` | all of the above | every chain artifact | dashboards |

Run any stage out of order and the downstream stage silently consumes stale data - no error, just last week's numbers.

**The authoritative, fully-expanded version of this order is `fec/weekly_refresh.py`** - the unattended Sunday-06:00 Task Scheduler job (`MoneyballWeeklyRefresh`; remove with `schtasks /Delete /TN MoneyballWeeklyRefresh /F`). It is also "fine to run by hand anytime" (docstring) and is the best template when you need a full manual refresh. Its sequence (verified at `weekly_refresh.py:58-108`): CREC (last 14 days) → CHRG hearings (last 400 days - transcripts publish months late) → `big5_traits` → `interaction_features` → `behavior_panel` → `behavioral_dispositions` → `big5_lexcal_v2` → `big5_hybrid` → `social_interaction_layer` → `build_multilayer_network` → `co_appearance_layer` → `member_reference_layer --rebuild` (FREE cache-only; paid `--score` passes stay manual) → `press_stance_stack` → `build_media_blend` → **run_pipeline** → diagnostic layers (signed_coalitions, kb_benchmark, lep_criterion, say_do_gap) → incremental audio/narrative steps (cost-capped by `NARR_MAX`, default 15) → desk + combined re-embed.

Behaviors to know:
- Collector failures never block the refresh; only a pipeline failure is a hard error (`weekly_refresh.py:8-9`).
- If `run_pipeline` fails (typically: Excel holds the workbook locked at the col-G sync), the refresh falls back to `run_pipeline.py --from per_topic_flip`, which skips every workbook-writing step and rebuilds engines+dashboards from the last consistent state. The col-G view stays stale until the next unlocked run - that is the standard self-heal contract, not a bug (`weekly_refresh.py:73-80`).
- X/Truth/Bluesky collectors are NOT run unattended (keys/discovery are interactive) - run `tweet_collector.py` / `process_quorum.py` manually, then the refresh (`weekly_refresh.py:17-18`).

---

## 3. Collector operations

Collectors pull member-of-Congress text into `social_media.db` (SQLite, WAL journal mode - WAL = "write-ahead log", which allows concurrent readers alongside a writer). Shared disciplines: **resumability** (per-key fetch-log tables - rerunning never repeats finished work), **drop-never-guess attribution** (any speaker that cannot be uniquely resolved against the 533-member roster in `congestion.json` is DROPPED, never approximated - `fetch_congressional_record.py:19-20`), and politeness (delays, honest User-Agent).

**May collectors run while the chain runs? YES.** Verified 2026-07-09: none of chain steps 1-16 opens `social_media.db` (grep the CHAIN scripts for `social_media` - zero hits). The final audit (step 17) DOES open it, but strictly read-only (`PRAGMA integrity_check` at `audit_full.py:177-182`; `PRAGMA query_only=1` at `audit_full.py:315-320`), and WAL mode permits a reader during collector writes. The converse also holds: collectors never see chain artifacts mid-write, because chain writes are atomic via `dump_atomic` (temp file + `os.replace`).

| Collector | Command (from live root) | Source | Key/auth | Resume mechanism |
|---|---|---|---|---|
| Floor speeches | `python "fec\fetch_congressional_record.py" crec --since 2025-07-01 [--until YYYY-MM-DD]` | GovInfo CREC | `GOVINFO_KEY` env or `fec/govinfo_key.txt`, else DEMO_KEY (~30 req/hr, discovery only; content zips keyless) | `cr_fetch_log` keys `crec:CREC-YYYY-MM-DD` |
| Hearings | `python "fec\fetch_congressional_record.py" chrg --since 2025-01-01` | GovInfo CHRG (finance-title filtered) | same | `cr_fetch_log` keys `chrg:<packageId>` + stored-package guard (any existing rows for a package = never re-insert) |
| Corpus status | `python "fec\fetch_congressional_record.py" status` (read-only) | - | - | - |
| Interviews | `python "fec\fetch_interviews.py" <leg>` where leg ∈ `cnn mtp cbs abc pbs npr fox hewitt status`; `--since/--until` only for cnn/pbs/npr; `--verify` cnn only (`fetch_interviews.py:662-693`) | network transcript sites | none | `iv_fetch_log` per-leg keys (e.g. `fox:<slug>` where `gone` = hard 404/410 only; timeouts stay retryable); completion sentinel `collector_sentinels\<leg>.done` |
| Social posts | `python "fec\tweet_collector.py" <cmd>` where cmd ∈ `init fetch status build-influence discover-bluesky search classify`; `--platform {bluesky,x,truth}` (default bluesky), `--limit-members N` (`tweet_collector.py:319-320`) | Bluesky (keyless) / X (`X_BEARER_TOKEN`, paid) / Truth (`TRUTH_TOKEN`) | per platform | `fetch_log(platform,bioguide)` checkpoints; `BSKY_SKIP_FETCHED=1` skips ok-logged members |
| Quorum export | `python "fec\process_quorum.py"` then `python "fec\build_social_master.py"` (NO flags; whole scripts run at import; build_social_master RE-EXECUTES process_quorum via its import at line 18) | licensed `Quorum Master.xlsx` (no in-repo fetcher - irreplaceable without re-export) | - | not resumable; rerun = full reprocess |
| Staffers | `python "fec\build_staff_directory.py"` (env `STAFF_SRC`, default `C:\Users\pgoff\Downloads`) | Quorum staffer exports | - | rerun = rebuild |
| Press full text | `python "fec\fetch_press_text.py"` (NO flags) | press URLs | - | `press_text_cache.jsonl` |
| Vote Smart NPAT | `python "fec\votesmart_npat_fetch.py" --limit N` | Vote Smart API | `fec/votesmart_api_key.txt` - absent on main (user-gated). **Main-state only - do NOT probe the key file for freshness**: branch `claude/clever-elbakyan-15fa11` completed the collection 517/518 via a user-directed browser-session amendment (no key) and consumed the ES look (@e77703c). Check `git log --all --oneline \| Select-String "Vote Smart"` per `moneyball-docs-and-claims` §3.2; never re-collect | - |

**Attribution safety is not optional.** The Record collector excludes witness surnames for whole hearings (the Gov. Michael Barr vs Rep. Andy Barr collision, `fetch_congressional_record.py:105-119`); interviews carry nickname classes, rank-scoped surname pools, and first-name-compatibility guards. Unverified Bluesky handles are stored with an `[UNVERIFIED — confirm]` suffix and excluded from rollups until Paul confirms. If you write or modify a collector, "honest drop beats mis-attribution" is the standard.

**Supervisor:** `fec/collector_supervisor.py` runs under Windows Task Scheduler as `MoneyballCollectorSupervisor` (every 10 min, idempotent, self-terminating). Each tick it relaunches dead legs DETACHED, kills+relaunches legs wedged >45 min (no DB progress AND no CPU), and when all target legs have sentinels it fires GATE-1 (free: weekly_refresh) then GATE-2 (**SPENDS REAL MONEY**: the user-approved full big5 re-score, capped by `B5_GATE_CAP`=$200 / `REF_GATE_CAP`=$100; an unparseable cost estimate fails CLOSED). Targets come from `collector_targets.json`. Do not start the supervisor casually - GATE-2 is a paid, one-shot event.

**DB hygiene:** commit in SHORT transactions (a day-long write transaction once starved the CREC collector's lock, `fetch_interviews.py:245`). Never DELETE duplicate rows - exact-duplicate ledgers ("D2") are user-gated (session-ratified, 2026-07). `social_media.db` is precious: parts of its corpus (the Fox archive) are frozen upstream and unre-crawlable; back it up before anything destructive (`backups\social_media.PRE-*` convention).

---

## 4. Workbook discipline

The workbook `Moneyball Main Version - Blended.xlsx` (live root) is a self-refreshing VIEW, not the system of record - `ranks_python.json` is the rank authority ("Phase 2", 2026-07-02). Python writes only literal values; the workbook's own formulas recalculate when a human next opens it in Excel, because every Python writer sets `fullCalcOnLoad=True` before saving (`fec/sync_stance_g.py:25`).

Operating rules:

1. **Excel must be CLOSED for any write.** An openpyxl save against an open workbook raises PermissionError - record it, skip the step, continue; never kill Excel, never reach for COM (`.claude/commands/fable-audit.md:13-15`). In the weekly refresh a locked workbook triggers the sanctioned `--from per_topic_flip` fallback (section 2).
2. **`backups/` is the recovery layer, auto-created by writers.** `build_media_blend.py` copies the workbook to `backups\...BACKUP-<ts>.xlsx` FIRST (`build_media_blend.py:113-115`); the one-shot tools back up as `.PRE-<TAG>-<ts>.xlsx`. Exceptions to know: `sync_stance_g.py` makes NO backup (it only touches col G), and `write_im_sheet.py` uses a FIXED backup name (`...PRE-IM-20260626.xlsx`) that overwrites its own previous backup. Treat `backups/` as read-only.
3. **openpyxl saves strip cached formula values.** After ANY pipeline run (the col-G sync saves the workbook), `data_only=True` reads of FORMULA cells return `None` until the user opens Excel again (typed literal cells always survive). This is the documented self-heal contract, not a bug - do not "fix" it. `compute_pillars` snapshots the formula-backed pillar inputs to `pillar_inputs_snapshot.json` for exactly this reason; its "(view cache dead -> snapshot)" print is normal.
4. **"Refreshing the view" = the user opens Excel.** If someone reports the workbook "looks stale/blank", the answer is usually: open it in Excel, let fullCalcOnLoad recalculate, save.
5. **The IM-sheet lag:** the chain refreshes `im_allocation.json` every run (step 11), but the workbook's `IM Allocation` SHEET is rebuilt only by the manual COM tool `write_im_sheet.py` (which regenerates `im_allocation.json` first, then writes the sheet with a B1 FLIP/COALITION switch). The sheet therefore lags the JSON until that tool is deliberately run - with Excel closed.
6. **User dials live in Excel and are Paul's domain**: AB pillar weights (Blended Model AB2:AB5; live-verified 30/25/40/5 via `ranks_python.json['ab_weights']`), row-535 press tier weights, Category Stance / col-G taxonomy. Never change them in code or via a tool run (session-ratified, 2026-07).

### DANGER table: the `fec/apply_*` one-shot family (+ friends)

These are COM-era manual workbook mutators ("COM" = `win32com` driving a live Excel process; retired from the pipeline, NOT from the repo). They execute at import, most drive Excel COM, and several encode shipped calibration decisions in their docstrings. **Never run any of them casually; several require explicit user direction** (session-ratified, 2026-07). Purposes below are from each file's verified docstring:

| Script | One-line purpose | Mechanism / hazard |
|---|---|---|
| `apply_weights.py` | Set Blended AB2:AB5 pillar weights + recalc | COM. **LANDMINE: its hardcoded WEIGHTS (0.30/0.20/0.40/0.10) are STALE vs Paul's live 30/25/40/5 - running it silently overwrites the user's ratified dials** |
| `apply_alloc_cap.py` | Water-fill capped allocator; rewrites the col-U Allocation formula + cap cells | COM + recalc, backs up first |
| `apply_committee_fix.py` | Replaced double-percentile Influence% with raw/MAX (col R) | COM + recalc; historical fix, already applied |
| `apply_committee_reweight.py` | Recompute Committee Data B/C/D from the seats text | Default = read-only VALIDATE; `--apply` rewrites via COM + CalculateFull |
| `apply_leg_stance.py` | Stance-aware legislative pillar (writes Blended col 4) | COM + recalc, backs up first |
| `apply_press_dedup.py` | Rebuild `Press Release - Raw` excluding 1,310 billstatus double-count rows | COM, backs up first |
| `apply_press_overrides.py` | Merge dashboard-exported press-stance overrides into `press_stance_overrides.json` + re-flow the press pillar | COM. This is the SANCTIONED override path for stance corrections (stance labels are Paul's domain - never relabel by model judgment; route through this mechanism) |
| `apply_raw_max_norm.py` | Signed-magnitude (value/MAX) normalization for cols R and I | COM + full recalc; historical fix |
| `apply_two_hop_stance.py` | Compose model stance with the curated valence registry | `--eval` / `--uncovered` are analysis modes; still executes at import |
| `apply_stance_guard.py` | HARD-GUARDED: `sys.exit('SUPERSEDED...')` at import | Would clobber col-G tiers - leave the guard alone |
| `sync_stance_clean.py` | HARD-GUARDED: `sys.exit('SUPERSEDED...')` at import | Would restore a pristine backup OVER the live workbook |
| `write_im_sheet.py` | Rebuild the workbook `IM Allocation` sheet (the one writer that writes formulas) | COM; fixed self-overwriting backup name |
| `add_judiciary_seats.py` | One-shot: added Judiciary to the tracked committee set (user-directed 2026-07-05) | openpyxl; idempotent, but its `CMTE_ROSTER` env default points at a dead scratchpad path |

---

## 5. Dashboards: build, preview, lock, deploy

**Build** (steps 13-16 of the chain; runnable individually, all MUTATE the live tree):

```powershell
python "fec\build_dashboard_bundle.py"   # -> dashboard_data.json + bipartisan.json (bipartisan.json feeds BACK into engines - a casual run changes engine inputs)
python "fec\make_dashboard_html.py"      # -> "Moneyball Dashboard.html" (replaces __DATA__ in fec/templates/make_dashboard_html_00.tpl)
python "fec\make_member_desk.py"         # -> member_desk_bundle.json + cu-member-desk.html;  --data = bundle only
python "fec\make_combined.py"            # -> Moneyball.html (must run AFTER both HTML files exist)
```

The dashboard JS is a hand-maintained mirror of the Python engines and is INVISIBLE to the audit (only `dashboard_data.json` is audit-checked, not the templates); mirror-edit discipline is owned by **moneyball-architecture-contract**. Operationally: after any engine-math change, regenerate the bundle AND check the in-page `engine ✓` badge bottom-right of the dashboard.

**Safe preview.** Never open the built HTML via `file://` - browser preview tooling forces https so `file://` URLs break, and the locked deploy page hard-blocks non-secure contexts (`window.crypto.subtle` check, `fec/lock_dashboard.py:31-32`). Serve over localhost http instead:

```powershell
# Option A (READ-ONLY view of the live tree): the launch.json server
#   .claude/launch.json defines "moneyball-ui-audit" = python -m http.server 8802 --bind 127.0.0.1
#   --directory "C:\Users\pgoff\OneDrive\Desktop\Melange Systems"   <- serves the LIVE tree, not your worktree
python -m http.server 8802 --bind 127.0.0.1 --directory "C:\Users\pgoff\OneDrive\Desktop\Melange Systems"
# then browse http://127.0.0.1:8802/Moneyball%20Dashboard.html

# Option B (for template experiments): NEVER run the builders just to preview a tpl edit.
# Copy the tpl + dashboard_data.json to your scratchpad, substitute __DATA__ yourself,
# and serve the scratchpad directory on 8802.
```

Port rules: **8801 is Paul's own server** (launch.json's `static` config) - never bind it; previews/audits use **8802** (session-ratified, 2026-07; `.claude/launch.json:5-15`). A UI smoke test must not leave test state in localStorage - the desk's engagement tracker and overrides live there and belong to the user.

**Lock and deploy:**

```powershell
python "fec\lock_dashboard.py" "your-password"    # omit the arg to auto-generate a strong password
```

Reads `Moneyball.html`, writes `deploy\index.html`: the whole HTML encrypted with AES-256-GCM (key = PBKDF2-SHA256 of the password, 250,000 iterations), wrapped in a self-decrypting page using browser WebCrypto - safe to host anywhere; only the password decrypts, in-browser (`fec/lock_dashboard.py:3-14`). The page refuses to decrypt on plain http/file - deploy behind https.

---

## 6. What lands where: artifact map of the live root

All paths relative to `C:\Users\pgoff\OneDrive\Desktop\Melange Systems`. Every chain writer is atomic (`dump_atomic`: temp sibling + `os.replace` - artifacts are either old or new, never truncated).

**Chain artifacts** (regenerated every `run_pipeline` run - see section 1 table): `member_receptivity.json`, `category_stance.json`, `ranks_python.json`, `pillar_inputs_snapshot.json`, `per_topic_alloc.json`, `per_topic_coalition.json`, `lt_priming.json`, `budget_frontier.json`, `budget_frontier_electoral.json`, `optimize_result.json`, `im_allocation.json`, `salience_advisory.json`, `bipartisan.json`, `dashboard_data.json`, `member_desk_bundle.json`, `Moneyball Dashboard.html`, `cu-member-desk.html`, `Moneyball.html`, plus workbook col G.

**Data-refresh artifacts** (section 2): `social_media.db`, `big5_traits.json`, `social_interactions.json`, `congress_cosponsor_network_AUG<date>.xlsx`, workbook `Press Release - Raw` + `press_component_meta.json`, plus the disposition/psych artifacts weekly_refresh rebuilds (`behavioral_dispositions.json`, `big5_v2.json`, `co_appearance.json`, `member_references.json`, `member_narratives.json`, ...).

**Diagnostics-only artifacts - safe to regenerate anytime, no live consumer** (README "Diagnostics-only" section, confirmed 2026-07-02): `stance_dynamics.json`, `social_stance_signals.json`, `tweet_influence.json`, `imviz.json`, `corrected_signals.json`, `social_member_summary.json`, `cu_golden_labels_stats.json`, `per_topic_alloc_bridge.json` (written only under `--bridge`/`BRIDGE=1`).

**NOT regenerable - treat as precious:** `social_media.db` (frozen upstream sources), `Quorum Master.xlsx` + staffer exports (licensed, no fetcher), `press_raw_original.json` (media-blend idempotence cache - rebuildable ONLY from a pre-blend backup via `rebuild_press_cache.py`), `congestion.json` (the canonical roster: its builders are attic'd - no live producer), everything in `Draft Systems` (irreplaceable raw; out of scope, do not even scan it), `backups/` (read-only recovery layer). The workbook itself is data of record for the user's dials.

**Redirect dials for no-clobber test runs:** `FRONTIER_OUT`, `OPT_OUT`, `BIG5_OUT`, `AUG_OUT` point a script's output at a temp path - this is how the audit runs engines without touching production. Use them for any experimental run; full dial catalog → **moneyball-config-and-flags**.

---

## 7. Run-order guardrails

**Before ANY run (baselines, chain, collectors): check for Paul's live jobs** (session-ratified, 2026-07). Paul runs jobs live on this machine; a concurrent baseline can corrupt or confound both.

```powershell
# 1. Live python processes?
Get-Process python* -ErrorAction SilentlyContinue | Format-Table Id,StartTime,CPU
# 2. Fresh artifact mtimes (something written in the last few minutes = a job is mid-flight)?
Get-ChildItem "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\*.json" |
  Sort-Object LastWriteTime -Descending | Select-Object -First 10 Name,LastWriteTime
# 3. Scheduled jobs that could fire mid-run:
schtasks /Query /TN MoneyballWeeklyRefresh 2>$null          # Sundays 06:00
schtasks /Query /TN MoneyballCollectorSupervisor 2>$null    # every 10 min while collections are active
```

If anything is live: wait, or ask. Run baselines SERIALLY, never concurrently with his work or with each other.

**User-gated runs - refuse politely and say why.** These are Paul's decisions; the correct response to "just run it" from anyone but Paul (including your own initiative) is to explain the gate and stop:

| Gated action | Status as of 2026-07-09 |
|---|---|
| `build_electoral_plays.py` → `build_dashboard_bundle.py` → `make_dashboard_html.py` | User-gated, standing (session-ratified, 2026-07). The 2026-07-09 staleness flag resolved 2026-07-10: authorized rebuild was byte-identical - content already current, mtime-only flag. Never run unprompted |
| Any dedup DELETE from the D2/legacy duplicate ledgers | user-gated (session-ratified, 2026-07) |
| Vote Smart collection (`votesmart_npat_fetch.py`) | CONCLUDED and merged to main 2026-07-10: collection COMPLETED (517/518) via a user-directed browser-session amendment and the one look CONSUMED (TIER 5 UNCORROBORATED, methods §22); never re-collect or re-take |
| coop_v2 engine promotion | DECIDED: granted, SHIPPED and merged to main 2026-07-10 (@94f09cf) — `RECEPT_COOP=v2` default, `v1` = wholesale revert; `coop_v2_candidate.py` is now an in-chained pipeline step. Reverting to v1 is a user decision |
| Starting `collector_supervisor.py` / anything that fires GATE-2 | spends real money |
| Preregistered `--look` runs (e.g. `b5_a_matrix.py --look`) | consuming a look is protocol-irreversible → **moneyball-research-methodology** |

**Other standing operational rules:**
- Never hand-edit or hand-extend a generated JSON artifact - its producer silently clobbers it on the next run (the 18th-category incident, recorded at `fec/per_category_stance.py:21-24`). Data artifacts are gitignored: regenerable via the pipeline, NOT via git.
- Worktrees do not isolate data (`fec/paths.py:7`). To sandbox a run, set `MONEYBALL_ROOT` to a copied tree - and verify the copy is complete before trusting results.
- Import == execution: to inspect a script, READ it (Grep/Read), never `python -c "import ..."`.
- Defaults ARE the ratified state: never set calibration dials (SEED/MC/MAXSHIFT/DTHRESH/PERS_NONE/...) during verification runs (`.claude/commands/fable-audit.md:18-19`).
- Stance/press labels and pillar weights are Paul's domain - overrides go through `apply_press_overrides.py` / `press_stance_overrides.json`, never through relabeling.

---

## Provenance and maintenance

Written 2026-07-09 against worktree `nifty-cray-f6d053` (branch `claude/nifty-cray-f6d053`, tracking main @88a7048). All file:line cites verified that day. Re-verification one-liners (run from the repo root; all read-only):

```powershell
# Chain steps + flags still as documented:
Get-Content "fec\run_pipeline.py" -TotalCount 51
# Data refresh order (README) and its full expansion:
Select-String -Path "README.md" -Pattern "Data refresh order" -Context 0,2
Select-String -Path "fec\weekly_refresh.py" -Pattern "^step\(" | Select-Object -First 30
# Chain touches no social_media.db except the read-only audit:
Select-String -Path "fec\receptivity_layer.py","fec\per_category_stance.py","fec\compute_pillars.py","fec\sync_stance_g.py","fec\per_topic_flip.py","fec\per_topic_coalition.py","fec\lt_priming.py","fec\budget_frontier.py","fec\optimize.py","fec\build_im_allocation.py","fec\salience_shock.py","fec\build_dashboard_bundle.py","fec\make_dashboard_html.py","fec\make_member_desk.py","fec\make_combined.py" -Pattern "social_media"   # expect: no output
Select-String -Path "fec\audit_full.py" -Pattern "query_only|integrity_check"
# Collector CLIs:
Select-String -Path "fec\fetch_congressional_record.py" -Pattern "Usage:" -Context 0,3
Select-String -Path "fec\fetch_interviews.py" -Pattern "usage:"
Select-String -Path "fec\tweet_collector.py" -Pattern "add_argument"
# apply_* family roster (any NEW file here must be added to the DANGER table):
Get-ChildItem "fec\apply_*.py" | Select-Object Name
# apply_weights stale-constant landmine:
Select-String -Path "fec\apply_weights.py" -Pattern "WEIGHTS ="
# Live pillar weights (the only truth; reads the LIVE artifact):
Select-String -Path "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\ranks_python.json" -Pattern "ab_weights"
# Ports / preview servers:
Get-Content ".claude\launch.json"
# Lock/deploy paths:
Select-String -Path "fec\lock_dashboard.py" -Pattern "SRC =|OUT =|ITERS"
# Kernel test count (printed at runtime; grep approximation = ok( sites minus the def):
(Select-String -Path "fec\tests\run_tests.py" -Pattern "[^_a-z]ok\(").Count
# Runtime expectations still on record:
Select-String -Path ".claude\commands\fable-audit.md" -Pattern "6.19 min"
Select-String -Path "MATHEMATICAL_SPECIFICATION.md" -Pattern "19 min"
# Scheduled tasks (live machine state, may legitimately differ):
schtasks /Query /TN MoneyballWeeklyRefresh; schtasks /Query /TN MoneyballCollectorSupervisor
# Diagnostics-only artifact list:
Select-String -Path "README.md" -Pattern "Diagnostics-only" -Context 0,5
```

Volatile facts to re-check on every major merge: the CHAIN list (steps get added - lt_priming joined 2026-07-04), the audit check count (grows), the kernel test count (grows; README's "30" already lags), the apply_* roster, runtime figures, and every gate status in section 7 (electoral_plays, D2 ledger; the Vote Smart and coop_v2 rows were CONCLUDED/DECIDED and merged to main 2026-07-10).
