# Melange: behavior-qualified rank labels

The later [overall tier and standing reconciliation](OVERALL_TIER_IMPLEMENTATION_REVIEW_2026-09-12.md) completes overall treatment while preserving the subfield policy below.

Date: 2026-09-12 (America/New_York). Originally a proposal following a read-only audit; now implemented and reviewed after the user's instruction to proceed. The implementation uses the proposed fixed 5% Champion default. See [implementation and review results](TIER_RANK_IMPLEMENTATION_REVIEW_2026-09-12.md) for the published generation, validation and limitations. The proposal below records the design rationale at planning time.

## 1. Recommended design

Make an earned label the result of three explicit operations: **verify action in the field → rank eligible members on their field record → apply a rank cutoff**. Publish the evidence, rank, denominator, and label together from one authority.

The user specified overall Champion = top 13, behavior required in the relevant field, subfield ordering by rank, tensor used only to break ties, and no rank-weight normalization. The user subsequently confirmed that **subfield Champions are the top 1–5%**; Ally remains cumulative top 15% and Highly Persuadable cumulative top 20%. The Champion label and 1–5% range are confirmed. This plan uses a fixed **5% proposed cutoff** for its formulas and examples; the exact cutoff within the confirmed range has not been selected by the user. Selecting another fixed value within 1–5% changes one policy parameter; do not vary the cutoff by category to obtain desired names or counts.

| Recognition | Qualification | Scope |
|---|---|---|
| Overall Champion | One of the authoritative overall board's first 13 qualified members | Overall credit-union record |
| Subfield Champion | Positive observed field record; top 1–5% of the field's eligible cohort, with 5% proposed for this implementation | That field only |
| Subfield Ally | Same evidence requirement; within the first 15%, after excluding Champions | That field only |
| Subfield Highly Persuadable | Same evidence requirement; within the first 20%, after excluding higher recognitions | That field only |
| No earned recognition | Observed behavior, but below a cutoff or without positive net support | Evidence remains visible |
| No recorded action / Evidence unavailable | No qualifying observed action / required source cannot be evaluated | No rank or earned label |

These are cumulative boundaries. In a hypothetical 100-person field with positive scores and no boundary ties, there are 5 Champions, 10 additional Allies, and 5 additional Highly Persuadable members—not 5 + 15 + 20.

Keep three concepts separate in the data model: **earned recognition**, **observed alignment**, and **modeled persuasion**. “Highly Persuadable” is retained as the requested recognition name, but a rank does not establish a probability of persuasion. Do not convert the new rank bands into persuasion probabilities. The UI should explain the rank qualification; any actual persuasion forecast keeps its separately named model output.

## 2. What is wrong today

### Observed saved-data findings

The final audit receipt captured inputs at 2026-09-13 01:13 UTC / September 12 21:13 Eastern. The saved category labels and legislative/vote artifacts inspected were last modified on September 8. This is a census of those local artifacts, not a claim that all real-world activity through September 12 has been collected. The census covers **533 members × 18 categories = 9,594 member–field cells**. Input hashes and modification times matched before and after the audit, and all four action-source hashes embedded in the category-label artifact matched the current files. Counts below are pooled across chambers and parties; they describe data consistency, not estimated behavioral effects.

Source: [audit receipt](audits/tier_rank_plan_20260912/tier_input_audit.json), reproducible with [audit_tier_inputs.py](audits/tier_rank_plan_20260912/audit_tier_inputs.py).

| Finding in that snapshot | Measurement and interpretation |
|---|---|
| Labels can exist without either form of recorded action | 443 of 9,594 cells have a label but neither a selected legislative routing row nor a category-vote record with `n >= 1`. Of those 443, 20 are Ally and 9 Highly Persuadable; 204 carry one of the five positive label names. This is absence in these sources, not proof that the member never acted. |
| Real voting behavior can be hidden by the label gate | 1,513 of 9,594 cells are blank despite a category-vote record with one to four votes and no selected legislative row. These aggregate vote records still require event-level reconciliation for the new ranking. |
| Top labels are numerous and do not mean top ranks | Of 9,594 cells, 1,325 are Champion, 37 Defender, 1,794 Ally, and 224 Highly Persuadable. These are outputs of the old score rules, not eligible-cohort percentile awards. |
| A failed action test still produces a positive title | 76 cells in the snapshot were explicitly capped from a raw top label to Ally. |
| Some fields have no supportive basis in the inspected action sources | Interchange has 18 distinct members with selected legislative action, but no positive selected legislative contributions or qualifying net-aligned vote records under the audit's `lean >= .5, n >= 1` corroboration check. A rank-only rule must not award supportive honors to the least negative record. |
| Tensor coverage is sparse | The inspected ledger contains 15 active CU tensor cells keyed by measure and Congress, with no category key. A complete per-member, per-field tensor ranking does not currently exist. |

### Source-level causes

| Cause | Code evidence | Consequence |
|---|---|---|
| Mixed classification systems | `fec/stance/stance_rules.py:11–20, 28–33, 106–142`: fixed score bands, except four categories transformed by separate signed empirical curves | Identical-looking titles have different qualifications by field. A `.70` threshold on a curve is not a top-5% rule. |
| Media qualifies as behavior | `fec/stance/per_category_stance.py:60–69`: `has_leg or has_press or hv`; `stance_rules.py:59–65`: present-source weighted mean | With media alone, the nominal media weight cancels out of the denominator. “Diminished” media can therefore supply the entire cell score. |
| Action gate is applied too late and too narrowly | `fec/moneyball_core.py:711–727` | Only Champion/Defender are checked; failure becomes Ally. Other positive labels pass through. |
| Score/rank/label divergence | `per_category_stance.py:63–101`: compression, cross-domain rounding, overall anti floors, curves; `fec/surfaces/make_member_desk.py:1414–1421`: separate rank sort | The shown rank is not the rule that earned the shown label. |
| Everyone receives a local field rank | `make_member_desk.py:1415–1421` sorts every member in `SCORES`, without field eligibility or tensor | Zero, missing, and genuine ties receive misleading distinct positions; equal values follow input order. |
| Labels are computational inputs | `moneyball_core.py:431–434, 486–560`; `fec/engine/per_topic_flip.py:68–75`; `fec/engine/budget_frontier.py:76–80` | Replacing label strings in place changes coalition seeds, allocation, persuasion, and overall calculations. |
| Browser has the same coupling | `fec/surfaces/templates/make_dashboard_html_00.tpl:530–556, 685` uses `DATA.stance` in simulation | Separating only the Python implementation would leave browser and batch behavior inconsistent. |
| Stale overall terminology | `moneyball_core.py:503–559` and emitted metadata still say Legislative+Press Tier 1; `fec/tier_util.py:594–666` actually defaults to the primacy-factor board | Explanations name a retired scoring basis. |

The current legislative action substrate is useful: `build_archive_legislative.py:242–265` selects one preferred role per member/measure/Congress/category and sums signed role × decay. The audit found 8,073 selected rows and no duplicate selected member/measure/category keys under its checked key. Reuse this accepted evidence, rather than rebuilding eligibility from press scores or UI ranks.

## 3. Preserve the authoritative overall top 13

Overall Champion should be a projection of the active overall board, never an average of the new field honors and never the top 13 in `ranks_python.json`'s separate four-pillar reporting rank.

There is a relevant pending change. Project decision D-028 and [activation contract v2](audits/legislative_effectiveness_shadow_20260911/ACTIVATION_CONTRACT_2026-09-12_v2.md) authorize the overall board formula `P × (0.80 + 0.20 × L)` and reporting Leg% = `L`. The contract explicitly says it is not active. Its v1/results-only predecessor is superseded. The inspected default live board remains `factor`.

This plan consumes **whichever versioned board is actually active**. It does not activate D-028, copy its chamber percentiles into field honors, or alter its coefficients, conduct rules, evidence floor, or tie order. Store `overall_board_mode` and the board generation with the crown. This resolves the apparent conflict: “no rank-weight normalization” governs the new field-label process; the separately authorized overall-board policy is outside this change.

Before publication, independently verify that every top-13 member has qualifying overall CU action evidence. Missing evidence files, a future manual placement, or the existing fail-open floor (`tier_util.py:565–591`) must not silently prove behavior. If the board's 13 members cannot pass that check, fail the candidate publication with their reasons; do not invent evidence or silently substitute a different board. If the entire valid overall cohort has fewer than 13 people, publish no padded top-13 release. A future “up to 13” rule would be a separate explicit policy change.

Keep exactly one Overall Champion badge. An overall Champion can have no observed action in a particular field and receive no field rank or label. A subfield Champion need not be an overall Champion.

Other overall honors were not specified. Do not invent percentage bands for overall Ally or Highly Persuadable. Replace ambiguous public “General Stance” honor usage with the overall crown plus an explicitly named observed-alignment summary; preserve the old analytical ladder for the existing engines under a distinct internal field.

Define that summary from the normalized accepted action records, never from the legacy ladder: **Supportive actions** when positive actions exist and negative actions do not; **Opposing actions** when negative actions exist and positive actions do not; **Mixed actions** when both exist; **Neutral actions** when only explicitly neutral actions exist. No qualifying records gives **No recorded action**; unavailable required data gives **Evidence unavailable**. Count a multi-category event once for this overall summary, using its accepted overall CU direction; unresolved conflicting directions block the summary. Field summaries use the same vocabulary over that field's records. Show counts and the evidence window. These descriptions do not add honors or imply a probability of persuasion. Legacy Champion/Ally/Highly Persuadable/Defender ladder names are never rendered as an alternative public earned ranking.

## 4. Exact subfield policy

The following defaults make the proposal implementable. Action types, vote weight, positive-support gate, and residual-tie handling are recommendations, not claims about already ratified policy.

### 4.1 Eligibility and cohort

Use a frozen active roster, canonical category IDs, an explicit as-of date, and a declared evidence window. Recommended first version: Congresses 117–119, the terms represented in the current bill/vote inputs, with the existing Congress-decay schedule. Inventory out-of-window rows before activation; do not silently mix an all-history source with a current-term source. This field window is independent of the pending D-028 term aggregation.

A member is eligible in field `c` when at least one verified, deduplicated, in-window action belongs to `c`:

- Sponsorship, original cosponsorship, or later cosponsorship that remains accepted under the official membership policy.
- A recorded substantive final-passage Yea/Nay vote, with accepted measure/category/direction mapping. One verified vote is action; there is no `n >= 5` eligibility test. Use event rows, not an aggregate lean as if it were an event.
- A verified signed policy letter already admitted to the legislative ledger. An article saying the member supports a position is not a signed letter.
- Eligible amendments only where already admitted by the existing measure policy; retain their canonical identities and declared weights rather than inferring a new family rule.

Press, speech, committee membership, party, demographics, donations, model predictions, overall rank, and tensor availability cannot make a person eligible. A withdrawn membership does not remain current support; retain its history as evidence, but apply the existing accepted-membership policy to current qualification. Do not infer withdrawal from missing collection.

Use Bioguide or the existing validated stable member ID. Reject unresolved member IDs and category IDs. Normalize aliases at the source adapter, not by joining display names opportunistically.

Deduplication keys:

- Legislative role: `(member_id, congress, canonical_measure_id, category_id)`, keeping the preferred current role once.
- Vote: `(member_id, congress, chamber, rollcall_id, category_id)`, with a separate canonical measure reference. Count a duplicate ingestion once; distinct valid final-passage votes remain separate recorded actions.
- Letter: `(member_id, canonical_letter_id, category_id)`.

A sponsorship and a vote are different actions. Category assignments must come from accepted routing; duplicate category rows are not extra actions. Do not collapse distinct companions across chambers without an explicit existing policy.

The evidence adapter must also recover verified neutral-only participation. `build_archive_legislative.py:220–235` records `neutral-official-evidence` and `neutral-registry` dispositions with zero contribution before the `selected` aggregation. Admit these only after verifying accepted in-category membership, an explicit neutral direction, and source provenance; apply the same preferred-role deduplication and record zero primary contribution. Do not admit a row merely because its disposition contains “neutral”: excluded, off-topic, unresolved, and rejected records stay outside the cohort. Keep signed subtotals reconciling to `archive_leg.json`. The audit census above deliberately used the narrower selected-row/vote definition, so its diagnostic denominator is not a final count of this proposed broader cohort.

Let `E_c` be all eligible members and `N_c = |E_c|`. Include positive, negative, and offsetting records in this denominator. Exclude members with no observed field action. Compute the cohort before looking at recognition labels or tensor availability. Search, party/chamber filters, and hiding rows do not recompute it. This proposal uses one combined active-roster cohort per field, as requested; report House/Senate counts and award distributions in the rollout review so chamber opportunity differences are visible. Do not silently add chamber-normalized field scores or quotas.

Distinguish `observed`, `no_recorded_action`, and `unavailable`. Real opposing actions that cancel to zero remain observed. A source failure is unavailable, never zero or no action. A required-source failure blocks a new generation; retain the prior valid generation with its date.

### 4.2 Primary field order: raw action contribution

There is no authoritative behavior-only field rank to plug in today. The existing desk rank orders mixed stance scores. The plan therefore needs a declared primary measure before a percentile can mean anything.

Recommended version `field_action_sum_v1`:

`S[m,c] = sum(alignment[e] × action_weight[e] × decay[e])`

Here `alignment` is the accepted CU-aligned direction of the member's actual action, in `{-1,0,+1}`. Use the existing selected legislative contributions for bill/letter rows. Their current role weights are sponsor **3**, original cosponsor **2**, later cosponsor **1** (`fec/bill_rules.py:211–219`), with the existing stored/letter Congress decay. Do not substitute the primacy model's different 1/.5/.25 role schedule.

For newly integrated event-level votes, propose weight **1** per accepted final-passage vote, with the same Congress decay. This is a new comparability assumption, not a coefficient found in the current aggregate vote model. Before activation, show the label changes and vote-only recipients at vote weights 0.5, 1, and 2; choose by the intended meaning of an action, never by preferred member outcomes. Weight 1 is the concrete default in this plan. Do not let vote-only members enter the cohort and then silently give them an archive-only score of zero.

Rank `S` descending. No square root, clipping, min-max scaling, percentile score conversion, rank normalization, present-source renormalization, cross-field rounding, overall-stance floor, or media term enters this order. Existing action/decay weights define the raw legislative measure; they do not become rank weights. A percentile is used only later to compare an ordinal position to a cutoff.

Use exact decimal arithmetic over canonical input literals, preserving the current decay precision. Compute before presentation rounding, and verify the selected-row subtotal against `archive_leg.json` within a declared conversion tolerance. Do not treat `2.4000000000000004` versus `2.4` as different merit. The conversion/precision convention belongs in the policy and must be covered by a test.

### 4.3 Tensor is a secondary key only

For a primary-score tie, use a field-local secondary quantity over the same actions:

`T[m,c] = sum(action_weight[e] × decay[e] × position_on_measure[e] × tensor_cu[measure(e)])`

`tensor_cu = relevance × valence`, using the existing active adjudicated CU tensor cell. Confidence remains provenance; the current tensor loader does not multiply it into the effective weight (`fec/engine/primacy_factors.py:111–194`). No tensor value, overall `factor_ranked`, or normalized tensor percentile enters `S`.

Avoid a sign bug: `position_on_measure` is support for the measure (`+1`) or opposition to the measure (`-1`), not the already CU-aligned direction. A Nay on a CU-adverse bill reverses the signed tensor once. Multiplying an already aligned direction by signed valence would double-reverse adverse bills. A letter is usable only when its scoped position and tensor mapping are explicit.

Order by **`S descending`, then `T descending` only within equal `S`**. Never calculate `S + epsilon*T` or a weighted blend. Tensor changes must be mathematically incapable of reversing unequal primary scores.

The current ledger is sparse. A missing tensor cell is not zero; zero is a real assessed value. For each equal-`S` block, apply tensor ordering only if every required action for every member in the block has a usable, correctly scoped tensor cell. Otherwise leave that entire primary block tied and record `tensor_unavailable_for_tie`. This group-level rule is deterministic; pairwise “ignore missing” comparisons can be non-transitive. Do not silently use `primacy_factors.act_weight()` fallbacks and call them observed tensor values.

Coverage will therefore limit how often tensor resolves ties in version 1. Report unresolved boundary groups and missing measure IDs. Adding adjudicated tensor cells later is a data update with its own before/after record; do not manufacture values to fill a tier. No tensor coverage is needed to rank members whose primary scores differ.

### 4.4 Exact thresholds, small cohorts, and remaining ties

For percentage `p` in `{5,15,20}`, define `K_p = floor(p × N_c / 100)`. These are maximum rank boundaries, not quotas that must be filled. There is no forced minimum award and no backfill outside the boundary.

After primary and, where available, tensor ordering, members still tied on merit form a group with `rank_start` and `rank_end`. **Give the whole group the highest label whose cutoff contains its `rank_end`.** This conservative honors rule keeps equal merit equal and respects the stated top-X% ceiling. It can leave a band partly empty. It neither expands a boundary nor uses an arbitrary ID to award one person and exclude another. Use stable ID only to arrange equal rows visually.

Also require `S > 0` and at least one positive qualifying action for supportive recognition. This proposed safeguard prevents an all-negative field from producing Allies. Zero/negative members retain their evidence and rank in the demonstrated cohort but no positive honor. Do not turn low rank into Opponent or assume a net-zero record means indifference.

```text
if evidence unavailable: no rank; no honor; block new generation
elif no qualifying field action: no rank; no honor
else:
    establish primary-score groups within the eligible cohort
    resolve each group with tensor only when that whole group has coverage
    calculate each remaining group's rank_start and rank_end
    if S <= 0 or positive_action_count == 0: no supportive honor
    elif 100 * rank_end <= 5  * N: Champion
    elif 100 * rank_end <= 15 * N: Ally
    elif 100 * rank_end <= 20 * N: Highly Persuadable
    else: no earned recognition
```

Examples assume positive records and no ties unless stated:

| Hypothetical field | Cutoffs C / A / HP | Result |
|---|---|---|
| `N=100` | 5 / 15 / 20 | Exclusive bands 1–5, 6–15, 16–20 |
| `N=37` | 1 / 5 / 7 | 1 Champion, 4 additional Allies, 2 additional HP |
| `N=18` | 0 / 2 / 3 | No Champion; ranks 1–2 Ally; rank 3 HP |
| `N=1` | 0 / 0 / 0 | Observed and ranked, with no percentile honor |
| `N=100`, residual tie at 5–7 | 5 / 15 / 20 | All three are Ally; four Champions remain |
| `N=100`, all records tied | 5 / 15 / 20 | All share rank interval 1–100; none earns a top-20% distinction |
| `N=100`, all scores negative | 5 / 15 / 20 | No supportive honors |

“Top 5%” does not guarantee a Champion in a field with fewer than 20 actors. This is the necessary consequence of a strict percentage threshold, not an error to fix with rounding upward.

## 5. One canonical recognition artifact

Add a pure policy module, a normalized action builder, and a producer:

- `fec/stance/rank_honors_policy.py`: policy IDs, exact arithmetic, eligibility/rank/tie/label functions; no file reads at import.
- `fec/stance/build_field_action_evidence.py`: accepted legislative rows plus verified event-level votes and letter provenance, with stable identities and validation receipts.
- `fec/stance/build_rank_honors.py`: creates a versioned generation of `rank_honors.json`, an evidence reference table, and a transition report.
- `fec/stance/honors_views.py`: shared validated loader/accessors for workbook, dashboard, and member desk.

Each generation records schema and policy versions; as-of and Congress window; roster/category IDs and hashes; input and producer hashes; active overall board mode/generation; field cohort sizes; cutoff counts; coverage failures; and all boundary ties.

Each member/field record includes:

```json
{
  "member_id": "<stable-id>",
  "category_id": "<canonical-id>",
  "evidence_status": "observed",
  "action_count": 4,
  "positive_action_count": 3,
  "negative_action_count": 1,
  "raw_field_score": "4.8",
  "tensor_tiebreak": null,
  "tensor_status": "incomplete",
  "rank_start": 8,
  "rank_end": 8,
  "cohort_size": 112,
  "cutoffs": {"champion": 5, "ally": 16, "highly_persuadable": 22},
  "recognition": "Ally",
  "reason": "within_ally_rank_cutoff",
  "evidence_ids": ["<accepted-event-id>"],
  "policy_id": "field_rank_honors_v1"
}
```

The JSON above is an illustrative shape, not a measured member. Provide explicit `reason` values for no action, unavailable source, nonpositive record, below cutoff, and unresolved boundary tie. A tied range is not flattened into an unexplained unique rank. Validate the observed counts against distinct normalized evidence IDs.

Publish to an immutable generation directory and atomically replace a small active-generation pointer only after validation. A label, rank, denominator, and evidence table from different generations must fail validation. Source snapshotting is essential: Python modules that read mutable global files repeatedly can otherwise build an internally inconsistent generation.

## 6. Consumer changes and compatibility

| Area | Implementation |
|---|---|
| Existing stance producer | Keep `category_stance.json` as the legacy analytical input during migration; explicitly name its accessor `analytic_stance`. Its curves/caps no longer define public earned honors. |
| Core engines | Inventory every direct matrix/label read in `moneyball_core.py` and `fec/engine/`. Route through explicit analytical accessors. New honors never enter `PERS`, `TORD`, salience, seed selection, or overall weighted-tier averaging by accident. |
| Dashboard data and browser | Add separate `honors`/`overall_honors` payloads. Retain distinct `engine_stance`/`engine_overall_stance` inputs for JavaScript simulations. Update both producer and JS call sites before displaying new labels. |
| Member desk | Replace `category_ranks()` and exported `adjrank` authority with canonical honor ranks. Read the same record for badge, rank, denominator, and tooltip. |
| Workbook | Update `sync_stance_g.py` and `workbook_stance_views.py`: dedicated earned-recognition columns/sheet, matching legends, counts, styles, and evidence/rank fields. Preserve existing analytic input cells until their readers migrate. Do not change an engine's cell meaning in place. Public “General Stance” presentation must no longer imply that the analytical ladder is the earned recognition. |
| Audit workbook and exports | Update `build_audit_workbook.py`, dashboard/email builders and combined-page builders. Include policy/generation and evidence links or IDs. Exports use canonical labels, not Excel or JS reclassification formulas. |
| Overall crown / industry boards | Project only the active canonical top 13. Check `champions_v2.py`, industry-board exclusivity, and cross-sector crown checks. Other sector board scoring is outside this task. |
| Documentation | Replace public references to curved tiers, cap-to-Ally, and Legislative+Press crown. Describe rank qualification, action window, and the active overall board. Update README and mathematical specification at implementation. |

Example display: **Ally · 8 of 112 with recorded action**. Detail: “Ally cutoff: rank 16. Four recorded actions. Evidence through [date].” For a tie: “Tied 5–7 of 100; Ally; Champion cutoff 5.” For a field with no action: “No recorded action in this field.” Keep policy/version machinery in details and exports rather than crowding the main view.

Retire Defender as a competing field honor; where relevant, show “Defensive action” as a factual action-type descriptor. A defensive action and a Champion rank can coexist without creating two parallel ladders. Maintain the old Defender value internally only for legacy model compatibility.

## 7. Implementation sequence and deliverables

1. **Freeze the baseline and policy.** Capture source/code hashes, full current overall board, reporting ranks, labels, field scores, and model outputs. Complete the event inventory and source reconciliation. Record the selected Champion cutoff, vote coefficient, window, and conservative tie rule. Use the current audit as diagnosis, not as an automatically trusted activation baseline days later.
2. **Build and verify normalized field evidence.** Reconcile selected signed rows to archive totals and import validated neutral participation as specified above; join canonical event-level votes from `votes/cu_rollcall_votes_clean.csv` through the maintained `build_vote_category.py` mapping policy. Verify actual cast codes, paired/announced votes, abstentions, and duplicate rollcalls explicitly; only actual qualifying Yea/Nay actions count in this proposal. Emit rejected/pending/withdrawn counts and evidence links. Do not activate an aggregate-only vote fallback.
3. **Implement the pure honors classifier.** Add policy, integer-safe cutoffs, group-level tensor handling, exact tie intervals, and positive-support guard. Produce all field honors in a candidate generation. Generate a per-member/per-field transition report with old label, new label, old display rank, new rank interval, denominator, boundary, and reason.
4. **Separate analytical and public consumers.** Update Python and browser accessors together. Before the display switch, prove that candidate honors cannot change the analytical inputs or model outputs. Make the distinction explicit at the schema level, not a naming convention only.
5. **Wire all public views to the candidate.** Build candidate member desk, dashboard, exports, and workbook views. Remove local reclassification/rank sorts. Compare every displayed badge/rank/denominator back to independently recomputed source expectations. Check representative and boundary records visually.
6. **Integrate the pipeline.** In `fec/run_pipeline.py`, place field evidence after its legislative/vote dependencies; place honors after its field evidence/tensor and active overall-board dependencies and before workbook sync/public renderers. Existing sequence is stance → pillars → primacy → sync → engines → public surfaces. Do not use a newly rendered member desk as the same-run upstream authority for honors. Reuse a validated prior-generation input only where the existing pipeline explicitly requires it and record that lineage.
7. **Review the candidate and switch a complete generation.** Deliver the full transition report, field/chamber counts, unresolved tensor boundary groups, engine-isolation evidence, and the 13-member crown comparison. Public labels change only after the implementation's candidate is reviewable. Do not rerun unrelated collectors or alter adjudicated bill direction/tensor values as part of label construction.
8. **Rehearse rollback.** `HONORS_MODE=legacy` selects the previous public generation; `field_rank_honors_v1` selects the validated new one. Restore workbook/public files as a matched bundle. Preserve the analytical matrix and its behavior in both modes. Prove rollback against the frozen same-input baseline, not against files that changed in an unrelated refresh.

Useful parallel implementation assignments: one evidence adapter lane; one pure rank-policy lane using fixed fixtures; one consumer lane against the agreed artifact schema. The consumer migration depends on the schema, and integrated publication depends on all three. Independent review should reconstruct the boundary results from action records without calling the production label function.

## 8. Acceptance criteria

1. Every public field honor has at least one qualifying field action and a positive raw action score. A media-only, committee-only, imputed, or unrelated-field record never gains an honor or enters that field's denominator.
2. One verified vote is eligible; event-level vote contribution is actually present in the primary measure. Aggregated `n=1…4` evidence is not discarded merely for being below five.
3. For each field, the published cohort equals the independently derived set of observed qualified member IDs. All thresholds use that cohort, not 533, total rows, positive-only members, or currently visible members.
4. For all awarded groups, `100 × rank_end <= p × N` at their awarded cumulative cutoff. Equal residual merit receives equal recognition; no stable ID can change an honor. Test N=0,1,4,5,6,7,18,19,20,37,100 and groups crossing each boundary.
5. Tensor mutation can reorder only equal-primary-score members. Test extreme positive/negative changes, numeric zero, missing coverage, and reversed input order. Partial coverage disables tensor for the entire primary tie block.
6. No cross-field leakage: modifying another field's actions, media, score, or honor cannot change this field's primary score or eligible membership. Adding an inactive roster member does not change the field's awards. Adding an eligible actor can legitimately change its denominator; the delta report explains that change.
7. Zero cancellation and verified neutral-only participation are observed, not missing. Test admitted neutral dispositions separately from excluded/unresolved records and verify they affect the cohort without changing signed archive totals. All-negative and all-zero fields produce no positive honors. Abstentions/absence and inferred positions never become recorded Yea/Nay actions.
8. Duplicate imports do not add action credit; role upgrades select the preferred role once; typed bill identities separate H.R. and H.J.Res. numbers and separate Congresses. Reordering input rows changes neither scores nor honors.
9. Overall Champion equals exactly the active board's top 13, with valid overall action evidence, across every surface. The reporting top 13 and field honors cannot create additional crowns. D-028 remains independently versioned and activates only through its own implementation.
10. Workbook, member desk, dashboard, email, and audit export agree on the same policy/generation, eligibility, rank interval, cohort, cutoff, and recognition for every emitted record. UI filters do not alter recognition.
11. Changing honors thresholds alone leaves analytical stance inputs, reporting ranks, primacy board, allocations, coalition seeds, modeled resistance, and Python/browser simulations unchanged for fixed inputs. A change fails this gate even if the public badges look correct.
12. Missing/corrupt required sources, malformed signed action data, conflicting identities/categories, mismatched generations, and nonfinite scores fail candidate publication. Last valid output remains identifiable and dated; there is no silent replacement by zeros.
13. Fixed-input rebuilds reproduce the same semantic artifact; timestamps are isolated to receipts. A rollback restores the baseline public bundle and engine parity.

Register new suites in `fec/tests/run_tests.py`. Retain and extend `test_workbook_stance_views.py` and engine/browser parity tests. Existing curve tests and `audit_full.py:1821–1839` cap-to-Ally assertions should remain attached to the preserved analytical model; add separate honors checks instead of weakening or deleting valid model checks. Update obsolete *public UI wording* assertions deliberately. If a later release retires the analytical classifier, that is a separate versioned engine migration with replacement tests.

This planning task did not run the production pipeline or mutate its outputs. Several existing producers execute work at import and some tests write workbooks; use pure fixtures and a staged root for implementation development, then the project's required live-tree gate with captured inputs when performing the authorized integration. A clean synthetic test result is not a claim about the live data plane.

## 9. Decisions to carry into implementation

| Item | Proposed default | Why it is explicit |
|---|---|---|
| Confirmed Champion range | Top 1–5%; fixed 5% proposed | User confirmed the label and range; the exact cutoff remains a proposed implementation choice |
| Primary rank basis | Signed raw field action sum, current legislative weights, proposed vote weight 1 | Existing displayed field rank includes media and score transforms |
| Evidence window | 117th–119th, frozen as-of, current decay convention | Different windows cannot silently share a denominator |
| Positive recognition | Require positive net score and a positive action | Activity can be adverse; rank alone cannot imply support |
| Residual merit tie | Entire group must fit cutoff; underfill permitted | Preserves equal treatment and strict percentage ceilings |
| Missing tensor | No tensor comparison for the whole equal-primary block | No fabricated zeros or hidden fallback classifications |
| Below-threshold activity | Evidence and rank shown; no invented lower honor | Low rank is not proof of skepticism or persuadability |
| Engines | Keep existing analytical behavior under explicit fields | Rank recognition is not a calibrated persuasion model |

Draft continuity update for the project brain (proposal record, not a new ratified decision): “2026-09-12: behavior-qualified rank-label audit and implementation plan completed in TIER_RANK_IMPLEMENTATION_PLAN_2026-09-12.md. Receipt: audits/tier_rank_plan_20260912/tier_input_audit.json. Production unchanged. User requests overall top-13 crown and behavior-only subfield rank thresholds, tensor secondary only, no rank-weight normalization. In a follow-up, the user confirmed subfield Champions at top 1–5%. A fixed 5% cutoff and the other enumerated implementation defaults remain proposed. Overall D-028 activation remains separate and its v2 contract supersedes v1.”
