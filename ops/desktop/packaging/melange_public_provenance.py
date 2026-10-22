"""Offline, source-native government input closure. No enabled production plan.

ReviewedPlan is trusted producer configuration, never downloaded authorization.
The normalized receipt format is deliberately closed. Existing House/Senate raw
receipts need a separately reviewed normalization before an actual plan is used.
Nothing here certifies employment, merges people, activates readers or uploads.
"""
from contextlib import contextmanager, ExitStack
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
from types import MappingProxyType
from urllib.parse import unquote, urlsplit


MiB = 1024 ** 2
ROLE_FAMILIES = MappingProxyType({'house-observations': 'house',
    'senate-personal-candidates': 'senate', 'senate-committee-candidates': 'senate'})
PRODUCTION_PUBLIC_INPUT_PLANS = MappingProxyType({})
MAX_STRING, MAX_JSON_BYTES, MAX_DEPTH = 4096, MiB, 32
MAX_DOCUMENTS, MAX_RECEIPTS, MAX_RECORDS = 2048, 64, 2_000_000
MAX_FILE_BYTES, MAX_TOTAL_BYTES = 512 * MiB, 8 * 1024 * MiB
_HASH = re.compile(r'[a-f0-9]{64}\Z')
_IDENTIFIER = re.compile(r'[a-z][a-z0-9._-]{0,95}\Z')
_CAPABILITY = object()


def require(condition, message='Public government input was rejected'):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True,
                      separators=(',', ':'), allow_nan=False).encode('ascii')


def strict_json(raw):
    require(type(raw) is bytes and len(raw) <= MAX_JSON_BYTES)
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result and key not in ('__proto__', 'constructor', 'prototype'))
            result[key] = value
        return result
    def integer(text):
        require(len(text) <= 20)
        value = int(text)
        require(-(2 ** 63) <= value < 2 ** 63)
        return value
    def constant(_):
        raise ValueError('Nonfinite JSON number was rejected')
    try:
        value = json.loads(raw.decode('utf-8', errors='strict'), object_pairs_hook=pairs,
                           parse_int=integer, parse_constant=constant)
        nodes = [0]
        def bounded(item, depth=0):
            nodes[0] += 1
            require(depth <= MAX_DEPTH and nodes[0] <= 100_000)
            if type(item) is dict:
                require(len(item) <= 4096)
                for key, child in item.items():
                    bounded(key, depth + 1)
                    bounded(child, depth + 1)
            elif type(item) is list:
                require(len(item) <= 50_000)
                for child in item:
                    bounded(child, depth + 1)
            elif type(item) is str:
                require(len(item) <= MAX_STRING and '\x00' not in item)
                item.encode('utf-8', errors='strict')
            elif type(item) is float:
                require(math.isfinite(item))
            else:
                require(item is None or type(item) in (bool, int))
        bounded(value)
        return value
    except (RecursionError, UnicodeError) as error:
        raise ValueError('Bounded UTF8 JSON was rejected') from error


def _exact(value, fields):
    require(type(value) is dict and set(value) == set(fields))


def _identifier(value):
    require(type(value) is str and _IDENTIFIER.fullmatch(value) is not None)


def _hash(value):
    require(type(value) is str and _HASH.fullmatch(value) is not None)


def _relative(value):
    require(type(value) is str and 0 < len(value) <= 240 and '\\' not in value
            and ':' not in value and not any(ord(c) < 32 for c in value))
    parts = value.split('/')
    reserved = {'con', 'prn', 'aux', 'nul', *(f'com{i}' for i in range(1, 10)), *(f'lpt{i}' for i in range(1, 10))}
    require(all(part not in ('', '.', '..') and not part.endswith(('.', ' '))
                and part.split('.')[0].casefold() not in reserved for part in parts)
            and str(PurePosixPath(value)) == value and not value.startswith('/'))


def _official_url(value, family):
    require(type(value) is str and 0 < len(value) <= 2048)
    require(value.isascii() and not any(ord(c) < 33 for c in value))
    try:
        parsed = urlsplit(value)
        roots = {'house': ('house.gov',), 'senate': ('senate.gov',)}[family]
        require(parsed.scheme == 'https' and parsed.hostname is not None
                and parsed.netloc == parsed.hostname and parsed.username is None
                and parsed.password is None and parsed.port is None
                and not parsed.query and not parsed.fragment)
        require(any(parsed.hostname == root or parsed.hostname.endswith('.' + root) for root in roots))
        decoded = unquote(parsed.path, errors='strict')
        require(parsed.path.startswith('/') and '\\' not in decoded
                and not any(ord(c) < 32 for c in decoded)
                and all(part not in ('.', '..') for part in decoded.split('/')))
    except (KeyError, UnicodeError) as error:
        raise ValueError('Official document URL was rejected') from error


@dataclass(frozen=True)
class DocumentSpec:
    document_id: str
    family: str
    relative: str
    bytes: int
    sha256: str
    url: str


@dataclass(frozen=True)
class ReceiptSpec:
    receipt_id: str
    family: str
    relative: str
    bytes: int
    sha256: str
    producer_sha256: str
    dependencies: tuple
    outputs: tuple


@dataclass(frozen=True)
class InputSpec:
    role: str
    relative: str
    bytes: int
    sha256: str
    records: int
    receipt_id: str


@dataclass(frozen=True)
class ReviewedPlan:
    documents: tuple
    receipts: tuple
    inputs: tuple


def _plan(plan):
    require(type(plan) is ReviewedPlan)
    require(type(plan.documents) is tuple and 0 < len(plan.documents) <= MAX_DOCUMENTS
            and type(plan.receipts) is tuple and 0 < len(plan.receipts) <= MAX_RECEIPTS
            and type(plan.inputs) is tuple and len(plan.inputs) == len(ROLE_FAMILIES))
    documents, receipts, inputs, paths = {}, {}, {}, set()
    total = 0
    for specs, expected in ((plan.documents, DocumentSpec), (plan.receipts, ReceiptSpec), (plan.inputs, InputSpec)):
        for spec in specs:
            require(type(spec) is expected)
            _relative(spec.relative)
            require(spec.relative.casefold() not in paths)
            paths.add(spec.relative.casefold())
            _hash(spec.sha256)
            limit = MAX_JSON_BYTES if expected is ReceiptSpec else MAX_FILE_BYTES
            require(type(spec.bytes) is int and 0 < spec.bytes <= limit)
            total += spec.bytes
    require(total <= MAX_TOTAL_BYTES)
    for spec in plan.documents:
        _identifier(spec.document_id)
        require(spec.document_id not in documents and spec.family in ('house', 'senate'))
        _official_url(spec.url, spec.family)
        require(all(old.url != spec.url for old in documents.values()))
        documents[spec.document_id] = spec
    for spec in plan.receipts:
        _identifier(spec.receipt_id)
        _hash(spec.producer_sha256)
        require(spec.receipt_id not in receipts and spec.family in ('house', 'senate'))
        require(type(spec.dependencies) is tuple and 0 < len(spec.dependencies) <= MAX_DOCUMENTS + MAX_RECEIPTS
                and len(set(spec.dependencies)) == len(spec.dependencies))
        require(type(spec.outputs) is tuple and len(spec.outputs) <= 1)
        for key in spec.dependencies:
            _identifier(key)
        for role in spec.outputs:
            require(role in ROLE_FAMILIES and ROLE_FAMILIES[role] == spec.family)
        receipts[spec.receipt_id] = spec
    require(not (set(documents) & set(receipts)) and not ((set(documents) | set(receipts)) & set(ROLE_FAMILIES)))
    for spec in plan.inputs:
        require(spec.role in ROLE_FAMILIES and spec.role not in inputs)
        require(type(spec.records) is int and 0 < spec.records <= MAX_RECORDS)
        require(spec.receipt_id in receipts)
        receipt = receipts[spec.receipt_id]
        require(receipt.family == ROLE_FAMILIES[spec.role] and receipt.outputs == (spec.role,))
        inputs[spec.role] = spec
    require(set(inputs) == set(ROLE_FAMILIES))
    by_role, used_receipts, used_documents = {}, set(), set()
    for role, source in inputs.items():
        visiting, reachable, complete = set(), set(), set()
        def visit(key):
            require(key not in visiting, 'Government receipt dependency cycle was rejected')
            if key in complete:
                return
            if key in documents:
                require(documents[key].family == ROLE_FAMILIES[role])
                reachable.add(key)
                return
            require(key in receipts and receipts[key].family == ROLE_FAMILIES[role])
            visiting.add(key)
            used_receipts.add(key)
            for child in receipts[key].dependencies:
                visit(child)
            visiting.remove(key)
            complete.add(key)
        visit(source.receipt_id)
        require(bool(reachable))
        by_role[role] = frozenset(reachable)
        used_documents.update(reachable)
    require(used_receipts == set(receipts) and used_documents == set(documents))
    for receipt in receipts.values():
        for role in receipt.outputs:
            require(inputs[role].receipt_id == receipt.receipt_id)
    return documents, receipts, inputs, by_role


def _regular(path, *, directory=False):
    info = path.lstat()
    require(not path.is_symlink() and not getattr(info, 'st_file_attributes', 0) & 0x400)
    require(stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode) and info.st_nlink == 1)
    return info


def _directory(path):
    path = Path(path)
    require(path.is_absolute() and '..' not in path.parts)
    for entry in (path, *path.parents):
        _regular(entry, directory=True)
    return path


def _stamp(info):
    # Python 3.12's Windows path and fd st_ctime_ns disagree on newly created
    # files. Use the same native ChangeTime query for both opened identities.
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,
            info.st_ctime_ns if os.name != 'nt' else None, info.st_nlink)


def _handle_stamp(stream):
    result = _stamp(os.fstat(stream.fileno()))
    if os.name != 'nt':
        return result
    import ctypes
    from ctypes import wintypes
    import msvcrt
    class BasicInformation(ctypes.Structure):
        _fields_ = [('CreationTime', ctypes.c_longlong), ('LastAccessTime', ctypes.c_longlong),
                    ('LastWriteTime', ctypes.c_longlong), ('ChangeTime', ctypes.c_longlong),
                    ('FileAttributes', wintypes.DWORD)]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    query = kernel.GetFileInformationByHandleEx
    query.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    query.restype = wintypes.BOOL
    info = BasicInformation()
    require(query(msvcrt.get_osfhandle(stream.fileno()), 0, ctypes.byref(info), ctypes.sizeof(info)),
            'Windows file change identity was unavailable')
    require(not info.FileAttributes & 0x400)
    return result + (info.ChangeTime,)


def _path_stamp(path):
    before = _regular(path)
    flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)
    with os.fdopen(os.open(path, flags), 'rb') as stream:
        require(_stamp(before) == _stamp(os.fstat(stream.fileno())))
        result = _handle_stamp(stream)
        require(_stamp(_regular(path)) == _stamp(os.fstat(stream.fileno())))
        return result


def _path(root, relative):
    result = root.joinpath(*relative.split('/'))
    for parent in result.parents:
        _regular(parent, directory=True)
        if parent == root:
            break
    return result


class ValidatedInputs:
    def __init__(self, capability, root, plan, documents, receipts, inputs, by_role, streams, stamps):
        require(capability is _CAPABILITY)
        self.root, self.plan = root, plan
        self.documents, self.receipts, self.inputs = map(MappingProxyType, (documents, receipts, inputs))
        self._by_role, self._streams, self._stamps = by_role, streams, stamps
        self.closed = False
        self.coverage = {'closedGovernmentInputs': True, 'fullApplication': False}
        manifest = {
            'schemaVersion': 1,
            'documents': [{'id': s.document_id, 'family': s.family, 'url': s.url, 'bytes': s.bytes, 'sha256': s.sha256}
                          for s in sorted(documents.values(), key=lambda s: s.document_id)],
            'receipts': [{'id': s.receipt_id, 'family': s.family, 'bytes': s.bytes, 'sha256': s.sha256,
                          'producerSha256': s.producer_sha256, 'dependencies': sorted(s.dependencies), 'outputs': list(s.outputs)}
                         for s in sorted(receipts.values(), key=lambda s: s.receipt_id)],
            'inputs': [{'role': role, 'bytes': inputs[role].bytes, 'sha256': inputs[role].sha256,
                        'records': inputs[role].records, 'receiptId': inputs[role].receipt_id} for role in ROLE_FAMILIES]}
        self._manifest_bytes = canonical(manifest)
        require(len(self._manifest_bytes) <= MAX_JSON_BYTES)
        self.manifest_digest = hashlib.sha256(self._manifest_bytes).hexdigest()

    @property
    def manifest(self):
        return strict_json(self._manifest_bytes)

    def ensure_current(self):
        require(not self.closed, 'Government input capability is closed')
        _directory(self.root)
        for relative, stream in self._streams.items():
            path = _path(self.root, relative)
            require(not stream.closed and _handle_stamp(stream) == self._stamps[relative]
                    and _path_stamp(path) == self._stamps[relative], 'Government input changed')

    def input_stream(self, role):
        require(not self.closed and role in self.inputs)
        stream = self._streams[self.inputs[role].relative]
        stream.seek(0)
        return stream

    def document_for(self, role, url, sha256):
        require(not self.closed and role in self.inputs)
        require(type(url) is str and type(sha256) is str)
        found = [self.documents[key] for key in self._by_role[role]
                 if self.documents[key].url == url and self.documents[key].sha256 == sha256]
        require(len(found) == 1, 'Observation document is outside the reviewed inventory')
        return found[0]


def _receipt(raw, spec, documents, receipts, inputs):
    value = strict_json(raw)
    _exact(value, ('schemaVersion', 'receiptId', 'family', 'producerSha256', 'dependencies', 'outputs', 'canonicalPromotions'))
    require(type(value['schemaVersion']) is int and value['schemaVersion'] == 1
            and value['receiptId'] == spec.receipt_id and value['family'] == spec.family
            and value['producerSha256'] == spec.producer_sha256)
    _exact(value['canonicalPromotions'], ('identity', 'employment', 'office', 'date'))
    require(all(type(n) is int and n == 0 for n in value['canonicalPromotions'].values()))
    require(type(value['dependencies']) is list and len(value['dependencies']) == len(spec.dependencies))
    seen = set()
    for binding in value['dependencies']:
        _exact(binding, ('id', 'bytes', 'sha256'))
        key = binding['id']
        require(type(key) is str and key in spec.dependencies and key not in seen)
        seen.add(key)
        expected = documents.get(key) or receipts.get(key)
        require(expected is not None and type(binding['bytes']) is int
                and binding['bytes'] == expected.bytes and binding['sha256'] == expected.sha256)
    require(type(value['outputs']) is list and len(value['outputs']) == len(spec.outputs))
    seen = set()
    for binding in value['outputs']:
        _exact(binding, ('role', 'bytes', 'sha256'))
        role = binding['role']
        require(type(role) is str and role in spec.outputs and role not in seen)
        seen.add(role)
        require(type(binding['bytes']) is int and binding['bytes'] == inputs[role].bytes
                and binding['sha256'] == inputs[role].sha256)


@contextmanager
def validated_inputs(root, plan):
    documents, receipts, inputs, by_role = _plan(plan)
    root = _directory(Path(root).absolute())
    streams, stamps, result, identities = {}, {}, None, set()
    with ExitStack() as stack:
        for spec in (*plan.documents, *plan.receipts, *plan.inputs):
            path = _path(root, spec.relative)
            before = _regular(path)
            require(before.st_size == spec.bytes)
            stamp = _path_stamp(path)
            flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)
            stream = stack.enter_context(os.fdopen(os.open(path, flags), 'rb'))
            require(_handle_stamp(stream) == stamp and stamp[:2] not in identities)
            identities.add(stamp[:2])
            h, total = hashlib.sha256(), 0
            while True:
                block = stream.read(MiB)
                if not block:
                    break
                total += len(block)
                require(total <= spec.bytes)
                h.update(block)
            require(total == spec.bytes and h.hexdigest() == spec.sha256)
            require(_handle_stamp(stream) == stamp and _path_stamp(path) == stamp)
            stream.seek(0)
            streams[spec.relative], stamps[spec.relative] = stream, stamp
        for spec in plan.receipts:
            _receipt(streams[spec.relative].read(MAX_JSON_BYTES + 1), spec, documents, receipts, inputs)
        result = ValidatedInputs(_CAPABILITY, root, plan, documents, receipts, inputs, by_role, streams, stamps)
        result.ensure_current()
        try:
            yield result
        finally:
            result.closed = True
