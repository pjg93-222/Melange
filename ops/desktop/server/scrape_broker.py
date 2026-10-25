"""Optional authenticated, quota-controlled reads of fixed government APIs.

Credentials stay in the server environment and are sent only as X-Api-Key to
the compiled origin. Persistent reservations count attempted upstream requests,
including failures. SQLite leases enforce concurrency across server processes.
"""
from contextlib import contextmanager
from dataclasses import dataclass
import base64
import hashlib
import http.client
from email.utils import parsedate_to_datetime
import json
import os
from pathlib import Path
import re
import sqlite3
import socket
import stat
import time
import threading
import urllib.error
import urllib.parse
import urllib.request
import uuid

PROVIDERS = {
    'fec': ('https://api.open.fec.gov/v1/', 'FEC_API_KEY', frozenset((
        'candidate', 'candidates', 'committee', 'committees', 'schedules', 'elections',
        'totals', 'reports', 'names', 'filings', 'operations', 'presidential'))),
    'congress': ('https://api.congress.gov/v3/', 'CONGRESS_API_KEY', frozenset((
        'bill', 'amendment', 'member', 'committee', 'nomination', 'treaty', 'summaries',
        'congress', 'bound-congressional-record', 'daily-congressional-record',
        'house-vote', 'house-vote-member-votes', 'hearing', 'committee-report',
        'committee-print', 'committee-meeting', 'crsreport', 'communication'))),
}
MAX_RESPONSE = 16 * 1024 ** 2
RESPONSE_HEADERS = frozenset(('content-type', 'date', 'last-modified', 'etag', 'retry-after'))
SECRET_FIELDS = frozenset(('apikey', 'api_key', 'x-api-key', 'authorization', 'access_token',
                           'token', 'headers', 'url', 'callback', 'redirect', 'host'))


class BrokerError(Exception):
    def __init__(self, status, code, retry_after=None):
        self.status, self.code, self.retry_after = status, code, retry_after
        super().__init__(code)


@dataclass(frozen=True)
class UpstreamResponse:
    body: bytes
    status: int = 200
    headers: dict = None


@dataclass(frozen=True)
class Limits:
    # The global budget spans providers because api.data.gov keys can be shared.
    per_principal_hour: int = 120
    global_hour: int = 900
    per_principal_concurrent: int = 1
    global_concurrent: int = 4

    def __post_init__(self):
        for value in vars(self).values():
            if type(value) is not int or not 1 <= value <= 100000:
                raise ValueError('Invalid scrape broker limits')
        if self.global_concurrent > 8 or self.per_principal_concurrent > self.global_concurrent:
            raise ValueError('Scrape broker concurrency exceeds reserved listener capacity')


def checked_request(value):
    if (type(value) is not dict or set(value) != {'schemaVersion', 'provider', 'path', 'query'}
            or type(value['schemaVersion']) is not int or value['schemaVersion'] != 1
            or type(value['provider']) is not str or value['provider'] not in PROVIDERS):
        raise BrokerError(400, 'invalid_scrape_request')
    provider, path, query = value['provider'], value['path'], value['query']
    if (type(path) is not str or not 1 <= len(path) <= 240
            or not re.fullmatch(r'[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*/?', path)
            or path.split('/')[0] not in PROVIDERS[provider][2]
            or type(query) is not dict or len(query) > 40):
        raise BrokerError(400, 'invalid_scrape_request')
    pairs = []
    for key, values in query.items():
        if (type(key) is not str or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,63}', key)
                or key.lower() in SECRET_FIELDS):
            raise BrokerError(400, 'invalid_scrape_request')
        items = values if type(values) is list else [values]
        if not 1 <= len(items) <= 100:
            raise BrokerError(400, 'invalid_scrape_request')
        for item in items:
            if type(item) not in (str, int, bool):
                raise BrokerError(400, 'invalid_scrape_request')
            text = str(item).lower() if type(item) is bool else str(item)
            if len(text) > 1024 or any(ord(char) < 32 or ord(char) == 127 for char in text):
                raise BrokerError(400, 'invalid_scrape_request')
            pairs.append((key, text))
    if provider == 'congress':
        if query.get('format', 'json') != 'json':
            raise BrokerError(400, 'invalid_scrape_request')
        pairs = [(k, v) for k, v in pairs if k != 'format'] + [('format', 'json')]
    size_name, maximum = ('per_page', 100) if provider == 'fec' else ('limit', 250)
    size = query.get(size_name, maximum)
    if type(size) not in (int, str) or not str(size).isascii() or not str(size).isdecimal() or not 1 <= int(size) <= maximum:
        raise BrokerError(400, 'invalid_scrape_request')
    pairs = [(k, v) for k, v in pairs if k != size_name] + [(size_name, str(size))]
    encoded = urllib.parse.urlencode(pairs)
    if len(encoded) > 8192:
        raise BrokerError(400, 'invalid_scrape_request')
    return provider, PROVIDERS[provider][0] + path.rstrip('/') + '/?' + encoded


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        raise BrokerError(502, 'upstream_redirect_refused')


def retry_seconds(value, now):
    try:
        seconds = int(value) if str(value).isdigit() else int(parsedate_to_datetime(value).timestamp() - now)
    except (TypeError, ValueError, OverflowError):
        seconds = 60
    return max(1, min(seconds, 86400))


def upstream(provider, url, key, *, now=time.time):
    request = urllib.request.Request(url, headers={'X-Api-Key': key, 'Accept': 'application/json',
        'Accept-Encoding': 'identity', 'User-Agent': 'Melange-Mentat-ScrapeBroker/1'}, method='GET')
    deadline = time.monotonic() + 60
    try:
        try:
            response = urllib.request.build_opener(_NoRedirect()).open(request, timeout=30)
        except urllib.error.HTTPError as error:
            if error.code == 429:
                retry = retry_seconds(error.headers.get('Retry-After'), now()); error.close()
                raise BrokerError(429, 'upstream_rate_limited', retry) from None
            response = error
        with response:
            if not 200 <= response.status <= 599 or response.headers.get('Content-Encoding', 'identity') != 'identity':
                raise BrokerError(502, 'upstream_response_refused')
            # Socket timeouts alone reset on every packet. Shutdown interrupts a
            # trickling buffered read so its quota lease cannot outlive 120s.
            response_stream = response.fp.fp if isinstance(response, urllib.error.HTTPError) else response.fp
            transport = response_stream.raw._sock
            expired = threading.Event()
            def interrupt():
                expired.set()
                try: transport.shutdown(socket.SHUT_RDWR)
                except OSError: pass
            timer = threading.Timer(max(0.001, deadline - time.monotonic()), interrupt)
            timer.daemon = True; timer.start()
            raw, total = [], 0
            try:
                while True:
                    if time.monotonic() >= deadline:
                        raise BrokerError(504, 'upstream_timeout')
                    block = response.read(min(65536, MAX_RESPONSE + 1 - total))
                    if not block:
                        break
                    raw.append(block); total += len(block)
                    if total > MAX_RESPONSE:
                        raise BrokerError(502, 'upstream_response_too_large')
                if expired.is_set(): raise BrokerError(504, 'upstream_timeout')
            finally: timer.cancel()
            headers = {name.lower(): value for name, value in response.headers.items() if name.lower() in RESPONSE_HEADERS}
            return UpstreamResponse(b''.join(raw), response.status, headers)
    except urllib.error.HTTPError as error:
        retry = retry_seconds(error.headers.get('Retry-After'), now()) if error.code == 429 else None
        status = error.code; error.close()
        raise BrokerError(429 if status == 429 else 502,
                          'upstream_rate_limited' if status == 429 else 'upstream_request_failed', retry) from None
    except BrokerError:
        raise
    except (OSError, http.client.HTTPException, urllib.error.URLError):
        raise BrokerError(503, 'upstream_unavailable', 5) from None
    except (ValueError, UnicodeError, RecursionError):
        raise BrokerError(502, 'upstream_response_refused') from None


def reject_reflected_key(value, secret, depth=0):
    if depth > 40:
        raise BrokerError(502, 'upstream_response_refused')
    if isinstance(value, dict):
        for key, item in value.items():
            reject_reflected_key(key, secret, depth + 1)
            reject_reflected_key(item, secret, depth + 1)
    elif isinstance(value, list):
        for item in value: reject_reflected_key(item, secret, depth + 1)
    elif isinstance(value, str):
        # Inspect decoded JSON strings and URL escapes without rewriting evidence.
        if secret in value or secret in urllib.parse.unquote(value):
            raise BrokerError(502, 'upstream_response_refused')


def raw_envelope(result, secret):
    if (not isinstance(result, UpstreamResponse) or type(result.body) is not bytes
            or not 0 < len(result.body) <= MAX_RESPONSE or type(result.status) is not int
            or not 200 <= result.status <= 599 or type(result.headers or {}) is not dict):
        raise BrokerError(502, 'upstream_response_refused')
    try:
        text = result.body.decode('utf-8')
        value = json.loads(text, parse_float=str,
            parse_constant=lambda _v: (_ for _ in ()).throw(ValueError()))
        reject_reflected_key(text, secret)
        reject_reflected_key(value, secret)
        headers = {key.lower(): val for key, val in (result.headers or {}).items()
                   if type(key) is str and key.lower() in RESPONSE_HEADERS}
        if any(type(val) is not str or len(val) > 1024 or '\r' in val or '\n' in val for val in headers.values()):
            raise ValueError()
        reject_reflected_key(headers, secret)
    except (UnicodeError, ValueError, RecursionError):
        raise BrokerError(502, 'upstream_response_refused') from None
    return {'status': result.status, 'headers': headers, 'bodyBase64': base64.b64encode(result.body).decode('ascii'),
            'sha256': hashlib.sha256(result.body).hexdigest(), 'bytes': len(result.body), 'originalResponseBytes': True}


class ScrapeBroker:
    def __init__(self, root, *, keys, limits=Limits(), fetch=upstream, clock=time.time):
        self.root, self.keys, self.limits, self.fetch, self.clock = Path(root), dict(keys), limits, fetch, clock
        if (not self.root.is_absolute() or not self.root.is_dir() or not self.keys
                or set(self.keys) - set(PROVIDERS) or any(type(key) is not str or not key.strip()
                    or len(key) > 512 or any(ord(c) < 33 or ord(c) > 126 for c in key) for key in self.keys.values())):
            raise ValueError('Scrape broker needs a private existing state directory and configured server keys')
        for path in (self.root, *self.root.parents):
            info = path.lstat()
            if not stat.S_ISDIR(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400 or path.is_symlink():
                raise ValueError('Scrape broker state directory is unsafe')
        self.db = self.root / 'scrape-broker.sqlite3'
        with self.connect() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS calls (at INTEGER NOT NULL, principal TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS calls_at ON calls(at);
                CREATE INDEX IF NOT EXISTS calls_principal ON calls(principal,at);
                CREATE TABLE IF NOT EXISTS leases (id TEXT PRIMARY KEY, principal TEXT NOT NULL, expires INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS cooldowns (provider TEXT PRIMARY KEY, until INTEGER NOT NULL);''')

    @contextmanager
    def connect(self):
        if self.db.exists():
            info = self.db.lstat()
            if self.db.is_symlink() or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or getattr(info, 'st_file_attributes', 0) & 0x400:
                raise BrokerError(503, 'service_unavailable')
        db = sqlite3.connect(self.db, timeout=10)
        try:
            with db: yield db
        finally: db.close()

    @contextmanager
    def reserve(self, principal, provider):
        now, token = int(self.clock()), uuid.uuid4().hex
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM calls WHERE at<=?', (now - 3600,))
            db.execute('DELETE FROM leases WHERE expires<=?', (now,))
            cooldown = db.execute('SELECT until FROM cooldowns WHERE provider=?', (provider,)).fetchone()
            if cooldown and cooldown[0] > now:
                raise BrokerError(429, 'upstream_rate_limited', cooldown[0] - now)
            for predicate, args, budget in [('', (), self.limits.global_hour),
                    (' WHERE principal=?', (principal,), self.limits.per_principal_hour)]:
                count, oldest = db.execute('SELECT COUNT(*),MIN(at) FROM calls' + predicate, args).fetchone()
                if count >= budget:
                    raise BrokerError(429, 'scrape_quota_exceeded', max(1, oldest + 3600 - now))
            for predicate, args, budget in [('', (), self.limits.global_concurrent),
                    (' WHERE principal=?', (principal,), self.limits.per_principal_concurrent)]:
                if db.execute('SELECT COUNT(*) FROM leases' + predicate, args).fetchone()[0] >= budget:
                    raise BrokerError(429, 'scrape_concurrency_exceeded', 5)
            db.execute('INSERT INTO calls VALUES (?,?)', (now, principal))
            db.execute('INSERT INTO leases VALUES (?,?,?)', (token, principal, now + 120))
        try:
            yield
        finally:
            with self.connect() as db: db.execute('DELETE FROM leases WHERE id=?', (token,))

    def execute(self, grant, value):
        # Only AccessStore.authenticate returns the grant used by the HTTP seam.
        if (not isinstance(grant, dict) or grant.get('app') not in ('melange', 'mentat')
                or grant.get('revoked') or not isinstance(grant.get('principal_id'), str)):
            raise BrokerError(403, 'access_denied')
        try: principal = str(uuid.UUID(grant['principal_id']))
        except (ValueError, AttributeError): raise BrokerError(403, 'access_denied') from None
        provider, url = checked_request(value)
        if provider not in self.keys:
            raise BrokerError(503, 'scrape_provider_unavailable', 60)
        with self.reserve(principal, provider):
            try:
                result = self.fetch(provider, url, self.keys[provider])
            except BrokerError as error:
                if error.status == 429:
                    retry = max(1, min(error.retry_after or 60, 86400))
                    with self.connect() as db:
                        db.execute('INSERT INTO cooldowns VALUES (?,?) ON CONFLICT(provider) DO UPDATE SET until=MAX(until,excluded.until)',
                                   (provider, int(self.clock()) + retry))
                raise BrokerError(error.status, error.code, error.retry_after) from None
            except Exception:
                # HTTP exception strings can contain URLs and credential headers.
                raise BrokerError(503, 'upstream_unavailable', 5) from None
            return {'schemaVersion': 1, 'provider': provider, 'raw': raw_envelope(result, self.keys[provider])}


def from_environment(root, environ=None):
    environ = os.environ if environ is None else environ
    enabled = environ.get('MELANGE_SCRAPE_BROKER_ENABLED', '').lower().strip()
    if enabled in ('', '0', 'false', 'no', 'off'):
        return None
    if enabled not in ('1', 'true', 'yes', 'on'):
        raise ValueError('Invalid scrape broker enable flag')
    settings = {}
    for field in Limits.__dataclass_fields__:
        value = environ.get('MELANGE_SCRAPE_' + field.upper())
        if value is not None:
            if not value.isascii() or not value.isdecimal():
                raise ValueError('Invalid scrape broker limit')
            settings[field] = int(value)
    keys = {name: environ[spec[1]] for name, spec in PROVIDERS.items() if environ.get(spec[1])}
    return ScrapeBroker(root, keys=keys, limits=Limits(**settings))
