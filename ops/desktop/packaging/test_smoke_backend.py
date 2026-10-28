"""The packaged-backend smoke launches each app the way the desktop client does."""
import json
from pathlib import Path
import re
from types import SimpleNamespace

import smoke_backend

CLIENT = Path(__file__).resolve().parents[1] / 'client'


def launch(app, tmp_path):
    options = SimpleNamespace(app=app, runtime=tmp_path / 'runtime', binary=None, source=tmp_path / 'runtime' / 'sources')
    return smoke_backend.launch(options, 4321, 't' * 43, tmp_path)


def test_terrier_gets_a_fresh_approved_administrator_for_the_clients_first_launch_district(tmp_path, monkeypatch):
    monkeypatch.setenv('DESKTOP_ACCESS_PRINCIPAL', 'stale')
    monkeypatch.setenv('CU_DISTRICT', 'or-05')
    command, environment = launch('terrier', tmp_path)
    default = re.search(r"configuration\.district\|\|'([a-z0-9-]+)'", (CLIENT / 'runtime-roots.cjs').read_text(encoding='utf-8'))
    assert command[-2:] == ['--district', default.group(1)] == ['--district', smoke_backend.TERRIER_DISTRICT]
    assert '--legacy-owner' not in command and '--owner-root' not in command
    assert 'CU_DISTRICT' not in environment and environment['DESKTOP_LAUNCH_TOKEN'] == 't' * 43
    principal = json.loads(environment['DESKTOP_ACCESS_PRINCIPAL'])
    assert list(principal) == ['schemaVersion', 'serverId', 'deviceId', 'principalId', 'accountIdentity',
                               'localAccountIdentity', 'localUserId', 'role', 'districtId', 'mode']
    assert principal['accountIdentity'] == principal['localAccountIdentity'] == 'recipient_' + principal['principalId'].replace('-', '')
    assert (principal['mode'], principal['role'], principal['localUserId'], principal['districtId']) == (
        'recipient', 'local_administrator', None, smoke_backend.TERRIER_DISTRICT)
    assert len({principal['serverId'], principal['deviceId'], principal['principalId']}) == 3
    assert json.loads(launch('terrier', tmp_path)[1]['DESKTOP_ACCESS_PRINCIPAL'])['principalId'] != principal['principalId']


def test_other_apps_get_no_principal_or_district(tmp_path):
    for app in ('melange', 'mentat'):
        command, environment = launch(app, tmp_path)
        assert '--district' not in command and 'DESKTOP_ACCESS_PRINCIPAL' not in environment


def test_packaged_python_smoke_does_not_write_bytecode_into_signed_tree(tmp_path):
    import subprocess
    import sys
    bootstrap = tmp_path / 'runtime' / 'bootstrap'
    bootstrap.mkdir(parents=True)
    (bootstrap / 'desktop_backend.py').write_text('import fixture_dependency\n')
    (bootstrap / 'fixture_dependency.py').write_text('value = 42\n')
    command, environment = launch('melange', tmp_path)
    command[0] = sys.executable  # execute only these temporary fixture modules
    subprocess.run(command, env=environment, check=True, capture_output=True)
    assert not list((tmp_path / 'runtime').rglob('__pycache__'))
