import importlib.util
import base64
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location("directory_zip", Path(__file__).with_name("directory_zip.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class DirectoryZipTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="directory-zip-packager-")
        self.root = Path(self.temp.name).resolve()
        self.source = self.root / "win-unpacked"
        for name, data in {"Melange.exe": b"MZ signed fixture", "resources/app.asar": b"bound ASAR fixture", "resources/runtime/melange/python/python.exe": b"MZ bundled runtime"}.items():
            file = self.source / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(data)

    def tearDown(self):
        self.temp.cleanup()

    def test_flat_package_preserves_bytes_and_inventory(self):
        output = self.root / "melange-1.0.20-win32-x64.zip"
        receipt = module.build(self.source, output, "melange", "1.0.20")
        self.assertEqual(receipt["format"], "windows-directory-zip-v1")
        self.assertEqual(receipt["sha512"], base64.b64encode(hashlib.sha512(output.read_bytes()).digest()).decode("ascii"))
        payload = module.publisher_payload(receipt)
        self.assertTrue(payload.startswith(b"MELANGE-DESKTOP-DIRECTORY-ZIP-V1\n"))
        value = json.loads(payload.split(b"\n", 1)[1])
        self.assertEqual(list(value), ["appId", "version", "platform", "arch", "format", "entrypoint", "name", "size", "sha256", "sha512"])
        self.assertEqual(value["name"], "melange-1.0.20-win32-x64.zip")
        with zipfile.ZipFile(output) as archive:
            self.assertEqual(archive.namelist()[0], "directory-package.json")
            inventory = json.loads(archive.read("directory-package.json"))
            for item in inventory["files"]:
                self.assertEqual(archive.read(item["path"]), (self.source / item["path"]).read_bytes())
        with self.assertRaises(module.Refused):
            module.build(self.source, output, "melange", "1.0.20")

    def test_excludes_installer_helpers_only(self):
        (self.source / "Uninstall Melange.exe").write_bytes(b"MZ uninstaller")
        (self.source / "resources/elevate.exe").write_bytes(b"MZ elevation helper")
        receipt = module.build(self.source, self.root / "app.zip", "melange", "1.0.20")
        self.assertEqual(sorted(receipt["excludedInstallerFiles"]), ["Uninstall Melange.exe", "resources/elevate.exe"])
        self.assertEqual(receipt["fileCount"], 3)

    def test_refuses_user_state_private_keys_and_private_pem(self):
        for name, contents in [("settings.json", b"{}"), ("resources/runtime/melange/sources/fec/cache.sqlite", b"db"), ("release.pfx", b"key"), ("resources/test.pem", b"-----BEGIN RSA PRIVATE KEY-----\n" + b"A" * 64 + b"\n-----END RSA PRIVATE KEY-----\n")]:
            with self.subTest(name=name):
                file = self.source / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(contents)
                with self.assertRaises(module.Refused):
                    module.build(self.source, self.root / "bad.zip", "melange", "1.0.20")
                self.assertFalse((self.root / "bad.zip").exists())
                file.unlink()

    def test_preserves_required_third_party_runtime_databases(self):
        names = ["resources/runtime/melange/native/R/doc/KEYWORDS.db", "resources/runtime/melange/native/R/library/RSQLite/db/datasets.sqlite", "resources/runtime/melange/native/R/share/licenses/license.db", "resources/runtime/melange/python/Lib/site-packages/pyogrio/proj_data/proj.db", "resources/runtime/melange/python/Lib/site-packages/pyproj/proj_dir/share/proj/proj.db"]
        for name in names:
            file = self.source / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(b"required third-party data")
        output = self.root / "vendor-data.zip"
        module.build(self.source, output, "melange", "1.0.20")
        with zipfile.ZipFile(output) as archive:
            for name in names:
                self.assertEqual(archive.read(name), b"required third-party data")

    def test_rejects_source_state_directory_and_database_sidecars(self):
        for name in ["resources/runtime/mentat/sources/fec/state/values.json", "resources/runtime/melange/sources/cache.DB", "resources/runtime/terrier/sources/data.sqlite-wal", "resources/runtime/melange/sources/cache-journal"]:
            with self.subTest(name=name), self.assertRaises(module.Refused):
                module.refuse_private(name)

    def test_public_cryptography_marker_literal_is_not_private_key_material(self):
        name = "resources/runtime/melange/python/Lib/site-packages/cryptography/hazmat/primitives/serialization/ssh.py"
        file = self.source / name
        file.parent.mkdir(parents=True)
        file.write_bytes(b'_SK_START = b"-----BEGIN OPENSSH PRIVATE KEY-----"\n_SK_END = b"-----END OPENSSH PRIVATE KEY-----"\n')
        module.build(self.source, self.root / "cryptography.zip", "melange", "1.0.20")

    def test_private_pem_spanning_read_chunks_is_rejected(self):
        file = self.source / "resources/secret.txt"
        file.write_bytes(b" " * (1024 * 1024 - 20) + b"\n-----BEGIN PRIVATE KEY-----\n" + b"A" * 64 + b"\n-----END PRIVATE KEY-----\n")
        with self.assertRaises(module.Refused):
            module.stream_file(file)

    def test_refuses_incomplete_and_cross_application_payload(self):
        with self.assertRaises(module.Refused):
            module.inventory_for(self.source, "terrier", "1.0.20")
        (self.source / "resources/app.asar").unlink()
        with self.assertRaises(module.Refused):
            module.inventory_for(self.source, "melange", "1.0.20")

    def test_windows_paths_and_output_inside_source_are_refused(self):
        for name in ["../escape", "C:/escape", "a\\b", "a/CON.txt", "LPT²", "a:ads", "a./b", "a /b"]:
            with self.subTest(name=name), self.assertRaises(module.Refused):
                module.safe_path(name)
        with self.assertRaises(module.Refused):
            module.build(self.source, self.source / "inside.zip", "melange", "1.0.20")

    def test_hardlinked_source_refused(self):
        (self.root / "linked.exe").hardlink_to(self.source / "Melange.exe")
        with self.assertRaises(module.Refused):
            module.inventory_for(self.source, "melange", "1.0.20")


if __name__ == "__main__":
    unittest.main()
