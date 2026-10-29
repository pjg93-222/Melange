// Restored original Congress.gov design (Draft Systems\congress_member_scraper.R). Pure tests:
// R-generated fixtures (fec/tools/export_congress_search_urls.R), fake fetch, fake clock.
import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import {
  CLEARANCE_WAIT_MS,
  DEFAULT_WORKERS,
  HAND_SOLVE_TIMEOUT_MS,
  HandSolveTimeoutError,
  MAX_WORKERS_WITHOUT_PAUL_OK,
  PAGE_SIZE,
  applyRole,
  assembleTemplate,
  assertWorkerCount,
  awaitClearance,
  buildMemberUrl,
  constructDisplayName,
  D359_CDFI_FIX,
  D360_METADATA_FIELD,
  DISCOVERY_SOURCE_TAGS,
  instrumentFor,
  mergeWithPrior,
  readAfterNavigation,
  zeroYieldSections,
  createPoliteness,
  decayWeight,
  fetchWithReplay,
  isChallengeHtml,
  pageCheckpointPath,
  planMemberPasses,
  rosterFromCsv,
  validateSections,
  walkMemberPass,
} from "../lib/congress_member_scrape.mjs";
import { classifyChallenge } from "../lib/congress_cdp_browser.mjs";

const HERE = import.meta.dirname;
const SECTIONS = validateSections(JSON.parse(fs.readFileSync(path.join(HERE, "../collect/congress_member_search_sections.json"), "utf8")));
const R = JSON.parse(fs.readFileSync(path.join(HERE, "collect/fixtures/congress_member_r_urls.json"), "utf8"));
const DRAFT = "C:\\Users\\pgoff\\OneDrive\\Desktop\\Draft Systems\\congress_search_urls.R";
const sha = (s) => crypto.createHash("sha256").update(s, "utf8").digest("hex");

function clock() {
  const state = { t: 0, slept: [] };
  return { now: () => state.t, sleep: async (ms) => { state.slept.push(ms); state.t += ms; }, state };
}

// ---- URL and filter construction, exact against R ----------------------------------------

// D-360: the fixture holds URLs R built from today's (06-25, title-only) congress_search_urls.R.
// Undoing the D-360 field swap must give R's URL byte for byte, so the swap is the only difference.
const undoD360 = (template) => template.replaceAll(D360_METADATA_FIELD.to, D360_METADATA_FIELD.from);

test("every member/section/role/page URL of the 16 uncorrected sections matches R build_member_url + apply_role byte for byte, D-360 field swap aside", () => {
  assert.equal(R.urls.length, 17 * 3 * 3 * 2);
  for (const row of R.urls) {
    if (row.section === D359_CDFI_FIX.section) continue; // corrected by D-359; pinned below
    const section = SECTIONS.sections.find((s) => s.key === row.section);
    const url = buildMemberUrl(applyRole(undoD360(assembleTemplate(section.parts)), row.role), row.member, row.page);
    assert.equal(sha(url), row.sha256, `${row.section}/${row.role}/${row.member}/p${row.page}`);
    if (typeof row.url === "string") assert.equal(url, row.url);
  }
});

test("member encoding matches R URLencode(reserved=TRUE) for all 537 pinned roster names and edge cases", () => {
  assert.equal(R.encodings.length, 540);
  for (const row of R.encodings) assert.equal(buildMemberUrl("__MEMBER__", row.member, 1), row.encoded, row.member);
});

test("the sections file holds congress_search_urls.R's *_url_parts verbatim except the D-360 field revert: 16 identical, CDFI corrected only as D-359 rules", { skip: !fs.existsSync(DRAFT) && "Draft Systems not on this machine" }, () => {
  const source = fs.readFileSync(DRAFT, "utf8");
  let identical = 0;
  let swaps = 0;
  for (const section of SECTIONS.sections) {
    const start = source.indexOf(`${section.key}_url_parts <- c(`);
    assert.ok(start >= 0, section.key);
    const block = source.slice(start, source.indexOf("\n)", start));
    const rawParts = [...block.matchAll(/^\s*"([^"]*)",?\s*$/gm)].map((m) => m[1]);
    swaps += rawParts.join("").split(D360_METADATA_FIELD.from).length - 1;
    const parts = rawParts.map((p) => p.replaceAll(D360_METADATA_FIELD.from, D360_METADATA_FIELD.to));
    if (section.key !== D359_CDFI_FIX.section) {
      assert.deepEqual(section.parts, parts, section.key);
      identical += 1;
      continue;
    }
    // The original defect, still in the R file: no closing %5D and a "contains" member match.
    assert.ok(!parts.join("").endsWith("%5D") && parts.at(-1).includes(D359_CDFI_FIX.from));
    const corrected = [...parts.slice(0, -1), parts.at(-1).replace(D359_CDFI_FIX.from, D359_CDFI_FIX.to), D359_CDFI_FIX.appendedPart];
    assert.deepEqual(section.parts, corrected, "cdfi_fund differs from R only by the D-359 correction");
  }
  assert.equal(identical, 16);
  assert.equal(swaps, D360_METADATA_FIELD.swaps, "the R file still holds the 06-25 title-only conditions");
});

test("D-360: the 06-25 title-only edit is reverted; all 145 keyword conditions search metadata, nothing else changed", () => {
  // Provenance: congress_search_urls.R was written 2026-06-25 21:49, after the 06-24 16:29 baseline
  // checkpoint; the 06-10 backup searched these keywords in `metadata`. Paul's ruling D-360
  // ("1. Yeah accept the full run") accepted the metadata slice at 104.6% of R 06-24, time-adjusted.
  const count = (s, token) => s.split(token).length - 1;
  const perSection = Object.fromEntries(SECTIONS.sections.map((s) => [s.key, count(assembleTemplate(s.parts), D360_METADATA_FIELD.to)]));
  assert.deepEqual(perSection, {
    examination_supervision: 13, cu_capital_requirements: 8, ncua_budget_share_insurance: 8, interchange_status_quo: 0,
    payments: 4, technology_emerging: 7, fraud_prevention: 6, data_privacy_cybersecurity: 10, charter_modernization: 8,
    defense_credit_union: 6, field_of_membership: 9, cdfi_fund: 6, cfpb_reform: 16, credit_card_consumer_fee: 8,
    tcpa: 6, member_business_lending: 16, mortgage_lending_housing: 14,
  });
  assert.equal(Object.values(perSection).reduce((a, b) => a + b, 0), D360_METADATA_FIELD.swaps);
  for (const s of SECTIONS.sections) {
    const t = assembleTemplate(s.parts);
    assert.equal(count(t, D360_METADATA_FIELD.from), 0, `${s.key}: a title-only keyword condition survived`);
    assert.equal(count(t, "%22field%22%3A%22title%22"), 0, `${s.key}: no title-field condition of any kind`);
  }
  // The whole new set, pinned.
  assert.equal(sha(SECTIONS.sections.map((s) => `${s.key}\n${assembleTemplate(s.parts)}`).join("\n")),
    "5f498ca960eb7734f05f8c12ee8317c1385a6d77980615958e4a97e5870f4ac9");
});

test("D-359: the corrected CDFI URL is valid JSON with a sponsor 'phrase' switch and a closing bracket", () => {
  const section = SECTIONS.sections.find((s) => s.key === D359_CDFI_FIX.section);
  const template = assembleTemplate(section.parts);
  assert.equal(sha(template), "9e6073a92ee13164bce5da75e68c46c81daf1e87a3be8b4d3403502c4203ac44");
  assert.equal(sha(undoD360(template)), "cbeb670d1f72aa451d231596267554cf5cec84c76248caf467278b3b4479b3e2", "D-359 template before D-360");
  assert.ok(template.endsWith("%5D") && !template.includes("%22contains%22%2C%22value%22%3A%22__MEMBER__"));
  const decoded = JSON.parse(decodeURIComponent(buildMemberUrl(template, "Ann Wagner", 1).split("raw=")[1].split("&pageSize=")[0].replace(/\+/g, " ")));
  const switches = JSON.stringify(decoded).match(/"field":"sponsor","operator":"(\w+)","value":"Ann Wagner"/);
  assert.equal(switches?.[1], "phrase");
  for (const role of ["original-cosponsor", "cosponsor"]) assert.ok(applyRole(template, role).includes(`%22field%22%3A%22${role}%22%2C%22operator%22%3A%22phrase%22`));
});

test("16 of 17 sections carry the policy-area (subject) filter; Interchange has none", () => {
  const withSubject = SECTIONS.sections.filter((s) => assembleTemplate(s.parts).includes("%22field%22%3A%22subject%22"));
  assert.equal(withSubject.length, 16);
  assert.deepEqual(SECTIONS.sections.filter((s) => !withSubject.includes(s)).map((s) => s.key), ["interchange_status_quo"]);
  const payments = decodeURIComponent(assembleTemplate(SECTIONS.sections.find((s) => s.key === "payments").parts).split("raw=")[1].replace(/\+/g, " "));
  assert.match(payments, /"field":"subject","operator":"multi","value":\["Agriculture and Food","Commerce","Finance and Financial Sector"\]/);
});

test("roles swap the single sponsor token like R apply_role; plan order is section > role > member", () => {
  const base = assembleTemplate(SECTIONS.sections[0].parts);
  assert.equal(applyRole(base, "sponsor"), base);
  assert.ok(applyRole(base, "original-cosponsor").includes("%22field%22%3A%22original-cosponsor%22"));
  assert.throws(() => applyRole(base + base, "cosponsor"), /exactly ONE/);
  const plan = planMemberPasses(SECTIONS, ["A B", "C D"]);
  assert.equal(plan.length, 17 * 3 * 2);
  assert.deepEqual(plan.slice(0, 3).map((p) => [p.section, p.role, p.member]),
    [["examination_supervision", "sponsor", "A B"], ["examination_supervision", "sponsor", "C D"], ["examination_supervision", "original-cosponsor", "A B"]]);
  assert.equal(plan[0].category, "examination_supervision");
});

test("display names and decay weights match R construct_display_name / congress_decay_weight", () => {
  for (const row of R.display_names) assert.equal(constructDisplayName(row.full_name, row.first, row.last), row.display);
  for (const row of R.decay) assert.ok(Math.abs(decayWeight(row.congress) - row.weight) < 1e-12, String(row.congress)); // JSON keeps 15 digits
  const csv = 'last_name,first_name,full_name,type\nHill,French,"J. French Hill",rep\nBarr,Andy,Andy Barr,rep\nX,Y,"Y X",gov\n';
  assert.deepEqual(rosterFromCsv(csv), ["Andy Barr", "French Hill"]);
});

// ---- challenge -> hand-solve pause; timeout -> DEGRADED path --------------------------------

test("a challenge polls ~1 s through the 90 s automatic window, then pauses for a hand-solve with a console message and a toast", async () => {
  const c = clock();
  const logs = [];
  const toasts = [];
  const solvedAt = CLEARANCE_WAIT_MS + 45_000;
  const result = await awaitClearance({
    probe: async () => c.now() >= solvedAt, sleep: c.sleep, now: c.now,
    log: (m) => logs.push(m), notify: (t, b) => toasts.push([t, b]),
  });
  assert.equal(result.via, "human");
  assert.ok(c.state.slept.every((ms) => ms === 1_000));
  assert.equal(toasts.length, 1);
  assert.ok(logs.some((m) => m.includes("HAND-SOLVE")));
  assert.equal(toasts[0][0], "Melange: Congress.gov hand-solve needed");
});

test("an automatic clearance inside the window never asks for a human", async () => {
  const c = clock();
  const toasts = [];
  const result = await awaitClearance({ probe: async () => c.now() >= 3_000, sleep: c.sleep, now: c.now, notify: () => toasts.push(1), log: () => {} });
  assert.equal(result.via, "automatic");
  assert.equal(toasts.length, 0);
});

test("no human within the hand-solve timeout -> CONGRESS_AUTOMATIC_VERIFICATION_TIMEOUT (wrapper -> GovInfo, DEGRADED)", async () => {
  const c = clock();
  await assert.rejects(
    awaitClearance({ probe: async () => false, sleep: c.sleep, now: c.now, log: () => {}, observe: async () => ({ page_title: "Just a moment..." }) }),
    (error) => error instanceof HandSolveTimeoutError && error.code === "CONGRESS_AUTOMATIC_VERIFICATION_TIMEOUT"
      && error.classification.kind === "automatic_security_verification" && error.classification.page_title === "Just a moment..."
      && error.wait_ms === HAND_SOLVE_TIMEOUT_MS,
  );
  assert.ok(c.now() >= CLEARANCE_WAIT_MS + HAND_SOLVE_TIMEOUT_MS);
});

// ---- cookie replay: retries, backoff, challenge -------------------------------------------

const SESSION = { cookie: "cf_clearance=x", userAgent: "UA-from-the-visible-chrome" };
const reply = (status, text, headers = {}) => ({ status, url: "https://www.congress.gov/advanced-search?raw=x", text: async () => text, headers: new Headers(headers) });

test("'Failed to fetch' is retried per page with backoff and never thrown", async () => {
  const c = clock();
  let calls = 0;
  const ok = await fetchWithReplay({
    url: "u", session: SESSION, sleep: c.sleep, random: () => 0,
    fetchImpl: async (_, init) => { calls += 1; assert.equal(init.headers["User-Agent"], SESSION.userAgent); assert.equal(init.headers.Cookie, SESSION.cookie); if (calls < 3) throw new TypeError("Failed to fetch"); return reply(200, "<title>Results</title>"); },
  });
  assert.equal(ok.kind, "ok");
  assert.equal(ok.tries, 3);
  assert.deepEqual(c.state.slept, [3_000, 6_000]);
  const gap = await fetchWithReplay({ url: "u", session: SESSION, sleep: c.sleep, fetchImpl: async () => { throw new TypeError("fetch failed"); } });
  assert.equal(gap.kind, "error");
  assert.match(gap.error, /fetch failed/);
});

test("429 honours Retry-After, then backs off exponentially; outcomes feed the politeness controller", async () => {
  const c = clock();
  const outcomes = [];
  let calls = 0;
  const result = await fetchWithReplay({
    url: "u", session: SESSION, sleep: c.sleep, random: () => 0, onOutcome: (o) => outcomes.push(o),
    fetchImpl: async () => { calls += 1; return calls === 1 ? reply(429, "slow down", { "retry-after": "7" }) : calls === 2 ? reply(503, "busy") : reply(200, "ok"); },
  });
  assert.equal(result.kind, "ok");
  assert.deepEqual(c.state.slept, [7_000, 6_000]);
  assert.deepEqual(outcomes, ["rate_limited", "error", "ok"]);
});

test("a Cloudflare interstitial is a challenge (re-take the cookie), a normal page is not", async () => {
  const page = "<html><head><title>Just a moment...</title></head><body><form id='challenge-form'></form></body></html>";
  assert.equal(isChallengeHtml(page), true);
  assert.equal(isChallengeHtml("<title>Legislation Search Results | Congress.gov</title><script src='/cdn-cgi/challenge-platform/scripts/jsd/main.js'></script>"), false);
  const result = await fetchWithReplay({ url: "u", session: SESSION, fetchImpl: async () => reply(403, page) });
  assert.equal(result.kind, "challenge");
  assert.equal((await fetchWithReplay({ url: "u", session: null })).kind, "challenge");
});

test("error rate above 5% halves concurrency for a while, then it recovers", () => {
  const c = clock();
  const p = createPoliteness({ workers: 12, now: c.now });
  for (let i = 0; i < 18; i += 1) p.record("ok");
  p.record("rate_limited");
  p.record("error");
  assert.equal(p.activeWorkers, 6);
  assert.equal(p.halvings, 1);
  c.state.t += 60_001;
  assert.equal(p.activeWorkers, 12);
});

test("worker count: default 12, never above 16 without Paul's OK", () => {
  assert.equal(DEFAULT_WORKERS, 12);
  assert.equal(MAX_WORKERS_WITHOUT_PAUL_OK, 16);
  assert.equal(assertWorkerCount(16), 16);
  assert.throws(() => assertWorkerCount(17), /Paul's OK/);
  assert.throws(() => createPoliteness({ workers: 32 }), /Paul's OK/);
  assert.throws(() => assertWorkerCount(0));
});

// ---- per-page checkpoint / resume ---------------------------------------------------------

test("resume: checkpointed pages are reused, only missing pages are fetched; a changed URL is refetched", async () => {
  const pass = planMemberPasses(SECTIONS, ["Ann Wagner"])[0];
  const store = new Map();
  const full = (n) => Array.from({ length: n }, (_, i) => ({ result_url: `https://www.congress.gov/bill/119th-congress/house-bill/${i + 1}` }));
  store.set(pageCheckpointPath(pass, 1), { url: buildMemberUrl(pass.template, pass.member, 1), kind: "results", records: full(PAGE_SIZE), page: 1 });
  const fetched = [];
  const result = await walkMemberPass({
    pass,
    loadPage: async (file) => store.get(file) ?? null,
    savePage: async (file, page) => store.set(file, page),
    fetchPage: async (url, _, page) => { fetched.push(page); return { kind: "results", records: full(3) }; },
  });
  assert.deepEqual(fetched, [2]);
  assert.equal(result.pages.length, 2);
  assert.ok(store.has(pageCheckpointPath(pass, 2)));
  // A crash after page 2 resumes with zero fetches.
  const again = [];
  await walkMemberPass({ pass, loadPage: async (f) => store.get(f) ?? null, savePage: async () => {}, fetchPage: async (u, _, p) => { again.push(p); return { kind: "results", records: [] }; } });
  assert.deepEqual(again, []);
  // A checkpoint written for a different URL (template changed) is not trusted.
  store.set(pageCheckpointPath(pass, 1), { ...store.get(pageCheckpointPath(pass, 1)), url: "stale" });
  const refetch = [];
  await walkMemberPass({ pass, loadPage: async (f) => store.get(f) ?? null, savePage: async () => {}, fetchPage: async (u, _, p) => { refetch.push(p); return { kind: "results", records: [] }; } });
  assert.deepEqual(refetch, [1]);
});

test("a page that fails after retries is a gap row, the pass stops, nothing is thrown", async () => {
  const pass = planMemberPasses(SECTIONS, ["Ann Wagner"])[0];
  const result = await walkMemberPass({ pass, loadPage: async () => null, savePage: async () => {}, fetchPage: async () => ({ gap: { reason: "fetch_failed", tries: 3 } }) });
  assert.equal(result.gap.reason, "fetch_failed");
  assert.equal(result.gap.page, 1);
  assert.equal(result.pages.length, 0);
});

// ---- review fixes 2026-10-27 -------------------------------------------------------------------

test("instrumentFor: the exact primary only with zero gaps; any gap makes the string the weekly compares differ", () => {
  const primary = "Congress.gov Advanced Search - Legislation";
  assert.equal(instrumentFor(primary, 0), primary);
  assert.equal(instrumentFor(primary, 3), `${primary} (incomplete: 3 page(s) not collected)`);
  assert.notEqual(instrumentFor(primary, 1), primary);
});

test("zeroYieldSections names a section with no rows in any role, and only that one", () => {
  const q = (section_key, rows) => ({ section_key, rows_by_role: { sponsor: rows[0], "original-cosponsor": rows[1], cosponsor: rows[2] } });
  assert.deepEqual(zeroYieldSections([q("cdfi_fund", [0, 0, 0]), q("payments", [0, 0, 2]), q("tcpa", [1, 0, 0])]), ["cdfi_fund"]);
});

test("D-346 carry-forward: no prior row is dropped, overlaps merge categories and sources, new rows are tagged", () => {
  const rec = (key, extra = {}) => ({ canonical_key: key, title: `t ${key}`, matched_scoring_categories: [], matched_monitor_categories: [], matched_coverage_probes: [], ...extra });
  const prior = {
    manifest: { schema: "acu-govinfo-discovery-fallback-manifest-v1", primary_instrument: "GovInfo BILLSTATUS/BILLS official bulk fallback" },
    manifest_sha256: "x",
    records: [
      rec("117:hr:1", { matched_scoring_categories: ["payments"], matched_coverage_probes: ["probe_a"] }),
      rec("118:s:2", { fallback_discovery: { source: "govinfo" } }),
      rec("119:hr:3"),
    ],
    memberships: [{ query_id: "payments", canonical_key: "117:hr:1", record_kind: "query" }, { query_id: "fraud_prevention", canonical_key: "119:hr:3" }],
  };
  const walk = {
    records: [rec("117:hr:1", { title: "fresh", matched_scoring_categories: ["cfpb_issues_structural_reform"] }), rec("119:hr:9", { matched_scoring_categories: ["payments"] })],
    memberships: [{ query_id: "payments", canonical_key: "117:hr:1", section_key: "payments", member_roles: [{ member: "A" }] }, { query_id: "payments", canonical_key: "119:hr:9", section_key: "payments", member_roles: [] }],
  };
  const out = mergeWithPrior(walk, prior);
  const by = Object.fromEntries(out.records.map((r) => [r.canonical_key, r]));
  assert.deepEqual(Object.keys(by), ["117:hr:1", "118:s:2", "119:hr:3", "119:hr:9"]);
  assert.equal(by["117:hr:1"].title, "fresh");
  assert.deepEqual(by["117:hr:1"].matched_scoring_categories, ["cfpb_issues_structural_reform", "payments"]);
  assert.deepEqual(by["117:hr:1"].matched_coverage_probes, ["probe_a"]);
  assert.deepEqual(by["117:hr:1"].discovery_sources, [DISCOVERY_SOURCE_TAGS.categorySearch, DISCOVERY_SOURCE_TAGS.memberPages].sort());
  assert.deepEqual(by["118:s:2"].discovery_sources, [DISCOVERY_SOURCE_TAGS.govinfo]);
  assert.deepEqual(by["119:hr:3"].discovery_sources, [DISCOVERY_SOURCE_TAGS.categorySearch]);
  assert.deepEqual(by["119:hr:9"].discovery_sources, [DISCOVERY_SOURCE_TAGS.memberPages]);
  assert.equal(out.memberships.length, 3);
  const overlap = out.memberships.find((m) => m.query_id === "payments" && m.canonical_key === "117:hr:1");
  assert.equal(overlap.record_kind, "query");
  assert.deepEqual(overlap.member_roles, [{ member: "A" }]);
  assert.deepEqual(out.carried_forward, {
    prior_manifest_sha256: "x", prior_schema: prior.manifest.schema, prior_primary_instrument: prior.manifest.primary_instrument,
    prior_record_count: 3, prior_membership_count: 2, walk_record_count: 2, walk_records_already_known: 1,
    walk_records_new: 1, prior_records_not_found_by_walk: 2, rows_deleted: 0,
  });
  // member_roles is a union keyed on member|role: a member a later walk misses keeps its provenance.
  const later = mergeWithPrior(
    { records: [], memberships: [{ query_id: "payments", canonical_key: "117:hr:1", member_roles: [{ member: "B", role: "cosponsor" }] }] },
    { ...prior, records: out.records, memberships: out.memberships });
  assert.deepEqual(later.memberships.find((m) => m.canonical_key === "117:hr:1").member_roles.map((r) => r.member), ["A", "B"]);
  // A second walk over the merged union keeps the tags it already carries.
  const again = mergeWithPrior({ records: [], memberships: [] }, { ...prior, manifest: { collection_design: "member x section x role" }, records: out.records, memberships: out.memberships });
  assert.deepEqual(again.records, out.records);
});
test("readAfterNavigation: a read racing the post-clearance navigation is settled and retried; other errors are thrown", async () => {
  const c = clock();
  let settles = 0;
  const page = { waitForLoadState: async () => { settles += 1; } };
  let calls = 0;
  const ua = await readAfterNavigation(page, async () => {
    calls += 1;
    if (calls < 3) throw new Error("page.evaluate: Execution context was destroyed, most likely because of a navigation");
    return "Mozilla/5.0 (the visible Chrome)";
  }, { sleep: c.sleep });
  assert.equal(ua, "Mozilla/5.0 (the visible Chrome)");
  assert.equal(calls, 3);
  assert.equal(settles, 3);
  assert.deepEqual(c.state.slept, [1000, 2000]);
  // Playwright's page.content() reports the same race in its own words.
  let contentCalls = 0;
  const html = await readAfterNavigation(page, async () => {
    contentCalls += 1;
    if (contentCalls === 1) throw new Error("page.content: Unable to retrieve content because the page is navigating and changing the content.");
    return "<html>results</html>";
  }, { sleep: c.sleep });
  assert.equal(html, "<html>results</html>");
  await assert.rejects(readAfterNavigation(page, async () => { throw new Error("Target page, context or browser has been closed"); }, { sleep: c.sleep }), /has been closed/);
  let n = 0;
  await assert.rejects(readAfterNavigation(page, async () => { n += 1; throw new Error("Execution context was destroyed"); }, { tries: 3, sleep: c.sleep }), /Execution context was destroyed/);
  assert.equal(n, 3);
});
// ---- Paul 2026-10-27: automatic clearance, no click sign-in -----------------------------------

test("the automatic window is the R design's 90 s", () => {
  assert.equal(CLEARANCE_WAIT_MS, 90_000);
});

test("a NON-interactive check that clears by itself at ~33 s raises no banner and no toast", async () => {
  const c = clock();
  const logs = [];
  const toasts = [];
  const result = await awaitClearance({
    probe: async () => c.now() >= 33_000,
    classify: async () => classifyChallenge({ loadedUrl: "https://www.congress.gov/advanced-search", title: "Just a moment...",
      bodyText: "www.congress.gov Verifying you are human. This may take a few seconds." }),
    sleep: c.sleep, now: c.now, log: (m) => logs.push(m), notify: () => toasts.push(1),
  });
  assert.equal(result.via, "automatic");
  assert.equal(result.waited_ms, 33_000);
  assert.equal(toasts.length, 0);
  assert.ok(!logs.some((m) => m.includes("HAND-SOLVE")));
});

test("an INTERACTIVE widget escalates after 3 readings (~2 s) to the banner; nothing is clicked", async () => {
  const c = clock();
  const logs = [];
  const toasts = [];
  let probes = 0;
  const result = await awaitClearance({
    probe: async () => { probes += 1; return c.now() >= 120_000; },
    classify: async () => classifyChallenge({ loadedUrl: "https://www.congress.gov/advanced-search", title: "Just a moment...",
      bodyText: "www.congress.gov Verify you are human by completing the action below." }),
    sleep: c.sleep, now: c.now, log: (m) => logs.push(m), notify: (t) => toasts.push([t, c.now()]),
  });
  assert.equal(result.via, "human");
  assert.equal(result.escalation, "interactive");
  assert.equal(toasts.length, 1);
  assert.equal(toasts[0][1], 2_000, "after 3 consecutive interactive readings (~2 s), not after the 90 s window");
  assert.ok(logs.some((m) => m.includes("is interactive")));
});

test("a check that never clears within 90 s escalates on the timeout, never before", async () => {
  const c = clock();
  const toasts = [];
  const result = await awaitClearance({
    probe: async () => c.now() >= 100_000, classify: async () => "automatic",
    sleep: c.sleep, now: c.now, log: () => {}, notify: () => toasts.push(c.now()),
  });
  assert.equal(result.via, "human");
  assert.equal(result.escalation, "timeout");
  assert.equal(toasts[0], 90_000);
});
test("one transient interactive reading does not raise a banner; a throwing classify keeps polling", async () => {
  const c = clock();
  const toasts = [];
  let reads = 0;
  const result = await awaitClearance({
    probe: async () => c.now() >= 33_000,
    classify: async () => { reads += 1; if (reads === 2) return "interactive"; if (reads === 3) throw new Error("body detached"); return "automatic"; },
    sleep: c.sleep, now: c.now, log: () => {}, notify: () => toasts.push(1),
  });
  assert.equal(result.via, "automatic");
  assert.equal(toasts.length, 0);
});

test("a hand-solve timeout after an interactive escalation says so in its receipt (still DEGRADED via GovInfo)", async () => {
  const c = clock();
  await assert.rejects(
    awaitClearance({ probe: async () => false, classify: async () => "interactive", sleep: c.sleep, now: c.now, log: () => {} }),
    (error) => error instanceof HandSolveTimeoutError && error.code === "CONGRESS_AUTOMATIC_VERIFICATION_TIMEOUT"
      && error.classification.interactive === true && error.classification.escalation === "interactive",
  );
});