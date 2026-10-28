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
