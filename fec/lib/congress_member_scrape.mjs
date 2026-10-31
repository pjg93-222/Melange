// Paul's original Congress.gov discovery design (Draft Systems\congress_member_scraper.R),
// ported for the pipeline collector. Pure logic, no browser and no files, so every rule is
// testable with injected fetch / sleep / clock.
//
//   * 17 sections (congress_search_urls.R, verbatim) x 3 roles x every current member,
//     one advanced-search result page of 250 per request (R :728-743, :777-790).
//   * A visible, real Chrome clears Cloudflare; parallel workers replay its clearance cookie
//     and user agent (R :346-389, :409-468). A challenged round re-takes the cookie from the
//     browser (R :1328-1331).
//   * Paul 2026-10-27: "Restore original, but ramp up the number of collectors, keep the
//     handsolve, vastly reduce the cloudflare wait, and keep the cookie replay".
//
// Intentionally NOT ported: R apply_stealth (congress_member_scraper.R:283-298), which hid
// navigator.webdriver and faked window.chrome/languages/plugins. No automation-signal hiding,
// no user-agent invention or rotation, no proxy rotation. The only user agent sent is the one
// the visible Chrome itself reports, together with that Chrome's own cookie (the replay Paul kept).

export const DEFAULT_WORKERS = 12;            // R had 6 (HTTP_WORKERS, :311)
export const MAX_WORKERS_WITHOUT_PAUL_OK = 16; // brief: never above 16 without Paul's OK
// Automatic clearance window, as the original R design (90 s). Paul 2026-10-27: "I don't want the
// click sign-in, that needs to be handled automatically, and we can't sacrifice speed". Overnight
// Cloudflare's NON-interactive "Just a moment..." check cleared by itself in about 33 s; the old 10 s
// window escalated to the hand-solve banner before it could finish. One wait per clearance; cookie
// replay keeps the workers at full speed afterwards.
export const CLEARANCE_WAIT_MS = 90_000;
// Consecutive "interactive" readings (one per ~1 s poll) before the banner is raised early.
export const INTERACTIVE_READINGS = 3;
export const CLEARANCE_POLL_MS = 1_000;
export const HAND_SOLVE_TIMEOUT_MS = 20 * 60_000;
export const PAGE_SIZE = 250;
export const MAX_PAGES_PER_MEMBER = 20;       // R max_pages_per_member (:1175)
export const MAX_TRIES = 3;                   // R HTTP_MAX_TRIES (:319)
export const RETRY_BASE_MS = 3_000;           // R HTTP_RETRY_BASE_S (:320)
export const RETRY_CAP_MS = 60_000;
export const REQUEST_TIMEOUT_MS = 45_000;     // R HTTP_TIMEOUT_S (:318)
export const PAUSE_RANGE_MS = [300, 1_200];   // R HTTP_PAUSE (:312)
export const CHALLENGE_ROUNDS = 3;            // R max_rounds (:1319)
export const MAX_FALLBACK_PAGES_PER_PASS = 40; // R MAX_CHALLENGED_BEFORE_ABORT (:331)
export const ERROR_RATE_LIMIT = 0.05;
export const ERROR_WINDOW = 100;
export const ERROR_MIN_SAMPLES = 20;
export const HALVE_HOLD_MS = 60_000;
export const NEWEST_CONGRESS = 119;           // R :107-114
export const DECAY_PER_CONGRESS = 0.8;
export const MEMBER_PLACEHOLDER = "__MEMBER__";

// R section key -> acu_legislation_search_registry.json category id (same outline sections).
export const SECTION_TO_CATEGORY = Object.freeze({
  examination_supervision: "examination_supervision",
  cu_capital_requirements: "credit_union_capital_requirements",
  ncua_budget_share_insurance: "ncua_budget_share_insurance",
  interchange_status_quo: "interchange",
  payments: "payments",
  technology_emerging: "technology_emerging_issues",
  fraud_prevention: "fraud_prevention",
  data_privacy_cybersecurity: "data_privacy_cybersecurity",
  charter_modernization: "charter_modernization_governance",
  defense_credit_union: "defense_credit_union_issues",
  field_of_membership: "field_of_membership",
  cdfi_fund: "cdfi_fund",
  cfpb_reform: "cfpb_issues_structural_reform",
  credit_card_consumer_fee: "credit_card_consumer_fee_mandates",
  tcpa: "telephone_consumer_protection_act",
  member_business_lending: "member_business_lending",
  mortgage_lending_housing: "mortgage_lending_housing",
});

// D-359 (Paul 2026-10-27, "Fix it"): a deliberate departure from congress_search_urls.R (D-360 below is the other).
// The original cdfi_fund template lacked its closing "%5D" (its decoded query was not valid JSON)
// and matched the member with "contains" instead of "phrase"; R's 06-24 run returned 0 CDFI rows
// for all 537 members. congress_member_search_sections.json carries the corrected template; the
// other 16 sections stay byte-identical to the R file.
export const D359_CDFI_FIX = Object.freeze({
  section: "cdfi_fund",
  from: "%22operator%22%3A%22contains%22%2C%22value%22%3A%22__MEMBER__%22",
  to: "%22operator%22%3A%22phrase%22%2C%22value%22%3A%22__MEMBER__%22",
  appendedPart: "%5D",
});

// D-360 (Paul 2026-10-27, "1. Yeah accept the full run"): revert the 2026-06-25 edit of
// congress_search_urls.R (written 06-25 21:49, after the 06-24 baseline run), which switched every
// keyword condition from `metadata` to `title`. The sections file searches the keywords in
// `metadata` again, as the 06-24 run did: 145 conditions in 16 sections (Interchange has none).
// Nothing else differs (values, phrase conditions, policy areas, congress range, member, roles).
export const D360_METADATA_FIELD = Object.freeze({
  from: "%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22",
  to: "%22field%22%3A%22metadata%22%2C%22operator%22%3A%22containsAll%22",
  swaps: 145,
});

// Per-record provenance in the carried-forward union (D-346 interim default).
export const DISCOVERY_SOURCE_TAGS = Object.freeze({
  memberPages: "congress_gov_member_pages",
  categorySearch: "congress_gov_category_search",
  govinfo: "govinfo_bulk_fallback",
});

// D-346 interim default: the walk's union merged into the verified union already in --out. Nothing
// is dropped: prior rows are kept (tagged), rows the walk found again take the fresh fields and the
// union of categories and sources, and new rows are tagged as member-page finds.
export function mergeWithPrior(walk, prior) {
  const design = String(prior.manifest.collection_design ?? "");
  const priorTag = (row) => row.discovery_sources
    ?? [row.fallback_discovery ? DISCOVERY_SOURCE_TAGS.govinfo
      : design.startsWith("member x section") ? DISCOVERY_SOURCE_TAGS.memberPages : DISCOVERY_SOURCE_TAGS.categorySearch];
  const sortedUnion = (a, b) => [...new Set([...(a ?? []), ...(b ?? [])])].sort();
  const records = new Map(prior.records.map((row) => [row.canonical_key, { ...row, discovery_sources: priorTag(row) }]));
  const carriedKeys = new Set(records.keys());
  for (const row of walk.records) {
    const old = records.get(row.canonical_key);
    records.set(row.canonical_key, old ? {
      ...old, ...row,
      matched_scoring_categories: sortedUnion(old.matched_scoring_categories, row.matched_scoring_categories),
      matched_monitor_categories: sortedUnion(old.matched_monitor_categories, row.matched_monitor_categories),
      matched_coverage_probes: sortedUnion(old.matched_coverage_probes, row.matched_coverage_probes),
      discovery_sources: sortedUnion(old.discovery_sources, [DISCOVERY_SOURCE_TAGS.memberPages]),
    } : { ...row, discovery_sources: [DISCOVERY_SOURCE_TAGS.memberPages] });
  }
  const memberships = new Map(prior.memberships.map((m) => [`${m.query_id}\u0000${m.canonical_key}`, m]));
  for (const m of walk.memberships) {
    const id = `${m.query_id}\u0000${m.canonical_key}`;
    const old = memberships.get(id) ?? {};
    // member_roles is a union keyed on member|role: a member the later walk misses keeps its provenance.
    const roles = new Map([...(old.member_roles ?? []), ...(m.member_roles ?? [])].map((r) => [`${r.member}|${r.role}`, r]));
    const merged = { ...old, ...m };
    if (old.member_roles || m.member_roles) {
      merged.member_roles = [...roles.values()].sort((a, b) => `${a.member}|${a.role}`.localeCompare(`${b.member}|${b.role}`));
    }
    memberships.set(id, merged);
  }
  const byKey = (a, b) => a.localeCompare(b, undefined, { numeric: true });
  const walkKeys = new Set(walk.records.map((r) => r.canonical_key));
  const out = {
    records: [...records.values()].sort((a, b) => byKey(a.canonical_key, b.canonical_key)),
    memberships: [...memberships.values()].sort((a, b) => byKey(`${a.query_id}:${a.canonical_key}`, `${b.query_id}:${b.canonical_key}`)),
  };
  if (out.records.length < prior.records.length || out.memberships.length < prior.memberships.length) throw new Error("carry-forward lost rows");
  out.carried_forward = {
    prior_manifest_sha256: prior.manifest_sha256,
    prior_schema: prior.manifest.schema ?? null,
    prior_primary_instrument: prior.manifest.primary_instrument ?? null,
    prior_record_count: prior.records.length,
    prior_membership_count: prior.memberships.length,
    walk_record_count: walk.records.length,
    walk_records_already_known: [...walkKeys].filter((k) => carriedKeys.has(k)).length,
    walk_records_new: [...walkKeys].filter((k) => !carriedKeys.has(k)).length,
    prior_records_not_found_by_walk: [...carriedKeys].filter((k) => !walkKeys.has(k)).length,
    rows_deleted: 0,
  };
  return out;
}

// A tab that just passed a Cloudflare check (automatically or by a hand-solve) navigates on to the
// real page; a read that lands inside that navigation throws "Execution context was destroyed"
// (walk of 2026-10-27 17:54). Settle the page and retry such a read; any other error is thrown.
// The last alternative is Playwright's page.content() wording for the same race.
const NAVIGATION_RACE = /Execution context was destroyed|because of a navigation|Cannot find context with specified id|page is navigating/i;
export async function readAfterNavigation(page, read, { tries = 5, sleep = (ms) => new Promise((r) => setTimeout(r, ms)) } = {}) {
  for (let attempt = 1; ; attempt += 1) {
    await page.waitForLoadState("domcontentloaded").catch(() => {});
    try {
      return await read();
    } catch (error) {
      if (attempt >= tries || !NAVIGATION_RACE.test(String(error?.message))) throw error;
      await sleep(1_000 * attempt);
    }
  }
}

// manifest.json primary_instrument: the exact primary only when every page was collected. Any gap
// rewrites it, so every reader that compares the exact string (the weekly, the wrapper) says DEGRADED.
export function instrumentFor(primary, gapCount) {
  return gapCount ? `${primary} (incomplete: ${gapCount} page(s) not collected)` : primary;
}

// Sections with no rows in any role across the whole walk (R's 06-24 CDFI defect looked like this).
// Recorded and printed; the verdict is unchanged (Paul's call whether it should be a gap).
export const zeroYieldSections = (queries) =>
  queries.filter((q) => Object.values(q.rows_by_role).every((n) => n === 0)).map((q) => q.section_key);

export function validateSections(doc) {
  if (doc?.schema !== "congress-member-search-sections-v1") throw new Error("bad sections file schema");
  if (doc.sections.length !== 17) throw new Error(`expected 17 sections, found ${doc.sections.length}`);
  for (const section of doc.sections) {
    const template = section.parts.join("");
    if (template.split(MEMBER_PLACEHOLDER).length !== 2) {
      throw new Error(`section ${section.key} must have exactly one ${MEMBER_PLACEHOLDER} slot`);
    }
    if (!SECTION_TO_CATEGORY[section.key]) throw new Error(`unmapped section ${section.key}`);
  }
  return doc;
}

// R assemble_url_template (:771).
export const assembleTemplate = (parts) => parts.join("");

// R apply_role (:780-790): swap the single sponsor field token for the role's token.
export function applyRole(template, role, token = "%22field%22%3A%22sponsor%22") {
  if (role === "sponsor") return template;
  const hits = template.split(token).length - 1;
  if (hits !== 1) {
    throw new Error(`Expected exactly ONE sponsor switch token in the template, found ${hits}. ` +
      `Cannot safely swap to role '${role}'.`);
  }
  return template.replace(token, () => `%22field%22%3A%22${role}%22`);
}

// R URLencode(nm, reserved = TRUE) then "%20" -> "+" (:739-740): every UTF-8 byte outside
// [A-Za-z0-9._~-] becomes %XX (upper-case hex).
export function encodeMember(name) {
  const trimmed = String(name).replace(/^[\t\r\n ]+|[\t\r\n ]+$/g, "");
  let out = "";
  for (const byte of Buffer.from(trimmed, "utf8")) {
    const ch = String.fromCharCode(byte);
    out += /[A-Za-z0-9._~-]/.test(ch) ? ch : `%${byte.toString(16).toUpperCase().padStart(2, "0")}`;
  }
  return out.replaceAll("%20", "+");
}

// R build_member_url (:728-743).
export function buildMemberUrl(template, member, page = 1, pageSize = PAGE_SIZE) {
  if (!template.includes(MEMBER_PLACEHOLDER)) {
    throw new Error("URL template has no '__MEMBER__' placeholder");
  }
  const url = template.replace(MEMBER_PLACEHOLDER, () => encodeMember(member));
  return `${url}&pageSize=${pageSize}&page=${page}`;
}

// R congress_decay_weight (:109-114).
export function decayWeight(congress) {
  const value = Number.parseInt(congress, 10);
  let age = NEWEST_CONGRESS - value;
  if (!Number.isFinite(age) || age < 0) age = 0;
  return DECAY_PER_CONGRESS ** age;
}

// R construct_display_name (:513-524): congress.gov names members by their official name.
export function constructDisplayName(official, fallbackFirst, last) {
  const src0 = official && String(official).length ? String(official) : `${fallbackFirst} ${last}`;
  const src = src0.replace(/"[^"]*"/g, " ").replace(/\([^)]*\)/g, " ").trim();
  let tokens = src ? src.split(/\s+/).map((token) => token.replace(/,$/, "")) : [];
  tokens = tokens.filter((token) => !/^[A-Za-z]\.?$/.test(token));
  tokens = tokens.filter((token) => !/^(Jr|Sr|II|III|IV|V)\.?$/.test(token));
  const lastTokens = String(last).toLowerCase().split(/\s+/);
  tokens = tokens.filter((token) => !lastTokens.includes(token.toLowerCase()));
  const first = tokens.length ? tokens[0] : String(fallbackFirst).trim();
  return `${first} ${last}`.trim();
}

export function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;
  const body = String(text).replace(/^﻿/, "");
  for (let i = 0; i < body.length; i += 1) {
    const ch = body[i];
    if (quoted) {
      if (ch === '"' && body[i + 1] === '"') { field += '"'; i += 1; }
      else if (ch === '"') quoted = false;
      else field += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ",") { row.push(field); field = ""; }
    else if (ch === "\n" || ch === "\r") {
      if (ch === "\r" && body[i + 1] === "\n") i += 1;
      row.push(field); rows.push(row); row = []; field = "";
    } else field += ch;
  }
  if (field.length || row.length) { row.push(field); rows.push(row); }
  const [header, ...data] = rows.filter((r) => r.length > 1 || r[0] !== "");
  return data.map((r) => Object.fromEntries(header.map((name, i) => [name, r[i] ?? ""])));
}

// R get_roster_119 + get_pinned_roster (:526-548, :606-619): unitedstates congress-legislators
// legislators-current.csv, reps + senators, display names, unique, radix (byte-order) sort.
export function rosterFromCsv(text, types = ["rep", "sen"]) {
  const rows = parseCsv(text).filter((row) => !("type" in row) || types.includes(row.type));
  const names = rows
    .map((row) => constructDisplayName(row.full_name, row.first_name, row.last_name))
    .filter(Boolean);
  const unique = [...new Set(names)];
  return unique.sort((a, b) => (Buffer.compare(Buffer.from(a), Buffer.from(b))));
}

// ---- cookie-replay fetch (R fetch_html_http :409-468) ------------------------------------

// R is_challenge_html (:401-404). "challenge-platform" is left out on purpose: Cloudflare can
// load /cdn-cgi/challenge-platform/ scripts on ordinary pages, which would mark every good page
// as challenged. The title/DOM checks below are what a challenge interstitial always carries.
export function isChallengeHtml(html) {
  const text = String(html ?? "");
  const title = text.match(/<title[^>]*>([^<]*)<\/title>/i)?.[1] ?? "";
  if (/just a moment|checking your browser|attention required|verifying you are human|verify you are human|security check/i.test(title)) {
    return true;
  }
  return /id=["'](?:challenge-form|challenge-running|cf-challenge-running)["']|cf-browser-verification/i.test(text);
}

export function backoffMs(attempt, random = Math.random) {
  return Math.min(RETRY_CAP_MS, RETRY_BASE_MS * 2 ** (attempt - 1)) + random() * 1_500;
}

export function retryAfterMs(value) {
  const seconds = Number(value);
  if (Number.isFinite(seconds) && seconds > 0) return Math.min(seconds * 1_000, RETRY_CAP_MS);
  const date = Date.parse(value ?? "");
  if (Number.isFinite(date)) return Math.min(Math.max(0, date - Date.now()), RETRY_CAP_MS);
  return null;
}

// One page, cookie replay. Never throws: returns
//   {kind:"ok", status, text, finalUrl, tries}
//   {kind:"challenge", status, tries}   -> caller re-takes the cookie and retries (R rounds)
//   {kind:"error", status, error, tries} -> transport / 429 / 5xx exhausted: a gap, never fatal
export async function fetchWithReplay({
  url,
  session,
  fetchImpl = globalThis.fetch,
  sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
  random = Math.random,
  onOutcome = () => {},
  maxTries = MAX_TRIES,
}) {
  if (!session?.cookie) return { kind: "challenge", status: null, tries: 0 };
  let last = { status: null, error: null };
  for (let attempt = 1; attempt <= maxTries; attempt += 1) {
    let response;
    let text;
    try {
      response = await fetchImpl(url, {
        redirect: "follow",
        signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
        headers: {
          "User-Agent": session.userAgent,
          Cookie: session.cookie,
          Accept: "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
          "Accept-Language": "en-US,en;q=0.9",
          Referer: "https://www.congress.gov/",
        },
      });
      text = await response.text();
    } catch (error) {
      // "Failed to fetch" / "fetch failed" / reset / timeout: back off and retry this page only.
      onOutcome("error");
      last = { status: null, error: `${error?.name ?? "Error"}: ${error?.message ?? error}` };
      if (attempt < maxTries) await sleep(backoffMs(attempt, random));
      continue;
    }
    const status = response.status;
    if (isChallengeHtml(text)) {
      onOutcome("challenge");
      return { kind: "challenge", status, tries: attempt };
    }
    if (status === 429 || status >= 500) {
      onOutcome(status === 429 ? "rate_limited" : "error");
      last = { status, error: `HTTP ${status}` };
      if (attempt < maxTries) {
        const wait = retryAfterMs(response.headers?.get?.("retry-after"));
        await sleep(wait ?? backoffMs(attempt, random));
      }
      continue;
    }
    if (status === 403) {
      onOutcome("challenge");
      return { kind: "challenge", status, tries: attempt };
    }
    if (status >= 400) {
      onOutcome("error");
      return { kind: "error", status, error: `HTTP ${status}`, tries: attempt };
    }
    if (!text) {
      onOutcome("error");
      last = { status, error: "empty body" };
      if (attempt < maxTries) await sleep(backoffMs(attempt, random));
      continue;
    }
    onOutcome("ok");
    return { kind: "ok", status, text, finalUrl: response.url || url, tries: attempt };
  }
  return { kind: "error", status: last.status, error: last.error, tries: maxTries };
}

// ---- adaptive politeness ------------------------------------------------------------------

// Error rate over the last ERROR_WINDOW responses; above ERROR_RATE_LIMIT the pool runs at half
// width for HALVE_HOLD_MS. runPool reads activeWorkers whenever it dispatches.
export function createPoliteness({
  workers = DEFAULT_WORKERS,
  limit = ERROR_RATE_LIMIT,
  windowSize = ERROR_WINDOW,
  minSamples = ERROR_MIN_SAMPLES,
  holdMs = HALVE_HOLD_MS,
  now = Date.now,
} = {}) {
  assertWorkerCount(workers);
  const recent = [];
  let holdUntil = 0;
  let halvings = 0;
  const counts = { ok: 0, error: 0, rate_limited: 0, challenge: 0 };
  return {
    get maxWorkers() { return workers; },
    get activeWorkers() { return now() < holdUntil ? Math.max(1, Math.floor(workers / 2)) : workers; },
    get halvings() { return halvings; },
    get counts() { return { ...counts }; },
    record(outcome) {
      counts[outcome] = (counts[outcome] ?? 0) + 1;
      if (outcome === "challenge") return; // handled by re-clearance, not an error-rate signal
      recent.push(outcome === "ok" ? 0 : 1);
      if (recent.length > windowSize) recent.shift();
      const errors = recent.reduce((sum, value) => sum + value, 0);
      if (recent.length >= minSamples && errors / recent.length > limit && now() >= holdUntil) {
        holdUntil = now() + holdMs;
        halvings += 1;
        recent.length = 0;
      }
    },
  };
}

export function assertWorkerCount(workers) {
  if (!Number.isInteger(workers) || workers < 1) throw new Error("--workers must be a positive integer");
  if (workers > MAX_WORKERS_WITHOUT_PAUL_OK) {
    throw new Error(`--workers ${workers} exceeds ${MAX_WORKERS_WITHOUT_PAUL_OK}; more needs Paul's OK`);
  }
  return workers;
}

// ---- challenge: short automatic wait, then the hand-solve pause ---------------------------

export class HandSolveTimeoutError extends Error {
  constructor(observation, waitMs, escalation = "timeout") {
    super(
      `Congress.gov Cloudflare check was not solved within ${Math.round(waitMs / 60_000)} min ` +
        "(hand-solve pause); collection stopped without interacting with or bypassing it.",
    );
    this.name = "HandSolveTimeoutError";
    // The discovery wrapper and the GovInfo fallback key on this code (fallback = DEGRADED).
    this.code = "CONGRESS_AUTOMATIC_VERIFICATION_TIMEOUT";
    this.classification = {
      kind: "automatic_security_verification",
      provider: "cloudflare",
      interactive: escalation === "interactive",
      escalation,
      collection_outcome: "not_a_result_page",
      captcha_bypass_attempted: false,
      verification_interaction_performed: false,
      hand_solve_wait_ms: waitMs,
      ...observation,
    };
    this.wait_ms = waitMs;
  }
}

// probe() -> true when the visible tab shows a cleared congress.gov page. Detect at once, then poll
// every second while Cloudflare's own automatic check runs, for at most autoMs. Escalate to the
// hand-solve pause (at most handSolveMs) early only when classify() reports an INTERACTIVE challenge
// (a checkbox or widget a person must act on). Nothing here clicks, solves or masks anything.
export async function awaitClearance({
  probe,
  classify = async () => "automatic",
  observe = async () => ({}),
  notify = () => {},
  log = console.log,
  sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
  now = Date.now,
  autoMs = CLEARANCE_WAIT_MS,
  handSolveMs = HAND_SOLVE_TIMEOUT_MS,
  pollMs = CLEARANCE_POLL_MS,
  interactiveReadings = INTERACTIVE_READINGS,
}) {
  if (await probe()) return { via: "none", waited_ms: 0 };
  const start = now();
  let escalation = "timeout";
  let interactiveRun = 0;
  while (now() - start < autoMs) {
    // Several readings in a row: a managed check can show the interactive wording for a moment and
    // then pass on its own; one reading must not raise a banner for nothing.
    const kind = await classify().catch(() => "automatic");
    interactiveRun = kind === "interactive" ? interactiveRun + 1 : 0;
    if (interactiveRun >= interactiveReadings) { escalation = "interactive"; break; }
    await sleep(pollMs);
    if (await probe()) return { via: "automatic", waited_ms: now() - start };
  }
  log(`Cloudflare check ${escalation === "interactive" ? "is interactive" : `did not clear automatically within ${Math.round(autoMs / 1000)} s`}; asking for a hand-solve.`);
  const message =
    "CONGRESS.GOV NEEDS A HAND-SOLVE: a Cloudflare check is showing in the open Chrome window. " +
    `Solve it there; the collector is paused and waits up to ${Math.round(handSolveMs / 60_000)} min.`;
  log(`\n${"=".repeat(78)}\n${message}\n${"=".repeat(78)}`);
  notify("Melange: Congress.gov hand-solve needed", message);
  const pauseStart = now();
  while (now() - pauseStart < handSolveMs) {
    await sleep(pollMs);
    if (await probe()) {
      log("Cloudflare check solved; collection resumes.");
      return { via: "human", waited_ms: now() - start, escalation };
    }
  }
  throw new HandSolveTimeoutError(await observe().catch(() => ({})), handSolveMs, escalation);
}

// ---- jobs, checkpoints -------------------------------------------------------------------

// R loop order (:1369-1420): section by section, sponsor -> original cosponsor -> cosponsor,
// every member inside each pass.
export function planMemberPasses(sectionsDoc, members) {
  const passes = [];
  for (const section of sectionsDoc.sections) {
    const base = assembleTemplate(section.parts);
    for (const role of sectionsDoc.roles) {
      const template = applyRole(base, role, sectionsDoc.sponsor_field_token);
      for (const member of members) {
        passes.push({ section: section.key, label: section.label, category: SECTION_TO_CATEGORY[section.key], role, member, template });
      }
    }
  }
  return passes;
}

export function memberSlug(member) {
  const ascii = String(member).normalize("NFKD").replace(/[^\w]+/g, "_").replace(/^_|_$/g, "");
  let hash = 0;
  for (const byte of Buffer.from(String(member), "utf8")) hash = (hash * 31 + byte) >>> 0;
  return `${ascii.slice(0, 40)}_${hash.toString(16).padStart(8, "0")}`;
}

// Checkpoint path, relative to the output directory, for one page of one member pass.
export function pageCheckpointPath(pass, page) {
  return ["raw", "member_pages", pass.section, pass.role, memberSlug(pass.member), `page-${page}.json`].join("/");
}

// Walk one member pass page by page (R scrape_member_overview_impl :1172-1238), reusing any
// valid checkpoint. loadPage(path) -> stored page or null; fetchPage(url) -> parsed page or
// {gap}; savePage(path, page). Stops after a short page, a single-result redirect, or page 20.
export async function walkMemberPass({ pass, loadPage, fetchPage, savePage, maxPages = MAX_PAGES_PER_MEMBER }) {
  const pages = [];
  for (let page = 1; page <= maxPages; page += 1) {
    const url = buildMemberUrl(pass.template, pass.member, page);
    const file = pageCheckpointPath(pass, page);
    let stored = await loadPage(file);
    if (stored && stored.url !== url) stored = null;
    if (!stored) {
      const fetched = await fetchPage(url, pass, page);
      if (fetched.gap) return { pages, gap: { ...fetched.gap, url, page, section: pass.section, role: pass.role, member: pass.member } };
      stored = { schema: "congress-member-page-v1", url, section: pass.section, role: pass.role, member: pass.member, page, ...fetched };
      await savePage(file, stored);
    }
    pages.push(stored);
    if (stored.kind !== "results" || stored.records.length < PAGE_SIZE) break;
  }
  return { pages, gap: null };
}
