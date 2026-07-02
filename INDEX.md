# Moneyball — Project Index

## The deliverable
- **`Moneyball.html`** — the single combined dashboard (SNA network + member desk). Open this.

## Source of truth
- **`Moneyball Main Version - Blended.xlsx`** — the workbook. Ranks, scores, per-category stance, committee
  data, and the pillar weights (`Blended Model!AB2:AB5`) all live here. Everything downstream is generated from it.

## Regenerate the dashboard (run after any workbook change), from `fec/`:
```
python build_dashboard_bundle.py     # workbook -> dashboard_data.json (SNA bundle)
python make_dashboard_html.py        # -> Moneyball Dashboard.html
python make_member_desk.py           # workbook -> member_desk_bundle.json + cu-member-desk.html
python make_combined.py              # merges the two -> Moneyball.html
```
(`optimize.py` regenerates `optimize_result.json` independently of the workbook.)

## Current model config (2026-07-01, live-verified)
- **Score weights** (`Blended Model!AB2:AB5`, set via `apply_weights.py`): **Legislative 0.25 / Press 0.30 /
  Committee·Influence 0.40 / Demo 0.05** (read live from the workbook 2026-07-01 — weights oscillated across
  the 6/29–6/30 sessions; ALWAYS verify against the live cells, not this doc). Committee-weighted because press
  as the lead pillar was a tone/visibility proxy that mis-ranked the real power players. Committee = structural
  CU power. NOT a pure influence ranking — underdogs surface in the separate Intrinsic/Visibility/Undervaluation/
  Underdog-rank columns + the optimizer (the Moneyball layer). Allocator: Pot $2M, Fund-top-133, uncapped
  (the $10k/member cap config exists in `apply_alloc_cap.py` but is NOT applied).
- **Committee/Influence pillar**: `Blended Model!R` (col18) = **committee_raw / MAX(committee_raw)** (`apply_committee_fix.py`)
  — was a double percentile-rank that flattened a backbencher (score 2.5) up to the 90th percentile alongside chairs;
  the normalized raw score distinguishes leadership/seniority (Crapo #1, Tim Scott #2; Byron Donalds dropped #8→#14).
- **Press pillar**: CLEAN — bills DE-DUPED out (`apply_press_dedup.py`), real CU press only. The billstatus rows are
  also hidden from the press display (`billstatus:` skip in make_member_desk). They were synthetic one-liners, not articles.
  KNOWN ISSUE: the DEBATE sentiment model mislabels some articles (reads procedural negativity like "prohibit"/"disapproval"
  as anti-CU stance). **Corrections handoff:** add entries to **`press_stance_overrides.json`** (match by `url` or
  `title_contains`, `stance` = support|oppose|neutral); make_member_desk applies them to the press DISPLAY on regen.
  (Correcting the press PILLAR/ranks additionally needs the upstream press_value re-flowed.)
- **Legislative pillar**: STANCE-GATED / directional (`apply_leg_stance.py` → Blended col4 = per-topic activity ×
  per-category stance sign × importance). Opponents' activity counts AGAINST them; active allies stay positive.
  Result: Williams #1, Tim Scott #5, Lummis #12, Crapo #13; opponents AOC #211, Welch #175, Marshall #184, Lofgren #515.
- **Overall stance**: importance-weighted aggregate of the per-category Champion→Opponent tiers (10-tier ladder +
  Defender) — the member-desk stance LAYER, a separate alignment axis from the influence rank. Resync col G after
  IMP/matrix changes with **`sync_stance_g.py`** (safe, col-G-only — `sync_stance_clean.py` restores a pristine
  backup that would WIPE the leg-stance col D; do not run it as-is).
- **Issue importance (IMP) — ABB26-anchored (2026-07-01)**: weights re-tiered to America's Credit Unions'
  2026 Advocacy Priorities handout. Tax Status 3.0 / Credit Card Mandates 3.0 / Interchange 2.0; named
  priorities 1.0 (NCUA & regulatory regime, Field of Membership, Charter Modernization, Data Privacy, CFPB)
  or 0.75 (Exam & Supervision, Payments, Technology & Emerging, Fraud Prevention); unlisted unchanged.
  ⚠ IMP is duplicated in SIX files (apply_leg_stance, sync_stance, sync_stance_clean, sync_stance_g,
  build_dashboard_bundle `_IMP`, corrected_signals `AREA_IMP`) — keep all copies in sync.
- **CU Tax Status = 18th category** (the ABB26 flagship Protect priority; was a taxonomy gap): Category Stance
  sheet col T + category_stance.json cats/matrix/scores — all `—`/0.0 scaffolding until data collection tags
  tax bills & press (LEGPRE prefix pre-wired). No legislative block yet, so it does not enter the flip engine.
- **Joint allocation**: `optimize.py`, **BUDGET $2.5M total** (user 2026-07-01) — THE allocation of record,
  computed jointly across all issues; prints a Golovin-Krause data-dependent optimality certificate. The
  per-topic $2M tools (per_topic_flip/coalition) are per-issue diagnostics, not additive budgets. (The
  workbook rank-based pot is still $2M/top-133 — not yet synced to $2.5M, pending user decision.)
- **Money defection**: walks the FULL 10-rung overall ladder (one DTHRESH=11.25 crossing = one rung);
  only terminal Champion/Opponent are immune — Highly Skeptical is deep but movable.

## Live data files (read/written by the pipeline — DO NOT move)
`dashboard_data.json`, `member_desk_bundle.json`, `member_desk_src.json`, `category_stance.json`,
`congestion.json`, `optimize_result.json`, `confidence.json`, `archive_leg.json`, `electoral*.json`,
`budget_frontier*.json`, and **`congress_cosponsor_network_*.xlsx`** (globbed — the latest by mtime is used).

## Scripts (`fec/`)
- **Pipeline**: `build_dashboard_bundle.py`, `make_dashboard_html.py`, `make_member_desk.py`, `make_combined.py`
- **Engine**: `flip_model.py`, `money_response.py`, `optimize.py`, `lt_priming.py`, `scenario.py`,
  `per_category_stance.py`, `aggregate.py`
- **One-off model edits** (COM writes to the workbook, then recalc): `apply_press_dedup.py`, `apply_weight_swap.py`,
  `apply_leg_stance.py`, `sync_stance_clean.py`
- **Audits / diagnostics**: `audit_*.py`, `_diff_bm.py`, `_verify_clean.py`, `method_audit.py`, `category_audit.py`, etc.

## Folders
- **`backups/`** — workbook safety copies (`*.PRE-*.xlsx`). To revert a model change, copy the relevant one back
  over `Moneyball Main Version - Blended.xlsx` and regenerate. Newest-to-oldest: PRE-LEGSTANCE → PRE-WEIGHTSWAP →
  PRE-PRESSDEDUP → PRE-STANCESYNC → PRE-STANCEGUARD.
- **`archive/`** — stale dated intermediate exports (old leg-score / press-scoring / Ballotpedia snapshots). Not
  read by the live pipeline.

## Rank snapshots (root, CSV)
- `Moneyball - New Ranks (press de-dup).csv`, `Moneyball - New Ranks (leg-stance).csv`, `bills_audit.csv`, `stance_audit.csv`.


## Salience + press-SNA layers (2026-07-01)
- `fec/salience_shock.py` — Noble–Turner going-public shock engine; `--advise` writes `salience_advisory.json` (go-public vs quiet-work verdicts, defensive-appeal holds).
- `fec/press_hcoi.py` → `press_hcoi.json` — hidden communities of interest from press topic profiles (+ genealogy; D4 partial fix).
- `fec/press_engagement_layer.py` → `press_engagement.json` — Fink-normalized press-mention influence probabilities.
- `fec/stance_dynamics.py` → `stance_dynamics.json` + `stance_imputation_proposals.csv` — quarterly stance trajectories, flip curves, seven-dynamics taxonomy, network-imputed stance PROPOSALS (user adjudicates).
- `fec/frame_alignment.py` → `frame_alignment.json` — coordinated-messaging (duplication) index + party framing chi-squared.
- `fec/build_multilayer_network.py` → `congress_cosponsor_network_AUG*.xlsx` — LIVE multilayer cascade graph (cosponsor + engagement + isolated-incident HCoI); revert = delete the AUG file.
- `fec/stance_template_xval.py` → `stance_templates_review.md` + `stance_template_variants.csv` — template cross-validation (T1 kappa 0.529; B-section circularity caveat) + S3 NLI paraphrase set.
- `fec/prepare_stance_training.py` + `fec/train_stance_domain.py` — Khan-et-al stance pipeline on the user's AUGMENTED two-hop label set (`stance_training.jsonl`; LinearSVM 0.792 macro-F1; --transformer fine-tune; --save -> stance_clf_composed.pkl).
- ADJUDICATED BENCHMARK: `stance_eval.py` on the corrected gold queue — DEBATE 0.430 vs API pass 0.750 macro-F1.
- `tweet_collector.py` extended: Truth Social adapter (TRUTH_TOKEN), X keyword `search`, CU_TERMS relevance filter, `classify` -> social_stance_signals.json.
- `fec/tweet_collector.py` + `social_media.db` — X/Bluesky collector, handle discovery, Fink influence builder.
- Dashboard System-shocks exec cue is now Noble-structured (engine.sal per issue; party-asymmetric, regime-weighted).

## Known issues / open questions
1. **Rank conflates influence and alignment.** The blended score mixes "how much power a member has" with
   "are they pro-CU." High-influence opponents (e.g. active consumer-finance legislators opposed to CUs) rank
   high. Read rank as influence; use the stance layer as the friend/foe filter.
2. **Legislative pillar is stance-gated but "muted"** (state as of 2026-07-01: `apply_leg_stance.py` gating is
   ON — col D = stance-signed leg raw, opponents go negative — but the PERCENTRANK normalization compresses the
   signal, so a disengaged opponent still lands mid-board on Leg% alone; the 7/1 press own-domain-attribution
   fix is what actually ranks opponents low (AOC #344 / Welch #374 / Marshall #473). A winsorized normalizer
   (÷ 90th-pct magnitude) would make leg bite harder if ever wanted. A fully clean directional leg pillar would
   need per-bill CU positions (data only has ~1,300 of ~11,000 cosponsorships).
3. **Bills are counted in the press pillar but hidden from the display.** They double-count cosponsorship as
   "press," but the user wants them counted (kept the dense pillar) — only the dead-link articles are hidden.
