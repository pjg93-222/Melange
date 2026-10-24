"""release_from_main.py against real temporary git repositories; every other tool is a fake behind the injected runner."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tomllib
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import release_from_main as rfm
import desktop_admin  # on sys.path once release_from_main is imported
from github_release import validate_spec

# Tests never sign commits or tags (this machine signs commits globally).
GIT = ['git', '-c', 'user.name=t', '-c', 'user.email=t@t', '-c', 'commit.gpgsign=false', '-c', 'tag.gpgsign=false']
NAMES = {'melange': 'Melange', 'mentat': 'Mentat', 'terrier': 'Geo'}
PUBLISHER = rfm.SUBJECT  # the only subject the signing hook signs as
VERSION = '1.2.3'
LOCK = 'pkg==1.0 --hash=sha256:' + '0' * 64 + '\n'
HOOK = "'use strict';\n"
ORIGINAL_EXCEPTIONS = '# the private exceptions\n[[exception]]\nid = "EX-001"\n'
TERRIER_EXCEPTIONS = '[[exception]]\nid = "TERRIER-001"\n'
LOCKS = {'melange': 'src/melange/ops/desktop/packaging/melange-runtime.constraints.txt',
         'mentat': 'src/mentat/ops/desktop/packaging/mentat-runtime.constraints.txt', 'terrier': 'src/melange/ops/desktop/packaging/terrier-runtime.constraints.txt'}


def git(cwd, *args):
    return subprocess.run([*GIT, *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def commit(checkout, relative, text, message='change'):
    path = Path(checkout) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    git(checkout, 'add', relative)
    git(checkout, 'commit', '-q', '-m', message)


def tool(call):
    return Path(call[0]).name.lower()


class Fake:
    """Records every command and its cwd. git runs for real; npm (with the signing hook), python tools, PowerShell and gh
    are scripted."""

    def __init__(self):
        self.calls, self.cwds = [], []
        self.signed = set()
        self.builds = []  # environment of each `npm run build`
        self.policy = 'RemoteSigned'  # effective execution policy Get-ExecutionPolicy reports
        self.hook = True  # the build's signing hook signs the installer
        self.hook_receipt = True  # and writes <installer>.signatures.json
        self.existing = set()  # repositories whose desktop release already exists
        self.fail = lambda cmd: False  # gh commands to fail
        self.tamper = None  # app whose prepared release.json gets another sequence
        self.view_error = None  # stderr of a failing `gh release view` that is not "release not found"
        self.gates = []  # (security_gate.py command, text of its --exceptions file or None)
        self.npm_fail = lambda cmd, cwd: False  # npm commands to fail
        self.tips = {}  # repository -> main sha `gh api repos/R/commits/main` answers; `release` fills in origin's own

    def __call__(self, cmd, cwd=None, env=None):
        self.calls.append(list(cmd))
        self.cwds.append(cwd)
        name = tool(cmd)
        if name in ('git', 'git.exe'):
            return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
        if 'Get-ExecutionPolicy' in cmd:
            assert cmd == [rfm.POWERSHELL, '-NoProfile', '-NonInteractive', '-Command', 'Get-ExecutionPolicy'], cmd
            return rfm.Ran(0, self.policy + '\r\n', '')
        if name == 'npm':
            if self.npm_fail(cmd, cwd):
                return rfm.Ran(1, '', 'scripted npm failure')
            if cmd[1:3] == ['run', 'build'] and env and 'DESKTOP_APP_ID' in env:
                self.build(cwd, env)
            return rfm.Ran(0, 'ok', '')
        if name == 'powershell.exe':
            path = env['DESKTOP_VERIFY_PACKAGE']
            signed = path in self.signed
            return rfm.Ran(0, json.dumps({'Status': 'Valid' if signed else 'NotSigned', 'Subject': PUBLISHER if signed else '',
                                          'Thumbprint': rfm.THUMBPRINT if signed else '', 'Timestamped': signed}), '')
        if name.startswith('python'):  # sys.executable or a build venv
            return self.python(cmd)
        if name == 'gh':
            return self.gh(cmd)
        raise AssertionError(f'unexpected command {cmd}')

    def build(self, cwd, env):
        """electron-builder with release-signing.cjs: the environment its options() requires, then a signed installer."""
        self.builds.append(env)
        root, dist = Path(env['DESKTOP_SIGNING_ROOT']), Path(env['DESKTOP_DIST_ROOT'])
        assert env['DESKTOP_SIGNING_CERT_SHA1'] == rfm.THUMBPRINT and env['WINDOWS_PUBLISHER_NAME'] == rfm.SUBJECT
        assert root.is_absolute() and root.is_dir() and dist.parent == root
        assert not (root / 'nsis').exists() and not (root / 'nsis-resources').exists()  # one fresh package per root
        assert not {'CSC_LINK', 'WIN_CSC_LINK', 'CSC_KEY_PASSWORD', 'WIN_CSC_KEY_PASSWORD'} & set(env)
        assert env.get('ELECTRON_BUILDER_OFFLINE') != 'true'
        (root / 'nsis').mkdir()
        version = json.loads((Path(cwd) / 'package.json').read_text(encoding='utf-8'))['version']
        app = env['DESKTOP_APP_ID']
        installer = dist / app / f'{rfm.PRODUCTS[app]}-{version}-win-x64.exe'
        installer.parent.mkdir(parents=True, exist_ok=True)
        installer.write_bytes(b'MZ synthetic ' + app.encode() + (b'\0signature' if self.hook else b''))
        if not self.hook:
            return
        self.signed.add(str(installer))
        if self.hook_receipt:
            row = {'path': str(installer), 'sha256': hashlib.sha256(installer.read_bytes()).hexdigest(), 'status': 'Valid',
                   'thumbprint': rfm.THUMBPRINT, 'timestamped': True}
            (installer.parent / (installer.name + '.signatures.json')).write_text(json.dumps(
                {'schemaVersion': 1, 'appId': app, 'certificateThumbprint': rfm.THUMBPRINT, 'installer': str(installer),
                 'files': [row], 'currentFiles': [row], 'uninstallerEvidence': 'staged-history-only'}), encoding='utf-8')

    def gh(self, cmd):
        if self.fail(cmd):
            return rfm.Ran(1, '', 'scripted failure')
        if cmd[1:3] == ['release', 'view']:
            repo = cmd[cmd.index('--repo') + 1]
            if self.view_error:
                return rfm.Ran(1, '', self.view_error)
            return rfm.Ran(0, '{}', '') if repo in self.existing else rfm.Ran(1, '', 'release not found')
        if cmd[1:3] == ['repo', 'view']:
            return rfm.Ran(0, 'PUBLIC\n', '')
        if cmd[1] == 'api' and cmd[2].endswith('/commits/main'):
            return rfm.Ran(0, self.tips[cmd[2][len('repos/'):-len('/commits/main')]] + '\n', '')
        if cmd[1] == 'api':
            return rfm.Ran(0, cmd[2].rsplit('/', 1)[1] + '\n', '')
        if cmd[1:3] == ['release', 'upload']:
            self.uploaded = [Path(part) for part in cmd[4:cmd.index('--repo')]]
        if cmd[1:3] == ['release', 'download']:
            for path in self.uploaded:
                shutil.copyfile(path, Path(cmd[cmd.index('--dir') + 1]) / path.name)
        return rfm.Ran(0, '', '')

    def python(self, cmd):
        arg = lambda name: cmd[cmd.index(name) + 1]
        script = next((Path(part).name for part in cmd if part.endswith('.py')), None)
        if script is None and '-m' in cmd:
            module = arg('-m')
            if module == 'venv':
                (Path(cmd[-1]) / 'Scripts').mkdir(parents=True)
                (Path(cmd[-1]) / 'pyvenv.cfg').write_text('include-system-site-packages = false\n', encoding='utf-8')
            if module == 'pip' and 'freeze' in cmd:
                return rfm.Ran(0, 'pkg==1.0\n', '')
            assert module in ('venv', 'pip', 'pytest'), cmd
        elif script == 'build_runtime.py':
            app = arg('--app')
            if '--stage-only' in cmd:
                inventory = Path(arg('--build-root')) / app / 'stagehash' / 'source-inventory.json'
                (inventory.parent / 'sources' / 'ops').mkdir(parents=True)
                (inventory.parent / 'sources' / 'ops' / 'app.py').write_text('', encoding='utf-8')
                inventory.write_text(json.dumps(['ops/app.py']), encoding='utf-8')
            elif '--sync-sources-only' in cmd:  # the injected runtime is already in place
                assert (Path(arg('--runtime-root')) / app / 'python' / 'python.exe').is_file()
            else:
                runtime = Path(arg('--runtime-root')) / app
                runtime.mkdir(parents=True)
                (runtime / 'runtime-status.json').write_text(json.dumps({'appId': app, 'missingNativeRuntimes': []}), encoding='utf-8')
                (runtime / 'dependency-inventory.json').write_text(json.dumps([{'name': 'pkg', 'license': 'MIT'}]), encoding='utf-8')
        elif script == 'github_release.py' and '--spec' in cmd:
            spec = json.loads(Path(arg('--spec')).read_text(encoding='utf-8'))
            for app in spec['packages']:
                bundle = Path(arg('--output')) / app
                bundle.mkdir(parents=True)
                installer = f'{app}-{spec["version"]}-win32-x64.exe'
                (bundle / installer).write_bytes(Path(spec['packages'][app]['package']).read_bytes())
                for name in (f'{app}-win32-x64.manifest.json', f'{app}-trust.json', 'turn-on-updates.cmd'):
                    (bundle / name).write_text('{}', encoding='utf-8')
                sequence = spec['sequence'] + (app == self.tamper)
                (bundle / 'release.json').write_text(json.dumps({'appId': app, 'version': spec['version'], 'sequence': sequence,
                                                                 'sourceRefs': spec['sourceRefs']}), encoding='utf-8')
                (bundle / 'SHA256SUMS').write_text(''.join(hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + path.name + '\n'
                                                           for path in sorted(bundle.iterdir())), encoding='ascii')
        elif script == 'security_gate.py':
            assert cmd[1] == '-B', cmd  # never writes bytecode into the private tree
            self.gates.append((cmd, Path(arg('--exceptions')).read_text(encoding='utf-8') if '--exceptions' in cmd else None))
            Path(arg('--report')).write_text(json.dumps({'stage': 'export', 'result': 'PASS', 'checks': []}), encoding='utf-8')
        elif script not in ('smoke_backend.py', 'github_release.py'):
            raise AssertionError(f'unexpected python command {cmd}')
        return rfm.Ran(0, '', '')


class Shell:
    """desktop_admin's own Get-AuthenticodeSignature run (the 'check' step), answered from the bytes the fake hook appended."""

    def __init__(self):
        self.checked = []

    def run(self, cmd, env=None, **_):
        path = Path(env['DESKTOP_VERIFY_PACKAGE'])
        self.checked.append(path)
        signed = path.read_bytes().endswith(b'\0signature')
        return SimpleNamespace(stdout=json.dumps({'Status': 'Valid' if signed else 'NotSigned', 'Subject': PUBLISHER if signed else None}))


@pytest.fixture(scope='module')
def template(tmp_path_factory):
    """Bare origins at pjg93-222/<Name>.git with main, and checkouts cloned from them. Built once: git is slow on Windows."""
    root = tmp_path_factory.mktemp('template')
    package = json.dumps({'name': 'client', 'version': VERSION})
    files = {'melange': {'ops/desktop/client/package.json': package, 'ops/desktop/packaging/melange-runtime.constraints.txt': LOCK,
                         'ops/desktop/packaging/terrier-runtime.constraints.txt': LOCK, rfm.SIGNING_HOOK: HOOK,
                         'ops/desktop/packaging/terrier-security-exceptions.toml': TERRIER_EXCEPTIONS,
                         'ops/desktop/packaging/runtime-manifest.json': json.dumps({'apps': {'terrier': {
                             'requirements': 'requirements.txt', 'sourceDirectories': ['server', 'frontend/dist']}}})},
             'mentat': {'README.md': 'Mentat', 'ops/desktop/client/package.json': package,
                        'ops/desktop/packaging/mentat-runtime.constraints.txt': LOCK, rfm.SIGNING_HOOK: HOOK},
             'terrier': {'README.md': 'Geo', 'requirements.build.lock': LOCK, 'requirements.txt': 'Django>=5.2,<5.3\n',
                         'frontend/package.json': '{"name": "terrier"}'}}  # Geo's Linux lock: present, hash-locked, and must never be used
    for app, name in NAMES.items():
        origin = root / 'pjg93-222' / f'{name}.git'
        subprocess.run([*GIT, 'init', '-q', '--bare', '-b', 'main', str(origin)], check=True)
        checkout = root / 'checkouts' / app
        subprocess.run([*GIT, 'clone', '-q', str(origin), str(checkout)], check=True, capture_output=True)
        # A relative origin (resolved from the checkout) keeps the template self-contained; `world` repoints it at GitHub.
        git(checkout, 'remote', 'set-url', 'origin', f'../../pjg93-222/{name}.git')
        git(checkout, 'symbolic-ref', 'HEAD', 'refs/heads/main')
        for relative, text in files[app].items():
            (checkout / relative).parent.mkdir(parents=True, exist_ok=True)
            (checkout / relative).write_text(text, encoding='utf-8')
        git(checkout, 'add', '.')
        git(checkout, 'commit', '-q', '-m', 'initial')
        git(checkout, 'push', '-q', 'origin', 'main')
    return root


@pytest.fixture
def world(template, tmp_path, monkeypatch):
    """A private copy of the repositories, plus a synthetic build venv and publisher state (never the real one)."""
    for name in ('DESKTOP_MELANGE_SOURCE', 'DESKTOP_MENTAT_SOURCE', 'DESKTOP_GEO_SOURCE', 'DESKTOP_BUILD_PYTHON'):
        monkeypatch.delenv(name, raising=False)
    shell = Shell()
    monkeypatch.setattr(desktop_admin, 'subprocess', shell)
    shutil.copytree(template, tmp_path, dirs_exist_ok=True)
    paths = {app: tmp_path / 'checkouts' / app for app in NAMES}
    for app, name in NAMES.items():
        git(paths[app], 'remote', 'set-url', 'origin', f'https://github.com/pjg93-222/{name}.git')
        # git reaches the local bare repository for every fetch, ls-remote and push of that GitHub URL.
        git(paths[app], 'config', f'url.{tmp_path.as_posix()}/.insteadOf', 'https://github.com/')
    venv = tmp_path / 'venv'
    (venv / 'Scripts').mkdir(parents=True)
    (venv / 'pyvenv.cfg').write_text('include-system-site-packages = false\n', encoding='utf-8')
    state = tmp_path / 'state'
    state.mkdir()
    (state / 'trust.json').write_text(json.dumps({'windowsPublisher': PUBLISHER}), encoding='utf-8')
    ledger = sqlite3.connect(state / 'github-prepared.sqlite3')
    ledger.execute('CREATE TABLE prepared (repository TEXT, app TEXT, platform TEXT, arch TEXT, sequence INTEGER, version TEXT, envelope TEXT)')
    ledger.execute("INSERT INTO prepared VALUES ('pjg93-222/melange','melange','win32','x64',7,'1.0.14','{}')")
    ledger.commit()
    ledger.close()
    security = tmp_path / 'private'  # stands in for the owner's private checkout
    (security / 'ops' / 'security').mkdir(parents=True)
    (security / 'ops' / 'security_gate.py').write_text('# private gate\n', encoding='utf-8')
    (security / 'ops' / 'security' / 'canaries.txt').write_text('canary-token\n', encoding='utf-8')
    (security / 'ops' / 'security' / 'exceptions.toml').write_text(ORIGINAL_EXCEPTIONS, encoding='utf-8')
    return {'tmp': tmp_path, 'paths': paths, 'state': state, 'out': tmp_path / 'out', 'python': venv / 'Scripts' / 'python.exe',
            'shell': shell, 'security': security}


def release(world, *extra, fake=None, environ=None, build_python=True, sources=True):
    fake = fake or Fake()
    for app in NAMES:
        fake.tips.setdefault(rfm.REPOSITORIES[app], origin_main(world, app))
    argv = ['--state', str(world['state']), '--output-root', str(world['out']), '--security-root', str(world['security']), *extra]
    if sources:
        argv += ['--melange', str(world['paths']['melange']), '--mentat', str(world['paths']['mentat']),
                 '--geo', str(world['paths']['terrier'])]
    if build_python:
        argv += ['--build-python', str(world['python'])]
    return rfm.main(argv, runner=fake, environ={} if environ is None else environ, os_name='nt'), fake


def origin_main(world, app):
    return git(world['tmp'] / 'pjg93-222' / f'{NAMES[app]}.git', 'rev-parse', 'refs/heads/main')


def push(world, app, relative, text):
    commit(world['paths'][app], relative, text)
    git(world['paths'][app], 'push', '-q', 'origin', 'main')


def test_dirty_checkout_is_refused_at_sources(world, capsys):
    (world['paths']['mentat'] / 'README.md').write_text('edited', encoding='utf-8')
    code, _ = release(world)
    error = capsys.readouterr().err
    assert code == 1
    assert "Release stopped at step 'sources'" in error and 'pjg93-222/Mentat' in error and 'modified' in error


def test_untracked_files_are_ignored(world, capsys):
    (world['paths']['mentat'] / 'scratch.txt').write_text('untracked', encoding='utf-8')
    code, _ = release(world)
    assert code == 0, capsys.readouterr().err


def test_head_not_at_origin_main_is_refused_at_sources(world, capsys):
    commit(world['paths']['terrier'], 'local.txt', 'unpushed')
    code, _ = release(world)
    error = capsys.readouterr().err
    assert code == 1
    assert "Release stopped at step 'sources'" in error and 'pjg93-222/Geo' in error and 'origin/main' in error


@pytest.mark.parametrize('url', ['https://github.com/someone/pjg93-222-Mentat.git', 'https://gitlab.com/pjg93-222/Mentat.git',
                                 'https://github.com.evil.example/pjg93-222/Mentat.git', 'file:///x/pjg93-222/Mentat.git'])
def test_wrong_origin_is_refused_at_sources(world, capsys, url):
    git(world['paths']['mentat'], 'remote', 'set-url', 'origin', url)
    code, _ = release(world)
    error = capsys.readouterr().err
    assert code == 1 and "step 'sources'" in error and 'not pjg93-222/Mentat' in error


def test_missing_given_checkout_is_refused_not_cloned(world, capsys):
    world['paths']['mentat'] = world['tmp'] / 'missing' / 'Mentat'
    code, fake = release(world)
    error = capsys.readouterr().err
    assert code == 1 and "step 'sources'" in error and 'pjg93-222/Mentat' in error and 'checkout not found' in error
    assert not any('clone' in call for call in fake.calls)


def test_default_checkouts_are_cloned_then_released(world, capsys, monkeypatch):
    monkeypatch.setattr(rfm, 'SOURCES', world['tmp'] / 'sources')
    # git (here, not the checkouts' own config) maps the GitHub URL to the local bare repositories: no network.
    monkeypatch.setenv('GIT_CONFIG_COUNT', '1')
    monkeypatch.setenv('GIT_CONFIG_KEY_0', f'url.{world["tmp"].as_posix()}/.insteadOf')
    monkeypatch.setenv('GIT_CONFIG_VALUE_0', 'https://github.com/')
    code, fake = release(world, sources=False)
    assert code == 0, capsys.readouterr().err
    clones = [call for call in fake.calls if call[:2] == ['git', 'clone']]
    assert [call[2:] for call in clones] == [[f'https://github.com/{rfm.REPOSITORIES[app]}.git', str(world['tmp'] / 'sources' / NAMES[app])]
                                             for app in rfm.APPS]
    spec = json.loads((world['out'] / f'release-spec-{VERSION}.json').read_text(encoding='utf-8'))
    assert all(spec['sourceRefs'][app]['commit'] == origin_main(world, app) for app in rfm.APPS)
    # A second run finds the clones and does not clone again.
    shutil.rmtree(world['out'])
    code, fake = release(world, sources=False)
    assert code == 0, capsys.readouterr().err
    assert not any(call[:2] == ['git', 'clone'] for call in fake.calls)


def test_existing_release_tag_is_refused_at_version(world, capsys):
    checkout = world['paths']['mentat']
    git(checkout, 'tag', 'desktop-v' + VERSION)
    git(checkout, 'push', '-q', 'origin', 'desktop-v' + VERSION)
    git(checkout, 'tag', '-d', 'desktop-v' + VERSION)
    code, _ = release(world)
    error = capsys.readouterr().err
    assert code == 1
    assert "Release stopped at step 'version'" in error and 'desktop-v1.2.3' in error and 'pjg93-222/Mentat' in error


def test_version_must_equal_package_json(world, capsys):
    code, fake = release(world, '--version', '1.2.4')
    error = capsys.readouterr().err
    assert code == 1 and "step 'version'" in error and 'bump the version on main first' in error
    assert not any(tool(call) == 'npm' for call in fake.calls)


def test_client_versions_must_match_across_melange_and_mentat(world, capsys):
    push(world, 'mentat', 'ops/desktop/client/package.json', json.dumps({'name': 'client', 'version': '1.2.4'}))
    code, fake = release(world)
    error = capsys.readouterr().err
    assert code == 1 and "step 'version'" in error
    assert 'pjg93-222/Melange ops/desktop/client/package.json 1.2.3' in error and 'pjg93-222/Mentat ops/desktop/client/package.json 1.2.4' in error
    assert not any(tool(call) == 'npm' for call in fake.calls)


def test_build_python_must_be_a_venv(world, capsys):
    (world['python'].parent.parent / 'pyvenv.cfg').unlink()
    code, fake = release(world)
    assert code == 1 and "step 'local'" in capsys.readouterr().err and fake.calls == []


def test_ci_is_refused_at_local(world, capsys):
    code, fake = release(world, environ={'GITHUB_ACTIONS': 'true'})
    assert code == 1 and "step 'local'" in capsys.readouterr().err and fake.calls == []


def test_dry_run_completes_without_github_writes_or_ledger(world, capsys):
    code, fake = release(world, '--version', VERSION)
    out, error = capsys.readouterr()
    assert code == 0, error
    assert 'no GitHub writes were made and no release sequence was reserved' in out
    summary = json.loads(out[:out.rindex('}') + 1])
    assert summary['published'] is False and summary['version'] == VERSION and summary['sequence'] == 8
    receipts = world['out'] / f'receipts-{VERSION}'
    assert [(item['app'], item['name'], item['sha256']) for item in summary['artifacts']] == [
        (app, f'{rfm.PRODUCTS[app]}-{VERSION}-win-x64.exe', json.loads((receipts / f'{app}.json').read_text(encoding='utf-8'))['sha256'])
        for app in rfm.APPS]
    assert all(status == 'passed' for gates in summary['gates'].values() for status in gates.values())
    for call in fake.calls:
        assert tool(call) != 'gh', call  # a dry run makes no GitHub call at all
        assert not any(part.endswith('github_release.py') for part in call), call  # prepare would reserve a sequence
        if tool(call) in ('git', 'git.exe'):
            assert 'push' not in call and 'tag' not in call, call
    ledger = sqlite3.connect(world['state'] / 'github-prepared.sqlite3')
    assert ledger.execute('SELECT COUNT(*) FROM prepared').fetchone()[0] == 1
    ledger.close()
    assert (world['out'] / f'release-spec-{VERSION}.json').is_file() and not (world['out'] / f'release-{VERSION}' / 'bundle').exists()
    # The check step ran desktop_admin's own gate verification on each signed installer.
    assert sorted(path.name for path in world['shell'].checked) == sorted(f'{rfm.PRODUCTS[app]}-{VERSION}-win-x64.exe' for app in rfm.APPS)
    runtime = [call for call in fake.calls if any(part.endswith('build_runtime.py') for part in call)]
    assert len(runtime) == 6 and all(call[0] == str(world['python']) for call in runtime)
    assert not any('signtool' in part for call in fake.calls for part in call)  # the build's hook signs, nothing else
    powershell = [call[0] for call in fake.calls if tool(call) == 'powershell.exe']
    assert len(powershell) == 4 and set(powershell) == {rfm.POWERSHELL}  # policy query and each signature check: never via PATH
    assert [env['DESKTOP_SIGNING_ROOT'] for env in fake.builds] == [str(world['out'] / f'release-{VERSION}' / 'signing' / app)
                                                                    for app in rfm.APPS]
    for app in rfm.APPS:
        evidence = json.loads((receipts / f'{app}.json').read_text(encoding='utf-8'))['osSignature']['evidence']
        assert '.signatures.json sha256 ' in evidence and rfm.THUMBPRINT in evidence and rfm.SIGNING_HOOK in evidence
    for app in rfm.APPS:
        assert git(world['paths'][app], 'tag', '--list') == ''


def test_each_app_is_built_with_its_own_repositorys_client(world, capsys):
    code, fake = release(world)
    assert code == 0, capsys.readouterr().err
    src = world['out'] / f'release-{VERSION}' / 'src'
    client = lambda repo: str(src / repo / 'ops' / 'desktop' / 'client')
    npm = [(call[1:3], cwd) for call, cwd in zip(fake.calls, fake.cwds) if tool(call) == 'npm']
    for repo in ('melange', 'mentat'):  # tested and audited once per client repository
        assert [verbs for verbs, cwd in npm if cwd == client(repo) and verbs != ['run', 'build']] == [['ci', '--no-fund'], ['test'], ['audit', '--omit=dev']]
        assert [cwd for call, cwd in zip(fake.calls, fake.cwds) if 'pytest' in call].count(str(src / repo)) == 1
    builds = [cwd for call, cwd in zip(fake.calls, fake.cwds) if call[1:3] == ['run', 'build'] and cwd != str(src / 'terrier' / 'frontend')]
    assert builds == [client('melange'), client('mentat'), client('melange')]  # melange, mentat, terrier
    for app, repo in rfm.TOOLS.items():
        runtime = [call for call in fake.calls if any(part.endswith('build_runtime.py') for part in call) and call[call.index('--app') + 1] == app]
        assert len(runtime) == 2 and all(Path(call[1]).parents[3] == src / repo for call in runtime)
        assert all(call[call.index('--source') + 1] == str(src / app) for call in runtime)
    for app, repo in rfm.TOOLS.items():  # each installer is signed by its own client repository's hook
        evidence = json.loads((world['out'] / f'receipts-{VERSION}' / f'{app}.json').read_text(encoding='utf-8'))['osSignature']['evidence']
        assert f'{rfm.REPOSITORIES[repo]}@{origin_main(world, repo)}' in evidence
    # The private checkout's gate scans each app's staged (shipped) sources.
    security = [call for call in fake.calls if any(part.endswith('security_gate.py') for part in call)]
    assert [call[call.index('--target') + 1] for call in security] == [
        str(world['out'] / f'release-{VERSION}' / 'stage' / app / 'stagehash' / 'sources') for app in rfm.APPS]
    receipt = json.loads((world['out'] / f'receipts-{VERSION}' / 'mentat.json').read_text(encoding='utf-8'))
    assert receipt['clientCommit'] == origin_main(world, 'mentat')


def test_build_venvs_are_created_from_hash_locked_files(world, capsys):
    code, fake = release(world, build_python=False)
    assert code == 0, capsys.readouterr().err
    release_dir = world['out'] / f'release-{VERSION}'
    frozen = hashlib.sha256(b'pkg==1.0\n').hexdigest()
    for app in rfm.APPS:
        python = str(release_dir / 'venv' / app / 'Scripts' / 'python.exe')
        assert [sys.executable, '-I', '-m', 'venv', str(release_dir / 'venv' / app)] in fake.calls
        assert [python, '-m', 'pip', 'install', '--disable-pip-version-check', '--no-input', '--require-hashes', '--only-binary=:all:',
                '--no-deps', '-r', str(release_dir / LOCKS[app])] in fake.calls
        assert [python, '-m', 'pip', 'check'] in fake.calls
        runtime = [call for call in fake.calls if any(part.endswith('build_runtime.py') for part in call) and call[call.index('--app') + 1] == app]
        assert len(runtime) == 2 and all(call[0] == python for call in runtime)
        receipt = json.loads((world['out'] / f'receipts-{VERSION}' / f'{app}.json').read_text(encoding='utf-8'))
        assert f'build venv {python} pip freeze --all sha256 {frozen}' in receipt['gates']['tests']['evidence']


def test_app_without_a_hash_locked_file_is_refused_at_venv(world, capsys):
    melange = world['paths']['melange']  # Geo keeps its hash-locked requirements.build.lock; Melange loses the Terrier Windows lock
    git(melange, 'rm', '-q', 'ops/desktop/packaging/terrier-runtime.constraints.txt')
    git(melange, 'commit', '-q', '-m', 'drop terrier lock')
    git(melange, 'push', '-q', 'origin', 'main')
    code, fake = release(world, build_python=False)
    error = capsys.readouterr().err
    assert code == 1 and "step 'venv'" in error and 'terrier' in error and 'terrier-runtime.constraints.txt' in error
    assert 'requirements.build.lock' not in error and '--build-python' in error
    assert not any('venv' in call for call in fake.calls)  # refused before any venv is made


def test_release_spec_and_receipts_bind_origin_main(world, capsys):
    code, _ = release(world)
    assert code == 0, capsys.readouterr().err
    expected = {app: {'repository': rfm.REPOSITORIES[app], 'ref': 'main', 'commit': origin_main(world, app)} for app in rfm.APPS}
    spec = json.loads((world['out'] / f'release-spec-{VERSION}.json').read_text(encoding='utf-8'))
    validate_spec(spec)
    assert spec['sourceRefs'] == expected and spec['sequence'] == 8 and set(spec['packages']) == set(rfm.APPS)
    for app in rfm.APPS:
        receipt = json.loads(Path(spec['packages'][app]['receipt']).read_text(encoding='utf-8'))
        assert receipt['source'] == expected[app] and receipt['clientCommit'] == expected[rfm.TOOLS[app]]['commit']
        assert receipt['sha256'] == hashlib.sha256(Path(spec['packages'][app]['package']).read_bytes()).hexdigest()
        assert set(receipt['gates']) == set(rfm.GATES) and receipt['osSignature']['status'] == 'passed'
        assert receipt['nativeAcceptance']['status'] == 'passed'
    # A second dry run of the same version refuses instead of overwriting.
    code, _ = release(world)
    assert code == 1 and "step 'export'" in capsys.readouterr().err


def test_publish_after_dry_run_prepares_and_publishes_its_installers(world, capsys):
    assert release(world)[0] == 0, capsys.readouterr().err
    capsys.readouterr()
    code, fake = release(world, '--publish')
    out, error = capsys.readouterr()
    assert code == 0, error
    assert json.loads(out[:out.rindex('}') + 1])['published'] is True
    tools = [tool(call) for call in fake.calls]
    assert 'npm' not in tools  # nothing rebuilt or re-signed; PowerShell only answers the execution-policy preflight
    assert [call for call in fake.calls if tool(call) == 'powershell.exe'] == [
        [rfm.POWERSHELL, '-NoProfile', '-NonInteractive', '-Command', 'Get-ExecutionPolicy']]
    assert not any(part.endswith('build_runtime.py') or part == 'venv' for call in fake.calls for part in call)
    assert all('push' not in call and 'tag' not in call for call in fake.calls)
    prepare = [i for i, call in enumerate(fake.calls) if '--spec' in call]
    assert len(prepare) == 1 and prepare[0] < tools.index('gh')
    gh = lambda *verbs: [i for i, call in enumerate(fake.calls) if tool(call) == 'gh' and call[1:3] == list(verbs)]
    # Every draft is created, uploaded and verified before any release is made public.
    assert len(gh('release', 'edit')) == 3 and max(gh('release', 'download')) < min(gh('release', 'edit'))
    for app in rfm.APPS:
        repo, sha = rfm.REPOSITORIES[app], origin_main(world, app)
        edit = next(i for i in gh('release', 'edit') if repo in fake.calls[i])
        verified = [i for i, call in enumerate(fake.calls) if '--verify-output' in call and 'verify-download' in ' '.join(call) and repo in call]
        assert verified and verified[0] < edit
        calls = [call for call in fake.calls if tool(call) == 'gh' and repo in ' '.join(call)]
        assert [call[1:3] for call in calls] == [['repo', 'view'], ['api', f'repos/{repo}/commits/{sha}'],
                                                 ['api', f'repos/{repo}/commits/main'], ['release', 'view'],
                                                 ['release', 'create'], ['release', 'upload'], ['release', 'download'], ['release', 'edit']]
        create = calls[4]
        assert create[3] == 'desktop-v' + VERSION and create[create.index('--target') + 1] == sha and '--draft' in create
        assert len(calls[5]) == 4 + 6 + 2 and '--clobber' not in calls[5]
        assert calls[7][-2:] == ['--draft=false', '--latest']


def test_publish_without_a_dry_run_builds_then_prepares(world, capsys):
    code, fake = release(world, '--publish')
    assert code == 0, capsys.readouterr().err
    tools = [tool(call) for call in fake.calls]
    prepare = next(i for i, call in enumerate(fake.calls) if '--spec' in call)
    signature = [i for i, call in enumerate(fake.calls) if tool(call) == 'powershell.exe' and 'Get-ExecutionPolicy' not in call]
    assert len(signature) == 3 and max(signature) < prepare < tools.index('gh')
    assert len(world['shell'].checked) == 3


def test_phase_one_failure_publishes_nothing(world, capsys):
    assert release(world)[0] == 0, capsys.readouterr().err
    capsys.readouterr()
    fake = Fake()
    fake.fail = lambda cmd: cmd[1:3] == ['release', 'upload'] and rfm.REPOSITORIES['mentat'] in cmd
    code, fake = release(world, '--publish', fake=fake)
    assert code == 1 and "step 'publish'" in capsys.readouterr().err
    gh = [call[1:3] for call in fake.calls if tool(call) == 'gh']
    assert ['release', 'create'] in gh and ['release', 'edit'] not in gh


def test_publish_refuses_an_existing_release_before_creating_any_draft(world, capsys):
    assert release(world)[0] == 0, capsys.readouterr().err
    capsys.readouterr()
    fake = Fake()
    fake.existing = {rfm.REPOSITORIES['terrier']}
    code, fake = release(world, '--publish', fake=fake)
    assert code == 1 and "step 'publish'" in capsys.readouterr().err
    gh = [call[1:3] for call in fake.calls if tool(call) == 'gh']
    assert ['release', 'create'] not in gh and ['release', 'edit'] not in gh


def test_publish_refuses_when_main_moved_after_the_spec_before_any_draft(world, capsys):
    assert release(world)[0] == 0, capsys.readouterr().err
    capsys.readouterr()
    fake = Fake()
    fake.tips[rfm.REPOSITORIES['terrier']] = 'f' * 40
    code, fake = release(world, '--publish', fake=fake)
    error = capsys.readouterr().err
    assert code == 1 and "step 'publish'" in error and rfm.REPOSITORIES['terrier'] in error
    assert 'f' * 40 in error and origin_main(world, 'terrier') in error
    gh = [call[1:3] for call in fake.calls if tool(call) == 'gh']
    assert ['release', 'create'] not in gh and ['release', 'edit'] not in gh


def test_publish_refuses_a_bundle_that_differs_from_the_spec(world, capsys):
    assert release(world)[0] == 0, capsys.readouterr().err
    capsys.readouterr()
    fake = Fake()
    fake.tamper = 'mentat'
    code, fake = release(world, '--publish', fake=fake)
    error = capsys.readouterr().err
    assert code == 1 and "step 'manifest'" in error and 'mentat bundle release.json' in error
    assert not any(tool(call) == 'gh' for call in fake.calls)


def test_publish_refuses_an_installer_that_differs_from_its_receipt(world, capsys):
    assert release(world)[0] == 0, capsys.readouterr().err
    spec = json.loads((world['out'] / f'release-spec-{VERSION}.json').read_text(encoding='utf-8'))
    with open(spec['packages']['terrier']['package'], 'ab') as stream:
        stream.write(b'changed')
    capsys.readouterr()
    code, fake = release(world, '--publish')
    error = capsys.readouterr().err
    assert code == 1 and "step 'version'" in error and 'Terrier-1.2.3-win-x64.exe' in error
    assert not any(tool(call) == 'gh' or '--spec' in call for call in fake.calls)


def test_publish_refuses_a_dry_run_once_main_moved(world, capsys):
    assert release(world)[0] == 0, capsys.readouterr().err
    push(world, 'mentat', 'later.txt', 'new work')
    capsys.readouterr()
    code, fake = release(world, '--publish')
    error = capsys.readouterr().err
    assert code == 1 and "step 'version'" in error and 'pjg93-222/Mentat' in error
    assert not any(tool(call) == 'gh' or '--spec' in call for call in fake.calls)


def test_publish_refuses_when_release_view_fails_for_another_reason(world, capsys):
    assert release(world)[0] == 0, capsys.readouterr().err
    capsys.readouterr()
    fake = Fake()
    fake.view_error = 'HTTP 401: Bad credentials (https://api.github.com/graphql)'
    code, fake = release(world, '--publish', fake=fake)
    error = capsys.readouterr().err
    assert code == 1 and "step 'publish'" in error and 'HTTP 401: Bad credentials' in error and 'cannot be ruled out' in error
    gh = [call[1:3] for call in fake.calls if tool(call) == 'gh']
    assert ['release', 'create'] not in gh and ['release', 'edit'] not in gh


def test_release_not_found_in_any_case_counts_as_absent(world, capsys):
    assert release(world)[0] == 0, capsys.readouterr().err
    fake = Fake()
    fake.view_error = 'GraphQL: Release Not Found (repository.release)'
    code, _ = release(world, '--publish', fake=fake)
    assert code == 0, capsys.readouterr().err


def test_check_refuses_when_the_signature_check_fails(world, capsys, monkeypatch):
    # desktop_admin's own Get-AuthenticodeSignature run (the check step) reports the installer unsigned.
    unsigned = SimpleNamespace(run=lambda *a, **k: SimpleNamespace(stdout=json.dumps({'Status': 'NotSigned', 'Subject': None})))
    monkeypatch.setattr(desktop_admin, 'subprocess', unsigned)
    code, fake = release(world)
    error = capsys.readouterr().err
    assert code == 1 and "step 'check'" in error and 'pinned Windows publisher' in error
    assert not any(tool(call) == 'gh' or '--spec' in call for call in fake.calls)


def add_ledger_row(world, app, sequence, version):
    ledger = sqlite3.connect(world['state'] / 'github-prepared.sqlite3')
    ledger.execute('INSERT INTO prepared VALUES (?,?,?,?,?,?,?)', (rfm.REPOSITORIES[app], app, 'win32', 'x64', sequence, version, '{}'))
    ledger.commit()
    ledger.close()


@pytest.mark.parametrize('version', [VERSION, '1.3.0'])
def test_check_refuses_a_version_that_does_not_advance_the_ledger(world, capsys, version):
    add_ledger_row(world, 'mentat', 5, version)  # lower sequence than the next (8), but this version is not above it
    code, fake = release(world)
    error = capsys.readouterr().err
    assert code == 1 and "step 'check'" in error and 'mentat' in error and 'must advance' in error
    assert not any('--spec' in call for call in fake.calls)


def test_check_refuses_a_sequence_the_ledger_already_has(world, capsys, monkeypatch):
    # version_step already enforces the global last + 1; check applies prepare's per-app rule as well.
    monkeypatch.setattr(rfm.Release, 'last_sequence', lambda self: 0)
    code, _ = release(world)
    error = capsys.readouterr().err
    assert code == 1 and "step 'check'" in error and 'melange' in error and 'sequence 1' in error and 'must advance' in error


def test_check_passes_without_a_ledger(world, capsys):
    (world['state'] / 'github-prepared.sqlite3').unlink()
    code, _ = release(world)
    assert code == 0, capsys.readouterr().err


def test_publish_refuses_a_different_sequence_than_the_dry_run(world, capsys):
    assert release(world)[0] == 0, capsys.readouterr().err
    capsys.readouterr()
    code, fake = release(world, '--publish', '--sequence', '99')
    error = capsys.readouterr().err
    assert code == 1 and "step 'version'" in error and '--sequence 99' in error and 'prepared sequence 8' in error
    assert not any(tool(call) == 'gh' or '--spec' in call for call in fake.calls)


def test_publish_refuses_an_existing_bundle_on_resume(world, capsys):
    assert release(world)[0] == 0, capsys.readouterr().err
    (world['out'] / f'release-{VERSION}' / 'bundle').mkdir()
    capsys.readouterr()
    code, fake = release(world, '--publish')
    error = capsys.readouterr().err
    assert code == 1 and "step 'manifest'" in error and 'bundle' in error and 'exists' in error
    assert not any(tool(call) == 'gh' or '--spec' in call for call in fake.calls)


class Interpreter:
    """rfm's view of sys with another version_info; every other attribute is the real one."""

    def __init__(self, version_info):
        self.version_info = version_info

    def __getattr__(self, name):
        return getattr(sys, name)


@pytest.mark.parametrize('implementation, version_info', [('CPython', (3, 11, 9)), ('PyPy', (3, 12, 1))])
def test_other_interpreters_are_refused_at_local_without_build_python(world, capsys, monkeypatch, implementation, version_info):
    monkeypatch.setattr(rfm.platform, 'python_implementation', lambda: implementation)
    monkeypatch.setattr(rfm, 'sys', Interpreter(version_info))
    code, fake = release(world, build_python=False)
    error = capsys.readouterr().err
    assert code == 1 and "step 'local'" in error and 'CPython 3.12' in error and '--build-python' in error
    assert fake.calls == []


def test_build_python_skips_the_interpreter_check(world, capsys, monkeypatch):
    monkeypatch.setattr(rfm.platform, 'python_implementation', lambda: 'PyPy')
    monkeypatch.setattr(rfm, 'sys', Interpreter((3, 11, 9)))
    code, _ = release(world)  # --build-python given
    assert code == 0, capsys.readouterr().err


@pytest.mark.parametrize('policy', ['Restricted', 'AllSigned', 'Undefined', ''])
def test_blocking_execution_policy_is_refused_at_local(world, capsys, policy):
    fake = Fake()
    fake.policy = policy
    code, fake = release(world, fake=fake)
    error = capsys.readouterr().err
    assert code == 1 and "step 'local'" in error and 'sign-staged-binary.ps1' in error
    assert 'Set-ExecutionPolicy -Scope Process RemoteSigned' in error and 'your decision' in error
    assert fake.calls == [[rfm.POWERSHELL, '-NoProfile', '-NonInteractive', '-Command', 'Get-ExecutionPolicy']]


def test_execution_policy_query_inherits_the_operators_environment(world, capsys):
    seen = []

    class Recording(Fake):
        def __call__(self, cmd, cwd=None, env=None):
            if 'Get-ExecutionPolicy' in cmd:
                seen.append(env)
            return super().__call__(cmd, cwd, env)

    code, fake = release(world, fake=Recording(), environ={'PSExecutionPolicyPreference': 'RemoteSigned'})
    assert code == 0, capsys.readouterr().err
    assert seen == [{'PSExecutionPolicyPreference': 'RemoteSigned'}]
    assert all(env['PSExecutionPolicyPreference'] == 'RemoteSigned' for env in fake.builds)  # and so does the hook's child


def test_publisher_other_than_the_hook_subject_is_refused_at_local(world, capsys):
    (world['state'] / 'trust.json').write_text(json.dumps({'windowsPublisher': 'CN=Someone else'}), encoding='utf-8')
    code, fake = release(world)
    error = capsys.readouterr().err
    assert code == 1 and "step 'local'" in error and rfm.SUBJECT in error and fake.calls == []


def test_tool_repository_without_the_signing_hook_is_refused_at_version(world, capsys):
    mentat = world['paths']['mentat']
    git(mentat, 'rm', '-q', rfm.SIGNING_HOOK)
    git(mentat, 'commit', '-q', '-m', 'drop hook')
    git(mentat, 'push', '-q', 'origin', 'main')
    code, fake = release(world)
    error = capsys.readouterr().err
    assert code == 1 and "step 'version'" in error and 'pjg93-222/Mentat' in error and rfm.SIGNING_HOOK in error
    assert not any(tool(call) == 'npm' for call in fake.calls) and not (world['out'] / f'release-{VERSION}').exists()


def test_installer_the_hook_did_not_sign_is_refused_at_sign(world, capsys):
    fake = Fake()
    fake.hook = False
    code, fake = release(world, fake=fake)
    error = capsys.readouterr().err
    assert code == 1 and "step 'sign'" in error and 'NotSigned' in error and 'signing hook was not active' in error
    assert not (world['out'] / f'receipts-{VERSION}').exists() and not (world['out'] / f'release-spec-{VERSION}.json').exists()


def test_missing_hook_receipt_is_refused_at_sign(world, capsys):
    fake = Fake()
    fake.hook_receipt = False
    code, fake = release(world, fake=fake)
    error = capsys.readouterr().err
    assert code == 1 and "step 'sign'" in error and 'Melange-1.2.3-win-x64.exe.signatures.json is missing' in error
    assert not (world['out'] / f'receipts-{VERSION}').exists()


def test_hook_receipt_for_other_bytes_is_refused_at_sign(world, capsys):
    class Changed(Fake):
        def build(self, cwd, env):
            super().build(cwd, env)
            installer = next((Path(env['DESKTOP_DIST_ROOT']) / env['DESKTOP_APP_ID']).glob('*.exe'))
            installer.write_bytes(installer.read_bytes().replace(b'synthetic', b'Synthetic'))  # changed after the hook verified it

    code, _ = release(world, fake=Changed())
    error = capsys.readouterr().err
    assert code == 1 and "step 'sign'" in error and 'does not record' in error


def test_terrier_alone_needs_only_melange_and_geo(world, capsys):
    push(world, 'mentat', 'ops/desktop/client/package.json', json.dumps({'name': 'client', 'version': '9.9.9'}))  # not needed
    code, fake = release(world, '--apps', 'terrier')
    assert code == 0, capsys.readouterr().err
    release_dir = world['out'] / f'release-{VERSION}'
    src = release_dir / 'src'
    assert sorted(path.name for path in src.iterdir()) == ['melange', 'terrier']
    assert {cwd for call, cwd in zip(fake.calls, fake.cwds) if tool(call) == 'npm' or 'pytest' in call} == {
        str(src / 'melange'), str(src / 'melange' / 'ops' / 'desktop' / 'client'), str(src / 'terrier' / 'frontend')}
    spec = json.loads((world['out'] / f'release-spec-{VERSION}.json').read_text(encoding='utf-8'))
    validate_spec(spec)
    assert set(spec['packages']) == {'terrier'}
    assert {app: ref['commit'] for app, ref in spec['sourceRefs'].items()} == {app: origin_main(world, app) for app in rfm.APPS}
    tags = [cwd for call, cwd in zip(fake.calls, fake.cwds) if any('refs/tags/' in part for part in call)]
    assert tags and set(tags) == {str(world['paths']['terrier'])}
    assert sorted(path.name for path in (world['out'] / f'receipts-{VERSION}').iterdir()) == ['terrier.json']
    assert [env['DESKTOP_APP_ID'] for env in fake.builds] == ['terrier']


def runtime(world, python=True, provenance=True, commit=None, reviewed=None):
    """A previously built Terrier runtime, built from Geo main (or the given commits)."""
    folder = world['tmp'] / 'previous' / 'terrier'
    folder.mkdir(parents=True)
    if provenance:
        (folder / 'source-provenance.json').write_text(json.dumps(
            {'app': 'terrier', 'repository': 'pjg93-222/Geo', 'commit': commit or origin_main(world, 'terrier'),
             'reviewedBase': reviewed or origin_main(world, 'terrier')}), encoding='utf-8')
    for part in ('python', 'sources', 'bootstrap'):
        (folder / part).mkdir(parents=True)
    if python:
        (folder / 'python' / 'python.exe').write_bytes(b'MZ python')
    (folder / 'runtime-status.json').write_text(json.dumps({'appId': 'terrier', 'missingNativeRuntimes': []}), encoding='utf-8')
    (folder / 'dependency-inventory.json').write_text(json.dumps([{'name': 'Django', 'version': '5.2.7', 'license': 'BSD'}]), encoding='utf-8')
    return folder


def test_injected_runtime_replaces_only_the_sources(world, capsys):
    folder = runtime(world)
    code, fake = release(world, '--apps', 'terrier', '--inject-runtime', f'terrier={folder}', build_python=False)
    assert code == 0, capsys.readouterr().err
    release_dir = world['out'] / f'release-{VERSION}'
    python = release_dir / 'runtime' / 'terrier' / 'python' / 'python.exe'
    assert python.read_bytes() == b'MZ python'
    assert not any('venv' in call or 'pip' in call for call in fake.calls)  # no venv, no install
    runtime_calls = [call for call in fake.calls if any(part.endswith('build_runtime.py') for part in call)]
    assert [('--stage-only' in call, '--sync-sources-only' in call) for call in runtime_calls] == [(True, False), (False, True)]
    assert all(call[0] == str(python) for call in runtime_calls)
    assert [call for call in fake.calls if 'pytest' in call][0][0] == sys.executable  # Terrier's lock has no pytest
    receipt = json.loads((world['out'] / f'receipts-{VERSION}' / 'terrier.json').read_text(encoding='utf-8'))
    digest = lambda name: hashlib.sha256((folder / name).read_bytes()).hexdigest()
    tests = receipt['gates']['tests']['evidence']
    assert f'runtime injected from {folder}' in tests
    assert f'dependency-inventory.json sha256 {digest("dependency-inventory.json")}' in tests
    assert f'runtime-status.json sha256 {digest("runtime-status.json")}' in tests
    assert (f'source-provenance.json commit {origin_main(world, "terrier")}: requirements.txt sha256 '
            f'{hashlib.sha256(b"Django>=5.2,<5.3" + chr(10).encode()).hexdigest()}') in tests
    assert f'runtime injected from {folder}' in receipt['gates']['redistribution']['evidence']
    assert receipt['nativeAcceptance']['status'] == 'passed'


@pytest.mark.parametrize('case', ['requirements', 'lock', 'provenance', 'unresolved'])
def test_injected_runtime_is_refused_unless_its_requirements_are_mains(world, capsys, case):
    folder = runtime(world, provenance=case != 'provenance', commit='1' * 40 if case == 'unresolved' else None,
                     reviewed='2' * 40 if case == 'unresolved' else None)  # built from the current Geo main
    if case in ('requirements', 'lock'):
        push(world, 'terrier', 'requirements.txt' if case == 'requirements' else 'requirements.lock.txt', 'Django==6.0.1\n')
    code, fake = release(world, '--apps', 'terrier', '--inject-runtime', f'terrier={folder}')
    error = capsys.readouterr().err
    assert code == 1 and "step 'build'" in error and 'full build is required' in error, error
    assert not any('--sync-sources-only' in call for call in fake.calls)


def test_injected_runtime_falls_back_to_its_reviewed_base(world, capsys):
    folder = runtime(world, commit='1' * 40)  # not on GitHub, so not fetchable
    code, fake = release(world, '--apps', 'terrier', '--inject-runtime', f'terrier={folder}')
    assert code == 0, capsys.readouterr().err
    assert ['fetch', 'origin', '1' * 40] in [call[-3:] for call in fake.calls]
    receipt = json.loads((world['out'] / f'receipts-{VERSION}' / 'terrier.json').read_text(encoding='utf-8'))
    assert f'source-provenance.json reviewedBase {origin_main(world, "terrier")}' in receipt['gates']['tests']['evidence']


def test_injected_runtime_without_python_is_refused(world, capsys):
    code, fake = release(world, '--apps', 'terrier', '--inject-runtime', f'terrier={runtime(world, python=False)}')
    error = capsys.readouterr().err
    assert code == 1 and "step 'local'" in error and 'python.exe' in error and fake.calls == []


def test_publish_after_a_terrier_dry_run_publishes_only_to_geo(world, capsys):
    folder = runtime(world)
    assert release(world, '--apps', 'terrier', '--inject-runtime', f'terrier={folder}')[0] == 0, capsys.readouterr().err
    capsys.readouterr()
    code, fake = release(world, '--publish')  # another app set than the dry run
    error = capsys.readouterr().err
    assert code == 1 and "step 'version'" in error and '--apps' in error
    assert not any(tool(call) == 'gh' or '--spec' in call for call in fake.calls)
    code, fake = release(world, '--publish', '--apps', 'terrier')
    out, error = capsys.readouterr()
    assert code == 0, error
    gh = [call for call in fake.calls if tool(call) == 'gh']
    assert gh and all('pjg93-222/Geo' in ' '.join(call) for call in gh)
    assert 'Published desktop-v1.2.3 to pjg93-222/Geo.' in out


def snapshot(root):
    return {path: (path.read_bytes() if path.is_file() else None, path.stat().st_mtime_ns) for path in sorted(root.rglob('*'))}


def test_gate_runs_from_security_root_on_the_staged_sources_after_the_allowlist(world, capsys):
    before = snapshot(world['security'])
    code, fake = release(world)
    assert code == 0, capsys.readouterr().err
    stage = world['out'] / f'release-{VERSION}' / 'stage'
    for app in rfm.APPS:
        staged = next(i for i, call in enumerate(fake.calls) if '--stage-only' in call and call[call.index('--app') + 1] == app)
        gate = next(i for i, call in enumerate(fake.calls) if str(stage / app / 'stagehash' / 'sources') in call)
        assert staged < gate and fake.calls[gate][2] == str(world['security'] / 'ops' / 'security_gate.py')
        assert not str(fake.cwds[gate]).startswith(str(world['security']))
        evidence = json.loads((world['out'] / f'receipts-{VERSION}' / f'{app}.json').read_text(encoding='utf-8'))['gates']['security']['evidence']
        assert f'from {world["security"]} on the {app} shipped sources' in evidence
    assert snapshot(world['security']) == before  # the private tree is never written
    assert not any(str(cwd or '').startswith(str(world['security'])) for cwd in fake.cwds)


@pytest.mark.parametrize('missing', ['ops/security/canaries.txt', 'ops/security_gate.py'])
def test_missing_private_gate_files_are_refused_at_local(world, capsys, missing):
    (world['security'] / missing).unlink()
    code, fake = release(world)
    error = capsys.readouterr().err
    assert code == 1 and "step 'local'" in error and missing in error and fake.calls == []


def test_terrier_exceptions_are_appended_for_terrier_only(world, capsys):
    code, fake = release(world)
    assert code == 0, capsys.readouterr().err
    by_app = {Path(cmd[cmd.index('--target') + 1]).parents[1].name: (cmd, text) for cmd, text in fake.gates}  # stage/<app>/<id>/sources
    assert by_app['melange'][1] is None and by_app['mentat'][1] is None
    assert '--exceptions' not in by_app['melange'][0] and '--exceptions' not in by_app['mentat'][0]
    merged = world['out'] / f'release-{VERSION}' / 'security-gate' / 'terrier-exceptions.toml'
    assert by_app['terrier'][0][by_app['terrier'][0].index('--exceptions') + 1] == str(merged)
    assert by_app['terrier'][1] == ORIGINAL_EXCEPTIONS + '\n' + TERRIER_EXCEPTIONS
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    evidence = json.loads((world['out'] / f'receipts-{VERSION}' / 'terrier.json').read_text(encoding='utf-8'))['gates']['security']['evidence']
    original = world['security'] / 'ops' / 'security' / 'exceptions.toml'
    extra = world['out'] / f'release-{VERSION}' / 'src' / 'melange' / 'ops' / 'desktop' / 'packaging' / 'terrier-security-exceptions.toml'
    assert f'exceptions.toml {original} sha256 {digest(original)}' in evidence
    assert f'terrier-security-exceptions.toml sha256 {digest(extra)} appended' in evidence
    assert f'merged {merged} sha256 {hashlib.sha256(merged.read_bytes()).hexdigest()}' in evidence
    assert (world['security'] / 'ops' / 'security' / 'exceptions.toml').read_text(encoding='utf-8') == ORIGINAL_EXCEPTIONS


def test_committed_terrier_exceptions_excuse_only_the_shipped_assets():
    entries = tomllib.loads((Path(__file__).resolve().parent / 'terrier-security-exceptions.toml').read_text(encoding='utf-8'))
    assert set(entries) == {'exception'}
    assert [(e['stage'], e['check'], e['match'], e['approver']) for e in entries['exception']] == [
        ('export', 'data_leak', 'data/field_dictionary.csv: denied extension .csv', 'Paul'),
        ('export', 'data_leak', 'frontend/dist/brand/terrier-loading-hq.mp4: denied extension .mp4', 'Paul'),
        ('export', 'data_leak', 'frontend/dist/ocr/tesseract-6.0.1/eng.traineddata.gz: denied extension .gz', 'Paul')]
    assert all(e['decision'] == 'D-292' and e['expires'] == '2026-11-23' and 'owner ruling 2026-10-24' in e['reason']
               for e in entries['exception'])


def test_frontend_is_built_and_audited_before_staging_for_apps_that_ship_it(world, capsys):
    code, fake = release(world)
    assert code == 0, capsys.readouterr().err
    src = world['out'] / f'release-{VERSION}' / 'src'
    frontend = [(i, call[1:]) for i, (call, cwd) in enumerate(zip(fake.calls, fake.cwds)) if cwd == str(src / 'terrier' / 'frontend')]
    assert [verbs for _, verbs in frontend] == [['ci', '--no-fund'], ['run', 'build'], ['audit', '--omit=dev', '--audit-level=high']]
    staged = next(i for i, call in enumerate(fake.calls) if '--stage-only' in call and call[call.index('--app') + 1] == 'terrier')
    assert frontend[1][0] < staged
    assert not any(str(cwd or '').endswith('frontend') and 'terrier' not in str(cwd) for cwd in fake.cwds)  # Melange, Mentat: none
    receipt = json.loads((world['out'] / f'receipts-{VERSION}' / 'terrier.json').read_text(encoding='utf-8'))['gates']
    assert 'npm-build-frontend-terrier.log' in receipt['dataAllowlist']['evidence']
    assert 'npm-audit-frontend-terrier.log' in receipt['dependencies']['evidence']


@pytest.mark.parametrize('verb, step', [('build', 'dataAllowlist'), ('ci', 'dataAllowlist'), ('audit', 'dependencies')])
def test_frontend_failure_is_refused_before_staging(world, capsys, verb, step):
    fake = Fake()
    fake.npm_fail = lambda cmd, cwd: str(cwd).endswith('frontend') and verb in cmd
    code, fake = release(world, '--apps', 'terrier', fake=fake)
    error = capsys.readouterr().err
    assert code == 1 and f"step '{step}'" in error and 'npm' in error and 'frontend-terrier.log' in error
    assert not any('--stage-only' in call for call in fake.calls)


def test_pwsh_module_path_never_reaches_a_child(world, capsys):
    seen = []

    class Recording(Fake):
        def __call__(self, cmd, cwd=None, env=None):
            seen.append(env)
            return super().__call__(cmd, cwd, env)

    environ = {'PSModulePath': r'C:\Program Files\PowerShell\7\Modules', 'PSExecutionPolicyPreference': 'RemoteSigned'}
    code, fake = release(world, fake=Recording(), environ=environ)
    assert code == 0, capsys.readouterr().err
    assert seen and all(env is not None and 'PSExecutionPolicyPreference' in env for env in seen)
    assert not any(key.upper() == 'PSMODULEPATH' for env in seen for key in env)


def test_desktop_admin_gate_check_never_sees_pwsh_module_path(world, capsys, monkeypatch):
    seen = []

    class Spy(Shell):
        def run(self, cmd, env=None, **kwargs):
            seen.append(dict(env))
            return super().run(cmd, env=env, **kwargs)

    spy = Spy()
    monkeypatch.setattr(desktop_admin, 'subprocess', spy)
    monkeypatch.setenv('PSModulePath', r'C:\Program Files\PowerShell\Modules')
    code, _ = release(world)
    assert code == 0, capsys.readouterr().err
    assert seen and not any(key.upper() == 'PSMODULEPATH' for env in seen for key in env)
    assert os.environ['PSModulePath'] == r'C:\Program Files\PowerShell\Modules'
    monkeypatch.delenv('PSModulePath')
    with rfm.without_ps_module_path():
        pass
    assert 'PSModulePath' not in os.environ
