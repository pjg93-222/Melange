/* What the Sort and Show-mark-labels controls claim, asserted without a browser.

   Owner: "Sort mark labels, sort ascending and descending don't do anything."
   The controls were wired; what they claimed was wrong. Three separate facts
   are pinned here, because each was a different way of being silently inert:

   1. sheet().sort opens at 'none' and this path reads anything but 'asc' as
      descending, so from the opening state "Sort descending" produced a
      byte-identical query. 'none' MEANS descending; effectiveSort() says so
      once, for the compile and the toolbar alike.
   2. The toolbar used to decide "locked" from the CLASSIC compile, which does
      not know combination, dual-line or histogram - so on those three the
      buttons stayed enabled and changed nothing. sortLock() is the one answer.
   3. spec.labels is honoured by some renderers and silently ignored by the
      rest. LABEL_SUPPORT names every producible mark and, where it is not
      supported, the true reason the button shows.

   Run with the glob form; Node 24 rejects a bare directory:
     node --test "app/tests/**"/"*.test.js"      (cwd: mentat/) */
const test = require('node:test');
const assert = require('node:assert/strict');
const studio = require('../chart-studio-contributions.js');
const core = require('../chart-studio-core.js');

const catalog = [
  ...['company', 'cycle', 'date', 'year', 'zip5', 'state', 'recipient']
    .map(id => ({id, label: id, role: 'dimension'})),
  ...['amount', 'records', 'contributors', 'average_amount', 'gross_amount']
    .map(id => ({id, label: id, role: 'measure',
      unit: id === 'records' || id === 'contributors' ? 'count' : 'cents'}))];
const columns = studio.fields(catalog);
const index = id => columns.find(f => f.id === id).index;
const pill = (id, aggregation = 'sum') => ({column: index(id), aggregation});

function sheet() {
  const s = core.createSheet('A');
  s.columns = [pill('company')];
  s.rows = [pill('amount')];
  s.marks.type = 'bar';
  return s;
}
const compile = s => studio.compile(s, columns, {dataset: 'Banking', basis: 'receipt'});

/* ------------------------------------------------------------------- sort */

test('[studio-sort] a stored sort of none means descending, and only asc means ascending', () => {
  assert.equal(core.createSheet('A').sort, 'none', 'a new sheet opens at none');
  for (const stored of ['none', 'desc', '', null, undefined, 'nonsense'])
    assert.equal(studio.effectiveSort({sort: stored}), 'desc',
      JSON.stringify(stored) + ' is descending');
  assert.equal(studio.effectiveSort({sort: 'asc'}), 'asc');
  assert.equal(studio.effectiveSort({}), 'desc', 'a sheet with no sort at all');
  assert.equal(studio.effectiveSort(null), 'desc', 'and no sheet at all');
});

test('[studio-sort] sortLock names the views that refuse to be reordered, and why', () => {
  for (const type of ['line', 'area', 'combination', 'dual-line'])
    assert.equal(studio.sortLock(type, {}), studio.SORT_LOCK_TIME, type + ' is a time view');
  assert.equal(studio.sortLock('histogram', {}), studio.SORT_LOCK_BINS);
  for (const type of ['bar', 'scatter', 'table', 'stacked', 'heatmap', 'treemap', 'box'])
    assert.equal(studio.sortLock(type, {}), '', type + ' sorts');
  // compile() forces type to 'line' for any transform before it picks the
  // order, so a transform view IS chronological on this path whatever mark the
  // reader chose. sortLock says so from the mark the toolbar still sees.
  for (const transform of ['annual', 'yoy', 'change', 'forecast'])
    assert.equal(studio.sortLock('bar', {analytics: {transform}}), studio.SORT_LOCK_TIME,
      transform + ' is chronological');
  assert.equal(studio.sortLock('bar', {analytics: {transform: 'none'}}), '');
  assert.equal(studio.sortLock('bar', {analytics: {}}), '', 'no transform recorded is no transform');
});

test('[studio-sort] a bar orders by the first measure: none and desc descend, asc ascends', () => {
  for (const stored of ['none', 'desc', undefined]) {
    const s = sheet(); s.sort = stored;
    assert.deepEqual(compile(s).query.sort, [{field: 'amount', direction: 'desc'}],
      JSON.stringify(stored) + ' must produce the descending query');
  }
  const ascending = sheet(); ascending.sort = 'asc';
  assert.deepEqual(compile(ascending).query.sort, [{field: 'amount', direction: 'asc'}]);
  // measures[0] only - the second measure is not a tie-break, and the button
  // titles say which measure the order is by for exactly this reason.
  const two = sheet(); two.rows = [pill('contributors'), pill('amount')];
  assert.deepEqual(compile(two).query.sort, [{field: 'contributors', direction: 'desc'}]);
});

test('[studio-sort] a locked view keeps its own order whatever Sort says', () => {
  const time = () => { const s = sheet(); s.columns = [pill('cycle')]; return s; };
  const cases = [
    ['line', time, 'cycle'],
    ['area', time, 'cycle'],
    ['combination', () => { const s = time(); s.rows = [pill('amount'), pill('contributors')]; return s; }, 'cycle'],
    ['dual-line', () => { const s = time(); s.rows = [pill('amount'), pill('contributors')]; return s; }, 'cycle'],
    ['histogram', sheet, 'amount_bin']];
  for (const [type, build, axis] of cases) {
    for (const stored of ['none', 'asc', 'desc']) {
      const s = build(); s.marks.type = type; s.sort = stored;
      const result = compile(s);
      assert.equal(result.spec.type, type, type + ' compiled to ' + result.spec.type);
      assert.deepEqual(result.query.sort, [{field: axis, direction: 'asc'}],
        type + ' with sort=' + stored + ' must keep its axis order');
      assert.ok(studio.sortLock(type, s), type + ' must also report itself locked');
    }
  }
  // A transform is the same story through a different door: the type is
  // rewritten to line first, so the order is the time axis.
  for (const stored of ['none', 'asc', 'desc']) {
    const s = sheet(); s.columns = [pill('cycle')]; s.sort = stored;
    s.analytics = {...s.analytics, transform: 'annual', period: 'cycle'};
    assert.deepEqual(compile(s).query.sort, [{field: 'cycle', direction: 'asc'}]);
  }
});

/* ----------------------------------------------------------------- labels */

test('[studio-labels] every mark type this path can accept or produce has an entry', () => {
  // The accepted ids, plus the two the compile produces but never accepts:
  // 'circle' becomes 'scatter' and 'text' becomes 'table'.
  const producible = new Set([...studio.MARK_TYPES, 'scatter', 'table']);
  const missing = [...producible].filter(type => !(type in studio.LABEL_SUPPORT));
  assert.deepEqual(missing, [], 'LABEL_SUPPORT is missing: ' + missing.join(', '));
  const stale = Object.keys(studio.LABEL_SUPPORT).filter(type => !producible.has(type));
  assert.deepEqual(stale, [], 'LABEL_SUPPORT names types this path cannot produce: ' + stale.join(', '));
  for (const [type, value] of Object.entries(studio.LABEL_SUPPORT)) {
    assert.ok(value === true || (typeof value === 'string' && value.length > 10),
      type + ' must be true or carry a reason a reader can act on');
    if (typeof value === 'string')
      assert.ok(/[a-z]/.test(value) && !/^[a-z]/.test(value), type + ': the reason reads as a sentence');
  }
});

test('[studio-labels] labelLock answers with the empty string only where labels are drawn', () => {
  for (const type of ['bar', 'line', 'area', 'scatter', 'heatmap', 'dot', 'series-dot',
    'stacked', 'histogram', 'bubbles'])
    assert.equal(studio.labelLock(type, 'none'), '', type + ' draws labels');
  for (const type of ['table', 'text', 'highlight', 'treemap', 'box', 'gantt', 'bullet',
    'combination', 'dual-line', 'pie', 'doughnut', 'waterfall', 'pareto', 'radar', 'map', 'filled-map'])
    assert.equal(studio.labelLock(type, 'none'), studio.LABEL_SUPPORT[type],
      type + ' must give its own reason');
  // Period analysis is redrawn by charts.js, which never reads spec.labels -
  // except 'annual', which stays on the normal render path and keeps them.
  for (const transform of ['yoy', 'change', 'forecast'])
    assert.equal(studio.labelLock('bar', transform), studio.LABEL_LOCK_TRANSFORM,
      transform + ' is drawn on the report canvas');
  assert.equal(studio.labelLock('bar', 'annual'), '', 'period totals keep their labels');
  assert.deepEqual(studio.LABELLED_TRANSFORMS, ['none', 'annual']);
  // A type nobody has heard of is refused, not silently allowed.
  assert.ok(studio.labelLock('invented-mark', 'none'), 'an unknown mark is not labellable');
});

test('[studio-labels] the labels toggle is render-only: it never changes the query', () => {
  const off = sheet(), on = sheet();
  // Build 03 (S1): a new sheet starts with its labels on, so "off" is set.
  off.showLabels = false;
  on.showLabels = true;
  assert.deepEqual(compile(on).query, compile(off).query, 'the query must be identical');
  assert.equal(compile(on).spec.labels, true);
  assert.equal(compile(off).spec.labels, false);
});
