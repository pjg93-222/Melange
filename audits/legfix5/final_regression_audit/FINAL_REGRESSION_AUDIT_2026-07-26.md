# Legislation final regression audit

Generated: `2026-07-26T11:53:24.749-05:00`

## Outcome

- Python compilation: **110/110 legislation-focused files passed**. Bytecode
  was redirected to `C:\tmp`; no production file was written.
- Python regression suite: **477 passed, 5 failed, 0 errors, 0 skipped,
  0 unrunnable** across **482 tests / 59 modules**. The suite includes 133
  top-level contract functions adapted to `unittest.FunctionTestCase`, with
  `tmp_path` and `monkeypatch` supplied only in temporary directories.
- Node collector contracts: **13/13 TAP tests passed**. The official-text
  matcher additionally reports **9/9 internal behavior checks passed**.
- Actual implementation regressions remaining: **0**.
- Explicit current acceptance blockers represented by failures: **1**
  underlying blocker, fanning out across 5 tests.
- Mainframe/production sync or promotion: **not performed**.

## Failure classification

All five remaining failures are the same fail-closed decay/freeze blocker:

1. `test_artifact_is_hash_bound_and_workflow_snapshot_is_not_authority`
2. `test_production_is_frozen_and_not_cut_over`
3. `test_presync_decay_checks_staged_producers_not_live_cutover`
4. `test_decay_propagation_receipt_is_required_and_hash_current`
5. `test_decay_workflow_snapshot_values_are_not_gate_authority`

The current decay audit is `FAIL`, with only **35/55** frozen/live pairs
matching and `production_cutover_detected=true`. Its sole blocking issue is
`frozen production baseline or live source drift detected`. This is an
explicit acceptance blocker, not an implementation assertion regression, and
was not bypassed or rewritten.

The pre-sync checkpoint remains **BLOCKED** with **16 blockers**, including
strict coverage at **22/62**, missing final merged coverage and ratified review,
unresolved computation and role-weight approvals, missing accepted roll-call
artifacts, and the decay/freeze blocker. `sync_allowed=false`.

## Test defects corrected

- The shadow-recompute fixture now declares the required fail-closed
  `staged_only=true` and `production_artifacts_written=false` fields.
- The historical display-tier test now uses the explicitly superseding,
  user-ratified `0.84 / 0.16` legislation/press weights.
- The historical adverse-band test now protects the combined strict adverse
  tail rather than a stale exact minimum for one adjacent label.

The corrected historical modules pass **39/39** in isolation, and the shadow
contracts pass in the final exhaustive suite.

## Current gate hashes

| Gate / artifact | SHA-256 | State |
|---|---|---|
| Search registry | `ba865417a0e722e0103d8a8ff65b657d15f66fde0fd76eeabaa37ba169d20b39` | Congress.gov Advanced Search; Quorum false |
| Strict manifest | `e7d0832dec751a6b60ab2c0a1d8132ca5b151794791788e4526af9adcd9dac6b` | 22/62 |
| Query specificity | `8154e6b169f3ea8ae500aa90d90eb5161f49ab7d3cba2d6c45dd4d0ef9062376` | PASS |
| BILLSTATUS snapshot plan | `6bd61b18ad017623bfb5fb25bd862081259ca26f4b6d33c6f076dd2950b4f536` | CURRENT through semantic rollover |
| Semantic identity | `85aec08da8cd5930dadc7ae6934720ff2021a8f2219022f6ec809b7794849538` | PASS, zero-network reuse only |
| BILLSTATUS completeness audit | `b2acd1ff3c0ff7a39406196d268e24e97eacc828de6445982d37f45da6a45739` | CURRENT |
| Structured relevance pointer | `c2f2b86a6d15d2ccbd64fa3e9eba88ec4a7a076088062573069fb8c7bae496fa` | review-only |
| Structured augmentation pointer | `58312de4980fd385c8bb0d10d766fe461f2146c0e9c8802fdde697032a71fdfb` | current; all authority false |
| Pre-sync checkpoint | `a7bbf46d8f386663e2e390cf445a20999e93932c49b9ae55ba763c4499768404` | BLOCKED, 16 blockers |
| Downstream readiness | `52597b2b9ba99a8904a26ac4223b274be73350771bc45c8bf5caae7963599c16` | `sync_allowed=false` |
| Decay propagation audit | `0da7d4b63031975e7e6df1a5afcffc7a2cbb40af33c52b8e7cc1472a66ce09fc` | FAIL, 35/55 |
| Decay audit basis | `5c397e8abe0de1f3ecae9ed41c91d51993d269fc15bd19cb20d914a1fbef6c8e` | source-count 27 |
| Formula cache pointer | `155617ba5b4dc4b8117285ee8afca2cf076ada9c747c04624beb39372d67c3d8` | temporary recalculation PASS; live not proven |
| Downstream drift pointer | `40657bf1dab35547e773db94a60cf4965d60104ea855b70d85d524f2990fc549` | observational, authority false |
| Behavior/stance pointer | `1538c9bedf3b14f97ad47ef9770c6748fed297a7d22e5653961ac6938815ed39` | observational, authority false |
| Planning/dashboard pointer | `0e7ac9f19790aa753667de74d54fa4783308f15393761ffedc919ce1182f8de7` | observational, authority false |
| Rank drift pointer | `3585e8b43fc172f3d0dc84256320ce89e1eb75e0dd5329c96857e754ce662127` | not authoritative for legislation ranks |
| Workbook OOXML pointer | `8e231ac37dfa95c226af19c2c08052cf84eb0149db8ca32e4ae8a5115d04ad94` | observational; accepted recomputation false |

## Authority and safety receipt

- Congress.gov Advanced Search remains the discovery instrument.
- `quorum_used=false`.
- Candidate/review/relevance/augmentation authority remains false.
- No membership decision import occurred.
- No scoring input was authorized.
- No accepted roll-call ledger was created.
- No live collector, network request, Excel automation, pipeline, persistent
  producer, sync, promotion, or mainframe write was executed by this audit.
  Producer contracts were exercised only against disposable test fixtures.
