# Mentat Chart Studio design draft — 2026-09-13

Status: for user review. Defect repairs are implemented separately; the state-destination and two-chart features below are not yet implemented.

## Confirmed design requirements

- Recipient committee address and candidate represented state are distinct selectable views.
- Split view contains two independently configured charts side by side, with optional linked filters.

## Two-chart workspace

Each pane owns a saved chart, source workbook, location view, accounting basis, chart type, dimensions, measures, cycles, filters, query revision, and record inspector. Editing a chart affects that pane. Changing the active pane moves the existing field shelves and analytics controls to that chart. Both charts remain visible. On narrow screens panes stack in A/B order.

The comparison toolbar offers links for Company, Party, and State, off or on individually. The interactive draft demonstrates Company and State. Recommend Company linked initially, with cycles and location views independent. Turning a filter link on explicitly copies the active pane's filter to the other pane. Links apply only to compatible fields; an unavailable field produces a visible explanation. A linked state uses the same label in each pane's location view, which remains plainly visible. Unknown, ambiguous, national/not applicable, DC, territories, and foreign locations must not silently become a US state or zero.

Provide a shared-scale option only for compatible measures, units, location definitions, and chart families. Never compare dollar amount and percentage on one implicit scale. Source changes invalidate each affected pane and its inspector independently. Save the pair and its link settings; export either chart or both with titles, cycle scope, accounting basis, and provenance. Keep observed money visibly distinct from projections.

## Workbook-generated destination data

Generate location fields alongside the complete eligible receipt data, before chart aggregation:

| Field | Meaning |
| --- | --- |
| Recipient committee state | State in the receiving committee's reported address, with evidence period |
| Candidate represented state | State of the candidate uniquely linked to the receiving committee for that cycle |
| Location status | Known, unknown, ambiguous, or not applicable/national |
| Location evidence | Source identifier, candidate/committee link, and effective/reporting cycle |

Add a State Destinations worksheet and expose both fields in Recipient Detail / verified source observations. Each summary row retains company, cycle, accounting basis, location view, destination, amount, and receipt count. Treat the two location views as alternative partitions of the same receipt population; they must never be summed together. Totals including unresolved destinations must reconcile to the eligible receipt total in each view.

A national committee receiving money is not proof that the money reached its later candidate beneficiaries. Show complete downstream committee-to-candidate activity as a separately labelled stage, with its own accounting basis and support/opposition distinctions. It describes associated committee activity, not traced company dollars. Do not derive state totals from the top-100 Beneficiary Summary or the repeated company-to-beneficiary bridge. Do not allocate one receipt's full value to multiple linked candidates. Missing cycle-specific mappings remain unresolved.

Implementation crosses R enrichment/export, the workbook payload and builder, the complete contribution warehouse, query field metadata, and Chart Studio. Add cache/schema revision stamps. Published workbooks require regeneration after design approval; an old workbook without destination fields must show that the view is unavailable.

## Review choices

The interactive draft has independent location, cycle, chart type, company, and state controls, optional linked filters, and a second tab for proposed workbook sheets. Values and recipient names are illustrative. Proposed initial layout: two equal-width panes, settings above each chart, Company linked, other filters independent. The design controls also offer a single-column settings arrangement.

After layout review, implement the workbook-to-chart path and saved chart-pair model together, then verify reconciliation, missing/ambiguous locations, independent queries, linked filter behavior, source-change invalidation, persistence, export, and responsive layout.
