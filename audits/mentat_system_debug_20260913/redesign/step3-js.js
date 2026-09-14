/* Steps 1-4 + 6 in chart-studio.js: header and Inspector wiring, the filter
   popover and Inspector Filters tab, the measure/aggregation menu, data-type
   actions, and the member-facet negative cache. */
'use strict';

const menus = `  const engine = () => verified() ? 'verified' : 'worksheet';
  const fieldOf = column => core.fieldAt(core.classifyFields(columns(), sheet().types), Number(column));

  // Type glyphs are drawn, never typed: no emoji, and they take the pill's ink.
  function typeGlyph(kind) {
    const svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('viewBox', '0 0 12 12');
    svg.setAttribute('aria-hidden', 'true');
    const shapes = kind === 'cal'
      ? [['rect', {x: 1, y: 2.6, width: 10, height: 8.4, rx: 1, fill: 'none', stroke: 'currentColor', 'stroke-width': 1.2}],
         ['line', {x1: 1, y1: 5.2, x2: 11, y2: 5.2, stroke: 'currentColor', 'stroke-width': 1.2}],
         ['line', {x1: 3.6, y1: 1, x2: 3.6, y2: 3.6, stroke: 'currentColor', 'stroke-width': 1.2}],
         ['line', {x1: 8.4, y1: 1, x2: 8.4, y2: 3.6, stroke: 'currentColor', 'stroke-width': 1.2}]]
      : [['path', {d: 'M6 1.1c-2 0-3.5 1.5-3.5 3.4C2.5 7.2 6 11 6 11s3.5-3.8 3.5-6.5C9.5 2.6 8 1.1 6 1.1z',
          fill: 'none', stroke: 'currentColor', 'stroke-width': 1.2}],
         ['circle', {cx: 6, cy: 4.5, r: 1.2, fill: 'currentColor'}]];
    for (const [tag, attributes] of shapes) {
      const node = document.createElementNS(NS, tag);
      for (const name of Object.keys(attributes)) node.setAttribute(name, String(attributes[name]));
      svg.append(node);
    }
    return svg;
  }

  // Data-type actions. A verified field keeps the role its source defines, so
  // the menu says so rather than offering a change the query cannot express.
  function typeMenuItems(anchor, field, settings) {
    const items = [['Data type', null, {group: true}]];
    const overrides = sheet().types || {};
    for (const role of ['dimension', 'measure']) {
      const label = 'Treat as ' + (role === 'dimension' ? 'Dimension' : 'Measure');
      if (verified()) {
        items.push([label, null, {disabled: true,
          reason: 'Verified fields keep the role the source defines. ZIP, committee ID and election cycle are already dimensions.'}]);
        continue;
      }
      const check = core.canTreatAs(field, role);
      if (!check.ok) { items.push([label, null, {disabled: true, reason: check.reason}]); continue; }
      items.push([label, () => commit(() => {
        const next = Object.assign({}, sheet().types || {});
        next[String(field.index)] = {role: role};
        sheet().types = next;
      })]);
    }
    if (overrides[String(field.index)]) items.push(['Use the detected type', () => commit(() => {
      const next = Object.assign({}, sheet().types || {});
      delete next[String(field.index)];
      sheet().types = next;
    })]);
    if (field.isTime && field.role === 'dimension') {
      const parts = core.datePartsFor(field, columns(), engine());
      items.push(['Date part', null, {group: true}]);
      if (!parts.length) items.push(['No other date part in this source', null,
        {disabled: true, reason: 'This source has no other date column.'}]);
      for (const part of parts) items.push([part.label, () => commit(() => {
        if (!verified()) { sheet().analytics.period = part.id; sheet().analytics.transform = 'annual'; return; }
        if (settings.zone === 'columns' || settings.zone === 'rows') {
          const pills = core.shelf(sheet()[settings.zone]);
          if (pills[settings.position]) { pills[settings.position] = {column: part.column, aggregation: 'sum'}; sheet()[settings.zone] = pills; }
          return;
        }
        place('columns', part.column);
      })]);
    }
    return items;
  }

  function sendMenu(anchor, field, settings) {
    const items = ZONES.map(([zone, label]) => ['Send to ' + label, () => commit(() => {
      if (settings.zone) removeFrom(settings.zone, settings.position);
      place(zone, field.index, null, settings.aggregation);
    })]);
    if (settings.zone) items.push(['Remove from ' + settings.zone, () => commit(() => removeFrom(settings.zone, settings.position))]);
    if (settings.zone === 'filters') items.unshift(['Edit filter\\u2026', () => filterEditor(anchor, settings.position)]);
    const onAxis = settings.zone === 'columns' || settings.zone === 'rows';
    const aggregations = onAxis ? core.aggregationsFor(field, engine()) : [];
    if (onAxis && field.role === 'measure') {
      items.push(['Measure', null, {group: true}]);
      if (aggregations.length) items.push(['Aggregation\\u2026', () => aggregationMenu(anchor, settings.zone, settings.position, aggregations)]);
      else items.push(['Aggregation\\u2026', null, {disabled: true,
        reason: field.name + ' is computed from the source observations, so it has one definition.'}]);
      const others = core.classifyFields(columns(), sheet().types).measures.filter(f => f.index !== field.index);
      items.push(['Replace measure\\u2026', others.length ? () => popup(anchor, others.map(other => [other.name, () => commit(() => {
        const pills = core.shelf(sheet()[settings.zone]);
        if (pills[settings.position]) { pills[settings.position] = {column: other.index, aggregation: 'sum'}; sheet()[settings.zone] = pills; }
      })])) : null, {disabled: !others.length, reason: 'This source has no other measure.'}]);
      items.push(['Political money\\u2026', () => popup(anchor, core.measurePresets(columns(), engine(), sheet().types)
        .map(preset => [preset.label,
          preset.available ? () => commit(() => { sheets[active] = core.applyMeasurePreset(preset.id, sheet(), columns(), engine()); }) : null,
          {disabled: !preset.available, reason: preset.reason}]))]);
    }
    if (verified() && field.role === 'dimension' && field.isTime && onAxis) {
      for (const id of ['year', 'quarter', 'month', 'date']) {
        const target = columns().find(f => f.id === id);
        if (target && target.id !== field.id) items.push(['Use ' + target.name + ' here', () => commit(() => {
          sheet()[settings.zone][settings.position] = {column: target.index, aggregation: 'sum'};
        })]);
      }
    }
    items.push(...typeMenuItems(anchor, field, settings));
    popup(anchor, items);
  }
  function aggregationMenu(anchor, zone, position, list) {
    popup(anchor, (list || core.AGGREGATIONS).map(([id, label]) => [label, () => commit(() => {
      const pills = core.shelf(sheet()[zone]);
      if (pills[position]) { pills[position].aggregation = id; sheet()[zone] = pills; }
    })]));
  }
`;

const facets = `  // The facet query behind a member list, and the key that identifies it. A
  // field's own filter never narrows its own member list, so opening the
  // checklist shows every member the rest of the scope allows.
  function facetSpec(column) {
    const field = columns().find(f => f.index === column);
    if (!field || field.role !== 'dimension' || !dataset()) return null;
    const filters = [];
    for (const f of sheet().filters || []) {
      if (f.stage === 'aggregate') continue;
      const source = columns().find(c => c.index === Number(f.column));
      if (!source || source.index === column) continue;
      if (source.role === 'measure' && source.id !== 'amount') continue;
      try { filters.push(...contributions.clauses(f, source)); }
      catch { /* an unfinished filter does not narrow the member list */ }
    }
    const facet = {dataset: dataset().id, basis: basis(), dimensions: [field.id], measures: ['records'],
      filters: filters, aggregate_filters: [], sort: [{field: field.id, direction: 'asc'}], limit: 100000, offset: 0};
    return {key: JSON.stringify(facet), facet: facet, field: field};
  }
  function membersCached(column) {
    const spec = verified() ? facetSpec(column) : null;
    if (!spec) return null;
    const entry = memberCache.get(spec.key);
    return entry && !entry.error && entry.values.length ? entry.values : null;
  }
  const memberTotal = column => verified() ? (membersCached(column) || []).length : members(column).length;
`;

const filterEditor = `  // The filter pill's editor: a searchable member checklist for dimensions, a
  // pair of bounds for numbers and dates, and the verified engine's stage
  // choice. Apply goes through commit(), so a filter edit is one undo step.
  function filterEditor(anchor, position) {
    const stored = sheet().filters[position];
    if (!stored) return;
    const filter = core.normalizeFilter(stored);
    const field = fieldOf(filter.column);
    if (!field) return;
    const menu = popup(anchor, []);
    const form = document.createElement('div');
    form.className = 'studio-filter-editor';
    const head = document.createElement('div');
    head.className = 'studio-filter-head';
    const title = document.createElement('strong');
    title.textContent = field.name;
    head.append(title);
    const numeric = field.role === 'measure';
    const dated = !numeric && (field.type === 'date' || field.unit === 'date');
    const choices = numeric
      ? [['between', 'Between'], ['gte', 'At least'], ['lte', 'At most'], ['equals', 'Equals']]
      : dated ? [['between', 'Between'], ['equals', 'Equals']]
      : [['in', 'Is one of'], ['notin', 'Is not one of'], ['equals', 'Equals'], ['contains', 'Contains']];
    const operator = document.createElement('select');
    operator.setAttribute('aria-label', 'Filter operation');
    for (const [id, label] of choices) operator.append(new Option(label, id));
    operator.value = choices.some(choice => choice[0] === filter.op) ? filter.op : choices[0][0];
    let stage = null;
    if (verified()) {
      stage = document.createElement('select');
      stage.setAttribute('aria-label', 'Filter stage');
      if (field.role === 'dimension' || field.id === 'amount') stage.append(new Option('Source records, before grouping', 'rows'));
      if (field.role === 'measure') stage.append(new Option('Grouped values, after aggregation', 'aggregate'));
      stage.value = stored.stage || (field.role === 'measure' && field.id !== 'amount' ? 'aggregate' : 'rows');
    }
    const body = document.createElement('div');
    const hint = document.createElement('small');
    hint.textContent = verified()
      ? (numeric ? 'Money is entered in USD; counts are whole observations.'
        : 'Exact text preserves identifiers such as leading-zero ZIPs.')
      : 'Worksheet filters apply to source rows before aggregation.';
    let read = () => ({op: operator.value, value: ''});
    let poll = 0;
    const stopPoll = () => { if (poll) { clearInterval(poll); poll = 0; } };

    function drawScalar(count) {
      const inputs = [];
      for (let i = 0; i < count; i++) {
        const input = document.createElement('input');
        input.type = dated ? 'date' : numeric ? 'number' : 'text';
        input.setAttribute('aria-label', count === 1 ? 'Filter value' : i ? 'Upper bound' : 'Lower bound');
        if (count === 2) input.placeholder = i ? 'Up to' : 'From';
        inputs.push(input);
      }
      const bounds = core.filterBounds(filter);
      if (count === 2) inputs.forEach((input, i) => { input.value = filter.op === 'between' ? bounds[i] : ''; });
      else inputs[0].value = Array.isArray(filter.value) ? '' : filter.value;
      body.replaceChildren(...inputs);
      read = () => ({op: operator.value,
        value: count === 2 ? [inputs[0].value.trim(), inputs[1].value.trim()] : inputs[0].value.trim()});
      inputs[0].focus();
    }

    function drawList() {
      const chosen = new Set(core.filterValues(filter));
      const search = document.createElement('input');
      search.type = 'search';
      search.placeholder = 'Search values';
      search.setAttribute('aria-label', 'Search values');
      const links = document.createElement('div');
      links.className = 'studio-filter-links-row';
      const all = document.createElement('button');
      all.type = 'button';
      all.textContent = 'All';
      const none = document.createElement('button');
      none.type = 'button';
      none.textContent = 'None';
      links.append(all, none);
      const list = document.createElement('div');
      list.className = 'studio-filter-members';
      body.replaceChildren(search, links, list);
      const paint = () => {
        const available = members(field.index);
        const query = search.value.trim().toLowerCase();
        const shown = available.filter(value => !query || value.toLowerCase().includes(query)).slice(0, 400);
        list.replaceChildren();
        if (!available.length) {
          const note = document.createElement('p');
          note.textContent = verified() ? 'Reading the values of this field\\u2026' : 'This column has no values.';
          list.append(note);
        }
        for (const value of shown) {
          const row = document.createElement('label');
          const box = document.createElement('input');
          box.type = 'checkbox';
          box.checked = chosen.has(value);
          box.onchange = () => { if (box.checked) chosen.add(value); else chosen.delete(value); };
          row.append(box, document.createTextNode(value === '' ? '(blank)' : value));
          list.append(row);
        }
        if (available.length > shown.length) {
          const note = document.createElement('p');
          note.textContent = (available.length - shown.length) + ' more values \\u2014 narrow the search.';
          list.append(note);
        }
        return available.length;
      };
      search.oninput = paint;
      all.onclick = () => { for (const value of members(field.index)) chosen.add(value); paint(); };
      none.onclick = () => { chosen.clear(); paint(); };
      // members() memoises its facet query, so polling for the answer costs no
      // extra request; the negative cache stops a failed facet from re-firing.
      if (!paint() && verified()) {
        poll = setInterval(() => { if (!menu.isConnected || paint()) stopPoll(); }, 400);
        setTimeout(stopPoll, 20000);
      }
      read = () => ({op: operator.value, value: [...chosen]});
      search.focus();
    }

    const draw = () => {
      stopPoll();
      const op = operator.value;
      if (op === 'in' || op === 'notin') drawList(); else drawScalar(op === 'between' ? 2 : 1);
    };
    operator.onchange = draw;
    const actions = document.createElement('div');
    actions.className = 'studio-editor-actions';
    const apply = document.createElement('button');
    apply.type = 'button';
    apply.className = 'is-primary';
    apply.textContent = 'Apply';
    apply.onclick = () => {
      const next = read();
      stopPoll();
      menu.remove();
      commit(() => {
        sheet().filters[position] = core.normalizeFilter(Object.assign({column: Number(filter.column)}, next,
          stage ? {stage: stage.value} : {}));
      });
    };
    const cancel = document.createElement('button');
    cancel.type = 'button';
    cancel.textContent = 'Cancel';
    cancel.onclick = () => { stopPoll(); menu.remove(); if (anchor.isConnected) anchor.focus(); };
    const remove = document.createElement('button');
    remove.type = 'button';
    remove.textContent = 'Remove';
    remove.onclick = () => { stopPoll(); menu.remove(); commit(() => removeFrom('filters', position)); };
    actions.append(apply, cancel, remove);
    form.append(head, operator, body);
    if (stage) form.append(stage);
    form.append(hint, actions);
    menu.append(form);
    draw();
  }

  // The Inspector's Filters tab and the Filters shelf are the same filters.
  function renderFilterRows() {
    const meta = core.classifyFields(columns(), sheet().types);
    const rows = (sheet().filters || []).map((filter, position) => {
      const field = core.fieldAt(meta, Number(filter.column));
      if (!field) return null;
      const row = document.createElement('div');
      row.className = 'studio-filter-row';
      const name = document.createElement('strong');
      name.textContent = field.name;
      const summary = document.createElement('span');
      summary.textContent = core.filterSummary(filter, field, memberTotal(field.index));
      const actions = document.createElement('div');
      actions.className = 'studio-editor-actions';
      const edit = document.createElement('button');
      edit.type = 'button';
      edit.textContent = 'Edit';
      edit.onclick = () => filterEditor(edit, position);
      const drop = document.createElement('button');
      drop.type = 'button';
      drop.textContent = 'Remove';
      drop.onclick = () => commit(() => removeFrom('filters', position));
      actions.append(edit, drop);
      row.append(name, summary, actions);
      return row;
    }).filter(Boolean);
    el('filter-rows').replaceChildren(...rows);
    const used = new Set((sheet().filters || []).map(f => Number(f.column)));
    fill(el('filter-add'), [['', 'Add a field\\u2026'],
      ...meta.dimensions.concat(meta.measures).filter(f => !used.has(f.index)).map(f => [String(f.index), f.name])]);
    el('tab-filters').textContent = rows.length ? 'Filters (' + rows.length + ')' : 'Filters';
  }

  // The scope chip states the industry, cycle and company this view is reading,
  // and says when that scope arrived from the Graph tab.
  function scopeText() {
    if (!data) return '';
    if (!verified()) {
      const source = sheet().source;
      return [source.reportName, data.sheet].filter(Boolean).join(' \\u00b7 ');
    }
    const meta = core.classifyFields(columns(), sheet().types);
    const valueOf = id => {
      const field = meta.fields.find(f => f.id === id);
      if (!field) return '';
      const filter = (sheet().filters || []).find(f => Number(f.column) === field.index);
      if (!filter || !core.filterActive(filter)) return '';
      const values = core.filterValues(filter);
      return values.length === 1 ? values[0] : values.length ? values.length + ' selected' : '';
    };
    const carried = !!(appliedScope && appliedScope.carried);
    const company = valueOf('company');
    const parts = [(dataset() || {}).label || (dataset() || {}).id || '', valueOf('cycle') || 'All cycles'];
    if (carried || company) parts.push(company || 'All companies');
    return (carried ? 'Carried from Graph \\u00b7 ' : '') + parts.filter(Boolean).join(' \\u00b7 ');
  }
  function renderScopeChip() {
    const text = scopeText();
    el('scope-chip').textContent = text;
    el('scope-change').hidden = !text;
  }

  // Canvas only hides the builder surfaces; the control that does it never
  // hides, so there is always a way back.
  function setOptionsHidden(hidden) {
    const host = document.querySelector('#view-chart-studio .studio');
    if (host) host.classList.toggle('studio-options-hidden', !!hidden);
    el('view-builder').setAttribute('aria-checked', String(!hidden));
    el('view-canvas').setAttribute('aria-checked', String(!!hidden));
    el('view-builder').tabIndex = hidden ? -1 : 0;
    el('view-canvas').tabIndex = hidden ? 0 : -1;
  }
  const applyOptionsHidden = hidden => {
    const pane = window.MentatStudioPane;
    if (pane && typeof pane.options === 'function') pane.options(hidden);
    else setOptionsHidden(hidden);
  };
  function setInspectorTab(name) {
    inspectorTab = ['marks', 'analytics', 'filters'].includes(name) ? name : 'marks';
    for (const id of ['marks', 'analytics', 'filters']) {
      const selected = id === inspectorTab;
      el('tab-' + id).setAttribute('aria-selected', String(selected));
      el('tab-' + id).tabIndex = selected ? 0 : -1;
      el('pane-' + id).hidden = !selected;
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
        find: `  const OPERATORS = [['equals', 'Equals'], ['contains', 'Contains'], ['gte', 'At least'], ['lte', 'At most']];`,
        replace: `  const OPERATORS = core.FILTER_OPS;
  const AGG_LABEL = {sum: 'SUM', mean: 'AVG', count: 'COUNT', median: 'MEDIAN', min: 'MIN', max: 'MAX'};`
      },
      {
        find: `  let pendingScope = null;`,
        replace: `  let pendingScope = null, appliedScope = null;
  let inspectorTab = 'marks', overviewMode = false, overviewRevision = 0, overviewCompany = '';
  let queryRequests = 0;`
      },
      {
        find: `  async function contributionAPI(path, body, signal) {
    const response=await fetch`,
        replace: `  async function contributionAPI(path, body, signal) {
    if(path==='query'&&body)queryRequests++;
    const response=await fetch`
      },
      {
        find: `    if (!pills.length && !missing.length) return;
    commit(() => {
      const kept = (sheet().filters || []).filter(f => !pills.some(p => p.column === f.column));`,
        replace: `    appliedScope = {carried: true, industry: scope.industry};
    if (!pills.length && !missing.length) return;
    commit(() => {
      const kept = (sheet().filters || []).filter(f => !pills.some(p => p.column === Number(f.column)));`
      },
      {
        find: `      const field=columns().find(f=>f.index===column);if(!field||field.role!=='dimension'||!dataset())return [];
      const filters=(sheet().filters||[]).filter(f=>f.stage!=='aggregate').flatMap(f=>{const column=columns().find(c=>c.index===Number(f.column));if(!column||column.role==='measure'&&column.id!=='amount')return [];return [{field:column.id,op:{equals:'eq',contains:'contains',gte:'gte',lte:'lte'}[f.op],value:contributions.filterValue(f.value,column)}];});
      const facet={dataset:dataset().id,basis:basis(),dimensions:[field.id],measures:['records'],filters,aggregate_filters:[],sort:[{field:field.id,direction:'asc'}],limit:100000,offset:0};
      const key=JSON.stringify(facet);if(core.pill(sheet().pages)?.column===column)pageMembersKey=key;const cached=memberCache.get(key);if(cached)return cached.values||[];
      memberCache.set(key,{values:[]});const selectedDataset=dataset().id;
      contributionReady('query',facet).then(result=>{
        const values=result.rows.map(r=>String(r[field.id]??''));memberCache.set(key,{values});if(verified()&&dataset()?.id===selectedDataset&&pageMembersKey===key&&core.pill(sheet().pages)?.column===column){if(!values.includes(sheet().pageMember))sheet().pageMember=values[0]||'';persist();renderAll();}
      }).catch(error=>{memberCache.delete(key);failure(error.message);});return [];`,
        replace: `      const spec=facetSpec(column);if(!spec)return [];
      const {key,facet,field}=spec;
      if(core.pill(sheet().pages)?.column===column)pageMembersKey=key;
      // A facet that failed is remembered for thirty seconds instead of being
      // deleted, because deleting it re-fired the same query from every later
      // render - the page-load query burst.
      const cached=memberCache.get(key);
      if(cached&&(!cached.error||Date.now()-cached.at<30000))return cached.values||[];
      memberCache.set(key,{values:(cached&&cached.values)||[],at:Date.now()});const selectedDataset=dataset().id;
      contributionReady('query',facet).then(result=>{
        const values=result.rows.map(r=>String(r[field.id]??''));memberCache.set(key,{values,at:Date.now()});
        if(verified()&&dataset()?.id===selectedDataset&&pageMembersKey===key&&core.pill(sheet().pages)?.column===column&&!values.includes(sheet().pageMember)){sheet().pageMember=values[0]||'';persist();}
        renderAll();
      }).catch(error=>{memberCache.set(key,{values:[],at:Date.now(),error:error.message});failure(error.message);});return [];`
      },
      {
        find: `    const label = core.AGGREGATIONS.find(a => a[0] === aggregation);
    return (label ? label[1] : 'Sum').toUpperCase() + '(' + field.name + ')';`,
        replace: `    return (AGG_LABEL[aggregation] || 'SUM') + '(' + field.name + ')';`
      },
      {
        find: `    glyph.textContent = field.glyph === 'geo'?'\u25ce':field.glyph==='bool'?'T/F':field.glyph === '#' ? '#' : field.glyph === 'cal' ? '\u25a6' : 'Abc';`,
        replace: `    if (field.glyph === 'cal' || field.glyph === 'geo') glyph.append(typeGlyph(field.glyph));
    else glyph.textContent = field.glyph === 'bool' ? 'T/F' : field.glyph === '#' ? '#' : 'Abc';
    glyph.title = field.glyph === 'cal' ? 'Date' : field.glyph === 'geo' ? 'Geography'
      : field.glyph === '#' ? 'Number' : field.glyph === 'bool' ? 'True/false' : 'Text';`
      },
      {
        find: `    if (settings.zone && field.role === 'measure' && ['columns', 'rows'].includes(settings.zone) && (!verified()||field.id==='amount')) {
      const menu = document.createElement('button');
      menu.type = 'button';
      menu.className = 'studio-pill-menu';
      menu.textContent = '\u25be';
      menu.setAttribute('aria-label', 'Aggregation for ' + field.name);
      menu.onclick = event => { event.stopPropagation(); aggregationMenu(node, settings.zone, settings.position); };
      node.append(menu);
      node.oncontextmenu = event => { event.preventDefault(); aggregationMenu(node, settings.zone, settings.position); };
    }`,
        replace: `    if (settings.zone) {
      const menu = document.createElement('button');
      menu.type = 'button';
      menu.className = 'studio-pill-menu';
      menu.textContent = '\u25be';
      menu.setAttribute('aria-label', 'Actions for ' + field.name);
      menu.onclick = event => { event.stopPropagation(); sendMenu(node, field, settings); };
      node.append(menu);
      node.oncontextmenu = event => { event.preventDefault(); sendMenu(node, field, settings); };
    }`
      },
      {
        find: `    for (const [label, action] of items) {
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = label;
      button.onclick = () => {
        menu.remove();
        if (anchor.isConnected) anchor.focus();
        action();
      };
      menu.append(button);
    }`,
        replace: `    for (const [label, action, options] of items) {
      const settings = options || {};
      if (settings.group) {
        const heading = document.createElement('div');
        heading.className = 'studio-send-group';
        heading.textContent = label;
        menu.append(heading);
        continue;
      }
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = label;
      if (settings.disabled || !action) {
        button.disabled = true;
        button.title = settings.reason || '';
      } else {
        button.onclick = () => {
          menu.remove();
          if (anchor.isConnected) anchor.focus();
          action();
        };
      }
      menu.append(button);
    }`
      },
      {
        find: `    const first = menu.querySelector('button');`,
        replace: `    const first = menu.querySelector('button:not(:disabled)');`
      },
      {
        find: `  function sendMenu(anchor, field, settings) {
    const items = ZONES.map(([zone, label]) => ['Send to ' + label, () => commit(() => {
      if (settings.zone) removeFrom(settings.zone, settings.position);
      place(zone, field.index, null, settings.aggregation);
    })]);
    if (settings.zone) items.push(['Remove from ' + settings.zone, () => commit(() => removeFrom(settings.zone, settings.position))]);
    if(verified()&&field.role==='dimension'&&field.isTime&&['columns','rows'].includes(settings.zone))for(const id of ['year','quarter','month','date']){const target=columns().find(f=>f.id===id);if(target&&target.id!==field.id)items.push(['Use '+target.name+' here',()=>commit(()=>{sheet()[settings.zone][settings.position]={column:target.index,aggregation:'sum'};})]);}
    popup(anchor, items);
  }
  function aggregationMenu(anchor, zone, position) {
    popup(anchor, core.AGGREGATIONS.map(([id, label]) => [label, () => commit(() => {
      const pills = core.shelf(sheet()[zone]);
      if (pills[position]) { pills[position].aggregation = id; sheet()[zone] = pills; }
    })]));
  }`,
        replace: menus
      },
      {
        find: `    } else if (zone === 'filters') {
      if (!canPlace(zone, column)) return false;
      state.filters = state.filters.concat({column, op: 'equals', value: firstMember(column)});`,
        replace: `    } else if (zone === 'filters') {
      if (!canPlace(zone, column)) return false;
      // A new filter starts as an empty choice, which selects nothing and
      // therefore filters nothing, instead of inheriting an arbitrary value.
      const chosen = core.fieldAt(core.classifyFields(columns(), state.types), column);
      state.filters = state.filters.concat(chosen && chosen.role === 'measure'
        ? {column, op: 'between', value: ['', '']}
        : {column, op: 'in', value: []});`
      },
      {
        find: `  function members(column) {
    if (!data) return [];`,
        replace: facets + `  function members(column) {
    if (!data) return [];`
      },
      {
        find: `      const node = pillNode(field, {zone: 'filters', position});
      const operator = OPERATORS.find(o => o[0] === filter.op);
      node.querySelector('.studio-pill-name').textContent =
        field.name + ' ' + (operator ? operator[1].toLowerCase() : filter.op) + ' ' + filter.value;
      return node;`,
        replace: `      const node = pillNode(field, {zone: 'filters', position});
      const summary = core.filterSummary(filter, field, memberTotal(field.index));
      node.querySelector('.studio-pill-name').textContent = summary;
      node.title = summary + ' \\u00b7 Enter for actions, Delete to remove it';
      return node;`
      },
      {
        find: `core.classifyFields(columns())`,
        replace: `core.classifyFields(columns(), sheet().types)`,
        count: 5
      },
      {
        find: `    el('showme-toggle').setAttribute('aria-pressed', String(!el('showme').hidden));`,
        replace: `    el('showme-toggle').setAttribute('aria-pressed', String(!el('showme').hidden));
    el('showme-toggle').classList.toggle('is-primary', el('showme').hidden);`
      },
      {
        find: `  function filterEditor(anchor, position) {
    const filter = sheet().filters[position];
    if (!filter) return;
    const menu = popup(anchor, []);
    const form = document.createElement('div');
    form.className = 'studio-filter-editor';
    const operator = document.createElement('select');
    operator.setAttribute('aria-label', 'Filter operation');
    for (const [id, label] of OPERATORS) operator.append(new Option(label, id));
    operator.value = filter.op;
    const value = document.createElement('input');
    value.type = 'text';
    value.setAttribute('aria-label', 'Filter value');
    value.value = filter.value;
    const actions = document.createElement('div');
    let stage=null;
    if(verified()){
      const field=columns().find(f=>f.index===Number(filter.column));
      stage=document.createElement('select');stage.setAttribute('aria-label','Filter stage');
      if(field?.role==='dimension'||field?.id==='amount')stage.append(new Option('Source records, before grouping','rows'));
      if(field?.role==='measure')stage.append(new Option('Grouped values, after aggregation','aggregate'));
      stage.value=filter.stage||(field?.role==='measure'&&field.id!=='amount'?'aggregate':'rows');form.append(stage);
      const hint=document.createElement('small');hint.textContent=field?.role==='measure'?'Money values are entered in USD; counts are whole observations.':'Exact text preserves identifiers such as leading-zero ZIPs.';form.append(hint);
    }
    actions.className = 'studio-editor-actions';
    const apply = document.createElement('button');
    apply.type = 'button';
    apply.textContent = 'Apply';
    apply.onclick = () => {
      menu.remove();
      commit(() => {
        sheet().filters[position] = {column: Number(filter.column), op: operator.value, value: value.value,...(stage?{stage:stage.value}:{})};
      });
    };
    const remove = document.createElement('button');
    remove.type = 'button';
    remove.textContent = 'Remove';
    remove.onclick = () => { menu.remove(); commit(() => removeFrom('filters', position)); };
    actions.append(apply, remove);
    form.append(operator, value, actions);
    menu.append(form);
    operator.focus();
  }`,
        replace: filterEditor
      },
      {
        find: `  for (const id of ['tab-data', 'tab-analytics']) el(id).onclick = () => {
    const wantData = id === 'tab-data';
    el('tab-data').setAttribute('aria-selected', String(wantData));
    el('tab-analytics').setAttribute('aria-selected', String(!wantData));
    el('pane-data').hidden = !wantData;
    el('pane-analytics').hidden = wantData;
  };`,
        replace: `  for (const id of ['marks', 'analytics', 'filters']) el('tab-' + id).onclick = () => setInspectorTab(id);
  el('view-builder').onclick = () => applyOptionsHidden(false);
  el('view-canvas').onclick = () => applyOptionsHidden(true);
  el('scope-change').onclick = () => {
    el('source-details').open = true;
    el('source-details').querySelector('summary').focus();
  };
  el('inspector-toggle').onclick = () => {
    const open = el('inspector').hidden;
    el('inspector').hidden = !open;
    el('inspector-toggle').setAttribute('aria-expanded', String(open));
  };
  el('inspector-close').onclick = () => {
    el('inspector').hidden = true;
    el('inspector-toggle').setAttribute('aria-expanded', 'false');
    el('inspector-toggle').focus();
  };
  el('filter-add').onchange = () => {
    const column = Number(el('filter-add').value);
    el('filter-add').value = '';
    if (!Number.isInteger(column)) return;
    commit(() => { place('filters', column); });
    setInspectorTab('filters');
  };`
      },
      {
        find: `    renderDataSource();
    if (!dataSourceTab) renderView();`,
        replace: `    renderDataSource();
    renderScopeChip();
    renderFilterRows();
    if (!dataSourceTab && !overviewMode) renderView();`
      },
      {
        find: `    options(hidden) { document.querySelector('#view-chart-studio > .studio, #view-chart-studio .studio').classList.toggle('studio-options-hidden',hidden); }`,
        replace: `    options(hidden) { setOptionsHidden(hidden); },
    setOptionsHidden`
      },
      {
        find: `el('status').textContent=fmt(result.totals.records)+' source observations · '+fmt(result.group_count)+' groups · '+(result.reconciliation?.receipt_matches_workbook===true?'Included receipts reconcile to the workbook.':'Verified source records.');`,
        replace: `el('status').textContent=fmt(result.totals.records)+' source observations · '+fmt(result.group_count)+' groups · '+(result.reconciliation?.receipt_matches_workbook===true?'Included receipts reconcile to the workbook.':'Verified source records.')+' · '+fmt(queryRequests)+' verified queries this session';`
      }
    ]
  }]
};
