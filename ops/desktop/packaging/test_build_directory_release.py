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
        return subprocess.check_output(["git", "-C", str(self.repo), "-c", "maintenance.auto=false", "-c", "gc.auto=0", "-c", "core.hooksPath=" + str(self.root / "no-hooks"), "-c", "commit.gpgsign=false", *args], stderr=subprocess.DEVNULL).decode().strip()

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
        self.assertGreaterEqual(module.peak_reserve(reused), 2 * reused["runtime"]["inputBytes"] + 2 * module.GIB)
        self.assertGreaterEqual(module.peak_reserve(fresh), 3 * module.runtime_budget(fresh) + 2 * module.GIB)

    def test_runtime_retirement_requires_completed_signed_tree_and_saved_receipt(self):
        runtime = self.runtime()
        config = self.config()
        config["apps"]["melange"]["runtime"] = str(runtime)
        prepared = module.plan(config)
        for valid in [True, False]:
            build = module.Build(prepared, self.root / ("good" if valid else "bad"), self.root / ("out-good" if valid else "out-bad"), self.root / "python.exe")
            def call(label, *_args, **_kwargs):
                if label == "melange-runtime":
                    (build.root / "runtime/melange/bootstrap").mkdir()
                if label == "melange-electron":
                    unpacked = build.root / "signing/melange/dist/melange/win-unpacked"
                    unpacked.mkdir(parents=True)
                    (unpacked / "Melange.exe").write_bytes(b"completed signed app fixture")
                    if valid:
                        unpacked.with_name(unpacked.name + ".signatures.json").write_text('{"fixture":"completed signing receipt"}')
            def packaged(_app, unpacked, _package):
                self.assertFalse((build.root / "runtime/melange").exists())
                self.assertEqual((unpacked / "Melange.exe").read_bytes(), b"completed signed app fixture")
                self.assertEqual((build.artifacts / "melange/build-signatures.json").read_text(), '{"fixture":"completed signing receipt"}')
                return {}, {}
            with patch.object(build, "space"), patch.object(build, "call", side_effect=call), patch.object(build, "package_signed_tree", side_effect=packaged) as packaging, patch.object(build, "finish_package", return_value={"complete": True}):
                if valid:
                    build.run()
                    packaging.assert_called_once()
                else:
                    with self.assertRaisesRegex(module.Refused, "signing receipt missing"):
                        build.run()
                    self.assertTrue((build.root / "runtime/melange").exists())
                    packaging.assert_not_called()

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

    def test_resume_records_actual_legacy_or_controller_packager(self):
        frozen = self.root / "frozen-packaging"
        frozen.mkdir()
        (frozen / "directory_zip.py").write_bytes(b"original frozen implementation")
        directory, identity = module.packager_for_resume(self.root, frozen, self.commit)
        self.assertEqual(directory, frozen)
        self.assertEqual(identity, {"source": "frozen-tooling", "sha256": module.digest(frozen / "directory_zip.py"), "commit": self.commit, "dirty": False})
        current = {"source": "controller", "sha256": module.digest(module.HERE / "directory_zip.py"), "commit": self.commit, "dirty": False}
        record = self.root / "packager-implementation.json"
        record.write_text(json.dumps(current))
        self.assertEqual(module.packager_for_resume(self.root, frozen, self.commit), (module.HERE, current))
        record.write_text(json.dumps({**current, "sha256": "a" * 64}))
        with self.assertRaisesRegex(module.Refused, "implementation changed"):
            module.packager_for_resume(self.root, frozen, self.commit)
        record.write_text(json.dumps({**current, "dirty": True}))
        with self.assertRaisesRegex(module.Refused, "Invalid recorded"):
            module.packager_for_resume(self.root, frozen, self.commit)

    def test_native_resume_binds_every_helper_and_executable_identity(self):
        names = ["directory_zip_native.py", "directory_inventory_parallel.py", "directory_zip.py"]
        tool = self.root / "7za.exe"
        tool.write_bytes(b"native-tool-fixture")
        identity = {"source": "native-controller", "sha256": module.digest(module.HERE / names[0]), "modules": {name: module.digest(module.HERE / name) for name in names},
                    "nativeTool": {"path": str(tool), "sha256": module.digest(tool)}, "commit": self.commit, "dirty": False}
        record = self.root / "packager-implementation.json"
        record.write_text(json.dumps(identity))
        self.assertEqual(module.packager_for_resume(self.root, self.root, self.commit), (module.HERE, identity))
        changed = json.loads(json.dumps(identity))
        changed["modules"]["directory_inventory_parallel.py"] = "a" * 64
        record.write_text(json.dumps(changed))
        with self.assertRaisesRegex(module.Refused, "implementation changed"):
            module.packager_for_resume(self.root, self.root, self.commit)
        record.write_text(json.dumps(identity))
        tool.write_bytes(b"changed tool")
        with self.assertRaisesRegex(module.Refused, "tool changed"):
            module.packager_for_resume(self.root, self.root, self.commit)

    def verification_fixture(self, name="retry", shared=False):
        config = self.config()
        if not shared:
            (self.repo / "controller-fixture.txt").write_text(name)
            config["tooling"] = {"path": str(self.repo), "commit": self.commit_files()}
        prepared = module.plan(config)
        scratch, artifacts = self.root / name, self.root / (name + "-outputs")
        scratch.mkdir()
        (scratch / "src").mkdir()
        (scratch / "logs").mkdir()
        (scratch / "verify/melange").mkdir(parents=True)
        output = artifacts / "melange"
        output.mkdir(parents=True)
        module.json_write(scratch / "plan.json", prepared)
        module.json_write(scratch / "owner.json", {"id": "f" * 32, "purpose": "local-directory-candidate"})
        for label in ["tooling", "melange"]:
            source = prepared["tooling"] if label == "tooling" else prepared["apps"]["melange"]["source"]
            if shared and label == "melange":
                rows = json.loads((scratch / "tooling-source-inventory.json").read_text())
            else:
                rows = module.export_commit(source, scratch / "src" / label)
            module.json_write(scratch / (label + "-source-inventory.json"), rows)
        provenance = {"sourceCommit": self.commit, "toolingCommit": prepared["tooling"]["commit"], "dirty": False,
                      "sourceExportInventorySha256": module.digest(scratch / "melange-source-inventory.json"),
                      "toolingExportInventorySha256": module.digest(scratch / "tooling-source-inventory.json")}
        module.json_write(output / "source-provenance.json", provenance)
        for value in ["build-signatures.json", "runtime-source-inventory.json", "publisher-proof.json"]:
            module.json_write(output / value, {})
        identity = {"source": "controller", "sha256": module.digest(module.HERE / "directory_zip.py"), "commit": self.commit, "dirty": False}
        module.json_write(output / "packager-implementation.json", identity)
        build = module.Build(prepared, scratch, artifacts, self.root / "python.exe")
        package = output / "melange-1.0.20-win32-x64.zip"
        descriptor = self.descriptor(package)
        module.json_write(output / "package.json", descriptor)
        unpacked = scratch / "signing/melange/dist/melange/win-unpacked"
        command = subprocess.list2cmdline([str(x) for x in build.zip_command("melange", module.HERE, unpacked, package)])
        (scratch / "logs/melange-zip.log").write_text(command + "\n" + json.dumps(descriptor, indent=2))
        (scratch / "logs/melange-verify.log").write_bytes(b"preserved original verification failure\n")
        return build, descriptor, provenance, identity

    def test_verification_resume_supports_a_shared_tooling_source_export(self):
        build, _, _, _ = self.verification_fixture(shared=True)
        self.assertFalse((build.root / "src/melange").exists())
        with patch.object(build, "call"), patch.object(build, "verify_package", return_value={"verified": True}):
            self.assertEqual(build.resume_verification("melange"), {"verified": True})

    def test_verification_resume_preserves_failed_log_and_only_checks_existing_proof(self):
        build, descriptor, _provenance, _identity = self.verification_fixture()
        original = (build.root / "logs/melange-verify.log").read_bytes()
        with patch.object(build, "call") as call, patch.object(build, "verify_package", return_value={"verified": True}) as verify:
            self.assertEqual(build.resume_verification("melange"), {"verified": True})
        self.assertEqual(call.call_count, 1)
        self.assertIn("-proof", call.call_args.args[0])
        self.assertEqual(call.call_args.args[1][0:2], ["node", "-e"])
        self.assertEqual(verify.call_args.args[1], descriptor)
        continuation = verify.call_args.args[4]
        self.assertTrue(continuation["retainedExtraction"])
        self.assertEqual(continuation["previousVerifierLogSha256"], hashlib.sha256(original).hexdigest())
        self.assertNotEqual(continuation["verificationLogLabel"], "melange-verify")
        self.assertEqual((build.root / "logs/melange-verify.log").read_bytes(), original)

    def test_verification_resume_rejects_changed_inputs_and_passed_evidence_before_calling_tools(self):
        for case in ["source", "tooling", "zip", "plan", "native-verification.json", "engineering-receipt.json"]:
            with self.subTest(case=case):
                build, descriptor, _, _ = self.verification_fixture("retry-" + case.replace(".", "-"))
                output = build.artifacts / "melange"
                if case in ["source", "tooling"]:
                    (build.root / "src" / ("melange" if case == "source" else "tooling") / "requirements.txt").write_bytes(b"changed source")
                elif case == "zip":
                    Path(descriptor["path"]).write_bytes(b"changed zip")
                elif case == "plan":
                    saved = json.loads((build.root / "plan.json").read_text())
                    saved["tooling"]["commit"] = "a" * 40
                    (build.root / "plan.json").write_text(json.dumps(saved))
                else:
                    module.json_write(output / case, {"passed": True})
                with patch.object(build, "call") as call, patch.object(build, "verify_package") as verify:
                    with self.assertRaises(module.Refused):
                        build.resume_verification("melange")
                    call.assert_not_called()
                    verify.assert_not_called()

    def test_verification_resume_proof_failure_never_reaches_directory_or_native_checks(self):
        build, _, _, _ = self.verification_fixture()
        with patch.object(build, "call", side_effect=module.Refused("publisher proof invalid")), patch.object(build, "verify_package") as verify:
            with self.assertRaisesRegex(module.Refused, "publisher proof"):
                build.resume_verification("melange")
            verify.assert_not_called()

    def test_verification_continuation_requests_full_recheck_and_writes_fresh_provenance(self):
        build, descriptor, provenance, identity = self.verification_fixture()
        build.owner, build.root_identity = "f" * 32, build.root.stat().st_ino
        continuation = {"retainedExtraction": True, "verificationLogLabel": "melange-unique-retry"}
        def checked(label, command, **_kwargs):
            self.assertEqual(label, "melange-unique-retry")
            self.assertEqual(command[-1], "--reuse-extraction")
            self.assertTrue((build.root / "verify/melange").is_dir())
            module.json_write(build.artifacts / "melange/native-verification.json", {"verifierImplementationSha256": module.digest(module.HERE / "verify_directory_release.cjs")})
        with patch.object(build, "space") as space, patch.object(build, "call", side_effect=checked):
            receipt = build.verify_package("melange", descriptor, provenance, identity, continuation)
        space.assert_called_once_with(0)
        self.assertEqual(receipt["verificationContinuation"], continuation)
        self.assertFalse(receipt["publicationAllowed"])
        self.assertFalse((build.root / "verify/melange").exists())
        self.assertTrue((build.artifacts / "melange/engineering-receipt.json").is_file())
        with self.assertRaisesRegex(module.Refused, "already exists"):
            build.verify_package("melange", descriptor, provenance, identity, continuation)

    def test_terrier_constraint_matches_reviewed_pypi_certifi_wheel(self):
        text = Path(__file__).with_name("terrier-runtime.constraints.txt").read_text()
        self.assertIn("certifi==2026.10.19", text)
        self.assertIn("42d35340cc5b9ba78e818ddbff0c5b1c2b779de448a340fd1b989f5fa8670e1b", text)
        self.assertIn("https://pypi.org/pypi/certifi/2026.10.19/json", text)

    def test_terrier_desktop_extras_cover_required_runtime_imports_at_existing_versions(self):
        text = Path(__file__).with_name("terrier-runtime.constraints.txt").read_text()
        manifest = json.loads(Path(__file__).with_name("runtime-manifest.json").read_text())
        for name, version, sha in [("cryptography", "49.0.0", "e5dfc1e64de5677cec922ffa8da89c546d0415bf6efdf081842e5d44c84e1f0e"),
                                   ("joblib", "1.5.3", "5fc3c5039fc5ca8c0276333a188bbd59d6b7ab37fe6632daa76bc7f9ec18e713"),
                                   ("pyarrow", "24.0.0", "295f0a7f2e242dabd513737cf076007dc5b2d59237e3eca37b05c0c6446f3826"),
                                   ("scipy", "1.18.0", "71ccc8faa2dd16ac310233203474a8b5cb67f10dedd54a3116d34943f4b19132")]:
            self.assertIn(name, manifest["apps"]["terrier"]["hiddenImports"])
            self.assertIn(name + "==" + version + " \\\n    --hash=sha256:" + sha, text)


if __name__ == "__main__":
    unittest.main()
