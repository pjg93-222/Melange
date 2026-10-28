# Installer-free desktop engineering handoff

This records the immutable Windows 1.0.20 engineering candidates built on
2026-10-27 and verified through 2026-10-28 UTC. The source change adds a true
directory ZIP distribution and authenticated ZIP updates for Melange, Mentat and
Terrier. No installer-free binary release or update feed has been published by
this work. Publishing source code does not publish these packages or activate
their update channel.

## Migration and future releases

For the one-time transition, quit the old app through its tray/menu, extract the
complete ZIP to `%USERPROFILE%\Downloads\MelangeApplications\<Product>-1.0.20`,
then open `<Product>.exe` there. Closing the old window can leave its background
process holding the shared single-instance lock. Keep the entire program tree
together. Preserve existing profiles, credentials, configured data locations and
data; manual uninstallation or profile deletion is unnecessary.

All three products use the same common desktop client, selected by application
configuration. Their backend sources remain separate. The old NSIS updater and
the new directory ZIP updater are distinct channels; an old installed client
needs the initial manual ZIP migration. A future release containing only the
legacy NSIS output will not update directory-mode clients. Keep channel handling
explicit while a mixed fleet remains.

Use this tested client baseline, or a reviewed descendant containing its ZIP
receiver, for subsequent directory builds. Establish the recovery baseline in
the authorized release channel by publishing each exact 1.0.20 ZIP identified
below with its authorized signed manifest **before higher versions are delivered
automatically**. A source-code commit alone does not establish that baseline.
Publication still requires the release gates and authorization described below.
Future directory releases require:

- The complete signed tree packaged as `<app>-<version>-win32-x64.zip`.
- A correctly authorized, signed
  `<app>-win32-x64-directory-zip.manifest.json`, with package format
  `windows-directory-zip-v1`, the exact product executable as `entrypoint`, and
  `minimumUpdaterVersion: "2.0.0"`. This is the updater implementation version;
  the candidate application version is 1.0.20.
- The independent pinned publisher proof covering the whole ZIP, plus the
  existing manifest authorization, sequence, identity and integrity gates.
- Final-byte verification, required acceptance, and authorized hosted-asset
  readback before release publication or update promotion.

The directory build wrapper does not replace the legacy build default or publish
an update. See [the distribution guide](DIRECTORY_DISTRIBUTION.md) for the build
specification and [the packaging guide](packaging/README.md) for release context.

## Invariants

The packaging change preserves profile identity, access/enrollment checks,
configured data and application-specific behavior. Updates stage a verified
version, activate it with readiness acknowledgement, and retain a verified
rollback version. Retention does not make arbitrary Downloads folders disposable.

Archive verification must use the authenticated ZIP's inventory, never an
unsigned inventory read from an installed directory. Preserve path, file-type,
resource-limit, archive-hash, publisher and native-signature checks. The approved
publisher thumbprint remains `0EBC9AD04E929CDD731EDB5D278A4143BC3D3D30`.
Application-owned native files require its timestamped signature; valid vendor
signatures retain their original bytes. Keep private signing material outside
source and artifacts. Recipient ThreatLocker approval remains an IT policy gate.

## Exact candidate baseline

The common desktop client/tooling commit for every candidate is
`9ef9eb75219d9ad122f13538d51c5bec853ad7e7`. Backend/source commits are recorded
separately:

| Product | Source repository | Backend/source commit |
|---|---|---|
| Melange | `pjg93-222/Melange` | `6461fb489dec83569c673511889ba7e9f5f959f8` |
| Mentat | `pjg93-222/Mentat` | `b817d6c0f11500ca6b7d0190ededf8f3077dcbcf` |
| Terrier | `pjg93-222/Geo` | `d6cf452bf688086c37e796d350399bae47865d72` |

| Final ZIP | SHA-256 |
|---|---|
| `melange-1.0.20-win32-x64.zip` | `b307a8b2e8eb8dc2ee20a3a6b2818ffcc9b91a54d214c6aa85f3f5df53854323` |
| `mentat-1.0.20-win32-x64.zip` | `ef1ca82d55335230be7374ead1eb3ba0007db1fcb1f6d1c3aca0ac9a0cf28e9b` |
| `terrier-1.0.20-win32-x64.zip` | `4ea628a9d044935376df3aca0796f28263fb721d31d29d9182e597e85d65474e` |

Later controller/verifier fixes through
`49daf7e7ff5715ea69760cc0815f1aa40b151431` did not change the frozen application
client. Each engineering receipt records the actual controller and verifier
commit/hash separately. The final packaged `directory-package.cjs` SHA-256 is
`b078600b102d0ae697c3bdbf3d4cecc8bbb415664c0017dfc091b62311500310`.

Terrier's dependency-only preparation separately records tooling
`6461fb489dec83569c673511889ba7e9f5f959f8` and reviewed Windows constraint inputs
at `79507944e6670b0e967896d586c6fcbceccec62b`. Preserve that dependency lineage
when reproducing the candidate; its final client remains the common commit above.
Use release tooling containing the constraint fixes for fresh future builds.

## Evidence and remaining gates

The frozen client suite recorded **803 passing tests**. All three final ZIPs
passed independent inventory, source/bootstrap, ASAR, publisher-proof and complete
native-signature checks: **544** native files for Melange, **310** for Mentat and
**306** for Terrier.

All three isolated package smokes passed. They started the packaged executable's
settings shell and preload IPC, checked the bundled backend interface and
unauthorized-request refusal, and confirmed unchanged program hashes afterward.
Temporary profiles supplied no production data or login. This did not exercise
full authenticated application startup or business workflows.

The following remain unaccepted: full authenticated workflows, an actual
end-to-end product update, the complete security and dependency/redistribution
release gates, hosted-asset readback, and execution under the recipient work PC's
ThreatLocker policy. The smoke results do not grant release approval.

Retained local evidence is organized as `final/<app>/engineering-receipt.json`,
`native-verification.json`, source/signing/proof records, and
`verification/<app>-final-smoke.json` with exact source-inventory reports.
`verification/build-history` preserves the retired scratch build's provenance
and logs. Evidence describes these exact bytes and its recorded environment.

## Coordination with concurrent work

These candidates were exported from explicit commits. Concurrent Claude changes
in other sections are not included in the tested ZIPs. Coordinate ownership of
the common desktop client and release tooling before integrating overlapping
edits; preserve each contributor's work. A new backend or client change requires
a new frozen source specification and a newly built, signed, verified immutable
release with fresh acceptance evidence. Do not patch these ZIPs or their ASARs in
place, reuse their receipts for changed bytes, or replace the frozen 1.0.20
candidate with different content under the same identity.
