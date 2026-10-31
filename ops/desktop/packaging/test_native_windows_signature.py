"""Native API regressions. Real fixtures require explicitly named Windows inputs."""
import copy
import datetime
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import native_windows_signature as native


def verdict(**changes):
    value = dict(thumbprint=native.PINNED, validAtVerificationTime=True, counterSignerErrors=False,
                 certificateError=0, signerError=0, chainErrors=0, wintrustStatus=0, selfSigned=True)
    value.update(changes)
    return value


class VerdictTests(unittest.TestCase):
    def test_only_root_trust_exception_and_timestamp_time_are_accepted(self):
        self.assertTrue(native.accepted(verdict()))
        self.assertTrue(native.accepted(verdict(wintrustStatus=native.UNTRUSTED_ROOT,
            chainErrors=0x20, certificateError=native.UNTRUSTED_ROOT, signerError=native.UNTRUSTED_ROOT)))
        # The API result is validity at Windows' verified signing timestamp, not
        # current wall time. An expired-today certificate is not rejected here.
        self.assertTrue(native.accepted(verdict(validAtVerificationTime=True)))
        self.assertTrue(native.accepted(verdict(chainErrors=0x01000040)))
        for change in ({'wintrustStatus': 0x80096010}, {'wintrustStatus': 0x800B0100},
                       {'wintrustStatus': 0x800B0101}, {'wintrustStatus': 0x800B010C},
                       {'wintrustStatus': 0x800B0004},
                       {'thumbprint': '0' * 40}):
            with self.subTest(change=change):
                self.assertFalse(native.accepted(verdict(**change)))
        for change in ({'chainErrors': 0x01000040}, {'validAtVerificationTime': False},
                       {'counterSignerErrors': True}, {'certificateError': 0x800B010C}, {'signerError': 0x80096010}):
            with self.subTest(root_exception=change):
                self.assertFalse(native.accepted(verdict(wintrustStatus=native.UNTRUSTED_ROOT, **change)))
        self.assertFalse(native.accepted(verdict(wintrustStatus=native.UNTRUSTED_ROOT,
                                               chainErrors=0x20, selfSigned=False)))

    def test_request_rejects_duplicate_fields(self):
        with self.assertRaises(ValueError):
            json.loads('{"path":"a","path":"b"}', object_pairs_hook=native._object)


@unittest.skipUnless(os.name == 'nt' and os.environ.get('SIGNATURE_TEST_SIGNED_PE')
                     and os.environ.get('SIGNATURE_TEST_SIGNTOOL'),
                     'Set SIGNATURE_TEST_SIGNED_PE and SIGNATURE_TEST_SIGNTOOL for real Windows verification')
class RealWindowsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='native-signature-test-')
        cls.root = Path(cls.temporary.name)
        cls.signed = Path(os.environ['SIGNATURE_TEST_SIGNED_PE'])
        original = cls.signed.read_bytes()
        pe = struct.unpack_from('<I', original, 0x3c)[0]
        optional = pe + 24
        magic = struct.unpack_from('<H', original, optional)[0]
        security = optional + (112 if magic == 0x20b else 96) + 32
        certificate_at, certificate_bytes = struct.unpack_from('<II', original, security)
        if certificate_at + certificate_bytes != len(original):
            raise ValueError('The signed fixture must have a final Authenticode table')
        unsigned = bytearray(original[:certificate_at])
        struct.pack_into('<II', unsigned, security, 0, 0)
        struct.pack_into('<I', unsigned, optional + 64, 0)
        cls.unsigned = cls.root / 'unsigned.exe'
        cls.unsigned.write_bytes(unsigned)
        first_section = optional + struct.unpack_from('<H', original, pe + 20)[0]
        raw_start = struct.unpack_from('<I', original, first_section + 20)[0]
        tampered = bytearray(original)
        tampered[raw_start + 16] ^= 1
        cls.tampered = cls.root / 'tampered.exe'
        cls.tampered.write_bytes(tampered)
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives.serialization import pkcs12
        from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'Disposable signature regression fixture')])
        now = datetime.datetime.now(datetime.timezone.utc)
        cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
                .serial_number(x509.random_serial_number()).not_valid_before(now - datetime.timedelta(days=1))
                .not_valid_after(now + datetime.timedelta(days=1))
                .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
                .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CODE_SIGNING]), critical=False)
                .sign(key, hashes.SHA256()))
        cls.other_pin = cert.fingerprint(hashes.SHA1()).hex().upper()
        pfx = cls.root / 'disposable.pfx'
        pfx.write_bytes(pkcs12.serialize_key_and_certificates(b'fixture', key, cert, None, serialization.NoEncryption()))
        cls.other = cls.root / 'untrusted-self-signed.exe'
        cls.other.write_bytes(unsigned)
        completed = subprocess.run([os.environ['SIGNATURE_TEST_SIGNTOOL'], 'sign', '/fd', 'SHA256',
                                    '/f', str(pfx), str(cls.other)], capture_output=True, timeout=30)
        if completed.returncode:
            raise RuntimeError('Signing the disposable fixture failed')

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_actual_pinned_signature(self):
        result = native.signature(str(self.signed))
        self.assertEqual(result['verdict'], 'verified')
        self.assertEqual(result['thumbprint'], native.PINNED)

    def test_actual_unsigned_and_tampered(self):
        for filename, status in ((self.unsigned, 0x800B0100), (self.tampered, 0x80096010)):
            with self.subTest(filename=filename.name):
                result = native.signature(str(filename))
                self.assertEqual(result['verdict'], 'refused')
                self.assertEqual(result['wintrustStatus'], status)

    def test_actual_untrusted_self_signed_is_distinct_from_wrong_publisher(self):
        result = native.signature(str(self.other))
        self.assertEqual(result['wintrustStatus'], native.UNTRUSTED_ROOT)
        self.assertEqual(result['chainErrors'], 0x20)
        self.assertTrue(result['selfSigned'])
        self.assertTrue(result['validAtVerificationTime'])
        self.assertEqual(result['thumbprint'], self.other_pin)
        self.assertEqual(result['verdict'], 'refused')  # never the production pin
        # Evaluate the very same real Windows chain verdict under a test-only
        # matching pin. No certificate is inserted into any Windows trust store.
        with patch.object(native, 'PINNED', self.other_pin):
            self.assertTrue(native.accepted(result))

    def test_missing_file_is_no_verdict(self):
        with self.assertRaises(OSError):
            native.signature(str(self.root / 'missing.exe'))

    @unittest.skipUnless(os.environ.get('SIGNATURE_TEST_TIMESTAMPED_PE'),
                         'Set SIGNATURE_TEST_TIMESTAMPED_PE to an expired-today, timestamped vendor fixture')
    def test_real_timestamp_preserves_an_expired_today_signer(self):
        from cryptography.hazmat.primitives.serialization import pkcs7
        from cryptography.hazmat.primitives import hashes
        import warnings
        filename = Path(os.environ['SIGNATURE_TEST_TIMESTAMPED_PE'])
        result = native.signature(str(filename))
        self.assertEqual(result['wintrustStatus'], 0)
        self.assertTrue(result['validAtVerificationTime'])
        raw = filename.read_bytes()
        optional = struct.unpack_from('<I', raw, 60)[0] + 24
        security = optional + (112 if struct.unpack_from('<H', raw, optional)[0] == 0x20b else 96) + 32
        offset, length = struct.unpack_from('<II', raw, security)
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            certificates = pkcs7.load_der_pkcs7_certificates(raw[offset + 8:offset + length])
        signer = next(cert for cert in certificates if cert.fingerprint(hashes.SHA1()).hex().upper() == result['thumbprint'])
        self.assertLess(signer.not_valid_after_utc, datetime.datetime.now(datetime.timezone.utc))
        self.assertEqual(result['verdict'], 'refused')  # vendor is not our publisher
        with patch.object(native, 'PINNED', result['thumbprint']):
            self.assertTrue(native.accepted(result))  # Windows verified its timestamp


if __name__ == '__main__':
    unittest.main()
