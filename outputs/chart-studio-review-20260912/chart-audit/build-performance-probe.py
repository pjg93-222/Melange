"""Toy-only SQL plans and staging/cleanup timings; no application data opened."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import time

ROOT=Path(__file__).parent
CROSS='''SELECT c.source_id FROM canonical_sources c JOIN filing_roots h ON c.file_num=h.file_num AND c.committee=h.committee
JOIN (SELECT c.committee,h.root,c.transaction_id FROM canonical_sources c JOIN filing_roots h ON c.file_num=h.file_num AND c.committee=h.committee
WHERE c.transaction_id!='' GROUP BY c.committee,h.root,c.transaction_id HAVING COUNT(DISTINCT c.company)>1) x
ON c.committee=x.committee AND h.root=x.root AND c.transaction_id=x.transaction_id'''

def plans_and_scale():
    results=[]
    for n in (4000,8000,16000,32000):
        with closing(sqlite3.connect(':memory:')) as db:
            db.executescript('CREATE TABLE canonical_sources(source_id TEXT PRIMARY KEY,company TEXT,committee TEXT,transaction_id TEXT,file_num TEXT,payload TEXT);CREATE INDEX canonical_company ON canonical_sources(company);CREATE TABLE filing_roots(file_num TEXT PRIMARY KEY,committee TEXT,root TEXT);CREATE TABLE receipts(source_id TEXT PRIMARY KEY,payload TEXT);CREATE TABLE facts(source_id TEXT PRIMARY KEY,amount INTEGER);')
            db.executemany('INSERT INTO filing_roots VALUES (?,?,?)',[(str(k),'C'+str(k%4),'ROOT'+str(k%4)) for k in range(20)])
            db.executemany('INSERT INTO canonical_sources VALUES (?,?,?,?,?,?)',[(str(i),'Company'+str(i%10),'C'+str(i%4),'TX'+str(i//20),str(i%20),'') for i in range(n)])
            calls=[0]
            def tick():calls[0]+=1;return 0
            db.set_progress_handler(tick,100)
            start=time.perf_counter();rows=db.execute(CROSS).fetchall();elapsed=time.perf_counter()-start
            db.set_progress_handler(None,0)
            results.append({'rows':n,'cross_company_result_rows':len(rows),'seconds':round(elapsed,6),'approx_vm_instructions':calls[0]*100})
            if n==4000:
                print(json.dumps({'cross_company_plan':[r[3] for r in db.execute('EXPLAIN QUERY PLAN '+CROSS)],
                    'company_read_plan':[r[3] for r in db.execute('EXPLAIN QUERY PLAN SELECT payload FROM canonical_sources WHERE company=?',('Company1',))],
                    'receipt_read_plan':[r[3] for r in db.execute('EXPLAIN QUERY PLAN SELECT payload FROM receipts WHERE source_id=?',('1',))],
                    'missing_receipt_plan':[r[3] for r in db.execute('EXPLAIN QUERY PLAN SELECT COUNT(*) FROM receipts r LEFT JOIN facts f USING(source_id) WHERE f.source_id IS NULL')]}),flush=True)
    print(json.dumps({'toy_cross_company_scaling':results}),flush=True)

def cleanup(full):
    with tempfile.TemporaryDirectory(prefix='toy-build-',dir=ROOT) as temporary:
        path=Path(temporary)/'stage.db';phases=[];trace=[]
        with closing(sqlite3.connect(path)) as db:
            db.execute('PRAGMA auto_vacuum='+str(full));db.execute('PRAGMA cache_size=-32768');db.set_trace_callback(lambda sql:trace.append(sql) if sql in ('BEGIN ','COMMIT') else None)
            db.executescript('CREATE TABLE facts(source_id TEXT PRIMARY KEY,company TEXT,cycle TEXT,payload TEXT);CREATE INDEX facts_company_cycle ON facts(company,cycle);CREATE TABLE receipts(source_id TEXT PRIMARY KEY,payload TEXT);')
            def phase(label,fn):
                start=time.perf_counter();fn();phases.append({'phase':label,'seconds':round(time.perf_counter()-start,6),'file_bytes':path.stat().st_size,'pages':db.execute('PRAGMA page_count').fetchone()[0],'free_pages':db.execute('PRAGMA freelist_count').fetchone()[0]})
            n=12000
            phase('receipts_insert',lambda:db.executemany('INSERT INTO receipts VALUES (?,?)',((str(i),'r'*350) for i in range(n))))
            phase('stage_schema_executescript',lambda:db.executescript('CREATE TABLE observations(source_id TEXT,payload TEXT);CREATE TABLE canonical_sources(source_id TEXT PRIMARY KEY,company TEXT,payload TEXT);'))
            phase('observations_insert',lambda:db.executemany('INSERT INTO observations VALUES (?,?)',((str(i),'o'*1400) for i in range(n))))
            phase('canonical_insert',lambda:db.execute("INSERT INTO canonical_sources SELECT source_id,'Company'||(CAST(source_id AS INTEGER)%10),payload FROM observations"))
            phase('drop_observations',lambda:db.execute('DROP TABLE observations'))
            phase('facts_insert',lambda:db.execute("INSERT INTO facts SELECT source_id,company,'2023-2024',substr(payload,1,400) FROM canonical_sources"))
            phase('drop_canonical_executescript',lambda:db.executescript('DROP TABLE canonical_sources;'))
            phase('drop_receipts',lambda:db.execute('DROP TABLE receipts'))
            phase('final_commit',db.commit)
            phase('integrity_check',lambda:db.execute('PRAGMA integrity_check').fetchone())
        print(json.dumps({'toy_cleanup_auto_vacuum':full,'rows':n,'phases':phases,'transaction_trace':trace}),flush=True)

def grouped_query_plans():
    with closing(sqlite3.connect(':memory:')) as db:
        db.executescript('CREATE TABLE facts(source_id TEXT PRIMARY KEY,company TEXT,cycle TEXT,zip5 TEXT,committee_id TEXT,state TEXT,contributor_key TEXT,receipt_cents INTEGER,original_cents INTEGER,supported_cents INTEGER,raw_cents INTEGER,unresolved INTEGER);CREATE INDEX facts_company_cycle ON facts(company,cycle);CREATE INDEX facts_zip ON facts(zip5);CREATE INDEX facts_recipient ON facts(committee_id);CREATE INDEX facts_state ON facts(state);')
        n=16000
        db.executemany('INSERT INTO facts VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',((str(i),'Company'+str(i%40),'2023-2024',str(10000+i%400),'C1','NY','Donor'+str(i%10000),100,100,0,100,1) for i in range(n)))
        full='SELECT zip5,COALESCE(SUM(receipt_cents),0) AS amount,COUNT(*) AS records,COUNT(DISTINCT contributor_key) AS contributors FROM facts WHERE receipt_cents!=0 GROUP BY zip5'
        minimal='SELECT zip5,COALESCE(SUM(receipt_cents),0) AS amount FROM facts WHERE receipt_cents!=0 GROUP BY zip5'
        queries={
            'current_group_count':'SELECT COUNT(*) FROM ('+full+') WHERE 1',
            'current_page':'SELECT * FROM ('+full+') WHERE 1 ORDER BY amount DESC,zip5 ASC LIMIT 50 OFFSET 0',
            'current_grouped_amount':'SELECT COALESCE(SUM(amount),0) FROM ('+full+') WHERE 1',
            'totals':'SELECT SUM(receipt_cents),COUNT(*),COUNT(DISTINCT contributor_key) FROM facts WHERE receipt_cents!=0',
            'comparison':'SELECT SUM(receipt_cents),SUM(original_cents),SUM(supported_cents),SUM(CASE WHEN unresolved=1 THEN ABS(raw_cents) ELSE 0 END),COUNT(CASE WHEN unresolved=1 THEN 1 END) FROM facts WHERE 1',
            'geography':'SELECT COUNT(*),COUNT(CASE WHEN zip5!=\'\' THEN 1 END),SUM(CASE WHEN zip5=\'\' THEN receipt_cents ELSE 0 END) FROM facts WHERE receipt_cents!=0',
            'minimal_page':'SELECT *,COUNT(*) OVER() AS group_count,SUM(amount) OVER() AS grouped_amount FROM ('+minimal+') WHERE 1 ORDER BY amount DESC,zip5 ASC LIMIT 50 OFFSET 0'}
        results={}
        for label,query in queries.items():
            calls=[0]
            def tick():calls[0]+=1;return 0
            db.set_progress_handler(tick,100)
            start=time.perf_counter();rows=db.execute(query).fetchall();elapsed=time.perf_counter()-start
            db.set_progress_handler(None,0)
            results[label]={'seconds':round(elapsed,6),'approx_vm_instructions':calls[0]*100,'returned_rows':len(rows),
                            'plan':[r[3] for r in db.execute('EXPLAIN QUERY PLAN '+query)],
                            'aggregate_opcodes':[list(r[1:7]) for r in db.execute('EXPLAIN '+query) if r[1]=='AggStep']}
        print(json.dumps({'toy_grouped_query_rows':n,'groups':400,'results':results}),flush=True)

plans_and_scale()
grouped_query_plans()
cleanup(1)
cleanup(0)
