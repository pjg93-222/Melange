# Melange 1.0.17 build plan

Build status: **NOT STARTED: disk gate.** The build script requires 32 GiB free on C:; about 16 GiB was free on 2026-10-23.

No build, signing, tag or GitHub write has been done for 1.0.17. The tag `desktop-v1.0.17` is created only after the build gate passes.

## Source of the 1.0.16 procedure

The 1.0.16 installer was built by `C:\Users\pgoff\Documents\Codex\2026-10-22\hey\work\build-mm16-inner-signed-parallel.ps1`. The lines that pin and gate the build:

Lines 6-7 (source and base pins):

```
$taskSourcePins = @{melange='3958bc60b7c57fe6b6c10120c789b24bcbc86f2b';mentat='8cc4d9eec635be98ee40394cf8156de500772443'}
$taskBasePins = @{melange='0194af87d3d37e3dae5feb14f1ef70b4b15afae6';mentat='426ddd6c52a4ad0fdbb32ec9f5352457f5bfcf01'}
```

Line 15 (disk gate):

```
if ((Get-PSDrive -Name C).Free -lt 32GB) { throw 'At least 32 GiB free space is required before building' }
```

Lines 31-36 (signing environment and the build command):

```
$env:DESKTOP_SIGNING_CERT_SHA1='0EBC9AD04E929CDD731EDB5D278A4143BC3D3D30'
$env:DESKTOP_SIGNING_ROOT=$taskBuildRoot
$env:DESKTOP_DIST_ROOT=Join-Path $taskBuildRoot 'dist'
$env:CSC_IDENTITY_AUTO_DISCOVERY='false'
Set-Location -LiteralPath $taskClient
& npm.cmd run build -- --win nsis --x64 --publish never *> (Join-Path $taskBuildRoot 'build.log')
```

## Three differences from 1.0.16 that must be settled before the build

The 1.0.16 procedure cannot be reused with only the pins changed.

1. **The runtime must be re-staged from this source.** 1.0.16 was a signing-only release: line 30 loads `DESKTOP_RUNTIME_ROOT` from `mm16-signing-build-inputs\melange-environment.json`, which points at the runtime extracted from the 1.0.15 installer (`...\mm15-extracted-melange-d547955c1bd9e0be\app\resources\runtime`, application source `0194af87d`). 1.0.17 changes the Python runtime sources (Task 1 served generations, including the bootstrap file `desktop_backend.py`; Task 2 personal texture and Big Five status; Task 3 public pages and the publication seam; Task 4 scrape client). Packaging the 1.0.15 runtime would ship none of those Python changes. Proposed step: copy the verified 1.0.15 runtime into the new build root, then refresh its sources from this branch with `build_runtime.py --sync-sources-only` (it keeps the private CPython and native dependencies). The copy needs space beyond the 32 GiB gate.
2. **The base-pin check on line 16 must change.** Line 16 refuses unless the runtime verification's `sourceA` equals the base pin. The existing verification JSON records `sourceA = 0194af87d`. With the base pin set to `46c22a9b4` (the 1.0.16 visible-startup source), that check fails by design. Either keep `0194af87d` as the verified runtime origin and record `46c22a9b4` as the previous packaging source, or write a new runtime verification for the re-staged runtime.
3. **PowerShell execution policy on this machine.** PR #60 commit `187ccd569` ("Remove signing policy and module-path overrides") removed `-ExecutionPolicy Bypass` from the signing hook's `powershell.exe` call (`release-signing.cjs`). Every execution-policy scope on this machine is `Undefined`, so Windows applies `Restricted` and refuses to load `sign-staged-binary.ps1`. The node test "actual Windows subprocess verifies a copied vendor binary without signing or changing it" fails here for that reason, and the hook would fail the same way during the build. Choosing how the build host permits that script (process-scoped `PSExecutionPolicyPreference` in the build script, a user-scope policy, or an Authenticode-signed `sign-staged-binary.ps1`) is a security setting for Paul to decide. This plan does not change it.

## Adapted command sequence (run only after the gate and the three decisions)

Paths: build root `C:\Users\pgoff\Documents\Codex\2026-10-23\release-1.0.17\`, source the release worktree `C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees\release-1.0.17-prep`.

```
# 0. Gates
if ((Get-PSDrive -Name C).Free -lt 32GB) { throw 'At least 32 GiB free space is required before building' }
$source = 'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees\release-1.0.17-prep'
$sourcePin = '<release/1.0.17-prep HEAD: the commit that adds this file, read with git rev-parse at build time>'
$basePin = '46c22a9b4'   # 1.0.16 packaging source (see difference 2)
if ((& git -C $source rev-parse HEAD).Trim() -cne $sourcePin) { throw 'Source pin changed' }
if (& git -C $source status --porcelain --untracked-files=normal) { throw 'Source checkout is not clean' }
# Certificate check unchanged from the 1.0.16 script (lines 24-25): Cert:\CurrentUser\My\0EBC9AD04E929CDD731EDB5D278A4143BC3D3D30, HasPrivateKey, subject.

# 1. Build root and inputs record
$root = 'C:\Users\pgoff\Documents\Codex\2026-10-23\release-1.0.17\ml17-' + [guid]::NewGuid().ToString('N').Substring(0,8)
New-Item -ItemType Directory -Path $root | Out-Null
# build-inputs.json as in line 28, with version='1.0.17', packagingSource=$sourcePin, previous packaging source=$basePin,
# baselineInstallerSHA256='58bc455db6cdfa785d252cdfcdc8ac7b5cd0ad8af0aed8ee78fac1507846a9fc'.

# 2. Runtime (difference 1)
# Copy the verified 1.0.15 runtime to $root\runtime, then:
& python (Join-Path $source 'ops\desktop\packaging\build_runtime.py') --app melange --source $source --sync-sources-only --runtime-root "$root\runtime"

# 3. Client dependencies: npm ci in $source\ops\desktop\client (node_modules is ignored by ops/desktop/client/.gitignore).

# 4. Environment (lines 30-34), with DESKTOP_RUNTIME_ROOT pointed at $root\runtime
$env:DESKTOP_SIGNING_CERT_SHA1='0EBC9AD04E929CDD731EDB5D278A4143BC3D3D30'
$env:DESKTOP_SIGNING_ROOT=$root
$env:DESKTOP_DIST_ROOT=Join-Path $root 'dist'
$env:CSC_IDENTITY_AUTO_DISCOVERY='false'
# plus DESKTOP_APP_ID=melange, WINDOWS_PUBLISHER_NAME, DESKTOP_UPDATE_PROVIDER=github, DESKTOP_GITHUB_REPOSITORY=pjg93-222/melange,
# DESKTOP_ACCESS_TRUST (sha256 666b027a4aed84f371f84c98e9d89426cfb41ac14ed57bcdbb02ea02b532ae59), from melange-environment.json.
# DESKTOP_SHARED_SCRAPE and DESKTOP_PUBLIC_DATA_MODE stay unset (broker off, legacy public data), as reviewed.

# 5. Build (lines 35-36)
Set-Location -LiteralPath "$source\ops\desktop\client"
& npm.cmd run build -- --win nsis --x64 --publish never *> (Join-Path $root 'build.log')

# 6. Result record and pin re-check (lines 37-45 unchanged in shape).
```

Expected output: `$root\dist\melange\Melange-1.0.17-win-x64.exe`. Signing goes through `release-signing.cjs` and `sign-staged-binary.ps1`, which runs `signtool sign /sha1 $thumbprint /s My /fd sha256 /tr http://timestamp.digicert.com /td sha256`.

## Verifier after the build

`C:\Users\pgoff\Documents\Codex\2026-10-22\hey\work\verify_terrier_signed_artifact.py --app melange` (sha256 `1ee631e818569d021d7df8429faeb5ce376c5236f9754bd10b2dfe0873217586`, checked 2026-10-23), with baseline the 1.0.16 installer `C:\Users\pgoff\Documents\Codex\2026-10-22\hey\work\ml16-69e7b31b\dist\melange\Melange-1.0.16-win-x64.exe` (sha256 `58bc455db6cdfa785d252cdfcdc8ac7b5cd0ad8af0aed8ee78fac1507846a9fc`).

Before using it: the verifier was written for signing-only releases. Its `BASELINES['melange']` entry pins the 1.0.15 installer (`d547955c...`) and expects version 1.0.16. It refuses on "Shipped application JS/assets changed", "Runtime/source/frontend or other non-PE file changed", and "Package metadata changed beyond version". 1.0.17 changes shipped JS (`main.cjs`, `runtime.cjs`, `builder.cjs` metadata, module inventory, scrape and public-data modules) and runtime sources by design. As written, it will refuse 1.0.17 even against the 1.0.16 baseline. A 1.0.17 variant needs a melange entry `(1.0.16 installer, 58bc455d..., "1.0.16", "1.0.17")` and an explicit allow-list of expected changed files, taken from `git diff --name-only 46c22a9b4..<sourcePin>` restricted to packaged paths. Every other file must still match byte for byte, and the Authenticode and publisher-pin checks must stay.
