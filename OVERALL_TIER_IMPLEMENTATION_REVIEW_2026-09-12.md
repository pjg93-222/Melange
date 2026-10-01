# Overall priority tiers and behavioral standing

Implemented, activated and verified locally on 2026-09-12 (America/New_York). Active generation: `0ed697a1821e0d8fd3ac3bbe`. Evidence snapshot as of 2026-09-12.

**Live-entrypoint correction (2026-09-13 03:21 UTC):** The initial verification covered generated pages but missed `Moneyball_Redesign.html`, the alias actually served by both the dashboard and installed Edge app. That alias still had the older labels. It has now been updated through the existing guarded synchronizer, retaining a rollback copy. The actual app HTTP response was verified against both complete generated payloads for all 533 members. Cortez Masto is Ally, action rank 55, priority rank 18 / Tier 2. The activation script now includes alias synchronization and the projection verifier checks the alias. Existing open pages need a refresh to load the replacement. See the [live app verification](audits/overall_stance_implementation_20260913/live_app_verification.json).

The previous implementation correctly rebuilt subfield recognition but left overall standing incomplete: it gave the top 13 their Champion recognition and reduced everyone else to coarse action-pattern labels. The dashboard also repurposed the priority-tier controls as recognition filters, obscuring Tier 2 and Tier 3. This follow-up addresses both gaps.

Overall priority now retains the actual active board's membership: **13 Tier 1 Champions, 24 Tier 2 members, 48 Tier 3 members, and 448 members outside the priority tiers**. Every member keeps their original priority rank. The active ranking formula, overrides, evidence floor and conduct rules are unchanged.

Every member also receives a separate **behavioral standing** from their deduplicated legislative action record. Priority and standing have separate labels, ranks, filters and workbook columns. For example, Alex Padilla remains Tier 1 Champion while his action rank of 117 of 533 qualifies as Persuadable. The system does not imply that priority rank 1 and action rank 117 measure the same thing.

## Complete overall treatment

These overall bands are versioned implementation defaults under the instruction to proceed. The user explicitly supplied the subfield bands and the top-13 overall Champion rule; the additional overall standing thresholds are not represented as separately selected user thresholds.

| Behavioral standing | Qualification | All members | Outside priority tiers |
|---|---|---:|---:|
| Ally | Positive record; cumulative top 15% of all observed actors | 79 | 35 |
| Highly Persuadable | Positive record; cumulative top 20% | 27 | 21 |
| Persuadable | Positive record; cumulative top 50% | 159 | 137 |
| Lean Persuadable | Remaining positive records | 266 | 253 |
| True Neutral | Observed zero score; neutral-only and balanced records distinguished | 0 | 0 |
| Lean Skeptic | Remaining net-negative records | 2 | 2 |
| Skeptic | Cumulative top 20% of net-negative actors, strongest opposition first | 0 | 0 |
| Highly Skeptical | Cumulative top 15% of that negative cohort | 0 | 0 |
| Opponent | Cumulative top 5% of that negative cohort | 0 | 0 |
| Insufficient evidence | No qualifying action; excluded from behavioral ranks | 0 | 0 |
| **Total** | | **533** | **448** |

The standing names retain the product vocabulary; they are not predictions of persuasion probability. Mixed positive and negative actions remain visible alongside the standing. A low positive rank never becomes opposition, and missing evidence never becomes neutrality.

The overall score is the raw signed sum of action weight × Congress decay. It counts each overall event once across fields and validates that copies agree on action identity, weight, decay and tensor position. A signed field copy takes precedence over a neutral copy; conflicting nonzero directions stop publication. The verified snapshot has **14,851 distinct overall events**.

Tensor can only break equal primary scores, and only when coverage is complete for every member in the tied block. Positive ordering descends; opposition ordering ascends. All cutoffs round down and require the whole remaining tie to fit. Mike Johnson and Steve Cohen share ranks 266–267 at raw score 24.96; the Persuadable cutoff is 266, so both are Lean Persuadable. The two net-negative members form a cohort of two, whose 5%, 15% and 20% cutoffs all round to zero; neither automatically becomes an Opponent.

## Implementation and review

- Added `overall_behavioral_standing_v1` alongside the unchanged `field_rank_honors_v1` policy.
- Restored canonical priority controls in the dashboard, including an explicit outside-priority filter; behavioral standing and subfield recognition have independent filters.
- Updated member-desk list, profile and efficiency displays with separate priority and standing, action ranks, mixed/balanced records and evidence explanations.
- Extended Field Recognition and added Overall Standing in the workbook; Recognition Detail continues to explain the 18 subfields.
- Added strict overall policy and record validation, deterministic deduplication, full transition rows, and independent arithmetic checks for both cohorts.

The reviewed candidate reproduces **all 9,594 subfield records exactly**, including the existing field cutoffs and recognition recipients. It also preserves every overall priority rank, Champion and Tier 2/Tier 3 membership. Original analytical stance and scoring fields remain model inputs.

Focused validation passed **277 checks across 14 suites**, including 19 new overall policy tests, 13 Node member-desk rendering tests invoked by its Python gate, dashboard syntax/filter tests, primacy tests, workbook preservation, package regressions and Python/JavaScript network-formula parity. Independent review found no blocking issues in the core, projections, filters or workbook plan. A separate audit reconstructed the live candidate's ranks, cohorts, tensor values, evidence counts and all overall standings.

The coordinated rebuild and final publication audit passed. The dashboard, member desk, combined local page, combined email page, workbook and ZIP packages all use the reviewed generation. The final audit verified the embedded payloads in all four HTML pages, every original analytical dashboard/member field, all 30 original worksheet cell blocks, the unchanged 9,594 field records, and byte-exact ZIP round-trips. All nine protected analytical input files remained byte-identical during activation. Tier 2 and Tier 3 retain their exact original memberships.

The all-in-one package is **14,291,525 bytes**, below the unchanged **14,680,064-byte** limit; its delivery alias matches exactly. The family ZIP is 5,269,777 bytes. Rollback copies and the activation receipt are retained.

All three artifact-rendered workbook views were inspected and are legible. The artifact runtime again exited abnormally during teardown after export; the publisher accepted the output only after verifying its bound author receipt, hashes and every authored cell independently. Browser visual inspection remains unavailable because the browser blocked local-file URLs; no workaround or browser walkthrough is claimed.

The existing family ZIP's omission of the deferred member-profile script remains a pre-existing limitation. The combined all-in-one package embeds the profile content and is the self-contained offline deliverable checked by the publication audit.

Evidence: [candidate and preservation receipt](audits/overall_stance_implementation_20260913/candidate_receipt.json), [independent review](audits/overall_stance_implementation_20260913/review_receipt.json), [focused tests](audits/overall_stance_implementation_20260913/tests/receipt.json), [activation](audits/overall_stance_implementation_20260913/activation_20260913T024136Z/receipt.json), [delivered-artifact verification](audits/overall_stance_implementation_20260913/published_projection_receipt.json), and [operating policy](fec/stance/RANK_HONORS.md).
