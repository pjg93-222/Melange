/* Chart Studio: shelf state -> chart configuration. Pure functions only; no DOM,
   no network, no timers. Field classification and chart choice come from
   chart-math.js so the rules are never forked. Exercised by node:test. */
(function (root) {
  'use strict';

  const math = (typeof module !== 'undefined' && module.exports) ? require('./chart-math.js') : root.MentatCharts;

  const AGGREGATIONS = [['sum','Sum'],['mean','Mean'],['count','Count'],['median','Median'],['min','Minimum'],['max','Maximum']];
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

  /* ---------------------------------------------------------------- fields */

  // A sheet may re-read a column as a dimension or a measure. The override is
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
      // Identifier columns are real fields; they are folded away until the user
      // asks for them, exactly as recommend() already ignores them.
      field.hidden = column.visible === true ? false : field.isIdentifier && !field.isTime;
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
        field.glyph = field.geographic_role ? 'geo' : field.data_type === 'boolean' ? 'bool'
          : field.role === 'measure' ? '#' : field.type === 'date' ? 'cal' : 'Abc';
      }
    }
    return {
      fields,
      dimensions: fields.filter(f => f.role === 'dimension' && !f.hidden),
      measures: fields.filter(f => f.role === 'measure' && !f.hidden),
      hidden: fields.filter(f => f.hidden)
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

  // The Studio's own default: forty marks is a view a reader can still take in.
  // The engine's default is the legacy callers' sixty, so the Studio never leans
  // on it - every compiled configuration carries its limit explicitly, and the
  // Group limit box in Parameters raises it.
  const STUDIO_GROUP_LIMIT = 60;

  function compileReport(state, columns) {
    const meta = classifyFields(columns, state && state.types);
    const issues = [], notes = [];
    const attach = list => shelf(list)
      .map(p => Object.assign({}, p, {field: fieldAt(meta, p.column)}))
      .filter(p => p.field);
    const columnPills = attach(state.columns);
    const rowPills = attach(state.rows);
    const colDimensions = columnPills.filter(p => p.field.role === 'dimension');
    const colMeasures = columnPills.filter(p => p.field.role === 'measure');
    const rowDimensions = rowPills.filter(p => p.field.role === 'dimension');
    const rowMeasures = rowPills.filter(p => p.field.role === 'measure');
    const allMeasures = colMeasures.concat(rowMeasures);
    const allDimensions = colDimensions.concat(rowDimensions);
    const marks = state.marks || {};
    const markType = MARK_IDS.includes(marks.type) ? marks.type : 'automatic';
    const colorPill = pill(marks.color);
    const color = colorPill ? fieldAt(meta, colorPill.column) : null;
    for (const channel of ['size', 'label', 'tooltip']) {
      const values = Array.isArray(marks[channel]) ? shelf(marks[channel]) : [pill(marks[channel])].filter(Boolean);
      if (values.length) issues.push(channel[0].toUpperCase() + channel.slice(1) + ' is not available for worksheet data. Remove this field or switch to Verified contributions.');
    }
    const details = attach(marks.detail);
    if (details.some(p => p.field.role !== 'dimension')) issues.push('Detail requires dimensions; move a measure to Rows or Columns.');

    const firstDimension = allDimensions[0] || null;
    const firstMeasure = rowMeasures[0] || colMeasures[0] || null;
    const timeDimension = allDimensions.find(p => p.field.isTime) || null;
    // A dimension on Columns draws upright bars; a dimension only on Rows lays
    // the same view on its side, which is what Tableau's Rows shelf means here.
    const orientation = marks.orientation || (colDimensions.length ? 'vertical' : rowDimensions.length ? 'horizontal' : 'none');

    let type = '', xPill = null, yPill = null;

    if (markType === 'automatic') {
      if (colMeasures.length && rowMeasures.length) {
        type = 'scatter'; xPill = colMeasures[0]; yPill = rowMeasures[0];
      } else if (orientation === 'none') {
        if (firstMeasure) { type = 'bar'; yPill = firstMeasure; }
        else issues.push('Add a grouping (company, recipient, cycle) and a dollar measure.');
      } else {
        const dimension = (orientation === 'vertical' ? colDimensions[0] : rowDimensions[0]) || firstDimension;
        const measure = orientation === 'vertical'
          ? (rowMeasures[0] || colMeasures[0] || null)
          : (colMeasures[0] || rowMeasures[0] || null);
        xPill = dimension; yPill = measure;
        type = orientation === 'horizontal' ? 'horizontal' : (dimension?.field.isTime && measure ? 'line' : 'bar');
      }
    } else if (markType === 'circle') {
      type = 'scatter';
      yPill = rowMeasures[0] || allMeasures[0] || null;
      xPill = colMeasures.find(p => !yPill || p.column !== yPill.column)
        || allMeasures.find(p => !yPill || p.column !== yPill.column) || null;
      if (!xPill || !yPill) issues.push('A circle view needs two numeric measures — put one on Columns and one on Rows.');
    } else if (markType === 'histogram') {
      type = 'histogram'; yPill = firstMeasure;
      if (!yPill) issues.push('A histogram needs one numeric measure.');
    } else if (markType === 'box') {
      type = 'box'; xPill = firstDimension; yPill = firstMeasure;
      if (!yPill) issues.push('A box plot needs one numeric measure.');
    } else if (markType === 'line' || markType === 'area') {
      type = markType;
      xPill = timeDimension || firstDimension;
      yPill = firstMeasure;
      if (!xPill) issues.push('A ' + markType + ' mark needs a dimension on Columns or Rows.');
    } else if (markType === 'bar' || markType === 'text') {
      type = orientation === 'horizontal' ? 'horizontal' : 'bar';
      xPill = orientation === 'horizontal' ? (rowDimensions[0] || firstDimension) : (colDimensions[0] || firstDimension);
      yPill = orientation === 'horizontal' ? (colMeasures[0] || rowMeasures[0] || null) : firstMeasure;
      if (!xPill && !yPill) issues.push('Add a grouping (company, recipient, cycle) and a dollar measure.');
    } else {
      type = markType; // pie, doughnut, waterfall, pareto, radar
      xPill = firstDimension; yPill = firstMeasure;
      if (!xPill) issues.push('A ' + markType + ' view needs one dimension.');
    }

    let series = -1;
    if (color && type) {
      const axisColumn = xPill ? xPill.column : -1;
      if (color.role !== 'dimension') notes.push('Colour separates a view by a dimension; ' + color.name + ' is a measure, so it is not applied.');
      else if (color.index === axisColumn) notes.push('Colour repeats the field already on the axis, so it adds nothing to this view.');
      else if (!['bar', 'horizontal', 'line'].includes(type)) notes.push('Colour separates series for bar, horizontal-bar and line marks; this view does not use it.');
      else {
        series = color.index;
        type = type === 'bar' ? 'grouped' : type === 'horizontal' ? 'groupedhorizontal' : 'multiline';
      }
    }

    const analytics = state.analytics || {};
    let transform = TRANSFORMS.includes(analytics.transform) ? analytics.transform : 'none';
    if (transform !== 'none') {
      if (!timeDimension) {
        issues.push('Time analysis needs a date, year or election-cycle dimension on Columns or Rows.');
        transform = 'none';
      } else {
        xPill = timeDimension;
        if (!['bar', 'line', 'area'].includes(type)) {
          notes.push('Time analysis draws bar, line or area marks, so this view is drawn as a line.');
          type = 'line';
        }
        if (series !== -1) {
          notes.push('Time analysis compares periods within one series, so Colour is not applied.');
          series = -1;
        }
      }
    }

    let x = xPill ? xPill.column : -1;
    let y = yPill ? yPill.column : -1;
    let aggregation = yPill ? yPill.aggregation : 'count';
    const selectedAccounting = fieldAt(meta, y)?.accounting;
    if (aggregation === 'sum' && selectedAccounting?.safe_to_sum === false) issues.push(selectedAccounting.reason || 'This raw measure is not safe to sum. Choose the analysis amount.');
    if (type === 'histogram') x = -1;
    if (y === -1) aggregation = 'count';
    if (['scatter', 'box', 'histogram'].includes(type)) {
      if (y === -1) aggregation = 'sum';
      else if (aggregation === 'count') aggregation = 'sum';
    }
    if (y === -1 && ['scatter', 'box', 'histogram'].includes(type)) issues.push('This view plots individual values, so it needs a numeric measure.');
    const unusedMeasures = allMeasures.filter(p => p !== yPill && !(type === 'scatter' && p === xPill));
    if (unusedMeasures.length) issues.push('Worksheet charts show one measure. Not drawn: ' + unusedMeasures.map(p => p.field.name).join(', ') + '. Use separate sheets, a two-measure scatter, or Verified contributions.');
    let grouping = [...new Set(allDimensions.concat(details.filter(p => p.field.role === 'dimension')).map(p => p.column))];
    if (type === 'scatter' && grouping.length) issues.push('Scatter shows individual rows here. Grouping needs Verified contributions.');
    if (type === 'histogram' && grouping.length) notes.push('Histogram uses individual values; shelf dimensions do not group bins. Remove them or use a box plot for grouped distributions.');
    if (['scatter', 'histogram'].includes(type)) grouping = [];
    if (x < 0 && grouping.length) x = grouping[0];
    if (x >= 0 && !['scatter', 'histogram'].includes(type)) grouping = [x, ...grouping.filter(column => column !== x && column !== series)];
    if (transform !== 'none' && grouping.some(column => column !== x)) issues.push('Time analysis needs one time grouping; filter the other dimensions or use separate ordinary series.');

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
    // The engine refuses to add several subjects together over time, and the
    // classic dialog answers that with its own Subject select; the studio asks
    // for the same choice in Parameters instead of letting the engine throw.
    const subject = subjectField(meta.fields);
    if (subject && transform !== 'none' && !filters.some(f => f.column === subject.index)) {
      const chosen = params.subject == null ? '' : String(params.subject);
      if (chosen) filters.push({column: subject.index, op: 'equals', value: chosen});
      else issues.push('Choose a Subject in Parameters for time analysis.');
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
      maxGroups: positiveInteger(params.maxGroups) || STUDIO_GROUP_LIMIT,
      splitMulti: !!params.splitMulti,
      series: series,
      filters: filters
    } : null;

    if (config && transform === 'forecast' && (config.start || config.end || config.limit)) {
      notes.push('The same-phase forecast reads every worksheet row; clear the row range and row limit in Parameters.');
    }
    if (config && config.splitMulti && config.aggregation !== 'count') issues.push('Split multi-value cells is coverage-only. Choose Count or use transaction-level ZIP data for money.');
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
      fields: meta
    };
  }

  const compileConfig = (state, columns) => compileReport(state, columns).config;

  /* -------------------------------------------------------------- show me */

  const tile = (id, label, requirement, rule) => Object.assign(
    {id: id, label: label, requirement: requirement, disabled: false, note: '',
     needDimensions: 0, needMeasures: 0, needTime: false}, rule);

  const SHOW_ME = [
    tile('text-table', 'Text table', '1 or more Dimensions, 1 or more Measures', {needDimensions: 1, needMeasures: 1}),
    tile('heat-map', 'Heat map', '1 or more Dimensions, 1 or 2 Measures', {disabled: true}),
    tile('highlight-table', 'Highlight table', '1 or more Dimensions, 1 Measure', {disabled: true}),
    tile('symbol-map', 'Symbol map', '1 geographic Dimension, 0 to 2 Measures', {disabled: true}),
    tile('filled-map', 'Filled map', '1 geographic Dimension, 0 or 1 Measures', {disabled: true}),
    tile('pie-chart', 'Pie chart', '1 or more Dimensions, 1 or 2 Measures', {needDimensions: 1, needMeasures: 1,
      note: 'Shares need nonnegative values; use bars for signed amounts.'}),
    tile('horizontal-bars', 'Horizontal bars', '0 or more Dimensions, 1 or more Measures', {needDimensions: 1, needMeasures: 1}),
    tile('stacked-bars', 'Stacked bars', '1 or more Dimensions, 1 or more Measures', {needDimensions: 2, needMeasures: 1,
      note: 'This release draws the colour breakdown side by side rather than stacked.'}),
    tile('side-by-side-bars', 'Side-by-side bars', '1 or more Dimensions, 1 or more Measures', {needDimensions: 2, needMeasures: 1}),
    tile('treemap', 'Treemap', '1 or more Dimensions, 1 or 2 Measures', {disabled: true}),
    tile('circle-views', 'Circle views', '1 or more Dimensions, 1 or more Measures', {needDimensions: 1, needMeasures: 1,
      note: 'Drawn as circles joined by a line; this release has no dimension-axis circle mark.'}),
    tile('side-by-side-circles', 'Side-by-side circles', '1 or more Dimensions, 1 or more Measures', {needDimensions: 2, needMeasures: 1,
      note: 'Drawn as one circle series per colour member, joined by a line.'}),
    tile('lines-continuous', 'Lines (continuous)', '1 Date, 1 or more Measures', {needDimensions: 1, needMeasures: 1, needTime: true}),
    tile('lines-discrete', 'Lines (discrete)', '1 Date, 1 or more Measures', {needDimensions: 1, needMeasures: 1, needTime: true,
      note: 'Groups the dates into calendar-year or election-cycle periods.'}),
    tile('dual-lines', 'Dual lines', '1 Date, 2 Measures', {needDimensions: 2, needMeasures: 1, needTime: true,
      note: 'One axis only: the second line comes from the Colour dimension, not a second measure.'}),
    tile('area-continuous', 'Area chart (continuous)', '1 Date, 1 or more Measures', {needDimensions: 1, needMeasures: 1, needTime: true}),
    tile('area-discrete', 'Area chart (discrete)', '1 Date, 1 or more Measures', {needDimensions: 1, needMeasures: 1, needTime: true,
      note: 'Groups the dates into calendar-year or election-cycle periods.'}),
    tile('dual-combination', 'Dual combination', '1 Date, 2 Measures', {disabled: true}),
    tile('scatter-plot', 'Scatter plot', '0 or more Dimensions, 2 to 4 Measures', {needMeasures: 2}),
    tile('histogram', 'Histogram', '0 Dimensions, 1 Measure', {needMeasures: 1}),
    tile('box-and-whisker', 'Box-and-whisker', '0 or more Dimensions, 1 or more Measures', {needMeasures: 1}),
    tile('gantt', 'Gantt', '1 Date, 0 or 1 Measures', {disabled: true}),
    tile('bullet-graph', 'Bullet graph', '0 or more Dimensions, 2 Measures', {disabled: true}),
    tile('packed-bubbles', 'Packed bubbles', '1 or more Dimensions, 1 or 2 Measures', {disabled: true})
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

  function showMeEligibility(selection) {
    return SHOW_ME.map(t => {
      const view = {id: t.id, label: t.label, requirement: t.requirement, note: t.note, enabled: false, reason: ''};
      if (t.disabled) { view.reason = 'not in this release'; return view; }
      const missing = [];
      if (selection.dimensions < t.needDimensions) missing.push(plural(t.needDimensions, 'dimension'));
      if (selection.measures < t.needMeasures) missing.push(plural(t.needMeasures, 'measure'));
      if (t.needTime && selection.times < 1) missing.push('a date, year or election-cycle dimension');
      view.enabled = missing.length === 0;
      view.reason = missing.length ? 'Needs ' + missing.join(' and ') : '';
      return view;
    });
  }

  function showMeApply(tileId, state, columns, selected) {
    const t = SHOW_ME.find(item => item.id === tileId);
    const selection = showMeSelection(state, columns, selected);
    if (!t || t.disabled) return clone(state);
    const dimensions = selection.fields.filter(f => f.role === 'dimension');
    const times = dimensions.filter(f => f.isTime);
    const plain = dimensions.filter(f => !f.isTime);
    const measures = selection.fields.filter(f => f.role === 'measure');
    const next = clone(state);
    // Changing a chart changes its marks, not the user's chosen data question.
    // Seed empty shelves only; preserve every existing pill, filter and aggregate.
    if (shelf(state.columns).length || shelf(state.rows).length) {
      const marks = {'text-table':'text','pie-chart':'pie','horizontal-bars':'bar',
        'stacked-bars':'bar','side-by-side-bars':'bar','circle-views':'line',
        'side-by-side-circles':'line','lines-continuous':'line','lines-discrete':'line',
        'dual-lines':'line','area-continuous':'area','area-discrete':'area',
        'scatter-plot':'circle','histogram':'histogram','box-and-whisker':'box'};
      next.marks = {...next.marks, type: marks[tileId] || next.marks.type};
      if (tileId === 'horizontal-bars') next.marks.orientation = 'horizontal';
      return next;
    }
    next.columns = []; next.rows = [];
    next.marks = Object.assign({}, next.marks, {color: null});
    next.analytics = Object.assign({}, next.analytics, {transform: 'none'});
    const measurePill = index => {
      const existing = shelf(state.columns).concat(shelf(state.rows)).find(p => p.column === index);
      return {column: index, aggregation: existing ? existing.aggregation : 'sum'};
    };
    const dimension = position => (plain[position] || dimensions[position] || null);
    const time = times[0] || null;
    const colour = () => {
      const used = next.columns.concat(next.rows).map(p => p.column);
      // A date belongs on the axis, so Colour prefers a plain dimension.
      const candidate = plain.find(f => used.indexOf(f.index) === -1)
        || dimensions.find(f => used.indexOf(f.index) === -1);
      if (candidate) next.marks.color = {column: candidate.index, aggregation: 'sum'};
    };
    const setMark = id => { next.marks.type = id; };

    if (t.id === 'text-table' || t.id === 'pie-chart') {
      if (dimension(0)) next.columns = [{column: dimension(0).index, aggregation: 'sum'}];
      if (measures[0]) next.rows = [measurePill(measures[0].index)];
      setMark(t.id === 'pie-chart' ? 'pie' : 'text');
    } else if (t.id === 'horizontal-bars') {
      if (dimension(0)) next.rows = [{column: dimension(0).index, aggregation: 'sum'}];
      if (measures[0]) next.columns = [measurePill(measures[0].index)];
      setMark('bar');
    } else if (t.id === 'stacked-bars' || t.id === 'side-by-side-bars') {
      if (dimension(0)) next.columns = [{column: dimension(0).index, aggregation: 'sum'}];
      if (measures[0]) next.rows = [measurePill(measures[0].index)];
      setMark('bar'); colour();
    } else if (t.id === 'circle-views' || t.id === 'side-by-side-circles') {
      if (dimension(0)) next.columns = [{column: dimension(0).index, aggregation: 'sum'}];
      if (measures[0]) next.rows = [measurePill(measures[0].index)];
      setMark('line');
      if (t.id === 'side-by-side-circles') colour();
    } else if (['lines-continuous', 'lines-discrete', 'dual-lines', 'area-continuous', 'area-discrete'].indexOf(t.id) !== -1) {
      if (time) next.columns = [{column: time.index, aggregation: 'sum'}];
      if (measures[0]) next.rows = [measurePill(measures[0].index)];
      setMark(t.id.indexOf('area') === 0 ? 'area' : 'line');
      if (t.id === 'lines-discrete' || t.id === 'area-discrete') next.analytics.transform = 'annual';
      if (t.id === 'dual-lines') colour();
    } else if (t.id === 'scatter-plot') {
      if (measures[0]) next.columns = [measurePill(measures[0].index)];
      if (measures[1]) next.rows = [measurePill(measures[1].index)];
      setMark('circle');
    } else if (t.id === 'histogram') {
      if (measures[0]) next.rows = [measurePill(measures[0].index)];
      setMark('histogram');
    } else if (t.id === 'box-and-whisker') {
      if (dimension(0)) next.columns = [{column: dimension(0).index, aggregation: 'sum'}];
      if (measures[0]) next.rows = [measurePill(measures[0].index)];
      setMark('box');
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

  // Chronological order is the meaning of a time axis, so sorting such a view
  // by value would destroy it rather than reorder it. A built result and a
  // compiled configuration both answer this, so the toolbar can switch Sort off
  // before the view is drawn and sortResult can refuse it afterwards.
  const TIME_VIEWS = ['line', 'area', 'multiline'];
  const sortLocked = view => !!view && (!!view.temporal ||
    (view.transform != null && view.transform !== 'none') || TIME_VIEWS.indexOf(view.type) !== -1);

  function sortResult(result, direction) {
    if (!result || !Array.isArray(result.groups)) return result;
    if (['asc', 'desc'].indexOf(direction) === -1) return result;
    if (['scatter', 'histogram'].indexOf(result.type) !== -1) return result;
    if (sortLocked(result)) return result;
    const size = group => result.series
      ? group.values.reduce((total, v) => total + (v.value == null ? 0 : v.value), 0)
      : groupValue(group);
    // An Other rollup is the tail the engine folded away, not a member of the
    // view, so it keeps the last position however the real groups are ordered.
    const rollup = result.groups.filter(g => g.other);
    const groups = result.groups.filter(g => !g.other)
      .sort((a, b) => direction === 'asc' ? size(a) - size(b) : size(b) - size(a));
    return Object.assign({}, result, {groups: groups.concat(rollup)});
  }

  // Mark values in the order the renderer appends them, so a caller can label
  // marks without knowing how the SVG was drawn. Empty where labels do not fit.
  function markValues(result) {
    if (!result) return [];
    if (result.series) return result.groups.reduce((all, g) => all.concat(g.values.filter(v => v.value != null).map(v => v.value)), []);
    if (['scatter', 'box', 'pie', 'doughnut', 'radar'].indexOf(result.type) !== -1) return [];
    return (result.groups || []).map(g => g.value);
  }

  function referenceValues(result, analytics) {
    const wanted = analytics || {};
    // One dashed rule cannot stand for several independent series, so a view
    // separated by Colour has no single average or median of its own.
    if (result && result.series) return [];
    const values = markValues(result).filter(v => typeof v === 'number' && Number.isFinite(v));
    const lines = [];
    if (!values.length) return lines;
    if (wanted.average) lines.push({kind: 'average', label: 'Average', value: values.reduce((a, b) => a + b, 0) / values.length});
    if (wanted.median) lines.push({kind: 'median', label: 'Median', value: math.quantile(values.slice().sort((a, b) => a - b), .5)});
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
    if (result.series) return 'Grand total is not shown: series are independent.';
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

  const AGGREGATION_LABEL = {sum: 'SUM', mean: 'AVG', count: 'CNT', median: 'MED', min: 'MIN', max: 'MAX'};

  function rowsToMarksSummary(result, config, columns) {
    if (!result || !config) return null;
    const meta = classifyFields(columns);
    const measure = fieldAt(meta, config.y);
    const marks = result.type === 'scatter' ? (result.points || []).length
      : result.series ? result.groups.reduce((n, g) => n + g.values.filter(v => v.value != null).length, 0)
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
    FILTER_OPS, LIST_OPS, RANGE_OPS, MEASURE_PRESETS, DATE_PARTS, COMPANY_OVERVIEW,
    canTreatAs, isDateLike, filterValues, filterActive, filterBounds, normalizeFilter, filterSummary,
    aggregationsFor, measurePresets, applyMeasurePreset, datePartsFor,
    companyOverviewPresets, companyOverviewMissing, companyOverviewSheet,
    classifyFields, fieldAt, paneBuckets, subjectField, pill, shelf, createSheet, clearSheet, swapShelves, sourceKey,
    carriedFilterValue, graphCycleValue, quickAddZone, migrateSheet,
    WORKSHEET_GROUP_LABELS, NO_DATA_WORKBOOK_HINT, COMMITTEE_ACTIVITY_NOTE,
    defaultGuards, committeeActivitySheet, workbookKind, groupWorksheets,
    compileConfig, compileReport,
    showMeSelection, showMeEligibility, showMeApply, recommendedTile,
    sortResult, sortLocked, markValues, referenceValues, grandTotal, totalNote, rowsToMarksSummary,
    sourceLabelOf, captionSource, captionSourceForKey, viewSourceRecord, chartSourceRecord, chartProvenanceRecord,
    normalizeBoard,
    parseSnapshotRegistry
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.MentatStudioCore = api;
})(globalThis);
