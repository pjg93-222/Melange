# Live sentinel measurement receipt

The core source-to-dashboard reconciliation is **PASS**. Full audit: **COMPLETE_WITH_ACKNOWLEDGED_FINDINGS**.

Full audit: **565 passed**; only the four user-excluded old backup-path checks remain. Seven large-store/evidence checks were explicitly skipped by their existing audit policies.

Focused regression suite: **264 passed**, zero failures.

[All 22 decisions and their live ledger effects](live_receipt/RECEIPT.md).
[Machine-readable decision evidence](live_receipt/decisions_and_live_effect.json).

## Live result

- H.R.10082 now contributes +3 for Janelle Bynum and +2 for Young Kim in Charter Modernization and the legislative agenda used by headline ranks.
- H.R.10230 remains held: the revived supervisory authority has unresolved net CU direction. The other 14 exclusions and six original holds remain intact. No ACU endorsement was inferred.
- Verified durable memberships increased from 205 to 212; verified interaction rows from 210 to 217.
- Headline ranks changed for 518 of 533 members after replacing the stale Excel pillar with current evidence. See [rank changes](rank_changes.json). This is the combined repair, not an isolated bill effect.
- Primacy-board positions changed for 456 of 533 members; 4 crossed a tier boundary. Evidence portfolios changed for 178 members in the combined refresh. See [primacy rank changes](primacy_rank_changes.json).
- Catherine Cortez Masto moved from primacy #17 to #18 and stayed Tier 2. Her factor, agenda credit, mix, and PAC-2026-004 adjudicated credit are unchanged; Young Kim moved past her after H.R.10082 supplied new scoring CU-primary evidence. Catherine's separate headline rank moved #9 to #46 because the repaired live legislative percentile changed from 0.93796 to 0.73308.
- Primacy tier crossings: Janelle Bynum #228 to #76 and Darrell Issa #145 to #85 entered Tier 3; Cynthia Lummis #49 to #236 and Bernie Moreno #73 to #308 left Tier 3. These are combined-refresh effects, not all direct effects of the 22-row overlay.
- Current-cycle OpenFEC contributions reach the member desk and interactive engines. Observed PAC dollars and verified zeros are preserved when fundraising totals are missing.
- The actual local dashboard alias is regenerated with the final page and checked for byte equality.

## Automatic refresh contract

The existing Sunday 06:00 Windows task now collects new Congress.gov/GovInfo bills, checks official bill text and membership movements, refreshes FEC and rollcall sources, persists the sentinel ledger, rebuilds measurements, and verifies the dashboard. Document-reference classification is enabled before network rebuilding; its new classifier path passed an isolated synthetic end-to-end canary. The production document rebuild used the existing classification cache. Reference cache keys now cover the complete classifier window; a frozen legacy binding preserves prior labels and queues ambiguous prefixes for reclassification. Each unattended pass handles up to 128 contexts and reports its remaining backlog; a three-pass bounded-refresh regression reached completion without losing earlier evidence.

The headline legislative pillar preserves the workbook 70% agenda / 30% efficiency blend and the 45/10/40/5 overall weights. Agenda uses accepted signed role contributions and existing topic priorities. Efficiency uses signed, decay-weighted advancement of sponsor/original-cosponsor bills, preserving the 17 efficiency slots; unknown outcomes are recorded separately. Committee and demographic inputs are evaluated from source cells instead of Excel formula caches.

## Coverage and limits

- The reference-cache migration scanned 52,973 extracted references. It preserves inherited labels and queues 384 ambiguous legacy contexts for exact-window reclassification; it does not claim those labels were re-adjudicated today.
- The live bill repository refresh verified 465 bills. Automatic discovery adjudication is incremental; 14,015 candidates remain deferred. This receipt does not claim the historical backlog is exhausted.
- FEC was checked September 8 for cycle 2026; the newest attributed transaction is July 31. Alan Armstrong remains unresolved because the candidate identity mapping is absent. Modeled fundraising capacities remain explicitly distinguished from reported totals.
- X/Truth/Bluesky exports and manual evidence-review lanes still depend on their existing access/review inputs. The current change does not claim every external source has unrestricted unattended access.
- Backup recovery is outside scope per the user’s instruction: "Oh backups are done, don't bother". The old rescue-path findings remain visible and are narrowly acknowledged by the weekly gate.

## Preservation

Work stayed on main. The original 22-row overlay is byte-identical. No stash, reset, merge, stage, or commit was used. Before-images of edited source files and 19,192 production artifacts are retained locally; unrelated work was not reverted.

[Original branch integration and ACU/Higgsfield styling receipt](../govinfo_acu_integration_20260908/RECEIPT.md).

[Live browser verification](live_browser_verification.json). [Original dirty work reconciliation](initial_dirty_work_reconciliation.json). [Document cache migration](reference_cache_migration_receipt.json).

[Verification and artifact hashes](verification.json). [Production activation](activation_result.json). [Focused tests](focused_tests_final.log). [Full audit](audit_full.final.log).
