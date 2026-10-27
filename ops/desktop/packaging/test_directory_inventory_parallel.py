import importlib.util
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("directory_inventory_parallel", Path(__file__).with_name("directory_inventory_parallel.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ParallelInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="parallel-directory-inventory-")
        self.root = Path(self.temp.name).resolve()
        self.source = self.root / "win-unpacked"
        for name, contents in {"Melange.exe": b"MZ fixture", "resources/app.asar": b"ASAR fixture", "resources/runtime/melange/python/python.exe": b"MZ runtime fixture"}.items():
            self.add(name, contents)

    def tearDown(self):
        self.temp.cleanup()

    def add(self, name, contents=b"fixture"):
        target = self.source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(contents)
        return target

    def inventory(self, **kwargs):
        return module.inventory_for(self.source, "melange", "1.0.20", **kwargs)

    def test_exact_serial_equivalence_and_bounded_parallel_reads(self):
        for index in range(48):
            self.add(f"resources/data/{index:02}.txt", bytes([index]) * (index + 1))
        self.add("Uninstall Melange.exe")
        expected = module.guards.inventory_for(self.source, "melange", "1.0.20")
        original = module.guards.stream_file
        executor = module.ThreadPoolExecutor
        mutex = threading.Lock()
        active = outstanding = peak = pending_peak = 0
        seen = set()

        class CountingExecutor(executor):
            def submit(self, *args, **kwargs):
                nonlocal outstanding, pending_peak
                with mutex:
                    outstanding += 1
                    pending_peak = max(pending_peak, outstanding)
                future = super().submit(*args, **kwargs)
                def finished(_future):
                    nonlocal outstanding
                    with mutex:
                        outstanding -= 1
                future.add_done_callback(finished)
                return future

        def read(file):
            nonlocal active, peak
            with mutex:
                active += 1
                peak = max(peak, active)
                seen.add(file.relative_to(self.source).as_posix())
            try:
                time.sleep(0.005)
                return original(file)
            finally:
                with mutex:
                    active -= 1

        with patch.object(module, "ThreadPoolExecutor", CountingExecutor), patch.object(module.guards, "stream_file", read):
            actual = self.inventory()
        self.assertEqual(actual, expected)
        self.assertEqual(seen, {record["path"] for record in expected[0]["files"]})
        self.assertGreater(peak, 1)
        self.assertLessEqual(peak, 8)
        self.assertLessEqual(pending_peak, 16)
        self.assertEqual((active, outstanding), (0, 0))

    def test_worker_failure_cancels_queue_and_drains_running_readers(self):
        self.add("a-failure.bin")
        for index in range(32):
            self.add(f"z{index:02}.bin")
        original = module.guards.stream_file
        started, failure = threading.Event(), threading.Event()
        mutex = threading.Lock()
        active = 0

        def read(file):
            nonlocal active
            with mutex:
                active += 1
            try:
                if file.name == "Melange.exe":
                    started.set()
                    self.assertTrue(failure.wait(5))
                    time.sleep(0.03)
                elif file.name == "a-failure.bin":
                    self.assertTrue(started.wait(5))
                    failure.set()
                    raise RuntimeError("injected read failure")
                return original(file)
            finally:
                with mutex:
                    active -= 1

        with patch.object(module.guards, "stream_file", read), self.assertRaisesRegex(RuntimeError, "injected read failure"):
            self.inventory(workers=2)
        self.assertEqual(active, 0)
        self.assertFalse(any(thread.name.startswith("directory-inventory") for thread in threading.enumerate()))

    def test_invalid_worker_counts_are_refused(self):
        for workers in (0, 9, -1, True, 1.5, "8"):
            with self.subTest(workers=workers), self.assertRaises(module.guards.Refused):
                self.inventory(workers=workers)

    def test_private_filename_content_and_empty_directory_are_refused(self):
        for name, contents in [("settings.json", b"{}"), ("resources/key.pem", b"-----BEGIN PRIVATE KEY-----\n" + b"A" * 64 + b"\n-----END PRIVATE KEY-----\n"), ("resources/runtime/melange/sources/cache.sqlite", b"db")]:
            with self.subTest(name=name):
                target = self.add(name, contents)
                with self.assertRaises(module.guards.Refused):
                    self.inventory()
                target.unlink()
        (self.source / ".ssh").mkdir()
        with self.assertRaises(module.guards.Refused):
            self.inventory()

    def test_hardlink_and_excluded_hardlink_are_refused(self):
        (self.root / "linked.exe").hardlink_to(self.source / "Melange.exe")
        with self.assertRaises(module.guards.Refused):
            self.inventory()
        (self.root / "linked.exe").unlink()
        target = self.add("Uninstall Melange.exe")
        (self.root / "linked.exe").hardlink_to(target)
        with self.assertRaises(module.guards.Refused):
            self.inventory()

    def test_case_alias_limits_and_required_files_are_refused(self):
        original_walk = os.walk
        def aliases(*args, **kwargs):
            for current, dirs, names in original_walk(*args, **kwargs):
                yield current, dirs, names + (["Melange.EXE"] if Path(current) == self.source else [])
        with patch.object(module.os, "walk", aliases), self.assertRaises(module.guards.Refused):
            self.inventory()
        with patch.object(module.guards, "MAX_FILES", 2), self.assertRaises(module.guards.Refused):
            self.inventory()
        with patch.object(module.guards, "MAX_TOTAL", 1), self.assertRaises(module.guards.Refused):
            self.inventory()
        (self.source / "resources/app.asar").unlink()
        with self.assertRaises(module.guards.Refused):
            self.inventory()


if __name__ == "__main__":
    unittest.main()
