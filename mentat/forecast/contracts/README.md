# Giving Forecast contracts (brain DE-021)

Two JSON documents cross a lane boundary. Each has **one JSON Schema, one example payload and shared negative controls**, and
every producer and consumer is asserted against them (a prose contract failed here before: DE-021).

| Document | Schema | Example | Producer | Consumer |
|---|---|---|---|---|
| Model bundle v2 | `giving-models-v2.schema.json` | `giving-models-v2.example.json` | R refit pipeline `mentat/forecast/refit` (`rf_bundle.R`) | `mentat/app/giving_forecast.py` |
| Anchor snapshot v1 | `giving-anchors-v1.schema.json` | `giving-anchors-v1.example.json` | `mentat/forecast/anchors/build_giving_anchors.py` (Python, read-only over Mentat) | `mentat/app/giving_forecast.py` |

Shared: `negative-controls.json` (mutations that MUST fail), `contract.py` (Python validator, loader, mutation helper, anchor invariants).
Tests: `mentat/tests/test_giving_contracts.py` (validator and controls), `test_giving_forecast.py` (consumer), `test_giving_anchors.py` (producer).

## For the R pipeline builder: how to assert `rf_bundle_v2()` against this

1. Validate the writer's output against `giving-models-v2.schema.json` with a hand-written validator of the keyword subset below.
   `jsonvalidate` is not installed; `contract.py::_check` is 60 lines and is the reference implementation.
2. Validate `giving-models-v2.example.json` with the same validator (proves the validator accepts a good document).
3. Apply every `target: "models"` control of `negative-controls.json` to the example **and** to the writer's output; every one must be
   rejected. Ops: `delete` a key, `set` a value; `{"$nonfinite": "NaN"}` as a value means R's `NaN` / `Inf`.
4. Fixture note: the example is a **contract fixture**, not a refit output (`producer.pipeline` says so). Its numbers are the frozen
   v1 numbers plus the v2 fields computed from the phase-2 design (`SP\tailoring`, the PAC panel, the LobbyView pairs, the Polymarket
   daily files); the console reproduces ADDENDUM section F from it. Do not assert the writer's numbers against it, assert the shape.

### Keyword subset (both validators implement exactly this)

`$schema $id $defs $ref(#/$defs/x only) title description type(string|list) enum const properties required additionalProperties(bool|schema)
propertyNames(pattern only) minProperties items minItems minimum maximum exclusiveMinimum minLength pattern`. No `oneOf/anyOf/allOf/if`:
a nullable value is `"type": ["number","null"]`; cross-field rules live in code (`check_anchor_invariants`), not in the schema.
`type: number` and `integer` reject booleans and non-finite values; an integral double is an integer (R writes `2024` as `2024.0`).
Objects are closed (`additionalProperties: false`) except the `evidence` blocks, which are open by design.

## Model bundle v2: what the consumer reads (and therefore what the writer must emit)

Top level: `schema_version` (2), `model_version`, `built_on`, `built_at_utc`, `previous_model_version`, `producer`, `currency`, `deflator`,
`inference`, `validation`, `interval_labels`, `anchor_contract`, `industries`, `pac_model`, `share_models`, `evidence_models`, `lobby_model`,
`political_inputs`, `evidence`, `industry_slopes`, `validation_metrics`, `backtests`, `saved_outlook`, `sources`, `gates`.

* **`anchor_contract`** names which Mentat measure each model applies to, and the change kind the consumer must apply. The consumer
  refuses a bundle whose contract it does not implement (unknown measure ids or change kinds).
  * `pac`: `pac_model` applied as a **relative (log) change** to the **previous cycle's Mentat level**, twice, side by side:
    measure `pac_to_candidates` (the roster companies' PACs' own giving to House and Senate candidates, FEC pas2, D-049, direct +
    in-kind, refunds netted, IE excluded) and measure `general_giving` (the console's included receipt amount = workbook Analysis Amount, all channels).
  * `share`: `control_House` / `control_Senate` give a **pp change** added to the previous cycle's Mentat R share, on two bases side by
    side: `employee_candidate` (employees' included giving to candidate committees) and `pac_candidate` (the roster PACs' own giving to candidates).
  * `lobbying`: `lobby_model.log_refit` applied as a relative change to the **latest complete year's** Melange-LDA level, both LDA series
    (`income_total` outside-firm fees, `expenses_total` in-house) side by side, never summed.
* **`industries[id]`**: v1 fields (`id label code growth_mean growth_sd growth_min growth_max history scope`) plus `opensecrets_codes`,
  `mentat_key` (null = no Mentat data: the console does not offer the industry, it stays in estimation), `ibisworld_code`,
  `lobbyview_sector`, `calculator`, `capabilities {pac, control, lobbying}`, `withheld {model: reason}`, `growth_scaling_cycles`, `lobbying_history`.
  An industry without a capability carries a `withheld` reason; the console shows it, never guesses.
* **`pac_model`**: pooled values as in v1 (`beta ordinary_se ordinary_p critical_95 n cycles selection_repeated_p`) plus `formula`, `industries`,
  `residual_df`, `residual_sd`, `slope_rule` (R0 pooled / R1 own / R2 DerSimonian-Laird, what the auto-pick chose) with `slope_rule_reason`,
  `tau2`, `Q`, `k`, `df_interaction`, `anchor_rule` (`previous_cycle`), and two per-industry maps:
  * `slopes[id] = {own_beta, own_se, own_p, dl_weight, dl_beta, dl_se, applied}` where **`applied` is the slope the calculator uses**
    (`rule, beta, se, df, critical_95 = qt(.975, df), ordinary_p`). Each industry's own slope is `applied` when the rule is R1. The consumer
    never re-derives a rule: it labels R0 "pooled slope", R1 "industry-specific slope", R2 "partially pooled slope".
  * `prediction.industries[id] = {sigma2, pairs, df, critical_95}`: the residual variance of the anchored step (PAC: pairs (t-2, t) per
    industry, `e = dlog_pac - applied.beta * dG`; `sigma2 = sum(e^2)/(pairs-1)`, `critical_95 = qt(.975, pairs-1)`). Interval:
    `exp(b dG +/- crit * sqrt(dG^2 se^2 + steps * sigma2))`, `steps` = cycles from the anchor (1; 2 for a chained next cycle).
* **`share_models.control_House|control_Senate`**: v1 keys (`terms beta covariance ordinary_p critical_95 residual_df n adjusted_r2 residual_sd
  training_cycles history specification id signal chamber`) plus `formula`, `slope_rule(_reason)`, `tau2`, `slopes`, `prediction` (same shape;
  pairs are the **previous-cycle** steps (t-2, t), full dx over the non-industry terms), `anchor_rule` (`previous_cycle`, NOT v1's same-phase),
  `calculator: true`, `evidence`, and `application`: `pooled` = use the top-level pooled fit; `offset` = non-focal terms from `offset`
  {terms, beta, covariance}, focal Forecast slope from `slopes[id].applied` (variance `dx_o V_o dx_o + dF^2 se^2`). `offset` is null when pooled.
  Only the two control models live here: seats and the `*_industry` variants move to `evidence_models` with `calculator: false`.
* **`lobby_model`**: v1 dollar fields kept as evidence; `log_refit` is what the calculator applies: `formula dly ~ dg + factor(year)`,
  `unit`, `beta se ordinary_p critical_95 residual_df n`, `slope_rule`, `slopes[id]` (as above, `applied` per industry), `prediction.industries[id]`
  (F.4: one pooled residual variance over 71 pairs repeated per industry, `critical_95 = qt(.975, 70)`), `provenance`.
  A relative change `exp(beta * dg) - 1` per +1 pp of the change in predicted growth; the level it multiplies is Mentat's (Melange LDA).
* **`political_inputs.anchor_cycles["2024"]`**: the expected-control input of the anchor cycle, which has no row in the model history:
  `current_control {House, Senate}` (RMajNow), `window`, and per chamber `{p_rep, market, days, expected_days, first_day, partial_window, note}`.
  **Polymarket January-June 2024** (Kalshi has no 2024 January-June data; House covers 131 of 182 days, from 2024-02-21; `partial_window` must be true
  and the console flags it). The 2026 input is **Polymarket January-June 2026**: `saved_outlook.control.{House,Senate}.value` (score x100, primary),
  with `markets[]` (both markets, day counts, file sha256) and `sensitivity {kalshi_score, equal_weight_score}`. Polymarket-to-Polymarket is primary.
* **`saved_outlook`**: `control` only; `seats` is gone.
* **`evidence_models`**: seat regressions (`seats_House`, `seats_Senate`, ...) kept as evidence, every one `calculator: false`; the console lists them as "no signal".
* **`backtests`**, **`gates`**, **`sources`**, **`producer`**: as SPEC 3.12 (`sources[]` adds `role`, `pinned`).

### Deviations from phase-1 SPEC 3.12 that the R writer must follow (owner rulings of 2026-09-30)

1. `share_models.*.anchor_rule` is `previous_cycle` (SPEC said `same_phase_latest`); the step residual for shares uses (t-2, t) pairs.
2. `saved_outlook.control.*.value` is the **Polymarket** Jan-Jun 2026 score (SPEC: the Kalshi/Polymarket equal weight 19.03 / 56.40); the equal weight is a sensitivity.
3. `pac_model.slopes[id].applied` (and the same in `share_models`, `lobby_model.log_refit`) carries the rule the auto-pick chose; own slope = R1.
4. `lobby_model.log_refit` is required (the lobbying calculator is relative).
5. `political_inputs` is new (the 2024 anchor-cycle control input).

## Anchor snapshot v1: what the builder writes and the consumer reads

File `MENTAT\mentat\state\giving-anchors\giving-anchors-v1.json` (+ `giving-anchors-v1.receipt.json`), runtime state (D-048: not in git), rebuilt nightly
and after each Mentat publish. A separate file from the model bundle, because anchors move whenever Mentat republishes, independent of refits.
`MENTAT_GIVING_ANCHORS` overrides the path. The console **refuses** (`status: anchor_stale`) when `industries[id].mentat.workbook_sha256` differs from
the sha256 of the workbook file now published in the report directory.

* The example `giving-anchors-v1.example.json` is **real builder output** (the four Mentat datasets built from the published workbooks, indexes,
  FEC files and Melange LDA file on 2026-09-30), not hand-made: every number in ADDENDUM section F comes from it, and
  `MENTAT_ANCHORS_REAL=all python -m pytest mentat/tests/test_giving_anchors.py` re-derives banks and credit unions from the real tree and compares.
* Top: `schema_version` 1, `kind`, `built_at_utc`, `builder`, `unavailable` ({id: reason} for industries it could not anchor), `cpi` (`multipliers`: cycle end year -> `cpi[2025] / mean(cpi[t-1], cpi[t])`; a missing
  year means face value: 2026 CPI does not exist), `thin_base_threshold_usd` (100,000), `industries`.
* `industries[id]` (`id` is the forecast industry id: `commercial_banks` = Mentat Banking, `credit_unions` = Credit Union, `property_casualty`;
  `community_banks` is a separate entry with `forecast_industry: null`, never merged into banks; auto has no Mentat data and no entry):
  * `mentat`: dataset, workbook file, `workbook_sha256`, `index_token`, `database_sha256`, `payload_sha256`.
  * `coverage`: `rule`, `collection_date`, `rule_coverage_end` (last quarter-end whose report deadline, the 15th of the next month, was on or before the
    collection date), `coverage_end` (== the rule end, or earlier when a cut-back applies: credit unions 2026-05-31, reason "June incomplete"), `reason`, `flags`.
  * `general_giving`: `cycles {"2022","2024","2026"}` (dollars, nominal, net of negative adjustments; the open cycle holds every row to date),
    `by_funding_source`, `observed` = cumulative month-end cuts of the open cycle up to `coverage_end` ({through, amount}); rows dated after the
    coverage end belong to the remainder window, never to observed.
  * `candidate_receipts`: employees' included giving to House / Senate candidate committees (index joined to the pinned source DB on `sub_id`;
    `recipient_committee_type` H or S; presidential P excluded), `{D, R, other}` per chamber per cycle; `observed` cuts; `thin_base` flags ($100K of D+R per chamber).
  * `pac_to_candidates`: the roster companies' PACs' own giving to candidates (FEC pas2, D-049 `count_latest`, 24K + 24Z signed, 24A/24E excluded;
    chamber from the CAND_ID prefix, party from the candidate master), `committees`, `inputs` (file sha256 + FEC last_modified), per cycle `{House, Senate, to_house_senate,
    presidential, no_candidate, all_recipients}`, `observed` cuts, `thin_base`, `single_pac` (true for credit unions: SchoolsFirst only).
  * `lda`: Melange LDA `income_total` and `expenses_total` (two series, never summed; bank total for banks) annual + the partial year's quarters, `source_sha256`.
    `status: unavailable` with a `reason` for industries without a Melange-LDA sector (P&C).
  * Every measure has `status` ready | unavailable (+ `reason`); a consumer never reads numbers from an unavailable block.
* Cross-field invariants (`contract.py::check_anchor_invariants`): cut dates strictly increasing and ending on `coverage_end`; `to_house_senate` equals the House +
  Senate parts; `all_recipients` equals its parts; thin-base flags agree with the dollars; `single_pac` agrees with the committee list; partial LDA totals equal their quarters. Each industry's anchor cycle (`current_cycle - 2`) has a CPI multiplier (a missing one must never read as 1.0); a ready LDA block carries both series over the same complete years.
