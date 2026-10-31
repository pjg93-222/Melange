#!/usr/bin/env node
/**
 * Congress.gov discovery, Paul's original design (Draft Systems\congress_member_scraper.R +
 * congress_search_urls.R), restored 2026-10-27 on his ruling: "Restore original, but ramp up
 * the number of collectors, keep the handsolve, vastly reduce the cloudflare wait, and keep the
 * cookie replay".
 *
 * 17 sections x 3 roles x every current member -> advanced-search result pages (250 rows).
 * A real, visible Chrome (CDP 9222) clears Cloudflare; parallel workers replay its cookie.
 * Any challenge: 10 s automatic window, then a hand-solve pause (console + toast) for up to
 * 20 min; no human -> exit with CONGRESS_AUTOMATIC_VERIFICATION_TIMEOUT, which the discovery
 * wrapper turns into the GovInfo fallback reported DEGRADED.
 *
 * Writes the pipeline's discovery contract into --out: congress_advanced_records.ndjson,
 * congress_advanced_memberships.ndjson, coverage_gap_ledger.ndjson, exclusion_ledger.ndjson,
 * scope_and_exclusion_contract.json, manifest.json; one checkpoint per page under
 * raw/member_pages so a crash or reboot resumes where it stopped.
 *
 * No stealth: R apply_stealth (congress_member_scraper.R:283-298) is intentionally omitted.
 */

import crypto from "node:crypto";
import os from "node:os";
import fs from "node:fs/promises";
import path from "node:path";
import { spawn } from "node:child_process";
import { createRequire } from "node:module";
import { defaultCongressProfileDir } from "../lib/congress_profile_dir.mjs";
import { parseSingleResultPageSnapshot } from "../lib/congress_advanced_navigation.mjs";
import { writeJsonAtomicWithRetry, writeTextAtomicWithRetry } from "../lib/atomic_checkpoint.mjs";
import { DEFAULT_CDP_PORT, classifyChallenge, clearedProbeExpression, ensureChrome, snapshot, openCollectorTabs, raiseTab, recordClearance, visibilityOf, wakeFrozenPages } from "../lib/congress_cdp_browser.mjs";
import { runPool } from "../lib/congress_page_queue.mjs";
import {
  CHALLENGE_ROUNDS,
  CLEARANCE_WAIT_MS,
  DEFAULT_WORKERS,
  HAND_SOLVE_TIMEOUT_MS,
  MAX_FALLBACK_PAGES_PER_PASS,
  PAGE_SIZE,
  PAUSE_RANGE_MS,
  SECTION_TO_CATEGORY,
  assertWorkerCount,
  awaitClearance,
  createPoliteness,
  decayWeight,
  fetchWithReplay,
  instrumentFor,
  mergeWithPrior,
  planMemberPasses,
  readAfterNavigation,
  rosterFromCsv,
  validateSections,
  walkMemberPass,
  zeroYieldSections,
} from "../lib/congress_member_scrape.mjs";

const require = createRequire(import.meta.url);
const ROOT = path.resolve(import.meta.dirname, "../..");
// Exact string the weekly (lane/gates-to-rulings) and the wrapper compare against.
const PRIMARY_INSTRUMENT = "Congress.gov Advanced Search - Legislation";
// A parse in the background about:blank tab that does not answer becomes a gap, never a hang.
const PARSE_TIMEOUT_MS = 60_000;
const ROSTER_CSV_URL = "https://unitedstates.github.io/congress-legislators/legislators-current.csv";
const DEFAULT_CHROME = process.platform === "win32"
  ? "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" : "/usr/bin/google-chrome";
const TYPE_SLUG_TO_CODE = {
  "house-bill": "hr", "senate-bill": "s", "house-resolution": "hres", "senate-resolution": "sres",
  "house-joint-resolution": "hjres", "senate-joint-resolution": "sjres",
  "house-concurrent-resolution": "hconres", "senate-concurrent-resolution": "sconres",
  "house-amendment": "hamdt", "senate-amendment": "samdt",
};

function parseArgs(argv) {
  const args = {
    registry: path.join("source_data", "legislation", "acu_legislation_search_registry.json"),
    sections: path.join("fec", "collect", "congress_member_search_sections.json"),
    out: path.join("data", "legislation", "congress_advanced_current"),
    profile: defaultCongressProfileDir(),
    chrome: DEFAULT_CHROME,
    cdpPort: DEFAULT_CDP_PORT,
    workers: DEFAULT_WORKERS,
    members: null,
    sectionKeys: null,
    rosterCsv: null,
    categories: null,
  };
  for (let i = 0; i < argv.length; i += 1) {
    const value = argv[i];
    const next = () => argv[++i];
    if (value === "--registry") args.registry = next();
    else if (value === "--sections") args.sections = next();
    else if (value === "--out") args.out = next();
    else if (value === "--profile") args.profile = next();
    else if (value === "--chrome") args.chrome = next();
    else if (value === "--cdp-port") args.cdpPort = Number(next());
    else if (value === "--workers") args.workers = Number(next());
    else if (value === "--members") args.members = next().split(";").map((s) => s.trim()).filter(Boolean);
    else if (value === "--only-sections") args.sectionKeys = new Set(next().split(",").map((s) => s.trim()));
    else if (value === "--roster-csv") args.rosterCsv = next();
    else if (value === "--categories") args.categories = new Set(next().split(",").map((s) => s.trim()).filter(Boolean));
    else if (value === "--resume" || value === "--headed") { /* always resumes; always headed */ }
    else if (value === "--headless") throw new Error("--headless is not supported: Cloudflare is cleared in a visible Chrome");
    else throw new Error(`unknown argument ${value}`);
  }
  assertWorkerCount(args.workers);
  return args;
}

const isoNow = () => new Date().toISOString();
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const stableHash = (value) => crypto.createHash("sha256")
  .update(typeof value === "string" ? value : JSON.stringify(value)).digest("hex");
const rel = (from, file) => path.relative(from, file).split(path.sep).join("/");

function withinRoot(target) {
  const resolved = path.resolve(ROOT, target);
  const relative = path.relative(ROOT, resolved);
  if (relative.startsWith("..") || path.isAbsolute(relative)) throw new Error(`Output must stay within repository root: ${resolved}`);
  return resolved;
}

async function readJsonOrNull(file) {
  try { return JSON.parse(await fs.readFile(file, "utf8")); } catch { return null; }
}

async function writeNdjson(file, rows) {
  const body = rows.map((row) => JSON.stringify(row)).join("\n");
  await writeTextAtomicWithRetry(file, body ? `${body}\n` : "");
}

// Best effort Windows toast through the existing watchdog helper; never throws.
function toast(title, body) {
  try {
    const python = process.env.MELANGE_PYTHON || (process.platform === "win32" ? "python" : "python3");
    const code = "import sys; sys.path.insert(0, sys.argv[1]); import refresh_watchdog as w; w.send_toast(sys.argv[2], sys.argv[3])";
    const child = spawn(python, ["-c", code, path.join(ROOT, "fec"), title, body], { stdio: "ignore", windowsHide: true });
    child.on("error", () => {});
    child.unref();
  } catch { /* the console message is the durable channel */ }
}

const bootEpoch = () => Math.round(Date.now() / 1000 - os.uptime());

async function acquireLock(outDir) {
  const file = path.join(outDir, ".collector.lock");
  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      await fs.writeFile(file, JSON.stringify({ pid: process.pid, at: isoNow(), boot: bootEpoch() }), { flag: "wx" });
      return file;
    } catch (error) {
      if (error.code !== "EEXIST") throw error;
      const held = await readJsonOrNull(file);
      let alive = false;
      try { process.kill(held?.pid, 0); alive = true; } catch { alive = false; }
      // A pid from an earlier boot (or a lock without one) may now belong to anything: stale.
      if (alive && (typeof held?.boot !== "number" || Math.abs(held.boot - bootEpoch()) > 120)) alive = false;
      if (alive) throw new Error(`another collector (pid ${held.pid}) holds ${file}`);
      await fs.rm(file, { force: true });
    }
  }
  throw new Error(`could not take ${file}`);
}

// Runs IN the parse tab (about:blank). DOMParser documents are inert: no scripts, no requests.
function extractInBrowser({ html, loadedUrl }) {
  const doc = new DOMParser().parseFromString(html, "text/html");
  const clean = (value) => String(value ?? "").replace(/\s+/g, " ").trim();
  const text = (node) => clean(node?.textContent);
  const blockText = (root) => {
    const clone = root.cloneNode(true);
    clone.querySelectorAll("script,style,noscript").forEach((n) => n.remove());
    clone.querySelectorAll("br,p,div,li,tr,h1,h2,h3,h4,h5,h6,dt,dd,table,section,ul,ol,th,td,span.result-item")
      .forEach((n) => n.append(doc.createTextNode("\n")));
    return clone.textContent.split("\n").map(clean).filter(Boolean).join("\n");
  };
  const main = doc.querySelector("#main") ?? doc.body;
  const mainText = text(main);
  const range = mainText.match(/Search Results\s+([\d,]+)-([\d,]+) of ([\d,]+)/i);
  const cards = [...doc.querySelectorAll("ol.basic-search-results-lists > li.expanded")];
  if (range || cards.length) {
    const records = cards.map((card) => {
      const heading = card.querySelector(".result-heading");
      const resultLink = heading?.querySelector("a");
      const items = [...card.querySelectorAll(":scope > .result-item")];
      const itemTexts = items.map(text);
      const withPrefix = (prefix) => itemTexts.find((v) => v.toLowerCase().startsWith(prefix.toLowerCase())) ?? null;
      const sponsorLine = withPrefix("Sponsor:");
      const sponsorItem = items.find((n) => text(n).toLowerCase().startsWith("sponsor:"));
      const sponsorLink = sponsorItem?.querySelector('a[href*="/member/"]');
      const actionDate = sponsorLine?.match(/\((Introduced|Submitted|Offered|Proposed)\s+(\d{2}\/\d{2}\/\d{4})\)/i);
      const latest = withPrefix("Latest Action:");
      const latestDate = latest?.match(/Latest Action:\s*.*?\s-\s(\d{2}\/\d{2}\/\d{4})\s/i);
      const tracker = text(card.querySelector(".result-tracker .hide_fromsighted"));
      const visible = card.cloneNode(true);
      visible.querySelectorAll(".hide_fromsighted,script,style").forEach((n) => n.remove());
      const abs = (href) => (href ? new URL(href, "https://www.congress.gov").href : null);
      return {
        indicator: text(card.querySelector(".visualIndicator")),
        heading: text(heading),
        display_number: text(resultLink),
        result_url: abs(resultLink?.getAttribute("href")),
        title: text(card.querySelector(".result-title")) || null,
        purpose: withPrefix("Purpose:"),
        sponsor_line: sponsorLine,
        sponsor: sponsorLine?.replace(/^Sponsor:\s*/i, "")
          .replace(/\s+\((?:Introduced|Submitted|Offered|Proposed)\s+\d{2}\/\d{2}\/\d{4}\).*$/i, "").trim() || null,
        sponsor_url: abs(sponsorLink?.getAttribute("href")),
        initial_action: actionDate?.[1] ?? null,
        initial_action_date: actionDate?.[2] ?? null,
        cosponsor_count: Number(sponsorLine?.match(/Cosponsors:\s*\((\d+)\)/i)?.[1] ?? 0),
        committees: withPrefix("Committees:"),
        latest_action: latest,
        latest_action_date: latestDate?.[1] ?? null,
        amends: withPrefix("Amends "),
        tracker_status: tracker.replace(/^This bill has the status\s*/i, "") || null,
        raw_text: text(visible),
      };
    });
    return {
      kind: "results",
      range: range ? { start: +range[1].replaceAll(",", ""), end: +range[2].replaceAll(",", ""), total: +range[3].replaceAll(",", ""), header: range[0] } : null,
      bill_count_facet: [...doc.querySelectorAll("#innerbox_congress .count")]
        .map((n) => Number(text(n).replace(/\D/g, ""))).filter(Number.isFinite).reduce((a, b) => a + b, 0),
      records,
    };
  }
  if (/\/(bill|amendment)\/\d+(st|nd|rd|th)-congress\//i.test(new URL(loadedUrl).pathname)) {
    const sponsor = doc.querySelector('a[href*="/member/"]');
    return {
      kind: "single",
      title: clean(doc.title),
      body_text: blockText(doc.body),
      sponsor_url: sponsor ? new URL(sponsor.getAttribute("href"), "https://www.congress.gov").href : null,
    };
  }
  if (/no results found|no search results|0 results|did not match any documents/i.test(mainText)) {
    return { kind: "zero", records: [] };
  }
  return { kind: "unparsed", excerpt: mainText.slice(0, 700), title: clean(doc.title) };
}

function parseCanonicalUrl(rawUrl) {
  const url = new URL(rawUrl);
  const match = url.pathname.match(/\/(?:index\.php\/)?(bill|amendment)\/(\d+)(?:st|nd|rd|th)-congress\/([^/]+)\/(\d+)\/?$/i);
  if (!match) throw new Error(`Unrecognized Congress.gov legislation URL: ${rawUrl}`);
  const [, kind, congressText, slug, numberText] = match;
  const type = TYPE_SLUG_TO_CODE[slug.toLowerCase()];
  if (!type) throw new Error(`Unrecognized Congress.gov type slug: ${slug}`);
  const congress = Number(congressText);
  const number = Number(numberText);
  return {
    record_kind: kind.toLowerCase(), congress, type, number,
    canonical_key: `${congress}:${type}:${number}`,
    canonical_url: `https://www.congress.gov/${kind.toLowerCase()}/${congress}th-congress/${slug.toLowerCase()}/${number}`,
  };
}

function normalizeDate(value) {
  const match = String(value ?? "").match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
  return match ? `${match[3]}-${match[1]}-${match[2]}` : null;
}

function windowStatus(value, contract) {
  const iso = normalizeDate(value);
  if (!iso) return "date_unknown";
  if (iso < contract.required_window_start) return "boundary_extension_before_window";
  if (iso > contract.required_window_end) return "after_required_window";
  return "within_required_window";
}

// Same record shape as collect_congress_advanced_pages.mjs normalizePageRecords.
function normalizeRecord(raw, pass, page, index, contract) {
  if (!raw.result_url) throw new Error(`missing result URL (${pass.section}/${pass.role}/${pass.member} p${page} row ${index + 1})`);
  const canonical = parseCanonicalUrl(raw.result_url);
  return {
    ...canonical,
    display_number: raw.display_number,
    heading: raw.heading ?? null,
    title: raw.title,
    purpose: raw.purpose,
    sponsor: raw.sponsor,
    sponsor_url: raw.sponsor_url,
    sponsor_line: raw.sponsor_line,
    initial_action: raw.initial_action,
    initial_action_date: raw.initial_action_date,
    initial_action_date_iso: normalizeDate(raw.initial_action_date),
    window_status: windowStatus(raw.initial_action_date, contract),
    candidate_status: "included_unreviewed_candidate",
    cosponsor_count: raw.cosponsor_count,
    committees: raw.committees,
    latest_action: raw.latest_action,
    latest_action_date: raw.latest_action_date,
    amends: raw.amends,
    tracker_status: raw.tracker_status,
    result_url: raw.result_url,
    raw_text: raw.raw_text,
    source_page: page,
    source_rank: (page - 1) * PAGE_SIZE + index + 1,
  };
}

function buildUnion(passResults, categories, contract) {
  const records = new Map();
  const memberships = new Map();
  for (const { pass, pages } of passResults) {
    const category = categories.get(pass.category);
    for (const page of pages) {
      page.records.forEach((raw, index) => {
        const rec = normalizeRecord(raw, pass, page.page, index, contract);
        const { source_page, source_rank, ...base } = rec;
        if (!records.has(rec.canonical_key)) {
          records.set(rec.canonical_key, { ...base, matched_scoring_categories: new Set(), matched_monitor_categories: new Set(), matched_coverage_probes: new Set() });
        }
        const union = records.get(rec.canonical_key);
        (category?.scoring_category ? union.matched_scoring_categories : union.matched_monitor_categories).add(pass.category);
        const id = `${pass.category}\u0000${rec.canonical_key}`;
        if (!memberships.has(id)) {
          memberships.set(id, {
            query_id: pass.category,
            label: category?.label ?? pass.label,
            scoring_category: Boolean(category?.scoring_category),
            record_kind: "member_section_search",
            parent_category_id: null,
            parent_category_label: null,
            identifier_text: null,
            title_alias: null,
            ambiguous_short_act_alias: null,
            membership_non_dispositive: null,
            source_paragraph: null,
            canonical_key: rec.canonical_key,
            source_page,
            source_rank,
            result_url: rec.result_url,
            section_key: pass.section,
            decay_weight: decayWeight(rec.congress),
            member_roles: [],
          });
        }
        memberships.get(id).member_roles.push({ member: pass.member, role: pass.role, source_page, source_rank });
      });
    }
  }
  const byKey = (a, b) => a.localeCompare(b, undefined, { numeric: true });
  const outRecords = [...records.values()].map((r) => ({
    ...r,
    matched_scoring_categories: [...r.matched_scoring_categories].sort(),
    matched_monitor_categories: [...r.matched_monitor_categories].sort(),
    matched_coverage_probes: [],
  })).sort((a, b) => byKey(a.canonical_key, b.canonical_key));
  const outMemberships = [...memberships.values()].map((m) => ({
    ...m,
    member_roles: m.member_roles.sort((a, b) => `${a.member}|${a.role}`.localeCompare(`${b.member}|${b.role}`)),
  })).sort((a, b) => byKey(`${a.query_id}:${a.canonical_key}`, `${b.query_id}:${b.canonical_key}`));
  return { records: outRecords, memberships: outMemberships };
}

// D-346 interim default (keep all, union, source-tagged; Paul has not ruled keep-vs-replace): the
// complete union already in --out is read and verified against its own manifest before the walk and
// again before writing. A manifest whose union files do not verify stops the run: nothing is replaced.
async function readNdjsonRows(file) {
  const text = await fs.readFile(file, "utf8");
  return text.split("\n").filter((line) => line.trim()).map((line) => JSON.parse(line));
}

// A writer (this collector or the GovInfo fallback) writes manifest.pending.json with the NEW union
// before it replaces the union files, and removes it after manifest.json lands. So after a crash at any
// point the files verify against manifest.json or against manifest.pending.json.
const PENDING_MANIFEST = "manifest.pending.json";

// Rows of `final` when they match (count, sha). With stagedOk (the pending manifest), a `.next`
// sibling that matches is moved into place first: the writer died between its renames.
async function verifiedRows(final, count, sha, stagedOk) {
  const matches = (rows) => rows.length === count && stableHash(rows) === sha;
  try {
    const rows = await readNdjsonRows(final);
    if (matches(rows)) return rows;
  } catch (error) { if (error.code !== "ENOENT") throw error; }
  if (!stagedOk) return null;
  try {
    const rows = await readNdjsonRows(`${final}.next`);
    if (matches(rows)) { await promote(`${final}.next`, final); return rows; }
  } catch (error) { if (error.code !== "ENOENT") throw error; }
  return null;
}

// Rename a staged union file into place; a OneDrive sharing lock gets a few retries.
async function promote(staged, final) {
  for (let attempt = 1; ; attempt += 1) {
    try { await fs.rename(staged, final); return; } catch (error) {
      if (attempt >= 5 || !["EPERM", "EBUSY", "EACCES"].includes(error.code)) throw error;
      await sleep(500 * attempt);
    }
  }
}

async function loadPriorUnion(outDir) {
  let namedUnion = false;
  for (const name of ["manifest.json", PENDING_MANIFEST]) {
    let raw;
    try { raw = await fs.readFile(path.join(outDir, name)); } catch (error) { if (error.code === "ENOENT") continue; throw error; }
    const manifest = JSON.parse(raw.toString("utf8").replace(/^﻿/, ""));
    const union = manifest.union ?? {};
    if (!["complete", "in_progress"].includes(manifest.status) || !union.records_file || !union.memberships_file) continue;
    if (name === "manifest.json") namedUnion = true;
    const stagedOk = name === PENDING_MANIFEST;
    const records = await verifiedRows(path.join(outDir, union.records_file), union.unique_record_count, union.records_sha256, stagedOk);
    if (!records) continue;
    const memberships = await verifiedRows(path.join(outDir, union.memberships_file), union.membership_count, union.memberships_sha256, stagedOk);
    if (memberships) {
      return { manifest, manifest_file: name, manifest_sha256: crypto.createHash("sha256").update(raw).digest("hex"), records, memberships };
    }
  }
  if (namedUnion) throw new Error(`refusing to replace ${outDir}: its union files match neither manifest.json nor ${PENDING_MANIFEST}`);
  return null;
}

// Prior coverage-gap rows about records the union still carries are kept (D-346). Page gaps of an
// earlier walk are superseded by this walk's own page gaps.
async function carriedGapRows(outDir, keys) {
  let rows;
  try { rows = await readNdjsonRows(path.join(outDir, "coverage_gap_ledger.ndjson")); } catch (error) { if (error.code === "ENOENT") return []; throw error; }
  const seen = new Set();
  return rows.filter((row) => {
    if (row.gap_kind === "page_not_collected" || (row.canonical_key && !keys.has(row.canonical_key))) return false;
    const id = `${row.gap_kind}\u0000${row.canonical_key ?? JSON.stringify(row)}`;
    if (seen.has(id)) return false;
    seen.add(id);
    return true;
  });
}

// Under a writer lease (the wrapper's own, or the pipeline's) the lease must still be ours before
// anything is written: a walk orphaned by a killed wrapper never writes under a later chain's lease.
async function assertLeaseStillHeld() {
  const token = process.env.MELANGE_PIPELINE_LOCK_TOKEN;
  if (!token) return;
  const held = await readJsonOrNull(path.join(ROOT, ".pipeline_run.lock"));
  if (held?.token !== token) throw new Error("the writer lease (.pipeline_run.lock) is no longer this run's; nothing written");
}

function countBy(rows, field) {
  const counts = {};
  for (const row of rows) counts[String(row[field])] = (counts[String(row[field])] ?? 0) + 1;
  return Object.fromEntries(Object.entries(counts).sort(([a], [b]) => a.localeCompare(b, undefined, { numeric: true })));
}

async function loadRoster(args, outDir) {
  if (args.members) return { members: args.members, source: "--members" };
  const pinned = path.join(outDir, "roster_119_names.json");
  const existing = await readJsonOrNull(pinned);
  if (existing?.members?.length) return { members: existing.members, source: existing.source, pinned: true };
  const csv = args.rosterCsv
    ? await fs.readFile(args.rosterCsv, "utf8")
    : await (await fetch(ROSTER_CSV_URL, { signal: AbortSignal.timeout(60_000) })).text();
  const members = rosterFromCsv(csv);
  if (members.length < 500) throw new Error(`roster has only ${members.length} members; refusing to run`);
  const doc = { schema: "congress-member-roster-v1", source: args.rosterCsv ?? ROSTER_CSV_URL, fetched_at: isoNow(), csv_sha256: stableHash(csv), members };
  await writeJsonAtomicWithRetry(pinned, doc);
  return { members, source: doc.source, pinned: false };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const outDir = withinRoot(args.out);
  await fs.mkdir(outDir, { recursive: true });
  const registryText = await fs.readFile(path.resolve(ROOT, args.registry), "utf8");
  const registry = JSON.parse(registryText);
  const sectionsText = await fs.readFile(path.resolve(ROOT, args.sections), "utf8");
  const sectionsDoc = validateSections(JSON.parse(sectionsText));
  if (args.sectionKeys) {
    sectionsDoc.sections = sectionsDoc.sections.filter((s) => args.sectionKeys.has(s.key));
    if (sectionsDoc.sections.length !== args.sectionKeys.size) throw new Error("unknown --only-sections key");
  }
  if (args.categories) {
    // Registry category ids (the wrapper's --categories); ids the original design has no section for are skipped.
    sectionsDoc.sections = sectionsDoc.sections.filter((s) => args.categories.has(SECTION_TO_CATEGORY[s.key]));
    if (!sectionsDoc.sections.length) throw new Error("--categories selects none of the 17 original sections");
  }
  const categories = new Map(registry.categories.map((c) => [c.id, c]));
  const contract = registry.collection_contract;
  const slice = Boolean(args.members || args.sectionKeys);
  const partialFile = path.join(outDir, `manifest.partial.${process.pid}.json`);
  const manifest = {
    schema: "acu-congress-advanced-pages-manifest-v1",
    status: "running",
    started_at: isoNow(),
    completed_at: null,
    primary_instrument: PRIMARY_INSTRUMENT,
    collection_design: "member x section x role (Paul's original R design, congress_member_scraper.R)",
    quorum_used: false,
    registry_file: rel(ROOT, path.resolve(ROOT, args.registry)),
    registry_sha256: stableHash(registryText),
    sections_file: rel(ROOT, path.resolve(ROOT, args.sections)),
    sections_sha256: stableHash(sectionsText),
    collection_contract: contract,
    page_contract: { page_size: PAGE_SIZE, discovery_transport: "Official Congress.gov result pages (cookie replay from the visible Chrome)" },
    browser_policy: {
      visible_chrome_cdp_port: args.cdpPort,
      clearance_wait_ms: CLEARANCE_WAIT_MS,
      hand_solve_timeout_ms: HAND_SOLVE_TIMEOUT_MS,
      stealth: "none (R apply_stealth intentionally omitted)",
      captcha_bypass_attempted: false,
    },
    slice,
    selected_query_ids: sectionsDoc.sections.map((s) => SECTION_TO_CATEGORY[s.key]),
    queries: [],
  };
  // The lock covers everything from here to the last write in finish().
  const lock = await acquireLock(outDir);
  try {
    return await walkAndFinish();
  } finally {
    await fs.rm(lock, { force: true });
  }

  async function walkAndFinish() {
  // A slice never writes over a full checkpoint (it would replace the live union with a sample).
  // Any manifest that is not a readable slice manifest counts as a full checkpoint.
  if (slice) {
    for (const name of ["manifest.json", PENDING_MANIFEST]) {
      const file = path.join(outDir, name);
      let text = null;
      try { text = await fs.readFile(file, "utf8"); } catch (error) { if (error.code !== "ENOENT") throw error; }
      if (text === null) continue;
      let doc = null;
      try { doc = JSON.parse(text.replace(/^\uFEFF/, "")); } catch { doc = null; }
      if (doc?.slice !== true) {
        throw new Error(`refusing a --members/--only-sections slice into ${outDir}: ${name} is not a slice checkpoint; pass a sandbox --out`);
      }
    }
  }
  // Fail fast, before hours of walking, if the union already in --out cannot be carried forward.
  if (!slice) {
    const prior = await loadPriorUnion(outDir);
    console.log(prior ? `Carry-forward: ${prior.records.length} record(s) / ${prior.memberships.length} membership(s) already in ${rel(ROOT, outDir)} are kept (D-346 union).` : "Carry-forward: no prior union in --out.");
  }
  await writeJsonAtomicWithRetry(partialFile, manifest);

  const roster = await loadRoster(args, outDir);
  manifest.roster = { source: roster.source, member_count: roster.members.length, pinned_for_cycle: !args.members };
  const passes = planMemberPasses(sectionsDoc, roster.members).map((pass, index) => ({ ...pass, index }));
  console.log(`PLAN: ${sectionsDoc.sections.length} section(s) x ${sectionsDoc.roles.length} role(s) x ${roster.members.length} member(s) = ${passes.length} member pass(es); workers ${args.workers}`);

  const politeness = createPoliteness({ workers: args.workers });
  const stats = { live_pages: 0, resumed_pages: 0, browser_fallback_pages: 0, harvests: 0, hand_solves: 0, paused_ms: 0, transports: {} };
  const fallbackByPass = new Map();
  const gaps = [];
  let browser = null;
  let context = null;
  let mainPage = null;
  let parsePage = null;
  let session = null;
  let harvesting = null;
  let lastHarvestAt = 0;
  let fallbackTabChain = Promise.resolve();
  const startedMs = Date.now();

  const observe = async (page) => ({ loaded_url: page.url(), page_title: await page.title().catch(() => null) });
  const clearIn = async (page) => {
    const probe = clearedProbeExpression();
    const result = await awaitClearance({
      probe: () => page.evaluate(probe).catch(() => false),
      // Read-only: title and body text decide whether a person must act (checkbox/widget).
      // A short body timeout keeps each ~1 s poll ~1 s while the tab is between documents.
      classify: async () => classifyChallenge(await snapshot(page, { bodyTimeoutMs: 300 })),
      observe: () => observe(page),
      notify: toast,
    });
    if (result.via !== "none") stats.paused_ms += result.waited_ms;
    if (result.via === "automatic") {
      stats.automatic_clearances = (stats.automatic_clearances ?? 0) + 1;
      stats.automatic_clearance_ms = (stats.automatic_clearance_ms ?? 0) + result.waited_ms;
    }
    if (result.via === "human") {
      stats.hand_solves += 1;
      stats.hand_solve_escalations = [...(stats.hand_solve_escalations ?? []), result.escalation];
    }
    return result;
  };
  // R harvest_cf_session (:346-389): the visible tab loads the page, clears, and its cookies and
  // its own user agent are re-taken. Single flight: concurrent challenged workers share it.
  const harvest = (probeUrl) => {
    // A worker whose request left before the last re-take finished just retries with it.
    if (!harvesting && Date.now() - lastHarvestAt < 5_000) return Promise.resolve();
    harvesting ??= (async () => {
      try {
        stats.harvests += 1;
        await raiseTab(mainPage);
        await mainPage.goto(probeUrl, { waitUntil: "domcontentloaded", timeout: 60_000 }).catch(() => {});
        const visibility = await visibilityOf(mainPage);
        console.log(`Clearance tab is ${visibility ?? "of unknown visibility"} (must be "visible" for the Cloudflare check).`);
        const cleared = await clearIn(mainPage);
        // The cleared tab navigates on to the results page: read only once it has settled.
        const userAgent = await readAfterNavigation(mainPage, () => mainPage.evaluate(() => navigator.userAgent));
        const cookies = (await context.cookies("https://www.congress.gov")).filter((c) => /congress\.gov$/i.test(c.domain.replace(/^\./, "")));
        session = { cookie: cookies.map((c) => `${c.name}=${c.value}`).join("; "), userAgent };
        const meta = await recordClearance({ context, userAgent, profile: args.profile });
        manifest.clearance_session = { harvested_at: meta.harvested_at, cf_clearance_present: meta.cf_clearance_present, cookies_taken: cookies.length, harvests: stats.harvests, cleared_via: cleared.via, clearance_tab_visibility: visibility, cookie_value_recorded: false };
        console.log(`Harvested ${cookies.length} congress.gov cookie(s)${meta.cf_clearance_present ? " (incl. cf_clearance)" : " (no cf_clearance)"}; cleared via ${cleared.via}.`);
      } finally {
        lastHarvestAt = Date.now();
        harvesting = null;
      }
    })();
    return harvesting;
  };
  const parse = async (html, loadedUrl, pass, page) => {
    let timer;
    const timedOut = new Promise((resolve) => { timer = setTimeout(() => resolve({ kind: "parse_timeout" }), PARSE_TIMEOUT_MS); });
    const out = await Promise.race([parsePage.evaluate(extractInBrowser, { html, loadedUrl }), timedOut]).finally(() => clearTimeout(timer));
    if (out.kind === "parse_timeout") return { gap: { reason: "parse_timeout", detail: `parse tab did not answer within ${PARSE_TIMEOUT_MS} ms` } };
    if (out.kind === "unparsed") return { gap: { reason: "unparsed_page", detail: `${out.title}: ${out.excerpt}`.slice(0, 500) } };
    if (out.kind === "single") {
      const snap = parseSingleResultPageSnapshot({ loadedUrl, title: out.title, bodyText: out.body_text, sponsorUrl: out.sponsor_url });
      const canonical = parseCanonicalUrl(loadedUrl);
      return { kind: "single", records: [{ ...snap, heading: snap.display_number, result_url: canonical.canonical_url }], range: { total: 1 } };
    }
    if (out.kind === "results" && out.range && out.records.length !== out.range.end - out.range.start + 1) {
      return { gap: { reason: "page_range_mismatch", detail: `${out.records.length} rows vs ${out.range.header}` } };
    }
    for (const record of out.records ?? []) {
      try { parseCanonicalUrl(record.result_url); } catch (error) {
        return { gap: { reason: "unrecognized_result_url", detail: String(error.message).slice(0, 300) } };
      }
    }
    return { kind: out.kind, records: out.records, range: out.range ?? { total: 0 }, bill_count_facet: out.bill_count_facet ?? null };
  };
  const pause = () => sleep(PAUSE_RANGE_MS[0] + Math.random() * (PAUSE_RANGE_MS[1] - PAUSE_RANGE_MS[0]));
  const fetchPage = async (url, pass, page) => {
    for (let round = 1; round <= CHALLENGE_ROUNDS; round += 1) {
      await pause();
      const result = await fetchWithReplay({ url, session, onOutcome: (o) => politeness.record(o) });
      if (result.kind === "ok") {
        stats.live_pages += 1;
        stats.transports.cookie_replay = (stats.transports.cookie_replay ?? 0) + 1;
        const parsed = await parse(result.text, result.finalUrl, pass, page);
        return parsed.gap ? parsed : { ...parsed, transport: "cookie_replay", fetched_at: isoNow(), html_sha256: stableHash(result.text) };
      }
      if (result.kind === "error") return { gap: { reason: "fetch_failed", status: result.status, detail: result.error, tries: result.tries } };
      console.log(`  challenged (round ${round}/${CHALLENGE_ROUNDS}) ${pass.section} | ${pass.role} | ${pass.member} p${page} -> re-taking the cookie`);
      await harvest(url);
    }
    // R per-page browser fallback (:1341-1349), a throwaway tab per page.
    const key = `${pass.section}|${pass.role}`;
    fallbackByPass.set(key, (fallbackByPass.get(key) ?? 0) + 1);
    if (fallbackByPass.get(key) > MAX_FALLBACK_PAGES_PER_PASS) {
      throw new Error(`Aborting: more than ${MAX_FALLBACK_PAGES_PER_PASS} pages of ${key} still challenged after ${CHALLENGE_ROUNDS} rounds; checkpoints kept, re-run resumes.`);
    }
    // Single flight: one fallback tab at a time, so concurrent workers never fight over the front tab
    // the Cloudflare check needs (the background-tab failure 611deeafa fixed).
    const run = fallbackTabChain.then(async () => {
      const tab = await context.newPage();
      try {
        await raiseTab(tab);
        await tab.goto(url, { waitUntil: "domcontentloaded", timeout: 60_000 }).catch(() => {});
        await clearIn(tab);
        await tab.waitForLoadState("domcontentloaded").catch(() => {});
        stats.live_pages += 1;
        stats.browser_fallback_pages += 1;
        stats.transports.browser_fallback = (stats.transports.browser_fallback ?? 0) + 1;
        // URL and HTML read together, so they describe the same document.
        const { html, loadedUrl } = await readAfterNavigation(tab, async () => ({ html: await tab.content(), loadedUrl: tab.url() }));
        const parsed = await parse(html, loadedUrl, pass, page);
        return parsed.gap ? parsed : { ...parsed, transport: "browser_fallback", fetched_at: isoNow(), html_sha256: stableHash(html) };
      } finally {
        await tab.close().catch(() => {});
      }
    });
    fallbackTabChain = run.catch(() => {});
    return run;
  };
  const loadPage = async (file) => {
    const stored = await readJsonOrNull(path.join(outDir, file));
    if (stored) stats.resumed_pages += 1;
    return stored;
  };
  const savePage = (file, page) => writeJsonAtomicWithRetry(path.join(outDir, file), page);

  const passResults = new Array(passes.length);
  try {
    // Connect lazily: a fully checkpointed run never touches the browser.
    const ensureBrowser = async (probeUrl) => {
      if (browser) return;
      const chrome = await ensureChrome({ port: args.cdpPort, profile: args.profile, chromePath: args.chrome });
      console.log(`Chrome ${chrome.spawned ? "launched" : "reused"} on ${chrome.endpoint}`);
      const woken = await wakeFrozenPages(args.cdpPort);
      if (woken) console.log(`Marked ${woken} idle tab(s) active so the CDP attach does not wait on a frozen page.`);
      const { chromium } = require("playwright");
      browser = await chromium.connectOverCDP(chrome.endpoint, { timeout: 90_000 });
      context = browser.contexts()[0] ?? (await browser.newContext());
      // mainPage: the visible, front tab Cloudflare is cleared (or hand-solved) in.
      ({ mainPage, parsePage } = await openCollectorTabs(context));
      await harvest(probeUrl);
    };
    let connecting = null;
    const ensureBrowserOnce = (probeUrl) => (connecting ??= ensureBrowser(probeUrl));
    let completedPasses = 0;
    await runPool({
      items: passes,
      governor: politeness,
      run: async (pass) => {
        const result = await walkMemberPass({
          pass,
          loadPage,
          savePage,
          fetchPage: async (url, p, page) => {
            await ensureBrowserOnce(url);
            return fetchPage(url, p, page);
          },
        });
        passResults[pass.index] = { pass, pages: result.pages };
        if (result.gap) gaps.push({ gap_kind: "page_not_collected", ...result.gap });
        completedPasses += 1;
        if (completedPasses % 25 === 0 || completedPasses === passes.length) {
          const minutes = (Date.now() - startedMs) / 60_000;
          console.log(`  ${completedPasses}/${passes.length} member passes | live pages ${stats.live_pages} | ${(stats.live_pages / Math.max(minutes, 1e-9)).toFixed(1)} pages/min | workers ${politeness.activeWorkers}/${politeness.maxWorkers} | gaps ${gaps.length}`);
        }
      },
    });
  } catch (error) {
    await failRun(error);
    throw error;
  } finally {
    if (browser) {
      await parsePage?.close().catch(() => {});
      await mainPage?.close().catch(() => {});
      await browser.close().catch(() => {}); // disconnect only: Paul's Chrome window stays open
    }
  }
  try {
    return await finish();
  } catch (error) {
    await failRun(error);
    throw error;
  }

  async function failRun(error) {
    manifest.status = "failed";
    manifest.failed_at = isoNow();
    manifest.stats = { ...stats, politeness: politeness.counts, halvings: politeness.halvings };
    manifest.error = { name: error.name, code: error.code ?? null, message: error.message, stack: error.stack };
    if (error.code === "CONGRESS_AUTOMATIC_VERIFICATION_TIMEOUT") {
      const receiptDir = path.join(outDir, "raw", "failure_debug");
      await fs.mkdir(receiptDir, { recursive: true });
      const receipt = path.join(receiptDir, `hand_solve_timeout_${process.pid}_${Date.now()}.json`);
      const body = { schema: "congress-hand-solve-timeout-v1", observed_at: isoNow(), classification: error.classification, wait_ms: error.wait_ms };
      await writeJsonAtomicWithRetry(receipt, body);
      manifest.automatic_verification_timeout = {
        classification: "automatic_verification_timeout",
        cause: "hand_solve_timeout",
        receipt_file: rel(outDir, receipt),
        receipt_sha256: stableHash(await fs.readFile(receipt, "utf8")),
        hand_solve_timeout_ms: HAND_SOLVE_TIMEOUT_MS,
        interaction_performed: false,
        captcha_bypass_attempted: false,
        collection_stopped_without_result_acceptance: true,
      };
    }
    await writeJsonAtomicWithRetry(partialFile, manifest).catch(() => {});
  }

  async function finish() {
    const minutes = (Date.now() - startedMs) / 60_000;
    const activeMinutes = Math.max(1e-9, minutes - stats.paused_ms / 60_000);
    manifest.stats = {
      ...stats,
      politeness: politeness.counts,
      concurrency_halvings: politeness.halvings,
      elapsed_minutes: +minutes.toFixed(2),
      pages_per_minute: +(stats.live_pages / Math.max(minutes, 1e-9)).toFixed(1),
      pages_per_minute_excluding_clearance_waits: +(stats.live_pages / activeMinutes).toFixed(1),
    };
    const done = passResults.filter(Boolean);
    const union = buildUnion(done, categories, contract);
    for (const section of sectionsDoc.sections) {
      const category = section.key;
      const rows = union.memberships.filter((m) => m.section_key === section.key);
      const perRole = Object.fromEntries(sectionsDoc.roles.map((role) => [role,
        done.filter((r) => r.pass.section === category && r.pass.role === role).reduce((n, r) => n + r.pages.reduce((k, p) => k + p.records.length, 0), 0)]));
      manifest.queries.push({ query_id: SECTION_TO_CATEGORY[section.key], section_key: section.key, label: section.label, unique_record_count: rows.length, rows_by_role: perRole });
    }
    manifest.zero_yield_sections = slice ? [] : zeroYieldSections(manifest.queries);
    if (manifest.zero_yield_sections.length) console.warn(`WARNING: no rows in any role for section(s): ${manifest.zero_yield_sections.join(", ")}`);
    manifest.walk_union = { unique_record_count: union.records.length, membership_count: union.memberships.length };
    // D-346 interim default: everything already in --out is kept and source-tagged (re-verified now).
    const prior = slice ? null : await loadPriorUnion(outDir);
    if (prior) {
      const merged = mergeWithPrior(union, prior);
      union.records = merged.records;
      union.memberships = merged.memberships;
      manifest.carried_forward = { ...merged.carried_forward, prior_manifest_file: prior.manifest_file };
    }
    const gapsFile = path.join(outDir, "coverage_gap_ledger.ndjson");
    const gapLedger = slice ? gaps : [...await carriedGapRows(outDir, new Set(union.records.map((r) => r.canonical_key))), ...gaps];
    // Usable data with holes: the union is written and the run exits 0, but the instrument
    // string no longer equals the primary, so every reader (weekly, wrapper) reports DEGRADED.
    manifest.primary_instrument = instrumentFor(PRIMARY_INSTRUMENT, gaps.length);
    if (gaps.length) {
      manifest.coverage_gaps = gaps.length;
      console.error(`DEGRADED: ${gaps.length} page(s) not collected after retries; see coverage_gap_ledger.ndjson`);
    }
    const recordsFile = path.join(outDir, "congress_advanced_records.ndjson");
    const membershipsFile = path.join(outDir, "congress_advanced_memberships.ndjson");
    const exclusionsFile = path.join(outDir, "exclusion_ledger.ndjson");
    const scopeFile = path.join(outDir, "scope_and_exclusion_contract.json");
    manifest.status = slice ? "slice_complete" : "complete";
    manifest.completed_at = isoNow();
    manifest.union = {
      unique_record_count: union.records.length,
      membership_count: union.memberships.length,
      counts_by_congress: countBy(union.records, "congress"),
      counts_by_type: countBy(union.records, "type"),
      scoring_candidate_count: union.records.filter((r) => r.matched_scoring_categories.length).length,
      monitor_candidate_count: union.records.filter((r) => r.matched_monitor_categories.length).length,
      recall_probe_count: 0,
      records_file: rel(outDir, recordsFile),
      records_sha256: stableHash(union.records),
      memberships_file: rel(outDir, membershipsFile),
      memberships_sha256: stableHash(union.memberships),
      coverage_visibility: {
        gap_ledger_file: rel(outDir, gapsFile), gap_ledger_sha256: stableHash(gapLedger),
        exclusion_ledger_file: rel(outDir, exclusionsFile), exclusion_ledger_sha256: stableHash([]),
        scope_contract_file: rel(outDir, scopeFile),
      },
    };
    // Crash safety: both new union files are staged as .next, then the new manifest lands as
    // manifest.pending.json, then the staged files are renamed into place. The files on disk always
    // verify against manifest.json (old) or manifest.pending.json (new, once a staged file left
    // behind is moved in by the next reader).
    await assertLeaseStillHeld();
    const pendingFile = path.join(outDir, PENDING_MANIFEST);
    await writeNdjson(`${recordsFile}.next`, union.records);
    await writeNdjson(`${membershipsFile}.next`, union.memberships);
    await writeJsonAtomicWithRetry(pendingFile, manifest);
    await promote(`${recordsFile}.next`, recordsFile);
    await promote(`${membershipsFile}.next`, membershipsFile);
    await writeNdjson(gapsFile, gapLedger);
    await writeNdjson(exclusionsFile, []);
    await writeJsonAtomicWithRetry(scopeFile, {
      design: manifest.collection_design,
      included_congresses: [117, 118, 119],
      sections: sectionsDoc.sections.map((s) => s.key),
      roles: sectionsDoc.roles,
      members: roster.members.length,
      not_covered_by_the_original_design: registry.categories.filter((c) => !Object.values(SECTION_TO_CATEGORY).includes(c.id)).map((c) => c.id),
      automated_semantic_exclusions: 0,
    });
    await writeJsonAtomicWithRetry(path.join(outDir, "manifest.json"), manifest);
    await fs.rm(pendingFile, { force: true });
    await fs.rm(partialFile, { force: true });
    console.log(`${manifest.status.toUpperCase()}: ${union.records.length} unique record(s), ${union.memberships.length} section membership(s); ` +
      `${stats.live_pages} live page(s), ${stats.resumed_pages} resumed; ${manifest.stats.pages_per_minute} pages/min ` +
      `(${manifest.stats.pages_per_minute_excluding_clearance_waits} excluding clearance waits)`);
  }
  } // walkAndFinish
}

await main();
