const $ = id => document.getElementById(id);
const renderedHtml = new Map();
function setHtml(id, html) { if (renderedHtml.get(id) !== html) { $(id).innerHTML = html; renderedHtml.set(id, html); } }
let token = '', upload = null, selectedRun = '', selectedLane = '', busy = false, warningIds = [];
let rosterRevision = 0, companySequence = 0, currentView = 'loading';
const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const number = value => value == null ? '—' : Number(value).toLocaleString();
const label = value => String(value || '').replaceAll('_', ' ');
const duration = value => value == null ? '—' : value < 60 ? '<1 min' : value < 3600 ? Math.ceil(value / 60) + ' min' : (value / 3600).toFixed(1) + ' hr';
function showError(message) { $('error').textContent = message; $('error').hidden = !message; }
function showView(view, focus = false) {
  currentView = ['loading', 'collection', 'evidence'].includes(view) ? view : 'loading';
  for (const name of ['loading', 'collection', 'evidence']) {
    const active = name === currentView;
    $('view-' + name).hidden = !active;
    $('tab-' + name).setAttribute('aria-selected', String(active));
    $('tab-' + name).tabIndex = active ? 0 : -1;
  }
  $('workspace-title').textContent = {loading:'Load a sector',collection:'Collection monitor',evidence:'Follow PAC spending'}[currentView];
  $('stage').hidden = currentView !== 'collection';
  history.replaceState(null, '', '#' + currentView);
  if (focus) $('tab-' + currentView).focus();
}
document.querySelector('.workspace-tabs').addEventListener('click', event => {
  const tab = event.target.closest('[role=tab]'); if (tab) showView(tab.id.slice(4));
});
window.addEventListener('hashchange', () => showView(location.hash.slice(1)));
document.querySelector('.workspace-tabs').addEventListener('keydown', event => {
  const names = ['loading','collection','evidence'], index = names.indexOf(currentView);
  const next = {ArrowRight:(index + 1) % 3, ArrowLeft:(index + 2) % 3, Home:0, End:2}[event.key];
  if (next != null) { event.preventDefault(); showView(names[next], true); }
});
function draftData() {
  return {sector:$('sector').value, companies:[...document.querySelectorAll('.company-entry')].map(row => ({
    name:row.querySelector('.company-name').value,
    aliases:row.querySelector('.company-aliases').value.split(/\r?\n/).map(value => value.trim()).filter(Boolean)
  }))};
}
function invalidateRoster() {
  rosterRevision++; upload = null; $('start').disabled = true; $('start').textContent = 'Start collection';
  $('upload-review').hidden = true; $('review-placeholder').hidden = false;
  try { localStorage.setItem('mentat-roster-draft-v1', JSON.stringify(draftData()));
    $('draft-status').textContent = 'Draft saved in this browser. Review it when ready.';
  } catch { $('draft-status').textContent = 'Browser storage unavailable. Keep this tab open until you review your roster.'; }
}
function addCompany(company = {name:'',aliases:[]}) {
  const id = ++companySequence, row = document.createElement('div'); row.className = 'company-entry';
  row.innerHTML = `<div class="company-entry-heading"><strong>Company</strong><button type="button" class="remove-company" aria-label="Remove company">Remove</button></div><label class="field" for="company-${id}">Company name</label><input id="company-${id}" class="company-name" type="text" required maxlength="250" placeholder="e.g. Coinbase" value="${escapeHtml(company.name)}"><label class="field" for="aliases-${id}">Alternative names <span>One name per line · optional</span></label><textarea id="aliases-${id}" class="company-aliases" rows="3" placeholder="e.g. Coinbase Inc.&#10;Coinbase Global Inc.">${escapeHtml(company.aliases.join('\n'))}</textarea>`;
  $('company-editor').append(row); numberCompanies(); return row;
}
function numberCompanies() {
  const rows = [...document.querySelectorAll('.company-entry')];
  rows.forEach((row,index) => { row.querySelector('strong').textContent = `Company ${index + 1}`;
    row.querySelector('button').disabled = rows.length === 1;
    row.querySelector('button').setAttribute('aria-label', `Remove company ${index + 1}`); });
  $('add-company').disabled = rows.length >= 1000;
}
function restoreDraft() {
  try {
    const draft = JSON.parse(localStorage.getItem('mentat-roster-draft-v1') || 'null');
    if (draft && typeof draft.sector === 'string' && Array.isArray(draft.companies) && draft.companies.length <= 1000 && draft.companies.every(c => typeof c.name === 'string' && Array.isArray(c.aliases) && c.aliases.every(a => typeof a === 'string'))) {
      $('sector').value = draft.sector; draft.companies.forEach(addCompany);
    }
  } catch { /* An invalid or unavailable local draft never prevents a fresh roster. */ }
  if (!$('company-editor').children.length) addCompany();
}
$('roster-form').addEventListener('input', invalidateRoster);
$('add-company').addEventListener('click', () => { const row = addCompany(); invalidateRoster(); row.querySelector('input').focus(); });
$('company-editor').addEventListener('click', event => {
  if (!event.target.closest('.remove-company')) return;
  event.target.closest('.company-entry').remove(); numberCompanies(); invalidateRoster();
});
async function acceptRoster(value, revision) {
  if (revision !== rosterRevision) return;
  upload = value; roster(value.readiness); selectedRun = value.id; selectedLane = '';
  $('start').textContent = 'Start collection';
  $('draft-status').textContent = value.state === 'ready' ? 'Roster validated and saved. Choose cycles, then start collection.' : 'Review the name conflicts before starting.';
  await refreshRuns(); await refreshRun();
}
$('roster-form').addEventListener('submit', async event => {
  event.preventDefault(); showError(''); const revision = ++rosterRevision;
  upload = null; $('start').disabled = true; $('review-roster').disabled = true; $('review-roster').textContent = 'Checking names…';
  try { await acceptRoster(await api('/api/roster', draftData()), revision); }
  catch (error) { if (revision === rosterRevision) showError(error.message); }
  finally { $('review-roster').disabled = false; $('review-roster').textContent = 'Review roster'; }
});
async function api(path, data) {
  const response = await fetch(path, data === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json','X-Mentat-Token':token}, body:JSON.stringify(data)});
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || 'The request could not be completed.');
  return body;
}
function roster(readiness) {
  $('upload-review').hidden = false;
  $('review-placeholder').hidden = true;
  const groups = readiness.readiness || [];
  const count = groups.reduce((n,g) => n + g.company_count, 0);
  const variants = groups.reduce((n,g) => n + g.variant_count, 0);
  $('roster-counts').textContent = `${count} ${count === 1 ? 'company' : 'companies'} · ${variants} search names · ${groups.length} ${groups.length === 1 ? 'sector' : 'sectors'}`;
  $('roster-list').innerHTML = groups.map(group => `<h3>${escapeHtml(group.industry)}</h3>` + group.companies.map(company => `<div class="roster-company"><b>${escapeHtml(company.company)}</b><small>${company.variants.map(v => escapeHtml(v.variant)).join(' · ')}</small>${company.exclusions.length ? '<small>Exclude: ' + company.exclusions.map(escapeHtml).join(', ') + '</small>' : ''}</div>`).join('') + (group.ready ? '' : `<p class="error">Resolve ambiguous names or invalid blocks: ${escapeHtml(JSON.stringify({duplicates:group.duplicate_companies,ambiguous:group.cross_company_variants,errors:group.parse_errors}))}</p>`)).join('');
  $('start').disabled = readiness.status !== 'succeeded';
}
$('file').addEventListener('change', async () => {
  const file = $('file').files[0]; if (!file) return;
  showError(''); $('start').disabled = true; upload = null; const revision = ++rosterRevision;
  try {
    if (file.size > 5000000) throw new Error('Upload a file smaller than 5 MB.');
    const content = await new Promise((resolve,reject) => { const reader = new FileReader(); reader.onload = () => resolve(reader.result.split(',')[1]); reader.onerror = reject; reader.readAsDataURL(file); });
    await acceptRoster(await api('/api/upload', {filename:file.name,content}), revision);
  } catch (error) { if (revision === rosterRevision) showError(error.message); }
});
$('save-keys').addEventListener('click', async () => {
  try { const result = await api('/api/keys', {keys:$('api-key').value}); $('api-key').value = ''; $('key-hint').textContent = `${result.active_key_count} enabled keys; ${result.stored_key_count - result.active_key_count} disabled. Saved with Windows encryption.`; } catch (error) { showError(error.message); }
});
$('clear-quality').addEventListener('click', async () => {
  try { await api('/api/quality/acknowledge', {id:selectedRun, warning_ids:warningIds}); await refreshRun(); }
  catch (error) { showError(error.message); }
});
$('start').addEventListener('click', async () => {
  if (!upload) return;
  $('start').disabled = true; $('start').textContent = 'Starting…'; showError('');
  try {
    await api('/api/start', {id:upload.id, cycles:[...document.querySelectorAll('input[name=cycle]:checked')].map(c => Number(c.value)), api_key:$('api-key').value});
    $('api-key').value = ''; $('start').textContent = 'Collection started'; upload = null;
    showView('collection');
    await refreshRun();
  } catch (error) { showError(error.message); $('start').disabled = false; $('start').textContent = 'Start collection'; }
});
$('runs').addEventListener('change', async () => { selectedRun = $('runs').value; selectedLane = ''; await refreshRun().catch(e => showError(e.message)); });
$('lanes').addEventListener('change', async () => { selectedLane = $('lanes').value; await refreshRun().catch(e => showError(e.message)); });
async function refreshRuns(initial) {
  const body = initial || await api('/api/runs');
  const options = body.runs.map(run => `<option value="${escapeHtml(run.id)}">${escapeHtml(run.name)} · ${escapeHtml(run.state)}</option>`).join('');
  if ($('runs').innerHTML !== options) $('runs').innerHTML = options || '<option value="">No collections yet</option>';
  if (!selectedRun && body.runs.length) selectedRun = body.runs[0].id;
  $('runs').value = selectedRun;
  $('key-status').textContent = body.key_configured ? `${body.active_key_count} enabled FEC keys saved · ${body.stored_key_count - body.active_key_count} disabled` : 'No enabled FEC keys saved';
  if (body.key_configured) $('key-hint').textContent = `${body.active_key_count} enabled keys; ${body.stored_key_count - body.active_key_count} disabled. Stored with Windows encryption. Leave blank to use them.`;
}
function render(run) {
  $('run-title').textContent = run.name;
  const status = run.status || {}, fanout = status.fanout || run.completed_collection || {};
  $('worker-panel').hidden = status.kind === 'report_repair';
  $('records-panel').hidden = status.kind === 'report_repair';
  $('stage').textContent = label(run.state === 'failed' ? 'failed' : status.stage || run.state);
  const assurance = run.assurance || [];
  const passed = assurance.filter(check => check.collection === 'passed').length;
  const failed = assurance.some(check => check.collection === 'failed');
  const oldReports = run.reports.some(report => report.quality?.direction_columns === false);
  const changedReports = run.reports.some(report => report.quality?.matches_run === false);
  const allWarnings = run.reports.flatMap(report => (report.quality?.warnings || []).map(warning => ({...warning, report:report.name})));
  const warnings = allWarnings.filter(warning => !warning.reviewed_at);
  const reviewed = allWarnings.filter(warning => warning.reviewed_at);
  warningIds = warnings.filter(warning => warning.severity !== 'fail').map(warning => warning.id);
  $('clear-quality').hidden = !warningIds.length;
  $('quality-title').textContent = oldReports ? 'Report warning: downstream directions are combined' : failed ? 'Collection coverage checks failed' : passed && passed === assurance.length ? 'Saved collection checks passed · downstream coverage unverified' : 'Collection coverage not yet verified';
  $('quality-detail').textContent = oldReports ? 'An exported workbook lacks separate support and opposition columns. Its party totals may include spending against that party’s candidates.' : changedReports ? 'A workbook has changed since this run. Its current contents do not match the run’s recorded file.' : 'A finished search is not proof that every contribution or downstream transfer was captured.';
  let qualityHtml = assurance.map(check => `<span class="quality-chip">${escapeHtml(check.industry)} · ${escapeHtml(check.collection)}${check.recorded_checks ? ' (' + check.recorded_checks + ' checks)' : ''}</span>`).join('');
  if (warnings.length) {
    $('quality-title').textContent = `${warnings.length} report quality warnings require review`;
    $('quality-detail').textContent = 'The repaired workbooks retain unresolved collection and classification warnings. Open Data Quality in each workbook for the evidence.';
    qualityHtml += `<details><summary>Review ${warnings.length} report warnings</summary>` + warnings.map(warning => `<details><summary>${escapeHtml(warning.report)} · ${escapeHtml(label(warning.check))}</summary><p>${escapeHtml(warning.detail)}</p></details>`).join('') + '</details>';
  }
  if (reviewed.length) {
    if (!warnings.length && !failed && !oldReports && !changedReports) {
      $('quality-title').textContent = 'Saved report warnings reviewed';
      $('quality-detail').textContent = 'The previous notices are cleared. Their evidence remains available below and in each workbook; new or changed report warnings will appear again.';
    }
    qualityHtml += `<details><summary>${reviewed.length} reviewed notices</summary>` + reviewed.map(warning => `<details><summary>${escapeHtml(warning.report)} · ${escapeHtml(label(warning.check))}</summary><p>${escapeHtml(warning.detail)}</p></details>`).join('') + '</details>';
  }
  setHtml('quality-checks', qualityHtml);
  $('quality-title').closest('.quality-panel').classList.toggle('reviewed', !!reviewed.length && !warnings.length && !failed && !oldReports && !changedReports);
  setHtml('source-snapshots', (run.source_snapshots || []).map(source => `<li>${escapeHtml(source.name)}: local file modified ${escapeHtml(source.modified_at.slice(0,10))} (${source.age_days} days ago). This is not a verified data-through date.</li>`).join('') || '<li>No local source file dates available.</li>');
  $('resume-setup').hidden = run.state !== 'ready';
  $('empty').hidden = true; $('monitor').hidden = false;
  if (!run.status) {
    $('freshness').textContent = run.state === 'ready' ? 'Roster validated. Choose cycles and start collection.' : `Run ${label(run.state)}. Waiting for runner status.`;
  } else {
    const terminal = ['completed','failed'].includes(status.stage) || ['completed','failed'].includes(run.state);
    $('freshness').textContent = terminal ? `Last recorded update: ${status.updated_at || 'unavailable'}` : run.age_seconds > 60 ? `No recent worker update · last checkpoint ${duration(run.age_seconds)} ago. The collector may be waiting, paused, or no longer running.` : `Monitoring · refreshed ${new Date().toLocaleTimeString()} · runner update ${number(run.age_seconds)} seconds ago`;
  }
  $('completed').textContent = fanout.total == null ? '—' : `${number(fanout.completed)} / ${number(fanout.total)}`;
  $('workers').textContent = number(fanout.running); $('failed').textContent = number(fanout.failed);
  $('eta').textContent = status.stage === 'completed' ? 'Finished' : status.stage === 'failed' ? 'Stopped' : duration(status.estimated_remaining_seconds);
  $('progress').style.width = fanout.total ? Math.min(100,100 * fanout.completed / fanout.total) + '%' : '0%';
  $('phase-description').textContent = status.current_industry ? `${status.current_industry} · ${label(status.stage)}. Tasks measure company/cycle attempts; successful coverage is verified separately.` : label(status.stage || run.state);
  setHtml('industries', (status.industries || []).map(industry => `<div class="industry"><b>${escapeHtml(industry.industry)}</b> ${escapeHtml(label(industry.stage))}${industry.detail ? '<details><summary>Run details</summary><p>' + escapeHtml(industry.detail) + '</p></details>' : ''}</div>`).join(''));
  const choices = run.lanes.map(lane => `<option value="${escapeHtml(lane.id)}">${escapeHtml(lane.industry)} / ${escapeHtml(lane.label)} / ${escapeHtml(label(lane.state.status))}</option>`).join('') || '<option value="">No workers yet</option>';
  if ($('lanes').innerHTML !== choices) $('lanes').innerHTML = choices;
  selectedLane = run.selected_lane || ''; $('lanes').value = selectedLane;
  const selected = run.lanes.find(l => l.id === selectedLane);
  $('lane-summary').textContent = selected ? `${label(selected.state.status)} · ${selected.state.current_company || 'No current company'} ${selected.state.current_cycle || ''} · ${selected.state.completed || 0}/${selected.state.total || 0} tasks` : 'Waiting for collection workers.';
  const preview = run.preview || {};
  setHtml('checkpoints', (preview.progress || []).map(row => `<tr><td>${escapeHtml(row.company)}</td><td>${escapeHtml(row.cycle)}</td><td>${escapeHtml(label(row.kind))}</td><td>${number(row.rows_seen)}</td><td>${number(row.records_total)}</td><td>${row.stored_complete ? 'Stored' : row.fetched_complete ? 'Fetched' : 'Collecting'}</td></tr>`).join('') || '<tr><td colspan="6">No readable collection checkpoints yet.</td></tr>');
  setHtml('records', (preview.records || []).map(row => `<tr><td>${escapeHtml(row.contributor_name)}<small>${escapeHtml(row.sub_id)}</small></td><td>${escapeHtml(row.company)}<small>${escapeHtml(row.matched_variant)}</small></td><td>${escapeHtml(row.committee_name)}</td><td>${escapeHtml(row.contribution_receipt_date)}</td><td class="number">${row.contribution_receipt_amount == null ? '—' : Number(row.contribution_receipt_amount).toLocaleString('en-US',{style:'currency',currency:'USD'})}</td><td>${escapeHtml(row.company_match_status)}</td></tr>`).join('') || `<tr><td colspan="6">${escapeHtml(preview.message || 'Records will appear as the selected worker stores them.')}</td></tr>`);
  setHtml('events', run.events.slice().reverse().map(event => `<div class="event"><b>${escapeHtml(label(event.event))}</b> ${escapeHtml(event.industry)}<small>${escapeHtml(event.timestamp || event.at || event.time || '')}</small>${escapeHtml(event.detail || event.message || '')}</div>`).join('') || '<p class="muted">No activity recorded yet.</p>');
  setHtml('reports', run.reports.map(report => `<a class="report-link" download="${escapeHtml(report.name)}" href="/api/report?id=${encodeURIComponent(run.id)}&index=${report.index}">${escapeHtml(report.name)} ↗</a><p class="muted">${report.quality?.direction_columns === false ? 'Older layout: support and opposition are combined.' : report.quality?.direction_columns === true ? 'Opposition is shown in a separate column.' : 'Direction columns not verified.'}${report.quality?.matches_run === false ? ' File changed since this run.' : ''}</p>`).join('') || '<p class="muted">Reports appear after collection and validation succeed.</p>');
}
async function refreshRun() {
  if (!selectedRun) return;
  const requested = selectedRun;
  const run = await api('/api/run?id=' + encodeURIComponent(requested) + '&lane=' + encodeURIComponent(selectedLane));
  if (requested === selectedRun) render(run);
}
async function poll() {
  if (busy) return;
  busy = true;
  try { await refreshRuns(); await refreshRun(); $('connection').textContent = '● Local connection'; }
  catch (error) { $('connection').textContent = 'Connection interrupted · retrying'; }
  finally { busy = false; }
}
async function init() {
  try { const session = await api('/api/session'); token = session.token; await refreshRuns(session); await refreshRun(); $('connection').textContent = '● Local connection'; }
  catch (error) { showError(error.message); }
  setInterval(poll, 3000);
}
$('resume-setup').addEventListener('click', async () => {
  try {
    const value = await api('/api/run?id=' + encodeURIComponent(selectedRun));
    if (value.state !== 'ready') throw new Error('This roster is no longer awaiting collection.');
    rosterRevision++; upload = {id:value.id,readiness:value.readiness}; roster(value.readiness);
    $('start').textContent = 'Start collection'; showView('loading');
  } catch (error) { showError(error.message); }
});
let evidence = null;
const currency = value => value == null ? 'Unresolved' : Number(value).toLocaleString('en-US', {style:'currency', currency:'USD', maximumFractionDigits:2});
const sourceAnchor = (url, text) => /^https:\/\/(docquery\.fec\.gov|www\.fec\.gov)\//.test(url || '') ? `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(text)} ↗</a>` : escapeHtml(text);
function renderEvidence() {
  if (!evidence) return;
  const cycle = Number($('evidence-cycle').value), committee = $('evidence-committee').value;
  const finances = evidence.committee_finances.find(row => row.cycle === cycle && row.committee_id === committee);
  const names = new Map(evidence.committee_finances.map(row => [row.committee_id, row.committee_name || row.committee_id]));
  const receipts = evidence.receipts.filter(row => row.cycle === cycle && row.committee_id === committee);
  const contributions = receipts.filter(row => row.included_company_contribution).reduce((sum,row) => sum + row.amount,0);
  const conversions = receipts.filter(row => row.role === 'asset_liquidation').reduce((sum,row) => sum + row.amount,0);
  $('evidence-scope').textContent = `Evidence collected ${evidence.retrieved_at?.slice(0,10) || 'date unavailable'}. ${evidence.scope}`;
  setHtml('evidence-funding', `<div><span>${escapeHtml(evidence.company)} · direct itemized contributions</span><strong>${currency(contributions)}</strong><small>Includes reported in-kind value; excludes personal donations.</small></div><div><span>Exchange proceeds · excluded from contributions</span><strong>${currency(conversions)}</strong><small>Asset conversions are not another donation by the exchange.</small></div><div><span>Committee ending cash · all donors</span><strong>${currency(finances?.ending_cash_as_reported)}</strong><small>Financial summary through ${escapeHtml(finances?.coverage_end || 'unknown')}.</small></div>`);
  const transfers = new Map();
  for (const row of evidence.transfers.filter(row => row.cycle === cycle && row.source === committee)) {
    const prior = transfers.get(row.destination) || {name:row.destination_name,amount:0}; prior.amount += row.amount; transfers.set(row.destination,prior);
  }
  const incoming = new Map();
  for (const row of evidence.transfers.filter(row => row.cycle === cycle && row.destination === committee)) incoming.set(row.source, (incoming.get(row.source) || 0) + row.amount);
  const incomingHtml = incoming.size ? '<h3 class="evidence-subheading">Incoming committee transfers</h3>' + [...incoming].map(([id,amount]) => `<p>${escapeHtml(names.get(id) || id)} → ${escapeHtml(names.get(committee) || committee)} <b>${currency(amount)}</b></p>`).join('') : '';
  setHtml('evidence-transfers', incomingHtml + `<h3 class="evidence-subheading">Outgoing committee transfers</h3>` + ([...transfers].map(([id,row]) => `<p>${escapeHtml(names.get(committee) || committee)} → ${escapeHtml(row.name || names.get(id) || id)} <b>${currency(row.amount)}</b></p>`).join('') || '<p class="muted">No contribution or transfer disbursements found in this snapshot.</p>') + `<p class="muted">${finances?.regular_ie_reconciles ? 'The collected regular-report expenditure total matches the committee financial summary.' : 'The collected regular-report expenditure total differs from the financial summary. Coverage remains unresolved; no donor allocation is calculated.'}</p>`);
  setHtml('evidence-receipts', receipts.map(row => `<tr><td>${escapeHtml(row.reported_name)}<small>${escapeHtml(label(row.role))} · ${row.included_company_contribution ? 'Included contribution' : 'Excluded from company contribution total'}</small></td><td>${escapeHtml(row.date)}</td><td class="number">${currency(row.amount)}</td><td>${sourceAnchor(row.source_url, row.description || 'Original filing')}<small>Line ${escapeHtml(row.line_number)} · ${escapeHtml(row.sub_id)}</small></td></tr>`).join('') || '<tr><td colspan="4">No matching company receipts in this committee and cycle.</td></tr>');
  const candidates = evidence.candidate_activity.filter(row => row.cycle === cycle && row.committee_id === committee).sort((a,b) => b.committee_spending - a.committee_spending);
  const estimate = evidence.cash_estimates?.cycles?.find(row => row.cycle === cycle);
  const candidateEstimates = new Map();
  const candidateKey = row => JSON.stringify([row.candidate_id_as_filed, row.candidate_name_as_filed, row.direction]);
  if (estimate?.status === 'estimated') {
    setHtml('allocation-status', '<div class="allocation-status allocation-ready"><strong>Cash ledger reconciled · conditional estimate available</strong><p>Uses proportional pooling and receipts-before-payments ordering within each day. These are modeling assumptions, not verified donor choices.</p></div>');
    const selected = estimate.allocations.filter(row => row.committee === committee);
    const values = new Map();
    for (const row of selected) {
      const kind = row.kind === 'candidate' ? `candidate · ${row.direction}` : row.kind;
      const value = row.estimated_funding[evidence.company] || 0;
      values.set(kind, (values.get(kind) || 0) + value);
      if (row.kind === 'candidate') candidateEstimates.set(candidateKey(row), (candidateEstimates.get(candidateKey(row)) || 0) + value);
    }
    setHtml('allocation-results', [...values].map(([kind,value]) => `<div class="allocation-result"><span>${escapeHtml(evidence.company)} · estimated ${escapeHtml(label(kind))}</span><strong>${currency(value)}</strong></div>`).join('') + `<div class="allocation-result"><span>Estimated company cash retained</span><strong>${currency(estimate.closing_funding?.[committee]?.[evidence.company] || 0)}</strong></div>`);
  } else {
    const issues = estimate?.issues || [];
    setHtml('allocation-status', `<div class="allocation-status"><strong>Company cash estimate awaits reconciliation</strong><p>${estimate ? 'The saved network does not yet support a balanced, dated cash ledger. An unavailable estimate is not zero.' : 'No verified cash-estimation receipt is available for this snapshot.'}</p>${issues.length ? '<details><summary>' + issues.length + ' outstanding checks across the selected cycle’s network</summary><ul>' + issues.map(issue => `<li><b>${escapeHtml(names.get(issue.committee_id) || issue.committee_id || 'Network')}</b> — ${escapeHtml(issue.detail)}</li>`).join('') + '</ul></details>' : ''}</div>`);
    setHtml('allocation-results', '');
  }
  setHtml('evidence-candidates', candidates.map(row => `<tr><td><details><summary>${escapeHtml(row.candidate_name_as_filed || 'Candidate name missing')}</summary><p>As-filed ID: ${escapeHtml(row.candidate_id_as_filed)}<br>Register: ${escapeHtml(row.registered_candidate_name || 'Unresolved')}<br>${row.identity_status === 'name_matches_registration' ? 'Name matches the candidate register.' : 'Name / ID needs review. Aliases and filing errors can cause differences; no automatic reassignment.'}</p></details></td><td>${escapeHtml(row.direction)}</td><td class="number">${currency(row.committee_spending)}</td><td class="number">${estimate?.status === 'estimated' ? currency(candidateEstimates.get(candidateKey(row)) ?? null) : 'Awaiting reconciliation'}</td><td>${escapeHtml(row.first_date)}<small>to ${escapeHtml(row.last_date)}</small></td><td>${sourceAnchor(row.source_urls?.[0], 'Filing')}<small>${row.source_rows} records</small></td></tr>`).join(''));
  const timing = (evidence.temporal_routes || []).filter(row => row.cycle === cycle);
  const assets = new Set(timing.filter(row => row.status === 'asset_liquidation_link_required').map(row => row.receipt_sub_id)).size;
  $('evidence-timing').textContent = `${assets} in-kind receipt(s) in this cycle require a documented liquidation link before a cash route can be evaluated. Date-compatible routes are possibilities, not assigned dollars. Transfers outside the ${evidence.committee_finances.filter(row => row.cycle === cycle).length}-committee snapshot remain outside its coverage.`;
}
async function loadEvidence() {
  const id = $('evidence-snapshot').value;
  if (!id) return;
  evidence = await api('/api/evidence?id=' + encodeURIComponent(id));
  $('evidence-cycle').innerHTML = [...new Set(evidence.committee_finances.map(row => row.cycle))].sort().map(cycle => `<option value="${cycle}">${cycle - 1}–${cycle}</option>`).join('');
  const names = new Map(evidence.committee_finances.map(row => [row.committee_id, row.committee_name || row.committee_id]));
  $('evidence-committee').innerHTML = [...names].map(([id,name]) => `<option value="${escapeHtml(id)}">${escapeHtml(name)}</option>`).join('');
  $('evidence-panel').hidden = false;
  renderEvidence();
}
async function initEvidence() {
  try {
    const result = await api('/api/evidence');
    $('evidence-snapshot').innerHTML = result.snapshots.map(row => `<option value="${escapeHtml(row.id)}">${escapeHtml(row.company)} · ${escapeHtml(row.retrieved_at?.slice(0,10))}</option>`).join('');
    if (result.snapshots.length) await loadEvidence();
    $('evidence-empty').hidden = result.snapshots.length > 0;
  } catch (error) { showError(error.message); }
}
$('evidence-snapshot').addEventListener('change', () => loadEvidence().catch(error => showError(error.message)));
$('evidence-cycle').addEventListener('change', renderEvidence);
$('evidence-committee').addEventListener('change', renderEvidence);
restoreDraft();
showView(location.hash.slice(1));
init();
initEvidence();
