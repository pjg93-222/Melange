/* Flow (Sankey) renderer: SVG for the Flow views (lane F, boards #44-#46).
 *
 * One rendering path. svgString() turns a flow-layout.js result into SVG markup (pure,
 * so node:test reads exactly what the page draws); mount() puts it in a host and wires
 * the reader's hands with delegated listeners:
 *  - hover (or keyboard focus) lights one whole route upstream and downstream and fades
 *    the rest;
 *  - click re-roots on a committee (options.onReroot) and opens a candidate
 *    (options.onCandidate: the downstream drawer);
 *  - a tooltip gives the amount, its share of the stage, the rows behind it and the FEC
 *    link (MentatScope.fecLink, the one place such URLs are vetted);
 *  - arrow keys move focus through the nodes (up/down in a column, left/right across).
 *
 * Ribbon colour: Source | Target | Outcome | Gradient. Gradient is an SVG linearGradient
 * per ribbon, userSpaceOnUse from the source's right edge to the target's left edge: the
 * source colour blends into the target colour. Default opacity 40%. Colours come only
 * from MentatTheme.categorical. Pooled money is never coloured by an original donor: a
 * ribbon takes the colour of the committee it leaves (or its outcome), never a donor's.
 *
 * CSP (style-src 'self'): no style attributes and no <style>; presentation attributes and
 * classes only, and the tooltip is placed through the CSSOM.
 */
(function (root) {
  'use strict';

  const layoutApi = () => root.MentatFlowLayout || (typeof require === 'function' ? require('./flow-layout.js') : null);
  const NEUTRAL = '#a39b92';
  const FALLBACK = ['#327a7a', '#57447b', '#8b6984', '#eca91c', '#de8aab', '#7d4b00', '#3cb0a3', '#83333e', '#99973f',
    '#a09eea', '#d88766', '#509ecd'];
  const PARTY_RING = {R: '#83333e', D: '#509ecd'};
  const MODES = ['gradient', 'source', 'target', 'outcome'];

  const escape = value => String(value == null ? '' : value).replace(/[&<>"']/g, character =>
    ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[character]));
  const f = number => String(Math.round(number * 100) / 100);

  function short(value) {
    const size = Math.abs(value), sign = value < 0 ? '-' : '';
    // Tenths of a million rounded half up on the exact number, as the board prints $54.6M
    // for $54,550,000 (toFixed on the binary 54.55 would say 54.5).
    if (size >= 999950) return `${sign}$${(Math.round(size / 1e5) / 10).toFixed(1)}M`;
    if (size >= 1000) return `${sign}$${Math.round(size / 1000).toLocaleString('en-US')}K`;
    return `${sign}$${Math.round(size).toLocaleString('en-US')}`;
  }
  const full = value => (value < 0 ? '-' : '') + '$' + Math.abs(value).toLocaleString('en-US',
    {minimumFractionDigits: 2, maximumFractionDigits: 2});
  const percent = share => `${(share * 100).toFixed(1)}%`;

  function palette() {
    const theme = root.MentatTheme;
    return theme && Array.isArray(theme.categorical) && theme.categorical.length >= 12 ? theme.categorical : FALLBACK;
  }

  const HELD = {bitcoin: 'bitcoin', 'USD coin': 'USD coin', ether: 'ether', tether: 'tether', solana: 'solana', stock: 'stock'};
  const heldWords = kinds => (kinds || []).map(kind => HELD[kind] || kind).join(' and ') || 'donated assets';

  // Text fitted to the room before the next column (MentatTheme.fitText in the page).
  function fitter(options) {
    const theme = root.MentatTheme;
    if (options.fit) return options.fit;
    if (theme && typeof theme.fitText === 'function') return (text, width, size) => theme.fitText(text, width, size);
    return (text, width, size) => {
      const room = Math.floor(width / (size * 0.56));
      return String(text).length <= room ? String(text) : String(text).slice(0, Math.max(1, room - 1)).trimEnd() + '\u2026';
    };
  }

  function nodeTitle(node) {
    if (node.kind !== 'candidate' || node.outcome) return node.label;
    const where = [node.party, node.state].filter(Boolean).join('-');
    return where ? `${node.label} (${where})` : node.label;
  }

  function prepare(payload, options) {
    const api = layoutApi();
    const theme = root.MentatTheme;
    if (!options.wrap && theme && typeof theme.wrapText === 'function')
      options = Object.assign({}, options, {wrap: (text, width, size) => theme.wrapText(text, width, size)});
    const result = api.layout(payload, options);
    const colours = api.colours(result, options.palette || palette(), options.neutral || NEUTRAL);
    // Chart Studio (#46): a worksheet flow deals its own colours after the palette's
    // (a stage member on Colour, a ribbon split by its Colour or Outcome member).
    if (typeof options.recolour === 'function') options.recolour(result, colours, options.palette || palette(), options.neutral || NEUTRAL);
    const outcomes = api.outcomes(result, colours);
    return {result, colours, outcomes, format: options.format || {short, full}};
  }

  function ribbonFill(link, context, mode, index, prefix) {
    const {colours, outcomes, result} = context;
    const byId = id => result.nodes.find(node => node.id === id);
    const source = byId(link.source), target = byId(link.target);
    const sourceColour = source.stub ? colours.get(target.id) : colours.get(source.id);
    const targetColour = target.stub ? colours.get(source.id) : colours.get(target.id);
    if (link.colour) return link.colour;
    if (mode === 'source') return sourceColour;
    if (mode === 'target') return targetColour;
    if (mode === 'outcome') return outcomes.get(target.stub ? source.id : target.id) || targetColour;
    return `url(#${prefix}-g-${index})`;
  }

  /* ----------------------------------------------------------------- markup */
  function svgString(payload, options) {
    options = Object.assign({ribbons: 'gradient', opacity: 0.4, width: 1100, height: 520, headers: true,
      labelSize: 13.5, subSize: 11.5, labelLine: 16, subLine: 15, amounts: true}, options || {});
    const mode = MODES.includes(options.ribbons) ? options.ribbons : 'gradient';
    const prefix = String(options.idPrefix || 'flow').replace(/[^A-Za-z0-9_-]/g, '');
    const context = prepare(payload, options);
    const {result, colours, format} = context;
    const fit = fitter(options);
    const byId = new Map(result.nodes.map(node => [node.id, node]));
    const parts = [];
    parts.push(`<svg xmlns="http://www.w3.org/2000/svg" class="flow-chart" viewBox="0 0 ${f(result.width)} ${f(result.height)}"`
      + ` width="${f(result.width)}" height="${f(result.height)}" role="group" aria-label="${escape(options.title || 'Flow of money')}">`);
    parts.push(`<defs><pattern id="${prefix}-hatch" patternUnits="userSpaceOnUse" width="6" height="6" patternTransform="rotate(45)">`
      + `<rect width="6" height="6" fill="#f4efe9"/><line x1="0" y1="0" x2="0" y2="6" stroke="${NEUTRAL}" stroke-width="1.4"/></pattern>`);
    result.links.forEach((link, index) => {
      const source = byId.get(link.source), target = byId.get(link.target);
      if (target.stub === 'before_gate') return;
      if ((mode !== 'gradient' || link.colour) && !source.stub && !target.stub) return;
      // Stubs fade in (money from outside) or out (money leaving the view) in the node's colour.
      const from = source.stub ? colours.get(target.id) : colours.get(source.id);
      const to = target.stub ? colours.get(source.id) : colours.get(target.id);
      const fadeIn = source.stub ? 0 : 1, fadeOut = target.stub ? 0 : 1;
      parts.push(`<linearGradient id="${prefix}-g-${index}" gradientUnits="userSpaceOnUse" x1="${f(link.gradient.x1)}" y1="0"`
        + ` x2="${f(link.gradient.x2)}" y2="0"><stop offset="0" stop-color="${from}" stop-opacity="${fadeIn}"/>`
        + `<stop offset="1" stop-color="${to}" stop-opacity="${fadeOut}"/></linearGradient>`);
    });
    parts.push('</defs>');
    if (options.headers) {
      parts.push('<g class="flow-headers" aria-hidden="true">');
      for (const column of result.columns)
        parts.push(`<text class="flow-header" x="${f(column.x)}" y="14">${escape(String(column.label || '').toUpperCase())}</text>`);
      parts.push('</g>');
    }
    if (Array.isArray(options.legend) && options.legend.length) {
      parts.push(`<g class="flow-legend" aria-label="${escape(options.legendTitle || 'Colour')}">`);
      for (const item of options.legend) {
        parts.push(`<rect class="flow-legend-swatch" x="${f(item.x)}" y="${f(item.y - options.labelSize * 0.72)}" width="12" height="12"`
          + ` rx="2" fill="${item.colour}"/><text class="flow-legend-label" x="${f(item.x + 17)}" y="${f(item.y)}">${escape(item.label)}</text>`);
      }
      parts.push('</g>');
    }
    parts.push('<g class="flow-links">');
    result.links.forEach((link, index) => {
      const source = byId.get(link.source), target = byId.get(link.target);
      const stubbed = source.stub || target.stub;
      const fill = stubbed ? `url(#${prefix}-g-${index})` : ribbonFill(link, context, mode, index, prefix);
      // F12: money paid before the network's arrived is a line under the node, not a ribbon.
      if (target.stub === 'before_gate') return;
      const late = link.date_unverified ? ' flow-link--unverified' : '';
      parts.push(`<path class="flow-link${stubbed ? ' flow-link--stub' : ''}${late}" data-link="${escape(link.id)}"`
        + ` d="${link.path}" fill="${fill}" fill-opacity="${options.opacity}"/>`);
    });
    parts.push('</g><g class="flow-nodes">');
    const first = result.columns.flatMap(column => column.ids)[0];
    for (const node of result.nodes) {
      if (node.stub) continue;
      const colour = colours.get(node.id);
      const hatched = node.kind === 'balance' && ['unspent', 'kept', 'uncounted', 'untraced', 'unreported'].includes(node.balance);
      const height = Math.max(node.y1 - node.y0, 2);
      const label = nodeTitle(node);
      const aria = `${label}, ${format.full(node.value)}`;
      parts.push(`<g class="flow-node flow-node--${node.kind}${node.root ? ' flow-node--root' : ''}" data-node="${escape(node.id)}"`
        + ` tabindex="${node.id === first ? 0 : -1}" role="button" aria-label="${escape(aria)}">`);
      parts.push(`<rect class="flow-bar" x="${f(node.x0)}" y="${f(node.y0)}" width="${f(node.x1 - node.x0)}" height="${f(height)}"`
        + ` fill="${hatched ? `url(#${prefix}-hatch)` : colour}"${hatched ? ` stroke="${NEUTRAL}" stroke-width="1"` : ''}/>`);
      let x = node.x1 + 8;
      const y = node.label_y + Math.round(options.labelSize * 0.89);
      if (node.kind === 'candidate' && PARTY_RING[node.party]) {
        parts.push(`<circle class="flow-party" cx="${f(x + 5)}" cy="${f(y - 4)}" r="4.5" fill="none" stroke="${PARTY_RING[node.party]}"`
          + ' stroke-width="2"/>');
        x += 16;
      }
      const room = (node.label_width || 180) - (x - node.x1 - 8);
      const lines = node.label_text && node.label_text.length ? node.label_text : [node.label];
      lines.forEach((line, at) => parts.push(`<text class="flow-label" x="${f(x)}" y="${f(y + at * options.labelLine)}">`
        + `${escape(fit(line, room, options.labelSize))}</text>`));
      const below = y + lines.length * options.labelLine;
      // The Studio's Labels toggle takes the amounts off; a Label measure prints its own text.
      if (options.amounts !== false)
        parts.push(`<text class="flow-amount" x="${f(x)}" y="${f(below)}">`
          + `${escape(node.amount_text != null ? node.amount_text : format.short(node.amount ?? node.value))}</text>`);
      (node.sublines || []).forEach((line, at) =>
        parts.push(`<text class="flow-subline" x="${f(x)}" y="${f(below + options.labelLine + at * options.subLine)}">`
          + `${escape(fit(line, room, options.subSize))}</text>`));
      parts.push('</g>');
    }
    parts.push('</g></svg>');
    return parts.join('');
  }

  /* ---------------------------------------------------------------- tooltip */
  // Where a pooling committee's receipts came from, largest first (two at most): the reader is
  // told whose money is in the pool, never that a donor's dollars went to a candidate.
  function shares(node, cycle) {
    const list = (node.share_from_upstream || []).filter(item => item.share != null)
      .slice().sort((a, b) => b.share - a.share).slice(0, 2);
    if (!list.length) return 'pooled, not traced dollars';
    const [first, second] = list;
    return `${percent(first.share)} of its ${cycle} receipts came from ${first.label}`
      + (second ? `, ${percent(second.share)} from ${second.label}` : '') + ' · pooled, not traced dollars';
  }

  function describe(target, context, payload) {
    const {result} = context;
    const {short, full} = context.format || {short: module_short, full: module_full};
    const worksheet = payload.source === 'worksheet';
    const byId = new Map(result.nodes.map(node => [node.id, node]));
    const cycle = payload.cycle ? `${Number(payload.cycle) - 1}–${payload.cycle}` : '';
    const fec = url => (root.MentatScope && root.MentatScope.fecLink ? root.MentatScope.fecLink(url) : '');
    if (target.link) {
      const link = target.link;
      const source = byId.get(link.source), sink = byId.get(link.target);
      const route = (payload.routes || []).find(item => item.target === link.target && item.committee === link.committee
        && Math.round(item.value * 100) === link.cents);
      const path = route ? route.path.map(step => step.label) : [source.stub ? sink.label : source.label];
      const lines = [];
      const title = sink.kind === 'candidate'
        ? [...path, nodeTitle(sink)].join(' → ') + (sink.outcome ? '' : `, ${sink.direction}`)
        : `${source.label} → ${sink.label}`;
      const spender = link.committee ? (byId.get('committee:' + link.committee) || {}).label || source.label : source.label;
      lines.push(sink.kind === 'candidate' ? `${full(link.value)} spent by ${spender}` : full(link.value));
      const pooled = byId.get('committee:' + (link.committee || ''));
      if (pooled && pooled.pooled && (pooled.share_from_upstream || []).length) lines.push(shares(pooled, cycle));
      const column = result.columns[sink.stub ? source.stage : sink.stage];
      const rowWord = worksheet ? 'worksheet row' : 'filing';
      if (column && column.total) lines.push(`${percent(link.value / column.total)} of ${column.label || 'this stage'}`
        + (link.rows ? ` · ${link.rows.toLocaleString('en-US')} ${rowWord}${link.rows === 1 ? '' : 's'}` : ''));
      for (const line of link.details || []) lines.push(line);
      if (link.date_unverified) lines.push('Undated in the filing: counted, date not verified');
      if (source.stub && source.carryover) lines.push(`Carried over: ${source.carryover}`);
      const record = (link.evidence || []).find(item => fec(item.source_url));
      const url = record ? fec(record.source_url) : fec(link.evidence_url || '');
      return {title, lines, url, urlText: record ? 'FEC filing' : 'Committee on FEC'};
    }
    const node = target.node;
    const lines = [full(node.value)];
    const column = result.columns[node.stage];
    if (column && column.total && !node.stub) lines.push(`${percent(node.value / column.total)} of ${column.label || 'this stage'}`);
    if (node.pooled && (node.share_from_upstream || []).length) lines.push(shares(node, cycle));
    if (node.balance === 'unspent') lines.push(`cash on hand ${full(node.cash || 0)} at the end of the window`
      + ((node.held || 0) > 0 ? ` + ${heldWords(node.held_kinds)} ${full(node.held)} still held` : ''));
    if (node.bucket === 'other') lines.push(`${node.member_count} grouped: ` + (node.members || []).slice(0, 4)
      .map(member => `${member.label} ${short(member.value)}`).join(', ') + (node.member_count > 4 ? ', …' : ''));
    if (node.name_as_filed && node.name_as_filed !== node.label) lines.push(`As filed: ${node.name_as_filed}`);
    for (const line of node.details || []) lines.push(line);
    if (node.unreached) lines.push(`Not collected (${String(node.unreached).replace(/_/g, ' ')}); not traced past it`);
    // Carryover (b), in the measurement's words: the gate the previous cycle's transfers opened.
    if (node.carryover) {
      lines.push(`Counted from the start of the cycle: ${node.carryover.label}`);
      const by = node.carryover.opened_by || [];
      if (by.length) lines.push('Opened by ' + by.slice(0, 2).map(item => `${item.label} ${short(item.amount)}`
        + (item.first_date ? ` from ${item.first_date}` : '')).join(', ') + (by.length > 2 ? `, and ${by.length - 2} more` : ''));
    }
    return {title: nodeTitle(node), lines, url: fec(node.fec_url || ''), urlText: node.kind === 'candidate' ? 'Candidate on FEC' : 'Committee on FEC'};
  }

  /* ------------------------------------------------------------------ mount */
  let mounted = 0;
  function mount(host, payload, options) {
    mounted += 1;
    options = Object.assign({ribbons: 'gradient', opacity: 0.4, idPrefix: `flow${mounted}`}, options || {});
    const state = {payload, options, context: null, focus: null};
    const tip = host.ownerDocument.createElement('div');
    tip.className = 'flow-tooltip';
    tip.hidden = true;
    tip.setAttribute('role', 'status');

    function draw() {
      const width = options.width || Math.max(640, Math.floor(host.clientWidth || 1100));
      const height = options.height || Math.max(360, Math.floor(host.clientHeight || 520));
      const settings = Object.assign({}, state.options, {width, height});
      state.context = prepare(state.payload, settings);
      host.innerHTML = svgString(state.payload, settings);
      host.appendChild(tip);
    }

    const find = id => state.context.result.nodes.find(node => node.id === id);
    const findLink = id => state.context.result.links.find(link => link.id === id);

    function light(start) {
      const svg = host.querySelector('svg.flow-chart');
      if (!svg) return;
      if (!start) { svg.classList.remove('is-tracing'); for (const item of svg.querySelectorAll('.is-lit')) item.classList.remove('is-lit'); return; }
      const lit = layoutApi().route(state.context.result, start);
      svg.classList.add('is-tracing');
      for (const path of svg.querySelectorAll('.flow-link')) path.classList.toggle('is-lit', lit.links.has(path.dataset.link));
      for (const group of svg.querySelectorAll('.flow-node')) group.classList.toggle('is-lit', lit.nodes.has(group.dataset.node));
    }

    function show(target, anchor) {
      const text = describe(target, state.context, state.payload);
      tip.replaceChildren();
      const title = host.ownerDocument.createElement('strong');
      title.textContent = text.title;
      tip.appendChild(title);
      for (const line of text.lines) {
        const row = host.ownerDocument.createElement('span');
        row.textContent = line;
        tip.appendChild(row);
      }
      if (text.url) {
        const link = host.ownerDocument.createElement('a');
        link.href = text.url; link.target = '_blank'; link.rel = 'noopener noreferrer';
        link.textContent = `${text.urlText} ↗`;
        tip.appendChild(link);
      }
      tip.hidden = false;
      const box = host.getBoundingClientRect(), at = anchor.getBoundingClientRect();
      const left = Math.min(Math.max(8, at.left - box.left + at.width / 2 - 150), Math.max(8, box.width - 316));
      tip.style.left = `${Math.round(left)}px`;
      tip.style.top = `${Math.round(Math.max(4, at.top - box.top - 12))}px`;
      tip.style.transform = 'translateY(-100%)';
    }

    function hide() { tip.hidden = true; }

    function targetOf(element) {
      const group = element.closest('.flow-node');
      if (group) return {node: find(group.dataset.node), element: group};
      const path = element.closest('.flow-link');
      if (path) return {link: findLink(path.dataset.link), element: path};
      return null;
    }

    function activate(node) {
      if (!node) return;
      if (node.kind === 'committee' && !node.root && node.committee_id && options.onReroot) options.onReroot(node.committee_id, node);
      else if (node.kind === 'candidate' && options.onCandidate) options.onCandidate(node);
      else if (node.bucket === 'other' && options.onOther) options.onOther(node);
    }

    function move(node, key) {
      const result = state.context.result;
      const column = result.columns[node.stage];
      const at = column.ids.indexOf(node.id);
      let next = null;
      if (key === 'ArrowDown') next = column.ids[at + 1];
      if (key === 'ArrowUp') next = column.ids[at - 1];
      if (key === 'ArrowRight' || key === 'ArrowLeft') {
        const step = key === 'ArrowRight' ? 1 : -1;
        for (let index = node.stage + step; index >= 0 && index < result.columns.length && !next; index += step) {
          const ids = result.columns[index].ids;
          if (!ids.length) continue;
          const middle = (node.y0 + node.y1) / 2;
          next = ids.slice().sort((a, b) => Math.abs((find(a).y0 + find(a).y1) / 2 - middle)
            - Math.abs((find(b).y0 + find(b).y1) / 2 - middle))[0];
        }
      }
      if (!next) return;
      const group = host.querySelector(`.flow-node[data-node="${CSS.escape(next)}"]`);
      for (const item of host.querySelectorAll('.flow-node[tabindex="0"]')) item.setAttribute('tabindex', '-1');
      group.setAttribute('tabindex', '0');
      group.focus();
    }

    const over = event => {
      const target = targetOf(event.target);
      if (!target || (!target.node && !target.link)) return;
      light(target.node ? target.node.id : target.link.id);
      show(target, target.element);
    };
    const out = event => {
      if (event.relatedTarget && host.contains(event.relatedTarget) && targetOf(event.relatedTarget)) return;
      light(null); hide();
    };
    const click = event => {
      const target = targetOf(event.target);
      if (target && target.node) activate(target.node);
    };
    const key = event => {
      const target = targetOf(event.target);
      if (!target || !target.node) return;
      if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); activate(target.node); return; }
      if (event.key === 'Escape') { light(null); hide(); return; }
      if (event.key.startsWith('Arrow')) { event.preventDefault(); move(target.node, event.key); }
    };
    const focusIn = event => {
      const target = targetOf(event.target);
      if (target && target.node) { light(target.node.id); show(target, target.element); }
    };
    host.addEventListener('pointerover', over);
    host.addEventListener('pointerout', out);
    host.addEventListener('click', click);
    host.addEventListener('keydown', key);
    host.addEventListener('focusin', focusIn);
    host.addEventListener('focusout', event => { if (!host.contains(event.relatedTarget)) { light(null); hide(); } });
    draw();
    return {
      update(nextPayload, nextOptions) {
        if (nextPayload) state.payload = nextPayload;
        if (nextOptions) Object.assign(state.options, nextOptions);
        hide(); draw();
      },
      result: () => state.context.result,
      colours: () => state.context.colours,
      trace: light,
      describe: target => describe(target, state.context, state.payload),
      destroy() {
        host.removeEventListener('pointerover', over);
        host.removeEventListener('pointerout', out);
        host.removeEventListener('click', click);
        host.removeEventListener('keydown', key);
        host.removeEventListener('focusin', focusIn);
        host.replaceChildren();
      }
    };
  }

  const module_short = short, module_full = full;
  const api = {svgString, mount, describe, short, full, MODES};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.MentatFlowChart = api;
})(typeof globalThis === 'undefined' ? this : globalThis);
