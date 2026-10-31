"""Passive, paged public-source observations. No graph/service/model imports."""
from array import array
import hashlib
import os
from pathlib import Path
import threading
from urllib.parse import parse_qs

try:
    import melange_public_provenance as p
except ModuleNotFoundError as error:
    if error.name != 'melange_public_provenance':
        raise
    # Direct source-server use has the program root, rather than the bundled
    # packaging directory, on sys.path. This fixed program import reads no data.
    from ops.desktop.packaging import melange_public_provenance as p


KIND = 'melange.official-payroll-observations.v1'
ROLES = ('house-observations', 'senate-personal-candidates', 'senate-committee-candidates')
MAX_RECORDS, MAX_BYTES, MAX_LINE = 3_000_000, 8 * 1024 ** 3, 1024 ** 2
BLOCK = 128
_CAPABILITY = object()
_TOP = ('schemaVersion', 'recordId', 'sourceRole', 'source', 'sourceExtracted', 'literalTokens',
        'originalBeforeRepair', 'extractionStatus', 'recordProvenance', 'review')
_RECEIPT = ('schemaVersion', 'kind', 'programFingerprint', 'inputManifestDigest', 'currentMapperFiles',
    'sourceManifest', 'recordCounts', 'normalizationCounts', 'provenanceStatus', 'output', 'canonicalPromotions', 'coverage')
PERSONAL_PARSE = frozenset(('HISTORICAL_REVERSE_LAYOUT_HEURISTIC_SPLIT', 'HISTORICAL_REVERSE_LAYOUT_LINE_SPLIT', 'HEURISTIC_SPLIT'))
COMMITTEE_PARSE = frozenset(('COLUMN_COORDINATE_SPLIT', 'COLUMN_COORDINATE_SPLIT_WITH_LEADING_TITLE',
    'COLUMN_COORDINATE_SPLIT_WITH_WRAPPED_TITLE', 'COLUMN_COORDINATE_SPLIT_WITH_LEADING_TITLE_WITH_WRAPPED_TITLE',
    'COLUMN_COORDINATE_SPLIT_NO_TITLE_COLUMN_WITH_LEADING_TITLE_WITH_WRAPPED_TITLE',
    'COLUMN_COORDINATE_SPLIT_NO_TITLE_COLUMN_WITH_LEADING_TITLE'))


def _exact(value, keys):
    p.require(type(value) is dict and set(value) == set(keys), 'Public data has an unsupported schema')


def _int(value, maximum, minimum=0):
    p.require(type(value) is int and minimum <= value <= maximum, 'Public data pagination or count is invalid')
    return value


def _text(value, maximum=4096, nullable=False):
    p.require((value is None and nullable) or (type(value) is str and len(value) <= maximum and '\x00' not in value))
    return value


def _fields(value, keys, nullable=True):
    _exact(value, keys)
    for item in value.values():
        _text(item, nullable=nullable)


def _manifest(value):
    _exact(value, ('schemaVersion', 'documents', 'receipts', 'evidence', 'inputs'))
    p.require(type(value['schemaVersion']) is int and value['schemaVersion'] == 1)
    documents = {}
    p.require(type(value['documents']) is list and 0 < len(value['documents']) <= p.MAX_DOCUMENTS)
    for doc in value['documents']:
        _exact(doc, ('id', 'family', 'url', 'bytes', 'sha256', 'format', 'pageCount'))
        p._identifier(doc['id'])
        p._hash(doc['sha256'])
        p.require(doc['family'] in ('house', 'senate') and doc['format'] in ('pdf', 'csv'))
        p._official_url(doc['url'], doc['family'])
        _int(doc['bytes'], p.MAX_FILE_BYTES, 1)
        if doc['pageCount'] is not None:
            _int(doc['pageCount'], 100_000, 1)
        p.require(doc['id'] not in documents and not any(d['url'] == doc['url'] for d in documents.values()))
        documents[doc['id']] = doc
    for key in ('receipts', 'evidence', 'inputs'):
        p.require(type(value[key]) is list and 0 < len(value[key]) <= p.MAX_DOCUMENTS)
    for receipt in value['receipts']:
        _exact(receipt, ('id', 'family', 'bytes', 'sha256', 'producerSha256', 'sourceFormat',
            'historicalProducerProof', 'receiptEvidence', 'dependencies', 'outputs'))
        p._identifier(receipt['id'])
        p._hash(receipt['sha256'])
        _int(receipt['bytes'], p.MAX_JSON_BYTES, 1)
        p.require(receipt['family'] in ('house', 'senate') and receipt['sourceFormat'] in p.SOURCE_RECEIPTS
            and receipt['producerSha256'] is None and receipt['historicalProducerProof'] == 'GENERATION_CODE_UNAVAILABLE'
            and receipt['receiptEvidence'] == 'SOURCE_REPORTED_NOT_REPLAYED')
        p.require(type(receipt['dependencies']) is list and type(receipt['outputs']) is list)
        for name in receipt['dependencies'] + receipt['outputs']:
            p._identifier(name)
    for evidence in value['evidence']:
        _exact(evidence, ('id', 'family', 'kind', 'bytes', 'sha256'))
        p._identifier(evidence['id'])
        p._hash(evidence['sha256'])
        _int(evidence['bytes'], p.MAX_FILE_BYTES, 1)
        p.require(evidence['family'] in ('house', 'senate') and evidence['kind'] in ('source-inventory',
            'source-extraction-receipts', 'source-text-cache', 'current-mapping-source', 'excluded-origin-dependency'))
    expected_roles = set(ROLES) | set(p.AUXILIARY_FAMILIES)
    seen = set()
    for source in value['inputs']:
        _exact(source, ('role', 'bytes', 'sha256', 'records', 'receiptId'))
        p.require(source['role'] in expected_roles and source['role'] not in seen)
        seen.add(source['role'])
        p._hash(source['sha256'])
        p._identifier(source['receiptId'])
        _int(source['bytes'], p.MAX_FILE_BYTES, 1)
        _int(source['records'], p.MAX_RECORDS, 1)
    p.require(seen == expected_roles)
    # Reuse the pure graph/schema validator only. These synthetic relative
    # names are never opened; downloaded provenance grants no file authority.
    graph = p.ReviewedPlan(
        tuple(p.DocumentSpec(d['id'], d['family'], 'documents/' + d['id'] + '.bin', d['bytes'],
            d['sha256'], d['url'], d['format'], d['pageCount']) for d in value['documents']),
        tuple(p.ReceiptSpec(r['id'], r['family'], 'receipts/' + r['id'] + '.json', r['bytes'],
            r['sha256'], r['producerSha256'], tuple(r['dependencies']), tuple(r['outputs']), r['sourceFormat'])
            for r in value['receipts']),
        tuple(p.InputSpec(i['role'], 'inputs/' + i['role'] + '.gz', i['bytes'], i['sha256'], i['records'], i['receiptId'])
            for i in value['inputs'] if i['role'] in ROLES),
        tuple(p.InputSpec(i['role'], 'inputs/' + i['role'] + '.gz', i['bytes'], i['sha256'], i['records'], i['receiptId'])
            for i in value['inputs'] if i['role'] in p.AUXILIARY_FAMILIES),
        tuple(p.EvidenceSpec(e['id'], e['family'], 'evidence/' + e['id'] + '.bin', e['bytes'], e['sha256'], e['kind'])
            for e in value['evidence']))
    p._plan(graph)
    return documents


def _row(value, documents):
    _exact(value, _TOP)
    p.require(type(value['schemaVersion']) is int and value['schemaVersion'] == 1 and value['sourceRole'] in ROLES)
    role = value['sourceRole']
    source = value['source']
    _exact(source, ('documentId', 'sha256', 'url', 'locator', 'reportPeriod'))
    p.require(type(source['documentId']) is str and source['documentId'] in documents)
    doc = documents[source['documentId']]
    p.require(source['sha256'] == doc['sha256'] and source['url'] == doc['url']
              and doc['family'] == ('house' if role == ROLES[0] else 'senate'))
    _fields(source['reportPeriod'], ('start', 'end'))
    locator = source['locator']
    p.require(type(locator) is dict)
    kind = locator.get('kind')
    if kind == 'csv-data-row':
        _exact(locator, ('kind', 'dataRow'))
        p.require(role == ROLES[0] and doc['format'] == 'csv')
        _int(locator['dataRow'], 5_000_000, 1)
        _fields(value['literalTokens'], ('office', 'payee', 'title', 'amount', 'serviceStart', 'serviceEnd'))
        p.require(value['extractionStatus'] == {'method': 'CSV_SOURCE_COLUMN',
            'literalEquivalence': 'VERIFIED_RAW_CSV_FIELDS', 'adapter': 'UTF8_REPLACE_CELL_STRIP_OPTIONAL_SHIFTED_VENDOR_V1'})
        p.require(value['recordProvenance'] == {})
    elif kind == 'pdf-layout-row':
        _exact(locator, ('kind', 'physicalPage', 'yMilli'))
        p.require(role == ROLES[0] and doc['format'] == 'pdf')
        _int(locator['physicalPage'], 100_000, 1)
        _int(locator['yMilli'], 2**31-1)
        _fields(value['literalTokens'], ('payee', 'amount', 'serviceStart', 'serviceEnd'), False)
        status = value['extractionStatus']
        _exact(status, ('method', 'review', 'literalEquivalence'))
        p.require(status['method'] in ('SOURCE_NAME', 'DITTO_FROM_PRIOR_PERSONNEL_ROW_SAME_OFFICE')
            and status['review'] == 'REVIEW_REQUIRED' and status['literalEquivalence'] == 'CACHED_EXTRACTION_NOT_REPLAYED')
        _exact(value['recordProvenance'], ('auxiliaryRole', 'candidateOrdinal'))
        p.require(value['recordProvenance']['auxiliaryRole'] == 'house-pdf-candidates')
        _int(value['recordProvenance']['candidateOrdinal'], p.MAX_RECORDS, 1)
    else:
        p.require(kind == 'pdf-extracted-row' and role in ROLES[1:] and doc['format'] == 'pdf')
        _exact(locator, ('kind', 'physicalPage', 'rowOrdinal'))
        _int(locator['physicalPage'], 100_000, 1)
        _int(locator['rowOrdinal'], 2**31-1, 1)
        p.require(value['literalTokens'] is None and value['recordProvenance'] == {})
        status = value['extractionStatus']
        keys = ('method', 'boundaryRepair', 'identity', 'literalEquivalence') if role == ROLES[1] else (
            'method', 'parser', 'officeAttribution', 'identity', 'literalEquivalence')
        _exact(status, keys)
        p.require(status['identity'] == 'UNVERIFIED_CANDIDATE' and status['literalEquivalence'] == 'CACHED_EXTRACTION_NOT_REPLAYED')
        p.require(status['method'] in (PERSONAL_PARSE if role == ROLES[1] else COMMITTEE_PARSE))
        if role == ROLES[1]:
            p.require(status['boundaryRepair'] in ('NONE', 'RAW_EVIDENCE_HEURISTIC_REPAIR_REVIEW_REQUIRED'))
            if status['boundaryRepair'] != 'NONE':
                _fields(value['originalBeforeRepair'], ('payee', 'title'))
        else:
            p.require(status['parser'] == 'senate-committee-payroll-parser-v2'
                and status['officeAttribution'] in ('PAGE_HEADER_ABBREVIATED_FUNDING_LINE_ONLY', 'PAGE_HEADER', 'CARRIED_FROM_PREVIOUS_VOLUME_II_PAGE'))
    if doc['pageCount'] is not None and 'physicalPage' in locator:
        p.require(locator['physicalPage'] <= doc['pageCount'])
    _fields(value['sourceExtracted'], ('office', 'payee', 'title', 'amount'))
    if role != ROLES[1] or value['extractionStatus'].get('boundaryRepair') == 'NONE':
        p.require(value['originalBeforeRepair'] is None)
    _exact(value['review'], ('status', 'identityPromoted', 'employmentPromoted', 'officePromoted', 'datePromoted'))
    p.require(value['review']['status'] == 'SOURCE_OBSERVATION_ONLY'
              and all(value['review'][k] is False for k in ('identityPromoted', 'employmentPromoted', 'officePromoted', 'datePromoted')))
    identity = hashlib.sha256(p.canonical([role, doc['sha256'], locator])).hexdigest()
    p.require(value['recordId'] == 'government-observation:' + identity)
    return role


class PublicDataCatalogue:
    def __init__(self, capability, snapshot, *, cancelled=lambda: False, validation_cache=None):
        p.require(capability is _CAPABILITY)
        if validation_cache is not None:
            from module_catalogue_cache import ValidationCache
            p.require(type(validation_cache) is ValidationCache)
        self._lock, self._streams, self._stamps, self._paths = threading.Lock(), {}, {}, {}
        self._index = {role: array('Q') for role in ROLES}
        self._counts = {role: 0 for role in ROLES}
        self._closed = False
        self._validation_cache_hit = False
        try:
            for role in ('observations', 'receipt'):
                path = Path(snapshot.files[role])
                p._directory(path.parent)
                p._regular(path)
                before = p._path_stamp(path)
                stream = os.fdopen(os.open(path, os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)), 'rb')
                self._streams[role], self._paths[role], self._stamps[role] = stream, path, before
                p.require(p._handle_stamp(stream) == before)
            raw = self._streams['receipt'].read(p.MAX_JSON_BYTES + 1)
            receipt = p.strict_json(raw)
            _exact(receipt, _RECEIPT)
            p.require(receipt['kind'] == KIND and type(receipt['schemaVersion']) is int and receipt['schemaVersion'] == 1)
            p._hash(receipt['programFingerprint'])
            _exact(receipt['currentMapperFiles'], ('melange_public_provenance.py', 'melange_public_payroll_projection.py', 'melange_public_payroll_normalize.py'))
            for value in receipt['currentMapperFiles'].values():
                p._hash(value)
            p.require(hashlib.sha256(p.canonical(receipt['currentMapperFiles'])).hexdigest() == receipt['programFingerprint'])
            self._documents = _manifest(receipt['sourceManifest'])
            p.require(hashlib.sha256(p.canonical(receipt['sourceManifest'])).hexdigest() == receipt['inputManifestDigest'])
            _exact(receipt['recordCounts'], ROLES)
            for value in receipt['recordCounts'].values():
                _int(value, p.MAX_RECORDS, 1)
            _exact(receipt['output'], ('format', 'bytes', 'sha256', 'records'))
            p.require(receipt['output']['format'] == 'strict-utf8-ndjson'
                and type(receipt['output']['bytes']) is int and 0 < receipt['output']['bytes'] <= MAX_BYTES
                and type(receipt['output']['records']) is int and 0 < receipt['output']['records'] <= MAX_RECORDS
                and receipt['output']['bytes'] == snapshot.objects['observations']['bytes']
                and receipt['output']['sha256'] == snapshot.objects['observations']['sha256']
                and hashlib.sha256(raw).hexdigest() == snapshot.objects['receipt']['sha256'])
            p.require(sum(receipt['recordCounts'].values()) == receipt['output']['records'])
            _exact(receipt['canonicalPromotions'], ('identity', 'employment', 'office', 'date'))
            p.require(all(type(v) is int and v == 0 for v in receipt['canonicalPromotions'].values()))
            _exact(receipt['coverage'], ('sourceNativeObservations', 'fullApplication'))
            p.require(receipt['coverage']['sourceNativeObservations'] is True and receipt['coverage']['fullApplication'] is False)
            _exact(receipt['normalizationCounts'], ('houseCsvFieldEquivalentRows', 'housePdfCandidateJoins', 'senateAcceptedSubsequence',
                'senateRawRecords', 'senateExcludedRecords', 'senateAcceptedRepairs'))
            for value in receipt['normalizationCounts'].values():
                _int(value, p.MAX_RECORDS)
            input_counts = {s['role']: s['records'] for s in receipt['sourceManifest']['inputs']}
            p.require(all(input_counts[role] == receipt['recordCounts'][role] for role in ROLES))
            p.require(receipt['provenanceStatus'] == {'currentMapper': 'EXACT_CODE_CLOSURE',
                'historicalProducer': 'SEE_SOURCE_RECEIPTS_NOT_INFERRED_FROM_CURRENT_CODE',
                'sourceExtraction': 'RECEIPT_REPORTED_NOT_INDEPENDENTLY_REPLAYED'})
            self._receipt_raw, self.revision = p.canonical(receipt), hashlib.sha256(raw).hexdigest()
            cached = (validation_cache.load(snapshot, roles=ROLES, block=BLOCK, counts=receipt['recordCounts'])
                      if validation_cache is not None else None)
            if cached is not None:
                # A protected successful semantic scan does not replace fresh
                # content verification. Hash the exact handles retained by this
                # reader, rather than trusting names, mtimes or earlier probes.
                stream, h, total = self._streams['observations'], hashlib.sha256(), 0
                while True:
                    p.require(not cancelled(), 'Public data preparation was cancelled')
                    chunk = stream.read(4 * 1024 ** 2)
                    if not chunk:
                        break
                    total += len(chunk)
                    p.require(total <= receipt['output']['bytes'])
                    h.update(chunk)
                p.require(total == receipt['output']['bytes'] and h.hexdigest() == receipt['output']['sha256'])
                self._counts = dict(receipt['recordCounts'])
                self._index = {role: array('Q', cached[role]) for role in ROLES}
                self._check()
                p.require(not cancelled(), 'Public data preparation was cancelled')
                self._validation_cache_hit = True
                return
            stream, h, total, count, current, seen = self._streams['observations'], hashlib.sha256(), 0, 0, 0, set()
            csv_count = pdf_count = repairs = 0
            while True:
                p.require(not cancelled(), 'Public data preparation was cancelled')
                offset = total  # Exact raw byte offset, including UTF8/CRLF; no per-row OS tell().
                line = stream.readline(MAX_LINE + 1)
                if not line:
                    break
                total += len(line)
                count += 1
                p.require(line.endswith(b'\n') and len(line) <= MAX_LINE and total <= MAX_BYTES and count <= MAX_RECORDS)
                value = p.strict_json(line)
                role = _row(value, self._documents)
                position = ROLES.index(role)
                p.require(position >= current, 'Public data source partitions are not contiguous in producer order')
                current = position
                key = bytes.fromhex(value['recordId'].removeprefix('government-observation:'))
                p.require(key not in seen, 'Duplicate public source observation was rejected')
                seen.add(key)
                if self._counts[role] % BLOCK == 0:
                    self._index[role].append(offset)
                self._counts[role] += 1
                csv_count += value['source']['locator']['kind'] == 'csv-data-row'
                pdf_count += value['source']['locator']['kind'] == 'pdf-layout-row'
                repairs += value['originalBeforeRepair'] is not None
                h.update(line)
            p.require(self._counts == receipt['recordCounts'] and count == receipt['output']['records']
                and total == receipt['output']['bytes'] and h.hexdigest() == receipt['output']['sha256'])
            p.require(receipt['normalizationCounts'] == {'houseCsvFieldEquivalentRows': csv_count,
                'housePdfCandidateJoins': pdf_count, 'senateAcceptedSubsequence': self._counts[ROLES[1]],
                'senateRawRecords': input_counts['senate-personal-unfiltered'],
                'senateExcludedRecords': input_counts['senate-personal-unfiltered'] - self._counts[ROLES[1]],
                'senateAcceptedRepairs': repairs})
            self._check()
            p.require(not cancelled(), 'Public data preparation was cancelled')
            if validation_cache is not None:
                validation_cache.save(snapshot, roles=ROLES, block=BLOCK, counts=self._counts, index=self._index)
                self._check()
                p.require(not cancelled(), 'Public data preparation was cancelled')
        except BaseException:
            self.close()
            raise

    def _check(self):
        p.require(not self._closed, 'Public data is unavailable')
        for role, stream in self._streams.items():
            p._directory(self._paths[role].parent)
            p.require(p._handle_stamp(stream) == self._stamps[role] and p._path_stamp(self._paths[role]) == self._stamps[role],
                      'Public data snapshot changed')

    def catalogue(self):
        with self._lock:
            self._check()
            return {'schemaVersion': 1, 'status': 'available', 'revision': self.revision,
                'sources': [{'id': role, 'records': self._counts[role]} for role in ROLES],
                'coverage': {'sourceNativeObservations': True, 'fullApplication': False}}

    def provenance(self):
        with self._lock:
            self._check()
            return p.strict_json(self._receipt_raw)

    def observations(self, source, offset=0, limit=100, *, revision=None):
        p.require(type(source) is str and source in ROLES)
        _int(offset, self._counts[source])
        _int(limit, 200, 1)
        p.require(revision is None or revision == self.revision, 'Public data revision changed; refresh the catalogue')
        with self._lock:
            self._check()
            rows = []
            if offset < self._counts[source]:
                stream = self._streams['observations']
                stream.seek(self._index[source][offset // BLOCK])
                for _ in range(offset % BLOCK):
                    p.require(len(stream.readline(MAX_LINE + 1)) <= MAX_LINE)
                for _ in range(min(limit, self._counts[source] - offset)):
                    line = stream.readline(MAX_LINE + 1)
                    p.require(line.endswith(b'\n') and len(line) <= MAX_LINE)
                    row = p.strict_json(line)
                    p.require(_row(row, self._documents) == source)
                    rows.append(row)
            self._check()
            following = offset + len(rows)
            return {'schemaVersion': 1, 'revision': self.revision, 'source': source, 'offset': offset,
                'limit': limit, 'total': self._counts[source], 'records': rows,
                'nextOffset': following if following < self._counts[source] else None}

    def close(self):
        for stream in self._streams.values():
            stream.close()
        self._closed = True


def prepare_public_data(snapshot, *, cancelled=lambda: False, validation_cache=None):
    from module_data_snapshot import Snapshot
    p.require(type(snapshot) is Snapshot and snapshot.app == 'melange' and snapshot.kind == KIND
              and set(snapshot.files) == set(snapshot.objects) == {'observations', 'receipt'})
    return PublicDataCatalogue(_CAPABILITY, snapshot, cancelled=cancelled, validation_cache=validation_cache)


def handle_public_data_request(handler, path, query, reader):
    """Fixed host/token-guarded server seam; no paths or private service lookup."""
    assets = {'/public-data/': ('index.html', 'text/html; charset=utf-8'),
        '/public-data/public-data.js': ('public-data.js', 'application/javascript; charset=utf-8'),
        '/public-data/public-data.css': ('public-data.css', 'text/css; charset=utf-8')}
    endpoints = {'/api/public-data/catalogue', '/api/public-data/provenance', '/api/public-data/observations'}
    if path not in assets and path not in endpoints:
        return False
    if path in assets:
        name, mime = assets[path]
        asset = Path(__file__).parent / 'public_data' / name
        p._directory(asset.parent)
        p.require(p._regular(asset).st_size <= 128 * 1024)
        handler.send_bytes(asset.read_bytes(), mime)
        return True
    try:
        p.require(type(query) is str and len(query) <= 1024)
        values = parse_qs(query, keep_blank_values=True, strict_parsing=True, max_num_fields=4)
        p.require(all(len(v) == 1 for v in values.values()))
        if path != '/api/public-data/observations':
            p.require(not values)
        else:
            p.require(set(values) <= {'source', 'offset', 'limit', 'revision'} and 'source' in values
                      and values['source'][0] in ROLES)
            for key, default in (('offset', '0'), ('limit', '100')):
                value = values.get(key, [default])[0]
                p.require(0 < len(value) <= 10 and value.isascii() and value.isdecimal())
                values[key] = int(value)
            _int(values['limit'], 200, 1)
            _int(values['offset'], MAX_RECORDS)
            if 'revision' in values:
                p._hash(values['revision'][0])
    except (ValueError, TypeError):
        handler.send_bytes(b'{"error":"Invalid public source page."}', 'application/json', 400)
        return True
    from .melange_public_pages import PagedPublicDataCatalogue
    if type(reader) not in (PublicDataCatalogue, PagedPublicDataCatalogue):
        handler.send_bytes(b'{"error":"Verified public data is not loaded."}', 'application/json', 503)
        return True
    try:
        if path.endswith('/catalogue'):
            result = reader.catalogue()
        elif path.endswith('/provenance'):
            result = reader.provenance()
        else:
            result = reader.observations(values['source'][0], values['offset'], values['limit'],
                                         revision=values.get('revision', [None])[0])
        handler.send_bytes(p.canonical(result), 'application/json; charset=utf-8')
    except (ValueError, OSError):
        handler.send_bytes(b'{"error":"Verified public data changed or is unavailable. Refresh the catalogue."}',
                           'application/json', 503)
    return True
