"""send_zip over a real prepared bundle (github_release.prepare + verify_bundle run for real); only the native Authenticode call is the shared test double."""
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import zipfile

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import github_release as release
import send_zip
from test_github_release import prepared_inputs  # noqa: F401  (pytest fixture: signer double, synthetic installers, Authenticode double)


@pytest.fixture
def bundle(tmp_path, prepared_inputs, monkeypatch):
    store, spec, verified = prepared_inputs
    output = tmp_path / 'public-assets'
    release.prepare(store, spec, output)
    monkeypatch.setattr(send_zip, 'Store', lambda _state: store)
    args = ['--app', 'mentat', '--state', str(store.root), '--out', str(tmp_path / 'send')]
    return output, args, tmp_path / 'send', verified


def test_denied_names():
    assert all(send_zip.denied(name) for name in ('x.sqlite3', 'a.sqlite', '.env', '.env.local', 'id.key', 'keys.json', 'ID.KEY'))
    assert not any(send_zip.denied(name) for name in ('melange-1.0.3-win32-x64.exe', 'README.txt'))


def test_tampered_installer_is_refused_and_nothing_is_written(bundle, capsys):
    output, args, out, _ = bundle
    installer = output / 'mentat' / 'mentat-1.0.0-win32-x64.exe'
    data = bytearray(installer.read_bytes())
    data[0] ^= 1
    installer.write_bytes(data)
    assert send_zip.main(args + ['--bundle', str(output / 'mentat')]) == 1
    assert 'Send zip refused' in capsys.readouterr().err
    assert not out.exists()


def test_planted_database_is_refused_by_the_deny_check(bundle, capsys):
    output, args, out, _ = bundle
    (output / 'mentat' / 'x.sqlite3').write_bytes(b'')
    assert send_zip.main(args + ['--bundle', str(output / 'mentat')]) == 1
    err = capsys.readouterr().err
    assert 'x.sqlite3' in err and 'must never be sent' in err
    assert not out.exists()


@pytest.mark.parametrize('signature', [{'Status': 'NotSigned', 'Subject': None}, {'Status': 'Valid', 'Subject': 'CN=Someone else'}])
def test_unsigned_or_wrong_publisher_installer_is_refused(bundle, monkeypatch, capsys, signature):
    output, args, out, _ = bundle
    monkeypatch.setattr(send_zip.subprocess, 'run', lambda *_args, **_kwargs: SimpleNamespace(stdout=json.dumps(signature)))
    assert send_zip.main(args + ['--bundle', str(output)]) == 1
    assert 'Send zip refused' in capsys.readouterr().err
    assert not out.exists() or not any(out.iterdir())


def test_installer_swapped_after_verification_is_refused(bundle, monkeypatch, capsys):
    output, args, out, _ = bundle
    installer = output / 'mentat' / 'mentat-1.0.0-win32-x64.exe'

    def swap_then_pass(*_args):  # runs after verify_bundle and before the zip is written
        data = bytearray(installer.read_bytes())
        data[0] ^= 1
        installer.write_bytes(data)
        return 'Valid'

    monkeypatch.setattr(send_zip, 'authenticode', swap_then_pass)
    assert send_zip.main(args + ['--bundle', str(output)]) == 1
    assert 'differs from the signed release' in capsys.readouterr().err
    assert not out.exists() or not any(out.iterdir())


def test_checksum_write_failure_leaves_no_zip_behind(bundle, monkeypatch, capsys):
    output, args, out, _ = bundle
    original = Path.write_bytes

    def write_bytes(self, data):
        if self.name.endswith('.sha256'):
            raise OSError('disk full')
        return original(self, data)

    monkeypatch.setattr(Path, 'write_bytes', write_bytes)
    assert send_zip.main(args + ['--bundle', str(output)]) == 1
    assert 'disk full' in capsys.readouterr().err
    assert not out.exists() or not any(out.iterdir())  # no zip, no .sha256, no .send-zip-*.tmp


def test_unpinned_publisher_is_refused(bundle, monkeypatch, capsys):
    output, args, out, _ = bundle
    store = send_zip.Store(None)
    config = {key: value for key, value in store.config().items() if key != 'windowsPublisher'}
    monkeypatch.setattr(store, 'config', lambda: config)
    assert send_zip.main(args + ['--bundle', str(output)]) == 1
    assert 'no Windows publisher is pinned' in capsys.readouterr().err
    assert not out.exists() or not any(out.iterdir())


def test_good_bundle_makes_the_three_member_zip_and_its_checksum(bundle, capsys):
    output, args, out, verified = bundle
    assert send_zip.main(args + ['--bundle', str(output)]) == 0  # the prepare output root, not the per-app directory
    summary = json.loads(capsys.readouterr().out)
    zip_path = out / 'Mentat-1.0.0-windows.zip'
    assert verified[-1] == str(output / 'mentat' / 'mentat-1.0.0-win32-x64.exe')
    assert summary['zip'] == str(zip_path) and summary['authenticode'] == 'Valid' and summary['app'] == 'mentat'
    setup = (output / 'mentat' / 'mentat-1.0.0-win32-x64.exe').read_bytes()
    with zipfile.ZipFile(zip_path) as archive:
        assert sorted(archive.namelist()) == ['Mentat-1.0.0-Setup.exe', 'README.txt', 'SHA256SUMS']
        assert archive.read('Mentat-1.0.0-Setup.exe') == setup
        listed = {}
        for line in archive.read('SHA256SUMS').decode('ascii').splitlines():
            digest, name = line.split('  ')
            listed[name] = digest
            assert hashlib.sha256(archive.read(name)).hexdigest() == digest
        assert sorted(listed) == ['Mentat-1.0.0-Setup.exe', 'README.txt']
        readme = archive.read('README.txt')
    assert hashlib.sha256(setup).hexdigest().upper().encode() in readme and summary['setupSha256'] == hashlib.sha256(setup).hexdigest()
    assert b'\n' not in readme.replace(b'\r\n', b'')
    assert readme.index(hashlib.sha256(setup).hexdigest().upper().encode()) < readme.index(b'Run anyway')  # hash check comes first
    assert (out / 'Mentat-1.0.0-windows.zip.sha256').read_text() == f'{hashlib.sha256(zip_path.read_bytes()).hexdigest()}  {zip_path.name}\n'
    assert sorted(path.name for path in out.iterdir()) == ['Mentat-1.0.0-windows.zip', 'Mentat-1.0.0-windows.zip.sha256']
    assert send_zip.main(args + ['--bundle', str(output)]) == 1  # an existing zip is never replaced
    assert 'already exists' in capsys.readouterr().err
