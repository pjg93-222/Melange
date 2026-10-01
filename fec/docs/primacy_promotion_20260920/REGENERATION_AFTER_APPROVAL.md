# Regeneration after the approved interview cleanup

Paul answered **“Yes”** to the prepared, backed-up four-row cleanup after reviewing its scope and the fact that two passages genuinely repeat in their source broadcasts. This resolves the owner-approval requirement recorded in STATUS.md; those earlier verification results remain a historical record.

The live cleanup removed exactly rowids 103939, 189056, 190576 and 193063 from `speeches`, reducing its count from 271,255 to 271,251. A complete SQLite backup was saved before the transaction at `tmp/primacy_promotion_20260920/social_media.before_four_row_cleanup.db`. Every unique statement remains represented.

A read-only full-table comparison against that backup confirms unchanged schemas and identical rowids and values in every other record across all 15 tables. The exact row plan, transaction receipt and comparison receipt are retained in the same local evidence directory.

The canonical full pipeline was restarted from its first step without bypassing intake or changing scoring rules. Its output is in `pipeline_after_cleanup.log`; final publication and audit status is recorded in [STATUS.md](STATUS.md).

The collection gate passed in 279.3 seconds: **ACCEPTED, zero errors, zero interview duplicate groups**, with 153,572 interview turns retained. The press feed rebuilt with 291 stance rows and 21,877 typed official mentions across three accepted runs. The audio adapter rebuilt its 6,911-item partition (784 queued, 6,127 excluded); its candidate stage did not promote unreviewed audio evidence.

The first resumed chain rebuilt the engine inputs, honors and workbook, then stopped at the profile claim gate. The runner was resumed from the repaired profile producer, then from the repaired industry producer as detailed below.

## Profile evidence repair

The current ledger no longer supports repeated floor-defense claims for Pramila Jayapal (defense percentile .424) or Susan Collins (.199). The preserved source profiles asserted the opposite, so the existing mechanical gate correctly rejected them. The repair in `9082804cd` omits whole sentences carrying that unsupported claim when its existing evidence gate is absent, records every omission, and runs all existing claim gates afterward. It generates no new personality prose and does not change evidence thresholds.

The complete candidate passes all 533 current-evidence gates. Exactly three sentences are omitted across two profiles; the remaining 531 source profiles are unchanged. The five new tests cover preserving supported claims and unaffected bytes, removing dependent advice, refusing an empty paragraph and retaining unrelated failures. Their suite is registered in the kernel. The source narratives remain archived, and the active artifact is still published only through its normal producer and receipt.

The canonical resume command is `fec/run_pipeline.py --from regenerate_member_profiles.py`; its output is retained in `pipeline_after_profile_repair.log`.

## Industry publication integration

The profile resume rebuilt the dashboard and then stopped at a historical hard-coded `.25` pin in `industry_tiers.py`. The runtime and current factor artifact both correctly carry diagnostic K=0; the extra pin still required the legacy value. Commit `7fe4de76b` makes that pin method-aware while preserving runtime/artifact agreement and refusal of unratified values.

Bank, crypto and fintech remain on their previous factor-only arithmetic with K=.25; the CU diagnostic adoption is not silently extended to those boards. The shared globals are restored even on a failed compute. A same-input comparison against the unmodified producer matched every output field for all 533 members in each of the three non-CU industries. The CU board independently matched all 533 canonical ranks and tiers. All 32 industry-valence tests pass, including selected-method and scoped-state regression coverage. Independent adversarial review approved the production diff; its one mock-signature finding was repaired and the suite rerun successfully.

The next canonical resume command is `fec/run_pipeline.py --from industry_tiers.py`; its output is retained in `pipeline_after_industry_repair.log`.

The cosponsorship forecast detected eight changed input hashes and successfully rebuilt in 208.9 seconds. This resolves the earlier stale-forecast condition through its proper producer.

## Input-driven movement against the frozen approval

An isolated replay retained all inputs from the approved diagnostic snapshot except the current member bill-role bundle, current reporting-rank input and grade date (September 19 to September 20). It exactly reproduced the entire current factor document, grade document and all 533 seats. The regenerated bundle has bill-role changes for 191 members; agenda credit changes for 173, shifting the common roster baseline from .482222 to .481361. The full member/act changes are in `refresh_purity_receipt.json`.

The honors board has 338 rank differences from the frozen approved diagnostic but retains the same 13 Tier 1 members. Kim remains 11, Barr 38, Daines 29, Golden 37 and Cuellar 47. Barr remains naturally 15/Tier 2 when the conduct adjustment is removed in an isolated diagnostic. This is an input-driven regeneration under the same approved method, not an assertion that all frozen numeric placements remain fixed forever. Final factor and grade documents, plus all 533 seats, match the isolated replay exactly. The canonical tiers, dashboard and member desk agree for all 533 published members; the surface honors guard, live alias sync and source-to-dashboard audit also pass.

The email packages regenerated successfully. Compared with the old live honors board, 511 ranks and 29 tiers changed. The separate four-pillar reporting ranks have 21 movements; their score and component-percentile deltas are recorded separately in [BOARD_MOVERS.md](BOARD_MOVERS.md), alongside every honors-board row. They are not presented as effects of changing the primacy method.

## Findings during the resumed chain

The descriptive-speech step refused a stale local YouTube verification input receipt after 251.2 seconds. The canonical runner explicitly treats this display-only step as tolerant and retained its bound last-good artifact/receipt. A direct hash comparison isolated the mismatch to `data/speech/local_youtube_turn_candidates_v1.jsonl` (expected `85ce697e2813cefcd64bf1912a179141b47bf9ed853533c83659819a967d9c9e`, observed `e724d093c5e7cd3e4d7a7e4680cec400d18998b5675e1087f3f9a696b883b8da`). The speaker-anchor receipt, anchor vectors and model manifest still match. The candidate file's observed mtime is August 31, before the interview cleanup. No receipt hash was hand-edited or bypassed.

The intake's audio audit rechecks 6,911 clips totaling 95.558 hours and computes PCM RMS with a Python per-sample sum. A possible later optimization is an exactly equivalent, overflow-safe integer accumulation; it must preserve file-hash, audio-format and RMS checks. This is a performance observation, not an implemented change or a measured speedup claim.

Additional ACU context found while the chain ran is documented in [ACU_FOLLOWUP.md](ACU_FOLLOWUP.md). It adds no scoring inputs.

Paul subsequently accepted Golden at 37 and Cuellar at 47 and asked what the press evidence says. [The statement-level review](GOLDEN_CUELLAR_PRESS.md) covers all 18 admitted occurrences, whose archived text hashes were verified against the committed ledger. Their signed weighted ratios are .3203498229 and .6643025799 respectively. Acceptance of the placements does not imply a new ruling on each classification or intensity weight.
