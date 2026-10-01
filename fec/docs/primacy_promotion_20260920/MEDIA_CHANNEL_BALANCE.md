# Media channel units in the adopted diagnostic

This is a descriptive audit of the immutable 7,413-occurrence corpus, not a new scoring arm, validation result or change to the accepted board. It follows Paul's question about Golden and Cuellar's press evidence.

The model's media component contains five channels, including floor speeches, hearing remarks and interviews. Calling all of it press can obscure that composition.

| Channel | Occurrences | Covered members | Total admitted intensity mass | Share of total mass | Median occurrence intensity |
|---|---:|---:|---:|---:|---:|
| Social | 5,652 | 431 | 2,637.69800 | 84.106% | .46667 |
| Floor speech | 168 | 74 | 150.55000 | 4.800% | 1.00000 |
| Hearing | 187 | 64 | 187.00000 | 5.963% | 1.00000 |
| Interview | 25 | 16 | 25.00000 | .797% | 1.00000 |
| Official/association press | 1,381 | 317 | 135.90192 | 4.333% | .03000 |

Covered-member counts overlap. Mass is the sum of the ledger's `intensity_scaled` field before applying direction or beneficiary relevance. It is not the numerator, number of independent acts or percentage contribution to final ranks. The final statistic is computed per member, then normalized within chamber and blended into the grade; these corpus totals cannot identify its causal rank influence.

The median social occurrence carries about 15.6 times the intensity of the median press occurrence. Hearing and interview occurrences in this admitted corpus all have intensity 1.0. The 1,381 press occurrences are 18.63% of the item count but 4.33% of intensity mass.

The production media-blend source documents press intensity as the absolute `press_value`, capped at 3.0. Its comments explicitly describe tiny units around .03 and a previously rejected .25 floor that flattened all articles into a count measure. The diagnostic imports its frozen corpus's provided intensity values; it does not establish that different channel scales measure one common amount of advocacy. This source observation does not authorize reinstating that rejected floor.

For Golden, a supportive social occurrence carries .66667 intensity, while the official overdraft-opposition release carries .00562 before the shared-class multiplier. The adopted classifications separately zero general CFPB commentary in the signed numerator. These two mechanisms must be distinguished: beneficiary relevance and cross-channel intensity can each change the resulting ratio. See [the statement-level review](GOLDEN_CUELLAR_PRESS.md).

## Next decision to make explicit

The intended evidence unit should be settled before changing a coefficient: an independent policy statement, an event, a published occurrence, or intensity in a channel-specific instrument. A crosspost can increase occurrence mass without adding another independent commitment. Confidence can report that dependence separately from support share, consistent with Paul's preference that depth add confidence.

A future comparison should hold classifications fixed while examining the channel scales, and separately hold channel scales fixed while examining event duplication. Combining those changes would make it difficult to explain any movement. No new comparison is run or promoted in this note, and no member's preferred position is used to set a parameter.

Eligibility is a separate source of sensitivity: Golden's five admitted occurrences comprise four messages, so the retained crosspost helps him meet the five-occurrence gate even though its OFF_TOPIC class contributes nothing to the numerator. Reporting independent-message depth would expose this distinction without silently changing the adopted support-share arithmetic. Any alternative gate should be evaluated across the full roster rather than chosen for this one case.

Reproduction: group `fec/config/primacy_press_v1.ndjson` by `channel`, count rows and unique members, and sum/take the median of `float(intensity_scaled)`. Corpus SHA-256: `575478340702136c9d1858f6f38d20495aafa4712ceb8c3cc4a073387caa78d5`. Supporting production code: `fec/stance/build_media_blend.py`, press-intensity calculation around lines 398–402.
