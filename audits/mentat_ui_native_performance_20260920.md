# Mentat UI: native scanning and deeper exploration — 2026-09-20

## Result and scope

Local implementation, not a deployed hosted replacement. No saved report, raw
observation, production evidence database, calibrated Moneyball parameter, or
historical accounting result was regenerated or rewritten in this pass.
Existing unrelated worktree edits were preserved.

Rust now decodes projected workbook tables for Graph receipts and downstream
activity. Two reusable workers avoid per-request process startup. Python remains
the reference/fallback and owns classification and accounting. Binary absence,
staleness or capacity saturation permits fallback; malformed native input fails
closed rather than returning an empty dataset. The built executable and minimal
GNU Rust toolchain are under ignored `mentat/.cache`, not installed system-wide.
Tracked Rust source and Cargo.lock plus `mentat/tools/build_native.ps1` reproduce it.
See `mentat/native/mentat-scan/README.md` for operation and limits.

Graph and geography responses now use bounded, dependency-keyed, single-flight
caches. Keys track source files, boundaries/crosswalks, candidate/committee masters,
and relevant SQLite/WAL changes. Readers receive independent response objects.
Ordered report identities remain in the key: duplicate report inputs must still
fail the overlapping-cycle gate. Updating masters invalidates their underlying
lookup caches as well as the map payload cache.

## Measured, not extrapolated

`mentat/tools/benchmark_native_ui.py`, 50,000 receipt rows plus 50,000 downstream
rows, one synthetic 3,221,309-byte XLSX. Medians of three uncached workbook reads
with warm filesystem and reusable native workers. Final repeat was run after this
task's browser/regression jobs completed; other user processes were not stopped.
Every timed reader result was compared for exact Python-object equality. Raw
samples are retained at `mentat/.cache/ui-performance-20260920/results.json`.

| Read | Reference Python | Rust | Ratio |
| --- | ---: | ---: | ---: |
| Receipt facts | 7,554.522 ms | 566.297 ms | 13.34× |
| Downstream activity | 1,114.903 ms | 401.782 ms | 2.77× |

Already-decoded Graph reaggregation in this small-group fixture was 0.538 ms;
cached view retrieval was 0.337 ms (seven samples). This is a modest warm-path
improvement, not a claimed 13× improvement to every UI action.

The browser explorer built 40 visible table rows from 10,000 searchable saved
relationships in 23.7 ms in the recorded browser run. Map interaction recorded a
2.3 ms median / 5.7 ms maximum **JS transform update**, not whole-frame paint time.
First map open was 1,441 ms including localhost fetches during concurrent tests.
These are fixture measurements, not production latency guarantees. Network/FEC
collection and full Excel report generation have not been Rust-rewritten or
benchmarked here.

## Interaction changes

- PAC maps: 40-row searchable/sortable rankings across all server-returned places,
  replacing the silent client-side top-200 ZIP limit. The existing server ZIP cap
  remains disclosed with omitted ZIP count and amount. No amounts disappear from
  totals. Up to four pinned place/scope comparisons retain their original cycle,
  direction and hidden-kind filter. Overlapping places are explicitly not additive.
- Source-row paging uses the map's exact cycle, separate from an all-cycle pane.
  It clearly says matches are from the current source page, not all donors there.
- Map navigation batches pointer/wheel transforms per animation frame, uses a
  spatial index to cull offscreen ZIP circles, and no longer forces layout in every
  production transform. Selection and layer operations preserve zoom/SVG identity.
- Request/render revisions prevent late responses painting over newer map scopes.
- Graph: full-width/compact explorer, candidate/PAC/route search, signed-value
  sorting, cycle filters, cycle-safe multi-hop navigation, descendant filtering,
  paged relationships and routes, candidate evidence/coverage inspection, and
  filtered CSV export with scope and formula-injection protection. Direction
  toggles reuse the four groups from one payload instead of requesting them again.
- Negative geography remains visible as a net reversal. Invalid net shares are
  unavailable, including when unlocated negative adjustments invalidate a share.
  Candidate/PAC paths remain observed connections, never traced donor dollars.

## Verification and corrected test assumptions

- Rust release build and Rust unit test passed.
- Full Python discovery: **1,078 tests passed**; log retained at
  `mentat/.cache/ui-performance-20260920/python-regression.log`. The runner emits
  an existing unclosed-socket ResourceWarning after successful completion.
- All app JavaScript unit tests: **274 passed**.
- Map browser suite: **17 steps passed**, no page/console errors; checks include
  all-list search, pagination, pinning, exact-cycle source pages, zoom/node identity,
  layers, reconciliation, enlargement and reduced motion.
- Graph browser suites: downstream-measurement integration, 10,000-relationship
  explorer and lazy chart tables passed. Full-width expansion was separately
  verified after visual inspection of the narrow drawer.
- Native/reference parity covers signed outliers, missing amounts, rich/shared
  Unicode strings, cached formulas, projection, errors, row limits, worker reuse,
  parallel reads, fallback, unchanged source bytes and duplicate-report rejection.
- Two legacy contribution tests (discovered twice) initially failed because they
  assumed an unexplained `rejected` status proved a contradiction. The fixtures now
  distinguish a bare heuristic rejection from documented adjudication. A new
  counterexample retains an observation with conflicting ZIP metadata as provisional,
  with zero certified-unique support. Production accounting code was not changed
  to satisfy the old mistaken expectations; documented rejections still exclude.
- Console template parity and whitespace checks passed. Preview screenshots are
  under `mentat/.cache/ui-performance-20260920/screenshots` and use synthetic data.

## Skills and Higgsfield

The project change-control and failure-archaeology skills kept this work away from
calibrated Moneyball changes and production regeneration. The Higgsfield skill was
used to create a synthetic, evidence-first Mentat UI concept (job
`d92f10ef-53be-4758-a92a-1d6b6b7ed648`); no private source data was uploaded.
Its website-builder workflow creates a separate hosted application, so it was not
used to replace or deploy this existing local app. No new hosting account/project
was created. The actual interaction changes are repo-native JavaScript/CSS/Python
with the Rust decoder described above.

Start/restart Mentat to load the new backend, then reload the UI. Do not interrupt
an active collection merely to refresh the app. No live production server was
restarted by this task.
