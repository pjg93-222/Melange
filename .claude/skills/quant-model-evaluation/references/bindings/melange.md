# Binding: Melange Systems

> **Load when:** evaluating anything in the Melange Systems repository (the Moneyball engine under `fec/`), the Mentat R pipeline (`C:\Users\pgoff\Mentat`), or the CU-geography lane (`C:\Users\pgoff\Documents\Codex\2026-09-27\we-are-going-to-have-an\outputs\cu-geography`). Load it right after `SKILL.md`; where this file and the general skill differ, this file wins. Its presentation rules add to the general contract; they never remove a general requirement.
> **Status:** the original system map and audit-first list came from the 2026-09-29 census at `25eefa3fc` and the 2026-09-20 artifacts. Updated 2026-09-30 for Paul's F1–F6 rulings, the F1/F4 landing at LIVE `b488a99fe`, the leakage fix at `9a6816a9d`, and the admissions fix at `f94d72e6a`. Updated 2026-10-01 for Paul's rulings after the full-chain retry (brain D-075 to D-081): mixed-direction holds, desk and browser ROI matched to the backend, a qualified publication sign-off, the manifest rebuild, and a single start of the 8841 server (section 2). The 2026-10-01 retry ran all 79 chain steps in the DE-044 shape, with `audit_full` as the halting last step, and F1/F4 passed on its final artifacts; its publication verifier returned INCOMPLETE, which Paul signed off with three named qualifications (D-078). These are code and ruling records. They do not claim that every regenerated artifact passed, and the D-077 ROI change reaches the artifacts only at the next regeneration. Line numbers drift; re-read source before citing them.

## 1. Load order and authority

1. Boot the Project Brain as `CLAUDE.md` instructs (`brainctl.py boot`). Precedence is CONSTRAINTS > DECISIONS > STATE > session judgment, and a contradiction halts work until Paul resolves it.
2. Load `moneyball-change-control`, the repository's constitution. Nothing here overrides it.
3. Load this skill, then this binding.
4. For confirmatory claims, the prereg → battery → one-look discipline in `moneyball-research-methodology` governs. This skill supplies the tests inside it; it never runs an ad hoc look.
5. The default instruction in `CLAUDE.md` is to draft Project Brain updates for Paul to apply. Brain D-006 permits session commits. Paul explicitly authorized applying this lane's brain drafts with "F6. Proceed" on 2026-09-30, replying to "Apply the brain update drafts"; that lane-specific ruling does not rewrite either general instruction. Record whether an update is a draft or applied, and check current IDs before inserting a draft.

## 2. House rules that tighten the general skill

**Gates**
- **Ask first.** Present findings and a proposed plan, then wait for Paul. Read-only investigation, tests and reports need no gate. Editing source, regenerating artifacts, writing the workbook and committing all do. This overrides any auto-mode or "keep going" instruction.
- **Money collection is frozen.** Never change Mentat money-collection or receipt-counting code without Paul's explicit approval of that specific change: `R/collect.R`, `R/schema.R`, `inputs/fec_receipt_rules.json`, `tools/pac_evidence.py`, `tools/cross_reference_engine.py`, the money logic in `app/flow_data.py`, and the METHODOLOGY rules. Findings there are report-only questions, phrased in money terms. A "no" to a removal means leave it.
- **Import is execution.** Nearly every `fec/*.py` writes artifacts at import time. Only `fec/tests/run_tests.py` and `fec/audit/audit_full.py` may be run casually (change-control law 8). Read files; never import Melange modules to inspect them. Check for Paul's live jobs before running anything.
- **Never point an executing script at `fec/` code.** `scripts/mutation_check.py` runs its command dozens of times, which law 8 forbids for anything but the two allowed harnesses. `fec/audit/audit_frontier.py` also reads fixed paths and ignores `{input}`, so every mutant would "survive" and the harness would print a false vacuous-check KILLED. To show a check can fail, copy its predicate into a scratch script that reads `{input}` and imports nothing from `fec/`, then mutate a copy of the raw input. That run is a proposal to Paul.
- **Gates live in LIVE.** The kernel tests and `audit_full.py` count as gates only in the LIVE tree (`C:\Users\pgoff\OneDrive\Desktop\Melange Systems`). A worktree figure is not a gate. Never compare raw sha across the git and worktree boundary, and never EOL-normalize LIVE.
- **Engine re-runs are Paul's call.** Re-running Monte-Carlo sufficiency (`mc_stability_check.py`), spawning engines, or scoring the frozen outcome snapshot are all proposals to Paul first.
- **LLM spend** (change-control law 2): in-product verification and classification steps use Haiku 4.5, and Fable writes only the 533 narratives. Multi-model or paraphrase re-annotation (ML-28, SOC-19) spends money and is a proposal to Paul.
- **Fail-open by design.** The say-do gate fails open by ratified design (change-control law 14). An AUT-07 finding on it is a question, not a defect.

**Paul's domains** (evaluate them; never relabel or remove them)
- **Labels.** Stance and press labels are Paul's; never relabel by model judgment. Paul's own adjudication is the label of record, and machine labels are never gold (`moneyball-validation-and-qa` §2). A single adjudicator, the owner, is the design: report SOC-16, ML-22 and the multi-coder rules of `social-science.md` §2.14-2.15 as a stated limitation, never as a fail. Never propose recruiting raters or reviving the expert panel (change-control law 4; the psychometric grade A− is final).
- **Ratified constants** (sensitivity analysis welcome; proposals to change them are not):
  - `PERSONA_W = 0.30`; `DTHRESH = 11.25`; the no-position persuadability `PERS['—'] = 0.45`.
  - Coalition pricing: SEN_K .35, LOWCONF_K 1.10, EB_K 2.0, W_C = W_X = .5 (ratified 2026-08-03, `fec/lobbying/coalition_pricing.py:75-79`). The chair access cost 1.75 is labelled calibrated, not ratified; confirm its status with Paul before treating it as either.
  - `BP_SRC = cosponsor`, the say-do A/V/J three-path design and the row-535 press tier weights (change-control law 14).
- **Not on main.** The Big-5 60/40 blend (`SUSC_B5_W = 0.60`) was ruled by Paul on 2026-07-31, but commit `6226a1f71` is not an ancestor of HEAD and neither tree's `receptivity_layer.py` contains the dial. Do not assume the engine uses it; treat its landing as an open question.
- **R2 ratified.** Paul ruled "F3. Ratify" on 2026-09-30 for D-051's industry-money imputation rule: the four engines retain `industry_money_missing()`, including verified PAC zeros when receipts are missing. This ruling changes no code. D-051's R1 and R3 are not resolved by it. Pillar weights 45/10/40/5 remain subject to their separate re-ratification question (change-control S-5).
- **Rulings of 2026-10-01** (Paul's recommended options, then "Finish it all"). F1/F4, F2 and R2 stay settled.
  - **Mixed-direction holds (D-075, D-076).** An include whose categories carry both +1 and −1 becomes a hold, not an error: `validate_decision` raises `MixedCategoryDirections`, the key leaves bills, and `sentinel_admissions.load` refuses a generation that still admits one. `refresh_sentinel_admissions.main` runs the same check on each selected key's published decision before `collect()`, so a mixed include is held with no fetch and no model call. A held key still in `bill_catalog` rejoins the oldest-first hold-retry quota; Paul kept the default retry priority. A retry re-asks the classifier on the same evidence, so a later admission can come from re-asking rather than new evidence.
  - **ROI peer maximum (D-077), "Match backend".** `desk_roi` in `make_member_desk.py` and `flipModel` in `make_dashboard_html_00.tpl` divide peer pressure by the real camp maximum, with 1 only when that maximum is 0 (an empty camp), as `flip_model.topic_setup` does (`mAt = max(nA.values()) or 1`). They used to floor it at 1. This is a surface change; it moves no rank.
  - **Qualified publication sign-off (D-078).** `audits/qme_fix_round_20260930/publication_recovery_receipt.py` returns INCOMPLETE for the 2026-10-01 publication. Paul signed it off with three named qualifications: (1) LIVE `congress_bill_refresh_receipt.json` `c0d29f11` reads FAIL, not the interrupted PENDING the verifier requires; (2) the verifier counts the tolerated `build_descriptive_speech` step as a producer failure, and that step's YouTube verification receipt has been stale since 2026-08-31; (3) 10 of the 17 audit names fall outside `fec/audit_failure_gate.py`'s patterns. No receipt is edited and nothing is re-run for it. Cite the result as a qualified sign-off with all three qualifications, never as a verifier PASS.
  - **Manifest rebuild (D-079).** `build_system_manifest.py` and then `audit_full.py`, both in LIVE, to clear the 15 A2/A2b reds that compared disk with the 2026-09-18 inventory. This knowingly rewrites the tracked `data/system/system_manifest.json`. A rebuild re-baselines the inventory; it does not explain the drift, so the 09-18 → 10-01 list stays the record of what changed. Paul also acknowledged two chain-made changes to other lanes' tracked files (D-081): `system_manifest.json` `bcfe7399` → `ae876b86` and `Moneyball_email.zip` `15cc35ef` → `cd210dd6`.
  - **Staffer live server (D-080).** Port 8841 is started once on the new data and checked for an answer. The `MelangeStafferLiveSidecar` scheduled task stays disabled.
- **Looks.** `electoral_plays` is user-gated. The gold-template looks are consumed: never re-run them. Any computation that pairs an instrument (Big-5, receptivity, persona scores, the stance classifier) with a behavioural or outcome criterion is a look fragment: SOC-13, SOC-20, psychometric specification curves and scoring the outcome snapshot are prereg-gated. Criterion-side-only and synthetic checks are allowed.

**Presentation** (Paul's standing rules, added to the general contract)
- Every regression is shown as the real R `summary(lm())` print plus a labelled block: CR1 standard errors, bootstrap p and CI, draws, clusters (CR2 may appear as a secondary row). Use `scripts/regression_report.R`. Before quoting it on house data, reproduce one table of the Mentat sector-growth study with it (a second computation path against the house reference engine).
- Trend over significance: lead with sign, size and consistency; put p and CI on one line after; never write "confirmed". The usefulness test is an out-of-sample backtest against the current seasonal-naive forecast (Paul's rule), reported beside the naive and historical-mean benchmarks the general skill requires. In the sector study, last-year naive (MAE 3.634) beats seasonal naive (7.288), so a seasonal-only test can pass a model that loses to naive.
- Every figure names its window and denominator. A pooled coefficient over party, chamber or sector is quoted with its strata or labelled UNSTRATIFIED. Member-level correlations residualize party and gender (`moneyball-validation-and-qa`).
- Sector-study rulings: prediction markets are never read, and no trend is a finding before the year-fixed-effect and incremental-fit checks.
- Audience rule (CONSTRAINTS): surfaces show rankings and data, with no advisory copy, no pitch framing and no recommendations. Efficiency labels, ROI copy and the salience advisory's "GO PUBLIC" verdicts sit in tension with this; flag, do not fix.

**Claims, evidence and settled results**
- `moneyball-docs-and-claims` owns the validated-claims ledger, forbidden wordings and the honest-analogical citation standard. `influence-modeling-reference` §11 holds binding literature-audit rules (Byrne covers N+ and A+ only; the (1-1/e) guarantee is scoped; Chen = UAI 2021; Bakker backfire clamped at 0).
- Psychometric inputs: the instrument is 3/5 (O/C/E); A is valid but not discriminant; the grade A− is final; never write "5/5". The A-validation search stays open until Paul says stop.
- **Refuted, closed and known-benign items bind** (change-control law 10). Before recording a finding, check the AUDIT_FINDINGS refuted lists, `.claude/commands/fable-audit.md:72-82` and `moneyball-failure-archaeology`. Known-tolerant items include up to 4 same-article train/test collisions and the frontier defend-skew tripwire at 0.92.
- **Collisions with settled house results go to Paul as questions, never as KILLED.** Two are known: MC=20 sufficiency judged by 100% seed overlap (`influence-modeling-reference` §5; the general skill rejects overlap as evidence of sufficiency, and the 2026-07-01 knee still moved between $350k and $550k), and the (1-1/e) scope for follower IC against fixed opponent seeds (`influence-modeling-reference` §6, §11.2).
- Reports follow `moneyball-docs-and-claims` §2.2: a dated, append-only file; severity beside each verdict; the refuted list; known-benign additions; an agent-calibration ledger of overruled verdicts.
- Brain decisions and dead ends that bind any evaluation:
  - D-007: the six-pass findings-examination framework; its SURVIVES / WOUNDED / KILLED / UNVERIFIED-HERE vocabulary is this skill's.
  - D-051: recording what production runs is not ratifying it.
  - D-025 (the staffer model's reversal clause) and CONSTRAINTS: never tune coefficients or thresholds to obtain preferred named people or top lists.
  - DE-012: never validate a self-describing artifact in the tree that produced it.
  - DE-029: census a property instead of sampling it when stored data decides it.
  - DE-037: measure a recommendation's blast radius before putting it to Paul.
  - DE-042: a change graded only by its builder is ungraded.
  - DE-047: restore a rare class's probability from a class-weighted random forest by prior correction (multiply by prevalence, renormalize).
  - CONSTRAINTS: never weaken a test, floor or count; never choose a threshold because it restores or removes a member; never reprice one item at a time.

**Operations**
- Every process emits to the Glass Box (`C:\Users\pgoff\.claude\glassbox\events`). The skill's scripts do this already.
- Model routing: reasoning stays in the session model; code is written by Opus or Fable, never Sonnet or Haiku; Haiku scouts facts only. Reviews are done by the session model, reproducing against the real route.
- Scouts fabricate: brief fully, require a negative control, verify adversarially. Existence claims need a repository-wide grep.

## 3. Tooling on this machine (2026-09-30)

- Python 3.12.10 on PATH: numpy 2.4.6, pandas 3.0.3, scipy 1.18.0, statsmodels 0.14.6, scikit-learn 1.9.0, geopandas 1.1.4, networkx; installed 2026-09-30: linearmodels 7.0, SALib 1.6.0, libpysal 4.15.0, esda 2.10.0, arch 8.0.0 (no existing package changed version). The install also made bs4 and matplotlib importable by the production interpreter.
- R 4.6.0 at `C:\Program Files\R\R-4.6.0\bin\Rscript.exe`, not on PATH: broom, sf, boot, jsonlite, digest, data.table, readxl, testthat; installed 2026-09-30: sandwich 3.1-3, lmtest 0.9-40, strucchange 1.6-0, fixest 0.14.2, sensemakr 0.1.6, rdrobust 4.0.0, Benchmarking 0.33, spdep 1.4-2.
- The Mentat sector-growth study hand-builds CR1 and a wild cluster restricted bootstrap in base R; it is the house reference implementation. Its frozen Python twin matches it to 2.2e-10 (139/139 tests).

## 4. Spending-efficiency system map (census 2026-09-29; re-verify lines)

**Money path.** `fec/collect/refresh_fec_money.py` (OpenFEC; Schedule B types 24K/24Z; memos excluded; current cycle) → `fec/engine/apply_fec_money_refresh.py` (refuses stale or hash-drifted refreshes older than 8 days; replaces 15 money fields in `data/engine/congestion.json`) → the engines. The committee policy (11 CU, 23 bank and 10 finserv PAC IDs) lives in `fec/attic/full_congestion.py`.

**Imputation (R2 ratified by Paul, 2026-09-30).** `industry_money_missing()` in `fec/engine/money_observation.py` decides which members get median-imputed industry money. It runs in `flip_model`, `per_topic_flip`, `budget_frontier` and `salience_shock`, and through them the optimizer, the in-browser engine and the desk ROI. `per_topic_coalition` and the scenario cascade use raw industry money. Receipts still use the older `receipts > 0` test. Ratification does not assert that every engine uses the same imputation rule.

**Kernel.** `fec/engine/flip_model.py`:
- pflip = a/(a+b), with Michaelis-Menten money terms relative to receipts (HALFF = 0.10 of receipts).
- WM/WP = 0.35/0.65 are "calibrated" by citation, not by fit.
- The target value `tgt` is primacy priority × PERS × passage bonus × delivery multiplier.
- `fec/engine/money_response.py`: MAXSHIFT 18, HALF .10, RFLOOR $200k, DTHRESH 11.25 (ratified), LOSSFRAME 1.10, and a 10-rung defection ladder. Its 2026-07-01 comment (`:33-39`) calls Highly Skeptical members "deep but movable" and names Durbin.
- The same curve exists three times: Python, the dashboard JavaScript, and the member-desk ROI port. `build_dashboard_bundle.py` hard-codes the money-response literals (`:628`) and reads WM, WP and HALFF from flip_model (`:624`). The JavaScript parity record is within 0.15% on 18 issues (2026-07-09), but the live self-check tolerates 3%, and the 2026-09-30 dry run measured a 0.99% drift. Until D-077 the desk and the JavaScript divided peer pressure by max(1, camp maximum), and the backend does not. On the 2026-10-01 bundle (`dashboard_data.json` `d03e67e9`), the default CU adjacency (`engine.adj`) has only two camp maxima below 1: Data Privacy & Cybersecurity anti at 0.2431 and TCPA anti at 0.9129. `desk_roi`, the published `refflip` figures and the dashboard's default Credit union view all use that adjacency. On it the old template's worst self-check drift is also 0.99%, on Data Privacy, and it comes from that floor. Running the changed template's JavaScript on the same bundle cuts the Data Privacy drift to 0.03% and the worst issue's drift to 0.23%. The bundle also ships four more adjacencies, which the dashboard's Network toggle swaps in (`setNetConfig` rebuilds `ADJ` from `engine.adj_<config>`), so the rule also changes browser figures, including the what-if panels, in two of those views. `adj_bank_reg` and `adj_crypto` each have 5 anti camp maxima in (0,1). Per-issue browser totals move by up to 1.43% in Bank regulation (Field of Membership 2.6038 → 2.5665) and up to 0.85% in Crypto (Member Business Lending 2.9225 → 2.8976). `adj_holistic` and `adj_holistic_norm` have no camp maximum below 1, so nothing moves in the two All bills views. No self-check badge changes state in any of the five views. In the four non-CU views the self-check still compares the page's total with the CU-network published figure, so it reads failed on 7 (Bank regulation), 18 (Crypto), 15 (All bills) and 18 (All bills · normalized) of the 18 issues, both before and after the change. These were scratch measurements, not a regenerated page.

**Allocators and diagnostics**
- `fec/engine/optimize.py` is the real plan:
  - $2.5M in $500 steps, $10k per member above existing CU money, lazy greedy with a fixed-state certificate. Paul clarified "F2. One PAC's": the pot represents one PAC's budget. The $10k cap is the model's existing cap; this statement is not a fresh legal determination.
  - F1 adopted and landed: `moneyball_core.stance_gate_tiers` and `STANCE_GATE_BLOCKED` supply the same analytic overall-tier gate used by `per_topic_flip`. Skeptic, Highly Skeptical and Opponent members receive no allocation. Their existing modeled flip value remains in the base objective; the fixed-state certificate only covers fundable members.
  - Consumers: the dashboard optimizer panel, desk `opt_alloc` and `gap`, and the efficiency investment score.
- `fec/engine/budget_frontier.py`:
  - Per-topic Independent-Cascade seed frontier; $50k flat per seed; MC 20; SEED 7.
  - The display path is a running max (`:133-138`), and the knee comes from its differences.
  - MC sufficiency was last recorded on 2026-07-01, before later physics changes.
- `fec/engine/per_topic_flip.py`: $2M per topic, $50k per-member cap. It applies the system-level stance gate (`BLOCK_OVERALL`).
- `fec/engine/per_topic_coalition.py`: proportional, not greedy. It uses raw industry money, and the code records an unexplained set-construction sensitivity.
- `fec/engine/build_im_allocation.py` sums the per-topic diagnostics into per-member totals, although per-topic budgets are not additive.
- `lt_priming.py` (money term ignores receptivity), `cosponsor_route.py` (prints only), `scenario.py` (MC 40), `salience_shock.py --advise` ("GO PUBLIC" goes to the top quartile by construction).
- Decision layers that move no rank:
  - `efficiency_layers.py`: contest index, investment score from optimizer shares, quartile labels by construction.
  - `fec/lobbying/coalition_pricing.py`.
  - Desk metrics in `make_member_desk.py` (F4 landed): ROI is expected weighted flips from the next $10k, with the same stance gate and Highly Skeptical in the anti camp; gated members have ROI 0. Its peer maximum matches the backend (D-077). `eff_value` uses tie-aware midrank percentiles. `gap = max(0, opt_alloc)` because the allocation already is an increment; Paul reaffirmed that gap stays equal to Suggested. The dashboard preserves optimizer dollars when encoding thousands (`$500` becomes `0.5`).
- `fec/engine/apply_alloc_cap.py`: a manual Excel water-fill (COM). It is in the danger family; never run it.

**Existing checks.** `run_tests.py` (curve shape, bounds, immunity), `audit_full.py` (money, optimizer, frontier determinism, imputation guard), `audit_frontier.py`. F1/F4 added `test_optimizer_stance_gate`, `test_desk_efficiency_metrics`, and two artifact audit checks. D-077 extended `test_desk_efficiency_metrics` with three fixture checks: desk-vs-`flip_model` parity when every camp maximum is below 1; the review's three-member fixture, which gives 0.021468455244484982 at camp maximum 0.1 and at the maximum-2 control; and the template's own `flipModel`, run in node, against the desk. None establishes outcome calibration. The authorized 2026-09-30 score attempt for `outcome_snapshot_2026-07-04.json` stopped at its minimum-data gate: 88 days, 511 members covered in both panels, 19 positive cosponsorship deltas versus the required 150. Result UNDERPOWERED; H1/H2 correlations were not computed. Paul subsequently chose to refresh the bills archive. A criterion-only pod check using canonical bill IDs, independently repeated from workbook XML, found the same 468 bills in both archives and reproduced all 511 nonmissing frozen counts; an earlier title-based report claiming dropped bills was wrong. The real comparability issue is row multiplicity: 862 removed plain-cosponsor rows retain an original-cosponsor twin, while H2's tier construction also changed after the freeze. The authorized pod refresh completed on 2026-09-30: all 468 frozen bill IDs, 6,284 dated official GovInfo cosponsorship events, zero fetch errors, with source hashes and withdrawal dates retained. Independent XML replay passed. Of the original 511 eligible members, 72 had a new dated event (73 events), below the unchanged 150-member minimum; the current-roster count of 77 is not the original denominator. The candidate archive remains outside production. No predictor/criterion association was computed and the look remains unspent. Durable evidence: `audits/qme_fix_round_20260930/README.md`, its official evidence archive, and `independent_final_receipt.json` (original pod generation: /workspace/f5-check/official-refresh-20260930T214102Z). The pod QME suite passed 175 tests with two skips; this is not a full-chain or parity gate.

**Mentat.**
- The sector money-growth study (R, `code/R`, CR1 plus wild cluster bootstrap, Holm families) is the house reference for regressions and backtests. In its backtest, last-year naive (MAE 3.634) beats every covariate model.
- The in-flight giving forecast is untracked: selection-conditional OLS on n = 18-21, and its stepwise House model loses to its own baseline.
- The PAC cash model pools cash pro rata. That is a stated accounting assumption, and the code is frozen.

**CU geography.** RF/KNN imputation: 81.00% against a 77.89% majority baseline, with 48.3% majority-default fills. Prior correction per DE-047. Never edit the locked stratified code.

## 5. Audit-first list

The census observations of 2026-09-29 are hypotheses. REPRODUCED records refer to the independent 2026-09-30 checks of the pre-fix system. F1/F4 below are historical findings with adopted code fixes, verified on the 2026-10-01 full-chain artifacts. The D-077 ROI change awaits the next regeneration. Everything else re-enters the protocol at phase 3.

1. **Joint optimizer (T1).**
   - F1, REPRODUCED before the fix: the 2026-09-20 plan funded 10 of 20 system-level gated members, $54,500 (2.2% of the pot; Durbin, Opponent, $7,000; three at the $10k cap). `per_topic_alloc.json` funded none. The historical assumption "every allocating engine shares one stance gate" was KILLED (second reader: the dry run).
   - Resolved by Paul: "F1. Yes" adopted the shared gate; "F2. One PAC's" settled the pot's scope. F1/F4 landed as `b488a99fe`. A scratch optimizer run on unchanged inputs funded 0 of 20 gated members, with unchanged base objective and a valid fixed-state certificate; it was not a production regeneration.
   - Verified on the 2026-10-01 full-chain artifacts: 19 members gated and none funded; 380 funded and $2,500,000 of $2,500,000 spent; for all 533 desk rows, gap equals Suggested and every gated member shows ROI 0. Cap/headroom and sensitivity studies remain separate proposals. The authorized outcome score stopped UNDERPOWERED; archive refresh is authorized, but no contaminated or altered-hypothesis look is implied.
2. **Money kernel.** D-077 resolved the peer-maximum disagreement, and fixture parity of the desk, the backend and the template JavaScript is now a kernel test. Still open: a production parity harness across the three implementations on regenerated artifacts (the self-check tolerates 3%); a sensitivity sweep on the decision surface; an outcome-calibration design (prereg-gated).
3. **Money inputs and R2.** R2 is ratified. An imputation census by engine and decision sensitivity to `IMPUTE_IND0` remain separate studies; cycle-to-date zeros may reflect timing rather than true absence. The 2026-09-27 FEC refresh that the original census found unapplied was applied by the 2026-10-01 chain (source `57d8f9c9`, congestion `8e9e29ec`). Under the 8-day rule it goes stale at 2026-10-05T10:29:36Z.
4. **Efficiency surfaces** (historical findings REPRODUCED 2026-09-30; F4 code landed):
   - Before: `gap` subtracted existing money from an incremental allocation; 72 of 389 funded members showed zero or negative gaps. Now `desk_plan_fields` returns the increment and its nonnegative gap; Paul chose to keep gap equal to Suggested.
   - Before: 521 of 533 members shared an invested value, and a row shuffle changed 497 `eff_value`s in the census probe. Now `desk_eff_values` uses tie-aware midrank percentiles.
   - Before: rounding thousands zeroed 47 allocations and changed 14 downstream efficiency labels. Now `opt_alloc_thousands` preserves dollars.
   - Before: ROI was labelled "co-sponsors" and treated Highly Skeptical as neutral. Now the label is weighted flips, the anti camp is `OSK`, and stance-gated members have ROI 0.
   - Before: the desk and the browser floored the peer maximum at 1 and the backend did not (`audits/qme_fix_round_20260930/SYSTEM_LOGIC_REVIEW.md` P2; on the review fixture, 0.1172411240 against 0.0214684552). Now both use the real maximum (D-077). Measured on the 2026-10-01 artifacts before regeneration:
     - 10 desk values change at 4 dp and 18 at any precision; the largest is Danny Davis, 0.0092 → 0.0115.
     - The total changes from 9.859224 to 9.858661.
     - The top 20 and the 19 gated zeros do not change.
   - Quartile labels are forced by construction (134 / 265 / 134).
5. **Frontier and per-topic allocators.**
   - The frontier's monotonicity audit check reads the running-max path, so it cannot fail. That stands on [CODE] (`budget_frontier.py:133-138`; `audit_frontier.py:10-17`); do not run `mutation_check.py` against it (section 2).
   - MC error bars on the knee (engine re-run: Paul's call).
   - `im_allocation` sums non-additive diagnostics ($38.0M FLIP, $32.07M COALITION).
   - The unexplained coalition sensitivity.
6. **Salience advisory.** Its verdicts are structural rather than empirical, and it conflicts with the audience rule.
7. **Mentat.** The giving forecast before it ships; the sector-growth study's 2020 gap; PAC cash attribution (report only).

## 6. Where the existing library already covers a test

Use these instead of re-deriving them:
- **`moneyball-proof-and-analysis-toolkit`:** power studies, plant batteries, split-half reliability, permutation gates, input-purity byte-match, CRN and MC sufficiency, sensitivity bounding, confound partials, stratum diagnostics, adversarial re-derivation.
- **`moneyball-research-methodology`:** prereg, battery, one look, outcome vocabulary.
- **`moneyball-validation-and-qa`:** the evidence ladder, gold-label law, documented thresholds, schema guards, fail-open vs fail-closed.
- **`moneyball-diagnostics-and-tooling`:** the shipped harnesses (`run_tests`, `audit_full`, `audit_frontier`, `mc_stability_check`, `receptivity_sensitivity`, `kb_benchmark`, `outcome_snapshot`).
- **Brain procedures:** `examine-a-findings-document`, `verify-a-rank-moving-change`.

Several of these skills carry stale engine facts. Verify against code before citing them:
- inline P kernels (they now call `MBC.build_P`);
- the tgt formula;
- PERS "Highly Persuadable" .55 in the skill vs .65 in code;
- the `paths.py` worktree claim;
- frontier artifact paths;
- `influence-modeling-reference` §6: conversions keep (1-1/e), although `optimize.py` now refuses the certificate when a conversion is reachable;
- §8.2: "median-imputed everywhere", although `per_topic_coalition` and the scenario cascade use raw industry money.
