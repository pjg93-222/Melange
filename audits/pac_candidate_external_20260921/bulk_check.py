"""Compare all saved independent-spending groups with fresh FEC PAS2 evidence."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict,Counter
from decimal import Decimal
import json,urllib.request,zipfile,io,hashlib

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]

def load_cycle(cycle):
    suffix=str(cycle)[-2:]
    url=f'https://www.fec.gov/files/bulk-downloads/{cycle}/pas2{suffix}.zip'
    path=OUT/f'official-pas2{suffix}.zip'
    if not path.exists():
        with urllib.request.urlopen(url,timeout=60) as response:
            raw=response.read()
            path.write_bytes(raw)
            (OUT/f'official-pas2{suffix}-receipt.json').write_text(json.dumps({'url':url,'last_modified':response.headers.get('Last-Modified'),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)},indent=2))
    groups=defaultdict(list)
    with zipfile.ZipFile(path) as z:
        name=next(n for n in z.namelist() if n.lower().endswith('itpas2.txt'))
        with z.open(name) as stream:
            for line in io.TextIOWrapper(stream,encoding='utf-8',errors='replace'):
                x=line.rstrip('\r\n').split('|')
                if len(x)!=22 or x[5] not in ('24E','24A'):continue
                direction={'24E':'Support','24A':'Oppose'}[x[5]]
                groups[(str(cycle),x[0],x[16],direction)].append(x)
    print(cycle,'groups',len(groups),'rows',sum(map(len,groups.values())),flush=True)
    return groups

def main():
    target=json.loads((OUT/'report_activity.json').read_text())
    target=[r for r in target if r['direction'] in ('Support','Oppose')]
    allgroups={}
    with ThreadPoolExecutor(max_workers=3) as pool:
        for g in pool.map(load_cycle,(2022,2024,2026)):allgroups.update(g)
    result=[]
    for r in target:
        k=(r['cycle'],r['committee'],r['candidate_id'],r['direction'])
        rows=allgroups.get(k,[])
        nonmemo=[x for x in rows if x[19]!='X']
        by_id={x[21]:x for x in nonmemo}
        simple_total=sum((Decimal(x[14]) for x in by_id.values()),Decimal(0))
        # No guessed amendment resolver: raw sums are comparison signals only.
        status='exact_current_bulk_match' if simple_total==Decimal(r['amount']) and rows else 'requires_reconciliation' if rows else 'no_current_bulk_group'
        result.append(dict(r,current_bulk_sum=str(simple_total),current_bulk_rows=len(rows),current_nonmemo_unique_rows=len(by_id),status=status))
    (OUT/'bulk_comparison.json').write_text(json.dumps(result,indent=2))
    summary=Counter(r['status'] for r in result)
    print('RESULT',dict(summary),flush=True)
    print('BY_REPORT',json.dumps({p:dict(Counter(r['status'] for r in result if r['report']==p)) for p in sorted({r['report'] for r in result})}),flush=True)

if __name__=='__main__':main()
