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
  const KEYS = ['industry', 'company', 'cycle', 'mode', 'direction', 'tier',
    'funding', 'category', 'recipient', 'saved'];
  // The #graph-mode option values, verbatim (index.html:105).
  const MODES = ['direct', 'activity', 'estimates'];
  // S6's pane model owns these. S5 never writes one and never removes one.
  const RESERVED = ['evidence', 'id', 'committee', 'offset', 'limit'];

  const CYCLE_REASON = 'cycle must be a four-digit election-cycle end year';
  const MODE_REASON = 'mode must be one of ' + MODES.join(', ');
  const SAVED_REASON = 'saved must be a 32-character hexadecimal saved-view id';
  const BLANK_REASON = 'a blank value names no scope, so the key is dropped';

  // A bad permalink still has to open its tab, so nothing in here throws: an
  // unusable value is dropped from the scope and reported through invalid[].
  function check(key, raw) {
    const text = raw == null ? '' : String(raw);
    if (!text) return {ok: false, value: text, reason: BLANK_REASON};
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
  // Every other key in the query - studioPane, S6's reserved keys, anything a
  // future session adds - is preserved untouched and keeps its place.
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

  const api = {KEYS, MODES, RESERVED, read, write, parse, serialize, href, subscribe};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.MentatScope = api;
})(typeof globalThis === 'undefined' ? this : globalThis);
