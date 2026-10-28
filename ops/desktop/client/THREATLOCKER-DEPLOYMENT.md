# ThreatLocker deployment: Melange, Mentat and Terrier

The native installers use built-in NSIS operations and create no uninstaller.
They do not load the former `StdUtils.dll`, `Nsis7z.dll`, `System.dll` or
`UAC.dll` installer plug-ins. The reported 1.0.22 failure is now ThreatLocker
denying the installed `Melange.exe`: allowing its installer does not also allow
that executable or its dependencies. A desktop shortcut still launches the
same executable and needs the same permission.

Version 1.0.22 is a manual-test delivery. Version 1.0.23 and its stable signed
update feed are in preparation; this document does not establish publication
or managed-workstation acceptance.

## Recommended IT workflow: capture the complete applications

Have IT use ThreatLocker's **Testing Environment** to catalog each complete
application, including its installed files, signatures and behavior. Exercise
installation, the real Desktop/Start Menu shortcut, representative bundled
tools, login startup and a signed update. If that environment is unsuitable,
ThreatLocker documents a scoped single-device **Installation Mode** as the
next option. IT controls the test scope and duration; fleet-wide Learning Mode
is not needed. [Maintenance Modes](https://threatlocker.kb.help/maintenance-modes/),
[Testing Environment](https://www.threatlocker.com/blog/testing-environment-your-questions-answered).

Then select the three applications and their captured dependency definitions
in **one permit policy** scoped to the tester device group. A policy can select
multiple application definitions. Do not select **All Applications**. Ask
ThreatLocker/CyberHero support to help convert changing version/hash matches
into reusable, constrained application rules for later releases. Capturing one
release does not automatically approve all future releases. The routes and
inventories below are evidence for that work, not a request for users to
maintain a separate policy for every file.
[Managing Application Policies](https://threatlocker.kb.help/managing-application-policies/),
[Creating Custom Rules](https://threatlocker.kb.help/creating-custom-rules/).

## Application routes for reusable 1.x rules

These are rule-authoring templates, not whole-folder permits. `<Downloads>` is
the actual Windows Downloads known folder, normally `C:\Users\*\Downloads`;
company redirection can change it. `<LocalAppData>` is normally
`C:\Users\*\AppData\Local`. Confirm both on the managed device. Combine paths
with the appropriate certificate and calling/creating-process constraints.

| Application | Downloaded installer: execute | Installed app: execute, including login receiver |
|---|---|---|
| Melange | `<Downloads>\melange-1.*-win32-x64.exe` | `<Downloads>\MelangeApplications\Melange-1.*\Melange.exe` |
| Mentat | `<Downloads>\mentat-1.*-win32-x64.exe` | `<Downloads>\MelangeApplications\Mentat-1.*\Mentat.exe` |
| Terrier | `<Downloads>\terrier-1.*-win32-x64.exe` | `<Downloads>\MelangeApplications\Terrier-1.*\Terrier.exe` |

| Application | Verified pending update installer: execute |
|---|---|
| Melange | `<Downloads>\MelangeApplications\updates\melange\pending\melange-1.*-win32-x64.exe` |
| Mentat | `<Downloads>\MelangeApplications\updates\mentat\pending\mentat-1.*-win32-x64.exe` |
| Terrier | `<Downloads>\MelangeApplications\updates\terrier\pending\terrier-1.*-win32-x64.exe` |

The downloaded filenames are canonical GitHub asset names. A browser duplicate
suffix or manually renamed file must be assessed using its actual audit path.
A future `2.*` release needs a policy revision. ThreatLocker supports `*` in
path rules; every populated rule parameter must still match. A stale filename
or fixed hash can therefore prevent an otherwise matching certificate rule
from applying. Never wildcard the certificate.
[Managing Application Definitions](https://threatlocker.kb.help/managing-application-definitions/),
[Creating Custom Rules](https://threatlocker.kb.help/creating-custom-rules/).

## Signatures and dependency file types

The release signer is `CN=Melange Systems Desktop Release (self-signed)`, with
certificate SHA-1 `0EBC9AD04E929CDD731EDB5D278A4143BC3D3D30`. Use that exact
certificate for the main executables, installers and native files actually
signed with it. ThreatLocker documents certificate-SHA matching for self-signed
certificates. A Windows trust-store change alone does not demonstrate that a
ThreatLocker rule matches.
[Managing Application Definitions](https://threatlocker.kb.help/managing-application-definitions/).

Existing vendor signatures are preserved. The 1.0.22 inventory includes these
publishers; precise certificate thumbprints and hashes are in the inventories.

| Preserved signer | Examples beneath the installed version folder |
|---|---|
| Python Software Foundation | Each app's `resources\runtime\<app>\python\python.exe` and signed Python libraries |
| Microsoft Windows Software Compatibility Publisher | Microsoft runtime DLLs inside the program and bundled tools |
| Microsoft Windows | Catalog-signed libraries such as `d3dcompiler_47.dll` and `dxil.dll` |
| OpenJS Foundation | Mentat's `resources\runtime\mentat\native\Node\node.exe` |
| The Document Foundation | Melange's `resources\runtime\melange\native\LibreOffice\` tools and libraries |

Other helpers, including Mentat's R tools, need their actual signer rather than
an assumed vendor certificate. The 1.0.22 native inventory contains `.exe`,
`.dll`, `.pyd`, `.com` and `.bin` files. `.pyd` files are Python native extension
modules; executable native files can also have `.com` or `.bin` extensions.
Use file identity and the audit operation, not only the extension.

- [1.0.22 signer summary: 13 certificates](deployment/desktop-1.0.22-signers.csv)
- [1.0.22 native signature inventory: 1,164 file rows](deployment/desktop-1.0.22-signature-inventory.csv)

These exports describe local inspection of 1.0.22, not 1.0.23 or work-PC
approval. `downloaded-installer/` denotes the installer asset; other paths are
relative to the version folder. `LocalSignatureStatus` is the inspecting PC's
result. A locally valid catalog signature does not prove the managed PC will
resolve that catalog or classify the file identically. Confirm the actual
certificate/hash in ThreatLocker.

Use matching dependency definitions constrained to packaged paths and intended
calling processes. Include interpreted resources if separately controlled,
using their actual packaged paths and parent process. Do not permit every
Python, Node or R interpreter, every DLL, or all content in Downloads. An
installer permit without its dependencies can still leave the app blocked.
[Permitting Software from the Approval Center](https://threatlocker.kb.help/permitting-software-from-the-approval-center/).

## Shortcuts and the login receiver

Interactive installation creates `<Product>.lnk` in the current user's Desktop
known folder and Start Menu Programs folder. The usual locations are
`%USERPROFILE%\Desktop\<Product>.lnk` and
`%APPDATA%\Microsoft\Windows\Start Menu\Programs\<Product>.lnk`; Desktop may be
redirected to OneDrive or another company location. Target and icon are the
installed `<Product>.exe`, with the version folder as working directory.
Updates retarget existing shortcuts and preserve a user's choice to remove one.

A `.lnk` is a shortcut, not another signed app or an execution approval. If its
target is denied, approving or recreating the shortcut does not allow it.
Inspect the target and calling process (for example, Windows Explorer), plus
any policy separately restricting shortcut creation.

The login receiver is the same installed app executable with
`--desktop-updater`; there is no separate elevated update service. After
successful extraction, the installer updates these per-user registry values:

```text
HKCU\Software\Microsoft\Windows\CurrentVersion\Run
org.melange.desktop.melange = "<Downloads>\MelangeApplications\Melange-<version>\Melange.exe" --desktop-updater
org.melange.desktop.mentat = "<Downloads>\MelangeApplications\Mentat-<version>\Mentat.exe" --desktop-updater
org.melange.desktop.terrier = "<Downloads>\MelangeApplications\Terrier-<version>\Terrier.exe" --desktop-updater
```

The installer also writes `InstallLocation` and `Version` beneath
`HKCU\Software\org.melange.desktop.<app>`. Scope those registry writes and permit
the installed app in its intended startup context. Blocking that executable
blocks both ordinary launch and the receiver.

## Signed updates, storage and recovery

Each app reads its configured public GitHub repository: `pjg93-222/Melange`,
`pjg93-222/Mentat`, or `pjg93-222/Geo` for Terrier. A stable `desktop-v<version>`
release must host the signed `<app>-win32-x64.manifest.json`, matching
`<app>-trust.json`, and `<app>-<version>-win32-x64.exe`. Packaged per-app keys
verify signed metadata and trust transitions; package hashes and pinned native
publisher verification gate installation. A source commit, draft, prerelease,
or unsigned GitHub asset is not an automatic update.

The receiver passes an accepted package through its verified loopback feed to
the native updater. The pending installer routes above execute with
`--updated /S`; a requested foreground relaunch adds `--force-run`, which
launches the new app with `--updated`. Each version installs into its own
folder. A silent background update retargets the next-login receiver without
opening the app immediately.

| Storage route | Use |
|---|---|
| `<LocalAppData>\org.melange.desktop.<app>\updater\updates\<sequence>\<package>.exe` | Verified package storage and recovery; read/write and hash checks |
| `<LocalAppData>\org.melange.desktop.<app>\baseline\<version>\<downloaded-installer-name>.exe` | Best-effort recovery copy from an interactive first install; preserves the downloaded filename |
| `<Downloads>\MelangeApplications\updates\<app>\pending\<package>.exe` | Native updater execution location after verification |

The storage rows do not request blanket execution permission. Recovery copies
are verified and staged through the same pending update route. Before the
first automatic upgrade, the running version needs its own signed recovery
manifest at its exact `desktop-v<running-version>` tag. The receiver retains
that manifest and locally available installer; if the copy is missing or
invalid, recovery needs the hosted package. Missing or invalid current-version
recovery metadata blocks activation. Baseline copying is retained for offline
recovery; silent updates do not repeat it.

Allow the scoped file, registry and network operations required by this flow,
including GitHub HTTPS metadata/assets and local backend/update-feed traffic.
Profiles and private data remain separate from program files. Discovery is
cached for six hours plus up to 30 minutes of jitter; 15-minute lifecycle checks
reuse that cache. Installation waits for safe close or a background session.
There is no promise of immediate synchronization with every GitHub commit.
See [the update lifecycle](README.md#update-lifecycle).

## Investigating a denial

Start with the actual request or Unified Audit event, including earlier events
from the same attempt. Record:

- Device, user and attempt time with time zone, shared only through approved IT channels.
- Full denied-file path, observed certificate, ThreatLocker hash and SHA-256 when available.
- Calling/parent process path, command line and Created By process when present.
- Action type, reason, matched application definition, policy name/ID and Effective Action.

Correlate Execute/Install and relevant Write, Registry or Network activity;
inspect Any Deny or Ringfenced events as appropriate. Distinguish an effective
denial from a simulated policy action. A later write error can follow an earlier
blocked dependency. Approval Center links the requested file and its process to
Unified Audit. [Approval Center](https://threatlocker.kb.help/using-the-approval-center/),
[Unified Audit](https://threatlocker.kb.help/using-the-threatlocker-unified-audit/).

Confirm the policy reached the test device, then record installation, shortcut
launch, next-login startup, update and recovery results. A source commit,
signed installer or local inventory alone does not establish work-PC
acceptance. Company IT owns the ThreatLocker policy; these changes do not
disable or bypass it.
