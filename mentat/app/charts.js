/* The graph explorer makes same-origin reads only; SVG is generated locally. */
(() => {
  'use strict';
  const el = id => document.getElementById('chart-' + id);
  const esc = escapeHtml, math = globalThis.MentatCharts;
  let data = null, suggestions = [], revision = 0, chart = null, chartConfig = null;
  const palette = MentatTheme.palette;
  const fmt = n => Number(n).toLocaleString('en-US', {maximumFractionDigits:3});
  function error(message='') { el('error').textContent = message; el('error').hidden = !message; }
  function clearChart() { chart = null; el('image').replaceChildren(); el('values').replaceChildren(); el('export').hidden = true; el('scope').textContent = ''; }
  function reset() { data = null; clearChart(); error(); el('settings').disabled = true; el('columns').replaceChildren(); el('context').textContent = 'Choose a worksheet to begin.'; }
  function options(node, items) { node.replaceChildren(...items.map(([value,label]) => new Option(label, value))); }
  function requestPath(sheet='', header=0) {
    const params = new URLSearchParams({id:el('run').value, index:el('report').value});
    if (sheet) params.set('sheet', sheet);
    if (header) params.set('header', header);
    return '/api/report-data?' + params;
  }
  async function loadRuns() {
    try {
      const body = await api('/api/runs');
      options(el('run'), body.runs.map(r => [r.id, r.name]));
      const preferred = body.runs.find(r => r.id === selectedRun && !['ready','needs review'].includes(r.state))
        || body.runs.find(r => r.state === 'completed');
      if (preferred) el('run').value = preferred.id;
      await loadReports();
    } catch (e) { error(e.message); }
  }
  async function loadReports() {
    const ticket = ++revision; reset(); options(el('report'), []); options(el('sheet'), []);
    el('loading').textContent = 'Reading reports…';
    try {
      if (!el('run').value) { el('loading').textContent = 'No collection runs available.'; return; }
      const run = await api('/api/run?id=' + encodeURIComponent(el('run').value));
      if (ticket !== revision) return;
      options(el('report'), run.reports.map(r => [r.index, r.name]));
      if (!run.reports.length) { el('loading').textContent = 'This run has no completed reports.'; return; }
      await loadSheets();
    } catch (e) { if (ticket === revision) { error(e.message); el('loading').textContent = 'Report list unavailable.'; } }
  }
  async function loadSheets() {
    const ticket = ++revision; reset(); options(el('sheet'), []); el('loading').textContent = 'Reading worksheets…';
    try {
      const body = await api(requestPath());
      if (ticket !== revision) return;
      options(el('sheet'), body.sheets.map(s => [s,s]));
      const preferred = ['Candidate Funding','Funding Cohorts','Allocation Estimates','Beneficiary Summary'].find(s => body.sheets.includes(s));
      if (preferred) el('sheet').value = preferred;
      await scan();
    } catch (e) { if (ticket === revision) { error(e.message); el('loading').textContent = 'Worksheets unavailable.'; } }
  }
  async function scan(manual=false) {
    const ticket = ++revision; reset(); el('loading').textContent = 'Scanning columns…';
    try {
      if (manual && !el('header').reportValidity()) throw new Error('Enter a header row from 1 to 100.');
      const body = await api(requestPath(el('sheet').value, manual ? Number(el('header').value) : 0));
      if (ticket !== revision) return;
      data = body; el('header').value = data.header_row; el('settings').disabled = false;
      el('filters').replaceChildren(); el('start').value = ''; el('end').value = '';
      el('loading').textContent = `${fmt(data.row_count)} rows · ${data.columns.length} columns scanned`;
      el('context').textContent = data.note;
      options(el('x'), [[-1,'All rows'], ...data.columns.map(c => [c.index, `${c.name} · ${c.type}`])]);
      options(el('y'), data.columns.map(c => [c.index, `${c.name} · ${c.type}`]));
      suggestions = math.recommend(data.columns);
      options(el('suggestion'), suggestions.length ? suggestions.map((s,i) => [i,s.label]) : [['','Choose columns below']]);
      el('columns').innerHTML = data.columns.map(c => `<tr><td>${esc(c.name)}</td><td>${esc(c.type)}</td><td>${fmt(c.distinct)}</td><td>${fmt(c.missing)}</td></tr>`).join('');
      if (suggestions.length) { applySuggestion(); create(); }
    } catch (e) { if (ticket === revision) { error(e.message); el('loading').textContent = 'Column scan unavailable.'; } }
  }
  function applySuggestion() {
    const s = suggestions[Number(el('suggestion').value)]; if (!s) return;
    el('type').value = s.type; el('x').value = s.x; if (s.y >= 0) el('y').value = s.y;
    el('aggregation').value = s.aggregation; syncControls(); clearChart();
  }
  function syncControls() {
    const type = el('type').value;
    el('aggregation').disabled = ['box','scatter','histogram'].includes(type);
    el('x').disabled = type === 'histogram';
    el('y').disabled = !el('aggregation').disabled && el('aggregation').value === 'count';
  }
  function addFilter() {
    if (!data) return;
    const row = document.createElement('div'); row.className = 'chart-filter';
    const column = document.createElement('select'); column.setAttribute('aria-label','Filter column');
    options(column, data.columns.map(c => [c.index,c.name]));
    const op = document.createElement('select'); op.setAttribute('aria-label','Filter operation');
    options(op, [['equals','Equals'],['contains','Contains'],['gte','At least'],['lte','At most']]);
    const value = document.createElement('input'); value.setAttribute('aria-label','Filter value'); value.placeholder = 'Value';
    const remove = document.createElement('button'); remove.type = 'button'; remove.className = 'secondary'; remove.textContent = 'Remove filter';
    remove.onclick = () => { row.remove(); clearChart(); };
    row.append(column,op,value,remove); el('filters').append(row); clearChart();
  }
  function configuration() {
    if (!el('start').reportValidity() || !el('end').reportValidity()) throw new Error('Enter valid worksheet row numbers.');
    return {type:el('type').value, x:Number(el('x').value), y:Number(el('y').value), aggregation:el('aggregation').value,
      start:Number(el('start').value), end:Number(el('end').value), filters:[...el('filters').children].map(row => ({
        column:Number(row.children[0].value), op:row.children[1].value, value:row.children[2].value}))};
  }
  function create() {
    error(); clearChart(); if (!data) return;
    try {
      chartConfig = configuration(); chart = math.build(data, chartConfig);
      const count = chartConfig.aggregation === 'count' && ['bar','line','pie'].includes(chart.type);
      const measure = count ? 'Row count' : data.columns[chartConfig.y].name;
      el('title').textContent = `${measure} · ${el('type').selectedOptions[0].textContent}`;
      const filterText = chartConfig.filters.map(f => `${data.columns[f.column].name} ${f.op} ${f.value}`).join('; ');
      const group = chart.type === 'histogram' ? 'Numeric bins' : data.columns[chartConfig.x]?.name || 'All rows';
      el('scope').textContent = `${el('report').selectedOptions[0].textContent} / ${data.sheet} · ${chart.selected} of ${data.row_count} rows selected; ${chart.excluded} rows excluded for missing/non-numeric values. Group/X: ${group}. ${['box','scatter','histogram'].includes(chart.type) ? 'Individual worksheet values.' : 'Aggregation: ' + chartConfig.aggregation + '.'} Worksheet rows: ${chartConfig.start || 'first data row'}–${chartConfig.end || 'last data row'}. Filters: ${filterText || 'none'}. SHA-256: ${data.sha256}.` +
        (chart.type === 'box' ? ' Quartiles use linear interpolation; whiskers end at observations within 1.5×IQR; dots show outliers.' : '');
      draw(chart, measure); renderValues(); el('export').hidden = false;
    } catch (e) { clearChart(); error(e.message); }
  }
  function svgNode(tag, attrs={}, text) {
    const node = document.createElementNS('http://www.w3.org/2000/svg',tag);
    for (const [k,v] of Object.entries(attrs)) node.setAttribute(k,String(v));
    if (text != null) node.textContent = text; return node;
  }
  function draw(result, measure) {
    const svg = svgNode('svg',{xmlns:'http://www.w3.org/2000/svg',viewBox:'0 0 960 560',role:'img','aria-label':el('title').textContent});
    const add = (tag,attrs,text) => { const n = svgNode(tag,attrs,text); svg.append(n); return n; };
    add('title',{},el('title').textContent); add('desc',{},el('scope').textContent);
    add('rect',{width:960,height:560,fill:'#fff'});
    const label = (x,y,text,attrs={}) => add('text',{x,y,fill:MentatTheme.ink,'font-family':MentatTheme.sans,'font-size':12,...attrs},text);
    label(20,25,el('title').textContent,{'font-size':20,'font-weight':400,'font-family':MentatTheme.serif});
    label(20,48,`${data.sheet} · ${result.selected - result.excluded} plotted rows`);
    const tooltip = (node,text) => node.append(svgNode('title',{},text));
    if (result.type === 'pie') {
      const total = result.groups.reduce((n,g) => n+g.value,0); let angle = -Math.PI/2;
      result.groups.forEach((g,i) => {
        const next = angle + 2*Math.PI*g.value/total, color = palette[i%palette.length], cx=285,cy=290,r=175;
        if (g.value > 0) {
          const node = g.value === total ? add('circle',{cx,cy,r,fill:color}) : add('path',{
            d:`M ${cx} ${cy} L ${cx+r*Math.cos(angle)} ${cy+r*Math.sin(angle)} A ${r} ${r} 0 ${next-angle > Math.PI ? 1:0} 1 ${cx+r*Math.cos(next)} ${cy+r*Math.sin(next)} Z`,fill:color,stroke:'#fff','stroke-width':2});
          tooltip(node,`${g.label}: ${fmt(g.value)} (${(100*g.value/total).toFixed(1)}%)`);
        }
        if (i < 16) { add('rect',{x:510,y:85+i*27,width:12,height:12,fill:color}); label(533,96+i*27,`${g.label.slice(0,34)} · ${(100*g.value/total).toFixed(1)}%`); }
        angle = next;
      });
      if (result.groups.length > 16) label(510,535,'Full labels and values are in the chart table below.');
    } else {
      const groups = result.groups || [], isBox = result.type === 'box', scatter = result.type === 'scatter';
      const values = scatter ? result.points.map(p=>p.y) : isBox ? groups.flatMap(g=>[g.low,g.high,...g.outliers]) : groups.map(g=>g.value);
      let min = Math.min(...values), max = Math.max(...values);
      if (!isBox && !scatter) { min = Math.min(0,min); max = Math.max(0,max); }
      if (min === max) { min -= Math.abs(min)*.1 || 1; max += Math.abs(max)*.1 || 1; }
      const y = v => 430 - (v-min)/(max-min)*335;
      for (let i=0;i<=5;i++) { const value=min+(max-min)*i/5; add('line',{x1:100,x2:920,y1:y(value),y2:y(value),stroke:MentatTheme.grid}); label(90,y(value)+4,fmt(value),{'text-anchor':'end'}); }
      label(100,78,result.type === 'histogram' ? 'Row count' : measure);
      if (scatter) {
        const xs=result.points.map(p=>p.x); let lo=Math.min(...xs),hi=Math.max(...xs); if(lo===hi){lo--;hi++;}
        const x=v=>100+(v-lo)/(hi-lo)*820;
        result.points.forEach(p=>tooltip(add('circle',{cx:x(p.x),cy:y(p.y),r:4,fill:palette[0],'fill-opacity':.65}),`${fmt(p.x)}, ${fmt(p.y)}`));
        for(let i=0;i<=5;i++){const v=lo+(hi-lo)*i/5;label(x(v),453,fmt(v),{'text-anchor':'middle'});}
        label(510,495,data.columns[chartConfig.x].name,{'text-anchor':'middle'});
      } else {
        const step=820/groups.length, x=i=>100+step*(i+.5), width=Math.min(60,step*.7);
        if (result.type==='line') add('polyline',{points:groups.map((g,i)=>`${x(i)},${y(g.value)}`).join(' '),fill:'none',stroke:palette[0],'stroke-width':2});
        groups.forEach((g,i)=>{
          const color=palette[i%palette.length];
          if(isBox){
            add('line',{x1:x(i),x2:x(i),y1:y(g.low),y2:y(g.high),stroke:color,'stroke-width':2});
            for(const v of [g.low,g.high])add('line',{x1:x(i)-width/3,x2:x(i)+width/3,y1:y(v),y2:y(v),stroke:color,'stroke-width':2});
            tooltip(add('rect',{x:x(i)-width/2,y:y(g.q3),width,height:Math.max(1,y(g.q1)-y(g.q3)),fill:color,'fill-opacity':.25,stroke:color}),`${g.label}: median ${fmt(g.median)}, Q1 ${fmt(g.q1)}, Q3 ${fmt(g.q3)}, n=${g.n}`);
            add('line',{x1:x(i)-width/2,x2:x(i)+width/2,y1:y(g.median),y2:y(g.median),stroke:color,'stroke-width':3});
            g.outliers.forEach(v=>tooltip(add('circle',{cx:x(i),cy:y(v),r:3,fill:color}),`${g.label}: ${fmt(v)} (outlier)`));
          }else if(result.type==='line') tooltip(add('circle',{cx:x(i),cy:y(g.value),r:4,fill:palette[0]}),`${g.label}: ${fmt(g.value)}`);
          else tooltip(add('rect',{x:x(i)-width/2,y:Math.min(y(0),y(g.value)),width,height:Math.max(1,Math.abs(y(0)-y(g.value))),fill:color}),`${g.label}: ${fmt(g.value)}`);
          if(i % Math.max(1,Math.ceil(groups.length/16)) === 0) label(x(i),450,g.label.length>20 ? g.label.slice(0,18)+'…' : g.label,{transform:`rotate(35 ${x(i)} 450)`});
        });
      }
    }
    el('image').replaceChildren(svg);
  }
  function tableRows() {
    if (chart.type === 'scatter') return [['X','Y'], ...chart.points.map(p=>[p.x,p.y])];
    if (chart.type === 'box') return [['Group','Count','Q1','Median','Q3','Lower whisker','Upper whisker','Outliers'],...chart.groups.map(g=>[g.label,g.n,g.q1,g.median,g.q3,g.low,g.high,g.outliers.join('; ')])];
    return [['Group','Value'],...chart.groups.map(g=>[g.label,g.value])];
  }
  function renderValues() {
    const [head,...rows]=tableRows();
    el('values').innerHTML='<table><thead><tr>'+head.map(h=>`<th>${esc(h)}</th>`).join('')+'</tr></thead><tbody>'+rows.map(r=>'<tr>'+r.map(v=>`<td>${esc(typeof v==='number'?fmt(v):v)}</td>`).join('')+'</tr>').join('')+'</tbody></table>';
  }
  function download(content,type,name) {
    const url=URL.createObjectURL(new Blob([content],{type})), link=document.createElement('a');
    link.href=url; link.download=name; link.click(); setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  for(const format of ['svg','png']) el('save-'+format).onclick=async()=>{
    if(!chart)return;
    try {await MentatExport.image(el('image').firstChild,format,el('title').textContent,el('scope').textContent);}
    catch(e){error(e.message);}
  };
  el('save-csv').onclick=()=>{
    if(!chart)return;
    const quote=v=>'"'+String(typeof v==='string' && /^[=+\-@\t\r]/.test(v)?"'"+v:v).replaceAll('"','""')+'"';
    const rows=[['Chart',el('title').textContent],['Scope',el('scope').textContent],...tableRows()];
    download('\uFEFF'+rows.map(r=>r.map(quote).join(',')).join('\r\n'),'text/csv;charset=utf-8','mentat-chart.csv');
  };
  el('run').onchange=loadReports; el('report').onchange=loadSheets; el('sheet').onchange=()=>scan();
  el('rescan').onclick=()=>scan(true); el('suggestion').onchange=applySuggestion; el('add-filter').onclick=addFilter; el('create').onclick=create;
  el('settings').addEventListener('input',()=>{syncControls();clearChart();error();});
  el('header').addEventListener('input',()=>{clearChart();el('settings').disabled=true;el('loading').textContent='Rescan columns to apply the new header row.';});
  let loaded=false;
  function activate() {if(currentView==='graph' && document.getElementById('graph-builder').open && !loaded){loaded=true;loadRuns();}}
  document.getElementById('graph-builder').addEventListener('mentat:open',activate);
  document.getElementById('graph-advanced').addEventListener('toggle',activate);
  document.querySelector('.workspace-tabs').addEventListener('click',activate);
  document.querySelector('.workspace-tabs').addEventListener('keydown',activate);
  window.addEventListener('hashchange',activate); activate();
})();
