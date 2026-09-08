const $ = id => document.getElementById(id);
const renderedHtml = new Map();
function setHtml(id, html) { if (renderedHtml.get(id) !== html) { $(id).innerHTML = html; renderedHtml.set(id, html); } }
let token = '', upload = null, selectedRun = '', selectedLane = '', busy = false;
const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const number = value => value == null ? '—' : Number(value).toLocaleString();
const label = value => String(value || '').replaceAll('_', ' ');
const duration = value => value == null ? '—' : value < 60 ? '<1 min' : value < 3600 ? Math.ceil(value / 60) + ' min' : (value / 3600).toFixed(1) + ' hr';
function showError(message) { $('error').textContent = message; $('error').hidden = !message; }
async function api(path, data) {
  const response = await fetch(path, data === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json','X-Mentat-Token':token}, body:JSON.stringify(data)});
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || 'The request could not be completed.');
  return body;
}
function roster(readiness) {
  $('upload-review').hidden = false;
  const groups = readiness.readiness || [];
  const count = groups.reduce((n,g) => n + g.company_count, 0);
  const variants = groups.reduce((n,g) => n + g.variant_count, 0);
  $('roster-counts').textContent = `${count} companies · ${variants} search names · ${groups.length} industries`;
  $('roster-list').innerHTML = groups.map(group => `<h3>${escapeHtml(group.industry)}</h3>` + group.companies.map(company => `<div class="roster-company"><b>${escapeHtml(company.company)}</b><small>${company.variants.map(v => escapeHtml(v.variant)).join(' · ')}</small>${company.exclusions.length ? '<small>Exclude: ' + company.exclusions.map(escapeHtml).join(', ') + '</small>' : ''}</div>`).join('') + (group.ready ? '' : `<p class="error">Resolve ambiguous names or invalid blocks: ${escapeHtml(JSON.stringify({duplicates:group.duplicate_companies,ambiguous:group.cross_company_variants,errors:group.parse_errors}))}</p>`)).join('');
  $('start').disabled = readiness.status !== 'succeeded';
}
$('file').addEventListener('change', async () => {
  const file = $('file').files[0]; if (!file) return;
  showError(''); $('start').disabled = true; upload = null;
  try {
    if (file.size > 5000000) throw new Error('Upload a file smaller than 5 MB.');
    const content = await new Promise((resolve,reject) => { const reader = new FileReader(); reader.onload = () => resolve(reader.result.split(',')[1]); reader.onerror = reject; reader.readAsDataURL(file); });
    upload = await api('/api/upload', {filename:file.name,content});
    roster(upload.readiness); selectedRun = upload.id; selectedLane = '';
    $('roster-panel').open = true;
    await refreshRuns(); await refreshRun();
  } catch (error) { showError(error.message); }
});
$('save-keys').addEventListener('click', async () => {
  try { const result = await api('/api/keys', {keys:$('api-key').value}); $('api-key').value = ''; $('key-hint').textContent = `${result.active_key_count} enabled keys; ${result.stored_key_count - result.active_key_count} disabled. Saved with Windows encryption.`; } catch (error) { showError(error.message); }
});
$('start').addEventListener('click', async () => {
  if (!upload) return;
  $('start').disabled = true; $('start').textContent = 'Starting…'; showError('');
  try {
    await api('/api/start', {id:upload.id, cycles:[...document.querySelectorAll('input[name=cycle]:checked')].map(c => Number(c.value)), api_key:$('api-key').value});
    $('api-key').value = ''; $('start').textContent = 'Collection started'; upload = null;
    $('roster-panel').open = false;
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
  if (!body.runs.length) $('roster-panel').open = true;
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
  const warnings = run.reports.flatMap(report => (report.quality?.warnings || []).map(warning => ({...warning, report:report.name})));
  $('quality-title').textContent = oldReports ? 'Report warning: downstream directions are combined' : failed ? 'Collection coverage checks failed' : passed && passed === assurance.length ? 'Saved collection checks passed · downstream coverage unverified' : 'Collection coverage not yet verified';
  $('quality-detail').textContent = oldReports ? 'An exported workbook lacks separate support and opposition columns. Its party totals may include spending against that party’s candidates.' : changedReports ? 'A workbook has changed since this run. Its current contents do not match the run’s recorded file.' : 'A finished search is not proof that every contribution or downstream transfer was captured.';
  let qualityHtml = assurance.map(check => `<span class="quality-chip">${escapeHtml(check.industry)} · ${escapeHtml(check.collection)}${check.recorded_checks ? ' (' + check.recorded_checks + ' checks)' : ''}</span>`).join('');
  if (warnings.length) {
    $('quality-title').textContent = `${warnings.length} report quality warnings require review`;
    $('quality-detail').textContent = 'The repaired workbooks retain unresolved collection and classification warnings. Open Data Quality in each workbook for the evidence.';
    qualityHtml += `<details><summary>Review ${warnings.length} report warnings</summary>` + warnings.map(warning => `<details><summary>${escapeHtml(warning.report)} · ${escapeHtml(label(warning.check))}</summary><p>${escapeHtml(warning.detail)}</p></details>`).join('') + '</details>';
  }
  setHtml('quality-checks', qualityHtml);
  setHtml('source-snapshots', (run.source_snapshots || []).map(source => `<li>${escapeHtml(source.name)}: local file modified ${escapeHtml(source.modified_at.slice(0,10))} (${source.age_days} days ago). This is not a verified data-through date.</li>`).join('') || '<li>No local source file dates available.</li>');
  if (run.state === 'ready' && run.readiness && (!upload || upload.id !== run.id)) {
    upload = {id:run.id,readiness:run.readiness};
    roster(run.readiness);
    $('start').textContent = 'Start collection';
  }
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
init();
