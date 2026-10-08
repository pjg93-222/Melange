# Local classifier preflight — 76-source snapshot

Run phase: **before the physical-bounds guard**. Audited 2026-09-04 at 21:31:51 UTC.

The existing tokenizer-only preflight returned `FAIL_PREFLIGHT` (exit 1). No model weights were loaded, no model inference or API requests ran, and no canonical evidence or candidate artifacts were written. The source snapshot and classifier helpers were not changed by this audit.

Settings: CPU threads 2; at most 2 disjoint regions per recording; 1,800 seconds after each cue, with 90 seconds before it; 1,500 reserved output tokens; Qwen 2.5 1.5B context limit 32,768.

## Token fit

| Measure | Result |
| --- | ---: |
| Sources / members | 76 / 76 |
| Planned local generation regions | 85 |
| Regions fitting the token budget | 84 |
| Oversized regions | 1 |
| Token-fit sources before physical validation | 75 |
| Sources with two regions | 9 |

Sydney Kamlager-Dove (`sdzvbf6aEoo`) is oversized: **32,162 input + 1,500 reserved output = 33,662**, exceeding the model limit by **894 tokens**. The proposed region is 0–4,380.402 seconds. The transcript was not truncated and the gate was not lowered.

The nine two-region recordings are Cory Booker, James Lankford, Janice Schakowsky, Jerrold Nadler, Joe Neguse, Laurel Lee, Tammy Duckworth, Thomas Massie, and Tom Emmer. Thus these settings imply **85 hypothetical local generation calls, not 76**; this audit made zero generation calls.

## Coverage is not the same as token fit

Only **42 of 76** recordings put every transcript word inside their planned regions; **34 have partial transcript coverage**. Overlapping cue windows are merged, so 1,800 seconds is not a hard region ceiling: 35 planned regions exceed 30 minutes and two exceed 60 minutes. Scalise's full 3,034.39-second transcript fits at 22,922 input tokens, but fit alone says nothing about output completeness.

Across all 85 planned regions, including the oversized region, their intervals cover **76.06% of the WAV timeline**. This is not verified member-speaking time and was not actually processed by a model. Particularly partial examples are Herbert Conaway (12.4%), John Cornyn (14.3%), Johnny Olszewski (17.1%), Ted Cruz (26.4%), and Thomas Massie (29.2%).

The classifier must not describe these cue-centered excerpts as complete-recording analysis. Short trailing gaps can also reflect silence or untranscribed audio; this check does not determine what the omitted audio contains.

## Physical-bounds issue found after preflight

Margaret Hassan (`sq3snuBYQvE`) has a transcript ending at **1,326.34 seconds**, but the physical WAV header gives **1,324.605562 seconds**: **1.734438 seconds beyond the audio**. Her 8,289-token prompt passed the old token check, which did not validate audio bounds. This is the only apparent whole-WAV timeline coverage case and is **not a valid whole-recording coverage result**.

Root/QA is adding shared physical source validation to preflight and inference separately. This audit is explicitly **pre-fix**; it does not claim a post-fix rerun or clearance. Snapshot inputs remain unchanged.

All transcript hashes were checked by preflight. The supplementary geometry audit read WAV headers but did not rehash all 76 complete WAV files. All identity, complete-turn continuity, independent boundary-review, and human-review requirements remain unchanged.

The 1,500-token output allowance was only reserved mathematically; this test does not demonstrate that it is sufficient to return every complete turn.

## Reproduction and detailed results

Exact command, historical code hash, tokenizer/config hashes, source hashes, per-region token counts, and per-recording uncovered intervals are in [the machine-readable audit](roster_local_preflight_20260904.json).

Input: `C:/melange-data/longform_candidate_runs/roster-ready-20260904/ready_sources.jsonl`

Input SHA-256: `e7f8034541b8441d46c02cf365a690454774e24528b17ea0a3547f0e0919286f`

Executed classifier SHA-256, before the later guard change: `e9fb573c0031dc2305952ab4aa4e763c457323812e0f5888f36cb87cb06b4fd9`.

