# Ecosystem route adjudication — Kathleen Coulombe pilot

September 8, 2026. Read-only investigation; proposed relationship classes have not been activated.

## Findings

The activity index joins people on the same source activity ID: an issue section within a filing. It does not expand to everyone in the same quarterly filing. Its displayed label, shared lobbying report, obscures this narrower implementation. Historical issue-section records are searched, but the returned neighbor evidence retains the latest period rather than aggregating repeated periods into a duration measure.

Kathleen's two previously confirmed source identities have 23 activity rows across 22 distinct quarterly filings: ACLI for 21 quarters from 2021 Q1 through 2026 Q1, and America's Credit Unions for 2026 Q2. This is the available corpus history, not her entire career.

The source-only audit finds 15 other LDA identities in her issue sections and 24 in her whole filings. Nine additional whole-filing candidates are Kimberly W Ross (10 shared quarters), Marti Thomas (10), Douglas Lathrop (6), David Leifer (15), Dianne Sullivan (4), Ian Steger (21), Jeffry Janoska (21), Paul Kangas (21), and Joyce Meyer (13). These are source identities before final identity/eligibility adjudication. Same-registrant, same-quarter expansion adds no further candidates for Kathleen in this corpus; it can still matter for firms filing separately for different clients.

Independent source inspection confirms Kathleen appears in the retirement issue section and Jeffry Janoska/Doug Lathrop in the tax section of the same ACLI 2026 Q1 report:
https://lda.gov/filings/public/filing/f11fb96a-0d51-4e80-837d-715e6a9134ca/print/

The current live result has 14 collaborators rather than the 15 source identities. Gregory Mesack (source 148612) is present in source activity evidence but absent from Kathleen's collaborator result. The person API resolves him to 121707 with REFERENCE_RESOLVED_SAME_PERSON, retaining IDs 121707, 148612 and 70066. ActivityIndex explicitly propagates USER_CONFIRMED aliases but not this reference-resolved class. Repair must consume the established identity mapping consistently and test both routing directions; do not create a new name-based merge. Evidence: gregory_identity_audit.json.

## Proposed relationship classes

1. Same issue section in the same filing: reported issue-team association, with exact filing and reporting period.
2. Same registrant and same quarterly filing, different issue sections: reported organizational association. Especially useful for in-house advocacy teams; weaker proximity than a shared issue team.
3. Same registrant during overlapping reporting periods across different client filings: reported firm association. Retain registrant versus client roles; working for a firm is different from representing its client.
4. In-house team and outside firms representing the same client during the same period: a client-mediated ecosystem path. Display the organization between the people; do not silently convert it to coworker evidence.
5. Independently documented employment, board, task-force or working-group overlap: dated professional associations. Reconcile the exact people, organization and dates before routing.
6. A former coworker or reported collaborator's verified government employment: bridge from the ecosystem into the operational staffer network. Each hop retains its relationship type and period.

Common issue codes, bill mentions, chamber-level contact statements and broad association membership are discovery context. They alone do not establish a person-to-person relationship. Statements that a report contacted the House or Senate cannot identify a particular member or staffer. Do not infer all employees knew one another because their employers share a parent organization.

## Proximity and time

Keep the two dimensions. For ecosystem associations, proximity is an explicit relationship class: issue team, organization, firm or client-mediated connection. Time is distinct observed shared reporting periods, with gaps retained. Twenty-one quarters is repeated quarterly evidence, not proof of continuous daily collaboration over 5.25 years. Store date precision separately from proximity. Exact work intervals remain the operational network's duration measure.

Deduplicate issue sections and amendments within a period. Repeated records should strengthen the same tie with diminishing returns, not add independent parallel ties or multiply a quarter's duration. The same evidence appearing in both an issue section and a whole filing contributes once at the strongest supported class. Keep historical evidence inspectable even when a more recent period is used for route display. Recency, if used for introduction usefulness, should be shown separately from accumulated duration.

## Adjudication and evaluation sequence

First repair loss of already-adjudicated aliases and establish reciprocal collaborator results. Then adjudicate the nine whole-filing candidates: active lobbyist section, filing version/amendment, registrant/client classification, exact identity, internship exclusion, and reporting-period bounds. Preserve accepted, rejected and unresolved decisions with evidence and reasons.

Evaluate the new relationship classes in a separate candidate graph before activation. Compare Kathleen and a stratified sample of similar in-house heads, outside-firm lobbyists, small teams, large registrants and ambiguous identities. Measure reviewed edge precision, recovered valid connections, degree changes by source and organization size, duplicate-period inflation, route availability, weak steps per route and all-shortest-path changes. Include negative controls: same firm in nonoverlapping periods, unrelated clients, same issue at unrelated firms, same-name people, superseded reports and interns.

Avoid complete organization cliques: retain organization/period membership evidence and generate candidate neighbors on demand. Rank ties using specificity and repeated distinct periods, and explain large-team associations rather than imposing an arbitrary degree cap that hides valid evidence.

Kathleen's missing biography roles at ACLI, SHRM, Defense and the Nevada Governor's Office, plus her professional-association leadership, provide targeted research leads. Confirm dates and specific counterpart roles before creating new person-to-person links. Payroll remains targeted support for ambiguities; it does not become the default population source. LDA stays within the ecosystem layer.

## Artifacts

- adjudicate_kathleen_routes.py: reproducible read-only extraction.
- kathleen_route_adjudication_candidates.json: candidate source identities and every supporting activity/filing/period.
- gregory_identity_audit.json: live reference-resolved alias evidence.

No production routing rules or identities changed during this adjudication/design pass.
