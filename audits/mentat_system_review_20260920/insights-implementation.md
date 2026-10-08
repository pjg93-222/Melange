# Mentat Insights implementation — 2026-09-20

Implemented a local Insights workspace using the user's chosen default: industry
favorites, comparable trends and change explanations visible; eight additional
panels optional. Lobbying disclosures and BLS inflation are excluded.

Higgsfield generated synthetic design reference job
`c67f4e78-17a0-436d-abb3-87f21ae1e450`. It was visually inspected, then translated
into repository HTML, CSS and SVG: compact teal switches, white cards, plum serif
headings, three desktop columns, collapsible comparison controls and detailed
tables. No contribution data was sent to Higgsfield. Browser tests and screenshots
use synthetic fixtures. The actual local app retains the existing Mentat theme.

## Implemented behavior

- All eleven panels are independently visible/hidden, with preferences saved in
  the browser. Controls retain automatic cycle selection rather than silently
  changing the next query's scope when a result arrives.
- Exact signed-cent analysis uses all selected, verified facts; positive-gross
  shares do not net away refunds. Funding channels remain separate. Comparison
  cutoffs match election stage, and baseline/current source drilldowns reconcile.
- New metrics cover recipient preference and breadth, trends, company-change
  decomposition, concentration, relationship persistence, portfolio overlap,
  timing and conservative forecast baselines.
- FEC recipient masters and Melange's saved, hash-verified evidence supply
  profiles, outgoing payments, payee/purpose patterns, campaign finances and
  legislative context. Each context panel identifies its own accounting scope
  and source files. Campaign totals are not presented as selected-industry money.
- The local observation journal stores hashes and first/last inspection times.
  It preserves changed identity/financial versions without copying donor names.
  Snapshot transactions roll back if preparation fails or source identity changes.
- As-of filters apply to event dates, not historical public knowledge. The
  interface explicitly distinguishes those concepts. Forecasts remain unavailable
  for current published indexes lacking verified complete historical cycles.
- Paginated source records, sortable tables and CSV/JSON exports preserve scope,
  cents units, source identities and limitations. CSV text is formula-safe.
- Background preparation has bounded concurrency and exact-result capacity
  guards. A capacity refusal retains narrowing options and publishes no partial
  totals or journal snapshot. Verified results use the existing integrity-checked
  disk cache across restarts, invalidated by source, integration and code identity.
- Existing Host/Origin/session-token gates and published-workbook source proofs
  protect the new HTTP routes. Clients cannot provide filesystem roots or claim
  historical completeness.

## Verification and live results

The full Python suite passed **1,157 tests** before the final cache refinement.
After that refinement, the focused final runs passed **80 Insights tests**, **10
query tests**, **23 HTTP tests**, **16 build-identity tests**, and **12 query-cache
tests**. The JavaScript unit suite passed **274 tests**. Insights browser checks
passed against both synthetic engine output and the generated complete console,
including actual backend request validation, direct links, navigation, slow/stale
responses, pagination, exports, toggles and a 390-pixel layout. The existing
console browser suite passed, and the navigation-scope suite passed all 13 steps.
Template parity and JavaScript syntax checks passed.

An earlier broad run had three build-identity failures while source files were
still being edited; the frozen full-suite rerun passed. The full Python suite
still emits its pre-existing unclosed test-socket ResourceWarning.

Read-only live checks used the authoritative published report directory:

- Banking/Citibank: **42,000 included giving observations**, 418 recipient groups,
  498 recipient/profile links, 541 saved payment/financial rows and 298 legislative
  matches before presentation limits. Context coverage is partial and labeled.
- One displayed recipient's **259 records reconciled exactly to 12,841,160
  cents**. Inspection timestamps were present. Individual donor records were not
  copied into this audit.
- Full Banking: **592,570 included observations** processed into 24,284 exact
  compact cells; `complete_input_scan=true`. Core panels returned 2,385 recipient
  groups, 12 trend rows and 15 change-component rows before display limits.
- Independent integration checks found exact-cycle Warren/Cantwell identities,
  saved financial totals through June 30, and dated legislative relationships.
  Citibank's dated affiliations yielded 427 saved payments, 254 payee groups,
  64 reported-purpose groups and two sender summaries.

The application was updated through its idle-safe restart endpoint, preserving
its data root and report directory. Its loaded Python and asset hashes matched
the on-disk build afterward. The isolated preview server was closed.

## Additional diagnosed cache defect

A follow-up run reproduced an existing Windows projection-cache defect twice
in ten isolated trials. A completed SQLite update could retain the same file
size, modification timestamp and creation timestamp. Both the verification fast
path and the separately memoized hash could therefore accept changed projection
amounts. This was not concurrent-test contamination.

Projection verification now includes the first 100 SQLite header bytes, including
its transaction change counter, and freshly hashes a changed projection. A new
deterministic test forces identical stat tuples and exercises both retained and
cleared verification caches. It failed before the fix, then passed in ten paired
repetitions; the complete 12-test cache suite also passed. This repair concerns
derived projection verification between requests; it does not claim to detect
every possible same-stat mutation of an immutable original index during a query.

## Evidence

- `insights-python-final.log`, `insights-focused-final.log`
- `insights-javascript-final.log`, `insights-browser-final.log`
- `insights-console-browser-final.log`, `insights-query-final.log`
- `insights-http-final.log`, `insights-build-final.log`, `insights-cache-final.log`
- `insights-fixture-console.png` — synthetic full-console UI
- `insights-live-citibank.json`, `insights-live-reconciliation.json`
- `insights-live-banking.json`, `insights-live-banking-summary.json`
- `insights-live-banking-final.json`, `insights-live-cache-hit.json`
- `insights-live-build.json`

Usage, source contracts and limitations are documented in `mentat/INSIGHTS.md`.
Pre-existing working-tree changes were preserved; no commits, Moneyball pipeline
runs, raw-source edits or report rewrites were performed for this addition.

Final deployment check: the full Banking result completed on the running main
application, persisted a verified cache entry, and returned all eleven requested
panels from that completed scope. The core panel payloads were identical before
and after the cache refinement. Forecast status remained unavailable. Loaded and
on-disk build hashes still matched.
