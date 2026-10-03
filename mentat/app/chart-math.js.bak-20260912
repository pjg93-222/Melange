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
    if (data.independent_series != null && new Set(filterRows(data,config).map(r=>r[data.independent_series])).size > 1) throw new Error('Use side-by-side bars, horizontal comparison or separate lines to keep funding sources and activities separate.');
    if (config.transform && config.transform !== 'none') return temporal(data, config);
    if (!['bar','pie','line','scatter','box','histogram','area','doughnut','waterfall','radar','horizontal','pareto'].includes(config.type)) throw new Error('Choose a chart type.');
    if (!['sum','mean','count','median','min','max'].includes(config.aggregation)) throw new Error('Choose an aggregation.');
    const rows = filterRows(data, config), points = [], groups = new Map();
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
    if (groups.size > 60) throw new Error('Filter to 60 groups or fewer, or choose a different grouping column.');
    let output = [...groups].map(([label, values]) => config.type === 'box' ? {label, ...box(values)} :
      {label, value:count ? values.length : config.aggregation==='median'?quantile(values.slice().sort((a,b)=>a-b),.5):config.aggregation==='min'?Math.min(...values):config.aggregation==='max'?Math.max(...values):values.reduce((a,b) => a+b,0) / (config.aggregation === 'mean' ? values.length : 1), n:values.length});
    if (['line','area'].includes(config.type)) output.sort((a,b) => a.label.localeCompare(b.label, undefined, {numeric:true}));
    if (config.type==='pareto')output.sort((a,b)=>b.value-a.value);
    if(config.type==='radar'&&output.length<3)throw new Error('Radar charts need at least three groups.');
    if (['pie','doughnut','pareto','radar'].includes(config.type) && !output.some(g => g.value > 0)) throw new Error('This chart needs a positive total.');
    return {type:config.type, groups:output, selected:rows.length, excluded};
  }
  function grouped(data, config) {
    if (config.transform && config.transform !== 'none') throw new Error('Choose None for time analysis to compare separate series.');
    if (!data.columns[config.x] || !data.columns[config.series]) throw new Error('Choose a grouping column and a separate series.');
    if(data.independent_series!=null && config.x!==data.independent_series && config.series!==data.independent_series && new Set(filterRows(data,config).map(r=>r[data.independent_series])).size>1)throw new Error('Keep Source / activity as the grouping or separate series so independent amounts are not combined.');
    if (!['sum','mean','count','median','min','max'].includes(config.aggregation)) throw new Error('Choose an aggregation.');
    const order=data.independent_series==null || config.series===data.independent_series ? data.series_order||[] : [];
    const rows=filterRows(data,config), groups=new Map(), series=new Set(order);let excluded=0;
    for(const row of rows) {
      const label=String(row[config.x]??'(Missing)'), name=String(row[config.series]??'(Missing)');
      if(!groups.has(label))groups.set(label,new Map());series.add(name);
      const value=config.aggregation==='count'?1:numeric(row[config.y]);
      if(value===null){excluded++;continue;}
      if(!groups.get(label).has(name))groups.get(label).set(name,[]);
      groups.get(label).get(name).push(value);
    }
    if(!rows.length)throw new Error('No rows match this subsection.');
    if(groups.size>60)throw new Error('Choose 60 recipients per view or fewer.');
    const output=[...groups].map(([label,values])=>({label,values:[...series].map(name=>{
      const a=values.get(name);return {series:name,value:!a?null:config.aggregation==='count'?a.length:config.aggregation==='median'?quantile(a.slice().sort((a,b)=>a-b),.5):config.aggregation==='min'?Math.min(...a):config.aggregation==='max'?Math.max(...a):a.reduce((n,v)=>n+v,0)/(config.aggregation==='mean'?a.length:1),n:a?.length||0};
    })}));
    return {type:config.type,groups:output,series:[...series],selected:rows.length,excluded,note:'Series are independent; no combined total. Gaps mean unavailable observations, not zero.'};
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
    chartColumns, timeColumn, identifierColumn, measureScore,
    chartTypes:Object.freeze(chartTypes.slice()), aggregations:Object.freeze(aggregations.slice())};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.MentatCharts = api;
})(globalThis);
