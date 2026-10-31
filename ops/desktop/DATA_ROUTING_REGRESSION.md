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
   variations. A configured workspace-v1 feed now also takes precedence for
   used/custom directories; limited builds without that channel retain their
   previous local-workspace behavior.
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

## Build configuration follow-up

The release 1.0.40-r31 package had no `desktopWorkspaceData` setting. The common
builder also defaulted to disabled and ignored Mentat even when workspace-v1
was explicitly requested. This prevented the paired report/model receiver
from being selected, independently of the route defects above.

Normal standalone GitHub builds for Melange and Mentat now default to their
matching `desktopWorkspaceData: {<app>: 'workspace-v1'}` channel. An explicit
`DESKTOP_WORKSPACE_DATA_MODE=disabled` remains supported for limited or offline
builds. Managed builds, Terrier, Windows sign-in, each app's binary update
repository, and the separate `desktopPublicData` setting are unchanged. Selecting
a local data directory does not disable a configured workspace-v1 feed. Original
directories and user records remain in place; the paired reader binds separate
verified inputs before the backend is shown.

For Melange, this channel stages the signed dashboard, graph, payroll, industry,
and staffer-analysis workspace at startup, then renders the native dashboard
from the verified snapshot. The current public snapshot's asset payload is about
2.21 GiB, with about 5.60 GiB of archive expansion; first launch therefore needs
several GiB of free disk and a working GitHub connection. Later launches reuse
the verified cache. It does not load the full archive payload into memory.

For normal builds, `builder.cjs`'s `extraMetadata.desktopAppConfig`, consumed
by `build-native.cjs`, is authoritative. The historical per-release
`prepare-client.cjs` overlay copies `previous.desktopAppConfig` from an older
ASAR and therefore bypasses the new builder default. Any custom overlay
release must deliberately adopt the reviewed builder configuration and
inspect the final packaged metadata; copying the 1.0.40-r31 configuration
would retain the missing feed. This change does not modify old installers.

The builder regression matrix covers each application, standalone/managed
access and unset, empty, disabled, workspace-v1 and invalid modes. It also
passes the normal Melange build metadata into the real main-process dispatch to
confirm the workspace receiver is selected before renderer reveal. Run:

```text
node --test ops/desktop/client/tests/builder-update-source.test.cjs
```

All **3 builder tests passed**, including the 30-case workspace mode matrix.

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
performed for this candidate. Cross-reference still requires separate local
reconciliation evidence and is not supplied by the signed report feed. Activity and estimate modes
retain their native evidence availability checks. The graph adapter retains
native calculation caching, but does not add the ordinary server's HTTP ETag
wrapper or access telemetry; the renderer accepts uncached responses.
`graph_schema(stamp)` retains the native 32-entry cache, so repeated catalog
reads stat the fixed workbook set without repeatedly decoding sheet metadata.

These changes do not establish that every Mentat feature is backed by GitHub.
Future source edits require another standard inventory refresh and appropriate
integration checks before packaging.

## Expected client disconnects

Native Mentat commit `9dd6d3db22a09ef2129f4b4027bc52704805881c`
(parent `2b623be182881039e974940b652fab7d39a87ce6`) catches broken pipes,
resets and aborted connections before the broad native GET error handler can
try sending a second response. Its six focused tests passed on independent
review; ordinary validation/I/O errors and successful access logging remain.

Workspace routes write during `guarded_handler.parse_request`, before native
`do_GET`. The shared desktop adapter therefore also catches those same three
exception classes around `handle_one_request`. It closes the canceled
connection without sending another response. All other exceptions retain
their existing behavior. The existing native guard is still needed to stop
its own broad error handler attempting a second write.

```text
python -B -m unittest test_desktop_disconnect test_desktop_backend -q
```

**35 tests passed**: four new boundary tests and 31 existing backend tests.
The new tests exercise actual stdlib request parsing, intercepted workspace
responses, native responses, all three expected disconnect classes, premature
request-read cancellation, and propagation of generic I/O/validation errors.
The original adapter reproduces four disconnect errors across the two
regression test methods. Native-source tests are separately run with:

```text
python -B -m unittest discover -s mentat/tests -p test_graph_client_disconnect.py -v
```

The public native checkout lacks some declared program sources (first missing
input: `mentat/forecast/anchors/build_giving_anchors.py`). Inventory generation
therefore used an isolated staging of exactly 230 source files, 7,898,582
bytes, from the assembled 1.0.39 runtime. Every file matched its existing size
and SHA-256 before copying. Only the reviewed native `mentat/app/server.py`
was overlaid. The standard `refresh_module_inventory.outputs` generator was
run for shared bootstrap descriptors, then for Mentat against that staging.
This final refresh changes only `desktop_backend.py` in shared bootstrap
contracts and `mentat/app/server.py` in Mentat public/workspace contracts;
all other source descriptors are preserved. Both generated inventories are
stable on repeat generation, and the 14 inventory tests passed again.

Release assembly must include the reviewed native commit as well as this
common-client branch: the inventories now pin its server bytes. No runtime,
installer or release was produced by these integration changes.

## Advanced comparison integration

`/api/comparison` and `/api/comparison-flows` now select the same fixed signed
workbooks as Graph and invoke the unchanged native `comparison_subjects` and
`comparison_flows` readers. Returned workbook hashes must match signed
receipts. Missing committee-activity evidence retains the native
`issues`/`unavailable_activity_cycles` output; no evidence is synthesized.
Hosted person-selection refusal and person-subject redaction are preserved.

The access attributes are available before the workspace route executes:
native `Handler.access_cfg` is initialized on the class and set by `main`
before server creation. `AccessMixin.parse_request` authenticates and assigns
`access_user` before returning to the desktop adapter's `parse_request`.

The reader regression command above now passes **9 tests**, including actual
native subjects/flows parity, invalid selectors/hash changes and the native
person-redaction helpers. Both comparison endpoints fall through on the
previous adapter. The standard bootstrap-only inventory refresh was repeated
and reports no drift. This completes Advanced comparison routing; the
Cross-reference tab still needs its separate saved reconciliation run/digest.

## Used profiles, native transport and retry scope

Follow-up review of Claude commit `41631706884b93cd848da60f18615f3f2098877f`
confirmed two remaining startup selection issues. The configured workspace-v1
branch now precedes local-cache detection for both supported applications.
Explicit disabled builds keep their existing limited/local selection; no new
per-profile override was invented. Production downloads select the existing
Electron network adapter after `app.whenReady()`, allowing system proxy/PAC
resolution. TLS, fixed-host redirects, anonymous requests and signed-data
verification remain enforced; unresolved proxy authentication still defers.

The reported `startupRetry` ReferenceError came from a test that extracted
`launchAuthorized` without its enclosing declaration (and omitted
`windowsAuthentication`). The production declaration was already in the same
lexical block before any ready/IPC launch. Its code was not changed. The owner
resume test now executes the complete main module with an Electron host double,
its real retry coordinator, and the original lifecycle implementation. A new
whole-main regression covers deferred startup/retry, network readiness, and
configured feeds with populated custom directories while preserving user files.

The following **113 tests passed** (with ordinary client dependencies available):

```text
node --test ops/desktop/client/tests/full-main-startup.test.cjs ops/desktop/client/tests/terrier-owner-resume.test.cjs ops/desktop/client/tests/local-workspace.test.cjs ops/desktop/client/tests/network-transport.test.cjs ops/desktop/client/tests/main-module-lifecycle.test.cjs ops/desktop/client/tests/main-module-preflight.test.cjs
```

A separate real Electron **44.7.2** run of
`tests/network-transport-electron.cjs --package=<prepared-package.json>` used an
isolated temporary profile and the actual native adapter. Both public and
workspace signed pointers verified, and their 3,937/4,766-byte manifest hashes
matched. System proxy resolution completed. This checks actual metadata
transport, not a corporate proxy deployment or full data activation. No data
payloads were downloaded in that check. Full packaged application/data/UI
acceptance remains required for the revised artifact.

The 1.0.39 client repair commit `6625901e0` remains an ancestor. The older-instance
replacement, junction-aware roots, and installer-cleanup implementation are
preserved. The standard bootstrap inventory check reports no drift: this
follow-up changes client startup and its tests, not native runtime source bytes.

## Terrier sleep/wake with an active signed district

The Windows sleep path retained the running backend, but warm Runtime.start
required the already-consumed one-use district launch capability again. This
raised the generic application verification/startup failure before authorizing
the resumed Windows session. It was not duplicate-instance replacement.

Runtime now retains private authority only after native active-health validation
and protected activation commit. A warm start requires the same child object,
generation, exact configuration, physical roots, account, token, installed
program fingerprint and authenticated native district health. Stop and matching
child exit clear that record. Every new backend still requires a fresh one-use
capability; the original capability and file handles are closed normally.

The retained snapshot is intentionally exact: native PreparedSnapshot.health
returns its immutable self.key and rejects an active snapshot different from
that key. Public and paired workspace bindings already retain their own active
child authority; those paths were not changed.

97 focused tests passed with ordinary client dependencies available:

```text
node --test ops/desktop/client/tests/district-warm-runtime.test.cjs ops/desktop/client/tests/full-main-sleep.test.cjs ops/desktop/client/tests/terrier-owner-resume.test.cjs ops/desktop/client/tests/full-main-startup.test.cjs
node --test ops/desktop/client/tests/runtime-configuration.test.cjs ops/desktop/client/tests/runtime-stop.test.cjs ops/desktop/client/tests/district-runtime-input.test.cjs ops/desktop/client/tests/district-runtime-wiring.test.cjs ops/desktop/client/tests/module-runtime-boundary.test.cjs ops/desktop/client/tests/workspace-data-startup.test.cjs
```

The first command passed 34 tests; the second passed 63. The 15 new tests
reproduced four failures against unmodified dea7b30f3ed5c3e480aad1225e886eb40eca846f
by setting LIFECYCLE_BASELINE_ROOT to that checkout's client directory. They
cover delayed suspension drain, rapid sleep/lock/resume/unlock, changed Windows
identity, stale settings/child, native health mismatches, installed-program
changes, stop/exit requiring fresh authority, and stop during warm health.

These execute real Runtime, one-use district binding, Windows gate and complete
main lexical scope. Host process creation, native program census, HTTP, Electron
windows and power events are doubles. The exact production power-registration
block is replayed in that scope. They do not establish a packaged GUI pass or
physical work-PC sleep/resume verification. No installed app or Windows session
was stopped, locked or suspended during these tests.
