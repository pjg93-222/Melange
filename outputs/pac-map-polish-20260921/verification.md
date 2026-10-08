# PAC map interaction and layout verification

2026-09-20 local / 2026-09-21 UTC. Scoped to the PAC evidence map. Browser fixtures use real Census geography and synthetic receipts, not verified political-finance findings.

## Behavior

- Ordinary wheel scrolling stays with the page; Ctrl/Command + wheel and trackpad pinch zoom the map. Zoom buttons and keyboard navigation remain available.
- New navigation cancels a fly animation immediately. Pan stays within bounded canvas limits.
- Search has an explicit Find action. Repeating a search is idempotent. Search text/caret and keyboard focus survive toolbar updates, including state/chamber changes.
- Selecting a district or ZIP preserves comparison across visible geography. Heat colors and endpoints rescale after focusing a state or settling a pan/zoom. National outliers do not set the Texas range.
- Enlarge/Collapse retains the same SVG and zoom, expands across the workspace, and moves rankings below. Phone enlargement avoids vertical letterboxing.
- Stable committee heading, compact grouped controls, phone layer selector, unobstructed phone map, inline heat strip, neutral reference boundaries, and source disclosure. Provenance and approximation warnings remain available; the main source label stays visible.

## Evidence

- `node --test mentat/app/tests/evidence-map.test.js`: 17 passed.
- `node mentat/tests/test_evidence_map_interaction_browser.cjs`: all 22 steps passed; zero page/console errors. Includes every overlay, late-response race, absent chamber, source labels, search, keyboard focus, phone layout, reduced motion, enlargement and SVG retention.
- Latest interaction measurement: wheel-transform JavaScript median 0.80 ms, max 1.80 ms over 30 samples; 667 markers, below the 800 cap. This measures transform work, not total frame/paint time. First open was 1.95 s including localhost requests.
- Real-geometry rendering suite passed: 33,780 ZIPs -> 520 clustered markers; Texas lower-chamber paths 150 -> 6 in a tight viewport; focus recolors retained nodes. Transform median 0.20 ms, max 0.70 ms in that isolated run.
- Final visual/interaction capture verified desktop, intermediate and phone widths without horizontal overflow: 1168/1168, 850/850, 356/356 client/scroll widths. Phone map width increased from 270 px to 330 px. Toolbar height reduced from 423.5 px to 345.3 px while retaining 44 px phone targets.
- Browser teardown exceeded the suite's 10-second cleanup bound after successful assertions. The suite exited successfully and stopped its scratch server; this is not counted as an application test failure.
- JavaScript syntax checks and scoped `git diff --check` passed.
- Impeccable detector run once: removed the in-scope thick pin-card accent; two unrelated app-shell accents were left outside scope. Rendered desktop/phone layouts were inspected independently of the detector.

## Selected design comparison

Reference: Higgsfield job `b6a2ab5e-3ef9-48e2-a728-604dc63468c0`, actual image 1168 x 880, inspected directly in the browser:
https://d8j0ntlcm91z4.cloudfront.net/user_3J1aVESwhbXLraSW8PtRFWWgpV2/hf_20260921_024245_b6a2ab5e-3ef9-48e2-a728-604dc63468c0.png

- `selected-design-desktop.png`: matching 1168 x 880 capture of the live local component, with title, toolbar, Texas map, heat index and source line. The panel occupies the workspace beside the application's navigation; the capture omits surrounding app chrome.
- `selected-design-mobile.png`: responsive 390 px browser / 358 px outer panel. Rankings and source qualifications remain below the map.
- `before-desktop.png` and `before-mobile.png`: original interaction/layout baseline. Desktop baseline outer width 1172 px, within 4 px of the reference canvas; phone outer width 358 px is identical. Baseline includes the full ranking panel; the selected desktop crop ends after the source line.
- `before-audit.json` and `selected-design-audit.json`: measured interaction and layout results.

The reference composition is implemented, but this is not a pixel-identical reproduction. Intentional differences: real Census district shapes and real synthetic-fixture amounts replace generated illustration; illustrative Mexico/ocean/place labels are absent; actual boundary lines and neutral reference states remain; Find, numeric zoom, contributor-kind toggle, keyboard focus outline and source disclosure remain functional; breadcrumb includes the source's region; desktop help is in the source disclosure and zoom tooltip; rankings and pins follow below the captured panel. No generated map pixels or invented financial values were installed.

## Files

- `mentat/app/evidence-map.js`: gesture handling, interruptible navigation, focus-aware heat domain, heat strip, neutral reference background.
- `mentat/app/evidence.js`: map controls, focus retention, search behavior, stable title, source disclosure and breadcrumb.
- `mentat/app/workspace.css`: scoped map panel, responsive controls, enlargement and legend layout.
- `mentat/app/tests/evidence-map.test.js`, `mentat/tests/test_evidence_map_interaction_browser.cjs`: focused regression coverage.

Earlier overlay work also touched map static routing in `mentat/app/server.py` and added the real-geometry browser suite. This polish did not change collectors, attribution rules, workbook values or downstream tracing. No commit was made; unrelated working-tree changes remain intact.
