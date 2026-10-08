# Cosponsorship forecast: model family, frozen state, timed dry run, and coupling design

Date: 2026-09-04. Lane: `claude/bill-lobbying-regression-d38c1e` (worktree `employment-tenure-adjudication-e27de8`, zero commits vs main `8953e7181`). Nothing in production was changed. All measurement and the dry run wrote only to the session scratch directory; evidence paths are listed in section 9.

Paul's request: (1) make "the current linear regression regarding the likelihood of getting onto a new bill based on their lobbying" self-updating in accordance with the Excel sheet (ruled: Sentinel Bill Ledger and the Blended workbook) and the sentinel collectors; (2) would a logistic regression be a better measure given the binary outcome; (3) "do the timed dry run"; (4) option C, the ledger/workbook coupling.

## 1. Answer on logistic vs linear

The model is already logistic. `fec/lobbying/cosponsor_forecast.py` fits ridge logistic regression by iteratively reweighted least squares, with the ridge penalty pinned at 1.0 by an explicit raise (`:1676`), isotonic calibration fitted on the 117->118 split, and ranking metrics (AUC, average precision, Brier, precision at k). The unit is (bill, member); every same-chamber member who did not join is a real zero. Base rate is 6.5%. On the primary split (train 118, test 119) the model's average precision is 0.236 against 0.176 for the best simple baseline (sponsor affinity).

There is no linear regression on sign-on anywhere in the repo. The only linear fit in the lobbying family is the FEC x LDA bridge look (`fec_lda_bridge2_look.py`), a different question whose predictor language is barred by its prereg. A linear probability model would be strictly worse here: at a 6.5% base rate it emits negative and above-one "probabilities" and ranks worse.

One upgrade genuinely suited to "new bill" use is a discrete-time hazard on days since introduction, which lets a bill's sign-on probability age as it sits. That is a model change and would need its own prereg. It is not proposed here.

## 2. What the model does and does not use

Lobbying is not a predictor. It only selects the bill universe: a 119th bill enters when a pinned finance organization named it on the strict LD-2 channel (13 of the 790 modeled 119th bills) or when BILLSTATUS records an introduction-date referral to House Financial Services, Senate Banking, House Agriculture, or Senate Agriculture (785 bills). The report states this itself: `cosponsorship_is_lobbying_substrate_not_lobbying: true`. Predictors are prior-Congress sponsor affinity and cosponsorship propensity, prior network degree and eigenvector, NOMINATE positions and distances, party/state/chamber matches, seniority, committee referral count, majority-party sponsor, bill type, and policy area. The 2026-08-19 finding that a member-level "lobbied" variable is an identity with "joined" applies to any such feature; this model has none.

The trait-features route into this forecaster was retired without a look on 2026-08-17 (`audits/FORECAST_COLLINEARITY_2026-08-17.md:115`). The core forecaster is not retired; `forecast_ledger.py` freezes `cosponsor_join` predictions from it.

## 3. Frozen state

- BILLSTATUS bulk zips under `%LOCALAPPDATA%\Melange\lda_rebuild\raw\billstatus119` are a one-time pull dated 2026-08-01 (8 zips, about 49 MB, no receipt beside them). The producer `fec/legislation/run_billstatus_bulk_enrichment.py` is manual and nothing schedules it.
- LDA rebuild receipts are dated 2026-08-02, committee snapshots 2026-08-01. Both manual.
- The forecaster last ran 2026-08-14 01:05. It is not in `run_pipeline.py`. The chain step `bill_lobbying_sidecar.py` (`run_pipeline.py:176`) re-reads the frozen scores every run, so the lobby-network surface's "Chance they sign on" has not moved since the 08-01 snapshot. Bills introduced after that have no forecast; joins after that still read `actual = 0`.
- Weekly step 3 (`update_bill_repository.py`) refreshes `bill_repository_live.json` (464 official bills) from per-bill GovInfo XML. It does not touch the bulk zips. The press, hearing, and interview sentinels never touch bills.
- Both schedulers are Disabled (production hold). Nothing self-updates until that changes.

## 4. Timed dry run (done, scratch only)

Command: `python fec/lobbying/cosponsor_forecast.py --same-chamber-only --out-dir <scratch>\cosponsor_dryrun`, run from the worktree with production inputs read only. Write surface was verified before launch: the script writes only under its out-dir (final files plus its own temp spools) and makes no network calls.

| Measure | Value |
|---|---|
| Wall clock | 16.1 minutes (18:00:14Z to 18:16:20Z) |
| Peak resident memory | 1.06 GB |
| Exit code | 0 |
| `cosponsor_scores.csv` vs production | byte-identical (sha256 `f87df8ab...`, 164,733,852 bytes) |
| `cosponsor_forecast_report.json` vs production | 52 differences, all in `provenance`: two new fields per archive (`observed_congress`, `vintage_witness`) that today's code emits and the 08-14 code did not. Every model number is identical. |
| `provenance.every_input_sha256` | identical to production |
| Leftover files in out-dir | none |

Reading: the run is deterministic on unchanged inputs and the report already pins every input hash. A chain step can therefore skip the 16-minute run whenever the current input hashes equal the last report's, and re-run only when an input moved. Nothing about the retrain needs to be cached separately, because training on 117/118 is frozen and re-derives byte-identically.

## 5. Coupling measurements (read only)

Sources: `Sentinel Bill Ledger.xlsx` (18,803 rows: 464 `bill`, 18,118 `discovery candidate`, 221 `membership`; 201 rows Scoring Eligible), `bill_repository_live.json` (464 bills, updated 2026-09-02), the production scores and report, and the 08-01 BILLSTATUS-119 zips.

Bill universes overlap partially, not by containment:

| Congress | Repository bills | Forecaster modeled bills | Overlap |
|---|---|---|---|
| 119 | 142 | 790 | 57 |
| 118 | 169 | 1,113 | 59 |

Of the 85 repository 119th bills outside the modeled set, 74 have fewer than 5 cosponsors (26 have zero) and would be excluded by `--min-cosponsors 5` on that alone; 11 have 5 or more. The ledger's 119th discovery pool is 4,118 distinct bills, of which 294 are in the modeled set.

Verified joins versus the forecaster (Congress 119, 188 Scoring Eligible pairs): 178 are present in the same-chamber candidate pool for their bill. 166 already carry `actual = 1`; 12 carry `actual = 0` and are joins dated 2026-08-03 to 2026-08-27, after the snapshot. Rank of the verified joiner among their bill's candidates: minimum 2, median 122, maximum 413 (pools up to 436). Five of 188 land in the sidecar's top-8 cutoff, 17 in the top 25, 40 in the top 50. This is the forecaster's real performance on the CU-adjudicated joins and should weigh on how much to invest in option C.

Repository roster completeness (corrected measurement): the repository splits each roster into `original_cosponsors` and `cosponsors`. Taking the union minus withdrawn entries, the repository roster equals the 08-01 BILLSTATUS roster exactly on 126 of 132 hr/s bills and exceeds it on 6 bills by 19 joins, all dated after 08-01. Zero bioguides are missing from the repository. A first pass had reported 806 gaps; that number was an artifact of comparing only the later-joiner list and of an XPath that swept amendment-level cosponsor blocks into the bill count (H.R.1 has 99 amendments and zero bill-level cosponsors). The repository is a complete, weekly-refreshed roster source for its 464 bills.

Frozen-label gaps on the 57 overlap bills: 35 repository joins are not counted in the frozen `actual`. The 15 post-08-01 joins are the freshness gap. The 20 pre-08-01 joins are all members absent from `fec/legislators.csv`, which the forecaster uses to exclude departed members from the 119th candidate universe (`cosponsor_forecast.py:1138-1144`). That is policy, not a defect, but it means departed members' joins never count as positives in the live Congress.

The repository carries no committee or referral data at any nesting depth. Its `areas` field is the CU category taxonomy (58 distinct values), separate from `policy_area`.

## 6. Design

A. Weekly BILLSTATUS-119 bulk re-pull. A thin wrapper around the existing GovInfo fetcher writes the 8 zips atomically into `raw\billstatus119` with a sha256 receipt beside them. Sits in `weekly_refresh.py` next to step 3 with `hard=False`, since a failed pull leaves last week's zips in place. Network step, so it belongs in the weekly job, not the chain.

B. Forecaster as a chain step in `run_pipeline.py`, placed before `bill_lobbying_sidecar.py`. The step computes the current input hashes, compares them with `provenance.every_input_sha256` in the existing report, and skips when equal. When they differ it runs the 16-minute job into a staging directory and promotes both files atomically, then the sidecar and the lobby-network surface pick up fresh scores on the same chain run. Add an `audit_full` check (`cosponsor_forecast_freshness`) that fails when the report's input hashes no longer match the inputs on disk, so a silent skip cannot hide. The chain stays network-free.

C-ledger (Sentinel Bill Ledger). Three separable pieces, in order of value:
1. Outcome feed. Use the repository's union roster to update `actual` weekly for the 57 overlap bills and any future ones, closing the 12-join gap above without waiting on the bulk zips.
2. Live scoring universe. Score all 142 repository 119th bills with the frozen 118-trained coefficients as a display-only universe with no cosponsor floor, kept strictly separate from the evaluated panel so the AP claims are untouched. Requires a score-only mode (none exists today) and committee referrals, which the repository lacks; the per-bill GovInfo XML the repository refresh already fetches carries `<committees>`, so retaining or parsing it is the cheap route. Without referrals the two committee features must be dropped for that universe and said so.
3. Ledger sheet. Write the top-8 "chance they sign on" per repository bill into the ledger as its own sheet through the same artifact-tool path Codex used, with the runtime-absent clean skip from the finishing patch set.

C-Blended (Moneyball Main Version - Blended.xlsx). Recommended: read nothing, write nothing. The forecaster needs rosters, which the workbook does not hold, and the workbook is the rank authority. Writing a forecast sheet into it would (a) trip the formula-cache trap on any openpyxl save, (b) put a display artifact one column away from becoming a rank input, which would be a rank-moving change needing its own prereg, and (c) fall squarely under `DOWNSTREAM_RECOMPUTATION_CONTRACT.md`, which forbids syncing collected legislation into the workbook until the 16-step shadow order passes and Paul approves the pre-sync report. If a forecast must be visible in Excel, the ledger sheet in C-ledger item 3 is the place.

D. Scheduler. `MoneyballWeeklyRefresh` is Disabled and the 09-01 `RUNNING` marker is a killed supervisor tick. Self-updating in practice starts when Paul re-enables it, and the Codex sentinel integration in that same job is ruled unsafe unattended until its F1-F7 patch set is applied.

Sequencing: A and B are independent of the sentinel lane and can be built now. C-ledger rides the sentinel lane and sits behind the F1-F7 apply and the contract. C-Blended is declined unless Paul overrules.

## 7. Decisions for Paul

1. Build A + B (wrapper, chain step, freshness check, tests). Executor lane, then verification in the live tree.
2. C-ledger items 1 to 3: which of the three, and whether item 2 may drop the two committee features or must parse `<committees>` from the per-bill XML.
3. C-Blended: confirm no writes to the Blended workbook.
4. `--min-cosponsors 5` for the evaluated panel stays; the display-only universe in C-ledger item 2 has no floor. Confirm.
5. The departed-member policy leaves 20 pre-snapshot joins uncounted in the live Congress. Leave as is, or count departed members' joins as positives while still excluding them as candidates.
6. Scheduler re-enable timing, after the sentinel finish patch set.

## 8. Change-control notes

Everything above is a code, chain, audit, or scheduler change and waits for Paul's apply. The forecaster's evaluated panel, its ridge penalty, and its AP claims are untouched by A, B, and C-ledger items 1 and 3. C-ledger item 2 creates a new display-only artifact and must never be merged into the evaluated panel. Any run that changes `cosponsor_scores.csv` must be reproduced once (the dry run proves determinism) and the sidecar's receipt must show the new forecast counts.

## 9. Evidence

Scratch root: `C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-employment-tenure-adjudication-e27de8\27337674-dfbb-4dce-8acd-ad49411e9dfb\scratchpad\`

- `run_cosponsor_dryrun.py`, `cosponsor_dryrun_timing.json`, `cosponsor_dryrun\cosponsor_forecast_report.json`, `cosponsor_dryrun\cosponsor_scores.csv` (dry run; glassbox events emitted under source `cosponsor_forecast_dryrun`, run id `cosponsor-dryrun-20260904T180014Z-52084`)
- `c_measure\RESULTS.md`, `results.json`, `measure.py` (M0 to M4; M3 in this file is superseded)
- `c_measure\RESULTS_M3B.md`, `results_m3b.json`, `measure_m3b.py` (corrected roster comparison, frozen-label gaps, repository schema)
- `c_measure\RESULTS_M3C_EXPLAIN.md` (departed-member explanation of the pre-snapshot gaps)
- Production artifacts read: `%LOCALAPPDATA%\Melange\lda_rebuild\derived\cosponsor_sc\` (report and scores dated 2026-08-14), `raw\billstatus119\` (2026-08-01), `C:\Users\pgoff\OneDrive\Desktop\Melange Systems\Sentinel Bill Ledger.xlsx` (2026-09-04), `bill_repository_live.json` (2026-09-02), `Moneyball Main Version - Blended.xlsx` (sheet names and headers only)

## 10. Brain update draft (STATE.md, Active workstream)

BILL-LOBBYING REGRESSION LANE (2026-09-04): the forecaster Paul calls "the linear regression" is `fec/lobbying/cosponsor_forecast.py`, already ridge-logistic; lobbying is bill selection, not a predictor. Frozen at the 2026-08-01 BILLSTATUS pull / 08-14 run, outside the chain; the sidecar re-reads stale scores. Timed dry run 2026-09-04: 16.1 min, 1.06 GB peak, scores byte-identical to production, input hashes identical, so a hash-gated chain step is sound. Coupling measured: repository 119th bills overlap the modeled set 57/142; verified joiners rank median 122/436, 5/188 in top-8; repository rosters complete and weekly-fresh. Record: `audits/COSPONSOR_FORECAST_SELF_UPDATE_2026-09-04.md`. Decisions 1-6 in that record await Paul; nothing applied.
