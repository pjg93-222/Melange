# Native installers without an uninstaller

The requested Windows distribution retains the existing NSIS installer for
Melange, Mentat, and Terrier. It removes application uninstaller generation and
execution. The separate installer-free ZIP prototype is superseded.

The shared client builds all three applications. Its reviewed, hash-pinned NSIS
template omits the uninstaller build/sign/embed pass and both previous-version
uninstaller calls. Installs and updates use version folders under the user's
Downloads\MelangeApplications directory, preserving older versions and profiles.
After successful installation, the per-user Windows login entry points to the
new executable with `--desktop-updater`. The Windows application entry has no
Uninstall command.

The existing GitHub receiver checks signed release manifests, verifies package
hashes and the approved Windows publisher, and installs eligible newer releases.
It receives published releases, not arbitrary repository commits. Background
updates depend on the receiver running, network access, a valid signed recovery
baseline, and endpoint policy allowing the installer and its components. A
1.0.19 installation without its exact recovery release needs one manual install
of a new fully published release before subsequent automatic updates can work.

Use `release_from_main.py` for release gates. Default sources remain origin/main;
an explicit `--source-commit APP=40HEX` selects a committed source that must also
exist on GitHub. Receipts record that exact commit. Existing runtime reuse must
pass requirement, provenance, source, dependency, and packaged-runtime checks.

`verify_native_release.py` independently extracts the final installer and checks
the complete file set, all native binaries, signatures, vendor preservation,
ASAR integrity, frozen sources/configuration, and the absence of uninstallers.
The absence contract requires matching package metadata and signing evidence;
it does not waive any other signature check. The legacy verifier retains its
original default and accepts absence only with its explicit opt-in.

Publish new immutable assets and signed native update metadata only after all
release gates and hosted-byte readback pass. Share GitHub release download URLs,
not temporary redirected `release-assets.githubusercontent.com` URLs. Passing
local checks does not establish ThreatLocker approval on a recipient computer.
