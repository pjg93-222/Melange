---
name: Mentat
description: A visual research workspace for comparing political giving and inspecting its evidence.
colors:
  plum: "#342649"
  purple: "#57447B"
  teal: "#327A7A"
  gold: "#ECA91C"
  ivory: "#f7ede4"
  paper: "#fcf7f4"
  workspace: "#FAF8F6"
  plot: "#ffffff"
  muted: "#62596e"
  line: "#d9d4de"
  panel-border: "#d9d4de"
  control-border: "#c8c0d1"
  secondary-border: "#b4a4bd"
  analysis-control-border: "#b7a9c5"
  chart-grid: "#e5e1e8"
  negative: "#bf3f36"
  insights-negative: "#ac7180"
  unknown: "#805c11"
  selected-wash: "#e8f3f1"
  hover-wash: "#f7f2fa"
  aqua: "#9ed4d5"
  mauve: "#8b6984"
  lilac: "#d6c8e2"
  taupe: "#bcaea1"
typography:
  display:
    fontFamily: '"Freight Text Pro", freight-text-pro, Georgia, serif'
    fontSize: "30px"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.5px"
  display-mobile:
    fontFamily: '"Freight Text Pro", freight-text-pro, Georgia, serif'
    fontSize: "27px"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.5px"
  headline:
    fontFamily: '"Freight Text Pro", freight-text-pro, Georgia, serif'
    fontSize: "22px"
    fontWeight: 700
    lineHeight: 1.2
  body:
    fontFamily: '"Articulat CF", articulat-cf, Arial, sans-serif'
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.5
  detail:
    fontFamily: '"Articulat CF", articulat-cf, Arial, sans-serif'
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: '"Articulat CF", articulat-cf, Arial, sans-serif'
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.6
  control:
    fontFamily: '"Articulat CF", articulat-cf, Arial, sans-serif'
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.3
  scope-label:
    fontFamily: '"Articulat CF", articulat-cf, Arial, sans-serif'
    fontSize: "13px"
    fontWeight: 600
    lineHeight: 1.5
  action:
    fontFamily: '"Articulat CF", articulat-cf, Arial, sans-serif'
    fontSize: "13px"
    fontWeight: 500
  analysis-tab:
    fontFamily: '"Articulat CF", articulat-cf, Arial, sans-serif'
    fontSize: "14px"
    fontWeight: 500
  workspace-tab:
    fontFamily: '"Articulat CF", articulat-cf, Arial, sans-serif'
    fontSize: "16px"
    fontWeight: 500
    lineHeight: 1.35
  selection-title:
    fontFamily: '"Freight Text Pro", freight-text-pro, Georgia, serif'
    fontSize: "20px"
    fontWeight: 700
    lineHeight: 1.25
  place-title:
    fontFamily: '"Freight Text Pro", freight-text-pro, Georgia, serif'
    fontSize: "24px"
    fontWeight: 700
    lineHeight: 1.2
  amount:
    fontFamily: '"Freight Text Pro", freight-text-pro, Georgia, serif'
    fontSize: "26px"
    fontWeight: 700
    lineHeight: 1.2
  place-amount:
    fontFamily: '"Freight Text Pro", freight-text-pro, Georgia, serif'
    fontSize: "28px"
    fontWeight: 700
rounded:
  control: "5px"
  panel: "7px"
  navigation: "6px"
  chip: "18px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
  xxl: "32px"
  workspace-gutter: "28px"
components:
  button-primary:
    backgroundColor: "{colors.plum}"
    textColor: "{colors.ivory}"
    rounded: "{rounded.control}"
    padding: "8px 12px"
    height: "40px"
  button-primary-hover:
    backgroundColor: "{colors.purple}"
  button-secondary:
    backgroundColor: "{colors.plot}"
    textColor: "{colors.plum}"
    rounded: "{rounded.control}"
    padding: "8px 12px"
    height: "40px"
  button-secondary-hover:
    backgroundColor: "{colors.hover-wash}"
  scope-field:
    backgroundColor: "{colors.plot}"
    textColor: "{colors.plum}"
    typography: "{typography.control}"
    rounded: "{rounded.control}"
    padding: "8px 10px"
    height: "40px"
  workspace-navigation:
    textColor: "{colors.plum}"
    typography: "{typography.workspace-tab}"
    rounded: "{rounded.navigation}"
    padding: "11px 12px"
  workspace-navigation-selected:
    backgroundColor: "{colors.plum}"
    textColor: "{colors.plot}"
  analysis-navigation:
    textColor: "{colors.plum}"
    typography: "{typography.analysis-tab}"
    padding: "12px"
    height: "40px"
  chart-controls:
    backgroundColor: "{colors.plot}"
    textColor: "{colors.plum}"
    typography: "{typography.action}"
    rounded: "{rounded.control}"
    padding: "8px 12px"
    height: "40px"
  chart-controls-selected:
    backgroundColor: "{colors.plum}"
    textColor: "{colors.plot}"
  analysis-card:
    backgroundColor: "{colors.plot}"
    textColor: "{colors.plum}"
    rounded: "{rounded.panel}"
    padding: "16px"
  evidence-detail:
    backgroundColor: "{colors.plot}"
    textColor: "{colors.plum}"
    rounded: "{rounded.panel}"
    padding: "16px"
  scope-chip:
    backgroundColor: "{colors.hover-wash}"
    textColor: "{colors.plum}"
    rounded: "{rounded.chip}"
    padding: "0 6px 0 12px"
    height: "36px"
---

# Design System: Mentat

**Current Graph and PAC exceptions — September 21, 2026:** The user explicitly reverted Graph and subsequently said the PAC tab “was better before.” Graph retains its saved summary-first, recipient-type/candidate overview and original controls; its company sparklines now use verified quarterly observations rather than election-cycle years. PAC evidence uses the saved pre-redesign runtime and template plus its original two-column geography and map-shell rules. Those restored compositions take precedence over the superseded Graph and PAC redesign guidance below. Insights retains the current visual direction. See the [rollback record](.impeccable/surfaces/visual-analysis.md). Do not reapply either rejected redesign.

## Overview

**Creative North Star: "Giving, in perspective."**

Mentat pairs warm paper, plum text, and editorial serif headings with direct sans-serif controls. Its recognizable identity frames a working research surface: generous plots hold attention, compact controls establish scope, and exact evidence stays close to the selected observation.

The approved Graph, PAC evidence, and Insights references establish one shared visual language. Fine borders, restrained corners, and flat white plotting surfaces make dense comparisons readable. The reference images guide composition; their illustrative figures, geography, and unsupported time series are not data specifications.

**Key Characteristics:**

- Large, readable data graphics with nearby evidence.
- One seven-workspace shell and consistent analysis controls.
- Plum hierarchy, teal observed series, purple comparisons, and sparing gold accents.
- Explicit scope, signs, unknown states, and accessible exact values.

This system record was refreshed from the corrected implementation on September 21, 2026. The user rejected the preceding release because it did not match the approved images; its earlier **ship** verdict and `reviewfix2` captures are superseded. The corrected release's final independent review returned **ship**: all six scored corrections were resolved, with no material regressions from this batch visible in the required viewport and full-page matrix. This verdict is limited to those fixes, not whole-surface perfection. The [surface brief](.impeccable/surfaces/visual-analysis.md) records the correction history, current release evidence, and bounded acceptance. Sources: [theme tokens](mentat/app/acu-theme.css), [shared presentation](mentat/app/workspace-polish.css), [shell and geography](mentat/app/workspace.css), [Graph](mentat/app/graph.css), [Insights](mentat/app/insights.css), [PAC evidence renderer](mentat/app/evidence.js), [text measurement](mentat/app/theme.js), and the [approved direction brief](outputs/visual-analysis-direction-20260921/implementation-prompt.md). The brief's original proposal status predates the user's subsequent approval of all three references.

## Colors

The palette uses plum and warm neutrals for structure, with teal and purple carrying explicit analytical roles. Frontmatter values are normative; names below describe their use. The sidecar's synthesized tonal ramps are preview metadata, not additional live palette tokens.

### Primary

- **Plum ink:** primary text, primary actions, solid selected workspace navigation, and selected Chart/Table segments.
- **Comparison purple:** baseline or comparison series, secondary links, active analysis underlines, and visible keyboard focus.

### Secondary

- **Observed teal:** selected or observed series and positive observed marks. Its meaning remains attached to the chart legend and funding basis.
- **Gold accent:** limited attention and focus accents inherited from the theme, rather than a second default action color.
- **Aqua, mauve, lilac, and taupe:** the existing supplementary chart palette, available when several categorical series need distinct encodings.

### Neutral

- **Workspace paper:** the warm shared workspace ground; **plot white** is the main chart and panel surface.
- **Ivory and paper:** inherited theme surfaces and primary-button text.
- **Muted ink:** scope summaries, descriptions, and secondary labels.
- **Line and panel border:** the shared light plum-neutral frame and separator. **Control border** frames scope fields; **analysis control border** frames page actions and Chart/Table switches. **Secondary border** remains the inherited generic secondary-button stroke. **Chart grid** provides a quieter plotting reference.
- **Selected wash and hover wash:** low-contrast context beneath an outlined or otherwise marked selection.

### Named Rules

**The Signed Evidence Rule.** Negative amounts keep their minus sign, a negative encoding, and a zero-based context; unknown, unavailable, and observed zero remain visibly different. The general chart negative and the incumbent Insights negative are separate scoped colors, not interchangeable positive series.

**The Scope Before Color Rule.** Shared colors never imply shared accounting. Industry-associated receipts, independent PAC downstream activity, and modeled attribution retain explicit, separate labels and denominators.

## Typography

**Display Font:** Freight Text Pro, then the local `freight-text-pro` family, with Georgia and serif fallbacks.

**Body Font:** Articulat CF, then the local `articulat-cf` family, with Arial and sans-serif fallbacks.

These are locally preferred font names. The stylesheet does not load an Adobe or other font CDN, and naming a family does not establish that it is installed. Georgia and Arial provide the offline fallback behavior.

The pairing gives titles an editorial character while controls, data labels, and source records remain familiar and compact. There is no separate monospaced identity; financial values use tabular numerals where supported.

### Hierarchy

- **Display:** the desktop page title; use the mobile display role when the mobile layout applies.
- **Headline:** chart and section headings, bold serif with a compact line height.
- **Body:** page introductions; ordinary prose stays in the established 14–15px range.
- **Detail:** evidence paragraphs, card descriptions, and contextual explanations.
- **Label:** scope, legends, chart axes, and supporting labels; chart/control text must render at least 12px.
- **Control and scope label:** field values use the regular control role; visible field captions use the stronger scope-label role.
- **Action and analysis tab:** shared page/chart actions use the action role; Graph chart-tool labels retain their 12px local variant. Flat analysis tabs use the analysis-tab role, with weight 600 when active.
- **Workspace tab:** the larger desktop navigation role, with weight 600 for the current workspace.
- **Selection title and place title:** the compact Graph selection header and the PAC selected-place header have distinct serif roles.
- **Amount and place amount:** bold selected-record and selected-place amounts retain exact values and signs in the evidence context.

**The Rendered Label Rule.** Resize and redraw the plotting surface to its container instead of shrinking a fixed SVG until its labels become unreadable. Graph uses measured pixel budgets and wrapping through the shared theme helper; Insights also wraps compact labels. Preserve full names in accessible text, source detail, or the exact table when a visible label is shortened.

## Layout

The desktop shell uses a shared 180px fixed sidebar at widths of 1100px and above. All seven destinations remain: Loading, Collection, Graph, Chart Studio, Insights, Cross-reference, and PAC evidence. At 1099px and below, the sidebar becomes a horizontal, scrollable navigation row; this is the actual current breakpoint, including the requested 900px composition.

Workspace padding is 24px at the top, the workspace-gutter token horizontally, and 40px at the bottom. At 760px and below it becomes 20px, 16px, and 32px. The workspace is left aligned, fills the available width, and has no maximum-width cap or auto-centering. Its desktop content starts at 208px from the viewport edge: the 180px sidebar plus the 28px gutter. This alignment continues on ultrawide screens. Use the frontmatter spacing rhythm for gaps; most analysis frames use 16px padding, reducing to 12px on mobile. Compact scope frames use 12px vertically and 16px horizontally.

Page chrome has a shared baseline: title and Export/Sources actions, a short description, compact scope controls, a scope line, and underline analysis navigation. Insights keeps its auto-width Refresh action alongside Export and Sources. A meaningful Graph scope trail follows the main scope line in normal flow; a one-part duplicate industry label stays hidden. Advanced controls stay available through disclosure. A collapsed PAC map scope retains its exact committee identity in the summary. At 760px and below, actions enter normal document flow and scope controls use a mobile disclosure. Controls are 40px on desktop and at least 44px in the mobile composition.

For the visual-analysis surfaces, the rollback exception above is authoritative for Graph and PAC evidence. PAC keeps its restored full map-and-ranking composition rather than the later compact selected-evidence rail. Insights places the cycle comparison across the full row, with supporting analyses in two columns; they stack at 1100px and below. These arrangements are surface choices, not a requirement to turn every workspace into the same chart layout. See the [visual-analysis surface brief](.impeccable/surfaces/visual-analysis.md).

Local scrolling is appropriate for an exact evidence table. Whole-page horizontal overflow, unreadable SVG scaling, and an empty reserved detail rail are not part of this system.

## Elevation & Depth

Panels are flat at rest. White plotting surfaces, the warm workspace ground, fine neutral borders, and selection outlines establish depth. Do not add ornamental shadows or decorative gradients to analysis frames. Existing floating menus and map tooltips use small functional shadows to separate temporary overlays; these are recorded in the sidecar, not promoted into a card style.

**The Flat Frame Rule.** Chart prominence comes from usable plotting area and hierarchy, not stacked ornament or heavier elevation.

Motion belongs to state and orientation. The existing graph entrance and map movement timings remain implementation details with reduced-motion support; opening Graph's evidence drawer currently has no entrance animation. Motion must not obscure a source change, delay exact values, or substitute for an explicit selected state.

## Shapes

Use the panel radius for analysis containers and evidence details, and the control radius for inputs, buttons, and segmented control shells. Their modest rounding supports a precise research interface. Desktop workspace navigation retains its existing navigation radius. Removable PAC scope chips retain the incumbent pill shape, a specialized selected-scope pattern rather than the default shape for actions.

Keep plot backgrounds rectangular and quiet. Use one-pixel neutral borders for structure, a three-pixel underline for active analysis navigation, and an explicit outline or stroke alongside color for a selected mark. A circular chart dot encodes data or a legend; it is not ornamental interface chrome.

## Components

### Buttons

Direct, compact actions with clearly different primary and secondary weight. Primary buttons use plum and ivory, moving to purple on hover; secondary actions use white, a fine border, plum text, and the hover wash. Shared action padding and desktop height live in frontmatter. Mobile actions reach at least 44px. Focus uses a visible two-pixel purple outline with a three-pixel offset in the workspace. Disabled states remain recognizable and do not look actionable.

### Chips

Removable scope chips use a light purple wash and a rounded outline, with a separate keyboard-accessible remove button. A clipped chip label must retain the full scope elsewhere. Chips represent actual selections; they do not replace the scope line or create a financial category.

### Cards / Containers

White, flat frames with panel corners and fine neutral borders. A title, contextual description when needed, actions, plot, and supporting source text form one coherent chart frame. Avoid subdividing one comparison into a grid of tiny repeated cards.

### Inputs / Fields

White fields with a warm neutral stroke, plum values, and muted labels. Use real labels, the control typography, and visible keyboard focus. Compact desktop scopes reflow into two columns on mobile without dropping fields; advanced choices stay inside accessible disclosures.

### Navigation

The selected workspace has a solid plum background. Analysis navigation uses a purple underline and a stronger label, retaining its flat background. Keep these two levels visually distinct. Preserve all seven destinations when the navigation reflows horizontally.

### Chart / Table / Export

Use one segmented Chart/Table switch and a nearby Export action in each supported chart heading. Selected segments use plum with white text. Switching views preserves the query and snapshot: tables and exports must describe the same observations as the chart. A record detail area does not gain a meaningless Chart switch.

### Evidence detail

The selected record or place uses the same quiet panel language, a readable serif heading, a prominent amount, explicit source/basis context, and exact available records. Pointer and keyboard activation expose the same evidence. Clearing a selection restores the compatible scope and returns focus logically. Source links and clearing actions use consistent labels and placement; an aggregate without records must not invent a filing link. In PAC geography, each recipient keeps its name and amount on the main line, its kind and place below, and a native disclosure when multiple real filing records are available. The record list scrolls locally; it does not turn every recipient into a separate decorative card.

Graph keeps the selected receipt amount, committee identity, source-record availability, independent-accounting distinction, Clear selection, and the full-width plum PAC evidence handoff visible above an initially closed native disclosure, **Explore downstream PAC activity**. The downstream chart and existing route explorer stay available inside that disclosure. On desktop at 1250px and above, an opened compact detail rail uses a 680px maximum height with local scrolling; the existing expanded explorer remains exempt. This preserves the main comparison's prominence without dropping downstream tools.

## Do's and Don'ts

### Do:

- **Do** let real charts, maps, and ranked comparisons dominate the analysis surface.
- **Do** keep scope, cycle, accounting basis, sources, and material coverage limits near the relevant visualization.
- **Do** retain exact signed values, readable labels, accessible tables, and keyboard-operable selections.
- **Do** preserve distinct receipt, independent PAC activity, and estimate meanings even when their visual styles match.
- **Do** use real cycle-level and same-stage observations, and reconcile a waterfall in signed cents within one funding channel.
- **Do** use the offline font fallbacks and support reduced motion.

### Don't:

- **Don't** treat unknown coverage, missing geography, or unavailable evidence as proven zero.
- **Don't** interpolate cycle totals into invented monthly trajectories or imply matching filing completeness from matching cutoffs.
- **Don't** convert negative values to positive bars or describe observation changes as proven changes in intent.
- **Don't** use generated mockup figures, map boundaries, or fictional records as application data.
- **Don't** shrink labels to preserve a desktop grid; stack the analyses and redraw their plotting surfaces.
- **Don't** replace the shared shell, add ornamental chart shadows or gradients, or reserve an empty evidence rail.
