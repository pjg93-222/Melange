import hashlib
import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import data_release  # noqa: E402


class BuildTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "data"
        self.out = Path(self.tmp.name) / "out"
        files = {
            "Moneyball.html": b"<html>real</html>",
            "audits/a/b.json": b'{"x": 1}',
            "data/engine/e.csv": b"a,b\n1,2\n" * 50,
            "keys/x.json": b"secret",
            "audits/staffer_network/politico_profile_crawl_1_raw/a.html": b"licensed",
        }
        for rel, body in files.items():
            p = self.root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(body)

    def tearDown(self):
        self.tmp.cleanup()

    def test_build_manifest_and_exclusions(self):
        m = data_release.build("melange", self.root, self.out, "data-melange-2026-10-21", [], data_release.DENY,
                               data_release.DEFAULT_PART_BYTES)
        self.assertEqual(sorted(m["excluded"]),
                         ["audits/staffer_network/politico_profile_crawl_1_raw/a.html", "keys/x.json"])
        self.assertEqual(len(m["assets"]), 1)
        names = set()
        for asset in m["assets"]:
            zp = self.out / asset["name"]
            self.assertEqual(hashlib.sha256(zp.read_bytes()).hexdigest(), asset["sha256"])
            with zipfile.ZipFile(zp) as zf:
                for info in zf.infolist():
                    self.assertFalse(info.filename.startswith(("/", "..")))
                    body = zf.read(info)
                    entry = next(f for f in m["files"] if f["path"] == info.filename)
                    self.assertEqual(hashlib.sha256(body).hexdigest(), entry["sha256"])
                    names.add(info.filename)
        self.assertEqual(names, {f["path"] for f in m["files"]})
        sums = (self.out / "SHA256SUMS").read_text().splitlines()
        self.assertEqual(len(sums), len(m["assets"]) + 1)
        self.assertIn("manifest.json", sums[-1])
        self.assertEqual(json.loads((self.out / "manifest.json").read_text())["schema"], data_release.SCHEMA)
        self.assertIn("keys/x.json", (self.out / "EXCLUDED.txt").read_text())

    def test_parts_split_and_cover_every_file_once(self):
        m = data_release.build("melange", self.root, self.out, "data-melange-2026-10-21", [], data_release.DENY,
                               part_bytes=100)
        self.assertGreater(len(m["assets"]), 1)
        seen = []
        for asset in m["assets"]:
            with zipfile.ZipFile(self.out / asset["name"]) as zf:
                seen.extend(zf.namelist())
        self.assertEqual(sorted(seen), sorted(f["path"] for f in m["files"]))
        self.assertEqual(len(seen), len(set(seen)))

    def test_file_that_grows_during_the_build_matches_its_zip_member(self):
        growing, real_open = self.root / "data/engine/e.csv", Path.open

        def open_after_a_write(path, mode="r", *args, **kwargs):
            if path == growing and mode == "rb":  # a writer appends after the size was read and before the copy
                with real_open(path, "ab") as fh:
                    fh.write(b"3,4\n")
            return real_open(path, mode, *args, **kwargs)
        with mock.patch.object(Path, "open", open_after_a_write):
            m = data_release.build("melange", self.root, self.out, "data-melange-2026-10-21", [], data_release.DENY,
                                   data_release.DEFAULT_PART_BYTES)
        entry = next(f for f in m["files"] if f["path"] == "data/engine/e.csv")
        with zipfile.ZipFile(self.out / entry["asset"]) as zf:
            body = zf.read("data/engine/e.csv")
        self.assertEqual(entry["bytes"], len(body))
        self.assertEqual(entry["sha256"], hashlib.sha256(body).hexdigest())

    def test_allow_overrides_soft_denies_only(self):
        hard = ["keys/x.json", "a/credentials/c.json", "a/blob.dpapi", "a/accounts.sqlite3", "a/.env.local", "a/keys.json",
                "a/tls.pem", ".melange-data-release.json"]
        for rel in hard[1:] + ["audits/session_118.json"]:
            (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.root / rel).write_bytes(b"x")
        m = data_release.build("melange", self.root, self.out, "data-melange-2026-10-21",
                               ["**/*"], data_release.DENY, data_release.DEFAULT_PART_BYTES)
        self.assertEqual(sorted(m["excluded"]), sorted(hard))
        self.assertIn("audits/session_118.json", {f["path"] for f in m["files"]})
        self.assertIn("audits/staffer_network/politico_profile_crawl_1_raw/a.html", {f["path"] for f in m["files"]})

    def test_restricted_lda_corpus_never_ships_even_when_allowed(self):
        corpus = ["__state__/Melange/staffer_network/normalized/lda-source-native/generation-x/lda_lobbyist_assertions.ndjson.gz",
                  "data/engine/staffer_organisations_section.json", "data/engine/staffer_clients_section.json",
                  "staffer-network.html"]
        for rel in corpus + ["data/engine/staffer_offices_section.json"]:
            (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.root / rel).write_bytes(b"x")
        m = data_release.build("melange", self.root, self.out, "data-melange-2026-10-21",
                               ["**/*"], data_release.DENY, data_release.DEFAULT_PART_BYTES)
        shipped = {f["path"] for f in m["files"]}
        self.assertFalse(shipped & set(corpus))
        self.assertTrue(set(corpus) <= set(m["excluded"]))
        self.assertIn("data/engine/staffer_offices_section.json", shipped)
        # A --map mount under a neutral name is still caught by the real path.
        m = data_release.build("melange", None, self.out, "data-melange-2026-10-21", ["**/*"], data_release.DENY,
                               data_release.DEFAULT_PART_BYTES, [("catalog/c", self.root / "__state__")])
        self.assertEqual(m["files"], [])

    def test_single_file_map_cannot_rename_a_credential_in(self):
        m = data_release.build("melange", None, self.out, "data-melange-2026-10-21", ["**/*"], data_release.DENY,
                               data_release.DEFAULT_PART_BYTES, [("catalog/one.json", self.root / "keys" / "x.json"),
                                                                 ("catalog/two.json", self.root / "audits" / "a" / "b.json")])
        self.assertEqual(m["excluded"], ["catalog/one.json"])
        self.assertEqual([f["path"] for f in m["files"]], ["catalog/two.json"])

    def test_links_inside_a_source_are_not_followed(self):
        import subprocess
        outside = Path(self.tmp.name) / "outside"
        outside.mkdir()
        (outside / "private.csv").write_bytes(b"not for release")
        link = self.root / "audits" / "linked"
        if os.name == "nt":
            subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(outside)], check=True, capture_output=True)
        else:
            link.symlink_to(outside, target_is_directory=True)
        m = data_release.build("melange", self.root, self.out, "data-melange-2026-10-21", [], data_release.DENY,
                               data_release.DEFAULT_PART_BYTES)
        self.assertIn("audits/linked", m["excluded"])
        self.assertFalse(any("private" in f["path"] for f in m["files"]))

    def test_out_inside_a_source_is_refused(self):
        with self.assertRaises(ValueError):
            data_release.build("melange", self.root, self.root / "release", "data-melange-2026-10-21", [], data_release.DENY,
                               data_release.DEFAULT_PART_BYTES)

    def test_maps_mount_sources_at_virtual_paths(self):
        base = Path(self.tmp.name)
        audits, state, single = base / "src_audits", base / "src_state", base / "loose.json"
        for p, body in {audits / "r.json": b"1", audits / "deep/s.csv": b"2", state / "a.sqlite": b"3",
                        state / "keys/k.json": b"secret", single: b"4"}.items():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(body)
        rc = data_release.main(["build", "--app", "melange", "--out", str(self.out), "--tag", "data-melange-2026-10-21",
                                "--map", f"audits/x={audits}", "--map", f"__state__/Melange/y={state}",
                                "--map", f"catalog/one.json={single}"])
        self.assertEqual(rc, 0)
        m = json.loads((self.out / "manifest.json").read_text())
        expected = ["__state__/Melange/y/a.sqlite", "audits/x/deep/s.csv", "audits/x/r.json", "catalog/one.json"]
        self.assertEqual(sorted(f["path"] for f in m["files"]), expected)
        self.assertEqual(m["excluded"], ["__state__/Melange/y/keys/k.json"])
        with zipfile.ZipFile(self.out / m["assets"][0]["name"]) as zf:
            self.assertEqual(sorted(zf.namelist()), expected)
            self.assertEqual(zf.read("catalog/one.json"), b"4")
        # maps add to --data-root; a virtual path claimed twice is refused
        m = data_release.build("melange", self.root, self.out, "data-melange-2026-10-21", [], data_release.DENY,
                               data_release.DEFAULT_PART_BYTES, [("audits/x", audits)])
        self.assertIn("Moneyball.html", {f["path"] for f in m["files"]})
        self.assertIn("audits/x/r.json", {f["path"] for f in m["files"]})
        with self.assertRaises(ValueError):
            data_release.build("melange", self.root, self.out, "data-melange-2026-10-21", [], data_release.DENY,
                               data_release.DEFAULT_PART_BYTES, [("Moneyball.html", single)])
        for bad in ("../x=" + str(single), "/x=" + str(single), "x=relative/path", "noequals"):
            with self.assertRaises(SystemExit):
                data_release.main(["build", "--app", "melange", "--out", str(self.out), "--map", bad])
        with self.assertRaises(SystemExit):
            data_release.main(["build", "--app", "melange", "--out", str(self.out)])


if __name__ == "__main__":
    unittest.main()
