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
 * source colour blends into the target colour. Default opacity 40%; the PAC evidence and
 * Graph views rest at VIEW_OPACITY, 28% (boards #44/#45, lane F2a FL2). Colours come only
 * from MentatTheme.categorical. Pooled money is never coloured by an original donor: a
 * ribbon takes the colour of the committee it leaves (or its outcome), never a donor's.
 *
 * Labels (lane F2a): beside the bars, 12-13 px, no halo; each node's label is drawn at the
 * level of detail the layout chose (flow-layout.js), cut at a word with an ellipsis and an
 * amount kept whole; every word the drawing leaves out is in the tooltip and the node's
 * accessible name. The tooltip is compact and sits by the hovered point, flipping so it
 * never covers the column headers or the title above the drawing.
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
  const VIEW_OPACITY = 0.28;
  const HEADER_SIZE = 11, HEADER_SPACING = 0.14;     // flow.css .flow-header: 11px, letter-spacing .14em
  const ELLIPSIS = '…';
  const MONEY_TAIL = /\s(\$[\d.,]+[MK]?)$/;

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

  // Text fitted to the room before the next column (MentatTheme.fitText in the page); the
  // suffix is kept whole (an amount).
  function fitter(options) {
    const theme = root.MentatTheme;
    if (options.fit) return options.fit;
    if (theme && typeof theme.fitText === 'function')
      return (text, width, size, suffix) => theme.fitText(text, width, size, undefined, suffix);
    return (text, width, size, suffix) => {
      const tail = suffix == null ? '' : String(suffix);
      const room = Math.floor(width / (size * 0.56)) - tail.length;
      return String(text).length <= room ? String(text) + tail
        : String(text).slice(0, Math.max(1, room - 1)).trimEnd() + ELLIPSIS + tail;
    };
  }

  // A text's width in px (MentatTheme.measureText in the page, else the fitter's estimate).
  function measurer(options) {
    const theme = root.MentatTheme;
    if (options.measure) return options.measure;
    if (theme && typeof theme.measureText === 'function') return (text, size) => theme.measureText(text, size);
    return (text, size) => String(text).length * size * 0.56;
  }

  // One line fitted to its room, cut between words with an ellipsis (FL3); a trailing amount
  // ("Other donors $85.2M") is kept whole, and only a single word too long for the room is cut
  // inside it, by the fitter, still with an ellipsis.
  function fitLine(text, room, size, fit, measure) {
    const value = String(text == null ? '' : text);
    if (measure(value, size) <= room) return value;
    const money = MONEY_TAIL.exec(value);
    const head = money ? value.slice(0, money.index) : value;
    const tail = money ? ' ' + money[1] : '';
    const words = head.split(' ');
    for (let count = words.length - 1; count >= 1; count -= 1) {
      const shown = words.slice(0, count).join(' ').replace(/[\s,\u00b7:;(]+$/, '') + ELLIPSIS + tail;
      if (measure(shown, size) <= room) return shown;
    }
    return fit(head, room, size, tail);
  }

  // A column header in the room before the next column, cut between words (its letter-spacing
  // counted); the full words go in a <title>.
  function fitHeader(text, room, fit, measure) {
    const width = value => measure(value, HEADER_SIZE) + HEADER_SPACING * HEADER_SIZE * value.length;
    if (width(text) <= room) return text;
    const words = text.split(' ');
    for (let count = words.length - 1; count >= 1; count -= 1) {
      const shown = words.slice(0, count).join(' ') + ELLIPSIS;
      if (width(shown) <= room) return shown;
    }
    return fit(text, room / (1 + HEADER_SPACING / 0.56), HEADER_SIZE);
  }

  function nodeTitle(node) {
    if (node.kind !== 'candidate' || node.outcome) return node.label;
    const where = [node.party, node.state].filter(Boolean).join('-');
    return where ? `${node.label} (${where})` : node.label;
  }

  function prepare(payload, options) {
    const api = layoutApi();
    // The layout wraps names between words with the page's measured widths (FL3).
    if (!options.measure) options = Object.assign({}, options, {measure: measurer(options)});
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
      labelSize: 13, subSize: 11.5, labelLine: 16, subLine: 14, amounts: true}, options || {});
    const mode = MODES.includes(options.ribbons) ? options.ribbons : 'gradient';
    const prefix = String(options.idPrefix || 'flow').replace(/[^A-Za-z0-9_-]/g, '');
    const context = prepare(payload, options);
    const {result, colours, format} = context;
    const fit = fitter(options);
    const measure = measurer(options);
    const byId = new Map(result.nodes.map(node => [node.id, node]));
    const labels = nodeMarkup(result, options, {colours, format, fit, measure, prefix});
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
      result.columns.forEach((column, at) => {
        const words = String(column.label || '').toUpperCase();
        const next = result.columns[at + 1];
        const shown = fitHeader(words, (next ? next.x : result.width - 8) - column.x - 12, fit, measure);
        const text = `<text class="flow-header" x="${f(column.x)}" y="14">${escape(shown)}</text>`;
        parts.push(shown === words ? text : `<g class="flow-header-cut"><title>${escape(words)}</title>${text}</g>`);
      });
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
    // Labels are drawn over the translucent ribbons as they are, with no halo and no knocked-out
    // box behind them (boards #44 and #46; a knock-out read as a halo in the round-1 captures).
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
    parts.push(...labels.parts);
    parts.push('</g></svg>');
    return parts.join('');
  }

  // Each node's bar and label, the label at the level of detail the layout chose.
  function nodeMarkup(result, options, tools) {
    const {colours, format, fit, measure, prefix} = tools;
    const amountSize = options.amountSize || 12;
    const parts = [];
    const first = result.columns.flatMap(column => column.ids)[0];
    for (const node of result.nodes) {
      if (node.stub) continue;
      const colour = colours.get(node.id);
      const hatched = node.kind === 'balance' && ['unspent', 'kept', 'uncounted', 'untraced', 'unreported'].includes(node.balance);
      const height = Math.max(node.y1 - node.y0, 2);
      const label = nodeTitle(node);
      // The accessible name says everything the label may leave to the tooltip (FL6).
      const said = (node.sublines || []).length ? `; ${node.sublines.join('; ')}` : '';
      const aria = `${label}, ${format.full(node.value)}${said}`;
      parts.push(`<g class="flow-node flow-node--${node.kind}${node.root ? ' flow-node--root' : ''}" data-node="${escape(node.id)}"`
        + ` tabindex="${node.id === first ? 0 : -1}" role="button" aria-label="${escape(aria)}">`);
      parts.push(`<rect class="flow-bar" x="${f(node.x0)}" y="${f(node.y0)}" width="${f(node.x1 - node.x0)}" height="${f(height)}"`
        + ` fill="${hatched ? `url(#${prefix}-hatch)` : colour}"${hatched ? ` stroke="${NEUTRAL}" stroke-width="1"` : ''}/>`);
      const lines = Array.isArray(node.label_text) ? node.label_text : [node.label];
      if (node.label_level !== 4 && lines.length) {
        // Beside the bar: to its right, or (the Studio's first column, #46) to its left, right-aligned.
        const left = node.label_side === 'left';
        const anchor = left ? ' text-anchor="end"' : '';
        let x = left ? node.x0 - 8 : node.x1 + 8;
        const y = node.label_y + Math.round(options.labelSize * 0.89);
        if (!left && node.kind === 'candidate' && PARTY_RING[node.party]) {
          parts.push(`<circle class="flow-party" cx="${f(x + 5)}" cy="${f(y - 4)}" r="4.5" fill="none" stroke="${PARTY_RING[node.party]}"`
            + ' stroke-width="2"/>');
          x += 16;
        }
        const room = (node.label_width || 180) - (left ? 0 : x - node.x1 - 8);
        // The Studio's Labels toggle takes the amounts off; a Label measure prints its own text.
        const amount = options.amounts === false ? ''
          : node.amount_text != null ? String(node.amount_text) : format.short(node.amount ?? node.value);
        const inline = node.label_amount === 'inline' && amount;
        lines.forEach((line, at) => {
          const last = at === lines.length - 1;
          if (inline && last) {
            // One line: the name, then its amount beside it.
            const beside = measure(amount, amountSize) + 6;
            const shown = fitLine(line, room - beside, options.labelSize, fit, measure);
            parts.push(`<text class="flow-label" x="${f(x)}" y="${f(y + at * options.labelLine)}"${anchor}>`
              + `${escape(shown)}<tspan class="flow-amount" dx="6">${escape(amount)}</tspan></text>`);
          } else {
            const shown = fitLine(line, room, options.labelSize, fit, measure);
            parts.push(`<text class="flow-label" x="${f(x)}" y="${f(y + at * options.labelLine)}"${anchor}>${escape(shown)}</text>`);
          }
        });
        let below = y + lines.length * options.labelLine;
        if (amount && node.label_amount === 'line') {
          parts.push(`<text class="flow-amount" x="${f(x)}" y="${f(below)}"${anchor}>${escape(amount)}</text>`);
          below += options.subLine;
        } else below += options.subLine - options.labelLine;
        // At most one short line under the label (FL6); the rest is in the tooltip.
        if (node.subline_shown) {
          const shown = fitLine(node.subline_shown, room, options.subSize, fit, measure);
          parts.push(`<text class="flow-subline" x="${f(x)}" y="${f(below)}"${anchor}>${escape(shown)}</text>`);
        }
      }
      parts.push('</g>');
    }
    return {parts};
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
    // The lines the drawing leaves off (FL6: one line under a label at most): here, every one.
    for (const line of node.sublines || []) if (line !== node.subline_shown) lines.push(line);
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

    // FL5: the tooltip sits by the hovered point (by a focused node's bar), above it when there
    // is room below the column headers, else below it; right of it, else left. It never reaches
    // up over the headers, and the title and subtitle sit above the drawing.
    function place(anchor, point) {
      const box = host.getBoundingClientRect();
      const scrollX = host.scrollLeft || 0, scrollY = host.scrollTop || 0;
      let x, y, below;
      if (point) { x = point.x - box.left; y = point.y - box.top; below = 14; }
      else {
        const bar = (anchor.querySelector && anchor.querySelector('.flow-bar')) || anchor;
        const at = bar.getBoundingClientRect();
        x = at.right - box.left; y = at.top - box.top + Math.min(at.height / 2, 14); below = Math.max(at.height / 2, 8) + 6;
      }
      const svg = host.querySelector('svg.flow-chart');
      const bands = svg ? [...svg.querySelectorAll('.flow-header, .flow-legend-label, .flow-legend-swatch')] : [];
      const floor = Math.max(4, ...bands.map(item => item.getBoundingClientRect().bottom - box.top + 6));
      const width = tip.offsetWidth, height = tip.offsetHeight;
      const room = host.clientWidth || box.width;
      const bottom = Math.max(host.clientHeight || box.height, floor + height);
      let top = y - 12 - height;
      if (top < floor) top = y + below;
      if (top + height > bottom - 4 && y - 12 - height >= floor) top = y - 12 - height;
      let left = x + 14;
      if (left + width > room - 4) left = x - 14 - width;
      left = Math.max(4, Math.min(left, room - width - 4));
      tip.style.transform = 'none';
      tip.style.left = `${Math.round(left + scrollX)}px`;
      tip.style.top = `${Math.round(Math.max(floor, top) + scrollY)}px`;
    }

    function show(target, anchor, point) {
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
      place(anchor, point);
    }

    function hide() { tip.hidden = true; state.shown = null; }

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
      const id = target.node ? target.node.id : target.link.id;
      // Moving between a node's bar and its words keeps the tooltip where it is.
      if (state.shown === id && !tip.hidden) return;
      light(id);
      // By the pointer, for a ribbon or a node alike (keyboard focus places it by the bar).
      show(target, target.element, Number.isFinite(event.clientX) ? {x: event.clientX, y: event.clientY} : null);
      state.shown = id;
    };
    // Moving onto the tooltip keeps it (its FEC link can be clicked); leaving it for the page hides it.
    const out = event => {
      const next = event.relatedTarget;
      if (next && host.contains(next) && (targetOf(next) || tip.contains(next))) return;
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

  /* ------------------------------------------------------------- the foot */
  // FL7: the notes under a Flow as the boards set them, one grey line, with a Details
  // disclosure that lists every note in full (F2, F4, F12, pooled money, crypto counted once:
  // none is dropped). The line ends with an ellipsis where it runs out of room.
  let footSerial = 0;
  function footnote(host, notes) {
    const doc = host.ownerDocument;
    const texts = (notes || []).map(note => (typeof note === 'string' ? note : (note && note.text) || '')).filter(Boolean);
    host.replaceChildren();
    if (!texts.length) return {line: null, toggle: null, list: null};
    footSerial += 1;
    const line = doc.createElement('p');
    line.className = 'flow-foot-line';
    line.textContent = texts.join(' · ');
    const list = doc.createElement('ul');
    list.className = 'flow-foot-list';
    list.id = `flow-foot-list-${footSerial}`;
    list.hidden = true;
    for (const text of texts) {
      const item = doc.createElement('li');
      item.textContent = text;
      list.appendChild(item);
    }
    const toggle = doc.createElement('button');
    toggle.type = 'button';
    toggle.className = 'flow-foot-toggle';
    toggle.textContent = 'Details';
    toggle.setAttribute('aria-expanded', 'false');
    toggle.setAttribute('aria-controls', list.id);
    toggle.addEventListener('click', () => {
      const open = list.hidden;
      list.hidden = !open;
      toggle.setAttribute('aria-expanded', String(open));
      toggle.textContent = open ? 'Hide details' : 'Details';
    });
    host.append(line, toggle, list);
    // One short note that fits needs no disclosure; anything more is listed under Details.
    toggle.hidden = texts.length < 2 && !(line.scrollWidth > line.clientWidth + 1);
    return {line, toggle, list};
  }

  // FL10: a Flow heading on one line: its stylesheet size, stepped down to 20 px while it
  // overflows, then cut with an ellipsis and the full words in its title. The size is set
  // through the CSSOM (the console's CSP refuses a style attribute).
  // Whether a one-line heading's words are wider than its box, to the subpixel (scrollWidth is
  // rounded, and an overflow of half a pixel is enough for the ellipsis to show).
  function overflows(element) {
    const doc = element.ownerDocument;
    if (doc && typeof doc.createRange === 'function') {
      const range = doc.createRange();
      range.selectNodeContents(element);
      const style = getComputedStyle(element);
      const room = element.clientWidth - (parseFloat(style.paddingLeft) || 0) - (parseFloat(style.paddingRight) || 0);
      return range.getBoundingClientRect().width > room - 0.5;
    }
    return element.scrollWidth > element.clientWidth;
  }

  function fitHeading(element, least) {
    if (!element || typeof getComputedStyle !== 'function') return;
    element.style.fontSize = '';
    element.removeAttribute('title');
    if (!element.clientWidth) return;
    let size = parseFloat(getComputedStyle(element).fontSize) || 26;
    const floor = least || 20;
    while (overflows(element) && size > floor) {
      size -= 1;
      element.style.fontSize = `${size}px`;
    }
    if (overflows(element)) element.title = element.textContent;
    // Measured before the serif face arrived, the fit is done again once it has (a heading fitted
    // in the fallback face overflowed in the real one: round-1 capture, Democrats Serve).
    const fonts = element.ownerDocument && element.ownerDocument.fonts;
    if (fonts && fonts.status !== 'loaded' && !element.__flowFitPending) {
      element.__flowFitPending = true;
      fonts.ready.then(() => { element.__flowFitPending = false; fitHeading(element, least); });
    }
  }

  const module_short = short, module_full = full;
  const api = {svgString, mount, describe, short, full, footnote, fitHeading, fitLine, MODES, VIEW_OPACITY};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.MentatFlowChart = api;
})(typeof globalThis === 'undefined' ? this : globalThis);
