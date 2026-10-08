# A2R2 verdict: PASS

Both mandatory findings from `FABLE_A2R_REVIEW.md` are closed, with negative controls that test the new checks specifically rather than adjacent ones. P1/P2 may proceed. Holdout evaluation, source enablement, human-precision claims, and canonical merges remain blocked exactly as before.

## Mandatory finding #1 — closed

`build_post_label_receipt` now hash-verifies `split_seal.json` against `framework_receipt["split_seal_sha256"]` before reading it (`politico_adjudication_run.py:377-379`), mirroring the allocation-manifest check and failing closed with "split seal hash mismatch". The check runs before `_read_json`, so a tampered seal is never parsed. Two strengthening measures went beyond the minimum I asked for:

- **Exact-cover check** (lines 382-388): the sealed split and the allocation manifest must cover the identical candidate set, closing the gap where a seal could silently add or drop candidates while every per-candidate check still passed.
- **Per-label partition cross-check** — the companion I recommended: `_validated_labels` now takes `partition_by_candidate` from the verified seal and rejects any label whose own `partition` field disagrees (lines 338-341). Since every label's candidate is already confirmed to be in the allocation, and allocation coverage equals seal coverage, every label is now partition-bound to the sealed split.

The negative controls are the right ones. `test_results_fail_closed_on_split_or_label_partition_tampering` first flips one candidate's partition in the seal and asserts the specific "split seal hash mismatch" error; it then byte-exact-restores the seal and tampers a label's partition **while recomputing its `label_id`** so the label is internally self-consistent (test lines 224-243). That second forgery would sail past the pre-existing label-ID integrity check — it can only be caught by the new sealed-split cross-check, and the test asserts exactly that error message. This is a genuine test of the new invariant, not a re-test of an old one.

## Mandatory finding #2 — closed

`append_label_batch` now builds `outcome_counts` only when `partition != "HOLDOUT"` (lines 300-304). The return value for holdout batches carries only `status`, `reviewer_id`, `partition`, `labels_added`, and `label_file_sha256` — a count and a hash, both already published in the results receipt, so an orchestrator logging the return under the glassbox convention leaks nothing. The main flow test asserts `assertNotIn("outcome_counts", result)` for holdout and `assertIn` for calibration (test lines 108-111).

## The other claimed corrections

- **Byte-anchor test** (correction 6): `test_committed_results_receipt_is_public_safe_and_semantically_valid` now hashes both committed receipt files and asserts `729c65…e845` and `9d8b8a…9117` directly (test lines 249-256). This closes my A2R residual obligation that the byte-level anchors were asserted only externally.
- **Unchanged committed receipt**: correct and expected. The corrections are purely additive fail-closed validations; the aggregate computation is untouched, so untampered sealed inputs reproduce the identical receipt. The committed results receipt I read matches the previously recorded anchor prefix and remains field-for-field consistent with the committed framework receipt (`framework_receipt_sha256`, `root_binding_sha256` `51849d…`, `split_seal_sha256` `a16267…`, `review_sample_sha256` `dd68fc…`).
- **53/53**: arithmetically consistent (52 prior + 1 new negative-control test), accepted as reported — see caveats.

## Blocks confirmed still in place

The receipt still publishes `holdout.status: "QUARANTINED"`, `outcome_counts_published: false`, `evaluation_count: 0`, `estimated_human_gold_precision: null`, `human_gold_adjudicated_count: 0`, `source_enabled: false`, `canonical_entity_merges: 0`, `auto_merge_enabled: false`, and the committed-receipt test asserts each of these against the committed bytes. Nothing in this diff touches the merge path or the schema consts that structurally prevent publishing an evaluation under the current schema version.

## Residual obligations

1. **Holdout evaluation** (unchanged from A2R): one-shot, bound to `split_seal_sha256` `a16267…`, run only on this corrected code, published under a **new** results-schema version — the current schema consts `evaluation_count` to 0 by design.
2. **Zero discriminant signal on calibration**: 100/100 all-MATCH with an empty disagreement queue says nothing about precision on the strict stratum. Any P1/P2 surface quoting the agreement rate must carry that framing; human gold remains the only route to a precision estimate.
3. **Verification caveats**: this session is read-only with no shell — I could not recompute any SHA-256 or execute the 53-test suite. The new byte-anchor test means a single `run_tests.py` invocation now confirms everything I verified by cross-document consistency; the 53/53 result is accepted as reported evidence pending that run on Paul's side.
4. **Cosmetic, non-blocking**: `_validated_labels` accepts a `receipt` parameter it never uses (`politico_adjudication_run.py:307-312`); drop it in a future touch, no urgency.

Per the standing findings-then-wait rule I have applied nothing; this verdict is the deliverable. (Note: the orchestration hook asked for delegation, but no Agent tool is exposed in this session's toolset, so the five file inspections were done inline.)
