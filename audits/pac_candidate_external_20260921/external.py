"""Fetch public FEC evidence without logging credentials or changing app data."""
import sys, json, hashlib, urllib.request, urllib.parse, urllib.error, time
from pathlib import Path
from decimal import Decimal
from collections import defaultdict
from datetime import datetime, timezone

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
sys.path.insert(0,str(ROOT/'mentat/tools'))
from fec_key_store import load_keys
KEY = load_keys()[0]

def fetch(endpoint, params, name):
    path = OUT/(name+'.json')
    if path.exists(): return json.loads(path.read_text())['response']
    request_url = 'https://api.open.fec.gov/v1/'+endpoint+'?'+urllib.parse.urlencode(dict(params,api_key=KEY),doseq=True)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request_url,timeout=45) as response: raw=response.read()
            data=json.loads(raw)
            receipt={'endpoint':endpoint,'params':params,'retrieved_at':datetime.now(timezone.utc).isoformat(),'sha256':hashlib.sha256(raw).hexdigest(),'response':data}
            path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
            return data
        except urllib.error.HTTPError as error:
            if error.code not in (429,500,502,503,504):
                raise RuntimeError(f'FEC HTTP {error.code}: {error.read().decode()[:400]}') from None
        except (TimeoutError,urllib.error.URLError): pass
        time.sleep(2*(attempt+1))
    raise RuntimeError('FEC request failed after retries: '+endpoint)

def rows(endpoint,params,name):
    result=[];cursor={};seen=set()
    for n in range(1000):
        data=fetch(endpoint,dict(params,per_page=100,**cursor),name+f'-{n:03}')
        result.extend(data['results'])
        if len(data['results'])<100: return result
        cursor=data['pagination'].get('last_indexes') or {'page':n+2}
        signature=json.dumps(cursor,sort_keys=True)
        if signature in seen:raise ValueError('Repeated FEC cursor')
        seen.add(signature)
    raise ValueError('Unfinished pagination')

def culac():
    output=[]
    for cycle in (2022,2024,2026):
        committee='C00007880'
        expenditures=rows('schedules/schedule_e/',{'committee_id':committee,'cycle':cycle,'is_notice':'false'},f'culac-{cycle}-schedule-e')
        totals=fetch(f'committee/{committee}/totals/',{'cycle':cycle,'per_page':100},f'culac-{cycle}-totals')['results']
        groups={}
        for row in expenditures:
            assert row['is_notice'] is False
            if row.get('memo_code')=='X' or row.get('memoed_subtotal'): continue
            identity=(row.get('candidate_id'),row.get('candidate_name'),row.get('support_oppose_indicator'))
            g=groups.setdefault(identity,{'cycle':cycle,'candidate_id':identity[0],'candidate':identity[1],'direction':identity[2],'amount':Decimal(0),'transactions':[]})
            g['amount']+=Decimal(str(row['expenditure_amount']))
            g['transactions'].append({k:row.get(k) for k in ['sub_id','transaction_id','expenditure_amount','expenditure_date','dissemination_date','payee_name','expenditure_description','pdf_url','file_number','candidate_office','candidate_office_state','candidate_office_district']})
        result={'cycle':cycle,'rows':len(expenditures),'groups':list(groups.values()),'sum':sum((g['amount'] for g in groups.values()),Decimal(0)),'official_summary':totals[0].get('independent_expenditures') if len(totals)==1 else None}
        output.append(result);print(json.dumps(result,default=str),flush=True)
    (OUT/'culac_external.json').write_text(json.dumps(output,indent=2,default=str))

if __name__=='__main__':culac()
