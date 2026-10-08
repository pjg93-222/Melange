/* Optional industry intelligence. Queries, record inspection and exports all
   retain one server-resolved scope; changing it invalidates every old reply.
   Design reference: synthetic Higgsfield c67f4e78-17a0-436d-abb3-87f21ae1e450,
   2026-09-20: ivory surfaces, plum serif, teal marks and compact controls. */
(function (root) {
  'use strict';
  const PANELS = [
    ['favorites', 'Industry favorites', 'Amount, company breadth, persistence and relative preference.'],
    ['trends', 'Comparable-cycle trends', 'Spending pace through matching points in the cycle.'],
    ['changes', 'Explain the change', 'Separate continuing companies, coverage and accounting changes.'],
    ['concentration', 'Concentration & breadth', 'See how much the largest sources and recipients account for.'],
    ['relationships', 'Relationship persistence', 'Recurring, new and no-longer-observed recipient relationships.'],
    ['overlap', 'Company portfolio overlap', 'Compare companies’ distributions of support across recipients.'],
    ['timing', 'Timing patterns', 'Monthly peaks, recurring rhythms and unusual activity.'],
    ['profiles', 'Recipient profiles', 'Dated candidate and committee identities with financial context.'],
    ['spending', 'Outgoing spending', 'Committee expenditures and vendor patterns where supported.'],
    ['legislation', 'Legislative context', 'Legislative activity beside contribution timelines.'],
    ['forecast', 'Forecasts', 'Historical baselines, backtests and supported projections.']
  ];
  const CORE = ['favorites', 'trends', 'changes'];
  const SHORT_TITLES = {favorites:'Favorites',trends:'Trends',changes:'Changes',concentration:'Concentration',relationships:'Relationships',overlap:'Company overlap',timing:'Timing',profiles:'Recipient profiles',spending:'Outgoing spending',legislation:'Legislative context',forecast:'Forecasts'};
  const KEYS = PANELS.map(p => p[0]);
  const BASES = ['receipt', 'original_observed', 'original_supported', 'pac_activity'];
  const STORAGE = 'mentat.insights.panels.v1';
  const PANEL_CONTEXT = {profiles:'Dated FEC identity context; no contribution allocation',spending:'Saved outgoing payments and full campaign or committee finances; separate from industry giving',legislation:'Dated legislative context; no contribution dollars assigned to bills'};
  const FUNDING_LABELS = {employee_original:'Employee giving',employee:'Employee giving',corporate_original:'Corporate giving',corporate:'Corporate giving',pac_activity:'PAC activity',organization_unverified:'Unverified organization',funding_unverified:'Unverified funding',unverified:'Unverified funding',conflicting_source_evidence:'Conflicting source evidence',linked_refund:'Linked refunds',non_giving:'Non-giving records',excluded_source_policy:'Excluded by source policy',excluded_company_match:'Excluded company matches',connected_pac:'Connected PAC'};
  const STATUS_LABELS = {ready:'Available',partial:'Partial coverage',unavailable:'Not available',empty:'No observed rows',insufficient_history:'More history needed',observed:'Observed'};
  const chartChannels = {};
  const PAGE_SIZE = 50;
  const money = new Intl.NumberFormat('en-US', {style: 'currency', currency: 'USD', maximumFractionDigits: 2});
  const number = new Intl.NumberFormat('en-US', {maximumFractionDigits: 2});
  function fundingLabel(value) { return FUNDING_LABELS[value] || String(value).replace(/_/g,' ').replace(/^./,letter=>letter.toUpperCase()); }
  function display(value, column) {
    if (value === null || value === undefined || value === '') return '—';
    if (['funding_source','channel'].includes(column.key)) return fundingLabel(value);
    if (typeof value === 'boolean') return value ? 'Yes' : 'No';
    if (column.type === 'money' && Number.isFinite(Number(value))) return money.format(Number(value) / (column.unit === 'dollars' ? 1 : 100));
    if (column.type === 'percent' && Number.isFinite(Number(value))) return number.format(Number(value) * (column.unit === 'percent' ? 1 : 100)) + '%';
    if (column.type === 'number' && Number.isFinite(Number(value))) return number.format(Number(value));
    return typeof value === 'object' ? JSON.stringify(value) : String(value);
  }
  function csvCell(value) {
    let text = value === null || value === undefined ? '' : String(value);
    // Spreadsheet applications interpret formulas even when a CSV cell is quoted.
    if (/^[\s\uFEFF]*[=+@-]/.test(text) && typeof value !== 'number') text = "'" + text;
    return '"' + text.replace(/"/g, '""') + '"';
  }
  function inferredColumns(rows) {
    const keys = [...new Set(rows.flatMap(row => Object.keys(row)))].filter(key => !['filters','comparison_scopes','backtests'].includes(key));
    return keys.map(key => ({key,label:key.replace(/_/g,' '),type:key.endsWith('_cents') ? 'money' : /(?:share|retention|overlap)$/.test(key) ? 'percent' : rows.some(row => typeof row[key] === 'number') ? 'number' : 'text'}));
  }
  function supplementary(panel) {
    const tables = [];
    for (const [key,title] of [['cards','Summary measures'],['company_changes','Company change details'],['series','Monthly observations'],['quarterly_series','Quarterly observations'],['diagnostics','Forecast requirements and validation'],['vendor_patterns','Outgoing payee patterns'],['purpose_patterns','Reported payment purposes'],['spending_summaries','Saved outgoing-payment summaries']]) {
      const rows = panel[key]; if (Array.isArray(rows) && rows.length) tables.push({key,title,rows,columns:inferredColumns(rows),total_rows:panel[key+'_total_rows'] || panel[key+'_total']});
    }
    const backtests = (panel.diagnostics || []).flatMap(d => (d.backtests || []).map(row => ({funding_source:d.funding_source,...row})));
    if (backtests.length) tables.push({key:'backtests',title:'Held-out cycle errors',rows:backtests,columns:inferredColumns(backtests)});
    return tables;
  }
  function exportCSV(result) {
    const scope = result.scope || {};
    const provenance = JSON.stringify(result.provenance || {});
    const tables = Object.entries(result.panels || {}).flatMap(([key,panel]) => [[key,panel],...supplementary(panel).map(table => [key+'.'+table.key,{...table,status:panel.status,notices:panel.notices,sources:panel.sources}])]);
    const columns = [];
    for (const [,panel] of tables) for (const column of panel.columns || []) {
      const key = column.key + (column.type === 'money' ? column.unit === 'dollars' ? ' (dollars)' : ' (cents)' : column.type === 'percent' && column.unit !== 'percent' ? ' (ratio)' : '');
      if (!columns.includes(key)) columns.push(key);
    }
    const headers = ['panel', 'panel_status', 'scope.dataset', 'scope.contribution_basis', 'panel_accounting_context', 'scope.as_of', 'scope.baseline_cycle', 'scope.current_cycle', 'scope.company', 'scope.funding_source', 'scope.comparison_dataset', 'provenance', 'panel_sources', 'notices', ...columns];
    const lines = [headers];
    for (const [key, panel] of tables) {
      const notices = [...(result.notices || []), ...(panel.notices || [])].map(noticeText).join(' | ');
      for (const row of (panel.rows || []).length ? panel.rows : [{}]) {
        const values = {};
        for (const column of panel.columns || []) values[column.key + (column.type === 'money' ? column.unit === 'dollars' ? ' (dollars)' : ' (cents)' : column.type === 'percent' && column.unit !== 'percent' ? ' (ratio)' : '')] = row[column.key];
        lines.push([key, panel.status || '', scope.dataset || '', scope.basis || '', PANEL_CONTEXT[key.split('.')[0]] || scope.basis_label || scope.basis || '',scope.as_of || '', scope.baseline_cycle || '', scope.current_cycle || '', scope.company || '', scope.funding_source || '', scope.comparison_dataset || '', provenance, JSON.stringify(panel.sources || []), notices, ...columns.map(c => values[c])]);
      }
    }
    return '\uFEFF' + lines.map(row => row.map(csvCell).join(',')).join('\r\n');
  }
  function noticeText(value) { return typeof value === 'string' ? value : value && (value.message || value.description || value.label) || JSON.stringify(value); }
  if (typeof module !== 'undefined' && module.exports) { module.exports = {display, csvCell, exportCSV, PANELS}; return; }
  if (!root.document.getElementById('view-insights')) return;
  const el = id => root.document.getElementById('insights-' + id);
  function node(tag, text, className) { const out = document.createElement(tag); if (text !== undefined) out.textContent = text; if (className) out.className = className; return out; }
  let active = false, catalog = null, token = '', result = null, revision = 0, sourceRevision = 0;
  let request = null, sourceRequest = null, pollTimer = null, loading = false, sourceContext = null, sourceReturnFocus = null;
  let enabled = CORE.slice(), storageAvailable = true;
  try { const saved = JSON.parse(localStorage.getItem(STORAGE)); if (Array.isArray(saved)) enabled = KEYS.filter(key => saved.includes(key)); } catch (_) { storageAvailable = false; }
  const sorts = {}, tablesShown = {};
  function preferences() {
    try { localStorage.setItem(STORAGE, JSON.stringify(enabled)); storageAvailable = true; } catch (_) { storageAvailable = false; }
    el('preference-note').textContent = storageAvailable ? 'Choices saved in this browser.' : 'Choices apply to this visit; browser storage is unavailable.';
    el('preference-note').hidden = storageAvailable;
  }
  function renderToggles() {
    el('toggles').replaceChildren();
    for (const [key, title, description] of PANELS) {
      const metadata = (catalog && catalog.panels || []).find(p => p.id === key) || {};
      const label = node('label', undefined, 'insights-toggle'), checkbox = node('input');
      checkbox.type = 'checkbox'; checkbox.value = key; checkbox.checked = enabled.includes(key); checkbox.id = 'insights-toggle-' + key;
      const text = node('span'); text.append(node('strong', SHORT_TITLES[key] || metadata.title || title), node('small', metadata.description || description)); label.title=(metadata.title || title)+': '+(metadata.description || description); label.append(checkbox, text);
      checkbox.addEventListener('change', () => { enabled = KEYS.filter(k => k === key ? checkbox.checked : enabled.includes(k)); preferences(); updateCount(); load(); });
      el('toggles').append(label);
    }
    updateCount();
  }
  function updateCount() { el('enabled-count').textContent = enabled.length + ' of ' + KEYS.length + ' enabled'; }
  function status(message, state) { el('status').textContent = message; el('status').dataset.state = state || ''; }
  function exporting(allowed) { el('export-csv').disabled = !allowed; el('export-json').disabled = !allowed; }
  function invalidate() {
    revision++; if (request) request.abort(); request = null;
    clearTimeout(pollTimer); pollTimer = null; loading = false;
    result = null; exporting(false); el('results').replaceChildren(); el('results').setAttribute('aria-busy', 'false');
    el('scope').hidden = true; el('notices').replaceChildren(); el('retry').hidden = true; closeSources();
    return revision;
  }
  function fillSelect(target, values, emptyLabel, current, preserveMissing = false) {
    const wanted = current === undefined ? target.value : String(current || '');
    target.replaceChildren(); if (emptyLabel !== null) target.append(new Option(emptyLabel, ''));
    for (const value of values || []) {
      const id = typeof value === 'object' ? value.id === undefined ? value.value : value.id : value;
      if (id === undefined || id === null) continue;
      const label = typeof value === 'object' ? value.label || String(id) : String(value);
      target.append(new Option(label, String(id)));
    }
    if (wanted && preserveMissing && !Array.from(target.options).some(o => o.value === wanted)) target.append(new Option((target.id==='insights-funding-source'?fundingLabel(wanted):wanted)+(target.id==='insights-dataset'?' · unavailable':' · not in current options'),wanted));
    if (Array.from(target.options).some(o => o.value === wanted)) target.value = wanted;
  }
  function updateComparisonOptions() {
    for(const option of el('comparison-dataset').options) option.disabled=Boolean(option.value) && option.value===el('dataset').value;
    if(el('comparison-dataset').value===el('dataset').value)el('comparison-dataset').value='';
  }
  function resetIndustryFilters() {
    // Company/funding choices belong to an industry. Accounting and the two
    // comparison periods are independent Insights controls, not Graph's cycle.
    fillSelect(el('company'),[],'All covered companies','');
    fillSelect(el('funding-source'),[],'All reported sources','');
    updateComparisonOptions();
  }
  function adoptSharedIndustry(scope) {
    const industry=scope && scope.industry;
    if(!industry || !catalog || industry===el('dataset').value)return false;
    if(!Array.from(el('dataset').options).some(option=>option.value===industry))el('dataset').append(new Option(industry+' · unavailable',industry));
    el('dataset').value=industry;resetIndustryFilters();return true;
  }
  function installCatalog(data) {
    catalog = data;
    const datasets = data.datasets || [];
    const wanted = root.MentatScope?.read()?.industry || el('dataset').value || document.getElementById('graph-industry')?.value || '';
    fillSelect(el('dataset'), datasets.map(d => ({id: d.id, label: (d.label || d.id) + (d.available === false ? ' · unavailable' : '')})), datasets.length ? null : 'No industries available', wanted,true);
    fillSelect(el('comparison-dataset'), datasets.filter(d => d.available !== false), 'No industry comparison');
    updateComparisonOptions();
    renderToggles();
  }
  function installOptions(data) {
    const options = data.options || {}, scope = data.scope || {};
    if (options.companies) fillSelect(el('company'), options.companies, 'All covered companies', scope.company === undefined ? el('company').value : scope.company,true);
    if (options.funding_sources) fillSelect(el('funding-source'), options.funding_sources.map(value=>typeof value==='string'?{id:value,label:fundingLabel(value)}:value), 'All reported sources', scope.funding_source === undefined ? el('funding-source').value : scope.funding_source,true);
    if (options.cycles) {
      // Resolved automatic periods describe the result, not a user filter edit.
      // Keep the request stable so showing another panel reuses its analysis.
      fillSelect(el('baseline-cycle'), options.cycles, 'Automatic', el('baseline-cycle').value,true);
      fillSelect(el('current-cycle'), options.cycles, 'Automatic', el('current-cycle').value,true);
    }
  }
  function scopeQuery() {
    const out = {dataset: el('dataset').value, basis: BASES.includes(el('basis').value) ? el('basis').value : 'receipt', panels: enabled.slice()};
    for (const [field, control] of [['company','company'],['funding_source','funding-source'],['as_of','as-of'],['baseline_cycle','baseline-cycle'],['current_cycle','current-cycle'],['comparison_dataset','comparison-dataset']]) if (el(control).value) out[field] = el(control).value;
    return out;
  }
  async function api(path, body, signal) {
    const response = await fetch(path, body === undefined ? {signal, cache: 'no-store'} : {method: 'POST', headers: {'Content-Type': 'application/json', 'X-Mentat-Token': token}, body: JSON.stringify(body), signal});
    let data; try { data = await response.json(); } catch (_) { throw new Error('The server returned an unreadable response.'); }
    if (!response.ok || data.error || data.status === 'failed') throw new Error(data.error || data.message || 'The analysis could not be loaded.');
    return data;
  }
  async function load(retry = false) {
    const ticket = invalidate();
    if (!active) return;
    if (!enabled.length) { status('All analyses are off. Enable an analysis to explore this industry.'); el('results').append(node('p', 'Choose analyses above to build your workspace.', 'insights-empty')); return; }
    loading = true; request = new AbortController(); const signal = request.signal;
    el('results').setAttribute('aria-busy', 'true'); status('Loading industry scope and source information…', 'loading');
    try {
      if (!catalog || !token) {
        const [data, session] = await Promise.all([api('/api/insights/catalog', undefined, signal), api('/api/contributions/session', undefined, signal)]);
        if (ticket !== revision || !active) return;
        token = session.token; if (!token) throw new Error('The local session did not provide an analysis token.'); installCatalog(data);
      }
      const query = scopeQuery();
      if (retry) query.retry = true;
      if (!query.dataset) { status('No industry data is available. Load an industry report to begin.'); loading = false; el('results').setAttribute('aria-busy','false'); return; }
      await queryReady(query, ticket, signal, 0);
    } catch (error) { fail(error, ticket); }
  }
  async function queryReady(query, ticket, signal, attempts) {
    const data = await api('/api/insights/query', query, signal);
    if (ticket !== revision || !active) return;
    if (['building', 'queued', 'preparing'].includes(data.status)) {
      if (attempts >= 120) throw new Error('Preparation is still running on the server. Retry to check its progress.');
      status(data.message || 'Preparing the selected analysis…', 'loading');
      const nextQuery = {...query}; delete nextQuery.retry;
      pollTimer = setTimeout(() => { queryReady(nextQuery, ticket, signal, attempts + 1).catch(error => fail(error, ticket)); }, Math.max(500, Math.min(5000, data.retry_after_ms || 1500)));
      return;
    }
    result = data; result._request = query; loading = false; el('results').setAttribute('aria-busy','false');
    installOptions(data); renderResult(data);
  }
  function fail(error, ticket) {
    if (ticket !== revision || !active || error.name === 'AbortError') return;
    loading = false; el('results').setAttribute('aria-busy', 'false'); status(error.message, 'error'); el('retry').hidden = false; exporting(false);
  }
  function addNotices(target, notices) { for (const notice of notices || []) target.append(node('p', noticeText(notice), 'insights-notice')); }
  function renderScope(data) {
    const scope = data.scope || {}, provenance = data.provenance || {};
    const target = el('scope'); target.hidden = false; target.replaceChildren();
    const dataset = (catalog.datasets || []).find(d => d.id === scope.dataset);
    target.append(node('strong', (dataset && dataset.label || scope.dataset || 'Selected industry') + ' · ' + (scope.basis_label || scope.basis || 'Accounting basis not supplied')));
    const parts = ['Through ' + (scope.as_of || 'latest available date'), scope.company || 'All covered companies', scope.funding_source ? fundingLabel(scope.funding_source) : 'All funding sources'];
    if (scope.baseline_cycle || scope.current_cycle) parts.push('Cycles: ' + (scope.baseline_cycle || 'automatic') + ' → ' + (scope.current_cycle || 'automatic'));
    if (scope.comparison_dataset) parts.push('Industry comparison: ' + scope.comparison_dataset);
    target.append(node('div', parts.join(' · ')+' · Saved coverage; completeness unverified'));
    if (enabled.some(key=>PANEL_CONTEXT[key])) target.append(node('div','Identity, spending and legislative panels use this selection to find related entities. Each has its own source coverage and accounting context.'));
    const details = node('details'), summary = node('summary','Source and accounting provenance'), list = node('dl',undefined,'insights-provenance');
    for (const [key, value] of Object.entries(provenance)) { list.append(node('dt',key.replace(/_/g,' ')), node('dd', typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value === null ? 'not supplied' : value))); }
    if (!list.children.length) list.append(node('dt','Source'),node('dd','No source fingerprint was supplied.'));
    details.append(summary,list); target.append(details);
    if (data.history || data.source_history) {
      const history=node('details'), body=node('pre',undefined,'insights-history');
      history.append(node('summary','Inspection history and source snapshots'));
      history.append(node('p','Inspection timestamps record when this Insights workspace encountered evidence. They are not filing dates or the dates records first became public.'));
      body.textContent=JSON.stringify({inspection:data.history,source_snapshots:data.source_history},null,2); history.append(body);target.append(history);
    }
  }
  function renderResult(data) {
    renderScope(data);
    if((data.notices || []).length){const notes=node('details',undefined,'insights-global-notes');notes.append(node('summary','Scope and coverage notes · '+data.notices.length));addNotices(notes,data.notices);el('notices').append(notes);}
    plotObserver?.disconnect();el('results').replaceChildren();
    for (const key of [...enabled].sort((a,b)=>(a==='trends'?-1:b==='trends'?1:0))) renderPanel(key, (data.panels || {})[key] || {status:'unavailable',summary:'This analysis was not returned by the source.'});
    const count = enabled.filter(key => (data.panels || {})[key]?.rows?.length).length;
    status(count ? count + ' analyses contain results.' : 'Analysis complete. No observed rows are available for this selection; missing evidence does not establish zero activity.');
    exporting(true);
  }
  function renderPanel(key, panel) {
    const card = node('article', undefined, 'panel insights-card'); card.id = 'insights-panel-' + key;
    if (!CORE.includes(key) && (panel.columns || []).length > 6) card.classList.add('insights-card-wide');
    const heading = node('div',undefined,'insights-panel-heading'), title = node('h3',key==='trends'?'Giving through the same point in each cycle':key==='favorites'?'Favorite recipients':key==='changes'?'What changed':panel.title || PANELS.find(p => p[0] === key)[1]); title.id = card.id + '-title'; card.setAttribute('aria-labelledby',title.id);
    const badge = node('span',STATUS_LABELS[panel.status || 'observed'] || (panel.status || 'observed').replace(/_/g,' '),'insights-panel-badge'); badge.dataset.status = panel.status || 'observed'; heading.append(title,badge); card.append(heading);
    if (panel.summary) card.append(node('p',noticeText(panel.summary),'insights-card-summary'));
    let rows = (panel.rows || []).slice();
    if (!rows.length) card.append(node('p',panel.message || 'No observed records for this analysis in the selected scope.','insights-empty'));
    else {
      const chart = makeChart(key,panel); if (chart) {const area=node('div',undefined,'insights-chart-area');area.append(chart);card.append(area);if(key==='trends'){const filter=chart.querySelector('.insights-chart-filter');if(filter)heading.append(filter);const summary=card.querySelector('.insights-card-summary');if(summary)area.append(summary);}}
      const tableHost = node('div');
      const renderTable = () => {
        const sort=sorts[key], previous=tableHost.firstElementChild, scrollLeft=previous?.scrollLeft || 0, scrollTop=previous?.scrollTop || 0;
        if(sort)rows.sort((a,b)=>{const av=a[sort.key],bv=b[sort.key];if(av===null||av===undefined)return bv===null||bv===undefined?0:1;if(bv===null||bv===undefined)return -1;return(typeof av==='number'&&typeof bv==='number'?av-bv:String(av).localeCompare(String(bv),undefined,{numeric:true}))*sort.direction;});
        tableHost.replaceChildren(makeTable(panel.columns || [],rows,{key,sort,onSort:column=>{sorts[key]={key:column.key,direction:sort&&sort.key===column.key?-sort.direction:-1};renderTable();Array.from(tableHost.querySelectorAll('.insights-sort')).find(button=>button.dataset.column===column.key)?.focus({preventScroll:true});}}));
        tableHost.firstElementChild.scrollLeft=scrollLeft;tableHost.firstElementChild.scrollTop=scrollTop;
      };
      renderTable(); card.append(tableHost);
      const tools=node('div',undefined,'insights-card-tools analysis-chart-actions'), segment=node('div',undefined,'analysis-segment'), chartButton=node('button','Chart','secondary'),tableButton=node('button','Table','secondary'),exportButton=node('button','Export','secondary');
      tableHost.id='insights-table-'+key;tableButton.setAttribute('aria-controls',tableHost.id);
      const toggle=show=>{tableHost.hidden=!show;tablesShown[key]=show;tableButton.setAttribute('aria-expanded',String(show));tableButton.setAttribute('aria-pressed',String(show));chartButton.setAttribute('aria-pressed',String(!show));if(chart)chart.parentElement.hidden=show;};
      chartButton.type=tableButton.type=exportButton.type='button';chartButton.disabled=!chart;chartButton.onclick=()=>toggle(false);tableButton.onclick=()=>toggle(tableHost.hidden);toggle(!chart||Boolean(tablesShown[key]));
      segment.setAttribute('role','group');segment.setAttribute('aria-label',title.textContent+' presentation');segment.append(chartButton,tableButton);
      exportButton.setAttribute('aria-label','Export '+title.textContent+' as CSV');exportButton.onclick=()=>download('csv',key);tools.append(segment,exportButton);heading.append(tools);
      if (panel.truncated || (panel.total_rows && panel.total_rows > rows.length)) card.append(node('p','Showing ' + rows.length + (panel.total_rows ? ' of ' + panel.total_rows : '') + ' analysis rows. Exports contain these returned rows. Narrow the scope for a smaller result.','insights-notice'));
    }
    if ((panel.notices || []).length) { const notes = node('details',undefined,'insights-method-notes'); notes.append(node('summary','Method and coverage · '+panel.notices.length)); addNotices(notes,panel.notices); card.append(notes); }
    for (const table of supplementary(panel)) {
      const details = node('details',undefined,'insights-extra-table'); details.append(node('summary',table.title+' · '+table.rows.length+' rows'),makeTable(table.columns,table.rows,{key}));
      if (table.total_rows > table.rows.length) details.append(node('p','Showing '+table.rows.length+' of '+table.total_rows+' rows. Exports include this returned subset. Narrow the scope to inspect the remainder.','muted'));
      card.append(details);
    }
    const context = result.scope || {};
    if (PANEL_CONTEXT[key]) {
      card.append(node('p',PANEL_CONTEXT[key]+' · cutoff '+(context.as_of || 'latest available')+(key==='spending'?' · amounts in USD':''),'insights-card-source'));
      const sources=node('details',undefined,'insights-extra-table');sources.append(node('summary','Source snapshots · '+(panel.sources || []).length));
      if(!(panel.sources || []).length)sources.append(node('p','No verified source snapshot is available for this panel.'));
      for(const source of panel.sources || []){const list=node('dl',undefined,'insights-provenance');for(const [field,value] of Object.entries(source))list.append(node('dt',field.replace(/_/g,' ')),node('dd',typeof value==='object'?JSON.stringify(value):String(value)));sources.append(list);}card.append(sources);
    } else card.append(node('p',(context.basis_label || context.basis || '') + ' · cutoff ' + (context.as_of || 'latest available') + ' · amounts in USD' + (result.provenance?.workbook ? '\nSource: '+result.provenance.workbook : ''),'insights-card-source'));
    el('results').append(card);
  }
  function makeTable(columns, rows, config) {
    const wrap = node('div',undefined,'insights-table-wrap'); wrap.tabIndex = 0; wrap.setAttribute('role','region'); wrap.setAttribute('aria-label',config && config.key ? 'Data for ' + config.key : 'Underlying records');
    const table = node('table',undefined,'insights-table'), thead = node('thead'), head = node('tr'), tbody = node('tbody');
    const sources = Boolean(config && rows.some(row => row.filters && typeof row.filters === 'object' && Object.keys(row.filters).length));
    for (const column of columns) {
      const th = node('th'); th.scope = 'col'; if (['money','percent','number'].includes(column.type)) th.className = 'insights-numeric';
      if (config && config.onSort) { const button = node('button', column.label || column.key,'insights-sort'); button.type = 'button'; button.dataset.column=column.key; button.setAttribute('aria-label','Sort by ' + (column.label || column.key)); button.addEventListener('click',() => config.onSort(column)); th.append(button); if (config.sort?.key === column.key) th.setAttribute('aria-sort',config.sort.direction === 1 ? 'ascending' : 'descending'); } else th.textContent = column.label || column.key;
      head.append(th);
    }
    if (sources) head.append(node('th','Evidence')); thead.append(head);
    for (const row of rows) {
      const tr = node('tr');
      for (const column of columns) {
        const td=node('td',display(row[column.key],column),['money','percent','number'].includes(column.type)?'insights-numeric':undefined);
        if(column.type==='url' && /^https?:\/\//i.test(String(row[column.key] || ''))) {const link=node('a','Open source','insights-source-link');link.href=String(row[column.key]);link.target='_blank';link.rel='noopener noreferrer';link.title=String(row[column.key]);td.replaceChildren(link);}tr.append(td);
      }
      if (sources) {
        const td = node('td');
        if (row.filters && typeof row.filters === 'object' && Object.keys(row.filters).length) {
          const choices = row.comparison_scopes ? Object.entries(row.comparison_scopes).map(([label,filters]) => ({label:label==='baseline'?'Baseline records':'Current records',filters})) : [{label:'View records',filters:row.filters}];
          if (config.key === 'trends' && row.matched_through && Array.isArray(row.filters)) { choices[0].label = 'Full observed'; choices.push({label:'Same-stage records',filters:row.matched_filters || [...row.filters,{field:'date',op:'lte',value:row.matched_through},{field:'date',op:'gte',value:String(row.cycle || '').slice(0,4)+'-01-01'}]}); }
          for (const choice of choices) { const button=node('button',choice.label,'insights-source-button'); button.type='button'; button.addEventListener('click',()=>openSources(config.key,{...row,filters:choice.filters},choice.label,button)); td.append(button); }
        } else td.textContent = 'No record filter';
        tr.append(td);
      }
      tbody.append(tr);
    }
    table.append(thead,tbody); wrap.append(table); return wrap;
  }
  const SVG_NS = 'http://www.w3.org/2000/svg';
  function svgNode(tag, attrs, text) { const out = document.createElementNS(SVG_NS,tag); for (const [key,value] of Object.entries(attrs || {})) out.setAttribute(key,String(value)); if (text !== undefined) out.textContent = text; return out; }
  const plotDrawers=new WeakMap();
  const plotObserver=typeof ResizeObserver==='undefined'?null:new ResizeObserver(entries=>{
    for(const {target,contentRect}of entries){const draw=plotDrawers.get(target),width=Math.round(contentRect.width);if(draw&&width>0&&target.dataset.width!==String(width)){target.dataset.width=width;draw(width);}}
  });
  function responsiveFigure(label,draw){
    const figure=node('figure',undefined,'insights-chart');
    const repaint=width=>{figure.replaceChildren();draw(figure,width);};plotDrawers.set(figure,repaint);
    plotObserver?.observe(figure);requestAnimationFrame(()=>{if(figure.isConnected)repaint(Math.max(240,figure.clientWidth));});return figure;
  }
  const compactMoney=value=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',notation:'compact',maximumFractionDigits:1}).format(value/100);
  function chartMark(svg,mark,key,row,label,amount,value,filters){
    const context=[label,display(amount,value),result?.scope?.basis_label,result?.scope?.as_of?'through '+result.scope.as_of:'',row.coverage||'Saved coverage; completeness unverified'].filter(Boolean).join(' · ');
    const group=svgNode('g',{'aria-label':context,role:filters?'button':'img',...(filters?{tabindex:0}:{}),class:'insights-mark'});group.append(svgNode('title',{},context),mark);
    if(filters){const select=()=>{document.querySelectorAll('.insights-mark[aria-pressed]').forEach(n=>n.removeAttribute('aria-pressed'));group.setAttribute('aria-pressed','true');openSources(key,{...row,filters},label,group);};group.onclick=select;group.onkeydown=e=>{if(['Enter',' '].includes(e.key)){e.preventDefault();select();}};}
    svg.append(group);return group;
  }
  function makeChart(key,panel){
    if(!['favorites','concentration','trends','timing','changes'].includes(key))return null;
    if(key==='changes'&&panel.cards?.length)return waterfall(panel);
    if(key==='trends'&&panel.rows?.some(r=>r.cycle&&r.funding_source))return channelTrends(key,panel);
    if(key==='concentration'&&panel.rows?.some(r=>r.dimension&&r.name)){
      const host=node('div');for(const dimension of new Set(panel.rows.map(r=>r.dimension))){const chart=makeChart('favorites',{...panel,rows:panel.rows.filter(r=>r.dimension===dimension),columns:[{key:'name',label:dimension,type:'text'},...panel.columns.filter(c=>c.key!=='name'&&c.key!=='dimension')]});if(chart){chart.prepend(node('p',dimension));host.append(chart);}}return host;
    }
    const cols=panel.columns||[],label=cols.find(c=>c.key===(key==='favorites'?'recipient':key==='timing'?'month':'name'))||cols.find(c=>!['money','number','percent'].includes(c.type)),value=cols.find(c=>c.type==='money')||cols.find(c=>['number','percent'].includes(c.type));
    if(!label||!value)return null;
    const valid=(panel.rows||[]).filter(r=>r[value.key]!=null&&r[value.key]!==''&&Number.isFinite(Number(r[value.key])));
    const rows=(key==='timing'?valid:valid.slice().sort((a,b)=>b[value.key]-a[value.key])).slice(0,key==='timing'?30:8);if(!rows.length)return null;
    return responsiveFigure(panel.title||key,(figure,width)=>{
      const compact=width<680,left=compact?0:Math.min(300,width*.34),right=100;
      const layouts=rows.map(row=>{const name=String(row[label.key]),lines=compact?(root.MentatTheme?.wrapText?.(name,width-4,12,root.MentatTheme.sans)||[name]):[name];return {name,lines,pitch:compact?76+(lines.length-1)*16:48};});
      let cursor=18;for(const layout of layouts){layout.y=cursor;cursor+=layout.pitch;}const height=cursor+18;
      const low=Math.min(0,...rows.map(r=>r[value.key])),high=Math.max(0,...rows.map(r=>r[value.key])),span=high-low||1,space=width-left-right,zero=left-low/span*space;
      const svg=svgNode('svg',{viewBox:`0 0 ${width} ${height}`,width,height,role:'img','aria-label':(panel.title||key)+' · '+value.label});
      svg.append(svgNode('line',{x1:zero,x2:zero,y1:0,y2:height-24,class:'insights-axis'}));
      rows.forEach((row,i)=>{const amount=row[value.key],{name,y,lines}=layouts[i],by=compact?y+(lines.length-1)*16+25:y-12;
        const text=svgNode('text',{x:0,y});(compact?lines:[name.length>Math.floor(left/7)?name.slice(0,Math.floor(left/7)-2)+'…':name]).forEach((line,index)=>text.append(svgNode('tspan',{x:0,dy:index?16:0},line)));text.append(svgNode('title',{},name));svg.append(text);
        if(row.funding_source)svg.append(svgNode('text',{x:0,y:y+(lines.length-1)*16+16,class:'insights-channel-label'},fundingLabel(row.funding_source)));
        const rect=svgNode('rect',{x:Math.min(zero,zero+amount/span*space),y:by,width:Math.abs(amount/span*space),height:20,fill:amount<0?'#ac7180':'#327A7A'});
        chartMark(svg,rect,key,row,name,amount,value,row.filters);
        svg.append(svgNode('text',{x:width,y:by+15,'text-anchor':'end'},value.type==='money'?compactMoney(amount):display(amount,value)));
      });
      svg.append(svgNode('text',{x:zero,y:height-5},value.type==='money'?'$0':'0'));
      figure.append(svg,node('figcaption',value.label+' · '+rows.length+' of '+(panel.rows||[]).length+' observed rows. Select a mark for exact source records.'));
    });
  }
  function channelTrends(key,panel){
    const host=node('div'),channels=[...new Set(panel.rows.map(r=>r.funding_source))],select=node('select'),control=node('label','Funding source','insights-chart-filter');select.setAttribute('aria-label','Trend chart funding source');
    channels.forEach(c=>select.append(new Option(fundingLabel(c),c)));if(channels.includes(chartChannels.trends))select.value=chartChannels.trends;
    control.append(select);host.append(control);
    const figure=responsiveFigure('Cycle comparison',(figure,width)=>{
      const rows=panel.rows.filter(r=>r.funding_source===select.value).sort((a,b)=>String(a.cycle).localeCompare(String(b.cycle))),compact=width<600,left=compact?0:115,right=compact?92:130,space=width-left-right,pitch=compact?108:106,height=Math.max(320,rows.length*pitch+48);
      const numbers=rows.flatMap(r=>[r.amount_cents,r.matched_amount_cents]).filter(v=>v!=null),low=Math.min(0,...numbers),high=Math.max(0,...numbers),span=high-low||1,zero=left-low/span*space;
      const svg=svgNode('svg',{viewBox:`0 0 ${width} ${height}`,width,height,role:'img','aria-label':'Full observed and same-stage net amounts by election cycle'});
      for(let i=0;i<=4;i++){const x=left+i*space/4;svg.append(svgNode('line',{x1:x,x2:x,y1:8,y2:height-30,class:'insights-axis'}),svgNode('text',{x,y:height-8,'text-anchor':i===0?'start':i===4?'end':'middle'},compactMoney(low+i*span/4)));}
      rows.forEach((row,i)=>{
        const y=i*pitch+26;svg.append(svgNode('text',{x:0,y},row.cycle));
        for(const [j,field,name,color]of [[0,'amount_cents','Full observed','#57447B'],[1,'matched_amount_cents','Same-stage','#327A7A']]){
          const amount=row[field],by=y+(compact?20:0)+j*26-12;
          if(amount==null){svg.append(svgNode('text',{x:left+8,y:by+15},name+': unavailable'));continue;}
          const rect=svgNode('rect',{x:Math.min(zero,zero+amount/span*space),y:by,width:Math.abs(amount/span*space),height:19,fill:amount<0?'#ac7180':color});
          chartMark(svg,rect,'trends',row,row.cycle+' · '+name+' · '+fundingLabel(select.value)+(j===1?' · cutoff '+(row.matched_through||'unavailable'):''),amount,{type:'money'},j===1?row.matched_filters:row.filters);
          svg.append(svgNode('text',{x:width,y:by+15,'text-anchor':'end'},compactMoney(amount)));
        }
      });
      const legend=node('div',undefined,'insights-chart-legend');for(const [label,color]of [['Full observed net','#57447B'],['Same election-stage net','#327A7A']]){const entry=node('span'),swatch=node('i');swatch.style.background=color;entry.append(swatch,document.createTextNode(label));legend.append(entry);}
      figure.append(svg,legend,node('figcaption','Cycle-level observations · '+fundingLabel(select.value)+'. No monthly interpolation. Matching cutoffs does not establish matching filing coverage.'));
    });host.append(figure);
    select.onchange=()=>{chartChannels.trends=select.value;plotDrawers.get(figure)?.(Math.max(240,figure.clientWidth));};return host;
  }
  function waterfall(panel){
    const host=node('div'),cards=panel.cards||[],select=node('select'),label=node('label','Funding source','insights-chart-filter');select.setAttribute('aria-label','Change chart funding source');
    for(const card of cards)select.append(new Option(fundingLabel(card.funding_source),card.funding_source));if(cards.some(c=>c.funding_source===chartChannels.changes))select.value=chartChannels.changes;label.append(select);if(cards.length>1)host.append(label);
    for(const card of cards){
      const components=(panel.rows||[]).filter(r=>r.funding_source===card.funding_source);if(!components.length)continue;
      const reconciled=Number.isSafeInteger(card.baseline_cents)&&Number.isSafeInteger(card.current_cents)&&components.every(r=>Number.isSafeInteger(r.change_cents))&&card.baseline_cents+components.reduce((n,r)=>n+r.change_cents,0)===card.current_cents;
      if(!reconciled){host.append(node('p','Change components do not reconcile; see exact returned values in the table.','insights-notice'));continue;}
      const figure=responsiveFigure('Change waterfall',(figure,width)=>{
        let running=card.baseline_cents;const bars=[{label:'Baseline',from:0,to:running,amount:running,total:true}];
        for(const row of components){bars.push({label:row.component.replace(' observed companies',' observed').replace(' companies',''),from:running,to:running+row.change_cents,amount:row.change_cents,row});running+=row.change_cents;}
        bars.push({label:'Current',from:0,to:card.current_cents,amount:card.current_cents,total:true});
        const height=300,left=12,right=12,top=34,bottom=92,low=Math.min(0,...bars.flatMap(b=>[b.from,b.to])),high=Math.max(1,...bars.flatMap(b=>[b.from,b.to])),step=(width-left-right)/bars.length,bw=step*.6,y=n=>top+(high-n)/(high-low)*(height-top-bottom);
        const svg=svgNode('svg',{viewBox:`0 0 ${width} ${height}`,width,height,role:'img','aria-label':'Change waterfall for '+fundingLabel(card.funding_source)});
        svg.append(svgNode('line',{x1:left,x2:width-right,y1:y(0),y2:y(0),class:'insights-axis'}));
        bars.forEach((bar,i)=>{const x=left+i*step+(step-bw)/2,rect=svgNode('rect',{x,y:y(Math.max(bar.from,bar.to)),width:bw,height:Math.abs(y(bar.from)-y(bar.to)),class:bar.amount<0?'insights-bar-negative':bar.total?'insights-waterfall-total':'insights-bar'});chartMark(svg,rect,'changes',bar.row||{},bar.label,bar.amount,{type:'money'},bar.row?.filters);
          svg.append(svgNode('text',{x:x+bw/2,y:y(Math.max(bar.from,bar.to))-10,'text-anchor':'middle'},compactMoney(bar.amount)));
          if(i<bars.length-1)svg.append(svgNode('line',{x1:x+bw,x2:x+step,y1:y(bar.to),y2:y(bar.to),class:'insights-connector'}));
          const text=svgNode('text',{x:x+bw/2,y:height-bottom+22,'text-anchor':'middle'});bar.label.split(' ').forEach((word,j)=>text.append(svgNode('tspan',{x:x+bw/2,dy:j?16:0},word)));svg.append(text);
        });figure.append(svg,node('figcaption',fundingLabel(card.funding_source)+': '+money.format(card.baseline_cents/100)+' → '+money.format(card.current_cents/100)+'. Reconciled in signed cents. Observation changes do not establish changes in intent.'));
      });figure.dataset.channel=card.funding_source;figure.hidden=card.funding_source!==select.value;host.append(figure);
    }
    select.onchange=()=>{chartChannels.changes=select.value;for(const f of host.querySelectorAll('figure')){f.hidden=f.dataset.channel!==select.value;if(!f.hidden)plotDrawers.get(f)?.(Math.max(240,f.clientWidth));}};return host;
  }
  function closeSources(restoreFocus=false) { sourceRevision++; if (sourceRequest) sourceRequest.abort(); sourceRequest = null; sourceContext = null; el('sources').hidden = true; el('sources-table').replaceChildren();if(restoreFocus){document.querySelectorAll('.insights-mark[aria-pressed]').forEach(mark=>mark.removeAttribute('aria-pressed'));if(sourceReturnFocus?.isConnected)sourceReturnFocus.focus();}sourceReturnFocus=null; }
  function openSources(key,row,label,trigger) {
    closeSources(); if (!result) return;
    const resolved = {...result._request};
    // Automatic cycle/cutoff choices become explicit in the evidence request.
    for (const field of ['dataset','basis','company','funding_source','as_of','baseline_cycle','current_cycle','comparison_dataset']) if (Object.prototype.hasOwnProperty.call(result.scope || {},field)) { if(result.scope[field]===null || result.scope[field]==='')delete resolved[field];else resolved[field] = result.scope[field]; }
    delete resolved.retry;
    sourceContext = {query:{...resolved, filters:row.filters,index_token:result.provenance?.index_token}, offset:0};
    sourceReturnFocus=trigger || null;
    el('sources').hidden = false; el('sources-title').textContent = (label || 'Contributing records') + ' · ' + ((result.panels || {})[key]?.title || key);
    el('sources').focus(); loadSources();
  }
  async function loadSources(retry=false) {
    if (!sourceContext || !active) return;
    const ticket = ++sourceRevision; if (sourceRequest) sourceRequest.abort(); sourceRequest = new AbortController();
    const context = sourceContext; el('sources-table').replaceChildren(); el('sources-status').textContent = 'Loading records for the selected analysis row…'; el('sources-retry').hidden = true; el('sources-prev').disabled = true; el('sources-next').disabled = true;
    try {
      const data = await api('/api/insights/records',{...context.query,offset:context.offset,limit:PAGE_SIZE,...(retry===true?{retry:true}:{})},sourceRequest.signal);
      if (ticket !== sourceRevision || !active || !sourceContext) return;
      if (['building','queued','preparing'].includes(data.status)) throw new Error(data.message || 'The record source is still preparing. Retry in a moment.');
      const rows = data.rows || data.records || [];
      const columns = (data.columns || inferredColumns(rows)).map(column=>({...column}));
      for (const [key,label] of [['first_seen_by_insights','First inspected here'],['last_seen_by_insights','Last inspected here']]) {
        const column=columns.find(c=>c.key===key); if(column) column.label=label; else if(rows.some(row=>row[key])) columns.push({key,label,type:'text'});
      }
      if (rows.length) el('sources-table').append(makeTable(columns,rows));
      const total = data.total === undefined ? data.total_rows === undefined ? data.total_records : data.total_rows : data.total;
      el('sources-status').textContent = rows.length ? 'Records ' + (context.offset+1) + '–' + (context.offset+rows.length) + (Number.isFinite(Number(total)) ? ' of ' + total : '') + '. Same industry, basis and contribution cutoff as the analysis.' : 'No source records matched this filter. This does not prove zero giving.';
      el('sources-prev').disabled = context.offset === 0;
      el('sources-next').disabled = data.has_more === undefined ? total === undefined ? rows.length < PAGE_SIZE : context.offset+rows.length >= total : !data.has_more;
      if (data.notices) addNotices(el('sources-table'),data.notices);
      if (rows.some(row=>row.first_seen_by_insights || row.last_seen_by_insights)) el('sources-table').append(node('p','Inspection timestamps describe this workspace’s history, not filing or publication dates.','muted'));
    } catch (error) { if (ticket !== sourceRevision || !active || error.name === 'AbortError') return; el('sources-status').textContent = error.message; el('sources-retry').hidden = false;el('sources-prev').disabled=context.offset===0; }
  }
  function download(kind,panelKey) {
    if (!result) return;
    const clean = {...result}; delete clean._request;
    if(panelKey) clean.panels={[panelKey]:clean.panels[panelKey]};
    const text = kind === 'csv' ? exportCSV(clean) : JSON.stringify({...clean,exported_at:new Date().toISOString()},null,2);
    const blob = new Blob([text],{type:kind === 'csv' ? 'text/csv;charset=utf-8' : 'application/json'}), url = URL.createObjectURL(blob), link = node('a');
    link.href = url; link.download = 'mentat-insights-' + String(result.scope?.dataset || 'industry').replace(/[^a-z0-9_-]/gi,'-') + (panelKey?'-'+panelKey:'') + '.' + kind; document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url),1000);
  }
  const refresh=el('refresh'),pageActions=document.querySelector('#view-insights .analysis-page-actions');if(refresh&&pageActions){refresh.setAttribute('form','insights-controls');pageActions.append(refresh);}
  el('page-sources')?.addEventListener('click',()=>{const details=el('scope').querySelector('details');if(details){details.open=!details.open;if(details.open)details.scrollIntoView({block:'nearest'});}});
  el('analysis-choose')?.addEventListener('click',()=>{el('panel-picker').open=!el('panel-picker').open;el('panel-picker').scrollIntoView({block:'nearest'});});
  el('analysis-overview')?.addEventListener('click',()=>el('results').scrollIntoView({block:'start'}));
  el('analysis-sources')?.addEventListener('click',()=>{if(result)openSources('trends',{filters:[]},'Current analysis scope',el('analysis-sources'));});
  el('controls').addEventListener('submit',event => { event.preventDefault(); if (!el('controls').reportValidity()) return; load(); });
  for (const id of ['dataset','basis','company','funding-source','as-of','baseline-cycle','current-cycle','comparison-dataset']) el(id).addEventListener('change',() => {
    if (id === 'dataset') { resetIndustryFilters();root.MentatScope?.write({industry:el('dataset').value}); }
    load();
  });
  for (const [id,value] of [['enable-all',KEYS],['core-only',CORE],['disable-all',[]]]) el(id).addEventListener('click',() => { enabled = value.slice(); preferences(); renderToggles(); load(); });
  el('retry').addEventListener('click',() => { token = ''; load(true); });
  el('export-csv').addEventListener('click',() => download('csv')); el('export-json').addEventListener('click',() => download('json'));
  el('sources-close').addEventListener('click',()=>closeSources(true)); el('sources-retry').addEventListener('click',()=>loadSources(true));
  el('sources-prev').addEventListener('click',() => { if (sourceContext) { sourceContext.offset = Math.max(0,sourceContext.offset-PAGE_SIZE); loadSources(); } });
  el('sources-next').addEventListener('click',() => { if (sourceContext) { sourceContext.offset += PAGE_SIZE; loadSources(); } });
  renderToggles(); preferences();
  root.MentatInsights = {setActive(value) { const next = Boolean(value); if (next === active) return; active = next; if (active) {adoptSharedIndustry(root.MentatScope?.read());load();} else { invalidate(); status('Open Insights to load the selected analyses.'); } }};
  root.MentatScope?.subscribe(scope=>{if(adoptSharedIndustry(scope) && active)load();});
  // app.js can resolve a direct #insights link before this deferred module runs.
  if (!document.getElementById('view-insights').hidden) root.MentatInsights.setActive(true);
})(typeof window === 'undefined' ? globalThis : window);
