import assert from "node:assert/strict";
import test from "node:test";
import {
  buildSessionMeta,
  chromeSpawnArgs,
  classifyChallenge,
  classifyFetchPushback,
  clearanceNeedsRefresh,
  clearedProbeExpression,
  ensureChrome,
  isClearedSignal,
  waitForClearance,
} from "../lib/congress_cdp_browser.mjs";

const okResponse = { ok: true };

test("ensureChrome reuses a debugger that is already up and does not spawn", async () => {
  let spawned = 0;
  const result = await ensureChrome({
    port: 9333,
    profile: "P",
    chromePath: "chrome.exe",
    fetchImpl: async (url) => {
      assert.equal(url, "http://127.0.0.1:9333/json/version");
      return okResponse;
    },
    spawnImpl: () => {
      spawned += 1;
    },
  });
  assert.deepEqual(result, { endpoint: "http://127.0.0.1:9333", spawned: false });
  assert.equal(spawned, 0);
});

test("ensureChrome spawns detached with exactly the four plain flags, then waits for readiness", async () => {
  let probes = 0;
  const calls = [];
  const result = await ensureChrome({
    port: 9222,
    profile: "C:\\prof",
    chromePath: "C:\\chrome.exe",
    fetchImpl: async () => {
      probes += 1;
      if (probes < 4) throw new Error("ECONNREFUSED");
      return okResponse;
    },
    spawnImpl: (exe, args, options) => {
      calls.push({ exe, args, options });
      return { unref() {} };
    },
    sleep: async () => {},
  });
  assert.equal(result.spawned, true);
  assert.equal(calls.length, 1);
  assert.deepEqual(calls[0].args, [
    "--remote-debugging-port=9222",
    "--user-data-dir=C:\\prof",
    "--no-first-run",
    "--no-default-browser-check",
  ]);
  assert.equal(calls[0].options.detached, true);
  const joined = calls[0].args.join(" ");
  assert.doesNotMatch(joined, /automation|AutomationControlled|headless|user-agent|stealth/i);
  assert.deepEqual(chromeSpawnArgs(9222, "C:\\prof"), calls[0].args);
});

test("ensureChrome times out with an actionable error", async () => {
  let t = 0;
  await assert.rejects(
    ensureChrome({
      chromePath: "x",
      fetchImpl: async () => {
        throw new Error("down");
      },
      spawnImpl: () => ({ unref() {} }),
      now: () => t,
      sleep: async (ms) => {
        t += ms;
      },
      timeoutMs: 1000,
    }),
    /never came up/,
  );
});

test("cleared signal: any non-challenge congress.gov page passes (incl. the search form)", () => {
  const base = { title: "Search Results | Congress.gov", hasChallengeDom: false, hostname: "www.congress.gov" };
  assert.equal(isClearedSignal(base), true);
  // the advanced-search FORM has no results list and must still count as cleared
  assert.equal(
    isClearedSignal({ ...base, title: "Advanced Search - Legislation | Congress.gov | Library of Congress" }),
    true,
  );
  for (const title of ["Just a moment...", "Attention Required! | Cloudflare", "Security Check", "Verify you are human"]) {
    assert.equal(isClearedSignal({ ...base, title }), false, title);
  }
  assert.equal(isClearedSignal({ ...base, hasChallengeDom: true }), false);
  assert.equal(isClearedSignal({ ...base, hostname: "example.com" }), false);
  assert.equal(isClearedSignal({ ...base, hostname: "evilcongress.gov" }), false);
});

test("page probe expression embeds the same classifier and evaluates against a fake document", () => {
  const expression = clearedProbeExpression();
  const run = (doc, loc) => new Function("document", "location", `return ${expression}`)(doc, loc);
  const loc = { hostname: "www.congress.gov" };
  const form = {
    title: "Advanced Search - Legislation | Congress.gov | Library of Congress",
    querySelector: () => null,
  };
  assert.equal(run(form, loc), true);
  const challenge = {
    title: "Just a moment...",
    querySelector: (sel) => (sel.includes("#challenge-running") ? {} : null),
  };
  assert.equal(run(challenge, loc), false);
});

function fakeChallengePage({ title, bodyText }) {
  const state = { reloads: 0, waits: [] };
  return {
    state,
    waitForFunction: async (_probe, _arg, { timeout }) => {
      state.waits.push(timeout);
      const err = new Error("timeout");
      err.name = "TimeoutError";
      throw err;
    },
    reload: async () => {
      state.reloads += 1;
    },
    title: async () => title,
    url: () => "https://www.congress.gov/index.php/advanced-search/legislation",
    locator: () => ({ innerText: async () => bodyText }),
  };
}

test("waitForClearance: interactive challenge reloads once then waits for a human", async () => {
  const page = fakeChallengePage({ title: "Just a moment...", bodyText: "Please complete the CAPTCHA" });
  const logs = [];
  await assert.rejects(
    waitForClearance(page, { autoMs: 40, humanMs: 5000, log: (m) => logs.push(m) }),
    (error) => error.name === "CongressAutomaticVerificationTimeoutError",
  );
  assert.equal(page.state.reloads, 1);
  assert.deepEqual(page.state.waits, [20, 20, 5000]);
  assert.equal(logs.length, 1);
});

test("waitForClearance: automatic challenge reloads once and does not wait for a human", async () => {
  const page = fakeChallengePage({ title: "Just a moment...", bodyText: "Performing security verification" });
  await assert.rejects(waitForClearance(page, { autoMs: 40, humanMs: 5000, log: () => {} }));
  assert.equal(page.state.reloads, 1);
  assert.deepEqual(page.state.waits, [20, 20]);
});

test("classifyChallenge distinguishes automatic, interactive, and none", () => {
  const url = "https://www.congress.gov/index.php/advanced-search/legislation";
  assert.equal(
    classifyChallenge({
      loadedUrl: url,
      title: "Just a moment...",
      bodyText: "Performing security verification\nThis page is displayed while the website verifies you are not a bot.",
    }),
    "automatic",
  );
  assert.equal(
    classifyChallenge({ loadedUrl: url, title: "Just a moment...", bodyText: "Please complete the CAPTCHA" }),
    "interactive",
  );
  assert.equal(classifyChallenge({ loadedUrl: url, title: "Search Results", bodyText: "Search Results 1-250 of 900" }), "none");
});

test("classifyFetchPushback: status codes and challenge bodies", () => {
  assert.equal(classifyFetchPushback({ status: 429, text: "" }).kind, "rate_limit");
  assert.equal(classifyFetchPushback({ status: 503, text: "" }).kind, "rate_limit");
  assert.equal(classifyFetchPushback({ status: 403, text: "forbidden" }).kind, "rate_limit");
  assert.equal(classifyFetchPushback({ status: 403, text: "<title>Just a moment...</title>" }).kind, "challenge");
  assert.equal(classifyFetchPushback({ status: 200, text: "<title>Just a moment...</title>" }).kind, "challenge");
  assert.equal(classifyFetchPushback({ status: 200, text: "<title>Search Results</title><ol></ol>" }), null);
});

test("session metadata never contains the cookie value", () => {
  const now = Date.parse("2026-10-25T12:00:00Z");
  const meta = buildSessionMeta({
    cookies: [{ name: "cf_clearance", value: "SECRET-VALUE", expires: (now + 3_600_000) / 1000 }],
    userAgent: "Chrome/141",
    profile: "P",
    now,
  });
  assert.equal(JSON.stringify(meta).includes("SECRET-VALUE"), false);
  assert.equal(meta.measured_lifetime_ms, 3_600_000);
  assert.equal(meta.cf_clearance_expires, "2026-10-25T13:00:00.000Z");
  const session = buildSessionMeta({ cookies: [{ name: "cf_clearance", value: "v", expires: -1 }], now });
  assert.equal(session.cf_clearance_expires, null);
});

test("clearanceNeedsRefresh: margin, keep-warm, missing cookie", () => {
  const now = Date.parse("2026-10-25T12:00:00Z");
  const margin = 10 * 60_000;
  const meta = (expiresInMs, harvestedAgoMs = 0) => ({
    cf_clearance_present: true,
    cf_clearance_expires: new Date(now + expiresInMs).toISOString(),
    harvested_at: new Date(now - harvestedAgoMs).toISOString(),
  });
  assert.equal(clearanceNeedsRefresh(meta(3_600_000), now, margin), false);
  assert.equal(clearanceNeedsRefresh(meta(9 * 60_000), now, margin), true);
  assert.equal(clearanceNeedsRefresh(meta(3_600_000, 25 * 60_000), now, margin, { keepWarmMs: 20 * 60_000 }), true);
  assert.equal(
    clearanceNeedsRefresh(meta(3_600_000, 25 * 60_000), now, margin, { keepWarmMs: 20 * 60_000, lastRefreshAtMs: now - 5 * 60_000 }),
    false,
  );
  assert.equal(clearanceNeedsRefresh({ cf_clearance_present: false }, now, margin), true);
  assert.equal(clearanceNeedsRefresh(null, now, margin), true);
});
