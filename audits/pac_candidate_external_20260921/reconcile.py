"""Resolve bulk-comparison exceptions with current regular-report Schedule E."""
from external import rows, OUT
from concurrent.futures import ThreadPoolExecutor,as_completed
from collections import defaultdict,Counter
from decimal import Decimal
import json,hashlib

def task(unit, candidates):
    cycle,committee=unit
    # Candidate IDs scope the query; separate support/opposition in the result.
    candidates=sorted(candidates)
    data=[]
    for start in range(0,len(candidates),10):
        params={'committee_id':committee,'cycle':int(cycle),'is_notice':'false','candidate_id':candidates[start:start+10]}
        suffix='' if len(candidates)<=10 else f'-batch{start//10}'
        data.extend(rows('schedules/schedule_e/',params,f'exception-{cycle}-{committee}'+suffix))
    groups=defaultdict(list)
    for r in data:
        if r.get('is_notice') is not False:raise ValueError('Unexpected notice')
        if r.get('memo_code')=='X' or r.get('memoed_subtotal'):continue
        groups[r.get('candidate_id'),{'S':'Support','O':'Oppose'}.get(r.get('support_oppose_indicator'),'Unknown')].append(r)
    return unit,groups

def main():
    comparisons=json.loads((OUT/'bulk_comparison.json').read_text())
    exceptions=[r for r in comparisons if r['status']!='exact_current_bulk_match']
    targets=defaultdict(set)
    for r in exceptions:targets[r['cycle'],r['committee']].add(r['candidate_id'])
    results={};failures=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures={pool.submit(task,unit,candidates):unit for unit,candidates in targets.items()}
        for n,future in enumerate(as_completed(futures),1):
            try:
                unit,groups=future.result();results[unit]=groups
            except Exception as e:
                failures.append({'unit':futures[future],'error':str(e)})
            if n%5==0:print('Fetched',n,'of',len(targets),'committee/cycles',flush=True)
    out=[]
    for r in exceptions:
        unit=(r['cycle'],r['committee'])
        if unit not in results:
            out.append(dict(r,external_status='unavailable'));continue
        source=results[unit].get((r['candidate_id'],r['direction']),[])
        fingerprint_fields=('file_number','transaction_id','candidate_id','support_oppose_indicator','expenditure_amount','expenditure_date','dissemination_date','payee_name','expenditure_description')
        unique={tuple(x.get(k) for k in fingerprint_fields):x for x in source}
        dedup_exact=sum((Decimal(str(x['expenditure_amount'])) for x in unique.values()),Decimal(0))
        dedup_integer=sum((Decimal(int(Decimal(str(x['expenditure_amount'])))) for x in unique.values()),Decimal(0))
        exact=sum((Decimal(str(x['expenditure_amount'])) for x in source),Decimal(0))
        integer=sum((Decimal(int(Decimal(str(x['expenditure_amount'])))) for x in source),Decimal(0))
        value=Decimal(r['amount'])
        status=('no_regular_api_rows' if not source else 'matches_api_exact' if exact==value else 'matches_api_whole_dollar_source' if integer==value else 'matches_identical_filing_items_once' if dedup_integer==value else 'different_from_current_api')
        out.append(dict(r,external_status=status,api_exact=str(exact),api_whole_dollar=str(integer),api_unique_exact=str(dedup_exact),api_unique_whole_dollar=str(dedup_integer),api_count=len(source),api_unique_count=len(unique),api_latest_filing=max((str(x.get('filing_date') or '') for x in source),default=''),source_urls=sorted({x['pdf_url'] for x in source if x.get('pdf_url')})))
    (OUT/'external_exceptions.json').write_text(json.dumps(out,indent=2))
    (OUT/'external_failures.json').write_text(json.dumps(failures,indent=2))
    print('RECONCILIATION',dict(Counter(r['external_status'] for r in out)),'failures',len(failures),flush=True)

if __name__=='__main__':main()
