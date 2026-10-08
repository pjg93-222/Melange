# Staffer governing-file audit — September 10, 2026

Scope: live Staffer/Ecosystem routing contracts, payroll source admission, exposure and uncertainty math, route provenance, map positioning and request lifecycle, exclusions, installer coverage, and the README/visible methodology. This is a subsystem audit, not a claim that the entire repository or source corpus is free of defects.

## Verified defects and corrections

| Finding | Consequence | Correction |
|---|---|---|
| Hop provenance selected every employment row at a shared office, regardless of dates | An unrelated old report-period record could relabel an otherwise documented overlap as modeled and appear as supporting evidence | Keep joint overlap intervals in workplace support; select only source rows intersecting those intervals |
| Source coverage admitted internship rows whenever the person had another eligible stint at the same office | Coverage totals and source details could include rows that created no route exposure | Require a non-intern role and intersection with an admitted exposure segment; preserve internship headcount evidence |
| Exposure extended beyond the route's as-of date | Future scheduled employment could create a present connection and accumulate years of unsupported exposure | Exclude future starts and clip interval ends through the as-of day; retain original end bounds in source_end_exclusive |
| Null container metadata overwrote payroll workplace type/chamber | A member-office pair could use the generic 0.5 multiplier instead of 1.0 | Only non-null node metadata overrides source metadata |
| Same-office staleness used only the last joint day across all historical runs | A one-day return could refresh ten years of old exposure | Weight each continuous joint run's final day by that run's exposure; apply the same rule to terminal office anchors. Headcount/allocation boundaries within a continuous run do not split recency |
| Clearing the last highlight did not invalidate an outstanding position request | A delayed worker reply could resurrect cleared map highlights | Advance the position-request generation on every lookup, including empty selections; drop inactive highlight points |
| Installer omitted newer routing modules and their Staffer dependencies | An install into an older checkout could leave incompatible or missing components | Add dependencies to the scoped manifest and verify direct Staffer import coverage |
| Governing descriptions lagged behind the implementation | Parent Methods said the rebuild was not live; README described old map filters, universal bidirectional search and only Yen alternatives; directory-only responses claimed payroll inputs | Align descriptions with source modes, graph scope, algorithms, scoring, uncertainty and explicit exclusions; repair corrupted punctuation |

The backend regressions reproduced five failures before correction. The continuous-contact recency test already passed and remains a control against over-penalizing a still-continuous connection.

The old inventory-worker test still expected text search to remove people from the map and expected obsolete employment filters. Its fixtures now reflect the current contract: the server supplies the scope-specific inventory and text search changes only the result list.

## Governing implementation

- Source admission and precedence: `fec/surfaces/staffer_work_sources.py`.
- Exposure and continuous overlap runs: `fec/staffer_network/closeness_math.py`.
- Uncertainty costs: `fec/staffer_network/relationship_uncertainty.py`.
- Person/office routing and route evidence: `fec/surfaces/staffer_closeness_routes.py`, `staffer_routing.py`, `staffer_distinct_routes.py`, `staffer_live_service.py`.
- Map lifecycle: `fec/surfaces/staffer_live/staffer-explorer.js`, `staffer-inventory-worker.js`, `staffer-live.js`.
- Explicit exclusions and route controls: `fec/surfaces/staffer_live/staffer-route.js`.
- Installation: `fec/surfaces/install_staffer_live.py`; existing checkout and its general dependencies are prerequisites.

Routing version is now `employment-routing-v7-overlap-evidence-audit`; exposure version is `staffer-closeness-exposure-v3-overlap-runs`. Versioning invalidates old route-cache revisions. The selected static graph generation remains September 8 v8 math; no sealed graph or raw-source artifact was rebuilt.

## Decisions left explicit

The audit does not calibrate friendship or willingness. The 2%/5% shared-role factors, workplace multipliers, hop factor and uncertainty coefficients remain scenario assumptions.

Shared-role recognition still relies on the two normalized shared-employee titles. A trajectory's last title may summarize a whole fallback stint. Simultaneous conflicting role records use the higher allocation, and unknown titles receive ordinary-role allocation. These require a source-role reconciliation policy, not an arbitrary additional penalty.

Headcount remains distinct observed person IDs rather than FTE or verified unique humans. Incomplete coverage and unresolved identities can distort it. Person-to-person routing does not use member centrality; office terminal scoring still has a bounded member-context adjustment.

Different-people alternatives are greedy conditional searches. Their contacts are disclosed; they do not prove a globally optimal set of independent routes. No named person is excluded by default. Search latency remains material in the expanded corpus, and abandoning a browser request does not cancel an already-running shared backend search job.

## Validation

98 focused Python tests passed, followed by the additional installer-dependency regression (99 distinct tests in that scope). All 20 Staffer JavaScript runner entries passed; the groups entry also contains 19 internal assertions. The guarded restart passed 121 source-integration tests. Counts overlap between suites and must not be summed as unique coverage.

See `test-receipt.json`, `javascript-tests.log`, and `live-restart.log`. The fresh route reproduction and comparison are recorded by `verify_live.py` in `live-receipt.json` and `live-gordon-casca.json`.

Live verification passed on routing revision `e192acd1195840678bdf`, process 28140. Gordon Holzberg → Hailey M Barringer → Rene O Castellanos → Mike Casca remains the best route; cost 6.11683081028798 differs from the previous receipt only by floating-point rounding. The returned exposure model is v3. The browser visibly renders four labeled people and three connecting lines, with No people excluded in the toolbar. Indexed people/workplaces remain 84,734/1,547; admitted source-episode counts decrease where previously counted rows did not contribute route exposure.
