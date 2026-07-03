# Melange Systems

Credit-union legislative-influence modeling & money-allocation system (the "Moneyball" project).
533 members × **18 issue categories**; rank lives in the workbook, influence engines in Python.
*(Refreshed 2026-07-02 — the previous README predated the architecture refactor; see git history.)*

## Layout
- `fec/` — the engine. Entry points: **`run_pipeline.py`** (canonical chain), **`moneyball_core.py`**
  (shared kernel: rosters, network loader, the TWO partisan physics, CRN, constants),
  **`paths.py`** (roots; `MONEYBALL_ROOT`/`MONEYBALL_DRAFT` env overrides).
- `fec/tests/run_tests.py` — kernel invariant checks (currently 30). `fec/attic/` — retired scripts.
- `fec/templates/` — dashboard HTML/JS templates. `backups/` — workbook backups (auto, pre-write).
- `Moneyball Main Version - Blended.xlsx` — the rank workbook (system of record; user dial sheets:
  Topic Weights, Category Stance). `votes/` — voteview rosters. `research/` — the source papers.
- Root `*.json` — derived artifacts (regenerable; all writes are atomic via `MC.dump_atomic`).
- `social_media.db` — posts, member↔member interactions, floor speeches + hearing transcripts.

## The model (five layers)
1. **Stance** (`per_category_stance.py` → category_stance.json): 533×18 self-calibrating matrix;
   defensive issues (Interchange, Credit Card Mandates) are Defender-tiered. `sync_stance_g.py`
   aggregates to the workbook's overall tier (col G) with the ABB26 IMP weights.
2. **Media** (`build_media_blend.py`): press pillar = 50% press + 50% social (p80-scaled, tiered
   category weights from the Topic Weights sheet, exp decay 2.0y/0.5y, RT×0.5, thin-cat shrink).
3. **Network** (`build_multilayer_network.py`): cosponsorship + press engagement + HCoI + social
   repost/mention edges (Fink-normalized; new links AND +30%-capped reinforcement).
4. **Receptivity** (`big5_traits.py` → `receptivity_layer.py`): Big Five from 6.6M words of floor
   speech/hearings/posts → susceptibility (Byrne), electoral incentive (Fouirnaies-Hall), prospect-
   theory domain (Linde-Vis), contingency seed-gates (stance-graded).
5. **Influence engines**: coalition cascades (`budget_frontier.py` [+`--electoral`],
   `per_topic_coalition.py`), Linear-Threshold flips (`flip_model.py`, `per_topic_flip.py`,
   `lt_priming.py`), adaptive $ optimizer (`optimize.py`, Golovin-Krause), going-public advisory
   (`salience_shock.py`, Noble-Turner), scenario runner (`scenario.py`), routes (`cosponsor_route.py`).

## Running
```
python fec/run_pipeline.py [--from <step>]   # the whole chain, audited at the end (NO Excel/COM involved)
python fec/tests/run_tests.py                # 30 kernel checks (run after ANY code change)
python fec/audit_full.py                     # full-body audit, 52 checks (expect ALL MODULES CLEAN)
```
**Rank authority = `ranks_python.json`** (phase 2): Python computes the entire rank chain;
the workbook is a view that recalculates itself when opened in Excel (fullCalcOnLoad). Edit dials
(Topic Weights / Category Stance / AB weights) in Excel as always — saving in Excel refreshes
everything the pipeline reads.
Verification protocol for code changes: kernel tests → pipeline → **zero rank delta** vs the last
`ranks_*.json` (unless the change is supposed to move ranks) → audit clean.
Data refresh order: collectors (`fetch_congressional_record.py`, `tweet_collector.py`, Quorum) →
`big5_traits` → `social_interaction_layer` → `build_multilayer_network` → `build_media_blend` →
`run_pipeline --recalc`. Determinism: SEED=7, MC=20, splitmix64 CRN — same-seed runs are identical.

## Data collectors
- `fetch_congressional_record.py` — CREC floor speeches (keyless date-driven) + CHRG finance
  hearings (GovInfo key in `fec/govinfo_key.txt`); resumable; witness-collision-safe attribution.
- `tweet_collector.py` — X/Bluesky/Truth Social handles, posts, interactions.
- `process_quorum.py` / `build_social_master.py` — Quorum export pipeline → Social Master.
- `rebuild_press_cache.py` — recovery path for the media-blend press cache (refuses post-blend sources).
- `build_staff_directory.py` — weaves the Quorum staffer exports into staff_directory.json (5,773 staffers
  matched to all 533 offices); feeds the member desk's Staff section + In-contact panel.

## Diagnostics-only artifacts (confirmed 2026-07-02)
`stance_dynamics.json`, `social_stance_signals.json`, `tweet_influence.json`, `imviz.json`,
`corrected_signals.json`, `social_member_summary.json`, `cu_golden_labels_stats.json` are
human-inspection outputs with no live consumer — safe to regenerate anytime, never load-bearing.

## Canonical docs
`MATHEMATICAL_SPECIFICATION.md` (law of the system: authoritative-code table, conventions, dials) ·
`ARCHITECTURE_REVIEW_2026-07-02.md` · `AUDIT_FINDINGS_2026-07-02.md` · `INDEX.md`.

_Upstream raw data (FEC source files, press indexes, old workbooks) lives in the original
`Draft Systems` folder — needed only to regenerate base data, includes irreplaceable files._
