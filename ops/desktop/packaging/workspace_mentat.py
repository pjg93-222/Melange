"""Fixed, read-only Mentat inputs and native HTTP consumers.

The installed query planners, statistical engines and forecast calculations are
reused. Signed facts replace source discovery; no report/source database, code,
private console directory or application state is selected by downloaded data.
"""
from collections import OrderedDict
import copy
import builtins
import hashlib
import hmac
from http.server import ThreadingHTTPServer
import json
import math
from pathlib import Path
import sqlite3
import sys
import threading
from types import MappingProxyType, ModuleType
from urllib.parse import parse_qs, urlsplit

from module_application_contracts import DataIntakeBlocked, ProgramFile, require
from module_data_snapshot import Snapshot, parse, ReadAliases
from workspace_data_contract import REPORT_ANALYSIS_KIND, REPORT_INDUSTRIES
from workspace_sqlite import readonly, require_schema

FORECAST_KIND = 'mentat.aggregate-forecast-core.v1'
REPORTS = MappingProxyType(dict(zip(REPORT_INDUSTRIES, (
    ('Banking', 'Banking Industry Spending Overview.xlsx'),
    ('Credit Union', 'Credit Union Industry Spending Overview.xlsx'),
    ('Property & Casualty Insurance', 'Property & Casualty Insurance Industry Spending Overview.xlsx'),
    ('Telecom', 'Telecom Industry Spending Overview.xlsx'),
    ('Community Banks', 'Community Banks Industry Spending Overview.xlsx'),
    ('Credit Arms', 'Credit Arms Industry Spending Overview.xlsx'),
    ('Fintech', 'Fintech Industry Spending Overview.xlsx'),
    ('Crypto', 'Crypto Industry Spending Overview.xlsx')))))
FINANCIAL = ('raw_cents', 'receipt_cents', 'original_cents', 'supported_cents', 'pac_cents', 'unresolved')


def data_require(value):
    if not value:
        raise DataIntakeBlocked('integrity')


def read_json(path, maximum=4 * 1024**2):
    raw = path.read_bytes()
    data_require(len(raw) <= maximum)
    try:
        value = parse(raw)
    except (ValueError, UnicodeError, RecursionError):
        raise DataIntakeBlocked('integrity') from None
    return value


class MentatComponentContent:
    def __init__(self, kind, *, models=None, archives=(), facts=None, supplemental=None):
        self.kind, self.models, self.archives = kind, models, tuple(archives)
        self.facts, self.supplemental = MappingProxyType(dict(facts or {})), MappingProxyType(dict(supplemental or {}))
        self.closed = False

    def verify(self):
        return not self.closed and all(archive.verify() is True for archive in self.archives)

    def close(self):
        if self.closed:
            return
        self.closed = True
        for archive in self.archives:
            archive.close()


def prepare(snapshot, *, source, profile, program_fingerprint, is_cancelled=lambda: False):
    from module_workspace_inputs import WorkspaceComponent, extract_archive
    require(type(snapshot) is Snapshot and snapshot.app == 'mentat'
            and snapshot.kind in (FORECAST_KIND, REPORT_ANALYSIS_KIND))
    content = None
    try:
        if snapshot.kind == FORECAST_KIND:
            from mentat_module_data import validate
            # This fixed routine is the existing data-schema boundary, not an
            # import/program-error catch. Source-program failures remain fatal.
            try:
                models = validate(snapshot, full_workspace=True)
            except ValueError as error:
                if type(error) is ValueError:
                    raise DataIntakeBlocked('integrity') from None
                raise
            content = MentatComponentContent(snapshot.kind, models=models)
        else:
            supplemental = extract_archive(snapshot, profile, 'supplemental-reports', is_cancelled=is_cancelled)
            try:
                facts_archive = extract_archive(snapshot, profile, 'facts', is_cancelled=is_cancelled)
            except Exception:
                supplemental.close()
                raise
            content = MentatComponentContent(snapshot.kind, archives=(supplemental, facts_archive))
            facts = {}
            for slug in REPORT_INDUSTRIES:
                if is_cancelled():
                    raise InterruptedError('Workspace input preparation was cancelled')
                path, receipt_path = facts_archive.paths[slug + '/index.sqlite'], facts_archive.paths[slug + '/receipt.json']
                receipt = read_json(receipt_path)
                data_require(type(receipt) is dict and type(receipt.get('schemaVersion')) is int and receipt.get('schemaVersion') == 1
                    and receipt.get('industry') == slug and receipt.get('label') == REPORTS[slug][0]
                    and receipt.get('sourceWorkbook') == REPORTS[slug][1]
                    and receipt.get('sourceIdsAndFinancialValuesPreserved') is True
                    and receipt.get('donorStreetValuesIncluded') is False)
                member = facts_archive.derivation['members'][slug + '/index.sqlite']
                data_require(type(receipt.get('index')) is dict
                             and receipt['index'].get('sha256') == member['sha256']
                             and type(receipt['index'].get('bytes')) is int and receipt['index']['bytes'] == member['bytes']
                             and type(receipt['index'].get('rows')) is dict
                             and type(receipt['index']['rows'].get('facts')) is int)
                try:
                    with readonly(path, 'mentat-facts') as db:
                        expected = receipt['financialParity']['countAndFinancial']
                        data_require(type(expected) is list and len(expected) == 7
                                     and all(type(value) is int and abs(value) <= 2**63-1 for value in expected))
                        actual = list(db.execute('SELECT COUNT(*),' + ','.join('COALESCE(SUM('+name+'),0)' for name in FINANCIAL) + ' FROM facts').fetchone())
                        data_require(actual == expected and actual[0] == receipt['index']['rows']['facts'])
                        manifest = json.loads(db.execute("SELECT value FROM metadata WHERE key='manifest'").fetchone()[0])
                        data_require(manifest['totals']['records'] == actual[0]
                                     and manifest['totals']['receipt'] == actual[2])
                except (sqlite3.DatabaseError, KeyError, ValueError) as error:
                    if type(error) is DataIntakeBlocked:
                        raise
                    raise DataIntakeBlocked('integrity') from None
                facts[slug] = {'path': path, 'receipt_path': receipt_path, 'receipt': receipt}
            content.facts = MappingProxyType(facts)
            content.supplemental = MappingProxyType({slug: supplemental.paths[slug.replace('_', '-') + '.xlsx']
                for slug in ('credit_arms', 'fintech', 'crypto')})
        return WorkspaceComponent(snapshot, source, profile, program_fingerprint, content, is_cancelled=is_cancelled)
    except Exception:
        if content is not None:
            content.close()
        raise


_MODULES = ('contribution_data', 'contribution_query_store', 'contribution_semantics', 'records_sidecar',
            'contribution_query', 'snapshot_registry', 'industry_scope', 'contribution_workbook_guard',
            'analysis_history', 'analysis_scan', 'analysis_metrics', 'analysis_integrations', 'analysis_data')


def isolated_programs(snapshot, *, program_files):
    """Fixed native-source modules, isolated before any HTTP/service thread."""
    prior = {name: sys.modules.get(name) for name in _MODULES}
    old_path, bytecode = list(sys.path), sys.dont_write_bytecode
    loaded = {}
    require(type(program_files) is tuple and all(type(row) is ProgramFile for row in program_files))
    expected = {row.path: row for row in program_files if row.root == 'source'}
    original_import = builtins.__import__
    def scoped_import(name, globals=None, locals=None, fromlist=(), level=0):
        if level == 0 and name in _MODULES:
            return load_fixed(name)
        return original_import(name, globals, locals, fromlist, level)
    def load_fixed(name):
        if name in loaded:
            return loaded[name]
        relative = 'mentat/app/' + name + '.py'
        path = snapshot.source_file(relative)
        row = expected.get(relative)
        raw = path.read_bytes()
        require(row is not None and len(raw) == row.bytes and hashlib.sha256(raw).hexdigest() == row.sha256)
        unique = '_workspace_mentat_' + hashlib.sha256(str(path).encode()).hexdigest() + '_' + name
        module = ModuleType(unique)
        module.__file__, module.__package__ = str(path), ''
        module.__dict__['__builtins__'] = {**vars(builtins), '__import__': scoped_import}
        loaded[name] = module
        sys.modules[name] = sys.modules[unique] = module
        # These are the exact compiled native program bytes, checked against
        # its immutable ProgramFile table above. No dataset supplies code.
        exec(compile(raw, str(path), 'exec'), module.__dict__)
        return module
    try:
        sys.dont_write_bytecode = True
        app = snapshot.source_file('mentat/app/contribution_data.py').parent
        sys.path[:0] = [str(app), str(snapshot.source_file('mentat/tools/cross_reference_engine.py').parent)]
        for name in _MODULES:
            sys.modules.pop(name, None)
        for name in _MODULES:
            load_fixed(name)
        return loaded
    finally:
        sys.path[:] = old_path
        sys.dont_write_bytecode = bytecode
        for name, module in prior.items():
            sys.modules.pop(name, None)
            if module is not None:
                sys.modules[name] = module


class _FactPath:
    """An actual signed fact file, paired with its actual signed receipt."""
    def __init__(self, path, receipt):
        self.path, self.receipt = Path(path), Path(receipt)

    def __fspath__(self):
        return str(self.path)

    def __str__(self):
        return str(self.path)

    def with_suffix(self, suffix):
        require(suffix == '.json')
        return self.receipt


class MentatBinding:
    def __init__(self, server, prepared):
        from module_public_input_installers import _program_module
        module = _program_module(prepared.roots['sourceRoot'], 'mentat', server=True)
        require(type(server) is ThreadingHTTPServer and type(server.app) is module.Console)
        self.server, self.prepared, self.module, self.console = server, prepared, module, server.app
        self.originals = (self.console.root, self.console.report_directory, self.console.report_cache)
        self.state_directories = ()
        self.components = tuple(bound['reader'] for bound in prepared.readers.values())
        parts = {component.snapshot.kind: component for component in self.components}
        self.forecast, self.analysis = parts[FORECAST_KIND].content, parts[REPORT_ANALYSIS_KIND].content
        require(type(self.forecast) is MentatComponentContent and type(self.analysis) is MentatComponentContent)
        self.books = {**{slug: self.forecast.models['workbook_path'](label)
            for slug, (_name, label) in REPORTS.items() if slug not in self.analysis.supplemental}, **self.analysis.supplemental}
        self.book_aliases = ReadAliases({REPORTS[slug][1]: path for slug, path in self.books.items()}, 'workspace-reports')
        # Existing forecast role IDs use the original model cohort spellings.
        self.programs = isolated_programs(parts[REPORT_ANALYSIS_KIND].snapshot,
                                          program_files=prepared.contract.program_files)
        self.engine, self.query = self.programs['contribution_data'], self.programs['contribution_query']
        self.store, self.semantics = self.programs['contribution_query_store'], self.programs['contribution_semantics']
        self.sources = []
        self.by_path = {}
        for slug in REPORT_INDUSTRIES:
            item = self.analysis.facts[slug]
            receipt, path = item['receipt'], item['path']
            data_require(hashlib.sha256(self.books[slug].read_bytes()).hexdigest() == receipt.get('projectedWorkbookSha256'))
            source = {'id': REPORTS[slug][0], 'industry': REPORTS[slug][0], 'label': REPORTS[slug][0],
                'available': True, 'workbook': self.book_aliases.path(REPORTS[slug][1]), 'workbook_sha256': receipt['projectedWorkbookSha256'],
                'database': path, 'database_sha256': receipt['index']['sha256'], 'payload_sha256': receipt['payloadSha256'],
                'original_database_sha256': receipt['databaseSha256'], 'data_workbook': None, 'destination_schema': 1,
                'workspace_source': prepared.binding['sourceDigest'], 'workspace_slug': slug}
            self.sources.append(source)
            self.by_path[str(path.resolve())] = item
        self._wire_readers()

    def _source(self, source):
        require(type(source) is dict and any(source.get('id') == item['id'] and source.get('workspace_source') == item['workspace_source'] for item in self.sources))
        return self.analysis.facts[source['workspace_slug']]

    def _readonly(self, path):
        require(str(Path(path).resolve()) in self.by_path and self.verify())
        db = sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro&immutable=1', uri=True)
        try:
            db.enable_load_extension(False)
            db.execute('PRAGMA trusted_schema=OFF')
            db.execute('PRAGMA query_only=ON')
            require_schema(db, 'mentat-facts')
            db.row_factory = sqlite3.Row
            return db
        except Exception:
            db.close()
            raise

    def _wire_readers(self):
        data, query, store = self.engine, self.query, self.store
        data._sources = lambda _directory: [dict(source) for source in self.sources]
        data._ready = lambda source, **_options: (self._source(source)['path'], None)
        data._token = lambda source: self._source(source)['receipt']['index']['sha256']
        data._ro = self._readonly
        original_provenance = data._provenance
        data._provenance = lambda source: {**original_provenance(source),
            'workspace_source_digest': self.prepared.binding['sourceDigest'],
            'original_workbook_sha256': self._source(source)['receipt']['originalWorkbookSha256']}
        registry = self.programs['snapshot_registry']
        original_entry = registry.entry
        def entry(source):
            result = original_entry(source)
            result['workbook']['name'] = REPORTS[source['workspace_slug']][1]
            return result
        registry.entry = entry
        # Select the existing planner's full-fact relations directly. Its real
        # proof-path guard observes the signed receipt, not an unsigned marker.
        store.view = lambda path: _FactPath(path, self.by_path[str(Path(path).resolve())]['receipt_path'])
        store.tables = lambda _dimensions, _filters: ('facts', 'facts')
        store._readonly = self._readonly
        native_table = self.semantics.table
        def original_fact_table(base, refs, request, *, original=False, raw_relation=None):
            # The signed source relation has rowid/source_id, whereas the
            # optional optimized projection uses fact_id. Select the existing
            # original-fact branch for both queries and record inspection.
            return native_table(base, refs, request, original=True, raw_relation=raw_relation)
        self.semantics.table = original_fact_table
        query._view_ready = lambda path: str(Path(path).resolve()) in self.by_path and self.verify()
        query.sidecar.eligible = lambda _path: False
        self.cache, self.cache_lock = OrderedDict(), threading.RLock()
        def cached(namespace, identity, build, stable):
            key = (namespace, json.dumps(identity, sort_keys=True, separators=(',', ':'), default=str))
            require(stable() and self.verify())
            with self.cache_lock:
                raw = self.cache.get(key)
            if raw is None:
                result = build()
                require(stable() and self.verify())
                raw = json.dumps(result, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
                if len(raw) <= 4 * 1024**2:
                    with self.cache_lock:
                        self.cache[key] = raw
                        while len(self.cache) > 16:
                            self.cache.popitem(last=False)
            return json.loads(raw)
        store.cached = cached
        self.programs['contribution_workbook_guard'].verify_sources = self._verified_sources
        # All analytical journals/hints belong to a separate native-owned
        # derived cache. The original console/report/state paths stay intact.
        state = Path(self.prepared.roots['profileRoot']) / 'packs/github-workspace-analysis' / self.prepared.binding['sourceDigest']
        from workspace_cache import fixed_directory
        parent = fixed_directory(Path(self.prepared.roots['profileRoot']), 'packs')
        parent = fixed_directory(parent, 'github-workspace-analysis')
        state = fixed_directory(parent, self.prepared.binding['sourceDigest'])
        store.ROOT = fixed_directory(state, 'query')
        # Observation history is private app state, not a disposable versioned
        # result cache. Keep it stable when a newer signed dataset is selected.
        self.programs['analysis_history'].ROOT = fixed_directory(parent, 'history')
        analysis = self.programs['analysis_data']
        analysis.ROOT = fixed_directory(state, 'insights')
        from workspace_cache import directory_id
        self.state_directories = tuple((path, directory_id(path)) for path in
            (parent, state, store.ROOT, self.programs['analysis_history'].ROOT, analysis.ROOT))
        def probe(identity):
            key = ('insights', json.dumps(identity, sort_keys=True, separators=(',', ':'), default=str))
            with self.cache_lock:
                value = self.cache.get(key)
            return json.loads(value) if value is not None else None
        analysis._probe = probe

    def _verified_sources(self, _directory, dataset=None, *, sources=None, **_options):
        require(self.verify())
        return [{'dataset': source['id'], 'matched': True, 'workbook_sha256': source['workbook_sha256'],
            'database_sha256': source['database_sha256'], 'source_financial_universe_verified': True,
            'source_proof_token': self._source(source)['receipt']['financialParity']['financialIdentitySha256']}
            for source in self.sources if dataset is None or source['id'] == dataset]

    def verify(self):
        from workspace_cache import directory_id
        return self.server.app is self.console and (self.console.root is self.originals[0]) \
            and (self.console.report_directory is self.originals[1]) and (self.console.report_cache is self.originals[2]) \
            and all(directory_id(path) == identity for path, identity in self.state_directories) \
            and all(component.verify() is True for component in self.components)

    def _scope(self, body):
        scope = self.programs['industry_scope']
        entry = scope.from_body(self.console.report_directory, body, self.sources)
        if entry is not None and 'dataset' not in body:
            body['dataset'] = entry['dataset']
        body.pop('industry', None)
        return entry

    def _catalog(self):
        return self.semantics.catalog(self.console.report_directory, self.sources)

    def _graph_catalog(self, identifier):
        if identifier != 'published-reports':
            raise ValueError('Choose a verified workspace report.')
        industries = []
        for slug, path in self.books.items():
            if self.module.graph_schema(self.module.stamp(path)):
                label, filename = REPORTS[slug]
                industries.append({'name': label,
                    'indices': [int(hashlib.sha256(filename.encode()).hexdigest()[:12], 16)]})
        return {'industries': sorted(industries, key=lambda item: item['name']),
                'unavailable_reports': [], 'report_directory': 'Verified GitHub workspace',
                'message': '' if industries else 'No supported reports are available in the verified workspace.'}

    def _graph(self, identifier, industry, filters):
        catalog = self._graph_catalog(identifier)
        slug = next((slug for slug in self.books if industry in (slug, REPORTS[slug][0])), None)
        if slug is None or not any(item['name'] == REPORTS[slug][0] for item in catalog['industries']):
            raise ValueError('Choose an industry with completed reports.')
        path, (label, filename) = self.books[slug], REPORTS[slug]
        # Use the installed graph engine and its source/cache guards unchanged.
        # Only the fixed, verified workbook selection differs from local mode.
        result = copy.deepcopy(self.module.graph_view([path], filters))
        receipt = self.analysis.facts[slug]['receipt']
        data_require(len(result.get('reports', [])) == 1
                     and result['reports'][0].get('sha256') == receipt['projectedWorkbookSha256'])
        registry = self.programs['snapshot_registry'].registry(self.console.report_directory, self.sources)
        entry = next(item for item in registry['snapshots'] if item['industry'] == label)
        result['reports'][0].update(name=filename, source_directory='Verified GitHub workspace',
                                   build_stamp=entry['build_stamp'], freshness=self.module.report_freshness(path))
        result.update(industry=label, report_directory='Verified GitHub workspace',
                      workspace_source_digest=self.prepared.binding['sourceDigest'])
        return result

    def handle_request(self, handler):
        require(handler.server is self.server and self.verify())
        parsed = urlsplit(handler.path)
        gets = {'/api/contributions/session', '/api/contributions/catalog', '/api/insights/catalog',
                '/api/forecast/pac', '/api/forecast/catalog', '/api/reports', '/api/report-sources', '/api/report', '/api/report-data',
                '/api/graph-catalog', '/api/graph'}
        posts = {'/api/contributions/query', '/api/contributions/records', '/api/insights/query', '/api/insights/records', '/api/forecast/project'}
        if parsed.path not in gets | posts:
            return False
        if not handler.valid_host():
            handler.send({'error': 'Local access only.'}, 403)
            return True
        try:
            if handler.command == 'POST' and parsed.path in posts:
                if (not hmac.compare_digest(handler.headers.get('X-Mentat-Token', ''), handler.session_token())
                        or handler.headers.get('Origin') and not handler.valid_origin(handler.headers['Origin'])):
                    handler.discard_body()
                    handler.send({'error': 'Refresh the app before continuing.'}, 403)
                    return True
                length = int(handler.headers.get('Content-Length', '0'))
                if not 0 < length <= 7_000_000 or handler.headers.get('Transfer-Encoding'):
                    raise ValueError('Request is empty or too large.')
                body = json.loads(handler.rfile.read(length))
                if type(body) is not dict:
                    raise ValueError('Expected an analytical request.')
                if parsed.path == '/api/forecast/project':
                    result = self.forecast.models['giving'].project(body)
                else:
                    entry = self._scope(body)
                    engine = self.query if parsed.path.startswith('/api/contributions/') else self.programs['analysis_data']
                    function = engine.query if parsed.path.endswith('/query') else engine.records
                    result = function(self.console.report_directory, body, self.sources)
                    if type(result) is dict:
                        source = next((source for source in self.sources if source['id'] == body.get('dataset')), None)
                        if source is not None and type(result.get('provenance')) is dict:
                            result['provenance'].update(self.engine._provenance(source))
                            result['provenance'].pop('query_projection_sha256', None)
                            result['provenance']['query_plan'] = 'native-planner-over-signed-facts'
                        result.update(self.programs['industry_scope'].echo(entry))
                require(self.verify())
                handler.send(result)
                return True
            if handler.command != 'GET' or parsed.path not in gets:
                handler.send({'error': 'Method not allowed.'}, 405)
                return True
            query = parse_qs(parsed.query, keep_blank_values=True)
            if any(len(values) != 1 for values in query.values()):
                raise ValueError('Duplicate request selector.')
            if parsed.path == '/api/graph-catalog':
                result = self._graph_catalog(query.get('id', [''])[0])
            elif parsed.path == '/api/graph':
                result = self._graph(query.get('id', [''])[0], query.get('industry', [''])[0],
                                     {key: values[0] for key, values in query.items()})
            elif parsed.path == '/api/forecast/pac':
                result = self.forecast.models['pac'].catalog()
            elif parsed.path == '/api/forecast/catalog':
                result = self.forecast.models['giving'].catalog()
            elif parsed.path == '/api/contributions/catalog':
                result = self._catalog()
            elif parsed.path == '/api/insights/catalog':
                result = self.programs['analysis_data'].catalog(self.console.report_directory, self.sources)
            elif parsed.path == '/api/contributions/session':
                registry = self.programs['snapshot_registry'].registry(self.console.report_directory, self.sources)
                result = {'token': handler.session_token(), 'read_only': True, 'industry': None,
                    'industries': [{key: item[key] for key in ('industry', 'slug', 'available', 'build_stamp')} for item in registry['snapshots']]}
            elif parsed.path == '/api/report-sources':
                result = {'runs': [{'id': 'published-reports', 'name': 'Verified GitHub workspace', 'state': 'completed'}],
                          'report_directory': 'Verified GitHub workspace'}
            elif parsed.path == '/api/reports':
                result = {'reports': [{'index': int(hashlib.sha256(REPORTS[slug][1].encode()).hexdigest()[:12], 16),
                    'name': REPORTS[slug][1], 'industry': REPORTS[slug][0], 'kind': 'overview'} for slug, path in self.books.items()],
                    'report_directory': 'Verified GitHub workspace'}
            else:
                if query.get('id', [''])[0] != 'published-reports':
                    raise ValueError('Choose a verified workspace report.')
                index = int(query.get('index', ['-1'])[0])
                path = next((path for slug, path in self.books.items() if int(hashlib.sha256(REPORTS[slug][1].encode()).hexdigest()[:12], 16) == index), None)
                if path is None:
                    raise ValueError('Choose a verified workspace report.')
                if parsed.path == '/api/report':
                    handler.send(path.read_bytes(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    return True
                result = self.module.worksheet_data(self.module.stamp(path), query.get('sheet', [''])[0], int(query.get('header', ['0'])[0]))
            require(self.verify())
            handler.send(result)
            return True
        except (ValueError, KeyError, sqlite3.DatabaseError) as error:
            if isinstance(error, DataIntakeBlocked):
                raise
            handler.send({'error': 'The requested verified workspace view could not be prepared.'}, 400)
            return True


def bind(server, prepared):
    return MentatBinding(server, prepared)
