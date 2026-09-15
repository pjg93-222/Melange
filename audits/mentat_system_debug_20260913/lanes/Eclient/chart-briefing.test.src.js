/* The briefing tray's model: order and the cap, with no document in sight.
   Run: node --test mentat/app/tests */
const test = require('node:test');
const assert = require('node:assert');
const model = require('../chart-briefing.js');

const chart = id => ({id, title: 'Chart ' + id, provenance: 'sha-' + id});
const ids = items => items.map(item => item.id);
const filled = n => Array.from({length: n}, (unused, i) => chart('c' + i))
  .reduce((items, item) => model.add(items, item), []);

test('the tray keeps charts in the order they were added', () => {
  const items = filled(3);
  assert.deepStrictEqual(ids(items), ['c0', 'c1', 'c2']);
});

test('adding returns a new list, so an export already running keeps its own order', () => {
  const first = filled(2);
  const second = model.add(first, chart('c2'));
  assert.notStrictEqual(first, second);
  assert.deepStrictEqual(ids(first), ['c0', 'c1']);
  assert.deepStrictEqual(ids(second), ['c0', 'c1', 'c2']);
});

test('move walks a chart exactly one place in the direction asked', () => {
  const items = filled(3);
  assert.deepStrictEqual(ids(model.move(items, 'c2', -1)), ['c0', 'c2', 'c1']);
  assert.deepStrictEqual(ids(model.move(items, 'c0', 1)), ['c1', 'c0', 'c2']);
});

test('move off either end changes nothing at all, rather than wrapping round', () => {
  const items = filled(3);
  assert.strictEqual(model.move(items, 'c0', -1), items);
  assert.strictEqual(model.move(items, 'c2', 1), items);
  assert.strictEqual(model.move(items, 'missing', -1), items);
  assert.deepStrictEqual(ids(items), ['c0', 'c1', 'c2']);
});

test('remove takes out exactly the named chart and leaves the rest in order', () => {
  const items = filled(4);
  assert.deepStrictEqual(ids(model.remove(items, 'c1')), ['c0', 'c2', 'c3']);
  assert.deepStrictEqual(ids(model.remove(items, 'missing')), ['c0', 'c1', 'c2', 'c3']);
  assert.deepStrictEqual(ids(items), ['c0', 'c1', 'c2', 'c3']);
});

test('the tray holds forty charts and refuses the forty-first rather than dropping the first', () => {
  const items = filled(model.CAP);
  assert.strictEqual(items.length, 40);
  assert.strictEqual(model.CAP, 40);
  assert.throws(() => model.add(items, chart('over')), /holds 40 charts/);
  assert.strictEqual(items[0].id, 'c0', 'the oldest chart must still be there after the refusal');
});

test('a chart removed from a full tray makes room for exactly one more', () => {
  const items = model.remove(filled(model.CAP), 'c0');
  assert.strictEqual(items.length, 39);
  const refilled = model.add(items, chart('fresh'));
  assert.strictEqual(refilled.length, 40);
  assert.strictEqual(refilled.at(-1).id, 'fresh');
  assert.throws(() => model.add(refilled, chart('over')), /Remove one before adding another/);
});
