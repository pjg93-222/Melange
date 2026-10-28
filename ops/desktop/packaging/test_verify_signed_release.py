"""Synthetic-fixture tests for the source-bound release verifier (no installer needed)."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_signed_release as v

sha = lambda data: hashlib.sha256(data).hexdigest()


def pe(body_extra=b""):
    """Minimal PE32+ image: DOS header, PE header, optional header with 16 data directories."""
    raw = bytearray(64)
    raw[:2] = b"MZ"
    struct.pack_into("<I", raw, 60, 64)
    raw += b"PE\0\0" + struct.pack("<HHIIIHH", 0x8664, 0, 0, 0, 0, 240, 0x22)
    optional = bytearray(240)
    struct.pack_into("<H", optional, 0, 0x20B)
    raw += optional
    return bytes(raw + b"code" * 8 + body_extra)


def sign(raw, blob, checksum=1):
    checksum_at, security, _, _ = v.pe_layout(raw)
    body = bytearray(v.unsigned_body(raw))
    body += b"\0" * (-len(body) % 8)
    struct.pack_into("<II", body, security, len(body), len(blob))
    struct.pack_into("<I", body, checksum_at, checksum)
    return bytes(body + blob)


def asar_bytes(files):
    header, data, offset = {"files": {}}, b"", 0
    for name, content in files.items():
        header["files"][name] = {"offset": str(offset), "size": len(content)}
        data += content
        offset += len(content)
    raw = json.dumps(header).encode()
    padded = raw + b"\0" * (-len(raw) % 4)
    return struct.pack("<IIII", 4, len(padded) + 8, len(padded) + 4, len(raw)) + padded + data


class GitAllowList(unittest.TestCase):
    def test_changes_and_head_contents_come_from_git(self):
        with tempfile.TemporaryDirectory() as tmp:
            git = lambda *a: subprocess.run(["git", "-C", tmp, "-c", "commit.gpgsign=false", "-c", "user.name=t", "-c", "user.email=t@t", *a], check=True, capture_output=True)
            git("init", "-q")
            for name, text in (("kept.py", "k"), ("edited.py", "old"), ("gone.py", "g")):
                Path(tmp, name).write_text(text)
            git("add", ".")
            git("commit", "-qm", "base")
            base = v.resolve_commit(tmp, "HEAD")
            Path(tmp, "edited.py").write_text("new")
            Path(tmp, "added.py").write_text("a")
            Path(tmp, "gone.py").unlink()
            git("add", "-A")
            git("commit", "-qm", "head")
            head = v.resolve_commit(tmp, "HEAD")
            self.assertEqual(v.changed_paths(tmp, base, head), {"added.py": "A", "edited.py": "M", "gone.py": "D"})
            self.assertEqual(v.head_contents(tmp, head), {"kept.py": sha(b"k"), "edited.py": sha(b"new"), "added.py": sha(b"a")})


class SourceBound(unittest.TestCase):
    head = {"fec/a.py": sha(b"new"), "fec/same.py": sha(b"s"), "fec/added.py": sha(b"x")}
    changes = {"fec/a.py": "M", "fec/added.py": "A", "fec/gone.py": "D"}
    src = "resources/runtime/melange/sources/"

    def run_case(self, old, new, bound=None):
        return v.source_bound(old, new, self.changes, self.head, v.payload_source, bound)

    def test_changed_added_and_deleted_sources_pass_when_equal_to_head(self):
        old = {self.src + "fec/a.py": sha(b"old"), self.src + "fec/same.py": sha(b"s"), self.src + "fec/gone.py": sha(b"g")}
        new = {self.src + "fec/a.py": sha(b"new"), self.src + "fec/same.py": sha(b"s"), self.src + "fec/added.py": sha(b"x")}
        rows = self.run_case(old, new)
        self.assertEqual({r["path"]: r["gitStatus"] for r in rows}, {self.src + "fec/a.py": "M", self.src + "fec/added.py": "A", self.src + "fec/gone.py": "D"})

    def test_difference_outside_git_diff_fails(self):
        with self.assertRaisesRegex(v.Refused, "not in git diff"):
            self.run_case({"resources.pak": sha(b"1")}, {"resources.pak": sha(b"2")})

    def test_stale_packaged_source_fails_even_when_unchanged_from_baseline(self):
        with self.assertRaisesRegex(v.Refused, "does not equal release HEAD"):
            self.run_case({self.src + "fec/a.py": sha(b"old")}, {self.src + "fec/a.py": sha(b"old")})

    def test_changed_file_must_equal_head_bytes(self):
        with self.assertRaisesRegex(v.Refused, "does not equal release HEAD"):
            self.run_case({self.src + "fec/a.py": sha(b"old")}, {self.src + "fec/a.py": sha(b"tampered")})

    def test_removed_file_needs_a_git_deletion(self):
        with self.assertRaisesRegex(v.Refused, "presence disagrees"):
            self.run_case({self.src + "fec/a.py": sha(b"old")}, {})

    def test_bound_build_output_needs_its_exact_hash(self):
        name = "resources/app.asar"
        self.assertEqual(self.run_case({name: sha(b"1")}, {name: sha(b"2")}, {name: sha(b"2")})[0]["basis"], "bound-build-output")
        with self.assertRaisesRegex(v.Refused, "bound hash"):
            self.run_case({name: sha(b"1")}, {name: sha(b"3")}, {name: sha(b"2")})

    def test_build_receipt_must_bind_exactly_the_known_outputs(self):
        full = {"resources/app.asar": "a", v.SOURCE_INVENTORY: "b"}
        self.assertEqual(v.bound_outputs({"boundBuildOutputs": {v.SOURCE_INVENTORY: "b"}}, {"boundBuildOutputs": {"resources/app.asar": "a"}}), full)
        with self.assertRaises(v.Refused):
            v.bound_outputs({"boundBuildOutputs": dict(full, **{"resources.pak": "c"})})
        with self.assertRaises(v.Refused):
            v.bound_outputs({"boundBuildOutputs": {"resources/app.asar": "a"}})


class SignedPe(unittest.TestCase):
    def compare(self, old, new):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp, "old.dll"), Path(tmp, "new.dll")
            a.write_bytes(old)
            b.write_bytes(new)
            return v.compare_signed_pe(a, b)

    def test_resigned_owned_binary_passes_and_body_change_fails(self):
        image = pe(b"\x01\x02\x03")
        self.assertEqual(self.compare(sign(image, b"S" * 16), sign(image, b"T" * 24, checksum=7)), "authenticode-only")
        self.assertEqual(self.compare(image, sign(image, b"T" * 24)), "authenticode-only")
        with self.assertRaisesRegex(v.Refused, "outside approved"):
            self.compare(sign(image, b"S" * 16), sign(pe(b"\x01\x02\x04"), b"T" * 24))

    def test_signature_must_be_an_appended_table(self):
        image = pe()
        signed = bytearray(sign(image, b"T" * 16))
        signed += b"trailing"
        with self.assertRaises(v.Refused):
            self.compare(image, bytes(signed))


class AsarAndPackage(unittest.TestCase):
    def test_asar_members_are_hashed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "app.asar")
            path.write_bytes(asar_bytes({"main.cjs": b"code", "package.json": b'{"version":"1.0.17"}'}))
            _, members = v.asar(path)
            self.assertEqual(members["main.cjs"]["sha256"], sha(b"code"))
            self.assertEqual(members["package.json"]["json"], {"version": "1.0.17"})
            self.assertEqual(v.asar_source("main.cjs"), "ops/desktop/client/main.cjs")
            self.assertIsNone(v.asar_source("node_modules/semver/index.js"))

    def test_package_may_change_version_and_add_named_config_keys_only(self):
        keys = v.asar_config_keys("x={extraMetadata:{desktopAppConfig:{appId:selected.id,desktopUpdateSource,desktopScrapeBroker}}}")
        self.assertEqual(keys, {"appId", "desktopUpdateSource", "desktopScrapeBroker"})
        old = {"name": "melange-desktop", "version": "1.0.16", "desktopAppConfig": {"appId": "melange"}}
        new = {"name": "melange-desktop", "version": "1.0.17", "desktopAppConfig": {"appId": "melange", "desktopScrapeBroker": False}}
        self.assertEqual(v.check_package(old, new, keys), {"desktopScrapeBroker": False})
        with self.assertRaisesRegex(v.Refused, "not named"):
            v.check_package(old, dict(new, desktopAppConfig={"appId": "melange", "other": 1}), keys)
        with self.assertRaisesRegex(v.Refused, "beyond version"):
            v.check_package(old, dict(new, main="evil.cjs"), keys)
        with self.assertRaisesRegex(v.Refused, "values changed"):
            v.check_package(old, dict(new, desktopAppConfig={"appId": "mentat"}), keys)


class NoUninstallerIntegration(unittest.TestCase):
    """Exercise the full verifier with tiny archives and synthetic OS verdicts.

    Real PE classification, ASAR parsing, metadata/source checks and signature
    requirements run; no installer or native payload is executed.
    """
    def inspect_fixture(self, without=True, candidate_uninstaller=False, bad_signature=None):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            build = root / "build"
            candidate = build / "dist" / "melange" / "Melange-1.0.17-win-x64.exe"
            candidate.parent.mkdir(parents=True)
            candidate.write_bytes(b"candidate-container")
            baseline, seven, output = root / "baseline.exe", root / "7za.exe", root / "inspection"
            baseline.write_bytes(b"baseline-container")
            seven.write_bytes(b"inspection-tool-fixture")
            output.mkdir()
            package = lambda version: {"name": "melange-desktop", "version": version,
                                       "desktopAppConfig": {"appId": "melange"}}
            old_package, new_package = package(v.OLD), package(v.NEW)
            if without:
                new_package["desktopAppConfig"]["desktopUninstaller"] = False
            payloads = {}
            for label, pkg in (("baseline", old_package), ("candidate", new_package)):
                payloads[label] = {"Melange.exe": pe(label.encode()), "resources/elevate.exe": pe(b"elevate"),
                                   "resources/app.asar": asar_bytes({"package.json": json.dumps(pkg).encode(), "main.cjs": b"unchanged JS"}),
                                   v.SOURCE_INVENTORY: b"[]"}
            head, base = "a" * 40, "b" * 40
            inputs = {"app": v.APP, "version": v.NEW, "baselineInstallerSHA256": v.digest(baseline),
                      "packagingSource": head, "basePin": base, "root": str(build)}
            result = {"exitCode": 0, "sourcePin": head, "sourceClean": True, "inputsUnchanged": True,
                      "boundBuildOutputs": {key: sha(payloads["candidate"][key]) for key in v.BUILD_OUTPUTS}}
            v.write_json(build / "build-inputs.json", inputs)
            v.write_json(build / "build-result.json", result)
            row = {"path": str(candidate), "sha256": v.digest(candidate), "status": "Valid", "thumbprint": v.PIN, "timestamped": True}
            v.write_json(str(candidate) + ".signatures.json", {"schemaVersion": 1, "appId": "melange", "certificateThumbprint": v.PIN,
                "installer": str(candidate), "desktopUninstaller": False, "uninstallerEvidence": "intentionally-absent",
                "files": [row], "currentFiles": [row]})

            def extract(_seven, archive, destination, _budget):
                destination.mkdir()
                label = destination.parent.name
                if destination.name == "app":
                    files = payloads[label]
                else:
                    files = {"$PLUGINSDIR/app-64.7z": b"archive", **{"$PLUGINSDIR/" + name: pe(name.encode()) for name in v.PLUGINS}}
                    if label == "baseline" or candidate_uninstaller:
                        files["$PLUGINSDIR/Uninstall Melange.exe"] = pe(b"uninstaller")
                for name, content in files.items():
                    target = destination / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(content)
                return sum(map(len, files.values()))

            native_ids = []
            def signatures(items, _output):
                native_ids.extend(items)
                return {key: {"id": key, "sha256": v.digest(file), "status": "NotSigned" if key == bad_signature else "Valid",
                              "thumbprint": v.PIN, "signatureType": "Authenticode", "timestampSubject": "DigiCert fixture",
                              "fileVersion": v.NEW, "productVersion": v.NEW} for key, file in items.items()}

            helper = Path(v.__file__).with_name("no_uninstaller_contract.py")
            head_files = {"ops/desktop/client/main.cjs": sha(b"unchanged JS"),
                          "ops/desktop/packaging/no_uninstaller_contract.py": v.digest(helper)}
            args = SimpleNamespace(installer=str(candidate), baseline=str(baseline), output=str(output), seven_zip=str(seven),
                                   repo=str(root), head="HEAD", build_inputs=str(build / "build-inputs.json"),
                                   without_uninstaller=without, signing_receipt=None)
            with mock.patch.multiple(v, BASE_SHA=v.digest(baseline), EXPECTED_PES=2), \
                    mock.patch.object(v, "extract", side_effect=extract), \
                    mock.patch.object(v, "resolve_commit", side_effect=lambda _repo, ref: base if ref == v.BASE_PIN else head), \
                    mock.patch.object(v, "changed_paths", return_value={}), \
                    mock.patch.object(v, "head_contents", return_value=head_files), \
                    mock.patch.object(v, "git", return_value=b"extraMetadata:{desktopAppConfig:{appId:selected.id,desktopUninstaller:false}}"), \
                    mock.patch.object(v, "signatures", side_effect=signatures), \
                    mock.patch.object(v, "compare_signed_pe", return_value="authenticode-plus-version-and-asar-integrity"):
                report = {}
                v.verify(args, report)
            return report, native_ids

    def test_opt_in_keeps_complete_other_native_census(self):
        report, ids = self.inspect_fixture()
        self.assertEqual(report["status"], "passed")
        self.assertNotIn("candidate/uninstaller", ids)
        self.assertIn("baseline/uninstaller", ids)
        self.assertEqual(len(ids), 2 + 1 + 2 * 2 + 2 * len(v.PLUGINS))
        self.assertTrue(report["checks"]["uninstallerIntentionallyAbsent"])
        self.assertTrue(report["checks"]["mainElevateOuterApprovedAndTimestamped"])
        self.assertNotIn("mainElevateUninstallerOuterApprovedAndTimestamped", report["checks"])
        self.assertIsNone(report["generatedUninstaller"])

    def test_legacy_default_still_requires_and_verifies_uninstaller(self):
        with self.assertRaisesRegex(v.Refused, "uninstaller missing"):
            self.inspect_fixture(without=False)
        report, ids = self.inspect_fixture(without=False, candidate_uninstaller=True)
        self.assertIn("candidate/uninstaller", ids)
        self.assertTrue(report["checks"]["mainElevateUninstallerOuterApprovedAndTimestamped"])
        self.assertEqual(report["generatedUninstaller"]["thumbprint"], v.PIN)

    def test_opt_in_refuses_existing_uninstaller_and_any_bad_remaining_signature(self):
        with self.assertRaisesRegex(ValueError, "Unexpected uninstaller"):
            self.inspect_fixture(candidate_uninstaller=True)
        for name in ("candidate/installer", "candidate/app/Melange.exe", "candidate/app/resources/elevate.exe", "candidate/plugin/System.dll"):
            with self.subTest(name=name), self.assertRaisesRegex(v.Refused, "Expected valid"):
                self.inspect_fixture(bad_signature=name)


if __name__ == "__main__":
    unittest.main()
