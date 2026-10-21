// D-157 F-18 (R9): re-clicking the selected member deselects it; a different member still selects.
// Runs the dashboard template's real rowSelect, canvas-click and touchend handlers in a vm with stubbed
// selectMember/backToTargets. No page, no data, no server.
// A touch tap is handled in touchend, which preventDefaults it so the browser synthesizes no click (no timing guard).
const test = require('node:test'), assert = require('node:assert/strict');
const fs = require('node:fs'), vm = require('node:vm'), path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../../surfaces/templates/make_dashboard_html_00.tpl'), 'utf8');

function braced(name) {
  const start = source.indexOf('function ' + name + '(');
  assert.ok(start >= 0, name + ' missing');
  let depth = 0;
  for (let i = source.indexOf('{', start); i < source.length; i++) {
    if (source[i] === '{') depth++;
    else if (source[i] === '}' && --depth === 0) return source.slice(start, i + 1);
  }
  throw new Error('unbalanced ' + name);
}
const line = (re) => { const m = source.match(re); assert.ok(m, String(re)); return m[0]; };

function harness() {
  const listeners = {}, passive = {}, calls = [];
  const ctx = vm.createContext({
    calls, listeners, N: 2, LX: [0, 100], LY: [0, 0],
    cv: { addEventListener: (type, fn, opts) => { listeners[type] = fn; passive[type] = opts && opts.passive; } },
    window: { innerWidth: 1200, getSelection: () => '' },
    document: { getElementById: () => null }, setTimeout: () => 0,
    tierHidden: () => false, toScreen: (x, y) => [x, y], radOf: () => 5,
  });
  vm.runInContext(`let sel=-1,hi=-1,panMoved=false,tdrag=null,pinch=null;
    function selectMember(v){sel=v;calls.push('select '+v);}
    function backToTargets(){sel=-1;hi=-1;calls.push('back');}
    ${braced('rowSelect')}
    ${line(/^cv\.addEventListener\('click'.*$/m)}
    ${line(/^cv\.addEventListener\('touchend'.*$/m)}`, ctx);
  const get = (n) => vm.runInContext(n, ctx), set = (code) => vm.runInContext(code, ctx);
  const touchend = (e) => { let prevented = 0; listeners.touchend({ touches: [], ...e, preventDefault: () => { prevented++; } }); return prevented; };
  return { calls, listeners, passive, get, set, touchend,
    row: (i, e = { target: { closest: () => null } }) => vm.runInContext('rowSelect', ctx)(e, { dataset: { i: String(i) } }),
    click: () => listeners.click(), tap: (x) => { set(`tdrag={x:${x},y:0};panMoved=false`); return touchend(); } };
}

test('a row click selects another member and deselects the already-selected one', () => {
  const h = harness();
  h.row(0); assert.equal(h.get('sel'), 0);
  h.row(1); assert.equal(h.get('sel'), 1);
  h.row(1); assert.equal(h.get('sel'), -1);
  assert.deepEqual(h.calls, ['select 0', 'select 1', 'back']);
  h.row(0); assert.equal(h.get('sel'), 0, 'selecting again after a toggle-off works');
});

test('a row click on the profile anchor or over selected text never toggles', () => {
  const h = harness();
  h.row(0);
  h.row(0, { target: { closest: () => ({}) } });
  assert.equal(h.get('sel'), 0);
  h.set("window.getSelection=()=>'some words'"); h.row(0);
  assert.equal(h.get('sel'), 0);
});

test('a canvas click on the selected node deselects; another node selects; blank clears', () => {
  const h = harness();
  h.set('hi=0'); h.click(); assert.equal(h.get('sel'), 0);
  h.set('hi=1'); h.click(); assert.equal(h.get('sel'), 1);
  h.set('hi=1'); h.click(); assert.equal(h.get('sel'), -1);
  h.set('hi=0'); h.click(); assert.equal(h.get('sel'), 0);
  h.set('hi=-1'); h.click(); assert.equal(h.get('sel'), -1);
  h.set('hi=0'); h.click();
  h.set('panMoved=true;hi=0'); h.click(); assert.equal(h.get('sel'), 0, 'a drag-pan is not a click');
});

test('a touch tap selects and prevents the synthesized click; a second tap deselects; blank space clears', () => {
  const h = harness();
  assert.equal(h.tap(0), 1, 'a handled tap preventDefaults touchend'); assert.equal(h.get('sel'), 0);
  assert.equal(h.tap(0), 1); assert.equal(h.get('sel'), -1, 'tapping the selected node again deselects it');
  assert.equal(h.tap(100), 1); assert.equal(h.get('sel'), 1);
  assert.equal(h.tap(500), 1); assert.equal(h.get('sel'), -1, 'a tap on blank space clears');
});

test('touchend that is not a tap never preventDefaults, and is registered non-passive so it can', () => {
  const h = harness();
  assert.equal(h.passive.touchend, false, 'touchend needs {passive:false} for preventDefault to count');
  h.set('tdrag={x:0,y:0};panMoved=true'); assert.equal(h.touchend(), 0, 'a drag-pan');
  h.set('tdrag=null;panMoved=false'); assert.equal(h.touchend(), 0, 'no touch in progress (e.g. after a pinch)');
  h.set('tdrag={x:0,y:0};panMoved=false'); assert.equal(h.touchend({ touches: [{}] }), 0, 'a finger is still down');
  assert.deepEqual(h.calls, []);
  assert.ok(source.includes("cv.addEventListener('touchmove',e=>{e.preventDefault();"), 'touchmove still blocks page scroll while panning');
});

test('the canvas click toggles with no timing guard: it deselects at once after a tap, and lastTap is gone', () => {
  const h = harness();
  h.tap(0); assert.equal(h.get('sel'), 0);
  h.set('hi=0'); h.click(); assert.equal(h.get('sel'), -1, 'no time window swallows a click');
  assert.ok(!/lastTap/.test(source), 'the lastTap timestamp guard is gone');
  assert.ok(!/Date\.now\(\)-/.test(line(/^cv\.addEventListener\('click'.*$/m)), 'the click handler reads no clock');
});
