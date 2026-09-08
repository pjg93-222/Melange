"""Encrypted storage regression tests; never access real credentials."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from fec_key_store import load_keys, save_keys, record_validation


@unittest.skipUnless(os.name == 'nt', 'Windows DPAPI')
class KeyStoreTests(unittest.TestCase):
    def test_disabled_keys_survive_import_without_becoming_active(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'keys.dpapi'
            save_keys(['fixture-one', 'fixture-two'], path)
            identifier = hashlib.sha256(b'fixture-one').hexdigest()[:12]
            record_validation([{'key_id': identifier, 'status': 'http_403'}], path)
            save_keys(['fixture-one', 'fixture-three'], path)
            self.assertEqual(load_keys(path), ['fixture-two', 'fixture-three'])
            self.assertEqual(len(load_keys(path, include_disabled=True)), 3)
            self.assertNotIn(b'fixture', path.read_bytes())
            record_validation([{'key_id': identifier, 'status': 'valid'}], path)
            self.assertEqual(len(load_keys(path)), 3)

    def test_concurrent_imports_preserve_all_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'keys.dpapi'
            with ThreadPoolExecutor(max_workers=4) as pool:
                list(pool.map(lambda i: save_keys([f'fixture-{i}'], path), range(12)))
            self.assertEqual(set(load_keys(path)), {f'fixture-{i}' for i in range(12)})

    def test_corrupt_ciphertext_fails_without_overwriting_it(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'keys.dpapi'
            path.write_bytes(b'corrupt encrypted store')
            with self.assertRaises(RuntimeError):
                save_keys(['fixture-key'], path)
            self.assertEqual(path.read_bytes(), b'corrupt encrypted store')


if __name__ == '__main__':
    unittest.main()
