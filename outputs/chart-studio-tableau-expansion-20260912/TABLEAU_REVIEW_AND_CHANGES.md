# Tableau concepts applied to Mentat Chart Studio

The original interface is preserved. Verified contributions now exposes **94 fields: 76 dimensions and 18 measures**, up from 18 dimensions and nine measures. Every one of the 24 Show Me choices has an implementation for this source mode; field requirements still determine which choices fit the current selection. The separate worksheet mode remains available for every sheet in the eight configured report workbooks.

Open [Chart Studio](http://127.0.0.1:8813/#chart-studio). Choose **Data Source** at the bottom for the complete field dictionary, report choices and relationship descriptions. The **Fields from** control filters the existing Data pane by logical table. These changes do not replace the original layout or styling.

## Review of the four supplied references

| Reference | Finding used in Mentat |
|---|---|
| [Tableau: Relate Your Data](https://help.tableau.com/current/pro/desktop/en-us/relate_tables.htm) | Keep the observation grain explicit, query only necessary tables, preserve unmatched observations, and establish cardinality from evidence. Mentat's reported metadata is related by source ID, industry and original source table; alternate report summaries are not appended to contribution facts. |
| [Deepak Holla: All about Data Types](https://medium.com/@deepak.holla/understanding-tableau-concepts-all-about-data-types-in-tableau-desktop-e8a1bc82aa0e) | The field dictionary should distinguish data type, analytical role and geographic role. ZIPs and identifiers stay text dimensions; monetary measures retain cent precision. Fields now have type/role/table descriptions and appropriate geographic, date and Boolean icons. |
| [Deepak Holla: How Tableau Detects Data Types](https://medium.com/@deepak.holla/how-tableau-desktop-detects-data-types-and-why-it-matters-more-than-you-think-31ae11323378) | Inferring a number from a numeric-looking identifier can corrupt analysis. Verified-source typing is now explicit. The article's generalized sampling/version history was not adopted as an implementation specification; see the official correction below. |
| [Rihab Feki: Tableau Features—The Complete Learning Guide](https://rihab-feki.medium.com/part-i-tableau-the-ultimate-guide-a8ff2cf97fea) | Source selection, field roles, relationship grain, date levels, filters and bins form one workflow. Mentat now exposes year → quarter → month → date, selectable typed fields, and histograms/box plots computed from individual receipt observations. |

All four were read. The two Holla articles initially returned an incomplete body or a fetch failure through web retrieval; their complete public article bodies were subsequently read in the browser. No sign-in or paywall bypass was used. Technical decisions were checked against Tableau's primary documentation rather than relying on the tutorial articles alone.

Two distinctions matter. A field's type, its dimension/measure role and its discrete/continuous presentation are separate concepts. A text ZIP can group data without becoming a summable number. Date fields can also define chronological axes. [Tableau's field roles](https://help.tableau.com/current/pro/desktop/en-us/datafields_typesandroles.htm).

Tableau's current documentation specifies sampling the first **10,000 Excel rows** and **1,024 CSV rows** when mapping mixed values. It also describes incompatible values becoming null and possible precision loss when changing types before extraction. Mentat's verified analytical source does not infer its monetary fields from a sample or silently coerce IDs into numbers. [Tableau's data types](https://help.tableau.com/current/pro/desktop/en-us/datafields_typesandroles_datatypes.htm).

## Field and source expansion

The 21 added analytical/audit fields include source observation ID, recorded postal code, original source table, source URL, complete accounting-reason/evidence-reference lists, month, quarter, weekday, review requirement, signed-amount direction and amount bins. Added measures cover first/third quartiles, population standard deviation, distinct committees and companies, active receipt days, first/last dates and observed date span. Existing field positions remain stable so saved sheets still refer to the same fields.

Another **46 reported metadata dimensions** expose previously hidden source columns: transaction/original IDs; donor name components; reported year-to-date aggregate; committee type/designation; entity and election types; receipt and filing forms; memo, back-reference and conduit details; amendment/report/file indicators; ingestion and matching metadata; and reported exclusion/refund/passthrough/duplicate flags. The `Reported` prefix distinguishes these raw fields from Mentat's accounting decisions. Their values can be grouped and filtered but do not replace the selected accounting basis.

Reported year-to-date totals are deliberately descriptive fields, not additive contribution measures: summing the same cumulative total across receipts would recreate the original overcounting problem. Raw metadata conflicts remain complete value lists in one related row. Neither lists nor multiple source representations are exploded into copies of money. Missing columns and unmatched metadata remain blank groups with their original contribution amounts intact.

The Data Source view describes seven logical groups: contribution observations, recipient attribution, contributor geography, source evidence, reported receipt metadata, Census geography, and report worksheets. The first four expose fields from the verified observation model; they are not new independent monetary ledgers. Reported metadata uses the pinned contributions/corporate-giving tables. Census geometry remains a lookup/overlay. Candidate funding, committee spending, coverage and other worksheet tables remain accessible at their own grain through **Explore every report worksheet**.

The relationship model is fixed and audited. It is not an arbitrary drag-to-join database editor, nor a claim that every worksheet measure is interchangeable with receipt dollars. Tableau's recommendations favor retaining tables' native grain and matching key types; its relationship performance settings require known cardinality. Mentat uses a declared unique source key where available and otherwise groups conflicting metadata variants before relating them. [Tableau relationships](https://help.tableau.com/current/pro/desktop/en-us/relate_tables.htm).

The complete machine-readable inventory is [field-catalog.json](field-catalog.json), with labels, types, units, roles and descriptions.

## Chart availability and meaning

| Family | Behavior in verified contributions |
|---|---|
| Text table | Displays queried dimensions and source-level measures, including date statistics. |
| Heat map / highlight table | Two-dimensional cells retain signed values; blank cells are not manufactured zeros. |
| Symbol / filled map | ZIP/state symbols or filled recorded-state totals, with independent state/congressional overlays. ZIP overlap never allocates dollars into districts. |
| Pie | Uses source aggregates; negative values require a suitable signed-value chart. |
| Horizontal / side-by-side bars | Displays the selected source groups and typed measures. |
| Stacked bars | Actually stacks positive and negative contributions separately from zero. |
| Treemap / packed bubbles | Area represents absolute magnitude; negative values are explicitly distinguished and retain signed tooltips. |
| Circle views / side-by-side circles | Categorical circles on a numeric axis, without joined lines. |
| Scatter | Two numeric measures with exact grouping dimensions; the existing Circle mark remains an XY option. |
| Continuous / discrete lines and areas | Date, quarter, month, year and cycle levels; missing periods remain gaps. |
| Dual lines / dual combination | Two explicitly labelled scales; line/line or bar/line combinations. |
| Histogram | Server bins individual selected amounts. Bin width is configurable in dollars; negative boundaries use mathematical floor. All occupied bins are requested. More than 10,000 bins requires a wider bin or narrower filters rather than silently cutting off the distribution. |
| Box-and-whisker | Source-level quartiles and median; whiskers explicitly show full minimum–maximum range, including outliers. |
| Gantt | Observed first-to-last receipt span, explicitly not continuous giving or a project duration. |
| Bullet | Two same-unit measures; the comparison measure is not an invented goal or target. |

The existing doughnut, waterfall, Pareto and radar options also remain. Chart suitability still matters; making a choice available does not make every combination of fields meaningful. Tableau similarly organizes charts by the analytical question: distribution, comparison, magnitude, time and other relationships. [Visual best practices](https://help.tableau.com/current/blueprint/en-us/bp_visual_best_practices.htm).

Histogram counts come from source observations rather than chart subtotals, matching the bin-and-count construction described in [Tableau's histogram guide](https://help.tableau.com/current/pro/desktop/en-us/buildexamples_histogram.htm). Box quartiles are also computed from the individual selected amounts. Full-range whiskers are labelled explicitly, one of Tableau's supported whisker interpretations. [Tableau's box plot guide](https://help.tableau.com/current/pro/desktop/en-us/buildexamples_boxplot.htm).

## Accounting, provenance and verification

The published included-receipt basis remains the default. Raw observations, provisional original giving, the supported gross subset and recipient-reported PAC activity remain distinct. The new fields do not certify unique economic gifts or change source amounts. Authoritative workbooks and accounting indexes were preserved.

New field definitions have their own code fingerprint. Caches include it, source identity and the query code. Reported-metadata queries additionally check the source database stamp and active WAL/journal state. Drill-through reuses the same derived-field and metadata relationship rules as the chart. CSV and the SVG/PNG source context carry the semantic fingerprint and histogram bin width alongside existing workbook/index/query provenance.

The guarded API validation compares all eight industry totals with the accepted published receipts and checks repeated-response equality. Banking checks cover month/party, full histogram, quartiles, observed date spans, filing metadata and source audit groupings. Their result rows and timings are recorded in [live-validation.json](live-validation.json). The histogram includes 154 occupied $100 bins; all selected observations remain accounted for.

Focused tests cover signed bin boundaries, quartiles, excluded zero-basis representations, distinct counts, date spans, every added analytical dimension, raw metadata conflicts and unmatched values, exact drill filters, source/WAL drift and byte-identical source indexes. The original numerical equivalence and query-cache suites remain in place; their comparisons ignore only the newly added descriptive metadata. Browser checks verify all 13 added renderer types, keyboard source inspection, finite coordinates, unchanged input records, all 24 Show Me choices, the original shell, map conservation, CSV and source-mode switching.

New raw-metadata and source-statistic configurations can take longer than cached company charts because they read related source detail or individual values. Ordinary chart queries keep using the compact verified projection, and complete results are cached. The performance receipts retain both cold/new-configuration and repeated timings rather than presenting every query as instantaneous.

The metadata SQL benchmark returned identical rows with disk-backed temporary storage (46.8 seconds) and memory temporary storage (8.3 seconds). A follow-up measured 58.1 seconds with larger source page caches alone and 13.1 seconds with memory temporary storage; a 128 MiB temporary page cache still took 52.2 seconds. These are component timings on this machine, not guaranteed end-to-end latency. See [initial profile](metadata-profile.json), [cache isolation profile](metadata-cache-profile.json), and [bounded temporary-cache profile](metadata-bounded-cache-profile.json). The implemented optimization uses memory temporary storage only when at most four reported fields are requested from a source no larger than 1 GiB, with one such workspace at a time. Wider/larger metadata views retain the existing temporary-storage behavior. Ordinary queries are unaffected. This is a workload eligibility limit, not a hard memory-allocation ceiling.

Final focused regression runs passed: 21 query/cache tests; 28 semantic-suite tests (including inherited source-accounting checks); and both browser suites covering the 13 new renderers, 24 Show Me choices and original UI workflow. Earlier HTTP/security and console-delivery checks also passed. Syntax and scoped whitespace checks passed. The final live API run was partly concurrent with regression tests, so its timings include local contention.

The final end-to-end Banking run measured 2.55 seconds for month/party, 2.84 for the full histogram, 10.93 for source quartiles, 3.05 for observed date spans, 55.37 for filing metadata and 11.98 for source-audit grouping. All eight industry totals and all six analytical configurations reconciled, and each repeated response was identical. The filing-metadata first query still has substantial latency; the faster isolated SQL benchmark must not be presented as the complete API time.

Live UI checks confirmed 94 dictionary rows, seven logical groups and all eight source selectors; a complete Banking histogram with 154 occupied bins; and a filled-state map with 53 inspectable state/territory shapes. Its selected total remained $54,762,844.05, with unmapped money retained. Pressing Enter on Alabama's $172,881.04 shape opened the 4,474 matching source observations. New chart marks support keyboard inspection; these tests do not constitute a complete accessibility audit of every application control.

This work is local and uncommitted. It does not restart active collections or publish data externally.
