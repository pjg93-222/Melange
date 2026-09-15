const $ = id => document.getElementById(id);
const renderedHtml = new Map();
function setHtml(id, html) { if (renderedHtml.get(id) !== html) { $(id).innerHTML = html; renderedHtml.set(id, html); } }
let token = '', upload = null, selectedRun = '', selectedLane = '', busy = false, warningIds = [];
let readOnly = false, evidenceCollectionAvailable=false;
let rosterRevision = 0, companySequence = 0, currentView = 'loading', splitView = false;
let runCatalog = [], runGroup = '', runArchiveBusy = false;
let savedCoverage = [];
function renderLoadingCoverage() {
  const sectors = upload?.readiness?.readiness?.map(group => group.industry) || [$('sector').value];
  const cycles = [...document.querySelectorAll('input[name=cycle]:checked')].map(c => Number(c.value));
  setHtml('loading-coverage', cycles.length ? MentatCoverage.html(MentatCoverage.select(savedCoverage, sectors, cycles)) : '<p>Select an election cycle to review coverage.</p>');
}
document.querySelectorAll('input[name=cycle]').forEach(input => input.addEventListener('change', renderLoadingCoverage));
const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const number = value => value == null ? '—' : Number(value).toLocaleString();
const label = value => String(value || '').replaceAll('_', ' ');
const duration = value => value == null ? '—' : value < 60 ? '<1 min' : value < 3600 ? Math.ceil(value / 60) + ' min' : (value / 3600).toFixed(1) + ' hr';
function showError(message) { $('error').classList.add('error'); $('error').textContent = message; $('error').hidden = !message; }
function showStatus(message) { $('error').classList.remove('error'); $('error').textContent = message; $('error').hidden = !message; }
function showView(view, focus = false) {
  if (view === 'charts') view = 'graph';
  currentView = ['loading', 'collection', 'cross-reference', 'evidence', 'graph', 'chart-studio'].includes(view) ? view : 'loading';
  for (const name of ['loading', 'collection', 'cross-reference', 'evidence', 'graph', 'chart-studio']) {
    const active = name === currentView;
    const pane = $('view-' + name), paired = splitView && ['graph','evidence'].includes(currentView) && ['graph','evidence'].includes(name);
    pane.hidden = !(active || paired);
    pane.setAttribute('role', paired ? 'region' : 'tabpanel');
    $('tab-' + name).setAttribute('aria-selected', String(active));
    $('tab-' + name).tabIndex = active ? 0 : -1;
  }
  $('workspace-title').textContent = {loading:'Load a sector',collection:'Collection monitor','cross-reference':'Cross-reference the evidence',evidence:'Follow PAC spending',graph:'Graph','chart-studio':'Chart Studio'}[currentView];
  window.MentatCrossReference?.setActive(currentView === 'cross-reference');
  $('stage').hidden = currentView !== 'collection';
  $('graph-actions').hidden = currentView !== 'graph';
  const paired = splitView && ['graph','evidence'].includes(currentView);
  document.querySelector('.workspace').classList.toggle('split-workspace', paired);
  $('split-view').hidden = !['graph','evidence'].includes(currentView);
  $('split-view').setAttribute('aria-pressed', String(paired));
  $('split-view').textContent = paired ? 'Single view' : currentView === 'graph' ? 'Split with PAC evidence' : 'Split with Graph';
  if (paired) { $('workspace-title').textContent = 'Graph & PAC evidence'; $('graph-actions').hidden = false; }
  history.replaceState(null, '', '#' + currentView);
  window.dispatchEvent(new CustomEvent('mentat:view', {detail:{view:currentView,split:paired}}));
  if (focus) {
    const activeTab = $('tab-' + currentView);
    activeTab.focus({preventScroll:true});
    activeTab.scrollIntoView({block:'nearest', inline:'nearest'});
  }
}
document.querySelector('.workspace-tabs').addEventListener('click', event => {
  const tab = event.target.closest('[role=tab]'); if (tab) showView(tab.id.slice(4));
});
window.addEventListener('hashchange', () => showView(location.hash.slice(1)));
document.querySelector('.skip-link').addEventListener('click', event => {
  event.preventDefault(); document.getElementById('workspace-main').focus();
});
document.querySelector('.workspace-tabs').addEventListener('keydown', event => {
  const names = [...document.querySelectorAll('.workspace-tabs [role=tab]')].map(tab => tab.id.slice(4)), index = names.indexOf(currentView);
  const next = {ArrowRight:(index + 1) % names.length, ArrowDown:(index + 1) % names.length, ArrowLeft:(index + names.length - 1) % names.length, ArrowUp:(index + names.length - 1) % names.length, Home:0, End:names.length - 1}[event.key];
  if (next != null) { event.preventDefault(); showView(names[next], true); }
});
const sidebarLayout = window.matchMedia('(min-width: 1100px)');
function updateNavigationOrientation() {
  document.querySelector('.workspace-tabs').setAttribute('aria-orientation', sidebarLayout.matches ? 'vertical' : 'horizontal');
}
$('split-view').addEventListener('click', () => { splitView = !splitView; showView(currentView); });
sidebarLayout.addEventListener('change', updateNavigationOrientation);
updateNavigationOrientation();
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
  renderLoadingCoverage();
}
function addCompany(company = {name:'',aliases:[]}) {
  const id = ++companySequence, row = document.createElement('div'); row.className = 'company-entry';
  row.innerHTML = `<div class="company-entry-heading"><strong>Company</strong><button type="button" class="remove-company" aria-label="Remove company">Remove</button></div><label class="field" for="company-${id}">Company name</label><input id="company-${id}" class="company-name" type="text" required maxlength="250" placeholder="e.g. Harborlight Credit Union" value="${escapeHtml(company.name)}"><label class="field" for="aliases-${id}">Alternative names <span>One name per line · optional</span></label><textarea id="aliases-${id}" class="company-aliases" rows="3" placeholder="e.g. Harborlight CU&#10;Harborlight Federal Credit Union">${escapeHtml(company.aliases.join('\n'))}</textarea>`;
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
  upload = value; roster(value.readiness); runGroup = 'progress'; selectedRun = value.id; selectedLane = ''; clearRunDisplay();
  $('start').textContent = 'Start collection';
  $('draft-status').textContent = value.state === 'ready' ? 'Roster validated and saved. Choose cycles, then start collection.' : 'Review the name conflicts before starting.';
  if(!await refreshRuns())await refreshRun();
}
$('roster-form').addEventListener('submit', async event => {
  event.preventDefault(); showError(''); const revision = ++rosterRevision;
  upload = null; $('start').disabled = true; $('review-roster').disabled = true; $('review-roster').textContent = 'Checking names…';
  try { await acceptRoster(await api('/api/roster', draftData()), revision); }
  catch (error) { if (revision === rosterRevision) showError(error.message); }
  finally { $('review-roster').disabled = false; $('review-roster').textContent = 'Review roster'; }
});
async function api(path, data) {
  if(readOnly && data !== undefined)throw new Error('This preview is read-only while the original console manages collection.');
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
let keySave = null;
$('save-keys').addEventListener('click', async () => {
  $('save-keys').disabled = true;
  keySave = api('/api/keys', {keys:$('api-key').value});
  try { const result = await keySave; $('api-key').value = ''; $('key-hint').textContent = `${result.active_key_count} enabled keys; ${result.stored_key_count - result.active_key_count} disabled. Saved with Windows encryption.`; }
  catch (error) { showError(error.message); }
  finally { keySave = null; $('save-keys').disabled = false; }
});
$('clear-quality').addEventListener('click', async () => {
  try { await api('/api/quality/acknowledge', {id:selectedRun, warning_ids:warningIds}); await refreshRun(); }
  catch (error) { showError(error.message); }
});
$('start').addEventListener('click', async () => {
  if (!upload) return;
  $('start').disabled = true; $('start').textContent = 'Starting…'; showError('');
  try {
    if (keySave) await keySave;
    await api('/api/start', {id:upload.id, cycles:[...document.querySelectorAll('input[name=cycle]:checked')].map(c => Number(c.value)), api_key:$('api-key').value});
    $('api-key').value = ''; $('start').textContent = 'Collection started'; upload = null;
    showView('collection');
    await refreshRun();
  } catch (error) { showError(error.message); $('start').disabled = false; $('start').textContent = 'Start collection'; }
});
$('stop').addEventListener('click', async event => {
  if (!selectedRun) return;
  const force = !event.shiftKey;
  const question = force
    ? 'Stop this collection? This immediately terminates the collection and its worker processes. Partial lane data for the current run is discarded. The source database is not modified. This cannot be undone.'
    : 'Stop this collection gracefully? In-flight lanes are allowed to finish first, and the run cannot be un-stopped.';
  if (!confirm(question)) return;
  try {
    const result = await api('/api/stop', {id:selectedRun, force});
    await refreshRun();
    if (result.ok === false) showError(result.message || 'The collection could not be stopped.');
  }
  catch (error) { showError(error.message); }
});
$('apply-workers').addEventListener('click', async () => {
  if (!selectedRun) return;
  try {
    const workers = Number($('worker-target').value);
    await api('/api/workers', {id:selectedRun, workers});
    await refreshRun();
    showStatus(`Workers set to ${workers} - takes effect within a few seconds`);
  }
  catch (error) { showError(error.message); }
});
$('runs').addEventListener('change', async () => { selectedRun = $('runs').value; selectedLane = ''; clearRunDisplay(); renderRunLibrary(); await refreshRun().catch(e => showError(e.message)); });
$('lanes').addEventListener('change', async () => { selectedLane = $('lanes').value; await refreshRun().catch(e => showError(e.message)); });
function collectionGroup(run) {
  return run.archived ? 'archived' : ['completed','failed','stopped','launch failed'].includes(run.state) ? 'history' : 'progress';
}
function collectionChoice(run) {
  const created = new Date(typeof run.created_at === 'number' ? run.created_at*1000 : run.created_at || '');
  return [run.name,label(run.state),Number.isFinite(created.getTime()) ? created.toLocaleString(undefined,{month:'short',day:'numeric',hour:'numeric',minute:'2-digit',second:'2-digit'}) : ''].filter(Boolean).join(' · ');
}
function clearRunDisplay() {
  timerRun = null; $('monitor').hidden = true; $('resume-setup').hidden = true;
  $('run-readiness-note').hidden = true;
  for (const id of ['stop','apply-workers','worker-target','clear-quality']) $(id).disabled = true;
  $('run-title').textContent = selectedRun ? 'Loading collection…' : 'No collections in this folder';
  $('stage').textContent = selectedRun ? 'Loading' : 'No selected collection';
}
function renderRunLibrary() {
  if (!runGroup) runGroup = runCatalog.some(run => collectionGroup(run)==='progress') ? 'progress' : 'history';
  const choices = runCatalog.filter(run => collectionGroup(run) === runGroup);
  const previous = selectedRun;
  if (!choices.some(run => run.id === selectedRun)) selectedRun = choices[0]?.id || '';
  if (previous !== selectedRun) { selectedLane = ''; clearRunDisplay(); }
  setHtml('runs', choices.map(run => `<option value="${escapeHtml(run.id)}">${escapeHtml(collectionChoice(run))}</option>`).join('') || '<option value="">No collections in this folder</option>');
  $('runs').value = selectedRun;
  document.querySelectorAll('[data-run-group]').forEach(button => {
    button.setAttribute('aria-pressed', String(button.dataset.runGroup === runGroup));
    $('run-count-' + button.dataset.runGroup).textContent = runCatalog.filter(run => collectionGroup(run) === button.dataset.runGroup).length;
  });
  const selected = choices.find(run => run.id === selectedRun);
  $('archive-run').textContent = selected?.archived ? 'Restore run' : 'Archive run';
  $('archive-run').disabled = runArchiveBusy || readOnly || !selected || (!selected.archived && !selected.can_archive);
  $('archive-run').title = !selected ? 'Choose a collection' : !selected.archived && !selected.can_archive ? 'Active collections must finish or stop before archiving' : 'Hide or restore this run in the collection list; keep its files';
  $('run-library-note').textContent = {progress:'Rosters and collection work waiting or running. Checkpoints stay in the collection working folder.',history:'Finished and stopped collections. Archive a run to remove it from this list; its files remain available.',archived:'Archived runs are hidden from the main list. Restore one whenever you need its collection records.'}[runGroup];
  if (!selectedRun) {
    $('monitor').hidden = true; $('empty').hidden = false; $('resume-setup').hidden = true;
    $('run-title').textContent = 'No collections in this folder'; $('stage').textContent = 'No selected collection';
  }
  return previous !== selectedRun;
}
document.querySelectorAll('[data-run-group]').forEach(button => button.addEventListener('click', async () => {
  runGroup = button.dataset.runGroup; renderRunLibrary(); await refreshRun().catch(error=>showError(error.message));
}));
$('archive-run').addEventListener('click', async () => {
  const run = runCatalog.find(run=>run.id===selectedRun); if (!run || runArchiveBusy) return;
  runArchiveBusy = true; $('archive-run').disabled = true;
  try { await api('/api/run-archive', {id:run.id, archived:!run.archived}); if(!await refreshRuns())await refreshRun(); showStatus(run.archived ? 'Run restored.' : 'Run archived. Its files are preserved.'); }
  catch (error) { showError(error.message); }
  finally { runArchiveBusy = false; renderRunLibrary(); }
});
$('view-completed-reports').addEventListener('click', () => showView('graph'));
async function refreshRuns(initial) {
  const body = initial || await api('/api/runs?include_archived=1');
  savedCoverage = body.coverage || []; renderLoadingCoverage();
  runCatalog = body.runs || []; const changed = renderRunLibrary();
  $('collection-directory').textContent = body.collection_directory || 'Local collection workspace';
  $('completed-directory').textContent = body.report_directory || 'Configured completed-report folder';
  if (changed && selectedRun) await refreshRun();
  window.dispatchEvent(new CustomEvent('mentat:runs', {detail:body.runs}));
  $('key-status').textContent = body.key_status_available===false ? body.key_status_message : body.key_configured ? `${body.active_key_count} enabled FEC keys saved · ${body.stored_key_count - body.active_key_count} disabled` : 'No enabled FEC keys saved';
  if(body.key_status_available===false)$('key-hint').textContent=body.key_status_message;
  if (body.key_configured) $('key-hint').textContent = `${body.active_key_count} enabled keys; ${body.stored_key_count - body.active_key_count} disabled. Stored with Windows encryption. Leave blank to use them.`;
  return changed;
}
let timerRun=null, timerSample=0;
function updateTimer() {
  if(!timerRun)return;
  const value=MentatState.timer(timerRun,(performance.now()-timerSample)/1000);
  $('eta').textContent=value.remaining; $('elapsed').textContent=value.elapsed;
}
setInterval(updateTimer,1000);
function render(run) {
  $('run-title').textContent = run.name;
  setHtml('collection-coverage', MentatCoverage.html(run.fec_coverage || []));
  const status = run.status || {}, fanout = status.fanout || run.completed_collection || {};
  $('worker-panel').hidden = status.kind === 'report_repair';
  $('records-panel').hidden = status.kind === 'report_repair';
  const terminalStates = ['completed','failed','stopped','launch failed'];
  const terminal = terminalStates.includes(run.state) || terminalStates.includes(status.stage);
  const displayStage = run.state === 'stopped' ? 'stopped' : [run.state,status.stage].find(value => ['failed','launch failed'].includes(value)) || (terminalStates.includes(run.state) ? run.state : status.stage || run.state);
  $('stage').textContent = label(displayStage);
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
  $('clear-quality').disabled = false;
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
  const dateCell = value => escapeHtml(value || 'Unknown');
  setHtml('report-freshness', run.reports.map(report => {
    const fresh = report.freshness || {}, sources = fresh.sources || [];
    return `<details class="report-freshness-card"><summary><strong>${escapeHtml(report.name)}</strong> · Report freshness unknown · ${fresh.verified_source_count || 0}/${sources.length} sources with verified data-through dates</summary><p>Report file modified: ${dateCell(fresh.report_modified_at)}. ${escapeHtml(fresh.note)}</p>` +
      (fresh.issues || []).map(issue => `<p class="freshness-unknown">${escapeHtml(issue)}</p>`).join('') +
      '<div class="table-scroll"><table><thead><tr><th>Source / cycle</th><th>Retrieved</th><th>Local source file modified</th><th>Verified data-through</th><th>Freshness</th><th>Other receipt evidence</th></tr></thead><tbody>' +
      sources.map(source => `<tr><td>${escapeHtml(source.industry || '')} ${escapeHtml(source.source)}<small>${escapeHtml(source.cycle)}</small></td><td>${dateCell(source.retrieved_at)}</td><td>${dateCell(source.file_modified_at)}</td><td>${dateCell(source.verified_data_through)}</td><td class="${source.freshness === 'verified' ? 'freshness-verified' : 'freshness-unknown'}">${source.freshness === 'verified' ? 'Verified date in receipt' : 'Unknown'}</td><td>Checked: ${dateCell(source.checked_at)}<small>Server last modified: ${dateCell(source.server_last_modified)}</small><details><summary>Receipt</summary><p>${escapeHtml(source.receipt)}<br>${escapeHtml(source.local_receipt)}<br>${escapeHtml(source.sha256)}<br>${escapeHtml(source.note)}<br>${escapeHtml(source.verification_evidence)}</p></details></td></tr>`).join('') + '</tbody></table></div></details>';
  }).join('') || '<p class="muted">No completed reports available. Freshness is unknown.</p>');
  const archived = !!runCatalog.find(item=>item.id===run.id)?.archived;
  $('resume-setup').hidden = run.state !== 'ready' || archived;
  $('empty').hidden = true; $('monitor').hidden = false;

  if (!run.status) {
    $('freshness').textContent = run.launch_error || (run.state === 'ready' ? 'Roster validated. Choose cycles and start collection.' : `Run ${label(run.state)}. Waiting for runner status.`);
  } else {
    $('freshness').textContent = terminal ? `Last recorded update: ${status.updated_at || 'unavailable'}` : run.age_seconds > 60 ? `No recent worker update · last checkpoint ${duration(run.age_seconds)} ago. The collector may be waiting, paused, or no longer running.` : `Monitoring · refreshed ${new Date().toLocaleTimeString()} · runner update ${number(run.age_seconds)} seconds ago`;
  }
  const notStarted = ['ready','needs review'].includes(run.state);
  const active = !!selectedRun && !terminal && !notStarted;
  $('monitor').hidden = notStarted;
  $('run-readiness-note').hidden = !notStarted;
  $('run-readiness-note').textContent = archived ? 'Restore this saved roster above before continuing collection setup.' : run.state === 'ready' ? 'Roster saved. Continue setup to choose cycles and start collection, or archive this draft.' : 'This roster needs review before collection. Review the names in Loading.';
  $('run-controls').hidden = !active;
  const inactiveReason = active ? '' : 'No collection is running';
  $('stop').disabled = !active; $('stop').title = active ? 'Shift-click to stop gracefully and let in-flight lanes finish first.' : inactiveReason;
  $('worker-target').disabled = !active; $('worker-target').title = inactiveReason;
  $('apply-workers').disabled = !active; $('apply-workers').title = inactiveReason;
  $('completed').textContent = fanout.total == null ? '—' : `${number(fanout.completed)} / ${number(fanout.total)}`;
  $('workers').textContent = number(fanout.running); $('failed').textContent = number(fanout.failed);
  const recordedWorkers = terminal || run.age_seconds == null || run.age_seconds > 60;
  $('worker-metric-label').textContent = recordedWorkers ? 'Workers at last checkpoint' : 'Active workers';
  const currentWorkers = ((status.industries || []).find(item => item.industry === status.current_industry) || {}).workers;
  if(currentWorkers?.request_pool) $('workers').textContent=number(currentWorkers.active_workers);
  $('worker-detail').textContent = currentWorkers ? `${number(currentWorkers.active_workers)} active / ${number(currentWorkers.requested_workers)} requested` + (currentWorkers.request_pool ? ` · shared fetch workers · ${number(currentWorkers.database_writers)} database coordinators · ${number(currentWorkers.request_pool.queued_requests)} requests queued` : currentWorkers.scheduling === 'company_work_sharing' ? ` · ${number(currentWorkers.pending_companies)} companies waiting · ${number(currentWorkers.company_handoffs)} handoffs` : '') : '';
  if (recordedWorkers && $('worker-detail').textContent) $('worker-detail').textContent = 'Last recorded: ' + $('worker-detail').textContent;
  $('stopping-banner').hidden = terminal || !(run.control && run.control.stop);
  timerRun = run; timerSample = performance.now(); updateTimer();
  $('progress').style.width = fanout.total ? Math.min(100,100 * fanout.completed / fanout.total) + '%' : '0%';
  $('phase-description').textContent = terminal ? `${label(displayStage)}. ${status.current_industry ? `Last checkpoint: ${status.current_industry} · ${label(status.stage)}.` : 'Showing saved collection records.'}` : status.current_industry ? `${status.current_industry} · ${label(status.stage)}. Tasks measure company/cycle attempts; successful coverage is verified separately.` : label(displayStage);
  setHtml('industries', (status.industries || []).map(industry => `<div class="industry"><b>${escapeHtml(industry.industry)}</b> ${terminal ? 'Last checkpoint: ' : ''}${escapeHtml(label(industry.stage))}${industry.detail ? '<details><summary>Run details</summary><p>' + escapeHtml(industry.detail) + '</p></details>' : ''}</div>`).join(''));
  const choices = run.lanes.map(lane => `<option value="${escapeHtml(lane.id)}">${escapeHtml(lane.industry)} / ${escapeHtml(lane.label)} / ${escapeHtml(label(lane.state.status))}</option>`).join('') || '<option value="">No workers yet</option>';
  if ($('lanes').innerHTML !== choices) $('lanes').innerHTML = choices;
  selectedLane = run.selected_lane || ''; $('lanes').value = selectedLane;
  const selected = run.lanes.find(l => l.id === selectedLane);
  $('lane-summary').textContent = selected ? `${label(selected.state.status)} · ${selected.state.current_company || 'No current company'} ${selected.state.current_cycle || ''} · ${selected.state.completed || 0}/${selected.state.total || 0} tasks` : 'Waiting for collection workers.';
  const preview = run.preview || {};
  setHtml('checkpoints', (preview.progress || []).map(row => `<tr><td>${escapeHtml(row.company)}</td><td>${escapeHtml(row.cycle)}</td><td>${escapeHtml(label(row.kind))}</td><td>${number(row.rows_seen)}</td><td>${number(row.records_total)}</td><td>${row.stored_complete ? 'Stored' : row.fetched_complete ? 'Fetched' : 'Collecting'}</td></tr>`).join('') || '<tr><td colspan="6">No readable collection checkpoints yet.</td></tr>');
  setHtml('records', (preview.records || []).map(row => `<tr><td>${escapeHtml(row.contributor_name || 'Unreported')}<small>${escapeHtml(row.company)} · ${escapeHtml(row.contribution_receipt_date)}</small></td><td class="number">${currency(row.contribution_receipt_amount)}</td><td>${escapeHtml(({Chief:'Chief','Middle Management':'Middle-Management',Employee:'Employees'})[row.employee_tier] || row.employee_tier || MentatState.titlePosition(row.contributor_occupation))}</td><td>${escapeHtml(row.contributor_occupation || 'Unreported')}</td><td>${escapeHtml(row.committee_name || 'Unreported')}<small>${escapeHtml(row.sub_id)}</small></td></tr>`).join('') || `<tr><td colspan="5">${escapeHtml(preview.message || 'Records will appear as the selected worker stores them.')}</td></tr>`);
  setHtml('events', run.events.slice().reverse().map(event => `<div class="event"><b>${escapeHtml(label(event.event))}</b> ${escapeHtml(event.industry)}<small>${escapeHtml(event.timestamp || event.at || event.time || '')}</small>${escapeHtml(event.detail || event.message || '')}</div>`).join('') || '<p class="muted">No activity recorded yet.</p>');
  setHtml('reports', run.reports.map(report => `<a class="report-link" download="${escapeHtml(report.name)}" href="/api/report?id=${encodeURIComponent(run.id)}&index=${report.index}">${escapeHtml(report.name)} ↗</a><p class="muted">${report.quality?.direction_columns === false ? 'Older layout: support and opposition are combined.' : report.quality?.direction_columns === true ? 'Opposition is shown in a separate column.' : 'Direction columns not verified.'}${report.quality?.matches_run === false ? ' File changed since this run.' : ''}</p>`).join('') || `<p class="muted">${escapeHtml(run.report_source_notice || 'Reports appear after collection and validation succeed.')}</p>`);
}
async function refreshRun() {
  if (!selectedRun) return;
  const requested = selectedRun, lane = selectedLane;
  const run = await api('/api/run?id=' + encodeURIComponent(requested) + '&lane=' + encodeURIComponent(selectedLane));
  if (requested === selectedRun && lane === selectedLane) { render(run); window.dispatchEvent(new CustomEvent('mentat:run', {detail:run})); }
}
async function poll() {
  if (busy || document.hidden || !['loading','collection'].includes(currentView)) return;
  busy = true;
  try { const changed=await refreshRuns(); if(!changed)await refreshRun(); $('connection').textContent = '● Local connection'; }
  catch (error) { $('connection').textContent = 'Connection interrupted · retrying'; }
  finally { busy = false; }
}
async function init() {
  try { const session = await api('/api/session?light=1'); token = session.token; readOnly=!!session.read_only;
    try { renderBuild(session); scheduleBuildPoll(); } catch { }
    evidenceCollectionAvailable=!!session.evidence_collection_available;
    $('evidence-collect').disabled=readOnly||!evidenceCollectionAvailable||!!evidenceJob;
    if(!evidenceCollectionAvailable)$('evidence-job-status').textContent='Restart the MENTAT server to enable new snapshot collection. Saved evidence controls are ready to use.';
    if(readOnly)showStatus('Read-only preview · the original console continues managing your active collection.');
    $('connection').textContent = '● Local connection';
    if(['loading','collection'].includes(currentView))poll(); }
  catch (error) { showError(error.message); }
  setInterval(poll, 3000);
}
window.addEventListener('mentat:view',()=>{if(token&&['loading','collection'].includes(currentView))poll();});
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
let graphContext=null, evidenceRevision=0;
let evidencePreference={};
try{evidencePreference=JSON.parse(localStorage.getItem('mentat-evidence-selection')||'{}')||{};}catch{}
if(['saved','graph'].includes(evidencePreference.mode))$('evidence-mode').value=evidencePreference.mode;
function saveEvidenceSelection() {
  evidencePreference={mode:$('evidence-mode').value,snapshot:$('evidence-snapshot').value,
    cycle:$('evidence-cycle').value,committee:$('evidence-committee').value};
  try{localStorage.setItem('mentat-evidence-selection',JSON.stringify(evidencePreference));}catch{}
}
const followsGraph=()=>$('evidence-mode').value==='graph';
function clearEvidence(message) {
  evidence=null; $('evidence-panel').hidden=true; $('evidence-empty').hidden=false;
  $('evidence-empty').textContent=message;
}
async function loadEvidence() {
  const id=$('evidence-snapshot').value, ticket=++evidenceRevision;
  const previousCycle=$('evidence-cycle').value||evidencePreference.cycle;
  clearEvidence('Loading saved evidence…');
  if(!id)return;
  let body;
  try{body=await api('/api/evidence?id='+encodeURIComponent(id));}
  catch(error){if(ticket===evidenceRevision)clearEvidence(error.message);return;}
  if(ticket!==evidenceRevision)return;
  const graphCycle=followsGraph()?graphContext?.filters.cycle:'';
  const cycles=[...new Set(body.committee_finances.map(row=>row.cycle))].filter(c=>!graphCycle||String(c)===graphCycle).sort((a,b)=>b-a);
  if(!cycles.length){clearEvidence('No evidence snapshot covers the loaded graph cycle.');return;}
  evidence=body;
  $('evidence-cycle').replaceChildren(...cycles.map(c=>new Option(`${c-1}–${c}`,c)));
  if(cycles.some(c=>String(c)===previousCycle))$('evidence-cycle').value=previousCycle;
  $('evidence-cycle').disabled=!!graphCycle;
  $('evidence-panel').hidden=false; $('evidence-empty').hidden=true; updateEvidenceCommittees();
}
function updateEvidenceCommittees() {
  if(!evidence)return;
  const previous=$('evidence-committee').value||evidencePreference.committee;
  const names=new Map(evidence.committee_finances.filter(row=>String(row.cycle)===$('evidence-cycle').value).map(row=>[row.committee_id,row.committee_name||row.committee_id]));
  $('evidence-committee').replaceChildren(...[...names].map(([id,name])=>new Option(`${name} · ${id}`,id)));
  if(names.has(previous))$('evidence-committee').value=previous;
  renderEvidence();saveEvidenceSelection();
}
async function initEvidence() {
  if(!savedEvidenceVisible())return;
  const ticket=++evidenceRevision;
  const previous=$('evidence-snapshot').value||evidencePreference.snapshot;
  $('evidence-snapshot').replaceChildren();
  clearEvidence('Finding saved evidence…');
  if(followsGraph()&&!graphContext){clearEvidence('Load a graph, or choose saved evidence above.');return;}
  try {
    const snapshotCatalog=await api('/api/evidence');
    if(ticket!==evidenceRevision)return;
    const companies=graphContext?(graphContext.filters.company?[graphContext.filters.company]:(graphContext.options?.companies||graphContext.companies.map(row=>row.id))):[];
    const names=new Set(companies.map(MentatState.normalizeName));
    const matches=snapshotCatalog.snapshots.filter(row=>!followsGraph()||(names.has(MentatState.normalizeName(row.company)) &&
      (!graphContext.filters.cycle || (row.cycles || []).some(c=>String(c)===graphContext.filters.cycle)))).sort((a,b)=>String(b.retrieved_at||'').localeCompare(String(a.retrieved_at||'')));
    $('evidence-snapshot').replaceChildren(...matches.map(row=>new Option(`${row.company} · ${row.retrieved_at?.slice(0,10)||'Undated'}`,row.id)));
    if(matches.some(row=>row.id===previous))$('evidence-snapshot').value=previous;
    if(matches.length)await loadEvidence();else clearEvidence(followsGraph()?'No saved PAC evidence matches the loaded graph companies and cycle. Choose saved evidence above to explore another snapshot.':'No saved PAC evidence is available.');
  }catch(error){if(ticket===evidenceRevision)clearEvidence(error.message);}
}
let savedEvidenceActive=false;
function savedEvidenceVisible(){return !$('view-evidence').hidden&&$('evidence-source').value==='snapshot';}
function activateSavedEvidence(){const active=savedEvidenceVisible();if(active&&!savedEvidenceActive)initEvidence();else if(!active&&savedEvidenceActive)++evidenceRevision;savedEvidenceActive=active;}
window.addEventListener('mentat:view',activateSavedEvidence);
window.addEventListener('DOMContentLoaded',activateSavedEvidence);
$('evidence-source').addEventListener('change',activateSavedEvidence);
window.addEventListener('mentat:graph', event=>{graphContext=event.detail;if(followsGraph())initEvidence();});
$('evidence-mode').addEventListener('change', ()=>{saveEvidenceSelection();initEvidence();});
$('evidence-refresh').addEventListener('click', initEvidence);
$('evidence-snapshot').addEventListener('change', () => loadEvidence().catch(error => clearEvidence(error.message)));
$('evidence-cycle').addEventListener('change', updateEvidenceCommittees);
$('evidence-committee').addEventListener('change', ()=>{renderEvidence();saveEvidenceSelection();});
$('evidence-use-config').addEventListener('click',()=>{
  if(!evidence){$('evidence-job-status').textContent='Choose a saved snapshot first.';return;}
  $('evidence-company-input').value=evidence.company;
  $('evidence-cycles-input').value=[...new Set(evidence.committee_finances.map(r=>r.cycle))].join(', ');
  $('evidence-committees-input').value=[...new Set(evidence.committee_finances.map(r=>r.committee_id))].join(', ');
  $('evidence-aliases-input').value=(evidence.aliases||[]).join('\n');
});
let evidenceJob='', evidenceJobTimer;
async function pollEvidenceJob() {
  if(!evidenceJob)return;
  try {
    const job=await api('/api/evidence-job?id='+encodeURIComponent(evidenceJob));
    $('evidence-job-status').textContent=job.state==='collecting'?`Collecting ${job.company} evidence… Saved responses are retained as collection progresses.`:job.message||label(job.state);
    if(job.state!=='collecting'){
      clearTimeout(evidenceJobTimer);$('evidence-collect').disabled=readOnly||!evidenceCollectionAvailable;
      const id=evidenceJob;evidenceJob='';try{localStorage.removeItem('mentat-evidence-job');}catch{}
      if(job.state==='completed'){
        $('evidence-mode').value='saved';await initEvidence();
        if([...$('evidence-snapshot').options].some(o=>o.value===id)){$('evidence-snapshot').value=id;await loadEvidence();}
      }
      return;
    }
  }catch(error){$('evidence-job-status').textContent=error.message+' · retrying';}
  evidenceJobTimer=setTimeout(pollEvidenceJob,3000);
}
$('evidence-form').addEventListener('submit',async event=>{
  event.preventDefault();if(evidenceJob)return;
  $('evidence-collect').disabled=true;
  try {
    const job=await api('/api/evidence-collect',{company:$('evidence-company-input').value,
      aliases:$('evidence-aliases-input').value.split(/\r?\n/).map(v=>v.trim()).filter(Boolean),
      committees:$('evidence-committees-input').value,cycles:$('evidence-cycles-input').value});
    evidenceJob=job.id;
    try{localStorage.setItem('mentat-evidence-job',evidenceJob);}catch{}
    pollEvidenceJob();
  }catch(error){$('evidence-job-status').textContent=error.message;$('evidence-collect').disabled=readOnly||!evidenceCollectionAvailable;}
});
try{evidenceJob=localStorage.getItem('mentat-evidence-job')||'';}catch{}
if(evidenceJob){$('evidence-collect').disabled=true;pollEvidenceJob();}
/* Build stamp and stale-build guard. A console window outlives edits to the
   server tree, so the page states which build answered it, and offers the
   same-port restart the launcher performs. Both elements are built here
   because index.html is owned elsewhere this lane. */
let buildStatus = null, buildPollTimer = 0, buildRestarting = false, buildBannerMode = '';
// The "already current" confirmation clears itself; held here so a second press
// restarts the countdown instead of stacking timers.
let currentNoticeTimer = 0;
function buildStartedText(value) {
  const at = typeof value === 'number' ? new Date(value * 1000) : new Date(value ?? NaN);
  return Number.isFinite(at.getTime()) ? at.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'}) : 'unknown';
}
function buildStampText(build) {
  const revision = build.git_sha && build.git_sha !== 'unknown' ? String(build.git_sha) : String(build.code_sha256 || 'unknown');
  return `build ${revision.slice(0, 7)} · port ${build.port ?? '?'} · up since ${buildStartedText(build.started_at)}`;
}
function mountBuildElements() {
  if ($('build-stamp')) return;
  const stamp = document.createElement('span');
  stamp.id = 'build-stamp';
  stamp.className = 'build-stamp';
  stamp.setAttribute('role', 'status');
  document.querySelector('.app-navigation')?.append(stamp);
  const banner = document.createElement('div');
  banner.id = 'stale-banner';
  banner.className = 'stale-banner';
  banner.hidden = true;
  banner.setAttribute('role', 'status');
  const message = document.createElement('span');
  message.id = 'stale-banner-message';
  const action = document.createElement('button');
  action.id = 'stale-restart';
  action.type = 'button';
  action.textContent = 'Restart';
  action.addEventListener('click', () => { if (buildBannerMode === 'assets') location.reload(); else restartConsole(); });
  banner.append(message, action);
  const workspace = document.querySelector('.workspace'), anchor = $('error');
  if (workspace && anchor && anchor.parentNode === workspace) workspace.insertBefore(banner, anchor);
  else workspace?.prepend(banner);
}
function renderBuild(response) {
  const build = response && response.code_sha256 === undefined && response.build ? response.build : response;
  if (!build || typeof build !== 'object' || typeof build.code_sha256 !== 'string') return;
  buildStatus = build;
  mountBuildElements();
  const stamp = $('build-stamp'), banner = $('stale-banner'), action = $('stale-restart');
  if (stamp) stamp.textContent = buildStampText(build);
  if (!banner || buildRestarting) return;
  const codeChanged = !!build.on_disk_code_sha256_now && build.on_disk_code_sha256_now !== build.code_sha256;
  const assetsChanged = !!build.on_disk_assets_sha256_now && build.on_disk_assets_sha256_now !== build.assets_sha256;
  buildBannerMode = codeChanged ? 'code' : assetsChanged ? 'assets' : '';
  banner.hidden = !buildBannerMode;
  action.disabled = false;
  if (codeChanged) {
    // The launcher rebinds this same port, so this origin is where the
    // current build answers once the restart finishes.
    $('stale-banner-message').textContent = readOnly
      ? `This preview runs an older build. Close this tab and open ${location.origin}.`
      : `This console runs an older build. Press Restart, or close this tab and open ${location.origin}.`;
    action.textContent = 'Restart';
    action.hidden = readOnly;
  } else if (assetsChanged) {
    $('stale-banner-message').textContent = 'Interface files changed.';
    action.textContent = 'Reload';
    action.hidden = false;
  }
}
async function restartConsole() {
  const action = $('stale-restart'), message = $('stale-banner-message');
  const before = buildStatus && buildStatus.pid;
  buildRestarting = true;
  action.disabled = true;
  action.textContent = 'Restarting…';
  let answer;
  try { answer = await api('/api/restart', {}); }
  catch (error) {
    buildRestarting = false; action.disabled = false; action.textContent = 'Restart';
    message.textContent = `${error.message} Close this tab and open ${location.origin} instead.`;
    return;
  }
  // A console already running the build on disk answers current:true and does
  // not restart. Polling for a new pid then could only ever time out, so the
  // reader is told the console is current and the poll never starts. The telling
  // is transient: a standing bar offering Restart when nothing is stale is the
  // same lie in a quieter voice, so the confirmation clears itself and hands the
  // banner back to whatever renderBuild computes - which is hidden, on a console
  // that is current.
  if (answer && answer.current) {
    buildRestarting = false;
    action.disabled = false;
    action.textContent = 'Restart';
    if (answer.build) renderBuild(answer);
    const banner = $('stale-banner'), note = $('stale-banner-message') || message;
    const settle = () => { if (answer.build) renderBuild(answer); else if (banner) banner.hidden = true; };
    if (banner) banner.hidden = false;
    action.hidden = true;
    note.textContent = 'Already up to date.';
    clearTimeout(currentNoticeTimer);
    currentNoticeTimer = setTimeout(settle, 5000);
    return;
  }
  message.textContent = 'Restarting. This page reloads when the new build is ready.';
  const deadline = Date.now() + 120000;
  const waitForNewBuild = async () => {
    if (Date.now() > deadline) {
      buildRestarting = false; action.disabled = false; action.textContent = 'Restart';
      message.textContent = `Restart is taking too long. Close this tab and open ${location.origin}.`;
      return;
    }
    try {
      const health = await api('/api/health');
      if (health.pid && before && health.pid !== before) { location.reload(); return; }
    } catch { }
    setTimeout(waitForNewBuild, 1500);
  };
  setTimeout(waitForNewBuild, 1500);
}
function scheduleBuildPoll() {
  clearTimeout(buildPollTimer);
  buildPollTimer = setTimeout(pollBuild, 60000);
}
async function pollBuild() {
  if (!document.hidden && !buildRestarting) {
    try { renderBuild(await api('/api/health')); } catch { }
  }
  scheduleBuildPoll();
}
restoreDraft();
showView(location.hash.slice(1));
init();
activateSavedEvidence();
