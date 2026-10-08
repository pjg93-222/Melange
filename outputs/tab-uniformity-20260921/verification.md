# Tab consistency review — September 21, 2026

Reviewed Loading, Collection, Graph, Chart Studio, Insights, Cross-reference, and PAC evidence.

The existing shared stylesheet excluded PAC evidence from navigation, workspace spacing, title styling, focus and selection treatment. All seven workspaces now use those shared rules. Matching scope controls share sizing and label treatment; panels share borders and radii; primary actions, section heading sizes, table headings, and links use the existing palette and typography consistently. Specialized chart, collection, and map layouts are preserved.

Source changes: mentat/app/workspace-polish.css and mentat/tests/test_workspace_polish_browser.cjs. Existing unrelated working-tree changes were retained.

Validation:
- Seven tabs at 1168, 900, and 390 pixels: all 21 layout checks pass, with matching navigation/page computed styles and no horizontal page overflow.
- Browser flows cover roster keyboard focus, status isolation, coverage disclosures, Studio mobile Data/Inspector controls, cross-reference refresh focus, and adding a PAC pane. No browser exceptions or remote requests in this fixture suite.
- PAC map browser suite: all 23 steps pass, including layer toggles, district selection and clearing, cycle selection, return to panes, and permalink restoration; no browser or console errors.
- Golden HTML matches the templates.
- Impeccable detector returned an empty findings list. Screenshot inspection covered the rendered tabs; final-review.png contains desktop, intermediate, and mobile views. Data in these captures is synthetic test data.

No collection jobs were started and no production reports were changed.
