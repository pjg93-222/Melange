# Legislative effectiveness shadow: validation and completion record

Date: 2026-09-11. Frozen vintage: this file records what was built, what was measured, and what was verified on this date. Later corrections belong in the living plane (brain, commands, skills), not here.

Scope: the Codex implementation of `research/LEGISLATIVE_IMPACT_EFFECTIVENESS_IMPLEMENTATION_PLAN_2026-09-10.md` (Bucchianeri/Volden/Wiseman five-stage results score, C=1 / S=5 / SS=10 impact weights, half-life-discounted later cosponsorship, sentiment-free CU/trade-publication frequency as sector significance), executed as a SHADOW comparison. Nothing in this lane is applied to the live tree, and no production artifact changed.

## 1. Provenance

| Item | Fact |
|---|---|
| Commissioning session | Codex Desktop, thread `01a08e6b-37c5-7521-87c2-9a7ba98659d4`, cwd = live tree, 2026-09-10 23:03 ET. Paul's task: review the paper, draft the plan; follow-up: "Can we infer from the number of co-sponsors and amendments to the bill its significance? What about trade associations? ... the later a member of congress co-sponsored ... the less it should count ... focus on the NUMBER of times a bill is mentioned not the language"; then: "Start a new session, and execute the implementation plan, then show me the diff". |
| Implementation session | Codex thread `01a08e94-fe66-72b0-96f0-5c1c32a1c989`, worktree `C:\Users\pgoff\.codex\worktrees\f149\Melange Systems`, created from live main `2f11d9490`. Baseline-carryover commit `d68ddcda6` ("Record live legislative baseline separately from effectiveness implementation", 20 files, +1,678/-175) so the live tree's uncommitted legislative state is not presented as new work. Three sub-agents (official_evidence, scoring_engine, integrations). |
| How it ended | `usage_limit_exceeded` on the coordinator and all three sub-agents at 2026-09-11 04:06-04:07Z ("try again at Sep 17th, 2026 1:16 PM"). The `integrations` sub-agent produced nothing; the coordinator wrote the integrations itself. Its last message (04:06:33Z): "I'm freezing the code, repeating the scores for reproducibility, and finishing the validation report and diff." The `--verify-reproducible` re-run it had launched COMPLETED on disk at 04:09:09Z, after the error, unread by any model turn. The validation report and the diff presentation were never produced. Evidence: `C:\Users\pgoff\.codex\sessions\2026\09\10\rollout-2026-09-10T23-48-44-*.jsonl`. |
| This record | Claude session 2026-09-11 (worktree graph-consolidation-identity-d8d358, branch claude/work-in-progress-completion-1d24a7): read-only verification of the f149 state, independent reproduction into the session scratchpad, this record, and the review packet beside it. |

## 2. What was built (state of f149 on 2026-09-11)

Tracked files modified on top of `d68ddcda6` (11 files, +193/-18; full text in `IMPLEMENTATION_DIFF_2026-09-11.patch` beside this file):

| File | Change | Default-path effect |
|---|---|---|
| `fec/engine/compute_pillars.py` | `--effectiveness-shadow` early exit to `reporting_shadow_cli`; Leg% now `legislative_percentiles(O, mode='legacy')` | Value-identical to `percentrank` on all 533 members (section 5) |
| `fec/engine/live_legislative_pillar.py` | new `from_effectiveness(comparison, mode)` | Unused unless called |
| `fec/engine/primacy_factors.py` | `with_realized_results()`; sidecar output only when `EFFECTIVENESS_COMPARISON_PATH` is set, and then requires `PRIMACY_SHADOW_OUT` | Production `data/engine/primacy_factors.json` path unchanged |
| `fec/lobbying/industry_tiers.py` | `realized_results_v1` board branch in `_canonical_cu_board`; output path guard when that mode is active | Default `factor` mode unchanged |
| `fec/moneyball_core.py` | `primacy_engine_state` accepts keyword-only candidate args; cache key extended only when they are passed | Legacy call shape unchanged |
| `fec/run_pipeline.py` | `--effectiveness-shadow` routes to `legislation.run_effectiveness_shadow.main` before argparse | No chain step added |
| `fec/surfaces/build_dashboard_bundle.py`, `fec/surfaces/make_member_desk.py` | `optional_shadow_explanations(bundle, out)` before the atomic dump | Returns the bundle object unchanged when `EFFECTIVENESS_COMPARISON_PATH` is unset |
| `fec/surfaces/templates/make_dashboard_html_00.tpl`, `make_member_desk_00.tpl` | render `effectiveness_shadow_html` when present | Empty string when absent |
| `fec/tier_util.py` | `PRIMACY_BOARD_MODES += realized_results_v1`; `legislative_press_tiers(mode=...)`; new `realized_results_tiers()` | `factor`/`legxfactor` paths unchanged |

New modules (untracked in f149): `fec/engine/legislative_effectiveness.py` (509 lines, pure scoring), `fec/engine/effectiveness_integration.py` (325), `fec/engine/replay_effectiveness_allocations.py` (191), `fec/legislation/build_bill_milestones.py` (441), `fec/legislation/build_bill_impact.py` (245), `fec/legislation/effectiveness_sources.py`, `fec/legislation/run_effectiveness_shadow.py`, `fec/legislation/audit_bill_milestone_samples.py`, `fec/legislation/verify_effectiveness_shadow.py`. Carried from the live tree in the baseline commit and hashed into the code freeze: `fec/engine/pillar_policy.py`, `fec/engine/live_legislative_pillar.py`, `fec/bill_rules.py`, `fec/legislation_measure_key.py`.

New unittest suites (6 files, 77 tests, all passing 2026-09-11 on this box with both `python -m unittest` and pytest 9.1.1): `fec/tests/engine/test_effectiveness_integration.py` (13), `fec/tests/engine/test_legislative_effectiveness.py` (24), `fec/tests/legislation/test_bill_impact.py` (12), `fec/tests/legislation/test_effectiveness_sources.py` (5), `fec/tests/legislation/test_verify_effectiveness_shadow.py` (6), `fec/tests/test_bill_milestones.py` (17). They are NOT registered in `fec/tests/run_tests.py` `_LANE_MODULES` (Codex: "Runner unchanged"); see section 7.

Shadow outputs: `f149\outputs\legislative_effectiveness_shadow\` (51 files, 886,718,559 bytes; receipt `shadow_generation.json`, status `complete`, `production_activation: false`). Inputs are read from the LIVE tree (`--source-root`) and the official BILLSTATUS zips under `%LOCALAPPDATA%\Melange\lda_rebuild\raw\billstatus118|119`; the runner refuses an output root inside the source tree and re-hashes all inputs, the six production artifacts and the 14 code files after the run (a drift raises).

## 3. What the shadow measured (as-of 2026-09-06, half-life 180 days = illustrative, not adopted)

Universe and denominators (source: `118/shadow_summary.json`, `119/shadow_summary.json`; eligible types hr, s, hjres, sjres; constitutional-amendment joint resolutions and non-law measure types excluded):

| Term | Eligible measures | N (distinct bioguide, incl. replacements) | Weighted denominators BILL / AIC / ABC / PASS / LAW | Stage counts BILL / AIC / ABC / PASS / LAW |
|---|---|---|---|---|
| 118 House | 10,740 of 12,556 archive records | 451 | 53,260 / 6,892 / 5,460 / 3,129 / 679 | 10,740 / 1,432 / 1,144 / 677 / 183 |
| 118 Senate | 5,755 of 6,759 | 105 | 28,611 / 3,420 / 3,501 / 1,345 / 415 | 5,755 / 700 / 717 / 285 / 91 |
| 119 House (provisional) | 10,455 of 12,140 | 449 | 51,899 / 6,728 / 4,866 / 3,346 / 325 (`denominators_available: false`: 5 reserved-number records have no action history) | 10,455 / 1,380 / 994 / 690 / 65 |
| 119 Senate (provisional) | 5,567 of 6,467 | 104 | 27,735 / 3,414 / 2,847 / 991 / 196 | 5,567 / 698 / 571 / 199 / 40 |

Sponsor-reference means (the paper's average-of-one property, not expected exactly because 8 AIC credits per 118th chamber and 6 in the 119th Senate precede introduction and are withheld): 118 House 0.9988, 118 Senate 0.9977, 119 House 1.0000, 119 Senate 0.9982.

Impact classes: 118th, C 151 / S 16,344 of 16,495 eligible; 119th, C 119 / S 15,903. SS was assigned to NO bill: `SS_thresholds: not_adopted; no calibration from incomplete member feed`. Publication evidence: 1,301 deduplicated publications from 3,855 member-excerpt fragment rows; 3 distinct verified bill links (118th) and 13 (119th); `complete_panel_inventory: false`. The plan's frequency threshold (5 to 10) therefore remains uncalibrated, as the plan itself anticipated.

Accepted CU signals joined to the official universe: 118th 2,978 signals over 165 unique measures (excluded: 20 letters with unverified signature date/document, 13 measures not in the official universe, 2 missing tensor tag); 119th 2,502 signals over 132 measures (259 letters unverified). Scope caveat carried verbatim from the receipts: "current accepted CU selection; historical nonselected members have unknown CU coverage".

Enactment cross-check (`outputs/legislative_effectiveness_validation/official_enactment_coverage_review.json`): all 274 recorded 118th laws (183 House, 91 Senate) and all 105 recorded 119th laws (65, 40) map to LAW milestones, zero discrepancies. Milestone sample review: 16 records, 80 stage checks, all agree; this is developer review, not independent human validation.

Member comparison (`118/data/engine/legislative_effectiveness_comparison_v1.json`, 533 member rows): 352 of 533 members receive results-only and advocacy-composite Leg%; 351 receive tensor results; 80 are `member_term: not_covered`. Spearman rank correlation between the legacy Leg% and the results-only Leg% is 0.498 (n = 352); legacy vs the 70/30 advocacy composite 0.719. 119th (n = 83): 0.619 and 0.750. Largest 118th moves legacy to results-only: up, Fetterman 0.0 to 0.7, Reed 0.5 to 1.0, Burlison 0.1 to 0.6; down, Case 0.9 to 0.0, Salazar 0.8 to 0.0, Gallego 0.9 to 0.1.

Board comparison (`118/data/engine/board_priority_comparison_v1.json`, board mode `realized_results_v1`, gate `distinct_signed_measures_v1` minimum 1): 131 of 533 members change tier, 131 change priority, 182 have no results or fail the gate. Cross-tab legacy tier (rows) vs results tier (columns), tiers 0/1/2/3: row 0 = 391 / 6 / 14 / 37; row 1 = 9 / 0 / 4 / 0; row 2 = 16 / 2 / 3 / 3; row 3 = 32 / 5 / 3 / 8. All 13 legacy Tier-1 seats change hands (9 unseated, 4 to Tier 2); 57 legacy-seated members are unseated and 57 previously unseated members take seats.

Allocation replay (`118/allocations/*_dollar_comparison.json`, current network, frozen non-legislative inputs, only the tier/priority authority substituted; MC = 20, seed 7, NET_CONFIG = cu): FLIP, 19 of 19 topics change, member-topic absolute dollar movement $40,326,000 against a $38,000,000 topic budget sum (19 x $2,000,000, unchanged), 412 members' aggregate totals move; coalition, 19 of 19 topics, $34,408,000 absolute movement, budget sums $32,080,000 baseline vs $32,386,000 candidate, 239 members move. These are diagnostic per-topic replays; the receipts say the totals are not one deployable joint budget.

Half-life sensitivity: `118/data/engine/half_life_sensitivity.json` (1.2 MB) carries the per-half-life rows; not summarized here.

## 4. Independent verification performed 2026-09-11

All checks ran read-only against f149 and the live tree, writing only into the session scratchpad; no git command was used for any of them.

| Check | Result | Evidence |
|---|---|---|
| Input freshness before re-run | 20 of 20 `inputs_sha256` paths match the receipt | `scratchpad\repro\FRESHNESS_CHECK.txt` |
| Code freeze | 14 of 14 `code_sha256` paths match | same |
| Independent re-run, fresh `--output-root`, same arguments | exit 0; 46 of 50 receipt outputs byte-identical; the 4 differing files are `allocations\*\stdout.log` (timestamps only) | `scratchpad\repro\full_50_comparison.md`, `run_stdout.log` |
| Allocation replays (4 variants, run separately as Codex did) | 10 of 10 artifact JSONs byte-identical to Codex's; 4 stderr logs identical (empty) | `scratchpad\repro\ALLOCATION_VERIFICATION.txt` |
| Codex's audit script on both generations | `verify_effectiveness_shadow.py` exit 0 for Codex's generation and for the reproduction | `scratchpad\repro\audit_codex.log`, `audit_repro.log` |
| Baseline replay equals production | `per_topic_alloc.json` (72,378 B) and `per_topic_coalition.json` (20,434 B) byte-identical between the live tree and the baseline replay | `scratchpad\flipcheck\FLIP_BASELINE_CHECK.md` |
| Live tree untouched by any run | 4 of 4 production artifacts in the live tree unchanged before/after; f149's own receipts unchanged | `scratchpad\repro\integrity_check.json` |
| Live tree drift since the baseline | all 21 baseline files normalized-equal to the live tree (CRLF/LF normalized); none of the 15 new files exists in the live tree | `scratchpad\drift_check.md` |
| New suites | 6 suites, 77 tests, 0 failures (unittest and pytest) | `scratchpad\f149_tests\`, `scratchpad\codex_dispatch\*.log` |
| Baseline suites in the worktree | `test_dashboard_adjustments` 11 passed; `test_primacy_tier` 80 passed, 3 failed on missing gitignored data files (worktree data-plane absence, not a defect) | `scratchpad\f149_tests\VERIFICATION_REPORT.txt` |

Worktree figures are not gate figures: the kernel gate and `audit_full` are live-tree only (CONSTRAINTS). They were not run here.

## 5. Production neutrality

- Leg% refactor: `percentrank(Ov, O[m])` and `legislative_percentiles(O, mode='legacy')[m]` agree with exact float equality for 533 of 533 members on the live `data/engine/live_legislative_pillar.json` inputs, and both equal the live `ranks_python.json` `pcts[m]['leg']` for 533 of 533. Evidence: `scratchpad\parity\parity_output.txt`.
- `optional_shadow_explanations` returns the same bundle object and creates no file when `EFFECTIVENESS_COMPARISON_PATH` is unset (unit check, same evidence file).
- `moneyball_core.primacy_engine_state` with no keyword arguments keeps the old cache key and the old `legislative_press_tiers(list(roster))` call.
- `run_pipeline.py` gains no chain step; the shadow runs only when `--effectiveness-shadow` is the first argument.
- The shadow runner set `production_hashes_unchanged: true` only after re-hashing the six production artifacts and raising on any change; this session re-hashed them again after its own runs (unchanged).

## 6. Limitations to carry (verbatim from the receipts where quoted)

1. "Official snapshot completeness is local, not recertified against current remote sources."
2. "C/S automated content coding is provisional; full operative text and independent adjudication are incomplete." The classifier is a title/summary regex; 7,248 of the 118th eligible measures and 13,043 of the 119th have no as-of summary (`coverage_exceptions.no_as_of_summary`).
3. SS never fires: the member-excerpt press feed cannot establish zero coverage or a calibrated threshold; 3 verified bill links out of 1,301 deduplicated publications (118th).
4. "Current selected CU membership/annotations do not cover all historical legislators; absence is unknown." 80 of 533 members are not covered in the 118th comparison.
5. 119th House denominators are unavailable (5 records without action histories); the 119th is a current-term provisional view.
6. Undated or undocumented congressional letters (20 in the 118th, 259 in the 119th) are held out of attributable advocacy.
7. Committee and leadership intervals are not reconciled; institutional context is descriptive only.
8. The milestone-mapping sample (16 records, 80 checks) is developer review; the plan calls for independently adjudicated hand-coding before release thresholds.
9. Allocation replays are a current-network sensitivity experiment, not a historical allocation reconstruction.
10. Mention-frequency significance is adjacent to DE-001 (never price CU relevance from mention density). The implemented signal counts distinct publications mentioning a bill as a significance proxy, not term occurrences inside bill text, and it never enters CU relevance; keep that boundary explicit if SS is ever calibrated.

## 7. What is not done

| Item | Status | Owner |
|---|---|---|
| Register the six suites in `fec/tests/run_tests.py` | Contract prepared and validated (`scratchpad\codex_dispatch\contract.json`), ledger dispatch recorded (run-id legeff-runtests-20260911). The MCP Codex route is blocked by the health check on this box ("stdin is not a terminal"; config.toml now pins gpt-6-astra / ultra) and the Codex account quota is exhausted until 2026-09-17 13:16. A single headless `codex exec` attempt was made; see the packet README for its outcome. Claude does not author code (rule of 2026-07-24). | Codex, after quota resets |
| Kernel gate and `audit_full` with the change applied | Not measurable in a worktree | Paul, live tree, after apply |
| Apply the diff to the live tree | Not done; APPLY-class and rank-adjacent | Paul's gate |
| Decisions before activation (plan section 8): headline basis results-only vs 70/30 composite; tensor board mode; role weights and half-life H; SS panel and 5-to-10 threshold; cosponsor/amendment counts; letters; institutional power; scope | Open; the shadow now provides the comparison the plan asked for | Paul |
| Independent human adjudication of milestone mapping and C/S coding | Not done | Paul or a delegate |
| Brain entries (STATE, optional DEADENDS trap) | Drafted in `BRAIN_UPDATE_DRAFT_2026-09-11.md` | Paul applies |

## 8. How to apply and how to revert (for Paul's gate)

Apply: copy the 11 modified tracked files and the 15 new source/test files from f149 into the live tree (the packet's `NEW_FILES_MANIFEST.txt` lists every path with sha256); the live tree is currently identical to the baseline for all 11 files, so the diff applies cleanly. Then in the LIVE tree: `python fec/tests/run_tests.py` (expect the standing `test_primacy_tier` frozen-board pin plus, once registered, six new green suites), `python fec/audit/audit_full.py`, and `compute_pillars --write` should rewrite `ranks_python.json` byte-identical (0 of 533 moved) since the legacy percentile path is value-identical.

Run the shadow (read-only on the live tree): `python fec\run_pipeline.py --effectiveness-shadow --source-root <live tree> --archive-root %LOCALAPPDATA%\Melange\lda_rebuild\raw --draft-root "<Draft Systems>" --output-root <a directory outside both trees> --service-reference <congress-legislators snapshot dir> --congress 118 119 --as-of 2026-09-06 --half-life 180 --verify-reproducible`, then `python fec\legislation\verify_effectiveness_shadow.py <output-root>`.

Candidate consumers are opt-in only: `EFFECTIVENESS_COMPARISON_PATH` + `EFFECTIVENESS_SHADOW_ROOT` (explanations, sidecar factors with `PRIMACY_SHADOW_OUT`), `PRIMACY_BOARD=realized_results_v1` (board), `compute_pillars.py --effectiveness-shadow --mode results_only_v1|advocacy_composite_v1 --output <inside shadow root>` (reporting ranks). Revert: unset those variables; or restore the 11 files from `f149\outputs\legislative_effectiveness_baseline\` (normalized-identical to the live tree today).

## 9. Evidence index

- f149 receipts: `outputs\legislative_effectiveness_shadow\shadow_generation.json`, `118\shadow_summary.json`, `119\shadow_summary.json`, `118\allocations\*\receipt.json`, `outputs\legislative_effectiveness_validation\*.json`
- Codex transcripts: `C:\Users\pgoff\.codex\sessions\2026\09\10\rollout-2026-09-10T23-03-08-*.jsonl` (commissioning), `rollout-2026-09-10T23-48-44-*.jsonl` (implementation coordinator), the three `23-50-*` sub-agents, `23-51-41-*` (guardian review of the baseline commit)
- Session scratchpad (`C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-graph-consolidation-identity-d8d358\9fc471fa-1635-4e3c-a015-49ba06ce36d3\scratchpad\`): `repro\`, `parity\`, `flipcheck\`, `drift_check.md`, `f149_tests\`, `f149_snapshot_pre\` (108-file pre-touch snapshot with sha256 manifest), `codex_sessions_report.md`, `headline\`
