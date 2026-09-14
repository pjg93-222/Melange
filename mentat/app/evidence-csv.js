/* CSV evidence uses selected source rows only; imported files live in this server session. */
(() => {
  let source = null, revision = 0, offset = 0;
  const pageSize = 100;
  const channelName = value => String(value || 'Unclassified').replaceAll('_',' ');
  function sourceMode() {
    const saved = $('evidence-source').value === 'snapshot';
    $('evidence-saved').hidden = !saved; $('evidence-csv-workspace').hidden = saved;
    try { localStorage.setItem('mentat-evidence-source', saved ? 'snapshot' : 'csv'); } catch {}
  }
  try { if (localStorage.getItem('mentat-evidence-source') === 'snapshot') $('evidence-source').value = 'snapshot'; } catch {}
  $('evidence-source').addEventListener('change', sourceMode); sourceMode();
  function resetSelection() {
    source = null; offset = 0; $('evidence-csv-results').hidden = true;
    $('evidence-csv-committee').replaceChildren(new Option('Choose a CSV first',''));
    $('evidence-csv-cycle').replaceChildren(new Option('All cycles',''));
    $('evidence-csv-committee').disabled = true; $('evidence-csv-cycle').disabled = true;
  }
  function renderRows(body) {
    const rows = body.rows || [], pages = body.pagination || body;
    const total = pages.total_rows ?? body.total_rows ?? rows.length;
    const supported = body.supported_rows ?? rows.filter(row=>row.status==='supported').length;
    $('evidence-csv-title').textContent = body.committee?.name || body.committee?.id || 'Reported activity';
    $('evidence-csv-scope').textContent = `${body.source?.name || source.name} · ${body.committee?.id || $('evidence-csv-committee').value} · ${body.selected_cycle || 'All cycles'} · ${number(total)} selected rows`;
    setHtml('evidence-csv-totals', (body.totals || []).map(item => `<div><span>${escapeHtml(channelName(item.channel))}</span><strong>${currency(item.amount)}</strong><small>${number(item.row_count)} supported CSV rows</small></div>`).join('') || '<p>No supported amount totals for these rows. Review the original fields below.</p>');
    $('evidence-csv-provenance').textContent = `${body.source?.name || source.name} · Imported UTF-8 text SHA-256 ${body.source?.sha256 || source.sha256} · ${number(body.source?.row_count || source.row_count)} file rows. Imported into this local server session. Values are observed filings or labeled cycle aggregates, not donor allocations or reconciled giving totals.`;
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
    $('evidence-csv-status').textContent = 'Reading selected PAC rows…';
    $('evidence-csv-results').hidden = true;
    $('evidence-csv-prev').disabled = true; $('evidence-csv-next').disabled = true;
    try {
      const body = await api('/api/evidence-csv?' + new URLSearchParams({id:source.id,committee,cycle,offset:String(offset),limit:String(pageSize)}));
      if (ticket!==revision) return;
      const cycles = (body.cycles || []).map(String);
      $('evidence-csv-cycle').replaceChildren(new Option('All cycles',''),...cycles.map(value=>new Option(value,value)));
      if(cycles.includes(cycle)) $('evidence-csv-cycle').value = cycle;
      $('evidence-csv-cycle').disabled = !cycles.length;
      renderRows(body); $('evidence-csv-status').textContent = `${source.name} · ${number(source.row_count)} rows in file`;
    } catch (error) { if(ticket===revision) $('evidence-csv-status').textContent = error.message; }
  }
  $('evidence-csv-file').addEventListener('change', async () => {
    const file = $('evidence-csv-file').files[0]; if (!file) return;
    const ticket = ++revision; resetSelection();
    if (file.size > 5_000_000) { $('evidence-csv-status').textContent = 'Choose a CSV no larger than 5 MB.'; return; }
    $('evidence-csv-status').textContent = `Reading ${file.name}…`;
    try {
      const text = await file.text(); if(ticket!==revision)return;
      const body = await api('/api/evidence-csv', {name:file.name,text}); if(ticket!==revision)return;
      source = body.source || body;
      const committees = body.committees || [];
      $('evidence-csv-committee').replaceChildren(...committees.map(item=>new Option(`${item.name || item.id} · ${item.id}`,item.id)));
      $('evidence-csv-committee').disabled = !committees.length;
      await loadRows();
    } catch(error) { if(ticket===revision) $('evidence-csv-status').textContent = error.message; }
  });
  for (const id of ['evidence-csv-committee','evidence-csv-cycle']) $(id).addEventListener('change',()=>{offset=0;loadRows();});
  $('evidence-csv-prev').addEventListener('click',()=>{offset=Math.max(0,offset-pageSize);loadRows();});
  $('evidence-csv-next').addEventListener('click',()=>{offset+=pageSize;loadRows();});
})();
