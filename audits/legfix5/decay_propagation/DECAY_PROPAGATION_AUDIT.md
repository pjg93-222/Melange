# Congress decay propagation audit

- Static audit status: **PASS**
- Staged schedule: `119/118/117/116 = 1/.66/.33/.16`
- Frozen production schedule: `119/118/117/116 = 1/.8/.64/.512`
- Staged producer contracts: **9/9**
- Frozen copies matching the immutable manifest: **55/55**
- Live files byte-identical to the frozen snapshot: **8/55**
- Explicitly retained live-drift rows: **47**
- Staged old-schedule consumers: **0**
- Production cutover detected: **NO**
- Promotion/sync authorized: **NO**

## Downstream ledger

| Stage | Decay mode | Contract |
|---|---|---|
| `materialize_archive_and_legislative_workbook` | `direct` | Bills and archive contributions use staged decay; CU/CW manual LTR units and efficiency are rebuilt under it. |
| `materialize_rollcall_aggregate` | `mixed` | Canonical lean enforces bill=1/amendment=.5; the separately named diagnostic also applies staged Congress decay, while n remains a raw recorded-vote count. |
| `materialize_base_network_and_prebehavior_bipartisan` | `inherited` | Base edges already contain staged decay; bipartisanship consumes those weights and the adapter applies no second decay. |
| `recompute_behavior_panel` | `mixed` | Bipartisanship inherits decayed edge weights; sponsorship counts and unweighted graph degree intentionally have no Congress decay. |
| `recompute_behavioral_dispositions` | `mixed` | Cooperation inherits decayed bipartisanship; activity counts and legislative breadth intentionally remain counts. |
| `recompute_cooperation` | `mixed` | c1 inherits decayed bipartisanship; c2 cross-party share and c3 reciprocity intentionally remain relationship shares. |
| `recompute_receptivity` | `inherited` | Consumes recomputed behavioral dispositions/cooperation; no additional Congress decay is appropriate. |
| `recompute_augmented_network` | `mixed` | Cosponsor edges are copied verbatim with staged decay already embedded; nonlegislative added layers intentionally have no Congress decay. |
| `recompute_category_stance` | `mixed` | Legislation input inherits staged-decayed archive scores; roll-call lean enforces bill=1/amendment=.5 while its Congress-decayed variant remains diagnostic. |
| `recompute_say_do` | `intentionally_absent` | Preserved say/do DO is role_weight x advancement_weight with no Congress term; adding one would change the approved consumer-specific method. |
| `recompute_legislative_raw_normalized_sublayer` | `direct` | Consumes the staged numeric plan for bills, LTR rows, efficiency, normalization, and sublayers. |
| `recompute_pillars_and_ranks` | `inherited` | Consumes the evaluated workbook; the legislation pillar inherits staged decay without a second decay. |
| `recompute_coalitions_flips_budget_optimizer_allocation` | `inherited` | Consumes recomputed stance, network, workbook, and ranks; applies no separate Congress-age term. |
| `recompute_dashboard_and_member_desk` | `inherited` | Displays/joins recomputed archive, stance, network, workbook, and rank outputs; applies no separate decay. |
| `recompute_say_do_second_pass` | `intentionally_absent` | Re-runs the same preserved say/do formula after the final desk; Congress decay remains intentionally absent. |
| `recompute_second_pass_dependents` | `inherited` | Consumes hash-bound final say/do, stance, network, workbook, and ranks; applies no new Congress decay. |

## Important intentional absences

- Official roll-call event collection is factual and undecayed. Canonical `lean` enforces bill=1/amendment=.5, `n` stays a raw vote count, and only the explicitly named diagnostic additionally uses Congress decay.
- Behavior sponsorship counts, graph degree, breadth, cross-party share, and reciprocity remain counts/shares. Decayed network weights still propagate through bipartisanship.
- Say/do preserves `role_weight × advancement_weight` with no Congress term in both passes. Adding decay there would be a separate method change.
- Direction, culling, relationship visibility, and exclusions never consume decay.

The static propagation gate passing does not approve the staged schedule, complete coverage, execute a real shadow run, or permit promotion.
