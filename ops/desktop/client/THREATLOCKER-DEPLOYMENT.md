# ThreatLocker deployment: Melange, Mentat and Terrier

The plugin-free native installers use built-in NSIS operations and create no
uninstaller. Removing installer plug-ins does not grant permission to the
application, its runtimes or its dependencies. Version 1.0.22 is a manual-test
delivery; managed-workstation acceptance and stable rollout remain pending.

## Application and dependency coverage

Create or update the intended application definitions and permit policies for
each app, initially scoped to an approved test device or device group. Include
the downloaded installer, the installed application and the dependencies it
actually executes or loads. Approval Center supports reviewing associated
dependencies and existing matching applications. [ThreatLocker Approval Center](https://threatlocker.kb.help/using-the-approval-center/).

`<Downloads>` means the user's actual Windows Downloads location, including a
configured redirection. `<version>` changes with each release, for example
`1.0.22`.

| Application | Main executable | Bundled backend beneath its version folder |
|---|---|---|
| Melange | `<Downloads>\MelangeApplications\Melange-<version>\Melange.exe` | `resources\runtime\melange\python\python.exe` |
| Mentat | `<Downloads>\MelangeApplications\Mentat-<version>\Mentat.exe` | `resources\runtime\mentat\python\python.exe` |
| Terrier | `<Downloads>\MelangeApplications\Terrier-<version>\Terrier.exe` | `resources\runtime\terrier\python\python.exe` |

Cover the applicable Electron libraries, backend executables, DLLs, Python
extension modules (`.pyd`) and packaged helper tools. Mentat also bundles native
tooling such as R. Keep these dependencies tied to their intended application
and calling-process context; permitting every Python executable or every DLL
is not the deployment model.

Some native dependencies retain their original vendor signatures. They do not
all use the application's release certificate. Use matching dependency
definitions or scoped rules for the actual vendor-signed files; do not replace
their signatures to make a single publisher rule match everything.

The application release certificate's SHA-1 thumbprint is
`0EBC9AD04E929CDD731EDB5D278A4143BC3D3D30`. Confirm the certificate on the actual
audited file. ThreatLocker documents certificate-SHA matching for self-signed
certificates and requires every populated rule parameter to match. Review path,
filename, process, certificate and hash constraints together; fixed file hashes
need revision when their files change. This is rule-design guidance, not a
diagnosis that Windows certificate trust caused a particular denial.
[Managing Application Definitions](https://threatlocker.kb.help/managing-application-definitions/).

## Login receiver and update flow

The login receiver is the same installed app executable with
`--desktop-updater`; there is no separate elevated update service. After
successful extraction, the installer updates the per-user registry entry:

```text
HKCU\Software\Microsoft\Windows\CurrentVersion\Run
Value: org.melange.desktop.<app>
Command: "<Downloads>\MelangeApplications\<Product>-<version>\<Product>.exe" --desktop-updater
```

`<app>` is `melange`, `mentat` or `terrier`; `<Product>` is the corresponding
capitalized product name. The apps obtain releases from their configured GitHub
repositories: Melange, Mentat and Geo (Terrier), respectively.

Downloaded native updates execute from
`<Downloads>\MelangeApplications\updates\<app>\pending\` with
`--updated /S`. An interactive relaunch also supplies `--force-run`, which starts
the newly installed app with `--updated`. A silent update without that flag
updates the next-login receiver without launching the app immediately. Each
release installs into its own version folder. Ordinary interactive installation
also makes a best-effort recovery copy of its installer beneath
`%LOCALAPPDATA%\org.melange.desktop.<app>\baseline\<version>\`.

Retain the scoped process, file, registry and network permissions required by
that flow, including the intended GitHub release downloads and local backend
communication. Application profiles and access requirements remain in place.
Do not grant a blanket Downloads-folder permit or disable security controls.

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

Confirm that the intended policy reached the test device, then retry and record
installation, application startup, next-login startup and update results. A
source commit or signed installer alone does not establish work-PC acceptance.
