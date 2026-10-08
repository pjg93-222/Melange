# Mentat: six workspace UI review

Scope: Loading, Collection, Graph, Chart Studio, Insights, and Cross-reference. The PAC map was completed in the preceding pass. Impeccable refinement preserved the existing plum, teal, ivory, and financial/evidence vocabulary.

## Visual review

- Generated and inspected one Higgsfield reference per tab. Exact URLs are recorded in `references.json`.
- Captured a baseline, inspected one desktop/mobile implementation batch, applied one correction batch, and inspected the final confirmation batch.
- `comparison.html` pairs each reference with a local screenshot at **1168 × 880**, with an opacity overlay and full-page/mobile views.
- Local fixtures are synthetic. No production collections were started, reports overwritten, or financial values invented for the live app.
- Generated content was not treated as financial truth. The implementation retains actual source labels, coverage cautions, worker-record fields, amounts, accessible controls, and accounting distinctions. Resulting content lengths differ from the references; this is not a pixel-identical certification.

## Changes

- Loading: simpler roster structure, tighter setup form, readable mobile coverage rows, and focus restored after removing a company.
- Collection: working details before coverage tables; workers/activity beside reports/events; coverage and freshness disclosures retain the full underlying evidence.
- Graph: full-width scope controls, consistent chart headings/actions and a two-column overview.
- Chart Studio: one heading, narrower side panels, three columns at desktop reference size, a mobile Data & fields control, visible Inspector access in Canvas mode, and larger worksheet chart text.
- Insights: grouped scope actions, three desktop analyses, less unnecessary chart space, preserved evidence/export access.
- Cross-reference: shorter introduction, compact scope with the accounting-of-record statement, aligned amounts, collapsible unmatched adjustments, separate large-receipt section, and focus/disclosure continuity on same-run refreshes.
- Shared navigation keeps the selected tab visible after resizing. Completed status messages no longer carry into unrelated tabs.
- Build fingerprints now include relative paths and deterministic ordering. The added geography directories legitimately reuse state filenames; tests verify that swapping bytes between same-named layers changes the fingerprint.

## Validation

- New `test_workspace_polish_browser.cjs`: six tabs at 1168, 900, and 390px; **18 layout checks**, no document overflow, no browser exceptions or remote requests. Exercises roster focus, status isolation, evidence disclosures, Studio Data/Inspector/Canvas behavior, and refresh focus retention/reset across run identity changes.
- Comprehensive console browser suite: Graph scopes, JFC, employee levels, direct/downstream separation, exports, chart builder, coverage/freshness disclosures, responsive navigation, skip link, and keyboard tabs.
- Navigation scope browser suite: **13 steps**, including permalink persistence, Studio handoffs, saved views, and Cross-reference industry scope.
- Insights browser and control suites: lazy loading, eleven toggles, sources, exports, stale response rejection, failure recovery, scope/filter behavior, keyboard focus, and unavailable storage.
- Studio click-to-add, worksheet guard (three cases), data-source disclosure, and Canvas/Inspector browser coverage.
- Cross-reference scope and rendered-evidence tests; coverage rendering tests.
- Template/CSP/asset fingerprint suite: **10 passing tests**. Golden HTML regeneration check passes.
- Impeccable detector invoked once for this six-tab pass, returned exit 0 without output. Rendered inspection was performed separately.

All checks run with temporary local fixtures. Browser tests that use isolated HTML fixtures are complemented by the new suite loading the real application and complete stylesheets.
