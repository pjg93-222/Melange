"""Generated component transport fixtures only; production bootstrap stays disabled.

Private _ensure_component_data calls do not authorize an app/data release.
"""
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import threading
import zipfile

import pytest

import data_release_fetch as fetch
from melange_bootstrap import initialize_workspace

NEWER = 'data-melange-2026-10-20'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def build_release(members, app='melange', tag=NEWER, corrupt_sha=False):
    """One zip asset plus its manifest; members maps archive name -> bytes."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_STORED) as bundle:
        for name, data in members.items():
            bundle.writestr(name, data)
    archive = buffer.getvalue()
    manifest = {'schema': fetch.SCHEMA, 'app': app, 'tag': tag, 'created': '2026-10-20T00:00:00Z',
                'assets': [{'name': 'data-1.zip', 'bytes': len(archive), 'sha256': '0' * 64 if corrupt_sha else sha(archive)}],
                'files': [{'path': name, 'bytes': len(data), 'sha256': sha(data), 'asset': 'data-1.zip'} for name, data in members.items()],
                'excluded': []}
    return {'manifest.json': json.dumps(manifest).encode(), 'data-1.zip': archive}


class Server:
    def __init__(self, assets, app='melange', truncate_first=False, tag=NEWER, ignore_range=False):
        self.assets, self.requests, self.truncate_first, self.tag = assets, [], truncate_first, tag
        self.ignore_range, self.by_tag, self.tag_only = ignore_range, False, {}  # tag_only: served by tag, never listed
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                owner.requests.append((self.path, self.headers.get('Range')))
                if self.path == '/repos/x/y/releases?per_page=20':
                    return self.reply(200, json.dumps(owner.releases(app)).encode())
                if self.path.startswith('/repos/x/y/releases/tags/'):
                    owner.by_tag = True
                    requested = self.path.rsplit('/', 1)[-1]
                    found = owner.tag_only.get(requested) or next((r for r in owner.releases(app) if r['tag_name'] == requested), None)
                    return self.reply(200, json.dumps(found).encode()) if found else self.reply(404, b'missing')
                name = self.path.rsplit('/', 1)[-1]
                if not self.path.startswith('/dl/%s/' % owner.tag) or name not in owner.assets:
                    return self.reply(404, b'missing')
                body = owner.assets[name]
                if name.endswith('.zip') and owner.truncate_first:
                    owner.truncate_first = False
                    self.send_response(200)
                    self.send_header('Content-Length', str(len(body)))
                    self.end_headers()
                    self.wfile.write(body[:1000])
                    self.close_connection = True
                    return
                ranged = self.headers.get('Range')
                if ranged and not owner.ignore_range:
                    start = int(ranged.split('=')[1].rstrip('-'))
                    self.send_response(206)
                    self.send_header('Content-Range', 'bytes %d-%d/%d' % (start, len(body) - 1, len(body)))
                    return self.finish_body(body[start:])
                self.reply(200, body)

            def reply(self, code, body):
                self.send_response(code)
                self.finish_body(body)

            def finish_body(self, body):
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self.httpd = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.base = 'http://127.0.0.1:%d' % self.httpd.server_port
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def releases(self, app):
        def release(tag, when, draft=False):
            return {'tag_name': tag, 'draft': draft, 'published_at': when, 'assets': [
                {'name': name, 'browser_download_url': '%s/dl/%s/%s' % (self.base, tag, name)} for name in self.assets]}
        return [release('data-%s-2026-10-22' % app, '2026-10-22T00:00:00Z', draft=True),
                release('data-mentat-2026-10-21' if app == 'melange' else 'data-melange-2026-10-21', '2026-10-21T00:00:00Z'),
                release('data-%s-2026-10-01' % app, '2026-10-01T00:00:00Z'),
                release(self.tag, '2026-10-20T00:00:00Z')]

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


@pytest.fixture(autouse=True)
def no_retry_delay(monkeypatch):
    monkeypatch.setattr(fetch, 'RETRY_DELAY', 0)


@pytest.fixture
def roots(tmp_path):
    data, state = tmp_path / 'data', tmp_path / 'state'
    data.mkdir()
    state.mkdir()
    return data, state


REAL_PAGE = b'<html>real dashboard</html>'
MEMBERS = {'public/fixture.json': b'{"fixture":true}', 'fec/surfaces/bulk.bin': os.urandom(5000)}


def test_newest_release_is_resumed_verified_extracted_and_then_a_no_op(roots):
    data, state = roots
    initialize_workspace(data)
    server = Server(build_release(MEMBERS), truncate_first=True)
    seen = []
    try:
        result = fetch._ensure_component_data('melange', data, state, 'x/y', api_base=server.base, progress=lambda **s: seen.append(s))
        downloads = [r for r in server.requests if r[0].endswith('.zip')]
        assert result['status'] == 'component-extracted' and result['tag'] == NEWER and result['kept'] == []
        assert downloads == [('/dl/%s/data-1.zip' % NEWER, None), ('/dl/%s/data-1.zip' % NEWER, 'bytes=1000-')]
        assert (data / 'public' / 'fixture.json').read_bytes() == MEMBERS['public/fixture.json']
        assert (data / 'fec/surfaces/bulk.bin').read_bytes() == MEMBERS['fec/surfaces/bulk.bin']
        marker = json.loads((data / fetch.MARKER).read_text(encoding='utf-8'))
        assert marker['tag'] == NEWER and marker['manifestSha256'] == sha(server.assets['manifest.json']) and marker['extractedAt']
        assert not (state / 'data-download' / NEWER).exists()
        assert seen[-1]['phase'] == 'done' and any(s.get('phase') == 'downloading' for s in seen)
        count = len(server.requests)
        assert fetch._ensure_component_data('melange', data, state, 'x/y', api_base=server.base) == {'status': 'component-present', 'tag': NEWER}
        assert len(server.requests) == count
    finally:
        server.close()


def test_checksum_mismatch_aborts_without_extracting(roots):
    data, state = roots
    server = Server(build_release(MEMBERS, corrupt_sha=True))
    try:
        with pytest.raises(fetch.DataReleaseError, match='Checksum mismatch'):
            fetch._ensure_component_data('melange', data, state, 'x/y', api_base=server.base)
    finally:
        server.close()
    assert list(data.iterdir()) == []
    assert not any((state / 'data-download' / NEWER).iterdir())


def test_parent_directory_member_is_refused_before_anything_is_written(roots):
    data, state = roots
    server = Server(build_release({'public/fixture.json': MEMBERS['public/fixture.json'], '../escape.txt': b'outside'}))
    try:
        with pytest.raises(fetch.DataReleaseError, match='unsafe'):
            fetch._ensure_component_data('melange', data, state, 'x/y', api_base=server.base)
    finally:
        server.close()
    assert list(data.iterdir()) == [] and not (data.parent / 'escape.txt').exists()


@pytest.mark.parametrize('name', ['/etc/x', '\\x', 'C:/x', 'c:x', 'a/../b', 'a\\..\\b', '..', 'a//b', './a', 'CON', 'a/nul.txt',
                                  'COM1.json', 'a.json.', 'a/b /c', 'a?b', 'a\x01b'])
def test_unsafe_member_names(name):
    with pytest.raises(fetch.DataReleaseError):
        fetch.member_path(name)
    assert fetch.member_path('fec\\surfaces/a.json') == 'fec/surfaces/a.json'


def test_launch_skips_existing_data_disabled_and_https_only_by_default(roots, monkeypatch):
    data, state = roots
    (data / 'Moneyball.html').write_bytes(REAL_PAGE)
    assert fetch.launch('melange', data, state, environ={}) is None
    assert fetch.launch('terrier', data, state, environ={}) is None
    (data / 'Moneyball.html').unlink()
    assert fetch.launch('melange', data, state, environ={'DESKTOP_DATA_RELEASE': 'off'}) is None
    (data / 'reports').mkdir()
    (data / 'reports' / 'r.pdf').write_bytes(b'x')
    assert fetch.launch('mentat', data, state, environ={}) is None
    with pytest.raises(fetch.DataReleaseError, match='non-HTTPS'):
        fetch._open('http://127.0.0.1:1/x', 'a/b')


def test_mismatched_required_original_refuses_without_a_false_complete_marker(roots):
    data, state = roots
    target = data / 'fec' / 'surfaces' / 'bulk.bin'
    target.parent.mkdir(parents=True)
    target.write_bytes(b'user copy')
    server = Server(build_release(MEMBERS))
    try:
        with pytest.raises(fetch.DataReleaseError):
            fetch._ensure_component_data('melange', data, state, 'x/y', api_base=server.base)
    finally:
        server.close()
    assert target.read_bytes() == b'user copy'
    assert not (data / fetch.MARKER).exists() and not (data / 'public' / 'fixture.json').exists()



def test_production_entries_ignore_environment_and_refuse_before_all_io(roots, monkeypatch):
    data, state = roots
    def forbidden(*args, **kwargs):
        raise AssertionError('Disabled production bootstrap must not prepare paths, lock, fetch or start a thread')
    monkeypatch.setattr(fetch, 'Path', forbidden)
    monkeypatch.setattr(fetch, '_lock', forbidden)
    monkeypatch.setattr(fetch, '_open', forbidden)
    monkeypatch.setattr(fetch.threading, 'Thread', forbidden)
    for app in ('melange', 'mentat', 'terrier'):
        assert fetch.ensure_app_data(app, data, state, 'untrusted/repo', api_base='http://untrusted.invalid') == {'status': 'unsupported'}
        assert fetch.start_background(app, data, state, 'untrusted/repo', api_base='http://untrusted.invalid') is None
        assert fetch.launch(app, data, state, environ={'DESKTOP_DATA_RELEASE':'on', 'DESKTOP_DATA_RELEASE_REPO':'untrusted/repo', 'DESKTOP_DATA_RELEASE_API':'http://untrusted.invalid'}) is None
    assert list(data.iterdir()) == [] and list(state.iterdir()) == []
    with pytest.raises(TypeError):
        fetch._COMPILED_PUBLIC_PLANS['melange'] = {'approved':True}
    monkeypatch.setattr(fetch, '_COMPILED_PUBLIC_PLANS', {'melange': {'approved': True, 'complete': True}})
    with pytest.raises(fetch.DataReleaseError): fetch.ensure_app_data('melange', data, state, 'untrusted/repo')
    with pytest.raises(fetch.DataReleaseError): fetch.start_background('melange', data, state, 'untrusted/repo')
    with pytest.raises(fetch.DataReleaseError): fetch.launch('melange', data, state)



def test_backend_hook_never_blocks_startup(roots, monkeypatch, capsys):
    import desktop_backend
    data, state = roots
    monkeypatch.setenv('DESKTOP_DATA_RELEASE', 'off')
    assert desktop_backend.start_data_release('melange', data, state) is None
    monkeypatch.setattr(fetch, 'launch', lambda *a, **k: (_ for _ in ()).throw(OSError('offline')))
    assert desktop_backend.start_data_release('mentat', data, state, reports_root=data / 'reports') is None
    assert 'data release fetch not started' in capsys.readouterr().err


@pytest.mark.parametrize('relative', ['__state__/Melange/public.sqlite', '__state__/accounts.sqlite3', 'accounts.sqlite3', 'Moneyball.html', 'public/code.js'])
def test_state_account_and_code_members_are_never_component_inputs(roots, relative):
    data, state = roots
    part = state / 'fixture.zip'
    raw = b'generated fixture only'
    with zipfile.ZipFile(part, 'w') as bundle:
        bundle.writestr(relative, raw)
    with pytest.raises(fetch.DataReleaseError, match='Code, account or state'):
        fetch._extract([(part, 'fixture.zip')], data, state, {relative:{'path':relative, 'bytes':len(raw), 'sha256':sha(raw)}}, 'melange')
    assert list(data.iterdir()) == [] and not (state / 'accounts.sqlite3').exists()



@pytest.mark.parametrize('name', ['__state__/data-download/x.zip', '__state__/Data-Download/x.zip', '__state__/../escape.txt'])
def test_unsafe_state_members_are_refused_before_anything_is_written(roots, name):
    data, state = roots
    server = Server(build_release({'public/fixture.json': MEMBERS['public/fixture.json'], name: b'x'}))
    try:
        with pytest.raises(fetch.DataReleaseError, match='unsafe|state'):
            fetch._ensure_component_data('melange', data, state, 'x/y', api_base=server.base)
    finally:
        server.close()
    assert list(data.iterdir()) == [] and not (state.parent / 'escape.txt').exists()


def edited_release(members, edit):
    release = build_release(members)
    manifest = json.loads(release['manifest.json'])
    edit(manifest)
    release['manifest.json'] = json.dumps(manifest).encode()
    return release


@pytest.mark.parametrize('edit, message', [
    (lambda m: m['files'].append({'path': 'fec/missing.bin', 'bytes': 1, 'sha256': '0' * 64, 'asset': 'data-1.zip'}), 'lack 1 file'),
    (lambda m: m['files'].append({**m['files'][1], 'path': 'FEC/Surfaces/BULK.bin'}), 'twice'),
    (lambda m: m['files'].append(dict(m['files'][1])), 'twice'),
])
def test_manifest_and_archive_must_list_the_same_files(roots, edit, message):
    data, state = roots
    server = Server(edited_release(MEMBERS, edit))
    try:
        with pytest.raises(fetch.DataReleaseError, match=message):
            fetch._ensure_component_data('melange', data, state, 'x/y', api_base=server.base)
    finally:
        server.close()
    assert list(data.iterdir()) == []


def test_member_repeated_inside_the_archive_is_refused(roots):
    data, state = roots
    part = state / 'p.zip'
    with zipfile.ZipFile(part, 'w') as bundle:
        bundle.writestr('a.txt', b'one')
        with pytest.warns(UserWarning):
            bundle.writestr('a.txt', b'one')
    with pytest.raises(fetch.DataReleaseError, match='more than once'):
        fetch._extract([(part, 'p.zip')], data, state, {'a.txt': {'path': 'a.txt', 'bytes': 3, 'sha256': sha(b'one')}}, 'melange')
    assert list(data.iterdir()) == []


def test_redirects_must_stay_on_https_unless_testing():
    import urllib.request
    request = urllib.request.Request('https://github.com/x/y/releases/download/t/a.zip')
    for target in ('http://objects.example/a.zip', 'ftp://objects.example/a.zip'):
        with pytest.raises(fetch.DataReleaseError, match='non-HTTPS'):
            fetch._HttpsRedirects(False).redirect_request(request, None, 302, 'Found', {}, target)
    assert fetch._HttpsRedirects(False).redirect_request(request, None, 302, 'Found', {}, 'https://objects.example/a.zip').full_url == 'https://objects.example/a.zip'
    assert fetch._HttpsRedirects(True).redirect_request(request, None, 302, 'Found', {}, 'http://127.0.0.1/a.zip') is not None
    with pytest.raises(fetch.DataReleaseError, match='non-HTTPS'):
        fetch._HttpsRedirects(True).redirect_request(request, None, 302, 'Found', {}, 'ftp://127.0.0.1/a.zip')


def test_second_launch_while_a_download_runs_is_busy_and_touches_nothing(roots):
    data, state = roots
    initialize_workspace(data)
    welcome = (data / 'Moneyball.html').read_bytes()
    server = Server(build_release(MEMBERS))
    held = fetch._lock(state / 'data-download' / '.lock')
    try:
        assert held is not None
        assert fetch._ensure_component_data('melange', data, state, 'x/y', api_base=server.base) == {'status': 'busy'}
        environment = {'DESKTOP_DATA_RELEASE_REPO': 'x/y', 'DESKTOP_DATA_RELEASE_API': server.base}
        assert fetch.launch('melange', data, state, environ=environment) is None
        assert server.requests == [] and not (state / 'data-download' / 'status.json').exists()
        assert (data / 'Moneyball.html').read_bytes() == welcome
        fetch._unlock(held)
        held = None
        assert fetch._ensure_component_data('melange', data, state, 'x/y', api_base=server.base)['status'] == 'component-extracted'
    finally:
        if held:
            fetch._unlock(held)
        server.close()


def test_interrupted_download_of_an_older_tag_is_removed(roots):
    data, state = roots
    old = state / 'data-download' / 'data-melange-2026-01-01'
    old.mkdir(parents=True)
    (old / 'melange-data-part1.zip').write_bytes(b'x' * 100)
    server = Server(build_release(MEMBERS))
    try:
        assert fetch._ensure_component_data('melange', data, state, 'x/y', api_base=server.base)['status'] == 'component-extracted'
    finally:
        server.close()
    assert not old.exists() and not (state / 'data-download' / NEWER).exists()


def test_too_little_disk_space_stops_before_downloading(roots, monkeypatch):
    data, state = roots
    seen = []
    monkeypatch.setattr(fetch, '_free_bytes', lambda path: (seen.append(path), fetch.SPACE_MARGIN + 100)[1])
    server = Server(build_release(MEMBERS))
    try:
        with pytest.raises(fetch.DataReleaseError, match='Not enough free disk space'):
            fetch._ensure_component_data('melange', data, state, 'x/y', api_base=server.base)
        assert not [r for r in server.requests if r[0].endswith('.zip')] and list(data.iterdir()) == [] and seen
        monkeypatch.setattr(fetch, '_free_bytes', lambda path: 1 << 40)
        assert fetch._ensure_component_data('melange', data, state, 'x/y', api_base=server.base)['status'] == 'component-extracted'
    finally:
        server.close()


def test_failed_extraction_leaves_no_partial_file(roots, monkeypatch):
    data, state = roots
    monkeypatch.setattr(fetch, '_replace', lambda source, target, **options: (_ for _ in ()).throw(OSError(28, 'No space left on device')))
    server = Server(build_release(MEMBERS))
    try:
        with pytest.raises(OSError):
            fetch._ensure_component_data('melange', data, state, 'x/y', api_base=server.base)
    finally:
        server.close()
    assert not [p for p in data.rglob('*') if p.is_file()] and not (data / fetch.MARKER).exists()


def test_error_redaction_helper_preserves_fixed_labels(roots):
    from pathlib import Path
    data, state = roots
    error = 'cannot read ' + str(state / 'private.fixture') + ' or ' + str(data / 'public.fixture')
    text = fetch._redact(error, data, state)
    assert '<state>' in text and '<data>' in text
    assert str(state) not in text and str(data) not in text



def test_server_that_ignores_range_restarts_the_part(roots):
    data, state = roots
    server = Server(build_release(MEMBERS), truncate_first=True, ignore_range=True)
    try:
        assert fetch._ensure_component_data('melange', data, state, 'x/y', api_base=server.base)['status'] == 'component-extracted'
        assert [r[1] for r in server.requests if r[0].endswith('.zip')] == [None, 'bytes=1000-']
    finally:
        server.close()
    assert (data / 'fec/surfaces/bulk.bin').read_bytes() == MEMBERS['fec/surfaces/bulk.bin']


def test_interrupted_mentat_extraction_resumes_at_the_next_launch(roots, monkeypatch):
    data, state = roots
    tag = 'data-mentat-2026-10-20'
    members = {'app-data/m.bin': b'model', 'reports/a.txt': b'report a', 'reports/b.txt': b'report b'}
    real_replace = fetch._replace

    def fail_on_b(source, target, **options):
        if target.name == 'b.txt':
            raise OSError('app closed')
        return real_replace(source, target, **options)
    server = Server(build_release(members, app='mentat', tag=tag), app='mentat', tag=tag)
    try:
        monkeypatch.setattr(fetch, '_replace', fail_on_b)
        with pytest.raises(OSError):
            fetch._ensure_component_data('mentat', data, state, 'x/y', api_base=server.base)
        assert not (data / 'reports' / 'a.txt').exists() and not (data / fetch.MARKER).exists()
        assert (state / 'data-download' / fetch.EXTRACTING).is_file()
        monkeypatch.setattr(fetch, '_replace', real_replace)
        environment = {'DESKTOP_DATA_RELEASE_REPO': 'x/y', 'DESKTOP_DATA_RELEASE_API': server.base}
        assert fetch.launch('mentat', data, state, environ=environment) is None
        assert fetch._ensure_component_data('mentat', data, state, 'x/y', api_base=server.base)['status'] == 'component-extracted'
    finally:
        server.close()
    assert (data / 'reports' / 'b.txt').read_bytes() == b'report b'
    assert json.loads((data / fetch.MARKER).read_text(encoding='utf-8'))['tag'] == tag
    assert not (state / 'data-download' / fetch.EXTRACTING).exists()
    (data / fetch.MARKER).unlink()
    assert fetch.launch('mentat', data, state, environ={}) is None  # finished: a non-empty reports/ is the user's again


def test_interrupted_extraction_resumes_its_own_release_not_a_newer_one(roots, monkeypatch):
    data, state = roots
    tag, newer = 'data-mentat-2026-10-19', 'data-mentat-2026-10-25'
    members = {'reports/a.txt': b'report a', 'reports/b.txt': b'report b'}
    real_replace = fetch._replace

    def fail_on_b(source, target, **options):
        if target.name == 'b.txt':
            raise OSError('app closed')
        return real_replace(source, target, **options)
    server = Server(build_release(members, app='mentat', tag=tag), app='mentat', tag=tag)
    listed = server.releases('mentat')
    newest = {'tag_name': newer, 'draft': False, 'published_at': '2026-10-25T00:00:00Z', 'assets': [
        {'name': name, 'browser_download_url': '%s/dl/%s/%s' % (server.base, newer, name)} for name in server.assets]}
    try:
        monkeypatch.setattr(fetch, '_replace', fail_on_b)
        with pytest.raises(OSError):
            fetch._ensure_component_data('mentat', data, state, 'x/y', api_base=server.base)
        monkeypatch.setattr(fetch, '_replace', real_replace)
        server.releases = lambda app: [newest]  # the interrupted release was withdrawn: stop, do not mix releases
        with pytest.raises(fetch.DataReleaseError, match='no longer published'):
            fetch._ensure_component_data('mentat', data, state, 'x/y', api_base=server.base)
        assert not (data / 'reports' / 'b.txt').exists() and not (data / fetch.MARKER).exists()
        server.by_tag, server.tag_only = False, {tag: next(r for r in listed if r['tag_name'] == tag)}  # off the listing
        result = fetch._ensure_component_data('mentat', data, state, 'x/y', api_base=server.base)
        assert server.by_tag  # found by tag, so 20 newer releases cannot push it off the first page
    finally:
        server.close()
    assert result['status'] == 'component-extracted' and result['tag'] == tag
    assert (data / 'reports' / 'b.txt').read_bytes() == b'report b'
    assert json.loads((data / fetch.MARKER).read_text(encoding='utf-8'))['tag'] == tag
    assert not (state / 'data-download' / fetch.EXTRACTING).exists()


def two_asset_release(first, second):
    """data-1.zip holds fec/a.bin, data-2.zip holds fec/b.bin; one manifest lists both."""
    assets, files = {}, []
    for name, (path, data) in (('data-1.zip', ('fec/a.bin', first)), ('data-2.zip', ('fec/b.bin', second))):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_STORED) as bundle:
            bundle.writestr(path, data)
        assets[name] = buffer.getvalue()
        files.append({'path': path, 'bytes': len(data), 'sha256': sha(data), 'asset': name})
    manifest = {'schema': fetch.SCHEMA, 'app': 'melange', 'tag': NEWER, 'created': '2026-10-20T00:00:00Z', 'files': files, 'excluded': [],
                'assets': [{'name': n, 'bytes': len(b), 'sha256': sha(b)} for n, b in assets.items()]}
    return {'manifest.json': json.dumps(manifest).encode(), **assets}


def test_resume_refuses_a_manifest_replaced_under_the_same_tag(roots, monkeypatch):
    data, state = roots
    real_replace = fetch._replace

    def fail_on_b(source, target, **options):
        if target.name == 'b.bin':
            raise OSError('app closed')
        return real_replace(source, target, **options)
    server = Server(two_asset_release(b'generation A one', b'generation A two'))
    try:
        monkeypatch.setattr(fetch, '_replace', fail_on_b)
        with pytest.raises(OSError):
            fetch._ensure_component_data('melange', data, state, 'x/y', api_base=server.base)
        monkeypatch.setattr(fetch, '_replace', real_replace)
        assert not (data / 'fec' / 'a.bin').exists() and not (data / 'fec' / 'b.bin').exists()
        record = json.loads((state / 'data-download' / fetch.EXTRACTING).read_text(encoding='utf-8'))
        assert record == {'tag': NEWER, 'manifestSha256': sha(server.assets['manifest.json'])}
        before = {p: p.read_bytes() for p in (data.parent).rglob('*') if p.is_file()}
        server.assets.clear()
        server.assets.update(two_asset_release(b'generation B one', b'generation B two'))  # republished under the same tag
        server.requests.clear()
        seen = []
        result = fetch._ensure_component_data('melange', data, state, 'x/y', api_base=server.base, progress=lambda **s: seen.append(s))
    finally:
        server.close()
    assert result == {'status': 'error', 'reason': 'manifest_changed', 'tag': NEWER}
    assert seen[-1]['phase'] == 'error' and 'manifest_changed' in seen[-1]['error']
    assert not [r for r in server.requests if r[0].endswith('.zip')]
    assert {p: p.read_bytes() for p in (data.parent).rglob('*') if p.is_file()} == before  # nothing further written
    assert not (data / fetch.MARKER).exists()


def component_archive(root, members):
    part = root / 'preservation-fixture.zip'
    with zipfile.ZipFile(part, 'w') as bundle:
        for name, raw in members.items(): bundle.writestr(name, raw)
    files = {name:{'path':name, 'bytes':len(raw), 'sha256':sha(raw)} for name, raw in members.items()}
    return [(part, part.name)], files


def test_predictable_legacy_temp_hardlink_never_truncates_original(roots):
    data, state = roots
    private = state / 'private-account.fixture'; private.write_bytes(b'original fixture')
    os.link(private, data / 'fresh.bin.data-release-part')
    archives, files = component_archive(state, {'fresh.bin':b'public fixture'})
    assert fetch._extract(archives, data, state, files, 'melange') == (1, [])
    assert private.read_bytes() == b'original fixture' and private.stat().st_nlink == 2
    assert (data / 'fresh.bin.data-release-part').read_bytes() == b'original fixture'


def test_late_original_target_is_preserved_and_cannot_report_success(roots, monkeypatch):
    data, state = roots
    archives, files = component_archive(state, {'fresh.bin':b'public fixture'})
    real = fetch._replace
    def late(source, target, **options):
        target.write_bytes(b'late original user file')
        return real(source, target, **options)
    monkeypatch.setattr(fetch, '_replace', late)
    with pytest.raises(FileExistsError): fetch._extract(archives, data, state, files, 'melange')
    assert (data / 'fresh.bin').read_bytes() == b'late original user file'
    assert not list(data.glob('.melange-data-*'))


def test_foreign_replacement_of_owned_temporary_is_never_removed_or_installed(roots, monkeypatch):
    data, state = roots
    archives, files = component_archive(state, {'fresh.bin':b'public fixture'})
    real = fetch._replace
    foreign = []
    def replaced(source, target, **options):
        before = source.stat()
        other = source.with_name(source.name + '.foreign')
        other.write_bytes(b'foreign temporary replacement')
        os.replace(other, source)  # Distinct inode allocated before the original is released.
        assert (source.stat().st_dev, source.stat().st_ino) != (before.st_dev, before.st_ino)
        foreign.append(source)
        return real(source, target, **options)
    monkeypatch.setattr(fetch, '_replace', replaced)
    with pytest.raises(fetch.DataReleaseError): fetch._extract(archives, data, state, files, 'melange')
    assert foreign[0].read_bytes() == b'foreign temporary replacement'
    assert not (data / 'fresh.bin').exists()


@pytest.mark.parametrize('failure_at', ['verification', 'source_unlink'])
def test_post_link_failure_rolls_back_owned_names_and_allows_retry(roots, monkeypatch, failure_at):
    data, state = roots
    archives, files = component_archive(state, {'fresh.bin': b'public fixture'})
    error, failed = OSError('injected post-link failure'), []
    checked, unlink = fetch._checked_file, Path.unlink
    def verify(path, entry, identity=None, **options):
        if failure_at == 'verification' and Path(path).name == 'fresh.bin' and options.get('links') == 2 and not failed:
            failed.append(True)
            raise error
        return checked(path, entry, identity, **options)
    def remove(path, *args, **options):
        if failure_at == 'source_unlink' and path.name.startswith('.melange-data-') and path.stat().st_nlink == 2 and not failed:
            failed.append(True)
            raise error
        return unlink(path, *args, **options)
    with monkeypatch.context() as patch:
        patch.setattr(fetch, '_checked_file', verify)
        patch.setattr(Path, 'unlink', remove)
        with pytest.raises(OSError) as raised:
            fetch._extract(archives, data, state, files, 'melange')
        assert raised.value is error and failed
    assert not (data / 'fresh.bin').exists() and not list(data.glob('.melange-data-*'))
    assert fetch._extract(archives, data, state, files, 'melange') == (1, [])
    assert (data / 'fresh.bin').read_bytes() == b'public fixture'


def test_recovery_record_post_link_failure_preserves_exception_and_can_retry(roots, monkeypatch):
    data, state = roots
    record = state / 'fixture-record.json'
    error, failed, unlink = PermissionError('injected sharing violation'), [], Path.unlink
    def remove(path, *args, **options):
        if path.name.startswith('.melange-data-') and path.stat().st_nlink == 2 and not failed:
            failed.append(True)
            raise error
        return unlink(path, *args, **options)
    with monkeypatch.context() as patch:
        patch.setattr(Path, 'unlink', remove)
        with pytest.raises(PermissionError) as raised:
            fetch._atomic_write(record, '{"fixture":true}')
        assert raised.value is error and failed
    assert not record.exists() and not list(state.glob('.melange-data-*'))
    fetch._atomic_write(record, '{"fixture":true}')
    assert record.read_bytes() == b'{"fixture":true}'


def test_completed_temporary_in_place_change_survives_failure_cleanup(roots, monkeypatch):
    data, state = roots
    archives, files = component_archive(state, {'fresh.bin': b'public fixture'})
    changed, error = [], OSError('injected refusal after foreign change')
    def refuse(source, target, **options):
        before = source.stat()
        source.write_bytes(b'x' * before.st_size)
        os.utime(source, ns=(before.st_atime_ns, before.st_mtime_ns))
        changed.append((source, fetch._path_stamp(source)))
        raise error
    monkeypatch.setattr(fetch, '_replace', refuse)
    with pytest.raises(OSError) as raised:
        fetch._extract(archives, data, state, files, 'melange')
    assert raised.value is error and not (data / 'fresh.bin').exists()
    assert changed[0][0].read_bytes() == b'x' * len(b'public fixture')
    assert fetch._path_stamp(changed[0][0]) == changed[0][1]


@pytest.mark.parametrize('change_bytes', [False, True])
def test_changed_linked_stage_is_preserved_after_completed_verification(roots, monkeypatch, change_bytes):
    data, state = roots
    archives, files = component_archive(state, {'fresh.bin': b'public fixture'})
    error, changed, unlink = OSError('injected unlink refusal after mutation'), [], Path.unlink
    def remove(path, *args, **options):
        if path.name.startswith('.melange-data-') and path.stat().st_nlink == 2 and not changed:
            before = path.stat()
            raw = b'x' * before.st_size if change_bytes else path.read_bytes()
            path.write_bytes(raw)
            os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
            changed.append((path, raw, fetch._path_stamp(path, links=2)))
            raise error
        return unlink(path, *args, **options)
    monkeypatch.setattr(Path, 'unlink', remove)
    with pytest.raises(OSError) as raised:
        fetch._extract(archives, data, state, files, 'melange')
    assert raised.value is error
    stage, raw, stamp = changed[0]
    assert stage.read_bytes() == (data / 'fresh.bin').read_bytes() == raw
    assert fetch._path_stamp(stage, links=2) == stamp and stage.stat().st_nlink == 2


def test_changed_published_member_is_preserved_during_later_failure_rollback(roots, monkeypatch):
    data, state = roots
    archives, files = component_archive(state, {'a.bin': b'first fixture', 'z.bin': b'later fixture'})
    real, changed, error = fetch._replace, [], OSError('injected later publication failure')
    def fail_later(source, target, **options):
        if target.name == 'z.bin':
            first = data / 'a.bin'
            before = first.stat()
            first.write_bytes(first.read_bytes())
            os.utime(first, ns=(before.st_atime_ns, before.st_mtime_ns))
            changed.append(fetch._path_stamp(first))
            raise error
        return real(source, target, **options)
    monkeypatch.setattr(fetch, '_replace', fail_later)
    with pytest.raises(OSError) as raised:
        fetch._extract(archives, data, state, files, 'melange')
    assert raised.value is error and not (data / 'z.bin').exists()
    assert (data / 'a.bin').read_bytes() == b'first fixture'
    assert fetch._path_stamp(data / 'a.bin') == changed[0]
    assert not list(data.glob('.melange-data-*'))


def test_hardlinked_or_reparse_temporary_is_never_cleaned_as_owned(roots, monkeypatch):
    data, state = roots
    archives, files = component_archive(state, {'fresh.bin':b'public fixture'})
    real = fetch._replace
    kept = []
    def linked(source, target, **options):
        os.link(source, state / 'foreign-link.fixture'); kept.append(source)
        return real(source, target, **options)
    monkeypatch.setattr(fetch, '_replace', linked)
    with pytest.raises(fetch.DataReleaseError): fetch._extract(archives, data, state, files, 'melange')
    assert kept[0].exists() and kept[0].stat().st_nlink == 2
    assert not (data / 'fresh.bin').exists()


def test_later_member_checksum_failure_never_publishes_the_first_member(roots):
    data, state = roots
    archives, files = component_archive(state, {'a.bin':b'first', 'z.bin':b'second'})
    files['z.bin']['sha256'] = '0' * 64
    with pytest.raises(fetch.DataReleaseError): fetch._extract(archives, data, state, files, 'mentat')
    assert list(data.iterdir()) == []


def test_existing_welcome_is_preserved_even_when_download_claims_to_replace_it(roots):
    data, state = roots
    initialize_workspace(data); before = (data / 'Moneyball.html').read_bytes()
    archives, files = component_archive(state, {'Moneyball.html':b'<script>fixture only</script>'})
    with pytest.raises(fetch.DataReleaseError): fetch._extract(archives, data, state, files, 'melange')
    assert (data / 'Moneyball.html').read_bytes() == before and not (data / fetch.MARKER).exists()


def directory_alias(path, outside):
    if os.name == 'nt':
        import subprocess
        result = subprocess.run(['cmd.exe', '/c', 'mklink', '/J', str(path), str(outside)],
            capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        assert result.returncode == 0, result.stderr.decode(errors='replace')
    else:
        path.symlink_to(outside, target_is_directory=True)


def test_actual_reparse_directory_never_redirects_a_component_write(roots, tmp_path):
    data, state = roots
    outside = tmp_path / 'unrelated'; outside.mkdir()
    sentinel = outside / 'original.fixture'; sentinel.write_bytes(b'preserve original')
    directory_alias(data / 'public', outside)
    archives, files = component_archive(state, {'public/fresh.bin': b'public fixture'})
    with pytest.raises(fetch.DataReleaseError): fetch._extract(archives, data, state, files, 'melange')
    assert sentinel.read_bytes() == b'preserve original'
    assert sorted(path.name for path in outside.iterdir()) == ['original.fixture']


def test_actual_reparse_temporary_replacement_is_preserved(roots, tmp_path, monkeypatch):
    data, state = roots
    outside = tmp_path / 'unrelated'; outside.mkdir()
    sentinel = outside / 'original.fixture'; sentinel.write_bytes(b'preserve original')
    archives, files = component_archive(state, {'fresh.bin': b'public fixture'})
    real, foreign = fetch._replace, []
    def replaced(source, target, **options):
        source.unlink(); directory_alias(source, outside); foreign.append(source)
        return real(source, target, **options)
    monkeypatch.setattr(fetch, '_replace', replaced)
    with pytest.raises(fetch.DataReleaseError): fetch._extract(archives, data, state, files, 'melange')
    assert foreign[0].is_dir() and not (data / 'fresh.bin').exists()
    assert sentinel.read_bytes() == b'preserve original'
