# Mentat Chart Studio: accounting, Tableau behavior, and geographic analysis

Mentat can support contribution analysis by ZIP with optional congressional-district and state overlays. The immediate priority is the accounting model that feeds those views. Current charts can count overlapping worksheet summaries, repeat money when splitting multi-value fields, and aggregate raw amounts that the workbook excludes from its analysis. Separately, the upstream reporting basis retains some superseded and duplicate filing observations. Fixing the chart renderer alone will not make these totals represent unique giving.

The strongest Tableau pattern to adopt is an explicit data model: define what one record represents, define the meaning and valid aggregation of each measure, and query at the level of detail requested by the fields in the view. The familiar shelves should expose that model. Tableau's relationships preserve tables at their native detail and help avoid multiplication caused by physical joins; they do not repair incorrectly defined source facts. [Tableau data model](https://help.tableau.com/current/pro/desktop/en-us/datasource_datamodel.htm), [relationship analysis](https://help.tableau.com/current/pro/desktop/en-us/datasource_multitable_analysis_overview.htm).

## Scope and current state

This review covers the current Mentat working tree, the two supplied close-out reports, published workbook structure, targeted published dollar reconciliations, and official Tableau, Census, HUD, and FEC documentation accessed on September 12, 2026. The checked-out commit was `b44fcef7ad45887e15b2ebd9cb53e3d9d56dbe4d`; numerous upstream files also contained existing uncommitted changes. Working-tree findings must therefore be distinguished from deployed workbook behavior.

The attached fields-lane report described the detail-sheet work as uncommitted; the later close-out report said it was committed as `b44fcef7a`. Git confirms that commit. However, none of the eight workbooks in the configured publication directory contains **Recipient Detail** or **Contributor Detail**. The eight scopes are Banking, Community Banks, Credit Arms, Credit Union, Crypto, Fintech, Property & Casualty Insurance, and Telecom. Banking and Community Banks remain separate scopes.

The authoritative folder is [Mentat Complete Files](<C:/Users/pgoff/OneDrive/Desktop/Mentat Complete Files>), resolved through [report-directory.json](C:/Users/pgoff/Mentat/mentat/config/report-directory.json). The [published inventory](C:/Users/pgoff/Mentat/outputs/chart-studio-review-20260912/upstream/published_inventory.json) records all eight workbooks and sheet dimensions. The supplied reports are historical evidence; their rebuild, classification, commit, and cleanup instructions are not actions performed by this review.

## Confirmed accounting findings

### 1. A worksheet can contain the same dollars two or three times

**Priority: P1.** The chart reader accepts every nonempty row beneath its inferred header. It does not identify fact rows, subtotals, alternative breakdowns, or overlapping subject scopes. Its response includes a general warning about overlapping totals, but that warning appears only in the Data Source tab and is omitted from the normal chart notes and exported scope. It supplies no machine-readable rules for safe aggregation. See [report_insights.py:283](C:/Users/pgoff/Mentat/mentat/app/report_insights.py:283), [Data Source note](C:/Users/pgoff/Mentat/mentat/app/chart-studio.js:933), and [export scope](C:/Users/pgoff/Mentat/mentat/app/chart-studio.js:855).

Published Banking provides a concrete example. In **Spending Overview**, cycle **2023–2024**, the stated Total Giving in C21 is **$26,107,204.16**. The current engine, with Cycle and SUM(Total Giving), sums C21:C35 to **$78,321,612.48**, exactly **three times** the stated figure to the cent. Filtering Scope to Total Giving restores the $26,107,204.16 workbook-basis amount. The sheet presents the same money as the overall total, a role breakdown, and a recipient-category breakdown. Those are alternative views of the dollars, not additive components of one larger amount. [Executed published-data results](C:/Users/pgoff/Mentat/outputs/chart-studio-review-20260912/upstream/chart_math_reproduction.json).

The Banking **Recipient List** also demonstrates an exact double count across all three cycles. Its 3,342 Industry-view rows total **$54,762,844.05**, and its 6,651 Company-view rows independently total **$54,762,844.05**. The current engine sums both to **$109,525,688.10**. That exactly matches the “grand total unchanged” figure reported in the supplied fields-lane report. Preserving the incoming sum established that Other rollup did not lose money; it did not establish that the incoming rows represented exclusive amounts. [Banking recipient reconciliation](C:/Users/pgoff/Mentat/outputs/chart-studio-review-20260912/upstream/banking_recipient_reconciliation.json), [actual engine result](C:/Users/pgoff/Mentat/outputs/chart-studio-review-20260912/upstream/recipient_math_reproduction.json).

The published Crypto **Recipient List** similarly contains industry-level and company-level views, each totaling **$145,462,078.45** for 2023–2024. Combining them counts the included basis twice. This is different from legitimate grouping within one exclusive partition.

**Remedy:** publish chart datasets with an explicit grain and row role. A summary worksheet can remain a readable report, but its multiple tables should not become one unrestricted chart fact table. Select one scope and one breakdown, or query a single canonical fact dataset directly. Every view needs an explicit industry, companies, cycle window, accounting basis, and dataset version.

### 2. Splitting ZIP lists repeats the full amount, and two splits multiply each other

**Priority: P1.** [explodeRows](C:/Users/pgoff/Mentat/mentat/app/chart-math.js:90) copies the entire row for every semicolon-separated value. When both the X field and Colour field split, it creates every combination. No allocation or economic-transaction identity prevents the copied amounts from being summed.

| Reproduced input | Current result | Meaning |
|---|---:|---|
| One $100 row with three ZIPs, plus one $50 row | $350 in displayed money and grand total | Original rows contain $150 |
| One $100 row with three ZIPs and two district values | $600 across six marks | Three multiplied by two copies |
| One $100 row with the same ZIP token repeated twice | $200 in one mark | Even repeated identical tokens multiply money |

These are executed examples from the current chart engine, recorded in [chart reproduction results](C:/Users/pgoff/Mentat/outputs/chart-studio-review-20260912/chart-audit/reproduce-chart-accounting.jsonl). Hiding a combined total for grouped series does not correct the duplicated marks. Single-series split charts still receive an ordinary grand total from [grandTotal](C:/Users/pgoff/Mentat/mentat/app/chart-studio-core.js:517).

The published Banking **Employee List** contains 4,500 employee-summary rows, including 2,229 multi-ZIP rows. Their Total Giving values sum to **$36,925,530.61**. The current engine with ZIP splitting enabled produces **$89,135,413.84**, an additional **$52,209,883.23**, across 7,333 expanded rows. Both runs include the Other mark, so display truncation does not explain the difference. This is the published top-150-employees-per-company subset: 1,500 rows in each of 2021–2022, 2023–2024, and 2025–2026, not all Banking giving. A person's list of ZIPs does not reveal how much of their aggregate giving belongs to each ZIP. [Executed published-data results](C:/Users/pgoff/Mentat/outputs/chart-studio-review-20260912/upstream/chart_math_reproduction.json).

**Remedy:** ordinary money measures must not operate on exploded coverage lists. Build ZIP totals from each accepted contribution's recorded ZIP. If a separate coverage analysis remains useful, name it as coverage, define whether it counts unique entities or occurrences, and prevent its repeated values from being presented as giving. Dividing equally among ZIPs would be an estimate and cannot reconstruct the missing transaction allocation.

### 3. Raw Amount can resurrect money excluded from Analysis Amount

**Priority: P1.** Published Crypto supplies a particularly clear distinction. On **2023–2024**, rows **24–28**, five Coinbase/FAIRSHAKE observations each show **$23 million**. Their raw Amount totals **$115 million**. Their Analysis Amount totals **$23 million**, because four memo rows are already excluded from analysis.

Thus these five rows do **not** demonstrate that the published included total is currently five times too high. They demonstrate that charting raw **Amount** instead of **Analysis Amount** can add back **$92 million** that the workbook has already excluded. Both numeric fields can be exposed to a generic chart builder without a distinction in their permitted use.

**Remedy:** define separate named measures for raw reported amounts and accepted analytical amounts. Put the accepted basis first for ordinary giving analysis, retain raw observations in an evidence view, and make the current basis visible in titles, exports, and the source summary. A numeric type alone cannot establish that a column is safe to sum.

### 4. The source reporting basis includes some repeated filing observations

**Priority: P1 for unique-giving claims; a substantive accounting change is required.** The current [fec_receipt_countable predicate](C:/Users/pgoff/Mentat/mentat/R/collect.R:103) checks company acceptance, exclusion reasons, duplicate-memo status, and receipt role. It does not exclude `superseded_by_amendment` or `duplicate_filing_version` merely because those flags are set. The reporting code documents this preservation policy at [report.R:3117](C:/Users/pgoff/Mentat/mentat/R/report.R:3117).

This behavior is deliberate enough to be encoded in tests. A $100 original contribution amended to $125 must produce **two analytical rows totaling $225** in [test_report.R:273](C:/Users/pgoff/Mentat/mentat/tests/test_report.R:273). Another fixture retains five $23 million filing-version records. These are code-contract examples, not estimates of the overstatement in every published workbook.

The published Crypto 2023–2024 included total is **$145,462,078.45**. Within that included scope, 169 rows marked **Duplicate Filing Version** carry **$65,140,793.73**, and one superseded-amendment row carries **$1,000**. These flags identify a high-value reconciliation population; subtracting their full amounts is **not yet a validated corrected total**. Version identity, legitimate repeated gifts, memorandum relationships, refunds, and retained representatives still require evidence.

FEC documentation explains why raw disclosure records and economic giving must be distinguished: amendments can add, edit, or delete information; memo entries provide supplemental information whose amounts are not included in schedule line totals; and contributions through conduits generate associated disclosures. An arbitrary sum across these records does not necessarily equal new money contributed. [FEC amendments](https://www.fec.gov/help-candidates-and-committees/filing-amendments/), [FEC memo entries](https://www.fec.gov/updates/check-the-box-to-report-memo-entries/), [FEC conduit reporting](https://www.fec.gov/help-candidates-and-committees/filing-reports/contributions-received-through-conduits/).

The FEC's bulk-data description adds two essential qualifications. A transaction ID can persist through the original filing and amendments, while SUB_ID is only a unique row identifier. Memo-code X records can contain earmarking or partnership information needed for analysis, and the FEC explicitly advises including them when analyzing the bulk file. Therefore neither distinct source-row IDs nor blanket removal of all memo records establishes correct economic giving. The analytical measure must interpret their relationships and purpose. [FEC individual-contribution file description](https://www.fec.gov/campaign-finance-data/contributions-individuals-file-description/).

**Remedy:** preserve the raw evidence and derive a separate, versioned analytical ledger. Represent filing versions, economic contributions, and later transfers as distinct objects. Determine canonical contributions from supported transaction and amendment relationships, not from matching names and dollar amounts. A contribution to a PAC and a later PAC expenditure can both be valid activities while still being inappropriate to add as unique donor-origin giving.

### 5. Temporal views can report totals with the wrong meaning

**Priority: P1.** Grand-total eligibility checks the chart type and aggregation but not the transform's resulting unit or whether a point is forecast. Current reproductions show two 100% year-over-year observations yielding a status total of **200** under `SUM(Amount)`. A forecast example adds **$1,100** in future estimates to **$3,600** in observed amounts, presenting **$4,700** as the combined total. See [temporal transforms](C:/Users/pgoff/Mentat/mentat/app/chart-math.js:346) and [total eligibility](C:/Users/pgoff/Mentat/mentat/app/chart-studio-core.js:508).

**Remedy:** measures need units and result semantics. YoY is a percentage change, period change is a difference, and forecast is estimated rather than observed. Give each its own label and summary rule. Keep observed and forecast totals separate. An annual sum over exclusive observed periods remains a valid amount total.

### 6. Counts and averages need their own accounting rules

**Priority: P2.** Current `COUNT(Amount)` counts rows even when Amount is missing. On preaggregated detail sheets, `COUNT(Gift Count)` counts detail rows, whereas `SUM(Gift Count)` adds the supplied gift counts. Likewise, the Contributor Detail writer computes distinct contributors within each fine-grained group; adding those group counts can count the same contributor under multiple ZIPs, employers, or occupations. See [detail aggregation](C:/Users/pgoff/Mentat/mentat/R/report.R:1973).

Define **row count**, **accepted contribution count**, and **distinct contributor count** separately. An average contribution should be a ratio of accepted amounts to accepted gift counts at the requested scope. Averaging employee totals answers a different question. A mean of detail-group means is generally not the mean of the underlying gifts.

## How Tableau works, and what Mentat currently implements

Tableau authoring has several connected stages. The analyst connects data, defines relationships and field properties, places fields on shelves, chooses mark encodings, filters the analytical population, and then inspects or exports the result. Each stage can affect the query or the view's level of detail. A chart type picker is only one part of that process.

| Capability | Tableau behavior | Current Mentat finding | Required direction |
|---|---|---|---|
| Source preparation | Tables and relationships have defined detail; Excel Data Interpreter can identify titles, notes, and separate tables | Whole worksheet imported after one header | Use analytical tables and explicit row roles |
| Field semantics | Dimension/measure and discrete/continuous are distinct properties | Mainly inferred number/category, time and identifier flags | Add field schema, unit, aggregation policy, geographic role |
| Rows and Columns | Additional fields create further headers, axes, and detail | Main compiler consumes one X and one Y, with a limited Colour split | Support composite grouping/facets or reject unsupported shelves visibly |
| Marks | Color, Size, Label, Detail, Tooltip encode information with defined behavior | Several accepted pills never affect the compiled query | Implement each encoding or disable it |
| Aggregation | Measures aggregate at the view's level; COUNT and COUNTD differ | Generic sum/mean/count/median/min/max over selected worksheet values | Use measure-specific calculations and distinct keys |
| Filters | Row, aggregate, context, and table-calculation stages differ | Numeric filters act on source rows before grouping | Distinguish row filters from aggregate filters |
| Totals | Totals can be recomputed over underlying records using their own aggregation context | Sum of visible additive mark values with limited guards | Query totals at the intended scope and result unit |
| Geographic analysis | Geographic roles, generated coordinates, spatial data, and separate map layers | Symbol and filled map tiles disabled | Add explicit geography plus independent boundaries |
| Inspection | A mark can expose its underlying records | Chart exports expose calculated values; no canonical contribution lineage in this path | Add an inspect-records route and reconciliation receipt |

Sources: [Tableau Data Interpreter](https://help.tableau.com/current/pro/desktop/en-us/data_interpreter.htm), [field roles](https://help.tableau.com/current/pro/desktop/en-us/datafields_typesandroles.htm), [shelves and cards](https://help.tableau.com/current/pro/desktop/en-us/buildmanual_shelves.htm), [aggregations](https://help.tableau.com/current/pro/desktop/en-us/calculations_aggregation.htm), [totals](https://help.tableau.com/current/pro/desktop/en-us/calculations_totals_grandtotal_turnon.htm), [underlying data](https://help.tableau.com/current/pro/desktop/en-us/inspectdata_viewdata.htm).

### Field placement must change the calculation predictably

Tableau dimensions partition data and establish the view's detail. Discrete fields create headers; continuous fields create axes. A numeric identifier remains an identifier even though its values contain digits. Postal codes therefore belong in categorical/geographic fields, with leading zeros preserved. [Tableau field roles](https://help.tableau.com/current/pro/desktop/en-us/datafields_typesandroles.htm).

Mentat's [compileReport](C:/Users/pgoff/Mentat/mentat/app/chart-studio-core.js:125) currently accepts more state than it implements. Executed probes start with State and Total Giving, then separately add another dimension, another measure, Detail, Size, Label, or Tooltip. Each produces the same configuration and no issue or note. Two Massachusetts ZIPs remain one $300 state mark after ZIP is added as a second dimension or Detail. The UI can hold these pills at [chart-studio.js:356](C:/Users/pgoff/Mentat/mentat/app/chart-studio.js:356), giving an impression of detail the engine has not applied. The Label drop also toggles generic numeric labels; it does not make the selected label field part of the query.

The [shelf probe](C:/Users/pgoff/Mentat/outputs/chart-studio-review-20260912/shelf-semantics.cjs) reproduces these results. This is not evidence that the compiler automatically sums multiple selected measures; it often ignores the additional measure. The problem is a mismatch between visible field placement and the answer calculated.

### Filter stages and calculated totals must be explicit

Suppose a ZIP has two $60 contributions. A **raw Amount >= $100** filter removes both; a **SUM(Giving) >= $100 by ZIP** filter retains their $120 group. Mentat currently performs the former. Tableau has a defined order of operations, and FIXED level-of-detail calculations can intentionally use a different scope from ordinary dimension filters. This also affects whether a percent-of-total denominator is the selected population or a broader baseline. [Tableau order of operations](https://help.tableau.com/current/pro/desktop/en-us/order_of_operations.htm), [level-of-detail expressions](https://help.tableau.com/current/pro/desktop/en-us/calculations_calculatedfields_lod.htm).

Mentat does not need to copy Tableau's complete calculation language to handle this safely. It needs a small explicit sequence: select accepted facts and scope, apply row filters, group, calculate measures, apply group filters, calculate totals/transforms, then render. Display limits should not become unannounced changes to accounting scope.

### Show Me should describe the view it actually builds

Tableau's Show Me evaluates selected fields and offers suitable view types. Mentat already has eligibility rules, but some tile names promise a different visual: Stacked Bars produces side-by-side bars, Dual Lines uses one measure split by Colour rather than two measures, and several other tiles are disabled. These limitations are partly described in tile notes at [chart-studio-core.js:307](C:/Users/pgoff/Mentat/mentat/app/chart-studio-core.js:307). Name implemented views directly, and enable fuller Tableau behavior as it is delivered. [Tableau Show Me](https://help.tableau.com/current/pro/desktop/en-us/buildauto_showme.htm).

## ZIP tracking and optional district/state overlays

### The data exists, but the published chart source is incomplete

The contribution schema retains city, state, and ZIP. The new Contributor Detail code groups by cycle, company, state, city, ZIP5, employer, and occupation, and preserves missing geography rather than discarding its dollars. ZIP+4 values are normalized to ZIP5. See [schema.R:12](C:/Users/pgoff/Mentat/mentat/R/schema.R:12) and [report.R:1857](C:/Users/pgoff/Mentat/mentat/R/report.R:1857).

However, current published workbooks lack that new sheet. When detail exceeds the writer's 45,000-row cap, it folds excess groups into company/cycle Other rows with blank geographic attributes. A grand-total reconciliation can then pass while geographic detail is lost. Map queries should therefore aggregate by geography from accepted facts before transport/display limits, rather than treating a folded worksheet as a complete geographic source. [Detail folding](C:/Users/pgoff/Mentat/mentat/R/report.R:1914).

### Keep three geographic questions separate

| Question | Correct geographic meaning | Evidence required |
|---|---|---|
| Where did contributions originate? | Recorded donor ZIP/state at contribution time | Contribution-level recorded geography |
| What districts overlap those ZIP areas? | Contextual district boundaries | Versioned ZIP-area and district geometry |
| Which district received political support? | Recipient candidate's district for the applicable election/Congress | Recipient/candidate relationship and time-specific district |

A district outline over a ZIP map does not prove that every donor in that ZIP lives in the district. It also does not change the recipient's district. Donor origin, recipient destination, and geographic overlap should be separately named fields and views.

### ZIP polygons are an approximation

Postal ZIP codes describe mail-delivery geography. Census ZCTAs are generalized areas that approximate the distribution of ZIP codes, and not every valid postal ZIP has a corresponding ZCTA. Label filled maps **ZIP areas (Census ZCTAs)**. Keep invalid, missing, and unmatched ZIP amounts visible in coverage figures and the downloadable table. [Census ZCTA definitions](https://www.census.gov/programs-surveys/geography/guidance/geo-areas/zctas.html).

The present contribution schema has no street-address or point-coordinate fields. The Census Geocoder requires a structure number and street name for address geocoding and provides benchmark/vintage controls. Consequently, the stored ZIP by itself cannot support precise address-based donor-district assignment. A representative ZIP point can be used as a labeled display location, not as evidence of each donor's address. [Census Geocoder API](https://geocoding.geo.census.gov/geocoder/Geocoding_Services_API.html).

### Build layers that do not multiply money

The first map should have a ZIP-area fill or proportional-symbol layer, an optional congressional-district outline layer, and an optional state-outline layer. Each boundary layer needs visibility, ordering, and selection controls. All should carry the same selected accounting/cycle context while retaining separate geometry data. Tableau's geographic roles and independent marks layers provide the relevant interaction model. [Geographic roles](https://help.tableau.com/current/pro/desktop/en-us/maps_geographicroles.htm), [geographic layers](https://help.tableau.com/current/pro/desktop/en-us/maps_marks_layers.htm).

The essential invariant is simple: **turning a boundary overlay on or off changes the picture, not the total money**. Join the aggregate to its own geometry key without duplicating the aggregate. Load contextual district and state outlines independently. A spatial intersection join is useful for discovering overlaps, but a ZIP touching two districts does not justify placing its full amount into both district totals. Tableau supports such spatial joins; the nonduplication requirement is an accounting design inference, not a property automatically supplied by the map renderer. [Tableau spatial joins](https://help.tableau.com/current/pro/desktop/en-us/maps_spatial_join.htm).

### Offer estimated district allocation separately

HUD publishes ZIP-to-congressional-district crosswalks with address ratios. A ZIP can have several district matches, crosswalks are quarterly, some ZIP types are absent, and ratio sums may vary slightly through rounding. These are **address shares**, not observed shares of political giving. An allocation such as 60%/40% of a ZIP's $100 can yield estimated $60/$40, provided the chosen weight, vintage, coverage, and rounding policy are disclosed. [HUD crosswalk documentation](https://www.huduser.gov/portal/datasets/usps_crosswalk.html).

ZIPs can also cross state boundaries. Neither ZIP-to-state nor ZIP-to-district should be implemented as a universally exclusive hierarchy. Retain the donor's recorded state separately from polygon overlap and crosswalk-based allocation. [HUD geographic crosswalk guidance](https://www.huduser.gov/portal/datasets/usps_crosswalk.html).

Do not silently normalize away missing matches. Track unallocated amounts, and distinguish residential, business, or total-address weighting. ZIP-to-CD and CD-to-ZIP tables have different denominators; the HUD API exposes them as different types. Census district/ZCTA relationship files can describe geometric intersections but do not establish donation weights. [HUD API](https://www.huduser.gov/portal/dataset/uspszip-api.html), [Census geographic relationships](https://www.census.gov/geographies/reference-files/time-series/geo/relationship-files.2020.html).

### Pin the congressional boundary version

The live Census TIGERweb legislative service inspected for this review already labels its Current congressional layer **120th Congressional Districts**, and separately exposes **119th Congressional Districts**. A generic latest-boundaries request is therefore unsafe for a view intended to show a specific Congress. Save the Congress, geometry vintage, source URL, and checksum; distinguish boundaries for an election from the districts of sitting officeholders. [TIGERweb legislative service](https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer).

## Recommended implementation order

### First: contain misleading dollar views

Use an explicit analytical measure for giving. Prevent dollar aggregation over split multi-value fields. Partition report tables so totals and alternative breakdowns cannot be added together. Distinguish raw Amount from Analysis Amount, and prevent temporal percentages and forecasts from becoming ordinary giving grand totals. Reject unsupported field combinations visibly instead of silently ignoring pills.

This work can make the existing interface less misleading, but it cannot certify unique giving while the upstream basis retains repeated observations. The initial UI should clearly name the basis that actually exists.

### Second: create a canonical contribution layer and reconcile it

Preserve the raw evidence. Derive accepted economic events and their amendment/memo/transfer relationships using traceable rules. Keep separate measures for contribution value, refunds or reversals, and later downstream activity. Record whether values are observed, allocated, or forecast.

At minimum, the analytical schema needs:

| Object | Key responsibility |
|---|---|
| Raw observation | Original source record, filing, transaction identifier, memo and version metadata |
| Economic contribution | Canonical event identity, accepted amount, date/cycle, donor and recipient, accounting status |
| Company attribution | Supported company membership/relationship; detect multi-company overlap |
| Money-flow record | Transfer or downstream activity linked to supporting evidence |
| Geography | Raw ZIP, normalized ZIP5, recorded state, match status, geometry version |
| Measure definition | Unit, aggregation rule, additive dimensions, basis, and allowed transforms |

The same fact seen through Contributor Detail and Recipient Detail remains one fact. These are alternative aggregations, not two datasets to append. Distinct people require identity-aware queries; duplicate dollars require event-aware reconciliation. `SUM(DISTINCT amount)` is never a substitute, since two legitimate $100 gifts must total $200.

For a supported amendment from $100 to $125, the evidence ledger retains both observations while the current-giving measure counts the accepted $125 version once. For a $100 donor-to-PAC event followed by a $100 PAC-to-candidate transfer, origin giving and downstream activity remain separately inspectable rather than becoming an unexplained $200 giving total.

### Third: make field placement drive a real query

Compile the complete supported dimension set, measure set, filters, and mark encodings into a query plan. Attach the grain and accounting basis to the response. Produce totals from the selected fact scope, not merely by summing whatever marks remain visible. Add per-mark inspection with canonical IDs and source evidence.

An endpoint returning aggregated results is a better long-term fit than shipping arbitrary complete worksheets to the browser. It can preserve geography at scale and retain useful detail even when a source sheet exceeds the current 50,000-row reader ceiling. The published Banking and Telecom Downstream Activity sheets already exceed that ceiling.

### Fourth: deliver ZIP maps and boundary overlays

Expose donor ZIP as a visible geographic dimension. Provide ZIP totals and a coverage table from accepted facts. Add independent state and congressional outlines with a Congress selector. Display selected, mapped, unmapped, and excluded/unresolved amounts without conflating them. Add optional district estimates only after the observed ZIP view reconciles.

## Acceptance evidence required before trusted publication

| Test | Required outcome |
|---|---|
| Published Banking Spending Overview, 2023–2024 | The ordinary giving query selects one basis and returns $26,107,204.16 under the present workbook basis, not $78,321,612.48 |
| Published Banking Recipient List, all three cycles | Select Industry or Company view; each sums to $54,762,844.05 under the present basis, rather than combining to $109,525,688.10 |
| Employee ZIP list | Dollar analysis uses contribution-level ZIP; list expansion cannot inflate money |
| Raw versus analytical amount | The five Crypto observations remain inspectable; accepted analysis preserves the recorded $23m treatment, raw $115m is explicitly separate |
| Supported amended event | Raw evidence retains $100 and $125; current-giving measure uses one accepted $125 event |
| Identical legitimate gifts | Two independent $100 events total $200 |
| Multiple company attributions | Global unique total uses event union; attribution views explain any overlapping coverage |
| Origin and downstream activity | One $100 origin event is not enlarged by its later $100 transfer |
| Contributor counts | One person appearing in two detail groups counts once in the appropriate distinct-person scope |
| Totals and limits | Sorting and top-N presentation preserve the selected additive total; omitted groups remain accounted for |
| Additional shelf dimension | Adding ZIP to State changes detail or produces an explicit unsupported-operation message |
| Filters | Raw >=$100 and grouped SUM >=$100 remain distinct operations |
| Forecast/YoY | Estimates and percentage changes do not appear as observed giving totals |
| Geographic overlays | One $100 fact remains $100 with ZIP, district, and state layers visible |
| Split district estimate | $60 + $40 reconciles to $100, with explicit weights and retained unallocated remainder |
| Missing ZIP or geometry | Missing/unmapped amounts remain visible in reconciliation |
| Boundary version | 119th and 120th geometries are distinguishable and saved with the view |

These tests establish both arithmetic and meaning. A total that reconciles to an already duplicated reporting basis proves internal consistency, not unique economic giving.

## Verification record and limitations

The current Chart Studio core suite passed **54 of 54** tests. The separate chart-math suite passed **14 tests and failed 1**: its older test still expects more than 60 groups to throw, whereas the committed implementation now folds them into Other. That failure is a stale contract assertion rather than evidence that the new accounting findings have been fixed. New read-only reproduction scripts demonstrate the problems described above without changing product code.

Published workbook figures are taken from saved values. Formula caches can be missing or stale, so the reported numbers are scoped to the saved artifacts, not a fresh rebuild. Hashes identifying the two quantified workbooks are:

- Banking: `842ba7a2312ffb03d969e8452c970b32f227fd09befcbf80f935a63c94e97bd3`.
- Crypto: `88ea228457b8499d1ec27eeaba967f61505bde842ae0ecfe35c30791c23d66f6`.

The evidence supports specific counting defects and a mismatch between the reporting basis and unique-giving interpretation. It does not establish one corrected total for the whole Mentat system. The dollar effects above overlap and must not be added together. Upstream flags are a review population, not permission to delete records or subtract an unverified amount.

The supplied fields-lane report records a failed Banking rebuild on 2,070 unresolved receipts worth $20.68m. That is historical evidence of a publication blocker; the rebuild and classification gate were not rerun here. Solving those receipt classifications alone would not fix worksheet overlaps, ZIP multiplication, or filing-version accounting.

No production source files, databases, or published workbooks were changed by this review. Deliverables are the report and its reproduction/evidence files.

## Evidence and source register

### Local evidence

- [Published workbook inventory](C:/Users/pgoff/Mentat/outputs/chart-studio-review-20260912/upstream/published_inventory.json).
- [Published dollar quantification](C:/Users/pgoff/Mentat/outputs/chart-studio-review-20260912/upstream/published_quantification.json).
- [Actual engine results on published Banking values](C:/Users/pgoff/Mentat/outputs/chart-studio-review-20260912/upstream/chart_math_reproduction.json) and [runnable reproduction](C:/Users/pgoff/Mentat/outputs/chart-studio-review-20260912/upstream/reproduce_chart_math.cjs).
- [Detailed upstream evidence](C:/Users/pgoff/Mentat/outputs/chart-studio-review-20260912/upstream/UPSTREAM_EVIDENCE.md) and [chart findings](C:/Users/pgoff/Mentat/outputs/chart-studio-review-20260912/chart-audit/FINDINGS.md).
- [Chart reproduction script](C:/Users/pgoff/Mentat/outputs/chart-studio-review-20260912/chart-audit/reproduce-chart-accounting.cjs) and [results](C:/Users/pgoff/Mentat/outputs/chart-studio-review-20260912/chart-audit/reproduce-chart-accounting.jsonl).
- [Shelf semantics probe](C:/Users/pgoff/Mentat/outputs/chart-studio-review-20260912/shelf-semantics.cjs).
- [Fields-lane report](C:/Users/pgoff/Downloads/MENTAT_CHART_STUDIO_FIELDS_LANE_REPORT_2026-09-12.md), especially sections 2–5.
- [Session close-out report](C:/Users/pgoff/Downloads/CHART_STUDIO_SESSION_CLOSEOUT_2026-09-12.md), committed scope and outstanding publication work.

### Primary online sources

All sources were accessed September 12, 2026. Tableau links use its rolling current documentation; feature behavior and live geography endpoints should be rechecked when implementation starts.

1. Tableau. [The Tableau Data Model](https://help.tableau.com/current/pro/desktop/en-us/datasource_datamodel.htm). Logical relationships, physical joins, and native table detail.
2. Tableau. [How Analysis Works for Data Sources that Use Relationships](https://help.tableau.com/current/pro/desktop/en-us/datasource_multitable_analysis_overview.htm). Aggregation and relationship behavior.
3. Tableau. [Clean Data with Data Interpreter](https://help.tableau.com/current/pro/desktop/en-us/data_interpreter.htm). Worksheet cleanup and separate-table identification.
4. Tableau. [Dimensions and Measures, Blue and Green](https://help.tableau.com/current/pro/desktop/en-us/datafields_typesandroles.htm). Field roles, discrete/continuous, and detail.
5. Tableau. [Shelves and Cards Reference](https://help.tableau.com/current/pro/desktop/en-us/buildmanual_shelves.htm). Rows, Columns, Marks, Filters, and Pages.
6. Tableau. [Data Aggregation](https://help.tableau.com/current/pro/desktop/en-us/calculations_aggregation.htm). Measure aggregation, COUNT, COUNTD, and attributes.
7. Tableau. [Show Totals in a Visualization](https://help.tableau.com/current/pro/desktop/en-us/calculations_totals_grandtotal_turnon.htm). Total aggregation context.
8. Tableau. [Order of Operations](https://help.tableau.com/current/pro/desktop/en-us/order_of_operations.htm). Filter and calculation sequencing.
9. Tableau. [Level of Detail Expressions](https://help.tableau.com/current/pro/desktop/en-us/calculations_calculatedfields_lod.htm). Calculations at specified detail.
10. Tableau. [Use Show Me](https://help.tableau.com/current/pro/desktop/en-us/buildauto_showme.htm). Field-driven chart suggestions.
11. Tableau. [View Underlying Data](https://help.tableau.com/current/pro/desktop/en-us/inspectdata_viewdata.htm). Mark-level inspection and downloads.
12. Tableau. [Assign Geographic Roles](https://help.tableau.com/current/pro/desktop/en-us/maps_geographicroles.htm). ZIP, state, and congressional geography.
13. Tableau. [Create Geographic Layers for Maps](https://help.tableau.com/current/pro/desktop/en-us/maps_marks_layers.htm). Independent layer formatting, visibility, and selection.
14. Tableau. [Join Spatial Files](https://help.tableau.com/current/pro/desktop/en-us/maps_spatial_join.htm). Supported geometry and intersection joins.
15. U.S. Census Bureau. [ZIP Code Tabulation Areas](https://www.census.gov/programs-surveys/geography/guidance/geo-areas/zctas.html). ZIP/ZCTA distinction and coverage.
16. U.S. Census Bureau. [Geocoding Services API](https://geocoding.geo.census.gov/geocoder/Geocoding_Services_API.html), updated February 2026. Address requirements and vintage parameters.
17. HUD. [USPS ZIP Code Crosswalk Files](https://www.huduser.gov/portal/datasets/usps_crosswalk.html). Address ratios, coverage, and geographic splits.
18. HUD. [ZIP Code Crosswalk API](https://www.huduser.gov/portal/dataset/uspszip-api.html). Directional ZIP/district crosswalk types.
19. U.S. Census Bureau. [2020 Geographic Relationship Files](https://www.census.gov/geographies/reference-files/time-series/geo/relationship-files.2020.html). District/ZCTA relationships and measurement limits.
20. U.S. Census Bureau. [TIGERweb Legislative Service](https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer). Available congressional-boundary versions.
21. FEC. [Filing Amendments](https://www.fec.gov/help-candidates-and-committees/filing-amendments/). Changes to previously reported information.
22. FEC. [Check the Box to Report Memo Entries](https://www.fec.gov/updates/check-the-box-to-report-memo-entries/), February 9, 2016. Memo-entry amounts and line totals.
23. FEC. [Contributions Received through Conduits](https://www.fec.gov/help-candidates-and-committees/filing-reports/contributions-received-through-conduits/). Contribution and associated conduit reporting.
24. FEC. [Contributions by Individuals File Description](https://www.fec.gov/campaign-finance-data/contributions-individuals-file-description/). Transaction versus row identity and memo-record interpretation.
