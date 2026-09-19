# Chart accounting audit — 2026-09-12

Read-only review of the current files under `C:/Users/pgoff/Mentat/mentat/app`. No product files, source data, workbooks, or tests were changed. Reproductions use synthetic rows and invoke the shipped pure JavaScript modules. Findings distinguish documented implementation behavior from financial correctness.

Run all seven reproductions:

```powershell
node 'C:\Users\pgoff\Mentat\outputs\chart-studio-review-20260912\chart-audit\reproduce-chart-accounting.cjs'
```

Captured output: `reproduce-chart-accounting.jsonl` beside this file.

## P1 — ZIP splitting duplicates money, and the status/grand-total path treats it as additive

`mentat/app/chart-math.js:84-90` explicitly documents that splitting repeats the measure and overstates money. The implementation at `:94-110` selects X and series dimensions, splits each semicolon-separated cell, and copies the full row per token. `:106` uses `batch.flatMap`, which creates a Cartesian product when both dimensions contain multiple values. No allocation weight, receipt identity, or duplicate-token normalization is present.

Synthetic evidence:

- One $100 row naming three ZIPs plus one $50 row naming one ZIP: unsplit source total $150, split marks $150/$100/$100, `grandTotal` and status `SUM(Amount)` $350.
- One $100 row naming three ZIPs and two congressional districts: six $100 marks, or $600 across marks. Grouped grand total is correctly withheld, but every money mark still repeats the same underlying money. The relationship between ZIPs and districts is also fabricated as all possible pairs.
- One $100 row with `10001; 10001`: one $200 mark for ZIP 10001. Even a coverage interpretation should deduplicate the repeated token.

`mentat/app/chart-studio-core.js:508-521` blocks grand totals for grouped/non-sum/distribution views, but never checks `result.split` or a fact-grain contract. `:534-543` labels the returned sum `SUM(Amount)`. `mentat/app/chart-studio.js:885-889` renders that grand total on request, and `:900-906` always includes that sum in the status bar even when the Totals overlay is off.

The repetition is acknowledged in an explanatory note and split mode defaults off; it is not an arithmetic implementation surprise. It remains unsuitable as an option for reporting actual ZIP-level giving. A warning does not make overlapping dollars additive.

Recommended boundary: support exploded membership/coverage views separately from money views; monetary ZIP maps must group deduplicated transaction facts by the ZIP attached to each transaction, with explicit unknown/unmatched buckets. A donor summary's unordered list of several ZIPs cannot allocate its entire lifetime amount among those ZIPs. Do not repair this with SUM(DISTINCT amount), and do not assume equal allocation is factual. Any modeled allocation must be separately labeled and reconciled.

## P1 — transformed time marks are summed and labeled as actual monetary totals

`mentat/app/chart-math.js:346-350` replaces period amounts with percentages for YoY or period differences. `:379-383` appends forecast marks by copying historical amounts. `:388` returns a generic temporal result. `mentat/app/chart-studio-core.js:508-521` ignores both the transform and each mark's `forecast` flag; `:542` labels the result using the original measure aggregation.

Synthetic evidence:

- Yearly amounts $100, $200, $400 become two 100% YoY marks. The status is nevertheless `SUM(Amount): 200`, and `totalNote` returns no refusal.
- Eight annual observations $100 through $800 total $3,600. Forecast adds copied $500 and $600 marks. Status/grand total becomes $4,700, including $1,100 of hypothetical future money.

Recommended boundary: carry units and provenance through the calculation result. Suppress a monetary total for ratios/percent changes, describe period differences with their actual meaning, and separate observed totals from forecast totals. A forecast should not silently inflate the status figure representing the source money.

## P1 — worksheet adapter admits summary rows as ordinary facts; normal chart view omits its warning

`mentat/app/report_insights.py:283-292` reads every nonempty worksheet row into one untyped row set. It provides no row role, fact key, accounting layer, additive dimensions, or `independent_series` annotation. It cannot distinguish transaction rows from grand totals, overlapping sections, or repeated summaries. `:293` acknowledges the issue in `data.note`: “Worksheet totals and overlapping summaries may double count: filter to the subsection you need.”

`mentat/app/chart-studio.js:855-868` builds chart/export scope from report metadata, config, and `result.note` but omits `data.note`. The chart's visible note at `:895` also only includes compiler/result notes. The source warning is available in the separate Data Source tab at `:933`. Thus the ingestion path's only generic guard is not displayed beside a normal chart or carried into its assembled export scope.

This is a confirmed permissive mechanism, not a quantified claim about a particular live workbook. The upstream-accounting lane is independently inspecting actual published worksheets.

Recommended boundary: expose curated chart tables of one declared grain/accounting basis; preserve source summaries but keep them outside fact-table aggregation. Carry source provenance/caveats into chart scope. Unknown mixed-grain sheets should require a deliberate subsection or refuse a financial grand total, rather than rely on every analyst discovering the workbook layout.

## P2 — Count(Amount) counts missing amounts

`mentat/app/chart-math.js:208-213` and grouped path `:280` replace every selected row with 1 for Count, regardless of whether the chosen field is missing. `mentat/app/chart-studio-core.js:535-542` labels this `CNT(Amount)` when a measure was chosen.

Synthetic evidence: amounts [100, null, 50] produce `CNT(Amount): 3`, although there are only two non-null Amount values. This differs from a field count in Tableau and SQL; the current operation is a row count. The existing test `mentat/tests/test_chart_math.cjs:26-32` deliberately expects the null row to count.

Recommended boundary: distinguish Count rows, Count non-null field, and Count distinct identity. Counting transactions after joins or geography bridges requires explicit transaction identity.

## P2 — numeric filters apply before aggregation only

`mentat/app/chart-math.js:27-46` compares each raw row to the numeric filter threshold before grouping. The compiler at `mentat/app/chart-studio-core.js:243-245` carries no filter stage or aggregation. This is coherent as a raw-value filter but cannot express a Tableau aggregate measure filter.

Synthetic evidence: company A has receipts $60+$60, company B has $150. A raw Amount >=100 filter keeps only B. A SUM(Amount)>=100 filter would retain both A=$120 and B=$150. The UI needs to explicitly distinguish those intents before introducing richer Tableau-style interactions.

## Existing protections that work

- Grouped chart grand totals are suppressed, preventing a separate direct cross-series grand-total error (`chart-studio-core.js:510`).
- Top-N + Other pools raw rows and conserves additive totals (`chart-math.js:240-255`); tests verify the total stays $2,485 at different cutoffs.
- Missing money is dropped for SUM and is not converted to zero (`chart-math.js:212-214`).
- Ordinary bar charts aggregate only the selected Y measure, not every measure column. Extra shelf fields are silently ignored by the compiler, a separate semantics problem reproduced by the root audit lane.

## Tests executed

```powershell
node --test 'C:\Users\pgoff\Mentat\mentat\app\tests\chart-studio-core.test.js'
node --test 'C:\Users\pgoff\Mentat\mentat\tests\test_chart_math.cjs'
```

- Chart Studio core: **54 passed, 0 failed**.
- Chart math legacy suite: **14 passed, 1 failed**. Failure at `mentat/tests/test_chart_math.cjs:67`: stale expectation that more than 60 groups throws; implementation now folds the tail into Other. This test failure is independent of the monetary duplication findings.
- New bounded reproduction script: exit 0; all assertions confirm the defective results described above. These are diagnostic assertions of current behavior, not regression tests of desired behavior.

Why the passing core suite misses the money problems: tests `chart-studio-core.test.js:694-752` intentionally verify split row repetition and caveats but do not assert conservation for a monetary ZIP map. Grand-total tests at `:367-395` cover grouped, histogram, mean, and scatter, but omit split-money, YoY, and forecasts.
