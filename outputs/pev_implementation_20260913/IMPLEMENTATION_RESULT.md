# PEV implementation result

**Implemented and tested as an isolated candidate.** The scoring order is Primacy → Efficiency → Useful Volume. The package contains executable scoring and replay code, corrected evidence notes, revised activation and collection contracts, and a searchable full-roster comparison.

Open the [interactive comparison](generation_01/review.html), [complete board data](generation_01/board.json), or [validation receipt](VALIDATION_RECEIPT.json).

| Frozen comparison | 118th Congress | 119th Congress |
|---|---:|---:|
| Displayed members | 533 | 533 |
| Members with observed efficiency | 417 | 440 |
| Efficiency unavailable | 116 | 93 |
| Fully observed member–measure opportunities | 1,774 | 1,639 |
| Opportunities with further advancement | 466 | 635 |
| Candidate ranks changed | 158 | 136 |
| Candidate tier memberships changed | 0 | 0 |

All 13 current Tier-1 members remain in Tier 1. That follows the strict primacy order; it is not a threshold selected to preserve particular names. Existing evidence and conduct constraints remain in force. The two Congresses are separate comparisons, using the frozen current primacy board and historical outcome windows.

The engine replaces the ambiguous delivery blend with a measured conversion rate: a unique beneficial member–measure engagement succeeds if it reaches a further milestone during a fully observed 180-day window after the first verified join. A conventional Wilson adjustment reduces the influence of thin records; House and Senate percentiles are calculated separately. Raw rates, counts, role breakdowns, stages and coverage remain inspectable. Helpful volume counts distinct positive CU measures, without rewarding harmful or neutral activity.

Zero opportunities, unknown evidence and recent opportunities remain distinguishable. Withdrawal does not remove a failed attempt from the denominator; rejoining cannot reset its clock. Mature early successes and failures face identical observation requirements. Stale histories and contradictory records cannot turn into favorable scores.

Validation completed:

- **58/58 behavioral and adapter tests passed**, including output isolation, chronology, normalization, duplicate handling, invalid data, ordering and HTML injection protection.
- The source board's **533/533 tiers and ranks reproduced exactly**, with exact published primacy-score parity.
- Both per-Congress candidates passed identity, normalized-metric, priority-order and final evidence/conduct checks.
- Two independent replays produced **byte-identical board JSON, opportunity ledger, report and HTML**.
- All consumed source hashes were unchanged across both runs.

The 180-day horizon and z=1.96 are explicit candidate settings, not an empirically proven optimum. Observed advancement is not member causality, economic benefit or return per lobbying dollar. The accepted historical evidence is retrospective.

**Production remains unchanged.** This result verifies the executable candidate, not production wiring. The [activation contract](ACTIVATION_CONTRACT_PEV_2026-09-13_v3.md) specifies the remaining consumer integration and full-chain checks before live activation; these checks were not run by this isolated replay. The existing task's request has been used to implement and compare the revised design, without presenting the frozen document's historical dispatch instructions as fresh authorization.
