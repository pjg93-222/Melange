# Fable A2R read-only adjudication review

Meta LOOP run: `run-20260830T0416179390616Z-17a7cf4477`

Act as the independent A2 reviewer. Return a decisive `PASS`, `REVISE`, or
`BLOCK` verdict. Review the implementation, committed public receipt, focused
tests, and only the two aggregate restricted receipts named below. Do not read
reviewer packet files, raw label logs, or response staging files. Holdout
outcomes must remain quarantined.

## Files in scope

- `fec/staffer_network/politico_adjudication_run.py`
- `fec/staffer_network/schemas/politico_adjudication_results_receipt.schema.json`
- `fec/staffer_network/publication.py`
- `fec/staffer_network/schema_validation.py`
- `fec/tests/staffer_network/test_staffer_politico_adjudication_run.py`
- `fec/tests/staffer_network/test_staffer_schema.py`
- `fec/tests/run_tests.py`
- `data/staffer_network/receipts/politico_adjudication_framework_20260830.json`
- `data/staffer_network/receipts/politico_adjudication_results_20260830.json`
- restricted aggregate view receipt:
  `C:\Users\pgoff\AppData\Local\Melange\staffer_network\adjudication_views\politico-quorum\a2-v3-20260830T054000Z\reviewer_views_receipt.json`
- restricted aggregate result receipt:
  `C:\Users\pgoff\AppData\Local\Melange\staffer_network\adjudication_results\politico-quorum\a2-20260830T061200Z\adjudication_results_receipt.json`

## Observed evidence

- Framework public anchor SHA-256:
  `729c653278dedfb65a410f89764206430ee78df7e7a517b94a04cc300757e845`.
- Final reviewer-view receipt SHA-256:
  `d9c0508dbf267cb4906fbe04416e86f0268e59c9128d5ddeccd05e5b01551543`.
- Restricted and committed A2 result receipts are byte-identical, SHA-256:
  `9d8b8ac83362d02b8c551ac4aa9445ed8766e3f440a1d2f759f0c25939f79117`.
- 400 append-only `MODEL_ASSISTED` labels cover 200 candidates, two reviewers,
  and calibration/holdout partitions.
- Calibration: 100/100 exact agreement; both reviewers returned `MATCH` on all
  100 strict candidates. This is not human gold and does not estimate precision.
- Holdout: both reviewers completed 100 labels. Outcome counts are not in either
  aggregate receipt and evaluation count remains zero.
- Human-gold adjudications: 0. Estimated human-gold precision: null.
- Canonical merges: 0. Source enabled: false. Auto-merge: false.
- All 52 focused staffer-network tests pass.
- Two earlier view generations were superseded after response-schema/CLI
  compatibility failures; no labels from them were accepted. One placeholder
  Codex calibration response was rejected before ingest. One Codex holdout
  dispatch timed out and was killed before any response was accepted.

## A1R2 obligations to verify

1. Framework SHA comes from the committed public receipt.
2. A2 emits a new post-label receipt rather than mutating the A1 receipt.
3. Holdout outcomes stay quarantined until one evaluation bound to the split hash.
4. Claims are limited to machine-flag blinding; source identity and partition are
   not falsely claimed to be hidden.
5. All labels remain `MODEL_ASSISTED`, never human gold.
6. Disagreements use a separate queue; no label edits.
7. Synced output is aggregate/hash-only; calibration denominator semantics are
   explicit, and possible/abstain remain separate.
8. A2 preserves original machine/path binding.

Evaluate fail-closed behavior, semantic invariants, leakage risk, evidentiary
claims, and whether A2 is complete enough to unlock corpus stages P1/P2 while
leaving source enablement and canonical merge publication blocked. List any
mandatory fixes with file/line evidence. End with residual obligations for the
next stage.
