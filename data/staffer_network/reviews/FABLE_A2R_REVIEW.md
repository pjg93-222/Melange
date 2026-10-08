# A2R verdict: REVISE

The implementation is sound, the committed and restricted receipts are mutually consistent, and all eight A1R2 obligations are substantively met — but I found one real integrity gap in the receipt builder that touches the exact invariant this stage protects (holdout binding to the sealed split), plus one minor leakage vector. Neither invalidates the receipts already produced, but both must land before the holdout evaluation stage runs.

## Mandatory fixes

**1. `build_post_label_receipt` reads the split seal without verifying its hash** — `fec/staffer_network/politico_adjudication_run.py:370`. The function verifies the allocation manifest against `allocation_manifest_sha256` (lines 364–366) and the root binding, but then does `_read_json(root / "sealed_controls" / "split_seal.json")` with no comparison to `framework_receipt["split_seal_sha256"]` — even though the receipt it emits *advertises* that hash (line 441). The calibration/holdout partitioning that decides which outcomes get published comes from this unverified file. A tampered `split_seal.json` relabeling holdout candidates as CALIBRATION would surface their outcomes in the published aggregates while the receipt still claims binding to the original split — a quarantine bypass. Fix: `sha256_file(split_path) != framework_receipt["split_seal_sha256"] → raise`, mirroring the allocation check two lines above. A stronger companion: `_validated_labels` (lines 303–342) never cross-checks each label's own `partition` field against the sealed split; add that.

Why this is REVISE and not BLOCK: `prepare_reviewer_views` ran `verify_adjudication_framework` — which *does* verify the split-seal hash — at 05:40, labels were appended afterward under root-bound append-only controls on the same sealed root, and the published counts (100/100) match the framework receipt's sealed `calibration_count`/`holdout_count`. There is no evidence of tampering in this run; the gap is a missing defense, not an observed breach.

**2. `append_label_batch` returns holdout outcome aggregates** — `politico_adjudication_run.py:298`. The return value includes `outcome_counts` for every batch, including HOLDOUT partitions. It appears in no receipt (verified), but under the glassbox everything-emits convention, an orchestrator logging that return value would put holdout outcome counts outside the quarantine before any evaluation exists. Suppress `outcome_counts` when `partition == "HOLDOUT"`.

## Obligations verified (1–8)

1. **Framework SHA from the committed public receipt** — the results receipt's `framework_receipt_sha256` is `729c65...`, matching the stated public anchor, and every field it echoes (`root_binding_sha256` `51849d...`, `split_seal_sha256` `a16267...`, `review_sample_sha256` `dd68fc...`) matches the committed framework receipt field-for-field. Caveat: this session has no shell, so I could not *recompute* any SHA-256; hash claims are verified for cross-document consistency only.
2. **New post-label receipt, A1 untouched** — the builder writes a fresh results root, refuses an existing one (`run.py:358-359`), and loads the A1 receipt read-only under its anchor; any A1 mutation would break the anchor check itself.
3. **Holdout quarantine** — the receipt publishes only candidate/label counts plus `QUARANTINED`/`false`/`0`, all pinned as schema consts (`schema.json:112-114`) and re-enforced by `_validate_record_semantics` (`publication.py:414-427`). Notably, the schema's `evaluation_count: const 0` means this schema version *structurally cannot* publish an evaluation — a future evaluation requires a new schema version. Good fail-closed design, subject to fix #1.
4. **Claims limited to machine-flag blinding** — the view receipt claims only `machine_control_visibility: false` and `cross_reviewer_visibility: false`; packets openly carry `partition` and `reviewer_id`, and nothing claims source identity is hidden. Accurate.
5. **MODEL_ASSISTED everywhere** — hardcoded in both append paths, const-pinned in the label schema and results schema; `human_gold_adjudicated_count` and precision are const-pinned to 0/null.
6. **Separate disagreement queue, no edits** — disagreements go to `calibration_disagreements.ndjson` in the restricted results root (count + hash only in the synced receipt; the recorded `e3b0c4...` is correctly the empty-input SHA for zero disagreements); labels are append-only under an exclusive lock with duplicate refusal, and no edit API exists.
7. **Aggregate/hash-only, explicit denominators** — exact, determinate, and consensus denominators are separate fields; `possible_or_abstain_pair_count` is its own field; the semantics validator enforces every decomposition and rate. Both committed receipts pass `assert_public_safe`.
8. **Machine/path binding** — `_verify_root_binding` (path-resolve-normcase fingerprint) is enforced in both `append_label_batch` and `build_post_label_receipt`, and the A1 test suite includes a moved-root forgery negative control.

Fail-closed behavior is consistently good: staging-then-`os.replace` with cleanup on `BaseException` everywhere, zero-label precondition for view creation, exact-cover batch validation with a verified no-partial-write negative test (`test_..._run.py:129-161`), stale locks fail closed, and `run_tests.py` treats unrecognized suite output as failure with both adjudication suites registered (lines 337–338). The restricted and committed result receipts are character-identical as read.

## P1/P2 unlock

Acceptable to unlock P1/P2 once fix #1 lands, since P1/P2 consume no holdout outcomes and the receipts' aggregate claims stand on their own evidence. Source enablement and canonical merges remain blocked by schema consts, receipt semantics, and the unconditional `request_canonical_merge` negative control — leave all three exactly as they are.

## Residual obligations for the next stage

- The holdout evaluation must be one-shot, bound to `split_seal_sha256` `a16267...`, run only on code carrying fix #1, and published under a new results-schema version (the current one consts `evaluation_count` to 0 by design).
- Add an anchor-binding test that hashes the two committed receipt files and compares them to the recorded anchors (`729c65...`, `9d8b8a...`); today the committed pair are schema/semantics-validated but their byte-level anchors are asserted only externally. I also could not independently recompute any digest this session, and I did not re-run the 52-test suite (read-only review) — both are accepted as reported evidence.
- Record explicitly that calibration 100/100 all-MATCH carries zero discriminant signal on the strict stratum: the disagreement queue is empty, agreement is uninformative about precision, and human gold remains the only route to a precision estimate (correctly null today).

Per the standing findings-then-wait rule, I've applied nothing — both fixes are cited with file/line for Paul's APPLY gate.
