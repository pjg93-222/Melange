/* Chart Studio: shelf state -> chart configuration. Pure functions only; no DOM,
   no network, no timers. Field classification and chart choice come from
   chart-math.js so the rules are never forked. Exercised by node:test. */
(function (root) {
  'use strict';

  const math = (typeof module !== 'undefined' && module.exports) ? require('./chart-math.js') : root.MentatCharts;

  // Paul, 2026-09-23: "Additionally, within the Chart Studio make sure everything
  // is freely flexible, that all graph types properly register and nothing is
  // logically constrained, it needs to be utterly maluable." Count distinct
  // (engine contract W12) is how a text field is read as a measure.
  const AGGREGATIONS = [['sum','Sum'],['mean','Mean'],['count','Count'],['median','Median'],['min','Minimum'],['max','Maximum'],['countd','Count distinct']];
  const AGGREGATION_IDS = AGGREGATIONS.map(a => a[0]);
  const TRANSFORMS = ['none','annual','yoy','change','forecast'];

  // Marks card. Doughnut is not a Tableau mark; it is here so that every chart
  // the classic dialog could draw stays reachable from the shelves.
  const MARK_TYPES = [
    ['automatic','Automatic'],['bar','Bar'],['line','Line'],['area','Area'],['circle','Circle'],
    ['pie','Pie'],['doughnut','Doughnut'],['text','Text'],['box','Box'],['histogram','Histogram'],
    ['waterfall','Waterfall'],['pareto','Pareto'],['radar','Radar']
  ];
  const MARK_IDS = MARK_TYPES.map(m => m[0]);
  // One mark list for both sources (census A-W06): every chart the Verified
  // menu offers is offered for a report worksheet too, in the same order and
  // with the same names, so a mark never exists in one mode only.
  const EXTRA_MARK_TYPES = [['map','Map'],['heatmap','Heat map'],['highlight','Highlight table'],['stacked','Stacked bars'],
    ['dot','Circle view'],['series-dot','Side-by-side circles'],['treemap','Treemap'],['bubbles','Packed bubbles'],
    ['gantt','Observed date span'],['bullet','Bullet comparison'],['combination','Dual combination'],['dual-line','Dual lines'],
    ['filled-map','Filled state map']];
  const ALL_MARK_TYPES = MARK_TYPES.concat(EXTRA_MARK_TYPES);
  const ALL_MARK_IDS = ALL_MARK_TYPES.map(m => m[0]);
  const markLabel = id => (ALL_MARK_TYPES.find(m => m[0] === id) || [id, 'Automatic'])[1];

  /* ---------------------------------------------------------------- fields */

  // A sheet may re-read a column as a dimension or a measure. The override is
  // per sheet and persisted with it. A text or date column read as a measure
  // is counted: COUNT and COUNT DISTINCT are the aggregations it offers.
  function canTreatAs(field, role) {
    if (!field) return {ok: false, reason: 'That field is not in this source.'};
    if (role === 'dimension') {
      if (field.role === 'dimension') return {ok: false, reason: field.name + ' is already a dimension.'};
      return {ok: true, reason: ''};
    }
    if (role !== 'measure') return {ok: false, reason: 'Choose Dimension or Measure.'};
    if (field.role === 'measure') return {ok: false, reason: field.name + ' is already a measure.'};
    if (field.type !== 'number') {
      return {ok: true, reason: '', counted: true,
        note: field.name + ' holds ' + (field.type === 'date' ? 'dates' : 'text') + ', so as a measure it is counted: Count or Count distinct.'};
    }
    return {ok: true, reason: ''};
  }

  function classifyFields(columns, overrides) {
    const fields = (columns || []).map((column, position) => {
      const field = {
        index: Number.isInteger(column.index) ? column.index : position,
        name: String(column.name == null ? 'Column ' + (position + 1) : column.name),
        type: column.type || 'category', id: column.id, unit: column.unit,
        data_type:column.data_type,table:column.table,geographic_role:column.geographic_role,description:column.description,discrete:column.discrete,
        distinct: column.distinct == null ? null : column.distinct,
        missing: column.missing == null ? null : column.missing
      };
      if (column.accounting) field.accounting = column.accounting;
      field.isTime = column.is_time === true || !!math.timeColumn(field);
      field.isIdentifier = !!math.identifierColumn(field);
      field.role = column.role || (field.type === 'number' && !field.isTime && !field.isIdentifier ? 'measure' : 'dimension');
      // Identifier columns are real fields, listed like any other (census
      // B-S21): the Data pane puts them under its "More fields" fold rather
      // than behind a checkbox. recommend() still ignores them.
      field.hidden = false;
      // The calendar marks a date (type 'date'), as S1 draws it; a cycle, year,
      // quarter or month is still a time axis (isTime) but its glyph is Abc.
      field.glyph = field.geographic_role ? 'geo' : field.data_type==='boolean'?'bool':field.role === 'measure' ? '#' : field.type === 'date' ? 'cal' : 'Abc';
      return field;
    });
    const types = overrides && typeof overrides === 'object' ? overrides : {};
    for (const field of fields) {
      const wanted = types[String(field.index)];
      const role = wanted && wanted.role;
      if ((role === 'dimension' || role === 'measure') && role !== field.role && canTreatAs(field, role).ok) {
        field.role = role;
        field.coerced = true;
        field.hidden = false;
        if (role === 'measure' && field.type !== 'number') field.counted = true;
        field.glyph = field.geographic_role ? 'geo' : field.data_type === 'boolean' ? 'bool'
          : field.role === 'measure' ? '#' : field.type === 'date' ? 'cal' : 'Abc';
      }
    }
    return {
      fields,
      dimensions: fields.filter(f => f.role === 'dimension' && !f.hidden),
      measures: fields.filter(f => f.role === 'measure' && !f.hidden),
      hidden: fields.filter(f => f.hidden),
      identifiers: fields.filter(f => f.role === 'dimension' && f.isIdentifier && !f.isTime)
    };
  }

  const fieldAt = (meta, index) => meta.fields.find(f => f.index === index) || null;

  // Board S1 opens each Data-pane bucket on a short list of named fields, in
  // the board's order; the bucket's other fields fold under "More fields".
  // An id the catalog does not have is skipped, never stood in for.
  function paneBuckets(fields, ids) {
    const list = fields || [];
    const shown = (ids || []).map(id => list.find(f => f.id === id)).filter(Boolean);
    return {shown, more: list.filter(f => !shown.includes(f))};
  }

  // The classic dialog and the engine both find the subject by an exact
  // 'Subject' column name (charts.js prepareSubjects, chart-math temporal), so
  // the studio reads it the same way rather than inventing a looser rule.
  const subjectField = fields => (fields || []).find(f => f.name === 'Subject') || null;

  /* ----------------------------------------------------------------- state */

  function pill(value) {
    if (value == null) return null;
    if (typeof value === 'number') return Number.isInteger(value) ? {column: value, aggregation: 'sum'} : null;
    if (typeof value === 'string' && /^-?\d+$/.test(value)) return {column: Number(value), aggregation: 'sum'};
    if (typeof value !== 'object' || !Number.isInteger(Number(value.column))) return null;
    return {column: Number(value.column), aggregation: AGGREGATION_IDS.includes(value.aggregation) ? value.aggregation : 'sum'};
  }

  const shelf = list => (Array.isArray(list) ? list : []).map(pill).filter(Boolean);

  function createSheet(name, id) {
    return {
      id: id || '',
      name: name || 'Sheet 1',
      // No dataset or industry key by default: a report worksheet has neither,
      // and an EMPTY industry is the shape the save gate refuses. Contributions
      // mode and migrateSheet() set both when a dataset exists.
      source: {run: '', runName: '', report: '', reportName: '', sheet: '', header: 0, sha256: ''},
      // The ordered series sources a sheet can fan out across - empty means
      // the sheet reads one series, its own `source`. Each entry is
      // {industry, dataset, label}. Populated by contributions mode and by
      // migrateSheet(); nothing renders more than one source yet (S4 delivers
      // the model, not the chart).
      sources: [],
      columns: [],
      rows: [],
      marks: {type: 'automatic', color: null, size: null, label: null, detail: [], tooltip: []},
      filters: [],
      pages: null,
      pageMember: '',
      analytics: {transform: 'none', period: '', horizon: 2, totals: false, average: false, median: false},
      types: {},
      params: {start: 0, end: 0, limit: 0, subject: '', maxGroups: 0, splitMulti: false},
      sort: 'none',
      // S1 (build 03): a new sheet writes each bar's value at its end. Labels
      // stays a toggle, and a saved sheet keeps its own choice.
      showLabels: true,
      fit: 'standard'
    };
  }

  const clone = value => JSON.parse(JSON.stringify(value));

  function swapShelves(state) {
    const next = clone(state);
    next.columns = clone(state.rows || []);
    next.rows = clone(state.columns || []);
    return next;
  }

  function clearSheet(state) {
    const next = createSheet(state.name, state.id);
    next.source = clone(state.source || {});
    return next;
  }

  // Backfills a sheet loaded from disk or the browser-local store before the
  // industry parameter existed: a source that only ever recorded `dataset`
  // gets `industry = dataset` (S4_DESIGN.md section 0.2 - the dataset id IS
  // the industry label), and `sources` is normalized to an array of
  // {industry, dataset, label} entries, dropping anything that cannot resolve
  // to an industry rather than carrying a fan-out entry openability() could
  // never check against the registry.
  function migrateSheet(sheet) {
    const next = sheet && typeof sheet === 'object' ? clone(sheet) : {};
    const source = next.source && typeof next.source === 'object' ? next.source : {};
    if (source.dataset && !source.industry) source.industry = source.dataset;
    next.source = source;
    const rawSources = Array.isArray(next.sources) ? next.sources : [];
    next.sources = rawSources
      .filter(entry => entry && typeof entry === 'object')
      .map(entry => ({
        industry: typeof entry.industry === 'string' ? entry.industry : '',
        dataset: typeof entry.dataset === 'string' ? entry.dataset : '',
        label: typeof entry.label === 'string' ? entry.label : ''
      }))
      .filter(entry => entry.industry);
    return next;
  }

  // Where a single click puts a field. A grouping goes across the top unless
  // something is already there; a dollar or count measure goes down the side
  // unless something is already there. Only the shelves are read, so a click
  // chooses the zone a drop onto that same empty shelf would choose.
  function quickAddZone(field, state) {
    const columnsEmpty = shelf(state && state.columns).length === 0;
    const rowsEmpty = shelf(state && state.rows).length === 0;
    if (field && field.role === 'measure') return rowsEmpty ? 'rows' : 'columns';
    return columnsEmpty ? 'columns' : 'rows';
  }

  // One worksheet, one saved session. data.sha256 digests the whole workbook,
  // so it is identical for every sheet in the file and cannot tell them apart;
  // the run, the report, the worksheet and the header row can.
  function sourceKey(fields, data) {
    const source = fields || {}, body = data || {};
    return [source.run, source.report, body.sheet || source.sheet,
      String(body.header_row ?? ''), body.sha256 || ''].join('|');
  }

  /* ------------------------------------------------------- carried scope */

  // Graph names an election cycle by the year it ends in ('2024'); the
  // verified index stores the pair that cycle covers ('2023-2024'). A scope
  // carried from Graph without this translation filtered on a value the
  // index never holds, so the studio answered "No matching observations"
  // for a company that plainly has receipts. Every other field is carried
  // unchanged: this is a spelling difference, not a rule.
  function carriedFilterValue(fieldId, value) {
    const text = value == null ? '' : String(value);
    if (fieldId !== 'cycle' || !/^\d{4}$/.test(text)) return text;
    return (Number(text) - 1) + '-' + text;
  }

  // The reverse, for the Graph query the reconciliation strip fires. A label
  // that is not a consecutive pair is not a cycle Graph can answer for, so
  // it returns '' rather than a year the reader never chose.
  function graphCycleValue(cycleLabel) {
    const text = cycleLabel == null ? '' : String(cycleLabel);
    const pair = /^(\d{4})-(\d{4})$/.exec(text);
    if (pair) return Number(pair[2]) === Number(pair[1]) + 1 ? pair[2] : '';
    return /^\d{4}$/.test(text) ? text : '';
  }

  /* ------------------------------------------------- report-workbook guards */

  // The published `<Industry> Industry Spending Overview.xlsx` is a report
  // layout, not a table. Its cycle sheets stack three partitions of the same
  // money under `Fact Type` - Recipient, Employee and Master - and only the
  // Recipient partition matches the report's own Total Giving; `Recipient List`
  // repeats every recipient once under an Industry view and again under a
  // Company view. Summing such a sheet whole triples or doubles it, so a
  // worksheet that carries one of those columns opens with the partition the
  // report itself totals already selected. The guard is an ordinary filter
  // pill: one click removes it, and the note says what removing it shows.
  // Each guard needs its own value to be present in the column: a sheet that
  // names the column but never holds the value would otherwise open empty.
  const WORKSHEET_GUARDS = [
    {column: 'Fact Type', value: 'Recipient', needsValue: true,
      note: 'Cycle sheets stack three fact partitions (Recipient, Employee, Master) of the same money. Only one partition matches the report total; Recipient is selected. Remove this filter to see the others.'},
    {column: 'View', value: 'Industry', needsValue: true,
      note: 'This sheet repeats every recipient under an Industry view and a Company view. Industry is selected so amounts are not doubled.'}
  ];

  // These four sheets carry the recipient committees' own receipts and
  // disbursements. That money is the committee's, not the industry's, and it
  // is orders of magnitude larger, so it is never presented as an industry
  // total.
  const COMMITTEE_ACTIVITY_SHEETS = ['Downstream Activity', 'Beneficiary Summary',
    'Beneficiary Bridge', 'Transfer Paths'];
  const COMMITTEE_ACTIVITY_NOTE = 'This sheet reports recipient committees\u2019 own activity, not the industry\u2019s giving. Totals here are not industry money and do not reconcile to the report\u2019s Total Giving.';

  const WORKSHEET_GROUP_LABELS = {data: 'Data workbook (tall, chart-ready)',
    overview: 'Overview workbook (report layout)'};
  const NO_DATA_WORKBOOK_HINT = 'The chart-ready Data workbook has not been published for this industry yet.';

  const guardText = value => String(value == null ? '' : value).trim();
  const guardSame = (a, b) => guardText(a).toLowerCase() === guardText(b).toLowerCase();

  // `columns` is the scanned column metadata. `values` reads one column's
  // values: either a function of the column index, or anything indexable by it.
  // Only the `View` guard reads values, and only for the column it has already
  // matched by name, so a caller never scans a sheet this returns nothing for.
  function defaultGuards(columns, values) {
    const read = index => {
      const list = typeof values === 'function' ? values(index) : (values || {})[index];
      return Array.isArray(list) ? list : [];
    };
    const guards = [];
    (columns || []).forEach((column, position) => {
      const index = Number.isInteger(column && column.index) ? column.index : position;
      for (const guard of WORKSHEET_GUARDS) {
        if (!guardSame(column && column.name, guard.column)) continue;
        // A column of either name can appear elsewhere without holding the
        // value this guard selects, and filtering on a value the sheet does
        // not have would empty the chart instead of correcting it.
        if (guard.needsValue && !read(index).some(value => guardSame(value, guard.value))) continue;
        guards.push({column: index, name: guardText(column && column.name),
          value: guard.value, note: guard.note});
      }
    });
    return guards;
  }

  const committeeActivitySheet = name =>
    COMMITTEE_ACTIVITY_SHEETS.some(sheet => guardSame(sheet, name)) ? COMMITTEE_ACTIVITY_NOTE : null;

  // The catalog tags every workbook with `kind` (server.py published_reports).
  // A server that does not send it still names the companion in the filename,
  // which is the same rule read from the other end.
  const DATA_WORKBOOK_NAME = /\s+Industry Spending Data\.xlsx$/i;
  function workbookKind(entry) {
    const kind = guardText(entry && entry.kind).toLowerCase();
    if (kind === 'data' || kind === 'overview') return kind;
    return DATA_WORKBOOK_NAME.test(guardText(entry && entry.name)) ? 'data' : 'overview';
  }
  function groupWorksheets(catalog) {
    const rows = Array.isArray(catalog) ? catalog
      : Array.isArray(catalog && catalog.reports) ? catalog.reports : [];
    const data = [], overview = [];
    for (const entry of rows) (workbookKind(entry) === 'data' ? data : overview).push(entry);
    return {data: data, overview: overview};
  }

  /* --------------------------------------------------------------- compile */

  const positiveInteger = value => {
    const number = Number(value);
    return Number.isFinite(number) && number >= 1 ? Math.trunc(number) : 0;
  };

  // The Studio's own default: sixty marks per view, which is the engine's
  // standing contract too. Every compiled configuration carries its limit
  // explicitly, and the Group limit box in Parameters raises it - to "All"
  // (engine contract W10) when the reader wants every group.
  const STUDIO_GROUP_LIMIT = 60;
  const groupLimitOf = value => value === 'all' ? 'all' : positiveInteger(value) || STUDIO_GROUP_LIMIT;

  // Colour on these types is a series the engine draws per member (contract
  // W11); on every other type it joins the grouping tuple instead.
  const SERIES_TYPES = ['bar', 'horizontal', 'line', 'area', 'dot', 'scatter', 'histogram', 'box',
    'pie', 'doughnut', 'waterfall', 'pareto', 'radar'];
  const PAIRED = {bar: 'grouped', horizontal: 'groupedhorizontal', line: 'multiline'};

  // Paul, 2026-09-23: "Additionally, within the Chart Studio make sure
  // everything is freely flexible, that all graph types properly register and
  // nothing is logically constrained, it needs to be utterly maluable." So the
  // compiler never refuses a composition. Every mark draws from whatever is on
  // the shelves; a field a mark prefers but the shelves lack is picked from the
  // source and named in a quiet note; every sentence that used to block the
  // drawing is a note under it. Only an empty sheet has nothing to draw.
  function compileReport(state, columns) {
    const meta = classifyFields(columns, state && state.types);
    const issues = [], notes = [];
    const attach = list => shelf(list)
      .map(p => Object.assign({}, p, {field: fieldAt(meta, p.column)}))
      .filter(p => p.field);
    const columnPills = attach(state.columns);
    const rowPills = attach(state.rows);
    const isDimension = p => p.field.role === 'dimension';
    const isMeasure = p => p.field.role === 'measure';
    const colDimensions = columnPills.filter(isDimension);
    const colMeasures = columnPills.filter(isMeasure);
    const rowDimensions = rowPills.filter(isDimension);
    const rowMeasures = rowPills.filter(isMeasure);
    const allMeasures = colMeasures.concat(rowMeasures);
    const allDimensions = colDimensions.concat(rowDimensions);
    const marks = state.marks || {};
    const markType = ALL_MARK_IDS.includes(marks.type) ? marks.type : 'automatic';
    const markName = markLabel(markType);
    const encoded = channel => attach(Array.isArray(marks[channel]) ? marks[channel] : [marks[channel]].filter(v => v != null));
    const colorPill = encoded('color')[0] || null;
    const color = colorPill ? colorPill.field : null;
    const sizePill = encoded('size')[0] || null;
    const labelPill = encoded('label')[0] || null;
    const tooltipPills = encoded('tooltip');
    const details = encoded('detail');
    // Dimensions on Detail, Tooltip, Label and Size join the grouping behind
    // each mark, as they do on the verified path; a measure on Detail or
    // Tooltip is carried into each mark's tooltip (census B-S03).
    const markDimensions = [...details, ...tooltipPills, ...(labelPill ? [labelPill] : []),
      ...(sizePill ? [sizePill] : [])].filter(isDimension);
    const anything = columnPills.length || rowPills.length || colorPill || sizePill || labelPill ||
      tooltipPills.length || details.length;

    const firstDimension = allDimensions[0] || null;
    const firstMeasure = rowMeasures[0] || colMeasures[0] || null;
    const timeDimension = allDimensions.find(p => p.field.isTime) || null;
    // A dimension on Columns draws upright bars; a dimension only on Rows lays
    // the same view on its side, which is what Tableau's Rows shelf means here.
    const orientation = marks.orientation || (colDimensions.length ? 'vertical' : rowDimensions.length ? 'horizontal' : 'none');

    const chosen = new Set([...allDimensions, ...allMeasures, ...details, ...tooltipPills,
      ...(colorPill ? [colorPill] : []), ...(sizePill ? [sizePill] : []), ...(labelPill ? [labelPill] : [])].map(p => p.column));
    function pick(kind, prefer) {
      const free = (kind === 'measure' ? meta.measures : meta.dimensions).filter(f => !f.hidden && !chosen.has(f.index));
      const plain = free.filter(f => !f.isTime && !f.isIdentifier);
      const order = kind === 'measure' ? free
        : prefer === 'time' ? [...free.filter(f => f.isTime), ...plain, ...free]
        : prefer === 'geo' ? [...free.filter(f => f.geographic_role || /zip|postal|state/i.test(f.name)), ...plain, ...free]
        : [...plain, ...free];
      const field = order[0] || null;
      if (!field) return null;
      chosen.add(field.index);
      return {column: field.index, aggregation: 'sum', field: field, picked: true};
    }
    const pickedNote = (p, why, where) => notes.push(markName + ' ' + why + ', so it uses ' + p.field.name +
      '. Put ' + where + ' to choose another.');
    const extraMeasures = [];
    const extra = {};

    let type = '', xPill = null, yPill = null, seriesPill = null, map = null;
    const needMeasure = why => {
      if (!yPill && (yPill = pick('measure'))) pickedNote(yPill, why, 'a measure on the shelves');
    };
    const needAxis = (why, prefer) => {
      if (!xPill && (xPill = pick('dimension', prefer))) pickedNote(xPill, why, 'a dimension on the shelves');
    };
    const secondMeasure = why => {
      if (allMeasures.length + extraMeasures.length >= 2 || (color && color.role === 'dimension')) return;
      const second = pick('measure');
      if (second) { extraMeasures.push(second); pickedNote(second, why, 'a second measure on the shelves'); }
    };
    const barLike = () => {
      type = orientation === 'horizontal' ? 'horizontal' : 'bar';
      xPill = orientation === 'horizontal' ? (rowDimensions[0] || firstDimension) : (colDimensions[0] || firstDimension);
      yPill = orientation === 'horizontal' ? (colMeasures[0] || rowMeasures[0] || null) : firstMeasure;
    };

    if (!anything) {
      issues.push('Add a grouping (company, recipient, cycle) and a dollar measure.');
    } else if (markType === 'automatic') {
      if (colMeasures.length && rowMeasures.length) {
        type = 'scatter'; xPill = colMeasures[0]; yPill = rowMeasures[0];
      } else if (orientation === 'none') {
        type = 'bar'; yPill = firstMeasure;
      } else {
        const dimension = (orientation === 'vertical' ? colDimensions[0] : rowDimensions[0]) || firstDimension;
        const measure = orientation === 'vertical'
          ? (rowMeasures[0] || colMeasures[0] || null)
          : (colMeasures[0] || rowMeasures[0] || null);
        xPill = dimension; yPill = measure;
        type = orientation === 'horizontal' ? 'horizontal' : (dimension?.field.isTime && measure ? 'line' : 'bar');
      }
    } else if (markType === 'circle') {
      yPill = rowMeasures[0] || allMeasures[0] || null;
      xPill = colMeasures.find(p => p !== yPill) || allMeasures.find(p => p !== yPill) || null;
      if (xPill && yPill) type = 'scatter';
      else {
        // One measure: one circle per group at its value (contract W6 'dot').
        type = 'dot'; xPill = firstDimension;
        needAxis('needs a grouping for its circles');
      }
    } else if (markType === 'histogram') {
      type = 'histogram'; yPill = firstMeasure;
      needMeasure('needs a measure to bin');
      // A shelf dimension stacks the bins by its members (contract W11, W3).
      if (firstDimension && !(color && color.role === 'dimension')) {
        seriesPill = firstDimension; extra.stack = 'stacked';
        notes.push('Histogram bins are stacked by ' + firstDimension.field.name + '.');
      }
    } else if (markType === 'box') {
      type = 'box'; xPill = firstDimension; yPill = firstMeasure;
      needMeasure('needs a measure to summarise');
    } else if (markType === 'line' || markType === 'area' || markType === 'dual-line') {
      // The first dimension placed is the axis: a category axis draws in its
      // own order, and a time axis stays chronological.
      type = markType === 'area' ? 'area' : 'line';
      xPill = firstDimension; yPill = firstMeasure;
      needAxis('needs an axis', 'time');
      if (markType === 'dual-line') {
        needMeasure('needs a measure');
        secondMeasure('needs a second measure for its second axis');
        extra.dualAxis = true; extra.dualMark = 'line';
      }
    } else if (markType === 'dot' || markType === 'series-dot') {
      type = 'dot'; xPill = firstDimension; yPill = firstMeasure;
      needAxis('needs a grouping for its circles');
      if (markType === 'series-dot' && !(color && color.role === 'dimension')) {
        seriesPill = allDimensions.find(p => p !== xPill) || null;
        if (!seriesPill && (seriesPill = pick('dimension'))) pickedNote(seriesPill, 'needs a breakdown for its circle series', 'a dimension on Colour');
      }
    } else if (markType === 'gantt') {
      type = 'gantt'; xPill = firstDimension; yPill = firstMeasure;
      needAxis('needs a grouping for its spans');
      const date = meta.fields.find(f => !f.hidden && f.type === 'date');
      if (date) extra.dateColumn = date.index;
      else {
        type = 'bar';
        notes.push('An observed date span needs a date column and this worksheet has none, so it is drawn as bars.');
      }
    } else if (markType === 'bullet') {
      type = 'bullet'; xPill = firstDimension; yPill = firstMeasure;
      needMeasure('needs a measure');
      secondMeasure('needs a second measure to compare');
    } else if (['bar', 'text', 'stacked', 'combination', 'map', 'filled-map'].includes(markType)) {
      barLike();
      if (markType === 'stacked') {
        extra.stack = 'stacked';
        if (!(color && color.role === 'dimension') && allMeasures.length < 2) {
          seriesPill = allDimensions.find(p => p !== xPill) || null;
          if (!seriesPill && (seriesPill = pick('dimension'))) pickedNote(seriesPill, 'needs a breakdown to stack', 'a dimension on Colour');
        }
      } else if (markType === 'combination') {
        needAxis('needs an axis', 'time');
        needMeasure('needs a measure for its bars');
        secondMeasure('needs a second measure for its line');
        extra.dualAxis = true; extra.dualMark = 'line';
      } else if (markType === 'map' || markType === 'filled-map') {
        // Census C-16: a worksheet with a place field draws a real map. A
        // place on the shelves wins (the finest for a symbol map, a shape for
        // a filled map); with none placed, the sheet's own place field is
        // picked and named. Only a sheet with no place field at all is drawn
        // as bars, and it says so.
        const filled = markType === 'filled-map';
        const rank = f => geoRank(f, filled);
        let geography = allDimensions.filter(p => geoKind(p.field)).sort((a, b) => rank(a.field) - rank(b.field))[0] || null;
        if (!geography) {
          const field = meta.dimensions.filter(f => !f.hidden && geoKind(f) && !chosen.has(f.index))
            .sort((a, b) => geoRank(a, filled, true) - geoRank(b, filled, true))[0];
          if (field) {
            chosen.add(field.index);
            geography = {column: field.index, aggregation: 'sum', field: field, picked: true};
            pickedNote(geography, 'needs a place to group by', 'a ZIP, state, district or city field on the shelves');
          }
        }
        if (geography) {
          xPill = geography;
          const kind = geoKind(geography.field);
          let stateColumn = -1;
          if (kind === 'district') {
            const onShelf = allDimensions.find(p => geoKind(p.field) === 'state');
            const state = onShelf ? onShelf.field : meta.dimensions.find(f => !f.hidden && geoKind(f) === 'state');
            if (state) stateColumn = state.index;
            else notes.push('A district is placed with its state and this worksheet has no state field, so only districts written like MN-05 are mapped.');
          }
          map = {kind: kind, column: geography.column, stateColumn: stateColumn, filled: filled, name: geography.field.name};
          const combined = [...allDimensions, ...(color && color.role === 'dimension' ? [colorPill] : [])]
            .filter(p => p.column !== geography.column && p.column !== stateColumn);
          if (combined.length) notes.push('Each map mark combines every ' +
            [...new Set(combined.map(p => p.field.name))].join(' / ') + ' group at its place.');
          if ((color && color.role === 'measure') || sizePill || labelPill) notes.push('A map shades and sizes each place by ' +
            (firstMeasure ? firstMeasure.field.name : 'its row count') + '; Colour, Size and Label do not change it.');
        } else {
          needAxis('needs a place to group by');
          notes.push('Maps need a ZIP, state, congressional district or city field and this worksheet has none, so it is drawn as bars' +
            (xPill ? ' by ' + xPill.field.name : '') + '.');
        }
      }
    } else {
      // pie, doughnut, waterfall, pareto, radar, heatmap, highlight, treemap, bubbles
      type = markType; xPill = firstDimension; yPill = firstMeasure;
      needAxis('needs a grouping');
    }

    // Colour: a dimension separates series (or joins the grouping), a measure
    // shades each mark (contract W11 colorMeasure). Colour that repeats the
    // axis gives every mark its own colour, which the bars already have.
    if (type && color) {
      if (color.role === 'measure') extra.colorMeasure = {column: colorPill.column, aggregation: colorPill.aggregation};
      else if (!xPill || color.index !== xPill.column) seriesPill = colorPill;
    }
    if (type && sizePill) {
      if (isMeasure(sizePill)) extra.size = {column: sizePill.column, aggregation: sizePill.aggregation};
      else notes.push('Size follows a measure; ' + sizePill.field.name + ' joins the grouping instead.');
    }
    if (type && labelPill) extra.label = {column: labelPill.column, aggregation: isMeasure(labelPill) ? labelPill.aggregation : 'first'};
    const tips = [...tooltipPills, ...details].filter(isMeasure).map(p => ({column: p.column, aggregation: p.aggregation}));
    if (type && tips.length) extra.tooltip = tips;

    const analytics = state.analytics || {};
    let transform = TRANSFORMS.includes(analytics.transform) ? analytics.transform : 'none';
    if (transform !== 'none' && type && map) {
      // A map has no time axis: it draws each place's total over the rows
      // selected, so period analysis is left off and said to be.
      notes.push('A map draws each place’s total over the selected rows; period analysis needs a chart with a time axis, so it is left off.');
      transform = 'none';
    } else if (transform !== 'none' && type) {
      if (!timeDimension) {
        notes.push('Time analysis needs a date, year or election-cycle dimension on Columns or Rows, so the chart is drawn without it.');
        transform = 'none';
      } else {
        // Contract W5: the chosen mark is kept, and Colour and every other
        // dimension become series over the periods.
        xPill = timeDimension;
      }
    }

    let series = -1;
    const seriesType = SERIES_TYPES.includes(type);
    if (type && seriesPill && seriesType) {
      series = seriesPill.column;
      if (transform === 'none' && PAIRED[type]) type = PAIRED[type];
    }

    let x = xPill ? xPill.column : -1;
    let y = yPill ? yPill.column : -1;
    let aggregation = yPill ? yPill.aggregation : 'count';
    const selectedAccounting = y >= 0 ? fieldAt(meta, y)?.accounting : null;
    if (aggregation === 'sum' && selectedAccounting?.safe_to_sum === false) notes.push(selectedAccounting.reason || 'This raw measure is not safe to sum. Choose the analysis amount.');
    if (type === 'histogram') x = -1;
    if (y === -1) aggregation = 'count';
    let grouping = [...new Set([...allDimensions, ...markDimensions].map(p => p.column))];
    if (seriesPill && !seriesType && !grouping.includes(seriesPill.column)) grouping.push(seriesPill.column);
    // A scatter over dimensions plots one circle per group of them, each an
    // aggregate (contract W9); with none it plots individual rows, as before.
    // Census B-S07 / C-04 (Paul, 2026-09-23: "nothing is logically
    // constrained"): a dimension on Detail (or Tooltip, Label, Size) sets a box's
    // or a histogram's level of detail the same way - each value is that group's
    // aggregate - so a box of recipient totals per company, or a histogram of
    // committee totals, is one gesture. Without one they read individual rows.
    const detailGrain = (type === 'box' || type === 'histogram') && markDimensions.length > 0;
    const grain = (type === 'scatter' && grouping.length) || detailGrain ? 'group' : 'row';
    const AGGREGATE_WORD = {sum: 'total', mean: 'average', count: 'row count', median: 'median', min: 'minimum', max: 'maximum', countd: 'distinct count'};
    if (grain === 'group' && type === 'scatter') {
      extra.grain = 'group';
      extra.xAggregation = xPill.aggregation;
      notes.push('Each circle is one ' + grouping.map(column => (fieldAt(meta, column) || {name: 'group'}).name).join(' / ') +
        ' group; both measures are aggregated over it.');
    } else if (grain === 'group') {
      extra.grain = 'group';
      const detailNames = [...new Set(markDimensions.map(p => p.field.name))].join(' / ');
      const what = (AGGREGATE_WORD[aggregation] || aggregation) + ' of ' + (yPill ? yPill.field.name : 'rows');
      notes.push(type === 'box' ? 'Each box summarises the ' + what + ' of every ' + detailNames + ' group.'
        : 'The bins count ' + detailNames + ' groups by their ' + what + '.');
      // Each group must carry one Colour member for the bins to stack by it.
      if (type === 'histogram') grouping = [...new Set([...markDimensions.map(p => p.column), ...(series >= 0 ? [series] : [])])];
    } else if (['scatter', 'box', 'histogram'].includes(type)) {
      if (aggregation === 'count') aggregation = 'sum';
    }
    if ((type === 'histogram' && grain === 'row') || (type === 'scatter' && grain === 'row')) grouping = [];
    if (x < 0 && grouping.length && type !== 'scatter' && type !== 'histogram') x = grouping[0];
    if (x >= 0 && !['scatter', 'histogram'].includes(type)) grouping = [x, ...grouping.filter(column => column !== x && column !== series)];

    const measurePills = type === 'scatter'
      ? [xPill, yPill, ...allMeasures.filter(p => p !== xPill && p !== yPill)]
      : [yPill, ...allMeasures.filter(p => p !== yPill), ...extraMeasures];
    const seen = new Set(), measures = [];
    for (const p of measurePills) {
      if (!p || p.column < 0) continue;
      const entry = {column: p.column, aggregation: p === yPill ? aggregation : p.aggregation};
      const key = entry.column + '|' + entry.aggregation;
      if (seen.has(key)) continue;
      seen.add(key);
      measures.push(entry);
    }

    const timeField = xPill && xPill.field.isTime ? xPill.field : null;
    const period = ['year', 'cycle'].includes(analytics.period) ? analytics.period
      : timeField && /cycle/i.test(timeField.name) ? 'cycle' : 'year';
    const horizon = Number.isFinite(Number(analytics.horizon)) && Number(analytics.horizon) >= 1
      ? Math.trunc(Number(analytics.horizon)) : 2;

    const filters = (state.filters || [])
      .filter(f => f && filterActive(f) && fieldAt(meta, Number(f.column)))
      .map(f => normalizeFilter(f));
    if (filters.some(f => ['gte','lte'].includes(f.op))) notes.push('Number filters apply to rows, not totals. Filter totals in Verified contributions.');
    const pagePill = pill(state.pages);
    if (pagePill && fieldAt(meta, pagePill.column) && state.pageMember) {
      filters.push({column: pagePill.column, op: 'equals', value: String(state.pageMember)});
    }

    const params = state.params || {};
    // Several subjects over time are drawn as one series each (contract W5);
    // the Subject choice in Parameters still narrows time analysis to one.
    const subject = subjectField(meta.fields);
    if (subject && transform !== 'none' && !filters.some(f => f.column === subject.index)) {
      const chosenSubject = params.subject == null ? '' : String(params.subject);
      if (chosenSubject) filters.push({column: subject.index, op: 'equals', value: chosenSubject});
      else notes.push('Every Subject is drawn as its own series over time; choose one in Parameters to add up a single Subject.');
    }

    const config = type ? {
      type: type,
      x: x,
      y: y,
      dimensions: grouping,
      aggregation: aggregation,
      transform: transform,
      period: period,
      horizon: horizon,
      start: positiveInteger(params.start),
      end: positiveInteger(params.end),
      limit: positiveInteger(params.limit),
      maxGroups: groupLimitOf(params.maxGroups),
      splitMulti: !!params.splitMulti,
      series: series,
      filters: filters,
      lenient: true
    } : null;
    if (config) {
      if (measures.length) config.measures = measures;
      for (const key of Object.keys(extra)) config[key] = extra[key];
      const width = Number(params.binWidth);
      if (type === 'histogram' && Number.isFinite(width) && width > 0) config.binWidth = width;
      if (type === 'histogram' && positiveInteger(params.bins)) config.bins = Math.min(1000, positiveInteger(params.bins));
    }

    if (config && transform === 'forecast' && (config.start || config.end || config.limit)) {
      notes.push('The same-phase forecast reads every worksheet row; clear the row range and row limit in Parameters.');
    }
    if (config && config.splitMulti && config.aggregation !== 'count') notes.push('Split multi-value cells repeats the measure across values, so the grand total is not shown. Choose Count for coverage, or use transaction-level ZIP data for money.');
    // Splitting rewrites the grouping cell, so a view with nothing on the axis
    // has no cell to split and the parameter would silently do nothing.
    if (config && config.splitMulti && config.x < 0 && config.series < 0) {
      notes.push('Splitting multi-value cells applies to the grouping field; put a dimension on Columns or Rows.');
    }

    return {
      config: config,
      issues: issues,
      notes: notes,
      renderMode: markType === 'text' ? 'table' : 'chart',
      markType: markType,
      map: config ? map : null,
      fields: meta
    };
  }

  const compileConfig = (state, columns) => compileReport(state, columns).config;

  /* -------------------------------------------------------- worksheet maps */

  // Census C-16. Which kind of place a worksheet field holds, read from its
  // geographic role or its name: 'zip', 'city-state', 'district', 'state', or
  // '' for a field that is not a place.
  function geoKind(field) {
    if (!field) return '';
    const role = String(field.geographic_role || '').toLowerCase(), name = String(field.name || '');
    if (/zip|postal/.test(role) || /\bzip|postal|zcta/i.test(name)) return 'zip';
    if (/city/.test(role) || /\bcit(y|ies)\b/i.test(name)) return 'city-state';
    if (/district/.test(role) || /\bdistricts?\b/i.test(name)) return 'district';
    if (/state/.test(role) || /\bstates?\b/i.test(name)) return 'state';
    return '';
  }
  // Among places the reader put on the shelves, a symbol map takes the finest
  // and a filled map a place with a shape (a district over its state). When
  // the Studio picks one itself it prefers the place every row can have: a
  // ZIP for symbols, a state for a filled map ("Filled state map").
  const GEO_ORDER = {symbol: ['zip', 'district', 'city-state', 'state'], filled: ['district', 'state', 'city-state', 'zip'],
    pickSymbol: ['zip', 'state', 'city-state', 'district'], pickFilled: ['state', 'district', 'city-state', 'zip']};
  const geoRank = (field, filled, picking) => {
    const order = picking ? (filled ? GEO_ORDER.pickFilled : GEO_ORDER.pickSymbol) : (filled ? GEO_ORDER.filled : GEO_ORDER.symbol);
    const at = order.indexOf(geoKind(field));
    return at < 0 ? 99 : at;
  };
  // Postal code, Census state FIPS and name for every US state and territory
  // the Census boundary layers carry.
  const US_STATES = ('AL01Alabama|AK02Alaska|AZ04Arizona|AR05Arkansas|CA06California|CO08Colorado|CT09Connecticut|' +
    'DE10Delaware|DC11District of Columbia|FL12Florida|GA13Georgia|HI15Hawaii|ID16Idaho|IL17Illinois|IN18Indiana|' +
    'IA19Iowa|KS20Kansas|KY21Kentucky|LA22Louisiana|ME23Maine|MD24Maryland|MA25Massachusetts|MI26Michigan|' +
    'MN27Minnesota|MS28Mississippi|MO29Missouri|MT30Montana|NE31Nebraska|NV32Nevada|NH33New Hampshire|' +
    'NJ34New Jersey|NM35New Mexico|NY36New York|NC37North Carolina|ND38North Dakota|OH39Ohio|OK40Oklahoma|' +
    'OR41Oregon|PA42Pennsylvania|RI44Rhode Island|SC45South Carolina|SD46South Dakota|TN47Tennessee|TX48Texas|' +
    'UT49Utah|VT50Vermont|VA51Virginia|WA53Washington|WV54West Virginia|WI55Wisconsin|WY56Wyoming|' +
    'AS60American Samoa|GU66Guam|MP69Northern Mariana Islands|PR72Puerto Rico|VI78U.S. Virgin Islands')
    .split('|').map(s => ({code: s.slice(0, 2), fips: s.slice(2, 4), name: s.slice(4)}));
  const STATE_BY_CODE = new Map(US_STATES.map(s => [s.code, s]));
  const STATE_BY_NAME = new Map(US_STATES.map(s => [s.name.toUpperCase(), s]));
  const stateOf = text => {
    const value = String(text == null ? '' : text).trim().toUpperCase();
    return STATE_BY_CODE.get(value) || STATE_BY_NAME.get(value) || null;
  };
  // A five-digit ZIP from a ZIP, ZIP+4 or a ZIP whose leading zero a
  // spreadsheet dropped (4 or 8 digits); '' for anything else.
  const zipOf = token => {
    const digits = String(token).trim().replace(/^(\d{5})-(\d{4})$/, '$1$2');
    if (!/^\d+$/.test(digits)) return '';
    const padded = digits.length === 4 || digits.length === 8 ? '0' + digits : digits;
    const zip = padded.length === 5 || padded.length === 9 ? padded.slice(0, 5) : '';
    return zip === '00000' ? '' : zip;
  };
  // 'MN-05' from 'MN-05', 'MN05', 'MN-AL', or a bare district number with its
  // row's state; district 0 and at-large are '00', as the Census codes them.
  const districtOf = (token, stateCell) => {
    const text = String(token == null ? '' : token).trim().toUpperCase();
    let found = /^([A-Z]{2})[-\s]?(\d{1,2}|AL)$/.exec(text), state = null, number = null;
    if (found) { state = stateOf(found[1]); number = found[2]; }
    else if ((found = /^(\d{1,2})(?:\.0+)?$/.exec(text)) || text === 'AL') {
      state = stateOf(stateCell); number = found ? found[1] : 'AL';
    }
    if (!state || number == null) return '';
    return state.code + '-' + (number === 'AL' ? '00' : number.padStart(2, '0'));
  };
  const NO_PLACE = '(No place)', SEVERAL_PLACES = '(Several places)';
  // The one place a worksheet cell names. A cell naming several different
  // places is '(Several places)', or every place ('a; b') when the reader
  // split multi-value cells, for the engine to split as it splits any cell.
  function placeOf(kind, cell, stateCell, split) {
    const tokens = String(cell == null ? '' : cell).split(';').map(s => s.trim()).filter(Boolean);
    const read = kind === 'zip' ? zipOf
      : kind === 'state' ? t => (stateOf(t) || {}).code || ''
      : kind === 'city-state' ? t => (stateOf(t.split(',').pop()) || {}).code || ''
      : kind === 'district' ? t => districtOf(t, stateCell)
      : () => '';
    const places = [...new Set(tokens.map(read).filter(Boolean))];
    if (!places.length) return NO_PLACE;
    if (places.length === 1) return places[0];
    return split ? places.join('; ') : SEVERAL_PLACES;
  }
  // The worksheet with one more column: each row's place. The engine then
  // aggregates the sheet's own measure per place, so an average or a median is
  // taken over the place's rows, never added up from pieces.
  function placeData(data, map, split) {
    const column = data.columns.length;
    const stateColumn = Number.isInteger(map.stateColumn) ? map.stateColumn : -1;
    const rows = data.rows.map(row => row.concat([placeOf(map.kind, row[map.column],
      stateColumn >= 0 ? row[stateColumn] : null, split)]));
    const columns = data.columns.concat([{index: column, name: map.name, type: 'category'}]);
    return {data: Object.assign({}, data, {columns: columns, rows: rows}), column: column};
  }
  // The configuration a worksheet map is built from: its first measure over
  // every place (no top-N cutoff), with the sheet's filters and row range.
  function mapConfig(config, placeColumn) {
    const out = {type: 'bar', x: placeColumn, y: config.y, dimensions: [placeColumn], aggregation: config.aggregation,
      transform: 'none', period: config.period, horizon: config.horizon, start: config.start, end: config.end,
      limit: config.limit, maxGroups: 'all', splitMulti: !!config.splitMulti, series: -1, filters: config.filters, lenient: true};
    if (Array.isArray(config.measures) && config.measures.length) out.measures = [config.measures[0]];
    return out;
  }
  // Engine groups (one per place) as MentatContributionMap groups.
  function mapGroups(result, kind) {
    return ((result && result.groups) || []).filter(g => !g.other).map(g => {
      const label = String(g.label);
      const base = {label: label, value: typeof g.value === 'number' && Number.isFinite(g.value) ? g.value : 0,
        records: Number.isFinite(g.n) ? g.n : 0};
      if (label === NO_PLACE || label === SEVERAL_PLACES) {
        return Object.assign(base, {unplaced: label === NO_PLACE ? 'no_place' : 'several_places'});
      }
      if (kind === 'zip') return Object.assign(base, {zip5: label});
      if (kind === 'district') {
        const state = STATE_BY_CODE.get(label.slice(0, 2));
        return Object.assign(base, {state: label.slice(0, 2), district: state ? state.fips + label.slice(3) : ''});
      }
      return Object.assign(base, {state: label});
    });
  }

  /* -------------------------------------------------------------- show me */

  const tile = (id, label, requirement, rule) => Object.assign(
    {id: id, label: label, requirement: requirement, mark: '', note: '',
     needDimensions: 0, needMeasures: 0, needTime: false}, rule);

  // Paul, 2026-09-23: "...all graph types properly register and nothing is
  // logically constrained". Every tile is a real mark in both sources and is
  // never greyed: the requirement is what the tile PREFERS, and a click draws
  // with what is on the shelves, seeding what it can and letting the compiler
  // pick the rest (and say so).
  const SHOW_ME = [
    tile('text-table', 'Text table', '1 or more Dimensions, 1 or more Measures', {mark: 'text', needDimensions: 1, needMeasures: 1}),
    tile('heat-map', 'Heat map', '1 or more Dimensions, 1 or 2 Measures', {mark: 'heatmap', needDimensions: 2, needMeasures: 1}),
    tile('highlight-table', 'Highlight table', '1 or more Dimensions, 1 Measure', {mark: 'highlight', needDimensions: 2, needMeasures: 1}),
    tile('symbol-map', 'Symbol map', '1 geographic Dimension, 0 to 2 Measures', {mark: 'map', needDimensions: 1,
      note: 'Draws from a ZIP, state, congressional district or city field; a worksheet with none shows the same groups as bars.'}),
    tile('filled-map', 'Filled map', '1 geographic Dimension, 0 or 1 Measures', {mark: 'filled-map', needDimensions: 1,
      note: 'Fills states or districts from the sheet’s place field; a worksheet with none shows the same groups as bars.'}),
    tile('pie-chart', 'Pie chart', '1 or more Dimensions, 1 or 2 Measures', {mark: 'pie', needDimensions: 1, needMeasures: 1,
      note: 'Shares need nonnegative values; negative groups are left out and counted in a note.'}),
    tile('horizontal-bars', 'Horizontal bars', '0 or more Dimensions, 1 or more Measures', {mark: 'bar', needDimensions: 1, needMeasures: 1}),
    tile('stacked-bars', 'Stacked bars', '1 or more Dimensions, 1 or more Measures', {mark: 'stacked', needDimensions: 2, needMeasures: 1,
      note: 'Each bar stacks its Colour breakdown, or its measures when there are several.'}),
    tile('side-by-side-bars', 'Side-by-side bars', '1 or more Dimensions, 1 or more Measures', {mark: 'bar', needDimensions: 2, needMeasures: 1}),
    tile('treemap', 'Treemap', '1 or more Dimensions, 1 or 2 Measures', {mark: 'treemap', needDimensions: 1, needMeasures: 1}),
    tile('circle-views', 'Circle views', '1 or more Dimensions, 1 or more Measures', {mark: 'dot', needDimensions: 1, needMeasures: 1,
      note: 'One circle per group at its value.'}),
    tile('side-by-side-circles', 'Side-by-side circles', '1 or more Dimensions, 1 or more Measures', {mark: 'series-dot', needDimensions: 2, needMeasures: 1,
      note: 'One circle series per Colour member.'}),
    tile('lines-continuous', 'Lines (continuous)', '1 Date, 1 or more Measures', {mark: 'line', needDimensions: 1, needMeasures: 1, needTime: true}),
    tile('lines-discrete', 'Lines (discrete)', '1 Date, 1 or more Measures', {mark: 'line', needDimensions: 1, needMeasures: 1, needTime: true,
      note: 'Groups the dates into calendar-year or election-cycle periods.'}),
    tile('dual-lines', 'Dual lines', '1 Date, 2 Measures', {mark: 'dual-line', needDimensions: 1, needMeasures: 2, needTime: true,
      note: 'Two measures on two axes, or the Colour breakdown on one.'}),
    tile('area-continuous', 'Area chart (continuous)', '1 Date, 1 or more Measures', {mark: 'area', needDimensions: 1, needMeasures: 1, needTime: true}),
    tile('area-discrete', 'Area chart (discrete)', '1 Date, 1 or more Measures', {mark: 'area', needDimensions: 1, needMeasures: 1, needTime: true,
      note: 'Groups the dates into calendar-year or election-cycle periods.'}),
    tile('dual-combination', 'Dual combination', '1 Date, 2 Measures', {mark: 'combination', needDimensions: 1, needMeasures: 2, needTime: true,
      note: 'The first measure as bars, the second as a line on its own axis.'}),
    tile('scatter-plot', 'Scatter plot', '0 or more Dimensions, 2 to 4 Measures', {mark: 'circle', needMeasures: 2}),
    tile('histogram', 'Histogram', '0 Dimensions, 1 Measure', {mark: 'histogram', needMeasures: 1}),
    tile('box-and-whisker', 'Box-and-whisker', '0 or more Dimensions, 1 or more Measures', {mark: 'box', needMeasures: 1}),
    tile('gantt', 'Gantt', '1 Date, 0 or 1 Measures', {mark: 'gantt', needDimensions: 1,
      note: 'First-to-last observed date of each group.'}),
    tile('bullet-graph', 'Bullet graph', '0 or more Dimensions, 2 Measures', {mark: 'bullet', needMeasures: 2}),
    tile('packed-bubbles', 'Packed bubbles', '1 or more Dimensions, 1 or 2 Measures', {mark: 'bubbles', needDimensions: 1, needMeasures: 1})
  ];

  function showMeSelection(state, columns, selected) {
    const meta = classifyFields(columns, state && state.types);
    const indices = [];
    const add = value => {
      const p = pill(value);
      if (p && indices.indexOf(p.column) === -1) indices.push(p.column);
    };
    (state && state.columns || []).forEach(add);
    (state && state.rows || []).forEach(add);
    const marks = (state && state.marks) || {};
    ['color', 'size', 'label'].forEach(key => add(marks[key]));
    (marks.detail || []).forEach(add);
    (selected || []).forEach(add);
    const fields = indices.map(index => fieldAt(meta, index)).filter(Boolean);
    return {
      fields: fields,
      dimensions: fields.filter(f => f.role === 'dimension').length,
      measures: fields.filter(f => f.role === 'measure').length,
      times: fields.filter(f => f.role === 'dimension' && f.isTime).length
    };
  }

  const plural = (n, word) => n + ' ' + word + (n === 1 ? '' : 's');

  // Every tile is enabled. `fits` says whether the shelves already hold what
  // the tile prefers; `fill` says, in the reader's words, what a click will
  // pick from the source when they do not.
  function showMeEligibility(selection) {
    return SHOW_ME.map(t => {
      const missing = [];
      if (selection.dimensions < t.needDimensions) missing.push(plural(t.needDimensions - selection.dimensions, 'dimension'));
      if (selection.measures < t.needMeasures) missing.push(plural(t.needMeasures - selection.measures, 'measure'));
      if (t.needTime && selection.times < 1) missing.push('a date, year or election-cycle dimension');
      return {id: t.id, label: t.label, requirement: t.requirement, note: t.note, mark: t.mark, enabled: true, reason: '',
        fits: missing.length === 0, missing: missing,
        fill: missing.length ? 'Draws with the fields on the shelves and picks ' + missing.join(' and ') + ' from the source' : ''};
    });
  }

  // A tile changes the mark and keeps every pill, filter, aggregate and
  // encoding on the sheet (census B-S28). Shelves that are empty are seeded
  // from the fields in use, then from the source itself, so a click on an
  // empty sheet still draws.
  function showMeApply(tileId, state, columns, selected) {
    const t = SHOW_ME.find(item => item.id === tileId);
    if (!t) return clone(state);
    const meta = classifyFields(columns, state && state.types);
    const selection = showMeSelection(state, columns, selected);
    const next = clone(state);
    next.marks = Object.assign({}, next.marks, {type: t.mark});
    if (tileId === 'horizontal-bars') next.marks.orientation = 'horizontal';
    else if (next.marks.orientation) delete next.marks.orientation;
    // Discrete lines and areas are period totals; the continuous tiles take a
    // period grouping away again. Nothing else about the analytics changes.
    const transform = (next.analytics || {}).transform;
    if (['lines-discrete', 'area-discrete'].includes(tileId)) next.analytics = Object.assign({}, next.analytics, {transform: 'annual'});
    else if (['lines-continuous', 'area-continuous'].includes(tileId) && transform === 'annual') next.analytics = Object.assign({}, next.analytics, {transform: 'none'});
    if (shelf(state.columns).length || shelf(state.rows).length) return next;

    const usable = f => !f.hidden;
    const inUse = selection.fields;
    const dimensions = [...inUse.filter(f => f.role === 'dimension'),
      ...meta.dimensions.filter(f => usable(f) && !inUse.includes(f))];
    const plain = dimensions.filter(f => !f.isTime && !f.isIdentifier);
    const times = dimensions.filter(f => f.isTime);
    const measures = [...inUse.filter(f => f.role === 'measure'),
      ...meta.measures.filter(f => usable(f) && !inUse.includes(f))];
    const measurePill = index => {
      const existing = shelf(state.columns).concat(shelf(state.rows)).find(p => p.column === index);
      return {column: index, aggregation: existing ? existing.aggregation : 'sum'};
    };
    const dim = f => ({column: f.index, aggregation: 'sum'});
    const dimension = position => (plain[position] || dimensions.filter(f => !plain.includes(f))[position - plain.length] || null);
    const colour = () => {
      if (next.marks.color != null) return;
      const used = next.columns.concat(next.rows).map(p => p.column);
      // A date belongs on the axis, so Colour prefers a plain dimension.
      const candidate = plain.find(f => used.indexOf(f.index) === -1)
        || dimensions.find(f => used.indexOf(f.index) === -1);
      if (candidate) next.marks.color = {column: candidate.index, aggregation: 'sum'};
    };
    const axis = preferTime => (preferTime ? times[0] : null) || dimension(0) || times[0] || null;
    next.columns = []; next.rows = [];
    const id = t.id;
    if (id === 'horizontal-bars') {
      if (dimension(0)) next.rows = [dim(dimension(0))];
      if (measures[0]) next.columns = [measurePill(measures[0].index)];
    } else if (id === 'scatter-plot' || id === 'bullet-graph') {
      if (measures[0]) next.columns = [measurePill(measures[0].index)];
      if (measures[1]) next.rows = [measurePill(measures[1].index)];
      if (id === 'bullet-graph' && dimension(0)) next.columns.unshift(dim(dimension(0)));
    } else if (id === 'histogram') {
      if (measures[0]) next.rows = [measurePill(measures[0].index)];
    } else if (['lines-continuous', 'lines-discrete', 'dual-lines', 'area-continuous', 'area-discrete',
      'dual-combination', 'gantt'].includes(id)) {
      const x = axis(true);
      if (x) next.columns = [dim(x)];
      if (measures[0]) next.rows = [measurePill(measures[0].index)];
      if ((id === 'dual-lines' || id === 'dual-combination') && measures[1]) next.rows.push(measurePill(measures[1].index));
      if (id === 'dual-lines' && !measures[1]) colour();
    } else if (id === 'heat-map' || id === 'highlight-table') {
      if (dimension(0)) next.columns = [dim(dimension(0))];
      if (dimension(1)) next.rows = [dim(dimension(1))];
      if (measures[0]) next.rows.push(measurePill(measures[0].index));
    } else if (id === 'symbol-map' || id === 'filled-map') {
      const place = dimensions.filter(f => geoKind(f)).sort((a, b) => geoRank(a, id === 'filled-map', true) - geoRank(b, id === 'filled-map', true))[0]
        || dimension(0);
      if (place) next.columns = [dim(place)];
      if (measures[0]) next.rows = [measurePill(measures[0].index)];
    } else {
      // text, pie, stacked, side-by-side, treemap, circles, box, bubbles
      if (dimension(0)) next.columns = [dim(dimension(0))];
      if (measures[0]) next.rows = [measurePill(measures[0].index)];
      if (['stacked-bars', 'side-by-side-bars', 'side-by-side-circles'].includes(id)) colour();
    }
    return next;
  }

  const RECOMMENDED_TILE = {bar: 'horizontal-bars', pie: 'pie-chart', line: 'lines-continuous',
    scatter: 'scatter-plot', box: 'box-and-whisker', histogram: 'histogram'};

  function recommendedTile(columns) {
    const choices = math.recommend(columns || []) || [];
    for (const choice of choices) if (RECOMMENDED_TILE[choice.type]) return RECOMMENDED_TILE[choice.type];
    return '';
  }

  /* --------------------------------------------------------------- filters */

  // Include/exclude member lists join the four original scalar operations. A
  // list filter with no members chosen is not a filter at all: it is dropped
  // before it reaches either engine, so an empty choice never means "nothing".
  const FILTER_OPS = [['equals', 'Equals'], ['contains', 'Contains'], ['gte', 'At least'],
    ['lte', 'At most'], ['between', 'Between'], ['in', 'Is one of'], ['notin', 'Is not one of']];
  const LIST_OPS = ['in', 'notin'];
  const RANGE_OPS = ['between'];

  const filterValues = filter => !filter ? []
    : Array.isArray(filter.value) ? filter.value.map(String)
    : filter.value == null || filter.value === '' ? [] : [String(filter.value)];

  function filterActive(filter) {
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
  }

  function normalizeFilter(filter) {
    const op = FILTER_OPS.some(o => o[0] === (filter && filter.op)) ? filter.op : 'equals';
    const out = {column: Number(filter.column), op: op,
      value: LIST_OPS.indexOf(op) !== -1 ? filterValues(filter)
        : RANGE_OPS.indexOf(op) !== -1 ? filterBounds(filter)
        : String(filter && filter.value == null ? '' : filter.value)};
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
    if (RANGE_OPS.indexOf(filter.op) !== -1) {
      const [low, high] = filterBounds(filter);
      if (low !== '' && high !== '') return name + ' ' + show(low) + ' to ' + show(high);
      if (low !== '') return name + ' \u2265 ' + show(low);
      if (high !== '') return name + ' \u2264 ' + show(high);
      return name + ': any value';
    }
    if (LIST_OPS.indexOf(filter.op) !== -1) {
      if (!values.length) return name + ': any value';
      const total = Number.isFinite(Number(memberCount)) && Number(memberCount) >= values.length ? Number(memberCount) : null;
      const listed = values.length <= 3 ? values.join(', ')
        : total ? values.length + ' of ' + total + ' values' : values.length + ' values';
      return name + (filter.op === 'in' ? ': ' : ' excludes ') + listed;
    }
    if (filter.op === 'contains') return name + ' contains ' + show(filter.value);
    if (filter.op === 'gte') return name + ' \u2265 ' + show(filter.value);
    if (filter.op === 'lte') return name + ' \u2264 ' + show(filter.value);
    return name + ' = ' + show(filter.value);
  }

  /* ---------------------------------------------------- measures and types */

  // Only offer what the active engine can actually compute. The verified server
  // aggregates one money column six ways; every other verified measure is a
  // source aggregate that is already defined, so it has no aggregation menu.
  const VERIFIED_AGGREGATED = 'amount';

  // A worksheet measure offers every aggregation, Count distinct included; a
  // text or date column read as a measure is counted (Count, Count distinct).
  // The verified server has no distinct count of money, so amount keeps its six.
  const COUNTED = AGGREGATIONS.filter(a => a[0] === 'count' || a[0] === 'countd');
  function aggregationsFor(field, engine) {
    if (!field || field.role !== 'measure') return [];
    if (engine !== 'verified') return field.type === 'number' ? AGGREGATIONS.slice() : COUNTED.slice();
    return field.id === VERIFIED_AGGREGATED ? AGGREGATIONS.filter(a => a[0] !== 'countd') : [];
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
  const DATE_PARTS = [['cycle', 'Election cycle'], ['year', 'Year'], ['quarter', 'Quarter'],
    ['month', 'Month'], ['date', 'Exact date']];
  const DATE_FIELD_IDS = DATE_PARTS.map(part => part[0]);

  // Date-likeness is read from the catalog's own date hierarchy first. The
  // detected time flag is only a fallback, so a date part cannot disappear
  // because that flag was lost somewhere between the catalog and the pill.
  const isDateLike = field => !!field && field.role === 'dimension' &&
    (DATE_FIELD_IDS.indexOf(field.id) !== -1 || !!field.isTime);

  function datePartsFor(field, columns, engine, state) {
    if (!isDateLike(field)) return [];
    if (engine === 'verified') {
      const meta = classifyFields(columns);
      return DATE_PARTS
        .map(([id, label]) => {
          const target = meta.fields.find(f => f.id === id);
          return {id: id, label: label, column: target ? target.index : -1, current: field.id === id};
        })
        .filter(part => part.column >= 0);
    }
    // A worksheet has one date column, so the part is the period the existing
    // transform groups by rather than a column the worksheet does not have.
    const analytics = (state && state.analytics) || {};
    const grouped = analytics.transform === 'annual';
    return [['cycle', 'Election cycle'], ['year', 'Year']]
      .map(([id, label]) => ({id: id, label: label, column: field.index, current: grouped && analytics.period === id}));
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

  /* -------------------------------------------------------- result helpers */

  const groupValue = group => group.value != null ? group.value : group.median != null ? group.median : 0;

  // Paul, 2026-09-23: "nothing is logically constrained". Sort works on every
  // mark, time axes included (census B-S15, contract W13); 'none' is the
  // engine's own order, which on a time axis is chronological, so a time view
  // still opens in time order. sortLocked is kept for its callers and answers
  // false for every view.
  const sortLocked = () => false;
  // 'az' and 'za' order the groups by their label (contract W13 {by: 'label'}).
  const SORTS = ['none', 'asc', 'desc', 'az', 'za'];

  function sortResult(result, direction, options) {
    if (!result || !Array.isArray(result.groups)) return result;
    const byLabel = (options && options.by === 'label') || direction === 'az' || direction === 'za';
    const ascending = direction === 'asc' || direction === 'az';
    if (!['asc', 'desc', 'az', 'za'].includes(direction)) return result;
    // A scatter's points are not an axis order; there is nothing to reorder.
    if (result.type === 'scatter') return result;
    const size = group => seriesResult(result)
      ? (group.values || []).reduce((total, v) => total + (v.value == null ? 0 : v.value), 0)
      : groupValue(group);
    const compare = byLabel
      ? (a, b) => String(a.label).localeCompare(String(b.label), undefined, {numeric: true})
      : (a, b) => size(a) - size(b);
    // An Other rollup is the tail the engine folded away, not a member of the
    // view, so it keeps the last position however the real groups are ordered.
    const rollup = result.groups.filter(g => g.other);
    const groups = result.groups.filter(g => !g.other)
      .sort((a, b) => ascending ? compare(a, b) : compare(b, a));
    return Object.assign({}, result, {groups: groups.concat(rollup)});
  }

  // Mark values in the order the renderer appends them, so a caller can label
  // marks without knowing how the SVG was drawn. Empty where labels do not fit.
  // A result is drawn as series only when every group carries its per-series
  // values. Scatter (points, no groups) and box (groups without values) results
  // also name their Colour members in `series` (contract W11) and are not series
  // results here; this is the predicate chartSVG and tableRows use.
  const seriesResult = result => !!(result && result.series && Array.isArray(result.groups) &&
    result.groups.every(g => g && Array.isArray(g.values)));

  function markValues(result) {
    if (!result) return [];
    if (seriesResult(result)) return result.groups.reduce((all, g) => all.concat(g.values.filter(v => v.value != null).map(v => v.value)), []);
    if (['scatter', 'box', 'pie', 'doughnut', 'radar'].indexOf(result.type) !== -1) return [];
    return (result.groups || []).map(g => g.value);
  }

  // A view separated by Colour or by several measures gets the mean and median
  // of every mark it draws (census B-S19): the rule is labelled as such, so it
  // is never read as one series' own average.
  function referenceValues(result, analytics) {
    const wanted = analytics || {};
    const values = markValues(result).filter(v => typeof v === 'number' && Number.isFinite(v));
    const lines = [];
    if (!values.length) return lines;
    const every = seriesResult(result) ? ' of every mark' : '';
    if (wanted.average) lines.push({kind: 'average', label: 'Average' + every, value: values.reduce((a, b) => a + b, 0) / values.length});
    if (wanted.median) lines.push({kind: 'median', label: 'Median' + every, value: math.quantile(values.slice().sort((a, b) => a - b), .5)});
    return lines;
  }

  // A grand total only means something when the marks are additive parts of one
  // whole. Independent series, bin counts, five-number summaries, shares of a
  // circle and a sum of means are not, so the studio says why instead of
  // printing a number that reads as money.
  const UNTOTALLED = ['histogram', 'scatter', 'box', 'pie', 'doughnut', 'radar'];

  function totalNote(result, config) {
    if (!result) return '';
    if (result.totalRefusal) return result.totalRefusal;
    if (result.split) return 'Grand total is not shown: split coverage groups can overlap.';
    if (['yoy', 'change'].includes(result.transform || config?.transform)) return 'Grand total is not shown for percentages or period changes.';
    if (result.accounting?.safe_to_sum === false) return result.accounting.reason || 'Grand total is not shown for this accounting grain.';
    if (seriesResult(result)) return 'Grand total is not shown: series are independent.';
    if (result.type === 'histogram') return 'Grand total is not shown for histograms (bins are row counts).';
    if (UNTOTALLED.indexOf(result.type) !== -1) return 'Grand total is not shown for ' + result.type + ' views.';
    if (config && ['sum', 'count'].indexOf(config.aggregation) === -1) return 'Grand total is only available for SUM and COUNT.';
    return '';
  }

  function grandTotal(result, config) {
    if (totalNote(result, config)) return null;
    if ((result?.transform || config?.transform) === 'forecast') return Number.isFinite(result.observedTotal) ? result.observedTotal : null;
    const values = markValues(result).filter(v => typeof v === 'number' && Number.isFinite(v));
    return values.length ? values.reduce((a, b) => a + b, 0) : null;
  }

  const AGGREGATION_LABEL = {sum: 'SUM', mean: 'AVG', count: 'CNT', median: 'MED', min: 'MIN', max: 'MAX', countd: 'CNTD'};

  function rowsToMarksSummary(result, config, columns) {
    if (!result || !config) return null;
    const meta = classifyFields(columns);
    const measure = fieldAt(meta, config.y);
    const marks = result.type === 'scatter' ? (result.points || []).length
      : seriesResult(result) ? result.groups.reduce((n, g) => n + g.values.filter(v => v.value != null).length, 0)
      : (result.groups || []).length;
    const viewColumns = result.type === 'scatter' ? 1 : (result.groups || []).length;
    const viewRows = result.series ? result.series.length : 1;
    const total = grandTotal(result, config);
    const name = config.aggregation === 'count' && config.y === -1 ? 'rows' : measure ? measure.name : 'value';
    return {
      marks: marks,
      viewRows: viewRows,
      viewColumns: viewColumns,
      selected: result.selected == null ? null : result.selected,
      excluded: result.excluded == null ? null : result.excluded,
      measureLabel: ((result.transform || config.transform) === 'forecast' ? 'Observed ' : '') +
        ((result.transform || config.transform) === 'yoy' ? 'YoY %(' + name + ')' :
        (result.transform || config.transform) === 'change' ? 'Period change(' + name + ')' :
        (result.split ? 'Coverage ' : '') + AGGREGATION_LABEL[config.aggregation] + '(' + name + ')'),
      total: total
    };
  }

  /* ------------------------------------------- what a payload says about its source */

  // The server keeps a saved view's source, and a briefing item's source and
  // provenance, as objects, and replaces anything else with an empty one. A
  // caption sent bare is therefore either refused outright (a saved view came
  // back 400) or silently thrown away (a briefing item's workbook digest, which
  // then printed as "[object Obje" in every deck). The shapes are built here,
  // in the one module both the browser and the test runner can load, so a test
  // can read exactly what the client will put on the wire without a document.

  // The caption a reader sees for a source, from any shape it has ever had:
  // today's object, an older bare string, or nothing at all. It never hands an
  // object to string concatenation.
  function sourceLabelOf(value) {
    if (typeof value === 'string') return value;
    if (!value || typeof value !== 'object') return '';
    return value.label || value.datasetLabel || value.reportName || '';
  }

  // A source known only by its caption - a view recovered from the old
  // browser-local store, which never recorded anything else.
  function captionSource(label) {
    return label ? {label: String(label)} : {};
  }

  // The same recovery, from a store key rather than a resolved label. This
  // module never touches the network, so a contributions key
  // ('contributions|<dataset>|<sha>') cannot look the dataset up in a
  // catalog - but the dataset id IS the industry label (S4_DESIGN.md section
  // 0.2), so the key alone is enough to recover industry and dataset instead
  // of losing them the way a bare caption always did.
  function captionSourceForKey(key) {
    const parts = String(key || '').split('|');
    if (parts[0] === 'contributions') {
      const label = parts[1] || '';
      return label ? {label: label, dataset: label, industry: label} : {};
    }
    return captionSource(parts.filter(Boolean).pop() || '');
  }

  // What a saved view carries: enough to name the report, its digest and the
  // folder it came from a year from now, plus the caption the menu prints.
  function viewSourceRecord(state, chosen) {
    const source = state || {};
    const record = {};
    const label = chosen ? (chosen.label || chosen.id) : (source.reportName || '');
    if (label) record.label = label;
    for (const key of ['reportName', 'sha256', 'runName', 'sheet', 'mode', 'dataset', 'industry']) {
      if (source[key]) record[key] = source[key];
    }
    if (chosen) {
      record.dataset = chosen.id;
      if (chosen.label) record.datasetLabel = chosen.label;
      // The DE-021 fix: a chosen catalog entry resolves to an industry,
      // falling back to its id when an older catalog has not been extended
      // with the field yet (id and industry are the same string today -
      // S4_DESIGN.md section 0.2). A catalog entry with neither sets no key:
      // an empty industry is the shape studio_api.json refuses, so writing
      // one here would send the server a payload it must reject.
      const industry = chosen.industry || chosen.id;
      if (typeof industry === 'string' && industry) record.industry = industry;
    }
    return record;
  }

  // What a chart carries into the briefing, and from there into a slide.
  function chartSourceRecord(state) {
    const source = state || {};
    const label = source.reportName || '';
    const record = {label: label, reportName: label, runName: source.runName || '',
      sheet: source.sheet || '', mode: source.mode || '', dataset: source.dataset || ''};
    // Every worksheet-mode chart reaches the briefing through here, and an
    // empty industry is exactly the payload studio_api.json's third negative
    // control says must be refused. The key is written only when it carries
    // a value - the same truthy-only rule viewSourceRecord above follows.
    if (source.industry) record.industry = source.industry;
    return record;
  }

  function chartProvenanceRecord(state, sha, generatedAt) {
    const label = (state || {}).reportName || '';
    return {sha: sha || '', reportName: label, source: label,
      generatedAt: generatedAt || new Date().toISOString()};
  }

  /* --------------------------------------------------------- snapshot registry */

  const BUILD_STAMP_RE = /^[0-9a-f]{64}$/;

  // Reads the snapshot registry envelope (contracts/snapshot_registry.json)
  // or the bare `industries[]` array GET /api/contributions/session folds it
  // into, and throws in plain English on anything that is not a usable
  // entry. Consumed by industry_scope.resolve server-side and by the picker
  // here; both need the same refusal the first time a bad entry is seen,
  // not a silent `undefined` two calls later.
  // The board a saved view may carry (studio_api.json v2): 1, 2 or 4 tiles, each
  // slot holding one sheet or standing empty. Returns the board, or null when the
  // view has none and when the one it has does not describe its own sheets - a
  // dangling index would draw a tile from a sheet that is not there. server.py's
  // save_view applies the same rules, so a board that opens here is a board that
  // saves, and a malformed one is dropped on open rather than failing the open.
  function normalizeBoard(view) {
    const board = view && view.board;
    if (!board || typeof board !== 'object' || Array.isArray(board)) return null;
    const tiles = board.tiles;
    if (typeof tiles !== 'number' || ![1, 2, 4].includes(tiles)) return null;
    const slots = board.slots;
    if (!Array.isArray(slots) || slots.length !== tiles) return null;
    const sheets = (view && view.sheets) || [];
    const placed = new Set();
    for (const slot of slots) {
      if (slot === null) continue;
      if (typeof slot !== 'number' || !Number.isInteger(slot) || slot < 0 || slot >= sheets.length) return null;
      if (placed.has(slot)) return null;
      placed.add(slot);
    }
    return {tiles: tiles, slots: slots.slice()};
  }

  function parseSnapshotRegistry(payload) {
    const list = Array.isArray(payload) ? payload
      : (payload && Array.isArray(payload.snapshots)) ? payload.snapshots
      : null;
    if (!list) throw new Error('The snapshot registry must be a list of entries or an envelope with a snapshots array.');
    for (const entry of list) {
      if (!entry || typeof entry !== 'object') {
        throw new Error('Each snapshot entry must be an object.');
      }
      if (typeof entry.industry !== 'string' || !entry.industry) {
        throw new Error('Each snapshot entry needs a non-empty industry label.');
      }
      if (typeof entry.slug !== 'string') {
        throw new Error(entry.industry + ' is missing its slug.');
      }
      if (typeof entry.available !== 'boolean') {
        throw new Error(entry.industry + ' is missing its available flag.');
      }
      // A workbook the console could not open has no hash and therefore no
      // stamp (contracts/snapshot_registry.json v2, the Telecom example). That
      // is the ONLY entry allowed to omit it: an entry claiming to be available
      // without a stamp is negative_controls[0], and still throws here.
      const unreadable = entry.available === false && entry.build_stamp == null;
      if (!unreadable && (typeof entry.build_stamp !== 'string' || !BUILD_STAMP_RE.test(entry.build_stamp))) {
        throw new Error(entry.industry + ' is missing a valid build_stamp.');
      }
      if (entry.workbook && typeof entry.workbook === 'object' && typeof entry.workbook.name === 'string'
          && /[\\/:]/.test(entry.workbook.name)) {
        throw new Error(entry.industry + '’s workbook name must be relative to the report directory, not a path.');
      }
      // Not in the field list S4_DESIGN.md section 2 gives this function, but
      // required to fail negative_controls[2] in contracts/snapshot_registry.json
      // (an entry whose industry is the collector slug 'credit-unions' while
      // dataset still reads the published label 'Credit Union'): section 1
      // states dataset carries "the same value as industry", so the two
      // disagreeing is exactly the DE-021 shape this contract exists to catch.
      if (typeof entry.dataset === 'string' && entry.dataset && entry.dataset !== entry.industry) {
        throw new Error(entry.industry + ' does not match its dataset (' + entry.dataset + ').');
      }
      // Also not in that field list, but required to fail negative_controls[4]
      // (a companion sent as a bare filename string): section 2 defines
      // companion, when present, as an object carrying its own sha256/bytes/
      // modified_at/lineage_matches, the same DE-021 shape as industry-as-object.
      if (entry.companion != null && typeof entry.companion !== 'object') {
        throw new Error(entry.industry + '’s companion must be an object, not a bare filename.');
      }
    }
    return list;
  }

  const api = {
    AGGREGATIONS, AGGREGATION_IDS, MARK_TYPES, MARK_IDS, TRANSFORMS, SHOW_ME, STUDIO_GROUP_LIMIT,
    EXTRA_MARK_TYPES, ALL_MARK_TYPES, ALL_MARK_IDS, markLabel, groupLimitOf, SORTS,
    FILTER_OPS, LIST_OPS, RANGE_OPS, MEASURE_PRESETS, DATE_PARTS, COMPANY_OVERVIEW,
    canTreatAs, isDateLike, filterValues, filterActive, filterBounds, normalizeFilter, filterSummary,
    aggregationsFor, measurePresets, applyMeasurePreset, datePartsFor,
    companyOverviewPresets, companyOverviewMissing, companyOverviewSheet,
    classifyFields, fieldAt, paneBuckets, subjectField, pill, shelf, createSheet, clearSheet, swapShelves, sourceKey,
    carriedFilterValue, graphCycleValue, quickAddZone, migrateSheet,
    WORKSHEET_GROUP_LABELS, NO_DATA_WORKBOOK_HINT, COMMITTEE_ACTIVITY_NOTE,
    defaultGuards, committeeActivitySheet, workbookKind, groupWorksheets,
    compileConfig, compileReport, geoKind, placeOf, placeData, mapConfig, mapGroups, NO_PLACE, SEVERAL_PLACES,
    showMeSelection, showMeEligibility, showMeApply, recommendedTile,
    sortResult, sortLocked, markValues, referenceValues, grandTotal, totalNote, rowsToMarksSummary,
    sourceLabelOf, captionSource, captionSourceForKey, viewSourceRecord, chartSourceRecord, chartProvenanceRecord,
    normalizeBoard,
    parseSnapshotRegistry
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.MentatStudioCore = api;
})(globalThis);
