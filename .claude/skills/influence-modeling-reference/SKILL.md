---
name: influence-modeling-reference
description: The influence/persuasion/network theory pack for the Moneyball congressional model, explained from zero and mapped to exact code. Load to understand or modify WHAT the engines compute and WHY — Independent-Cascade vs Linear-Threshold, the two cpf physics, submodular/CELF/Golovin-Krause greedy optimization and the (1-1/e) guarantee's scope, Monte-Carlo + Common Random Numbers (why MC=20 is safe), Bakker cross-cue signing, prospect theory / LOSSFRAME, Fouirnaies-Hall electoral incentive, Noble-Turner going-public, Fink multiplex layers, RELINK/GCOMB/D*-Lite pathfinding, the say-do gate, or how receptivity multipliers enter an engine. Also load when asked "what paper is this formula from?" or before writing any claim that cites a paper (citation-honesty rules live here). Does NOT cover engine operation (moneyball-run-and-operate), receptivity psychometrics (psychometrics-reference), the dial catalog (moneyball-config-and-flags), or prereg/look discipline (moneyball-research-methodology).
---

# Influence modeling reference — the theory as implemented here

This project models how a credit-union (CU) advocacy shop can move the U.S. Congress: which members to fund, which to recruit as messengers, when to run a loud public campaign vs quiet diplomacy. It does this with two families of network influence models (Independent Cascade for coalition contagion, Linear Threshold for direct persuasion), greedy submodular optimization for budget allocation, and a layer of behavioral-science multipliers (personality, electoral incentive, loss aversion) that scale everything per member. Every concept below is defined in plain language, then pinned to the exact file and line that implements it. All citations in this codebase are **honest-analogical** — they mean "we borrowed this paper's mechanism," never "this paper validated our numbers" (see the Citation honesty section, which is binding on anything you write).

## When NOT to use this skill

- You want to **run** an engine, the pipeline, or a dashboard → `moneyball-run-and-operate`. (Reminder that applies to everything here: importing almost any `fec/*.py` executes it. `fec/paths.py:7-8` sets ROOT to `MONEYBALL_ROOT` when set, else to the parent of the imported paths.py, so a script run from a git worktree targets that worktree's EMPTY data plane; with `MONEYBALL_ROOT` pointed at LIVE, writes DO land in LIVE. `fec/tests/run_tests.py` resolves its own root from `__file__` and ignores `MONEYBALL_ROOT`. See `moneyball-change-control` law 7.) (corrected 2026-09-30; verified against `fec/paths.py:7-8`, `fec/tests/run_tests.py:8`)
- You want the **meaning/validity of the personality inputs** (Big Five, reliability, the behavioral dispositions) → `psychometrics-reference`.
- You want to **change a constant or env dial** → `moneyball-config-and-flags` (the dial table) and `moneyball-change-control` (many constants are user-ratified).
- You want the **history of dead ends** (what was tried and killed) → `moneyball-failure-archaeology`.
- You want **analysis recipes** (how to prove MC stability yourself, power studies) → `moneyball-proof-and-analysis-toolkit`.

## Quick reference

| Concept | Plain meaning | Code home | Output artifact |
|---|---|---|---|
| Competitive IC cascade | pro & anti "colors" race across the network | `fec/moneyball_core.py:421-428` (`build_P`) + per-engine `cascade()` | — (kernel) |
| LT winnability (`pflip`) | money pull vs peer pull vs resistance | `fec/engine/flip_model.py:74-94` | (library) |
| LT priming | cheapest recruits+money to tip one member | `fec/engine/lt_priming.py` | `lt_priming.json` |
| Budget frontier (IC greedy) | spend→coalition-size curve per issue | `fec/engine/budget_frontier.py` | `budget_frontier[_electoral].json` |
| Joint $2.5M allocator (G-K/CELF) | the joint money plan across all issues; guarantee scope in Section 6 (corrected 2026-09-30; verified against `fec/engine/optimize.py:3-11`) | `fec/engine/optimize.py` | `optimize_result.json` |
| Per-issue diagnostics ($2M each, NOT additive) | flip $ / coalition seeding per issue | `fec/engine/per_topic_flip.py`, `fec/engine/per_topic_coalition.py` | `per_topic_alloc.json`, `per_topic_coalition.json` |
| Salience shock (Noble-Turner) | when going public helps vs backfires | `fec/engine/salience_shock.py` | `salience_advisory.json` |
| Money→lean curve + defection | saturating donation effect, DTHRESH=11.25 | `fec/engine/money_response.py` | (library) |
| Route finder (RELINK/MOPBD*) | Pareto-optimal recruitment chains | `fec/engine/cosponsor_route.py` | prints only |
| Scenario runner | what-if: money/stance/defection deltas | `fec/engine/scenario.py` | prints only |
| MC stability proof | MC=20+CRN is not draw-overfit | `fec/engine/mc_stability_check.py` | prints only |
| Receptivity multipliers | per-member behavioral scaling of all of the above | `fec/members/receptivity_layer.py` | `member_receptivity.json` |
| Multiplex network | cosponsor + press + social + interest edges | `fec/network/build_multilayer_network.py` | `congress_cosponsor_network_AUG*.xlsx` |

Key constants (env-dialable unless noted; changing user-ratified ones is Paul's call — see `moneyball-change-control`): `SEED=7 MC=20` (frontier/coalition), `MC=40` (scenario), `WM,WP=0.35,0.65` (flip_model.py:12), `MAXSHIFT=18 HALF=0.10 DTHRESH=11.25 LOSSFRAME=1.10` (money_response.py:13-28), `PERS_NONE=0.45` user-ratified (moneyball_core.py:138), `BUDGET=2500000 INC=500 PMAX=10000` (optimize.py:20-21), `CEDGE=10000 K=5` (cosponsor_route.py:9-10), `SOC_REINF=0.3` i.e. +30% cap (build_multilayer_network.py:83).

---

## 1. The domain, from zero: Congress as this model sees it

- **Members**: 533 tracked members of Congress (House + Senate combined; the roster is `congestion.json`, one record per member with `bioguide` ID, party, and money fields `cu`/`banks`/`finserv`/`receipts` = dollars received from CU PACs / bank PACs / financial-services PACs / total fundraising). The 533 count is audit-enforced (`fec/audit/legacy_workbook_audit.py:26,57,73`).
- **Party**: 'D'/'R'/'I' resolved from roll-call roster CSVs `votes/HS119..117_members.csv` (moneyball_core.py:28-39). Party matters because cross-party influence is weaker (Section 2).
- **Cosponsorship**: when a member formally signs onto another member's bill. The base influence network's edges are cosponsorship counts between member pairs, loaded from the newest `congress_cosponsor_network_*.xlsx` (moneyball_core.py:102-119). Cosponsoring together = a working relationship = a channel influence can flow through.
- **Roll-call votes**: recorded floor votes. Used two ways: `vote_category_lean.json` per-issue vote leans (say-do gate Path V, Section 8.4) and participation rates (a diligence input — see `psychometrics-reference`).
- **Committees**: Congress does most gatekeeping in committees; the Chair and Ranking Member ("gavel" holders) can block bills from ever reaching a vote. The workbook 'Committee Data' sheet records seats/roles; committee jurisdiction is say-do gate Path J (moneyball_core.py:250-275).
- **The stance matrix**: `category_stance.json` classifies every member on each of **18 CU issue categories** (list at `fec/stance/per_category_stance.py:17-20`: Examination & Supervision, CU Capital Requirements, NCUA Budget & Insurance, Interchange, Payments, Technology & Emerging, Fraud Prevention, Data Privacy & Cyber, Charter Modernization, Defense CU Issues, Field of Membership, CU Tax Status, CDFI Fund, CFPB, Credit Card Mandates, TCPA, Member Business Lending, Mortgage & Housing).
- **Per-category tier ladder** (pro → anti): `Champion / Defender / Ally / Highly Persuadable / True Neutral / Lean Skeptic / Skeptic / Opponent`, plus `—` = no recorded position (59.8% of cells; flip_model.py:13). A separate finer **10-rung overall ladder** (adds Persuadable / Lean Persuadable / Highly Skeptical) summarizes each member across all categories, IMP-weighted (moneyball_core.py:154-167).
- **Defensive vs offensive categories**: `DEFENSIVE={'Interchange','Credit Card Mandates'}` (per_category_stance.py:25) are issues the CU side wins by **blocking** legislation (gridlock is victory), so their top tier is **Defender** and press weighs more. Everything else is offensive (CU wants a law passed). CU Tax Status is a defend-type fight but is deliberately NOT in DEFENSIVE — changing that weighting is the user's call (standing flag, per_category_stance.py:24). The defend/offense split drives the salience-shock advisory (Section 8.3) and the GATEKEEP set (Section 8.4).
- **Persuadability by tier**: `PERS` table (`fec/moneyball_core.py:430-434`): Champion .10, Defender .12, Ally .40, Highly Persuadable .65, Persuadable .60, Lean Persuadable .55, True Neutral .50, Neutral .50, Lean Skeptic .40, Skeptic .25, Highly Skeptical .15, Opponent .08, `—` = `PERS_NONE` (env, .45). Highly Persuadable was .55 until the 2026-07-15 WIP snapshot e3d2923d0; no ratification is recorded. `'—'` = `PERS_NONE` = 0.45, user-ratified 2026-07-02 as "Ally parity" (silence never outranks a declared Ally); the code has Ally = 0.40 (`fec/moneyball_core.py:430-431`), so parity does not currently hold — open ruling N6, Paul's; do not change either value in code. (corrected 2026-09-30; verified against `fec/moneyball_core.py:430-434`)
- **Issue importance**: `IMP` weights per category (CU Tax Status and Credit Card Mandates = 3.0, the max), anchored to the ABB26 conference handout (moneyball_core.py:141-144).

## 2. Two partisan physics + one cascade kernel

Cross-party influence is weaker than same-party influence, but HOW MUCH weaker depends on what's flowing. The kernel deliberately has **two named edge factors** (moneyball_core.py:8-12) — pre-refactor there was one ambiguous `cpf` copy-pasted 8 times under both physics, which caused real drift bugs:

- **`cpf_diffusion(n,u)`** (moneyball_core.py:120-122) — cascade/contagion physics: cross-party edges dampened to `0.4 + 0.6*sqrt(bpf_n*bpf_u)`, same-party 1.0. `bpf` = each member's bipartisanship fraction (from `bipartisan.json`, default 0.24; moneyball_core.py:40-44). Two bridge-builders keep near-full cross-party flow. Used by every **spread/cascade** engine through `build_P`'s default `physics=cpf_diffusion` (`fec/moneyball_core.py:421`): budget_frontier.py:46, per_topic_coalition.py:24, lt_priming.py:34, cosponsor_route.py:23, salience_shock.py:69, scenario.py:39 (corrected 2026-09-30; verified against those `MBC.build_P(adj)` call sites).
- **`cpf_pressure(n,u)`** (moneyball_core.py:123-125) — direct-persuasion physics: co-partisan ×1.7, out-partisan ×0.5. Rationale: source alignment — people weight persuasion attempts from their own side far more (Furnas/Bakker line of work). Used by the **flip** engines: flip_model.py:49, per_topic_flip.py:38.

**The cascade kernel** `build_P` (moneyball_core.py:421-428) converts an edge weight to an activation probability:

```
p(u→v) = w·cpf·σ_v / (w·cpf·σ_v + 6)      σ_v = rc(v,'edge_mult')  (receiver susceptibility)
```

A weight-6 tie ≈ 50% activation. Note the receptivity multiplier sits on the RECEIVER — how movable v is, not how loud u is. All cascade, priming and route engines share `MBC.build_P(adj)`, whose default `edge_mult=True` puts the RECEIVER's susceptibility on every edge (`fec/moneyball_core.py:421-428`); call sites include `fec/engine/scenario.py:39`, `fec/engine/cosponsor_route.py:23`, `fec/engine/lt_priming.py:34` (unified by the 2026-07-08 audit fix N-1, commit 158d311c2). Off-chain exception: `fec/engine/method_audit.py:46` still hand-rolls its own kernel without cpf or edge_mult (diagnostic only). (corrected 2026-09-30; verified against `fec/moneyball_core.py:421-428`)

## 3. Independent Cascade (IC): the coalition/mobilization side

**Model**: seed members start "active"; each newly-active member gets ONE chance to activate each neighbor with probability `p(u→v)`; repeat until nothing new fires. Here it is **competitive**: two colors race — 'A' (pro-CU coalition) vs 'B' (anti: declared opponents + money-activated bystanders) — first color to reach a member claims them. This is Bharathi, Kempe & Salek's competing-diffusion model, cited at scenario.py:6-7.

Implementation (identical `cascade()` in budget_frontier.py:40-51, per_topic_coalition.py:27-38, scenario.py:40-51, salience_shock.py:71-80):
- A-seeds = members whose tier on this issue is in `PRO={'Champion','Defender','Ally'}`; B-seeds = `ANTI={'Opponent','Skeptic'}` plus **bystanders**: neutral members drawn anti with probability `min(0.9, industry_$/400000)` per iteration (bank money makes a neutral member a potential anti-mobilizer).
- **Contingent seeding** (Chen et al. UAI 2021, receptivity_layer.py:28-33): a member YOU lobby into the coalition is not guaranteed to activate — "legislators know they are being lobbied." A lobbied seed fires with `gate(n,cs) = max(0.15, seed_prob(n) * SGATE[tier])` (moneyball_core.py:151-153) on a dedicated CRN stream (budget_frontier.py:84, per_topic_coalition.py:56). Committed allies are never gated — they're already active.
- **Spread** = expected number of A-colored members, averaged over MC=20 iterations.

Used by: budget_frontier (greedy seed picking per issue, incl. `--electoral` mode adding contest/defend plays with `REPFAC=0.6` primary-win discount, budget_frontier.py:26-27,72-92), per_topic_coalition ($2M per-issue seeding, budget ∝ marginal × (1+0.8·bpf) bridge boost, per_topic_coalition.py:17,64), scenario.py (what-if deltas), salience_shock (spread under stance shocks).

## 4. Linear Threshold (LT): the flip/persuasion side

**Model**: a member flips when accumulated pro-influence exceeds their resistance threshold θ. Two implementations:

**4a. `flip_model.py` — winnability.** `pflip(n) = a/(a+b)` where (flip_model.py:74-79):

```
a = WM·pm·(cu+1)/((cu+1)+HALFF·R) + WP·nA/mAt     (pro pull:  CU money + proximity to this issue's champions)
b = WM·pm·(ind+1)/((ind+1)+HALFF·R) + WP·nB/mBt   (anti pull: industry money + proximity to opponents)
```

- `WM,WP = 0.35,0.65` — money is deliberately the **minority partner** to peer influence ("money buys access/effort, not votes" — Ansolabehere; Hall & Wayman; Kalla & Broockman; flip_model.py:12).
- The money term is a **Michaelis-Menten saturation curve** (biochemistry's diminishing-returns form): dollars relative to the member's own fundraising `R`, half-max at `HALFF=10%` of receipts. A $100k check barely moves a $8M fundraiser.
- `nA/nB` = cpf_pressure-weighted network proximity to this issue's pro/anti camps (flip_model.py:86-87).
- `pm = rc(n,'pressure_mult')` — the receptivity layer (Section 7).
- **Target value** `tgt = priority_base_signal(engagement, topic_priority(cat,'flip'), BASE) · PERS[tier] · (1+0.3·bpf) · delivery_mult` (`fec/engine/flip_model.py:127-128`, `BASE=0.15` at `:18`) — how much a flip is WORTH: issue engagement, primacy-tier priority, persuadability, a bridge-builder bonus, and the say-do talker discount. `priority_base_signal(e,p,b) = max(0, e + b·p)` (`fec/moneyball_core.py:477-479`); the flip priority is the member's primacy-tier anchor adjusted by a leave-one-topic-out orientation over the member's OTHER CU issue positions (α = 0.15 for flip, `PRIORITY_ORIENTATION_ALPHA`, `fec/moneyball_core.py:439-444`). The old `0.15·score/smax` rank-score term is gone. (corrected 2026-09-30; verified against `fec/engine/flip_model.py:86-93,127-128`)
- `flip_value(cat) = Σ tgt·pflip` = expected weighted flips on a topic (flip_model.py:91-94). **Read it as remaining-pool value**: converting someone to Ally DRAINS winnability even though it's a win (salience_shock.py:182-184).

**4b. `lt_priming.py` — cheapest tip for one target.** Classic LT: recruited pro neighbors contribute `P[u][v]` units of pressure (`fec/engine/lt_priming.py:78`; corrected 2026-09-30); money contributes via the money_response curve; the member tips when `pressure + money ≥ θ`. θ per tier widens at the committed end (`THETA` lt_priming.py:16 — Bakker asymmetry; Kalla-Broockman find ~0 persuasion effect on the opposed), plus a money-capture term and `COMMIT=0.25` per declared Opponent cell anywhere in the member's matrix (a PAC-free ideologue is not cheap; lt_priming.py:59,71-72). Stance-integrity gates (user-ratified 2026-07-04) forbid targeting or recruiting system-level Skeptics/Opponents, with **Lean Skeptic explicitly carved out** (lt_priming.py:57-66). The greedy recruit-vs-money tradeoff buys network pressure only where it's cheaper per influence-unit than money (lt_priming.py:76-91). Writes `lt_priming.json` (single-topic, default TOPIC=Mortgage — running with another TOPIC clobbers the chain artifact until the next pipeline run).

**Guarantee scope caveat** (lit-audit-verified wording, scenario.py:8-12): the competitive-LT flip side has **NO general submodularity guarantee** — Borodin et al. prove submodularity can fail there — so flip-side greedy runs as a heuristic. No audit checks flip-side marginals: `fec/audit/audit_frontier.py:18-26` checks them only on the budget_frontier coalition and electoral paths, and the allocator tests its own per-member diminishing returns with `concavity_violations()` (`fec/engine/optimize.py:53`) (corrected 2026-09-30). Never claim (1−1/e) for the flip side. The joint allocator's own scope (exact on its `INC` grid only in a fixed stance state) is in Section 6, on the authority of `fec/engine/optimize.py:3-11,36-38` (corrected 2026-09-30).

## 5. Monte Carlo + Common Random Numbers; why MC=20 is safe

IC spread has no closed form, so it's estimated by simulation: MC iterations, average the spread. Naive resimulation makes marginals (`spread(S+c) − spread(S)`) mostly RNG noise. Two-layer fix:

1. Per-iteration reseed `random.seed(1000003*SEED+it)` so baseline and treatment share the bystander-draw stream (budget_frontier.py:77, per_topic_coalition.py:54). Bystander draws are rolled for EVERY member first, THEN filtered — gating the draw behind membership changes draw counts and desyncs the stream (the 5.A fix, per_topic_coalition.py:57).
2. **Edge-keyed CRN**: each edge draw is `sm64(it*NM*NM + idx[u]*NM + idx[v])` — a splitmix64 hash of (iteration, edge), so edge (u,v) at iteration `it` ALWAYS draws the same value no matter which seeds changed (moneyball_core.py:126-131; scenario.py:41-43). Seed-activation rolls use a separate stream keyed `(1<<62)+it*NM+idx[n]` (per_topic_coalition.py:56). Baseline vs perturbed runs therefore differ ONLY by the real perturbation.

**Why MC=20 doesn't break greedy** (the Almazaydeh failure mode): Almazaydeh et al. (Sci Rep 2026) showed noisy independent MC estimates corrupt lazy-greedy seed selection (their CELF++ at 50 sims captured only 11.2% of true spread). Here that exact failure cannot occur because competing candidates are always compared under IDENTICAL draws (CRN); the residual risk — the picked set overfitting to one particular 20-draw realization — is measured directly by `fec/engine/mc_stability_check.py` (docstring lines 3-10): it rebuilds a single-topic frontier at MC=100 and at SEED=1/13 and compares picked seed sets. Validated result: 100% seed overlap (comment at salience_shock.py:44). If you change cascade physics, RE-RUN this check (it spawns budget_frontier subprocesses with `FRONTIER_OUT` temp files — see `moneyball-run-and-operate` before executing anything).

Defaults: SEED=7, MC=20 (budget_frontier.py:6-7, per_topic_coalition.py:5-6), MC=40 in scenario.py:27 and cosponsor_route.py:28. Trap: `MC` is the moneyball_core module alias in non-simulation scripts but an integer in simulation scripts — read the import line before copying code.

## 6. Greedy optimization: submodularity, CELF, Golovin-Krause

**Submodularity** = diminishing returns: adding a seed to a bigger set helps less. For monotone submodular objectives, picking greedily (always the best next marginal) is guaranteed to achieve at least `(1 − 1/e) ≈ 63.2%` of the optimal value.

- **Lazy greedy / CELF** (Leskovec et al. KDD'07): keep candidates in a priority queue by their LAST-KNOWN marginal; re-evaluate one only when it reaches the head (submodularity ⇒ marginals only shrink, so a stale value is an upper bound). Implemented with `heapq` + a step/level check in budget_frontier.py:96-106, per_topic_flip.py:67-71, optimize.py:74-96.
- **The joint allocator** `optimize.py` is THE real budget: $2.5M pot, $500 increments, `PMAX=$10k` per member = the FEC PAC-to-candidate per-cycle legal cap (optimize.py:20-21). Objective = total LT winnability across all issues (separable-concave in money only in a fixed stance state — scope note below; corrected 2026-09-30; verified against `fec/engine/optimize.py:3-11`). The per-topic tools each spend a hard-coded $2M **per issue as diagnostics — the budgets are NOT additive** (optimize.py:20 comment).
- **Adaptive submodularity** (Golovin & Krause) — NOT claimed here. Their guarantee is for a greedy policy that re-plans after OBSERVING outcomes; a **conversion** here is a MODELED threshold crossing, not an observed outcome: when cumulative CU money on a member crosses their money-response defection threshold, they join the coalition — their flip is banked into `secured` at certainty, their stance improves by at most `CONV_MAXSTEP=1` fine tier, and the queue is rebuilt (optimize.py:112-122, shift_pro cap at :78). The engine replans after that modeled transition but claims neither an adaptive-submodularity guarantee nor the fixed-state certificate (`optimize.py:3-11`; `conversion_reachable` at `:36-37`). At production defaults the path does not fire: the live `optimize_result.json` read 2026-09-30 shows `conversion_reachable: false`, `certificate_valid: true`. (corrected 2026-09-30; verified against `fec/engine/optimize.py:3-11,36-38,112-122`)
- **The G-K data-dependent bound** (`dd_bound`, optimize.py:86-98; JAIR'11 Lemma 5.3/A.9): from the current state, no policy spending ≤ BUDGET can beat the budget-filling sum of current per-chunk marginals. It is kept only as a diagnostic, computed when the fixed-state certificate holds (no reachable conversion, verified diminishing returns; `:100-102,142-143`) and printed on the `Fixed-state certificate: exact $<INC>-grid optimum … G-K diagnostic upper bound …` line (`:151-153`); otherwise the run prints that the certificate is unavailable and records `guarantee.kind: none` (`:154-158,172-177`). The old "greedy gain ≥ X% of any policy's gain" print is gone. (corrected 2026-09-30; verified against `fec/engine/optimize.py:86-102,142-177`)
- **Knee**: the spend level where marginals fall below a fraction of peak — 25% for the frontier (budget_frontier.py:107-111), 20% for the optimizer, which reports honestly when no knee exists within budget (optimize.py:97-104).

**(1−1/e) scope — memorize this** (allocator: `fec/engine/optimize.py:3-11,36-38`; coalition and flip sides: `fec/engine/scenario.py:8-12`, lit-audit run-4j; corrected 2026-09-30): in a fixed stance state the allocator's objective is separable with diminishing-returns chunks, so greedy is the exact discrete optimum on the `INC` grid; the Golovin-Krause data-dependent bound is kept as a diagnostic. If a MODELED money threshold can flip a stance (`conversion_reachable`), the engine replans after that modeled transition but claims neither an adaptive-submodularity guarantee nor the fixed-state certificate. Coalition side: follower-vs-fixed-opponent IC is submodular (Bharathi-Kempe-Salek). Competitive-LT flip: no general guarantee (Borodin et al.) — heuristic (caveat in Section 4). Any doc/commit claiming otherwise is wrong.

## 7. The receptivity multipliers: how behavior science enters every engine

`fec/members/receptivity_layer.py` fuses four literatures into per-member multipliers, written to `member_receptivity.json` and read via `MC.rc(member, key, default=1.0)` — **neutral fallback**: if the artifact is missing or `RECEPT_LAYER=0`, every engine silently reverts to legacy behavior (moneyball_core.py:45-51). The multipliers and their clips (receptivity_layer.py:133-154):

| Multiplier | Formula | Clip | Consumed by |
|---|---|---|---|
| `susc_mult` | `1 + .18·susc` | [0.70, 1.30] | salience shock step size (salience_shock.py:113) |
| `edge_mult` | `1 + .12·susc` | [0.80, 1.20] | cascade kernel receiver side (moneyball_core.py:135) |
| `pressure_mult` | `susc_mult · incent_mult · pt_mult` | [0.50, 1.60] | money pull in flip_model.py:94, per_topic_flip.py:42, optimize.py:31, money_response.py:54 |
| `seed_prob` | `0.60 + .10·coop + .06·breadth + .04·visibility` | [0.30, 0.90] | contingent seed gate (moneyball_core.py:153) |

where `susc` = the Byrne susceptibility composite blended with the persona channel at `PERSONA_W=0.30` (user-ratified KEEP — do not propose removal; receptivity_layer.py:92,126), `incent_mult` = Fouirnaies-Hall electoral incentive, `pt_mult` = Linde-Vis prospect theory. Construction and validation status of `susc` itself → `psychometrics-reference`.

- **Fouirnaies & Hall (APSR)**: legislators in their FINAL term (no reelection incentive) systematically reduce effort/responsiveness. `incent_mult = 0.60` if retiring (list = `fec/retiring_members.txt`, a hook file), else `1 + 0.30·(competitiveness − 0.5)` clipped [0.85, 1.15] — safe seats below 1, competitive seats above (receptivity_layer.py:15-20,136).
- **Prospect theory (Linde & Vis, Pol.Psych 2016)**: politicians are risk-seeking in the LOSS domain, risk-averse in the GAIN domain. Loss domain = live race (electoral play defend/contest, or security<0.45) → `pt_mult=1.15`; safe → 0.92 (receptivity_layer.py:21-27,137-138). Separately, **`LOSSFRAME=1.10`**: a competitor THREAT moves lean more than an equal-sized CU gift — Kahneman-Tversky loss aversion (λ≈2.25) deliberately attenuated to elite scale per Linde & Vis's finding that politicians' framing effects are real but smaller than students' (money_response.py:24-28,55).
- **`delivery_mult` — the say-do talker discount** (moneyball_core.py:294-306): `clip(1 − 0.15·max(0, gap−1), 0.70, 1.00)` from `say_do_gap.json` — a member whose CU rhetoric far outruns recorded action gets their engine TARGET VALUE (never their rank) priced down up to 30%. Consumed in flip_model.py:89, per_topic_flip.py:64, per_topic_coalition.py:60.

**Coverage differs by path**: every `build_P` consumer (cascade, priming and route engines) gets `edge_mult`; flip/money paths get `pressure_mult` (Section 2; corrected 2026-09-30; verified against `fec/moneyball_core.py:421-428`). The dashboard's JS engine mirror ships `pmult/emult/dmult` in the bundle since commit fd963ab (parity within 0.15% on all 18 issues) — any engine change here requires a matching template edit (see `moneyball-architecture-contract` on the JS-mirror invariant).

## 8. Behavioral-science mechanisms, one by one

### 8.1 Bakker cross-cue signing (out-party cues ≤ 0)
Bakker-Lelkes-Malka (JOP): **out-party cues do not persuade** — the effect is null-to-backfire. The cascade kernel's unconditional 0.4 cross-party floor is exactly an attenuated-POSITIVE out-party cue, which the priming engine (direct persuasion) must not inherit. Fix (lt_priming.py:31-39, landed @0e131c0, `BAKKER_XCUE=0` reverts): in lt_priming's pressure/recruit terms ONLY (kernel untouched), a cross-party pro-cue is scaled by `xf(u,v)=sqrt(bpf_u·bpf_v)` — perfect bridge pairs keep full influence, non-bridge out-party cues fall to ~0, **clamped at 0, never negative** (backfire magnitude not invented). Mirrored in the dashboard JS `prime()` — keep in lockstep.

### 8.2 Money → lean → defection (`money_response.py`)
`shift_lean = MAXSHIFT·(r/(r+HALF)) · pressure_mult · (LOSSFRAME if competitor)`, r = donation/receipts (money_response.py:50-56). `MAXSHIFT` was calibrated 40→18 ("money buys access, not votes" — Ansolabehere; Fowler-Garro-Spenkuch null on vote-buying; :13). `DTHRESH=11.25` = the lean shift that risks a defection, RESCALED from 25 when MAXSHIFT was cut so defection stayed mathematically possible — the boundary is a donation ≥ ~1/6 of receipts, still rare/earned (:16-23). Defection walks the FULL 10-rung overall ladder one rung per DTHRESH crossing; only Champion/Opponent are immune; Highly Skeptical is deep but movable (user 2026-07-01) (:30-42,57-63). `receipts=0/null` means MISSING FEC data: the median is imputed unconditionally in `money_response.py` (`receipts()`, :57-63), `flip_model.py:32-33`, `per_topic_flip.py:28-29` and `lt_priming.py:44-50`. Industry money (banks+finserv) is imputed separately, only when `industry_money_missing()` (`fec/engine/money_observation.py:4-13`) finds no verified or observed money, in exactly four engines: `flip_model.py:40-41`, `per_topic_flip.py:24-25`, `budget_frontier.py:28-30`, `salience_shock.py:144-146`; `IMPUTE_IND0=0` disables it. That 2026-09-08 rule is recorded on main but not ratified (Project Brain D-051, ruling R2). Raw industry money: `per_topic_coalition.py:14` (a chain step; bystander draws at `:68`) and `scenario.py:65` (bystander channel only; its flip channel uses the imputed baseline at `:111`). (corrected 2026-09-30; verified against `fec/engine/money_observation.py:4-13` and the lines cited)

### 8.3 Noble-Turner going-public (`salience_shock.py`)
"Going public" = a loud, high-salience advocacy campaign (an executive speech, or by extension an ABB26 fly-in) instead of quiet lobbying. Noble & Turner (2024) show it is STRUCTURED, not a flat boost (docstring :4-38 — the old flat ×1.6/×0.6 dial is the retired dead end):
- Three regimes with probabilities summing to 1: **rally** (both parties move toward the actor), **retreat** (co-partisans toward, out-partisans AWAY), **backfire** (both away). Estimated FROM the stance matrix per issue: `b = min(.35, .05+.10·ψ)`, `p=(1−b)(1−z_n)`, `q=(1−b)·z_n` — so p+q+b=1; z = the D-vs-R stance gap on this issue (polarization), ψ = share with no established posture (uncertainty) (:94-105).
- Going public always hollows the persuadable middle (Prop 1, tracked as `gridlock_width` :134).
- **Defensive-appeal channel** (Prop 2): on DEFEND issues the campaign raises co-partisan defection thresholds ×(1+DELTA/2) — counted as "fair-weather friends" held against a standardized $250k competitor probe (:135-147).
- Per-member step = regime sign × `VULN(m)·rc(m,'susc_mult')` — electorally vulnerable members "gamble for reelection" ×1.35 (Noble A.4; :55-62,108-120).
- `--advise` ranks all 18 issues GO PUBLIC vs quiet work; Noble's prediction holds by construction: positive on defend issues, weakest/negative on high-polarization offense issues (:218-249). `--intensity auto` scales by measured press frame alignment (:206-217).

### 8.4 The say-do gate (A/V/J corroboration)
Cheap-talk filter, user-ratified 2026-07-07/08 (moneyball_core.py:169-184): a **Champion/Defender** stance cell must be backed by a COSTLY RECORDED action or it displays as **Ally**. Three paths, matching how a category is actually contested: **A** — Authored (sponsored/original-cosponsored an in-category bill; plain cosponsorship does NOT count, :199-202); **V** — a recorded CU-aligned final-passage vote (lean ≥ 0.5, `vote_category_lean.json`, :232-249); **J** — Chair/Ranking of a committee with primary jurisdiction over a GATEKEEP category ({CU Tax Status, Interchange, Credit Card Mandates}, :229-231) — for defend-by-blocking issues, the gavel IS the follow-through. Applied where `category_stance.json` is WRITTEN (per_category_stance.py:144-157), so every consumer inherits it; raw tiers preserved in the artifact's `gate` block. It only ever LOWERS Champion/Defender→Ally (:276-293) and **fails OPEN** — a missing evidence source means no caps, never fail-capped (:221-224). The A/V/J 3-path design is a user-ratified constant (change control applies).

## 9. The multiplex network: layered edges, honestly weighted

`build_multilayer_network.py` writes `congress_cosponsor_network_AUG<date>.xlsx`, picked up by mtime glob by all loaders; REVERT = delete the AUG file (:5-7,108). Layer policy (:9-20):
1. **Cosponsor** edges verbatim, mean-symmetrized (the source has 41 reverse-dup asymmetric pairs).
2. **Engagement** edges (press cross-engagement) only for untied pairs. These arrive as **Fink-normalized empirical probabilities** — influence(i→j) = j's engagements with i ÷ i's output volume (directed, floor 25, pair-mean capped 0.25; `fec/network/social_interaction_layer.py:15-19`, press analog `fec/network/press_engagement_layer.py:6-11`). Converted to kernel units by the **kernel-inverse** `w = 6p/(1−p)` (the inverse of `p=w/(w+6)`), capped ENG_CAP=2.0 ≈ a strong cosponsor tie (:50-61).
3. **HCoI** ("who talks about the same issues") similarity edges ONLY incident to cosponsor-ISOLATED members (leadership doesn't cosponsor by norm — the D4 surgical fix), weight ≤ 0.12; adding all 1,239 would triple density on a similarity signal (:15-19,63-76).
4. **Social**: new edges via the same kernel-inverse (cap 2.0); already-tied pairs get **reinforcement `w *= 1 + SOC_REINF·min(1, p/0.10)`** — default cap **+30%** — a public repost channel on top of cosponsorship means the tie is live, not just on paper (:77-97).
A Provenance sheet records every edge's layer + the policy string (:99-108).

## 10. Pathfinding: RELINK / MOPBD* / D*-Lite / GCOMB

The in-repo paper library is `research/4_Closed_Network_IM_CIKM25_temp.pdf` ("paper 04") and `research/Multi-Objective_Path-Based_D_Lite.pdf` (both git-tracked).

- **`fec/engine/cosponsor_route.py`** (docstring :3-5, "RELINK + MOPBD*" — Ren et al., Multi-Objective Path-Based D* Lite): champions are seeds; each recruiter personally whips ≤ K=5 colleagues (out-degree budget); edge cost `CEDGE/max(0.1,p)` — unlikely recruitments cost more to land (:43); greedy routes at risk-aversion λ ∈ {0, 0.5, 1, 2, 4}, then the **Pareto front** over (money, co-sponsors gained, cascade-failure risk) — the set of routes no other route beats on all three axes (:67-80). `MCMODE=1` swaps optimistic tree-reach for exact MC reach, capturing reinforcement (:28-42). Prints only.
- **Dashboard JS twins** (in `fec/surfaces/templates/make_dashboard_html_00.tpl`; hand-maintained mirror, no audit coverage): the RELINK-style recruitment tree (tpl:398), the "PROVABLY-OPTIMAL recruitment chain" = **max-product path via Dijkstra on −log p** — the single most-reliable chain, and this optimality claim is TRUE as scoped (tpl:458, ratified by lit-audit run-4j); `multiTarget` shared trees (tpl:490); **GCOMB-grounded budget recruitment** (Manchanda et al., NeurIPS'20) = cost-bounded max-coverage greedy with locality pruning, keeping the classic (1−1/e) coverage guarantee (tpl:496-499,502,708); `cascadeProbs` field tinting (tpl:522). The D*-Lite idea ("recompute only what the scenario touches") is cited as the design principle of scenario.py (scenario.py:13).

## 11. Citation honesty — binding rules from the literature audit

The run-4j literature-conformance audit (commit d3bc997, 2026-07-04) checked all 39 papers in the machine corpus against the code. Verdict: **all citations are honest-analogical** — they credit a mechanism's source, they do NOT claim the paper validated this implementation or its constants. Zero formula changes were required; three comment-level over-attributions were fixed. When writing docs, commits, or claims, obey:

1. **Byrne covers N+ and A+ ONLY.** Byrne, Silasi-Mansat & Worthy (PAID 2015) support: Neuroticism degrades decisions under pressure (replicated core) and high Agreeableness adds under social pressure (their Exp-2). The C− and E− dampeners in the susceptibility composite are **our design priors, NOT Byrne findings** — their E effect was null; their lone C signal was weak, unreplicated, opposite-signed (receptivity_layer.py:8-13, with the sensitivity bound cited: 9/9 weight variants keep the top-20, ρ≥.998).
2. **(1−1/e) is scoped.** Allocator: exact on its `INC` grid only in a fixed stance state (G-K bound = diagnostic), and no guarantee claimed once a modeled conversion can change stances (`fec/engine/optimize.py:3-11,36-38`; corrected 2026-09-30). Coalition IC: Bharathi-Kempe-Salek follower-submodular. Competitive LT flip = heuristic with no flip-side marginal audit (scenario.py:8-12; `audit_frontier.py` checks only the coalition/electoral frontier; corrected 2026-09-30). The one "provably optimal" UI claim is the max-product Dijkstra chain — true as scoped (tpl:458).
3. **Chen = UAI 2021**, not ICML (venue corrected twice in run-4j; receptivity_layer.py:28).
4. **Bakker means backfire, clamped at 0** — out-party cues sign ≤ 0; we do not invent a negative magnitude (lt_priming.py:31-39).
5. General rule: calibrate criticism and claims against the ACTUAL code wording — all four run-4j verification agents over-claimed at least once (commit d3bc997 message). Before asserting "the code claims X paper proved Y," open the comment and read it.

House rules for external claims and the validated-claims ledger → `moneyball-docs-and-claims`.

## 12. Worked example: Jared Golden through one engine pass

Values below read from live artifacts **as of 2026-07-09** (they change every refresh — recompute, don't trust). Golden: House (ME), `receipts` $7,943,838, `cu` $10,000, `banks+finserv` $6,500, **retiring=true**, and per-issue tiers mostly `—`/True Neutral/Lean Skeptic (e.g. Mortgage & Housing = True Neutral).

**Step 1 — receptivity record** (`member_receptivity.json`, produced by receptivity_layer.py):
- Behavioral dispositions: cooperation_z −0.081, diligence_z −0.294, dominance_z −0.381, breadth_z +0.41, visibility_z −0.507; reactivity (N-slot) missing → neutral 0 (`n_source:"neutral"`).
- `susc_trait = .40(−0.081) + .30(0) − .20(−0.294) − .10(−0.381) = +0.065`.
- Persona blend: `susc = 0.7(0.065) + 0.3(−0.231) = −0.024` (read: "both-neutral").
- `susc_mult = 1+.18(−0.024) = 0.996`; `edge_mult = 0.997`.
- Retiring → `incent_mult = 0.60` (Fouirnaies-Hall); loss domain → `pt_mult = 1.15`.
- `pressure_mult = clip(0.996·0.60·1.15) = 0.687` — the retirement discount dominates: money pressure lands at ~69% strength.
- `seed_prob = clip(0.60 + .10(−0.081) + .06(0.41) + .04(−0.507)) = 0.596`.

**Step 2 — money response.** A $100k CU donation: `r = 100000/7943838 = 0.0126`; `mag = 18·(0.0126/0.1126) = 2.01`; × 0.687 → **+1.4 lean points**. The same $100k as a competitor threat: × LOSSFRAME 1.10 → **−1.5**. Both are far below DTHRESH=11.25 → no defection risk; Golden absorbs money without moving tiers (exactly the "money is weak" calibration working).

**Step 3 — flip model on Mortgage & Housing** (tier True Neutral → PERS=0.50). `pflip`'s money term: `a_money = 0.35·0.687·(10001)/((10001)+0.10·7943838) ≈ 0.003` — negligible against the `0.65·nA/mAt` peer term, so Golden's winnability is almost entirely his network proximity to the issue's champions. His `tgt` gets PERS 0.50 and `delivery_mult=1.00` (say-do gap −0.99 → no discount: he's a doer, not a talker).

**Step 4 — cascade role.** As a Neutral on most issues he's a potential bystander: drawn anti with prob `6500/400000 ≈ 1.6%` per iteration (tiny). If an engine lobbies him into a coalition, his seed fires with `gate = max(0.15, 0.596·SGATE['True Neutral'=0.90]) = 0.536` — a coin-flip seed, and incoming cascade edges are scaled by his edge_mult 0.997 (≈neutral).

**Net read**: the model prices Golden as nearly money-immune, personality-neutral, a weak but honest network node whose main lever is peers — and every engine reached that conclusion from the same four multipliers plus the stance matrix. That is the whole architecture in one member.

## 13. Modeling gotchas (cross-cutting)

- **Per-topic budgets are NOT additive** — $2M per issue in per_topic_flip/per_topic_coalition are diagnostics; optimize.py's $2.5M is the one real pot.
- **Winnability drops when you win** — flip_value measures the remaining persuadable pool (salience_shock.py:182-184).
- **Frontier display curve is clamped non-decreasing** (dips = MC noise) while the true `cur` drives marginals (budget_frontier.py:103) — never diff the display path.
- **`MC` alias collision** — module in flip-family scripts, int in cascade-family scripts.
- **Neutral fallbacks hide breakage** — a deleted `member_receptivity.json` or `say_do_gap.json` doesn't error; engines silently go legacy (moneyball_core.py:45-51,294-306). Check artifact presence before interpreting a run.
- **One P-matrix build** — every engine builds `P` with `MBC.build_P(adj)` (with edge_mult); the one hand-rolled exception is the off-chain diagnostic `fec/engine/method_audit.py:46` (no cpf, no edge_mult) (Section 2; corrected 2026-09-30; verified against `fec/engine/method_audit.py:46`).
- **`lt_priming.json` is single-topic and always written to the production name** (lt_priming.py:98).
- **`electoral_plays.json`** feeds frontier electoral mode and salience VULN; its regeneration is **user-gated** — never run the fix chain unprompted (session-ratified, 2026-07). The 2026-07-09 staleness flag resolved 2026-07-10: the authorized rebuild was byte-identical (mtime-only flag).
- **JS mirror**: any change to flip_model terms, build_P physics, lt_priming gates/pricing, salience estimation, or engine constants requires a matching `make_dashboard_html_00.tpl` edit; the audit does not check the template (see `moneyball-architecture-contract`).

## Provenance and maintenance

Written 2026-07-09 against the live tree (branch main lineage @88a7048; every file:line above opened and read at that state). All commands below are read-only; run from the repo root: `cd "C:\Users\pgoff\OneDrive\Desktop\Melange Systems"`.

Re-verification one-liners (paste to confirm a volatile fact still holds):

```powershell
# Two physics + kernel formula
Select-String -Path "fec\moneyball_core.py" -Pattern "cpf_diffusion|cpf_pressure|def build_P|def sm64"
# PERS table + PERS_NONE ('Ally parity', open ruling N6 — corrected 2026-09-30) + gate + overall ladder
Select-String -Path "fec\moneyball_core.py" -Pattern "PERS_NONE|SGATE|def overall_tier"
# Say-do gate paths + fail-open + delivery clip
Select-String -Path "fec\moneyball_core.py" -Pattern "GATEKEEP_JURIS|cap_uncorroborated|fail-open|def delivery_mult"
# Receptivity formulas, clips, citations (Byrne scope, F&H, Linde-Vis, Chen UAI)
Select-String -Path "fec\members\receptivity_layer.py" -Pattern "susc_trait=|pressure_mult|seed_prob=clip|UAI 2021|NOT Byrne"
# Flip model constants + Michaelis-Menten + delivery in tgt
Select-String -Path "fec\engine\flip_model.py" -Pattern "WM,WP|def pflip|delivery_mult"
# Optimizer: budget/caps, CELF, G-K bound, conversion cap
Select-String -Path "fec\engine\optimize.py" -Pattern "BUDGET=|PMAX=|CONV_MAXSTEP|dd_bound"
# lt_priming: THETA, Bakker signing, stance gates, LS carve-out
Select-String -Path "fec\engine\lt_priming.py" -Pattern "THETA=|BAKKER_XCUE|BLOCK_OVERALL|Lean Skeptic"
# money_response dials incl. DTHRESH rescale rationale + LOSSFRAME
Select-String -Path "fec\engine\money_response.py" -Pattern "MAXSHIFT|DTHRESH|LOSSFRAME"
# Salience: regime estimation p/q/b, DELTA, vulnerability
Select-String -Path "fec\engine\salience_shock.py" -Pattern "p=\(1-b\)|SAL_DELTA|1.35"
# MC=20 safety + CRN keys
Select-String -Path "fec\engine\mc_stability_check.py" -Pattern "Almazaydeh|MC=100"
Select-String -Path "fec\engine\per_topic_coalition.py" -Pattern "1000003\*SEED|1<<62"
# Guarantee scope: allocator (optimize.py docstring = the authority; corrected 2026-09-30) + flip caveat (Borodin)
Select-String -Path "fec\engine\optimize.py","fec\engine\scenario.py" -Pattern "fixed stance state|conversion_reachable=|Borodin|1-1/e"
# Multiplex layer policy: kernel-inverse + reinforcement cap
Select-String -Path "fec\network\build_multilayer_network.py" -Pattern "6p/\(1-p\)|SOC_REINF"
# Pathfinder claims in the JS mirror
Select-String -Path "fec\surfaces\templates\make_dashboard_html_00.tpl" -Pattern "RELINK|GCOMB|Dijkstra"
# Roster count 533 (audit-enforced) + 18 categories + DEFENSIVE set
Select-String -Path "fec\audit\legacy_workbook_audit.py" -Pattern "533"
Select-String -Path "fec\stance\per_category_stance.py" -Pattern "DEFENSIVE=|CU Tax Status',16"
# Lit-audit provenance (citation-honesty fixes)
git log --oneline -1 d3bc997; git log --oneline -1 0e131c0; git log --oneline -1 2636444
# In-repo paper library
git ls-files research/
```

Volatile facts to re-check on any refresh: the Golden worked-example numbers (Section 12; recompute from `member_receptivity.json` / `congestion.json` / `say_do_gap.json`), the electoral_plays staleness note, and the 100%-overlap MC claim if cascade physics ever change (re-run mc_stability_check via `moneyball-run-and-operate` procedures).
