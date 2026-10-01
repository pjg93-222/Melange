# Melange rank recognition — implementation and review

Historical report for the initial field-recognition release. Its overall treatment and dashboard tier controls are superseded by the [overall tier and standing reconciliation](OVERALL_TIER_IMPLEMENTATION_REVIEW_2026-09-12.md).

Implemented and published on 2026-09-12 (America/New_York), following the request to implement the proposed plan and review it. Active generation: `daf1f6b94dcc65148fac534d`; evidence as of 2026-09-12.

Overall Champion is exactly the active overall board's top 13, with qualifying action verified for every recipient. Subfield Champion uses the plan's fixed 5% default within the confirmed 1–5% range; Ally and Highly Persuadable use cumulative 15% and 20% cutoffs. A member must have accepted action in the particular field before receiving a field rank or recognition.

The implementation ranks the raw signed action sum without rank-weight normalization. Tensor values can break equal primary scores only when coverage is complete for the entire tied group. Remaining merit ties share a rank interval; the whole interval must fit the cutoff. Positive recognition also requires a positive raw record and at least one supportive action. The observed action record is shown separately from the award, so low rank does not imply opposition and absence of action does not imply neutrality.

| Verified result | Count |
|---|---:|
| Members / subfields | 533 / 18 |
| Accepted field actions | 22,014 |
| Accepted legislative and letter actions | 8,095 |
| Actual recorded final-passage votes | 13,919 |
| Distinct overall actions after cross-field deduplication | 14,851 |
| Member-field cells with recorded action | 5,585 |
| Member-field cells without recorded action | 4,009 |
| Overall Champions | 13 |
| Subfield Champion / Ally / Highly Persuadable awards | 259 / 478 / 244 |

The public dashboard, member desk, combined local page, combined email page, workbook views, and generated ZIP packages now use this generation. Excel has **Field Recognition** and **Recognition Detail** sheets. The older analytical stance sheets and label columns are hidden while their data, formulas and cached values remain intact. Both canonical build paths now generate and validate recognition after the active overall board. The analytical desk build used before that board exists has an explicit internal mode that avoids a circular dependency.

The original fault was that several independent labeling systems combined fixed bands, category curves, present-signal normalization, caps, and separate browser ranks. A media-only record could receive a positive label; a low-action vote record could disappear; and the visible label and visible rank could be drawn from different orderings. The new recognition authority keeps eligibility, ranking, cutoff and explanation in one record. Existing model-facing stance values remain analytical inputs; public labels no longer derive from those values.

Review found and fixed the following issues before completion:

- Stale source data or a different active overall-board mode could otherwise leave old honors visible. The loader now verifies source hashes, policy settings and generation hashes before rendering.
- Consistent-looking but incorrectly reordered ranks and fabricated overall evidence summaries could pass structural validation. Both production validation and an independent audit now reconstruct ranking, tensor values, alignment, counts and evidence references.
- Explicit neutral votes were being confused with unknown direction. The final evidence includes 521 explicitly neutral CFPB vote records; unknown directions and non-actual casts remain excluded. Fractional Congress identifiers and incomplete source receipts also fail validation.
- Repeated workbook builds could accumulate styles or reuse a rollback copy that predates intervening edits. Styles are deduplicated; rollback is hash-protected; managed model updates restore the bound baseline first; fresh audit-workbook replacement is explicit.
- Combination could validate a different disk version from the HTML already captured in memory. It now validates the captured pages, and combination/packaging reject missing or mixed generation markers.
- The complete evidence ledger was repeated inside both page payloads and exceeded the existing email size limit. The pages retain their qualification fields and audit provenance while the full ledger stays in the immutable artifact. A tested, lossless standard-DEFLATE fallback using pinned `zopfli==0.4.3` preserves exact HTML bytes and the original 14 MiB limit.

Validation finished with **251 passing checks, zero failures, across 13 suites**, including 61 new honors tests, seven compression tests, the seven-test member-desk Node gate, existing primacy/workbook contracts, and package regressions. Python/browser calculation parity passed across all five network configurations and 206,601 directed edges with zero numerical difference. Failed checks and their corrected reruns remain in the test logs.

The delivered-artifact audit additionally verified every embedded recognition payload in all four HTML pages, all existing dashboard fields, all existing fields of every member record, nine analytical input files, and the cell XML of all 30 original workbook sheets. Dashboard data gained only its three recognition fields; the desk's existing member fields are identical. Its integrity/freshness metadata was refreshed. The active overall board and current model calculations were preserved.

The all-in-one package is **14,245,933 bytes**, under the **14,680,064-byte** cap. Every packaged entry passed CRC and byte-for-byte extraction checks. The delivery alias matches the all-in-one ZIP.

Current limitations are explicit. Tensor coverage resolves **zero** of the current equal-primary score groups; 28 unresolved groups cross an award boundary, so some award bands underfill. The full transition artifact records these cases and vote-weight sensitivity (294 label changes at vote weight 0.5; 377 at weight 2, compared with the selected weight 1). These are audit scenarios, not activated policies. The existing family ZIP omits the deferred member-profile script; the combined all-in-one page embeds the profiles and is the verified self-contained offline deliverable. This pre-existing family-package limitation was not expanded into a separate packaging redesign.

Both workbook views were rendered and visually inspected. The artifact runtime exited abnormally during teardown after producing the workbook; publication accepted it only after checking the generation-bound author receipt, output hashes and every authored cell independently. Direct browser visual inspection was blocked by the browser's local-file URL policy; no workaround was attempted. The rendering-function tests and actual HTML payload checks passed, but a visual browser walkthrough is not claimed.

The implementation does not require another policy decision to run. Operating details, repeated-build behavior and coordinated legacy rollback are documented in [RANK_HONORS.md](fec/stance/RANK_HONORS.md). The earlier proposal remains in [the implementation plan](TIER_RANK_IMPLEMENTATION_PLAN_2026-09-12.md).

Evidence:

- [Activation receipt](audits/tier_rank_implementation_20260913/activation_20260913T015928Z/receipt.json)
- [Delivered projection and preservation checks](audits/tier_rank_implementation_20260913/published_projection_receipt.json)
- [Final tests and dependency versions](audits/tier_rank_implementation_20260913/final_tests/test_receipt.json)
- [Independent evidence/rank audit](audits/tier_rank_implementation_20260913/candidate_independent_audit.json)
- [All label transitions, cutoff ties and sensitivity results](data/stance/rank_honors/daf1f6b94dcc65148fac534d/transition_report.json)
