// End to end through collect_congress_member_pages.mjs on a fully checkpointed --out (no browser is
// touched: every page is already on disk). Covers the D-346 carry-forward write path, crash recovery
// from manifest.pending.json, fail-closed drift, the slice guard and the lock span (review 2026-10-27).
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { SECTION_TO_CATEGORY, buildMemberUrl, pageCheckpointPath, planMemberPasses, validateSections } from "../lib/congress_member_scrape.mjs";

const HERE = import.meta.dirname;
const ROOT = path.resolve(HERE, "../..");
const COLLECTOR = path.join(ROOT, "fec", "collect", "collect_congress_member_pages.mjs");
const SECTIONS = validateSections(JSON.parse(fs.readFileSync(path.join(ROOT, "fec/collect/congress_member_search_sections.json"), "utf8")));
const MEMBERS = ["Ann Wagner", "Andy Barr"];
const stableHash = (v) => crypto.createHash("sha256").update(JSON.stringify(v)).digest("hex");
const ndjson = (rows) => rows.map((r) => JSON.stringify(r)).join("\n") + "\n";
const readRows = (f) => fs.readFileSync(f, "utf8").split("\n").filter(Boolean).map((l) => JSON.parse(l));

const bill = (n) => ({ canonical_key: `119:hr:${n}`, congress: 119, type: "hr", number: n, title: `prior ${n}`,
  matched_scoring_categories: ["payments"], matched_monitor_categories: [], matched_coverage_probes: [] });
const PRIOR_RECORDS = [bill(7), { ...bill(8), fallback_discovery: { source: "govinfo" } }];
const PRIOR_MEMBERSHIPS = [{ query_id: "payments", canonical_key: "119:hr:7" }, { query_id: "payments", canonical_key: "119:hr:8" }];

function world(name) {
  const out = path.join(ROOT, "fec", "tests", `.tmp_walk_${process.pid}_${name}`);
  fs.rmSync(out, { recursive: true, force: true });
  fs.mkdirSync(out, { recursive: true });
  const registry = path.join(out, "..", `.tmp_walk_${process.pid}_${name}.registry.json`);
  fs.writeFileSync(registry, JSON.stringify({
    categories: Object.values(SECTION_TO_CATEGORY).map((id) => ({ id, label: id, scoring_category: true })),
    collection_contract: { required_window_start: "2021-01-03", required_window_end: "2027-01-03" },
  }));
  fs.writeFileSync(path.join(out, "roster_119_names.json"), JSON.stringify({ schema: "congress-member-roster-v1", source: "test", members: MEMBERS }));
  // Every page checkpointed: one result (H.R.7, already known) in the first pass, every other page empty.
  planMemberPasses(SECTIONS, MEMBERS).forEach((pass, index) => {
    const file = path.join(out, pageCheckpointPath(pass, 1));
    fs.mkdirSync(path.dirname(file), { recursive: true });
    const hit = index === 0 || index === 1;   // H.R.7 for Ann Wagner, H.R.9 (new) for Andy Barr
    const n = index === 0 ? 7 : 9;
    const records = hit ? [{ result_url: `https://www.congress.gov/bill/119th-congress/house-bill/${n}`, display_number: `H.R.${n}`, title: `walk ${n}`, initial_action_date: "03/01/2025" }] : [];
    fs.writeFileSync(file, JSON.stringify({ schema: "congress-member-page-v1", url: buildMemberUrl(pass.template, pass.member, 1), section: pass.section, role: pass.role, member: pass.member, page: 1, kind: hit ? "results" : "zero", records, range: { total: records.length } }));
  });
  const cleanup = () => { fs.rmSync(out, { recursive: true, force: true }); fs.rmSync(registry, { force: true }); };
  return { out, registry, cleanup };
}

function writePrior(out, manifestName, { records = PRIOR_RECORDS, memberships = PRIOR_MEMBERSHIPS, union = {} } = {}) {
  fs.writeFileSync(path.join(out, "congress_advanced_records.ndjson"), ndjson(records));
  fs.writeFileSync(path.join(out, "congress_advanced_memberships.ndjson"), ndjson(memberships));
  fs.writeFileSync(path.join(out, manifestName), JSON.stringify({
    schema: "acu-govinfo-discovery-fallback-manifest-v1", status: "complete",
    primary_instrument: "GovInfo BILLSTATUS/BILLS official bulk fallback",
    union: { records_file: "congress_advanced_records.ndjson", unique_record_count: records.length, records_sha256: stableHash(records),
      memberships_file: "congress_advanced_memberships.ndjson", membership_count: memberships.length, memberships_sha256: stableHash(memberships), ...union },
  }));
}

function run(w, extra = [], env = {}) {
  const base = { ...process.env, MELANGE_PYTHON: "python-not-used" };
  delete base.MELANGE_PIPELINE_LOCK_TOKEN;
  delete base.MELANGE_PIPELINE_LOCK_OWNER_PID;
  return spawnSync(process.execPath, [COLLECTOR, "--registry", w.registry, "--out", path.relative(ROOT, w.out), "--workers", "2", ...extra],
    { cwd: ROOT, encoding: "utf8", env: { ...base, ...env }, timeout: 120_000 });
}

test("full walk over a prior union: every prior row kept and tagged, new rows added, no pending manifest or lock left", () => {
  const w = world("full");
  try {
    writePrior(w.out, "manifest.json");
    const result = run(w);
    assert.equal(result.status, 0, result.stderr + result.stdout);
    const manifest = JSON.parse(fs.readFileSync(path.join(w.out, "manifest.json"), "utf8"));
    assert.equal(manifest.status, "complete");
    assert.equal(manifest.primary_instrument, "Congress.gov Advanced Search - Legislation");
    const rows = Object.fromEntries(readRows(path.join(w.out, "congress_advanced_records.ndjson")).map((r) => [r.canonical_key, r]));
    assert.deepEqual(Object.keys(rows).sort(), ["119:hr:7", "119:hr:8", "119:hr:9"]);
    assert.deepEqual(rows["119:hr:7"].discovery_sources, ["congress_gov_category_search", "congress_gov_member_pages"]);
    assert.deepEqual(rows["119:hr:8"].discovery_sources, ["govinfo_bulk_fallback"]);
    assert.deepEqual(rows["119:hr:9"].discovery_sources, ["congress_gov_member_pages"]);
    assert.equal(manifest.union.unique_record_count, 3);
    assert.equal(manifest.union.records_sha256, stableHash(readRows(path.join(w.out, "congress_advanced_records.ndjson"))));
    assert.equal(manifest.carried_forward.rows_deleted, 0);
    assert.equal(manifest.carried_forward.prior_manifest_file, "manifest.json");
    assert.deepEqual(manifest.walk_union, { unique_record_count: 2, membership_count: 2 });
    assert.ok(!fs.existsSync(path.join(w.out, "manifest.pending.json")));
    assert.ok(!fs.existsSync(path.join(w.out, ".collector.lock")));
  } finally { w.cleanup(); }
});

test("crash after the union files were replaced: the files verify against manifest.pending.json and the next run carries them", () => {
  const w = world("pending");
  try {
    writePrior(w.out, "manifest.pending.json");
    writePrior(w.out, "manifest.json", { union: { unique_record_count: 99 } }); // old manifest, files already new
    writePrior(w.out, "manifest.pending.json");
    const result = run(w);
    assert.equal(result.status, 0, result.stderr + result.stdout);
    const manifest = JSON.parse(fs.readFileSync(path.join(w.out, "manifest.json"), "utf8"));
    assert.equal(manifest.carried_forward.prior_manifest_file, "manifest.pending.json");
    assert.equal(manifest.union.unique_record_count, 3);
  } finally { w.cleanup(); }
});

test("union files matching neither manifest: the run refuses before walking and replaces nothing", () => {
  const w = world("drift");
  try {
    writePrior(w.out, "manifest.json", { union: { records_sha256: "0".repeat(64) } });
    const before = fs.readFileSync(path.join(w.out, "congress_advanced_records.ndjson"));
    const result = run(w);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /match neither manifest\.json nor manifest\.pending\.json/);
    assert.deepEqual(fs.readFileSync(path.join(w.out, "congress_advanced_records.ndjson")), before);
    assert.ok(!fs.existsSync(path.join(w.out, ".collector.lock")), "the lock is released on refusal");
  } finally { w.cleanup(); }
});

test("a slice into a full checkpoint is refused and replaces nothing", () => {
  const w = world("slice");
  try {
    writePrior(w.out, "manifest.json");
    const before = fs.readFileSync(path.join(w.out, "congress_advanced_records.ndjson"));
    const result = run(w, ["--members", "Ann Wagner"]);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /refusing a --members\/--only-sections slice/);
    assert.deepEqual(fs.readFileSync(path.join(w.out, "congress_advanced_records.ndjson")), before);
  } finally { w.cleanup(); }
});

test("a writer died between its two renames: the staged memberships file is completed from the pending manifest", () => {
  const w = world("staged");
  try {
    writePrior(w.out, "manifest.json");                       // old union, verified
    const newer = [...PRIOR_MEMBERSHIPS, { query_id: "payments", canonical_key: "119:hr:8", extra: 1 }].slice(0, 2).map((m, i) => ({ ...m, n: i }));
    fs.writeFileSync(path.join(w.out, "congress_advanced_memberships.ndjson.next"), ndjson(newer));
    fs.writeFileSync(path.join(w.out, "manifest.pending.json"), JSON.stringify({
      schema: "acu-congress-advanced-pages-manifest-v1", status: "complete", slice: false,
      union: { records_file: "congress_advanced_records.ndjson", unique_record_count: 2, records_sha256: stableHash(PRIOR_RECORDS),
        memberships_file: "congress_advanced_memberships.ndjson", membership_count: 2, memberships_sha256: stableHash(newer) },
    }));
    // manifest.json still matches the old files, so it wins first; break it to model the mixed state.
    writePrior(w.out, "manifest.json", { union: { memberships_sha256: "f".repeat(64) } });
    const result = run(w);
    assert.equal(result.status, 0, result.stderr + result.stdout);
    const manifest = JSON.parse(fs.readFileSync(path.join(w.out, "manifest.json"), "utf8"));
    assert.equal(manifest.carried_forward.prior_manifest_file, "manifest.pending.json");
    assert.ok(!fs.existsSync(path.join(w.out, "congress_advanced_memberships.ndjson.next")));
    assert.ok(readRows(path.join(w.out, "congress_advanced_memberships.ndjson")).some((m) => m.n === 1));
  } finally { w.cleanup(); }
});

test("prior coverage-gap rows about carried records are kept; this walk's page gaps replace older page gaps", () => {
  const w = world("gaps");
  try {
    writePrior(w.out, "manifest.json");
    fs.writeFileSync(path.join(w.out, "coverage_gap_ledger.ndjson"), ndjson([
      { gap_kind: "boundary_extension_included", canonical_key: "119:hr:8" },
      { gap_kind: "boundary_extension_included", canonical_key: "119:hr:8" },
      { gap_kind: "page_not_collected", url: "old" },
      { gap_kind: "date_unknown_requires_review", canonical_key: "119:hr:404" },
    ]));
    const result = run(w);
    assert.equal(result.status, 0, result.stderr + result.stdout);
    const rows = readRows(path.join(w.out, "coverage_gap_ledger.ndjson"));
    assert.deepEqual(rows, [{ gap_kind: "boundary_extension_included", canonical_key: "119:hr:8" }]);
    const manifest = JSON.parse(fs.readFileSync(path.join(w.out, "manifest.json"), "utf8"));
    assert.equal(manifest.union.coverage_visibility.gap_ledger_sha256, stableHash(rows));
    assert.equal(manifest.primary_instrument, "Congress.gov Advanced Search - Legislation");
  } finally { w.cleanup(); }
});

test("a run whose writer lease is no longer its own writes nothing", () => {
  const w = world("lease");
  try {
    writePrior(w.out, "manifest.json");
    const before = fs.readFileSync(path.join(w.out, "congress_advanced_records.ndjson"));
    const result = run(w, [], { MELANGE_PIPELINE_LOCK_TOKEN: `not-held-${process.pid}`, MELANGE_PIPELINE_LOCK_OWNER_PID: "1" });
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /writer lease .* is no longer this run's/);
    assert.deepEqual(fs.readFileSync(path.join(w.out, "congress_advanced_records.ndjson")), before);
    assert.ok(!fs.existsSync(path.join(w.out, "manifest.pending.json")));
  } finally { w.cleanup(); }
});

test("a .collector.lock from an earlier boot (or without one) is stale even if its pid is alive", () => {
  const w = world("stale_lock");
  try {
    writePrior(w.out, "manifest.json");
    fs.writeFileSync(path.join(w.out, ".collector.lock"), JSON.stringify({ pid: process.pid, at: "x", boot: 1 }));
    const result = run(w);
    assert.equal(result.status, 0, result.stderr + result.stdout);
  } finally { w.cleanup(); }
});

test("a slice is refused when manifest.json is unreadable (treated as a full checkpoint)", () => {
  const w = world("slice_unreadable");
  try {
    fs.writeFileSync(path.join(w.out, "manifest.json"), "{not json");
    const result = run(w, ["--members", "Ann Wagner"]);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /manifest\.json is not a slice checkpoint/);
  } finally { w.cleanup(); }
});