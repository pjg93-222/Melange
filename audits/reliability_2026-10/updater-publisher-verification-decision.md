# Updater publisher verification: thumbprint pinning

Date: 2026-10-23. Branch: `infra/shared-service-reconcile` (Task 4). Ships to installations with the Task 5 desktop build.

## Decision

The desktop updater accepts a Windows installer only when the thumbprint of the certificate that signed it is on an
allow-list carried inside the Ed25519-signed release manifest (`publisherThumbprints`). The current list is
`["0EBC9AD04E929CDD731EDB5D278A4143BC3D3D30"]`, the release certificate already pinned by `publisher-trust.cjs`.

- Windows trust status (`Valid`) is not required, and no certificate store is consulted. A self-signed release root that
  is not in the user's Trusted Root store reports `UnknownError` or `NotTrusted`, and it still names its signer.
- The statuses `NotSigned` (2) and `HashMismatch` (3) are refused even when a thumbprint is reported. An installer with
  no signer certificate is refused.
- Tampering is still caught by the existing gates, which this change leaves alone: the download stream and every cached
  file are checked against the manifest's size, sha256 and sha512 (`trust.cjs` `downloadVerified` and
  `verifyPackageFile`). Those checks run before the signature check on every activation path.
- Replay and downgrade are still refused by the existing version and sequence high-water checks in `verifyEnvelope`.

## Why `verifyUpdateCodeSignature` stays disabled (`main.cjs`)

electron-updater's own check runs `Get-AuthenticodeSignature`, requires `Status Valid` (so the release root must be in
the user's Trusted Root store) and matches a subject string. Requiring the store is what the owner ruled out. The check
is replaced, not dropped: `updater.cjs` `verifyNativeFile` calls `native-signature.cjs` (the default
`verifyNativePackage`; `main.cjs` no longer passes the former no-op) on the staged file at preparation and again on
the cached file and each native file just before `quitAndInstall`. `builder.cjs` keeps `verifyUpdateCodeSignature:true`
so `publisherName` stays configured for `updater.cjs` `nativeTrust`.

## Mechanism and files

| File | Change |
|---|---|
| `ops/desktop/server/desktop_admin.py` | `PUBLISHER_THUMBPRINTS` constant; LAN `publish()` writes `publisherThumbprints` for win32; `validate_manifest` checks the field when present (1-8 entries, 40 uppercase hex); the publish gate `verify_release_gates` also requires the staged installer's signer thumbprint to be in the manifest's list, so a manifest that every client would refuse is never signed. |
| `ops/desktop/packaging/github_release.py` | GitHub release manifests carry `publisherThumbprints` inside the signed payload. |
| `ops/desktop/client/trust.cjs` | `verifyEnvelope` validates the field when present. |
| `ops/desktop/client/native-signature.cjs` | Reads `SignerCertificate.Thumbprint`; the decision is thumbprint against the allow-list, plus the exact installer path. A missing allow-list is a refusal decided before PowerShell runs. "No verdict" failures keep the `SIGNATURE_CHECK_UNAVAILABLE` code (retry without backoff), as before. |
| `ops/desktop/client/updater.cjs` | Passes `manifest.publisherThumbprints` to `verifyNativePackage`. |
| `ops/desktop/client/main.cjs` | Removes the `verifyNativePackage:async()=>{}` no-op so the real check is the default. Comment on why electron-updater's chain check stays disabled. |

## Tests

`node --test tests/*.test.cjs` in `ops/desktop/client`: 344 passed, 0 failed (335 before the change).
New file `tests/publisher-thumbprint.test.cjs` drives the real updater and the real `native-signature.cjs`; only the
`Get-AuthenticodeSignature` answer is simulated.

| Case | Test | Result |
|---|---|---|
| Positive: pinned signer, root not trusted by Windows | `a signer thumbprint in the manifest allow-list installs, even when Windows does not trust the self-signed root` | pass |
| Unsigned installer | `an unsigned installer is refused` | pass |
| Wrong publisher | `an installer signed by a different publisher is refused, whatever its Windows status` | pass |
| HashMismatch status | `a HashMismatch Authenticode status is refused even with the pinned thumbprint` | pass |
| Tampered after signing | `an installer tampered with after signing is refused by the signed hash gate before any signature check` | pass |
| Replayed older signed build | `a replayed older signed build is refused (version and sequence high-water)` | pass |
| Legacy manifest | `a legacy manifest without publisherThumbprints is refused at activation (fail closed)` | pass |
| Launch-time install | `a staged update whose signer no longer verifies is refused at launch and the current version starts normally` | pass |
| Field validation | `publisherThumbprints must be a non-empty list of 40 uppercase hex digits when present` | pass |

Each refusal case also asserts that the running version keeps working: `check()` resolves, `quitAndInstall` is never
reached, `activateAfterClose()` returns false, and the installed record still names the current version.
`tests/native-signature.test.cjs` covers the verdict rules and the no-verdict codes. `tests/updates-and-settings.test.cjs`
now asserts that `main.cjs` passes no `verifyNativePackage:` override.

Python: `ops/desktop/packaging/test_github_release.py` passed 24 of 24 with `NODE_PATH` set to the locked client
dependencies. That includes the unchanged-client acceptance runs that feed the new manifests to `trust.cjs`, and the new
`test_an_installer_signed_outside_the_thumbprint_allow_list_is_never_published`.
`ops/desktop/server/test_desktop_admin.py` passed 59 of 59.

## Legacy manifests (fail closed)

A signed manifest without `publisherThumbprints` can still be read: recovery baselines and high-water marks keep
working. Its installer is refused at activation with "The signed release manifest names no publisher thumbprint". So:

- An installation running this client does not install any release published before this change. Task 5 must ship
  the next release from `github_release.py` or `desktop_admin.py publish` at this branch or later, so its manifest
  carries the field.
- A rollback to a release whose manifest predates this change is refused too. The rollback targets that remain are
  releases published with the field.
- `github_release.py` refuses to re-prepare an already-prepared sequence with different metadata, so the first release
  with the field needs a new sequence. That is normal for every release.

## Rotation

1. Add the new certificate's thumbprint to `PUBLISHER_THUMBPRINTS` in `desktop_admin.py`, keeping the old one.
2. Publish releases signed by either certificate. Every client already accepts both, because the allow-list travels
   in each signed manifest.
3. Once no supported release is signed by the old certificate, remove its thumbprint.

The Ed25519 manifest keys rotate separately through the existing `keyTransition` envelopes (`trust.cjs`
`applyKeyTransitions`).
