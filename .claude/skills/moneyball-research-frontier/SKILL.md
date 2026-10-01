---
name: moneyball-research-frontier
description: Load when asked "what should this project research next", "is there a publishable result here", "when do the gated rounds unlock (MEM_N >= 250, the 5-seed diagnostic)", "how do we validate the influence model against real outcomes", "how do we beat the 0.872 stance-compose ceiling", or "what's the next cross-modal (audio) experiment". It catalogs the five open frontier problems — behavioral-criterion LLM psychometrics, prospective outcome validation, signed-multiplex influence maximization, the stance-valence bottleneck, and cross-modal personality measurement — each with why published methods fail, this repo's asset, first file-level steps, and falsifiable milestones. It does NOT cover prereg/look mechanics (moneyball-research-methodology), analysis recipes like power studies (moneyball-proof-and-analysis-toolkit), day-to-day operations (moneyball-run-and-operate), or the 120th-Congress rollover (moneyball-congress-rollover-campaign). Everything on this page is CANDIDATE/OPEN work, not validated results.
---

# Moneyball research frontier

This skill is the project's forward-looking research agenda: the five open problems where this repo's unusual assets (a 533-member behavioral dataset, a prereg-disciplined measurement program, and a live influence-targeting campaign) could produce results that advance the state of the art. "State of the art" here has a fixed, user-set definition (Paul, 2026-07-09): **BOTH tracks must be carried** — (a) *methods rigor*: preregistered LLM-psychometrics and influence-modeling that would survive peer review, and (b) *real-world capability*: measurably better persuasion targeting. Each problem below carries a separate milestone for each track. **Nothing on this page is a validated result.** Every item is labeled candidate, open, or gated; several are blocked behind data thresholds or Paul's explicit decisions, and this page never authorizes skipping a gate.

## When NOT to use this skill

- **Executing an experiment** (writing/locking a prereg, running a look, the battery discipline) → `moneyball-research-methodology`. That skill owns the scientific method; this one only names targets.
- **Statistical machinery** (power study, planted-signal battery, split-half reliability, permutation gates, CRN proofs) → `moneyball-proof-and-analysis-toolkit`.
- **Whether a change is allowed at all**, gating vocabulary, user-domain boundaries → `moneyball-change-control`.
- **What has already been tried and killed** (the kill-ledger, refuted findings, do-not-reflag lists) → `moneyball-failure-archaeology`. Do not re-derive dead ends from here.
- **Theory background** (what a cascade or a Big-Five trait even is, in depth) → `influence-modeling-reference` and `psychometrics-reference`.
- **What may be claimed publicly** about any of this → `moneyball-docs-and-claims`.
- **The 120th-Congress rollover** → `moneyball-congress-rollover-campaign` (an executable campaign, not a research problem).

## Quick reference — the five problems (all CANDIDATE/OPEN as of 2026-07-09)

| # | Problem | Status as of 2026-07-09 | What unblocks it | Key files |
|---|---------|------------------------|------------------|-----------|
| 1 | Behavioral-criterion LLM psychometrics at n≈500 public figures | Two routes gated: N-route **DATA-GATED** (needs MEM_N ≥ 250; currently 201), A-route **DIAGNOSTIC-GATED** (needs 5-seed synthetic check ≥3/5) | Interview-corpus growth; bills-archive growth | `big5_methods.md` §20–21, `big5_n_matrix_prereg.md`, `big5_a_matrix_prereg.md`, `fec/members/b5_n_matrix.py`, `fec/members/b5_a_matrix.py` |
| 2 | Prospective outcome validation of the influence model | Harness BUILT and **armed once**: `outcome_snapshot_2026-07-04.json` frozen 2026-07-04, scoreable from ~2026-09-02 if the ≥150-mover floor is met (verified on the live tree 2026-07-10; operational state owned by `moneyball-diagnostics-and-tooling`) | Scoring the existing snapshot at its horizon; additional freezes after receptivity-formula changes | `fec/engine/outcome_snapshot.py`, `fec/members/receptivity_sensitivity.py` |
| 3 | Signed-multiplex influence maximization with psychological susceptibility | All components live in the engine; NO external validation of the combination vs an unsigned ablation | Writing the ablation benchmark + a prereg | `fec/moneyball_core.py` (build_P), `fec/engine/lt_priming.py` (Bakker signing), `fec/network/build_multilayer_network.py`, `fec/engine/kb_benchmark.py` (the pattern) |
| 4 | Stance→valence decomposition bottleneck | Stance-hop 0.915 solved; valence-hop 0.689 is the bottleneck; compose ceiling 0.872 | Paul's registry curation (his domain) + a focused valence model | `fec/stance/apply_two_hop_stance.py`, `fec/stance/derive_valence_registry.py`, `fec/stance/stance_eval.py` |
| 5 | Cross-modal personality (text / audio / votes) | Audio validly measures E + ES only (vs the LLM instrument); voice-C has ONE pre-declared untried route (MFCC); asset grew N=90 → 395 verified voiceprints | Building the MFCC block + a locked prereg | `fec/members/b5_audio_build.py`, `big5_audio_round2_prereg.md`, `big5_audio_faithful_prereg.md` |

## Standing rules that bind ALL frontier work

These are project law. The master list with rationale lives in `moneyball-change-control`; the ones that repeatedly matter here:

1. **One-look discipline.** Every validity test is preregistered (a locked file stating hypothesis, numeric bars, and consequences BEFORE seeing data) and evaluated exactly once. A "look" consumed on noise is gone forever. See `moneyball-research-methodology` before touching any of this. (Repo-documented in every `big5_*_prereg.md`.)
2. **Gates are not suggestions.** DATA-GATED = blocked until a pinned data threshold; DIAGNOSTIC-GATED = blocked until a pinned synthetic check passes; user-gated = Paul decides. Rounds 4 and 5 were retired WITHOUT a look *on purpose* — "helpfully" retrying them burns the discipline (`big5_n_matrix_prereg.md:266-276`, `big5_a_matrix_prereg.md:196-205`).
3. **Never re-propose human raters / the expert panel.** Built, then canceled by Paul; the psych-framework grade A− is FINAL. (Session-ratified, 2026-07; the panel scorer `fec/members/b5_panel_score.py` refuses the look while its prereg is unlocked.)
4. **LLM cost rule (HARD):** Fable/Opus ONLY for the 533 per-member narratives; every other LLM step (verification, classification, extraction — including anything new you build for these problems) uses Haiku 4.5. (Session-ratified, 2026-07; stated in code at `fec/members/b5_narratives.py:10-11`, `fec/members/b5_audio_verify.py:10`.)
5. **Stance/press classification is Paul's domain.** Problem 4 in particular: you build curation tooling and override mechanisms; you NEVER relabel by model judgment. (Session-ratified, 2026-07; the shipped mechanism is `fec/stance/apply_press_overrides.py`.)
6. **The RL (reinforcement-learning) envelope is Paul's roadmap — do not build it uninvited.** (Session-ratified, 2026-07.) The influence-maximization problem below is deliberately scoped to NOT include RL.
7. **Import == execution.** Nearly every `fec/*.py` writes artifacts under ROOT at import time. `fec/paths.py:7-8` sets ROOT to `MONEYBALL_ROOT` when set, else to the parent of the imported paths.py, so a script run from a git worktree targets that worktree's EMPTY data plane; with `MONEYBALL_ROOT` pointed at LIVE, writes DO land in LIVE. `fec/tests/run_tests.py` resolves its own root from `__file__` and ignores `MONEYBALL_ROOT`. See `moneyball-change-control` law 7 (corrected 2026-09-30; verified against `fec/paths.py:7-8`). Only `fec/tests/run_tests.py` and `fec/audit/audit_full.py` are read-only-safe to run casually. Check for Paul's live jobs before running anything. (Session-ratified, 2026-07.)
8. **Claim discipline.** Never "5/5 traits validated" (the real instrument look was 3/5: O/C/E); "A passed via audio" is FALSE (audio-A was null twice; audio's real pass is E + ES); ES always carries the gender-confound caveat. Verify wording against `big5_methods.md` before writing anything down. See `moneyball-docs-and-claims`.

---

## Problem 1 — Behavioral-criterion LLM psychometrics at n≈500 public figures

**Status: OPEN — one route still gated, one consumed. Update (2026-07-10, merged to main):** the A-route's 5-seed diagnostic was MET by a NEW instrument (st_mean semantic embeddings, synthetic-only), a fresh prereg (round 6) was locked and its look CONSUMED: **MISS on all 5 bars — the st_mean A route is CLOSED** (@b7573c9). Still open: the N-route data gate (MEM_N ≥ 250) and round-5's Empath data-growth clause. Any future instrument basis is bound by round 6's anti-basis-shopping clause (own diagnostic + fresh-seed confirmation + full screening ledger + adversarial prereg).

**Plain-language framing.** The Big Five are the standard five personality dimensions in psychology: Openness, Conscientiousness, Extraversion, Agreeableness, Emotional Stability (O/C/E/A/ES). Published attempts to measure politicians' personalities use either self-report questionnaires (politicians won't fill them out honestly, if at all) or "lexical" methods — word-count statistics over their speech — validated against *other text-derived scores*, which is circular. "Halo" is the failure mode where one warm, polished speaking style inflates several traits at once. A *behavioral criterion* breaks the circle: validate the text measurement against what the person verifiably *does* (votes, cosponsorships, hearing attendance), not what they say.

**Why current SOTA fails.** The field's congressional benchmark (Ramey/Klingler/Hollibaugh, "RKH") is itself text-derived, so text-vs-RKH agreement is shared-method variance, not validation. Self-report is unavailable for elites at scale. Nobody has published per-trait *behavioral* criterion validity with discriminant evidence (each trait predicting its OWN behavior better than other traits do — "diagonal dominance") at n≈500 public figures.

**This repo's asset.**
- Six behavioral criteria measured directly from congressional records: cooperation, diligence, dominance, visibility, breadth (`fec/members/behavioral_dispositions.py:3-24`), plus reactivity (live-interview cutoff proneness, the N-role; same file, lines 92-109).
- A hardened prereg discipline: locked bars, a synthetic "battery" (planted signal / null / confound-only / true+confound checks) that refuses a look the sample can't support, SHA-256 input pinning, adversarial re-derivation of every pass. Rounds 4 and 5 (2026-07-09) proved the discipline works by *refusing* looks: see `big5_methods.md` §20-21.
- A multi-modal corpus: 6.6M words of floor speech, hearings, press, and interviews as of 2026-07-02 (`README.md:27`; `PERSONALITY_RECEPTIVITY_LAYER_2026-07-02.md:6`) — grown since via weekly interview collection.
- A quantified power map: a true correlation of r=.40 is recoverable reliably only from n≈250 in this feature space (round-4 power study, `big5_n_matrix_prereg.md:258-264`); the finance-active A-stratum is genuinely signal-poor at n=290 (`big5_a_matrix_prereg.md:185-194`). This "when is a masked look even possible" result is itself novel methods content.

**The gates (verbatim conditions — do not soften them).**
- **N-route (text→reactivity), DATA-GATED:** a successor prereg may be locked only when reactivity coverage within the eligible roster reaches **MEM_N ≥ 250** (currently 201/456). Coverage = members with ≥30 attributed live-interview turns; grows with interview collection. (`big5_n_matrix_prereg.md:269-273`.)
- **A-route (text→cooperation_v2), DIAGNOSTIC-GATED:** a successor prereg may be locked only when the pinned 5-seed synthetic diagnostic (the battery's constructor, seeds 424242/515151/616161/717171/818181, run on the then-current MEM_A stratum) passes **≥3/5 on bars 1-4**. Synthetic-only — checking it never risks a look. (`big5_a_matrix_prereg.md:197-202`.) Note: only seed 424242 is wired into `fec/members/b5_a_matrix.py:89`; the 5-seed sweep has no shipped one-command runner and must be reconstructed from `simulate_battery` (`fec/members/b5_a_matrix.py:81`) with the pinned seeds.

**First three steps (in this repo).**
1. **Measure the gates, read-only.** From the repo root (quote it — it contains spaces):
   ```powershell
   cd "C:\Users\pgoff\OneDrive\Desktop\Melange Systems"
   python -c "import json; print(json.load(open('behavioral_dispositions.json'))['coverage'])"
   ```
   This prints per-disposition coverage counts (the artifact's own `coverage` block, written at `fec/members/behavioral_dispositions.py:136-138`). MEM_N is the reactivity count *intersected with the §17-eligible roster of 456*, so the raw number is an upper bound — the exact stratum definition is in `big5_n_matrix_prereg.md`.
2. **Reconstruct the 5-seed A-diagnostic** as a standalone read-only script (new file, e.g. `fec/a_stratum_diagnostic.py`, guarded `__main__`, no artifact writes) that imports the constructor logic from `fec/members/b5_a_matrix.py:81-129` and runs the five pinned seeds on the current MEM_A stratum. **Already done**: `fec/members/b5_a_stratum_diag.py` (@4d11a5b, merged to main) — it exists in the tree; extend it rather than rebuilding. Caution: `b5_a_matrix.py` loads live artifacts at import — coordinate per `moneyball-change-control` before running anything that touches the live tree.
3. **Draft (do not lock) the flagged confirmatory text-C look.** The audio round-2 RESULT flagged an exploratory finding for confirmation: Empath text → behavioral diligence r=+0.348, perm-p=.003, party-controlled — with the confirmatory step already named: "full roster (500+), held-out split, seniority + party controls, pre-registered" (`big5_audio_round2_prereg.md:45-52`). This is the one near-term look NOT blocked by either gate. Drafting means writing the prereg skeleton per `moneyball-research-methodology`; locking and looking follow that skill's protocol.

**You have a result when...**
- *Methods track:* a successor prereg look (five-bar masked-matrix structure, battery-gated, fresh fingerprints) PASSES for a sub-E-class trait (N or A) at the gated sample size, survives adversarial re-derivation, and its RESULT is recorded verbatim — the first behavioral-criterion, discriminant-valid text measurement of that trait class at n≥250 public figures. A recorded MISS is also a (lesser) publishable methods result; an un-prereg'd positive is NOT a result.
- *Capability track:* the newly validated trait upgrades an engine slot (e.g. text-N corroborating `reactivity_z`) **via a separate user-gated ratified step** — engine promotion is never automatic on a pass (precedent: `big5_methods.md:532-535`).

**Do NOT:** re-run the retired round-4/5 preregs (single-vintage by design — they refuse on fingerprint drift); re-take the round-6 look (consumed, MISS stands, @b7573c9); re-propose CT-CM latent modeling (four misses, "DO NOT re-run", `big5_methods.md` §15); re-propose human raters; re-decide or quietly revert the coop_v2 engine promotion (granted+shipped 2026-07-10 @94f09cf — `RECEPT_COOP=v1` is the engineering revert, and flipping it is a user decision under change control).

**Siblings to load:** `moneyball-research-methodology` (the prereg/look protocol), `psychometrics-reference` (criterion validity, halo, power), `moneyball-proof-and-analysis-toolkit` (plant battery, power study recipes), `moneyball-change-control`.

---

## Problem 2 — Prospective outcome validation of influence models

**Status: OPEN — harness BUILT and armed once: `outcome_snapshot_2026-07-04.json` was frozen 2026-07-04 (the behavioral-basis ship day) and sits at `data\engine\outcome_snapshot_2026-07-04.json` in the live tree (corrected 2026-09-30; verified by listing LIVE `data\engine\`); scoreable from ~2026-09-02 if the ≥150-mover floor is met. `moneyball-diagnostics-and-tooling` owns the harness's operational state.**

**Plain-language framing.** The engines predict which members of Congress are persuadable and how money/network pressure moves them. Every constant in that machinery (e.g. the 0.18 susceptibility scaling, the 0.60 retiring-member factor) is a literature-shaped *design choice* — no real-world outcome has ever tested the magnitudes. "Prospective" validation means freezing today's predictions, waiting, and scoring them against what actually happened — the only test that can't be overfit, because the answers don't exist yet at prediction time.

**Why current SOTA fails.** Published influence-maximization and lobbying models validate *retrospectively*: fit to historical data, report fit quality. Retrospective fit cannot distinguish a causal model from a correlate. Political-influence field experiments exist (e.g. contact experiments) but not for network-model-driven targeting of legislators with pre-declared bars.

**This repo's asset.** `fec/engine/outcome_snapshot.py` — a complete, pre-registered prospective harness, already armed once (the 2026-07-04 freeze; docstring: "freeze today's receptivity predictions, score them against the future... the A-grade path for the receptivity magnitudes"). Verified contents as of 2026-07-09:
- **H1** (seeding): frozen `seed_prob` correlates positively with NEW cosponsorships adopted after the freeze. **H2** (pressure): frozen `pressure_mult` correlates positively with |overall-tier movement| (lines 8-13).
- **Bars locked in the file:** Spearman rho ≥ +.20 PASS · +.10–.20 DIRECTIONAL · below +.10 NULL ("magnitudes stay design choices") · ≤ −.10 INDICTED (lines 14-15, 88-89).
- **Refusal rule:** the scorer refuses unless ≥60 days elapsed AND ≥150 members show a cosponsorship delta (lines 16-17, 82-83) — an underpowered look cannot be taken by accident.
- Companion: `fec/members/receptivity_sensitivity.py` already *bounded* the untested constants (decision-robustness sweep, its docstring lines 3-17) — the honest interim result; the outcome test is its named successor.
- A live campaign to score against: the stance matrix, tiers, and cosponsorship panel refresh weekly, so "what actually happened" accrues automatically.

**First three steps (in this repo).**
1. Read `fec/engine/outcome_snapshot.py` end-to-end (95 lines) and confirm the bars/hypotheses above still match. Then locate and read the EXISTING snapshot — `data\engine\outcome_snapshot_2026-07-04.json` in the live tree (corrected 2026-09-30) — and calendar its scoring date (~2026-09-02, i.e. ≥60 days after the freeze).
2. **Score the existing snapshot at its horizon** (`python fec/engine/outcome_snapshot.py --score "<live-root>\data\engine\outcome_snapshot_2026-07-04.json"`, read-only; the scorer refuses if <60 days or <150 movers), **and/or propose an ADDITIONAL freeze to Paul, then run it** — multiple freezes are the documented practice, and a NEW freeze is needed after any change to the receptivity formulas (the old snapshot still scores the old formula; per `moneyball-diagnostics-and-tooling`). A freeze writes one new dated artifact to the live tree, `data\engine\outcome_snapshot_<date>.json` (`fec/engine/outcome_snapshot.py:64`; corrected 2026-09-30) — additive, but still a live-tree write; check for his live jobs first per rule 7:
   ```powershell
   cd "C:\Users\pgoff\OneDrive\Desktop\Melange Systems"
   python fec/engine/outcome_snapshot.py --freeze
   ```
   It prints the exact `--score` command to run later, with the snapshot filename embedded (lines 60-68).
3. Prepare the H2 engaged-only variant: the file anticipates filtering to members Paul's "In-contact" log marks as actually engaged (lines 12-13, 92). Ask Paul whether that export exists; if so, extend the scorer's engaged-only branch BEFORE the horizon date (changing the scorer after outcomes are knowable is bar-moving — see `moneyball-research-methodology`).

**You have a result when...**
- *Methods track:* a frozen snapshot is scored at the pre-declared horizon with the ≥60-day/≥150-mover minimum met, and the H1/H2 verdicts (PASS / DIRECTIONAL / NULL / INDICTED) are recorded regardless of direction. That artifact — frozen predictions, immutable bars, real congressional outcomes — is the peer-review-grade object. An INDICTED verdict is a *result* (the dials go back to Paul for a re-look, per the file's own wording), not a failure to hide.
- *Capability track:* H1 or H2 at PASS (rho ≥ +.20) upgrades the receptivity magnitudes from "design choices, sensitivity-bounded" to "outcome-validated" — which is the difference between plausible targeting and demonstrated targeting. Repeat freezes each quarter turn one result into a track record.

**Do NOT:** score early, lower the movers threshold, or re-freeze after peeking at partial outcomes (each is bar-moving); change engine dials mid-window (it contaminates the frozen predictions' meaning — coordinate any dial change with the open snapshot in mind).

**Siblings to load:** `moneyball-research-methodology`, `moneyball-run-and-operate` (safe execution, live-job checks), `moneyball-change-control` (dial changes are user-ratified), `influence-modeling-reference`.

---

## Problem 3 — Signed-multiplex influence maximization with psychological susceptibility

**Status: OPEN — every component is live in the engine; the COMBINATION has no external validation against an unsigned ablation.**

**Plain-language framing.** "Influence maximization" (IM) = pick the k people whose activation spreads furthest through a network. Academic IM almost universally assumes an *unsigned* (all ties positive), *single-layer* (one edge type) graph with *uniform* node psychology. This repo's cascade runs on none of those assumptions: a *multiplex* network (multiple edge types: cosponsorship, press engagement, interest similarity, social interaction — `fec/network/build_multilayer_network.py:9-20`), with *signed* persuasion physics (cross-party cues from non-bridge-builders are clamped toward zero per Bakker et al.: out-party cues don't persuade — `fec/engine/lt_priming.py:31-39`, dial `BAKKER_XCUE=0` reverts), and *per-node psychological susceptibility* (each member's receiver probability is scaled by `edge_mult` from the receptivity layer — `fec/moneyball_core.py:421-428`). An "ablation" = the same system with one component switched off, to measure that component's contribution.

**Why current SOTA fails.** IM benchmarks (greedy/CELF on IC/LT models) optimize spread on synthetic or social-media graphs and validate on simulated spread — the model grades its own homework. Signed IM and multiplex IM exist as separate literatures; psychologically heterogeneous receivers barely exist in either; and *external* validation (does the enriched model predict real-world adoption better?) is essentially absent.

**This repo's asset.**
- The full stack already runs in production: Fink-normalized empirical influence probabilities as an edge layer (engagement events ÷ author volume, `fec/network/build_multilayer_network.py:11-14`), receptivity multipliers in the kernel, Bakker signing in the priming engine, greedy allocators — `fec/engine/optimize.py` (exact on its `INC` grid only in a fixed stance state; no guarantee claimed once a modeled conversion can change stances, `fec/engine/optimize.py:3-11,36-38`; full scope in `influence-modeling-reference` Section 6) and `fec/engine/budget_frontier.py` (greedy coalition seeding; it states no guarantee of its own) (corrected 2026-09-30; verified against `fec/engine/optimize.py:3-11`).
- **A shipped template for external benchmarking:** `fec/engine/kb_benchmark.py` computes Katz-Bonacich centrality (a network-position score from the economics-of-lobbying literature, Battaglini & Patacchini) on the live kernel and correlates it against *observed real money flows*. Its recorded run-4k findings: industry money tracks KB centrality (+0.24) more than credit-union money does (+0.14); the allocator anti-correlates (−0.21) *by design* (`AUDIT_FINDINGS_2026-07-04.md:682-690`). That is the pattern to copy: model quantity vs external reality, with the "expected" direction argued in advance.
- Clean ablation switches already exist as env dials: `RECEPT_LAYER=0` (psychology off, `fec/moneyball_core.py:48`), `BAKKER_XCUE=0` (signing off), and the multiplex reverts by deleting the AUG network file / pointing at the newest non-AUG file (`fec/network/build_multilayer_network.py:5-7`). Common-random-numbers determinism (`sm64`, `fec/moneyball_core.py:126-131`) means full-vs-ablated deltas are real effects, not simulation noise.

**First three steps (in this repo).**
1. Write the ablation benchmark as a new read-only diagnostic, `fec/engine/im_ablation_benchmark.py`, modeled line-for-line on `fec/engine/kb_benchmark.py` (guarded `__main__`, writes one tagged JSON, chain consumes nothing): compute the frontier/optimizer top-k target sets and per-member predicted-influence scores under (a) full kernel, (b) `RECEPT_LAYER=0`, (c) `BAKKER_XCUE=0`, (d) base non-AUG network, using `FRONTIER_OUT`/`OPT_OUT` temp redirects so production artifacts are never clobbered (redirect pattern: `fec/engine/budget_frontier.py:152-153` (corrected 2026-09-30), and `fec/engine/mc_stability_check.py` shows the subprocess-with-temp-files idiom).
2. Pick and pin the external criterion BEFORE computing anything: the honest candidates are (i) prospective new-cosponsorship adoption (piggyback on Problem 2's frozen snapshot — same outcome data, different predictor), and (ii) observed money flows à la kb_benchmark (retrospective, weaker, but immediate). Write the choice, the comparison statistic, and the bars into a prereg per `moneyball-research-methodology`.
3. Only then run the benchmark and record full-vs-each-ablation deltas under the locked bars. Define first which engine's predictions you are ablating, or the ablation is ill-posed: receptivity enters engines differently — every `build_P` consumer (including `lt_priming.py`, `scenario.py` and `cosponsor_route.py` since the 2026-07-08 audit fix N-1) gets `edge_mult` on its edges, while flip/money paths get `pressure_mult` (`fec/engine/lt_priming.py:34`, `fec/moneyball_core.py:421-428`; see `moneyball-architecture-contract`; corrected 2026-09-30).

**You have a result when...**
- *Methods track:* under a locked prereg, the full signed-multiplex-psychological kernel beats the unsigned/single-layer/uniform ablation on the pinned external criterion (e.g. higher Spearman rho against real post-freeze cosponsorship adoption, bar pre-declared) — external, not simulated, validation of the enrichments. A recorded null ("the enrichments don't improve external prediction") is also a result and would be genuinely informative.
- *Capability track:* the winning kernel's top-k target list demonstrably differs from the ablated list AND the members unique to the winning list out-adopt the members unique to the ablated list over the horizon window — i.e. the psychology and signing bought better *targets*, not just a better statistic.

**Do NOT:** validate on simulated cascades from the same kernel (circular); build the RL envelope (rule 6); clobber production artifacts — always redirect outputs (`FRONTIER_OUT`, `OPT_OUT`); run concurrent baselines while Paul has live jobs (rule 7).

**Siblings to load:** `influence-modeling-reference` (cascades, submodularity, Bakker, Fink), `moneyball-research-methodology`, `moneyball-diagnostics-and-tooling` (kb_benchmark, mc_stability_check interpretation), `moneyball-config-and-flags` (the ablation dials).

---

## Problem 4 — The stance→valence decomposition bottleneck

**Status: OPEN — the decomposition is proven; the weak hop is identified; the fix path runs through Paul's domain.**

**Plain-language framing.** To know whether a tweet/press release is good or bad for credit unions ("CU alignment"), the system composes two judgments: the **stance hop** — WHO does this text target, and is the author for or against them? — and the **valence hop** — is that target itself good or bad for credit unions? Measured on 400 user-adjudicated gold-label tweets: the model's stance hop is right 91.5% of the time; its valence hop only 68.9% — and composing model-stance with a *human-curated* valence registry tops out at 87.2% (`fec/stance/apply_two_hop_stance.py:3-5`; the derivation harness prints the same ladder: "flat baseline 0.677 | trained classical 0.737 | oracle ceiling 0.872", `fec/stance/derive_valence_registry.py:151`). The bottleneck is world knowledge (is the CFPB's expansion good for CUs?), not language understanding.

**Why current SOTA fails.** Stance-detection benchmarks score stance-toward-target and stop; "target-aware sentiment" research rarely composes through an explicit, auditable valence knowledge layer. End-to-end LLM classification entangles the two hops, so errors can't be attributed, and domain valence judgments get hallucinated instead of adjudicated. The compose architecture here — model handles language, a human-owned registry handles domain valence, with `policy_force` entries that BIND the final label (`fec/stance/derive_valence_registry.py`, consumed at `fec/stance/tweet_stance_stack.py` / `fec/stance/press_stance_stack.py`) — is the unusual part.

**This repo's asset.** The user-adjudicated gold machinery (queues, adjudication sheets, `fec/stance/stance_eval.py` macro-F1 harness scoring any prediction column against gold), the tracked-in-git valence registry `cu_valence_registry.json` (the ONLY tracked JSON — the user's committed judgments), a free error-attribution tool (`fec/stance/apply_two_hop_stance.py --uncovered` ranks high-volume targets the registry misses, no API calls, `fec/stance/apply_two_hop_stance.py:9-11,39-45`), and a quantified ceiling that makes progress falsifiable.

**First three steps (in this repo).**
1. Run the free coverage probe and hand Paul the curation list (valence judgments are HIS — rule 5):
   ```powershell
   cd "C:\Users\pgoff\OneDrive\Desktop\Melange Systems"
   python fec/stance/apply_two_hop_stance.py --uncovered
   ```
   (Reads gold + registry, prints the top-20 uncovered targets; writes nothing. It does read live-tree files at import — coordinate per rule 7.)
2. After Paul rules on new families, re-derive and re-measure: `python fec/stance/derive_valence_registry.py` (free 5-fold cross-validation report, writes nothing) and only with his sign-off `--write` (it rewrites the tracked registry — `fec/stance/derive_valence_registry.py:172-200`). The registry `_doc` already flags "Re-eval before production" for the policy_force families pending a fresh gold sample on the new CFPB axis — that fresh gold batch (Paul labels; you build the queue via the `fec/stance/build_gold_queue.py` / `fec/stance/build_tweet_gold_queue.py` family) is the honest held-out set for any ceiling claim.
3. If registry curation plateaus below the ceiling, attack the stance hop's remaining 8.5% and/or build a focused valence-hop classifier as a *registry-fallback* (never a registry-override): training scaffolding exists in `fec/stance/prepare_stance_training.py` / `fec/stance/train_stance_domain.py`; score every variant with `fec/stance/stance_eval.py` against adjudicated gold only. Any new LLM step is Haiku 4.5 (rule 4).

**You have a result when...**
- *Methods track:* composed CU-alignment accuracy on a FRESH held-out user-adjudicated gold batch (labels collected AFTER the method is frozen) exceeds the 0.872 compose ceiling — which mathematically requires improving the 0.915 stance hop or joint modeling, since perfect valence alone caps at 0.872. Matching ~0.87 on fresh gold with full error attribution (which hop failed, per item) is the lesser but still publishable architecture result.
- *Capability track:* the media-blend and stance-matrix inputs to targeting (`fec/stance/build_media_blend.py`, `fec/stance/per_category_stance.py`) inherit the accuracy gain — measured as fewer user overrides needed per weekly refresh (the override ledger `press_stance_overrides.json` is the natural counter).

**Do NOT:** relabel any stance/press item by model judgment (rule 5 — Velázquez CFPB=Opponent / CCM=True-Neutral is user-ratified CORRECT, do not re-flag); "fix" the registry's ~0.52 CV against OLD golds (intentional — policy_force families override historical labels by user directive, `cu_valence_registry.json` `_doc`); hand-edit the registry JSON (it has a producer — `derive_valence_registry.py --write`).

**Siblings to load:** `moneyball-validation-and-qa` (gold-label machinery, what counts as evidence), `moneyball-change-control` (user-domain boundary), `moneyball-research-methodology` (freezing methods before fresh gold).

---

## Problem 5 — Cross-modal personality measurement (text / audio / votes)

**Status: OPEN — one modality pair validated for two traits only; one pre-declared route untried; the data asset quietly 4×'d.**

**Plain-language framing.** "Cross-modal" = measuring the same trait from *independent channels* — text (what they write/say), audio (HOW they sound: pitch, loudness, rhythm), and behavior (votes, cosponsorships). Agreement across channels that share no method is the strongest validity evidence measurement science has. The audio features used are eGeMAPS (a standard 88-number acoustic summary per recording) and, untried here, MFCC/spectral features (a finer-grained voice-quality representation).

**Why current SOTA fails.** Voice-personality studies (Marrero 2022; Rubio 2024 lineage) run on lab samples with self-report criteria, n in the dozens-to-low-hundreds, and no identity verification problem. Nobody has a *verified-speaker* elite-politician voiceprint corpus with independent behavioral criteria attached. And the known killer — speaker sex confounding acoustic-trait correlations — is usually unhandled; this repo learned it the hard way (the +0.208 voice-ES pass fell to partial r = −0.03 given gender; recorded at `big5_es_robustness_prereg.md:40-57`).

**This repo's asset.**
- **395 identity-verified clean voiceprints** with ≥180s each (median ~17 min): auto-caption + Haiku hard-signal speaker verification caught 142 wrong-member clips (`big5_methods.md:329`; pipeline `fec/members/b5_audio_fetch.py` → `b5_audio_verify.py` → `b5_audio_build.py`; `README.md:45`). The published-grade looks so far ran at **N=90** — the 395-member asset is 4× that and already carried one N=395 look (`big5_aes_round2_prereg.md:130`).
- A validated foothold: the faithful Marrero replication showed full eGeMAPS validly measures **E (+0.284, perm-p .030) and ES (+0.298, perm-p .017)** against the LLM instrument — the arousal traits — while A/C/O were null (`big5_audio_faithful_prereg.md:61-64`).
- **One pre-declared, still-untried route:** the MFCC fallback. The audio-round-2 prereg pinned it BEFORE that look: a null on eGeMAPS→C "is NOT yet a C verdict... a documented follow-up (not this look) would test an MFCC block before C-from-voice is closed" (`big5_audio_round2_prereg.md:22-24`); the RESULT confirms "the Rubio MFCC fallback remains the only untried voice-C route" (line 43). A pre-declared follow-up is the cleanest possible next experiment — the hypothesis space was fixed before any data.
- Behavioral criteria on the voice roster: diligence_z (the valid C criterion) etc. from Problem 1's disposition layer — voice and votes share zero method.

**First three steps (in this repo).**
1. **Build the MFCC/spectral feature block** as a sibling of `fec/members/b5_audio_build.py` (which already handles clip iteration, the verification gate, duration-weighted pooling, and z-scoring — copy that skeleton): new script `fec/b5_audio_mfcc_build.py`, guarded `__main__`, writing `b5_audio_mfcc_cache.json.candidate` (the `.candidate` suffix = built-but-unpromoted, the repo's staging convention). Critical trap to inherit: `b5_audio_build.py` keeps ALL clips if the verify artifact is missing — make the new script HARD-FAIL without `b5_audio_verify.json` instead.
2. **Quantify the sample, read-only:** count the overlap of the 395 voiceprinted members with diligence_z coverage (from `behavioral_dispositions.json`) — that intersection is the effective n for voice-C, and per Problem 1's power map it needs to be large enough that a true r=.40 is recoverable; if the overlap is ≈200, run a plant-battery power check FIRST (recipe in `moneyball-proof-and-analysis-toolkit`) so a look is never wasted on an underpowered stratum.
3. **Lock a prereg** (per `moneyball-research-methodology`) for MFCC→diligence_z: bars of the established shape (held-out r ≥ +0.15 AND exact perm-p < .05 — the A1 bar from `big5_audio_round2_prereg.md:17`), with the sex/gender partial as a GATING bar (the repo's recurring confound — never optional again), party partial reported, and a simulate battery in front of the look.

**You have a result when...**
- *Methods track:* a second trait beyond E/ES — realistically C via MFCC, since audio-A is dead — clears a LOCKED cross-modal look against a *behavioral* criterion with the gender partial gating, and survives adversarial re-derivation. That would be voice→behavior validity on verified elite speakers at n≈300+, which does not exist in the literature. A clean MISS finally *closes* voice-C honestly (the round-2 RESULT explicitly left it open pending MFCC) — also a result.
- *Capability track:* the validated second modality feeds the desk's confidence tiers (display-only first, like every instrument here — the firewall: no engine reads trait scores, `big5_methods.md` §15); any engine consequence is a separate user-gated ratified step.

**Do NOT:** re-open voice-ES as a *validation* route (CLOSED PERMANENTLY — the sex-relative retrain was the pre-declared final attempt, `big5_methods.md:421-429`); re-try audio-A (null twice) or CT-CM latent modeling with audio anchors (third CT-CM failure, "Closed.", `big5_audio_round2_prereg.md:56-60`); claim ES cross-modal validation without the gender-confound caveat (rule 8); run `b5_audio_fetch.py`/`b5_audio_verify.py` casually (network + API spend + live-tree writes).

**Siblings to load:** `psychometrics-reference` (cross-modal validity, confounds), `moneyball-research-methodology`, `moneyball-proof-and-analysis-toolkit` (power check before the look), `moneyball-build-and-env` (new-script conventions: `__main__` guard, utf-8 boilerplate, `.candidate` suffix).

---

## Cross-problem synergies (candidate, unvalidated)

- Problems 2 and 3 share one outcome stream: a single frozen snapshot (Problem 2) can score BOTH the receptivity magnitudes (H1/H2) and the full-vs-ablated kernel comparison (Problem 3) — one wait, two results. Declare both uses at freeze time, not after.
- Problem 1's gates open passively: interview collection grows MEM_N toward 250, and bills-archive + corpus growth feed the A-diagnostic. Check the gates at each 120th-Congress planning point (see `moneyball-congress-rollover-campaign` — note a Congress rollover changes the roster, which resets every stratum definition).
- Problem 5's MFCC block, if it validates voice-C, gives Problem 1 a third method for the C column — the multi-method matrix everyone in this program has wanted, WITHOUT re-opening the closed CT-CM machinery (report the matrix; do not fit latent factors).

## Provenance and maintenance

Written 2026-07-09 against the live tree at commit 88a7048 (main merged into the round-5 session branch). Every fact below is volatile; paste these from the repo root — `cd "C:\Users\pgoff\OneDrive\Desktop\Melange Systems"` — to re-verify before relying on it. All commands are read-only.

| Fact (as of 2026-07-09) | Re-verify with |
|---|---|
| N-route DATA-GATED at MEM_N ≥ 250 (currently 201/456) | `Select-String -Path big5_n_matrix_prereg.md -Pattern "MEM_N"` and the coverage one-liner in Problem 1 step 1 |
| A-route DIAGNOSTIC-GATED, 5 seeds, ≥3/5 on bars 1-4 | `Select-String -Path big5_a_matrix_prereg.md -Pattern "DIAGNOSTIC-GATED","424242"` |
| Only seed 424242 wired in code (no 5-seed runner shipped) | `Select-String -Path fec\members\b5_a_matrix.py,fec\members\b5_n_matrix.py -Pattern "424242"` |
| Flagged confirmatory text-C step (Empath→diligence +0.348) | `Select-String -Path big5_audio_round2_prereg.md -Pattern "0.348","CONFIRMATORY"` |
| outcome_snapshot bars (≥.20/.10/−.10) and refusal (60 days, 150 movers) | `Select-String -Path fec\engine\outcome_snapshot.py -Pattern "BARS","MINIMUM DATA","UNDERPOWERED"` |
| One snapshot frozen 2026-07-04 (armed state; more may accrue) | `Get-ChildItem "data\engine\outcome_snapshot_*.json"` (live tree; `data\engine\outcome_snapshot_2026-07-04.json` exists, verified 2026-09-30; `--freeze` writes new snapshots there, `fec/engine/outcome_snapshot.py:64`; corrected 2026-09-30) |
| kb_benchmark recorded numbers (+0.24 / +0.14 / −0.21) | `Select-String -Path AUDIT_FINDINGS_2026-07-04.md -Pattern "kb_benchmark" -Context 0,8` |
| Ablation dials exist (RECEPT_LAYER, BAKKER_XCUE, edge_mult in build_P) | `Select-String -Path fec\moneyball_core.py -Pattern "RECEPT_LAYER","edge_mult"` ; `Select-String -Path fec\engine\lt_priming.py -Pattern "BAKKER_XCUE"` |
| Stance 0.915 / valence 0.689 / ceiling 0.872 | `Select-String -Path fec\stance\apply_two_hop_stance.py -Pattern "0.915"` |
| Registry ladder print (0.677 / 0.737 / 0.872) | `Select-String -Path fec\stance\derive_valence_registry.py -Pattern "ladder"` |
| 395 verified voiceprints | `Select-String -Path big5_methods.md,README.md -Pattern "395"` |
| Audio E+ES pass; A/C/O null; MFCC route untried | `Select-String -Path big5_audio_faithful_prereg.md -Pattern "0.284","0.298"` ; `Select-String -Path big5_audio_round2_prereg.md -Pattern "MFCC"` |
| coop_v2 promotion state (granted+shipped @94f09cf, merged to main 2026-07-10; the docstring was updated post-promotion @c80e1d3) | `git log --oneline \| Select-String "ENGINE PROMOTION"` |
| Vote Smart ES status (adjacent, not a frontier problem) | `git log --all --oneline \| Select-String "Vote Smart"` — the authoritative freshness test per `moneyball-docs-and-claims` §3.2. Do NOT probe the key file: collection completed 517/518 via a user-directed browser-session amendment that never used it; look CONSUMED @e77703c, RESULT-VS TIER 5 UNCORROBORATED; merged to main 2026-07-10 |
| 6.6M-word corpus figure (dated 2026-07-02; grows weekly) | `Select-String -Path README.md -Pattern "6.6M"` |
| Behavioral dispositions = six criteria incl. reactivity_z | `Select-String -Path fec\members\behavioral_dispositions.py -Pattern "reactivity_z" -List` |

If any gate condition, bar, or count above has changed, trust the prereg/methods files over this page — they are the documents of record (`moneyball-docs-and-claims`), and this page must be updated to match, never the reverse.
