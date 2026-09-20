/* Original Chart Studio workbench: verified contribution aggregates come from
   the local server; worksheet views retain their local chart-math path.
   Both sources share the original shelves, Marks, Show Me and SVG canvas. */
(() => {
  'use strict';
  const core = globalThis.MentatStudioCore;
  const math = globalThis.MentatCharts;
  const paint = globalThis.MentatChartRender;
  const contributions = globalThis.MentatStudioContributions;
  const contributionPlot = globalThis.MentatContributionPlot;
  const NS = 'http://www.w3.org/2000/svg';
  const el = id => document.getElementById('studio-' + id);
  const fmt = n => Number(n).toLocaleString('en-US', {maximumFractionDigits: 3});
  const compact = n => Math.abs(n) >= 1e5
    ? Number(n).toLocaleString('en-US', {notation: 'compact', maximumFractionDigits: 1})
    : Number(n).toLocaleString('en-US', {maximumFractionDigits: 2});
  const STORE = 'mentat-chart-studio-v1';
  const ZONES = [['columns', 'Columns'], ['rows', 'Rows'], ['color', 'Colour'], ['size', 'Size'],
    ['label', 'Label'], ['detail', 'Detail'], ['tooltip', 'Tooltip'], ['filters', 'Filters'], ['pages', 'Pages']];
  const AGG_LABEL = {sum: 'SUM', mean: 'AVG', count: 'COUNT', median: 'MEDIAN', min: 'MIN', max: 'MAX'};
  // Every gesture a Data-pane field answers to, in the order a reader meets
  // them. The pill says this before the click, so nobody has to discover it.
  const CLICK_HINT = 'Click to add \u00b7 drag to place \u00b7 Enter for actions';
  const ANALYTICS = [
    {id: 'annual', group: 'transform', label: 'Period totals', hint: 'Group dated rows into calendar years or election cycles'},
    {id: 'yoy', group: 'transform', label: 'Year-over-year %', hint: 'Percentage change from the previous calendar year'},
    {id: 'change', group: 'transform', label: 'Period change', hint: 'Difference from the preceding period'},
    {id: 'forecast', group: 'transform', label: 'Same-phase forecast', hint: 'Repeat the last completed value from the matching election phase'},
    {id: 'totals', group: 'flag', label: 'Totals', hint: 'Add a grand total of the plotted marks'},
    {id: 'average', group: 'flag', label: 'Average line', hint: 'Dashed reference line at the mean of the marks'},
    {id: 'median', group: 'flag', label: 'Median line', hint: 'Dashed reference line at the median of the marks'}
  ];

  let sheets = [core.createSheet('Sheet 1', 's1')];
  let active = 0;
  let data = null;
  let sourceKey = '';
  let history = [], future = [];
  let dragging = null, dropped = false;
  let selection = [];
  let dataSourceTab = false;
  let loadedSources = false, revision = 0;
  let pageTimer = 0;
  let hoverTile = '';
  let lastResult = null, lastConfig = null, lastTitle = '', lastScope = '';
  let contributionCatalog = null, contributionToken = '', contributionResult = null, contributionRequest = null;
  // The snapshot registry folded into GET /api/contributions/session as
  // industries[] (S4_DESIGN.md section 2). Left null on an older server that
  // does not send the field yet; nothing here has a reader for it beyond
  // parseSnapshotRegistry's own validation.
  let industries = null;
  let contributionOffset = 0, contributionRevision = 0;
  // One entry per question in flight: {key, promise, controller, waiters}. The
  // controller belongs to the request, not to the surface that started it, and
  // the request is only cancelled once the last surface waiting on it has moved
  // on - a tile that changes its question must not cancel the answer the tile
  // beside it is still waiting for.
  const contributionPending = new Map();
  // The single canvas needs a claim of its own, the way each tile has one.
  const mainFlight = {waiting: null};
  let contributionMap = null, contributionGeometry = null, geometryKey = '', geometryRevision = 0, geometryTimer = null;
  // The canvas the one map instance is drawn into. A surface only tears a map
  // down when it is the surface holding it: on a board the tiles draw together,
  // and a chart tile must not destroy the map beside it.
  let contributionMapHost = null;
  let recordOffset = 0, recordSelection = null, recordRevision = 0, exporting = false;
  let pageMembersKey = '';
  let pendingScope = null, appliedScope = null;
  // The saved-view id currently in the URL, and the flag that lets an open
  // install its own sheets without the edit-detector treating them as an edit.
  let openedSaved = '', holdingSavedId = false;
  let inspectorTab = 'marks', overviewMode = false, overviewRevision = 0, overviewCompany = '';
  let queryRequests = 0;
  // The Data source panel opens on arrival and folds itself away once, after
  // the first load that actually produced fields. sourceReady is what the
  // folded summary reports; it is cleared whenever a load starts again.
  let sourceReady = false;
  let progressStart = 0, progressTimer = 0, progressDepth = 0, progressOpened = false;
  // Canvas mode as a board of 1, 2 or 4 tiles (studio_api.json v2). null is one
  // tile, which is today's single canvas. What a sheet last drew is kept by its
  // own id, so a tile is never redrawn from another tile's answer.
  let board = null, boardSurfaces = [], boardNodes = [];
  const tileMemory = new Map();
  const contributionCache = new Map(), memberCache = new Map(), geometryCache = new Map(), geometryPending = new Map();
  let contributionCacheEpoch=0;
  const verified = () => el('source-mode').value === 'contributions';
  const basis = () => sheet().source.basis || 'receipt';
  // charts.js prints this as the canvas subtitle. A source object without it
  // puts the literal word "undefined" on the chart; 53efc2c4a named it on the
  // Company overview cards and this is the same name for the main canvas.
  const sheetName = () => (dataset() || {}).label || (dataset() || {}).id || '';
  const dataset = () => contributionCatalog?.datasets.find(d => d.id === el('dataset').value);

  const sheet = () => sheets[active];
  const columns = () => (data && data.columns) || [];

  /* ------------------------------------------------------------ storage */

  function readStore() {
    try { return JSON.parse(localStorage.getItem(STORE) || '{}') || {}; } catch { return {}; }
  }
  function persist() {
    if (!sourceKey) return;
    try {
      const store = readStore();
      // Entries written before the key named the worksheet are keyed by a bare
      // workbook digest and can never be matched again, so drop them rather
      // than let them use up the twelve-worksheet cap.
      for (const key of Object.keys(store)) if (!key.includes('|')) delete store[key];
      store[sourceKey] = {sheets, active, board};
      const keys = Object.keys(store);
      // Keep the file small: only the twelve most recent worksheets are kept.
      if (keys.length > 12) delete store[keys[0]];
      localStorage.setItem(STORE, JSON.stringify(store));
    } catch { /* private browsing or a full quota simply means no persistence */ }
  }
  function restore(key) {
    const saved = readStore()[key];
    if (saved && Array.isArray(saved.sheets) && saved.sheets.length) {
      sheets = saved.sheets.map(s => Object.assign(core.createSheet(s.name, s.id), s));
      active = Math.min(Math.max(0, saved.active | 0), sheets.length - 1);
      board = core.normalizeBoard({sheets: sheets, board: saved.board});
      settleBoard();
      return true;
    }
    sheets = [core.createSheet('Sheet 1', 's1')];
    active = 0;
    board = null;
    return false;
  }

  /* ---------------------------------------------------------------- focus */

  function focusMemory() {
    const node = document.activeElement;
    if (!node || node === document.body) return null;
    if (node.classList && node.classList.contains('studio-pill')) {
      return {zone: node.dataset.zone || '', column: node.dataset.column};
    }
    return node.id ? {id: node.id} : null;
  }
  function focusRestore(memory) {
    if (!memory) return;
    if (memory.id) {
      const node = document.getElementById(memory.id);
      if (node) node.focus();
      return;
    }
    const selector = '.studio-pill[data-column="' + memory.column + '"]';
    const scope = memory.zone ? el(memory.zone) : null;
    const node = (scope && scope.querySelector(selector)) ||
      document.getElementById('studio-pane-data').querySelector(selector) ||
      document.getElementById('studio-grid').querySelector(selector);
    if (node) node.focus();
  }

  /* -------------------------------------------------------------- history */

  function commit(change) {
    history.push(JSON.stringify({sheets, active, board}));
    if (history.length > 50) history.shift();
    future = [];
    const memory = focusMemory();
    change();
    viewEdited();
    persist();
    renderAll();
    focusRestore(memory);
  }
  function step(from, to) {
    if (!from.length) return;
    to.push(JSON.stringify({sheets, active, board}));
    const snapshot = JSON.parse(from.pop());
    const memory = focusMemory();
    sheets = snapshot.sheets;
    active = Math.min(snapshot.active, sheets.length - 1);
    board = snapshot.board || null;
    settleBoard();
    viewEdited();
    persist();
    renderAll();
    focusRestore(memory);
  }

  /* --------------------------------------------------------------- source */

  const fill = (node, items) => node.replaceChildren(...items.map(([value, label]) => new Option(label, value)));
  function sourceFields() {
    return {run: el('run').value, report: el('report').value, sheet: el('sheet').value, header: Number(el('header').value) || 0};
  }
  function status(message) { el('loading').textContent = message; renderSourceSummary(); }

  // The summary is the only part of the panel that survives being folded
  // away, so the state the panel would have shown is written there rather
  // than disappearing with it.
  function renderSourceSummary() {
    const details = el('source-details'), summary = el('source-summary');
    if (!details || !summary) return;
    // A chip line, open or folded: what this panel is pointed at, then whether
    // it is ready (UI clean-up item 16). It used to read "Data source" while
    // open and a sentence while folded, so the state disappeared with the fold.
    const chips = [];
    if (verified()) {
      const chosen = dataset();
      chips.push(chosen ? (chosen.label || chosen.id) : '', (contributions.BASIS[basis()] || [])[0] || '');
    } else if (data) {
      chips.push(sheet().source.reportName || '', data.sheet || '');
    }
    summary.replaceChildren();
    for (const text of chips.filter(Boolean)) {
      const chip = document.createElement('span');
      chip.textContent = text;
      summary.append(chip);
    }
    const mark = document.createElement('span');
    mark.className = sourceReady ? 'is-ready' : 'is-waiting';
    mark.textContent = sourceReady ? '✓ Ready' : (el('loading').textContent || 'Data source');
    summary.append(mark);
  }

  // The panel stays open (item 16). Its selects are the way into every report,
  // and folding them away after the first load was the console's doing, not the
  // reader's; the ready mark on the summary carries what the fold used to say.
  function settleSource() {
    sourceReady = true;
    renderSourceSummary();
  }

  // A report that cannot be read says why under the select, in the server's
  // own words, instead of only inside a thrown error nobody kept.
  function renderDatasetMessage() {
    const node = el('dataset-message');
    if (!node) return;
    const datasets = (contributionCatalog && contributionCatalog.datasets) || [];
    const chosen = datasets.find(d => d.id === el('dataset').value);
    const blocked = datasets.filter(d => !d.available && d.message);
    const text = chosen && chosen.message ? chosen.message
      : blocked.map(d => (d.label || d.id) + ': ' + d.message).join(' · ');
    node.textContent = text;
    node.hidden = !text;
    node.classList.toggle('is-warning', !!text);
  }

  /* Preparing the verified index can take minutes. The reader gets the
     server's own message, the time it has taken so far, and a way out that
     keeps the view they already had instead of an empty canvas. */
  function showProgress(message) {
    // A prepare nobody can see is a console that looks frozen, and the way
    // out of it is the Cancel button in this panel, so the panel opens for
    // the duration and returns to where it was afterwards.
    const details = el('source-details');
    if (details && !details.open) { progressOpened = true; details.open = true; renderSourceSummary(); }
    if (!progressStart) { progressStart = Date.now(); progressTimer = setInterval(tickProgress, 1000); }
    el('progress-message').textContent = message;
    el('progress').hidden = false;
    tickProgress();
  }
  function tickProgress() {
    if (!progressStart) return;
    const seconds = Math.max(0, Math.floor((Date.now() - progressStart) / 1000));
    el('progress-elapsed').textContent =
      Math.floor(seconds / 60) + ':' + String(seconds % 60).padStart(2, '0') + ' elapsed';
  }
  function clearProgress() {
    clearInterval(progressTimer);
    progressTimer = 0; progressStart = 0;
    el('progress').hidden = true;
    const details = el('source-details');
    if (progressOpened && details) { details.open = false; renderSourceSummary(); }
    progressOpened = false;
  }
  // Several verified calls can be waiting at once (a view, its member lists,
  // its records), so the row stays up until the last of them is done.
  function releaseProgress() {
    progressDepth = Math.max(0, progressDepth - 1);
    if (!progressDepth) clearProgress();
  }
  function failure(message) {
    el('error').textContent = message || '';
    el('error').hidden = !message;
  }

  async function loadRuns() {
    const ticket = ++revision;
    sourceReady = false;
    status('Choosing a report folder…');
    try {
      const body = await api('/api/report-sources');
      if (ticket !== revision) return;
      fill(el('run'), body.runs.map(r => [r.id, r.name]));
      await loadReports();
    } catch (e) { if (ticket === revision) { status('Report folders unavailable.'); failure(e.message); } }
  }
  async function loadReports() {
    const ticket = ++revision;
    status('Reading reports…');
    try {
      if (!el('run').value) { status('No report folder is available.'); return; }
      const body = await api('/api/reports?id=' + encodeURIComponent(el('run').value));
      if (ticket !== revision) return;
      fillReports(body.reports || []);
      if (!body.reports.length) { status('This folder has no completed reports.'); return; }
      await loadSheets();
    } catch (e) { if (ticket === revision) { status('Reports unavailable.'); failure(e.message); } }
  }
  // Both books of an industry arrive in one catalog. The tall companion is the
  // one a chart should be built from, so it is listed first and picked first;
  // the Overview keeps its own group because its sheets are a report layout,
  // not a table. `fill` cannot hold groups, so these options are built here.
  function worksheetHint() {
    let node = document.getElementById('studio-worksheet-hint');
    if (!node) {
      node = document.createElement('p');
      node.id = 'studio-worksheet-hint';
      node.className = 'studio-note';
      el('worksheet-source').append(node);
    }
    return node;
  }
  function fillReports(reports) {
    const groups = core.groupWorksheets(reports);
    el('report').replaceChildren(...['data', 'overview']
      .filter(kind => groups[kind].length)
      .map(kind => {
        const group = document.createElement('optgroup');
        group.label = core.WORKSHEET_GROUP_LABELS[kind];
        group.append(...groups[kind].map(r => new Option(r.name, r.index)));
        return group;
      }));
    if (groups.data.length) el('report').value = String(groups.data[0].index);
    const hint = worksheetHint();
    hint.textContent = groups.data.length ? '' : core.NO_DATA_WORKBOOK_HINT;
    hint.hidden = groups.data.length > 0;
  }
  async function loadSheets() {
    const ticket = ++revision;
    status('Reading worksheets…');
    try {
      const body = await api(requestPath());
      if (ticket !== revision) return;
      fill(el('sheet'), (body.sheets || []).map(s => [s, s]));
      const preferred = ['Candidate Funding', 'Funding Cohorts', 'Allocation Estimates', 'Beneficiary Summary']
        .find(s => (body.sheets || []).includes(s));
      if (preferred) el('sheet').value = preferred;
      await scan(false);
    } catch (e) { if (ticket === revision) { status('Worksheets unavailable.'); failure(e.message); } }
  }
  function requestPath(withSheet, header) {
    const params = new URLSearchParams({id: el('run').value, index: el('report').value});
    if (withSheet) params.set('sheet', el('sheet').value);
    if (header) params.set('header', header);
    return '/api/report-data?' + params;
  }
  async function scan(manual) {
    const ticket = ++revision;
    sourceReady = false;
    status('Scanning columns…');
    failure('');
    try {
      if (manual && !el('header').reportValidity()) throw new Error('Enter a header row from 1 to 100.');
      const body = await api(requestPath(true, manual ? Number(el('header').value) : 0));
      if (ticket !== revision) return;
      data = body;
      el('header').value = data.header_row;
      const fields = sourceFields();
      const key = core.sourceKey(fields, data);
      if (key !== sourceKey) {
        sourceKey = key;
        history = []; future = [];
        // A field picked in the previous worksheet still drives Show Me, so the
        // selection belongs to the source it was made in.
        selection = [];
        restore(key);
        applyDefaultGuards();
      }
      const record = {run: fields.run, runName: text(el('run')), report: fields.report, reportName: text(el('report')),
        sheet: data.sheet, header: data.header_row, sha256: data.sha256};
      for (const s of sheets) s.source = Object.assign({}, record);
      const subject = core.subjectField(core.classifyFields(data.columns).fields);
      if (subject) for (const s of sheets) defaultSubject(s, subject);
      status(fmt(data.row_count) + ' rows · ' + data.columns.length + ' columns scanned');
      persist();
      renderAll();
      settleSource();
    } catch (e) { if (ticket === revision) { status('Column scan unavailable.'); failure(e.message); } }
  }
  // A polymorphic Overview sheet opens with the partition the report itself
  // totals already selected, on every sheet of this workbook's state, so
  // nothing sums three stacked partitions before the reader has looked. The
  // guard is an ordinary filter pill, so removing it stands for as long as this
  // worksheet stays loaded and comes back the next time it is loaded.
  let guardsKey = '', guardsList = [];
  function worksheetGuards() {
    if (!data || verified()) return [];
    if (guardsKey !== sourceKey) { guardsKey = sourceKey; guardsList = core.defaultGuards(data.columns, members); }
    return guardsList;
  }
  function applyDefaultGuards() {
    const guards = worksheetGuards();
    if (!guards.length) return;
    for (const state of sheets) {
      const filters = Array.isArray(state.filters) ? state.filters : [];
      const added = guards.filter(guard => !filters.some(f => Number(f.column) === guard.column))
        .map(guard => ({column: guard.column, op: 'equals', value: guard.value, stage: 'row'}));
      if (added.length) state.filters = [...filters, ...added];
    }
  }
  // What a report worksheet says on its own account: the guard currently
  // holding one partition, and the sheets whose money is a recipient
  // committee's rather than the industry's.
  function worksheetNotes(state) {
    if (!data || verified()) return [];
    const committee = core.committeeActivitySheet(data.sheet);
    const filters = (state || sheet()).filters || [];
    const active = worksheetGuards()
      .filter(guard => filters.some(f => Number(f.column) === guard.column &&
        f.op === 'equals' && String(f.value) === guard.value))
      .map(guard => guard.note);
    return committee ? [committee, ...active] : active;
  }
  const text = select => select.selectedOptions[0] ? select.selectedOptions[0].textContent : '';

  /* Verified contributions use the original shelves and canvas. Query results
     are reused across display edits; underlying rows never enter browser sums. */
  async function contributionAPI(path, body, signal) {
    if(path==='query'&&body)queryRequests++;
    const response=await fetch('/api/contributions/'+path,body?{method:'POST',headers:{'Content-Type':'application/json','X-Mentat-Token':contributionToken},body:JSON.stringify(body),signal}:{signal});
    const result=await response.json();if(!response.ok||result.error)throw new Error(result.error||'Contribution data unavailable.');return result;
  }
  async function contributionReady(path, query, signal) {
    progressDepth++;
    try{
      for(;;){if(signal?.aborted)throw new DOMException('View changed','AbortError');const result=await contributionAPI(path,query,signal);if(result.status==='failed')throw new Error(result.message||'Source verification failed.');if(!['preparing','building','queued'].includes(result.status))return result;const waiting=result.message||'Verifying source records…';status(waiting);showProgress('Preparing verified data · '+waiting);await new Promise(resolve=>setTimeout(resolve,Math.min(4000,result.retry_after_ms||1000)));if(signal?.aborted)throw new DOMException('View changed','AbortError');}
    } finally { releaseProgress(); }
  }
  async function loadContributions(refresh=false) {
    const ticket=++revision;failure('');sourceReady=false;status('Reading verified contribution fields…');
    try {
      if(!contributionCatalog||refresh){const [session,catalog]=await Promise.all([contributionAPI('session'),contributionAPI('catalog')]);if(ticket!==revision||!verified())return;contributionToken=session.token;contributionCatalog=catalog;try{if(Array.isArray(session.industries))industries=core.parseSnapshotRegistry(session.industries);}catch(error){industries=null;}}
      // The permalink's industry, read through the one module that owns the URL
      // vocabulary (contracts/url_scope.json) instead of a second raw reader.
      const previous=el('dataset').value||globalThis.MentatScope?.read().industry||document.getElementById('graph-industry')?.value;
      fill(el('dataset'),contributionCatalog.datasets.map(d=>[d.id,d.label||d.id]));
      // An unavailable report carries the reason on its own option, so it is
      // readable before it is chosen and not only after a failure.
      for(const option of el('dataset').options){const d=contributionCatalog.datasets.find(d=>d.id===option.value);option.disabled=!d.available;option.title=d.message||'';if(!d.available)option.textContent+=' — unavailable';}
      el('dataset').value=contributionCatalog.datasets.some(d=>d.id===previous&&d.available)?previous:contributionCatalog.datasets.find(d=>d.available)?.id||'';
      renderDatasetMessage();
      if(!dataset())throw new Error(['No verified sources are available in the configured report folder.',
        ...contributionCatalog.datasets.filter(d=>d.message).map(d=>(d.label||d.id)+': '+d.message)].join(' '));
      selectContributionDataset();
      // A permalink arrives with no pendingScope, so the URL supplies one; a
      // click through from Graph already set it and is left alone.
      if(!pendingScope)pendingScope=urlGraphScope();
      applyGraphScope();
      settleSource();
      await openSavedFromUrl();
    }catch(error){if(ticket===revision){status('Verified data unavailable.');failure(error.message);renderDatasetMessage();}}
  }
  function selectContributionDataset() {
    ++revision;abortContributionRequests();tileMemory.clear();contributionOffset=0;contributionResult=null;contributionRequest=null;selection=[];history=[];future=[];
    const d=dataset(),key='contributions|'+d.id+'|'+d.provenance.workbook_sha256;sourceKey=key;const restored=restore(key);
    for(const state of sheets)state.source={...state.source,mode:'contributions',dataset:d.id,industry:d.industry,basis:state.source.basis||'receipt',reportName:d.provenance.workbook,sheet:'Verified source observations',runName:'Configured completed-report folder',sha256:d.provenance.workbook_sha256};
    data={columns:contributions.fields(d.fields||contributionCatalog.fields,basis()),rows:[],row_count:0,header_row:0,sha256:d.provenance.workbook_sha256,sheet:'Verified source observations',note:d.provenance.scope};
    if(!restored){sheet().columns=[{column:data.columns.findIndex(f=>f.id==='company'),aggregation:'sum'}];sheet().rows=[{column:data.columns.findIndex(f=>f.id==='amount'),aggregation:'sum'}];sheet().marks.type='bar';}
    persist();renderAll();
    // Four call sites reach this function - the Data panel picker, the shelf
    // source buttons, openView() and the permalink path - and every one of them
    // is a producer of the URL's `industry`, so the write lives here rather than
    // at four places that could drift apart (DE-021).
    globalThis.MentatScope?.write({industry:d.industry||d.id||''});
  }
  function syncContributionControls() {
    const on=verified();el('contribution-source').hidden=!on;el('worksheet-source').hidden=on;el('verified-summary').hidden=!on;el('result-controls').hidden=!on;
    el('marks-note').textContent=on?'Colour separates series. Detail, Label and Tooltip dimensions define each mark’s grouping. Select a mark to inspect its source records.':'Colour separates series. Label shows the plotted value. Unsupported encodings produce an explanation.';
    for(const id of ['param-start','param-end','param-limit','param-horizon','param-split'])el(id).closest('label').hidden=on&&id!=='param-horizon';
    if(!on){el('map-settings').hidden=true;return;}
    fill(el('mark'),[...core.MARK_TYPES,['map','Map'],...contributions.EXTRA_MARKS]);el('mark').value=sheet().marks.type;
    const d=dataset();if(!d)return;
    fill(el('basis'),d.bases.map(b=>[b.id,contributions.BASIS[b.id]?.[0]||b.label]));el('basis').value=basis();el('basis-note').textContent=contributions.BASIS[basis()]?.[1]||'';
    if(data)data.columns=contributions.fields(d.fields||contributionCatalog.fields,basis());
    if(el('destination'))el('destination').value=core.shelf(sheet().columns).map(p=>columns()[p.column]?.id).find(id=>['recipient_state','represented_state','state'].includes(id))||'';
    el('param-groups').title='Groups shown per page. Totals and CSV exports include every group.';
    const mapWasHidden=el('map-settings').hidden;
    el('map-settings').hidden=!['map','filled-map'].includes(sheet().marks.type);
    if(mapWasHidden&&!el('map-settings').hidden)el('map-settings').open=true;
    const binWasHidden=el('bin-width-label').hidden;
    el('bin-width-label').hidden=sheet().marks.type!=='histogram';el('bin-width').value=sheet().params.binWidth||100;
    if(binWasHidden&&!el('bin-width-label').hidden&&el('params-details'))el('params-details').open=true;
    const map=sheet().map||{layers:['states','districts'],congress:'119'};
    el('congress').value=map.congress;for(const [id,layer]of [['states','states'],['districts','districts'],['zips','zip_areas']])el('layer-'+id).checked=map.layers.includes(layer);
  }
  // A permalink's company and cycle become the same carried pills the Graph
  // handoff produces, so applyGraphScope() below stays the only consumer and
  // one code path renders both. Graph spells a cycle by its end year and the
  // verified index by the pair it covers, so the same translation the handoff
  // uses is applied here (chart-studio-core.js carriedFilterValue).
  function urlGraphScope() {
    const url=globalThis.MentatScope?.read();
    if(!url||(!url.company&&!url.cycle))return null;
    const filters=[];
    if(url.company)filters.push({field:'company',value:url.company});
    if(url.cycle)filters.push({field:'cycle',value:core.carriedFilterValue('cycle',url.cycle)});
    return {industry:url.industry||'',filters,notCarried:[]};
  }
  // The saved-view id in the URL. A view that lives only in this tab
  // (viewsMemory, id "memory-...") is not addressable, so it is never written:
  // writing it would silently remove a real id that was already there.
  function rememberSavedView(id) {
    const value=String(id||'');
    if(!/^[a-f0-9]{32}$/.test(value))return;
    openedSaved=value;
    globalThis.MentatScope?.write({saved:value});
  }
  // The first change to the working sheets after an open or a save. From here
  // the id in the URL no longer describes what is on screen, and leaving it
  // there would let the next reload re-open the saved view over the edit.
  function viewEdited() {
    if (holdingSavedId || !openedSaved) return;
    openedSaved = '';
    globalThis.MentatScope?.write({saved: ''});
  }
  // A saved-view permalink. The list is the cheapest way to get the view's
  // sourceKey, which openability() needs before openView() will touch it;
  // openView() fetches the sheets itself. A link to a view this console does
  // not have says so rather than opening the wrong thing.
  async function openSavedFromUrl() {
    const id=globalThis.MentatScope?.read().saved;
    if(!id||id===openedSaved)return;
    openedSaved=id;
    let views=[];
    try { views=(await getJSON('/api/studio/views')).views||[]; }
    catch (error) { failure(viewMessage(error)+' The saved view in this link could not be listed.'); return; }
    const view=views.find(item=>item.id===id);
    if(!view){failure('This console has no saved view '+id+'.');return;}
    await openView(view);
  }
  // Carried Graph scope becomes ordinary filter pills, so the reader can see
  // and remove every one of them. A field this dataset does not have is
  // reported, never silently dropped.
  function applyGraphScope() {
    const scope = pendingScope;
    if (!scope) return;
    // The carried scope is only consumed once it can actually be applied.
    // "Open in Chart Studio" calls this eagerly, and loadContributions()
    // calls it again when the verified data lands; on a page where Chart
    // Studio has not loaded yet the eager call arrives first, and clearing
    // pendingScope there threw the reader's company and cycle away before
    // the second call could use them.
    if (verified() && !data) return;
    pendingScope = null;
    if (!verified()) return;
    const missing = [];
    const pills = [];
    for (const {field, value} of scope.filters) {
      const column = columns().find(f => f.id === field);
      if (!column) { missing.push(field); continue; }
      pills.push({column: column.index, op: 'equals', value: String(value), stage: 'row'});
    }
    appliedScope = {carried: true, industry: scope.industry,
      company: (scope.filters.find(f => f.field === 'company') || {}).value || '',
      cycle: (scope.filters.find(f => f.field === 'cycle') || {}).value || '',
      notCarried: [...(scope.notCarried || []),
        ...missing.map(field => field + ': not carried (not in this data)')]};
    if (!pills.length && !missing.length) return;
    commit(() => {
      const kept = (sheet().filters || []).filter(f => !pills.some(p => p.column === Number(f.column)));
      sheet().filters = [...kept, ...pills];
    });
    failure(missing.length ? 'This source has no ' + missing.join(' or ') + ' field, so that part of the Graph scope was not carried.' : '');
  }

  // A surface lets go of the answer it was waiting for. The request itself is
  // only cancelled when nobody is left waiting on it.
  function releaseFlight(claim) {
    const flight = claim && claim.waiting;
    if (!flight) return;
    claim.waiting = null;
    flight.waiters -= 1;
    if (flight.waiters > 0) return;
    if (contributionPending.get(flight.key) === flight) contributionPending.delete(flight.key);
    flight.controller.abort();
  }
  const everyClaim = () => [mainFlight, ...tileMemory.values()];
  // Cancel, Refresh and a change of source stop every surface, not just the one
  // the module happened to remember.
  function abortContributionRequests() {
    for (const claim of everyClaim()) releaseFlight(claim);
    for (const flight of [...contributionPending.values()]) flight.controller.abort();
    contributionPending.clear();
  }
  function queryCached(query,view) {
    const key=JSON.stringify(query),cached=contributionCache.get(key),epoch=contributionCacheEpoch;
    const claim=(view&&view.flight)||mainFlight;
    if(contributionResult&&contributionRequest&&JSON.stringify(contributionRequest)===key)return Promise.resolve(contributionResult);
    if(cached&&Date.now()-cached.at<30000)return Promise.resolve(cached.result);
    releaseFlight(claim);
    const flying=contributionPending.get(key);
    if(flying){flying.waiters+=1;claim.waiting=flying;return flying.promise;}
    const flight={key,controller:new AbortController(),waiters:1,promise:null};
    flight.promise=contributionReady('query',query,flight.controller.signal).then(result=>{if(epoch===contributionCacheEpoch){contributionCache.set(key,{result,at:Date.now()});if(contributionCache.size>12)contributionCache.delete(contributionCache.keys().next().value);}return result;}).finally(()=>{if(contributionPending.get(key)===flight&&epoch===contributionCacheEpoch)contributionPending.delete(key);});
    contributionPending.set(key,flight);claim.waiting=flight;return flight.promise;
  }
  // The scope under the chart title: the parts the header chips carry, plus the
  // basis, so the chart and the chrome cannot disagree about what is on screen.
  function scopeSubtitle(state) {
    if(!data)return '';
    const parts=scopeText().split(' · ').filter(Boolean);
    if(verified()){const label=contributions.BASIS[basisOf(state)];if(label&&label[0])parts.push(label[0].toLowerCase());}
    return parts.join(' · ');
  }
  // What one chart draws into, and whose staleness ticket it carries. The single
  // canvas is the main surface, and its storage IS the module state the Inspector,
  // the exports, the print sheet and the briefing already read, so one code path
  // writes both. A board tile passes its own nodes and its own ticket; the
  // selected tile is primary and writes the module state too, which is what
  // "Export acts on the selected tile" means.
  function mainSurface() {
    return {state: sheet(), index: active, el: el, primary: true, flight: mainFlight, canvasClass: '',
      bump: () => ++contributionRevision, stale: ticket => ticket !== contributionRevision,
      ticket: () => contributionRevision,
      get offset() { return contributionOffset; }, set offset(value) { contributionOffset = value; },
      get request() { return contributionRequest; }, set request(value) { contributionRequest = value; },
      get result() { return contributionResult; }, set result(value) { contributionResult = value; },
      get title() { return lastTitle; }, set title(value) { lastTitle = value; },
      get scope() { return lastScope; }, set scope(value) { lastScope = value; }};
  }
  const basisOf = state => (state || sheet()).source.basis || 'receipt';
  function sourceScope(result,request) {
    const p=result.provenance;
    return [request.dataset,contributions.BASIS[request.basis]?.[0],p.workbook,'Workbook SHA256 '+p.workbook_sha256,'Analytical index '+p.index_token,'Query engine SHA256 '+p.query_engine_sha256,'Field semantics SHA256 '+p.field_semantics_sha256,'Groups '+(result.offset+1)+'–'+(result.offset+result.rows.length)+' of '+result.group_count,JSON.stringify({filters:request.filters,aggregate_filters:request.aggregate_filters,bin_width_cents:request.bin_width_cents}),p.scope].join(' · ');
  }
  async function renderContributionView(view) {
    view=view||mainSurface();const node=view.el,state=view.state;
    if(!data||!dataset()){node('reconcile').hidden=true;node('canvas').replaceChildren();node('table').replaceChildren();node('verified-summary').textContent='Reading verified source fields…';node('result-controls').hidden=true;node('title').textContent='';node('subtitle').textContent='';node('note').textContent='Choose a verified report in the Data panel to begin.';if(view.primary)lastResult=null;return;}
    const ticket=view.bump(),sheetBasis=basisOf(state);
    try {
      const compiled=contributions.compile(state,columns(),{dataset:dataset().id,industry:dataset().industry,basis:sheetBasis,offset:view.offset});
      const query=compiled.query,key=JSON.stringify(query),previous=view.request;
      if(previous&&JSON.stringify({...previous,offset:0})!==JSON.stringify({...query,offset:0})&&view.offset){view.offset=0;query.offset=0;}
      if(!previous||JSON.stringify(previous)!==key){node('canvas').setAttribute('aria-busy','true');node('verified-summary').textContent='Reading verified totals…';if(view.primary){status('Reading verified source observations…');el('inspection').hidden=true;++recordRevision;lastResult=null;}}
      const result=await queryCached(query,view);if(view.stale(ticket)||!verified())return;
      view.result=result;view.request=query;
      if(view.primary){failure('');lastResult=result;lastConfig=compiled;data.row_count=result.totals.records;data.rows=result.rows.map(row=>data.columns.map(f=>row[f.id]??''));}
      let title=contributions.BASIS[sheetBasis][0]+(query.dimensions.length?' by '+query.dimensions.map(id=>data.columns.find(f=>f.id===id)?.name||id).join(' / '):'');if(compiled.spec.measures.length!==1||compiled.spec.measures[0]!=='amount')title=compiled.spec.measures.map(id=>result.columns.find(c=>c.id===id)?.name||id).join(' / ')+' · '+title;view.title=title;view.scope=sourceScope(result,query);node('title').textContent=title;node('subtitle').textContent=scopeSubtitle(state);
      const money=value=>contributionPlot.format(value,'amount');
      node('verified-summary').replaceChildren();
      for(const [label,value]of [[sheetBasis==='original_supported'?'Selected gross amount':'Selected net amount',money(result.totals.amount)],['Source observations',fmt(result.totals.records)],['Reported donor identities',fmt(result.totals.contributors)]]){const item=document.createElement('span'),strong=document.createElement('strong');strong.textContent=value;item.append(strong,document.createTextNode(label));node('verified-summary').append(item);}
      node('verified-summary').title='Totals cover all matching source records before grouped filters. Group distinct identity counts are not added together.';
      node('group-count').textContent=result.group_count?`${fmt(result.offset+1)}–${fmt(result.offset+result.rows.length)} of ${fmt(result.group_count)} groups · totals cover all ${fmt(result.group_count)}`:'No matching observations';
      node('groups-prev').disabled=!query.offset;node('groups-next').disabled=!result.has_more;node('result-controls').hidden=false;
      node('groups-prev').hidden=node('groups-next').hidden=compiled.spec.type==='map'||compiled.transform!=='none';
      let rows=result.rows,spec={...compiled.spec,columns:result.columns,title:title},temporalModel=null,drewReferences=false;const notes=[...compiled.notes,...(result.notices||[])];
      if(spec.type==='histogram'&&result.has_more)throw new Error('This histogram has more than 10,000 occupied bins. Increase the bin width or narrow the filters to display the complete distribution.');
      if(compiled.transform!=='none'&&compiled.transform!=='annual'){
        if(result.has_more)throw new Error('Period analysis requires every selected period. Narrow the filters.');
        const time=query.dimensions[0],modelData={columns:[{index:0,name:time==='cycle'?'Election cycle':'Year',type:'category'},{index:1,name:'Amount',type:'number'}],rows:rows.map(r=>[r[time],r.amount]),row_numbers:rows.map((_,i)=>i+1),row_count:rows.length,header_row:0};
        const model=math.build(modelData,{type:'line',x:0,y:1,series:-1,aggregation:'sum',filters:[],transform:compiled.transform,period:time==='cycle'?'cycle':'year',horizon:state.analytics.horizon||2,start:0,end:0,limit:0});
        const id=compiled.transform==='yoy'?'percent_change':'amount';rows=model.groups.map(g=>({[time]:time==='cycle'?`${g.year-1}-${g.year}`:String(g.year),[id]:g.value}));spec.measures=[id];spec.columns=[{id,name:compiled.transform==='forecast'?'Observed amount and same-phase baseline':id==='amount'?'Period change':'Year-over-year change (%)',unit:id==='amount'?'cents':'percent'}];notes.push(model.note);
        temporalModel={...model,type:spec.type,groups:model.groups.map(g=>({...g,value:g.value/(id==='amount'?100:1)}))};
      }
      // One map at a time: it owns the geometry cache and the Census request, so
      // it is drawn for the tile the reader selected. An unselected map tile names
      // the gesture that brings it back rather than drawing nothing.
      if(spec.type==='map'){
        if(!view.primary){node('canvas').replaceChildren();node('table').hidden=true;node('status').textContent='';node('note').textContent='This sheet draws a map. Select this tile to see it.';return;}
        await renderContributionMap(ticket,compiled,null,view);return;
      }
      if(contributionMapHost===node('canvas')){clearTimeout(geometryTimer);contributionMap?.destroy?.();contributionMap=null;contributionMapHost=null;++geometryRevision;}
      node('canvas').hidden=false;node('table').hidden=true;node('canvas').className=view.canvasClass+'studio-canvas fit-'+state.fit;
      if(temporalModel){
        const measure=spec.columns[0].name+(spec.columns[0].unit==='cents'?' (USD)':'');
        const drawn=paint.chartSVG(temporalModel,measure,{type:spec.type,aggregation:'sum',x:0,y:1},{sheet:sheetName(),columns:[{name:'Period'},{name:measure}]},view.title,view.scope);node('canvas').replaceChildren(drawn.svg);
      }else if(['pie','doughnut','waterfall','pareto','radar'].includes(spec.type)){
        if(spec.measures.length!==1)throw new Error('This mark type uses one measure.');
        const id=spec.measures[0],currency=contributions.MONEY.has(id),groups=rows.map(row=>({label:contributionPlot.label(row,spec.dimensions),value:row[id]/(currency?100:1),n:1}));
        const drawn=paint.chartSVG({type:spec.type,groups,selected:result.totals.records,excluded:0},(result.columns.find(c=>c.id===id)?.name||id)+(currency?' (USD)':''),{type:spec.type,aggregation:'sum',x:0,y:1},{sheet:sheetName(),columns:[{name:'Group'},{name:id}]},view.title,view.scope);node('canvas').replaceChildren(drawn.svg);
      }else if(MentatContributionCharts.TYPES.includes(spec.type))MentatContributionCharts.render(node('canvas'),rows,spec,row=>{if(view.primary)inspectContributions(row);});
      else {contributionPlot.render(node('canvas'),rows,spec,row=>{if(view.primary)inspectContributions(row);});drewReferences=spec.type!=='scatter';}
      if(state.analytics.totals)notes.push('Selected source total: '+money(result.totals.amount)+'. This total excludes projections and covers every matching group before grouped filters.');
      // Say plainly when a requested reference line was not drawn, instead
      // of describing one the reader cannot see.
      if(state.analytics.average||state.analytics.median)notes.push(
        drewReferences?'Reference lines mark the mean and median of the shown marks; source-level averages and medians are available as measures.'
        :'Reference lines are not drawn on this mark type. Choose a bar, line, area or circle mark to see the mean and median of the shown marks.');
      node('note').textContent=[contributions.BASIS[sheetBasis][1],query.aggregate_filters.length?'Grouped filters apply after aggregation.':result.has_more?'Additional groups are on later pages; source totals cover all pages.':'All selected groups shown.',...notes].join(' ');
      node('status').textContent=fmt(result.totals.records)+' source observations · '+fmt(result.group_count)+' groups · '+(result.reconciliation?.receipt_matches_workbook===true?'Included receipts reconcile to the workbook.':'Verified source records.')+(view.primary?' · '+fmt(queryRequests)+' verified queries this session':'');
      if(view.primary)status('Verified contribution fields · '+data.columns.length+' fields');
      if(view.primary)renderPager();
      renderReconcile(result,view,ticket).catch(()=>{node('reconcile').hidden=true;});
    }catch(error){if(!view.stale(ticket)&&error.name!=='AbortError'){node('reconcile').hidden=true;node('canvas').replaceChildren();node('note').textContent=error.message;if(view.primary){failure(error.message);lastResult=null;}}}
    finally{if(!view.stale(ticket))node('canvas').setAttribute('aria-busy','false');}
  }
  async function renderContributionMap(ticket,compiled,bbox=null,view=null) {
    view=view||mainSurface();const node=view.el;
    const current=++geometryRevision,result=view.result,map=view.state.map||{layers:['states','districts'],congress:'119'},zips=MentatContributionMap.eligibleZips(result.rows).sort(),key=JSON.stringify({zips,congress:map.congress,bbox});
    if(result.has_more)throw new Error('Narrow the map filters so every geographical group can be included.');
    const saved=contributionMap?.getView();status('Loading Census boundaries…');
    const cached=geometryCache.get(key),pendingKey=key+'|'+[...map.layers].sort().join(',');let geometry=cached&&map.layers.every(layer=>cached.layers?.[layer])?cached:null;if(!geometry){if(!geometryPending.has(pendingKey))geometryPending.set(pendingKey,contributionAPI('geography',{zips,layers:map.layers,congress:map.congress,...(bbox?{bbox}:{})}).finally(()=>geometryPending.delete(pendingKey)));geometry=await geometryPending.get(pendingKey);geometryCache.set(key,geometry);}
    if(view.stale(ticket)||current!==geometryRevision||!verified())return;
    geometryCache.set(key,geometry);if(geometryCache.size>8)geometryCache.delete(geometryCache.keys().next().value);contributionGeometry=geometry;geometryKey=key;contributionMap?.destroy?.();contributionMapHost=node('canvas');node('canvas').hidden=false;node('table').hidden=true;
    contributionMap=MentatContributionMap.render(node('canvas'),{groups:result.rows.map(r=>({...r,amount_cents:r.amount})),geometry,layers:map.layers,filled:compiled.spec.filled,title:view.title,valueLabel:basisOf(view.state)==='original_supported'?'Selected gross amount':'Selected net amount',showLayerControls:false,onSelect:row=>inspectContributions(contributions.mapSelection(row)),onViewport:event=>{if(!map.layers.includes('zip_areas'))return;clearTimeout(geometryTimer);geometryTimer=setTimeout(()=>renderContributionMap(view.ticket(),compiled,event.bbox,view).catch(e=>failure(e.message)),450);}});
    if(saved)contributionMap.setView(saved);
    view.scope+=' · Congress '+map.congress+'; '+map.layers.join(', ')+'; overlays do not allocate money. Mapped '+contributionPlot.format(contributionMap.data.mapped_cents,'amount')+'; unmapped '+contributionPlot.format(contributionMap.data.unmapped_cents,'amount')+' · '+(geometry.sources||[]).map(s=>(s.vintage||s.label||s.url)+' SHA256 '+s.sha256).join(' · ');
    node('note').textContent=[contributions.BASIS[basisOf(view.state)][1],'ZIP marks combine eligible ZIP/state groups; grouped filters apply before this combination. Unmapped money remains in the selected total.',...(contributionMap.data.coverage_notes||[]),...(geometry.warnings||[])].join(' ');
    node('status').textContent=fmt(result.group_count)+' geographic groups · '+fmt(contributionMap.data.marks.length)+' mapped marks · boundaries do not change money';status('Verified ZIP/state records and Census boundaries');
  }
  async function inspectContributions(row=null,offset=0) {
    if(!contributionResult)return;recordSelection=row;recordOffset=offset;const ticket=++recordRevision,sourceRevision=contributionRevision;el('inspection').hidden=false;el('record-count').textContent='Reading source records…';el('records').replaceChildren();
    try{const query={...contributionRequest,filters:contributions.markFilters(contributionRequest,row),aggregate_filters:[],limit:100,offset};const result=await contributionReady('records',query);if(ticket!==recordRevision||sourceRevision!==contributionRevision)return;if(!['workbook_sha256','database_sha256','index_token'].every(key=>result.provenance?.[key]===contributionResult.provenance?.[key]))throw new Error('Source changed before record inspection. Refresh the verified data.');
      const columns=[['date','Date'],['contributor','Contributor'],['company','Company'],['recipient','Recipient'],['amount_cents','Selected amount'],['raw_cents','Raw observation'],['zip5','ZIP'],['state','State'],['decision_status','Accounting status'],['receipt_role','Receipt role'],['reasons','Reasons'],['source_id','Source ID'],['source_url','FEC filing']];for(const id of query.dimensions||[])if(!columns.some(c=>c[0]===id))columns.push([id,data.columns.find(c=>c.id===id)?.name||id]);const table=document.createElement('table'),head=document.createElement('tr'),body=document.createElement('tbody');for(const[,name]of columns){const th=document.createElement('th');th.textContent=name;head.append(th);}const thead=document.createElement('thead');thead.append(head);table.append(thead,body);
      for(const record of result.rows){const tr=document.createElement('tr');for(const[id]of columns){const td=document.createElement('td'),value=record[id];td.textContent=id.endsWith('_cents')?contributionPlot.format(value,'amount'):Array.isArray(value)?value.join('; '):value??'';if(id==='source_url'&&/^https:\/\/(?:[^/]+\.)?fec\.gov\//.test(value||'')){const a=document.createElement('a');a.href=value;a.target='_blank';a.rel='noopener noreferrer';a.textContent='Open filing';td.replaceChildren(a);}tr.append(td);}body.append(tr);}el('records').append(table);el('record-count').textContent=`${result.total_records?offset+1:0}–${offset+result.rows.length} of ${fmt(result.total_records)} source observations`;el('record-prev').disabled=!offset;el('record-next').disabled=!result.has_more;
    }catch(error){if(ticket===recordRevision)el('record-count').textContent=error.message;}
  }
  async function downloadContributions(format) {
    const view=activeSurface();if(!view.result||!lastResult||exporting)return;const result=view.result,query=structuredClone(view.request),ticket=view.ticket();
    try{if(format==='csv'){exporting=true;status('Preparing complete grouped CSV…');let rows=[],offset=0;for(;;){const page=await contributionReady('query',{...query,offset,limit:100000});if(view.stale(ticket))throw new Error('View changed during export. Start the download again.');if(!contributions.sameSource(page.provenance,result.provenance))throw new Error('Source changed during export. Refresh the verified data.');rows.push(...page.rows);if(!page.has_more)break;if(!page.rows.length)throw new Error('The next export page is empty.');offset+=page.rows.length;}MentatExport.download(contributions.csv({...result,rows},query),'text/csv;charset=utf-8','mentat-chart-studio.csv');status('Exported '+fmt(rows.length)+' groups with source and accounting provenance.');}
      else{const svg=view.el('canvas').querySelector('svg');if(!svg)throw new Error('This view has no image. Download its data CSV.');await MentatExport.image(svg,format,view.title,view.scope,'mentat-chart-studio');}
    }catch(error){failure(error.message);}finally{exporting=false;}
  }

  /* ---------------------------------------------------------------- pills */

  function fieldLabel(field, aggregation) {
    if(verified()&&field.role==='measure'&&field.id!=='amount')return field.name;
    if (field.role !== 'measure' || !aggregation) return field.name;
    return (AGG_LABEL[aggregation] || 'SUM') + '(' + field.name + ')';
  }
  function fieldTooltip(field) {
    if(verified())return [field.name,'Data type: '+(field.data_type||field.type),'Role: '+field.role,field.discrete?'Discrete grouping':'Continuous aggregate',field.table,field.geographic_role?'Geography: '+field.geographic_role:'',field.description].filter(Boolean).join(' · ');
    const kind = field.role === 'measure' ? 'measure' : field.isTime ? 'date dimension' : 'dimension';
    return [field.name, 'detected type: ' + field.type + ' (' + kind + ')',
      'distinct values: ' + (field.distinct == null ? 'unknown' : fmt(field.distinct)),
      'missing values: ' + (field.missing == null ? 'unknown' : fmt(field.missing))].join(' · ');
  }
  function pillNode(field, options) {
    const settings = options || {};
    const node = document.createElement('span');
    node.className = 'studio-pill' + (field.role === 'measure' ? ' is-measure' : '') +
      (selection.includes(field.index) && !settings.zone ? ' is-selected' : '');
    node.draggable = true;
    node.tabIndex = 0;
    node.dataset.column = String(field.index);
    if (settings.zone) node.dataset.zone = settings.zone;
    if (settings.position != null) node.dataset.position = String(settings.position);
    // The gesture comes first in the tooltip: the field facts are useful, but
    // what a click will do is the thing a reader needs before they click.
    node.title = settings.zone
      ? fieldTooltip(field) + ' · Enter to move it, Delete to remove it'
      : CLICK_HINT + ' · ' + fieldTooltip(field);
    node.setAttribute('role', 'button');
    node.setAttribute('aria-label', fieldLabel(field, settings.aggregation) +
      (settings.zone ? ', on ' + settings.zone + '. Press Enter for actions.' : ', field. ' + CLICK_HINT + '.'));
    const glyph = document.createElement('span');
    glyph.className = 'studio-glyph';
    if (field.glyph === 'cal' || field.glyph === 'geo') glyph.append(typeGlyph(field.glyph));
    else glyph.textContent = field.glyph === 'bool' ? 'T/F' : field.glyph === '#' ? '#' : 'Abc';
    glyph.title = field.glyph === 'cal' ? 'Date' : field.glyph === 'geo' ? 'Geography'
      : field.glyph === '#' ? 'Number' : field.glyph === 'bool' ? 'True/false' : 'Text';
    const name = document.createElement('span');
    name.className = 'studio-pill-name';
    name.textContent = fieldLabel(field, settings.aggregation);
    node.append(glyph, name);
    if (settings.zone) {
      const menu = document.createElement('button');
      menu.type = 'button';
      menu.className = 'studio-pill-menu';
      menu.textContent = '▾';
      menu.setAttribute('aria-label', 'Actions for ' + field.name);
      menu.onclick = event => { event.stopPropagation(); sendMenu(node, field, settings); };
      node.append(menu);
      node.oncontextmenu = event => { event.preventDefault(); sendMenu(node, field, settings); };
    }
    node.addEventListener('dragstart', event => {
      dragging = settings.zone
        ? {kind: 'pill', column: field.index, zone: settings.zone, position: settings.position}
        : {kind: 'field', column: field.index};
      dropped = false;
      node.dataset.dragging = 'true';
      event.dataTransfer.effectAllowed = 'move';
      event.dataTransfer.setData('text/plain', field.name);
    });
    node.addEventListener('dragend', () => {
      node.removeAttribute('data-dragging');
      if (dragging && dragging.kind === 'pill' && !dropped) commit(() => removeFrom(dragging.zone, dragging.position));
      dragging = null;
    });
    node.addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); sendMenu(node, field, settings); }
      else if ((event.key === 'Delete' || event.key === 'Backspace') && settings.zone) {
        event.preventDefault();
        commit(() => removeFrom(settings.zone, settings.position));
      }
    });
    node.addEventListener('click', () => {
      if (settings.zone === 'filters') { filterEditor(node, settings.position); return; }
      if (settings.zone) return;
      // A click on a Data-pane field goes through the same place()/commit()
      // path a drop uses, so it is one undo step and one query, not a
      // selection the reader then has to do something else with.
      quickAdd(field);
    });
    return node;
  }

  function popup(anchor, items) {
    document.querySelectorAll('.studio-send').forEach(node => node.remove());
    const menu = document.createElement('div');
    menu.className = 'studio-send';
    for (const [label, action, options] of items) {
      const settings = options || {};
      if (settings.group) {
        const heading = document.createElement('div');
        heading.className = 'studio-send-group';
        heading.textContent = label;
        menu.append(heading);
        continue;
      }
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = label;
      if (settings.disabled || !action) {
        button.disabled = true;
        button.title = settings.reason || '';
      } else {
        button.onclick = () => {
          menu.remove();
          if (anchor.isConnected) anchor.focus();
          action();
        };
      }
      menu.append(button);
    }
    const box = anchor.getBoundingClientRect();
    menu.style.left = Math.round(box.left + window.scrollX) + 'px';
    menu.style.top = Math.round(box.bottom + window.scrollY + 4) + 'px';
    document.body.append(menu);
    // A long menu must never run off the bottom of the window: the entries at
    // the end are the ones nobody thinks to scroll for.
    const height = menu.getBoundingClientRect().height;
    const below = window.innerHeight - box.bottom;
    if (height > below && box.top > below) {
      menu.style.top = Math.max(4, Math.round(box.top + window.scrollY - height - 4)) + 'px';
    }
    const first = menu.querySelector('button:not(:disabled)');
    if (first) first.focus();
    const dismiss = () => {
      menu.remove();
      document.removeEventListener('mousedown', outside);
      document.removeEventListener('keydown', escape);
    };
    const outside = event => { if (!menu.contains(event.target)) dismiss(); };
    const escape = event => { if (event.key === 'Escape') { dismiss(); anchor.focus(); } };
    document.addEventListener('mousedown', outside);
    document.addEventListener('keydown', escape);
    return menu;
  }
  const engine = () => verified() ? 'verified' : 'worksheet';
  const fieldOf = column => core.fieldAt(core.classifyFields(columns(), sheet().types), Number(column));

  // Type glyphs are drawn, never typed: no emoji, and they take the pill's ink.
  function typeGlyph(kind) {
    const svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('viewBox', '0 0 12 12');
    svg.setAttribute('aria-hidden', 'true');
    const shapes = kind === 'cal'
      ? [['rect', {x: 1, y: 2.6, width: 10, height: 8.4, rx: 1, fill: 'none', stroke: 'currentColor', 'stroke-width': 1.2}],
         ['line', {x1: 1, y1: 5.2, x2: 11, y2: 5.2, stroke: 'currentColor', 'stroke-width': 1.2}],
         ['line', {x1: 3.6, y1: 1, x2: 3.6, y2: 3.6, stroke: 'currentColor', 'stroke-width': 1.2}],
         ['line', {x1: 8.4, y1: 1, x2: 8.4, y2: 3.6, stroke: 'currentColor', 'stroke-width': 1.2}]]
      : [['path', {d: 'M6 1.1c-2 0-3.5 1.5-3.5 3.4C2.5 7.2 6 11 6 11s3.5-3.8 3.5-6.5C9.5 2.6 8 1.1 6 1.1z',
          fill: 'none', stroke: 'currentColor', 'stroke-width': 1.2}],
         ['circle', {cx: 6, cy: 4.5, r: 1.2, fill: 'currentColor'}]];
    for (const [tag, attributes] of shapes) {
      const node = document.createElementNS(NS, tag);
      for (const name of Object.keys(attributes)) node.setAttribute(name, String(attributes[name]));
      svg.append(node);
    }
    return svg;
  }

  // Data-type actions. A verified field keeps the role its source defines, so
  // the menu says so rather than offering a change the query cannot express.
  function typeMenuItems(anchor, field, settings) {
    const items = [['Data type', null, {group: true}]];
    const overrides = sheet().types || {};
    for (const role of ['dimension', 'measure']) {
      const label = 'Treat as ' + (role === 'dimension' ? 'Dimension' : 'Measure');
      if (verified()) {
        items.push([label, null, {disabled: true,
          reason: 'Verified fields keep the role the source defines. ZIP, committee ID and election cycle are already dimensions.'}]);
        continue;
      }
      const check = core.canTreatAs(field, role);
      if (!check.ok) { items.push([label, null, {disabled: true, reason: check.reason}]); continue; }
      items.push([label, () => commit(() => {
        const next = Object.assign({}, sheet().types || {});
        next[String(field.index)] = {role: role};
        sheet().types = next;
      })]);
    }
    if (overrides[String(field.index)]) items.push(['Use the detected type', () => commit(() => {
      const next = Object.assign({}, sheet().types || {});
      delete next[String(field.index)];
      sheet().types = next;
    })]);
    return items;
  }

  // Date part is one control, not two: it replaces the older "Use <field> here"
  // swap, it sits at the top of the pill menu so it can never be the entry that
  // falls below the fold, and it reads the catalog's date hierarchy.
  function datePartItems(anchor, field, settings) {
    const parts = core.datePartsFor(field, columns(), engine(), sheet());
    if (!parts.length) return [];
    const items = [['Date part', null, {group: true}]];
    for (const part of parts) {
      if (part.current) {
        items.push(['\u2713 ' + part.label, null,
          {disabled: true, reason: 'This pill already groups by ' + part.label.toLowerCase() + '.'}]);
        continue;
      }
      items.push([part.label, () => commit(() => {
        if (!verified()) { sheet().analytics.period = part.id; sheet().analytics.transform = 'annual'; return; }
        const zone = settings.zone === 'rows' ? 'rows' : settings.zone === 'columns' ? 'columns' : '';
        if (zone) {
          const pills = core.shelf(sheet()[zone]);
          if (pills[settings.position]) {
            pills[settings.position] = {column: part.column, aggregation: 'sum'};
            sheet()[zone] = pills;
            return;
          }
        }
        place('columns', part.column);
      })]);
    }
    return items;
  }

  // The zone a single click uses, and the sentence that names it.
  const zoneLabel = zone => (ZONES.find(z => z[0] === zone) || [zone, zone])[1];
  const quickAddLabel = field => zoneLabel(core.quickAddZone(field, sheet()));
  // A drag takes the pill with it; a click has no pill to take, so a field
  // that is already on a shelf would be copied onto the other one rather than
  // moved. Both the click and its menu entry ask here first.
  const placedOn = field => ['columns', 'rows'].find(name =>
    core.shelf(sheet()[name]).some(p => p.column === field.index));
  function quickAdd(field) {
    const placed = placedOn(field);
    if (placed) { status(field.name + ' is already on ' + zoneLabel(placed) + '.'); return; }
    const zone = core.quickAddZone(field, sheet());
    commit(() => place(zone, field.index));
    status('Added ' + field.name + ' to ' + zoneLabel(zone) + '.');
  }

  function sendMenu(anchor, field, settings) {
    const items = [];
    // The first entry is the gesture a click performs, so the keyboard reaches
    // the same shelf the mouse does without reading down to the Place group.
    if (!settings.zone) {
      const placed = placedOn(field);
      items.push(placed
        ? ['Add to a shelf', null, {disabled: true, reason: field.name + ' is already on ' +
            zoneLabel(placed) + '. Use Send to… to move it.'}]
        : ['Add to ' + quickAddLabel(field), () => quickAdd(field)]);
    }
    if (settings.zone === 'filters') items.push(['Edit filter\u2026', () => filterEditor(anchor, settings.position)]);
    items.push(...datePartItems(anchor, field, settings));
    const onAxis = settings.zone === 'columns' || settings.zone === 'rows';
    if (onAxis && field.role === 'measure') {
      const aggregations = core.aggregationsFor(field, engine());
      items.push(['Measure', null, {group: true}]);
      if (aggregations.length) items.push(['Aggregation\u2026', () => aggregationMenu(anchor, settings.zone, settings.position, aggregations)]);
      else items.push(['Aggregation\u2026', null, {disabled: true,
        reason: field.name + ' is computed from the source observations, so it has one definition.'}]);
      const others = core.classifyFields(columns(), sheet().types).measures.filter(f => f.index !== field.index);
      items.push(['Replace measure\u2026', others.length ? () => popup(anchor, others.map(other => [other.name, () => commit(() => {
        const pills = core.shelf(sheet()[settings.zone]);
        if (pills[settings.position]) { pills[settings.position] = {column: other.index, aggregation: 'sum'}; sheet()[settings.zone] = pills; }
      })])) : null, {disabled: !others.length, reason: 'This source has no other measure.'}]);
      items.push(['Political money\u2026', () => popup(anchor, core.measurePresets(columns(), engine(), sheet().types)
        .map(preset => [preset.label,
          preset.available ? () => commit(() => { sheets[active] = core.applyMeasurePreset(preset.id, sheet(), columns(), engine()); }) : null,
          {disabled: !preset.available, reason: preset.reason}]))]);
    }
    items.push(...typeMenuItems(anchor, field, settings));
    items.push(['Place', null, {group: true}]);
    items.push(...ZONES.map(([zone, label]) => ['Send to ' + label, () => commit(() => {
      if (settings.zone) removeFrom(settings.zone, settings.position);
      place(zone, field.index, null, settings.aggregation);
    })]));
    if (settings.zone) items.push(['Remove from ' + settings.zone, () => commit(() => removeFrom(settings.zone, settings.position))]);
    popup(anchor, items);
  }
  function aggregationMenu(anchor, zone, position, list) {
    popup(anchor, (list || core.AGGREGATIONS).map(([id, label]) => [label, () => commit(() => {
      const pills = core.shelf(sheet()[zone]);
      if (pills[position]) { pills[position].aggregation = id; sheet()[zone] = pills; }
    })]));
  }


  /* ----------------------------------------------------------- shelf edits */

  function removeFrom(zone, position) {
    const state = sheet();
    if (zone === 'columns' || zone === 'rows') state[zone] = core.shelf(state[zone]).filter((_, i) => i !== position);
    else if (zone === 'filters') state.filters = state.filters.filter((_, i) => i !== position);
    else if (zone === 'detail' || zone === 'tooltip') state.marks[zone] = core.shelf(state.marks[zone]).filter((_, i) => i !== position);
    else if (zone === 'pages') { state.pages = null; state.pageMember = ''; }
    else state.marks[zone] = null;
  }
  // The one shelf that can refuse a drop: a column carries a single filter.
  // The drop handler asks before it removes the pill it is moving.
  const canPlace = (zone, column) => zone !== 'filters' ||
    !sheet().filters.some(f => Number(f.column) === column);
  function place(zone, column, position, aggregation) {
    const state = sheet();
    const entry = {column, aggregation: aggregation || 'sum'};
    if (zone === 'columns' || zone === 'rows' || zone === 'detail' || zone === 'tooltip') {
      const list = zone === 'columns' || zone === 'rows' ? core.shelf(state[zone]) : core.shelf(state.marks[zone]);
      const existing = list.findIndex(p => p.column === column);
      if (existing !== -1) list.splice(existing, 1);
      const at = position == null || position > list.length ? list.length : position;
      list.splice(at, 0, entry);
      if (zone === 'columns' || zone === 'rows') state[zone] = list; else state.marks[zone] = list;
    } else if (zone === 'filters') {
      if (!canPlace(zone, column)) return false;
      // A new filter starts as an empty choice, which selects nothing and
      // therefore filters nothing, instead of inheriting an arbitrary value.
      const chosen = core.fieldAt(core.classifyFields(columns(), state.types), column);
      state.filters = state.filters.concat(chosen && chosen.role === 'measure'
        ? {column, op: 'between', value: ['', '']}
        : {column, op: 'in', value: []});
    } else if (zone === 'pages') {
      state.pages = entry;
      state.pageMember = firstMember(column);
    } else {
      state.marks[zone] = entry;
      if (zone === 'label') state.showLabels = true;
    }
    return true;
  }
  // The facet query behind a member list, and the key that identifies it. A
  // field's own filter never narrows its own member list, so opening the
  // checklist shows every member the rest of the scope allows.
  function facetSpec(column) {
    const field = columns().find(f => f.index === column);
    if (!field || field.role !== 'dimension' || !dataset()) return null;
    const filters = [];
    for (const f of sheet().filters || []) {
      if (f.stage === 'aggregate') continue;
      const source = columns().find(c => c.index === Number(f.column));
      if (!source || source.index === column) continue;
      if (source.role === 'measure' && source.id !== 'amount') continue;
      try { filters.push(...contributions.clauses(f, source)); }
      catch { /* an unfinished filter does not narrow the member list */ }
    }
    const facet = {dataset: dataset().id, basis: basis(), dimensions: [field.id], measures: ['records'],
      filters: filters, aggregate_filters: [], sort: [{field: field.id, direction: 'asc'}], limit: 100000, offset: 0};
    return {key: JSON.stringify(facet), facet: facet, field: field};
  }
  function membersCached(column) {
    const spec = verified() ? facetSpec(column) : null;
    if (!spec) return null;
    const entry = memberCache.get(spec.key);
    return entry && !entry.error && entry.values.length ? entry.values : null;
  }
  const memberTotal = column => verified() ? (membersCached(column) || []).length : members(column).length;
  function members(column) {
    if (!data) return [];
    if(verified()){
      const spec=facetSpec(column);if(!spec)return [];
      const {key,facet,field}=spec;
      if(core.pill(sheet().pages)?.column===column)pageMembersKey=key;
      // A facet that failed is remembered for thirty seconds instead of being
      // deleted, because deleting it re-fired the same query from every later
      // render - the page-load query burst.
      const cached=memberCache.get(key);
      if(cached&&(!cached.error||Date.now()-cached.at<30000))return cached.values||[];
      memberCache.set(key,{values:(cached&&cached.values)||[],at:Date.now()});const selectedDataset=dataset().id;
      contributionReady('query',facet).then(result=>{
        const values=result.rows.map(r=>String(r[field.id]??''));memberCache.set(key,{values,at:Date.now()});
        if(verified()&&dataset()?.id===selectedDataset&&pageMembersKey===key&&core.pill(sheet().pages)?.column===column&&!values.includes(sheet().pageMember)){sheet().pageMember=values[0]||'';persist();}
        renderAll();
      }).catch(error=>{memberCache.set(key,{values:[],at:Date.now(),error:error.message});failure(error.message);});return [];
    }
    const seen = [];
    for (const row of data.rows) {
      const value = String(row[column] == null ? '' : row[column]);
      if (value !== '' && !seen.includes(value)) seen.push(value);
      if (seen.length >= 500) break;
    }
    return seen.sort((a, b) => a.localeCompare(b, undefined, {numeric: true}));
  }
  const firstMember = column => verified() ? String(data?.rows.find(row=>row[column]!=null&&row[column]!=='')?.[column]??'') : members(column)[0] || '';

  function dropTarget(node, zone) {
    node.dataset.zone = zone;
    node.addEventListener('dragover', event => {
      if (!dragging) return;
      event.preventDefault();
      event.dataTransfer.dropEffect = 'move';
      node.classList.add('is-over');
    });
    node.addEventListener('dragleave', () => node.classList.remove('is-over'));
    node.addEventListener('drop', event => {
      event.preventDefault();
      node.classList.remove('is-over');
      if (!dragging) return;
      dropped = true;
      const move = dragging;
      dragging = null;
      const before = event.target.closest ? event.target.closest('.studio-pill') : null;
      let at = before && before.dataset.position != null && before.parentElement === node ? Number(before.dataset.position) : null;
      if (move.kind === 'analytics') { applyAnalytics(move.id); return; }
      // Filters are ANDed, so their order carries no meaning: a filter pill
      // dropped back onto the Filters shelf — onto itself, another filter or the
      // empty shelf — is a silent no-op. Origin is dragging.zone; the live drag
      // marker on the still-attached pill is a fallback, so this can never fall
      // through to the "already has a filter" refusal on the pill's own column.
      // A pill from Columns/Rows/marks is in another shelf, so its column is
      // still refused with the note below.
      if (zone === 'filters' && move.kind === 'pill' &&
          (move.zone === 'filters' || el('filters').querySelector('.studio-pill[data-dragging="true"]'))) return;
      if (move.kind === 'pill' && move.zone === zone) {
        if (at === move.position) return; // dropping a pill on itself is not an edit
        // The target position was read while the pill was still on this shelf,
        // so everything after it shifts down by one once the pill leaves.
        if (at != null && move.position < at) at -= 1;
      }
      // Decide before removing: a shelf that refuses the drop must not cost the
      // user the pill they were dragging.
      if (move.kind === 'pill' && !canPlace(zone, move.column)) {
        const field = core.fieldAt(core.classifyFields(columns(), sheet().types), move.column);
        el('note').textContent = (field ? field.name : 'That field') + ' already has a filter.';
        return;
      }
      commit(() => {
        const aggregation = move.zone ? (core.shelf(sheet()[move.zone] || (sheet().marks || {})[move.zone])[move.position] || {}).aggregation : 'sum';
        if (move.kind === 'pill') removeFrom(move.zone, move.position);
        place(zone, move.column, at, aggregation);
      });
    });
  }

  /* -------------------------------------------------------------- rendering */

  function renderFields() {
    const meta = core.classifyFields(columns(), sheet().types);
    el('field-table-label').hidden=!verified();const table=el('field-table').value;fill(el('field-table'),[['','All related tables'],...[...new Set(meta.fields.map(f=>f.table).filter(Boolean))].map(t=>[t,t])]);el('field-table').value=table;
    const query = el('search').value.trim().toLowerCase();
    const matches = field => (!verified()||!table||field.table===table)&&(!query || [field.name,field.id,field.table,field.data_type,field.description].filter(Boolean).join(' ').toLowerCase().includes(query));
    const into = (node, fields) => node.replaceChildren(...fields.filter(matches).map(f => pillNode(f, {})));
    into(el('dimensions'), meta.dimensions);
    into(el('measures'), meta.measures);
    into(el('hidden'), meta.hidden);
    el('hidden-block').hidden = !el('show-hidden').checked || !meta.hidden.length;
    el('hidden-note').hidden = !meta.hidden.length;
    el('hidden-note').textContent = meta.hidden.length + ' identifier field' + (meta.hidden.length === 1 ? '' : 's') +
      ' hidden (IDs, codes, ZIPs) — tick "Show identifier fields" to chart by them';
  }

  function renderShelves() {
    const meta = core.classifyFields(columns(), sheet().types);
    const state = sheet();
    const shelfInto = (node, zone, list, placeholder) => {
      const pills = core.shelf(list)
        .map((p, position) => ({p, position, field: core.fieldAt(meta, p.column)}))
        .filter(item => item.field)
        .map(item => pillNode(item.field, {zone, position: item.position, aggregation: item.p.aggregation}));
      node.replaceChildren(...pills);
      node.dataset.placeholder = placeholder;
      node.dataset.empty = pills.length ? 'false' : 'true';
    };
    shelfInto(el('columns'), 'columns', state.columns, 'Drop a field here');
    shelfInto(el('rows'), 'rows', state.rows, 'Drop a field here');
    shelfInto(el('detail'), 'detail', state.marks.detail, 'Detail');
    shelfInto(el('tooltip'), 'tooltip', state.marks.tooltip, 'Tooltip');
    for (const zone of ['color', 'size', 'label']) {
      shelfInto(el(zone), zone, state.marks[zone] == null ? [] : [state.marks[zone]], zone === 'color' ? 'Colour' : zone === 'size' ? 'Size' : 'Label');
    }
    shelfInto(el('pages'), 'pages', state.pages == null ? [] : [state.pages], 'One dimension');
    const filterPills = state.filters.map((filter, position) => {
      const field = core.fieldAt(meta, Number(filter.column));
      if (!field) return null;
      const node = pillNode(field, {zone: 'filters', position});
      const summary = core.filterSummary(filter, field, memberTotal(field.index));
      node.querySelector('.studio-pill-name').textContent = summary;
      node.title = summary + ' \u00b7 Enter for actions, Delete to remove it';
      return node;
    }).filter(Boolean);
    el('filters').replaceChildren(...filterPills);
    el('filters').dataset.placeholder = 'Drop a field to filter';
    el('filters').dataset.empty = filterPills.length ? 'false' : 'true';
    el('mark').value = state.marks.type;
    renderPager();
  }

  function renderPager() {
    const state = sheet();
    const pill = core.pill(state.pages);
    // A pager inside a folded disclosure is a control nobody can find, so
    // placing a Pages field opens it once.
    const pagerWasHidden = el('pager').hidden;
    el('pager').hidden = !pill;
    if (pill && pagerWasHidden && el('pages-details')) el('pages-details').open = true;
    if (!pill) { stopPlay(); return; }
    const list = members(pill.column);
    const at = Math.max(0, list.indexOf(state.pageMember));
    el('pager-label').textContent = list.length ? (at + 1) + ' of ' + list.length + ' · ' + state.pageMember : 'No members';
    el('pager-prev').disabled = !list.length;
    el('pager-next').disabled = !list.length;
  }
  function stepPage(delta) {
    const pill = core.pill(sheet().pages);
    if (!pill) return;
    const list = members(pill.column);
    if (!list.length) return;
    const at = (list.indexOf(sheet().pageMember) + delta + list.length) % list.length;
    commit(() => { sheet().pageMember = list[at]; });
  }
  function stopPlay() {
    if (pageTimer) clearInterval(pageTimer);
    pageTimer = 0;
    el('pager-play').setAttribute('aria-pressed', 'false');
    el('pager-play').textContent = '▶';
  }
  function togglePlay() {
    if (pageTimer) { stopPlay(); return; }
    pageTimer = setInterval(() => stepPage(1), 1400);
    el('pager-play').setAttribute('aria-pressed', 'true');
    el('pager-play').textContent = '❚❚';
  }

  /* --------------------------------------------------------------- show me */

  const GLYPHS = {
    'text-table': 'table', 'heat-map': 'grid', 'highlight-table': 'grid', 'symbol-map': 'map', 'filled-map': 'map',
    'pie-chart': 'pie', 'horizontal-bars': 'barsh', 'stacked-bars': 'stack', 'side-by-side-bars': 'side',
    'treemap': 'tree', 'circle-views': 'circles', 'side-by-side-circles': 'circles2', 'lines-continuous': 'line',
    'lines-discrete': 'linestep', 'dual-lines': 'line2', 'area-continuous': 'area', 'area-discrete': 'area',
    'dual-combination': 'combo', 'scatter-plot': 'scatter', 'histogram': 'hist', 'box-and-whisker': 'box',
    'gantt': 'gantt', 'bullet-graph': 'bullet', 'packed-bubbles': 'bubbles'
  };
  const SHAPES = {
    table: [['r', 2, 3, 28, 5], ['r', 2, 10, 28, 5], ['r', 2, 17, 28, 5]],
    grid: [['r', 2, 3, 8, 8], ['r', 12, 3, 8, 8], ['r', 22, 3, 8, 8], ['r', 2, 13, 8, 8], ['r', 12, 13, 8, 8], ['r', 22, 13, 8, 8]],
    map: [['p', '4,16 10,5 18,9 24,4 29,14 20,21 9,20']],
    pie: [['c', 16, 12, 10], ['l', 16, 12, 16, 2], ['l', 16, 12, 25, 17]],
    barsh: [['r', 2, 3, 26, 4], ['r', 2, 10, 18, 4], ['r', 2, 17, 10, 4]],
    stack: [['r', 4, 10, 7, 12], ['r', 4, 4, 7, 6], ['r', 14, 13, 7, 9], ['r', 14, 6, 7, 7], ['r', 24, 8, 5, 14]],
    side: [['r', 3, 9, 4, 13], ['r', 8, 5, 4, 17], ['r', 15, 12, 4, 10], ['r', 20, 7, 4, 15], ['r', 26, 10, 4, 12]],
    tree: [['r', 2, 3, 16, 12], ['r', 19, 3, 11, 7], ['r', 19, 11, 11, 4], ['r', 2, 16, 9, 6], ['r', 12, 16, 18, 6]],
    circles: [['c', 6, 17, 3], ['c', 13, 10, 3], ['c', 20, 14, 3], ['c', 27, 6, 3]],
    circles2: [['c', 6, 17, 3], ['c', 11, 8, 3], ['c', 19, 15, 3], ['c', 24, 6, 3]],
    line: [['pl', '2,20 9,12 16,15 23,6 30,9']],
    linestep: [['pl', '2,20 9,20 9,12 16,12 16,15 23,15 23,6 30,6']],
    line2: [['pl', '2,20 9,12 16,15 23,6 30,9'], ['pl', '2,13 9,17 16,8 23,14 30,4']],
    area: [['p', '2,21 2,14 9,8 16,13 23,5 30,10 30,21']],
    combo: [['r', 3, 12, 5, 10], ['r', 12, 8, 5, 14], ['r', 21, 14, 5, 8], ['pl', '5,9 14,4 23,11 29,6']],
    scatter: [['c', 5, 18, 2], ['c', 11, 11, 2], ['c', 15, 16, 2], ['c', 21, 7, 2], ['c', 26, 12, 2], ['c', 9, 6, 2]],
    hist: [['r', 3, 15, 4, 7], ['r', 8, 9, 4, 13], ['r', 13, 4, 4, 18], ['r', 18, 8, 4, 14], ['r', 23, 14, 4, 8]],
    box: [['l', 8, 4, 8, 20], ['r', 4, 8, 9, 8], ['l', 22, 6, 22, 21], ['r', 18, 10, 9, 6]],
    gantt: [['r', 3, 4, 12, 4], ['r', 9, 10, 14, 4], ['r', 16, 16, 12, 4]],
    bullet: [['r', 2, 9, 28, 7], ['r', 2, 9, 17, 7], ['l', 23, 6, 23, 19]],
    bubbles: [['c', 10, 13, 7], ['c', 22, 9, 5], ['c', 23, 19, 3], ['c', 5, 5, 3]]
  };
  function glyphSvg(kind) {
    const svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('viewBox', '0 0 32 24');
    svg.setAttribute('aria-hidden', 'true');
    for (const shape of SHAPES[kind] || SHAPES.table) {
      let node;
      if (shape[0] === 'r') {
        node = document.createElementNS(NS, 'rect');
        node.setAttribute('x', shape[1]); node.setAttribute('y', shape[2]);
        node.setAttribute('width', shape[3]); node.setAttribute('height', shape[4]);
        node.setAttribute('fill', 'currentColor');
      } else if (shape[0] === 'c') {
        node = document.createElementNS(NS, 'circle');
        node.setAttribute('cx', shape[1]); node.setAttribute('cy', shape[2]); node.setAttribute('r', shape[3]);
        node.setAttribute('fill', 'currentColor');
      } else if (shape[0] === 'l') {
        node = document.createElementNS(NS, 'line');
        node.setAttribute('x1', shape[1]); node.setAttribute('y1', shape[2]);
        node.setAttribute('x2', shape[3]); node.setAttribute('y2', shape[4]);
        node.setAttribute('stroke', 'currentColor'); node.setAttribute('stroke-width', '1.6');
      } else {
        node = document.createElementNS(NS, shape[0] === 'p' ? 'polygon' : 'polyline');
        node.setAttribute('points', shape[1]);
        node.setAttribute('fill', shape[0] === 'p' ? 'currentColor' : 'none');
        node.setAttribute('stroke', 'currentColor');
        node.setAttribute('stroke-width', '1.6');
      }
      svg.append(node);
    }
    return svg;
  }

  function renderShowMe() {
    // Show Me reads the shelves. A click now places a field instead of marking
    // it, so there is no separate selection for a tile to read.
    const selectionCounts = core.showMeSelection(sheet(), columns(), []);
    const tiles = verified()?contributions.showMeEligibility(selectionCounts):core.showMeEligibility(selectionCounts);
    const recommended = data ? core.recommendedTile(columns()) : '';
    el('showme-grid').replaceChildren(...tiles.map(tile => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'studio-tile' + (tile.id === recommended && tile.enabled ? ' is-recommended' : '');
      button.disabled = !tile.enabled || !data;
      button.dataset.tile = tile.id;
      const caption = document.createElement('span');
      caption.textContent = tile.label;
      button.append(glyphSvg(GLYPHS[tile.id]), caption);
      button.title = tile.enabled
        ? tile.label + ': ' + tile.requirement + (tile.note ? ' · ' + tile.note : '')
        : tile.label + ': ' + tile.reason;
      button.setAttribute('aria-label', button.title);
      const describe = () => {
        hoverTile = tile.id;
        el('showme-foot').textContent = tile.label + ' — ' + tile.requirement +
          (tile.enabled ? (tile.note ? ' · ' + tile.note : '') : ' · ' + tile.reason);
      };
      button.addEventListener('mouseenter', describe);
      button.addEventListener('focus', describe);
      button.onclick = () => commit(() => {
        if(verified()&&['symbol-map','filled-map'].includes(tile.id)){
          const filled=tile.id==='filled-map';sheet().columns=[{column:columns().find(f=>f.id===(filled?'state':'zip5')).index,aggregation:'sum'}];sheet().rows=[{column:columns().find(f=>f.id==='amount').index,aggregation:'sum'}];sheet().marks={type:filled?'filled-map':'map',color:null,size:null,label:null,detail:[],tooltip:[]};sheet().analytics.transform='none';return;
        }
        const next = (verified()?contributions:core).showMeApply(tile.id, sheet(), columns(), []);
        sheets[active] = next;
      });
      return button;
    }));
    if (!hoverTile) el('showme-foot').textContent = recommended
      ? 'Suggested from the scanned columns: ' + (tiles.find(t => t.id === recommended) || {}).label
      : 'Choose fields to see what fits.';
    // The suggestion also rides on the closed disclosure's own summary, so a
    // reader can see what fits without opening it.
    const hint = el('showme-hint');
    if (hint) hint.textContent = recommended
      ? ' · suggested: ' + ((tiles.find(t => t.id === recommended) || {}).label || '')
      : '';
  }

  /* ------------------------------------------------------------- analytics */

  // An analytics object that cannot change this view must say so rather than
  // toggle and draw nothing. The reasons are the renderers' own limits: the
  // verified path draws reference lines only in contribution-plot.js, and a
  // grand total there is a stated figure, not a mark.
  function analyticsRefusal(item) {
    const state = sheet();
    if (!data) return 'Choose a data source first.';
    if (!verified()) return '';
    const type = (state.marks && state.marks.type) || 'automatic';
    if (item.group === 'transform') {
      const timely = core.shelf([...state.columns, ...state.rows])
        .some(p => ['date', 'year', 'cycle'].includes(columns()[p.column] && columns()[p.column].id));
      return timely ? '' : 'Needs Contribution date, Year or Election cycle on Columns or Rows.';
    }
    if (item.id === 'totals') return '';
    if (MentatContributionCharts.TYPES.includes(type) || ['pie','doughnut','waterfall','pareto','radar','map','filled-map','table','text'].includes(type)) {
      return 'Reference lines are drawn on bar, line, area and circle marks.';
    }
    if (state.analytics.transform !== 'none') return 'Reference lines are not drawn on a period-analysis view.';
    return '';
  }

  function analyticsRow(item, state, role) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'studio-analytics-item';
    const refusal = analyticsRefusal(item);
    button.draggable = !refusal;
    button.disabled = !!refusal;
    const on = item.group === 'transform' ? state.analytics.transform === item.id : !!state.analytics[item.id];
    button.setAttribute('role', role);
    button.setAttribute('aria-checked', String(on));
    const text = document.createElement('span');
    text.className = 'studio-analytics-text';
    const title = document.createElement('span');
    title.textContent = item.label;
    const hint = document.createElement('small');
    hint.textContent = refusal || item.hint;
    text.append(title, hint);
    const knob = document.createElement('span');
    knob.className = 'studio-switch';
    knob.setAttribute('aria-hidden', 'true');
    if (refusal) button.title = refusal;
    button.append(text, knob);
    button.onclick = () => applyAnalytics(item.id);
    button.addEventListener('dragstart', event => {
      dragging = {kind: 'analytics', id: item.id};
      dropped = false;
      event.dataTransfer.effectAllowed = 'copy';
      event.dataTransfer.setData('text/plain', item.label);
    });
    button.addEventListener('dragend', () => { dragging = null; });
    return button;
  }

  function renderAnalytics() {
    const state = sheet();
    const host = el('analytics-list');
    host.replaceChildren();
    // One period analysis at a time; the reference lines are independent.
    for (const [kind, heading, role] of [['transform', 'Period analysis', 'radio'], ['flag', 'Summarize', 'switch']]) {
      const label = document.createElement('p');
      label.className = 'studio-analytics-group';
      label.textContent = heading;
      const box = document.createElement('div');
      if (role === 'radio') {
        box.setAttribute('role', 'radiogroup');
        box.setAttribute('aria-label', heading);
      }
      for (const item of ANALYTICS.filter(a => a.group === kind)) box.append(analyticsRow(item, state, role));
      host.append(label, box);
    }
  }
  function applyAnalytics(id) {
    const item = ANALYTICS.find(a => a.id === id);
    if (!item) return;
    commit(() => {
      const analytics = sheet().analytics;
      if (item.group === 'transform') analytics.transform = analytics.transform === id ? 'none' : id;
      else analytics[id] = !analytics[id];
    });
  }

  /* ------------------------------------------------------- company overview */

  // Four preset views of one company. No iframes: each card compiles a preset
  // sheet, runs the ordinary verified query and paints it with the same
  // renderers the builder uses, so a card and its builder view are one view.
  function overviewCycle() {
    const field = columns().find(f => f.id === 'cycle');
    if (!field) return '';
    const filter = (sheet().filters || []).find(f => Number(f.column) === field.index);
    if (!filter || !core.filterActive(filter)) return '';
    const values = core.filterValues(filter);
    return (filter.op === 'equals' || filter.op === 'in') && values.length === 1 ? values[0] : '';
  }
  function renderOverviewControls() {
    const toggle = el('overview-toggle');
    const reason = !verified() ? 'Company overview uses verified contributions.'
      : !data || !dataset() ? 'Choose a verified report source first.'
      : !columns().some(f => f.id === 'company') ? 'This source has no company field.' : '';
    toggle.disabled = !!reason;
    toggle.title = reason || 'Four preset views of one company';
    if (reason) overviewMode = false;
    syncViewMode();
    el('overview').hidden = !overviewMode;
    el('grid').hidden = dataSourceTab || overviewMode;
    const host = document.querySelector('#view-chart-studio .studio');
    if (host) host.classList.toggle('studio-overview-mode', overviewMode);
  }
  function renderOverview() {
    const field = columns().find(f => f.id === 'company');
    if (!field) return;
    const list = members(field.index);
    const carried = (appliedScope && appliedScope.company) || '';
    if (!overviewCompany || (list.length && list.indexOf(overviewCompany) === -1)) {
      overviewCompany = list.indexOf(carried) !== -1 ? carried : list[0] || '';
    }
    fill(el('overview-company'), list.length ? list.map(m => [m, m]) : [['', 'Reading companies\u2026']]);
    el('overview-company').value = overviewCompany;
    const cycle = overviewCycle();
    el('overview-scope').textContent = [overviewCompany || 'No company selected',
      (dataset() || {}).label || (dataset() || {}).id || '', cycle ? 'Cycle ' + cycle : 'All cycles',
      contributions.BASIS[basis()][0]].filter(Boolean).join(' \u00b7 ');
    const ticket = ++overviewRevision;
    const grid = el('overview-grid');
    grid.replaceChildren();
    const cards = core.companyOverviewPresets().map(preset => {
      const card = document.createElement('section');
      card.className = 'studio-overview-card';
      const title = document.createElement('h3');
      title.textContent = preset.title;
      const note = document.createElement('p');
      note.className = 'studio-note';
      note.textContent = preset.note;
      const body = document.createElement('div');
      body.className = 'studio-overview-body';
      body.textContent = 'Reading verified totals\u2026';
      const actions = document.createElement('div');
      actions.className = 'studio-overview-actions';
      const open = document.createElement('button');
      open.type = 'button';
      open.textContent = 'Open in builder';
      open.onclick = () => {
        overviewMode = false;
        commit(() => {
          sheets[active] = core.companyOverviewSheet(preset, columns(),
            {company: overviewCompany, cycle: overviewCycle()}, sheet());
        });
      };
      actions.append(open);
      card.append(title, note, body, actions);
      if (!grid.children.length) card.classList.add('is-focused');
      card.onmouseenter = () => {
        for (const other of grid.children) other.classList.toggle('is-focused', other === card);
      };
      grid.append(card);
      return {preset: preset, body: body};
    });
    if (!overviewCompany) {
      for (const item of cards) item.body.textContent = 'Choose a company to read its giving.';
      return;
    }
    // One query at a time: queryCached aborts the previous request, so four
    // parallel cards would cancel each other.
    (async () => {
      for (const item of cards) {
        if (ticket !== overviewRevision) return;
        try { await renderOverviewCard(item.preset, item.body, ticket); }
        catch (error) { if (ticket === overviewRevision && error.name !== 'AbortError') item.body.textContent = error.message; }
      }
    })();
  }
  async function renderOverviewCard(preset, body, ticket) {
    const missing = core.companyOverviewMissing(preset, columns());
    if (missing.length) { body.textContent = 'This source has no ' + missing.join(' or ') + ' field.'; return; }
    const state = core.companyOverviewSheet(preset, columns(), {company: overviewCompany, cycle: overviewCycle()});
    const compiled = contributions.compile(state, columns(), {dataset: dataset().id, industry: dataset().industry, basis: basis(), offset: 0});
    const result = await queryCached(compiled.query);
    if (ticket !== overviewRevision) return;
    body.replaceChildren();
    if (!result.rows.length) { body.textContent = 'No matching observations in this scope.'; return; }
    const spec = Object.assign({}, compiled.spec, {columns: result.columns, title: preset.title});
    if (['pie', 'doughnut', 'waterfall', 'pareto', 'radar'].includes(spec.type)) {
      const id = spec.measures[0], currency = contributions.MONEY.has(id);
      const groups = result.rows.map(row => ({label: contributionPlot.label(row, spec.dimensions),
        value: row[id] / (currency ? 100 : 1), n: 1}));
      const measure = ((result.columns.find(c => c.id === id) || {}).name || id) + (currency ? ' (USD)' : '');
      const drawn = paint.chartSVG({type: spec.type, groups: groups, selected: result.totals.records, excluded: 0},
        measure, {type: spec.type, aggregation: 'sum', x: 0, y: 1},
        {sheet: (dataset() || {}).label || (dataset() || {}).id || '', columns: [{name: 'Group'}, {name: id}]},
        preset.title, '');
      body.append(drawn.svg);
    } else if (MentatContributionCharts.TYPES.includes(spec.type)) {
      MentatContributionCharts.render(body, result.rows, spec, () => {});
    } else {
      contributionPlot.render(body, result.rows, spec, () => {});
    }
  }

  /* ---------------------------------------------------------------- board */

  // Canvas mode as a board of 1, 2 or 4 tiles, each holding one sheet. Exactly
  // one tile is selected, and the selected tile is the sheet `active` names, so
  // the Inspector, Show Me, Export and "Add to briefing" have one answer to
  // "which chart?" whether a board is up or not. Nothing here reaches the URL or
  // a storage key of its own: the board rides in the workspace entry beside the
  // sheets (D-039).
  const BOARD_TILES = [1, 2, 4];
  const canvasOnly = () => {
    const host = document.querySelector('#view-chart-studio .studio');
    return !!(host && host.classList.contains('studio-options-hidden'));
  };
  const boardTiles = () => (board && !overviewMode && !dataSourceTab && canvasOnly()) ? board.tiles : 1;
  const filledSlots = () => board ? board.slots.filter(at => at != null).length : 0;

  // What a sheet last drew, kept by its own id so it survives a re-index.
  // Keyed by the source as well as the sheet: sheet ids start again at s1 in every
  // workspace, so a bare id would hand a tile the figures another report left behind.
  const tileKey = state => sourceKey + '|' + ((state && state.id) || '');
  function tileRecord(state) {
    const key = tileKey(state);
    if (!tileMemory.has(key)) {
      tileMemory.set(key, {revision: 0, waiting: null, request: null, result: null,
        title: '', scope: '', offset: 0});
    }
    return tileMemory.get(key);
  }
  // Nothing is remembered for a sheet that is not on the board. The map is at most
  // four entries wide, and a tile cannot be handed what it drew two arrangements ago.
  function pruneTileMemory() {
    const keep = new Set((board ? board.slots : []).filter(at => at != null).map(at => tileKey(sheets[at])));
    for (const key of [...tileMemory.keys()]) {
      if (keep.has(key)) continue;
      releaseFlight(tileMemory.get(key));
      tileMemory.delete(key);
    }
  }
  // The tile's own title, subtitle, canvas, table, note, reconciliation strip and
  // status line. Anything else a render path writes belongs to the chrome: the
  // selected tile writes the real one, an unselected tile writes a node nobody
  // can see, which is how one render path serves both without a flag per line.
  function tileNodes(tile, selected) {
    const spare = new Map();
    return id => {
      const own = tile.querySelector('.studio-board-tile-' + id);
      if (own) return own;
      if (selected) return el(id);
      if (!spare.has(id)) spare.set(id, document.createElement('div'));
      return spare.get(id);
    };
  }
  function tileSurface(tile, index, selected) {
    const state = sheets[index], record = tileRecord(state);
    return {state: state, index: index, el: tileNodes(tile, selected), primary: selected,
      flight: record, canvasClass: 'studio-board-tile-canvas ',
      // The selected tile also moves the console's own ticket, so a record
      // inspection started against the previous chart is still invalidated.
      bump: () => { if (selected) ++contributionRevision; return ++record.revision; },
      stale: ticket => ticket !== record.revision,
      ticket: () => record.revision,
      // Its own page. The group pager, the label under the chart and the caption
      // an export carries all read this one number, so a tile on page two and the
      // tile beside it on page one can never describe each other's figures.
      get offset() { return record.offset; }, set offset(value) { record.offset = value; },
      get request() { return record.request; },
      set request(value) { record.request = value; if (selected) contributionRequest = value; },
      get result() { return record.result; },
      set result(value) { record.result = value; if (selected) contributionResult = value; },
      get title() { return record.title; },
      set title(value) { record.title = value; if (selected) lastTitle = value; },
      get scope() { return record.scope; },
      set scope(value) { record.scope = value; if (selected) lastScope = value; }};
  }
  // Export, Copy image, Print and Add to briefing act on the selected tile when
  // a board is up, and on the single canvas when it is not.
  function activeSurface() {
    return boardSurfaces.find(view => view && view.primary) || mainSurface();
  }
  function syncBoardSelection() {
    if (!board || board.slots.includes(active)) return;
    const first = board.slots.find(at => at != null);
    if (first != null) active = first;
  }
  // A sheet can leave (a saved view with fewer sheets opens, an undo steps back),
  // and a slot naming one that is gone would draw a tile from nothing. The tile
  // count is the reader's choice and is kept; the slot is cleared.
  function settleBoard() {
    if (!board) return;
    const tiles = BOARD_TILES.includes(board.tiles) ? board.tiles : 1;
    if (tiles === 1) { board = null; return; }
    const taken = new Set(), slots = [];
    for (let slot = 0; slot < tiles; slot += 1) {
      const at = (board.slots || [])[slot];
      const keep = Number.isInteger(at) && at >= 0 && at < sheets.length && !taken.has(at);
      slots.push(keep ? at : null);
      if (keep) taken.add(at);
    }
    board = core.normalizeBoard({sheets: sheets, board: {tiles: tiles, slots: slots}});
    syncBoardSelection();
  }
  // A sheet inserted above a placed one shifts its index, so the board follows
  // the sheets rather than the numbers.
  function shiftBoard(at) {
    if (!board) return;
    board.slots = board.slots.map(slot => (slot == null || slot < at) ? slot : slot + 1);
  }
  // Putting a sheet in a tile, or emptying one, is an edit like any other: it goes
  // through commit(), so Undo steps back through it and Redo brings it back.
  function placeInSlot(slot, index) {
    if (!board) return;
    commit(() => {
      board.slots = board.slots.map((at, other) => (index != null && at === index && other !== slot) ? null : at);
      board.slots[slot] = index;
      if (index != null) active = index; else syncBoardSelection();
    });
  }
  function setBoard(tiles) {
    if (!BOARD_TILES.includes(tiles)) return;
    if ((board ? board.tiles : 1) === tiles) return;
    commit(() => arrangeBoard(tiles));
  }
  function arrangeBoard(tiles) {
    if (tiles === 1) board = null;
    else {
      const taken = new Set(), slots = [];
      for (let slot = 0; slot < tiles; slot += 1) {
        const at = board ? board.slots[slot] : (slot === 0 ? active : null);
        const keep = Number.isInteger(at) && at >= 0 && at < sheets.length && !taken.has(at);
        slots.push(keep ? at : null);
        if (keep) taken.add(at);
      }
      if (!slots.includes(active) && slots.indexOf(null) >= 0) {
        slots[slots.indexOf(null)] = active;
        taken.add(active);
      }
      // An empty tile beside a full one is a hole nobody asked for, so the
      // sheets not placed yet fill the rest in their own order.
      for (let slot = 0; slot < slots.length; slot += 1) {
        if (slots[slot] != null) continue;
        const next = sheets.findIndex((sheet, at) => !taken.has(at));
        if (next < 0) break;
        slots[slot] = next;
        taken.add(next);
      }
      board = {tiles: tiles, slots: slots};
      syncBoardSelection();
    }
  }
  // A sheet sits in one tile only, so a tile offers the sheet it holds and the
  // sheets no other tile has taken. The last filled tile keeps its sheet: an empty
  // board would leave no tile selected and nothing for the Inspector.
  function sheetChoices(index, slot) {
    const placed = new Set(board.slots.filter((at, other) => at != null && other !== slot));
    const options = index == null ? [['', 'Choose a sheet']]
      : filledSlots() > 1 ? [['', 'Empty this tile']] : [];
    sheets.forEach((entry, at) => { if (!placed.has(at)) options.push([String(at), entry.name]); });
    return options;
  }
  // Everything about a tile that can change while the tile itself stays: which
  // sheet it holds, whether it is the selected one, what its select offers. The
  // select is only rewritten when its choices really differ, so a reader with the
  // list open, or the keyboard in it, keeps it.
  function dressTile(tile, index, slot) {
    const state = index == null ? null : sheets[index];
    const selected = state != null && index === active;
    tile.classList.toggle('is-selected', selected);
    tile.dataset.sheet = state ? state.id : '';
    const select = tile.querySelector('.studio-board-tile-sheet');
    const options = sheetChoices(index, slot);
    const same = select.options.length === options.length
      && [...select.options].every((option, at) => option.value === options[at][0]
        && option.textContent === options[at][1]);
    if (!same) select.replaceChildren(...options.map(([value, label]) => new Option(label, value)));
    const wanted = state == null ? '' : String(index);
    if (select.value !== wanted) select.value = wanted;
    select.onchange = () => placeInSlot(slot, select.value === '' ? null : Number(select.value));
    const head = tile.querySelector('.studio-board-tile-head');
    let mark = tile.querySelector('.studio-board-tile-mark');
    if (selected && !mark) {
      mark = document.createElement('span');
      mark.className = 'studio-board-tile-mark';
      mark.textContent = 'Selected \u00b7 the Inspector edits this tile';
      head.append(mark);
    } else if (!selected && mark) {
      mark.remove();
    }
    tile.onclick = event => {
      if (event.target.closest('.studio-board-tile-head')) return;
      if (state == null || index === active) return;
      active = index;
      persist();
      renderAll();
    };
  }
  function buildTile(index, slot) {
    const state = index == null ? null : sheets[index];
    const tile = document.createElement('section');
    tile.className = 'studio-board-tile';
    tile.setAttribute('aria-label', 'Board tile ' + (slot + 1));
    const head = document.createElement('div');
    head.className = 'studio-board-tile-head';
    const select = document.createElement('select');
    select.className = 'studio-board-tile-sheet';
    select.setAttribute('aria-label', 'Sheet in tile ' + (slot + 1));
    head.append(select);
    const title = document.createElement('h3');
    title.className = 'studio-board-tile-title';
    const subtitle = document.createElement('p');
    subtitle.className = 'studio-board-tile-subtitle';
    const canvas = document.createElement('div');
    canvas.className = 'studio-board-tile-canvas studio-canvas fit-' + (state ? state.fit : 'standard');
    const table = document.createElement('div');
    table.className = 'studio-board-tile-table table-scroll';
    table.hidden = true;
    const foot = document.createElement('div');
    foot.className = 'studio-board-tile-foot';
    const reconcile = document.createElement('p');
    reconcile.className = 'studio-board-tile-reconcile studio-reconcile';
    reconcile.setAttribute('role', 'status');
    reconcile.hidden = true;
    const note = document.createElement('p');
    note.className = 'studio-board-tile-note';
    const status = document.createElement('p');
    status.className = 'studio-board-tile-status';
    foot.append(reconcile, note, status);
    tile.append(head, title, subtitle);
    if (state == null) {
      const empty = document.createElement('p');
      empty.className = 'studio-board-tile-empty';
      empty.textContent = 'Empty tile. Choose a sheet for it above.';
      canvas.hidden = true;
      tile.append(empty);
    }
    tile.append(canvas, table, foot);
    dressTile(tile, index, slot);
    return tile;
  }
  // A tile's nodes going away for good. The one map instance lives in a canvas, so
  // a tile that was hosting it takes it with it rather than leaving the instance
  // and its listeners behind.
  function discardTile(node) {
    if (!node) return;
    if (contributionMapHost && node.contains(contributionMapHost)) {
      clearTimeout(geometryTimer);
      contributionMap?.destroy?.();
      contributionMap = null;
      contributionMapHost = null;
      ++geometryRevision;
    }
    node.remove();
  }
  function renderBoard() {
    const host = el('board');
    const tiles = boardTiles();
    const studio = document.querySelector('#view-chart-studio .studio');
    if (studio) studio.classList.toggle('studio-board-on', tiles > 1);
    boardSurfaces = [];
    if (tiles < 2) {
      for (const node of boardNodes) discardTile(node);
      boardNodes = [];
      host.hidden = true;
      host.replaceChildren();
      pruneTileMemory();
      return;
    }
    pruneTileMemory();
    // The board takes the canvas over, so the canvas is emptied rather than left
    // holding a drawing that only CSS is hiding.
    el('canvas').replaceChildren();
    syncBoardSelection();
    host.hidden = false;
    host.className = 'studio-board studio-board-' + tiles;
    // A slot that still holds the same sheet keeps its own nodes: its drawing, its
    // title, its reconciliation line, its scroll and the focus in it all survive a
    // render, so a refresh in flight - or a cancelled one - leaves the last loaded
    // view on screen exactly as the single canvas does.
    const made = board.slots.map((index, slot) => {
      const kept = boardNodes[slot];
      const wanted = index == null ? '' : sheets[index].id;
      if (kept && kept.dataset.sheet === wanted) { dressTile(kept, index, slot); return kept; }
      discardTile(kept);
      return buildTile(index, slot);
    });
    for (const node of boardNodes.slice(tiles)) discardTile(node);
    boardNodes = made;
    // Only touch the host when the arrangement really changed: re-inserting a node
    // that is already in place would reset its scroll and drop the focus in it.
    const showing = [...host.children];
    if (showing.length !== made.length || made.some((node, at) => showing[at] !== node)) {
      host.replaceChildren(...made);
    }
    board.slots.forEach((index, slot) => {
      if (index == null) return;
      const view = tileSurface(made[slot], index, index === active);
      boardSurfaces[slot] = view;
      renderView(view);
    });
  }
  // One briefing card per filled tile, in slot order, each made by the same
  // description a single "Add to briefing" would make for that sheet. One
  // serializer, so a board slide and a single slide can never disagree.
  async function boardToBriefing() {
    if (!window.MentatBriefing) { failure('Briefing needs a console restart.'); return; }
    const filled = boardSurfaces.filter(Boolean);
    if (!filled.length) { failure('The board has no charts on it yet.'); return; }
    failure('');
    for (const view of filled) await window.MentatBriefing.capture(currentChart(view));
  }

  /* ---------------------------------------------------------------- sheets */

  function renderSheets() {
    el('sheet-source').setAttribute('aria-selected', String(dataSourceTab));
    el('sheet-tabs').replaceChildren(...sheets.map((state, index) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = state.name;
      button.setAttribute('aria-selected', String(!dataSourceTab && index === active));
      button.title = 'Double-click to rename this sheet';
      button.onclick = () => {
        // Selecting the sheet that is already showing changes nothing, and the
        // re-render would replace this button between the two clicks of a
        // double-click, leaving the rename to run on a detached node.
        if (!dataSourceTab && index === active) return;
        dataSourceTab = false; active = index; persist(); renderAll();
      };
      button.ondblclick = () => renameSheet(button, index);
      return button;
    }));
  }
  function renameSheet(button, index) {
    const input = document.createElement('input');
    input.type = 'text';
    input.value = sheets[index].name;
    input.setAttribute('aria-label', 'Sheet name');
    let done = false;
    const finish = keep => {
      // Enter commits and then blurs, so the name would otherwise be committed
      // twice; a detached input means the tab was replaced under us and there
      // is nothing left to put back.
      if (done || !input.isConnected) return;
      done = true;
      const name = input.value.trim();
      input.replaceWith(button);
      if (keep && name) commit(() => { sheets[index].name = name; });
    };
    input.onkeydown = event => {
      if (event.key === 'Enter') { event.preventDefault(); finish(true); }
      if (event.key === 'Escape') { event.preventDefault(); finish(false); }
    };
    input.onblur = () => finish(true);
    button.replaceWith(input);
    input.focus();
    input.select();
  }
  function nextName() {
    let n = sheets.length + 1;
    while (sheets.some(s => s.name === 'Sheet ' + n)) n++;
    return 'Sheet ' + n;
  }

  /* -------------------------------------------------------------- the view */

  function overlayLabels(svg, result) {
    const values = core.markValues(result);
    if (!values.length) return false;
    const marks = [...svg.querySelectorAll('rect,circle')].filter(node => node.querySelector(':scope > title'));
    if (marks.length !== values.length) return false;
    const sideways = ['horizontal', 'groupedhorizontal'].includes(result.type);
    marks.forEach((mark, index) => {
      const value = values[index];
      if (typeof value !== 'number' || !Number.isFinite(value)) return;
      const label = document.createElementNS(NS, 'text');
      label.textContent = compact(value);
      label.setAttribute('fill', MentatTheme.ink);
      label.setAttribute('font-family', MentatTheme.sans);
      label.setAttribute('font-size', '10');
      label.setAttribute('data-mark-label', 'true');
      if (mark.tagName === 'circle') {
        label.setAttribute('x', mark.getAttribute('cx'));
        label.setAttribute('y', Number(mark.getAttribute('cy')) - 8);
        label.setAttribute('text-anchor', 'middle');
      } else if (sideways) {
        label.setAttribute('x', Number(mark.getAttribute('x')) + Number(mark.getAttribute('width')) + 4);
        label.setAttribute('y', Number(mark.getAttribute('y')) + Number(mark.getAttribute('height')) / 2 + 3);
      } else {
        label.setAttribute('x', Number(mark.getAttribute('x')) + Number(mark.getAttribute('width')) / 2);
        label.setAttribute('y', Number(mark.getAttribute('y')) - 4);
        label.setAttribute('text-anchor', 'middle');
      }
      svg.append(label);
    });
    return true;
  }
  function overlayReference(svg, plot, lines) {
    if (!plot || !lines.length || plot.max === plot.min) return;
    for (const line of lines) {
      if (line.value < plot.min || line.value > plot.max) continue;
      const at = plot.p0 + (line.value - plot.min) / (plot.max - plot.min) * (plot.p1 - plot.p0);
      const rule = document.createElementNS(NS, 'line');
      const vertical = plot.orient === 'vertical';
      rule.setAttribute('x1', vertical ? plot.from : at);
      rule.setAttribute('x2', vertical ? plot.to : at);
      rule.setAttribute('y1', vertical ? at : plot.from);
      rule.setAttribute('y2', vertical ? at : plot.to);
      rule.setAttribute('stroke', MentatTheme.ink);
      rule.setAttribute('stroke-width', '1.5');
      rule.setAttribute('stroke-dasharray', '7 5');
      const note = document.createElementNS(NS, 'text');
      note.textContent = line.label + ' ' + compact(line.value);
      note.setAttribute('x', vertical ? plot.to : at + 4);
      note.setAttribute('y', vertical ? at - 5 : plot.from + 12);
      note.setAttribute('text-anchor', vertical ? 'end' : 'start');
      note.setAttribute('fill', MentatTheme.ink);
      note.setAttribute('font-family', MentatTheme.sans);
      note.setAttribute('font-size', '11');
      svg.append(rule, note);
    }
  }
  function overlayTotal(svg, total) {
    if (total == null) return false;
    const box = String(svg.getAttribute('viewBox') || '0 0 960 620').split(' ').map(Number);
    const note = document.createElementNS(NS, 'text');
    note.textContent = (lastConfig?.transform === 'forecast' ? 'Observed total ' : 'Grand total ') + compact(total);
    note.setAttribute('x', box[2] - 28);
    note.setAttribute('y', 88);
    note.setAttribute('text-anchor', 'end');
    note.setAttribute('fill', MentatTheme.ink);
    note.setAttribute('font-family', MentatTheme.sans);
    note.setAttribute('font-size', '12');
    note.setAttribute('font-weight', '600');
    svg.append(note);
    return true;
  }

  function renderTable(result, config, node) {
    const rows = paint.tableRows(result, config, data);
    const table = document.createElement('table');
    const head = document.createElement('thead');
    const headRow = document.createElement('tr');
    for (const cell of rows[0]) {
      const th = document.createElement('th');
      th.textContent = String(cell);
      headRow.append(th);
    }
    head.append(headRow);
    const body = document.createElement('tbody');
    for (const row of rows.slice(1, 401)) {
      const tr = document.createElement('tr');
      for (const cell of row) {
        const td = document.createElement('td');
        td.textContent = typeof cell === 'number' ? fmt(cell) : String(cell == null ? '' : cell);
        tr.append(td);
      }
      body.append(tr);
    }
    table.append(head, body);
    node('table').replaceChildren(table);
    if (rows.length > 401) {
      const note = document.createElement('p');
      note.className = 'studio-note';
      note.textContent = 'Showing the first 400 of ' + fmt(rows.length - 1) + ' rows. Download the data CSV for every value.';
      node('table').prepend(note);
    }
  }

  function renderView(view) {
    view = view || mainSurface();
    const node = view.el, state = view.state;
    if(verified()){renderContributionView(view);return;}
    if (view.primary) { lastResult = null; lastConfig = null; }
    node('reconcile').hidden = true;
    node('canvas').replaceChildren();
    node('table').replaceChildren();
    node('status').replaceChildren();
    if (!data) {
      node('title').textContent = '';
      node('subtitle').textContent = '';
      node('note').textContent = 'Choose a report worksheet in the Data panel to begin.';
      return;
    }
    const report = core.compileReport(state, columns());
    const markName = (core.MARK_TYPES.find(m => m[0] === report.markType) || ['', 'Automatic'])[1];
    // Provisional only: measureLabel reads the built result to tell an
    // aggregated view from one that plots individual values, so a box,
    // histogram or scatter title would read "· Sum" without it. The real title
    // is set again below, once math.build has produced that result.
    // The h2 never names the console (item 17): before a chart is drawn it is
     // empty, and an empty title is not rendered at all (chart-studio.css).
    node('title').textContent = report.config
      ? paint.measureLabel(report.config, null, data) + ' · ' + markName
      : '';
    node('subtitle').textContent = report.config ? scopeSubtitle(state) : '';
    if (!report.config || report.issues.length) {
      node('note').textContent = [...worksheetNotes(state),
        report.issues.join(' ') || 'Drag a field onto Columns or Rows.'].join(' ');
      node('canvas').hidden = false;
      node('table').hidden = true;
      return;
    }
    let result;
    try {
      result = math.build(data, report.config);
    } catch (e) {
      node('note').textContent = e.message;
      node('table').hidden = true;
      return;
    }
    result = core.sortResult(result, state.sort);
    if (view.primary) { lastResult = result; lastConfig = report.config; }
    const measure = paint.measureLabel(report.config, result, data);
    node('title').textContent = measure + ' · ' + markName;
    node('subtitle').textContent = scopeSubtitle(state);
    const source = state.source;
    const filterText = report.config.filters
      .map(f => (core.fieldAt(report.fields, f.column) || {name: 'field'}).name + ' ' + f.op + ' ' + f.value).join('; ');
    view.title = node('title').textContent;
    view.scope = [source.reportName + ' / ' + data.sheet,
      (result.split ? fmt(result.selected) + ' values from ' + fmt(data.row_count) + ' worksheet rows selected (' + result.split.cells + ' multi-value cells split); '
        : result.selected + ' of ' + data.row_count + ' rows selected; ') + result.excluded + ' rows excluded for missing or non-numeric values.',
      'Group/X: ' + (result.groupingLabel || (core.fieldAt(report.fields, report.config.x) || {name: 'All rows'}).name) + '.',
      ['box', 'scatter', 'histogram'].includes(result.type) ? 'Individual worksheet values.' : 'Aggregation: ' + report.config.aggregation + '.',
      'Worksheet rows: ' + (report.config.start || 'first data row') + '–' + (report.config.end || 'last data row') + '.',
      'Row count limit: ' + (report.config.limit || 'all matching rows') + ' (after filters).',
      'Filters: ' + (filterText || 'none') + '.',
      'Sort: ' + state.sort + '.',
      'Group limit: ' + report.config.maxGroups + '.',
      'Split multi-value cells: ' + (report.config.splitMulti ? 'on' : 'off') + '.',
      'SHA-256: ' + data.sha256 + '.'].join(' ');
    if (result.note) view.scope += ' ' + result.note;
    // Recipient-committee activity is not the industry's money, so a grand
    // total over it would print a figure that reads as one the report
    // reconciles to. The engine's own refusal field carries the reason into
    // totalNote(), grandTotal() and the status line at once.
    const committee = core.committeeActivitySheet(data.sheet);
    if (committee && !result.totalRefusal) result.totalRefusal = committee;
    const notes = [...worksheetNotes(state), ...report.notes];

    if (report.renderMode === 'table') {
      node('canvas').hidden = true;
      node('table').hidden = false;
      renderTable(result, report.config, node);
    } else {
      node('canvas').hidden = false;
      node('table').hidden = true;
      const drawn = paint.chartSVG(result, measure, report.config, data, view.title, view.scope);
      if (state.showLabels && !overlayLabels(drawn.svg, result)) notes.push('Mark labels are unavailable for this view.');
      const analytics = state.analytics;
      const references = core.referenceValues(result, analytics);
      if (references.length && !drawn.plot) notes.push('Reference lines need a value axis; this view has none.');
      // Say why a requested overlay is missing, but only when it was requested.
      if ((analytics.average || analytics.median) && result.series) notes.push('Reference lines need a single series.');
      overlayReference(drawn.svg, drawn.plot, references);
      if (analytics.totals) {
        const refusal = core.totalNote(result, report.config);
        // The committee-activity caption is already in the list; it is the
        // same sentence, and saying it twice reads as two reasons.
        if (refusal) { if (!notes.includes(refusal)) notes.push(refusal); }
        else if (!overlayTotal(drawn.svg, core.grandTotal(result, report.config))) {
          notes.push('A grand total is not defined for this view.');
        }
      }
      node('canvas').className = view.canvasClass + 'studio-canvas fit-' + state.fit;
      node('canvas').replaceChildren(drawn.svg);
    }
    node('note').textContent = notes.concat(result.note ? [result.note] : []).join(' ') ||
      source.reportName + ' / ' + data.sheet + ' · ' + fmt(result.selected) + ' rows selected';
    renderStatus(result, report.config, node);
  }

  function renderStatus(result, config, node) {
    const summary = core.rowsToMarksSummary(result, config, columns());
    if (!summary) return;
    const parts = [
      fmt(summary.marks) + ' mark' + (summary.marks === 1 ? '' : 's'),
      summary.viewRows + ' row' + (summary.viewRows === 1 ? '' : 's') + ' by ' + summary.viewColumns + ' column' + (summary.viewColumns === 1 ? '' : 's'),
      summary.total == null ? '' : summary.measureLabel + ': ' + fmt(summary.total)
    ].filter(Boolean);
    const nodes = parts.map(part => {
      const span = document.createElement('span');
      span.textContent = part;
      return span;
    });
    const badge = document.createElement('span');
    badge.className = 'studio-local';
    badge.textContent = 'LOCAL ONLY';
    badge.title = 'Every value is read from the local report file and drawn in this browser.';
    nodes.push(badge);
    if (parts.length > 2) nodes[2].title = 'Total of the plotted marks, each aggregated as ' + config.aggregation + '.';
    node('status').replaceChildren(...nodes);
  }

  function renderDataSource() {
    const worksheet = !dataSourceTab;
    el('grid').hidden = !worksheet;
    el('datasource').hidden = worksheet;
    if (worksheet || !data) return;
    if(verified()){renderRelationshipSource();return;}
    const meta = core.classifyFields(columns(), sheet().types);
    const source = sheet().source;
    const list = document.createElement('dl');
    const pairs = [['Report folder', source.runName], ['Report', source.reportName], ['Worksheet', data.sheet],
      ['Header row', data.header_row], ['Rows', fmt(data.row_count)], ['Columns', columns().length],
      ['Dimensions', meta.dimensions.length + ' (' + meta.hidden.length + ' identifier fields hidden)'],
      ['Measures', meta.measures.length], ['SHA-256', data.sha256], ['Note', data.note]];
    for (const [term, value] of pairs) {
      const dt = document.createElement('dt');
      dt.textContent = term;
      const dd = document.createElement('dd');
      dd.textContent = String(value == null ? '' : value);
      list.append(dt, dd);
    }
    const table = document.createElement('table');
    const head = document.createElement('thead');
    head.innerHTML = '<tr><th>Column</th><th>Detected type</th><th>Role</th><th>Distinct</th><th>Missing</th></tr>';
    const body = document.createElement('tbody');
    for (const field of meta.fields) {
      const tr = document.createElement('tr');
      for (const cell of [field.name, field.type, field.hidden ? 'hidden identifier' : field.role,
        field.distinct == null ? '' : fmt(field.distinct), field.missing == null ? '' : fmt(field.missing)]) {
        const td = document.createElement('td');
        td.textContent = String(cell);
        tr.append(td);
      }
      body.append(tr);
    }
    table.append(head, body);
    const heading = document.createElement('h3');
    heading.textContent = 'Scanned columns';
    el('datasource').replaceChildren(list, heading, table);
  }

  function renderRelationshipSource(){
    const model=dataset()?.model||contributionCatalog?.model,host=el('datasource');host.replaceChildren();
    const add=(tag,value,parent=host)=>{const n=document.createElement(tag);n.textContent=value;parent.append(n);return n;};
    add('h2','Sources, relationships and field definitions');add('p',model?.grain||'One preserved source observation. Measures aggregate at this grain.');
    add('h3','Available report sources');const sources=add('div','');sources.className='studio-source-choices';
    for(const item of contributionCatalog?.datasets||[]){const button=add('button',item.label||item.id,sources);button.type='button';button.disabled=!item.available;button.setAttribute('aria-pressed',String(item.id===dataset()?.id));button.onclick=()=>{el('dataset').value=item.id;selectContributionDataset();};}
    const worksheets=add('button','Explore every report worksheet');worksheets.type='button';worksheets.onclick=()=>{dataSourceTab=false;el('source-mode').value='worksheet';el('source-mode').dispatchEvent(new Event('change'));};
    add('p','Candidate funding, committee spending, coverage and evidence sheets have their own rows and measures. Select a worksheet to inspect its complete scanned field list. Alternative summary tables are never automatically added to receipt facts.');
    if(model){add('h3','Logical tables');const cards=add('div','');cards.className='studio-model-tables';
      for(const table of model.tables){const card=add('section','',cards);add('h4',table.name,card);add('p',table.grain,card);add('small','Key: '+table.key+' · '+table.source,card);}
      add('h3','Relationships');for(const r of model.relationships){const p=add('p','');add('strong',r.from+' → '+r.to,p);add('span',' · '+r.cardinality+' · '+r.matching+'. '+r.behavior,p);}
      add('p',model.notes.join(' '));add('h3','Date and geography levels');for(const [name,levels]of Object.entries(model.hierarchies))add('p',name+': '+levels.map(id=>columns().find(f=>f.id===id)?.name||id).join(' → '));
    }
    add('h3','Complete analytical field catalog');const table=add('table',''),thead=add('thead','',table),tr=add('tr','',thead);for(const title of ['Field','Logical table','Data type','Role','Interpretation','Use'])add('th',title,tr);const body=add('tbody','',table);
    for(const field of columns()){const row=add('tr','',body);for(const value of [field.name,field.table||'Observation',field.data_type||field.type,field.role+(field.discrete?' · discrete':' · continuous'),field.description||''])add('td',value,row);const cell=add('td','',row),button=add('button',field.role==='measure'?'Add to Rows':'Add to Columns',cell);button.type='button';button.onclick=()=>{dataSourceTab=false;commit(()=>place(field.role==='measure'?'rows':'columns',field.index));};}
    add('h3','Tableau references');for(const [name,url]of [['Relationships preserve table grain','https://help.tableau.com/current/pro/desktop/en-us/relate_tables.htm'],['Data types and mixed values','https://help.tableau.com/current/pro/desktop/en-us/datafields_typesandroles_datatypes.htm'],['Dimensions, measures, discrete and continuous fields','https://help.tableau.com/current/pro/desktop/en-us/datafields_typesandroles.htm']]){const p=add('p',''),a=add('a',name,p);a.href=url;a.target='_blank';a.rel='noopener noreferrer';}
  }

  // Sort is switched off for a time view: chronological order is the meaning of
  // the axis, and core.sortResult refuses to reorder one, so a pressed-looking
  // button would promise something the view never does.
  const SORT_BUTTONS = [['sort-asc', 'asc', 'Sort the grouping smallest first'],
    ['sort-desc', 'desc', 'Sort the grouping largest first']];
  // The labels button's own markup title is its hint. It is cached on first
  // read, before a lock reason overwrites it, rather than restated here.
  let labelsHint = null;
  const labelHint = () => labelsHint === null ? (labelsHint = el('labels').title) : labelsHint;
  // The query the verified path will actually send. The CLASSIC compile does
  // not know combination, dual-line or histogram, so asking it whether Sort
  // applies left two enabled buttons on exactly those three marks - and they
  // did nothing. Shelves the compile refuses have no answer to give: the
  // canvas already names that error, so the toolbar leaves the buttons alone.
  function verifiedCompile() {
    if (!verified() || !data || !dataset()) return null;
    try {
      return contributions.compile(sheet(), columns(),
        {dataset: dataset().id, industry: dataset().industry, basis: basis(), offset: 0});
    } catch (error) { return null; }
  }
  // The sort reads measures[0] only, so the button says which measure that is.
  function sortedMeasureName(compiled) {
    const id = compiled && compiled.spec.measures[0];
    if (!id) return '';
    return (columns().find(f => f.id === id) || {}).name || id;
  }
  function renderSortButtons(view) {
    const compiled = verifiedCompile();
    // On the verified path 'none' means descending (contributions
    // .effectiveSort), so 'Sort descending' is pressed from the moment a sheet
    // opens rather than being a button that reproduces the same query.
    const onVerified = verified() && !!compiled;
    const locked = onVerified
      ? contributions.sortLock(compiled.spec.type, sheet())
      : (core.sortLocked(view) ? 'Time views keep chronological order' : '');
    const pressed = onVerified ? contributions.effectiveSort(sheet()) : sheet().sort;
    const measure = onVerified ? sortedMeasureName(compiled) : '';
    for (const [id, direction, hint] of SORT_BUTTONS) {
      el(id).disabled = !!locked;
      el(id).title = locked || (measure
        ? 'Sort by ' + measure + ', ' + (direction === 'asc' ? 'smallest first' : 'largest first')
        : hint);
      el(id).setAttribute('aria-pressed', String(!locked && pressed === direction));
    }
  }
  // Labels are render-only, so this changes no query: it only stops the button
  // claiming a toggle on a mark whose renderer never reads spec.labels. The
  // stored showLabels is left exactly as it was, so it returns when the reader
  // goes back to a mark that draws them.
  function renderLabelButton(state) {
    const compiled = verifiedCompile();
    const locked = verified() && compiled
      ? contributions.labelLock(compiled.spec.type, compiled.transform) : '';
    el('labels').disabled = !!locked;
    el('labels').title = locked || labelHint();
    el('labels').setAttribute('aria-pressed', String(!locked && !!state.showLabels));
  }

  // The classic dialog picks the first subject by itself, so the studio settles
  // on one too. That is a derived default, not a user edit: it is written
  // straight to the sheet with no commit, so it costs no undo step.
  function defaultSubject(state, field) {
    const list = members(field.index);
    if (!list.includes(String(state.params.subject || ''))) state.params.subject = list[0] || '';
    return list;
  }

  // Time analysis adds one subject's periods together and the engine refuses a
  // worksheet holding several, so the studio offers the same Subject choice the
  // classic dialog does. The control appears only where that column exists.
  function renderSubjectParam() {
    const field = data ? core.subjectField(core.classifyFields(columns(), sheet().types).fields) : null;
    el('param-subject-label').hidden = !field;
    if (!field) return;
    const list = defaultSubject(sheet(), field);
    fill(el('param-subject'), list.length ? list.map(m => [m, m]) : [['', 'Choose a subject…']]);
    el('param-subject').value = String(sheet().params.subject || '');
  }

  function renderToolbar() {
    const state = sheet();
    el('undo').disabled = !history.length;
    el('redo').disabled = !future.length;
    renderSortButtons(data ? core.compileReport(state, columns()).config : null);
    renderLabelButton(state);
    el('fit').value = state.fit;
    el('showme-toggle').setAttribute('aria-pressed', String(!!el('showme-details').open));
    for (const tiles of BOARD_TILES) {
      el('board-' + tiles).setAttribute('aria-pressed', String((board ? board.tiles : 1) === tiles));
    }
    el('param-start').value = state.params.start || '';
    el('param-end').value = state.params.end || '';
    el('param-limit').value = state.params.limit || '';
    el('param-groups').value = state.params.maxGroups || '';
    el('param-split').checked = !!state.params.splitMulti;
    el('param-horizon').value = state.analytics.horizon || 2;
    el('param-period').value = state.analytics.period || '';
    renderSubjectParam();
  }

  function renderAll() {
    settleBoard();
    syncContributionControls();
    renderToolbar();
    renderFields();
    renderShelves();
    renderAnalytics();
    renderShowMe();
    renderSheets();
    renderDataSource();
    renderScopeChip();
    renderDatasetMessage();
    renderSourceSummary();
    renderFilterRows();
    renderOverviewControls();
    renderBoard();
    if (overviewMode) renderOverview();
    else if (!dataSourceTab && boardTiles() < 2) renderView();
  }

  /* ------------------------------------------------------------- downloads */

  function download(format) {
    if(verified()){downloadContributions(format);return;}
    if (!lastResult) { failure('Build a view before downloading.'); return; }
    failure('');
    // Everything a download carries comes off the surface the reader is looking
    // at: its drawing, its title and the scope line that names its page.
    const view = activeSurface();
    if (format === 'csv') {
      const quote = v => '"' + String(typeof v === 'string' && /^[=+\-@\t\r]/.test(v) ? "'" + v : v).replaceAll('"', '""') + '"';
      const rows = [['Chart', view.title], ['Scope', view.scope], ['Note', view.el('note').textContent],
        ...paint.tableRows(lastResult, lastConfig, data)];
      MentatExport.download('\uFEFF' + rows.map(r => r.map(quote).join(',')).join('\r\n'),
        'text/csv;charset=utf-8', 'mentat-chart-studio.csv');
      return;
    }
    const svg = view.el('canvas').firstChild;
    if (!svg) { failure('This view has no image to export. Download the data CSV instead.'); return; }
    MentatExport.image(svg, format, view.title, view.scope, 'mentat-chart-studio').catch(e => failure(e.message));
  }

  // Everything that takes a chart out of this console needs the same account
  // of it. One reader of the live view, so a download, a clipboard image, a
  // print sheet and a slide can never disagree about what they are showing.
  function currentChart(view) {
    view = view || activeSurface();
    const state = view.state, source = state.source || {};
    const basisLabel = verified()
      ? (contributions.BASIS[basisOf(state)] || [])[0] || ''
      : 'Worksheet values';
    // Both of these leave the console: into the briefing the server stores,
    // and from there into every slide's speaker notes. The server keeps each
    // one as an object and replaces anything else with an empty one, so
    // sending a caption here threw the workbook digest away and left the
    // exports printing "[object Obje" where a SHA-256 belongs. Send the
    // objects, and keep the captions beside them for the print sheet, which
    // has one line and no room for either.
    const sourceLabel = source.reportName || '';
    const sha = source.sha256 || (data && data.sha256) || '';
    return {
      svg: view.el('canvas').querySelector('svg'),
      title: view.title || view.el('title').textContent || 'Chart Studio',
      scope: view.scope || scopeText() || '',
      chip: scopeText(),
      note: view.el('note').textContent || '',
      basis: basisLabel,
      sheetId: state.id,
      sheetName: state.name,
      source: core.chartSourceRecord(source),
      provenance: core.chartProvenanceRecord(source, sha),
      sourceLabel: sourceLabel,
      sha: sha
    };
  }

  // The clipboard gets the same drawing the download would write, caption and
  // all: an image pasted into a message has to carry its own scope.
  async function copyImage() {
    const chart = currentChart();
    if (!chart.svg) { failure('No image to copy. Export the CSV instead.'); return; }
    failure('');
    try {
      const size = await MentatExport.copy(chart.svg, chart.title, chart.scope);
      status('Copied image.');
    } catch (error) { failure(error.message); }
  }

  // A printed sheet is still on a desk long after this window is closed, so
  // it states its own title, scope, basis, workbook hash and date instead of
  // relying on whoever printed it to remember them.
  function printChart() {
    const chart = currentChart();
    if (!chart.svg) { failure('No image to print. Export the CSV instead.'); return; }
    failure('');
    el('print-title').textContent = chart.title;
    el('print-scope').textContent = [chart.scope, chart.note].filter(Boolean).join(' \u00b7 ');
    el('print-source').textContent = [chart.basis,
      chart.sourceLabel ? 'Source ' + chart.sourceLabel : '',
      chart.sha ? 'Workbook SHA-256 ' + chart.sha : '',
      'Printed ' + new Date().toLocaleDateString('en-US', {year: 'numeric', month: 'long', day: 'numeric'})]
      .filter(Boolean).join(' \u00b7 ');
    document.body.classList.add('studio-printing');
    const done = () => {
      document.body.classList.remove('studio-printing');
      window.removeEventListener('afterprint', done);
      clearTimeout(timer);
    };
    // A dialog dismissed in a way that never fires afterprint must not leave
    // the console wearing its print skin.
    const timer = setTimeout(done, 60000);
    window.addEventListener('afterprint', done);
    window.print();
  }

  /* ---------------------------------------------------------- saved views */

  // Views the server refused to keep still open in this tab, so a read-only
  // preview is a console that cannot persist, not one that cannot work.
  const VIEW_MIGRATION = 'mentat-chart-studio-migrated-v1';
  let viewsMemory = [];
  const previewReadOnly = () => { try { return !!readOnly; } catch { return false; } };
  function viewMessage(error) {
    if (previewReadOnly()) return 'Read-only preview. Save views from the main console.';
    const text = String((error && error.message) || '');
    if (!text || /JSON|Unexpected token|Failed to fetch|NetworkError|<!DOCTYPE/i.test(text)) return 'Server unavailable.';
    return text;
  }
  async function getJSON(path) {
    const response = await fetch(path, {credentials: 'same-origin'});
    let body = null;
    try { body = await response.json(); } catch { body = null; }
    if (!response.ok) throw new Error((body && body.error) || 'Server unavailable (' + response.status + ').');
    return body || {};
  }
  const viewSourceLabel = () => {
    if (verified()) { const chosen = dataset(); return chosen ? (chosen.label || chosen.id) : ''; }
    return (sheet().source || {}).reportName || '';
  };

  // A saved view carries the source it was built from, and the server keeps
  // that as an object: a view reopened next year has to name the report, its
  // digest and the folder it came from, not just the words that happened to be
  // on screen. Sending the caption alone was refused outright with 400. The
  // shaping lives in chart-studio-core.js so the payload this console puts on
  // the wire is the payload a test can read, and every caller goes through it.
  const viewSourceRecord = () => core.viewSourceRecord(sheet().source, verified() ? dataset() : null);
  // Views kept in this tab by an older build, and any view a future build
  // shapes differently, still have to print something.
  const viewSourceText = view => core.sourceLabelOf(view && view.source);
  const defaultViewName = () => [sheet().name, viewSourceLabel()].filter(Boolean).join(' \u00b7 ');
  function storeKeyLabel(key) {
    const parts = String(key || '').split('|');
    if (parts[0] === 'contributions') {
      const entry = ((contributionCatalog && contributionCatalog.datasets) || []).find(d => d.id === parts[1]);
      return entry ? (entry.label || entry.id) : (parts[1] || key);
    }
    return parts.filter(Boolean).pop() || 'worksheet';
  }
  const viewLabel = view => [view.name,
    view.sheet_count ? view.sheet_count + ' sheet' + (view.sheet_count === 1 ? '' : 's') : '',
    view.saved_at ? new Date(typeof view.saved_at === 'number'
      ? view.saved_at * 1000 : view.saved_at).toLocaleString() : '',
    view.memory ? 'this tab only' : ''].filter(Boolean).join(' \u00b7 ');

  // The name is typed in place of the menu entry, the way a sheet is renamed,
  // so naming a view never moves the reader out of the menu they opened.
  function saveView() {
    const button = el('save-view');
    if (!button || !button.isConnected) return;
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'studio-view-name';
    input.value = defaultViewName();
    input.setAttribute('aria-label', 'View name');
    let done = false;
    const finish = keep => {
      if (done || !input.isConnected) return;
      done = true;
      const name = input.value.trim().slice(0, 80);
      input.replaceWith(button);
      if (keep && name) saveViewNamed(name);
    };
    input.onkeydown = event => {
      if (event.key === 'Enter') { event.preventDefault(); finish(true); }
      if (event.key === 'Escape') { event.preventDefault(); finish(false); }
    };
    input.onblur = () => finish(true);
    button.replaceWith(input);
    input.focus();
    input.select();
  }
  async function saveViewNamed(name) {
    const record = {name, sourceKey, source: viewSourceRecord(),
      sheets: JSON.parse(JSON.stringify(sheets)), active};
    // Written only for a board of 2 or 4 tiles, so a view saved on the single
    // canvas is the payload it has always been (studio_api.json v2).
    const shape = core.normalizeBoard({sheets: sheets, board: board});
    if (shape && shape.tiles > 1) record.board = shape;
    failure('');
    try {
      const body = await api('/api/studio/views', record);
      rememberSavedView(body && body.id);
      status('Saved view "' + name + '" \u00b7 ' + record.sheets.length +
        ' sheet' + (record.sheets.length === 1 ? '' : 's') + '.');
      return body;
    } catch (error) {
      viewsMemory.unshift(Object.assign({}, record, {id: 'memory-' + Date.now(),
        saved_at: new Date().toISOString(), sheet_count: record.sheets.length, memory: true}));
      failure(viewMessage(error) + ' "' + name + '" stays in this tab.');
      return null;
    }
  }

  // What a view needs before it can be opened here, said before the click
  // rather than after it.
  function openability(view) {
    if (view.sourceKey === sourceKey) return {ok: true};
    const parts = String(view.sourceKey || '').split('|');
    if (parts[0] !== 'contributions') return {ok: false,
      reason: 'Open ' +
        (viewSourceText(view) || 'that report') + ' in the Data panel first. This view was saved there.'};
    if (!verified()) return {ok: false, reason: 'Switch to Verified contributions to open this view.'};
    const entry = ((contributionCatalog && contributionCatalog.datasets) || []).find(d => d.id === parts[1]);
    if (!entry) return {ok: false, reason: 'This console has no report called ' + parts[1] + '.'};
    if (!entry.available) return {ok: false, reason: entry.message || 'That report is unavailable on this console.'};
    // A view whose sheets fan out across more than one industry (S4_DESIGN.md
    // section 4, sheet.sources[]) names every industry it needs at the view
    // level too, so opening it can be refused up front rather than partway
    // through a sheet that turns out to name an unregistered or unavailable
    // report.
    if (Array.isArray(view.industries)) {
      const datasets = (contributionCatalog && contributionCatalog.datasets) || [];
      for (const label of view.industries) {
        const match = datasets.find(d => d.industry === label || d.id === label);
        if (!match) return {ok: false, reason: 'This console has no report called ' + label + '.'};
        if (!match.available) return {ok: false, reason: match.message || 'That report is unavailable on this console.'};
      }
    }
    return {ok: true, dataset: parts[1]};
  }
  async function openView(view) {
    failure('');
    const state = openability(view);
    if (!state.ok) { failure(state.reason); return; }
    let full = view;
    if (!Array.isArray(full.sheets)) {
      try { full = (await getJSON('/api/studio/views?id=' + encodeURIComponent(view.id))).view; }
      catch (error) { failure(viewMessage(error)); return; }
    }
    if (!full || !Array.isArray(full.sheets) || !full.sheets.length) { failure('That saved view has no sheets in it.'); return; }
    // Another dataset is selected first, exactly as the Data panel would, so
    // the shelves land on the fields that view was built against.
    if (state.dataset && state.dataset !== (dataset() || {}).id) {
      el('dataset').value = state.dataset;
      selectContributionDataset();
    }
    holdingSavedId = true;
    try {
      commit(() => {
        sheets = full.sheets.map(s => core.migrateSheet(Object.assign(core.createSheet(s.name, s.id), s)));
        active = Math.min(Math.max(0, full.active | 0), sheets.length - 1);
        // A view without a board opens as one sheet, exactly as before. A board
        // that does not describe its own sheets is dropped with a word about it,
        // because failing the whole open over a layout would lose the sheets too.
        const opened = core.normalizeBoard(full);
        board = opened && opened.tiles > 1 ? opened : null;
        if (board) { syncBoardSelection(); if (!canvasOnly()) setOptionsHidden(true); }
        dataSourceTab = false;
      });
    } finally { holdingSavedId = false; }
    rememberSavedView(full.id);
    status('Opened view "' + full.name + '".'
      + (full.board && !board ? ' Its board did not match its sheets, so it opened as one sheet.' : ''));
  }

  // The views that lived in this browser before the server had a place for
  // them are offered back once, under their own names, rather than left to
  // rot behind a feature that replaced them.
  async function migrateStoredViews() {
    let migrated = true;
    try { migrated = localStorage.getItem(VIEW_MIGRATION) === '1'; } catch { migrated = true; }
    if (migrated || previewReadOnly()) return [];
    const store = readStore();
    const saved = [];
    for (const key of Object.keys(store)) {
      const entry = store[key];
      if (!entry || !Array.isArray(entry.sheets) || !entry.sheets.length) continue;
      const label = storeKeyLabel(key);
      const name = ('Recovered \u00b7 ' + label + ' \u00b7 ' + entry.sheets.length +
        ' sheet' + (entry.sheets.length === 1 ? '' : 's')).slice(0, 80);
      // The old store never recorded anything but the key, so the key itself
      // is all there is to carry - as an object, because a bare string is
      // refused. A contributions key still carries its dataset (the dataset
      // id IS the industry label), so captionSourceForKey recovers industry
      // and dataset here instead of losing them the way a bare caption did.
      const source = core.captionSourceForKey(key);
      try {
        const body = await api('/api/studio/views',
          {name, sourceKey: key, source, sheets: entry.sheets, active: entry.active | 0});
        saved.push({id: body.id, saved_at: body.saved_at, name, sourceKey: key,
          source, sheet_count: entry.sheets.length});
      } catch (error) {
        // Returning quietly here left the reader believing their old views had
        // been recovered when the console had refused every one of them, and
        // the migration flag below was never set so it silently retried for ever.
        failure(viewMessage(error) + ' Browser-saved views were not moved to this console.');
        return saved;
      }
    }
    try { localStorage.setItem(VIEW_MIGRATION, '1'); } catch {}
    return saved;
  }

  async function openViews() {
    const anchor = el('open-views');
    failure('');
    let views = [], notice = '';
    try { views = (await getJSON('/api/studio/views')).views || []; }
    catch (error) { notice = viewMessage(error); }
    if (!notice && !views.length) views = await migrateStoredViews();
    const all = [...views, ...viewsMemory.filter(saved => !views.some(v => v.id === saved.id))];
    const here = all.filter(view => view.sourceKey === sourceKey);
    const others = all.filter(view => view.sourceKey !== sourceKey);
    const items = [];
    if (notice) items.push([notice, null, {disabled: true, reason: notice}]);
    items.push(['This source', null, {group: true}]);
    if (here.length) for (const view of here) items.push([viewLabel(view), () => openView(view)]);
    else items.push(['No saved views for this source yet', null,
      {disabled: true, reason: 'Save one with Export \u203a Save view.'}]);
    items.push(['Other sources', null, {group: true}]);
    if (others.length) for (const view of others) {
      const state = openability(view);
      const sourceText = viewSourceText(view);
      items.push([viewLabel(view) + (sourceText ? ' \u00b7 ' + sourceText : ''),
        state.ok ? () => openView(view) : null,
        state.ok ? {} : {disabled: true, reason: state.reason}]);
    }
    else items.push(['None', null, {disabled: true, reason: 'Views saved on other reports appear here.'}]);
    popup(anchor, items);
  }

  /* --------------------------------------------------------------- filters */

  // The filter pill's editor: a searchable member checklist for dimensions, a
  // pair of bounds for numbers and dates, and the verified engine's stage
  // choice. Apply goes through commit(), so a filter edit is one undo step.
  function filterEditor(anchor, position) {
    const stored = sheet().filters[position];
    if (!stored) return;
    const filter = core.normalizeFilter(stored);
    const field = fieldOf(filter.column);
    if (!field) return;
    const menu = popup(anchor, []);
    const form = document.createElement('div');
    form.className = 'studio-filter-editor';
    const head = document.createElement('div');
    head.className = 'studio-filter-head';
    const title = document.createElement('strong');
    title.textContent = field.name;
    head.append(title);
    const numeric = field.role === 'measure';
    const dated = !numeric && (field.type === 'date' || field.unit === 'date');
    const choices = numeric
      ? [['between', 'Between'], ['gte', 'At least'], ['lte', 'At most'], ['equals', 'Equals']]
      : dated ? [['between', 'Between'], ['equals', 'Equals']]
      : [['in', 'Is one of'], ['notin', 'Is not one of'], ['equals', 'Equals'], ['contains', 'Contains']];
    const operator = document.createElement('select');
    operator.setAttribute('aria-label', 'Filter operation');
    for (const [id, label] of choices) operator.append(new Option(label, id));
    operator.value = choices.some(choice => choice[0] === filter.op) ? filter.op : choices[0][0];
    let stage = null;
    if (verified()) {
      stage = document.createElement('select');
      stage.setAttribute('aria-label', 'Filter stage');
      if (field.role === 'dimension' || field.id === 'amount') stage.append(new Option('Source records, before grouping', 'rows'));
      if (field.role === 'measure') stage.append(new Option('Grouped values, after aggregation', 'aggregate'));
      stage.value = stored.stage || (field.role === 'measure' && field.id !== 'amount' ? 'aggregate' : 'rows');
    }
    const body = document.createElement('div');
    const hint = document.createElement('small');
    hint.textContent = verified()
      ? (numeric ? 'Money is entered in USD; counts are whole observations.'
        : 'Exact text preserves identifiers such as leading-zero ZIPs.')
      : 'Worksheet filters apply to source rows before aggregation.';
    let read = () => ({op: operator.value, value: ''});
    let poll = 0;
    const stopPoll = () => { if (poll) { clearInterval(poll); poll = 0; } };

    function drawScalar(count) {
      const inputs = [];
      for (let i = 0; i < count; i++) {
        const input = document.createElement('input');
        input.type = dated ? 'date' : numeric ? 'number' : 'text';
        input.setAttribute('aria-label', count === 1 ? 'Filter value' : i ? 'Upper bound' : 'Lower bound');
        if (count === 2) input.placeholder = i ? 'Up to' : 'From';
        inputs.push(input);
      }
      const bounds = core.filterBounds(filter);
      if (count === 2) inputs.forEach((input, i) => { input.value = filter.op === 'between' ? bounds[i] : ''; });
      else inputs[0].value = Array.isArray(filter.value) ? '' : filter.value;
      body.replaceChildren(...inputs);
      read = () => ({op: operator.value,
        value: count === 2 ? [inputs[0].value.trim(), inputs[1].value.trim()] : inputs[0].value.trim()});
      inputs[0].focus();
    }

    function drawList() {
      const chosen = new Set(core.filterValues(filter));
      const search = document.createElement('input');
      search.type = 'search';
      search.placeholder = 'Search values';
      search.setAttribute('aria-label', 'Search values');
      const links = document.createElement('div');
      links.className = 'studio-filter-links-row';
      const all = document.createElement('button');
      all.type = 'button';
      all.textContent = 'All';
      const none = document.createElement('button');
      none.type = 'button';
      none.textContent = 'None';
      links.append(all, none);
      const list = document.createElement('div');
      list.className = 'studio-filter-members';
      body.replaceChildren(search, links, list);
      const paint = () => {
        const available = members(field.index);
        const query = search.value.trim().toLowerCase();
        const shown = available.filter(value => !query || value.toLowerCase().includes(query)).slice(0, 400);
        list.replaceChildren();
        if (!available.length) {
          const note = document.createElement('p');
          note.textContent = verified() ? 'Reading the values of this field\u2026' : 'This column has no values.';
          list.append(note);
        }
        for (const value of shown) {
          const row = document.createElement('label');
          const box = document.createElement('input');
          box.type = 'checkbox';
          box.checked = chosen.has(value);
          box.onchange = () => { if (box.checked) chosen.add(value); else chosen.delete(value); };
          row.append(box, document.createTextNode(value === '' ? '(blank)' : value));
          list.append(row);
        }
        if (available.length > shown.length) {
          const note = document.createElement('p');
          note.textContent = (available.length - shown.length) + ' more values \u2014 narrow the search.';
          list.append(note);
        }
        return available.length;
      };
      search.oninput = paint;
      all.onclick = () => { for (const value of members(field.index)) chosen.add(value); paint(); };
      none.onclick = () => { chosen.clear(); paint(); };
      // members() memoises its facet query, so polling for the answer costs no
      // extra request; the negative cache stops a failed facet from re-firing.
      if (!paint() && verified()) {
        poll = setInterval(() => { if (!menu.isConnected || paint()) stopPoll(); }, 400);
        setTimeout(stopPoll, 20000);
      }
      read = () => ({op: operator.value, value: [...chosen]});
      search.focus();
    }

    const draw = () => {
      stopPoll();
      const op = operator.value;
      if (op === 'in' || op === 'notin') drawList(); else drawScalar(op === 'between' ? 2 : 1);
    };
    operator.onchange = draw;
    const actions = document.createElement('div');
    actions.className = 'studio-editor-actions';
    const apply = document.createElement('button');
    apply.type = 'button';
    apply.className = 'is-primary';
    apply.textContent = 'Apply';
    apply.onclick = () => {
      const next = read();
      stopPoll();
      menu.remove();
      commit(() => {
        sheet().filters[position] = core.normalizeFilter(Object.assign({column: Number(filter.column)}, next,
          stage ? {stage: stage.value} : {}));
      });
    };
    const cancel = document.createElement('button');
    cancel.type = 'button';
    cancel.textContent = 'Cancel';
    cancel.onclick = () => { stopPoll(); menu.remove(); if (anchor.isConnected) anchor.focus(); };
    const remove = document.createElement('button');
    remove.type = 'button';
    remove.textContent = 'Remove';
    remove.onclick = () => { stopPoll(); menu.remove(); commit(() => removeFrom('filters', position)); };
    actions.append(apply, cancel, remove);
    form.append(head, operator, body);
    if (stage) form.append(stage);
    form.append(hint, actions);
    menu.append(form);
    draw();
  }

  // The Inspector's Filters tab and the Filters shelf are the same filters.
  function renderFilterRows() {
    const meta = core.classifyFields(columns(), sheet().types);
    const rows = (sheet().filters || []).map((filter, position) => {
      const field = core.fieldAt(meta, Number(filter.column));
      if (!field) return null;
      const row = document.createElement('div');
      row.className = 'studio-filter-row';
      const name = document.createElement('strong');
      name.textContent = field.name;
      const summary = document.createElement('span');
      summary.textContent = core.filterSummary(filter, field, memberTotal(field.index));
      const actions = document.createElement('div');
      actions.className = 'studio-editor-actions';
      const edit = document.createElement('button');
      edit.type = 'button';
      edit.textContent = 'Edit';
      edit.onclick = () => filterEditor(edit, position);
      const drop = document.createElement('button');
      drop.type = 'button';
      drop.textContent = 'Remove';
      drop.onclick = () => commit(() => removeFrom('filters', position));
      actions.append(edit, drop);
      row.append(name, summary, actions);
      return row;
    }).filter(Boolean);
    el('filter-rows').replaceChildren(...rows);
    const used = new Set((sheet().filters || []).map(f => Number(f.column)));
    fill(el('filter-add'), [['', 'Add a field\u2026'],
      ...meta.dimensions.concat(meta.measures).filter(f => !used.has(f.index)).map(f => [String(f.index), f.name])]);
    el('tab-filters').textContent = rows.length ? 'Filters (' + rows.length + ')' : 'Filters';
    // Below 1200px the Inspector is behind a button, so the number of filters
    // shaping this view has to be readable without opening it.
    const badge = el('inspector-count');
    badge.textContent = rows.length ? String(rows.length) : '';
    badge.hidden = !rows.length;
    el('inspector-toggle').setAttribute('aria-label', rows.length
      ? 'Inspector · ' + rows.length + ' active filter' + (rows.length === 1 ? '' : 's')
      : 'Inspector');
  }

  // The scope chip states the industry, cycle and company this view is reading,
  // and says when that scope arrived from the Graph tab.
  function scopeText() {
    if (!data) return '';
    if (!verified()) {
      const source = sheet().source;
      return [source.reportName, data.sheet].filter(Boolean).join(' \u00b7 ');
    }
    const meta = core.classifyFields(columns(), sheet().types);
    const valueOf = id => {
      const field = meta.fields.find(f => f.id === id);
      if (!field) return '';
      const filter = (sheet().filters || []).find(f => Number(f.column) === field.index);
      if (!filter || !core.filterActive(filter)) return '';
      const values = core.filterValues(filter);
      return values.length === 1 ? values[0] : values.length ? values.length + ' selected' : '';
    };
    const carried = !!(appliedScope && appliedScope.carried);
    const company = valueOf('company');
    const parts = [(dataset() || {}).label || (dataset() || {}).id || '', valueOf('cycle') || 'All cycles'];
    if (carried || company) parts.push(company || 'All companies');
    return (carried ? 'Carried from Graph \u00b7 ' : '') + parts.filter(Boolean).join(' \u00b7 ');
  }
  /* ------------------------------------------------------- reconciliation */

  // The Graph controls that have no verified field. They are read at the
  // moment of the comparison, because they decide which question Graph was
  // asked, and therefore which difference has to be explained.
  const graphFilterState = () => ({
    tier: (document.getElementById('graph-tier') || {}).value || '',
    funding: (document.getElementById('graph-funding') || {}).value || 'all'
  });

  // The same question, asked of Graph. One request per scope, remembered for
  // the session, because the strip is redrawn on every display edit and a
  // reconciliation must never cost a query the reader did not ask for.
  const graphTotalsCache = new Map();
  // The strip is often the first thing a reader opens, on a console where the
  // Graph view has never rendered and #graph-run is therefore still empty - and
  // an empty select made every reconciliation refuse itself. It cannot guess a
  // run either: reconciling against a run Graph would not display is worse than
  // no strip at all. So it calls the very chooser Graph calls, which prefers the
  // selected run, skips runs that are only ready or awaiting review, and walks
  // on past any run whose catalog has no industries.
  let graphRunPromise = null;
  function graphRunId() {
    const chosen = (document.getElementById('graph-run') || {}).value || '';
    if (chosen) return Promise.resolve(chosen);
    const chooser = globalThis.MentatGraphRun;
    if (!chooser) return Promise.resolve('');
    if (!graphRunPromise) {
      graphRunPromise = chooser.choose()
        .then(result => {
          // Only a run Graph would actually display counts, and only a real
          // answer is worth remembering: caching '' would leave the strip dead
          // for the rest of the session over one bad moment.
          const id = (result && result.catalog && result.run) ? result.run.id : '';
          if (!id) graphRunPromise = null;
          return id;
        })
        .catch(() => { graphRunPromise = null; return ''; });
    }
    return graphRunPromise;
  }
  async function graphTotals(company, cycle) {
    const run = await graphRunId();
    const industry = (dataset() || {}).id || '';
    if (!run || !industry) return Promise.reject(new Error('Graph has no run selected.'));
    const chosen = graphFilterState();
    const params = new URLSearchParams({id: run, industry: industry, company: company || '',
      tier: chosen.tier, cycle: core.graphCycleValue(cycle), funding: chosen.funding,
      mode: 'direct', direction: '', category: '', recipient: ''});
    // Graph's own first paint asks for latest=1, and the server answers it by
    // pinning the newest cycle it holds. A sheet that carries no cycle of its own
    // has to ask that same question, or the strip quotes a figure covering every
    // cycle at once and calls it what Graph is showing on screen.
    if (!core.graphCycleValue(cycle)) params.set('latest', '1');
    const key = params.toString();
    if (graphTotalsCache.has(key)) return graphTotalsCache.get(key);
    const promise = Promise.resolve(api('/api/graph?' + params))
      .catch(error => { graphTotalsCache.delete(key); throw error; });
    graphTotalsCache.set(key, promise);
    return promise;
  }

  // The strip only means anything when both views were asked the same
  // question, so it fires for a sheet whose row filters are a company, a
  // cycle, or both - each one exact single value - and nothing else.
  function reconcileScope(state) {
    const meta = core.classifyFields(columns(), state.types);
    const scope = {company: '', cycle: ''};
    for (const filter of state.filters || []) {
      if (!core.filterActive(filter)) continue;
      const field = meta.fields.find(f => f.index === Number(filter.column));
      const id = field ? field.id : '';
      const values = core.filterValues(filter);
      if ((id !== 'company' && id !== 'cycle') || filter.stage === 'aggregate' ||
          ['equals', 'in'].indexOf(filter.op) === -1 || values.length !== 1 || scope[id]) return null;
      scope[id] = values[0];
    }
    return scope;
  }

  // A Graph request that fails, or a scope Graph cannot express, leaves the
  // strip away entirely. An absent strip is honest; a guessed one is not.
  async function renderReconcile(result, view, ticket) {
    view = view || mainSurface();
    const node = view.el('reconcile');
    node.hidden = true;
    if (!verified() || !result) return;
    const scope = reconcileScope(view.state);
    if (!scope) return;
    let graphView;
    try { graphView = await graphTotals(scope.company, scope.cycle); }
    catch { return; }
    if (view.stale(ticket) || !verified()) return;
    // Whatever cycle Graph pinned is the cycle this sentence has to name. Saying
    // "All cycles" while Graph displays one was the strip describing a screen
    // nobody was looking at.
    const graphCycle = String(((graphView || {}).filters || {}).cycle || '');
    const state = contributions.reconcile(result, basisOf(view.state), graphView,
      Object.assign({}, graphFilterState(), {studioCycle: scope.cycle, graphCycle: graphCycle}));
    if (state.reasonId === 'unavailable') return;
    const money = value => contributionPlot.format(value, 'amount');
    const where = [scope.company || 'All companies',
      scope.cycle || graphCycle || 'All cycles'].join(' · ');
    const lead = document.createElement('span');
    lead.textContent = 'Graph shows ' + money(state.graphCents) + ' for ' + where +
      '. Studio shows ' + money(state.studioCents) + '. ';
    const verdict = document.createElement('strong');
    verdict.className = state.agree ? 'studio-reconcile-agree' : 'studio-reconcile-differ';
    verdict.textContent = state.agree ? 'Agree.'
      : 'They differ by ' + money(Math.abs(state.differenceCents)) + ' because ' + state.reason + '.';
    const link = document.createElement('button');
    link.type = 'button';
    link.className = 'studio-reconcile-link';
    link.textContent = 'Why Cross-reference differs';
    link.onclick = () => {
      if (typeof showView === 'function') showView('cross-reference');
      else location.hash = '#cross-reference';
    };
    node.replaceChildren(lead, verdict, document.createTextNode(' '), link);
    node.hidden = false;
  }

  function renderScopeChip() {
    // The Data source button is permanent. The one way back to the report
    // picker must never depend on there being a scope to describe.
    const host = el('scope-chip');
    host.replaceChildren();
    for (const part of scopeText().split(' · ').filter(Boolean)) {
      const chip = document.createElement('span');
      chip.textContent = part;
      host.append(chip);
    }
    // What the hand-off could not bring across is stated beside the scope,
    // not left for the reader to meet as a number that looks too large.
    const notes = (appliedScope && appliedScope.notCarried) || [];
    el('scope-note').textContent = notes.join(' · ');
    el('scope-note').hidden = !notes.length;
  }

  // Canvas only hides the builder surfaces; the control that does it never
  // hides, so there is always a way back.
  function setOptionsHidden(hidden) {
    const host = document.querySelector('#view-chart-studio .studio');
    if (host) host.classList.toggle('studio-options-hidden', !!hidden);
    syncViewMode();
    // Canvas only puts the Inspector behind its header button the way a narrow
    // window does: the filter count stays readable and the panel stays off the
    // chart until it is asked for.
    const narrow = !!(window.matchMedia && window.matchMedia('(max-width: 1200px)').matches);
    const closed = !!hidden || narrow;
    el('inspector').hidden = closed;
    el('inspector-toggle').setAttribute('aria-expanded', String(!closed));
  }
  // Builder, Company overview and Canvas are three states of one thing, so they
  // are one radiogroup (item 13). Before this, Company overview was a separate
  // toggle beside a two-way segment and both could look "on" at once.
  function syncViewMode() {
    const host = document.querySelector('#view-chart-studio .studio');
    const hidden = !!(host && host.classList.contains('studio-options-hidden'));
    const state = overviewMode ? 'overview' : hidden ? 'canvas' : 'builder';
    for (const [id, name] of [['view-builder', 'builder'], ['overview-toggle', 'overview'], ['view-canvas', 'canvas']]) {
      const on = state === name;
      el(id).setAttribute('aria-checked', String(on));
      if (id === 'overview-toggle') el(id).setAttribute('aria-pressed', String(on));
      el(id).tabIndex = on ? 0 : -1;
    }
  }
  function setViewMode(mode) {
    const was = overviewMode;
    overviewMode = mode === 'overview';
    if (overviewMode) el('inspection').hidden = true;
    if (!overviewMode) setOptionsHidden(mode === 'canvas');
    if (overviewMode !== was || (board && board.tiles > 1)) renderAll(); else syncViewMode();
  }
  function setInspectorTab(name) {
    inspectorTab = ['marks', 'analytics', 'filters'].includes(name) ? name : 'marks';
    for (const id of ['marks', 'analytics', 'filters']) {
      const selected = id === inspectorTab;
      el('tab-' + id).setAttribute('aria-selected', String(selected));
      el('tab-' + id).tabIndex = selected ? 0 : -1;
      el('pane-' + id).hidden = !selected;
    }
  }


  /* ----------------------------------------------------------------- wiring */

  fill(el('mark'), core.MARK_TYPES);
  for (const [zone] of ZONES) dropTarget(el(zone), zone);
  // The view applies Analytics objects dropped on it. It also accepts a pill and
  // does nothing with it: the drop has to fire so that dragend does not read the
  // gesture as "dragged off the shelves" and delete the field. The effect stays
  // 'move' because a dropEffect of 'none' cancels the drop event itself.
  el('canvas-wrap').addEventListener('dragover', event => {
    if (!dragging) return;
    if (dragging.kind === 'analytics') {
      event.preventDefault();
      event.dataTransfer.dropEffect = 'copy';
      el('canvas-wrap').classList.add('is-over');
      return;
    }
    if (dragging.kind !== 'pill') return;
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  });
  el('canvas-wrap').addEventListener('dragleave', () => el('canvas-wrap').classList.remove('is-over'));
  el('canvas-wrap').addEventListener('drop', event => {
    el('canvas-wrap').classList.remove('is-over');
    if (!dragging) return;
    event.preventDefault();
    dropped = true;
    const move = dragging;
    dragging = null;
    if (move.kind === 'analytics') applyAnalytics(move.id);
  });

  el('undo').onclick = () => step(history, future);
  el('redo').onclick = () => step(future, history);
  el('swap').onclick = () => commit(() => { sheets[active] = core.swapShelves(sheet()); });
  // Verified: a radio pair. Pressing the direction the view is already in is
  // not an edit, so it costs no undo step, no persist and no re-render - and
  // 'none' stays a valid stored value meaning descending, so no saved view is
  // migrated. Worksheet: the existing toggle-back-to-none, unchanged.
  const chooseSort = direction => {
    if (verified()) {
      if (contributions.effectiveSort(sheet()) === direction) return;
      commit(() => { sheet().sort = direction; });
      return;
    }
    commit(() => { sheet().sort = sheet().sort === direction ? 'none' : direction; });
  };
  el('sort-asc').onclick = () => chooseSort('asc');
  el('sort-desc').onclick = () => chooseSort('desc');
  el('labels').onclick = () => commit(() => { sheet().showLabels = !sheet().showLabels; });
  el('fit').onchange = () => commit(() => { sheet().fit = el('fit').value; });
  el('clear').onclick = () => commit(() => { sheets[active] = core.clearSheet(sheet()); });
  el('duplicate').onclick = () => commit(() => {
    const copy = JSON.parse(JSON.stringify(sheet()));
    copy.id = 's' + Date.now();
    copy.name = nextName();
    sheets.splice(active + 1, 0, copy);
    // The copy takes the selected tile, because the copy is what the reader is
    // about to edit; every placed sheet above it moves up one with the splice.
    shiftBoard(active + 1);
    if (board) { const at = board.slots.indexOf(active); if (at >= 0) board.slots[at] = active + 1; }
    active += 1;
    dataSourceTab = false;
  });
  el('new-sheet').onclick = () => commit(() => {
    const fresh = core.createSheet(nextName(), 's' + Date.now());
    fresh.source = Object.assign({}, sheet().source);
    sheets.push(fresh);
    if (board) { const at = board.slots.indexOf(active); board.slots[at >= 0 ? at : 0] = sheets.length - 1; }
    active = sheets.length - 1;
    dataSourceTab = false;
  });
  el('sheet-source').onclick = () => { dataSourceTab = true; renderAll(); };
  el('download-png').onclick = () => download('png');
  el('download-svg').onclick = () => download('svg');
  el('download-csv').onclick = () => download('csv');
  el('copy-image').onclick = () => copyImage();
  el('print-chart').onclick = () => printChart();
  for (const tiles of BOARD_TILES) el('board-' + tiles).onclick = () => setBoard(tiles);
  el('board-briefing').onclick = () => boardToBriefing();
  el('save-view').onclick = () => saveView();
  el('open-views').onclick = () => openViews();
  // The tray itself lives in chart-briefing.js. A console that is not yet
  // serving it says so rather than answering the click with nothing.
  const toBriefing = () => {
    if (!window.MentatBriefing) {
      failure('Briefing needs a console restart.');
      return;
    }
    window.MentatBriefing.capture(currentChart());
  };
  el('briefing-add').onclick = toBriefing;
  // Show Me lives in exactly one place in the DOM - the Inspector's own
  // disclosure (item 18) - and the toolbar button opens that disclosure rather
  // than a second copy of it: it brings the Inspector back if it is closed,
  // puts the Marks pane in front, and scrolls the block into view.
  el('showme-toggle').onclick = () => {
    const details = el('showme-details'), open = !details.open;
    details.open = open;
    if (open) {
      if (el('inspector').hidden) {
        el('inspector').hidden = false;
        el('inspector-toggle').setAttribute('aria-expanded', 'true');
      }
      setInspectorTab('marks');
      details.scrollIntoView({block: 'nearest'});
    }
    renderToolbar();
  };
  el('showme-close').onclick = () => { el('showme-details').open = false; renderToolbar(); };
  el('classic').onclick = () => {
    // The classic dialog only scans its report list while the Graph view is
    // showing (charts.js activate()), so go there first and then open it.
    if (typeof showView === 'function') showView('graph');
    const dialog = document.getElementById('graph-builder');
    dialog.showModal();
    dialog.dispatchEvent(new Event('mentat:open'));
  };
  el('mark').onchange = () => commit(() => { const type=el('mark').value;sheet().marks.type=type;if(verified()&&type==='histogram'&&columns().some(f=>f.id==='amount_bin')){sheet().columns=[{column:columns().find(f=>f.id==='amount_bin').index,aggregation:'sum'}];sheet().rows=[{column:columns().find(f=>f.id==='records').index,aggregation:'sum'}];sheet().marks={type,color:null,size:null,label:null,detail:[],tooltip:[]};sheet().analytics.transform='none';}if(verified()&&['map','filled-map'].includes(type)&&(type==='filled-map'||!core.shelf([...sheet().columns,...sheet().rows]).some(p=>['zip5','state'].includes(columns()[p.column]?.id)))){sheet().columns=[{column:columns().find(f=>f.id===(type==='filled-map'?'state':'zip5')).index,aggregation:'sum'}];sheet().rows=[{column:columns().find(f=>f.id==='amount').index,aggregation:'sum'}];sheet().marks={type,color:null,size:null,label:null,detail:[],tooltip:[]};sheet().map={...sheet().map,layers:[...new Set([...(sheet().map?.layers||['districts']),'states'])]};sheet().analytics.transform='none';} });
  el('search').oninput = renderFields;
  el('field-table').onchange=renderFields;
  el('bin-width').onchange=()=>{if(el('bin-width').reportValidity())commit(()=>{sheet().params.binWidth=Number(el('bin-width').value);});};
  el('show-hidden').onchange = () => {
    // The reveal is a reading habit, not part of the view, so it is remembered
    // in this browser rather than saved into the sheet.
    try { localStorage.setItem('mentat-chart-studio-show-identifiers', el('show-hidden').checked ? '1' : '0'); } catch {}
    renderFields();
  };
  el('run').onchange = loadReports;
  el('report').onchange = loadSheets;
  el('sheet').onchange = () => scan(false);
  el('rescan').onclick = () => scan(true);
  el('source-mode').onchange=()=>{persist();data=null;sourceKey='';clearTimeout(geometryTimer);abortContributionRequests();tileMemory.clear();++contributionRevision;contributionMap?.destroy?.();contributionMap=null;el('inspection').hidden=true;renderAll();if(verified())loadContributions();else{fill(el('mark'),core.MARK_TYPES);loadRuns();}};
  el('dataset').onchange=()=>{persist();selectContributionDataset();};
  el('basis').onchange=()=>commit(()=>{sheet().source.basis=el('basis').value;activeSurface().offset=0;});
  el('refresh-data').onclick=()=>{++contributionCacheEpoch;abortContributionRequests();contributionCache.clear();memberCache.clear();graphTotalsCache.clear();loadContributions(true);};
    // The pager pages the tile the reader is looking at, and redraws that tile.
  el('groups-prev').onclick=()=>{const view=activeSurface();view.offset=Math.max(0,view.offset-(Number(view.state.params.maxGroups)||60));renderView(view);};
  el('groups-next').onclick=()=>{const view=activeSurface();view.offset+=Number(view.state.params.maxGroups)||60;renderView(view);};
  el('inspect-all').onclick=()=>inspectContributions();
  el('inspection-close').onclick=()=>{++recordRevision;el('inspection').hidden=true;};
  el('record-prev').onclick=()=>inspectContributions(recordSelection,Math.max(0,recordOffset-100));
  el('record-next').onclick=()=>inspectContributions(recordSelection,recordOffset+100);
  for(const id of ['layer-states','layer-districts','layer-zips','congress'])el(id).onchange=()=>commit(()=>{sheet().map={congress:el('congress').value,layers:[['states','states'],['districts','districts'],['zips','zip_areas']].filter(([id])=>el('layer-'+id).checked).map(([,layer])=>layer)};});
  el('pager-prev').onclick = () => stepPage(-1);
  el('pager-next').onclick = () => stepPage(1);
  el('pager-play').onclick = togglePlay;
  for (const [id, apply] of [
    ['param-start', v => { sheet().params.start = v; }],
    ['param-end', v => { sheet().params.end = v; }],
    ['param-limit', v => { sheet().params.limit = v; }],
    ['param-groups', v => { sheet().params.maxGroups = v; }],
    ['param-horizon', v => { sheet().analytics.horizon = v || 2; }]
  ]) el(id).onchange = () => commit(() => apply(Number(el(id).value) || 0));
  el('param-period').onchange = () => commit(() => { sheet().analytics.period = el('param-period').value; });
  el('param-subject').onchange = () => commit(() => { sheet().params.subject = el('param-subject').value; });
  el('param-split').onchange = () => commit(() => { sheet().params.splitMulti = el('param-split').checked; });
  for (const id of ['marks', 'analytics', 'filters']) el('tab-' + id).onclick = () => setInspectorTab(id);
  el('view-builder').onclick = () => setViewMode('builder');
  el('view-canvas').onclick = () => setViewMode('canvas');
  // A radiogroup the keyboard can cross: the unselected options carry
  // tabIndex -1, so without this they could only be reached with a mouse.
  el('view-mode').addEventListener('keydown', event => {
    const order = ['view-builder', 'overview-toggle', 'view-canvas'];
    const at = order.indexOf(event.target.id);
    const step = {ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1}[event.key];
    if (at < 0 || !step) return;
    event.preventDefault();
    for (let i = 1; i <= order.length; i += 1) {
      const next = el(order[(at + step * i + order.length * order.length) % order.length]);
      if (next.disabled) continue;
      next.focus();
      next.click();
      return;
    }
  });
  el('scope-change').onclick = () => {
    // An explicit open outlives the prepare that may have opened the panel
    // for its own reasons, so nothing closes it behind the reader's back.
    progressOpened = false;
    el('source-details').open = true;
    renderSourceSummary();
    el('source-details').querySelector('summary').focus();
  };
  el('source-details').addEventListener('toggle', renderSourceSummary);
  // Cancelling aborts the request that is preparing and leaves the last good
  // view exactly where it was: renderContributionView ignores AbortError.
  el('progress-cancel').onclick = () => {
    abortContributionRequests();
    progressDepth = 0;
    clearProgress();
    status('Cancelled. Showing the last loaded view.');
  };
  el('inspector-toggle').onclick = () => {
    const open = el('inspector').hidden;
    el('inspector').hidden = !open;
    el('inspector-toggle').setAttribute('aria-expanded', String(open));
  };
  el('inspector-close').onclick = () => {
    el('inspector').hidden = true;
    el('inspector-toggle').setAttribute('aria-expanded', 'false');
    el('inspector-toggle').focus();
  };
  el('overview-toggle').onclick = () => setViewMode('overview');
  el('overview-company').onchange = () => { overviewCompany = el('overview-company').value; renderOverview(); };
  // The Inspector is a column on a wide window and a drawer on a narrow one.
  // Crossing that line applies the same rule the first paint applies, so a
  // resized window never leaves the drawer sitting on top of its own toggle.
  // The toggle states what it is showing from the start, not only after a
  // click: a wide window arrives with the Inspector already open.
  const narrowStudio = window.matchMedia ? window.matchMedia('(max-width: 1200px)') : null;
  const syncInspector = isNarrow => {
    const host = document.querySelector('#view-chart-studio .studio');
    const closed = !!isNarrow || !!(host && host.classList.contains('studio-options-hidden'));
    el('inspector').hidden = closed;
    el('inspector-toggle').setAttribute('aria-expanded', String(!closed));
  };
  if (narrowStudio) {
    syncInspector(narrowStudio.matches);
    narrowStudio.addEventListener('change', event => syncInspector(event.matches));
  } else {
    el('inspector-toggle').setAttribute('aria-expanded', String(!el('inspector').hidden));
  }
  el('filter-add').onchange = () => {
    const column = Number(el('filter-add').value);
    el('filter-add').value = '';
    if (!Number.isInteger(column)) return;
    commit(() => { place('filters', column); });
    setInspectorTab('filters');
  };

  // An industry the URL changed while this panel was hidden, applied the moment
  // it is shown. Held rather than dropped when the panel is not ready yet, so a
  // change that arrives during the first load is not lost.
  let pendingIndustry = '';
  function followScopeIndustry() {
    if (!pendingIndustry || !loadedSources || !verified() || !contributionCatalog) return;
    const label = pendingIndustry;
    if (label === el('dataset').value) { pendingIndustry = ''; return; }
    if (!(contributionCatalog.datasets || []).some(entry => entry.id === label && entry.available)) { pendingIndustry = ''; return; }
    pendingIndustry = '';
    el('dataset').value = label;
    selectContributionDataset();
  }
  function activate() {
    const view = document.getElementById('view-chart-studio');
    if (!view || view.hidden) { stopPlay(); return; }
    if (!loadedSources) { loadedSources = true; if(verified())loadContributions();else loadRuns(); }
    followScopeIndustry();
  }
  // The Graph tab's "Create chart" button now opens Chart Studio; the classic
  // dialog stays one click away in the Chart Studio toolbar.
  // The Graph scope a verified contribution dataset can express. Employee tier
  // and the transfer mode/direction have no field in the contribution source,
  // and the drill-down category/recipient live only inside graph.js, so none of
  // them are carried. The button title says what does travel.
  const GRAPH_SCOPE = [['company', 'company'], ['cycle', 'cycle']];
  // What Graph can narrow by and this source cannot. Naming each one on the
  // scope chip is the difference between a total that looks wrong and a
  // total the reader knows is wider than the one they just left.
  const GRAPH_NOT_CARRIED = [
    ['tier', 'Employee level', 'not in verified data', ''],
    ['funding', 'Giving type', 'not in verified data', 'all'],
    ['mode', 'Candidate view', 'Graph only', 'direct'],
    ['direction', 'Support or opposition', 'Graph only', 'Support']
  ];
  function graphScope() {
    const read = id => (document.getElementById('graph-' + id) || {}).value || '';
    const scope = {industry: read('industry'), filters: [], notCarried: []};
    for (const [control, field] of GRAPH_SCOPE) {
      const value = read(control);
      // Graph spells a cycle by its end year and the verified index spells it
      // as the pair it covers, so the carried value is translated here rather
      // than filtered on a spelling the index never holds.
      if (value) scope.filters.push({field, value: core.carriedFilterValue(field, value)});
    }
    for (const [control, label, why, ignored] of GRAPH_NOT_CARRIED) {
      const value = read(control);
      if (value && value !== ignored) scope.notCarried.push(label + ': not carried (' + why + ')');
    }
    return scope;
  }
  const openBuilder = document.getElementById('graph-open-builder');
  if (openBuilder) {
    openBuilder.textContent = 'Open in Chart Studio';
    openBuilder.title = 'Carry the industry, company and cycle now showing into Chart Studio';
    openBuilder.removeAttribute('aria-haspopup');
    openBuilder.onclick = () => {
      pendingScope = graphScope();
      // The URL carries Graph's own spelling of the cycle (the end year, per
      // contracts/url_scope.json); the carried pill keeps the verified index's
      // pair spelling. One scope, two vocabularies, and the contract says which
      // is which - so the scope is read from the Graph controls, not from the
      // already-translated pendingScope.
      const read = id => (document.getElementById('graph-' + id) || {}).value || '';
      globalThis.MentatScope?.write({industry: pendingScope.industry, company: read('company'), cycle: read('cycle')});
      if (typeof showView === 'function') showView('chart-studio'); else location.hash = '#chart-studio';
      if (loadedSources && verified()) applyGraphScope();
    };
  }
  // Back, or a scope written by another view in this document, can change the
  // industry in the URL. Chart Studio follows it, but only when it disagrees
  // with the picker, so its own write can never loop back into a second
  // selection - and only once this panel is on screen, because re-selecting a
  // dataset fires a verified query and nobody asked for one behind a hidden
  // tab. A dataset this console does not have available is left alone;
  // openability() and the Data panel already say why.
  globalThis.MentatScope?.subscribe(next => {
    const label = (next && next.industry) || '';
    if (!label || label === el('dataset').value) return;
    pendingIndustry = label;
    const panel = document.getElementById('view-chart-studio');
    if (panel && !panel.hidden) followScopeIndustry();
  });
  window.addEventListener('mentat:view', activate);
  window.addEventListener('hashchange', activate);
  try { el('show-hidden').checked = localStorage.getItem('mentat-chart-studio-show-identifiers') === '1'; } catch {}
  if(new URLSearchParams(location.search).has('worksheet'))el('source-mode').value='worksheet';
  // What the rest of the console may ask this studio about its chart. The
  // filter reader is also what a browser test reads the carried pills from.
  window.MentatStudioPane = {
    filters() { return (sheet().filters || []).map(f=>({...f,field:columns()[f.column]?.id || columns()[f.column]?.name})); },
    // The briefing drawer and the share dialog live in chart-briefing.js and
    // read the chart through the same one description the studio uses.
    currentChart,
    saveView,
    openViews,
    // The payload builders, so a browser test can assert what this console puts
    // on the wire rather than what a fixture claims it puts there.
    viewSourceRecord,
    viewSourceText
  };
  if(el('destination'))el('destination').onchange=()=>{const id=el('destination').value;if(!id)return;const at=columns().findIndex(f=>f.id===id),amount=columns().findIndex(f=>f.id==='amount');if(at<0||amount<0){failure('Regenerate this workbook to create its destination fields.');return;}commit(()=>{sheet().columns=[{column:at,aggregation:'sum'}];sheet().rows=[{column:amount,aggregation:'sum'}];sheet().marks={type:'bar',color:null,size:null,label:null,detail:[],tooltip:[]};sheet().analytics.transform='none';});};
  renderAll();
  activate();
})();
