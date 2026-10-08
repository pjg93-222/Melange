"""Read-only replay of preserved snapshots and raw PAS2 evidence."""
from collections import defaultdict
from decimal import Decimal
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result
old=module(HERE/'before/mentat/app/downstream.py','before_downstream')
new=module(ROOT/'mentat/app/downstream.py','after_downstream')
source=ROOT/'mentat/.cache/pac-evidence/fairshake-20260908/snapshots.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
fingerprint=sha(source)
units={(str(u['cycle']),u['committee_id']):dict(u,_source=str(source),_sha256=fingerprint)
       for u in json.loads(source.read_bytes())}
roots=[(str(cycle),'C00835959') for cycle in [2024,2026]]
results=[]
for implementation in [old,new]:
    found=implementation.network(roots,units)
    totals=defaultdict(Decimal)
    for row in implementation.activity(found):
        totals[row['cycle'],row['committee'],row['candidate_id'],row['direction']]+=row['amount']
    results.append((found,totals))
before,after=results[0][1],results[1][1]
ledger=[dict(cycle=k[0],committee=k[1],candidate_id=k[2],direction=k[3],
             before=str(before[k]),after=str(after[k]),delta=str(after[k]-before[k]))
        for k in sorted(set(before)|set(after))]
barr=[r for r in ledger if r['candidate_id']=='H0KY06104']
assert sum(Decimal(r['after']) for r in barr if r['cycle']=='2024')==Decimal('106708')
assert sum(Decimal(r['after']) for r in barr if r['cycle']=='2026')==Decimal('7170138.4')
bulk=[]
for year in [2024,2026]:
    path=ROOT/f'mentat/inputs/fec_beneficiary/pas2{str(year)[2:]}/itpas2.txt'
    selected={committee for cycle,committee in results[1][0]['keys'] if cycle==str(year)}
    rows=[];seen={}
    with path.open(encoding='utf-8-sig') as stream:
        for number,line in enumerate(stream,1):
            fields=line.rstrip('\n\r').split('|')
            if len(fields)<22 or fields[0] not in selected or fields[16].strip() or fields[19].strip()=='X':continue
            key=fields[21].strip()
            if key and key in seen:
                assert seen[key]==fields,'Conflicting source ID'
                continue
            if key:seen[key]=fields
            rows.append(dict(line=number,committee=fields[0],sub_id=key,amount=fields[14],
                             transaction_id=fields[17],file_num=fields[18]))
    bulk.append(dict(cycle=year,source=str(path),sha256=sha(path),committees=sorted(selected),
                     unidentified_candidate_rows=rows,
                     before_amount='0',after_amount=str(sum((Decimal(r['amount']) for r in rows),Decimal(0))),
                     basis='Non-memo PAS2 rows with blank candidate ID; exact repeated IDs counted once. Current count_all policy.'))
assert fingerprint==sha(source)
result=dict(source=str(source),sha256_before=fingerprint,sha256_after=sha(source),
            ledger=ledger,barr=barr,material_deltas=[r for r in ledger if Decimal(r['delta'])],
            missing_frontier=[list(k) for k in results[1][0]['missing']],sources=new.sources(results[1][0]),
            unidentified_candidate_bulk=bulk,
            basis='Before/after implementation on identical preserved observations; not a published-workbook delta.')
(HERE/'preserved_evidence_ledger.json').write_text(json.dumps(result,indent=2))
print(json.dumps(dict(barr=barr,material_delta_rows=len(result['material_deltas']),
                     unknown_bulk=[dict(cycle=r['cycle'],amount=r['after_amount'],rows=len(r['unidentified_candidate_rows'])) for r in bulk],
                     missing_frontier=result['missing_frontier'])))
