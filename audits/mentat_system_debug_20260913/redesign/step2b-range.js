/* Step 2b: a numeric/date filter carries both bounds in one pill, because the
   Filters shelf allows one filter per column. */
'use strict';

module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat\\app',
  eol: 'crlf',
  files: [{
    path: 'chart-studio-core.js',
    edits: [
      {
        find: `  const FILTER_OPS = [['equals', 'Equals'], ['contains', 'Contains'], ['gte', 'At least'],
    ['lte', 'At most'], ['in', 'Is one of'], ['notin', 'Is not one of']];
  const LIST_OPS = ['in', 'notin'];`,
        replace: `  const FILTER_OPS = [['equals', 'Equals'], ['contains', 'Contains'], ['gte', 'At least'],
    ['lte', 'At most'], ['between', 'Between'], ['in', 'Is one of'], ['notin', 'Is not one of']];
  const LIST_OPS = ['in', 'notin'];
  const RANGE_OPS = ['between'];`
      },
      {
        find: `  function filterActive(filter) {
    if (!filter || !filter.op) return false;
    if (LIST_OPS.indexOf(filter.op) !== -1) return filterValues(filter).length > 0;
    return filter.value !== '' && filter.value != null;
  }`,
        replace: `  function filterActive(filter) {
    if (!filter || !filter.op) return false;
    if (LIST_OPS.indexOf(filter.op) !== -1) return filterValues(filter).length > 0;
    if (RANGE_OPS.indexOf(filter.op) !== -1) return filterBounds(filter).some(bound => bound !== '');
    return filter.value !== '' && filter.value != null;
  }

  // A range keeps both ends in one value, so an open end stays an empty string
  // rather than a zero that would quietly exclude everything below it.
  function filterBounds(filter) {
    const value = filter && filter.value;
    const list = Array.isArray(value) ? value : [value, ''];
    return [list[0] == null ? '' : String(list[0]), list[1] == null ? '' : String(list[1])];
  }`
      },
      {
        find: `    const out = {column: Number(filter.column), op: op,
      value: LIST_OPS.indexOf(op) !== -1 ? filterValues(filter) : String(filter && filter.value == null ? '' : filter.value)};`,
        replace: `    const out = {column: Number(filter.column), op: op,
      value: LIST_OPS.indexOf(op) !== -1 ? filterValues(filter)
        : RANGE_OPS.indexOf(op) !== -1 ? filterBounds(filter)
        : String(filter && filter.value == null ? '' : filter.value)};`
      },
      {
        find: `    const values = filterValues(filter);
    if (LIST_OPS.indexOf(filter.op) !== -1) {`,
        replace: `    const values = filterValues(filter);
    if (RANGE_OPS.indexOf(filter.op) !== -1) {
      const [low, high] = filterBounds(filter);
      if (low !== '' && high !== '') return name + ' ' + show(low) + ' to ' + show(high);
      if (low !== '') return name + ' \\u2265 ' + show(low);
      if (high !== '') return name + ' \\u2264 ' + show(high);
      return name + ': any value';
    }
    if (LIST_OPS.indexOf(filter.op) !== -1) {`
      },
      {
        find: `    FILTER_OPS, LIST_OPS, MEASURE_PRESETS, DATE_PARTS, COMPANY_OVERVIEW,
    canTreatAs, filterValues, filterActive, normalizeFilter, filterSummary,`,
        replace: `    FILTER_OPS, LIST_OPS, RANGE_OPS, MEASURE_PRESETS, DATE_PARTS, COMPANY_OVERVIEW,
    canTreatAs, filterValues, filterActive, filterBounds, normalizeFilter, filterSummary,`
      }
    ]
  }, {
    path: 'chart-math.js',
    eol: 'lf',
    edits: [
      {
        find: `      // A member list is the only filter shape that is not a single scalar.
      if (['in','notin'].includes(f.op) && (!Array.isArray(f.value) || !f.value.length)) throw new Error('A member filter needs at least one chosen value.');`,
        replace: `      // A member list and a range are the filter shapes that are not scalars.
      if (['in','notin'].includes(f.op) && (!Array.isArray(f.value) || !f.value.length)) throw new Error('A member filter needs at least one chosen value.');
      if (f.op === 'between' && (!Array.isArray(f.value) || f.value.every(bound => bound === '' || bound == null))) throw new Error('A range filter needs a lower or an upper bound.');`
      },
      {
        find: `        if (f.op === 'in' || f.op === 'notin') {`,
        replace: `        if (f.op === 'between') {
          const [low, high] = f.value;
          const inclusive = (bound, test) => bound === '' || bound == null || test(bound);
          const n = numeric(v);
          if (n !== null) return inclusive(low, b => n >= numeric(b)) && inclusive(high, b => n <= numeric(b));
          const raw = String(v ?? '');
          return raw !== '' && inclusive(low, b => raw >= String(b)) && inclusive(high, b => raw <= String(b));
        }
        if (f.op === 'in' || f.op === 'notin') {`
      }
    ]
  }]
};
