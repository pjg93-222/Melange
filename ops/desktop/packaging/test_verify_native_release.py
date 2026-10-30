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
            builtin_bytes = sum(map(len, self.payload.values()))
            # The original runtime remains old; the independently inspected
            # archive and frozen bootstrap must contain the reviewed replacement.
            relative = "resources/runtime/melange/bootstrap/terrier_standalone.py"
            old, new = b"old reviewed bootstrap", b"new reviewed bootstrap"
            self.write_files(self.program, {relative: old})
            self.payload[relative] = new
            packaging = self.client.parent / "packaging"
            (packaging / "build_runtime.py").write_text("BOOTSTRAP_FILES=('desktop_backend.py','terrier_standalone.py')\n")
            (packaging / "terrier_standalone.py").write_bytes(new)
            provenance_relative = "resources/runtime/melange/source-provenance.json"
            old_provenance = b'{"retained":"previous inspected provenance"}'
            self.write_files(self.program, {provenance_relative: old_provenance})
            provenance = {"schemaVersion": 1, "app": args.app, "version": args.version,
                "sourceCommit": args.source_commit, "commonClientCommit": args.client_commit, "bootstrapCommit": args.client_commit,
                "previousRuntimeProvenanceSha256": hashlib.sha256(old_provenance).hexdigest(),
                "sourceOrigin": {"kind": "retained-verified-export", "baseSourceCommit": args.source_commit, "sourceFileCount": 1}}
            provenance_bytes = json.dumps(provenance).encode()
            (self.staged.parent / "source-provenance.json").write_bytes(provenance_bytes)
            self.payload[provenance_relative] = provenance_bytes
            manifest = self.root / "source-overlay/manifest.json"
            self.write_files(manifest.parent / "files", {relative: new, provenance_relative: provenance_bytes})
            manifest.write_text(json.dumps({"schemaVersion": 1, "appId": args.app, "version": args.version,
                "clientCommit": args.client_commit, "sourceCommit": args.source_commit,
                "files": [{"path": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
                          for name, raw in ((relative, new), (provenance_relative, provenance_bytes))]}))
            args.source_overlay = str(manifest)
            args.output = str(self.root / "inspection-source-overlay")
            source_report = n.verify(args)
            self.assertEqual(source_report["status"], "passed")
            self.assertEqual((self.program / relative).read_bytes(), old)
            self.assertEqual(source_report["sourceOverlay"]["sha256"], n.legacy.digest(manifest))
            for label, target, raw, failure in (
                    ("overlay", manifest.parent / "files" / relative, b"changed after extraction", "overlay bytes differ"),
                    ("base", self.program / relative, b"changed retained base", "Final signed program input"),
                    ("extra", manifest.parent / "files/extra.py", b"unexpected closure", "inventory is not closed")):
                def mutate(items, output, **kwargs):
                    rows = signatures(items, output, **kwargs)
                    if any(key.startswith("app/") for key in items):
                        target.write_bytes(raw)
                    return rows
                args.output = str(self.root / ("inspection-source-mutation-" + label))
                with mock.patch.object(n.legacy, "signatures", side_effect=mutate), self.assertRaisesRegex(n.Refused, failure):
                    n.verify(args)
                if label == "extra":
                    target.unlink()
                else:
                    target.write_bytes(new if label == "overlay" else old)
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
        self.assertEqual(builtin_report["extractedBytes"], builtin_bytes)


class SourceOverlayFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.program = self.root / "base"
        self.name = "resources/runtime/terrier/sources/server/research/street_views.py"
        self.manifest = self.root / "overlay/manifest.json"
        self.data = b"reviewed new guard\n"
        NativeFixture.write_files(self.program, {self.name: b"old guard", "vendor.dll": pe(b"retained vendor")})
        NativeFixture.write_files(self.manifest.parent / "files", {self.name: self.data})
        self.value = {"schemaVersion": 1, "appId": "terrier", "version": "1.0.31",
            "clientCommit": "a" * 40, "sourceCommit": "b" * 40,
            "files": [{"path": self.name, "bytes": len(self.data), "sha256": hashlib.sha256(self.data).hexdigest()}]}
        self.save()

    def save(self):
        self.manifest.write_text(json.dumps(self.value))

    def run_overlay(self):
        return n.source_overlays(*n.scan(self.program), "terrier", "1.0.31", self.manifest, "a" * 40, "b" * 40)

    def test_exact_replacement_preserves_base_and_vendor_census(self):
        original = n.scan(self.program)
        files, pes, mapping, inputs, binding = self.run_overlay()
        self.assertEqual(pes, original[1])
        self.assertEqual(mapping["vendor.dll"], original[2]["vendor.dll"])
        self.assertEqual(set(mapping), set(original[2]))
        self.assertEqual(mapping[self.name]["sha256"], hashlib.sha256(self.data).hexdigest())
        self.assertEqual((self.program / self.name).read_bytes(), b"old guard")
        self.assertEqual(len(inputs), 2)
        self.assertEqual(binding["sourceCommit"], "b" * 40)

    def test_frozen_commit_version_and_app_must_match(self):
        for key, value in (("clientCommit", "c" * 40), ("sourceCommit", "d" * 40), ("version", "1.0.30"), ("appId", "melange")):
            with self.subTest(key=key):
                old = self.value[key]
                self.value[key] = value
                self.save()
                with self.assertRaisesRegex(n.Refused, "identity differs"):
                    self.run_overlay()
                self.value[key] = old

    def test_paths_are_exact_and_closed_without_new_or_vendor_members(self):
        for name in ("../outside.py", "C:/outside.py", self.name.upper(), self.name.replace("/", "\\"),
                     "resources/runtime/mentat/sources/server/research/street_views.py", "vendor.dll",
                     "resources/runtime/terrier/bootstrap/terrier_standalone.py"):
            with self.subTest(path=name):
                self.value["files"][0]["path"] = name
                self.save()
                with self.assertRaisesRegex(n.Refused, "Invalid source overlay member"):
                    self.run_overlay()

    def test_duplicate_member_unknown_field_and_boolean_size_are_refused(self):
        self.value["files"].append(dict(self.value["files"][0]))
        self.save()
        with self.assertRaisesRegex(n.Refused, "Invalid source overlay member"):
            self.run_overlay()
        self.value["files"].pop()
        self.value["files"][0]["bytes"] = True
        self.save()
        with self.assertRaisesRegex(n.Refused, "Invalid source overlay member"):
            self.run_overlay()
        self.value["unexpected"] = "authority"
        self.save()
        with self.assertRaisesRegex(n.Refused, "identity differs"):
            self.run_overlay()

    def test_changed_bytes_and_extra_files_are_refused(self):
        source = self.manifest.parent / "files" / self.name
        source.write_bytes(b"tampered source")
        with self.assertRaisesRegex(n.Refused, "bytes differ"):
            self.run_overlay()
        source.write_bytes(self.data)
        (self.manifest.parent / "files/extra.py").write_bytes(b"extra")
        with self.assertRaisesRegex(n.Refused, "inventory is not closed"):
            self.run_overlay()

    def test_header_identified_native_image_under_python_name_is_refused(self):
        raw = pe(b"disguised image")
        (self.manifest.parent / "files" / self.name).write_bytes(raw)
        self.value["files"][0].update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        self.save()
        with self.assertRaisesRegex(n.Refused, "native images"):
            self.run_overlay()

    def test_hardlinked_input_is_refused(self):
        os.link(self.manifest.parent / "files" / self.name, self.root / "alias.py")
        with self.assertRaisesRegex(n.Refused, "physical"):
            self.run_overlay()

    def test_duplicate_json_properties_are_refused(self):
        self.manifest.write_text('{"schemaVersion":1,' + json.dumps(self.value)[1:])
        with self.assertRaisesRegex(n.Refused, "Duplicate source overlay property"):
            self.run_overlay()

    def composite_provenance(self):
        original = n.scan(self.program)[2]
        final = self.run_overlay()[2]
        prefix = "resources/runtime/terrier/"
        old = b'{"sourceCommit":"' + b"c" * 40 + b'"}'
        original[prefix + "source-provenance.json"] = {"sha256": hashlib.sha256(old).hexdigest(), "size": len(old)}
        proof = {"status": "passed", "provenanceKind": "composite-retained-export-plus-exact-git-override",
            "baseSourceCommit": "c" * 40, "overrideSourceCommit": "b" * 40, "sharedBootstrapCommit": "d" * 40,
            "changedGitPaths": ["server/research/street_views.py"], "sourceFileCount": 1, "gitBackedFileCount": 1,
            "retainedExportFileCount": 0, "override": {"bytes": len(self.data), "sha256": hashlib.sha256(self.data).hexdigest()},
            "files": [{"path": "server/research/street_views.py", "origin": "git-blob", "matchesPublished30Native": True,
                       "bytes": len(b"old guard"), "baseSha256": hashlib.sha256(b"old guard").hexdigest(),
                       "effectiveSha256": hashlib.sha256(self.data).hexdigest()}]}
        proof_path = self.root / "origin-proof.json"
        proof_path.write_text(json.dumps(proof))
        provenance = {"schemaVersion": 1, "app": "terrier", "version": "1.0.31", "sourceCommit": "b" * 40,
            "commonClientCommit": "a" * 40, "bootstrapCommit": "a" * 40,
            "previousRuntimeProvenanceSha256": hashlib.sha256(old).hexdigest(),
            "sourceOrigin": {"kind": proof["provenanceKind"], "baseSourceCommit": "c" * 40,
                "proofSha256": n.legacy.digest(proof_path), "sharedBootstrapSourceCommit": "d" * 40,
                "sourceFileCount": 1, "gitBackedFileCount": 1, "retainedExportFileCount": 0}}
        stage = self.root / "stage/sources"
        stage.mkdir(parents=True)
        expected = stage.parent / "source-provenance.json"
        def save():
            expected.write_text(json.dumps(provenance))
            final[prefix + "source-provenance.json"] = {"sha256": n.legacy.digest(expected), "size": expected.stat().st_size}
        save()
        args = dict(app="terrier", version="1.0.31", client_commit="a" * 40, source_commit="b" * 40,
            staged=stage, program_map=final, original_reference=original, origin_proof=proof_path)
        return args, provenance, proof, proof_path, save

    def test_composite_provenance_binds_origin_proof_and_exact_source_map(self):
        args, provenance, proof, proof_path, save = self.composite_provenance()
        result = n.source_provenance(**args)
        self.assertEqual(result["kind"], "composite-retained-export-plus-exact-git-override")
        self.assertEqual(result["originProofSha256"], n.legacy.digest(proof_path))
        args["program_map"][self.name] = {"size": len(self.data), "sha256": "0" * 64}
        with self.assertRaisesRegex(n.Refused, "differs from packaged source"):
            n.source_provenance(**args)

    def test_old_or_misleading_provenance_cannot_pass_with_correct_source_manifest(self):
        args, provenance, proof, proof_path, save = self.composite_provenance()
        args["program_map"]["resources/runtime/terrier/source-provenance.json"] = args["original_reference"]["resources/runtime/terrier/source-provenance.json"]
        with self.assertRaisesRegex(n.Refused, "differs from gated provenance"):
            n.source_provenance(**args)
        save()
        provenance["sourceOrigin"]["kind"] = "clean-git-export"
        save()
        with self.assertRaisesRegex(n.Refused, "origin identity differs"):
            n.source_provenance(**args)

    def test_origin_proof_mutation_missing_proof_and_wrong_counts_are_refused(self):
        args, provenance, proof, proof_path, save = self.composite_provenance()
        with self.assertRaisesRegex(n.Refused, "proof is required"):
            n.source_provenance(**dict(args, origin_proof=None))
        proof_path.write_text(json.dumps(proof) + "\n")
        with self.assertRaisesRegex(n.Refused, "origin identity differs"):
            n.source_provenance(**args)
        provenance["sourceOrigin"]["proofSha256"] = n.legacy.digest(proof_path)
        provenance["sourceOrigin"]["retainedExportFileCount"] = 1
        save()
        with self.assertRaisesRegex(n.Refused, "origin counts differ"):
            n.source_provenance(**args)


class MelangeCompositeFixture(unittest.TestCase):
    """One real frozen reader blob plus otherwise identical retained fixture files."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.prefix = "resources/runtime/melange/"
        self.name = "fec/surfaces/melange_public_data.py"
        self.client = self.root / "frozen/ops/desktop/client"
        self.client.mkdir(parents=True)
        self.reader = self.root / "frozen" / self.name
        self.reader.parent.mkdir(parents=True)
        self.raw = b"reviewed exact frozen reader\n"
        self.reader.write_bytes(self.raw)
        self.commit = "a" * 40
        sha = hashlib.sha256(self.raw).hexdigest()
        blob = hashlib.sha1(b"blob " + str(len(self.raw)).encode() + b"\0" + self.raw).hexdigest()
        old = b"retained approved reader"
        old_provenance = b'{"retainedSourceCommit":"' + b"b" * 40 + b'"}'
        self.original = {
            self.prefix + "sources/" + self.name: {"size": len(old), "sha256": hashlib.sha256(old).hexdigest()},
            self.prefix + "sources/untouched.py": {"size": 9, "sha256": "c" * 64},
            self.prefix + "source-provenance.json": {"size": len(old_provenance), "sha256": hashlib.sha256(old_provenance).hexdigest()}}
        self.program = copy.deepcopy(self.original)
        self.program[self.prefix + "sources/" + self.name] = {"size": len(self.raw), "sha256": sha}
        self.freeze_path = self.root / "frozen/source-freeze-evidence.json"
        self.freeze = {"schemaVersion": 1, "status": "passed-committed-source-freeze", "sourceClientCommit": self.commit,
            "readerGitBlob": {"path": self.name, "gitObject": blob, "bytes": len(self.raw), "sha256": sha},
            "readerMatchesExactGitBlob": True, "protectedResidueWritten": False, "archiveContainsProtectedResidue": False,
            "before": {"head": self.commit, "remoteBranchCommit": self.commit, "trackedStatus": ""},
            "after": {"head": self.commit, "remoteBranchCommit": self.commit, "trackedStatus": ""}}
        self.proof_path = self.root / "origin-proof.json"
        self.proof = {"schemaVersion": 1, "appId": "melange", "status": "passed",
            "provenanceKind": "composite-retained-export-plus-exact-git-override", "baseSourceCommit": "b" * 40,
            "overrideSourceCommit": self.commit, "sharedBootstrapCommit": self.commit,
            "sourceFileCount": 2, "gitOverrideFileCount": 1, "retainedExportFileCount": 1, "changedGitPaths": [self.name],
            "baseReader": {"bytes": len(old), "sha256": hashlib.sha256(old).hexdigest()},
            "override": {"path": str(self.reader), "bytes": len(self.raw), "sha256": sha, "gitBlob": blob},
            "sourceFreezeEvidence": {"path": str(self.freeze_path), "sha256": ""}}
        self.staged = self.root / "stage/sources"
        self.staged.mkdir(parents=True)
        self.provenance = {"schemaVersion": 1, "app": "melange", "version": "1.0.32", "sourceCommit": self.commit,
            "commonClientCommit": self.commit, "bootstrapCommit": self.commit,
            "previousRuntimeProvenanceSha256": hashlib.sha256(old_provenance).hexdigest(),
            "sourceOrigin": {"kind": self.proof["provenanceKind"], "baseSourceCommit": "b" * 40,
                "proofSha256": "", "sharedBootstrapSourceCommit": self.commit,
                "sourceFileCount": 2, "gitOverrideFileCount": 1, "retainedExportFileCount": 1}}
        self.save()

    def save(self):
        self.freeze_path.write_text(json.dumps(self.freeze))
        self.proof["sourceFreezeEvidence"]["sha256"] = n.legacy.digest(self.freeze_path)
        self.proof_path.write_text(json.dumps(self.proof))
        self.provenance["sourceOrigin"]["proofSha256"] = n.legacy.digest(self.proof_path)
        path = self.staged.parent / "source-provenance.json"
        path.write_text(json.dumps(self.provenance))
        self.program[self.prefix + "source-provenance.json"] = {"size": path.stat().st_size, "sha256": n.legacy.digest(path)}

    def verify(self, **overrides):
        args = dict(app="melange", version="1.0.32", client_commit=self.commit, source_commit=self.commit,
            staged=self.staged, program_map=self.program, original_reference=self.original,
            origin_proof=self.proof_path, client=self.client)
        return n.source_provenance(**dict(args, **overrides))

    def test_exact_git_reader_and_unchanged_retained_closure_pass(self):
        self.assertEqual(self.verify()["originProofSha256"], n.legacy.digest(self.proof_path))
        self.assertEqual(self.verify()["sourceFileCount"], 2)

    def test_missing_proof_or_frozen_export_and_unrelated_source_changes_refuse(self):
        for change in ({"origin_proof": None}, {"client": None}):
            with self.subTest(change=change), self.assertRaisesRegex(n.Refused, "proof and frozen client are required"):
                self.verify(**change)
        self.program[self.prefix + "sources/untouched.py"]["sha256"] = "d" * 64
        with self.assertRaisesRegex(n.Refused, "unapproved retained member"):
            self.verify()
        self.program[self.prefix + "sources/untouched.py"] = self.original[self.prefix + "sources/untouched.py"]
        self.program[self.prefix + "sources/extra.py"] = {"size": 1, "sha256": "e" * 64}
        with self.assertRaisesRegex(n.Refused, "changed the retained source closure"):
            self.verify()

    def test_origin_commit_count_base_and_blob_claims_cannot_grant_authority(self):
        baseline = copy.deepcopy(self.proof)
        for mutate, reason in (
            (lambda v: v.update(overrideSourceCommit="d" * 40), "origin identity differs"),
            (lambda v: v.update(changedGitPaths=["untouched.py"]), "origin identity differs"),
            (lambda v: v.update(sourceFileCount=3), "origin counts differ"),
            (lambda v: v.update(gitOverrideFileCount=True), "origin counts differ"),
            (lambda v: v["baseReader"].update(sha256="d" * 64), "retained base"),
            (lambda v: v["override"].update(gitBlob="d" * 40), "exact frozen Git blob"),
            (lambda v: v.update(unreviewedSource="other.py"), "origin identity differs")):
            self.proof = copy.deepcopy(baseline)
            mutate(self.proof)
            self.save()
            with self.subTest(reason=reason), self.assertRaisesRegex(n.Refused, reason):
                self.verify()

    def test_independent_frozen_bytes_and_paths_must_match_proof(self):
        self.reader.write_bytes(b"different frozen reader")
        with self.assertRaisesRegex(n.Refused, "exact frozen Git blob"):
            self.verify()
        self.reader.write_bytes(self.raw)
        outside = self.root / "outside.py"
        outside.write_bytes(self.raw)
        self.proof["override"]["path"] = str(outside)
        self.save()
        with self.assertRaisesRegex(n.Refused, "outside frozen source"):
            self.verify()

    def test_frozen_evidence_must_bind_commit_blob_clean_state_and_hash(self):
        baseline = copy.deepcopy(self.freeze)
        for mutate, reason in (
            (lambda v: v.update(sourceClientCommit="d" * 40), "freeze evidence differs"),
            (lambda v: v["readerGitBlob"].update(gitObject="d" * 40), "freeze evidence differs"),
            (lambda v: v["after"].update(head="d" * 40), "not clean and committed"),
            (lambda v: v["before"].update(trackedStatus=" M reader.py"), "not clean and committed"),
            (lambda v: v.update(archiveContainsProtectedResidue=True), "freeze evidence differs")):
            self.freeze = copy.deepcopy(baseline)
            mutate(self.freeze)
            self.save()
            with self.subTest(reason=reason), self.assertRaisesRegex(n.Refused, reason):
                self.verify()
        self.freeze = baseline
        self.save()
        self.freeze_path.write_text(self.freeze_path.read_text() + "\n")
        with self.assertRaisesRegex(n.Refused, "freeze evidence differs"):
            self.verify()

    def test_fixed_helper_addition_is_allowed_but_other_missing_base_members_refuse(self):
        program, overlay = self.root / "base", self.root / "overlay/manifest.json"
        NativeFixture.write_files(program, {"vendor.dll": pe(b"unchanged vendor")})
        helper = self.prefix + "bootstrap/module_catalogue_cache.py"
        NativeFixture.write_files(overlay.parent / "files", {helper: b"reviewed frozen cache helper"})
        value = {"schemaVersion": 1, "appId": "melange", "version": "1.0.32", "clientCommit": self.commit,
            "sourceCommit": self.commit, "files": [{"path": helper, "bytes": len(b"reviewed frozen cache helper"),
                "sha256": hashlib.sha256(b"reviewed frozen cache helper").hexdigest()}]}
        overlay.write_text(json.dumps(value))
        files, pes, mapping, _inputs, _binding = n.source_overlays(*n.scan(program), "melange", "1.0.32",
            overlay, self.commit, self.commit)
        self.assertEqual(set(mapping), {"vendor.dll", helper})
        self.assertEqual(pes, {"vendor.dll"})
        self.assertEqual(mapping[helper]["sha256"], value["files"][0]["sha256"])
        self.assertFalse((program / helper).exists())
        value["files"][0]["path"] = self.prefix + "bootstrap/module_application_contracts.py"
        overlay.write_text(json.dumps(value))
        with self.assertRaisesRegex(n.Refused, "Invalid source overlay member"):
            n.source_overlays(*n.scan(program), "melange", "1.0.32", overlay, self.commit, self.commit)


class CompiledModuleBridgeFixture(unittest.TestCase):
    """Tiny literal authorities join an actual file map; no inventory is monkeypatched."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.rows, self.mapping = [], {}
        for root, name, raw in (("source", "reader.py", b"reviewed public reader"),
                                ("bootstrap", "desktop_backend.py", b"reviewed native bootstrap")):
            file = self.root / root / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(raw)
            row = {"root": root, "path": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
            self.rows.append(row)
            for app in ("melange", "mentat"):
                prefix = "resources/runtime/" + app + ("/sources/" if root == "source" else "/bootstrap/")
                self.mapping[prefix + name] = {"size": file.stat().st_size, "sha256": n.legacy.digest(file)}
        self.specs = {}
        for app in ("melange", "mentat"):
            self.specs[app] = {"schemaVersion": 1, "appId": app, "contractId": app + ".public-data.v1",
                "programFingerprint": self.fingerprint(self.rows), "programFiles": copy.deepcopy(self.rows),
                "requiredKinds": ["melange.official-payroll-observations.v1" if app == "melange" else "mentat.public-fec-tables.v1"],
                "publicReaders": [app + ".public-data.catalogue"], "privateBoundaries": [app + ".original.console"],
                "startupTimeoutMs": 600000 if app == "melange" else 300000}

    @staticmethod
    def fingerprint(rows):
        ordered = sorted(rows, key=lambda row: (row["root"], row["path"]))
        return hashlib.sha256(json.dumps(ordered, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def encoded(self, js=None, py=None):
        javascript = ("const APPLICATION_SPECS=freeze(" + json.dumps(js or self.specs) + ");\n"
                      "module.exports=Object.freeze({APPLICATION_SPECS});\n").encode()
        python = ("from types import MappingProxyType\nAPPLICATION_SPECS=MappingProxyType(" + repr(py or self.specs) + ")\n").encode()
        return javascript, python

    def check(self, *, app="mentat", js=None, py=None, mode=None):
        javascript, python = self.encoded(js, py)
        return n.compiled_module_tables(app=app, javascript=javascript, python=python,
            program_map=self.mapping, config={"desktopPublicData": {app: mode}} if mode else {})

    def three_tables(self, *, js_change=None, py_change=None):
        public = copy.deepcopy(self.specs)
        workspace = copy.deepcopy(public)
        for app, spec in workspace.items():
            spec['contractId'] = app + '.workspace.v1'
            spec['requiredKinds'] = [app + '.workspace-fixture.v1']
        district = {'terrier': {'schemaVersion':1, 'appId':'terrier', 'programFiles':copy.deepcopy(self.rows),
            'programFingerprint':self.fingerprint(self.rows)}}
        tables = dict(zip(n.COMPILED_TABLE_NAMES, (public, workspace, district)))
        py = copy.deepcopy(tables)
        if js_change:js_change(tables)
        if py_change:py_change(py)
        js = n.COMPILED_TABLE_PREAMBLE + ''.join('const '+name+'=freeze('+json.dumps(tables[name])+');\n' for name in n.COMPILED_TABLE_NAMES)
        js += 'module.exports=Object.freeze({APPLICATION_SPECS,WORKSPACE_APPLICATION_SPECS,DISTRICT_PROGRAM_SPECS});\n'
        python = 'from types import MappingProxyType\n' + ''.join(name+'=MappingProxyType('+repr(py[name])+')\n' for name in n.COMPILED_TABLE_NAMES)
        return js.encode(), python.encode()

    def check_three(self, javascript=None, python=None, *, app='mentat'):
        if javascript is None:javascript, python = self.three_tables()
        mapping = dict(self.mapping)
        for key, value in self.mapping.items():mapping[key.replace('/mentat/', '/terrier/')] = value
        return n.compiled_module_tables(app=app, javascript=javascript, python=python, program_map=mapping,
            config={'desktopAccessMode':'standalone','desktopAuthentication':'windows',
                'desktopWorkspaceData':{app:'workspace-v1'} if app!='terrier' else {}})

    def test_three_literal_tables_bind_public_workspace_and_actual_district_program(self):
        for app in ('melange','mentat','terrier'):
            with self.subTest(app=app):
                result=self.check_three(app=app)
                self.assertTrue(result['matchesActualPackagedProgram'])
                self.assertEqual(result['literalTableNames'],list(n.COMPILED_TABLE_NAMES))
                if app!='terrier':self.assertEqual(result['workspaceContract']['contractId'],app+'.workspace.v1')

    def test_three_literals_reject_extra_code_unknown_duplicate_and_omitted_tables(self):
        js, py=self.three_tables()
        for bad in (b'doNotExecute();'+js, js+b'doNotExecute();',
                js.replace(b'DISTRICT_PROGRAM_SPECS});',b'DISTRICT_PROGRAM_SPECS,UNKNOWN});'),
                js.replace(b'const WORKSPACE_APPLICATION_SPECS=',b'const APPLICATION_SPECS='),
                js.replace(b'const DISTRICT_PROGRAM_SPECS=',b'const UNKNOWN=')):
            with self.subTest(bad=bad[-90:]):
                with self.assertRaises(n.Refused):self.check_three(bad,py)
        with self.assertRaises(n.Refused):self.check_three(js,py+b'runUnknown()\n')

    def test_three_literals_reject_python_boolean_integer_parity_and_relative_import(self):
        js, py=self.three_tables(py_change=lambda t:t['APPLICATION_SPECS']['mentat'].__setitem__('schemaVersion',True))
        with self.assertRaisesRegex(n.Refused,'disagree'):self.check_three(js,py)
        js, py=self.three_tables()
        with self.assertRaises(n.Refused):self.check_three(js,py.replace(b'from types',b'from .types'))
        duplicate_js=js.replace(b'"schemaVersion": 1',b'"schemaVersion": 1,"schemaVersion": 1',1)
        with self.assertRaisesRegex(n.Refused,'duplicate'):self.check_three(duplicate_js,py)
        text=py.decode().replace("'schemaVersion': 1", "'schemaVersion': 1, 'schemaVersion': 1",1)
        with self.assertRaisesRegex(n.Refused,'duplicate'):self.check_three(js,text.encode())

    def test_three_literals_reject_mismatched_or_forged_workspace_and_district_tables(self):
        cases=[lambda t:t['WORKSPACE_APPLICATION_SPECS']['mentat'].__setitem__('programFingerprint','f'*64),
            lambda t:t['DISTRICT_PROGRAM_SPECS']['terrier']['programFiles'][0].__setitem__('sha256','f'*64)]
        for change in cases:
            with self.subTest(change=change):
                with self.assertRaises(n.Refused):self.check_three(*self.three_tables(js_change=change))
                with self.assertRaises(n.Refused):self.check_three(*self.three_tables(js_change=change,py_change=change))

    def test_real_file_map_and_both_literals_agree(self):
        result = self.check()
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["programFileCount"], 2)
        self.assertTrue(result["matchesActualPackagedProgram"])

    def test_stale_pin_fails_even_when_source_inventory_and_packaged_map_agree(self):
        # The old release gate accepted this coherent actual/staged file map;
        # the compiled authority still expects the original reader bytes.
        self.mapping["resources/runtime/mentat/sources/reader.py"] = {
            "size": 7, "sha256": hashlib.sha256(b"changed").hexdigest()}
        with self.assertRaisesRegex(n.Refused, "descriptor differs from actual packaged bytes"):
            self.check()

    def test_cross_language_difference_is_refused(self):
        changed = copy.deepcopy(self.specs)
        changed["mentat"]["programFiles"][0]["sha256"] = "a" * 64
        with self.assertRaisesRegex(n.Refused, "tables disagree"):
            self.check(py=changed)

    def test_fingerprint_is_recomputed_not_borrowed_from_matching_literals(self):
        self.specs["mentat"]["programFingerprint"] = "b" * 64
        with self.assertRaisesRegex(n.Refused, "fingerprint differs"):
            self.check()

    def test_actual_packaged_paged_mode_selects_the_paged_contract(self):
        value = self.check(app="melange", mode="paged-v1")
        self.assertEqual(value["contractId"], "melange.public-data.pages.v1")
        self.assertEqual(value["requiredKinds"], ["melange.official-payroll-pages.v1"])
        self.assertEqual(self.check(app="melange")["requiredKinds"], ["melange.official-payroll-observations.v1"])
        with self.assertRaisesRegex(n.Refused, "Unsupported packaged public data mode"):
            self.check(app="mentat", mode="paged-v1")

    def test_duplicates_redirects_boolean_sizes_and_missing_members_are_refused(self):
        for replacement in ({"root": "source", "path": "../reader.py"}, {"bytes": True},
                            {"path": "module_application_inventory.py"}):
            with self.subTest(replacement=replacement):
                before = copy.deepcopy(self.specs)
                self.specs["mentat"]["programFiles"][0].update(replacement)
                with self.assertRaises(n.Refused):
                    self.check()
                self.specs = before
        self.specs["mentat"]["programFiles"].append(copy.deepcopy(self.rows[0]))
        with self.assertRaisesRegex(n.Refused, "Duplicate"):
            self.check()
        self.specs["mentat"]["programFiles"].pop()
        del self.mapping["resources/runtime/mentat/sources/reader.py"]
        with self.assertRaisesRegex(n.Refused, "descriptor differs"):
            self.check()

    def test_python_expression_and_javascript_dynamic_suffix_are_not_executed(self):
        javascript, python = self.encoded()
        with self.assertRaisesRegex(n.Refused, "not a closed literal"):
            n.compiled_module_tables(app="mentat", javascript=javascript + b"doNotExecute();",
                python=python, program_map=self.mapping, config={})
        python = b"APPLICATION_SPECS = unknown_selector()"
        with self.assertRaisesRegex(n.Refused, "executable selectors"):
            n.compiled_module_tables(app="mentat", javascript=javascript, python=python,
                program_map=self.mapping, config={})

    def test_asar_reader_uses_actual_member_bytes_and_refuses_missing_members(self):
        javascript, _ = self.encoded()
        archive = self.root / "app.asar"
        archive.write_bytes(asar_bytes({"module-application-inventory.cjs": javascript}))
        self.assertEqual(n.asar_member_bytes(archive, "module-application-inventory.cjs"), javascript)
        with self.assertRaisesRegex(n.Refused, "Missing or redirected"):
            n.asar_member_bytes(archive, "missing.cjs")


class ReusedBuiltinExtractionFixture(unittest.TestCase):
    """Only the external 7z listing is simulated; all physical byte checks run."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.client = self.root / 'frozen/ops/desktop/client'
        self.client.mkdir(parents=True)
        self.previous_verifier = self.client.parent / 'packaging/verify_native_release.py'
        self.previous_verifier.parent.mkdir()
        self.previous_verifier.write_bytes(b'production2122 verifier fixture; never executed')
        self.installer = self.root / 'Mentat-1.0.33-win-x64.exe'
        self.installer.write_bytes(b'closed33 builtin installer fixture; never executed')
        self.program = self.root / 'reference-program'
        self.previous_output = self.root / 'previous-inspection'
        self.extracted = self.previous_output / 'app'
        self.payload = {'Mentat.exe': pe(b'reused main PE'), 'resources/app.asar': b'closed client fixture',
                        'resources/runtime/mentat/bootstrap/desktop_backend.py': b'closed bootstrap fixture'}
        NativeFixture.write_files(self.program, self.payload)
        NativeFixture.write_files(self.extracted, self.payload)
        self.reference = n.scan(self.program)[2]
        self.paths = {}
        for key, name in (('signing_receipt','signatures.json'), ('source_overlay','overlay.json'),
                          ('source_origin_proof','origin.json')):
            self.paths[key] = self.root / name
            self.paths[key].write_bytes(b'{"closed":"fixture"}')
        self.paths['staged_sources'] = self.root / 'staged-sources'
        self.paths['staged_sources'].mkdir()
        self.paths['app_executable'] = self.root / 'overlay/Mentat.exe'
        self.paths['app_executable'].parent.mkdir()
        self.paths['app_executable'].write_bytes(self.payload['Mentat.exe'])
        self.paths['app_asar'] = self.root / 'overlay/app.asar'
        self.paths['app_asar'].write_bytes(self.payload['resources/app.asar'])
        self.build_receipts = {
            'signatureReceiptSha256': self.paths['signing_receipt'],
            'sourceOverlaySha256': self.paths['source_overlay'],
            'buildReceiptSha256': Path(str(self.installer) + '.build.json'),
            'payloadBuildReceiptSha256': self.paths['app_executable'].parent / 'payload-build.json',
            'baseProvenanceSha256': self.root / 'mentat-1.0.33-base.provenance.json'}
        for path in self.build_receipts.values():
            if not path.exists():path.write_bytes(b'{"bound":"input"}')
        self.prior_report_path = self.root / 'previous-failed-report.json'
        self.prior_report = {'status':'failed','appId':'mentat','version':'1.0.33',
            'error':'Refused: Compiled JavaScript module table is not a closed literal',
            'inspectionRetained':str(self.previous_output)}
        self.prior_report_path.write_text(json.dumps(self.prior_report))
        self.proof_path = self.root / 'reuse.json'
        self.args = SimpleNamespace(app='mentat',version='1.0.33',installer=str(self.installer),client_commit='c'*40,
            source_commit='b'*40,installer_format='builtin-nsis-v1',reuse_extraction=str(self.proof_path),
            program_directory=str(self.program),client=str(self.client),**{key:str(value) for key,value in self.paths.items()})
        command = ['python.exe','-B',str(self.previous_verifier)]
        values = {'app':'mentat','version':'1.0.33','client-commit':self.args.client_commit,
            'source-commit':self.args.source_commit,'installer':str(self.installer),
            'program-directory':str(self.program),'client':str(self.client),
            'report':str(self.prior_report_path),'output':str(self.previous_output),
            **{key.replace('_','-'):str(value) for key,value in self.paths.items()}}
        for key,value in values.items():command += ['--'+key,value]
        self.invocation_path = self.root / 'previous-invocation.json'
        self.invocation = {'command':command,'verifierSha256':self.ref(self.previous_verifier)['sha256'],
            'installerSha256':self.ref(self.installer)['sha256'],'sourceClientCommit':self.args.client_commit,
            'sourceBackendCommit':self.args.source_commit,
            **{key:self.ref(value)['sha256'] for key,value in self.build_receipts.items()}}
        self.invocation_path.write_text(json.dumps(self.invocation))
        info = self.extracted.stat()
        self.proof = {'schemaVersion':1,'purpose':'release33-builtin-extraction-reuse','appId':'mentat',
            'version':'1.0.33','clientCommit':self.args.client_commit,'sourceCommit':self.args.source_commit,
            'installer':self.ref(self.installer),'previousFailedReport':self.ref(self.prior_report_path),
            'previousInvocation':self.ref(self.invocation_path),'previousVerifier':self.ref(self.previous_verifier),
            'extractedApp':{'path':str(self.extracted),'volume':info.st_dev,'fileId':info.st_ino},
            'expectedReferenceSha256':hashlib.sha256(json.dumps(self.reference,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
        self.persist()
        self.listing = '\n\n'.join('Path = '+name+'\nSize = '+str(row['size'])+'\nFolder = -'
                                  for name,row in self.reference.items()).encode()

    @staticmethod
    def ref(path):
        return {'path':str(path),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

    def persist(self):
        self.proof_path.write_text(json.dumps(self.proof))

    def check(self):
        with mock.patch.object(n.legacy,'run',return_value=self.listing):
            return n.reused_builtin_extraction(args=self.args,installer=self.installer,
                client=self.client,reference=self.reference,seven='7z-listing-fixture')

    def test_exact_prior_failure_rechecks_actual_complete_bytes(self):
        extracted, _files, _pes, mapping, receipt = self.check()
        self.assertEqual(extracted,self.extracted)
        self.assertEqual(mapping,self.reference)
        self.assertEqual(receipt['status'],'passed-reused-extraction-full-byte-revalidation')
        self.assertFalse(receipt['freshUnpackPerformed'])

    def test_different_installer_path_is_rejected_even_with_identical_bytes(self):
        other = self.root / 'other-installer.exe'
        other.write_bytes(self.installer.read_bytes())
        self.proof['installer'] = self.ref(other)
        self.persist()
        with self.assertRaisesRegex(n.Refused,'installer path differs'):self.check()

    def test_other_prior_failure_is_rejected_after_rebinding_evidence_hash(self):
        self.prior_report['error'] = 'Refused: unrelated verification failure'
        self.prior_report_path.write_text(json.dumps(self.prior_report))
        self.proof['previousFailedReport'] = self.ref(self.prior_report_path)
        self.persist()
        with self.assertRaisesRegex(n.Refused,'exact known literal-parser failure'):self.check()

    def test_swapped_extracted_directory_identity_is_rejected(self):
        self.proof['extractedApp']['fileId'] += 1
        self.persist()
        with self.assertRaisesRegex(n.Refused,'physical identity changed'):self.check()

    def test_modified_extracted_payload_is_rejected_by_real_scan(self):
        target = self.extracted / 'resources/app.asar'
        target.write_bytes(b'x' * target.stat().st_size)
        with self.assertRaisesRegex(n.Refused,'Reused complete signed application file census or bytes differ'):self.check()

    def test_extra_extracted_payload_is_rejected_by_real_scan(self):
        (self.extracted / 'unexpected.bin').write_bytes(b'unapproved extra file')
        with self.assertRaisesRegex(n.Refused,'Reused complete signed application file census or bytes differ'):self.check()

    def test_missing_extracted_payload_is_rejected_by_real_scan(self):
        (self.extracted / 'resources/app.asar').unlink()
        with self.assertRaisesRegex(n.Refused,'Reused complete signed application file census or bytes differ'):self.check()

    def test_current_source_or_build_receipt_changes_cannot_reuse_old_inspection(self):
        for key,path in self.build_receipts.items():
            with self.subTest(receipt=key):
                original = path.read_bytes()
                path.write_bytes(original + b' changed')
                try:
                    with self.assertRaisesRegex(n.Refused,'inputs changed'):self.check()
                finally:path.write_bytes(original)


if __name__ == "__main__":
    unittest.main()
