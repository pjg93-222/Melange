# Staffer connection ranking — September 10, 2026

The revised model reduces connections inferred from large workplaces, discounts shared employment more strongly on the House side, and ranks member recommendations by documented office access. Member eigenvector centrality supplies a bounded contextual adjustment from the independent overall member network.

## Mathematical review and implemented rules

The review corrected an assumption in the first draft: the minimum of two work allocations is an upper bound on their overlap, not a conservative estimate. The implemented product of allocations is an explicit independent-mixing assumption. It does not assert observed schedules.

For each distinct concurrent workplace, each person's allocation is `a = q / K`, where K is the number of simultaneous distinct workplaces. Shared-role q is 0.02 for House, 0.05 for Senate and 0.02 when chamber is unknown; documented dedicated work has q=1. The role adjustment is dated, so an earlier shared role does not penalize later dedicated employment.

Pair exposure is `E = sum_days,workplaces(kappa * a_i * a_j / (N - 1))`, where N counts distinct concurrently observed staff. Strength is `W = min(identity tiers) * (1 - exp(-E / tau))`, with `tau = 365.2425 / 19`. Duplicated records do not create extra allocations or headcount. Known parent/team overlaps are deduplicated; absent team assignments are not inferred. Interns contribute to workplace headcount but not scored staff routes or office anchors.

A member-office anchor uses allocated exposure divided by N, with `tau_M = 365.2425 / 20`. Committee affiliation alone cannot create employment anchors to committee members. Static member lists sort direct office-anchor strength times the member-context modifier, then direct anchor strength; global staff PageRank is diagnostic. Bridge lists compare documented anchor strength outside the person's strongest eligible office.

Live work routes optimize the product of edge strengths, a 0.8 factor per staff hop, and the destination office anchor where applicable. The terminal contact's member-context adjustment participates in route search. Dijkstra minimizes negative logarithms; Yen enumerates loopless alternatives using a hidden terminal sink. Candidate office contacts are compared together, avoiding a post-search reordering of only a few preselected routes.

Member context uses eigenvector centrality of the independently built, mean-symmetrized all-bills AUG member graph dated August 18, 2026. Pair proximity combines normalized one-, two- and three-step adjacency with weights 0.7, 0.2 and 0.1. Eigenvectors are normalized and compared within the target's connected component. The held graph has 533 members in one component. The adjustment is `1 + 0.15 * context`, so it cannot create a connection from zero or add more than 15%.

## Evidence boundaries and release scope

The active Staffer UI explicitly requests the revised `work_time` model, identified as `staffer-closeness-exposure-v1`. It retains the existing authenticated dated directory-employment gate. Payroll observations can enlarge the workplace census but cannot create a live work-route edge or a live member anchor. Static member lists use the sealed trajectory evidence and its existing identity-strength tiers.

The published `data/engine/staffer_network_section.json` contains 533 member records and 7,669 ranked rows. Its first-ranked contact changed for 406 member lists. Average retention of the previous top 15 was 56.52%; this measures ranking movement, not recommendation quality. The normal Groups HTML artifact was rebuilt. Its existing Groups presentation remains separate from static member-list presentation.

The sealed historical graph generation, historical centrality diagnostics, standalone legacy outreach CLI, and other legacy routing objectives were not rebuilt or replaced. API calls that omit an objective retain their prior default for compatibility. The full Moneyball dashboard was not rebuilt as part of this change.

## Verification

- Focused routing/math suite: 98 passed before the final intern case; subsequent math/work-route checks: 16 passed, including the added intern case. These suites overlap and must not be summed.
- Static section checks: 210 passed; HTML producer checks: 219 passed; route JavaScript checks: 7 passed.
- Guarded live restart integration suite: 121 passed in 79.60 seconds.
- Independent full-population release verification checked rank ordering, positive dated anchors, excluded shared/intern top-role labels and the 15% bound across all 7,669 rows. A separate daily-array calculation reproduced 40 sampled anchors with maximum absolute error 0.0000004916485, consistent with published rounding.
- Four initially failing integration cases also failed with the pre-change router. Their stale fixtures lacked required client IDs, current identity-provenance fields or operational-population receipts. Only those fixtures were brought into line with their existing contracts; all 12 checks in the two affected files then passed. See `integration_baseline.log` and `integration_fixture_repairs.log`.

Live HTTP results and runtime status are recorded separately in `live_release_verification.json` and `completion_receipt.json`. No claim is made that the entire repository test suite was run.

## Limits and calibration

The coefficients are exploratory. No labeled successful introductions or user-supplied good/bad examples were available to validate ranking relevance. Observed rosters can undercount actual staff, and missing schedules remain a modeling assumption. Dedicated committee work can still support coworker connections within its documented workplace. Employment dates establish possible professional exposure, not friendship or willingness to provide access. No additional recency decay was introduced.

The comparison, formula draft, validation scripts, logs, exact live responses and scoped pre-change backups are retained in this audit directory. `completion_receipt.json` records hashes of the published artifacts and implementation files.
