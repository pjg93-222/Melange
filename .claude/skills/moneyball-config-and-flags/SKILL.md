---
name: moneyball-config-and-flags
description: Load this skill when you need to know what a Moneyball environment variable does, what its default is, where it is read, or whether it is safe to change — e.g. questions like "what does DTHRESH do", "how do I revert the Bakker change", "why did my env var have no effect", "what are the pillar weights and where do they live", "is HALF the same as HALFF", "how do I add a new dial", or "which knobs are user-owned vs code-owned". It owns the complete dial catalog — every os.environ dial in fec/**/*.py (recursive; the pre-reorg `fec/*.py` phrasing now covers only 12 of 638 files), the workbook (Excel) dials, key kernel constants, and the add-a-dial checklist. It does NOT cover how to run the pipeline (see moneyball-run-and-operate), the rules for when a change is allowed (see moneyball-change-control), why the math is shaped this way (see moneyball-architecture-contract and influence-modeling-reference), or debugging failures (see moneyball-debugging-playbook).
---

# Moneyball configuration and flags

The Moneyball system (a Python model of the 533 members of the US Congress — who is persuadable on credit-union issues, how influence and money flow through their network) has **no config file**. It is tuned entirely by (1) environment variables with hard-coded defaults throughout `fec/**/*.py`, (2) a handful of user-typed cells in the Excel workbook, and (3) constants in `fec/moneyball_core.py` (the shared "kernel" module). An **empty environment always reproduces production behavior** — every default IS the ratified production value. This skill is the single catalog of all three tiers, plus the checklist for adding a new dial. Every default and file:line below was re-verified on 2026-07-09, **before the 2026-08 package reorg** — treat pre-reorg citations as approximate and re-derive with the greps at the bottom.

> **COVERAGE, stated honestly (census 2026-08-19, recursive over 638 files).** The tree holds **239 distinct env names at 443 read sites across 169 files**; this catalog documents **96**. **~140 live dials are UNDOCUMENTED**, including whole families — `PRIMACY_*` (7), `LEGISLATION_SHADOW_*` (4), `NARRATIVE_*` (6), `CU_*_CHANNEL` (5), `INDUSTRY_TIERS_*` (4), and ~40 collector dials (`ACS_*`, `CBP_*`, `HMDA_*`, `LODES_*`, …). The network/sector family was added 2026-08-19; the rest of the gap is real and open. **Do not read a dial’s absence here as evidence it does not exist.**

## When NOT to use this skill

- Actually **running** the chain, collectors, or dashboards → `moneyball-run-and-operate`.
- Deciding whether you're **allowed** to change a dial (user-gated decisions, change classes) → `moneyball-change-control`.
- Understanding **why** a constant has its value (theory, calibration history) → `moneyball-architecture-contract`, `influence-modeling-reference`, `moneyball-failure-archaeology`.
- A dial change produced **wrong output** and you're triaging → `moneyball-debugging-playbook`.
- Setting up the machine/environment from scratch → `moneyball-build-and-env`.

## Quick reference

```powershell
# cd to repo root first (path has spaces — always quote):
cd "C:\Users\pgoff\OneDrive\Desktop\Melange Systems"   # or any worktree of this repo (read-only commands only)

# List EVERY env dial + its default (read-only, safe; top-level fec\*.py — attic excluded by not recursing):
Get-ChildItem fec -Recurse -Filter *.py \| Where-Object FullName -notmatch "_quarantine|__pycache__" | Select-String -Pattern "os\.environ|from os import environ"

# Check one dial's default and its inline rationale:
Select-String -Path fec\engine\money_response.py -Pattern "DTHRESH"

# Set a dial for ONE run (PowerShell — no inline VAR=x syntax):
$env:TOPIC = 'Interchange'; python fec\engine\budget_frontier.py   # WARNING: this RUNS the engine and WRITES under ROOT — the LIVE data tree when run from the live root; a git-worktree run targets that worktree's EMPTY data plane unless MONEYBALL_ROOT points at LIVE (fec/paths.py:7-8; corrected 2026-09-30)
```

Three rules before touching anything:

1. **Dials are read at IMPORT TIME.** Nearly every `fec/*.py` executes its whole body at module top level, including the `os.environ.get(...)` lines. Setting a variable mid-session does nothing to an already-imported module — you need a **fresh python process** with the variable set before launch.
2. **Import == execution == data-plane writes.** `fec/paths.py:7-8` sets ROOT to `MONEYBALL_ROOT` when set, else to the parent of the imported paths.py, so a script run from a git worktree targets that worktree's EMPTY data plane; with `MONEYBALL_ROOT` pointed at LIVE, writes DO land in LIVE. `fec/tests/run_tests.py` resolves its own root from `__file__` and ignores `MONEYBALL_ROOT`. Never `import` a script "just to check a dial"; read the source instead. (Rule detail: `moneyball-change-control` law 7.) (corrected 2026-09-30; verified against `fec/paths.py:7-8`, `fec/tests/run_tests.py:8`)
3. **Defaults = production.** If you add a dial, its default must reproduce the current behavior exactly (see the add-a-dial checklist below).

Class legend used in the tables: **P** = production-ratified calibration · **R** = revert switch (non-default rolls back a shipped, ratified change — a debug/audit tool, not a tuning knob) · **E** = experimental/validation hook · **O** = output-redirect (test isolation) · **G** = gate (spend cap / credential) · **S** = scenario/selection · **D** = display-only (used in §1.8) · **X** = **guard bypass — setting it makes the system ACCEPT something it would otherwise refuse**.

> **Why X exists (added 2026-08-19).** Guard-bypass dials were previously scattered through the O and R tables, which reads as "harmless redirect" and "reversible switch". They are neither: each one disables a fail-closed check that exists because something went wrong once. They are now marked X and collected in §1.16 so they are visually separable at a glance. An O redirect writes your output somewhere else; an X dial lets bad data through.

---

## 1. Environment dials — the complete catalog

### 1.1 Engine physics (class P — calibrated, user-ratified; changing these is Paul's decision)

"Net lean" = a member's money-derived disposition score; "defection" = a money shock moving a member down the stance ladder; "receipts" = a member's campaign fundraising total.

| Var | Default | Read at | Effect (one line) |
|---|---|---|---|
| `MAXSHIFT` | `18` | `fec/engine/money_response.py:13` | Max net-lean points money can move (calibrated 40→18: money buys access, not votes) |
| `HALF` | `0.10` | `fec/engine/money_response.py:14` | A donation equal to HALF×receipts produces half of MAXSHIFT (diminishing returns) |
| `DTHRESH` | `11.25` | `fec/engine/money_response.py:23` | Net-lean shift needed to risk a defection; 11.25 = 18·(1/6)/((1/6)+0.10), preserving the original "≥~1/6 of receipts" boundary after the MAXSHIFT rescale (rationale comment at `money_response.py:16–22`) |
| `LOSSFRAME` | `1.10` | `fec/engine/money_response.py:28` | A competitor threat (loss frame) moves lean more than an equal gift (loss aversion) |
| `HALFF` | `0.10` | `fec/engine/flip_model.py:25`, `fec/engine/per_topic_flip.py:26` | Same capacity scale mirrored in the flip engines — **see the HALF vs HALFF warning below** |
| `PERS_NONE` | `0.45` | `fec/moneyball_core.py:430` | Persuadability of a blank (`—`) stance cell. `'—'` = `PERS_NONE` = 0.45, user-ratified 2026-07-02 as "Ally parity" (silence never outranks a declared Ally); the code has Ally = 0.40 (`fec/moneyball_core.py:430-431`), so parity does not currently hold — open ruling N6, Paul's; do not change either value in code (corrected 2026-09-30; verified against `fec/moneyball_core.py:430-431`) |
| `OVERALL_OPPONENT_CUTOFF` | `-1.60` | `fec/moneyball_core.py:214` | Overall scores below this cutoff are Opponents; USER-RATIFIED 2026-07-15 to populate the previously empty rung. Higher values create more Opponents; `-2.50` reverts |
| `CONV_MAXSTEP` | `1` | `fec/engine/optimize.py:50`, `fec/engine/scenario.py:84` | Max stance-ladder rungs one money shock converts (caps cross-taxonomy magnitude) |
| `CEDGE` | `10000` | `fec/engine/lt_priming.py:12`, `fec/engine/cosponsor_route.py:10` | Base $ per peer-recruitment ask |
| `K` | `5` | `fec/engine/cosponsor_route.py:9` | Recruitment bandwidth: one member personally whips ≤K colleagues |
| `IMPUTE_IND0` | `1` (on) | `fec/engine/salience_shock.py:145`, `fec/engine/per_topic_flip.py:23`, `fec/engine/flip_model.py:41`, `fec/engine/budget_frontier.py:29` | The industry-money dial, not a receipts dial: industry money (banks+finserv) gets the median only when `industry_money_missing()` (`fec/engine/money_observation.py:4-13`) finds no verified or observed money, in exactly these four engines; `0` disables it. That 2026-09-08 rule is recorded on main but not ratified (Project Brain D-051, ruling R2). `receipts=0/null` (MISSING FEC data) is median-imputed unconditionally, with no dial, in `money_response.py` (`receipts()`), `flip_model.py`, `per_topic_flip.py` and `lt_priming.py` (corrected 2026-09-30; verified against the four read sites) |
| `REPFAC` | `0.6` | `fec/engine/budget_frontier.py:27` | Primary-win feasibility discount on electoral contest plays |
| `LELEV` | `0.8` | `fec/engine/build_electoral.py:6` | Electoral-leverage strength (competitive seats are cheaper to move) |
| `LEV` | `1` (on) | `fec/engine/budget_frontier.py:8` | `0` disables electoral leverage in the budget frontier |

> **HALF vs HALFF — TWO DISTINCT DIALS, SAME DEFAULT (0.10).** `HALF` lives in `money_response.py` (the money-lean curve); `HALFF` lives in `flip_model.py` / `per_topic_flip.py` (the flip engines' capacity scale). Setting one does NOT set the other. If you sweep "the half-saturation constant" and only set `HALF`, the flip engines silently keep 0.10 and your sweep is incoherent. `lt_priming.py:13` hard-codes `HALF=0.10` locally (not env at all). This split is documented in `MATHEMATICAL_SPECIFICATION.md` ("Standing dials" section: "HALFF=0.10 (flip-family capacity — DISTINCT dial, same default)").

### 1.2 Revert / kill switches (class R — each rolls back a shipped, ratified change)

| Var | Default | Read at | Non-default reverts what |
|---|---|---|---|
| `BAKKER_XCUE` | `1` (on) | `fec/engine/lt_priming.py:38` | `0` reverts cross-party pro-cue signing (`xf()` at :39 passes cross-party cues through √(bpf_u·bpf_v); Bakker et al.: out-party cues don't persuade). **Mirrored in the dashboard JS** (`fec/surfaces/templates/make_dashboard_html_00.tpl`, `prime()` around line 357) — flipping the env dial without regenerating the dashboard leaves Python and JS disagreeing |
| `RECEPT_TRAITS` | `behavioral` | `fec/members/receptivity_layer.py:57` | `lexical` reverts the whole disposition basis to the indicted lexical Big-Five (see `psychometrics-reference` for why it was indicted) |
| `RECEPT_N` | `behavioral` | `fec/members/receptivity_layer.py:66` | `text` reverts the susceptibility N-slot from behavioral reactivity_z (interview cutoff-proneness) to shrunken lexical N (pre-round-3 legacy) |
| `RECEPT_COOP` | `v2` | `fec/members/receptivity_layer.py:76` (@94f09cf, user-ratified and merged to main 2026-07-10) | A-slot source: `v2` = share-based cooperation_v2 (`coop_v2_candidate.json`; feeds BOTH the susc .40 and seed .10 slots; 218 uncovered members → neutral 0, never a silent fallback); `v1` = wholesale legacy revert to cooperation_z |
| `RECEPT_LAYER` | `1` (on) | `fec/moneyball_core.py:48` | `0` kills the entire receptivity layer — all engines fall back to neutral multipliers |
| `PERSONA_W` | `0.30` | `fec/members/receptivity_layer.py:92` | Persona-channel blend weight in susceptibility: `susc=(1−PW)·trait+PW·persona` (:126); `0` disables. **USER-RATIFIED KEEP — never propose its removal**; it reopens only on a failed 3+ rater panel to Bono & Loomis standards (session-ratified, 2026-07; master list in `moneyball-change-control`) |
| `B5_FAST` | `1` (on, opus only) | `fec/members/big5_llm.py:49` | `0` reverts opus fast-mode (2.5× speed at exactly 2× price); self-disarms if the org lacks preview access (:45–48). `collector_supervisor.py:160` force-pins it to `'0'` for unattended batch runs |
| `SOCIAL_SHRINK` | `1` (on) | `fec/stance/build_media_blend.py:30` | `0` reverts thin-category social-share shrinkage (restores the one-tweet≈eight-press-releases artifact; rationale :24–29) |
| `RT_W` | `0.5` | `fec/stance/build_media_blend.py:30` | Retweet stance weight vs an original post (an RT is amplification, not authorship); `1.0` = old behavior |
| `PRESS_DYNAMIC` | `1` (on) | `fec/stance/build_media_blend.py:130` | `0` reverts to the frozen press archive (`press_raw_original.json`) instead of the dynamic stack-labeled feed |
| `PRESS_THIRD_W` | `0.5` | `fec/stance/build_media_blend.py:152` | Credit discount for third-party/trade articles that merely tag a member (labels untouched — this scales CREDIT only, never relabels; stance labels are Paul's domain); `1.0` = old behavior |
| `SOCIAL_HL_YEARS` | `0.5` | `fec/stance/build_media_blend.py:23` | Recency half-life (years) for social stance decay |
| `PRESS_URL_CANON` | `2` (release identity) | `fec/press_stream.py` (beside `release_url_key`) | `1` restores the legacy ingest key byte for byte, re-admitting one release counted under two URL forms: 11 aliased pairs (same member, date and title; a 12th candidate, Vargas, reuses one headline on two dates and is kept as a different release), 6 of them with more than one `used` row (2026-09-19, packet `audits/laundry_list_closeout_20260918` A5). Reached ONLY through `tone_turn_key`, never through `canonical_url` — folding the path rules into `canonical_url` collapses the press router's primary basis from 627 api-target hits to 93 (receipt `fixM/m2_canon_candidates.out.txt`). Merged rows stay visible in `press_component_meta.json.tone_ingest_dedup`. **Engine input** — moves the press pillar for one member (Roger Marshall, Interchange) once the chain runs |
| `CROSSPOST_KEY_CHARS` | `0` (whole statement) | `fec/stance/media_rules.py` (beside `crosspost_key`) | `120` restores the truncated cross-post duplicate key byte for byte, re-creating 445 of 1,434 FALSE duplicate groups (2026-09-19, packet `audits/laundry_list_closeout_20260918` A3). Separate from `normalized_text`, which stays the 120-char `tweet_stance_final` JOIN key and must not move. **Engine input** via `build_media_blend.py`'s `_event` key; at `CROSSPOST_DEDUP=0` no score changes (measured identical, 5,722 scored either way) — it corrects 298 desk notes and 289 rows the `CROSSPOST_DEDUP=1` rollback would have wrongly dropped |
| `BP_SRC` | `cosponsor` | `fec/surfaces/build_dashboard_bundle.py:100` | `aug` redefines bipartisanship on the augmented (social/press) network — **available but unratified**; only if Paul ratifies (comment :93–99) |
| `CONTESTED_V1` | RESERVED (no reader yet) | future coalition-builder consumer of `fec/lobbying/contested_bills.py` | `0` will ignore the contested-bills registry entirely once a consumer ships (2026-07-31 design, user-ratified "Apply"); until that consumer's own APPLY, the dial is documentation-only — nothing reads it |

### 1.3 Scenario / selection / Monte-Carlo dials (class S) — DEFAULTS DIFFER PER SCRIPT

"MC" = Monte-Carlo repetitions (how many random cascade simulations are averaged).

| Var | Defaults (per consumer!) | Notes |
|---|---|---|
| `TOPIC` | `Mortgage` (`lt_priming.py:11`) · `Interchange` (`cosponsor_route.py:11`, `mc_stability_check.py:14`) · unset = all topics (`optimize.py:23`, `budget_frontier.py:9`) | Substring-matched against category names, case-insensitive. **Three different defaults — never assume a global one** |
| `MC` | `20` (`salience_shock.py:44`, `per_topic_coalition.py:6`, `budget_frontier.py:7`) · `40` (`scenario.py:27`, `cosponsor_route.py:28`) | MC=20 was validated against MC=100 (100% seed overlap, `mc_stability_check.py`) |
| `SEED` | `7` (`per_topic_coalition.py:5`, `budget_frontier.py:6`) | `salience_shock.py:44` hard-codes `SEED=7` (not env). Non-default SEED/MC **changes the output filename** to `per_topic_coalition_seed%d_mc%d.json` (`per_topic_coalition.py:74`) — downstream consumers of the unsuffixed name won't see your run |
| `MCMODE` | `0` | `cosponsor_route.py:28`; `1` enables MC cascade evaluation instead of tree-reach |
| `MAXSEEDS` | `60` | `budget_frontier.py:7` |
| `ELECTORAL` | `0` | `budget_frontier.py:26`; `1` (or `--electoral`) adds electoral contest plays and renames the output `data\money\budget_frontier_electoral.json` (:152; corrected 2026-09-30) |
| `BRIDGE` | unset | `per_topic_flip.py:37`; `1` (or `--bridge`) directly prioritizes bridge-builders in flip targeting (GAMMA=1.2 constant on the same line) |
| `BUDGET` / `INC` / `PMAX` | `2500000` / `500` / `10000` | `optimize.py:20–21`: total joint pot / $500 allocation step / $10k per-member cap (= FEC PAC per-cycle legal limit) |
| `SAL_B0` / `SAL_BPSI` / `SAL_DELTA` | `0.05` / `0.10` / `0.5` | `salience_shock.py:91–93`: backfire base probability / backfire growth with uncertainty / defensive-appeal threshold lift |
| `SAL_PROBE` | `250000` | `salience_shock.py:135`: standardized industry-money probe used to test the defection window |
| `SAL_PSI_DAMP` | `0` (off) | `salience_shock.py:227`: built-but-dormant M4 dial — damp value on high-uncertainty issues |

### 1.4 Network / media-layer dials (class P)

| Var | Default | Read at | Effect |
|---|---|---|---|
| `ENG_CAP` | `2.0` | `fec/network/build_multilayer_network.py:26` | Weight cap on press-engagement edges added to the AUG network |
| `HCOI_W` | `0.2` | `fec/network/build_multilayer_network.py:26` | Press co-coverage (HCoI) layer weight |
| `SOC_CAP` | `2.0` | `fec/network/build_multilayer_network.py:83` | Weight cap on new social edges (kernel-inverse mapping w=6p/(1−p)) |
| `SOC_REINF` | `0.3` | `fec/network/build_multilayer_network.py:83` | Reinforcement boost on already-tied pairs with live social interaction (+30% at full strength; `0` disables) |
| `AUG_OUT` | dated production name | `fec/network/build_multilayer_network.py:100` | Output-path override for the AUG network file (class O) |
| `SOC_VOLFLOOR` | `25` | `fec/network/social_interaction_layer.py:25` | Minimum post volume before a member's social probabilities are trusted |
| `SOC_MEN_W` | `0.4` | `fec/network/social_interaction_layer.py:25` | Mention weight vs reply/quote in social interaction edges |
| `HCOI_CORR` / `HCOI_MINW` | `0.6` / `3.0` | `fec/network/press_hcoi.py:21–22` | Co-coverage correlation threshold / transient-author filter |
| `ENG_MIN_ITEMS` | `5` | `fec/network/press_engagement_layer.py:57` | Minimum source items before an engagement edge is minted (blocks fake P=1.0 from tiny denominators) |
| `SD_WINDOW` / `SD_CONF` / `SD_MINNB` | `91` / `0.75` / `5` | `fec/stance/stance_dynamics.py:26,130` | Stance-dynamics window (days) / confidence threshold / minimum neighbors |
| `SC_MINW` / `SC_RESTARTS` | `0.0` / `60` | `fec/network/signed_coalitions.py:21–22` | Signed-coalition edge floor / clustering restarts (diagnostic) |
| `KB_DELTA` | `0.85` | `fec/engine/kb_benchmark.py:24` | Katz-Bonacich delta as a fraction of spectral radius (diagnostic; must stay <1) |

### 1.5 Big-Five / psych dials (class E validation hooks unless marked)

| Var | Default | Read at | Effect |
|---|---|---|---|
| `LOWCONF_TOKENS` | `1500` | `fec/members/big5_traits.py:28` | Below this token count a member's trait z-scores are flagged low-confidence and shrunk downstream (P) |
| `BIG5_SOURCES` | all | `fec/members/big5_traits.py:36` | CSV subset of genres {social, CREC, INTERVIEW, CHRG} for genre-restricted scoring |
| `BIG5_BEFORE` / `BIG5_AFTER` | unset | `fec/members/big5_traits.py:37` | ISO-date time-slicing of speeches (test-retest hook) |
| `BIG5_HALF` | unset | `fec/members/big5_traits.py:206–209` | `1` or `2` = score alternating documents only (split-half reliability hook; see `psychometrics-reference`) |
| `BIG5_OUT` | production `big5_traits.json` | `fec/members/big5_traits.py:237` | Redirect the artifact so split halves never clobber production (O) |
| `B5_WORKERS` | `8` | `fec/members/big5_llm.py:43` | Thread pool for LLM scoring |
| `B5_GENRES` | `CREC,INTERVIEW` | `fec/members/big5_llm.py:181` | Genres scored by the LLM battery |
| `B5_NO_DUMP` | unset | `fec/members/big5_llm.py:383` | `1` suppresses the artifact dump |
| `B5_COMPOSITE` | **DEAD PATH** | `fec/members/big5_hybrid.py:74`, `fec/members/big5_lexcal_v2.py:71`, `fec/members/validate_nomological.py:10` | Scratch dir for hybrid/validation experiments. The default is a hard-coded scratchpad of a long-gone worktree session — **always set it explicitly** |
| `REACT_TURNS` | `150` | `fec/members/behavioral_dispositions.py:103` | Graded-shrinkage scale for reactivity_z: `sh=√(min(1,turns/150))`; members with <30 turns → None (neutral). Inline note: `iv_burst` was probed and REJECTED (split-half .04) — do not add it back (:101–102) |
| `CLAUDE_AC_MODEL` | fable if `--fable` else sonnet | `fec/members/agency_communion_llm.py:24` | Persona-cue classifier model (LLM cost rule lives in `moneyball-change-control`) |
| `AC_NSENT` / `AC_WORKERS` | `40` / `8` | `fec/members/agency_communion_llm.py:26–27` | Sentences sampled per member / threads |
| ~~`NARR_MAX`~~ | — | **RETIRED — zero readers in `fec/**`** | WAS the weekly Fable narrative cap. Verified 2026-08-19: no reader anywhere; the paid narrative chain is retired (`fec/weekly_refresh.py:157-161`) and regeneration is manual via `b5_narratives_local.py` at $0. **Setting this does nothing** |
| `REF_DYAD_CAP` / `REF_WORKERS` | `4` / `8` | `fec/members/member_reference_layer.py:34,229` | Scored contexts per (a→b, source) dyad / threads |
| `B5_GATE_CAP` / `REF_GATE_CAP` | `200` / `100` ($) | passed to `spend_guard` at `fec/collector_supervisor.py:163,178` (reader :130) | Unattended spend caps (G). The guard runs the script WITHOUT `--go`, parses its `est ~$X` line, and proceeds only if X ≤ cap; an unparseable estimate **fails CLOSED** (:126–141) |

### 1.6 Credentials and collectors (class G/C)

| Var / file | Read at | Notes |
|---|---|---|
| `ANTHROPIC_API_KEY` | `fec/members/agency_communion_llm.py:75–77`, `fec/stance/api_stance_layer.py:34–36`, `fec/members/member_reference_layer.py:190–192` | Falls back to the file `fec/anthropic_key.txt` (several scripts, e.g. `big5_llm.py:33`, read the file directly). Never paste keys into chat |
| `GOVINFO_KEY` | `fec/fetch_congressional_record.py:31` | Fallback file `fec/govinfo_key.txt` |
| `X_BEARER_TOKEN` / `TRUTH_TOKEN` | `fec/tweet_collector.py:53,138,234` / `:192` | X (Twitter) / Truth Social API tokens |
| `BSKY_SKIP_FETCHED` | `fec/tweet_collector.py:98` | Skip already-fetched members in chunked Bluesky sweeps |
| `TW_MIN_POSTS` | `25` at `fec/tweet_collector.py:253` | Minimum-activity floor for the Fink influence computation |
| Vote Smart key | `fec/members/votesmart_npat_fetch.py:20` | A FILE, not env: `fec/votesmart_api_key.txt` (gitignored, absent). **The key file is NOT a freshness probe** — the collection was completed 517/518 on branch `claude/clever-elbakyan-15fa11` via a user-directed browser-session protocol amendment that never used the key, and the ES look was consumed there (@e77703c). Check `git log --all --oneline \| Select-String "Vote Smart"` per `moneyball-docs-and-claims` §3.2 before citing status; the collector itself stays user-gated |

### 1.7 Path / IO roots and output redirects (class O)

| Var | Default | Read at | Effect |
|---|---|---|---|
| `MONEYBALL_ROOT` | unset → the parent of the imported `paths.py` (`C:\Users\pgoff\OneDrive\Desktop\Melange Systems` from the live tree) | `fec/paths.py:8` | THE project data root. `fec/paths.py:7-8` sets ROOT to `MONEYBALL_ROOT` when set, else to the parent of the imported paths.py, so a script run from a git worktree targets that worktree's EMPTY data plane; with `MONEYBALL_ROOT` pointed at LIVE, writes DO land in LIVE. `fec/tests/run_tests.py` resolves its own root from `__file__` and ignores `MONEYBALL_ROOT`. See `moneyball-change-control` law 7 (corrected 2026-09-30; verified against `fec/paths.py:7-8`) |
| `MONEYBALL_DRAFT` | unset → `ROOT\..\Draft Systems` (`C:\Users\pgoff\OneDrive\Desktop\Draft Systems` from the live tree; from a worktree, `.claude\worktrees\Draft Systems`, which does not exist) | `fec/paths.py:14` | The external R press-pipeline root (corrected 2026-09-30; verified against `fec/paths.py:14`) |
| `FRONTIER_OUT` | production `data\money\budget_frontier[_electoral].json` (`fec/engine/budget_frontier.py:152`) | `fec/engine/budget_frontier.py:153` | Output redirect; the audit's no-clobber pattern (`audit_full.py:212` runs the engine with `TOPIC=Interchange`, `FRONTIER_OUT=data\system\audit_scratch\_audit_tmp_frontier.json`) (corrected 2026-09-30; verified against `fec/engine/budget_frontier.py:152-153`, `fec/audit/audit_full.py:173,212`) |
| `OPT_OUT` | production `optimize_result.json` | `fec/engine/optimize.py:33` | Same pattern (`audit_full.py:176`, into `data\system\audit_scratch\`) (corrected 2026-09-30; verified against `fec/engine/optimize.py:33`, `fec/audit/audit_full.py:173-176`) |
| `CONGEST` / `CATSTANCE` | production paths | `fec/engine/budget_frontier.py:11,23` | Input overrides so scenario runs can inject alternate money/stance states |
| `CMTE_ROSTER` | **DEAD PATH** | `fec/engine/add_judiciary_seats.py:33` | Default is a stale scratchpad of a gone session — set explicitly if ever used |
| `STAFF_SRC` | `C:\Users\pgoff\Downloads` | `fec/members/build_staff_directory.py:22` | Machine-local input dir (external, unregenerable source) |
| `FT_WORKERS` | `6` | `fec/stance/press_reader_ftfix.py:24` | Fine-tune fixer thread pool |
| `FEC_SPENDING_OUT` | `%LOCALAPPDATA%\Melange\fec_spending\derived` | `fec/lobbying/build_opposition_prior.py` (`_build_parser`), `fec/collect_fec_spending.py` | Derived-output dir for the FEC precognition lane; the opposition-prior builder additionally REFUSES any `--out` inside MB_ROOT (deliberately data-plane-independent) |
| `CONTESTED_BILLS_PATH` | `MB_ROOT\contested_bills.json` | `fec/lobbying/contested_bills.py` (`registry_path`) | Path override for the per-bill contested/advisory registry (2026-07-31, user-ratified "Apply"). ABSENT FILE = standard mode everywhere — that is the shipped default; the file is deliberately not created. A present-but-unreadable registry fails loud, never absent |

### 1.8 Member-desk display dials (class D — display-only; none can move a rank)

| Var | Default | Read at | Effect (one line) |
|---|---|---|---|
| `DESK_FOOTPRINT` | `1` (on) | `fec/surfaces/make_member_desk.py:610` | `0` reverts the whole interviews+hearings+bluesky media-footprint section (2026-07-16) |
| `DESK_MEDIA_CAP` | `50` | `fec/surfaces/make_member_desk.py:611` | Per member+source recency cap on footprint rows; `0` = show all; graded-stance rows are EXEMPT from the cap (they skew old) |
| `DESK_MEDIA_STANCE` | `1` (on) | `fec/surfaces/make_member_desk.py` (search `DESK_MEDIA_STANCE`) | `0` reverts the interview/hearing CU-stance chip + transcript-passage display (2026-07-19); fingerprinted by `fec/audit/dashboard_integrity.py`, so flipping it legitimately changes the integrity input hash |
| `REF_PRESS_OWN_DOMAIN` / `REF_ROSTER_FILTER` / `REF_IDENTICAL_ONCE` | `1` each | `fec/members/member_reference_layer.py` (rules in `fec/members/reference_filters.py`) | Member-reference admission filters (2026-09-19, packet `audits/laundry_list_closeout_20260918` B6/B4/B5): a PRESS headline counts only off the speaker's own .house.gov/.senate.gov domain; roll-call rosters and signature blocks are not references; identical windows on one edge count once in n_scored/pos/neg/neu while n_raw keeps every mention. Each `0` restores the prior behaviour exactly; the census lands in the artifact's `admission_filters` block. NOT an engine input: no step up to `compute_pillars` reads `member_references.json`; takes effect at the next `--rebuild` |
| `LEG_SPONSOR_FROM_COLUMN` | `1` | `fec/legislation/sponsor_column.py` (hooked in `build_archive_legislative.py`) | The bill archive's bill-level `Sponsor` column mints the sponsor-role rows the archive names but never rowed; each row then passes every unchanged producer gate (2026-09-19, packet `audits/laundry_list_closeout_20260918` F1/N4). `0` synthesises nothing. **Engine input**, rank-moving: Tim Scott / Member Business Lending 10.76 -> 17.00 on the 20260825 archive; no other cell moves |
| `DESK_PRESS_SOURCE` | `engine` (the ranking engine's stream, unioned with the sheet) | `fec/surfaces/desk_press_source.py` (beside `desk_press_rows`) | `sheet` restores the pre-2026-09-19 workbook-only path byte for byte (packet `audits/laundry_list_closeout_20260918` A1). The desk read workbook sheet `Press Release Articles`, which no chain script writes — it arrives from the external R pipeline — while the engine reads `fec/press_stream.py`: **291 engine rows had no sheet row, 221 of them scoring**, so press that moved a member's rank was invisible on that member's desk. Under `engine` the desk walks every sheet row unchanged and then the engine rows the sheet has no release key for: **288 rows added across 146 members, 0 removed, 0 existing rows changed** (receipt `fixN1/n1_desk_press_union.out.txt`). The SHEET wins the overlap, measured: on the 2,376 shared keys the CSV disagrees on `date` (2,138 — it stores `M/D/YYYY`, which `fdate()` blanks), `score_graded` (1,207), `stance_src` (493) and **the displayed stance label (57)**, and press classification is Paul's domain. **Display only** — no engine input, rank input or stance label moves; `say_do_gap.json` (a self-declared NON-chain diagnostic) is the only downstream artifact whose numbers move. Fingerprinted by `fec/audit/dashboard_integrity.py` together with the two tone files and the refresh receipt. NEW FAILURE MODE: the desk now inherits `press_stream.validate_refresh_receipt()`, so a mixed or uncommitted refresh output set stops the desk build; `sheet` is the documented way past it |
| `IV_TURN_TAGS` | `2` (repaired) | `fec/members/fetch_interviews.py` (rules in the pure `fec/members/turn_tags.py`) | The interview collector's TURN-BOUNDARY grammar (2026-09-19, packet `audits/laundry_list_closeout_20260918` R1 d / N12). The legacy `LABEL` (`:202`), `INLINE_LABEL` (`:97`) and `MIXED_LABEL` (`:421`) accepted only an ALL-CAPS tag anchored at LINE start, so a backtick (`O`DONNELL:`, 1,434 occurrences on MS NOW), any lower-case parenthetical (`WALLACE (voice-over):`), a bracketed timestamp and PBS's `", U.S. <Title>:"` witness tail were not boundaries — **the next speaker's words stayed inside the previous member's row in 5,835 of 153,576 stored rows** (MS NOW 8.7%, CNN 4.5%, PBS / NPR / C-SPAN 0%; graded 40/40 and 72/72). `1` restores all three patterns byte for byte and is pinned as a literal in `fec/tests/members/test_interview_turn_tags.py`. **NEW ROWS ONLY**: the dial cannot repair history, because there is no raw transcript archive — the stored corpus is repaired once by `fec/members/migrate_interview_turn_bleed.py --apply`, which is a DATA change the owner gates separately (it re-attributes 64 turns, orphans the one contaminated in-use interview gold label, and re-runs through the media blend into ranks). Do NOT set `1` to undo a migration: `--restore` does that, byte-exact, from `speeches_turn_split_ledger` |
| `DESK_B5_FALLBACK` | `1` (on) | `fec/surfaces/make_member_desk.py:226` | `0` disables the Big5 estimate-layer fallback panels (2026-07-17 desert fill) |
| `DESK_OUT` | unset | `fec/surfaces/make_member_desk.py` (search `DESK_OUT`) | No-clobber redirect DIRECTORY for preview/test desk builds; unset = write the live tree |
| `COMBINED_STALE_OK` | `0` | `fec/surfaces/make_combined.py` (the new guard from item A) | `1` bypasses the stale-desk-HTML refusal — emergency use only |

---


### 1.9 Network configuration and sector dials (added 2026-08-19)

Five networks ship. `NET_CONFIG` selects which graph every engine on the page runs on, so it is the
highest-blast-radius dial in the system: it is fail-closed (an unknown value RAISES, never a silent
CU fallback) and it is read PER CALL so one process can serve several configs through the
config-keyed memo cache. The registry of accepted values is `moneyball_core.NETWORKS` — read it
there rather than trusting this table to stay current.

| Var | Default | Read at | Effect (one line) |
|---|---|---|---|
| `NET_CONFIG` | `cu` | `fec/moneyball_core.py` `_net_config()` | Selects the engine graph: `cu` \| `holistic` \| `holistic_norm` \| `bank_reg` \| `crypto`; validated against `NETWORKS`, unknown values RAISE (S) |
| `MEDIA_ADMIT` | `dominance` if holistic else `untied` | `fec/network/build_multilayer_network.py` | Media-edge admission fork: `untied` adds media only to untied pairs, `dominance` raises a tied pair to `max(cosponsor, media)` (P) |
| `NET_VALIDATE_ONLY` | unset | `fec/network/build_multilayer_network.py` | **Exercises the config guard and EXITS, writing nothing.** Exists because these producers BUILD ON IMPORT — see the trap below (E) |
| `SECTOR_PROMOTE` | unset | `fec/network/build_sector_diagnostic.py` | `1` writes an engine-loadable `sector_network_<sector>_*.xlsx` **to the live root**; otherwise an audit-only `sector_diagnostic_*` under `audits/` (O) |
| `SECTOR_ONLY` | `crypto,bank_reg` | `fec/network/build_sector_diagnostic.py` | Comma list restricting which sectors are built (S) |
| `HOLISTIC_CONGRESSES` | `117,118,119` | `fec/network/build_holistic_base.py` `dials()` | Congresses included in the all-bills base (S) |
| `HOLISTIC_TYPES` | all 8 bill types | `fec/network/build_holistic_base.py` `dials()` | Bill types included in the all-bills base (S) |
| `HOLISTIC_REGULAR_W` | `0.2` | `fec/network/build_holistic_base.py` | Regular-cosponsor role weight in the holistic base. **NOTE the CU base uses 0.5** — the two shipped families are on different role-weight scales by construction (P) |

**TRAP — `import == execution`, and the dial that exists because of it.** Every producer in
`fec/network/` builds when the module is imported. On 2026-08-19 importing
`build_multilayer_network` merely to check that it *refused* a sector config silently wrote
`holistic_network_AUG_20260819.xlsx` into the live root — content-identical to the reviewed
artifact, but newest-by-mtime selection had already made it the graph the engine would load. Use
`NET_VALIDATE_ONLY=1` to exercise the guard instead. **A guard you cannot exercise without side
effects is a guard nobody will exercise.**

**TRAP — filename families are load-bearing.** 24 lines across 17 files glob
`congress_cosponsor_network_*`, and three of them take `max(..., key=getmtime)` with NO `AUG` filter
and no family filter (`press_engagement_layer.py`, `press_hcoi.py`, `stance_dynamics.py`). One
misnamed artifact at the live root silently re-points the press, HCoI and stance layers. Sector and
holistic artifacts must fail that glob; `assert_output_name` enforces it and `audit_full`'s `[NET]`
section checks the families are disjoint on disk.


## 2. Workbook dials (user-owned — Paul edits these in Excel, code only READS them)

The workbook is `Moneyball Main Version - Blended.xlsx` at the data root. Since the 2026-07-02 "system of record inversion", Python owns all derived math and the workbook is a self-refreshing VIEW — but a few **typed literal cells** remain live inputs that Python reads as data. Changing them is Paul's decision, made in Excel, never silently in code (session-ratified, 2026-07; see `moneyball-change-control`).

| Dial | Where it lives | Where code reads it | Current value (as of 2026-07-09) |
|---|---|---|---|
| **AB pillar weights** (the blend of the 4 rank pillars: legislative / press / influence / demographic) | 'Blended Model' sheet, column 28 ("AB" in Excel letters), rows 2–5 | `fec/engine/compute_pillars.py:81` (`bm.cell(r,28)` for r in 2..5), applied at :88 as `score = AB2·leg + AB3·press + AB4·inf + AB5·dem` | **0.30 / 0.25 / 0.40 / 0.05** — verified live in `ranks_python.json` (`"ab_weights": {"2": 0.3, "3": 0.25, "4": 0.4, "5": 0.05}`); user-set 2026-07-07 |
| **Row-535 press tier weights** | 'Press Release - Normalized' sheet, row 535, columns 5–23 (one weight per press category) | `fec/moneyball_core.py:72` (`press_matrix()`); guarded by the audit | User-typed literals; survive openpyxl saves (typed cells always do) |
| **'Topic Weights' sheet** | Workbook sheet | **NOWHERE — reference-only/cosmetic.** The model uses hardcoded weights instead: `fec/stance/per_category_stance.py:26` returns (leg .55, press .70, vote .20) for the DEFENSIVE set {Interchange, Credit Card Mandates} else (.55, .35, .10). Confirmed by the comment at `fec/engine/apply_alloc_cap.py:54` ("Model uses hardcoded 0.70/0.35 … NOT this sheet") | Do not "fix" the model by editing this sheet — it changes nothing |
| **Category Stance edits** | Stance cells Paul edits in Excel ('Category Stance' named as a user-edit surface in `MATHEMATICAL_SPECIFICATION.md`, "User dial edits" paragraph) | Flow into `category_stance.json` via the chain; Rank & Allocation col G is a pure OUTPUT view (`per_category_stance.py:9–13`), never an input | Stance/press classification is Paul's domain — never relabel by model judgment (session-ratified, 2026-07; see `moneyball-change-control`) |

Trap: code comments can lag the workbook. Any "the weights are X" comment is untrustworthy — the ground truth for the live blend is the `ab_weights` block in `ranks_python.json` (written by `compute_pillars --write`).

---

## 3. Kernel constants worth knowing (code constants — NOT env dials)

These live in source and change only through change control. Listed so you don't mistake them for dials or re-derive them wrong.

**`fec/moneyball_core.py` (the kernel):**

| Constant | Where | Value / meaning |
|---|---|---|
| `PERS` persuadability map | :430–434 | Champion .10, Defender .12, Ally .40, Highly Persuadable .65, Persuadable .60, Lean Persuadable .55, True Neutral .50, Neutral .50, Lean Skeptic .40, Skeptic .25, Highly Skeptical .15, Opponent .08, `—` = `PERS_NONE` (env, .45). Highly Persuadable was .55 until the 2026-07-15 WIP snapshot e3d2923d0; no ratification is recorded (corrected 2026-09-30; verified against `fec/moneyball_core.py:430-434`) |
| `IMP` category importance | :141–144 | 18 categories, ABB26-handout-anchored; heaviest: Credit Card Mandates 3.0, CU Tax Status 3.0, Interchange 2.0 |
| `SGATE` seed gates | :151–153 | Per-stance seeding gate; floor 0.15 via `gate()` |
| `TORD` + `OVERALL_BANDS` + `overall_tier()` | :207–237 | IMP-weighted ten-rung overall ladder with bounded ±0.05 rounding: Champion ≥2.85; Highly Skeptical ≥`OVERALL_OPPONENT_CUTOFF` (default −1.60); below that is Opponent |
| `cpf_diffusion` | :120–122 | Cross-party diffusion factor `0.4+0.6·√(bpf_u·bpf_v)` (bpf = bipartisanship fraction) |
| `cpf_pressure` | :123–125 | Cross-party 0.5 / same-party 1.7 / else 1.0 — the kernel's TWO deliberate partisan physics |
| `build_P` cascade kernel | :421–428 | Edge activation `p = w·cpf·σ_v/(w·cpf·σ_v + 6.0)`; σ_v = receiver `edge_mult` |
| `delivery_mult` | :296–306 | Say-do talker discount on engine target value: `clip(1−0.15·max(0,gap−1), 0.70, 1.00)`; never touches rank |
| `GATEKEEP_JURIS` | :229–231 | Path-J say-do committees for {CU Tax Status, Interchange, Credit Card Mandates}; editing it is a stance-domain (Paul) decision |

**`fec/members/receptivity_layer.py` (per-member psych multipliers):**

| Constant | Where | Value |
|---|---|---|
| Susceptibility composite | :121 | `susc_trait = .40·coop + .30·N − .20·dil − .10·dom` (lexical mirror :124) |
| `susc_mult` | :133 | `clip(1+.18·susc, 0.70, 1.30)` |
| `edge_mult` | :134 | `clip(1+.12·susc, 0.80, 1.20)` |
| `incent_mult` | :136 | retiring → 0.60; else `clip(1+.30·(comp−0.5), 0.85, 1.15)` |
| Prospect-theory mult | :138 | loss domain 1.15 / gain 0.92 |
| **`pressure_mult` clip bounds** | :154 | `clip(susc_mult·incent·pt, 0.50, 1.60)` — **the [0.50, 1.60] engine clip** |
| `seed_prob` | :141–145 | `clip(0.60+.10·coop+.06·breadth+.04·visibility, 0.30, 0.90)` |

**Others:** `C_INT_W = 2.0` at `fec/members/big5_llm.py:344` — interview chunks count double for trait C (earned by the preregistered 2026-07-07 retest PASS; a CONSTANT, not env — do not try to set it from the environment). `THETA` flip thresholds `fec/engine/lt_priming.py:16`; the old `BETA=1.5` is gone, removed as dead by the 2026-07-08 audit fix N-1 (`fec/engine/lt_priming.py:33` "(BETA was dead.)"; corrected 2026-09-30). `RFLOOR=200000` `fec/engine/money_response.py:15` and the 10-rung `ORDER` ladder :38–39. Threshold engine `K=1.25`, rate clamp `.10–.40`, `MINN=8`, `PRIOR=0.70` at `fec/stance/per_category_stance.py:36–38`. `PIN={'MEM':456,'MEM_A':290}` (`fec/members/b5_a_matrix.py:26`) and `PIN={'MEM':456,'MEM_N':201,...}` (`fec/members/b5_n_matrix.py:28`) look like gates but are **pinned prereg roster constants** — a non-simulate run aborts on roster drift; never "update" them outside the prereg protocol (`moneyball-research-methodology`).

**JS mirror status (as of 2026-07-09):** the dashboard template `fec/surfaces/templates/make_dashboard_html_00.tpl` mirrors kernel math in JavaScript, including `edge_mult` (tpl:330), `pressure_mult` + `delivery_mult` (tpl:340,344 — "psych parity 2026-07-09"), and the Bakker `xf()` signing (~tpl:357). Any change to these Python formulas must be re-ported by regenerating AND editing the template; JS reads no env vars.

---

## 4. Add-a-dial checklist

Use this when a change needs an escape hatch or an experiment needs a knob. A dial is the project's standard mechanism for "shipped but revertible".

1. **Name it** SCREAMING_SNAKE, short, prefixed by subsystem where one exists (`SOC_`, `SAL_`, `B5_`, `BIG5_`, `RECEPT_`, `SD_`, `HCOI_`, `REF_`, `AC_`). Avoid names one typo away from an existing dial (the HALF/HALFF pair is the cautionary tale — don't mint a third).
2. **Default = current behavior, exactly.** `os.environ.get('NAME','<current>')` where an empty environment is byte-identical to production. Never ship a dial whose default changes output.
3. **Read it once, at top level,** next to the other dials of that file, with an inline comment stating: what it does, the ratification date/status, and what the non-default value reverts or enables. The inline comment is the primary documentation — every existing dial carries one.
4. **Document it** in `MATHEMATICAL_SPECIFICATION.md` → the "## Standing dials (env; defaults = the ratified state)" section, in the same `NAME=default (one-line note)` format. That list is the spec-of-record for dials.
5. **Class it honestly**: if it guards an unratified alternative (like `BP_SRC=aug`), say "available but unratified" in the comment; unproven things stay labeled open/candidate/gated.
6. **Verification implications** (`moneyball-validation-and-qa` owns the standards): with the default set, run the standard protocol — `python fec\tests\run_tests.py`, then the chain, then **zero rank delta** vs the last `ranks_*.json` baseline, then `python fec\audit\audit_full.py` all-clean. If the dial redirects output, teach the audit the no-clobber pattern (`FRONTIER_OUT`/`OPT_OUT` precedent at `audit_full.py:176,212`; corrected 2026-09-30). If it gates spend, follow the `spend_guard` fail-CLOSED pattern (`collector_supervisor.py:126–141`).
7. **JS-mirror implications**: if the dial touches engine math that the dashboard re-implements (priming, cascade, money curve, receptivity multipliers), the JS port in `fec/surfaces/templates/make_dashboard_html_00.tpl` must stay in lockstep — either the dial's effect is baked into the regenerated artifacts the JS reads, or the JS needs the same branch. `BAKKER_XCUE` is the worked example (lt_priming.py:36–37 comment).
8. **Cost dials**: anything that can spend money must dry-run-print `est ~$X` and exit without `--go` (the `big5_llm.py:253–256` pattern) so `spend_guard` can parse it.
9. **Ownership**: if the value encodes a judgment call (weights, thresholds, category membership), it is Paul's dial — ship the mechanism with the ratified default and flag the decision, don't tune it yourself (`moneyball-change-control`).

---

## 5. Known traps (all verified 2026-07-09)

- **Setting a dial did nothing** → you set it after import, or in a different process, or you edited `os.environ` in a session where the module was already loaded. Fresh process, variable first.
- **PowerShell syntax**: `$env:NAME = 'value'` then run python in the same command; there is no bash-style `NAME=x python ...` inline prefix.
- **`B5_COMPOSITE` / `CMTE_ROSTER` defaults are dead paths** (hard-coded scratchpads of deleted worktree sessions). Set explicitly.
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
cd "C:\Users\pgoff\OneDrive\Desktop\Melange Systems"   # or any worktree of this repo (read-only commands only)
```

| Volatile fact | Re-verification one-liner (PowerShell) |
|---|---|
| Complete env-dial inventory (any new/removed dial) | `Get-ChildItem fec -Recurse -Filter *.py \| Where-Object FullName -notmatch "_quarantine|__pycache__" \| Select-String -Pattern "os\.environ|from os import environ"` (RECURSIVE. The old non-recursive form matched 14 of 638 files after the 2026-08 reorg and silently reported a 13-dial world; the attic is now excluded BY NAME, which is what that rationale actually wanted) |
| Any single dial's default + comment | `Select-String -Path fec\<consumer>.py -Pattern "DIALNAME"` (e.g. `Select-String -Path fec\engine\money_response.py -Pattern "DTHRESH"`) |
| HALF vs HALFF still distinct, both 0.10 | `Get-ChildItem fec -Recurse -Filter *.py \| Where-Object FullName -notmatch "_quarantine|__pycache__" \| Select-String -Pattern "'HALFF?'"` and the spec: `Select-String -Path MATHEMATICAL_SPECIFICATION.md -Pattern "HALFF"` |
| Live pillar weights -- 45/10/40/5 since 2026-09-03, cross-check `fec/engine/pillar_policy.py:11-15`; 30/25/40/5 was the 2026-07-07 GATE-2 ratification and the change was out-of-lane and is not re-ratified (open ruling S-5), so trust the command below, not either literal | `[regex]::Match((Get-Content "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\ranks_python.json" -Raw), '"ab_weights"[^}]*}').Value` |
| AB-weight cell read (col 28, rows 2–5) | `Select-String -Path fec\engine\compute_pillars.py -SimpleMatch "cell(r,28)"` |
| Row-535 press weights read | `Select-String -Path fec\moneyball_core.py -SimpleMatch "cell(535"` |
| Topic Weights sheet still cosmetic | `Get-ChildItem fec -Recurse -Filter *.py \| Select-String -Pattern "Topic Weights"` (expect only the apply_alloc_cap cosmetic note) |
| Receptivity clip bounds (.70–1.30 / .50–1.60 / .30–.90) | `Select-String -Path fec\members\receptivity_layer.py -SimpleMatch "clip("` |
| PERS map + PERS_NONE | `Select-String -Path fec\moneyball_core.py -Pattern "PERS_NONE","PERS="` |
| MC/SEED/TOPIC per-script defaults | `Get-ChildItem fec -Recurse -Filter *.py \| Where-Object FullName -notmatch "_quarantine|__pycache__" \| Select-String -Pattern "get\('MC'","get\('SEED'","get\('TOPIC'"` |
| Spend caps + fail-CLOSED guard | `Select-String -Path fec\collector_supervisor.py -Pattern "B5_GATE_CAP","REF_GATE_CAP","failing CLOSED"` |
| JS psych parity still present | `Select-String -Path fec\surfaces\templates\make_dashboard_html_00.tpl -Pattern "psych parity","pressure_mult","xf"` |
| Spec dial list still current | `Select-String -Path MATHEMATICAL_SPECIFICATION.md -Pattern "Standing dials" -Context 0,6` |
| C_INT_W still a constant (not env) | `Select-String -Path fec\members\big5_llm.py -Pattern "C_INT_W"` |
| Vote Smart key still file-based; live route status | `Select-String -Path fec\members\votesmart_npat_fetch.py -Pattern "votesmart_api_key"` — and for STATUS use `git log --all --oneline \| Select-String "Vote Smart"` (per `moneyball-docs-and-claims` §3.2), NOT a key-file existence probe (§1.6) |
| Prereg roster pins | `Select-String -Path fec\members\b5_a_matrix.py, fec\members\b5_n_matrix.py -SimpleMatch "PIN = {"` |
