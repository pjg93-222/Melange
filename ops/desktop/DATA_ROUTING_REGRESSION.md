# GitHub data routing repair — 2026-10-31

This candidate starts from source commit `5e095b3c6`, with default-root startup
repair `d8cb691ba6f05f165644c70592678bedf421fbdf`. The native route regression
uses the staged Mentat 1.0.39 runtime; its original `workspace_mentat.py` is
25,636 bytes, SHA-256
`f3c5705e4204d5137e03689c3aabe3a6c4c4cdd44ed5b653cd3f2137c82d10c5`.

Three defects are addressed:

1. Files created in the default desktop data directory could satisfy the local
   workspace heuristic and prevent any GitHub data startup. The default root
   now retains GitHub startup, including physical aliases and Windows case
   variations. Custom local directories retain their previous behavior.
2. Signed GitHub report downloads were exposed by `/api/report-sources`, but
   `/api/graph-catalog` and `/api/graph` fell through to the empty local report
   folder. Both now select signed workbooks and invoke the existing native
   graph reader. Numerical calculations, workbook hashes, native freshness and
   registry build stamps are retained; local console directories are unchanged.
3. `/api/report-data` passed a `Path` to a reader requiring a file-stamp tuple,
   raising `TypeError: 'WindowsPath' object is not subscriptable`. It now passes
   `stamp(path)`, preserving the reader's cache identity and the UI's
   `id`, `index`, `sheet` and `header` parameters.

Application binary updates and signed analysis-data downloads are separate
mechanisms. Successful binary updating alone does not establish data readiness.

## Evidence

From `ops/desktop/packaging`, with `MENTAT_TEST_RUNTIME` explicitly set to the
assembled runtime directory containing `bootstrap` and `sources`:

```text
python -B -m unittest test_workspace_graph_routes -v
```

**6 tests passed** against the actual 1.0.39 graph, worksheet, freshness and
snapshot-registry readers. Tests cover an empty local report folder, matching
catalog/report indices, native numerical parity, filters/slugs, bad selectors,
signed-hash mismatch, worksheet selection and unrelated-route preservation.
Without an explicit runtime, discovery reports an explanatory skip. The test
substitutes an already-installed binding's verification method, so it is not
proof of an entire signed download/handoff or desktop launch.

Using `MENTAT_TEST_BINDING` to select the preserved original module reproduces
both defects: the graph-catalog test fails on route fallthrough; the worksheet
test raises the WindowsPath TypeError. The startup change separately passed
**62 client tests**; its review found no blocking issue.

Client command from the repository root, with `NODE_PATH` set to the staged
1.0.39 client's `node_modules` directory:

```text
node --test ops/desktop/client/tests/local-workspace.test.cjs ops/desktop/client/tests/main-module-lifecycle.test.cjs ops/desktop/client/tests/module-runtime-boundary.test.cjs
```

The standard inventory tool was run from the repository root:

```text
python -B ops/desktop/packaging/refresh_module_inventory.py --bootstrap-only --write
python -B ops/desktop/packaging/refresh_module_inventory.py --bootstrap-only
```

The second invocation reports no drift. Both Python and client inventories
were regenerated together. All source descriptors remain byte-for-byte equal
to their prior declarations. Shared bootstrap references update Melange,
Mentat and Terrier fingerprints. The tool also reconciles a preexisting
Melange `mentat_layout.py` descriptor with the current helper, which already
matched the Mentat descriptor. No source or data-channel schema was changed.
`test_refresh_module_inventory` and `test_module_application_inventory` passed
**14 tests**. The build copies these inventories; it does not automatically run
this refresh tool.

## Remaining scope

No installer build, publication, work-PC test or full desktop acceptance was
performed for this candidate. Comparison and cross-reference routes still
use local-source paths and are separate gaps. Activity and estimate modes
retain their native evidence availability checks. The graph adapter retains
native calculation caching, but does not add the ordinary server's HTTP ETag
wrapper or access telemetry; the renderer accepts uncached responses.
`graph_schema(stamp)` retains the native 32-entry cache, so repeated catalog
reads stat the fixed workbook set without repeatedly decoding sheet metadata.

These changes do not establish that every Mentat feature is backed by GitHub.
Future source edits require another standard inventory refresh and appropriate
integration checks before packaging.
