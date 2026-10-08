# V3 diagnostic results

- Status: **COMPLETE**
- Receipts: **32/32**
- Clean primary receipts: **28/30**
- Repaired known v2 semantic failures: **7/8**
- Hidden mismatches detected: **1/2**
- Decision: **NO_GO_OR_INCOMPLETE**
- Production consumers: **0**
- Stored-turn grounding, selected cases: **2/10 in v2 -> 9/10 in v3 A/V**
- Unavailable-modality discipline: **10/10 audio-only; 10/10 visual-only**

## Hard gates

- FAIL - `all_30_primary_clean`
- PASS - `seven_of_eight_failures_repaired`
- PASS - `both_sentinels_grounded`
- FAIL - `both_hidden_mismatches_detected`
- PASS - `at_most_one_false_mismatch`
- PASS - `zero_prohibited_inference`

## Receipt issues

- `F004-audiovisual`: audio_interval[0].end: timestamp_out_of_bounds:116.5, audio_event[0].end: timestamp_out_of_bounds:116.5, audio_event[1].start: timestamp_out_of_bounds:117, audio_event[1].end: timestamp_out_of_bounds:122, visual_event[0].end: timestamp_out_of_bounds:117, visual_event[1].start: timestamp_out_of_bounds:119.5, visual_event[1].end: timestamp_out_of_bounds:125, evidence[1]: timestamp_out_of_bounds:120
- `F020-audiovisual`: visual.displayed_text_type
