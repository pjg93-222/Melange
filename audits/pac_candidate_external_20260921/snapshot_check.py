from pathlib import Path
from collections import defaultdict,Counter
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
import json,sys
from external import OUT,ROOT,rows
sys.path.insert(0,str(ROOT/'mentat/app'))
import downstream

def aggregate(data):
    groups=defaultdict(Decimal)
    for r in data:
        if downstream.memo(r) or r.get('is_notice') is True:continue
        groups[r.get('candidate_id') or '',r.get('support_oppose_indicator') or '']+=Decimal(str(r['expenditure_amount']))
    return groups

def check(item):
    (cycle,committee),unit=item
    current=rows('schedules/schedule_e/',{'committee_id':committee,'cycle':int(cycle),'is_notice':'false'},f'snapshot-{cycle}-{committee}')
    old=aggregate(downstream.observations(unit,'expenditures'));new=aggregate(current)
    result=[]
    for k in old.keys() | new.keys():
        state='match' if k in old and k in new and old[k]==new[k] else 'new_current_group' if k not in old else 'changed_current_group' if k in new else 'absent_current_group'
        result.append({'cycle':cycle,'committee':committee,'candidate_id':k[0],'direction':k[1],'saved_amount':str(old[k]) if k in old else None,'current_amount':str(new[k]) if k in new else None,'status':state,'saved_coverage_end':unit['totals'].get('coverage_end_date'),'source':unit['_source']})
    return result

out=[]
with ThreadPoolExecutor(max_workers=3) as pool:
    for result in pool.map(check,downstream.inventory().items()):out.extend(result)
(OUT/'snapshot_comparison.json').write_text(json.dumps(out,indent=2))
print(dict(Counter((r['cycle'],r['status']) for r in out)))
