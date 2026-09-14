/* Shared, offline-testable presentation for saved collection coverage. */
(function (root) {
  'use strict';
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function select(rows, sectors, cycles) {
    const names = sectors.map(s => s.trim().toLocaleLowerCase()).filter(Boolean);
    const selected = rows.filter(r => (!names.length || names.includes(r.industry.toLocaleLowerCase())) && cycles.includes(r.cycle));
    for (const sector of sectors.filter(s => s.trim())) for (const cycle of cycles) {
      if (!selected.some(r => r.industry.toLocaleLowerCase() === sector.trim().toLocaleLowerCase() && r.cycle === cycle)) {
        selected.push({industry:sector,cycle,freshness:'unverifiable',reason:'No saved collection evidence for this sector/cycle.'});
      }
    }
    return selected;
  }
  function html(rows) {
    if (!rows.length) return '<p class="coverage-unverifiable">Unverifiable · No saved FEC coverage evidence available.</p>';
    return '<div class="table-scroll"><table><thead><tr><th>Sector / cycle</th><th>Verified FEC data-through</th><th>Coverage status</th><th>Latest observed transaction</th><th>Evidence</th></tr></thead><tbody>' + rows.map(row => {
      const verified = !!row.verified_data_through && ['current','stale'].includes(row.freshness);
      const state = verified ? row.freshness : 'unverifiable';
      const status = state === 'current' ? 'Current within policy' : state === 'stale' ? 'Stale coverage' : 'Unverifiable coverage';
      const lag = verified ? `<small>${escape(row.lag_days)} days behind ${escape(row.target_date)}</small>` : '';
      const evidence = (row.evidence || []).map(e => `<li>${escape(e.company)} · ${escape(e.kind)} · ${escape(e.verified_data_through)}<small>${escape((e.verification_evidence || []).join('; '))}</small></li>`).join('');
      return `<tr><td>${escape(row.industry)}<small>${row.cycle - 1}–${escape(row.cycle)}</small></td><td>${escape(verified ? row.verified_data_through : 'Unknown')}</td><td class="coverage-${state}"><strong>${status}</strong>${lag}</td><td>${escape(row.latest_observed_transaction_date || 'Unknown')}<small>Observed only; does not establish coverage.</small></td><td>${escape(row.reason)}<small>${escape(row.run_name || '')}${row.company_count != null ? ' · ' + escape(row.company_count) + ' companies' : ''}</small><details><summary>Coverage evidence</summary><p>${escape(row.scope || 'FEC employer and corporate searches')}<br>${escape(row.receipt || 'No receipt')}</p><p>Database file modified: ${escape(row.database_modified_at || 'Unknown')} · file event only.</p>${evidence ? '<ul>' + evidence + '</ul>' : '<p>No dated evidence for the full scope.</p>'}</details></td></tr>`;
    }).join('') + '</tbody></table></div>';
  }
  const api = {select, html};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.MentatCoverage = api;
})(typeof window === 'undefined' ? globalThis : window);
