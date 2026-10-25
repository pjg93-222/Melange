# Public GitHub desktop updates

The Electron apps can use public GitHub Releases. Each app has its own public
repository (Paul's correction, 2026-10-15): Melange `pjg93-222/Melange`, Mentat
`pjg93-222/Mentat`, Terrier `pjg93-222/Geo`. The combined `melange-platform`
repository is no longer a destination. Binary update checks are independent of application
feature approval. The app still verifies an Ed25519 manifest against its
independently installed update roots, exact app/OS/architecture, increasing
sequence/version, installer hashes, and the native OS signer before activation.
Feature access keeps its separate signed approval checks. No GitHub PAT,
publisher private key, access credential, or recipient list belongs in an app
or release asset. Making the repository public is an owner action; none of the
tools here change repository visibility.

> **Signing: self-signed certificate plus one-click trust (Paul's choice,
> 2026-10-16; trust step added for 1.0.6).** Each installer is Authenticode-signed
> on Paul's PC with the self-signed certificate
> `CN=Melange Systems Desktop Release (self-signed)` (SHA-1 thumbprint
> `0EBC9AD04E929CDD731EDB5D278A4143BC3D3D30`; end-entity, CA:false, Code Signing
> EKU only, Digital Signature key usage). Its non-exportable key stays in Paul's
> `CurrentUser\My`; no publicly trusted signing identity is used or needed. The
> hosted build stays unsigned but bakes the public pin
> `WINDOWS_PUBLISHER_NAME = CN=Melange Systems Desktop Release (self-signed)`
> (workflow `RELEASE_PUBLISHER`, signed-release input mode, with `STABLE_TAG`
> reserved). Paul then signs the installer (RFC 3161 timestamp),
> `packaging/authenticode_binding.py` proves the signed file is the hosted bytes
> plus only an appended signature, and the steps below prepare and publish the
> stable `desktop-v<version>` release. The per-app Ed25519 update roots and the
> pinned publisher subject live in the protected publisher state
> (`server/desktop_admin.py` `init` and `trust-publisher`), outside this repository.
>
> A PC installs updates only when Windows reports that signer as `Valid`, that
> is, when the public certificate is in the user's trusted roots. Trust is one
> click, through Windows' own Yes/No security dialog, with no command line and
> no administrator rights; it adds only that public certificate (shipped as
> `client/melange-systems-desktop-release.cer`) to `CurrentUser\Root`:
>
> - the installer no longer touches the certificate store (no `certutil`, nothing
>   elevated), so there is no "all users" or different-administrator account
>   mismatch: trust is always granted to the account that runs the app;
> - the app asks once, at its first interactive launch, when Windows definitely
>   reports the certificate as not trusted and the user has not declined before
>   (a refusal is remembered). The prompt is Windows' own Yes/No dialog;
> - until trusted, the app shows "Automatic updates are off until this PC trusts
>   the Melange Systems release certificate" in Settings, with a **Turn on
>   updates** button (also in the app menu) that asks again
>   (`client/publisher-trust.cjs`: it reads the bundled certificate once, refuses
>   any bytes whose SHA-1 is not the pinned thumbprint, and imports those same
>   in-memory bytes) and skips update downloads until trusted. Only a definite
>   "not in the store" answer counts as untrusted; if the check itself fails the
>   update check runs anyway, because Authenticode still gates every install;
> - the certificate intentionally stays trusted after an app is uninstalled,
>   because all three apps (Melange, Mentat, Terrier) share it;
> - PCs that already run 1.0.5 (which cannot verify updates until trusted) can
>   double-click `turn-on-updates.cmd`, published with every release: it carries
>   the certificate, refuses to import anything but the pinned thumbprint (it
>   adds the checked in-memory certificate, no temporary file), and reports the
>   result in a Windows message box. Windows SmartScreen may first ask to
>   confirm the downloaded file.
>
> Verified updates then apply without asking: when the app closes (silent NSIS
> install), or, if one is still pending (for example after a shutdown), at the
> next start before any window or backend opens, followed by a relaunch. A
> running session is never interrupted. None of the manifest, sequence,
> anti-rollback, hash or exact-publisher checks changed.

## From committed sources to a prepared installer

1. Commit completed source to each app's own repository `main` (Melange to
   `pjg93-222/Melange`, Mentat to `pjg93-222/Mentat`, Terrier to
   `pjg93-222/Geo`). The earlier instruction to run the combined source-only sync
   in `../SOURCE_SYNC.md` to `melange-platform` main is **superseded** by that
   correction, and `ops/sync_sources.py` now refuses `--apply` and `--push`.
   No step here creates binaries or deploys servers.
2. On a Windows x64 builder, follow `packaging/README.md` to freeze each native
   runtime and build the three NSIS installers with the GitHub source selected.
   The builder defaults to `DESKTOP_UPDATE_PROVIDER=github` and, when
   `DESKTOP_GITHUB_REPOSITORY` is unset, to the selected app's repository named in the
   introduction (`DESKTOP_APP_ID` = `melange`, `mentat` or `terrier`). Set the
   variable only to override that default. Supply the independently
   reviewed public descriptor through `DESKTOP_ACCESS_TRUST`; its
   `updatePublicKeysByApp[appId]` supplies initial update roots without login or
   server enrollment. `DESKTOP_UPDATE_PROVIDER=publisher` explicitly selects
   the existing custom publisher instead. Use a new stable three-part version
   and a strictly increasing positive release sequence for each released app
   (its own ledger row). Record the exact source commits used;
   Terrier's original source checkout is separate from Melange/Mentat.
3. Complete native application acceptance and the existing `tests`, `security`,
   `dependencies`, `redistribution`, and `dataAllowlist` gates. Sign each installer
   with the configured Windows Authenticode identity. Each reviewed gate receipt
   must bind its installer SHA-256, app/version/platform/architecture, gate evidence,
   and a `source` object equal to that app's entry in the release specification.
   Source provenance is an operator attestation in that exact-byte receipt;
   this tool does not reconstruct or independently prove installer source.
4. Use the existing protected publisher state. Configure its independently
   provisioned per-app Ed25519 update roots and exact Windows publisher subject
   using the existing administrator tools. Preserve this state and the
   `github-prepared.sqlite3` sequence ledger across builds. It is not an asset.
5. Prepare a **new** output directory, then reverify each app's release before upload:

```powershell
python ops/desktop/packaging/github_release.py --state $publisherState --spec $releaseSpec --output $newBundle
foreach ($app in (Get-ChildItem -LiteralPath $newBundle -Directory).Name) {  # the apps this bundle releases
  python ops/desktop/packaging/github_release.py --state $publisherState --verify-output (Join-Path $newBundle $app)
  if ($LASTEXITCODE -ne 0) { throw "$app release verification failed" }
}
```

One specification names one or more apps under `packages` (release owner,
2026-10-16: the first signed release is Melange only). The named apps are signed
together or not at all. Each takes the top-level `version` and `sequence` unless
its `packages` entry sets its own, and each passes every per-app gate:
Authenticode Valid by the exact subject, the receipt bound to its bytes and
source, and its own ledger advance. `sourceRefs` always names all three apps,
because every signed manifest binds them and the installed client requires all
three (`client/github-source.cjs` `githubPolicy`). For an app that is not released,
give the reviewed commit of its own repository's main. Each app's release is bound to its own
repository from the fixed map in `github_release.py` (`melange` to
`pjg93-222/Melange`, `mentat` to `pjg93-222/Mentat`, `terrier` to `pjg93-222/Geo`).
An optional `repositories` object may restate entries of that map (case is
ignored); any other repository, an unknown app key, or the retired single
`repository` field is refused. Replace every placeholder with the actual
completed build inputs. The all-zero commit below is deliberately invalid.

```json
{
  "version": "1.0.0",
  "sequence": 1,
  "platform": "win32",
  "arch": "x64",
  "repositories": {"melange": "pjg93-222/Melange", "mentat": "pjg93-222/Mentat", "terrier": "pjg93-222/Geo"},
  "sourceRefs": {
    "melange": {"repository": "pjg93-222/Melange", "ref": "main", "commit": "0000000000000000000000000000000000000000"},
    "mentat": {"repository": "pjg93-222/Mentat", "ref": "main", "commit": "0000000000000000000000000000000000000000"},
    "terrier": {"repository": "pjg93-222/Geo", "ref": "main", "commit": "0000000000000000000000000000000000000000"}
  },
  "packages": {
    "melange": {"package": "C:/build/melange.exe", "receipt": "C:/receipts/melange.json"},
    "mentat": {"package": "C:/build/mentat.exe", "receipt": "C:/receipts/mentat.json"},
    "terrier": {"package": "C:/build/terrier.exe", "receipt": "C:/receipts/terrier.json"}
  }
}
```

Preparation checks the actual staged Windows signatures and exact-byte gate
receipts before signing. It refuses partial three-app releases, source-receipt
mismatch, old versions/sequences, and reusing a sequence for different bytes.
The sequence ledger is checked per app across every repository it has recorded,
and each new row records that app's own repository. Repeating the identical
release at a new directory reproduces its envelopes. No network request or upload
occurs. The output holds one directory per app, each with exactly six files:

- `<app>-win32-x64.manifest.json`, `<app>-<version>-win32-x64.exe`, `<app>-trust.json`;
- `turn-on-updates.cmd`, byte-identical to `client/turn-on-updates.cmd` (the
  one-click trust file above; `--verify-output` refuses any other bytes);
- that app's `release.json` (with its `appId` and `repository`) and `SHA256SUMS`.

A directory prepared before the trust file existed (`desktop-v1.0.5`) still
verifies with its original five files.

Each signed manifest binds `purpose: melange-desktop-github-release`,
`distribution: public-installations`, that app's lowercase GitHub repository,
all three source references, app/version/sequence/platform/architecture and
package hashes. The installed client accepts it only when that repository equals
its own configured repository (`client/github-source.cjs` `githubPolicy`), so a
release uploaded to another app's repository cannot install. The signed logical
package path remains `/v1/packages/<app>/<sequence>/<installer-name>`; the GitHub
adapter maps it to the exact asset in `desktop-v<version>`. Trust files contain
only signed key transitions rooted in keys the installed app already trusts. A
failed download cannot replace those roots. From 1.0.6 the client records the
running version's signed manifest as its rollback baseline without downloading
that version's installer, and rollback works offline from locally kept
installers: the installer that was downloaded to update stays in the app's own
per-user updater cache (`%LOCALAPPDATA%\<application id>\updater\updates`, moved out
of the Documents profile so large installers are never synced; the update state,
including the anti-rollback high-water, stays in the profile and is unaffected, and
installers cached at the old location are ignored and fetched once again) after it
is verified and activated, only the current and
the immediately previous version keep one (older ones are pruned once the new
version is confirmed running), and an interactive first install keeps a copy of
its own setup file (`%LOCALAPPDATA%\<application id>\baseline\<version>`) so
even the first rollback needs no download. A rollback verifies the local copy
exactly as an activation does (signed-manifest hashes, then the exact
Authenticode subject, twice). Only when no local copy exists, or it fails
verification (it is then deleted), is the older installer fetched from its
exact `desktop-v<version>` release, which therefore must stay hosted for that
fallback. Network is needed only to fetch new updates. A per-machine (all users) install skips the first-install copy, because the app reads the signed-in user's `%LOCALAPPDATA%`; the first rollback there falls back to the network. The baseline copy is copied (not moved) and removed only after the rollback completes and the target version is confirmed running. A cached installer is deleted only when its own size or hash check fails, never for an untrusted signature or a tool error. If the installer later cannot be spawned, electron-updater exits the app once and the update is recorded as failed at the next start; the exceptions are EACCES/UNKNOWN (retried through its elevation helper, which can show a UAC prompt, rare for this per-user install) and ENOENT (opened interactively without `/S`), neither of which reports an error. Disk cost is about one
extra installer per app (Melange roughly 575 MB).

## Release from main

`packaging/release_from_main.py` runs the steps above, and the publishing steps
below, as one local command. It stops at the first failed step and names that step.

- **Sources.** Each checkout's `origin` must be its app's GitHub repository: the
  configured URL (`git config --get remote.origin.url`, before any `insteadOf`
  rewriting) must be `https://github.com/pjg93-222/<Name>[.git]` or
  `git@github.com:pjg93-222/<Name>[.git]`. The command fetches, then refuses modified tracked files and any `HEAD` that is not
  `origin/main`. Untracked files are ignored, because every source is exported
  from the commit with `git archive`. The checkouts default to dedicated clean
  clones in `~/Documents/MelangeReleaseSources/{Melange,Mentat,Geo}`; a missing
  default clone is cloned from `https://github.com/pjg93-222/<Name>.git` first.
  (Everyday checkouts are other lineages whose `HEAD` is not `origin/main`.)
  Override them with `--melange`/`--mentat`/`--geo` or
  `DESKTOP_MELANGE_SOURCE`/`DESKTOP_MENTAT_SOURCE`/`DESKTOP_GEO_SOURCE`; a given
  path that does not exist is refused, never cloned.
- **Clients.** Each app is built with its own repository's desktop client:
  Melange with Melange's `ops/desktop/{client,packaging}`, Mentat with Mentat's,
  and Terrier with Melange's, Geo being its application source.
- **Version.** The version is `ops/desktop/client/package.json`, which must be
  the same on Melange main and Mentat main. `--version` must equal it.
  `desktop-v<version>` must not exist in any of the three repositories. The
  sequence is the ledger's last + 1, unless you pass `--sequence`.
- **Build venvs.** Without `--build-python` (or `DESKTOP_BUILD_PYTHON`) the
  command creates one venv per app in `release-<v>/venv/<app>` with its own
  interpreter (CPython 3.12) and installs it as CI does (`--require-hashes
  --only-binary=:all: --no-deps`, then `pip check`) from a hash-locked file:
  `ops/desktop/packaging/<app>-runtime.constraints.txt` in the app's client
  (tool) repository: `melange-` (Melange), `mentat-` (Mentat repo),
  `terrier-` (Melange, Terrier's tool repo). Geo's `requirements.build.lock` is
  a Linux lock and is never used. Each file's header says how it was generated
  (Windows x64 / cp312 wheel hashes). An app with no such file is refused at step `venv`; pass `--build-python` for it (then that
  one venv serves every app). Each venv's `pip freeze --all` SHA-256 is in its
  app's tests gate.
- **Gates.** Per app: an app whose export has `frontend/package.json` and whose
  `runtime-manifest.json` sources need `frontend/dist` (Terrier) first gets
  `npm ci --no-fund` and `npm run build` in `<export>/frontend` (step
  `dataAllowlist`) and `npm audit --omit=dev --audit-level=high` there (its
  `dependencies` evidence). Then `build_runtime.py --stage-only`, then `security_gate.py export`
  on the sources it staged (`release-<v>/stage/<app>/<id>/sources`, the files the
  app installs; tests, fixtures and other unshipped files drop out; owner ruling
  2026-10-24 "Scan shipped files only"). The gate is the private checkout's
  `ops/security_gate.py` with its `ops/security/` (canaries, exceptions):
  `--security-root` (env `DESKTOP_SECURITY_ROOT`, default
  `~/OneDrive/Desktop/Melange Systems`), refused at step `local` without
  `ops/security_gate.py` or `ops/security/canaries.txt`. It runs in place with
  `python -B` and is never written. When the app's client repository has
  `ops/desktop/packaging/<app>-security-exceptions.toml` (Terrier only), those
  entries are appended to a copy of the private `exceptions.toml` in
  `release-<v>/security-gate/` and passed with `--exceptions`; the security
  evidence records the SHA-256 of the original, the appended file and the merged
  copy. Each entry needs a `D-###` that is in the brain's `DECISIONS.md` and
  expires within 30 days (Terrier's three: D-292, until 2026-11-23). The one reviewed Mentat finding still goes through
  `desktop_source_review.py`. Then the runtime build (native runtimes complete, licence metadata for every
  dependency), `npm run build` and the packaged backend smoke. Per client
  repository, the tests gate runs every test module under `ops/desktop`, each
  with what it needs: `npm ci` first (the client tests and `test_district_packs`
  load `node_modules`; pytest never recurses into it), then pytest inside a git
  work tree as in a checkout (`test_district_packs` checks that its own file is
  refused there; `git init` makes the export one for the run, and its `.git` is
  removed afterwards). A module that reads another app's source tests that
  app's integration and runs when that app is released: `TERRIER_TEST_SOURCE`
  is then Geo's export (its `frontend/dist` built) and `MENTAT_TEST_ENGINE`
  Mentat's `mentat/app/contribution_data.py`. In a release without that app the
  tests evidence lists those modules as not run, and the shared run `--ignore`s
  them; every other module runs in every release. The modules that import
  Melange's own `fec` from their repository root (`APP_TEST_MODULES`, checked
  against a scan by `test_release_from_main`) run in Melange's shared run; in
  another repository they run, with Melange released, in Melange's test venv
  with Melange's export on pytest's `pythonpath`, and are otherwise listed as
  not run and `--ignore`d. pytest runs in test venvs
  only, never a build venv or a runtime: `release-<v>/venv/<repo>-tests` from the repository's
  `<repo>-runtime.constraints.txt` (plus `mentat-test.constraints.txt` in Mentat),
  installed like the build venvs. The modules that read `TERRIER_TEST_SOURCE`
  set up Django once per process, so each runs alone in `venv/terrier-tests`:
  Melange's `terrier-runtime.constraints.txt` plus pytest's hashed entries from
  `melange-runtime.constraints.txt` (`venv/pytest.constraints.txt`). The shipped
  Terrier runtime cannot run them (the runtime build drops every `test`
  directory, `django/test` included). The shared run `--ignore`s exactly those
  modules. Then `npm test` and `npm audit`. Every gate's evidence names its
  command, exit code, log and log SHA-256. The runtime build and the smoke run
  in the build venvs.
- **Signing.** Signing happens inside `npm run build`, by the merged hook
  `ops/desktop/client/release-signing.cjs` of each app's client repository
  (`packaging/INNER-SIGNING.md`), with the certificate held in this PC's TPM-backed
  `Cert:\CurrentUser\My` store (thumbprint `0EBC9AD0...3D30`). The command passes
  `DESKTOP_SIGNING_CERT_SHA1`, `WINDOWS_PUBLISHER_NAME`, and a fresh per-app
  `DESKTOP_SIGNING_ROOT` (`release-<v>/signing/<app>`) with `DESKTOP_DIST_ROOT`
  inside it. It strips `CSC_*`/`WIN_CSC_*`; the rest of your environment is
  inherited. Step `version` refuses a client repository whose main lacks the
  hook. `trust.json` `windowsPublisher` must be the hook's subject,
  `CN=Melange Systems Desktop Release (self-signed)`. Step `sign` then only
  verifies: each installer must be Valid, with that thumbprint, subject and a
  timestamp. Its `<installer>.signatures.json` hook receipt must record those
  installer bytes, and its SHA-256 goes into `osSignature`. A NotSigned installer
  means the hook was not active and is refused. The manifest keys stay in the
  state directory (`--state`, default `~/Documents/MelangeDesktopAdmin`). The
  command refuses to run in CI, and `--publish` never runs there.
- **Execution policy.** The hook runs `sign-staged-binary.ps1` with
  `powershell.exe -File` and no execution-policy argument. Step `local` reads the
  effective policy (`Get-ExecutionPolicy`, with your environment) and refuses
  anything other than RemoteSigned, Unrestricted or Bypass, before any other
  command runs. If every scope is Undefined (Restricted), the choice is yours,
  for example running the command from a PowerShell session after
  `Set-ExecutionPolicy -Scope Process RemoteSigned`. That lasts only for that
  session and reaches the build via `PSExecutionPolicyPreference`. The command
  never sets or overrides the policy. The check also runs for a `--publish`
  after a dry run, which builds nothing.
- **Outputs** (under `--output-root`, default `~/Documents/Desktop-Installers-<date>`):
  `receipts-<v>/`, `release-spec-<v>.json` and `release-<v>/` (sources, venvs,
  logs, signed installers and their hook receipts in `signing/<app>/dist/<app>/`). A dry run (no `--publish`) ends with a
  `check` step: the release spec and each receipt pass the same spec and gate
  verification (`desktop_admin` `verify_release_gates`, including the signature)
  and the same version and sequence advance rule against the ledger (read only)
  that `github_release.py` will apply, but nothing is prepared, so there are no
  GitHub writes and no ledger sequence is reserved.
  `--publish` after a dry run reuses its signed installers and receipts: it
  rechecks that every `origin/main` still equals the spec's `sourceRefs`, that
  no tag exists and that each installer's SHA-256 equals its receipt, then
  runs `github_release.py --spec` (which reserves the sequence) into
  `release-<v>/bundle/`, checks each `release.json` against the spec, and
  publishes. Without a prior dry run, `--publish` builds everything first.
  `--output-root` defaults to a dated folder, so pass the dry run's
  `--output-root` when `--publish` runs on a later day. Otherwise it finds no
  dry run and rebuilds. The publish first checks, for all
  three apps, that the repository is public, that the commit exists on GitHub
  (a pushed `origin/main`) and that there is no `desktop-v<v>` tag, release or
  draft; a `gh release view` failure other than "release not found" (auth,
  network) stops it instead of counting as absent. It then creates, uploads, re-downloads and
  verifies all three drafts, and only then makes any of them public. If it stops
  partway, delete the leftover drafts it made with
  `gh release delete desktop-v<v> --repo <repo>` (only those), remove
  `release-<v>/bundle/` and rerun `--publish`; `github_release.py` reuses the
  signed manifests stored for that sequence when the bytes are identical.
- **Git config.** Every git command follows your `url.*.insteadOf` settings
  (only the origin check reads the unrewritten URL).
- **Tags.** The command creates no git tags; `gh release create --target` makes
  the release tag. Keep any district tag created alongside a release lightweight
  (`git -c tag.gpgsign=false tag <name> <sha>`) until a release containing
  `0084dd739` ships, because the 1.0.15 client rejects annotated district tags.

```powershell
$version = '1.0.17'
$out = "$HOME\Documents\Desktop-Installers-$version"
py -3.12 ops/desktop/packaging/release_from_main.py --native-root $nativeRoot --output-root $out            # dry run
py -3.12 ops/desktop/packaging/release_from_main.py --native-root $nativeRoot --output-root $out --publish  # publish it
```

**Single app, injected runtime.** `--apps` (comma list, default all three)
limits the export, build, gates, signing, receipts, release spec packages and
publish to those apps. The sources step still checks all three checkouts,
because every release spec binds all three `main` commits. Only the selected
apps' client repositories must agree on the version (Terrier alone needs only
Melange's), and only the selected apps' repositories must lack the tag.
`--inject-runtime APP=DIR` copies a previously built runtime for APP (the folder
holding `python\`, `sources\`, `bootstrap\`, `runtime-status.json` and
`dependency-inventory.json`) to `release-<v>/runtime/<app>` and replaces only its
sources with `build_runtime.py --sync-sources-only`: no venv, no full build. The
build step reads DIR's `source-provenance.json` (its `repository` must be the
app's) and, in the app's checkout, takes the requirements file
`runtime-manifest.json` names (Terrier: `requirements.txt`), plus
`requirements.lock.txt` when the export has one, at its `commit` (fetched if
absent; else `reviewedBase`). Every file must be byte-identical to main's;
otherwise, or with no provenance or no resolvable commit, the dependencies may
have changed and it refuses: a full build is required. Every gate, the signing
and the check still run; the tests evidence names DIR, the SHA-256 of its two
JSON files, the provenance commit used and the requirements hashes. `--publish`
after such a dry run needs the same `--apps`.

```powershell
python ops\desktop\packaging\release_from_main.py --apps terrier --inject-runtime terrier=<path to previous Terrier runtime> --output-root <dir>
python ops\desktop\packaging\release_from_main.py --apps terrier --inject-runtime terrier=<path to previous Terrier runtime> --output-root <dir> --publish
```

## Publish the verified releases

These are explicit operator steps after real native acceptance. They require
an authenticated `gh` with release-write permission on each already public
destination. The installer never receives that credential. Use one publisher
and its preserved sequence ledger; review `gh release list --repo $repo` for
every app repository before choosing the next version. Never overwrite/delete
an accepted tag or asset.

Set `$newBundle`, `$publisherState` and `$notesFile` to the reviewed output,
private state and release notes file. Set `$sourceCommits` to a map from app to
the exact pushed commit, in that app's own repository, whose checks passed (for
example `@{melange='...'; mentat='...'; terrier='...'}`). The loop handles each
app in turn and stops on every native command error:

```powershell
$ErrorActionPreference = 'Stop'
foreach ($app in (Get-ChildItem -LiteralPath $newBundle -Directory).Name) {  # the apps this bundle releases
  $bundle = (Resolve-Path -LiteralPath (Join-Path $newBundle $app)).Path
  $index = Get-Content -LiteralPath (Join-Path $bundle 'release.json') -Raw | ConvertFrom-Json
  if ($index.appId -ne $app) { throw "$bundle is not the $app release" }
  $repo = $index.repository
  $tag = $index.tag
  $commit = $sourceCommits[$app]
  python ops/desktop/packaging/github_release.py --state $publisherState --verify-output $bundle --repository $repo
  if ($LASTEXITCODE -ne 0) { throw "$app release verification failed" }
  $visibility = gh repo view $repo --json visibility --jq '.visibility'
  if ($LASTEXITCODE -ne 0 -or $visibility -ne 'PUBLIC') { throw "$repo must already be public" }
  $remoteCommit = gh api "repos/$repo/commits/$commit" --jq '.sha'
  if ($LASTEXITCODE -ne 0 -or $remoteCommit -ne $commit) { throw "Reviewed $app commit is not on $repo" }
  gh release create $tag --repo $repo --target $commit --draft --title "Desktop $($index.version)" --notes-file $notesFile
  if ($LASTEXITCODE -ne 0) { throw "$app draft creation failed; inspect existing tag/release before retrying" }
  $paths = @(@($index.assets) + @('release.json', 'SHA256SUMS') | ForEach-Object { Join-Path $bundle $_ })
  gh release upload $tag @paths --repo $repo
  if ($LASTEXITCODE -ne 0) { throw "$app upload incomplete; leave draft for review, never clobber assets" }
  $downloaded = Join-Path ([IO.Path]::GetTempPath()) ("melange-release-$app-" + [guid]::NewGuid().ToString('N'))
  gh release download $tag --repo $repo --dir $downloaded
  if ($LASTEXITCODE -ne 0) { throw "$app release could not be downloaded for verification" }
  python ops/desktop/packaging/github_release.py --state $publisherState --verify-output $downloaded --repository $repo
  if ($LASTEXITCODE -ne 0) { throw "$app uploaded bytes failed verification; keep the release draft" }
  gh release view $tag --repo $repo --json tagName,isDraft,assets,url
  if ($LASTEXITCODE -ne 0) { throw "$app release review failed" }
}
```

After reviewing each draft and its exact six assets, make it discoverable in
that app's repository (set `$repo` and `$tag` from that app's `release.json`):

```powershell
gh release edit $tag --repo $repo --draft=false --latest
if ($LASTEXITCODE -ne 0) { throw 'Publication failed; inspect release state before retrying' }
```

The CLI argument behavior is documented by GitHub for
[create](https://cli.github.com/manual/gh_release_create),
[upload](https://cli.github.com/manual/gh_release_upload), and
[edit](https://cli.github.com/manual/gh_release_edit). The local
`--verify-output` mode rejects extra/private files (including another app's
assets), renamed or changed assets, signature/identity mismatch, a release
directory checked against a repository other than its app's own
(`--repository`), stale trust transition files, and altered checksum lists. A
failed upload stays a draft; do not use `--clobber` to hide a mismatch.

## First install and remaining prerequisites

An existing app needs the GitHub receiver and independently installed trusted
update roots before it can discover this lane. Distribute the first signed
installer through a reviewed channel, verify its OS publisher, and include its
exact version's signed release as the recovery seed. New manifest keys require
an authenticated transition from an already trusted root. Downloaded GitHub
metadata or a new access grant cannot bootstrap arbitrary update keys.

This release producer intentionally accepts Windows x64 only. Windows signer
credentials, full native runtimes, redistribution approval, and real native
acceptance receipts remain external prerequisites. Mac builds additionally need
Apple signing/notarization, native runtime/Keychain acceptance, and a completed
activation path; Linux desktop activation is not implemented. Do not enable the
inert `native-build.yml.template` or claim cross-OS deployment from source tests.
The source-check workflow is ready to run without those signing secrets. A
source push alone will not produce or install a binary until this native lane
has been completed and a new verified desktop release is published.
