/* PAC evidence: one scope bar, up to four PAC panes side by side from any
   imported industry file or saved FEC snapshot, and a comparison strip.

   This module owns the whole tab. It replaces evidence-csv.js (the import
   mechanics moved into the Import drawer here) and the snapshot half that
   used to live in app.js: one heading, one status region, one picker.

   Pane state is `{source: 'csv'|'snapshot', id, committee, cycle}` per pane,
   round-tripped through the URL under the prefixed keys a.* - d.* (scope.js;
   D-039). The single-pane keys the HANDOFF reserved for S6 (`evidence`, `id`,
   `committee`, `offset`, `limit`) are superseded and never written.

   Figures come from two routes and nothing is recomputed from rows the page
   never asked for: GET /api/evidence-csv?...&summary=1 for an import's
   committee, GET /api/evidence?id= for a snapshot. Rows stay on the paginated
   SELECT, inside the pane that asked for them. */
(() => {
  const PANE_KEYS = ['a', 'b', 'c', 'd'];
  const MAX_PANES = PANE_KEYS.length;
  const PAGE_SIZE = 100;
  const POLL_DELAY = 500;
  const POLL_FAILURE_LIMIT = 5;
  const NOT_REPORTED = 'Not reported';
  // F4. The mockup shows five in the pane; the summary answers ten and the rest
  // are spelled out in the About popover, so the depth is reachable, not gone.
  const TOP_IN_PANE = 5;

  /* ------------------------------------------------------------- formatting */
  const channelName = value => String(value || 'Unclassified').replaceAll('_', ' ');
  const money = value => value == null ? '—'
    : (value < 0 ? '-' : '') + '$' + Math.round(Math.abs(value)).toLocaleString('en-US');
  const megabytes = value => (Number(value || 0) / 1e6).toFixed(1);
  const cycleLabel = value => value ? `${Number(value) - 1}–${value}` : 'All cycles';
  // F1. A catalog name is whatever the filing carries: CULAC's is
  // "AMERICA'S CREDIT UNIONS PAC OF CREDIT UNION NATIONAL ASSOCIATION, INC. /
  // CULAC THE PAC OF CREDIT UNION NATIONAL ASSOCIATION", five lines in a pane
  // title and a chip row of its own. Everything the reader SCANS - chip, pane
  // title, compare heading, PAC option - gets the text before the first " / ",
  // capped at 34 characters; the full name rides on a title attribute and is
  // spelled out in the About popover, so nothing is hidden, only folded.
  const NAME_LIMIT = 34;
  const shortName = value => {
    const text = String(value == null ? '' : value).trim();
    const head = (text.split(' / ')[0] || text).trim() || text;
    return head.length > NAME_LIMIT ? head.slice(0, NAME_LIMIT - 1).trimEnd() + '\u2026' : head;
  };
  const suffixOf = name => { const at = String(name || '').lastIndexOf('.'); return at === -1 ? '' : String(name).slice(at).toLowerCase(); };
  const directoryOf = value => {
    const trimmed = String(value || '').trim();
    if (!trimmed) return '';
    const stripped = trimmed.replace(/[\\/]+$/, '');
    if (!stripped) return trimmed;
    const at = Math.max(stripped.lastIndexOf('\\'), stripped.lastIndexOf('/'));
    return at === -1 ? '' : trimmed.slice(0, at + 1);
  };
  // Only FEC-hosted filing links are turned into anchors; anything else is
  // shown as text, so a snapshot can never plant a link in the page.
  const sourceAnchor = (url, text) => /^https:\/\/(docquery\.fec\.gov|www\.fec\.gov)\//.test(url || '')
    ? `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(text)} ↗</a>`
    : escapeHtml(text);
  const render = (element, html) => { if (element && element.innerHTML !== html) element.innerHTML = html; };
  const say = text => { $('evidence-status').textContent = text; };
  // The bar in a figure or compare cell: normalised per row, a full bar for the
  // largest value and a visible sliver for anything positive, so $178M beside
  // $37K reads as the difference it is rather than as two full bars.
  //
  // The width rides on data-bar-width and is applied through the CSSOM after
  // the markup lands, because the console serves
  // `Content-Security-Policy: ... style-src 'self'` (server.py:1944): a
  // style="width:..%" attribute written into innerHTML is BLOCKED, and every
  // bar in the page silently measured zero. graph.js:163 sets its bars the same
  // way. Measured, not assumed - a real-client pass read style.width as ''.
  const barWidth = (value, peak) => !value || value <= 0 ? 0 : Math.max(1, Math.round(value / peak * 100));
  const bar = (value, peak, thin) =>
    `<div class="bartrack"><div class="bar${thin ? ' thin' : ''}" data-bar-width="${barWidth(value, peak)}"></div></div>`;
  function applyBars(root) {
    if (!root) return;
    for (const node of root.querySelectorAll('[data-bar-width]')) node.style.width = node.dataset.barWidth + '%';
  }

  /* ------------------------------------------------------------------ state */
  let imports = [], snapshots = [], limits = null;
  const snapshotBodies = new Map();       // snapshot id -> /api/evidence?id= body
  const panes = new Map();                // 'a'..'d' -> pane state
  let revision = 0, importRevision = 0;
  let pendingUploadFile = null, pendingPathRequest = null;
  let rereadTimer = null, rereadDeadline = 0;
  let graphContext = null;
  let started = false, restored = false;
  let collectorAvailable = false, collectorReadOnly = false;
  let evidenceJob = '', evidenceJobTimer = 0;

  const scope = () => (typeof MentatScope === 'undefined' ? null : MentatScope);
  const sourceValue = () => $('evidence-source').value;
  const parseSourceValue = value => {
    const at = String(value || '').indexOf(':');
    return at === -1 ? {kind: '', id: ''} : {kind: value.slice(0, at), id: value.slice(at + 1)};
  };
  const importById = id => imports.find(item => item.id === id) || null;
  const snapshotById = id => snapshots.find(item => item.id === id) || null;

  /* ---------------------------------------------------- the committee lists */
  // A file can hold 523 PACs (the Crypto workbook does), so the picker is a
  // committee-type filter and a search over one rebuilt select. A committee the
  // file never categorised reads as Unclassified, the same word the FEC
  // committee master falls back to, so one option covers both.
  const categoryOf = item => item.category || 'Unclassified';
  const committeeOrder = item => item.id === 'unassigned' ? '￿' : String(item.name || item.id).toLowerCase();

  function chosenCommittees() {
    const chosen = parseSourceValue(sourceValue());
    if (chosen.kind === 'csv') {
      const source = importById(chosen.id);
      return source ? (source.committees || []) : [];
    }
    if (chosen.kind === 'snapshot') {
      const body = snapshotBodies.get(chosen.id);
      if (!body) return [];
      const seen = new Map();
      for (const row of body.committee_finances || []) {
        const current = seen.get(row.committee_id);
        const rows = (current ? current.rows : 0) + 1;
        seen.set(row.committee_id, {id: row.committee_id, name: row.committee_name || row.committee_id,
          category: row.category || '', category_source: row.category_source || '',
          rows: rows, supported_rows: rows, excluded_rows: 0});
      }
      return [...seen.values()];
    }
    return [];
  }

  function chosenCategories() {
    const chosen = parseSourceValue(sourceValue());
    if (chosen.kind === 'csv') {
      const source = importById(chosen.id);
      return source ? (source.categories || []) : [];
    }
    const buckets = new Map();
    for (const item of chosenCommittees()) {
      if (!item.category) continue;
      const bucket = buckets.get(item.category) || {category: item.category, committees: 0};
      bucket.committees += 1;
      buckets.set(item.category, bucket);
    }
    return [...buckets.values()];
  }

  function chosenCycles() {
    const chosen = parseSourceValue(sourceValue());
    if (chosen.kind === 'csv') {
      const source = importById(chosen.id);
      return source ? (source.cycles || []).map(String) : [];
    }
    const body = snapshotBodies.get(chosen.id);
    if (!body) return [];
    return [...new Set((body.committee_finances || []).map(row => String(row.cycle)))].sort().reverse();
  }

  function visibleCommittees() {
    const type = $('evidence-type').value;
    const text = $('evidence-find').value.trim().toLowerCase();
    return chosenCommittees()
      .filter(item => !type || categoryOf(item) === type)
      .filter(item => !text || String(item.name || '').toLowerCase().includes(text)
                            || String(item.id || '').toLowerCase().includes(text))
      .sort((a, b) => committeeOrder(a).localeCompare(committeeOrder(b)));
  }

  function fillTypes() {
    const select = $('evidence-type'), previous = select.value;
    const items = chosenCategories();
    select.replaceChildren(new Option('All types', ''),
      ...items.map(item => new Option(`${item.category} · ${number(item.committees)}`, item.category)));
    select.value = items.some(item => item.category === previous) ? previous : '';
    select.disabled = !items.length;
    $('evidence-find').disabled = !chosenCommittees().length;
  }

  function fillCycles() {
    const select = $('evidence-cycle'), previous = select.value;
    const cycles = chosenCycles();
    select.replaceChildren(new Option('All cycles', ''), ...cycles.map(value => new Option(cycleLabel(value), value)));
    if (cycles.includes(previous)) select.value = previous;
    select.disabled = !cycles.length;
  }

  function fillPacs() {
    const select = $('evidence-pac'), previous = select.value;
    const visible = visibleCommittees();
    select.replaceChildren(...visible.map(item => new Option(
      `${shortName(item.name || item.id)} · ${item.id} · ${categoryOf(item)}`
      + (item.rows == null ? '' : ` · ${number(item.rows)} row${Number(item.rows) === 1 ? '' : 's'}`), item.id)));
    select.disabled = !visible.length;
    if (visible.some(item => item.id === previous)) select.value = previous;
    else if (visible.length) select.value = visible[0].id;
  }

  function scopeStatus() {
    const chosen = parseSourceValue(sourceValue());
    if (!chosen.kind) return imports.length || snapshots.length
      ? `${number(imports.length)} imported file${imports.length === 1 ? '' : 's'} and ${number(snapshots.length)} saved snapshot${snapshots.length === 1 ? '' : 's'} on this computer · choose a source`
      : 'Nothing imported yet. Import a file, or collect a snapshot.';
    const all = chosenCommittees(), visible = visibleCommittees();
    const type = $('evidence-type').value, text = $('evidence-find').value.trim();
    const source = chosen.kind === 'csv' ? importById(chosen.id) : snapshotById(chosen.id);
    const name = source ? (source.name || source.company || chosen.id) : chosen.id;
    return `${name} · ${number(all.length)} PACs in file · ${number(visible.length)} shown`
      + (type ? ` (${type})` : '') + (text ? ` matching "${text}"` : '')
      + (chosen.kind === 'csv' && source ? ` · ${number(source.row_count)} rows in file` : '')
      // The pane ceiling is a SUFFIX, not a replacement: the status region also
      // carries import progress, and with four panes open it used to swallow
      // every "Reading x.xlsx" line the reader was waiting on.
      + (panes.size >= MAX_PANES ? ` · ${MAX_PANES} panes open · remove one to add another` : '');
  }

  function updateAdd() {
    const chosen = parseSourceValue(sourceValue());
    const committee = $('evidence-pac').value;
    const already = [...panes.values()].some(pane => pane.source === chosen.kind
      && pane.id === chosen.id && pane.committee === committee);
    $('evidence-add').disabled = !chosen.kind || !committee || already || panes.size >= MAX_PANES;
  }

  function applyFilter() {
    fillPacs();
    updateAdd();
    say(scopeStatus());
  }

  /* ------------------------------------------------------------ the sources */
  function sourceLabel(item) {
    return `${item.industry || item.name} · ${number(item.row_count)} rows`
      + (item.reread ? ' · re-reading under the current rules' : '');
  }

  function fillSourceSelect(keep) {
    const select = $('evidence-source');
    const options = [new Option('Choose a file or a snapshot', '')];
    for (const item of imports) {
      const option = new Option(sourceLabel(item), 'csv:' + item.id);
      option.disabled = !!item.reread;
      options.push(option);
    }
    for (const item of snapshots) {
      options.push(new Option(`Snapshot · ${item.company || item.id} · ${(item.cycles || []).join(', ') || 'no cycles'}`,
        'snapshot:' + item.id));
    }
    select.replaceChildren(...options);
    select.value = [...select.options].some(option => option.value === keep && !option.disabled) ? keep : '';
  }

  async function refreshSources() {
    const keep = sourceValue();
    const [listing, catalog] = await Promise.all([
      api('/api/evidence-csv').catch(error => ({error: error.message})),
      api('/api/evidence').catch(() => ({snapshots: []})),
    ]);
    if (listing.error) { say('GET /api/evidence-csv failed: ' + listing.error); }
    else { limits = listing.limits || limits; imports = listing.sources || []; }
    snapshots = (catalog.snapshots || []).slice()
      .sort((a, b) => String(b.retrieved_at || '').localeCompare(String(a.retrieved_at || '')));
    fillSourceSelect(keep);
    watchRereads();
    return imports;
  }

  // An import read under an older rule set is re-read by the console on the
  // first listing, so its entry is briefly unusable. Poll until it is back, and
  // give up after ten minutes rather than polling a console that is never going
  // to answer differently.
  function watchRereads() {
    const waiting = imports.filter(item => item.reread).map(item => item.id);
    if (!waiting.length) { rereadDeadline = 0; return; }
    if (!rereadDeadline) rereadDeadline = Date.now() + 600000;
    if (Date.now() > rereadDeadline || rereadTimer) return;
    rereadTimer = setTimeout(async () => {
      rereadTimer = null;
      await refreshSources();
      applyFilter();
      for (const pane of panes.values()) if (pane.source === 'csv' && waiting.includes(pane.id)) loadPane(pane);
    }, 2000);
  }

  async function chooseSource() {
    const chosen = parseSourceValue(sourceValue());
    $('evidence-type').value = ''; $('evidence-find').value = '';
    if (chosen.kind === 'snapshot' && !snapshotBodies.has(chosen.id)) {
      say('Reading the saved snapshot…');
      try { snapshotBodies.set(chosen.id, await api('/api/evidence?id=' + encodeURIComponent(chosen.id))); }
      catch (error) { say(`GET /api/evidence?id=${chosen.id}: ${error.message}`); return; }
    }
    fillTypes(); fillCycles(); applyFilter();
  }

  /* -------------------------------------------------------------- the panes */
  function freeKey() { return PANE_KEYS.find(key => !panes.has(key)) || ''; }

  function paneFrom(key, source, id, committee, cycle) {
    return {key, source, id, committee, cycle: cycle || '', follows: false,
      offset: 0, rowsOpen: false, rows: null, loaded: false, message: '',
      name: committee, industry: '', sourceKind: '', category: '', categorySource: '',
      totals: [], totalsByCycle: {}, counterparties: [], cycles: [],
      rowCount: null, supported: null, excluded: null, unsupported: null,
      provenance: '', warnings: [], legs: [], detail: ''};
  }

  async function loadPane(pane) {
    const ticket = ++revision;
    pane.loaded = false; pane.message = 'Reading…';
    renderPanes();
    try {
      if (pane.source === 'csv') await loadCsvPane(pane);
      else await loadSnapshotPane(pane);
      pane.message = '';
      pane.loaded = true;
    } catch (error) {
      pane.message = error.message;
    }
    if (ticket > revision) return;
    renderPanes(); renderChips(); renderCompare(); say(scopeStatus());
  }

  async function loadCsvPane(pane) {
    const query = new URLSearchParams({id: pane.id, committee: pane.committee, cycle: pane.cycle, summary: '1'});
    const body = await api('/api/evidence-csv?' + query);
    pane.name = body.committee.name || body.committee.id;
    pane.category = body.committee.category || 'Unclassified';
    pane.categorySource = body.committee.category_source || 'Not recorded';
    pane.rowCount = body.committee.rows;
    pane.supported = body.committee.supported_rows;
    pane.excluded = body.committee.excluded_rows;
    pane.unsupported = body.counts.unsupported;
    pane.totals = body.totals || [];
    pane.totalsByCycle = body.totals_by_cycle || {};
    pane.counterparties = body.counterparties || [];
    pane.cycles = (body.cycles || []).map(String);
    pane.industry = body.source.industry || '';
    pane.sourceKind = body.source.industry ? 'Spending workbook' : 'Imported file';
    const source = importById(pane.id);
    pane.provenance = `${body.source.name}`
      + (source ? ` · ${number(source.row_count)} rows · sha ${String(source.sha256 || '').slice(0, 8)}` : '');
    pane.warnings = source ? (source.warnings || []) : [];
    pane.detail = source ? fileDetail(source) : '';
    pane.legs = [];
  }

  function fileDetail(source) {
    return `${source.name} · Imported UTF-8 text SHA-256 ${source.sha256} · ${number(source.row_count)} file rows.`
      + (source.source_kind === 'path' && source.source_path ? ` Read from ${source.source_path}.` : '')
      + ' Stored on this computer under the console data root; visible to every Mentat console that uses it.'
      + ' Values are observed filings or labeled cycle aggregates, not donor allocations or reconciled giving totals.';
  }

  async function loadSnapshotPane(pane) {
    let body = snapshotBodies.get(pane.id);
    if (!body) {
      body = await api('/api/evidence?id=' + encodeURIComponent(pane.id));
      snapshotBodies.set(pane.id, body);
    }
    const finances = (body.committee_finances || []).filter(row => row.committee_id === pane.committee);
    if (!finances.length) throw new Error(`${pane.committee} is not in the snapshot ${pane.id}.`);
    const cycles = [...new Set(finances.map(row => String(row.cycle)))].sort().reverse();
    const inCycle = pane.cycle ? finances.filter(row => String(row.cycle) === pane.cycle) : finances;
    const sum = (rows, field) => rows.reduce((total, row) => total + Number(row[field] || 0), 0);
    pane.name = finances[0].committee_name || pane.committee;
    pane.category = finances[0].category || 'Unclassified';
    pane.categorySource = finances[0].category_source || 'From the saved snapshot';
    pane.cycles = cycles;
    pane.industry = body.company || '';
    pane.sourceKind = `Saved FEC snapshot · ${String(body.retrieved_at || '').slice(0, 10) || 'undated'}`;
    pane.rowCount = null; pane.supported = null; pane.excluded = null; pane.unsupported = null;
    pane.totals = [
      {channel: 'Receipts as reported', amount: sum(inCycle, 'receipts_as_reported'), row_count: 0},
      {channel: 'Independent spending · reported', amount: sum(inCycle, 'regular_ie_total'), row_count: 0},
    ].filter(item => item.amount);
    pane.totalsByCycle = {};
    for (const cycle of cycles) {
      const rows = finances.filter(row => String(row.cycle) === cycle);
      pane.totalsByCycle[cycle] = [
        {channel: 'Receipts as reported', amount: sum(rows, 'receipts_as_reported'), row_count: 0},
      ];
    }
    const receipts = (body.receipts || []).filter(row => row.committee_id === pane.committee
      && (!pane.cycle || String(row.cycle) === pane.cycle));
    const outgoing = (body.transfers || []).filter(row => row.source === pane.committee
      && (!pane.cycle || String(row.cycle) === pane.cycle));
    const incoming = (body.transfers || []).filter(row => row.destination === pane.committee
      && (!pane.cycle || String(row.cycle) === pane.cycle));
    const activity = (body.candidate_activity || []).filter(row => row.committee_id === pane.committee
      && (!pane.cycle || String(row.cycle) === pane.cycle));
    const support = activity.filter(row => /support/i.test(row.direction || ''));
    const oppose = activity.filter(row => !/support/i.test(row.direction || ''));
    pane.counterparties = [
      {name: `${body.company || 'Company'} receipt legs`, amount: receipts.reduce((t, r) => t + Number(r.amount || 0), 0), rows: receipts.length},
      {name: 'Transfers out to other committees', amount: outgoing.reduce((t, r) => t + Number(r.amount || 0), 0), rows: outgoing.length},
      {name: 'Transfers in from other committees', amount: incoming.reduce((t, r) => t + Number(r.amount || 0), 0), rows: incoming.length},
      {name: 'Candidate activity · support', amount: support.reduce((t, r) => t + Number(r.committee_spending || 0), 0), rows: support.length},
      {name: 'Candidate activity · oppose', amount: oppose.reduce((t, r) => t + Number(r.committee_spending || 0), 0), rows: oppose.length},
    ].filter(item => item.rows);
    pane.provenance = `Snapshot ${pane.id} · openFEC · receipts as reported`;
    pane.warnings = [finances.every(row => row.regular_ie_reconciles)
      ? 'The collected regular-report expenditure total matches the committee financial summary.'
      : 'The collected regular-report expenditure total differs from the financial summary. Coverage remains unresolved; no donor allocation is calculated.'];
    pane.detail = `Evidence collected ${String(body.retrieved_at || '').slice(0, 10) || 'date unavailable'}. ${body.scope || ''}`;
    pane.legs = {receipts, outgoing, incoming, activity, finances: inCycle, body};
  }

  /* ------------------------------------------------------------- rendering  */
  function mainFigure(pane) {
    const leading = (pane.totals || []).slice().sort((a, b) => b.amount - a.amount)[0];
    return leading || {channel: 'Receipts', amount: null, row_count: 0};
  }

  function paneHtml(pane) {
    const leading = mainFigure(pane);
    const cycles = Object.keys(pane.totalsByCycle || {}).sort().reverse();
    const cycleTotal = cycle => (pane.totalsByCycle[cycle] || []).reduce((total, item) => total + item.amount, 0);
    const peak = Math.max(1, ...cycles.map(cycleTotal));
    const isSnapshot = pane.source === 'snapshot';
    const rowsNote = pane.rowCount == null ? 'snapshot: legs, not file rows'
      : (pane.excluded ? `${number(pane.supported)} supported · ${number(pane.excluded)} excluded by the workbook`
                       : `${number(pane.supported)} supported`);
    const topLabel = isSnapshot ? 'Snapshot legs' : 'Top contributors in this file';
    return `<section class="panel evidence-pane" data-pane="${pane.key}" data-committee="${escapeHtml(pane.committee)}" aria-label="${escapeHtml(pane.name)} pane">
      <div class="pane-head">
        <div class="pane-title">
          <div class="pane-kind">${escapeHtml(pane.industry || 'Imported file')} · ${escapeHtml(pane.sourceKind)}</div>
          <h2 title="${escapeHtml(pane.name)}">${escapeHtml(shortName(pane.name))}</h2>
          <div class="pane-tags">
            <span class="badge" title="${escapeHtml(pane.categorySource)}">${escapeHtml(pane.category)}</span>
            <span class="muted">${escapeHtml(pane.committee)}</span>
            <span class="muted">${escapeHtml(cycleLabel(pane.cycle))}</span>
            ${pane.follows ? '<span class="badge">follows Graph</span>' : ''}
          </div>
        </div>
        <div class="pane-buttons">
          <button type="button" class="secondary pane-map">Map</button>
          <button type="button" class="secondary pane-rows" aria-expanded="${pane.rowsOpen}">${pane.rowsOpen ? 'Hide rows' : 'Rows'}</button>
          <button type="button" class="secondary pane-remove" aria-label="Remove ${escapeHtml(shortName(pane.name))}">×</button>
        </div>
      </div>
      ${pane.message ? `<p class="muted pane-message">${escapeHtml(pane.message)}</p>` : ''}
      <div class="pane-figures">
        <div class="pane-figure"><span class="label">${escapeHtml(channelName(leading.channel))}</span>
          <strong>${money(leading.amount)}</strong>
          <span class="muted">${isSnapshot ? 'FEC financial summary for the cycle'
            : `${number(leading.row_count)} supported rows`}</span></div>
        <div class="pane-figure"><span class="label">Rows in file</span>
          <strong>${pane.rowCount == null ? '—' : number(pane.rowCount)}</strong>
          <span class="muted">${escapeHtml(rowsNote)}</span></div>
      </div>
      ${(pane.totals || []).length > 1 ? `<div class="pane-channels">${(pane.totals || []).slice(1).map(item =>
        `<div><span class="muted">${escapeHtml(channelName(item.channel))}</span><span class="num">${money(item.amount)}</span></div>`).join('')}</div>` : ''}
      <div class="pane-cycles"><span class="label">By cycle</span>
        ${cycles.length ? cycles.map(cycle => `<div class="pane-cycle"><span class="muted">${escapeHtml(cycleLabel(cycle))}</span>
          ${bar(cycleTotal(cycle), peak)}<span class="num">${money(cycleTotal(cycle))}</span></div>`).join('')
          : '<p class="muted">No cycle is recorded for these rows.</p>'}</div>
      <div class="pane-top"><span class="label">${topLabel}</span>
        ${(pane.counterparties || []).length ? `<table><tbody>${(pane.counterparties || []).slice(0, TOP_IN_PANE).map(item =>
          `<tr><td title="${escapeHtml(item.name)}">${escapeHtml(item.name)}</td><td class="num">${money(item.amount)}</td></tr>`).join('')}</tbody></table>`
          : '<p class="muted">No counterparty is named on these rows.</p>'}</div>
      ${pane.rowsOpen ? paneDrawerHtml(pane) : ''}
      <p class="muted pane-provenance">${escapeHtml(pane.provenance)} ·
        <button type="button" class="link-button pane-about" aria-expanded="false">About these figures</button></p>
      <div class="pane-about-body" hidden><p><strong>${escapeHtml(pane.name)}</strong> · ${escapeHtml(pane.committee)}</p>
        <p>${escapeHtml(pane.detail)}</p><ul>${(pane.warnings || [])
        .map(warning => `<li>${escapeHtml(typeof warning === 'string' ? warning : warning.message || JSON.stringify(warning))}</li>`).join('')
        || '<li>No parser warnings. Source coverage and filing completeness remain unverified.</li>'}</ul>
        ${(pane.counterparties || []).length > TOP_IN_PANE ? `<p>Also in the top ten: ${(pane.counterparties || [])
          .slice(TOP_IN_PANE).map(item => `${escapeHtml(item.name)} ${money(item.amount)}`).join(' · ')}.</p>` : ''}
        <p class="muted">Sums reflect the selected rows. Receipts, disbursements and independent spending stay separate; amended or duplicate filings may overlap.</p></div>
    </section>`;
  }

  function paneDrawerHtml(pane) {
    return pane.source === 'snapshot' ? snapshotDrawerHtml(pane) : csvDrawerHtml(pane);
  }

  function csvDrawerHtml(pane) {
    const body = pane.rows;
    if (!body) return '<div class="pane-drawer"><p class="muted">Reading rows…</p></div>';
    // S8. A district clicked on the map filters this page of rows by the
    // contributor ZIP, through the same crosswalk that drew the map; the
    // header says which district and on what basis, and Clear puts it back.
    const rows = rowsInDistrict(pane, body.rows || []);
    const total = body.total_rows ?? rows.length;
    const excluded = body.excluded_rows ?? 0;
    return `<div class="pane-drawer">
      ${pane.district ? `<p class="pane-district-filter">Filtered to <strong>${escapeHtml(pane.district)}</strong>`
        + `${pane.districtBasis ? ' by ' + escapeHtml(pane.districtBasis) : ''} · ${number(rows.length)} of ${number((body.rows || []).length)} rows on this page`
        + ` <button type="button" class="link-button pane-district-clear">Clear</button></p>` : ''}
      <span class="label">Source rows · ${total ? `${number(pane.offset + 1)}–${number(pane.offset + rows.length)} of ${number(total)}` : 'no matching rows'}</span>
      <p class="muted">${number(body.supported_rows ?? 0)} supported${excluded ? ` · ${number(excluded)} excluded by the workbook` : ''} · ${number(body.unsupported_rows ?? 0)} need interpretation. All selected rows contribute to the figures above, across pages.</p>
      <div class="table-scroll"><table><thead><tr><th>Row</th><th>Date / cycle</th><th class="num">Amount</th><th>Counterparty / activity</th><th>Status</th></tr></thead><tbody>
      ${rows.map(row => `<tr><td>${number(row.row_number)}</td>
        <td>${escapeHtml(row.date || 'Date unavailable')}<small>${escapeHtml(row.cycle || 'Cycle unavailable')}</small></td>
        <td class="num">${row.amount == null ? 'Not reported' : currency(row.amount)}</td>
        <td>${escapeHtml(row.counterparty || row.candidate_name || row.candidate_id || NOT_REPORTED)}<small>${escapeHtml(channelName(row.channel || row.kind))}</small></td>
        <td>${row.status === 'excluded' ? '<span class="badge excluded">excluded by the workbook</span>'
              : `<span class="muted">${escapeHtml(row.status || '')}</span>`}
          <details><summary>Original fields</summary><dl class="csv-raw">${Object.entries(row.raw || {})
            .map(([key, value]) => `<dt>${escapeHtml(key)}</dt><dd>${escapeHtml(value)}</dd>`).join('')}</dl>
          ${(row.issues || []).map(issue => `<p>${escapeHtml(issue)}</p>`).join('')}</details></td></tr>`).join('')}
      </tbody></table></div>
      <div class="csv-pagination"><button type="button" class="secondary pane-prev"${pane.offset === 0 ? ' disabled' : ''}>Previous rows</button>
        <button type="button" class="secondary pane-next"${body.has_more ? '' : ' disabled'}>Next rows</button></div></div>`;
  }

  function snapshotDrawerHtml(pane) {
    const legs = pane.legs || {};
    const body = legs.body || {};
    const estimate = (body.cash_estimates?.cycles || []).find(row => String(row.cycle) === (pane.cycle || String(row.cycle)));
    const names = new Map((body.committee_finances || []).map(row => [row.committee_id, row.committee_name || row.committee_id]));
    return `<div class="pane-drawer">
      <span class="label">Company → PAC → candidates</span>
      <p class="muted">Explore the recorded legs. Spending from a pooled PAC is committee activity; it cannot be assigned to a particular donor without further evidence.</p>
      <h3 class="evidence-subheading">Committee transfers</h3>
      ${(legs.incoming || []).map(row => `<p>${escapeHtml(names.get(row.source) || row.source)} → ${escapeHtml(pane.name)} <b>${currency(row.amount)}</b></p>`).join('')}
      ${(legs.outgoing || []).map(row => `<p>${escapeHtml(pane.name)} → ${escapeHtml(row.destination_name || names.get(row.destination) || row.destination)} <b>${currency(row.amount)}</b></p>`).join('')
        || '<p class="muted">No contribution or transfer disbursements found in this snapshot.</p>'}
      <div class="allocation-panel"><h3>Conditional company cash estimate</h3>
        <p role="status">${estimate?.status === 'estimated' ? 'Estimated from the collected cash shares.'
          : 'Awaiting reconciliation. No donor allocation is calculated.'}</p>
        <details><summary>Estimation method &amp; assumptions</summary>
          <p>At each payment, assign the same fraction as the company's share of the PAC's available cash. Carry that fraction through PAC transfers; leave retained cash and operating expenses in their own categories.</p>
          <p class="formula">Estimated company-funded spending = payment × company cash share before payment</p>
          <p class="muted">Example only: a 25% cash share × $10 million of candidate spending gives a $2.5 million estimate. This is an accounting assumption, not proof of donor intent or influence.</p></details></div>
      <details><summary>Company receipt evidence and excluded conversions</summary><div class="table-scroll"><table>
        <thead><tr><th>Reported name / role</th><th>Date</th><th class="num">Amount</th><th>Filing explanation</th></tr></thead><tbody>
        ${(legs.receipts || []).map(row => `<tr><td>${escapeHtml(row.reported_name)}<small>${escapeHtml(label(row.role))} · ${row.included_company_contribution ? 'Included contribution' : 'Excluded from company contribution total'}</small></td><td>${escapeHtml(row.date)}</td><td class="num">${currency(row.amount)}</td><td>${sourceAnchor(row.source_url, row.description || 'Original filing')}<small>Line ${escapeHtml(row.line_number)} · ${escapeHtml(row.sub_id)}</small></td></tr>`).join('')
          || '<tr><td colspan="4">No matching company receipts in this committee and cycle.</td></tr>'}
        </tbody></table></div></details>
      <h3 class="evidence-subheading">Candidate activity as filed</h3>
      <p class="muted">Amounts below belong to this committee. Support and opposition stay separate. Expand a name to compare the filing with the candidate register.</p>
      <div class="table-scroll"><table><thead><tr><th>Candidate / identity check</th><th>Direction</th><th class="num">Committee spending</th><th>Activity dates</th><th>Evidence</th></tr></thead><tbody>
        ${(legs.activity || []).slice().sort((a, b) => b.committee_spending - a.committee_spending).map(row =>
          `<tr><td><details><summary>${escapeHtml(row.candidate_name_as_filed || 'Candidate name missing')}</summary><p>As-filed ID: ${escapeHtml(row.candidate_id_as_filed)}<br>Register: ${escapeHtml(row.registered_candidate_name || 'Unresolved')}<br>${row.identity_status === 'name_matches_registration' ? 'Name matches the candidate register.' : 'Name / ID needs review. Aliases and filing errors can cause differences; no automatic reassignment.'}</p></details></td>
          <td>${escapeHtml(row.direction)}</td><td class="num">${currency(row.committee_spending)}</td>
          <td>${escapeHtml(row.first_date)}<small>to ${escapeHtml(row.last_date)}</small></td>
          <td>${sourceAnchor(row.source_urls?.[0], 'Filing')}<small>${number(row.source_rows)} records</small></td></tr>`).join('')
          || '<tr><td colspan="5">No candidate activity in this committee and cycle.</td></tr>'}
      </tbody></table></div>
      <details><summary>What is needed for a donor allocation?</summary><p>Reconcile all receipts and disbursements, opening and retained cash, asset conversions and refunds. Enforce donation → transfer → expenditure dates, including transfers between cycles. Document any earmark before calling a dollar amount traced. Otherwise, show assumptions and uncertainty with the estimate.</p></details></div>`;
  }

  function renderPanes() {
    const open = PANE_KEYS.filter(key => panes.has(key)).map(key => panes.get(key));
    const host = $('evidence-panes');
    // F3. The figure type and the card grid narrow with the number of panes; the
    // count rides on the host so the CSS can key off it without a container query.
    host.dataset.panes = String(open.length);
    host.style.gridTemplateColumns = `repeat(${Math.max(1, splitWithGraph() ? 1 : open.length)}, minmax(0, 1fr))`;
    render(host, open.map(paneHtml).join(''));
    applyBars(host);
    host.hidden = Boolean(mapPane);
    $('evidence-empty').hidden = open.length > 0 || Boolean(mapPane);
  }

  const splitWithGraph = () => document.querySelector('.workspace')?.classList.contains('split-workspace') || false;

  function renderChips() {
    const open = PANE_KEYS.filter(key => panes.has(key)).map(key => panes.get(key));
    render($('evidence-chips'), open.map(pane =>
      `<span class="chip" data-chip="${pane.key}" title="${escapeHtml(pane.name)}">`
      + `${escapeHtml(shortName(pane.name))} · ${escapeHtml(pane.industry || pane.sourceKind || 'file')}`
      + (pane.cycle ? ` · ${escapeHtml(pane.cycle)}` : '')
      + (pane.follows ? ' · follows Graph' : '')
      + `<button type="button" aria-label="Remove ${escapeHtml(shortName(pane.name))}">×</button></span>`).join('')
      || '<span class="muted">None yet</span>');
  }

  function compareRows(open) {
    const channels = [];
    for (const pane of open) for (const item of pane.totals || []) if (!channels.includes(item.channel)) channels.push(item.channel);
    const lead = channels.includes('Receipts') ? 'Receipts' : (channels[0] || 'Receipts');
    const others = channels.filter(channel => channel !== lead);
    const cycles = [...new Set(open.flatMap(pane => Object.keys(pane.totalsByCycle || {})))].sort();
    const channelAmount = (pane, channel) => {
      const item = (pane.totals || []).find(entry => entry.channel === channel);
      return item ? item.amount : 0;
    };
    const cycleAmount = (pane, cycle) => (pane.totalsByCycle[cycle] || []).reduce((total, item) => total + item.amount, 0);
    const rows = [[`${channelName(lead)} · ${cycleLabel(open[0].cycle)}`, pane => channelAmount(pane, lead), 'money']];
    for (const channel of others) rows.push([channelName(channel), pane => channelAmount(pane, channel), 'money']);
    for (const cycle of cycles) rows.push([cycleLabel(cycle), pane => cycleAmount(pane, cycle), 'money']);
    rows.push(['Rows supported', pane => pane.supported, 'count']);
    rows.push(['Rows excluded by the workbook', pane => pane.excluded, 'count']);
    rows.push(['Top contributor', pane => (pane.counterparties || [])[0]?.name || '—', 'text']);
    rows.push(['Category', pane => pane.category, 'text']);
    rows.push(['Source', pane => `${pane.industry || 'Imported file'} · ${pane.sourceKind}`, 'text']);
    return rows;
  }

  function renderCompare() {
    const open = PANE_KEYS.filter(key => panes.has(key)).map(key => panes.get(key));
    const host = $('evidence-compare');
    host.hidden = open.length < 2 || Boolean(mapPane);
    if (open.length < 2) { render(host, ''); return; }
    const heads = open.map(pane => `<th title="${escapeHtml(pane.name)}">${escapeHtml(shortName(pane.name))}`
      + `<br><span class="th-sub">${escapeHtml(pane.industry || 'Imported file')} · ${escapeHtml(pane.category)}</span></th>`).join('');
    const body = compareRows(open).map(([metric, read, kind]) => {
      const values = open.map(read);
      const peak = Math.max(1, ...values.map(value => typeof value === 'number' ? value : 0));
      const cells = values.map(value => {
        if (kind === 'text' || value == null) return `<td><span>${escapeHtml(value == null ? '—' : String(value))}</span></td>`;
        return `<td><div class="compare-cell">${bar(value, peak, true)}<span class="num">${kind === 'money' ? money(value) : number(value)}</span></div></td>`;
      }).join('');
      return `<tr><td class="compare-metric">${escapeHtml(metric)}</td>${cells}</tr>`;
    }).join('');
    render(host, `<div class="panel-heading"><h2>Compare</h2>
      <button type="button" class="secondary" id="evidence-compare-map">Top districts &middot; Map</button>
      <span class="muted">Bars are scaled per row to the largest pane. Figures are observed filings from each source; a bar across industries compares sources, not FEC totals.</span></div>
      <div class="table-scroll"><table><thead><tr><th class="compare-metric">Metric</th>${heads}</tr></thead><tbody>${body}</tbody></table></div>`);
    applyBars(host);
  }

  /* --------------------------------------------------------------- pane rows */
  async function loadPaneRows(pane) {
    if (pane.source === 'snapshot') { renderPanes(); return; }
    try {
      pane.rows = await api('/api/evidence-csv?' + new URLSearchParams({id: pane.id, committee: pane.committee,
        cycle: pane.cycle, offset: String(pane.offset), limit: String(PAGE_SIZE)}));
    } catch (error) {
      pane.rows = null; pane.message = error.message;
    }
    renderPanes();
  }

  /* ----------------------------------------------------------------- the URL */
  function writeScope() {
    const api = scope();
    if (!api || restored === false) return;
    const partial = {};
    for (const key of PANE_KEYS) {
      const pane = panes.get(key);
      partial[key + '.source'] = pane ? pane.source : '';
      partial[key + '.id'] = pane ? pane.id : '';
      partial[key + '.committee'] = pane ? pane.committee : '';
      partial[key + '.cycle'] = pane ? pane.cycle : '';
      // S8. `<pane>.map` is the open map's direction, and absent when the pane
      // grid is showing: a permalink reopens exactly the view it was cut from.
      partial[key + '.map'] = (pane && mapPane === key) ? mapStateFor(key).direction : '';
    }
    partial.category = $('evidence-type').value || '';
    api.write(partial);
  }

  async function restorePanes() {
    const api = scope();
    restored = true;
    if (!api) return;
    const current = api.read();
    if (current.category) {
      $('evidence-type').value = current.category;
      if ($('evidence-type').value !== current.category) $('evidence-type').value = '';
    }
    let opened = 0;
    for (const key of PANE_KEYS) {
      const source = current[key + '.source'], id = current[key + '.id'], committee = current[key + '.committee'];
      if (!source || !id || !committee) continue;
      if (source === 'snapshot' && !snapshotBodies.has(id)) {
        try { snapshotBodies.set(id, await api2Evidence(id)); } catch { continue; }
      }
      if (source === 'csv' && !importById(id)) continue;
      const pane = paneFrom(key, source, id, committee, current[key + '.cycle'] || '');
      panes.set(key, pane);
      opened += 1;
      await loadPane(pane);
    }
    const wantsMap = PANE_KEYS.find(key => panes.has(key) && current[key + '.map']);
    if (wantsMap) {
      mapStateFor(wantsMap).direction = current[wantsMap + '.map'];
    }
    if (opened) {
      const first = panes.get(PANE_KEYS.find(key => panes.has(key)));
      $('evidence-source').value = first.source + ':' + first.id;
      await chooseSource();
      $('evidence-cycle').value = first.cycle || '';
    }
    renderPanes(); renderChips(); renderCompare(); applyFilter();
    if (wantsMap) await openMap(wantsMap, current[wantsMap + '.map']);
  }

  const api2Evidence = id => api('/api/evidence?id=' + encodeURIComponent(id));

  /* ------------------------------------------------------------ Follow Graph */
  // Ported from app.js: Graph publishes its company and cycle on mentat:graph,
  // and pane A tracks it through the snapshot catalog when the box is checked.
  async function followGraph() {
    if (!$('evidence-follow-graph').checked || !graphContext) return;
    const companies = graphContext.filters?.company ? [graphContext.filters.company]
      : (graphContext.options?.companies || (graphContext.companies || []).map(row => row.id));
    const wanted = new Set((companies || []).map(MentatState.normalizeName));
    const cycle = graphContext.filters?.cycle || '';
    const match = snapshots.find(row => wanted.has(MentatState.normalizeName(row.company))
      && (!cycle || (row.cycles || []).some(value => String(value) === cycle)));
    if (!match) { say('No saved PAC evidence matches the loaded graph companies and cycle.'); return; }
    let body = snapshotBodies.get(match.id);
    if (!body) { body = await api2Evidence(match.id); snapshotBodies.set(match.id, body); }
    const finances = (body.committee_finances || []).filter(row => !cycle || String(row.cycle) === cycle);
    if (!finances.length) { say(`Snapshot ${match.id} covers no ${cycleLabel(cycle)} activity.`); return; }
    const pane = paneFrom('a', 'snapshot', match.id, finances[0].committee_id, cycle);
    pane.follows = true;
    panes.set('a', pane);
    await loadPane(pane);
    writeScope();
  }

  /* ------------------------------------------------------- import mechanics  */
  function hideSheetPicker() { $('evidence-sheet-label').hidden = true; }
  function showSheets(job) {
    const sheets = job.sheets || [];
    if (sheets.length > 1) {
      $('evidence-sheet').replaceChildren(...sheets.map(name => new Option(name, name)));
      $('evidence-sheet').value = sheets.includes(job.sheet) ? job.sheet : sheets[0];
      $('evidence-sheet-label').hidden = false;
    } else hideSheetPicker();
  }

  // app.js assigns the page's token when GET /api/session?light=1 answers, a
  // different round trip from the listing this module fetches on load, so a
  // reader who chose a file in that window got HTTP 403 'Refresh the app before
  // continuing.' and had to reload. `token` is a top-level `let` in app.js and
  // both files are classic scripts, so they share the binding.
  async function awaitToken(name) {
    if (token) return true;
    say(`${name}: Waiting for the console session…`);
    const deadline = Date.now() + 5000;
    while (!token && Date.now() < deadline) {
      try { const session = await api('/api/session?light=1'); if (!token && session && session.token) token = session.token; }
      catch { /* app.js is asking for the same thing; try again below */ }
      if (token) return true;
      await new Promise(resolve => setTimeout(resolve, 200));
    }
    if (token) return true;
    say(`${name}: The console session is not ready. Reload the page, then choose the file again.`);
    return false;
  }

  async function followJob(job, ticket, chosenName) {
    let current = job, failures = 0;
    while (ticket === importRevision) {
      const name = current.name || chosenName;
      if (current.state === 'failed') { showSheets(current); say(`${name}: ${current.message || 'The file could not be read.'}`); return; }
      if (current.state === 'ready') {
        showSheets(current);
        await refreshSources();
        if (ticket !== importRevision) return;
        $('evidence-source').value = 'csv:' + current.id;
        await chooseSource();
        return;
      }
      say(current.bytes_read
        ? `Reading ${name} · ${number(current.rows_read)} rows · ${megabytes(current.bytes_read)} of ${megabytes(current.bytes)} MB`
        : (!current.rows_read && (current.format === 'xlsx' || current.format === 'json'))
          ? `Reading ${name} · opening the ${current.format === 'xlsx' ? 'workbook' : 'file'}…`
          : `Reading ${name} · ${number(current.rows_read)} rows`);
      await new Promise(resolve => setTimeout(resolve, POLL_DELAY));
      if (ticket !== importRevision) return;
      try { current = await api('/api/evidence-csv?' + new URLSearchParams({job: job.id})); failures = 0; }
      catch (error) {
        // One failed poll is not a failed import: the read can lose a race with
        // the progress the reader itself is writing. Keep the last good state.
        failures += 1;
        say(`${name}: GET /api/evidence-csv?job=${job.id} failed: ${error.message}`
          + (failures < POLL_FAILURE_LIMIT ? ' Retrying.' : ''));
        if (failures >= POLL_FAILURE_LIMIT) return;
      }
    }
  }

  async function importFile(file, sheet) {
    const ticket = ++importRevision; hideSheetPicker();
    const suffix = suffixOf(file.name);
    if (limits && limits.accepted_suffixes && !limits.accepted_suffixes.includes(suffix)) {
      say(`${file.name}: This file type (${suffix}) is not supported. Choose CSV, TSV, TXT, XLSX, JSON or an FEC bulk ZIP.`);
      return;
    }
    if (limits && file.size > limits.max_bytes) { say(`${file.name} (${megabytes(file.size)} MB): ${limits.max_bytes_message}`); return; }
    pendingUploadFile = file; pendingPathRequest = null;
    if (!await awaitToken(file.name)) return;
    if (ticket !== importRevision) return;
    say(`Uploading ${file.name}…`);
    let response;
    try {
      const headers = {'Content-Type': suffix === '.csv' ? 'text/csv' : 'application/octet-stream',
        'X-Mentat-Token': token, 'X-Evidence-Name': encodeURIComponent(file.name)};
      if (sheet) headers['X-Evidence-Sheet'] = encodeURIComponent(sheet);
      response = await fetch('/api/evidence-csv', {method: 'POST', headers, body: file});
    } catch (error) { if (ticket === importRevision) say(`${file.name}: upload to /api/evidence-csv failed: ${error.message}`); return; }
    if (ticket !== importRevision) return;
    let body = null;
    try { body = await response.json(); } catch { body = null; }
    if (ticket !== importRevision) return;
    if (!body || typeof body !== 'object') { say(`${file.name}: /api/evidence-csv answered HTTP ${response.status} with no error message.`); return; }
    if (!response.ok) { say(`${file.name}: ${body.error || `/api/evidence-csv answered HTTP ${response.status} with no error message.`}`); return; }
    await followJob(body, ticket, file.name);
  }

  async function importPath(path, sheet, headerPath) {
    const ticket = ++importRevision; hideSheetPicker();
    pendingPathRequest = {path, header_path: headerPath || ''}; pendingUploadFile = null;
    $('evidence-path').value = path;
    if (!await awaitToken(path)) return;
    if (ticket !== importRevision) return;
    say(`Reading ${path}…`);
    let job;
    try { job = await api('/api/evidence-csv', {path, sheet: sheet || '', header_path: headerPath || ''}); }
    catch (error) { if (ticket === importRevision) say(`${path}: ${error.message}`); return; }
    if (ticket !== importRevision) return;
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
      const cells = `<td>${escapeHtml(entry.name)}</td><td>${escapeHtml(entry.kind)}</td><td class="num">${size}</td><td>${escapeHtml(String(entry.modified || '').slice(0, 10))}</td>`;
      if (entry.kind === 'dir') return `<tr data-browse-path="${escapeHtml(entry.path)}">${cells}</tr>`;
      if (entry.supported) return `<tr data-open-path="${escapeHtml(entry.path)}">${cells}</tr>`;
      return `<tr class="muted" title="Not a supported file type">${cells}</tr>`;
    }).join('');
    render($('evidence-browser'), `${header}<div class="evidence-toolbar">${up}${roots}${shortcuts}</div>`
      + `<div class="table-scroll"><table><thead><tr><th>Name</th><th>Kind</th><th>Size</th><th>Modified</th></tr></thead><tbody>${rows}</tbody></table></div>`
      + (body.truncated ? '<p class="muted">Showing the first 2,000 entries.</p>' : ''));
  }

  async function browse(path) {
    try { renderBrowser(await api('/api/evidence-files', {path: path || ''})); }
    catch (error) { say(error.message); }
  }

  /* -------------------------------------------------------- the collector    */
  function collectorState() {
    $('evidence-collect').disabled = collectorReadOnly || !collectorAvailable || !!evidenceJob;
    if (!collectorAvailable) {
      $('evidence-job-status').textContent =
        'Restart the MENTAT server to enable new snapshot collection. Saved evidence controls are ready to use.';
    }
  }

  async function pollEvidenceJob() {
    if (!evidenceJob) return;
    try {
      const job = await api('/api/evidence-job?id=' + encodeURIComponent(evidenceJob));
      $('evidence-job-status').textContent = job.state === 'collecting'
        ? `Collecting ${job.company} evidence… Saved responses are retained as collection progresses.`
        : job.message || label(job.state);
      if (job.state !== 'collecting') {
        clearTimeout(evidenceJobTimer);
        const id = evidenceJob; evidenceJob = '';
        try { localStorage.removeItem('mentat-evidence-job'); } catch {}
        collectorState();
        if (job.state === 'completed') {
          await refreshSources();
          if ([...$('evidence-source').options].some(option => option.value === 'snapshot:' + id)) {
            $('evidence-source').value = 'snapshot:' + id;
            await chooseSource();
          }
        }
        return;
      }
    } catch (error) { $('evidence-job-status').textContent = error.message + ' · retrying'; }
    evidenceJobTimer = setTimeout(pollEvidenceJob, 3000);
  }

  /* ------------------------------------------------------------ the map (S8) */
  /* One map per pane, opened from the pane header or from the Compare heading.

     Geography is static and served from /geo (built once by
     tools/build_district_geo.py); the money comes from GET /api/evidence-geo,
     which has already reconciled located + unlocated back to what the committee
     reported. This module draws what that route balanced and never re-adds it.

     Heat: candidate spending colours the DISTRICT; Senate races, transfers,
     operating payments and asset conversions colour the whole STATE, because
     that is as far as their basis reaches (S6_DESIGN). Support and oppose stay
     apart in the list and the tooltip; the map heats the amount. */
  const MAP_RAMP = ['#f1e9e3', '#d6c8e2', '#8b6984', '#57447b', '#342649'];
  const MAP_OUTLINE = '#bcaea1';
  let mapPane = '';                    // the pane key whose map is open, or ''
  const mapStates = new Map();         // pane key -> map view state
  const vintages = new Map();          // '118' -> the parsed boundary file
  let crosswalk = null, crosswalkVintage = '';

  function mapStateFor(key) {
    if (!mapStates.has(key)) {
      mapStates.set(key, {direction: 'spent', cycle: null, body: null, off: null,
                          district: '', message: '', loading: false});
    }
    return mapStates.get(key);
  }

  // A continuous ramp on a log scale, so $10,000 and $10,000,000 both read.
  // The five published stops sit at $1,000 .. $10,000,000+; the legend below
  // the map draws the same gradient and labels them from body.stops.
  const mixColour = (from, to, position) => {
    const parts = value => [1, 3, 5].map(at => parseInt(value.slice(at, at + 2), 16));
    const start = parts(from), end = parts(to);
    return '#' + start.map((value, index) => Math.round(value + (end[index] - value) * position)
      .toString(16).padStart(2, '0')).join('');
  };
  function heatColour(value) {
    if (!(value > 0)) return '';
    const span = MAP_RAMP.length - 1;
    const position = Math.min(1, Math.max(0, (Math.log10(value) - 2) / 5));
    const slot = Math.min(span - 1, Math.floor(position * span));
    return mixColour(MAP_RAMP[slot], MAP_RAMP[slot + 1], position * span - slot);
  }

  const isSenateKey = key => /-SEN$/.test(String(key || ''));
  const kindsOn = (body, off) => (body.kinds || []).filter(kind => !off.has(kind.kind));

  // Every visible row, folded onto the shape that carries it. A Senate row
  // keeps its CA-SEN key in the list and heats the state CA on the map.
  function heatFrom(body, off) {
    const districts = new Map(), states = new Map(), notes = new Map();
    const fold = (table, key, row, kind) => {
      table.set(key, (table.get(key) || 0) + (row.amount || 0));
      const lines = notes.get(key) || [];
      lines.push(`${kind.label} ${money(row.amount)} · ${number(row.rows)} rows · `
        + `${(row.share * 100).toFixed(1)}% of the kind`
        + (row.support ? ` · support ${money(row.support)}` : '')
        + (row.oppose ? ` · oppose ${money(row.oppose)}` : '')
        + (row.who ? ` · ${row.who}` : '') + ` · ${kind.basis}`);
      notes.set(key, lines);
    };
    for (const kind of kindsOn(body, off)) {
      for (const row of kind.districts || []) fold(isSenateKey(row.key) ? states : districts,
        isSenateKey(row.key) ? row.key.slice(0, 2) : row.key, row, kind);
      for (const row of kind.states || []) fold(states, row.key, row, kind);
    }
    return {districts, states, notes};
  }

  async function vintageFile(name) {
    if (!name) return null;
    if (vintages.has(name)) return vintages.get(name);
    // Static assets need no token (server.py do_GET gates only on the host).
    const response = await fetch('/geo/' + name);
    if (!response.ok) throw new Error(`The ${name} district boundaries could not be loaded.`);
    const body = await response.json();
    vintages.set(name, body);
    return body;
  }

  function mapSvgHtml(shapes, heat) {
    const state = [];
    const district = [];
    const outline = [];
    for (const [key, entry] of Object.entries(shapes.states || {})) {
      const value = heat.states.get(key) || 0;
      state.push(`<path class="map-shape" d="${escapeHtml(entry.path)}" data-key="${escapeHtml(key)}"`
        + ` data-fill="${escapeHtml(heatColour(value) || MAP_RAMP[0])}"></path>`);
      outline.push(`<path class="map-outline" d="${escapeHtml(entry.path)}" data-stroke="${MAP_OUTLINE}"></path>`);
    }
    for (const [key, entry] of Object.entries(shapes.districts || {})) {
      const value = heat.districts.get(key) || 0;
      district.push(`<path class="map-shape map-district" d="${escapeHtml(entry.path)}"`
        + ` data-key="${escapeHtml(key)}" data-district="${escapeHtml(key)}"`
        + ` data-fill="${escapeHtml(value > 0 ? heatColour(value) : 'none')}"></path>`);
    }
    return `<svg class="map-canvas" viewBox="0 0 ${shapes.width || 975} ${shapes.height || 610}"`
      + ` role="img" aria-label="Spending by congressional district" preserveAspectRatio="xMidYMid meet">`
      + `<g class="map-states">${state.join('')}</g>`
      + `<g class="map-districts">${district.join('')}</g>`
      + `<g class="map-outlines">${outline.join('')}</g></svg>`;
  }

  function mapListHtml(body, off) {
    const groups = (body.kinds || []).map(kind => {
      const rows = [...(kind.districts || []), ...(kind.states || [])]
        .sort((first, second) => second.amount - first.amount);
      const share = body.reported_total ? kind.total / body.reported_total * 100 : 0;
      const lines = rows.map(row => {
        const tone = row.oppose > 0 && !(row.support > 0) ? 'oppose' : (row.support > 0 ? 'support' : '');
        const label = isSenateKey(row.key) ? `${row.key.slice(0, 2)} · Senate` : row.key;
        return `<tr class="map-row" data-district="${escapeHtml(row.key)}">`
          + `<td><strong>${escapeHtml(label)}</strong>${row.split ? ' <span class="badge">split</span>' : ''}</td>`
          + `<td>${escapeHtml(row.who || '—')}</td>`
          + `<td class="${tone}">${escapeHtml(tone || kind.kind)}</td>`
          + `<td class="num">${money(row.amount)}</td>`
          + `<td class="num">${(row.share * 100).toFixed(1)}%</td></tr>`;
      }).join('');
      return `<tr class="group"><td colspan="3">${escapeHtml(kind.label)} · ${money(kind.total)} · `
        + `${escapeHtml(kind.basis)}${off.has(kind.kind) ? ' · off the heat' : ''}</td>`
        + `<td class="num">${money(kind.total)}</td><td class="num">${share.toFixed(1)}%</td></tr>${lines}`;
    }).join('');
    const unlocated = (body.unlocated || []).map(item =>
      `<tr class="map-unlocated"><td><strong>Unlocated</strong></td><td colspan="2">${escapeHtml(item.reason)}</td>`
      + `<td class="num">${money(item.amount)}</td><td class="num">${number(item.rows)} rows</td></tr>`).join('');
    return `<div class="table-scroll map-list"><table>
      <thead><tr><th>Where</th><th>To</th><th>Kind</th><th class="num">Amount</th><th class="num">Share</th></tr></thead>
      <tbody>${groups}${unlocated || ''}</tbody></table></div>`;
  }

  function mapHtml(pane, state) {
    const body = state.body;
    const cycles = pane.cycles || [];
    const off = state.off || new Set();
    const raised = state.direction === 'raised';
    const reconciliation = body
      ? `${money(body.located_total)} located + ${money(body.unlocated_total)} unlocated = `
        + `${money(body.reported_total)} ${raised ? 'reported receipts' : 'reported disbursements'}`
        + (body.reconciles ? '' : ' — these do not reconcile; the route says so above')
      : '';
    return `<div class="map-head">
      <div class="pane-title">
        <div class="pane-kind">${escapeHtml(pane.industry || 'Imported file')} · ${escapeHtml(pane.sourceKind)}</div>
        <h2 title="${escapeHtml(pane.name)}">${escapeHtml(shortName(pane.name))}
          <span class="muted">${escapeHtml(pane.committee)}</span></h2>
      </div>
      <div class="map-controls">
        <div class="seg" role="group" aria-label="Direction">
          <button type="button" class="map-direction${raised ? ' on' : ''}" data-direction="raised"
            aria-pressed="${raised}">Raised · where it came from</button>
          <button type="button" class="map-direction${raised ? '' : ' on'}" data-direction="spent"
            aria-pressed="${!raised}">Spent · where it went</button></div>
        <label class="map-cycle-label" for="evidence-map-cycle">Cycle
          <select id="evidence-map-cycle">${cycles.map(value =>
            `<option value="${escapeHtml(value)}"${value === (state.cycle ?? pane.cycle) ? ' selected' : ''}>${escapeHtml(cycleLabel(value))}</option>`).join('')}</select></label>
        <button type="button" class="secondary" id="evidence-map-back">Back to panes</button>
      </div></div>
    ${state.message ? `<p class="muted map-message">${escapeHtml(state.message)}</p>` : ''}
    ${body ? `<div class="map-layers">
      <span class="muted">${escapeHtml(raised ? 'All receipts' : 'All spend')}, ${escapeHtml(cycleLabel(body.cycle))}:
        <strong>${money(body.reported_total)}</strong> as reported · located ${money(body.located_total)} ·
        unlocated ${money(body.unlocated_total)}</span>
      ${(body.kinds || []).map((kind, index) => `<button type="button" class="layer${off.has(kind.kind) ? ' off' : ''}"
        data-layer="${escapeHtml(kind.kind)}" aria-pressed="${!off.has(kind.kind)}">
        <span class="dot" data-fill="${MAP_RAMP[Math.min(MAP_RAMP.length - 1, index + 1)]}"></span>
        ${escapeHtml(kind.label)} · ${money(kind.total)}${off.has(kind.kind) ? ' · off' : ''}</button>`).join('')}
    </div>
    <div class="map-grid">
      <section class="map-figure" aria-label="Spend heatmap">
        <div class="panel-heading"><h2>${escapeHtml(raised ? 'Receipts' : 'Spend')} heatmap ·
          by congressional district and state</h2>
          <span class="muted">Hover for amount, share and kind · click a district to filter this pane&rsquo;s rows</span></div>
        <div class="map-canvas-host" data-district-filter="${escapeHtml(state.district)}"></div>
        <div class="map-legend"><span class="muted">Heat</span><div class="map-ramp"></div>
          <span class="muted">${(body.stops || []).map(stop => money(stop)).join(' · ')}+</span>
          <span class="muted map-basis">${escapeHtml(body.congress ? body.congress + ' boundaries' : '')}${
            body.zip_basis ? ' · ZIP shares by ' + escapeHtml(body.zip_basis) : ''}</span></div>
      </section>
      <section class="map-ranked" aria-label="Ranked list">
        <div class="panel-heading"><h2>${escapeHtml(raised ? 'All receipts' : 'All spend')}, ranked</h2>
          <span class="muted">${number((body.kinds || []).reduce((total, kind) => total + (kind.rows || 0), 0))} placed rows</span></div>
        ${mapListHtml(body, off)}
        <p class="muted map-reconcile">${escapeHtml(reconciliation)}${
          raised ? ' · Contributor geography is by ZIP, approximate, and a ZIP that straddles districts is split by its land-area shares and marked “split”.' : ''}</p>
      </section>
    </div>` : '<p class="muted">Loading this map…</p>'}`;
  }

  function paintMap(host, shapes, heat) {
    for (const node of host.querySelectorAll('[data-fill]')) {
      // CSP style-src 'self': a style attribute written through innerHTML is
      // blocked, so every fill is set through the CSSOM, as graph.js does.
      node.style.fill = node.dataset.fill;
    }
    for (const node of host.querySelectorAll('[data-stroke]')) {
      node.style.fill = 'none';
      node.style.stroke = node.dataset.stroke;
    }
    for (const node of host.querySelectorAll('.map-shape')) {
      const lines = heat.notes.get(node.dataset.key);
      const title = document.createElementNS('http://www.w3.org/2000/svg', 'title');
      title.textContent = lines ? `${node.dataset.key}\n${lines.join('\n')}`
        : `${node.dataset.key}\nNo spending on this map`;
      node.appendChild(title);
    }
    void shapes;
  }

  async function renderMap() {
    const host = $('evidence-map');
    const pane = panes.get(mapPane);
    if (!pane) { host.hidden = true; return; }
    const state = mapStateFor(mapPane);
    host.hidden = false;
    render(host, mapHtml(pane, state));
    if (!state.body) return;
    const canvas = host.querySelector('.map-canvas-host');
    let shapes = null;
    try {
      shapes = await vintageFile(state.body.boundary_file);
    } catch (error) {
      render(canvas, `<p class="muted">${escapeHtml(error.message)}</p>`);
      return;
    }
    if (!shapes) {
      render(canvas, '<p class="muted">No district boundaries are built for this cycle.</p>');
      return;
    }
    const heat = heatFrom(state.body, state.off || new Set());
    render(canvas, mapSvgHtml(shapes, heat));
    paintMap(host, shapes, heat);
    for (const node of host.querySelectorAll('.layer .dot')) node.style.background = node.dataset.fill;
    if (state.district) {
      const chosen = canvas.querySelector(`[data-district="${CSS.escape(state.district)}"]`);
      if (chosen) chosen.classList.add('chosen');
    }
  }

  async function loadMap() {
    const pane = panes.get(mapPane);
    if (!pane) return;
    const state = mapStateFor(mapPane);
    state.loading = true;
    state.message = '';
    try {
      const cycle = state.cycle ?? pane.cycle ?? '';
      state.body = await api('/api/evidence-geo?' + new URLSearchParams({
        source: pane.source, id: pane.id, committee: pane.committee,
        cycle: cycle, direction: state.direction}));
      state.cycle = state.body.cycle || cycle;
      if (state.off === null) {
        state.off = new Set((state.body.kinds || []).filter(kind => !kind.default_on).map(kind => kind.kind));
      }
      if (state.body.reason) state.message = state.body.reason;
      if (!state.body.reconciles) {
        state.message = (state.message ? state.message + ' ' : '')
          + 'Located and unlocated do not add up to the reported total; the gap is listed below.';
      }
    } catch (error) {
      state.body = null;
      state.message = error.message;
    }
    state.loading = false;
    await renderMap();
  }

  async function openMap(key, direction) {
    if (!panes.has(key)) return;
    mapPane = key;
    const state = mapStateFor(key);
    if (direction) state.direction = direction;
    $('evidence-panes').hidden = true;
    $('evidence-compare').hidden = true;
    $('evidence-empty').hidden = true;
    $('evidence-map').hidden = false;
    await renderMap();
    writeScope();
    if (!state.body) await loadMap();
  }

  function closeMap() {
    mapPane = '';
    $('evidence-map').hidden = true;
    $('evidence-panes').hidden = false;
    renderPanes(); renderChips(); renderCompare();
    writeScope();
  }

  // The rows drawer's district filter. An imported file carries the
  // contributor's ZIP, so the crosswalk that built the map answers which rows
  // belong to the district that was clicked; nothing is guessed from a name.
  async function crosswalkFor(vintage) {
    if (!vintage) return null;
    if (crosswalk && crosswalkVintage === vintage) return crosswalk;
    const body = await vintageFile('zcta_cd' + vintage + '.json');
    crosswalk = body; crosswalkVintage = vintage;
    return body;
  }

  async function chooseDistrict(key) {
    const pane = panes.get(mapPane);
    const state = mapStateFor(mapPane);
    if (!pane || !state.body) return;
    state.district = state.district === key ? '' : key;
    pane.district = state.district;
    pane.districtBasis = '';
    if (state.district && pane.source === 'csv') {
      try {
        await crosswalkFor(state.body.vintage);
        pane.districtBasis = 'contributor ZIP';
      } catch (error) { pane.districtBasis = ''; state.message = error.message; }
    }
    pane.rowsOpen = Boolean(state.district);
    if (pane.rowsOpen && !pane.rows) await loadPaneRows(pane);
    await renderMap();
  }

  const districtOfZip = value => {
    const digits = String(value == null ? '' : value).replace(/\D/g, '').slice(0, 5);
    if (!crosswalk || digits.length < 5) return [];
    return (crosswalk[digits] || []).map(part => part[0]);
  };

  function rowsInDistrict(pane, rows) {
    if (!pane.district) return rows;
    if (pane.source !== 'csv' || !crosswalk) return rows;
    return rows.filter(row => {
      const raw = row.raw || {};
      const field = Object.keys(raw).find(name => /zip/i.test(name));
      return field ? districtOfZip(raw[field]).includes(pane.district) : false;
    });
  }

  /* ---------------------------------------------------------------- wiring   */
  function toggleDrawer(button, drawer) {
    const opening = $(drawer).hidden;
    $(drawer).hidden = !opening;
    $(button).setAttribute('aria-expanded', String(opening));
    if (opening && drawer === 'evidence-import-drawer') $('evidence-csv-file').focus({preventScroll: true});
  }

  function removePane(key) {
    panes.delete(key);
    renderPanes(); renderChips(); renderCompare(); updateAdd(); say(scopeStatus()); writeScope();
  }

  async function addPane() {
    const chosen = parseSourceValue(sourceValue());
    const key = freeKey();
    if (!chosen.kind || !key) return;
    const pane = paneFrom(key, chosen.kind, chosen.id, $('evidence-pac').value, $('evidence-cycle').value);
    panes.set(key, pane);
    updateAdd();
    await loadPane(pane);
    writeScope();
  }

  $('evidence-source').addEventListener('change', () => { chooseSource().then(writeScope); });
  $('evidence-type').addEventListener('change', () => { applyFilter(); writeScope(); });
  $('evidence-find').addEventListener('input', applyFilter);
  $('evidence-pac').addEventListener('change', updateAdd);
  $('evidence-cycle').addEventListener('change', updateAdd);
  $('evidence-add').addEventListener('click', addPane);
  $('evidence-import-open').addEventListener('click', () => toggleDrawer('evidence-import-open', 'evidence-import-drawer'));
  $('evidence-snapshot-open').addEventListener('click', () => toggleDrawer('evidence-snapshot-open', 'evidence-snapshot-drawer'));
  $('evidence-follow-graph').addEventListener('change', () => {
    if ($('evidence-follow-graph').checked) followGraph();
    else { const pane = panes.get('a'); if (pane) { pane.follows = false; renderChips(); renderPanes(); } }
  });
  $('evidence-chips').addEventListener('click', event => {
    const chip = event.target.closest('[data-chip]');
    if (chip && event.target.tagName === 'BUTTON') removePane(chip.dataset.chip);
  });
  $('evidence-panes').addEventListener('click', event => {
    const root = event.target.closest('[data-pane]');
    if (!root) return;
    const pane = panes.get(root.dataset.pane);
    if (!pane) return;
    if (event.target.closest('.pane-map')) { openMap(pane.key, mapStateFor(pane.key).direction); return; }
    if (event.target.closest('.pane-district-clear')) {
      pane.district = ''; mapStateFor(pane.key).district = ''; renderPanes(); return;
    }
    if (event.target.closest('.pane-remove')) { removePane(pane.key); return; }
    if (event.target.closest('.pane-rows')) {
      pane.rowsOpen = !pane.rowsOpen;
      if (pane.rowsOpen && !pane.rows) loadPaneRows(pane); else renderPanes();
      return;
    }
    if (event.target.closest('.pane-prev')) { pane.offset = Math.max(0, pane.offset - PAGE_SIZE); loadPaneRows(pane); return; }
    if (event.target.closest('.pane-next')) { pane.offset += PAGE_SIZE; loadPaneRows(pane); return; }
    const about = event.target.closest('.pane-about');
    if (about) {
      const body = root.querySelector('.pane-about-body');
      body.hidden = !body.hidden;
      about.setAttribute('aria-expanded', String(!body.hidden));
    }
  });
  $('evidence-map').addEventListener('click', event => {
    if (event.target.closest('#evidence-map-back')) { closeMap(); return; }
    const direction = event.target.closest('.map-direction');
    if (direction) {
      const state = mapStateFor(mapPane);
      if (state.direction !== direction.dataset.direction) {
        state.direction = direction.dataset.direction;
        state.body = null; state.off = null; state.district = '';
        renderMap().then(loadMap).then(writeScope);
      }
      return;
    }
    const layer = event.target.closest('.layer');
    if (layer) {
      const state = mapStateFor(mapPane);
      const kind = layer.dataset.layer;
      if (state.off.has(kind)) state.off.delete(kind); else state.off.add(kind);
      renderMap();
      return;
    }
    const shape = event.target.closest('[data-district]');
    if (shape) chooseDistrict(shape.dataset.district);
  });
  $('evidence-map').addEventListener('change', event => {
    if (event.target.id !== 'evidence-map-cycle') return;
    const state = mapStateFor(mapPane);
    state.cycle = event.target.value;
    state.body = null; state.off = null; state.district = '';
    loadMap();
  });
  // The compare strip is rendered from JS, so its Map button is reached by
  // delegation from the static host rather than by id at load time.
  $('evidence-compare').addEventListener('click', event => {
    if (!event.target.closest('#evidence-compare-map')) return;
    const first = PANE_KEYS.find(key => panes.has(key));
    if (first) openMap(first, mapStateFor(first).direction);
  });
  $('evidence-csv-file').addEventListener('change', () => {
    const file = $('evidence-csv-file').files[0];
    if (file) importFile(file, '');
  });
  $('evidence-sheet').addEventListener('change', () => {
    const sheet = $('evidence-sheet').value;
    if (pendingUploadFile) importFile(pendingUploadFile, sheet);
    else if (pendingPathRequest) importPath(pendingPathRequest.path, sheet, pendingPathRequest.header_path);
  });
  $('evidence-path-read').addEventListener('click', readPathBox);
  $('evidence-path').addEventListener('keydown', event => {
    if (event.key === 'Enter') { event.preventDefault(); readPathBox(); }
  });
  $('evidence-browse').addEventListener('click', () => {
    const opening = $('evidence-browser').hidden;
    $('evidence-browser').hidden = !opening;
    if (opening) browse(directoryOf($('evidence-path').value));
  });
  $('evidence-browser').addEventListener('click', event => {
    const open = event.target.closest('[data-open-path]');
    if (open) { importPath(open.dataset.openPath, '', $('evidence-header-path').value.trim()); return; }
    const step = event.target.closest('[data-browse-path]');
    if (step) browse(step.dataset.browsePath);
  });
  $('evidence-refresh').addEventListener('click', () => refreshSources().then(chooseSource));
  $('evidence-use-config').addEventListener('click', () => {
    const chosen = parseSourceValue(sourceValue());
    const body = chosen.kind === 'snapshot' ? snapshotBodies.get(chosen.id) : null;
    if (!body) { $('evidence-job-status').textContent = 'Choose a saved snapshot first.'; return; }
    $('evidence-company-input').value = body.company || '';
    $('evidence-cycles-input').value = [...new Set((body.committee_finances || []).map(row => row.cycle))].join(', ');
    $('evidence-committees-input').value = [...new Set((body.committee_finances || []).map(row => row.committee_id))].join(', ');
    $('evidence-aliases-input').value = (body.aliases || []).join('\n');
  });
  $('evidence-form').addEventListener('submit', async event => {
    event.preventDefault();
    if (evidenceJob) return;
    $('evidence-collect').disabled = true;
    try {
      const job = await api('/api/evidence-collect', {company: $('evidence-company-input').value,
        aliases: $('evidence-aliases-input').value.split(/\r?\n/).map(value => value.trim()).filter(Boolean),
        committees: $('evidence-committees-input').value, cycles: $('evidence-cycles-input').value});
      evidenceJob = job.id;
      try { localStorage.setItem('mentat-evidence-job', evidenceJob); } catch {}
      pollEvidenceJob();
    } catch (error) { $('evidence-job-status').textContent = error.message; collectorState(); }
  });
  window.addEventListener('mentat:graph', event => { graphContext = event.detail; followGraph(); });
  window.addEventListener('mentat:view', () => { renderPanes(); start(); });

  /* ------------------------------------------------------------------ start */
  async function start() {
    if (started) return;
    started = true;
    say('Finding imported files and saved snapshots…');
    await refreshSources();
    await restorePanes();
    if (!panes.size) { fillTypes(); fillCycles(); applyFilter(); }
    say(scopeStatus());
  }

  window.MentatEvidence = {
    setCollector(available, readOnly) { collectorAvailable = !!available; collectorReadOnly = !!readOnly; collectorState(); },
    panes: () => [...panes.values()].map(pane => ({key: pane.key, source: pane.source, id: pane.id,
      committee: pane.committee, cycle: pane.cycle})),
  };

  try { evidenceJob = localStorage.getItem('mentat-evidence-job') || ''; } catch {}
  if (evidenceJob) { $('evidence-collect').disabled = true; pollEvidenceJob(); }
  if (!$('view-evidence').hidden) start();
})();
