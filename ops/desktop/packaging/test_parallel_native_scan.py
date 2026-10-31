"""Exact-census equivalence and hardlink denial for bounded parallel scanning."""
from pathlib import Path
import os
import struct
import tempfile
import unittest
import verify_native_release as native


class ParallelScan(unittest.TestCase):
    def test_same_complete_map_and_header_classification_as_serial(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'nested').mkdir()
            header = bytearray(512)
            header[:2] = b'MZ'
            struct.pack_into('<I', header, 60, 128)
            header[128:132] = b'PE\0\0'
            for name, data in {'empty': b'', 'not-native.exe': b'text',
                               'nested/native.data': header,
                               'nested/large': bytes(range(256)) * 10000}.items():
                (root / name).write_bytes(data)
            serial_files = native.legacy.tree(root)
            for path in serial_files.values():
                native.physical(path)
            serial_native, serial_hashes = native.legacy.inspect_files(serial_files)
            files, pes, actual = native.scan(root)
            self.assertEqual(files, serial_files)
            self.assertEqual(pes, serial_native)
            self.assertEqual(pes, {'nested/native.data'})
            self.assertEqual(actual, {name: {'sha256': serial_hashes[name], 'size': path.stat().st_size}
                                      for name, path in serial_files.items()})

    def test_parallel_scan_retains_single_link_requirement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'original').write_bytes(b'bound content')
            os.link(root / 'original', root / 'alias')
            with self.assertRaises(native.Refused):
                native.scan(root)


if __name__ == '__main__':
    unittest.main()
