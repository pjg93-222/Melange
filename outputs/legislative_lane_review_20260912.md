# Legislative lane review: Primacy, Efficiency, Volume

Prepared from the September 12, 2026 status record, its supporting packet, and the scoring source. This is a proposed replacement design and evidence correction, not an activated policy or a newly validated model. The document's dispatch instructions and historical approvals were treated as background. No production code, ranks, labels, collectors, or pipeline settings were changed.

**Recommendation: retain the existing evidence-adjusted CU primacy measure, introduce a real legislative conversion measure, and make useful volume the third ranking criterion. The current delivery blend does not implement that order.**

The interpretation used here is: primacy means credit-union interests take precedence in a member's observed agenda; efficiency means advancing those interests per attributable legislative opportunity; volume means the amount of useful legislative activity. Institutional power and originating a bill are different concepts. Sponsor leadership remains relevant through attribution.

## 1. The proposed decision rule

Apply the existing evidence eligibility, conduct rules, and explicit adjudications in their established order. Among comparable, qualified records, rank by:

**Primacy descending → conversion efficiency descending → useful volume descending → stable member identity.**

This is a hierarchy, rather than three exchangeable weighted ingredients. A lower criterion cannot buy its way past a higher one. The existing 13/24/48 seat structure can remain a display convention; it does not establish the quality of the measurements.

| Priority | Recommended measure | Interpretation |
|---|---|---|
| 1. Primacy | Existing `factor_ranked`, with raw orientation and evidence support visible | How consistently does the observed agenda prioritize CU beneficiaries? |
| 2. Efficiency | Evidence-adjusted beneficial advancement per eligible CU legislative opportunity | How reliably does the member move attributable CU work forward? |
| 3. Volume | Distinct verified beneficial CU measures, with role and date details | How much useful work does the member undertake? |

An exact hierarchy has a real cost: even a tiny P difference dominates E and V. If almost all P values differ, efficiency rarely changes the order. If the desired policy treats small P differences as indistinguishable, define fixed primacy bands before examining the resulting member list, then compare E and V within each band. The band boundaries would be an additional policy choice; this packet does not establish them. Avoid pairwise “within epsilon” comparisons, which can produce an inconsistent ordering.

No optimal numerical weights can be inferred from the three priorities alone. The exact hierarchy is the most faithful default for a literal reading of the requested order. A compensating blend requires an explicit willingness to trade primacy for delivery.

## 2. Why the current formula needs revision

The draft defines `F = P × (0.80 + 0.20L)` and `L = 0.35S + 0.35A + 0.30B`. It protects primacy to a degree, but it does not make primacy absolute. For example, P=.60/L=0 scores .48, while P=.50/L=1 scores .50. The lower-primacy member wins. This is arithmetic, not a newly measured member comparison. [Activation definitions](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/audits/legislative_effectiveness_shadow_20260911/ACTIVATION_CONTRACT_2026-09-12_v2.md:9>).

More fundamentally, S is relative legislative output, not efficiency. The scorer adds role-, timing-, and alignment-weighted milestone credit and divides by chamber-wide milestone totals. It does not divide by the member's attempts, staff time, or lobbying cost. Taking a percentile does not add an efficiency denominator. S and A also have equal weights. [Stage calculations](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/fec/engine/legislative_effectiveness.py:394>).

The separate B term compounds the problem. Although all recorded impact weights are 5, B remains a varying signed advocacy score because role, timing, and activity differ. It is not zero, constant, or universally identical to A. All 352 eligible members used the actual advocacy percentile; the fallback B=A was never used. The accurate statement is **“substance differentiation is dormant; the 30% B term still affects rankings.”** [B census](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/audits/legislative_effectiveness_shadow_20260911/evidence/COMPOSITE_BOARDS_118.md:33>).

Existing P already uses evidence volume to reduce uncertainty in orientation. Preserve that distinction: more evidence can make a primacy estimate more credible without making sheer activity a higher policy priority. [Orientation and evidence adjustment](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/fec/engine/primacy_factors.py:384>).

## 3. Build efficiency from the underlying opportunities

Use a dedicated **legislative conversion efficiency** measure. The initial observable is a stage-specific rate:

`credited beneficial advancements / corresponding eligible CU attempts`

Construct numerator and denominator from the same member-measure registry, alignment convention, role attribution, and observation window. Do not divide S's percentile by A's percentile: their populations and scoring bases differ, and percentiles discard the quantities needed for a rate.

- Include verified attempted measures that did not advance. Count each member-measure once per relevant opportunity; repeated categories, stages, URLs, or rows cannot create extra attempts.
- Keep introduction as an attempt, rather than treating introduction itself as successful conversion. Report committee action, action beyond committee, chamber passage, and enactment separately. Define any scalar aggregation before using it to choose winners.
- Credit only milestones for which the member had an eligible role at the time. Preserve the existing sponsor/original/later-cosponsor distinctions and withdrawal chronology. A later join must not receive an earlier accomplishment.
- Compare opportunities with similar time to mature. A completed Congress and an in-progress Congress are not equally exposed to enactment. Keep current-term rates provisional; use chamber, term, bill age, and service exposure in the comparison.
- Display successes, attempts, coverage, and uncertainty beside the rate. One win from one attempt is thin evidence, not automatically a more reliable record than eight from ten. Choose an evidence adjustment prospectively using appropriate historical data; this review does not invent a “validated” shrinkage constant or minimum count.
- Preserve zero, unknown, and not-yet-mature states. Zero attempts make a conversion rate undefined; they do not establish a 0% success rate.

These are descriptive attribution measures. They do not establish that a member caused a bill's passage, or measure return per lobbying dollar. The latter requires actual engagement costs and a defensible incremental-effect model.

Bill substance should enter as a measure-level value input when sufficiently supported, using compatible weights in both sides of a weighted rate. It should not independently reward a second tally of advocacy. Retain absolute output alongside efficiency so users can see both scale and conversion.

## 4. Make the third criterion useful volume

The present `distinct_signed_measures` counts measures with known contributions, including zero and negative contributions. “Signed” means an alignment value is known; it does not mean the work benefits CUs. Its positive volume reward can therefore count harmful activity. That does not prove every harmful act increases the final composite score, because other components may decrease. [Count construction](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/fec/engine/legislative_effectiveness.py:69>).

Define the reward as distinct measures with verified beneficial CU activity. Keep harmful, neutral, and unknown activity visible in separate totals and retain the existing primacy accounting. Preserve records rather than deleting inconvenient evidence. Repeated milestones are one measure, and verified policy lineage can identify duplicate vehicles without silently merging merely similar bills.

For lobbying use, defensive outcomes also matter. A verified removal of a harmful provision can be valuable, but a bill's failure to pass does not by itself prove a member blocked it. Add defensive credit only through an explicit outcome-and-attribution rule, not automatic inference from absence of enactment.

## 5. Correct four decision-relevant claims

**The .556 purity bar is not an enforced threshold.** The sweep reports .55606 as the lowest P among its selected Tier-1 members. The ranking formula does not impose P≥.55606. That realized minimum can change with the candidates and their delivery. [Sweep table](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/audits/legislative_effectiveness_shadow_20260911/evidence/CHAMPION_SHARE_AND_FLOOR_SWEEP.md:102>).

**The Cortez Masto calculation uses the wrong board.** Her supporting report identifies V7 as the f=.80 blend, but V7 orders P first and uses L as a tiebreak. It substitutes Mike Rounds's pure-P score .564270 as the blend's 13th-seat cutoff. The actual f=.80 table ends with Steve Daines at .548744. [Mistaken comparison](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/audits/legislative_effectiveness_shadow_20260911/evidence/CORTEZ_MASTO_AND_COVERAGE.md:31>), [actual cutoff](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/audits/legislative_effectiveness_shadow_20260911/evidence/CHAMPION_SHARE_AND_FLOOR_SWEEP.md:183>).

Using only the published rounded values, P=.550714 and L=.673865:

| Calculation with other members fixed | Result |
|---|---:|
| Current blended score | .514793 |
| P needed to tie the published cutoff at current L | approximately .587034 |
| L needed to tie the published cutoff at current P | approximately .982114 |

Thus the formula does allow delivery alone to reach that frozen cutoff, subject to eligibility and conduct rules. The .604 requirement and “delivery alone cannot seat her” conclusion are unsupported. Rank 18 is sourced from V7 and is not verified as her f=.80 rank. These arithmetic corrections do not adjudicate her four disputed acts or constitute a fresh full-board computation.

**Missing delivery receives preferential treatment in the draft.** An unavailable L gives score=P, equivalent algebraically to maximum L. A member with the same P and measured L<1 receives less. At P=.60 and L=.50, the measured score is .54 while the missing-data score is .60; the maximum relative advantage is 25% against L=0. [Fallback rule](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/audits/legislative_effectiveness_shadow_20260911/ACTIVATION_CONTRACT_2026-09-12_v2.md:27>). Preserve the established production result when required inputs fail, flag the attempted generation, and show incomplete records as provisional in analysis. Do not silently mix incomparable fallback formulas into a new authoritative board.

**Champion retention and the 119th check do not validate the optimum.** The existing champion set equals legacy Tier 1 exactly, so champion retention and legacy overlap are the same benchmark. The 119th analysis is explicitly exploratory: it reuses the same 533-person roster and P/legacy fields, and observed results cover only 83 people, all Senate. It examines V1–V7 rather than establishing the later f=.80 policy's superiority. [Set identity](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/audits/legislative_effectiveness_shadow_20260911/evidence/CHAMPION_SHARE_AND_FLOOR_SWEEP.md:15>), [119th limitations](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/audits/legislative_effectiveness_shadow_20260911/evidence/OUT_OF_SAMPLE_119.md:11>).

## 6. Spend collection effort where it improves the decision

The highest-value next work is the opportunity denominator, historical coverage, and coherent scoring policy. Expanding the publication corpus is secondary while efficiency is undefined.

The publication collector should retain its fixed source panel, full-body provenance, deduplication, documented exclusions, and collection outside the scoring chain. Add the missing contract between collector and scorer: an observed document count is not proof of complete exposure. The scorer already requires explicit complete-inventory and complete-bill-reference-search coverage certificates before producing calibrated F. A seed list drawn from a press cache cannot establish that completeness by itself. [Collector exposure rule](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/audits/legislative_effectiveness_shadow_20260911/COLLECTOR_CONTRACT_CU_PUBLICATIONS_2026-09-12.md:19>), [scorer's coverage requirement](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/fec/legislation/build_bill_impact.py:177>).

Keep NCUA as a separate regulator family. Keep unavailable or incomplete paywalled sources outside the calibrated panel until usable coverage exists. Assess archival CUNA/NAFCU coverage if the 118th term will support calibration. Freeze source and bill-age windows before scoring historical attention; later publicity must not leak into an earlier snapshot. Treat attention as a significance proxy, not direct economic benefit or causal impact.

Resolve article identity before scaling collection: the contract counts substantive updates as new publications, while the registry merges records sharing a canonical URL. Store origin publication, version, and syndication identities explicitly, and test same-URL updates. Also map collection timestamps to the scorer's `available_date`/`observed_date` fields. Existing date guards are useful, but missing availability fields do not establish that the evidence existed at a historical cutoff. These are contract boundary risks, not demonstrated production leakage. [Registry behavior](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/fec/legislation/build_bill_impact.py:80>).

Check embedded provisions as a distinct coverage improvement. The Center for Effective Lawmaking's methodology now credits sponsored language substantially incorporated into other enacted vehicles. A standalone-bill-only outcome registry may miss this route. That is a reason to assess lineage coverage, not to transfer the Center's validation to Melange or award automatic duplicate credit. [Official methodology](https://thelawmakers.org/methodology).

## 7. Execution order and acceptance conditions

1. Preserve the frozen status record and issue an annotated correction. Replace the activation draft's ambiguous objective with the agreed P/E/V hierarchy and explicit missingness rules.
2. Build the unique opportunity registry and efficiency calculation in an isolated candidate. Preserve existing primacy judgments; define beneficial volume and record excluded/unknown cases.
3. Test the actual decision properties: lower-priority criteria cannot overturn higher ones under the literal hierarchy; duplication cannot raise volume; unchanged conversion with more observations improves evidence rather than the raw rate; additional mature failures cannot raise conversion; late joins cannot claim earlier milestones; missing inputs cannot receive best-case scores.
4. Recompute the full frozen roster, including zero, sparse, unavailable, chamber-switching, and partial-service records. The earlier blend used 352 eligible members; its listing is not proof of behavior under a new 533-member fallback policy. Explain every mover with P, raw efficiency numerator/denominator, evidence adjustment, V, and rule version.
5. Complete suite registration and source-contract repair, inspect all existing failures, verify generation consistency and conduct/crown rules, and prove deterministic rollback before activation. The status's reported 77/77 lane tests and kernel 187/4 are historical receipts, not results rerun for this review.
6. Use the already examined 118th/119th evidence for development. Freeze the new method before evaluating an untouched later window. Report House and Senate coverage and performance separately; historical agreement alone is insufficient.

The design preserves the useful engineering work while changing the decision objective to match the requested priorities. It does not claim an empirically optimal calibration, a new final member ranking, or completed production implementation.
