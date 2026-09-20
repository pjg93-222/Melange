/* Guided Graph section: read-only, same-origin report queries and local SVG. */
(() => {
  'use strict';

  /* ----------------------------------------------------- pure row geometry
     One account of where a bar row's six columns are, shared by the drawing
     below and by app/tests/graph-layout.test.js. Keeping it pure is what lets
     the invariant be asserted without a browser: the dot, label, bar, value,
     share and sparkline boxes are pairwise disjoint and all inside [0, W].
     Painting a panel needs a document; this geometry does not, so node:test
     loads the file for the geometry and stops at the guard below. */
  const SPARK_W = 54, SPARK_GAP = 10, SHARE_W = 44, VALUE_GAP = 10;
  const BAR_MIN = 48, DOT_COL = 18, DOT_CX = 8, LABEL_SIZE = 12.5;
  function layoutColumns(width, options) {
    const opts = options || {};
    const W = Math.max(420, Math.min(920, Math.round(Number(width) || 520)));
    const sparkWidth = opts.spark ? SPARK_W : 0, sparkGap = opts.spark ? SPARK_GAP : 0;
    const sparkX = W - 4 - sparkWidth;
    // The share is anchored to the column the layout reserves for it, never to
    // the panel edge: that unconditional edge is how the percentage ended up
    // underneath the sparkline it was supposed to sit beside.
    const shareRight = W - 4 - sparkWidth - sparkGap;
    const valueRight = shareRight - SHARE_W;
    // The same label column in every panel, so bars line up between stacked
    // cards instead of each panel starting its bars at its own fraction.
    const labelRight = Math.max(130, Math.min(260, Math.round(W * 0.34)));
    const barLeft = labelRight + 8;
    const dotColumn = opts.party ? DOT_COL : 0;
    // A value column cannot eat the bar: what is left once the minimum bar and
    // its gutter are taken is the widest value column this width can carry.
    const room = Math.max(0, valueRight - barLeft - BAR_MIN - VALUE_GAP);
    const valueWidth = Math.max(0, Math.min(Number(opts.valueWidth) || 0, room));
    const barMax = Math.max(BAR_MIN, valueRight - valueWidth - VALUE_GAP - barLeft);
    return {width: W, dotColumn: dotColumn, dotCX: DOT_CX,
      labelLeft: dotColumn, labelRight: labelRight, labelWidth: labelRight - dotColumn,
      barLeft: barLeft, barMax: barMax,
      valueRight: valueRight, valueWidth: valueWidth,
      shareRight: shareRight, shareWidth: SHARE_W,
      sparkX: sparkX, sparkWidth: sparkWidth, labelSize: LABEL_SIZE};
  }
  // What fitText() is told to protect from the cut. A party CODE is worth
  // keeping whole - a truncated row still says which side of the aisle it is
  // on - but a party VALUE is not a code: 'Other / Unclassified' rode through
  // as the protected suffix and left the name a bare ellipsis, so anything
  // longer than a code is appended to the name and fitted with it.
  const PARTY_CODE_MAX = 3;
  function labelParts(name, party) {
    const text = name == null ? '' : String(name);
    const code = (party == null ? '' : String(party)).trim();
    if (!code) return {text: text, suffix: ''};
    if (Array.from(code).length <= PARTY_CODE_MAX) return {text: text, suffix: ' · ' + code};
    return {text: text + ' · ' + code, suffix: ''};
  }
  const layout = {layoutColumns: layoutColumns, labelParts: labelParts,
    PARTY_CODE_MAX: PARTY_CODE_MAX, SPARK_W: SPARK_W, SPARK_GAP: SPARK_GAP,
    SHARE_W: SHARE_W, VALUE_GAP: VALUE_GAP, BAR_MIN: BAR_MIN, DOT_COL: DOT_COL,
    DOT_CX: DOT_CX, LABEL_SIZE: LABEL_SIZE};
  if (typeof module !== 'undefined' && module.exports) module.exports = layout;
  globalThis.MentatGraphLayout = layout;
  if (typeof document === 'undefined') return;

  const get = name => document.getElementById('graph-' + name);
  const dollars = n => Number(n).toLocaleString('en-US',{style:'currency',currency:'USD',maximumFractionDigits:2});
  const titleFor = {categories:'Recipient types',organizations:'Top organizations',candidates:'Top candidates',companies:'Company comparison',levels:'Giving by employee level'};
  let analysis = 'overview';
  let loaded = false, revision = 0, view = null, category = '', recipient = '', controller = null, unavailable = [];
  // Whether this console has a report to show. The Candidate view select is
  // visible from that moment on (Paul's ruling A(ii), 2026-09-17), not only on
  // the Candidates analysis tab, so Downstream PAC activity is a control the
  // reader can see and `mode=activity` is a state a permalink can name.
  let reportChosen = false;
  // A permalink's company, cycle and tier cannot be put on the selects before
  // the first response: those options are built in render() from the view the
  // server echoes back. So they ride along with the first request instead, and
  // render()'s own options(..., view.filters.company) lands them on the selects.
  let urlScope = null;
  function options(node, values, selected='') {
    node.replaceChildren(...values.map(([id,label]) => new Option(label,id)));
    if ([...node.options].some(o=>o.value===selected)) node.value=selected;
  }
  function error(text='') {get('error').textContent=text;get('error').hidden=!text;}
  function clear() {view=null;window.dispatchEvent(new CustomEvent('mentat:graph',{detail:null}));get('results').hidden=true;get('candidate-detail').hidden=true;get('freshness').replaceChildren();get('provenance').replaceChildren();error();}
  function syncControls() {
    get('tier').disabled=get('funding').value==='corporate';
    if(get('tier').disabled)get('tier').value='';
    get('direction').parentElement.hidden=get('mode').value==='direct';
  }
  function filters() {
    return new URLSearchParams({id:get('run').value,industry:get('industry').value,
      company:urlScope?.company ?? get('company').value,
      tier:urlScope?.tier ?? get('tier').value,
      cycle:urlScope?.cycle ?? get('cycle').value,
      funding:get('funding').value,mode:get('mode').value,
      direction:get('direction').value,category,recipient});
  }
  // Graph's own defaults are absent from the URL rather than spelled out in it,
  // so a permalink names only what the reader actually chose.
  const SCOPE_DEFAULTS={mode:'direct',direction:'Support',funding:'all'};
  // The URL mirrors the request that was just made - same keys, same spellings
  // (audits/mentat_failings_20260915/contracts/url_scope.json) - so a permalink,
  // a reload and a tab switch all describe one query. A page that did not load
  // scope.js keeps working; it simply has no URL scope.
  function writeScope(query) {
    const value=key=>{const text=query.get(key)||'';return text===SCOPE_DEFAULTS[key]?'':text;};
    globalThis.MentatScope?.write({industry:query.get('industry')||'',company:query.get('company')||'',
      cycle:query.get('cycle')||'',mode:value('mode'),direction:value('direction'),
      tier:query.get('tier')||'',funding:value('funding'),
      category:query.get('category')||'',recipient:query.get('recipient')||''});
  }
  // The permalink, applied once the catalog's own options exist. A value with no
  // matching option is skipped, never invented.
  function applyUrlScope() {
    urlScope=null;
    const scope=globalThis.MentatScope?.read();
    if(!scope)return;
    for(const name of ['industry','mode','direction','funding'])
      if(scope[name]&&[...get(name).options].some(option=>option.value===scope[name]))get(name).value=scope[name];
    category=scope.category||'';recipient=scope.recipient||'';
    if(scope.company||scope.cycle||scope.tier)urlScope={company:scope.company,cycle:scope.cycle,tier:scope.tier};
  }
  // Which saved run this console reads. Chart Studio's reconciliation strip has
  // to answer this the same way Graph does - a strip that reconciles against a
  // run Graph would never display is worse than no strip - so the rule lives in
  // one function and both views call it. A run that is only ready, or awaiting
  // review, is never chosen; a run whose catalog has no industries is walked
  // past rather than displayed empty.
  function runCandidates(runs, preferred) {
    const usable = run => !['ready','needs review'].includes(run.state);
    const first = runs.find(r => r.id === preferred && usable(r))
      || runs.find(r => r.state === 'completed') || runs[0];
    return [first, ...runs.filter(usable)].filter((r,i,a) => r && a.findIndex(v => v?.id === r.id) === i);
  }
  async function chooseRun(preferred) {
    const body = await api('/api/report-sources');
    const runs = body.runs || [];
    const candidates = runCandidates(runs, preferred);
    for (const candidate of candidates) {
      const available = await api('/api/graph-catalog?id=' + encodeURIComponent(candidate.id));
      if (available.industries.length) return {runs, run: candidate, catalog: available};
    }
    return {runs, run: candidates[0] || null, catalog: null};
  }
  globalThis.MentatGraphRun = {
    choose: preferred => chooseRun(preferred === undefined ? selectedRun : preferred),
    candidates: runCandidates};

  async function loadRuns() {
    try {
      const {runs, run: chosen, catalog} = await chooseRun(selectedRun);
      options(get('run'),runs.map(r=>[r.id,`${r.name} · ${r.state}`]),chosen?.id);
      await loadCatalog(catalog);
    } catch(e){error(e.message);get('status').textContent='Report sources unavailable.';}
  }
  async function loadCatalog(preloaded=null) {
    const ticket=++revision;controller?.abort();clear();get('status').textContent='Reading saved report sources…';
    options(get('industry'),[]);options(get('company'),[['','All companies']]);options(get('cycle'),[['','All cycles']]);
    category='';recipient='';get('tier').value='';get('funding').value='all';get('mode').value='direct';reportChosen=false;urlScope=null;syncControls();
    if(!get('run').value){get('status').textContent='No saved runs available.';return;}
    try {
      const body=preloaded?.industries ? preloaded : await api('/api/graph-catalog?id='+encodeURIComponent(get('run').value));
      if(ticket!==revision)return;
      options(get('industry'),body.industries.map(i=>[i.name,i.name]));
      unavailable=body.unavailable_reports||[];
      if(unavailable.length)get('source-label').textContent='Unavailable saved reports: '+unavailable.join(', ');
      if(!body.industries.length){get('status').textContent=body.message||'This run has no finalized report. Choose another run or check Collection.';return;}
      reportChosen=true;applyUrlScope();syncControls();applyAnalysis();
      await refresh(true);
    } catch(e){if(ticket===revision){error(e.message);get('status').textContent='Report sources unavailable.';}}
  }
  async function refresh(initial=false) {
    const ticket=++revision;controller?.abort();controller=new AbortController();clear();syncControls();
    if(!get('industry').value)return;
    get('status').textContent='Reading saved giving data…';
    // One query object: the request that goes out and the URL the reader can
    // copy are the same values, and the permalink is consumed exactly once.
    const query=filters();writeScope(query);urlScope=null;
    try {
      // latest=1 makes graph_view() replace the requested cycle with max(years)
      // (graph_data.py:317-318). The URL already carries the cycle the reader
      // chose, and writeScope() has just published it, so sending latest=1 as
      // well left the URL saying 2022 while the view showed 2024. It is still
      // sent on a first load that names no cycle, which is what it is for.
      const response=await fetch('/api/graph?'+query+(initial&&!query.get('cycle')?'&latest=1':''),{signal:controller.signal});
      const body=await response.json();if(!response.ok)throw new Error(body.error||'Graph unavailable.');
      if(ticket!==revision)return;
      view=body;render();window.dispatchEvent(new CustomEvent('mentat:graph',{detail:{...body,run:get('run').value,industry:get('industry').value}}));
    } catch(e){if(ticket===revision&&e.name!=='AbortError'){error(e.message);get('status').textContent='Graph unavailable for this selection.';}}
  }
  function chip(text,clearFilter) {
    const button=document.createElement('button');button.type='button';button.className='secondary';button.textContent=text+' ×';
    button.onclick=()=>{clearFilter();refresh();};get('chips').append(button);
  }
  function render() {
    const opts=view.options;
    options(get('company'),[['','All companies'],...opts.companies.map(c=>[c,c])],view.filters.company);
    options(get('cycle'),[['','All cycles'],...opts.cycles.map(c=>[c,`${Number(c)-1}–${c}`])],view.filters.cycle);
    options(get('tier'),[['','All levels'],...['Chief','Middle-Management','Employees',...(opts.unknown_tiers?['Unknown']:[])].map(t=>[t,t])],view.filters.tier);
    syncControls();get('chips').replaceChildren();
    if(category)chip(category,()=>{category='';recipient='';});
    if(recipient)chip(opts.recipients.find(r=>r.id===recipient)?.label||recipient,()=>{recipient='';});
    // The scope sentence is no longer printed on screen - it only repeated the
    // selects the reader is looking at (UI clean-up 2026-09-17, item 1) - but
    // it is still built here, because the CSV, the image caption, the SVG
    // <desc> and the briefing slide all quote it as their scope line.
    const scope=[get('industry').value,view.filters.company||'All companies',view.filters.tier||'All levels',get('funding').selectedOptions[0].textContent,get('cycle').selectedOptions[0].textContent,category,recipient].filter(Boolean).join(' · ');
    get('scope').textContent=scope;
    get('source-label').textContent=get('run').selectedOptions[0].textContent+(unavailable.length?' · Unavailable saved reports: '+unavailable.join(', '):'');
    get('status').textContent=`${view.totals.receipt_groups.toLocaleString()} included receipt groups · local data`;
    get('total').textContent=dollars(view.totals.giving);get('direct').textContent=dollars(view.totals.direct);
    // Name the figure, so a reader can match it to Chart Studio rather than
    // wonder which of two numbers on two screens is the real one.
    get('basis-note').textContent='Net workbook receipts. Same basis as Chart Studio’s Published included receipts.';
    get('recipient-count').textContent=dollars(view.totals.organizations);
    // Each part figure carries a share bar and the share in words. The bar is
    // drawn only when the share is a real fraction of the net: a signed total
    // has no width to draw, and a bar at 0% would read as "none of it".
    for(const [name,value] of [['direct',view.totals.direct],['organization',view.totals.organizations]]) {
      const usable=view.totals.giving>0&&value>=0&&value<=view.totals.giving;
      const percent=usable?100*value/view.totals.giving:0;
      get(name+'-share').textContent=usable?percent.toFixed(1)+'% of net giving':'Share unavailable for signed totals';
      const bar=get(name+'-bar');bar.style.width=percent.toFixed(1)+'%';
      bar.parentElement.hidden=!usable;
    }
    get('candidate-note').textContent=view.candidate_note;
    // Item 4: the candidate-category receipts with no unique authorized
    // candidate link are an aside about the denominator, so they became the
    // tooltip on the candidates panel's information mark instead of a second
    // sentence of prose under the chart.
    unresolvedNote=view.filters.mode==='direct'&&view.totals.unresolved_candidate_links!==0
      ? `${dollars(view.totals.unresolved_candidate_links)} in candidate-category receipts has no unique authorized candidate link and is excluded from these rankings.`
      : '';
    get('method').textContent=view.note;
    get('provenance').replaceChildren(...view.reports.map(r=>{const p=document.createElement('p');p.className='muted';p.textContent=`${r.name} · SHA-256 ${r.sha256}`;return p;}));
    // Layout first, paint second. clear() hides #graph-results at the top of
    // refresh(), so painting here - as this did - measured clientWidth 0 on
    // every panel, fell back to 520, and left CSS to scale one column up and
    // the other down. applyAnalysis() settles which panels are shown, then the
    // results are revealed, and only then does each panel have a width to draw
    // at.
    applyAnalysis();
    get('results').hidden=false;
    paintAll();
    renderFreshness();syncExport();
  }
  function svgNode(tag,attributes={},text) {
    const node=document.createElementNS('http://www.w3.org/2000/svg',tag);
    Object.entries(attributes).forEach(([k,v])=>node.setAttribute(k,String(v)));
    if(text!==undefined)node.textContent=text;
    return node;
  }
  const PANELS=['categories','organizations','candidates','companies','levels'];
  // What each panel's share is a share OF. These are the figures the KPI strip
  // above already prints, so a reader can add a panel's shares up and land on
  // the tile the panel belongs to (item 6).
  // Downstream PAC activity and conditional industry estimates are not part of
  // "direct to candidates" - they are other committees' whole reported
  // activity - so only the direct view divides by that KPI. The other two
  // divide by the candidate rows they are showing, and the label says so.
  function denomLabel(name) {
    if(name!=='candidates')return {categories:'net giving',organizations:'recipient organizations',
      companies:'net giving',levels:'the shown levels'}[name]||'net giving';
    return view&&view.filters.mode!=='direct'?'this candidate view':'direct to candidates';
  }
  const PANEL_CLICK={
    categories:id=>{category=id;recipient='';refresh();},
    organizations:id=>{recipient=id;refresh();},
    candidates:id=>showCandidate(id),
    companies:id=>{get('company').value=id;category='';recipient='';refresh();},
    levels:id=>{get('tier').value=id;get('funding').value='personal';refresh();}
  };
  // Top N is a client-side slice of the payload the one /api/graph request has
  // already returned. /api/graph has no row-count parameter - the old global
  // "Rows per chart" input sliced in this function too - so a Top N change
  // costs no request, no route change and nothing in the URL (item 2).
  function topN(name) {
    const select=document.getElementById('graph-top-'+name);
    return Math.max(1,Number(select&&select.value)||10);
  }
  function denominator(name) {
    if(!view)return 0;
    if(name==='candidates')return view.filters.mode==='direct'
      ? view.totals.direct
      : (view.candidates||[]).reduce((sum,row)=>sum+row.amount,0);
    if(name==='levels')return (view.levels||[]).reduce((sum,row)=>sum+row.amount,0);
    if(name==='organizations')return view.totals.organizations;
    return view.totals.giving;
  }
  // Party colour only where the payload actually carries a party
  // (graph_data.py:371 joins every party recorded for a candidate). A label
  // this console cannot read as one party gets the neutral dot, never a guess.
  function partyClass(party) {
    const text=String(party||'').toUpperCase();
    if(!text)return '';
    const dem=/(^|[^A-Z])(DEM|D|DFL)([^A-Z]|$)/.test(text),rep=/(^|[^A-Z])(REP|R|GOP)([^A-Z]|$)/.test(text);
    if(dem&&!rep)return 'is-dem';
    if(rep&&!dem)return 'is-rep';
    return 'is-other';
  }
  function emptyPanel(name,message) {
    const container=get(name);container.replaceChildren();
    const p=document.createElement('p');p.className='graph-empty';p.textContent=message;container.append(p);
    const foot=document.getElementById('graph-foot-'+name);
    if(foot)foot.textContent='';
  }
  // The full-value table stays exactly where it was - inside the panel's own
  // container, built on first open - because "Full table", "View all" and the
  // lazy-table regression all reach for `#graph-<name> > details`.
  function appendValues(container,name,rows,onClick) {
    const details=document.createElement('details'),summary=document.createElement('summary');
    summary.textContent=`All ${rows.length} values`;
    let valuesBuilt=false;
    details.addEventListener('toggle',()=>{
      if(!details.open||valuesBuilt)return;
      const scroll=document.createElement('div');scroll.className='table-scroll';
      const table=document.createElement('table'),head=document.createElement('thead'),body=document.createElement('tbody');
      head.innerHTML='<tr><th>Name</th><th>Net amount</th></tr>';
      rows.forEach(row=>{const tr=document.createElement('tr'),label=document.createElement('td'),value=document.createElement('td'),button=document.createElement('button');button.type='button';button.className='graph-text-button';button.textContent=row.label;button.onclick=()=>onClick(row.id);label.append(button);value.textContent=dollars(row.amount);tr.append(label,value);body.append(tr);});
      table.append(head,body);scroll.append(table);details.append(scroll);valuesBuilt=true;
    });
    details.append(summary);container.append(details);
  }
  function footText(name,shown,total,percentages,covered) {
    return `Showing ${shown} of ${total}`+(percentages
      ? ` · ${covered.toFixed(1)}% of ${denomLabel(name)}`
      : ' · shares withheld for signed net amounts');
  }
  const ROW_HEIGHT=30,ROW_TOP=22;
  // The chart is drawn at the panel's own pixel width, so its viewBox and its
  // layout width agree and nothing is scaled: a 720-wide drawing inside a
  // 540-wide bento tile renders 13px type at under 10px. A panel with no
  // width yet - hidden, or not laid out - falls back to 520 and is redrawn by
  // panelObserver as soon as it has one.
  const panelWidth=container=>Math.max(420,Math.min(920,Math.round(container.clientWidth||520)));
  function draw(name,rows,onClick) {
    if(!rows.length){emptyPanel(name,'No nonzero amounts recorded for this selection.');return;}
    const container=get(name);container.replaceChildren();
    const shown=rows.slice(0,topN(name)),total=denominator(name);
    const spark=name==='companies';
    // The value column is as wide as the widest figure it has to hold, measured
    // at the size it is drawn at, rather than a fixed 96px guess.
    const valueWidth=shown.reduce((wide,row)=>Math.max(wide,MentatTheme.measureText(dollars(row.amount),LABEL_SIZE,MentatTheme.sans)),0);
    const box=layoutColumns(panelWidth(container),{party:name==='candidates',spark,valueWidth});
    const CHART_WIDTH=box.width,shareRight=box.shareRight,sparkX=box.sparkX,valueRight=box.valueRight;
    const LABEL_RIGHT=box.labelRight,BAR_LEFT=box.barLeft,barMax=box.barMax;
    const percentages=total>0&&shown.every(row=>row.amount>=0);
    const height=shown.length*ROW_HEIGHT+ROW_TOP+10;
    const svg=svgNode('svg',{viewBox:`0 0 ${CHART_WIDTH} ${height}`,role:'img','aria-label':titleFor[name],class:'graph-bars'});
    svg.append(svgNode('title',{},titleFor[name]),svgNode('desc',{},`${get('scope').textContent}. ${shown.length} of ${rows.length} groups. Values in USD.`));
    const positive=Math.max(0,...shown.map(r=>r.amount)),negative=Math.min(0,...shown.map(r=>r.amount));
    const scale=barMax/(positive-negative||1),zero=BAR_LEFT-negative*scale;
    const colors=MentatTheme.palette;
    let covered=0;
    shown.forEach((row,i)=>{
      const y=ROW_TOP+i*ROW_HEIGHT,label=row.label+(row.party?` · ${row.party}`:'');
      const percent=percentages?100*row.amount/total:null;
      if(percent!==null)covered+=percent;
      const party=name==='candidates'?partyClass(row.party):'';
      // Measured, not counted: the budget is the pixels between the dot column
      // and LABEL_RIGHT, and the party rides in the suffix so that it survives
      // the cut instead of being the first thing lost.
      const parts=labelParts(row.label,row.party);
      const text=MentatTheme.fitText(parts.text,box.labelWidth,LABEL_SIZE,MentatTheme.sans,parts.suffix);
      // The accessible name is unchanged: name, colon, money. The share and the
      // per-cycle figures ride in <title>, which is the hover detail (item 12).
      const group=svgNode('g',{role:'button',tabindex:0,'aria-label':`${label}: ${dollars(row.amount)}`,class:'graph-bar-button'});
      group.append(svgNode('title',{},`${label} · ${dollars(row.amount)}`+(percent!==null?` · ${percent.toFixed(1)}% of ${denomLabel(name)}`:'')));
      group.append(svgNode('rect',{x:0,y:y-13,width:CHART_WIDTH,height:ROW_HEIGHT-2,fill:'transparent','pointer-events':'all'}));
      if(party)group.append(svgNode('circle',{cx:box.dotCX,cy:y-4,r:4.5,class:'graph-party '+party}));
      group.append(svgNode('text',{x:LABEL_RIGHT,y,fill:MentatTheme.ink,'text-anchor':'end','font-family':MentatTheme.sans,'font-size':LABEL_SIZE},text));
      group.append(svgNode('rect',{x:Math.min(zero,zero+row.amount*scale),y:y-11,width:Math.max(1,Math.abs(row.amount*scale)),height:14,rx:2,fill:row.amount<0?MentatTheme.negative:colors[Math.min(i,colors.length-1)],class:'graph-mark'}));
      group.append(svgNode('text',{x:valueRight,y,fill:MentatTheme.ink,'text-anchor':'end','font-family':MentatTheme.sans,'font-size':LABEL_SIZE,class:'graph-value'},dollars(row.amount)));
      group.append(svgNode('text',{x:shareRight,y,fill:MentatTheme.muted,'text-anchor':'end','font-family':MentatTheme.sans,'font-size':11.5,class:'graph-share'},percent!==null?percent.toFixed(1)+'%':'—'));
      if(spark)group.append(svgNode('g',{class:'graph-spark','data-spark':row.id,transform:`translate(${sparkX},${y-11})`}));
      const select=()=>onClick(row.id);group.addEventListener('click',select);group.addEventListener('keydown',event=>{if(['Enter',' '].includes(event.key)){event.preventDefault();select();}});
      svg.append(group);
    });
    container.append(svg);
    appendValues(container,name,rows,onClick);
    const foot=document.getElementById('graph-foot-'+name);
    if(foot)foot.textContent=footText(name,shown.length,rows.length,percentages,covered);
  }
  // Item 11: employee level is one stacked bar with a legend. Each segment is
  // still a .graph-bar-button carrying the same accessible name the bars use,
  // so the keyboard path, the export preview count and the click-through into
  // the level are all unchanged.
  function drawStack(name,rows,onClick) {
    if(!rows.length){emptyPanel(name,'No nonzero amounts recorded for this selection.');return;}
    const container=get(name);container.replaceChildren();
    const shown=rows.slice(0,topN(name)),total=denominator(name);
    const percentages=total>0&&shown.every(row=>row.amount>=0);
    const width=panelWidth(container),height=36;
    const svg=svgNode('svg',{viewBox:`0 0 ${width} ${height}`,role:'img','aria-label':titleFor[name],class:'graph-bars graph-stack'});
    svg.append(svgNode('title',{},titleFor[name]),svgNode('desc',{},`${get('scope').textContent}. ${shown.length} of ${rows.length} levels. Values in USD.`));
    const span=shown.reduce((sum,row)=>sum+Math.max(0,row.amount),0)||1;
    const colors=MentatTheme.palette,legend=document.createElement('div');
    legend.className='graph-legend';
    let x=0,covered=0;
    shown.forEach((row,i)=>{
      const wide=percentages?Math.max(2,width*Math.max(0,row.amount)/span):Math.max(2,width/shown.length);
      const percent=percentages?100*row.amount/total:null;
      if(percent!==null)covered+=percent;
      const fill=row.amount<0?MentatTheme.negative:colors[Math.min(i,colors.length-1)];
      const group=svgNode('g',{role:'button',tabindex:0,'aria-label':`${row.label}: ${dollars(row.amount)}`,class:'graph-bar-button'});
      group.append(svgNode('title',{},`${row.label} · ${dollars(row.amount)}`+(percent!==null?` · ${percent.toFixed(1)}% of ${denomLabel(name)}`:'')));
      group.append(svgNode('rect',{x,y:6,width:wide,height:24,rx:2,fill,class:'graph-mark'}));
      const select=()=>onClick(row.id);group.addEventListener('click',select);group.addEventListener('keydown',event=>{if(['Enter',' '].includes(event.key)){event.preventDefault();select();}});
      svg.append(group);
      x+=wide;
      const item=document.createElement('button');item.type='button';item.className='graph-legend-item';
      const swatch=document.createElement('i');swatch.style.background=fill;
      const caption=document.createElement('span');
      caption.textContent=`${row.label} ${dollars(row.amount)}`+(percent!==null?` · ${percent.toFixed(1)}%`:'');
      item.append(swatch,caption);item.onclick=select;
      legend.append(item);
    });
    container.append(svg,legend);
    appendValues(container,name,rows,onClick);
    const foot=document.getElementById('graph-foot-'+name);
    if(foot)foot.textContent=footText(name,shown.length,rows.length,percentages,covered);
  }
  function drawPanel(name) {
    if(!view)return;
    const panel=get(name);
    if(panel)drawnWidth.set(name,Math.round(panel.clientWidth));
    if(name==='candidates'&&!view.candidate_available){
      emptyPanel('candidates','This candidate view is unavailable for the selected scope.');return;
    }
    if(name==='levels')drawStack(name,view.levels||[],PANEL_CLICK.levels);
    else draw(name,view[name]||[],PANEL_CLICK[name]);
    if(name==='companies')fillSparklines();
  }
  function paintAll() { for(const name of PANELS)drawPanel(name); }
  for(const name of PANELS) {
    const select=document.getElementById('graph-top-'+name);
    if(select)select.onchange=()=>{if(view)drawPanel(name);};
  }
  // A panel is redrawn when its own column changes width, and only then: the
  // drawing is sized in the viewBox, so a stale one is scaled by CSS rather
  // than relaid. A redraw at the same rounded width would repaint the same
  // pixels, and a redraw at no width at all would put the 520 fallback back,
  // so both are skipped - which is also what makes the observer unable to
  // feed itself.
  const drawnWidth=new Map(),resized=new Set();
  let resizeTimer=0;
  const RESIZE_DEBOUNCE=120;
  function redrawResized() {
    resizeTimer=0;
    const names=[...resized];resized.clear();
    if(!view)return;
    for(const name of names)drawPanel(name);
  }
  if(typeof ResizeObserver!=='undefined') {
    const panelObserver=new ResizeObserver(entries=>{
      for(const entry of entries) {
        const name=entry.target.id.replace('graph-',''),width=Math.round(entry.target.clientWidth);
        if(width>0&&drawnWidth.get(name)!==width)resized.add(name);
      }
      if(!resized.size)return;
      clearTimeout(resizeTimer);resizeTimer=setTimeout(redrawResized,RESIZE_DEBOUNCE);
    });
    for(const name of PANELS){const node=get(name);if(node)panelObserver.observe(node);}
  }
  /* --------------------------------------------------- company sparklines */
  // One /api/graph request per registered election cycle, with every other
  // filter left exactly as the panel's own request had it, cached by that
  // request string for the life of the session so the same key is never
  // fetched twice. The panel paints without them and they arrive afterwards;
  // an arrival from a scope the reader has already left is dropped by the
  // revision it was started under. Fewer than three cycles draws nothing: a
  // two-point line is a segment, not a shape.
  const sparkCache=new Map();
  const SPARK_CYCLES=5,SPARK_MINIMUM=3;
  function sparkQueries() {
    if(!view)return [];
    const cycles=[...new Set((view.options.cycles||[]).map(String))].sort();
    if(cycles.length<SPARK_MINIMUM)return [];
    return cycles.slice(-SPARK_CYCLES).map(cycle=>{
      const query=filters();query.set('cycle',cycle);query.delete('latest');
      return {cycle,key:query.toString()};
    });
  }
  async function fillSparklines() {
    const ticket=revision,queries=sparkQueries();
    if(!queries.length)return;
    const answers=await Promise.all(queries.map(async entry=>{
      if(!sparkCache.has(entry.key))sparkCache.set(entry.key,fetch('/api/graph?'+entry.key)
        .then(response=>response.ok?response.json():null)
        .then(body=>body&&!body.error&&Array.isArray(body.companies)?body.companies:null)
        .catch(()=>null));
      return {cycle:entry.cycle,rows:await sparkCache.get(entry.key)};
    }));
    if(ticket!==revision||!view)return;
    const series=new Map(),cycles=[];
    for(const answer of answers) {
      if(!answer.rows)continue;
      cycles.push(answer.cycle);
      for(const row of answer.rows) {
        if(!series.has(row.id))series.set(row.id,[]);
        series.get(row.id).push([answer.cycle,row.amount]);
      }
    }
    if(cycles.length<SPARK_MINIMUM)return;
    drawSparklines(series,cycles);
  }
  function drawSparklines(series,cycles) {
    const svg=get('companies').querySelector('svg');
    if(!svg)return;
    for(const slot of svg.querySelectorAll('[data-spark]')) {
      const points=(series.get(slot.dataset.spark)||[]).slice().sort((a,b)=>String(a[0]).localeCompare(String(b[0])));
      if(points.length<SPARK_MINIMUM)continue;
      const values=points.map(point=>point[1]),low=Math.min(...values),high=Math.max(...values);
      // The polyline is drawn into the same slot the layout reserves for it,
      // with its end dot inside: a 54px line in a 46px slot is how the last
      // point used to land past the right edge of the viewBox.
      const span=high-low||1,wide=SPARK_W-2,tall=14;
      const coords=points.map((point,i)=>[i*wide/(points.length-1),tall-2-((point[1]-low)/span)*(tall-4)]);
      slot.replaceChildren();
      slot.append(svgNode('polyline',{fill:'none','stroke-width':1.5,class:'graph-spark-line',
        points:coords.map(([x,y])=>`${x.toFixed(1)},${y.toFixed(1)}`).join(' ')}));
      slot.append(svgNode('circle',{cx:coords[coords.length-1][0].toFixed(1),cy:coords[coords.length-1][1].toFixed(1),r:1.8,class:'graph-spark-dot'}));
      const title=slot.parentElement&&slot.parentElement.querySelector('title');
      if(title&&!title.textContent.includes(points[0][0]))
        title.textContent+=' · '+points.map(([cycle,value])=>`${cycle} ${dollars(value)}`).join(' · ');
    }
    const foot=document.getElementById('graph-foot-companies');
    if(foot&&!foot.textContent.includes('sparkline'))foot.textContent+=` · sparkline ${cycles.join(' · ')}`;
  }
  function showCandidate(id) {
    const row=view.candidates.find(c=>c.id===id);if(!row)return;
    get('candidate-detail-title').textContent=`${row.label} · ${id} · ${view.filters.mode==='direct'?'Included receipt groups':'Source committee activity'}`;
    const rows=view.candidate_details.filter(r=>r.candidate_id===id);
    get('candidate-rows').replaceChildren(...rows.map(row=>{const tr=document.createElement('tr');for(const value of [row.company||'—',row.tier||'—',row.recipient,row.cycle,dollars(row.amount)]){const td=document.createElement('td');td.textContent=value;tr.append(td);}return tr;}));
    get('candidate-detail').hidden=false;get('candidate-detail').open=true;
    get('candidate-detail').scrollIntoView({behavior:'smooth',block:'nearest'});
  }
  function exportChart(name) {
    if(!view)return;
    const safe=value=>'"'+String(typeof value==='string'&&/^[=+\-@\t\r]/.test(value)?"'"+value:value).replaceAll('"','""')+'"';
    const rows=[['Graph',titleFor[name]],['Scope',get('scope').textContent],['Candidate view',get('mode').selectedOptions[0].textContent],['Direction',view.filters.mode==='direct'?'Direct':view.filters.direction],
      ['Note',name==='candidates'?view.candidate_note:view.note],...view.reports.map(r=>['Report SHA-256',r.name+' '+r.sha256]),['Name','USD','Identifier'],...view[name].map(r=>[r.label,r.amount,r.id])];
    const url=URL.createObjectURL(new Blob(['\uFEFF'+rows.map(r=>r.map(safe).join(',')).join('\r\n')],{type:'text/csv;charset=utf-8'}));
    const link=document.createElement('a');link.href=url;link.download='mentat-'+name+'.csv';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  get('run').onchange=loadCatalog;
  get('industry').onchange=()=>{category='';recipient='';options(get('company'),[['','All companies']]);options(get('cycle'),[['','All cycles']]);refresh(true);};
  for(const name of ['company','tier','cycle','funding'])get(name).onchange=()=>{category='';recipient='';if(name==='tier'&&get('tier').value)get('funding').value='personal';syncControls();refresh();};
  for(const name of ['mode','direction'])get(name).onchange=()=>{syncControls();refresh();};
  get('reset').onclick=()=>{category='';recipient='';get('company').value='';get('tier').value='';get('cycle').value=view?.options.cycles.at(-1)||'';get('funding').value='all';get('mode').value='direct';get('direction').value='Support';selectAnalysis('overview');refresh();};
  // The candidates panel's asides. The separation sentence and the server's
  // candidate note were two lines of prose wedged around the bars; they are
  // asides about the denominator, not headlines, so they ride on the panel's
  // information mark the way the other three panels' notes already do. The
  // server note stays a visible muted line whenever the figures are NOT direct
  // contributions, because then it is a disclosure rather than an aside.
  let unresolvedNote='';
  const SEPARATION='Direct contributions only. Downstream PAC activity and conditional estimates are separate candidate views.';
  function candidateAside() {
    const direct=get('mode').value==='direct',note=get('candidate-note');
    note.hidden=direct||!note.textContent;
    const text=[direct?SEPARATION:'',direct?note.textContent:'',unresolvedNote].filter(Boolean).join(' ');
    const mark=get('unresolved');
    mark.hidden=!text;mark.title=text;mark.setAttribute('aria-label',text);
  }
  function applyAnalysis() {
    const names=['overview','recipients','candidates','companies'];
    names.forEach(name=>{const tab=get('tab-'+name);tab.setAttribute('aria-selected',String(name===analysis));tab.tabIndex=name===analysis?0:-1;});
    get('analysis-panel').setAttribute('aria-labelledby','graph-tab-'+analysis);
    document.querySelector('.graph-panels').dataset.analysis=analysis;
    // Item 8: the Overview is a two by two grid of the four analyses; each tab
    // still opens its own analysis in full, with the organization breakdown
    // only where a reader asked for recipients.
    get('category-panel').hidden=!['overview','recipients'].includes(analysis);
    get('organization-panel').hidden=analysis!=='recipients';
    get('candidate-panel').hidden=!['overview','candidates'].includes(analysis);
    // Ruling A(ii): the Candidate view select appears as soon as a report is
    // chosen, wherever the candidate panel is showing, rather than only on the
    // Candidates analysis tab. Downstream PAC activity was reachable before
    // this only by finding a tab that revealed the control.
    get('candidate-controls').hidden=get('candidate-panel').hidden||!reportChosen;
    candidateAside();
    get('company-panel').hidden=!['overview','companies'].includes(analysis);
    get('level-panel').hidden=!['overview','companies'].includes(analysis);
  }
  function selectAnalysis(name,focus=false) {
    analysis=name;applyAnalysis();
    // A panel that was hidden when it was drawn had no width to draw at, so
    // the panels are redrawn as its tab opens. This costs no request: Top N is
    // a slice of the payload already in hand, and the sparkline cache is keyed
    // by request string.
    if(view)paintAll();
    get('export-target').value={overview:'categories',recipients:'organizations',candidates:'candidates',companies:'companies'}[name];syncExport();
    if(name==='overview'&&get('mode').value!=='direct'){get('mode').value='direct';refresh();}
    if(focus)get('tab-'+name).focus();
  }
  document.querySelector('.analysis-tabs').addEventListener('click',e=>{const tab=e.target.closest('[role=tab]');if(tab)selectAnalysis(tab.id.replace('graph-tab-',''));});
  document.querySelector('.analysis-tabs').addEventListener('keydown',e=>{
    const names=['overview','recipients','candidates','companies'],index=names.indexOf(analysis);
    const next={ArrowRight:(index+1)%4,ArrowLeft:(index+3)%4,Home:0,End:3}[e.key];
    if(next!==undefined){e.preventDefault();selectAnalysis(names[next],true);}
  });
  function showValues(name) {
    selectAnalysis({categories:'recipients',organizations:'recipients',candidates:'candidates',companies:'companies',levels:'companies'}[name]);
    get('export-target').value=name;syncExport();
    const details=get(name).querySelector('details');if(details){details.open=true;details.scrollIntoView({block:'nearest'});details.querySelector('summary').focus();}
  }
  document.querySelectorAll('[data-analysis-tab]').forEach(b=>b.onclick=()=>selectAnalysis(b.dataset.analysisTab,true));
  document.querySelectorAll('[data-values]').forEach(b=>b.onclick=()=>showValues(b.dataset.values));
  get('view-candidates').onclick=()=>showValues('candidates');
  get('full-table').onclick=()=>showValues(get('export-target').value);
  function syncExport() {
    const name=get('export-target').value;
    get('export').disabled=!view||(name==='candidates'&&!view.candidate_available)||!view[name]?.length;
    get('full-table').disabled=get('export').disabled;
    get('copy-image').disabled=get('export').disabled;
    get('briefing').disabled=get('export').disabled;
  }
  get('export-target').onchange=syncExport;
  // One set of panel actions, wherever the reader presses it: a panel's own
  // Export menu and the view's export line both go through the same
  // exportSubject() / exportChart() pair, so the two can never disagree about
  // which chart, which scope or which provenance they are writing out.
  document.querySelectorAll('#view-graph [data-export]').forEach(button=>{
    button.onclick=()=>{
      const name=button.dataset.export,format=button.dataset.format;
      const menu=button.closest('details');
      if(menu)menu.open=false;
      get('export-target').value=name;syncExport();
      if(format==='table'){showValues(name);return;}
      if(format==='copy'){get('copy-image').click();return;}
      if(format==='briefing'){get('briefing').click();return;}
      get('export-format').value=format;get('export').click();
    };
  });
  // A menu left open after the reader has moved on is a menu in the way. Only
  // an outside click closes them: Escape belongs to the dialogs these menus
  // open, and a menu that vanished on Escape would take the button the dialog
  // has to return focus to with it.
  document.addEventListener('click',event=>{
    for(const menu of document.querySelectorAll('#view-graph details.graph-menu[open]'))
      if(!menu.contains(event.target))menu.open=false;
  });
  // One account of the chart being exported, read by the download, the
  // clipboard copy and the briefing, so the three can never disagree.
  function exportSubject() {
    if(!view)return null;
    const name=get('export-target').value;
    if(name==='candidates'&&!view.candidate_available)return null;
    const svg=get(name).querySelector('svg');
    if(!svg)return null;
    const note=name==='candidates'?view.candidate_note:view.note;
    const context=`${get('scope').textContent}. ${name==='candidates'?get('mode').selectedOptions[0].textContent+'. '+(view.filters.mode==='direct'?'':view.filters.direction+'. '):''}${note} Preview: ${get(name).querySelectorAll('svg .graph-bar-button').length} of ${view[name].length} groups. `+view.reports.map(r=>`${r.name} SHA-256 ${r.sha256}`).join('; ');
    return {name,svg,title:titleFor[name],context,reports:view.reports};
  }
  get('export').onclick=async()=>{
    if(!view)return;
    const format=get('export-format').value,subject=exportSubject();
    if(!subject)return;
    if(format==='csv'){exportChart(subject.name);return;}
    try {await MentatExport.image(subject.svg,format,subject.title,subject.context,'mentat-'+subject.name);}
    catch(e){error(e.message);}
  };
  get('copy-image').onclick=async()=>{
    const subject=exportSubject();
    if(!subject){error('No image to copy. Export the CSV instead.');return;}
    error('');
    try {await MentatExport.copy(subject.svg,subject.title,subject.context);}
    catch(e){error(e.message);}
  };
  get('briefing').onclick=()=>{
    const subject=exportSubject();
    if(!subject){error('No image to add. Export the CSV instead.');return;}
    if(!window.MentatBriefing){error('Briefing needs a console restart.');return;}
    error('');
    const report=(subject.reports||[])[0]||{};
    window.MentatBriefing.capture({svg:subject.svg,title:subject.title,scope:subject.context,
      chip:get('scope').textContent,note:'',basis:'Graph totals',sheetId:subject.name,sheetName:subject.title,
      source:report.name||'',provenance:report.sha256||'',origin:'graph'});
  };
  function renderFreshness() {
    const host=get('freshness');host.replaceChildren();
    const field=(node,label,value)=>{
      const row=document.createElement('div');row.className='source-field';
      const key=document.createElement('span'),val=document.createElement('span');key.textContent=label;val.textContent=value||'Unknown';
      if(!value)val.className='freshness-unknown';row.append(key,val);node.append(row);
    };
    view.reports.forEach(report=>{
      const fresh=report.freshness||{},section=document.createElement('section');section.className='source-receipt';
      const h=document.createElement('h3');h.textContent=report.name;section.append(h);
      field(section,'Report file modified',fresh.report_modified_at);
      const status=document.createElement('p');status.className='chart-note';status.textContent='Overall report freshness unknown. Source dates do not establish complete search coverage.';section.append(status);
      for(const source of fresh.sources||[]) {
        const group=document.createElement('section');group.className='source-receipt';
        const name=document.createElement('h3');name.textContent=[source.source,source.cycle].filter(Boolean).join(' · ');group.append(name);
        field(group,'Retrieved',source.retrieved_at);field(group,'File modified',source.file_modified_at);field(group,'Verified data through',source.verified_data_through);
        const badge=document.createElement('p');badge.className=source.verified_data_through?'freshness-verified':'freshness-unknown';badge.textContent=source.verified_data_through?'Verified date in receipt':'Freshness unknown';group.append(badge);
        const details=document.createElement('details'),summary=document.createElement('summary'),receipt=document.createElement('p');summary.textContent='Source receipt';receipt.className='chart-note';receipt.textContent=[source.receipt,source.local_receipt,source.sha256,source.note,source.verification_evidence].filter(Boolean).join(' · ')||'Receipt unavailable';details.append(summary,receipt);
        field(details,'Last checked',source.checked_at);field(details,'Server last modified',source.server_last_modified);group.append(details);section.append(group);
      }
      if(!fresh.sources?.length)field(section,'Source freshness',null);
      for(const issue of fresh.issues||[]){const p=document.createElement('p');p.className='freshness-unknown';p.textContent=issue;section.append(p);}
      host.append(section);
    });
  }
  for(const name of ['sources','builder']) {
    get('open-'+name).onclick=()=>{get(name).showModal();if(name==='builder')get(name).dispatchEvent(new Event('mentat:open'));};
    get('close-'+name).onclick=()=>get(name).close();
  }
  let reportSignature='';
  window.addEventListener('mentat:run',event=>{
    const run=event.detail;if(!loaded||get('run').value!=='published-reports')return;
    const signature=JSON.stringify(run.reports.map(r=>[r.index,r.quality?.sha256]));
    if(reportSignature&&signature!==reportSignature)loadCatalog();
    reportSignature=signature;
  });
  applyAnalysis();
  function activate(){if((currentView==='graph'||(currentView==='evidence'&&splitView))&&!loaded){loaded=true;loadRuns();}}
  window.addEventListener('mentat:view',activate);
  document.querySelector('.workspace-tabs').addEventListener('click',activate);
  document.querySelector('.workspace-tabs').addEventListener('keydown',activate);
  window.addEventListener('hashchange',activate);activate();
})();
