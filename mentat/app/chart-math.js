/* Pure local chart calculations, also exercised by node:test. */
(function (root) {
  'use strict';
  function numeric(value) {
    if (typeof value === 'number') return Number.isFinite(value) ? value : null;
    if (typeof value !== 'string') return null;
    const text = value.trim();
    if (!/^\(?-?\$?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?%?\)?$/.test(text)) return null;
    let n = Number(text.replace(/[(),$%]/g, ''));
    if (text.startsWith('(') && text.endsWith(')')) n = -n;
    if (text.endsWith('%')) n /= 100;
    return Number.isFinite(n) ? n : null;
  }
  function quantile(sorted, p) {
    if (!sorted.length) return null;
    const i = (sorted.length - 1) * p, low = Math.floor(i);
    return sorted[low] + (sorted[Math.ceil(i)] - sorted[low]) * (i - low);
  }
  function box(values) {
    const a = values.slice().sort((x, y) => x - y);
    const q1 = quantile(a, .25), median = quantile(a, .5), q3 = quantile(a, .75), iqr = q3 - q1;
    const inside = a.filter(n => n >= q1 - 1.5 * iqr && n <= q3 + 1.5 * iqr);
    return {n:a.length, q1, median, q3, low:inside[0], high:inside.at(-1),
      outliers:a.filter(n => n < q1 - 1.5 * iqr || n > q3 + 1.5 * iqr)};
  }
  function filterRows(data, config) {
    for (const f of config.filters || []) {
      if (!data.columns[f.column]) throw new Error('Choose a valid filter column.');
      if (!['equals','contains','gte','lte'].includes(f.op)) throw new Error('Choose a filter operation.');
      if (['gte','lte'].includes(f.op) && numeric(f.value) === null) throw new Error('A numeric filter needs a number.');
    }
    if (config.start && config.end && config.start > config.end) throw new Error('First worksheet row must precede the last.');
    return data.rows.filter((row, i) => {
      const number = data.row_numbers[i];
      if (config.start && number < config.start || config.end && number > config.end) return false;
      return (config.filters || []).every(f => {
        const v = row[f.column], text = String(v ?? '').toLocaleLowerCase(), wanted = String(f.value).toLocaleLowerCase();
        if (f.op === 'equals') return text === wanted;
        if (f.op === 'contains') return text.includes(wanted);
        const n = numeric(v), threshold = numeric(f.value);
        return n !== null && (f.op === 'gte' ? n >= threshold : n <= threshold);
      });
    });
  }
  function recommend(columns) {
    const measures = columns.filter(c => c.type === 'number');
    const category = columns.find(c => c.type === 'category' && c.distinct > 1 && c.distinct <= 30);
    const date = columns.find(c => c.type === 'date');
    const choices = [];
    if (measures.length) {
      choices.push({type:'box', x:category?.index ?? -1, y:measures[0].index, aggregation:'sum', label:'Distribution · box plot'});
      choices.push({type:'histogram', x:-1, y:measures[0].index, aggregation:'count', label:'Frequency · histogram'});
    }
    if (category) {
      choices.unshift({type:'bar', x:category.index, y:measures[0]?.index ?? -1, aggregation:measures.length ? 'sum' : 'count', label:'Compare groups · bar chart'});
      choices.push({type:'pie', x:category.index, y:-1, aggregation:'count', label:'Share of rows · pie chart'});
    }
    if (date && measures.length) choices.push({type:'line', x:date.index, y:measures[0].index, aggregation:'sum', label:'Over time · line chart'});
    if (measures.length > 1) choices.push({type:'scatter', x:measures[0].index, y:measures[1].index, aggregation:'sum', label:'Compare measures · scatter plot'});
    return choices;
  }
  function build(data, config) {
    if (!['bar','pie','line','scatter','box','histogram'].includes(config.type)) throw new Error('Choose a chart type.');
    if (!['sum','mean','count'].includes(config.aggregation)) throw new Error('Choose an aggregation.');
    const rows = filterRows(data, config), points = [], groups = new Map();
    if (!rows.length) throw new Error('No rows match this subsection.');
    const count = config.aggregation === 'count' && ['bar','pie','line'].includes(config.type);
    if (!count && !data.columns[config.y]) throw new Error('Choose a numeric measure.');
    if (config.type === 'scatter' && !data.columns[config.x]) throw new Error('Choose an X measure.');
    let excluded = 0;
    for (const row of rows) {
      const y = count ? 1 : numeric(row[config.y]);
      if (y === null) { excluded++; continue; }
      if (config.type === 'pie' && y < 0) throw new Error('Pie charts require nonnegative values. Use a bar chart for signed amounts.');
      if (config.type === 'scatter') {
        const x = numeric(row[config.x]);
        if (x === null) { excluded++; continue; }
        points.push({x, y}); continue;
      }
      const group = config.x < 0 || config.type === 'histogram' ? 'All rows' : String(row[config.x] ?? '(Missing)');
      if (!groups.has(group)) groups.set(group, []);
      groups.get(group).push(y);
    }
    if (excluded === rows.length) throw new Error('No numeric values remain. Missing values are not treated as zero.');
    if (config.type === 'scatter') {
      if (points.length > 5000) throw new Error('Filter to 5,000 points or fewer for a scatter plot.');
      return {type:config.type, points, selected:rows.length, excluded};
    }
    if (config.type === 'histogram') {
      const values = groups.get('All rows'), min = Math.min(...values), max = Math.max(...values);
      const n = min === max ? 1 : Math.min(30, Math.ceil(Math.sqrt(values.length)));
      const width = min === max ? 1 : (max - min) / n;
      const bins = Array.from({length:n}, (_, i) => ({label:`${(min + width*i).toPrecision(5)} – ${(min + width*(i+1)).toPrecision(5)}`, value:0}));
      for (const v of values) bins[Math.min(n-1, Math.floor((v-min)/width))].value++;
      return {type:config.type, groups:bins, selected:rows.length, excluded};
    }
    if (groups.size > 60) throw new Error('Filter to 60 groups or fewer, or choose a different grouping column.');
    let output = [...groups].map(([label, values]) => config.type === 'box' ? {label, ...box(values)} :
      {label, value:count ? values.length : values.reduce((a,b) => a+b,0) / (config.aggregation === 'mean' ? values.length : 1), n:values.length});
    if (config.type === 'line') output.sort((a,b) => a.label.localeCompare(b.label, undefined, {numeric:true}));
    if (config.type === 'pie' && !output.some(g => g.value > 0)) throw new Error('A pie chart needs a positive total.');
    return {type:config.type, groups:output, selected:rows.length, excluded};
  }
  const api = {numeric, quantile, box, filterRows, recommend, build};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.MentatCharts = api;
})(globalThis);
