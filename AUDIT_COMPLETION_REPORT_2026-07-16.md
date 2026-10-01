# Moneyball Audit Completion Report — 2026-07-16

## Outcome

The interrupted Claude audit has been reconstructed, completed, repaired, and verified.

- The original workflow did not fail because of a repository or pipeline exception. The recovered Claude workflow logs show that it stopped at the account token/monthly-spend boundary.
- All 367 tracked files were inventoried. All 360 tracked text/code/data files were read literally (120,763 lines, 6.23 MB) with zero read errors. Both tracked PDFs were fully extracted and visually sampled; both ZIP archives were inventoried.
- The final repaired downstream production chain completed in 13.3 minutes.
- The final fail-closed audit reported `ALL MODULES CLEAN.`
- Kernel tests: 65 passed, 0 failed.
- Full regression suite: 121 passed, 0 failed, 1 intentional skip.
- Dashboard/runtime QA: the shipped JavaScript compiles, the closed-network selector was replayed independently against the published bundle, and the reset contracts are regression-tested. In-app browser control was unavailable for the final follow-up, so no new click-through claim is invented.
- This completion made no paid API or LLM calls.

## Concurrency incident found during completion

Two queued live-root pipelines (`run_pipeline.py --from build_media_blend`) acquired the artifact lock during the first completion pass. The first began while a standalone audit was reading the same production artifacts. That created a mixed-generation view: stance, ranks, workbook, dashboard, and desk were changing at different times, producing apparent cross-artifact failures. A later third live-root run (`--from hearing_stance_stack`) published from source files that did not contain the repaired stance, optimizer, route, or audit logic. It was allowed to finish without interference; the repaired worktree chain was then republished under the exclusive lock.

This was not ignored or worked around. `audit_full.py` now:

- separates the worktree code directory from the live data directory;
- permits the audit stage launched by its own parent pipeline;
- refuses a standalone audit when a foreign live pipeline owns `.pipeline_run.lock`;
- uses a non-shadowed workbook sheet handle for final workbook parity checks.

After the foreign pipeline finished, its rank authority hash was recorded and the repaired worktree chain was rerun from `per_category_stance` through the final audit.

## Rank impact

The first repaired downstream pass was proven rank-neutral relative to the first completed Claude refresh:

- Post-Claude rank hash before repaired chain: `DE2F1B051A28294ED4AB40FCE4FBD9DA553101E9B9BDA6770D4333985FD79068`
- Rank hash after that repaired pass: `DE2F1B051A28294ED4AB40FCE4FBD9DA553101E9B9BDA6770D4333985FD79068`
- Rank delta in that controlled handoff: **0 members**

Later queued media and hearing refreshes changed upstream evidence. The final rank authority is `1F90BA14D452446E18BF3948F0769BED23A23192C03AF6A992AFAA6B3BF3B046`. The repaired chain ran after those refreshes and passed exact pillar/rank parity. Because no controlled hash was captured in the brief gap before the last hearing refresh, this report does not invent a separate numeric attribution for that handoff.

An earlier intermediate comparison found 479 rank changes against the pre-refresh `64B61F22...` baseline. That count predates the final hearing refresh and is retained only as historical context, not presented as the final refresh attribution.

## Applied fixes

### 1. Overall stance ladder and Champion crown

The overall taxonomy had two competing meanings of “Champion”: a high score band and a Legislative+Press tier crown. The requested business rule resolves that conflict completely: Tier 1 is the Champion qualifier.

Implemented one law:

- `Ally` is the highest score-derived overall tier.
- `Champion` is the display crown for every Legislative+Press Tier 1 member. Tier 1 is sufficient even when the underlying score band is Highly Persuadable or an aggregate say-do diagnostic would otherwise cap the base label.
- The score-derived `Ally` floor is 2.85, while the Highly Persuadable floor remains 2.05. This moves near-positive members such as Katie Britt into `Ally` without broadening the Champion crown beyond Tier 1.
- The fixed overall ladder validates its cutoff ordering and fails closed on an invalid `OVERALL_OPPONENT_CUTOFF` override.
- Dashboard, workbook column G, outcome snapshots, and the member desk use the same shared crown function.
- Audit assertions require the Champion set to equal the Tier 1 set exactly, with exact dashboard and workbook parity.

Final Champion roster under the refreshed data:

- Daniel Meuser
- Young Kim
- Bill Hagerty
- Andy Barr
- Roger Williams
- William Timmons
- Brian Fitzpatrick
- Cynthia Lummis
- Tim Scott
- Ritchie Torres
- Zachary Nunn
- French Hill

Final overall distribution across 533 members:

- Champion 12; Ally 162; Highly Persuadable 130; Persuadable 71; Lean Persuadable 52
- True Neutral 49; Lean Skeptic 20; Skeptic 20; Highly Skeptical 3; Opponent 3; no evidence 11

Notable corrected outputs:

- Mike Crapo: Highly Persuadable, Tier 2, not Champion.
- French Hill: Tier 1, therefore Champion despite a Highly Persuadable base score.
- Tim Scott: Tier 1, therefore Champion despite a non-Champion base score.
- Zachary Nunn: Ally + Tier 1 = Champion.
- Katie Britt: raw overall value `2.908443`, base/display `Ally`, Tier 2 rank 35.

### 2. Coalition allocator

`per_topic_coalition.py` evaluated existing Allies as funding candidates even though they were already unconditional coalition seeds. On the prior artifact, 469 of 810 top-45 candidate slots were Allies whose marginal effect was structurally zero.

Fixes:

- Candidate shortlist is neutral members only.
- Reported joint spread uses the members actually funded, not every positive-marginal candidate.

Final production artifact covers 18 topics, 805 funded member-topic slots, and $30.612M of per-topic diagnostic allocation.

### 3. Per-topic flip integrity gate

The per-topic money allocator could fund a member who looked mild on one issue even when the system-level stance was Skeptic, Highly Skeptical, or Opponent.

Fixes:

- Shared system-level stance gate blocks those members from money targeting.
- Budget loop cannot overspend a partial increment.

Final verification: **0 blocked-system members received an allocation**.

### 4. Budget frontier correctness

The electoral frontier removed every funded contest target from the opponent set before knowing whether the target’s activation gate succeeded. A failed activation was therefore counted as a conversion.

Fixes:

- Only successfully activated contest seeds are removed from the opponent set.
- CELF stops when the reevaluated marginal is non-positive.
- `TOPIC` probes receive a scoped output filename and cannot overwrite the full production artifact unless an explicit output path is supplied.
- Output now records `topic` and whether a genuine interior knee was found.

Final results:

- Coalition frontier: 17 issue curves; 16 report an interior knee.
- Electoral frontier: 17 issue curves; 9 report an interior knee.
- Deterministic single-topic repeated-run audit passes.

### 5. Joint optimizer correctness, certificate honesty, and output safety

The optimizer claimed a Golovin–Krause/adaptive certificate even though it recorded no real observations, and a money-triggered modeled conversion could change the objective state. Its knee calculation could also include conversion jumps.

Fixes:

- Real observations and modeled threshold transitions are now separate fields; a deterministic scenario replan is not called an adaptive observed policy.
- The fixed-state objective was traced to its actual structure: it is separable by member, and each legal equal-cost contribution sequence has diminishing returns. The optimizer verifies those marginal sequences before certifying.
- Under those verified fixed-state conditions, highest-next-marginal lazy greedy is the **exact discrete optimum on the configured increment grid**, not merely a 63.2% approximation. Golovin–Krause lazy evaluation/data-dependent bounds remain useful acceleration and diagnostic tools.
- The exact certificate is withheld if a modeled conversion is reachable or if any member violates diminishing returns.
- Knee math uses selected pre-conversion chunk marginals.
- Mode, observations, conversion reachability, concavity verification, certificate scope, grid increment, knee validity, selected marginals, and topic scope are explicit in the JSON.
- `TOPIC` probes cannot clobber the all-topic production output.
- Budget and increment inputs are validated; allocation cannot overspend a partial increment.

Final production result:

- Budget: $2.5M, fully allocated across 381 members; zero members exceed the $10,000 cap.
- Winnability: 100.7405 → 117.1739 (+16.4334 expected weighted flips).
- No conversions occurred and no conversion is reachable under the $10,000 cap.
- Fixed-state exact-grid certificate valid at 117.174; zero concavity violations.
- The separately reported Golovin–Krause diagnostic upper bound is 122.523; it is not mislabeled as the exact bound.
- Interior knee reported at $12,000.

### 6. Shared salience estimator

The dashboard and Python salience-shock engine used different stance-score coverage and different uncertainty handling.

Fixes:

- One `salience_issue_params` implementation in `moneyball_core.py` now serves both producers.
- Fine overall tiers and the True Neutral uncertainty term are handled identically.

Final dashboard exports 18 salience parameter rows for 18 displayed issues.

### 7. Dashboard interaction and scenario math

Fixes:

- Blank canvas click/tap clears the selected member, routes, search fields, and refits the full network.
- “← Targets” performs the same complete reset.
- Head-to-head CU/industry pull and the break-even inverse now include the member pressure multiplier.
- Max-cascade is now an outward, multi-hop closed-network edge-activation route from the selected seed.
- Each newly recruited member exposes the next frontier; every recruiter has a two-ask fan-out limit.
- Edge priority combines route reliability, marginal new coverage, and a weighted PageRank structural prior.
- Max-cascade recruits must be stance-viable and not system-level skeptics/opponents.
- Anti/system-skeptic members cannot be used as max-cascade seeds.
- The route is explicitly labeled a non-submodular heuristic; it makes no false `(1-1/e)` claim.
- Flip route remains inward and target-specific: it ranks colleagues by leverage over one chosen target. Max route has no fixed target and expands the best spread frontier.

The redesign follows the supplied research:

- Arya et al., *RELINK: Edge Activation for Closed Network Influence Maximization via Deep Reinforcement Learning* (CIKM 2025 manuscript): closed-network influence is modeled as sequential edge activation from a fixed seed, with per-node outgoing-edge constraints; its objective is non-submodular.
- Golovin and Krause, *Adaptive Submodularity: Theory and Applications in Active Learning and Stochastic Optimization* (JAIR 2011): adaptive claims require actual observations, while lazy evaluation and data-dependent bounds apply when the required diminishing-return structure exists.
- Almazaydeh et al., *Heuristic centrality methods challenge greedy optimization in influence maximization* (Scientific Reports 2026): PageRank/betweenness can be strong time-efficient structural priors, and theoretical greedy claims require their assumptions to be demonstrated.

Independent route replay on Interchange using John Kennedy produced a four-level, five-recruiter outward tree. Its recruited set had Jaccard overlap `0.091` with Kennedy’s target-specific flip levers, demonstrating that the two buttons now solve materially different problems.

### 8. Network authority and deterministic compact layout

- Dashboard network selection now uses the kernel’s canonical network-file selector.
- `sna_layout.py` uses the same augmented, mean-symmetrized network authority as the engines.
- Node/edge ordering and ties are deterministic.
- Compact layout output uses atomic JSON replacement.

### 9. Test/worktree reliability

- Tests that previously treated the worktree as both code and data now honor `MONEYBALL_ROOT` for live artifacts while loading code from the worktree.
- CSV handles in the stance-stack scripts/tests use context managers, eliminating the observed resource warnings.
- A new 2026-07-16 regression module covers crown law, allocation gates, frontier activation, scoped outputs, optimizer certificates, dashboard reset/cascade behavior, salience authority, network authority, and audit writer safety.

## Claude legislation/media work verified

The Claude commit already contained the legislation-display corrections; they were verified rather than duplicated:

- Bill-status press records are excluded from ordinary press.
- Final direction is used instead of an earlier intermediate direction.
- Subject areas route to canonical categories.
- Original-sponsor/cosponsor duplicates collapse by bill and Congress.
- Exclusion accounting is preserved.

No stance/domain labels owned by the user were silently relabeled.

## Findings intentionally not auto-fixed

These are real issues or architecture debts, but an automatic edit would exceed the safe scope of this audit.

### CU Tax Status is absent from the per-topic workbook block schema

The kernel/category stance supports `CU Tax Status`, but the per-topic diagnostic workbook blocks expose the legacy 18-topic set and the dashboard/frontier expose 17 unique issue curves plus Overall. Adding Tax Status requires a schema/workbook decision about budgets, labels, historical comparability, and whether the dashboard issue count should expand. No category was fabricated or aliased to hide the omission.

### Reference-layer “own words” provenance

`member_reference_layer.py` reads an external `Draft Systems/cu_press_stance_tone.csv` source and is explicitly Fable-valenced. Press headlines/third-party references are not automatically equivalent to a member’s own words. No collector or model call was run. A redesign should define an approved source boundary and a gold-reviewed attribution rule before regeneration.

### `sna_compact.json` remains orphaned

The compact-layout producer is corrected, but the artifact has no confirmed production consumer. It should either be wired to a named consumer or moved to the attic after user confirmation.

### Electoral leverage interpretation

Electoral leverage affects seed selection cost/effectiveness, while the displayed frontier curve remains a co-sponsor-spread curve. That is internally consistent but can be misread as a leverage-adjusted outcome curve. Changing the reported outcome measure is a modeling/product decision, not a safe bug fix.

### Frozen vote-category input

`vote_category_lean.json` remains manually maintained. The final audit says it is currently fresh relative to the newest bill archive, but it still has no normal orchestrator producer. The freshness tripwire remains active.

## Final verification record

- Pipeline: `python fec/run_pipeline.py --from per_category_stance`
- Result: success, 13.3 minutes
- Final fail-closed audit: `ALL MODULES CLEAN.`
- Kernel: 65 passed, 0 failed
- Unit/regression: 121 passed, 0 failed, 1 skipped
- Python compilation: clean for every modified Python file
- `git diff --check`: clean (line-ending warnings only)
- Champion/Tier 1 equality: 12 of 12; dashboard parity 533 of 533; workbook parity 533 of 533
- Dashboard JavaScript: 1 script block, 363,498 characters, compilation clean
- Max-route replay: John Kennedy/Interchange depth 4, 6 edges, 5 distinct recruiters; Jaccard overlap with flip-route top six = 0.091
- Optimizer: exact fixed-state $500-grid certificate, 100% certified gain ratio, zero observations/conversions/concavity violations
- Final rank authority after the queued refreshes and repaired publication: `1F90BA14...`
- User-owned untracked `HANDOFF_LAUNDRY_LIST_2026-07-16.md`: preserved untouched

## Final production hashes

- `ranks_python.json`: `1F90BA14D452446E18BF3948F0769BED23A23192C03AF6A992AFAA6B3BF3B046`
- `category_stance.json`: `0753A17561DD750113FDC946FA7D13071A816C5B5C6E27382DB4C985FA00BBC3`
- `dashboard_data.json`: `AF99CC700AD2D2282F21AAFC4F5B2AE196D6455F772B1BF1BB16E27E4D2336F6`
- `Moneyball Dashboard.html`: `893083D887213AEE78E66A1101D6D72F4ADCAE076A530085B7E0F4115D516FFF`
- `per_topic_coalition.json`: `D9429D9374F6E28BE40E73F7A63472AA773EEF98F4A9EFEEE29ED30029627DAD`
- `budget_frontier.json`: `9C5A102C60F71B58EA678F654EE1ECABCBB10CE1272CE77187C998568AEA1812`
- `optimize_result.json`: `06A9E80751804FB194CFCAB6D0F042D8D817739972BA5F503F115C9B10268D05`
- `per_topic_alloc.json`: `ECF739332B03A20F4551B183DB657AF35053774848FB1F782356DF70CD73E37B`
- `Moneyball Main Version - Blended.xlsx`: `816DB183A8AF7F020788740DA72F0D7AA07BA32D72E1038C3E77F7764F4FA2D5`
