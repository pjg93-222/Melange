/* Step 5: company overview mode - one company, four preset views, rendered in
   this page through the same compile -> query -> paint path as the builder. */
'use strict';

const overview = `  /* ------------------------------------------------------- company overview */

  // Four preset views of one company. No iframes: each card compiles a preset
  // sheet, runs the ordinary verified query and paints it with the same
  // renderers the builder uses, so a card and its builder view are one view.
  function overviewCycle() {
    const field = columns().find(f => f.id === 'cycle');
    if (!field) return '';
    const filter = (sheet().filters || []).find(f => Number(f.column) === field.index);
    if (!filter || !core.filterActive(filter)) return '';
    const values = core.filterValues(filter);
    return (filter.op === 'equals' || filter.op === 'in') && values.length === 1 ? values[0] : '';
  }
  function renderOverviewControls() {
    const toggle = el('overview-toggle');
    const reason = !verified() ? 'Company overview uses verified contributions.'
      : !data || !dataset() ? 'Choose a verified report source first.'
      : !columns().some(f => f.id === 'company') ? 'This source has no company field.' : '';
    toggle.disabled = !!reason;
    toggle.title = reason || 'Four preset views of one company';
    if (reason) overviewMode = false;
    toggle.setAttribute('aria-pressed', String(overviewMode));
    el('overview').hidden = !overviewMode;
    el('grid').hidden = dataSourceTab || overviewMode;
    const host = document.querySelector('#view-chart-studio .studio');
    if (host) host.classList.toggle('studio-overview-mode', overviewMode);
  }
  function renderOverview() {
    const field = columns().find(f => f.id === 'company');
    if (!field) return;
    const list = members(field.index);
    const carried = (appliedScope && appliedScope.company) || '';
    if (!overviewCompany || (list.length && list.indexOf(overviewCompany) === -1)) {
      overviewCompany = list.indexOf(carried) !== -1 ? carried : list[0] || '';
    }
    fill(el('overview-company'), list.length ? list.map(m => [m, m]) : [['', 'Reading companies\\u2026']]);
    el('overview-company').value = overviewCompany;
    const cycle = overviewCycle();
    el('overview-scope').textContent = [overviewCompany || 'No company selected',
      (dataset() || {}).label || (dataset() || {}).id || '', cycle ? 'Cycle ' + cycle : 'All cycles',
      contributions.BASIS[basis()][0]].filter(Boolean).join(' \\u00b7 ');
    const ticket = ++overviewRevision;
    const grid = el('overview-grid');
    grid.replaceChildren();
    const cards = core.companyOverviewPresets().map(preset => {
      const card = document.createElement('section');
      card.className = 'studio-overview-card';
      const title = document.createElement('h3');
      title.textContent = preset.title;
      const note = document.createElement('p');
      note.className = 'studio-note';
      note.textContent = preset.note;
      const body = document.createElement('div');
      body.className = 'studio-overview-body';
      body.textContent = 'Reading verified totals\\u2026';
      const actions = document.createElement('div');
      actions.className = 'studio-overview-actions';
      const open = document.createElement('button');
      open.type = 'button';
      open.textContent = 'Open in builder';
      open.onclick = () => {
        overviewMode = false;
        commit(() => {
          sheets[active] = core.companyOverviewSheet(preset, columns(),
            {company: overviewCompany, cycle: overviewCycle()}, sheet());
        });
      };
      actions.append(open);
      card.append(title, note, body, actions);
      card.onmouseenter = () => {
        for (const other of grid.children) other.classList.toggle('is-focused', other === card);
      };
      grid.append(card);
      return {preset: preset, body: body};
    });
    if (!overviewCompany) {
      for (const item of cards) item.body.textContent = 'Choose a company to read its giving.';
      return;
    }
    // One query at a time: queryCached aborts the previous request, so four
    // parallel cards would cancel each other.
    (async () => {
      for (const item of cards) {
        if (ticket !== overviewRevision) return;
        try { await renderOverviewCard(item.preset, item.body, ticket); }
        catch (error) { if (ticket === overviewRevision && error.name !== 'AbortError') item.body.textContent = error.message; }
      }
    })();
  }
  async function renderOverviewCard(preset, body, ticket) {
    const missing = core.companyOverviewMissing(preset, columns());
    if (missing.length) { body.textContent = 'This source has no ' + missing.join(' or ') + ' field.'; return; }
    const state = core.companyOverviewSheet(preset, columns(), {company: overviewCompany, cycle: overviewCycle()});
    const compiled = contributions.compile(state, columns(), {dataset: dataset().id, basis: basis(), offset: 0});
    const result = await queryCached(compiled.query);
    if (ticket !== overviewRevision) return;
    body.replaceChildren();
    if (!result.rows.length) { body.textContent = 'No matching observations in this scope.'; return; }
    const spec = Object.assign({}, compiled.spec, {columns: result.columns, title: preset.title});
    if (['pie', 'doughnut', 'waterfall', 'pareto', 'radar'].includes(spec.type)) {
      const id = spec.measures[0], currency = contributions.MONEY.has(id);
      const groups = result.rows.map(row => ({label: contributionPlot.label(row, spec.dimensions),
        value: row[id] / (currency ? 100 : 1), n: 1}));
      const measure = ((result.columns.find(c => c.id === id) || {}).name || id) + (currency ? ' (USD)' : '');
      const drawn = paint.chartSVG({type: spec.type, groups: groups, selected: result.totals.records, excluded: 0},
        measure, {type: spec.type, aggregation: 'sum', x: 0, y: 1},
        {columns: [{name: 'Group'}, {name: id}]}, preset.title, '');
      body.append(drawn.svg);
    } else if (MentatContributionCharts.TYPES.includes(spec.type)) {
      MentatContributionCharts.render(body, result.rows, spec, () => {});
    } else {
      contributionPlot.render(body, result.rows, spec, () => {});
    }
  }

`;

module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat\\app',
  eol: 'crlf',
  files: [{
    path: 'chart-studio.js',
    edits: [
      {
        find: `    appliedScope = {carried: true, industry: scope.industry};`,
        replace: `    appliedScope = {carried: true, industry: scope.industry,
      company: (scope.filters.find(f => f.field === 'company') || {}).value || '',
      cycle: (scope.filters.find(f => f.field === 'cycle') || {}).value || ''};`
      },
      {
        find: `  /* ---------------------------------------------------------------- sheets */`,
        replace: overview + `  /* ---------------------------------------------------------------- sheets */`
      },
      {
        find: `    renderScopeChip();
    renderFilterRows();
    if (!dataSourceTab && !overviewMode) renderView();`,
        replace: `    renderScopeChip();
    renderFilterRows();
    renderOverviewControls();
    if (overviewMode) renderOverview();
    else if (!dataSourceTab) renderView();`
      },
      {
        find: `  el('filter-add').onchange = () => {`,
        replace: `  el('overview-toggle').onclick = () => {
    overviewMode = !overviewMode;
    if (overviewMode) el('inspection').hidden = true;
    renderAll();
  };
  el('overview-company').onchange = () => { overviewCompany = el('overview-company').value; renderOverview(); };
  if (window.matchMedia && window.matchMedia('(max-width: 1200px)').matches) el('inspector').hidden = true;
  el('filter-add').onchange = () => {`
      }
    ]
  }, {
    path: 'index.html',
    edits: [
      {
        find: `<button id="studio-inspector-close" class="studio-inspector-close" type="button" hidden>Close</button>`,
        replace: `<button id="studio-inspector-close" class="studio-inspector-close" type="button">Close</button>`
      }
    ]
  }, {
    path: 'chart-studio.css',
    edits: [
      {
        find: `.studio-inspector-close { font: inherit;`,
        replace: `.studio-inspector-close { display: none; font: inherit;`
      },
      {
        find: `  .studio-inspector-close { display: inline-block!important; }`,
        replace: `  .studio-inspector-close { display: inline-block; }`
      },
      {
        find: `.studio-overview { padding: 14px; background: var(--acu-paper); }`,
        replace: `.studio-overview-mode .studio-toolbar, .studio-overview-mode .studio-quick-tools { display: none; }
.studio-overview { padding: 14px; background: var(--acu-paper); }`
      }
    ]
  }, {
    path: 'chart-comparison.js',
    edits: [
      {
        find: `  let hidden=false;
  const quick=document.createElement('div');quick.className='studio-quick-tools';
  const name=document.createElement('strong');name.textContent='Chart '+(embedded?paneId:'A');quick.append(name);
  const mark=document.getElementById('studio-mark').closest('label');mark.firstChild.textContent='Chart variant';quick.append(mark);
  const toggle=button('Hide chart options',()=>setOptions(!hidden));toggle.setAttribute('aria-expanded','true');
  toggle.className='studio-options-restore';toggle.id='studio-options-toggle';quick.append(toggle);
  document.getElementById('studio-canvas-wrap').before(quick);
  function setOptions(value){hidden=!!value;studio.classList.toggle('studio-options-hidden',hidden);
    toggle.textContent=hidden?'Show chart options':'Hide chart options';toggle.setAttribute('aria-expanded',String(!hidden));
    window.dispatchEvent(new Event('mentat:studio-options'));}
  const pane=window.MentatStudioPane;if(pane)pane.options=setOptions;`,
        replace: `  let hidden=false;
  const api=window.MentatStudioPane;
  const quick=document.createElement('div');quick.className='studio-quick-tools';
  const name=document.createElement('span');name.className='studio-pane-tag';name.textContent='Chart '+(embedded?paneId:'A');quick.append(name);
  const mark=document.getElementById('studio-mark').closest('label');mark.firstChild.textContent='Chart variant';quick.append(mark);
  (document.getElementById('studio-shelves')||document.getElementById('studio-canvas-wrap')).before(quick);
  // The header's Builder | Canvas only control is the one visible switch. This
  // stays as the pane API the grid calls, so every pane moves together.
  function setOptions(value){hidden=!!value;
    if(api&&api.setOptionsHidden)api.setOptionsHidden(hidden);else studio.classList.toggle('studio-options-hidden',hidden);
    window.dispatchEvent(new Event('mentat:studio-options'));}
  if(api)api.options=setOptions;`
      },
      {
        find: `  }toolbar.append(links);`,
        replace: `  }toolbar.append(links);
  const overviewToggle=document.getElementById('studio-overview-toggle');if(overviewToggle)toolbar.append(overviewToggle);`
      },
      {
        find: `    allOptions.textContent=state.hidden?'Show all options':'Hide all options';`,
        replace: `    allOptions.textContent=state.hidden?'Builder in every chart':'Canvas only in every chart';`
      }
    ]
  }]
};
