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
    target.append(node('strong', 'Giving selection: ' + (dataset && dataset.label || scope.dataset || 'Selected industry') + ' · ' + (scope.basis_label || scope.basis || 'Accounting basis not supplied')));
    const parts = ['Through ' + (scope.as_of || 'latest available date'), scope.company || 'All covered companies', scope.funding_source ? fundingLabel(scope.funding_source) : 'All funding sources'];
    if (scope.baseline_cycle || scope.current_cycle) parts.push('Cycles: ' + (scope.baseline_cycle || 'automatic') + ' → ' + (scope.current_cycle || 'automatic'));
    if (scope.comparison_dataset) parts.push('Industry comparison: ' + scope.comparison_dataset);
    target.append(node('div', parts.join(' · ')));
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
    el('results').replaceChildren();
    for (const key of enabled) renderPanel(key, (data.panels || {})[key] || {status:'unavailable',summary:'This analysis was not returned by the source.'});
    const count = enabled.filter(key => (data.panels || {})[key]?.rows?.length).length;
    status(count ? count + ' analyses contain results.' : 'Analysis complete. No observed rows are available for this selection; missing evidence does not establish zero activity.');
    exporting(true);
  }
  function renderPanel(key, panel) {
    const card = node('article', undefined, 'panel insights-card'); card.id = 'insights-panel-' + key;
    if (!CORE.includes(key) && (panel.columns || []).length > 6) card.classList.add('insights-card-wide');
    const heading = node('div',undefined,'insights-panel-heading'), title = node('h3',key==='trends'?'Giving trends':panel.title || PANELS.find(p => p[0] === key)[1]); title.id = card.id + '-title'; card.setAttribute('aria-labelledby',title.id);
    const badge = node('span',STATUS_LABELS[panel.status || 'observed'] || (panel.status || 'observed').replace(/_/g,' '),'insights-panel-badge'); badge.dataset.status = panel.status || 'observed'; heading.append(title,badge); card.append(heading);
    if (panel.summary) card.append(node('p',noticeText(panel.summary),'insights-card-summary'));
    let rows = (panel.rows || []).slice();
    if (!rows.length) card.append(node('p',panel.message || 'No observed records for this analysis in the selected scope.','insights-empty'));
    else {
      const chart = makeChart(key,panel); if (chart) {const area=node('div',undefined,'insights-chart-area');area.append(chart);card.append(area);}
      const tableHost = node('div');
      const renderTable = () => {
        const sort=sorts[key], previous=tableHost.firstElementChild, scrollLeft=previous?.scrollLeft || 0, scrollTop=previous?.scrollTop || 0;
        if(sort)rows.sort((a,b)=>{const av=a[sort.key],bv=b[sort.key];if(av===null||av===undefined)return bv===null||bv===undefined?0:1;if(bv===null||bv===undefined)return -1;return(typeof av==='number'&&typeof bv==='number'?av-bv:String(av).localeCompare(String(bv),undefined,{numeric:true}))*sort.direction;});
        tableHost.replaceChildren(makeTable(panel.columns || [],rows,{key,sort,onSort:column=>{sorts[key]={key:column.key,direction:sort&&sort.key===column.key?-sort.direction:-1};renderTable();Array.from(tableHost.querySelectorAll('.insights-sort')).find(button=>button.dataset.column===column.key)?.focus({preventScroll:true});}}));
        tableHost.firstElementChild.scrollLeft=scrollLeft;tableHost.firstElementChild.scrollTop=scrollTop;
      };
      renderTable(); card.append(tableHost);
      const tools=node('div',undefined,'insights-card-tools'), tableButton=node('button','Table','secondary'), exportButton=node('button','Export','secondary');
      tableHost.hidden=Boolean(chart) && !tablesShown[key];
      tableButton.type='button'; tableButton.setAttribute('aria-expanded',String(!tableHost.hidden)); tableHost.id='insights-table-'+key; tableButton.setAttribute('aria-controls',tableHost.id);
      tableButton.addEventListener('click',()=>{tableHost.hidden=!tableHost.hidden;tablesShown[key]=!tableHost.hidden;tableButton.setAttribute('aria-expanded',String(!tableHost.hidden));});
      exportButton.type='button'; exportButton.setAttribute('aria-label','Export '+title.textContent+' as CSV'); exportButton.addEventListener('click',()=>download('csv',key)); tools.append(tableButton,exportButton); heading.append(tools);
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
  function makeChart(key,panel) {
    if (!['favorites','concentration','trends','timing','changes'].includes(key)) return null;
    if (key === 'changes' && panel.cards?.some(card => card.baseline_cents !== undefined)) return waterfall(panel);
    if (['trends','timing'].includes(key) && panel.rows?.some(row => row.funding_source && (row.cycle || row.month))) return channelTrends(key,panel);
    if (key === 'concentration' && panel.rows?.some(row=>row.dimension && row.name)) {
      const host=node('div');
      for(const dimension of [...new Set(panel.rows.map(row=>row.dimension))]) {
        const rows=panel.rows.filter(row=>row.dimension===dimension), columns=[{key:'name',label:dimension,type:'text'},...(panel.columns || []).filter(c=>c.key!=='name' && c.key!=='dimension')];
        const chart=makeChart('favorites',{...panel,title:dimension+' concentration',rows,columns}); if(chart) {chart.prepend(node('p',dimension+' concentration','muted'));host.append(chart);}
      }
      return host;
    }
    const columns = panel.columns || [], label = columns.find(c => c.key === (key === 'concentration' ? 'name' : key === 'changes' ? 'component' : key === 'favorites' ? 'recipient' : 'cycle')) || columns.find(c => !['money','number','percent'].includes(c.type));
    const value = columns.find(c => c.type === 'money') || columns.find(c => ['number','percent'].includes(c.type));
    if (!label || !value) return null;
    const rows = (panel.rows || []).filter(row => row[value.key] !== null && row[value.key] !== '' && Number.isFinite(Number(row[value.key]))).slice(0,['trends','timing'].includes(key) ? 30 : 8);
    if (!rows.length) return null;
    const figure = node('figure',undefined,'insights-chart'), svg = svgNode('svg',{role:'img','aria-label':(panel.title || key) + ': ' + value.label + ' by ' + label.label});
    const max = Math.max(1,...rows.map(r => Math.abs(Number(r[value.key]))));
    if (['trends','timing'].includes(key) && rows.length > 1) {
      const width = 600, height = 200, left = 65, right = 25, top = 18, bottom = 43;
      const low = Math.min(0,...rows.map(r => Number(r[value.key]))), high = Math.max(1,...rows.map(r => Number(r[value.key])));
      const x = i => left + i / (rows.length - 1) * (width-left-right), y = n => top + (high-n)/(high-low)*(height-top-bottom);
      svg.setAttribute('viewBox',`0 0 ${width} ${height}`); svg.append(svgNode('line',{x1:left,x2:width-right,y1:y(0),y2:y(0),class:'insights-axis'}));
      svg.append(svgNode('text',{x:left-8,y:top+4,'text-anchor':'end'},display(high,value)),svgNode('text',{x:left-8,y:height-bottom+4,'text-anchor':'end'},display(low,value)));
      svg.append(svgNode('polyline',{points:rows.map((r,i) => x(i)+','+y(Number(r[value.key]))).join(' '),class:'insights-line'}));
      rows.forEach((r,i) => { const dot = svgNode('circle',{cx:x(i),cy:y(Number(r[value.key])),r:4,class:'insights-dot'}); dot.append(svgNode('title',{},String(r[label.key]) + ': ' + display(r[value.key],value))); svg.append(dot); if (i === 0 || i === rows.length-1 || rows.length < 7) svg.append(svgNode('text',{x:x(i),y:height-16,'text-anchor':'middle'},String(r[label.key]).slice(0,18))); });
    } else {
      const width = 640, left = 220, end = 520, height = rows.length * 48 + 12, negatives = rows.some(row => Number(row[value.key]) < 0), zero = negatives ? left + (end-left)/2 : left, available = negatives ? (end-left)/2 : end-left;
      svg.setAttribute('viewBox',`0 0 ${width} ${height}`); svg.append(svgNode('line',{x1:zero,x2:zero,y1:0,y2:height,class:'insights-axis'}));
      rows.forEach((r,i) => {
        const amount=Number(r[value.key]),size=Math.abs(amount)/max*available,y=i*48+7,name=String(r[label.key]),fullName=name+(r.funding_source?' · '+fundingLabel(r.funding_source):'');
        const text=svgNode('text',{x:left-10,y:y+13,'text-anchor':'end'},name.length>20?name.slice(0,19)+'…':name);text.append(svgNode('title',{},fullName));
        if(r.funding_source)text.append(svgNode('tspan',{x:left-10,dy:18,style:'font-size:16px'},fundingLabel(r.funding_source)));
        const rect=svgNode('rect',{x:amount<0?zero-size:zero,y,width:size,height:29,rx:2,class:amount<0?'insights-bar-negative':'insights-bar'});rect.append(svgNode('title',{},fullName+': '+display(amount,value)));
        const shown=value.type==='money' && Math.abs(amount)>=100000000 ? new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',notation:'compact',maximumFractionDigits:1}).format(amount/(value.unit==='dollars'?1:100)) : display(amount,value);
        svg.append(text,rect,svgNode('text',{x:end+10,y:y+21},shown));
      });
    }
    figure.append(svg,node('figcaption',(value.label || value.key) + (rows.length < (panel.rows || []).length ? ' · first '+rows.length+' rows' : '') + ' · Exact values in table.')); return figure;
  }
  function channelTrends(key,panel) {
    const amountKey=key==='trends' && panel.rows.some(row=>row.matched_amount_cents!==null && row.matched_amount_cents!==undefined) ? 'matched_amount_cents' : 'amount_cents';
    const labelKey=key==='trends'?'cycle':'month', value=(panel.columns || []).find(c=>c.key===amountKey)||{key:amountKey,label:'Net amount',type:'money'};
    const all=panel.rows.filter(row=>row[amountKey]!==null && row[amountKey]!==undefined && Number.isFinite(Number(row[amountKey])));
    const labels=[...new Set(all.map(row=>String(row[labelKey])))].sort(), channels=[...new Set(all.map(row=>row.funding_source))];
    if(!labels.length) return null;
    const width=610,height=230,left=80,right=22,top=20,bottom=49,low=Math.min(0,...all.map(row=>row[amountKey])),high=Math.max(1,...all.map(row=>row[amountKey]));
    const x=label=>left+(labels.length===1?.5:labels.indexOf(label)/(labels.length-1))*(width-left-right), y=amount=>top+(high-amount)/(high-low)*(height-top-bottom);
    const figure=node('figure',undefined,'insights-chart'), svg=svgNode('svg',{viewBox:`0 0 ${width} ${height}`,role:'img','aria-label':value.label+' by '+labelKey+', separate lines for each funding source'}),legend=node('div',undefined,'insights-chart-legend');
    const compact=new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',notation:'compact',maximumFractionDigits:1});
    svg.append(svgNode('line',{x1:left,x2:width-right,y1:y(0),y2:y(0),class:'insights-axis'}),svgNode('text',{x:left-8,y:top+4,'text-anchor':'end'},compact.format(high/100)),svgNode('text',{x:left-8,y:height-bottom+4,'text-anchor':'end'},compact.format(low/100)));
    const palette=['#57447b','#327a7a','#ac7180','#bd8721','#4b7194'];
    channels.forEach((channel,index)=>{
      const color=palette[index%palette.length], points=all.filter(row=>row.funding_source===channel).sort((a,b)=>String(a[labelKey]).localeCompare(String(b[labelKey]))), segments=[]; let segment=[];
      for(const row of points){const previous=segment[segment.length-1],distance=previous ? key==='timing' ? (Number(String(row.month).slice(0,4))-Number(String(previous.month).slice(0,4)))*12+Number(String(row.month).slice(5))-Number(String(previous.month).slice(5)) : Number(String(row.cycle).slice(-4))-Number(String(previous.cycle).slice(-4)) : 0;if(previous && distance>(key==='timing'?1:2)){segments.push(segment);segment=[];}segment.push(row);}if(segment.length)segments.push(segment);
      for(const group of segments) if(group.length>1) svg.append(svgNode('polyline',{points:group.map(row=>x(String(row[labelKey]))+','+y(Number(row[amountKey]))).join(' '),fill:'none',stroke:color,'stroke-width':2.5}));
      points.forEach(row=>{const dot=svgNode('circle',{cx:x(String(row[labelKey])),cy:y(Number(row[amountKey])),r:4,fill:color});dot.append(svgNode('title',{},fundingLabel(channel)+' · '+row[labelKey]+': '+display(row[amountKey],value)));svg.append(dot);});
      const item=node('span'),swatch=node('i');swatch.style.backgroundColor=color;item.append(swatch,document.createTextNode(fundingLabel(channel)));legend.append(item);
    });
    labels.forEach((label,index)=>{if(index===0||index===labels.length-1||labels.length<=5)svg.append(svgNode('text',{x:x(label),y:height-18,'text-anchor':'middle'},label));});
    figure.append(svg,legend,node('figcaption',value.label+' · Missing periods remain gaps.'));return figure;
  }
  function waterfall(panel) {
    const host=node('div'),cards=panel.cards || [],select=node('select'),label=node('label','Funding source','insights-chart-filter');
    select.setAttribute('aria-label','Change chart funding source');
    for(const card of cards)select.append(new Option(fundingLabel(card.funding_source),card.funding_source));
    if(cards.some(card=>card.funding_source===chartChannels.changes))select.value=chartChannels.changes;
    label.append(select);if(cards.length>1)host.append(label);
    for(const card of panel.cards || []) {
      const components=(panel.rows || []).filter(row=>row.funding_source===card.funding_source);if(!components.length)continue;
      let running=card.baseline_cents;const bars=[{label:'Baseline',from:0,to:running,amount:running,total:true}];
      for(const row of components){bars.push({label:row.component.replace(' observed companies','').replace(' companies',''),from:running,to:running+row.change_cents,amount:row.change_cents});running+=row.change_cents;}
      bars.push({label:'Current',from:0,to:card.current_cents,amount:card.current_cents,total:true});
      const width=640,height=240,left=20,right=20,top=35,bottom=60,low=Math.min(0,...bars.flatMap(b=>[b.from,b.to])),high=Math.max(1,...bars.flatMap(b=>[b.from,b.to])),step=(width-left-right)/bars.length,bw=step*.58,y=n=>top+(high-n)/(high-low)*(height-top-bottom);
      const figure=node('figure',undefined,'insights-chart'),svg=svgNode('svg',{viewBox:`0 0 ${width} ${height}`,role:'img','aria-label':'Change waterfall for '+fundingLabel(card.funding_source)}),compact=new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',notation:'compact',maximumFractionDigits:1});figure.dataset.channel=card.funding_source;figure.hidden=card.funding_source!==select.value;
      svg.append(svgNode('line',{x1:left,x2:width-right,y1:y(0),y2:y(0),class:'insights-axis'}));
      bars.forEach((bar,index)=>{const x=left+index*step+(step-bw)/2; const rect=svgNode('rect',{x,y:y(Math.max(bar.from,bar.to)),width:bw,height:Math.max(1,Math.abs(y(bar.from)-y(bar.to))),rx:2,class:bar.total?'insights-waterfall-total':bar.amount<0?'insights-bar-negative':'insights-bar'});rect.append(svgNode('title',{},bar.label+': '+money.format(bar.amount/100)));svg.append(rect,svgNode('text',{x:x+bw/2,y:y(Math.max(bar.from,bar.to))-9,'text-anchor':'middle'},compact.format(bar.amount/100)));if(index<bars.length-1)svg.append(svgNode('line',{x1:x+bw,x2:x+step,y1:y(bar.to),y2:y(bar.to),class:'insights-connector'}));const label=svgNode('text',{x:x+bw/2,y:height-bottom+20,'text-anchor':'middle'});const words=bar.label.split(' ');words.forEach((word,j)=>label.append(svgNode('tspan',{x:x+bw/2,dy:j?23:0},word)));svg.append(label);});
      if(cards.length===1)figure.append(node('p',fundingLabel(card.funding_source),'muted'));
      figure.append(svg,node('figcaption',fundingLabel(card.funding_source)+': '+money.format(card.baseline_cents/100)+' → '+money.format(card.current_cents/100)+'.'+(card.reconciled?' Reconciled.':'')));host.append(figure);
    }
    select.addEventListener('change',()=>{chartChannels.changes=select.value;for(const figure of host.querySelectorAll('figure'))figure.hidden=figure.dataset.channel!==select.value;});
    return host;
  }
  function closeSources(restoreFocus=false) { sourceRevision++; if (sourceRequest) sourceRequest.abort(); sourceRequest = null; sourceContext = null; el('sources').hidden = true; el('sources-table').replaceChildren();if(restoreFocus && sourceReturnFocus?.isConnected)sourceReturnFocus.focus();sourceReturnFocus=null; }
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
