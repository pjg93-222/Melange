import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
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
        self.ignore_range = ignore_range
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                owner.requests.append((self.path, self.headers.get('Range')))
                if self.path == '/repos/x/y/releases?per_page=20':
                    return self.reply(200, json.dumps(owner.releases(app)).encode())
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
MEMBERS = {'Moneyball.html': REAL_PAGE, 'fec/surfaces/bulk.bin': os.urandom(5000)}


def test_newest_release_is_resumed_verified_extracted_and_then_a_no_op(roots):
    data, state = roots
    initialize_workspace(data)
    server = Server(build_release(MEMBERS), truncate_first=True)
    seen = []
    try:
        result = fetch.ensure_app_data('melange', data, state, 'x/y', api_base=server.base, progress=lambda **s: seen.append(s))
        downloads = [r for r in server.requests if r[0].endswith('.zip')]
        assert result['status'] == 'installed' and result['tag'] == NEWER and result['kept'] == []
        assert downloads == [('/dl/%s/data-1.zip' % NEWER, None), ('/dl/%s/data-1.zip' % NEWER, 'bytes=1000-')]
        assert (data / 'Moneyball.html').read_bytes() == REAL_PAGE
        assert (data / 'fec/surfaces/bulk.bin').read_bytes() == MEMBERS['fec/surfaces/bulk.bin']
        marker = json.loads((data / fetch.MARKER).read_text(encoding='utf-8'))
        assert marker['tag'] == NEWER and marker['manifestSha256'] == sha(server.assets['manifest.json']) and marker['extractedAt']
        assert not (state / 'data-download' / NEWER).exists()
        assert seen[-1]['phase'] == 'done' and any(s.get('phase') == 'downloading' for s in seen)
        count = len(server.requests)
        assert fetch.ensure_app_data('melange', data, state, 'x/y', api_base=server.base) == {'status': 'present', 'tag': NEWER}
        assert len(server.requests) == count
    finally:
        server.close()


def test_checksum_mismatch_aborts_without_extracting(roots):
    data, state = roots
    server = Server(build_release(MEMBERS, corrupt_sha=True))
    try:
        with pytest.raises(fetch.DataReleaseError, match='Checksum mismatch'):
            fetch.ensure_app_data('melange', data, state, 'x/y', api_base=server.base)
    finally:
        server.close()
    assert list(data.iterdir()) == []
    assert not any((state / 'data-download' / NEWER).iterdir())


def test_parent_directory_member_is_refused_before_anything_is_written(roots):
    data, state = roots
    server = Server(build_release({'Moneyball.html': REAL_PAGE, '../escape.txt': b'outside'}))
    try:
        with pytest.raises(fetch.DataReleaseError, match='unsafe'):
            fetch.ensure_app_data('melange', data, state, 'x/y', api_base=server.base)
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


def test_existing_user_files_are_kept(roots):
    data, state = roots
    (data / 'fec' / 'surfaces').mkdir(parents=True)
    (data / 'fec' / 'surfaces' / 'bulk.bin').write_bytes(b'user copy')
    server = Server(build_release(MEMBERS))
    try:
        result = fetch.ensure_app_data('melange', data, state, 'x/y', api_base=server.base)
    finally:
        server.close()
    assert result['kept'] == ['fec/surfaces/bulk.bin']
    assert (data / 'fec' / 'surfaces' / 'bulk.bin').read_bytes() == b'user copy'


def test_background_melange_progress_page_and_mentat_readme(roots, tmp_path):
    data, state = roots
    initialize_workspace(data)
    server = Server(build_release(MEMBERS))
    try:
        environment = {'DESKTOP_DATA_RELEASE_REPO': 'x/y', 'DESKTOP_DATA_RELEASE_API': server.base}
        fetch.launch('melange', data, state, environ=environment).join(30)
        status = json.loads((state / 'data-download' / 'status.json').read_text(encoding='utf-8'))
        assert status['phase'] == 'done' and status['bytesDone'] == status['bytesTotal'] > 0
        assert (data / 'Moneyball.html').read_bytes() == REAL_PAGE
        page = fetch.progress_page({'phase': 'downloading', 'bytesDone': 50, 'bytesTotal': 200})
        assert '25%' in page and 'http-equiv="refresh"' in page
        written = tmp_path / 'page.html'
        written.write_text(page, encoding='utf-8')
        assert fetch.is_bootstrap_page(written)
    finally:
        server.close()
    mentat_data, mentat_state = tmp_path / 'mdata', tmp_path / 'mstate'
    mentat_data.mkdir()
    (mentat_data / 'reports').mkdir()
    tag = 'data-mentat-2026-10-20'
    server = Server(build_release({'reports/a.txt': b'report'}, app='mentat', tag=tag), app='mentat', tag=tag)
    try:
        environment = {'DESKTOP_DATA_RELEASE_REPO': 'x/y', 'DESKTOP_DATA_RELEASE_API': server.base}
        fetch.launch('mentat', mentat_data, mentat_state, environ=environment).join(30)
    finally:
        server.close()
    assert (mentat_data / 'reports' / 'a.txt').read_bytes() == b'report'
    assert json.loads((mentat_data / fetch.MARKER).read_text(encoding='utf-8'))['tag'] == tag
    assert 'restart' in (mentat_data / 'reports' / 'README-first-run.txt').read_text(encoding='utf-8')


def test_backend_hook_never_blocks_startup(roots, monkeypatch, capsys):
    import desktop_backend
    data, state = roots
    monkeypatch.setenv('DESKTOP_DATA_RELEASE', 'off')
    assert desktop_backend.start_data_release('melange', data, state) is None
    monkeypatch.setattr(fetch, 'launch', lambda *a, **k: (_ for _ in ()).throw(OSError('offline')))
    assert desktop_backend.start_data_release('mentat', data, state, reports_root=data / 'reports') is None
    assert 'data release fetch not started' in capsys.readouterr().err


def test_state_members_land_in_the_state_root_and_user_files_are_kept(roots):
    data, state = roots
    (state / 'Melange').mkdir()
    (state / 'Melange' / 'mine.json').write_bytes(b'user state')
    members = {**MEMBERS, '__state__/Melange/staffer_network/a.sqlite': b'sqlite', '__state__/Melange/mine.json': b'release'}
    server = Server(build_release(members))
    try:
        result = fetch.ensure_app_data('melange', data, state, 'x/y', api_base=server.base)
    finally:
        server.close()
    assert result['kept'] == ['__state__/Melange/mine.json']
    assert (state / 'Melange' / 'staffer_network' / 'a.sqlite').read_bytes() == b'sqlite'
    assert (state / 'Melange' / 'mine.json').read_bytes() == b'user state'
    assert not (data / '__state__').exists() and (data / 'Moneyball.html').read_bytes() == REAL_PAGE


@pytest.mark.parametrize('name', ['__state__/data-download/x.zip', '__state__/Data-Download/x.zip', '__state__/../escape.txt'])
def test_unsafe_state_members_are_refused_before_anything_is_written(roots, name):
    data, state = roots
    server = Server(build_release({'Moneyball.html': REAL_PAGE, name: b'x'}))
    try:
        with pytest.raises(fetch.DataReleaseError, match='unsafe|download cache'):
            fetch.ensure_app_data('melange', data, state, 'x/y', api_base=server.base)
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
            fetch.ensure_app_data('melange', data, state, 'x/y', api_base=server.base)
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
        assert fetch.ensure_app_data('melange', data, state, 'x/y', api_base=server.base) == {'status': 'busy'}
        environment = {'DESKTOP_DATA_RELEASE_REPO': 'x/y', 'DESKTOP_DATA_RELEASE_API': server.base}
        fetch.launch('melange', data, state, environ=environment).join(30)
        assert server.requests == [] and not (state / 'data-download' / 'status.json').exists()
        assert (data / 'Moneyball.html').read_bytes() == welcome
        fetch._unlock(held)
        held = None
        assert fetch.ensure_app_data('melange', data, state, 'x/y', api_base=server.base)['status'] == 'installed'
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
        assert fetch.ensure_app_data('melange', data, state, 'x/y', api_base=server.base)['status'] == 'installed'
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
            fetch.ensure_app_data('melange', data, state, 'x/y', api_base=server.base)
        assert not [r for r in server.requests if r[0].endswith('.zip')] and list(data.iterdir()) == [] and seen
        monkeypatch.setattr(fetch, '_free_bytes', lambda path: 1 << 40)
        assert fetch.ensure_app_data('melange', data, state, 'x/y', api_base=server.base)['status'] == 'installed'
    finally:
        server.close()


def test_failed_extraction_leaves_no_partial_file(roots, monkeypatch):
    data, state = roots
    monkeypatch.setattr(fetch, '_replace', lambda source, target: (_ for _ in ()).throw(OSError(28, 'No space left on device')))
    server = Server(build_release(MEMBERS))
    try:
        with pytest.raises(OSError):
            fetch.ensure_app_data('melange', data, state, 'x/y', api_base=server.base)
    finally:
        server.close()
    assert not [p for p in data.rglob('*') if p.is_file()] and not (data / fetch.MARKER).exists()


def test_error_status_and_page_do_not_show_absolute_user_folders(roots, monkeypatch):
    from pathlib import Path
    data, state = roots
    initialize_workspace(data)

    def fail(*args, **kwargs):
        raise PermissionError(13, 'Access is denied', str(state / 'Melange' / 'x.sqlite'))
    monkeypatch.setattr(fetch, 'ensure_app_data', fail)
    fetch.start_background('melange', data, state, 'x/y').join(30)
    status = (state / 'data-download' / 'status.json').read_text(encoding='utf-8')
    page = (data / 'Moneyball.html').read_text(encoding='utf-8')
    for text in (status, page):
        assert 'Access is denied' in text and 'Melange' in text
        for folder in (str(state), str(Path.home()), Path.home().as_posix()):
            assert folder.lower() not in text.lower()
            assert folder.replace(os.sep, os.sep * 2).lower() not in text.lower()
    assert '&lt;state&gt;' in page


def test_server_that_ignores_range_restarts_the_part(roots):
    data, state = roots
    server = Server(build_release(MEMBERS), truncate_first=True, ignore_range=True)
    try:
        assert fetch.ensure_app_data('melange', data, state, 'x/y', api_base=server.base)['status'] == 'installed'
        assert [r[1] for r in server.requests if r[0].endswith('.zip')] == [None, 'bytes=1000-']
    finally:
        server.close()
    assert (data / 'fec/surfaces/bulk.bin').read_bytes() == MEMBERS['fec/surfaces/bulk.bin']
