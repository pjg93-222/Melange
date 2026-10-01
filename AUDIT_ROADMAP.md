# Moneyball — Self-Audit Roadmap

A file-by-file review plan. Folder: `C:\Users\pgoff\OneDrive\Desktop\Melange Systems\`
Python scripts in `fec\`, data as root `*.json`, master workbook `Moneyball Main Version - Blended.xlsx`.

**How to use:** go phase by phase. For each file: read the code, then check the "VERIFY" bullets. 🟡 = recently calibrated/changed (highest scrutiny). 📐 = the math is documented in `MATHEMATICAL_SPECIFICATION.md` — read the matching section alongside the code.

Suggested split: **Weekend = Phases 0–2** (orient + data + core models). **Next week = Phases 3–7** (allocation, tools, electoral, dashboard, the calibration).

---

## Phase 0 — Orientation (start here, ~1 hr)
1. **`MATHEMATICAL_SPECIFICATION.md`** — the formula bible. Every equation, constant, and data source. Read it once end-to-end; keep it open as your reference for every later phase.
2. **`README.md`** — the module map + how to run things.
3. **Run the three audits** (they're the system's own checks — confirm they're green before you trust anything):
   - `python fec/audit/legacy_workbook_audit.py`  → integrity (22 checks)
   - `python fec/audit/audit_frontier.py`  → budget frontier (11 checks)
   - `python fec/audit/audit_full.py`  → full-body (31 checks; runs the others + scenario/optimizer/frontier)
   These tell you the system is internally consistent. Your job in the later phases is to check it's *correct*, which the audits don't fully cover.

---

## Phase 1 — Source data & integrity (the foundation; if this is wrong, everything is)
- **`fec/full_congestion.py`** (+ `final_congestion.py`) → `congestion.json`. FEC money: aggregates bank/finserv/CU PAC dollars from `itpas2.txt` (24K/24Z transactions) over a **hardcoded set of ~33 major industry PAC committee IDs**, joined name→bioguide→FEC-candidate via `legislators.csv`; receipts from `weball24.txt`.
  - VERIFY: the BANKS/FINSERV/CU committee-ID lists are the right majors (they are: ABA, Citi, Wells, JPM, BofA, Visa, MC, Amex…). The `resolve()` name→bioguide matching. **`ind=0` ≠ no opposition** — it means "no money from the *tracked* PACs" (real for ~91 no-corporate-PAC members; verified via the FEC gap-test).
- **`congestion.json`** — per-member cu/banks/finserv/receipts/total + the derived net_lean. VERIFY: 533 members; how many have `total=0` (no FEC record, 63) vs `receipts=0` (truly blind, 18).
- **`category_stance.json`** (built by `fec/stance/per_category_stance.py` / `write_category_stance.py`) — the **533 × 17 stance matrix** (the 3rd dimension). VERIFY: the per-issue tiers (Champion…Opponent, `—`), the `defensive` set, the leg/press/votes blend weights. 📐 §"per-category stance".
- **`Moneyball Main Version - Blended.xlsx`** — the upstream stance/score source (Blended Model col 19 = score; Rank & Allocation col 7 = overall tier; Legislative Score - Normalized = per-block engagement). VERIFY: rows 3–535 = the 533 members (no header bleed, no dup names).
- **`congress_cosponsor_network_*.xlsx`** (newest by mtime) — the cosponsorship network edges (bioguide-keyed). VERIFY: edge weights, the bio2name join coverage (~41 members are network-isolated).
- **`bipartisan.json`** (bpf), **`electoral.json`** (security/leverage), **`confidence.json`** (data-coverage per member), **`archive_leg.json`** (legislative pillar). VERIFY: member-set consistency = 533 across all.
- **Cross-cutting integrity check:** member set is exactly 533 everywhere; the imputations (below) are applied where intended and nowhere else.

---

## Phase 2 — Core influence models 🟡📐 (the heart — these were just calibrated)
- **`fec/engine/flip_model.py`** 🟡 — the shared Linear-Threshold **winnability** `pflip = a/(a+b)`. Imported by scenario + optimize + dashboard. 📐 §"flip / winnability".
  - VERIFY: `WM=0.35 / WP=0.65` (money now the minority partner — CALIBRATED); the **compressed `PERS`** tiers (~3:1 spread); `cpf` is now **source-ALIGNMENT** (co-partisan ×1.7 / out-partisan ×0.5) in nA/nB; `tgt` has the **passage bonus** ×(1+0.3·bpf); the **H3 imputation** (median industry for `receipts=0` members only — `ind_imputed`); the capacity-aware money term `(cu+1)/((cu+1)+HALFF·R)`.
- **`fec/engine/money_response.py`** 🟡 — money→lean curve + defection. 📐 §"money/defection".
  - VERIFY: `MAXSHIFT=18` (CALIBRATED from 40), `HALF=0.10`, `DTHRESH=15` (money flips now rare, not impossible); `receipts()` imputes **median receipts** for no-data members (HIGH-2 fix); `defection()` uses the overall 5-tier `ORDER`.
- **`fec/engine/per_topic_flip.py`** 🟡 — per-issue flip allocation → `per_topic_alloc.json`. Mirrors flip_model's calibration (WM/WP, PERS, cpf→align, passage bonus). VERIFY it stays numerically consistent with flip_model.
- **`fec/engine/per_topic_coalition.py`** 🟡 — competitive Independent-Cascade **coalition** spread → `per_topic_coalition.json`. 📐 §"competitive cascade".
  - VERIFY: `cpf` is now **damping** (cross-party ×0.4–1.0, CALIBRATED — was an amplifier); `BSCALE=400000`; edge prob `(w·cpf)/(w·cpf+6)`; the splitmix64 `_sm` CRN (deterministic); `BETA_C=0.8` bipartisan seed-boost (the "passage" side).

---

## Phase 3 — Allocation & optimization 🟡📐
- **`fec/engine/budget_frontier.py`** 🟡 — nested **CELF greedy** budget frontier (coalition + `--electoral` contest/defend) → `budget_frontier.json` / `budget_frontier_electoral.json`. 📐 §"budget frontier".
  - VERIFY: cpf damping + edge prob +6 + BSCALE 400k (CALIBRATED); the (1−1/e) greedy; the diminishing-returns knee; the electoral contest/defend integration. **Trap:** regenerate the `_electoral` version whenever you regenerate the coalition one (they must share calibration, or audit_frontier flags the base-discount check).
- **`fec/engine/optimize.py`** — adaptive (Golovin-Krause) optimizer → `optimize_result.json`. VERIFY: the `won`/`secured` accounting (a conversion is a GAIN — path is monotone); CELF == exhaustive greedy; `INC` min-chunk + `PMAX` cap. Note: money-conversions are now rare (DTHRESH 15 + MAXSHIFT 18).
- **`fec/engine/build_im_allocation.py`** → `im_allocation.json` (FLIP = per_topic_alloc row-sums, COALITION = per_topic_coalition row-sums). **`fec/surfaces/write_im_sheet.py`** pushes it to the workbook's "IM Allocation" sheet (COM; needs Excel closed). VERIFY the sheet matches the live per-topic model.

---

## Phase 4 — Pathfinding & campaign tools 🟡📐
- **`fec/engine/cosponsor_route.py`** 🟡 — multi-objective **recruitment routes** (RELINK edge-IM, Pareto over cosponsors/$/risk). VERIFY cpf damping + edge prob +6 (CALIBRATED).
- **`fec/engine/lt_priming.py`** 🟡 — **flip-a-member**: cheapest pressure + money to tip a target. 📐 §"LT priming". VERIFY: `MAXSHIFT=18`; widened `THETA` (Skeptic 2.0, +Opponent 3.0); cpf damping + edge prob +6; `dollars_for_units` (FEC-bounded).
- **`fec/engine/scenario.py`** 🟡 — end-to-end **what-if runner** (money/defection/stance shocks → cascade + flip deltas). VERIFY: cpf damping, BSCALE 400k, edge prob +6; the `_sm` true-CRN cascade; both channels sign-sane (a competitor shock lowers both).

---

## Phase 5 — Electoral layer 🟡📐
- **`fec/engine/build_electoral.py`** 🟡 → `electoral.json`: `leverage = 1 + LELEV·(1−security)`, `LELEV=0.8` (CALIBRATED → max 1.8×). Security from Ballotpedia election-average data.
- **`fec/engine/build_electoral_plays.py`** → `electoral_plays.json`: per-member **contest (primary vs general route)** / **defend** / none. VERIFY: the non-partisan primary-default routing; `route='primary' if primary≥general else 'general'` (43 primary / 10 general — the generals are the competitive seats); party balance.

---

## Phase 6 — Dashboard
- **`fec/surfaces/build_dashboard_bundle.py`** → `dashboard_data.json` (columnar, minified). Bakes the network layout, stances, flip/coal allocations, frontier paths, electoral plays, the optimizer result, AND the `engine` block (full adjacency + per-member money + eng matrix + all calibrated constants) for the in-browser engine. VERIFY: 19 issues (incl. "Overall CU stance"); the engine `const` reflects the calibration (WM 0.35, MAXSHIFT 18, DTHRESH 15, BSCALE 400k, SRCPRO 1.7, SRCANTI 0.5, DCROSS 0.4).
- **`fec/surfaces/make_dashboard_html.py`** → `Moneyball Dashboard.html`. The UI + the **in-browser engine** (faithful JS port of flip + cascade + priming + pathfinder). VERIFY: `cpf` (damping) for diffusion vs `align` (source) for the flip; edge prob +6; the `engine ✓` self-check badge matches Python per issue. **This is a port — confirm it tracks the Python** (the badge is the live check).
- **`Moneyball Dashboard.html`** — open it; click a member; try the pathfinder modes (Path / Best / Multi / Budget), the scenario sliders, the head-to-head, the system shocks (dropout / executive), and Issue → "Overall CU stance".

---

## Phase 7 — The calibration (HIGHEST scrutiny — the most recent, most consequential change) 🟡
Read `project`-level rationale in `MATHEMATICAL_SPECIFICATION.md` and decide if you agree with each magnitude. These are **evidence-anchored, not statistically fitted** — judgment values, all `env`-overridable.
- **Money is weak** (MAXSHIFT 40→18, WM 0.6→0.35): from the "money buys access not votes" consensus (Ansolabehere; Fowler-Garro-Spenkuch; Kalla-Broockman). Sanity-check: does a realistic donation move a position only a little?
- **Persuadability compressed** (~10:1 → ~3:1; `—` → 0.50): Coppock "parallel publics"; Kalla-Broockman minimal effects.
- **Cross-party flipped** (amplifier → damping in DIFFUSION; bonus moved to PASSAGE): homophily evidence (Harmon; Andris) vs Volden-Wiseman (bipartisan *bills* advance). Check the two are in the right places.
- **Source-alignment added** (co-partisan ×1.7 / out ×0.5 in the flip): Furnas; Bakker.
- **LELEV 1.8×, BSCALE 400k, edge-prob +6, THETA widened.**
- **To compare pre/post:** backups of all 11 pre-calibration files are in the scratchpad `calib_backup/` folder; or set the `env` overrides (e.g., `MAXSHIFT=40`, `WM`… ) to flip individual changes back and diff outputs.

---

## Appendix

**Auxiliary audits you can also run** (deeper, single-aspect): `fec/category_audit.py`, `fec/per_category_deep_audit.py`, `fec/coverage_audit.py`, `fec/data_confidence.py`, `fec/engine/method_audit.py`.

**Regenerate the whole pipeline** (after any data/param change), in order:
`build_electoral.py → build_electoral_plays.py → per_topic_flip.py → per_topic_coalition.py → budget_frontier.py → budget_frontier.py --electoral → optimize.py → build_im_allocation.py → build_dashboard_bundle.py → make_dashboard_html.py`, then `audit_full.py`.

**Legacy / one-off / scratch — safe to SKIP** (superseded or exploratory; not in the live pipeline): `final.py`, `final_table.py`, `makeup.py`, `makeup2.py`, `recheck2.py`, `durbin_sanity.py`, `aggregate.py`, `map_to_model.py`, `compute_fp_clean.py`, `im_allocate.py`, `im_allocate2.py`, `assemble_viz.py`, `saturation.py`, `match_committees.py`, `vote_by_category.py`, `final_congestion.py` (use `full_congestion.py`). Root `_*.json` and the many timestamped `*_HHMMSS.xlsx` are intermediates — the newest / un-suffixed ones are canonical.

**Known honest limitations to keep in mind** (not bugs — documented trade-offs): the model is methodologically grounded but only *partially* empirically fitted; `ind=0`/`receipts=0` imputations; the dashboard cascade's bystander RNG differs from Python (Δ is clean, absolute spread indicative); network-isolated members; the workbook IM sheet lags until `write_im_sheet.py` is pushed.
