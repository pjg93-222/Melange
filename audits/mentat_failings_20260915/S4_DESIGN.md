# S4 DESIGN — Cross-industry addressing (Area E)

Date: 2026-09-16. Status: ACCEPTED by Paul 2026-09-16 ("The condition is met,
proceed"); S3 committed as `303409192`, precondition verified in git, phases 1-7
IN PROGRESS. Questions A-E resolved by that go: A commit S3 first (done), S1
waived for S4; B one console; C S4 fixes the contract and the server-side echo,
`graph_data.py` stays S5's; D street joins the grain, measured first; E names
relative to `report_directory`. Every line number below was re-read from the
live tree today by read-only scouts; the brief's line numbers were not trusted
(HANDOFF correction). Slug correction after acceptance: the console's slug rule is
`contribution_data._slug` (underscores: `credit_union`), not hyphens.

## 0. Premise corrections (measured, not assumed)

1. **There is no console-global industry.** `server.py:1977-1994` takes
   `--port`, `--data-root`, `--keys-file`, `--rscript`, `--read-only` and nothing
   else; `Console.__init__` (`:501-522`) holds `report_directory` only. The
   server already serves all eight published snapshots from one process.
   `POST /api/contributions/query` and `/records` select by `dataset`
   (`contribution_data.py:290-300`), and `GET /api/graph`, `/api/comparison`,
   `/api/comparison-flows` select by `industry` (`server.py:1805-1811`).
   So "one console addressing many snapshots" is already the architecture. S4's
   job is to make the selector **one explicit, uniform, registry-backed
   parameter** that every industry-scoped route accepts and echoes, and that
   every saved sheet and series persists.
2. **The dataset id IS the industry label.** `contribution_data.py:186`:
   `industry = workbook.name.removesuffix(' Industry Spending Overview.xlsx')`
   and `item = {'id': industry, 'industry': industry, 'label': industry, ...}`.
   Eight labels exist on disk: Banking, Community Banks, Credit Arms, Credit
   Union, Crypto, Fintech, Property & Casualty Insurance, Telecom.
3. **No companion Data workbook exists on disk today** (search of the report
   directory, 2026-09-16). The registry must carry `companion: null` as a normal
   state, not an error.
4. **Saved views already persist `source` and `sheets` verbatim**
   (`server.py:945-965`), so `source.industry` and `sheets[].source.industry`
   round-trip without a server change; the record-level `value` dict at `:960`
   whitelists keys, so a top-level `industry` would be DROPPED. The DE-021 gap is
   on the client producer: `viewSourceRecord()` (`chart-studio-core.js:887-900`)
   copies only `reportName, sha256, runName, sheet, mode, dataset` — an
   `industry` set anywhere upstream is silently discarded at save time. That is
   the exact DE-021 shape (a producer nobody enumerated).
5. **`/api/cross-reference` refuses any query string** (`server.py:1802-1803`)
   and serves whatever `state/cross-reference/latest.json` points at. Whether
   `report.json` carries an `industry` field is UNVERIFIED — phase 5 measures it
   before promising per-industry cross-reference.

## 1. Vocabulary (the S5 parameter names)

- `industry` — the published label exactly as the registry lists it
  (`"Credit Union"`, `"Property & Casualty Insurance"`), URL-encoded on GET
  routes, a JSON string on POST bodies. The server also accepts the label's slug
  (`_slug(industry)`, the `.cache/industry-report/<slug>` directory name) and
  always echoes the label. No new naming vocabulary is invented; the collector
  slugs (`credit-unions`, `MENTAT_INDUSTRY` in R) are NOT touched and are not a
  valid value here.
- `dataset` — legacy selector on `/api/contributions/query|records`; same value
  as `industry`. Kept so every existing caller keeps working.
- `id=published-reports` — the Graph routes' fixed run identifier (`server.py:1458`).
- `build_stamp` — per-snapshot 64-hex, echoed on every industry-scoped response.

Resolution rule (`industry_scope.resolve`), applied identically on every route:

1. `industry` present → must resolve in the registry by label or slug, else 400.
   The body is the one shape `server.py` emits from its `except` clauses
   (`do_GET :1853`, `do_POST :1974`) and carries no other key:
   `{"error": "Choose a registered industry: Banking, Credit Union."}` — the
   registered labels, sorted, joined with a comma and a space, one terminal
   period. There is no `known` key; adding one would need a second `send()`,
   and every existing handler answers with `{"error": str(error)}` alone.
2. else `dataset` present → industry = registry entry whose `dataset == value`.
3. both present and they disagree → 400
   `{"error": "The industry and dataset in this request disagree."}`.
4. neither → the route's legacy behaviour, unchanged (catalog/session: all
   industries; query/records: today's "Choose an available contribution
   dataset."; cross-reference: latest pointer).

Responses add `industry` (label or `null`) and, where a snapshot was read,
`build_stamp`. No existing key changes meaning or position.

## 2. Snapshot registry

New module `mentat/app/snapshot_registry.py` (S4-owned, new file):

- `registry(report_directory) -> dict` wraps `contribution_data._sources()`
  (`:174-227`) so dataset ids, availability, hydration and lineage checks stay
  the single source of truth. No second glob, no second hash.
- Entry shape (names, never absolute paths outside `report_directory`; the
  existing provenance at `:247-259` deliberately exposes workbook NAMES only, and
  `report_directory` is already public via `/api/graph-catalog`):

```json
{
  "industry": "Credit Union",
  "slug": "credit_union",
  "dataset": "Credit Union",
  "available": true,
  "message": null,
  "workbook":  {"name": "Credit Union Industry Spending Overview.xlsx", "sha256": "<64hex>", "bytes": 15728640, "modified_at": "2026-07-28T23:01:00Z"},
  "companion": null,
  "database":  {"path": ".cache/industry-report/credit_union/mentat.db", "sha256": "<64hex>", "hydrated": false},
  "payload_sha256": "<64hex>",
  "destination_schema": 1,
  "build_stamp": "<64hex>"
}
```

  `companion`, when present:
  `{"name": "<Industry> Industry Spending Data.xlsx", "sha256", "bytes", "modified_at", "lineage_matches": true|false}`
  (`lineage_matches` is `_sources()`'s `data_lineage_matches`, reported never
  silently accepted — same rule as today). `database.path` is relative to the
  project root; `hydrated` is true when the recovery receipt path was taken.
- `build_stamp = sha256("\n".join([workbook_sha256, companion_sha256 or "", database_sha256 or "", payload_sha256 or ""]))`.
  Deterministic, recomputable by anyone holding the four hashes, changes when
  any input changes, and independent of the console's code stamp.
- Envelope: `{"schema_version": 1, "report_directory": "<abs>", "generated_at": "<iso>", "snapshots": [...]}`,
  sorted by label. Unavailable snapshots stay listed with `available: false`
  and their `message` (mirrors `catalog()` at `:262-268`).
- **Nullable only when unavailable.** A workbook this process cannot open
  (Excel holding it, a scanner mid-pass) is reported as one entry with
  `available: false` and `message: "Report workbook is unreadable."`; it has no
  hash, so `workbook.sha256` and `build_stamp` are `null`. A stamp built from
  the three remaining fields would be the SAME string for every unreadable
  book, so none is invented. Every `available: true` entry carries both, and
  `validate_entry` still refuses an available entry that drops either.
- **Two invariants the client parser adds** (`chart-studio-core.js`
  `parseSnapshotRegistry`), neither in the field list above but both needed to
  fail this contract's negative controls: `dataset`, when present and
  non-empty, must equal `industry` (section 1 says they carry the same value,
  so the two disagreeing is the collector-slug negative control); and
  `companion` is `null` or an object, never a bare filename string (the same
  DE-021 shape as industry-as-object).
- Route `GET /api/snapshots` (new; `?industry=` filters to one entry). Also
  folded into `GET /api/contributions/session` as `industries[]`
  (label, slug, available, build_stamp) so the client needs one call at load.
- Contract: `contracts/snapshot_registry.json` — examples: one available entry
  with `companion: null`, one with a companion, one `available: false`.
  Negative controls: entry without `build_stamp`; workbook given as an absolute
  path; an entry whose `industry` is a collector slug (`credit-unions`).

## 3. `industry` on the routes

| Route | Today (line) | Change |
| --- | --- | --- |
| `GET /api/contributions/session` | `:1729` `{token, read_only}` | + `industry` echo (or null), + `industries[]` from the registry |
| `GET /api/contributions/catalog` | `:1731` all datasets | `?industry=` filters `datasets`; every dataset gains `build_stamp`; + `industry` echo |
| `GET /api/contributions/geography/catalog` | `:1742` static catalog | `?industry=` accepted and echoed only — `geo_catalog()` (`contribution_geo.py:178`) is industry-independent and stays so |
| `POST /api/contributions/query` | `:1908` body `dataset` | body `industry` optional per section 1; response + `industry`, `build_stamp` |
| `POST /api/contributions/records` | `:1910` | same |
| `POST /api/contributions/geography` | `:1912` | body `industry` accepted and echoed |
| `GET/POST /api/studio/views` | `:1824`, `:1960` | see section 4 |
| `GET /api/studio/briefing`, `POST .../add` | `:1817`, `:1954` | `source.industry` persisted (already verbatim at `:1023`) and asserted in the contract |
| `GET /api/cross-reference` | `:1801` refuses any query | `?industry=` becomes the ONLY accepted query key; see section 5 |
| `GET /api/graph`, `/api/comparison*` | `:1805-1811` already take `industry` | response + `industry` echo and `build_stamp` per report; resolution goes through `industry_scope` so slug and label both work |
| `GET /api/snapshots` | — | new, section 2 |

Every route hunk in `server.py` is a one-line call into `industry_scope`
(new module, S4-owned) so the contended file takes the smallest possible diff.

Contract: `contracts/contributions_api.json` — request/response example pairs
for each row above (with and without `industry`), the two error bodies, and
negative controls: `industry` as a number, as a path, unknown label, and
`industry`/`dataset` disagreeing. Producers asserted: the real routes on an
in-process `Console` (the `test_studio_views.py` pattern) with
`MENTAT_REPORT_DIRECTORY` pointed at a fixture directory holding two snapshots.

## 4. Chart Studio model and round-trip

`chart-studio-core.js` (S4-owned):

- `createSheet()` (`:101-119`) `source` gains `industry: ''` and `dataset: ''`.
- New `sheet.sources: []` — the ordered **series sources**. Empty means the
  sheet has one series source, its own `source`. Each entry
  `{industry, dataset, label}`. The word "series" already means the colour
  column index inside `compileReport()` (`:269-295`, `series = -1`), so the
  persisted array is named `sources` to avoid that collision; the contract
  says "one series per source".
- `viewSourceRecord()` (`:887-900`) copies `industry` and sets it from
  `chosen.industry` — the DE-021 producer fix.
- `STUDIO_GROUP_LIMIT = 60` (`:191`) is unchanged and applies per source query
  (`maxGroups` at `:360` is sent per compiled query; one query per source).
- Migration on load: a sheet with `source.dataset` and no `source.industry`
  gets `industry = dataset` (they are the same string today).

`chart-studio.js` (S4-owned): the dataset picker sets `source.industry`;
`compile()` (`chart-studio-contributions.js:71,127`, unowned — one-line body
addition, claimed in the table) sends `industry` beside `dataset`;
`openability()` (`:1901-1908`) checks every `sources[].industry` against the
registry, not only `parts[1]` of `sourceKey`. `sourceKey`
(`'contributions|'+id+'|'+workbook_sha256`, `:349`) is unchanged.

Rendering two industries on one chart is NOT built here; S4 delivers the model,
the fan-out contract and the round-trip. Nothing in the UI writes
`sheet.sources[]` yet: `selectContributionDataset` rewrites every sheet's
`source`, and `sourceKey` is one per view, not one per sheet. So the
two-industry single view is proven at the contract, API and server
round-trip level, and in the browser by two saved single-industry views —
not by a picker. The picker is S5's. `server.py` `save_view` (`:945-965`)
gains shape validation only: `source.industry` and each `sources[].industry`,
when present, must be non-empty strings (negative control: object, empty
string); `list_views` (`:919-935`) adds `industries: [distinct labels]` per
view so the picker can print "Banking + Credit Union". Membership in the
registry is NOT validated at save or load — a saved view must reload after a
snapshot is retired; the client reports it at open time.

Contract: `contracts/studio_api.json` — a two-industry save payload, its list
and get responses, a briefing `add` with `source.industry`, negative controls.
Asserted by: `app/tests/studio-contract.test.js` (producers
`viewSourceRecord`, `createSheet`, migration), `tests/test_studio_views.py`
(server round-trip), and a new browser `.cjs`
(`tests/test_studio_industry_browser.cjs`, spawning `server.py` on a free port
with a throwaway data root, saving a two-industry view from the real client,
reloading, and pasting the on-disk `<id>.json` into the receipt — the DE-021
real-client pass).

## 5. Graph and cross-reference readers

- Graph: `app.graph()` (`server.py:1466-1475`) resolves through
  `industry_scope` and echoes `industry` + `build_stamp`; `graph_view(paths,
  filters)` (`graph_data.py:308`) is unchanged in signature. **`graph_data.py`
  is S5's file in the ownership table.** S4 fixes the contract (the `industry`
  echo, the `build_stamp` per report) and touches the file only if Paul moves
  the reader-signature change to S4 — otherwise S5 implements against the
  contract. Paul's call (question C).
- Cross-reference: phase 5 first measures whether `report.json` /
  `progress.json` under `state/cross-reference/<run>/` carry the industry. If
  yes: `?industry=` selects the newest run for that industry and the "no path
  or run parameters" guard stays for every other key. If no: the route echoes
  the run's industry as `null`, the contract records "latest pointer only", and
  a producer change in `tools/run_cross_reference.py` (unowned) is written up as
  a proposed patch, not applied.

## 6. Contributor Detail (S2 decision 7, S4 work order)

1. `contribution_data.py` `DIMENSIONS` (`:48-58`): insert `street_1`,
   `street_2` between `occupation` and `city` and REORDER to employer,
   occupation, street_1, street_2, city, state, zip5. Order drives the
   dimension list (`:240`) and a `CREATE TABLE` column list (`:309`), so the
   analytics cache key/version must change with it or an old cache silently
   mis-positions columns — phase 6 verifies the cache is rebuilt, by negative
   control. Record builder (`:343-348`) reads `contributor_street_1/2`.
2. `tools/crypto_workbook_builder.mjs` `buildContributorDetail` (`:2205`):
   header gains Street 1, Street 2; table widens A5:K → A5:M; all eleven sites
   S2 listed (`:2207-2256`). File is unowned; S4 claims it in the table.
3. New test importing `contracts/raw_contribution_columns.json` and asserting
   `surfaces.contributor_detail_sheet.required_headers` against the real
   builder; flip that surface's `status` off `"deferred to S4"` in the same
   change.
4. `report.R` `contributor_keys` (`:1828-1831`): **Paul's call (question D).**
   Recommendation: add `street_1, street_2` to the grain. Without them the two
   columns have no defined value on an aggregated row (which street, when a
   contributor gave from two?), so the only honest alternatives are a silent
   blank or a first-seen pick. The 45,000-row cap per (cycle, company) with the
   reconciling fold already handles growth. Phase 6 measures the row-count
   delta on the Banking snapshot (largest, 39 MB) before the edit lands.

## 7. Phases (blueprint; every phase ends with a verifier pass and a receipt)

| # | Phase | Files | Agent | Exit |
| --- | --- | --- | --- | --- |
| 0 | Gate | — | Paul | go; S3 committed (server.py); S1 waived or committed; questions A-E answered |
| 1 | Contracts | `contracts/snapshot_registry.json`, `contributions_api.json`, `studio_api.json`, README index rows | executor, architect review | three files, negative controls non-empty, README index updated |
| 2 | Registry | `snapshot_registry.py` (new), `tests/test_snapshot_registry.py` | executor | build stamp changes when any input changes; companion null; 8 live entries listed |
| 3 | Scope on routes | `industry_scope.py` (new), `server.py` (thin hunks), `contribution_data.py`, `tests/test_industry_routes.py` | architect (server.py), executor (rest) | routes green with and without `industry`; both 400s; negative controls FAIL |
| 4 | Studio model | `chart-studio-core.js`, `chart-studio.js`, `chart-studio-contributions.js` (one line), `server.py` (save_view/list_views), `app/tests/studio-contract.test.js`, `tests/test_studio_views.py`, new `.cjs` | executor, typescript-reviewer | two-industry view saves, lists with `industries`, reloads byte-intact; real-client receipt |
| 5 | Graph / cross-reference | `server.py` graph echo; cross-reference per measurement | architect | contract fixed; `graph_data.py` only if Paul reassigns |
| 6 | Contributor Detail | `contribution_data.py`, `crypto_workbook_builder.mjs`, `report.R` (if D says yes), new header test | executor | cache rebuild proven; header test green; status flipped |
| 7 | Gates + receipts | patch, receipts, HANDOFF S4 section, `/ecc:quality-gate`, `/ecc:code-review`, python + typescript reviewers | verifier | existing suites unchanged from S0's known-red list; acceptance run on a scratch console against the real report directory |

Acceptance run (phase 7): scratch console on a free port (never 8802/8806/8808),
writable throwaway `--data-root`, `MENTAT_REPORT_DIRECTORY` = the real
published folder (8 snapshots, read-only workbooks). One `query` per industry
returns rows whose `industry` and `build_stamp` match the registry; a saved view
with two industries reloads intact; `/api/health` gives the expected
`code_sha256` / `assets_sha256` pair Paul's restart must reach.

Receipt: `patches/S4_cross_industry_contract.patch` + `receipts/S4_*.txt`;
HANDOFF S4 section appended with the parameter names in section 1;
`/ecc:save-session mentat-failings-S4`; brain STATE line and a DECISIONS draft
("industry is a request parameter, never a console global").

## 8. Questions for Paul (blocking)

- **A. Preconditions.** S3 is BUILT, UNCOMMITTED with four `server.py` hunks at
  `@@ -1729` and `@@ -1851` — the same regions S4's route hunks land in. S1 is
  "not started" but touches only `mentat/R/*` and two `tools/` files, none of
  S4's. Proposal: commit S3 first; waive S1 for S4.
- **B. One console.** PREAMBLE was not pasted, so your one-versus-two answer
  did not reach this session. Design assumes ONE console addressing many
  snapshots, which is what the code already does.
- **C. `graph_data.py` ownership.** Table says S5; brief says S4 changes the
  readers. Move the reader-signature change to S4, or S4 writes the contract
  and S5 implements?
- **D. Contributor Detail grain.** Street into `contributor_keys` (recommended,
  measured first) or not?
- **E. Registry paths.** Names relative to `report_directory` and a
  project-relative database path (proposed), or absolute paths as the brief
  literally says?
