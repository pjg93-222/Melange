# Final publication verification and remaining system findings

This records the earlier diagnostic promotion. The subsequent mathematical/source repair and its fresh audit totals are in [MATHEMATICAL_REPAIRS.md](MATHEMATICAL_REPAIRS.md) and [math_repair_completion_receipt.json](math_repair_completion_receipt.json); current counts can differ after source regeneration.

The regenerated diagnostic is visible on the live board. All 533 canonical seats match the dashboard and member desk; rendered honors, live alias, source-to-dashboard and email-package checks passed. The broader pipeline still returned failure at its final audit: **555 checks passed, 13 failed**. Publication parity is established; whole-system cleanliness is not.

## Two non-inventory findings

**Pillar snapshot age.** The snapshot is stamped September 3 and exceeds the 14-day ceiling. The active `live_legislative_pillar=true` branch in `compute_pillars.py` recomputes legislative inputs and obtains committee/demographic inputs through `nonlegislative_inputs`, bypassing this O/E/F snapshot entirely. The audit unconditionally checks the old snapshot afterward. Thus this specific alarm does not demonstrate stale inputs in the active board. A future repair should make freshness validation follow the active input path and retain the legacy snapshot guard when legacy inputs are used. No timestamp was refreshed merely to clear the alarm, and no audit assertion was waived.

**Personal-texture classification completeness.** The display-only artifact contains 4,727 details for 480 members. Direct inspection found zero malformed details, zero local-to-narrative leaks and zero invalid display admissions. Coverage is above its floor, but classified candidates number 5,894 against a semantic gate of 5,953: an aggregate deficit of 59. The selected queue's exact uncached count requires the producer's probe; subtracting these totals does not establish that count because the classified total covers all candidates. The cache-only rebuild cannot manufacture missing judgments. This needs the supported classification workflow and subsequent display regeneration; lowering the gate or inventing labels would not resolve it. This artifact does not feed ranks or traits.

## Eleven system-inventory findings

The remaining checks compare an earlier system manifest with current disk. They include both normal producer changes and missing historical sentinel paths. They must not all be dismissed as corruption, nor all be erased through an unexamined baseline refresh.

| Store | Failed checks | Direct observation |
|---|---:|---|
| `repo.data_stance` | 2 | Size class differs; `big5_gold_anchored.json` has a different hash and is 20 bytes smaller. |
| `repo.data_legislation` | 1 | `bank_anchor_reconciliation.json` hash changed at the same byte length. |
| `repo.data_network` | 1 | `co_appearance.json` changed in size and hash. |
| `repo.data_engine` | 1 | `per_area_grade.json` changed through this approved diagnostic regeneration; the current value is bound by the independent replay and publication receipts. |
| `repo.worktrees` | 1 | Two recorded packet paths under older worktrees are absent. This task did not delete them. Their archival disposition remains to be reconciled. |
| `repo.git` | 2 | Size class differs; two recorded pack files retain their byte lengths but differ in metadata, with no recorded content hash to establish equality. A recorded historical worktree-backup bundle is absent. |
| `local.lda_derived` | 1 | `cosponsor_sc/cosponsor_scores.csv` grew after the successful forecast refresh. The prior sentinel has no content hash. |
| `local.billstatus` | 1 | The 119th-Congress receipt differs in size and hash. |
| `mirror.melange` | 1 | A recorded mirror pack path is absent. Repacking is a possible explanation, not established by absence alone. |

The complete changed paths, before/after sizes and available hashes are in [remaining_audit_diagnostics.json](remaining_audit_diagnostics.json). The pre-existing dirty system manifest was preserved. Before refreshing it with its proper producer, reconcile missing historical backup/packet/mirror sentinels and review the changed evidence artifacts. No manual hash replacement or automatic acceptance of missing material was performed.

## Kernel tests

The final kernel totals are recorded in [STATUS.md](STATUS.md) and [completion_receipt.json](completion_receipt.json). The old generated-grade provenance failure is resolved: `test_per_area_board` now passes, as do the diagnostic suites. The missing historical bill-direction fixture and staffer absent-offices fixture were already recorded before this promotion in `audits/refresh_tick_20260919/COMPLETION_20260920.md`. They remain failed gates, not passes inferred from being pre-existing.

## Retained display and source limits

The descriptive-speech producer rejected a stale local YouTube candidate verification receipt. The canonical runner's existing tolerant-step policy retained its bound last-good display artifact. Candidate bytes differ from the verification receipt; the other three bound inputs still match. This is separate from the 13 final full-body failures. District industry regeneration also skipped an absent LODES source. Neither limitation was concealed by modifying a receipt.

The classified media corpus remains historical and fixed. Consult [MEDIA_CHANNEL_BALANCE.md](MEDIA_CHANNEL_BALANCE.md) before interpreting its cross-channel weights, and [NEXT_REVIEW.md](NEXT_REVIEW.md) for the unresolved methodological questions. All these findings are compatible with the narrower verified result that the requested diagnostic was committed and regenerated exactly under its approved rules.
