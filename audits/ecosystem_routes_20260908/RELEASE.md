# Ecosystem route expansion — September 8, 2026

## Implemented

- Propagate previously accepted user-confirmed and reference-resolved LDA identities into all named activity evidence. This restores Gregory Mesack's retained source IDs without creating a new identity decision.
- Build a separate sealed v2 index from the complete verified LDA corpus, preserving the v1 rollback artifact.
- Route through shared issue sections, entire quarterly filings, and the same registrant in the same reporting quarter. These are labeled ecosystem associations, not coworker employment records.
- Deduplicate each person's filing membership and each pair's reporting quarters. Keep the strongest relationship per quarter and retain all observed periods as evidence.
- Use the latest uniquely posted filing for each exact registrant/client/quarter combination. Older versions remain in raw activity browsing; ambiguous latest ties are withheld.
- Expose distinct observed period counts and full provenance in collaborator and route cards. The existing base cost is 2 for an issue-section association, with costs 3 for a full filing and 4 for a registrant-period association. Period counts are displayed separately; the future work-proximity × duration math is not activated by this release.
- Keep organization memberships sparse and generate neighbors on demand instead of constructing full organization cliques.
- Implement shared-client-period evidence with a visible client-organization label in both route cards and route-map edges. The code requires a common exact client identity; it does not create name-only organization merges.

## Evaluated

Candidate evaluation covers Kathleen, Gregory and a deterministic 40-person source sample. It verifies reciprocal relation/cost/period results, deduplicated periods, no claimed continuous employment and explicit organization mediation. All 42 checks passed. This is a structural/source-coverage evaluation, not an independent manual precision certification of every edge.

Kathleen has 24 candidate canonical neighbors in the evaluated source graph, including the nine approved ACLI filing candidates and Gregory. Ian Steger, Jeffry Janoska and Paul Kangas each have 21 observed shared quarters. The original live display had 14; v1 with the identity propagation fix has 15, and whole-filing expansion adds nine.

The 42-person sample includes 364 issue-section associations, 42 whole-filing associations and 64 registrant-period associations (directional sample counts, not corpus totals). Maximum sampled degree changes from 49 to 65. Some counts fall after superseded reports are removed.

Final targeted verification: 53 Python tests and 8 Node route/map/zoom tests passed, including relationship-label/period-display and mixed workplace/filing route regressions. JavaScript syntax checks passed. Browser and live API activation results are recorded separately in `live_verification.json`.

Live testing exposed repeated scans of the same registrant-quarter for people with many client filings. The provider now scans each firm/client reporting group once, preserving identical reciprocal results. A 200-client-filing regression verifies bounded scan work and one counted reporting period. All six ecosystem tests pass. Repeating the 42-person evaluation preserved every sampled degree and relationship count while reducing measured evaluation time from 26.28 to 4.80 seconds. The service was restarted with this correction before final live verification.

Final live verification: Kathleen has 24 lobbying-record collaborators and Gregory has 49; neither lookup is search-limited, and Gregory's results include Kathleen. The live API and reloaded sidebar dashboard both find Kathleen → Ian Steger in one step, cost 3, labeled "Same organization and quarterly filing" with 21 distinct shared reporting periods. The visible Ecosystem routes control and highlighted map route were checked in the in-app browser. This verifies the corrected service, not merely an offline candidate.

## Activation and rollback

The service reads `audits/staffer_live_runtime/ecosystem_activity_pin.json`, validates its PASS status and database hash, and opens `lda_activity_v2.sqlite`. The original v1 index remains unchanged. Removing the new pin and restarting the service returns to v1 data coverage with the identity propagation repair still in code. Source backups are in `before/` here. No original source assertions were rewritten.

## Remaining evidence work

The corpus has zero client IDs shared by different registrants: client IDs are registration-specific. Thus the shared-client code is tested but does not yet produce cross-firm client bridges in this dataset. `client_identity_candidates.json` identifies 6,136 exact-name candidate groups covering 17,586 client source IDs; these are explicitly withheld pending organization identity adjudication. ACLI alone has seven distinct client IDs with the same reported full name and DC location. This is a useful adjudication queue, not seven automatically merged identities.

New employment, board and working-group histories still need source-specific identity and date reconciliation before they can create additional routes. Existing dated workplace evidence continues to provide ecosystem-to-staffer bridges. This release does not invent colleagues from a title, reactivate interns, use LDA to qualify staffer population, or activate the pending operational-spine population/new scoring model.
