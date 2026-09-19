"""Physical source database checks with SQLite read-only connections."""
import hashlib
import json
from pathlib import Path
import sqlite3
import time

OUT=Path(__file__).resolve().parent
sources=json.loads((OUT/'report-sources.json').read_text())
results=[]
for source in sources:
    if not source.get('available'):continue
    path=Path(source['database']);started=time.monotonic()
    stat=path.stat();before=(stat.st_size,stat.st_mtime_ns)
    row={'dataset':source['id'],'database':str(path),'bytes':stat.st_size}
    sidecars=[str(p) for suffix in ('-wal','-journal') if (p:=Path(str(path)+suffix)).exists() and p.stat().st_size]
    row['nonempty_write_sidecars']=sidecars
    if sidecars:row['status']='skipped_active_sidecar'
    else:
        try:
            with sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True,timeout=.2) as db:
                db.execute('PRAGMA query_only=ON')
                row['quick_check']=[r[0] for r in db.execute('PRAGMA quick_check')]
                row['tables']={}
                for table in ('contributions','corporate_giving'):
                    rows,missing=db.execute('SELECT COUNT(*),SUM(CASE WHEN sub_id IS NULL OR sub_id=\'\' THEN 1 ELSE 0 END) FROM '+table+' WHERE industry=?',(source['industry'],)).fetchone()
                    row['tables'][table]={'observations':rows,'missing_source_ids':missing or 0}
            stat=path.stat()
            row['unchanged_during_check']=before==(stat.st_size,stat.st_mtime_ns)
            row['status']='checked'
        except Exception as error:row.update(status='error',error=str(error))
    row['seconds']=round(time.monotonic()-started,2)
    results.append(row)
    (OUT/'source-database-checks.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(json.dumps(row),flush=True)
