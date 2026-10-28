# Windows directory ZIP distribution

See the [engineering handoff](INSTALLER_FREE_HANDOFF.md) for the exact tested
candidate baseline, migration/channel requirements, evidence limits and
coordination with concurrent development.

The `directory-zip` build contains the complete signed Electron application and
its private runtime. It has no NSIS launcher, installer, uninstaller, extraction
plugin, elevation step, or legacy `portable.marker`. The user extracts the ZIP
once and opens the application executable. Future updates use authenticated ZIPs.

## First use

Extract the complete archive into the normal Downloads location, for example:

```text
Downloads\MelangeApplications\Melange-1.0.20\Melange.exe
Downloads\MelangeApplications\Mentat-1.0.20\Mentat.exe
Downloads\MelangeApplications\Terrier-1.0.20\Terrier.exe
```

Keep all files beside the executable. Launching from this managed application
root lets startup and shortcut registration use the supported layout. An old
NSIS installation needs this initial manual transition; its old updater does not
understand the new ZIP release channel. Existing application data is separate
from the versioned program directories and must be preserved.

Before the first ZIP launch, choose **Quit** from the old application's tray icon
or menu. Closing its window can leave it running in the background; that process
can receive the new launch through the shared single-instance lock. Then open the
executable inside the new version folder. Keep the existing profile and data;
manual uninstallation is unnecessary. The pinned archive and publisher checks
do not require importing a certificate into Windows trust stores.

ThreatLocker policy still applies to the application, Python/R/Node runtimes,
native libraries and data writes. Removing NSIS removes its execution and plugin
requirements; only the organization's IT administrator can approve remaining
denials. A local valid signature does not establish recipient policy approval.

## Building a local candidate

`packaging/build_directory_release.py` exports explicit local Git commits. It
uses one frozen Melange desktop client/tooling commit for all three applications;
each backend is exported from its own repository commit. The source and tooling
commits are recorded separately. Uncommitted checkout changes are never copied.

Create a JSON specification with this structure, using full local commit IDs:

```json
{
  "schemaVersion": 1,
  "version": "1.0.20",
  "tooling": {"path": "C:/checkouts/Melange", "commit": "FULL_FROZEN_MELANGE_COMMIT"},
  "apps": {
    "melange": {
      "source": {"path": "C:/checkouts/Melange", "commit": "FULL_FROZEN_MELANGE_COMMIT"},
      "runtime": "C:/reviewed-runtime-inputs/melange"
    },
    "mentat": {
      "source": {"path": "C:/checkouts/Mentat", "commit": "FULL_FROZEN_MENTAT_COMMIT"},
      "runtime": "C:/reviewed-runtime-inputs/mentat"
    },
    "terrier": {
      "source": {"path": "C:/checkouts/Geo", "commit": "FULL_FROZEN_GEO_COMMIT"},
      "runtimeSizeBaseline": "C:/reviewed-runtime-inputs/terrier"
    }
  }
}
```

With `runtime`, dependency reuse requires readable provenance and byte-identical
requirements at the old and new commits. All backend sources and bootstrap files
are regenerated from the frozen inputs. Without `runtime`, the command makes a
fresh CPython 3.12 venv using the app's Windows wheel constraints with required
hashes. Terrier's frontend is rebuilt from its frozen source and npm lock.
`runtimeSizeBaseline` only measures disk-space needs for a fresh build; none of
that old runtime's files are reused. Each heavy phase checks free space before
allocation, including a conservative reserve for concurrent runtime copies,
Electron/npm output and a worst-case uncompressed ZIP.

```powershell
python ops/desktop/packaging/build_directory_release.py `
  --spec C:/build-inputs/directory-spec.json `
  --root C:/short-build-root `
  --artifacts C:/candidate-output/installer-free `
  --python312 C:/Python312/python.exe
```

The default command validates inputs. Add `--build` to build locally. Use a fresh
short scratch root, at most 70 characters, outside the output directory. Failed
runs retain their logs; a retry generally uses a new scratch/output root. If a
controller failed immediately after successfully producing the ZIP, use
`--resume-packaged melange` (or the relevant app) with its original root/spec.
This limited continuation binds saved source inventories, ZIP hashes and signing
payload before creating proof and rerunning independent final verification. It
does not rebuild the app. Queued apps can then use a new scratch root with the
same frozen source/tooling commits. Controller commit/hash evidence is recorded
separately from program source provenance. The command keeps
at least 32 GiB free, builds apps sequentially, and removes only its owned scratch
directories after preserving the package and evidence.

The build uses the pinned certificate in `CurrentUser\My`; no private key is
exported. Directory signing skips NSIS tools, signs the app tree, preserves valid
vendor signatures and records a fresh verification of each native binary. The
ZIP packager preserves all application bytes, creates the complete file inventory
and emits canonical publisher-proof payload bytes. The final verifier extracts
the ZIP again, checks complete inventory and native PE signatures, validates ASAR
configuration, and verifies the publisher proof without launching the app.

Outputs for each app include its ZIP, publisher proof, signing receipt, source
provenance and inventories, native verification and `engineering-receipt.json`.
These are local engineering candidates. The wrapper does not publish, promote
an update, reserve a release sequence, or claim native acceptance. Isolated
packaged-app and update smoke checks, security/dependency/redistribution gates
and final release authorization remain required before delivery.

## Update trust and release metadata

The distribution format is `windows-directory-zip-v1`. Release files are named
`<app>-<version>-win32-x64.zip` and the manifest asset is
`<app>-win32-x64-directory-zip.manifest.json`. The minimum ZIP updater version is
`2.0.0`. The manifest's existing release authorization and the pinned publisher's
independent whole-ZIP proof are both required. Inventory inspection and extraction
hash the same open ZIP descriptor; on-disk inventory alone cannot authorize files.

The staged version is verified before activation. The application launches its
replacement from the next version directory, waits for readiness, and retains
the previous verified version for rollback. Retention protects active, staged,
last-good and pending-activation directories. It never treats arbitrary folders
under Downloads as disposable app versions.


## Receiver schedule and migration verification

The receiver enrolls from the verification keys bundled in the application; it
does not need a GitHub token or feature-access approval to receive public binary
updates. It checks at application/login startup and on reconnect/resume/unlock,
then every 15 minutes while running. GitHub release discovery has a separate
6–6.5 hour cache to limit anonymous API traffic. Consequently, a newly published
release is not guaranteed to appear at the next 15-minute tick. Offline machines,
closed processes, GitHub rate limits and recipient policy can delay updates.

A successful application-ready launch from `Downloads/MelangeApplications`
registers this version's executable as the login receiver. Verify the actual
login target and shortcuts after migrating: an existing entry pointing into
`Documents/MelangeApplications` still starts the old NSIS client. Merely extracting
a ZIP or opening its setup screen does not prove successful registration.
Updates download and verify in the background, then activate after safe close or
before a later normal launch. Readiness, rather than process creation alone,
confirms the replacement; retain the last verified working version for rollback.

## Publishing an update to this channel

Use the directory build above and `packaging/github_release.py` for every future
ZIP update. The existing default Windows workflow and `release_from_main.py`
produce the native/NSIS channel; their successful completion does not publish a
ZIP update. Source commits and private drafts are not receiver-visible releases.

1. Freeze the common client and each backend commit. Build a new immutable
   application version, preserving valid vendor signatures. Never replace a
   distributed ZIP with different bytes under the same version.
2. Complete the required tests, shipped-source secret/data scans, dependency and
   redistribution checks, final native/inventory verification, and isolated
   packaged-app/update acceptance. Record actual evidence in the publisher gate
   receipt bound to the final ZIP's SHA-256. An engineering build receipt is not
   a passing publisher gate receipt.
3. Choose a version and sequence higher than that app's protected publisher
   ledger. Prepare a release specification using the structure below. All three
   source references are required even when releasing only one app. Each package
   entry may override the top-level version and sequence for independent releases.
4. Run the protected publisher, then independently verify its output. It produces
   exactly five assets per app: ZIP, directory manifest, trust transitions,
   `release.json`, and `SHA256SUMS`. Use the existing protected signing state;
   never initialize replacement keys or export private signing material.
5. Upload all five assets to a private draft `desktop-v<version>` in the app's
   own repository (`Melange`, `Mentat`, or `Geo`). Download them back into a fresh
   directory and run the same `--verify-output` command against those bytes.
6. After release authorization and all gates pass, publish as a stable release
   (`draft: false`, `prerelease: false`). Discovery ignores drafts and prereleases
   and selects the highest eligible signed ZIP version independently of GitHub's
   `Latest` badge. A native-only release cannot advance this channel. Verify the
   permanent download URL and signed recovery baseline anonymously after publishing.

```json
{
  "version": "1.0.21",
  "sequence": 14,
  "platform": "win32",
  "arch": "x64",
  "sourceRefs": {
    "melange": {"repository": "pjg93-222/Melange", "ref": "FULL_COMMIT", "commit": "FULL_COMMIT"},
    "mentat": {"repository": "pjg93-222/Mentat", "ref": "FULL_COMMIT", "commit": "FULL_COMMIT"},
    "terrier": {"repository": "pjg93-222/Geo", "ref": "FULL_COMMIT", "commit": "FULL_COMMIT"}
  },
  "packages": {
    "mentat": {
      "package": "C:/candidate-output/mentat/mentat-1.0.21-win32-x64.zip",
      "receipt": "C:/verified-release-evidence/mentat-publisher-gates.json",
      "format": "windows-directory-zip-v1",
      "publisherProof": "C:/candidate-output/mentat/publisher-proof.json"
    }
  }
}
```

The example numbers are placeholders, not reserved release identities. Check the
existing ledger before selecting them. The source values must be full real Git
commit IDs and the receipt must bind those exact sources and package bytes.

```powershell
python ops/desktop/packaging/github_release.py `
  --state C:/Users/pgoff/Documents/MelangeDesktopAdmin `
  --spec C:/verified-release-evidence/github-directory-spec.json `
  --output C:/fresh-release-assets

python ops/desktop/packaging/github_release.py `
  --state C:/Users/pgoff/Documents/MelangeDesktopAdmin `
  --verify-output C:/fresh-release-assets/mentat `
  --repository pjg93-222/Mentat
```

Repeat verification on the downloaded-back asset directory before publication.
Keep every installed version's approved signed recovery manifest and ZIP hosted;
removing that baseline can prevent its next automatic update. Permanent links
use the public release URL, not an expiring redirected storage URL:
`https://github.com/<owner>/<repository>/releases/download/desktop-v<version>/<app>-<version>-win32-x64.zip`.
