# Contract fixtures — MENTAT FAILINGS LANE (2026-09-15)

This directory holds the lane's API contracts. A contract here is an **example
payload in a JSON file that both test suites import**. It is never a prose
description, and a prose description in a session note, a HANDOFF.md section, or
a code comment does not create, amend, or satisfy a contract.

## Why this rule exists

From the project brain, `DEADENDS.md`, verbatim:

> ## DE-021 - Splitting one feature across two lanes with a prose-only API contract
> Date: 2026-09-14
> Approach: The Mentat usability lane (fix1, round 2) built the Chart Studio saved-views and briefing-tray write path across two parallel lanes, client (F) and server (E), with the `source`/`provenance` field's shape agreed only in prose between the lanes rather than in a shared schema. Measured 2026-09-14, lanes/fix1 receipt and integrity review.
> Failure mode: the client lane sent `source`/`provenance` as strings, the server lane demanded dicts, each side's unit tests passed against its own reading, and only a real-client run on a writable console exposed it (no view ever reached disk; every .pptx printed "[object Obje" as the SHA).
> Root cause: A second producer (`migrateStoredViews`) slipped past even the first fix because the shared fixture tested readers, not producers.
> Would reconsider if: never as prose. Rule: the contract carries example payloads in one fixture both suites import, the fixture is asserted against the PRODUCERS (negative control must fail), and a lane is not done until a real-client pass on a writable instance has exercised every write path.

Three failures are encoded in that record, and this convention answers each one:

1. Two lanes agreed in prose, so each side's tests passed against its own
   reading. **Answer: one file, imported by both suites.** Not two copies, not a
   Python fixture mirrored into a JS fixture.
2. The shared fixture tested *readers*, so a second producer slipped past the
   first fix. **Answer: assertions run against producers.**
3. Nothing proved the assertion had teeth. **Answer: a negative control that
   must fail.**

## When a contract is required

Write a contract file *before* writing code whenever a session introduces or
changes any of:

- an HTTP request or response shape on any `/api/*` route;
- a URL scheme, including query-parameter names and any deep-link or permalink format;
- a column order or column set in an export (CSV, `.xlsx` worksheet, warehouse dump);
- a status or state vocabulary crossing a process boundary (for example the
  terminal state a fanout task lands in, or a job-status string the console polls);
- any on-disk JSON a different session's code reads.

If two sessions touch the same shape, the contract lands before either one edits
code, and the session that owns the file per HANDOFF.md writes it.

## File convention

One JSON file per contract, named for the shape it describes, kebab-case:

```
contracts/evidence-job-status.json
contracts/fanout-task-terminal-state.json
contracts/contribution-detail-columns.json
```

Each file has this envelope:

```json
{
  "contract": "evidence-job-status",
  "version": 1,
  "owner": "S3",
  "produced_by": [
    "mentat/app/server.py:<fn>",
    "mentat/tools/pac_evidence.py:<fn>"
  ],
  "consumed_by": [
    "mentat/app/evidence-csv.js:<fn>"
  ],
  "description": "One sentence. Orientation only — the examples are the contract.",
  "examples": [
    { "...": "a payload a producer MUST be able to emit and a consumer MUST accept" }
  ],
  "negative_controls": [
    {
      "why": "the DE-021 shape: provenance as a bare string, not an object",
      "payload": { "...": "a payload that MUST be rejected" }
    }
  ]
}
```

Rules on the envelope:

- `produced_by` lists **every** producer, not the obvious one. DE-021 was not
  caught by the first fix because a second producer existed and nobody had
  enumerated it. Before a contract is considered complete, grep for every
  writer of the shape and list them all.
- `examples` is the normative part. Prose in `description` is orientation and
  carries no authority.
- `negative_controls` is mandatory and non-empty. A contract with no negative
  control is not finished.
- `version` increments on any change to `examples`. Bumping the version
  obliges the owning session to re-run both suites.

## Both suites import the same file

The fixture is read from disk at test time by both languages. Neither suite
embeds a copy; neither suite keeps a translated mirror. The paths below assume
the suites run with `C:\Users\pgoff\Mentat\mentat` as the working directory,
which is the invocation directory HANDOFF.md records as proven.

Python:

```python
import json, pathlib

CONTRACTS = pathlib.Path(__file__).resolve().parents[2] / "audits" / "mentat_failings_20260915" / "contracts"

def load_contract(name):
    return json.loads((CONTRACTS / f"{name}.json").read_text(encoding="utf-8"))
```

Node (`.cjs`):

```js
const fs = require('node:fs');
const path = require('node:path');

const CONTRACTS = path.resolve(__dirname, '..', '..', 'audits', 'mentat_failings_20260915', 'contracts');

function loadContract(name) {
  return JSON.parse(fs.readFileSync(path.join(CONTRACTS, `${name}.json`), 'utf8'));
}
```

R (`Rscript`), where a contract crosses into the R pipeline:

```r
contracts_dir <- file.path("..", "..", "audits", "mentat_failings_20260915", "contracts")
load_contract <- function(name) jsonlite::fromJSON(file.path(contracts_dir, paste0(name, ".json")), simplifyVector = FALSE)
```

A session that adds the first R-side contract test confirms `jsonlite` is
available and records that in its receipt; if it is not, it records the
substitute it used.

## Assertions run against producers

This is the part DE-021 says the previous lane got wrong. A test that feeds
`examples` into a parser and checks the parser accepts them proves nothing about
what the other side actually sends.

For each entry in `produced_by`, the owning session writes a test that:

1. **invokes the real producer** — calls the function, hits the route with a
   test client, or runs the export — rather than hand-building a payload;
2. asserts the producer's actual output matches the contract's example shape
   (keys present, types correct, column order identical where order is part of
   the contract);
3. does this for **every** producer in the list, not just the first.

For each entry in `consumed_by`, a second test feeds each `examples` payload to
the real consumer and asserts it is accepted.

## The negative control must fail

Every contract test file ends with a control proving the assertion has teeth:
feed each `negative_controls[].payload` to the same assertion used in the
producer test, and assert that it **is rejected**. If a negative control passes
the assertion, the assertion is not testing anything, and the session treats
that as a red test — not as a passing suite.

Record in the receipt, for each contract: the number of producers asserted, the
number of consumers asserted, and the negative-control result. A receipt that
does not show a failing negative control has not demonstrated a working contract.

## Real-client pass

DE-021's rule ends with a condition that is not a unit test: *"a lane is not
done until a real-client pass on a writable instance has exercised every write
path."* For any contract on a write path, the owning session runs the real
console on a scratch port in writable mode, exercises the path from the client,
and pastes the resulting artifact — the file that reached disk, or the response
body — into its receipt. Port 8802 is Paul's console and is never used for this.

## Changing a contract

1. Edit the JSON first and bump `version`.
2. Re-run both suites; expect red.
3. Change the code until both are green and the negative control still fails.
4. Record the version bump and the full test output in the receipt.
5. Note the change in the owning session's HANDOFF.md section, naming every
   other session whose files consume the shape.

Contract files are committed by Paul from the session's patch, like any other
change in this lane.

## Index

| Contract file | Owner | Shape | Status |
| --- | --- | --- | --- |
| _(none yet — S0 is read-only and writes no contracts)_ | — | — | — |
| `raw_contribution_columns.json` (v2) | S2 | column-order block + per-surface headers (raw warehouse x2, R stage, Contributions sheet, tidy registry, Contributor Detail, Chart Studio DIMENSIONS - no surface deferred) | asserted by `tests/test_raw_contribution_columns.{py,R,cjs}`, `tests/test_contribution_dimensions_order.py`, `tests/test_contributor_detail_header.cjs` |
| `snapshot_registry.json` (v2) | S4 | registry envelope + per-snapshot entry (industry, slug, workbook/companion/database/payload hashes, build_stamp; sha256 and build_stamp are null on an unreadable, unavailable workbook) | asserted by: `tests/test_snapshot_registry.py`, `tests/test_industry_routes.py` (GET /api/snapshots), `app/tests/studio-contract.test.js` (parseSnapshotRegistry) |
| `contributions_api.json` (v2) | S4 | industry-scoped request/response pairs across every contributions/graph/comparison/cross-reference/snapshots route, plus the two industry-resolution error bodies | asserted by: `tests/test_industry_routes.py` |
| `studio_api.json` (v1) | S4 | Chart Studio sheet + saved-view + briefing shapes carrying `source.industry` and `sheet.sources[]` round-trip | asserted by: `tests/test_studio_views_industry.py`, `app/tests/studio-contract.test.js`, `tests/test_studio_industry_browser.cjs` |
| `url_scope.json` (v1) | S5 | the console URL scheme: hash names the tab, query string carries the scope (`industry`, `company`, `cycle`, `mode`, `direction`, `tier`, `funding`, `category`, `recipient`, `saved`), plus write() merge semantics (remove-on-empty, preserve-unknown) and S6's reserved keys | asserted by: `app/tests/scope.test.js`, `tests/test_navigation_scope_browser.cjs` |

Each session appends its contracts to this table as it creates them.
