"""Collector access to the native shared broker; never reads a provider key.

The packaged main process supplies this ephemeral loopback capability only to
its backend. A configured broker failure never falls back to direct API keys.
"""
import base64
import hashlib
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

MAX_SOURCE_BYTES = 16 * 1024 ** 2
MAX_BYTES = 24 * 1024 ** 2


class ScrapeBrokerError(urllib.error.URLError):
    def __init__(self, status=503, retry_after=None):
        self.status, self.retry_after = status, retry_after
        message = 'Shared collection is unavailable'
        if retry_after: message += '; retry after ' + str(retry_after) + ' seconds'
        super().__init__(message)


def configuration(environ=None):
    environ = os.environ if environ is None else environ
    url, token = environ.get('MELANGE_SCRAPE_BROKER_URL'), environ.get('MELANGE_SCRAPE_BROKER_TOKEN')
    if not url and not token:
        return None
    try:
        parsed = urllib.parse.urlsplit(url or '')
        if (parsed.scheme != 'http' or parsed.hostname != '127.0.0.1' or parsed.path != '/query'
                or not parsed.port or parsed.username or parsed.password or parsed.query or parsed.fragment
                or type(token) is not str or not re.fullmatch(r'[A-Za-z0-9_-]{43}', token)):
            raise ValueError()
    except ValueError:
        raise ScrapeBrokerError() from None
    return url, token


def available():
    return configuration() is not None


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        raise ScrapeBrokerError()


def fetch_raw_url(source_url):
    config = configuration()
    if config is None:
        raise ScrapeBrokerError()
    try:
        parsed = urllib.parse.urlsplit(source_url)
        match = {'api.open.fec.gov': ('fec', '/v1/'), 'api.congress.gov': ('congress', '/v3/')}.get(parsed.hostname)
        if (not match or parsed.scheme != 'https' or parsed.port not in (None, 443)
                or parsed.username or parsed.password or parsed.fragment or not parsed.path.startswith(match[1])):
            raise ValueError()
        query = {}
        for key, value in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True, strict_parsing=True):
            if key.lower() in ('api_key', 'apikey', 'authorization', 'access_token'):
                raise ValueError()
            if key in query:
                if not isinstance(query[key], list): query[key] = [query[key]]
                query[key].append(value)
            else: query[key] = value
        value = {'schemaVersion': 1, 'provider': match[0], 'path': parsed.path.removeprefix(match[1]), 'query': query}
        body = json.dumps(value, separators=(',', ':')).encode('utf-8')
        if len(body) > 16384: raise ValueError()
    except (ValueError, TypeError):
        raise ScrapeBrokerError(400) from None
    request = urllib.request.Request(config[0], data=body, method='POST',
        headers={'Authorization': 'Bearer ' + config[1], 'Content-Type': 'application/json'})
    try:
        # Disable environment proxies for the loopback capability.
        with urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect()).open(request, timeout=95) as response:
            raw = response.read(MAX_BYTES + 1)
            if response.status != 200 or len(raw) > MAX_BYTES: raise ValueError()
        result = json.loads(raw)
        if (type(result) is not dict or set(result) != {'schemaVersion', 'provider', 'raw'}
                or result['schemaVersion'] != 1 or result['provider'] != match[0]): raise ValueError()
        source = result['raw']
        if (type(source) is not dict or set(source) != {'status','headers','bodyBase64','sha256','bytes','originalResponseBytes'}
                or source['originalResponseBytes'] is not True or type(source['status']) is not int
                or not 200 <= source['status'] <= 599 or type(source['headers']) is not dict
                or type(source['bytes']) is not int or not 0 < source['bytes'] <= MAX_SOURCE_BYTES
                or type(source['bodyBase64']) is not str or type(source['sha256']) is not str
                or not re.fullmatch('[a-f0-9]{64}', source['sha256'])): raise ValueError()
        content = base64.b64decode(source['bodyBase64'], validate=True)
        if (len(content) != source['bytes'] or hashlib.sha256(content).hexdigest() != source['sha256']
                or any(key not in ('content-type','date','last-modified','etag','retry-after')
                       or type(val) is not str or len(val)>1024 or '\r' in val or '\n' in val
                       for key,val in source['headers'].items())): raise ValueError()
        return content, source['status'], source['headers']
    except urllib.error.HTTPError as error:
        retry = error.headers.get('Retry-After', '')
        retry = max(1, min(int(retry), 86400)) if retry.isascii() and retry.isdecimal() else None
        status = error.code; error.close()
        raise ScrapeBrokerError(status, retry) from None
    except (OSError, ValueError, TypeError):
        raise ScrapeBrokerError() from None


def fetch_json_url(source_url):
    content, status, headers = fetch_raw_url(source_url)
    if status != 200:
        retry = headers.get('retry-after', '')
        raise ScrapeBrokerError(status, int(retry) if retry.isdecimal() else None)
    try: return json.loads(content)
    except (ValueError, UnicodeError): raise ScrapeBrokerError(502) from None
