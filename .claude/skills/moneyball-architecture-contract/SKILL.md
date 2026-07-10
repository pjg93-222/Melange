---
name: moneyball-architecture-contract
description: The Moneyball system's shape contract - the layer stack and data flow, artifact ownership (which script writes which JSON), the load-bearing invariants (two cpf physics, the '-' no-position ontology, SEED=7/MC=20 splitmix64 determinism, atomic writes, rank authority = ranks_python.json with the workbook as a view), paths.py root resolution and why git worktrees do NOT isolate data, known-weak points (congestion.json has no live producer, the hand-maintained Python-to-JS engine mirror, OneDrive locks), and the moneyball_core kernel API a new fec script should import. Triggers - "where does X come from", "which script writes Y", "can I merge these two cpf functions", "why is my run non-deterministic", "why did the workbook read None", "is it safe to run this from a worktree". Does NOT cover day-to-day running (moneyball-run-and-operate), change rules (moneyball-change-control), dials (moneyball-config-and-flags), live-failure triage (moneyball-debugging-playbook), or env setup (moneyball-build-and-env).
---

# Moneyball architecture contract

Moneyball is a legislative-influence model: it ranks the 533 members of the U.S. Congress by how useful they are to a credit-union lobbying association, classifies each member's stance on 18 credit-union issue categories, and simulates where money and persuasion effort would move the most votes. The code is Python under `fec/` in the live tree `C:\Users\pgoff\OneDrive\Desktop\Melange Systems`; user dials live in an Excel workbook; three self-contained HTML apps render the results. This skill is the **shape contract**: the layer stack, the invariants that must always hold (and why they exist), the artifact-ownership table, and the known-weak points. The root document of record is `MATHEMATICAL_SPECIFICATION.md` at the repo root — it declares "the code is authoritative; this document tells you where to look and what must always hold." Nothing below may be changed in a way that contradicts it without going through change control.

## When NOT to use this skill

- Running the pipeline, collectors, or dashboards day-to-day → **moneyball-run-and-operate**
- Whether you are ALLOWED to make a change, and the user-gated decision list → **moneyball-change-control**
- Looking up a specific env var / dial default → **moneyball-config-and-flags**
- A live failure you need to triage right now → **moneyball-debugging-playbook**
- Why a past design decision was reverted / what was already tried → **moneyball-failure-archaeology**
- The influence/persuasion theory behind the engines (cascades, submodularity, Bakker) → **influence-modeling-reference**
- Measurement theory (Big Five, reliability, z-scores as statistics) → **psychometrics-reference**

## Quick reference — the invariants at a glance

| # | Invariant | One-line statement | Enforced/declared at |
|---|---|---|---|
| 1 | Two partisan physics | `cpf_diffusion` (cascades) and `cpf_pressure` (direct persuasion) are deliberate, distinct — **never merge** | `fec/moneyball_core.py:120-125`; `MATHEMATICAL_SPECIFICATION.md` "Cross-module conventions" |
| 2 | '—' ontology | "No recorded position" = *unknown*: never zero, never enthusiasm; `PERS['—']=0.45` | `fec/moneyball_core.py:138-140`; spec |
| 3 | Determinism | SEED=7, MC=20, splitmix64 CRN keyed on (iteration, edge/member); new draws claim a fresh key range (seed gating uses offset 2^62) | spec "Determinism contract"; `fec/per_topic_coalition.py:56` |
| 4 | Atomic writes | Every chain artifact is written via `MC.dump_atomic` (temp sibling + `os.replace`) — never a truncated JSON | `fec/moneyball_core.py:88-101` |
| 5 | Rank authority | `ranks_python.json` is THE score/rank source; the workbook is a self-refreshing VIEW | `fec/compute_pillars.py` docstring; `fec/moneyball_core.py:76-87` |
| 6 | Corpus-relative z | All psych measurements are z-scores relative to THIS roster/corpus, not absolute scales | `fec/big5_traits.py:235`; `fec/behavioral_dispositions.py` |
| 7 | Engine-input vs display-only | Only ratified artifacts feed the engines; LLM overlays are display-only until promoted (a user-gated step) | `fec/make_member_desk.py:101-104,140-141` |
| 8 | Worktree ≠ sandbox | `fec/paths.py` hardcodes the live tree; any fec script run anywhere reads/writes production data | `fec/paths.py:7` |
| 9 | Import == execution | Most fec scripts have no `__main__` guard; importing them runs them | e.g. `fec/per_topic_coalition.py` (whole MC loop at module level) |

## 1. The system in one page

Five layers, each producing named artifacts the next layer consumes. Everything below lives in the LIVE tree root (`C:\Users\pgoff\OneDrive\Desktop\Melange Systems`) unless noted; almost all data files are gitignored (the repo tracks code + docs + a short force-tracked whitelist: `cu_valence_registry.json`, `quorum_query.txt`, `fec/retiring_members.txt`, `.claude/launch.json`, and the `fec/*24.zip` FEC bulk files).

```
LAYER 0 — ROSTER (static, no live producer — see weak point 5.1)
  congestion.json ............. canonical 533-member roster + FEC money fields; keyed by member name,
                                carries bioguide IDs. Loaded by EVERYTHING via moneyball_core.congestion().

LAYER 1 — COLLECTORS (external sources -> local raw stores)
  fetch_congressional_record.py, fetch_interviews.py -> social_media.db (speeches: CREC/CHRG/INTERVIEW)
  tweet_collector.py -> social_media.db (posts/interactions)     process_quorum.py -> Quorum Processed.xlsx
  External/irreplaceable inputs: Draft Systems folder (R press pipeline -> cu_press_stance_tone.csv,
  workbook 'Press Release Articles' sheet), Quorum Master.xlsx, votes/cu_rollcall_votes_clean.csv.

LAYER 2 — STANCE / MEDIA / NETWORK (raw evidence -> derived signal)
  per_category_stance.py -> category_stance.json ......... 533x18 stance matrix (Champion..Opponent + '—'),
                                                            say-do gate applied at write time
  build_media_blend.py -> workbook 'Press Release - Raw' .. 50% press + 50% social blended pillar input
  build_multilayer_network.py -> congress_cosponsor_network_AUG<date>.xlsx (cosponsor+engagement+HCoI+social edges)
  member_reference_layer.py -> member_references.json ..... signed colleague-mention layer (display + diagnostics)
  vote_by_category.py -> vote_category_lean.json .......... per-category vote lean (say-do path V evidence)

LAYER 3 — PSYCH / RECEPTIVITY (who is movable, and how much)
  behavioral_dispositions.py -> behavioral_dispositions.json  (6 behavior-measured traits, z within chamber)
  agency_communion_llm.py -> agency_communion.json            (persona channel, PERSONA_W=0.30 blend weight)
  receptivity_layer.py -> member_receptivity.json ........... susc_mult / edge_mult / pressure_mult / seed_prob
  say_do_gap diagnostic -> say_do_gap.json .................. delivery_mult talker discount

LAYER 4 — INFLUENCE ENGINES (what to do about it)  [all read ranks_python.json + category_stance.json]
  compute_pillars.py --write -> ranks_python.json ..... THE RANK AUTHORITY
  per_topic_flip.py -> per_topic_alloc.json           per_topic_coalition.py -> per_topic_coalition.json
  lt_priming.py -> lt_priming.json                    budget_frontier.py -> budget_frontier[_electoral].json
  optimize.py -> optimize_result.json                 salience_shock.py --advise -> salience_advisory.json
  build_im_allocation.py -> im_allocation.json

LAYER 5 — VIEWS (never inputs)
  sync_stance_g.py -> workbook Rank&Allocation col G (overall stance tier; OUTPUT-ONLY view)
  build_dashboard_bundle.py -> dashboard_data.json + bipartisan.json
  make_dashboard_html.py -> Moneyball Dashboard.html      make_member_desk.py -> cu-member-desk.html
  make_combined.py -> Moneyball.html                      lock_dashboard.py -> deploy/index.html (AES-encrypted)
```

The canonical run order is the 17-step `CHAIN` list in `fec/run_pipeline.py:19-35` (layers 3→2-stance→4→5→audit, in that exact order; collectors and `big5_traits.py` are manual/weekly, outside the chain). One ordering rule is load-bearing: `compute_pillars.py --write` runs BEFORE `sync_stance_g.py` because any openpyxl save destroys the workbook's cached formula values (see invariant 2.5). One feedback edge exists: `bipartisan.json` is written at chain step 13 (`build_dashboard_bundle.py`) but read by the kernel's `bpf()` in steps 5–12 — those steps consume the *previous* run's copy, which is why a stance/network change legitimately shifts engine outputs once more on the NEXT run (two-run convergence, not a bug).

## 2. Invariants — with the why

### 2.1 The two partisan physics — deliberate, distinct, never merge

"cpf" = cross-party factor: a multiplier applied to an edge or a persuasion attempt depending on the two members' parties. There are exactly TWO, with opposite shapes, because two different social-science mechanisms are being modeled (`fec/moneyball_core.py:8-12`; spec "The two partisan physics"):

- **`cpf_diffusion(n,u)`** — contagion/cascade physics. Cross-party edges are *dampened* unless both ends are bridge-builders: `0.4 + 0.6*sqrt(bpf_n * bpf_u)` when parties differ (both D/R), else `1.0`. (`bpf` = each member's bipartisanship fraction, 0–1.) Ideas spread across the aisle only through people who already work across it. Used by the spread/cascade engines (budget_frontier, per_topic_coalition, lt_priming, salience_shock, cosponsor_route, scenario) and as the default physics of the kernel's `build_P`. Code: `fec/moneyball_core.py:120-122`.
- **`cpf_pressure(n,u)`** — direct-persuasion physics (Furnas/Bakker source-alignment: people accept pressure from their own side). Co-partisan ×`1.7`, out-partisan ×`0.5`, `1.0` if either member is an independent. Used by the flip/persuasion engines (flip_model, per_topic_flip). Code: `fec/moneyball_core.py:123-125`.

WHY the rule exists: pre-refactor these were a single ambiguous local name `cpf` copy-pasted 8 times *under the two different formulas*, and duplication drift caused real bugs (kernel header, `fec/moneyball_core.py:2-6`). The spec's exact words: "deliberate, distinct — never merge." Engines still locally alias (`cpf = MBC.cpf_diffusion` etc.) — always read the alias line in a script before assuming which physics it runs.

### 2.2 The '—' (no-recorded-position) ontology — never zero, never enthusiasm

`'—'` in the stance matrix means the member has *no recorded position* on that category. The system-wide rule (spec "'—' ontology"): a blank is **unknown**, and each module maps unknown to its own neutral point — never to zero (which would make silent members free wins or free losses) and never to enthusiasm (silence must not outrank a declared supporter). Concretely:

| Module | '—' treatment | Where |
|---|---|---|
| Persuadability | `PERS['—'] = PERS_NONE = 0.45` — "Ally parity; silence never outranks a declared Ally" (USER-RATIFIED 2026-07-02) | `fec/moneyball_core.py:138-140` |
| Seed-activation gate | `SGATE['—'] = 0.85` — an unknown is slightly harder to activate than a known Neutral | `fec/moneyball_core.py:151-152` |
| Overall-tier aggregation | '—' **excluded** — silence doesn't dilute earned tiers | `fec/moneyball_core.py:155-167` (`overall_tier`) |
| Salience shock | the '—' share **raises** issue uncertainty ψ | spec; `fec/salience_shock.py` |

`PERS_NONE` is an env dial with a user-ratified default of 0.45; changing it is Paul's decision (see moneyball-change-control). This ontology is also why the Congress-rollover weak point (5.5) matters: a freshman has '—' in nearly every cell.

### 2.3 Determinism contract — SEED=7, MC=20, splitmix64 CRN, key ranges

Every stochastic engine (the Monte-Carlo cascade simulators) must be exactly reproducible so a re-run with no input change produces byte-identical artifacts, and so a *marginal* — `spread(seeds + {candidate}) − spread(seeds)` — measures the candidate's true effect rather than random-number noise. Three mechanisms, all mandatory for new stochastic code:

1. **Fixed defaults**: `SEED=7`, `MC=20` (MC here = Monte-Carlo iteration count; validated safe against MC=100 and alternate seeds by `fec/mc_stability_check.py`).
2. **Edge-keyed CRN** ("common random numbers"): draws come from `sm64(key)`, a splitmix64 hash mapping an integer key to [0,1) deterministically and independent of evaluation order (`fec/moneyball_core.py:126-131`). Cascade edge (u,v) at iteration `it` uses key `it*NM*NM + idx[u]*NM + idx[v]` (NM = roster size) — so adding a seed member cannot desync the stream (`fec/per_topic_coalition.py:27-36`).
3. **Key-range claims**: any NEW family of random draws must claim its own dedicated key range so it cannot collide with the edge keys. The existing example: seed-activation rolls use offset 2^62 — `_sm((1<<62) + it*NM + idx[n])` at `fec/per_topic_coalition.py:56`. If you add a new draw type, pick a fresh disjoint offset and document it.

Corollary trap: draws must be rolled *unconditionally* then filtered — gating a draw behind set membership changes the number of draws consumed and desyncs everything downstream (the "5.A fix" comment at `fec/per_topic_coalition.py:57` records exactly this bug). Beware the **MC alias collision**: `import moneyball_core as MC` in non-simulation scripts vs `MC = int(os.environ.get('MC','20'))` in simulation scripts — check the import line before copying any `MC.` snippet between files.

### 2.4 Atomic writes — MC.dump_atomic

Every JSON artifact in the chain is written with `MC.dump_atomic(obj, path, **kw)` (`fec/moneyball_core.py:88-101`): dump to a `tempfile.mkstemp` sibling **in the same directory**, then `os.replace()` (atomic on NTFS); on any exception the temp is removed and the original file survives. WHY: audit finding S2-03 (2026-07-02) — an Excel force-kill under OneDrive contention risked truncating an artifact mid-write, and a truncated JSON silently poisons every downstream consumer. Rule for new code: never `json.dump(obj, open(path,'w'))` for a shared artifact; use `dump_atomic`. It is unit-tested in `fec/tests/run_tests.py`.

### 2.5 Rank authority = ranks_python.json; the workbook is a VIEW

Since "Phase 2" (system-of-record inversion, user sign-off 2026-07-02): **Python computes the entire rank chain**; `fec/compute_pillars.py --write` emits `ranks_python.json`, and engines read scores/ranks ONLY through `moneyball_core.scores()/ranks()`, which raises loudly if the file is missing ("the workbook is a VIEW, not the score source", `fec/moneyball_core.py:76-87`). The Excel workbook `Moneyball Main Version - Blended.xlsx` is demoted to a self-refreshing view: every Python writer sets `fullCalcOnLoad=True`, so Excel recalculates all formulas the next time Paul opens the file. Excel COM automation (driving a live Excel process) is retired from the pipeline entirely (`fec/run_pipeline.py:6-11` records the incidents: a PermissionError lock race and a 2.2 MB truncated save from COM+OneDrive contention).

What openpyxl does to the file — the single most confusing physics in this project: **any openpyxl save strips the cached results of every formula cell**. Afterwards, `load_workbook(..., data_only=True)` reads of FORMULA cells return `None` until Paul next opens the workbook in Excel (the fullCalcOnLoad self-heal). TYPED (literal) cells always survive. This is not a bug and must not be "fixed". Consequences baked into the design:

- Rosters are read from TYPED columns (Rank & Allocation col A), never formula-backed ones (`fec/compute_pillars.py:32-34`).
- The formula-backed pillar inputs O/E/F are snapshotted to `pillar_inputs_snapshot.json`, auto-refreshed while the cache is alive, bootstrapped from the newest cache-alive backup in `backups/` if missing (`fec/compute_pillars.py:47-50` comments).
- Chain order: the rank authority is computed BEFORE the cache-killing col-G sync (`fec/run_pipeline.py:21-22`).
- Never use `read_only=True` for random `.cell()` access: streamed sheets make each call O(sheet) — a measured 640-second pathology — and misread openpyxl-saved files (`fec/moneyball_core.py:61`).
- Python writes VALUES only, backup-first into `backups/`; Excel must be CLOSED for any workbook write (PermissionError otherwise).

Rank math itself: `Score = AB2·Leg% + AB3·Press% + AB4·Influence% + AB5·Demo%`, with the AB pillar weights read LIVE from workbook cells (user dials, `fec/compute_pillars.py:11` docstring) — the spec's printed literals are stale relative to the live cells; the workbook cells and `ranks_python.json` are the only truth. Excel's `PERCENTRANK.INC(...,5)` is reproduced exactly as "truncate to 5 decimal digits" (empirically pinned, `fec/compute_pillars.py:42-46`).

### 2.6 Corpus-relative z-scores in psych

Every psychological measurement in the system is a **z-score relative to this corpus/roster**, not an absolute scale: the text Big-Five output declares "z relative to THIS corpus" in its own provenance string (`fec/big5_traits.py:235`), and the six behavioral dispositions are z-scored within chamber (`fec/behavioral_dispositions.py`). A z-score answers "how far above/below the average member of Congress is this member, in standard deviations" — it says nothing about the general population. WHY it matters architecturally: (a) scores are only comparable within a build — never compare a member's z across corpus rebuilds or roster changes; (b) at Congress rollover the reference population itself changes, silently re-centering every trait; (c) missing data maps to `None` → neutral 0 downstream, "never an invented disposition" (`fec/behavioral_dispositions.py:23-24`), so coverage gaps read as average, not as absent.

### 2.7 Engine-inputs vs display-only artifacts

A hard split exists between artifacts that feed the influence engines and artifacts that only render on the member desk/dashboard. Promotion from display-only to engine-input is a **separate user-ratified step**, stated in code (`fec/make_member_desk.py:101-104`: "engines untouched — promotion into receptivity stays a separate ratified step").

| Engine inputs (ratified) | Display-only / diagnostics (never engine-read) |
|---|---|
| `behavioral_dispositions.json` | `big5_llm_opus.json` ("Pink" Opus item-read; dashed desk overlay) |
| `agency_communion.json` (persona blend, PERSONA_W=0.30 — user-ratified KEEP) | `member_narratives.json` (Fable 3-paragraph briefs) |
| `big5_traits.json` (only via legacy `RECEPT_TRAITS=lexical` / `RECEPT_N=text` fallbacks) | `b5_es_voice.json` (voice-ES; gender-confounded caveat baked into `make_member_desk.py:141`) |
| `member_receptivity.json` (the fused multipliers) | `big5_v2.json` / `big5_v3_hybrid.json` (desk radar + validation criteria) |
| `say_do_gap.json` (delivery_mult); `coop_v2_candidate.json` (an ENGINE INPUT since the promotion @94f09cf, merged to main 2026-07-10 — `RECEPT_COOP=v2` sources both cooperation slots from it; the `_candidate` name is historical) | — |
| `category_stance.json`, `ranks_python.json`, `bipartisan.json`, network xlsx, `vote_category_lean.json`, `electoral_plays.json` | `kb_benchmark.json`, `signed_coalitions.json`, `member_references.json`, `co_appearance.json` (relational display/diagnostics), plus the README §"Diagnostics-only artifacts" list (`stance_dynamics.json`, `imviz.json`, `tweet_influence.json`, ...) |

The `.candidate` suffix / `*_candidate` naming = built-but-unpromoted, staged awaiting Paul (e.g. `fec/liwc/behavior_calibrated.json.candidate`). Related fallback contract: every engine-side psych consumer degrades to neutral if its artifact is missing — `rc(member, key, default=1.0)` (`fec/moneyball_core.py:51`) — so deleting `member_receptivity.json` doesn't error, it silently reverts engines to pre-psych behavior. Silent degradation is a feature here; know it exists.

## 3. Authoritative-code table — which script owns which artifact

From the spec's "Authoritative sources by subsystem" table, spot-verified in code 2026-07-09. Rule: exactly ONE producer per artifact; **never hand-edit or hand-extend a generated JSON** (incident: an 18th stance category hand-added to `category_stance.json` was silently clobbered by its producer — `fec/per_category_stance.py:21-24`).

| Artifact | Sole producer | Notes |
|---|---|---|
| `ranks_python.json` | `fec/compute_pillars.py --write` | THE rank authority |
| `category_stance.json` | `fec/per_category_stance.py` | 18 categories; say-do gate applied at write |
| workbook col G (overall tier) | `fec/sync_stance_g.py` | output-only view; single `overall_tier` law shared with the producer (S2-04 fix) |
| workbook 'Press Release - Raw' | `fec/build_media_blend.py` | press+social blend; backup-first |
| `member_receptivity.json` | `fec/receptivity_layer.py` | susc/edge/pressure/seed multipliers |
| `behavioral_dispositions.json` | `fec/behavioral_dispositions.py` | 6 behavioral traits |
| `big5_traits.json` | `fec/big5_traits.py` | manual/weekly, outside the chain |
| `per_topic_alloc.json` / `_bridge` | `fec/per_topic_flip.py` | LT flip allocator |
| `per_topic_coalition.json` | `fec/per_topic_coalition.py` | IC coalition seeding |
| `lt_priming.json` | `fec/lt_priming.py` | in-chain since 2026-07-04 (artifact fossilized once) |
| `budget_frontier[_electoral].json` | `fec/budget_frontier.py [--electoral]` | `FRONTIER_OUT` env redirects for safe test runs |
| `optimize_result.json` | `fec/optimize.py` | `OPT_OUT` redirects |
| `im_allocation.json` | `fec/build_im_allocation.py` | |
| `salience_advisory.json` | `fec/salience_shock.py --advise` | must precede the bundle in the chain |
| `dashboard_data.json` + `bipartisan.json` | `fec/build_dashboard_bundle.py` | bipartisan.json feeds back into next run's engines |
| `Moneyball Dashboard.html` / `cu-member-desk.html` / `Moneyball.html` | `make_dashboard_html.py` / `make_member_desk.py` / `make_combined.py` | template substitution only |
| `congress_cosponsor_network_AUG*.xlsx` | `fec/build_multilayer_network.py` | loaders pick newest by mtime; revert = delete the AUG file |
| `member_references.json` / `co_appearance.json` | `member_reference_layer.py` / `co_appearance_layer.py` | display/diagnostic layers |
| `cu_valence_registry.json` | `fec/derive_valence_registry.py --write` | the ONLY force-tracked JSON — the user's committed valence judgments |
| shared math/loaders | `fec/moneyball_core.py` | verified by `fec/tests/run_tests.py` (37 checks as of 2026-07-09) |
| Rank formula cells, committee pillar | **live Excel formulas — no builder script** | see weak point 5.4 |
| `congestion.json` | **NO live producer** | see weak point 5.1 |

## 4. paths.py and the worktree-shares-live-tree consequence

`fec/paths.py` is 12 lines and is the whole path story:

```python
ROOT  = os.environ.get('MONEYBALL_ROOT',  r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems')
DRAFT = os.environ.get('MONEYBALL_DRAFT', r'C:\Users\pgoff\OneDrive\Desktop\Draft Systems')  # R press-pipeline root
FEC=ROOT\fec   WORKBOOK=ROOT\Moneyball Main Version - Blended.xlsx   BACKUPS=ROOT\backups
```

Every fec script starts with `sys.path.insert(0, <its own dir>); from paths import ROOT` — so a git-worktree *copy* of paths.py gets imported, but its ROOT default is still the absolute live-tree path. **Consequence: git worktrees isolate CODE, not DATA.** Any fec script run (or merely imported — import == execution for nearly all of them) from any checkout reads and writes the production data tree and workbook. There is no such thing as "trying it in a worktree first". The only redirects are the env vars: set `MONEYBALL_ROOT` (and `MONEYBALL_DRAFT`) to a copied tree if you genuinely need a sandbox — and know that a full sandbox needs the workbook, all root JSONs, `social_media.db`, the `votes/` CSVs, and Draft Systems inputs present at that root. For casual verification, only `fec/tests/run_tests.py` and `fec/audit_full.py` are read-only-safe to run:

```powershell
cd "C:\Users\pgoff\OneDrive\Desktop\Melange Systems"
python "fec\tests\run_tests.py"
python "fec\audit_full.py"
```

OneDrive is part of the physics here: the live tree sits inside OneDrive, whose sync locks and latency caused the truncation/lock incidents that motivated dump_atomic and the COM retirement. paths.py's own docstring calls out that "escaping OneDrive is a one-variable change" — but relocating is Paul's call.

## 5. Known-weak points — stated plainly

### 5.1 congestion.json has NO live producer

The canonical 533-member roster + FEC money artifact — the file literally everything loads first — is not produced by any live script. Its writers exist only in `fec/attic/` (`full_congestion.py`, `final_congestion.py`, `final.py`, `final_table.py`, `makeup.py`, `makeup2.py`, `saturation.py` — all with hardcoded live-tree output paths), and its raw inputs are the git-tracked FEC bulk zips `fec/ccl24.zip`, `fec/cm24.zip`, `fec/cn24.zip`, `fec/pas224.zip`, `fec/weball24.zip`, whose only consumers are those same attic scripts. As of 2026-07-09 the artifact simply *is*; regenerating it (e.g. for the 120th Congress with 2026-cycle FEC files) means resurrecting retired attic code. This is the single most important thing to know before a Congress rollover — see **moneyball-congress-rollover-campaign**.

### 5.2 The hand-maintained Python↔JS engine mirror

The network dashboard re-implements the persuasion engines in template JavaScript (`fec/templates/make_dashboard_html_00.tpl`, banner at line 324: "faithful port of flip_model + competitive cascade + lt_priming") so the browser can run scenarios live. It is a **hand-maintained mirror**: any change to `flip_model.py` terms, `lt_priming.py` gates/pricing, `build_P` physics, salience parameter estimation, or engine constants requires a matching tpl edit (`fec/lt_priming.py` and `fec/build_dashboard_bundle.py` carry "KEEP IN SYNC" comments; constants are duplicated as literals in the bundle, not imported). The audit has **zero template coverage** — `audit_full.py` contains no reference to `templates/` or `.tpl`, so all checks stay green while the JS mirror is arithmetically wrong. The only guard is the in-page `#engchk` badge (`updateEngChk()`, tpl:761), which checks the flipModel total per issue within max(0.2, 3%) — it does NOT cover prime()/spread()/pathfinder logic. The psych-multiplier gap (JS ignoring pressure/edge/delivery multipliers) was closed 2026-07-09 (`tpl:326`, `const PM=EG.pmult||...` with neutral fallback for old bundles), but no repeatable parity test exists; treat every engine edit as a two-file edit.

### 5.3 OneDrive latency and locks

The live tree is inside OneDrive. Historical damage: a COM+OneDrive lock race, a 2.2 MB truncated workbook save, and artifact-truncation risk that motivated `dump_atomic` (`fec/run_pipeline.py:9-11`, `fec/moneyball_core.py:89-90`). Standing consequences: Excel must be closed for any workbook write (an open workbook = PermissionError — record, skip, never kill Excel); `weekly_refresh.py` has a ratified fallback (`run_pipeline.py --from per_topic_flip`) that skips workbook-writing steps when the file is locked; expect occasional slow first-reads of large files while OneDrive hydrates.

### 5.4 The committee pillar exists only as live Excel formulas

The Influence% pillar's committee score has **no Python builder**. The data path is: workbook `Committee Data` sheet (seats-held text per member) → Rank & Allocation col E via live `INDEX/MATCH` formulas → Blended col R `=E/MAX(E)` → Influence%. The formula logic is documented as a *validating port* in `fec/apply_committee_reweight.py:3-10` (membership tier weights Highly 3.0 / Moderately 1.8 / Slightly 0.9, subcommittee = base/6; leadership bonus ×mw Chair 3.0/7.5, Ranking 2.0/4.5, Vice 1.0/2.0; all Small Business seats = Highly; **committee score = (Membership + Leadership)/2**), whose default mode recomputes and confirms it reproduces the sheet — but the authoritative computation lives in the workbook's formulas, edited by hand. If the workbook were lost, the pillar's machinery survives only in backups and that port. Also note the INDEX/MATCH ranges have a hard row cap (`$2:$360`) that had to be manually extended once (`fec/add_judiciary_seats.py`).

### 5.5 The '—'-heavy freshman roster at Congress rollover

Every stance cell starts as '—' for a member with no legislative/press/vote history. Under the '—' ontology a freshman is: persuadability 0.45 everywhere, seed gate 0.85, excluded from overall-tier math, and raising salience uncertainty on every issue — i.e., the model degrades to near-uniform priors over the entire incoming class, while the psych layer's corpus-relative z (2.6) simultaneously re-centers on the new population and the behavioral dispositions have no behavior to measure (missing → neutral). The invariants make this degradation *graceful and honest*, not wrong — but expect the engines' discrimination among freshmen to be close to zero until evidence accumulates. Planning for this is owned by **moneyball-congress-rollover-campaign**.

### 5.6 Smaller standing weaknesses

- **Say-do gate fails OPEN**: a missing/unreadable evidence source (workbook role sheets, `vote_category_lean.json`) means NO caps, never wrongly-capped (`fec/moneyball_core.py:222-224,282`) — an absent file silently un-caps Champions. The unattended spend guards fail CLOSED; know each failure's direction.
- **Kernel caches are process-lifetime**: `_c` and the say-do lazy globals never refresh within a process (`fec/moneyball_core.py:17,198,232,250,294`); long-lived processes will not see artifact updates.
- **`build_media_blend.py` decay is anchored to a hardcoded `TODAY=2026-07-02`**, not the wall clock (`fec/build_media_blend.py:31`).
- **Roster ranges are hardcoded** (`range(3,536)` etc.) across workbook readers; a roster-size change breaks silently, guarded only by audit checks.

## 6. The kernel API surface — use moneyball_core, don't reinvent

Any new fec script should `import moneyball_core as MC` (or `as MBC` if it needs `MC` as an iteration count) and use these instead of writing its own loaders — the kernel exists precisely because 17 copy-pasted network loaders and 8 cpf copies drifted into real bugs. Importing the kernel does NO workbook IO (loaders are lazy + cached).

| Call | Returns / does |
|---|---|
| `MC.congestion()` / `MC.members()` | roster dict keyed by member name / name list |
| `MC.name2bio()` / `MC.bio2name()` | name ↔ bioguide-ID maps (bioguide = the cross-dataset join key) |
| `MC.party()` | name → 'D'/'R'/'I'/'?' from the HS119..117 vote rosters |
| `MC.bpf()` | name → bipartisanship fraction (bipartisan.json / 100; default 0.24) |
| `MC.receptivity()` / `MC.rc(m, key, d=1.0)` | receptivity dict / per-member multiplier with neutral fallback (`RECEPT_LAYER=0` kills) |
| `MC.press_matrix()` | Python-owned press normalization (norm, row-535 weights, headers) |
| `MC.pillar_scores()` / `MC.scores()` / `MC.ranks()` | the rank authority; raises loudly if `ranks_python.json` is missing |
| `MC.dump_atomic(obj, path, **kw)` | the mandatory atomic JSON writer |
| `MC.load_network()` | newest cosponsor-network xlsx by mtime, mean-symmetrized, name-keyed adjacency; EVERY member has an entry (isolated → `{}`) |
| `MC.cpf_diffusion` / `MC.cpf_pressure` | the two partisan physics (2.1) |
| `MC.sm64(key)` | splitmix64 keyed draw in [0,1) — the CRN primitive |
| `MC.build_P(adj=None, physics=cpf_diffusion, edge_mult=True)` | cascade edge probabilities `p = w·cpf·σ_v/(w·cpf·σ_v+6)`, σ_v = receiver `edge_mult` |
| `MC.PERS` / `MC.PERS_NONE` / `MC.IMP` / `MC.SGATE` / `MC.TORD` | the calibrated constant tables (persuadability, category importance, seed gate, tier ordinals) — single copies |
| `MC.blocks` / `MC.BLOCKCAT` / `MC.CATBLOCKS` | workbook column-block ↔ category maps (incl. the CFPB 99+145 fold) |
| `MC.gate(n, cs)` | seed-activation probability `max(0.15, seed_prob·SGATE[tier])` |
| `MC.overall_tier(cm)` | category-map → 10-rung overall ladder (the SINGLE copy behind col G) |
| `MC.cap_uncorroborated(member, cm)` | say-do gate (paths A/V/J); only ever lowers Champion/Defender → Ally |
| `MC.bill_corroboration()` / `MC.vote_corroboration()` / `MC.juris_corroboration()` / `MC.GATEKEEP_JURIS` | the three say-do evidence sources (all fail-open) |
| `MC.delivery_mult(m)` | say-do talker discount on target value, clip [0.70, 1.00], neutral 1.0 fallback |
| `MC.NICK_SETS` / `MC.name_variants(first)` | nickname equivalence classes for name resolution |

New-script conventions (see **moneyball-build-and-env** for the full list): UTF-8 coding header + `sys.stdout.reconfigure(encoding='utf-8', errors='replace')`; the `from paths import ROOT` bootstrap line; `print` with a meaningful final summary line (run_pipeline shows only each step's last stdout line); dump_atomic for every artifact; and a `__main__` guard if the script is ever meant to be importable.

## Provenance and maintenance

Written 2026-07-09 against the worktree at commit 88a7048 (branch claude/nifty-cray-f6d053, live tree on main). Every volatile fact below has a paste-ready re-verification command; run them from the repo root (`cd "C:\Users\pgoff\OneDrive\Desktop\Melange Systems"` — or the worktree; these are all read-only).

| Fact | Re-verify with |
|---|---|
| Spec is still the pointer-doc of record | `git log -1 --format="%h %ad" -- MATHEMATICAL_SPECIFICATION.md` and reread its header |
| Two physics formulas unchanged | `git grep -n "def cpf_diffusion" -- fec/moneyball_core.py` then read the two functions (~lines 120-125) |
| PERS_NONE default 0.45 / PERS table | `git grep -n "PERS_NONE" -- fec/moneyball_core.py` |
| SGATE['—']=0.85, TORD/overall_tier single copy | `git grep -n "SGATE=" -- fec/moneyball_core.py; git grep -n "def overall_tier" -- fec/moneyball_core.py` |
| SEED=7 / MC=20 defaults | `git grep -n "SEED=int" -- fec/budget_frontier.py fec/per_topic_coalition.py` |
| 2^62 seed-gating key offset | `git grep -n "1<<62" -- fec/per_topic_coalition.py` |
| dump_atomic implementation | `git grep -n "def dump_atomic" -- fec/moneyball_core.py` |
| Rank-authority loud failure | `git grep -n "ranks_python.json missing" -- fec/moneyball_core.py` |
| 17-step chain order | read `CHAIN` in `fec/run_pipeline.py` (lines ~19-35) |
| paths.py hardcoded ROOT | `git grep -n "MONEYBALL_ROOT" -- fec/paths.py` |
| congestion.json still has no live producer | `git grep -ln "congestion.json','w'" -- fec/` and `git grep -ln "congestion.json'" -- fec/attic/` (writers found 2026-07-09 only in fec/attic/: saturation, full_congestion, final, final_table, makeup, makeup2) |
| FEC zips still attic-only consumers | `git grep -l "weball24" -- fec/` (expect only fec/attic/*) |
| JS mirror banner + engchk badge | `git grep -n "faithful port" -- fec/templates/make_dashboard_html_00.tpl; git grep -n "updateEngChk" -- fec/templates/make_dashboard_html_00.tpl` |
| Audit still tpl-blind | `git grep -n "templates" -- fec/audit_full.py` (expect no matches) |
| JS psych parity shim present | `git grep -n "EG.pmult" -- fec/templates/make_dashboard_html_00.tpl` |
| Committee formula still Excel-only (port doc) | read the docstring of `fec/apply_committee_reweight.py` (lines 3-10); `git grep -ln "Committee Data" -- fec/` for any NEW builder |
| Corpus-relative z declaration | `git grep -n "z relative to THIS corpus" -- fec/big5_traits.py` |
| Display-only declarations | `git grep -n "display-only" -- fec/make_member_desk.py; git grep -n "separate ratified step" -- fec/make_member_desk.py` |
| Kernel test count (37 as of 2026-07-09) | `python "fec\tests\run_tests.py"` and read the final count line |
| Susceptibility formula (.40/.30/−.20/−.10) | `git grep -n "susc_trait=" -- fec/receptivity_layer.py` |
| Force-tracked data whitelist | `git ls-files -- "*.json" "*.zip" "*.txt"` (expect cu_valence_registry.json, launch.json, the fec zips, quorum_query.txt, retiring_members.txt) |
| Stale doc counts (README says 30/59 vs live 37/69) | compare README.md lines ~56-57 against actual run output — a doc-rot pass was already due 2026-07-09 |
