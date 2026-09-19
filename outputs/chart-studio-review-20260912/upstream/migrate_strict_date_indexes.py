"""One-time, audited compatibility copy; original strict-date indexes stay intact."""
import ast,hashlib,json,os,shutil,sqlite3,sys,time,uuid
from contextlib import closing
from pathlib import Path
sys.path.insert(0,'mentat/app')
import contribution_data as c
import contribution_source_guard as source_guard
import contribution_workbook_guard as workbook_guard

ROOT=Path('outputs/chart-studio-implementation-20260912/cache-migration')
INPUT=json.loads((ROOT/'inputs.json').read_text())
DIRECTORY=Path(r'C:/Users/pgoff/OneDrive/Desktop/Mentat Complete Files')

def facts_digest(db):
    digest=hashlib.sha256();count=0
    for row in db.execute('SELECT * FROM facts ORDER BY rowid'):
        digest.update(json.dumps(list(row),ensure_ascii=False,separators=(',',':')).encode('utf-8'));digest.update(b'\n');count+=1
    return {'rows':count,'sha256':digest.hexdigest(),'algorithm':'SHA256 of every complete fact row in preserved rowid order, JSON UTF-8 plus newline'}

assert c._hash(ROOT/'contribution_data.before.py')==INPUT['old_code_sha256']
assert c._hash('mentat/app/contribution_data.py')==INPUT['new_code_sha256']
before=ast.parse((ROOT/'contribution_data.before.py').read_text())
after=ast.parse(Path('mentat/app/contribution_data.py').read_text())
untouched=lambda tree:[ast.dump(n,include_attributes=False) for n in tree.body if getattr(n,'name',None) not in ('_record','_Receipts','_materialize')]
assert untouched(before)==untouched(after),'Changes extend beyond the reviewed schema adapter and source preflight.'
for path,expected in INPUT['rules'].items():
    if Path(path).resolve()!=Path(c.__file__).resolve():assert c._hash(path)==expected,('Accounting rule changed',path)

receipt=[]
for item in INPUT['indexes']:
    start=time.monotonic();source=c._source(DIRECTORY,{'dataset':item['industry']});token=c._token(source)
    assert c._provenance(source)==item['provenance'],'Source/workbook/payload/engine identity changed.'
    # Capture matched the old live token. Unmodified evidence, manifests and
    # other token inputs must still predate that capture; only data.py changed.
    epoch=[source['workbook'],source['database'],source['payload'],source['manifest']]
    if source.get('hydration_manifest'):epoch.append(source['hydration_manifest'])
    if source.get('ledger'):epoch += [source['ledger'],source['ledger'].with_name('report.json')]
    else:epoch += [p for suffix in ('','-wal') if (p:=c.PROJECT/('state/cross-reference/evidence.sqlite'+suffix)).exists() and p.stat().st_size]
    assert all(max(Path(p).stat().st_mtime_ns,Path(p).stat().st_ctime_ns)<=INPUT['capture_mtime_ns'] for p in epoch),'A pinned token component changed after capture.'
    proof=source_guard.verify(source);workbook_guard.verify_sources(DIRECTORY,item['industry'])
    old=Path(item['path']);destination=c.CACHE_ROOT/(token+'.sqlite')
    assert old.resolve().is_relative_to(c.CACHE_ROOT.resolve()) and destination.resolve().is_relative_to(c.CACHE_ROOT.resolve())
    assert old.name==item['old_token']+'.sqlite' and token!=item['old_token'] and not destination.exists()
    original_sha=c._hash(old)
    with closing(c._ro(old)) as db:
        manifest=json.loads(db.execute("SELECT value FROM metadata WHERE key='manifest'").fetchone()[0])
        assert manifest['token']==item['old_token'] and manifest['provenance']['index_token']==item['old_token']
        assert {k:v for k,v in manifest['provenance'].items() if k!='index_token'}==item['provenance']
        assert manifest['ledger_run_id']==(source.get('ledger_report') or {}).get('run_id')
        assert manifest['receipt_cycles']==manifest['expected_receipt_cycles']
        old_facts=facts_digest(db)
    pending=destination.with_suffix('.migration-'+uuid.uuid4().hex+'.pending')
    shutil.copyfile(old,pending)
    assert c._hash(pending)==original_sha,'Copied bytes differ from the original index.'
    migration={'reason':'Explicitly declared compact payload date omission is now validated by source date-derived cycle and complete source proof. Existing seven indexes passed strict present-date comparison; their facts are unchanged.',
        'original_index_token':item['old_token'],'original_index_sha256':original_sha,'original_build_code_sha256':INPUT['old_code_sha256'],
        'adapter_code_sha256':INPUT['new_code_sha256'],'facts':old_facts,'source_proof':proof}
    manifest['token']=token;manifest['provenance']['index_token']=token
    manifest['provenance']['cache_compatibility']={k:v for k,v in migration.items() if k not in ('source_proof','reason')}
    manifest['cache_compatibility']=migration;manifest['source_proof']=proof
    with closing(sqlite3.connect(pending)) as db:
        db.execute("UPDATE metadata SET value=? WHERE key='manifest'",(json.dumps(manifest),));db.commit()
        assert facts_digest(db)==old_facts,'Any fact changed during metadata-only compatibility copy.'
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert dict(db.execute('SELECT cycle,SUM(receipt_cents) FROM facts NOT INDEXED GROUP BY cycle'))==manifest['expected_receipt_cycles']
    assert c._hash(old)==original_sha and c._token(source)==token
    os.replace(pending,destination)
    result={'industry':item['industry'],'status':'passed','old_index':str(old),'new_index':str(destination),'new_index_token':token,
        'new_index_sha256':c._hash(destination),'seconds':round(time.monotonic()-start,2),**migration}
    receipt.append(result);(ROOT/'receipt.json').write_text(json.dumps(receipt,indent=2))
    print(json.dumps({'industry':item['industry'],'status':'passed','facts':old_facts,'seconds':result['seconds']}),flush=True)
assert len(receipt)==7
