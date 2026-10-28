# Windows installers without NSIS plug-ins

ThreatLocker on a recipient PC permitted the outer Melange installer but reported
blocks for `StdUtils.dll`, `nsis7z.dll`, `System.dll`, and `UAC.dll`. Removing the
uninstaller did not remove those NSIS dependencies.

Use `build-plugin-free.cjs` for the replacement Windows distribution. It embeds
the application files using NSIS's built-in per-file LZMA compression and `File`
instructions. It uses built-in commands for the per-user Downloads path,
shortcuts, registry entry, and launch arguments. It creates no uninstaller and
uses no external installer plug-ins or elevation calls. The legacy
electron-builder NSIS output still uses plug-ins and is not this replacement.

Per-file compression with an 8 MiB dictionary avoids the old compiler's size limit
when a solid build first accumulates the full uncompressed runtime. Each build
uses a fresh `<output>.work` directory for compiler temporary files; failed build
evidence is retained there.

The shared builder supports Melange, Mentat and Terrier. Its input is an existing
signed application directory; it does not compile the backend or sign the output.

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

The installer retains the HKCU login receiver (`--desktop-updater`), versioned
program folders, interactive baseline copy, and updater arguments
`--updated /S` and `--force-run`. Application profiles are not moved or deleted.

## Recipient policy

An installer approval does not automatically approve its payload. The application,
Python/runtime executables, native libraries, and subsequent updates still need
the recipient administrator's application definitions and policies. Preserve
vendor signatures and keep approval scoped to the intended apps. Do not treat
this packaging change as proof of ThreatLocker approval.

## Current delivery evidence

For the October 28, 2026 manual test delivery, the user explicitly requested that
the verification stage be skipped. Record compilation and signing separately;
do not produce passing native-census or application-acceptance receipts for checks
that were not run. This delivery instruction does not permanently disable the
project's normal release checks. The previous verifier expects the older nested
NSIS layout and must be adapted before it can check this new direct payload.
