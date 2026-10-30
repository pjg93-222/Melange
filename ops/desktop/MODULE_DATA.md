# Verified module-data foundations

These modules provide a separate owner-only GitHub data transport for Melange
and Mentat. They are foundations: `main.cjs` does not enable this provider, and
these source tests do not establish a published dataset, installed feature, or
complete application preload.

The ordinary runtime launcher rejects any own `ownerGitHubModuleData` setting
before authorization, storage preparation, or process creation, regardless of
the marker's value. A source descriptor is not a native launch capability. Normal
marker-free Melange and Mentat configurations retain their original data and
state roots. No native module-data launch capability is enabled by this guard.

Binary updates, Terrier district data, and recipient dataset access retain their
existing protocols and protected state. This provider uses the existing per-app
verification keys with the distinct `melange-public-module-data` and
`mentat-public-module-data` signature purposes. It never sends account credentials
to GitHub.

## Signed inputs and cache

Each compiled app repository has a fixed `docs/desktop-data/current.json` pointer.
The 1.0.33 transport reads that fixed raw-CDN pointer, verifies its signature and
sequence, and verifies the public prerelease and release-tag/commit binding when
accepting a new pointer. Unchanged pointers reuse only a protected, owner/profile-
bound accepted record, after rechecking the exact signed envelope under current
compiled keys and the hash-bound cached manifest. Loose cache files, a high-water
alone, another owner, or a different signing epoch cannot supply that attestation.
Older protected journals remain readable; they already recorded the result only
after the earlier release/tag checks. This removes steady anonymous REST polling,
while a first acceptance still performs bounded GitHub release/tag queries.
The exact manifest bytes are then verified. The manifest
selects compiled kinds and roles; it cannot supply filesystem paths, commands,
executable content, downloaded adapters, or arbitrary URLs.

Logical role files contain ordered raw segments of at most 1 GiB each. Segment
hashes and the concatenated whole-file hash must match. Limits are 32 segments
per role, 256 per catalogue, 32 datasets, a 2 MiB manifest, and a compiled total
budget no greater than 32 GiB. A compiled reader can decode a fixed data format
from an opaque role; there is no generic archive extraction.

Segment transfers have a 30-second idle limit and a separate signed-size-aware
total budget, between two and thirty minutes per attempt. Useful progress
refreshes the idle limit; awaiting local disk writes does not count as network
idleness. Partial files remain bounded and exclusive, and resume requires exact
206 status, remaining Content-Length, Content-Range, identity encoding, and the
final segment and whole-role hashes. Cancellation and integrity failures never
promote a partial file. Recognized network/proxy/rate-limit errors are explicitly
marked for the native startup retry path; certificate, storage, source, and hash
failures cannot acquire that retry authority.

The cache is native-derived and separate from original workspaces, account state,
and application files. Downloads use validated exclusive partial files and
retained write handles. Snapshot closure, regular-file identity, hashes, and
actual typed readers are checked before use and again before activation.
Matching original inputs may be copied after stable verification; originals are
never hardlinked or rewritten.

The independent `github-module-state` journal distinguishes accepted, staged,
and active revisions. Its sequence cannot decrease or equivocate. Offline use
requires a previously activated snapshot that revalidates completely, and is
allowed only for recognized network failures. Invalid signatures, scope, hashes,
or rollback cannot trigger an older-data fallback.

## Native integration contract

`GitHubModuleController` obtains original saved settings and owner authorization
inside its serialized work. It exposes sanitized status and staging over fixed,
argument-free IPC. Preparing or committing a candidate is native-only.

`ModuleDataTransition` holds an exclusive startup lease across preparation,
authenticated backend health, and the entire protected active-record write.
Candidate identity, selected configuration, access generation, runtime, and
healthy child must remain bound. Invalidation aborts work and drains outstanding
commits before teardown. A staged revision never replaces an open backend or
overrides calculation, close-confirmation, or unsaved-work guards.

`validateModuleBinding` independently checks the cached signature, descriptor,
manifest, compiled roles, complete snapshot closure, hashes, and native reader
probes using read-only handles. The caller must also require the original owner's
authorization and the native prepared-candidate capability. Settings and renderer
requests cannot submit an `ownerGitHubModuleData` marker.

Original `dataDirectory` and connection fields remain unchanged. The effective
configuration adds only the strictly checked native source descriptor. Read-only
input aliases must be separate from account, console, report-output, identity,
waiver, and other writable user-state roots.

The Python `module_data_launch` bridge rechecks that native descriptor and its
cache, then constructs scoped actual readers. Its `native_verified` argument is
an internal caller assertion after native signature and owner checks, never a
downloaded field or proof of authorization by itself. The bridge reports whether
signature authority came from native JavaScript or an additional trusted Python
callback. It does not independently establish owner access or journal high-water.

A failed raw-host connection may use GitHub's Contents API RAW-media response for
the same compiled repository, ref and pointer path. Only explicitly typed
transport timeouts or unreachable connections enable this alternative. TLS,
HTTP404, framing, schema, signature, hash and rollback failures do not. The
returned bytes still pass the same pinned signature, public-release/tag and
owner-bound high-water checks. API-origin cooldown does not block a recovered
raw host or immutable assets. Normal successful raw checks use no REST calls;
this availability fallback consumes the anonymous API quota and reports its
limits honestly. Previously accepted data may be reused only under the existing
verified offline policy.

## Implemented component contracts

| Kind | Immutable inputs |
| --- | --- |
| `melange.staffer-graph-core.v1` | Graph receipt and verification, nine graph objects, upstream spine and office index |
| `melange.payroll-identity-core.v1` | Config, evidence, and five receipt-bound source objects |
| `mentat.aggregate-forecast-core.v1` | Aggregate model selection and pointers, two models, anchors and receipt, five authoritative workbooks |

Each probe reports `completeKind: true` and `fullApplication: false`. Actual
program readers operate through closed input aliases over generated test data;
validation does not run forecasts. Mentat's original waiver and panel-state
access is preserved.

These kinds do not cover all Melange dashboard inputs or all Mentat report and
contribution-analytics inputs. Data-bearing HTML/JavaScript requires a reviewed
application-template and typed-data split. Report lineage and analytical-index
relocation need their own contracts. The production factory must remain disabled
until the intended required-kind set and reader bindings are complete.

The producer-only `module_data_islands` helper accepts reviewed template bytes,
closed slots, and explicit typed schemas. All bytes outside those slots must
match the compiled template. Its explanation adapter accepts one exact passive
markup grammar, converts it to a plain text document, and regenerates escaped
markup through compiled code. It performs no file or network I/O and has no
enabled production page contracts. This is not a general HTML exporter or proof
that the current dashboards' complete inputs have been mapped.

Before enabling a release, review its exact data-role manifest and provenance,
finish native runtime/UI integration, test the actual built artifact, and verify
the signed installed app, owner startup, GitHub/cache state, and account
preservation. No source test or data tag alone proves deployed readiness.
