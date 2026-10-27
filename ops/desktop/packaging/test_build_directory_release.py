import importlib.util
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("build_directory_release", Path(__file__).with_name("build_directory_release.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class FrozenDirectoryBuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="directory-build-")
        self.root = Path(self.temp.name).resolve()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "Build fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("remote", "add", "origin", "https://github.com/pjg93-222/Melange.git")
        files = {"requirements.txt": "example==1.0\n", "ops/desktop/client/package.json": json.dumps({"version": "1.0.20"}),
                 "ops/desktop/packaging/runtime-manifest.json": json.dumps({"apps": {"melange": {"requirements": "requirements.txt", "nativeRuntimes": []}}})}
        for name, value in files.items():
            target = self.repo / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(value, encoding="utf-8")
        self.commit = self.commit_files()
        self.source = {"path": str(self.repo), "commit": self.commit}

    def tearDown(self):
        self.temp.cleanup()

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repo), "-c", "core.hooksPath=" + str(self.root / "no-hooks"), "-c", "commit.gpgsign=false", *args], stderr=subprocess.DEVNULL).decode().strip()

    def commit_files(self):
        self.git("add", ".")
        self.git("commit", "-qm", "fixture")
        return self.git("rev-parse", "HEAD")

    def config(self):
        return {"schemaVersion": 1, "version": "1.0.20", "tooling": self.source, "apps": {"melange": {"source": self.source}}}

    def runtime(self):
        root = self.root / "runtime"
        (root / "python").mkdir(parents=True)
        (root / "python/python.exe").write_bytes(b"fixture")
        (root / "dependency-inventory.json").write_text("[]")
        (root / "runtime-status.json").write_text(json.dumps({"appId": "melange", "missingNativeRuntimes": []}))
        (root / "source-provenance.json").write_text(json.dumps({"repository": "pjg93-222/Melange", "commit": self.commit}))
        return root

    def test_frozen_export_ignores_dirty_checkout_and_records_it_truthfully(self):
        (self.repo / "requirements.txt").write_text("uncommitted changes\n")
        prepared = module.plan(self.config())
        self.assertTrue(prepared["tooling"]["checkoutDirty"])
        self.assertFalse(prepared["tooling"]["exportDirty"])
        output = self.root / "export"
        rows = module.export_commit(prepared["tooling"], output)
        self.assertEqual((output / "requirements.txt").read_bytes(), module.git(self.repo, "show", self.commit + ":requirements.txt"))
        self.assertTrue(any(row["path"] == "requirements.txt" for row in rows))
        self.assertFalse(prepared["publicationAllowed"])

    def test_dependency_reuse_rejects_changed_lock_and_wrong_app(self):
        runtime = self.runtime()
        source = module.source_identity(self.source, "melange")
        module.dependency_reuse("melange", source, runtime, {"requirements": "requirements.txt", "nativeRuntimes": []})
        (self.repo / "requirements.lock.txt").write_text("example==2.0\n")
        changed = module.source_identity({"path": str(self.repo), "commit": self.commit_files()}, "melange")
        with self.assertRaisesRegex(module.Refused, "changed"):
            module.dependency_reuse("melange", changed, runtime, {"requirements": "requirements.txt", "nativeRuntimes": []})
        with self.assertRaisesRegex(module.Refused, "Unexpected"):
            module.source_identity(self.source, "mentat")

    def test_candidate_version_must_equal_frozen_client(self):
        config = self.config()
        config["version"] = "1.0.21"
        with self.assertRaisesRegex(module.Refused, "version differs"):
            module.plan(config)

    def test_cleanup_rejects_escape_and_replaced_build_identity(self):
        scratch = self.root / "scratch"
        scratch.mkdir()
        target = scratch / "owned"
        target.mkdir()
        (scratch / "owner.json").write_text(json.dumps({"id": "fixture-owner"}))
        build = module.Build({}, scratch, self.root / "outputs", Path("python"))
        build.owner, build.root_identity = "fixture-owner", scratch.stat().st_ino
        with self.assertRaises(module.Refused):
            build.remove(Path("..") / "repo")
        build.root_identity = -1
        with self.assertRaisesRegex(module.Refused, "identity changed"):
            build.remove("owned")
        self.assertTrue(target.exists())

    def test_disk_floor_is_enforced_before_expansion(self):
        build = module.Build({}, self.root, self.root / "outputs", Path("python"))
        usage = type("Usage", (), {"free": 33 * module.GIB})()
        with patch.object(module.shutil, "disk_usage", return_value=usage):
            build.space(1 * module.GIB)
            with self.assertRaises(module.Refused):
                build.space(2 * module.GIB)

    def test_peak_reserve_covers_measured_runtime_copies_and_fresh_venv(self):
        reused = {"runtime": {"inputBytes": 2 * module.GIB}, "source": {"exportBytes": 10_000}}
        fresh = {"runtime": None, "runtimeBaselineBytes": module.GIB, "source": {"exportBytes": 10_000}}
        self.assertGreaterEqual(module.peak_reserve(reused), 3 * reused["runtime"]["inputBytes"] + 2 * module.GIB)
        self.assertGreaterEqual(module.peak_reserve(fresh), 4 * module.runtime_budget(fresh) + 2 * module.GIB)

    def test_packager_descriptor_is_independent_of_command_log_position(self):
        package = self.root / "melange-1.0.20-win32-x64.zip"
        value = self.descriptor(package)
        payload = json.dumps(value, indent=2)
        for text in ["python directory_zip.py\n" + payload + "\n", payload + "\npython directory_zip.py\n"]:
            self.assertEqual(module.package_log_descriptor(text, "melange", "1.0.20", package, "python directory_zip.py"), value)
        with self.assertRaises(module.Refused):
            module.package_log_descriptor("no output\n", "melange", "1.0.20", package, "python directory_zip.py")
        for text in [payload + "\n{}\n", "unreviewed-command\n" + payload, "python directory_zip.py\n" + payload + "\n{}"]:
            with self.assertRaises(module.Refused):
                module.package_log_descriptor(text, "melange", "1.0.20", package, "python directory_zip.py")
        for change in [{"appId": "terrier"}, {"version": "1.0.21"}, {"sha256": "wrong"}, {"size": True}, {"path": str(self.root / "other.zip")}, {"extra": 1}]:
            with self.assertRaises(module.Refused):
                module.package_log_descriptor("python directory_zip.py\n" + json.dumps({**value, **change}, indent=2), "melange", "1.0.20", package, "python directory_zip.py")

    def descriptor(self, package):
        contents = b"zip fixture"
        package.write_bytes(contents)
        value = {"path": str(package), "appId": "melange", "version": "1.0.20", "platform": "win32", "arch": "x64", "format": "windows-directory-zip-v1", "entrypoint": "Melange.exe", "name": package.name, "size": len(contents), "sha256": hashlib.sha256(contents).hexdigest(), "sha512": base64.b64encode(hashlib.sha512(contents).digest()).decode(), "fileCount": 3, "expandedBytes": 30, "excludedInstallerFiles": [], "publisherProofPayloadPath": str(package.parent / "publisher-payload.json")}
        names = ("appId", "version", "platform", "arch", "format", "entrypoint", "name", "size", "sha256", "sha512")
        (package.parent / "publisher-payload.json").write_bytes(b"MELANGE-DESKTOP-DIRECTORY-ZIP-V1\n" + json.dumps({key: value[key] for key in names}, separators=(",", ":")).encode())
        return value

    def test_resume_bytes_and_canonical_signing_payload_are_bound_before_signing(self):
        package = self.root / "melange-1.0.20-win32-x64.zip"
        value = self.descriptor(package)
        module.validate_packaged_bytes(value, package)
        package.write_bytes(b"bad fixture")
        with self.assertRaisesRegex(module.Refused, "hash changed"):
            module.validate_packaged_bytes(value, package)
        value = self.descriptor(package)
        (package.parent / "publisher-payload.json").write_bytes(b"changed")
        with self.assertRaisesRegex(module.Refused, "payload changed"):
            module.validate_packaged_bytes(value, package)

    def test_frozen_resume_identity_requires_every_source_and_tooling_commit(self):
        prepared = module.plan(self.config())
        same = json.loads(json.dumps(prepared))
        same["tooling"]["checkoutDirty"] = not same["tooling"]["checkoutDirty"]
        self.assertEqual(module.frozen_plan_identity(prepared), module.frozen_plan_identity(same))
        for target in [same["tooling"], same["apps"]["melange"]["source"]]:
            before = target["commit"]
            target["commit"] = "a" * 40
            self.assertNotEqual(module.frozen_plan_identity(prepared), module.frozen_plan_identity(same))
            target["commit"] = before

    def test_terrier_constraint_matches_reviewed_pypi_certifi_wheel(self):
        text = Path(__file__).with_name("terrier-runtime.constraints.txt").read_text()
        self.assertIn("certifi==2026.10.19", text)
        self.assertIn("42d35340cc5b9ba78e818ddbff0c5b1c2b779de448a340fd1b989f5fa8670e1b", text)
        self.assertIn("https://pypi.org/pypi/certifi/2026.10.19/json", text)


if __name__ == "__main__":
    unittest.main()
