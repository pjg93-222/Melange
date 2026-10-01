# Dashboard repair and verification — September 8, 2026

The local dashboard was regenerated from its current source surfaces and retains the newer sidebar presentation. The directory-led candidate spine has **not** been activated. Neither existing routing engine's mathematics nor the saved identity and coworker assertions were changed.

## Repaired behavior

- Apply the newer presentation before the body first renders; suppress the older staffer panel in the local dashboard.
- Remove conflicting member addresses from member-to-staffer links and canonicalize older mixed links before startup.
- Preserve person, office, route endpoints and route-network selection across the parent dashboard and People frame. Reuse the frame when returning through the sidebar or Back.
- Show the pathfinder by default, bring selected person details into view, and retain displayed connections while replacement data loads.
- Prevent inventory refresh from replacing a complete selected profile with a compact search row.
- Compact the sidebar from 184 to 144 pixels and the desktop person/path panel from 360 to 300 pixels. Provide Hide panel / Show people & paths.
- Increase maximum zoom from 12 to 256; keep the point under the cursor stable. Resizing the map no longer resets it to the overview.
- Label the selected person's individual work/report connections and add Focus connections.
- Expose the existing evidence-cost engine as **Ecosystem · lobbying reports**, separate from **Work & background**. Ecosystem excludes policy-only links and does not admit unresolved identities. Shared reports remain labeled as reports rather than employment.

## Kathleen Coulombe diagnosis

The live search resolves Kathleen to `person:lda:lobbyist:154321`. Her two LDA identities remain combined under the previously confirmed identity decision. The person endpoint returns 14 shared-report collaborators, zero dated coworkers, and no admitted features in the current work/background scoring categories.

The same Kathleen-to-Gordon query returned `unreachable` under `overlap_balanced` and a one-step path under `evidence_cost`. The dashboard now reproduces that ecosystem route and labels its April–June 2026 shared lobbying report. This is a route-model coverage distinction, not evidence of real-world isolation.

The diagnostic responses are retained in `audits/dashboard_consistency_20260908/kathleen_*.json`.

## Verification

- 48 targeted Python tests passed.
- 12 Node test entries passed, including navigation, route state, zoom, snapshot recovery and group browsing. The group entry contains 19 behavioral checks.
- 46 combined-surface contract checks passed.
- Browser verification: newer sidebar; populated network; A.C. Sansalone's person facts; a three-step staffer route; Kathleen's one-step ecosystem route; individual report connections; hidden-panel map; zoom beyond the previous ceiling (13.7466 with 85 individual people visible); canonicalized saved member/staffer link; restored endpoints; Industry → Back preserved Kathleen's displayed ecosystem route.
- The local service was ready after its index warm-up.

Browser automation intermittently timed out, including while opening the large combined page. One startup MutationObserver console error lacked source attribution; no associated failure was reproduced in the verified flows. This report documents the tested flows rather than certifying the entire dashboard free of defects.

## Release scope

The local server continues to serve `Moneyball_Redesign.html`; that file and `Moneyball_Email_Redesign.html` were rebuilt with the existing source data. Local People features are served from `fec/surfaces/staffer_live/`. Offline bundles retain their separate offline contract and are not the live application.

Source and output backups, hashes, route diagnostics and the final receipt are in `audits/dashboard_consistency_20260908/`. Existing unrelated workspace edits were preserved.

Production identity adjudication, the smaller staffer population, a separately navigable ecosystem population, and the new work-proximity × time scoring graph remain part of the spine release. Adding the ecosystem routing option does not complete that population migration.
