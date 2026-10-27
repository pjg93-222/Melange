import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import directory_zip_native as native


class NativeZipTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="native-directory-zip-")
        self.root = Path(self.temp.name).resolve()
        self.archive = self.root / "fixture.zip"
        self.files = {"000-first.bin": b"alphabetically before inventory", "resources/caf\u00e9.txt": b"exact nested unicode file", "Melange.exe": b"MZ fixture", "resources/app.asar": b"ASAR fixture", "resources/runtime/melange/fixture.py": b"fixture runtime"}
        self.inventory = {"schemaVersion": 1, "appId": "melange", "version": "1.0.20", "entrypoint": "Melange.exe", "files": [
            {"path": name, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()} for name, data in self.files.items()]}
        self.encoded = json.dumps(self.inventory, separators=(",", ":")).encode()
        with zipfile.ZipFile(self.archive, "w", compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr("000-first.bin", self.files["000-first.bin"])
            z.writestr(native.guard.INVENTORY, self.encoded)
            for name, data in self.files.items():
                if name != "000-first.bin":
                    z.writestr(name, data)

    def tearDown(self):
        self.temp.cleanup()

    def test_reorder_changes_only_central_record_order_and_preserves_offsets(self):
        before = self.archive.read_bytes()
        with zipfile.ZipFile(self.archive) as z:
            offsets = {row.filename: row.header_offset for row in z.infolist()}
        region = native.reorder_directory(self.archive, [native.guard.INVENTORY, *self.files])
        after = self.archive.read_bytes()
        self.assertEqual(before[:region["offset"]], after[:region["offset"]])
        end = region["offset"] + region["size"]
        self.assertEqual(before[end:], after[end:])
        self.assertEqual(len(before), len(after))
        with zipfile.ZipFile(self.archive) as z:
            self.assertEqual(z.namelist()[0], native.guard.INVENTORY)
            self.assertEqual({row.filename: row.header_offset for row in z.infolist()}, offsets)
        native.verify_archive(self.archive, self.inventory, self.encoded)

    def test_rejects_unknown_missing_or_duplicate_members_before_rewriting(self):
        before = self.archive.read_bytes()
        for names in [[native.guard.INVENTORY], [native.guard.INVENTORY, *self.files, "unknown"]]:
            with self.assertRaises(native.guard.Refused):
                native.reorder_directory(self.archive, names)
            self.assertEqual(self.archive.read_bytes(), before)
        with zipfile.ZipFile(self.archive, "a") as z:
            z.writestr("000-first.bin", b"duplicate")
        with self.assertRaises(native.guard.Refused):
            native.reorder_directory(self.archive, [native.guard.INVENTORY, *self.files])

    def test_rejects_zip64_multidisk_and_out_of_bounds_records(self):
        original = self.archive.read_bytes()
        end = original.rfind(b"PK\x05\x06")
        for offset, encoding, value in [(end + 4, "<H", 1), (end + 10, "<H", 65535), (end + 16, "<I", len(original))]:
            changed = bytearray(original)
            struct.pack_into(encoding, changed, offset, value)
            self.archive.write_bytes(changed)
            with self.assertRaises(native.guard.Refused):
                native.reorder_directory(self.archive, [native.guard.INVENTORY, *self.files])
            self.assertEqual(self.archive.read_bytes(), changed)

    def test_completed_zip_rejects_source_mutation_before_publisher_proof(self):
        native.reorder_directory(self.archive, [native.guard.INVENTORY, *self.files])
        changed = json.loads(json.dumps(self.inventory))
        changed["files"][0]["sha256"] = "a" * 64
        with self.assertRaisesRegex(native.guard.Refused, "bytes differ"):
            native.verify_archive(self.archive, changed, self.encoded)

    @unittest.skipUnless(os.environ.get("DIRECTORY_ZIP_7ZA"), "Set DIRECTORY_ZIP_7ZA for native compatibility test")
    def test_real_native_append_then_reorder_is_runtime_compatible(self):
        source = self.root / "source"
        source.mkdir()
        for name, data in self.files.items():
            file = source / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(data)
        (source / "not-listed.txt").write_bytes(b"must not enter ZIP")
        listing = self.root / "files.txt"
        listing.write_text("\n".join(self.files) + "\n", encoding="utf-8")
        archive = self.root / "native.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr(native.guard.INVENTORY, self.encoded)
        subprocess.run([os.environ["DIRECTORY_ZIP_7ZA"], "a", "-tzip", "-mm=Deflate", "-mx=1", "-mmt=4", "-scsUTF-8", "-spd", "-r-", "-y", str(archive), "@" + str(listing)], cwd=source, check=True, capture_output=True)
        native.reorder_directory(archive, [native.guard.INVENTORY, *self.files])
        native.verify_archive(archive, self.inventory, self.encoded)

    @unittest.skipUnless(os.environ.get("DIRECTORY_ZIP_7ZA"), "Set DIRECTORY_ZIP_7ZA for native compatibility test")
    def test_complete_native_package_passes_actual_runtime_reader(self):
        source = self.root / "source"
        for name, data in self.files.items():
            file = source / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(data)
        archive = self.root / "complete.zip"
        descriptor = native.build(source, archive, "melange", "1.0.20", Path(os.environ["DIRECTORY_ZIP_7ZA"]))
        client = Path(__file__).resolve().parents[1] / "client/directory-package.cjs"
        script = "const [m,a,d,p]=process.argv.slice(1);require(m).extract(a,d,{appId:'melange',version:'1.0.20',entrypoint:'Melange.exe',archive:JSON.parse(p)}).then(i=>{if(i.files.length!==5)throw Error('wrong file count')}).catch(e=>{console.error(e);process.exitCode=1})"
        subprocess.run(["node", "-e", script, str(client), str(archive), str(self.root / "extracted"), json.dumps(descriptor)], check=True, capture_output=True)
        for name, data in self.files.items():
            self.assertEqual((self.root / "extracted" / name).read_bytes(), data)

    @unittest.skipUnless(os.environ.get("DIRECTORY_ZIP_7ZA"), "Set DIRECTORY_ZIP_7ZA for native compatibility test")
    def test_preexisting_list_file_is_not_deleted_on_exclusive_creation_failure(self):
        source = self.root / "source"
        for name, data in self.files.items():
            file = source / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(data)
        temporary = self.root / "collision.tmp"
        listing = temporary.with_suffix(".list")
        listing.write_bytes(b"preexisting unrelated file")
        def collision(**_):
            return os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL), str(temporary)
        with patch.object(native.tempfile, "mkstemp", side_effect=collision), self.assertRaises(FileExistsError):
            native.build(source, self.root / "refused.zip", "melange", "1.0.20", Path(os.environ["DIRECTORY_ZIP_7ZA"]))
        self.assertEqual(listing.read_bytes(), b"preexisting unrelated file")
        self.assertFalse(temporary.exists())


if __name__ == "__main__":
    unittest.main()
