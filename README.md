# Melange Systems

Credit-union legislative-influence modeling & money-allocation system (the "Moneyball" project).
533 members × **18 issue categories**; `ranks_python.json` is the rank authority and the
influence engines are Python-owned.
*(Runbook refreshed 2026-07-15.)*

## Layout
- `fec/` — the engine. Entry points: **`run_pipeline.py`** (canonical chain), **`moneyball_core.py`**
  (shared kernel: rosters, network loader, the TWO partisan physics, CRN, constants),
  **`paths.py`** (roots; `MONEYBALL_ROOT`/`MONEYBALL_DRAFT` env overrides).
- `fec/tests/run_tests.py` — 64 kernel invariants. `fec/tests/test_bug_report_regressions.py` adds
  bug-report contracts; `fec/attic/` is retired code.
- `fec/templates/` — dashboard HTML/JS templates. `backups/` — workbook backups (auto, pre-write).
- `Moneyball Main Version - Blended.xlsx` — legacy inputs and Excel formula view, not live-rank or
  live-stance authority. **`fec/build_audit_workbook.py`** (openpyxl) produces the compact review
  workbook `outputs/workbook_repair/Moneyball Audit Workbook.xlsx` with current category stance,
  same-row normalization, and workbook-coherent ranks — run `python fec/build_audit_workbook.py`
  (it runs the read-only `extract_workbook_audit_inputs.py` first if the JSON handoff is absent; no
  network, no pipeline run). Its contracts are enforced by `fec/tests/test_workbook_contracts.py`.
  The older `fec/build_audit_workbook.mjs`/`verify_audit_workbook.mjs` require the OpenAI
  code-interpreter package `@oai/artifact-tool` and do **not** run on the workstation (no Node, no
  `node_modules`); they are kept only as the original reference for the value contract. `votes/`
  contains voteview rosters; `research/` contains source papers.
- Root `*.json` — derived artifacts (regenerable). Every PIPELINE-CHAIN writer is atomic via
  `MC.dump_atomic`; manual collector/diagnostic scripts may still write raw (audit run-2, S3-01).
- `social_media.db` — posts, member↔member interactions, floor speeches + hearing transcripts.

## The model (five layers)
1. **Stance** (`per_category_stance.py` → category_stance.json): 533×18 self-calibrating matrix;
   defensive issues (Interchange, Credit Card Mandates) are Defender-tiered. `sync_stance_g.py`
   aggregates to the workbook's overall tier (col G) with the ABB26 IMP weights.
2. **Media** (`build_media_blend.py`): press pillar = 50% press + 50% social (p80-scaled, tiered
   category weights from the Topic Weights sheet, exp decay 2.0y/0.5y, RT×0.5, thin-cat shrink).
3. **Network** (`build_multilayer_network.py`): cosponsorship + press engagement + HCoI + social
   repost/mention edges (Fink-normalized; new links AND +30%-capped reinforcement).
4. **Receptivity** (`big5_traits.py` → `receptivity_layer.py`): Big Five/public-behavior inputs from
   floor speech, hearings, interviews, and posts → susceptibility (Byrne), electoral incentive
   (Fouirnaies-Hall), prospect-theory domain (Linde-Vis), and contingency seed-gates. The product's
   Extraversion is an OOF-gold-validated public-personality estimate: 20% Blue visibility-calibrated,
   60% Pink observer-item, 10% interaction dominance, and 10% role-adjusted visibility. The latter two
   remain separately labeled behavioral/context fields and are not Extraversion by themselves. All
   five canonical profile axes now use the OOF Senate-gold composites: E/A clear both panels, while
   O/C/N are explicitly labeled one-panel association-supported estimates.
5. **Influence engines**: coalition cascades (`budget_frontier.py` [+`--electoral`],
   `per_topic_coalition.py`), Linear-Threshold flips (`flip_model.py`, `per_topic_flip.py`,
   `lt_priming.py`), adaptive $ optimizer (`optimize.py`, Golovin-Krause), going-public advisory
   (`salience_shock.py`, Noble-Turner), scenario runner (`scenario.py`), routes (`cosponsor_route.py`).
6. **Media & psychology layer** (2026-07-04/06): interview collectors (`fetch_interviews.py` —
   cnn/mtp/cbs/abc/pbs/npr/fox/hewitt legs, iv_fetch_log-resumable, drop-never-guess attribution)
   → behavioral dispositions (`behavior_panel.py` → `behavioral_dispositions.py`, receptivity's
   basis) + archived LLM Big-Five research artifacts (diagnostic/display only) + signed
   reference layer (`member_reference_layer.py` → member_references.json, Fable-valenced,
   --rebuild is free / --score is gated) + co-appearances (`co_appearance_layer.py` →
   co_appearance.json). All are chain-independent inputs/diagnostics; audit_full guards their
   schemas (run-5b).
7. **Clean-audio & narrative layer** (2026-07-09): audio fetch (`b5_audio_fetch.py --search`, yt-dlp
   floor clips) → caption speaker/identity verification (`b5_audio_verify.py` → b5_audio_verify.json
   + b5_caption_cache.json; Haiku, HARD-signal identity, keep = solo & not-mismatch) → verified
   eGeMAPS voiceprints (`b5_audio_build.py` → b5_audio_cache.json). The legacy verifier currently
   contains 2,192 clips / 1,761 kept / 435 members; those counts are historical corpus coverage, not
   profile acceptance. The strict profile gate accepts 0 members until the independent-review,
   cross-program contract is satisfied. Its current member floor is 60 confirmed target seconds:
   two independent programs times the existing 30-second minimum accepted clip. Historical
   180-second research samples remain historical results, not the active eligibility rule. The
   historical voice-ES channel is retired from validation and
   display because its independent criterion was gender-confounded. The active display uses
   source-primary O/C, externally anchored public-personality E (509/533 coverage), low-antagonism A,
   and affective-content N. The historic gold is validation, not a population norm. Audio is fail-closed:
   only descriptors passing the v2 identity, independence, and cross-source guards may enter a
   profile. Accepted audio is measured per speech as mean-F0 deviation from that speaker's baseline
   and summarized only within transcript-identified topics; absolute pitch never enters Big Five.
   A deterministic zero-API three-paragraph renderer is available but is not activated
   roster-wide without explicit user approval. Expert-panel infrastructure
   (`b5_panel_{items,build,score}.py`) is DORMANT (prereg CANCELED; scorer refuses the look).
   All display-only — no engine/rank consumer.

## Running
```
python -m pip install -r requirements.txt     # canonical Python 3.12 runtime
python fec/run_pipeline.py [--from <step>]   # the whole chain, audited at the end (NO Excel/COM involved)
python fec/tests/run_tests.py                # 64 kernel checks (run after ANY code change)
python -m unittest fec.tests.test_bug_report_regressions -v  # 42 bug-report regressions
python fec/audit_full.py                     # 97 full-audit checks (expect ALL MODULES CLEAN)
```
**Rank authority = `ranks_python.json`** (phase 2): Python computes the entire rank chain;
the legacy workbook is an input/formula view that recalculates itself when opened in Excel
(fullCalcOnLoad). The shipped adjusted rank—including eligible party-office influence—must be read
from `ranks_python.json`; the compact audit workbook exposes base and adjusted values side by side.
Verification protocol for code changes: kernel tests → pipeline → **zero rank delta** vs the last
`ranks_*.json` (unless the change is supposed to move ranks) → audit clean.
Data refresh order: collectors (`fetch_congressional_record.py`, `tweet_collector.py`, Quorum) →
`big5_traits` → `social_interaction_layer` → `build_multilayer_network` → `build_media_blend` →
`run_pipeline --recalc`. Determinism: SEED=7, MC=20, splitmix64 CRN — same-seed runs are identical.

The combined self-contained HTML is deliberately an offline/desktop artifact and is about 19 MB.
Treat mobile deployment as a separate packaging decision; eager base64 loading can exceed browser
memory on phones even when the underlying dashboard logic is correct.

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
`corrected_signals.json`, `social_member_summary.json`, `cu_golden_labels_stats.json`, and
`per_topic_alloc_bridge.json` (written only under `--bridge`/`BRIDGE=1`) are human-inspection
outputs with no live consumer — safe to regenerate anytime, never load-bearing.

## Canonical docs
`MATHEMATICAL_SPECIFICATION.md` (law of the system: authoritative-code table, conventions, dials) ·
`ARCHITECTURE_REVIEW_2026-07-02.md` (historical snapshot) · `AUDIT_FINDINGS_2026-07-02.md` · `INDEX.md`.

_Upstream raw data (FEC source files, press indexes, old workbooks) lives in the original
`Draft Systems` folder — needed only to regenerate base data, includes irreplaceable files._
