"""Closed analytical SQLite families and clean publication-time rebuilds.

The SQL below is packaged program code. SQL, extensions, views and triggers
from data files are never executed. Rebuilds copy selected live records only;
source freelists, WALs, request credentials and private street cells stay out.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import zlib
from functools import lru_cache

_CATALOG = '''CREATE TABLE chunks(id INTEGER PRIMARY KEY,payload BLOB NOT NULL);
CREATE TABLE entities(id TEXT PRIMARY KEY,label TEXT,kind TEXT,source TEXT,summary TEXT,chunk INTEGER,ordinal INTEGER);
CREATE TABLE relationships(id INTEGER PRIMARY KEY,subject TEXT,object TEXT,category TEXT,chunk INTEGER,ordinal INTEGER);
CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT);
CREATE INDEX entity_label ON entities(label COLLATE NOCASE);
CREATE INDEX relationship_subject ON relationships(subject,id);
CREATE INDEX relationship_object ON relationships(object,id);'''
_ACTIVITY = '''CREATE TABLE activity(id INTEGER PRIMARY KEY,source_id TEXT NOT NULL UNIQUE,start TEXT,end_exclusive TEXT,posted TEXT,filing_uuid TEXT,firm_id TEXT,issue TEXT,client_id TEXT);
CREATE TABLE named(person TEXT NOT NULL,activity INTEGER NOT NULL,edge_id TEXT NOT NULL,PRIMARY KEY(person,activity)) WITHOUT ROWID;
CREATE TABLE active_filing(filing_uuid);
CREATE TABLE member(person TEXT,filing_uuid TEXT,firm_id TEXT,client_id TEXT,start TEXT,end_exclusive TEXT,posted,activities,edge_ids);
CREATE UNIQUE INDEX active_filing_id ON active_filing(filing_uuid);
CREATE INDEX member_person ON member(person);
CREATE INDEX member_firm_period ON member(firm_id,start,end_exclusive);
CREATE INDEX member_client_period ON member(client_id,start,end_exclusive);
CREATE INDEX named_activity ON named(activity,person);'''
FACT_DIMENSIONS = ('industry','cycle','year','company','date','employer','occupation','street_1','street_2',
    'city','state','zip5','contributor','recipient','committee_id','recipient_category','party','funding_source',
    'decision_status','receipt_role','recipient_state','represented_state','recipient_location_status',
    'represented_location_status','recipient_location_evidence','represented_location_evidence')
_FACTS = 'CREATE TABLE facts(source_id TEXT PRIMARY KEY,' + ','.join('"'+name+'" TEXT NOT NULL' for name in FACT_DIMENSIONS) + ''',
contributor_key TEXT,raw_zip TEXT,raw_cents INTEGER NOT NULL,receipt_cents INTEGER NOT NULL,
original_cents INTEGER NOT NULL,supported_cents INTEGER NOT NULL,pac_cents INTEGER NOT NULL,
unresolved INTEGER NOT NULL,reasons TEXT NOT NULL,evidence_ids TEXT NOT NULL,source_url TEXT,source_table TEXT NOT NULL);
CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE INDEX facts_company_cycle ON facts(company,cycle);
CREATE INDEX facts_zip ON facts(zip5);
CREATE INDEX facts_recipient ON facts(committee_id);
CREATE INDEX facts_state ON facts(state);'''
SCHEMAS = {'source': _CATALOG,
           'lda': _CATALOG.replace('CREATE INDEX entity_label ON entities(label COLLATE NOCASE);','') + 'CREATE TABLE source_ids(id TEXT PRIMARY KEY);',
           'activity': _ACTIVITY, 'facts': _FACTS}
RAW_COLUMNS = ('sub_id','industry','transaction_id','original_sub_id','contributor_first_name','contributor_last_name','contributor_suffix',
 'contributor_aggregate_ytd','recipient_committee_type','recipient_committee_designation','entity_type','election_type',
 'fec_election_type_desc','receipt_type_full','memo_code','memoed_subtotal','filing_form','receipt_type','line_number_label',
 'back_reference_transaction_id','back_reference_schedule_name','memo_text','conduit_committee_id','conduit_committee_name',
 'amendment_indicator','report_year','report_type','file_num','two_year_transaction_period','line_number','load_date',
 'matched_variant','phase','match_confidence','scraped_at','is_conduit_leg','is_memo_leg','is_passthrough_leg','memo_review',
 'possible_amendment','superseded_by_amendment','duplicate_filing_version','duplicate_memo','is_refund','is_entity_contributor',
 'company_match_status','company_match_reason','excluded_reason')
# No affinity or uniqueness is imposed: raw_relation preserves SQLite storage
# classes and groups the actual duplicate/variant observations itself.
MENTAT_REPORTED_SQL = ''.join('CREATE TABLE '+table+'('+','.join('"'+name+'"' for name in RAW_COLUMNS)+');'
                              for table in ('contributions','corporate_giving'))
SCHEMAS['mentat-facts'] = _FACTS + MENTAT_REPORTED_SQL
_ORDER = {'chunks':'id','entities':'id','relationships':'id','metadata':'key','source_ids':'id',
          'activity':'id','named':'person,activity','active_filing':'filing_uuid',
          'member':'person,filing_uuid,firm_id,client_id,start,end_exclusive,posted,activities,edge_ids','facts':'source_id'}
_ORDER.update({table:','.join('"'+name+'"' for name in RAW_COLUMNS) for table in ('contributions','corporate_giving')})
_IDENTITY_COLUMNS = {'facts':{'source_id','contributor_key'},'entities':{'id'},
    'relationships':{'subject','object'},'source_ids':{'id'},
    'activity':{'source_id','filing_uuid','firm_id','client_id'},'named':{'person','edge_id'},
    'member':{'person','filing_uuid','firm_id','client_id'},'active_filing':{'filing_uuid'}}
_IDENTITY_COLUMNS.update({table:{'sub_id','industry'} for table in ('contributions','corporate_giving')})


def _sql(value):
    return re.sub(r'\s+', '', value or '').casefold()


def schema(db):
    rows = db.execute("SELECT type,name,tbl_name,sql FROM sqlite_schema ORDER BY type,name").fetchall()
    if len(rows) > 64 or any(kind not in ('table','index') for kind, _name, _table, _code in rows):
        raise ValueError('Analytical database contains an unsupported schema object')
    return tuple((kind, name, table, _sql(code)) for kind, name, table, code in rows)


@lru_cache(maxsize=8)
def expected_schema(family):
    if family not in SCHEMAS:
        raise ValueError('Unknown analytical database family')
    db = sqlite3.connect(':memory:')
    try:
        db.executescript(SCHEMAS[family])
        return schema(db)
    finally:
        db.close()


def require_schema(db, family):
    if schema(db) != expected_schema(family):
        raise ValueError('Analytical database does not have the compiled fixed schema')


@contextmanager
def readonly(path, family, *, expected_sha256=None, expected_bytes=None, final_hash=False):
    path = Path(path)
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or path.is_symlink() or before.st_nlink != 1 or getattr(before, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
        raise ValueError('Analytical database must be an ordinary immutable file')
    for suffix in ('-wal','-shm','-journal'):
        if Path(str(path)+suffix).exists():
            raise ValueError('Analytical database cannot carry SQLite sidecars')
    held=path.open('rb');opened=os.fstat(held.fileno())
    def physical(info):return info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_nlink
    def stamp(info):return (*physical(info),info.st_ctime_ns)
    if physical(before)!=physical(opened):
        held.close();raise ValueError('Analytical database changed while its handle was opened')
    db=None;initial_hash=None
    try:
        if expected_sha256 is not None or expected_bytes is not None:
            if not isinstance(expected_sha256,str) or re.fullmatch('[0-9a-f]{64}',expected_sha256) is None or type(expected_bytes) is not int or before.st_size != expected_bytes:
                raise ValueError('Analytical database identity is invalid')
        if expected_sha256 is not None or final_hash:
            initial_hash=hashlib.file_digest(held,'sha256').hexdigest()
            if expected_sha256 is not None and initial_hash != expected_sha256:
                raise ValueError('Analytical database hash does not match its signed input')
        db = sqlite3.connect(path.resolve().as_uri()+'?mode=ro&immutable=1', uri=True)
        db.enable_load_extension(False)
        db.execute('PRAGMA trusted_schema=OFF')
        db.execute('PRAGMA query_only=ON')
        require_schema(db, family)
        yield db
    finally:
        try:
            if db is not None:db.close()
            after,final_opened = path.lstat(),os.fstat(held.fileno())
            # Windows path-stat and handle-stat ctime can have different
            # meanings. Compare each with its OWN snapshot, cross APIs only
            # for stable physical identity, never creation/change-time.
            if stamp(before)!=stamp(after) or stamp(opened)!=stamp(final_opened) or physical(after)!=physical(final_opened):
                raise ValueError('Analytical database changed while it was read')
            if final_hash and initial_hash is not None:
                held.seek(0)
                if hashlib.file_digest(held,'sha256').hexdigest()!=initial_hash:
                    raise ValueError('Analytical database bytes changed during publication')
        finally:
            held.close()


def postal(value):
    value = str(value or '').strip()
    return value[:5] if re.fullmatch(r'[0-9]{5}(?:-?[0-9]{4})?', value) else ''


def _chunk(value, projection, context):
    decoder = zlib.decompressobj()
    raw = decoder.decompress(value, 64*1024*1024+1)
    if len(raw) > 64*1024*1024 or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
        raise ValueError('Analytical source chunk exceeds its decoded budget')
    def unique(items):
        result={}
        for key,item in items:
            if key in result:raise ValueError('Analytical source chunk has duplicate object fields')
            result[key]=item
        return result
    rows = json.loads(raw,object_pairs_hook=unique)
    if not isinstance(rows, list) or len(rows) > 10000:
        raise ValueError('Analytical source chunk has invalid records')
    projected=projection.record(rows,context)
    if projected==rows:
        # Fully decoded/checked live records can retain their compressed value;
        # the surrounding database is still rebuilt from clean fixed DDL.
        return value
    return zlib.compress(json.dumps(projected, ensure_ascii=False,
                                    separators=(',', ':'), allow_nan=False).encode('utf-8'), 3)


def rebuild(source, destination, family, projection, *, cancel=lambda:False):
    """Create a NEW deterministic DB; never replace or modify source inputs."""
    if family not in SCHEMAS:
        raise ValueError('Unknown analytical database family')
    destination = Path(destination)
    with destination.open('xb'):
        pass
    output = sqlite3.connect(destination)
    counts, hashes = {}, {}
    try:
        output.execute('PRAGMA journal_mode=OFF')
        output.execute('PRAGMA synchronous=OFF')
        output.execute('PRAGMA temp_store=FILE')
        output.execute('PRAGMA cache_size=-32768')
        # Indices are created before insertion so final bytes are repeatable.
        output.executescript(SCHEMAS[family])
        with readonly(source, family, final_hash=True) as incoming:
            tables = [name for kind,name,_table,_code in expected_schema(family) if kind == 'table']
            for table in tables:
                columns = [row[1] for row in incoming.execute('PRAGMA table_info("'+table+'")')]
                order = _ORDER[table]
                cursor = incoming.execute('SELECT * FROM "'+table+'" ORDER BY '+order)
                count, rowhash = 0, hashlib.sha256()
                for row in cursor:
                    if cancel():
                        raise InterruptedError('Analytical publication was cancelled')
                    result = list(row)
                    for index, (name, value) in enumerate(zip(columns, row)):
                        if table == 'chunks' and name == 'payload':
                            result[index] = _chunk(value, projection, family+'/chunks/[]')
                        elif family in ('facts','mentat-facts') and table == 'facts' and name in ('street_1','street_2'):
                            result[index] = ''
                            if value:
                                projection.changed('donor-street', 'facts/'+name, value, '')
                        elif family in ('facts','mentat-facts') and table == 'facts' and name == 'raw_zip':
                            result[index] = postal(value)
                            if result[index] != value:
                                projection.changed('donor-postal-precision', 'facts/raw_zip', value, result[index])
                        elif isinstance(value, str):
                            if name in _IDENTITY_COLUMNS.get(table,()):
                                # Existing assigned identities are never regrouped
                                # or rewritten by a display/privacy projection.
                                continue
                            # Metadata values can contain nested encoded request URLs.
                            if table == 'metadata':
                                try:
                                    decoded = json.loads(value)
                                except (ValueError, TypeError):
                                    decoded = None
                                if isinstance(decoded, (dict,list)):
                                    if family in ('facts','mentat-facts') and isinstance(decoded,dict):
                                        decoded.pop('token', None); decoded.pop('built_at', None)
                                        if isinstance(decoded.get('provenance'),dict):
                                            decoded['provenance'].pop('index_token', None)
                                    result[index] = json.dumps(projection.record(decoded, family+'/metadata'), ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
                                    continue
                            result[index] = projection.text(value, family+'/'+table+'/'+name)
                    values = tuple(result)
                    output.execute('INSERT INTO "'+table+'" VALUES ('+','.join('?' for _ in values)+')', values)
                    encoded = [hashlib.sha256(value).hexdigest() if isinstance(value,bytes) else value for value in values]
                    rowhash.update(json.dumps(encoded,ensure_ascii=False,separators=(',', ':'),allow_nan=False).encode('utf-8')+b'\n')
                    count += 1
                counts[table], hashes[table] = count, rowhash.hexdigest()
        output.commit()
        require_schema(output, family)
        if output.execute('PRAGMA integrity_check').fetchone() != ('ok',) or output.execute('PRAGMA freelist_count').fetchone() != (0,):
            raise ValueError('Clean analytical database failed integrity/free-page validation')
    finally:
        output.close()
    with destination.open('rb') as published:
        published_hash = hashlib.file_digest(published,'sha256').hexdigest()
    return {'schemaVersion':1,'family':family,'rows':counts,'rowSha256':hashes,
            'bytes':destination.stat().st_size,'sha256':published_hash}
