"""Container security fixtures only; these do not attest domain/app readiness."""
import hashlib
import io
import os
from pathlib import Path
import stat
import struct
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import zlib

from module_application_contracts import DataIntakeBlocked
from workspace_archive import DomainArchive
from workspace_data_contract import INDUSTRY_MEMBERS, INDUSTRY_PAGES_KIND


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='closed analytical archive ')
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / 'pages.data.zip'

    def make(self, *, names=INDUSTRY_MEMBERS, symlink=False, zip64=False, large=False):
        with zipfile.ZipFile(self.path, 'w') as archive:
            for number, name in enumerate(names):
                info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = ((stat.S_IFLNK if symlink and number == 0 else stat.S_IFREG) | 0o600) << 16
                payload = b'{"fixture":"' + b'a' * (1024 * 1024 if large else 1) + b'"}'
                with archive.open(info, 'w', force_zip64=zip64) as stream:
                    stream.write(payload)
        return hashlib.sha256(self.path.read_bytes()).hexdigest()

    def open(self, digest, **options):
        return DomainArchive(self.path, app_id='melange', kind=INDUSTRY_PAGES_KIND,
                             role='pages', expected_sha256=digest, **options)

    def test_exact_enum_deflate_and_zip64_stream_without_extracting_files(self):
        for zip64 in (False, True):
            digest = self.make(zip64=zip64, large=True)
            with self.open(digest) as archive:
                self.assertEqual(set(archive.index), set(INDUSTRY_MEMBERS))
                self.assertEqual(len(archive.json('champions.json')['fixture']), 1024 * 1024)
            self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_older_changed_timestamp_archive_reopens_without_cross_api_ctime_assumption(self):
        digest=self.make()
        os.utime(self.path,(946684800,946684800))
        with self.open(digest) as archive:
            self.assertEqual(archive.json('champions.json'),{'fixture':'a'})
            archive._check()

    def test_unknown_missing_case_alias_ads_dot_path_and_symlink_members_reject(self):
        for bad in ('../champions.json', '/champions.json', 'Champions.json', 'champions.json:secret',
                    'champions.json/./value', 'code.py'):
            with self.subTest(member=bad):
                digest = self.make(names=(bad, *INDUSTRY_MEMBERS[1:]))
                with self.assertRaises(DataIntakeBlocked):
                    self.open(digest)
        with self.assertRaises(DataIntakeBlocked):
            self.open(self.make(symlink=True))
        with self.assertRaises(DataIntakeBlocked):
            self.open(self.make(names=INDUSTRY_MEMBERS[:-1]))
        self.make()
        # ZipInfo's writer truncates NUL; mutate the actual local+central name
        # bytes instead, preserving the encoded lengths of this hostile input.
        raw = self.path.read_bytes().replace(b'champions.json', b'champions\x00json')
        self.path.write_bytes(raw)
        with self.assertRaises(DataIntakeBlocked):
            self.open(hashlib.sha256(raw).hexdigest())

    def test_hash_mutation_and_cancellation_refuse_before_serving(self):
        digest = self.make()
        with self.assertRaises(DataIntakeBlocked):
            self.open('0' * 64)
        with self.assertRaises(DataIntakeBlocked):
            self.open(digest, is_cancelled=lambda: True)
        with self.open(digest) as archive:
            raw = self.path.read_bytes()
            self.path.write_bytes(raw[:-1] + bytes([raw[-1] ^ 1]))
            with self.assertRaises(DataIntakeBlocked):
                archive.json('champions.json')

    def test_central_directory_count_is_bounded_before_zipfile_allocates_entries(self):
        digest = self.make()
        raw = bytearray(self.path.read_bytes())
        raw[-14:-10] = b'\xff\xff\xff\xff'
        self.path.write_bytes(raw)
        with patch('workspace_archive.zipfile.ZipFile', side_effect=AssertionError('unbounded parser must not run')) as parser:
            with self.assertRaises(DataIntakeBlocked):
                self.open(hashlib.sha256(raw).hexdigest())
            parser.assert_not_called()

    def test_prepended_hidden_bytes_and_comments_are_not_members(self):
        self.make()
        for change in (lambda raw: b'MZhidden' + raw, lambda raw: raw + b'hidden'):
            self.make()
            raw = change(self.path.read_bytes())
            self.path.write_bytes(raw)
            with self.assertRaises(DataIntakeBlocked):
                self.open(hashlib.sha256(raw).hexdigest())

    def test_compressed_padding_is_rejected_even_when_zip_crc_and_declared_size_match(self):
        local, central = bytearray(), bytearray()
        for name in INDUSTRY_MEMBERS:
            encoded, raw = name.encode('ascii'), b'{}'
            compressor = zlib.compressobj(1, zlib.DEFLATED, -15)
            packed = compressor.compress(raw) + compressor.flush()
            if name == 'champions.json':
                packed += b'private unparsed padding'
            crc, offset = zlib.crc32(raw), len(local)
            local.extend(struct.pack('<4s5H3L2H', b'PK\x03\x04', 20, 0, 8, 0, 0, crc, len(packed), len(raw), len(encoded), 0))
            local.extend(encoded + packed)
            central.extend(struct.pack('<4s6H3L5H2L', b'PK\x01\x02', 20, 20, 0, 8, 0, 0, crc,
                len(packed), len(raw), len(encoded), 0, 0, 0, 0, 0, offset))
            central.extend(encoded)
        body = bytes(local + central + struct.pack('<4s4H2LH', b'PK\x05\x06', 0, 0, len(INDUSTRY_MEMBERS),
            len(INDUSTRY_MEMBERS), len(central), len(local), 0))
        self.path.write_bytes(body)
        with self.open(hashlib.sha256(body).hexdigest()) as archive:
            with self.assertRaises(DataIntakeBlocked):
                archive.json('champions.json')


if __name__ == '__main__':
    unittest.main()
