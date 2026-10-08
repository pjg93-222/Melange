# Staffer extraction, reconciliation, and social-network completion

Status: **PASS** (2026-09-03)

## Name and payroll coverage

- The official House SOD PDF corpus from 2009Q3 through 2015Q4 was reparsed from all 26 reports.
- All 275,047 indexed name references resolve to a parsed payroll row (100%).
- 385,480 of 385,486 person-bearing rows were parsed (99.9984435%). The six retained residues are explicit unresolved ditto rows, not silently discarded names.
- The corrected House ledger contains 1,066,657 observations, 79,264 distinct payee keys, 137,402 office spans, and 52,887 member-quarter rows across 67 quarters.
- The verified Senate committee corpus contains 35,004 accepted rows from 30 report packages. All 35,004 source checks pass.
- Bare official Senate committee headings (for example `JUDICIARY`, `FINANCE`, and `HEALTH, EDUCATION, LABOR, AND PENSIONS`) are now classified as committee. Before this correction, 34,035 verified committee rows incorrectly fell into the administrative fallback.

## Identity and personnel spine

- Final review-only personnel spine: 142,135 people and 201,239 person-office spans.
- All 1,334,562 admitted payroll observations are conserved exactly once in the span payload.
- Container mix: 135,647 member-office spans, 24,988 committee spans, 18,018 administrative spans, 4,567 leadership spans, and 18,019 unresolved spans.
- Gordon Holzberg resolves to one review-only spine person with two day-precise House stints: Alma Adams through 2023-02-09 and Emilia Sykes beginning 2023-02-10. The trajectory contains one `ABUTTING` move with `gap_days=0`.
- Stephanie Belk resolves to one review-only spine person attached to David Vitter (`V000127`) over seven Senate payroll periods.
- Primary and twin spine payloads are byte-identical. The independent verifier re-derived every emitted row and passed all schema, conservation, source-binding, link-status, language-law, and anti-promotion checks.

## Social network

The graph retains the existing modeling defaults and keeps four analysis layers separate:

1. `co_tenure`: person-to-person, only when guaranteed service calendars overlap.
2. `membership`: person-to-office/committee container.
3. `revolving`: Member-office container to LDA registrant organization.
4. `policy_area`: current person-to-policy-area categorical membership; undated and never included in duration-weighted work.

Congress's own network is untouched. Member offices are attachment containers; the graph emits zero Member-to-Member/container-to-container edges.

Final graph counts:

- 145,933 nodes: 142,135 people, 2,029 office containers, 1,734 organizations, and 35 policy areas.
- 14,958,104 emitted edge rows.
- 12,104,859 guaranteed co-tenure edges.
- 2,639,847 possible-only review edges with zero operator weight.
- 13,762,134 same-container, zero-overlap pairs rejected and never emitted.
- 201,239 person-to-container memberships.
- 5,717 revolving-layer rows, of which 4,627 guaranteed rows enter the operator.
- 6,442 person-to-policy-area memberships across 691 strictly joined people and 35 policy areas.
- The largest weighted component contains 145,621 nodes (99.7862% of the node universe).

The primary and twin graph payloads are byte-identical. The edge payload SHA-256 is `225c8e61d0694bd1a0075e5ec2ee3210dec5f7d39e2a1976aab27b4a077263c7`; the canonical artifact-family hash is `153955fa88997e91fb879eb26ac08e45e46da25d6c01b8424759dfc93d040a4d`.

## Verification receipts

- House complete reparse: `house_sod_payroll_complete_20260903_v5_primary/house_sod_complete_reparse_receipt.json` — PASS, SHA-256 `e98a215a70b1ac6e7e362b0ea7a0cdceaf06d35a5233f2ef5d120ac96e68f375`.
- House name matching: `house_sod_pdf_lda_name_matches_20260903_v3_verification/verification_report.json` — PASS.
- Senate committee payroll: `senate_committee_payroll_20260903_v3_verification_v2/verification_report.json` — PASS.
- Personnel spine: `hill_personnel_spine_20260903_v5_verification_r3/hill_personnel_spine_verification_receipt.json` — PASS.
- Social graph: `staffer_social_network_20260903_v2_verification_r2/staffer_social_network_verification_receipt.json` — PASS, zero failures.

The graph verifier independently reproduced all 28,506,840 distinct same-container candidate pairs, matched the guaranteed/possible/rejected split exactly, found zero layer-semantic violations, recomputed 2,000 sampled overlap-day totals with zero mismatches, matched connected components and committee ablations, and found zero self-loops, Member-to-Member edges, promoted rows, or non-review rows.

## Intentional limits retained from the plan

- All artifacts remain review-only; canonical identity and employment promotions are zero.
- Policy-area cards are a current undated snapshot. They use categorical weight 1 only inside the separate policy layer and duration weight 0.
- Committee side is known as majority/minority for 1,053 of 24,988 committee episodes; 23,935 remain `UNKNOWN`. The plan's existing fallback kappa remains in force.
- Verified official full House reports before 2009Q3 were not located in digital form; 1996Q1-2008Q4 remain explicit evidence gaps rather than inferred payroll.

## Project-brain update draft

Suggested STATE entry: complete House SOD reparse (2009Q3-2015Q4), corrected combined House/Senate spine v5, and four-layer staffer social graph v2 are PASS with byte-identical twins and independent verification. Preserve review-only status, separate Congress layer, day-precision same-quarter non-overlap rule, and bare Senate committee-heading vocabulary.

Suggested DECISION entry: a same-quarter House office transition may join one spine person only when every observation in both office nodes has valid printed service dates and the inclusive day ranges do not overlap. Bare headings found in the verified Senate Volume II committee corpus are committee containers even when the printed header omits the word `COMMITTEE`.
