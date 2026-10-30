"""Publisher-only factual-data projection; never changes original inputs.

Private transformation evidence contains hashes and local-path mappings, never
copies of removed credentials. Published data contains neither local paths nor
request authentication. Domain producers separately prove numerical parity.
"""
from collections import Counter
from functools import lru_cache
import hashlib
import json
import math
import re
from urllib.parse import unquote_plus, urlsplit, urlunsplit

_AUTH = frozenset(('apikey', 'apitoken', 'accesstoken', 'refreshtoken', 'clientsecret',
                  'authorization', 'proxyauthorization', 'cookie', 'cookies', 'setcookie', 'xapikey'))
_QUERY_AUTH = _AUTH | {'token', 'auth', 'signature', 'sig', 'jwt',
                     'xamzcredential', 'xamzsecuritytoken', 'xamzsignature', 'xgoogcredential', 'xgoogsignature'}
_LOCAL = re.compile(r'(?i)(?:[a-z]:[\\/](?:users|programdata|windows|melange-data)[\\/]|file:///)')
_TOKEN = re.compile(r'(?i)(?:\bgithub_pat_[a-z0-9_]{30,}\b|\bgh[pousr]_[a-z0-9]{30,}\b|-----BEGIN [A-Z ]*PRIVATE KEY-----)')
_URL = re.compile(r'https?://[^\s<>"\']+',re.I)
_UNICODE = re.compile(r'<U\+([A-Fa-f0-9]{4,6})>')


def digest(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


@lru_cache(maxsize=1024)
def _short_key_id(value):
    return re.sub('[^a-z0-9]', '', value.casefold())


def key_id(value):
    return _short_key_id(value) if len(value)<=128 else re.sub('[^a-z0-9]','',value.casefold())


class PublicationProjection:
    def __init__(self):
        self.changes = Counter()
        self.path_map = {}

    def changed(self, kind, context, original, result):
        self.changes[(kind, context, digest(original), digest(result))] += 1

    def source_identifier(self, value, context):
        identifier = 'workspace-source:' + hashlib.sha256(value.encode('utf-8')).hexdigest()
        self.path_map[value] = identifier
        self.changed('local-source-path', context, value, identifier)
        return identifier

    def public_url(self, value, context):
        parts = urlsplit(value)
        if parts.scheme not in ('http', 'https') or not parts.netloc:
            raise ValueError('A request URL could not be projected safely')
        retained = []
        for parameter in parts.query.split('&') if parts.query else ():
            raw_key = parameter.split('=', 1)[0]
            if key_id(unquote_plus(raw_key)) not in _QUERY_AUTH:
                retained.append(parameter)
        netloc = parts.netloc.rsplit('@', 1)[-1]
        fragment = parts.fragment
        if '=' in fragment:
            fragment = '&'.join(part for part in fragment.split('&')
                                if key_id(unquote_plus(part.split('=', 1)[0])) not in _QUERY_AUTH)
        projected = urlunsplit((parts.scheme, netloc, parts.path, '&'.join(retained), fragment))
        if projected != value:
            self.changed('request-authentication', context, value, projected)
        return projected

    def text(self, value, context):
        # Almost all analytical cells are plain ASCII names/identifiers. Avoid
        # several regular-expression scans when none of their literal markers
        # is present. Non-ASCII keeps the original Unicode regex behavior.
        if value.isascii():
            lower=value.lower()
            if not any(marker in lower for marker in ('\\',':/','<u+','github_pat_','ghp_','gho_','ghu_','ghs_','ghr_','-----begin')):
                return value
        if _LOCAL.search(value):
            return self.source_identifier(value, context)
        if _TOKEN.search(value):
            result = '[private credential omitted]'
            self.changed('credential-material', context, value, result)
            return result
        projected = _URL.sub(lambda match: self.public_url(match.group(0), context), value)
        def codepoint(match):
            number = int(match[1], 16)
            if not 0 <= number <= 0x10ffff or 0xd800 <= number <= 0xdfff:
                raise ValueError('Invalid source Unicode placeholder')
            return chr(number)
        result = _UNICODE.sub(codepoint, projected)
        if result != projected:
            self.changed('source-unicode-placeholder', context, projected, result)
        return result

    def record(self, value, context='', *, depth=0):
        if depth > 48:
            raise ValueError('Public data projection is too deeply nested')
        if isinstance(value, dict):
            result = {}
            for key, item in value.items():
                if not isinstance(key, str) or key in ('__proto__', 'constructor', 'prototype'):
                    raise ValueError('Invalid public-data object field')
                field = context + '/' + key
                normalized=key_id(key)
                if normalized in _AUTH or normalized in ('privateusernotes', 'privatenotes', 'requestheaders'):
                    self.changed('private-request-field', field, item, None)
                    continue
                name = self.source_identifier(key, context + '/<source-key>') if _LOCAL.search(key) else key
                if name in result:
                    raise ValueError('Source projection produced a duplicate field')
                result[name] = self.record(item, field, depth=depth + 1)
            return result
        if isinstance(value, list):
            return [self.record(item, context + '/[]', depth=depth + 1) for item in value]
        if isinstance(value, str):
            return self.text(value, context)
        if type(value) not in (int, float, bool, type(None)):
            raise ValueError('Unsupported public-data value')
        # Reject non-finite numbers without modifying genuine financial values.
        if isinstance(value,float) and not math.isfinite(value):
            raise ValueError('Non-finite public-data value')
        return value

    def receipt(self):
        return {'schemaVersion': 1, 'privateEvidence': True,
                'changes': [{'kind': kind, 'context': context, 'originalSha256': original,
                             'projectedSha256': projected, 'occurrences': count}
                            for (kind, context, original, projected), count in sorted(self.changes.items())],
                'privateSourcePathMap': dict(sorted(self.path_map.items()))}


def assert_public_record(value):
    projection = PublicationProjection()
    projection.record(value)
    if projection.changes:
        raise ValueError('Public data still contains unprojected private request/source material')
