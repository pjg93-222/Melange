# Directory-led staffer spine: candidate rebuild

Date: September 8, 2026  
Candidate: `generation-20260908-candidate-v3`  
Result: spine built; integrity, eligibility and population-comparison checks passed  
Live activation: not performed; new identity adjudication and relationship qualification remain pending

## Rebuilt population

The replacement starts with Politico Pro and Quorum staff records. Politico is preferred for populated role/title/office claims. Quorum-only people remain available with unknown service dates. LDA supplies the separate lobbyist ecosystem. Payroll is retained only as evidence for documented questions; no payroll roster was loaded as a population seed.

| Candidate population | Distinct retained identity IDs |
|---|---:|
| Staff currently reported by Politico Pro | 16,852 |
| Quorum-only staff with undated roles | 775 |
| Historical-only staff from Politico Pro | 19 |
| **All three admitted staff scopes** | **17,646** |
| LDA lobbyist ecosystem | 25,092 |
| Review plane | 6,478 |
| Excluded intern-only profiles | 267 |

These are source identities after preserving existing decisions, not a certified count of globally unique humans. Population memberships can overlap in principle and should not generally be summed. The current snapshot has no accepted current-staffer/lobbyist identity overlap; that does not establish that none exists in reality.

The prior pinned work graph contained 144,692 payroll-derived person candidates across historical periods. Its count and the new current roster have different scope and identity semantics. A smaller count is not itself a quality result.

## What is implemented

The candidate is a sealed SQLite spine with people, complete source records, existing identity decisions, stable source bindings, role evidence, population memberships, preferred roles, container labels, review queues, targeted payroll evidence, and ecosystem references. Raw source snapshots and input hashes are retained beside it.

- All 49,731 input source records are conserved: 18,618 Politico profiles, 5,773 Quorum records, and 25,340 LDA records.
- All 5,827 existing accepted identity-decision records and 5,860 alias mappings are retained. New cross-source proposals have not been silently accepted. Explicit keep-separate constraints remain enforced.
- The 4,990 Quorum records with plausible unresolved Politico leads remain in review instead of being counted as additional current staff. The candidate crosswalk is retained with Politico precedence recorded for use after identity acceptance.
- The 775 undated Quorum-only records include cases with unavailable or contradictory Politico name leads. Missing Politico content does not erase Quorum evidence.
- Politico's 1,473 unavailable profiles remain visible in review and do not establish current staff roles. Fifteen additional source profiles have unresolved role classification.
- Intern-only current roles are excluded from staff membership. All internship and mixed/unknown-role episodes are ineligible for temporal evidence use. A later substantive role can still qualify.
- The role ledger contains 97,658 deduplicated records. Of these, 59,106 are bounded non-intern source-history interval candidates. They are not canonical employment episodes or automatically qualified person-to-person edges.
- Forty-five targeted payroll questions and 212 referenced proof-row entries were carried forward from the earlier ambiguity review. Those entries remain evidence, not population seeds or scored tenure. The original query-specific context and unresolved status are preserved.
- LDA and LittleSis ecosystem datasets remain referenced through their source manifests. Broad organizational memberships are not expanded into all-pairs acquaintance links.

## Source cleanup found during the rebuild

Some Politico current-position arrays contained a job heading split across two entries, followed by navigation and other page text. The builder reconstructed 74 clearly split title/office pairs. It withheld 2,035 unparsed fragments across 76 profiles from the role table while retaining their original source payloads and review indices.

The parser accepts technical and administrative staff roles as source staff; it does not introduce an unapproved job-title blacklist. Intern exclusion is role-specific. Present-tense source history stops at the profile's observation date; the build date does not extend its tenure. Quorum ingestion time is never used as employment time. Duplicate source role descriptions do not duplicate role records.

## Population-only connectivity evaluation

This experiment reads the entire pinned baseline graph and preserves every retained edge's existing weight. It isolates the effect of changing population scope. It does not certify the old payroll-derived relationships, apply the proposed new proximity attribution, or reproduce the live router's additional LDA and user-stated evidence.

| Measure | Result |
|---|---:|
| Baseline guaranteed work edges examined | 4,546,099 |
| Baseline possible-only edges accounted for separately | 766,885 |
| Admitted staff identities with exact baseline work nodes | 5,349 |
| Admitted directory identities without an exact baseline work node | 12,297 |
| Old work edges remaining between admitted baseline nodes | 41,921 |
| Isolates in that common-node projection | 13 |
| Connected components in that projection | 18 |
| Largest component | 5,298 |
| Diagnostic origin/target cases | 10 |
| Cases with higher route cost after population filtering | 9 |
| Cases unchanged | 1 |

The 12,297 identities without exact baseline work nodes are a coverage queue, not isolated people. The 13 isolates are a property of the population-filtered old graph, not a finding of no real-world relationships. Removed neighbors are out of scope under this population definition; their former ties have not thereby been adjudicated false.

Using alpha 0.85, the rank-order correlation between baseline PageRank and the scope-filtered PageRank within the common cohort is about 0.642. This is a diagnostic of changed graph context, not proof of improved ranking. Raw scores from the different graph universes are not directly comparable. Edge weights and the primary mathematical implementation remain unchanged.

Two review cohorts contain 50 high-baseline-degree cases and 50 sparse-after-filter cases. Each row reports the original degree, remaining degree and out-of-scope neighbor count. The ten route fixtures preserve their baseline paths, filtered paths and removed intermediaries.

## Verification

Seventeen focused unit tests passed. They cover alias conflicts and cycles, preservation of keep-separate decisions, exclusion of unaccepted identity proposals, Quorum's undated and review scopes, separation of LDA from staff membership, missing Politico content, intern/mixed-role exclusions, duplicate role invariance, source-bounded dates, split-header recovery, technical-role retention, route changes after removing a bridge, and PageRank mass conservation with isolates.

The independent candidate verifier passed all recorded checks, including source counts and payload hashes, frozen input hashes, SQLite integrity and foreign keys, directory-only staff admission, no payroll population seeds, no intern or mixed-role temporal eligibility, no fabricated Quorum dates, Politico role preference, preserved aliases, targeted payroll provenance, and zero canonical promotions or live activation.

The population comparison verified both baseline artifact hashes and read the complete edge file. It checked that removing nodes from a positive-cost graph could not produce a cheaper route. The live service remained ready, and its graph selector and saved user decisions were not modified.

These checks establish that this candidate follows the implemented population/evidence rules. They do not substitute for independent identity-accuracy calibration or adjudication of new work relationships.

## What remains before a live replacement

The candidate spine rebuild is complete. A production relationship graph still needs:

1. Adjudication of proposed Quorum/Politico identities, using the documented payroll questions where needed.
2. Validation of office/team identities and non-intern employment intervals before deriving new ties, especially for directory identities absent from the old work graph.
3. Review of the high-degree and sparse cohorts against their actual evidence.
4. A separate evaluation of proximity and shared-duration attribution, followed by routing, ranking and UI integration under the same eligibility rules.

Until then, the candidate remains a separate reviewable generation. No candidate role interval has been represented as a confirmed work relationship, and no live graph switch has occurred.

## Artifacts and reproducible commands

- [Candidate spine database](/C:/Users/pgoff/AppData/Local/Melange/staffer_network/normalized/operational-spine/generation-20260908-candidate-v3/spine.sqlite)
- [Build receipt and input manifest](/C:/Users/pgoff/AppData/Local/Melange/staffer_network/normalized/operational-spine/generation-20260908-candidate-v3/spine_receipt.json)
- [Independent verification](/C:/Users/pgoff/AppData/Local/Melange/staffer_network/normalized/operational-spine/generation-20260908-candidate-v3/spine_verification.json)
- [Population evaluation](/C:/Users/pgoff/AppData/Local/Melange/staffer_network/normalized/operational-spine/generation-20260908-candidate-v3/population_evaluation.json)
- [High-degree and sparse review cohorts](/C:/Users/pgoff/AppData/Local/Melange/staffer_network/normalized/operational-spine/generation-20260908-candidate-v3/connectivity_review_cohorts.ndjson)
- [Route comparisons](/C:/Users/pgoff/AppData/Local/Melange/staffer_network/normalized/operational-spine/generation-20260908-candidate-v3/population_route_comparison.json)
- [Directory identities without baseline work nodes](/C:/Users/pgoff/AppData/Local/Melange/staffer_network/normalized/operational-spine/generation-20260908-candidate-v3/directory_people_without_baseline_work_nodes.ndjson)
- [Framework](</C:/Users/pgoff/OneDrive/Desktop/Melange Systems/STAFFER_NETWORK_IMPLEMENTATION_EVALUATION_FRAMEWORK_20260908.md>)
- [Builder](</C:/Users/pgoff/OneDrive/Desktop/Melange Systems/fec/staffer_network/operational_spine.py>)
- [Verifier](</C:/Users/pgoff/OneDrive/Desktop/Melange Systems/fec/staffer_network/verify_operational_spine.py>)
- [Population evaluator](</C:/Users/pgoff/OneDrive/Desktop/Melange Systems/fec/staffer_network/evaluate_operational_spine.py>)
- [Read-only inspector](</C:/Users/pgoff/OneDrive/Desktop/Melange Systems/fec/staffer_network/inspect_operational_spine.py>)

From the project root, inspect the candidate without starting a server:

```powershell
python -m fec.staffer_network.inspect_operational_spine "$env:LOCALAPPDATA/Melange/staffer_network/normalized/operational-spine/generation-20260908-candidate-v3" --population staffer_current_reported --limit 10
```

The builder takes a new output directory and refuses to overwrite a generation. The inspector verifies the sealed database and receipt before reading. The old live graph remains selected by the unchanged `staffer_graph_snapshot.py` pin; no rollback action is currently required.
