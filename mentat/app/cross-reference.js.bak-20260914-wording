/* Cross-reference is a view of saved evidence. Opening it never starts a job. */
(function (root) {
  'use strict';
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const numeric = value => typeof value === 'number' && Number.isFinite(value);
  const money = value => numeric(value) ? value.toLocaleString('en-US', {style:'currency',currency:'USD',minimumFractionDigits:2,maximumFractionDigits:2}) : 'Unavailable';
  const number = value => numeric(value) ? value.toLocaleString('en-US') : 'Unavailable';
  const percent = value => numeric(value) && value >= 0 && value <= 100 ? value.toLocaleString('en-US',{maximumFractionDigits:2}) + '%' : 'Unavailable';
  const items = value => Array.isArray(value) ? value : [];
  const steps = [
    ['define','Define','Set the companies, dates and kinds of giving.'],
    ['collect','Collect','Preserve FEC evidence and check coverage.'],
    ['identify','Identify','Establish the source, recipient and transaction.'],
    ['connect','Connect','Link records that describe the same money.'],
    ['count','Count','Count original giving once; keep PAC activity separate.'],
    ['verify','Verify & report','Reconcile decisions and expose remaining uncertainty.'],
  ];
  const statuses = {pending:'Pending',running:'In progress',completed:'Processed',review:'Needs evidence',failed:'Failed'};
  // Engine keys, in the plain words a lobbyist reads. Anything unmapped still
  // falls back to the key with its underscores removed, so a new engine
  // reason is legible before it is named here.
  const reasons = {
    filing_relationship_evidence_missing:'Filing and amendment relationship needs evidence',
    latest_filing_completeness_unproven:'Complete latest filing has not been established',
    company_pac_affiliation_unresolved:'Company connection to the PAC needs dated evidence',
    signed_adjustment_not_linked_refund:'Negative adjustment has no linked refund',
    receipt_role_unresolved:'Transaction meaning needs evidence',
    treasury_ownership_unresolved:'Corporate ownership needs dated evidence',
    reciprocal_earmark_not_established:'Intermediary route lacks a matching disclosure',
    source_or_attribution_conflict:'Source facts or company matches disagree',
    funding_identity_unresolved:'Who supplied the money is unresolved',
    memo_parent_ambiguous:'Memo points to more than one possible receipt',
    company_attribution_unresolved:'Donor not yet matched to a listed company (counted at $0)',
    attribution_unresolved:'Attribution not settled (counted at $0)',
    company_attribution_not_accepted:'Company match not accepted',
    memo_parent_not_established:'Memo entry without a proven parent receipt',
    original_source_of_transfer_unresolved:'Transfer whose original donor is unresolved',
    earmark_counterpart_not_unique:'Earmark with more than one possible counterpart',
    earmark_destination_ambiguous:'Earmark destination ambiguous',
    overlapping_or_cyclic_earmark_links:'Earmark links overlap or loop',
    observed_filing_versions_unresolved:'Amended filings not reconciled',
    latest_filing_transaction_replacement_missing:'Latest filing lacks the replacing transaction',
    latest_filing_manifest_not_corroborated:'Latest filing not corroborated by its manifest',
    linked_refunds_exceed_original_gift:'Refunds exceed the original gift',
    receipt_date_missing:'Receipt date missing',
    excluded_source_metadata_conflict:'Source metadata conflict',
    superseded_in_observed_filing_family:'Superseded by a later filing',
    same_original_gift_at_conduit_and_destination:'Same gift seen at conduit and destination',
    explicit_same_filing_memo_reference:'Memo references its own filing',
    explicit_observed_refund:'Observed refund',
    linked_refund:'Linked refund adjustment',
  };
  const reason = value => escape(String(value || '').split(';').map(part => Object.hasOwn(reasons, part.trim()) ? reasons[part.trim()] : part.trim().replaceAll('_',' ')).join('; '));
  function recordLink(row) {
    const label = escape(row.record_id);
    try {
      const url = new URL(row.source_url);
      if (url.protocol !== 'https:' || !['docquery.fec.gov','www.fec.gov'].includes(url.hostname) || url.username || url.password ||
          (url.port && url.port !== '443') || (url.search && !/^\?\d{5,30}$/.test(url.search))) return label;
      url.hash = '';
      return `<a href="${escape(url.href)}" target="_blank" rel="noopener noreferrer" referrerpolicy="no-referrer" title="Open the public FEC filing">${label || 'FEC filing'} ↗</a>`;
    } catch { return label; }
  }

  function stepHtml(values) {
    return '<ol class="xref-steps">' + steps.map(([id, title, purpose], index) => {
      const row = items(values).find(value => value.id === id) || {};
      const state = Object.hasOwn(statuses, row.status) ? row.status : 'pending';
      return `<li class="xref-step xref-step-${state}"><span class="xref-step-number">${index + 1}</span><div><h3>${title}</h3><p>${purpose}</p><strong class="xref-step-state">${statuses[state]}</strong>${row.detail ? `<p class="xref-step-detail">${escape(row.detail)}</p>` : ''}</div></li>`;
    }).join('') + '</ol>';
  }

  // Which election cycles a figure describes. A dollar total with no period
  // beside it invites the reader to compare it with one from another run.
  let scopeCycles = '';
  function metric(title, value, detail, money) {
    const cycles = money && scopeCycles ? `<small class="xref-metric-cycles">Cycles ${escape(scopeCycles)}</small>` : '';
    return `<div class="xref-metric"><span>${title}</span><strong>${value}</strong>${cycles}<small>${detail}</small></div>`;
  }

  function table(rows, headings, cells, empty) {
    if (!rows.length) return `<p class="muted">${escape(empty)}</p>`;
    return '<div class="table-scroll"><table><thead><tr>' + headings.map(title => `<th>${title}</th>`).join('') + '</tr></thead><tbody>' + rows.map(row => '<tr>' + cells(row).map(value => `<td>${value}</td>`).join('') + '</tr>').join('') + '</tbody></table></div>';
  }

  function html(data) {
    scopeCycles = '';
    if (!data || data.status === 'empty') return '<section class="panel xref-empty"><h2>From evidence to one coherent account</h2><p>Cross-referencing runs automatically as collected data is prepared for a report. Its decisions, dollar changes and remaining questions will appear here.</p>' + stepHtml([]) + '<p class="muted">No run has been saved yet. Viewing this page does not start collection.</p></section>';
    if (data.status === 'error' || !data.available) return `<section class="panel xref-warning" role="alert"><h2>Saved evidence unavailable</h2><p>${escape(data.message || 'The latest run could not be read.')}</p><p>No totals are shown until the saved run and its evidence agree.</p></section>`;
    const report = data.report, progress = data.progress;
    let content = `<div class="xref-run"><span class="badge">${data.status === 'completed' ? 'Computation complete' : data.status === 'failed' ? 'Run failed' : 'Cross-referencing'}</span><span>Run ${escape(data.run_id)}</span></div>`;
    const notices = [...items(data.notices)];
    if (data.status === 'failed') notices.push(progress?.message || 'The run did not complete successfully. Review its saved evidence before relying on any totals.');
    if (notices.length) content += `<div class="xref-warning" role="status">${notices.map(value => `<p>${escape(value)}</p>`).join('')}</div>`;
    content += stepHtml(report?.steps || progress?.steps);
    if (!report) return content + `<section class="panel"><h2>Evidence is being reconciled</h2><p>${escape(progress?.message || 'Totals appear after the computation finishes. Unresolved evidence will remain visible.')}</p><p class="muted">Last progress update: ${escape(progress?.updated_at || 'Unknown')}. A saved status is not proof that a worker is still running.</p></section>`;
    const s = report.summary || {}, scope = report.scope || {};
    scopeCycles = items(scope.cycles).join(', ');
    content += `<section class="panel xref-scope"><h2>What this run covers</h2><p>${escape(items(scope.industries).join(', ') || 'Industry scope unavailable')} · Cycles ${escape(items(scope.cycles).join(', ') || 'unavailable')}</p><p class="muted">${number(scope.company_count ?? items(scope.companies).length)} listed companies · ${number(scope.source_count)} source snapshots · Generated ${escape(report.generated_at || 'at an unknown time')}</p><details><summary>Companies in scope</summary><p>${escape(items(scope.companies).join(', ') || 'Company scope unavailable')}</p>${scope.company_count > items(scope.companies).length ? '<p class="muted">Company names are truncated in this display; the full scope is preserved in the saved report.</p>' : ''}</details><p class="xref-caption">Generation time describes this computation. It does not establish the FEC data-through date or completeness of company coverage.</p></section>`;
    content += '<div class="xref-metrics">' + metric('Records examined', number(s.input_records), 'Rows available in the selected sources.') + metric('Automatically resolved', number(s.automatic_decisions), 'Decisions supported by the available evidence; not an accuracy percentage.') + metric('Records needing review', number(s.unresolved_records), 'Missing or conflicting transaction evidence needs a check.') + '</div>';
    if (numeric(s.source_verified_records) || numeric(s.classified_from_stored_records)) {
      content += '<div class="xref-metrics">';
      if (numeric(s.source_verified_records)) content += metric('Source-verified receipts', number(s.source_verified_records), 'Receipt facts checked against preserved source evidence.');
      if (numeric(s.classified_from_stored_records)) content += metric('Classified from stored evidence', number(s.classified_from_stored_records), 'Transaction decisions supported by the stored records.');
      content += '</div>';
    }
    content += `<section class="panel"><div class="panel-heading"><h2>Keep each stage of money separate</h2><span class="badge">${s.verified_unique ? 'Scoped uniqueness established' : 'Provisional totals'}</span></div><div class="xref-money-grid">`;
    content += metric('Observed original giving', money(s.observed_original_giving), s.verified_unique ? 'Counted under the scope and evidence rules of this run.' : 'Signed amounts after cross-referencing. Includes unresolved giving; not yet verified unique dollars.', true);
    content += metric('Observed PAC outgoing activity', money(s.pac_outgoing), 'Recipient-reported activity in these records; incomplete. Do not add it to original giving.', true);
    content += '</div><dl class="xref-breakdown"><div><dt>Employee giving · reported employer</dt><dd>' + money(s.employee_giving) + '</dd></div><div><dt>Corporate treasury giving · supported ownership</dt><dd>' + money(s.corporate_giving) + '</dd></div><div><dt>Funding attribution unverified</dt><dd>' + money(s.unverified_funding) + '</dd></div>';
    if (numeric(s.linked_refund_adjustments)) content += '<div><dt>Linked refund adjustments</dt><dd>' + money(s.linked_refund_adjustments) + '</dd></div>';
    content += '</dl><p class="xref-caption">These amounts follow the classifications supported in this run. Unverified funding attribution remains in the original-giving view.</p>';
    content += '<p class="xref-caption">Rows with an unresolved company attribution are counted at $0 in every total above; memo, transfer, earmark and role reviews stay inside Observed original giving until resolved.</p>';
    if (numeric(s.supported_original_giving)) content += `<p class="xref-caption">Gross giving with complete uniqueness evidence: ${money(s.supported_original_giving)}. This separate measure requires complete filing, origin and route evidence; it does not invalidate resolved receipt classifications.</p>`;
    content += '</section>';
    if (items(report.partisan_breakdowns).length) {
      content += '<section class="panel"><h2>Partisan composition</h2><p>D/R shares use only Democratic and Republican receipt dollars in the same view. Classification coverage uses absolute receipt dollars, so signed adjustments do not cancel the evidence gap. These percentages do not measure accuracy.</p>';
      content += table(items(report.partisan_breakdowns), ['Money view','Democratic receipts','Republican receipts','Other / unknown receipts','D/R denominator','Democratic share of D/R','Republican share of D/R','D/R classification coverage'], row => [escape(String(row.view || '').replaceAll('_',' ')),money(row.democratic),money(row.republican),money(row.other_unknown),money(row.denominator_dr),percent(row.democratic_percent),percent(row.republican_percent),percent(row.classified_gross_percent)], 'Partisan evidence unavailable.');
      content += '<details><summary>Denominators and evidence basis</summary>' + items(report.partisan_breakdowns).map(row => `<p><strong>${escape(String(row.view || '').replaceAll('_',' '))}:</strong> ${escape(row.basis || 'Evidence basis unavailable.')}</p>`).join('') + '<p class="xref-caption">A missing or invalid share is unavailable, not zero. Original giving and recipient-reported PAC activity remain separate.</p></details></section>';
    }
    content += `<section class="panel"><h2>What changed, and why</h2><div class="xref-money-grid">${metric('Previous receipt total', money(s.baseline_amount), 'Selected baseline. Changes may also separate different money stages.', true)}${metric('Change from previous total', money(s.amount_change), 'Every change is preserved with its evidence in the local ledger.', true)}</div>`;
    content += table(items(report.changes).slice(0,20), ['Company / cycle','Reason / record','Before','After','Change'], row => [escape(row.company) + '<small>' + escape(row.cycle) + '</small>',reason(row.reason) + (row.source_description ? '<small>' + escape(String(row.source_description).slice(0,500)) + '</small>' : '') + '<small>' + recordLink(row) + '</small>',money(row.before),money(row.after),money(row.delta)], 'No changed records are listed in this summary.');
    content += '<p class="xref-caption">Up to 20 decisions are shown here. The saved local ledger retains the complete record-level history.</p></section>';
    content += `<section class="panel"><h2>Records needing review</h2><p>${money(s.unresolved_amount)} is associated with unresolved records. This is an evidence gap, not an estimated error amount.</p>`;
    content += table(items(report.unresolved_reasons).slice(0,50), ['Reason','Records','Associated amount'], row => [reason(row.reason),number(row.records),money(row.amount)], 'No unresolved reason groups are listed. This alone does not establish complete collection coverage.');
    content += '<h3>Review priority</h3><p class="muted">Supported decisions are resolved automatically. This queue contains transaction questions that still need evidence.</p>' + table(items(report.review_queue).slice(0,20), ['Company / cycle','Reason / next check','Associated amount','Record'], row => [escape(row.company) + '<small>' + escape(row.cycle) + '</small>',reason(row.reason) + (row.action ? '<small>' + escape(row.action) + '</small>' : ''),money(row.amount),recordLink(row)], 'No records are queued in this summary.');
    content += '<p class="xref-caption">Up to 20 priority records. Reasons can overlap; do not add category amounts unless the ledger establishes separate records.</p></section>';
    if (numeric(s.coverage_records) || items(report.coverage_reasons).length) {
      content += '<section class="panel"><h2>Collection coverage follow-up</h2><p>Receipt decisions and collection coverage are checked separately. These shared source checks do not require a manual review of every affected receipt.</p>';
      if (numeric(s.coverage_records)) content += `<p>${number(s.coverage_records)} records are affected by collection coverage checks${numeric(s.coverage_amount) ? ` (${money(s.coverage_amount)} associated amount)` : ''}.</p>`;
      if (numeric(s.coverage_only_records)) content += `<p>${number(s.coverage_only_records)} of those records have no remaining transaction question.</p>`;
      content += table(items(report.coverage_reasons).slice(0,50), ['Coverage check','Affected records','Associated amount','Next check'], row => [reason(row.reason),number(row.records),money(row.amount),escape(row.action || '')], 'No collection coverage follow-up is listed for this run.');
      content += '<p class="xref-caption">Source verification confirms the receipt facts checked. Complete filing collection and unique-dollar totals are separate conclusions. Coverage reasons may overlap.</p></section>';
    }
    if (items(report.limitations).length) content += `<section class="panel"><h2>Limits of this result</h2><ul>${items(report.limitations).map(value => `<li>${escape(value)}</li>`).join('')}</ul></section>`;
    return content;
  }

  const api = {html, stepHtml, money};
  if (typeof module !== 'undefined' && module.exports) { module.exports = api; return; }
  root.MentatCrossReference = api;
  let active = false, fetching = false, lastHtml = '';
  async function refresh() {
    if (!active || fetching || document.hidden) return;
    fetching = true;
    const message = document.getElementById('xref-refresh-status');
    try {
      const response = await fetch('/api/cross-reference', {cache:'no-store'});
      if (!response.ok) throw new Error('The cross-reference view could not refresh.');
      const data = await response.json(), next = html(data);
      if (next !== lastHtml) { document.getElementById('xref-results').innerHTML = next; lastHtml = next; }
      message.textContent = 'Saved evidence refreshed. This page is read-only.';
    } catch (error) {
      message.textContent = `${error.message} Any previously displayed result is an older snapshot.`;
    } finally { fetching = false; }
  }
  api.setActive = value => { active = !!value; if (active) refresh(); };
  api.refresh = refresh;
  document.getElementById('xref-refresh')?.addEventListener('click', refresh);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) refresh(); });
  api.setActive(!document.getElementById('view-cross-reference')?.hidden);
  root.setInterval(refresh, 5000);
})(typeof window === 'undefined' ? globalThis : window);
