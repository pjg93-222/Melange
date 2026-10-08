# Mentat Impeccable refinement — September 20, 2026

Installed official Impeccable 4.3.1 from pbakaus/impeccable at revision f2c7051853848826aac2f4646581d62a732155ad. The user confirmed the product purpose in PRODUCT.md and selected image mockups first for future design work; the project preference is `.impeccable/config.json` (`buildPath: comp`). This pass refines the existing visual identity.

## Changes

- Evidence headers wrap before actions collide. Full PAC names use the existing two-line clamp, with full names retained in titles and evidence details.
- Chip labels truncate independently of their remove buttons. Source context and other compact labels stay within available width.
- Financial figures use consistent 20px type without ellipses. Unusually long amounts can scroll; titles retain the formatted values.
- Figure grids respond to actual pane width (four, two, or one column). Removed conflicting pane-count overrides.
- Evidence filters use three columns at ordinary desktop widths and six weighted columns on wider screens. Graph search controls can shrink; Insights text cells wrap unbroken strings while numeric cells retain their existing behavior.
- Removed two redundant numbered captions from Loading. Regenerated index.html from the template.

Changes are CSS and display markup only. This pass does not change dollar aggregation, attribution, transfer selection, source evidence, or reports. `before/`, `changes.diff`, and `source-hashes.json` isolate these edits from the pre-existing dirty workspace.

## Verification

- 69 existing Node tests passed across graph layout, graph navigation, graph explorer, evidence map, and theme text fitting.
- `node --check mentat/app/evidence.js` passed.
- `python mentat/tools/render_console.py --check` passed (70,629 bytes).
- Visually inspected the running Graph and populated PAC evidence UI, including the desktop evidence layout at 1440px and narrow controls at 390px.
- At 390px, measured document scroll width was 375px (no page overflow). The populated evidence figure grid was one 300px column. All four figure values fit their 268px content widths: $98,594,280 receipts, $87,235,588 independent spending, 54 legs, and 2 cycles. These are the selected saved snapshot's existing values, not a new financial audit.
- Temporary browser viewport override was reset.

## Limits

The one Impeccable detector pass returned eight existing style warnings (five side accents, two rounded-border accents, one easing curve). Existing identity was preserved; these warnings do not indicate newly introduced layout defects. The detector output is retained in detector.json.

Browser automation intermittently timed out, including the final scrolled narrow-pane screenshot; narrow figure measurements succeeded. This is not exhaustive visual coverage of every view, pane combination, browser, or long value. The running Python server displayed an older-build banner and was not restarted; refreshed static assets/templates were used for this UI review.
