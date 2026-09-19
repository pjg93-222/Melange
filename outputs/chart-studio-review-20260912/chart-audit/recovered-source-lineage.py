"""Read-only comparison of recovered full source universes to accepted facts."""
from collections import Counter
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'mentat/tools'))
from report_source_guard import source_facts

def read(path): return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def ro(path):return sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)

reports=[]
for p in (ROOT/'mentat/state/cross-reference').glob('*/report.json'):
    try:
        report=read(p)
        if report.get('status')=='completed':reports.append((p,report))
    except (OSError,ValueError):pass

output=Path(__file__).with_name('recovered-source-lineage.jsonl')
with output.open('w',encoding='utf-8') as receipt:
    for hydration_path in sorted((ROOT/'mentat/.cache/receipt-metadata-repair-20260910').glob('*/mentat.db.hydration.json')):
        hydration=read(hydration_path);slug=hydration_path.parent.name
        current_path=ROOT/'mentat/state/accepted-report-sources'/slug/'2022-2024-2026/current.json'
        accepted=read(current_path);source=Path(hydration['output']);snapshot=Path(accepted['snapshot'])
        before=sha(source);snapshot_hash=sha(snapshot)
        if snapshot_hash!=accepted['snapshot_sha256']:raise ValueError('Accepted snapshot hash mismatch: '+slug)
        if accepted['database_sha256']!=hydration['source_sha256']:raise ValueError('Original source identity mismatch: '+slug)
        sidecars={suffix:Path(str(source)+suffix).stat().st_size for suffix in ('-wal','-journal') if Path(str(source)+suffix).exists()}
        if any(sidecars.values()):raise ValueError('Recovered source has active writes: '+slug)
        with closing(ro(snapshot)) as db:
            baseline=dict(db.execute('SELECT id,raw FROM facts'))
        counts=Counter();seen={};net=0;gross=0
        for sid,raw in source_facts(source,accepted['industry'],[2022,2024,2026]):
            counts['source_observations']+=1
            if sid in seen:
                counts['repeated_source_observations']+=1
                if seen[sid]!=raw:counts['conflicting_source_copies']+=1
                continue
            seen[sid]=raw;counts['source_ids']+=1
            amount=json.loads(raw)['amount_cents'];net+=amount;gross+=abs(amount)
            old=baseline.pop(sid,None)
            counts['added' if old is None else 'changed' if old!=raw else 'unchanged']+=1
        counts['missing']=len(baseline)
        after=sha(source)
        matching=[]
        for p,r in reports:
            scope=r.get('scope',{})
            if scope.get('database_sha256')==before and scope.get('industries')==[accepted['industry']]:
                comparison=p.with_name('source-comparison.json')
                c=read(comparison) if comparison.exists() else {}
                matching.append({'report':str(p),'report_sha256':sha(p),'cycles':scope.get('cycles'),
                                 'source_comparison_changes':len(c.get('changes',[])),
                                 'comparison_baseline':c.get('baseline'),
                                 'comparison_has_baseline':bool(c.get('baseline'))})
        row={'industry':accepted['industry'],'source':str(source),'current_database_sha256':before,
             'source_stable':before==after,'original_database_sha256':accepted['database_sha256'],
             'initial_hydration_database_sha256':hydration.get('output_sha256'),
             'accepted_pointer':str(current_path),'accepted_pointer_sha256':sha(current_path),
             'snapshot':str(snapshot),'snapshot_sha256':snapshot_hash,'counts':dict(counts),
             'raw_source_net_cents':net,'raw_source_gross_cents':gross,
             'matching_current_hash_reports':matching,
             'full_financial_universe_preserved':before==after and all(counts[k]==0 for k in ('added','changed','missing','conflicting_source_copies'))}
        line=json.dumps(row,sort_keys=True);receipt.write(line+'\n');receipt.flush();print(line,flush=True)
