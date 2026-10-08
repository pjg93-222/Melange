# Coordinated desktop design adjudication

User approval: the Higgsfield layout is approved, with an instruction to first review and reconcile the work in **Update Melange branding and debug** (task `01a082b3-a647-70e0-9277-e00beec7b416`). This document supersedes the original charcoal/copper proposal's visual identity. It does not certify a finished app or a data release.

## Decisions

| Element | Decision | Reason |
|---|---|---|
| Brand identity | Adopt the existing America's Credit Unions palette and type pairing | The branding task inspected the organization's site and implemented this identity in both dashboard and People styles. |
| Navigation | Retain the existing 184px sidebar, destinations, deep links and keyboard behavior | Preserve the approved newer layout and restored features. Avoid a second competing navigation shell. |
| Main composition | Adapt the approved Higgsfield composition: compact route controls above a large map, with a 300px collapsible person panel | Reduce controls competing with the map and make individual connections easier to inspect. |
| Reading surfaces | Cream background, near-white cards, purple text; sans-serif controls and body text, serif page/person headings | Match Members and the organization while keeping dense records readable. |
| Network canvas | Deep purple canvas; cream labels and controls; restrained gold selection and teal accents | Preserve contrast and the visual continuity of the existing graph. Review categorical evidence colors independently of UI colors. |
| Network modes | Visible adjacent Staffer and Ecosystem controls; expose model status beside them | A shared person record can support two separate networks. Membership or co-reporting must not silently become a coworker relationship. |
| Evidence | Selected connection shows source, period, relationship type and uncertainty; expandable evidence archive | Explain why each edge exists without crowding the map. |
| Existing repairs | Retain heading specificity, disclosure chevron escape, themed View options and Notes & exports | These were concrete fixes with reported UI checks. |
| GovInfo overlay | Preserve the 22 decisions and their existing non-scoring treatment | This is independent legislation work, not a staffer population or scoring change. |

## Visual contract

- Purple `#342649`: navigation, graph ground and text on light surfaces.
- Cream `#f7ede4`: main reading background; paper `#fcf7f4`: panels.
- Gold `#eca91c`: selection, focus and accents on dark surfaces; never normal text on cream.
- Teal `#8cc3c4`: restrained accent and selected borders; use purple text on teal controls.
- Articulat CF for body, forms and numerical data; Aptos / Segoe UI fallbacks. Freight Text Pro for page and person headings; Georgia fallback. Keep network labels sans-serif. Existing hosted fonts must have usable fallbacks; do not package font files without established redistribution rights.
- Keep the map's available area large; collapse the person panel for full-width exploration. Small screens stack details after the map and retain direct section links.
- Wheel/button zoom, Fit, Focus person and Focus route remain available. Render individual supported connections at suitable zoom; grouping circles must not imply relationships.

## Data and interaction boundaries

The future Staffer mode uses the validated directory-led work-proximity × overlapping-time model. Until that cutover passes, label the available engine **Work & background — existing model**. A design change must not rename it into the promised new model prematurely.

Ecosystem includes explicitly labeled shared lobbying activity, shared filings and registrant/client-period associations. Period associations do not establish employment or familiarity. Missing dated work coverage is described as missing evidence, not social isolation. Politico remains preferred in directory reconciliation; payroll remains targeted to ambiguities; internship roles do not contribute staffer ties.

Preserve query selection, person links, route mode, origin/destination, zoom/focus controls and source inspection when navigating or reloading. The app launcher, live URL and generated dashboard must use the same versioned presentation assets. An older embedded page must never flash into view during initialization or return on reload.

## Review findings and completion gates

The branding receipt reports 46 legislative tests, 7 dashboard tests and 5 People navigation tests passing. People inventory was still loading during its browser inspection. Those checks support the reported theme and overlay work; they are not proof of full network readiness. A later separate dashboard receipt verifies member rendering and fonts, not this proposed People layout.

Current source inspection found two controls referencing undefined `--ml-line2`; define it consistently with the existing secondary border color. The canvas renderer still contains hard-coded old-theme background and label colors. Reconcile those during layout implementation, preserving semantic layer colors and checking selected routes and labels against the final canvas. CSS-only theming cannot change canvas pixels.

Before coordinated release, verify desktop and narrow layouts, visible ecosystem selection, Kathleen's documented connections and route evidence, independent person/edge inspection, deeper zoom, back/forward/reload consistency, model labels, and font fallback. Check live and regenerated copies against the same asset hashes. Run focused regression checks after relevant changes; do not repeat unchanged legislative tests.

The current unsigned native executable remains blocked by Windows Application Control. Design approval does not resolve the pending choice between an installed Edge app window and a signed native installer. No desktop installation or complete cleanup is claimed here.

## Evidence reviewed

- [Branding verification](../govinfo_acu_integration_20260908/theme_verification.json)
- [GovInfo and branding receipt](../govinfo_acu_integration_20260908/RECEIPT.md)
- [Later member UI verification](../self_update_20260908/live_browser_verification.json)
- `fec/surfaces/staffer_live/melange-dashboard.css`
- `fec/surfaces/staffer_live/staffer-live.css`
- `fec/surfaces/staffer_live/staffer-explorer.js`
- `fec/surfaces/staffer_live/index.html`
- Approved Higgsfield composition: job `39a57dd3-763b-4f5a-aee0-1c49d21be6fe`; no additional image generation required.
