import assert from "node:assert/strict";
import test from "node:test";
import { createGovernor } from "../lib/congress_governor.mjs";
import { PushbackError, governedAttempt, runPool } from "../lib/congress_page_queue.mjs";

function fakeClock() {
  const state = { t: 0, slept: [] };
  return {
    now: () => state.t,
    sleep: async (ms) => {
      state.slept.push(ms);
      state.t += ms;
    },
    state,
  };
}

test("429 triggers the 10 s pause, halves workers, then the retry succeeds", async () => {
  const c = fakeClock();
  const g = createGovernor({ maxWorkers: 8, maxRps: 1000, now: c.now });
  let calls = 0;
  const result = await governedAttempt({
    governor: g,
    sleep: c.sleep,
    request: async () => {
      calls += 1;
      if (calls === 1) throw new PushbackError("rate_limit", { status: 429 });
      return "html";
    },
  });
  assert.equal(result.ok, true);
  assert.equal(result.attempts, 2);
  assert.equal(g.activeWorkers, 4);
  assert.ok(c.state.slept.some((ms) => ms >= 10_000 - 5), `slept ${c.state.slept}`);
});

test("challenge pushback re-runs clearance before resuming", async () => {
  const c = fakeClock();
  const g = createGovernor({ maxWorkers: 2, maxRps: 1000, now: c.now });
  const order = [];
  let calls = 0;
  await governedAttempt({
    governor: g,
    sleep: c.sleep,
    onChallenge: async () => order.push("clearance"),
    request: async () => {
      order.push("request");
      if (++calls === 1) throw new PushbackError("challenge", { status: 403 });
      return "ok";
    },
  });
  assert.deepEqual(order, ["request", "clearance", "request"]);
});

test("retries cap at 3 and return a gap instead of throwing", async () => {
  const c = fakeClock();
  const g = createGovernor({ maxWorkers: 4, maxRps: 1000, now: c.now });
  let calls = 0;
  const result = await governedAttempt({
    governor: g,
    sleep: c.sleep,
    request: async () => {
      calls += 1;
      throw new PushbackError("rate_limit", { status: 503 });
    },
  });
  assert.equal(calls, 3);
  assert.equal(result.ok, false);
  assert.equal(result.error.status, 503);
});

test("non-pushback errors propagate (validation failures stay fatal)", async () => {
  const g = createGovernor({ maxRps: 1000 });
  await assert.rejects(
    governedAttempt({ governor: g, request: async () => { throw new Error("parse"); } }),
    /parse/,
  );
});

test("pool skips resumed items and never exceeds active workers", async () => {
  const g = createGovernor({ maxWorkers: 3, maxRps: 1000 });
  const done = new Set([2, 4]);
  let inFlight = 0;
  let peak = 0;
  const ran = [];
  const results = await runPool({
    items: [1, 2, 3, 4, 5, 6, 7],
    governor: g,
    isDone: (item) => done.has(item),
    run: async (item, slot) => {
      inFlight += 1;
      peak = Math.max(peak, inFlight);
      ran.push(item);
      assert.ok(slot >= 0 && slot < 3);
      await new Promise((resolve) => setImmediate(resolve));
      inFlight -= 1;
      return item * 10;
    },
  });
  assert.deepEqual(ran.sort(), [1, 3, 5, 6, 7]);
  assert.ok(peak <= 3);
  assert.deepEqual(results.map((r) => r.status), ["ok", "resumed", "ok", "resumed", "ok", "ok", "ok"]);
});

test("pool narrows to the halved worker cap after a pushback", async () => {
  const c = fakeClock();
  const g = createGovernor({ maxWorkers: 4, maxRps: 1000, now: c.now });
  g.onPushback(); // 4 -> 2
  let inFlight = 0;
  let peak = 0;
  await runPool({
    items: [1, 2, 3, 4, 5, 6],
    governor: g,
    run: async () => {
      inFlight += 1;
      peak = Math.max(peak, inFlight);
      await new Promise((resolve) => setImmediate(resolve));
      inFlight -= 1;
    },
  });
  assert.equal(peak, 2);
});

test("pool rejects and stops dispatching on a fatal error", async () => {
  const g = createGovernor({ maxWorkers: 1, maxRps: 1000 });
  const ran = [];
  await assert.rejects(
    runPool({
      items: [1, 2, 3],
      governor: g,
      run: async (item) => {
        ran.push(item);
        if (item === 2) throw new Error("boom");
      },
    }),
    /boom/,
  );
  assert.deepEqual(ran, [1, 2]);
});

test("a transient 'Failed to fetch' is retried and, if it persists, is a gap result, never a thrown error", async () => {
  const c = fakeClock();
  const g = createGovernor({ maxWorkers: 4, maxRps: 1000, now: c.now });
  let calls = 0;
  const recovered = await governedAttempt({
    governor: g, sleep: c.sleep, transportBackoffMs: 10,
    request: async () => { calls += 1; if (calls === 1) throw new TypeError("page.evaluate: TypeError: Failed to fetch"); return "html"; },
  });
  assert.equal(recovered.ok, true);
  assert.equal(recovered.attempts, 2);
  const exhausted = await governedAttempt({
    governor: g, sleep: c.sleep, transportBackoffMs: 10,
    request: async () => { throw new TypeError("Failed to fetch"); },
  });
  assert.equal(exhausted.ok, false);
  assert.match(exhausted.error.message, /Failed to fetch/);
  await assert.rejects(governedAttempt({ governor: g, sleep: c.sleep, request: async () => { throw new RangeError("a real bug"); } }), /a real bug/);
});
