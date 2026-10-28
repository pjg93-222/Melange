"""Small native-verifier fixtures; archive transport and OS verdicts are simulated.

PE header classification, source/ASAR/file-set checks, receipt binding and all
signature policy decisions run normally. No fixture executable is launched.
"""
import copy
import base64
import argparse
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

    def test_explicit_reference_overlays_bind_actual_paths_and_bytes_without_copying_runtime(self):
        original_files, original_pes, original_map = n.scan(self.program)
        overlay = self.root / "signed-overlay.exe"
        overlay.write_bytes(original_files["Melange.exe"].read_bytes() + b"reviewed version-resource overlay")
        files, pes, mapping = n.reference_overlays(original_files, original_pes, original_map, "melange", executable=overlay)
        self.assertEqual(original_map["Melange.exe"]["sha256"], n.legacy.digest(self.program / "Melange.exe"))
        self.assertNotEqual(original_map["Melange.exe"], mapping["Melange.exe"])
        receipt = copy.deepcopy(self.receipt)
        receipt.update(installerFormat="builtin-nsis-v1", installerPlugins=[])
        main = next(row for row in receipt["currentFiles"] if row["path"] == str(self.program / "Melange.exe"))
        main.update(self.row(overlay), payloadRelativePath="Melange.exe")
        kwargs = dict(installer=self.installer, program_directory=self.program, app_files=files, app_pes=pes,
                      app_map=mapping, nsis_files=files, nsis_pes=pes, nsis_map=mapping,
                      receipt=receipt, installer_format="builtin-nsis-v1", reference_files=files)
        items, _ = n.native_census(**kwargs)
        self.assertEqual(len(items), 4)
        main["path"] = str(self.program / "Melange.exe")
        with self.assertRaisesRegex(n.Refused, "actual reference input"):
            n.native_census(**kwargs)
        main["path"] = str(overlay)
        main["payloadRelativePath"] = "../Melange.exe"
        with self.assertRaises(n.Refused):
            n.native_census(**kwargs)

    def test_reference_overlay_cannot_change_native_classification(self):
        files, pes, mapping = n.scan(self.program)
        invalid = self.root / "not-an-executable.exe"
        invalid.write_bytes(b"not a Windows executable")
        with self.assertRaisesRegex(n.Refused, "native classification"):
            n.reference_overlays(files, pes, mapping, "melange", executable=invalid)

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
        def run(argv, **kwargs):
            commands.append([str(value) for value in argv])
            if "-EncodedCommand" in argv:
                command = base64.b64decode(argv[argv.index("-EncodedCommand") + 1]).decode("utf-16le")
                self.assertEqual(command, "& {\n" + n.legacy.PS + "\n} -InputList $env:DESKTOP_SIGNATURE_INPUT_LIST -OutputFile $env:DESKTOP_SIGNATURE_OUTPUT_FILE")
                output = Path(kwargs["env"]["DESKTOP_SIGNATURE_OUTPUT_FILE"])
                self.assertEqual(json.loads(Path(kwargs["env"]["DESKTOP_SIGNATURE_INPUT_LIST"]).read_text()),
                                 [{"id": "installer", "path": str(self.installer)}])
                self.assertEqual((output.parent / "inspect-signatures.ps1").read_text(), n.legacy.PS)
            else:
                output = Path(argv[argv.index("-OutputFile") + 1])
            output.write_text('[{"id":"installer"}]')
            return b""
        with mock.patch.object(n.legacy, "run", side_effect=run):
            for name, options in (("native-policy", {"preserve_execution_policy": True}), ("legacy-policy", {})):
                folder = self.root / name
                folder.mkdir()
                n.legacy.signatures({"installer": self.installer}, folder, **options)
        self.assertNotIn("-ExecutionPolicy", commands[0])
        self.assertNotIn("Bypass", commands[0])
        self.assertNotIn("-File", commands[0])
        self.assertIn("-EncodedCommand", commands[0])
        self.assertEqual(commands[1][commands[1].index("-ExecutionPolicy") + 1], "Bypass")

    def test_desktop_reserve_accepts16_and_refuses_below16_and_overbudget_extraction(self):
        self.assertEqual(n.free_floor_gib("16"), 16)
        with self.assertRaises(argparse.ArgumentTypeError):
            n.free_floor_gib("15")
        def run(argv, **_kwargs):
            if "l" in argv:
                return b"Path = fixture.txt\nSize = 1\n"
            destination = Path(next(arg[2:] for arg in argv if isinstance(arg, str) and arg.startswith("-o")))
            (destination / "fixture.txt").write_bytes(b"x")
            return b""
        with mock.patch.object(n.legacy, "run", side_effect=run), mock.patch.object(n.shutil, "disk_usage", return_value=SimpleNamespace(free=16 * n.GIB + 1)):
            self.assertEqual(n.extract(self.tool, self.installer, self.root / "reserve16", 1, reserve=16 * n.GIB), 1)
        with mock.patch.object(n.legacy, "run", side_effect=run), mock.patch.object(n.shutil, "disk_usage", return_value=SimpleNamespace(free=16 * n.GIB)):
            with self.assertRaisesRegex(n.Refused, "selected desktop workspace reserve"):
                n.extract(self.tool, self.installer, self.root / "under-reserve", 1, reserve=16 * n.GIB)
            self.assertFalse((self.root / "under-reserve").exists())

    def test_nsis_reader_capability_is_required(self):
        with mock.patch.object(n.legacy, "run", return_value=b"0  C  7z 7z\n"):
            with self.assertRaisesRegex(n.Refused, "NSIS-capable"):
                n.reader_capabilities(self.tool)
        with mock.patch.object(n.legacy, "run", return_value=b"0 ...F.G... Nsis nsis offset=4\n"):
            self.assertTrue(n.reader_capabilities(self.tool)["nsis"])

    def test_unknown_sizes_are_only_allowed_for_exact_nsis_member_closure(self):
        calls = []
        listing = "\n\n".join("Path = " + name + "\nSize = \n" for name in n.NSIS_MEMBERS).encode()
        def run(argv, **_kwargs):
            calls.append(argv)
            if "l" in argv:
                return listing
            destination = Path(next(arg[2:] for arg in argv if isinstance(arg, str) and arg.startswith("-o")))
            for name in n.NSIS_MEMBERS:
                file = destination / name
                file.parent.mkdir(exist_ok=True)
                file.write_bytes(b"x")
            return b""
        with mock.patch.object(n.legacy, "run", side_effect=run):
            self.assertEqual(n.extract(self.tool, self.installer, self.root / "unknown-nsis", n.GIB, reserve=16 * n.GIB, archive_format="Nsis"), 9)
            self.assertTrue(all("-tNsis" in command for command in calls))
            with self.assertRaisesRegex(n.Refused, "Missing or invalid"):
                n.extract(self.tool, self.installer, self.root / "unknown-inner", n.GIB, reserve=16 * n.GIB)
            listing += b"\n\nPath = unexpected.exe\nSize = \n"
            with self.assertRaisesRegex(n.Refused, "member set"):
                n.extract(self.tool, self.installer, self.root / "unexpected", n.GIB, reserve=16 * n.GIB, archive_format="Nsis")

    def test_unknown_nsis_sizes_still_reserve_space_before_extraction(self):
        listing = "\n\n".join("Path = " + name + "\nSize = \n" for name in n.NSIS_MEMBERS).encode()
        with mock.patch.object(n.legacy, "run", return_value=listing) as command, mock.patch.object(n.shutil, "disk_usage", return_value=SimpleNamespace(free=16 * n.GIB + 1)):
            with self.assertRaisesRegex(n.Refused, "selected desktop workspace reserve"):
                n.extract(self.tool, self.installer, self.root / "under-nsis-reserve", n.GIB, reserve=16 * n.GIB, archive_format="Nsis")
            self.assertEqual(command.call_count, 1)
            self.assertFalse((self.root / "under-nsis-reserve").exists())

    def test_direct_nsis_requires_exact_reference_and_reserves_actual_expanded_bytes(self):
        reference = {"Melange.exe": {"size": 3, "sha256": hashlib.sha256(b"app").hexdigest()},
                     "resources/app.asar": {"size": 4, "sha256": hashlib.sha256(b"asar").hexdigest()}}
        listing = b"Path = Melange.exe\nSize = \n\nPath = resources/app.asar\nSize = \n"
        calls = []
        def run(argv, **_kwargs):
            calls.append(argv)
            if "l" in argv:
                return listing
            destination = Path(next(arg[2:] for arg in argv if isinstance(arg, str) and arg.startswith("-o")))
            self.write_files(destination, {"Melange.exe": b"app", "resources/app.asar": b"asar"})
            return b""
        with mock.patch.object(n.legacy, "run", side_effect=run), mock.patch.object(n.shutil, "disk_usage", return_value=SimpleNamespace(free=16 * n.GIB + 7)):
            self.assertEqual(n.extract(self.tool, self.installer, self.root / "direct", 7, reserve=16 * n.GIB,
                                       archive_format="Nsis", expected_files=reference), 7)
            self.assertEqual(len(calls), 2)
            listing += b"\nPath = $PLUGINSDIR/System.dll\nSize = \n"
            with self.assertRaisesRegex(n.Refused, "Direct NSIS member set"):
                n.extract(self.tool, self.installer, self.root / "direct-plugin", 7, reserve=16 * n.GIB,
                          archive_format="Nsis", expected_files=reference)
            self.assertFalse((self.root / "direct-plugin").exists())
        listing = b"Path = Melange.exe\nSize = \n\nPath = resources/app.asar\nSize = \n"
        with mock.patch.object(n.legacy, "run", side_effect=run), mock.patch.object(n.shutil, "disk_usage", return_value=SimpleNamespace(free=16 * n.GIB + 6)):
            with self.assertRaisesRegex(n.Refused, "workspace reserve"):
                n.extract(self.tool, self.installer, self.root / "direct-reserve", 7, reserve=16 * n.GIB,
                          archive_format="Nsis", expected_files=reference)
            self.assertFalse((self.root / "direct-reserve").exists())

    def test_direct_nsis_rejects_declared_and_extracted_size_mismatch(self):
        reference = {"payload": {"size": 2, "sha256": hashlib.sha256(b"ab").hexdigest()}}
        listing = b"Path = payload\nSize = 3\n"
        def run(argv, **_kwargs):
            if "l" in argv:
                return listing
            destination = Path(next(arg[2:] for arg in argv if isinstance(arg, str) and arg.startswith("-o")))
            (destination / "payload").write_bytes(b"x")
            return b""
        with mock.patch.object(n.legacy, "run", side_effect=run):
            with self.assertRaisesRegex(n.Refused, "declared size"):
                n.extract(self.tool, self.installer, self.root / "direct-declared", 2, reserve=16 * n.GIB,
                          archive_format="Nsis", expected_files=reference)
            self.assertFalse((self.root / "direct-declared").exists())
            listing = b"Path = payload\nSize = \n"
            with self.assertRaisesRegex(n.Refused, "extracted sizes"):
                n.extract(self.tool, self.installer, self.root / "direct-size", 2, reserve=16 * n.GIB,
                          archive_format="Nsis", expected_files=reference)

    def test_direct_native_census_counts_program_once_and_refuses_extra_plugin(self):
        files, pes, mapping = n.scan(self.program)
        receipt = dict(self.receipt, installerFormat="builtin-nsis-v1", installerPlugins=[])
        args = dict(installer=self.installer, program_directory=self.program, app_files=files, app_pes=pes,
                    app_map=mapping, nsis_files=files, nsis_pes=pes, nsis_map=mapping, receipt=receipt,
                    installer_format="builtin-nsis-v1")
        items, expected = n.native_census(**args)
        self.assertEqual(len(items), 1 + len(pes))
        self.assertEqual(set(items), {"installer", *("app/" + name for name in pes)})
        self.assertEqual(set(expected), pes)
        receipt["installerPlugins"] = ["System.dll"]
        with self.assertRaisesRegex(n.Refused, "zero-plugin"):
            n.native_census(**args)
        receipt["installerPlugins"] = []
        args["nsis_files"] = {**files, "$PLUGINSDIR/System.dll": self.tool}
        with self.assertRaisesRegex(n.Refused, "Direct NSIS census"):
            n.native_census(**args)

    @unittest.skipUnless(os.name == "nt" and os.environ.get("NATIVE_VERIFIER_TEST_7Z") and os.environ.get("NATIVE_VERIFIER_TEST_NSIS"), "Explicit real7z/NSIS fixture tools required")
    def test_real_compiled_nsis_unknown_sizes_and_exact_inner7z_roundtrip(self):
        seven = Path(os.environ["NATIVE_VERIFIER_TEST_7Z"])
        compiler = Path(os.environ["NATIVE_VERIFIER_TEST_NSIS"])
        self.assertTrue(n.reader_capabilities(seven)["nsis"])
        member = self.root / "payload.txt"
        member.write_bytes(b"real archive fixture; never execute installer")
        inner = self.root / "inner.7z"
        n.legacy.run([seven, "a", "-t7z", inner, member])
        installer = self.root / "compiled-fixture.exe"
        script = self.root / "fixture.nsi"
        lines = ['Name "Native verifier fixture"', 'OutFile "' + str(installer) + '"', 'SetCompressor zlib', 'SetCompress force', 'Section', 'SetOutPath "$PLUGINSDIR"']
        for name in sorted(n.NSIS_MEMBERS):
            source = inner if name.endswith("/app-64.7z") else member
            lines.append('File /oname=' + name.split("/")[-1] + ' "' + str(source) + '"')
        script.write_text("\n".join([*lines, "SectionEnd", ""]), encoding="utf-8")
        n.legacy.run([compiler, "-V2", "-WX", script])
        listing = n.legacy.run([seven, "l", "-tNsis", "-slt", "-ba", installer]).decode()
        self.assertRegex(listing, r"Size = \r?\n")
        outer = self.root / "real-nsis"
        with n.locked_input(installer):
            used = n.extract(seven, installer, outer, n.GIB, reserve=16 * n.GIB, archive_format="Nsis")
        self.assertGreater(used, 0)
        self.assertEqual(set(n.legacy.tree(outer)), n.NSIS_MEMBERS)
        extracted = self.root / "real-inner"
        self.assertEqual(n.extract(seven, outer / "$PLUGINSDIR/app-64.7z", extracted, n.GIB, reserve=16 * n.GIB), member.stat().st_size)
        self.assertEqual((extracted / "payload.txt").read_bytes(), member.read_bytes())

    @unittest.skipUnless(os.name == "nt", "Windows input sharing semantics")
    def test_full_verifier_rejects_bad_native_verdict_and_passes_complete_fixture(self):
        args = SimpleNamespace(app="melange", version="1.0.21", installer=str(self.installer), program_directory=str(self.program),
            client=str(self.client), staged_sources=str(self.staged), client_commit="1" * 40, source_commit="2" * 40,
            trust_descriptor=str(self.trust), signing_receipt=str(self.receipt_path), seven_zip=str(self.tool),
            source=None, output=str(self.root / "inspection"), free_floor_gib=16)
        def extract(_seven, _archive, destination, _budget, *, reserve, archive_format="7z", expected_files=None):
            self.assertEqual(reserve, 16 * n.GIB)
            if expected_files is not None:
                self.assertEqual(archive_format, "Nsis")
                self.assertEqual(set(expected_files), set(self.payload))
            else:
                self.assertEqual(archive_format, "Nsis" if destination.name == "nsis" else "7z")
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
        with mock.patch.object(n, "reader_capabilities", return_value={"nsis": True}), mock.patch.object(n, "extract", side_effect=extract), mock.patch.object(n.legacy, "signatures", side_effect=signatures):
            with self.assertRaisesRegex(n.Refused, "not Valid"):
                n.verify(args)
            self.assertTrue(Path(args.output).is_dir(), "failed inspection remains reviewable")
            args.output = str(self.root / "inspection-passing")
            bad = False
            report = n.verify(args)
            args.output = str(self.root / "inspection-builtin")
            args.installer_format = "builtin-nsis-v1"
            self.receipt.update(installerFormat="builtin-nsis-v1", installerPlugins=[])
            self.persist()
            for name in n.BUILTIN_BUILD_INPUTS:
                if not (self.client / name).exists():
                    (self.client / name).write_bytes(b"reviewed builtin installer source")
            builtin_report = n.verify(args)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["freeFloorGiB"], 16)
        self.assertTrue(report["completeNativeCensus"])
        self.assertFalse(report["desktopUninstaller"])
        self.assertEqual(report["completeNativeCount"], 11)
        self.assertEqual(report["installerSha256"], n.legacy.digest(self.installer))
        self.assertEqual(report["noUninstaller"]["observedUninstallerFiles"], 0)
        self.assertEqual(builtin_report["status"], "passed")
        self.assertEqual(builtin_report["installerFormat"], "builtin-nsis-v1")
        self.assertEqual(builtin_report["nsisPluginCount"], 0)
        self.assertEqual(builtin_report["completeNativeCount"], 4)
        self.assertEqual(builtin_report["nsisPluginContract"]["files"], [])
        self.assertEqual(builtin_report["extractedBytes"], sum(map(len, self.payload.values())))


if __name__ == "__main__":
    unittest.main()
