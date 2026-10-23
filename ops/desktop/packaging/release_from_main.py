"""Build, gate, sign and stage desktop-v<version> of Melange, Mentat and Terrier from each repository's origin/main.

Local only: the Authenticode certificate (pinned thumbprint below, used by each client's release-signing.cjs hook during
the build) and the update-manifest keys in the publisher state directory never leave this PC, so the command refuses to
run in CI. Without --publish it makes no GitHub writes and reserves no release sequence.
"""
# Any district release tag created alongside a release must stay lightweight (`git -c tag.gpgsign=false tag <name> <sha>`)
# until a release containing commit 0084dd739 ships, because the 1.0.15 client rejects annotated district tags. This
# command creates no git tags at all: desktop-v<version> is created on GitHub by `gh release create --target <sha>`.
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import tempfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from github_release import REPOSITORIES, Refused, app_release, repositories, valid_sequence, valid_version, validate_spec
from desktop_admin import Store  # importable once github_release has put ops/desktop/server on sys.path

APPS = ('melange', 'mentat', 'terrier')
PRODUCTS = {'melange': 'Melange', 'mentat': 'Mentat', 'terrier': 'Terrier'}
# The export whose ops/desktop/{client,packaging} builds each app: Mentat ships its own client; Terrier is built by
# Melange's client and packaging with Geo as the application source. Every app's source is its own export.
TOOLS = {'melange': 'melange', 'mentat': 'mentat', 'terrier': 'melange'}
PACKAGING = Path('ops') / 'desktop' / 'packaging'
GATES = ('tests', 'security', 'dependencies', 'redistribution', 'dataAllowlist')
# What ops/desktop/client/release-signing.cjs accepts: it signs only with this certificate and this exact subject.
THUMBPRINT = '0EBC9AD04E929CDD731EDB5D278A4143BC3D3D30'
SUBJECT = 'CN=Melange Systems Desktop Release (self-signed)'
SIGNING_HOOK = 'ops/desktop/client/release-signing.cjs'
# The host the hook runs sign-staged-binary.ps1 with (`-File`, no execution-policy argument), and the effective
# policies under which that script runs; the operator chooses the policy, this command never overrides it.
POWERSHELL = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
RUNNABLE_POLICIES = {'RemoteSigned', 'Unrestricted', 'Bypass'}
DEFAULT_STATE = Path.home() / 'Documents' / 'MelangeDesktopAdmin'  # same default as desktop_admin.py
# Dedicated clean clones, one per repository (the everyday checkouts are other lineages); cloned on first use.
SOURCES = Path.home() / 'Documents' / 'MelangeReleaseSources'
# Runtime databases and secret-named files; build_runtime.py already skips them, the inventory is rechecked here.
DATABASE = re.compile(r'\.(sqlite3?|db)(-wal|-shm|-journal)?$', re.I)
SECRET_NAMES = {'keys.json', '.env', '.secret', 'accounts.sqlite3', 'dashboard_password.txt'}
# Get-AuthenticodeSignature of the path in DESKTOP_VERIFY_PACKAGE; the path never enters the script text.
SIGNATURE = ('$s=Get-AuthenticodeSignature -LiteralPath $env:DESKTOP_VERIFY_PACKAGE; '
             '@{Status=[string]$s.Status;Subject=[string]$s.SignerCertificate.Subject;'
             'Thumbprint=[string]$s.SignerCertificate.Thumbprint;Timestamped=[bool]$s.TimeStamperCertificate}'
             '|ConvertTo-Json -Compress')


class StepFailed(Exception):
    def __init__(self, step, message):
        super().__init__(message)
        self.step, self.message = step, message


class Ran:
    def __init__(self, returncode, stdout, stderr, evidence=None):
        self.returncode, self.stdout, self.stderr, self.evidence = returncode, stdout, stderr, evidence


def run(cmd, cwd=None, env=None):
    """The one real process runner (tests inject a fake). npm is npm.cmd on Windows, hence which()."""
    p = subprocess.run([shutil.which(cmd[0]) or cmd[0], *cmd[1:]], cwd=cwd, env=env, capture_output=True, stdin=subprocess.DEVNULL)
    return Ran(p.returncode, p.stdout.decode('utf-8', 'replace'), p.stderr.decode('utf-8', 'replace'))


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def origin_matches(url, repository):
    """The raw configured origin is https://github.com/<repository>[.git][/] or git@github.com:<repository>[.git] (any case)."""
    return re.fullmatch(r'(https://github\.com/|git@github\.com:)' + re.escape(repository) + r'(\.git)?/?', url.strip(), re.I) is not None


def gate(evidence):
    return {'status': 'passed', 'evidence': evidence}


class Release:
    def __init__(self, args, runner=run, environ=None, os_name=None):
        self.args, self.runner = args, runner
        self.environ = dict(os.environ if environ is None else environ)
        self.os_name = os.name if os_name is None else os_name
        self.paths = {'melange': args.melange, 'mentat': args.mentat, 'terrier': args.geo}
        self.state, self.root = args.state, args.output_root
        self.python = sys.executable  # release tools, and the interpreter that creates the build venvs
        self.build_python = args.build_python  # one given build venv for every app; otherwise one venv per app is made
        self.logs = None
        self.resume = False

    # ---------------------------------------------------------------- helpers
    def call(self, step, cmd, cwd=None, env=None, log=None, check=True):
        cmd = [str(part) for part in cmd]
        shown = subprocess.list2cmdline(cmd)
        try:
            result = self.runner(cmd, cwd=None if cwd is None else str(cwd), env=env)
        except OSError as error:
            raise StepFailed(step, f'{cmd[0]} could not start: {error}') from error
        ran = Ran(result.returncode, result.stdout or '', result.stderr or '')
        if log:
            path = self.logs / (log + '.log')
            path.write_text(f'$ {shown}\ncwd {cwd}\nexit {ran.returncode}\n--- stdout ---\n{ran.stdout}\n--- stderr ---\n{ran.stderr}\n',
                            encoding='utf-8')
            ran.evidence = f'`{shown}` exit {ran.returncode}; log {path} sha256 {sha256(path)}'
        if check and ran.returncode != 0:
            tail = (ran.stderr.strip() or ran.stdout.strip()).splitlines()[-3:]
            raise StepFailed(step, f'`{shown}` exited {ran.returncode}' + (f' (log {path})' if log else '')
                             + (': ' + ' | '.join(tail) if tail else ''))
        return ran

    def git(self, step, app, *args, check=True):
        result = self.call(step, ['git', *args], cwd=self.paths[app], check=False)
        if check and result.returncode != 0:
            raise StepFailed(step, f'{self.label(app)}: git {" ".join(args)} failed: {result.stderr.strip()}')
        return result

    def label(self, app):
        return f'{REPOSITORIES[app]} at {self.paths[app]}'

    def signature(self, step, path):
        result = self.call(step, ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', SIGNATURE],
                           env={**self.environ, 'DESKTOP_VERIFY_PACKAGE': str(path)})
        try:
            return json.loads(result.stdout)
        except ValueError as error:
            raise StepFailed(step, f'unreadable Get-AuthenticodeSignature output for {path}') from error

    def tool(self, app, relative):
        """The export holding `relative` for this app: its tool export, else Melange's."""
        root = self.export[TOOLS[app]]
        return root if (root / relative).is_file() else self.export['melange']

    def python_tool(self, step, app, script, *args, log, check=True, python=None, root=None):
        root = root or self.export[TOOLS[app]]
        return self.call(step, [python or self.python, '-E', '-s', '-B', root / PACKAGING / script, *args], cwd=root, log=log, check=check)

    # ---------------------------------------------------------------- steps
    def local(self):
        for name in ('CI', 'GITHUB_ACTIONS'):
            if name in self.environ:
                raise StepFailed('local', f'{name} is set: the signing certificate and update keys never run in CI')
        if self.os_name != 'nt':
            raise StepFailed('local', 'a release is built and Authenticode-signed on Windows only')
        try:
            self.publisher = json.loads((self.state / 'trust.json').read_text(encoding='utf-8')).get('windowsPublisher')
        except (OSError, ValueError) as error:
            raise StepFailed('local', f'publisher state {self.state} is unreadable: {error}') from error
        if not isinstance(self.publisher, str) or not self.publisher:
            raise StepFailed('local', f'{self.state / "trust.json"} has no windowsPublisher; configure the publisher state first')
        if self.publisher != SUBJECT:
            raise StepFailed('local', f'{self.state / "trust.json"} windowsPublisher is {self.publisher!r}; the signing hook signs '
                                      f'only as {SUBJECT!r}')
        # bundle_python.py copies the build interpreter into the runtime and accepts only a dedicated virtual environment.
        if self.build_python is None:
            if platform.python_implementation() != 'CPython' or sys.version_info[:2] != (3, 12):
                raise StepFailed('local', f'the build venvs are created with this interpreter, which must be CPython 3.12 '
                                          f'(it is {platform.python_implementation()} {platform.python_version()}); '
                                          'run the command with Python 3.12 or pass --build-python')
        elif not (Path(self.build_python).parent.parent / 'pyvenv.cfg').is_file():
            raise StepFailed('local', f'--build-python {self.build_python} is not the python.exe of a virtual environment '
                                      '(omit it to create hash-locked build venvs, or pass the python.exe of one)')
        # The build inherits this environment, so a process-scoped policy the operator set (PSExecutionPolicyPreference)
        # reaches the hook's PowerShell child; this query reads the effective policy and never sets one.
        policy = self.call('local', [POWERSHELL, '-NoProfile', '-NonInteractive', '-Command', 'Get-ExecutionPolicy'],
                           env=self.environ).stdout.strip()
        if policy not in RUNNABLE_POLICIES:
            raise StepFailed('local', f'the effective PowerShell execution policy is {policy or "unknown"}: the signing hook runs '
                                      'sign-staged-binary.ps1 with powershell.exe -File and no policy override, so it would be '
                                      'blocked. Which policy to allow is your decision; for example run this command from a '
                                      'PowerShell session after `Set-ExecutionPolicy -Scope Process RemoteSigned`')

    def sources(self):
        self.shas = {}
        for app in APPS:
            path = Path(self.paths[app])
            if not path.exists() and app in self.args.default_sources:
                path.parent.mkdir(parents=True, exist_ok=True)
                self.call('sources', ['git', 'clone', f'https://github.com/{REPOSITORIES[app]}.git', path])
            if not path.is_dir():
                raise StepFailed('sources', f'{self.label(app)}: checkout not found')
            # The configured text, not `remote get-url`: insteadOf rewriting must not disguise another host as GitHub.
            url = self.git('sources', app, 'config', '--get', 'remote.origin.url').stdout.strip()
            if not origin_matches(url, REPOSITORIES[app]):
                raise StepFailed('sources', f'{self.label(app)}: origin is {url}, not {REPOSITORIES[app]}')
            self.git('sources', app, 'fetch', '--tags', 'origin')
            # Untracked files are ignored: every source is exported from the commit with git archive, never copied.
            if self.git('sources', app, 'status', '--porcelain', '--untracked-files=no').stdout.strip():
                raise StepFailed('sources', f'{self.label(app)}: tracked files are modified; commit to main or discard them')
            head = self.git('sources', app, 'rev-parse', 'HEAD').stdout.strip()
            main = self.git('sources', app, 'rev-parse', '--verify', 'refs/remotes/origin/main^{commit}').stdout.strip()
            if not re.fullmatch(r'[0-9a-f]{40}', head) or head != main:
                raise StepFailed('sources', f'{self.label(app)}: HEAD {head[:12]} is not origin/main {main[:12]}; '
                                            'check out main and fast-forward it to origin/main')
            self.shas[app] = head

    def version_step(self):
        versions = {}
        for tool in sorted(set(TOOLS.values())):
            package = self.git('version', tool, 'show', self.shas[tool] + ':ops/desktop/client/package.json').stdout
            try:
                versions[tool] = json.loads(package)['version']
            except (ValueError, KeyError, TypeError) as error:
                raise StepFailed('version', f'ops/desktop/client/package.json at {REPOSITORIES[tool]} '
                                            f'{self.shas[tool][:12]} has no version') from error
            if self.git('version', tool, 'cat-file', '-e', f'{self.shas[tool]}:{SIGNING_HOOK}', check=False).returncode != 0:
                raise StepFailed('version', f'{REPOSITORIES[tool]} main {self.shas[tool][:12]} has no {SIGNING_HOOK}; its installers '
                                            'would be built unsigned. Merge the inner-signing hook to that main first')
        if len(set(versions.values())) != 1:
            raise StepFailed('version', 'the client versions differ: ' + ', '.join(
                f'{REPOSITORIES[tool]} ops/desktop/client/package.json {version}' for tool, version in sorted(versions.items()))
                + '; set the same version on both mains')
        version = versions['melange']
        if self.args.version is not None and self.args.version != version:
            raise StepFailed('version', f'--version {self.args.version} differs from ops/desktop/client/package.json {version} on '
                                        'Melange and Mentat main; bump the version on main first')
        if not valid_version(version):
            raise StepFailed('version', f'{version} is not a stable X.Y.Z version')
        self.version, self.tag = version, 'desktop-v' + version
        for app in APPS:
            if self.git('version', app, 'rev-parse', '-q', '--verify', 'refs/tags/' + self.tag, check=False).returncode == 0:
                raise StepFailed('version', f'{self.label(app)}: tag {self.tag} already exists locally; bump the version on main')
            if self.git('version', app, 'ls-remote', '--tags', 'origin', 'refs/tags/' + self.tag).stdout.strip():
                raise StepFailed('version', f'{self.label(app)}: tag {self.tag} already exists on origin; bump the version on main')
        self.release = self.root / f'release-{version}'
        self.spec_path = self.root / f'release-spec-{version}.json'
        self.receipts = self.root / f'receipts-{version}'
        # --publish after a completed dry run publishes its signed installers, as long as every origin/main is unchanged.
        self.resume = bool(self.args.publish and self.spec_path.is_file())
        if self.resume:
            self.spec = json.loads(self.spec_path.read_text(encoding='utf-8'))
            for app in APPS:
                if self.spec.get('sourceRefs', {}).get(app) != self.source(app):
                    raise StepFailed('version', f'{self.spec_path} was prepared from other commits than origin/main of '
                                                f'{REPOSITORIES[app]}; bump the version on main and run again')
            if self.args.sequence is not None and self.args.sequence != self.spec['sequence']:
                raise StepFailed('version', f'--sequence {self.args.sequence} differs from the prepared sequence {self.spec["sequence"]}')
            self.sequence = self.spec['sequence']
            self.installers = {}
            for app in APPS:
                files = self.spec['packages'][app]
                installer = Path(files['package'])
                receipt = json.loads(Path(files['receipt']).read_text(encoding='utf-8'))
                if not installer.is_file() or sha256(installer) != receipt.get('sha256'):
                    raise StepFailed('version', f'{installer} is not the signed installer {files["receipt"]} records; '
                                                'bump the version on main and run again')
                self.installers[app] = installer
            return
        last = self.last_sequence()
        self.sequence = self.args.sequence if self.args.sequence is not None else last + 1
        if not valid_sequence(self.sequence) or self.sequence <= last:
            raise StepFailed('version', f'sequence {self.sequence} must be a positive integer above the last prepared {last}')

    def ledger(self, query, parameters=()):
        """First row of a read-only query on the prepare ledger; None when there is no ledger or no table yet."""
        ledger = self.state / 'github-prepared.sqlite3'
        if not ledger.exists():
            return None
        connection = sqlite3.connect(ledger.resolve().as_uri() + '?mode=ro', uri=True)
        try:
            return connection.execute(query, parameters).fetchone()
        except sqlite3.OperationalError as error:
            if 'no such table' in str(error):
                return None
            raise
        finally:
            connection.close()

    def last_sequence(self):
        return (self.ledger('SELECT MAX(sequence) FROM prepared') or (0,))[0] or 0

    def source(self, app):
        return {'repository': REPOSITORIES[app], 'ref': 'main', 'commit': self.shas[app]}

    def export_step(self):
        if self.release.exists():
            raise StepFailed('export', f'{self.release} already exists; remove it or bump the version '
                                       '(--publish reuses it only when its receipts and release spec are complete)')
        self.logs = self.release / 'logs'
        self.logs.mkdir(parents=True)
        (self.release / 'src').mkdir()
        self.export = {}
        for app in APPS:
            destination = self.release / 'src' / app
            archive = self.release / 'src' / (app + '.tar')
            # Committed bytes: no autocrlf/native-eol conversion on the way out.
            self.git('export', app, '-c', 'core.autocrlf=false', '-c', 'core.eol=lf', 'archive', '--format=tar',
                     '-o', str(archive), self.shas[app])
            with tarfile.open(archive) as tar:
                tar.extractall(destination, filter='data')
            archive.unlink()
            self.export[app] = destination

    def lock_file(self, app):
        # Windows locks only: Geo's requirements.build.lock is a Linux (manylinux) lock and cannot install here.
        path = self.export[TOOLS[app]] / PACKAGING / f'{app}-runtime.constraints.txt'
        if path.is_file() and '--hash=' in path.read_text(encoding='utf-8'):
            return path
        raise StepFailed('venv', f'{app}: no hash-locked requirements file (looked for {path}); '
                                 'pass --build-python with a prepared build venv')

    def venv(self):
        self.pythons, self.frozen = {}, {}
        locks = {} if self.build_python else {app: self.lock_file(app) for app in APPS}  # all found before any venv is made
        for app in APPS:
            python = self.build_python
            if python is None:
                folder = self.release / 'venv' / app
                self.call('venv', [self.python, '-I', '-m', 'venv', folder], log=f'venv-{app}')
                python = folder / 'Scripts' / 'python.exe'
                # The CI install (.github/workflows/desktop-windows.yml): hashes required, wheels only, nothing unlocked.
                self.call('venv', [python, '-m', 'pip', 'install', '--disable-pip-version-check', '--no-input', '--require-hashes',
                                   '--only-binary=:all:', '--no-deps', '-r', locks[app]], log=f'pip-install-{app}')
                self.call('venv', [python, '-m', 'pip', 'check'], log=f'pip-check-{app}')
            frozen = self.call('venv', [python, '-m', 'pip', 'freeze', '--all'], log=f'pip-freeze-{app}')
            self.pythons[app] = python
            self.frozen[app] = (f'build venv {python} pip freeze --all sha256 {hashlib.sha256(frozen.stdout.encode()).hexdigest()} '
                                f'({frozen.evidence})')

    def build(self):
        self.gates = {app: {} for app in APPS}
        self.native = {}
        self.installers = {}
        # Security and data gates first, on the pristine exports (before npm ci or pytest write into them).
        for app in APPS:
            self.gates[app]['security'] = gate(self.security(app))
            self.gates[app]['dataAllowlist'] = gate(self.data_allowlist(app))
        runtime_root = self.release / 'runtime'
        for app in APPS:
            native = ['--native-root', self.args.native_root] if self.args.native_root else []
            built = self.call('build', [self.pythons[app], self.export[TOOLS[app]] / PACKAGING / 'build_runtime.py', '--app', app,
                                        '--source', self.export[app], *native, '--build-root', self.release / 'build',
                                        '--runtime-root', runtime_root], cwd=self.export[TOOLS[app]], log=f'runtime-{app}')
            status_path = runtime_root / app / 'runtime-status.json'
            status = json.loads(status_path.read_text(encoding='utf-8'))
            if status.get('missingNativeRuntimes') != []:
                raise StepFailed('nativeAcceptance', f'{app}: missing native runtimes {status.get("missingNativeRuntimes")} '
                                                     '(pass --native-root)')
            self.native[app] = f'{built.evidence}; runtime-status.json sha256 {sha256(status_path)} missingNativeRuntimes []'
            self.gates[app]['redistribution'] = gate(self.redistribution(app, runtime_root / app / 'dependency-inventory.json'))
        tested, audited = {}, {}
        for tool in sorted(set(TOOLS.values())):  # once per client repository
            client = self.export[tool] / 'ops' / 'desktop' / 'client'
            tests_env = {**self.environ, 'DESKTOP_TEST_PYTHON': str(self.pythons[tool])}
            # pytest before npm ci, so it never collects anything under node_modules.
            tested[tool] = [self.call('tests', [self.pythons[tool], '-E', '-s', '-B', '-m', 'pytest', '-p', 'no:cacheprovider', '-q',
                                                'ops/desktop'], cwd=self.export[tool], log=f'pytest-ops-desktop-{tool}').evidence,
                            self.call('tests', ['npm', 'ci', '--no-fund'], cwd=client, log=f'npm-ci-{tool}').evidence,
                            self.call('tests', ['npm', 'test'], cwd=client, env=tests_env, log=f'npm-test-{tool}').evidence]
            audited[tool] = self.call('dependencies', ['npm', 'audit', '--omit=dev', '--audit-level=high'], cwd=client,
                                      log=f'npm-audit-{tool}').evidence
        for app in APPS:
            self.gates[app]['tests'] = gate('; '.join(tested[TOOLS[app]] + [self.frozen[app]]))
            self.gates[app]['dependencies'] = gate(audited[TOOLS[app]])
        build_env = {key: value for key, value in self.environ.items()
                     if key.upper() not in {'CSC_LINK', 'CSC_KEY_PASSWORD', 'WIN_CSC_LINK', 'WIN_CSC_KEY_PASSWORD', 'CSC_NAME'}}
        for app in APPS:
            tools = self.export[TOOLS[app]]
            # The hook accepts one fresh package per signing root (it stages its own NSIS copies there), so each app gets its
            # own; the dist root must lie inside it.
            signing_root = self.release / 'signing' / app
            signing_root.mkdir(parents=True)
            dist_root = signing_root / 'dist'
            env = {**build_env, 'DESKTOP_APP_ID': app, 'DESKTOP_RUNTIME_ROOT': str(runtime_root), 'DESKTOP_DIST_ROOT': str(dist_root),
                   'DESKTOP_SIGNING_ROOT': str(signing_root), 'DESKTOP_SIGNING_CERT_SHA1': THUMBPRINT,
                   'WINDOWS_PUBLISHER_NAME': self.publisher, 'DESKTOP_UPDATE_PROVIDER': 'github',
                   'DESKTOP_GITHUB_REPOSITORY': REPOSITORIES[app],
                   'DESKTOP_ACCESS_TRUST': str(tools / PACKAGING / 'desktop-access-trust.public.json')}
            self.call('build', ['npm', 'run', 'build', '--', '--publish', 'never'], cwd=tools / 'ops' / 'desktop' / 'client', env=env,
                      log=f'npm-build-{app}')
            installer = dist_root / app / f'{PRODUCTS[app]}-{self.version}-win-x64.exe'
            if not installer.is_file():
                raise StepFailed('build', f'{app}: electron-builder produced no {installer}')
            self.installers[app] = installer
            packaged = dist_root / app / 'win-unpacked' / 'resources' / 'runtime' / app
            smoke = self.python_tool('nativeAcceptance', app, 'smoke_backend.py', '--app', app, '--runtime', packaged,
                                     '--output', self.logs / f'smoke-{app}.json', log=f'smoke-{app}', python=self.pythons[app])
            self.native[app] += '; packaged backend smoke on empty data: ' + smoke.evidence

    def security(self, app):
        report = self.logs / f'security-{app}.json'
        root = self.tool(app, Path('ops') / 'security_gate.py')
        raw = self.call('security', [self.python, root / 'ops' / 'security_gate.py', 'export', '--target', self.export[app],
                                     '--report', report], cwd=root, log=f'security-gate-{app}', check=False)
        if not report.is_file():
            raise StepFailed('security', f'{app}: security_gate.py wrote no report ({raw.evidence})')
        if raw.returncode == 0:
            return f'security_gate.py export (gitleaks, data leak, exact secrets) on the {app} export: {raw.evidence}; report sha256 {sha256(report)}'
        if app == 'mentat' and raw.returncode == 1:
            # The one reviewed finding (desktop_source_review.py: a fixed localStorage key name); anything else blocks.
            review = self.logs / 'security-mentat-review.json'
            reviewed = self.python_tool('security', app, 'desktop_source_review.py', '--report', report, '--source', self.export[app],
                                        '--output', review, log='security-review-mentat', check=False,
                                        root=self.tool(app, PACKAGING / 'desktop_source_review.py'))
            if reviewed.returncode == 0:
                return (f'security_gate.py export on the mentat export: {raw.evidence}; its only finding is the reviewed '
                        f'mentat-pocket.html localStorage key name: {reviewed.evidence}; review sha256 {sha256(review)}')
            raise StepFailed('security', f'mentat: findings beyond the reviewed one ({reviewed.evidence})')
        raise StepFailed('security', f'{app}: security_gate.py export failed ({raw.evidence})')

    def data_allowlist(self, app):
        stage = self.release / 'stage'
        staged = self.call('dataAllowlist', [self.pythons[app], self.export[TOOLS[app]] / PACKAGING / 'build_runtime.py', '--app', app,
                                             '--source', self.export[app], '--stage-only', '--build-root', stage,
                                             '--runtime-root', self.release / 'runtime'], cwd=self.export[TOOLS[app]], log=f'stage-{app}')
        inventories = list((stage / app).glob('*/source-inventory.json'))
        if len(inventories) != 1:
            raise StepFailed('dataAllowlist', f'{app}: expected one source-inventory.json under {stage / app}')
        files = json.loads(inventories[0].read_text(encoding='utf-8'))
        denied = [name for name in files if DATABASE.search(name) or name.rsplit('/', 1)[-1].lower() in SECRET_NAMES]
        if denied:
            raise StepFailed('dataAllowlist', f'{app}: staged sources include databases or secret-named files: {denied[:5]}')
        return f'{staged.evidence}; source-inventory.json sha256 {sha256(inventories[0])} ({len(files)} files)'

    def redistribution(self, app, path):
        try:
            entries = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError) as error:
            raise StepFailed('redistribution', f'{app}: {path} is missing or unreadable') from error
        if not isinstance(entries, list) or not entries:
            raise StepFailed('redistribution', f'{app}: {path} lists no dependencies')
        # build_runtime.py records licenseExpression, license and licenseFiles; at least one must say something.
        unlicensed = [entry.get('name', '?') if isinstance(entry, dict) else '?' for entry in entries
                      if not isinstance(entry, dict) or not (str(entry.get('licenseExpression') or '').strip()
                                                             or str(entry.get('license') or '').strip() or entry.get('licenseFiles'))]
        if unlicensed:
            raise StepFailed('redistribution', f'{app}: no licence recorded for {", ".join(sorted(unlicensed)[:10])}')
        return f'dependency-inventory.json sha256 {sha256(path)}: {len(entries)} distributions, each with licence metadata'

    def sign(self):
        """The build's signing hook signed every app binary and the installer; verify the installer and the hook's receipt."""
        self.signatures = {}
        for app in APPS:
            installer = self.installers[app]
            signature = self.signature('sign', installer)
            if signature.get('Status') == 'NotSigned':
                raise StepFailed('sign', f'{installer} is NotSigned: the signing hook was not active in the build '
                                         f'(does {REPOSITORIES[TOOLS[app]]} ops/desktop/client/builder.cjs use {SIGNING_HOOK}?)')
            if (signature.get('Status') != 'Valid' or str(signature.get('Thumbprint', '')).upper() != THUMBPRINT
                    or signature.get('Timestamped') is not True or signature.get('Subject') != self.publisher):
                raise StepFailed('sign', f'{installer}: signature check failed {signature}')
            evidence = installer.with_name(installer.name + '.signatures.json')
            if not evidence.is_file():
                raise StepFailed('sign', f'{evidence} is missing: the signing hook did not complete its verification')
            receipt = json.loads(evidence.read_text(encoding='utf-8'))
            digest = sha256(installer)
            # The hook's own final verification of the installer must describe these bytes.
            current = [row for row in receipt.get('currentFiles') or [] if isinstance(row, dict)
                       and str(row.get('path', '')).lower() == str(installer).lower()]
            if (receipt.get('certificateThumbprint') != THUMBPRINT or len(current) != 1 or current[0].get('status') != 'Valid'
                    or current[0].get('sha256') != digest or current[0].get('timestamped') is not True):
                raise StepFailed('sign', f'{evidence} does not record a Valid, timestamped {THUMBPRINT} signature on these '
                                         f'installer bytes ({digest})')
            self.signatures[app] = gate(
                f'Get-AuthenticodeSignature Valid, {self.publisher}, thumbprint {THUMBPRINT}, timestamped; signed during '
                f'`npm run build` by {SIGNING_HOOK} at {REPOSITORIES[TOOLS[app]]}@{self.shas[TOOLS[app]]}; hook receipt '
                f'{evidence} sha256 {sha256(evidence)}: {len(receipt.get("files") or [])} signing records, installer sha256 '
                f'{digest} verified by the hook')

    def write_receipts(self):
        targets = [self.spec_path] + [self.receipts / f'{app}.json' for app in APPS]
        if any(path.exists() for path in targets):
            raise StepFailed('receipts', f'receipts or {self.spec_path.name} for {self.version} already exist')
        documents, packages = {}, {}
        for app in APPS:
            documents[app] = {
                'schemaVersion': 1, 'appId': app, 'version': self.version, 'platform': 'win32', 'arch': 'x64',
                'sha256': sha256(self.installers[app]), 'source': self.source(app), 'clientCommit': self.shas[TOOLS[app]],
                'gates': {name: self.gates[app][name] for name in GATES},
                'osSignature': self.signatures[app],
                'nativeAcceptance': gate(self.native[app]),
            }
            packages[app] = {'package': str(self.installers[app]), 'receipt': str(self.receipts / f'{app}.json')}
        self.spec = {'version': self.version, 'sequence': self.sequence, 'platform': 'win32', 'arch': 'x64',
                     'repositories': dict(REPOSITORIES), 'sourceRefs': {app: self.source(app) for app in APPS}, 'packages': packages}
        try:
            validate_spec(self.spec)
            repositories(self.spec)
        except Refused as error:
            raise StepFailed('receipts', f'release specification refused: {error}') from error
        self.receipts.mkdir(parents=True, exist_ok=True)
        for app in APPS:
            with open(self.receipts / f'{app}.json', 'x', encoding='utf-8') as stream:
                stream.write(json.dumps(documents[app], indent=2) + '\n')
        with open(self.spec_path, 'x', encoding='utf-8') as stream:
            stream.write(json.dumps(self.spec, indent=2) + '\n')

    def check(self):
        """What github_release.py prepare will verify, read from disk, without its ledger write (no sequence reserved)."""
        spec = json.loads(self.spec_path.read_text(encoding='utf-8'))
        store = Store(self.state)  # the constructor and verify_release_gates only read the state directory
        try:
            validate_spec(spec)
            repositories(spec)
            for app in APPS:
                installer = Path(spec['packages'][app]['package'])
                receipt = json.loads(Path(spec['packages'][app]['receipt']).read_text(encoding='utf-8'))
                target = {'appId': app, 'version': self.version, 'platform': 'win32', 'arch': 'x64',
                          'package': {'sha256': sha256(installer)}}
                store.verify_release_gates(receipt, target, installer)
                # github_release.prepare's advance rule, on its newest row for the app (a fresh build never matches that
                # row's bytes, so an equal sequence is a refusal here too).
                version, sequence = app_release(spec, app)
                row = self.ledger('SELECT sequence,version FROM prepared WHERE app=? AND platform=? AND arch=? '
                                  'ORDER BY sequence DESC LIMIT 1', (app, 'win32', 'x64'))
                if row and (sequence <= row[0] or tuple(map(int, version.split('.'))) <= tuple(map(int, row[1].split('.')))):
                    raise StepFailed('check', f'{app}: version {version} sequence {sequence} must advance beyond the last prepared '
                                              f'release (version {row[1]} sequence {row[0]})')
        except (Refused, subprocess.SubprocessError) as error:
            raise StepFailed('check', f'{error}') from error

    def manifest(self):
        bundle = self.release / 'bundle'
        if bundle.exists():
            raise StepFailed('manifest', f'{bundle} exists from an earlier --publish; remove it and rerun --publish '
                                         '(the same sequence reuses its stored signed manifests for identical bytes)')
        self.logs = self.release / 'logs'
        self.logs.mkdir(parents=True, exist_ok=True)
        self.release_tool('--spec', self.spec_path, '--output', bundle, log='github-release-prepare')
        for app in APPS:
            index = json.loads((bundle / app / 'release.json').read_text(encoding='utf-8'))
            if (not isinstance(index, dict) or (index.get('version'), index.get('sequence'), index.get('sourceRefs'))
                    != (self.version, self.spec['sequence'], self.spec['sourceRefs'])):
                raise StepFailed('manifest', f'{app} bundle release.json has another version, sequence or sourceRefs than '
                                             f'{self.spec_path}')
            self.release_tool('--verify-output', bundle / app, '--repository', REPOSITORIES[app], log=f'github-release-verify-{app}')

    def release_tool(self, *args, log, step='manifest'):
        tool = self.release / 'src' / 'melange' / PACKAGING / 'github_release.py'
        return self.call(step, [self.python, '-E', '-s', '-B', tool, '--state', self.state, *args],
                         cwd=self.release / 'src' / 'melange', log=log)

    def publish(self):
        notes = self.release / 'release-notes.md'
        notes.write_text(f'Desktop {self.version} (sequence {self.sequence}), built from each repository\'s main:\n\n'
                         + ''.join(f'- {PRODUCTS[app]}: {REPOSITORIES[app]}@{self.shas[app]}\n' for app in APPS), encoding='utf-8')
        downloads = self.release / 'verify-download'
        downloads.mkdir(exist_ok=True)
        # All-or-nothing as far as GitHub allows: checks, then verified drafts for every app, and only then the public edits.
        for app in APPS:  # read-only checks first, so a refusal leaves no draft behind
            repo, sha = REPOSITORIES[app], self.shas[app]
            visibility = self.call('publish', ['gh', 'repo', 'view', repo, '--json', 'visibility', '--jq', '.visibility'],
                                   log=f'gh-visibility-{app}').stdout.strip()
            if visibility != 'PUBLIC':
                raise StepFailed('publish', f'{repo} must be public (it is {visibility or "unknown"})')
            remote = self.call('publish', ['gh', 'api', f'repos/{repo}/commits/{sha}', '--jq', '.sha'], log=f'gh-commit-{app}')
            if remote.stdout.strip() != sha:
                raise StepFailed('publish', f'{sha} is not on {repo}')
            if self.git('publish', app, 'ls-remote', '--tags', 'origin', 'refs/tags/' + self.tag).stdout.strip():
                raise StepFailed('publish', f'{repo} already has {self.tag}')
            view = self.call('publish', ['gh', 'release', 'view', self.tag, '--repo', repo], log=f'gh-view-{app}', check=False)
            if view.returncode == 0:
                raise StepFailed('publish', f'{repo} already has a release or draft {self.tag}; delete it only if this command made it')
            if 'release not found' not in view.stderr.lower():  # gh's own words; anything else (auth, network) proves nothing
                raise StepFailed('publish', f'{repo}: gh release view {self.tag} failed, so an existing release cannot be ruled out: '
                                            f'{view.stderr.strip() or "no error text"}')
            self.release_tool('--verify-output', self.release / 'bundle' / app, '--repository', repo, log=f'publish-verify-{app}', step='publish')
        for app in APPS:
            repo, sha, bundle = REPOSITORIES[app], self.shas[app], self.release / 'bundle' / app
            self.call('publish', ['gh', 'release', 'create', self.tag, '--repo', repo, '--target', sha, '--draft',
                                  '--title', f'{PRODUCTS[app]} {self.version}', '--notes-file', notes], log=f'gh-create-{app}')
            # Never --clobber: a failed upload leaves the draft for review.
            self.call('publish', ['gh', 'release', 'upload', self.tag, *sorted(bundle.iterdir()), '--repo', repo], log=f'gh-upload-{app}')
            fresh = Path(tempfile.mkdtemp(prefix=app + '-', dir=downloads))
            self.call('publish', ['gh', 'release', 'download', self.tag, '--repo', repo, '--dir', fresh], log=f'gh-download-{app}')
            self.release_tool('--verify-output', fresh, '--repository', repo, log=f'download-verify-{app}', step='publish')
        for app in APPS:
            self.call('publish', ['gh', 'release', 'edit', self.tag, '--repo', REPOSITORIES[app], '--draft=false', '--latest'],
                      log=f'gh-publish-{app}')

    def summary(self, published):
        artifacts, gates = [], {}
        for app in APPS:
            receipt = json.loads((self.receipts / f'{app}.json').read_text(encoding='utf-8'))
            artifacts.append({'app': app, 'name': self.installers[app].name, 'sha256': receipt['sha256']})
            gates[app] = {name: receipt[name]['status'] if name in ('osSignature', 'nativeAcceptance') else receipt['gates'][name]['status']
                          for name in (*GATES, 'nativeAcceptance', 'osSignature')}
        return {'version': self.version, 'sequence': self.sequence, 'sources': {app: self.source(app) for app in APPS},
                'artifacts': artifacts, 'gates': gates, 'published': published}

    # ---------------------------------------------------------------- driver
    def step(self, name, action):
        try:
            return action()
        except StepFailed:
            raise
        except (OSError, ValueError, KeyError, TypeError, sqlite3.Error, tarfile.TarError) as error:
            raise StepFailed(name, f'{type(error).__name__}: {error}') from error

    def execute(self):
        self.step('local', self.local)
        self.step('sources', self.sources)
        self.step('version', self.version_step)
        if not self.resume:
            self.step('export', self.export_step)
            self.step('venv', self.venv)
            self.step('build', self.build)
            self.step('sign', self.sign)
            self.step('receipts', self.write_receipts)
            self.step('check', self.check)
        if self.args.publish:
            self.step('manifest', self.manifest)
            self.step('publish', self.publish)
        summary = self.step('summary', lambda: self.summary(bool(self.args.publish)))
        print(json.dumps(summary, indent=2))
        if self.args.publish:
            print(f'Published {self.tag} to ' + ', '.join(REPOSITORIES[app] for app in APPS) + '.')
        else:
            print(f'Dry run: no GitHub writes were made and no release sequence was reserved. Signed installers and receipts: '
                  f'{self.receipts}. Rerun with --publish and the same --output-root to publish them.')
        return summary


def parse(argv=None):
    environ = os.environ
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--melange', type=Path,
                        help=f'Melange checkout (env DESKTOP_MELANGE_SOURCE; default {SOURCES / "Melange"}, cloned if absent)')
    parser.add_argument('--mentat', type=Path,
                        help=f'Mentat checkout (env DESKTOP_MENTAT_SOURCE; default {SOURCES / "Mentat"}, cloned if absent)')
    parser.add_argument('--geo', type=Path,
                        help=f'Geo (Terrier) checkout (env DESKTOP_GEO_SOURCE; default {SOURCES / "Geo"}, cloned if absent)')
    parser.add_argument('--version', help='expected version; must equal ops/desktop/client/package.json on Melange and Mentat main')
    parser.add_argument('--sequence', type=int, help='release sequence (default: last prepared + 1)')
    parser.add_argument('--state', type=Path, default=DEFAULT_STATE, help='publisher state directory (default %(default)s)')
    parser.add_argument('--output-root', type=Path,
                        default=Path.home() / 'Documents' / f'Desktop-Installers-{dt.date.today().isoformat()}',
                        help='where receipts-<v>, release-spec-<v>.json and release-<v> are written (default %(default)s)')
    parser.add_argument('--native-root', type=Path, help='native runtimes passed to build_runtime.py')
    parser.add_argument('--build-python', type=Path, default=environ.get('DESKTOP_BUILD_PYTHON') or None,
                        help='one build venv python.exe for every app (env DESKTOP_BUILD_PYTHON; default: a hash-locked venv per app)')
    parser.add_argument('--publish', action='store_true', help='also publish to GitHub (otherwise no GitHub writes)')
    args = parser.parse_args(argv)
    args.default_sources = set()  # apps whose checkout is the default clone, which may be created
    for name, app in (('melange', 'melange'), ('mentat', 'mentat'), ('geo', 'terrier')):
        if getattr(args, name) is None:
            given = environ.get(f'DESKTOP_{name.upper()}_SOURCE')
            if not given:
                args.default_sources.add(app)
            setattr(args, name, Path(given) if given else SOURCES / REPOSITORIES[app].split('/')[1])
    for name in ('melange', 'mentat', 'geo', 'state', 'output_root', 'native_root', 'build_python'):
        if getattr(args, name) is not None:
            setattr(args, name, getattr(args, name).expanduser().absolute())
    return args


def main(argv=None, runner=run, environ=None, os_name=None):
    args = parse(argv)
    try:
        Release(args, runner=runner, environ=environ, os_name=os_name).execute()
        return 0
    except StepFailed as error:
        print(f"Release stopped at step '{error.step}': {error.message}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
