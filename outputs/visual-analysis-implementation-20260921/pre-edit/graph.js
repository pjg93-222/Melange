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
  const SPARK_W = 54, SPARK_GAP = 10, SHARE_W = 46, VALUE_GAP = 10;
  const BAR_MIN = 48, DOT_COL = 22, DOT_CX = 9, LABEL_SIZE = 13;
  /* The card's own rhythm, from the approved board: 34px between row
     baselines, 24px of head room above the first, 13px label and value,
     12px share. Top organizations is the one two-line panel - the name owns
     the first line at the card's full width, the bar, value and share the
     second - because a registered PAC name does not fit a third of a card
     and was arriving as an ellipsis. These live beside the columns so the
     geometry suite can pin the pitch instead of the drawing re-deciding it. */
  const ROW_PITCH = 34, ROW_HEAD = 24, TWO_LINE_PITCH = 50, SHARE_SIZE = 12;
  const TWO_LINE_NAME_DROP = 20;
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
  /* ------------------------------------------------- pure navigation model
     Which parts of the scope trail are shown, what pressing one clears, and how
     deep the Back stack goes. It lives beside the geometry and above the
     document guard for the same reason: app/tests/graph-navigation.test.js can
     assert it without a browser, and the drawing below has one account to
     follow rather than a second one of its own. */
  const TRAIL_ORDER = ['industry', 'company', 'category', 'recipient'];
  const PAST_MAX = 20;
  // Only the parts that are set. `index` is the part's place in TRAIL_ORDER, not
  // its place on screen: a trail with no company still clears the right things.
  function trailModel(scope) {
    const named = scope || {};
    return TRAIL_ORDER
      .map((key, index) => ({key: key, index: index,
        label: String(named[key] == null ? '' : named[key])}))
      .filter(part => part.label);
  }
  // Pressing a part clears it and everything to its right. The industry is the
  // one exception: a Graph with no industry has nothing to show, so pressing it
  // returns to the whole industry rather than leaving the page unloadable.
  function clearedBy(index) {
    return TRAIL_ORDER.slice(Math.max(1, Number(index) || 0));
  }
  // The oldest entry is dropped, never the newest: a reader twenty-one steps in
  // can still go back one.
  function pushPast(stack, entry, max) {
    const ceiling = max === undefined ? PAST_MAX : max;
    const kept = (stack || []).concat([entry]);
    return kept.slice(Math.max(0, kept.length - ceiling));
  }
  const layout = {layoutColumns: layoutColumns, labelParts: labelParts,
    PARTY_CODE_MAX: PARTY_CODE_MAX, SPARK_W: SPARK_W, SPARK_GAP: SPARK_GAP,
    SHARE_W: SHARE_W, VALUE_GAP: VALUE_GAP, BAR_MIN: BAR_MIN, DOT_COL: DOT_COL,
    DOT_CX: DOT_CX, LABEL_SIZE: LABEL_SIZE, ROW_PITCH: ROW_PITCH,
    ROW_HEAD: ROW_HEAD, TWO_LINE_PITCH: TWO_LINE_PITCH, SHARE_SIZE: SHARE_SIZE,
    TWO_LINE_NAME_DROP: TWO_LINE_NAME_DROP,
    trailModel: trailModel, clearedBy: clearedBy, pushPast: pushPast,
    TRAIL_ORDER: TRAIL_ORDER, PAST_MAX: PAST_MAX};
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
  /* Four card skeletons in the shape the panels will take, so a 20-35 second
     Banking read is a page that is filling rather than a page that is empty.
     The status line above them keeps saying what is being read. */
  function skeleton(on) {const node=get('skeleton');if(node)node.hidden=!on;}
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
    pendingDrawer=scope.drawer?{id:scope.drawer,direction:scope.drawerDirection||''}:null;
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
    if(!get('industry').value){skeleton(false);return;}
    get('status').textContent='Reading saved giving data…';
    skeleton(true);
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
    } catch(e){if(ticket===revision&&e.name!=='AbortError'){skeleton(false);error(e.message);get('status').textContent='Graph unavailable for this selection.';}}
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
    roll('total',view.totals.giving);roll('direct',view.totals.direct);
    // Name the figure, so a reader can match it to Chart Studio rather than
    // wonder which of two numbers on two screens is the real one.
    get('basis-note').textContent='Net workbook receipts. Same basis as Chart Studio’s Published included receipts.';
    roll('recipient-count',view.totals.organizations);
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
    skeleton(false);
    get('results').hidden=false;
    paintAll(true);
    renderFreshness();syncExport();renderTrail();restoreDrawer();
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
    categories:id=>{remember();category=id;recipient='';closeDrawer(false);pendingDrawer=null;refresh();},
    // A PAC click still narrows the page to that PAC - that is what the chip,
    // the trail and the permalink all describe - and now also opens the drawer
    // beside the panel, which is the second hop the reader came for.
    organizations:id=>{remember();recipient=id;closeDrawer(false);pendingDrawer={id,direction:''};refresh();},
    candidates:id=>showCandidate(id),
    companies:id=>{remember();get('company').value=id;category='';recipient='';closeDrawer(false);pendingDrawer=null;refresh();},
    levels:id=>{remember();get('tier').value=id;get('funding').value='personal';refresh();}
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
  function emptyPanel(name,message,host,footNode) {
    const container=host||get(name);container.replaceChildren();
    const p=document.createElement('p');p.className='graph-empty';p.textContent=message;container.append(p);
    const foot=footNode===null?null:(footNode||document.getElementById('graph-foot-'+name));
    if(foot)foot.textContent='';
  }
  /* MOTION. One switch: the reduced-motion media query rewrites --motion in
     graph.css, and everything here - the CSS animations and the JS number
     roll alike - reads that token rather than asking matchMedia a second
     time. A stagger of 42ms is capped at seven steps so a fifty-row panel
     still finishes growing inside 300ms. */
  const MOTION_STEPS=7;
  function motionMs() {
    const raw=getComputedStyle(document.documentElement).getPropertyValue('--motion');
    const value=parseFloat(raw);
    return Number.isFinite(value)?(raw.trim().endsWith('ms')?value:value*1000):0;
  }
  // An entrance is over once it has run; the class goes with it, so a chart
  // exported later cannot carry an animation the export would have to strip.
  function settle(svg) {
    setTimeout(()=>{
      svg.classList.remove('graph-enter');
      for(const node of svg.querySelectorAll('[style]'))node.style.removeProperty('--i');
    },Math.max(40,motionMs()+MOTION_STEPS*42+120));
  }
  const rolled=new Map();
  // The three figures in the strip travel from the number that was there to
  // the number that replaced it, so a scope change is legible as a change.
  // A figure nobody has seen yet is simply written: there is nothing to roll
  // from, and a roll from zero would read as growth that did not happen.
  function roll(name,value) {
    const node=get(name),from=rolled.get(name),to=Number(value)||0;
    rolled.set(name,to);
    const span=motionMs()<=1||from===undefined||from===to?0:800;
    if(!span){node.textContent=dollars(to);return;}
    const started=performance.now();
    const step=now=>{
      const part=Math.min(1,(now-started)/span),eased=1-Math.pow(1-part,3);
      if(rolled.get(name)!==to)return;
      node.textContent=dollars(from+(to-from)*eased);
      if(part<1)requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
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
  const ROW_HEIGHT=ROW_PITCH,ROW_TOP=ROW_HEAD;
  /* Which way a panel's names read, from the approved board. Recipient types
     stay right-anchored against their bars; candidates and companies read
     left from one x, so a column of names is a column and not a ragged right
     edge. Top organizations is two-line (see TWO_LINE_PITCH). */
  const LEFT_LABELLED=['candidates','companies'];
  const TWO_LINE=['organizations'];
  // The chart is drawn at the panel's own pixel width, so its viewBox and its
  // layout width agree and nothing is scaled: a 720-wide drawing inside a
  // 540-wide bento tile renders 13px type at under 10px. A panel with no
  // width yet - hidden, or not laid out - falls back to 520 and is redrawn by
  // panelObserver as soon as it has one.
  const panelWidth=container=>Math.max(420,Math.min(920,Math.round(container.clientWidth||520)));
  function draw(name,rows,onClick,options) {
    const opts=options||{};
    const container=opts.container||get(name);
    const footNode=opts.foot===null?null:(opts.foot||document.getElementById('graph-foot-'+name));
    if(!rows.length){emptyPanel(name,opts.empty||'No nonzero amounts recorded for this selection.',container,footNode);return;}
    container.replaceChildren();
    const shown=rows.slice(0,opts.topN||topN(name)),total=opts.total===undefined?denominator(name):opts.total;
    const spark=opts.spark===undefined?name==='companies':opts.spark;
    const party=opts.party===undefined?name==='candidates':opts.party;
    const twoLine=opts.twoLine===undefined?TWO_LINE.includes(name):opts.twoLine;
    const leftRead=twoLine||(opts.leftRead===undefined?LEFT_LABELLED.includes(name):opts.leftRead);
    const heading=opts.title||titleFor[name],denom=opts.denom||denomLabel(name);
    const pitch=twoLine?TWO_LINE_PITCH:ROW_HEIGHT;
    const selected=opts.selected===undefined?(name==='organizations'?recipient:''):opts.selected;
    // The value column is as wide as the widest figure it has to hold, measured
    // at the size it is drawn at, rather than a fixed 96px guess.
    const valueWidth=shown.reduce((wide,row)=>Math.max(wide,MentatTheme.measureText(dollars(row.amount),LABEL_SIZE,MentatTheme.sans)),0);
    const box=layoutColumns(panelWidth(container),{party:party&&!twoLine,spark,valueWidth});
    const CHART_WIDTH=box.width,shareRight=box.shareRight,sparkX=box.sparkX,valueRight=box.valueRight;
    const LABEL_RIGHT=box.labelRight,BAR_LEFT=box.barLeft,barMax=box.barMax;
    const percentages=total>0&&shown.every(row=>row.amount>=0);
    const height=shown.length*pitch+ROW_TOP+(twoLine?18:10);
    const svg=svgNode('svg',{viewBox:`0 0 ${CHART_WIDTH} ${height}`,role:'img','aria-label':heading,class:'graph-bars'+(opts.animate?' graph-enter':'')});
    svg.append(svgNode('title',{},heading),svgNode('desc',{},`${get('scope').textContent}. ${shown.length} of ${rows.length} groups. Values in USD.`));
    const positive=Math.max(0,...shown.map(r=>r.amount)),negative=Math.min(0,...shown.map(r=>r.amount));
    const scale=barMax/(positive-negative||1),zero=BAR_LEFT-negative*scale;
    const colors=MentatTheme.palette;
    let covered=0;
    shown.forEach((row,i)=>{
      const top=ROW_TOP+i*pitch;
      // Two-line rows put the name on the first line and the bar, value and
      // share on the second; single-line rows share one baseline.
      const y=top,barBase=twoLine?top+TWO_LINE_NAME_DROP:top;
      const label=row.label+(row.party?` · ${row.party}`:'');
      const percent=percentages?100*row.amount/total:null;
      if(percent!==null)covered+=percent;
      const dot=party?partyClass(row.party):'';
      // Measured, not counted: the budget is the pixels the name is given -
      // the whole card on a two-line row - and the party rides in the suffix
      // so that it survives the cut instead of being the first thing lost.
      const parts=labelParts(row.label,party?row.party:'');
      const budget=twoLine?CHART_WIDTH-8:box.labelWidth;
      const text=MentatTheme.fitText(parts.text,budget,LABEL_SIZE,MentatTheme.sans,parts.suffix);
      // The accessible name is unchanged: name, colon, money. The share and the
      // per-cycle figures ride in <title>, which is the hover detail (item 12).
      // A drawer row is a reading, not a control: there is nothing behind it
      // to open, so it is not announced as a button and not in the tab order.
      const group=svgNode('g',opts.click===false
        ?{role:'listitem','aria-label':`${label}: ${dollars(row.amount)}`,class:'graph-bar-row'}
        :{role:'button',tabindex:0,'aria-label':`${label}: ${dollars(row.amount)}`,
          class:'graph-bar-button'+(selected&&row.id===selected?' is-selected':'')});
      group.append(svgNode('title',{},`${label} · ${dollars(row.amount)}`+(percent!==null?` · ${percent.toFixed(1)}% of ${denom}`:'')));
      group.append(svgNode('rect',{x:0,y:top-15,width:CHART_WIDTH,height:pitch-4,rx:4,class:'graph-row'}));
      if(selected&&row.id===selected)
        group.append(svgNode('rect',{x:0,y:top-15,width:3,height:pitch-4,class:'graph-row-rule'}));
      if(dot)group.append(svgNode('circle',{cx:box.dotCX,cy:y-4,r:4.5,class:'graph-party '+dot}));
      group.append(svgNode('text',{x:twoLine?0:(leftRead?box.labelLeft:LABEL_RIGHT),y,fill:MentatTheme.ink,'text-anchor':twoLine||leftRead?'start':'end','font-family':MentatTheme.sans,'font-size':LABEL_SIZE},text));
      const mark=svgNode('rect',{x:Math.min(zero,zero+row.amount*scale),y:barBase-11,width:Math.max(1,Math.abs(row.amount*scale)),height:14,rx:2,fill:row.amount<0?MentatTheme.negative:colors[Math.min(i,colors.length-1)],class:'graph-mark'});
      if(opts.animate)mark.style.setProperty('--i',String(Math.min(i,MOTION_STEPS)));
      group.append(mark);
      group.append(svgNode('text',{x:valueRight,y:barBase,fill:MentatTheme.ink,'text-anchor':'end','font-family':MentatTheme.sans,'font-size':LABEL_SIZE,class:'graph-value'},dollars(row.amount)));
      group.append(svgNode('text',{x:shareRight,y:barBase,fill:MentatTheme.muted,'text-anchor':'end','font-family':MentatTheme.sans,'font-size':SHARE_SIZE,class:'graph-share'},percent!==null?percent.toFixed(1)+'%':'—'));
      if(spark)group.append(svgNode('g',{class:'graph-spark','data-spark':row.id,transform:`translate(${sparkX},${barBase-11})`}));
      if(opts.click!==false){
        const select=()=>onClick(row.id);group.addEventListener('click',select);
        group.addEventListener('keydown',event=>{if(['Enter',' '].includes(event.key)){event.preventDefault();select();}});
      }
      svg.append(group);
    });
    if(opts.click===false)svg.setAttribute('role','list');
    container.append(svg);
    if(opts.animate)settle(svg);
    if(opts.values!==false)appendValues(container,name,rows,onClick);
    if(footNode)footNode.textContent=footText(name,shown.length,rows.length,percentages,covered);
    if(opts.values!==false)labelValues(name,shown.length,rows.length);
  }
  // Item 11: employee level is one stacked bar with a legend. Each segment is
  // still a .graph-bar-button carrying the same accessible name the bars use,
  // so the keyboard path, the export preview count and the click-through into
  // the level are all unchanged.
  function drawStack(name,rows,onClick,options) {
    const opts=options||{};
    if(!rows.length){emptyPanel(name,'No nonzero amounts recorded for this selection.');return;}
    const container=get(name);container.replaceChildren();
    const shown=rows.slice(0,topN(name)),total=denominator(name);
    const percentages=total>0&&shown.every(row=>row.amount>=0);
    const width=panelWidth(container),height=36;
    const svg=svgNode('svg',{viewBox:`0 0 ${width} ${height}`,role:'img','aria-label':titleFor[name],class:'graph-bars graph-stack'+(opts.animate?' graph-enter':'')});
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
      const mark=svgNode('rect',{x,y:6,width:wide,height:24,rx:2,fill,class:'graph-mark'});
      if(opts.animate)mark.style.setProperty('--i',String(Math.min(i,MOTION_STEPS)));
      group.append(mark);
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
    if(opts.animate)settle(svg);
    appendValues(container,name,rows,onClick);
    const foot=document.getElementById('graph-foot-'+name);
    if(foot)foot.textContent=footText(name,shown.length,rows.length,percentages,covered);
    labelValues(name,shown.length,rows.length);
  }
  function drawPanel(name,animate) {
    if(name==='drawer'){drawDrawerRows(animate);return;}
    if(!view)return;
    const panel=get(name);
    if(panel)drawnWidth.set(name,Math.round(panel.clientWidth));
    if(name==='candidates'&&!view.candidate_available){
      emptyPanel('candidates','This candidate view is unavailable for the selected scope.');return;
    }
    if(name==='levels')drawStack(name,view.levels||[],PANEL_CLICK.levels,{animate});
    else draw(name,view[name]||[],PANEL_CLICK[name],{animate});
    if(name==='companies')fillSparklines();
  }
  function paintAll(animate) { for(const name of PANELS)drawPanel(name,animate); drawDrawerRows(animate); }
  for(const name of PANELS) {
    const select=document.getElementById('graph-top-'+name);
    if(select)select.onchange=()=>{if(view)drawPanel(name,false);};
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
    // A resize is not a scope change, so nothing grows again: the bars are
    // relaid at the new width and left where they are.
    for(const name of names)drawPanel(name,false);
  }
  if(typeof ResizeObserver!=='undefined') {
    const panelObserver=new ResizeObserver(entries=>{
      for(const entry of entries) {
        const raw=entry.target.id.replace('graph-','');
        const name=raw==='drawer-rows'?'drawer':raw,width=Math.round(entry.target.clientWidth);
        if(width>0&&drawnWidth.get(name)!==width)resized.add(name);
      }
      if(!resized.size)return;
      clearTimeout(resizeTimer);resizeTimer=setTimeout(redrawResized,RESIZE_DEBOUNCE);
    });
    for(const name of [...PANELS,'drawer-rows']){const node=get(name);if(node)panelObserver.observe(node);}
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
      // The line is drawn inside its own group: the slot carries a transform
      // ATTRIBUTE for its position, and a CSS transform on the same element
      // would replace it rather than compose with it.
      const ink=svgNode('g',{class:'graph-spark-draw'});
      ink.append(svgNode('polyline',{fill:'none','stroke-width':1.5,class:'graph-spark-line',
        points:coords.map(([x,y])=>`${x.toFixed(1)},${y.toFixed(1)}`).join(' ')}));
      ink.append(svgNode('circle',{cx:coords[coords.length-1][0].toFixed(1),cy:coords[coords.length-1][1].toFixed(1),r:1.8,class:'graph-spark-dot'}));
      slot.append(ink);
      const title=slot.parentElement&&slot.parentElement.querySelector('title');
      if(title&&!title.textContent.includes(points[0][0]))
        title.textContent+=' · '+points.map(([cycle,value])=>`${cycle} ${dollars(value)}`).join(' · ');
    }
    const foot=document.getElementById('graph-foot-companies');
    if(foot&&!foot.textContent.includes('sparkline'))foot.textContent+=` · sparkline ${cycles.join(' · ')}`;
  }
  /* ------------------------------------------------ where the reader has been
     One in-memory stack of the scope each drill-down was made FROM. It is not a
     second store of navigational state: nothing reaches localStorage or
     sessionStorage, the URL stays the only persisted scope, and a new industry
     empties it because none of its entries could be restored into it. Paul's
     ruling C stands - replaceState, never pushState - so the browser's own Back
     leaves the console, and this is the only way back inside it. */
  let PAST=[];
  let pendingDrawer=null;
  function snapshot() {
    return {company:get('company').value,tier:get('tier').value,cycle:get('cycle').value,
      funding:get('funding').value,mode:get('mode').value,direction:get('direction').value,
      category,recipient,analysis,
      drawer:drawer?drawer.id:'',drawerDirection:drawer?drawer.direction:''};
  }
  function remember() { PAST=pushPast(PAST,snapshot()); }
  function back() {
    const past=PAST.pop();
    if(!past)return;
    for(const name of ['company','tier','cycle','funding','mode','direction'])
      if([...get(name).options].some(option=>option.value===past[name]))get(name).value=past[name];
    category=past.category;recipient=past.recipient;analysis=past.analysis||analysis;
    closeDrawer(false);
    pendingDrawer=past.drawer?{id:past.drawer,direction:past.drawerDirection}:null;
    syncControls();applyAnalysis();refresh();
  }
  // The parts of the trail, left to right. Pressing one clears it and everything
  // to its right; the industry cannot be cleared - a Graph with no industry has
  // nothing to show - so pressing it returns to the whole industry.
  function recipientLabel(id) {
    return (view&&view.options.recipients.find(r=>r.id===id)||{}).label||id;
  }
  function trailParts() {
    return trailModel({industry:get('industry').value,
      company:(view&&view.filters.company)||get('company').value,
      category:category,recipient:recipient?recipientLabel(recipient):''});
  }
  function clearFrom(index) {
    remember();
    for(const key of clearedBy(index)) {
      if(key==='company')get('company').value='';
      if(key==='category')category='';
      if(key==='recipient')recipient='';
    }
    closeDrawer(false);pendingDrawer=null;
    refresh();
  }
  function renderTrail() {
    const host=get('trail-parts'),row=get('trail');
    if(!host||!row)return;
    const parts=trailParts();
    host.replaceChildren();
    parts.forEach((part,at)=>{
      if(at){const mark=document.createElement('span');mark.className='graph-trail-mark';
        mark.setAttribute('aria-hidden','true');mark.textContent='\u203a';host.append(mark);}
      const button=document.createElement('button');
      button.type='button';button.className='graph-trail-part';
      button.textContent=part.label;
      button.title=at?`Back to ${parts[at-1].label}`:'Back to the whole industry';
      if(at===parts.length-1)button.setAttribute('aria-current','page');
      button.onclick=()=>clearFrom(part.index);
      host.append(button);
    });
    get('back').hidden=!drawer&&!PAST.length;
    get('back').textContent=drawer?'← Back to all recipients':'← Back';
    get('back').title=drawer?'Back to all recipients':'Back to the previous scope';
    row.hidden=parts.length<1||get('industry').closest('#view-graph').hidden;
  }

  /* ------------------------------------------------------- downstream drawer
     The second hop has always been on the server: /api/graph with mode=activity
     and a recipient answers the candidates that committee went on to fund. It
     was unreachable because a PAC click only narrowed the page, and the panel
     the answer lands in is never on screen at the same time as the panel the
     PAC was clicked in. So the drawer asks for itself, beside the panel that
     was clicked, and leaves the page's own Candidate view alone. */
  const DIRECTION_LABEL={'Contribution / Other':'Contributions / Other','Support':'Support',
    'Oppose':'Oppose','Unknown':'Unknown'};
  let drawer=null,drawerController=null;
  function writeDrawerScope() {
    globalThis.MentatScope?.write({drawer:drawer?drawer.id:'',
      drawerDirection:drawer&&drawer.direction?drawer.direction:''});
  }
  function closeDrawer(write) {
    drawerController?.abort();drawerController=null;
    if(!drawer)return;
    const panel=get('drawer-panel');
    drawer=null;
    // It leaves the way it came in. The card is kept for the length of the
    // slide and hidden after it, so the grid column does not collapse out
    // from under a card that is still on screen.
    if(panel&&!panel.hidden){
      panel.classList.add('is-closing');
      setTimeout(()=>{panel.classList.remove('is-closing');applyDrawer();},
        motionMs()<=1?0:420);
    } else applyDrawer();
    if(write!==false)writeDrawerScope();
  }
  function drawerCycle() {
    const value=(view&&view.filters.cycle)||'';
    return value?`${Number(value)-1}\u2013${value}`:'all saved cycles';
  }
  async function openDrawer(id,preferred) {
    drawerController?.abort();
    const mine=new AbortController();drawerController=mine;
    const label=recipientLabel(id);
    drawer={id,label,direction:preferred||'',totals:[],rows:[],note:'',loading:true,error:''};
    applyDrawer();
    // The drawer's own request. It never touches #graph-mode: the page stays on
    // the candidate view the reader chose, and this asks activity for itself.
    const ask=async direction=>{
      const query=filters();
      query.set('recipient',id);query.set('mode','activity');query.set('direction',direction);
      const response=await fetch('/api/graph?'+query,{signal:mine.signal});
      const body=await response.json();
      if(!response.ok)throw new Error(body.error||'Downstream activity is unavailable for this committee.');
      return body;
    };
    try {
      let direction=preferred||get('direction').value||'Support';
      let body=await ask(direction);
      const totals=Array.isArray(body.direction_totals)?body.direction_totals:[];
      // direction_totals is the same four numbers whichever side was asked for,
      // so opening on the largest side costs one extra request at most, and none
      // when the side asked for is already the largest.
      if(!preferred&&totals.length){
        const best=totals.slice().sort((a,b)=>Math.abs(b.amount)-Math.abs(a.amount))[0];
        if(best&&Math.abs(best.amount)>0&&best.direction!==direction){
          direction=best.direction;
          if(body.candidates_by_direction?.[direction]) body={...body,candidates:body.candidates_by_direction[direction]};
          else body=await ask(direction);
        }
      }
      if(drawerController!==mine)return;
      drawer={id,label,direction,totals,
        rows:body.candidate_available?(body.candidates||[]):[],
        relationships:body.pac_candidate_relationships||[],
        allDirections:body.candidates_by_direction||{},edges:body.downstream_edges||[],
        sources:body.downstream_sources||[],comparisons:body.measurement_comparisons||[],
        note:body.candidate_note||'',loading:false,
        error:body.candidate_available?'':(body.candidate_note||'This committee has no saved downstream activity.')};
      applyDrawer();writeDrawerScope();
    } catch(e) {
      if(e.name==='AbortError'||drawerController!==mine)return;
      drawer={id,label,direction:preferred||'',totals:[],rows:[],note:'',loading:false,error:e.message};
      applyDrawer();writeDrawerScope();
    }
  }
  function drawDirections() {
    const host=get('drawer-directions');
    if(!host)return;
    // Unknown is offered only when it holds something: three sides is the shape
    // the reader was shown, and a fourth empty cell is a question nobody asked.
    const sides=(drawer.totals||[]).filter(row=>row.direction!=='Unknown'||Number(row.candidates)>0||Number(row.unidentified_amount||0)!==0);
    host.replaceChildren(...sides.map(row=>{
      const button=document.createElement('button');
      button.type='button';button.className='graph-drawer-side';
      button.setAttribute('aria-pressed',String(row.direction===drawer.direction));
      const name=document.createElement('span');name.className='graph-drawer-side-name';
      name.textContent=DIRECTION_LABEL[row.direction]||row.direction;
      const count=document.createElement('strong');
      count.textContent=Number(row.candidates||0).toLocaleString()+(row.unidentified_amount?' + ?':'');
      button.append(name,count);
      button.title=`${dollars(row.amount)} across ${Number(row.candidates||0).toLocaleString()} identified candidates`+
        (row.unidentified_amount?`; ${dollars(row.unidentified_amount)} has no candidate identity`:'');
      button.onclick=()=>{
        if(row.direction===drawer.direction)return;
        if(drawer.allDirections?.[row.direction]) {
          drawer.direction=row.direction;drawer.rows=drawer.allDirections[row.direction];applyDrawer();writeDrawerScope();
        } else openDrawer(drawer.id,row.direction);
      };
      return button;
    }));
    host.hidden=!sides.length;
  }
  function drawDrawerRows(animate) {
    const host=get('drawer-rows'),panel=get('drawer-panel');
    if(!host||!panel||panel.hidden||!drawer)return;
    drawnWidth.set('drawer',Math.round(host.clientWidth));
    if(drawer.loading){host.replaceChildren();return;}
    const rows=drawer.rows||[];
    draw('drawer',rows,()=>{},{container:host,foot:null,values:false,click:false,
      total:rows.reduce((sum,row)=>sum+row.amount,0),party:true,spark:false,leftRead:true,
      twoLine:false,selected:'',animate:Boolean(animate),topN:10,
      title:'Candidates in saved PAC activity',denom:'this direction of saved network activity',
      empty:drawer.error||'No candidates are recorded on this side of this committee\u2019s activity.'});
    const ties=(drawer.relationships||[]).filter(row=>row.direction===drawer.direction);
    if(globalThis.MentatGraphExplorer) {
      globalThis.MentatGraphExplorer.mount(host,{root:drawer.id,rootLabel:drawer.label,direction:drawer.direction,
        rows:drawer.relationships||[],edges:drawer.edges||[],sources:drawer.sources||[],
        onEvidence:(id,cycle)=>{
          globalThis.MentatEvidence?.openCommittee?.(id,cycle);
          globalThis.MentatReturn?.arrive('graph','evidence');
          if(typeof showView==='function')showView('evidence');else location.hash='#evidence';
        }});
    }
    if(ties.length&&!globalThis.MentatGraphExplorer){
      const details=document.createElement('details');details.open=true;
      const summary=document.createElement('summary');summary.textContent=`PAC–candidate ties · all ${ties.length} relationships`;
      const scroll=document.createElement('div');scroll.className='table-scroll';
      const table=document.createElement('table');
      const head=table.createTHead().insertRow();
      ['Candidate','Net amount','Net share','Spending PAC / observed route','Cycle'].forEach(text=>{
        const th=document.createElement('th');th.textContent=text;head.append(th);
      });
      const body=table.createTBody();
      for(const tie of ties){
        const tr=body.insertRow();
        const values=[tie.candidate,dollars(tie.amount),
          tie.share_of_pac_direction==null?'Unavailable':`${(tie.share_of_pac_direction*100).toFixed(1)}%`,
          `${tie.committee_name} · ${tie.route.join(' → ')}`,tie.cycle];
        values.forEach(text=>{const td=tr.insertCell();td.textContent=text;});
      }
      const note=document.createElement('p');note.className='muted';
      note.textContent='Net share is of this PAC’s saved activity in the selected direction, not donor-attributed dollars or candidate control. Routes show committee connections, not a traced path for these dollars. Percentages are unavailable when net reversals make a share misleading.';
      scroll.append(table);details.append(summary,note,scroll);host.append(details);
    }
    if(drawer.note){
      const details=document.createElement('details');
      const summary=document.createElement('summary');summary.textContent='Measurement details';
      const note=document.createElement('p');note.textContent=drawer.note;
      details.append(summary,note);host.append(details);
    }
    if((drawer.comparisons||[]).length){
      const details=document.createElement('details');details.open=true;
      const summary=document.createElement('summary');summary.textContent='Different saved measurements · not reconciled';
      details.append(summary);
      for(const row of drawer.comparisons){
        const p=document.createElement('p');
        p.textContent=`${row.committee} · ${row.cycle} · ${row.schedule}: workbook ${row.workbook_amount == null ? 'not present in saved activity' : dollars(row.workbook_amount)}; selected snapshot ${dollars(row.snapshot_amount)}. ${row.basis}`;
        details.append(p);
      }
      host.append(details);
    }
    if((drawer.sources||[]).length){
      const details=document.createElement('details');
      const summary=document.createElement('summary');summary.textContent='Saved snapshot coverage';details.append(summary);
      for(const row of drawer.sources){
        const p=document.createElement('p');p.textContent=`${row.committee} · cycle ${row.cycle} · ${row.coverage_start||'unknown start'} to ${row.coverage_end||'unknown end'} · SHA-256 ${row.sha256||'unavailable'}`;details.append(p);
      }
      host.append(details);
    }
  }
  function applyDrawer() {
    const panel=get('drawer-panel');
    if(!panel)return;
    const open=Boolean(drawer)&&analysis==='recipients';
    panel.hidden=!open;
    const grid=document.querySelector('.graph-panels');
    if(grid)grid.dataset.drawer=open?'open':'';
    renderTrail();
    if(!open)return;
    get('drawer-title').textContent=`Saved downstream PAC activity \u00b7 ${drawerCycle()}`;
    get('drawer-committee').textContent=`${drawer.label} \u00b7 ${drawer.id}`;
    drawDirections();
    const status=get('drawer-status');
    status.textContent=drawer.loading?'Reading this committee\u2019s onward funding\u2026':'';
    status.hidden=!drawer.loading;
    const note=get('drawer-note');
    // The server's note is a disclosure, not an aside: it says in words that
    // these are the committee's own dollars, not the selected company's.
    note.textContent=drawer.loading?'':drawer.error||'Downstream backing assumes recorded PAC transfers. Each spending PAC is counted once per cycle.';
    note.hidden=Boolean(drawer.loading)||!drawer.note;
    drawDrawerRows(true);
  }
  // A permalink, or a Back, names a drawer before there is a view to open it
  // against. It is opened here, once the answer that knows the recipients is in.
  function restoreDrawer() {
    const wanted=pendingDrawer;pendingDrawer=null;
    if(!wanted||!wanted.id){if(drawer)closeDrawer(true);else writeDrawerScope();return;}
    if(analysis!=='recipients')selectAnalysis('recipients');
    openDrawer(wanted.id,wanted.direction||'');
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
  get('industry').onchange=()=>{PAST=[];closeDrawer(false);pendingDrawer=null;category='';recipient='';options(get('company'),[['','All companies']]);options(get('cycle'),[['','All cycles']]);refresh(true);};
  for(const name of ['company','tier','cycle','funding'])get(name).onchange=()=>{category='';recipient='';if(name==='tier'&&get('tier').value)get('funding').value='personal';syncControls();refresh();};
  for(const name of ['mode','direction'])get(name).onchange=()=>{syncControls();refresh();};
  get('reset').onclick=()=>{remember();closeDrawer(false);pendingDrawer=null;category='';recipient='';get('company').value='';get('tier').value='';get('cycle').value=view?.options.cycles.at(-1)||'';get('funding').value='all';get('mode').value='direct';get('direction').value='Support';selectAnalysis('overview');refresh();};
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
    applyDrawer();
    renderTrail();
  }
  function selectAnalysis(name,focus=false) {
    analysis=name;applyAnalysis();
    // A panel that was hidden when it was drawn had no width to draw at, so
    // the panels are redrawn as its tab opens. This costs no request: Top N is
    // a slice of the payload already in hand, and the sparkline cache is keyed
    // by request string.
    if(view)paintAll(false);
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
  /* The full table opens where the reader is standing. It used to switch the
     analysis sub-tab first, so pressing \u201cView all\u201d in the Overview moved the
     reader to another tab with no way back - the label promised a list and
     delivered a navigation. The one case left is a chart named from the view's
     own Export menu whose panel is not on screen: expanding a table nobody can
     see would be a dead control, so that, and only that, reveals its panel. */
  const VALUES_ANALYSIS={categories:'recipients',organizations:'recipients',
    candidates:'candidates',companies:'companies',levels:'companies'};
  function showValues(name) {
    const panel=get(name)?.closest('.graph-panel');
    if(panel&&panel.hidden)selectAnalysis(VALUES_ANALYSIS[name]);
    get('export-target').value=name;syncExport();
    const details=get(name).querySelector('details');
    if(!details){labelValues(name);return;}
    details.open=!details.open;
    if(details.open){details.scrollIntoView({block:'nearest'});details.querySelector('summary').focus();}
    labelValues(name);
  }
  // Keep the board's short action label; the accessible hint carries the count.
  function labelValues(name,shown,total) {
    const button=document.querySelector('#view-graph [data-values=\"'+name+'\"]');
    if(!button)return;
    const host=get(name),details=host?host.querySelector('details'):null;
    const open=Boolean(details&&details.open);
    const all=total===undefined?(view&&Array.isArray(view[name])?view[name].length:null):total;
    const top=shown===undefined?topN(name):shown;
    button.setAttribute('aria-expanded',String(open));
    button.textContent=open?`Show top ${top.toLocaleString()}`
      :'View all \u2192';
    button.title=open?`Show top ${top.toLocaleString()}`:all===null?'View all rows':`View all ${all.toLocaleString()} rows`;
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
  get('back').onclick=()=>{
    if(drawer){remember();recipient='';closeDrawer(true);pendingDrawer=null;refresh();}
    else back();
  };
  get('drawer-close').onclick=()=>closeDrawer(true);
  // Evidence resolves this committee against its saved sources and preserves
  // the requested cycle, including on the first visit to that tab.
  get('drawer-evidence').onclick=()=>{
    const api=globalThis.MentatEvidence;
    if(api&&typeof api.openCommittee==='function'&&drawer)
      api.openCommittee(drawer.id,(view&&view.filters.cycle)||'');
    globalThis.MentatReturn?.arrive('graph','evidence');
    if(typeof showView==='function')showView('evidence');else location.hash='#evidence';
  };
  let copyTimer=0;
  get('copy-link').onclick=async()=>{
    const api=globalThis.MentatScope,button=get('copy-link');
    if(!api)return;
    const url=new URL(api.href('graph',api.read()),location.href).href;
    const say=text=>{button.textContent=text;clearTimeout(copyTimer);
      copyTimer=setTimeout(()=>{button.textContent='Copy link';},2000);};
    try {
      if(!navigator.clipboard||typeof navigator.clipboard.writeText!=='function')
        throw new Error('This browser has no clipboard here.');
      await navigator.clipboard.writeText(url);
      get('copy-fallback').hidden=true;say('Copied');
    } catch(e) {
      // A plain http:// host is not a secure context and has no clipboard, and a
      // write can be refused. The link is put on screen rather than lost.
      const field=get('copy-url');
      field.value=url;get('copy-fallback').hidden=false;field.focus();field.select();
      say('Copy it from the field');
    }
  };
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
  function activate(){renderTrail();if((currentView==='graph'||(currentView==='evidence'&&splitView))&&!loaded){loaded=true;loadRuns();}}
  window.addEventListener('mentat:view',activate);
  document.querySelector('.workspace-tabs').addEventListener('click',activate);
  document.querySelector('.workspace-tabs').addEventListener('keydown',activate);
  window.addEventListener('hashchange',activate);activate();
})();
