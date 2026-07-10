---
name: moneyball-config-and-flags
description: Load this skill when you need to know what a Moneyball environment variable does, what its default is, where it is read, or whether it is safe to change — e.g. questions like "what does DTHRESH do", "how do I revert the Bakker change", "why did my env var have no effect", "what are the pillar weights and where do they live", "is HALF the same as HALFF", "how do I add a new dial", or "which knobs are user-owned vs code-owned". It owns the complete dial catalog — every os.environ dial in fec/*.py, the workbook (Excel) dials, key kernel constants, and the add-a-dial checklist. It does NOT cover how to run the pipeline (see moneyball-run-and-operate), the rules for when a change is allowed (see moneyball-change-control), why the math is shaped this way (see moneyball-architecture-contract and influence-modeling-reference), or debugging failures (see moneyball-debugging-playbook).
---

# Moneyball configuration and flags

The Moneyball system (a Python model of the 533 members of the US Congress — who is persuadable on credit-union issues, how influence and money flow through their network) has **no config file**. It is tuned entirely by (1) environment variables with hard-coded defaults in `fec/*.py`, (2) a handful of user-typed cells in the Excel workbook, and (3) constants in `fec/moneyball_core.py` (the shared "kernel" module). An **empty environment always reproduces production behavior** — every default IS the ratified production value. This skill is the single catalog of all three tiers, plus the checklist for adding a new dial. Every default and file:line below was re-verified against the repo on 2026-07-09; line numbers drift, so use the re-verification greps at the bottom if a citation looks stale.

## When NOT to use this skill

- Actually **running** the chain, collectors, or dashboards → `moneyball-run-and-operate`.
- Deciding whether you're **allowed** to change a dial (user-gated decisions, change classes) → `moneyball-change-control`.
- Understanding **why** a constant has its value (theory, calibration history) → `moneyball-architecture-contract`, `influence-modeling-reference`, `moneyball-failure-archaeology`.
- A dial change produced **wrong output** and you're triaging → `moneyball-debugging-playbook`.
- Setting up the machine/environment from scratch → `moneyball-build-and-env`.

## Quick reference

```powershell
# cd to repo root first (path has spaces — always quote):
cd "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees\nifty-cray-f6d053"

# List EVERY env dial + its default (read-only, safe; top-level fec\*.py — attic excluded by not recursing):
Get-ChildItem fec\*.py, fec\tests\*.py | Select-String -Pattern "os\.environ"

# Check one dial's default and its inline rationale:
Select-String -Path fec\money_response.py -Pattern "DTHRESH"

# Set a dial for ONE run (PowerShell — no inline VAR=x syntax):
$env:TOPIC = 'Interchange'; python fec\budget_frontier.py   # WARNING: this RUNS the engine and WRITES to the LIVE data tree
```

Three rules before touching anything:

1. **Dials are read at IMPORT TIME.** Nearly every `fec/*.py` executes its whole body at module top level, including the `os.environ.get(...)` lines. Setting a variable mid-session does nothing to an already-imported module — you need a **fresh python process** with the variable set before launch.
2. **Import == execution == live-tree writes.** `fec/paths.py:7` resolves `ROOT` to `C:\Users\pgoff\OneDrive\Desktop\Melange Systems` (the LIVE data tree) unless `MONEYBALL_ROOT` overrides it — even from a git worktree. Never `import` a script "just to check a dial"; read the source instead. (Rule detail: `moneyball-change-control`.)
3. **Defaults = production.** If you add a dial, its default must reproduce the current behavior exactly (see the add-a-dial checklist below).

Class legend used in the tables: **P** = production-ratified calibration · **R** = revert switch (non-default rolls back a shipped, ratified change — a debug/audit tool, not a tuning knob) · **E** = experimental/validation hook · **O** = output-redirect (test isolation) · **G** = gate (spend cap / credential) · **S** = scenario/selection.

---

## 1. Environment dials — the complete catalog

### 1.1 Engine physics (class P — calibrated, user-ratified; changing these is Paul's decision)

"Net lean" = a member's money-derived disposition score; "defection" = a money shock moving a member down the stance ladder; "receipts" = a member's campaign fundraising total.

| Var | Default | Read at | Effect (one line) |
|---|---|---|---|
| `MAXSHIFT` | `18` | `fec/money_response.py:13` | Max net-lean points money can move (calibrated 40→18: money buys access, not votes) |
| `HALF` | `0.10` | `fec/money_response.py:14` | A donation equal to HALF×receipts produces half of MAXSHIFT (diminishing returns) |
| `DTHRESH` | `11.25` | `fec/money_response.py:23` | Net-lean shift needed to risk a defection; 11.25 = 18·(1/6)/((1/6)+0.10), preserving the original "≥~1/6 of receipts" boundary after the MAXSHIFT rescale (rationale comment at `money_response.py:16–22`) |
| `LOSSFRAME` | `1.10` | `fec/money_response.py:28` | A competitor threat (loss frame) moves lean more than an equal gift (loss aversion) |
| `HALFF` | `0.10` | `fec/flip_model.py:25`, `fec/per_topic_flip.py:26` | Same capacity scale mirrored in the flip engines — **see the HALF vs HALFF warning below** |
| `PERS_NONE` | `0.45` | `fec/moneyball_core.py:138` | Persuadability of a blank (`—`) stance cell; USER-RATIFIED 2026-07-02: silence never outranks a declared Ally (0.40) |
| `CONV_MAXSTEP` | `1` | `fec/optimize.py:50`, `fec/scenario.py:84` | Max stance-ladder rungs one money shock converts (caps cross-taxonomy magnitude) |
| `CEDGE` | `10000` | `fec/lt_priming.py:12`, `fec/cosponsor_route.py:10` | Base $ per peer-recruitment ask |
| `K` | `5` | `fec/cosponsor_route.py:9` | Recruitment bandwidth: one member personally whips ≤K colleagues |
| `IMPUTE_IND0` | `1` (on) | `fec/salience_shock.py:153`, `fec/per_topic_flip.py:23`, `fec/flip_model.py:38`, `fec/budget_frontier.py:21` | receipts=0 is treated as MISSING → impute the median (otherwise the ~18 no-FEC-record members look 5–10× cheaper to move); `0` reverts |
| `REPFAC` | `0.6` | `fec/budget_frontier.py:27` | Primary-win feasibility discount on electoral contest plays |
| `LELEV` | `0.8` | `fec/build_electoral.py:6` | Electoral-leverage strength (competitive seats are cheaper to move) |
| `LEV` | `1` (on) | `fec/budget_frontier.py:8` | `0` disables electoral leverage in the budget frontier |

> **HALF vs HALFF — TWO DISTINCT DIALS, SAME DEFAULT (0.10).** `HALF` lives in `money_response.py` (the money-lean curve); `HALFF` lives in `flip_model.py` / `per_topic_flip.py` (the flip engines' capacity scale). Setting one does NOT set the other. If you sweep "the half-saturation constant" and only set `HALF`, the flip engines silently keep 0.10 and your sweep is incoherent. `lt_priming.py:13` hard-codes `HALF=0.10` locally (not env at all). This split is documented in `MATHEMATICAL_SPECIFICATION.md` ("Standing dials" section: "HALFF=0.10 (flip-family capacity — DISTINCT dial, same default)").

### 1.2 Revert / kill switches (class R — each rolls back a shipped, ratified change)

| Var | Default | Read at | Non-default reverts what |
|---|---|---|---|
| `BAKKER_XCUE` | `1` (on) | `fec/lt_priming.py:38` | `0` reverts cross-party pro-cue signing (`xf()` at :39 passes cross-party cues through √(bpf_u·bpf_v); Bakker et al.: out-party cues don't persuade). **Mirrored in the dashboard JS** (`fec/templates/make_dashboard_html_00.tpl`, `prime()` around line 357) — flipping the env dial without regenerating the dashboard leaves Python and JS disagreeing |
| `RECEPT_TRAITS` | `behavioral` | `fec/receptivity_layer.py:57` | `lexical` reverts the whole disposition basis to the indicted lexical Big-Five (see `psychometrics-reference` for why it was indicted) |
| `RECEPT_N` | `behavioral` | `fec/receptivity_layer.py:66` | `text` reverts the susceptibility N-slot from behavioral reactivity_z (interview cutoff-proneness) to shrunken lexical N (pre-round-3 legacy) |
| `RECEPT_COOP` | `v2` | `fec/receptivity_layer.py:76` (@94f09cf, user-ratified and merged to main 2026-07-10) | A-slot source: `v2` = share-based cooperation_v2 (`coop_v2_candidate.json`; feeds BOTH the susc .40 and seed .10 slots; 218 uncovered members → neutral 0, never a silent fallback); `v1` = wholesale legacy revert to cooperation_z |
| `RECEPT_LAYER` | `1` (on) | `fec/moneyball_core.py:48` | `0` kills the entire receptivity layer — all engines fall back to neutral multipliers |
| `PERSONA_W` | `0.30` | `fec/receptivity_layer.py:92` | Persona-channel blend weight in susceptibility: `susc=(1−PW)·trait+PW·persona` (:126); `0` disables. **USER-RATIFIED KEEP — never propose its removal**; it reopens only on a failed 3+ rater panel to Bono & Loomis standards (session-ratified, 2026-07; master list in `moneyball-change-control`) |
| `B5_FAST` | `1` (on, opus only) | `fec/big5_llm.py:49` | `0` reverts opus fast-mode (2.5× speed at exactly 2× price); self-disarms if the org lacks preview access (:45–48). `collector_supervisor.py:160` force-pins it to `'0'` for unattended batch runs |
| `SOCIAL_SHRINK` | `1` (on) | `fec/build_media_blend.py:30` | `0` reverts thin-category social-share shrinkage (restores the one-tweet≈eight-press-releases artifact; rationale :24–29) |
| `RT_W` | `0.5` | `fec/build_media_blend.py:30` | Retweet stance weight vs an original post (an RT is amplification, not authorship); `1.0` = old behavior |
| `PRESS_DYNAMIC` | `1` (on) | `fec/build_media_blend.py:130` | `0` reverts to the frozen press archive (`press_raw_original.json`) instead of the dynamic stack-labeled feed |
| `PRESS_THIRD_W` | `0.5` | `fec/build_media_blend.py:152` | Credit discount for third-party/trade articles that merely tag a member (labels untouched — this scales CREDIT only, never relabels; stance labels are Paul's domain); `1.0` = old behavior |
| `SOCIAL_HL_YEARS` | `0.5` | `fec/build_media_blend.py:23` | Recency half-life (years) for social stance decay |
| `BP_SRC` | `cosponsor` | `fec/build_dashboard_bundle.py:100` | `aug` redefines bipartisanship on the augmented (social/press) network — **available but unratified**; only if Paul ratifies (comment :93–99) |

### 1.3 Scenario / selection / Monte-Carlo dials (class S) — DEFAULTS DIFFER PER SCRIPT

"MC" = Monte-Carlo repetitions (how many random cascade simulations are averaged).

| Var | Defaults (per consumer!) | Notes |
|---|---|---|
| `TOPIC` | `Mortgage` (`lt_priming.py:11`) · `Interchange` (`cosponsor_route.py:11`, `mc_stability_check.py:14`) · unset = all topics (`optimize.py:23`, `budget_frontier.py:9`) | Substring-matched against category names, case-insensitive. **Three different defaults — never assume a global one** |
| `MC` | `20` (`salience_shock.py:44`, `per_topic_coalition.py:6`, `budget_frontier.py:7`) · `40` (`scenario.py:27`, `cosponsor_route.py:28`) | MC=20 was validated against MC=100 (100% seed overlap, `mc_stability_check.py`) |
| `SEED` | `7` (`per_topic_coalition.py:5`, `budget_frontier.py:6`) | `salience_shock.py:44` hard-codes `SEED=7` (not env). Non-default SEED/MC **changes the output filename** to `per_topic_coalition_seed%d_mc%d.json` (`per_topic_coalition.py:74`) — downstream consumers of the unsuffixed name won't see your run |
| `MCMODE` | `0` | `cosponsor_route.py:28`; `1` enables MC cascade evaluation instead of tree-reach |
| `MAXSEEDS` | `60` | `budget_frontier.py:7` |
| `ELECTORAL` | `0` | `budget_frontier.py:26`; `1` (or `--electoral`) adds electoral contest plays and renames the output `budget_frontier_electoral.json` (:120) |
| `BRIDGE` | unset | `per_topic_flip.py:37`; `1` (or `--bridge`) directly prioritizes bridge-builders in flip targeting (GAMMA=1.2 constant on the same line) |
| `BUDGET` / `INC` / `PMAX` | `2500000` / `500` / `10000` | `optimize.py:20–21`: total joint pot / $500 allocation step / $10k per-member cap (= FEC PAC per-cycle legal limit) |
| `SAL_B0` / `SAL_BPSI` / `SAL_DELTA` | `0.05` / `0.10` / `0.5` | `salience_shock.py:91–93`: backfire base probability / backfire growth with uncertainty / defensive-appeal threshold lift |
| `SAL_PROBE` | `250000` | `salience_shock.py:135`: standardized industry-money probe used to test the defection window |
| `SAL_PSI_DAMP` | `0` (off) | `salience_shock.py:227`: built-but-dormant M4 dial — damp value on high-uncertainty issues |

### 1.4 Network / media-layer dials (class P)

| Var | Default | Read at | Effect |
|---|---|---|---|
| `ENG_CAP` | `2.0` | `fec/build_multilayer_network.py:26` | Weight cap on press-engagement edges added to the AUG network |
| `HCOI_W` | `0.2` | `fec/build_multilayer_network.py:26` | Press co-coverage (HCoI) layer weight |
| `SOC_CAP` | `2.0` | `fec/build_multilayer_network.py:83` | Weight cap on new social edges (kernel-inverse mapping w=6p/(1−p)) |
| `SOC_REINF` | `0.3` | `fec/build_multilayer_network.py:83` | Reinforcement boost on already-tied pairs with live social interaction (+30% at full strength; `0` disables) |
| `AUG_OUT` | dated production name | `fec/build_multilayer_network.py:100` | Output-path override for the AUG network file (class O) |
| `SOC_VOLFLOOR` | `25` | `fec/social_interaction_layer.py:25` | Minimum post volume before a member's social probabilities are trusted |
| `SOC_MEN_W` | `0.4` | `fec/social_interaction_layer.py:25` | Mention weight vs reply/quote in social interaction edges |
| `HCOI_CORR` / `HCOI_MINW` | `0.6` / `3.0` | `fec/press_hcoi.py:21–22` | Co-coverage correlation threshold / transient-author filter |
| `ENG_MIN_ITEMS` | `5` | `fec/press_engagement_layer.py:57` | Minimum source items before an engagement edge is minted (blocks fake P=1.0 from tiny denominators) |
| `SD_WINDOW` / `SD_CONF` / `SD_MINNB` | `91` / `0.75` / `5` | `fec/stance_dynamics.py:26,130` | Stance-dynamics window (days) / confidence threshold / minimum neighbors |
| `SC_MINW` / `SC_RESTARTS` | `0.0` / `60` | `fec/signed_coalitions.py:21–22` | Signed-coalition edge floor / clustering restarts (diagnostic) |
| `KB_DELTA` | `0.85` | `fec/kb_benchmark.py:24` | Katz-Bonacich delta as a fraction of spectral radius (diagnostic; must stay <1) |

### 1.5 Big-Five / psych dials (class E validation hooks unless marked)

| Var | Default | Read at | Effect |
|---|---|---|---|
| `LOWCONF_TOKENS` | `1500` | `fec/big5_traits.py:28` | Below this token count a member's trait z-scores are flagged low-confidence and shrunk downstream (P) |
| `BIG5_SOURCES` | all | `fec/big5_traits.py:36` | CSV subset of genres {social, CREC, INTERVIEW, CHRG} for genre-restricted scoring |
| `BIG5_BEFORE` / `BIG5_AFTER` | unset | `fec/big5_traits.py:37` | ISO-date time-slicing of speeches (test-retest hook) |
| `BIG5_HALF` | unset | `fec/big5_traits.py:206–209` | `1` or `2` = score alternating documents only (split-half reliability hook; see `psychometrics-reference`) |
| `BIG5_OUT` | production `big5_traits.json` | `fec/big5_traits.py:237` | Redirect the artifact so split halves never clobber production (O) |
| `B5_WORKERS` | `8` | `fec/big5_llm.py:43` | Thread pool for LLM scoring |
| `B5_GENRES` | `CREC,INTERVIEW` | `fec/big5_llm.py:181` | Genres scored by the LLM battery |
| `B5_NO_DUMP` | unset | `fec/big5_llm.py:383` | `1` suppresses the artifact dump |
| `B5_SCRATCH` | **DEAD PATH** | `fec/big5_hybrid.py:74`, `fec/big5_lexcal_v2.py:71`, `fec/validate_nomological.py:10` | Scratch dir for hybrid/validation experiments. The default is a hard-coded scratchpad of a long-gone worktree session — **always set it explicitly** |
| `REACT_TURNS` | `150` | `fec/behavioral_dispositions.py:103` | Graded-shrinkage scale for reactivity_z: `sh=√(min(1,turns/150))`; members with <30 turns → None (neutral). Inline note: `iv_burst` was probed and REJECTED (split-half .04) — do not add it back (:101–102) |
| `CLAUDE_AC_MODEL` | fable if `--fable` else sonnet | `fec/agency_communion_llm.py:24` | Persona-cue classifier model (LLM cost rule lives in `moneyball-change-control`) |
| `AC_NSENT` / `AC_WORKERS` | `40` / `8` | `fec/agency_communion_llm.py:26–27` | Sentences sampled per member / threads |
| `NARR_MAX` | `15` | `fec/weekly_refresh.py:103` | Weekly cap on Fable narrative generations (cost bound); `0` disables the narratives step entirely (P) |
| `REF_DYAD_CAP` / `REF_WORKERS` | `4` / `8` | `fec/member_reference_layer.py:34,229` | Scored contexts per (a→b, source) dyad / threads |
| `B5_GATE_CAP` / `REF_GATE_CAP` | `200` / `100` ($) | passed to `spend_guard` at `fec/collector_supervisor.py:163,178` (reader :130) | Unattended spend caps (G). The guard runs the script WITHOUT `--go`, parses its `est ~$X` line, and proceeds only if X ≤ cap; an unparseable estimate **fails CLOSED** (:126–141) |

### 1.6 Credentials and collectors (class G/C)

| Var / file | Read at | Notes |
|---|---|---|
| `ANTHROPIC_API_KEY` | `fec/agency_communion_llm.py:75–77`, `fec/api_stance_layer.py:34–36`, `fec/member_reference_layer.py:190–192` | Falls back to the file `fec/anthropic_key.txt` (several scripts, e.g. `big5_llm.py:33`, read the file directly). Never paste keys into chat |
| `GOVINFO_KEY` | `fec/fetch_congressional_record.py:31` | Fallback file `fec/govinfo_key.txt` |
| `X_BEARER_TOKEN` / `TRUTH_TOKEN` | `fec/tweet_collector.py:53,138,234` / `:192` | X (Twitter) / Truth Social API tokens |
| `BSKY_SKIP_FETCHED` | `fec/tweet_collector.py:98` | Skip already-fetched members in chunked Bluesky sweeps |
| `TW_MIN_POSTS` | `25` at `fec/tweet_collector.py:253` | Minimum-activity floor for the Fink influence computation |
| Vote Smart key | `fec/votesmart_npat_fetch.py:20` | A FILE, not env: `fec/votesmart_api_key.txt` (gitignored, absent). **The key file is NOT a freshness probe** — the collection was completed 517/518 on branch `claude/clever-elbakyan-15fa11` via a user-directed browser-session protocol amendment that never used the key, and the ES look was consumed there (@e77703c). Check `git log --all --oneline \| Select-String "Vote Smart"` per `moneyball-docs-and-claims` §3.2 before citing status; the collector itself stays user-gated |

### 1.7 Path / IO roots and output redirects (class O)

| Var | Default | Read at | Effect |
|---|---|---|---|
| `MONEYBALL_ROOT` | `C:\Users\pgoff\OneDrive\Desktop\Melange Systems` | `fec/paths.py:7` | THE project data root. Every script resolves from it — which is why a worktree copy still writes to the live tree |
| `MONEYBALL_DRAFT` | `C:\Users\pgoff\OneDrive\Desktop\Draft Systems` | `fec/paths.py:8` | The external R press-pipeline root |
| `FRONTIER_OUT` | production `budget_frontier.json` | `fec/budget_frontier.py:120` | Output redirect; the audit's no-clobber pattern (`audit_full.py:113` runs the engine with `TOPIC=Interchange`, `FRONTIER_OUT=<tmp>`) |
| `OPT_OUT` | production `optimize_result.json` | `fec/optimize.py:22` | Same pattern (`audit_full.py:87–89`) |
| `CONGEST` / `CATSTANCE` | production paths | `fec/budget_frontier.py:11,23` | Input overrides so scenario runs can inject alternate money/stance states |
| `CMTE_ROSTER` | **DEAD PATH** | `fec/add_judiciary_seats.py:33` | Default is a stale scratchpad of a gone session — set explicitly if ever used |
| `STAFF_SRC` | `C:\Users\pgoff\Downloads` | `fec/build_staff_directory.py:22` | Machine-local input dir (external, unregenerable source) |
| `FT_WORKERS` | `6` | `fec/press_reader_ftfix.py:24` | Fine-tune fixer thread pool |

---

## 2. Workbook dials (user-owned — Paul edits these in Excel, code only READS them)

The workbook is `Moneyball Main Version - Blended.xlsx` at the data root. Since the 2026-07-02 "system of record inversion", Python owns all derived math and the workbook is a self-refreshing VIEW — but a few **typed literal cells** remain live inputs that Python reads as data. Changing them is Paul's decision, made in Excel, never silently in code (session-ratified, 2026-07; see `moneyball-change-control`).

| Dial | Where it lives | Where code reads it | Current value (as of 2026-07-09) |
|---|---|---|---|
| **AB pillar weights** (the blend of the 4 rank pillars: legislative / press / influence / demographic) | 'Blended Model' sheet, column 28 ("AB" in Excel letters), rows 2–5 | `fec/compute_pillars.py:81` (`bm.cell(r,28)` for r in 2..5), applied at :88 as `score = AB2·leg + AB3·press + AB4·inf + AB5·dem` | **0.30 / 0.25 / 0.40 / 0.05** — verified live in `ranks_python.json` (`"ab_weights": {"2": 0.3, "3": 0.25, "4": 0.4, "5": 0.05}`); user-set 2026-07-07 |
| **Row-535 press tier weights** | 'Press Release - Normalized' sheet, row 535, columns 5–23 (one weight per press category) | `fec/moneyball_core.py:72` (`press_matrix()`); guarded by the audit | User-typed literals; survive openpyxl saves (typed cells always do) |
| **'Topic Weights' sheet** | Workbook sheet | **NOWHERE — reference-only/cosmetic.** The model uses hardcoded weights instead: `fec/per_category_stance.py:26` returns (leg .55, press .70, vote .20) for the DEFENSIVE set {Interchange, Credit Card Mandates} else (.55, .35, .10). Confirmed by the comment at `fec/apply_alloc_cap.py:54` ("Model uses hardcoded 0.70/0.35 … NOT this sheet") | Do not "fix" the model by editing this sheet — it changes nothing |
| **Category Stance edits** | Stance cells Paul edits in Excel ('Category Stance' named as a user-edit surface in `MATHEMATICAL_SPECIFICATION.md`, "User dial edits" paragraph) | Flow into `category_stance.json` via the chain; Rank & Allocation col G is a pure OUTPUT view (`per_category_stance.py:9–13`), never an input | Stance/press classification is Paul's domain — never relabel by model judgment (session-ratified, 2026-07; see `moneyball-change-control`) |

Trap: code comments can lag the workbook. Any "the weights are X" comment is untrustworthy — the ground truth for the live blend is the `ab_weights` block in `ranks_python.json` (written by `compute_pillars --write`).

---

## 3. Kernel constants worth knowing (code constants — NOT env dials)

These live in source and change only through change control. Listed so you don't mistake them for dials or re-derive them wrong.

**`fec/moneyball_core.py` (the kernel):**

| Constant | Where | Value / meaning |
|---|---|---|
| `PERS` persuadability map | :139–140 | Champion .10, Defender .12, Ally .40, Highly Persuadable .55, True Neutral/Neutral .50, Lean Skeptic .40, Skeptic .25, Opponent .08, `—` = PERS_NONE (env, .45) |
| `IMP` category importance | :141–144 | 18 categories, ABB26-handout-anchored; heaviest: Credit Card Mandates 3.0, CU Tax Status 3.0, Interchange 2.0 |
| `SGATE` seed gates | :151–153 | Per-stance seeding gate; floor 0.15 via `gate()` |
| `TORD` + `overall_tier()` cutoffs | :154, :165–167 | IMP-weighted tier score → the 10-rung overall ladder (Champion ≥2.5 … Opponent <−1.9) |
| `cpf_diffusion` | :120–122 | Cross-party diffusion factor `0.4+0.6·√(bpf_u·bpf_v)` (bpf = bipartisanship fraction) |
| `cpf_pressure` | :123–125 | Cross-party 0.5 / same-party 1.7 / else 1.0 — the kernel's TWO deliberate partisan physics |
| `build_P` cascade kernel | :132–136 | Edge activation `p = w·cpf·σ_v/(w·cpf·σ_v + 6.0)`; σ_v = receiver `edge_mult` |
| `delivery_mult` | :296–306 | Say-do talker discount on engine target value: `clip(1−0.15·max(0,gap−1), 0.70, 1.00)`; never touches rank |
| `GATEKEEP_JURIS` | :229–231 | Path-J say-do committees for {CU Tax Status, Interchange, Credit Card Mandates}; editing it is a stance-domain (Paul) decision |

**`fec/receptivity_layer.py` (per-member psych multipliers):**

| Constant | Where | Value |
|---|---|---|
| Susceptibility composite | :121 | `susc_trait = .40·coop + .30·N − .20·dil − .10·dom` (lexical mirror :124) |
| `susc_mult` | :133 | `clip(1+.18·susc, 0.70, 1.30)` |
| `edge_mult` | :134 | `clip(1+.12·susc, 0.80, 1.20)` |
| `incent_mult` | :136 | retiring → 0.60; else `clip(1+.30·(comp−0.5), 0.85, 1.15)` |
| Prospect-theory mult | :138 | loss domain 1.15 / gain 0.92 |
| **`pressure_mult` clip bounds** | :154 | `clip(susc_mult·incent·pt, 0.50, 1.60)` — **the [0.50, 1.60] engine clip** |
| `seed_prob` | :141–145 | `clip(0.60+.10·coop+.06·breadth+.04·visibility, 0.30, 0.90)` |

**Others:** `C_INT_W = 2.0` at `fec/big5_llm.py:344` — interview chunks count double for trait C (earned by the preregistered 2026-07-07 retest PASS; a CONSTANT, not env — do not try to set it from the environment). `THETA` flip thresholds `fec/lt_priming.py:16` and `BETA=1.5` :28. `RFLOOR=200000` `fec/money_response.py:15` and the 10-rung `ORDER` ladder :38–39. Threshold engine `K=1.25`, rate clamp `.10–.40`, `MINN=8`, `PRIOR=0.70` at `fec/per_category_stance.py:36–38`. `PIN={'MEM':456,'MEM_A':290}` (`fec/b5_a_matrix.py:26`) and `PIN={'MEM':456,'MEM_N':201,...}` (`fec/b5_n_matrix.py:28`) look like gates but are **pinned prereg roster constants** — a non-simulate run aborts on roster drift; never "update" them outside the prereg protocol (`moneyball-research-methodology`).

**JS mirror status (as of 2026-07-09):** the dashboard template `fec/templates/make_dashboard_html_00.tpl` mirrors kernel math in JavaScript, including `edge_mult` (tpl:330), `pressure_mult` + `delivery_mult` (tpl:340,344 — "psych parity 2026-07-09"), and the Bakker `xf()` signing (~tpl:357). Any change to these Python formulas must be re-ported by regenerating AND editing the template; JS reads no env vars.

---

## 4. Add-a-dial checklist

Use this when a change needs an escape hatch or an experiment needs a knob. A dial is the project's standard mechanism for "shipped but revertible".

1. **Name it** SCREAMING_SNAKE, short, prefixed by subsystem where one exists (`SOC_`, `SAL_`, `B5_`, `BIG5_`, `RECEPT_`, `SD_`, `HCOI_`, `REF_`, `AC_`). Avoid names one typo away from an existing dial (the HALF/HALFF pair is the cautionary tale — don't mint a third).
2. **Default = current behavior, exactly.** `os.environ.get('NAME','<current>')` where an empty environment is byte-identical to production. Never ship a dial whose default changes output.
3. **Read it once, at top level,** next to the other dials of that file, with an inline comment stating: what it does, the ratification date/status, and what the non-default value reverts or enables. The inline comment is the primary documentation — every existing dial carries one.
4. **Document it** in `MATHEMATICAL_SPECIFICATION.md` → the "## Standing dials (env; defaults = the ratified state)" section, in the same `NAME=default (one-line note)` format. That list is the spec-of-record for dials.
5. **Class it honestly**: if it guards an unratified alternative (like `BP_SRC=aug`), say "available but unratified" in the comment; unproven things stay labeled open/candidate/gated.
6. **Verification implications** (`moneyball-validation-and-qa` owns the standards): with the default set, run the standard protocol — `python fec\tests\run_tests.py`, then the chain, then **zero rank delta** vs the last `ranks_*.json` baseline, then `python fec\audit_full.py` all-clean. If the dial redirects output, teach the audit the no-clobber pattern (`FRONTIER_OUT`/`OPT_OUT` precedent at `audit_full.py:87–89,113`). If it gates spend, follow the `spend_guard` fail-CLOSED pattern (`collector_supervisor.py:126–141`).
7. **JS-mirror implications**: if the dial touches engine math that the dashboard re-implements (priming, cascade, money curve, receptivity multipliers), the JS port in `fec/templates/make_dashboard_html_00.tpl` must stay in lockstep — either the dial's effect is baked into the regenerated artifacts the JS reads, or the JS needs the same branch. `BAKKER_XCUE` is the worked example (lt_priming.py:36–37 comment).
8. **Cost dials**: anything that can spend money must dry-run-print `est ~$X` and exit without `--go` (the `big5_llm.py:253–256` pattern) so `spend_guard` can parse it.
9. **Ownership**: if the value encodes a judgment call (weights, thresholds, category membership), it is Paul's dial — ship the mechanism with the ratified default and flag the decision, don't tune it yourself (`moneyball-change-control`).

---

## 5. Known traps (all verified 2026-07-09)

- **Setting a dial did nothing** → you set it after import, or in a different process, or you edited `os.environ` in a session where the module was already loaded. Fresh process, variable first.
- **PowerShell syntax**: `$env:NAME = 'value'` then run python in the same command; there is no bash-style `NAME=x python ...` inline prefix.
- **`B5_SCRATCH` / `CMTE_ROSTER` defaults are dead paths** (hard-coded scratchpads of deleted worktree sessions). Set explicitly.
- **Non-default `SEED`/`MC` suffix the artifact filename** (`_seed%d_mc%d`) — production consumers keep reading the old unsuffixed file.
- **`TOPIC` and `MC` have per-script defaults** (see §1.3). A "same-settings" comparison across engines must set both explicitly.
- **Cost gates fail differently**: `big5_llm`/`agency_communion_llm` exit unspent without `--go`; `collector_supervisor.spend_guard` fails CLOSED on an unparseable estimate.
- **`B5_FAST` doubles cost** and is pinned off for unattended runs; Fable is reserved for the 533 member narratives only — every other LLM step is Haiku 4.5 (session-ratified, 2026-07; see `moneyball-change-control`).
- **Workbook comments lie; artifacts don't.** Trust `ranks_python.json.ab_weights` over any "weights are..." comment.
- **`attic/` scripts have their own dials** — excluded from this catalog on purpose; attic code is retired and must not be run.

---

## Provenance and maintenance

Written 2026-07-09 against worktree `nifty-cray-f6d053` (branch `claude/nifty-cray-f6d053`, merged main @88a7048). All file:line citations verified by opening the file at that line on that date. Line numbers WILL drift — re-verify with the commands below (run from the repo root; all read-only-safe).

```powershell
cd "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees\nifty-cray-f6d053"
```

| Volatile fact | Re-verification one-liner (PowerShell) |
|---|---|
| Complete env-dial inventory (any new/removed dial) | `Get-ChildItem fec\*.py, fec\tests\*.py \| Select-String -Pattern "os\.environ"` (non-recursive, so attic is excluded) |
| Any single dial's default + comment | `Select-String -Path fec\<consumer>.py -Pattern "DIALNAME"` (e.g. `Select-String -Path fec\money_response.py -Pattern "DTHRESH"`) |
| HALF vs HALFF still distinct, both 0.10 | `Get-ChildItem fec\*.py \| Select-String -Pattern "'HALFF?'"` and the spec: `Select-String -Path MATHEMATICAL_SPECIFICATION.md -Pattern "HALFF"` |
| Live pillar weights (30/25/40/5) | `[regex]::Match((Get-Content "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\ranks_python.json" -Raw), '"ab_weights"[^}]*}').Value` |
| AB-weight cell read (col 28, rows 2–5) | `Select-String -Path fec\compute_pillars.py -SimpleMatch "cell(r,28)"` |
| Row-535 press weights read | `Select-String -Path fec\moneyball_core.py -SimpleMatch "cell(535"` |
| Topic Weights sheet still cosmetic | `Get-ChildItem fec -Recurse -Filter *.py \| Select-String -Pattern "Topic Weights"` (expect only the apply_alloc_cap cosmetic note) |
| Receptivity clip bounds (.70–1.30 / .50–1.60 / .30–.90) | `Select-String -Path fec\receptivity_layer.py -SimpleMatch "clip("` |
| PERS map + PERS_NONE | `Select-String -Path fec\moneyball_core.py -Pattern "PERS_NONE","PERS="` |
| MC/SEED/TOPIC per-script defaults | `Get-ChildItem fec\*.py \| Select-String -Pattern "get\('MC'","get\('SEED'","get\('TOPIC'"` |
| Spend caps + fail-CLOSED guard | `Select-String -Path fec\collector_supervisor.py -Pattern "B5_GATE_CAP","REF_GATE_CAP","failing CLOSED"` |
| JS psych parity still present | `Select-String -Path fec\templates\make_dashboard_html_00.tpl -Pattern "psych parity","pressure_mult","xf"` |
| Spec dial list still current | `Select-String -Path MATHEMATICAL_SPECIFICATION.md -Pattern "Standing dials" -Context 0,6` |
| C_INT_W still a constant (not env) | `Select-String -Path fec\big5_llm.py -Pattern "C_INT_W"` |
| Vote Smart key still file-based; live route status | `Select-String -Path fec\votesmart_npat_fetch.py -Pattern "votesmart_api_key"` — and for STATUS use `git log --all --oneline \| Select-String "Vote Smart"` (per `moneyball-docs-and-claims` §3.2), NOT a key-file existence probe (§1.6) |
| Prereg roster pins | `Select-String -Path fec\b5_a_matrix.py, fec\b5_n_matrix.py -SimpleMatch "PIN = {"` |
