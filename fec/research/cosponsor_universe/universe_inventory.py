"""Whole-system data-family census; avoids secrets, duplicate checkouts and browser stores."""
import collections
import csv
import datetime as dt
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess

from universe_common import ROOT, OUT, digest, log, read_json, stamp, write_json

DATA_SUFFIXES={'.json','.jsonl','.ndjson','.csv','.tsv','.parquet','.db','.sqlite','.sqlite3','.xlsx','.dta','.rds','.npz','.npy','.f32','.joblib','.pkl','.pdf','.docx','.wav','.mp3','.flac','.mp4','.zip','.gz'}
SKIP=['.git','.claude/worktrees','.venv-politico','node_modules','__pycache__','vendor','plot_vendor','.pytest_cache','chrome_debug_profile_20260817','backups','archive','originals','orphan','_quarantine*','CLEAN_STATE*']


def family(path,root):
    relative=path.relative_to(root)
    parts=list(relative.parts)
    # Keep distinct substantive pipeline families, collapse only dated run suffixes.
    if root==ROOT and parts[0] in ['data','source_data','fec']:
        return '/'.join(parts[:min(3,len(parts)-1)]) or 'root'
    if len(parts)>1:
        head=parts[:2] if parts[0]=='outputs' else parts[:1]
        return '/'.join(re.sub(r'[_-]20\d{6}(?:T\d+Z)?(?:[_-].*)?$','_DATED',x) for x in head)
    return 'root/'+re.sub(r'[_-]20\d{6}.*$','_DATED',path.stem)


def schema(path):
    suffix=path.suffix.lower();result={}
    try:
        if suffix in ['.csv','.tsv']:
            with path.open(encoding='utf-8-sig',errors='replace',newline='') as f:
                reader=csv.reader(f,delimiter='\t' if suffix=='.tsv' else ',');result['columns']=next(reader,[])
        elif suffix in ['.jsonl','.ndjson']:
            with path.open(encoding='utf-8-sig',errors='replace') as f:line=f.readline(2*1024*1024)
            row=json.loads(line);result['first_record_keys']=list(row) if isinstance(row,dict) else type(row).__name__
        elif suffix=='.json' and path.stat().st_size<=12*1024*1024:
            value=read_json(path)
            if isinstance(value,dict):
                result['top_level_keys']=list(value)[:80]
                result['top_level_key_count']=len(value)
                for key in ['generated_at','generated_utc','as_of','asof','snapshot_date','status','schema','scoring_authority','canonical_eligible']:
                    if key in value and isinstance(value[key],(str,int,float,bool,type(None))):result[key]=value[key]
                containers={k:len(v) for k,v in value.items() if isinstance(v,(list,dict))}
                result['container_lengths']=dict(list(containers.items())[:30])
            else:result.update(container_type=type(value).__name__,rows=len(value) if isinstance(value,list) else None)
        elif suffix=='.parquet':
            import pyarrow.parquet as pq
            p=pq.ParquetFile(path);result.update(rows=p.metadata.num_rows,columns=p.schema.names)
        elif suffix in ['.db','.sqlite','.sqlite3']:
            connection=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=10)
            try:
                tables=connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
                result['tables']={}
                for (name,) in tables:
                    escaped=name.replace('"','""')
                    cols=[r[1] for r in connection.execute(f'PRAGMA table_info("{escaped}")')]
                    result['tables'][name]=dict(columns=cols)
            finally:connection.close()
    except Exception as e:result['schema_error']=type(e).__name__+': '+str(e)[:180]
    return result


def run():
    manifest=read_json(ROOT/'data/system/system_manifest.json')
    store_rows=[];secret_paths=set()
    for s in manifest['stores']:
        if s['class']=='SECRET':
            secret_paths.add(Path(s['path']).resolve());store_rows.append(dict(id=s['id'],classification='SECRET',disposition='not opened; nonpredictive configuration'));continue
        p=Path(s['path']);store_rows.append(dict(id=s['id'],classification=s['class'],path=str(p),present_now=p.exists(),producer=s.get('producer'),
             consumers=s.get('consumers'),derives_from=s.get('derives_from'),note=s.get('note'),prior_measured=s.get('measured')))
    write_json(OUT/'declared_store_inventory.json',dict(observed_utc=stamp(),source_manifest_sha256=digest(ROOT/'data/system/system_manifest.json'),source_manifest_time=manifest['generated_utc'],stores=store_rows))
    roots=[ROOT,Path(os.environ['LOCALAPPDATA'])/'Melange',Path('C:/melange-data')]
    stats={};details=[];probes=[];total=0;errors=[]
    with (OUT/'artifact_inventory.jsonl').open('w',encoding='utf-8') as handle:
        for root in roots:
            command=['rg','--files','--hidden','--no-ignore']
            for exclude in SKIP:command+=['-g','!**/'+exclude+'/**','-g','!'+exclude+'/**']
            command+=['-g','!**/.env*','-g','!**/.mcp.json','-g','!**/*api_key*','-g','!**/*secret*']
            scan=subprocess.run(command,cwd=root,capture_output=True,text=True,encoding='utf-8',errors='replace')
            if scan.returncode not in [0,1]:errors.append(dict(root=str(root),stderr=scan.stderr[:500]))
            for relative in scan.stdout.splitlines():
                p=root/relative
                if p.suffix.lower() not in DATA_SUFFIXES or p.resolve() in secret_paths:continue
                if p.is_relative_to(OUT):continue
                try:st=p.stat()
                except OSError:continue
                group=str(root)+'::'+family(p,root)
                row=dict(path=str(p),family=group,bytes=st.st_size,mtime_utc=dt.datetime.fromtimestamp(st.st_mtime,dt.timezone.utc).isoformat(),suffix=p.suffix.lower())
                handle.write(json.dumps(row,ensure_ascii=False)+'\n');total+=1
                g=stats.setdefault(group,dict(files=0,bytes=0,extensions=collections.Counter(),examples=[],newest=None))
                g['files']+=1;g['bytes']+=st.st_size;g['extensions'][p.suffix.lower()]+=1
                if len(g['examples'])<4:g['examples'].append(str(p))
                if g['newest'] is None or row['mtime_utc']>g['newest']['mtime_utc']:g['newest']=row
                # Full schema census for root live artifacts and shallow canonical data, not every raw observation.
                relparts=p.relative_to(ROOT).parts if p.is_relative_to(ROOT) else []
                if root==ROOT and (len(relparts)==1 or (relparts and relparts[0]=='data' and len(relparts)<=3)):
                    if p.suffix.lower() in {'.json','.jsonl','.ndjson','.csv','.tsv','.db','.sqlite','.parquet'}:probes.append(p)
            log(f'Inventory walked {root}; {total:,} cumulative data artifacts')
    for p in probes:
        before=p.stat();detail=schema(p);after=p.stat()
        details.append(dict(path=str(p),bytes=before.st_size,stable_during_probe=(before.st_mtime_ns,before.st_size)==(after.st_mtime_ns,after.st_size),schema=detail))
    write_json(OUT/'live_schema_inventory.json',dict(observed_utc=stamp(),artifacts=details))
    write_json(OUT/'data_family_inventory.json',dict(completed_utc=stamp(),roots=[str(r) for r in roots],artifact_count=total,family_count=len(stats),
        families=stats,excluded_duplicate_or_operational_directories=SKIP,walk_errors=errors,schema_probed_artifacts=len(details),
        note='Metadata census plus schema inspection of live/shallow canonical artifacts; not a claim that every raw byte is scientifically validated. Backup/check-out copies are represented by store metadata, not counted as independent evidence.'))
    log(f'Inventory complete: {total:,} artifacts in {len(stats):,} path families; {len(details):,} live schemas')


if __name__=='__main__':run()
