"""Brand-new-tester round trip against ONE publisher: request -> approve -> activate -> status -> revoke.

Pure stdlib. The TLS pin (SPKI sha256 from the trust descriptor) is checked on every recipient connection, as
access-client.cjs does. The administrator side drives the real loopback dashboard routes with its one-time
session bootstrap, so nothing here uses an admin route over the recipient listener.

  python auth_roundtrip.py --origin https://127.0.0.1:38444 --trust trust.json --dashboard STATE_DIR
  ... --invite-code ABCD-EFGH-JKMN-PQRS   send a code (a junk value is fine too)
  ... --issue-invite                      issue a 1-use invite, use it, then try to reuse it (expect 403)
  ... --expect-request 403                the first POST should be refused with this status; stop there
  ... --deny-only                         request, then deny instead of approving (gate-off check)
  ... --allow-live --display-name "CLAUDE TEST ..."   the only way past the live-server refusal

--dashboard is a state directory (the dashboard is started in-process on a free loopback port, as
`access-dashboard` would, against the same sqlite files; its serverId must match --trust) or a running loopback
dashboard URL that carries its one-time `#bootstrap=...` fragment (counted as live: it needs --allow-live). Exit 0 only if every status code was the expected one AND cleanup
left none of this run's requests pending/approved, grants active or invite usable. Cleanup (deny, revoke,
invite-revoke) runs after every outcome, failures included. Every HTTP call prints its elapsed ms.
"""
import argparse
import base64
import hashlib
import http.client
import json
import secrets
import ssl
import sys
import threading
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit

DISPLAY = 'CLAUDE TEST 2026-10-21 - ignore'
SECRET_KEYS = {'requestSecret', 'activationKey', 'accessToken', 'code', 'bearer', 'csrf', 'inviteCode'}
LIVE_STATE = Path.home() / 'Documents' / 'MelangeDesktopAdmin'
ROWS, TIMES = [], []
CREATED = {'requests': [], 'devices': [], 'invite': None}   # everything cleanup() must leave inert
START = time.perf_counter()


class Failed(Exception):
    pass


def mask(value):
    if isinstance(value, dict):
        return {k: (v[:6] + '...') if k in SECRET_KEYS and isinstance(v, str) else mask(v) for k, v in value.items()}
    return [mask(v) for v in value] if isinstance(value, list) else value


def timed(label, call):
    begin = time.perf_counter()
    try:
        return call()
    finally:
        TIMES.append((time.perf_counter() - begin) * 1000)
        print(f'  {TIMES[-1]:7.0f} ms  {label}', flush=True)


def tlv(buf, pos):
    """(content_start, end) of the DER element at pos."""
    length, start = buf[pos + 1], pos + 2
    if length & 0x80:
        count = length & 0x7F
        length, start = int.from_bytes(buf[start:start + count], 'big'), start + count
    return start, start + length


def spki_sha256(cert):
    """sha256 of the DER SubjectPublicKeyInfo, which is what trust.tlsSpkiSha256 pins."""
    pos, _ = tlv(cert, 0)           # Certificate -> TBSCertificate
    pos, _ = tlv(cert, pos)
    items = []
    while len(items) < 7:           # [0] version, serial, sigalg, issuer, validity, subject, SPKI
        end = tlv(cert, pos)[1]
        items.append((pos, end))
        pos = end
    begin, end = items[6] if cert[items[0][0]] == 0xA0 else items[5]
    return hashlib.sha256(cert[begin:end]).hexdigest()


class Pinned(http.client.HTTPSConnection):
    pin = ''

    def connect(self):
        super().connect()
        actual = spki_sha256(self.sock.getpeercert(binary_form=True))
        if actual != self.pin:
            self.close()
            raise ssl.SSLError(f'TLS SPKI pin mismatch: got {actual[:12]} want {self.pin[:12]}')


def fail(message):
    raise Failed(message)


class Recipient:
    def __init__(self, origin, pin):
        url = urlsplit(origin)
        self.host, self.port, self.pin = url.hostname, url.port or 443, pin
        self.context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        self.context.check_hostname, self.context.verify_mode = False, ssl.CERT_NONE   # identity is the pin

    def call(self, method, path, value=None, authorization=None):
        connection = Pinned(self.host, self.port, context=self.context, timeout=10)
        connection.pin = self.pin
        headers = {'Accept': 'application/json', **({'Authorization': authorization} if authorization else {}),
                   **({'Content-Type': 'application/json'} if value is not None else {})}

        def send():
            connection.request(method, path, json.dumps(value) if value is not None else None, headers)
            response = connection.getresponse()
            return response.status, json.loads(response.read() or b'null')
        try:
            return timed(f'recipient {method} {path}', send)
        finally:
            connection.close()


class Admin:
    def __init__(self, dashboard):
        self.server_id = None   # known only for a state directory; a dashboard URL does not say which server it runs
        if dashboard.startswith('http'):
            url = urlsplit(dashboard)
        else:
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
            from desktop_admin import Store
            from access_store import AccessStore
            from admin_dashboard import create_server
            from apps_admin import UnavailableApps
            access = AccessStore(Store(Path(dashboard)))
            self.server_id = access.config()['serverId']   # refuses an uninitialised state directory
            server, boot = create_server(access, 0, apps=UnavailableApps('not used by auth_roundtrip'))
            threading.Thread(target=server.serve_forever, daemon=True).start()
            url = urlsplit(boot)
        self.port, self.auth = url.port, {}
        status, session = self.post('/session', {'bootstrap': url.fragment.removeprefix('bootstrap=')})
        if status != 200:
            fail(f'dashboard session exchange -> {status} {json.dumps(mask(session))}')
        self.auth = {'Authorization': 'Bearer ' + session['bearer'], 'X-Admin-CSRF': session['csrf']}

    def post(self, path, value):
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=10)

        def send():
            connection.request('POST', path, json.dumps(value), {'Content-Type': 'application/json',
                                                                 'Origin': f'http://127.0.0.1:{self.port}', **self.auth})
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        try:
            return timed(f'admin POST {path}', send)
        finally:
            connection.close()


def check(label, actual, expected, body):
    shown = json.dumps(mask(body), sort_keys=True)
    ROWS.append((label, expected, actual, f'{TIMES[-1]:.0f}', shown[:100]))
    print(f'{"ok  " if actual == expected else "FAIL"} {label}: HTTP {actual} (expected {expected}) {shown}', flush=True)
    if actual != expected:
        fail(f'{label}: HTTP {actual}, expected {expected}')


def finish(code):
    print('\ncase | expected | actual | ms | body')
    for row in ROWS:
        print(' | '.join(map(str, row)))
    print(f'HTTP calls: {len(TIMES)}, {sum(TIMES):.0f} ms; total wall {(time.perf_counter() - START) * 1000:.0f} ms')
    print('RESULT:', 'PASS' if code == 0 else 'FAIL', flush=True)
    return code


def cleanup(admin):
    """Deny this run's open requests, revoke its active grants and usable invite, then prove none remain."""
    requests, devices = set(CREATED['requests']), set(CREATED['devices'])

    def leftovers():
        status, board = admin.post('/dashboard', {})
        if status != 200:
            fail(f'dashboard listing -> {status}')
        return ([r['request_id'] for r in board['requests'] if r['request_id'] in requests and r['state'] in ('pending', 'approved')],
                [g['grant_id'] for g in board['grants'] if g['device_id'] in devices and not g['revoked']],
                [i['inviteId'] for i in board['invites'] if i['inviteId'] == CREATED['invite'] and i['state'] == 'active'])
    try:
        open_requests, grants, invites = leftovers()
        for request_id in open_requests:
            print('cleanup deny', request_id, '->', admin.post('/deny', {'requestId': request_id})[0], flush=True)
        for grant_id in grants:
            print('cleanup revoke', grant_id, '->', admin.post('/revoke', {'grantId': grant_id})[0], flush=True)
        for invite_id in invites:
            print('cleanup invite-revoke', invite_id, '->', admin.post('/invite-revoke', {'inviteId': invite_id})[0], flush=True)
        left = leftovers()
    except Exception as error:   # report, never hide, a cleanup that could not be verified
        left = (f'{type(error).__name__}: {error}',)
    if any(left):
        print('CLEANUP INCOMPLETE - deny/revoke by hand in the dashboard:', left, 'requests', sorted(requests), flush=True)
        return False
    print(f'cleanup ok: none of {len(requests)} request(s) pending/approved, no active grant, no usable invite', flush=True)
    return True


def payload(envelope):
    return json.loads(base64.b64decode(envelope['payload']))


def new_request(invite_code, display):
    request = {'requestId': str(uuid.uuid4()), 'deviceId': str(uuid.uuid4()), 'appId': 'melange', 'platform': 'win32',
               'arch': 'x64', 'displayName': display, 'requestSecret': secrets.token_urlsafe(32),
               **({'inviteCode': invite_code} if invite_code is not None else {})}
    CREATED['requests'].append(request['requestId'])   # recorded before sending: a lost response is still cleaned up
    CREATED['devices'].append(request['deviceId'])
    return request


def live_targets(args, trust):
    """Every argument that names the live server: the relay host, its port, or the live state directory."""
    named = [v for v in (args.origin, args.dashboard, str(trust.get('url', ''))) if 'bore.pub' in v.lower() or ':38443' in v]
    if args.dashboard.lower().startswith('http'):
        # A running dashboard URL cannot be told apart from the live administrator dashboard (no serverId on its
        # routes), and --issue-invite would mint a real invite there. Treat it as live.
        named.append(args.dashboard)
    elif Path(args.dashboard).resolve() == LIVE_STATE.resolve():
        named.append(args.dashboard)   # WindowsPath equality ignores case
    return named


def run(args, trust, admin):
    if admin.server_id is not None and admin.server_id != trust.get('serverId'):
        # e.g. the live state directory reached through another path (subst, UNC, junction) next to an isolated trust
        fail('--dashboard state directory belongs to a different server than --trust; nothing was sent')
    recipient, code = Recipient(args.origin, trust['tlsSpkiSha256']), args.invite_code
    if args.issue_invite:
        status, invite = admin.post('/invite-issue', {'label': args.display_name[:60], 'uses': 1, 'days': 1})
        check('admin invite-issue (1 use)', status, 200, invite)
        CREATED['invite'], code = invite['inviteId'], invite['code']
    request = new_request(code, args.display_name)
    status, body = recipient.call('POST', '/v1/access/requests', request)
    check('POST /v1/access/requests ' + ('(invite code)' if code else '(no code)'), status, args.expect_request, body)
    if args.expect_request != 201:
        return 0
    secret = 'Request ' + request['requestSecret']
    status, body = recipient.call('GET', '/v1/access/requests/' + request['requestId'], authorization=secret)
    check('GET request poll (pending)', status, 200, body)
    if body['status'] != 'pending':
        fail('expected pending')
    if args.deny_only:
        status, body = admin.post('/deny', {'requestId': request['requestId']})
        check('admin deny', status, 200, body)
        status, body = recipient.call('GET', '/v1/access/requests/' + request['requestId'], authorization=secret)
        check('GET request poll (denied)', status, 200, body)
        if body['status'] != 'denied':
            fail('expected denied')
        return 0
    status, approved = admin.post('/approve', {'requestId': request['requestId'], 'role': 'local_user', 'districtIds': []})
    check('admin approve', status, 200, approved)
    activation = {k: request[k] for k in ('requestId', 'deviceId', 'appId', 'platform', 'arch')}
    activation['activationKey'] = approved['activationKey']
    status, activated = recipient.call('POST', '/v1/access/activate', activation, secret)
    grant = payload(activated['grant']) if status == 200 else {}
    check('POST /v1/access/activate', status, 200, {k: grant.get(k) for k in ('grantId', 'role', 'appId', 'sequence', 'districtIds')}
          | {'accessToken': activated.get('accessToken', '')})
    if grant['serverId'] != trust['serverId']:
        fail('grant serverId differs from the trust descriptor')
    bearer = 'Bearer ' + activated['accessToken']
    for label, revoked in (('active', False), ('revoked', True)):
        if revoked:
            status, body = admin.post('/revoke', {'grantId': grant['grantId']})
            check('admin revoke', status, 200, body)
        status, signed = recipient.call('GET', '/v1/access/status', authorization=bearer)
        state = payload(signed) if status == 200 else {}
        check(f'GET /v1/access/status ({label})', status, 200, {k: state.get(k) for k in ('grantId', 'revoked', 'sequence')})
        if state.get('revoked') is not revoked or state.get('grantId') != grant['grantId']:
            fail(f'status should be {label} for this grant')
    if args.issue_invite:   # the single use is spent: a second brand-new tester with the same code is refused
        status, body = recipient.call('POST', '/v1/access/requests', new_request(code, args.display_name))
        check('POST /v1/access/requests (reused invite)', status, 403, body)
        if body != {'error': 'invite_invalid'}:
            fail('reuse should answer invite_invalid')
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--origin', required=True)
    parser.add_argument('--trust', required=True, help='access-trust JSON: SPKI pin + serverId')
    parser.add_argument('--dashboard', required=True, help='state directory, or loopback dashboard URL with #bootstrap=')
    parser.add_argument('--invite-code')
    parser.add_argument('--issue-invite', action='store_true')
    parser.add_argument('--expect-request', type=int, default=201, help='expected status of the first POST (default 201)')
    parser.add_argument('--deny-only', action='store_true')
    parser.add_argument('--display-name', default=DISPLAY, help='request displayName and invite label (live: must start CLAUDE TEST)')
    parser.add_argument('--allow-live', action='store_true', help='permit the live relay, port or state directory (approved runs only)')
    args = parser.parse_args()
    # Everything up to Admin() is local: no socket, DNS lookup or sqlite open happens before these refusals.
    trust = json.loads(Path(args.trust).read_text(encoding='utf-8'))
    live = [v.split('#')[0] for v in live_targets(args, trust)]   # never echo a #bootstrap= fragment
    if live and not args.allow_live:
        print(f'FAIL: refusing the live server ({live}); this harness is for isolated instances unless --allow-live', flush=True)
        return 2
    if trust.get('purpose') != 'melange-desktop-trust' or str(trust.get('url', '')).rstrip('/').lower() != args.origin.rstrip('/').lower():
        print(f'FAIL: trust descriptor does not match --origin (trust url {trust.get("url")})', flush=True)
        return 2
    if live:
        if not args.display_name.startswith('CLAUDE TEST'):
            print('FAIL: --allow-live requires --display-name starting with "CLAUDE TEST"', flush=True)
            return 2
        print('#' * 72 + f'\n#  LIVE ACCESS SERVER: {", ".join(live)}\n#  display name: {args.display_name}'
              '\n#  every request is denied or its grant revoked before exit\n' + '#' * 72, flush=True)
    if not args.dashboard.lower().startswith('http'):
        try:   # informational: the invite mode the supervisor started `serve` with
            status_file = json.loads((Path(args.dashboard) / 'listener-status.json').read_text(encoding='utf-8'))
            print('listener-status inviteRequired:', status_file.get('inviteRequired'), flush=True)
        except (OSError, ValueError):
            print('listener-status inviteRequired: unknown (no readable listener-status.json)', flush=True)
    admin, code = None, 1
    try:
        admin = Admin(args.dashboard)
        code = run(args, trust, admin)
    except Failed as error:
        print('FAIL:', error, flush=True)
    except Exception as error:   # pin mismatch, timeout, relay drop, odd body: still clean up
        print(f'FAIL: {type(error).__name__}: {error}', flush=True)
    finally:
        if admin is not None and not cleanup(admin):
            code = 1
    return finish(code)


if __name__ == '__main__':
    sys.exit(main())
