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

  function classifyFields(columns) {
    const fields = (columns || []).map((column, position) => {
      const field = {
        index: Number.isInteger(column.index) ? column.index : position,
        name: String(column.name == null ? 'Column ' + (position + 1) : column.name),
        type: column.type || 'category',
        distinct: column.distinct == null ? null : column.distinct,
        missing: column.missing == null ? null : column.missing
      };
      field.isTime = !!math.timeColumn(field);
      field.isIdentifier = !!math.identifierColumn(field);
      field.role = field.type === 'number' && !field.isTime && !field.isIdentifier ? 'measure' : 'dimension';
      // Identifier columns are real fields; they are folded away until the user
      // asks for them, exactly as recommend() already ignores them.
      field.hidden = field.isIdentifier && !field.isTime;
      field.glyph = field.role === 'measure' ? '#' : field.isTime ? 'cal' : 'Abc';
      return field;
    });
    return {
      fields,
      dimensions: fields.filter(f => f.role === 'dimension' && !f.hidden),
      measures: fields.filter(f => f.role === 'measure' && !f.hidden),
      hidden: fields.filter(f => f.hidden)
    };
  }

  const fieldAt = (meta, index) => meta.fields.find(f => f.index === index) || null;

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
      source: {run: '', runName: '', report: '', reportName: '', sheet: '', header: 0, sha256: ''},
      columns: [],
      rows: [],
      marks: {type: 'automatic', color: null, size: null, label: null, detail: [], tooltip: []},
      filters: [],
      pages: null,
      pageMember: '',
      analytics: {transform: 'none', period: '', horizon: 2, totals: false, average: false, median: false},
      params: {start: 0, end: 0, limit: 0},
      sort: 'none',
      showLabels: false,
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

  /* --------------------------------------------------------------- compile */

  const positiveInteger = value => {
    const number = Number(value);
    return Number.isFinite(number) && number >= 1 ? Math.trunc(number) : 0;
  };

  function compileReport(state, columns) {
    const meta = classifyFields(columns);
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

    const firstDimension = allDimensions[0] || null;
    const firstMeasure = rowMeasures[0] || colMeasures[0] || null;
    const timeDimension = allDimensions.find(p => p.field.isTime) || null;
    // A dimension on Columns draws upright bars; a dimension only on Rows lays
    // the same view on its side, which is what Tableau's Rows shelf means here.
    const orientation = colDimensions.length ? 'vertical' : rowDimensions.length ? 'horizontal' : 'none';

    let type = '', xPill = null, yPill = null;

    if (markType === 'automatic') {
      if (colMeasures.length && rowMeasures.length) {
        type = 'scatter'; xPill = colMeasures[0]; yPill = rowMeasures[0];
      } else if (orientation === 'none') {
        if (firstMeasure) { type = 'bar'; yPill = firstMeasure; }
        else issues.push('Drag a dimension onto Columns or a measure onto Rows to build a view.');
      } else {
        const dimension = orientation === 'vertical' ? colDimensions[0] : rowDimensions[0];
        const measure = orientation === 'vertical'
          ? (rowMeasures[0] || colMeasures[0] || null)
          : (colMeasures[0] || rowMeasures[0] || null);
        xPill = dimension; yPill = measure;
        type = orientation === 'horizontal' ? 'horizontal' : (dimension.field.isTime && measure ? 'line' : 'bar');
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
      xPill = orientation === 'horizontal' ? rowDimensions[0] : (colDimensions[0] || firstDimension);
      yPill = orientation === 'horizontal' ? (colMeasures[0] || rowMeasures[0] || null) : firstMeasure;
      if (!xPill && !yPill) issues.push('Drag a dimension onto Columns or a measure onto Rows to build a view.');
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
    if (type === 'histogram') x = -1;
    if (y === -1) aggregation = 'count';
    if (['scatter', 'box', 'histogram'].includes(type)) {
      if (y === -1) aggregation = 'sum';
      else if (aggregation === 'count') aggregation = 'sum';
    }
    if (y === -1 && ['scatter', 'box', 'histogram'].includes(type)) issues.push('This view plots individual values, so it needs a numeric measure.');

    const timeField = xPill && xPill.field.isTime ? xPill.field : null;
    const period = ['year', 'cycle'].includes(analytics.period) ? analytics.period
      : timeField && /cycle/i.test(timeField.name) ? 'cycle' : 'year';
    const horizon = Number.isFinite(Number(analytics.horizon)) && Number(analytics.horizon) >= 1
      ? Math.trunc(Number(analytics.horizon)) : 2;

    const filters = (state.filters || [])
      .filter(f => f && f.value !== '' && f.value != null && fieldAt(meta, Number(f.column)))
      .map(f => ({column: Number(f.column), op: f.op, value: String(f.value)}));
    const pagePill = pill(state.pages);
    if (pagePill && fieldAt(meta, pagePill.column) && state.pageMember) {
      filters.push({column: pagePill.column, op: 'equals', value: String(state.pageMember)});
    }

    const params = state.params || {};
    const config = type ? {
      type: type,
      x: x,
      y: y,
      aggregation: aggregation,
      transform: transform,
      period: period,
      horizon: horizon,
      start: positiveInteger(params.start),
      end: positiveInteger(params.end),
      limit: positiveInteger(params.limit),
      series: series,
      filters: filters
    } : null;

    if (config && transform === 'forecast' && (config.start || config.end || config.limit)) {
      notes.push('The same-phase forecast reads every worksheet row; clear the row range and row limit in Parameters.');
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
    const meta = classifyFields(columns);
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

  /* -------------------------------------------------------- result helpers */

  const groupValue = group => group.value != null ? group.value : group.median != null ? group.median : 0;

  function sortResult(result, direction) {
    if (!result || !Array.isArray(result.groups)) return result;
    if (['asc', 'desc'].indexOf(direction) === -1) return result;
    if (['scatter', 'histogram'].indexOf(result.type) !== -1) return result;
    const size = group => result.series
      ? group.values.reduce((total, v) => total + (v.value == null ? 0 : v.value), 0)
      : groupValue(group);
    const groups = result.groups.slice().sort((a, b) => direction === 'asc' ? size(a) - size(b) : size(b) - size(a));
    return Object.assign({}, result, {groups: groups});
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
    const values = markValues(result).filter(v => typeof v === 'number' && Number.isFinite(v));
    const lines = [];
    if (!values.length) return lines;
    if (wanted.average) lines.push({kind: 'average', label: 'Average', value: values.reduce((a, b) => a + b, 0) / values.length});
    if (wanted.median) lines.push({kind: 'median', label: 'Median', value: math.quantile(values.slice().sort((a, b) => a - b), .5)});
    return lines;
  }

  function grandTotal(result) {
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
    const total = result.type === 'scatter'
      ? (result.points || []).reduce((n, p) => n + p.y, 0)
      : grandTotal(result);
    const name = config.aggregation === 'count' && config.y === -1 ? 'rows' : measure ? measure.name : 'value';
    return {
      marks: marks,
      viewRows: viewRows,
      viewColumns: viewColumns,
      selected: result.selected == null ? null : result.selected,
      excluded: result.excluded == null ? null : result.excluded,
      measureLabel: AGGREGATION_LABEL[config.aggregation] + '(' + name + ')',
      total: ['box'].indexOf(result.type) === -1 ? total : null
    };
  }

  const api = {
    AGGREGATIONS, AGGREGATION_IDS, MARK_TYPES, MARK_IDS, TRANSFORMS, SHOW_ME,
    classifyFields, fieldAt, pill, shelf, createSheet, clearSheet, swapShelves,
    compileConfig, compileReport,
    showMeSelection, showMeEligibility, showMeApply, recommendedTile,
    sortResult, markValues, referenceValues, grandTotal, rowsToMarksSummary
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.MentatStudioCore = api;
})(globalThis);
