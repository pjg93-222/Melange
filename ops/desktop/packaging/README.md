# Independent native desktop applications

The client builds three separate applications. Set `DESKTOP_APP_ID` to `melange`, `terrier`, or `mentat`; each has its own application ID, settings, protected enrollment credential, local state, backend, and update history. Docker is not required on recipient computers.

The source adapter calls the real local services. It wraps the existing HTTP handler or Django WSGI application with a launch-token check before any route executes. It does not turn off hosted security or replace full applications with their hosted read-only images. Existing application routes, Host/origin checks, Mentat's token, and Django CSRF remain active.

## Native developer build

Use Python 3.12 on the target OS/architecture. Install the application's original pinned requirements and PyInstaller 6.22.3 in a dedicated build environment. Run:

    python ops/desktop/packaging/build_runtime.py --app terrier --source PATH_TO_TERRIER
    cd ops/desktop/client
    npm ci
    npm test
    # PowerShell: $env:DESKTOP_APP_ID='terrier'
    # macOS: export DESKTOP_APP_ID=terrier
    npm run build:dir

By default, `npm run build` makes NSIS installers on Windows, and DMG/ZIP artifacts on macOS. Build Mac packages on a native Mac, including their native geospatial and scientific libraries. The current `.github/workflows/desktop-windows.yml` and `release_from_main.py` paths produce NSIS installer assets, not the directory ZIP update channel.

For signed Windows applications that run from an extracted folder, use the
[directory ZIP build and migration workflow](../DIRECTORY_DISTRIBUTION.md).
Directory installations require future signed ZIP manifests; an NSIS-only release
from `release_from_main.py` does not update them. The existing native build default
remains available for clients that have not migrated. A source push does not
build, sign, publish or enable ZIP updates. The exact current-version ZIP and
its authorized signed manifest must first be published as the recovery baseline
before higher automatic updates, after the required release gates pass.

No user database, credentials or source dataset should be supplied as a runtime resource. Each installed app asks for its independently prepared, reviewed data directory. Terrier migrates only its installation-owned accounts database. Source staging rejects the Pocket template that contains a historical data snapshot rather than silently shipping it.

`runtime-status.json` lists missing native components. Full Mentat requires R plus its exact package library and any used Node/Chromium helpers; full Melange compute requires LibreOffice. Providing the Python backend alone is not a claim that these operations have passed. The native-runtime directory must contain approved redistributable builds for the target architecture. No successful release receipt is synthesized by this builder.

## Security and updates

The default binary update source is public GitHub Releases; see `../GITHUB_RELEASES.md` for committed-source routing, signed three-app release preparation, publication, and signing requirements. Binary updates do not require feature approval. The optional custom publisher accepts an explicit pairing bundle for this app and a configured HTTPS origin; its bundle pins TLS and Ed25519 keys, and discovery/enrollment cannot replace those roots. Device bearer credentials use Windows Credential Manager or macOS Security.framework Keychain through the bundled native helper, which receives secrets over stdin. Pinned trust metadata uses Electron safeStorage. Custom-publisher requests require TLS pin and certificate-validity checks and refuse redirects. The Mac Keychain path still needs a signed native-build acceptance run.

Updates first verify signed metadata, app/platform/architecture, installed version, monotonic sequence, package size, SHA-256 and SHA-512. Data schema versions other than 1 are refused until migration and backup acceptance exists. Trusted old keys must sign key transitions. In native NSIS mode, a verified artifact is then exposed to electron-updater through an ephemeral, token-path loopback feed; the native updater never receives publisher credentials. Current 1.0.20 Windows native checks enforce the fixed certificate thumbprint `0EBC9AD04E929CDD731EDB5D278A4143BC3D3D30`, not subject text alone. Directory mode instead requires the signed ZIP manifest and independent pinned publisher proof, verifies the complete archive inventory, and relaunches a verified version folder after normal close. Its separate ZIP cache and recovery state preserve existing profiles and data; see the [directory workflow](../DIRECTORY_DISTRIBUTION.md). No Windows trust-store import is required by these pinned package checks. Approved updates are scheduled for ordinary application exit, after its owned backend stops; OS shutdown/logoff events defer activation. Checks run on launch, every 15 minutes, and resume/unlock. Successful version activation is reported on the next launch. Local data and writable state are separate from replaced application binaries. Native installation, interruption recovery, previous-package recovery and network-reconnect activation have not yet passed acceptance.

Terrier desktop write requests have an additional per-installation, HMAC-chained audit of method, attempt/outcome and district. The audit omits request paths, queries, bodies and record IDs. Its integrity key is local, so it does not protect against an attacker who already controls the same OS account. Existing hosted auditing and authorization are unchanged.

Publication additionally requires real native acceptance tests, secret/data scans, dependency/security and redistribution checks, and an OS-signature receipt bound to the exact package hash. Unsigned developer artifacts are not publishable. Windows signer and Apple Developer/notarization credentials are external prerequisites; never put private signing keys in an installer.

## Remaining acceptance work

- Exercise every full local feature with approved synthetic or reviewed fixtures on each native target. Mentat's path relocation is a compatibility adapter and needs subprocess/index/collection acceptance; it is not yet a general replacement for source-level portable-path seams.
- Bundle and exercise R, Node/Chromium and LibreOffice features. Verify numeric parity under the project's existing standards.
- Verify signed Windows and Mac update installation, crash recovery and data-preserving schema migrations on clean recipient machines. The trust and transport tests alone do not prove native installation succeeds.
- Review source staging with the existing release security gate. The earlier private-container licence acceptance does not cover redistributed native runtimes or datasets.
