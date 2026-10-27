"""Verify the pinned code-signing publisher's detached proof for a whole ZIP.

No private signing key is loaded by this module. Payload encoding must stay
byte-identical to client/directory-package-proof.cjs.
"""
import base64
import datetime as dt
import hashlib
import json
import re

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import ExtendedKeyUsageOID

FORMAT = 'windows-directory-zip-v1'
DISTRIBUTION = 'directory-zip'
UPDATER_VERSION = '2.0.0'
PINNED_THUMBPRINT = '0EBC9AD04E929CDD731EDB5D278A4143BC3D3D30'
NAMES = {'melange': 'Melange', 'mentat': 'Mentat', 'terrier': 'Terrier'}
DOMAIN = b'MELANGE-DESKTOP-DIRECTORY-ZIP-V1\n'


def strict_base64(value, maximum):
    if not isinstance(value, str) or not 0 < len(value) <= maximum * 2:
        raise ValueError('invalid publisher proof encoding')
    raw = base64.b64decode(value, validate=True)
    if not 0 < len(raw) <= maximum or base64.b64encode(raw).decode('ascii') != value:
        raise ValueError('invalid publisher proof encoding')
    return raw


def package_identity(manifest):
    package = manifest.get('package', {})
    app = manifest.get('appId')
    version = manifest.get('version')
    if (app not in NAMES or not isinstance(version, str)
            or not re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', version)
            or manifest.get('platform') != 'win32' or manifest.get('arch') != 'x64'
            or package.get('format') != FORMAT or package.get('entrypoint') != NAMES[app] + '.exe'
            or package.get('name') != f'{app}-{version}-win32-x64.zip'
            or type(package.get('size')) is not int or not 0 < package['size'] <= 20 * 1024**3
            or not isinstance(package.get('sha256'), str) or not re.fullmatch(r'[0-9a-f]{64}', package['sha256'])
            or len(strict_base64(package.get('sha512'), 64)) != 64):
        raise ValueError('invalid directory ZIP package identity')
    return {**{key: manifest[key] for key in ('appId', 'version', 'platform', 'arch')},
            **{key: package[key] for key in ('format', 'entrypoint', 'name', 'size', 'sha256', 'sha512')}}


def publisher_proof_payload(manifest):
    return DOMAIN + json.dumps(package_identity(manifest), separators=(',', ':'), ensure_ascii=True).encode('utf-8')


def verify_directory_package_proof(manifest):
    payload = publisher_proof_payload(manifest)
    proof = manifest['package'].get('publisherProof')
    if (not isinstance(proof, dict) or set(proof) != {'schemaVersion', 'algorithm', 'certificateDer', 'signature'}
            or type(proof.get('schemaVersion')) is not int or proof['schemaVersion'] != 1 or proof['algorithm'] != 'rsa-sha256'):
        raise ValueError('invalid directory ZIP publisher proof')
    raw = strict_base64(proof['certificateDer'], 16384)
    signature = strict_base64(proof['signature'], 1024)
    certificate = x509.load_der_x509_certificate(raw)
    thumbprint = hashlib.sha1(raw).hexdigest().upper()
    if (certificate.public_bytes(serialization.Encoding.DER) != raw or thumbprint != PINNED_THUMBPRINT
            or not isinstance(manifest.get('publisherThumbprints'), list) or thumbprint not in manifest['publisherThumbprints']):
        raise ValueError('directory ZIP publisher differs from pinned certificate')
    key = certificate.public_key()
    if (not isinstance(key, rsa.RSAPublicKey) or key.key_size < 2048
            or ExtendedKeyUsageOID.CODE_SIGNING not in certificate.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value):
        raise ValueError('unsupported directory ZIP signing certificate')
    issued = dt.datetime.fromisoformat(manifest['issuedAt'].replace('Z', '+00:00'))
    if issued.tzinfo is None or not certificate.not_valid_before_utc <= issued <= certificate.not_valid_after_utc:
        raise ValueError('directory ZIP release outside publisher certificate validity')
    key.verify(signature, payload, padding.PKCS1v15(), hashes.SHA256())
    return thumbprint
