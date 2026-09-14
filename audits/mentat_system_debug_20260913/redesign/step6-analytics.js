/* Step 1 (Inspector, continued): the Analytics objects become switch rows -
   name, one-line hint, switch on the right - with the four transforms in a
   single-select radio group. A refused object shows its reason as the hint. */
'use strict';

const renderAnalytics = `  function analyticsRow(item, state, role) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'studio-analytics-item';
    const refusal = analyticsRefusal(item);
    button.draggable = !refusal;
    button.disabled = !!refusal;
    const on = item.group === 'transform' ? state.analytics.transform === item.id : !!state.analytics[item.id];
    button.setAttribute('role', role);
    button.setAttribute('aria-checked', String(on));
    const text = document.createElement('span');
    text.className = 'studio-analytics-text';
    const title = document.createElement('span');
    title.textContent = item.label;
    const hint = document.createElement('small');
    hint.textContent = refusal || item.hint;
    text.append(title, hint);
    const knob = document.createElement('span');
    knob.className = 'studio-switch';
    knob.setAttribute('aria-hidden', 'true');
    if (refusal) button.title = refusal;
    button.append(text, knob);
    button.onclick = () => applyAnalytics(item.id);
    button.addEventListener('dragstart', event => {
      dragging = {kind: 'analytics', id: item.id};
      dropped = false;
      event.dataTransfer.effectAllowed = 'copy';
      event.dataTransfer.setData('text/plain', item.label);
    });
    button.addEventListener('dragend', () => { dragging = null; });
    return button;
  }

  function renderAnalytics() {
    const state = sheet();
    const host = el('analytics-list');
    host.replaceChildren();
    // One period analysis at a time; the reference lines are independent.
    for (const [kind, heading, role] of [['transform', 'Period analysis', 'radio'], ['flag', 'Summarize', 'switch']]) {
      const label = document.createElement('p');
      label.className = 'studio-analytics-group';
      label.textContent = heading;
      const box = document.createElement('div');
      if (role === 'radio') {
        box.setAttribute('role', 'radiogroup');
        box.setAttribute('aria-label', heading);
      }
      for (const item of ANALYTICS.filter(a => a.group === kind)) box.append(analyticsRow(item, state, role));
      host.append(label, box);
    }
  }`;

module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat\\app',
  eol: 'crlf',
  files: [{
    path: 'chart-studio.js',
    edits: [
      {
        find: `  function renderAnalytics() {
    const state = sheet();
    el('analytics-list').replaceChildren(...ANALYTICS.map(item => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'studio-analytics-item';
      const refusal = analyticsRefusal(item);
      button.draggable = !refusal;
      button.disabled = !!refusal;
      const on = item.group === 'transform' ? state.analytics.transform === item.id : !!state.analytics[item.id];
      button.setAttribute('aria-pressed', String(on));
      const title = document.createElement('span');
      title.textContent = item.label;
      const hint = document.createElement('small');
      hint.textContent = refusal || item.hint;
      if (refusal) button.title = refusal;
      button.append(title, hint);
      button.onclick = () => applyAnalytics(item.id);
      button.addEventListener('dragstart', event => {
        dragging = {kind: 'analytics', id: item.id};
        dropped = false;
        event.dataTransfer.effectAllowed = 'copy';
        event.dataTransfer.setData('text/plain', item.label);
      });
      button.addEventListener('dragend', () => { dragging = null; });
      return button;
    }));
  }`,
        replace: renderAnalytics
      },
      {
        find: `      card.append(title, note, body, actions);`,
        replace: `      card.append(title, note, body, actions);
      if (!grid.children.length) card.classList.add('is-focused');`
      }
    ]
  }, {
    path: 'chart-studio.css',
    edits: [
      {
        find: `.studio-analytics-item[aria-pressed=true] .studio-switch { background: var(--acu-purple); }
.studio-analytics-item[aria-pressed=true] .studio-switch::after { left: 15px; }`,
        replace: `.studio-analytics-item[aria-checked=true] .studio-switch { background: var(--acu-purple); }
.studio-analytics-item[aria-checked=true] .studio-switch::after { left: 15px; }
.studio-analytics-item[aria-checked=true] { border-color: var(--acu-purple); }
.studio-analytics-item[aria-checked=true] .studio-analytics-text > span { font-weight: 600; }`
      }
    ]
  }]
};
