# Melange Systems

Credit-union legislative-influence modeling & money-allocation system (the "Moneyball" project).
Everything needed to run the system lives in this folder; paths are self-contained here.

## Layout
- `fec/` — all Python modules (the engine + scenario tools + audits)
- `*.json` — derived data the modules read/write (stance matrix, frontiers, electoral plays, etc.)
- `Moneyball Main Version - Blended.xlsx` — the master workbook (stances, money, allocations, the `Melange - Live` tab)
- `Moneyball Dashboard.html` — standalone interactive network dashboard
- `votes/` — voteview member files (party lookup)
- `baseline/` — frozen baseline snapshot for scenario diffs
- `research/` — the two papers the pathfinding work is built on

## The model (three layers)
1. **Per-category stance** (`per_category_stance.py` → `category_stance.json`): each of 533 members scored on 17 issues, self-calibrating thresholds (median+IQR, rate-bounded). Legislative pillar rebuilt from the bills archive (not the frozen sheet); offensive issues use Champion tiers, defensive issues (Interchange, Credit Card) use **Defender** tiers (press-led). Neutral split into Highly-Persuadable / True-Neutral / Lean-Skeptic.
2. **Influence allocation** — two competitive models:
   - **Coalition (Independent Cascade)** — `budget_frontier.py`: nested CELF greedy, core champions free then cautious expansion; `--electoral` mode adds **contest** (primary a hostile incumbent) and **defend** (insure a competitive ally) plays. Pareto-style multi-objective routing in `cosponsor_route.py` (RELINK edge-activation + MOPBD* fronts).
   - **Flip (Linear Threshold)** — `per_topic_flip.py` + `lt_priming.py`: the cheapest balance of network pressure + money to tip a member over their co-sponsor/flip threshold.
3. **Scenario layer** — `money_response.py` (saturation/capacity-aware money curve + money-triggered defections), `cosponsor_route.py` (multi-objective recruitment routes), `lt_priming.py`, `sheet_sync.py` (live workbook tab + D*-Lite incremental replanning).

## Research basis (`research/`)
- **RELINK (Closed-Network IM, CIKM'25)** — edge-activation IM under a per-member out-degree budget → the co-sponsor route finder.
- **Multi-Objective Path-Based D\* Lite** — incremental multi-objective path planning → the Pareto routes + the incremental sheet sync (recompute only changed slices).

## Key modules (`fec/`)
| Script | Produces | Notes |
|---|---|---|
| `per_category_stance.py` | `category_stance.json` | the 533×17 stance matrix |
| `build_archive_legislative.py` | `archive_leg.json` | legislative pillar from bills archive |
| `budget_frontier.py` | `budget_frontier[_electoral].json` | nested coalition frontier; `--electoral` toggles contest/defend |
| `build_electoral.py` / `build_electoral_plays.py` | `electoral.json` / `electoral_plays.json` | competitiveness + non-partisan contest/defend plays |
| `flip_model.py` | (shared module) | capacity-aware Linear-Threshold winnability `pflip`; imported by scenario + optimize |
| `money_response.py` | (callable) | money→lean curve + defection rule (same receipts-saturating curve as flip_model) |
| `cosponsor_route.py` | (stdout/Pareto) | multi-objective recruitment routes; `MCMODE=1` for exact reach |
| `lt_priming.py` | `lt_priming.json` | cheapest pressure+money to flip each target |
| **`scenario.py`** | (stdout) | **end-to-end scenario runner** — `--money/--defect/--stance`; reports BOTH coalition + flip influence change vs baseline |
| **`optimize.py`** | `optimize_result.json` | **adaptive budget optimizer** (Golovin-Krause) — greedily allocates a CU budget; observes conversions and re-optimizes. `INC`=min chunk, `PMAX`=per-member cap |
| `sheet_sync.py` | `Melange - Live` tab | COM write-back + incremental change detection |
| `make_baseline.py` / `scenario_diff.py` | `baseline/` | freeze + diff scenarios |
| `audit.py` / `audit_frontier.py` / `audit_full.py` | reports | integrity (22) / frontier (11) / **full-body (29)** |

## Running
- Determinism: coalition/route use a fixed seed + CRN + sorted cascade — same-seed runs are identical, so a scenario vs baseline at the same seed isolates the real effect.
- Full audit: `python fec/audit_full.py` (should report **29 passed, 0 FAILED**).
- Key dials (env vars): `MAXSEEDS`, `REPFAC`, `LELEV`, `LEV`, `MC`, `MCMODE`, `K`, `CEDGE`, `MAXSHIFT`, `HALF`, `DTHRESH`, `SEED`.

_Note: the upstream raw data (FEC source files, press indexes, fine-tuned debate models, old workbook versions) was left in the original `Draft Systems` folder — it's only needed to regenerate base data, not to run the system, and includes large/irreplaceable files._
