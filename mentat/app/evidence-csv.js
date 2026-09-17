/* CSV evidence uses selected source rows only; imports are stored under the console data root. */
(() => {
  let source = null, revision = 0, offset = 0, limits = null, picker = null, stored = [];
  let pendingUploadFile = null, pendingPathRequest = null;
  const pageSize = 100;
  const pollDelay = 500;
  const pollFailureLimit = 5;
  const channelName = value => String(value || 'Unclassified').replaceAll('_',' ');
  const megabytes = value => (Number(value || 0) / 1e6).toFixed(1);
  const suffixOf = name => { const idx = String(name || '').lastIndexOf('.'); return idx === -1 ? '' : String(name).slice(idx).toLowerCase(); };
  const directoryOf = value => {
    const trimmed = String(value || '').trim();
    if (!trimmed) return '';
    const stripped = trimmed.replace(/[\\/]+$/, '');
    if (!stripped) return trimmed;
    const idx = Math.max(stripped.lastIndexOf('\\'), stripped.lastIndexOf('/'));
    return idx === -1 ? '' : trimmed.slice(0, idx + 1);
  };
  const say = text => { $('evidence-csv-status').textContent = text; };
  const storedMessage = () => stored.length
    ? `${number(stored.length)} imported CSVs on this computer`
    : 'No CSV imported yet. Choose a file.';
  function sourceMode() {
    const saved = $('evidence-source').value === 'snapshot';
    $('evidence-saved').hidden = !saved; $('evidence-csv-workspace').hidden = saved;
    try { localStorage.setItem('mentat-evidence-source', saved ? 'snapshot' : 'csv'); } catch {}
  }
  try { if (localStorage.getItem('mentat-evidence-source') === 'snapshot') $('evidence-source').value = 'snapshot'; } catch {}
  $('evidence-source').addEventListener('change', sourceMode); sourceMode();
  function sourcePicker() {
    if (picker) return picker;
    const label = document.createElement('label');
    label.className = 'evidence-csv-source-label';
    label.htmlFor = 'evidence-csv-source';
    label.textContent = 'Previously imported';
    picker = document.createElement('select');
    picker.id = 'evidence-csv-source';
    picker.addEventListener('change', chooseStored);
    label.appendChild(picker);
    $('evidence-csv-workspace').prepend(label);
    return picker;
  }
  function resetSelection() {
    source = null; offset = 0; $('evidence-csv-results').hidden = true;
    $('evidence-csv-committee').replaceChildren(new Option('Choose a CSV first',''));
    $('evidence-csv-cycle').replaceChildren(new Option('All cycles',''));
    $('evidence-csv-committee').disabled = true; $('evidence-csv-cycle').disabled = true;
  }
  function fillCommittees(committees) {
    $('evidence-csv-committee').replaceChildren(...committees.map(item=>new Option(`${item.name || item.id} · ${item.id}`,item.id)));
    $('evidence-csv-committee').disabled = !committees.length;
  }
  function hideSheetPicker() { $('evidence-sheet-label').hidden = true; }
  function showSheets(job) {
    const sheets = job.sheets || [];
    if (sheets.length > 1) {
      $('evidence-sheet').replaceChildren(...sheets.map(name => new Option(name, name)));
      $('evidence-sheet').value = sheets.includes(job.sheet) ? job.sheet : sheets[0];
      $('evidence-sheet-label').hidden = false;
    } else {
      hideSheetPicker();
    }
  }
  async function refreshSources() {
    const select = sourcePicker();
    const keep = source ? source.id : select.value;
    try {
      const body = await api('/api/evidence-csv');
      limits = body.limits || limits;
      stored = body.sources || [];
      select.replaceChildren(new Option('Choose a previously imported CSV',''),
        ...stored.map(item => new Option(`${item.name} · ${number(item.row_count)} rows · ${item.format || 'delimited'} · ${String(item.imported_at || '').slice(0,10)}`, item.id)));
      select.value = stored.some(item => item.id === keep) ? keep : '';
      say(storedMessage());
      return stored;
    } catch (error) {
      say('GET /api/evidence-csv failed: ' + error.message);
      return null;
    }
  }
  async function chooseStored() {
    const chosenId = sourcePicker().value;
    const ticket = ++revision;
    resetSelection(); pendingUploadFile = null; pendingPathRequest = null; hideSheetPicker();
    sourcePicker().value = chosenId;
    if (!chosenId) { say(storedMessage()); return; }
    const chosen = stored.find(item => item.id === chosenId);
    if (!chosen) { say(`${chosenId}: that imported CSV is no longer listed. Choose the file again.`); await refreshSources(); return; }
    if (ticket !== revision) return;
    source = chosen; offset = 0;
    fillCommittees(chosen.committees || []);
    await loadRows();
  }
  function renderRows(body) {
    const rows = body.rows || [], pages = body.pagination || body;
    const total = pages.total_rows ?? body.total_rows ?? rows.length;
    const supported = body.supported_rows ?? rows.filter(row=>row.status==='supported').length;
    $('evidence-csv-title').textContent = body.committee?.name || body.committee?.id || 'Reported activity';
    $('evidence-csv-scope').textContent = `${body.source?.name || source.name} · ${body.committee?.id || $('evidence-csv-committee').value} · ${body.selected_cycle || 'All cycles'} · ${number(total)} selected rows`;
    setHtml('evidence-csv-totals', (body.totals || []).map(item => `<div><span>${escapeHtml(channelName(item.channel))}</span><strong>${currency(item.amount)}</strong><small>${number(item.row_count)} supported CSV rows</small></div>`).join('') || '<p>No supported amount totals for these rows. Review the original fields below.</p>');
    const sourceKind = body.source?.source_kind || source.source_kind;
    const sourcePath = body.source?.source_path || source.source_path;
    $('evidence-csv-provenance').textContent = `${body.source?.name || source.name} · Imported UTF-8 text SHA-256 ${body.source?.sha256 || source.sha256} · ${number(body.source?.row_count || source.row_count)} file rows.`
      + (sourceKind === 'path' && sourcePath ? ` Read from ${sourcePath}.` : '')
      + ` Stored on this computer under the console data root; visible to every Mentat console that uses it. Values are observed filings or labeled cycle aggregates, not donor allocations or reconciled giving totals.`;
    setHtml('evidence-csv-warnings', (body.warnings || []).map(warning=>`<li>${escapeHtml(typeof warning==='string'?warning:warning.message||JSON.stringify(warning))}</li>`).join('') || '<li>No parser warnings. Source coverage and filing completeness remain unverified.</li>');
    $('evidence-csv-row-status').textContent = `${total ? `${number(offset+1)}–${number(offset+rows.length)} of ${number(total)}` : 'No matching'} rows · ${number(supported)} supported · ${number(body.unsupported_rows ?? Math.max(0,total-supported))} need interpretation. All selected rows contribute to the counts above, across pages.`;
    setHtml('evidence-csv-rows', rows.map(row => `<tr><td>${number(row.row_number)}</td><td>${escapeHtml(row.date || 'Date unavailable')}<small>${escapeHtml(row.cycle || 'Cycle unavailable')}</small></td><td class="number">${(row.amount == null ? 'Not reported' : currency(row.amount))}</td><td>${escapeHtml(row.counterparty || row.candidate_name || row.candidate_id || 'Not reported')}<small>${escapeHtml(channelName(row.channel || row.kind))} · ${escapeHtml(row.status || '')}</small></td><td><details><summary>Original fields</summary><dl class="csv-raw">${Object.entries(row.raw || {}).map(([key,value])=>`<dt>${escapeHtml(key)}</dt><dd>${escapeHtml(value)}</dd>`).join('')}</dl>${row.extra_cells?.length ? `<p>Extra cells: ${escapeHtml(JSON.stringify(row.extra_cells))}</p>` : ''}${(row.issues||[]).map(issue=>`<p>${escapeHtml(issue)}</p>`).join('')}</details></td></tr>`).join(''));
    $('evidence-csv-prev').disabled = offset===0;
    $('evidence-csv-next').disabled = pages.has_more == null ? offset+rows.length>=total : !pages.has_more;
    $('evidence-csv-results').hidden = false;
  }
  async function loadRows() {
    if (!source) return;
    const ticket = ++revision;
    const committee = $('evidence-csv-committee').value, cycle = $('evidence-csv-cycle').value;
    say('Reading selected PAC rows…');
    $('evidence-csv-results').hidden = true;
    $('evidence-csv-prev').disabled = true; $('evidence-csv-next').disabled = true;
    try {
      const body = await api('/api/evidence-csv?' + new URLSearchParams({id:source.id,committee,cycle,offset:String(offset),limit:String(pageSize)}));
      if (ticket!==revision) return;
      const cycles = (body.cycles || []).map(String);
      $('evidence-csv-cycle').replaceChildren(new Option('All cycles',''),...cycles.map(value=>new Option(value,value)));
      if(cycles.includes(cycle)) $('evidence-csv-cycle').value = cycle;
      $('evidence-csv-cycle').disabled = !cycles.length;
      renderRows(body); say(`${source.name} · ${number(source.row_count)} rows in file`);
    } catch (error) {
      if (ticket!==revision) return;
      say(`GET /api/evidence-csv?id=${source.id}&committee=${committee}&cycle=${cycle}: ${error.message}`);
      if (String(error.message).includes('no longer on disk')) refreshSources();
    }
  }
  async function followJob(job, ticket, chosenName) {
    let current = job, failures = 0;
    while (ticket === revision) {
      const label = current.name || chosenName;
      if (current.state === 'failed') {
        showSheets(current);
        say(`${label}: ${current.message || 'The CSV could not be read.'}`);
        return;
      }
      if (current.state === 'ready') {
        showSheets(current);
        source = current.catalog; offset = 0;
        await refreshSources();
        if (ticket !== revision) return;
        fillCommittees(source.committees || []);
        await loadRows();
        return;
      }
      say(current.bytes_read
        ? `Reading ${label} · ${number(current.rows_read)} rows · ${megabytes(current.bytes_read)} of ${megabytes(current.bytes)} MB`
        : `Reading ${label} · ${number(current.rows_read)} rows`);
      await new Promise(resolve => setTimeout(resolve, pollDelay));
      if (ticket !== revision) return;
      try {
        current = await api('/api/evidence-csv?' + new URLSearchParams({job:job.id}));
        failures = 0;
      } catch (error) {
        // One failed poll is not a failed import. The read can lose a race
        // with the progress the reader itself is writing, and giving up on the
        // first one stranded the page on an error while the file went on being
        // read behind it. Keep the last good state and try again; say so, and
        // stop only once the failures are clearly not transient.
        failures += 1;
        say(`${label}: GET /api/evidence-csv?job=${job.id} failed: ${error.message}`
            + (failures < pollFailureLimit ? ' Retrying.' : ''));
        if (failures >= pollFailureLimit) return;
      }
    }
  }
  async function importFile(file, sheet) {
    const ticket = ++revision; resetSelection(); hideSheetPicker();
    const suffix = suffixOf(file.name);
    if (limits && limits.accepted_suffixes && !limits.accepted_suffixes.includes(suffix)) {
      say(`${file.name}: This file type (${suffix}) is not supported. Choose CSV, TSV, TXT, XLSX, JSON or an FEC bulk ZIP.`);
      return;
    }
    if (limits && file.size > limits.max_bytes) {
      say(`${file.name} (${megabytes(file.size)} MB): ${limits.max_bytes_message}`);
      return;
    }
    pendingUploadFile = file; pendingPathRequest = null;
    say(`Uploading ${file.name}…`);
    let response;
    try {
      const headers = {'Content-Type': suffix === '.csv' ? 'text/csv' : 'application/octet-stream',
        'X-Mentat-Token':token, 'X-Evidence-Name':encodeURIComponent(file.name)};
      if (sheet) headers['X-Evidence-Sheet'] = encodeURIComponent(sheet);
      response = await fetch('/api/evidence-csv', {method:'POST', headers, body:file});
    } catch (error) {
      if (ticket===revision) say(`${file.name}: upload to /api/evidence-csv failed: ${error.message}`);
      return;
    }
    if (ticket!==revision) return;
    let body = null;
    try { body = await response.json(); } catch { body = null; }
    if (ticket!==revision) return;
    if (!body || typeof body !== 'object') {
      say(`${file.name}: /api/evidence-csv answered HTTP ${response.status} with no error message.`);
      return;
    }
    if (!response.ok) { say(`${file.name}: ${body.error || `/api/evidence-csv answered HTTP ${response.status} with no error message.`}`); return; }
    await followJob(body, ticket, file.name);
  }
  async function importPath(path, sheet, headerPath) {
    const ticket = ++revision; resetSelection(); hideSheetPicker();
    pendingPathRequest = {path, header_path: headerPath || ''}; pendingUploadFile = null;
    $('evidence-path').value = path;
    say(`Reading ${path}…`);
    let job;
    try {
      job = await api('/api/evidence-csv', {path, sheet: sheet || '', header_path: headerPath || ''});
    } catch (error) {
      if (ticket===revision) say(`${path}: ${error.message}`);
      return;
    }
    if (ticket!==revision) return;
    await followJob(job, ticket, path);
  }
  function readPathBox() {
    const path = $('evidence-path').value.trim();
    if (!path) { say('Enter a path on this computer, then choose Read this file.'); return; }
    importPath(path, '', $('evidence-header-path').value.trim());
  }
  function renderBrowser(body) {
    const header = `<p class="muted">${escapeHtml(body.path || 'This computer')}</p>`;
    const up = body.parent ? `<button type="button" class="secondary" data-browse-path="${escapeHtml(body.parent)}">Up</button>` : '';
    const roots = (body.roots || []).map(root => `<button type="button" class="secondary" data-browse-path="${escapeHtml(root)}">${escapeHtml(root)}</button>`).join('');
    const shortcuts = (body.shortcuts || []).map(item => `<button type="button" class="secondary" data-browse-path="${escapeHtml(item.path)}">${escapeHtml(item.name)}</button>`).join('');
    const rows = (body.entries || []).map(entry => {
      const size = entry.kind === 'dir' ? '' : number(entry.size);
      const modified = escapeHtml(String(entry.modified || '').slice(0,10));
      const cells = `<td>${escapeHtml(entry.name)}</td><td>${escapeHtml(entry.kind)}</td><td class="number">${size}</td><td>${modified}</td>`;
      if (entry.kind === 'dir') return `<tr data-browse-path="${escapeHtml(entry.path)}">${cells}</tr>`;
      if (entry.supported) return `<tr data-open-path="${escapeHtml(entry.path)}">${cells}</tr>`;
      return `<tr class="muted" title="Not a supported file type">${cells}</tr>`;
    }).join('');
    const truncated = body.truncated ? '<p class="muted">Showing the first 2,000 entries.</p>' : '';
    setHtml('evidence-browser', `${header}<div class="evidence-toolbar">${up}${roots}${shortcuts}</div><div class="table-scroll"><table><thead><tr><th>Name</th><th>Kind</th><th>Size</th><th>Modified</th></tr></thead><tbody>${rows}</tbody></table></div>${truncated}`);
  }
  async function browse(path) {
    let body;
    try {
      body = await api('/api/evidence-files', {path: path || ''});
    } catch (error) {
      say(error.message);
      return;
    }
    renderBrowser(body);
  }
  $('evidence-csv-file').addEventListener('change', () => {
    const file = $('evidence-csv-file').files[0]; if (!file) return;
    importFile(file, '');
  });
  $('evidence-sheet').addEventListener('change', () => {
    const sheet = $('evidence-sheet').value;
    if (pendingUploadFile) importFile(pendingUploadFile, sheet);
    else if (pendingPathRequest) importPath(pendingPathRequest.path, sheet, pendingPathRequest.header_path);
  });
  $('evidence-path-read').addEventListener('click', readPathBox);
  $('evidence-path').addEventListener('keydown', event => { if (event.key === 'Enter') { event.preventDefault(); readPathBox(); } });
  $('evidence-browse').addEventListener('click', () => {
    const opening = $('evidence-browser').hidden;
    $('evidence-browser').hidden = !opening;
    if (opening) browse(directoryOf($('evidence-path').value));
  });
  $('evidence-browser').addEventListener('click', event => {
    const openTarget = event.target.closest('[data-open-path]');
    if (openTarget) { importPath(openTarget.dataset.openPath, '', $('evidence-header-path').value.trim()); return; }
    const browseTarget = event.target.closest('[data-browse-path]');
    if (browseTarget) browse(browseTarget.dataset.browsePath);
  });
  for (const id of ['evidence-csv-committee','evidence-csv-cycle']) $(id).addEventListener('change',()=>{offset=0;loadRows();});
  $('evidence-csv-prev').addEventListener('click',()=>{offset=Math.max(0,offset-pageSize);loadRows();});
  $('evidence-csv-next').addEventListener('click',()=>{offset+=pageSize;loadRows();});
  refreshSources();
})();
