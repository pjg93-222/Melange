import assert from "node:assert/strict";
import test from "node:test";
import { createGovernor } from "../lib/congress_governor.mjs";

function clock(start = 1_000_000) {
  const state = { t: start };
  return { now: () => state.t, advance: (ms) => (state.t += ms), state };
}

test("aggregate rps ceiling: sustained reservations are spaced at 1/maxRps", () => {
  const c = clock();
  const g = createGovernor({ maxRps: 2, maxWorkers: 4, now: c.now });
  const waits = Array.from({ length: 6 }, () => g.reserve());
  // burst of 2 allowed, then one slot every 500 ms
  assert.deepEqual(waits, [0, 0, 500, 1000, 1500, 2000]);
});

test("min interval floors the spacing even below the rps ceiling", () => {
  const c = clock();
  const g = createGovernor({ maxRps: 100, minIntervalMs: 300, now: c.now });
  assert.equal(g.reserve(), 0);
  assert.equal(g.reserve(), 300);
});

test("pushback pauses 10 s, halves workers (min 1), and is one event per pause window", () => {
  const c = clock();
  const g = createGovernor({ maxWorkers: 12, now: c.now });
  assert.equal(g.onPushback(), true);
  assert.equal(g.activeWorkers, 6);
  assert.equal(g.pauseRemaining(), 10_000);
  // eleven concurrent failures inside the same pause do not halve again
  for (let i = 0; i < 11; i += 1) assert.equal(g.onPushback(), false);
  assert.equal(g.activeWorkers, 6);
  assert.ok(g.reserve() >= 10_000);
  c.advance(10_001);
  assert.equal(g.pauseRemaining(), 0);
  g.onPushback();
  assert.equal(g.activeWorkers, 3);
  c.advance(10_001);
  g.onPushback();
  c.advance(10_001);
  g.onPushback();
  c.advance(10_001);
  g.onPushback();
  assert.equal(g.activeWorkers, 1);
});

test("recovery adds one worker per 40 clean responses, capped at max, reset by pushback", () => {
  const c = clock();
  const g = createGovernor({ maxWorkers: 4, now: c.now });
  g.onPushback();
  assert.equal(g.activeWorkers, 2);
  for (let i = 0; i < 39; i += 1) g.onSuccess();
  assert.equal(g.activeWorkers, 2);
  g.onSuccess();
  assert.equal(g.activeWorkers, 3);
  for (let i = 0; i < 39; i += 1) g.onSuccess();
  c.advance(10_001);
  g.onPushback(); // streak reset, halve 3 -> 1
  assert.equal(g.activeWorkers, 1);
  for (let i = 0; i < 400; i += 1) g.onSuccess();
  assert.equal(g.activeWorkers, 4);
});
