# Mentat visual analysis — implementation prompt

Status: proposed implementation brief, based on three Higgsfield mockups. Awaiting visual direction confirmation. This document does not record approval to implement.
User-selected workflow: **Compare giving, then trace it to evidence.**

## Copy-ready prompt

Redesign Mentat's **Graph, PAC evidence, and Insights** workspaces as one coherent visual analysis experience. Work in the existing local application at `C:/Users/pgoff/Mentat/mentat/app`. Preserve Mentat's recognizable plum, teal, ivory, serif headings, sans-serif controls, existing workflows, evidence access, and financial distinctions.

The result must make the data—not filters, warning blocks, or tiny repeated cards—the dominant content. Matching a few CSS values is insufficient. Unify information hierarchy, chart presentation, selection behavior, evidence inspection, and navigation across all three workspaces.

### Start from the actual application

Read `mentat/AGENTS.md`, `PRODUCT.md`, the applicable Impeccable instructions, existing templates and shared styles, and `mentat/INSIGHTS.md`. Preserve unrelated working-tree changes.

Identify the running Mentat instance, its source checkout, build fingerprint, port, and cached assets before editing. Establish whether the user is viewing this checkout. Capture the three current tabs at the user's actual viewport when available and at 1440 × 1000, 1168 × 880, 900 × 844, and 390 × 844. Never call a screenshot from a different server or fixture proof that the user's application is updated.

### Visual references and authority

Use these three proposed Higgsfield compositions together:

- Graph: https://d8j0ntlcm91z4.cloudfront.net/user_3J1aVESwhbXLraSW8PtRFWWgpV2/hf_20260921_142126_e50a039b-85a1-4ef8-9ad1-b14b327933fc.png
- PAC evidence: https://d8j0ntlcm91z4.cloudfront.net/user_3J1aVESwhbXLraSW8PtRFWWgpV2/hf_20260921_142127_9f2289b3-75a0-4df9-abe9-908ae7e7180e.png
- Insights: https://d8j0ntlcm91z4.cloudfront.net/user_3J1aVESwhbXLraSW8PtRFWWgpV2/hf_20260921_142126_45b09094-e866-4602-b792-0c913bcbdfb3.png

Use their large plotting areas, clear hierarchy, compact scope controls, and chart-to-evidence relationship. The written requirements below resolve disagreements between images. These images contain illustrative data and generated errors; they are not financial, geographic, or interaction specifications.

Keep the existing seven-item navigation. Use the same application shell on all tabs. Do not build another app or create three independent themes.

### One shared visual system

Use existing theme tokens wherever available:

- Primary text and actions: plum `#342649`.
- Comparison/baseline: purple `#57447B`.
- Observed selected series: teal `#327A7A`.
- Focus accents: gold `#ECA91C`, sparingly.
- Workspace: `#FAF8F6`; plotting surfaces: white.
- Negative amounts: the existing negative semantic color, never silently recast as positive.
- Unknown, unavailable, and observed zero must remain visually distinguishable.

Use one fixed desktop sidebar width across every tab; retain the current 180px width unless the approved reference requires a deliberate shared change. Use 28px desktop workspace gutters, 16px mobile gutters, and a 4/8/12/16/24/32px spacing scale. Page titles: 30px desktop, 27px mobile. Section/chart headings: 22px. Descriptions/body: 14–15px. Chart and control labels: at least 12px at their actual rendered size. Controls: 40px desktop and at least 44px touch targets. Use 7px panel radii, 5px controls, and fine neutral borders. No gradients or ornamental shadows.

All three pages follow the same order:
1. Title, short description, consistent Export and Sources actions.
2. Compact scope controls, with advanced options disclosed.
3. One readable scope line naming source, period, accounting basis, and material coverage limitations.
4. Underline-style analysis navigation.
5. The dominant visualization, followed by supporting analyses and evidence.

Keep the sidebar's solid-plum selected state distinct from the shared underline analysis navigation. Charts use the same segmented Chart / Table control and Export action in the same positions. A record detail panel does not receive a meaningless Chart switch. Source links and selection-clearing actions use identical labels and placement.

Create or reuse a small shared chart frame and evidence-detail pattern; consolidate conflicting rules at their correct source rather than append another layer of broad overrides. Preserve specialized map, chart-building, and collection behavior.

### Graph: compare first

Lead with a large, sorted horizontal bar chart for the current recipient breakdown. It should occupy about two-thirds of the desktop analysis row, with an adjacent evidence detail area when a supported item is selected. In the unselected state, give the chart the available space rather than reserve an empty rail.

Keep Overview, Recipients, Candidates, and Companies available. Preserve existing recipient, candidate, company, employee-level, and funding scopes. Keep supported breakdowns and chart-studio handoffs accessible.

Use full recipient labels where practical, zero-based axes, sensible tick units, signed values, aligned amount columns, and visible selection. Clicking a mark and keyboard activation must expose the same exact values and available source records. Company comparisons should use an appropriately large supporting chart, not shrink the main chart into a grid of tiny cards.

The Open PAC evidence handoff must use an exact available committee identity and compatible cycle. It opens reported PAC activity in its own accounting scope, explicitly distinguished from industry-associated receipts. Missing evidence should explain availability; never fabricate a source-record link from an aggregate.

### PAC evidence: locate, compare, inspect

Preserve source import, snapshot selection, multiple PAC panes, comparison, Raised/Spent, cycle, geography layers, map navigation, routes, records, and filing access. The reference depicts a selected single-PAC Geography state; it does not authorize removing multi-PAC workflows.

Use a large map with an adjacent selected-place detail panel and a directly linked ranked bar list. Map, list, and records must represent the same PAC/cycle/direction/filters. Selection must highlight the corresponding geography and ranking, expose exact amounts and available filing links, and clear consistently.

Use real existing geographic boundaries and actual reconciled data. Show units, the scale and its domain, unlocated amounts, and missing coverage. Use one scale across multiple panes when comparison is enabled; otherwise identify independent scales. Retain explicit treatment of net negatives. Missing geography must not appear as a proven zero.

Show located + unlocated = scoped reported amount only when the current response reconciles that way. Preserve route-transfer accounting and internal-transfer treatment. Reported PAC activity does not establish that a company's receipts funded a particular candidate. Never replace evidence with a decorative donor-to-candidate Sankey.

### Insights: give each analysis enough space

Use a dominant full-width trend comparison, with Favorite recipients and What changed below in two generous columns. At narrower widths, stack charts instead of shrinking labels. Preserve all eleven available analyses, their enable/disable controls, scope options, source inspection, and CSV/JSON exports.

Use existing same-stage and full-observed trend amounts with their labels and actual granularity. The current trends response supplies cycle-level observations; the mockup's monthly cumulative overlay is aspirational. Do not interpolate cycle totals into monthly points, invent a trajectory, or introduce cumulative semantics without a verified supported data contract. A readable cycle comparison is the default fallback; two points may be better represented as a paired bar or slope comparison. Preserve time gaps and source coverage limits.

Show recipient comparisons only where the current response supplies comparable series. Label each comparator and denominator. The waterfall must reconcile exact signed-cent baseline, change components, and current amounts within one funding channel. Newly/no-longer observed records must not be described as proven changes in intent. Forecasts remain unavailable when the existing completeness requirements are unmet.

### Chart and evidence contract

- Use live semantic HTML and responsive SVG/canvas; never ship the mockup image as the interface.
- Scale marks from values. Resize the drawing surface; do not scale a fixed SVG viewBox so its labels become unreadable.
- Retain current financial classifications, integer-cent calculations, provenance, source hashes, query boundaries, and authoritative report directory.
- Keep personal giving, corporate receipts, PAC transfers, candidate activity, and modeled attribution separate. Common colors must not imply common accounting.
- Hover, focus, and selection disclose the same amount, unit, date/cycle, basis, source context, and coverage.
- Preserve selection and supported scope on compatible handoffs. When scopes cannot translate, explicitly show the new scope.
- Use exact accessible tables and exports. Tables and charts must reconcile to the same query and snapshot.
- Use labels and shape as well as color. Keep reduced-motion support, visible keyboard focus, logical focus return, keyboard-operable marks, and non-map evidence access.
- Loading, no observations, unavailable coverage, error/retry, one-row, negative-only, long-name, and stale-response states must be deliberate. Unknown never becomes zero.
- Preserve material cautions beside the visualization; move repeated methodological prose into a consistent disclosure.

### Responsive composition and acceptance criteria

At 1440 × 1000, begin meaningful data visualization within roughly the first 300px of the workspace and devote at least 60% of the remaining first viewport's main content area to plots, maps, or ranked graphical comparisons. Treat this as a visual hierarchy target, not a reason to hide essential scope or warnings.

At 1168px, retain readable plotting widths and move the detail rail below when necessary. At 900px, collapse the navigation and reflow filters. At 390px, show one readable chart at a time with touch targets, wrapped labels, and an inline/detail drawer pattern. Local table scrolling is acceptable; whole-page horizontal overflow is not.

Acceptance requires:
1. All three screens visibly belong to the same application: fixed shell alignment, matching typography, controls, chart actions, selected states, and evidence patterns.
2. The user can compare giving, select a real mark, inspect exact evidence, and return without losing context.
3. PAC map and ranking selections agree; clearing geography restores the appropriate source rows.
4. Insights renders only supported comparisons and reconciled change components, with readable labels.
5. No dropped existing feature, changed accounting output, fabricated record, inferred completeness, or source-scope leakage.
6. The other four tabs remain usable and share the unchanged navigation shell.
7. Rendered screenshots demonstrate the intended chart prominence—not just passing DOM or overflow assertions.
8. Targeted browser suites cover navigation/scope, Graph data and handoffs, PAC panes/maps, Insights controls/sources, responsive layouts, and template parity; no new browser errors.
9. Final verification confirms the user's running instance serves the changed assets. If a reload or restart is needed, explain and perform only the necessary supported action.

Inspect desktop, intermediate, and mobile captures together; fix material issues in one batch and confirm once. Follow the applicable Impeccable independent review workflow when implementing. Compare the actual render with the agreed mockups and these corrections, report specific unresolved differences, and do not claim perfection from test counts.

Deliver the implemented changes, a concise before/after explanation, representative screenshots of all three views, test results, and the verified running build identity.

## Corrections identified in the generated mockups

- Analysis-tab treatments and Chart/Table controls differ between generated screens. Standardize them using the written shared system.
- Graph places Chart/Table controls on a record-detail panel; omit these there.
- Graph's fictional company and recipient totals do not describe a reconciled common dataset. Never reuse those values as application data.
- PAC evidence invents an “Accrual basis” footer and a recipient detail. Replace both with actual response metadata and verified records.
- The generated geographic illustration is a composition cue, not an authoritative map.
- Insights' monthly cumulative chart exceeds the current trend payload; use available cycle-level values unless a separate verified monthly implementation is approved.
- Generated numbers, names, positions, and cutoff marks are illustrative. The written accounting and interaction rules take precedence.

