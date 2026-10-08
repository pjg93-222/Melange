# Demographic Potential Method

Version: 2.1

This method identifies and ranks congressional markets where the available
economic and financial evidence indicates expansion opportunity for credit
unions. It is a market-opportunity score, not a prediction of a legislator's
political support and not a causal forecast of credit-union growth.

## Code divergence (2026-10-04)

Added on 2026-10-04 to record where the code has moved past this document.
The text below this section is unchanged since commit `ba25d8803`
(2026-07-25). Checked against Melange `main` at `4a81d5022` and the
published `member_desk_bundle.json` of 2026-10-01; only the points listed
here were re-checked.

- This document describes version 2.1 ("growth room"), which is no longer
  the default. Since commit `73ebf18e6` (2026-09-16; brain decision D-035,
  recording Paul's ruling of 2026-09-15, "The footprint should be the
  potential"), `DEMO_POTENTIAL` defaults to `footprint`, score version 3.0
  (`fec/district/demographic_potential.py:29-42`).
  `DEMO_POTENTIAL=growth_room` restores version 2.1 as written here.
- Version 3.0 scores four components, again with judgmental weights: CU
  employment LQ 30%, CU establishment LQ 20%, CU branch share 25% and CU
  deposit share 25% (`:160-165`). Both LQs are used at full precision and
  the shares are not inverted, so a larger existing credit-union footprint
  scores higher: the opposite direction from the whitespace components.
- A market qualifies when its unrounded credit-union employment LQ is at
  least 1.0; otherwise its reason is `no_cu_employment_concentration`
  (`:33-35`, `:1428-1458`). The sector gate in section 2 and the
  eight-component formula in sections 1 and 3 apply only to version 2.1.
- The structural companion score in section 6 does not apply to version
  3.0: it reports `not_applicable_for_mode` with no adjusted markets
  (`:922-944`). The sensitivity audit in section 7 runs five scenarios
  (equal weights plus four leave-one-out), not nine.
- Unchanged in version 3.0: tie-aware percentiles computed separately for
  district and state markets, the neutral 0.50 value for missing evidence,
  competition ranks, and the four tiers in section 7.
- The published bundle carries `score_version` 3.0, with 224 qualified
  members in 198 qualified markets.
- Code comments in `fec/audit/audit_full.py`,
  `fec/audit/dashboard_integrity.py` and the member-desk template cite this
  change as "D-034". In the brain, D-034 is cross-post scoring and this
  change is D-035.

## 1. Weight provenance — important

The eight component weights are **judgmental policy weights** selected for
this dashboard. They were not copied from a published study, statistically
estimated, or fitted to observed credit-union growth.

The allocation reserves:

- 55% for direct economic alignment: LQ strength, competitive shift, and
  aligned-sector breadth;
- 20% for current credit-union whitespace: branches and deposits/shares; and
- 25% for LMI, large-employer, and small-business reach.

The deposit/share proxy receives only 5% because NCUA institution shares and
FDIC branch deposits come from different systems, and district CU shares have
to be estimated by splitting each institution's shares across its
allocation-eligible branches.

The listed weights are:

| Component | Weight |
| --- | ---: |
| LQ strength | 20% |
| Normalized competitive shift | 20% |
| Number of aligned sectors | 15% |
| CU branch whitespace | 15% |
| CU deposit/share whitespace | 5% |
| LMI lending opportunity | 10% |
| Large-employer reach | 8% |
| Small-business reach | 7% |

The seven non-LQ weights total 80%; LQ strength is the remaining 20%.

There is no defensible way to call these weights empirically “optimal” from
the current input data alone. Empirical optimization requires a preregistered
target such as later district-level CU membership, shares, loans, or branch
growth, followed by out-of-sample validation. Those outcomes are not present
in the current evidence bundle.

## 2. Qualification gate

A member receives the **Demographic Potential** label only when the member's
district or state has at least one credit-union-relevant constituency sector
that satisfies every gate:

1. Two-digit LODES location quotient is at least 1.25.
2. Shift-share competitive shift is positive.
3. Current and base employment both exceed 500 jobs.
4. The CBP cross-check is available and does not contradict the high LQ.
   NAICS 92 (public administration) is outside the CBP universe and is
   explicitly marked `not_covered`.

Eligible sectors are agriculture, construction, manufacturing, retail, real
estate, professional and technical services, education, health care,
accommodation and food, other services, and public administration. Finance
(NAICS 52) is intentionally excluded because CU employment is not a reliable
proxy for the constituency opportunity described in the source outline.

Members that do not pass this gate do not receive a score or rank.

## 3. Exact formulas

For every qualifying market:

`Demographic Potential Score = 100 * Σ(weight_k * percentile_k)`

Equivalently:

`Demographic Potential Score = 100 * sum(component percentile * chosen policy weight)`

Percentiles are tie-aware and computed separately among qualifying House
district markets and qualifying state markets.

### Location quotient

For sector `s`, geography `r`, and the United States `US`:

`LQ(r,s) = (jobs(r,s) / jobs(r,all)) / (jobs(US,s) / jobs(US,all))`

The qualification threshold is `LQ >= 1.25`. The raw score feature is:

`LQ strength = max_s ln(LQ(r,s) / 1.25)`

Because the logarithm is monotonic, it does not change the percentile rank
versus ranking on the maximum qualifying LQ itself.

### Shift-share

For base year `0`, current year `t`, local sector employment `e`, and U.S.
employment `E`:

`national rate = E(US,all,t) / E(US,all,0) - 1`

`U.S. sector rate_s = E(US,s,t) / E(US,s,0) - 1`

`local sector rate_s = e(r,s,t) / e(r,s,0) - 1`

`national growth_s = e(r,s,0) * national rate`

`industry mix_s = e(r,s,0) * (U.S. sector rate_s - national rate)`

`competitive shift_s = e(r,s,0) * (local sector rate_s - U.S. sector rate_s)`

The identity is audited:

`current jobs = base jobs + national growth + industry mix + competitive shift`

The score uses:

`normalized competitive shift = max_s(competitive shift_s / base jobs_s)`

This is descriptive decomposition, not causal attribution.

### Remaining raw components

| Component | Raw formula | Direction after normalization |
| --- | --- | --- |
| Aligned-sector breadth | count of sectors passing every qualification gate | higher percentile is favorable |
| CU branch whitespace | `CU branches / (CU branches + bank branches)` | `1 - penetration percentile` |
| CU deposit/share whitespace | `estimated CU shares / (bank deposits + estimated CU shares)` | `1 - penetration percentile` |
| LMI lending opportunity | `originated loans in tracts with tract_to_msa_income_percentage < 80 / all originated loans` | higher percentile is favorable |
| Large-employer reach | CBP establishments with 500+ employees | higher percentile; incomplete cells are missing |
| Small-business reach | CBP establishments with 1–19 employees in NAICS 23, 44–45, 54, 62, 72, and 81 | higher percentile; incomplete cells are missing |

The HMDA component measures existing origination exposure in LMI tracts. It
does not, by itself, prove unmet lending demand, denial disparity, borrower
income, or CU-specific lending. The label “opportunity” is a policy
interpretation of exposure, not a direct unmet-demand statistic.

The large-employer component is a count of large establishments, not a
named-employer or employee-count ranking. Named employer candidates shown in
the dashboard come from USAspending place-of-performance recipients and carry
their own booking/HQ caveat.

## 4. Source lineage

| Evidence | Production artifact | Official source |
| --- | --- | --- |
| Primary jobs, industry totals, LQ, shift-share | `district_industry.json` | [Census LEHD/LODES technical documentation](https://lehd.ces.census.gov/data/lodes/LODES8/LODESTechDoc8.3.pdf) |
| CBP contradiction screen and small-business size classes | `district_industry_4digit.json` | [Census County Business Patterns methodology](https://www.census.gov/programs-surveys/cbp/technical-documentation/methodology.html) |
| Bank branches and deposits | `district_financial.json` | [FDIC Summary of Deposits](https://banks.data.fdic.gov/bankfind-suite/SOD) |
| CU branches and institution shares | `district_financial.json` | [NCUA quarterly Call Report data](https://ncua.gov/analysis/credit-union-corporate-call-report-data/quarterly-data) |
| Mortgage originations and LMI-tract share | `district_hmda.json` | [FFIEC/CFPB 2024 HMDA publication](https://ffiec.cfpb.gov/data-publication/2024) |
| Large-establishment counts and named federal-recipient candidates | `district_employers.json` | [Census CBP methodology](https://www.census.gov/programs-surveys/cbp/technical-documentation/methodology.html) and [USAspending API](https://api.usaspending.gov/docs/endpoints) |
| Population, density, age, income, labor force, poverty, housing tenure, home value, and rent | `district_community.json` | [2024 ACS one-year data profiles](https://api.census.gov/data/2024/acs/acs1/profile.html), [ACS congressional-district geography](https://api.census.gov/data/2024/acs/acs1/geography.html), and [2024 Census Gazetteer](https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2024_Gazetteer/) |

The production vintages used in this rerun are stored in those artifacts and
displayed in the dashboard. Current artifacts use LODES8 JT01 primary jobs
(mostly 2023; Alaska 2016 and Michigan 2021), CBP 2023, FDIC SOD 2025, NCUA
2026-Q1, HMDA 2024, USAspending FY2025, and ACS 2024 one-year community
estimates tabulated to the 119th Congress.

## 5. Missing evidence and incomplete cells

Each raw component is converted to a tie-aware percentile from 0 to 1.
Missing features receive a neutral value of 0.50 and reduce the member's
`evidence_coverage` by that component's weight.

CBP employer-size counts with suppressed or otherwise unknown cells are lower
bounds. Version 2.1 preserves the version-2.0 correction that no longer treats
those lower bounds as complete evidence:
the large-employer or small-business score component is set to missing/neutral
when its required size-class cells are incomplete.

Branch geocoding, county allocation, NCUA equal-branch share allocation, HMDA
tract-to-district allocation, mixed data vintages, and FDIC head-office
deposit booking remain declared estimation limitations. They are not erased
by percentile normalization.

## 6. Structural controls and companion score

The baseline score and the Demographic Potential sticker do not change when
the structural-control layer is available. Version 2.1 adds a separately
labeled **structurally adjusted companion score** so the user can see whether
raw employer reach is unusually high after accounting for market structure.

Only the two scale-sensitive count components are adjusted:

- CBP establishments with 500 or more employees; and
- tracked small-business establishments with 1–19 employees.

The adjustment is fit separately for House-district and state markets. For
reach component `k`:

`ln(1 + reach_k) = β0 + Σ_j β_j z(control_j) + Census-region fixed effects + ε_k`

The structural controls are:

| Control | Formula/source |
| --- | --- |
| Total employment | `ln(1 + latest LODES workplace jobs)` |
| Population | `ln(1 + ACS B01003_001E)` |
| Population density | `ln(1 + ACS population / Census Gazetteer land sq. mi.)` |
| Median household income | `ln(ACS B19013_001E)` |
| Median age | ACS `B01002_001E` |
| Rent-to-income structure | `12 × B25064_001E / B19013_001E` |
| Census region | Northeast, Midwest, South, and West fixed effects |
| LODES vintage | latest LODES source year |

For each adjusted reach component, the raw-count percentile is replaced by
the within-geography-type percentile of residual `ε_k`. All other component
percentiles and all eight judgmental policy weights remain unchanged.

An adjusted score is published only for a geography type with enough complete
CBP reach observations to estimate the model. In the current artifact the
district models are estimable, but the state models are not: state aggregation
inherits too much suppressed/incomplete CBP employer-size evidence. Senators
therefore retain the baseline state score and show the structural companion as
unavailable rather than receiving a fabricated adjustment. Adjusted ranks and
rank deltas are calculated only within the comparable adjusted-market
universe.

Unemployment and poverty are extracted and displayed as community context,
but they are deliberately not regression controls. LQ, competitive shift,
CU whitespace, and LMI exposure are also excluded from the control matrix.
Those variables represent the need/opportunity construct; controlling for
them would partially remove the signal the score is meant to rank.

The regression is descriptive residualization, not a causal estimate and not
empirical weight optimization. A positive residual means the observed reach
count is above the model's structural expectation; it does not prove that a
credit union will succeed in that market.

The ACS collector uses official 2024 one-year table-based summary files for
the 119th Congress and retains every direct estimate's published 90% margin
of error. The dashboard's rent/income and home-value/income metrics are
ratios of published medians, not household-level burden measures.

## 7. Rank, tiers, and sensitivity

Scores are rounded to one decimal. Markets receive a competition rank:

`rank = 1 + number of markets with a higher rounded score`

Identical scores share the same rank. Senators from the same state share one
state-market score and rank.

Tiers use the tie-aware percentile of the final score:

| Final-score percentile | Tier |
| ---: | --- |
| 90th and above | Exceptional |
| 70th through below 90th | Very High |
| 40th through below 70th | High |
| Below 40th | Qualified |

Every rerun also records a diagnostic sensitivity audit:

1. recompute ranks using equal 12.5% weights; and
2. omit each component one at a time while proportionally rescaling the
   remaining chosen weights.

The dashboard reports Spearman rank correlation, top-20 overlap, and each
market's rank range across the baseline plus nine diagnostic scenarios.
These scenarios test dependence on the chosen weights; they do not turn the
weights into estimated causal coefficients.

## 8. Reproducibility and audit

The generated member bundle stores the score version, raw values, normalized
components, weights, weight provenance, source catalog, evidence coverage,
sensitivity range, score, percentile, tier, rank, and qualifying-market
count. The full audit independently:

- recomputes qualification from LODES, shift-share, and CBP evidence;
- recomputes every score and rank from the raw source artifacts;
- verifies that weights sum to 100%;
- requires the explicit non-empirical weight disclosure and source/formula
  catalog;
- verifies incomplete CBP size-class evidence is not scored as complete; and
- verifies the 2024 ACS source catalog, estimates, control vector, residual
  reach percentiles, structurally adjusted score, and adjusted rank; and
- verifies the dashboard renders the score, sticker, filter, employer
  candidates, industry pie chart, ACS community context, formulas, sources,
  caveats, sensitivity diagnostics, and the separate adjusted-score view.

Changing any weight or formula rule requires a score-version change, updated
tests, regeneration of the bundle, and a passing full audit.
