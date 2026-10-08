/* Cross-reference is a view of saved evidence. Opening it never starts a job.
 *
 * Dwarfed on the owner's ruling: the published report workbook is the
 * accounting of record, so this tab carries no totals. It lists evidence-backed
 * contradictions, clear refunds and unusually large counted receipts for
 * inspection. Magnitude alone never excludes a receipt. */
(function (root) {
  'use strict';
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const numeric = value => typeof value === 'number' && Number.isFinite(value);
  const money = value => numeric(value) ? value.toLocaleString('en-US', {style:'currency',currency:'USD',minimumFractionDigits:2,maximumFractionDigits:2}) : 'Unavailable';
  const number = value => numeric(value) ? value.toLocaleString('en-US') : 'Unavailable';
  const items = value => Array.isArray(value) ? value : [];
  const LEDE = 'The published report workbook is the accounting of record. This view lists evidence-backed contradictions, clear refunds and unusually large counted receipts for inspection. Size alone never excludes a receipt; this view publishes no totals.';
  // The engine keys this view still prints, in the plain words a lobbyist
  // reads. Anything unmapped falls back to the key with its underscores
  // removed, so a new receipt role is legible before it is named here.
  const roles = {
    other_receipt:'Other receipt',
    asset_liquidation:'Asset or liability liquidation',
  };
  const entities = {IND:'Individual',ORG:'Organization',PAC:'Committee',COM:'Committee',CCM:'Committee',PTY:'Party committee',CAN:'Candidate'};
  const named = (table, value) => {
    const key = String(value || '').trim();
    if (!key) return 'Not stated';
    return Object.hasOwn(table, key) ? table[key] : key.replaceAll('_',' ');
  };
  const roleText = value => escape(named(roles, value));
  const entityText = value => escape(named(entities, value));
  /* One FEC link rule for the whole console: MentatScope.fecLink - https, the
     host exactly www.fec.gov or docquery.fec.gov, no userinfo, the default
     port, the fragment stripped - and this view's own fourth rule, which it
     no longer carries alone: a query string must be an FEC image number.
     That rule guards a credential (see scope.js), so it was raised to the
     shared rule rather than dropped, and the other three callers get it
     too. With no scope.js loaded, nothing here is linked. */
  function recordLink(row) {
    const label = escape(row.record_id);
    const href = globalThis.MentatScope ? globalThis.MentatScope.fecLink(row.source_url) : '';
    if (!href) return label;
    return `<a href="${escape(href)}" target="_blank" rel="noopener noreferrer" referrerpolicy="no-referrer" title="Open the public FEC filing">${label || 'FEC filing'} ↗</a>`;
  }

  function table(rows, headings, cells, empty) {
    if (!rows.length) return `<p class="muted">${escape(empty)}</p>`;
    return '<div class="table-scroll"><table><thead><tr>' + headings.map(title => `<th>${title}</th>`).join('') + '</tr></thead><tbody>' + rows.map(row => '<tr>' + cells(row).map(value => `<td>${value}</td>`).join('') + '</tr>').join('') + '</tbody></table></div>';
  }

  const where = row => escape(row.company || 'Company not stated') + '<small>' + escape(row.cycle) + '</small>';
  // How many rows exist, and whether this page is showing all of them. A count
  // of listed rows is not a total of money and never becomes one.
  function listed(count, shown, singular, plural) {
    if (!numeric(count)) return `<p class="xref-caption">The number of ${escape(plural)} in this run is unavailable.</p>`;
    const noun = count === 1 ? singular : plural;
    const more = count > shown ? ` The ${number(shown)} largest are listed here; the saved digest holds the rest.` : '';
    return `<p class="xref-caption">${number(count)} ${escape(noun)} in this run.${more}</p>`;
  }

  function html(data) {
    if (!data || data.status === 'empty') return `<section class="panel xref-empty"><h2>Contradictions, large receipts and clear refunds</h2><p>${escape(LEDE)}</p><p class="muted">No run has been saved yet. Viewing this page does not start collection.</p></section>`;
    if (data.status === 'error' || !data.available) return `<section class="panel xref-warning" role="alert"><h2>Saved evidence unavailable</h2><p>${escape(data.message || 'The latest run could not be read.')}</p><p>No totals are shown until the saved run and its evidence agree.</p></section>`;
    const report = data.report, progress = data.progress;
    let content = `<div class="xref-run"><span class="badge">${data.status === 'completed' ? 'Cross-referencing complete' : data.status === 'failed' ? 'Run failed' : 'Cross-referencing'}</span><span>Run ${escape(data.run_id)}</span></div>`;
    const notices = [...items(data.notices)];
    if (data.status === 'failed') notices.push(progress?.message || 'The run did not complete successfully. Review its saved evidence before relying on anything below.');
    if (notices.length) content += `<div class="xref-warning" role="status">${notices.map(value => `<p>${escape(value)}</p>`).join('')}</div>`;
    if (!report) return content + `<section class="panel"><h2>Evidence is being cross-referenced</h2><p>${escape(progress?.message || 'Contradictions, refunds and unusually large counted receipts appear after the computation finishes.')}</p><p class="muted">Last progress update: ${escape(progress?.updated_at || 'Unknown')}. A saved status is not proof that a worker is still running.</p></section>`;
    const scope = report.scope || {};
    content += `<section class="panel xref-scope"><h2>What this run covers</h2><p>${escape(items(scope.industries).join(', ') || 'Industry scope unavailable')} · Cycles ${escape(items(scope.cycles).join(', ') || 'unavailable')}</p><p class="muted">${number(scope.company_count ?? items(scope.companies).length)} listed companies · Generated ${escape(report.generated_at || 'at an unknown time')}</p><details><summary>Companies in scope</summary><p>${escape(items(scope.companies).join(', ') || 'Company scope unavailable')}</p>${scope.company_count > items(scope.companies).length ? '<p class="muted">Company names are truncated in this display; the full scope is preserved in the saved report.</p>' : ''}</details><p class="xref-caption">${escape(LEDE)}</p></section>`;
    const digest = report.digest;
    if (!report.digest_available || !digest) {
      return content + `<section class="panel"><h2>Contradictions, large receipts and clear refunds</h2><p class="muted">${escape(report.digest_message || 'This run has no contradiction/refund/large-receipt digest.')}</p></section>`;
    }
    const refunds = digest.refunds || {}, outliers = digest.outliers || {};
    const linked = items(refunds.linked), unlinked = items(refunds.unlinked);
    content += '<section class="panel"><h2>Clear refunds</h2><p>Money the filer gave back, matched to the gift it reverses.</p>';
    content += table(linked, ['Company / cycle','Refund amount','Original amount','Refund record','Original record'],
      row => [where(row), money(row.refund_amount), money(row.original_amount),
              recordLink({record_id: row.refund_record_id, source_url: row.refund_source_url}),
              recordLink({record_id: row.original_record_id, source_url: row.original_source_url})],
      'No refund in this run is matched to the gift it reverses.');
    content += listed(refunds.linked_count, linked.length, 'linked refund', 'linked refunds');
    content += '<h3>Negative adjustments without a matched original</h3>';
    content += table(unlinked, ['Company / cycle','Amount','Description','Record'],
      row => [where(row), money(row.amount), escape(row.description || 'No receipt description saved'), recordLink(row)],
      'Every negative adjustment in this run is matched to an original gift.');
    content += listed(refunds.unlinked_count, unlinked.length, 'unmatched negative adjustment', 'unmatched negative adjustments');
    content += '<p class="xref-caption">A negative amount alone does not establish returned money. These rows still need their counterpart before anyone calls them refunds.</p></section>';
    const nonGiving = items(outliers.non_giving), large = items(outliers.large);
    content += '<section class="panel"><h2>Contradictions and large receipts</h2><h3>Evidence-backed contradictions to giving</h3><p>Receipts the accepted report had counted as giving that this run contradicted with explicit evidence: loans, interest, dividends, fees and transfers in.</p>';
    content += table(nonGiving, ['Company / cycle','Description','Role','Amount removed','Record'],
      row => [where(row), escape(row.description || 'No receipt description saved'), roleText(row.role), money(row.amount), recordLink(row)],
      'No receipt the accepted report counted was reclassified as non-giving.');
    content += listed(outliers.non_giving_count, nonGiving.length, 'reclassified receipt', 'reclassified receipts');
    content += '<h3>Unusually large receipts retained for inspection</h3><p>These receipts remain counted. Magnitude alone is not a contradiction and never excludes a receipt.</p>';
    content += table(large, ['Company / cycle','Entity','Amount','Record'],
      row => [where(row), entityText(row.entity), money(row.amount), recordLink(row)],
      'No counted receipt in this run reached the size stated below.');
    content += `<p class="xref-caption">${escape(digest.basis || 'The size that selects these rows is unavailable.')}</p>`;
    content += listed(outliers.large_count, large.length, 'large receipt', 'large receipts');
    content += '</section>';
    return content;
  }

  const api = {html, money};
  if (typeof module !== 'undefined' && module.exports) { module.exports = api; return; }
  root.MentatCrossReference = api;
  let active = false, fetching = false, lastHtml = '', lastIndustry = null;
  // The industry the URL names, through the one module that owns that
  // vocabulary (audits/mentat_failings_20260915/contracts/url_scope.json).
  const scopeIndustry = () => (globalThis.MentatScope ? globalThis.MentatScope.read().industry : '') || '';
  // Which run the console actually read, said where the refresh status is said.
  // S4's route answers selected_by: "pointer" on the latest path, "industry"
  // when a label chose the run, so the reader is never left guessing whether a
  // permalink's industry took.
  const runText = data => {
    if (!data) return 'Latest run';
    // An industry-scoped ask that found nothing answers the empty envelope
    // ({available:false, industry:<label>}), and saying "Latest run" over it
    // would name the one run it is NOT showing. Before S5 this view always had
    // the latest run to fall back on; a reader who followed a permalink is owed
    // the reason the panel is empty.
    if (data.industry && data.available === false) return 'No cross-reference run for ' + data.industry;
    if (data.selected_by === 'industry' && data.industry) return 'Newest run for ' + data.industry;
    return 'Latest run';
  };
  async function refresh() {
    if (!active || fetching || document.hidden) return;
    fetching = true;
    const message = document.getElementById('xref-refresh-status');
    const industry = scopeIndustry();
    lastIndustry = industry;
    try {
      // industry is the only query key this route accepts (server.py:1918-1928);
      // without one it still answers for the latest saved run, as before.
      const response = await fetch('/api/cross-reference' +
        (industry ? '?industry=' + encodeURIComponent(industry) : ''), {cache:'no-store'});
      if (!response.ok) throw new Error('The cross-reference view could not refresh.');
      const data = await response.json(), next = html(data);
      if (next !== lastHtml) { document.getElementById('xref-results').innerHTML = next; lastHtml = next; }
      message.textContent = runText(data) + ' · Saved evidence refreshed. This page is read-only.';
    } catch (error) {
      message.textContent = `${error.message} Any previously displayed result is an older snapshot.`;
    } finally { fetching = false; }
  }
  api.setActive = value => { active = !!value; if (active) refresh(); };
  api.refresh = refresh;
  // A scope written elsewhere in this document, or a Back button, can change the
  // industry. Only a change matters, and only while this view is the one on
  // screen; lastHtml is cleared so two runs that happen to render identically
  // still repaint under their own status line.
  globalThis.MentatScope?.subscribe(next => {
    if (!active) return;
    const industry = (next && next.industry) || '';
    if (industry === lastIndustry) return;
    lastHtml = '';
    refresh();
  });
  document.getElementById('xref-refresh')?.addEventListener('click', refresh);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) refresh(); });
  api.setActive(!document.getElementById('view-cross-reference')?.hidden);
  root.setInterval(refresh, 5000);
})(typeof window === 'undefined' ? globalThis : window);
