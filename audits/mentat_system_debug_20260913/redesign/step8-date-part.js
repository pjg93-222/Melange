/* Step 8: make Date part appear for every date-like verified field.
   - core: date-likeness comes from the catalog's own date hierarchy (ids), not
     from the detected time flag, and the current part is reported.
   - studio: one Date part block instead of two overlapping ones, hoisted to the
     top of the pill menu, and a menu that flips above its anchor rather than
     running off the bottom of the window. */
'use strict';

const dateParts = `  const DATE_PARTS = [['cycle', 'Election cycle'], ['year', 'Year'], ['quarter', 'Quarter'],
    ['month', 'Month'], ['date', 'Exact date']];
  const DATE_FIELD_IDS = DATE_PARTS.map(part => part[0]);

  // Date-likeness is read from the catalog's own date hierarchy first. The
  // detected time flag is only a fallback, so a date part cannot disappear
  // because that flag was lost somewhere between the catalog and the pill.
  const isDateLike = field => !!field && field.role === 'dimension' &&
    (DATE_FIELD_IDS.indexOf(field.id) !== -1 || !!field.isTime);

  function datePartsFor(field, columns, engine, state) {
    if (!isDateLike(field)) return [];
    if (engine === 'verified') {
      const meta = classifyFields(columns);
      return DATE_PARTS
        .map(([id, label]) => {
          const target = meta.fields.find(f => f.id === id);
          return {id: id, label: label, column: target ? target.index : -1, current: field.id === id};
        })
        .filter(part => part.column >= 0);
    }
    // A worksheet has one date column, so the part is the period the existing
    // transform groups by rather than a column the worksheet does not have.
    const analytics = (state && state.analytics) || {};
    const grouped = analytics.transform === 'annual';
    return [['cycle', 'Election cycle'], ['year', 'Year']]
      .map(([id, label]) => ({id: id, label: label, column: field.index, current: grouped && analytics.period === id}));
  }`;

const datePartItems = `    return items;
  }

  // Date part is one control, not two: it replaces the older "Use <field> here"
  // swap, it sits at the top of the pill menu so it can never be the entry that
  // falls below the fold, and it reads the catalog's date hierarchy.
  function datePartItems(anchor, field, settings) {
    const parts = core.datePartsFor(field, columns(), engine(), sheet());
    if (!parts.length) return [];
    const items = [['Date part', null, {group: true}]];
    for (const part of parts) {
      if (part.current) {
        items.push(['\\u2713 ' + part.label, null,
          {disabled: true, reason: 'This pill already groups by ' + part.label.toLowerCase() + '.'}]);
        continue;
      }
      items.push([part.label, () => commit(() => {
        if (!verified()) { sheet().analytics.period = part.id; sheet().analytics.transform = 'annual'; return; }
        const zone = settings.zone === 'rows' ? 'rows' : settings.zone === 'columns' ? 'columns' : '';
        if (zone) {
          const pills = core.shelf(sheet()[zone]);
          if (pills[settings.position]) {
            pills[settings.position] = {column: part.column, aggregation: 'sum'};
            sheet()[zone] = pills;
            return;
          }
        }
        place('columns', part.column);
      })]);
    }
    return items;
  }`;

const sendMenu = `  function sendMenu(anchor, field, settings) {
    const items = [];
    if (settings.zone === 'filters') items.push(['Edit filter\\u2026', () => filterEditor(anchor, settings.position)]);
    items.push(...datePartItems(anchor, field, settings));
    const onAxis = settings.zone === 'columns' || settings.zone === 'rows';
    if (onAxis && field.role === 'measure') {
      const aggregations = core.aggregationsFor(field, engine());
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
    items.push(...typeMenuItems(anchor, field, settings));
    items.push(['Place', null, {group: true}]);
    items.push(...ZONES.map(([zone, label]) => ['Send to ' + label, () => commit(() => {
      if (settings.zone) removeFrom(settings.zone, settings.position);
      place(zone, field.index, null, settings.aggregation);
    })]));
    if (settings.zone) items.push(['Remove from ' + settings.zone, () => commit(() => removeFrom(settings.zone, settings.position))]);
    popup(anchor, items);
  }`;

module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat\\app',
  eol: 'crlf',
  files: [{
    path: 'chart-studio-core.js',
    edits: [
      {
        find: `  const DATE_PARTS = [['cycle', 'Election cycle'], ['year', 'Year'], ['quarter', 'Quarter'], ['month', 'Month']];

  function datePartsFor(field, columns, engine) {
    if (!field || !field.isTime || field.role !== 'dimension') return [];
    const meta = classifyFields(columns);
    if (engine === 'verified') {
      return DATE_PARTS
        .map(([id, label]) => ({id, label, column: (meta.fields.find(f => f.id === id) || {index: -1}).index}))
        .filter(part => part.column >= 0 && part.column !== field.index);
    }
    return [{id: 'cycle', label: 'Election cycle', column: field.index},
      {id: 'year', label: 'Year', column: field.index}];
  }`,
        replace: dateParts
      },
      {
        find: `    canTreatAs, filterValues, filterActive, filterBounds, normalizeFilter, filterSummary,`,
        replace: `    canTreatAs, isDateLike, filterValues, filterActive, filterBounds, normalizeFilter, filterSummary,`
      }
    ]
  }, {
    path: 'chart-studio.js',
    edits: [
      {
        find: `    if (field.isTime && field.role === 'dimension') {
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
  }`,
        replace: datePartItems
      },
      {
        find: `  function sendMenu(anchor, field, settings) {
    const items = ZONES.map(([zone, label]) => ['Send to ' + label, () => commit(() => {
      if (settings.zone) removeFrom(settings.zone, settings.position);
      place(zone, field.index, null, settings.aggregation);
    })]);
    if (settings.zone) items.push(['Remove from ' + settings.zone, () => commit(() => removeFrom(settings.zone, settings.position))]);
    if (settings.zone === 'filters') items.unshift(['Edit filter\u2026', () => filterEditor(anchor, settings.position)]);
    const onAxis = settings.zone === 'columns' || settings.zone === 'rows';
    const aggregations = onAxis ? core.aggregationsFor(field, engine()) : [];
    if (onAxis && field.role === 'measure') {
      items.push(['Measure', null, {group: true}]);
      if (aggregations.length) items.push(['Aggregation\u2026', () => aggregationMenu(anchor, settings.zone, settings.position, aggregations)]);
      else items.push(['Aggregation\u2026', null, {disabled: true,
        reason: field.name + ' is computed from the source observations, so it has one definition.'}]);
      const others = core.classifyFields(columns(), sheet().types).measures.filter(f => f.index !== field.index);
      items.push(['Replace measure\u2026', others.length ? () => popup(anchor, others.map(other => [other.name, () => commit(() => {
        const pills = core.shelf(sheet()[settings.zone]);
        if (pills[settings.position]) { pills[settings.position] = {column: other.index, aggregation: 'sum'}; sheet()[settings.zone] = pills; }
      })])) : null, {disabled: !others.length, reason: 'This source has no other measure.'}]);
      items.push(['Political money\u2026', () => popup(anchor, core.measurePresets(columns(), engine(), sheet().types)
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
  }`,
        replace: sendMenu
      },
      {
        find: `    const box = anchor.getBoundingClientRect();
    menu.style.left = Math.round(box.left + window.scrollX) + 'px';
    menu.style.top = Math.round(box.bottom + window.scrollY + 4) + 'px';
    document.body.append(menu);`,
        replace: `    const box = anchor.getBoundingClientRect();
    menu.style.left = Math.round(box.left + window.scrollX) + 'px';
    menu.style.top = Math.round(box.bottom + window.scrollY + 4) + 'px';
    document.body.append(menu);
    // A long menu must never run off the bottom of the window: the entries at
    // the end are the ones nobody thinks to scroll for.
    const height = menu.getBoundingClientRect().height;
    const below = window.innerHeight - box.bottom;
    if (height > below && box.top > below) {
      menu.style.top = Math.max(4, Math.round(box.top + window.scrollY - height - 4)) + 'px';
    }`
      }
    ]
  }, {
    path: 'tests/chart-studio-core.test.js',
    edits: [{
      find: `test('date parts use real catalog columns when verified and periods on a worksheet', () => {
  const verified = core.classifyFields(VERIFIED);
  const parts = core.datePartsFor(core.fieldAt(verified, 1), VERIFIED, 'verified');
  assert.deepStrictEqual(parts.map(p => p.id), ['year', 'quarter']);
  assert.deepStrictEqual(parts.map(p => p.column), [2, 3]);
  const worksheet = core.classifyFields(COLUMNS);
  const date = worksheet.fields.find(f => f.isTime);
  assert.deepStrictEqual(core.datePartsFor(date, COLUMNS, 'worksheet').map(p => p.id), ['cycle', 'year']);
  assert.deepStrictEqual(core.datePartsFor(core.fieldAt(worksheet, CATEGORY), COLUMNS, 'worksheet'), []);
});`,
      replace: `test('date parts use real catalog columns when verified and periods on a worksheet', () => {
  const verified = core.classifyFields(VERIFIED);
  const parts = core.datePartsFor(core.fieldAt(verified, 1), VERIFIED, 'verified');
  // The whole hierarchy this source has, with the pill's own part marked.
  assert.deepStrictEqual(parts.map(p => p.id), ['cycle', 'year', 'quarter']);
  assert.deepStrictEqual(parts.map(p => p.column), [1, 2, 3]);
  assert.deepStrictEqual(parts.map(p => p.current), [true, false, false]);
  const worksheet = core.classifyFields(COLUMNS);
  const date = worksheet.fields.find(f => f.isTime);
  assert.deepStrictEqual(core.datePartsFor(date, COLUMNS, 'worksheet').map(p => p.id), ['cycle', 'year']);
  assert.deepStrictEqual(core.datePartsFor(core.fieldAt(worksheet, CATEGORY), COLUMNS, 'worksheet'), []);
  // A worksheet marks the period the existing transform already groups by.
  const grouped = sheet({analytics: {transform: 'annual', period: 'year'}});
  assert.deepStrictEqual(core.datePartsFor(date, COLUMNS, 'worksheet', grouped).map(p => p.current), [false, true]);
});

test('a verified date field keeps its date parts even without the detected time flag', () => {
  // The catalog's date hierarchy is the authority; the flag is only a fallback,
  // so losing it anywhere between the catalog and the pill cannot hide the menu.
  const stripped = VERIFIED.map(field => {
    const copy = Object.assign({}, field);
    delete copy.is_time;
    return copy;
  });
  const meta = core.classifyFields(stripped);
  for (const id of ['cycle', 'year', 'quarter']) {
    const field = meta.fields.find(f => f.id === id);
    assert.strictEqual(core.isDateLike(field), true, id + ' should be date-like');
    assert.ok(core.datePartsFor(field, stripped, 'verified').length >= 3, id + ' should offer parts');
  }
  // A plain dimension is still not date-like, flag or no flag.
  assert.strictEqual(core.isDateLike(meta.fields.find(f => f.id === 'company')), false);
  assert.deepStrictEqual(core.datePartsFor(meta.fields.find(f => f.id === 'company'), stripped, 'verified'), []);
  // Neither is a measure that happens to be named like a date.
  assert.strictEqual(core.isDateLike({id: 'date', role: 'measure', isTime: true}), false);
});`
    }]
  }]
};
