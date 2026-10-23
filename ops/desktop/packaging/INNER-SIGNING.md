# Local Windows release signing

The historical hosted build deliberately produced an unsigned payload. Signing
only its final NSIS installer left the app executable, elevation helper,
uninstaller and installer plugins unsigned. Existing published versions remain
immutable; the correction requires a new version and a new local packaging run.

Use the reviewed source and runtime for the app being released. Terrier 1.0.14
used tooling commit `c3c30469658418f0cf7f192723ddf821445297ce`; Melange and Mentat's
newer releases require their own current sources. This signing change must not
replace their application code or include unrelated pending features.

On the release PC, set these values for the build process only:

```powershell
$env:DESKTOP_SIGNING_CERT_SHA1 = '0EBC9AD04E929CDD731EDB5D278A4143BC3D3D30'
$env:WINDOWS_PUBLISHER_NAME = 'CN=Melange Systems Desktop Release (self-signed)'
$env:DESKTOP_SIGNING_ROOT = '<new private absolute build directory>'
$env:DESKTOP_DIST_ROOT = Join-Path $env:DESKTOP_SIGNING_ROOT 'dist'
# Set the existing reviewed DESKTOP_APP_ID, DESKTOP_RUNTIME_ROOT and
# DESKTOP_ACCESS_TRUST inputs, then run the normal build for a NEW version.
npm run build -- --win nsis --x64 --publish never
```

The root must already exist; its `nsis` and `nsis-resources` children must not.
Only one fresh Windows package is accepted per invocation. Do not set inherited
NSIS overrides, certificate files/passwords, or offline timestamps. The signing
key stays in `Cert:\CurrentUser\My`; nothing exports it. The fixed installed SDK
is `C:\Program Files (x86)\Windows Kits\10\bin\10.0.28000.0\x64\signtool.exe`.

`beforePack` copies the pinned NSIS compiler/resources into the private root,
signs their unsigned executable binaries, and selects those copies using the
builder's supported NSIS environment overrides. Shared tool caches are checked
for unchanged bytes. This includes the plugins embedded into the installer. NSIS `Stubs` templates are
copied unsigned; the installer and uninstaller built from them are signed afterwards.

The builder's sign hook runs after Electron fuse/resource editing and before
NSIS archives the app. It also signs the elevation helper, generated uninstaller
and final installer. Executable build caching is disabled because a cache hit
can bypass signing. `afterSign` checks/signs remaining PE binaries (recognised by the DOS `MZ` header plus the `PE\0\0`
signature at `e_lfanew`, not their extension) in the packed application. Valid vendor signatures are preserved byte-for-byte;
an invalid existing signature fails rather than being overwritten.

The release requires Windows Authenticode status `Valid`, the approved exact
certificate and a timestamp for the owned app and installer. Files outside the
private root, reparse paths and hard links are refused. Each installer gains a
private `.signatures.json` receipt with file hashes and signature results.
Missing app, elevation or uninstaller evidence prevents that receipt.

This receipt supplements the existing source, runtime, extraction and release
checks. Extract the final signed installer and independently verify the app,
uninstaller, elevation helper and all embedded plugins; bind those results to
the final installer hash. Keep the existing source/frontend/runtime comparisons,
update trust and monotonic release sequence checks. The old outer-only signer
must not re-sign the already-signed output. Nothing here publishes, installs,
changes certificates, resets application state or restarts the admin service.

A valid signature does not override ThreatLocker policy. IT may still need to
approve the new installer hash or adjust the approved-publisher rule. Report
the exact blocked executable/path from the endpoint evidence; an outer installer
denial is not proof that unsigned inner files caused that denial.
