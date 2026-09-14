/* Step 6: node:test coverage for every pure addition. */
'use strict';

const tests = `

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
  assert.strictEqual(selectedRows([{column: AMOUNT, op: 'between', value: ['500', '2000']}]), 3);
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
  assert.deepStrictEqual(parts.map(p => p.id), ['year', 'quarter']);
  assert.deepStrictEqual(parts.map(p => p.column), [2, 3]);
  const worksheet = core.classifyFields(COLUMNS);
  const date = worksheet.fields.find(f => f.isTime);
  assert.deepStrictEqual(core.datePartsFor(date, COLUMNS, 'worksheet').map(p => p.id), ['cycle', 'year']);
  assert.deepStrictEqual(core.datePartsFor(core.fieldAt(worksheet, CATEGORY), COLUMNS, 'worksheet'), []);
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

test('company overview names the fields a source does not have', () => {
  const preset = core.companyOverviewPresets()[0];
  assert.deepStrictEqual(core.companyOverviewMissing(preset, COLUMNS), ['recipient_category', 'amount']);
  assert.deepStrictEqual(core.companyOverviewMissing(preset, VERIFIED), []);
});
`;

module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat\\app',
  eol: 'crlf',
  files: [{
    path: 'tests/chart-studio-core.test.js',
    edits: [{
      find: `test('independent accounting groups have separate marks but no cross-layer total', () => {
  const result={type:'bar',groups:[{label:'receipt',value:100},{label:'attribution',value:100}],totalRefusal:'Grand total is not shown: the displayed accounting groups can overlap.'};
  assert.strictEqual(core.grandTotal(result,{aggregation:'sum'}),null);
});`,
      replace: `test('independent accounting groups have separate marks but no cross-layer total', () => {
  const result={type:'bar',groups:[{label:'receipt',value:100},{label:'attribution',value:100}],totalRefusal:'Grand total is not shown: the displayed accounting groups can overlap.'};
  assert.strictEqual(core.grandTotal(result,{aggregation:'sum'}),null);
});
` + tests
    }]
  }]
};
