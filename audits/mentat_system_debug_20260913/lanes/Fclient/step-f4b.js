/* F4 continued. step-f4.js wrote chart-studio-contributions.js (reconcile) and
   then stopped on a stale index.html anchor: the Graph total carries a literal
   em dash, not the &#8212; entity I had written. This step carries the rest with
   that anchor corrected. Do NOT replay step-f4.js: its contributions edits are
   already on disk and would be inserted twice. */
'use strict';
module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat\\app',
  bak: '.bak-20260914-Fc',
  eol: 'crlf',
  files: [
    {
      path: 'index.html',
      eol: 'crlf',
      edits: [
        {
          find: '<span id="studio-scope-chip" class="studio-scope-chip" role="status"></span>\n',
          replace: '<span class="studio-scope-block"><span id="studio-scope-chip" class="studio-scope-chip" role="status"></span><small id="studio-scope-note" class="studio-scope-note" hidden></small></span>\n'
        },
        {
          find: '<h2 id="studio-title">Chart Studio</h2>\n',
          replace: '<h2 id="studio-title">Chart Studio</h2>\n<p id="studio-reconcile" class="studio-reconcile" role="status" hidden></p>\n'
        },
        {
          find: '<strong id="graph-total">\u2014</strong></div>',
          replace: '<strong id="graph-total">\u2014</strong><small id="graph-basis-note"></small></div>'
        },
        {
          find: '<label for="studio-param-groups">Group limit<input id="studio-param-groups" type="number" min="1" max="1000" step="1" placeholder="40" title="Groups beyond this limit are combined into an Other mark (default 40)"></label>',
          replace: '<label for="studio-param-groups">Group limit<input id="studio-param-groups" type="number" min="1" max="1000" step="1" placeholder="40" title="40 per page (verified) &#183; fold after 40 (worksheet); Graph and classic fold at 60"></label>'
        }
      ]
    },
    {
      path: 'chart-studio.js',
      eol: 'crlf',
      edits: [
        {
          find: "    if(!data||!dataset()){el('canvas').replaceChildren();el('table').replaceChildren();",
          replace: "    if(!data||!dataset()){el('reconcile').hidden=true;el('canvas').replaceChildren();el('table').replaceChildren();"
        },
        {
          find: "el('group-count').textContent=result.group_count?`${fmt(result.offset+1)}\u2013${fmt(result.offset+result.rows.length)} of ${fmt(result.group_count)} groups`:'No matching observations';",
          replace: "el('group-count').textContent=result.group_count?`${fmt(result.offset+1)}\u2013${fmt(result.offset+result.rows.length)} of ${fmt(result.group_count)} groups \u00b7 totals cover all ${fmt(result.group_count)}`:'No matching observations';"
        },
        {
          find: "status('Verified contribution fields \u00b7 '+data.columns.length+' fields');renderPager();\n",
          replace: "status('Verified contribution fields \u00b7 '+data.columns.length+' fields');renderPager();renderReconcile(result);\n"
        },
        {
          find: "    }catch(error){if(ticket===contributionRevision&&error.name!=='AbortError'){el('canvas').replaceChildren();el('note').textContent=error.message;failure(error.message);lastResult=null;}}\n",
          replace: "    }catch(error){if(ticket===contributionRevision&&error.name!=='AbortError'){el('reconcile').hidden=true;el('canvas').replaceChildren();el('note').textContent=error.message;failure(error.message);lastResult=null;}}\n"
        },
        {
          find: "    el('param-groups').title='Groups per page. Totals and CSV exports include every matching group.';\n",
          replace: "    el('param-groups').title='40 per page (verified) \u00b7 fold after 40 (worksheet); Graph and classic fold at 60. Totals and CSV exports include every matching group.';\n"
        },
        {
          find: "  function renderView() {\n    if(verified()){renderContributionView();return;}\n    lastResult = null; lastConfig = null;\n",
          replace: "  function renderView() {\n    if(verified()){renderContributionView();return;}\n    lastResult = null; lastConfig = null;\n    el('reconcile').hidden = true;\n"
        },
        {
          find: "  function renderScopeChip() {\n" +
            "    // The Data source button is permanent. The one way back to the report\n" +
            "    // picker must never depend on there being a scope to describe.\n" +
            "    el('scope-chip').textContent = scopeText();\n" +
            "  }\n",
          replace: "  /* ------------------------------------------------------- reconciliation */\n\n" +
            "  // The Graph controls that have no verified field. They are read at the\n" +
            "  // moment of the comparison, because they decide which question Graph was\n" +
            "  // asked, and therefore which difference has to be explained.\n" +
            "  const graphFilterState = () => ({\n" +
            "    tier: (document.getElementById('graph-tier') || {}).value || '',\n" +
            "    funding: (document.getElementById('graph-funding') || {}).value || 'all'\n" +
            "  });\n\n" +
            "  // The same question, asked of Graph. One request per scope, remembered for\n" +
            "  // the session, because the strip is redrawn on every display edit and a\n" +
            "  // reconciliation must never cost a query the reader did not ask for.\n" +
            "  const graphTotalsCache = new Map();\n" +
            "  function graphTotals(company, cycle) {\n" +
            "    const run = (document.getElementById('graph-run') || {}).value || '';\n" +
            "    const industry = (dataset() || {}).id || '';\n" +
            "    if (!run || !industry) return Promise.reject(new Error('Graph has no saved run selected.'));\n" +
            "    const chosen = graphFilterState();\n" +
            "    const params = new URLSearchParams({id: run, industry: industry, company: company || '',\n" +
            "      tier: chosen.tier, cycle: core.graphCycleValue(cycle), funding: chosen.funding,\n" +
            "      mode: 'direct', direction: '', category: '', recipient: ''});\n" +
            "    const key = params.toString();\n" +
            "    if (graphTotalsCache.has(key)) return graphTotalsCache.get(key);\n" +
            "    const promise = Promise.resolve(api('/api/graph?' + params))\n" +
            "      .catch(error => { graphTotalsCache.delete(key); throw error; });\n" +
            "    graphTotalsCache.set(key, promise);\n" +
            "    return promise;\n" +
            "  }\n\n" +
            "  // The strip only means anything when both views were asked the same\n" +
            "  // question, so it fires for a sheet whose row filters are a company, a\n" +
            "  // cycle, or both - each one exact single value - and nothing else.\n" +
            "  function reconcileScope() {\n" +
            "    const meta = core.classifyFields(columns(), sheet().types);\n" +
            "    const scope = {company: '', cycle: ''};\n" +
            "    for (const filter of sheet().filters || []) {\n" +
            "      if (!core.filterActive(filter)) continue;\n" +
            "      const field = meta.fields.find(f => f.index === Number(filter.column));\n" +
            "      const id = field ? field.id : '';\n" +
            "      const values = core.filterValues(filter);\n" +
            "      if ((id !== 'company' && id !== 'cycle') || filter.stage === 'aggregate' ||\n" +
            "          ['equals', 'in'].indexOf(filter.op) === -1 || values.length !== 1 || scope[id]) return null;\n" +
            "      scope[id] = values[0];\n" +
            "    }\n" +
            "    return scope;\n" +
            "  }\n\n" +
            "  // A Graph request that fails, or a scope Graph cannot express, leaves the\n" +
            "  // strip away entirely. An absent strip is honest; a guessed one is not.\n" +
            "  async function renderReconcile(result) {\n" +
            "    const node = el('reconcile');\n" +
            "    node.hidden = true;\n" +
            "    if (!verified() || !result) return;\n" +
            "    const scope = reconcileScope();\n" +
            "    if (!scope) return;\n" +
            "    const ticket = contributionRevision;\n" +
            "    let graphView;\n" +
            "    try { graphView = await graphTotals(scope.company, scope.cycle); }\n" +
            "    catch { return; }\n" +
            "    if (ticket !== contributionRevision || !verified()) return;\n" +
            "    const state = contributions.reconcile(result, basis(), graphView, graphFilterState());\n" +
            "    if (state.reasonId === 'unavailable') return;\n" +
            "    const money = value => contributionPlot.format(value, 'amount');\n" +
            "    const where = [scope.company || 'All companies', scope.cycle || 'All cycles'].join(' \u00b7 ');\n" +
            "    const lead = document.createElement('span');\n" +
            "    lead.textContent = 'Basis: ' + ((contributions.BASIS[basis()] || [])[0] || basis()) +\n" +
            "      '. Graph shows ' + money(state.graphCents) + ' for ' + where +\n" +
            "      ' (workbook receipts). Studio total ' + money(state.studioCents) + '. ';\n" +
            "    const verdict = document.createElement('strong');\n" +
            "    verdict.className = state.agree ? 'studio-reconcile-agree' : 'studio-reconcile-differ';\n" +
            "    verdict.textContent = state.agree ? 'Agree.'\n" +
            "      : 'Differ by ' + money(Math.abs(state.differenceCents)) + ' because ' + state.reason + '.';\n" +
            "    const link = document.createElement('button');\n" +
            "    link.type = 'button';\n" +
            "    link.className = 'studio-reconcile-link';\n" +
            "    link.textContent = 'Why Cross-reference differs';\n" +
            "    link.onclick = () => {\n" +
            "      if (typeof showView === 'function') showView('cross-reference');\n" +
            "      else location.hash = '#cross-reference';\n" +
            "    };\n" +
            "    node.replaceChildren(lead, verdict, document.createTextNode(' '), link);\n" +
            "    node.hidden = false;\n" +
            "  }\n\n" +
            "  function renderScopeChip() {\n" +
            "    // The Data source button is permanent. The one way back to the report\n" +
            "    // picker must never depend on there being a scope to describe.\n" +
            "    el('scope-chip').textContent = scopeText();\n" +
            "    // What the hand-off could not bring across is stated beside the scope,\n" +
            "    // not left for the reader to meet as a number that looks too large.\n" +
            "    const notes = (appliedScope && appliedScope.notCarried) || [];\n" +
            "    el('scope-note').textContent = notes.join(' \u00b7 ');\n" +
            "    el('scope-note').hidden = !notes.length;\n" +
            "  }\n"
        },
        {
          find: "    appliedScope = {carried: true, industry: scope.industry,\n" +
            "      company: (scope.filters.find(f => f.field === 'company') || {}).value || '',\n" +
            "      cycle: (scope.filters.find(f => f.field === 'cycle') || {}).value || ''};\n",
          replace: "    appliedScope = {carried: true, industry: scope.industry,\n" +
            "      company: (scope.filters.find(f => f.field === 'company') || {}).value || '',\n" +
            "      cycle: (scope.filters.find(f => f.field === 'cycle') || {}).value || '',\n" +
            "      notCarried: [...(scope.notCarried || []),\n" +
            "        ...missing.map(field => field + ': not carried (this source has no ' + field + ' field)')]};\n"
        },
        {
          find: "  const GRAPH_SCOPE = [['company', 'company'], ['cycle', 'cycle']];\n",
          replace: "  const GRAPH_SCOPE = [['company', 'company'], ['cycle', 'cycle']];\n" +
            "  // What Graph can narrow by and this source cannot. Naming each one on the\n" +
            "  // scope chip is the difference between a total that looks wrong and a\n" +
            "  // total the reader knows is wider than the one they just left.\n" +
            "  const GRAPH_NOT_CARRIED = [\n" +
            "    ['tier', 'Employee level', 'verified data has no level field', ''],\n" +
            "    ['funding', 'Giving type', 'verified data has no employee or corporate funding field', 'all'],\n" +
            "    ['mode', 'Candidate view', 'downstream PAC activity and estimates stay in Graph', 'direct'],\n" +
            "    ['direction', 'Support or opposition', 'that distinction exists only in Graph', '']\n" +
            "  ];\n"
        },
        {
          find: "    const scope = {industry: read('industry'), filters: []};\n",
          replace: "    const scope = {industry: read('industry'), filters: [], notCarried: []};\n"
        },
        {
          find: "      if (value) scope.filters.push({field, value: core.carriedFilterValue(field, value)});\n    }\n    return scope;\n  }\n",
          replace: "      if (value) scope.filters.push({field, value: core.carriedFilterValue(field, value)});\n" +
            "    }\n" +
            "    for (const [control, label, why, ignored] of GRAPH_NOT_CARRIED) {\n" +
            "      const value = read(control);\n" +
            "      if (value && value !== ignored) scope.notCarried.push(label + ': not carried (' + why + ')');\n" +
            "    }\n" +
            "    return scope;\n  }\n"
        }
      ]
    },
    {
      path: 'graph.js',
      eol: 'crlf',
      edits: [
        {
          find: "    get('total').textContent=dollars(view.totals.giving);get('direct').textContent=dollars(view.totals.direct);\n",
          replace: "    get('total').textContent=dollars(view.totals.giving);get('direct').textContent=dollars(view.totals.direct);\n" +
            "    // Name the figure, so a reader can match it to Chart Studio rather than\n" +
            "    // wonder which of two numbers on two screens is the real one.\n" +
            "    get('basis-note').textContent='Workbook included receipts, net. Same figure as Chart Studio\u2019s Published included receipts basis.';\n"
        }
      ]
    },
    {
      path: 'chart-studio.css',
      eol: 'crlf',
      edits: [
        {
          find: "  color: var(--ink, #342649);\n",
          replace: "  color: var(--acu-plum);\n"
        },
        {
          find: ".studio-scope-chip:empty { display: none; }\n",
          replace: ".studio-scope-chip:empty { display: none; }\n" +
            ".studio-scope-block { display: inline-flex; flex-direction: column; align-items: flex-start; gap: 2px; min-width: 0; }\n" +
            "/* What the hand-off could not bring across, under the scope it did. */\n" +
            ".studio-scope-note { font-size: 11px; color: var(--muted); max-width: 60ch; }\n" +
            ".studio-scope-note[hidden] { display: none; }\n"
        },
        {
          find: ".studio-note { font-size: 11px; color: var(--muted); margin: 0 0 8px; }\n",
          replace: ".studio-note { font-size: 11px; color: var(--muted); margin: 0 0 8px; }\n" +
            "/* Graph and Studio read one workbook. When their totals differ, the strip\n" +
            "   names the reason on the screen where the reader met the difference. */\n" +
            ".studio-reconcile {\n" +
            "  font-size: 12px;\n" +
            "  line-height: 1.45;\n" +
            "  color: var(--acu-plum);\n" +
            "  background: var(--acu-ivory);\n" +
            "  border: 1px solid var(--line);\n" +
            "  border-radius: 5px;\n" +
            "  padding: 7px 10px;\n" +
            "  margin: 0 0 10px;\n" +
            "}\n" +
            ".studio-reconcile[hidden] { display: none; }\n" +
            ".studio-reconcile-agree { color: var(--acu-teal); font-weight: 600; }\n" +
            ".studio-reconcile-differ { color: var(--chart-negative); font-weight: 600; }\n" +
            ".studio-reconcile-link {\n" +
            "  font: inherit;\n" +
            "  font-size: 12px;\n" +
            "  color: var(--acu-purple);\n" +
            "  background: none;\n" +
            "  border: 0;\n" +
            "  padding: 0;\n" +
            "  text-decoration: underline;\n" +
            "  cursor: pointer;\n" +
            "}\n"
        }
      ]
    },
    {
      path: 'cross-reference.js',
      eol: 'lf',
      edits: [
        {
          from: "  const reasons = {\n",
          to: "  const reason = value =>",
          replace: "  // Engine keys, in the plain words a lobbyist reads. Anything unmapped still\n" +
            "  // falls back to the key with its underscores removed, so a new engine\n" +
            "  // reason is legible before it is named here.\n" +
            "  const reasons = {\n" +
            "    filing_relationship_evidence_missing:'Filing and amendment relationship needs evidence',\n" +
            "    latest_filing_completeness_unproven:'Complete latest filing has not been established',\n" +
            "    company_pac_affiliation_unresolved:'Company connection to the PAC needs dated evidence',\n" +
            "    signed_adjustment_not_linked_refund:'Negative adjustment has no linked refund',\n" +
            "    receipt_role_unresolved:'Transaction meaning needs evidence',\n" +
            "    treasury_ownership_unresolved:'Corporate ownership needs dated evidence',\n" +
            "    reciprocal_earmark_not_established:'Intermediary route lacks a matching disclosure',\n" +
            "    source_or_attribution_conflict:'Source facts or company matches disagree',\n" +
            "    funding_identity_unresolved:'Who supplied the money is unresolved',\n" +
            "    memo_parent_ambiguous:'Memo points to more than one possible receipt',\n" +
            "    company_attribution_unresolved:'Donor not yet matched to a listed company (counted at $0)',\n" +
            "    attribution_unresolved:'Attribution not settled (counted at $0)',\n" +
            "    company_attribution_not_accepted:'Company match not accepted',\n" +
            "    memo_parent_not_established:'Memo entry without a proven parent receipt',\n" +
            "    original_source_of_transfer_unresolved:'Transfer whose original donor is unresolved',\n" +
            "    earmark_counterpart_not_unique:'Earmark with more than one possible counterpart',\n" +
            "    earmark_destination_ambiguous:'Earmark destination ambiguous',\n" +
            "    overlapping_or_cyclic_earmark_links:'Earmark links overlap or loop',\n" +
            "    observed_filing_versions_unresolved:'Amended filings not reconciled',\n" +
            "    latest_filing_transaction_replacement_missing:'Latest filing lacks the replacing transaction',\n" +
            "    latest_filing_manifest_not_corroborated:'Latest filing not corroborated by its manifest',\n" +
            "    linked_refunds_exceed_original_gift:'Refunds exceed the original gift',\n" +
            "    receipt_date_missing:'Receipt date missing',\n" +
            "    excluded_source_metadata_conflict:'Source metadata conflict',\n" +
            "    superseded_in_observed_filing_family:'Superseded by a later filing',\n" +
            "    same_original_gift_at_conduit_and_destination:'Same gift seen at conduit and destination',\n" +
            "    explicit_same_filing_memo_reference:'Memo references its own filing',\n" +
            "    explicit_observed_refund:'Observed refund',\n" +
            "    linked_refund:'Linked refund adjustment',\n" +
            "  };\n"
        },
        {
          find: "  function metric(title, value, detail) {\n" +
            "    return `<div class=\"xref-metric\"><span>${title}</span><strong>${value}</strong><small>${detail}</small></div>`;\n" +
            "  }\n",
          replace: "  // Which election cycles a figure describes. A dollar total with no period\n" +
            "  // beside it invites the reader to compare it with one from another run.\n" +
            "  let scopeCycles = '';\n" +
            "  function metric(title, value, detail, money) {\n" +
            "    const cycles = money && scopeCycles ? `<small class=\"xref-metric-cycles\">Cycles ${escape(scopeCycles)}</small>` : '';\n" +
            "    return `<div class=\"xref-metric\"><span>${title}</span><strong>${value}</strong>${cycles}<small>${detail}</small></div>`;\n" +
            "  }\n"
        },
        {
          find: "  function html(data) {\n",
          replace: "  function html(data) {\n    scopeCycles = '';\n"
        },
        {
          find: "    const s = report.summary || {}, scope = report.scope || {};\n",
          replace: "    const s = report.summary || {}, scope = report.scope || {};\n    scopeCycles = items(scope.cycles).join(', ');\n"
        },
        {
          find: "    content += metric('Observed original giving', money(s.observed_original_giving), s.verified_unique ? 'Counted under the scope and evidence rules of this run.' : 'Signed amounts after cross-referencing. Includes unresolved giving; not yet verified unique dollars.');\n" +
            "    content += metric('Observed PAC outgoing activity', money(s.pac_outgoing), 'Recipient-reported activity in these records; incomplete. Do not add it to original giving.');\n",
          replace: "    content += metric('Observed original giving', money(s.observed_original_giving), s.verified_unique ? 'Counted under the scope and evidence rules of this run.' : 'Signed amounts after cross-referencing. Includes unresolved giving; not yet verified unique dollars.', true);\n" +
            "    content += metric('Observed PAC outgoing activity', money(s.pac_outgoing), 'Recipient-reported activity in these records; incomplete. Do not add it to original giving.', true);\n"
        },
        {
          find: "    content += '</dl><p class=\"xref-caption\">These amounts follow the classifications supported in this run. Unverified funding attribution remains in the original-giving view.</p>';\n",
          replace: "    content += '</dl><p class=\"xref-caption\">These amounts follow the classifications supported in this run. Unverified funding attribution remains in the original-giving view.</p>';\n" +
            "    content += '<p class=\"xref-caption\">Rows with an unresolved company attribution are counted at $0 in every total above; memo, transfer, earmark and role reviews stay inside Observed original giving until resolved.</p>';\n"
        },
        {
          find: "${metric('Previous receipt total', money(s.baseline_amount), 'Selected baseline. Changes may also separate different money stages.')}${metric('Change from previous total', money(s.amount_change), 'Every change is preserved with its evidence in the local ledger.')}",
          replace: "${metric('Previous receipt total', money(s.baseline_amount), 'Selected baseline. Changes may also separate different money stages.', true)}${metric('Change from previous total', money(s.amount_change), 'Every change is preserved with its evidence in the local ledger.', true)}"
        }
      ]
    }
  ]
};
