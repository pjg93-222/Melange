/* Pure local chart calculations, also exercised by node:test. */
(function (root) {
  'use strict';
  function numeric(value) {
    if (typeof value === 'number') return Number.isFinite(value) ? value : null;
    if (typeof value !== 'string') return null;
    const raw = value.trim(), accounting = raw.startsWith('(') && raw.endsWith(')');
    const text = accounting ? raw.slice(1,-1) : raw;
    if (!/^-?\$?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?%?$/.test(text) || accounting && text.startsWith('-')) return null;
    let n = Number(text.replace(/[$%]/g, '').replaceAll(',', ''));
    if (accounting) n = -n;
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
    if (config.limit != null && config.limit !== 0 && (!Number.isInteger(config.limit) || config.limit < 1)) throw new Error('Row count must be a positive whole number.');
    for (const f of config.filters || []) {
      if (!data.columns[f.column]) throw new Error('Choose a valid filter column.');
      if (!['equals','contains','gte','lte'].includes(f.op)) throw new Error('Choose a filter operation.');
      if (['gte','lte'].includes(f.op) && numeric(f.value) === null) throw new Error('A numeric filter needs a number.');
    }
    if (config.start && config.end && config.start > config.end) throw new Error('First worksheet row must precede the last.');
    const matching = data.rows.filter((row, i) => {
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
    return config.limit ? matching.slice(0, config.limit) : matching;
  }
  const chartTypes=['bar','pie','line','scatter','box','histogram','area','doughnut','waterfall','radar','horizontal','pareto','grouped','groupedhorizontal','multiline'];
  const aggregations=['sum','mean','count','median','min','max'];
  // Refusing to draw is worse than showing the head of the distribution: the tail
  // is pooled into one Other mark, so the grand total still balances. 60 is the
  // standing per-view contract of the two callers that pass no limit - the classic
  // dialog in charts.js and funding-comparison.js, whose own control reads "Enter
  // 1-60 recipients per view". At 60 they draw exactly what they drew before and
  // only fold, with a note, where they used to throw. Chart Studio passes its own
  // tighter default from its compiler.
  const DEFAULT_GROUP_LIMIT = 60;
  function groupLimit(config) {
    const n = config.maxGroups;
    if (n == null || n === 0) return DEFAULT_GROUP_LIMIT;
    if (!Number.isInteger(n) || n < 1) throw new Error('Group limit must be a positive whole number.');
    return n;
  }
  // The one place a group of raw values becomes its mark's number. The Other
  // rollup calls it on the pooled raw values and never on already-aggregated
  // ones, so a pooled mean is the mean of the rows, not a mean of means.
  function aggregate(values, config, count) {
    if (count) return values.length;
    if (config.aggregation === 'median') return quantile(values.slice().sort((a, b) => a - b), .5);
    // reduce, not Math.min(...values): the Other rollup pools every folded row and
    // a spread of that many arguments overflows the call stack. Every value here
    // is a finite number (numeric() already dropped null), so both forms agree.
    if (config.aggregation === 'min') return values.reduce((low, v) => v < low ? v : low, Infinity);
    if (config.aggregation === 'max') return values.reduce((high, v) => v > high ? v : high, -Infinity);
    return values.reduce((a, b) => a + b, 0) / (config.aggregation === 'mean' ? values.length : 1);
  }
  // One builder owns the rollup's name, so the mark's label and the sentence that
  // explains it can never drift apart. The engine's default of 60 puts a one-group
  // fold within reach of the legacy callers, so the count agrees with its noun and verb.
  const otherLabel = folded => 'Other (' + folded + (folded === 1 ? ' group)' : ' groups)');
  const rollupNote = (limit, total, folded, by) => 'Top ' + limit + ' of ' + total + ' groups by ' + by +
    '; the other ' + folded + (folded === 1 ? ' group is' : ' groups are') + ' combined into "' + otherLabel(folded) +
    '". Raise the group limit in Parameters to show more.';
  const splitNote = split => split.cells + ' multi-value ' + split.columns.join(' / ') + ' cells were split on ";" into ' +
    split.values + ' separate values, each drawn as its own mark. The measure is repeated for every value from one cell, so SUM and COUNT along ' +
    split.columns.join(' / ') + ' count a split row once per value.';
  // Some worksheet cells hold several values joined with "; " - one filing that
  // names three ZIPs. Splitting them is opt-in because it repeats that row's
  // measure once per value, which answers a coverage question and overstates money.
  function explodeRows(data, config) {
    if (!config.splitMulti) return data;
    // Only grouping fields split: a scatter x is a measure and a histogram has
    // no x at all. A column named by both x and series is split once.
    const targets = [config.x, config.series].filter((column, at, all) => column >= 0 && all.indexOf(column) === at &&
      data.columns[column] && data.columns[column].type !== 'number');
    if (!targets.length) return data;
    const rows = [], row_numbers = [];
    let cells = 0, values = 0;
    const splitting = new Set(); // Candidates that actually produced a split.
    data.rows.forEach((row, i) => {
      let batch = [row];
      for (const column of targets) {
        const parts = String(row[column] ?? '').split(';').map(s => s.trim()).filter(Boolean);
        if (parts.length < 2) continue; // One value or none: the cell is left exactly as it was.
        cells++; values += parts.length; splitting.add(column);
        batch = batch.flatMap(current => parts.map(part => {
          const copy = current.slice(); copy[column] = part; return copy;
        }));
      }
      for (const emitted of batch) { rows.push(emitted); row_numbers.push(data.row_numbers[i]); }
    });
    if (!cells) return data;
    return Object.assign({}, data, {rows, row_numbers,
      // Name only the columns that actually split. A candidate with no multi-value
      // cell contributed nothing, and naming it would make the note claim it did.
      split:{cells, values, columns:targets.filter(column => splitting.has(column)).map(column => data.columns[column].name)}});
  }
  const timeColumn=c=>c.type==='date'||/\b(year|cycle|date)\b/i.test(c.name);
  const identifierColumn=c=>/(?:^|[\s_])(id|identifier|code|zip|index|row number|filing number|transaction number)(?:$|[\s_])/i.test(c.name);
  function chartColumns(columns) {
    const indexed=columns.map((c,index)=>({...c,index:c.index??index}));
    const measures=indexed.filter(c=>c.type==='number'&&!timeColumn(c)&&!identifierColumn(c)).sort((a,b)=>measureScore(b)-measureScore(a));
    const categories=indexed.filter(c=>c.type==='category'&&!identifierColumn(c)&&!timeColumn(c)&&(c.distinct==null||c.distinct>1&&c.distinct<=60));
    const times=indexed.filter(timeColumn);
    return {indexed,measures,categories,times};
  }
  function measureScore(column) {
    return /\b(net giving|amount|total giving)\b/i.test(column.name)?3:/giving|contribution|receipt|disbursement|spend|donat|cost|dollar|total|fund/i.test(column.name)?2:1;
  }
  function recommend(columns) {
    const {measures,categories,times}=chartColumns(columns);
    const category=categories[0], date=times[0];
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
  function quickConfig(data, current, choice) {
    const {indexed,measures,categories,times}=chartColumns(data.columns);
    const time=times.find(c=>c.index===current.x)||times[0];
    const temporal=['annual','yoy','change','forecast'].includes(choice);
    if(!temporal&&!chartTypes.includes(choice))throw new Error('Choose a chart type.');
    const numericOnly=['scatter','histogram','box'].includes(choice);
    const rowCount=current.y===-1&&current.aggregation==='count'&&!numericOnly;
    const selectedMeasure=measures.find(c=>c.index===current.y);
    const y=rowCount?null:selectedMeasure||measures[0];
    const grouping=[...categories,...times];
    const category=grouping.find(c=>c.index===current.x)||categories[0]||times[0];
    const next={...current,type:temporal?'line':choice,transform:temporal?choice:'none',y:y?.index??-1,
      aggregation:!y?'count':selectedMeasure&&aggregations.includes(current.aggregation)?current.aggregation:'sum',x:category?.index??-1,series:-1};
    if(numericOnly&&!y)throw new Error('This chart needs numeric data.');
    if (choice === 'scatter') {
      const other=measures.find(c=>c.index===current.x&&c.index!==y.index)||measures.find(c=>c.index!==y.index);
      if (!other) throw new Error('Scatter needs two numeric statistics.');
      next.x = other.index;
    }
    if (choice === 'histogram') next.x = -1;
    if (choice === 'box') next.x=categories.find(c=>c.index===current.x)?.index??categories[0]?.index??-1;
    if (['line','area','multiline'].includes(choice) && time) next.x = time.index;
    if (temporal) {
      if (!time) throw new Error('This worksheet has no date, year or election-cycle column.');
      next.x = time.index; next.period = /cycle/i.test(time.name) ? 'cycle' : 'year';
      if (choice === 'yoy' && next.period === 'cycle') throw new Error('Year over year needs annual data; these are two-year election cycles.');
    }
    const rows=Array.isArray(data.rows)?filterRows(data,next):null;
    const multipleIndependent=data.independent_series!=null&&(!rows||new Set(rows.map(r=>r[data.independent_series])).size>1);
    if(multipleIndependent){
      const paired={bar:'grouped',horizontal:'groupedhorizontal',line:'multiline'};
      if(!temporal&&paired[next.type])next.type=paired[next.type];
      else if(temporal||!['grouped','groupedhorizontal','multiline'].includes(next.type))throw new Error('Filter to one Source / activity, or use a comparison chart to keep independent funding amounts separate.');
    }
    if(['grouped','groupedhorizontal','multiline'].includes(next.type)){
      let x=grouping.find(c=>c.index===next.x), series=grouping.find(c=>c.index===current.series&&c.index!==x?.index);
      if(multipleIndependent){
        const independent=indexed.find(c=>c.index===data.independent_series);
        if(x?.index!==independent.index)series=independent;
        else series=series||grouping.find(c=>c.index!==independent.index);
      }
      series=series||categories.find(c=>c.index!==x?.index)||times.find(c=>c.index!==x?.index);
      x=x||grouping.find(c=>c.index!==series?.index);
      if(!x||!series||x.index===series.index)throw new Error('This comparison needs two distinct grouping columns, such as recipient and source.');
      next.x=x.index;next.series=series.index;
    }
    if(rows&&['pie','doughnut','pareto','radar'].includes(next.type)){
      if(next.aggregation!=='count'&&rows.some(row=>{const value=numeric(row[next.y]);return value!==null&&value<0;}))throw new Error('This chart requires nonnegative values. Use a bar chart for signed amounts.');
      const usable=rows.filter(row=>next.aggregation==='count'||numeric(row[next.y])!==null);
      if(next.type==='radar'&&new Set(usable.map(row=>next.x<0?'All rows':String(row[next.x]??'(Missing)'))).size<3)throw new Error('Radar charts need at least three groups.');
    }
    return next;
  }
  function build(data, config) {
    if (['grouped','groupedhorizontal','multiline'].includes(config.type)) return grouped(data, config);
    const source = explodeRows(data, config);
    if (source.independent_series != null && new Set(filterRows(source,config).map(r=>r[source.independent_series])).size > 1) throw new Error('Use side-by-side bars, horizontal comparison or separate lines to keep funding sources and activities separate.');
    if (config.transform && config.transform !== 'none') return temporal(data, config);
    if (!['bar','pie','line','scatter','box','histogram','area','doughnut','waterfall','radar','horizontal','pareto'].includes(config.type)) throw new Error('Choose a chart type.');
    if (!['sum','mean','count','median','min','max'].includes(config.aggregation)) throw new Error('Choose an aggregation.');
    const rows = filterRows(source, config), points = [], groups = new Map();
    if (!rows.length) throw new Error('No rows match this subsection.');
    const count = config.aggregation === 'count' && !['box','scatter','histogram'].includes(config.type);
    if (!count && !data.columns[config.y]) throw new Error('Choose a numeric measure.');
    if (config.type === 'scatter' && !data.columns[config.x]) throw new Error('Choose an X measure.');
    let excluded = 0;
    for (const row of rows) {
      const y = count ? 1 : numeric(row[config.y]);
      if (y === null) { excluded++; continue; }
      if (['pie','doughnut','pareto','radar'].includes(config.type) && y < 0) throw new Error('This chart requires nonnegative values. Use a bar chart for signed amounts.');
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
    const limit = groupLimit(config);
    let entries = [...groups], rolled = null;
    if (entries.length > limit) {
      // Rank by the number the mark itself would show, so the fold keeps the
      // groups the view is about. Selection is by size; the axis still lists the
      // survivors in the order the rows arrived, which is what a waterfall means.
      const key = new Map(entries.map(([label, values]) => [label,
        config.type === 'box' ? quantile(values.slice().sort((a,b)=>a-b), .5) : aggregate(values, config, count)]));
      const kept = new Set(entries.slice().sort((a, b) => key.get(b[0]) - key.get(a[0]) ||
        a[0].localeCompare(b[0], undefined, {numeric:true})).slice(0, limit).map(([label]) => label));
      const rest = entries.filter(([label]) => !kept.has(label)), pooled = rest.flatMap(([, values]) => values);
      entries = entries.filter(([label]) => kept.has(label));
      rolled = Object.assign({label:otherLabel(rest.length)},
        config.type === 'box' ? box(pooled) : {value:aggregate(pooled, config, count), n:pooled.length},
        {other:true, folded:rest.length});
    }
    let output = entries.map(([label, values]) => config.type === 'box' ? {label, ...box(values)} :
      {label, value:aggregate(values, config, count), n:values.length});
    if (['line','area'].includes(config.type)) output.sort((a,b) => a.label.localeCompare(b.label, undefined, {numeric:true}));
    if (config.type==='pareto')output.sort((a,b)=>b.value-a.value);
    if (rolled) output.push(rolled); // Other is the tail of the view, never a member sorted into it.
    if(config.type==='radar'&&output.length<3)throw new Error('Radar charts need at least three groups.');
    if (['pie','doughnut','pareto','radar'].includes(config.type) && !output.some(g => g.value > 0)) throw new Error('This chart needs a positive total.');
    const result = {type:config.type, groups:output, selected:rows.length, excluded};
    const notes = [];
    // selected counts exploded rows, so it can exceed the worksheet. The caller
    // needs the split facts to say "values from rows" rather than "7333 of 4500".
    if (source.split) { result.split = source.split; notes.push(splitNote(source.split)); }
    if (rolled) notes.push(rollupNote(limit, groups.size, rolled.folded, count ? 'row count' : config.aggregation));
    if (notes.length) result.note = notes.join(' ');
    return result;
  }
  function grouped(data, config) {
    if (config.transform && config.transform !== 'none') throw new Error('Choose None for time analysis to compare separate series.');
    if (!data.columns[config.x] || !data.columns[config.series]) throw new Error('Choose a grouping column and a separate series.');
    const source=explodeRows(data,config);
    if(source.independent_series!=null && config.x!==source.independent_series && config.series!==source.independent_series && new Set(filterRows(source,config).map(r=>r[source.independent_series])).size>1)throw new Error('Keep Source / activity as the grouping or separate series so independent amounts are not combined.');
    if (!['sum','mean','count','median','min','max'].includes(config.aggregation)) throw new Error('Choose an aggregation.');
    const order=source.independent_series==null || config.series===source.independent_series ? source.series_order||[] : [];
    const rows=filterRows(source,config), groups=new Map(), series=new Set(order);let excluded=0;
    for(const row of rows) {
      const label=String(row[config.x]??'(Missing)'), name=String(row[config.series]??'(Missing)');
      if(!groups.has(label))groups.set(label,new Map());series.add(name);
      const value=config.aggregation==='count'?1:numeric(row[config.y]);
      if(value===null){excluded++;continue;}
      if(!groups.get(label).has(name))groups.get(label).set(name,[]);
      groups.get(label).get(name).push(value);
    }
    if(!rows.length)throw new Error('No rows match this subsection.');
    const limit=groupLimit(config), countMode=config.aggregation==='count';
    let entries=[...groups], rolled=null;
    if(entries.length>limit){
      // A label is ranked by everything drawn under it, across every series.
      const key=new Map(entries.map(([label,byName])=>[label,aggregate([...byName.values()].flat(),config,countMode)]));
      const kept=new Set(entries.slice().sort((a,b)=>key.get(b[0])-key.get(a[0])||
        a[0].localeCompare(b[0],undefined,{numeric:true})).slice(0,limit).map(([label])=>label));
      const rest=entries.filter(([label])=>!kept.has(label)), pooled=new Map();
      entries=entries.filter(([label])=>kept.has(label));
      for(const [,byName] of rest)for(const [name,values] of byName){
        if(!pooled.has(name))pooled.set(name,[]);
        const into=pooled.get(name);for(const v of values)into.push(v); // push(...values) overflows on a large fold.
      }
      rolled={label:otherLabel(rest.length),members:pooled,folded:rest.length};
    }
    const mark=(label,byName)=>({label,values:[...series].map(name=>{
      const a=byName.get(name);return {series:name,value:!a?null:aggregate(a,config,countMode),n:a?.length||0};
    })});
    const output=entries.map(([label,byName])=>mark(label,byName));
    if(rolled)output.push(Object.assign(mark(rolled.label,rolled.members),{other:true,folded:rolled.folded}));
    let note='Series are independent; no combined total. Gaps mean unavailable observations, not zero.';
    if(source.split)note+=' '+splitNote(source.split);
    if(rolled)note+=' '+rollupNote(limit,groups.size,rolled.folded,countMode?'row count':config.aggregation);
    const result={type:config.type,groups:output,series:[...series],selected:rows.length,excluded,note};
    if(source.split)result.split=source.split; // selected counts exploded rows; the caller says so.
    return result;
  }
  function temporal(data, config) {
    if(!['annual','yoy','change','forecast'].includes(config.transform))throw new Error('Choose a time analysis.');
    if(!['bar','line','area'].includes(config.type))throw new Error('Time analysis supports bar, line and area charts.');
    const column=data.columns[config.x];
    if(!column)throw new Error('Choose a date or year column.');
    const cycleInput=/cycle/i.test(column.name), bucketCalendarYears=config.period==='cycle'&&!cycleInput;
    const bucketYear=year=>bucketCalendarYears?year+year%2:year;
    if(cycleInput&&config.period!=='cycle')throw new Error('Election cycles are two-year periods. Choose Election cycle instead of Calendar year.');
    if(config.period==='cycle'&&config.transform==='yoy')throw new Error('Year-over-year requires calendar-year data. Use Period change for election cycles.');
    if(!aggregations.includes(config.aggregation))throw new Error('Choose an aggregation.');
    const rows=filterRows(data,config), byYear=new Map(), incompleteYears=new Set(), sourceYears=new Map();let excluded=0;
    const subjectColumn=data.columns.find(c=>c.name==='Subject');
    if(subjectColumn&&new Set(rows.map(r=>r[subjectColumn.index])).size>1)throw new Error('Filter to one Subject for time analysis; overlapping subjects cannot be added together.');
    for(const row of rows) {
      const raw=String(row[config.x]??'').trim();
      const match=cycleInput?raw.match(/^(?:(\d{4})[-–])?(\d{4})$/):raw.match(/^(\d{4})(?:-\d{2}-\d{2}(?:T.*)?)?$/);
      const value=config.aggregation==='count'?1:numeric(row[config.y]);
      if(!match){excluded++;continue;}
      const sourceYear=Number(match[cycleInput?2:1]), year=bucketYear(sourceYear);
      if(sourceYear<1800||year>2200||cycleInput&&(sourceYear%2!==0||match[1]&&Number(match[1])!==sourceYear-1)){excluded++;continue;}
      if(!cycleInput&&raw.length>4){
        const calendarDate=new Date(raw.slice(0,10)+'T00:00:00Z'), timestamp=new Date(raw);
        if(!Number.isFinite(calendarDate.getTime())||calendarDate.toISOString().slice(0,10)!==raw.slice(0,10)||!Number.isFinite(timestamp.getTime())){incompleteYears.add(year);excluded++;continue;}
      }
      if(!sourceYears.has(year))sourceYears.set(year,new Set());sourceYears.get(year).add(sourceYear);
      if(value===null){incompleteYears.add(year);excluded++;continue;}
      if(!byYear.has(year))byYear.set(year,[]);byYear.get(year).push(value);
    }
    const groups=[...byYear].sort((a,b)=>a[0]-b[0]).map(([year,values])=>({label:String(year),year,n:values.length,value:config.aggregation==='count'?values.length:config.aggregation==='median'?quantile(values.slice().sort((a,b)=>a-b),.5):config.aggregation==='min'?Math.min(...values):config.aggregation==='max'?Math.max(...values):values.reduce((a,b)=>a+b,0)/(config.aggregation==='mean'?values.length:1)}));
    if(!groups.length)throw new Error('No valid dated numeric observations remain.');
    const step=config.period==='cycle'?2:1;
    const statistic=config.aggregation==='sum'?'totals':config.aggregation==='count'?'row counts':config.aggregation+' values';
    let output=groups, note=config.period==='cycle'?`Over time shows ${statistic} for each two-year election-cycle reporting period.`:`Over time shows calendar-year ${statistic}; partial years are not annualized.`;
    if(['yoy','change'].includes(config.transform)) {
      output=groups.flatMap(g=>{
        const prior=groups.find(p=>p.year===g.year-step);
        if(!prior||config.transform==='yoy'&&prior.value<=0)return [];
        return [{...g,value:config.transform==='yoy'?(g.value-prior.value)/prior.value*100:g.value-prior.value,prior:prior.value}];
      });
      note+=' '+(config.transform==='yoy'?'Year over year is (this year − previous year) / previous year × 100, rather than the amount itself. Nonpositive prior bases and missing prior years are unavailable.':'Absolute change from the immediately preceding period; missing periods are unavailable.');
      if(!output.length)throw new Error('No comparable consecutive periods with a valid prior base.');
    }
    if(config.transform==='forecast') {
      if(config.start||config.end||config.limit)throw new Error('Use all worksheet rows before forecasting; row bounds and row-count limits can cut a period short. Subject and category filters remain available.');
      const horizon=Number(config.horizon||2);
      if(!Number.isInteger(horizon)||horizon<1||horizon>10)throw new Error('Choose a projection horizon from 1 to 10 periods.');
      const asOf=new Date(config.as_of||new Date().toISOString());
      if(!Number.isFinite(asOf.getTime()))throw new Error('The forecast reference date is invalid.');
      const partial=new Set((data.partial_periods||[]).map(Number)), complete=Array.isArray(data.complete_periods)?new Set(data.complete_periods.map(Number)):null;
      const coverage=data.period_coverage||{};
      const through=data.verified_data_through?new Date(data.verified_data_through):null;
      const observed=groups.map(g=>{
        const members=bucketCalendarYears?[g.year-1,g.year]:[g.year];
        const openPeriod=g.year>=asOf.getUTCFullYear();
        const missingEvidence=incompleteYears.has(g.year)||members.some(year=>{
          const evidence=coverage[year], status=typeof evidence==='string'?evidence:evidence?.status;
          return partial.has(year)||complete&&!complete.has(year)||bucketCalendarYears&&!sourceYears.get(g.year)?.has(year)||evidence?.complete===false||['partial','incomplete','current','unknown'].includes(status);
        });
        const beforePeriodEnd=through&&(!Number.isFinite(through.getTime())||through.getTime()<Date.UTC(g.year,11,31));
        return {...g,partial:!!(openPeriod||missingEvidence||beforePeriodEnd)};
      });
      const history=observed.filter(g=>!g.partial), phases=config.period==='cycle'?[0,2]:[0,1,2,3];
      if(phases.some(phase=>history.filter(g=>g.year%4===phase).length<2))throw new Error(config.period==='cycle'?'An election-aware baseline needs at least four completed two-year cycles: two presidential-cycle and two midterm-cycle observations. Current, partial and missing-value periods cannot train it.':'An election-aware baseline needs at least eight completed calendar years: two observations in every phase of the four-year election calendar. Current, partial and missing-value years cannot train it.');
      if(history.some((g,i)=>i&&g.year-history[i-1].year!==step))throw new Error('The election-aware baseline needs consecutive completed periods; missing or partial history is not filled with zero.');
      // Seasonal-naïve benchmark: https://otexts.com/fpp3/simple-methods.html.
      // The four-year calendar determines matching, never an assumed dollar uplift.
      const predicted=Array.from({length:horizon},(_,i)=>{
        const year=observed.at(-1).year+step*(i+1), basis=history.findLast(g=>g.year%4===year%4);
        return {year,label:String(year),value:basis.value,forecast:true,n:0,forecast_basis_year:basis.year};
      });
      output=[...observed,...predicted];
      note+=' Dashed values are a same-election-phase historical baseline (seasonal naïve), not a calibrated prediction: each repeats the latest completed value from the same phase of the four-year calendar. Presidential and midterm differences come only from the selected history; no fixed uplift, extrapolated growth or causal effect is assumed.';
      if(observed.some(g=>g.partial))note+=' Current or partial periods remain visible as partial observations and are excluded from the baseline history.';
      note+=' Calendar closure alone does not establish collection completeness. Closed source periods without explicit completeness evidence are used as reported, with that limitation. No calibrated uncertainty interval is available; future totals can differ substantially.';
    }
    return {type:config.type,groups:output,selected:rows.length,excluded,note,temporal:true};
  }
  // chartColumns / timeColumn / identifierColumn are exported so Chart Studio
  // classifies fields through this module instead of forking the rules.
  const api = {numeric, quantile, box, filterRows, recommend, quickConfig, build, temporal,
    chartColumns, timeColumn, identifierColumn, measureScore, explodeRows, groupLimit, DEFAULT_GROUP_LIMIT,
    chartTypes:Object.freeze(chartTypes.slice()), aggregations:Object.freeze(aggregations.slice())};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.MentatCharts = api;
})(globalThis);
