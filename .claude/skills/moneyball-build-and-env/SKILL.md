---
name: moneyball-build-and-env
description: Load this skill when setting up or repairing the Moneyball environment - fresh machine, fresh clone, new worktree, missing Python packages, ModuleNotFoundError, "where is the data?", "why is my clone empty?", questions about paths.py / MONEYBALL_ROOT / MONEYBALL_DRAFT, API-key file locations, which data is irreplaceable vs regenerable, Windows/OneDrive/encoding errors (UnicodeEncodeError, PermissionError on the workbook, cp1252 mojibake), or when WRITING A NEW fec/*.py SCRIPT and needing the house style (encoding boilerplate, atomic writes, logging contract, path resolution). It does NOT cover running the pipeline day-to-day (see moneyball-run-and-operate), the env-var dial catalog (see moneyball-config-and-flags), change-control rules (see moneyball-change-control), or test/audit authoring (see moneyball-validation-and-qa).
---

# Moneyball: build the environment + house style for new code

This skill recreates a working Moneyball environment from zero and defines the conventions every new `fec/*.py` script must follow. The single most important fact: **the production data plane is gitignored, so a fresh clone cannot run data-dependent workflows.** The real system is the live data tree at `C:\Users\pgoff\OneDrive\Desktop\Melange Systems` (a OneDrive-synced folder that is also the git repo); a script run from that checkout resolves there, while a script run from a git worktree resolves to the worktree's EMPTY data plane unless `MONEYBALL_ROOT` overrides it. `requirements.txt` is the canonical production/audit/test manifest; optional research and paid dependencies remain documented below. Follow the from-zero checklist at the end; you are done when the kernel tests print `KERNEL TESTS — N passed, 0 FAILED` (count grows — trust the run's own tail). (Manifest claim corrected 2026-07-19; verified against `requirements.txt` and `fec/run_pipeline.py:78-95`.)

## When NOT to use this skill

- Running the chain, collectors, dashboards, or the dangerous `apply_*` tools → **moneyball-run-and-operate**
- Looking up an env dial, its default, or adding a new dial → **moneyball-config-and-flags**
- What you may change and how changes get verified/gated → **moneyball-change-control**
- Diagnosing a live failure (wrong ranks, hung collector, audit failure) → **moneyball-debugging-playbook**
- System invariants and data-flow design → **moneyball-architecture-contract**

## Quick reference

| Thing | Value (as of 2026-07-09) |
|---|---|
| Live data tree = git repo root | `C:\Users\pgoff\OneDrive\Desktop\Melange Systems` |
| Upstream raw-data folder | `C:\Users\pgoff\OneDrive\Desktop\Draft Systems` (irreplaceable originals) |
| Path resolver | `fec/paths.py` — env overrides `MONEYBALL_ROOT`, `MONEYBALL_DRAFT` |
| Python | 3.12.10 (plain `python` on this machine) |
| Dependency manifest | `requirements.txt` is canonical for production/audit/tests; section 3 lists optional research/paid packages |
| Chain-minimum third-party package | `openpyxl` only (everything else is stdlib + the kernel) |
| Safe-to-run scripts | ONLY `fec/tests/run_tests.py` and `fec/audit/audit_full.py` — everything else can mutate its resolved data plane, often at import time |
| Done-signal | `python "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\fec\tests\run_tests.py"` → `KERNEL TESTS — N passed, 0 FAILED` (count grows — trust the run's own tail) |
| Ports | 8801 = Paul's own server (hands off); 8802 = preview/audit server (`.claude/launch.json`) |

Vocabulary used below: an **artifact** is a generated data file (JSON/CSV/xlsx/HTML) written by a script; the **kernel** is `fec/moneyball_core.py` (shared loaders + math every engine imports); the **chain** is the `fec/run_pipeline.py` sequence (`CHAIN` in `fec/run_pipeline.py:45-292`: 80 entries; a default run executes 79 because `DESK_RESPONSIVENESS=0` drops `responsiveness_layers.py` at `:300-302`; as of 2026-09-30; corrected 2026-09-30, verified against `fec/run_pipeline.py:45-302`) that regenerates its chain-owned artifacts; a **worktree** is a secondary git checkout (under `.claude/worktrees/`) that shares the repo's history but has its own working files and empty gitignored data plane.

## 1. The code-vs-data split (.gitignore)

`.gitignore` excludes **every data extension**: `*.json`, `*.jsonl`, `*.csv`, `*.tab`, `*.xlsx`, `*.html`, `*.db` (+ `-wal`/`-shm`), `*.txt`, `*.pkl`, `*.wav`, `*.bak`, `*.log`, plus whole data directories (`backups/`, `archive/`, `baseline/`, `deploy/`, `audio_pilot/`, `_stance_ft/`, `stance_ft_composed/`, `fec/liwc/rkh/`, `fec/liwc/bl2025/`, `fec/lep/`) (.gitignore lines 5–28, 43–44). A fresh clone therefore contains: `fec/*.py` (~137 live scripts + `fec/attic/` retired ones + `fec/tests/`), all `*.md` docs (`!*.md` keep rule), the two dashboard templates `fec/surfaces/templates/*.tpl`, two algorithm papers in `research/`, and a short whitelist of tracked data:

| Tracked data file | What it is / why tracked |
|---|---|
| `cu_valence_registry.json` | The user's committed target→valence judgments, derived FROM Paul's gold labels (`derive_valence_registry.py`); read by `press_stance_stack.py`, `tweet_stance_stack.py`, `apply_two_hop_stance.py`. **Tracked despite matching the `*.json` ignore rule** — it was force-added. If it ever leaves the index, re-adding requires `git add -f`. |
| `quorum_query.txt` | Source-of-truth Boolean search query pasted into the Quorum vendor UI (dated header inside); read by `process_quorum.py`, `build_media_blend.py`, `build_social_master.py`. Explicit `!quorum_query.txt` keep (.gitignore:32). |
| `fec/retiring_members.txt` | Hook file, one canonical member name per line (comment lines `#` ignored); feeds the 0.60 retiring-member incentive multiplier in `receptivity_layer.py`. Populate as retirements are announced. Keep rule .gitignore:33. |
| `.claude/launch.json` | Preview-server config (ports 8801/8802 — see section 2). Keep rule .gitignore:34. |
| `.claude/commands/*.md` | Project slash commands (currently only `fable-audit.md`). Keep rules .gitignore:41–42. |
| `fec/ccl24.zip`, `fec/cm24.zip`, `fec/cn24.zip`, `fec/pas224.zip`, `fec/weball24.zip` | FEC 2024-cycle bulk-data downloads (committees, candidates, contributions, spending). Their only consumers are RETIRED scripts in `fec/attic/` (`full_congestion.py`, `final_congestion.py`, `final.py`, `final_table.py`, `saturation.py`) — the original builders of `congestion.json`, the canonical 533-member roster+money artifact. Tracked so the roster remains regenerable at the next Congress rollover (see moneyball-congress-rollover-campaign). |
| `fec/liwc/mairesse_smoreg.json`, `fec/liwc/empath_categories.dic`, `fec/liwc/norms/concreteness_brysbaert.txt` | Fitted/licensed lexical model assets for the Big-Five text pipeline (producers: `fit_smoreg_essays.py` / `fit_smoreg_rkh.py`, `build_empath_dic.py`). |
| `fec/liwc/behavior_calibrated.json.candidate` | A built-but-unpromoted artifact. The `.candidate` suffix (and `*_candidate.py/json` names) means **staged, awaiting Paul's ratification — consumed by nothing** until promoted (see moneyball-change-control). Note: `coop_v2_candidate.*` graduated 2026-07-10 (promotion shipped @94f09cf, merged to main) but keeps its `_candidate` name for history. |

Consequences you must internalize:

1. **You cannot run anything from a bare clone.** Every engine's first act is loading `congestion.json`, the workbook, or `ranks_python.json` from ROOT — none of which are in git. The live tree IS the system; git is a code-and-docs overlay on top of it.
2. **New `.txt`/`.json`/etc. files are invisible to git by default.** That is the intended safe default (secrets and artifacts can't leak into commits), but if you create a genuine source-of-truth text/config file, you must add a `!` keep rule in `.gitignore` AND `git add` it — otherwise it silently exists on one machine only.
3. **Secrets have belt-and-suspenders ignores**: `fec/govinfo_key.txt` and `*.key` (.gitignore:2–3), `fec/votesmart_api_key.txt` (.gitignore:45), and everything else key-shaped is caught by the blanket `*.txt` rule anyway.

## 2. Live tree, worktrees, and paths.py

`fec/paths.py:7-13` is the entire default path-resolution layer:

```python
_HERE=os.path.dirname(os.path.abspath(__file__))
ROOT=os.path.abspath(os.environ.get('MONEYBALL_ROOT',os.path.join(_HERE,os.pardir)))
DRAFT=os.path.abspath(os.environ.get('MONEYBALL_DRAFT',os.path.join(ROOT,os.pardir,'Draft Systems')))
FEC=os.path.join(ROOT,'fec')
WORKBOOK=os.path.join(ROOT,'Moneyball Main Version - Blended.xlsx')
BACKUPS=os.path.join(ROOT,'backups')
def p(*parts): return os.path.join(ROOT,*parts)
```

When a fec script inserts its own directory and imports `ROOT` from `paths.py`, a worktree run imports the **worktree's copy of paths.py**, whose default `ROOT` is the parent of that imported file: the worktree root. Result, stated as law (PROJECT LAW 7, corrected 2026-07-19): **git worktrees isolate DATA — which makes them the WRONG place to run data-dependent work.** A worktree run targets the worktree's EMPTY data plane: reads die on missing inputs and writes land as throwaway worktree artifacts, not in live. To operate on real data from a worktree set `MONEYBALL_ROOT` to the live tree — and then writes DO hit live, so the old caution stands in force either way: never run `fec/*.py` casually. To use a populated copied sandbox instead, point `MONEYBALL_ROOT` at that copy before launching Python:

```powershell
# PowerShell: redirect one session to a populated sandbox copy of the data tree
$env:MONEYBALL_ROOT = "C:\sandbox\Melange Systems copy"
python "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\fec\tests\run_tests.py"
```

`MONEYBALL_DRAFT` points at **Draft Systems**, the sibling folder holding upstream raw inputs (original FEC files, press indexes, old workbooks) consumed by an external R press pipeline — "needed only to regenerate base data, includes irreplaceable files" (README.md:88–89).

**Preview servers** (`.claude/launch.json`): config `static` serves the current directory on **8801** and `moneyball-ui-audit` serves the **live tree** on **8802**. Port 8801 is Paul's own server — never claim it; use 8802 for previews and audits (session-ratified, 2026-07; PROJECT LAW 3). Note the 8802 config explicitly serves the live tree even when launched from a worktree; that server setting is independent of `paths.py` root resolution.

## 3. Python environment

- **Python 3.12.10** is what `python` resolves to on this machine (as of 2026-07-09). No virtualenv is in use; packages are installed into the system interpreter.
- **`requirements.txt` is the canonical production/audit/test manifest.** No `pyproject.toml`, `setup.py`, `Pipfile`, or `environment.yml` exists. The table below retains the optional research/paid inventory. (Corrected 2026-07-19; verified against `requirements.txt` and `fec/run_pipeline.py:78-95`.)
- The collectors use **stdlib `urllib` only** — `requests` and `bs4` appear nowhere in the repo. Do not introduce them; HTML is parsed with regex/string ops by design.
- **Zero use of the `logging` module anywhere** (0 of 175 tracked .py files). Everything prints (see section 6).

Install tiers (file counts = live fec scripts importing the package, excluding `fec/attic/`; versions = observed `pip list` on the working machine 2026-07-09 — no pins exist anywhere, these are "known-good", not requirements):

| Tier | Package (observed version) | Used by | Needed for |
|---|---|---|---|
| **Canonical runtime** | `requirements.txt`: `networkx`, `numpy`, `openpyxl`, `pandas`, `scikit-learn`, `scipy`, `soundfile` | production chain, audit, and tests | Install the manifest; `run_pipeline.py:78-95` preflights the first six before any producer runs. |
| Research / psychometrics | `numpy` (2.5.0), `scikit-learn` (1.9.0), `scipy` (1.18.0), `pandas` (3.0.3), `empath` (0.89), `semopy` (2.3.11) | 34 / 21 / 7 / 12 / 5 / 4 files | Big-Five batteries, prereg harnesses, CT-CM models, stance trainers |
| LLM steps | `anthropic` (0.115.0) | 10 files | `big5_llm`, `api_prelabel*`, `api_stance_layer`, narratives. Cost rule applies — see moneyball-change-control |
| Network diagnostics | `networkx` (3.6.1) | 3 files | `press_hcoi`, `sna_layout` |
| Audio layer | `soundfile` (0.14.0), `opensmile` (2.6.0), `imageio-ffmpeg` (0.6.0), `yt-dlp` (2026.6.9, invoked as `python -m yt_dlp` subprocess) | `b5_audio_*` | Voiceprint pipeline |
| Deep-learning (optional) | `torch` (2.12.1+cpu), `transformers` (5.12.1), `sentence-transformers` (5.6.0) | 1 file each | `train_stance_domain` transformer path, `b5_emb_build` embeddings |
| Workbook one-shots | `pywin32` (312, imported as `win32com`) | 11 files, all COM-era manual `apply_*` tools | NOT needed for the chain (Phase 2 removed COM from the pipeline). Treat these scripts as dangerous — see moneyball-run-and-operate |
| Dashboard deploy | `cryptography` (49.0.0) | `lock_dashboard.py` | AES-encrypting the deployable HTML |

```powershell
# Full install (one line, safe — installs packages only, touches no project data):
python -m pip install openpyxl numpy scikit-learn scipy pandas empath semopy anthropic networkx soundfile opensmile imageio-ffmpeg yt-dlp torch transformers sentence-transformers pywin32 cryptography
# Canonical production/audit/test runtime:
python -m pip install -r requirements.txt
```

## 4. Keys and secrets

| Credential | Resolution order | State as of 2026-07-09 |
|---|---|---|
| GovInfo (CREC/CHRG discovery) | env `GOVINFO_KEY` → file `fec/govinfo_key.txt` → `DEMO_KEY` (~30 req/hr) (fetch_congressional_record.py:31–32) | File present in live tree, gitignored |
| Anthropic | env `ANTHROPIC_API_KEY` → file `fec/anthropic_key.txt` (agency_communion_llm.py:75–77 and same pattern in `api_stance_layer.py`, `member_reference_layer.py`) | File present in live tree, gitignored via `*.txt` |
| Vote Smart | file `fec/votesmart_api_key.txt` ONLY (no env) (votesmart_npat_fetch.py:8–9,20) | **ABSENT BY DESIGN** — collection is user-gated; explicitly gitignored (.gitignore:45). Do not create a placeholder. **The key file's absence is NOT a route-status probe**: the collection was already completed 517/518 on branch `claude/clever-elbakyan-15fa11` via a user-directed browser-session amendment that superseded the key-file route (look consumed @e77703c). Check status via `git log --all --oneline \| Select-String "Vote Smart"` per `moneyball-docs-and-claims` §3.2. |
| X/Twitter | env `X_BEARER_TOKEN` (paid tier) (tweet_collector.py) | Not set → X fetch idle |
| Truth Social | env `TRUTH_TOKEN` (manual OAuth bearer) (tweet_collector.py) | Not set |

Rules: **never paste a key into chat or a commit** — a live API key was once pasted into a chat session and had to be rotated (session-ratified, 2026-07; the in-code echo is the comment at agency_communion_llm.py:77: "never paste keys into chat"). New credentials follow the govinfo pattern: env var first, single-line file under `fec/` second, and confirm the filename is ignored (`git check-ignore -v fec/<name>` — blanket `*.txt` already covers `.txt` names, but add an explicit line for anything else).

## 5. Irreplaceable vs regenerable data

Before deleting, moving, or "cleaning up" ANY file in the live tree, classify it:

| Class | Files | Recovery story |
|---|---|---|
| **Irreplaceable — external originals** | Everything in `Draft Systems` (README.md:88–89); `Quorum Master.xlsx` + the staffer exports `search-results-generated-by-quorum (45..52).xlsx` (licensed vendor exports, **no fetcher in the repo**); `votes/cu_rollcall_votes_clean.csv` (consumed at vote_by_category.py:42; **no producer exists anywhere in the repo** — verified by grep; treat as external and unrestorable) | None. Loss is permanent (or requires a paid vendor re-export). |
| **Irreplaceable in practice** | `social_media.db` (posts + floor speeches + hearing + interview transcripts). Nominally re-crawlable, but the Fox transcript archive is frozen upstream (publisher stopped ~2024-10), old URLs 404 permanently, and full crawls took days | Restore from `backups/social_media.PRE-*.db`. The db is backed up before every destructive operation — keep that convention. |
| **Rebuildable only from a specific backup** | `press_raw_original.json` — the media-blend idempotence cache (pre-blend press values). If lost, ONLY a PRE-blend workbook backup can rebuild it: `python fec/stance/rebuild_press_cache.py --list` then `--from "<backup>"`; the script refuses post-blend sources (rebuild_press_cache.py:35–37) | Guarded self-service recovery. |
| **Tracked in git (safe)** | The section-1 whitelist, incl. the five FEC bulk zips | `git checkout` restores them. |
| **Regenerable by the chain** | Root `*.json` engine artifacts (`ranks_python.json`, `category_stance.json`, …) plus `data\money\budget_frontier*.json` (path corrected 2026-09-30; verified against `fec/engine/budget_frontier.py:152-153`), `Moneyball Dashboard.html`, `cu-member-desk.html`, `Moneyball.html` | One `run_pipeline.py` run — but that is a MUTATING operation with its own protocol; see moneyball-run-and-operate. |

**`backups/` convention** (`ROOT\backups`, paths.py:11): workbook-mutating scripts copy the workbook first as `Moneyball Main Version - Blended.PRE-<TAG>-<timestamp>.xlsx` (one-shot tools) or `.BACKUP-<timestamp>.xlsx` (media blend); database surgery writes `social_media.PRE-<TAG>-<timestamp>.db`. If you write a new mutating script, backup-first with a `PRE-<YOURTAG>-` name is mandatory house style. The whole `backups/` dir is gitignored — backups live on disk/OneDrive only.

## 6. New-code conventions (house style for a new fec script)

Derived from the near-universal patterns across the 175 tracked scripts (counts as of 2026-07-09: 158 use the stdout reconfigure, 117 carry the coding header, 0 use `logging`, 20 have a `__main__` guard, 14 use argparse, 33 read/write `utf-8-sig`). A new script MUST look like this:

```python
# -*- coding: utf-8 -*-
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__))); from paths import ROOT as MB_ROOT
"""WHAT THIS SCRIPT DOES — one paragraph: purpose, inputs, outputs, and the decision/audit
that motivated it (docstrings are this repo's design log; date-stamp decisions)."""
import json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')   # Windows console is cp1252; this prevents UnicodeEncodeError
from moneyball_core import dump_atomic                        # atomic JSON writes (temp sibling + os.replace)

# env dials: default = production behavior, always overridable, comment the rationale
MYDIAL = float(_o.environ.get('MYDIAL', '0.5'))               # register it in moneyball-config-and-flags

def main():
    data = json.load(open(MB_ROOT + r'\congestion.json'))     # ALL paths via paths.py roots — never hardcode a tree
    ...
    dump_atomic(out, MB_ROOT + r'\my_artifact.json', indent=1)
    print('my_artifact.json: %d members, %d flagged' % (n, k))  # FINAL SUMMARY LINE — see logging contract

if __name__ == '__main__':
    main()
```

Checklist, with the reason each rule exists:

- [ ] **`# -*- coding: utf-8 -*-` header + `sys.stdout.reconfigure(encoding='utf-8', errors='replace')`** immediately after imports. Windows consoles default to cp1252; member names (Velázquez, Jesús García) and em-dashes crash unprotected `print` with `UnicodeEncodeError`.
- [ ] **Paths only via `paths.py`** (`from paths import ROOT`, or `WORKBOOK`/`BACKUPS`/`p()`), with the standard one-liner bootstrap shown above so the script works regardless of cwd. Never hardcode a tree, a scratchpad, or a session directory — two dials (`B5_SCRATCH`, `CMTE_ROSTER`) still carry dead hardcoded paths of long-gone worktree sessions as their defaults; don't add a third.
- [ ] **Print-only logging with a FINAL SUMMARY LINE.** There is no `logging` module anywhere. `run_pipeline.py` runs each chain step as a subprocess and displays **only the last stdout line** (run_pipeline.py:172–191; 800-char tails only on failure) — so your last print must summarize the run (artifact name + counts). Exit nonzero on failure; the runner hard-stops the chain on the first nonzero return code.
- [ ] **JSON artifacts via `moneyball_core.dump_atomic(obj, path, **kw)`** (moneyball_core.py:88–101) — temp sibling + `os.replace()`, atomic on NTFS. Motivated by real truncated-artifact incidents under OneDrive/Excel contention. Plain `json.dump(open(...))` is banned for anything another script reads.
- [ ] **CSV encoding: write `utf-8-sig`, and read `utf-8-sig` for any CSV Excel may have touched** (the BOM-tolerant codec; plain `utf-8` reads choke on Excel's BOM). Established pattern in the adjudication queues and Quorum outputs.
- [ ] **argparse only when the script actually has flags** (14 scripts do). Flagless scripts take no arguments at all. Some older scripts scan `sys.argv` bare — argparse is the preferred form for new code.
- [ ] **Know that import == execution is the repo norm** — most scripts run their whole body at module top level (only 20 of ~137 live scripts have a `__main__` guard) because the chain runner invokes them as subprocesses. For NEW code, add the `__main__` guard anyway (the pattern `per_topic_flip.py` uses): it costs nothing and prevents the classic incident where `build_social_master.py` line 18 does `from network.process_quorum import CU_TERMS` and thereby **re-executes the entire Quorum pipeline**. Corollary: never import a sibling script just for a constant — shared constants belong in `moneyball_core.py`.
- [ ] **Never hand-edit or hand-extend a generated JSON artifact** (session-ratified, 2026-07; PROJECT LAW 6). Incident: a hand-added 18th category in `category_stance.json` was silently clobbered by its producer. Change the producer instead.
- [ ] **Backup-first for any workbook or DB mutation** (section 5 convention), and **Excel must be closed** for workbook writes — openpyxl saves raise `PermissionError` if Excel holds the file.
- [ ] **New env dials**: hardcoded default = current production behavior (an empty environment must always reproduce production), read via `os.environ.get` at top of file with a rationale comment, then registered in the dial table owned by moneyball-config-and-flags.
- [ ] **LLM calls**: model choice is governed by the hard cost rule (Fable/Opus only for the 533 member narratives; Haiku 4.5 for every other LLM step) and the `--go` cost-gate pattern — details in moneyball-change-control.

## 7. Windows / OneDrive traps

| Trap | Symptom | Defense |
|---|---|---|
| cp1252 console | `UnicodeEncodeError` printing member names/em-dashes | The reconfigure boilerplate (section 6). Already present in 158 scripts. |
| Excel file lock | `PermissionError` on any workbook write while Excel is open; one run lost 400 paid labels rewriting a queue CSV Excel held | Close Excel before ANY workbook/CSV write. For paid outputs, write a sidecar file first and merge later (the `api_prelabel_tweets.py --merge` pattern). |
| OneDrive sync contention | Truncated files when a write races the sync client (a historical 2.2 MB truncated workbook save came from COM+OneDrive contention — recorded in the `fec/run_pipeline.py` docstring until `e3d2923d0` removed that note on 2026-07-15; read it with `git show 23c48ea46:fec/run_pipeline.py`, lines 9-11; corrected 2026-09-30, verified against `fec/run_pipeline.py:7-14`) | `dump_atomic` for JSON; backup-first for the workbook. `paths.py`'s docstring notes the escape hatch: relocating the whole project off OneDrive is a one-variable change (`MONEYBALL_ROOT`). |
| OneDrive sync lag | A file you just wrote looks stale on another machine / in a cloud view | Trust local mtimes, not the OneDrive web view; never run baselines while files are mid-sync. |
| SQLite WAL sidecars | `social_media.db-wal` / `-shm` appear next to the DB | Normal (collectors set `PRAGMA journal_mode=WAL` for concurrent readers/writers). Never delete the sidecars of a live DB; they're gitignored. |
| PowerShell 5.1 quirks | `&&` chaining fails; `-f`-formatted floats emit locale decimal commas (this silently broke the collector-supervisor's process scan once) | Chain with `;`, and never parse locale-formatted numbers — emit/consume raw integers. |
| Machine sleep kills crawls | Long collectors die overnight | Collectors hold wake locks; operation details in moneyball-run-and-operate. |
| openpyxl view-cache death | After any openpyxl save, formula cells read `None` until a human opens Excel (`fullCalcOnLoad` self-heals) | Read TYPED cells, respect chain ordering; see MATHEMATICAL_SPECIFICATION.md "Workbook contract" and moneyball-architecture-contract. |

## 8. From-zero checklist

Recreating a working setup on a (new) machine. Note there is no scenario where git alone suffices — you need the live data tree.

1. **Locate or sync the live data tree.** `C:\Users\pgoff\OneDrive\Desktop\Melange Systems` must exist and contain `congestion.json`, `ranks_python.json`, `Moneyball Main Version - Blended.xlsx`, `social_media.db`, and `backups\`. On a new machine this arrives via OneDrive sync of Paul's account — there is no other distribution channel. If any of those five are missing, STOP and consult section 5 (recovery class) before doing anything.
2. **Confirm `Draft Systems` is present** (sibling folder) if you will ever regenerate base data. Read-only; contains irreplaceable originals.
3. **Install Python 3.12.x** and the packages: run the pip line in section 3 (full tier if you'll touch research/audio code; `openpyxl` alone runs the chain and tests).
4. **From the live data tree, set no environment variables.** Empty environment resolves ROOT to that checkout. Set `MONEYBALL_ROOT`/`MONEYBALL_DRAFT` only if you are deliberately targeting another complete data tree.
5. **Verify the git overlay**: from the live root, `git status` should be clean-ish and `git ls-files | Measure-Object -Line` around 230 files (as of 2026-07-09). Worktrees live under `.claude\worktrees\` — remember their gitignored data plane is empty unless `MONEYBALL_ROOT` redirects it (section 2).
6. **Check for Paul's live jobs before running anything** (session-ratified, 2026-07; PROJECT LAW 5): look for running `python` processes and fresh artifact mtimes in the live root. Never run concurrently with his work.
7. **Run the kernel tests** (read-only: its only write is a temp file in `%TEMP%`):

   ```powershell
   python "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\fec\tests\run_tests.py"
   ```

   Expect `KERNEL TESTS — N passed, 0 FAILED` (count grows — trust the run's own tail). This command uses the live-tree script, so it exercises the kernel against the LIVE artifacts — a pass certifies the interpreter, the imports those tests exercise, their resolved data inputs, and path resolution. **The tested environment is now working.** Anything beyond this (running the chain, collectors, audits) is operations: load moneyball-run-and-operate first.

## Provenance and maintenance

Written 2026-07-09 against the live tree / worktree `claude/nifty-cray-f6d053` (HEAD 88a7048). Every volatile fact above carries a re-verification command here — paste from the repo root (`cd "C:\Users\pgoff\OneDrive\Desktop\Melange Systems"`; Git-Bash/`sh` syntax for the grep lines).

| Fact | Re-verify with |
|---|---|
| Ignore rules & whitelist | `git show HEAD:.gitignore` and `git ls-files | grep -vE '\.(py|md)$'` |
| `cu_valence_registry.json` force-tracked despite `*.json` ignore | `git check-ignore -v --no-index cu_valence_registry.json` (matches `.gitignore:6`) + `git ls-files cu_valence_registry.json` (still listed) |
| paths.py roots + env overrides | `sed -n '1,12p' fec/paths.py` |
| Canonical dependency manifest | read `requirements.txt`; compare its production packages with `CANONICAL_DEPENDENCIES` at `fec/run_pipeline.py:78-95` |
| Python version | `python --version` |
| Package usage counts / no `requests`/`bs4`/`logging` | `grep -rlE '^[^#]*\b(import|from) (requests|bs4)\b' fec | wc -l` (expect 0); `grep -rl "^import logging" fec | wc -l` (expect 0); per-package: `grep -lE '^[^#]*\b(import|from) openpyxl\b|^\s*import .*\bopenpyxl\b' fec/*.py | wc -l` |
| Installed versions | `python -m pip list` |
| Key files present/absent | `ls fec/govinfo_key.txt fec/anthropic_key.txt fec/votesmart_api_key.txt` (first two exist, third absent — but its absence says nothing about Vote Smart route status; see §4) |
| Vote Smart key is file-not-env | `sed -n '1,25p' fec/members/votesmart_npat_fetch.py` |
| cu_rollcall CSV has no in-repo producer | `grep -rn "cu_rollcall" fec` (only the `read_csv` consumer at vote_by_category.py:42) |
| FEC zips consumed only by attic | `grep -rln "ccl24\|weball24\|cn24\|cm24\|pas224" fec` |
| Convention counts (reconfigure 158 / coding header 117 / main-guard 20 / argparse 14 / utf-8-sig 33) | `grep -rl "sys.stdout.reconfigure" fec | wc -l`; `grep -rl '^# -\*- coding: utf-8 -\*-' fec | wc -l`; `cd fec && grep -l __main__ *.py tests/*.py | wc -l`; `grep -l "import argparse" fec/*.py | wc -l`; `grep -l "utf-8-sig" fec/*.py | wc -l` |
| Last-line-only logging contract | `sed -n '46,50p' fec/run_pipeline.py` |
| dump_atomic semantics | `sed -n '88,101p' fec/moneyball_core.py` |
| Kernel test count (count grows — trust the run's own tail) | run the tests and read the final count line |
| launch.json ports | `git show HEAD:.claude/launch.json` |
| retiring_members.txt semantics | `head -10 fec/retiring_members.txt` + `grep -n "retiring_members" fec/members/receptivity_layer.py` |
| Draft Systems disclaimer | `sed -n '88,89p' README.md` |
| Volatile README counts (tests 84, audit 136 as of 2026-07-19) | compare README.md's running-command comments with actual run output — if those lines change, recheck this skill's numbers too |

Last measured (dated — counts drift, so trust each run's own tail): `fec/tests/run_tests.py` 247 passed / 2 FAILED in LIVE on 2026-09-20 (standing reds `test_bill_collision_guards`, `test_make_staffer_network_html`); `fec/audit/audit_full.py` 559 passed / 9 FAILED in LIVE on 2026-09-19 (after that day's membership refresh) (both recorded in the Project Brain STATE); the chain has 80 `CHAIN` entries, 79 run by default (`fec/run_pipeline.py:45-302`), counted 2026-09-30 at main 25eefa3fc.
