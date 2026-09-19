/* The console's URL scope: the hash names the tab, the query string carries the
   scope. Pure except for `location` and `history`, so node:test can drive it
   with a fake pair. Contract: audits/mentat_failings_20260915/contracts/url_scope.json.

   Tab switches stay on history.replaceState (Paul's ruling C, 2026-09-17).
   pushState is never used here: Back does not step through tabs today and S5
   does not change that. */
(function (root) {
  'use strict';

  // Every key this module owns, in the order it serializes them. A scope built
  // from nothing writes its keys in this order; a scope merged into a live
  // query leaves the keys already there where they are.
  // S6's pane model (D-039). Up to four PAC evidence panes, each addressed by
  // a PREFIXED key so `cycle` can go on belonging to Graph and "whose cycle is
  // this?" stays answerable: `a.source` is the kind of source (an import or a
  // saved snapshot), `a.id` the import id or the snapshot directory name,
  // `a.committee` the FEC committee, `a.cycle` its cycle. A fifth prefix is not
  // a key this module knows, so `e.id` is preserved in the query and never read
  // as scope - the same treatment the retired studioPane gets (v4, 2026-09-19:
  // the N charts strip that wrote it is gone, and nothing reads it now).
  const PANES = ['a', 'b', 'c', 'd'];
  // S8 adds `map`: the direction of the district map open on that pane
  // ('raised' or 'spent'). Absent means the pane grid is showing, so an
  // ordinary permalink is unchanged and a map permalink reopens the map.
  const PANE_FIELDS = ['source', 'id', 'committee', 'cycle', 'map'];
  const PANE_KEYS = [];
  for (let pane = 0; pane < PANES.length; pane += 1) {
    for (let field = 0; field < PANE_FIELDS.length; field += 1) {
      PANE_KEYS.push(PANES[pane] + '.' + PANE_FIELDS[field]);
    }
  }
  const PANE_SOURCES = ['csv', 'snapshot'];
  const PANE_ID = /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/;
  const PANE_COMMITTEE = /^(unassigned|[A-Za-z0-9][A-Za-z0-9-]{0,31})$/;
  const PANE_MAP = ['raised', 'spent'];
  const KEYS = ['industry', 'company', 'cycle', 'mode', 'direction', 'tier',
    'funding', 'category', 'recipient', 'saved'].concat(PANE_KEYS);
  // The #graph-mode option values, verbatim (index.html:105).
  const MODES = ['direct', 'activity', 'estimates'];
  // S6's pane model owns these. S5 never writes one and never removes one.
  const RESERVED = ['evidence', 'id', 'committee', 'offset', 'limit'];

  const CYCLE_REASON = 'cycle must be a four-digit election-cycle end year';
  const PANE_SOURCE_REASON = 'a pane source must be one of ' + PANE_SOURCES.join(', ');
  const PANE_ID_REASON = 'a pane id must be an import id or a saved-snapshot directory name';
  const PANE_COMMITTEE_REASON = 'a pane committee must be a committee id or "unassigned"';
  const PANE_MAP_REASON = 'a pane map must be one of ' + PANE_MAP.join(', ');
  const MODE_REASON = 'mode must be one of ' + MODES.join(', ');
  const SAVED_REASON = 'saved must be a 32-character hexadecimal saved-view id';
  const BLANK_REASON = 'a blank value names no scope, so the key is dropped';

  // A bad permalink still has to open its tab, so nothing in here throws: an
  // unusable value is dropped from the scope and reported through invalid[].
  function check(key, raw) {
    const text = raw == null ? '' : String(raw);
    if (!text) return {ok: false, value: text, reason: BLANK_REASON};
    const dot = key.indexOf('.');
    if (dot > 0) {
      const field = key.slice(dot + 1);
      if (field === 'source' && PANE_SOURCES.indexOf(text) < 0) return {ok: false, value: text, reason: PANE_SOURCE_REASON};
      if (field === 'id' && !PANE_ID.test(text)) return {ok: false, value: text, reason: PANE_ID_REASON};
      if (field === 'committee' && !PANE_COMMITTEE.test(text)) return {ok: false, value: text, reason: PANE_COMMITTEE_REASON};
      if (field === 'cycle' && !/^\d{4}$/.test(text)) return {ok: false, value: text, reason: CYCLE_REASON};
      if (field === 'map' && PANE_MAP.indexOf(text) < 0) return {ok: false, value: text, reason: PANE_MAP_REASON};
      return {ok: true, value: text};
    }
    if (key === 'cycle' && !/^\d{4}$/.test(text)) return {ok: false, value: text, reason: CYCLE_REASON};
    if (key === 'mode' && MODES.indexOf(text) < 0) return {ok: false, value: text, reason: MODE_REASON};
    // The same rule server.py get_view() enforces, so the client never fires a
    // saved-view request the console will answer 400 for.
    if (key === 'saved' && !/^[a-f0-9]{32}$/.test(text)) return {ok: false, value: text, reason: SAVED_REASON};
    return {ok: true, value: text};
  }

  function entries(search) {
    const text = String(search == null ? '' : search).replace(/^[?]/, '');
    // URLSearchParams decodes both %20 and '+', keeps duplicates, keeps order,
    // and never throws on a malformed escape.
    return text ? [...new URLSearchParams(text)] : [];
  }

  /* --------------------------------------------------------------- reading */

  function parse(search) {
    const scope = {invalid: []};
    const seen = Object.create(null);
    for (const [key, value] of entries(search)) {
      if (KEYS.indexOf(key) < 0 || seen[key]) continue;
      seen[key] = true;
      const checked = check(key, value);
      if (checked.ok) scope[key] = checked.value;
      else scope.invalid.push({key: key, value: checked.value, reason: checked.reason});
    }
    return scope;
  }

  function read(search) {
    if (search !== undefined) return parse(search);
    const here = typeof location === 'undefined' ? null : location;
    return parse(here ? here.search : '');
  }

  /* --------------------------------------------------------------- writing */

  // Values are encodeURIComponent'd, keys are written plain. URLSearchParams
  // .toString() would spell a space as '+', and a published label such as
  // "Property & Casualty Insurance" has to survive a copied permalink.
  const encode = value => encodeURIComponent(String(value == null ? '' : value));

  function serialize(scope) {
    const source = scope || {};
    const parts = [];
    for (const key of KEYS) {
      if (!Object.prototype.hasOwnProperty.call(source, key)) continue;
      const checked = check(key, source[key]);
      if (checked.ok) parts.push(key + '=' + encode(checked.value));
    }
    return parts.join('&');
  }

  // Merge a partial scope into a live query string. An empty, null or
  // undefined value removes its key; a value this module would refuse to read
  // back removes it too, so the URL can never carry something read() rejects.
  // Every other key in the query - the retired studioPane, S6's reserved keys,
  // anything a future session adds - is preserved untouched and keeps its place.
  function merge(search, partial) {
    const pairs = entries(search);
    const changes = partial || {};
    for (const key of Object.keys(changes)) {
      if (KEYS.indexOf(key) < 0) continue;
      const checked = check(key, changes[key]);
      const at = pairs.findIndex(pair => pair[0] === key);
      if (!checked.ok) {
        for (let i = pairs.length - 1; i >= 0; i -= 1) if (pairs[i][0] === key) pairs.splice(i, 1);
        continue;
      }
      if (at < 0) pairs.push([key, checked.value]);
      else {
        pairs[at] = [key, checked.value];
        for (let i = pairs.length - 1; i > at; i -= 1) if (pairs[i][0] === key) pairs.splice(i, 1);
      }
    }
    return pairs.map(pair => pair[0] + '=' + encode(pair[1])).join('&');
  }

  function notify(scope, options) {
    const opts = options || {};
    if (typeof opts.dispatch === 'function') { opts.dispatch(scope); return; }
    const target = opts.target || root;
    if (!target || typeof target.dispatchEvent !== 'function' || typeof CustomEvent !== 'function') return;
    target.dispatchEvent(new CustomEvent('mentat:scope', {detail: scope}));
  }

  function write(partial, options) {
    const opts = options || {};
    const here = opts.location || (typeof location === 'undefined' ? null : location);
    const past = opts.history || (typeof history === 'undefined' ? null : history);
    if (!here) return read();
    const before = String(here.search || '').replace(/^[?]/, '');
    const after = merge(before, partial);
    if (after === before || !past || typeof past.replaceState !== 'function') return parse(after);
    const url = (here.pathname || '/') + (after ? '?' + after : '') + (here.hash || '');
    // A document with an opaque origin (a page built by setContent, a sandboxed
    // frame) refuses replaceState. Nothing changed, so nothing is announced.
    try { past.replaceState(null, '', url); } catch (error) { return parse(before); }
    const scope = parse(after);
    notify(scope, opts);
    return scope;
  }

  // The permalink for a view and a scope. Used by "Open in Chart Studio" and
  // available to S6 for pane links.
  function href(view, scope, base) {
    const here = base === undefined ? (typeof location === 'undefined' ? null : location) : base;
    const path = (here && here.pathname) || '/';
    const query = serialize(scope);
    return path + (query ? '?' + query : '') + (view ? '#' + String(view) : '');
  }

  function subscribe(fn, target) {
    const host = target || root;
    if (typeof fn !== 'function' || !host || typeof host.addEventListener !== 'function') {
      return function () {};
    }
    const onScope = event => fn(event && event.detail ? event.detail : read());
    const onPop = () => fn(read());
    host.addEventListener('mentat:scope', onScope);
    host.addEventListener('popstate', onPop);
    return function () {
      host.removeEventListener('mentat:scope', onScope);
      host.removeEventListener('popstate', onPop);
    };
  }

  const api = {KEYS, MODES, RESERVED, PANES, PANE_FIELDS, PANE_KEYS, PANE_SOURCES,
    read, write, parse, serialize, href, subscribe};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.MentatScope = api;
})(typeof globalThis === 'undefined' ? this : globalThis);
