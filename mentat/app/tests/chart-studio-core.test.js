/* Chart Studio compiler and Show Me table. */
// Node 24 rejects the bare directory form; run with the glob:
//   node --test "mentat/app/tests/**/*.test.js"
const test = require('node:test');
const assert = require('node:assert');
const core = require('../chart-studio-core.js');
const math = require('../chart-math.js');

const COLUMNS = [
  {index: 0, name: 'Election Cycle', type: 'category', distinct: 3, missing: 0},
  {index: 1, name: 'Recipient Category', type: 'category', distinct: 4, missing: 0},
  {index: 2, name: 'Amount', type: 'number', distinct: 9, missing: 0},
  {index: 3, name: 'Employee Tier', type: 'category', distinct: 2, missing: 0},
  {index: 4, name: 'Contribution Count', type: 'number', distinct: 5, missing: 0},
  {index: 5, name: 'Committee ID', type: 'category', distinct: 9, missing: 0},
  {index: 6, name: 'Date', type: 'date', distinct: 9, missing: 0}
];
const ROWS = [
  ['2021-2022', 'Company PAC', 1000, 'Chief', 4, 'C001', '2021-03-01'],
  ['2021-2022', 'Trade Association', 500, 'Employees', 2, 'C002', '2021-06-01'],
  ['2023-2024', 'Company PAC', 2000, 'Chief', 6, 'C001', '2023-03-01'],
  ['2023-2024', 'Leadership PAC', 250, 'Employees', 1, 'C003', '2023-09-01'],
  ['2025-2026', 'Company PAC', 3000, 'Chief', 9, 'C001', '2025-02-01'],
  ['2025-2026', 'Trade Association', 750, 'Employees', 3, 'C002', '2025-07-01']
];
const DATA = {sheet: 'Facts', header_row: 1, columns: COLUMNS, rows: ROWS,
  row_numbers: [2, 3, 4, 5, 6, 7], row_count: ROWS.length, sha256: 'test'};

const CYCLE = 0, CATEGORY = 1, AMOUNT = 2, TIER = 3, COUNT = 4, ID = 5;

function sheet(patch) {
  const state = core.createSheet('Sheet 1', 's1');
  return Object.assign(state, patch || {});
}
const marks = patch => Object.assign(core.createSheet('x').marks, patch);

/* ------------------------------------------------------------ field roles */

test('classifyFields splits dimensions, measures and hidden identifier fields', () => {
  const meta = core.classifyFields(COLUMNS);
  assert.deepStrictEqual(meta.dimensions.map(f => f.name), ['Election Cycle', 'Recipient Category', 'Employee Tier', 'Date']);
  assert.deepStrictEqual(meta.measures.map(f => f.name), ['Amount', 'Contribution Count']);
  assert.deepStrictEqual(meta.hidden.map(f => f.name), ['Committee ID']);
  assert.strictEqual(meta.fields[CYCLE].isTime, true);
  assert.strictEqual(meta.fields[CYCLE].glyph, 'Abc');
  assert.strictEqual(meta.fields[6].glyph, 'cal');
  assert.strictEqual(meta.fields[CATEGORY].glyph, 'Abc');
  assert.strictEqual(meta.fields[AMOUNT].glyph, '#');
});

test('paneBuckets lists the named fields in their own order, folds the rest and skips ids it lacks', () => {
  const fields = [{id: 'a', name: 'A'}, {id: 'b', name: 'B'}, {id: 'c', name: 'C'}, {id: 'd', name: 'D'}];
  const split = core.paneBuckets(fields, ['c', 'missing', 'a']);
  assert.deepStrictEqual(split.shown.map(f => f.id), ['c', 'a']);
  assert.deepStrictEqual(split.more.map(f => f.id), ['b', 'd']);
  assert.deepStrictEqual(core.paneBuckets(fields, null).shown, []);
  assert.deepStrictEqual(core.paneBuckets(fields, null).more.map(f => f.id), ['a', 'b', 'c', 'd']);
  assert.deepStrictEqual(core.paneBuckets(null, ['a']), {shown: [], more: []});
});

test('classification agrees with chart-math chartColumns on measures', () => {
  const engine = math.chartColumns(COLUMNS);
  const core_ = core.classifyFields(COLUMNS);
  assert.deepStrictEqual(engine.measures.map(c => c.index).sort(), core_.measures.map(f => f.index).sort());
});

/* --------------------------------------------------------- compileConfig */

test('dimensions reach grouping and extra measures are explicitly refused', () => {
  const report = core.compileReport(sheet({columns: [CATEGORY, TIER], rows: [AMOUNT, COUNT]}), COLUMNS);
  const config = report.config;
  assert.strictEqual(config.x, CATEGORY);
  assert.strictEqual(config.y, AMOUNT);
  assert.strictEqual(config.type, 'bar');
  assert.deepStrictEqual(config.dimensions, [CATEGORY, TIER]);
  assert.match(report.issues.join(' '), /show one measure/);
});

test('a measure pill carries its own aggregation, defaulting to sum', () => {
  assert.strictEqual(core.compileConfig(sheet({columns: [CATEGORY], rows: [AMOUNT]}), COLUMNS).aggregation, 'sum');
  for (const aggregation of ['mean', 'count', 'median', 'min', 'max']) {
    const config = core.compileConfig(sheet({columns: [CATEGORY], rows: [{column: AMOUNT, aggregation}]}), COLUMNS);
    assert.strictEqual(config.aggregation, aggregation, aggregation + ' should reach the config');
  }
});

test('a dimension with no measure counts rows', () => {
  const config = core.compileConfig(sheet({columns: [CATEGORY]}), COLUMNS);
  assert.strictEqual(config.y, -1);
  assert.strictEqual(config.aggregation, 'count');
  assert.strictEqual(config.type, 'bar');
});

test('a date dimension on Columns with a measure draws a line under Automatic', () => {
  const config = core.compileConfig(sheet({columns: [CYCLE], rows: [AMOUNT]}), COLUMNS);
  assert.strictEqual(config.type, 'line');
  assert.strictEqual(config.x, CYCLE);
  assert.strictEqual(config.period, 'cycle', 'an election-cycle column selects the two-year period');
});

test('a date dimension with no measure stays a bar of row counts', () => {
  assert.strictEqual(core.compileConfig(sheet({columns: [CYCLE]}), COLUMNS).type, 'bar');
});

test('two measures, one on each shelf, draw a scatter', () => {
  const config = core.compileConfig(sheet({columns: [COUNT], rows: [AMOUNT]}), COLUMNS);
  assert.strictEqual(config.type, 'scatter');
  assert.strictEqual(config.x, COUNT);
  assert.strictEqual(config.y, AMOUNT);
  assert.notStrictEqual(config.aggregation, 'count', 'scatter plots individual values');
});

test('a dimension on Rows with a measure on Columns draws horizontal bars', () => {
  const config = core.compileConfig(sheet({rows: [CATEGORY], columns: [AMOUNT]}), COLUMNS);
  assert.strictEqual(config.type, 'horizontal');
  assert.strictEqual(config.x, CATEGORY);
  assert.strictEqual(config.y, AMOUNT);
});

test('a Colour pill becomes the separate series and pairs the chart type', () => {
  const bar = core.compileConfig(sheet({columns: [CATEGORY], rows: [AMOUNT], marks: marks({color: TIER})}), COLUMNS);
  assert.strictEqual(bar.type, 'grouped');
  assert.strictEqual(bar.series, TIER);
  const horizontal = core.compileConfig(sheet({rows: [CATEGORY], columns: [AMOUNT], marks: marks({color: TIER})}), COLUMNS);
  assert.strictEqual(horizontal.type, 'groupedhorizontal');
  const line = core.compileConfig(sheet({columns: [CYCLE], rows: [AMOUNT], marks: marks({color: TIER})}), COLUMNS);
  assert.strictEqual(line.type, 'multiline');
  assert.strictEqual(line.series, TIER);
});

test('a Colour measure is refused with a note rather than becoming a series', () => {
  const report = core.compileReport(sheet({columns: [CATEGORY], rows: [AMOUNT], marks: marks({color: COUNT})}), COLUMNS);
  assert.strictEqual(report.config.series, -1);
  assert.strictEqual(report.config.type, 'bar');
  assert.match(report.notes.join(' '), /measure/);
});

test('explicit mark types override Automatic', () => {
  const expected = {bar: 'bar', line: 'line', area: 'area', circle: 'scatter', pie: 'pie', doughnut: 'doughnut',
    text: 'bar', box: 'box', histogram: 'histogram', waterfall: 'waterfall', pareto: 'pareto', radar: 'radar'};
  for (const [mark, type] of Object.entries(expected)) {
    const state = sheet({columns: [CYCLE], rows: [AMOUNT], marks: marks({type: mark})});
    const report = core.compileReport(state, COLUMNS);
    assert.strictEqual(report.config.type, type, mark + ' should compile to ' + type);
  }
  assert.strictEqual(core.compileReport(sheet({columns: [CYCLE], rows: [AMOUNT], marks: marks({type: 'text'})}), COLUMNS).renderMode, 'table');
  assert.strictEqual(core.compileReport(sheet({columns: [CYCLE], rows: [AMOUNT]}), COLUMNS).renderMode, 'chart');
});

test('a circle mark without two measures reports an issue', () => {
  const report = core.compileReport(sheet({columns: [CATEGORY], rows: [AMOUNT], marks: marks({type: 'circle'})}), COLUMNS);
  assert.ok(report.issues.length, 'a one-measure circle view cannot be drawn');
});

test('a histogram ignores the grouping column', () => {
  const config = core.compileConfig(sheet({columns: [CATEGORY], rows: [AMOUNT], marks: marks({type: 'histogram'})}), COLUMNS);
  assert.strictEqual(config.x, -1);
  assert.strictEqual(config.y, AMOUNT);
});

test('Swap exchanges Columns and Rows', () => {
  const before = sheet({columns: [CATEGORY], rows: [AMOUNT]});
  const after = core.swapShelves(before);
  assert.deepStrictEqual(core.shelf(after.columns), [{column: AMOUNT, aggregation: 'sum'}], 'rows move to columns');
  assert.deepStrictEqual(core.shelf(after.rows), [{column: CATEGORY, aggregation: 'sum'}], 'columns move to rows');
  assert.strictEqual(core.compileConfig(after, COLUMNS).type, 'horizontal');
  assert.strictEqual(core.compileConfig(before, COLUMNS).type, 'bar', 'the original state is not mutated');
});

test('filters, pages and row parameters reach the configuration', () => {
  const state = sheet({
    columns: [CATEGORY], rows: [AMOUNT],
    filters: [{column: TIER, op: 'equals', value: 'Chief'}, {column: AMOUNT, op: 'gte', value: '100'}, {column: TIER, op: 'equals', value: ''}],
    pages: CYCLE, pageMember: '2023-2024',
    params: {start: 3, end: 9, limit: 25}
  });
  const config = core.compileConfig(state, COLUMNS);
  assert.deepStrictEqual(config.filters, [
    {column: TIER, op: 'equals', value: 'Chief'},
    {column: AMOUNT, op: 'gte', value: '100'},
    {column: CYCLE, op: 'equals', value: '2023-2024'}
  ]);
  assert.strictEqual(config.start, 3);
  assert.strictEqual(config.end, 9);
  assert.strictEqual(config.limit, 25);
});

test('blank row parameters compile to zero, which the engine reads as unbounded', () => {
  const config = core.compileConfig(sheet({columns: [CATEGORY], rows: [AMOUNT], params: {start: '', end: null, limit: 'x'}}), COLUMNS);
  assert.deepStrictEqual([config.start, config.end, config.limit], [0, 0, 0]);
});

test('analytics map to transform, period and horizon', () => {
  const state = sheet({columns: [CYCLE], rows: [AMOUNT], analytics: {transform: 'forecast', period: 'cycle', horizon: 3}});
  const config = core.compileConfig(state, COLUMNS);
  assert.strictEqual(config.transform, 'forecast');
  assert.strictEqual(config.period, 'cycle');
  assert.strictEqual(config.horizon, 3);
});

test('time analysis without a date field is refused', () => {
  const report = core.compileReport(sheet({columns: [CATEGORY], rows: [AMOUNT], analytics: {transform: 'annual'}}), COLUMNS);
  assert.strictEqual(report.config.transform, 'none');
  assert.match(report.issues.join(' '), /date, year or election-cycle/);
});

test('time analysis forces a bar, line or area mark and drops Colour', () => {
  const state = sheet({columns: [CYCLE], rows: [AMOUNT], marks: marks({type: 'pie', color: TIER}), analytics: {transform: 'annual'}});
  const report = core.compileReport(state, COLUMNS);
  assert.strictEqual(report.config.type, 'line');
  assert.strictEqual(report.config.series, -1);
  assert.strictEqual(report.notes.length, 2);
});

test('time analysis asks for one Subject and filters to it', () => {
  const SUBJECT = 7;
  const SUBJECT_COLUMNS = COLUMNS.concat({index: SUBJECT, name: 'Subject', type: 'category', distinct: 2, missing: 0});
  const timed = patch => sheet(Object.assign({columns: [CYCLE], rows: [AMOUNT],
    analytics: {transform: 'annual', period: 'cycle', horizon: 2}}, patch || {}));

  const missing = core.compileReport(timed(), SUBJECT_COLUMNS);
  assert.match(missing.issues.join(' '), /Choose a Subject/);
  assert.ok(!missing.config.filters.some(f => f.column === SUBJECT), 'nothing is narrowed until the user chooses');

  const chosen = core.compileReport(timed({params: {start: 0, end: 0, limit: 0, subject: 'Company A'}}), SUBJECT_COLUMNS);
  assert.strictEqual(chosen.issues.length, 0, chosen.issues.join('; '));
  assert.deepStrictEqual(chosen.config.filters, [{column: SUBJECT, op: 'equals', value: 'Company A'}]);

  const shelved = core.compileReport(timed({filters: [{column: SUBJECT, op: 'equals', value: 'Company B'}],
    params: {start: 0, end: 0, limit: 0, subject: 'Company A'}}), SUBJECT_COLUMNS);
  assert.deepStrictEqual(shelved.config.filters, [{column: SUBJECT, op: 'equals', value: 'Company B'}],
    'a filter on the shelf wins and is not duplicated');

  const untimed = core.compileReport(sheet({columns: [CATEGORY], rows: [AMOUNT],
    params: {start: 0, end: 0, limit: 0, subject: 'Company A'}}), SUBJECT_COLUMNS);
  assert.deepStrictEqual(untimed.config.filters, [], 'the subject narrows time analysis only');

  assert.strictEqual(core.compileReport(timed(), COLUMNS).issues.length, 0, 'a worksheet with no Subject column is unaffected');
  assert.strictEqual(core.subjectField(core.classifyFields(SUBJECT_COLUMNS).fields).index, SUBJECT);
  assert.strictEqual(core.subjectField(core.classifyFields(COLUMNS).fields), null);
  assert.strictEqual(core.createSheet('s').params.subject, '', 'a new sheet starts with no subject chosen');
});

test('an empty sheet compiles to no configuration and says why', () => {
  const report = core.compileReport(sheet({}), COLUMNS);
  assert.strictEqual(report.config, null);
  assert.match(report.issues.join(' '), /Add a grouping \(company, recipient, cycle\) and a dollar measure\./);
});

test('hidden identifier fields still compile when a user places them', () => {
  const config = core.compileConfig(sheet({columns: [ID], rows: [AMOUNT]}), COLUMNS);
  assert.strictEqual(config.x, ID);
  assert.strictEqual(config.type, 'bar');
});

/* ------------------------------------- the compiled config drives build() */

test('every compiled configuration is accepted by the chart engine', () => {
  const cases = [
    ['bar', sheet({columns: [CATEGORY], rows: [AMOUNT]})],
    ['count bar', sheet({columns: [CATEGORY]})],
    ['line', sheet({columns: [CYCLE], rows: [AMOUNT]})],
    ['horizontal', sheet({rows: [CATEGORY], columns: [AMOUNT]})],
    ['scatter', sheet({columns: [COUNT], rows: [AMOUNT]})],
    ['grouped', sheet({columns: [CATEGORY], rows: [AMOUNT], marks: marks({color: TIER})})],
    ['groupedhorizontal', sheet({rows: [CATEGORY], columns: [AMOUNT], marks: marks({color: TIER})})],
    ['multiline', sheet({columns: [CYCLE], rows: [AMOUNT], marks: marks({color: TIER})})],
    ['pie', sheet({columns: [CATEGORY], rows: [AMOUNT], marks: marks({type: 'pie'})})],
    ['doughnut', sheet({columns: [CATEGORY], rows: [AMOUNT], marks: marks({type: 'doughnut'})})],
    ['area', sheet({columns: [CYCLE], rows: [AMOUNT], marks: marks({type: 'area'})})],
    ['box', sheet({columns: [CATEGORY], rows: [AMOUNT], marks: marks({type: 'box'})})],
    ['histogram', sheet({rows: [AMOUNT], marks: marks({type: 'histogram'})})],
    ['waterfall', sheet({columns: [CATEGORY], rows: [AMOUNT], marks: marks({type: 'waterfall'})})],
    ['pareto', sheet({columns: [CATEGORY], rows: [AMOUNT], marks: marks({type: 'pareto'})})],
    ['radar', sheet({columns: [CATEGORY], rows: [AMOUNT], marks: marks({type: 'radar'})})],
    ['text table', sheet({columns: [CATEGORY], rows: [AMOUNT], marks: marks({type: 'text'})})],
    ['period totals', sheet({columns: [CYCLE], rows: [AMOUNT], analytics: {transform: 'annual', period: 'cycle', horizon: 2}})],
    ['period change', sheet({columns: [CYCLE], rows: [AMOUNT], analytics: {transform: 'change', period: 'cycle', horizon: 2}})],
    ['filtered', sheet({columns: [CATEGORY], rows: [AMOUNT], filters: [{column: TIER, op: 'equals', value: 'Chief'}]})]
  ];
  for (const [name, state] of cases) {
    const report = core.compileReport(state, COLUMNS);
    assert.strictEqual(report.issues.length, 0, name + ' should compile cleanly: ' + report.issues.join('; '));
    const result = math.build(DATA, report.config);
    assert.ok(result && result.type, name + ' should build');
  }
});

test('the 15 chart types the classic dialog offers are all reachable', () => {
  const reached = new Set();
  const states = [
    sheet({columns: [CATEGORY], rows: [AMOUNT]}),
    sheet({columns: [CYCLE], rows: [AMOUNT]}),
    sheet({rows: [CATEGORY], columns: [AMOUNT]}),
    sheet({columns: [COUNT], rows: [AMOUNT]}),
    sheet({columns: [CATEGORY], rows: [AMOUNT], marks: marks({color: TIER})}),
    sheet({rows: [CATEGORY], columns: [AMOUNT], marks: marks({color: TIER})}),
    sheet({columns: [CYCLE], rows: [AMOUNT], marks: marks({color: TIER})}),
    sheet({columns: [CATEGORY], rows: [AMOUNT], marks: marks({type: 'pie'})}),
    sheet({columns: [CATEGORY], rows: [AMOUNT], marks: marks({type: 'doughnut'})}),
    sheet({columns: [CYCLE], rows: [AMOUNT], marks: marks({type: 'area'})}),
    sheet({columns: [CATEGORY], rows: [AMOUNT], marks: marks({type: 'box'})}),
    sheet({rows: [AMOUNT], marks: marks({type: 'histogram'})}),
    sheet({columns: [CATEGORY], rows: [AMOUNT], marks: marks({type: 'waterfall'})}),
    sheet({columns: [CATEGORY], rows: [AMOUNT], marks: marks({type: 'pareto'})}),
    sheet({columns: [CATEGORY], rows: [AMOUNT], marks: marks({type: 'radar'})})
  ];
  for (const state of states) reached.add(core.compileConfig(state, COLUMNS).type);
  for (const type of math.chartTypes) assert.ok(reached.has(type), type + ' must stay reachable from the shelves');
});

/* ----------------------------------------------------------- sort and sum */

test('Sort orders the x dimension by the y measure and leaves scatter alone', () => {
  const config = core.compileConfig(sheet({columns: [CATEGORY], rows: [AMOUNT]}), COLUMNS);
  const result = math.build(DATA, config);
  assert.deepStrictEqual(core.sortResult(result, 'desc').groups.map(g => g.value), [6000, 1250, 250]);
  assert.deepStrictEqual(core.sortResult(result, 'asc').groups.map(g => g.value), [250, 1250, 6000]);
  assert.deepStrictEqual(core.sortResult(result, 'none').groups.map(g => g.value), result.groups.map(g => g.value));
  const scatter = math.build(DATA, core.compileConfig(sheet({columns: [COUNT], rows: [AMOUNT]}), COLUMNS));
  assert.strictEqual(core.sortResult(scatter, 'desc'), scatter);
});

test('a time view keeps chronological order whatever Sort says', () => {
  const line = core.compileConfig(sheet({columns: [CYCLE], rows: [AMOUNT]}), COLUMNS);
  const lineResult = math.build(DATA, line);
  const order = lineResult.groups.map(g => g.label);
  assert.deepStrictEqual(core.sortResult(lineResult, 'desc').groups.map(g => g.label), order, 'a line keeps its axis order');
  assert.deepStrictEqual(core.sortResult(lineResult, 'asc').groups.map(g => g.label), order);

  const overTime = core.compileConfig(sheet({columns: [CYCLE], rows: [AMOUNT],
    analytics: {transform: 'annual', period: 'cycle', horizon: 2}}), COLUMNS);
  const temporalResult = math.build(DATA, overTime);
  assert.strictEqual(temporalResult.temporal, true);
  assert.deepStrictEqual(core.sortResult(temporalResult, 'desc').groups.map(g => g.label),
    temporalResult.groups.map(g => g.label), 'periods stay in order');

  const bar = core.compileConfig(sheet({columns: [CATEGORY], rows: [AMOUNT]}), COLUMNS);
  assert.deepStrictEqual(core.sortResult(math.build(DATA, bar), 'desc').groups.map(g => g.value),
    [6000, 1250, 250], 'a bar view still sorts');

  assert.strictEqual(core.sortLocked(lineResult), true);
  assert.strictEqual(core.sortLocked(temporalResult), true);
  assert.strictEqual(core.sortLocked(overTime), true, 'a compiled time configuration locks Sort before the view is built');
  assert.strictEqual(core.sortLocked(core.compileConfig(sheet({columns: [CYCLE], rows: [AMOUNT],
    marks: marks({color: TIER})}), COLUMNS)), true, 'separate lines are a time view too');
  assert.strictEqual(core.sortLocked(bar), false);
  assert.strictEqual(core.sortLocked(math.build(DATA, bar)), false);
  assert.strictEqual(core.sortLocked(null), false);
});

test('rowsToMarksSummary describes the view for the status bar', () => {
  const config = core.compileConfig(sheet({columns: [CATEGORY], rows: [AMOUNT]}), COLUMNS);
  const summary = core.rowsToMarksSummary(math.build(DATA, config), config, COLUMNS);
  assert.strictEqual(summary.marks, 3);
  assert.strictEqual(summary.viewRows, 1);
  assert.strictEqual(summary.viewColumns, 3);
  assert.strictEqual(summary.measureLabel, 'SUM(Amount)');
  assert.strictEqual(summary.total, 7500);
  const grouped = core.compileConfig(sheet({columns: [CATEGORY], rows: [AMOUNT], marks: marks({color: TIER})}), COLUMNS);
  const groupedSummary = core.rowsToMarksSummary(math.build(DATA, grouped), grouped, COLUMNS);
  assert.strictEqual(groupedSummary.viewRows, 2, 'two colour members are two rows of the view');
  assert.strictEqual(groupedSummary.marks, 3, 'gaps are not marks');
});

test('mark values follow the order the renderer appends marks', () => {
  const config = core.compileConfig(sheet({columns: [CATEGORY], rows: [AMOUNT]}), COLUMNS);
  const result = math.build(DATA, config);
  assert.deepStrictEqual(core.markValues(result), result.groups.map(g => g.value));
  assert.deepStrictEqual(core.markValues(math.build(DATA, core.compileConfig(sheet({columns: [COUNT], rows: [AMOUNT]}), COLUMNS))), []);
});

test('reference lines average and median the plotted marks', () => {
  const config = core.compileConfig(sheet({columns: [CATEGORY], rows: [AMOUNT]}), COLUMNS);
  const result = math.build(DATA, config);
  const lines = core.referenceValues(result, {average: true, median: true});
  assert.deepStrictEqual(lines.map(l => l.kind), ['average', 'median']);
  assert.strictEqual(lines[0].value, 2500);
  assert.strictEqual(lines[1].value, 1250);
  assert.deepStrictEqual(core.referenceValues(result, {}), []);
});

test('a grand total is withheld unless the marks are additive parts of one whole', () => {
  const sum = core.compileConfig(sheet({columns: [CATEGORY], rows: [AMOUNT]}), COLUMNS);
  const sumResult = math.build(DATA, sum);
  assert.strictEqual(core.totalNote(sumResult, sum), '');
  assert.strictEqual(core.grandTotal(sumResult, sum), core.markValues(sumResult).reduce((a, b) => a + b, 0));
  assert.strictEqual(core.rowsToMarksSummary(sumResult, sum, COLUMNS).total, 7500);

  const grouped = core.compileConfig(sheet({columns: [CATEGORY], rows: [AMOUNT], marks: marks({color: TIER})}), COLUMNS);
  const groupedResult = math.build(DATA, grouped);
  assert.strictEqual(core.grandTotal(groupedResult, grouped), null, 'independent series have no combined total');
  assert.match(core.totalNote(groupedResult, grouped), /series are independent/);
  assert.strictEqual(core.rowsToMarksSummary(groupedResult, grouped, COLUMNS).total, null);

  const histogram = core.compileConfig(sheet({rows: [AMOUNT], marks: marks({type: 'histogram'})}), COLUMNS);
  const histogramResult = math.build(DATA, histogram);
  assert.strictEqual(core.grandTotal(histogramResult, histogram), null, 'bin counts are not a total of the measure');
  assert.match(core.totalNote(histogramResult, histogram), /histogram/);

  const mean = core.compileConfig(sheet({columns: [CATEGORY], rows: [{column: AMOUNT, aggregation: 'mean'}]}), COLUMNS);
  const meanResult = math.build(DATA, mean);
  assert.strictEqual(core.grandTotal(meanResult, mean), null, 'a sum of means is not a total');
  assert.match(core.totalNote(meanResult, mean), /SUM and COUNT/);
  assert.strictEqual(core.rowsToMarksSummary(meanResult, mean, COLUMNS).total, null);

  const box = core.compileConfig(sheet({columns: [CATEGORY], rows: [AMOUNT], marks: marks({type: 'box'})}), COLUMNS);
  assert.strictEqual(core.grandTotal(math.build(DATA, box), box), null);
  const scatter = core.compileConfig(sheet({columns: [COUNT], rows: [AMOUNT]}), COLUMNS);
  assert.strictEqual(core.rowsToMarksSummary(math.build(DATA, scatter), scatter, COLUMNS).total, null);
});

test('reference lines are withheld from independent series', () => {
  const grouped = core.compileConfig(sheet({columns: [CATEGORY], rows: [AMOUNT], marks: marks({color: TIER})}), COLUMNS);
  assert.deepStrictEqual(core.referenceValues(math.build(DATA, grouped), {average: true, median: true}), []);
});

/* --------------------------------------------------------------- show me */

test('Show Me holds the 24 Tableau tiles in order', () => {
  assert.strictEqual(core.SHOW_ME.length, 24);
  assert.deepStrictEqual(core.SHOW_ME.map(t => t.id), [
    'text-table', 'heat-map', 'highlight-table', 'symbol-map', 'filled-map', 'pie-chart',
    'horizontal-bars', 'stacked-bars', 'side-by-side-bars', 'treemap', 'circle-views', 'side-by-side-circles',
    'lines-continuous', 'lines-discrete', 'dual-lines', 'area-continuous', 'area-discrete', 'dual-combination',
    'scatter-plot', 'histogram', 'box-and-whisker', 'gantt', 'bullet-graph', 'packed-bubbles']);
});

test('the nine out-of-release tiles are always disabled', () => {
  const off = core.showMeEligibility({dimensions: 9, measures: 9, times: 9}).filter(t => !t.enabled);
  assert.deepStrictEqual(off.map(t => t.id), ['heat-map', 'highlight-table', 'symbol-map', 'filled-map',
    'treemap', 'dual-combination', 'gantt', 'bullet-graph', 'packed-bubbles']);
  for (const t of off) assert.strictEqual(t.reason, 'not in this release');
});

test('the Show Me eligibility table greys tiles the field selection cannot satisfy', () => {
  const table = selection => {
    const map = {};
    for (const t of core.showMeEligibility(selection)) map[t.id] = t.enabled;
    return map;
  };
  const none = table({dimensions: 0, measures: 0, times: 0});
  assert.deepStrictEqual(Object.values(none).filter(Boolean), []);

  const oneMeasure = table({dimensions: 0, measures: 1, times: 0});
  assert.deepStrictEqual(Object.keys(oneMeasure).filter(id => oneMeasure[id]), ['histogram', 'box-and-whisker']);

  const twoMeasures = table({dimensions: 0, measures: 2, times: 0});
  assert.deepStrictEqual(Object.keys(twoMeasures).filter(id => twoMeasures[id]), ['scatter-plot', 'histogram', 'box-and-whisker']);

  const oneEach = table({dimensions: 1, measures: 1, times: 0});
  assert.deepStrictEqual(Object.keys(oneEach).filter(id => oneEach[id]),
    ['text-table', 'pie-chart', 'horizontal-bars', 'circle-views', 'histogram', 'box-and-whisker']);

  const twoDimensions = table({dimensions: 2, measures: 1, times: 0});
  assert.deepStrictEqual(Object.keys(twoDimensions).filter(id => twoDimensions[id]),
    ['text-table', 'pie-chart', 'horizontal-bars', 'stacked-bars', 'side-by-side-bars', 'circle-views',
     'side-by-side-circles', 'histogram', 'box-and-whisker']);

  const dated = table({dimensions: 1, measures: 1, times: 1});
  for (const id of ['lines-continuous', 'lines-discrete', 'area-continuous', 'area-discrete']) assert.strictEqual(dated[id], true, id);
  assert.strictEqual(dated['dual-lines'], false, 'dual lines need a second dimension for the colour series');
  assert.strictEqual(table({dimensions: 2, measures: 1, times: 1})['dual-lines'], true);
});

test('a tile that needs a date says so', () => {
  const line = core.showMeEligibility({dimensions: 4, measures: 4, times: 0}).find(t => t.id === 'lines-continuous');
  assert.match(line.reason, /date, year or election-cycle/);
});

test('the selection counts shelf fields plus anything picked in the Data pane', () => {
  const state = sheet({columns: [CATEGORY], rows: [AMOUNT], marks: marks({color: TIER})});
  assert.deepStrictEqual(core.showMeSelection(state, COLUMNS, []), Object.assign(core.showMeSelection(state, COLUMNS, []), {
    dimensions: 2, measures: 1, times: 0
  }));
  const widened = core.showMeSelection(state, COLUMNS, [CYCLE]);
  assert.strictEqual(widened.dimensions, 3);
  assert.strictEqual(widened.times, 1);
});

test('clicking a tile sets marks and shelves in one step', () => {
  const base = sheet({source: {sheet: 'Facts'}});
  const selection = [CYCLE, CATEGORY, TIER, AMOUNT, COUNT];
  const expect = (id, type) => {
    const next = core.showMeApply(id, base, COLUMNS, selection);
    const report = core.compileReport(next, COLUMNS);
    assert.strictEqual(report.issues.length, 0, id + ': ' + report.issues.join('; '));
    assert.strictEqual(report.config.type, type, id + ' should build a ' + type);
    assert.ok(math.build(DATA, report.config), id + ' should render');
    return report.config;
  };
  expect('text-table', 'bar');
  expect('pie-chart', 'pie');
  assert.strictEqual(expect('horizontal-bars', 'horizontal').x, CATEGORY);
  assert.strictEqual(expect('stacked-bars', 'grouped').series, TIER);
  assert.strictEqual(expect('side-by-side-bars', 'grouped').series, TIER);
  expect('circle-views', 'line');
  expect('side-by-side-circles', 'multiline');
  assert.strictEqual(expect('lines-continuous', 'line').x, CYCLE);
  assert.strictEqual(expect('lines-discrete', 'line').transform, 'annual');
  expect('dual-lines', 'multiline');
  expect('area-continuous', 'area');
  assert.strictEqual(expect('area-discrete', 'area').transform, 'annual');
  const scatter = expect('scatter-plot', 'scatter');
  assert.strictEqual(scatter.x, AMOUNT);
  assert.strictEqual(scatter.y, COUNT);
  assert.strictEqual(expect('histogram', 'histogram').x, -1);
  expect('box-and-whisker', 'box');
  assert.strictEqual(core.showMeApply('treemap', base, COLUMNS, selection).marks.type, 'automatic', 'a disabled tile changes nothing');
});

test('the recommended tile follows chart-math recommend()', () => {
  assert.strictEqual(core.recommendedTile(COLUMNS), 'horizontal-bars');
  assert.strictEqual(core.recommendedTile([COLUMNS[AMOUNT], COLUMNS[COUNT]]), 'box-and-whisker');
  assert.strictEqual(core.recommendedTile([]), '');
});

/* ------------------------------------------------------------- housekeeping */

test('Clear keeps the data source and drops the view', () => {
  const state = sheet({columns: [CATEGORY], rows: [AMOUNT], marks: marks({type: 'pie'}), sort: 'desc'});
  state.source = {run: 'r', report: '0', sheet: 'Facts', header: 5, sha256: 'abc'};
  const cleared = core.clearSheet(state);
  assert.deepStrictEqual(cleared.columns, []);
  assert.deepStrictEqual(cleared.rows, []);
  assert.strictEqual(cleared.marks.type, 'automatic');
  assert.strictEqual(cleared.sort, 'none');
  assert.deepStrictEqual(cleared.source, state.source);
});

test('the session key names the worksheet, not just the workbook digest', () => {
  const fields = {run: 'r1', report: '0', sheet: 'Facts', header: 1};
  const body = {sheet: 'Facts', header_row: 1, sha256: 'abc'};
  const facts = core.sourceKey(fields, body);
  assert.strictEqual(facts, core.sourceKey(fields, {sheet: 'Facts', header_row: 1, sha256: 'abc'}), 'the same worksheet keeps its key');
  assert.notStrictEqual(facts, core.sourceKey(fields, {sheet: 'Funding Cohorts', header_row: 1, sha256: 'abc'}),
    'two worksheets of one workbook share a digest and must not share a key');
  assert.notStrictEqual(facts, core.sourceKey(fields, {sheet: 'Facts', header_row: 4, sha256: 'abc'}), 'the header row participates');
  assert.notStrictEqual(facts, core.sourceKey(Object.assign({}, fields, {report: '1'}), body), 'the report participates');
  assert.ok(facts.includes('|'), 'a legacy bare-digest key must be distinguishable');
  assert.strictEqual(core.sourceKey(fields, {}), 'r1|0|Facts||', 'an unscanned source falls back to the chosen worksheet');
});

test('pill accepts a bare column index, a numeric string and a full pill', () => {
  assert.deepStrictEqual(core.pill(3), {column: 3, aggregation: 'sum'});
  assert.deepStrictEqual(core.pill('3'), {column: 3, aggregation: 'sum'});
  assert.deepStrictEqual(core.pill({column: 3, aggregation: 'median'}), {column: 3, aggregation: 'median'});
  assert.deepStrictEqual(core.pill({column: 3, aggregation: 'bogus'}), {column: 3, aggregation: 'sum'});
  assert.strictEqual(core.pill(null), null);
  assert.strictEqual(core.pill({}), null);
});

/* ------------------------------------ group limit, Other rollup and cell splitting */

// Seventy recipients: more groups than any chart can show, so the engine folds
// the tail instead of refusing to draw. Amount i makes the ranking unambiguous.
const WIDE_COLUMNS = [
  {index: 0, name: 'Recipient', type: 'category', distinct: 70, missing: 0},
  {index: 1, name: 'Amount', type: 'number', distinct: 70, missing: 0},
  {index: 2, name: 'Party', type: 'category', distinct: 2, missing: 0},
  {index: 3, name: 'ZIPs', type: 'category', distinct: 5, missing: 0}
];
// Rows 5 and 6 name two ZIPs, row 7 names three; every other row names one.
const WIDE_ZIP = i => i === 5 || i === 6 ? '10001; 10002' : i === 7 ? '10001; 10002; 10003' : '10001';
const WIDE_ROWS = Array.from({length: 70}, (_, n) => {
  const i = n + 1;
  return ['R' + i, i, i % 2 ? 'D' : 'R', WIDE_ZIP(i)];
});
const WIDE = {sheet: 'Wide', header_row: 1, columns: WIDE_COLUMNS, rows: WIDE_ROWS,
  row_numbers: WIDE_ROWS.map((_, n) => n + 2), row_count: WIDE_ROWS.length, sha256: 'wide'};

const RECIPIENT = 0, WIDE_AMOUNT = 1, PARTY = 2, ZIPS = 3;
const wide = patch => Object.assign({type: 'bar', x: RECIPIENT, y: WIDE_AMOUNT, aggregation: 'sum',
  transform: 'none', series: -1, filters: []}, patch || {});
const labels = result => result.groups.map(g => g.label);
const sum = (from, to) => (from + to) * (to - from + 1) / 2;

test('more groups than the limit fold into one Other mark instead of refusing to draw', () => {
  // No limit in the configuration means the engine's own default, which is the 60
  // per view the classic dialog and the funding comparison have always allowed.
  assert.strictEqual(math.DEFAULT_GROUP_LIMIT, 60);
  const standing = math.build(WIDE, wide());
  assert.strictEqual(standing.groups.length, 61, '60 kept plus one Other');
  const tail = standing.groups[60];
  assert.strictEqual(tail.other, true, 'Other is the last mark');
  assert.strictEqual(tail.folded, 10);
  assert.strictEqual(tail.label, 'Other (10 groups)');
  assert.strictEqual(tail.value, sum(1, 10));
  assert.strictEqual(tail.value, 55, 'Other totals the 10 smallest amounts');
  assert.strictEqual(tail.n, 10);
  assert.deepStrictEqual(labels(standing).slice(0, 60), Array.from({length: 60}, (_, n) => 'R' + (n + 11)),
    'the 60 largest survive, in the order the rows arrived');
  assert.match(standing.note, /Top 60 of 70/);
  assert.match(standing.note, /the other 10 groups are combined into "Other \(10 groups\)"/);
  assert.match(standing.note, /Raise the group limit in Parameters/);

  // 61 groups against the engine's own 60 is the boundary the legacy callers now
  // reach, and the one case where the count needs a singular noun and verb.
  const single = math.build(WIDE, wide({limit: 61}));
  assert.strictEqual(single.groups.length, 61, '60 kept plus one Other');
  const one = single.groups[60];
  assert.strictEqual(one.label, 'Other (1 group)', 'singular at one folded group');
  assert.strictEqual(one.folded, 1);
  assert.strictEqual(one.value, 1, 'the single smallest amount');
  assert.strictEqual(one.n, 1);
  assert.match(single.note, /Top 60 of 61/);
  assert.match(single.note, /the other 1 group is combined into "Other \(1 group\)"/);

  // Chart Studio compiles its own tighter limit onto every configuration.
  const result = math.build(WIDE, wide({maxGroups: 40}));
  assert.strictEqual(result.groups.length, 41, '40 kept plus one Other');
  const other = result.groups[result.groups.length - 1];
  assert.strictEqual(other.other, true, 'Other is the last mark');
  assert.strictEqual(other.folded, 30);
  assert.strictEqual(other.label, 'Other (30 groups)');
  assert.strictEqual(other.value, sum(1, 30), 'Other totals the 30 smallest amounts');
  assert.strictEqual(other.value, 465);
  assert.strictEqual(other.n, 30);
  assert.deepStrictEqual(labels(result).slice(0, 40), Array.from({length: 40}, (_, n) => 'R' + (n + 31)),
    'the 40 largest survive, in the order the rows arrived');
  assert.match(result.note, /Top 40 of 70/);
  assert.match(result.note, /Raise the group limit in Parameters/);
});

test('the group limit is a parameter, and a high enough one folds nothing', () => {
  const sixty = math.build(WIDE, wide({maxGroups: 60}));
  assert.strictEqual(sixty.groups.length, 61);
  assert.strictEqual(sixty.groups[60].folded, 10);
  assert.strictEqual(sixty.groups[60].value, sum(1, 10));
  assert.match(sixty.note, /Top 60 of 70/);

  const all = math.build(WIDE, wide({maxGroups: 100}));
  assert.strictEqual(all.groups.length, 70);
  assert.ok(!all.groups.some(g => g.other), 'nothing is folded');
  assert.ok(!('note' in all), 'an unfolded result keeps the old shape, with no note key');
  assert.strictEqual(math.DEFAULT_GROUP_LIMIT, 60);
});

test('folding does not change the grand total', () => {
  const config = wide();
  assert.strictEqual(core.grandTotal(math.build(WIDE, config), config), sum(1, 70));
  assert.strictEqual(core.grandTotal(math.build(WIDE, config), config), 2485);
  const tight = wide({maxGroups: 40});
  assert.strictEqual(core.grandTotal(math.build(WIDE, tight), tight), 2485, 'a deeper fold still totals the same');
  assert.strictEqual(core.grandTotal(math.build(WIDE, wide({maxGroups: 100})), wide({maxGroups: 100})), 2485,
    'the same total whether or not the tail is folded');
});

test('Other pools the raw rows, so every aggregation reads the folded rows themselves', () => {
  const other = aggregation => {
    const result = math.build(WIDE, wide({aggregation, maxGroups: 40}));
    const last = result.groups[result.groups.length - 1];
    assert.strictEqual(last.other, true, aggregation + ' should still fold');
    return last;
  };
  assert.strictEqual(other('mean').value, 15.5, 'the mean of 1..30, not a mean of means');
  assert.strictEqual(other('median').value, 15.5);
  assert.strictEqual(other('min').value, 1);
  assert.strictEqual(other('max').value, 30);
  const counted = other('count');
  assert.strictEqual(counted.value, 30, 'counting rows counts every folded row');
  assert.strictEqual(counted.folded, 30);
  assert.match(math.build(WIDE, wide({aggregation: 'count', maxGroups: 40})).note, /groups by row count/);
});

test('a side-by-side comparison folds its grouping field the same way', () => {
  const result = math.build(WIDE, wide({type: 'grouped', series: PARTY, maxGroups: 40}));
  assert.deepStrictEqual(result.series, ['D', 'R']);
  assert.strictEqual(result.groups.length, 41);
  assert.deepStrictEqual(labels(result).slice(0, 40), Array.from({length: 40}, (_, n) => 'R' + (n + 31)));
  const other = result.groups[40];
  assert.strictEqual(other.label, 'Other (30 groups)');
  assert.strictEqual(other.other, true);
  assert.strictEqual(other.folded, 30);
  assert.deepStrictEqual(other.values, [
    {series: 'D', value: 225, n: 15},
    {series: 'R', value: 240, n: 15}
  ], 'each series pools only the folded rows that belong to it');
  assert.match(result.note, /Top 40 of 70/);
  assert.match(result.note, /Series are independent/, 'the standing caveat is kept');
});

test('a group limit that is not a positive whole number is refused', () => {
  for (const maxGroups of [1.5, -3, 0.5, -1]) {
    assert.throws(() => math.build(WIDE, wide({maxGroups})), /Group limit must be a positive whole number/,
      String(maxGroups) + ' is not a group limit');
    assert.throws(() => math.build(DATA, {type: 'bar', x: CATEGORY, y: AMOUNT, aggregation: 'sum', maxGroups}),
      /Group limit must be a positive whole number/, 'a small worksheet is checked too');
  }
  assert.throws(() => math.build(WIDE, wide({type: 'grouped', series: PARTY, maxGroups: 1.5})),
    /Group limit must be a positive whole number/);
});

test('Sort reorders the real groups and leaves Other at the end', () => {
  const synthetic = {type: 'bar', groups: [
    {label: 'A', value: 10, n: 1}, {label: 'B', value: 30, n: 1}, {label: 'C', value: 20, n: 1},
    {label: 'Other (2 groups)', value: 99, n: 2, other: true, folded: 2}], selected: 5, excluded: 0};
  assert.deepStrictEqual(labels(core.sortResult(synthetic, 'desc')), ['B', 'C', 'A', 'Other (2 groups)']);
  assert.deepStrictEqual(labels(core.sortResult(synthetic, 'asc')), ['A', 'C', 'B', 'Other (2 groups)']);
  assert.deepStrictEqual(labels(synthetic), ['A', 'B', 'C', 'Other (2 groups)'], 'the result is not mutated');

  const built = math.build(WIDE, wide({maxGroups: 40}));
  for (const direction of ['asc', 'desc']) {
    const sorted = core.sortResult(built, direction);
    assert.strictEqual(sorted.groups[sorted.groups.length - 1].other, true, direction + ' keeps Other last');
    assert.strictEqual(sorted.groups.length, 41);
  }
});

test('splitting a multi-value cell makes one row per value and leaves the data alone', () => {
  const exploded = math.explodeRows(WIDE, {splitMulti: true, x: ZIPS, series: -1});
  assert.strictEqual(exploded.rows.length, 74, '70 rows plus 4 extra parts');
  assert.deepStrictEqual(exploded.split, {cells: 3, values: 7, columns: ['ZIPs']});
  assert.strictEqual(exploded.row_numbers.length, 74);
  assert.strictEqual(exploded.row_numbers.filter(n => n === 6).length, 2, 'worksheet row 6 is named twice');
  assert.strictEqual(exploded.row_numbers.filter(n => n === 7).length, 2);
  assert.strictEqual(exploded.row_numbers.filter(n => n === 8).length, 3, 'three ZIPs, three marks, one row');
  assert.strictEqual(exploded.row_numbers.filter(n => n === 5).length, 1);
  assert.deepStrictEqual(exploded.rows.slice(4, 11).map(r => [r[0], r[ZIPS]]),
    [['R5', '10001'], ['R5', '10002'], ['R6', '10001'], ['R6', '10002'],
     ['R7', '10001'], ['R7', '10002'], ['R7', '10003']]);
  assert.strictEqual(WIDE.rows.length, 70, 'the worksheet rows are never rewritten');
  assert.strictEqual(WIDE.rows[6][ZIPS], '10001; 10002; 10003');

  assert.strictEqual(math.explodeRows(WIDE, {splitMulti: false, x: ZIPS, series: -1}), WIDE, 'splitting is opt-in');
  assert.strictEqual(math.explodeRows(WIDE, {splitMulti: true, x: RECIPIENT, series: -1}), WIDE,
    'a column with nothing to split is left alone, with no split record');
  assert.strictEqual(math.explodeRows(WIDE, {splitMulti: true, x: WIDE_AMOUNT, series: -1}), WIDE,
    'a measure is never split');

  const pair = {columns: [{index: 0, name: 'A', type: 'category'}, {index: 1, name: 'B', type: 'category'}],
    rows: [['x; y', 'p; q'], ['z', 'r']], row_numbers: [2, 3]};
  assert.throws(() => math.explodeRows(pair, {splitMulti: true, x: 0, series: 1}), /pairings are unknown/);
});

test('a split view counts a row once per value and says so', () => {
  const config = wide({x: ZIPS, y: -1, aggregation: 'count', splitMulti: true});
  const result = math.build(WIDE, config);
  assert.deepStrictEqual(result.groups.map(g => [g.label, g.value]), [['10001', 70], ['10002', 3], ['10003', 1]]);
  assert.strictEqual(result.selected, 74, 'the split rows are the rows the view selected');
  assert.match(result.note, /split on ";"/);
  assert.match(result.note, /count a split row once per value/);

  const joined = math.build(WIDE, wide({x: ZIPS, y: -1, aggregation: 'count'}));
  assert.deepStrictEqual(joined.groups.map(g => [g.label, g.value]),
    [['10001', 67], ['10001; 10002', 2], ['10001; 10002; 10003', 1]], 'without the parameter the joined string is one group');
  assert.ok(!('note' in joined));
});

test('a split result carries the split facts, so a reader is told values not rows', () => {
  const split = math.build(WIDE, wide({x: ZIPS, y: -1, aggregation: 'count', splitMulti: true}));
  assert.deepStrictEqual(split.split, {cells: 3, values: 7, columns: ['ZIPs']});
  assert.strictEqual(split.selected, 74, 'selected counts exploded rows');
  assert.ok(split.selected > WIDE.row_count,
    'which is why a caller must not print it as a share of the worksheet');

  const joined = math.build(WIDE, wide({x: ZIPS, y: -1, aggregation: 'count'}));
  assert.ok(!('split' in joined), 'an unsplit result keeps the old shape');
  assert.strictEqual(joined.selected, 70, 'and selected is a plain row count');

  const compared = math.build(WIDE, wide({type: 'grouped', x: ZIPS, series: PARTY, splitMulti: true, aggregation: 'count', y: -1}));
  assert.deepStrictEqual(compared.split, {cells: 3, values: 7, columns: ['ZIPs']},
    'Party was eligible to split but holds no multi-value cell, so the note does not name it');
  assert.strictEqual(compared.selected, 74);
  assert.ok(!('split' in math.build(WIDE, wide({type: 'grouped', x: ZIPS, series: PARTY}))),
    'a comparison without the parameter carries no split facts');
});

test('the group limit and the split parameter reach the configuration', () => {
  const config = core.compileConfig(sheet({columns: [CATEGORY], rows: [AMOUNT],
    params: {start: 0, end: 0, limit: 0, subject: '', maxGroups: 25, splitMulti: true}}), COLUMNS);
  assert.strictEqual(config.maxGroups, 25);
  assert.strictEqual(config.splitMulti, true);

  const blank = core.compileConfig(sheet({columns: [CATEGORY], rows: [AMOUNT],
    params: {maxGroups: '', splitMulti: false}}), COLUMNS);
  assert.strictEqual(core.STUDIO_GROUP_LIMIT, 60);
  assert.strictEqual(blank.maxGroups, 60, 'blank compiles to the Studio default, stated explicitly');
  assert.strictEqual(blank.splitMulti, false);
  assert.strictEqual(core.compileConfig(sheet({columns: [CATEGORY], rows: [AMOUNT],
    params: {maxGroups: 0}}), COLUMNS).maxGroups, 60, 'zero means the same');

  const ungrouped = core.compileReport(sheet({rows: [AMOUNT], params: {splitMulti: true}}), COLUMNS);
  assert.strictEqual(ungrouped.config.x, -1);
  assert.strictEqual(ungrouped.config.series, -1);
  assert.match(ungrouped.notes.join(' '), /Splitting multi-value cells applies to the grouping field/);
  assert.match(ungrouped.issues.join(' '), /coverage-only/, 'money splitting is refused even without grouping');

  const grouped = core.compileReport(sheet({columns: [CATEGORY], rows: [AMOUNT], params: {splitMulti: true}}), COLUMNS);
  assert.ok(!grouped.notes.some(n => /Splitting multi-value cells/.test(n)), 'a view with a grouping field is not warned');
});

test('a new sheet starts with no group limit and splitting off', () => {
  assert.strictEqual(core.createSheet('s').params.maxGroups, 0);
  assert.strictEqual(core.createSheet('s').params.splitMulti, false);
});

test('all shelf dimensions and Detail dimensions change the grouping grain', () => {
  const report=core.compileReport(sheet({columns:[CATEGORY],rows:[AMOUNT,TIER]}),COLUMNS);
  assert.deepStrictEqual(report.issues,[]);
  assert.deepStrictEqual(report.config.dimensions,[CATEGORY,TIER]);
  const detail=core.compileReport(sheet({columns:[CATEGORY],rows:[AMOUNT],marks:marks({detail:[TIER]})}),COLUMNS);
  assert.deepStrictEqual(detail.issues,[]);
  assert.deepStrictEqual(detail.config.dimensions,[CATEGORY,TIER]);
  const diverse={...DATA,rows:DATA.rows.map((row,i)=>i===2?row.map((value,j)=>j===TIER?'Employees':value):row)};
  const result=math.build(diverse,detail.config);
  assert.ok(result.groups.length>math.build(diverse,core.compileConfig(sheet({columns:[CATEGORY],rows:[AMOUNT]}),COLUMNS)).groups.length);
  assert.strictEqual(core.grandTotal(result,detail.config),7500);
  const alone=core.compileReport(sheet({rows:[AMOUNT],marks:marks({detail:[TIER]})}),COLUMNS);
  assert.strictEqual(alone.config.x,TIER);
  assert.deepStrictEqual(alone.config.dimensions,[TIER]);
});

test('unsupported encodings and duplicate measure pills cannot silently do nothing', () => {
  for(const channel of ['size','label','tooltip']){
    const report=core.compileReport(sheet({columns:[CATEGORY],rows:[AMOUNT],marks:marks({[channel]:channel==='tooltip'?[TIER]:TIER})}),COLUMNS);
    assert.match(report.issues.join(' '),/is not available for worksheet data/);
  }
  const repeated=core.compileReport(sheet({columns:[CATEGORY],rows:[AMOUNT,{column:AMOUNT,aggregation:'mean'}]}),COLUMNS);
  assert.match(repeated.issues.join(' '),/show one measure/);
  const scatter=core.compileReport(sheet({columns:[COUNT],rows:[AMOUNT],marks:marks({detail:[CATEGORY]})}),COLUMNS);
  assert.match(scatter.issues.join(' '),/Grouping needs Verified contributions/);
});

test('numeric ZIP variants and congressional district identifiers never become money measures', () => {
  const names=['ZIP','ZIPs','ZIP5','ZIP9','zipcode','Postal Code','Congressional District','Candidate ID(s)'];
  const fields=core.classifyFields(names.map((name,index)=>({name,index,type:'number'})));
  assert.deepStrictEqual(fields.measures,[]);
  assert.ok(fields.fields.every(field=>field.role==='dimension'));
});

test('split coverage has no additive grand total or monetary status label', () => {
  const config=wide({x:ZIPS,y:-1,aggregation:'count',splitMulti:true});
  const result=math.build(WIDE,config);
  assert.strictEqual(core.grandTotal(result,config),null);
  assert.match(core.totalNote(result,config),/coverage groups can overlap/);
  assert.strictEqual(core.rowsToMarksSummary(result,config,WIDE_COLUMNS).measureLabel,'Coverage CNT(rows)');
});

test('percentages and period differences have explicit units and no monetary grand total', () => {
  const d={columns:[{name:'Year',type:'category'},{name:'Amount',type:'number'}],rows:[[2022,100],[2023,200],[2024,400]],row_numbers:[2,3,4]};
  for(const transform of ['yoy','change']){
    const config={type:'line',x:0,y:1,aggregation:'sum',transform,period:'year'};
    const result=math.build(d,config);
    assert.strictEqual(core.grandTotal(result,config),null);
    assert.match(core.totalNote(result,config),/percentages or period changes/);
    assert.match(core.rowsToMarksSummary(result,config,d.columns).measureLabel,transform==='yoy'?/YoY %/:/Period change/);
    if(transform==='yoy')assert.strictEqual(result.units,'percent');
  }
});

test('forecast totals separate historical money from copied future baselines', () => {
  const d={columns:[{name:'Year',type:'category'},{name:'Amount',type:'number'}],rows:Array.from({length:8},(_,i)=>[2016+i,(i+1)*100]),row_numbers:[2,3,4,5,6,7,8,9]};
  const config={type:'line',x:0,y:1,aggregation:'sum',transform:'forecast',period:'year',horizon:2,as_of:'2025-01-01'};
  const result=math.build(d,config);
  assert.strictEqual(result.observedTotal,3600);
  assert.strictEqual(result.forecastTotal,1100);
  assert.strictEqual(core.grandTotal(result,config),3600);
  const summary=core.rowsToMarksSummary(result,config,d.columns);
  assert.strictEqual(summary.measureLabel,'Observed SUM(Amount)');
  assert.strictEqual(summary.total,3600);
});

test('independent accounting groups have separate marks but no cross-layer total', () => {
  const result={type:'bar',groups:[{label:'receipt',value:100},{label:'attribution',value:100}],totalRefusal:'Grand total is not shown: the displayed accounting groups can overlap.'};
  assert.strictEqual(core.grandTotal(result,{aggregation:'sum'}),null);
});


/* =================================================== redesign 2026-09-13 === */

const contributions = require('../chart-studio-contributions.js');

// A stand-in for the verified catalog: the ids the studio actually looks up.
const VERIFIED = [
  {index: 0, id: 'company', name: 'Company', type: 'category', role: 'dimension', visible: true},
  {index: 1, id: 'cycle', name: 'Election cycle', type: 'category', role: 'dimension', is_time: true, visible: true},
  {index: 2, id: 'year', name: 'Contribution year', type: 'category', role: 'dimension', is_time: true, visible: true},
  {index: 3, id: 'quarter', name: 'Contribution quarter', type: 'category', role: 'dimension', is_time: true, visible: true},
  {index: 4, id: 'recipient', name: 'Recipient committee', type: 'category', role: 'dimension', visible: true},
  {index: 5, id: 'recipient_category', name: 'Recipient category', type: 'category', role: 'dimension', visible: true},
  {index: 6, id: 'party', name: 'Recipient party', type: 'category', role: 'dimension', visible: true},
  {index: 7, id: 'amount', name: 'Selected amount', type: 'number', role: 'measure', unit: 'cents', visible: true},
  {index: 8, id: 'records', name: 'Observation count', type: 'number', role: 'measure', unit: 'count', visible: true},
  {index: 9, id: 'contributors', name: 'Distinct reported donor identities', type: 'number', role: 'measure', unit: 'count', visible: true}
];

function selectedRows(filters) {
  const state = sheet({columns: [{column: CATEGORY, aggregation: 'sum'}],
    rows: [{column: AMOUNT, aggregation: 'sum'}], filters: filters});
  const report = core.compileReport(state, COLUMNS);
  assert.deepStrictEqual(report.issues, []);
  return math.build(DATA, report.config).selected;
}

/* ------------------------------------------------------------- filters */

test('an empty member choice is not a filter, so it never selects nothing', () => {
  assert.strictEqual(core.filterActive({column: CATEGORY, op: 'in', value: []}), false);
  assert.strictEqual(core.filterActive({column: CATEGORY, op: 'in', value: ['Company PAC']}), true);
  assert.strictEqual(core.filterActive({column: AMOUNT, op: 'between', value: ['', '']}), false);
  assert.strictEqual(core.filterActive({column: AMOUNT, op: 'between', value: ['1000', '']}), true);
  assert.strictEqual(selectedRows([{column: CATEGORY, op: 'in', value: []}]), ROWS.length);
});

test('include and exclude lists select complementary worksheet rows', () => {
  assert.strictEqual(selectedRows([{column: CATEGORY, op: 'in', value: ['Company PAC']}]), 3);
  assert.strictEqual(selectedRows([{column: CATEGORY, op: 'notin', value: ['Company PAC']}]), 3);
  assert.strictEqual(selectedRows([{column: CATEGORY, op: 'in', value: ['Company PAC', 'Trade Association']}]), 5);
});

test('a range filter applies each bound it was given', () => {
  assert.strictEqual(selectedRows([{column: AMOUNT, op: 'between', value: ['500', '2000']}]), 4);
  assert.strictEqual(selectedRows([{column: AMOUNT, op: 'between', value: ['1000', '']}]), 3);
  assert.strictEqual(selectedRows([{column: AMOUNT, op: 'between', value: ['', '750']}]), 3);
});

test('normalizeFilter keeps lists as arrays, ranges two-ended and scalars as text', () => {
  assert.deepStrictEqual(core.normalizeFilter({column: '1', op: 'in', value: ['a', 'b']}),
    {column: 1, op: 'in', value: ['a', 'b']});
  assert.deepStrictEqual(core.normalizeFilter({column: 2, op: 'between', value: ['5']}),
    {column: 2, op: 'between', value: ['5', '']});
  assert.deepStrictEqual(core.normalizeFilter({column: 2, op: 'nonsense', value: 7}),
    {column: 2, op: 'equals', value: '7'});
  assert.deepStrictEqual(core.normalizeFilter({column: 0, op: 'equals', value: 'x', stage: 'rows'}),
    {column: 0, op: 'equals', value: 'x', stage: 'rows'});
});

test('filterSummary reads as a sentence about the members, not about the operator', () => {
  const company = {name: 'Company'};
  assert.strictEqual(core.filterSummary({op: 'in', value: []}, company), 'Company: any value');
  assert.strictEqual(core.filterSummary({op: 'in', value: ['Acme']}, company), 'Company: Acme');
  assert.strictEqual(core.filterSummary({op: 'in', value: ['a', 'b', 'c', 'd']}, company, 10), 'Company: 4 of 10 values');
  assert.strictEqual(core.filterSummary({op: 'notin', value: ['a', 'b', 'c', 'd']}, company, 10), 'Company excludes 4 of 10 values');
  const amount = core.filterSummary({op: 'between', value: ['1000', '']}, {name: 'Selected amount', unit: 'cents'});
  assert.ok(amount.startsWith('Selected amount'));
  assert.ok(amount.includes('1,000'), amount);
  assert.strictEqual(core.filterSummary({op: 'contains', value: 'PAC'}, {name: 'Recipient'}), 'Recipient contains PAC');
});

test('one filter pill becomes the clauses the verified engine understands', () => {
  const company = VERIFIED[0], amount = VERIFIED[7];
  assert.deepStrictEqual(contributions.clauses({column: 0, op: 'in', value: ['A', 'B']}, company),
    [{field: 'company', op: 'in', value: ['A', 'B']}]);
  // The server has no NOT IN, and filters are ANDed, so exclusion is a chain.
  assert.deepStrictEqual(contributions.clauses({column: 0, op: 'notin', value: ['A', 'B']}, company),
    [{field: 'company', op: 'ne', value: 'A'}, {field: 'company', op: 'ne', value: 'B'}]);
  assert.deepStrictEqual(contributions.clauses({column: 0, op: 'in', value: []}, company), []);
  assert.deepStrictEqual(contributions.clauses({column: 0, op: 'equals', value: ''}, company), []);
  assert.deepStrictEqual(contributions.clauses({column: 7, op: 'between', value: ['10', '20']}, amount),
    [{field: 'amount', op: 'gte', value: 1000}, {field: 'amount', op: 'lte', value: 2000}]);
});

/* -------------------------------------------------- measures and presets */

test('aggregation menus offer only what the active engine can compute', () => {
  const worksheet = core.classifyFields(COLUMNS);
  const verified = core.classifyFields(VERIFIED);
  const ids = list => list.map(a => a[0]);
  assert.deepStrictEqual(ids(core.aggregationsFor(core.fieldAt(worksheet, AMOUNT), 'worksheet')), core.AGGREGATION_IDS);
  assert.deepStrictEqual(core.aggregationsFor(core.fieldAt(worksheet, CYCLE), 'worksheet'), []);
  assert.deepStrictEqual(ids(core.aggregationsFor(core.fieldAt(verified, 7), 'verified')), core.AGGREGATION_IDS);
  // Every other verified measure is a source aggregate with one definition.
  assert.deepStrictEqual(core.aggregationsFor(core.fieldAt(verified, 8), 'verified'), []);
});

test('political-money presets say what a source cannot answer instead of failing later', () => {
  const verified = core.measurePresets(VERIFIED, 'verified');
  assert.deepStrictEqual(verified.map(p => p.available), [true, true, true, true]);
  assert.deepStrictEqual(verified.map(p => p.column), [7, 8, 7, 9]);
  assert.strictEqual(verified.find(p => p.id === 'average-gift').aggregation, 'mean');
  const worksheet = core.measurePresets(COLUMNS, 'worksheet');
  const distinct = worksheet.find(p => p.id === 'distinct-contributors');
  assert.strictEqual(distinct.available, false);
  assert.match(distinct.reason, /Verified contributions/);
  assert.strictEqual(core.measurePresets([], 'worksheet').every(p => !p.available), true);
});

test('a measure preset replaces the measure on the shelf that carried it', () => {
  const onRows = core.applyMeasurePreset('gift-count', sheet({
    columns: [{column: 0, aggregation: 'sum'}], rows: [{column: 7, aggregation: 'sum'}]}), VERIFIED, 'verified');
  assert.deepStrictEqual(onRows.rows, [{column: 8, aggregation: 'sum'}]);
  assert.deepStrictEqual(onRows.columns, [{column: 0, aggregation: 'sum'}]);
  const onColumns = core.applyMeasurePreset('average-gift', sheet({
    columns: [{column: 7, aggregation: 'sum'}], rows: [{column: 0, aggregation: 'sum'}]}), VERIFIED, 'verified');
  assert.deepStrictEqual(onColumns.columns, [{column: 7, aggregation: 'mean'}]);
  const refused = sheet({rows: [{column: AMOUNT, aggregation: 'sum'}]});
  assert.deepStrictEqual(core.applyMeasurePreset('distinct-contributors', refused, COLUMNS, 'worksheet').rows,
    [{column: AMOUNT, aggregation: 'sum'}]);
});

/* ------------------------------------------------------------ data types */

test('a text column can never become a measure; a numeric identifier can', () => {
  const meta = core.classifyFields(COLUMNS);
  const text = core.fieldAt(meta, CATEGORY);
  const refusal = core.canTreatAs(text, 'measure');
  assert.strictEqual(refusal.ok, false);
  assert.match(refusal.reason, /text/);
  assert.strictEqual(core.canTreatAs(text, 'dimension').ok, false); // already one
  const zip = core.classifyFields([{index: 0, name: 'ZIP Code', type: 'number', distinct: 9, missing: 0}]).fields[0];
  assert.strictEqual(zip.role, 'dimension');
  assert.strictEqual(core.canTreatAs(zip, 'measure').ok, true);
});

test('a per-sheet type override moves a field between the two lists and its glyph', () => {
  const plain = core.classifyFields(COLUMNS);
  assert.strictEqual(core.fieldAt(plain, COUNT).role, 'measure');
  const coerced = core.classifyFields(COLUMNS, {[String(COUNT)]: {role: 'dimension'}});
  assert.strictEqual(core.fieldAt(coerced, COUNT).role, 'dimension');
  assert.strictEqual(core.fieldAt(coerced, COUNT).glyph, 'Abc');
  assert.ok(coerced.dimensions.some(f => f.index === COUNT));
  assert.ok(!coerced.measures.some(f => f.index === COUNT));
  // A refused override changes nothing at all.
  const refused = core.classifyFields(COLUMNS, {[String(CATEGORY)]: {role: 'measure'}});
  assert.strictEqual(core.fieldAt(refused, CATEGORY).role, 'dimension');
  // The override travels into the compiler, so the view follows the reader.
  const state = sheet({columns: [{column: CYCLE, aggregation: 'sum'}], rows: [{column: COUNT, aggregation: 'sum'}],
    types: {[String(COUNT)]: {role: 'dimension'}}});
  const report = core.compileReport(state, COLUMNS);
  assert.ok(report.config.dimensions.includes(COUNT));
});

test('date parts use real catalog columns when verified and periods on a worksheet', () => {
  const verified = core.classifyFields(VERIFIED);
  const parts = core.datePartsFor(core.fieldAt(verified, 1), VERIFIED, 'verified');
  // The whole hierarchy this source has, with the pill's own part marked.
  assert.deepStrictEqual(parts.map(p => p.id), ['cycle', 'year', 'quarter']);
  assert.deepStrictEqual(parts.map(p => p.column), [1, 2, 3]);
  assert.deepStrictEqual(parts.map(p => p.current), [true, false, false]);
  const worksheet = core.classifyFields(COLUMNS);
  const date = worksheet.fields.find(f => f.isTime);
  assert.deepStrictEqual(core.datePartsFor(date, COLUMNS, 'worksheet').map(p => p.id), ['cycle', 'year']);
  assert.deepStrictEqual(core.datePartsFor(core.fieldAt(worksheet, CATEGORY), COLUMNS, 'worksheet'), []);
  // A worksheet marks the period the existing transform already groups by.
  const grouped = sheet({analytics: {transform: 'annual', period: 'year'}});
  assert.deepStrictEqual(core.datePartsFor(date, COLUMNS, 'worksheet', grouped).map(p => p.current), [false, true]);
});

test('a verified date field keeps its date parts even without the detected time flag', () => {
  // The catalog's date hierarchy is the authority; the flag is only a fallback,
  // so losing it anywhere between the catalog and the pill cannot hide the menu.
  const stripped = VERIFIED.map(field => {
    const copy = Object.assign({}, field);
    delete copy.is_time;
    return copy;
  });
  const meta = core.classifyFields(stripped);
  for (const id of ['cycle', 'year', 'quarter']) {
    const field = meta.fields.find(f => f.id === id);
    assert.strictEqual(core.isDateLike(field), true, id + ' should be date-like');
    assert.ok(core.datePartsFor(field, stripped, 'verified').length >= 3, id + ' should offer parts');
  }
  // A plain dimension is still not date-like, flag or no flag.
  assert.strictEqual(core.isDateLike(meta.fields.find(f => f.id === 'company')), false);
  assert.deepStrictEqual(core.datePartsFor(meta.fields.find(f => f.id === 'company'), stripped, 'verified'), []);
  // Neither is a measure that happens to be named like a date.
  assert.strictEqual(core.isDateLike({id: 'date', role: 'measure', isTime: true}), false);
});

/* ------------------------------------------------------ company overview */

test('each company-overview preset builds the sheet its caption promises', () => {
  const presets = core.companyOverviewPresets();
  assert.deepStrictEqual(presets.map(p => p.id),
    ['recipient-categories', 'giving-by-cycle', 'top-recipients', 'party-split']);
  const cards = presets.map(p => core.companyOverviewSheet(p, VERIFIED, {company: 'Acme', cycle: '2025-2026'}));
  assert.deepStrictEqual(cards.map(c => c.marks.type), ['bar', 'line', 'bar', 'doughnut']);
  assert.deepStrictEqual(cards.map(c => c.params.maxGroups), [10, 40, 8, 10]);
  assert.deepStrictEqual(cards[0].columns, [{column: 5, aggregation: 'sum'}]);
  assert.deepStrictEqual(cards[0].rows, [{column: 7, aggregation: 'sum'}]);
  assert.deepStrictEqual(cards[2].columns, [{column: 4, aggregation: 'sum'}]);
  for (const card of cards) {
    assert.strictEqual(card.analytics.transform, 'none');
    assert.deepStrictEqual(card.filters.map(f => f.value), ['Acme', '2025-2026']);
  }
  // No company and no cycle chosen means no scope filters, never a blank one.
  assert.deepStrictEqual(core.companyOverviewSheet(presets[0], VERIFIED, {}).filters, []);
});

test('a company-overview preset compiles into the verified query it describes', () => {
  const preset = core.companyOverviewPresets()[0];
  const card = core.companyOverviewSheet(preset, VERIFIED, {company: 'Acme', cycle: '2025-2026'});
  const compiled = contributions.compile(card, VERIFIED, {dataset: 'Banking', basis: 'receipt'});
  assert.deepStrictEqual(compiled.query.dimensions, ['recipient_category']);
  assert.deepStrictEqual(compiled.query.measures, ['amount']);
  assert.deepStrictEqual(compiled.query.filters,
    [{field: 'company', op: 'eq', value: 'Acme'}, {field: 'cycle', op: 'eq', value: '2025-2026'}]);
  assert.deepStrictEqual(compiled.query.sort, [{field: 'amount', direction: 'desc'}]);
  assert.strictEqual(compiled.query.limit, 10);
  assert.strictEqual(compiled.spec.type, 'bar');
  const cycles = contributions.compile(core.companyOverviewSheet(core.companyOverviewPresets()[1], VERIFIED,
    {company: 'Acme'}), VERIFIED, {dataset: 'Banking', basis: 'receipt'});
  assert.deepStrictEqual(cycles.query.dimensions, ['cycle']);
  assert.deepStrictEqual(cycles.query.sort, [{field: 'cycle', direction: 'asc'}]);
});

test('a single click sends a grouping across the top and a measure down the side', () => {
  const meta = core.classifyFields(COLUMNS);
  const dimension = core.fieldAt(meta, CATEGORY), measure = core.fieldAt(meta, AMOUNT);
  const empty = sheet({});
  assert.strictEqual(core.quickAddZone(dimension, empty), 'columns');
  assert.strictEqual(core.quickAddZone(measure, empty), 'rows');
  const taken = sheet({columns: [{column: CYCLE, aggregation: 'sum'}],
    rows: [{column: AMOUNT, aggregation: 'sum'}]});
  assert.strictEqual(core.quickAddZone(dimension, taken), 'rows');
  assert.strictEqual(core.quickAddZone(measure, taken), 'columns');
});

test('the click zone reads the shelves only, never a field selection', () => {
  const meta = core.classifyFields(COLUMNS);
  const dimension = core.fieldAt(meta, CATEGORY);
  // Marks channels are not shelves: a coloured view still sends the next
  // grouping to the empty Columns shelf.
  const coloured = sheet({marks: marks({color: {column: TIER, aggregation: 'sum'}})});
  assert.strictEqual(core.quickAddZone(dimension, coloured), 'columns');
  assert.strictEqual(core.quickAddZone(null, sheet({})), 'columns');
  assert.strictEqual(core.quickAddZone(dimension, {}), 'columns');
});

test('a cycle carried from Graph is translated into the spelling the index stores', () => {
  // graph.js option values are the end year; contribution_data.py stores the pair.
  assert.strictEqual(core.carriedFilterValue('cycle', '2024'), '2023-2024');
  assert.strictEqual(core.carriedFilterValue('cycle', 2026), '2025-2026');
  assert.strictEqual(core.carriedFilterValue('cycle', '2023-2024'), '2023-2024');
  assert.strictEqual(core.carriedFilterValue('cycle', ''), '');
  assert.strictEqual(core.carriedFilterValue('company', '2024'), '2024');
});

test('the reverse map gives Graph the end year, and refuses anything that is not a cycle', () => {
  assert.strictEqual(core.graphCycleValue('2023-2024'), '2024');
  assert.strictEqual(core.graphCycleValue('2024'), '2024');
  assert.strictEqual(core.graphCycleValue('2020-2024'), '');
  assert.strictEqual(core.graphCycleValue(''), '');
  assert.strictEqual(core.graphCycleValue(null), '');
});

test('company overview names the fields a source does not have', () => {
  const preset = core.companyOverviewPresets()[0];
  assert.deepStrictEqual(core.companyOverviewMissing(preset, COLUMNS), ['recipient_category', 'amount']);
  assert.deepStrictEqual(core.companyOverviewMissing(preset, VERIFIED), []);
});



/* ---- report-workbook guards: the Overview book is polymorphic ------------ */

// A cycle sheet as the published Overview writes it: one Fact Type column
// stacking three partitions of the SAME money. Summing the sheet whole is 3x.
const FACT_COLUMNS = [
  {index: 0, name: 'Fact Type', type: 'category'},
  {index: 1, name: 'Recipient', type: 'category'},
  {index: 2, name: 'Amount', type: 'number'}
];
const FACT_ROWS = [
  ['Recipient', 'Alpha PAC', 70], ['Recipient', 'Beta PAC', 30],
  ['Employee', 'Alpha PAC', 55], ['Employee', 'Beta PAC', 25],
  ['Master', 'Alpha PAC', 70], ['Master', 'Beta PAC', 30]
];
const FACT_DATA = {sheet: '2025-2026', header_row: 1, columns: FACT_COLUMNS, rows: FACT_ROWS,
  row_numbers: [2, 3, 4, 5, 6, 7], row_count: FACT_ROWS.length, sha256: 'fact'};

const VIEW_COLUMNS = [
  {index: 0, name: 'View', type: 'category'},
  {index: 1, name: 'Recipient', type: 'category'},
  {index: 2, name: 'Total Giving', type: 'number'}
];
const VIEW_ROWS = [['Industry', 'Alpha PAC', 70], ['Industry', 'Beta PAC', 30],
  ['Company', 'Alpha PAC', 70], ['Company', 'Beta PAC', 30]];

const valuesOf = (columns, rows) => index => [...new Set(rows.map(row => String(row[index])))];

test('a Fact Type column earns a Recipient guard, whatever its spacing or case', () => {
  const guards = core.defaultGuards(FACT_COLUMNS, valuesOf(FACT_COLUMNS, FACT_ROWS));
  assert.strictEqual(guards.length, 1);
  assert.strictEqual(guards[0].column, 0);
  assert.strictEqual(guards[0].value, 'Recipient');
  assert.match(guards[0].note, /^Cycle sheets stack three fact partitions \(Recipient, Employee, Master\) of the same money\./);
  const spaced = core.defaultGuards([{index: 4, name: '  fact type '}], {4: [' RECIPIENT ']});
  assert.strictEqual(spaced.length, 1);
  assert.strictEqual(spaced[0].column, 4, 'the guard names the column index the filter pill uses');
});

test('a Fact Type column that never holds Recipient earns no pill either', () => {
  // The three partitions are what the guard is for. A column of that name
  // holding something else would be filtered down to nothing, so it is left
  // alone - the same rule the View guard follows.
  assert.deepStrictEqual(core.defaultGuards(FACT_COLUMNS, {0: ['Employee', 'Master']}), []);
  assert.deepStrictEqual(core.defaultGuards(FACT_COLUMNS, {}), [],
    'no values read means no guard, on either column');
  assert.deepStrictEqual(core.defaultGuards(FACT_COLUMNS, () => []), []);
});

test('no Fact Type column means no pill', () => {
  assert.deepStrictEqual(core.defaultGuards(COLUMNS, {}), []);
  assert.deepStrictEqual(core.defaultGuards([{index: 0, name: 'Fact Types'}], {}), []);
  assert.deepStrictEqual(core.defaultGuards([], {}), []);
  assert.deepStrictEqual(core.defaultGuards(null, null), []);
});

test('a View column earns a guard only when the sheet actually holds an Industry view', () => {
  const guards = core.defaultGuards(VIEW_COLUMNS, valuesOf(VIEW_COLUMNS, VIEW_ROWS));
  assert.strictEqual(guards.length, 1);
  assert.strictEqual(guards[0].value, 'Industry');
  assert.match(guards[0].note, /^This sheet repeats every recipient under an Industry view and a Company view\./);
  // Negative control: the same column name over values that are not views.
  const other = [['Company', 'Alpha PAC', 70], ['Company', 'Beta PAC', 30]];
  assert.deepStrictEqual(core.defaultGuards(VIEW_COLUMNS, valuesOf(VIEW_COLUMNS, other)), []);
  assert.deepStrictEqual(core.defaultGuards(VIEW_COLUMNS, {}), [], 'no values read means no View guard');
});

test('a sheet carrying both columns is guarded twice, in column order', () => {
  const columns = [{index: 0, name: 'Fact Type'}, {index: 1, name: 'View'}];
  const guards = core.defaultGuards(columns, index => index === 0 ? ['Recipient'] : ['Industry']);
  assert.deepStrictEqual(guards.map(g => [g.column, g.value]), [[0, 'Recipient'], [1, 'Industry']]);
});

const factSheet = filters => sheet({columns: [{column: 1, aggregation: 'sum'}],
  rows: [{column: 2, aggregation: 'sum'}], filters: filters || []});

test('the Recipient guard is what makes a cycle sheet sum to the report total', () => {
  const bare = core.compileConfig(factSheet(), FACT_COLUMNS);
  const whole = math.build(FACT_DATA, bare);
  assert.strictEqual(core.grandTotal(whole, bare), 280, 'the unguarded sheet stacks three partitions');
  const guard = core.defaultGuards(FACT_COLUMNS, valuesOf(FACT_COLUMNS, FACT_ROWS))[0];
  const config = core.compileConfig(factSheet([{column: guard.column, op: 'equals', value: guard.value}]), FACT_COLUMNS);
  assert.strictEqual(core.grandTotal(math.build(FACT_DATA, config), config), 100, 'one partition is the report total');
});

test('the guard pill reads as the plain equality a reader can remove', () => {
  const guard = core.defaultGuards(FACT_COLUMNS, valuesOf(FACT_COLUMNS, FACT_ROWS))[0];
  const field = core.fieldAt(core.classifyFields(FACT_COLUMNS), guard.column);
  assert.strictEqual(core.filterSummary({column: guard.column, op: 'equals', value: guard.value}, field, 3),
    'Fact Type = Recipient');
});

test('the four committee-activity sheets carry a caption, and no other sheet does', () => {
  const note = core.committeeActivitySheet('Downstream Activity');
  assert.match(note, /^This sheet reports recipient committees\u2019 own activity, not the industry\u2019s giving\./);
  assert.match(note, /do not reconcile to the report\u2019s Total Giving\.$/);
  for (const name of ['Downstream Activity', 'Beneficiary Summary', 'Beneficiary Bridge', 'Transfer Paths',
    'transfer paths', '  BENEFICIARY BRIDGE  '])
    assert.strictEqual(core.committeeActivitySheet(name), note, name + ' must carry the caption');
  for (const name of ['Recipient Detail', 'Recipient List', '2025-2026', 'Candidate Funding', '', null, undefined])
    assert.strictEqual(core.committeeActivitySheet(name), null, String(name) + ' must not carry the caption');
});

test('a committee-activity caption suppresses the grand total through the engine refusal', () => {
  const config = core.compileConfig(factSheet(), FACT_COLUMNS);
  const result = math.build(FACT_DATA, config);
  assert.strictEqual(core.totalNote(result, config), '', 'nothing refuses this view on its own');
  result.totalRefusal = core.committeeActivitySheet('Transfer Paths');
  assert.strictEqual(core.totalNote(result, config), result.totalRefusal);
  assert.strictEqual(core.grandTotal(result, config), null);
  assert.strictEqual(core.rowsToMarksSummary(result, config, FACT_COLUMNS).total, null);
});

test('the catalog splits into the tall Data book and the Overview book', () => {
  const catalog = {reports: [
    {index: 11, name: 'Banking Industry Spending Overview.xlsx', industry: 'Banking', kind: 'overview'},
    {index: 22, name: 'Banking Industry Spending Data.xlsx', industry: 'Banking', kind: 'data'}
  ]};
  const groups = core.groupWorksheets(catalog);
  assert.deepStrictEqual(groups.data.map(r => r.index), [22]);
  assert.deepStrictEqual(groups.overview.map(r => r.index), [11]);
  assert.deepStrictEqual(core.groupWorksheets(catalog.reports), groups, 'the body or its rows, either way');
  assert.strictEqual(core.WORKSHEET_GROUP_LABELS.data, 'Data workbook (tall, chart-ready)');
  assert.strictEqual(core.WORKSHEET_GROUP_LABELS.overview, 'Overview workbook (report layout)');
});

test('a catalog of Overview books alone has an empty Data group', () => {
  const groups = core.groupWorksheets([
    {index: 1, name: 'Banking Industry Spending Overview.xlsx', kind: 'overview'},
    {index: 2, name: 'Credit Union Industry Spending Overview.xlsx', kind: 'overview'}
  ]);
  assert.deepStrictEqual(groups.data, []);
  assert.strictEqual(groups.overview.length, 2);
  assert.deepStrictEqual(core.groupWorksheets([]), {data: [], overview: []});
  assert.deepStrictEqual(core.groupWorksheets(null), {data: [], overview: []});
  assert.strictEqual(core.NO_DATA_WORKBOOK_HINT,
    'The chart-ready Data workbook has not been published for this industry yet.');
});

test('a server that sends no kind is read from the filename, the same rule at the other end', () => {
  assert.strictEqual(core.workbookKind({name: 'Banking Industry Spending Data.xlsx'}), 'data');
  assert.strictEqual(core.workbookKind({name: 'banking industry spending data.xlsx'}), 'data');
  assert.strictEqual(core.workbookKind({name: 'Banking Industry Spending Overview.xlsx'}), 'overview');
  assert.strictEqual(core.workbookKind({name: 'Industry Spending Data Appendix.xlsx'}), 'overview');
  assert.strictEqual(core.workbookKind({name: 'Fixture.xlsx'}), 'overview');
  // An explicit kind always wins over the filename.
  assert.strictEqual(core.workbookKind({name: 'Fixture.xlsx', kind: 'data'}), 'data');
  assert.strictEqual(core.workbookKind({name: 'Banking Industry Spending Data.xlsx', kind: 'overview'}), 'overview');
  assert.strictEqual(core.workbookKind(null), 'overview');
});

test('a board is 1, 2 or 4 tiles and nothing else', () => {
  const sheets = [{id: 's1'}, {id: 's2'}, {id: 's3'}, {id: 's4'}];
  assert.deepStrictEqual(core.normalizeBoard({sheets, board: {tiles: 1, slots: [0]}}), {tiles: 1, slots: [0]});
  assert.deepStrictEqual(core.normalizeBoard({sheets, board: {tiles: 2, slots: [0, 1]}}), {tiles: 2, slots: [0, 1]});
  assert.deepStrictEqual(core.normalizeBoard({sheets, board: {tiles: 4, slots: [0, 1, 2, 3]}}),
    {tiles: 4, slots: [0, 1, 2, 3]});
  for (const tiles of [0, 3, 5, 8, -1, 2.5, '2', null, true]) {
    assert.strictEqual(core.normalizeBoard({sheets, board: {tiles, slots: [0, 1]}}), null, 'tiles ' + tiles);
  }
});

test('a board has exactly one slot per tile', () => {
  const sheets = [{id: 's1'}, {id: 's2'}, {id: 's3'}];
  assert.strictEqual(core.normalizeBoard({sheets, board: {tiles: 2, slots: [0]}}), null);
  assert.strictEqual(core.normalizeBoard({sheets, board: {tiles: 2, slots: [0, 1, 2]}}), null);
  assert.strictEqual(core.normalizeBoard({sheets, board: {tiles: 4, slots: [0, 1]}}), null);
  assert.strictEqual(core.normalizeBoard({sheets, board: {tiles: 2, slots: 'both'}}), null);
  assert.strictEqual(core.normalizeBoard({sheets, board: {tiles: 2}}), null);
});

test('an empty tile is null, and every filled slot names a sheet that exists', () => {
  const sheets = [{id: 's1'}, {id: 's2'}];
  assert.deepStrictEqual(core.normalizeBoard({sheets, board: {tiles: 2, slots: [null, 1]}}),
    {tiles: 2, slots: [null, 1]});
  assert.deepStrictEqual(core.normalizeBoard({sheets, board: {tiles: 4, slots: [null, null, null, null]}}),
    {tiles: 4, slots: [null, null, null, null]});
  assert.strictEqual(core.normalizeBoard({sheets, board: {tiles: 2, slots: [0, 2]}}), null);
  assert.strictEqual(core.normalizeBoard({sheets: [], board: {tiles: 2, slots: [0, null]}}), null);
  assert.strictEqual(core.normalizeBoard({board: {tiles: 2, slots: [0, null]}}), null);
});

test('no sheet sits in two tiles at once', () => {
  const sheets = [{id: 's1'}, {id: 's2'}, {id: 's3'}];
  assert.strictEqual(core.normalizeBoard({sheets, board: {tiles: 2, slots: [0, 0]}}), null);
  assert.strictEqual(core.normalizeBoard({sheets, board: {tiles: 4, slots: [2, 1, 2, null]}}), null);
  assert.deepStrictEqual(core.normalizeBoard({sheets, board: {tiles: 4, slots: [2, 1, null, null]}}),
    {tiles: 4, slots: [2, 1, null, null]});
});

test('a slot is a non-negative whole number or null, never anything else', () => {
  const sheets = [{id: 's1'}, {id: 's2'}];
  for (const slot of [-1, 0.5, '0', true, false, undefined, {}, [], NaN, Infinity]) {
    assert.strictEqual(core.normalizeBoard({sheets, board: {tiles: 2, slots: [slot, 1]}}), null,
      'slot ' + String(slot));
  }
});

test('a board must be an object, and a view without one simply has none', () => {
  const sheets = [{id: 's1'}, {id: 's2'}];
  for (const board of ['2', 2, true, [0, 1], []]) {
    assert.strictEqual(core.normalizeBoard({sheets, board}), null, 'board ' + JSON.stringify(board));
  }
  assert.strictEqual(core.normalizeBoard({sheets}), null);
  assert.strictEqual(core.normalizeBoard({sheets, board: null}), null);
  assert.strictEqual(core.normalizeBoard(null), null);
  assert.strictEqual(core.normalizeBoard(undefined), null);
});

test('normalizeBoard copies the slots out, so a caller cannot edit the view through them', () => {
  const view = {sheets: [{id: 's1'}, {id: 's2'}], board: {tiles: 2, slots: [0, 1]}};
  const board = core.normalizeBoard(view);
  board.slots[0] = null;
  assert.deepStrictEqual(view.board.slots, [0, 1]);
});
