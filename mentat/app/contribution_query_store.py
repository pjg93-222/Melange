"""Disposable query acceleration, derived from immutable contribution indexes.

Amounts and observations are copied, never reclassified or aggregated here.
The small fact table keeps common chart scans away from long audit/detail text.
"""
from collections import OrderedDict
from contextlib import closing,contextmanager
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import threading
import time
import uuid

import contribution_data as data

ROOT=data.PROJECT/'state/contribution-query-cache'
CORE=('cycle','year','company','date','zip5','state')
DETAIL=tuple(k for k in data.DIMENSIONS if k not in CORE)
MONEY=('raw_cents','receipt_cents','original_cents','supported_cents','pac_cents','unresolved')
LOADED_STAMP=data._stamp(__file__)
LOADED_SHA=data._hash(__file__)
_mutex=threading.RLock()
_locks={}
_memory=OrderedDict()
_memory_bytes=0
_verified={}
MEMORY_LIMIT=32*1024*1024
ENTRY_LIMIT=24*1024*1024

def _loaded():
    if data._stamp(__file__)!=LOADED_STAMP:raise ValueError('Query cache code changed. Restart the app to load the current rules.')

def _key(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def source_stable(path,stamp):
    try:
        if data._stamp(path)!=stamp:return False
        return not any(p.exists() and p.stat().st_size for suffix in ('-wal','-journal') if (p:=Path(str(path)+suffix)))
    except OSError:return False

@contextmanager
def _lock(path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with _mutex:mutex=_locks.setdefault(str(path),threading.RLock())
    with mutex:
        with path.open('a+b') as stream:
            if stream.tell()==0:stream.write(b'0');stream.flush()
            stream.seek(0)
            if os.name=='nt':
                import msvcrt
                while True:
                    try:msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1);break
                    except OSError:time.sleep(.025)
                try:yield
                finally:stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
            else:
                import fcntl
                fcntl.flock(stream,fcntl.LOCK_EX)
                try:yield
                finally:fcntl.flock(stream,fcntl.LOCK_UN)

def _atomic(path,payload):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    pending=path.with_suffix('.'+uuid.uuid4().hex+'.pending')
    try:pending.write_bytes(payload);os.replace(pending,path)
    finally:
        if pending.exists():pending.unlink()

def _readonly(path):
    db=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True)
    db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON')
    return db

def _valid(path,proof_path,identity):
    if path.exists() and not source_stable(path,data._stamp(path)):
        raise ValueError('The query projection has active writes; retry after they finish.')
    try:
        stamp=(data._stamp(path),data._stamp(proof_path))
        with _mutex:
            if _verified.get(str(path))==stamp:return True
        proof=json.loads(proof_path.read_text())
        if not isinstance(proof,dict):return False
        if proof['identity']!=identity or data._hash(path)!=proof['sha256']:return False
        if not source_stable(path,stamp[0]) or (data._stamp(path),data._stamp(proof_path))!=stamp:return False
        with _mutex:_verified[str(path)]=stamp
        return True
    except (OSError,ValueError,KeyError,TypeError):return False

def view(source_path):
    """Return an exactly copied, narrower query index; coordinate all builders."""
    _loaded();source_path=Path(source_path);stamp=data._stamp(source_path)
    identity={'source_stamp':list(stamp),'projection_code':LOADED_SHA}
    key=_key(identity);path=ROOT/'views'/(key+'.sqlite');proof_path=path.with_suffix('.json')
    if not source_stable(source_path,stamp):raise ValueError('The contribution index has active writes.')
    if _valid(path,proof_path,identity):return path
    with _lock(path.with_suffix('.lock')):
        if not source_stable(source_path,stamp):raise ValueError('Contribution index changed while preparing its query view.')
        if _valid(path,proof_path,identity):return path
        pending=path.with_suffix('.'+uuid.uuid4().hex+'.pending');started=time.perf_counter()
        try:
            original_sha=data._hash(source_path)
            with closing(sqlite3.connect(pending,uri=True)) as db:
                db.execute('PRAGMA journal_mode=OFF');db.execute('PRAGMA synchronous=OFF')
                db.execute('ATTACH DATABASE ? AS original',(source_path.resolve().as_uri()+'?mode=ro',))
                metadata=json.loads(db.execute("SELECT value FROM original.metadata WHERE key='manifest'").fetchone()[0])
                db.execute('CREATE TABLE donors(id INTEGER PRIMARY KEY,value TEXT UNIQUE NOT NULL)')
                db.execute('INSERT INTO donors(value) SELECT DISTINCT contributor_key FROM original.facts WHERE contributor_key IS NOT NULL')
                db.execute('CREATE TABLE facts(fact_id INTEGER PRIMARY KEY,'+','.join('"'+k+'" TEXT NOT NULL' for k in CORE)+',contributor_key INTEGER,'+','.join(k+' INTEGER NOT NULL' for k in MONEY)+')')
                db.execute('INSERT INTO facts SELECT s.rowid,'+','.join('s."'+k+'"' for k in CORE)+',d.id,'+','.join('s.'+k for k in MONEY)+' FROM original.facts s LEFT JOIN donors d ON d.value=s.contributor_key')
                db.execute('CREATE TABLE detail(fact_id INTEGER PRIMARY KEY,'+','.join('"'+k+'" TEXT NOT NULL' for k in DETAIL)+')')
                db.execute('INSERT INTO detail SELECT rowid,'+','.join('"'+k+'"' for k in DETAIL)+' FROM original.facts')
                db.execute('CREATE VIEW facts_full AS SELECT f.*,'+','.join('d."'+k+'"' for k in DETAIL)+' FROM facts f JOIN detail d ON d.fact_id=f.fact_id')
                db.executescript('CREATE INDEX facts_company_cycle ON facts(company,cycle); CREATE INDEX facts_zip ON facts(zip5); CREATE INDEX facts_state ON facts(state); CREATE INDEX detail_recipient ON detail(committee_id);')
                # An identity-preserving join proves each copied field, not just
                # balanced totals. Donor IDs must decode to the exact source key.
                checks=['f.fact_id IS NULL','d.fact_id IS NULL','f.contributor_key IS NOT NULL AND ids.value IS NULL']
                checks += ['f."'+k+'" IS NOT s."'+k+'"' for k in CORE+MONEY]
                checks += ['d."'+k+'" IS NOT s."'+k+'"' for k in DETAIL]
                checks += ['ids.value IS NOT s.contributor_key']
                mismatch=db.execute('SELECT COUNT(*) FROM original.facts s LEFT JOIN facts f ON f.fact_id=s.rowid LEFT JOIN detail d ON d.fact_id=s.rowid LEFT JOIN donors ids ON ids.id=f.contributor_key WHERE '+' OR '.join(checks)).fetchone()[0]
                count=db.execute('SELECT COUNT(*) FROM original.facts').fetchone()[0]
                if mismatch or db.execute('SELECT COUNT(*) FROM facts').fetchone()[0]!=count or db.execute('SELECT COUNT(*) FROM detail').fetchone()[0]!=count:raise ValueError('The query projection does not preserve every contribution field.')
                db.execute('CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL)')
                db.execute('INSERT INTO metadata VALUES (?,?)',('manifest',json.dumps(metadata)))
                db.commit()
                if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('The query projection failed integrity verification.')
            if not source_stable(source_path,stamp):raise ValueError('Contribution index changed while preparing its query view.')
            proof={'identity':identity,'sha256':data._hash(pending),'source_index_sha256':original_sha,'fact_count':count,'field_mismatches':mismatch,'seconds':round(time.perf_counter()-started,6)}
            os.replace(pending,path);_atomic(proof_path,json.dumps(proof,sort_keys=True).encode())
            with _mutex:_verified[str(path)]=(data._stamp(path),data._stamp(proof_path))
            return path
        finally:
            if pending.exists():pending.unlink()

def tables(dimensions,filters):
    fields={f.get('field') for f in filters if isinstance(f,dict)}
    return ('facts_full' if (set(dimensions)|fields)&set(DETAIL) else 'facts',
            'facts_full' if fields&set(DETAIL) else 'facts')

def _remember(key,payload):
    global _memory_bytes
    if len(payload)>ENTRY_LIMIT:return
    with _mutex:
        previous=_memory.pop(key,None)
        if previous:_memory_bytes-=len(previous)
        _memory[key]=payload;_memory_bytes+=len(payload)
        while _memory_bytes>MEMORY_LIMIT:
            _,old=_memory.popitem(last=False);_memory_bytes-=len(old)

def _prune(directory):
    # Only disposable response JSON is removed. Lock files remain to preserve
    # cross-process locking identities, and source/index files are untouched.
    try:
        files=sorted(((p.stat().st_mtime_ns,p.stat().st_size,p) for p in directory.glob('*.json')),reverse=True)
        total=0
        for index,(_,size,path) in enumerate(files):
            total+=size
            if index>=128 or total>128*1024*1024:
                if path.resolve().is_relative_to((ROOT/'responses').resolve()):path.unlink(missing_ok=True)
    except OSError:pass

def cached(namespace,identity,compute,stable=lambda:True):
    """Return fresh object copies and publish only stable, complete responses."""
    _loaded();key=_key([LOADED_SHA,namespace,identity]);path=ROOT/'responses'/namespace/(key+'.json')
    def read():
        with _mutex:
            payload=_memory.get(key)
            if payload is not None:_memory.move_to_end(key);return payload
        try:
            envelope=json.loads(path.read_bytes())
            if not isinstance(envelope,dict):return None
            payload=envelope['payload'].encode('utf-8')
            if envelope['key']!=key or hashlib.sha256(payload).hexdigest()!=envelope['sha256']:return None
            _remember(key,payload);return payload
        except (OSError,ValueError,KeyError,AttributeError,TypeError):return None
    if not stable():raise ValueError('Contribution source changed before its query completed.')
    payload=read()
    if payload is None:
        with _lock(path.with_suffix('.lock')):
            payload=read()
            if payload is None:
                result=compute()
                if not stable():raise ValueError('Contribution source changed while computing its query.')
                payload=json.dumps(result,ensure_ascii=False,separators=(',',':')).encode('utf-8')
                if len(payload)<=ENTRY_LIMIT:
                    envelope={'key':key,'sha256':hashlib.sha256(payload).hexdigest(),'payload':payload.decode('utf-8')}
                    _atomic(path,json.dumps(envelope,separators=(',',':')).encode('utf-8'));_remember(key,payload);_prune(path.parent)
    if not stable():raise ValueError('Contribution source changed while reading its query cache.')
    return json.loads(payload)
