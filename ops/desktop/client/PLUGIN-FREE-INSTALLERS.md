# Windows installers without NSIS plug-ins

ThreatLocker on a recipient PC permitted the outer Melange installer but reported
blocks for `StdUtils.dll`, `nsis7z.dll`, `System.dll`, and `UAC.dll`. Removing the
uninstaller did not remove those NSIS dependencies.

The ordinary Windows build now uses the replacement distribution:

```powershell
npm run build -- --win --x64 --publish never
```

`build-native.cjs` builds the application directory, retains the configured
native signing hooks, compiles the built-in installer and signs the final EXE.
Production builds require the existing signing configuration; there is no
unsigned fallback. The release controller consumes the resulting installer and
its complete signature receipt. `npm run build:dir` remains an explicit staging
command and does not produce the final installer.

The underlying `build-plugin-free.cjs` embeds the application files using
NSIS's built-in per-file compression and `File`
instructions. It uses built-in commands for the per-user Downloads path,
shortcuts, registry entry, and launch arguments. It creates no uninstaller and
uses no external installer plug-ins or elevation calls. Explicitly invoking the
legacy electron-builder NSIS target still uses plug-ins; it is not the ordinary
Windows build entry point.

Per-file compression with an 8 MiB dictionary avoids the old compiler's size limit
when a solid build first accumulates the full uncompressed runtime. Each build
uses a fresh `<output>.work` directory for compiler temporary files; failed build
evidence is retained there.

Pass `--compression zlib` for faster per-file compression at the cost of a larger
download. Both supported codecs are built into NSIS; neither needs a plug-in DLL.

The shared helper supports Melange, Mentat and Terrier. Advanced callers can
supply an existing signed application directory; the helper does not rebuild
the backend. Its standalone CLI leaves signing to the caller, while the normal
production wrapper requires and performs the configured signing steps.

```powershell
node build-plugin-free.cjs --app melange --version 1.0.22 `
  --program C:/release/signed-program `
  --output C:/release/output/Melange-1.0.22-win-x64.exe `
  --makensis C:/tools/nsis
```

To retain an existing signed runtime while incrementing the application's version,
`prepare-plugin-free-payload.cjs` creates an updated `app.asar` and main executable
in a new output directory. It updates Electron's ASAR integrity resource and signs
the changed owned executable with the existing approved certificate. Pass these
two files through `--app-executable` and `--app-asar`. All other payload files are
read directly from the original application directory. Sign the final installer
with the approved certificate and a trusted timestamp before distribution.

The installer shows concise extraction phases without adding every extracted
filename to the details list. This reduces UI work; download size and physical
extraction still depend on the payload and computer.

The installer retains the HKCU login receiver (`--desktop-updater`), versioned
program folders, interactive baseline copy, and updater arguments
`--updated /S` and `--force-run`. Application profiles are not moved or deleted.

## Recipient policy

An installer approval does not automatically approve its payload. The application,
Python/runtime executables, native libraries, and subsequent updates still need
the recipient administrator's application definitions and policies. Preserve
vendor signatures and keep approval scoped to the intended apps. Do not treat
this packaging change as proof of ThreatLocker approval.

See [ThreatLocker deployment](THREATLOCKER-DEPLOYMENT.md) for per-application
runtime and dependency coverage, login/update paths, and the audit details IT
needs to investigate a denial.

## Current delivery evidence

The original October 28, 2026 `1.0.22-test` manual previews were delivered with a
user-requested verification skip. That historical instruction did not disable
future release gates. Subsequent preparation for signed automatic feeds completed
all six independent native/source/signature inspections for the exact 1.0.22 and
1.0.23 installers. `verify_native_release.py` now explicitly supports
`builtin-nsis-v1`, checks the complete direct payload and requires zero installer
plug-ins. Complete signing and source checks remain mandatory.

The frozen 1.0.23 installers use the retained native `5f545144` client/runtime,
their separately recorded backend commits, and `8c0d35036` build inputs plus
versioned main/ASAR overlays. Later production-wrapper and main changes are not
retroactively claimed as their runtime source. The native receiver uses each
app's signed GitHub manifest and trust metadata; stable 1.0.22 recovery metadata
must precede the 1.0.23 feed. Publication is a separate step from preparation.

The user subsequently reported that the app launches under ThreatLocker. This
is a reported result for the tested case, not all-device acceptance. The work-PC
automatic-update/recovery cycle and full authenticated business workflows remain
separate acceptance work; local native inspection and backend smoke results do
not establish those outcomes.
