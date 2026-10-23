"""Synthetic-fixture tests for the source-bound release verifier (no installer needed)."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

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


if __name__ == "__main__":
    unittest.main()
