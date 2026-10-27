"""ZIP publication uses real synthetic publisher/Ed25519 signatures; OS trust is a double."""
import base64
import datetime as dt
import hashlib
import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace
import zipfile

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from test_github_release import CLIENT, RUN, prepared_inputs, write_receipt
import github_release as release
import directory_package_proof as proof
from desktop_admin import Refused, Store, file_hashes, verify_envelope


@pytest.fixture
def directory_inputs(tmp_path, prepared_inputs, monkeypatch):
    store, spec, verified = prepared_inputs
    spec['packages'] = {'melange': spec['packages']['melange']}
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'Synthetic test signer')])
    now = dt.datetime.now(dt.timezone.utc)
    certificate = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(key.public_key())
                   .serial_number(x509.random_serial_number()).not_valid_before(now - dt.timedelta(days=1))
                   .not_valid_after(now + dt.timedelta(days=1))
                   .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CODE_SIGNING]), critical=False)
                   .sign(key, hashes.SHA256())).public_bytes(serialization.Encoding.DER)
    pin = hashlib.sha1(certificate).hexdigest().upper()
    monkeypatch.setattr(proof, 'PINNED_THUMBPRINT', pin)
    monkeypatch.setattr(release, 'PUBLISHER_THUMBPRINTS', (pin,))

    def signature(argv, **kwargs):
        assert argv[0] == 'powershell.exe'
        target = Path(kwargs['env']['DESKTOP_VERIFY_PACKAGE'])
        assert target.name == 'Melange.exe' and target.read_bytes() == b'SYNTHETIC APPLICATION'
        verified.append(str(target))
        return SimpleNamespace(stdout=json.dumps({'Status': 'Valid', 'Subject': 'CN=Synthetic test signer', 'Thumbprint': pin}))
    monkeypatch.setattr('desktop_admin.subprocess.run', signature)
    package = tmp_path / 'melange-1.0.0-win32-x64.zip'
    with zipfile.ZipFile(package, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('directory-package.json', '{}')
        archive.writestr('Melange.exe', b'SYNTHETIC APPLICATION')
        archive.writestr('resources/app.asar', b'SYNTHETIC ARCHIVE')
    manifest = {'appId': 'melange', 'version': '1.0.0', 'platform': 'win32', 'arch': 'x64',
                'issuedAt': now.isoformat(), 'publisherThumbprints': [pin],
                'package': {'name': package.name, 'format': proof.FORMAT, 'entrypoint': 'Melange.exe', **file_hashes(package)}}
    manifest['package']['publisherProof'] = {'schemaVersion': 1, 'algorithm': 'rsa-sha256',
        'certificateDer': base64.b64encode(certificate).decode(),
        'signature': base64.b64encode(key.sign(proof.publisher_proof_payload(manifest), padding.PKCS1v15(), hashes.SHA256())).decode()}
    proof_path = tmp_path / 'publisher-proof.json'
    proof_path.write_text(json.dumps(manifest['package']['publisherProof']))
    spec['packages']['melange'].update(package=str(package), format=proof.FORMAT, publisherProof=str(proof_path))
    write_receipt(spec, 'melange')
    receipt_path = Path(spec['packages']['melange']['receipt'])
    receipt = json.loads(receipt_path.read_text())
    receipt['osSignature']['format'] = proof.FORMAT
    receipt_path.write_text(json.dumps(receipt))
    return store, spec, verified, manifest


def test_directory_bundle_roundtrips_through_python_and_client_trust(tmp_path, directory_inputs):
    store, spec, verified, _ = directory_inputs
    output = tmp_path / 'release'
    index = release.prepare(store, spec, output)['melange']
    directory = output / 'melange'
    assert index['packageFormat'] == proof.FORMAT
    assert index['assets'] == sorted(['melange-1.0.0-win32-x64.zip', 'melange-win32-x64-directory-zip.manifest.json', 'melange-trust.json'])
    assert len(list(directory.iterdir())) == 5 and not (directory / 'turn-on-updates.cmd').exists()
    assert len(verified) == 1 and not Path(verified[0]).exists()
    assert release.verify_bundle(store, directory) == index
    envelope = json.loads((directory / 'melange-win32-x64-directory-zip.manifest.json').read_text())
    keys = store.config()['apps']['melange']['publicKeys']
    manifest = verify_envelope(envelope, keys, app='melange', platform='win32', arch='x64')
    assert manifest['minimumUpdaterVersion'] == '2.0.0'
    script = """const fs=require('node:fs'),v=JSON.parse(fs.readFileSync(0,'utf8'));
      require('./publisher-trust.cjs').THUMBPRINT=v.pin;
      const {verifyEnvelope}=require('./trust.cjs');
      const identity={appId:'melange',version:'0.9.0',platform:'win32',arch:'x64',distribution:'directory-zip'};
      const enrollment={source:'github',appId:'melange',repository:'pjg93-222/melange',publicKeys:v.keys};
      const m=verifyEnvelope(v.envelope,enrollment,identity).manifest;
      process.stdout.write(require('./directory-package-proof.cjs').publisherProofPayload(m));"""
    result = RUN(['node', '-e', script], cwd=CLIENT, input=json.dumps({'pin': proof.PINNED_THUMBPRINT, 'keys': keys, 'envelope': envelope}),
                 capture_output=True, text=True, check=True, timeout=30)
    assert result.stdout.encode() == proof.publisher_proof_payload(manifest)


@pytest.mark.parametrize('field,value', [('size', 77), ('sha256', 'a'*64), ('sha512', base64.b64encode(b'a'*64).decode()),
                                      ('entrypoint', 'Mentat.exe'), ('format', 'nsis'), ('name', 'other.zip')])
def test_publisher_proof_binds_every_archive_field(directory_inputs, field, value):
    _, _, _, manifest = directory_inputs
    assert proof.verify_directory_package_proof(manifest) == proof.PINNED_THUMBPRINT
    manifest['package'][field] = value
    with pytest.raises(Exception):
        proof.verify_directory_package_proof(manifest)


@pytest.mark.parametrize('mutation', ['missing-proof', 'wrong-signature', 'wrong-certificate', 'native-receipt', 'archive-bytes'])
def test_prepare_refuses_invalid_proof_or_wrong_exact_byte_gate(tmp_path, directory_inputs, mutation):
    store, spec, _, manifest = directory_inputs
    item = spec['packages']['melange']
    if mutation == 'missing-proof':
        del item['publisherProof']
    elif mutation in ('wrong-signature', 'wrong-certificate'):
        value = manifest['package']['publisherProof']
        value['signature' if mutation == 'wrong-signature' else 'certificateDer'] = base64.b64encode(b'forged').decode()
        Path(item['publisherProof']).write_text(json.dumps(value))
    elif mutation == 'native-receipt':
        receipt = json.loads(Path(item['receipt']).read_text())
        del receipt['osSignature']['format']
        Path(item['receipt']).write_text(json.dumps(receipt))
    else:
        with Path(item['package']).open('ab') as archive:
            archive.write(b'changed')
    with pytest.raises(Refused):
        release.prepare(store, spec, tmp_path / 'refused')
    assert store.signed == [] and not (tmp_path / 'refused').exists()


def test_directory_bundle_cannot_be_relabelled_for_native_discovery(tmp_path, directory_inputs):
    store, spec, _, _ = directory_inputs
    output = tmp_path / 'release'
    release.prepare(store, spec, output)
    index_path = output / 'melange' / 'release.json'
    index = json.loads(index_path.read_text())
    del index['packageFormat']
    index_path.write_text(json.dumps(index))
    with pytest.raises(Refused):
        release.verify_bundle(store, index_path.parent)


def test_custom_publisher_keeps_native_and_zip_discovery_and_recovery_separate(tmp_path, directory_inputs, monkeypatch):
    signer, spec, _, original = directory_inputs
    # Exercise Store.publish and selectors with in-memory test signing keys and
    # the minimum database rows, without creating or loading a real key store.
    store = Store(tmp_path / 'custom-publisher')
    store.root.mkdir()
    monkeypatch.setattr(store, 'config', signer.config)
    monkeypatch.setattr(store, 'sign', signer.sign)
    monkeypatch.setattr('desktop_admin.PUBLISHER_THUMBPRINTS', (proof.PINNED_THUMBPRINT,))
    with sqlite3.connect(store.db) as connection:
        connection.executescript('''
          CREATE TABLE devices (device_id TEXT, app TEXT, revoked INTEGER, platform TEXT, arch TEXT);
          CREATE TABLE releases (app TEXT, platform TEXT, arch TEXT, sequence INTEGER, version TEXT,
            envelope TEXT, package TEXT, recipients TEXT, withdrawn INTEGER);
          CREATE TABLE audit (time INTEGER, action TEXT, app TEXT, device_id TEXT, detail TEXT);
          INSERT INTO devices VALUES ('tester','melange',0,'win32','x64');
        ''')
        native = {**original, 'schemaVersion': 1, 'version': '0.9.9', 'sequence': 1,
                  'minimumUpdaterVersion': '1.0.0', 'dataSchemaVersion': 1,
                  'package': {key: value for key, value in original['package'].items()
                              if key not in ('format', 'entrypoint', 'publisherProof')}}
        native['package'].update(name='melange-0.9.9.exe', path='/v1/packages/melange/1/melange-0.9.9.exe')
        connection.execute('INSERT INTO releases VALUES (?,?,?,?,?,?,?,?,0)',
            ('melange', 'win32', 'x64', 1, '0.9.9', json.dumps(signer.sign('melange', native)), 'legacy.exe', '["tester"]'))
    item = spec['packages']['melange']
    receipt = json.loads(Path(item['receipt']).read_text())
    envelope = store.publish('melange', item['package'], receipt, '1.0.0', 2, 'win32', 'x64', ['tester'],
                             package_format=proof.FORMAT, publisher_proof=original['package']['publisherProof'])
    device = {'app': 'melange', 'device_id': 'tester', 'platform': 'win32', 'arch': 'x64'}
    assert store.latest(device, 'win32', 'x64')['version'] == '0.9.9'
    assert store.latest(device, 'win32', 'x64', proof.DISTRIBUTION)['version'] == '1.0.0'
    assert json.loads(store.recovery_seed(device, 'win32', 'x64', '1.0.0', proof.DISTRIBUTION)['envelope']) == envelope
    assert store.recovery_seed(device, 'win32', 'x64', '1.0.0') is None
    assert store.recovery_seed(device, 'win32', 'x64', '0.9.9', proof.DISTRIBUTION) is None
    assert store.latest({**device, 'device_id': 'unapproved'}, 'win32', 'x64', proof.DISTRIBUTION) is None
    with pytest.raises(Refused):
        store.latest(device, 'win32', 'x64', 'typo')
