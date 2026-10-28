"""Small native-verifier fixtures; archive transport and OS verdicts are simulated.

PE header classification, source/ASAR/file-set checks, receipt binding and all
signature policy decisions run normally. No fixture executable is launched.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_native_release as n
from test_verify_signed_release import pe, asar_bytes


def main_pe(header_hash):
    """Real minimal resource-directory layout; no executable fixture is run."""
    raw = bytearray(pe()[:328])
    struct.pack_into("<H", raw, 70, 1)
    struct.pack_into("<II", raw, 216, 0x1000, 512)
    raw += b".rsrc\0\0\0" + struct.pack("<IIIIIIHHI", 512, 0x1000, 512, 512, 0, 0, 0, 0, 0x40000040)
    raw += b"\0" * (512 - len(raw))
    resource = bytearray(512)
    for offset, name, target, named in ((0, 0x80000000 | 96, 0x80000000 | 24, True),
                                      (24, 0x80000000 | 116, 0x80000000 | 48, True),
                                      (48, 0x409, 72, False)):
        struct.pack_into("<HHII", resource, offset + 12, int(named), int(not named), name, target)
    for offset, name in ((96, "INTEGRITY"), (116, "ELECTRONASAR")):
        value = struct.pack("<H", len(name)) + name.encode("utf-16le")
        resource[offset:offset + len(value)] = value
    payload = json.dumps([{"file": "resources\\app.asar", "alg": "SHA256", "value": header_hash}]).encode()
    struct.pack_into("<IIII", resource, 72, 0x1000 + 160, len(payload), 0, 0)
    resource[160:160 + len(payload)] = payload
    return bytes(raw + resource)


class NativeFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.program = self.root / "program"
        self.client = self.root / "export/ops/desktop/client"
        self.staged = self.root / "stage/sources"
        for folder in (self.program, self.client, self.staged):
            folder.mkdir(parents=True)
        self.installer = self.root / "Melange-1.0.21-win-x64.exe"
        self.installer.write_bytes(b"synthetic outer installer")
        self.tool = self.root / "7za-fixture.exe"
        self.tool.write_bytes(b"never executed")
        self.trust = self.root / "public-trust.json"
        self.trust.write_text(json.dumps({"fixturePublicTrust": True}))
        self.names = ["main.cjs", "native-signature.cjs", "updater.cjs", "github-source.cjs", "trust.cjs", "package.json"]
        self.original = {"name": "melange-desktop-client", "version": "1.0.21", "main": "main.cjs", "dependencies": {"electron-updater": "6.8.9"}}
        self.package = dict(self.original, name="melange-desktop", desktopAppConfig={"appId": "melange", "desktopUninstaller": False,
            "windowsPublisherName": "CN=Melange Systems Desktop Release (self-signed)",
            "desktopUpdateSource": {"provider": "github", "repository": "pjg93-222/Melange"}, "desktopAccessTrust": {"fixturePublicTrust": True}})
        members = {}
        for name in self.names:
            content = json.dumps(self.original).encode() if name == "package.json" else b"const PUBLISHER_PIN_ENFORCE=true;" if name == "native-signature.cjs" else b"frozen application code"
            (self.client / name).write_bytes(content)
            members[name] = json.dumps(self.package).encode() if name == "package.json" else content
        (self.client / "release-files.cjs").write_text("module.exports=Object.freeze(" + repr(self.names) + ");")
        for name in n.BUILD_INPUTS:
            (self.client / name).write_bytes(b"reviewed frozen build input")
        (self.client / "melange-systems-desktop-release.cer").write_bytes(b"public certificate fixture")
        packaging = self.client.parent / "packaging"
        packaging.mkdir()
        (packaging / "build_runtime.py").write_text("BOOTSTRAP_FILES=('desktop_backend.py',)\n")
        (packaging / "desktop_backend.py").write_bytes(b"frozen bootstrap")
        (self.staged / "server.py").write_bytes(b"sanitized gated source")
        (self.staged.parent / "source-inventory.json").write_text('["server.py"]')
        archive = asar_bytes(members)
        header_size = struct.unpack_from("<I", archive, 12)[0]
        self.header_hash = hashlib.sha256(archive[16:16 + header_size]).hexdigest()
        self.payload = {"Melange.exe": main_pe(self.header_hash), "resources/elevate.exe": pe(b"elevation"), "resources/vendor.dll": pe(b"vendor"),
                        "resources/app.asar": archive, "resources/melange-systems-desktop-release.cer": b"public certificate fixture",
                        "resources/runtime/melange/sources/server.py": b"sanitized gated source",
                        "resources/runtime/melange/bootstrap/desktop_backend.py": b"frozen bootstrap", "resources/runtime/melange/source-inventory.json": b'["server.py"]'}
        self.write_files(self.program, self.payload)
        self.outer = {"$PLUGINSDIR/app-64.7z": b"synthetic inner archive", **{"$PLUGINSDIR/" + name: pe(name.encode()) for name in n.NATIVE_PLUGINS}}
        self.receipt_path = Path(str(self.installer) + ".signatures.json")
        current = [self.row(self.installer)] + [self.row(self.program / rel, vendor=rel.endswith("vendor.dll")) for rel in ("Melange.exe", "resources/elevate.exe", "resources/vendor.dll")]
        history = copy.deepcopy(current)
        for rel, data in self.outer.items():
            if rel.endswith(".dll"):
                digest = hashlib.sha256(data).hexdigest()
                history.append({"path": str(self.root / "private-plugins" / Path(rel).name), "sha256": digest, "beforeSha256": digest,
                                "status": "Valid", "thumbprint": n.legacy.PIN, "timestamped": True, "preserved": True, "signed": False})
        self.receipt = {"schemaVersion": 1, "appId": "melange", "certificateThumbprint": n.legacy.PIN, "installer": str(self.installer),
                        "desktopUninstaller": False, "uninstallerEvidence": "intentionally-absent", "files": history, "currentFiles": current}
        self.persist()

    @staticmethod
    def write_files(root, files):
        for name, data in files.items():
            file = root / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(data)

    def row(self, file, vendor=False):
        digest = n.legacy.digest(file)
        return {"path": str(file), "sha256": digest, "beforeSha256": digest, "status": "Valid",
                "thumbprint": "A" * 40 if vendor else n.legacy.PIN, "timestamped": not vendor, "preserved": True, "signed": False}

    def persist(self):
        self.receipt_path.write_text(json.dumps(self.receipt))

    def census(self):
        files, pes, mapping = n.scan(self.program)
        outer_root = self.root / "outer"
        outer_root.mkdir(exist_ok=True)
        self.write_files(outer_root, self.outer)
        outer_files, outer_pes, outer_map = n.scan(outer_root)
        return n.native_census(installer=self.installer, program_directory=self.program, app_files=files, app_pes=pes,
            app_map=mapping, nsis_files=outer_files, nsis_pes=outer_pes, nsis_map=outer_map, receipt=self.receipt)

    def test_header_census_includes_extensionless_images_and_requires_their_evidence(self):
        items, expected = self.census()
        self.assertEqual(len(items), 1 + 3 + 7)
        self.assertEqual(len(expected), 3)
        (self.program / "native-without-extension").write_bytes(pe(b"hidden"))
        with self.assertRaisesRegex(n.Refused, "header census"):
            self.census()

    def test_unknown_native_plugin_or_changed_plugin_bytes_fail(self):
        self.outer["$PLUGINSDIR/hidden.dat"] = pe(b"hidden")
        with self.assertRaisesRegex(n.Refused, "exact seven"):
            self.census()
        del self.outer["$PLUGINSDIR/hidden.dat"]
        (self.root / "outer/$PLUGINSDIR/hidden.dat").unlink()
        self.outer["$PLUGINSDIR/System.dll"] = pe(b"changed")
        with self.assertRaisesRegex(n.Refused, "signed private toolset"):
            self.census()

    def test_vendor_before_hash_and_original_signer_are_preserved(self):
        vendor = next(row for row in self.receipt["files"] if row["path"].endswith("vendor.dll"))
        vendor["beforeSha256"] = "0" * 64
        with self.assertRaisesRegex(n.Refused, "vendor image"):
            self.census()

    def test_main_integrity_must_match_the_actual_asar_header(self):
        main = self.program / "Melange.exe"
        n.verify_asar_integrity(main, self.header_hash)
        with self.assertRaisesRegex(n.Refused, "ASAR integrity"):
            n.verify_asar_integrity(main, "0" * 64)
        main.write_bytes(pe(b"missing integrity resource"))
        with self.assertRaisesRegex(n.Refused, "ASAR integrity"):
            n.verify_asar_integrity(main, self.header_hash)

    def sources(self):
        files, _, mapping = n.scan(self.program)
        members = n.legacy.asar(files["resources/app.asar"])[1]
        return n.verify_sources(app="melange", version="1.0.21", program_files=files, program_map=mapping, members=members,
                                client=self.client, staged=self.staged, trust=self.trust)

    def test_exact_source_bootstrap_receiver_and_member_sets_are_bound(self):
        evidence, package = self.sources()
        self.assertEqual(package["desktopAppConfig"]["desktopUninstaller"], False)
        self.assertEqual(len(evidence["runtimeSources"]), 1)
        (self.staged / "server.py").write_bytes(b"changed gated stage")
        with self.assertRaisesRegex(n.Refused, "Gated runtime sources"):
            self.sources()
        (self.staged / "server.py").write_bytes(b"sanitized gated source")
        (self.client / "updater.cjs").write_bytes(b"different updater")
        with self.assertRaisesRegex(n.Refused, "ASAR source differs"):
            self.sources()

    def test_public_certificate_must_equal_the_frozen_release_input(self):
        (self.client / "melange-systems-desktop-release.cer").write_bytes(b"wrong public certificate")
        with self.assertRaisesRegex(n.Refused, "public release certificate"):
            self.sources()

    def test_native_signature_command_preserves_policy_and_legacy_default_is_unchanged(self):
        commands = []
        def run(argv, **_kwargs):
            commands.append([str(value) for value in argv])
            Path(argv[argv.index("-OutputFile") + 1]).write_text('[{"id":"installer"}]')
            return b""
        with mock.patch.object(n.legacy, "run", side_effect=run):
            for name, options in (("native-policy", {"preserve_execution_policy": True}), ("legacy-policy", {})):
                folder = self.root / name
                folder.mkdir()
                n.legacy.signatures({"installer": self.installer}, folder, **options)
        self.assertNotIn("-ExecutionPolicy", commands[0])
        self.assertNotIn("Bypass", commands[0])
        self.assertEqual(commands[1][commands[1].index("-ExecutionPolicy") + 1], "Bypass")

    @unittest.skipUnless(os.name == "nt", "Windows input sharing semantics")
    def test_full_verifier_rejects_bad_native_verdict_and_passes_complete_fixture(self):
        args = SimpleNamespace(app="melange", version="1.0.21", installer=str(self.installer), program_directory=str(self.program),
            client=str(self.client), staged_sources=str(self.staged), client_commit="1" * 40, source_commit="2" * 40,
            trust_descriptor=str(self.trust), signing_receipt=str(self.receipt_path), seven_zip=str(self.tool),
            source=None, output=str(self.root / "inspection"))
        def extract(_seven, _archive, destination, _budget):
            destination.mkdir()
            files = self.outer if destination.name == "nsis" else self.payload
            self.write_files(destination, files)
            return sum(map(len, files.values()))
        bad = True
        def signatures(items, _output, *, preserve_execution_policy):
            self.assertIs(preserve_execution_policy, True)
            return {key: {"id": key, "sha256": n.legacy.digest(file), "status": "NotSigned" if bad and key == "app/Melange.exe" else "Valid",
                "thumbprint": "A" * 40 if key == "app/resources/vendor.dll" else n.legacy.PIN,
                "signatureType": "Authenticode", "timestampSubject": "DigiCert fixture", "fileVersion": "1.0.21", "productVersion": "1.0.21"}
                for key, file in items.items()}
        with mock.patch.object(n, "extract", side_effect=extract), mock.patch.object(n.legacy, "signatures", side_effect=signatures):
            with self.assertRaisesRegex(n.Refused, "not Valid"):
                n.verify(args)
            self.assertTrue(Path(args.output).is_dir(), "failed inspection remains reviewable")
            args.output = str(self.root / "inspection-passing")
            bad = False
            report = n.verify(args)
        self.assertEqual(report["status"], "passed")
        self.assertTrue(report["completeNativeCensus"])
        self.assertFalse(report["desktopUninstaller"])
        self.assertEqual(report["completeNativeCount"], 11)
        self.assertEqual(report["installerSha256"], n.legacy.digest(self.installer))
        self.assertEqual(report["noUninstaller"]["observedUninstallerFiles"], 0)


if __name__ == "__main__":
    unittest.main()
