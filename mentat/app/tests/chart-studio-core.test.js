/* Chart Studio compiler and Show Me table. Run: node --test mentat/app/tests */
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
  assert.strictEqual(meta.fields[CYCLE].glyph, 'cal');
  assert.strictEqual(meta.fields[CATEGORY].glyph, 'Abc');
  assert.strictEqual(meta.fields[AMOUNT].glyph, '#');
});

test('classification agrees with chart-math chartColumns on measures', () => {
  const engine = math.chartColumns(COLUMNS);
  const core_ = core.classifyFields(COLUMNS);
  assert.deepStrictEqual(engine.measures.map(c => c.index).sort(), core_.measures.map(f => f.index).sort());
});

/* --------------------------------------------------------- compileConfig */

test('first dimension on Columns becomes x and first measure on Rows becomes y', () => {
  const config = core.compileConfig(sheet({columns: [CATEGORY, TIER], rows: [AMOUNT, COUNT]}), COLUMNS);
  assert.strictEqual(config.x, CATEGORY);
  assert.strictEqual(config.y, AMOUNT);
  assert.strictEqual(config.type, 'bar');
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

test('an empty sheet compiles to no configuration and says why', () => {
  const report = core.compileReport(sheet({}), COLUMNS);
  assert.strictEqual(report.config, null);
  assert.match(report.issues.join(' '), /Drag a dimension/);
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

test('pill accepts a bare column index, a numeric string and a full pill', () => {
  assert.deepStrictEqual(core.pill(3), {column: 3, aggregation: 'sum'});
  assert.deepStrictEqual(core.pill('3'), {column: 3, aggregation: 'sum'});
  assert.deepStrictEqual(core.pill({column: 3, aggregation: 'median'}), {column: 3, aggregation: 'median'});
  assert.deepStrictEqual(core.pill({column: 3, aggregation: 'bogus'}), {column: 3, aggregation: 'sum'});
  assert.strictEqual(core.pill(null), null);
  assert.strictEqual(core.pill({}), null);
});
