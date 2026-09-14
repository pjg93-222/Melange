/* Steps 2-5 (pure logic): filter model, aggregation/measure model, data-type
   coercion and the company-overview preset builder, all in chart-studio-core.js
   so node:test can exercise them without a DOM. */
'use strict';

const classifyHead = `  // A sheet may re-read a column as a dimension or a measure. The override is
  // per sheet and persisted with it; a text column can never become a measure,
  // because there is nothing numeric in it to aggregate.
  function canTreatAs(field, role) {
    if (!field) return {ok: false, reason: 'That field is not in this source.'};
    if (role === 'dimension') {
      if (field.role === 'dimension') return {ok: false, reason: field.name + ' is already a dimension.'};
      return {ok: true, reason: ''};
    }
    if (role !== 'measure') return {ok: false, reason: 'Choose Dimension or Measure.'};
    if (field.role === 'measure') return {ok: false, reason: field.name + ' is already a measure.'};
    if (field.type !== 'number') {
      return {ok: false, reason: field.name + ' holds ' + (field.type === 'date' ? 'dates' : 'text') +
        ', so there is nothing numeric to aggregate. Count it with COUNT on another measure instead.'};
    }
    return {ok: true, reason: ''};
  }

  function classifyFields(columns, overrides) {`;

const classifyTail = `    const types = overrides && typeof overrides === 'object' ? overrides : {};
    for (const field of fields) {
      const wanted = types[String(field.index)];
      const role = wanted && wanted.role;
      if ((role === 'dimension' || role === 'measure') && role !== field.role && canTreatAs(field, role).ok) {
        field.role = role;
        field.coerced = true;
        field.hidden = false;
        field.glyph = field.geographic_role ? 'geo' : field.data_type === 'boolean' ? 'bool'
          : field.role === 'measure' ? '#' : field.isTime ? 'cal' : 'Abc';
      }
    }
    return {
      fields,
      dimensions: fields.filter(f => f.role === 'dimension' && !f.hidden),
      measures: fields.filter(f => f.role === 'measure' && !f.hidden),
      hidden: fields.filter(f => f.hidden)
    };
  }`;

const filterModel = `  /* --------------------------------------------------------------- filters */

  // Include/exclude member lists join the four original scalar operations. A
  // list filter with no members chosen is not a filter at all: it is dropped
  // before it reaches either engine, so an empty choice never means "nothing".
  const FILTER_OPS = [['equals', 'Equals'], ['contains', 'Contains'], ['gte', 'At least'],
    ['lte', 'At most'], ['in', 'Is one of'], ['notin', 'Is not one of']];
  const LIST_OPS = ['in', 'notin'];

  const filterValues = filter => !filter ? []
    : Array.isArray(filter.value) ? filter.value.map(String)
    : filter.value == null || filter.value === '' ? [] : [String(filter.value)];

  function filterActive(filter) {
    if (!filter || !filter.op) return false;
    if (LIST_OPS.indexOf(filter.op) !== -1) return filterValues(filter).length > 0;
    return filter.value !== '' && filter.value != null;
  }

  function normalizeFilter(filter) {
    const op = FILTER_OPS.some(o => o[0] === (filter && filter.op)) ? filter.op : 'equals';
    const out = {column: Number(filter.column), op: op,
      value: LIST_OPS.indexOf(op) !== -1 ? filterValues(filter) : String(filter && filter.value == null ? '' : filter.value)};
    if (filter && filter.stage) out.stage = filter.stage;
    return out;
  }

  // The one-line description a filter pill and the Inspector row both show.
  function filterSummary(filter, field, memberCount) {
    if (!filter) return '';
    const name = field ? field.name : 'Field';
    const money = !!(field && (field.unit === 'cents' || /amount|receipt|giving|dollar/i.test(field.name)));
    const show = value => {
      const number = Number(value);
      return money && Number.isFinite(number)
        ? number.toLocaleString('en-US', {style: 'currency', currency: 'USD', maximumFractionDigits: 0})
        : String(value);
    };
    const values = filterValues(filter);
    if (LIST_OPS.indexOf(filter.op) !== -1) {
      if (!values.length) return name + ': any value';
      const total = Number.isFinite(Number(memberCount)) && Number(memberCount) >= values.length ? Number(memberCount) : null;
      const listed = values.length <= 3 ? values.join(', ')
        : total ? values.length + ' of ' + total + ' values' : values.length + ' values';
      return name + (filter.op === 'in' ? ': ' : ' excludes ') + listed;
    }
    if (filter.op === 'contains') return name + ' contains ' + show(filter.value);
    if (filter.op === 'gte') return name + ' \\u2265 ' + show(filter.value);
    if (filter.op === 'lte') return name + ' \\u2264 ' + show(filter.value);
    return name + ' = ' + show(filter.value);
  }

  /* ---------------------------------------------------- measures and types */

  // Only offer what the active engine can actually compute. The verified server
  // aggregates one money column six ways; every other verified measure is a
  // source aggregate that is already defined, so it has no aggregation menu.
  const VERIFIED_AGGREGATED = 'amount';

  function aggregationsFor(field, engine) {
    if (!field || field.role !== 'measure') return [];
    if (engine !== 'verified') return AGGREGATIONS.slice();
    return field.id === VERIFIED_AGGREGATED ? AGGREGATIONS.slice() : [];
  }

  // Political-money shortcuts. Each one either exists in this source or says
  // why it does not, instead of failing when the query runs.
  const MEASURE_PRESETS = [
    {id: 'total-giving', label: 'Total giving', aggregation: 'sum'},
    {id: 'gift-count', label: 'Gift count', aggregation: 'count'},
    {id: 'average-gift', label: 'Average gift', aggregation: 'mean'},
    {id: 'distinct-contributors', label: 'Distinct contributors', aggregation: 'sum'}
  ];

  function measurePresets(columns, engine, overrides) {
    const meta = classifyFields(columns, overrides);
    const byId = id => meta.fields.find(f => f.id === id) || null;
    const firstMeasure = meta.measures[0] || null;
    return MEASURE_PRESETS.map(preset => {
      const view = Object.assign({}, preset, {available: false, reason: '', column: -1});
      if (engine === 'verified') {
        const wanted = preset.id === 'gift-count' ? 'records'
          : preset.id === 'distinct-contributors' ? 'contributors' : VERIFIED_AGGREGATED;
        const field = byId(wanted);
        if (!field) { view.reason = 'This source has no ' + wanted + ' measure.'; return view; }
        view.column = field.index;
        view.aggregation = preset.id === 'average-gift' ? 'mean' : 'sum';
        view.available = true;
        return view;
      }
      if (preset.id === 'distinct-contributors') {
        view.reason = 'Distinct contributor counts are computed from source records; use Verified contributions.';
        return view;
      }
      if (!firstMeasure) { view.reason = 'This worksheet has no numeric measure.'; return view; }
      view.column = firstMeasure.index;
      view.available = true;
      return view;
    });
  }

  function applyMeasurePreset(id, state, columns, engine) {
    const preset = measurePresets(columns, engine, state && state.types).find(p => p.id === id);
    const next = clone(state);
    if (!preset || !preset.available) return next;
    const entry = {column: preset.column, aggregation: preset.aggregation};
    const onColumns = shelf(next.columns).some(p => p.column === preset.column);
    const measures = classifyFields(columns, state && state.types).measures.map(f => f.index);
    const strip = list => shelf(list).filter(p => measures.indexOf(p.column) === -1);
    if (onColumns) next.columns = strip(next.columns).concat(entry);
    else next.rows = strip(next.rows).concat(entry);
    return next;
  }

  // Date parts. Verified sources carry real derived columns, so the pill simply
  // moves to that column and the grouping stays on the server. A worksheet has
  // one date column, so the part is expressed with the existing period
  // transform instead of inventing a column the worksheet does not have.
  const DATE_PARTS = [['cycle', 'Election cycle'], ['year', 'Year'], ['quarter', 'Quarter'], ['month', 'Month']];

  function datePartsFor(field, columns, engine) {
    if (!field || !field.isTime || field.role !== 'dimension') return [];
    const meta = classifyFields(columns);
    if (engine === 'verified') {
      return DATE_PARTS
        .map(([id, label]) => ({id, label, column: (meta.fields.find(f => f.id === id) || {index: -1}).index}))
        .filter(part => part.column >= 0 && part.column !== field.index);
    }
    return [{id: 'cycle', label: 'Election cycle', column: field.index},
      {id: 'year', label: 'Year', column: field.index}];
  }

  /* ------------------------------------------------------ company overview */

  // One company, four questions. Read-only presets: no shelf editing, and each
  // one names the field it groups by so "Open in builder" is the same view.
  const COMPANY_OVERVIEW = [
    {id: 'recipient-categories', title: 'Recipient categories', dimension: 'recipient_category',
     measure: 'amount', mark: 'bar', limit: 10, sort: 'desc',
     note: 'Net selected amount by recipient category, largest first.'},
    {id: 'giving-by-cycle', title: 'Giving by election cycle', dimension: 'cycle',
     measure: 'amount', mark: 'line', limit: 40, sort: 'none',
     note: 'Net selected amount by election cycle, in chronological order.'},
    {id: 'top-recipients', title: 'Top recipients', dimension: 'recipient',
     measure: 'amount', mark: 'bar', limit: 8, sort: 'desc',
     note: 'The eight largest recipient committees in this scope.'},
    {id: 'party-split', title: 'Party split', dimension: 'party',
     measure: 'amount', mark: 'doughnut', limit: 10, sort: 'desc',
     note: 'The split is by recipient party. This source has no employee-level field.'}
  ];

  const companyOverviewPresets = () => COMPANY_OVERVIEW.map(preset => Object.assign({}, preset));

  function companyOverviewMissing(preset, columns) {
    const meta = classifyFields(columns);
    return [preset.dimension, preset.measure].filter(id => !meta.fields.some(f => f.id === id));
  }

  function companyOverviewSheet(preset, columns, scope, base) {
    const meta = classifyFields(columns);
    const find = id => meta.fields.find(f => f.id === id) || null;
    const next = base ? clone(base) : createSheet(preset.title, 'overview');
    const dimension = find(preset.dimension);
    const measure = find(preset.measure);
    next.columns = dimension ? [{column: dimension.index, aggregation: 'sum'}] : [];
    next.rows = measure ? [{column: measure.index, aggregation: 'sum'}] : [];
    next.marks = {type: preset.mark, color: null, size: null, label: null, detail: [], tooltip: []};
    next.analytics = Object.assign({}, next.analytics || {},
      {transform: 'none', totals: false, average: false, median: false});
    next.params = Object.assign({}, next.params || {},
      {start: 0, end: 0, limit: 0, maxGroups: preset.limit, splitMulti: false});
    next.pages = null;
    next.pageMember = '';
    next.sort = preset.sort;
    next.filters = [];
    const scoped = scope || {};
    const company = find('company');
    const cycle = find('cycle');
    if (company && scoped.company) next.filters.push({column: company.index, op: 'equals', value: String(scoped.company), stage: 'row'});
    if (cycle && scoped.cycle) next.filters.push({column: cycle.index, op: 'equals', value: String(scoped.cycle), stage: 'row'});
    return next;
  }

`;

module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat\\app',
  eol: 'crlf',
  files: [{
    path: 'chart-studio-core.js',
    edits: [
      {find: '  function classifyFields(columns) {', replace: classifyHead},
      {
        find: `    return {
      fields,
      dimensions: fields.filter(f => f.role === 'dimension' && !f.hidden),
      measures: fields.filter(f => f.role === 'measure' && !f.hidden),
      hidden: fields.filter(f => f.hidden)
    };
  }`,
        replace: classifyTail
      },
      {
        find: `      analytics: {transform: 'none', period: '', horizon: 2, totals: false, average: false, median: false},`,
        replace: `      analytics: {transform: 'none', period: '', horizon: 2, totals: false, average: false, median: false},
      types: {},`
      },
      {
        find: `  function compileReport(state, columns) {
    const meta = classifyFields(columns);`,
        replace: `  function compileReport(state, columns) {
    const meta = classifyFields(columns, state && state.types);`
      },
      {
        find: `  function showMeSelection(state, columns, selected) {
    const meta = classifyFields(columns);`,
        replace: `  function showMeSelection(state, columns, selected) {
    const meta = classifyFields(columns, state && state.types);`
      },
      {
        find: `    const filters = (state.filters || [])
      .filter(f => f && f.value !== '' && f.value != null && fieldAt(meta, Number(f.column)))
      .map(f => ({column: Number(f.column), op: f.op, value: String(f.value)}));`,
        replace: `    const filters = (state.filters || [])
      .filter(f => f && filterActive(f) && fieldAt(meta, Number(f.column)))
      .map(f => normalizeFilter(f));`
      },
      {
        find: '  /* -------------------------------------------------------- result helpers */',
        replace: filterModel + '  /* -------------------------------------------------------- result helpers */'
      },
      {
        find: `    AGGREGATIONS, AGGREGATION_IDS, MARK_TYPES, MARK_IDS, TRANSFORMS, SHOW_ME, STUDIO_GROUP_LIMIT,
    classifyFields, fieldAt, subjectField, pill, shelf, createSheet, clearSheet, swapShelves, sourceKey,`,
        replace: `    AGGREGATIONS, AGGREGATION_IDS, MARK_TYPES, MARK_IDS, TRANSFORMS, SHOW_ME, STUDIO_GROUP_LIMIT,
    FILTER_OPS, LIST_OPS, MEASURE_PRESETS, DATE_PARTS, COMPANY_OVERVIEW,
    canTreatAs, filterValues, filterActive, normalizeFilter, filterSummary,
    aggregationsFor, measurePresets, applyMeasurePreset, datePartsFor,
    companyOverviewPresets, companyOverviewMissing, companyOverviewSheet,
    classifyFields, fieldAt, subjectField, pill, shelf, createSheet, clearSheet, swapShelves, sourceKey,`
      }
    ]
  }, {
    path: 'chart-math.js',
    eol: 'lf',
    edits: [
      {
        find: `      if (!['equals','contains','gte','lte'].includes(f.op)) throw new Error('Choose a filter operation.');
      if (['gte','lte'].includes(f.op) && numeric(f.value) === null) throw new Error('A numeric filter needs a number.');`,
        replace: `      if (!['equals','contains','gte','lte','in','notin'].includes(f.op)) throw new Error('Choose a filter operation.');
      if (['gte','lte'].includes(f.op) && numeric(f.value) === null) throw new Error('A numeric filter needs a number.');
      // A member list is the only filter shape that is not a single scalar.
      if (['in','notin'].includes(f.op) && (!Array.isArray(f.value) || !f.value.length)) throw new Error('A member filter needs at least one chosen value.');`
      },
      {
        find: `        if (f.op === 'equals') return text === wanted;
        if (f.op === 'contains') return text.includes(wanted);`,
        replace: `        if (f.op === 'in' || f.op === 'notin') {
          const chosen = f.value.some(member => String(member).toLocaleLowerCase() === text);
          return f.op === 'in' ? chosen : !chosen;
        }
        if (f.op === 'equals') return text === wanted;
        if (f.op === 'contains') return text.includes(wanted);`
      }
    ]
  }]
};
