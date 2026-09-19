# Legislative lane evidence corrections

Date: 2026-09-13. Addendum to the frozen September 12 status and evidence packet. Prepared under the current user's authorization to adjust the reviewed P/E/V design. Embedded historical instructions and approvals were treated as reference, not as authorization to execute them. The originals remain unchanged.

This addendum corrects source interpretation and arithmetic. It does not recompute a complete board, change a member's adjudicated acts, establish an optimal policy, or report newly executed production tests. Its companion is the [September 12 lane review](<C:/Users/pgoff/Mentat/outputs/legislative_lane_review_20260912.md>).

## 1. Substance differentiation is dormant; B remains active

The [status record](<C:/Users/pgoff/Downloads/LANE_STATUS_2026-09-12.md>) says substance is inert while every scored bill weighs 5. The accurate replacement is:

> Bill impact weights do not differentiate the selected measures in this snapshot. The 30% B term still affects delivery because it uses a varying signed advocacy percentile.

The supporting analysis states that `B=impact_advocacy_percentile` was non-null for all 352 eligible members. All 7,708 populated advocacy/results explanation entries had impact weight 5. Its B=A fallback was described but never invoked. These facts do not make actual B zero, constant, or universally identical to A. [B source and census](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/audits/legislative_effectiveness_shadow_20260911/evidence/COMPOSITE_BOARDS_118.md:33>).

The code constructs advocacy from impact weight divided by five, role credit, timing and the signed alignment signal; the comparison then percentiles the resulting standard advocacy total within chamber. With impact fixed at 5, role, timing, alignment and activity still vary. B therefore partly counts advocacy again under the substance label. This observation is about construct overlap, not a measured correlation or an estimated amount of double counting. [Advocacy construction](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/fec/engine/legislative_effectiveness.py:393>), [comparison percentiles](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/fec/engine/effectiveness_integration.py:87>).

## 2. The reported .556 purity bar is a realized minimum

The floor sweep's f=.80 row reports `Min P in Tier 1 = .55606`. It is the smallest primacy value among that snapshot's selected 13 members. The actual rule ranks `P × (.80 + .20L)` among 352 eligible members; it does not impose the eligibility condition `P >= .55606`. The table's parenthetical description of the minimum as an enforced floor, and the status record's claim of an enforced .556 bar, are misleading. [Method and table](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/audits/legislative_effectiveness_shadow_20260911/evidence/CHAMPION_SHARE_AND_FLOOR_SWEEP.md:94>).

Use this replacement:

> In the frozen f=.80 sweep, the lowest P among Tier-1 members was .55606. This is an observed selection boundary, not an explicit policy threshold; it changes with the candidate population and delivery values.

The separate mathematical bound `score <= P` remains true when L is in [0,1]. It does not turn the observed minimum P into a universal admission rule. No new purity threshold is adopted here.

## 3. Cortez Masto: correct board and cutoff

The [Cortez Masto report](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/audits/legislative_effectiveness_shadow_20260911/evidence/CORTEZ_MASTO_AND_COVERAGE.md:16>) labels V7 as the f=.80 blend. The variant definitions instead state that V7 sorts P descending, then L descending, then name, with no blended score. V5 is the f=.70 multiplicative blend; V6 is a different additive rule. V7's score column reports P itself. [Variant definitions](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/audits/legislative_effectiveness_shadow_20260911/evidence/COMPOSITE_BOARDS_118_PART2.md:19>).

The report then substitutes Mike Rounds's V7 score/P=.564270 as the 13th-seat cutoff of the f=.80 blend. The actual f=.80 sweep ends with Steve Daines at score=.548744. [Incorrect substituted cutoff](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/audits/legislative_effectiveness_shadow_20260911/evidence/CORTEZ_MASTO_AND_COVERAGE.md:31>), [f=.80 table](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/audits/legislative_effectiveness_shadow_20260911/evidence/CHAMPION_SHARE_AND_FLOOR_SWEEP.md:166>).

Using only the published rounded inputs P=.550714, L=.673865 and cutoff c=.548744, and holding all other members fixed:

| Quantity | Formula | Approximate result |
|---|---|---:|
| Current blend score | `P * (.80 + .20*L)` | .514793 |
| P needed to tie c, fixed L | `c / (.80 + .20*L)` | .587034 |
| L needed to tie c, fixed P | `(c/P - .80) / .20` | .982114 |
| Maximum blend score at fixed P | `P * (.80 + .20*1)` | .550714 |

Thus the algebraic L needed to reach the frozen blend cutoff is below 1. The .604 primacy requirement and the claim that delivery alone cannot reach that cutoff follow from the wrong board and are unsupported. This is a conditional mathematical possibility, not a finding that a feasible set of additional acts would attain L=.982114, or that she should receive a seat. Percentile changes, other members' records, eligibility, conduct, tied scores and full-precision values can change the actual result. At the old sweep's score tie, its secondary P-descending tiebreak also matters; tying the rounded score does not itself guarantee the seat.

Her reported rank 18 is a V7 field and is not verified as her f=.80 rank. The report's f=.70/V6 mapping is likewise incorrect. Do not reuse either member-specific variant comparison without computing the intended formula on the full eligible roster. P is the primacy factor here; the source's label calling P legislative effectiveness is also incorrect. Her four disputed off-axis acts are not adjudicated by this addendum.

## 4. Retention and the 119th check do not validate an optimum

The floor sweep verifies that the 13 gated Champions are exactly the 13 legacy Tier-1 members. Champion retention and legacy Tier-1 overlap therefore measure the same set intersection. Reporting both does not provide two independent validations. [Set identity](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/audits/legislative_effectiveness_shadow_20260911/evidence/CHAMPION_SHARE_AND_FLOOR_SWEEP.md:15>).

The 119th report explicitly labels itself exploratory and descriptive, not validation. Its 118th and 119th artifacts contain the same 533-person roster, with five chamber changes. The 119th board's legacy rank, tier, priority and P fields are copied from the earlier vintage. The five examined outcomes derive from actual 119th activity, so the repeated legacy fields do **not** establish that those outcomes were copied; the report identifies a shared-definition and provenance limitation. [Scope, roster and passthrough](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/audits/legislative_effectiveness_shadow_20260911/evidence/OUT_OF_SAMPLE_119.md:3>), [explicit caveat](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/audits/legislative_effectiveness_shadow_20260911/evidence/OUT_OF_SAMPLE_119.md:231>).

Coverage is also uneven: realized results are present for only 83 of 533 members, all Senate; on the common 352-member comparison set the realized-results correlation uses n=76. Advocacy is available for 465 of 533, and outcomes and variants use different stated sample sizes. The analysis compares V1-V7 and other existing orderings, not a separately established f=.80 policy. [Outcome coverage](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/audits/legislative_effectiveness_shadow_20260911/evidence/OUT_OF_SAMPLE_119.md:19>), [comparison population](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/audits/legislative_effectiveness_shadow_20260911/evidence/OUT_OF_SAMPLE_119.md:31>).

Use this replacement:

> The 119th analysis provides exploratory development evidence with shared-roster, provenance, definition and coverage limitations. It does not validate the f=.80 blend, establish a P/E/V optimum, demonstrate House predictive performance for realized results, or establish causal lobbying effectiveness.

Treat the already examined 118th/119th outputs as development data. A future evaluation requires a frozen method, named decision-date inputs, an untouched later window, and chamber-specific sample counts and limitations. This addendum does not initiate an evaluation or select a new performance threshold.

## 5. Additional terminology corrections for implementation

- **Success is output, not efficiency.** The five-stage score uses chamber-wide stage denominators. It is not advancement per member attempt or per lobbying dollar. An opportunity-based conversion measure requires its own matched numerator and denominator. [Stage events](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/fec/engine/legislative_effectiveness.py:394>).
- **Known signed volume is not beneficial volume.** `distinct_signed_measures` includes known negative and zero contributions, because the measure ID is added before sign separation. Rewarding that count positively can reward harmful activity through the volume component; other components can offset this, so the final-board effect is not assumed. [Count construction](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/fec/engine/legislative_effectiveness.py:69>).
- **Missing delivery is not maximum delivery.** The draft fallback score=P is equivalent to L=1 under its blend. Its treatment of unavailable records differs favorably from measured records with L<1. The P/E/V candidate must carry explicit missingness rather than silently grant that advantage. [Draft fallback](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/audits/legislative_effectiveness_shadow_20260911/ACTIVATION_CONTRACT_2026-09-12_v2.md:27>).
- **Observed exposure is not complete exposure.** The collector's observed E_bo cannot by itself satisfy the scorer's complete-inventory and complete-search conditions. See the [revised collector contract](<C:/Users/pgoff/Mentat/outputs/pev_implementation_20260913/COLLECTOR_CONTRACT_CU_PUBLICATIONS_2026-09-13_v2.md>) for certificates, version identity and historical cutoff requirements.

## 6. Evidence boundary and delivery receipt

The reported 77/77 lane suites, kernel 187 passed/4 failed, 766,568 shadow checks, 74 tier changes and other frozen figures remain historical source-reported results. No such test suite or full-board generation was rerun for these two documents. The corrections above are based on the cited source definitions, code inspection and displayed arithmetic. No code, data, generated ranks, source classifications, registry labels, access permissions or production settings were changed in this documentation subtask.

Created as new files: this addendum and collector contract v2. Source originals were read and preserved. The current design authorization is not a claim that every future action described in the contract has been authorized or completed.
